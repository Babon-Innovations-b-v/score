"""Runs in Newton's own Python (score/stages/physics/inside/newton_env.sh: Newton with its MuJoCo solver, pinned): every
character's sim body of one scene, each MyoFullBody sized to the person's SOMA body (`sizing`, `myo`), on its own
copy of the scene's ground (#65).

    <env>/bin/python score/stages/sim_body/inside/sim_body.py <job.json> <out.json>

job.json (written by score/stages/sim_body): {"rate", "gravity", "model" (the fetched model's folder), "residual"
({"force", "moment"}: the limits' shares of the weight, and of it times the centre's height), "adjust" ({"move most
m", "turn most deg", "follows deg"}: RRA's caps), "people":
[{"name", "kg", "height" (the person's own standing height, m), "rig" ({"names", "parents", "bind"}: the person's rig),
"segments" ([SOMA segment name], in the order of `targets`), "standing" (each segment's frame in the rig's
standing clip's first frame, or null), "targets" (an .npz whose `world` is frames x segments x
4 x 4: each segment's frame in the clip, `ground` n x 3 x 3: the scene's triangles it may touch, both in the
person's own frame, Y up, and `points`, `faces`, `weights`: the person's SOMA mesh at its bind and its skin weights,
which `sizing` sizes MyoFullBody to)}]}.

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

This file is the run only: each step is a module beside it (#70), imported from this folder as Python puts a script's
folder first: `bone_groups` (which body each segment rides), `ground`, `solvers`, `model` (the model Newton builds,
its couplings), `sizing` and `myo` (the person's file), `contact` (the feet on the ground), `fit` (OpenSense's fit),
`muscles` (the static optimisation), `rra` (the residual reduction) and `records` (what is written).

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

import myo
from bone_groups import FEET, RIDES, TARGETS, sided, sided_map
from contact import grounded, stances
from fit import LAND_ROUNDS, OFFSET_ROUNDS, calibration, landed, motion, offsets, refitted
from model import TO_OWN, body_index, built, filtered, posed_path, rates
from muscles import Physics
from records import adjustment_record, arrays, bones_of, com_height, entry, frames, placed
from rra import footed, off_clip, reduced, within_follows, within_frames
from sizing import Size


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def run_person(job, person, out_path):
    """One person: its model sized and built, its path fitted, its physics frame by frame."""
    targets = np.load(person["targets"])
    worlds, ground = targets["world"], targets["ground"]
    path = out_path.parent / f"{person['name']}.xml"
    rig = {**person["rig"], "points": targets["points"], "faces": targets["faces"], "weights": targets["weights"]}
    record = myo.person_file(job["model"], Size(rig), person["kg"], path)
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
    standing = calibration(person, person["segments"])
    planted = [{bodies[segment] for segment in stood}
               for stood in stances(standing, person["segments"], worlds, ground, job["rate"])]
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

    riders = (person["segments"], bodies, riding, parents)
    adjusted, moves, step = reduced(physics, qpath, job["rate"], limits, most, land, fitted_poses, riders)
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
    records, bones, segments, paths, counts = frames(physics, qpath, velocities, accelerations, worlds, ground, riders,
                                                     feet, (fitted_poses, adjusted_poses), drawn_ids)
    mine = arrays(person["name"], bones, segments, paths, counts, meshes)
    return entry(model, record, (muscles, joints, drawn), {segment: rides[segment] for segment in person["segments"]},
                 qpath[0], ground, shift, job["gravity"], adjustment, records), mine


def run(job_path, out_path):
    job = json.loads(job_path.read_text())
    people, arrays_found = {}, {}
    for person in job["people"]:
        people[person["name"]], mine = run_person(job, person, out_path)
        arrays_found.update(mine)
    np.savez_compressed(out_path.with_suffix(".npz"), **arrays_found)
    out_path.write_text(json.dumps({"engine": f"newton {newton.__version__} SolverMuJoCo's model (MuJoCo "
                                              f"{mujoco.__version__}, CPU), inverse dynamics with contact and static "
                                              "optimisation; nothing stepped", "rate": job["rate"], "people": people}))


if __name__ == "__main__":
    run(*arguments())
