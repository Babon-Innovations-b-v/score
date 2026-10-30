"""The sim body stage (experimental, #65; PRD #56): row `sim-body@<place>`, every character of the place's accepted cast
as a musculoskeletal body, MyoFullBody (MyoSuite's: its bones, joints, 416 muscles and their tendons), doing its clip
on the scene's own ground (CONTEXT.md "sim body"), for a place whose design shows people.

    make     each character of cast.json (its singles; the crowd, which is retiring, is left out by name; a cast of a
             crowd and no singles is a valid input, its record's `no bodies` saying why, every gate passing on none) is the
             clips rig (people-clips-made's rig.npz) moved onto its look's built body (people-body-<look>'s rig.npz,
             an optional read: its bind, moved mean surface and offsets, the travel scaled by its Hips' height, every
             clip lifted so the standing clip's first frame puts the feet where the bind does, as prop_build.py
             plays the clips; with none taken, the rig's own bind as the build, size 1, named). Its body is MyoFullBody
             (the pinned wheel MODEL, fetched once to $PROPS_HOME/models and checked by its sha256; never in this
             repository) sized to that build: each bone group by the person's joint distance (inside/sizing), then
             fitted to it with the clip (inside/fit: group sizes, joint centres, markers), its mass the stated
             weight when the cast gives one (`weight`, kg), else its height (`height`, m, else the body's own standing
             height) squared times the reference BMI of
             its sex (`sex`, else the mean of both), marked estimated. It stands on the scene's own ground: every solid
             of the stage the cast is measured on (the seed's base layer with its scene record written in, on the
             terrain row's made ground: layer_base.built and cast/measure.solids, so steps, decks and slopes are
             there), the triangles within REACH of its clip's path, in the frame its skeleton plays in (its spot and
             turn, then the dressed body's Turned: own_frame); a body with none is left out by name. The movement is
             its clip's (`doing`, the rig's clip_<doing>), followed exactly, root included (the owner, 2026-10-27);
             Newton and MuJoCo give its physics (inside/sim_body.py, in Newton's own Python,
             score/stages/physics/inside/newton_env.sh, on this machine, under the gravity of the body the scene
             stands on, physics/design.py ground): the model's joint angles fitted to the clip's segment turns and its
             skin's bony landmarks (one solver: mink per frame, scipy's least_squares over the constants), the
             forces that movement needs, shared between the ground's contacts and the muscles (activations and
             forces, static optimisation), what neither can give left over as the pelvis' residual and the joints'
             reserves, measured and never applied. Before the physics is measured, OpenSim's residual reduction (RRA)
             adjusts the pelvis' and trunk's path and the body's masses and torso centre of mass so the ground explains
             the movement, capped (MOVE_MOST, FOLLOWED) and kept within the `follows` limit; how far is recorded per
             body (`adjusted`); the skin plays SOMA's own clip. Written: sim_bodies.json (each body: its mass record, size, model
             record, the SOMA segments and the body each rides, the solids it may touch, measures and the gates'
             numbers), measures/<name>.json (per frame: the body's SOMA segments' turns and the clip's, joint
             moments, ground force, lowest point over the ground, each foot's height over the ground and its push, the
             residual, the largest reserve, each muscle's activation and force, and each SOMA segment's pose: the
             clip's own, never moved, scaled or grounded to the sim body (owner, 2026-10-28: SOMA is the truth),
             which the skin plays) and
             layers/sim_bodies.usda (each body under its character's prim, /<place>/Characters/<name>/SimBody, in
             the Turned frame: an Xform a SOMA segment riding its bone, every bone's mesh under the segment it rides or
             under Bones, and the muscles as lines along their paths, coloured by activation, every frame)
    gates    on floor     no collider point of any body goes into its ground by more than SUNK_MOST, any frame
             lands        a foot (Foot, ToeBase) the ground pushes with at least CONTACT of the weight is within
                          LANDED of the ground under it (its lowest collider point's height over the drawn triangles),
                          every such frame; a body no foot of which ever lands fails
             carries      over each run the ground's mean upward push is the body's weight within CARRIED
             follows      the mean angle between each SOMA segment's turn (riding its bone) and the clip's, over
                          segments and frames, at most FOLLOWED degrees; and RRA's move off the fitted path, every
                          frame, at most FOLLOWED degrees on any segment and MOVE_MOST at the pelvis
             residual     after RRA's capped adjustment the pelvis' residual stays within its limits, the net external
                          force taken as the body's weight: its force at most RESIDUAL_FORCE of it and its moment at most
                          RESIDUAL_MOMENT of it times the centre of mass' height, any frame (a trip, a float or a
                          movement no ground and muscles can make shows here: a dropped sample, never a forced pass)

Not here: muscles driving a forward simulation (the movement is given; the muscles are the forces that would make it,
with no activation dynamics), clips made for the ground (a flat-ground clip meets a step with its toe), a walker's cast
path (the clip plays its own root path from the spot), the build's feet brought in (stance.narrowed).
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import urllib.request
import zipfile

import numpy as np

from score import checks, contracts
from score.stages import layer_base
from score.stages.sim_body._body import (BODY, RATE, body_row, clip_frames, mass_of, person_rig,  # noqa: F401
                                         segments_of, standing_height)
from score.stages.sim_body._gates import (EMPTY_CAST, FOLLOWED, LAYER, MOVE_MOST, NO_SINGLES,  # noqa: F401
                                          RECORD, RESIDUAL_FORCE, RESIDUAL_MOMENT, judge_carries, judge_follows,
                                          judge_lands, judge_on_floor, judge_residual, measured, output_faults)
from score.stages.sim_body._ground import REACH, ground_of, own_frame, solids_of
from score.stages.sim_body._layer import ACTIVE, write_layer  # noqa: F401

REPO = pathlib.Path(__file__).resolve().parents[3]
INSIDE = "score/stages/sim_body/inside/sim_body.py"
INSIDE_FOLDER = "score/stages/sim_body/inside"  # the run and every module it imports from its own folder (#70)
ENV_SCRIPT = "score/stages/physics/inside/newton_env.sh"
HOME = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))
ENV = HOME / "envs/newton_env"
# MyoFullBody as MuscleMimic publishes it (Apache-2.0; its NOTICE: MyoSuite and myo_sim, Apache-2.0, from OpenSim's
# Rajagopal 2016, lumbar spine and hand models, MIT, and MoBL-ARMS, whose model definition was released for
# non-commercial use only): fetched by its pinned wheel and sha256, never kept in this repository.
# 1.0.6 (amathislab/musclemimic_models 001b723): the left knee's tibia couplings with their signs right (#10; 1.0.5
# turned and slid the left tibia the wrong way as the knee bent) and the deltoid and back wraps whose paths jumped (#9).
MODEL = ("https://files.pythonhosted.org/packages/c2/bf/deaa309a8af26e759c6ff49340707279b1c814eb4fd2916fb0636bce3d7e/"
         "musclemimic_models-1.0.6-py3-none-any.whl",
         "88b096fe072bd5d2cfcc88ec43ffef27a73bc5a54e6699d3bda0e92a76a03bea")
# Kept under MyoHub's Apache-2.0 (owner, 2026-10-27, #65); written into every body record.
ATTRIBUTION = ("MyoFullBody: MyoSuite and myo_sim (MyoHub, Apache-2.0), as MuscleMimic Models 1.0.6 publishes it; "
               "its arm and hand derived from MoBL-ARMS: Holzbaur, Murray and Delp 2005, "
               "doi:10.1007/s10439-005-3320-7, and Saul et al. 2015, doi:10.1080/10255842.2014.916698")
CLIPS_ROW = "people-clips-made"
# What a body's bone groups are calibrated on (#70: the static table, inside/calibration), the same for every person.
CALIBRATED_ON = ("the static calibration table: SOMA's template bind against MyoFullBody's default pose (its couplings "
                 "applied), never fitted")


def files(place):
    """The run's folder (its script and every module beside it), the Python it runs in and the environment's physics
    (whose gravity the scene has)."""
    return {"sim inside": "{repo}/" + INSIDE_FOLDER, "sim env": "{repo}/" + ENV_SCRIPT,
            "physics": "{data}/physics/setting.json", "within": "{data}/places/within.json",
            "seed": "{seeds}/usd-r3/{place}", **layer_base.files(place)}


# --- the run -------------------------------------------------------------------------------------------------------

def fetched():
    """The model's folder: MODEL's wheel downloaded once into $PROPS_HOME/models, checked by its sha256, unpacked."""
    url, sha = MODEL
    folder = HOME / "models" / sha[:16]
    if (folder / ".unpacked").exists():
        return folder
    folder.mkdir(parents=True, exist_ok=True)
    wheel = folder / url.rpartition("/")[2]
    with urllib.request.urlopen(url, timeout=120) as answer:
        wheel.write_bytes(answer.read())
    if hashlib.sha256(wheel.read_bytes()).hexdigest() != sha:
        wheel.unlink()
        raise ValueError(f"{url}: its sha256 is not the pinned {sha}")
    with zipfile.ZipFile(wheel) as packed:
        packed.extractall(folder)
    (folder / ".unpacked").touch()
    return folder


def ran(job, out):
    """inside/sim_body.py run on `job` in Newton's own Python on this machine (built once by the env script): its
    record and its arrays (bones, muscle paths)."""
    subprocess.run(["bash", str(REPO / ENV_SCRIPT), str(ENV)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([str(ENV / "bin/python"), str(REPO / INSIDE), str(job), str(out)], check=True)
    found = json.loads(out.read_text())
    arrays = dict(np.load(out.with_suffix(".npz")))
    out.unlink()
    out.with_suffix(".npz").unlink()
    for written in out.parent.glob("*.xml"):
        written.unlink()
    return found, arrays


def gravity_of(place, inputs):
    """The gravity of the body the scene stands on (the physics stage's own reading)."""
    from score.stages.physics import design
    within = {name: entry["within"] for name, entry in
              json.loads(pathlib.Path(inputs["within"]).read_text()).get("within", {}).items()}
    return design.ground(place, within, json.loads(pathlib.Path(inputs["physics"]).read_text()))


def make(inputs, out, seed, params):
    """Every character's sim body run on its clip: sim_bodies.json, measures/, layers/sim_bodies.usda."""
    cast = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())
    place = cast["place"]
    clips_rig = dict(np.load(pathlib.Path(inputs[CLIPS_ROW]) / "rig.npz"))
    body, gravity = gravity_of(place, inputs)
    solids = solids_of(inputs, place)
    job, records, left_out = {"rate": RATE, "gravity": gravity, "people": []}, {}, []
    (out / "clips").mkdir(parents=True)
    builds, clips = {}, {}
    for single in cast["characters"]:
        if f"clip_{single.get('doing')}" not in clips_rig:
            left_out.append(f"{single['name']}: its clip {single.get('doing')!r} is not in the rig")
            continue
        row = body_row(single)
        if row not in builds:
            built = dict(np.load(pathlib.Path(inputs[row]) / "rig.npz")) if row in inputs else None
            builds[row] = person_rig(clips_rig, built)
        rig, size = builds[row]
        kept = segments_of(rig)[0]
        worlds = clip_frames(rig, single["doing"], kept)
        ground, under = ground_of(solids, worlds, own_frame(single["at"], single.get("turn", 0.0)))
        if not len(ground):
            left_out.append(f"{single['name']}: no solid of the place within {REACH} m of its clip's path to stand on")
            continue
        mass = mass_of(single, standing_height(rig))
        targets = out / "clips" / f"{single['name']}.npz"
        np.savez_compressed(targets, world=worlds, ground=ground, points=rig["points"], faces=rig["faces"],
                            weights=rig["weights"])
        clips[single["name"]] = worlds
        job["people"].append({"name": single["name"], "kg": mass["kg"], "height": standing_height(rig),
                              "rig": {"names": [str(name) for name in rig["names"]],
                                      "parents": np.asarray(rig["parents"]).tolist(),
                                      "bind": np.asarray(rig["bind"]).tolist()},
                              "segments": [str(rig["names"][joint]) for joint in kept], "targets": str(targets)})
        records[single["name"]] = {"clip": single["doing"], "at": single["at"], "turn": single.get("turn", 0.0),
                                   "mass": mass, "ground": {"solids": under, "triangles": len(ground)},
                                   "calibrated on": CALIBRATED_ON,
                                   "size": {"of the rig": round(size, 4),
                                            "from": row if row in inputs else f"the rig's: no {row} taken"}}
    if cast.get("crowd"):
        left_out.append(f"{cast['crowd']['name']}: a crowd has no sim bodies (crowds are retiring, #56)")
    run, arrays = {"engine": None, "people": {}}, {}
    if job["people"]:
        job["model"] = str(fetched())
        job["residual"] = {"force": RESIDUAL_FORCE, "moment": RESIDUAL_MOMENT}
        job["adjust"] = {"move most m": MOVE_MOST, "turn most deg": FOLLOWED, "follows deg": FOLLOWED}
        (out / "job.json").write_text(json.dumps(job))
        run, arrays = ran(out / "job.json", out / "run.json")
    (out / "measures").mkdir()
    for name, entry in run["people"].items():
        for frame, worlds in zip(entry["frames"], clips[name]):  # SOMA is the truth: its joints leave as they came
            frame["poses"] = [soma_pose(world) for world in worlds]
        (out / "measures" / f"{name}.json").write_text(json.dumps(entry["frames"]))
        records[name].update(segments=entry["rides"], model=entry["model"], muscles=len(entry["muscles"]),
                             adjusted=entry["adjusted"], measures=measured(entry, gravity))
    write_layer(out / LAYER, place, run["people"], arrays, records)
    shutil.rmtree(out / "clips")
    (out / "job.json").unlink(missing_ok=True)
    (out / RECORD).write_text(json.dumps({"place": place, "on": body, "gravity": gravity, "engine": run["engine"],
                                          "rate": RATE, "model": {"wheel": MODEL[0].rpartition("/")[2],
                                                                  "attribution": ATTRIBUTION}, "bodies": records,
                                          "left out": left_out, **no_singles(cast)}, indent=1))


def no_singles(cast):
    """Why a cast of a crowd and no single characters has no bodies: a valid input, not a fault (#70)."""
    return {} if cast["characters"] or not cast.get("crowd") else {"no bodies": NO_SINGLES}


def soma_pose(world):
    """A SOMA segment's frame (4 x 4) as the skin plays it, unrounded: [x, y, z, qx, qy, qz, qw]."""
    from scipy.spatial.transform import Rotation
    return [*map(float, world[:3, 3]), *map(float, Rotation.from_matrix(world[:3, :3]).as_quat())]


CONTRACT = contracts.Contract("sim-body", 2, output_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("on floor", judge_on_floor), checks.Check("lands", judge_lands),
          checks.Check("carries", judge_carries),
          checks.Check("follows", judge_follows), checks.Check("residual", judge_residual))


