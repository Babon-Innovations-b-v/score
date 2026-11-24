"""A laid character as one skinned glTF for the scene package (scene_package.write; the 2099 prologue's leader, the
crowd and the walkers, 2026-11-20): what a game engine (2099's Unity, glTFast) imports as a skinned mesh playing its
clips. Converted from the laid USD with usd-core's UsdSkel queries, never from a file beside it, so a character laid
by `put` (a TRELLIS.2 player model rigged by tools/characters/still_rig, its `character.usdc`), by the cast stage's
characters layer (a dressed body, a sim body's own SkelAnimation) or as a crowd's PointInstancer prototype comes out
as the stage draws it.

The glTF (one per character, in the SkelRoot's own frame; scene.json's copy `matrix` stands it):

    node 0          the character (its SkelRoot): a copy's uneven stretch drawn in, and the SkelRoot's own moves
                    over time (a cast walker's route) as its played animation's translation and rotation channels
    node 1          the Skeleton's frame under the SkelRoot (the asset's `Turned`), its joints' parent
    nodes 2..       one node per joint, its rest transform its own, named as the joint's last path part
    mesh nodes      one per shown skinned Mesh (its far body and every body group not worn left out), a primitive per
                    look bound to its faces, each point's joints and weights the mesh's own (JOINTS_n / WEIGHTS_n,
                    four a set), its points in the SkelRoot's frame (the mesh's geomBindTransform and the
                    Skeleton's frame applied), so each joint's inverse bind matrix is its bind transform's in that
                    frame inverted
    skin 0          the joints in the Skeleton's order
    animations      every SkelAnimation under the character (its asset's clips, `Animations/<clip>`) and the one
                    its Skeleton plays when that one lies elsewhere (`Held`, a sim body's `SimDriven`): each keyed
                    from its own first sample (in seconds), a clip that runs round cut to one round
                    (score:clip_seconds), the rest whole
    materials       each bound look as scene_package.pbr reads it (factors, maps, glass); a palette recipe that
                    would need a bake is refused (Unconvertible): a character wears its own paint or flat colours

`about` (scene.json's object): `clips` {animation: seconds}, `plays` {animation, starts (the stage's second its first
key falls at: a crowd's phase is a start before 0), loops} or null (a character held still plays the clip its pose was
taken from, `lived`), and `check`: the glTF skinned in numpy at the animation the stage plays (`checked`: a held
character's still pose) against UsdSkel's own posed skin (ready/people.posed_body) at that time, in the
SkelRoot's frame, every point within CLOSE; its triangles against the USD's.
"""
import io
import sys

import numpy as np
from pxr import Usd, UsdGeom, UsdShade, UsdSkel

from score.stages import place_build
from score.stages.place_build import scene_package

sys.path.insert(0, str(place_build.REPO / "tools/characters"))
sys.path.insert(0, str(place_build.REPO / "tools/characters/people"))
import glb  # noqa: E402  (people/glb.py, the house's glTF writer)
import skel_usd  # noqa: E402  (its reader: read back what was written)

CLOSE = 1e-4  # metres: how far the glTF's skin may lie from UsdSkel's at the played key
ROUND = 1e-3  # frames: how near a sample must lie to a clip's round to be kept as its last
ON_THE_SPOT = ("walking",)  # clips whose feet stride on the spot: a body held from one walks no route, so stands


class Unconvertible(ValueError):
    """A character the package cannot carry as the stage draws it (scene.json's `left_out` names why)."""


# --- what is laid ---------------------------------------------------------------------------------------------------

def is_character(prim):
    """Whether a laid prim is a character: a SkelRoot, or a PointInstancer of SkelRoots (a crowd)."""
    if prim.IsA(UsdSkel.Root):
        return True
    if prim.IsA(UsdGeom.PointInstancer):
        targets = UsdGeom.PointInstancer(prim).GetPrototypesRel().GetTargets()
        return bool(targets) and all(prim.GetStage().GetPrimAtPath(path).IsA(UsdSkel.Root) for path in targets)
    return False


def copies_of(prim):
    """[(the SkelRoot drawn, the copy's name, its world transform row-major at its first time)]: the SkelRoot itself,
    or a crowd's every copy (`<crowd>_<n>`, its prototype and its instance transform)."""
    if prim.IsA(UsdSkel.Root):
        return [(prim, prim.GetName(), first_world(prim))]
    instancer = UsdGeom.PointInstancer(prim)
    stage = prim.GetStage()
    prototypes = [stage.GetPrimAtPath(path) for path in instancer.GetPrototypesRel().GetTargets()]
    world = np.asarray(instancer.ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    transforms = instancer.ComputeInstanceTransformsAtTime(Usd.TimeCode.Default(), Usd.TimeCode.Default())
    indices = instancer.GetProtoIndicesAttr().Get()
    return [(prototypes[index], f"{prim.GetName()}_{number}", np.asarray(transform) @ world)
            for number, (index, transform) in enumerate(zip(indices, transforms))]


def moved_times(prim):
    """The time codes the SkelRoot's own transform is sampled at (empty when it stands still)."""
    times = UsdGeom.Xformable(prim).GetTimeSamples()
    return list(times) if len(times) > 1 else []


def first_world(prim):
    """The SkelRoot's world transform (row-major) at its first sampled time, or its only one."""
    times = moved_times(prim)
    return np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(
        Usd.TimeCode(times[0]) if times else Usd.TimeCode.Default()))


# --- the skeleton and its skinned meshes ----------------------------------------------------------------------------

def binding_of(root):
    """The character's one skeleton binding (UsdSkel.Cache's); Unconvertible for none or several."""
    cache = UsdSkel.Cache()
    skel_root = UsdSkel.Root(root)
    cache.Populate(skel_root, Usd.TraverseInstanceProxies())
    bindings = cache.ComputeSkelBindings(skel_root, Usd.TraverseInstanceProxies())
    if len(bindings) != 1:
        raise Unconvertible(f"{len(bindings)} skeletons bound under it: one is converted")
    return cache, bindings[0]


def shown_targets(binding):
    """The binding's skinned meshes the stage shows, in its order (as ready/people.posed_body walks them)."""
    shown = []
    for target in binding.GetSkinningTargets():
        mesh_prim = target.GetPrim()
        if UsdGeom.Imageable(mesh_prim).ComputeVisibility() == UsdGeom.Tokens.invisible \
                or not mesh_prim.IsA(UsdGeom.Mesh) or not UsdGeom.Mesh(mesh_prim).GetPointsAttr().Get():
            continue
        shown.append(target)
    return shown


def influences_of(target, order, count):
    """Each point's joints (in the skeleton's order) and weights, `count` points, padded to a multiple of four
    influences with weight 0 and each point's weights summing to one: (joints (count x k), weights)."""
    indices, weights = target.ComputeVaryingJointInfluences(count)
    width = target.GetNumInfluencesPerComponent()
    joints = np.asarray(indices, dtype=np.int64).reshape(count, width)
    weights = np.asarray(weights, dtype=np.float64).reshape(count, width)
    own = target.GetJointOrder()
    if own:
        joints = np.array([order.index(str(name)) for name in own], dtype=np.int64)[joints]
    pad = -width % 4
    joints = np.hstack([joints, np.zeros((count, pad), dtype=np.int64)])
    weights = np.hstack([weights, np.zeros((count, pad))])
    weights /= np.maximum(weights.sum(axis=1, keepdims=True), 1e-12)
    return joints, weights


def mesh_corners(prim):
    """A Mesh's corners welded into vertices: (each vertex's point index, normal, texture coordinate or None, the
    triangles of vertices, each triangle's face)."""
    points, indices, triangles, faces, normals, uv = scene_package.drawn(prim)
    if normals is None:
        normals = scene_package.smooth_normals(points, indices, triangles)
    rows = np.hstack([indices[:, None].astype(np.float64), normals] + ([uv] if uv is not None else []))
    unique, vertex_of = np.unique(rows.round(7), axis=0, return_inverse=True)
    return (unique[:, 0].astype(np.int64), unique[:, 1:4], unique[:, 4:6] if uv is not None else None,
            vertex_of.reshape(-1)[triangles], faces)


# --- looks ----------------------------------------------------------------------------------------------------------

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
SLOTS = (("baseColorTexture", "diffuseColor"), ("normalTexture", "normal"), ("emissiveTexture", "emissiveColor"))


def picture_png(image):
    """A PIL picture as PNG bytes."""
    held = io.BytesIO()
    image.save(held, format="PNG")
    return held.getvalue()


def texture(contents, document, encoded, mime):
    """An encoded picture embedded in the buffer as a texture; its texture number."""
    document.setdefault("samplers", [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}])
    number = contents.picture(encoded, mime)
    document.setdefault("textures", []).append({"sampler": 0, "source": number})
    return len(document["textures"]) - 1


def map_texture(contents, document, pictures, source, image):
    """The texture of one map, embedded once a source (`pictures` holds each by its source): its own file's bytes
    when glTF reads its kind, else `image` (a PIL picture made from it) as PNG."""
    if source not in pictures:
        path = source[1] if source[0] != "metal_rough" else None
        if path is not None and path.suffix.lower() in MIME:
            pictures[source] = texture(contents, document, path.read_bytes(), MIME[path.suffix.lower()])
        else:
            pictures[source] = texture(contents, document, picture_png(image), "image/png")
    return pictures[source]


def material_of(look, contents, document, pictures):
    """A bound look as a glTF material (scene_package.pbr's reading), each map embedded once (`pictures`);
    Unconvertible for a recipe needing a bake."""
    read = scene_package.pbr(look)
    if read.get("bake"):
        raise Unconvertible(f"its look {scene_package.look_name(look)} is a palette recipe to bake")
    made = read["material"]
    factors = read.get("factors", {})
    metal = {"baseColorFactor": factors.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0]),
             "metallicFactor": factors.get("metallicFactor", 1.0 if made.metallicRoughnessTexture else 0.0),
             "roughnessFactor": factors.get("roughnessFactor", 1.0 if made.metallicRoughnessTexture else 0.5)}
    material = {"name": made.name or "no_look", "pbrMetallicRoughness": metal, "doubleSided": True,
                "alphaMode": made.alphaMode or "OPAQUE", "emissiveFactor": factors.get("emissiveFactor", [0, 0, 0])}
    shader = look.ComputeSurfaceSource()[0] if look else None
    for slot, name in SLOTS:
        image = getattr(made, slot)
        if image is not None:
            found = scene_package.texture_of(shader, name)
            holder = metal if slot == "baseColorTexture" else material
            holder[slot] = {"index": map_texture(contents, document, pictures, (slot, found[0]), image)}
    if made.metallicRoughnessTexture is not None:
        maps = tuple(str((scene_package.texture_of(shader, name) or [None])[0]) for name in ("roughness", "metallic"))
        metal["metallicRoughnessTexture"] = {"index": map_texture(
            contents, document, pictures, ("metal_rough",) + maps, made.metallicRoughnessTexture)}
    if factors.get("extensions"):
        material["extensions"] = factors["extensions"]
        document["extensionsUsed"] = sorted(set(document.get("extensionsUsed", [])) | set(factors["extensions"]))
    return material


# --- the clips ------------------------------------------------------------------------------------------------------

def animations_of(root, skeleton_query):
    """Every SkelAnimation under the character and the one its Skeleton plays: [(name, prim)], the played one's name
    (None when it plays none)."""
    found = [(inside.GetName(), inside) for inside in Usd.PrimRange(root, Usd.TraverseInstanceProxies())
             if inside.IsA(UsdSkel.Animation)]
    query = skeleton_query.GetAnimQuery()
    played = query.GetPrim() if query else None
    if played is None or not played.IsValid():
        return found, None
    if all(prim.GetPath() != played.GetPath() for _, prim in found):
        found.append((played.GetName(), played))
    return found, next(name for name, prim in found if prim.GetPath() == played.GetPath())


def lived(held, named, rate):
    """A held-still character's life in a game: the clip its still pose was taken from, played round from the second
    it was taken at ({animation, starts, loops}), or None. A still pose is only a picture's: in a game a person who
    stands still stands breathing (2099 #161, the owner: "the people are half, and just standing still"). The clip is
    the one the pose names (place_build.HELD_CLIP, HELD_SECONDS), else the one of its `Animations` whose sample equals
    the pose exactly (a scene laid before the pose named it); a pose set from a library pose (`score:pose`, place_build's
    `hold`: the smoker's arm) or one no clip holds stays still. A pose taken mid-stride (ON_THE_SPOT: the street's
    walkers, 2099 #161) has no route to walk, so it stands in place_build.CLIP, never treading on the spot."""
    if held is None or not held.IsValid() or held.GetAttribute("score:pose").HasAuthoredValue():
        return None
    if held.GetParent().GetName() == "Animations" or sample_times(held, None, rate) != [None]:
        return None  # a clip, or a keyed animation of its own (a sim body's): it is played as it is
    clips = {name: prim for name, prim in named if prim.GetParent().GetName() == "Animations"}
    clip, second = held.GetAttribute(place_build.HELD_CLIP).Get(), held.GetAttribute(place_build.HELD_SECONDS).Get()
    if clip not in clips:
        clip, second = taken_from(held, clips, rate)
    if clip is None:
        return None
    if clip in ON_THE_SPOT and place_build.CLIP in clips:
        clip = place_build.CLIP
    return {"animation": clip, "starts": -float(second or 0.0), "loops": clip not in skel_usd.ONCE}


def taken_from(held, clips, rate):
    """(clip, second) of the first clip time whose joints' rotations and translations equal the still pose's (within
    CLOSE), else (None, None). A pose is taken at any second, between two keys as often as on one (cast.held_still:
    the street's walkers, each a tenth of a frame on), so each pair of keys is also tried at the share of the way
    between them the pose lies at (between_keys)."""
    pose = UsdSkel.Animation(held)
    joints = list(pose.GetJointsAttr().Get() or [])
    rotations, translations = pose.GetRotationsAttr().Get(), pose.GetTranslationsAttr().Get()
    if not joints or rotations is None or translations is None:
        return None, None
    rotations, translations = np.array(rotations, dtype=np.float64), np.array(translations, dtype=np.float64)
    for name, prim in sorted(clips.items()):
        clip = UsdSkel.Animation(prim)
        if list(clip.GetJointsAttr().Get() or []) != joints:
            continue
        for time in between_keys(clip, rotations, translations):
            turned = np.array(clip.GetRotationsAttr().Get(time), dtype=np.float64)
            moved = np.array(clip.GetTranslationsAttr().Get(time), dtype=np.float64)
            same_turn = np.abs(np.abs(np.sum(turned * rotations, axis=1)) - 1.0)
            if np.max(same_turn) < CLOSE and np.max(np.abs(moved - translations)) < CLOSE:
                return name, time / rate
    return None, None


def between_keys(clip, rotations, translations):
    """The clip times a pose of `rotations` and `translations` may have been taken at: each key, and between each two
    keys the share of the way (0 to 1) that puts the keys' interpolation on the pose: by its translations, which
    UsdSkel interpolates linearly, else (none moves) by the turn of the joint that turns most, slerped."""
    times = list(clip.GetRotationsAttr().GetTimeSamples())
    keyed = [(np.array(clip.GetRotationsAttr().Get(time), dtype=np.float64),
              np.array(clip.GetTranslationsAttr().Get(time), dtype=np.float64)) for time in times]
    found = list(times)
    for (start, end), (before, after) in zip(zip(times, times[1:]), zip(keyed, keyed[1:])):
        share = share_between(before, after, rotations, translations)
        if share is not None:
            found.append(start + share * (end - start))
    return found


def share_between(before, after, rotations, translations):
    """How far (0 to 1) a pose lies from key `before` to key `after` (each (rotations, translations)), or None when
    the two keys are one pose."""
    step = after[1] - before[1]
    length = float(np.sum(step * step))
    if length > CLOSE * CLOSE:
        return min(1.0, max(0.0, float(np.sum((translations - before[1]) * step)) / length))
    turns = 2.0 * np.arccos(np.clip(np.abs(np.sum(before[0] * after[0], axis=1)), 0.0, 1.0))
    joint = int(np.argmax(turns))
    if turns[joint] <= CLOSE:
        return None
    turned = 2.0 * np.arccos(min(1.0, abs(float(np.sum(before[0][joint] * rotations[joint])))))
    return min(1.0, max(0.0, turned / float(turns[joint])))


def clip_round(root, name, prim):
    """A clip's one round in seconds (its asset's score:clip_seconds) when it is one of its `Animations`, else None."""
    if prim.GetParent().GetName() != "Animations":
        return None
    seconds = root.GetCustomDataByKey("score:clip_seconds") or {}
    return float(seconds[name]) if name in seconds else None


def sample_times(prim, round_seconds, rate):
    """The animation's time codes, cut to one round from its first when `round_seconds` is given; [None] when it is
    a pose with no samples."""
    animation = UsdSkel.Animation(prim)
    times = sorted({time for attribute in (animation.GetTranslationsAttr(), animation.GetRotationsAttr(),
                                           animation.GetScalesAttr()) if attribute
                    for time in attribute.GetTimeSamples()})
    if not times:
        return [None]
    if round_seconds is not None:
        times = [time for time in times if time <= times[0] + round_seconds * rate + ROUND]
    return times


def keys_of(prim, times, order):
    """The animation's keys at `times`: {path: (k x n x width) array} for translation, rotation (x, y, z, w, each
    turned onto its last's half so it slerps the short way) and scale, of the joints it moves (their skeleton
    numbers)."""
    animation = UsdSkel.Animation(prim)
    names = [str(name) for name in animation.GetJointsAttr().Get() or []]
    joints = [order.index(name) if name in order else -1 for name in names]
    found = {}
    for path, attribute in (("translation", animation.GetTranslationsAttr()),
                            ("rotation", animation.GetRotationsAttr()), ("scale", animation.GetScalesAttr())):
        if not attribute or not attribute.HasValue():
            continue
        frames = [attribute.Get(Usd.TimeCode.Default() if time is None else time) for time in times]
        if path == "rotation":
            values = np.array([[[*quat.GetImaginary(), quat.GetReal()] for quat in frame] for frame in frames])
            for frame in range(1, len(values)):
                flip = np.einsum("ij,ij->i", values[frame], values[frame - 1]) < 0
                values[frame][flip] *= -1.0
        else:
            values = np.array([[list(value) for value in frame] for frame in frames], dtype=np.float64)
        found[path] = values
    return joints, found


def shape_weights(prim, times, names):
    """The animation's blend shape weights at `times` for the shapes `names` (a mesh's morph targets, in its order;
    a shape it does not key at 0): (k x len(names)), or None when it keys none of them."""
    animation = UsdSkel.Animation(prim)
    keyed = [str(name) for name in animation.GetBlendShapesAttr().Get() or []]
    if not keyed or not set(keyed) & set(names):
        return None
    weights = animation.GetBlendShapeWeightsAttr()
    columns = [keyed.index(name) if name in keyed else -1 for name in names]
    found = np.zeros((len(times), len(names)))
    for row, time in enumerate(times):
        values = np.asarray(weights.Get(Usd.TimeCode.Default() if time is None else time) or [], dtype=np.float64)
        for column, source in enumerate(columns):
            if 0 <= source < len(values):
                found[row, column] = values[source]
    return found


def moves_of(root, rate):
    """The SkelRoot's own moves after its first time: (seconds from it, translations, rotations x y z w) of node 0,
    each its world then over its world first; None when it stands still."""
    times = moved_times(root)
    if not times:
        return None
    xform = UsdGeom.Xformable(root)
    first = np.linalg.inv(np.asarray(xform.ComputeLocalToWorldTransform(Usd.TimeCode(times[0]))))
    places, turns = [], []
    for time in times:
        local = (np.asarray(xform.ComputeLocalToWorldTransform(Usd.TimeCode(time))) @ first).T
        places.append(local[:3, 3])
        turns.append(quaternion_of(local[:3, :3]))
    return (np.array([(time - times[0]) / rate for time in times]), np.array(places), np.array(turns))


def quaternion_of(turn):
    """A column-vector rotation matrix as a unit quaternion (x, y, z, w)."""
    from scipy.spatial.transform import Rotation
    return Rotation.from_matrix(turn / np.linalg.norm(turn, axis=0)).as_quat()


# --- the glTF -------------------------------------------------------------------------------------------------------

def floats(values):
    return np.asarray(values, dtype=np.float32).ravel().tolist()


def joint_nodes(skeleton_query, order):
    """The joints as glTF nodes, numbered from 2 in `order`: each its rest transform (a row-major matrix is glTF's
    column-first list) and its children; and node 1's children, the root joints."""
    rest = skeleton_query.ComputeJointLocalTransforms(Usd.TimeCode.Default(), atRest=True)
    nodes = [{"name": path.rsplit("/", 1)[-1], "matrix": floats(np.asarray(matrix))} for path, matrix in
             zip(order, rest)]
    roots = []
    for number, path in enumerate(order):
        if "/" in path:
            nodes[order.index(path.rsplit("/", 1)[0])].setdefault("children", []).append(number + 2)
        else:
            roots.append(number + 2)
    return nodes, roots


def mesh_of(target, frame, order, contents, document, looks, pictures):
    """One shown skinned Mesh as a glTF mesh (a primitive a look) in the SkelRoot's frame (`frame`: the Skeleton's
    frame there, row-major); (the mesh, its triangle count, its vertices' point numbers)."""
    prim = target.GetPrim()
    points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(), dtype=np.float64)
    point_of, normals, uv, triangles, faces = mesh_corners(prim)
    placed = np.asarray(target.GetGeomBindTransform()) @ frame
    positions = points[point_of] @ placed[:3, :3] + placed[3, :3]
    turned = normals @ np.linalg.inv(placed[:3, :3]).T
    turned /= np.maximum(np.linalg.norm(turned, axis=1, keepdims=True), 1e-12)
    if np.linalg.det(placed[:3, :3]) < 0:
        triangles = triangles[:, ::-1]
    joints, weights = influences_of(target, order, len(points))
    attributes = {"POSITION": contents.reading(floats(positions), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER, True),
                  "NORMAL": contents.reading(floats(turned), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER)}
    if uv is not None:
        attributes["TEXCOORD_0"] = contents.reading(floats(np.column_stack([uv[:, 0], 1.0 - uv[:, 1]])), "VEC2",
                                                    glb.FLOAT, glb.ARRAY_BUFFER)
    for set_number in range(joints.shape[1] // 4):
        columns = slice(set_number * 4, set_number * 4 + 4)
        attributes[f"JOINTS_{set_number}"] = contents.reading(
            joints[point_of][:, columns].astype(np.uint16).ravel().tolist(), "VEC4", glb.UNSIGNED_SHORT,
            glb.ARRAY_BUFFER)
        attributes[f"WEIGHTS_{set_number}"] = contents.reading(floats(weights[point_of][:, columns]), "VEC4",
                                                               glb.FLOAT, glb.ARRAY_BUFFER)
    bound, per_face = scene_package.face_looks(prim, int(faces.max()) + 1)
    chosen = per_face[faces]
    primitives = []
    for number in np.unique(chosen):
        key = scene_package.pbr_key(bound[number])
        if key not in looks:
            document.setdefault("materials", []).append(material_of(bound[number], contents, document, pictures))
            looks[key] = len(document["materials"]) - 1
        picked = triangles[chosen == number].astype(np.uint32).ravel().tolist()
        primitives.append({"attributes": attributes, "material": looks[key], "indices": contents.reading(
            picked, "SCALAR", glb.UNSIGNED_INT, glb.ELEMENT_ARRAY_BUFFER)})
    names, targets = morph_targets(prim, point_of, placed, contents)
    mesh = {"name": prim.GetName(), "primitives": primitives}
    if names:
        for primitive in primitives:
            primitive["targets"] = targets
        mesh.update(weights=[0.0] * len(names), extras={"targetNames": names})
    return mesh, len(triangles), point_of


def morph_targets(prim, point_of, placed, contents):
    """The Mesh's UsdSkel blend shapes as glTF morph targets of its vertices (each point's offset turned into the
    SkelRoot's frame by `placed`'s linear part, a normal offset as given): (their names, [{POSITION, NORMAL?}]);
    Unconvertible for a shape with inbetweens."""
    binding = UsdSkel.BindingAPI(prim)
    names = [str(name) for name in binding.GetBlendShapesAttr().Get() or []] if binding.GetBlendShapesAttr() else []
    shapes = binding.GetBlendShapeTargetsRel().GetTargets() if names else []
    count = len(UsdGeom.Mesh(prim).GetPointsAttr().Get())
    targets = []
    for path in shapes:
        shape = UsdSkel.BlendShape(prim.GetStage().GetPrimAtPath(path))
        if shape.GetInbetweens():
            raise Unconvertible(f"its blend shape {path.name} has inbetweens, which the package does not carry")
        chosen = shape.GetPointIndicesAttr().Get()
        chosen = np.arange(count) if not chosen else np.asarray(chosen, dtype=np.int64)
        target = {}
        for key, attribute, turn in (("POSITION", shape.GetOffsetsAttr(), placed[:3, :3]),
                                     ("NORMAL", shape.GetNormalOffsetsAttr(), np.linalg.inv(placed[:3, :3]).T)):
            given = attribute.Get() if attribute else None
            if not given:
                continue
            full = np.zeros((count, 3))
            full[chosen] = np.asarray(given, dtype=np.float64) @ turn
            target[key] = contents.reading(floats(full[point_of]), "VEC3", glb.FLOAT, glb.ARRAY_BUFFER,
                                           key == "POSITION")
        targets.append(target)
    return names[:len(targets)], targets


def sampler(contents, animation, times, values, shape):
    """A LINEAR sampler of `values` at `times` (seconds) added to the animation; its number."""
    animation["samplers"].append({"input": contents.reading(floats(times), "SCALAR", glb.FLOAT, with_bounds=True),
                                  "output": contents.reading(floats(values), shape, glb.FLOAT),
                                  "interpolation": "LINEAR"})
    return len(animation["samplers"]) - 1


def animation_of(name, prim, times, order, contents, rate, morphed):
    """One SkelAnimation as a glTF animation keyed from its first sample, its blend shape weights on each morphed mesh
    node (`morphed` [(node, its target names)]): (the animation, its length in seconds)."""
    joints, keys = keys_of(prim, times, order)
    seconds = np.array([0.0] if times[0] is None else [(time - times[0]) / rate for time in times])
    animation = {"name": name, "samplers": [], "channels": []}
    shapes = {"translation": "VEC3", "rotation": "VEC4", "scale": "VEC3"}
    for path, values in keys.items():
        for column, joint in enumerate(joints):
            if joint >= 0:
                animation["channels"].append({"target": {"node": joint + 2, "path": path}, "sampler": sampler(
                    contents, animation, seconds, values[:, column], shapes[path])})
    for node, names in morphed:
        weights = shape_weights(prim, times, names)
        if weights is not None:
            animation["channels"].append({"target": {"node": node, "path": "weights"}, "sampler": sampler(
                contents, animation, seconds, weights, "SCALAR")})
    return animation, float(seconds[-1])


def moved_channels(animation, moves, contents):
    """The SkelRoot's moves (moves_of) as node 0's translation and rotation channels of the played animation."""
    seconds, places, turns = moves
    for path, values, shape in (("translation", places, "VEC3"), ("rotation", turns, "VEC4")):
        animation["channels"].append({"target": {"node": 0, "path": path},
                                      "sampler": sampler(contents, animation, seconds, values, shape)})


def root_node(baked):
    """Node 0: the character (named so, never by its SkelRoot: a crowd's prototypes of one look are one file), its
    copy's uneven stretch (`baked`, row-major 3 x 3, or None) drawn in."""
    node = {"name": "character", "children": [1]}
    if baked is not None:
        matrix = np.eye(4)
        matrix[:3, :3] = baked
        node["matrix"] = floats(matrix)
    return node


def character_glb(root, baked=None):
    """The character (its SkelRoot `root`) as a skinned GLB and its scene.json facts: (glb bytes, {triangles,
    usd_triangles, clips, plays, joints}); Unconvertible when it cannot be carried as drawn."""
    stage = root.GetStage()
    rate = stage.GetTimeCodesPerSecond()
    cache, binding = binding_of(root)
    skeleton = binding.GetSkeleton()
    skeleton_query = cache.GetSkelQuery(skeleton)
    order = [str(path) for path in skeleton_query.GetJointOrder()]
    targets = shown_targets(binding)
    if not targets:
        raise Unconvertible("it draws no face")
    frame = np.asarray(UsdGeom.XformCache().ComputeRelativeTransform(skeleton.GetPrim(), root)[0])
    contents, document = glb.Contents(), {"asset": {"version": "2.0", "generator": "score place_build skinned.py"}}
    joints, roots = joint_nodes(skeleton_query, order)
    document["nodes"] = [root_node(baked),
                         {"name": "skeleton", "matrix": floats(frame), "children": roots}] + joints
    binds = skeleton.GetBindTransformsAttr().Get()
    document["skins"] = [{"joints": [number + 2 for number in range(len(order))], "skeleton": 1,
                          "inverseBindMatrices": contents.reading(
                              floats([np.linalg.inv(np.asarray(bind) @ frame) for bind in binds]), "MAT4",
                              glb.FLOAT)}]
    document["meshes"], looks, pictures, triangles, points_of, morphed = [], {}, {}, 0, [], []
    for target in targets:
        mesh, count, point_of = mesh_of(target, frame, order, contents, document, looks, pictures)
        document["meshes"].append(mesh)
        document["nodes"].append({"name": mesh["name"], "mesh": len(document["meshes"]) - 1, "skin": 0})
        document["nodes"][0]["children"].append(len(document["nodes"]) - 1)
        triangles += count
        points_of.append(point_of)
        if "extras" in mesh:
            morphed.append((len(document["nodes"]) - 1, mesh["extras"]["targetNames"]))
    named, played = animations_of(root, skeleton_query)
    document["animations"], clips, plays, keyed, checked = [], {}, None, [None], None
    for name, prim in named:
        round_seconds = clip_round(root, name, prim)
        times = sample_times(prim, round_seconds, rate)
        animation, length = animation_of(name, prim, times, order, contents, rate, morphed)
        if name == played:
            moves = moves_of(root, rate)
            if moves is not None:
                moved_channels(animation, moves, contents)
            plays = {"animation": name, "starts": 0.0 if times[0] is None else float(times[0] / rate),
                     "loops": round_seconds is not None and name not in skel_usd.ONCE}
            keyed, checked = times, name
        document["animations"].append(animation)
        clips[name] = round(length, 6)
    if moves_of(root, rate) is None:  # a walker's route is keyed on the animation it plays: it keeps that one
        plays = lived(dict(named).get(played), named, rate) or plays
    document["scenes"], document["scene"] = [{"nodes": [0]}], 0
    glb.refuse_a_tangled_graph(document)
    blob = contents.blob()
    document.update(bufferViews=contents.views, accessors=contents.accessors, buffers=[{"byteLength": len(blob)}])
    if contents.images:
        document["images"] = contents.images
    usd_triangles = sum(len(scene_package.drawn(target.GetPrim())[2]) for target in targets)
    facts = {"triangles": triangles, "usd_triangles": usd_triangles, "clips": clips, "plays": plays,
             "joints": len(order), "points_of": points_of, "keyed": keyed, "checked": checked}
    return scene_package.packed(document, blob), facts


# --- the check ------------------------------------------------------------------------------------------------------

def node_matrix(node):
    """A glTF node's own transform as a column-vector 4 x 4."""
    if "matrix" in node:
        return np.asarray(node["matrix"], dtype=np.float64).reshape(4, 4).T
    from scipy.spatial.transform import Rotation
    matrix = np.eye(4)
    matrix[:3, :3] = Rotation.from_quat(node.get("rotation", [0, 0, 0, 1])).as_matrix() * np.asarray(
        node.get("scale", [1, 1, 1]))
    matrix[:3, 3] = node.get("translation", [0, 0, 0])
    return matrix


def posed_nodes(document, blob, animation, key):
    """Every node's own transform at the animation's key number `key` (None: at rest), column-vector, a keyed path
    replacing that part of its rest (a node's rest matrix read as translation, rotation and scale)."""
    from scipy.spatial.transform import Rotation
    local = [node_matrix(node) for node in document["nodes"]]
    if animation is None:
        return local
    parts = []
    for matrix in local:
        scale = np.linalg.norm(matrix[:3, :3], axis=0)
        parts.append({"translation": matrix[:3, 3], "rotation": Rotation.from_matrix(matrix[:3, :3] / scale).as_quat(),
                      "scale": scale})
    keyed = set()
    for channel in animation["channels"]:
        node, path = channel["target"]["node"], channel["target"]["path"]
        if path != "weights" and node != 0:  # node 0's moves are on keys of their own, and the check is in its frame
            parts[node][path] = skel_usd.accessor(
                document, blob, animation["samplers"][channel["sampler"]]["output"])[key]
            keyed.add(node)
    for node in keyed:
        local[node] = np.eye(4)
        local[node][:3, :3] = Rotation.from_quat(parts[node]["rotation"]).as_matrix() * parts[node]["scale"]
        local[node][:3, 3] = parts[node]["translation"]
    return local


def world_nodes(document, local):
    """Every node's transform below node 0 (node 0's own moves left out: the check is in the SkelRoot's frame)."""
    parent = {child: number for number, node in enumerate(document["nodes"]) for child in node.get("children", [])}
    found = {}

    def world(number):
        if number not in found:
            above = parent.get(number)
            found[number] = (world(above) if above is not None else np.eye(4)) @ local[number]
        return found[number]
    return [world(number) for number in range(len(document["nodes"]))]


def morphed_points(document, blob, mesh, weights):
    """A mesh's vertices with its morph targets weighed in (`weights` one a target)."""
    primitive = mesh["primitives"][0]
    points = skel_usd.accessor(document, blob, primitive["attributes"]["POSITION"]).astype(np.float64)
    for weight, target in zip(weights, primitive.get("targets", [])):
        if "POSITION" in target:
            points = points + weight * skel_usd.accessor(document, blob, target["POSITION"]).astype(np.float64)
    return points


def keyed_weights(document, blob, animation, node, key):
    """A mesh node's morph weights at the animation's key number `key`, else its mesh's own."""
    mesh = document["meshes"][document["nodes"][node]["mesh"]]
    count = len(mesh["primitives"][0].get("targets", []))
    for channel in (animation or {}).get("channels", []):
        if channel["target"] == {"node": node, "path": "weights"}:
            values = skel_usd.accessor(document, blob, animation["samplers"][channel["sampler"]]["output"])
            return values[key * count:(key + 1) * count]
    return mesh.get("weights", [0.0] * count)


def gltf_skin(glb_bytes, played, key=0):
    """The GLB's shown meshes skinned in numpy at its animation `played`'s key number `key` (None: at rest), its morph
    weights then weighed in first, in node 0's frame: [(vertices (n x 3))] a mesh node."""
    document, blob = scene_package.unpacked(glb_bytes, None)
    animation = next((found for found in document.get("animations", []) if found["name"] == played), None)
    world = world_nodes(document, posed_nodes(document, blob, animation, key))
    skin = document["skins"][0]
    inverse = skel_usd.accessor(document, blob, skin["inverseBindMatrices"]).astype(np.float64).reshape(-1, 4, 4)
    joint_matrices = np.array([world[joint] @ inverse[number].T for number, joint in enumerate(skin["joints"])])
    skinned = []
    for node, about in enumerate(document["nodes"]):
        if "mesh" not in about:
            continue
        mesh = document["meshes"][about["mesh"]]
        attributes = mesh["primitives"][0]["attributes"]
        points = morphed_points(document, blob, mesh, keyed_weights(document, blob, animation, node, key))
        points = np.hstack([points, np.ones((len(points), 1))])
        moved = np.zeros((len(points), 4))
        for set_number in range(sum(1 for key in attributes if key.startswith("JOINTS_"))):
            joints = skel_usd.accessor(document, blob, attributes[f"JOINTS_{set_number}"]).astype(np.int64)
            weights = skel_usd.accessor(document, blob, attributes[f"WEIGHTS_{set_number}"]).astype(np.float64)
            for column in range(4):
                moved += weights[:, column, None] * np.einsum("nij,nj->ni", joint_matrices[joints[:, column]], points)
        skinned.append(moved[:, :3])
    return skinned


def usd_skin(root, time):
    """UsdSkel's own posed skin (ready/people.posed_body: each shown mesh's points skinned in the Skeleton's space) at
    the time code `time` (None: its default), in the SkelRoot's frame: [(points (n x 3))] a shown mesh."""
    from score.stages.place_build.ready import people
    time = Usd.TimeCode.Default() if time is None else Usd.TimeCode(time)
    _, binding = binding_of(root)
    frame = np.asarray(UsdGeom.XformCache(time).ComputeRelativeTransform(binding.GetSkeleton().GetPrim(), root)[0])
    return [points @ frame[:3, :3] + frame[3, :3] for _, points, _ in people.posed_body(root, time).drawn]


def skin_error(root, glb_bytes, facts, key):
    """The largest distance (metres) between the glTF's skin and UsdSkel's at the played animation's key `key`."""
    ours = gltf_skin(glb_bytes, facts["checked"], key)
    theirs = usd_skin(root, facts["keyed"][key])
    if len(ours) != len(theirs):
        return float("inf")
    return max(float(np.max(np.linalg.norm(mine - their[point_of], axis=1)))
               for mine, their, point_of in zip(ours, theirs, facts["points_of"]))


def check_of(root, glb_bytes, facts):
    """The conversion's check: {pass, triangles, usd_triangles, skinned_error (metres, the largest distance between
    the glTF's skin and UsdSkel's at the played animation's first, middle and last keys: its joints, morph weights
    and points), joints, clips}."""
    count = len(facts["keyed"])
    error = max(skin_error(root, glb_bytes, facts, key) for key in sorted({0, count // 2, count - 1}))
    return {"pass": bool(error <= CLOSE and facts["triangles"] == facts["usd_triangles"] > 0),
            "triangles": facts["triangles"], "usd_triangles": facts["usd_triangles"],
            "skinned_error": round(error, 7), "joints": facts["joints"], "clips": len(facts["clips"])}
