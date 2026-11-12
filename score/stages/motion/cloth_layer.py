"""The flag cloth written into the motion layer, and read back skinned (the motion row's flag cloth, cloth.py).

One run a flag model is written once, as overs off the place (`/FlagCloth_<model>`: never drawn, no `def`): its rig
(`Rig`: the joints, a pole joint standing at the model's origin and the cloth's joints under it, at rest), its skin
(`Skin`: each point's four joints and shares, UsdSkel's primvars) and its animation (`Wave`: each joint's turn and
place every frame, the run looped, over the layer's seconds and `phases` seconds past them). Each flag is made a
SkelRoot with a Skeleton of its own (`ClothRig`, referencing the rig) whose animation (`ClothRig/Wave`) references the
run's, shifted by the flag's own phase; its mesh references the skin and is bound to its own skeleton. Everything is
in the layer itself: the assembly copies layers/motion.usda alone (assembly.LAYERS), so nothing else is read.

    write(layer, runs, flags, rate)     the runs and the flags written into an open Sdf layer
    skinned_over(stage, path, codes)    a flag's mesh points as UsdSkel skins them at each time code
"""
import numpy as np

PROTOTYPE = "FlagCloth_{key}"
RIG = "ClothRig"
POLE = "pole"


def joint_names(count):
    """The pole joint, then the cloth's joints under it."""
    return [POLE, *(f"{POLE}/cloth_{number}" for number in range(count))]


def matrices(frames):
    """Column-vector 4 x 4 frames as USD's row-vector matrices."""
    from pxr import Gf
    return [Gf.Matrix4d(*np.asarray(frame).T.ravel().tolist()) for frame in frames]


def quaternions(rotations):
    """Unit quaternions (w, x, y, z) of rotation matrices (n x 3 x 3), each with w >= 0."""
    rotations = np.asarray(rotations, dtype=np.float64)
    trace = np.trace(rotations, axis1=1, axis2=2)
    found = np.zeros((len(rotations), 4))
    for number, (turn, total) in enumerate(zip(rotations, trace)):
        if total > 0.0:
            scale = 2.0 * np.sqrt(1.0 + total)
            found[number] = [0.25 * scale, (turn[2, 1] - turn[1, 2]) / scale, (turn[0, 2] - turn[2, 0]) / scale,
                             (turn[1, 0] - turn[0, 1]) / scale]
            continue
        axis = int(np.argmax(np.diag(turn)))
        other, third = (axis + 1) % 3, (axis + 2) % 3
        scale = 2.0 * np.sqrt(1.0 + turn[axis, axis] - turn[other, other] - turn[third, third])
        found[number, 0] = (turn[third, other] - turn[other, third]) / scale
        found[number, 1 + axis] = 0.25 * scale
        found[number, 1 + other] = (turn[other, axis] + turn[axis, other]) / scale
        found[number, 1 + third] = (turn[third, axis] + turn[axis, third]) / scale
    found *= np.where(found[:, :1] < 0.0, -1.0, 1.0)
    return found / np.linalg.norm(found, axis=1)[:, None]


def attribute(spec, name, kind, value, interpolation=None, element=None, uniform=False):
    """An attribute spec on a prim spec with its value (uniform: one for all time, as UsdSkel's joint lists are)."""
    from pxr import Sdf
    made = Sdf.AttributeSpec(spec, name, kind, Sdf.VariabilityUniform if uniform else Sdf.VariabilityVarying)
    if value is not None:
        made.default = value
    if interpolation:
        made.SetInfo("interpolation", interpolation)
    if element:
        made.SetInfo("elementSize", element)
    return made


def over(layer, path, kind=""):
    """The prim spec at `path`, made as an over (with `kind` as its type, where given) where the layer has none."""
    from pxr import Sdf
    spec = layer.GetPrimAtPath(path) or Sdf.CreatePrimInLayer(layer, path)
    if kind:
        spec.typeName = kind
    return spec


def write_run(layer, key, run):
    """One run's rig, skin and animation as overs at /FlagCloth_<key>."""
    from pxr import Gf, Sdf, Vt
    root = Sdf.Path(f"/{PROTOTYPE.format(key=key)}")
    joints = Vt.TokenArray(joint_names(len(run["rest"])))
    rest = matrices([np.eye(4), *run["rest"]])
    rig = over(layer, root.AppendChild("Rig"))
    attribute(rig, "joints", Sdf.ValueTypeNames.TokenArray, joints, uniform=True)
    attribute(rig, "bindTransforms", Sdf.ValueTypeNames.Matrix4dArray, Vt.Matrix4dArray(rest), uniform=True)
    attribute(rig, "restTransforms", Sdf.ValueTypeNames.Matrix4dArray, Vt.Matrix4dArray(rest), uniform=True)
    skin = over(layer, root.AppendChild("Skin"))
    attribute(skin, "primvars:skel:jointIndices", Sdf.ValueTypeNames.IntArray,
              Vt.IntArray(np.asarray(run["indices"]).ravel().tolist()), "vertex", run["indices"].shape[1])
    attribute(skin, "primvars:skel:jointWeights", Sdf.ValueTypeNames.FloatArray,
              Vt.FloatArray(np.asarray(run["shares"]).ravel().tolist()), "vertex", run["shares"].shape[1])
    attribute(skin, "primvars:skel:geomBindTransform", Sdf.ValueTypeNames.Matrix4d, Gf.Matrix4d(1.0))
    wave = over(layer, root.AppendChild("Wave"))
    attribute(wave, "joints", Sdf.ValueTypeNames.TokenArray, joints, uniform=True)
    moved = attribute(wave, "translations", Sdf.ValueTypeNames.Float3Array, None)
    turned = attribute(wave, "rotations", Sdf.ValueTypeNames.QuatfArray, None)
    attribute(wave, "scales", Sdf.ValueTypeNames.Half3Array, Vt.Vec3hArray([Gf.Vec3h(1.0)] * len(joints)))
    for code, frames in enumerate(run["frames"]):
        places = np.concatenate([np.zeros((1, 3)), frames[:, :3, 3]])
        turns = quaternions(np.concatenate([np.eye(3)[None], frames[:, :3, :3]]))
        layer.SetTimeSample(moved.path, float(code), Vt.Vec3fArray.FromNumpy(places.astype(np.float32)))
        layer.SetTimeSample(turned.path, float(code),
                            Vt.QuatfArray([Gf.Quatf(*map(float, turn)) for turn in turns]))
    return root


def write_flag(layer, root, flag, rate):
    """One flag made a SkelRoot with its own skeleton, its animation the run's from its phase on, its mesh bound."""
    from pxr import Sdf
    path = Sdf.Path(flag["prim"])
    over(layer, path, "SkelRoot")
    skeleton = Sdf.CreatePrimInLayer(layer, path.AppendChild(RIG))
    skeleton.specifier, skeleton.typeName = Sdf.SpecifierDef, "Skeleton"
    skeleton.referenceList.Prepend(Sdf.Reference(primPath=root.AppendChild("Rig")))
    skeleton.SetInfo("apiSchemas", Sdf.TokenListOp.Create(prependedItems=["SkelBindingAPI"]))
    animation = Sdf.CreatePrimInLayer(layer, path.AppendChild(RIG).AppendChild("Wave"))
    animation.specifier, animation.typeName = Sdf.SpecifierDef, "SkelAnimation"
    animation.referenceList.Prepend(Sdf.Reference(primPath=root.AppendChild("Wave"),
                                                  layerOffset=Sdf.LayerOffset(-flag["phase"] * rate)))
    source = Sdf.RelationshipSpec(skeleton, "skel:animationSource", custom=False)
    source.targetPathList.Prepend(animation.path)
    mesh = over(layer, Sdf.Path(flag["mesh"]))
    mesh.SetInfo("apiSchemas", Sdf.TokenListOp.Create(prependedItems=["SkelBindingAPI"]))
    mesh.referenceList.Prepend(Sdf.Reference(primPath=root.AppendChild("Skin")))
    bound = Sdf.RelationshipSpec(mesh, "skel:skeleton", custom=False)
    bound.targetPathList.Prepend(skeleton.path)


def write(layer, runs, flags, rate):
    """Every run (`runs`: {key: {"rest": joints x 4 x 4, "frames": [joints x 4 x 4 a time code], "indices",
    "shares"}}, in the flag model's own space) and every flag ({"prim", "mesh", "run", "phase" seconds}) written into
    the open layer; saved by the caller."""
    roots = {key: write_run(layer, key, run) for key, run in sorted(runs.items())}
    for flag in flags:
        write_flag(layer, roots[flag["run"]], flag, rate)


def skinned_over(stage, path, codes):
    """The points of the flag at `path` as UsdSkel skins them at each of `codes` (codes x points x 3, in its mesh's
    own space), read off the composed stage; None where nothing skins it."""
    from pxr import Usd, UsdSkel
    root = UsdSkel.Root(stage.GetPrimAtPath(path))
    if not root:
        return None
    cache = UsdSkel.Cache()
    cache.Populate(root, Usd.TraverseInstanceProxies())
    for binding in cache.ComputeSkelBindings(root, Usd.TraverseInstanceProxies()):
        skeleton = cache.GetSkelQuery(binding.GetSkeleton())
        for target in binding.GetSkinningTargets():
            points = target.GetPrim().GetAttribute("points")
            found = []
            for code in codes:
                moved = points.Get(code)
                transforms = skeleton.ComputeSkinningTransforms(code)
                if not target.ComputeSkinnedPoints(transforms, moved, code):
                    return None
                found.append(np.asarray(moved))
            return np.asarray(found)
    return None
