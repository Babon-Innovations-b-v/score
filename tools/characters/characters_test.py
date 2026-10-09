"""Check the characters stage on a character made here: a two-joint body with a distant and a dressed mesh, a clip that
runs round and one that plays once. The UsdSkel asset skins its points where the glTF file's own skinning puts them,
keeps its joints parents first, repeats a running clip and holds a played-once one; the cast's spots, turns, kit mixes
and crowd are the cast's rules, repeated the same from the same seeds; the characters layer sits between the edit
layer and the base, every character plays its clip from its start and wears only its parts.

Run: .venv/bin/python tools/characters/characters_test.py   (make tests runs it with the framework's environment)
"""
import io
import json
import math
import pathlib
import struct
import sys
import tempfile

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
    `far` and `person`, skinned to Root and Hips; clips `walking` (runs round) and `door` (plays once)."""
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
    hips_at = [0.0, 1.0, 0.0]
    inverse_binds = blob.add([np.eye(4).reshape(-1),
                              np.linalg.inv(np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], hips_at + [1]],
                                                     float).T).T.reshape(-1)], np.float32, "MAT4")
    walk_times = blob.add([0.0, 1 / 30, 2 / 30], np.float32, "SCALAR")
    walk_turns = blob.add([[0, 0, 0, 1], QUARTER, [0, 0, 0, 1]], np.float32, "VEC4")
    walk_places = blob.add([hips_at, [0.0, 1.1, 0.0], hips_at], np.float32, "VEC3")
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
                                             {"input": walk_times, "output": walk_places}],
             "channels": [{"sampler": 0, "target": {"node": 2, "path": "rotation"}},
                          {"sampler": 1, "target": {"node": 2, "path": "translation"}}]},
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
    """The mesh's points as UsdSkel skins them with `clip` playing, at `time`."""
    skeleton = stage.GetPrimAtPath("/Character/Turned/Skeleton")
    UsdSkel.BindingAPI(skeleton).GetAnimationSourceRel().SetTargets([f"/Character/Animations/{clip}"])
    cache = UsdSkel.Cache()
    cache.Populate(UsdSkel.Root(stage.GetPrimAtPath("/Character")), Usd.PrimDefaultPredicate)
    transforms = cache.GetSkelQuery(UsdSkel.Skeleton(skeleton)).ComputeSkinningTransforms(time)
    mesh = stage.GetPrimAtPath(mesh_path)
    points = mesh.GetAttribute("points").Get()
    cache.GetSkinningQuery(mesh).ComputeSkinnedPoints(transforms, points, time)
    return np.array(points)


def test_asset(folder):
    asset = skel_usd.convert(body_glb(folder / "bodies/tester.glb"), folder / "assets")
    stage = Usd.Stage.Open(str(asset))
    skeleton = UsdSkel.Skeleton(stage.GetPrimAtPath("/Character/Turned/Skeleton"))
    assert list(skeleton.GetJointsAttr().Get()) == ["Root", "Root/Hips"]
    binds = skeleton.GetBindTransformsAttr().Get()
    assert Gf.IsClose(binds[1].ExtractTranslation(), Gf.Vec3d(0, 1, 0), 1e-6), "bind is the inverse of the file's"
    # The file's turn half round is on Turned, so a cast transform on the root never replaces it.
    turned = UsdGeom.Xformable(stage.GetPrimAtPath("/Character/Turned")).ComputeLocalToWorldTransform(0)
    assert Gf.IsClose(turned.TransformDir(Gf.Vec3d(0, 0, 1)), Gf.Vec3d(0, 0, -1), 1e-6)
    # At rest the points are the file's; one frame into the walk the hips' points have turned a quarter round z
    # about the hips and risen 0.1 m, as the file's own skinning does; the root's points never move.
    rest = skinned(stage, "/Character/Turned/Body/person/jacket_0", "walking", 0)
    assert np.allclose(rest[2], [-0.2, 1.5, 0.0], atol=1e-5)
    moved = skinned(stage, "/Character/Turned/Body/person/jacket_0", "walking", 1)
    turn = np.array([[math.cos(math.pi / 4), -math.sin(math.pi / 4)], [math.sin(math.pi / 4), math.cos(math.pi / 4)]])
    expected = turn @ np.array([-0.2, 0.5]) + [0.0, 1.1]
    assert np.allclose(moved[2][:2], expected, atol=1e-5), (moved[2], expected)
    assert np.allclose(moved[0], [-0.2, 0.0, 0.0], atol=1e-6)
    # The walk runs round: its two-frame cycle is repeated for the whole length; the door plays once and holds.
    walk = UsdSkel.Animation(stage.GetPrimAtPath("/Character/Animations/walking")).GetRotationsAttr()
    samples = walk.GetTimeSamples()
    assert len(samples) == skel_usd.SECONDS * skel_usd.RATE + 1 and samples[0] == 0
    def turn_of(time):
        quaternion = walk.Get(time)[1]
        return np.array([quaternion.GetReal(), *quaternion.GetImaginary()])
    assert np.allclose(turn_of(2), turn_of(0)) and not np.allclose(turn_of(3), turn_of(0), atol=1e-3)
    door = UsdSkel.Animation(stage.GetPrimAtPath("/Character/Animations/door")).GetRotationsAttr()
    assert door.GetTimeSamples() == [0.0, 1.0]
    # The dressed body is worn and the distant one hidden by default; the picture is written beside the asset.
    far = UsdGeom.Imageable(stage.GetPrimAtPath("/Character/Turned/Body/far"))
    assert far.ComputeVisibility() == UsdGeom.Tokens.invisible
    assert (folder / "assets/textures/tester_0.png").exists()
    lengths = stage.GetPrimAtPath("/Character").GetCustomDataByKey("score:clip_seconds")
    assert math.isclose(lengths["walking"], 2 / 30, rel_tol=1e-5)
    # An animal wears every mesh of its file: nothing is hidden when no outfit is named.
    every = Usd.Stage.Open(str(skel_usd.convert(folder / "bodies/tester.glb", folder / "animal", worn=None)))
    far = UsdGeom.Imageable(every.GetPrimAtPath("/Character/Turned/Body/far"))
    assert far.ComputeVisibility() == UsdGeom.Tokens.inherited


def test_cast_rules():
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
    assert all(abs(copy["tall"] - 1) <= 0.06 for copy in copies)
    assert 0.6 < sum(copy["clip"] == 0 for copy in copies) / 400 < 0.8, "clips dealt by their shares"


def test_layer(folder):
    stage_folder = folder / "stage"
    (stage_folder / "layers").mkdir(parents=True)
    root = Sdf.Layer.CreateNew(str(stage_folder / "yard.usda"))
    root.subLayerPaths.append("./layers/edit.usda")
    root.subLayerPaths.append("./layers/base.usda")
    root.Save()
    for name in ("edit", "base"):
        Sdf.Layer.CreateNew(str(stage_folder / f"layers/{name}.usda")).Save()
    for build in {cast.kit_mix(40 + number)["character"] for number in range(3)}:
        body_glb(folder / f"bodies/{build}.glb")
    found = {"people": [{"name": "keeper", "character": "tester", "doing": "door", "at": [1.0, 0.0, 2.0],
                         "facing_to": [1.0, 0.0, -5.0], "why": "keeps the door"},
                        {"name": "walker", "character": "tester", "doing": "walking", "at": [0.0, 0.0, 0.0],
                         "path": [[0.0, 0.0, 0.0], [0.0, 0.0, -4.0]], "pace": 2.0, "facing_to": [0, 0, -1],
                         "why": "walks by"},
                        {"name": "sleeper", "character": "tester", "doing": "walking", "at": [3.0, 0.0, 0.0],
                         "facing_to": [3.0, 0.0, -1.0], "held": True, "why": "lies still"}],
             "groups": [{"name": "row", "character": "kit", "outfit": "plain", "count": 3, "seed": 40,
                         "band": [0.0, 0.0, 2.0, 6.0], "doing": ["walking"], "phase_step": 0.5,
                         "facing_to": [0, 0, -9], "why": "a row"}]}
    placed = cast.write_layer("yard", found, stage_folder, folder / "bodies")
    assert placed == {"characters": 6, "crowd": 0, "layer": str(stage_folder / cast.LAYER)}
    assert list(Sdf.Layer.FindOrOpen(str(stage_folder / "yard.usda")).subLayerPaths) == [
        "./layers/edit.usda", "./layers/characters.usda", "./layers/base.usda"]
    stage = Usd.Stage.Open(str(stage_folder / "yard.usda"))
    keeper = stage.GetPrimAtPath("/yard/Characters/keeper")
    assert keeper.IsA(UsdSkel.Root)
    source = stage.GetPrimAtPath("/yard/Characters/keeper/Turned/Skeleton").GetRelationship("skel:animationSource")
    assert source.GetTargets() == [Sdf.Path("/yard/Characters/keeper/Animations/door")]
    at = UsdGeom.Xformable(keeper).ComputeLocalToWorldTransform(0).ExtractTranslation()
    assert Gf.IsClose(at, Gf.Vec3d(1, 0, 2), 1e-6)
    # The walker covers its 4 m at 2 m a second: at 2 s (60 time codes) it is at the path's end.
    walker = UsdGeom.Xformable(stage.GetPrimAtPath("/yard/Characters/walker"))
    end = walker.ComputeLocalToWorldTransform(60).ExtractTranslation()
    assert Gf.IsClose(end, Gf.Vec3d(0, 0, -4), 1e-6), end
    # A held character plays a pose of its own: the clip's joints at its start, with no time samples.
    sleeper = "/yard/Characters/sleeper"
    source = stage.GetPrimAtPath(f"{sleeper}/Turned/Skeleton").GetRelationship("skel:animationSource")
    assert source.GetTargets() == [Sdf.Path(f"{sleeper}/Held")]
    pose = UsdSkel.Animation(stage.GetPrimAtPath(f"{sleeper}/Held")).GetRotationsAttr()
    clip = UsdSkel.Animation(stage.GetPrimAtPath(f"{sleeper}/Animations/walking")).GetRotationsAttr()
    assert pose.GetTimeSamples() == [] and list(pose.Get(30)) == list(clip.Get(0))
    # The row's second member starts half way into its clip: its reference is offset back by that much.
    member = stage.GetPrimAtPath("/yard/Characters/row_1")
    offset = member.GetPrimStack()[0].referenceList.prependedItems[0].layerOffset.offset
    assert math.isclose(offset, -0.5 * (2 / 30) * skel_usd.RATE, abs_tol=1e-6)
    shown = [child.GetName() for child in stage.GetPrimAtPath("/yard/Characters/row_0/Turned/Body").GetChildren()
             if UsdGeom.Imageable(child).ComputeVisibility() != UsdGeom.Tokens.invisible]
    assert shown == [], "a kit member wears only the kit's parts, which this test body has none of"
    # Run again: the layer is rewritten whole and the root keeps one copy of it.
    cast.write_layer("yard", found, stage_folder, folder / "bodies")
    assert list(Sdf.Layer.FindOrOpen(str(stage_folder / "yard.usda")).subLayerPaths).count(
        "./layers/characters.usda") == 1


def test_review_plan(folder):
    import characters
    found = {"people": [{"name": "keeper", "character": "tester", "doing": "door", "at": [1.0, 0.0, 2.0],
                         "facing_to": [1.0, 0.0, -5.0], "why": "keeps the door"}],
             "crowd": {"name": "crowd", "count": 5, "spread": [0, 0, 4, 4], "facing_to": [0, 0, -9],
                       "views": [{"name": "above", "eye": [0, 9, 0], "aim": [2, 0, 2]}]}}
    characters.cast_of = lambda place: found
    planned = characters.plan("yard", folder / "stage/yard.usda")
    close = planned["closes"][0]
    assert close["eyes"][0] == [1.0, 1.6, 2.0 - characters.CLOSE_DISTANCE], "first from straight in front"
    assert [view["name"] for view in planned["wides"]] == ["crowd-above", "crowd-crowd-faced"]
    assert planned["moves"] == ["close-keeper", "crowd-above", "crowd-crowd-faced"]
    frames = [view["frame"] for view in planned["move_views"][:characters.MOVE_FRAMES]]
    assert frames == sorted(frames) and len(set(frames)) == characters.MOVE_FRAMES


def test_cast_check():
    """The cast check finds the same person twice (a named body, a kit look), a walk through somebody standing and a
    walk through a thing between knee and head, passes a walk round them, steps over a floor plate, and a group is
    dealt a new look for every member."""
    walker = {"name": "walker", "character": "bram", "doing": "walking", "at": [0.0, 0.0, 0.0], "facing_to": [4, 0, 0],
              "path": [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0]]}
    standing = {"name": "standing", "character": "take_c", "doing": "waiting", "at": [2.0, 0.0, 0.2],
                "facing_to": [2.0, 0.0, 1.0]}
    twice = {"people": [walker, dict(standing, name="again", at=[9.0, 0.0, 9.0]), standing]}
    assert cast_check.repeated_people(twice) == ["again and standing are the same person (take_c)"]
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
    looks = {cast.look_of(member["character"], member["worn"]) for member in members}
    assert len(looks) == len(members) == 40


def main():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        (folder / "bodies").mkdir()
        test_asset(folder)
        test_cast_rules()
        test_cast_check()
        test_layer(folder)
        test_review_plan(folder)
    print("characters_test: ok")


if __name__ == "__main__":
    main()
