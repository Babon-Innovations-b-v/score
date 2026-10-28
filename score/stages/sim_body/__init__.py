"""The sim body stage (experimental, #65; PRD #56): row `sim-body@<place>`, every character of the place's accepted cast
as a musculoskeletal body, MyoFullBody (MyoSuite's: its bones, joints, 416 muscles and their tendons), doing its clip
on the scene's own ground (CONTEXT.md "sim body"), for a place whose design shows people.

    make     each character of cast.json (its singles; the crowd, which is retiring, is left out by name) is the
             clips rig (people-clips-made's rig.npz) moved onto its look's built body (people-body-<look>'s rig.npz,
             an optional read: its bind, moved mean surface and offsets, the travel scaled by its Hips' height, as
             prop_build.py plays the clips; the rig's own size, named, with none taken). Its body is MyoFullBody
             (the pinned wheel MODEL, fetched once to $PROPS_HOME/models and checked by its sha256; never in this
             repository) sized to that build: each limb by the person's joint distance over the model's, the rest by
             its standing height (inside/sizing), its mass the stated weight when the cast gives one (`weight`, kg),
             else its height (`height`, m, else the body's own standing height) squared times the reference BMI of
             its sex (`sex`, else the mean of both), marked estimated. It stands on the scene's own ground: every solid
             of the stage the cast is measured on (the seed's base layer with its scene record written in, on the
             terrain row's made ground: layer_base.built and cast/measure.solids, so steps, decks and slopes are
             there), the triangles within REACH of its clip's path, in the frame its skeleton plays in (its spot and
             turn, then the dressed body's Turned: own_frame); a body with none is left out by name. The movement is
             its clip's (`doing`, the rig's clip_<doing>), followed exactly, root included (the owner, 2026-10-27);
             Newton and MuJoCo give its physics (inside/sim_body.py, in Newton's own Python,
             score/stages/physics/inside/newton_env.sh, on this machine, under the gravity of the body the scene
             stands on, physics/design.py ground): the model's joint angles fitted to the clip's segment turns, the
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
from score.stages import cast as cast_stage
from score.stages import layer_base
from score.stages.cast import measure

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
LAYER = "layers/sim_bodies.usda"
RECORD = "sim_bodies.json"
RATE = 30.0  # the rig's clips (tools/characters/skel_usd.py RATE)
# SOMA joints that carry no segment: the ground point under the body and the end sites.
NOT_SEGMENTS = ("Root", "HeadEnd", "LeftToeEnd", "RightToeEnd")
# Global age-standardised mean BMI of adults, 2016 (kg/m2): NCD-RisC, Lancet 2017;390:2627-42,
# https://doi.org/10.1016/S0140-6736(17)32129-3. Height times this is #64's rule for a body with no stated weight.
BMI = {"male": 24.5, "female": 24.8}
# MyoFullBody's foot colliders meet a MuJoCo floor within their 1 mm margin, MuJoCo's default solref and solimp, as
# MyoSuite, MuscleMimic and KINESIS leave them: 75 kg on two such capsules rests 0.1 mm into it without the margin and
# 0.9 mm over it with it (measured, MuJoCo 3.x, 1 ms steps, 2026-10-28), so
# a body more than a few millimetres into its ground is sunk (owner, 2026-10-28: "ground contact is real"); the ground
# pushes a point only within the run's GAP (5 mm) over it, so a carrying foot further off is floating.
SUNK_MOST = 0.003  # metres
LANDED = 0.005  # metres
CONTACT = 0.05  # share of the weight a foot's push must reach to count as landed
REACH = 1.0  # metres round a body's clip path (its segments, across the ground) whose solids it may touch
FEET = ("Foot", "ToeBase")
# A dressed body's Turned, degrees about up: the people build's root node (tools/characters/maker/prop_build.py build,
# "Person", rotation [0, 1, 0, 0]: the rig faces +z, a laid character -z). The skeleton plays the sim in that frame.
TURNED = 180.0
BODY = "people-body"  # a look's built body row: its rig.npz is the person's own build (prop_rig.py)
CARRIED = 0.05  # share of the weight
FOLLOWED = 5.0  # degrees
STANDING = "standing"  # the rig's clip a body is calibrated on (inside/sim_body.py offsets)
# The residual's limits, the body's weight standing in for the net external force (none is measured here): the force
# at most 2% of it (owner, 2026-10-28, from 5%: AddBiomechanics' published residual forces are "smaller than 2% of peak
# external force", Werling et al. 2023, PLoS ONE 18:e0295152, doi:10.1371/journal.pone.0295152, taken as the
# benchmark only), the moment at most 1% of it times the centre of mass' height (Hicks, Uchida, Seth, Rajagopal and
# Delp 2015, "Is my model good enough?", J Biomech Eng 137(2):020905, section 3.1.3).
RESIDUAL_FORCE = 0.02
RESIDUAL_MOMENT = 0.01
# The residual reduction's cap (inside/sim_body.py `reduced`, OpenSim's RRA): on every frame, all rounds together, the
# pelvis at most MOVE_MOST and every segment's turn at most FOLLOWED off the fitted path (owner, 2026-10-28;
# `within_frames`, gated by `follows`), and the adjusted path kept within FOLLOWED of the clip on the mean (the owner,
# 2026-10-28: "never more"). MOVE_MOST is ours: no published limit names a pelvis move.
MOVE_MOST = 0.02  # metres


def files(place):
    """The run's folder (its script and every module beside it), the Python it runs in and the environment's physics
    (whose gravity the scene has)."""
    return {"sim inside": "{repo}/" + INSIDE_FOLDER, "sim env": "{repo}/" + ENV_SCRIPT,
            "physics": "{data}/physics/setting.json", "within": "{data}/places/within.json",
            "seed": "{seeds}/usd-r3/{place}", **layer_base.files(place)}


# --- the body ------------------------------------------------------------------------------------------------------

def segments_of(rig):
    """The rig's segment joints (indices) and, for each rig joint, the segment that carries it (its nearest kept
    joint up the tree; the root's children carry the root)."""
    names, parents = [str(name) for name in rig["names"]], rig["parents"]
    kept = [joint for joint, name in enumerate(names) if name not in NOT_SEGMENTS]

    def carrier(joint):
        while joint >= 0 and joint not in kept:
            joint = parents[joint]
        return joint

    carriers = [carrier(joint) for joint in range(len(names))]
    top = next(joint for joint in kept if carrier(parents[joint]) < 0)
    return kept, [top if found < 0 else found for found in carriers]


def body_row(single):
    """The built body row of a character's look (people-cloth's own naming)."""
    return f"{BODY}-{(single.get('look') or '').replace('/', '-')}"


def person_rig(rig, built):
    """The clips rig at a person's own build, as the people build plays its clips (prop_build.py clip_world): the
    built body's bind and surface (rig.npz's moved mean surface), every clip's joint offsets the built ones and its
    travel (Hips) scaled by the built Hips' height over the rig's; and that size. The rig itself, size 1, for None."""
    if built is None:
        return rig, 1.0
    hips = [str(name) for name in rig["names"]].index("Hips")
    size = float(built["bind"][hips, 1, 3] / rig["bind"][hips, 1, 3])
    found = dict(rig, bind=np.asarray(built["bind"]), points=np.asarray(built["source_points"]))
    moved = [joint for joint, parent in enumerate(rig["parents"]) if parent >= 0 and joint != hips]
    for key in [key for key in rig if key.startswith("clip_")]:
        local = np.array(rig[key], dtype=float)
        for joint in moved:
            local[:, joint, :3, 3] = built["offsets"][joint]
        local[:, hips, :3, 3] *= size
        found[key] = local
    return found, size


def standing_height(rig):
    """The rig's own standing height at its bind pose (metres, its surface's top over its lowest point)."""
    points = np.asarray(rig["points"])
    return float(points[:, 1].max() - points[:, 1].min())


def mass_of(single, height):
    """A character's body mass record: the stated weight, else height squared times the reference BMI of its sex
    (the mean of both when none is stated), marked estimated (#64)."""
    if single.get("weight"):
        return {"kg": float(single["weight"]), "source": "stated weight"}
    stated = single.get("height")
    tall = float(stated or height)
    sex = single.get("sex")
    bmi = BMI[sex] if sex in BMI else sum(BMI.values()) / len(BMI)
    return {"kg": round(bmi * tall ** 2, 2), "source": "estimated", "height": round(tall, 4),
            "height from": "stated" if stated else "the SOMA body's own standing height",
            "sex": sex if sex in BMI else "not stated", "bmi": bmi}


def clip_frames(rig, clip, kept):
    """The clip's segment frames in the world, frame by frame (frames x segments x 4 x 4): its joints' transforms
    against their parents chained down the tree."""
    local = np.asarray(rig[f"clip_{clip}"], dtype=float)
    parents = rig["parents"]
    world = np.empty_like(local)
    for joint in range(local.shape[1]):
        world[:, joint] = local[:, joint] if parents[joint] < 0 else world[:, parents[joint]] @ local[:, joint]
    return world[:, kept]


# --- the ground ----------------------------------------------------------------------------------------------------

def solids_of(inputs, place):
    """{solid: its triangles in the place's frame} of the stage the cast is measured on: the seed's base layer with its
    scene record written in, on the place's made ground (the cast's own reading, cast/measure.solids); no water."""
    with layer_base.built(inputs) as folder:
        found = measure.solids(pathlib.Path(folder) / "layers/base.usda", place, cast_stage.made_ground(inputs, place))
    return {name: tris for name, tris in found.items() if not name.startswith(measure.WATER)}


def own_frame(at, turn):
    """The frame a character's sim body runs in, in the place's: its spot, then its turn about up (tools/characters/
    cast.py placed), then its dressed body's Turned (TURNED about up), the rig's frame its skeleton plays in."""
    from scipy.spatial.transform import Rotation
    frame = np.eye(4)
    frame[:3, :3], frame[:3, 3] = Rotation.from_euler("y", turn + TURNED, degrees=True).as_matrix(), at
    return frame


def ground_of(solids, worlds, frame):
    """The triangles a body may touch, in its own frame (n x 3 x 3), and the solids they are of: those whose span
    across the ground meets its clip's segments' span (`worlds`, its own frame) grown by REACH."""
    path = np.asarray(worlds)[:, :, [0, 2], 3].reshape(-1, 2)
    low, high = path.min(axis=0) - REACH, path.max(axis=0) + REACH
    back = np.linalg.inv(frame)
    found, names = [], []
    for name, tris in solids.items():
        mine = tris @ back[:3, :3].T + back[:3, 3]
        near = mine[((mine[:, :, [0, 2]].max(axis=1) >= low) & (mine[:, :, [0, 2]].min(axis=1) <= high)).all(axis=1)]
        if len(near):
            found.append(near)
            names.append(name)
    return (np.concatenate(found) if found else np.zeros((0, 3, 3))), names


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
                              "segments": [str(rig["names"][joint]) for joint in kept], "targets": str(targets),
                              "standing": clip_frames(rig, STANDING, kept)[0].tolist()
                              if f"clip_{STANDING}" in rig else None})
        records[single["name"]] = {"clip": single["doing"], "at": single["at"], "turn": single.get("turn", 0.0),
                                   "mass": mass, "ground": {"solids": under, "triangles": len(ground)},
                                   "calibrated on": f"the rig's {STANDING} clip, as the model's zero pose"
                                   if f"clip_{STANDING}" in rig else "SOMA's bind: the rig has no standing clip",
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
                                          "left out": left_out}, indent=1))


def soma_pose(world):
    """A SOMA segment's frame (4 x 4) as the skin plays it, unrounded: [x, y, z, qx, qy, qz, qw]."""
    from scipy.spatial.transform import Rotation
    return [*map(float, world[:3, 3]), *map(float, Rotation.from_matrix(world[:3, :3]).as_quat())]


# --- the measures and gates ----------------------------------------------------------------------------------------

def angle_between(one, other):
    """The angle (degrees) between two rotations given as rotation vectors in degrees."""
    from scipy.spatial.transform import Rotation
    turn = Rotation.from_rotvec(np.radians(one)) * Rotation.from_rotvec(np.radians(other)).inv()
    return np.degrees(turn.magnitude())


def landings(frames, weight):
    """Each landed foot's height over its ground (metres), frame by frame: a foot the ground pushes up with at least
    CONTACT of the weight."""
    return [height for frame in frames for height, push in frame["feet"].values()
            if push >= CONTACT * weight and height is not None]


def measured(entry, gravity):
    """A run's gate numbers: its deepest point into its ground, each landed foot's height off it, the mean upward push
    over its weight, the mean and worst angle off the clip, the largest move RRA made off the fitted path on any frame
    (a segment's turn, the pelvis' place), the largest joint moment and reserve, the residual's
    largest force and moment against their limits, and the muscles' activations and forces."""
    frames, weight = entry["frames"], entry["kg"] * gravity
    off = np.array([angle_between(frame["angles"], frame["targets"]) for frame in frames])
    push = np.mean([frame["ground"][1] for frame in frames])
    landed = np.abs(landings(frames, weight))
    force = np.array([float(np.linalg.norm(frame["residual"][:3])) for frame in frames])
    moment = np.array([float(np.linalg.norm(frame["residual"][3:])) for frame in frames])
    limits = (RESIDUAL_FORCE * weight, RESIDUAL_MOMENT * entry["com height"] * weight)
    forces, activations = np.array([frame["forces"] for frame in frames]), np.array([frame["activations"]
                                                                                     for frame in frames])
    return {"deepest": round(-min(0.0, min(frame["lowest"] for frame in frames if frame["lowest"] is not None)), 4),
            "landings": len(landed), "mean foot off ground m": round(float(landed.mean()), 4) if len(landed) else None,
            "worst foot off ground m": round(float(landed.max()), 4) if len(landed) else None,
            "weight N": round(weight, 2), "mean push N": round(float(push), 2),
            "push over weight": round(float(push / weight), 4),
            "mean off clip deg": round(float(off.mean()), 3), "worst off clip deg": round(float(off.max()), 3),
            "largest adjusted turn deg": entry["adjusted"]["largest turn deg"],
            "largest pelvis move cm": entry["adjusted"]["pelvis cm"][1],
            "largest torque Nm": round(float(max(np.abs(frame["torques"]).max() for frame in frames)), 2),
            "largest reserve Nm": round(float(max(frame["reserve"] for frame in frames)), 2),
            "largest residual N": round(float(force.max()), 2), "mean residual N": round(float(force.mean()), 2),
            "median residual N": round(float(np.median(force)), 2), "residual force limit N": round(limits[0], 2),
            "largest residual Nm": round(float(moment.max()), 2), "mean residual Nm": round(float(moment.mean()), 2),
            "median residual Nm": round(float(np.median(moment)), 2), "residual moment limit Nm": round(limits[1], 2),
            "frames within residual limits": round(float(((force <= limits[0]) & (moment <= limits[1])).mean()), 3),
            "largest muscle force N": round(float(forces.max()), 1),
            "muscle force N, mean of each frame's largest": round(float(forces.max(axis=1).mean()), 1),
            "largest activation": round(float(activations.max()), 4),
            "mean activation": round(float(activations.mean()), 4)}


def bodies_of(output):
    return json.loads((pathlib.Path(output) / RECORD).read_text())["bodies"]


def verdict(name, faults, passed, measures, findings=()):
    return checks.Verdict(name, checks.FAIL if faults else checks.PASS, "; ".join(faults[:3]) if faults else passed,
                          measures, {}, tuple(faults) or tuple(findings))


def judge_on_floor(output, inputs, evidence):
    """Fail a body that went into its ground by more than SUNK_MOST in any frame."""
    bodies = bodies_of(output)
    faults = [f"{name} went {body['measures']['deepest']:.3f} m into its ground" for name, body in bodies.items()
              if body["measures"]["deepest"] > SUNK_MOST]
    return verdict("on floor", faults, f"{len(bodies)} bodies, none into its ground by over {SUNK_MOST} m",
                   {"bodies": len(bodies)})


def judge_lands(output, inputs, evidence):
    """Fail a body a landed foot of which stood more than LANDED off its ground, or none of whose feet ever landed."""
    bodies = bodies_of(output)
    faults = [f"{name}: no foot landed on its ground" if not body["measures"]["landings"] else
              f"{name}: a landed foot {body['measures']['worst foot off ground m']:.3f} m off its ground"
              for name, body in bodies.items() if not body["measures"]["landings"]
              or body["measures"]["worst foot off ground m"] > LANDED]
    return verdict("lands", faults, f"{len(bodies)} bodies, each landed foot within {LANDED} m of its ground",
                   {"bodies": len(bodies)})


def judge_carries(output, inputs, evidence):
    """Fail a body whose ground's mean push is off its weight by more than CARRIED of it."""
    bodies = bodies_of(output)
    faults = [f"{name}: the ground pushes {body['measures']['push over weight']:.3f} of its weight"
              for name, body in bodies.items() if abs(body["measures"]["push over weight"] - 1.0) > CARRIED]
    return verdict("carries", faults, f"{len(bodies)} bodies, the ground carries each one's weight within "
                   f"{CARRIED:.0%}", {"bodies": len(bodies)})


def judge_follows(output, inputs, evidence):
    """Fail a body whose joints are off its clip's by more than FOLLOWED degrees on the mean, or that RRA moved off its
    fitted path by more than FOLLOWED degrees on a segment or MOVE_MOST at the pelvis on any frame."""
    bodies, faults = bodies_of(output), []
    for name, body in bodies.items():
        found = body["measures"]
        if found["mean off clip deg"] > FOLLOWED:
            faults.append(f"{name}: {found['mean off clip deg']:.2f} degrees off its clip on the mean")
        if found["largest adjusted turn deg"] > FOLLOWED:
            faults.append(f"{name}: a segment turned {found['largest adjusted turn deg']:.1f} degrees off its fitted "
                          f"path in a frame")
        if found["largest pelvis move cm"] > 100 * MOVE_MOST:
            faults.append(f"{name}: the pelvis moved {found['largest pelvis move cm']:.1f} cm off its fitted path in "
                          f"a frame")
    return verdict("follows", faults, f"{len(bodies)} bodies, each within {FOLLOWED} degrees of its clip on the mean "
                   f"and RRA's move within {FOLLOWED} degrees and {100 * MOVE_MOST:.0f} cm on every frame",
                   {"bodies": len(bodies)})


def judge_residual(output, inputs, evidence):
    """Fail a body whose pelvis residual passes its force or moment limit in any frame."""
    bodies = bodies_of(output)
    faults = []
    for name, body in bodies.items():
        found = body["measures"]
        if found["largest residual N"] > found["residual force limit N"]:
            faults.append(f"{name}: a residual of {found['largest residual N']:.0f} N, over its "
                          f"{found['residual force limit N']:.0f} N")
        if found["largest residual Nm"] > found["residual moment limit Nm"]:
            faults.append(f"{name}: a residual moment of {found['largest residual Nm']:.0f} N m, over its "
                          f"{found['residual moment limit Nm']:.0f} N m")
    return verdict("residual", faults, f"{len(bodies)} bodies, each residual within {RESIDUAL_FORCE:.0%} of its weight "
                   f"and {RESIDUAL_MOMENT:.0%} of its weight times its centre's height", {"bodies": len(bodies)})


def output_faults(folder):
    folder = pathlib.Path(folder)
    found = [f"no {name}" for name in (RECORD, LAYER) if not (folder / name).exists()]
    if not found and not bodies_of(folder):
        found.append("no sim body: the cast names no character whose clip the rig holds")
    return found


CONTRACT = contracts.Contract("sim-body", 2, output_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("on floor", judge_on_floor), checks.Check("lands", judge_lands),
          checks.Check("carries", judge_carries),
          checks.Check("follows", judge_follows), checks.Check("residual", judge_residual))


# --- the layer -----------------------------------------------------------------------------------------------------

MUSCLE_WIDTH = 0.006  # metres: a muscle's drawn line
DRAWN = 3  # decimals a drawn muscle point keeps (a millimetre): the layer is text
RESTING, ACTIVE = (0.25, 0.35, 0.85), (0.9, 0.1, 0.1)  # a muscle's colour at activation 0 and 1


def write_layer(path, place, runs, arrays, records):
    """layers/sim_bodies.usda: each body under its character's prim, a guide in the Turned frame: an Xform a SOMA
    segment (its pose every frame) holding the bones of the body it rides, every other bone under Bones (its pose
    every frame), each bone a Mesh; and Muscles, every muscle a line along its path every frame, coloured from RESTING
    to ACTIVE by its activation."""
    from pxr import Gf, Sdf, Usd, UsdGeom, Vt
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    layer.timeCodesPerSecond = layer.framesPerSecond = RATE
    stage = Usd.Stage.Open(layer)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    for name, entry in runs.items():
        frames = entry["frames"]
        root = f"/{place}/Characters/{name}/SimBody"
        for prim in (f"/{place}", f"/{place}/Characters", f"/{place}/Characters/{name}"):
            stage.OverridePrim(prim)
        body = UsdGeom.Xform.Define(stage, root)
        UsdGeom.Imageable(body).CreatePurposeAttr(UsdGeom.Tokens.guide)
        body.GetPrim().SetCustomDataByKey("score:mass", records[name]["mass"])
        segments = list(entry["rides"])
        bones, riders = arrays[f"{name}/bones"], arrays[f"{name}/segments"]
        held = {}
        for index, segment in enumerate(segments):
            part = UsdGeom.Xform.Define(stage, f"{root}/{segment}")
            timed(part, riders[:, index])
            held.setdefault(entry["rides"][segment], (f"{root}/{segment}", index))
        UsdGeom.Scope.Define(stage, f"{root}/Bones")
        for number, bone in enumerate(entry["bones"]):
            points = arrays[f"{name}/mesh/{bone}/points"].astype(float)
            if bone in held:  # drawn in the segment riding it, which carries it rigidly
                where, index = held[bone]
                carried = np.linalg.inv(pose_matrix(riders[0, index])) @ pose_matrix(bones[0, number])
                points = points @ carried[:3, :3].T + carried[:3, 3]
            else:
                where = f"{root}/Bones/bone_{bone}"
                timed(UsdGeom.Xform.Define(stage, where), bones[:, number])
            mesh = UsdGeom.Mesh.Define(stage, f"{where}/bone_{bone}")
            mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.round(points, DRAWN + 1).astype(np.float32)))
            faces = arrays[f"{name}/mesh/{bone}/faces"]
            mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(faces)))
            mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(faces.reshape(-1).astype(np.int32)))
            mesh.CreateDisplayColorAttr([Gf.Vec3f(0.89, 0.85, 0.79)])
        muscles = UsdGeom.BasisCurves.Define(stage, f"{root}/Muscles")
        muscles.CreateTypeAttr(UsdGeom.Tokens.linear)
        colours = UsdGeom.PrimvarsAPI(muscles).CreatePrimvar("displayColor", Sdf.ValueTypeNames.Color3fArray,
                                                             UsdGeom.Tokens.uniform)
        muscles.CreateWidthsAttr(Vt.FloatArray([MUSCLE_WIDTH]))
        muscles.SetWidthsInterpolation(UsdGeom.Tokens.constant)
        counts = arrays[f"{name}/counts"]
        muscles.CreateCurveVertexCountsAttr(Vt.IntArray.FromNumpy(counts.max(axis=0).astype(np.int32)))
        placed = muscles.CreatePointsAttr()
        for code, (frame, points) in enumerate(zip(frames, padded(arrays[f"{name}/paths"], counts))):
            placed.Set(Vt.Vec3fArray.FromNumpy(np.round(points, DRAWN).astype(np.float32)), code)
            shade = np.clip(np.asarray(frame["activations"]), 0.0, 1.0)[:, None]
            colours.Set(Vt.Vec3fArray.FromNumpy(np.round(np.asarray(RESTING) * (1 - shade) + np.asarray(ACTIVE) * shade,
                                                         DRAWN).astype(np.float32)), code)
    layer.Save()


def padded(paths, counts):
    """Each frame's muscle path points (the frames' paths end to end, `counts` frames x muscles), each muscle padded
    to its most points over the frames by repeating its last one, so the drawn lines keep one topology."""
    most, start = counts.max(axis=0), 0
    for row in counts:
        pieces = []
        for count, room in zip(row, most):
            mine = paths[start:start + count]
            pieces.append(np.concatenate([mine, np.repeat(mine[-1:], room - count, axis=0)]))
            start += count
        yield np.concatenate(pieces)


def pose_matrix(pose):
    """A pose [x, y, z, qx, qy, qz, qw] as a 4 x 4."""
    from scipy.spatial.transform import Rotation
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = Rotation.from_quat(np.asarray(pose[3:], dtype=float)).as_matrix(), pose[:3]
    return found


def timed(xform, poses):
    """An Xform's transform set at every frame's pose."""
    from pxr import Gf
    moved = xform.AddTransformOp()
    for code, pose in enumerate(poses):
        moved.Set(Gf.Matrix4d(np.round(pose_matrix(pose).T, 6).tolist()), code)
