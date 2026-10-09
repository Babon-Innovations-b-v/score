"""Turn one built character (a skinned, animated glTF binary from tools/characters/people/) into an OpenUSD asset with
UsdSkel: the framework's canonical form of a character, which every place's stage references as often as it is cast.

    .venv/bin/python tools/characters/skel_usd.py <character.glb> --out <folder> [--seconds 12]

The asset `<out>/<character>.usdc`, its maps in `<out>/textures/`:

    /Character                 SkelRoot, the asset's default prim; the cast's transform goes on it
      Turned                   the file's own turn (the body model builds people facing +z; a laid character faces -z)
        Skeleton               the file's joints, bind and rest transforms; `skel:animationSource` picks the clip
        Body/<node>/<part>     one skinned mesh per primitive of each mesh node of the file (`far`, `person`,
                               `work_navy`, `head_f2`, ...), every one bound to the Skeleton; the cast shows the
                               nodes a character wears and hides the rest
      Animations/<clip>        one SkelAnimation per clip of the file, at the file's 30 frames a second
      Looks/<material>         UsdPreviewSurface per material of the file: its picture, or its flat colour

A clip that runs round is repeated to fill `--seconds`, so a character the cast starts part-way into its clip (a
time offset on its reference) still moves for the whole of a review's walk; a clip that plays once (clips.ONCE in
the people tools: lifting, the car door) is written once and holds its last frame.

Nothing is guessed: the joints, weights (four a vertex, as the file has them), bind matrices and keys are the file's
own, read with numpy and written with usd-core (Pixar's OpenUSD, Apache 2.0 with a trademark clause).
"""
import argparse
import json
import pathlib
import struct

import numpy as np
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, UsdSkel, Vt

RATE = 30.0
SECONDS = 12.0
# The clips that play once and hold, by the name they carry in the file (tools/characters/people/clips.py ONCE).
ONCE = ("lifting", "door")
# The mesh nodes a character wears when the cast names nothing: a named person's clothes, a crew member's work suit.
DEFAULT_WORN = ("person", "person_cap", "work")
# The pictures a file may carry, by type, and the ending each is written with.
PICTURE_ENDINGS = {"image/png": ".png", "image/jpeg": ".jpg"}

_COMPONENTS = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


# --- reading the file ---------------------------------------------------------------------------------------------

def read_glb(path):
    """The file as (document, its binary chunk)."""
    data = pathlib.Path(path).read_bytes()
    length = struct.unpack("<I", data[12:16])[0]
    document = json.loads(data[20:20 + length])
    rest = data[20 + length:]
    return document, rest[8:8 + struct.unpack("<I", rest[:4])[0]]


def accessor(document, blob, index):
    """One accessor's values as an array of (count, width), or (count,) for scalars."""
    found = document["accessors"][index]
    view = document["bufferViews"][found["bufferView"]]
    kind = np.dtype(_COMPONENTS[found["componentType"]])
    width = _WIDTH[found["type"]]
    start = view.get("byteOffset", 0) + found.get("byteOffset", 0)
    stride = view.get("byteStride", kind.itemsize * width)
    if stride != kind.itemsize * width:
        raise ValueError(f"accessor {index}: interleaved data is not read here")
    values = np.frombuffer(blob, kind, found["count"] * width, start)
    return values.reshape(found["count"], width) if width > 1 else values


def joint_paths(document, joints):
    """Each joint's UsdSkel path ("Root/Hips/Spine1"), in the skin's order, which puts every parent first."""
    parent = {child: number for number, node in enumerate(document["nodes"]) for child in node.get("children", [])}
    names = {}
    for joint in joints:
        trail, node = [], joint
        while node in joints:
            trail.append(document["nodes"][node]["name"])
            node = parent.get(node)
        names[joint] = "/".join(reversed(trail))
    order = {joint: place for place, joint in enumerate(joints)}
    for joint in joints:
        above = parent.get(joint)
        if above in order and order[above] > order[joint]:
            raise ValueError("the skin lists a joint before its parent; UsdSkel needs parents first")
    return [names[joint] for joint in joints]


def matrix(values):
    """A glTF matrix (16 numbers, columns first) as USD's (rows first, translation in the last row): the same list."""
    return Gf.Matrix4d(*[float(value) for value in values])


def local_matrix(node):
    """A node's own transform as USD's matrix."""
    if "matrix" in node:
        return matrix(node["matrix"])
    rotation = node.get("rotation", [0, 0, 0, 1])
    turn = Gf.Matrix4d().SetRotate(Gf.Quatd(rotation[3], rotation[0], rotation[1], rotation[2]))
    scale = Gf.Matrix4d().SetScale(Gf.Vec3d(*node.get("scale", [1, 1, 1])))
    move = Gf.Matrix4d().SetTranslate(Gf.Vec3d(*node.get("translation", [0, 0, 0])))
    return scale * turn * move


# --- the clips ----------------------------------------------------------------------------------------------------

def clip_keys(document, blob, animation, joints):
    """One clip's keys per joint: (times, rotations as x y z w, translations), the rest pose where it has none."""
    nodes = document["nodes"]
    times = None
    rotations = np.array([nodes[joint].get("rotation", [0, 0, 0, 1]) for joint in joints], np.float64)
    translations = np.array([nodes[joint].get("translation", [0, 0, 0]) for joint in joints], np.float64)
    channels = {"rotation": {}, "translation": {}}
    for channel in animation["channels"]:
        target = channel["target"]
        if target["node"] not in joints or target["path"] not in channels:
            continue
        sampler = animation["samplers"][channel["sampler"]]
        if sampler.get("interpolation", "LINEAR") != "LINEAR":
            raise ValueError(f"{animation['name']}: only linear keys are read")
        keyed = accessor(document, blob, sampler["input"]).astype(np.float64)
        times = keyed if times is None else times
        if len(keyed) != len(times) or not np.allclose(keyed, times):
            raise ValueError(f"{animation['name']}: every channel of a clip is expected on the same keys")
        channels[target["path"]][joints.index(target["node"])] = accessor(document, blob, sampler["output"])
    frames = len(times)
    rotation_keys = np.repeat(rotations[None], frames, 0)
    translation_keys = np.repeat(translations[None], frames, 0)
    for joint, values in channels["rotation"].items():
        rotation_keys[:, joint] = values
    for joint, values in channels["translation"].items():
        translation_keys[:, joint] = values
    return times, rotation_keys, translation_keys


def repeated(times, keys, seconds, once):
    """The clip's frames laid end to end to fill `seconds` (a clip that runs round drops its last frame, which is its
    first), or once as it is; with the time of each in frames at RATE."""
    if once:
        return np.round(times * RATE), keys
    cycle = keys[:-1] if len(keys) > 2 and np.allclose(keys[0], keys[-1], atol=1e-4) else keys
    frames = int(np.ceil(seconds * RATE)) + 1
    picks = np.arange(frames) % len(cycle)
    return np.arange(frames, dtype=np.float64), cycle[picks]


def write_clip(stage, path, joint_names, times, rotations, translations):
    """One SkelAnimation: every joint's turn and place at every frame, scale one."""
    animation = UsdSkel.Animation.Define(stage, path)
    animation.CreateJointsAttr(Vt.TokenArray(joint_names))
    turn_attribute = animation.CreateRotationsAttr()
    place_attribute = animation.CreateTranslationsAttr()
    animation.CreateScalesAttr(Vt.Vec3hArray([Gf.Vec3h(1, 1, 1)] * len(joint_names)))
    for frame, turns, places in zip(times, rotations, translations):
        turn_attribute.Set(Vt.QuatfArray([Gf.Quatf(float(w), float(x), float(y), float(z)) for x, y, z, w in turns]),
                           float(frame))
        place_attribute.Set(Vt.Vec3fArray([Gf.Vec3f(*map(float, place)) for place in places]), float(frame))


# --- the body -----------------------------------------------------------------------------------------------------

def write_picture(document, blob, image, textures, stem):
    """A picture carried in the file, written out as it is (PNG or JPEG) beside the asset; its asset-relative path."""
    found = document["images"][image]
    view = document["bufferViews"][found["bufferView"]]
    start = view.get("byteOffset", 0)
    if found.get("mimeType") not in PICTURE_ENDINGS:
        raise ValueError(f"picture {image} is {found.get('mimeType')}, only PNG and JPEG are carried")
    target = textures / f"{stem}_{image}{PICTURE_ENDINGS[found['mimeType']]}"
    target.write_bytes(blob[start:start + view["byteLength"]])
    return f"./textures/{target.name}"


def write_look(stage, path, material, picture):
    """A material as UsdPreviewSurface: its picture through the mesh's `st`, or its flat colour."""
    look = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    pbr = material.get("pbrMetallicRoughness", {})
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(pbr.get("metallicFactor", 0.0)))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(pbr.get("roughnessFactor", 1.0)))
    if picture is None:
        colour = pbr.get("baseColorFactor", [0.8, 0.8, 0.8, 1.0])
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*colour[:3]))
    else:
        reader = UsdShade.Shader.Define(stage, f"{path}/uv")
        reader.CreateIdAttr("UsdPrimvarReader_float2")
        reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
        texture = UsdShade.Shader.Define(stage, f"{path}/base_color")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(picture)
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
            reader.CreateOutput("result", Sdf.ValueTypeNames.Float2))
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
    look.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    look.GetPrim().CreateAttribute("score:part", Sdf.ValueTypeNames.String).Set(material.get("name", ""))
    return look


def write_part(stage, path, document, blob, primitive, skeleton, look):
    """One primitive as a skinned mesh: points, normals, texture coordinates, triangles and four joint weights a
    point, bound to the skeleton and its look."""
    attributes = primitive["attributes"]
    points = accessor(document, blob, attributes["POSITION"])
    count = len(points)
    triangles = (accessor(document, blob, primitive["indices"]) if "indices" in primitive
                 else np.arange(count)).astype(np.int64)
    if primitive.get("mode", 4) != 4:
        raise ValueError(f"{path}: only triangles are read")
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.ascontiguousarray(points, np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * (len(triangles) // 3)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(triangles.astype(np.int32)))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    if "NORMAL" in attributes:
        mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(
            np.ascontiguousarray(accessor(document, blob, attributes["NORMAL"]), np.float32)))
        mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    if "TEXCOORD_0" in attributes:
        coordinates = accessor(document, blob, attributes["TEXCOORD_0"]).astype(np.float32).copy()
        coordinates[:, 1] = 1.0 - coordinates[:, 1]  # glTF counts down from the top, USD up from the bottom
        UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                                UsdGeom.Tokens.vertex).Set(Vt.Vec2fArray.FromNumpy(coordinates))
    extent = UsdGeom.Boundable.ComputeExtentFromPlugins(mesh, Usd.TimeCode.Default())
    mesh.CreateExtentAttr(extent)
    binding = UsdSkel.BindingAPI.Apply(mesh.GetPrim())
    binding.CreateSkeletonRel().SetTargets([skeleton])
    joints = accessor(document, blob, attributes["JOINTS_0"]).astype(np.int32)
    weights = accessor(document, blob, attributes["WEIGHTS_0"]).astype(np.float32)
    binding.CreateJointIndicesPrimvar(False, 4).Set(Vt.IntArray.FromNumpy(joints.reshape(-1)))
    binding.CreateJointWeightsPrimvar(False, 4).Set(Vt.FloatArray.FromNumpy(weights.reshape(-1)))
    binding.CreateGeomBindTransformAttr(Gf.Matrix4d(1))
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(look)


def prim_name(text):
    """A name USD accepts for a prim."""
    cleaned = "".join(letter if letter.isalnum() or letter == "_" else "_" for letter in text) or "unnamed"
    return cleaned if not cleaned[0].isdigit() else f"_{cleaned}"


# --- the way in ---------------------------------------------------------------------------------------------------

def convert(glb, out, seconds=SECONDS, worn=DEFAULT_WORN):
    """Write the character's asset under `out` and return its path; its name is the file's stem. The mesh nodes named
    in `worn` are shown and the rest hidden; with `worn` None every mesh is shown (an animal has no outfits)."""
    glb, out = pathlib.Path(glb), pathlib.Path(out)
    document, blob = read_glb(glb)
    if len(document.get("skins", [])) != 1:
        raise ValueError(f"{glb}: one skin expected, found {len(document.get('skins', []))}")
    skin = document["skins"][0]
    joints = list(skin["joints"])
    joint_names = joint_paths(document, joints)
    textures = out / "textures"
    textures.mkdir(parents=True, exist_ok=True)
    path = out / f"{glb.stem}.usdc"
    stage = Usd.Stage.CreateNew(str(path)) if not path.exists() else Usd.Stage.Open(str(path))
    stage.GetRootLayer().Clear()
    stage.SetTimeCodesPerSecond(RATE)
    stage.SetFramesPerSecond(RATE)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdSkel.Root.Define(stage, "/Character")
    stage.SetDefaultPrim(root.GetPrim())
    Usd.ModelAPI(root).SetKind(Kind.Tokens.component)
    scene_root = document["nodes"][document["scenes"][document.get("scene", 0)]["nodes"][0]]
    turned = UsdGeom.Xform.Define(stage, "/Character/Turned")
    turned.AddTransformOp().Set(local_matrix(scene_root))
    skeleton = UsdSkel.Skeleton.Define(stage, "/Character/Turned/Skeleton")
    skeleton.CreateJointsAttr(Vt.TokenArray(joint_names))
    inverse_binds = accessor(document, blob, skin["inverseBindMatrices"])
    skeleton.CreateBindTransformsAttr(Vt.Matrix4dArray([matrix(values).GetInverse() for values in inverse_binds]))
    skeleton.CreateRestTransformsAttr(Vt.Matrix4dArray([local_matrix(document["nodes"][joint]) for joint in joints]))
    UsdGeom.Scope.Define(stage, "/Character/Animations")
    clips = []
    lengths = {}
    for animation in document.get("animations", []):
        times, rotations, translations = clip_keys(document, blob, animation, joints)
        frames, turns = repeated(times, rotations, seconds, animation["name"] in ONCE)
        _, places = repeated(times, translations, seconds, animation["name"] in ONCE)
        name = prim_name(animation["name"])
        write_clip(stage, f"/Character/Animations/{name}", joint_names, frames, turns, places)
        clips.append(name)
        lengths[name] = float(times[-1] - times[0])
    if clips:
        UsdSkel.BindingAPI.Apply(skeleton.GetPrim()).CreateAnimationSourceRel().SetTargets(
            [Sdf.Path(f"/Character/Animations/{clips[0]}")])
    UsdGeom.Scope.Define(stage, "/Character/Looks")
    pictures = {}
    looks = []
    for number, material in enumerate(document.get("materials", [])):
        texture = material.get("pbrMetallicRoughness", {}).get("baseColorTexture")
        picture = None
        if texture is not None:
            image = document["textures"][texture["index"]]["source"]
            if image not in pictures:
                pictures[image] = write_picture(document, blob, image, textures, glb.stem)
            picture = pictures[image]
        looks.append(write_look(stage, f"/Character/Looks/m{number}_{prim_name(material.get('name', ''))}",
                                material, picture))
    UsdGeom.Scope.Define(stage, "/Character/Turned/Body")
    shown = []
    for node in document["nodes"]:
        if "mesh" not in node:
            continue
        name = prim_name(node.get("name", f"mesh{node['mesh']}"))
        holder = UsdGeom.Xform.Define(stage, f"/Character/Turned/Body/{name}")
        if worn is not None and name not in worn:
            holder.CreateVisibilityAttr(UsdGeom.Tokens.invisible)
        else:
            shown.append(name)
        for number, primitive in enumerate(document["meshes"][node["mesh"]]["primitives"]):
            part = document["materials"][primitive["material"]].get("name", "") if "material" in primitive else ""
            write_part(stage, f"/Character/Turned/Body/{name}/{prim_name(part)}_{number}", document, blob, primitive,
                       skeleton.GetPath(), looks[primitive.get("material", 0)])
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(float(np.ceil(seconds * RATE)))
    root.GetPrim().SetCustomDataByKey("score:clips", Vt.StringArray(clips))
    root.GetPrim().SetCustomDataByKey("score:worn", Vt.StringArray(shown))
    root.GetPrim().SetCustomDataByKey("score:clip_seconds", lengths)
    stage.GetRootLayer().Save()
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("glb", type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    parser.add_argument("--seconds", type=float, default=SECONDS)
    arguments = parser.parse_args()
    print(convert(arguments.glb, arguments.out, arguments.seconds))


if __name__ == "__main__":
    main()
