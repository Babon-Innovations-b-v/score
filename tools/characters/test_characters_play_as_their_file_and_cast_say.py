"""A character plays as its file and its cast say: the UsdSkel asset (skel_usd.py) skins its points where the glTF
file's own skinning puts them, its joints parents first and the file's half turn kept below the root, repeats a
running clip for the whole length and holds a played-once one, and wears its dressed body (an animal every mesh); the
cast's rules (cast.py) give the same people in the same spots from the same seeds, a crowd on its tiers by its
shares; the cast check (cast_check.py) refuses the same person twice and a walk through somebody or something; laid
with the cast's prims, every character stands or walks where the cast puts it, plays its clip from its start and
wears only its parts; and the review page (tools/review/characters.py) sees each from in front.

A two-joint body made here (a distant and a dressed mesh, a clip that runs round and one that plays once, a sparse
morph target keyed on in the walk's second frame) whose skinned points are worked out by hand in each test.

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_the_asset_skins_its_points_where_the_files_own_skinning_puts_them: convert's bind `matrix(values).GetInverse()`
  made `matrix(values)`; and, apart, write_part's `if shape_names:` made `if False:` (no blend shapes); and, apart,
  joint_paths' `"/".join(reversed(trail))` made `"/".join(trail)`.
- test_the_files_half_turn_is_kept_below_the_root: convert's `turned.AddTransformOp().Set(local_matrix(scene_root))`
  made `.Set(Gf.Matrix4d(1))`.
- test_a_running_clip_repeats_for_the_whole_length_and_a_played_once_one_holds: repeated's `cycle = keys[:-1] if ...
  else keys` made `cycle = keys`; and, apart, write_clips' `once = animation["name"] in ONCE` made `once = False`.
- test_a_person_wears_the_dressed_body_and_an_animal_every_mesh: write_body's `if worn is not None and name not in
  worn:` made `if name not in (worn or ()):`.
- test_a_dense_morph_target_keeps_the_points_it_moves: sparse_values keeps every point (its nonzero pick dropped).
- test_the_casts_rules_are_the_same_from_the_same_seeds: kit_mix's `random.Random(seed)` made `random.Random()`;
  and, apart, band_places' `along * (number + draw.random()) / group["count"]` made `along * draw.random()`.
- test_a_crowd_stands_on_its_tiers_clear_of_the_ground_kept_off_with_its_clips_by_their_shares: crowd_copies'
  `at = [x, ground_at(boxes, x, z), z]` made `at = [x, 0.0, z]`.
- test_the_cast_check_refuses_the_same_person_twice_and_a_walk_through_somebody: clash_with_things' `if top < feet +
  KNEE or bottom > feet + HEAD: continue` dropped (the floor plate counts); and, apart, look_of's head and hair parts
  dropped (`*sorted(...)` removed: two kit people of one build read the same).
- test_a_laid_character_stands_or_walks_where_the_cast_puts_it: walked's `seconds += math.dist(here, there) / pace`
  made `seconds += math.dist(here, there)`.
- test_a_laid_character_plays_its_clip_from_its_start_and_wears_only_its_parts: referenced's
  `Sdf.LayerOffset(-start_seconds * skel_usd.RATE)` made `Sdf.LayerOffset(0)`; and, apart, held_still's
  `GetRotationsAttr().Get(time)` made `.Get(time + 1)`.
- test_the_review_sees_a_person_from_in_front_and_a_crowd_from_its_views: tools/review/characters.py ahead's
  `at[2] - math.cos(angle) * distance` made `at[2] + ...`.
"""

import io
import json
import math
import pathlib
import struct
import sys

import numpy as np
import pytest
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


@pytest.fixture(scope="module")
def folder(tmp_path_factory):
    """The test's world: the test body and the kit builds the row's members are dealt, as body files."""
    found = tmp_path_factory.mktemp("characters")
    (found / "bodies").mkdir()
    body_glb(found / "bodies/tester.glb")
    for build in {cast.kit_mix(40 + number)["character"] for number in range(3)}:
        body_glb(found / f"bodies/{build}.glb")
    return found


@pytest.fixture(scope="module")
def asset(folder):
    return Usd.Stage.Open(str(skel_usd.convert(folder / "bodies/tester.glb", folder / "assets")))


def test_the_asset_skins_its_points_where_the_files_own_skinning_puts_them(asset):
    """At rest the points are the file's; one frame into the walk the hips' points have turned a quarter round z about
    the hips and risen 0.1 m, the third one moved 0.1 m along x first by its morph target (a blend shape here); the
    root's points never move; the far body has no shapes; the shape is keyed off again at frame 2."""
    skeleton = UsdSkel.Skeleton(asset.GetPrimAtPath("/Character/Turned/Skeleton"))
    assert list(skeleton.GetJointsAttr().Get()) == ["Root", "Root/Hips"]  # parents first, as paths
    assert Gf.IsClose(skeleton.GetBindTransformsAttr().Get()[1].ExtractTranslation(), Gf.Vec3d(0, 1, 0), 1e-6)
    person = "/Character/Turned/Body/person/jacket_0"
    assert np.allclose(skinned(asset, person, "walking", 0)[2], [-0.2, 1.5, 0.0], atol=1e-5)
    moved = skinned(asset, person, "walking", 1)
    turn = np.array([[math.cos(math.pi / 4), -math.sin(math.pi / 4)], [math.sin(math.pi / 4), math.cos(math.pi / 4)]])
    assert np.allclose(moved[2][:2], turn @ np.array([-0.1, 0.5]) + [0.0, 1.1], atol=1e-5), moved[2]
    assert np.allclose(moved[0], [-0.2, 0.0, 0.0], atol=1e-6)
    assert np.allclose(skinned(asset, "/Character/Turned/Body/far/clothes_0", "walking", 1)[2][:2],
                       turn @ np.array([-0.2, 0.5]) + [0.0, 1.1], atol=1e-5)
    assert np.allclose(skinned(asset, person, "walking", 2)[2], [-0.2, 1.5, 0.0], atol=1e-5)


def test_the_files_half_turn_is_kept_below_the_root(asset):
    """The file's turn half round is on Turned, so a cast transform on the root never replaces it."""
    turned = UsdGeom.Xformable(asset.GetPrimAtPath("/Character/Turned")).ComputeLocalToWorldTransform(0)
    assert Gf.IsClose(turned.TransformDir(Gf.Vec3d(0, 0, 1)), Gf.Vec3d(0, 0, -1), 1e-6)
    assert UsdGeom.Xformable(asset.GetPrimAtPath("/Character")).GetOrderedXformOps() == []


def test_a_running_clip_repeats_for_the_whole_length_and_a_played_once_one_holds(asset):
    """The walk's two-frame cycle (its third key is its first again) fills 12 s at 30 a second, 361 samples; the door
    plays its two keys once."""
    walk = UsdSkel.Animation(asset.GetPrimAtPath("/Character/Animations/walking")).GetRotationsAttr()
    samples = walk.GetTimeSamples()
    assert len(samples) == 361 and samples[0] == 0

    def turn_of(time):
        quaternion = walk.Get(time)[1]
        return np.array([quaternion.GetReal(), *quaternion.GetImaginary()])
    assert np.allclose(turn_of(2), turn_of(0)) and np.allclose(turn_of(3), turn_of(1), atol=1e-6)
    assert not np.allclose(turn_of(3), turn_of(0), atol=1e-3)
    door = UsdSkel.Animation(asset.GetPrimAtPath("/Character/Animations/door")).GetRotationsAttr()
    assert door.GetTimeSamples() == [0.0, 1.0]
    lengths = asset.GetPrimAtPath("/Character").GetCustomDataByKey("score:clip_seconds")
    assert math.isclose(lengths["walking"], 2 / 30, rel_tol=1e-5)


def test_a_person_wears_the_dressed_body_and_an_animal_every_mesh(folder, asset):
    """The dressed body is worn and the distant one hidden by default, its picture written beside the asset; an
    animal names no outfit and wears every mesh of its file."""
    far = UsdGeom.Imageable(asset.GetPrimAtPath("/Character/Turned/Body/far"))
    assert far.ComputeVisibility() == UsdGeom.Tokens.invisible
    assert (folder / "assets/textures/tester_0.png").exists()
    every = Usd.Stage.Open(str(skel_usd.convert(folder / "bodies/tester.glb", folder / "animal", worn=None)))
    assert UsdGeom.Imageable(every.GetPrimAtPath("/Character/Turned/Body/far")).ComputeVisibility() == \
        UsdGeom.Tokens.inherited


def test_a_dense_morph_target_keeps_the_points_it_moves():
    """The people route writes its correctives as dense morph targets (route_build.py): skel_usd keeps the points one
    moves, as it does a sparse one's."""
    values = np.array([[0, 0, 0], [0.1, 0, 0], [0, 0, 0], [0, -0.2, 0]], np.float32)
    document = {"bufferViews": [{"buffer": 0, "byteLength": values.nbytes}],
                "accessors": [{"bufferView": 0, "componentType": 5126, "count": 4, "type": "VEC3"}]}
    indices, offsets = skel_usd.sparse_values(document, values.tobytes(), 0)
    assert indices.tolist() == [1, 3] and np.allclose(offsets, values[[1, 3]]), (indices, offsets)


def test_the_casts_rules_are_the_same_from_the_same_seeds():
    mix = cast.kit_mix(5003)
    assert mix == cast.kit_mix(5003), "the same seed is the same person"
    assert mix["character"].startswith("kit_") and mix["worn"]["plain"][0].startswith("plain_")
    face = mix["worn"]["plain"][1].removeprefix("head_")
    assert mix["worn"]["plain"][2].endswith(f"_{face}"), "the hair is made on the face it is worn with"
    # A character faces -z: one at the origin facing a point on -x is turned a quarter round, to its right.
    assert math.isclose(cast.facing_degrees([0, 0, 0], [-5, 0, 0]), 90.0)
    group = {"name": "row", "count": 10, "seed": 7, "band": [-13.0, -16.0, 8.0, 26.0], "facing_to": [-45, 3, 0],
             "doing": ["standing", "clapping"], "phase_step": 0.37}
    places = cast.band_places(group)
    assert places == cast.band_places(group) and len(places) == 10
    assert all(-13 <= at[0] <= -5 and -16 <= at[2] <= 10 for at in places)
    assert [at[2] for at in places] == sorted(at[2] for at in places), "spread evenly along the band"
    assert all(-16 + 2.6 * number <= at[2] <= -16 + 2.6 * (number + 1) for number, at in enumerate(places))


def test_a_crowd_stands_on_its_tiers_clear_of_the_ground_kept_off_with_its_clips_by_their_shares():
    crowd = {"name": "crowd", "count": 400, "seed": 3, "spread": [-42.0, -56.0, 38.4, 112.0],
             "kept_off": [[-44.0, -13.0, 4.5, 19.0]], "clear_radius": 0.7,
             "tiers": [[-38.0, 0.0, -40.0, 23.0, 0.8, 74.0]], "tier_tread": 0.9, "tier_half_step": 0.4,
             "facing_to": [-45.5, 3.3, -3.5], "turn_jitter": 0.35, "height_jitter": 0.06,
             "doing": ["standing", "cheering"], "shares": [0.7, 0.3], "phases": 2,
             "palettes": [[[1, 2, 3]], [[4, 5, 6]]], "palette_parts": ["skin"], "palette_shares": [0.5, 0.5]}
    copies = cast.crowd_copies(crowd, keep_clear=[])
    assert copies == cast.crowd_copies(crowd, keep_clear=[]) and len(copies) == 400
    on_tier = [copy for copy in copies if -38 <= copy["at"][0] <= -15 and -40 <= copy["at"][2] <= 34]
    assert on_tier and all(copy["at"][1] == 0.8 for copy in on_tier), "standing on the tier's top"
    off_tier = [copy for copy in copies if copy not in on_tier and not (-38.9 <= copy["at"][0] <= -14.1
                                                                          and -40.9 <= copy["at"][2] <= 34.9)]
    assert off_tier and all(copy["at"][1] == 0.0 for copy in off_tier), "on the ground off the tiers"
    assert all(abs(copy["tall"] - 1) <= 0.06 for copy in copies)
    assert 0.6 < sum(copy["clip"] == 0 for copy in copies) / 400 < 0.8, "clips dealt by their shares"


def test_the_cast_check_refuses_the_same_person_twice_and_a_walk_through_somebody():
    """The cast check finds the same person twice (a named body, a kit look), a walk through somebody standing and a
    walk through a thing between knee and head, passes a walk round them, steps over a floor plate, and a group is
    dealt a new look for every member (owner, 2026-10-09: nobody twice, walks clear)."""
    walker = {"name": "walker", "character": "bram", "doing": "walking", "at": [0.0, 0.0, 0.0], "facing_to": [4, 0, 0],
              "path": [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0]]}
    standing = {"name": "standing", "character": "take_c", "doing": "waiting", "at": [2.0, 0.0, 0.2],
                "facing_to": [2.0, 0.0, 1.0]}
    twice = {"people": [walker, dict(standing, name="again", at=[9.0, 0.0, 9.0]), standing]}
    assert cast_check.repeated_people(twice) == ["again and standing are the same person (take_c)"]
    told_apart = {"people": [dict(standing, variant=1), dict(standing, name="again", variant=2)]}
    assert cast_check.repeated_people(told_apart) == [], "one body in two variants is two people"
    assert any("from standing" in fault for fault in cast_check.walk_faults({"people": [walker, standing]}, []))
    crate = ("Objects/crate_1", (1.8, -0.3, 2.4, 0.3), 0.0, 0.8)
    plate = ("Objects/plate_1", (1.0, -1.0, 3.0, 1.0), -0.05, 0.02)
    faults = cast_check.walk_faults({"people": [walker]}, [crate, plate])
    assert len(faults) == 1 and "crate_1" in faults[0], faults
    round_them = dict(walker, path=[[0.0, 0.0, 0.0], [2.0, 0.0, -1.2], [4.0, 0.0, 0.0]])
    assert cast_check.check({"people": [round_them, standing]}, [crate, plate]) == []
    group = {"name": "row", "count": 40, "seed": 5000, "band": [0.0, 0.0, 4.0, 20.0], "facing_to": [0, 0, -9],
             "doing": ["cheering"]}
    members = cast.characters_of({"groups": [group]})
    assert len({cast.look_of(member["character"], member["worn"]) for member in members}) == 40


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


@pytest.fixture(scope="module")
def stage(folder):
    return laid(folder, FOUND)


def test_a_laid_character_stands_or_walks_where_the_cast_puts_it(stage):
    keeper = stage.GetPrimAtPath("/yard/Characters/keeper")
    assert keeper.IsA(UsdSkel.Root)
    at = UsdGeom.Xformable(keeper).ComputeLocalToWorldTransform(0).ExtractTranslation()
    assert Gf.IsClose(at, Gf.Vec3d(1, 0, 2), 1e-6)
    # The walker covers its 4 m at 2 m a second: at 2 s (60 time codes) it is at the path's end, at 1 s half way.
    walker = UsdGeom.Xformable(stage.GetPrimAtPath("/yard/Characters/walker"))
    assert Gf.IsClose(walker.ComputeLocalToWorldTransform(60).ExtractTranslation(), Gf.Vec3d(0, 0, -4), 1e-6)
    assert Gf.IsClose(walker.ComputeLocalToWorldTransform(30).ExtractTranslation(), Gf.Vec3d(0, 0, -2), 1e-6)


def test_a_laid_character_plays_its_clip_from_its_start_and_wears_only_its_parts(stage):
    source = stage.GetPrimAtPath("/yard/Characters/keeper/Turned/Skeleton").GetRelationship("skel:animationSource")
    assert source.GetTargets() == [Sdf.Path("/yard/Characters/keeper/Animations/door")]
    # A held character plays a pose of its own: the clip's joints at its start, with no time samples.
    sleeper = "/yard/Characters/sleeper"
    source = stage.GetPrimAtPath(f"{sleeper}/Turned/Skeleton").GetRelationship("skel:animationSource")
    assert source.GetTargets() == [Sdf.Path(f"{sleeper}/Held")]
    pose = UsdSkel.Animation(stage.GetPrimAtPath(f"{sleeper}/Held")).GetRotationsAttr()
    clip = UsdSkel.Animation(stage.GetPrimAtPath(f"{sleeper}/Animations/walking")).GetRotationsAttr()
    assert pose.GetTimeSamples() == [] and list(pose.Get(30)) == list(clip.Get(0))
    # The row's second member starts half way into its 2/30 s clip: its reference is offset back by 1 time code.
    member = stage.GetPrimAtPath("/yard/Characters/row_1")
    offset = member.GetPrimStack()[0].referenceList.prependedItems[0].layerOffset.offset
    assert math.isclose(offset, -1.0, abs_tol=1e-6)
    shown = [child.GetName() for child in stage.GetPrimAtPath("/yard/Characters/row_0/Turned/Body").GetChildren()
             if UsdGeom.Imageable(child).ComputeVisibility() != UsdGeom.Tokens.invisible]
    assert shown == [], "a kit member wears only the kit's parts, which this test body has none of"


def test_the_review_sees_a_person_from_in_front_and_a_crowd_from_its_views(folder, stage, monkeypatch):
    """The review page's plan (tools/review/characters.py): a person seen close first from straight in front (2.6 m
    ahead of its -z front, at eye height 1.6), the crowd from its own views and from what it faces, and the moving
    shots' frames in order."""
    import characters
    found = {"people": [{"name": "keeper", "character": "tester", "doing": "door", "at": [1.0, 0.0, 2.0],
                         "facing_to": [1.0, 0.0, -5.0], "why": "keeps the door"}],
             "crowd": {"name": "crowd", "count": 5, "spread": [0, 0, 4, 4], "facing_to": [0, 0, -9],
                       "views": [{"name": "above", "eye": [0, 9, 0], "aim": [2, 0, 2]}]}}
    monkeypatch.setattr(characters, "cast_of", lambda place: found)
    planned = characters.plan("yard", folder / "stage/yard.usda")
    assert planned["closes"][0]["eyes"][0] == [1.0, 1.6, 2.0 - 2.6]
    assert [view["name"] for view in planned["wides"]] == ["crowd-above", "crowd-crowd-faced"]
    assert planned["moves"] == ["close-keeper", "crowd-above", "crowd-crowd-faced"]
    frames = [view["frame"] for view in planned["move_views"][:24]]
    assert frames == sorted(frames) and len(set(frames)) == 24
