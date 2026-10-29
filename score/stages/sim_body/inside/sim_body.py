"""Runs in Newton's own Python (score/stages/physics/inside/newton_env.sh: Newton with its MuJoCo solver, pinned): every
character's sim body of one scene, each MyoFullBody sized to the person's SOMA body (`sizing`, `myo`), on its own
copy of the scene's ground (#65).

    <env>/bin/python score/stages/sim_body/inside/sim_body.py <job.json> <out.json>

job.json (written by score/stages/sim_body): {"rate", "gravity", "model" (the fetched model's folder), "residual"
({"force", "moment"}: the limits' shares of the weight, and of it times the centre's height), "adjust" ({"move most
m", "turn most deg", "follows deg"}: RRA's caps), "people":
[{"name", "kg", "height" (the person's own standing height, m), "rig" ({"names", "parents", "bind"}: the person's rig),
"segments" ([SOMA segment name], in the order of `targets`), "targets" (an .npz whose `world` is frames x segments x
4 x 4: each segment's frame in the clip, `ground` n x 3 x 3: the scene's triangles it may touch, both in the
person's own frame, Y up, and `points`, `faces`, `weights`: the person's SOMA mesh at its bind and its skin weights,
which `sizing` sizes MyoFullBody to and the fit's markers are skinned on)}]}.

The movement is the clip's (the owner, 2026-10-27: "we have kimodo for the actual movement; and myobody plus mujoco and
newton for the physics"), and SOMA is the truth (#70): MyoFullBody is fitted to it, never the reverse, and nothing
here moves, scales or grounds SOMA.
- One solver (`fit`, #70): the person's constants (each bone group's size, the limbs' joint centres, each virtual
  marker's place on its bone) and every frame's joint angles, against the bone groups' turns (the main term: each SOMA
  segment's world turn on its group's site, turned by the static calibration table; OpenSense's orientation tracking,
  Al Borno et al. 2022, doi:10.1186/s12984-022-01001-x) and the SOMA mesh's bony landmarks skinned on the clip's own
  skin as markers, weighed as OpenSim's IK weighs its two goals: mink per frame (couplings held exactly, the leading
  joints in their ranges) and scipy's bounded least_squares over the constants together with the angles of frames
  spread over the clip (OpenSim's ScaleTool and MarkerPlacer, solved as one problem); then the person's file is
  written again with the found constants and every frame fitted on
  it. MyoFullBody's root follows the markers on SOMA's skin; nothing is grounded. How closely the path follows SOMA
  (each joint's mm, each group's degrees, split at a range limit or not) is the model record's `fit`.
- The fitted path carried onto Newton's model by joint name and low-passed at CUTOFF (Winter's 6 Hz, zero lag)
  before it is differentiated; velocities and accelerations its central differences.
- OpenSim's residual reduction (RRA: Delp et al. 2007, doi:10.1109/TBME.2007.901024; opensim-core's RRATool,
  Apache-2.0), in our own stack (`reduced`): RRA_ROUNDS times, the body's mass changed by the mean upward residual and
  the torso's centre of mass moved under the mean residual moment (RRATool::adjustCOMToReduceResiduals), then the
  pelvis' and trunk's path moved so the ground's pushes explain the movement, each frame's move capped, the feet kept
  where they stood by the legs (`Footing`: mink, as the fit); the result kept within the clip's `follows` limit
  (`within_follows`). Nothing is applied to the body; how far it moved is the body's `adjusted` record.
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
folder first: `bone_groups` (the bone groups: which body each segment rides), `ground`, `solvers`, `landmarks`,
`calibration`, `volumes`, `model` (the model Newton builds, its couplings), `sizing` and `myo` (the person's file),
`contact` (the feet on the ground), `fit` (the one solver), `muscles` (the static optimisation), `rra` (the residual
reduction) and `records` (what is written).

out.json: {"engine", "rate", "people": {name: {"model" (the person's model record), "muscles" ([name]), "joints" ([name]
of each driven dof), "com height" (m, frame 0, over its ground), "frames":
[{"angles": [[x, y, z] degrees, rotation vector, per SOMA segment but the first, against its parent, as the body's
segment riding its bone turns], "targets": [...the clip's...], "torques": [N m per joint], "ground": [x, y, z] N
(the ground's push), "lowest": m (the lowest collider
point's height over the ground, null off it), "feet": {segment: [its lowest collider point's height over the ground
(null off it), the ground's upward push on it N]} (FEET), "residual": [force xyz N, moment xyz N m], "reserve": N m
(the largest joint reserve), "activations": [0..1 per muscle], "forces": [N per muscle, tension]}],
"adjusted": RRA's moves (`adjustment_record`)}}}, everything in the person's own frame (Y
up); and beside it <out>.npz, per person: `<name>/bones` (each body's pose every frame, frames x bodies x 7),
`<name>/segments` (each SOMA segment riding its bone every frame, frames x segments x 7: turned by the calibration
table, at its start joint's centre, `fit.riding`), `<name>/paths` (every muscle's path points, all frames end to end),
`<name>/counts` (frames x muscles: each
path's point count) and `<name>/mesh/<body>/points|faces` (each bone in its body's frame)."""
import json
import pathlib
import sys

import mujoco
import newton
import numpy as np

import fit
import myo
from bone_groups import FEET, groups
from model import TO_OWN, body_index, built, carried, filtered, posed_path, rates
from muscles import Physics
from records import adjustment_record, arrays, bones_of, com_height, entry, frames
from rra import Footing, off_clip, reduced, within_follows, within_frames
from sizing import Size


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def fitted_person(job, person, rig, worlds, path):
    """The person's file at `path` with the fit's constants, its record (the fit and its following of SOMA in it),
    each body's scale and the fitted path (qpos of MuJoCo's own compile of the file)."""
    size, segments = Size(rig), person["segments"]
    _, scales = myo.person_file(job["model"], size, person["kg"], path)
    held = fit.followed(segments)
    turns, points = fit.targets(rig, segments, worlds, held)
    found = fit.constants(fit.fitting(path, scales, held), turns, points)
    record, scales = myo.person_file(job["model"], size, person["kg"], path, found)
    fitting = fit.fitting(path, scales, held, found["marks"])
    angles = fit.angles(fitting, turns, points)
    record["fit"] = {"method": fit.METHOD, "constants": fit.constants_record(found),
                     "following": fit.following(fitting.model, angles, worlds, segments, scales)}
    return record, scales, fitting.model, angles


def run_person(job, person, out_path):
    """One person: its model sized and fitted to SOMA, its path, its physics frame by frame."""
    targets = np.load(person["targets"])
    worlds, ground = targets["world"], targets["ground"]
    segments = person["segments"]
    path = out_path.parent / f"{person['name']}.xml"
    rig = {**person["rig"], "points": targets["points"], "faces": targets["faces"], "weights": targets["weights"]}
    record, scales, own, angles = fitted_person(job, person, rig, worlds, path)
    model = built(path, job["gravity"])
    rides = {segment: groups()[segment][2] for segment in segments}
    bodies = {segment: body_index(model, rides[segment]) for segment in segments}
    colliders = [geom for geom in range(model.ngeom) if model.geom_contype[geom] or model.geom_conaffinity[geom]]
    physics = Physics(model, ground, colliders)
    feet = {segment: [geom for geom in colliders if model.geom_bodyid[geom] == bodies[segment]]
            for segment in segments if segment.endswith(FEET)}
    soles = {bodies[segment]: geoms for segment, geoms in feet.items()}
    qpath = filtered(model, physics.couplings, carried(own, model, angles), job["rate"])
    names = [str(name) for name in person["rig"]["names"]]
    parents = [segments.index(names[parent]) if parent >= 0 and names[parent] in segments else -1
               for parent in (person["rig"]["parents"][names.index(segment)] for segment in segments)]
    riding = fit.riding(model, scales, segments)
    fitted_poses = posed_path(model, qpath, segments, bodies, riding)
    weight = sum(model.body_mass) * job["gravity"]
    limits = (job["residual"]["force"] * weight, job["residual"]["moment"] * weight * com_height(model, qpath[0], ground))
    most = (job["adjust"]["move most m"], np.radians(job["adjust"]["turn most deg"]))

    footing = Footing(model, physics.couplings, list(soles))

    def land(path):
        return footing.footed(path, qpath)

    riders = (segments, bodies, riding, parents)
    adjusted, moves, step = reduced(physics, qpath, job["rate"], limits, most, land, fitted_poses, riders)
    adjusted, kept = within_follows(physics, qpath, adjusted, moves, land, worlds, riders, job["adjust"]["follows deg"])
    adjusted, shares = within_frames(physics, qpath, kept * moves, land, fitted_poses, riders, most, job["rate"])
    adjusted_poses = posed_path(model, adjusted, segments, bodies, riding)
    adjustment = adjustment_record((adjusted[:, :3] - qpath[:, :3]) @ TO_OWN.T, kept, shares, step, fitted_poses,
                                   adjusted_poses, segments,
                                   [off_clip(model, walked, worlds, segments, bodies, riding, parents)
                                    for walked in (qpath, adjusted)])
    feet_off = footing.off(adjusted, qpath)
    adjustment["feet held mm, deg"] = [round(1000 * float(feet_off[:, 0].max()), 3),
                                       round(float(np.degrees(feet_off[:, 1].max())), 3)]
    qpath = adjusted
    record["fit"]["following, the path the physics takes"] = fit.following(model, qpath, worlds, segments, scales)
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
    records, bones, posed, paths, counts = frames(physics, qpath, velocities, accelerations, worlds, ground, riders,
                                                  feet, drawn_ids)
    mine = arrays(person["name"], bones, posed, paths, counts, meshes)
    return entry(model, record, (muscles, joints, drawn), rides, qpath[0], ground, job["gravity"], adjustment,
                 records), mine


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
