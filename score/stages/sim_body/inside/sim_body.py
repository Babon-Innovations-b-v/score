"""Runs in Newton's own Python (score/stages/physics/inside/newton_env.sh: Newton with its MuJoCo solver, pinned): every
character's sim body of one scene, each MyoFullBody sized to the person (myo.py), on its own copy of the scene's ground
(#65).

    <env>/bin/python score/stages/sim_body/inside/sim_body.py <job.json> <out.json>

job.json (written by score/stages/sim_body): {"rate", "gravity", "model" (the fetched model's folder), "residual"
({"force", "moment"}: the limits' shares of the weight, and of it times the centre's height), "adjust" ({"move most
m", "turn most deg", "follows deg"}: RRA's caps), "people":
[{"name", "kg", "height" (the person's own standing height, m), "rig" ({"names", "parents", "bind"}: the person's rig),
"segments" ([SOMA segment name], in the order of `targets`), "standing" (each segment's frame in the rig's
standing clip's first frame, or null), "targets" (an .npz whose `world` is frames x segments x
4 x 4: each segment's frame in the clip, and `ground` n x 3 x 3: the scene's triangles it may touch, both in the
person's own frame, Y up)}]}.

The movement is the clip's (the owner, 2026-10-27: "we have kimodo for the actual movement; and myobody plus mujoco and
newton for the physics"): the body, root included, follows it exactly, and the physics is what that movement asks.
- Rotations to joint angles as OpenSim's OpenSense does with IMUs (Al Borno, O'Day, Ibarra, Dunne, Seth, Habib, Ong,
  Hicks, Uhlrich and Delp 2022, "OpenSense: an open-source toolbox for inertial-measurement-unit-based measurement of
  lower extremity kinematics over long durations", J NeuroEng Rehabil 19:22, doi:10.1186/s12984-022-01001-x;
  opensim-core's IMUPlacer and IMUInverseKinematicsTool, Apache-2.0): each SOMA segment's world turn is a virtual
  orientation sensor on the MyoFullBody body it rides (TARGETS); each sensor's fixed offset to its body is calibrated
  on the person's standing frame as the model's default pose, its heading corrected (`offsets`), then fitted again
  over the whole clip (`refitted`, the owner's change: one least squares over every frame, jointly with the fit, so
  one odd frame cannot skew them); per frame the model's own joint angles minimise the sensors' squared error angles
  (`fitted`, Simbody's OrientationSensors goal), in its own coordinates: a joint MuJoCo couples to another (the knee's
  slides and turns, the patella, the lumbar levels, the shoulder rhythm) follows its leader by the model's own
  polynomial, never fitted apart. Newton's eval_ik and IKSolver (#59) do not keep MuJoCo's joint couplings, so they are
  not used here. The pelvis stands where SOMA's root path carries it (its place in the Hips' frame calibrated with the
  model's hip joints on SOMA's); nothing else is placed by position. A foot standing on the ground in the clip
  (`stances`: its SOMA joint low and still, Kovar et al. 2002) has its lowest point held on the ground and no foot
  point goes into it (`on_ground`), by the legs' joints alone. What MyoFullBody cannot do follows as near as its joints
  allow (LACKS).
- The fitted path low-passed at CUTOFF (Winter's 6 Hz, zero lag), its feet put back on the ground and low-passed again
  LAND_ROUNDS times, then put back last (`landed`), before it is differentiated; velocities and accelerations its
  central differences.
- The whole path is moved up or down once, so the body's lowest point stands on its ground at the median frame
  (`grounded`).
- OpenSim's residual reduction (RRA: Delp et al. 2007, doi:10.1109/TBME.2007.901024; opensim-core's RRATool,
  Apache-2.0), in our own stack (`reduced`): RRA_ROUNDS times, the body's mass changed by the mean upward residual and
  the torso's centre of mass moved under the mean residual moment (RRATool::adjustCOMToReduceResiduals), then the
  pelvis' and trunk's path moved so the ground's pushes explain the movement, each frame's move capped, the feet kept
  where they stood by the legs (`footed`); the result kept within the clip's `follows` limit (`within_follows`). Nothing is applied to the body; how far
  it moved is the body's `adjusted` record.
- The physics, frame by frame, on the MuJoCo model Newton builds (SolverMuJoCo on MuJoCo's CPU backend; nothing is
  stepped): the generalised forces the movement needs (inverse dynamics, armature and passive forces in), the ground's
  contacts (each collider's surface point within GAP of the drawn triangle under it or into it, along the triangle's
  normal: a friction pyramid, FRICTION, under SLIDE_MOST, else sliding, its friction against its slip), and one
  bounded least squares (`shared`) that gives the forces to the ground, to a joint at an end of its range (`stops`)
  and to the muscles (activations 0 to 1 on each muscle's force-length-velocity, its passive force in), least squared
  activation first, the pelvis' six balance rows BALANCE times dearer than a joint's; what they cannot give is left
  over: the residual on the pelvis (force and moment, OpenSim's residual actuators) and each joint's reserve. Neither
  is applied to anything: they are measures of how physically possible the movement is.

out.json: {"engine", "rate", "people": {name: {"model" (the person's model record), "muscles" ([name]), "joints" ([name]
of each driven dof), "com height" (m, frame 0, over its ground), "shift" (m, the path's one move up), "frames":
[{"angles": [[x, y, z] degrees, rotation vector, per SOMA segment but the first, against its parent, as the body's
segment riding its bone turns], "targets": [...the clip's...], "torques": [N m per joint], "ground": [x, y, z] N
(the ground's push), "lowest": m (the lowest collider
point's height over the ground, null off it), "feet": {segment: [its lowest collider point's height over the ground
(null off it), the ground's upward push on it N]} (FEET), "residual": [force xyz N, moment xyz N m], "reserve": N m
(the largest joint reserve), "activations": [0..1 per muscle], "forces": [N per muscle, tension], "poses": [[x, y, z,
qx, qy, qz, qw] per SOMA segment: the clip's own moved as RRA moved the body it rides, which the skin plays]}],
"adjusted": RRA's moves (`adjustment_record`)}}}, everything in the person's own frame (Y
up); and beside it <out>.npz, per person: `<name>/bones` (each body's pose every frame, frames x bodies x 7),
`<name>/segments` (each SOMA segment riding its bone every frame, frames x segments x 7: at the bind's correspondence,
`offsets`), `<name>/paths` (every muscle's path points, all frames end to end), `<name>/counts` (frames x muscles: each
path's point count) and `<name>/mesh/<body>/points|faces` (each bone in its body's frame)."""
import json
import pathlib
import sys

import mujoco
import newton
import numpy as np
from scipy.ndimage import minimum_filter1d
from scipy.optimize import lsq_linear
from scipy.signal import butter, filtfilt
from scipy.spatial.transform import Rotation

import myo

DEVICE = "cpu"  # MuJoCo's CPU backend: bit for bit, and MuJoCo Warp's deterministic mode breaks over 60 dofs (#60)
# MuJoCo's frame (Z up, the model's own: facing -y, left +x) into the person's (Y up, facing +z).
TO_OWN = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.0, -1.0, 0.0]])
# Free height over a surface for a body to stand on it (metres): under less (a table top, a shelf) it is a block.
HEADROOM = 1.0
FEET = ("Foot", "ToeBase")
# Each SOMA segment and the MyoFullBody body it rides ({side} its side's letter); the first carries the pelvis.
RIDES = {"Hips": "pelvis", "Spine1": "lumbar4", "Spine2": "lumbar2", "Chest": "torso", "Neck1": "head",
         "Neck2": "head", "Head": "head", "{Side}Shoulder": "clavicle_{side}", "{Side}Arm": "humerus_{side}",
         "{Side}ForeArm": "ulna_{side}", "{Side}Hand": "lunate_{side}", "{Side}Leg": "femur_{side}",
         "{Side}Shin": "tibia_{side}", "{Side}Foot": "calcn_{side}", "{Side}ToeBase": "toes_{side}"}
# The segments the fit follows, each a virtual orientation sensor on the body it rides (OpenSense's IMUs, weight 1
# each); the rest ride their bodies: MyoFullBody has no joint of its own for them.
TARGETS = ("Hips", "Chest", "{Side}Arm", "{Side}ForeArm", "{Side}Hand", "{Side}Leg", "{Side}Shin", "{Side}Foot",
           "{Side}ToeBase")
LACKS = {"Spine1, Spine2": "one lumbar joint spread over its five levels by the model's couplings",
         "Neck1, Neck2, Head": "MyoFullBody's head and neck are rigid on its thorax",
         "{Side}Shoulder": "the clavicle and scapula follow the arm's elevation (the model's shoulder rhythm)",
         "{Side}Shin, {Side}Foot, {Side}ToeBase": "the knee, ankle, subtalar and toe joints are hinges"}
# The hip joints, whose middle places the pelvis on SOMA's at calibration: each SOMA leg segment and its femur.
HIPS = {"LeftLeg": "femur_l", "RightLeg": "femur_r"}
FIT_DAMPING = 1e-3
# The fit's weight of a radian (or metre) a joint moves from the frame before: 0.05 left the hanging arm's plane of
# elevation (MoBL-ARMS' gimbal) swinging up to 10,000 deg/s2, about 130 N m of the pelvis' residual (2026-10-28).
FIT_STEADY = 0.2
# A foot segment (FEET) stands on its ground in a frame when its SOMA joint moves slower than STILL and stands within
# LOW of its calibration height over its ground (Kovar, Schreiner and Gleicher 2002, "Footskate cleanup for motion
# capture editing": contacts found by the joint's height and speed, then held by the fit); the fit then holds the
# lowest point of its body on the ground and keeps every foot point out of it, FIT_GROUND its weight per metre.
STILL = 0.5  # m/s
LOW = 0.02  # metres
FIT_GROUND = 100.0
LAND_ROUNDS = 2  # the path landed and low-passed again before it is landed last
OFFSET_ROUNDS = 3  # the offsets fitted again over the clip, each round with the path fitted on the last
FIT_FIRST, FIT_NEXT = 400, 40  # fit iterations at the first frame, then each next one from the last
CUTOFF = 6.0  # Hz (Winter, Biomechanics and Motor Control of Human Movement, 4th ed., 2009: 6 Hz for gait)
# The ground pushes only a foot point touching it: within GAP of its drawn triangle or into it (MuJoCo's contact: a
# geom meets the ground within its margin, MyoFullBody's foot colliders' 1 mm, and rests 0.1 to 0.4 mm into it under
# the body's weight with MuJoCo's default solref and solimp, as MyoSuite, MuscleMimic and KINESIS leave them).
GAP = 0.005  # metres
SLIDE_MOST = 1.2  # m/s
FRICTION = 0.5
CONTACT_COST = 1e-3  # the solve's weight of a newton of contact force (or N m of a joint's stop) against an activation
# The solve's weight of the pelvis' residual (a newton or N m) against a joint's reserve (N m): the ground must balance
# the whole body first, so a movement it cannot carry shows as residual, and one the muscles cannot make as reserves.
BALANCE = 100.0
AT_STOP = 1e-4  # radians or metres: a joint this near an end of its range stands against it
SOLVE_ROUNDS = 1000
SOLVE_TOLERANCE = 1e-9  # the solve's projected gradient against its largest linear term
BONE_CELL = 0.005  # metres: the drawn bones' vertices merged within this
# The residual reduction (OpenSim's RRA, `reduced`): its rounds (RRA is run again on its own output), the lumbar
# leaders it moves with the pelvis (the owner's: "adjust the pelvis and trunk path slightly"), the weight of a move the
# size of its cap against a residual the size of its limit (RRA's tracking), RRATool's 0.1 m limit on the torso's
# centre of mass, and the central differences' step (m, rad).
RRA_ROUNDS = 3
TRUNK = ("flex_extension", "lat_bending", "axial_rotation")
TRACK = 0.01
COM_MOST = 0.1
RRA_STEP = 1e-5
RRA_HALVINGS = 3
FRAME_ROUNDS = 20  # `within_frames`' rounds of lowering the frames over their cap
FRAME_MARGIN = 0.95  # a frame over its cap lowered this much further than its excess, so the rounds end
FOOTED_HEIGHT = 0.1  # the weight of a metre of the pelvis' height against one of a foot's place (`footed`)


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


# --- the ground (the person's own frame, Y up) --------------------------------------------------------------------

def crossings(points, ground):
    """Where the triangles cross the upright line through each point (x, z): its point indices, heights and
    triangles."""
    corner, edge1, edge2 = ground[:, 0], ground[:, 1] - ground[:, 0], ground[:, 2] - ground[:, 0]
    det = edge1[:, 0] * edge2[:, 2] - edge1[:, 2] * edge2[:, 0]
    flat = np.abs(det) > 1e-12  # an upright triangle crosses no upright line
    corner, edge1, edge2, det = corner[flat], edge1[flat], edge2[flat], det[flat]
    triangles = np.flatnonzero(flat)
    low, high = ground[flat][:, :, [0, 2]].min(axis=1), ground[flat][:, :, [0, 2]].max(axis=1)
    order = np.argsort(points[:, 0])
    firsts = np.searchsorted(points[order, 0], low[:, 0], side="left")
    lasts = np.searchsorted(points[order, 0], high[:, 0], side="right")
    found_points, found_heights, found_triangles = [], [], []
    for index in range(len(corner)):
        mine = order[firsts[index]:lasts[index]]
        mine = mine[(points[mine, 2] >= low[index, 1]) & (points[mine, 2] <= high[index, 1])]
        dx, dz = points[mine, 0] - corner[index, 0], points[mine, 2] - corner[index, 2]
        one = (dx * edge2[index, 2] - dz * edge2[index, 0]) / det[index]
        two = (edge1[index, 0] * dz - edge1[index, 2] * dx) / det[index]
        inside = (one >= 0) & (two >= 0) & (one + two <= 1)
        found_points.append(mine[inside])
        found_heights.append(corner[index, 1] + one[inside] * edge1[index, 1] + two[inside] * edge2[index, 1])
        found_triangles.append(np.full(inside.sum(), triangles[index]))
    return np.concatenate(found_points), np.concatenate(found_heights), np.concatenate(found_triangles)


def standing(points, ground):
    """Each point's ground: the lowest crossing with HEADROOM free over it, its height and its triangle (nan and -1
    where none is)."""
    which, heights, triangles = crossings(points, ground)
    order = np.lexsort((heights, which))
    which, heights, triangles = which[order], heights[order], triangles[order]
    above = np.append(heights[1:], np.inf)
    above[np.append(which[1:] != which[:-1], True)] = np.inf  # the top crossing of each point has nothing over it
    free = above - heights >= HEADROOM
    found, under = np.full(len(points), np.nan), np.full(len(points), -1)
    which, heights, triangles = which[free], heights[free], triangles[free]
    first = np.unique(which, return_index=True)[1]  # the lowest standing crossing of each point
    found[which[first]], under[which[first]] = heights[first], triangles[first]
    return found, under


def heights_over(points, ground):
    """Each point's height over its ground; nan where it has none."""
    return points[:, 1] - standing(points, ground)[0]


def normals(ground):
    """Each triangle's upward unit normal."""
    found = np.cross(ground[:, 1] - ground[:, 0], ground[:, 2] - ground[:, 0])
    found *= np.sign(found[:, 1:2]) + (found[:, 1:2] == 0)
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


# --- the model ------------------------------------------------------------------------------------------------------

def sided(names):
    """Each {Side}/{side} name made for both sides, other names as they are."""
    found = []
    for name in names:
        found += [name.format(Side=side, side=side[0].lower()) for side in ("Left", "Right")] if "{" in name else [name]
    return found


def sided_map(table):
    return {key.format(Side=side, side=side[0].lower()): (value.format(Side=side, side=side[0].lower())
                                                          if isinstance(value, str) else
                                                          tuple(part.format(Side=side, side=side[0].lower())
                                                                for part in value))
            for key, value in table.items() for side in (("Left", "Right") if "{" in key else ("Left",))}


def short_names(model, kind, count):
    """Each object's own name in a model Newton built (its label's last part)."""
    found = []
    for index in range(count):
        name = mujoco.mj_id2name(model, kind, index) or ""
        found.append(name)
    return found


def body_index(model, name):
    """A body of the model Newton built, by the MyoFullBody body's own name (Newton names it by its path)."""
    names = short_names(model, mujoco.mjtObj.mjOBJ_BODY, model.nbody)
    found = [index for index, full in enumerate(names) if full == name or full.endswith("_" + name)]
    if len(found) != 1:
        raise ValueError(f"no single body {name} in the model Newton built: {len(found)} found")
    return found[0]


def built(path, gravity):
    """MuJoCo's model of the person's body as Newton builds it (SolverMuJoCo, MuJoCo's CPU backend): no drives,
    nothing stepped."""
    builder = newton.ModelBuilder(up_axis=newton.Axis.Z, gravity=(0.0, 0.0, -gravity))
    newton.solvers.SolverMuJoCo.register_custom_attributes(builder)
    # Bone meshes are drawn from MuJoCo's own model of the file; Newton is given the colliders, wraps and joints.
    builder.add_mjcf(str(path), convert_mjc_equality_constraints=False, parse_meshes=False)
    return newton.solvers.SolverMuJoCo(builder.finalize(device=DEVICE), use_mujoco_cpu=True,
                                       use_mujoco_contacts=False, integrator="euler").mj_model


class Couplings:
    """MuJoCo's joint couplings of a model: which dofs lead, and each follower's polynomial in its leader."""

    def __init__(self, model):
        self.model = model
        self.followers = []  # (follower joint, leader joint or -1, polynomial)
        for equality in range(model.neq):
            if model.eq_type[equality] == mujoco.mjtEq.mjEQ_JOINT and model.eq_active0[equality]:
                poly = model.eq_data[equality, :5].copy()
                # a lock (no leader) reaches Newton's model with the last joint as its leader (#60's import bug B)
                leader = int(model.eq_obj2id[equality]) if poly[1:].any() else -1
                self.followers.append((int(model.eq_obj1id[equality]), leader, poly))
        following = {model.jnt_dofadr[joint] for joint, _, _ in self.followers}
        self.leads = np.array([dof for dof in range(model.nv) if dof not in following])

    def apply(self, qpos):
        """`qpos` with every follower set from its leader."""
        model = self.model
        for joint, leader, poly in self.followers:
            at = model.jnt_qposadr[joint]
            moved = qpos[model.jnt_qposadr[leader]] - model.qpos0[model.jnt_qposadr[leader]] if leader >= 0 else 0.0
            qpos[at] = model.qpos0[at] + sum(poly[power] * moved ** power for power in range(5))
        return qpos

    def map(self, qpos):
        """d(every dof) / d(leading dof) at `qpos` (nv x leads)."""
        model = self.model
        found = np.zeros((model.nv, len(self.leads)))
        found[self.leads, np.arange(len(self.leads))] = 1.0
        column = {dof: index for index, dof in enumerate(self.leads)}
        for joint, leader, poly in self.followers:
            if leader < 0:
                continue
            moved = qpos[model.jnt_qposadr[leader]] - model.qpos0[model.jnt_qposadr[leader]]
            found[model.jnt_dofadr[joint], column[model.jnt_dofadr[leader]]] = sum(
                power * poly[power] * moved ** (power - 1) for power in range(1, 5))
        return found


def limited(model, qpos, couplings):
    """`qpos` with every limited hinge or slide inside its range, its followers set again."""
    for joint in range(model.njnt):
        if model.jnt_limited[joint] and model.jnt_type[joint] in (mujoco.mjtJoint.mjJNT_HINGE,
                                                                   mujoco.mjtJoint.mjJNT_SLIDE):
            at = model.jnt_qposadr[joint]
            qpos[at] = np.clip(qpos[at], *model.jnt_range[joint])
    return couplings.apply(qpos)


# --- the fit ----------------------------------------------------------------------------------------------------------

def own_pose(model, data, body):
    """A body's frame in the person's frame (4 x 4)."""
    found = np.eye(4)
    found[:3, :3] = TO_OWN @ data.xmat[body].reshape(3, 3)
    found[:3, 3] = TO_OWN @ data.xpos[body]
    return found


def default_pose(model, couplings):
    """The model's default pose (MuJoCo's frame), its couplings applied: MyoSuite's own `stand` keyframe."""
    data = mujoco.MjData(model)
    data.qpos[:] = couplings.apply(model.qpos0.copy())
    mujoco.mj_kinematics(model, data)
    return data


def calibration(person, segments):
    """The frame the sensors are calibrated on (segments x 4 x 4, the person's frame): the rig's standing clip's first
    frame, else SOMA's bind."""
    if person.get("standing") is not None:
        return np.asarray(person["standing"], dtype=float)
    names = [str(name) for name in person["rig"]["names"]]
    bind = np.asarray(person["rig"]["bind"], dtype=float)
    return np.array([bind[names.index(segment)] for segment in segments])


def heading(model, data, frame, index):
    """OpenSense's heading correction (OpenSenseUtilities::computeHeadingCorrection): the turn about up (3 x 3, the
    person's frame) that faces the calibration frame as the model's default pose faces, read off the hip joints' line
    (left to right) of each."""
    theirs = frame[index["RightLeg"]][:3, 3] - frame[index["LeftLeg"]][:3, 3]
    mine = TO_OWN @ (data.xpos[body_index(model, HIPS["RightLeg"])] - data.xpos[body_index(model, HIPS["LeftLeg"])])
    angle = np.arctan2(theirs[0], theirs[2]) - np.arctan2(mine[0], mine[2])
    return Rotation.from_rotvec([0.0, -angle, 0.0]).as_matrix()


def offsets(model, couplings, person, segments, bodies):
    """OpenSense's IMUPlacer: each segment a sensor on the body it rides, calibrated once on the person's standing
    frame (`calibration`) as the model's default pose, its heading corrected (`heading`): each segment's fixed turn to
    its body ({segment: 3 x 3}, R_FB of IMUPlacer.cpp, transposed) and its body's place in the segment's frame
    ({segment: 3}), the model's hip joints' middle on SOMA's."""
    data = default_pose(model, couplings)
    frame = calibration(person, segments)
    index = {segment: number for number, segment in enumerate(segments)}
    turn = heading(model, data, frame, index)
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


def fitted(model, couplings, targets, qpos, rounds, before=None, ground=None, feet=(), planted=()):
    """The model's qpos whose bodies turn as `targets` ({body: 3 x 3, MuJoCo's frame}): OpenSense's inverse
    kinematics (Simbody's OrientationSensors goal, every sensor's error angle squared, weight 1 each), by damped least
    squares on the leading dofs, `rounds` steps from `qpos`, the joints kept in their ranges as OpenSim's assembler
    clamps them; with the frame `before` given, each joint is held lightly to it (FIT_STEADY), so a direction the
    targets leave free (the shoulder's plane of elevation with the arm hanging, MoBL-ARMS' gimbal) does not wander
    frame to frame; with `feet` given, their points held on and out of the `ground` (`on_ground`, FIT_GROUND), the
    pelvis' place kept."""
    data = mujoco.MjData(model)
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


def on_ground(model, data, ground, feet, planted):
    """The foot points the fit holds now ([(point, its body, how far it must rise)], MuJoCo's frame): each planted
    body's lowest collider point onto the ground, and every point of `feet` ({body: geoms}) under the ground or within
    GAP over it out of it (one that is over it rises by 0 but stays in the fit, so the fit's next step cannot put it
    back in: the one-sided bound's active set)."""
    found = []
    for body, geoms in feet.items():
        points = surface(model, data, geoms)
        heights = heights_over(points @ TO_OWN.T, ground)
        if np.isnan(heights).all():
            continue
        rise = {point: max(-heights[point], 0.0) for point in np.flatnonzero(heights < GAP)}
        if body in planted:
            rise[int(np.nanargmin(heights))] = -heights[int(np.nanargmin(heights))]
        found += [(points[point], body, rise[point]) for point in sorted(rise)]
    return found


def stances(person, worlds, ground, rate):
    """The foot segments standing on the ground, frame by frame ([{segment}]): its SOMA joint slower than STILL and
    no more than LOW higher over its ground than it stands in the calibration frame over the rig's floor (Kovar et al.
    2002)."""
    segments = person["segments"]
    standing = calibration(person, segments)
    found = [set() for _ in worlds]
    for number, segment in enumerate(segments):
        if segment.endswith(FEET):
            places = worlds[:, number, :3, 3]
            speed = np.linalg.norm(np.gradient(places, 1.0 / rate, axis=0), axis=1)
            low = heights_over(places, ground) <= standing[number][1, 3] + LOW
            for frame in np.flatnonzero(low & (speed < STILL)):
                found[frame].add(segment)
    return found


def surface(model, data, geoms):
    """Points round each collider (MuJoCo's frame): its surface sampled in 26 directions (a capsule's at both ends)."""
    directions = np.array([[x, y, z] for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1) if x or y or z], float)
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    found = []
    for geom in geoms:
        size, kind = model.geom_size[geom], model.geom_type[geom]
        if kind == mujoco.mjtGeom.mjGEOM_CAPSULE:
            local = np.concatenate([directions * size[0] + [0, 0, size[1]], directions * size[0] - [0, 0, size[1]]])
        elif kind == mujoco.mjtGeom.mjGEOM_BOX:
            local = np.sign(directions) * size
        elif kind == mujoco.mjtGeom.mjGEOM_SPHERE:
            local = directions * size[0]
        else:  # an ellipsoid
            local = directions * size
        found.append(local @ data.geom_xmat[geom].reshape(3, 3).T + data.geom_xpos[geom])
    return np.concatenate(found)


def lowest_over(model, data, geoms, ground):
    """The lowest of `geoms`' collider points over the ground (metres); None when none is over any of it."""
    heights = heights_over(surface(model, data, geoms) @ TO_OWN.T, ground)
    return None if np.isnan(heights).all() else float(np.nanmin(heights))


def sensed(person, world, bodies, turns):
    """Each sensor's body turn in a frame of the clip ({body: 3 x 3}, MuJoCo's frame): its segment's turn and offset."""
    return {bodies[segment]: TO_OWN.T @ (world[person["segments"].index(segment)][:3, :3] @ turns[segment])
            for segment in sided(TARGETS)}


def motion(model, couplings, person, worlds, bodies, fixed, ground=None, feet=None, planted=None):
    """The fitted path (frames x nq): every TARGETS segment's turn followed (`fitted`), then the root moved so the
    pelvis stands where SOMA's Hips carry it (its calibrated place in the Hips' frame), nothing else placed; with
    `feet` given, then fitted again with its feet on the ground (`on_ground`, `planted` frame by frame)."""
    turns, places = fixed
    hips = person["segments"].index("Hips")
    pelvis, path = bodies["Hips"], []
    data = default_pose(model, couplings)
    qpos = couplings.apply(model.qpos0.copy())
    root = model.jnt_bodyid[0]
    for frame, world in enumerate(worlds):
        wanted = sensed(person, world, bodies, turns)
        if frame == 0:  # the root turned so the pelvis turns as wanted
            rest = data.xmat[root].reshape(3, 3).T @ data.xmat[pelvis].reshape(3, 3)
            qpos[3:7] = Rotation.from_matrix(wanted[pelvis] @ rest.T).as_quat(scalar_first=True)
        qpos = fitted(model, couplings, wanted, qpos, FIT_FIRST if frame == 0 else FIT_NEXT,
                      None if frame == 0 else qpos)
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        qpos[:3] += TO_OWN.T @ (world[hips] @ [*places["Hips"], 1.0])[:3] - data.xpos[pelvis]
        if feet:
            qpos = fitted(model, couplings, wanted, qpos, FIT_NEXT, qpos, ground, feet, planted[frame])
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
    for qpos, held in zip(path, planted):
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        turns = {body: data.xmat[body].reshape(3, 3).copy() for body in sensed}
        found.append(fitted(model, couplings, turns, qpos, FIT_NEXT, qpos, ground, feet, held))
    return np.array(found)


def footed(model, couplings, path, before, feet):
    """`path` with each foot body (`feet`) put back where it stands in `before`, place and turn, frame by frame, by the
    legs' joints (damped least squares, FIT_NEXT steps): a move of the pelvis or trunk leaves the feet, and so the
    ground's contacts, as they were. The pelvis' height is in the solve, held to its own by FOOTED_HEIGHT: a pelvis
    raised past what a straight leg reaches comes down, or its feet would leave the ground (1 cm up lifted them 9 mm,
    600 N of residual, 2026-10-28)."""
    data, found = mujoco.MjData(model), []
    ancestors = set()
    for body in feet:
        while body > 0:
            ancestors.add(body)
            body = model.body_parentid[body]
    legs = [2] + [column for column, dof in enumerate(couplings.leads)
                  if column >= 6 and model.dof_bodyid[dof] in ancestors]
    height = np.zeros(len(legs))
    height[0] = FOOTED_HEIGHT
    places, turns = np.zeros((3, model.nv)), np.zeros((3, model.nv))
    for qpos, still in zip(path, before):
        data.qpos[:] = still
        mujoco.mj_kinematics(model, data)
        wanted = {body: (data.xpos[body].copy(), data.xmat[body].reshape(3, 3).copy()) for body in feet}
        qpos, asked = qpos.copy(), qpos[2]
        for _ in range(FIT_NEXT):
            data.qpos[:] = qpos
            mujoco.mj_kinematics(model, data)
            mujoco.mj_comPos(model, data)
            rows, errors = [], []
            for body, (place, turn) in wanted.items():
                mujoco.mj_jacBody(model, data, places, turns, body)
                rows += [places.copy(), turns.copy()]
                errors += [place - data.xpos[body], (Rotation.from_matrix(turn) * Rotation.from_matrix(
                    data.xmat[body].reshape(3, 3)).inv()).as_rotvec()]
            mapped = couplings.map(qpos)[:, legs]
            jacobian = np.concatenate([np.concatenate(rows) @ mapped, height[None]])
            errors.append([FOOTED_HEIGHT * (asked - qpos[2])])
            step = np.linalg.solve(jacobian.T @ jacobian + FIT_DAMPING * np.eye(len(legs)),
                                   jacobian.T @ np.concatenate(errors))
            mujoco.mj_integratePos(model, qpos, mapped @ step, 1.0)
            qpos = limited(model, qpos, couplings)
        found.append(qpos)
    return np.array(found)


def grounded(model, path, colliders, ground, name):
    """The path moved once up or down so its lowest collider point stands on its ground at the median frame, and that
    move (m). A walk always has a foot on its ground, so each frame's lowest point should be on it; the median frame's
    is (the frame 0 rule left the Kimodo walker's feet standing 2 to 3 cm over it once its legs followed the clip, and
    MuscleMimic's lowest over all frames lifted it 2.3 cm, with frames carried by nothing, 2026-10-27)."""
    data, lowest = mujoco.MjData(model), []
    for qpos in path:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        lowest.append(lowest_over(model, data, colliders, ground))
    lowest = [over for over in lowest if over is not None]
    if not lowest:
        raise SystemExit(f"{name}: no ground under its body in any frame")
    over = float(np.median(lowest))
    moved = path.copy()
    moved[:, 2] -= over  # MuJoCo's up
    return moved, -over


def filtered(model, couplings, path, rate):
    """The path low-passed at CUTOFF before anything is differentiated (biomechanics' order: Winter 2009): every
    leading coordinate but the root's turn through a 2nd-order Butterworth run forward and back (zero lag, 4th order),
    the root's quaternion likewise, its sign kept continuous and its length one; the followers set again."""
    low, high = butter(2, CUTOFF / (rate / 2))
    if len(path) <= 3 * max(len(low), len(high)):
        return path.copy()
    found = path.copy()
    turn = found[:, 3:7]
    for frame in range(1, len(turn)):  # q and -q are one turn: keep each next to the one before
        if turn[frame] @ turn[frame - 1] < 0:
            turn[frame] *= -1
    leads = [model.jnt_qposadr[model.dof_jntid[dof]] for dof in couplings.leads[6:]]
    found[:, [0, 1, 2, *leads]] = filtfilt(low, high, found[:, [0, 1, 2, *leads]], axis=0)
    found[:, 3:7] = filtfilt(low, high, turn, axis=0)
    found[:, 3:7] /= np.linalg.norm(found[:, 3:7], axis=1, keepdims=True)
    return np.array([couplings.apply(qpos) for qpos in found])


def rates(model, path, rate):
    """The path's velocities and accelerations (frames x nv each): central differences of the filtered path."""
    count = len(path)
    velocities = np.zeros((count, model.nv))
    for frame in range(count):
        before, after = path[max(frame - 1, 0)], path[min(frame + 1, count - 1)]
        span = (min(frame + 1, count - 1) - max(frame - 1, 0)) / rate
        if span:
            mujoco.mj_differentiatePos(model, velocities[frame], span, before, after)
    return velocities, np.gradient(velocities, 1.0 / rate, axis=0)


# --- the physics ------------------------------------------------------------------------------------------------------

class Physics:
    """One person's MuJoCo model as Newton built it, and the frame by frame share of its movement's forces."""

    def __init__(self, model, ground, colliders):
        self.model, self.data = model, mujoco.MjData(model)
        self.couplings = Couplings(model)
        self.ground, self.up = ground, normals(ground)
        self.colliders = colliders
        self.muscles = np.flatnonzero(model.actuator_dyntype == mujoco.mjtDyn.mjDYN_MUSCLE)

    def needed(self, qpos, qvel, qacc):
        """The state set, and the generalised forces the movement needs beyond the passive ones (nv)."""
        model, data = self.model, self.data
        data.qpos[:], data.qvel[:], data.qacc[:] = qpos, qvel, qacc
        mujoco.mj_fwdPosition(model, data)
        mujoco.mj_fwdVelocity(model, data)
        found = np.zeros(model.nv)
        mujoco.mj_rne(model, data, 1, found)
        return found + model.dof_armature * qacc - data.qfrc_passive

    def contacts(self):
        """The points the ground pushes ([(body, point's Jacobian, the directions it may push along)], MuJoCo's
        frame): the colliders' surface points (`surface`) within GAP of the drawn ground under them, or into it, each
        pushed along its triangle's normal with Coulomb's friction: a point slower than SLIDE_MOST sticks (a friction
        pyramid, FRICTION), a faster one slides (the normal and FRICTION of it against its slip)."""
        model, data = self.model, self.data
        found, along = [], np.zeros((3, model.nv))
        points = [surface(model, data, [geom]) for geom in self.colliders]
        owners = np.concatenate([np.full(len(mine), model.geom_bodyid[geom]) for geom, mine in
                                 zip(self.colliders, points)])
        points = np.concatenate(points)
        own = points @ TO_OWN.T
        heights, triangles = standing(own, self.ground)
        for point in np.flatnonzero(own[:, 1] - np.nan_to_num(heights, nan=np.inf) <= GAP):
            mujoco.mj_jac(model, data, along, None, points[point], owners[point])
            normal = TO_OWN.T @ self.up[triangles[point]]
            moving = along @ data.qvel
            slip = moving - (moving @ normal) * normal
            if np.linalg.norm(moving) > SLIDE_MOST and np.linalg.norm(slip) > 0:
                edges = [normal - FRICTION * slip / np.linalg.norm(slip)]
            else:
                first = np.cross(normal, [1.0, 0.0, 0.0] if abs(normal[0]) < 0.9 else [0.0, 1.0, 0.0])
                first /= np.linalg.norm(first)
                second = np.cross(normal, first)
                edges = [normal + FRICTION * first, normal - FRICTION * first, normal + FRICTION * second,
                         normal - FRICTION * second]
            found.append((owners[point], along.copy(), edges))
        return found

    def stops(self):
        """Each leading hinge or slide at an end of its range now, as a one-sided generalised force pushing it back
        in (nv x stops): MuJoCo's joint limit, the passive structures that hold a straight knee, say."""
        model, data = self.model, self.data
        found = []
        for dof in self.couplings.leads:
            joint = model.dof_jntid[dof]
            if not model.jnt_limited[joint] or model.jnt_type[joint] not in (mujoco.mjtJoint.mjJNT_HINGE,
                                                                              mujoco.mjtJoint.mjJNT_SLIDE):
                continue
            at, (low, high) = data.qpos[model.jnt_qposadr[joint]], model.jnt_range[joint]
            for sign, end in ((1.0, at <= low + AT_STOP), (-1.0, at >= high - AT_STOP)):
                if end:
                    column = np.zeros(model.nv)
                    column[dof] = sign
                    found.append(column)
        return np.array(found).T if found else np.zeros((model.nv, 0))

    def shared(self, needed):
        """The needed forces shared out: each contact's push (N, MuJoCo's frame, by body), each muscle's activation
        and force (N, tension), the residual on the pelvis (force N and moment N m, MuJoCo's frame) and each leading
        joint's reserve and net moment (N m)."""
        model, data = self.model, self.data
        mapped = self.couplings.map(data.qpos)
        moments = np.zeros((model.nu, model.nv))
        mujoco.mju_sparse2dense(moments, data.actuator_moment, data.moment_rownnz, data.moment_rowadr,
                                data.moment_colind)
        gains, biases = [], []
        for actuator in self.muscles:
            gains.append(mujoco.mju_muscleGain(data.actuator_length[actuator], data.actuator_velocity[actuator],
                                               model.actuator_lengthrange[actuator], model.actuator_acc0[actuator],
                                               model.actuator_gainprm[actuator, :9]))
            biases.append(mujoco.mju_muscleBias(data.actuator_length[actuator], model.actuator_lengthrange[actuator],
                                                model.actuator_acc0[actuator], model.actuator_biasprm[actuator, :9]))
        gains, biases = np.array(gains), np.array(biases)
        arms = moments[self.muscles].T  # nv x muscles
        contacts = self.contacts()
        columns = []
        for _, along, edges in contacts:
            columns += [along.T @ edge for edge in edges]
        pushes = np.array(columns).T if columns else np.zeros((model.nv, 0))
        stops = self.stops()
        wanted = mapped.T @ (needed - arms @ biases)
        system = mapped.T @ np.concatenate([pushes, stops, arms * gains], axis=1)
        count, held = pushes.shape[1], stops.shape[1]
        costs = np.concatenate([np.full(count + held, CONTACT_COST), np.ones(len(self.muscles))])
        rows = np.ones(len(wanted))
        rows[:6] = BALANCE  # the pelvis' six rows: the whole body's balance, kept before any joint's
        solved = least(system * rows[:, None], wanted * rows, costs, np.concatenate([np.full(count + held, np.inf),
                                                                                    np.ones(len(self.muscles))]))
        pushed, activations = solved[:count], solved[count + held:]
        left = wanted - system @ solved
        forces = np.zeros((model.nbody, 3))
        edges = [(body, edge) for body, _, mine in contacts for edge in mine]
        for (body, edge), weight in zip(edges, pushed):
            forces[body] += weight * edge
        root = data.xmat[model.jnt_bodyid[0]].reshape(3, 3)
        net = mapped.T @ (needed - pushes @ pushed)
        return {"pushes": forces, "activations": activations, "forces": -(gains * activations + biases),
                "residual": np.concatenate([left[:3], root @ left[3:6]]), "reserves": left[6:], "moments": net[6:]}


# --- the residual reduction (OpenSim's RRA) ---------------------------------------------------------------------------

def about(model, data, generalised, origin):
    """The pelvis' six rows of a generalised force as a world wrench (force, then moment about `origin`, MuJoCo's
    frame): the free joint's force is the world's, its moment the root body's about its own origin."""
    root = model.jnt_bodyid[0]
    force = generalised[:3]
    moment = data.xmat[root].reshape(3, 3) @ generalised[3:6] + np.cross(data.xpos[root] - origin, force)
    return np.concatenate([force, moment])


def balance(physics, qpos, qvel, qacc, origin):
    """The wrench the movement needs at the pelvis (about `origin`), the ground's pushes' wrenches (6 x pushes) and
    what the pushes cannot give of it: the pelvis' rows of `Physics.shared` alone (muscles and joint stops put no net
    force on the whole body), the same weights."""
    model, data = physics.model, physics.data
    needed = about(model, data, physics.needed(qpos, qvel, qacc), origin)
    columns = [about(model, data, along.T @ edge, origin) for _, along, edges in physics.contacts() for edge in edges]
    pushes = np.array(columns).T if columns else np.zeros((6, 0))
    pushed = least(BALANCE * pushes, BALANCE * needed, np.full(pushes.shape[1], CONTACT_COST),
                   np.full(pushes.shape[1], np.inf))
    return needed, needed - pushes @ pushed


def sensitivity(physics, qpos, qvel, qacc, origin, adjusted):
    """d(the needed wrench about `origin`) / d(each `adjusted` leading dof's place, speed and acceleration): three
    6 x adjusted matrices, by central differences of inverse dynamics."""
    model, couplings = physics.model, physics.couplings
    mapped = couplings.map(qpos)
    found = [np.zeros((6, len(adjusted))) for _ in range(3)]
    for column, lead in enumerate(adjusted):
        step = mapped[:, lead] * RRA_STEP
        for sign in (1.0, -1.0):
            placed = qpos.copy()
            mujoco.mj_integratePos(model, placed, sign * step, 1.0)
            for kind, state in enumerate(((couplings.apply(placed), qvel, qacc), (qpos, qvel + sign * step, qacc),
                                          (qpos, qvel, qacc + sign * step))):
                found[kind][:, column] += sign * about(model, physics.data, physics.needed(*state), origin) / (
                    2 * RRA_STEP)
    return found


def stencils(count, rate):
    """The path's speeds and accelerations as `rates` takes them, as matrices on a per-frame value (count x count)."""
    speeds = np.zeros((count, count))
    for frame in range(count):
        before, after = max(frame - 1, 0), min(frame + 1, count - 1)
        if after > before:
            speeds[frame, after] += rate / (after - before)
            speeds[frame, before] -= rate / (after - before)
    return speeds, np.gradient(speeds, 1.0 / rate, axis=0)


def adjusted_leads(physics):
    """The leading dofs RRA adjusts here (the owner's: the pelvis and the trunk): the root's six and the lumbar's
    leaders (TRUNK), as columns of the couplings' map."""
    model, leads = physics.model, physics.couplings.leads
    names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, model.dof_jntid[dof]) for dof in leads]
    trunk = [column for column, name in enumerate(names) if column >= 6 and name.endswith(TRUNK)]
    if len(trunk) != len(TRUNK):
        raise ValueError(f"the model's lumbar leaders {TRUNK} not found once each: {len(trunk)} found")
    return [0, 1, 2, 3, 4, 5, *trunk]


def moved(physics, path, adjustment, adjusted):
    """`path` with each frame's adjustment (frames x adjusted, the leading dofs' own units: metres, radians) added."""
    model, couplings = physics.model, physics.couplings
    found = []
    for qpos, change in zip(path, adjustment):
        leads = np.zeros(len(couplings.leads))
        leads[adjusted] = change
        qpos = qpos.copy()
        mujoco.mj_integratePos(model, qpos, couplings.map(qpos) @ leads, 1.0)
        found.append(limited(model, qpos, couplings))
    return np.array(found)


def reweighed(physics, path, residuals, home):
    """RRA's model step (opensim-core RRATool::adjustCOMToReduceResiduals): the whole body's mass changed by the mean
    upward residual over gravity, spread over the bodies by their masses (their inertias with them), and the torso's
    centre of mass moved under the mean horizontal residual moment, at most RRA's 0.1 m from where it was made (`home`)
    over every round; returns the share the mass changed by."""
    model, data = physics.model, physics.data
    gravity = -model.opt.gravity[2]
    share = -float(np.mean(residuals[:, 2])) / gravity / float(model.body_mass.sum())
    model.body_mass[:] *= 1 + share
    model.body_inertia[:] *= 1 + share
    torso = body_index(model, "torso")
    weight = model.body_mass[torso] * gravity
    rows, wanted = [], []
    for qpos, residual in zip(path, residuals):  # the torso's weight moved by d gives the pelvis (w d_y, -w d_x)
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        turn = data.xmat[torso].reshape(3, 3)
        rows += [weight * turn[1], -weight * turn[0]]
        wanted += [-residual[3], -residual[4]]
    shift = np.linalg.lstsq(np.array(rows), np.array(wanted), rcond=None)[0]
    model.body_ipos[torso] = home + np.clip(model.body_ipos[torso] + shift - home, -COM_MOST, COM_MOST)
    return share


def frame_states(physics, path, rate):
    """Each frame's speeds, accelerations (`rates`) and the pelvis' origin (MuJoCo's frame), the residuals' point."""
    model, data = physics.model, physics.data
    velocities, accelerations = rates(model, path, rate)
    origins = []
    for qpos in path:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        origins.append(data.xpos[model.jnt_bodyid[0]].copy())
    return list(zip(path, velocities, accelerations, origins))


def residuals(physics, states):
    """Each frame's residual after the ground's pushes alone (`balance`; frames x 6)."""
    return np.array([balance(physics, *state)[1] for state in states])


def smoothed(moves, rate):
    """A move low-passed as the path is (`filtered`: CUTOFF, zero lag), so it adds no shake to the movement."""
    low, high = butter(2, CUTOFF / (rate / 2))
    return filtfilt(low, high, moves, axis=0) if len(moves) > 3 * max(len(low), len(high)) else moves


def linearised(physics, states, adjusted, rate, scale):
    """The residuals' change with each frame's move of the `adjusted` dofs (6 frames x frames adjusted, over `scale`):
    each frame's sensitivity to its place, speed and acceleration, the speeds and accelerations `rates`' own
    differences of the places."""
    count, width = len(states), len(adjusted)
    speeds, accelerations = stencils(count, rate)
    system = np.zeros((6 * count, count * width))
    for frame, state in enumerate(states):
        places, speed, acceleration = sensitivity(physics, *state, adjusted)
        for other in range(max(frame - 2, 0), min(frame + 3, count)):
            block = speed * speeds[frame, other] + acceleration * accelerations[frame, other]
            system[6 * frame:6 * frame + 6, other * width:(other + 1) * width] = block + (places if other == frame
                                                                                           else 0.0)
    return system / scale[:, None]


def reduced(physics, path, rate, limits, most, land):
    """OpenSim's residual reduction (RRA: Delp et al. 2007, IEEE TBME 54(11):1940-50, doi:10.1109/TBME.2007.901024;
    opensim-core's RRATool, Apache-2.0) on the fitted path, in our own stack: RRA_ROUNDS times, the model step
    (`reweighed`) on the mean residual, then the pelvis' and trunk's path (`adjusted_leads`) moved so the ground
    explains the movement: one bounded linear least squares over every frame of the residual (force over `limits[0]`,
    moment over `limits[1]`) and the move (over its cap, TRACK its weight: RRA's tracking), each frame's change held
    within `most` (m, rad) of the fitted path, low-passed (`smoothed`), its feet kept where they stood by the legs
    (`land`: `footed`), and taken only when it lowers that cost as measured (halved up to RRA_HALVINGS times, else the
    rounds end). Nothing is applied to the body: only its path and masses change. Returns the path, the move (frames x
    adjusted) and the record."""
    model = physics.model
    adjusted = adjusted_leads(physics)
    count, width = len(path), len(adjusted)
    cap = np.tile([most[0]] * 3 + [most[1]] * (width - 3), count)
    scale = np.tile(np.concatenate([np.full(3, limits[0]), np.full(3, limits[1])]), count)
    track = np.sqrt(TRACK) / cap
    total, current, mass = np.zeros(count * width), path, 1.0
    home = model.body_ipos[body_index(model, "torso")].copy()

    def cost(moves, states):
        return float(np.sum((residuals(physics, states).reshape(-1) / scale) ** 2) + np.sum((track * moves) ** 2))

    for _ in range(RRA_ROUNDS):
        states = frame_states(physics, current, rate)
        mass *= 1 + reweighed(physics, current, residuals(physics, states), home)
        states = frame_states(physics, current, rate)
        left = residuals(physics, states).reshape(-1) / scale
        system = linearised(physics, states, adjusted, rate, scale)
        step = lsq_linear(np.concatenate([system, np.diag(track)]), np.concatenate([-left, -track * total]),
                          bounds=(-cap - total, cap - total)).x
        best = cost(total, states)
        for _ in range(RRA_HALVINGS + 1):
            trial = np.clip(smoothed((total + step).reshape(count, width), rate).reshape(-1), -cap, cap)
            walked = land(moved(physics, path, trial.reshape(count, width), adjusted))
            if cost(trial, frame_states(physics, walked, rate)) < best:
                total, current = trial, walked
                break
            step /= 2
        else:
            break
    return current, total.reshape(count, width), {"mass": mass - 1.0,
                                                   "torso": model.body_ipos[body_index(model, "torso")] - home}


def within_follows(physics, path, adjusted, moves, land, worlds, riders, follows):
    """The adjusted path kept within the clip's `follows` limit (the owner's cap: never further off the clip than the
    `follows` gate allows, degrees on the mean): the whole move, else the largest of its quarters that is, else none;
    and the share kept."""
    model = physics.model
    for share in (1.0, 0.75, 0.5, 0.25):
        found = adjusted if share == 1.0 else land(moved(physics, path, share * moves, adjusted_leads(physics)))
        if off_clip(model, found, worlds, *riders) <= follows:
            return found, share
    return path, 0.0


def within_frames(physics, path, moves, land, fitted, riders, most, rate):
    """The adjusted path held within `most` of the fitted path on every frame, all rounds together (owner, 2026-10-28:
    each segment's turn at most 5 degrees and the pelvis at most 2 cm off the fitted motion): each frame's share of the
    move (`moves`, frames x adjusted) lowered by how far it is over (`frame_excess`), the shares eroded and low-passed
    over a CUTOFF period so the move stays smooth, its feet kept (`land`), until no frame is over; the path and the
    shares."""
    adjusted, share = adjusted_leads(physics), np.ones(len(path))
    window = int(rate // CUTOFF) + 1
    for _ in range(FRAME_ROUNDS):
        found = land(moved(physics, path, share[:, None] * moves, adjusted))
        over = frame_excess(physics.model, path, found, fitted, riders, most)
        if over.max() <= 1.0:
            return found, share
        lowered = np.where(over > 1.0, share * FRAME_MARGIN / over, share)
        share = np.clip(np.minimum(lowered, smoothed(minimum_filter1d(lowered, window), rate)), 0.0, None)
    raise ValueError(f"the adjusted path is still {over.max():.2f} times its per-frame cap after {FRAME_ROUNDS} rounds")


def frame_excess(model, path, found, fitted, riders, most):
    """Each frame's largest move of `found` off the fitted `path` over its cap: its segments' turns (riding their bones,
    against `fitted`'s poses) over `most[1]` and the pelvis' place over `most[0]`, the larger."""
    turned = turned_off(fitted, posed_path(model, found, *riders[:3]))
    shift = np.linalg.norm(found[:, :3] - path[:, :3], axis=1)
    return np.maximum(turned.max(axis=1) / np.degrees(most[1]), shift / most[0])


def turned_off(before, after):
    """Each segment's turn between two posed paths (frames x segments x 4 x 4), degrees (frames x segments)."""
    return np.degrees(Rotation.from_matrix((np.swapaxes(after[..., :3, :3], -1, -2) @ before[..., :3, :3])
                                           .reshape(-1, 3, 3)).magnitude()).reshape(before.shape[:2])


def off_clip(model, path, worlds, segments, bodies, riding, parents):
    """The `follows` gate's measure on a path: the mean angle (degrees) between each segment's turn against its parent
    (riding its bone) and the clip's, over segments and frames."""
    found = []
    for posed, world in zip(posed_path(model, path, segments, bodies, riding), worlds):
        found += [np.degrees(Rotation.from_matrix((world[parent][:3, :3].T @ world[index][:3, :3])
                                                   @ (posed[index][:3, :3].T @ posed[parent][:3, :3])).magnitude())
                  for index, parent in enumerate(parents) if parent >= 0]
    return float(np.mean(found))


def posed_path(model, path, segments, bodies, riding):
    """Each SOMA segment riding its bone, every frame of a path (frames x segments x 4 x 4, the person's frame)."""
    data, found = mujoco.MjData(model), []
    for qpos in path:
        data.qpos[:] = qpos
        mujoco.mj_kinematics(model, data)
        found.append([own_pose(model, data, bodies[segment]) @ riding[segment] for segment in segments])
    return np.array(found)


def com_height(model, qpos, ground):
    """The centre of mass' height over its ground at a pose (m)."""
    data = mujoco.MjData(model)
    data.qpos[:] = qpos
    mujoco.mj_kinematics(model, data)
    mujoco.mj_comPos(model, data)
    return float(heights_over((data.subtree_com[model.jnt_bodyid[0]] @ TO_OWN.T)[None], ground)[0])


def adjustment_record(moved_by, kept, shares, step, before, after, segments, follows):
    """How far RRA moved the body (a quality measure, sim_bodies.json `adjusted`): the pelvis (cm) and its turn and
    each segment's turn (degrees) against the fitted path, median and largest over the frames, and the largest of any
    segment on any frame (the `follows` gate's per-frame cap), every body's mass change and the torso's centre of mass
    move (cm, its own frame), the share of the move kept under the follows cap, the least share a frame kept under the
    per-frame cap (`within_frames`), and the follows measure before and after."""
    turns = turned_off(before, after)
    turned = {segment: turns[:, index] for index, segment in enumerate(segments)}
    pelvis = 100 * np.linalg.norm(moved_by, axis=1)
    return {"method": "OpenSim's residual reduction (RRA; Delp et al. 2007, opensim-core RRATool): the pelvis' and "
                      "trunk's path and the body's masses and torso centre of mass adjusted, capped by follows",
            "rounds": RRA_ROUNDS, "kept share": kept, "least frame share": round(float(shares.min()), 3),
            "pelvis cm": [round(float(np.median(pelvis)), 2), round(float(pelvis.max()), 2)],
            "largest turn deg": round(float(turns.max()), 2),
            "segments deg": {segment: [round(float(np.median(found)), 2), round(float(found.max()), 2)]
                             for segment, found in turned.items()},
            "mass %": round(100 * float(step["mass"]), 3),
            "torso centre of mass cm": np.round(100 * step["torso"], 2).tolist(),
            "follows deg": [round(follows[0], 3), round(follows[1], 3)]}


def least(system, wanted, costs, highest):
    """The x in [0, highest] least in |system x - wanted|^2 + |costs x|^2: a bounded quadratic, solved by projected
    Newton steps (Bertsekas 1982): the bounds that hold the gradient back stay fixed, a Newton step on the rest (its
    inverse by Woodbury's identity, the system having far fewer rows than columns), the step halved until the cost
    falls; done when the projected gradient is under SOLVE_TOLERANCE of the largest linear term."""
    squares = costs ** 2
    linear = system.T @ wanted
    lowest = np.zeros(len(costs))
    enough = SOLVE_TOLERANCE * max(1.0, float(np.abs(linear).max(initial=0.0)))

    def cost(x):
        left = system @ x - wanted
        return 0.5 * (left @ left + squares @ x ** 2)

    x = np.zeros(len(costs))
    for _ in range(SOLVE_ROUNDS):
        gradient = system.T @ (system @ x) + squares * x - linear
        projected = np.abs(x - np.clip(x - gradient, lowest, highest)).max(initial=0.0)
        if projected <= enough:
            break
        near = min(projected, 1e-6)  # Bertsekas' epsilon: a bound this near, pushed on, is held
        held = ((x <= lowest + near) & (gradient > 0)) | ((x >= highest - near) & (gradient < 0))
        free = np.flatnonzero(~held)
        part = system[:, free] / squares[free]
        inner = np.eye(len(system)) + part @ system[:, free].T
        step = np.zeros(len(x))
        step[free] = -(gradient[free] / squares[free] - part.T @ np.linalg.solve(inner, part @ gradient[free]))
        size, before = 1.0, cost(x)
        while True:
            moved = np.clip(x + size * step, lowest, highest)
            if cost(moved) <= before + 1e-4 * gradient @ (moved - x) or size < 1e-10:
                break
            size /= 2
        x = moved
    return x


# --- the run ---------------------------------------------------------------------------------------------------------

def placed(turn, place):
    """A turn and a place as a 4 x 4."""
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = turn, place
    return found


def segment_pose(world):
    """A 4 x 4 as [x, y, z, qx, qy, qz, qw]."""
    return [*world[:3, 3], *Rotation.from_matrix(world[:3, :3]).as_quat()]


def local_turns(worlds, parents):
    """Each segment but the first against its parent, as rotation vectors in degrees."""
    return [Rotation.from_matrix(worlds[parent][:3, :3].T @ worlds[index][:3, :3]).as_rotvec(degrees=True)
            for index, parent in enumerate(parents) if parent >= 0]


def path_of(data, tendon):
    """A tendon's path points now (MuJoCo's frame): its wrap points, a pulley's (a break between branches, at the
    origin) left out."""
    span = slice(data.ten_wrapadr[tendon], data.ten_wrapadr[tendon] + data.ten_wrapnum[tendon])
    return data.wrap_xpos.reshape(-1, 3)[span][data.wrap_obj.reshape(-1)[span] != -2]


def bones_of(model):
    """The bone meshes of the person's model in their bodies' frames ({body name: (points, faces)}), from MuJoCo's own
    compile of its file (`model`), each mesh's vertices merged within BONE_CELL."""
    found = {}
    for geom in np.flatnonzero(model.geom_type == mujoco.mjtGeom.mjGEOM_MESH):
        mesh = model.geom_dataid[geom]
        points = model.mesh_vert[model.mesh_vertadr[mesh]:model.mesh_vertadr[mesh] + model.mesh_vertnum[mesh]]
        faces = model.mesh_face[model.mesh_faceadr[mesh]:model.mesh_faceadr[mesh] + model.mesh_facenum[mesh]]
        turn = np.zeros(9)
        mujoco.mju_quat2Mat(turn, model.geom_quat[geom])
        points = points @ turn.reshape(3, 3).T + model.geom_pos[geom]
        points, faces = merged(points, faces)
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, model.geom_bodyid[geom])
        if name in found:
            before = found[name]
            points, faces = np.concatenate([before[0], points]), np.concatenate([before[1], faces + len(before[0])])
        found[name] = (points, faces)
    return found


def merged(points, faces):
    """A mesh with its vertices merged within BONE_CELL (vertex clustering) and the faces that fell flat dropped."""
    cells = np.round(points / BONE_CELL).astype(np.int64)
    _, first, inverse = np.unique(cells, axis=0, return_index=True, return_inverse=True)
    faces = inverse.reshape(-1)[faces]
    faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
    return points[first], faces


def run_person(job, person, out_path):
    """One person: its model sized and built, its path fitted, its physics frame by frame."""
    targets = np.load(person["targets"])
    worlds, ground = targets["world"], targets["ground"]
    path = out_path.parent / f"{person['name']}.xml"
    record = myo.person_file(job["model"], {**limb_lengths(person), "height": person["height"]}, person["kg"], path)
    model = built(path, job["gravity"])
    rides = sided_map(RIDES)
    bodies = {segment: body_index(model, rides[segment]) for segment in person["segments"]}
    colliders = [geom for geom in range(model.ngeom) if model.geom_contype[geom] or model.geom_conaffinity[geom]]
    physics = Physics(model, ground, colliders)
    fixed = offsets(model, physics.couplings, person, person["segments"], bodies)
    feet = {segment: [geom for geom in colliders if model.geom_bodyid[geom] == bodies[segment]]
            for segment in person["segments"] if segment.endswith(FEET)}
    for _ in range(OFFSET_ROUNDS):
        fixed = refitted(model, motion(model, physics.couplings, person, worlds, bodies, fixed), worlds,
                         person["segments"], bodies, fixed)
    soles = {bodies[segment]: geoms for segment, geoms in feet.items()}
    planted = [{bodies[segment] for segment in standing} for standing in stances(person, worlds, ground, job["rate"])]
    qpath = filtered(model, physics.couplings, motion(model, physics.couplings, person, worlds, bodies, fixed, ground,
                                                      soles, planted), job["rate"])
    sensors = [bodies[segment] for segment in sided(TARGETS)]
    for landing in range(LAND_ROUNDS + 1):  # the low-pass moves a held foot again: land, filter, and land last
        qpath = landed(model, physics.couplings, qpath, ground, soles, planted, sensors)
        qpath = qpath if landing == LAND_ROUNDS else filtered(model, physics.couplings, qpath, job["rate"])
    qpath, shift = grounded(model, qpath, colliders, ground, person["name"])
    names = [str(name) for name in person["rig"]["names"]]
    parents = [person["segments"].index(names[parent]) if parent >= 0 and names[parent] in person["segments"] else -1
               for parent in (person["rig"]["parents"][names.index(segment)] for segment in person["segments"])]
    riding = {segment: np.linalg.inv(placed(*[part[segment] for part in fixed])) for segment in person["segments"]}
    fitted_poses = posed_path(model, qpath, person["segments"], bodies, riding)
    weight = sum(model.body_mass) * job["gravity"]
    limits = (job["residual"]["force"] * weight, job["residual"]["moment"] * weight * com_height(model, qpath[0], ground))
    most = (job["adjust"]["move most m"], np.radians(job["adjust"]["turn most deg"]))

    def land(path):
        return footed(model, physics.couplings, path, qpath, list(soles))

    adjusted, moves, step = reduced(physics, qpath, job["rate"], limits, most, land)
    riders = (person["segments"], bodies, riding, parents)
    adjusted, kept = within_follows(physics, qpath, adjusted, moves, land, worlds, riders, job["adjust"]["follows deg"])
    adjusted, shares = within_frames(physics, qpath, kept * moves, land, fitted_poses, riders, most, job["rate"])
    adjusted_poses = posed_path(model, adjusted, person["segments"], bodies, riding)
    adjustment = adjustment_record((adjusted[:, :3] - qpath[:, :3]) @ TO_OWN.T, kept, shares, step, fitted_poses,
                                   adjusted_poses, person["segments"],
                                   [off_clip(model, walked, worlds, person["segments"], bodies, riding, parents)
                                    for walked in (qpath, adjusted)])
    qpath = adjusted
    velocities, accelerations = rates(model, qpath, job["rate"])
    joints = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, model.dof_jntid[dof]) for dof in
              physics.couplings.leads[6:]]
    own_model = mujoco.MjModel.from_xml_path(str(path))  # MuJoCo's own compile: its meshes and muscle names
    named = {mujoco.mj_id2name(own_model, mujoco.mjtObj.mjOBJ_TENDON, own_model.actuator_trnid[actuator, 0]):
             mujoco.mj_id2name(own_model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator) for actuator in range(own_model.nu)}
    muscles = [named[mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_TENDON, model.actuator_trnid[actuator, 0])]
               for actuator in physics.muscles]
    meshes = bones_of(own_model)
    drawn = sorted(meshes)
    drawn_ids = [body_index(model, name) for name in drawn]
    frames, bones, segments, paths, counts = [], [], [], [], []
    weight = sum(model.body_mass) * job["gravity"]
    for frame in range(len(qpath)):
        share = physics.shared(physics.needed(qpath[frame], velocities[frame], accelerations[frame]))
        data = physics.data
        posed = [own_pose(model, data, bodies[segment]) @ riding[segment] for segment in person["segments"]]
        pushes = share["pushes"] @ TO_OWN.T
        frames.append({
            "angles": np.round(local_turns(posed, parents), 3).tolist(),  # the body's segments' turns
            "targets": np.round(local_turns(worlds[frame], parents), 3).tolist(),
            "torques": np.round(share["moments"], 3).tolist(),
            "ground": np.round(pushes.sum(axis=0), 3).tolist(),
            "lowest": rounded(lowest_over(model, data, colliders, ground)),
            "feet": {segment: [rounded(lowest_over(model, data, geoms, ground)) if geoms else None,
                               round(float(pushes[bodies[segment], 1]), 3)] for segment, geoms in feet.items()},
            "residual": np.round(np.concatenate([TO_OWN @ share["residual"][:3], TO_OWN @ share["residual"][3:]]),
                                 3).tolist(),
            "reserve": round(float(np.abs(share["reserves"]).max(initial=0.0)), 3),
            "activations": np.round(share["activations"], 4).tolist(),
            "forces": np.round(share["forces"], 2).tolist(),
            "poses": np.round([segment_pose(after @ np.linalg.inv(before) @ world) for after, before, world in
                               zip(adjusted_poses[frame], fitted_poses[frame], worlds[frame])], 5).tolist()})
        segments.append([segment_pose(world) for world in posed])
        bones.append([segment_pose(own_pose(model, data, body)) for body in drawn_ids])
        mine = [path_of(data, tendon) for tendon in model.actuator_trnid[physics.muscles, 0]]
        counts.append([len(points) for points in mine])
        paths.append(np.concatenate(mine) @ TO_OWN.T)
    arrays = {f"{person['name']}/bones": np.asarray(bones, dtype=np.float32),
              f"{person['name']}/segments": np.asarray(segments, dtype=np.float32),
              f"{person['name']}/paths": np.concatenate(paths).astype(np.float32),
              f"{person['name']}/counts": np.asarray(counts, dtype=np.int32)}
    for name, (points, faces) in meshes.items():
        arrays[f"{person['name']}/mesh/{name}/points"] = points.astype(np.float32)
        arrays[f"{person['name']}/mesh/{name}/faces"] = faces.astype(np.int32)
    entry = {"model": {**record, "lacks": {key: value for key, value in LACKS.items()}},
             "muscles": muscles, "joints": joints, "bones": drawn,
             "rides": {segment: rides[segment] for segment in person["segments"]},
             "com height": round(com_height(model, qpath[0], ground), 4), "shift": round(shift, 4), "kg": round(float(sum(model.body_mass)), 3),
             "weight N": round(float(weight), 2), "adjusted": adjustment, "frames": frames}
    return entry, arrays


def limb_lengths(person):
    """The person's own limb lengths from its rig's bind (metres, myo.LIMBS' segments)."""
    names = [str(name) for name in person["rig"]["names"]]
    bind = np.asarray(person["rig"]["bind"], dtype=float)
    ends = {"thigh": ("Leg", "Shin"), "shin": ("Shin", "Foot"), "foot": ("Foot", "ToeBase"),
            "upper arm": ("Arm", "ForeArm"), "forearm": ("ForeArm", "Hand")}
    return {f"{segment} {letter}": float(np.linalg.norm(bind[names.index(side + far), :3, 3]
                                                         - bind[names.index(side + near), :3, 3]))
            for segment, (near, far) in ends.items() for letter, side in myo.SIDES.items()}


def rounded(value):
    return None if value is None else round(value, 5)


def run(job_path, out_path):
    job = json.loads(job_path.read_text())
    people, arrays = {}, {}
    for person in job["people"]:
        people[person["name"]], mine = run_person(job, person, out_path)
        arrays.update(mine)
    np.savez_compressed(out_path.with_suffix(".npz"), **arrays)
    out_path.write_text(json.dumps({"engine": f"newton {newton.__version__} SolverMuJoCo's model (MuJoCo "
                                              f"{mujoco.__version__}, CPU), inverse dynamics with contact and static "
                                              "optimisation; nothing stepped", "rate": job["rate"], "people": people}))


if __name__ == "__main__":
    run(*arguments())
