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
which `sizing` sizes MyoFullBody to and the fit's markers are skinned on), optional "recordings" ([.npz path, each with
its `world`]: every recording of the person's SOMA body, its person constants solved from all of them together; else
the clip's alone)}]}.

The movement is the clip's (the owner, 2026-10-27: "we have kimodo for the actual movement; and myobody plus mujoco and
newton for the physics"), and SOMA is the truth (#70): MyoFullBody is fitted to it, never the reverse, and nothing
here moves, scales or grounds SOMA.
- One solver (`fit`, #70): the person's constants (each landmark's marker's place on its
  bone and each joint inside a bone group; the lengths are SOMA's, from the sizing) and every frame's joint angles, against the bone groups' turns (the main term: each SOMA
  segment's world turn on its group's site, turned by the static calibration table; OpenSense's orientation tracking,
  Al Borno et al. 2022, doi:10.1186/s12984-022-01001-x) and SCORE's landmark set skinned on the clip's own skin as
  markers, weighed by their trust as OpenSim's IK weighs its two goals: mink per frame (couplings held exactly, the
  leading joints in their ranges) and scipy's bounded least_squares over the constants, together with the angles of frames spread over all the body's recordings (the person constants,
  once per SOMA body); then the person's file is written again with the found constants and every frame's pose
  fitted on it, the constants held. MyoFullBody's root follows the markers on SOMA's skin; nothing is grounded. How closely the path follows SOMA
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
  contacts (each point of the person's skin, riding the bones, within GAP of the drawn triangle under it or into it, along the triangle's
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
(the ground's push), "lowest": m (the lowest skin
point's height over the ground, null off it), "touches": {part: [the ground's push on it, xyz N, and its centre of
pressure on the ground, xyz m]} (every part the ground pushes: each foot, its calcaneus and toes as one, by its Foot
segment's name, a seat under a thigh, a bed under the back, by its body's; low-passed over each span it touches, as the
path is: `records.steadied`),
"feet": {segment: [its lowest skin point's height over the ground
(null off it), the ground's upward push on it N]} (FEET), "residual": [force xyz N, moment xyz N m], "reserve": N m
(the largest joint reserve), "activations": [0..1 per muscle], "forces": [N per muscle, tension]}],
"adjusted": RRA's moves (`adjustment_record`), "pushes": the pushes' measures against the physics
(`records.push_measures`)}}}, everything in the person's own frame (Y
up); and beside it <out>.npz, per person: `<name>/bones` (each body's pose every frame, frames x bodies x 7),
`<name>/segments` (each SOMA segment riding its bone every frame, frames x segments x 7: turned by the calibration
table, at its start joint's centre, `fit.riding`), `<name>/paths` (every muscle's path points, all frames end to end),
`<name>/counts` (frames x muscles: each
path's point count) and `<name>/mesh/<body>/points|faces` (each bone in its body's frame)."""
import json
import os
import pathlib
import sys


def warp_cache(environ):
    """The variables that keep Warp's compiled modules in a cluster node's cache (the job runtime's `SCORE_CACHE`,
    else /cache: tools/cloud/runtime/weights.CACHE, a node's folder every pod on it mounts) when there is one and
    nothing names Warp's own: a node compiles a sim body's modules once, not every clip's pod (#70: 75 s of them on
    a first run, 0.2 s read back). Elsewhere Warp's own default, kept on the machine, stands."""
    cache = pathlib.Path(environ.get("SCORE_CACHE", "/cache"))
    if "WARP_CACHE_PATH" in environ or not os.access(cache, os.W_OK):
        return {}
    return {"WARP_CACHE_PATH": str(cache / "warp")}


os.environ.update(warp_cache(os.environ))  # before Warp is imported: it reads the folder once, at its start

import mujoco  # noqa: E402
import newton  # noqa: E402
import numpy as np  # noqa: E402

import fit  # noqa: E402
import myo  # noqa: E402
from bone_groups import FEET, groups  # noqa: E402
from contact import Skin  # noqa: E402
from landmarks import at_starts  # noqa: E402
from model import TO_OWN, body_index, built, carried, filtered, posed_path, rates  # noqa: E402
from muscles import Physics, parts_of  # noqa: E402
from records import adjustment_record, arrays, bones_of, com_height, entry, frames  # noqa: E402
from rra import Footing, off_clip, reduced, within_follows, within_frames  # noqa: E402
from sizing import Size  # noqa: E402


def arguments():
    given = sys.argv[1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), pathlib.Path(given[1])


def recordings(person, worlds):
    """Every recording of the person's SOMA body (each frames x segments x 4 x 4): the job's `recordings` (npz paths,
    each with its `world`) when given, else the clip's own `worlds` alone."""
    return [np.load(found)["world"] for found in person["recordings"]] if person.get("recordings") else [worlds]


def person_set_up(job, person, rig, worlds, path, size, made=None):
    """The person's file at `path` (MyoFullBody sized by `size`, `sizing.Size` of the person's rig) with the fit's
    constants (the person constants, solved once from all the body's `recordings`), its record (the fit's method and
    constants in it), each body's scale and the `Fitting` its clips' angles are solved on. `made`: the recordings'
    targets, when the caller made them already (`constants_set_up`)."""
    _, scales = myo.person_file(job["model"], size, person["kg"], path)
    return constants_set_up(job, person, rig, worlds, path, size, scales, made)


def constants_set_up(job, person, rig, worlds, path, size, scales, made=None, found=None):
    """`person_set_up` from the sized file without constants already at `path` (its scales `scales`): the constants
    solved on it, the file written again with them, its record, each body's scale and the `Fitting`. `made`: the
    recordings' `fit.targets` in order, when the caller made them already; `found`: the constants, when the caller
    solved them already (`fit.constants_across`, every set of a body at once)."""
    segments = person["segments"]
    held = fit.followed(segments)
    if found is None:
        made = made or [fit.targets(rig, segments, clip, held) for clip in recordings(person, worlds)]
        found = fit.constants(fit.fitting(path, scales, held, segments), made)
    record, scales = myo.person_file(job["model"], size, person["kg"], path, found)
    fitting = fit.fitting(path, scales, held, segments, found["marks"])
    record["fit"] = {"method": fit.METHOD, "constants": fit.constants_record(found)}
    return record, scales, fitting


def clip_angles(fitting, rig, segments, worlds, made=None):
    """The clip's fitted path on `fitting` (qpos of MuJoCo's own compile of the file: the pose alone per frame, the
    constants held), by `fit.angles`, the bones held inside SOMA's posed skin (the stage's; level 1's evaluation runs
    without them: `evaluation.SKIN_ROWS`, `evaluation._case.fitted_case`). `made`: the clip's `fit.targets`, when the
    caller made them already (`fitted_person`)."""
    turns, points, skins = made or fit.targets(rig, segments, worlds, fit.followed(segments))
    return fit.angles(fitting, turns, points, skins)


def followed_record(record, fitting, angles, worlds, segments, scales, rig):
    """`record`'s fit given its following of SOMA (`fit.following` of the clip's fitted path)."""
    record["fit"]["following"] = fit.following(fitting.model, angles, worlds, segments, scales, rig)
    return record


def fitted_person(job, person, rig, worlds, path):
    """The person's file at `path` with the fit's constants, its record (the fit and its following of SOMA in it),
    each body's scale, the fitted model and the clip's fitted path: set up, angles, record. The clip's targets are
    made once: with no `recordings` the clip is level 2's one recording too (#70: SOMA's skin was posed on every frame
    twice, about 11 s a clip)."""
    clip = fit.targets(rig, person["segments"], worlds, fit.followed(person["segments"]))
    made = None if person.get("recordings") else [clip]
    record, scales, fitting = person_set_up(job, person, rig, worlds, path, Size(rig), made)
    angles = clip_angles(fitting, rig, person["segments"], worlds, clip)
    record = followed_record(record, fitting, angles, worlds, person["segments"], scales, rig)
    return record, scales, fitting.model, angles


def skin_of(rig, segments, bodies, riding):
    """The person's drawn skin the ground pushes (`contact.Skin`): SOMA's mesh at its bind, its weights on the
    segments, each segment riding its bone from its group's start (`landmarks.at_starts`, as `riding` stands it)."""
    names = [str(name) for name in rig["names"]]
    joints = [names.index(segment) for segment in segments]
    table = groups()
    return Skin(rig["points"], np.asarray(rig["weights"], dtype=float)[:, joints],
                at_starts(rig, segments, [table[segment][0][0] for segment in segments]),
                [bodies[segment] for segment in segments], [riding[segment] for segment in segments])


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
    riding = fit.riding(model, scales, segments)
    skin = skin_of(rig, segments, bodies, riding)
    physics = Physics(model, ground, skin, parts_of(model, bodies))
    feet = {segment: np.flatnonzero(skin.owners == bodies[segment]) for segment in segments if segment.endswith(FEET)}
    qpath = filtered(model, physics.couplings, carried(own, model, angles), job["rate"])
    names = [str(name) for name in person["rig"]["names"]]
    parents = [segments.index(names[parent]) if parent >= 0 and names[parent] in segments else -1
               for parent in (person["rig"]["parents"][names.index(segment)] for segment in segments)]
    fitted_poses = posed_path(model, qpath, segments, bodies, riding)
    weight = sum(model.body_mass) * job["gravity"]
    limits = (job["residual"]["force"] * weight, job["residual"]["moment"] * weight * com_height(model, qpath[0], ground))
    most = (job["adjust"]["move most m"], np.radians(job["adjust"]["turn most deg"]))

    footing = Footing(model, physics.couplings, [bodies[segment] for segment in feet])

    def land(path):
        return footing.footed(path, qpath)

    riders = (segments, bodies, riding, parents)
    adjusted, moves, step = reduced(physics, qpath, job["rate"], limits, most, land, fitted_poses, riders)
    adjusted, kept = within_follows(physics, qpath, adjusted, moves, land, worlds, riders, job["adjust"]["follows deg"])
    own_model = mujoco.MjModel.from_xml_path(str(path))  # MuJoCo's own compile: its meshes and muscle names
    # its bones measured on MuJoCo's own compile (Newton is given no meshes); its qpos is Newton's in the same order
    skins = fit.FrameSkins(own_model, rig, segments, worlds)
    adjusted, shares = within_frames(physics, qpath, kept * moves, land, fitted_poses, riders, most, job["rate"],
                                     skins)
    adjusted_poses = posed_path(model, adjusted, segments, bodies, riding)
    adjustment = adjustment_record((adjusted[:, :3] - qpath[:, :3]) @ TO_OWN.T, kept, shares, step, fitted_poses,
                                   adjusted_poses, segments,
                                   [off_clip(model, walked, worlds, segments, bodies, riding, parents)
                                    for walked in (qpath, adjusted)])
    feet_off = footing.off(adjusted, qpath)
    adjustment["feet held mm, deg"] = [round(1000 * float(feet_off[:, 0].max()), 3),
                                       round(float(np.degrees(feet_off[:, 1].max())), 3)]
    qpath = adjusted
    record["fit"]["following, the path the physics takes"] = fit.following(own_model, qpath, worlds, segments, scales,
                                                                           rig)
    velocities, accelerations = rates(model, qpath, job["rate"])
    joints = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, model.dof_jntid[dof]) for dof in
              physics.couplings.leads[6:]]
    named = {mujoco.mj_id2name(own_model, mujoco.mjtObj.mjOBJ_TENDON, own_model.actuator_trnid[actuator, 0]):
             mujoco.mj_id2name(own_model, mujoco.mjtObj.mjOBJ_ACTUATOR, actuator) for actuator in range(own_model.nu)}
    muscles = [named[mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_TENDON, model.actuator_trnid[actuator, 0])]
               for actuator in physics.muscles]
    meshes = bones_of(own_model)
    drawn = sorted(meshes)
    drawn_ids = [body_index(model, name) for name in drawn]
    records, bones, posed, paths, counts, pushed = frames(physics, qpath, velocities, accelerations, worlds, ground,
                                                          riders, feet, drawn_ids, job["rate"])
    mine = arrays(person["name"], bones, posed, paths, counts, meshes)
    return entry(model, record, (muscles, joints, drawn), rides, qpath[0], ground, job["gravity"], adjustment,
                 records, pushed), mine


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
