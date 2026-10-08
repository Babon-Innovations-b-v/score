"""Check the place's OpenUSD stage on a place made here of two boxes: a creator's edit in the edit layer (an object
moved, a part given another library surface) survives a regenerated base; parts become subsets by surface; the
stage is in metres with y up and every object has a static collider; a kit room's pieces stand in their own frames
as the game lays them, a glowing part named apart from its host, its parts read from its bake job.

Run: .venv/bin/python tools/usd/export_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
import trimesh
from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export  # noqa: E402

PLACE = "wreck"  # a place the library knows; its layout and inventory here are the test's own
TOP, BOTTOM, EDITED = "hull_white_scorched", "bare_steel", "cast_iron_dark"


def box_gltf(folder, name="box", shape=None):
    """A 1 m box standing on its foot (or any other `shape`), as a made model `name`: one node, one primitive,
    normals, uvs and baked maps."""
    box = shape.copy() if shape is not None else trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    if shape is None:
        box.apply_translation((0.0, 0.5, 0.0))
    box = box.unmerge_vertices() or box
    positions = np.asarray(box.vertices, dtype=np.float32)
    normals = np.asarray(box.vertex_normals, dtype=np.float32)
    uvs = (positions[:, [0, 2]] + 0.5).astype(np.float32)
    indices = np.asarray(box.faces, dtype=np.uint32).reshape(-1)
    blobs = [positions.tobytes(), normals.tobytes(), uvs.tobytes(), indices.tobytes()]
    offsets = np.cumsum([0] + [len(blob) for blob in blobs])
    (folder / f"{name}.bin").write_bytes(b"".join(blobs))
    (folder / "textures").mkdir(exist_ok=True)
    for role in ("base_color", "metal_roughness", "normal"):
        Image.new("RGB", (8, 8), (200, 120, 60)).save(folder / f"textures/{name}_{role}.webp")
    accessor = [{"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3",
                 "min": positions.min(axis=0).tolist(), "max": positions.max(axis=0).tolist()},
                {"bufferView": 1, "componentType": 5126, "count": len(positions), "type": "VEC3"},
                {"bufferView": 2, "componentType": 5126, "count": len(positions), "type": "VEC2"},
                {"bufferView": 3, "componentType": 5125, "count": len(indices), "type": "SCALAR"}]
    document = {
        "asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": name}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3,
                                    "material": 0}]}],
        "materials": [{"name": f"{name}_game", "normalTexture": {"index": 2}, "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0}, "metallicRoughnessTexture": {"index": 1}}}],
        "textures": [{"extensions": {"EXT_texture_webp": {"source": index}}} for index in range(3)],
        "images": [{"uri": f"textures/{name}_{role}.webp"} for role in ("base_color", "metal_roughness", "normal")],
        "accessors": accessor,
        "bufferViews": [{"buffer": 0, "byteOffset": int(offsets[index]), "byteLength": len(blob)}
                        for index, blob in enumerate(blobs)],
        "buffers": [{"uri": f"{name}.bin", "byteLength": int(offsets[-1])}],
    }
    (folder / f"{name}.gltf").write_text(json.dumps(document))


def labelled_parts(folder, take="r1", halves=((TOP, 0.5, 1.0), (BOTTOM, 0.0, 0.5))):
    """The box's labelled take: its top half one library surface, its bottom half another."""
    take = folder / f"box-{take}"
    take.mkdir(parents=True)
    for name, low, high in halves:
        part = trimesh.creation.box(bounds=((-0.5, low, -0.5), (0.5, high, 0.5))).subdivide().subdivide()
        part.export(take / f"{name}.ply")


def place_files(folder, second_at, children=()):
    """The place's layout (two boxes of one row, the second at `second_at`, and any `children` standing on them) and
    its inventory."""
    piece = {"prop": "test_box", "kind": "test_box", "model": "box", "row": "box", "size": [1.0, 1.0, 1.0]}
    kit = {"place": PLACE, "pieces": [dict(piece, at=[0.0, 0.0, 0.0], facing=0.0),
                                      dict(piece, at=list(second_at), facing=90.0)], "lamps": [],
           "children": [{"row": row, "on": "box"} for row in children]}
    inventory = {"rows": [{"id": "box", "name": "a crate", "anchor": "floor", "thing": "prop:test_box"}]
                 + [{"id": row, "name": "a can", "anchor": "on:box", "thing": f"prop:test_{row}"} for row in children]}
    (folder / "kit.json").write_text(json.dumps(kit))
    (folder / "inventory.json").write_text(json.dumps(inventory))


def exported(folder, second_at, children=(), take=None):
    place_files(folder, second_at, children)
    return export.export(PLACE, folder / "models", folder / "stage", parts=folder / "parts",
                         kit_path=folder / "kit.json", inventory_path=folder / "inventory.json", take=take)


def made_place(folder):
    (folder / "models").mkdir()
    box_gltf(folder / "models")
    labelled_parts(folder / "parts")


def creators_edit(stage_path):
    """What a creator does in the edit layer: move the first box, give its bottom part another surface."""
    stage = Usd.Stage.Open(str(stage_path))
    edit = stage.GetLayerStack()[2]
    if not edit.identifier.endswith("layers/edit.usda"):
        raise AssertionError(f"the layer under the stage's own is {edit.identifier}, not the edit layer")
    stage.SetEditTarget(Usd.EditTarget(edit))
    box = stage.GetPrimAtPath(f"/{PLACE}/Objects/box_1")
    box.GetAttribute("xformOp:translate").Set(Gf.Vec3d(5.0, 0.0, 1.0))
    part = stage.GetPrimAtPath(f"/{PLACE}/Objects/box_1/geo/{BOTTOM}")
    UsdShade.MaterialBindingAPI(part).Bind(UsdShade.Material(stage.GetPrimAtPath(f"/{PLACE}/Library/{EDITED}")))
    part.GetAttribute("score:surface").Set(EDITED)
    edit.Save()


def an_edit_survives_a_regenerated_base():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_place(folder)
        creators_edit(exported(folder, (2.0, 0.0, 0.0)))
        stage = Usd.Stage.Open(str(exported(folder, (3.0, 0.0, -1.0))))
        moved = stage.GetPrimAtPath(f"/{PLACE}/Objects/box_1").GetAttribute("xformOp:translate").Get()
        part = stage.GetPrimAtPath(f"/{PLACE}/Objects/box_1/geo/{BOTTOM}")
        bound = UsdShade.MaterialBindingAPI(part).ComputeBoundMaterial()[0].GetPath()
        regenerated = stage.GetPrimAtPath(f"/{PLACE}/Objects/box_2").GetAttribute("xformOp:translate").Get()
        problems = []
        if moved != Gf.Vec3d(5.0, 0.0, 1.0):
            problems.append(f"the moved box is at {moved} after the base was made again")
        if bound != Sdf.Path(f"/{PLACE}/Library/{EDITED}") or part.GetAttribute("score:surface").Get() != EDITED:
            problems.append(f"the part given {EDITED} is bound to {bound} after the base was made again")
        if regenerated != Gf.Vec3d(3.0, 0.0, -1.0):
            problems.append(f"the base was not made again: the second box is at {regenerated}")
        return problems


def parts_become_subsets_by_surface():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_place(folder)
        stage = Usd.Stage.Open(str(exported(folder, (2.0, 0.0, 0.0))))
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Objects/box_2/geo"))
        points = np.asarray(mesh.GetPointsAttr().Get())
        triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
        problems = []
        subsets = {subset.GetPrim().GetName(): np.asarray(subset.GetIndicesAttr().Get())
                   for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh)}
        if set(subsets) != {TOP, BOTTOM}:
            return [f"the box's parts are {sorted(subsets)}, not {[BOTTOM, TOP]}"]
        if sorted(np.concatenate(list(subsets.values())).tolist()) != list(range(len(triangles))):
            problems.append("the parts do not cover every face exactly once")
        heights = points[triangles].mean(axis=1)[:, 1]
        if not (heights[subsets[TOP]] > 0.5).all() or not (heights[subsets[BOTTOM]] < 0.5).all():
            problems.append("a face was given the surface of the other half")
        sound = stage.GetPrimAtPath(f"/{PLACE}/Objects/box_2/geo/{TOP}").GetAttribute("score:sound:impact").Get()
        if not sound:
            problems.append("the top part has no impact sound")
        return problems


def stored_takes_paint_like_their_labels():
    """A take stored in the repository (stored_parts.py: a sample of the labels, 16-bit points) gives the same parts
    as the labelled folder it was stored from."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_place(folder)
        stored = folder / "stored"
        export.stored_parts.write(folder / "parts/box-r1", "box-r1", stored)
        (stored / export.stored_parts.INDEX).write_text(json.dumps({PLACE: {"box": "box-r1"}}))
        place_files(folder, (2.0, 0.0, 0.0))
        path = export.export(PLACE, folder / "models", folder / "stage", parts=export.stored_parts.takes_of(PLACE, stored),
                             kit_path=folder / "kit.json", inventory_path=folder / "inventory.json")
        mesh = UsdGeom.Mesh(Usd.Stage.Open(str(path)).GetPrimAtPath(f"/{PLACE}/Objects/box_1/geo"))
        points = np.asarray(mesh.GetPointsAttr().Get())
        triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
        heights = points[triangles].mean(axis=1)[:, 1]
        subsets = {subset.GetPrim().GetName(): np.asarray(subset.GetIndicesAttr().Get())
                   for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh)}
        if set(subsets) != {TOP, BOTTOM}:
            return [f"the stored box's parts are {sorted(subsets)}, not {[BOTTOM, TOP]}"]
        if not (heights[subsets[TOP]] > 0.5).all() or not (heights[subsets[BOTTOM]] < 0.5).all():
            return ["a face of the stored box was given the surface of the other half"]
        return []


def the_stage_is_in_metres_with_static_colliders():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_place(folder)
        stage = Usd.Stage.Open(str(exported(folder, (2.0, 0.0, 0.0))))
        problems = []
        if UsdGeom.GetStageMetersPerUnit(stage) != 1.0 or UsdGeom.GetStageUpAxis(stage) != UsdGeom.Tokens.y:
            problems.append("the stage is not in metres with y up")
        for box in ("box_1", "box_2"):
            collider = stage.GetPrimAtPath(f"/{PLACE}/Objects/{box}/collision")
            if not collider.HasAPI(UsdPhysics.CollisionAPI) or UsdGeom.Imageable(collider).GetPurposeAttr().Get() != "guide":
                problems.append(f"{box} has no collider drawn as a guide")
            if stage.GetPrimAtPath(f"/{PLACE}/Objects/{box}").HasAPI(UsdPhysics.RigidBodyAPI):
                problems.append(f"{box} is a moving body; the place's objects are static")
        turned = UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Objects/box_2")).ComputeLocalToWorldTransform(0)
        if not Gf.IsClose(turned.TransformDir(Gf.Vec3d(1, 0, 0)), Gf.Vec3d(0, 0, 1), 1e-6):
            problems.append("a box facing 90 degrees is not turned as the game turns it (across onto +z)")
        return problems


def a_child_moves_with_the_object_it_stands_on():
    """A can standing on each box, where the box's composite places it (its foot 1 m up, 0.2 m across, turned 90
    degrees): a child prim of the box, so moving the box in the edit layer carries the can."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_place(folder)
        box_gltf(folder / "models", "can")
        composites = folder / "composites.json"
        composites.write_text(json.dumps({"test_box": {"children": [
            {"kind": "test_can", "at": [0.2, 1.0, 0.0], "size": [1.0, 1.0, 1.0], "turn": 90.0}]}}))
        export.COMPOSITES, kept = composites, export.COMPOSITES
        try:
            path = exported(folder, (2.0, 0.0, 0.0), children=("can",))
        finally:
            export.COMPOSITES = kept
        stage = Usd.Stage.Open(str(path))
        can = stage.GetPrimAtPath(f"/{PLACE}/Objects/box_1/can_1")
        if not can.IsValid() or not stage.GetPrimAtPath(f"/{PLACE}/Objects/box_2/can_1").IsValid():
            return ["a box has no can_1 under it"]
        problems = []
        placed = UsdGeom.Xformable(can).ComputeLocalToWorldTransform(0)
        if not Gf.IsClose(placed.ExtractTranslation(), Gf.Vec3d(0.2, 1.0, 0.0), 1e-6):
            problems.append(f"the can stands at {placed.ExtractTranslation()}, not where the composite puts it")
        if not Gf.IsClose(placed.TransformDir(Gf.Vec3d(1, 0, 0)), Gf.Vec3d(0, 0, -1), 1e-6):
            problems.append("the can is not turned 90 degrees as the game's prop scene turns it (across onto -z)")
        if can.GetAttribute("score:kind").Get() != "test_can":
            problems.append("the can does not carry its kind")
        edit = stage.GetLayerStack()[2]
        stage.SetEditTarget(Usd.EditTarget(edit))
        stage.GetPrimAtPath(f"/{PLACE}/Objects/box_1").GetAttribute("xformOp:translate").Set(Gf.Vec3d(5.0, 0.0, 1.0))
        carried = UsdGeom.Xformable(can).ComputeLocalToWorldTransform(0).ExtractTranslation()
        if not Gf.IsClose(carried, Gf.Vec3d(5.2, 1.0, 1.0), 1e-6):
            problems.append(f"the box moved to (5, 0, 1) but its can stands at {carried}")
        return problems


def the_parts_are_found_where_the_run_recorded_them():
    """A rerun names its takes `-s1`, a first run `-r1`: the take the run recorded is read, and with none recorded a
    take of either name is found."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        (folder / "models").mkdir()
        box_gltf(folder / "models")
        labelled_parts(folder / "parts", "s1")
        labelled_parts(folder / "parts", "r1", halves=((TOP, 0.0, 1.0),))
        (folder / "plan-route.json").write_text(json.dumps({"take": "s1"}))
        parts, take = export.run_parts(folder)
        problems = []

        def surfaces(path):
            stage = Usd.Stage.Open(str(path))
            mesh = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Objects/box_1/geo"))
            return {subset.GetPrim().GetName() for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh)}

        if parts != folder / "parts" or take != "s1":
            problems.append(f"the run's records give parts {parts} and take {take}")
        if surfaces(exported(folder, (2.0, 0.0, 0.0), take=take)) != {TOP, BOTTOM}:
            problems.append("the recorded take s1 was not the one read")
        for found in (folder / "parts/box-r1").iterdir():
            found.unlink()
        (folder / "parts/box-r1").rmdir()
        if surfaces(exported(folder, (2.0, 0.0, 0.0))) != {TOP, BOTTOM}:
            problems.append("with no take recorded, the take named -s1 was not found")
        return problems


def a_kit_room_s_pieces_stand_in_their_frames():
    """Two pieces of a kit room, one turned a quarter about up and stretched to its laid size: each object's box is its
    laid box; the lamp's lens (a `part`) is an object of its own; the parts come from the model the bake job names."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_place(folder)
        work = folder / "work"
        work.mkdir()
        (work / "job-chunky.json").write_text(json.dumps({"chunky": [{"name": "box", "parts": str(folder / "parts/box-r1")}]}))
        piece = {"kind": "bay_box", "model": "box", "size": [1.0, 1.0, 1.0], "layer": 1}
        pieces = [dict(piece, at=[0.0, 0.0, 0.0], x=[1, 0, 0], y=[0, 1, 0], z=[0, 0, 1]),
                  dict(piece, at=[3.0, 0.0, 0.0], x=[0, 0, -1], y=[0, 1, 0], z=[1, 0, 0], size=[1.02, 2.0, 1.0]),
                  dict(piece, at=[3.0, 2.0, 0.0], x=[1, 0, 0], y=[0, 1, 0], z=[0, 0, 1], size=[0.2, 0.1, 0.2],
                       part="glow")]
        (folder / "kit.json").write_text(json.dumps({"room": "bay", "place": PLACE, "pieces": pieces}))
        (folder / "inventory.json").write_text(json.dumps({"rows": [{"id": "box", "name": "a crate"}]}))
        parts, take = export.run_parts(work)
        path = export.export(PLACE, folder / "models", folder / "stage", parts=parts, kit_path=folder / "kit.json",
                             inventory_path=folder / "inventory.json", take=take)
        stage = Usd.Stage.Open(str(path))
        cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
        problems = []
        wanted = {"box_1": ((-0.5, 0.0, -0.5), (0.5, 1.0, 0.5)), "box_2": ((2.5, 0.0, -0.51), (3.5, 2.0, 0.51)),
                  "box_glow_1": ((2.9, 2.0, -0.1), (3.1, 2.1, 0.1))}
        for name, (low, high) in wanted.items():
            prim = stage.GetPrimAtPath(f"/{PLACE}/Objects/{name}")
            if not prim:
                problems.append(f"no object {name}")
                continue
            box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
            if not (np.allclose(box.GetMin(), low, atol=1e-4) and np.allclose(box.GetMax(), high, atol=1e-4)):
                problems.append(f"{name} spans {box.GetMin()} to {box.GetMax()}, laid {low} to {high}")
        mesh = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Objects/box_1/geo"))
        if not {subset.GetPrim().GetName() for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh)} >= {TOP, BOTTOM}:
            problems.append("the parts the bake job names were not read")
        return problems


CHECKS = (an_edit_survives_a_regenerated_base, parts_become_subsets_by_surface, stored_takes_paint_like_their_labels,
          the_stage_is_in_metres_with_static_colliders, a_child_moves_with_the_object_it_stands_on,
          the_parts_are_found_where_the_run_recorded_them, a_kit_room_s_pieces_stand_in_their_frames)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
