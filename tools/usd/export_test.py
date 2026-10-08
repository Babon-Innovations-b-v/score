"""Check the place's OpenUSD stage on a place made here of two boxes: a creator's edit in the edit layer (an object
moved, a part given another library surface) survives a regenerated base; parts become subsets by surface; the
stage is in metres with y up and every object has a static collider.

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


def box_gltf(folder):
    """A 1 m box standing on its foot, as a made model: one node, one primitive, normals, uvs and baked maps."""
    box = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
    box.apply_translation((0.0, 0.5, 0.0))
    box = box.unmerge_vertices() or box
    positions = np.asarray(box.vertices, dtype=np.float32)
    normals = np.asarray(box.vertex_normals, dtype=np.float32)
    uvs = (positions[:, [0, 2]] + 0.5).astype(np.float32)
    indices = np.asarray(box.faces, dtype=np.uint32).reshape(-1)
    blobs = [positions.tobytes(), normals.tobytes(), uvs.tobytes(), indices.tobytes()]
    offsets = np.cumsum([0] + [len(blob) for blob in blobs])
    (folder / "box.bin").write_bytes(b"".join(blobs))
    (folder / "textures").mkdir()
    for role in ("base_color", "metal_roughness", "normal"):
        Image.new("RGB", (8, 8), (200, 120, 60)).save(folder / f"textures/box_{role}.webp")
    accessor = [{"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3",
                 "min": positions.min(axis=0).tolist(), "max": positions.max(axis=0).tolist()},
                {"bufferView": 1, "componentType": 5126, "count": len(positions), "type": "VEC3"},
                {"bufferView": 2, "componentType": 5126, "count": len(positions), "type": "VEC2"},
                {"bufferView": 3, "componentType": 5125, "count": len(indices), "type": "SCALAR"}]
    document = {
        "asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": "box"}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2}, "indices": 3,
                                    "material": 0}]}],
        "materials": [{"name": "box_game", "normalTexture": {"index": 2}, "pbrMetallicRoughness": {
            "baseColorTexture": {"index": 0}, "metallicRoughnessTexture": {"index": 1}}}],
        "textures": [{"extensions": {"EXT_texture_webp": {"source": index}}} for index in range(3)],
        "images": [{"uri": f"textures/box_{role}.webp"} for role in ("base_color", "metal_roughness", "normal")],
        "accessors": accessor,
        "bufferViews": [{"buffer": 0, "byteOffset": int(offsets[index]), "byteLength": len(blob)}
                        for index, blob in enumerate(blobs)],
        "buffers": [{"uri": "box.bin", "byteLength": int(offsets[-1])}],
    }
    (folder / "box.gltf").write_text(json.dumps(document))


def labelled_parts(folder):
    """The box's labelled take: its top half one library surface, its bottom half another."""
    take = folder / "box-r1"
    take.mkdir(parents=True)
    for name, low, high in ((TOP, 0.5, 1.0), (BOTTOM, 0.0, 0.5)):
        part = trimesh.creation.box(bounds=((-0.5, low, -0.5), (0.5, high, 0.5))).subdivide().subdivide()
        part.export(take / f"{name}.ply")


def place_files(folder, second_at):
    """The place's layout (two boxes of one row, the second at `second_at`) and its inventory."""
    piece = {"prop": "test_box", "kind": "test_box", "model": "box", "row": "box", "size": [1.0, 1.0, 1.0]}
    kit = {"place": PLACE, "pieces": [dict(piece, at=[0.0, 0.0, 0.0], facing=0.0),
                                      dict(piece, at=list(second_at), facing=90.0)], "lamps": [], "children": []}
    inventory = {"rows": [{"id": "box", "name": "a crate", "anchor": "floor"}]}
    (folder / "kit.json").write_text(json.dumps(kit))
    (folder / "inventory.json").write_text(json.dumps(inventory))


def exported(folder, second_at):
    place_files(folder, second_at)
    return export.export(PLACE, folder / "models", folder / "stage", parts=folder / "parts",
                         kit_path=folder / "kit.json", inventory_path=folder / "inventory.json")


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


CHECKS = (an_edit_survives_a_regenerated_base, parts_become_subsets_by_surface,
          the_stage_is_in_metres_with_static_colliders)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
