"""The clip's SOMA segment turns to MyoFullBody's joint angles, as OpenSim's OpenSense does with IMUs (Al Borno et al.
2022, doi:10.1186/s12984-022-01001-x; opensim-core's IMUPlacer and IMUInverseKinematicsTool, Apache-2.0): each
segment a virtual orientation sensor on the body it rides, calibrated on the person's standing frame (`calibration`,
`offsets`), fitted again over the whole clip (`refitted`); per frame the model's own leading coordinates minimise the
sensors' squared error angles, MuJoCo's couplings kept, the pelvis placed where SOMA's Hips carry it, the standing
feet held on the ground (`motion`); the low-passed path's feet put back on the ground (`landed`)."""
import mujoco
import numpy as np
from scipy.spatial.transform import Rotation

from bone_groups import HIPS, TARGETS, sided
from contact import on_ground, unslipped
from model import TO_OWN, body_index, default_pose, limited, own_pose

FIT_DAMPING = 1e-3
# The fit's weight of a radian (or metre) a joint moves from the frame before: 0.05 left the hanging arm's plane of
# elevation (MoBL-ARMS' gimbal) swinging up to 10,000 deg/s2, about 130 N m of the pelvis' residual (2026-10-28).
FIT_STEADY = 0.2
# The fit holds the lowest point of a standing foot's body on the ground and keeps every foot point out of it,
# FIT_GROUND its weight per metre.
FIT_GROUND = 100.0
LAND_ROUNDS = 2  # the path landed and low-passed again before it is landed last
OFFSET_ROUNDS = 3  # the offsets fitted again over the clip, each round with the path fitted on the last
FIT_FIRST, FIT_NEXT = 400, 40  # fit iterations at the first frame, then each next one from the last


def calibration(person, segments):
    """The frame the sensors are calibrated on (segments x 4 x 4, the person's frame): the rig's standing clip's first
    frame, else SOMA's bind."""
    if person.get("standing") is not None:
        return np.asarray(person["standing"], dtype=float)
    names = [str(name) for name in person["rig"]["names"]]
    bind = np.asarray(person["rig"]["bind"], dtype=float)
    return np.array([bind[names.index(segment)] for segment in segments])


def _heading(model, data, frame, index):
    """OpenSense's heading correction (OpenSenseUtilities::computeHeadingCorrection): the turn about up (3 x 3, the
    person's frame) that faces the calibration frame as the model's default pose faces, read off the hip joints' line
    (left to right) of each."""
    theirs = frame[index["RightLeg"]][:3, 3] - frame[index["LeftLeg"]][:3, 3]
    mine = TO_OWN @ (data.xpos[body_index(model, HIPS["RightLeg"])] - data.xpos[body_index(model, HIPS["LeftLeg"])])
    angle = np.arctan2(theirs[0], theirs[2]) - np.arctan2(mine[0], mine[2])
    return Rotation.from_rotvec([0.0, -angle, 0.0]).as_matrix()


def offsets(model, couplings, person, segments, bodies):
    """OpenSense's IMUPlacer: each segment a sensor on the body it rides, calibrated once on the person's standing
    frame (`calibration`) as the model's default pose, its heading corrected (`_heading`): each segment's fixed turn
    to its body ({segment: 3 x 3}, R_FB of IMUPlacer.cpp, transposed) and its body's place in the segment's frame
    ({segment: 3}), the model's hip joints' middle on SOMA's."""
    data = default_pose(model, couplings)
    frame = calibration(person, segments)
    index = {segment: number for number, segment in enumerate(segments)}
    turn = _heading(model, data, frame, index)
    middle = (frame[index["LeftLeg"]][:3, 3] + frame[index["RightLeg"]][:3, 3]) / 2
    frame = frame.copy()
    for world in frame:  # the calibration frame turned about its hips' middle
        world[:3, :3] = turn @ world[:3, :3]
        world[:3, 3] = middle + turn @ (world[:3, 3] - middle)
    moved = middle - TO_OWN @ np.mean([data.xpos[body_index(model, name)] for name in HIPS.values()], axis=0)
    turns, places = {}, {}
    for segment in segments:
        if segment in bodies:
            body = own_pose(model, data, bodies[segment])
            turns[segment] = frame[index[segment]][:3, :3].T @ body[:3, :3]
            places[segment] = (np.linalg.inv(frame[index[segment]]) @ [*(body[:3, 3] + moved), 1.0])[:3]
    return turns, places


def _fitted(model, couplings, targets, qpos, rounds, before=None, ground=None, feet=(), planted=(), stood=None):
    """The model's qpos whose bodies turn as `targets` ({body: 3 x 3, MuJoCo's frame}): OpenSense's inverse
    kinematics (Simbody's OrientationSensors goal, every sensor's error angle squared, weight 1 each), by damped least
    squares on the leading dofs, `rounds` steps from `qpos`, the joints kept in their ranges as OpenSim's assembler
    clamps them; with the frame `before` given, each joint is held lightly to it (FIT_STEADY), so a direction the
    targets leave free (the shoulder's plane of elevation with the arm hanging, MoBL-ARMS' gimbal) does not wander
    frame to frame; with `feet` given, their points held on and out of the `ground` (`on_ground`, FIT_GROUND), the
    pelvis' place kept; with `stood` (the frame before: its qpos and planted bodies) given too, a body planted in both
    rolls without slipping (`unslipped`)."""
    data = mujoco.MjData(model)
    if stood is not None:
        before_data = mujoco.MjData(model)
        before_data.qpos[:] = stood[0]
        mujoco.mj_kinematics(model, before_data)
    rotation, translation = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    qpos = couplings.apply(qpos.copy())
    joints = couplings.leads[6:]
    addresses = model.jnt_qposadr[model.dof_jntid[joints]]
    steady = np.zeros((len(joints), len(couplings.leads)))
    steady[np.arange(len(joints)), 6 + np.arange(len(joints))] = FIT_STEADY
    for _ in range(rounds):
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        mujoco.mj_comPos(model, data)
        rows, errors = [], []
        for body, target in targets.items():
            mujoco.mj_jacBody(model, data, None, rotation, body)
            rows.append(rotation.copy())
            errors.append((Rotation.from_matrix(target) * Rotation.from_matrix(
                data.xmat[body].reshape(3, 3)).inv()).as_rotvec())
        for point, body, rise in (on_ground(model, data, ground, feet, planted) if feet else ()):
            mujoco.mj_jac(model, data, translation, None, point, body)
            rows.append(FIT_GROUND * translation[2:3])
            errors.append([FIT_GROUND * rise])
        for point, body, slip in (unslipped(model, data, before_data, ground, feet, planted & stood[1])
                                  if feet and stood is not None else ()):
            mujoco.mj_jac(model, data, translation, None, point, body)
            rows.append(FIT_GROUND * translation[:2])
            errors.append(-FIT_GROUND * slip)
        mapped = couplings.map(qpos)
        jacobian = np.concatenate(rows) @ mapped
        if feet:  # the pelvis' place is SOMA's root path's: the legs bring the feet to the ground
            jacobian[:, :3] = 0.0
        if before is not None:
            jacobian = np.concatenate([jacobian, steady])
            errors.append(FIT_STEADY * (before[addresses] - qpos[addresses]))
        step = np.linalg.solve(jacobian.T @ jacobian + FIT_DAMPING * np.eye(jacobian.shape[1]),
                               jacobian.T @ np.concatenate(errors))
        mujoco.mj_integratePos(model, qpos, mapped @ step, 1.0)
        qpos = limited(model, qpos, couplings)
    return qpos


def _sensed(person, world, bodies, turns):
    """Each sensor's body turn in a frame of the clip ({body: 3 x 3}, MuJoCo's frame): its segment's turn and offset."""
    return {bodies[segment]: TO_OWN.T @ (world[person["segments"].index(segment)][:3, :3] @ turns[segment])
            for segment in sided(TARGETS)}


def motion(model, couplings, person, worlds, bodies, fixed, ground=None, feet=None, planted=None):
    """The fitted path (frames x nq): every TARGETS segment's turn followed (`_fitted`), then the root moved so the
    pelvis stands where SOMA's Hips carry it (its calibrated place in the Hips' frame), nothing else placed; with
    `feet` given, then fitted again with its feet on the ground (`on_ground`, `planted` frame by frame)."""
    turns, places = fixed
    hips = person["segments"].index("Hips")
    pelvis, path = bodies["Hips"], []
    data = default_pose(model, couplings)
    qpos = couplings.apply(model.qpos0.copy())
    root = model.jnt_bodyid[0]
    for frame, world in enumerate(worlds):
        wanted = _sensed(person, world, bodies, turns)
        if frame == 0:  # the root turned so the pelvis turns as wanted
            rest = data.xmat[root].reshape(3, 3).T @ data.xmat[pelvis].reshape(3, 3)
            qpos[3:7] = Rotation.from_matrix(wanted[pelvis] @ rest.T).as_quat(scalar_first=True)
        qpos = _fitted(model, couplings, wanted, qpos, FIT_FIRST if frame == 0 else FIT_NEXT,
                       None if frame == 0 else qpos)
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        qpos[:3] += TO_OWN.T @ (world[hips] @ [*places["Hips"], 1.0])[:3] - data.xpos[pelvis]
        if feet:
            qpos = _fitted(model, couplings, wanted, qpos, FIT_NEXT, qpos, ground, feet, planted[frame],
                           (path[-1], planted[frame - 1]) if frame else None)
        path.append(qpos.copy())
    return np.array(path)


def refitted(model, path, worlds, segments, bodies, fixed):
    """The sensor offsets fitted again over the whole clip (the owner's change to OpenSense, 2026-10-28: one odd
    calibration frame cannot skew them): each segment's turn to its body the mean (chordal least squares,
    Rotation.mean) of its turn to its fitted body over every frame of `path`; its place kept where its body sees it."""
    data, turns, places = mujoco.MjData(model), {}, {}
    seen = {segment: [] for segment in bodies}
    for qpos, world in zip(path, worlds):
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        for number, segment in enumerate(segments):
            if segment in bodies:
                seen[segment].append(world[number][:3, :3].T @ own_pose(model, data, bodies[segment])[:3, :3])
    for segment, found in seen.items():
        turns[segment] = Rotation.from_matrix(np.array(found)).mean().as_matrix()
        places[segment] = turns[segment] @ fixed[0][segment].T @ fixed[1][segment]
    return turns, places


def landed(model, couplings, path, ground, feet, planted, sensed):
    """The low-passed path with its feet put back on the ground (`on_ground`), frame by frame, every sensed body held
    to its turn and every joint to its angle there, the pelvis where it stands: the low-pass moves a held foot by
    millimetres to centimetres at a fast toe-off, and the ground is the last word on where a foot stands."""
    data, found = mujoco.MjData(model), []
    for frame, (qpos, held) in enumerate(zip(path, planted)):
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        turns = {body: data.xmat[body].reshape(3, 3).copy() for body in sensed}
        found.append(_fitted(model, couplings, turns, qpos, FIT_NEXT, qpos, ground, feet, held,
                             (found[-1], planted[frame - 1]) if frame else None))
    return np.array(found)
