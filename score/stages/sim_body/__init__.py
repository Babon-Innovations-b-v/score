"""The sim body stage (experimental, #65; PRD #56): row `sim-body@<place>`, every character of the place's accepted cast
as a physical body on Newton (CONTEXT.md "sim body"), for a place whose design shows people.

    make     each character of cast.json (its singles; the crowd, which is retiring, is left out by name) gets a body
             built straight from SOMA's segments as people-clips-made's rig.npz holds them (the 23 kept joints: one
             rigid segment a joint at SOMA's bind frame, a free root and ball joints, no template resizing): each
             segment's share of the mass and its inertia from the rig's closed surface cut into VOXEL cubes, each
             owned by its nearest vertex's strongest skin weight, a box collider round its own volume; its mass the
             stated weight when the cast gives one (`weight`, kg), else its height (`height`, m, else the body's own
             standing height) squared times the reference BMI of its sex (`sex`, else the mean of both), marked
             estimated. It stands on the scene's own ground: every solid of the stage the cast is measured on (the
             seed's base layer with its scene record written in, on the terrain row's made ground: layer_base.built
             and cast/measure.solids, so steps, decks and slopes are there), the triangles within REACH of its
             clip's path, in its own frame (its spot and turn), a static mesh only it meets; a body with none is
             left out by name. It plays its clip (`doing`, the rig's clip_<doing>): Newton's eval_ik turns the
             clip's segment frames into joint angles, MuJoCo position actuators drive them, the root's height is
             free, so its weight rests on its ground by contact (inside/sim_body.py, in Newton's own Python,
             score/stages/physics/inside/newton_env.sh, on this machine), under the gravity of the body the scene
             stands on (physics/design.py ground). Written: sim_bodies.json (each body: its mass record, segments,
             the solids it may touch, measures and the gates' numbers), measures/<name>.json (per frame: joint
             angles and the clip's, joint torques, ground force, lowest point over the ground, each foot's height
             over the ground and its push, root helper) and layers/sim_bodies.usda (each body
             under its character's prim, /<place>/Characters/<name>/SimBody: a guide Xform a segment with its
             UsdPhysics mass and its motion, its ball joints as UsdPhysics spherical joints)
    gates    on floor     no collider corner of any body goes into its ground by more than SUNK_MOST, any frame
             lands        past SETTLE, a foot (Foot, ToeBase) the ground pushes with at least CONTACT of the weight
                          is within LANDED of the ground under it (its lowest corner's height over the drawn
                          triangles), every such frame; a body no foot of which ever lands fails
             carries      over each run (past SETTLE seconds) the ground's mean upward push is the body's weight within
                          CARRIED (the body starts and ends at rest up and down, so Newton's second law leaves the
                          mean push its weight, on a slope too)
             follows      each body's joint angles follow its clip's: the mean angle between the sim's and the clip's
                          joint rotation, over joints and frames past SETTLE, at most FOLLOWED degrees

The root helper (its horizontal path and turn, never its weight) is reported: its largest and mean force.

Not here: muscles (they wait on #60), clips made for the ground (a flat-ground clip meets a step with its toe), a
walker's cast path (the clip plays its own root path from the spot), a person's own SOMA shape.
"""
import json
import os
import pathlib
import shutil
import subprocess

import numpy as np

from score import checks, contracts
from score.stages import cast as cast_stage
from score.stages import layer_base
from score.stages.cast import measure

REPO = pathlib.Path(__file__).resolve().parents[3]
INSIDE = "score/stages/sim_body/inside/sim_body.py"
ENV_SCRIPT = "score/stages/physics/inside/newton_env.sh"
ENV = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "envs/newton_env"
CLIPS_ROW = "people-clips-made"
LAYER = "layers/sim_bodies.usda"
RECORD = "sim_bodies.json"
RATE = 30.0  # the rig's clips (tools/characters/skel_usd.py RATE)
# SOMA joints that carry no segment: the ground point under the body and the end sites.
NOT_SEGMENTS = ("Root", "HeadEnd", "LeftToeEnd", "RightToeEnd")
VOXEL = 0.01  # metres
# Global age-standardised mean BMI of adults, 2016 (kg/m2): NCD-RisC, Lancet 2017;390:2627-42,
# https://doi.org/10.1016/S0140-6736(17)32129-3. Height times this is #64's rule for a body with no stated weight.
BMI = {"male": 24.5, "female": 24.8}
# Joint drive per kilogram the joint carries (the segments below it): stiffness N m/rad, damping N m s/rad.
DRIVE = (300.0, 30.0)
SETTLE = 0.5  # seconds let pass before the gates read: the body settling onto its ground
SUNK_MOST = 0.02  # metres
LANDED = 0.02  # metres: a foot further off its ground than this while it carries reads as floating or sunk
CONTACT = 0.05  # share of the weight a foot's push must reach to count as landed
REACH = 1.0  # metres round a body's clip path (its segments, across the ground) whose solids it may touch
FEET = ("Foot", "ToeBase")
CARRIED = 0.05  # share of the weight
FOLLOWED = 5.0  # degrees


def files(place):
    """The trial's script, the Python it runs in and the environment's physics (whose gravity the scene has)."""
    return {"sim script": "{repo}/" + INSIDE, "sim env": "{repo}/" + ENV_SCRIPT,
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


def voxels(points, faces):
    """The centres of the VOXEL cubes inside the closed surface."""
    import trimesh
    mesh = trimesh.Trimesh(points, faces, process=False)
    if not mesh.is_watertight:
        raise ValueError("the rig's surface is not closed: its volume cannot be cut into segments")
    return mesh.voxelized(VOXEL).fill().points


def body_of(rig):
    """The sim body of a rig at unit total mass: each segment's name, parent segment, joint frame in its parent's,
    mass share, centre of mass and inertia (its own frame) and box collider round its own volume."""
    from scipy.spatial import cKDTree
    names, parents, bind = [str(name) for name in rig["names"]], rig["parents"], np.asarray(rig["bind"], dtype=float)
    kept, carriers = segments_of(rig)
    owner = np.asarray(carriers)[np.asarray(rig["weights"]).argmax(axis=1)]
    inside = voxels(rig["points"], rig["faces"])
    _, nearest = cKDTree(rig["points"]).query(inside)
    voxel_owner = owner[nearest]
    share = 1.0 / len(inside)
    segments = []
    for joint in kept:
        frame = bind[joint]
        mine = inside[voxel_owner == joint]
        if not len(mine):
            raise ValueError(f"segment {names[joint]} owns no volume of the surface")
        local = (mine - frame[:3, 3]) @ frame[:3, :3]
        centre = local.mean(axis=0)
        spread = local - centre
        inertia = share * (np.eye(3) * (spread ** 2).sum() - spread.T @ spread)
        low, high = local.min(axis=0) - VOXEL / 2, local.max(axis=0) + VOXEL / 2
        parent = carriers[parents[joint]] if parents[joint] >= 0 else -1
        is_top = parent < 0 or parent == joint
        segments.append({"name": names[joint], "parent": -1 if is_top else kept.index(parent),
                         "local": (np.eye(4) if is_top else np.linalg.inv(bind[parent]) @ frame).tolist(),
                         "mass": share * len(mine), "com": centre.tolist(), "inertia": inertia.tolist(),
                         "box": [((low + high) / 2).tolist(), ((high - low) / 2).tolist()]})
    return segments, kept


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


def weighed(segments, kg):
    """The segments at a total mass of `kg` (mass and inertia scale with it)."""
    return [dict(segment, mass=segment["mass"] * kg, inertia=(np.asarray(segment["inertia"]) * kg).tolist())
            for segment in segments]


def gains(segments):
    """Each segment's joint drive (stiffness, damping): DRIVE times the mass its joint carries (itself and every
    segment below it)."""
    carried = [segment["mass"] for segment in segments]
    for index in reversed(range(len(segments))):
        if segments[index]["parent"] >= 0:
            carried[segments[index]["parent"]] += carried[index]
    return [[DRIVE[0] * mass, DRIVE[1] * mass] for mass in carried]


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
    """A character's frame in the place's (tools/characters/cast.py placed: its spot, then its turn about up)."""
    from scipy.spatial.transform import Rotation
    frame = np.eye(4)
    frame[:3, :3], frame[:3, 3] = Rotation.from_euler("y", turn, degrees=True).as_matrix(), at
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

def ran(job, out):
    """inside/sim_body.py run on `job` in Newton's own Python on this machine (built once by the env script)."""
    subprocess.run(["bash", str(REPO / ENV_SCRIPT), str(ENV)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run([str(ENV / "bin/python"), str(REPO / INSIDE), str(job), str(out)], check=True)
    found = json.loads(out.read_text())
    out.unlink()
    return found


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
    rig = dict(np.load(pathlib.Path(inputs[CLIPS_ROW]) / "rig.npz"))
    segments, kept = body_of(rig)
    body, gravity = gravity_of(place, inputs)
    solids = solids_of(inputs, place)
    job, records, left_out = {"rate": RATE, "gravity": gravity, "people": []}, {}, []
    (out / "clips").mkdir(parents=True)
    for single in cast["characters"]:
        if f"clip_{single.get('doing')}" not in rig:
            left_out.append(f"{single['name']}: its clip {single.get('doing')!r} is not in the rig")
            continue
        worlds = clip_frames(rig, single["doing"], kept)
        ground, under = ground_of(solids, worlds, own_frame(single["at"], single.get("turn", 0.0)))
        if not len(ground):
            left_out.append(f"{single['name']}: no solid of the place within {REACH} m of its clip's path to stand on")
            continue
        mass = mass_of(single, standing_height(rig))
        mine = weighed(segments, mass["kg"])
        targets = out / "clips" / f"{single['name']}.npz"
        np.savez_compressed(targets, world=worlds, ground=ground)
        job["people"].append({"name": single["name"], "segments": mine, "targets": str(targets), "gains": gains(mine)})
        records[single["name"]] = {"clip": single["doing"], "at": single["at"], "turn": single.get("turn", 0.0),
                                   "mass": mass, "ground": {"solids": under, "triangles": len(ground)},
                                   "segments": {segment["name"]: round(segment["mass"], 3) for segment in mine}}
    if cast.get("crowd"):
        left_out.append(f"{cast['crowd']['name']}: a crowd has no sim bodies (crowds are retiring, #56)")
    run = {"engine": None, "people": {}}
    if job["people"]:
        (out / "job.json").write_text(json.dumps(job))
        run = ran(out / "job.json", out / "run.json")
    (out / "measures").mkdir()
    for name, entry in run["people"].items():
        (out / "measures" / f"{name}.json").write_text(json.dumps(entry["frames"]))
        records[name]["measures"] = measured(entry["frames"], records[name]["mass"]["kg"], gravity)
    write_layer(out / LAYER, place, job["people"], run["people"], records)
    shutil.rmtree(out / "clips")
    (out / "job.json").unlink(missing_ok=True)
    (out / RECORD).write_text(json.dumps({"place": place, "on": body, "gravity": gravity, "engine": run["engine"],
                                          "rate": RATE, "bodies": records, "left out": left_out}, indent=1))


# --- the measures and gates ----------------------------------------------------------------------------------------

def angle_between(one, other):
    """The angle (degrees) between two rotations given as rotation vectors in degrees."""
    from scipy.spatial.transform import Rotation
    turn = Rotation.from_rotvec(np.radians(one)) * Rotation.from_rotvec(np.radians(other)).inv()
    return np.degrees(turn.magnitude())


def landings(frames, weight):
    """Each landed foot's height over its ground (metres), frame by frame past SETTLE: a foot the ground pushes up with
    at least CONTACT of the weight."""
    return [height for frame in frames[int(SETTLE * RATE):] for height, push in frame["feet"].values()
            if push >= CONTACT * weight and height is not None]


def measured(frames, kg, gravity):
    """A run's gate numbers: its deepest point into its ground, each landed foot's height off it, the mean upward push
    over its weight, the mean and worst angle off the clip (frames past SETTLE), the largest joint torque and the root
    helper's largest and mean force."""
    read = frames[int(SETTLE * RATE):]
    off = np.array([angle_between(frame["angles"], frame["targets"]) for frame in read])
    push = np.mean([frame["ground"][1] for frame in read])
    landed = np.abs(landings(frames, kg * gravity))
    helper = [np.linalg.norm(frame["helper"][:3]) for frame in read]
    return {"deepest": round(-min(0.0, min(frame["lowest"] for frame in frames if frame["lowest"] is not None)), 4),
            "landings": len(landed), "mean foot off ground m": round(float(landed.mean()), 4) if len(landed) else None,
            "worst foot off ground m": round(float(landed.max()), 4) if len(landed) else None,
            "weight N": round(kg * gravity, 2), "mean push N": round(float(push), 2),
            "push over weight": round(float(push / (kg * gravity)), 4),
            "mean off clip deg": round(float(off.mean()), 3), "worst off clip deg": round(float(off.max()), 3),
            "largest torque Nm": round(float(max(np.abs(frame["torques"]).max() for frame in read)), 2),
            "largest helper N": round(float(max(helper)), 2), "mean helper N": round(float(np.mean(helper)), 2)}


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
    """Fail a body whose joints are off its clip's by more than FOLLOWED degrees on the mean."""
    bodies = bodies_of(output)
    faults = [f"{name}: {body['measures']['mean off clip deg']:.2f} degrees off its clip on the mean"
              for name, body in bodies.items() if body["measures"]["mean off clip deg"] > FOLLOWED]
    return verdict("follows", faults, f"{len(bodies)} bodies, each within {FOLLOWED} degrees of its clip on the mean",
                   {"bodies": len(bodies)})


def output_faults(folder):
    folder = pathlib.Path(folder)
    found = [f"no {name}" for name in (RECORD, LAYER) if not (folder / name).exists()]
    if not found and not bodies_of(folder):
        found.append("no sim body: the cast names no character whose clip the rig holds")
    return found


CONTRACT = contracts.Contract("sim-body", 1, output_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("on floor", judge_on_floor), checks.Check("lands", judge_lands),
          checks.Check("carries", judge_carries),
          checks.Check("follows", judge_follows))


# --- the layer -----------------------------------------------------------------------------------------------------

def write_layer(path, place, people, runs, records):
    """layers/sim_bodies.usda: each body under its character's prim, a guide Xform a segment (its UsdPhysics mass,
    centre and box, its pose every frame in the character's frame) and a spherical joint at every ball joint."""
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics
    from scipy.spatial.transform import Rotation
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(path))
    layer.timeCodesPerSecond = layer.framesPerSecond = RATE
    stage = Usd.Stage.Open(layer)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    for person in people:
        frames = runs[person["name"]]["frames"]
        root = f"/{place}/Characters/{person['name']}/SimBody"
        for prim in (f"/{place}", f"/{place}/Characters", f"/{place}/Characters/{person['name']}"):
            stage.OverridePrim(prim)
        body = UsdGeom.Xform.Define(stage, root)
        UsdGeom.Imageable(body).CreatePurposeAttr(UsdGeom.Tokens.guide)
        UsdPhysics.ArticulationRootAPI.Apply(body.GetPrim())
        body.GetPrim().SetCustomDataByKey("score:mass", records[person["name"]]["mass"])
        for index, segment in enumerate(person["segments"]):
            part = UsdGeom.Xform.Define(stage, f"{root}/{segment['name']}")
            UsdPhysics.RigidBodyAPI.Apply(part.GetPrim())
            mass = UsdPhysics.MassAPI.Apply(part.GetPrim())
            mass.CreateMassAttr(segment["mass"])
            mass.CreateCenterOfMassAttr(Gf.Vec3f(*segment["com"]))
            mass.CreateDiagonalInertiaAttr(Gf.Vec3f(*np.linalg.eigvalsh(np.asarray(segment["inertia"]))))
            box = UsdGeom.Cube.Define(stage, f"{root}/{segment['name']}/box")
            box.AddTranslateOp().Set(Gf.Vec3d(*segment["box"][0]))
            box.AddScaleOp().Set(Gf.Vec3f(*segment["box"][1]))
            UsdPhysics.CollisionAPI.Apply(box.GetPrim())
            moved = part.AddTransformOp()
            for code, frame in enumerate(frames):
                pose = np.asarray(frame["poses"][index])
                matrix = np.eye(4)
                matrix[:3, :3], matrix[:3, 3] = Rotation.from_quat(pose[3:]).as_matrix(), pose[:3]
                moved.Set(Gf.Matrix4d(matrix.T.tolist()), code)
            if segment["parent"] >= 0:
                joint = UsdPhysics.SphericalJoint.Define(stage, f"{root}/{segment['name']}/joint")
                local = np.asarray(segment["local"])
                quat = Rotation.from_matrix(local[:3, :3]).as_quat()
                joint.CreateBody0Rel().SetTargets([f"{root}/{person['segments'][segment['parent']]['name']}"])
                joint.CreateBody1Rel().SetTargets([f"{root}/{segment['name']}"])
                joint.CreateLocalPos0Attr(Gf.Vec3f(*local[:3, 3]))
                joint.CreateLocalRot0Attr(Gf.Quatf(float(quat[3]), *map(float, quat[:3])))
    layer.Save()
