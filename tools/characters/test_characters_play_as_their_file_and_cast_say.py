"""A character plays as its file and its cast say: the UsdSkel asset (skel_usd.py) skins its points where the glTF
file's own skinning puts them, its joints parents first and the file's half turn kept below the root, repeats a
running clip for the whole length and holds a played-once one, and wears its dressed body (an animal every mesh); the
cast's rules (cast.py) give the same people in the same spots from the same seeds, a crowd on its tiers by its
shares; the cast check (cast_check.py) refuses the same person twice and a walk through somebody or something; laid
with the cast's prims, every character stands or walks where the cast puts it, plays its clip from its start and
wears only its parts; and the review page (tools/review/characters.py) sees each from in front.

One world: a two-joint body made here (a distant and a dressed mesh, a clip that runs round and one that plays once,
a sparse morph target keyed on in the walk's second frame) converted once dressed and once as an animal, a cast laid
from it, and the review's plan of that stage. Its skinned points are worked out by hand in the SKINNED rows, where
each laid character stands in the PLACED rows, what each body shows in the SHOWN rows, and the cast check's verdicts
in the FAULTS rows.

Breaks that turn the test red (each applied once and seen red, 2026-10-26; again after the fold, 2026-11-13):
- convert's bind `matrix(values).GetInverse()` made `matrix(values)` (the SKINNED rows); and, apart, write_part's
  `if shape_names:` made `if False:` (no blend shapes: the "hips point one frame in" row); and, apart, joint_paths'
  `"/".join(reversed(trail))` made `"/".join(trail)` (the joints' order).
- convert's `turned.AddTransformOp().Set(local_matrix(scene_root))` made `.Set(Gf.Matrix4d(1))` (the half turn).
- repeated's `cycle = keys[:-1] if ... else keys` made `cycle = keys`; and, apart, write_clips' `once =
  animation["name"] in ONCE` made `once = False` (the walk's and the door's samples).
- write_body's `if worn is not None and name not in worn:` made `if name not in (worn or ()):` (the "animal" row of
  SHOWN).
- sparse_values keeps every point (its nonzero pick dropped) (the dense morph target).
- kit_mix's `random.Random(seed)` made `random.Random()`; and, apart, band_places' `along * (number +
  draw.random()) / group["count"]` made `along * draw.random()` (the seeded rules and the band's spread).
- crowd_copies' `at = [x, ground_at(boxes, x, z), z]` made `at = [x, 0.0, z]` (the crowd on its tier).
- clash_with_things' `if top < feet + KNEE or bottom > feet + HEAD: continue` dropped (the floor plate counts: the
  "through the crate" row of FAULTS); and, apart, look_of's head and hair parts dropped (`*sorted(...)` removed: two
  kit people of one build read the same, the group's 40 looks).
- walked's `seconds += math.dist(here, there) / pace` made `seconds += math.dist(here, there)` (the walker's PLACED
  rows).
- referenced's `Sdf.LayerOffset(-start_seconds * skel_usd.RATE)` made `Sdf.LayerOffset(0)` (row_1's offset); and,
  apart, held_still's `GetRotationsAttr().Get(time)` made `.Get(time + 1)` (the sleeper's held pose).
- tools/review/characters.py ahead's `at[2] - math.cos(angle) * distance` made `at[2] + ...` (the close eye).
"""

import io
import json
import math
import pathlib
import struct
import sys

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdSkel

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools/review"))
import cast  # noqa: E402
import cast_check  # noqa: E402
import skel_usd  # noqa: E402

# A quarter turn about z for the hips, as x y z w.
QUARTER = [0.0, 0.0, math.sin(math.pi / 8), math.cos(math.pi / 8)]


class Blob:
    """The binary chunk of a glTF file being written, with its views and accessors."""

    def __init__(self):
        self.data = bytearray()
        self.views, self.accessors = [], []

    def add(self, values, kind, shape):
        while len(self.data) % 4:
            self.data.append(0)
        array = np.ascontiguousarray(values, dtype=kind)
        self.views.append({"buffer": 0, "byteOffset": len(self.data), "byteLength": array.nbytes})
        self.data.extend(array.tobytes())
        component = {np.float32: 5126, np.uint16: 5123, np.uint32: 5125}[kind]
        self.accessors.append({"bufferView": len(self.views) - 1, "componentType": component,
                               "count": len(array), "type": shape})
        return len(self.accessors) - 1

    def add_picture(self):
        picture = io.BytesIO()
        Image.new("RGB", (4, 4), (200, 30, 30)).save(picture, "PNG")
        while len(self.data) % 4:
            self.data.append(0)
        self.views.append({"buffer": 0, "byteOffset": len(self.data), "byteLength": len(picture.getvalue())})
        self.data.extend(picture.getvalue())
        return len(self.views) - 1


def body_glb(path):
    """A body file shaped as the people tools write one: Person (turned half round) holding Root, and two meshes,
    `far` and `person`, skinned to Root and Hips; clips `walking` (runs round) and `door` (plays once). The person's
    mesh has one sparse morph target, `walking.0` (its third point 0.1 m along x), which the walk keys to 1 in its
    second frame only, as garment_bake.py writes a settled garment's."""
    blob = Blob()
    points = np.array([[-0.2, 0.0, 0.0], [0.2, 0.0, 0.0], [-0.2, 1.5, 0.0], [0.2, 1.5, 0.0]], np.float32)
    meshes = []
    for _ in range(2):
        attributes = {"POSITION": blob.add(points, np.float32, "VEC3"),
                      "NORMAL": blob.add(np.tile([0, 0, 1], (4, 1)), np.float32, "VEC3"),
                      "TEXCOORD_0": blob.add([[0, 0], [1, 0], [0, 1], [1, 1]], np.float32, "VEC2"),
                      "JOINTS_0": blob.add([[0, 0, 0, 0], [0, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0]], np.uint16, "VEC4"),
                      "WEIGHTS_0": blob.add([[1, 0, 0, 0]] * 4, np.float32, "VEC4")}
        meshes.append({"primitives": [{"attributes": attributes,
                                       "indices": blob.add([0, 1, 2, 2, 1, 3], np.uint32, "SCALAR"),
                                       "material": len(meshes)}]})
    moved, offset = blob.add([2], np.uint32, "SCALAR"), blob.add([[0.1, 0.0, 0.0]], np.float32, "VEC3")
    blob.accessors.append({"componentType": 5126, "count": 4, "type": "VEC3", "sparse": {
        "count": 1, "indices": {"bufferView": blob.accessors[moved]["bufferView"], "componentType": 5125},
        "values": {"bufferView": blob.accessors[offset]["bufferView"]}}})
    meshes[1]["primitives"][0]["targets"] = [{"POSITION": len(blob.accessors) - 1}]
    meshes[1].update(weights=[0.0], extras={"targetNames": ["walking.0"]})
    hips_at = [0.0, 1.0, 0.0]
    inverse_binds = blob.add([np.eye(4).reshape(-1),
                              np.linalg.inv(np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], hips_at + [1]],
                                                     float).T).T.reshape(-1)], np.float32, "MAT4")
    walk_times = blob.add([0.0, 1 / 30, 2 / 30], np.float32, "SCALAR")
    walk_turns = blob.add([[0, 0, 0, 1], QUARTER, [0, 0, 0, 1]], np.float32, "VEC4")
    walk_places = blob.add([hips_at, [0.0, 1.1, 0.0], hips_at], np.float32, "VEC3")
    walk_shapes = blob.add([0.0, 1.0, 0.0], np.float32, "SCALAR")
    door_times = blob.add([0.0, 1 / 30], np.float32, "SCALAR")
    door_turns = blob.add([[0, 0, 0, 1], QUARTER], np.float32, "VEC4")
    picture = blob.add_picture()
    document = {
        "asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "Person", "rotation": [0.0, 1.0, 0.0, 0.0], "children": [1, 3, 4]},
                  {"name": "Root", "children": [2]}, {"name": "Hips", "translation": hips_at},
                  {"name": "far", "mesh": 0, "skin": 0}, {"name": "person", "mesh": 1, "skin": 0}],
        "skins": [{"joints": [1, 2], "inverseBindMatrices": inverse_binds, "skeleton": 1}],
        "meshes": meshes,
        "materials": [{"name": "clothes", "pbrMetallicRoughness": {"baseColorFactor": [0.1, 0.2, 0.3, 1.0]}},
                      {"name": "jacket", "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
        "textures": [{"source": 0}], "images": [{"bufferView": picture, "mimeType": "image/png"}],
        "animations": [
            {"name": "walking", "samplers": [{"input": walk_times, "output": walk_turns},
                                             {"input": walk_times, "output": walk_places},
                                             {"input": walk_times, "output": walk_shapes}],
             "channels": [{"sampler": 0, "target": {"node": 2, "path": "rotation"}},
                          {"sampler": 1, "target": {"node": 2, "path": "translation"}},
                          {"sampler": 2, "target": {"node": 4, "path": "weights"}}]},
            {"name": "door", "samplers": [{"input": door_times, "output": door_turns}],
             "channels": [{"sampler": 0, "target": {"node": 2, "path": "rotation"}}]}],
    }
    document["bufferViews"] = blob.views
    document["accessors"] = blob.accessors
    document["buffers"] = [{"byteLength": len(blob.data)}]
    while len(blob.data) % 4:
        blob.data.append(0)
    text = json.dumps(document).encode()
    text += b" " * (-len(text) % 4)
    chunks = struct.pack("<I4s", len(text), b"JSON") + text + struct.pack("<I4s", len(blob.data), b"BIN\0") + blob.data
    path.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(chunks)) + chunks)
    return path


def skinned(stage, mesh_path, clip, time):
    """The mesh's points as UsdSkel deforms them with `clip` playing, at `time`: its blend shapes at the clip's
    weights, then skinned."""
    skeleton = stage.GetPrimAtPath("/Character/Turned/Skeleton")
    UsdSkel.BindingAPI(skeleton).GetAnimationSourceRel().SetTargets([f"/Character/Animations/{clip}"])
    cache = UsdSkel.Cache()
    cache.Populate(UsdSkel.Root(stage.GetPrimAtPath("/Character")), Usd.PrimDefaultPredicate)
    query = cache.GetSkelQuery(UsdSkel.Skeleton(skeleton))
    transforms = query.ComputeSkinningTransforms(time)
    mesh = stage.GetPrimAtPath(mesh_path)
    points = mesh.GetAttribute("points").Get()
    skinning = cache.GetSkinningQuery(mesh)
    if skinning.HasBlendShapes() and query.GetAnimQuery().GetBlendShapeOrder():
        weights = skinning.GetBlendShapeMapper().Remap(query.GetAnimQuery().ComputeBlendShapeWeights(time))
        shapes = UsdSkel.BlendShapeQuery(UsdSkel.BindingAPI(mesh))
        sub_weights, shape_indices, sub_indices = shapes.ComputeSubShapeWeights(weights)
        shapes.ComputeDeformedPoints(sub_weights, shape_indices, sub_indices, shapes.ComputeBlendShapePointIndices(),
                                     shapes.ComputeSubShapePointOffsets(), points)
    skinning.ComputeSkinnedPoints(transforms, points, time)
    return np.array(points)



FOUND = {"people": [{"name": "keeper", "character": "tester", "doing": "door", "at": [1.0, 0.0, 2.0],
                     "facing_to": [1.0, 0.0, -5.0], "why": "keeps the door"},
                    {"name": "walker", "character": "tester", "doing": "walking", "at": [0.0, 0.0, 0.0],
                     "path": [[0.0, 0.0, 0.0], [0.0, 0.0, -4.0]], "pace": 2.0, "facing_to": [0, 0, -1],
                     "why": "walks by"},
                    {"name": "sleeper", "character": "tester", "doing": "walking", "at": [3.0, 0.0, 0.0],
                     "facing_to": [3.0, 0.0, -1.0], "held": True, "why": "lies still"}],
         "groups": [{"name": "row", "character": "kit", "outfit": "plain", "count": 3, "seed": 40,
                     "band": [0.0, 0.0, 2.0, 6.0], "doing": ["walking"], "phase_step": 0.5,
                     "facing_to": [0, 0, -9], "why": "a row"}]}


def laid(folder, found):
    """The cast's characters laid with cast.py's prims as the characters layer lays them (score/stages/cast/layer.py),
    each in its body's asset, the kit members wearing their own parts, under the place's root: the stage of the
    layer."""
    (folder / "stage/layers").mkdir(parents=True)
    root = Sdf.Layer.CreateNew(str(folder / "stage/yard.usda"))
    root.subLayerPaths.append("./layers/characters.usda")
    root.Save()
    layer = Sdf.Layer.CreateNew(str(folder / "stage/layers/characters.usda"))
    layer.timeCodesPerSecond = layer.framesPerSecond = skel_usd.RATE
    stage = Usd.Stage.Open(layer)
    for single in cast.characters_of(found):
        asset = skel_usd.convert(folder / f"bodies/{single['character']}.glb", folder / "stage/assets/characters")
        parts, clips = cast.asset_facts(asset)
        path = f"/yard/Characters/{single['name']}"
        start = single["start"] * clips.get(single["doing"], 0.0)
        prim = cast.referenced(stage, path, asset, start)
        if single["path"]:
            cast.walked(prim, single["path"], single["pace"])
        else:
            cast.placed(prim, single["at"], single["turn"])
        if single["worn"]:
            cast.dressed(stage, path, parts, single["worn"])
        cast.playing(stage, path, single["doing"], clips)
        if single["held"]:
            cast.held_still(stage, path, asset, single["doing"], start)
    layer.Save()
    return stage



TURN = np.array([[math.cos(math.pi / 4), -math.sin(math.pi / 4)], [math.sin(math.pi / 4), math.cos(math.pi / 4)]])
PERSON, FAR = "/Character/Turned/Body/person/jacket_0", "/Character/Turned/Body/far/clothes_0"

# The points UsdSkel deforms, worked out by hand: (row, mesh, clip, frame, point, coordinates compared, where, atol).
# One frame into the walk the hips' points have turned a quarter round z about the hips and risen 0.1 m, the third
# one moved 0.1 m along x first by its morph target; the root's points never move; the shape is keyed off at frame 2.
SKINNED = [
    ("at rest", PERSON, "walking", 0, 2, 3, [-0.2, 1.5, 0.0], 1e-5),
    ("hips point one frame in", PERSON, "walking", 1, 2, 2, TURN @ np.array([-0.1, 0.5]) + [0.0, 1.1], 1e-5),
    ("root point never moves", PERSON, "walking", 1, 0, 3, [-0.2, 0.0, 0.0], 1e-6),
    ("far body has no shapes", FAR, "walking", 1, 2, 2, TURN @ np.array([-0.2, 0.5]) + [0.0, 1.1], 1e-5),
    ("shape keyed off again", PERSON, "walking", 2, 2, 3, [-0.2, 1.5, 0.0], 1e-5),
]

# Where a laid character stands at a time code: the keeper where the cast puts it; the walker covers its 4 m at
# 2 m a second, at the path's end at 2 s (60 time codes) and half way at 1 s.
PLACED = [("keeper", 0, (1, 0, 2)), ("walker", 60, (0, 0, -4)), ("walker", 30, (0, 0, -2))]

# What a body shows: (row, world, body prim, the visible children). A person wears the dressed body, the distant one
# hidden; an animal names no outfit and wears every mesh; a kit member wears only the kit's parts, which this test
# body has none of.
SHOWN = [("person", "asset", "/Character/Turned/Body", ["person"]),
         ("animal", "animal", "/Character/Turned/Body", ["far", "person"]),
         ("kit member", "stage", "/yard/Characters/row_0/Turned/Body", [])]

WALKER = {"name": "walker", "character": "bram", "doing": "walking", "at": [0.0, 0.0, 0.0], "facing_to": [4, 0, 0],
          "path": [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0]]}
STANDING = {"name": "standing", "character": "take_c", "doing": "waiting", "at": [2.0, 0.0, 0.2],
            "facing_to": [2.0, 0.0, 1.0]}
CRATE = ("Objects/crate_1", (1.8, -0.3, 2.4, 0.3), 0.0, 0.8)
PLATE = ("Objects/plate_1", (1.0, -1.0, 3.0, 1.0), -0.05, 0.02)

# The cast check's verdicts (owner, 2026-10-09: nobody twice, walks clear): (row, people, things on the stage, the
# words each fault holds, one fault per entry).
FAULTS = [
    ("same person twice", [dict(STANDING, name="again", at=[9.0, 0.0, 9.0]), STANDING], [],
     ["again and standing are the same person (take_c)"]),
    ("one body in two variants", [dict(STANDING, variant=1), dict(STANDING, name="again", variant=2)], [], []),
    ("through somebody standing", [WALKER, STANDING], [], ["from standing"]),
    ("through the crate, over the plate", [WALKER], [CRATE, PLATE], ["crate_1"]),
    ("round them", [dict(WALKER, path=[[0.0, 0.0, 0.0], [2.0, 0.0, -1.2], [4.0, 0.0, 0.0]]), STANDING],
     [CRATE, PLATE], []),
]

ROW = {"name": "row", "count": 10, "seed": 7, "band": [-13.0, -16.0, 8.0, 26.0], "facing_to": [-45, 3, 0],
       "doing": ["standing", "clapping"], "phase_step": 0.37}
CROWD = {"name": "crowd", "count": 400, "seed": 3, "spread": [-42.0, -56.0, 38.4, 112.0],
         "kept_off": [[-44.0, -13.0, 4.5, 19.0]], "clear_radius": 0.7,
         "tiers": [[-38.0, 0.0, -40.0, 23.0, 0.8, 74.0]], "tier_tread": 0.9, "tier_half_step": 0.4,
         "facing_to": [-45.5, 3.3, -3.5], "turn_jitter": 0.35, "height_jitter": 0.06,
         "doing": ["standing", "cheering"], "shares": [0.7, 0.3], "phases": 2,
         "palettes": [[[1, 2, 3]], [[4, 5, 6]]], "palette_parts": ["skin"], "palette_shares": [0.5, 0.5]}
REVIEWED = {"people": [{"name": "keeper", "character": "tester", "doing": "door", "at": [1.0, 0.0, 2.0],
                        "facing_to": [1.0, 0.0, -5.0], "why": "keeps the door"}],
            "crowd": {"name": "crowd", "count": 5, "spread": [0, 0, 4, 4], "facing_to": [0, 0, -9],
                      "views": [{"name": "above", "eye": [0, 9, 0], "aim": [2, 0, 2]}]}}


def visible(stage, path):
    """The names of a body's children not hidden."""
    return [child.GetName() for child in stage.GetPrimAtPath(path).GetChildren()
            if UsdGeom.Imageable(child).ComputeVisibility() != UsdGeom.Tokens.invisible]


def quaternion_at(attribute, time):
    """The hips' turn of a clip's rotations at `time`, as w x y z."""
    quaternion = attribute.Get(time)[1]
    return np.array([quaternion.GetReal(), *quaternion.GetImaginary()])


def test_characters_play_as_their_file_and_cast_say(tmp_path, monkeypatch):
    """The test body converted dressed and as an animal, the cast laid from it and the review's plan of that stage
    each answer as the file and the cast say; the cast's rules and check judge their inputs as the rows say."""
    import characters
    (tmp_path / "bodies").mkdir()
    body_glb(tmp_path / "bodies/tester.glb")
    for build in {cast.kit_mix(40 + number)["character"] for number in range(3)}:
        body_glb(tmp_path / f"bodies/{build}.glb")
    worlds = {"asset": Usd.Stage.Open(str(skel_usd.convert(tmp_path / "bodies/tester.glb", tmp_path / "assets"))),
              "animal": Usd.Stage.Open(str(skel_usd.convert(tmp_path / "bodies/tester.glb", tmp_path / "animal",
                                                            worn=None))),
              "stage": laid(tmp_path, FOUND)}
    monkeypatch.setattr(characters, "cast_of", lambda place: REVIEWED)
    planned = characters.plan("yard", tmp_path / "stage/yard.usda")
    asset, stage = worlds["asset"], worlds["stage"]

    for row, mesh, clip, frame, point, axes, where, atol in SKINNED:
        got = skinned(asset, mesh, clip, frame)[point][:axes]
        assert np.allclose(got, where, atol=atol), (row, got)
    for name, time, where in PLACED:
        got = UsdGeom.Xformable(stage.GetPrimAtPath(f"/yard/Characters/{name}")).ComputeLocalToWorldTransform(time)
        assert Gf.IsClose(got.ExtractTranslation(), Gf.Vec3d(*where), 1e-6), (name, time, got.ExtractTranslation())
    for row, world, path, shown in SHOWN:
        assert visible(worlds[world], path) == shown, (row, visible(worlds[world], path))
    for row, people, things, words in FAULTS:
        faults = cast_check.check({"people": people}, things)
        assert len(faults) == len(words) and all(any(word in fault for fault in faults) for word in words), \
            (row, faults)

    # The asset: joints parents first as paths, the hips bound a metre up, the file's half turn on Turned below a
    # root a cast transform sets, the dressed body's picture beside it.
    skeleton = UsdSkel.Skeleton(asset.GetPrimAtPath("/Character/Turned/Skeleton"))
    assert list(skeleton.GetJointsAttr().Get()) == ["Root", "Root/Hips"]
    assert Gf.IsClose(skeleton.GetBindTransformsAttr().Get()[1].ExtractTranslation(), Gf.Vec3d(0, 1, 0), 1e-6)
    turned = UsdGeom.Xformable(asset.GetPrimAtPath("/Character/Turned")).ComputeLocalToWorldTransform(0)
    assert Gf.IsClose(turned.TransformDir(Gf.Vec3d(0, 0, 1)), Gf.Vec3d(0, 0, -1), 1e-6)
    assert UsdGeom.Xformable(asset.GetPrimAtPath("/Character")).GetOrderedXformOps() == []
    assert (tmp_path / "assets/textures/tester_0.png").exists()

    # Its clips: the walk's two-frame cycle (its third key its first again) fills 12 s at 30 a second, 361 samples;
    # the door plays its two keys once; the walk's own length is kept.
    walk = UsdSkel.Animation(asset.GetPrimAtPath("/Character/Animations/walking")).GetRotationsAttr()
    assert len(walk.GetTimeSamples()) == 361 and walk.GetTimeSamples()[0] == 0
    assert np.allclose(quaternion_at(walk, 2), quaternion_at(walk, 0))
    assert np.allclose(quaternion_at(walk, 3), quaternion_at(walk, 1), atol=1e-6)
    assert not np.allclose(quaternion_at(walk, 3), quaternion_at(walk, 0), atol=1e-3)
    door = UsdSkel.Animation(asset.GetPrimAtPath("/Character/Animations/door")).GetRotationsAttr()
    assert door.GetTimeSamples() == [0.0, 1.0]
    lengths = asset.GetPrimAtPath("/Character").GetCustomDataByKey("score:clip_seconds")
    assert math.isclose(lengths["walking"], 2 / 30, rel_tol=1e-5)

    # The people route writes its correctives as dense morph targets (route_build.py): skel_usd keeps the points one
    # moves, as it does a sparse one's.
    values = np.array([[0, 0, 0], [0.1, 0, 0], [0, 0, 0], [0, -0.2, 0]], np.float32)
    dense = {"bufferViews": [{"buffer": 0, "byteLength": values.nbytes}],
             "accessors": [{"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3"}]}
    indices, offsets = skel_usd.sparse_values(dense, values.tobytes(), 0)
    assert indices.tolist() == [1, 3] and np.allclose(offsets, values[[1, 3]]), (indices, offsets)

    # The laid stage: each plays its clip; a held one a pose of its own, the clip's joints at its start with no time
    # samples; the row's second member starts half way into its 2/30 s clip, its reference offset back 1 time code.
    keeper = stage.GetPrimAtPath("/yard/Characters/keeper")
    assert keeper.IsA(UsdSkel.Root)
    assert keeper.GetPrimAtPath("Turned/Skeleton").GetRelationship("skel:animationSource").GetTargets() == \
        [Sdf.Path("/yard/Characters/keeper/Animations/door")]
    sleeper = stage.GetPrimAtPath("/yard/Characters/sleeper")
    assert sleeper.GetPrimAtPath("Turned/Skeleton").GetRelationship("skel:animationSource").GetTargets() == \
        [Sdf.Path("/yard/Characters/sleeper/Held")]
    pose = UsdSkel.Animation(sleeper.GetPrimAtPath("Held")).GetRotationsAttr()
    clip = UsdSkel.Animation(sleeper.GetPrimAtPath("Animations/walking")).GetRotationsAttr()
    assert pose.GetTimeSamples() == [] and list(pose.Get(30)) == list(clip.Get(0))
    member = stage.GetPrimAtPath("/yard/Characters/row_1")
    assert math.isclose(member.GetPrimStack()[0].referenceList.prependedItems[0].layerOffset.offset, -1.0,
                        abs_tol=1e-6)

    # The cast's rules from the same seeds are the same people in the same spots.
    mix, places, copies = cast.kit_mix(5003), cast.band_places(ROW), cast.crowd_copies(CROWD, keep_clear=[])
    assert (mix, places, copies) == (cast.kit_mix(5003), cast.band_places(ROW), cast.crowd_copies(CROWD, keep_clear=[]))
    assert mix["character"].startswith("kit_") and mix["worn"]["plain"][0].startswith("plain_")
    face = mix["worn"]["plain"][1].removeprefix("head_")
    assert mix["worn"]["plain"][2].endswith(f"_{face}"), "the hair is made on the face it is worn with"
    members = cast.characters_of({"groups": [{"name": "row", "count": 40, "seed": 5000, "band": [0.0, 0.0, 4.0, 20.0],
                                              "facing_to": [0, 0, -9], "doing": ["cheering"]}]})
    assert len({cast.look_of(member["character"], member["worn"]) for member in members}) == 40, "a new look each"
    # A character faces -z: one at the origin facing a point on -x is turned a quarter round, to its right.
    assert math.isclose(cast.facing_degrees([0, 0, 0], [-5, 0, 0]), 90.0)
    assert len(places) == 10 and all(-13 <= at[0] <= -5 and -16 <= at[2] <= 10 for at in places)
    assert all(-16 + 2.6 * number <= at[2] <= -16 + 2.6 * (number + 1) for number, at in enumerate(places)), \
        "spread evenly along the band"
    on_tier = [copy for copy in copies if -38 <= copy["at"][0] <= -15 and -40 <= copy["at"][2] <= 34]
    assert len(copies) == 400 and on_tier and all(copy["at"][1] == 0.8 for copy in on_tier), "standing on the tier"
    off_tier = [copy for copy in copies if copy not in on_tier and not (-38.9 <= copy["at"][0] <= -14.1
                                                                          and -40.9 <= copy["at"][2] <= 34.9)]
    assert off_tier and all(copy["at"][1] == 0.0 for copy in off_tier), "on the ground off the tiers"
    assert all(abs(copy["tall"] - 1) <= 0.06 for copy in copies)
    assert 0.6 < sum(copy["clip"] == 0 for copy in copies) / 400 < 0.8, "clips dealt by their shares"

    # The review's plan: a person seen close first from straight in front (2.6 m ahead of its -z front, at eye height
    # 1.6), the crowd from its own views and from what it faces, and the moving shots' frames in order.
    assert planned["closes"][0]["eyes"][0] == [1.0, 1.6, 2.0 - 2.6]
    assert [view["name"] for view in planned["wides"]] == ["crowd-above", "crowd-crowd-faced"]
    assert planned["moves"] == ["close-keeper", "crowd-above", "crowd-crowd-faced"]
    frames = [view["frame"] for view in planned["move_views"][:24]]
    assert frames == sorted(frames) and len(set(frames)) == 24
