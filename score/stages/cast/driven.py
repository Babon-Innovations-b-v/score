"""A character driven by its sim body (#65, PRD #56): the characters layer's make (layer.py's, then `make` here) has
each person's skeleton play its sim body's simulated motion, so its skin and its look's clothes follow the physics,
and lays the sim body itself beside. Kept out of layer.py, which the cast and scene-clips rows import: they stay
unmoved by it.

    drive     the person's dressed body plays a SkelAnimation of its own (<person>/SimDriven) in place of its clip:
              at every clip frame the sim ran, each SOMA joint the sim body has a segment for turns as its segment did
              against its parent's (Hips against the clip's Root), and Hips stands where the sim's stood, times the
              body's size over the size the sim body was built at (sim_bodies.json `size`: the person's own build,
              so 1, but for a sim body built at the rig's size with no built body taken); the joints
              with no segment (SIM_LESS), every translation but Hips', the clip's blend shapes, and every frame after
              the sim's last keep the clip's values. Started where the person's clip starts.
    sim body  the sim-body row's layer, copied into the characters layer's assets and referenced under the person
              (<person>/SimBody, a guide) at the same start, in the skeleton's frame (the asset's Turned: the sim runs
              in the rig's own frame, which the asset turns)
    keeps     a person the sim body did not run (no sim-body output taken, its clip not in the rig, left out by the
              sim), a person held still and the crowd keep their clip, and characters.json and the prim's
              score:motion say why
    gate      on its sim body   each driven person's foot joints (FEET) stay within FEET_WITHIN of its sim body's
                                foot segments in every simulated frame, measured on the laid layer
"""
import json
import pathlib
import shutil

import numpy as np

from score import checks
from score.stages.cast import layer

SIM_ROW = "sim-body"
CLIPS_ROW = "people-clips-made"
SIM_LAYER = "layers/sim_bodies.usda"  # the sim-body row's (sim_body.LAYER)
SIM_RECORD = "sim_bodies.json"  # the sim-body row's (sim_body.RECORD)
SIM_ASSET = "assets/characters/sim_bodies.usda"
FEET = ("LeftFoot", "RightFoot")
FEET_WITHIN = 0.05  # metres
TRAVELLING = "Hips"  # the joint whose translation carries the clip's travel (prop_build.TRAVELLING_JOINT)


def sim_of(inputs, out):
    """The sim-body output's bodies with their measured frames, its layer copied into the layer's assets; None when
    no sim-body output (or no rig) was taken."""
    if SIM_ROW not in inputs or CLIPS_ROW not in inputs:
        return None
    folder = pathlib.Path(inputs[SIM_ROW])
    (out / SIM_ASSET).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(folder / SIM_LAYER, out / SIM_ASSET)
    bodies = json.loads((folder / SIM_RECORD).read_text())["bodies"]
    frames = {name: json.loads((folder / "measures" / f"{name}.json").read_text()) for name in bodies
              if (folder / "measures" / f"{name}.json").is_file()}
    return {"bodies": bodies, "frames": frames, "rig": dict(np.load(pathlib.Path(inputs[CLIPS_ROW]) / "rig.npz"))}


def kept_clip(single, sim):
    """Why a person keeps its clip, or None when its sim body drives it."""
    if sim is None:
        return "no sim-body output (with its rig) taken"
    if single.get("held"):
        return "held still by its cast"
    if single["name"] not in sim["frames"]:
        return "its sim body was not run (sim_bodies.json's `left out` says why)"
    return None


def pose_matrix(pose):
    """A sim pose (x, y, z, qx, qy, qz, qw) as a 4 x 4."""
    from scipy.spatial.transform import Rotation
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = Rotation.from_quat(pose[3:]).as_matrix(), pose[:3]
    return found


def size_over_sim(skeleton_bind, joint_names, rig, body):
    """The body's size against the size its sim body was built at: its Hips' bind height over the rig's (prop_build's
    scale), over the sim body's own (sim_bodies.json `size`)."""
    rig_names = [str(name) for name in rig["names"]]
    hips, rig_hips = joint_names.index(TRAVELLING), rig_names.index(TRAVELLING)
    size = float(skeleton_bind[hips][3][1]) / float(rig["bind"][rig_hips][1, 3])
    return size / float(body["size"]["of the rig"])


def driven_locals(poses, segments, parents, joint_names, root_local, size):
    """One frame's local transforms of the joints the sim body has a segment for ({joint index: 4 x 4}): each
    segment's world against its parent segment's, Hips' against the clip's Root, its height sized."""
    worlds = {name: pose_matrix(np.asarray(pose)) for name, pose in zip(segments, poses)}
    found = {}
    for joint, name in enumerate(joint_names):
        if name not in worlds:
            continue
        parent = joint_names[parents[joint]] if parents[joint] >= 0 else None
        above = worlds[parent] if parent in worlds else (root_local if parent else np.eye(4))
        local = np.linalg.inv(above) @ worlds[name]
        if name == TRAVELLING:
            local[1, 3] = size * local[1, 3]
        found[joint] = local
    return found


def joint_parents(tokens):
    """Each joint's parent index from the skeleton's joint paths (-1 for a root)."""
    paths = [str(token) for token in tokens]
    return [paths.index(path.rpartition("/")[0]) if "/" in path else -1 for path in paths]


def write_driven(stage, path, source, sim, single, start_frames):
    """<path>/SimDriven: the clip's SkelAnimation with every simulated frame's joints the sim body's (driven_locals),
    written at the times the person plays them; the skeleton set to play it. Returns the joints that keep the clip."""
    from pxr import Gf, UsdSkel, Vt
    from scipy.spatial.transform import Rotation
    tokens = source.GetJointsAttr().Get()
    names = [str(token).rpartition("/")[2] for token in tokens]
    parents = joint_parents(tokens)
    skeleton = UsdSkel.Skeleton(source.GetPrim().GetStage().GetPrimAtPath("/Character/Turned/Skeleton"))
    bind = skeleton.GetBindTransformsAttr().Get()
    segments = list(sim["bodies"][single["name"]]["segments"])
    frames = sim["frames"][single["name"]]
    hips = names.index(TRAVELLING)
    size = size_over_sim(bind, names, sim["rig"], sim["bodies"][single["name"]])
    animation = UsdSkel.Animation.Define(stage, f"{path}/SimDriven")
    animation.CreateJointsAttr(tokens)
    animation.CreateScalesAttr(source.GetScalesAttr().Get())
    turns, places = animation.CreateRotationsAttr(), animation.CreateTranslationsAttr()
    shapes = source.GetBlendShapesAttr().Get()
    weights = animation.CreateBlendShapeWeightsAttr() if shapes else None
    if shapes:
        animation.CreateBlendShapesAttr(shapes)
    for time in source.GetRotationsAttr().GetTimeSamples():
        rotations = list(source.GetRotationsAttr().Get(time))
        translations = list(source.GetTranslationsAttr().Get(time))
        if int(round(time)) < len(frames):
            root = np.eye(4)
            if parents[hips] >= 0:
                turn = rotations[parents[hips]]
                root[:3, :3] = Rotation.from_quat([*turn.GetImaginary(), turn.GetReal()]).as_matrix()
                root[:3, 3] = translations[parents[hips]]
            for joint, local in driven_locals(frames[int(round(time))]["poses"], segments, parents, names, root,
                                              size).items():
                quat = Rotation.from_matrix(local[:3, :3]).as_quat()
                rotations[joint] = Gf.Quatf(float(quat[3]), *map(float, quat[:3]))
                if joint == hips:
                    translations[joint] = Gf.Vec3f(*map(float, local[:3, 3]))
        turns.Set(Vt.QuatfArray(rotations), time - start_frames)
        places.Set(Vt.Vec3fArray(translations), time - start_frames)
        if shapes:
            weights.Set(source.GetBlendShapeWeightsAttr().Get(time), time - start_frames)
    stage.OverridePrim(f"{path}/Turned/Skeleton").CreateRelationship("skel:animationSource").SetTargets(
        [animation.GetPath()])
    return [name for name in names if name not in segments]


def lay_sim_body(stage, path, place, name, turned, start_frames):
    """The sim body referenced from the copied sim layer under the person, in the skeleton's frame (`turned`, the
    asset's Turned transform) and at the person's start."""
    from pxr import Sdf, UsdGeom
    prim = UsdGeom.Xform.Define(stage, f"{path}/SimBody").GetPrim()
    prim.GetReferences().AddReference(Sdf.Reference(f"../{SIM_ASSET}", f"/{place}/Characters/{name}/SimBody",
                                                    Sdf.LayerOffset(-start_frames)))
    UsdGeom.Xformable(prim).AddTransformOp().Set(turned)


def drive(stage, path, place, single, asset, sim, start_frames):
    """The person's skeleton played from its sim body and the sim body laid beside it (when it has one); what moves
    it, for characters.json and the prim's score:motion."""
    from pxr import Usd, UsdGeom, UsdSkel
    why = kept_clip(single, sim)
    if why is None and f"clip_{single['doing']}" not in sim["rig"]:
        why = f"its clip {single['doing']!r} is not in the rig"
    if why is not None:
        motion = {"by": "its clip", "why": why}
    else:
        body = Usd.Stage.Open(str(asset))
        source = UsdSkel.Animation(body.GetPrimAtPath(f"/Character/Animations/{single['doing']}"))
        kept = write_driven(stage, path, source, sim, single, start_frames)
        turned = UsdGeom.Xformable(body.GetPrimAtPath("/Character/Turned")).GetLocalTransformation()
        lay_sim_body(stage, path, place, single["name"], turned, start_frames)
        motion = {"by": "its sim body", "frames": len(sim["frames"][single["name"]]), "start": start_frames,
                  "clip keeps": kept}
    stage.GetPrimAtPath(path).SetCustomDataByKey("score:motion", motion["by"] + (f": {why}" if why else ""))
    return motion


def laid_from(prim, layer_path):
    """A laid person's body asset and its clip's start in frames, read off its reference (cast.py's `referenced`)."""
    reference = prim.GetMetadata("references").GetAddedOrExplicitItems()[0]
    return (pathlib.Path(layer_path).parent / reference.assetPath).resolve(), -reference.layerOffset.offset


def drive_people(stage, layer_path, place, people, looks, sim):
    """Every laid person driven by its sim body or kept on its clip (drive), into its `looks` entry's `motion`."""
    for single in people:
        if "missing" in looks.get(single["name"], {"missing": True}):
            continue
        path = f"/{place}/Characters/{single['name']}"
        asset, start = laid_from(stage.GetPrimAtPath(path), layer_path)
        looks[single["name"]]["motion"] = drive(stage, path, place, single, asset, sim, start)


def make(inputs, out, seed, params):
    """The characters layer (layer.make), each person then moved by its sim body or kept on its clip, said why in
    characters.json."""
    from pxr import Usd
    layer.make(inputs, out, seed, params)
    cast = json.loads((pathlib.Path(inputs["cast"]) / "cast.json").read_text())
    record = json.loads((out / layer.RECORD).read_text())
    stage = Usd.Stage.Open(str(out / layer.LAYER))
    drive_people(stage, out / layer.LAYER, cast["place"], cast["characters"], record["looks"], sim_of(inputs, out))
    if cast.get("crowd") and cast["crowd"]["name"] in record["looks"]:
        record["looks"][cast["crowd"]["name"]]["motion"] = {"by": "its clip",
                                                           "why": "a crowd has no sim bodies (retiring, #56)"}
    stage.GetRootLayer().Save()
    (out / layer.RECORD).write_text(json.dumps(record, indent=1))


# --- the gate ------------------------------------------------------------------------------------------------------

def feet_off(layer, place, name, motion):
    """The farthest any foot joint of a driven person stands from its sim body's foot segment over the simulated
    frames (metres), measured on the laid layer."""
    from pxr import Usd, UsdGeom, UsdSkel
    stage = Usd.Stage.Open(str(layer))
    path = f"/{place}/Characters/{name}"
    cache = UsdSkel.Cache()
    cache.Populate(UsdSkel.Root(stage.GetPrimAtPath(path)), Usd.TraverseInstanceProxies())
    query = cache.GetSkelQuery(UsdSkel.Skeleton(stage.GetPrimAtPath(f"{path}/Turned/Skeleton")))
    names = [str(token).rpartition("/")[2] for token in query.GetJointOrder()]
    worst = 0.0
    for frame in range(motion["frames"]):
        time = frame - motion["start"]
        joints = query.ComputeJointWorldTransforms(UsdGeom.XformCache(time))
        xforms = UsdGeom.XformCache(time)
        for foot in FEET:
            skin = joints[names.index(foot)].ExtractTranslation()
            sim = xforms.GetLocalToWorldTransform(stage.GetPrimAtPath(f"{path}/SimBody/{foot}")).ExtractTranslation()
            worst = max(worst, float((skin - sim).GetLength()))
    return worst


def judge_on_its_sim_body(output, inputs, evidence):
    """Fail a driven person whose feet stand more than FEET_WITHIN off its sim body's in any simulated frame; name
    every person that keeps its clip."""
    record = json.loads((pathlib.Path(output) / "characters.json").read_text())
    measures, faults, kept = {}, [], []
    for name, look in record["looks"].items():
        motion = look.get("motion")
        if not motion:
            continue
        if motion["by"] != "its sim body":
            kept.append(f"{name} keeps its clip: {motion['why']}")
            continue
        measures[name] = round(feet_off(pathlib.Path(output) / layer.LAYER, record["place"], name, motion), 4)
        if measures[name] > FEET_WITHIN:
            faults.append(f"{name}: a foot {measures[name]:.3f} m off its sim body's")
    reason = ("; ".join(faults[:3]) if faults else
              f"{len(measures)} driven by their sim body, feet within {FEET_WITHIN} m of it; {len(kept)} keep their clip")
    return checks.Verdict("on its sim body", checks.FAIL if faults else checks.PASS, reason,
                          {"driven": len(measures), "worst foot m": max(measures.values(), default=0.0)},
                          {"worst foot m": "lower"}, tuple(faults) + tuple(kept))


CHECKS = (*layer.CHECKS, checks.Check("on its sim body", judge_on_its_sim_body))
