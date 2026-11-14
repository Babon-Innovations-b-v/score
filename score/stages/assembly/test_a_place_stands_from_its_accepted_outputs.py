"""A place's assembly stands from its accepted outputs, never from the seed's own parts: each layer stage's output in
its place in the root's order, the accepted record over the seed's record prims, the bakes over the seed's models
(carrying their hash and the owner's pick), the sound stage's layer, the neighbours it shows read from their own
assemblies, each child scene at its hold on the plan, and each design object laid by what holds it at its built size
(base's garage door on its module's front, a door in its opening, a monitor on its console, a lamp on its wall); its
gates (layers, collision, resting, neighbours, child
scenes) fail or wait on what is missing. Every expected point and name is worked out by hand from the toy places
below. No spend, no machine: toy stages made here, a drop run in which nothing moved.

Each test below names the break that turns it red (`Break: <file>: `old` -> `new``), the last one also the yard
of its table the break turns red; each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
score/stages/assembly/test_a_place_stands_from_its_accepted_outputs.py
"""
import hashlib
import inspect
import json
import pathlib
import shutil
import struct
import sys

import numpy as np
import pytest
import trimesh
from PIL import Image

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))

from score import checks  # noqa: E402
from score.stages import assembly  # noqa: E402
from score.stages.assembly import (baked, fitting, made_waiting, neighbours, record,  # noqa: E402
                                     scene_tree, sounds)

TOY = "toy"
PLACE = "wreck"  # a place the environment knows (export lays its ground); its layout and inventory here are the test's


# --- the toy worlds -------------------------------------------------------------------------------------------------

def box_gltf(folder, name="box"):
    """A 1 m box standing on its foot, as a made model `name`: one node, one primitive, normals, uvs and maps."""
    box = trimesh.creation.box(extents=(1.0, 1.0, 1.0))
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
    accessors = [{"bufferView": 0, "componentType": 5126, "count": len(positions), "type": "VEC3",
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
        "accessors": accessors,
        "bufferViews": [{"buffer": 0, "byteOffset": int(offsets[index]), "byteLength": len(blob)}
                        for index, blob in enumerate(blobs)],
        "buffers": [{"uri": f"{name}.bin", "byteLength": int(offsets[-1])}]}
    (folder / f"{name}.gltf").write_text(json.dumps(document))


def row(identity, anchor="floor", **more):
    """An inventory row of this id, its name the id."""
    return {"id": identity, "name": identity, "anchor": anchor, "thing": f"prop:test_{identity}", **more}


def place_of(folder, pieces, rows):
    """A place of these pieces (row, model, at) and inventory rows, exported by tools/usd/export.py; its stage."""
    import export
    if not (folder / "models").exists():
        (folder / "models").mkdir()
        box_gltf(folder / "models")
    kit = {"place": PLACE, "lamps": [], "children": [],
           "pieces": [{"prop": f"test_{name}", "kind": f"test_{name}", "model": model, "row": name,
                       "size": [1.0, 1.0, 1.0], "at": list(at), "facing": 0.0} for name, model, at in pieces]}
    (folder / "kit.json").write_text(json.dumps(kit))
    (folder / "inventory.json").write_text(json.dumps({"scene": PLACE, "rows": rows}))
    return export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                         inventory_path=folder / "inventory.json")


def a_toy(root):
    """A seed stage of a place `toy` as round three left it: a root over edit, characters, sound, effects and base
    layers; the base with a fan of row `fan`, a door, and the old record's wall and lamp."""
    from pxr import Sdf, Usd, UsdGeom
    (root / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(root / "layers/base.usda"))
    UsdGeom.Xform.Define(base, f"/{TOY}/Objects/fan_1").GetPrim().CreateAttribute(
        "score:row", Sdf.ValueTypeNames.String).Set("fan")
    UsdGeom.Xform.Define(base, f"/{TOY}/Objects/door_1")
    UsdGeom.Cube.Define(base, f"/{TOY}/Structure/old_wall")
    UsdGeom.Xform.Define(base, f"/{TOY}/Lights/old_lamp")
    base.GetRootLayer().Save()
    for name in ("edit", "characters", "sound", "effects"):
        Sdf.Layer.CreateNew(str(root / f"layers/{name}.usda")).Save()
    stage = Usd.Stage.CreateNew(str(root / f"{TOY}.usda"))
    stage.GetRootLayer().subLayerPaths = [f"./layers/{name}.usda" for name in
                                          ("edit", "characters", "sound", "effects", "base")]
    stage.SetDefaultPrim(stage.GetPrimAtPath(f"/{TOY}"))
    stage.GetRootLayer().Save()
    return root / f"{TOY}.usda"


def a_record(folder, record_data):
    """An accepted scene-record output of the toy holding `record_data`, a kit with no pieces and an empty terrain:
    the inputs take_record writes the base over with."""
    (folder / "record/record").mkdir(parents=True)
    (folder / f"record/record/{TOY}.json").write_text(json.dumps({"place": TOY, **record_data}))
    (folder / "kit.json").write_text(json.dumps({"pieces": []}))
    (folder / "terrain").mkdir()
    return {"scene-record": folder / "record", "kit": folder / "kit.json", "terrain": folder / "terrain"}


ONE_LAMP = {"lights": [{"type": "omni", "at": [0, 2, 0], "energy": 1.0, "range": 4.0}]}


def read_only_toy(root):
    """The toy seed as a store checkout holds it: every file read-only, no assets/ folder."""
    stage = a_toy(root)
    for path in root.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    return stage


def an_asset(path, points, counts, indices):
    """A one-mesh asset, its default prim named after the file."""
    from pxr import Usd, UsdGeom
    path.parent.mkdir(parents=True, exist_ok=True)
    asset = Usd.Stage.CreateNew(str(path))
    mesh = UsdGeom.Mesh.Define(asset, f"/{path.stem}/geo")
    mesh.CreatePointsAttr(points)
    mesh.CreateFaceVertexCountsAttr(counts)
    mesh.CreateFaceVertexIndicesAttr(indices)
    asset.SetDefaultPrim(asset.GetPrimAtPath(f"/{path.stem}"))
    asset.Save()


def a_cube_asset(path, size):
    """An asset holding one cube `size` metres a side, its default prim named after the file."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.CreateNew(str(path))
    root = UsdGeom.Xform.Define(stage, f"/{path.stem}")
    UsdGeom.Cube.Define(stage, f"/{path.stem}/cube").GetSizeAttr().Set(size)
    stage.SetDefaultPrim(root.GetPrim())
    stage.GetRootLayer().Save()


def a_baked_triangle(made, name):
    """A one-triangle baked .gltf named `name` in `made`, its buffer beside it."""
    made.mkdir(parents=True, exist_ok=True)
    blob = (struct.pack("9f", 0, 0, 0, 1, 0, 0, 0, 1, 0) + struct.pack("9f", 0, 0, 1, 0, 0, 1, 0, 0, 1)
            + struct.pack("6f", 0, 0, 1, 0, 0, 1) + struct.pack("3H", 0, 1, 2))
    (made / f"{name}.bin").write_bytes(blob)
    views = [(0, 36), (36, 36), (72, 24), (96, 6)]
    kinds = [(5126, "VEC3"), (5126, "VEC3"), (5126, "VEC2"), (5123, "SCALAR")]
    document = {"buffers": [{"uri": f"{name}.bin", "byteLength": len(blob)}],
                "bufferViews": [{"buffer": 0, "byteOffset": start, "byteLength": length} for start, length in views],
                "accessors": [{"bufferView": index, "componentType": component, "count": 3, "type": kind}
                              for index, (component, kind) in enumerate(kinds)],
                "nodes": [{"mesh": 0}],
                "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1, "TEXCOORD_0": 2},
                                            "indices": 3}]}]}
    (made / f"{name}.gltf").write_text(json.dumps(document))


def opened(root):
    from pxr import Usd
    return Usd.Stage.Open(str(root))  # held by the caller: a prim of a stage nothing holds expires at once


# --- the resting gate reads the world's declared files --------------------------------------------------------------

def a_resting_place(root, case):
    """A place of the case's pieces (1 m boxes) and inventory rows as the stage's output, its inputs record naming the
    design inventory as the case has it (by default by full path as earth-seed lays it), the record laying the case's
    objects; the output and the world data the stage declares, its rules naming the case's kit groups, its inventory
    folder holding the place's rows."""
    (root / "made").mkdir(parents=True)
    stage = place_of(root / "made", case["pieces"], case["rows"])
    output = root / "output"
    shutil.copytree(stage.parent, output)
    named = case.get("inventory", str(root / f"home/design/inventory/{stage.stem}.json"))
    inputs_record = {name: value for name, value in json.loads((output / "inputs.json").read_text()).items()
                     if name != "inventory"}
    (output / "inputs.json").write_text(json.dumps({**inputs_record, **({"inventory": named} if named else {})}))
    if "record" in case:
        (output / record.RECORD).write_text(json.dumps({"objects": case["record"]}))
    data = root / "world/data"
    for part in ("checks", "kit", "inventory"):
        (data / part).mkdir(parents=True)
    rules = json.loads((REPO / "data/checks/resting.json").read_text())
    (data / "checks/resting.json").write_text(json.dumps({**rules, "fixed_in_kit": case["fixed in kit"]}))
    (data / "kit" / f"{stage.stem}.json").write_text(json.dumps({"kinds": {}}))
    (data / "inventory" / f"{stage.stem}.json").write_text(json.dumps({"rows": case["rows"]}))
    return output, {"resting rules": data / "checks/resting.json", "kit": data / "kit" / f"{stage.stem}.json",
                    "inventories": data / "inventory"}


# Fault (review of step 0, 2026-10-11): the judge read the repository's resting.json, so a world whose rules were
# elsewhere was judged on files its key did not cover. Fault (Buy of 2026-10-24): the assembly declared
# {data}/inventory while every designed seed is laid from {home}/design/inventory and records that full path, so no
# resting gate was judged. A floor plate sunk 40 cm (a kit piece's false alarm under the repository's rules) passes
# where the world's rules name its kit group and fails by name where they name none; a seed naming no inventory in the
# declared folder, or none at all, is unknown. Round 32's docking airlock (2026-11-11): its door's window and its suit
# in its locker, laid within their holders by the plan, failed as overlaps "still inside after the nudge": a window the
# record lays 30 cm within its door passes; the same pair with no planned relation, or laid on it, still fails.
SUNK = {"pieces": [("plate", "box", (6, -0.4, 0))], "rows": [row("plate", group="kit: floor")]}
PAIR = {"pieces": [("door", "box", (6, 0, 0)), ("window", "box", (6.3, 0, 0))], "rows": [row("door"), row("window")],
        "fixed in kit": []}
DOOR_1 = {"name": "door_1", "row": "door"}
RESTED = [
    {"name": "the sunk plate, its kit group named", **SUNK, "fixed in kit": ["kit: floor"], "answer": checks.PASS},
    {"name": "the sunk plate, no kit group named", **SUNK, "fixed in kit": [], "answer": checks.FAIL,
     "finding": "plate"},
    {"name": "the sunk plate naming an inventory elsewhere", **SUNK, "fixed in kit": ["kit: floor"],
     "inventory": "/elsewhere/rows.json", "answer": checks.UNKNOWN, "reason": "rows.json"},
    {"name": "the sunk plate naming no inventory", **SUNK, "fixed in kit": ["kit: floor"], "inventory": "",
     "answer": checks.UNKNOWN, "reason": "(none named)"},
    {"name": "a window in its door, no planned relation", **PAIR, "record": [DOOR_1], "answer": checks.FAIL,
     "finding": "overlaps"},
    {"name": "a window laid within its door", **PAIR, "answer": checks.PASS,
     "record": [DOOR_1, {"name": "window_1", "row": "window", "on": {"how": "within", "holder": ["door_1"]}}]},
    {"name": "a window laid on its door's top", **PAIR, "answer": checks.FAIL,
     "record": [DOOR_1, {"name": "window_1", "row": "window", "on": {"how": "top", "holder": ["door_1"]}}]},
]


# --- a hanging one against its holder's back ------------------------------------------------------------------------

# Round 32's docking airlock: spacesuit_left_1, laid within its locker at the plan's base, hung 4.1 cm off the
# locker's back and touched nothing (hangs free). A hanging one moves along its holder's back way until its built
# surface meets the holder's inside back face (hung_back): the back is opposite the side the holder's surface leaves
# open across it (an open-fronted locker, +x), else opposite the side toward the room's middle (a closed one). A suit
# 0.2 to 0.6 m deep in a locker 1 m deep, 2 m high and 0.8 m across: (axis, sign, how far it moves) by its walls and
# the room's middle.
STEPS, ACROSS = np.linspace(0.0, 2.0, 41), np.linspace(0.0, 0.8, 17)
LOCKER_BACK = [[0.0, up, side] for up in STEPS for side in ACROSS]
LOCKER_SIDES = [[deep, up, side] for deep in np.linspace(0.0, 1.0, 21) for up in STEPS for side in (0.0, 0.8)]
LOCKER_FRONT = [[1.0, up, side] for up in STEPS for side in ACROSS]
HUNG = [
    ("open-fronted, the room's middle behind its back", LOCKER_BACK + LOCKER_SIDES, [-5.0, 0.4], (0, -1.0, 0.2)),
    ("closed, the room's middle before it", LOCKER_BACK + LOCKER_SIDES + LOCKER_FRONT, [5.0, 0.4], (0, -1.0, 0.2)),
    ("closed, the room's middle behind its back", LOCKER_BACK + LOCKER_SIDES + LOCKER_FRONT, [-5.0, 0.4],
     (0, 1.0, 0.4)),
]
SUIT = np.array([[deep, up, side] for deep in (0.2, 0.6) for up in np.linspace(0.1, 1.9, 37)
                 for side in np.linspace(0.2, 0.6, 9)])


# --- the bakes laid over the seed's and the released models ---------------------------------------------------------

def a_baked_place(root):
    """A place of a crate laid from model `box`, the owner's pick of it the box's hash (sha256 of its .gltf and its
    buffer's hex digest, worked out here), and two fixtures laid from released files, each a 2 m cube: the rocket,
    whose bake is a 2 m cube, and the tower, whose bake is a 3 m cube (the bake moved its frame); the bake of the box
    is `plank` (another file, another hash). The stage, its inventory and the hashes {model: sha}."""
    from pxr import Sdf, Usd, UsdGeom
    (root / "models").mkdir(parents=True)
    box_gltf(root / "models")
    box_gltf(root / "models", "plank")

    def sha(gltf):
        digest = hashlib.sha256(gltf.read_bytes())
        digest.update(hashlib.sha256(gltf.with_suffix(".bin").read_bytes()).hexdigest().encode())
        return digest.hexdigest()
    hashes = {name: sha(root / f"models/{name}.gltf") for name in ("box", "plank")}
    pick = {"model": "box", "sha256": hashes["box"], "decided": "owner, 2026-10-09: this take"}
    stage = place_of(root, [("crate", "box", (0, 0, 0))], [row("crate", pick=pick)])
    for name, baked_size in (("rocket", 2.0), ("tower", 3.0)):
        a_cube_asset(stage.parent / f"assets/fixture_{name}.usdc", 2.0)
        a_cube_asset(stage.parent / f"assets/{name}.usdc", baked_size)
    base = Usd.Stage.Open(str(stage.parent / assembly.BASE_LAYER))
    for name in ("rocket", "tower"):
        prim = UsdGeom.Xform.Define(base, f"/{PLACE}/Fixtures/{name}").GetPrim()
        prim.GetReferences().AddReference(f"../assets/fixture_{name}.usdc")
        prim.CreateAttribute("score:model", Sdf.ValueTypeNames.String).Set(f"models/{name}s/{name}.gltf")
    base.GetRootLayer().Save()
    return stage, json.loads((root / "inventory.json").read_text()), hashes


# --- layers, record and sound ---------------------------------------------------------------------------------------

BOX_FACES = [0, 1, 3, 2, 4, 6, 7, 5, 0, 4, 5, 1, 2, 3, 7, 6, 0, 2, 6, 4, 1, 5, 7, 3]  # a box's six sides, of its corners


def boxes_mesh(boxes):
    """(points, face counts, indices) of a mesh of whole boxes (low, high), each its six sides."""
    points, indices = [], []
    for low, high in boxes:
        indices += [len(points) + corner for corner in BOX_FACES]
        points += [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    return points, [4] * (len(indices) // 4), indices


def a_box_asset(path, low, high):
    """A one-mesh asset, a box from `low` to `high`, its six sides."""
    an_asset(path, *boxes_mesh([(low, high)]))


# The laid toy (made_waiting.lay over one accepted record whose rows the bake made). The camp grounds' cairn
# (2026-10-13): the baked cairn spans 2 x 2 x 0.5 m; turned 90 degrees about y it spans 0.5 x 2 x 2, its foot at the
# spot's 0.5, its middle over (3, -2). settle@hangar (2026-11-13): its 28 m ship, laid across the hall over its landing
# pad laid along the hall, stood half on the pad and half on the deck, tipping; on a 2 x 6 m pad 0.1 m high, a 6 x 1 m
# ship laid across it is turned a quarter onto it about its middle; one hung from the roof (the crane) and one too long
# to fit turned (the barge) are left as laid, and one wholly on it (the cart) stays. Base's garage door (motion@base,
# 2026-10-29: it stood 0.17 m off its module's front and 4.7 m of its 6 m past the module's corner, laid at its plan
# item's middle): laid by its relation (on the module's S face, `out` +z) at their built sizes, the 12 m module from
# 26.254 to 38.254 across and to 39.4 in front, the 6 x 8 x 0.5 m door stands with its back on z 39.4, its foot on the
# floor, shifted in from the module's corner so its recess's 0.55 m of room on its hinge side (-x) fits the face too:
# its middle from 24.5585 to 26.254 + 0.55 + 3 = 29.804 (score, 2026-10-29: never swinging round the corner). The
# built garage door (#36, motion@base), 100 m along x: the module's box reaches z 39.43 only by a 0.39 m lip above the
# doorway, so a door laid on the box's side hung in the air, and the bake cut the recess from the row's 6 m (6.6 with
# its room) while the built 8.30 m door covered solid wall past it. Its module's face stands at z 39.0 below 8 m and
# its lip at 39.4 above, the bake's recess runs x 126.304 to 132.904 (its own -5.95 to 0.65) at the module's corner,
# 8 m tall, and the 8 x 8 x 0.5 m door with 0.6 m of room on its hinge side (-x) is shrunk to 6 / 8 = 0.75 to fit the
# recess less its room; it hangs in the recess as a door in its opening does (round 32: hung 0.6 m off the jamb, the
# shrunk door touched nothing once it swung): its hinge edge at the recess's -x jamb (x 126.304 to 132.304), its middle
# on the face, z 39.0 (38.8125 to 39.1875), from the recess's foot.
BUILT = 100.0  # the built garage's module stands this far along x from the plain one
LAID_AT = {  # each laid entry: (its scope, its world box's low and high, the tolerance it stands within)
    "cairn": ("Fixtures", (2.75, 0.5, -3.0), (3.25, 2.5, -1.0), 1e-5),
    "ship": ("Fixtures", (-0.5, 0.1, -3.0), (0.5, 1.1, 3.0), 5e-4),
    "crane": ("Fixtures", (-3.0, 0.1, -0.5), (3.0, 1.1, 0.5), 5e-4),
    "barge": ("Fixtures", (-3.5, 0.1, -0.5), (3.5, 1.1, 0.5), 5e-4),
    "cart": ("Fixtures", (-0.25, 0.1, -0.5), (0.25, 1.1, 0.5), 5e-4),
    "garage_door_1": ("Objects", (26.804, 0.0, 39.4), (32.804, 8.0, 39.9), 1e-4),
    "garage_door_2": ("Objects", (BUILT + 26.304, 0.0, 38.8125), (BUILT + 32.304, 6.0, 39.1875), 1e-4)}


def a_laid_toy(root):
    """The laid toy: a toy whose accepted record holds the cairn, the pad's four things and the two garages, each
    waiting on a model the bake made (the built module's bake naming its recess cut); the toy's root after
    made_waiting.lay, and the models it said it laid."""
    out = a_toy(root / "out")
    pad = {"name": "pad_1", "builder": "slab", "row": "pad", "low": 0.0, "high": 0.1, "surface": "floor_plate",
           "points": [[-1.0, -3.0], [1.0, -3.0], [1.0, 3.0], [-1.0, 3.0]]}
    things = {"ship": ({}, 3.0), "crane": ({"under roof": True}, 3.0), "barge": ({}, 3.5), "cart": ({}, 0.25)}
    entries = [{"name": "cairn", "model": "models/none/none.glb", "row": "cairn", "at": [3.0, 0.5, -2.0],
                "rotation": [0.0, 0.7071068, 0.0, 0.7071068], "waiting": "no released model"},
               *({"name": name, "row": name, "at": [0.0, 0.1, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0],
                  "waiting": "no model", **said} for name, (said, _) in things.items())]
    for number, (along, room) in enumerate(((0.0, 0.55), (BUILT, 0.6)), start=1):
        entries += [{"name": f"square_module_front_right_{number}", "row": "square_module_front_right",
                     "bake": f"module_{number}", "at": [along + 32.254, 0.0, 33.4], "rotation": [0.0, 0.0, 0.0, 1.0],
                     "kind": "object", "waiting": "bake"},
                    {"name": f"garage_door_{number}", "row": "garage_door", "bake": f"door_{number}",
                     "at": [along + 24.5585, 0.0, 39.8395], "rotation": [0.0, 0.0, 0.0, 1.0], "kind": "object",
                     "waiting": "bake", "on": {"how": "face", "holder": [f"square_module_front_right_{number}"],
                                               "out": [0.0, 1.0], "room": room, "room_way": [-1.0, 0.0],
                                               "why": "against its module's side the concept shows it on"}}]
    assembly.take_record(a_record(root, {"structure": [pad], "objects": entries}), out.parent, TOY)
    assets = out.parent / "assets"
    an_asset(assets / "cairn.usdc",
             [(-1.0, -1.0, -0.25), (1.0, -1.0, -0.25), (1.0, 1.0, 0.25), (-1.0, 1.0, 0.25)], [4], [0, 1, 2, 3])
    for name, (_, half) in things.items():
        an_asset(assets / f"{name}.usdc", [(-half, 0.0, -0.5), (half, 0.0, -0.5), (half, 1.0, 0.5)], [3], [0, 1, 2])
    a_box_asset(assets / "module_1.usdc", (-6.0, 0.0, -6.0), (6.0, 12.0, 6.0))
    a_box_asset(assets / "door_1.usdc", (-3.0, 0.0, -0.25), (3.0, 8.0, 0.25))
    an_asset(assets / "module_2.usdc", *boxes_mesh([
        ((-6.0, 0.0, -6.0), (-5.95, 8.0, 5.6)), ((0.65, 0.0, -6.0), (6.0, 8.0, 5.6)),  # the body beside the recess
        ((-5.95, 0.0, -6.0), (0.65, 8.0, -0.05)), ((-6.0, 8.0, -6.0), (6.0, 12.0, 6.0))]))  # its back, the lip
    a_box_asset(assets / "door_2.usdc", (-4.0, 0.0, -0.25), (4.0, 8.0, 0.25))
    (root / "bake").mkdir()
    (root / "bake/baked.json").write_text(json.dumps(
        {"cairn": {}, **{name: {} for name in things}, "module_1": {}, "door_1": {},
         "module_2": {"cuts": [{"recess": [[-5.95, 0.0, -0.05], [0.65, 8.0, 6.05]]}]}, "door_2": {"cuts": []}}))
    return out, made_waiting.lay(out.parent, TOY, root / "bake")


HELD_FACE = {"how": "face", "holder": ["module_1"], "out": [0.0, 1.0]}
HELD_NARROW = {"how": "face", "holder": ["shed_1"], "out": [0.0, 1.0], "room": 0.55, "room_way": [1.0, 0.0]}
FRONT, BACK = ({"how": "face", "holder": ["facade_1"], "out": [0.0, way]} for way in (1.0, -1.0))


def at_facade(along, z):
    """A 1 m door's laid box on the facade, its middle `along` x, its back at `z`."""
    return {"low": [along - 0.5, 0.0, z], "high": [along + 0.5, 2.1, z + 0.1]}


ITEM = {"low": [0.0, 0.0, 0.0], "high": [1.0, 2.0, 0.0]}
# #72: a door laid on its module's face (door_1), one 1 m beside it (door_2), a 6 m door on a 6 m face with 0.55 m of
# recess room (door_3), a window in no opening, a lamp held by nothing, a crate left at the room's middle; #36,
# street's three restaurant doors: entries 1 to 3 on the facade's +z face 0.58 m apart, a sign above them (no height
# shared) and entry_4 on its -z face at entry_1's spot.
HELD_RECORD = {"objects": [
    {"name": "door_1", "on": HELD_FACE}, {"name": "door_2", "on": HELD_FACE}, {"name": "door_3", "on": HELD_NARROW},
    {"name": "window_1", "fills": True}, {"name": "lamp_1", "unheld": "its holder lays nothing"},
    {"name": "crate_1", "unplaced": "left on the walls item"},
    *({"name": name, "on": BACK if name == "entry_4" else FRONT}
      for name in ("entry_1", "entry_2", "entry_3", "sign_1", "entry_4"))]}
HELD_LAID = {"holders": [{"name": "facade_1", "low": [40.0, 0.0, -1.0], "high": [50.0, 9.0, 0.0]}],
             "objects": [{"name": "module_1", "low": [-6.0, 0.0, -6.0], "high": [6.0, 12.0, 6.0]},
                         {"name": "door_1", "low": [-3.0, 0.0, 6.0], "high": [3.0, 8.0, 6.5]},
                         {"name": "door_2", "low": [-3.0, 0.0, 7.0], "high": [3.0, 8.0, 7.5]},
                         {"name": "shed_1", "low": [20.0, 0.0, 0.0], "high": [26.0, 9.0, 4.0]},
                         {"name": "door_3", "low": [20.0, 0.0, 4.0], "high": [26.0, 8.0, 4.5]},
                         *({"name": name, **ITEM} for name in ("window_1", "lamp_1", "crate_1")),
                         {"name": "entry_1", **at_facade(42.609, 0.0)}, {"name": "entry_2", **at_facade(43.189, 0.0)},
                         {"name": "entry_3", **at_facade(43.769, 0.0)}, {"name": "entry_4", **at_facade(42.609, -1.1)},
                         {"name": "sign_1", "low": [42.0, 2.5, 0.0], "high": [44.0, 3.0, 0.1]}]}
HELD_FINDINGS = [  # what the held gate names, in its order: the relations' faults (fitting.held_faults), then each
    # pair overlapping on one face (held_apart.overlapping); door_1, on its face, and entry_3, sign_1 and entry_4 pass
    ("door_2", "1.00 m off where it is laid face ()", 1.0),
    ("door_3", "its holder's face is 0.55 m too narrow for it and its recess", 0.55),
    ("door_3", "0.55 m off where it is laid face ()", 0.55),
    ("window_1", "a door or window in no opening and on no holder", None),
    ("lamp_1", "held by nothing: its holder lays nothing", None),
    ("crate_1", "at the room middle: left on the walls item", None),
    ("entry_1", "laid 0.10 m inside entry_2 at its built size", 0.1),  # 0.42 x 2.1 x 0.1 m into each other
    ("entry_2", "laid 0.10 m inside entry_3 at its built size", 0.1),
    ("door_1", "overlaps door_2 by 6.00 m along their holder's face", 6.0),  # two 6 m doors on module_1's +z face
    ("entry_1", "overlaps entry_2 by 0.42 m along their holder's face", 0.42),
    ("entry_2", "overlaps entry_3 by 0.42 m along their holder's face", 0.42)]
# #36: a 2.4 m wide, 2.66 m tall opening at z 0.15 in a built wall whose sill and lintel run z -0.276 to 0 (wall_1
# its jamb beside the opening); a 2.4 x 2.4 x 0.2 m door stands on the wall's room face, z 0 (door_1), one is left on
# the plan's line 0.15 m off (door_2), a 2 m one against its -x jamb (door_3).
DOOR_WALLS = [{"name": "wall_1", "low": [-5.0, -0.2, -0.276], "high": [-1.2, 4.6, 0.0]},
              {"name": "wall_1_2", "low": [-1.2, -0.2, -0.276], "high": [1.2, 0.0, 0.0]},
              {"name": "wall_1_3", "low": [-1.2, 2.66, -0.276], "high": [1.2, 4.6, 0.0]}]
DOORWAY_1 = {"how": "in", "middle": [0.0, 0.0, 0.15], "along": [1.0, 0.0], "wide": 2.4, "tall": 2.66,
             "why": "opening 1"}
DOORS_IN = {name: {"name": name, "low": [-1.2, 0.0, z], "high": [high, 2.4, z + 0.2]}
            for name, z, high in (("door_1", -0.1, 1.2), ("door_2", 0.05, 1.2), ("door_3", -0.1, 0.8))}
SHORT = "too small for its opening: 0.26 m short of its 2.66 m height"


def in_doorway(*names):
    """The record and the laid file of the named doors of DOORS_IN, each filling DOORWAY_1, among DOOR_WALLS."""
    return ({"objects": [{"name": name, "on": DOORWAY_1, "fills": True} for name in names]},
            {"walls": DOOR_WALLS, "objects": [DOORS_IN[name] for name in names]})


AGAINST = {"how": "wall", "span": [[0.0, 6.4685], [7.0, 6.4685]], "out": [0.0, 1.0], "why": "against the wall"}
TUNNEL_RECORD = {"objects": [{"name": "glass_tunnel_1", "row": "glass_tunnel", "on": AGAINST},
                             {"name": "pipe_1", "row": "pipe", "on": AGAINST}]}
TUNNEL_LAID = {"walls": [{"name": "wall_3", "low": [0.0, -0.242, 6.4805], "high": [7.0, 4.6, 6.7565]},
                         {"name": "deck_1", "low": [0.0, -0.242, 0.0], "high": [7.0, -0.042, 6.4]}],
               "objects": [{"name": "glass_tunnel_1", "low": [1.0, 0.0, 6.4685], "high": [5.0, 2.5, 9.0]},
                           {"name": "pipe_1", "low": [5.5, 0.0, 6.4685], "high": [6.0, 2.5, 6.9685]}]}
HELD_JUDGED = [  # (case, its record and laid file, the held gate's answer and measures, the faults it names
    # (fitting.held_faults, then held_apart.overlapping), the doors it names short of their openings)
    ("#72 and #36's held world", (HELD_RECORD, HELD_LAID), checks.FAIL,
     {"not held": 8, "worst off": 1.0, "overlapping": 3}, HELD_FINDINGS, []),
    ("a door on the built wall's face and one on the plan's line", in_doorway("door_1", "door_2"), checks.FAIL,
     {"not held": 1, "worst off": 0.15, "overlapping": 0},
     [("door_2", "0.15 m off where it is laid in (opening 1)", 0.15)],
     [("door_1", SHORT, 0.26), ("door_2", SHORT, 0.26)]),
    ("the door on the built wall's face alone", in_doorway("door_1"), checks.PASS,
     {"not held": 0, "worst off": 0.0, "overlapping": 0}, [], [("door_1", SHORT, 0.26)]),
    ("a narrow door against its jamb", in_doorway("door_3"), checks.PASS,
     {"not held": 0, "worst off": 0.0, "overlapping": 0}, [], [("door_3", SHORT, 0.26)]),
    ("a tunnel and a pipe against their wall, both reaching into it", (TUNNEL_RECORD, TUNNEL_LAID), checks.FAIL,
     {"not held": 1, "worst off": 0.276, "overlapping": 0},
     [("pipe_1", "laid 0.28 m inside wall_3, nothing holding it there", 0.276)], []),
]
DESK = (np.array([0.0, 0.0, 0.0]), np.array([1.2, 0.75, 0.6]))
UNIT = (np.array([0.0, 0.0, 0.0]), np.array([1.0, 2.0, 0.5]))
TOP = {"how": "top", "holder": ["desk_1"], "holder row": "desk"}
UNDER = {"how": "within", "under": True, "holder": ["desk_1"], "holder row": "desk"}
PLACED = [  # (case, the cables' relation, the placement faults its reading's "under desk" names; quarters, 2026-11-04)
    ("cables laid on the desk's top", TOP, [("cables_1", "laid top desk, though its reading says 'under desk' (under)",
                                            None)]),
    ("cables held under the desk", UNDER, [])]
OFF = [  # (case, a laid box's low and high, its relation, its holder's box, how far it stands off it within what,
    # whether on_holder stands it at the holder's foot)
    ("cables under the desk, laid 0.5 m up in it", [0.2, 0.5, 0.1], [0.6, 0.6, 0.3], UNDER, DESK, 0.5, 0.0, True),
    ("a box within its shelf unit laid on its top", [0.3, 2.0, 0.1], [0.7, 2.404, 0.5], {}, UNIT, 0.0, 0.0, False),
    ("a box through its shelf unit's top, its foot 0.2 m in", [0.3, 1.8, 0.1], [0.7, 2.204, 0.5], {}, UNIT, 0.2, 1e-9,
     False)]


def a_built_box(stage, path, low, high):
    """An Xform at `path` (one transform op) holding a box mesh from `low` to `high`."""
    from pxr import Gf, UsdGeom
    UsdGeom.Xform.Define(stage, path).AddTransformOp().Set(Gf.Matrix4d(1.0))
    mesh = UsdGeom.Mesh.Define(stage, f"{path}/geo")
    mesh.CreatePointsAttr([(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    mesh.CreateExtentAttr([low, high])


def a_solid_box(stage, path, low, high, degrees=0.0):
    """An Xform at `path` (one transform op) holding a box mesh from `low` to `high` with its faces, turned `degrees`
    about the up axis through its middle."""
    from pxr import Gf, UsdGeom
    box = trimesh.creation.box(bounds=[low, high])
    middle = (np.asarray(low, float) + np.asarray(high, float)) / 2
    box.apply_transform(trimesh.transformations.rotation_matrix(np.radians(degrees), [0.0, 1.0, 0.0], middle))
    UsdGeom.Xform.Define(stage, path).AddTransformOp().Set(Gf.Matrix4d(1.0))
    mesh = UsdGeom.Mesh.Define(stage, f"{path}/geo")
    mesh.CreatePointsAttr([tuple(map(float, point)) for point in box.vertices])
    mesh.CreateFaceVertexCountsAttr([3] * len(box.faces))
    mesh.CreateFaceVertexIndicesAttr([int(index) for index in box.faces.reshape(-1)])
    mesh.CreateExtentAttr([tuple(map(float, box.bounds[0])), tuple(map(float, box.bounds[1]))])


def test_a_ramp_rests_up_on_its_deck_and_nothing_starts_inside_a_deck_or_wall():
    """settle@airlock (2026-10-30): its ramp lay beside its porch deck, its end 0.14 m in the deck's slab, two sandbags
    in the slab and its porch post 0.14 m in wall_3, laid at the plan's estimates; the drop sank and tilted them. The
    assembly lays a ramp up its way onto its deck (the built static past its level's edge whose top is nearest the
    level's): its 2 m plank pitched asin(0.158 / 2) = 4.53 degrees from the ground to the deck's 0.158 m top, its high
    end's foot on the deck's near side at x 3.19. A thing nothing holds that starts inside a deck or wall is moved the
    least way out: a sandbag 0.158 m into the deck's top up onto it, the post 0.141 m into the wall back to its face
    at z 6.699, a locker reaching up into a loft deck out past its side (never down under the floor), a 4.2 m cable
    bundle across a 0.14 m wall 0.34 m past the wall's near side (tube's, 2026-10-30); a ship longer than the place
    across a wall fits nowhere clear of it and is left as laid, and named; a lamp in the
    roof's box, a crate in a slanted wall's 5 m box and a stair reaching into its loft deck are left (a roof's and a
    slanted wall's box hold the room, a stair climbs into its level). The held gate
    fails one left inside a deck by name and its depth, never a door the record lays in its opening.
    settle@flat (#72, 2026-11-03): floor things nothing holds, laid at their built size, bigger than the plan's
    estimates, stood in each other. They are parted on the floor at their built size by the relation solver, never
    shrunk: a 2.4 m bed and the wardrobe 0.2 m into it, a crate in a kit fixture (which never moves), all kept inside
    the walls; a table on a 2 cm rug is no overlap and neither moves. habitat (#72, 2026-11-04): bunk beds laid
    across its inner wall are moved to the nearest free spot in their own room (a bed across a two-room split goes
    1.75 m round a locker on its own side, never 1.2 m through the wall into the next room); one that fits nowhere
    in its room at its built size (3.5 m in a 3 m room) is left as laid, and two floor things left inside each other
    are named by the held gate (a bed in a crate, never a table on its rug).
    Break: score/stages/assembly/fitting.py: `if not (through(middle, middle + move, walls_near) & ~started).any():`
        -> `if True:`
    Break: score/stages/assembly/fitting.py: `return faults + crowded_faults(record, boxes, shapes)` -> `return faults`
    Break: score/stages/assembly/fitting.py: held_faults' `and not fills_holder(entry):` -> `:` (the door's window in
        the wall), or inside_of's `reach_into(corners, shapes.get(name, box_corners(box)))` -> `float(depths(low,
        high, box).min())` (the turned pipe past the wall's end named inside it), or its `shapes.get(name,
        box_corners(box))` -> `box_corners(box)` (lab's crate by its slanted wall named in it)
    Break: score/stages/assembly/fitting.py: held_faults' `distance = min(distance, stacked_off(...` -> `distance =
        min(distance, np.inf` (garage's stacked box named off its shelf), or off_holder's `above = 0.0 if
        on_shelves_of(on) else` dropped (storage's bag on its top board named over its unit)
    Break: score/stages/assembly/fitting.py: crowded_faults' `if entry["name"] in boxes` -> `if entry["name"] in
        boxes and not entry.get("on")` (two jars held at one spot on their shelf pass, galley 2026-11-03)
    Break: score/stages/assembly/fitting.py: holders_of's `more = {holder for one in more ...} - seen` -> `more =
        set()` (a book within a shelf on a desk named inside the desk)
    Break: score/stages/assembly/fitting.py: `return inside if (np.asarray(inside[:2]) <= middle).all()` -> `return
        inside if True`
    Break: score/stages/assembly/fitting.py: `done, fits = set(), parted(stage, place, loose, set(by_name))` -> `done,
        fits = set(), []`
    Break: score/stages/assembly/fitting.py: `if crossing({**held, **after}, thin) >= crossing({**held, **boxes},
        thin):` -> `if True:`
    Break: score/stages/assembly/fitting.py: `return pivot, np.cross(way, [0.0, 1.0, 0.0]),` -> `return pivot,
        np.cross([0.0, 1.0, 0.0], way),`
    Break: score/stages/assembly/fitting.py: `fits += moved_out(stage, place, loose)` -> `fits += []`
    Break: score/stages/assembly/fitting.py: `fits += floor_clear.off_edges(stage, place, loose) +
        floor_clear.apart(stage, place, loose)` -> `fits += []` (habitat's plant left across its rug's edge, its lamp
        in its sofa), or floor_clear.py's leans' `> LEAN_MOST` -> `> 0.0` (the table moved off its rug), or apart's
        `if not TOUCH < reach <= fitting.HELD_MOST:` -> `if not reach > 0.0:` (the touching crate moved)
    Break: score/stages/assembly/fitting.py: `and not entry.get("on") and not climbs(entry)]` (fitted's loose) ->
        `and not entry.get("on")]`
    Break: score/stages/assembly/fitting.py: `return [(name, box) for name, box in built if name.split("_")[0] in
        STATICS]` -> `return built`
    Break: score/stages/assembly/fitting.py: `if not held_in(on) and not climbs(entry):` -> `if True:`
    Break: score/stages/assembly/fitting.py: climbs' `return "_".join(words) in CLIMBING or words[0] in CLIMBING` ->
        `return bool(set(words) & set(CLIMBING))` (the step ladder climbs)
    Break: score/stages/assembly/fitting.py: statics' `or floor_piece(name, box)]` -> `]` (the ladder left inside its
        landing pad), or floor_piece's `float(box[0][1]) <= HELD_MOST and` dropped (the ceiling beam a static)
    Break: score/stages/assembly/fitting.py: `back[1] = np.inf` -> `pass`
    Break: score/stages/assembly/fitting.py: `<= WALL_THICKEST)]` -> `<= 99.0)]`
    Break: score/stages/assembly/fitting.py: `if depths(low, high, box).min() > HELD_MOST]` -> `if False]`
    Break: score/stages/assembly/fitting.py: free_spot's `clear &= slant_depth(middle[[0, 2]] + chunk[:, [0, 2]],
        size[[0, 2]] / 2, outline) <= HELD_MOST` -> `pass` (its free spot found in the slanted corner, the parting is refused: left in the fixture)
    Break: score/stages/assembly/fitting.py: shallow_out's `if abs(moves[axis]) > HELD_MOST:` -> `if False:` (a car
        laid across a wall pulled 4 m through it), or straight's `>= STRAIGHT_LEAST *` -> `>= 0.0 *` (moved out of a
        slanted wall's box)
    Break: score/stages/assembly/fitting.py: slants' `if not flight(name) and (name.split("_")[0] != "wall"` -> `if
        (name.split("_")[0] != "wall"` (the crate left on the flight), or free_spot's `outline)[0] >= 0.0` -> `outline)[0]
        > 0.0` (a point's depth is never over 0: a crate whose middle stands on the flight found no way off it)
    Break: score/stages/assembly/fitting.py: free_spot's `clear &= on_deck(box[0] + chunk, size, deck)` -> `pass` and
        parted_boxes' `if (deck := deck_at(boxes[name], floors)) is not None` -> `if False and ...` (greenhouse's desk
        parted past its deck's edge), or parted's `outlines = {name: outline ...}` -> `outlines = {}` (the desk clear
        of the railing, in its box, parted)
    Break: score/stages/assembly/fitting.py: `fits += held_along.carried(stage, place, list(by_name.values()), before)`
        -> `fits += []` (greenhouse's computer left at its parted desk's edge), or held_along.py's carried `if
        float(np.linalg.norm(shift)) <= fitting.MOVE_LEAST:` -> `if True:`
    assembly@walkway (2026-11-12): its ceiling ducts, built 0.069 m longer than the room between walls 1 and 3, were
    moved out of wall_1 into wall_3; its 4.7 cm floor lights lay wholly in wall_4, 0.0503 m from its face. A 10.06 m
    duct between walls 10 m apart is narrowed along z to the room, both ends on their walls; a 4.66 cm light in
    wall_4 is moved 0.0503 m out of it into the room; a 12 m beam (83%) is left at its length.
    Break: score/stages/assembly/fitting.py: `fits += room_clear.cleared(stage, place, loose)` dropped (the duct left
        0.06 m in wall_3, the light in wall_4), or room_clear.py's `if room >= length or room < SHRINK_MOST * length:`
        -> `if room >= length:` (the beam shrunk to 83%), or moved_across's `> float(box[1][axis] - box[0][axis]):`
        -> `> fitting.HELD_MOST:` (the light left in its wall), or `-> > 100.0:` (the spaceship across wall_5 moved
        3 m)
    light@walkway (2026-11-12): the floor lights were moved out of wall_4 and their lamps, laid at their plan spots
    inside them, left 2.7 cm in the wall, its spot-2 at 0.079 against its concept's 0.237. The light's lamp is carried
    0.0503 m into the room with it, its record spot kept (lamps_along.laid_at); a lamp in the duct's box, which is
    narrowed, and one beside the light stay.
    Break: score/stages/assembly/room_clear.py: `lamps_along.moved_with(stage, place, low, high, foot, 1.0, foot +
        move)` dropped (the lamp left in wall_4), or lamps_along.py's `if np.any(spot < np.asarray(low) - WITHIN) or
        ...: continue` -> `if False: continue` (the lamp beside the light carried too)
    settle@habitat (2026-11-13): its rugs 4 and 7 to 10 lay across its partition walls and under a wall thing, and its
    bookshelf 2 and bunk bed 2 stood 2 and 4.4 cm into slanted walls, which the parting lets stand (its HELD_MOST); the
    drop took them as laid inside (its triangles still crossing past a 5 mm nudge) or slid the bed 92 cm. A 2 m rug
    laid across a partition into a 1.52 m alcove is shrunk to 74% and moved 0.24 m into it, GAP from both walls; a
    crate 2 cm into a slanted wall is moved (0.03, 0.02) m off it; a rug 4 mm into wall_4 is no overlap to the drop and
    is left.
    Break: score/stages/assembly/fitting.py: `fits += floor_free.cleared(stage, place, loose, entries)` dropped (the
        rug and the crate left in their walls), or floor_free.py's reaches' `< half - NUDGE` -> `< half` (the rug 4 mm
        in moved), or spot_for's `for scale in scales:` -> `for scale in scales[:1]:` (the alcove's rug left), or
        free_moves' `reach = half + GAP` -> `reach = half` (the rug and crate left touching their walls)"""
    import math
    from pxr import Usd
    from score.stages.assembly import fitting
    stage = Usd.Stage.CreateInMemory()
    for name, low, high in (("deck_2", (3.19, -0.042, 2.0), (8.9, 0.158, 8.0)),
                            ("wall_3", (0.0, -0.242, 6.699), (7.0, 3.0, 6.999)),
                            ("roof_1", (-9.0, 2.8, -9.0), (9.0, 3.4, 9.0)),
                            ("deck_3", (10.0, 2.758, 10.0), (16.0, 2.958, 16.0)),
                            ("wall_9", (20.0, 0.0, 20.0), (25.0, 3.0, 25.0)),
                            ("wall_5", (30.0, -0.242, 30.0), (30.14, 3.0, 33.0))):
        a_built_box(stage, f"/{TOY}/Structure/{name}", low, high)
    for name, low, high in (("ramp_1", (1.31, 0.0, 4.75), (3.31, 0.209, 5.95)),
                            ("sandbags_1", (2.9, 0.0, 4.0), (3.5, 0.2, 4.4)),
                            ("porch_post_1", (0.34, 0.0, 6.36), (1.04, 2.5, 6.84)),
                            ("lamp_1", (0.0, 2.75, 0.0), (0.5, 2.9, 0.5)),
                            ("stairs_1", (11.0, 0.0, 8.0), (12.0, 2.997, 10.5)),
                            ("locker_1", (15.5, 0.0, 12.0), (16.3, 2.9, 12.6)),
                            ("crate_2", (22.0, 0.0, 22.0), (22.5, 0.5, 22.5)),
                            ("cable_bundles_1", (29.8, 0.0, 30.0), (34.0, 2.0, 30.4)),  # clear of the ship,
                            ("spaceship_1", (-1.0, 0.0, 30.5), (33.0, 2.0, 32.5))):  # longer than the place
        a_built_box(stage, f"/{TOY}/Objects/{name}", low, high)
    ramp = {"how": "ramp", "edge": [[3.34, 8.19], [3.34, 2.08]], "up": [1.0, 0.0], "top": 0.2, "why": "up to the deck"}
    entries = [{"name": "ramp_1", "row": "ramp", "on": ramp},
               *[{"name": name, "row": name[:-2]} for name in ("sandbags_1", "porch_post_1", "lamp_1", "stairs_1",
                                                                "locker_1", "crate_2", "cable_bundles_1", "spaceship_1")]]
    fits = {fit["name"]: fit for fit in fitting.fitted(stage, TOY, entries, {entry["name"] for entry in entries})}
    assert sorted(fits) == ["cable_bundles_1", "locker_1", "porch_post_1", "ramp_1", "sandbags_1"], fits
    boxes = {name: fitting.world_box(stage, f"/{TOY}/Objects/{name}") for name in fits}
    low, high = boxes["ramp_1"]
    pitch = math.asin(0.158 / 2.0)
    assert abs(fits["ramp_1"]["pitch"] - round(math.degrees(pitch), 2)) < 1e-9, fits["ramp_1"]
    assert np.allclose([high[0], low[1], high[1]], [3.19, 0.0, 0.158 + 0.209 * math.cos(pitch)], atol=1e-4), boxes
    assert abs(boxes["sandbags_1"][0][1] - 0.158) < 1e-6 and abs(boxes["porch_post_1"][1][2] - 6.699) < 1e-6, boxes
    assert np.allclose(boxes["locker_1"][0], (16.0, 0.0, 12.0)), boxes  # out across, never sunk under the floor
    assert abs(boxes["cable_bundles_1"][0][0] - 30.14) < 1e-6, boxes  # clear past the thin wall's near side
    boxes.update({name: fitting.world_box(stage, f"/{TOY}/Objects/{name}") for name in ("stairs_1", "crate_2")})
    # settle@hangar (2026-11-10): its step ladder, a free-standing object, read as a climbing row and never moved out
    # of the 0.1 m landing pad it was laid in; a stair, a ladder and a stair's railing still climb
    assert [fitting.climbs({"row": row}) for row in ("stairs", "ladder", "stair_railing", "step_ladder")] == [
        True, True, True, False]
    # ... and the 0.1 m landing pad, a piece laid on the floor (design_shell.floor_pieces), was no static: the ladder
    # laid at the floor inside it is moved up onto it; 2 cm floor grates hold nothing, and a 0.2 m ceiling beam is
    # none
    from pxr import Usd
    padded = Usd.Stage.CreateInMemory()
    a_built_box(padded, f"/{TOY}/Structure/landing_pad_1", (0.0, 0.0, 0.0), (4.0, 0.1, 4.0))
    a_built_box(padded, f"/{TOY}/Objects/step_ladder_1", (1.0, 0.0, 1.0), (1.6, 2.0, 1.4))
    [moved] = fitting.moved_out(padded, TOY, [{"name": "step_ladder_1", "row": "step_ladder"}])
    assert moved["holder"] == ["landing_pad_1"] and np.isclose(moved["low"][1], 0.1), moved
    pieces = [("landing_pad_1", (np.zeros(3), np.array([4.0, 0.1, 4.0]))),
              ("floor_grates_1", (np.zeros(3), np.array([4.0, 0.02, 4.0]))),
              ("ceiling_beam_1", (np.array([0.0, 4.4, 0.0]), np.array([4.0, 4.6, 0.3])))]
    assert [name for name, _ in fitting.statics(pieces)] == ["landing_pad_1", "floor_grates_1"]
    ship = fitting.world_box(stage, f"/{TOY}/Objects/spaceship_1")
    assert np.allclose(ship[0], (-1.0, 0.0, 30.5)), ship  # no spot clear of the wall in the place: left as laid, named
    walls = [{"name": name, "low": list(found[0]), "high": list(found[1])}
             for name, found in fitting.walls(stage, TOY)]
    laid = {"walls": walls, "objects": [{"name": name, "low": list(box[0]), "high": list(box[1])}
                                        for name, box in boxes.items()]}
    assert fitting.held_faults({"objects": entries}, laid) == [], fitting.held_faults({"objects": entries}, laid)
    laid["objects"].append({"name": "spaceship_1", "low": list(ship[0]), "high": list(ship[1])})
    assert fitting.held_faults({"objects": entries}, laid) == [
        ("spaceship_1", "laid 0.14 m inside wall_5, nothing holding it there", 0.14)], laid
    door = {"how": "in", "middle": [0.5, 0.0, 6.849], "along": [1.0, 0.0], "wide": 1.0, "tall": 2.0, "why": "opening"}
    record = {"objects": [{"name": "crate_1"}, {"name": "door_1", "on": door, "fills": True}]}
    laid = {"walls": walls, "objects": [{"name": "crate_1", "low": [4.0, 0.0, 3.0], "high": [4.5, 0.4, 3.5]},
                                        {"name": "door_1", "low": [0.0, 0.0, 6.799], "high": [1.0, 2.0, 6.899]}]}
    assert fitting.held_faults(record, laid) == [
        ("crate_1", "laid 0.16 m inside deck_2, nothing holding it there", 0.158)], fitting.held_faults(record, laid)
    # docking_airlock (2026-11-11): its door's window, filling the door hung in its opening, failed as 0.10 m in the
    # wall; a window on no door it fills is in the wall all the same
    window = {"name": "window_1", "on": {"how": "within", "holder": ["door_1"]}, "fills": True}
    framed = {**laid, "objects": [*laid["objects"][1:],
                                  {"name": "window_1", "low": [0.3, 1.0, 6.8], "high": [0.7, 1.5, 6.89]}]}
    assert fitting.held_faults({"objects": [record["objects"][1], window]}, framed) == []
    loose = [fault[0] for fault in fitting.held_faults({"objects": [record["objects"][1], {**window, "fills": False}]},
                                                       framed)]
    assert "window_1" in loose, loose
    # garage (2026-11-11): boxes stacked on the boxes on its shelf units' tops were named 0.33 m off their shelves.
    # A box standing on one within the same shelf stands on it; one floating over it is still named.
    shelf = {"how": "within", "holder": ["shelf_1"]}
    stack = {"objects": [{"name": "shelf_1", "low": [0.0, 0.0, 0.0], "high": [1.0, 1.0, 0.5]},
                         {"name": "box_1", "low": [0.1, 1.0, 0.1], "high": [0.4, 1.3, 0.4]},
                         {"name": "box_2", "low": [0.1, 1.3, 0.1], "high": [0.4, 1.6, 0.4]}]}
    piled = {"objects": [{"name": "shelf_1"}, {"name": "box_1", "on": shelf}, {"name": "box_2", "on": shelf}]}
    assert fitting.held_faults(piled, stack) == [], fitting.held_faults(piled, stack)
    stack["objects"][2] = {"name": "box_2", "low": [0.1, 1.5, 0.1], "high": [0.4, 1.8, 0.4]}
    assert [fault[0] for fault in fitting.held_faults(piled, stack)] == ["box_2"]
    # storage (2026-11-11): bags on their units' top boards reach 0.07 m over the units' frames; on its shelves that
    # is no fault, a thing within its holder otherwise is
    bag = {"objects": [{"name": "shelf_1", "low": [0.0, 0.0, 0.0], "high": [1.0, 1.0, 0.5]},
                       {"name": "bag_1", "low": [0.1, 0.8, 0.1], "high": [0.4, 1.07, 0.4]}]}
    shelved = {"how": "within", "holder": ["shelf_1"], "why": f"{fitting.SHELVES}shelf: its reading says 'top shelves'"}
    assert fitting.held_faults({"objects": [{"name": "shelf_1"}, {"name": "bag_1", "on": shelved}]}, bag) == []
    assert [fault[0] for fault in fitting.held_faults({"objects": [{"name": "shelf_1"}, {"name": "bag_1", "on": shelf}]},
                                                      bag)] == ["bag_1"]
    # lab (2026-11-11): things by its short slanted walls named in them by the walls' world boxes. A slab 1 m long
    # and 0.1 m thick at 45 degrees: its own box (wall_corners) is that thin slab; a crate in its world box's corner,
    # clear of the slab, is in no wall by it, and in the wall by the world box alone.
    from pxr import Usd as _Usd, UsdGeom as _UsdGeom
    slanted = _Usd.Stage.CreateInMemory()
    run, out = np.array([1.0, 0.0, 1.0]) / 2 ** 0.5, np.array([-1.0, 0.0, 1.0]) / 2 ** 0.5
    points = [tuple(float(value) for value in run * along + out * across + [0.0, height, 0.0])
              for along in (0.0, 1.0) for height in (0.0, 3.0) for across in (0.0, 0.1)]
    _UsdGeom.Xform.Define(slanted, f"/{TOY}/Structure/wall_1")
    _UsdGeom.Mesh.Define(slanted, f"/{TOY}/Structure/wall_1/geo").CreatePointsAttr(points)
    own = fitting.wall_corners(slanted, f"/{TOY}/Structure/wall_1")
    crate = fitting.box_corners((np.array([0.55, 0.0, 0.0]), np.array([0.7, 1.0, 0.15])))
    wall_box = (np.min(points, axis=0), np.max(points, axis=0))
    assert fitting.inside_of(crate.min(axis=0), crate.max(axis=0), [("wall_1", wall_box)], crate,
                             {"wall_1": own}) == []
    assert [name for name, _ in fitting.inside_of(crate.min(axis=0), crate.max(axis=0), [("wall_1", wall_box)],
                                                  crate)] == ["wall_1"]
    # lab and greenhouse (2026-11-11): pipes and railings turned along slanted walls and stairs failed as inside walls
    # and each other by their world boxes. A 2.83 m pipe at 45 degrees passing 0.09 m clear of a wall's end stands in
    # no wall by its turned box (its world box is 0.2 m in it); moved 0.5 m back along the wall it is in it.
    def pipe(middle):
        along, up, out = np.array([1.0, 0.0, 1.0]), np.array([0.0, 0.05, 0.0]), np.array([-1.0, 0.0, 1.0]) * 0.05 / 2 ** 0.5
        corners = [np.asarray(middle, float) + one * along + two * up + three * out
                   for one in (-1, 1) for two in (-1, 1) for three in (-1, 1)]
        return {"name": "pipe_1", "low": list(np.min(corners, axis=0)), "high": list(np.max(corners, axis=0)),
                "corners": [list(point) for point in corners]}
    end = {"walls": [{"name": "wall_9", "low": [0.0, 0.0, 0.0], "high": [0.2, 3.0, 5.0]}]}
    assert fitting.held_faults({"objects": [{"name": "pipe_1"}]}, {**end, "objects": [pipe((0.0, 1.0, 5.0))]}) == []
    through = fitting.held_faults({"objects": [{"name": "pipe_1"}]}, {**end, "objects": [pipe((0.0, 1.0, 4.5))]})
    assert [fault[0] for fault in through] == ["pipe_1"], through
    room = Usd.Stage.CreateInMemory()
    for name, low, high in (("deck_1", (0.0, -0.2, 0.0), (6.0, 0.0, 4.0)), ("wall_1", (6.0, 0.0, 0.0), (6.2, 3.0, 4.0)),
                            ("wall_2", (-0.2, 0.0, 0.0), (0.0, 3.0, 4.0))):
        a_built_box(room, f"/{TOY}/Structure/{name}", low, high)
    a_built_box(room, f"/{TOY}/Fixtures/kit_1", (0.6, 0.0, 0.2), (1.2, 1.0, 0.8))
    floor = {"bed_1": ((2.0, 0.0, 0.5), (4.4, 0.6, 2.5)), "wardrobe_1": ((4.2, 0.0, 0.5), (5.4, 2.0, 1.1)),
             "crate_3": ((0.2, 0.0, 0.2), (0.8, 0.5, 0.8)), "rug_1": ((0.2, 0.0, 2.6), (2.2, 0.02, 3.8)),
             "table_1": ((0.7, 0.0, 2.9), (1.7, 0.8, 3.5))}
    for name, (low, high) in floor.items():
        a_built_box(room, f"/{TOY}/Objects/{name}", low, high)
    entries = [{"name": name, "row": name[:-2]} for name in floor]
    fits = fitting.fitted(room, TOY, entries, set(floor))
    assert sorted(fit["name"] for fit in fits if fit["how"] == "parted") == ["bed_1", "crate_3", "wardrobe_1"], fits
    laid = {name: fitting.world_box(room, f"/{TOY}/Objects/{name}") for name in floor}
    kit = fitting.world_box(room, f"/{TOY}/Fixtures/kit_1")
    assert all(np.allclose(laid[name][1] - laid[name][0], np.subtract(high, low)) for name, (low, high) in
               floor.items()), laid  # at its built size: never shrunk
    assert np.allclose(kit[0], (0.6, 0.0, 0.2)) and fitting.crossing({**laid, "kit_1": kit}, []) == 0, laid
    assert all(box[0][0] >= -1e-3 and box[1][0] <= 6.2 + 1e-3 for box in laid.values()), laid  # inside the walls
    assert all(np.allclose(laid[name][0], floor[name][0]) for name in ("rug_1", "table_1")), laid  # on its rug: left
    split = Usd.Stage.CreateInMemory()
    for name, low, high in (("wall_1", (-0.1, 0.0, 0.0), (0.0, 3.0, 4.0)), ("wall_2", (6.0, 0.0, 0.0), (6.1, 3.0, 4.0)),
                            ("wall_3", (0.0, 0.0, -0.1), (6.0, 3.0, 0.0)), ("wall_4", (0.0, 0.0, 4.0), (6.0, 3.0, 4.1)),
                            ("wall_5", (3.0, 0.0, 0.0), (3.1, 3.0, 4.0))):  # the inner wall: two rooms
        a_built_box(split, f"/{TOY}/Structure/{name}", low, high)
    a_built_box(split, f"/{TOY}/Fixtures/locker_1", (3.1, 0.0, 0.0), (6.0, 2.0, 2.5))
    across = {"bunk_bed_2": ((2.2, 0.0, 1.0), (4.2, 0.6, 2.0)), "bunk_bed_3": ((-0.2, 0.0, 0.0), (3.3, 0.6, 1.0))}
    for name, (low, high) in across.items():
        a_built_box(split, f"/{TOY}/Objects/{name}", low, high)
    fitting.fitted(split, TOY, [{"name": name, "row": "bunk_bed"} for name in across], set(across))
    bunks = {name: fitting.world_box(split, f"/{TOY}/Objects/{name}") for name in across}
    assert np.allclose(bunks["bunk_bed_2"][0], (3.1, 0.0, 2.5)), bunks  # its own room's free spot, not 1.2 m through
    assert np.allclose(bunks["bunk_bed_3"][0], across["bunk_bed_3"][0]), bunks  # 3.5 m in a 3 m room: left, named
    # engineroom (2026-11-08): its slanted corner walls, which the parting knew only by the box of the walls, took
    # core_1 5.48 m into one. A crate laid in a kit fixture beside a slanted corner wall (4, 0) to (6, 2) goes to a
    # free spot clear of the wall's outline and on the room's side of it, never the 0.6 m out of the fixture
    # along the wall it stands by into the corner.
    corner = Usd.Stage.CreateInMemory()
    for name, low, high in (("wall_1", (-0.1, 0.0, 0.0), (0.0, 3.0, 4.0)), ("wall_2", (6.0, 0.0, 0.0), (6.1, 3.0, 4.0)),
                            ("wall_3", (0.0, 0.0, -0.1), (6.0, 3.0, 0.0)), ("wall_4", (0.0, 0.0, 4.0), (6.0, 3.0, 4.1))):
        a_built_box(corner, f"/{TOY}/Structure/{name}", low, high)
    from pxr import Gf, UsdGeom
    UsdGeom.Xform.Define(corner, f"/{TOY}/Structure/wall_5").AddTransformOp().Set(Gf.Matrix4d(1.0))
    slab = UsdGeom.Mesh.Define(corner, f"/{TOY}/Structure/wall_5/geo")
    side = 0.1 / np.sqrt(2.0)
    slab.CreatePointsAttr([(x + way * side, y, z - way * side) for x, z in ((4.0, 0.0), (6.0, 2.0)) for way in (1, -1)
                           for y in (0.0, 3.0)])
    slab.CreateExtentAttr([(4.0 - side, 0.0, -side), (6.0 + side, 3.0, 2.0 + side)])
    a_built_box(corner, f"/{TOY}/Fixtures/kit_1", (2.0, 0.0, 0.0), (3.5, 1.0, 1.5))
    a_built_box(corner, f"/{TOY}/Objects/crate_4", (2.9, 0.0, 0.0), (3.5, 0.5, 0.6))
    fitting.fitted(corner, TOY, [{"name": "crate_4", "row": "crate"}], {"crate_4"})
    crate = fitting.world_box(corner, f"/{TOY}/Objects/crate_4")
    [(outline, _)] = fitting.slants(corner, TOY)
    assert not np.allclose(crate[0], (2.9, 0.0, 0.0)), crate  # out of the fixture
    assert fitting.slant_depth(fitting.foot_middle(*crate)[[0, 2]], (0.3, 0.3), outline)[0] <= 0.0, crate
    assert crate[1][0] - crate[0][2] <= 4.0, crate  # on the room's side of the wall's line
    assert fitting.crossing({"crate_4": crate}, [], fitting.slants(corner, TOY)) == 0, crate
    # settle@campgrounds (2026-11-11): its lander and a dome laid 0.65 and 0.76 m into ramp_1 and ramp_2, flights the
    # record builds as steps, which statics leaves out. A flight turned 45 degrees from (1, 1) up to (3, 3), 0.8 m
    # wide: a crate laid on its middle is parted clear of its outline; one in its box's corner, 1.2 m off its line,
    # is clear of it and stays.
    import builders
    flown = Usd.Stage.CreateInMemory()
    steps = builders.stairs((1.0, 0.0, 1.0), (3.0, 1.0, 3.0), 0.8, 5, "s")
    UsdGeom.Xform.Define(flown, f"/{TOY}/Structure/ramp_6").AddTransformOp().Set(Gf.Matrix4d(1.0))
    flight = UsdGeom.Mesh.Define(flown, f"/{TOY}/Structure/ramp_6/geo")
    flight.CreatePointsAttr([tuple(map(float, point)) for point in steps["points"]])
    flight.CreateExtentAttr([tuple(map(float, steps["points"].min(axis=0))),
                             tuple(map(float, steps["points"].max(axis=0)))])
    laid_by = {"crate_5": ((2.3, 0.0, 2.3), (2.9, 0.5, 2.9)), "crate_6": ((2.7, 0.0, 1.0), (3.0, 0.3, 1.3))}
    for name, (low, high) in laid_by.items():
        a_built_box(flown, f"/{TOY}/Objects/{name}", low, high)
    fitting.fitted(flown, TOY, [{"name": name, "row": "crate"} for name in laid_by], set(laid_by))
    crates = {name: fitting.world_box(flown, f"/{TOY}/Objects/{name}") for name in laid_by}
    assert not np.allclose(crates["crate_5"][0], laid_by["crate_5"][0]), crates  # parted off the flight
    assert fitting.crossing(crates, [], fitting.slants(flown, TOY)) == 0, crates
    # settle@street (2026-11-11): its police car stood 0.044 m into wall_12, too little for the parting to take it.
    # It is moved back out the way it came, along the floor; one across the wall, or only touching it, is left; a
    # slanted wall's box is no wall piece's shape.
    wall_12 = (np.array([4.15, -0.2, -19.3]), np.array([4.45, 3.5, 18.45]))
    car = (np.array([0.478, 0.2, 8.937]), np.array([4.194, 1.521, 10.868]))
    assert np.allclose(fitting.shallow_out(*car, wall_12), (-0.044, 0.0, 0.0)), fitting.shallow_out(*car, wall_12)
    assert fitting.shallow_out(car[0], car[1] + (0.3, 0.0, 0.0), wall_12) is None
    assert fitting.shallow_out(car[0], car[1] - (0.04, 0.0, 0.0), wall_12) is None
    assert fitting.straight(wall_12) and not fitting.straight(((1.35, -0.2, -11.89), (2.53, 24.0, -8.72)))
    # settle@greenhouse (2026-11-11): its railings, 9.4 m chords turned off the floor's axes, have world boxes 3.7 m
    # deep, and its upper floor stops short of its walls. A desk clear of a railing turned 30 degrees, in its box,
    # stays (judged by the railing's outline, never its box); of two desks laid in each other at the deck's corner,
    # the one parted stays on the deck (x and z 0 to 4 at 3 m), never past its edge into the room's 2 m beyond it.
    decked = Usd.Stage.CreateInMemory()
    for name, low, high in (("wall_1", (-0.1, 0.0, 0.0), (0.0, 6.0, 6.0)), ("wall_2", (6.0, 0.0, 0.0), (6.1, 6.0, 6.0)),
                            ("wall_3", (0.0, 0.0, -0.1), (6.0, 6.0, 0.0)), ("wall_4", (0.0, 0.0, 6.0), (6.0, 6.0, 6.1)),
                            ("deck_2", (0.0, 2.8, 0.0), (4.0, 3.0, 4.0))):
        a_built_box(decked, f"/{TOY}/Structure/{name}", low, high)
    UsdGeom.Mesh(decked.GetPrimAtPath(f"/{TOY}/Structure/deck_2/geo")).CreateFaceVertexCountsAttr([4])
    UsdGeom.Mesh(decked.GetPrimAtPath(f"/{TOY}/Structure/deck_2/geo")).CreateFaceVertexIndicesAttr([2, 3, 7, 6])  # top
    UsdGeom.Xform.Define(decked, f"/{TOY}/Objects/railing_1").AddTransformOp().Set(
        Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), 30.0)) * Gf.Matrix4d().SetTranslate(Gf.Vec3d(2.0, 3.5,
                                                                                                         1.5)))
    UsdGeom.Cube.Define(decked, f"/{TOY}/Objects/railing_1/geo").AddScaleOp().Set(Gf.Vec3f(2.0, 0.5, 0.01))
    desks = {"desk_1": ((2.4, 3.0, 2.0), (3.2, 3.5, 2.5)), "desk_2": ((2.8, 3.0, 3.2), (3.8, 3.5, 3.9)),
             "desk_3": ((3.1, 3.0, 3.3), (3.9, 3.5, 3.95))}
    for name, (low, high) in desks.items():
        a_built_box(decked, f"/{TOY}/Objects/{name}", low, high)
    assert fitting.thin_outline(decked, f"/{TOY}/Objects/railing_1") is not None and fitting.thin_outline(
        decked, f"/{TOY}/Objects/desk_1") is None
    fitting.fitted(decked, TOY, [{"name": name, "row": name[:-2]} for name in ("railing_1", *desks)],
                   {"railing_1", *desks})
    after = {name: fitting.world_box(decked, f"/{TOY}/Objects/{name}") for name in desks}
    assert np.allclose(after["desk_1"][0], desks["desk_1"][0]), after  # in the railing's box, clear of it: stays
    assert not np.allclose(after["desk_2"][0], desks["desk_2"][0]) or not np.allclose(
        after["desk_3"][0], desks["desk_3"][0]), after  # parted
    assert all(box[0][0] >= -1e-6 and box[0][2] >= -1e-6 and box[1][0] <= 4.0 + 1e-6 and box[1][2] <= 4.0 + 1e-6
               for box in after.values()), after  # on the deck
    assert np.allclose(crates["crate_6"][0], laid_by["crate_6"][0]), crates  # by the outline, never the box
    record = {"objects": [{"name": name, "row": name[:-2]} for name in ("bed_1", "crate_3", "rug_1", "table_1")]}
    laid = {"walls": [], "objects": [{"name": name, "low": list(low), "high": list(high)} for name, (low, high) in
                                     {**floor, "crate_3": ((2.5, 0.0, 1.0), (3.1, 0.5, 1.6))}.items()]}
    assert fitting.held_faults(record, laid) == [
        ("bed_1", "laid 0.50 m inside crate_3 at its built size, nothing holding either there", 0.5)], laid
    shelf = {"how": "within", "holder": ["shelf_1"], "why": "within shelf"}
    record = {"objects": [{"name": "desk_1", "row": "desk"},
                          {"name": "shelf_1", "row": "shelf", "on": {"how": "top", "holder": ["desk_1"]}},
                          *[{"name": f"jar_{number}", "row": "jar", "on": shelf} for number in (1, 2)],
                          {"name": "book_1", "row": "book", "on": shelf}]}
    held = {"desk_1": ((0.0, 0.0, 0.0), (2.0, 0.8, 1.0)), "shelf_1": ((0.2, 0.0, 0.2), (1.8, 0.79, 0.8)),
            "jar_1": ((0.3, 0.3, 0.3), (0.5, 0.5, 0.5)), "jar_2": ((0.31, 0.3, 0.3), (0.51, 0.5, 0.5)),
            "book_1": ((1.0, 0.2, 0.3), (1.3, 0.5, 0.6))}
    laid = {"walls": [], "objects": [{"name": name, "low": list(low), "high": list(high)}
                                     for name, (low, high) in held.items()]}
    found = [fault for fault in fitting.held_faults(record, laid) if "inside" in fault[1]]
    assert found == [("jar_1", "laid 0.19 m inside jar_2 at its built size", 0.19)], found  # never its shelf or desk
    # settle@habitat (2026-11-11): its potted plant and table lamp stood across 2 cm rugs' edges and leaned 4.2 and 4.9
    # degrees once dropped; its sofa, parted, stood 0.047 m into a table lamp, which the parting lets stand. A 0.28 m
    # plant across a rug's edge is moved 0.11 m wholly off it (the least way: on it is 0.18 m); a 1.2 m table across
    # it leans under 3 degrees and is left; the lamp is moved 0.047 m out of the sofa, the smaller of the two; a crate
    # 0.2 m into a chest is the parting's, and one touching 0.02 m into another is left.
    rugged = Usd.Stage.CreateInMemory()
    rugs = {"rug_1": ((0.0, 0.0, 0.0), (2.0, 0.02, 2.0)), "plant_1": ((1.9, 0.0, 0.5), (2.18, 0.4, 0.78)),
            "table_1": ((1.5, 0.0, 1.0), (2.7, 0.75, 1.6)), "sofa_1": ((4.0, 0.0, 0.0), (6.0, 0.9, 0.874)),
            "lamp_1": ((4.5, 0.0, 0.827), (4.78, 0.5, 1.127)), "chest_1": ((8.0, 0.0, 0.0), (9.0, 0.8, 1.0)),
            "crate_1": ((8.8, 0.0, 0.2), (9.4, 0.5, 0.8)), "crate_2": ((7.42, 0.0, 2.0), (8.02, 0.5, 2.6)),
            "chest_2": ((8.0, 0.0, 1.8), (9.0, 0.8, 2.8))}
    for name, (low, high) in rugs.items():
        a_built_box(rugged, f"/{TOY}/Objects/{name}", low, high)
    fits = fitting.fitted(rugged, TOY, [{"name": name, "row": name[:-2]} for name in rugs], set(rugs))
    assert sorted((fit["name"], fit["how"], fit["moved"]) for fit in fits if fit["how"] != "parted") == [
        ("lamp_1", "apart", 0.047), ("plant_1", "off edge", 0.11)], fits
    assert np.allclose(fitting.world_box(rugged, f"/{TOY}/Objects/plant_1")[0], (2.01, 0.0, 0.5)), fits
    assert np.allclose(fitting.world_box(rugged, f"/{TOY}/Objects/lamp_1")[0], (4.5, 0.0, 0.874)), fits
    # settle@greenhouse (2026-11-11): desk_6 was parted 1.07 m and computer_4, laid on its top, stayed at its plan spot,
    # at the desk's edge. A desk laid 0.6 m into a kit fixture is parted 1 m along x; the computer on its top moves
    # the same 1 m with it, 0.9 m from the desk's near side as laid, never left at that side.
    desked = Usd.Stage.CreateInMemory()
    for name, low, high in (("wall_1", (-0.1, 0.0, 0.0), (0.0, 3.0, 6.0)), ("wall_2", (6.0, 0.0, 0.0), (6.1, 3.0, 6.0)),
                            ("wall_3", (0.0, 0.0, -0.1), (6.0, 3.0, 0.0)), ("wall_4", (0.0, 0.0, 6.0), (6.0, 3.0, 6.1))):
        a_built_box(desked, f"/{TOY}/Structure/{name}", low, high)
    a_built_box(desked, f"/{TOY}/Fixtures/kit_1", (2.0, 0.0, 2.0), (4.0, 1.0, 4.0))
    a_built_box(desked, f"/{TOY}/Objects/desk_6", (3.0, 0.0, 2.5), (4.6, 0.75, 3.3))
    a_built_box(desked, f"/{TOY}/Objects/computer_4", (3.9, 0.75, 2.7), (4.3, 1.15, 3.0))
    fits = fitting.fitted(desked, TOY, [{"name": "desk_6", "row": "desk"}, {
        "name": "computer_4", "row": "computer", "on": {"how": "top", "holder": ["desk_6"]}}], {"desk_6", "computer_4"})
    desk, computer = (fitting.world_box(desked, f"/{TOY}/Objects/{name}") for name in ("desk_6", "computer_4"))
    assert np.allclose(desk[0], (4.0, 0.0, 2.5), atol=1e-6), fits
    assert np.allclose(computer[0], (4.9, 0.75, 2.7), atol=1e-6), fits
    ducted = Usd.Stage.CreateInMemory()
    for name, low, high in (("wall_1", (-0.126, -0.2, -0.126), (1.5, 2.5, 0.0)),
                            ("wall_3", (-0.126, -0.2, 10.0), (1.5, 2.5, 10.126)),
                            ("wall_4", (-0.126, -0.2, -0.126), (0.0, 2.5, 10.126))):
        a_built_box(ducted, f"/{TOY}/Shell/{name}", low, high)
    for name, low, high in (("duct_1", (0.5, 1.7, -0.03), (0.8, 2.3, 10.03)),
                            ("light_1", (-0.0503, 0.0, 3.0), (-0.0037, 0.06, 3.8)),
                            ("beam_1", (1.0, 0.5, -0.03), (1.2, 0.7, 11.97))):
        a_built_box(ducted, f"/{TOY}/Objects/{name}", low, high)
    from pxr import Gf, UsdGeom, UsdLux
    for name, at in (("light_lamp", (-0.0270, 0.03, 3.4)), ("duct_lamp", (0.65, 2.0, 5.0)),
                     ("beside_lamp", (0.3, 0.03, 3.4))):
        UsdLux.SphereLight.Define(ducted, f"/{TOY}/Lights/{name}").AddTranslateOp().Set(Gf.Vec3d(*at))
    fits = fitting.fitted(ducted, TOY, [{"name": name, "row": name[:-2]} for name in ("duct_1", "light_1", "beam_1")],
                          {"duct_1", "light_1", "beam_1"})
    duct, light, beam = (fitting.world_box(ducted, f"/{TOY}/Objects/{name}") for name in ("duct_1", "light_1",
                                                                                           "beam_1"))
    assert np.allclose(duct, ((0.5, 1.7, 0.0), (0.8, 2.3, 10.0)), atol=1e-6), fits
    assert np.allclose(light, ((0.0, 0.0, 3.0), (0.0466, 0.06, 3.8)), atol=1e-6), fits
    assert abs(float(beam[1][2] - beam[0][2]) - 12.0) < 1e-6, fits
    from score.stages.assembly import lamps_along
    spots = {prim.GetName(): np.array(UsdGeom.Xformable(prim).GetOrderedXformOps()[0].Get())
             for prim in ducted.GetPrimAtPath(f"/{TOY}/Lights").GetChildren()}
    lamps = {name: (spot, lamps_along.laid_at(ducted, f"/{TOY}/Lights/{name}", spot)) for name, spot in spots.items()}
    assert np.allclose(lamps["light_lamp"], ((0.0233, 0.03, 3.4), (-0.027, 0.03, 3.4)), atol=1e-4), lamps
    assert np.allclose(lamps["duct_lamp"], ((0.65, 2.0, 5.0),) * 2) and np.allclose(
        lamps["beside_lamp"], ((0.3, 0.03, 3.4),) * 2), lamps
    walled = Usd.Stage.CreateInMemory()
    for name, low, high, degrees in (("wall_1", (-0.1, 0.0, 0.0), (0.0, 3.0, 6.0), 0.0),
                                     ("wall_2", (6.0, 0.0, 0.0), (6.1, 3.0, 6.0), 0.0),
                                     ("wall_3", (0.0, 0.0, -0.1), (6.0, 3.0, 0.0), 0.0),
                                     ("wall_4", (0.0, 0.0, 6.0), (6.0, 3.0, 6.1), 0.0),
                                     ("wall_5", (1.52, 0.0, 2.0), (1.62, 3.0, 6.0), 0.0),
                                     ("wall_6", (1.0 - 2 ** 0.5 / 2, 0.0, 0.95), (1.0 + 2 ** 0.5 / 2, 3.0, 1.05), 45.0)):
        a_solid_box(walled, f"/{TOY}/Structure/{name}", low, high, degrees)
    corner = 2.0 - 0.05 * 2 ** 0.5 + 0.02 * 2 ** 0.5  # the crate's far corner's x + z: 2 cm into wall_6's near face
    for name, low, high in (("rug_2", (0.0, 0.0, 3.0), (2.0, 0.017, 4.0)),
                            ("rug_3", (2.0, 0.0, 4.504), (4.0, 0.017, 6.004)),
                            ("crate_1", (0.5, 0.0, corner - 1.5), (1.0, 0.5, corner - 1.0))):
        a_solid_box(walled, f"/{TOY}/Objects/{name}", low, high)
    things = ("rug_2", "rug_3", "crate_1")
    fits = fitting.fitted(walled, TOY, [{"name": name, "row": name[:-2]} for name in things], set(things))
    found = {fit["name"]: (fit["how"], fit["moved"], fit["scale"]) for fit in fits
             if fit["how"] in ("flat clear", "off wall")}
    assert found == {"rug_2": ("flat clear", 0.24, 0.74), "crate_1": ("off wall", 0.036, 1.0)}, fits
    rug, crate = (fitting.world_box(walled, f"/{TOY}/Objects/{name}") for name in ("rug_2", "crate_1"))
    assert np.allclose(rug, ((0.02, 0.0, 3.13), (1.5, 0.017, 3.87)), atol=1e-6), rug
    assert np.allclose(crate[0][[0, 2]], (0.47, corner - 1.52), atol=1e-6), crate


def test_a_thing_up_through_a_roof_s_surface_is_moved_down_or_named_and_one_under_its_dome_is_left():
    """hangar's wall pipes stood 22 m up through its 15 m roof, and the inside-a-static check left roofs out because a
    dome's box holds the room under it. A roof is read by its mesh: a gable from 3 m eaves at x 0 and 10 to a 5 m ridge
    at x 5. A lamp under the ridge (its top 4.5 m, the roof 4.8 m over its edge) is inside the roof's box and left; a
    crate whose top corner reaches 3.6 m where the roof is 3.2 m is moved 0.4 m straight down; a ship 6 m tall 2.6 m
    up through it at its corner is left as laid (more than 1 m), and the held gate names it and a pipe its wall
    relation laid against its wall at the eave, 6 m up through the roof, by name and how far; a crate wholly above the
    roof is not through it, and a box on a loft deck under the eave, 0.42 m through, is left and named, never sunk
    into its deck. A light hung from the roof, built shorter than its reading (its top 0.4 m under the roof's 4.6 m over
    its corner, settle@airlock's roof light 0.13 m under its dome), is moved up to 0.01 m under it. A crane hung from
    the roof built taller than its reading, its box's top 2.1 m over the roof at its x 9 end, is hung down 2.11 m
    (more than 1 m: its hang sets its height) so its box's top stands 0.01 m under the roof. Of two cranes hung from
    the roof where a 10 m room holds one, the later is left out, never left in the other; two things on the floor
    are left as laid (the held gate names them). A valve on its pipe's top inside the pipe run packed over it is
    stacked onto that run, and the held gate judges it there. Under a frame roof (two 2 m edge strips at 5 m and a
    front strip, the middle open: hangar's, motion@hangar 2026-11-11) a crane hung by its box, its trolley's top 0.01 m
    under the roof up in the opening, its girder's ends 0.7 m under the strips touching nothing, is moved 0.69 m up so
    they stand 0.01 m under them, and 0.02 m out from under the front strip its trolley's lip overhangs by 0.01 m; a lip
    0.1 m under it (more than 0.05 m) is not moved out, so it hangs by that lip 0.39 m up; one already touching is left.
    Break: score/stages/assembly/fitting.py: `hung_up(stage, place, loose) + hung_by_parts(stage, place, loose)` ->
        `hung_up(stage, place, loose) + []` (the crane left hung by its box, touching nothing)
    Break: score/stages/assembly/fitting.py: part_hang's `if shift is None or float(np.linalg.norm(shift)) >
        HELD_MOST:` -> `if shift is None:` (the 0.1 m lip moved out), or its `lifts = sorted({...}, reverse=True)` ->
        `lifts = sorted({...})` (hung by the 0.01 m lip, the ends still 0.31 m under)
    Break: score/stages/assembly/fitting.py: `fits = moved_down(stage, place, [entry for entry in loose if
        entry.get("under roof")])` -> `fits = []` (the crane left 2.1 m through the roof), or moved_down's
        `(drop > OUT_MOST and not hung)` -> `drop > OUT_MOST`
    Break: score/stages/assembly/fitting.py: hung_up's `under_roof_gap(box_topped(surface_points(` ->
        `under_roof_gap((surface_points(` is caught by settle9's hangar only: a box's corners are its points
    Break: score/stages/assembly/fitting.py: parted_boxes' `if shift is None and name in hung:` -> `if False:` (both
        cranes left as laid in each other), or its `tried -= later` -> `pass` (the later never left out)
    Break: score/stages/assembly/fitting.py: `fits += stacked_on_runs(stage, place, topped, walled)` dropped, or
        held_faults' `stacked.get(entry["name"], on.get("holder") or [])` -> `on.get("holder") or []` (the stacked
        valve named off its holder's top)
    Break: score/stages/assembly/built_tops.py: stacked_down's `fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0,
        target)` dropped (hangar's valve left at its pipe's box top, 0.06 m over its surface), or held_faults' `if
        topped.get(entry["name"]) is not None:` -> `if False:` (the valve let down named off the pipe's box top)
    Break: score/stages/assembly/fitting.py: `return fits + moved_down(stage, place, loose)` -> `return fits`
    Break: score/stages/assembly/fitting.py: `+ hung_up(stage, place, loose)` -> `+ []`
    Break: score/stages/assembly/fitting.py: hung_up's `(np.inf if at_hang else OUT_MOST + ROOF_CLEAR)` -> `OUT_MOST +
        ROOF_CLEAR` (quarters' pipe left 4.5 m under the roof), or its `abs(...) <= MOVE_LEAST` -> `True` (the pipe
        moved off its hang moved up too); hung_up's `+ into_its_room(...)` or `+ clear_of_others(...)` dropped
        (quarters' pipe left through its wall, then across its lights: caught on quarters' laid seed), or
        clear_of_others' `shift[axis] += away * ...` -> `shift[axis] += 0.0 * ...` (the pipe left across the lights)
    Break: score/stages/assembly/fitting.py: roofs' `for scope in ("Structure", "Shell")]` -> `for scope in
        ("Structure",)]` (the Shell's dome is no roof: its light left under it)
    Break: score/stages/assembly/fitting.py: `if len(reach) and reach.min() < 0 < reach.max() else 0.0` -> `if
        len(reach) else 0.0`
    Break: score/stages/assembly/fitting.py: `lowest = height.min(axis=1)` -> `lowest = np.where(np.isfinite(height),
        height, -np.inf).max(axis=1)` (the roof's highest face over a place, as its box's top)
    Break: score/stages/assembly/fitting.py: `faults += [(entry["name"], f"laid {found['metres']:.2f} m up through`
        -> `faults += [] and [(entry["name"], ...`
    Break: score/stages/assembly/fitting.py: `if not through or drop > OUT_MOST or {name` -> `if not through or drop >
        OUT_MOST or False and {name`
    Break: score/stages/assembly/fitting.py: moved_in's `for _, triangles in built)` -> `for _, triangles in
        built) and False` (tube's screen left up through its vault), or its `for point in fit[key]] for key in
        ("span", "corners") if key in fit}})` -> `for point in fit[key]] for key in () if key in fit}})` (its face
        left on the wall's line, the held gate naming it 0.65 m off)
    Break: score/stages/assembly/fitting.py: `wall_clear.under_roofs(stage, place, walled, fits)` dropped (stairwell's
        lamp and conduit run left up through its roof), or wall_clear.py's `if float(lowered[0][1]) >= 0.0 and` ->
        `if` (the run sunk under the floor), or its `if scale < SHRINK_MOST:` -> `if False:` (the 4 m pipe shrunk to
        75%), or its `foot - out * deep * (1.0 - scale) / 2` -> `foot` (the run's back off its wall)
    Break: score/stages/assembly/fitting.py: `for box in rooms(leaf)), *climbing] if walled else ()` -> `for box in
        rooms(leaf))] if walled else ()` (stairwell's electrical box left in its stair railing), or wall_clear.py's
        climbing `if fitting.climbs(entry) and` -> `if False and`
    Break: score/stages/assembly/fitting.py: through_roof's `vault_feet.roof_over(points, near)` -> `roof_under(points,
        near)` (the screen on the bulged vault's wall read 2 m up through it), or vault_feet.py's `arched[:, None] &
        (found < foot)` -> `found < foot` (the crate read through none), or -> `False` (the screen read through it)
    Break: score/stages/assembly/fitting.py: `ribs.kept_clear(stage, place, path, entry["on"], clear, others, built)
        if turned` -> `(clear, built) if turned` (the screen and pipes left in the rib), or ribs.py's `if any(end -
        begin >= reach for begin, end in free):` -> `if True:` (the pipes shrunk to the 7.8 m beside it), or its
        `return [*clear, *parts], built` -> `return clear, [*built, *parts]` (the screen stood on the rib's front),
        or its `front = float((fronts[both] - (backs[both] - box_back)).max())` -> `pass` (the round pipe stood by
        its box's back, 0.04 m off the rib), or its `and (part := beside(mesh, start, run, out, band, own)) is not
        None]  # the pieces it crosses there` -> `if (part := ...) is not None]` (the pipe stood on the second rib
        by its bracket's back, 0.04 m off the first)
    Break: score/stages/assembly/fitting.py: `+ ribs.kept_off(stage, place, loose, list(by_name.values()))` -> `+ []`
        (the light left up in the rib, the lamp inside its leg), or ribs.py's `under = [(name, gap) for name, gap in
        over if gap < fitting.ROOF_CLEAR - fitting.MOVE_LEAST]` -> `under = over` (the light let down again), or
        `top = topped(*fitting.world_box(stage, path))` -> `top = fitting.box_topped(fitting.surface_points(stage,
        path))` (the light's corners, at its ends, stand under no rib: left up in it)
    Break: score/stages/assembly/vault_feet.py: `return fitting.wall_holes(built, on, band)` -> `return found` (the
        vault-only face one hole its whole length), or its `found = fitting.wall_holes(walls, on, band)` -> `found =
        fitting.wall_holes(built, on, band)` (the hole behind which the vault stands left unread)"""
    from pxr import Gf, Sdf, Usd, UsdGeom
    from score.stages.assembly import fitting
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(stage, f"/{TOY}/Structure/roof_1")
    roof = UsdGeom.Mesh.Define(stage, f"/{TOY}/Structure/roof_1/geo")
    roof.CreatePointsAttr([(0, 3, 0), (5, 5, 0), (5, 5, 10), (0, 3, 10), (10, 3, 0), (10, 3, 10),
                           (0, 3.1, 0), (5, 5.1, 0), (5, 5.1, 10), (0, 3.1, 10), (10, 3.1, 0), (10, 3.1, 10)])
    roof.CreateFaceVertexCountsAttr([4, 4, 4, 4])
    roof.CreateFaceVertexIndicesAttr([0, 1, 2, 3, 1, 4, 5, 2, 6, 7, 8, 9, 7, 10, 11, 8])
    a_built_box(stage, f"/{TOY}/Structure/deck_2", (0.0, 1.8, 8.5), (0.9, 2.0, 9.5))
    for name, low, high in (("lamp_1", (4.5, 3.5, 4.0), (5.5, 4.5, 5.0)),
                            ("box_1", (0.2, 2.0, 9.0), (0.6, 3.5, 9.4)),
                            ("crate_1", (0.5, 2.6, 1.0), (1.5, 3.6, 2.0)),
                            ("ship_1", (1.0, 0.0, 6.0), (3.0, 6.0, 8.0)),
                            ("crate_2", (2.0, 5.0, 2.0), (2.5, 5.5, 2.5)),
                            ("pipes_1", (8.0, 0.0, 4.0), (8.4, 9.0, 4.4)),
                            ("crane_1", (6.0, 3.5, 1.0), (9.0, 5.5, 3.0)),
                            ("light_1", (4.0, 3.8, 6.0), (4.4, 4.2, 6.4))):
        a_built_box(stage, f"/{TOY}/Objects/{name}", low, high)
    wall = {"how": "wall", "span": [[10.0, 0.0], [10.0, 10.0]], "out": [-1.0, 0.0], "why": "against its wall"}
    entries = [*[{"name": name, "row": name[:-2]} for name in ("lamp_1", "crate_1", "ship_1", "crate_2",
                                                                 "box_1")],
               {"name": "pipes_1", "row": "pipes", "on": wall}, {"name": "crane_1", "row": "crane", "under roof": True},
               {"name": "light_1", "row": "light", "under roof": True}]
    names = {entry["name"] for entry in entries}
    fitted = fitting.fitted(stage, TOY, entries, names)
    fits = [fit for fit in fitted if fit["how"] == "down"]
    assert [(fit["name"], fit["moved"], fit["holder"]) for fit in fits] == [("crane_1", 2.11, ["roof_1"]),
                                                                            ("crate_1", 0.4, ["roof_1"])], fits
    assert np.allclose(fitting.world_box(stage, f"/{TOY}/Objects/crane_1")[1], (9.0, 3.39, 3.0)), fits
    assert [(fit["name"], fit["moved"]) for fit in fitted if fit["how"] == "up"] == [("light_1", 0.39)], fitted
    assert np.allclose(fitting.world_box(stage, f"/{TOY}/Objects/light_1")[1], (4.4, 4.59, 6.4)), fitted
    assert np.allclose(fitting.world_box(stage, f"/{TOY}/Objects/crate_1")[1], (1.5, 3.2, 2.0)), fits
    assert np.allclose(fitting.world_box(stage, f"/{TOY}/Objects/ship_1")[0], (1.0, 0.0, 6.0))
    through = fitting.through_roofs(stage, TOY, sorted(names))
    assert [(found["name"], found["metres"]) for found in through] == [("box_1", 0.42), ("pipes_1", 6.0), ("ship_1", 2.6)], through
    faults = fitting.held_faults({"objects": entries}, {"roofs": through, "objects": [
        {"name": name, **dict(zip(("low", "high"), fitting.world_box(stage, f"/{TOY}/Objects/{name}")))}
        for name in ("pipes_1", "ship_1")]})
    assert [fault for fault in faults if "through" in fault[1]] == [
        ("ship_1", "laid 2.60 m up through roof_1, nothing holding it there", 2.6),
        ("pipes_1", "laid 6.00 m up through roof_1, nothing holding it there", 6.0)], faults
    # an inside place's roof under its Shell (design_shell.py) is a roof too: airlock's dome, its roof light left
    # 0.13 m under it (settle@airlock, 2026-11-10); a Shell wall is none
    shelled = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(shelled, f"/{TOY}/Shell/roof_1")
    dome = UsdGeom.Mesh.Define(shelled, f"/{TOY}/Shell/roof_1/geo")
    dome.CreatePointsAttr([(0, 3, 0), (5, 5, 0), (5, 5, 10), (0, 3, 10)])
    dome.CreateFaceVertexCountsAttr([4])
    dome.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    a_built_box(shelled, f"/{TOY}/Shell/wall_1", (0.0, 0.0, 0.0), (0.2, 3.0, 10.0))
    a_built_box(shelled, f"/{TOY}/Objects/light_1", (4.0, 3.8, 6.0), (4.4, 4.2, 6.4))
    assert [name for name, _ in fitting.roofs(shelled, TOY)] == ["roof_1"]
    assert [(fit["name"], fit["moved"]) for fit in fitting.hung_up(shelled, TOY, entries[-1:])] == [("light_1", 0.39)]
    # quarters' wall pipe (settle@quarters, 2026-11-13), read 4 m tall and built 4 m long, 0.33 m tall: the record hung
    # it 1.43 m under its floor, 3.68 m under its roof. One still at the record's hang is moved up however far (4.49 m
    # here, the dome 3.4 m up over its end); one moved off its hang is moved OUT_MOST at most, so left
    a_built_box(shelled, f"/{TOY}/Objects/pipe_1", (1.0, -1.43, 1.0), (4.0, -1.1, 1.2))
    a_built_box(shelled, f"/{TOY}/Objects/pipe_2", (1.0, -1.43, 3.0), (4.0, -1.1, 3.2))
    pipes = [{"name": "pipe_1", "row": "pipe", "under roof": True, "at": [2.5, -1.43, 1.1]},
             {"name": "pipe_2", "row": "pipe", "under roof": True, "at": [2.5, 0.0, 3.1]}]
    assert [(fit["name"], fit["moved"]) for fit in fitting.hung_up(shelled, TOY, pipes)] == [("pipe_1", 4.49)]
    # lifted, it ran 1.74 m on through its east wall, its room 4.23 m wide: one lifted into a wall piece is moved along
    # into the room between it and the piece facing it, then out of a string of lights already hung there; one longer
    # than that room is left
    roomed = Usd.Stage.CreateInMemory()
    for name, low, high in (("wall_1", (-0.2, 0.0, -1.0), (0.0, 2.5, 3.0)), ("wall_2", (4.23, 0.0, -1.0),
                                                                           (4.39, 2.5, 3.0))):
        a_built_box(roomed, f"/{TOY}/Shell/{name}", low, high)
    a_built_box(roomed, f"/{TOY}/Objects/lights_1", (4.18, 2.2, -1.0), (4.23, 2.375, 3.0))
    shift = fitting.into_its_room(roomed, TOY, np.array([2.0, 2.2, 0.0]), np.array([5.985, 2.5, 0.1]))
    assert np.allclose(shift, (-1.755, 0.0, 0.0)), shift
    away = fitting.clear_of_others(roomed, TOY, "pipe_9", np.array([0.245, 2.2, 0.0]), np.array([4.23, 2.5, 0.1]))
    assert np.allclose(away, (-0.06, 0.0, 0.0)) and not np.any(fitting.into_its_room(
        roomed, TOY, np.array([-0.5, 2.2, 0.0]), np.array([4.5, 2.5, 0.1]))), away
    cranes = {name: (np.array([0.0, 3.0, z]), np.array([10.0, 5.0, z + 6.0])) for name, z in (("crane_1", 0.0),
                                                                                                ("crane_2", 3.0))}
    sides = [(np.array(low, float), np.array(high, float)) for low, high in (
        ((-0.5, 0.0, -0.5), (10.5, 6.0, 0.0)), ((-0.5, 0.0, 10.0), (10.5, 6.0, 10.5)),
        ((-0.5, 0.0, 0.0), (0.0, 6.0, 10.0)), ((10.0, 0.0, 0.0), (10.5, 6.0, 10.0)))]
    after, left = fitting.parted_boxes(cranes, [], sides, [-0.5, -0.5, 10.5, 10.5], (), {"crane_1", "crane_2"})
    assert left == {"crane_2"} and list(after) == ["crane_1"], (after, left)
    assert -0.01 <= after["crane_1"][0][2] and after["crane_1"][1][2] <= 10.01, after
    after, left = fitting.parted_boxes(cranes, [], sides, [-0.5, -0.5, 10.5, 10.5])
    assert not left and sorted(after) == ["crane_1", "crane_2"], (after, left)
    for lip, moved, low in ((1.99, 0.69, (0.5, 4.69, 2.01)), (1.9, 0.39, (0.5, 4.39, 1.9))):
        frame = Usd.Stage.CreateInMemory()
        for name, (x0, x1, z0, z1) in (("roof_1", (0, 2, 0, 10)), ("roof_2", (8, 10, 0, 10)), ("roof_3", (2, 8, 0, 2))):
            UsdGeom.Xform.Define(frame, f"/{TOY}/Structure/{name}")
            strip = UsdGeom.Mesh.Define(frame, f"/{TOY}/Structure/{name}/geo")
            strip.CreatePointsAttr([(x0, 5, z0), (x1, 5, z0), (x1, 5, z1), (x0, 5, z1)])
            strip.CreateFaceVertexCountsAttr([4])
            strip.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        a_built_box(frame, f"/{TOY}/Objects/crane_1", (0.5, 4.0, 3.0), (9.5, 4.3, 6.0))  # the girder, its ends under
        a_built_box(frame, f"/{TOY}/Objects/crane_1/trolley", (4.0, 4.3, 2.1), (6.0, 4.99, 4.0))  # up in the opening
        a_built_box(frame, f"/{TOY}/Objects/crane_1/lip", (4.0, 4.3, lip), (6.0, 4.6, 2.1))  # under the front strip
        hung = fitting.fitted(frame, TOY, [{"name": "crane_1", "row": "crane", "under roof": True}], {"crane_1"})
        assert [(fit["name"], fit["how"], fit["moved"]) for fit in hung] == [("crane_1", "hung", moved)], hung
        assert np.allclose(fitting.world_box(frame, f"/{TOY}/Objects/crane_1")[0], low), hung
        assert fitting.hung_by_parts(frame, TOY, [{"name": "crane_1", "row": "crane", "under roof": True}]) == []
    runs = Usd.Stage.CreateInMemory()
    for name, low, high in (("pipe_3", (0.0, 1.0, 0.0), (4.0, 1.4, 0.4)),
                            ("pipe_1", (0.0, 1.45, 0.0), (4.0, 1.85, 0.4)),
                            ("valve_1", (1.0, 1.4, 0.1), (1.2, 1.7, 0.3)), ("valve_2", (3.0, 1.85, 0.1),
                                                                            (3.2, 2.15, 0.3))):
        a_built_box(runs, f"/{TOY}/Objects/{name}", low, high)
    topped = [{"name": name, "row": "valve", "on": {"how": "top", "holder": [holder]}}
              for name, holder in (("valve_1", "pipe_3"), ("valve_2", "pipe_1"))]
    stacked = fitting.stacked_on_runs(runs, TOY, topped, [{"name": "pipe_1"}, {"name": "pipe_3"}])
    assert [(fit["name"], fit["moved"], fit["holder"]) for fit in stacked] == [("valve_1", 0.45, ["pipe_1"])], stacked
    laid = {"objects": [{"name": name, **dict(zip(("low", "high"), fitting.world_box(runs, f"/{TOY}/Objects/{name}")))}
                        for name in ("pipe_3", "pipe_1", "valve_1")], "fitted": stacked}
    assert not fitting.held_faults({"objects": topped[:1]}, laid), laid
    assert fitting.held_faults({"objects": topped[:1]}, {**laid, "fitted": []})
    # hangar (2026-11-11): its valve, lifted to the box top of the pipe packed over its own, stood 0.06 m over that
    # pipe's surface. A pipe built 0.4 m round with a rail up 0.06 m at its far end lets the valve stacked onto it down
    # to its surface (1.79), and the held gate measures it there.
    from score.stages.assembly import built_tops
    from pxr import Gf
    railed = Usd.Stage.CreateInMemory()
    built = trimesh.util.concatenate([trimesh.creation.box(bounds=[(0.0, 1.45, 0.0), (4.0, 1.79, 0.4)]),
                                      trimesh.creation.box(bounds=[(3.9, 1.79, 0.0), (4.0, 1.85, 0.4)])])
    UsdGeom.Xform.Define(railed, f"/{TOY}/Objects/pipe_1").AddTransformOp().Set(Gf.Matrix4d(1.0))
    pipe = UsdGeom.Mesh.Define(railed, f"/{TOY}/Objects/pipe_1/geo")
    pipe.CreatePointsAttr([tuple(map(float, point)) for point in built.vertices])
    pipe.CreateFaceVertexCountsAttr([3] * len(built.faces))
    pipe.CreateFaceVertexIndicesAttr([int(index) for index in built.faces.ravel()])
    for name, low, high in (("pipe_3", (0.0, 1.0, 0.0), (4.0, 1.4, 0.4)),
                            ("valve_1", (1.0, 1.4, 0.1), (1.2, 1.7, 0.3))):
        a_built_box(railed, f"/{TOY}/Objects/{name}", low, high)
    stacked = fitting.stacked_on_runs(railed, TOY, topped[:1], [{"name": "pipe_1"}, {"name": "pipe_3"}])
    down = built_tops.stacked_down(railed, TOY, stacked)
    assert [(fit["name"], fit["top at"]) for fit in down] == [("valve_1", 1.79)], down
    assert np.isclose(fitting.world_box(railed, f"/{TOY}/Objects/valve_1")[0][1], 1.79)
    laid = {"objects": [{"name": name, **dict(zip(("low", "high"), fitting.world_box(railed, f"/{TOY}/Objects/{name}")))
                         } for name in ("pipe_3", "pipe_1", "valve_1")], "fitted": stacked + down}
    assert not fitting.held_faults({"objects": topped[:1]}, laid), fitting.held_faults({"objects": topped[:1]}, laid)
    # tube (2026-11-11): its screens and panels laid on its plan walls' lines stood up through its vault, whose sides
    # curve in over them. Under the gable (3 m at x 10, rising 0.4 m a metre in) a screen on the x 10 wall, its top
    # 3.3 m, 0.3 m through, is moved 0.65 m into the room, its fit's face with it, and the held gate passes it; the
    # 9 m pipes no step clears are left, named.
    vault = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(vault, f"/{TOY}/Structure/roof_1")
    arch = UsdGeom.Mesh.Define(vault, f"/{TOY}/Structure/roof_1/geo")
    arch.CreatePointsAttr([(0, 3, 0), (5, 5, 0), (5, 5, 10), (0, 3, 10), (10, 3, 0), (10, 3, 10)])
    arch.CreateFaceVertexCountsAttr([4, 4])
    arch.CreateFaceVertexIndicesAttr([0, 1, 2, 3, 1, 4, 5, 2])
    a_built_box(vault, f"/{TOY}/Structure/deck_1", (0.0, -0.2, 0.0), (10.0, 0.0, 10.0))
    floor = UsdGeom.Mesh(vault.GetPrimAtPath(f"/{TOY}/Structure/deck_1/geo"))
    floor.CreateFaceVertexCountsAttr([4])
    floor.CreateFaceVertexIndicesAttr([2, 3, 7, 6])
    a_built_box(vault, f"/{TOY}/Objects/screen_1", (9.8, 2.8, 4.0), (10.0, 3.3, 5.0))
    a_built_box(vault, f"/{TOY}/Objects/pipes_1", (9.6, 0.0, 6.0), (10.0, 9.0, 6.4))
    screens = [{"name": name, "row": name[:-2], "on": wall} for name in ("screen_1", "pipes_1")]
    moved = [{"name": "screen_1", "row": "screen", "how": "wall", "holder": None, "moved": 0.0, "scale": 1.0,
              "words": "laid wall", "span": [[10.0, 0.0], [10.0, 10.0]], "out": [-1.0, 0.0],
              "corners": [[9.8, 4.0], [9.8, 5.0], [10.0, 4.0], [10.0, 5.0]]}]  # as fitted laid it
    fitting.moved_in(vault, TOY, screens, moved)
    assert [(fit["name"], fit["moved"]) for fit in moved] == [("screen_1", 0.65)], moved
    assert np.allclose(moved[0]["span"], [[9.35, 0.0], [9.35, 10.0]]), moved
    assert np.allclose(fitting.world_box(vault, f"/{TOY}/Objects/screen_1")[1], (9.35, 3.3, 5.0)), moved
    walled = {"objects": [{"name": "screen_1", **dict(zip(("low", "high"), fitting.world_box(
        vault, f"/{TOY}/Objects/screen_1")))}], "fitted": moved}
    assert fitting.held_faults({"objects": screens[:1]}, walled) == [], fitting.held_faults({"objects": screens[:1]},
                                                                                            walled)
    # stairwell (2026-11-11): its conduit runs, built 3.1 m tall from the floor of a room 3 m to its flat roof, stood
    # 0.1 m up through it, which no move into the room clears; its wall lamp 0.15 m. The lamp is moved 0.16 m down so
    # its top stands 0.01 m under the roof; the run, on the floor, is shrunk to 96% about its foot, its back kept on
    # its wall; one 4 m tall (75%) is left for the held gate. Its electrical box, laid where a stair railing reaches
    # its wall, is slid along the wall clear of the railing (the parting never moves a climbing row's things).
    flat = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(flat, f"/{TOY}/Structure/roof_1")
    slab = UsdGeom.Mesh.Define(flat, f"/{TOY}/Structure/roof_1/geo")
    slab.CreatePointsAttr([(0, 3, -1), (10, 3, -1), (10, 3, 10), (0, 3, 10)])
    slab.CreateFaceVertexCountsAttr([4])
    slab.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    UsdGeom.Xform.Define(flat, f"/{TOY}/Structure/wall_1")
    back = trimesh.creation.box(bounds=((0.0, 0.0, -0.2), (10.0, 3.0, 0.0)))
    drawn = UsdGeom.Mesh.Define(flat, f"/{TOY}/Structure/wall_1/geo")
    drawn.CreatePointsAttr([tuple(map(float, point)) for point in back.vertices])
    drawn.CreateFaceVertexCountsAttr([3] * len(back.faces))
    drawn.CreateFaceVertexIndicesAttr([int(index) for index in back.faces.reshape(-1)])
    for name, low, high in (("conduit_1", (1.0, 0.0, 0.0), (1.1, 3.1, 0.2)),
                            ("lamp_1", (5.0, 2.5, 0.0), (5.2, 3.15, 0.15)),
                            ("pipes_2", (7.0, 0.0, 0.0), (7.1, 4.0, 0.1)), ("box_1", (1.9, 1.0, 0.0), (2.3, 1.4, 0.2)),
                            ("stair_railing_1", (2.0, 0.0, 0.0), (2.1, 1.5, 3.0))):
        a_built_box(flat, f"/{TOY}/Objects/{name}", low, high)
    along = {"how": "wall", "span": [[0.0, 0.0], [10.0, 0.0]], "out": [0.0, 1.0], "why": "against its wall"}
    hung = fitting.fitted(flat, TOY, [*[{"name": name, "row": name[:-2], "on": along}
                                        for name in ("box_1", "conduit_1", "lamp_1", "pipes_2")],
                                      {"name": "stair_railing_1", "row": "stair_railing"}],
                          {"box_1", "conduit_1", "lamp_1", "pipes_2", "stair_railing_1"})
    boxes = {name: fitting.world_box(flat, f"/{TOY}/Objects/{name}") for name in ("box_1", "conduit_1", "lamp_1",
                                                                                   "pipes_2")}
    assert np.allclose(boxes["lamp_1"], ((5.0, 2.34, 0.0), (5.2, 2.99, 0.15)), atol=1e-6), boxes
    assert np.allclose(boxes["conduit_1"][1][1], 2.99) and np.allclose(boxes["conduit_1"][0][[1, 2]], 0.0), boxes
    assert np.allclose(boxes["pipes_2"][1][1], 4.0), boxes  # 75%: left
    assert boxes["box_1"][0][0] >= 2.1 - 1e-6, boxes  # clear of the railing at x 2.0 to 2.1
    words = {fit["name"]: fit["words"] for fit in hung}
    assert "moved 0.16 m down under roof_1" in words["lamp_1"] and "shrunk to 96% under roof_1" in \
        words["conduit_1"], words
    # tube (2026-11-12): its vault springs from its walls' faces at the floor and bulges out behind them, so over a
    # spot just behind a wall's face it has a foot a few centimetres up and its arc over it. A screen 1 to 2 m up on
    # the x 10 wall, its back on the face, is under the arc and through no roof (fitting.moved_in had stood each 5 cm
    # off its wall, touching nothing); a panel up to 3.3 m still reaches 0.3 m over the arc's 3 m, and a crate 1 to
    # 1.5 m up out through a steep side, which stands 0.2 m up over its outer edge, 1.3 m.
    bulged = Usd.Stage.CreateInMemory()
    UsdGeom.Xform.Define(bulged, f"/{TOY}/Structure/roof_1")
    belly = UsdGeom.Mesh.Define(bulged, f"/{TOY}/Structure/roof_1/geo")
    belly.CreatePointsAttr([(9.9, 0, 0), (10.5, 1.5, 0), (10, 3, 0), (5, 5, 0),
                            (9.9, 0, 10), (10.5, 1.5, 10), (10, 3, 10), (5, 5, 10)])
    belly.CreateFaceVertexCountsAttr([4, 4, 4])
    belly.CreateFaceVertexIndicesAttr([0, 1, 5, 4, 1, 2, 6, 5, 2, 3, 7, 6])
    a_built_box(bulged, f"/{TOY}/Objects/screen_2", (9.8, 1.0, 4.0), (10.0, 2.0, 5.0))
    a_built_box(bulged, f"/{TOY}/Objects/panel_2", (9.8, 2.5, 6.0), (10.0, 3.3, 7.0))
    UsdGeom.Xform.Define(bulged, f"/{TOY}/Structure/roof_2")  # a steep side running down past a crate's foot
    steep = UsdGeom.Mesh.Define(bulged, f"/{TOY}/Structure/roof_2/geo")
    steep.CreatePointsAttr([(0, 4, 20), (2, 0, 20), (2, 0, 22), (0, 4, 22)])
    steep.CreateFaceVertexCountsAttr([4])
    steep.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    a_built_box(bulged, f"/{TOY}/Objects/crate_2", (0.5, 1.0, 20.5), (1.9, 1.5, 21.5))
    through = fitting.through_roofs(bulged, TOY, ["screen_2", "panel_2", "crate_2"])
    assert [(found["name"], found["metres"]) for found in through] == [("panel_2", 0.3), ("crate_2", 1.3)], through
    # tube (2026-11-12): its ribs are arches (a structure row, `score:row`) standing in front of its walls' faces.
    # Here one 1.4 to 1.6 m round the floor's middle line, z 2 to 2.2, in front of the x -1.6 wall from 0.3 m up. A
    # 0.8 m screen 0.6 to 1 m up across it slides along clear of it (to z 2.2); 8 m pipes 0.2 to 0.5 m up, which no
    # stretch of the 10 m wall holds whole beside it, stand on its front at their top, 0.29 m out (a round pipe on the
    # x 1.6 wall by its own surface where it crosses the rib, touching it, never by its bracket's back elsewhere nor
    # on a second rib at z 9.5 it does not reach); a light hung 0.05 m
    # up in its 1.4 m underside is let down 0.06 m; a lamp laid within its box inside its leg is drawn out to its face.
    from score.stages.assembly import ribs
    ribbed = Usd.Stage.CreateInMemory()
    turns = np.linspace(0.0, np.pi, 33)
    quads = []
    for step in range(32):
        corner = lambda depth, radius, turn: (depth * 2 + radius) * 33 + turn  # noqa: E731
        quads += [(corner(0, 0, step), corner(0, 0, step + 1), corner(1, 0, step + 1), corner(1, 0, step)),
                  (corner(0, 1, step), corner(1, 1, step), corner(1, 1, step + 1), corner(0, 1, step + 1)),
                  (corner(0, 0, step), corner(0, 1, step), corner(0, 1, step + 1), corner(0, 0, step + 1)),
                  (corner(1, 0, step), corner(1, 0, step + 1), corner(1, 1, step + 1), corner(1, 1, step))]
    for number, near in ((1, 2.0), (2, 9.5)):  # the second past the pipes' ends, which they do not cross
        ring = [(-np.cos(turn) * radius, np.sin(turn) * radius, depth) for depth in (near, near + 0.2)
                for radius in (1.4, 1.6) for turn in turns]  # [depth][radius][turn]
        UsdGeom.Xform.Define(ribbed, f"/{TOY}/Structure/ribs_{number}").GetPrim().CreateAttribute(
            "score:row", Sdf.ValueTypeNames.String).Set("ribs")
        arch = UsdGeom.Mesh.Define(ribbed, f"/{TOY}/Structure/ribs_{number}/geo")
        arch.CreatePointsAttr([tuple(map(float, point)) for point in ring])
        arch.CreateFaceVertexCountsAttr([4] * len(quads))
        arch.CreateFaceVertexIndicesAttr([int(index) for quad in quads for index in quad])
    UsdGeom.Xform.Define(ribbed, f"/{TOY}/Structure/wall_1")
    side = trimesh.creation.box(bounds=((-1.75, 0.0, 0.0), (-1.6, 3.0, 10.0)))
    built = UsdGeom.Mesh.Define(ribbed, f"/{TOY}/Structure/wall_1/geo")
    built.CreatePointsAttr([tuple(map(float, point)) for point in side.vertices])
    built.CreateFaceVertexCountsAttr([3] * len(side.faces))
    built.CreateFaceVertexIndicesAttr([int(index) for index in side.faces.reshape(-1)])
    UsdGeom.Xform.Define(ribbed, f"/{TOY}/Structure/wall_2")
    side = trimesh.creation.box(bounds=((1.6, 0.0, 0.0), (1.75, 3.0, 10.0)))
    built = UsdGeom.Mesh.Define(ribbed, f"/{TOY}/Structure/wall_2/geo")
    built.CreatePointsAttr([tuple(map(float, point)) for point in side.vertices])
    built.CreateFaceVertexCountsAttr([3] * len(side.faces))
    built.CreateFaceVertexIndicesAttr([int(index) for index in side.faces.reshape(-1)])
    round_pipe = trimesh.creation.cylinder(radius=0.15, height=8.0, sections=48)  # along z
    round_pipe.apply_translation((1.45, 0.35, 5.0))
    round_pipe = trimesh.util.concatenate([round_pipe, trimesh.creation.box(bounds=((1.45, 0.2, 5.0),
                                                                                   (1.6, 0.5, 5.1)))])  # a bracket
    UsdGeom.Xform.Define(ribbed, f"/{TOY}/Objects/pipes_4").AddTransformOp().Set(Gf.Matrix4d(1.0))
    drawn = UsdGeom.Mesh.Define(ribbed, f"/{TOY}/Objects/pipes_4/geo")
    drawn.CreatePointsAttr([tuple(map(float, point)) for point in round_pipe.vertices])
    drawn.CreateFaceVertexCountsAttr([3] * len(round_pipe.faces))
    drawn.CreateFaceVertexIndicesAttr([int(index) for index in round_pipe.faces.reshape(-1)])
    for name, low, high in (("screen_3", (-1.6, 0.6, 1.8), (-1.4, 1.0, 2.6)), ("pipes_3", (-1.6, 0.2, 1.0),
                                                                                 (-1.4, 0.5, 9.0)),
                            ("light_3", (-0.1, 1.35, 1.5), (0.1, 1.45, 2.5)),
                            ("lamp_3", (-1.55, 0.9, 2.05), (-1.45, 1.0, 2.15))):
        a_built_box(ribbed, f"/{TOY}/Objects/{name}", low, high)
    left = {"how": "wall", "span": [[-1.6, 10.0], [-1.6, 0.0]], "out": [1.0, 0.0], "why": "against its wall"}
    right = {"how": "wall", "span": [[1.6, 0.0], [1.6, 10.0]], "out": [-1.0, 0.0], "why": "against its wall"}
    fits = fitting.fitted(ribbed, TOY, [{"name": "screen_3", "row": "screen", "on": left},
                                        {"name": "pipes_3", "row": "pipes", "on": left},
                                        {"name": "pipes_4", "row": "pipes", "on": right},
                                        {"name": "light_3", "row": "light", "under roof": True},
                                        {"name": "lamp_3", "row": "lamp", "on": {
                                            "how": "within", "holder": ["ribs_1"], "holder scope": "Structure"}}],
                          {"screen_3", "pipes_3", "pipes_4", "light_3", "lamp_3"})
    boxes = {name: fitting.world_box(ribbed, f"/{TOY}/Objects/{name}") for name in ("screen_3", "pipes_3", "light_3",
                                                                                    "lamp_3")}
    assert np.isclose(boxes["screen_3"][0][2], 2.2, atol=1e-3) and np.isclose(boxes["screen_3"][0][0], -1.6), boxes
    assert np.isclose(boxes["pipes_3"][0][0], -1.6 + 1.6 - np.sqrt(1.4 ** 2 - 0.5 ** 2), atol=0.01) and \
        np.isclose(boxes["pipes_3"][1][2] - boxes["pipes_3"][0][2], 8.0), boxes
    assert np.isclose(boxes["light_3"][1][1], 1.39, atol=0.005) and np.isclose(boxes["lamp_3"][0][0], -0.979,
                                                                                atol=0.01), boxes
    assert {fit["name"]: fit["how"] for fit in fits if fit["name"] in ("light_3", "lamp_3")} == {
        "light_3": "down", "lamp_3": "within"}, fits
    assert ribs.kept_off(ribbed, TOY, [{"name": "light_3", "row": "light", "under roof": True}], []) == []
    _, gaps, _ = trimesh.proximity.closest_point(fitting.surface_mesh(ribbed, f"/{TOY}/Structure/ribs_1"),
                                                 trimesh.sample.sample_surface(fitting.surface_mesh(
                                                     ribbed, f"/{TOY}/Objects/pipes_4"), 20000, seed=0)[0])
    assert gaps.min() <= 0.01, gaps.min()  # the round pipe touches the rib, not its box's corner
    # tube's window holes, 2 m wide in its left wall, open onto its vault 0.42 m behind: read on the walls alone a
    # hole from z 4 to 6 (to the rays a step past its edges, 3.975 and 6.025) stands in a wall with the vault 0.4 m
    # behind it; a vault that is its own wall (no wall piece on the face) has no hole.
    from score.stages.assembly import vault_feet, wall_clear
    holed = Usd.Stage.CreateInMemory()
    for name, bounds in (("wall_1", ((-1.75, 0.0, 0.0), (-1.6, 3.0, 4.0))), ("wall_1_2", ((-1.75, 0.0, 6.0),
                                                                                          (-1.6, 3.0, 10.0)))):
        piece = trimesh.creation.box(bounds=bounds)
        UsdGeom.Xform.Define(holed, f"/{TOY}/Structure/{name}")
        drawn = UsdGeom.Mesh.Define(holed, f"/{TOY}/Structure/{name}/geo")
        drawn.CreatePointsAttr([tuple(map(float, point)) for point in piece.vertices])
        drawn.CreateFaceVertexCountsAttr([3] * len(piece.faces))
        drawn.CreateFaceVertexIndicesAttr([int(index) for index in piece.faces.reshape(-1)])
    UsdGeom.Xform.Define(holed, f"/{TOY}/Structure/roof_1")
    behind = UsdGeom.Mesh.Define(holed, f"/{TOY}/Structure/roof_1/geo")
    behind.CreatePointsAttr([(-2.0, 0.0, 0.0), (-2.0, 3.0, 0.0), (-2.0, 3.0, 10.0), (-2.0, 0.0, 10.0)])
    behind.CreateFaceVertexCountsAttr([4])
    behind.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    face = {"how": "wall", "span": [[-1.6, 0.0], [-1.6, 10.0]], "out": [1.0, 0.0]}
    everything, bare = fitting.built_walls(holed, TOY), wall_clear.face_walls(holed, TOY)
    assert fitting.wall_holes(everything, face, (1.0, 1.5)) == []
    [hole] = vault_feet.wall_holes(everything, bare, face, (1.0, 1.5))
    assert np.isclose(hole[:, 2].min(), 3.975) and np.isclose(hole[:, 2].max(), 6.025), hole
    holed.RemovePrim(f"/{TOY}/Structure/wall_1")
    holed.RemovePrim(f"/{TOY}/Structure/wall_1_2")
    assert vault_feet.wall_holes(fitting.built_walls(holed, TOY), wall_clear.face_walls(holed, TOY), face,
                                 (1.0, 1.5)) == []


def test_a_leaf_hangs_on_the_face_it_swings_to_and_a_wall_s_things_keep_out_of_its_swing():
    """#36, garage 2026-10-30: hung on its wall's room face, each door swung out, its kind's way, into its own jamb
    0.05 to 0.08 m, and 10 m pipes laid along the walls stood across both doorways; neither door swung. A 2 m door in
    the 2.4 m opening of a wall from z -0.276 to 0 (the room to +z) whose own -z way (its kind's swing) points out of
    the room hangs on the wall's outer face, z -0.276, its hinge at that face's jamb corner; one swinging into the room
    on the room face, z 0, never on the floor deck's side under it; the held gate passes it on either face. A
    1 x 2 x 0.1 m door in its 1.2 m opening, in a shell wall from z -0.1 to 0.1 (quarters' walls are its Shell), turned so its own left edge faces +x and its own -z the room, stands on the wall's room
    face, x -0.4 to 0.6, z 0.05 to 0.15; its swing takes z 0.1 to 1.1 over that span. A 3.2 m pipe laid on the wall
    across the doorway goes to the longest stretch beside its passage (the 1.2 m opening's), shrunk to 2.4 m, x -3 to
    -0.6, though it comes first in
    the record; a lamp on the wall above the door stays; a pipe beside a door swinging out of the room stays. Only a
    door, hatch or gate swings so (its row kind's motion): a window stands in its opening and claims no swing (tube's
    wall panel, moved 5.4 m clear of a window, 2026-10-30).
    Break: score/stages/assembly/fitting.py: `return bool(set(row_kinds.words(row).split()) & nouns)` -> `return
        True`
    Break: score/stages/assembly/fitting.py: `faces = [float(high[axis] if opens > 0 else low[axis]) for low, high in
        reach` -> `faces = [float(low[axis] if opens > 0 else high[axis]) for low, high in reach`
    Break: score/stages/assembly/fitting.py: `and high[axis] - low[axis] <= 2 * WALL_REACH]` -> `]`
    Break: score/stages/assembly/fitting.py: `for scope in ("Structure", "Shell")]` -> `for scope in ("Structure",)]`
    Break: score/stages/assembly/fitting.py: `own_way(stage, path, 0), own_way(stage, path, 2) if name in leaves else
        None, clear)` -> `own_way(stage, path, 0), None, clear)`
    Break: score/stages/assembly/fitting.py: `for opens in (None, across_it, np.negative(across_it))]` -> `for opens
        in (None,)]`
    Break: score/stages/assembly/fitting.py: `if off.max() > 0.0 and off.min() < deep and low[1] < band[1] and
        high[1] > band[0]:` -> `if off.max() > 0.0 and off.min() < deep:`
    Break: score/stages/assembly/fitting.py: `(middle, middle + wide) if way[axis // 2] > 0 else (middle - wide,
        middle)` -> `(middle - wide, middle) if way[axis // 2] > 0 else (middle, middle + wide)`
    Break: score/stages/assembly/fitting.py: `for name in sorted(by_name, key=lambda name: name not in leaves):` ->
        `for name in by_name:`
    Break: score/stages/assembly/fitting.py: fitted's `others = [box for other, box in mounted.items() ...]` -> `others
        = []` (lamp_2 left in lamp_1), or on_wall's `[*clear, *mounted]` -> `clear` (the cabinet left in the corner)
    Break: score/stages/assembly/fitting.py: on_wall's `start = start + out * stood_off(...)` dropped (the pipe through
        hangar's rib), or stood_off's `0.0 < off.max() <= STAND_OFF_MOST` -> `0.0 < off.max()` (stood on the deck's
        far side), or its `along.min() < reach[1]` dropped (stood on the rib past its reach)
    Break: score/stages/assembly/fitting.py: mounted_height's `return next((at for at in lower ...), height)` ->
        `return height` (the pipe shrunk beside the one over it), or its `wanted = min(reach, longest(height, clear))`
        -> `wanted = reach` (the pipe longer than its wall left in the one over it)
    Break: score/stages/assembly/fitting.py: on_wall's `reach, deep = float(np.ptp(floor @ run)), float(np.ptp(floor @
        out))` -> `reach, deep = across(run, size), across(out, size)` (the turned pipe 1.1 m off its slanted wall), or
        oriented_corners' `return box @ own[:3, :3] + own[3, :3]` -> its world box's corners
    Break: score/stages/assembly/fitting.py: on_built_face's `faces.append(origins[ray][[0, 2]] + back[[0, 2]] *
        float(reach.min()))` -> `faces.append(ends[ray])` (the span left 3 cm in front of its wall), or its `reach <= 2
        * WALL_REACH` dropped (the span pulled 3 m back onto a far wall), or its `normal = normal if normal @ out >=
        0.0 else -normal` -> `pass` with the turned face's normal flipped (out into the wall), or slanted_wall's `> 1e-6`
        -> `> 0.15` (workshop's tools on a span 7.5 degrees off x left 4 cm in their wall), or its `share in
        (FACE_INSET, 1.0 - FACE_INSET)` -> `share in (0.0, 1.0)` (a span ending past its wall's corner turned onto
        the wall behind, habitat's wall_9), or its `return face_near(on, height, mesh)` -> `return on, 0.0`
        (greenhouse's lamp left on its arc's chord, its pipe on the arc's outer face), or along_its_wall's `if deep <=
        STRAIGHT_LEAST * max(reach, 1e-9):` -> `if True:` (its pipe left sticking out of its wall)
    Break: score/stages/assembly/fitting.py: stood_off's `0.0 < float(along.min() + along.max()) / 2 < length`
        dropped (walkway's whole-wall pipe stood on its end walls' front, against the wall across), or off_wall's
        `if corners is not None:` -> `if False:` (hub's turned pipe off its slanted wall by its world box), or held_faults' `on = dict(on, **{key: walled[...]...})` dropped (a pipe stood on its
        rib's front named off its wall)
    Break: score/stages/assembly/fitting.py: fit's `if scale < SCALE_LEAST: return CROWDED` dropped (a wall thing with
        no stretch left shrunk to nothing), or oriented_corners' `or abs(float(np.linalg.det(own[:3, :3]))) < 1e-12`
        dropped (a prim scaled flat: LinAlgError, Singular matrix)
    Break: score/stages/assembly/wall_clear.py: face_walls' `if not name.startswith(fitting.ROOF)` -> `if True`
        (habitat's pipe over its wall's top laid on its dome's rim, 0.3 m behind its wall's face), or fitting.py's
        `on_built_face(entry["on"], (low[1] + high[1]) / 2, faced())` -> `..., faces())`"""
    from pxr import Gf, Usd, UsdGeom
    from score.stages.assembly import wall_clear
    from score.stages.assembly import fitting
    walls = [{"name": "wall_1", "low": [-5.0, -0.2, -0.276], "high": [-1.2, 4.6, 0.0]},
             {"name": "wall_1_2", "low": [-1.2, -0.2, -0.276], "high": [1.2, 0.0, 0.0]},
             {"name": "deck_1", "low": [-5.0, -0.2, -0.2], "high": [5.0, 0.0, 5.0]}]  # no wall: across the room
    opening = {"how": "in", "middle": [0.0, 0.0, 0.15], "along": [1.0, 0.0], "wide": 2.4, "tall": 2.66}
    boxes = [(wall["low"], wall["high"]) for wall in walls]
    for opens, face in (((0.0, -1.0), -0.276), ((0.0, 1.0), 0.0)):
        _, target, _, _ = fitting.fit((-1.0, 0.0, 0.05), (1.0, 2.4, 0.25), opening, boxes, left=(-1.0, 0.0),
                                      opens=opens)
        assert np.allclose(target, (-0.2, 0.0, face)), (opens, target)
        record = {"objects": [{"name": "door_1", "on": opening, "fills": True}]}
        assert fitting.held_faults(record, {"walls": walls, "objects": [
            {"name": "door_1", "low": [-1.2, 0.0, face - 0.1], "high": [0.8, 2.4, face + 0.1]}]}) == [], face
    stage = Usd.Stage.CreateInMemory()
    for name, size, turn, at in (("Objects/pipe_1", (3.2, 1.0, 0.32), 0.0, (0.0, 0.5, 2.0)),
                                 ("Objects/lamp_1", (0.4, 0.3, 0.1), 0.0, (0.0, 2.45, 0.15)),
                                 ("Objects/lamp_2", (0.4, 0.3, 0.1), 0.0, (0.1, 2.45, 0.15)),
                                 ("Objects/door_1", (1.0, 2.0, 0.1), 180.0, (0.0, 1.0, 3.0)),
                                 ("Shell/wall_2", (1.2, 0.1, 0.2), 0.0, (0.0, -0.05, 0.0))):
        xform = UsdGeom.Xform.Define(stage, f"/{TOY}/{name}")
        cube = UsdGeom.Cube.Define(stage, f"/{TOY}/{name}/geo")
        cube.AddScaleOp().Set(Gf.Vec3f(*(side / 2 for side in size)))
        xform.AddTransformOp().Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), turn))
                                   * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*at)))
    wall = {"how": "wall", "span": [[-3.0, 0.1], [3.0, 0.1]], "out": [0.0, 1.0]}
    entries = [{"name": "pipe_1", "row": "pipe", "on": wall}, {"name": "lamp_1", "row": "lamp", "on": wall},
               {"name": "lamp_2", "row": "lamp", "on": wall},
               {"name": "door_1", "row": "door", "on": {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [1.0, 0.0],
                                                          "wide": 1.2, "tall": 2.2}}]
    fits = {fit["name"]: fit for fit in fitting.fitted(stage, TOY, entries, {"pipe_1", "lamp_1", "lamp_2", "door_1"})}
    assert sorted(fits) == ["door_1", "lamp_2", "pipe_1"], fits
    assert np.allclose(fits["lamp_2"]["low"], (0.2, 2.3, 0.1)), fits  # slid along clear of lamp_1, laid before it
    assert np.allclose(fits["door_1"]["low"], (-0.4, 0.0, 0.05)) and np.allclose(fits["door_1"]["high"],
                                                                                  (0.6, 2.0, 0.15)), fits
    swing = fitting.swing_box(stage, f"/{TOY}/Objects/door_1")
    assert np.allclose(swing[0], (-0.4, 0.0, 0.1)) and np.allclose(swing[1], (0.6, 2.0, 1.1)), swing
    assert fits["pipe_1"]["scale"] == 0.75 and np.allclose(fits["pipe_1"]["low"], (-3.0, 0.0, 0.1)) \
        and np.allclose(fits["pipe_1"]["high"], (-0.6, 0.75, 0.34)), fits
    assert fitting.swings("round_door_left") and fitting.swings("metal_gate_open") and not fitting.swings("windows")
    out = (np.array([-0.4, 0.0, -0.9]), np.array([0.6, 2.0, 0.1]))
    scale, target = fitting.on_wall(np.array([-1.6, 0.0, 1.0]), np.array([1.6, 1.0, 1.32]), wall, [out])
    assert scale == 1.0 and np.allclose(target, (0.0, 0.0, 0.26)), (scale, target)
    # habitat (settle@habitat, 2026-11-10): two 3 m pipes 0.45 m tall stood 0.25 m apart on one wall, and kitchen
    # cabinets on meeting walls, crossed by their own depth. A 4 m pipe 0.45 m tall laid at 2.35 m over one laid at
    # 2.6 m on the same 6 m wall has no whole stretch at its height: it stands MOUNT_GAP under it, at 2.1 m; with
    # nothing laid before it, it stays. A 1 m cabinet laid into the corner where one on the meeting wall (x -3 to
    # -2.6) stands slides along clear of it, x -2.6 to -1.6.
    pipe = (np.array([-2.0, 2.35, 0.1]), np.array([2.0, 2.8, 0.3]))
    laid = [(np.array([-2.0, 2.6, 0.1]), np.array([2.0, 3.05, 0.3]))]
    scale, target = fitting.on_wall(*pipe, wall, (), laid)
    assert scale == 1.0 and np.allclose(target, (0.0, 2.1, 0.2)), (scale, target)
    scale, target = fitting.on_wall(*pipe, wall)
    assert scale == 1.0 and np.allclose(target, (0.0, 2.35, 0.2)), (scale, target)
    # hangar (2026-11-11): its 32 m pipes ran through the ribs standing 1.5 m out of its walls. A rib standing 0.9 m
    # out of the face across the pipe's reach stands it on the rib's front; one past its reach, and a deck across the
    # room, do not
    rib, past = (np.array([1.0, 0.0, 0.0]), np.array([1.3, 5.0, 1.0])), (np.array([2.5, 0.0, 0.0]), np.array([2.8, 5.0,
                                                                                                             2.0]))
    deck = (np.array([-3.0, 2.0, 0.0]), np.array([3.0, 2.5, 10.0]))
    scale, target = fitting.on_wall(*pipe, wall, built=[rib, past, deck])
    assert scale == 1.0 and np.allclose(target, (0.0, 2.35, 1.1)), (scale, target)
    # walkway (2026-11-11): a pipe along its whole wall was stood on the 1.5 m front of the walls meeting it at its
    # ends, onto the wall across; the walls at the face's ends are no ribs, and the held gate measures a stood pipe
    # off the rib's front it was laid on (stood_face), by its own turned box (laid_face)
    ends = [(np.array([-3.13, 0.0, 0.1]), np.array([-3.0, 2.5, 1.6])), (np.array([3.0, 0.0, 0.1]),
                                                                        np.array([3.13, 2.5, 1.6]))]
    whole = (np.array([-3.05, 2.35, 0.1]), np.array([3.05, 2.8, 0.3]))
    scale, target = fitting.on_wall(*whole, wall, built=ends)
    assert abs(scale - 6 / 6.1) < 1e-9 and np.allclose(target, (0.0, 2.35, 0.1 + 0.1 * 6 / 6.1)), (scale, target)
    stood = fitting.stood_face(*pipe, wall, None, [rib])
    assert np.allclose(stood["span"], [[-3.0, 1.0], [3.0, 1.0]]) and fitting.stood_face(*whole, wall, None, ends) \
        is wall, stood
    floor = [[x, z] for x in (-2.0, 2.0) for z in (1.0, 1.2)]
    laid_on = {"objects": [{"name": "pipe_1", "low": [-2.0, 2.35, 1.0], "high": [2.0, 2.8, 1.2]}],
               "fitted": [{"name": "pipe_1", "how": "wall",
                           **fitting.laid_face(stood, [[x, 2.35, z] for x, z in floor])}]}
    assert fitting.held_faults({"objects": [{"name": "pipe_1", "on": wall}]}, laid_on) == []
    assert fitting.held_faults({"objects": [{"name": "pipe_1", "on": wall}]}, dict(laid_on, fitted=[])) == [
        ("pipe_1", "0.90 m off where it is laid wall ()", 0.9)]
    # hub (2026-11-11): a 0.4 m deep pipe turned 45 degrees flush on its slanted wall stands off it by its world box,
    # never by its own turned box's corners
    slanted = {"how": "wall", "span": [[0.0, 0.0], [4.0, 4.0]], "out": [0.7071068, -0.7071068]}
    turned_floor = [[2.0 + along * 0.7071068 + off * 0.7071068, 2.0 + along * 0.7071068 - off * 0.7071068]
                    for along in (-1.5, 1.5) for off in (0.0, 0.4)]
    xs, zs = [x for x, _ in turned_floor], [z for _, z in turned_floor]
    low, high = np.array([min(xs), 0.0, min(zs)]), np.array([max(xs), 0.5, max(zs)])
    assert fitting.off_wall(low, high, slanted, turned_floor) < 1e-6 < fitting.off_wall(low, high, slanted) - 0.1
    # hangar's 32 m pipes on its 31.3 m walls: one longer than its wall stands under the one laid before it too
    long_pipe = (np.array([-3.5, 2.35, 0.1]), np.array([3.5, 2.8, 0.3]))
    scale, target = fitting.on_wall(*long_pipe, wall, (), [(np.array([-3.0, 2.6, 0.1]), np.array([3.0, 3.05, 0.3]))])
    assert abs(scale - 6 / 7) < 1e-9 and np.allclose(target, (0.0, 2.1, 0.1 + 0.1 * 6 / 7)), (scale, target)
    # habitat's 3 m pipes on its 45 degree walls were laid 1.5 m off them, as deep as their world box: a 3 x 0.45 x
    # 0.2 m pipe turned along a slanted wall (its face from (0, 0) to (4, 4), out to +x -z) stands with its own box's
    # back on the face, its middle 0.1 m out; its turned corners read off the stage (oriented_corners)
    slant = {"how": "wall", "span": [[0.0, 0.0], [4.0, 4.0]], "out": [0.7071068, -0.7071068]}
    turned = Usd.Stage.CreateInMemory()
    xform = UsdGeom.Xform.Define(turned, f"/{TOY}/Objects/pipe_9")
    UsdGeom.Cube.Define(turned, f"/{TOY}/Objects/pipe_9/geo").AddScaleOp().Set(Gf.Vec3f(1.5, 0.225, 0.1))
    xform.AddTransformOp().Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), -45.0))
                               * Gf.Matrix4d().SetTranslate(Gf.Vec3d(2.0, 2.0, 2.0)))
    corners = fitting.oriented_corners(turned, f"/{TOY}/Objects/pipe_9")
    low, high = fitting.world_box(turned, f"/{TOY}/Objects/pipe_9")
    scale, target = fitting.on_wall(low, high, slant, (), (), corners)
    assert scale == 1.0 and np.allclose(target, (2.0 + 0.1 * 0.7071068, low[1], 2.0 - 0.1 * 0.7071068)), target
    # workshop's slanted walls were built 3 cm behind and 6.5 degrees turned from their things' spans: the span is
    # put on the built face (a wall face 3 cm behind the slanted span: no turn; one turned 6.5 degrees about the
    # span's middle: its ends on it, its out the face's, turned 6.5 degrees), and kept where the wall stands 3 m behind
    # it, past reach
    behind = np.array([0.7071068, -0.7071068]) * -0.03
    face = trimesh.Trimesh([[-1.0 + behind[0], 0.0, -1.0 + behind[1]], [5.0 + behind[0], 0.0, 5.0 + behind[1]],
                            [5.0 + behind[0], 3.0, 5.0 + behind[1]], [-1.0 + behind[0], 3.0, -1.0 + behind[1]]],
                           [[0, 1, 2], [0, 2, 3]], process=False)
    moved, degrees = fitting.on_built_face(slant, 1.5, face)
    assert np.allclose(moved["span"], np.add(slant["span"], behind), atol=1e-6) and abs(degrees) < 1e-6, moved
    turn = trimesh.transformations.rotation_matrix(np.radians(6.5), [0.0, 1.0, 0.0], [2.0 + behind[0], 0.0,
                                                                                    2.0 + behind[1]])
    moved, degrees = fitting.on_built_face(slant, 1.5, face.copy().apply_transform(turn))
    run = np.subtract(*moved["span"][::-1]) / np.linalg.norm(np.subtract(*moved["span"][::-1]))
    assert abs(abs(degrees) - 6.5) < 1e-3 and abs(float(run @ moved["out"])) < 1e-6 and float(
        np.dot(moved["out"], slant["out"])) > 0.99, (moved, degrees)
    assert fitting.on_built_face(slant, 1.5, face.copy().apply_translation((-2.1213, 0.0, 2.1213))) == (slant, 0.0)
    # habitat's wall_9 (2026-11-11): its span ends 5 mm past its wall's corner, a wall 0.2 m behind: the face found
    # is its own wall's, not turned onto the one behind
    deep = np.array([0.7071068, -0.7071068]) * -0.2
    corner = trimesh.util.concatenate([trimesh.Trimesh(
        [[start + way[0], 0.0, start + way[1]], [5.0 + way[0], 0.0, 5.0 + way[1]], [5.0 + way[0], 3.0, 5.0 + way[1]],
         [start + way[0], 3.0, start + way[1]]], [[0, 1, 2], [0, 2, 3]], process=False)
        for start, way in ((0.0035, (0.0, 0.0)), (-1.0, deep))])
    moved, degrees = fitting.on_built_face(slant, 1.5, corner)
    assert np.allclose(moved["span"], slant["span"], atol=1e-6) and abs(degrees) < 1e-6, (moved, degrees)
    # greenhouse (2026-11-11): its plan walls an arc, its shell built on its outline's octagon 0.3 to 1.2 m behind the
    # arc's chords. A face 1.2 m behind the span's middle, turned 20 degrees, is past the face rays' reach: the span is
    # laid on it, along its run (10 m long here), its out the face's, turned 20 degrees; a face 0.7 m in front of a
    # span whose out points at it (a pipe on the arc's outer face) takes the span, its out turned round to the room
    middle, way = np.array([2.0, 2.0]), np.array([0.7071068, -0.7071068])

    def a_face(at, turn):
        run = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]]) @ np.array([way[1], -way[0]])
        ends = [at + run * 5.0, at - run * 5.0]
        return trimesh.Trimesh([[ends[0][0], 0.0, ends[0][1]], [ends[1][0], 0.0, ends[1][1]],
                                [ends[1][0], 3.0, ends[1][1]], [ends[0][0], 3.0, ends[0][1]]], [[0, 1, 2], [0, 2, 3]],
                               process=False), run

    for at, turn, toward in ((middle - way * 1.2, np.radians(20.0), 1.0), (middle + way * 0.7, 0.0, -1.0)):
        built, run = a_face(at, turn)
        moved, degrees = fitting.on_built_face(slant, 1.5, built)
        ends = np.asarray(moved["span"], float)
        assert np.allclose((ends - at) @ np.array([-run[1], run[0]]), 0.0, atol=1e-6), moved  # on the face
        assert abs(float(np.dot(moved["out"], run))) < 1e-6 and float(np.dot(moved["out"], way)) * toward > 0.9, moved
        assert np.linalg.norm(ends[1] - ends[0]) > 9.0 and abs(abs(degrees) - (20.0 if toward > 0 else 180.0)) < 1e-3, (
            moved, degrees)
    # ... and its 3 m pipes, built lying, stood 3 m out of their wall: one long across its wall is turned along it
    UsdGeom.Xform.Define(turned, f"/{TOY}/Objects/pipe_10").AddTransformOp().Set(
        Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), -45.0)))
    UsdGeom.Cube.Define(turned, f"/{TOY}/Objects/pipe_10/geo").AddScaleOp().Set(Gf.Vec3f(1.5, 0.1, 0.1))
    across_it = {"how": "wall", "span": [[0.0, 0.0], [4.0, -4.0]], "out": [0.7071068, 0.7071068]}
    assert not fitting.along_its_wall(turned, f"/{TOY}/Objects/pipe_10", slant)
    assert fitting.along_its_wall(turned, f"/{TOY}/Objects/pipe_10", across_it)
    assert not fitting.along_its_wall(turned, f"/{TOY}/Objects/pipe_10", across_it)  # along it now
    # habitat's pipes (2026-11-11), 2.6 m up and 0.44 m tall on walls 2.8 m tall, cast their face rays over the walls'
    # tops onto the dome's rim 0.3 m behind: a roof is no face. Under its wall's top the face is found as before.
    domed = Usd.Stage.CreateInMemory()
    rim = trimesh.Trimesh([[point[0] - 0.3 * 0.7071068, height, point[2] + 0.3 * 0.7071068]
                           for point in face.vertices[:2] for height in (2.8, 3.5)], [[0, 1, 3], [0, 3, 2]],
                          process=False)
    for name, mesh in (("wall_1", face.copy().apply_transform(np.diag([1.0, 2.8 / 3.0, 1.0, 1.0]))), ("roof_1", rim)):
        UsdGeom.Xform.Define(domed, f"/{TOY}/Structure/{name}")
        drawn = UsdGeom.Mesh.Define(domed, f"/{TOY}/Structure/{name}/geo")
        drawn.CreatePointsAttr([tuple(map(float, point)) for point in mesh.vertices])
        drawn.CreateFaceVertexCountsAttr([3] * len(mesh.faces))
        drawn.CreateFaceVertexIndicesAttr([int(index) for index in mesh.faces.reshape(-1)])
    moved, _ = fitting.on_built_face(slant, 2.9, fitting.built_walls(domed, TOY))
    assert np.allclose(moved["span"], np.add(slant["span"], behind + [-0.3 * 0.7071068, 0.3 * 0.7071068]),
                       atol=1e-3), moved  # the rim, as it was found before
    assert fitting.on_built_face(slant, 2.9, wall_clear.face_walls(domed, TOY)) == (slant, 0.0)
    moved, _ = fitting.on_built_face(slant, 1.5, wall_clear.face_walls(domed, TOY))
    assert np.allclose(moved["span"], np.add(slant["span"], behind), atol=1e-6), moved
    a_built_box(domed, f"/{TOY}/Objects/pipe_1", (1.9, 2.7, 1.9), (2.1, 3.1, 2.1))
    fitting.fitted(domed, TOY, [{"name": "pipe_1", "row": "pipe", "on": slant}], {"pipe_1"})
    foot = fitting.foot_middle(*fitting.world_box(domed, f"/{TOY}/Objects/pipe_1"))
    assert float((foot[[0, 2]] - slant["span"][0]) @ slant["out"]) > 0.0, foot  # in front of its wall, not the rim
    assert fitting.slanted_wall(slant) and fitting.slanted_wall({"out": [0.991393, -0.13092]}) and not \
        fitting.slanted_wall(wall)
    corner = [(np.array([-3.0, 1.5, 0.1]), np.array([-2.6, 2.2, 1.1]))]
    scale, target = fitting.on_wall(np.array([-3.0, 1.5, 0.1]), np.array([-2.0, 2.2, 0.5]), wall, (), corner)
    assert scale == 1.0 and np.allclose(target, (-2.1, 1.5, 0.3)), (scale, target)
    # habitat's third kitchen cabinet (2026-11-11): its wall taken, floor to top, by those laid before it but for a
    # stretch of no length at its end ((2.9064, 2.9064)), it was shrunk to 0% and its flat frame broke
    # oriented_corners' inverse. With no stretch of its wall left it is CROWDED (left as laid); with the wall free it
    # is laid; a prim scaled flat gives its world box's corners
    cabinet, whole = (np.array([-0.5, 1.5, 0.1]), np.array([0.5, 2.2, 0.5])), \
        [(np.array([-3.0, 0.0, 0.1]), np.array([3.0 - 1e-12, 3.0, 0.6]))]
    assert fitting.fit(*cabinet, wall, mounted=whole) is fitting.CROWDED
    assert fitting.fit(*cabinet, wall) is None
    xform.AddScaleOp().Set(Gf.Vec3f(0.0, 0.0, 0.0))
    low, high = fitting.world_box(turned, f"/{TOY}/Objects/pipe_9")
    assert np.allclose(fitting.oriented_corners(turned, f"/{TOY}/Objects/pipe_9"),
                       [[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])


def test_a_thing_on_a_face_stands_on_its_front_never_inside_it():
    """#36, street 2026-10-30: two drying racks (0.12 m tall) stood 1.3 and 2.3 m inside their facade: its flat front
    has corners only at its ends, and the corners within the racks' height were a window's back. A facade whose front
    (z 0) is one box 10 m wide and a window's back 1.9 m inside it, its corners in the rack's height: the rack's back
    stands on the front, z 0, never on the window's back.
    Break: score/stages/assembly/fitting.py: `hits, _, _ = mesh.ray.intersects_location(origins, directions,
        multiple_hits=False)` -> `hits = mesh.vertices[(mesh.vertices[:, 1] >= band[0]) & (mesh.vertices[:, 1] <=
        band[1])]`
    Break: score/stages/assembly/fitting.py: touching's `if not MOVE_LEAST < float(gaps[nearest]) <= FACE_REACH:` ->
        `if True:` (the lantern left under its string's end), or off_faces' `if behind < -MOVE_LEAST:` -> `if False:`
        (the clothes left in the wall)
    Break: score/stages/assembly/fitting.py: on_face's `if face is not None and clear:` -> `if False:` (the second
        panel laid on the first)
    settle@street (2026-11-11): its 0.4 m red paper lanterns, laid against the side of their 1 cm lantern string,
    were shrunk to 16% and 2% to fit its height. A 0.4 m lantern the plan stood 15 m off, which the record hangs
    `below` an 8 m string 1 cm thick and sagging 6 cm a quarter of the way along it, keeps its size, its middle under
    the string 2 m along it (6 m at three quarters), its top on the string's underside there, and is held there; the
    rack against the facade is laid as before.
    Break: score/stages/assembly/fitting.py: `if how == "face" and on.get("below"):` -> `if False:` (the lantern
        shrunk against the string's side)
    Break: score/stages/assembly/fitting.py: hung_under's `target[[0, 2]], top = met[0][[0, 2]], float(met[0][1])` ->
        `pass` (hung under the box's foot, beside the string), or `target[[0, 2]] = foot[[0, 2]] if share is None else
        hung_run(points, float(share))` -> `target[[0, 2]] = foot[[0, 2]]` (every lantern at the string's end)
    Break: score/stages/assembly/fitting.py: off_holder's `return hung_off(low, high, box)` -> `pass` (the hung
        lantern judged off the string's side)
    settle@lab (2026-11-11): valve_3, laid on pipe_3's room side, hung free 0.41 m off it: the pipe model zig-zags
    across its 0.9 m box and at the valve's height its tube runs 0.5 m along the face. A 0.2 m valve against a 1 m
    box's E side whose one tube stands 0.8 m along it and 0.1 m inside is slid along onto the tube's middle, its back on it;
    one already in front of the tube stays. settle@quarters (2026-11-13): a 1.3 cm wrench against its desk's back was
    slid 0.2 m up, where only its top met the slanting lower edge of the desk's back panel, inside the desk as laid. A
    wrench slid to a panel whose lower edge is 0.2125 m up stands with its foot on it too, 0.25 m up.
    Break: score/stages/assembly/face_spots.py: met's `if None in ends:` -> `if True:` (the valve left on the box's
        side, touching nothing), or -> `if ends[1] is None:` (the wrench 0.2 m up, its foot under the panel), or
        fitting.py's `target = face_spots.met(surface, on, box, size * scale, target, clear)` dropped
    assembly@base (2026-11-12): ramp_front_left_1, a platform on legs, was stood on the toe of its module's own built
    ramp, a lip reaching 3 m out of the module's face beside its legs, and hung free 0.15 m off it. A 0.2 m cube 1 m in
    front of a wall's face, beside a 0.2 m wide lip reaching out to it, is pushed in until its back meets the face (its
    face plane then the face's); one 2.5 cm off the face (touching it), and one 2 m out (past the holder's depth), are
    left.
    Break: score/stages/assembly/face_reach.py: met's `<= resting.TOLERANCE:` -> `<= -1.0:` (the touching cube
        pushed), `if not fitting.MOVE_LEAST < gap <= depth:` -> `if not fitting.MOVE_LEAST < gap:` (the far cube
        pushed), or gap_in's `least = min(least, ...)` -> `least = least` (nothing pushed)
    assembly@square (2026-11-12): its lantern strings, hung 6 m up between its buildings, floated where the plan drew
    them. Between two 8 m buildings 8 m apart, a 10 m string laid along z is turned along the run between them and
    shrunk to 80%, its ends on both; a 4 m one is laid at its size from the first, the held gate naming it 4 m short
    of the second; one whose second holder is not laid waits, its prim inactive.
    Break: score/stages/assembly/fitting.py: `fits += hung_between.laid(stage, place, [entry for entry in entries if
        entry["name"] in laid])` dropped (the strings left where the plan drew them)
    Break: score/stages/assembly/hung_between.py: `degrees = (degrees + 90.0) % 180.0 - 90.0` -> `degrees = 0.0` (the
        string left along z), or `scale = min(1.0, run / max(length, 1e-9))` -> `scale = 1.0` (into both buildings),
        or laid's `if missing or len(holders) != 2` -> `if len(holders) != 2` (string_3 laid against a holder not laid)
    Break: score/stages/assembly/fitting.py: off's `return hung_between.off(low, high, boxes)` -> `pass` (the short
        string judged on the nearer holder's box only, 0 off)"""
    import trimesh
    from score.stages.assembly import fitting
    points, _, indices = boxes_mesh([((-5.0, 0.0, -0.3), (5.0, 10.0, 0.0)), ((-0.5, 6.0, -2.0), (0.5, 6.1, -1.9))])
    facade = trimesh.Trimesh(points, [quad[:3] for quad in np.reshape(indices, (-1, 4))]
                             + [quad[[0, 2, 3]] for quad in np.reshape(indices, (-1, 4))], process=False)
    on = {"how": "face", "holder": ["facade_1"], "out": [0.0, 1.0]}
    box = (np.array([-5.0, 0.0, -2.0]), np.array([5.0, 10.0, 0.0]))
    scale, target, (back, hung) = fitting.on_face(np.array([-0.75, 6.0, 0.5]), np.array([0.75, 6.1, 1.0]), on, box,
                                                  facade)
    assert back == 0.0 and np.allclose(target, (0.0, 6.0, 0.25)) and scale == 1.0 and not hung, (back, target)
    walled = fitting.fit(np.array([-0.75, 6.0, 0.5]), np.array([0.75, 6.1, 1.0]), on, [box], facade)
    assert walled[0] == 1.0 and np.allclose(walled[1], target) and walled[3] == (0.0, False), walled
    sag = np.array([[x, 24.06 - 0.06 * (1.0 - (x / 4.0 - 1.0) ** 2), 0.0] for x in np.linspace(0.0, 8.0, 33)])
    string = trimesh.util.concatenate([trimesh.creation.box(bounds=[(first[0], min(first[1], second[1]), -0.005),
                                                                    (second[0], max(first[1], second[1]) + 0.01,
                                                                     0.005)]) for first, second in zip(sag, sag[1:])])
    strung = (np.asarray(string.bounds[0], float), np.asarray(string.bounds[1], float))
    lantern = (np.array([9.8, 6.0, -15.2]), np.array([10.2, 6.4, -14.8]))  # where the plan stood it, far off
    below = {"how": "face", "holder": ["lantern_string_1"], "out": [0.0, 1.0], "below": True, "along": 0.25}
    scale, target, _, face = fitting.fit(*lantern, below, [strung], string)
    under = string.vertices[np.abs(string.vertices[:, 0] - 2.0) < 0.13][:, 1].min()
    assert scale == 1.0 and face is None and abs(target[2]) <= 0.005 and abs(target[0] - 2.0) < 0.13, target
    assert abs(target[1] + 0.4 - under) < 0.01, (target, under)
    assert abs(fitting.fit(*lantern, dict(below, along=0.75), [strung], string)[1][0] - 6.0) < 0.13
    hung_low, hung_high = np.asarray(lantern[0]) - fitting.foot_middle(*lantern) + target, \
        np.asarray(lantern[1]) - fitting.foot_middle(*lantern) + target
    assert fitting.off(hung_low, hung_high, below, [strung]) <= fitting.HELD_MOST
    assert fitting.off(*lantern, below, [strung]) > fitting.HELD_MOST  # left where the plan stood it, 6 m up
    assert fitting.fit(*lantern, dict(below, below=False), [strung], string)[0] < 0.5  # against its side: shrunk
    # wreck (2026-11-11): three solar panels on their lander's N face laid at one spot, its built surface 1.5 m
    # inside its box's side, where the panels laid before it were never measured. A 0.3 m panel at a 2 m holder's
    # left end, the surface at z 0.9 inside its box (z 0 to 2) and one panel standing on it there, goes beside it.
    lander = (np.array([0.0, 0.0, 0.0]), np.array([2.0, 1.0, 2.0]))
    frame = trimesh.creation.box(bounds=[(0.0, 0.0, 0.9), (2.0, 1.0, 1.1)])
    north = {"how": "face", "holder": ["lander_1"], "out": [0.0, -1.0]}
    first = np.array([[x, y, z] for x in (0.0, 0.3) for y in (0.0, 0.13) for z in (0.79, 0.9)])
    _, beside, _, _ = fitting.fit((0.0, 0.0, 0.4), (0.3, 0.13, 0.51), north, [lander], frame, mounted=[first])
    _, alone, _, _ = fitting.fit((0.0, 0.0, 0.4), (0.3, 0.13, 0.51), north, [lander], frame)
    assert np.allclose(beside, (0.45, 0.0, 0.845)) and np.allclose(alone, (0.15, 0.0, 0.845)), (beside, alone)
    pipe = trimesh.creation.box(bounds=[(-0.2, 0.0, -0.92), (-0.1, 2.5, -0.78)])
    piped = (np.array([-0.5, 0.0, -1.0]), np.array([0.0, 2.5, 0.0]))
    east = {"how": "face", "holder": ["pipe_3"], "out": [1.0, 0.0]}
    _, valve, (valve_back, _) = fitting.on_face(np.array([0.0, 1.5, -0.2]), np.array([0.05, 1.7, 0.0]), east, piped,
                                                pipe)
    assert abs(valve_back + 0.1) < 1e-9 and np.allclose(valve, (-0.075, 1.5, -0.8)), (valve, valve_back)
    _, kept, (kept_back, _) = fitting.on_face(np.array([0.0, 1.5, -0.95]), np.array([0.05, 1.7, -0.75]), east, piped,
                                              pipe)
    assert abs(kept_back + 0.1) < 1e-9 and np.allclose(kept, (-0.075, 1.5, -0.85)), kept
    from score.stages.assembly import face_spots
    panel = trimesh.creation.box(bounds=[(0.0, 0.2125, 0.9), (0.5, 0.5, 1.0)])
    wrench = face_spots.met(panel, {"how": "face", "out": [0.0, 1.0]}, (np.zeros(3), np.array([1.0, 0.5, 1.0])),
                            (0.166, 0.013, 0.05), (0.75, 0.0, 1.025))
    assert np.allclose(wrench, (0.483, 0.25, 1.025)), wrench
    # settle@street (2026-11-11): lantern 11, on the 1 cm end of its sagging string, stood 0.045 m under it; hanging
    # clothes 3 and 4, within a drying rack turned along slanted wall_7, stood 0.05 m behind its face. A 0.1 m cube
    # 0.04 m under a holder's surface is moved up onto it, one 0.5 m away is left; one 0.05 m behind a wall face along
    # (1, 1) is moved out along the face's way until it stands in front of it.
    from pxr import Gf, Usd, UsdGeom

    def a_cube(stage, path, low, high):
        cube = trimesh.creation.box(bounds=[low, high])
        UsdGeom.Xform.Define(stage, path).AddTransformOp().Set(Gf.Matrix4d(1.0))
        mesh = UsdGeom.Mesh.Define(stage, f"{path}/geo")
        mesh.CreatePointsAttr([tuple(map(float, point)) for point in cube.vertices])
        mesh.CreateFaceVertexCountsAttr([3] * len(cube.faces))
        mesh.CreateFaceVertexIndicesAttr([int(index) for index in cube.faces.ravel()])
    placed = Usd.Stage.CreateInMemory()
    holder = trimesh.creation.box(bounds=[(0.0, 1.0, 0.0), (1.0, 1.1, 0.01)])
    for name, low in (("lantern_1", (0.4, 0.86, 0.0)), ("lantern_2", (0.4, 0.4, 0.0))):
        a_cube(placed, f"/{TOY}/Objects/{name}", low, np.add(low, 0.1))
    assert "onto its holder's surface" in fitting.touching(placed, f"/{TOY}/Objects/lantern_1", holder)
    assert abs(fitting.world_box(placed, f"/{TOY}/Objects/lantern_1")[1][1] - 1.0) < 1e-6
    assert fitting.touching(placed, f"/{TOY}/Objects/lantern_2", holder) == ""
    a_cube(placed, f"/{TOY}/Objects/clothes_1", (1.0, 0.0, 0.9), (1.2, 0.5, 1.1))
    wall = {"how": "wall", "span": [[0.0, 0.0], [3.0, 3.0]], "out": [-0.7071068, 0.7071068]}
    assert "out of the wall" in fitting.off_faces(placed, f"/{TOY}/Objects/clothes_1", [wall])
    corners = trimesh.bounds.corners(np.array(fitting.world_box(placed, f"/{TOY}/Objects/clothes_1")))[:, [0, 2]]
    assert abs(float((corners @ np.array(wall["out"])).min())) < 1e-6, corners
    from score.stages.assembly import face_reach
    module = trimesh.util.concatenate([trimesh.creation.box(bounds=[(-1.0, 0.0, -0.3), (1.0, 2.0, 0.0)]),
                                       trimesh.creation.box(bounds=[(0.5, 0.0, 0.0), (0.7, 0.2, 1.0)])])
    front = {"how": "face", "holder": ["module_1"], "out": [0.0, 1.0]}
    for name, low in (("ramp_1", (0.0, 0.5, 1.0)), ("ramp_2", (-0.5, 0.5, 0.025)), ("ramp_3", (-0.9, 0.5, 2.0))):
        a_cube(placed, f"/{TOY}/Objects/{name}", low, np.add(low, 0.2))
    words, face = face_reach.met(placed, f"/{TOY}/Objects/ramp_1", front, module, (1.0, False), "laid")
    back = fitting.world_box(placed, f"/{TOY}/Objects/ramp_1")[0][2]
    assert "pushed 0.99 m in" in words and abs(back - 0.005) < 1e-3 and abs(face[0] - back) < 1e-6, (words, back)
    for name, low in (("ramp_2", 0.025), ("ramp_3", 2.0)):
        assert face_reach.met(placed, f"/{TOY}/Objects/{name}", front, module, (low, False), "laid") == \
            ("laid", (low, False)), name
        assert abs(fitting.world_box(placed, f"/{TOY}/Objects/{name}")[0][2] - low) < 1e-6, name
    strung = Usd.Stage.CreateInMemory()
    for name, low, high in (("building_1", (-10.0, 0.0, -5.0), (-2.0, 20.0, 5.0)),
                            ("building_2", (6.0, 0.0, -5.0), (14.0, 20.0, 5.0)),
                            ("string_1", (1.9, 6.0, -4.0), (2.1, 6.2, 6.0)),
                            ("string_2", (0.0, 7.0, 2.9), (4.0, 7.2, 3.1)),
                            ("string_3", (0.0, 8.0, -1.1), (4.0, 8.2, -0.9))):
        a_cube(strung, f"/{TOY}/Objects/{name}", low, high)
    between = [{"name": f"string_{number}", "row": "string",
                "on": {"how": "between", "holder": ["building_1", f"building_{2 if number < 3 else 3}"]}}
               for number in (1, 2, 3)]
    hung = fitting.fitted(strung, TOY, [{"name": "building_1", "row": "building"},
                                        {"name": "building_2", "row": "building"}, *between],
                          {"building_1", "building_2", "string_1", "string_2", "string_3"})
    hows = {fit["name"]: fit["how"] for fit in hung}
    assert hows == {"string_1": "between", "string_2": "between", "string_3": "waiting"}, hung
    spans = {name: fitting.world_box(strung, f"/{TOY}/Objects/{name}") for name in ("string_1", "string_2")}
    assert np.allclose(spans["string_1"], ((-2.0, 6.0, 0.92), (6.0, 6.16, 1.08)), atol=1e-6), spans
    assert np.allclose(spans["string_2"], ((-2.0, 7.0, 2.9), (2.0, 7.2, 3.1)), atol=1e-6), spans
    assert not strung.GetPrimAtPath(f"/{TOY}/Objects/string_3").IsActive(), hung
    buildings = [fitting.world_box(strung, f"/{TOY}/Objects/building_{number}") for number in (1, 2)]
    assert fitting.off(*spans["string_1"], between[0]["on"], buildings) < 1e-6
    assert abs(fitting.off(*spans["string_2"], between[1]["on"], buildings) - 4.0) < 1e-6


def test_a_monitor_goes_on_its_console_s_top_within_its_span():
    """A 0.5 x 0.4 x 0.1 m monitor laid 2 m off its 3 x 1 x 0.8 m console (x 0 to 3, top at 1 m) stands on its top,
    moved in to x 3 - 0.25 = 2.75, z kept at 0.4, its foot at 1 m; a console narrower than it shrinks it to fit.
    Break: score/stages/assembly/fitting.py: `target[1] = hold_high[1] if how == "top" else` -> `target[1] = foot[1]
        if how == "top" else`
    Break: score/stages/assembly/fitting.py: on_boards' `if clear_of(hits, foot, tall) and not meets_any(...)` ->
        `if not meets_any(...)` (the box at 0.7 laid on the board under it, 0.42, through the next)
    Break: score/stages/assembly/fitting.py: on_boards' `return None` after `if not found:` reached first (`found =
        rests or tops` -> `found = []`): the box through the board named crowded
    Break: score/stages/assembly/fitting.py: on_boards' `return None` after `if not found:` -> `return target` (the
        box on a full unit piled at its target, garage 2026-11-10), or shelved's `for holder, box in sorted(held,
        key=distance)` -> `for holder, box in held[:1]` (the far unit never tried), or its `for stack in (False, True)`
        -> `for stack in (False,)` (the box on two full units crowded, not stacked), or stacked_spots' `or float(low[1]) >
        hold_high[1] + BOARD_BED` dropped (a box stacked on a stacked one)
    Break: score/stages/assembly/fitting.py: on_boards' `meets_any(*footprint(placed), taken)` -> `False` (the twin on
        its first)
    Break: score/stages/assembly/fitting.py: on_boards' `if not len(hits[0]) or (standing and clear_of(` -> `if not
        len(hits[0]) or (clear_of(` (the box laid between boards left over the board under it)
    Break: score/stages/assembly/fitting.py: crosses' `return bool(np.any(...))` -> `return False` (the box left
        across the divider)
    Break: score/stages/assembly/fitting.py: on_boards' `if not any(float(spot[1]) < inside for spot in rests):` ->
        `if False:` (the box on the packed unit's top, its board's clear stretch stepped over: garage 2026-11-11)
    Break: score/stages/assembly/fitting.py: supported's `return all(` -> `return True or all(` (galley's jars left on
        the strut and over the board's edge), or on_boards' `and float(target[1]) <= hold_low[1] + BOARD_BED` dropped
        (the jar left at 1.5 m over no board), or slid_spots' `for axis in (0, 2):` -> `for axis in (2,):` (the jar
        past the boards never slid across onto one)
    Break: score/stages/assembly/fitting.py: on_shelves_of's `return str(on.get("why") or "").startswith(SHELVES)` ->
        `return True`
    Break: score/stages/assembly/fitting.py: spread_on_tops' `target[axis], target[1] = at + gap + longs[name] / 2,
        top` -> `target[1] = top` (the boxes left in each other)
    Break: score/stages/assembly/fitting.py: spread_on_tops' `if gap < BOARD_CLEAR:` -> `if False:` (four boxes
        spread one in the next)
    Break: score/stages/assembly/fitting.py: top_run's `if any(lows[after, axis] > highs[before, axis] +
        BOARD_CLEAR ...)` -> `if False:` (boxes spread over the gap between units)
    Break: score/stages/assembly/fitting.py: spread_on_tops' `if len(rows) > 1: target[side] = across_at` -> `if False:`
        (hub's screens left in one another across the desk), or packed_rows' `BOARD_CLEAR * (len(rows) + 1) > depth:`
        -> `> 9.0:` (seven boxes in rows deeper than the top), or `carry(stage, place, carried, name, ...)` dropped
        (quarters' papers left where their book stood)
    Break: score/stages/assembly/fitting.py: off's `if on["how"] == "top" and len(boxes) > 1 and top_run(boxes) is not
        None:` -> `if False:` (workshop's box spread over two units' meeting named 0.2 m off one)
    Break: score/stages/assembly/built_tops.py: rest's `if height > foot + reach or np.any(...)` -> `if height > foot +
        reach:` (the keyboard on the slab's underside), or spot's `tries += sorted(...)` dropped (the lamp left across
        the divider), or let_down's `fitting.carry(...)` dropped (the paper left at 1.5 m), or held_on's `not
        fitting.on_shelves_of(on) and` dropped (the jar on the shelves let down), or rest's `if reach <=
        fitting.BOARD_BED and np.any(...)` -> `if False:` (the box under the slab on its shelf), or let_down's `if
        laid is None and not within:` -> `if False:` (the crate left over the divider)
    Break: score/stages/assembly/fitting.py: off_holder's `float(on.get("top at", hold_high[1]))` -> `hold_high[1]`
        (the monitor let down onto the slab named 0.45 m off its desk's top)
    Break: score/stages/assembly/crest_tops.py: rest's `lift = float(np.nanmax(np.concatenate(...))) + CLEAR` -> `lift
        = CLEAR` (the pile left 0.4 m over the crest), or one's `if here is not None and abs(here - CLEAR) <=
        fitting.MOVE_LEAST and stands(...):` -> `if False:` (the pile resting on the crest laid again), or may_rest's
        `lift = np.max(...) + CLEAR` -> `lift = np.max(...) + CLEAR + triage.TOLERANCE` (the sieve passes the crest
        by: the pile left over it), or its `& (most - weights[:, axis] >= triage.BALANCE - SLACK)` dropped
        (rest asked along the ridge's strip)
    Break: score/stages/assembly/fitting.py: shelved's `for stack in (False, True, piled.PILE):` -> `for stack in
        (False, True):` (camp's tray crowded), or piled.py: spots' `if not flat(size): return []` dropped (garage's
        box piled on its stacked one)
    Break: score/stages/assembly/flush_tops.py: laid's `if sloped is None or not triage.LEAN_MOST < sloped[1] <=
        SLOPE_MOST:` -> `if sloped is None:` (the box laid flush on the 30-degree slab), or crest_tops.py: stands'
        `triage.lean(turn, ...)` -> `triage.lean(np.eye(4), ...)` (the box left upright on the 15-degree slab)
    Break: score/stages/assembly/fine_tops.py: spot's `if crest_tops.stands(mesh, exact, move):` -> `if False:` (the
        computer left over the desk's slope), its `xs = np.arange(hold_low[0], ...)`, `zs = ...` -> each
        `fitting.kept_within(...)` of it as crest_tops.spot keeps them (its middle at most 0.64 m: left), or meets'
        `return overlap(square, np.asarray(outline, float)) > fitting.BOARD_CLEAR` -> `return True` (the box beside the
        diagonal railing read as in it)
    Break: score/stages/assembly/fine_tops.py: one's `found + beside(stage, place, entry, carried, ...)` -> `found`
        (the book left leaning on the wrench), or fitting.py: reaches_into's `np.minimum(BOARD_CLEAR, thinner / 4)` ->
        `BOARD_CLEAR` (the wrenches read clear) or -> `np.minimum(BOARD_CLEAR, thinner / 2)` (the book's corner read clear), beside's `< under]` -> `< -1.0]`, or crest_tops.py: stands' `points[:,
        1] - tops` -> `np.maximum(points[:, 1] - tops, 0.0)` (the book's points in the wrench read at their own height)
    Break: score/stages/assembly/fine_tops.py: laid's `fitting.with_stacked(stage, place, carried, list(by_name))` ->
        `carried` (the cup left at 1.4 m as its computer is laid on the rim), or fitting.py: with_stacked's `<=
        BOARD_BED and` -> `<= -1.0 and` (nothing read standing on anything)
    Break: score/stages/assembly/fine_tops.py: one's `and crowding(stage, place, entry, carried, (low, high)) is None`
        dropped (lab's monitor left 0.1 m into the other), or crowding's `float(found[1][1]) <= float(high[1]) + SAME
        and` dropped (quarters' wrench laid again for the book laid over it)
    Break: score/stages/assembly/fine_tops.py: one's `move, on_other = stacked(stage, place, entry, thing, (low, high),
        carried)` -> `pass` (the third cup left over the slope), or its `float(np.linalg.norm(move)) <
        fitting.MOVE_LEAST)` -> `False)` (the stacked cup laid again where it is)
    Break: score/stages/assembly/crest_tops.py: stands' `balance(moved.vertices)` -> `triage.BALANCE`, rest's `<
        balance(every)` -> `< triage.BALANCE` or may_rest's `inside = ..., balance(low)` -> `..., triage.BALANCE` (the
        6 cm box read not resting on the flat slab), or balance's `/ 4` -> `/ 0.5` (the box over the edge read resting)
    Break: score/stages/assembly/railings_held.py: held_up's `keep = min(1.0, ...)` -> `keep = 1.0` (the chord left 4.5
        m tall), cut_back's `if not inside(points[near], hulls):` -> `if True:` (its end left in the wall), change's
        `if outside_by(laid_mesh, under) <= triage.BALANCE - BALANCE_SPARE:` -> `if True:` (left over the opening),
        or held's `and not CLIMBED & set(climbing)` dropped (the stair's railing held)"""
    from score.stages.assembly import fitting
    console = (np.array([0.0, 0.0, 0.0]), np.array([3.0, 1.0, 0.8]))
    on = {"how": "top", "holder": ["console_1"]}
    scale, target, _, _ = fitting.fit((4.5, 0.0, 0.35), (5.0, 0.4, 0.45), on, [console])
    assert scale == 1.0 and np.allclose(target, (2.75, 1.0, 0.4)), target
    narrow = (np.array([0.0, 0.0, 0.0]), np.array([0.4, 1.0, 0.8]))
    scale, target, _, _ = fitting.fit((4.5, 0.0, 0.35), (5.0, 0.4, 0.45), on, [narrow])
    assert abs(scale - 0.8) < 1e-9 and np.allclose(target, (0.2, 1.0, 0.4)), (scale, target)
    # engineroom (2026-11-08): boxes laid within their shelf unit at the plan's base, through its boards. A shelf
    # unit 1 x 2 x 0.5 m, its 2 cm boards 0.4 m apart (tops at 0.02, 0.42 ... 1.62) and its top at 2.0: a 0.3 m box
    # laid at 0.7 through the board at 0.8 goes onto the nearest board it fits on, 0.82; its twin laid at the same
    # spot onto the board under, 0.42, and a third, both taken, slid along the unit (0.3 m and BOARD_CLEAR) onto the
    # board at 0.82; a 0.404 m box fits between no boards and
    # goes on the top; one laid between them over no board goes down onto the board under it, one on a board is left.
    unit = trimesh.util.concatenate([trimesh.creation.box(bounds=[(0.0, 0.4 * level, 0.0),
                                                                  (1.0, 0.4 * level + 0.02, 0.5)])
                                     for level in range(5)] + [trimesh.creation.box(bounds=[(0.0, 1.98, 0.0),
                                                                                            (1.0, 2.0, 0.5)])])
    shelf = (np.array([0.0, 0.0, 0.0]), np.array([1.0, 2.0, 0.5]))
    within = {"how": "within", "holder": ["shelf_1"]}
    _, target, _, _ = fitting.fit((0.35, 0.7, 0.1), (0.65, 1.0, 0.4), within, [shelf], unit)
    assert np.allclose(target, (0.5, 0.82, 0.25)), target
    first = ((0.35, 0.82, 0.1), (0.65, 1.12, 0.4))
    _, twin, _, _ = fitting.fit((0.35, 0.7, 0.1), (0.65, 1.0, 0.4), within, [shelf], unit, clear=[first])
    assert np.allclose(twin, (0.5, 0.42, 0.25)), twin
    _, third, _, _ = fitting.fit((0.35, 0.7, 0.1), (0.65, 1.0, 0.4), within, [shelf], unit,
                                 clear=[first, ((0.35, 0.42, 0.1), (0.65, 0.72, 0.4))])
    assert np.allclose(third, (0.81, 0.82, 0.25)), third
    _, target, _, _ = fitting.fit((0.3, 0.5, 0.05), (0.7, 0.904, 0.45), within, [shelf], unit)
    assert np.allclose(target, (0.5, 2.0, 0.25)), target
    _, target, _, _ = fitting.fit((0.35, 0.45, 0.1), (0.65, 0.75, 0.4), within, [shelf], unit)
    assert np.allclose(target, (0.5, 0.42, 0.25)), target
    assert fitting.fit((0.35, 0.42, 0.1), (0.65, 0.72, 0.4), within, [shelf], unit) is None
    # galley (2026-11-08): jars laid on a board through a side the rays straight down never meet; a box on the board
    # at 0.42 across an upright 4 cm divider at the unit's middle is slid along clear of it
    divided = trimesh.util.concatenate([unit, trimesh.creation.box(bounds=[(0.48, 0.0, 0.0), (0.52, 1.98, 0.5)])])
    _, target, _, _ = fitting.fit((0.35, 0.42, 0.1), (0.65, 0.72, 0.4), within, [shelf], divided)
    assert np.allclose(target, (0.81, 0.42, 0.25)), target
    # garage (2026-11-11): its shelf units carry their own boxes on their boards, a clear stretch beside them the
    # slide's 0.31 m steps from the box's spot step over. A unit 1 x 0.42 x 0.5 m (its board's top at 0.02, its top
    # at 0.42) whose own 0.25 m blocks fill its board but for x 0.49 to 0.82 lays a 0.3 m box laid at x 0.5 on that
    # stretch of its board, not on its top.
    packed = trimesh.util.concatenate([trimesh.creation.box(bounds=bounds) for bounds in (
        [(0.0, 0.0, 0.0), (1.0, 0.02, 0.5)], [(0.0, 0.40, 0.0), (1.0, 0.42, 0.5)],
        [(0.0, 0.02, 0.0), (0.49, 0.27, 0.5)], [(0.82, 0.02, 0.0), (1.0, 0.27, 0.5)])])
    low_unit = (np.array([0.0, 0.0, 0.0]), np.array([1.0, 0.42, 0.5]))
    _, target, _, _ = fitting.fit((0.35, 0.1, 0.1), (0.65, 0.4, 0.4), within, [low_unit], packed)
    assert 0.63 < target[0] < 0.68 and np.allclose(target[1:], (0.02, 0.25)), target
    # galley (settle@galley, 2026-11-11): corner shelves whose boards fill 0.6 m of its 1 m box. A jar laid at 1.5 m
    # past the boards, over none, one on a 3 cm strut and one half over a board's edge each go onto a board under the
    # inner half of their footprint; one at the unit's foot over none, and one on a board, are left.
    corner = trimesh.util.concatenate([trimesh.creation.box(bounds=[(0.0, level, 0.0), (0.6, level + 0.02, 0.5)])
                                       for level in (0.6, 1.6, 1.98)]
                                      + [trimesh.creation.box(bounds=[(0.81, 0.98, 0.0), (0.84, 1.0, 0.5)])])
    corners = (np.array([0.0, 0.0, 0.0]), np.array([1.0, 2.0, 0.5]))
    for foot, wanted in (((0.85, 1.5), (0.57, 1.62)), ((0.775, 1.0), (0.495, 0.62)), ((0.55, 0.62), (0.49, 0.62))):
        _, target, _, _ = fitting.fit((foot[0], foot[1], 0.2), (foot[0] + 0.1, foot[1] + 0.15, 0.3), within, [corners],
                                      corner)
        assert np.allclose(target, (*wanted, 0.25)), (foot, target)
    for foot in ((0.85, 0.0), (0.2, 1.62)):
        assert fitting.fit((foot[0], foot[1], 0.2), (foot[0] + 0.1, foot[1] + 0.15, 0.3), within, [corners],
                           corner) is None, foot
    # garage (settle@garage, 2026-11-10): 14 boxes within three shelf units all went to the nearest, 12 piled at two
    # spots of it. A unit 0.4 x 0.5 x 0.5 m with one board (top at 0.02) and its top at 0.5 takes a 0.3 m box on its
    # board, then on its top; with both taken the box goes onto the board of the next unit out (x 1 to 1.4); with
    # that one full too it is stacked on the box on the nearest unit's top (garage's three units hold 7 of its 14,
    # 2026-11-11), and with a box stacked on each top too it is crowded, never piled at its target.
    one_board = trimesh.util.concatenate([trimesh.creation.box(bounds=[(0.0, 0.0, 0.0), (0.4, 0.02, 0.5)]),
                                          trimesh.creation.box(bounds=[(0.0, 0.48, 0.0), (0.4, 0.5, 0.5)])])
    near, far = one_board, one_board.copy().apply_translation((1.0, 0.0, 0.0))
    held = [("unit_far", (np.array([1.0, 0.0, 0.0]), np.array([1.4, 0.5, 0.5]))),
            ("unit_near", (np.array([0.0, 0.0, 0.0]), np.array([0.4, 0.5, 0.5])))]
    surfaces = {"unit_near": near, "unit_far": far}
    laid = ((0.025, 0.1, 0.05), (0.375, 0.4, 0.45))
    full = [((0.025, 0.02, 0.05), (0.375, 0.32, 0.45)), ((0.025, 0.5, 0.05), (0.375, 0.8, 0.45))]
    holder, (_, target, _, _) = fitting.shelved(*laid, within, held, surfaces.get, {})
    assert holder == "unit_near" and np.allclose(target, (0.2, 0.02, 0.25)), (holder, target)
    holder, (_, target, _, _) = fitting.shelved(*laid, within, held, surfaces.get, {"unit_near": full})
    assert holder == "unit_far" and np.allclose(target, (1.175, 0.02, 0.25)), (holder, target)  # its near end
    far_full = [((low[0] + 1.0, *low[1:]), (high[0] + 1.0, *high[1:])) for low, high in full]
    holder, (_, target, _, _) = fitting.shelved(*laid, within, held, surfaces.get,
                                                {"unit_near": full, "unit_far": far_full})
    assert holder == "unit_near" and np.allclose(target, (0.2, 0.8, 0.25)), (holder, target)

    def piled(boxes):
        return [*boxes, ((boxes[1][0][0], 0.8, boxes[1][0][2]), (boxes[1][1][0], 1.1, boxes[1][1][2]))]

    assert fitting.shelved(*laid, within, held, surfaces.get, {"unit_near": piled(full), "unit_far": piled(far_full)}) \
        == (None, fitting.CROWDED)
    # camp (settle@camp, 2026-11-12): its plant rack's model holds plants on every board, so of its four trays one
    # went on its top, one stacked on that, and two were left crowded, floating and leaning. A flat tray (0.35 x 0.172
    # x 0.4 m: its height at most piled.FLAT of its narrower side), every board, top and stacking spot taken, piles on
    # the stacked box of the nearest unit; the 0.3 m box above never piles.
    tray = ((0.025, 0.1, 0.05), (0.375, 0.272, 0.45))
    holder, (_, target, _, _) = fitting.shelved(*tray, within, held, surfaces.get,
                                                {"unit_near": piled(full), "unit_far": piled(far_full)})
    assert holder == "unit_near" and np.allclose(target, (0.2, 1.1, 0.25)), (holder, target)
    # only a thing on its holder's shelves is laid on its boards (galley's sink in its counter, its stove top on it,
    # are laid as the plan draws them)
    # workshop (settle@workshop, 2026-11-10): seven 0.408 m storage boxes on two 1.5 m shelf units side by side, each
    # kept within its nearest unit, boxes 6 and 7 one in the other. Three 0.3 m boxes on two 0.5 m units (tops at 1 m,
    # x 0 to 1), two meeting, are spread evenly along the 1 m run in their order: gaps of 0.025 m; a fourth would not
    # fit and leaves them as laid; a unit standing 0.2 m apart makes no one run.
    from pxr import Usd
    stage = Usd.Stage.CreateInMemory()
    a_built_box(stage, f"/{TOY}/Objects/unit_1", (0.0, 0.0, 0.0), (0.5, 1.0, 0.4))
    a_built_box(stage, f"/{TOY}/Objects/unit_2", (0.5, 0.0, 0.0), (1.0, 1.0, 0.4))
    for name, start in (("box_1", 0.0), ("box_2", 0.5), ("box_3", 0.55)):
        a_built_box(stage, f"/{TOY}/Objects/{name}", (start, 1.0, 0.0), (start + 0.3, 1.2, 0.4))
    top = {"how": "top", "holder": ["unit_1", "unit_2"]}
    boxes = [{"name": f"box_{number}", "row": "box", "on": top} for number in (1, 2, 3)]
    fits = fitting.spread_on_tops(stage, TOY, boxes)
    assert sorted(fit["name"] for fit in fits) == ["box_1", "box_2", "box_3"], fits
    lows = [float(fitting.world_box(stage, f"/{TOY}/Objects/box_{number}")[0][0]) for number in (1, 2, 3)]
    assert np.allclose(lows, (0.025, 0.35, 0.675)), lows
    spread = {"objects": [{"name": name, **dict(zip(("low", "high"), fitting.world_box(stage, f"/{TOY}/Objects/{name}")))}
                          for name in ("unit_1", "unit_2", "box_1", "box_2", "box_3")]}
    assert fitting.held_faults({"objects": boxes}, spread) == [], fitting.held_faults({"objects": boxes}, spread)
    assert fitting.spread_on_tops(stage, TOY, boxes) == []  # spread: none meets another
    a_built_box(stage, f"/{TOY}/Objects/box_4", (0.6, 1.0, 0.0), (0.9, 1.2, 0.4))
    assert fitting.spread_on_tops(stage, TOY, [*boxes, {"name": "box_4", "row": "box", "on": top}]) == []
    assert fitting.top_run([(np.zeros(3), np.array([0.5, 1.0, 0.4])),
                            (np.array([0.7, 0.0, 0.0]), np.array([1.2, 1.0, 0.4]))]) is None
    # hub (2026-11-11): 16 monitors on its 1.75 x 0.81 m console laid at one spot. Six 0.3 x 0.1 m screens at one
    # spot of a 1 x 0.4 m desk top are spread in two rows of three, none meeting another; seven 0.3 x 0.3 m boxes
    # need three rows 0.9 m deep and are left for the held gate.
    a_built_box(stage, f"/{TOY}/Objects/desk_1", (3.0, 0.0, 0.0), (4.0, 0.8, 0.4))
    on_desk = {"how": "top", "holder": ["desk_1"]}
    for number in range(6):
        a_built_box(stage, f"/{TOY}/Objects/screen_{number}", (3.3, 0.8, 0.1), (3.6, 1.1, 0.2))
    screens = [{"name": f"screen_{number}", "row": "screen", "on": on_desk} for number in range(6)]
    assert len(fitting.spread_on_tops(stage, TOY, screens)) == 6
    laid = [fitting.world_box(stage, f"/{TOY}/Objects/screen_{number}") for number in range(6)]
    assert all(float(fitting.depths(*laid[one], laid[other]).min()) <= 0.0 for one in range(6)
               for other in range(one + 1, 6)), laid
    assert all(3.0 <= low[0] and high[0] <= 4.0 and 0.0 <= low[2] and high[2] <= 0.4 for low, high in laid), laid
    # quarters (2026-11-11): papers on a book stayed where the book stood before the desk's things were spread
    a_built_box(stage, f"/{TOY}/Objects/desk_2", (6.0, 0.0, 0.0), (7.0, 0.8, 0.4))
    on_second = {"how": "top", "holder": ["desk_2"]}
    a_built_box(stage, f"/{TOY}/Objects/paper_1", (6.3, 1.1, 0.1), (6.4, 1.11, 0.2))  # on tray_2, which is spread
    paper = {"name": "paper_1", "row": "paper", "on": {"how": "top", "holder": ["tray_2"]}}
    for name in ("tray_1", "tray_2"):
        a_built_box(stage, f"/{TOY}/Objects/{name}", (6.3, 0.8, 0.1), (6.6, 1.1, 0.2))
    before = fitting.world_box(stage, f"/{TOY}/Objects/tray_2")[0]
    fitting.spread_on_tops(stage, TOY, [{"name": "tray_1", "row": "tray", "on": on_second},
                                        {"name": "tray_2", "row": "tray", "on": on_second}, paper])
    shift = fitting.world_box(stage, f"/{TOY}/Objects/tray_2")[0] - before
    assert float(np.linalg.norm(shift)) > 0.01 and np.allclose(fitting.world_box(stage, f"/{TOY}/Objects/paper_1")[0],
                                                               np.array([6.3, 1.1, 0.1]) + shift), shift
    assert fitting.packed_rows([0.3] * 7, [0.3] * 7, 1.0, 0.4) is None
    assert fitting.on_shelves_of({"how": "within", "why": "on the shelves of shelf: its reading says 'on shelves'"})
    assert not fitting.on_shelves_of({"how": "within", "why": "within kitchen_counter: the plan lays it inside"})
    # lab, quarters, flat, workshop (settle@<place>, 2026-11-11): things on a desk laid on its box's top, the top of a
    # divider standing over it, floated over the desk's surface or leaned on an edge, past the settle's 30 cm snap. A
    # desk 1 x 0.6 m, its 3 cm slab's top at 0.75 and a divider up to 1.2 m along its back (z 0.5 to 0.6): a monitor
    # laid on its box top (1.2) goes down onto the slab, the paper on it with it, and the held gate measures it there;
    # a lamp across the divider's front is slid off it onto the slab; a keyboard laid within the desk across the slab
    # (0.7 to 0.76) goes onto the slab's top, never its underside; one within it at its foot is left.
    from score.stages.assembly import built_tops
    from pxr import Gf, UsdGeom
    built = trimesh.util.concatenate([trimesh.creation.box(bounds=bounds) for bounds in (
        [(8.0, 0.72, 0.0), (9.0, 0.75, 0.6)], [(8.0, 0.0, 0.0), (8.05, 0.72, 0.6)],
        [(8.95, 0.0, 0.0), (9.0, 0.72, 0.6)], [(8.0, 0.75, 0.5), (9.0, 1.2, 0.6)])])
    UsdGeom.Xform.Define(stage, f"/{TOY}/Objects/desk_3").AddTransformOp().Set(Gf.Matrix4d(1.0))
    desk = UsdGeom.Mesh.Define(stage, f"/{TOY}/Objects/desk_3/geo")
    desk.CreatePointsAttr([tuple(map(float, point)) for point in built.vertices])
    desk.CreateFaceVertexCountsAttr([3] * len(built.faces))
    desk.CreateFaceVertexIndicesAttr([int(index) for index in built.faces.ravel()])
    on_third = {"how": "top", "holder": ["desk_3"]}
    for name, low, high in (("monitor_9", (8.1, 1.2, 0.1), (8.4, 1.5, 0.3)),
                            ("paper_9", (8.2, 1.5, 0.15), (8.3, 1.51, 0.25)),
                            ("lamp_9", (8.6, 1.2, 0.35), (8.8, 1.5, 0.55)),
                            ("keyboard_9", (8.5, 0.7, 0.05), (8.9, 0.76, 0.2)), ("bin_9", (8.3, 0.0, 0.2), (8.5, 0.3, 0.4))):
        a_built_box(stage, f"/{TOY}/Objects/{name}", low, high)
    in_desk = {"how": "within", "holder": ["desk_3"], "why": "within desk: the plan lays it inside"}
    things = [{"name": "monitor_9", "row": "monitor", "on": on_third},
              {"name": "paper_9", "row": "paper", "on": {"how": "top", "holder": ["monitor_9"]}},
              {"name": "lamp_9", "row": "lamp", "on": on_third},
              {"name": "keyboard_9", "row": "keyboard", "on": in_desk},
              {"name": "bin_9", "row": "bin", "on": in_desk}]
    assert all(built_tops.held_on(thing) for thing in things)
    assert not built_tops.held_on({"name": "jar_1", "on": {"how": "within", "holder": ["shelf_1"],
                                                           "why": "on the shelves of shelf: its reading says so"}})
    fits = {fit["name"]: fit for fit in built_tops.let_down(stage, TOY, things)}
    assert sorted(fits) == ["keyboard_9", "lamp_9", "monitor_9"], fits  # the paper carried on its monitor
    laid = {name: fitting.world_box(stage, f"/{TOY}/Objects/{name}") for name in ("monitor_9", "paper_9", "lamp_9",
                                                                                  "keyboard_9", "bin_9", "desk_3")}
    assert np.allclose(laid["monitor_9"][0], (8.1, 0.75, 0.1)) and fits["monitor_9"]["top at"] == 0.75, laid
    assert np.allclose(laid["paper_9"][0], (8.2, 1.05, 0.15)), laid["paper_9"]
    assert np.allclose(laid["lamp_9"][0][1], 0.75) and laid["lamp_9"][1][2] <= 0.5 + 1e-6, laid["lamp_9"]
    assert np.allclose(laid["keyboard_9"][0], (8.5, 0.75, 0.05)) and np.allclose(laid["bin_9"][0], (8.3, 0.0, 0.2))
    on_desk_laid = {"objects": [{"name": name, "low": low, "high": high} for name, (low, high) in laid.items()],
                    "fitted": list(fits.values())}
    assert fitting.held_faults({"objects": things[:1] + things[2:4]}, on_desk_laid) == []
    # workshop's seventh storage box, its shelving units' tops full, straddled their meeting and tipped: a crate laid
    # over the desk's back divider, the desk's slab full of plates, stands on the nearest plate laid there before it
    def faced(path, bounds):
        made = trimesh.creation.box(bounds=bounds)
        UsdGeom.Xform.Define(stage, path).AddTransformOp().Set(Gf.Matrix4d(1.0))
        geo = UsdGeom.Mesh.Define(stage, f"{path}/geo")
        geo.CreatePointsAttr([tuple(map(float, point)) for point in made.vertices])
        geo.CreateFaceVertexCountsAttr([3] * len(made.faces))
        geo.CreateFaceVertexIndicesAttr([int(index) for index in made.faces.ravel()])

    on_full = {"how": "top", "holder": ["desk_3"]}
    trays = [((8.0, 0.75, 0.0), (8.5, 0.8, 0.45)), ((8.5, 0.75, 0.0), (9.0, 0.8, 0.45))]
    for number, bounds in enumerate(trays):
        faced(f"/{TOY}/Objects/plate_{number}", bounds)
    a_built_box(stage, f"/{TOY}/Objects/crate_9", (8.1, 1.2, 0.45), (8.4, 1.3, 0.6))
    crowd = [{"name": f"plate_{number}", "row": "plate", "on": on_full} for number in range(2)] + [
        {"name": "crate_9", "row": "crate", "on": on_full}]
    crated = {fit["name"]: fit for fit in built_tops.let_down(stage, TOY, crowd)}
    assert list(crated) == ["crate_9"] and np.isclose(crated["crate_9"]["top at"], 0.8), crated
    assert "onto plate_0's built surface" in crated["crate_9"]["words"], crated
    # quarters' mug, its desk's top at its spot no rest, went 0.3 m down onto the shelf under the top: a box over a
    # slab with a shelf under it and a 4 cm post through its spot slides along the slab, never down onto the shelf
    shelved_slab = trimesh.util.concatenate([trimesh.creation.box(bounds=bounds) for bounds in (
        [(0.0, 0.0, 0.0), (1.0, 0.03, 0.6)], [(0.0, -0.3, 0.0), (1.0, -0.28, 0.6)],
        [(0.48, 0.03, 0.28), (0.52, 0.23, 0.32)])])
    found, slid = built_tops.spot(shelved_slab, (0.4, 0.23, 0.2), (0.6, 0.43, 0.4),
                                  (np.zeros(3), np.array([1.0, 0.23, 0.6])))
    assert np.isclose(found[1], 0.03) and slid > 0.0 and (found[0] + 0.1 <= 0.48 or found[0] - 0.1 >= 0.52
                                                          or found[2] + 0.1 <= 0.28 or found[2] - 0.1 >= 0.32), found
    # old_station (2026-11-12): sandbags laid at the corners of its modules' curved tops floated 0.06 to 1.03 m over
    # them, no flat spot under their inner half. A 1.2 x 0.3 x 0.6 m pile 0.4 m over the corner of a 2 m cylinder
    # lying along z (its crest at x 21, y 2), which let_down leaves, is slid toward the crest until its middle stands
    # 5 cm inside the crest's 0.48 m strip it touches within 3 cm (x 20.81 to 21.19), its foot let down onto the
    # crest; laid again, it stays where it rests.
    from score.stages.assembly import crest_tops
    tube = trimesh.creation.cylinder(radius=1.0, height=4.0, sections=64)
    tube.apply_translation((21.0, 1.0, 2.0))
    UsdGeom.Xform.Define(stage, f"/{TOY}/Objects/module_9").AddTransformOp().Set(Gf.Matrix4d(1.0))
    module = UsdGeom.Mesh.Define(stage, f"/{TOY}/Objects/module_9/geo")
    module.CreatePointsAttr([tuple(map(float, point)) for point in tube.vertices])
    module.CreateFaceVertexCountsAttr([3] * len(tube.faces))
    module.CreateFaceVertexIndicesAttr([int(index) for index in tube.faces.ravel()])
    faced(f"/{TOY}/Objects/bags_9", [(20.0, 2.4, 0.0), (21.2, 2.7, 0.6)])
    piled = [{"name": "bags_9", "row": "bags", "on": {"how": "top", "holder": ["module_9"]}}]
    assert built_tops.let_down(stage, TOY, piled) == []
    crest = crest_tops.laid_on(stage, TOY, piled)
    low, high = fitting.world_box(stage, f"/{TOY}/Objects/bags_9")
    assert [fit["name"] for fit in crest] == ["bags_9"] and abs(low[1] - 2.0) <= 0.01, (crest, low)
    assert 20.8 <= (low[0] + high[0]) / 2 <= 21.2 and np.isclose(crest[0]["top at"], low[1], atol=1e-3), (low, high)
    assert crest_tops.laid_on(stage, TOY, piled) == []
    # base (2026-11-12): its hangar's roof opening was asked of rest at 1.5 million spots on the hangar's top, none
    # holding it, 3 hours. The sieve's first pass (may_rest) leaves the spot found by asking rest at every one; on a
    # 20 m ridge, where the pile touches a strip too narrow to stand balanced on, it asks rest at none.
    import triage
    ridge = trimesh.convex.convex_hull(np.array([(x, y, z) for x, y in ((0, 0), (2, 0), (1, 1)) for z in (0, 20)],
                                                float))

    def pile_spot(holder, at):
        pile = trimesh.creation.box((1.2, 0.3, 0.6))
        pile.apply_translation(at)
        hold = tuple(holder.bounds)
        thing = (pile, np.asarray(triage.low_points(pile), float),
                 np.vstack([pile.vertices, pile.sample(crest_tops.EVERY, seed=0)]))
        fields = crest_tops.height_field(holder, hold), crest_tops.exact_field(holder, hold)
        return crest_tops.spot(thing, fields, tuple(pile.bounds), hold, [])
    sieve, rest, asked = crest_tops.may_rest, crest_tops.rest, []
    try:
        crest_tops.rest = lambda *args: asked.append(args) or rest(*args)
        on_ridge, ridge_asked = pile_spot(ridge, (1.0, 2.0, 10.0)), len(asked)
        sieved = pile_spot(tube, (20.6, 2.55, 0.3))
        crest_tops.may_rest = lambda low, weight, field, shifts: np.ones(len(shifts), bool)
        unsieved = pile_spot(tube, (20.6, 2.55, 0.3))
    finally:
        crest_tops.may_rest, crest_tops.rest = sieve, rest
    assert on_ridge is None and ridge_asked == 0, (on_ridge, ridge_asked)
    assert sieved is not None and np.array_equal(sieved, unsieved), (sieved, unsieved)
    # camp (settle@camp, 2026-11-12): its kitchen counter's model leans 16 degrees in its frame, its top one plane
    # sloping 18 degrees with no level spot, and the coffee maker let down onto it leaned 18.3 degrees. A 0.2 x 0.1 x
    # 0.2 m box laid upright 0.3 m over a 1 x 0.1 x 1 m slab turned 15 degrees about z is laid flush on it, its up
    # along the slab's, and laid again it is left; over a slab turned 30 degrees (past flush_tops.SLOPE_MOST) it is
    # left upright.
    from score.stages.assembly import flush_tops
    for number, (degrees, at) in enumerate(((15.0, 30.0), (30.0, 33.0))):
        slab = trimesh.creation.box(bounds=[(at, 0.9, 0.0), (at + 1.0, 1.0, 1.0)])
        slab.apply_transform(trimesh.transformations.rotation_matrix(np.radians(degrees), (0.0, 0.0, 1.0),
                                                                     (at + 0.5, 0.95, 0.5)))
        UsdGeom.Xform.Define(stage, f"/{TOY}/Objects/counter_{number}").AddTransformOp().Set(Gf.Matrix4d(1.0))
        counter = UsdGeom.Mesh.Define(stage, f"/{TOY}/Objects/counter_{number}/geo")
        counter.CreatePointsAttr([tuple(map(float, point)) for point in slab.vertices])
        counter.CreateFaceVertexCountsAttr([3] * len(slab.faces))
        counter.CreateFaceVertexIndicesAttr([int(index) for index in slab.faces.ravel()])
        faced(f"/{TOY}/Objects/maker_{number}", [(at + 0.4, 1.3, 0.4), (at + 0.6, 1.4, 0.6)])
    makers = [{"name": f"maker_{number}", "row": "maker", "on": {"how": "top", "holder": [f"counter_{number}"]}}
              for number in range(2)]
    flush = flush_tops.laid(stage, TOY, makers)
    turned = np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(f"/{TOY}/Objects/maker_0"))
                        .ComputeLocalToWorldTransform(0))[1, :3]
    slab_up = (-np.sin(np.radians(15.0)), np.cos(np.radians(15.0)), 0.0)
    assert [fit["name"] for fit in flush] == ["maker_0"] and np.degrees(np.arccos(np.clip(
        turned @ slab_up / np.linalg.norm(turned), -1.0, 1.0))) < 1.0, (flush, turned)
    assert flush_tops.laid(stage, TOY, makers) == []
    # greenhouse (settle@greenhouse, 2026-11-13): its desk's top is sloping bowls but for its front rim, and its four
    # computers were left over the bowls, leaning 51 degrees once let down. A desk whose top (x 40 to 41) is a 40
    # degree slope from 0.1 m at z 0 to 0.6 m at z 0.6, then a 0.14 m rim at 1 m to its front, z 0.74: a 0.2 m box laid
    # over the slope stands on the rim, its middle at z 0.65 to 0.69 (its weight triage.BALANCE inside what it
    # touches), its front past the desk's; crest_tops keeps its footprint within the desk (its middle at most 0.64,
    # 0.04 inside the rim) and leaves it. Laid again it is left.
    from score.stages.assembly import fine_tops
    rim = trimesh.util.concatenate([
        trimesh.convex.convex_hull(np.array([(x, y, z) for x in (40.0, 41.0) for y, z in (
            (0.0, 0.0), (0.1, 0.0), (0.6, 0.6), (0.0, 0.6))], float)),
        trimesh.creation.box(bounds=[(40.0, 0.0, 0.6), (41.0, 1.0, 0.74)])])
    UsdGeom.Xform.Define(stage, f"/{TOY}/Objects/desk_40").AddTransformOp().Set(Gf.Matrix4d(1.0))
    desk = UsdGeom.Mesh.Define(stage, f"/{TOY}/Objects/desk_40/geo")
    desk.CreatePointsAttr([tuple(map(float, point)) for point in rim.vertices])
    desk.CreateFaceVertexCountsAttr([3] * len(rim.faces))
    desk.CreateFaceVertexIndicesAttr([int(index) for index in rim.faces.ravel()])
    faced(f"/{TOY}/Objects/computer_40", [(40.4, 1.2, 0.3), (40.6, 1.4, 0.5)])
    computers = [{"name": "computer_40", "row": "computer", "on": {"how": "top", "holder": ["desk_40"]}}]
    assert crest_tops.laid_on(stage, TOY, computers) == []
    fine = fine_tops.laid(stage, TOY, computers)
    low, high = fitting.world_box(stage, f"/{TOY}/Objects/computer_40")
    assert [fit["name"] for fit in fine] == ["computer_40"] and abs(low[1] - 1.0) <= 0.01, (fine, low)
    assert 0.65 - 1e-6 <= (low[2] + high[2]) / 2 <= 0.69 and high[2] > 0.74, (low, high)
    assert fine_tops.laid(stage, TOY, computers) == []
    # its railings run diagonally, their world boxes over the desks: a thing meets a thin one turned off the floor's
    # axes by its outline (a 0.1 m strip along x = z), never by the box round it.
    diagonal = (np.array([0.0, 0.0, 0.0]), np.array([4.0, 1.0, 4.0]),
                np.array([(0.05, -0.05), (4.05, 3.95), (3.95, 4.05), (-0.05, 0.05)]))
    assert not fine_tops.meets(np.array([2.5, 0.0, 0.5]), np.array([3.0, 0.5, 1.0]), diagonal)
    assert fine_tops.meets(np.array([1.8, 0.0, 1.8]), np.array([2.3, 0.5, 2.3]), diagonal)
    assert fine_tops.meets(np.array([2.5, 0.0, 0.5]), np.array([3.0, 0.5, 1.0]), (*diagonal[:2], None))
    # quarters (settle@quarters, 2026-11-13): a book laid 9.5 mm deep over a 1.3 cm wrench on its desk (fitting's
    # BOARD_CLEAR lets a box 1 cm into another) rested on the desk alone and leaned 7.9 degrees on the wrench. A thing
    # is judged on what it stands among lower than its top too: a 0.2 m book with one edge over a 1.3 cm wrench on a
    # slab, leaning 3.4 degrees on it as laid, is laid where it rests among them, the wrench left; laid again both are
    # left.
    faced(f"/{TOY}/Objects/desk_70", [(70.0, 0.0, 0.0), (71.0, 0.03, 0.6)])
    faced(f"/{TOY}/Objects/wrench_70", [(70.4, 0.03, 0.15), (70.57, 0.043, 0.2)])
    faced(f"/{TOY}/Objects/book_70", [(70.39, 0.0335, 0.15), (70.59, 0.0765, 0.35)])
    over = [{"name": name, "row": name.split("_")[0], "on": {"how": "top", "holder": ["desk_70"]}}
            for name in ("wrench_70", "book_70")]
    under = trimesh.util.concatenate([fitting.surface_mesh(stage, f"/{TOY}/Objects/{name}")
                                      for name in ("desk_70", "wrench_70")])
    among = crest_tops.exact_field(under, fitting.world_box(stage, f"/{TOY}/Objects/desk_70"))
    assert not crest_tops.stands(fitting.surface_mesh(stage, f"/{TOY}/Objects/book_70"), among, np.zeros(3))
    fine = fine_tops.laid(stage, TOY, over)
    assert [fit["name"] for fit in fine] == ["book_70"], fine
    assert crest_tops.stands(fitting.surface_mesh(stage, f"/{TOY}/Objects/book_70"), among, np.zeros(3))
    assert fine_tops.laid(stage, TOY, over) == []
    # its two wrenches, 1.3 cm thick, were let down one 9 mm into the other, and a book's corner 5 mm into one: boxes
    # reach into each other past a quarter of the thinner one's size along a way where that is under BOARD_CLEAR;
    # 0.2 m boxes 9 mm into each other do not
    thin = (np.array([0.0, 0.0, 0.0]), np.array([0.17, 0.013, 0.05]))
    assert fitting.meets_any(np.array([0.0, 0.004, 0.04]), np.array([0.17, 0.017, 0.09]), [thin])
    assert fitting.meets_any(np.array([0.13, 0.008, 0.03]), np.array([0.29, 0.05, 0.23]), [thin])  # a book's corner
    assert not fitting.meets_any(np.array([0.0, 0.013, 0.0]), np.array([0.17, 0.026, 0.05]), [thin])
    assert not fitting.meets_any(np.array([0.0, 0.191, 0.0]), np.array([0.2, 0.39, 0.2]), [
        (np.zeros(3), np.array([0.2, 0.2, 0.2]))])
    # its plant pot, stacked on a book (built_tops.stacked_spot) when the desk had no spot left, was left 0.69 m over
    # the desk's corner once the book was laid on a spot where it rests. What stands on a thing's top moves with it: a
    # cup on a computer over the slope of a desk whose rim (x 42 to 42.3) has no room beside it rides it onto the rim.
    assert fitting.with_stacked(stage, TOY, {"desk_40": ["computer_40"]}, ["computer_40", "paper_9"]) == {
        "desk_40": ["computer_40"]}
    shifted = rim.copy()
    shifted.vertices[:, 0] = np.where(shifted.vertices[:, 0] > 40.5, 42.3, 42.0)
    UsdGeom.Xform.Define(stage, f"/{TOY}/Objects/desk_41").AddTransformOp().Set(Gf.Matrix4d(1.0))
    desk = UsdGeom.Mesh.Define(stage, f"/{TOY}/Objects/desk_41/geo")
    desk.CreatePointsAttr([tuple(map(float, point)) for point in shifted.vertices])
    desk.CreateFaceVertexCountsAttr([3] * len(shifted.faces))
    desk.CreateFaceVertexIndicesAttr([int(index) for index in shifted.faces.ravel()])
    faced(f"/{TOY}/Objects/computer_41", [(42.05, 1.2, 0.3), (42.25, 1.4, 0.5)])
    faced(f"/{TOY}/Objects/cup_41", [(42.09, 1.4, 0.34), (42.21, 1.5, 0.46)])
    assert fitting.with_stacked(stage, TOY, {}, ["computer_41", "cup_41"]) == {"computer_41": ["cup_41"]}
    riding = [{"name": name, "row": name.split("_")[0], "on": {"how": "top", "holder": ["desk_41"]}}
              for name in ("computer_41", "cup_41")]
    fine = fine_tops.laid(stage, TOY, riding)
    low, high = fitting.world_box(stage, f"/{TOY}/Objects/computer_41")
    cup_low, cup_high = fitting.world_box(stage, f"/{TOY}/Objects/cup_41")
    assert [fit["name"] for fit in fine] == ["computer_41"] and abs(low[1] - 1.0) <= 0.01, (fine, low)
    assert np.isclose(cup_low[1], high[1]) and np.allclose((cup_low + cup_high)[[0, 2]] / 2,
                                                           (low + high)[[0, 2]] / 2), (cup_low, low, high)
    # a third thing, over the slope, the rim and the computer's top full, stands on the cup's top where it rests
    # there; laid again, all three are left
    faced(f"/{TOY}/Objects/cup_42", [(42.09, 1.2, 0.2), (42.21, 1.3, 0.32)])
    riding.append({"name": "cup_42", "row": "cup", "on": {"how": "top", "holder": ["desk_41"]}})
    fine = fine_tops.laid(stage, TOY, riding)
    stack_low = fitting.world_box(stage, f"/{TOY}/Objects/cup_42")[0]
    assert [fit["name"] for fit in fine] == ["cup_42"] and "onto cup_41's top" in fine[0]["words"], fine
    assert 0.0 <= stack_low[1] - fitting.world_box(stage, f"/{TOY}/Objects/cup_41")[1][1] <= 0.01, stack_low
    assert fine_tops.laid(stage, TOY, riding) == []
    # lab (settle@lab, 2026-11-14): its two monitors, laid at one corner of its desk bake 20 cm into each other, each
    # rested on the desk alone and was left, and the resting check read each one's foot inside the other as its
    # support, leaning 8.6 and 6.4 degrees. A thing resting where it is laid that reaches into another laid on its
    # holders as tall as it is laid again on the nearest spot clear of it: two 0.3 m boxes 0.1 m into each other on a
    # slab, the first laid clear, the second then left, and left again laid again.
    faced(f"/{TOY}/Objects/desk_80", [(80.0, 0.0, 0.0), (81.0, 0.03, 0.6)])
    faced(f"/{TOY}/Objects/monitor_80", [(80.1, 0.03, 0.1), (80.4, 0.33, 0.4)])
    faced(f"/{TOY}/Objects/monitor_81", [(80.3, 0.03, 0.2), (80.6, 0.33, 0.5)])
    crowded = [{"name": name, "row": "monitor", "on": {"how": "top", "holder": ["desk_80"]}}
               for name in ("monitor_80", "monitor_81")]
    fine = fine_tops.laid(stage, TOY, crowded)
    boxes = [fitting.world_box(stage, f"/{TOY}/Objects/{name}") for name in ("monitor_80", "monitor_81")]
    assert [fit["name"] for fit in fine] == ["monitor_80"] and not fitting.reaches_into(*boxes[0], boxes[1]), fine
    assert abs(boxes[0][0][1] - 0.03) <= 0.01 and np.allclose(boxes[1][0], (80.3, 0.03, 0.2)), boxes
    again = fine_tops.laid(stage, TOY, crowded)
    boxes = [fitting.world_box(stage, f"/{TOY}/Objects/{name}") for name in ("monitor_80", "monitor_81")]
    assert "monitor_81" not in [fit["name"] for fit in again] and not fitting.reaches_into(*boxes[0], boxes[1]), again
    # its mouse (10 x 6 cm), a 5 cm wrench and a plant pot were never found a spot where they rest: no point of a 6 cm
    # thing is BALANCE (5 cm) inside it. A 10 x 6 cm box on a flat slab rests there, its weight a quarter of its 6 cm
    # inside what it touches; hung 5 cm past the slab's edge it does not.
    import resting
    slab = trimesh.creation.box(bounds=[(60.0, 0.0, 0.0), (61.0, 0.03, 0.6)])
    flat = crest_tops.exact_field(slab, tuple(slab.bounds))
    mouse = trimesh.creation.box(bounds=[(60.4, 0.035, 0.2), (60.5, 0.075, 0.26)])
    low_points = np.asarray(triage.low_points(mouse), float)
    weight = resting.weight_at(mouse)
    assert np.isclose(crest_tops.balance(mouse.vertices), 0.015) and crest_tops.balance(slab.vertices) == 0.05
    assert crest_tops.stands(mouse, flat, np.zeros(3)) and crest_tops.rest(low_points, np.asarray(
        mouse.vertices), weight, flat, np.zeros(2)) is not None, crest_tops.balance(mouse.vertices)
    assert crest_tops.may_rest(low_points, weight, flat, np.zeros((1, 2)))[0]
    assert not crest_tops.stands(mouse, flat, np.array([0.55, 0.0, 0.0]))
    # its railing row, 1 m tall, built 4.5 m (its bake's parts from before railing_hold) as 9.4 m chords whose ends ran
    # 0.12 and 0.14 m into its walls, the first and fifth over its stair's opening once held. A chord 9.4 m along x = z,
    # 4.5 m tall, on a floor at 3 m that ends 0.9 m short of its middle, one end in a wall box, is held to 1 m, slid
    # back along itself until its weight stands within the check's 5 cm of the floor's edge, and drawn back until it
    # stands railings_held.CLEAR off the wall; laid again it is left. railing_hold's rule holds: a stair's railing,
    # which climbs, and a squat one are not held.
    from scipy.spatial import ConvexHull
    from score.stages.assembly import railings_held
    import score.stages.props.railing_hold as railing_hold
    import score.stages.props.thin_straight as thin_straight
    railing_row = {"id": "railing", "name": "metal railings", "noun": "railing", "anchor": "on:upper_floor",
                   "size": [50.0, 0.1, 1.0]}
    for kept in (railing_row, {**railing_row, "name": "stair railing", "anchor": "on:staircase"},
                 {**railing_row, "size": [2.0, 1.0, 1.0]}, {**railing_row, "name": "metal pipe", "noun": "pipe"}):
        assert railings_held.held(kept) == (thin_straight.profile(kept) == "railing" and not railing_hold.climbs(kept)
                                            and thin_straight.slender(kept["size"])), kept
    assert railings_held.held(railing_row) and not railings_held.held({**railing_row, "anchor": "on:staircase"})
    way = np.array([1.0, 0.0, 1.0]) / np.sqrt(2.0)
    chord = trimesh.creation.box(extents=(9.4, 4.5, 0.1))
    chord.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-45.0), (0.0, 1.0, 0.0)))
    chord.apply_translation((0.0, 5.25, 0.0))
    wall = ConvexHull(np.array([(x, y, z) for x in (2.6, 4.0) for y in (2.8, 8.0) for z in (2.0, 5.0)], float))

    def under(points):
        return np.where(points @ way > -0.9, np.inf, np.abs(points[:, 1] - 3.0))
    whole, words = railings_held.change(chord, railing_row, [wall], under)
    laid_chord = chord.copy()
    laid_chord.apply_transform(whole.T)
    assert np.isclose(np.ptp(laid_chord.vertices[:, 1]), 1.0) and np.isclose(laid_chord.bounds[0, 1], 3.0), words
    assert not railings_held.inside(laid_chord.vertices, [wall]) and "slid -0." in words, words
    assert railings_held.outside_by(laid_chord, under) <= 0.05 < railings_held.outside_by(chord, under), words
    assert railings_held.change(laid_chord, railing_row, [wall], under) is None


def test_a_kit_piece_moved_since_the_seed_stands_at_its_kit_spot(tmp_path, monkeypatch):
    """Fault (2026-10-12): the garage's fourth pressure gauge moved off the big door's track in its kit, yet the
    assembly kept the seed's object where the old kit put it. The second crate's kit spot moved to (5, 0, 2): it
    stands there; the first, unmoved, keeps its transform, and a second run moves nothing.
    Break: score/stages/assembly/record.py: `if all(abs(now[row][column] - then[row][column]) <= SAME for row in
        range(4) for column in range(4)):` -> `if True:`"""
    import ground
    from pxr import UsdGeom
    monkeypatch.setattr(ground, "place_ground", lambda place, seat: None)  # laid flat, as export.py --flat lays it
    stage = place_of(tmp_path, [("crate", "box", (0, 0, 0)), ("crate", "box", (3, 0, 0))], [row("crate")])
    kit = json.loads((tmp_path / "kit.json").read_text())
    kit["pieces"][1]["at"] = [5.0, 0.0, 2.0]
    (tmp_path / "kit.json").write_text(json.dumps(kit))
    said = record.relay_kit({"kit": tmp_path / "kit.json"}, stage.parent, PLACE)
    assert said == "; kit: 1 pieces laid at their kit spot (crate_2)", said
    held = opened(stage)
    moved = UsdGeom.Xformable(held.GetPrimAtPath(f"/{PLACE}/Objects/crate_2"))
    assert tuple(moved.ComputeLocalToWorldTransform(0).ExtractTranslation()) == (5.0, 0.0, 2.0)
    assert record.relay_kit({"kit": tmp_path / "kit.json"}, stage.parent, PLACE) == ""


def a_sound_output(folder, uses):
    """A sound stage's output: hum and tone, each one file, played by `uses`."""
    for name in ("hum", "tone"):
        (folder / f"files/sound/{name}.ogg").parent.mkdir(parents=True, exist_ok=True)
        (folder / f"files/sound/{name}.ogg").write_bytes(name.encode())
    played = {name: {"files": [f"files/sound/{name}.ogg"], "volume_db": -6.0, "bus": "ambience" if name == "tone"
                     else "machines", "loops": True, "reach": 8.0, "ground_thud": False} for name in ("hum", "tone")}
    (folder / "sound.json").write_text(json.dumps({"place": TOY, "sounds": played, "uses": uses}))
    return folder


# --- the layer stages taken over a read-only seed ---------------------------------------------------------------------

# The sound output's uses over the layered seed: the room tone, the hum at the fan's row, the door's sound at its own
# second, a hum on a row the stage lacks (the pump), and a motion's sound on the door the fitting left out (hangar's
# second crane, 2026-11-11: inactive, it crashed the assembly defining its sound under it).
USES = [{"sound": "tone", "role": "room", "on": None, "from": "places.json"},
        {"sound": "hum", "role": "object", "on": "fan", "from": "row fan"},
        {"sound": "hum", "role": "motion", "on": f"/{TOY}/Objects/door_1", "at": 2.5, "loops_until": None,
         "from": "door"},
        {"sound": "hum", "role": "object", "on": "pump", "from": "row pump"},
        {"sound": "hum", "role": "motion", "on": f"/{TOY}/Objects/door_2", "at": 1.0, "loops_until": None,
         "from": "door"}]
# Each layer stage's lamps: {lamp: {frame or None (a plain value): strength}}; the motion keys the cycle lamp 0 then 50
# at frame 12 (the airlock's cycle light, 2026-10-16) and the light sets both lamps 20.
LAMPS = {"effects": {}, "light": {"cycle": {None: 20.0}, "steady": {None: 20.0}},
         "motion": {"cycle": {0: 0.0, 12: 50.0}}}


def a_layered_seed(root):
    """The toy seed as a store checkout holds it (every file read-only, no assets/ folder), its base also holding a
    second door the fitting left out (inactive), and the accepted outputs over it: the record (ONE_LAMP), an effects
    layer, a motion layer of 480 frames and a light layer (LAMPS, the light's earth picture under assets/light), each
    read-only, and a sound output played by USES; the seed and make_from_seed's inputs."""
    from pxr import Usd, UsdGeom, UsdLux
    seed = a_toy(root / "store" / TOY)
    base = Usd.Stage.Open(str(seed.parent / "layers/base.usda"))
    UsdGeom.Xform.Define(base, f"/{TOY}/Objects/door_2").GetPrim().SetActive(False)
    base.GetRootLayer().Save()
    for path in seed.parent.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    for name, lamps in LAMPS.items():
        (root / name / "layers").mkdir(parents=True)
        stage = Usd.Stage.CreateNew(str(root / name / f"layers/{name}.usda"))
        for lamp, keys in lamps.items():
            strength = UsdLux.SphereLight.Define(stage, f"/{TOY}/Lights/{lamp}").CreateIntensityAttr()
            for frame, value in keys.items():
                strength.Set(value) if frame is None else strength.Set(value, frame)
        if name == "motion":
            layer = stage.GetRootLayer()
            layer.timeCodesPerSecond, layer.startTimeCode, layer.endTimeCode = 24.0, 0.0, 480.0
        stage.GetRootLayer().Save()
        (root / name / f"layers/{name}.usda").chmod(0o444)
    (root / "light/assets/light").mkdir(parents=True)
    (root / "light/assets/light/earth.png").write_bytes(b"png")
    (root / "surfaces.json").write_text(json.dumps({}))
    return seed, {"seed": seed.parent, "effects-layer": root / "effects", "motion": root / "motion",
                  "light": root / "light", "sound": a_sound_output(root / "sound", USES),
                  "sounds": root / "none.json", "surfaces": root / "surfaces.json", **a_record(root, ONE_LAMP)}


# --- the made ground's surface ---------------------------------------------------------------------------------------

# A made ground's triangle and the libraries a ground row takes its surface from: the toy's own (it holds
# lunar_regolith in the seed's Library), and the base's, its recipe and token laid under the toy's Library.
TRIANGLE = (np.array([[0, 0, 0], [1, 0, 0], [0, 0, 1]], float), np.array([[0, 2, 1]]))
OWN_LIBRARY = {"kinds": {"ground": ["lunar_regolith"], "wall": ["hull_paint"]}}
BASE_LIBRARY = {"recipes": {"regolith": {"roughness": 0.95}}, "tokens": {"regolith-tan": "#8a7350"},
                "families": {"regolith": {"variants": {"lunar_regolith": {"recipe": "regolith",
                                                                          "token": "regolith-tan"}}}},
                "kinds": {"ground": ["lunar_regolith"]}}
# Each toy on the base's ground (the base's plan holding it, its inventory the ground row lunar_surface): its own
# inventory's rows, the seed's Library holding lunar_regolith or not, its terrain's made grounds and water, its
# surface libraries; then the other scenes it and the base read beside (ground_scenes), the made grounds bound to
# Library/lunar_regolith (and its recipe), the water left with its finish missing, the placeholder gate's faults.
GROUNDED = [
    # Hub (#36, assembly@hub placeholders): the terrain's made ground came in as /<place>/Outside/near and far, its
    # finish named missing, drawn with no material. Its own row lunar_surface (a ground) takes its own library's
    # lunar_regolith; the sea, which the library gives none, keeps its finish named missing. With its own ground row
    # and water it reads no other scene's library; the base, with no water of its own, reads its sea's beside.
    {"name": "the hub's own library", "rows": [{"id": "lunar_surface", "noun": "ground", "terrain": True},
                                               {"id": "sea", "noun": "sea", "terrain": True}],
     "seed library": True, "grounds": ("near", "far"), "sea": True, "libraries": {"surface-library": OWN_LIBRARY},
     "beside": [], "base beside": [TOY], "bound": ("near", "far"), "faults": [f"/{TOY}/Outside/water"]},
    # Airlock (#36): a room the base holds stands on the base's made ground, which its own inventory and library lack,
    # so it stayed drawn with no material: it reads the base's library beside, lays its surface under its own Library
    # and binds the ground to it.
    {"name": "the airlock on the base's ground", "rows": [{"id": "hatch", "noun": "hatch"}], "seed library": False,
     "grounds": ("near",), "sea": False, "libraries": {"surface-library@base": BASE_LIBRARY}, "beside": ["base"],
     "base beside": [],
     "bound": ("near",), "recipe": "regolith", "faults": []},
]
# What a scene library gives a ground row (ground_surface): the square's, asked for its floor and its sea; its plaza, a
# made ground it was asked no kind for, takes its floor, the red dunes, a natural ground it names no kind for, none.
SQUARE = {"kinds": {"floor": ["plaza_floor_tiles"], "sea": ["bay_water"]}}
GROUND_SURFACE = [({"id": "plaza", "name": "main plaza", "noun": "plaza"}, "plaza_floor_tiles"),
                  ({"id": "sea", "name": "sea", "noun": "sea"}, "bay_water"),
                  ({"id": "dunes", "name": "red dunes", "noun": "dunes"}, None)]


def a_grounded_toy(root, case, monkeypatch):
    """A GROUNDED case's read-only toy seed on the base's ground (the creator's kept design under root/home/design,
    design_layers.KEPT pointed there), its terrain's made ground and its libraries; make_from_seed's inputs."""
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
    from score.stages import design_layers
    from score.stages.terrain import outside
    design = root / "home/design"
    for folder in ("plans", "sky", "inventory"):
        (design / folder).mkdir(parents=True)
    (design / "plans/base.json").write_text(json.dumps({"w": 20.0, "d": 20.0, "structure": ["lunar_surface"],
                                                        "holds": [{"place": TOY, "x": 2.0, "y": 2.0}]}))
    (design / f"plans/{TOY}.json").write_text(json.dumps({"w": 4.0, "d": 4.0}))
    (design / "sky/base.json").write_text(json.dumps({"top": "base", "site": {"on": "moon", "latitude": 0.0,
                                                                             "longitude": 0.0},
                                                      "setting": {"bodies": [{"body": "moon", "radius_km": 1737.4}]}}))
    (design / "inventory/base.json").write_text(json.dumps({"rows": [
        {"id": "lunar_surface", "noun": "ground", "terrain": True}]}))
    (design / f"inventory/{TOY}.json").write_text(json.dumps({"rows": case["rows"]}))
    monkeypatch.setattr(design_layers, "KEPT", design / "inventory")
    seed = a_toy(root / "store" / TOY).parent
    if case["seed library"]:
        base = Usd.Stage.Open(str(seed / "layers/base.usda"))
        shader = UsdShade.Shader.Define(base, f"/{TOY}/Library/lunar_regolith/surface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.34, 0.28, 0.22))
        UsdShade.Material.Define(base, f"/{TOY}/Library/lunar_regolith").CreateSurfaceOutput().ConnectToSource(
            shader.ConnectableAPI(), "surface")
        base.GetRootLayer().Save()
    for path in seed.rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    inputs = a_record(root, ONE_LAMP)
    (root / "terrain/moon/places").mkdir(parents=True)
    ground = Usd.Stage.CreateNew(str(root / "terrain/moon/places" / f"{TOY}.usdc"))
    outside.write(ground, TOY, dict.fromkeys(case["grounds"], TRIANGLE), "lunar_surface", ["regolith", "the test's"],
                  *([(*TRIANGLE, "sea", ["ocean", "the test's"])] if case["sea"] else []))
    ground.GetRootLayer().Save()
    (root / "terrain/moon/places" / f"{TOY}.usdc").chmod(0o444)
    for name, content in case["libraries"].items():
        (root / name).mkdir()
        (root / name / "materials.json").write_text(json.dumps(content))
        inputs[name] = root / name
    (root / "surfaces.json").write_text(json.dumps({}))
    return {"seed": seed, "surfaces": root / "surfaces.json", "inventories": design / "inventory", **inputs}


def a_thing_on_legs(folder, name, short, linked_to=None):
    """A place `toy` in `folder` laying one floor thing `name` from its own asset assets/<name>.usdc: a
    2 m square top on four 10 cm square legs 0.6 m long, the leg at (+0.9, +0.9) ending `short` metres over the
    others, with its collision hull; the asset a hard link to `linked_to`'s when given. The root's path."""
    parts = [trimesh.creation.box((2.0, 0.1, 2.0), trimesh.transformations.translation_matrix((0, 0.65, 0)))]
    for x in (-0.9, 0.9):
        for z in (-0.9, 0.9):
            lift = short if (x, z) == (0.9, 0.9) else 0.0
            parts.append(trimesh.creation.box((0.1, 0.6 - lift, 0.1), trimesh.transformations.translation_matrix(
                (x, 0.3 + lift / 2, z))))
    return a_floor_thing(folder, name, trimesh.util.concatenate(parts), linked_to)


def a_floor_thing(folder, name, mesh, linked_to=None, beside=()):
    """A place `toy` in `folder` laying one floor thing `name` at (3, 0, -2) from its own asset assets/<name>.usdc
    holding `mesh` and its collision hull (a hard link to `linked_to`'s when given), and a box laid beside it for each
    (low, high) of `beside`, in the place's frame. The root's path."""
    from pxr import Sdf, Usd, UsdGeom, Vt
    import colliders
    asset = folder / "assets" / f"{name}.usdc"
    asset.parent.mkdir(parents=True, exist_ok=True)
    if linked_to is not None:
        asset.hardlink_to(linked_to)
    else:
        stage = Usd.Stage.CreateNew(str(asset))
        stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{name}").GetPrim())
        geo = UsdGeom.Mesh.Define(stage, f"/{name}/geo")
        geo.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(mesh.vertices, dtype=np.float32)))
        geo.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(mesh.faces), 3, dtype=np.int32)))
        geo.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(mesh.faces, dtype=np.int32).reshape(-1)))
        geo.CreateExtentAttr([tuple(mesh.bounds[0]), tuple(mesh.bounds[1])])
        colliders.hull(stage, f"/{name}/collision", np.asarray(mesh.vertices))
        stage.GetRootLayer().Save()
    root = folder / f"{TOY}.usda"
    stage = Usd.Stage.CreateNew(str(root))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{TOY}").GetPrim())
    thing = UsdGeom.Xform.Define(stage, f"/{TOY}/Objects/{name}_1")
    thing.AddTranslateOp().Set((3.0, 0.0, -2.0))
    thing.GetPrim().GetReferences().AddReference(f"./assets/{name}.usdc")
    thing.GetPrim().CreateAttribute("score:anchor", Sdf.ValueTypeNames.String).Set("floor")
    for number, (low, high) in enumerate(beside):
        a_built_box(stage, f"/{TOY}/Objects/crate_{number}", low, high)
    stage.GetRootLayer().Save()
    return root


def a_sloped_place(folder, inside=False):
    """A place `toy` in `folder` on a made ground rising 0.2 m a metre north (-z) from 1 m at z 0
    (/toy/Outside/near on a layer of its own) with a built deck over x 6 to 10: a 1 m box laid at the floor (0 m) at
    x 0 holding a 0.2 m cube on its top, a 1 m box over the deck at x 8, a 1 m box the record lays on a level 3.3 m
    up at x -6, its record (`inside` as given) and laid.json.
    The root's path."""
    from pxr import Gf, Sdf, Usd, UsdGeom
    (folder / "layers").mkdir(parents=True)
    ground = Usd.Stage.CreateNew(str(folder / "layers/ground.usda"))
    across, along = np.meshgrid(np.linspace(-10, 10, 21), np.linspace(-10, 10, 21))
    points = np.c_[across.ravel(), 1.0 - 0.2 * along.ravel(), along.ravel()]
    corners = [triangle for row in range(20) for column in range(20) for triangle in (
        (row * 21 + column, row * 21 + column + 1, (row + 1) * 21 + column + 1),
        (row * 21 + column, (row + 1) * 21 + column + 1, (row + 1) * 21 + column))]
    near = UsdGeom.Mesh.Define(ground, f"/{TOY}/Outside/near")
    near.CreatePointsAttr([tuple(point) for point in points])
    near.CreateFaceVertexCountsAttr([3] * len(corners))
    near.CreateFaceVertexIndicesAttr([index for triangle in corners for index in triangle])
    ground.GetRootLayer().Save()
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    things = {"crate_1": ((-0.5, 0.0, -0.5), (0.5, 1.0, 0.5)), "cube_1": ((-0.1, 1.0, -0.1), (0.1, 1.2, 0.1)),
              "case_1": ((7.5, 0.0, -0.5), (8.5, 1.0, 0.5)), "podium_1": ((-6.5, 3.3, -0.5), (-5.5, 4.3, 0.5))}
    for name, (low, high) in things.items():
        a_built_box(base, f"/{TOY}/Objects/{name}", low, high)
        box = trimesh.creation.box(bounds=[low, high])
        UsdGeom.Mesh(base.GetPrimAtPath(f"/{TOY}/Objects/{name}/geo")).GetPointsAttr().Set(
            [tuple(point) for point in box.vertices])
    deck = UsdGeom.Mesh.Define(base, f"/{TOY}/Shell/deck_1/geo")
    deck.CreatePointsAttr([(6.0, -0.1, -2.0), (10.0, -0.1, -2.0), (10.0, -0.1, 2.0), (6.0, -0.1, 2.0)])
    deck.CreateFaceVertexCountsAttr([4])
    deck.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    base.GetRootLayer().Save()
    root = Usd.Stage.CreateNew(str(folder / f"{TOY}.usda"))
    root.GetRootLayer().subLayerPaths = ["./layers/ground.usda", "./layers/base.usda"]
    root.SetDefaultPrim(UsdGeom.Xform.Define(root, f"/{TOY}").GetPrim())
    root.GetRootLayer().Save()
    (folder / record.RECORD).write_text(json.dumps({"place": TOY, "inside": inside, "objects": [
        {"name": "crate_1", "row": "crate", "at": [0, 0, 0]}, {"name": "case_1", "row": "case", "at": [8, 0, 0]},
        {"name": "podium_1", "row": "podium", "at": [-6, 3.3, 0]},
        {"name": "cube_1", "row": "cube", "on": {"how": "top", "holder": ["crate_1"]}}]}))
    (folder / made_waiting.LAID).write_text(json.dumps({"objects": [
        {"name": name, "low": list(low), "high": list(high)} for name, (low, high) in things.items()]}))
    return folder / f"{TOY}.usda"


def a_faced_place(folder):
    """A place `toy` in `folder` on flat made ground (y 0, /toy/Outside/near on a layer of its own): a 1 m crate at the
    floor with a 0.1 m step beside its east side, a panel laid on that side 0.5 m up holding a 0.1 m cube on its top,
    a second panel of its row within the crate on a 0.2 m shelf, a sign laid on its west side 0.6 m up, the sign
    row's only object, and a rail on its east side 0.75 m up that the panel's back rests on higher up (solar_panels_5
    touched its lander's side at one point); its record and laid.json. The root's path."""
    from pxr import Usd, UsdGeom
    (folder / "layers").mkdir(parents=True)
    ground = Usd.Stage.CreateNew(str(folder / "layers/ground.usda"))
    across, along = np.meshgrid(np.linspace(-5, 5, 11), np.linspace(-5, 5, 11))
    points = np.c_[across.ravel(), np.zeros(across.size), along.ravel()]
    corners = [triangle for row in range(10) for column in range(10) for triangle in (
        (row * 11 + column, row * 11 + column + 1, (row + 1) * 11 + column + 1),
        (row * 11 + column, (row + 1) * 11 + column + 1, (row + 1) * 11 + column))]
    near = UsdGeom.Mesh.Define(ground, f"/{TOY}/Outside/near")
    near.CreatePointsAttr([tuple(point) for point in points])
    near.CreateFaceVertexCountsAttr([3] * len(corners))
    near.CreateFaceVertexIndicesAttr([index for triangle in corners for index in triangle])
    ground.GetRootLayer().Save()
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    things = {"crate_1": ((-0.5, 0.0, -0.5), (0.5, 1.0, 0.5)), "shelf_1": ((-0.4, 0.1, -0.4), (0.4, 0.2, 0.4)),
              "panel_1": ((0.5, 0.5, -0.3), (0.6, 0.9, 0.3)), "cube_2": ((0.5, 0.9, -0.05), (0.6, 1.0, 0.05)),
              "panel_2": ((-0.2, 0.2, -0.3), (-0.1, 0.6, 0.3)), "sign_1": ((-0.6, 0.6, -0.2), (-0.5, 0.9, 0.2)),
              "step_1": ((0.5, 0.0, -0.4), (0.75, 0.1, 0.4)), "rail_1": ((0.5, 0.75, -0.35), (0.55, 0.8, 0.35))}
    for name, (low, high) in things.items():
        a_built_box(base, f"/{TOY}/Objects/{name}", low, high)
        box = trimesh.creation.box(bounds=[low, high])
        mesh = UsdGeom.Mesh(base.GetPrimAtPath(f"/{TOY}/Objects/{name}/geo"))
        mesh.GetPointsAttr().Set([tuple(point) for point in box.vertices])
        mesh.CreateFaceVertexCountsAttr([3] * len(box.faces))
        mesh.CreateFaceVertexIndicesAttr([int(index) for index in box.faces.ravel()])
    base.GetRootLayer().Save()
    root = Usd.Stage.CreateNew(str(folder / f"{TOY}.usda"))
    root.GetRootLayer().subLayerPaths = ["./layers/ground.usda", "./layers/base.usda"]
    root.SetDefaultPrim(UsdGeom.Xform.Define(root, f"/{TOY}").GetPrim())
    root.GetRootLayer().Save()
    (folder / record.RECORD).write_text(json.dumps({"place": TOY, "inside": False, "objects": [
        {"name": "crate_1", "row": "crate", "at": [0, 0, 0]}, {"name": "step_1", "row": "step", "at": [0.6, 0, 0]},
        {"name": "shelf_1", "row": "shelf", "on": {"how": "within", "holder": ["crate_1"]}},
        {"name": "panel_1", "row": "panel", "on": {"how": "face", "holder": ["crate_1"], "out": [1.0, 0.0]}},
        {"name": "cube_2", "row": "cube", "on": {"how": "top", "holder": ["panel_1"]}},
        {"name": "panel_2", "row": "panel", "on": {"how": "within", "holder": ["crate_1"]}},
        {"name": "sign_1", "row": "sign", "on": {"how": "face", "holder": ["crate_1"], "out": [-1.0, 0.0]}},
        {"name": "rail_1", "row": "rail", "on": {"how": "face", "holder": ["crate_1"], "out": [1.0, 0.0]}}]}))
    (folder / made_waiting.LAID).write_text(json.dumps({"objects": [
        {"name": name, "low": list(low), "high": list(high)} for name, (low, high) in things.items()]}))
    return folder / f"{TOY}.usda"


def a_floored_place(folder):
    """An enclosed place `toy` in `folder` (no made ground) on a built floor (/toy/Shell/deck_1, its top at 0 m): a
    2 m ship laid 1 m over it holding a 0.2 m cube on its top and a seat within it 0.1 m under its corner, a crate laid
    0.2 m over the floor (the settle's to let down), a rack fixed where it is laid 1 m up and a lamp the record lays
    on the ship's face 1 m up; its record and laid.json. The root's path."""
    from pxr import Sdf, Usd, UsdGeom
    (folder / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    a_solid_box(base, f"/{TOY}/Shell/deck_1", (-5.0, -0.1, -5.0), (5.0, 0.0, 5.0))
    things = {"ship_1": ((-1.0, 1.0, -1.0), (1.0, 2.0, 1.0)), "cube_1": ((-0.1, 2.0, -0.1), (0.1, 2.2, 0.1)),
              "crate_1": ((2.0, 0.2, 2.0), (2.5, 0.7, 2.5)), "rack_1": ((-3.0, 1.0, -3.0), (-2.5, 2.0, -2.5)),
              "lamp_1": ((1.0, 1.0, -0.1), (1.1, 1.2, 0.1)), "seat_1": ((0.85, 1.5, 0.85), (1.15, 1.9, 1.15)),
              "crane_1": ((3.0, 3.0, -4.0), (4.0, 4.0, -3.0))}
    for name, (low, high) in things.items():
        a_solid_box(base, f"/{TOY}/Objects/{name}", low, high)
    Sdf.AttributeSpec(base.GetRootLayer().GetPrimAtPath(f"/{TOY}/Objects/rack_1"), "score:fixed",
                      Sdf.ValueTypeNames.Bool).default = True
    base.GetRootLayer().Save()
    root = Usd.Stage.CreateNew(str(folder / f"{TOY}.usda"))
    root.GetRootLayer().subLayerPaths = ["./layers/base.usda"]
    root.SetDefaultPrim(UsdGeom.Xform.Define(root, f"/{TOY}").GetPrim())
    root.GetRootLayer().Save()
    (folder / record.RECORD).write_text(json.dumps({"place": TOY, "inside": True, "objects": [
        {"name": "ship_1", "row": "ship", "at": [0, 1.0, 0]},
        {"name": "cube_1", "row": "cube", "on": {"how": "top", "holder": ["ship_1"]}},
        {"name": "crate_1", "row": "crate", "at": [2.25, 0.2, 2.25]},
        {"name": "rack_1", "row": "rack", "at": [-2.75, 1.0, -2.75]},
        {"name": "lamp_1", "row": "lamp", "on": {"how": "face", "holder": ["ship_1"], "out": [1.0, 0.0]}},
        {"name": "seat_1", "row": "seat", "on": {"how": "within", "holder": ["ship_1"]}},
        {"name": "crane_1", "row": "crane", "at": [3.5, 3.0, -3.5], "under roof": True}]}))
    (folder / made_waiting.LAID).write_text(json.dumps({"objects": [
        {"name": name, "low": list(low), "high": list(high)} for name, (low, high) in things.items()]}))
    return folder / f"{TOY}.usda"


def a_topped_place(folder):
    """A place `toy` in `folder` (no made ground): a hull lying on its side along x (a cylinder 1 m round, 4 m long,
    its crest 2 m up at z 0) and a 0.2 m box the record lays on its top, at the hull's box top 0.6 m off the crest
    (0.2 m over the hull under it); its record and laid.json. The root's path."""
    from pxr import Usd, UsdGeom
    (folder / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    hull = trimesh.creation.cylinder(radius=1.0, height=4.0, sections=96)
    hull.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0.0, 1.0, 0.0]))
    hull.apply_translation([0.0, 1.0, 0.0])
    hatch = trimesh.creation.box(bounds=[(-0.1, 2.0, 0.5), (0.1, 2.1, 0.7)])
    for name, mesh in (("hull_1", hull), ("hatch_1", hatch)):
        a_built_box(base, f"/{TOY}/Objects/{name}", *mesh.bounds)
        geo = UsdGeom.Mesh(base.GetPrimAtPath(f"/{TOY}/Objects/{name}/geo"))
        geo.GetPointsAttr().Set([tuple(map(float, point)) for point in mesh.vertices])
        geo.GetExtentAttr().Set([tuple(map(float, end)) for end in mesh.bounds])
        geo.CreateFaceVertexCountsAttr([3] * len(mesh.faces))
        geo.CreateFaceVertexIndicesAttr([int(index) for index in mesh.faces.ravel()])
    base.GetRootLayer().Save()
    root = Usd.Stage.CreateNew(str(folder / f"{TOY}.usda"))
    root.GetRootLayer().subLayerPaths = ["./layers/base.usda"]
    root.SetDefaultPrim(UsdGeom.Xform.Define(root, f"/{TOY}").GetPrim())
    root.GetRootLayer().Save()
    (folder / record.RECORD).write_text(json.dumps({"place": TOY, "inside": False, "objects": [
        {"name": "hull_1", "row": "hull", "at": [0, 0, 0]},
        {"name": "hatch_1", "row": "hatch", "on": {"how": "top", "holder": ["hull_1"]}}]}))
    (folder / made_waiting.LAID).write_text(json.dumps({"objects": [
        {"name": name, "low": [float(value) for value in mesh.bounds[0]], "high": [float(value) for value in
                                                                                   mesh.bounds[1]]}
        for name, mesh in (("hull_1", hull), ("hatch_1", hatch))]}))
    return folder / f"{TOY}.usda"


def a_roofed_place(folder):
    """A place `toy` in `folder` (no made ground): a hall of two walls 2 m tall at x -1.5 to -1.3 and 1.3 to 1.5, open
    between them, and a roof slab 3 m across them, its foot 2.5 m up (0.5 m over the walls), with a fin 0.8 m under
    its middle; the record lays the roof on the hall's top; its record and laid.json. The root's path."""
    from pxr import Usd, UsdGeom
    (folder / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    hall = trimesh.util.concatenate([trimesh.creation.box(bounds=[(-1.5, 0.0, -1.0), (-1.3, 2.0, 1.0)]),
                                     trimesh.creation.box(bounds=[(1.3, 0.0, -1.0), (1.5, 2.0, 1.0)])])
    roof = trimesh.util.concatenate([trimesh.creation.box(bounds=[(-1.5, 2.5, -0.5), (1.5, 2.6, 0.5)]),
                                     trimesh.creation.box(bounds=[(-0.05, 1.7, -0.5), (0.05, 2.5, 0.5)])])
    for name, mesh in (("hall_1", hall), ("roof_1", roof)):
        a_built_box(base, f"/{TOY}/Objects/{name}", *mesh.bounds)
        geo = UsdGeom.Mesh(base.GetPrimAtPath(f"/{TOY}/Objects/{name}/geo"))
        geo.GetPointsAttr().Set([tuple(map(float, point)) for point in mesh.vertices])
        geo.GetExtentAttr().Set([tuple(map(float, end)) for end in mesh.bounds])
        geo.CreateFaceVertexCountsAttr([3] * len(mesh.faces))
        geo.CreateFaceVertexIndicesAttr([int(index) for index in mesh.faces.ravel()])
    base.GetRootLayer().Save()
    root = Usd.Stage.CreateNew(str(folder / f"{TOY}.usda"))
    root.GetRootLayer().subLayerPaths = ["./layers/base.usda"]
    root.SetDefaultPrim(UsdGeom.Xform.Define(root, f"/{TOY}").GetPrim())
    root.GetRootLayer().Save()
    (folder / record.RECORD).write_text(json.dumps({"place": TOY, "inside": False, "objects": [
        {"name": "hall_1", "row": "hall", "at": [0, 0, 0]},
        {"name": "roof_1", "row": "roof", "on": {"how": "top", "holder": ["hall_1"]}}]}))
    (folder / made_waiting.LAID).write_text(json.dumps({
        "objects": [{"name": "roof_1", "low": [float(value) for value in roof.bounds[0]],
                     "high": [float(value) for value in roof.bounds[1]]}],
        "holders": [{"name": "hall_1", "low": [float(value) for value in hall.bounds[0]],
                     "high": [float(value) for value in hall.bounds[1]]}]}))
    return folder / f"{TOY}.usda"


def a_dented_place(folder):
    """A place `toy` in `folder` on a made ground (/toy/Outside/near, 0.25 m apart, on a layer of its own) flat at 0 but
    for a round dent at the middle, a sphere's cap 1.25 m round and 1 m deep; a 0.6 m box laid at the floor 0.25 m off
    the dent's middle and a 0.6 m crate on the flat ground at x 3; its record and laid.json. The root's path."""
    from pxr import Usd, UsdGeom
    (folder / "layers").mkdir(parents=True)
    ground = Usd.Stage.CreateNew(str(folder / "layers/ground.usda"))
    across, along = np.meshgrid(np.linspace(-5, 5, 41), np.linspace(-5, 5, 41))
    apart, bowl = np.hypot(across, along).ravel(), (1.25 ** 2 + 1.0) / 2.0
    heights = np.where(apart < 1.25, -1.0 + bowl - np.sqrt(np.maximum(bowl ** 2 - np.minimum(apart, 1.25) ** 2, 0)), 0)
    points = np.c_[across.ravel(), np.minimum(heights, 0.0), along.ravel()]
    corners = [triangle for row in range(40) for column in range(40) for triangle in (
        (row * 41 + column, row * 41 + column + 1, (row + 1) * 41 + column + 1),
        (row * 41 + column, (row + 1) * 41 + column + 1, (row + 1) * 41 + column))]
    near = UsdGeom.Mesh.Define(ground, f"/{TOY}/Outside/near")
    near.CreatePointsAttr([tuple(map(float, point)) for point in points])
    near.CreateFaceVertexCountsAttr([3] * len(corners))
    near.CreateFaceVertexIndicesAttr([index for triangle in corners for index in triangle])
    ground.GetRootLayer().Save()
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    things = {"tank_1": ((-0.05, 0.0, -0.3), (0.55, 0.6, 0.3)), "crate_1": ((2.7, 0.0, -0.3), (3.3, 0.6, 0.3))}
    for name, (low, high) in things.items():
        a_built_box(base, f"/{TOY}/Objects/{name}", low, high)
        box = trimesh.creation.box(bounds=[low, high])
        UsdGeom.Mesh(base.GetPrimAtPath(f"/{TOY}/Objects/{name}/geo")).GetPointsAttr().Set(
            [tuple(point) for point in box.vertices])
    base.GetRootLayer().Save()
    root = Usd.Stage.CreateNew(str(folder / f"{TOY}.usda"))
    root.GetRootLayer().subLayerPaths = ["./layers/ground.usda", "./layers/base.usda"]
    root.SetDefaultPrim(UsdGeom.Xform.Define(root, f"/{TOY}").GetPrim())
    root.GetRootLayer().Save()
    (folder / record.RECORD).write_text(json.dumps({"place": TOY, "inside": False, "objects": [
        {"name": "tank_1", "row": "tank", "at": [0.25, 0, 0]}, {"name": "crate_1", "row": "crate", "at": [3, 0, 0]}]}))
    (folder / made_waiting.LAID).write_text(json.dumps({"objects": [
        {"name": name, "low": list(low), "high": list(high)} for name, (low, high) in things.items()]}))
    return folder / f"{TOY}.usda"


def lowest_legs(asset):
    """The lowest point of each leg of a thing_on_legs asset (its drawn mesh) and of its collision hull, metres."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(asset))
    points = np.asarray(UsdGeom.Mesh(stage.GetPrimAtPath(f"/{asset.stem}/geo")).GetPointsAttr().Get())
    hull = np.asarray(UsdGeom.Mesh(stage.GetPrimAtPath(f"/{asset.stem}/collision")).GetPointsAttr().Get())
    legs = [round(float(points[(np.sign(points[:, 0]) == x) & (np.sign(points[:, 2]) == z), 1].min()), 4)
            for x in (-1, 1) for z in (-1, 1)]
    return legs, round(float(hull[(hull[:, 0] > 0.5) & (hull[:, 2] > 0.5), 1].min()), 4)


def test_the_settle_s_seed_is_laid_from_a_read_only_seed_with_no_assets_folder(tmp_path, monkeypatch):
    """The settle's grounded seed of a store checkout (read-only, no assets/ folder: Batch 1, 2026-10-25, every
    settle) is laid with its record written over the copied base and an assets folder of its own.
    Break: score/stages/assembly/grounded.py: `(folder / "assets").mkdir()` -> `pass`
    Break: score/stages/assembly/grounded.py: `parting.parted(folder, seed.name)` -> `pass` (the settle dropped
        airlock's control pedestal in its wall pipes, which the assembly parts: settle@airlock, 2026-11-10)
    Campgrounds' habitat domes (2026-11-11) stood on flat ground with eleven rim feet 3.1 to 8.8 cm up and its
    communications towers with a leg 3.4 cm up, feet the paint links into one (3% of the footprint's diagonal) and
    the resting check reads apart (5 cm): a floor thing's own asset is laid with a leg 5 cm short brought down onto
    its lowest, its hull with it; a leg 2 cm short (within the check's 3 cm), a fixed thing's and an asset linked
    from elsewhere are left as they are.
    Break: score/stages/assembly/even_feet.py: `if foot - lowest > most and not` -> `if False and not`
    Break: score/stages/assembly/big_bases.py: sole_cut's `for spare in (SPARE, 0.0):` -> `for spare in (0.0,):` (the
        cabinet left on a leg 2.7 cm short)
    Break: score/stages/assembly/even_feet.py: `or os.stat(path).st_nlink != 1` -> `` (a write through a link)
    Break: score/stages/assembly/even_feet.py: `and not said("score:fixed")` -> ``
    Break: score/stages/assembly/grounded.py: `even_feet.evened(folder, place)` -> `pass`
    Break: score/stages/assembly/big_bases.py: levelled's `stood = footing.cut_at(points, cut) if cut else ...` ->
        `stood = np.asarray(points, dtype=np.float64)` (the hub left on its post's foot, the tower on its slope)
    Break: score/stages/assembly/big_bases.py: upright's `stood = (points - middle) @ turn.T` -> `stood = points -
        middle` (the beam left leaning), or `key=lambda way: -way[1]):` -> `key=lambda way: -way[1])[:1]:` (the
        angle left on its leg tips)
    Break: score/stages/assembly/grounded.py: `roof_tops.let_down(folder, seed.name, inventory_rows(inputs))` -> `pass`
    Break: score/stages/assembly/roof_tops.py: downs' `if on_ground.TOLERANCE < between < np.inf:` -> `if between <
        np.inf:` (laid again, moved 5 mm down into the walls), `found[entry["name"]] = between - CLEAR` -> `=
        between` (moved 0.5 m), or let_down's `fits.append({**fit, "top at": ...} if one ==
        name else fit)` -> `fits.append(fit)` (the held gate measures it off the hall's box top)
    Break: score/stages/assembly/big_bases.py: deep_cut's `deepest = DEEP * float(np.ptp(points[:, 1]))` -> `deepest
        = 9.0` (the 4 m post cut level), or levelled's `stood, sole = sole_cut(stood, triangles)` -> `sole = []` (the
        hall left on its corners), or sole_cut's `SOLE * float(np.ptp(points[:, 1]))` -> `1.0` (the shed cut level)
    Break: score/stages/assembly/big_bases.py: outlines's within `return any(...)` -> `return True` (the foot beside
        the sole read inside it)
    Break: score/stages/assembly/footing.py: cut_at's `points[points[:, 1] <= lowest + cut, 1] = lowest` dropped (the
        hub's legs left 0.15 m up)
    Break: score/stages/assembly/even_feet.py: `plated = post_plate.based(root, scale)` -> `plated = []` (the flag left
        tipping on its pole), or post_foot's `if across > POST or wide < ...` -> `if wide < ...` (the lamp's 0.2 m
        foot read as a post and given a plate), or stood's `turned = (points - pivot) @ turn.T + pivot` -> `turned =
        points` (the pole left leaning), or standing_post's `<= LEAN_MOST` -> `<= 90.0` (the pipe stood on its leg), or
        joined's `subset.GetIndicesAttr().Set(...)` dropped (the plate in no part)
    Break: score/stages/assembly/even_feet.py: `laid_flat.flattened(stage, folder, place)` -> `pass` (the slab left
        standing), or laid_flat's `if axis is None or footing.stands(...)` -> `if axis is None` (the board laid down),
        or clear_side's `if all(not meets(...))` -> `if True` (the slab laid down into the crate)
    Break: score/stages/assembly/grounded.py: `on_ground.stood(folder, seed.name)` -> `pass`
    Break: score/stages/assembly/on_ground.py: `if record.get("inside") or not` -> `if not`, `if over_deck(pivot,
        decks):` -> `if False:`, `and at_floor(entry)` -> `` (square's podium let down off its stage), `for one in
        (name, *held):` -> `for one in (name,):`, `turn = turn_onto(up, normal)` -> `turn = np.eye(4)`, `if leans <=
        LEAN_MOST and abs(` -> `if False and abs(`, or `laid_path.write_text(json.dumps(laid, indent=1))` -> `pass`
    Break: score/stages/assembly/grounded.py: `face_down.let_down(folder, seed.name)` -> `pass`
    Break: score/stages/assembly/grounded.py: `floor_down.let_down(folder, seed.name)` -> `pass`
    Break: score/stages/assembly/floor_down.py: downs' `if DRIFT_MOST < gap < float("inf"):` -> `if gap <
        float("inf"):` (the crate let down too), `found[entry["name"]] = gap - CLEAR` -> `= gap`, `and
        even_feet.floor_thing(prim)` -> `` (the rack let down), `for one in (name, *held):` -> `for one in (name,):`,
        `if name not in held and below(` -> `if name != entry["name"] and below(` (the ship held up by its seat), `or
        entry.get("under roof"):` -> `:` (the crane let down), or
        let_down's `laid_path.write_text(json.dumps(laid, indent=1))` -> `pass`
    Break: score/stages/assembly/face_down.py: `and entry["row"] not in hanging` -> `` (the sign let down too),
        `if on_ground.TOLERANCE < gap < np.inf:` -> `if gap < np.inf:` (a second let down moves panel_1 again: 0),
        `for one in (name, *held):` -> `for one in (name,):`, gap_under's `if len(rays):` -> `if False:` (the panel
        let down through the step onto the ground), or downs' `points = points[points[:, 1] <= ...]` -> `pass` (let
        down 0.1 m onto the rail its back rests on)
    Break: score/stages/assembly/face_down.py: faced_standing's `and given.get(entry["row"]) in STANDING` -> `` (the
        panel on a rib built into a wall let down too), or downs' `faced_standing(record, rows)` ->
        `faced_standing(record)`
    Break: score/stages/assembly/face_down.py: tip_drop's `<= 0.0:` -> `<= np.inf:` (the tipping wrench
        left), or downs' `elif gap <= on_ground.TOLERANCE:` -> `elif False:` (caught on quarters' laid seed)
    Break: score/stages/assembly/grounded.py: `tops_levelled.laid(folder, seed.name)` -> `pass`, or
        `railings_held.laid(folder, seed.name, inventory_rows(inputs))` -> `pass`
    Break: score/stages/assembly/tops_levelled.py: `fits = crest_tops.laid_on(stage, place, entries)` -> `fits = []`,
        or `layer.Save()` -> `pass`
    Break: score/stages/assembly/grounded.py: `level_spot.slid(folder, seed.name)` -> `pass`
    Break: score/stages/assembly/level_spot.py: spot's `if level(low + shift, high + shift, ground):` -> `if True:`
        (slid 2 cm, still on the dent's side), or `or level(low, high, ground):` -> `` (the crate on flat ground slid
        too: it is level where it is)"""
    from pxr import Sdf
    from score.stages.assembly import (face_down, floor_down, grounded, level_spot, made_waiting, on_ground, parting,
                                       roof_tops, tops_levelled)
    monkeypatch.setattr(baked, "take_bake", lambda *args: None)
    monkeypatch.setattr(baked, "claimed_bakes", lambda *args: [])
    monkeypatch.setattr(made_waiting, "lay", lambda *args: [])
    bake = {"surfaces-bake": str(tmp_path / "bake"), "surfaces-paint": str(tmp_path / "paint")}
    (tmp_path / "elsewhere").mkdir()
    for name, short, how, legs in (("table", 0.05, "floor", [0.0] * 4), ("stool", 0.02, "floor", [0.0, 0.0, 0.0, 0.02]),
                                   ("rack", 0.05, "fixed", [0.0, 0.0, 0.0, 0.05]),
                                   ("shelf", 0.05, "linked", [0.0, 0.0, 0.0, 0.05])):
        source = a_thing_on_legs(tmp_path / "elsewhere", name, short) if how == "linked" else None
        root = a_thing_on_legs(tmp_path / name, name, short,
                               linked_to=source and source.parent / "assets" / f"{name}.usdc")
        if how == "fixed":
            layer = Sdf.Layer.FindOrOpen(str(root))
            Sdf.AttributeSpec(layer.GetPrimAtPath(f"/{TOY}/Objects/{name}_1"), "score:fixed",
                              Sdf.ValueTypeNames.Bool).default = True
            layer.Save()
        grounded.take_bakes(bake, tmp_path / name, TOY)
        assert lowest_legs(root.parent / "assets" / f"{name}.usdc") == (legs, legs[-1]), name
    # assembly@old_station (2026-11-12): its hub stood on a foot at its back edge 16 to 24 cm under its legs, its
    # weight 1.75 m outside what it touched, and its power cables, one 10 m cable on edge, tipped whatever its foot.
    # A 2 m table whose legs end 0.15 m over the foot of a post at its back edge stands on its legs and the post, its
    # top as made; the table on its legs alone, and a 4 m board 2 m tall and 0.18 m thick on its whole edge, are left
    # as made; a slab 0.1 m thick on a 1 m foot at one end lies down on its broad side, toward the side clear of the
    # crate beside it.
    def under(name, at, along, across):
        asset = Usd.Stage.Open(str(tmp_path / name / "assets" / f"{name}.usdc"))
        points = np.asarray(asset.GetPrimAtPath(f"/{name}/geo").GetAttribute("points").Get())
        part = points[(np.abs(points[:, 0] - at[0]) <= along) & (np.abs(points[:, 2] - at[1]) <= across)]
        return round(float(part[:, 1].min()), 3), round(float(np.ptp(points[:, 1])), 3), points

    from pxr import Usd
    box = trimesh.creation.box
    shift = trimesh.transformations.translation_matrix
    legs = [box((0.1, 0.45, 0.1), shift((x, 0.375, z))) for x in (-0.9, 0.9) for z in (-0.9, 0.9)]
    post = box((0.1, 0.65, 0.1), shift((0.0, 0.325, -0.95)))
    slab = trimesh.util.concatenate([box((1.0, 0.1, 0.1), shift((-1.5, 0.05, 0.0))),
                                     box((3.0, 1.7, 0.1), shift((0.5, 1.15, 0.0)))])
    for name, mesh, beside in (("hub", trimesh.util.concatenate([box((2.0, 0.1, 2.0), shift((0, 0.65, 0))), *legs,
                                                                   post]), ()),
                               ("bench", trimesh.util.concatenate([box((2.0, 0.1, 2.0), shift((0, 0.65, 0))), *legs]),
                                ()),
                               ("board", box((4.0, 2.0, 0.18), shift((0.0, 1.0, 0.0))), ()),
                               ("cable", slab, [((0.0, 0.0, -1.95), (6.0, 0.5, -1.0))])):
        a_floor_thing(tmp_path / name, name, mesh, beside=beside)
        grounded.take_bakes(bake, tmp_path / name, TOY)
    leg, tall, points = under("hub", (0.9, 0.9), 0.051, 0.051)
    assert leg == 0.0 and under("hub", (0.0, -0.95), 0.051, 0.051)[0] == 0.0 and tall == 0.7, (leg, tall)
    assert np.isclose(points[:, 1].max(), 0.7) and np.isclose(points[points[:, 1] > 0.55, 1].min(), 0.6), points
    assert under("bench", (0.9, 0.9), 0.051, 0.051)[:2] == (0.15, 0.55) and under("board", (0, 0), 9, 9)[1] == 2.0
    _, tall, points = under("cable", (0.0, 0.0), 9.0, 9.0)
    assert tall == 0.1 and np.isclose(points[:, 2].min(), -1.95, atol=0.06) and points[:, 2].max() <= 0.06, points
    # base (2026-11-12): its connecting tubes, a code build leaned 33 degrees, stood on legs at one side, its central
    # hub's bottom sloped 6 m across it, and its hangar and greenhouse dome stood with hundreds of feet 3 to 10 cm up
    # on bands the triage samples coarsely, which the feet's stretch read again apart. A 4 m beam leaned 20 degrees is
    # laid level, its middle across and its lowest where they were; a 9 m tower whose bottom slopes 0.9 m is cut level,
    # a 4 m one (an eighth of it under the slope) left; a 4 m floor whose inner corners stand 0.15 m up under a roof
    # 3.5 m up is cut level, under one 2 m up (a twentieth of it under the corners) left, the triage's band sampled as
    # coarsely as on the dome (4,000 points over 21 m^2); a foot is inside a touching foot's outline as the triage
    # reads it.
    import triage
    from score.stages.assembly import big_bases
    beam = box((4.0, 0.6, 0.6), trimesh.transformations.rotation_matrix(np.radians(20), (0, 0, 1)))
    beam.apply_translation((0.3, -beam.bounds[0][1], 0.1))
    towers = {}
    for tall in (9.0, 4.0):
        towers[tall] = box((2.0, tall, 2.0))
        corners = np.array(towers[tall].vertices)
        corners[(corners[:, 1] < 0) & (corners[:, 0] < 0), 1] += 0.9
        towers[tall].vertices = corners - (0.0, corners[:, 1].min(), 0.0)
    for name, mesh in (("beam", beam), ("tower", towers[9.0]), ("post", towers[4.0])):
        a_floor_thing(tmp_path / name, name, mesh)
        grounded.take_bakes(bake, tmp_path / name, TOY)
    _, tall, points = under("beam", (0.0, 0.0), 9.0, 9.0)
    assert np.isclose(tall, 0.6) and np.allclose((points.min(axis=0) + points.max(axis=0))[[0, 2]] / 2, (0.3, 0.1),
                                                 atol=1e-5) and np.isclose(points[:, 1].min(), 0.0), points
    assert sorted({round(float(height), 3) for height in under("tower", (0, 0), 9, 9)[2][:, 1]}) == [0.0, 9.0]
    assert sorted({round(float(height), 3) for height in under("post", (0, 0), 9, 9)[2][:, 1]}) == [0.0, 0.9, 4.0]
    monkeypatch.setattr(triage, "FOOT_SAMPLES", (400, 4000))
    across = np.arange(-2.0, 2.001, 1.0)
    corners = [(x, 0.15 if (row + column) % 2 and 0 < row < 4 and 0 < column < 4 else 0.0, z)
               for row, x in enumerate(across) for column, z in enumerate(across)]
    cells = [face for row in range(4) for column in range(4) for face in (
        [row * 5 + column, row * 5 + column + 1, (row + 1) * 5 + column + 1],
        [row * 5 + column, (row + 1) * 5 + column + 1, (row + 1) * 5 + column])]
    for name, roof in (("hall", 3.5), ("shed", 2.0)):
        a_floor_thing(tmp_path / name, name, trimesh.util.concatenate([trimesh.Trimesh(corners, cells, process=False),
                                                                      box((4.0, 0.2, 4.0), shift((0, roof, 0)))]))
        grounded.take_bakes(bake, tmp_path / name, TOY)
    assert sorted({round(float(height), 3) for height in under("hall", (0, 0), 1.5, 1.5)[2][:, 1]})[:2] == [0.0, 3.4]
    assert 0.15 in {round(float(height), 3) for height in under("shed", (0, 0), 1.5, 1.5)[2][:, 1]}
    sole = np.array([(x, 0.0, z) for x in (0.0, 1.0) for z in (0.0, 1.0)])
    for foot in (np.array([(0.4, 0.05, 0.4), (0.6, 0.05, 0.4), (0.5, 0.05, 0.6)]), np.array([(1.4, 0.05, 0.4)] * 3)):
        assert big_bases.outlines([sole])(foot) == triage.within_a_foot(foot, [sole]) == (foot[0, 0] < 1.0)
    # base, later that day: its greenhouse dome, its sole cut 0.60 m, kept a foot 2.99 cm up its model (a face rising
    # out of its sole), read 3.03 cm over its ground. A 2 m cabinet on four legs, one 2.7 cm short (within the check's
    # 3 cm, under its spare), has its sole cut level 0.05 m.
    legs = [box((0.1, 0.6 - lift, 0.1), shift((x, 0.3 + lift / 2, z))) for x, z, lift in (
        (-0.9, -0.9, 0.0), (-0.9, 0.9, 0.0), (0.9, -0.9, 0.0), (0.9, 0.9, 0.027))]
    a_floor_thing(tmp_path / "cabinet", "cabinet", trimesh.util.concatenate([box((2.0, 1.4, 2.0), shift((0, 1.3, 0))),
                                                                             *legs]))
    grounded.take_bakes(bake, tmp_path / "cabinet", TOY)
    assert under("cabinet", (0.9, 0.9), 0.051, 0.051)[:2] == (0.0, 2.0), under("cabinet", (0.9, 0.9), 0.051, 0.051)
    # base, later that day: its tube, retaken from its picture, lay 22 degrees off its frame, squashed in depth; on its
    # box axis nearest up no footing holds it, on its next one a cut of 0.09 m does. A 4 m angle (a 2 m top on a 1 m
    # leg at one end) leaned 20 degrees, which stood on its leg tips, is turned 70 degrees onto its leg's outer face.
    angle = trimesh.util.concatenate([box((2.0, 0.2, 4.0), shift((1.0, 0.9, 0.0))), box((0.2, 0.8, 4.0),
                                                                                        shift((0.1, 0.4, 0.0)))])
    angle.apply_transform(trimesh.transformations.rotation_matrix(np.radians(20), (0, 0, 1)))
    stood, turned = big_bases.upright(angle.vertices - (0.0, angle.bounds[0][1], 0.0), angle.faces)
    assert turned == [70.0] and np.allclose(np.ptp(stood, axis=0), (1.0, 2.0, 4.0), atol=1e-6), (turned, stood)
    # square (2026-11-12): its 41 red flags stood on a pole 1.5 cm wide at its foot leaning 10 degrees, their cloth
    # 0.42 m to one side, their weight (the triage's: by surface area) 0.18 m outside the pole's foot. A 0.5 m pole so
    # leaned with a 0.4 m cloth on it stands upright on a plate in the pole's part that holds it, its texture places,
    # normals and parts carried; a pole on a 0.2 m foot under a head to one side (no thin post), and a 3 m pipe on a
    # thin leg leaning 60 degrees (no post standing), are left as made.
    from pxr import UsdGeom, Vt
    from score.stages.assembly import post_plate
    for name, head, lean in (("flag", box((0.4, 0.3, 0.004), shift((0.2075, 0.35, 0.0))), 10),
                             ("lamp", trimesh.util.concatenate([box((0.2, 0.01, 0.2), shift((0.0, 0.005, 0.0))), box(
                                 (0.8, 0.02, 0.1), shift((0.4, 0.5, 0.0)))]), 0),
                             ("pipe", box((3.0, 0.05, 0.05), shift((1.4, 0.53, 0.0))), 0)):
        pole = box((0.015, 0.5, 0.015), shift((0.0, 0.25, 0.0)))
        if name == "pipe":
            pole.apply_transform(trimesh.transformations.rotation_matrix(np.radians(60), (0, 0, 1), (0, 0.25, 0)))
        mesh = trimesh.util.concatenate([pole, head])
        mesh.apply_transform(trimesh.transformations.rotation_matrix(np.radians(lean), (1, 0, 0)))
        mesh.apply_translation((0.0, -mesh.bounds[0][1], 0.0))
        a_floor_thing(tmp_path / name, name, mesh)
        asset = Usd.Stage.Open(str(tmp_path / name / "assets" / f"{name}.usdc"))
        geo = UsdGeom.Mesh(asset.GetPrimAtPath(f"/{name}/geo"))
        geo.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(mesh.vertex_normals, dtype=np.float32)))
        UsdGeom.PrimvarsAPI(geo).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                               UsdGeom.Tokens.vertex).Set([(0.25, 0.75)] * len(mesh.vertices))
        for part, faces in (("pole_iron", range(len(pole.faces))),
                            ("flag_cloth", range(len(pole.faces), len(mesh.faces)))):
            UsdGeom.Subset.CreateGeomSubset(geo, part, UsdGeom.Tokens.face, Vt.IntArray(list(faces)), "materialBind")
        asset.GetRootLayer().Save()
        grounded.take_bakes(bake, tmp_path / name, TOY)
    flag = Usd.Stage.Open(str(tmp_path / "flag" / "assets" / "flag.usdc"))
    geo = UsdGeom.Mesh(flag.GetPrimAtPath("/flag/geo"))
    points = np.asarray(geo.GetPointsAttr().Get(), dtype=np.float64)
    triangles = np.asarray(geo.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    parts = {subset.GetPrim().GetName(): np.asarray(subset.GetIndicesAttr().Get())
             for subset in UsdGeom.Subset.GetAllGeomSubsets(geo)}
    pole = points[np.unique(triangles[parts["pole_iron"][:12]])]
    plate = points[16:]
    assert len(points) == 16 + 4 * post_plate.SEGMENTS + 2 and len(parts["pole_iron"]) == 12 + 4 * post_plate.SEGMENTS
    assert np.ptp(pole[:, 2]) < 0.016 and np.isclose(pole[:, 1].min(), post_plate.THICK, atol=1e-4), pole
    assert np.isclose(plate[:, 1].min(), 0.0, atol=1e-4) and 0.05 <= np.ptp(plate[:, 0]) / 2 <= 0.3, plate
    assert big_bases.holds_as_made(points, triangles) and len(geo.GetNormalsAttr().Get()) == len(points)
    assert list(UsdGeom.PrimvarsAPI(geo).GetPrimvar("st").Get())[-1] == (0.25, 0.75)
    assert len(Usd.Stage.Open(str(tmp_path / "lamp" / "assets" / "lamp.usdc")).GetPrimAtPath(
        "/lamp/geo").GetAttribute("points").Get()) == 24
    assert len(Usd.Stage.Open(str(tmp_path / "pipe" / "assets" / "pipe.usdc")).GetPrimAtPath(
        "/pipe/geo").GetAttribute("points").Get()) == 16
    read_only_toy(tmp_path / "store" / TOY)
    parted, stood, downed, topped, levelled = [], [], [], [], []
    monkeypatch.setattr(parting, "parted", lambda folder, place: parted.append((folder, place)) or [])
    restore, lay_down, lay_tops, slide = on_ground.stood, face_down.let_down, tops_levelled.laid, level_spot.slid
    lay_roofs, roofed = roof_tops.let_down, []
    monkeypatch.setattr(roof_tops, "let_down", lambda folder, place, rows: roofed.append((folder, place)) or [])
    monkeypatch.setattr(level_spot, "slid", lambda folder, place: levelled.append((folder, place)) or [])
    monkeypatch.setattr(tops_levelled, "laid", lambda folder, place: topped.append((folder, place)) or [])
    from score.stages.assembly import railings_held
    railed = []
    monkeypatch.setattr(railings_held, "laid", lambda folder, place, rows: railed.append((folder, place)) or [])
    monkeypatch.setattr(on_ground, "stood", lambda folder, place: stood.append((folder, place)) or [])
    monkeypatch.setattr(face_down, "let_down", lambda folder, place, rows: downed.append((folder, place)) or [])
    lay_floored, floored = floor_down.let_down, []
    monkeypatch.setattr(floor_down, "let_down", lambda folder, place: floored.append((folder, place)) or [])
    root = grounded.grounded_seed({"seed": tmp_path / "store" / TOY, **a_record(tmp_path, ONE_LAMP)},
                                  tmp_path / "settle")
    stage = opened(root)
    assert stage.GetPrimAtPath(f"/{TOY}/Lights/light_1") and (root.parent / "assets").is_dir()
    assert parted == [(tmp_path / "settle", TOY)], parted  # parted as the assembly's make parts (wired.make)
    assert stood == [(tmp_path / "settle", TOY)], stood  # on its made ground, as the assembly's make stands them
    assert levelled == downed == topped == roofed == railed == floored == [(tmp_path / "settle", TOY)], downed
    # settle@hangar (2026-11-13): its spaceship, laid at the plan's keel height on its landing gear (1.039 m) though
    # its model stands on its own feet, floated 0.94 m: past the settle's 0.3 m, kept as laid, failing rested and
    # resting. A 2 m ship laid 1 m over a built floor is let down onto it, less the snap's 2 mm, the cube on its top
    # the lamp on its face and the seat within it with it; a crate 0.2 m over it (the settle's), a fixed rack and a
    # crane hung from the roof (settle@hangar's, let down 1.39 m off its roof, hanging free) are left, and a second
    # let down moves nothing.
    from pxr import Usd
    place = a_floored_place(tmp_path / "floored")
    fits = lay_floored(place.parent, TOY)
    stage = Usd.Stage.Open(str(place))
    low = {name: on_ground.world_points(stage.GetPrimAtPath(f"/{TOY}/Objects/{name}"))[:, 1].min()
           for name in ("ship_1", "cube_1", "crate_1", "rack_1", "lamp_1", "seat_1", "crane_1")}
    assert [(fit["name"], fit["how"], round(fit["moved"], 3)) for fit in fits] == [
        ("ship_1", "floored", 0.998), ("cube_1", "floored", 0.998), ("lamp_1", "floored", 0.998),
        ("seat_1", "floored", 0.998)], fits
    assert np.allclose(list(low.values()), [0.002, 1.002, 0.2, 1.0, 0.002, 0.502, 3.0]), low
    laid = {entry["name"]: entry for entry in json.loads((place.parent / made_waiting.LAID).read_text())["objects"]}
    assert np.isclose(laid["ship_1"]["low"][1], 0.002, atol=1e-3) and lay_floored(place.parent, TOY) == [], laid
    # assembly@wreck (2026-11-12): every thing laid at the plan's floor, 0 m, over a made ground from -4.8 to +4.0 m
    # under them. On a ground rising 0.2 m a metre north from 1 m at z 0, a 1 m box laid at 0 m is turned
    # atan(0.2) = 11.31 degrees with the slope and let down onto it, every corner of its foot on the ground and the
    # cube on its top moved with it; one over a built deck and one the record lays on a 3.3 m level (square's podium)
    # are left, a second stand moves nothing, and an enclosed place is left whole.
    from pxr import Usd
    for inside in (False, True):
        place = a_sloped_place(tmp_path / f"sloped-{inside}", inside)
        fits = restore(place.parent, TOY)
        stage = Usd.Stage.Open(str(place))

        def corners(name):
            prim = stage.GetPrimAtPath(f"/{TOY}/Objects/{name}")
            return on_ground.world_points(prim), on_ground.up_of(prim)
        crate, up = corners("crate_1")
        foot = crate[crate[:, 1] <= np.sort(crate[:, 1])[3] + 1e-6]
        cube, _ = corners("cube_1")
        if inside:
            assert fits == [] and np.isclose(crate[:, 1].min(), 0.0) and np.allclose(up, [0, 1, 0]), fits
            continue
        assert [(fit["name"], fit["how"]) for fit in fits] == [("crate_1", "grounded"), ("cube_1", "grounded")], fits
        assert np.isclose(np.degrees(np.arccos(up[1])), 11.31, atol=0.01) and up[2] > 0, up
        assert np.allclose(foot[:, 1], 1.0 - 0.2 * foot[:, 2], atol=1e-4), foot
        assert np.allclose(cube.mean(axis=0), crate.mean(axis=0) + 0.6 * up, atol=1e-4), (cube, crate)
        case, _ = corners("case_1")
        assert np.isclose(case[:, 1].min(), 0.0) and np.isclose(corners("podium_1")[0][:, 1].min(), 3.3), case
        laid = {entry["name"]: entry for entry in json.loads((place.parent / made_waiting.LAID).read_text())["objects"]}
        assert np.isclose(laid["crate_1"]["low"][1], crate[:, 1].min(), atol=1e-3), laid
        assert restore(place.parent, TOY) == []
    # assembly@wreck (2026-11-12): solar_panels_5, laid 0.41 m up its lander's side clear of solar_panels_4, floated:
    # its row (two panels within the lander) is judged standing. A panel laid on its crate's side 0.5 m up is let
    # down 0.4 m onto the 0.1 m step under it, and the cube on its top with it; a sign whose every object is on a
    # face (judged by touching) and the panel within the crate are left, and a second let down moves nothing.
    place = a_faced_place(tmp_path / "faced")
    fits = lay_down(place.parent, TOY)
    stage = Usd.Stage.Open(str(place))
    low = {name: on_ground.world_points(stage.GetPrimAtPath(f"/{TOY}/Objects/{name}"))[:, 1].min()
           for name in ("panel_1", "panel_2", "sign_1", "cube_2")}
    assert [(fit["name"], round(fit["moved"], 3)) for fit in fits] == [("panel_1", 0.4), ("cube_2", 0.4)], fits
    assert np.allclose([low["panel_1"], low["panel_2"], low["sign_1"], low["cube_2"]], [0.1, 0.2, 0.6, 0.5]), low
    laid = {entry["name"]: entry for entry in json.loads((place.parent / made_waiting.LAID).read_text())["objects"]}
    assert np.isclose(laid["panel_1"]["low"][1], 0.1, atol=1e-3) and lay_down(place.parent, TOY) == [], laid
    # quarters' flat wrench (settle@quarters, 2026-11-13), its back edge on its desk's panel 0.25 m up, the rest of it
    # over the floor, tipped: a foot touching only along one edge, its weight 6 cm past it, is let down by the least
    # gap of the rest (0.25 m); one standing on four points round its weight, and one touching nowhere, are not
    flat = np.array([(x, 0.25, z) for x in (0.0, 0.04, 0.08, 0.12, 0.16) for z in (0.0, 0.06, 0.12)])
    edge = np.where(flat[:, 2] == 0.0, 0.005, 0.25)
    assert np.isclose(face_down.tip_drop(flat, edge, (0.08, 0.06)), 0.25)
    assert face_down.tip_drop(flat, np.full(len(flat), 0.005), (0.08, 0.06)) == 0.0
    assert face_down.tip_drop(flat, np.full(len(flat), np.inf), (0.08, 0.06)) == 0.0
    # assembly@tube (2026-11-12): its wall lamps, a row on its structural ribs (a structure row on its wall panels),
    # four within a rib and seven on a rib's side, were let down 1.3 to 2.2 m from 2 m up, lamps 5 to 7 into the deck:
    # the resting gate judges the row mounted on its ribs by the inventory, by touching. The same panel, its row on a
    # rib built into a wall by the inventory, is left 0.5 m up its crate's side; its row on the crate, let down.
    rows = [{"id": "crate", "noun": "crate", "anchor": "on:rib"}, {"id": "hull_wall", "noun": "wall"},
            {"id": "rib", "noun": "rib", "part": "structure", "anchor": "on:hull_wall"}]
    for holder, moved in (("rib", []), ("crate", [("panel_1", 0.4), ("cube_2", 0.4)])):
        place = a_faced_place(tmp_path / f"faced-on-{holder}")
        fits = lay_down(place.parent, TOY, [*rows, {"id": "panel", "noun": "wall lamp", "anchor": f"on:{holder}"}])
        assert [(fit["name"], round(fit["moved"], 3)) for fit in fits] == moved, (holder, fits)
    # assembly@wreck (2026-11-12): its open hatch, left at its rocket half's box top in the fitting (its model a foot
    # off until even_feet levelled it), floated 1.74 m over the hull. A 0.2 m box at the box top of a hull lying on
    # its side (radius 1 m, crest 2 m up), 0.6 m off the crest (0.2 m over the hull there), is laid on the crest, its
    # foot on it; laid again it moves no more.
    place = a_topped_place(tmp_path / "topped")
    fits = lay_tops(place.parent, TOY)
    stage = Usd.Stage.Open(str(place))
    hatch = on_ground.world_points(stage.GetPrimAtPath(f"/{TOY}/Objects/hatch_1"))
    assert [fit["name"] for fit in fits] == ["hatch_1"], fits
    assert abs(hatch[:, 2].mean()) < 0.15 and abs(hatch[:, 1].min() - 2.0) < 0.01, hatch.min(axis=0)
    laid = {entry["name"]: entry for entry in json.loads((place.parent / made_waiting.LAID).read_text())["objects"]}
    assert np.isclose(laid["hatch_1"]["low"][1], hatch[:, 1].min(), atol=1e-3) and lay_tops(place.parent, TOY) == []
    # assembly@base (2026-11-12): its hangar roof opening, a slab with a fin hanging 2.7 m under it into the hangar's
    # open middle, was left at the hangar's box top and floated 2.98 m. A 3 m slab with a fin 0.8 m under it, laid
    # 0.5 m over the two walls of a hall it spans (the fin between them), is let down onto the walls' tops, its fin
    # into the hall, nothing slid across; its row read as an object, or laid again, it moves no more.
    rows = [{"id": "hall", "noun": "building"}, {"id": "roof", "part": "opening", "anchor": "on:hall"}]
    place = a_roofed_place(tmp_path / "roofed")
    fits = lay_roofs(place.parent, TOY, rows)
    stage = Usd.Stage.Open(str(place))
    roof = on_ground.world_points(stage.GetPrimAtPath(f"/{TOY}/Objects/roof_1"))
    assert [(fit["name"], fit["moved"], fit["top at"]) for fit in fits] == [("roof_1", 0.495, 1.205)], fits
    assert np.isclose(roof[:, 1].min(), 1.205) and np.allclose(roof[:, [0, 2]].min(axis=0), (-1.5, -0.5)), roof
    laid = {entry["name"]: entry for entry in json.loads((place.parent / made_waiting.LAID).read_text())["objects"]}
    assert np.isclose(laid["roof_1"]["low"][1], 1.205) and lay_roofs(place.parent, TOY, rows) == [], laid
    assert fitting.held_faults(json.loads((place.parent / record.RECORD).read_text()),
                               json.loads((place.parent / made_waiting.LAID).read_text())) == []
    place = a_roofed_place(tmp_path / "roofed-object")
    assert lay_roofs(place.parent, TOY, [rows[0], {**rows[1], "part": "object"}]) == []
    # assembly@wreck (2026-11-12): its spherical tank, laid 0.26 m off the middle of its 1 m dent, was turned 7.9
    # degrees with the dent's side and leaned. A 0.6 m box laid 0.25 m off the middle of a round dent 1 m deep (a
    # sphere's cap 1.25 m round) is slid to where the ground under it is level, at the dent's middle; one on the flat
    # ground beside it is left, and slid again neither moves.
    place = a_dented_place(tmp_path / "dented")
    fits = slide(place.parent, TOY)
    stage = Usd.Stage.Open(str(place))
    tank = on_ground.world_points(stage.GetPrimAtPath(f"/{TOY}/Objects/tank_1"))
    middle = (tank.min(axis=0) + tank.max(axis=0)) / 2
    assert [fit["name"] for fit in fits] == ["tank_1"] and np.hypot(middle[0], middle[2]) < 0.1, (fits, middle)
    crate = on_ground.world_points(stage.GetPrimAtPath(f"/{TOY}/Objects/crate_1"))
    assert np.isclose(crate[:, 0].min(), 2.7) and slide(place.parent, TOY) == [], crate.min(axis=0)


# --- the layers gate ------------------------------------------------------------------------------------------------

# Row-kind rules written here (data/checks/row-kinds.json's shape), so the test does not follow the house's table.
KINDS = {"person": {"nouns": ["astronaut"], "does": ["acts"]}, "kettle": {"nouns": ["kettle"], "does": ["emits"]},
         "door": {"nouns": ["door"], "does": ["moves"]}, "plant": {"nouns": ["plants", "planter"], "does": ["grows"]},
         "loose": {"nouns": ["crate"], "does": ["loose"]}}
# A design showing a person, a kettle, a door hung on its wall as code, and plants on a raised planter.
DESIGN = {"rows": [{"id": "wall", "noun": "wall", "kind": "code", "anchor": "floor"},
                   {"id": "pilot", "noun": "astronaut", "kind": "generate", "anchor": "floor"},
                   {"id": "kettle", "noun": "kettle", "kind": "generate", "anchor": "floor"},
                   {"id": "door", "noun": "door", "kind": "code", "anchor": "on:wall"},
                   {"id": "bed", "noun": "planter", "kind": "generate", "anchor": "floor"},
                   {"id": "greens", "noun": "plants", "kind": "generate", "anchor": "on:bed"}]}


# A crate on the floor: a loose row, so its place needs the settle.
CRATE = {"id": "crate", "noun": "crate", "kind": "generate", "anchor": "floor"}
EVERY = ["characters-layer", "crops-layer", "effects-layer", "motion", "light", "sound"]
# Each place's layers: its design (None: a place with no design), the layer stages the assembly took and the sounds it
# placed nowhere; the layers its design needs, and the layers gate's answer and the layers it waits on, each by name.
# DESIGN's person needs its characters layer, the kettle its effects, the door its motion, the plants on the planter
# their crops; no loose row, so no settle; light and sound always.
LAYERED = [
    {"name": "the design taking four", "design": DESIGN, "took": ["sound", "effects-layer", "motion", "light"],
     "needs": EVERY, "answer": checks.UNKNOWN, "waits": (f"characters-layer@{TOY}", f"crops-layer@{TOY}")},
    {"name": "the design taking all", "design": DESIGN, "took": EVERY, "needs": EVERY, "answer": checks.PASS,
     "waits": ()},
    {"name": "a sound placed nowhere", "design": DESIGN, "took": EVERY, "unplaced": ["hum"], "needs": EVERY,
     "answer": checks.FAIL},
    {"name": "a bare room", "design": {"rows": DESIGN["rows"][:1]}, "took": ["light", "sound"],
     "needs": ["light", "sound"], "answer": checks.PASS, "waits": ()},
    {"name": "a crate on the floor", "design": {"rows": [*DESIGN["rows"][:1], CRATE]}, "took": ["light", "sound"],
     "needs": ["settle", "light", "sound"], "answer": checks.UNKNOWN, "waits": (f"settle@{TOY}",)},
    {"name": "no design", "design": None, "took": EVERY, "answer": checks.UNKNOWN},
]


def layered(root, case):
    """The assembly's output for a LAYERED case (its origin naming the layers it took) and the gate's inputs."""
    output = root / case["name"].replace(" ", "_")
    output.mkdir(parents=True)
    (output / f"{TOY}.usda").write_text("#usda 1.0\n")
    (output / "row-kinds.json").write_text(json.dumps({"kinds": KINDS}))
    (output / "origin.json").write_text(json.dumps({"layers": dict.fromkeys(case["took"], "x"), "record": "r",
                                                    "unplaced sounds": case.get("unplaced", [])}))
    inputs = {"row kinds": output / "row-kinds.json"}
    if case["design"] is not None:
        (output / "design.json").write_text(json.dumps(case["design"]))
        inputs["design"] = output / "design.json"
    return output, inputs


# --- the neighbours stage -------------------------------------------------------------------------------------------

def a_place(root, place, shows=(), ground_shows=()):
    """A place's stage as the assembly leaves it: a root over layers/ground.usdc (the terrain's, with the shown places
    the seed lacks, and the place's own made ground under Outside) and layers/base.usda, its shown places referenced
    the seed's way (../../<other>/<other>.usda)."""
    from pxr import Usd, UsdGeom
    folder = root / place
    (folder / "layers").mkdir(parents=True)
    for layer, others in (("base.usda", shows), ("ground.usdc", ground_shows)):
        base = Usd.Stage.CreateNew(str(folder / "layers" / layer))
        UsdGeom.Xform.Define(base, f"/{place}/Objects/crate_1")
        for other in others:
            UsdGeom.Xform.Define(base, f"/{place}/Places/{other}").GetPrim().GetReferences().AddReference(
                f"../../{other}/{other}.usda")
        if layer == "ground.usdc":
            UsdGeom.Mesh.Define(base, f"/{place}/Outside/near")
        base.GetRootLayer().Save()
    stage = Usd.Stage.CreateNew(str(folder / f"{place}.usda"))
    stage.GetRootLayer().subLayerPaths.append("./layers/ground.usdc")
    stage.GetRootLayer().subLayerPaths.append("./layers/base.usda")
    stage.SetDefaultPrim(stage.GetPrimAtPath(f"/{place}"))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.GetRootLayer().Save()
    return folder


def shows(folder, *others):
    (folder / assembly.RECORD).write_text(json.dumps({"places": [{"name": other, "stage": other}
                                                                 for other in others]}))


# Each world of shown places: the place, the places its base and its terrain's ground show (each referenced the seed's
# way), the shown places made (each with the places it shows), whether its own made ground under Outside is gone; the
# seed's way judged (the place copied alone or with its neighbours beside it); then the made place judged once the
# outputs it was made from are gone: its answer, places shown, gap, prims active or left out, and the shown place whose
# copy, removed, fails it.
NEIGHBOURED = [
    # Fault (2026-10-12): the launch's assembly showed Places/square and Places/far_city with no children, its
    # references pointing at round-three seed files the store does not hold. Alone it fails on both shown places (no
    # file, no children: four faults); made, each stands from its own copied output.
    {"name": "the launch", "place": "launch", "shows": ("square", "wreck"), "made": {"square": (), "wreck": ()},
     "seed": {"beside": False, "faults": 4, "a finding": "resolves to no file"}, "shown": 2},
    # No stage makes the far city: the make stands the rest and names it a gap (gaps.json), and the gate moves only its
    # faults to the completion gate; a fault no gap names (the square's copy removed) still fails.
    {"name": "a lost far city", "place": "launch", "shows": ("square", "far_city"), "made": {"square": ()},
     "gap": "far_city", "removed": "square"},
    # Fault (2026-10-15): the stairwell's Places/flat, which its seed lacks and the terrain's ground layer adds, kept its
    # reference ../../flat/flat.usda: only the base layer's references were pointed at the copies.
    {"name": "the stairwell", "place": "stairwell", "shows": ("street",), "ground": ("flat",),
     "made": {"street": (), "flat": ("stairwell",)}, "shown": 2},
    # Fault (2026-10-18): the old station's film looked through a flat grey slab, the shown places' own made grounds:
    # the seed's way fails on both (two faults, each its own ground); made, both are left out and its own stays.
    {"name": "the old station", "place": "old_station", "shows": ("wreck",), "ground": ("garage",),
     "made": {"wreck": (), "garage": ()}, "seed": {"beside": True, "faults": 2, "every finding": "its own ground"},
     "shown": 2, "active": {"/old_station/Outside/near": True, "/old_station/Places/wreck/Outside": False}},
    # The airlock has no made ground of its own: through its doors the ground is the one its shown garage draws, so it
    # stays.
    {"name": "the airlock", "place": "airlock", "shows": ("garage",), "made": {"garage": ()}, "groundless": True,
     "active": {"/airlock/Places/garage/Outside": True}},
]
# The launch shows the square and the far city, the square the launch; only the square and the launch are written,
# and the launch is a part of an outside (data/places/within.json), no place of the build. Each query of neighbours.py
# on a place, and its answer.
RECORDS = {"launch": {"places": [{"name": "square", "stage": "square"}, {"name": "far_city", "stage": "far_city"}]},
           "square": {"places": [{"name": "launch", "stage": "launch"}]}}
ASKED = [("shown", "launch", ["far_city", "square"]), ("neighbours", "launch", ["square"]),
         ("lost", "launch", ["far_city"]), ("files", "launch", {}), ("applies", "square", True),
         ("applies", "nowhere", False), ("neighbours", "square", [])]


def the_neighbours(root, case):
    """A NEIGHBOURED case's place and the shown places made, under root/kept: the make's inputs."""
    from pxr import Sdf, Usd
    kept = root / "kept"
    folder = a_place(kept, case["place"], case["shows"], case.get("ground", ()))
    if case.get("groundless"):
        layer = Sdf.Layer.FindOrOpen(str(folder / "layers" / "ground.usdc"))
        Usd.Stage.Open(layer).RemovePrim(f"/{case['place']}/Outside")
        layer.Save()
    shows(folder, *case["shows"], *case.get("ground", ()))
    return {"assembly": folder, **{f"assembly@{other}": a_place(kept, other, theirs)
                                   for other, theirs in case["made"].items()}}


def the_seed_s_way(root, case, inputs):
    """The place as its seed stands it: copied to root/seed, its shown places copied beside it when the case says."""
    seed = root / "seed"
    shutil.copytree(inputs["assembly"], seed / case["place"])
    for other in case["made"] if case["seed"]["beside"] else ():
        shutil.copytree(inputs[f"assembly@{other}"], seed / other)
    return seed / case["place"]


# --- the scene tree -------------------------------------------------------------------------------------------------

# The yard: 20 x 12 m, no frame, so its north-west corner is at (-10, 0, -6). It holds the shed at (2, 3) and the hut
# at (10, 5), plan metres x east, y south.
YARD = {"w": 20.0, "d": 12.0, "holds": [{"place": "shed", "row": None, "x": 2.0, "y": 3.0, "w": 4.0, "d": 3.0},
                                       {"place": "hut", "row": None, "x": 10.0, "y": 5.0, "w": 4.0, "d": 3.0}]}
# The shed: 4 x 3 m, its north-west corner at (5, 0, -2) of its own frame; it holds the nook at (1, 1).
SHED = {"w": 4.0, "d": 3.0, "frame": {"anchor": {"plan": [0.0, 0.0], "place": [5.0, 0.0, -2.0]}},
        "holds": [{"place": "nook", "row": None, "x": 1.0, "y": 1.0, "w": 2.0, "d": 1.0}]}
# The hut: 4 x 3 m, turned: its plan's east runs along its frame's +z, its south along -x, its corner at the origin.
HUT = {"w": 4.0, "d": 3.0, "frame": {"anchor": {"plan": [0.0, 0.0], "place": [0.0, 0.0, 0.0]},
                                     "toward": {"plan": [1.0, 0.0], "place": [0.0, 0.0, 1.0]}}}
# The nook: 2 x 1 m, no frame: its north-west corner at (-1, 0, -0.5).
NOOK = {"w": 2.0, "d": 1.0}


def a_scene(root, scene, crate):
    """A scene's stage as the assembly leaves it: a root over layers/base.usda, one crate at `crate`."""
    from pxr import Gf, Usd, UsdGeom
    folder = root / scene
    (folder / "layers").mkdir(parents=True)
    base = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    UsdGeom.Xform.Define(base, f"/{scene}")
    UsdGeom.Xform.Define(base, f"/{scene}/Objects/crate_1").AddTranslateOp().Set(Gf.Vec3d(*crate))
    base.GetRootLayer().Save()
    stage = Usd.Stage.CreateNew(str(folder / f"{scene}.usda"))
    stage.GetRootLayer().subLayerPaths.append("./layers/base.usda")
    stage.SetDefaultPrim(stage.GetPrimAtPath(f"/{scene}"))
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.GetRootLayer().Save()
    return folder


def a_plan(root, scene, plan):
    path = root / "plans" / f"{scene}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan))
    return path


def tree_of(root, scene, made, plan, children):
    """scene_tree.make's output for the scene: its assembly, its plan, and each child's (tree, plan)."""
    out = root / "trees" / scene
    out.mkdir(parents=True)
    inputs = {"assembly": made, "plan": a_plan(root, scene, plan) if plan else None}
    for child, (tree, child_plan) in children.items():
        inputs[f"scene-tree@{child}"] = tree
        inputs[f"plan {child}"] = a_plan(root, child, child_plan)
    inputs = {name: path for name, path in inputs.items() if path is not None}
    scene_tree.make(inputs, out, 0, {})
    return out, inputs


def crate_at(stage, path):
    from pxr import UsdGeom
    return [round(value, 4) for value in
            UsdGeom.XformCache().GetLocalToWorldTransform(stage.GetPrimAtPath(path)).ExtractTranslation()]



# A held door between the shed and the hut, its kind and width (the square's flat under its stairwell door, 2026-11-04).
DOOR = {"kind": "door", "wide": 1.0, "sill": 0.0}
# The yard holding the hut three times (#72: a place held several times stands once a hold): as the yard lays it out,
# turned 90 degrees at (2, 7) in 3 x 4 m, and turned 45 degrees (the base's tubes off the hub's diagonal facets) in its
# 4.95 m box at (14, 0).
THRICE = {**YARD, "holds": [{**YARD["holds"][1], "instance": "hut#1"},
                            {"place": "hut", "instance": "hut#2", "turn": 90, "x": 2.0, "y": 7.0, "w": 3.0, "d": 4.0},
                            {"place": "hut", "instance": "hut#3", "turn": 45, "x": 14.0, "y": 0.0, "w": 4.949747,
                             "d": 4.949747}]}
# The shed's crate at (6, 0, -1) of its frame is plan (1, 1) on the shed, (3, 4) on the yard: (-7, 0, -2); the nook's
# crate at its middle is plan (1, 0.5) on the nook, (2, 1.5) on the shed, (4, 4.5) on the yard: (-6, 0, -1.5).
SHED_CRATES = {"/yard/Scenes/shed/Objects/crate_1": [-7.0, 0.0, -2.0],
               "/yard/Scenes/shed/Scenes/nook/Objects/crate_1": [-6.0, 0.0, -1.5]}
# Each yard: how it is made (the hut's, shed's and yard's plans, the children read, the plan the creator edits the
# yard's to after the make, the scene judged), the crates it must stand where (world points worked out by hand), the
# scenes copied under it, and its children gate's answer, measure, reason and findings.
YARDS = [
    # The hut's crate at (-1, 0, 2) is plan (2, 1) on the turned hut, (12, 6) on the yard: (2, 0, 0).
    {"name": "the whole tree", "answer": checks.PASS, "children": 2,
     "crates": {**SHED_CRATES, "/yard/Scenes/hut/Objects/crate_1": [2.0, 0.0, 0.0],
                "/yard/Objects/crate_1": [0.0, 0.0, 0.0]}},
    {"name": "a scene holding none", "scene": "nook", "answer": checks.PASS,
     "reason": "its plan lays out no child scene"},
    # A shed door to the hut 2.5 m up, the hut's door back on its floor, stands the hut 2.5 m up.
    {"name": "a child up a door", "answer": checks.PASS,
     "hut": {**HUT, "openings": [{**DOOR, "at": [0.0, 1.5], "to": "shed"}]},
     "shed": {**SHED, "openings": [{**DOOR, "at": [4.0, 1.5], "sill": 2.5, "to": "hut"}]},
     "crates": {"/yard/Scenes/hut/Objects/crate_1": [2.0, 2.5, 0.0],
                "/yard/Scenes/shed/Objects/crate_1": [-7.0, 0.0, -2.0]}},
    # The hut's crate at its plan (2, 1): (12, 6), (4, 9) and (16.83, 2.12) on the yard; its one tree copied once.
    {"name": "a child held thrice", "yard": THRICE, "read": ("hut",), "answer": checks.PASS, "children": 3,
     "copied": ["hut"], "crates": {"/yard/Scenes/hut_1/Objects/crate_1": [2.0, 0.0, 0.0],
                                   "/yard/Scenes/hut_2/Objects/crate_1": [-6.0, 0.0, 3.0],
                                   "/yard/Scenes/hut_3/Objects/crate_1": [6.8284, 0.0, -3.8787]}},
    {"name": "a child laid out and not read", "read": ("shed",), "answer": checks.FAIL,
     "findings": ("/yard/Scenes/hut: laid out on yard's plan, not in the stage (no scene of the batch: its design is "
                  "not done)",)},
    {"name": "a child planned wider than its hold", "hut": {**HUT, "w": 5.0}, "answer": checks.FAIL,
     "finding": "/yard/Scenes/hut: its plan laid in its hold is 5 x 3 m, its hold 4.0 x 3.0 m"},
    {"name": "a child standing where the plan lays out nothing", "edited": {**YARD, "holds": YARD["holds"][:1]},
     "answer": checks.FAIL, "findings": ("/yard/Scenes/hut: read as a child scene, laid out nowhere on yard's plan",)},
    {"name": "no plan read", "yard": None, "read": (), "answer": checks.UNKNOWN,
     "reason": "no plan of yard read: which child scenes it holds cannot be told"},
]


def the_yard(root, case):
    """The yard's tree over the shed's tree (holding the nook's) and the hut's, as the case makes them; its output and
    the inputs the gate judges `case["scene"]` (the yard by default) with."""
    hut_plan, shed_plan = case.get("hut", HUT), case.get("shed", SHED)
    nook, _ = tree_of(root, "nook", a_scene(root / "made", "nook", (0.0, 0.0, 0.0)), NOOK, {})
    shed, _ = tree_of(root, "shed", a_scene(root / "made", "shed", (6.0, 0.0, -1.0)), shed_plan,
                      {"nook": (nook, NOOK)})
    hut, _ = tree_of(root, "hut", a_scene(root / "made", "hut", (-1.0, 0.0, 2.0)), hut_plan, {})
    trees = {"shed": (shed, shed_plan), "hut": (hut, hut_plan)}
    yard, inputs = tree_of(root, "yard", a_scene(root / "made", "yard", (0.0, 0.0, 0.0)), case.get("yard", YARD),
                           {child: trees[child] for child in case.get("read", ("shed", "hut"))})
    if "edited" in case:
        inputs["plan"].write_text(json.dumps(case["edited"]))
    scene = case.get("scene", "yard")
    if scene != "yard":
        return root / "trees" / scene, {"plan": root / "plans" / f"{scene}.json"}
    return yard, inputs


# --- what each row's resting is judged by ---------------------------------------------------------------------------

# Each inventory (and the scene record laying it, or none) and the support the triage gives every row
# (assembly.resting_rows): None where it keeps what the triage gives it.
WALLED = {"rows": [{"id": "left_wall", "part": "wall"}, {"id": "ceiling_panels", "part": "roof"},
                   {"id": "floor_plates", "part": "floor"}, {"id": "locker", "part": "object"},
                   {"id": "wall_pipes", "anchor": "on:left_wall"}, {"id": "ceiling_rails", "anchor": "on:ceiling_panels"},
                   {"id": "fixed_pipe", "anchor": "on:left_wall", "support": "fixed"},
                   {"id": "crate", "anchor": "on:floor_plates"}, {"id": "suit", "anchor": "on:locker"},
                   {"id": "ribs", "part": "structure", "anchor": "on:left_wall"},
                   {"id": "wall_lamps", "anchor": "on:ribs"}, {"id": "cup", "anchor": "on:ribs"}]}
DOMED = {"rows": [{"id": "dome_module", "part": "object"}, {"id": "antenna", "anchor": "on:dome_module"},
                  {"id": "ceiling_panels", "part": "roof"}, {"id": "ceiling_rails", "anchor": "on:ceiling_panels"}]}
ROOFED = {"rows": [{"id": "hub", "noun": "building"}, {"id": "pyramid", "part": "roof", "anchor": "on:hub"},
                   {"id": "skylight", "part": "opening", "anchor": "on:hub"},
                   {"id": "porch", "part": "roof", "anchor": "on:hub"}, {"id": "lamp", "part": "object", "anchor": "on:hub"}]}
LOCKERED = {"rows": [{"id": "locker", "part": "object"}, {"id": "suit", "anchor": "on:locker"},
                     {"id": "string", "anchor": "on:locker"}, {"id": "crate", "anchor": "on:locker"},
                     {"id": "box", "anchor": "on:locker"}, {"id": "lantern", "anchor": "on:locker"},
                     {"id": "window", "anchor": "on:locker"},
                     {"id": "fixed_suit", "anchor": "on:locker", "support": "fixed"}]}


def laid(name, row_id, how=None, holder="locker_1", hung=False, **more):
    """A scene record's object of this row, laid on its holder `how` (hanging there when `hung`)."""
    on = {"how": how, "holder": [holder], **({"hangs": True} if hung else {})}
    return {"name": name, "row": row_id, "at": [0.0, 0.1, 0.0], **({"on": on} if how else {}), **more}


TRIAGED = [
    # Round 32's docking airlock (2026-10-30): its wall pipes and ceiling rails were judged standing on their wall and
    # panels, leaning and tipping: a row on a wall or ceiling row is mounted there unless it names its own support.
    # Tube's wall lamps on its ribs (settle@tube, 2026-11-12): a wall thing on a built-in row is mounted with it; a cup
    # on it still stands.
    {"name": "the airlock's walls", "inventory": WALLED, "record": None,
     "supports": {"left_wall": None, "ceiling_panels": None, "floor_plates": None, "locker": None,
                  "wall_pipes": "wall", "ceiling_rails": "ceiling", "fixed_pipe": "fixed", "crate": None,
                  "suit": None, "ribs": "wall", "wall_lamps": "wall", "cup": None}},
    # assembly@base (2026-11-12): its antenna on top of its dome module (a ceiling by its words) was judged a ceiling
    # piece touching nothing: laid on its holder's top it stands; laid under it, or with no record, it is mounted.
    {"name": "the base's antenna on top", "inventory": DOMED,
     "record": {"objects": [laid("antenna_1", "antenna", "top", "dome_module_1"),
                            laid("ceiling_rails_1", "ceiling_rails", "ceiling", "ceiling_panels_1")]},
     "supports": {"dome_module": None, "antenna": None, "ceiling_panels": None, "ceiling_rails": "ceiling"}},
    {"name": "the base's antenna with no record", "inventory": DOMED, "record": None,
     "supports": {"dome_module": None, "antenna": "ceiling", "ceiling_panels": None, "ceiling_rails": "ceiling"}},
    # assembly@base (2026-11-12): its glass pyramid roof and its hangar's roof opening, laid on their holders' tops,
    # floated 0.26 and 2.98 m judged standing: a roof or opening on its holder's top is fixed to it; one on a face
    # hangs there, a thing on a top stands.
    {"name": "the base's roofs", "inventory": ROOFED,
     "record": {"objects": [laid(f"{name}_1", name, how, "hub_1") for name, how in
                            (("pyramid", "top"), ("skylight", "top"), ("porch", "face"), ("lamp", "top"))]},
     "supports": {"hub": None, "pyramid": "fixed", "skylight": "fixed", "porch": "hanging", "lamp": None}},
    # Round 32's docking airlock: its spacesuits, hung within their lockers, were judged standing on the lockers'
    # insides and leaned 12 degrees; settle@street (2026-11-11): its lanterns, on the side of their string 24 m up,
    # floated; assembly@square (2026-11-12): its lantern strings, hung between its buildings, floated. A row whose every
    # object hangs within, on a face or between is hanging; one within not hanging (the crate), filling its holder (a
    # door's window), with another object laid otherwise (the box) or naming its own support keeps what it is given.
    {"name": "the airlock's lockers", "inventory": LOCKERED,
     "record": {"objects": [laid("locker_1", "locker"), laid("suit_1", "suit", "within", hung=True),
                            laid("suit_2", "suit", "within", hung=True), laid("crate_1", "crate", "within"),
                            laid("box_1", "box", "within", hung=True), laid("box_2", "box", "face"),
                            laid("window_1", "window", "within", hung=True, fills=True),
                            laid("fixed_suit_1", "fixed_suit", "within", hung=True),
                            laid("lantern_1", "lantern", "face"), laid("lantern_2", "lantern", "face"),
                            laid("string_1", "string", "between"), laid("box_3", "box", "between")]},
     "supports": {"locker": None, "suit": "hanging", "string": "hanging", "crate": None, "box": None,
                  "lantern": "hanging", "window": None, "fixed_suit": "fixed"}},
]


# --- the accepted record and the bakes laid over the toy ------------------------------------------------------------

# The accepted record over the toy: its one lamp, a wall and a flight of stairs written again with collision, and four
# waiting objects: the campgrounds' cairn, whose model is not released (2026-10-12), a design's lamp laid from its
# take's model bench_1 (2026-10-25), a rail whose model the bake has not made, and a rock ground-join joined
# (camp's rocks, stood twice, 2026-10-30).
WAITING_OBJECTS = [
    {"name": "cairn", "row": "cairn", "model": "models/none/none.glb", "at": [0, 0, 0],
     "waiting": "its model comes through the next batch"},
    *({"name": name, "row": row_id, "bake": bake, "at": [1.0, 0.0, 1.0], "rotation": [0.0, 0.0, 0.0, 1.0],
       "kind": "object", "waiting": "its model comes from the bake"}
      for name, row_id, bake in (("lamp_1", "lamp", "bench_1"), ("rail_1", "rail", "rail_1"),
                                 ("rock_1", "rock", "rock_1")))]
RECORDED = {**ONE_LAMP, "objects": WAITING_OBJECTS, "structure": [
    {"name": "wall", "builder": "box", "centre": [0, 1.5, -4], "size": [8, 3, 0.2], "surface": "concrete"},
    {"name": "steps", "builder": "stairs", "foot": [2, 0, 0], "top": [2, 1.2, -1.8], "wide": 1.0, "steps": 6,
     "surface": "concrete"}]}
# The models the toy lays from other places' bakes (its surface data's `elsewhere`): the hangar's parts_rack_1, which
# old_station bakes as parts_rack (2026-10-15), and the hub's wrenches of one take, workshop baking wrench_1 and
# wrench_2 each its own size and not wrench_9, its own bake naming wrench_1 every wrench's baked_as (2026-10-15).
ELSEWHERE = {"parts_rack_1": {"take": "parts_rack-r1", "place": "old_station"},
             **{name: {"take": "wrench-r6", "place": "workshop"} for name in ("wrench_1", "wrench_2", "wrench_9")}}
BAKED_AS = {"parts_rack_1": "parts_rack", "wrench_1": "wrench_1", "wrench_2": "wrench_1", "wrench_9": "wrench_1"}
BAKED_ELSEWHERE = {"old_station": {"parts_rack": {"parts": "parts_rack-r1"}},
                   "workshop": {"wrench_1": {"parts": "wrench-r6"}, "wrench_2": {"parts": "wrench-r6"}}}


def the_recorded_toy(root):
    """The toy seed with a seed floor drawn with no collision (as round three wrote every wall, floor and stair), and
    the settle's inputs over it: the accepted record (RECORDED), the toy's bake (bench_1 and rock_1 made), ground-join
    joining the rock, and the bakes of the places it claims models from; the root and the inputs."""
    from pxr import Sdf, Usd, UsdGeom, UsdShade
    seed = a_toy(root / "out")
    base = Usd.Stage.Open(str(seed.parent / "layers/base.usda"))
    UsdShade.Material.Define(base, f"/{TOY}/Library/concrete")
    bare = UsdGeom.Mesh.Define(base, f"/{TOY}/Structure/seed_floor")
    bare.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("structure")
    base.GetRootLayer().Save()
    inputs = a_record(root, RECORDED)
    bake = root / "bake"
    a_baked_triangle(bake / "made", "bench_1")
    (bake / "baked.json").write_text(json.dumps({"bench_1": {}, "rock_1": {}}))
    (bake / "elsewhere.json").write_text(json.dumps({name: dict(claim, baked_as=BAKED_AS[name])
                                                     for name, claim in ELSEWHERE.items()}))
    (root / "join").mkdir()
    (root / "join/join.json").write_text(json.dumps({"place": TOY, "pieces": {"rock": {}}, "code ground": {}}))
    (root / "surfaces").mkdir()
    (root / f"surfaces/{TOY}.json").write_text(json.dumps({"elsewhere": ELSEWHERE}))
    inputs.update({"surfaces-bake": bake, "surfaces-paint": root / "paint", "ground-join": root / "join",
                   "surfaces": root / f"surfaces/{TOY}.json"})
    for other, made in BAKED_ELSEWHERE.items():
        (root / other).mkdir()
        (root / other / "baked.json").write_text(json.dumps(made))
        inputs.update({f"surfaces-bake@{other}": root / other, f"surfaces-paint@{other}": root / f"paint_{other}"})
    a_baked_triangle(root / "old_station/made", "parts_rack")
    return seed, inputs


def built_of(*found):
    """One built-walls mesh of the boxes `found` ((low, high) each)."""
    return trimesh.util.concatenate([trimesh.creation.box(bounds=bounds) for bounds in found])


OPENING = {"how": "in", "middle": [5.0, 0.0, 0.0], "along": [1.0, 0.0], "wide": 1.2, "tall": 2.1}
JAMBS = [((4.25, -0.2, -1.0), (4.55, 2.8, 1.0)), ((5.45, -0.2, -1.0), (5.75, 2.8, 1.0))]  # built, 0.3 m thick
WALL_FACE = {"how": "wall", "span": [[2.0, 0.1], [2.0, 6.1]], "out": [1.0, 0.0]}  # z 0.1 to 6.1 at x 2, room to +x
FIT = [  # (case, a laid thing's low and high, its relation, its holders, its left, its scale, its foot's middle, words)
    ("a 1.4 x 2.4 m door in its 1.2 x 2.1 m opening", (0.3, 0.0, 2.95), (1.7, 2.4, 3.05), OPENING, (), None,
     (1.2 / 1.4, 2.1 / 2.4, 2.1 / 2.4), (5.0, 0.0, 0.0), "narrowed to 86% across"),
    ("a 1.4 m door between built jambs 0.9 m apart", (0.3, 0.0, 2.95), (1.7, 2.1, 3.05), OPENING, JAMBS, None,
     (0.9 / 1.4, 1.0, 1.0), (5.0, 0.0, 0.0), None),
    ("a 0.6 m door there against the jamb its left edge faces", (0.3, 0.0, 2.95), (0.9, 2.1, 3.05), OPENING, JAMBS,
     (-1.0, 0.0), 1.0, (4.85, 0.0, 0.0), None),
    ("a wall lamp laid at the room's middle, on its wall's face", (4.4, 0.0, 2.9), (4.6, 0.6, 3.9), WALL_FACE, (), None,
     1.0, (2.1, 0.0, 3.4), None),
    ("a 2.4 m door laid on the plan's line of its 2.4 m opening, on the built wall's face", (-1.2, 0.0, 0.05),
     (1.2, 2.4, 0.25), DOORWAY_1, [(wall["low"], wall["high"]) for wall in DOOR_WALLS], None, 1.0, (0.0, 0.0, 0.0),
     None),
    ("a 2 m door there, its hinge on the jamb its own left edge faces", (-1.0, 0.0, 0.05), (1.0, 2.4, 0.25), DOORWAY_1,
     [(wall["low"], wall["high"]) for wall in DOOR_WALLS], (-1.0, 0.0), 1.0, (-0.2, 0.0, 0.0), None),
]
SLANTED = {"how": "in", "middle": [-2.032, 0.2, -2.7], "along": [0.356, -0.934], "wide": 1.0, "tall": 2.5}
WALL_2 = (np.array([-2.85, 0.0, -4.4]), np.array([-2.55, 3.5, -1.1]))  # street's straight wall_2, x -2.85 to -2.55
HOLED = built_of([(-2.85, 0.0, -4.4), (-2.55, 3.5, -3.2)], [(-2.85, 0.0, -2.2), (-2.55, 3.5, -1.1)],
              [(-2.85, 0.0, -3.2), (-2.55, 0.2, -2.2)], [(-2.85, 2.7, -3.2), (-2.55, 3.5, -2.2)])  # its 1 m hole
ACROSS_X = {**SLANTED, "middle": [-2.7, 0.2, -2.032], "along": [-0.934, 0.356]}  # the same, mirrored x for z
HOLE_WALL = [  # (case, an opening, the wall pieces, the built walls, its relation laid there, the degrees it turns
    # within what)
    ("street's door 2 in the hole wall_2 has", SLANTED, WALL_2, HOLED,
     {**SLANTED, "middle": [-2.7, 0.2, -2.7], "along": [0.0, -1.0]}, 20.87, 0.049),
    ("no hole cut in wall_2", SLANTED, WALL_2, built_of([(-2.85, 0.0, -4.4), (-2.55, 3.5, -1.1)]), SLANTED, 0.0, 0.0),
    ("that hole with a post standing in it across the door's middle", SLANTED, WALL_2, trimesh.util.concatenate(
        [HOLED, built_of([(-2.85, 0.0, -2.8), (-2.55, 3.5, -2.6)])]), SLANTED, 0.0, 0.0),
    ("one cut in its own slanted wall, a wall on its line past its end", SLANTED, WALL_2, trimesh.util.concatenate(
        [HOLED, built_of([(-1.9, 0.0, -3.4), (-1.7, 3.5, -3.1)])]), SLANTED, 0.0, 0.0),
    ("the door 2 mirrored, its wall running along x", ACROSS_X,
     (np.array([-4.4, 0.0, -2.85]), np.array([-1.1, 3.5, -2.55])), built_of(
        [(-4.4, 0.0, -2.85), (-3.2, 3.5, -2.55)], [(-2.2, 0.0, -2.85), (-1.1, 3.5, -2.55)],
        [(-3.2, 0.0, -2.85), (-2.2, 0.2, -2.55)], [(-3.2, 2.7, -2.85), (-2.2, 3.5, -2.55)]),
     {**ACROSS_X, "middle": [-2.7, 0.2, -2.7], "along": [-1.0, 0.0]}, -20.87, 0.049),
]
COLLAR_ENDS = [((-1.1, -0.2, -0.45), (1.1, 0.0, -0.15)), ((-1.1, 2.6, -0.45), (1.1, 3.0, -0.15)),  # its sill, lintel
               ((-1.668, -0.2, -0.45), (-1.532, 3.2, 10.49))]  # and its left wall
COLLAR = {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [0.0, 1.0], "wide": 2.2, "tall": 2.6}
ACROSS = [  # (case, an opening, the built pieces about it, the way it is laid along, its middle, the degrees it
    # turns; opening_walls.across)
    ("tube's end opening given its left wall's way", COLLAR, COLLAR_ENDS, [1.0, 0.0], (0.0, 0.0, -0.3), 90.0),
    ("an opening on its own wall", {**COLLAR, "middle": [-1.6, 0.0, 5.0]}, COLLAR_ENDS, [0.0, 1.0], (-1.6, 0.0, 5.0),
     0.0),
    ("an opening on its own wall at its end, a sill running across it", {**COLLAR, "middle": [-1.6, 0.0, -0.3]},
     [((-1.7, -0.2, -0.45), (1.1, 0.0, -0.15)), COLLAR_ENDS[2]], [0.0, 1.0], (-1.6, 0.0, -0.3), 0.0),
]
TUBE_WINDOW = {"how": "in", "middle": [-1.6, 0.8, 2.027], "along": [0.0, 1.0], "wide": 2.0, "tall": 0.8}
TUBE_OWN = (np.array((-1.6511, 0.8, 1.789)), np.array((-1.5489, 1.0439, 2.2646)))  # windows_2's laid box
FIRST_WINDOW = ((-1.6511, 0.8, 1.221), (-1.5489, 1.0439, 1.6966))  # windows_1, laid against the rib
FREE_PART = [  # (case, the boxes laid before windows_2, its free opening's middle and width (None: left as it is))
    ("windows_1 against the rib at z 1.22", [((-1.6511, 0.8, 1.0), (-1.5489, 1.0439, 1.221)), FIRST_WINDOW],
     (-1.6, 0.8, 2.3618), 1.3304),
    ("one on the far wall", [((1.5489, 0.8, 1.221), (1.6511, 1.0439, 1.6966))], None, None),
    ("none", [], None, None),
    ("one leaving no stretch it fits", [((-1.6511, 0.8, 1.0), (-1.5489, 1.0439, 2.8))], None, None),
]
ALONG = {"how": "wall", "span": [[0.1, 0.0], [0.1, 6.0]], "out": [1.0, 0.0]}  # a face at x 0.1, z 0 to 6
KEPT_OUT = [  # (case, the built walls, how deep before the face (None: the holes through it), the runs found in z)
    ("a 1 m hole, z 2 to 3, a step's margin past its open rays", built_of([(0.0, 0.0, 0.0), (0.1, 3.0, 2.0)],
                                                                      [(0.0, 0.0, 3.0), (0.1, 3.0, 6.0)]),
     None, [(1.975, 3.025)]),
    ("a wall 0.2 m before the face, z 4 to 6, within 0.5 m", built_of([(0.3, 0.0, 4.0), (0.4, 3.0, 6.0)]), 0.5,
     [(3.975, 6.025)]),
    ("that wall, beyond 0.1 m", built_of([(0.3, 0.0, 4.0), (0.4, 3.0, 6.0)]), 0.1, []),
    ("a wall crossing the face at z 5: past it is outside the room", built_of([(0.0, 0.0, 5.0), (0.5, 3.0, 5.1)]), 0.5,
     [(4.975, 6.025)]),
]
ON_WALL = [  # (case, a thing's low and high, the KEPT_OUT case it keeps out of (None: nothing), its foot's middle)
    ("a 0.5 m screen in the hole", (0.1, 1.0, 2.25), (0.2, 1.5, 2.75), KEPT_OUT[0][0], (0.15, 1.0, 1.725)),
    ("that screen with nothing to keep out of", (0.1, 1.0, 2.25), (0.2, 1.5, 2.75), None, (0.15, 1.0, 2.5)),
    ("a 1 m rack 0.5 m deep laid at z 5, before the wall", (0.1, 1.0, 4.5), (0.6, 1.5, 5.5), KEPT_OUT[1][0],
     (0.35, 1.0, 3.475)),
]


def a_fitted_world(prims):
    """An in-memory stage of `prims` under /toy: ("cube", size, at, degrees) an Xform holding a cube of that size,
    turned `degrees` about the up axis, then moved to `at`; ("points", points) a mesh of those points alone; ("box",
    low, high) an Xform holding a box mesh's corners from `low` to `high` (a_built_box)."""
    from pxr import Gf, Usd, UsdGeom
    stage = Usd.Stage.CreateInMemory()
    for name, (kind, *made) in prims.items():
        if kind == "box":
            a_built_box(stage, f"/{TOY}/{name}", *made)
            continue
        if kind == "points":
            UsdGeom.Mesh.Define(stage, f"/{TOY}/{name}").GetPointsAttr().Set([Gf.Vec3f(*point) for point in made[0]])
            continue
        size, at, degrees = made
        xform = UsdGeom.Xform.Define(stage, f"/{TOY}/{name}")
        UsdGeom.Cube.Define(stage, f"/{TOY}/{name}/geo").AddScaleOp().Set(Gf.Vec3f(*(side / 2 for side in size)))
        xform.AddTransformOp().Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), degrees))
                                   * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*at)))
    return stage


RUN, NORMAL = np.array([0.6, 0.8]), np.array([0.8, -0.6])  # the slanted wall's run and the way across it
SLANTED_JAMBS = [[x, y, z] for x, z in [RUN * along + NORMAL * deep for along in (-1.5, -0.5, 0.5, 1.5)
                                        for deep in (0.3, 0.5)] for y in (0.0, 2.0)]
DOORWAY = {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [1.0, 0.0], "wide": 1.2, "tall": 2.2}
SLANTED_OPENING = {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [0.6, 0.8], "wide": 1.0, "tall": 2.0}
SHELL_WALL = {"how": "wall", "span": [[-3.0, 0.1], [3.0, 0.1]], "out": [0.0, 1.0]}
FACADE = {"how": "face", "holder": ["facade_1"], "out": [0.0, -1.0]}
FITTED = [  # (case, its prims, its entries (name, row, relation), each fit's scale (None: unread), foot's middle
    # (its height to 1e-6) and size (None: unread), the
    # names left unfitted, the doors the held gate passes in their openings, how near (atol), a door's passage (name,
    # low, high), the opening's spot on its wall's near face (opens, wall, spot), the width of the opening each named
    # one is held in when its fit narrowed it (None: its whole one))
    ("#36 garage and street: a door, a pipe and lamp on its wall, a shop door and rack on a facade",
     {"Objects/pipe_1": ("cube", (3.2, 1.0, 0.32), (0.0, 0.5, 2.0), 0.0),
      "Objects/lamp_1": ("cube", (0.4, 0.3, 0.1), (0.0, 2.05, 0.15), 0.0),
      "Objects/door_1": ("cube", (1.0, 2.0, 0.1), (0.0, 1.0, 3.0), 0.0),
      "Shell/wall_2": ("cube", (1.2, 0.1, 0.2), (0.0, -0.05, 0.0), 0.0),
      "Objects/facade_1": ("cube", (6.0, 3.0, 0.4), (0.0, 1.5, 5.0), 0.0),
      "Objects/shop_door_1": ("cube", (1.0, 2.0, 0.1), (2.0, 1.0, 3.0), 0.0),
      "Objects/drying_rack_1": ("cube", (1.2, 0.1, 0.4), (2.0, 0.05, 3.0), 0.0)},
     [("pipe_1", "pipe", SHELL_WALL), ("lamp_1", "lamp", SHELL_WALL), ("drying_rack_1", "drying_rack", FACADE),
      ("shop_door_1", "shop_door", FACADE), ("door_1", "door", DOORWAY)],
     {"door_1": (None, (-0.1, 0.0, -0.1), (1.0, 2.0, 0.1)), "pipe_1": (0.75, (-1.8, 0.0, 0.22), (2.4, 0.75, 0.24)),
      "shop_door_1": (None, (2.0, 0.0, 4.75), (1.0, 2.0, 0.1)),
      "drying_rack_1": (1.0, (0.9, 0.0, 4.6), (1.2, 0.1, 0.4))},
     ["lamp_1"], [], 1e-8, ("door_1", (-0.6, 0.0, -0.9), (0.6, 1.8, 0.85)), None, {}),
    ("#36 cockpit: a door turned to swing out of a slanted wall's opening, a deck's corner and a wall under its sill",
     {"Shell/wall_1": ("points", SLANTED_JAMBS),
      "Shell/deck_1": ("points", [(0.72, y, -0.54) for y in (-0.2, 0.0)] + [(-5.0, y, -5.0) for y in (-0.2, 0.0)]),
      "Shell/wall_2": ("points", [(x, y, z) for x, z in [RUN * along + NORMAL * 0.8 for along in (-0.5, 0.5)]
                                  for y in (-2.0, 0.0)]),
      "Objects/door_1": ("cube", (1.0, 2.0, 0.1), (0.0, 1.0, 2.0), -53.130102)},
     [("door_1", "door", SLANTED_OPENING)],
     {"door_1": (None, (0.4, 0.0, -0.3), None)}, [], ["door_1"], 1e-3, None,
     (-NORMAL, "Shell/wall_1", (0.24, 0.0, -0.18)), {}),
    ("tube: windows_2's cut opening overlapping windows_1's, laid before it against a rib",
     {**{f"Structure/{name}": ("box", low, high) for name, (low, high) in (
         ("wall_4_9", ((-1.668, -0.2, 0.336), (-1.532, 0.8, 2.336))),
         ("wall_4_7", ((-1.668, -0.2, 1.027), (-1.532, 0.8, 3.027))),
         ("wall_4_8", ((-1.668, 1.6, 0.336), (-1.532, 3.2, 3.027))),
         ("structural_ribs_2", ((-1.6, 0.0, 1.021), (1.6, 3.2, 1.221))),
         ("structural_ribs_3", ((-1.6, 0.0, 2.724), (1.6, 3.2, 2.924))))},
      **{f"Objects/{name}": ("box", (-1.6511, 0.8, middle - 0.2378), (-1.5489, 1.0439, middle + 0.2378))
         for name, middle in (("windows_1", 1.336), ("windows_2", 2.027))}},
     [(name, "windows", {**TUBE_WINDOW, "middle": [-1.6, 0.8, middle]})
      for name, middle in (("windows_1", 1.336), ("windows_2", 2.027))],
     {"windows_1": (1.0, (-1.6, 0.8, 1.7785), (0.1022, 0.2439, 0.4756)),
      "windows_2": (1.0, (-1.6, 0.8, 2.3701), (0.1022, 0.2439, 0.4756))},
     [], ["windows_1", "windows_2"], 1e-4, None, None, {"windows_1": None, "windows_2": 1.0107}),
]
RECESSED = [  # (case, the rack's relation, whether it hangs in the shop door's recess cut in its facade)
    ("a rack laid on the facade", FACADE, False),
    ("a rack whose relation names the door the recess was cut for", {**FACADE, "room": 0.0}, True),
]
OUTWARD = {"how": "wall", "span": [[-2.5, -4.7], [2.5, -4.7]], "out": [0.0, -1.0], "why": "against the wall"}
ROOM = {"Structure/wall_1": ((-5.0, 0.0, -6.2), (5.0, 3.0, -5.9)),
        "Structure/wall_3": ((-5.0, 0.0, 5.0), (5.0, 3.0, 5.2))}
ALCOVE = {"Structure/wall_1": ((-1.0, 0.0, -6.2), (1.0, 3.0, -5.9)),
          "Structure/wall_2": ((0.8, 0.0, -6.2), (1.0, 3.0, -5.6)),
          "Structure/wall_3": ((-5.0, 0.0, 5.0), (5.0, 3.0, 5.2))}


def laid_off(name, row, off):
    """A thing of this row laid with its back on its span `off` out of ROOM's wall_1 (outer face z -6.2), 3 m deep;
    its prim's box and its entry."""
    span = {"how": "wall", "span": [[-2.5, -6.2 - off], [2.5, -6.2 - off]], "out": [0.0, -1.0],
            "why": "against the wall"}
    return {f"Objects/{name}": ((-2.0, 0.0, -9.2 - off), (2.0, 2.5, -6.2 - off))}, (name, row, span)


PASSED = [  # (case, its solid boxes (path: low, high), its entries (name, row, relation), the fits that pass or draw
    # a thing through or to its wall (name: how, moved, holders), each thing's high corner after, the things
    # held_faults then finds held). workshop, settle@workshop 2026-11-10 and 11-11
    ("a tunnel laid out of its round room's alcove, through the alcove's walls, and a cabinet in the room",
     {**ALCOVE, "Objects/glass_tunnel_1": ((-2.0, 0.0, -8.0), (2.0, 2.5, -4.7)),
      "Objects/cabinet_1": ((-0.5, 0.0, -6.0), (0.5, 2.0, -5.0))},
     [("glass_tunnel_1", "glass_tunnel", OUTWARD), ("cabinet_1", "cabinet", {**OUTWARD, "out": [0.0, 1.0]})],
     {"glass_tunnel_1": ("past", 1.5, ["wall_1", "wall_2"])}, {"glass_tunnel_1": (2.0, 2.5, -6.2)},
     ["glass_tunnel_1"]),
    ("the same tunnel past the walls would reach a deck's raised edge farther out, more than its depth",
     {**ALCOVE, "Structure/deck_2": ((-1.0, -0.2, -9.2), (1.0, 0.1, -9.0)),
      "Objects/glass_tunnel_2": ((-2.0, 0.0, -8.0), (2.0, 2.5, -4.7))},
     [("glass_tunnel_2", "glass_tunnel", OUTWARD)], {}, {"glass_tunnel_2": (2.0, 2.5, -4.7)}, []),
    ("a tunnel past its room's floor, inside its walls' box, reaching into wall_1",
     {**ROOM, "Structure/deck_1": ((-5.0, -0.2, -5.0), (5.0, 0.0, 5.0)),
      "Objects/glass_tunnel_1": ((-1.0, 0.0, -7.0), (1.0, 2.5, -5.0))},
     [("glass_tunnel_1", "glass_tunnel", OUTWARD)], {"glass_tunnel_1": ("past", 1.5, ["wall_1"])},
     {"glass_tunnel_1": (1.0, 2.5, -6.2)}, ["glass_tunnel_1"]),
    ("that tunnel in a room with no deck reads in the room",
     {**ROOM, "Objects/glass_tunnel_1": ((-1.0, 0.0, -7.0), (1.0, 2.5, -5.0))},
     [("glass_tunnel_1", "glass_tunnel", OUTWARD)], {}, {"glass_tunnel_1": (1.0, 2.5, -4.7)}, []),
    *[(case, {**ROOM, **prims}, [entry], drawn, {entry[0]: (2.0, 2.5, high)}, list(drawn))
      for case, (prims, entry), drawn, high in (
          ("a tunnel laid 0.2 m out of its wall's face is drawn back to within GAP of it",
           laid_off("glass_tunnel_1", "glass_tunnel", 0.2), {"glass_tunnel_1": ("drawn", 0.198, None)}, -6.2025),
          ("a pipe laid so is no passage and is left", laid_off("pipe_1", "pipe", 0.2), {}, -6.4),
          ("a tunnel 1.2 m off, past OUT_MOST, is left", laid_off("glass_tunnel_2", "glass_tunnel", 1.2), {}, -7.4),
          ("a tunnel already within GAP is left", laid_off("glass_tunnel_3", "glass_tunnel", 0.004), {}, -6.204))],
]


def test_a_place_stands_from_its_accepted_outputs(tmp_path, monkeypatch):
    """A place waits on every layer its design needs, shows its neighbours from their own outputs, and stands each
    child scene at its hold on its plan: each place of LAYERED is judged by the layers gate; each world of NEIGHBOURED
    is judged the seed's way, made through neighbours.make, and judged again with the outputs it was made from gone,
    and the ASKED queries are answered from RECORDS; each yard of YARDS is made through scene_tree.make, opened, and
    judged by the children gate; the plans it reads are the creator's kept ones, each child's declared, and a plan
    laying out a scene above it is refused. Each inventory of TRIAGED gets the support its rows rest by; the toy, its
    seed floor failing the collision gate, takes the accepted RECORDED (its old record gone, its walls colliding, its
    waiting objects named) and its bakes the settle's way (grounded.take_bakes): the design's lamp laid under Objects
    from its take's model, the joined rock no object and no longer named, the models it lays from other places' bakes
    claimed under the names those bake them under; a toy with no record row keeps its seed's.
    Break: score/stages/assembly/__init__.py: resting_rows' `if row["id"] in given and not row.get("support") else
        row` -> `if False else row` (the airlock's walls)
    Break: score/stages/assembly/mounted.py: `return {**found, **on_built_in(rows, holders, found, built_in)}` ->
        `return found`, or structure_mounted.py's `and holder_kind(rows[row_id]) in ("wall", "ceiling")` -> `` (the
        airlock's walls: the cup mounted)
    Break: score/stages/assembly/on_tops.py: standing's `if kind != "ceiling" or row_id not in topped}` -> `}`, or
        laid_on_tops' `if all(topped)}` -> `}` (the base's antenna on top)
    Break: score/stages/assembly/roof_tops.py: roofs' `if row.get("part") in ROOF_PARTS and row["id"] in topped}` ->
        `if row["id"] in topped}` or `if row.get("part") in ROOF_PARTS}`; score/stages/assembly/__init__.py:
        `**roof_tops.roofs(inventory["rows"], record), ` -> `` (the base's roofs)
    Break: score/stages/assembly/fitting.py: `and bool(on.get("hangs"))` -> ``; score/stages/assembly/__init__.py:
        hung_within's `if all(hung)}` -> `if any(hung)}` (the airlock's lockers)
    Break: score/stages/assembly/mounted.py: on_faces' `if all(faced)}` -> `if any(faced)}`, or resting_rows'
        `**on_faces(record or {}), ` dropped (the airlock's lockers, the base's roofs)
    Break: score/stages/assembly/__init__.py: resting_rows' `**hung_between.rows(record or {}),` dropped, or
        hung_between.py's rows `if all(hung)}` -> `if any(hung)}` (the airlock's lockers)
    Break: score/stages/assembly/__init__.py: `solid = sum(fault["what"] != "model" for fault in faults)` -> `solid =
        0` (the recorded toy's seed floor)
    Break: score/stages/assembly/record.py: `edit.Add(f"/{place}/{name}", Sdf.Path.emptyPath)` -> `pass` (the old
        wall kept), or `laid, waiting = without_waiting(record)` -> `laid, waiting = record, []` (the cairn laid)
    Break: score/stages/assembly/made_waiting.py: `scope = f"/{place}/Objects" if "bake" in entry else
        f"/{place}/Fixtures"` -> `scope = f"/{place}/Fixtures"` (the design's lamp)
    Break: score/stages/assembly/made_waiting.py: `if entry.get("waiting") and entry.get("row") in joined:` ->
        `if False:`, or joined_rows' `return frozenset(json.loads(...)["pieces"])` -> `return frozenset()`;
        score/stages/assembly/grounded.py: `made_waiting.lay(folder, place, bake, made_waiting.joined_rows(inputs))`
        -> `made_waiting.lay(folder, place, bake)` (the joined rock laid again)
    Break: score/stages/assembly/baked.py: `else claims[model]["baked_as"]` -> `else model` (parts_rack_1, wrench_9),
        `baked.get(model, {}).get("parts") == claim["take"]` -> `False` (wrench_2), `if baked_as == model:` -> `if
        True:` (parts_rack_1 read under its own name), or claiming_places' `claim["place"]` -> `claim["take"]`
    Break: score/stages/assembly/__init__.py: `"physics": "settle", ` -> `` (a crate on the floor)
    Break: score/stages/assembly/__init__.py: `waiting = [f"{name}@{place}" for name in needed if name not in
        origin["layers"]]` -> `waiting = []` (the design taking four)
    Break: score/stages/assembly/__init__.py: `if origin["unplaced sounds"]:` -> `if False:` (a sound placed nowhere)
    Break: score/stages/assembly/neighbours.py: `layer.UpdateCompositionAssetDependency(f"../../{other}/{other}.usda",
        f"../{PLACES}/{other}/{other}.usda")` -> `pass` (the launch)
    Break: score/stages/assembly/neighbours.py: `if scene_record.written(other) and other not in parts()]` -> `if
        scene_record.written(other)]` (ASKED: the square's neighbours)
    Break: score/stages/assembly/neighbours.py: `left.append(lost_gap(stage_file(out).stem, other))` -> `pass` (a lost
        far city)
    Break: score/stages/assembly/neighbours.py: `glob("*.usd*")` -> `glob("*.usda")` (the stairwell)
    Break: score/stages/assembly/neighbours.py: `if owns:` -> `if False:` (the old station)
    Break: score/stages/assembly/neighbours.py: `owns = has_own_ground(layers, place)` -> `owns = True` (the airlock)
    Break: score/stages/assembly/scene_tree.py: `matrix[:3, :3] = turn.T` -> `matrix[:3, :3] = turn` (the whole tree)
    Break: score/stages/assembly/scene_tree.py:
        `shift = corner + east * start[0] + south * start[1] + up * level - turn @ child_corner`
        -> `shift = corner + east * start[0] + south * start[1] + up * level` (the whole tree)
    Break: score/stages/assembly/scene_tree.py: `+ up * level` -> `` (a child up a door)
    Break: score/stages/scene_record/plan.py: `return round(math.cos(turn), 12), round(math.sin(turn), 12)` ->
        `return round(math.cos(turn)), round(math.sin(turn))` (a child held thrice)
    Break: score/stages/assembly/scene_tree.py: `standing = sorted(child for child, hold in laid.items() if hold["place"] in children)` ->
        `standing = sorted(child for child in laid if child in children)` (a child held thrice)
    Break: score/stages/assembly/scene_tree.py: `children = sorted(set(laid) | read | standing)` -> `children =
        sorted(read | standing)` (a child laid out and not read)
    Break: score/stages/assembly/scene_tree.py: `if abs(wide - hold["w"]) > SIZED` -> `if False` (a child planned
        wider than its hold)
    Break: score/stages/assembly/scene_tree.py: `return [f"/{scene}/{SCENES}/{prim_name(child)}: read as a child
        scene, laid out nowhere on {scene}'s plan"]` -> `return []` (a child standing where the plan lays out nothing)
    Break: score/stages/assembly/scene_tree.py: `if plan is None:` -> `if False:` (no plan read)
    Break: score/stages/assembly/scene_tree.py: `if above:` -> `if False:` (the nook holding the yard)
    Break: score/stages/assembly/scene_tree.py: `named.update({f"plan {child}": plan_pattern(child) for child in
        held(place)})` -> `pass` (the yard's declared plans)
    The layered seed (a read-only seed from the store; Batch 1, 2026-10-25: every assembly refused the save) is made
    through make_from_seed: its copy takes the record over the base, each layer stage's read-only layer between the
    others in record.ORDER (light over motion over effects) in place of the seed's of the same name, the root playing
    the motion's 480 frames; the cycle lamp the motion keys and the light sets plays the motion's keys (the airlock's
    cycle light, 2026-10-16) while the steady one keeps 20, and no taken layer file changes; the sound layer is the
    sound stage's (camp, launch and square kept the seed's, 2026-10-12): the room tone under Sound/Room, the hum at the
    fan's row, the door's sound at its own second (2.5 x the stage's rate in frames), each file under its world name,
    the hum on a row the stage lacks and the motion on the door left out named as placed nowhere. The light stage's live
    lamps taken after (a layer and no assets, 2026-10-13) leave no stale assets/light behind. A walkway tube 6 m long
    with 2 m bays lays its bay piece three times, each with its spot; a room's pieces stand as laid.
    Break: score/stages/assembly/__init__.py: `shutil.copytree(source, out / part, copy_function=shutil.copyfile)` ->
        `shutil.copytree(source, out / part)`
    Break: score/stages/assembly/record.py: `return ORDER.index(stem) if stem in ORDER else ORDER.index("base") - 0.5`
        -> `return 0`
    Break: score/stages/assembly/__init__.py: `stage_root.endTimeCode = max(taken.endTimeCode, stage_root.endTimeCode if
        stage_root.HasEndTimeCode() else 0)` -> `pass`
    Break: score/stages/assembly/__init__.py: `shutil.rmtree(root.parent / assets, ignore_errors=True)` -> `pass`
    Break: score/stages/assembly/__init__.py: `held.insert(held.index(f"./{LAYERS['light'][1]}"), f"./{MOTION_KEYS}")`
        -> `held.append(f"./{MOTION_KEYS}")`
    Break: score/stages/assembly/sounds.py: `start=float(use["at"]) * rate` -> `start=float(use["at"])`
    Break: score/stages/assembly/sounds.py: `if not target or not target.IsActive():` -> `if not target:`
    Break: score/stages/assembly/sounds.py: `unplaced.append(f"{use['sound']} (object): no prim of the row or name
        {use['on']} on the stage")` -> `pass`
    Break: score/stages/assembly/record.py: `if "bay" not in kit or not record.get("tube_length"):` -> `if True:`
    Each place of RESTED is judged by the resting gate the stage's table names, on the world files the stage declares
    (its rules, its kit, the seed's inventory found by name in the declared folder, earth-seed's own); each suit of HUNG
    is hung on its locker's back; the baked place's crate carries its bake's hash and the seed's as repaint_of, so the
    owner's pick still holds and breaks without it, its rocket laid from a released file takes the bake of its model,
    and its tower, whose bake moved the frame, is refused.
    Break: score/stages/assembly/resting_within.py: `rules_file=inputs["resting rules"]` -> `rules_file=assembly.REPO /
        "data/checks/resting.json"` (the sunk plate, no kit group named)
    Break: score/stages/__init__.py: `"resting": resting_within.judge_resting` -> `"resting": assembly.judge_resting`,
        or resting_within.py: `and not planned_overlap(fault, within)]` -> `]` (a window laid within its door)
    Break: score/stages/assembly/resting_within.py: laid_within's `== "within"}` -> `in ("within", "top")}` (a window
        laid on its door's top)
    Break: score/stages/assembly/__init__.py: `"inventories": "{home}/design/inventory"` -> `"inventories":
        "{data}/inventory"` (earth-seed's folder)
    Break: score/stages/assembly/__init__.py: `return pathlib.Path(inventories) / pathlib.Path(named).name if named else
        None` -> `return pathlib.Path(named) if named else None` (the sunk plate, its kit group named)
    Break: score/stages/assembly/fitting.py: back_way's `return axis, -sign` -> `return axis, sign`
    Break: score/stages/assembly/fitting.py: back_way's `if not np.any(across & (sign * (points[:, axis] -
        middle[axis]) > 0)):` -> `if False:` (open-fronted, the room's middle behind its back)
    Break: score/stages/assembly/baked.py: `before.get("score:repaint_of") or before.get("score:model_sha256")` ->
        `None` (the crate's pick)
    Break: score/stages/assembly/baked.py: `abs(old_box[end][axis] - new_box[end][axis]) > BOX_TOLERANCE` -> `False`
        (the tower)
    The laid toy's waiting entries, their rows made by the bake, are laid by made_waiting.lay where LAID_AT stands
    them (the cairn on its spot, the ship turned onto its pad, the garage doors on their modules' faces) and named no
    longer; LAID names each garage door's fit (the built one's plane and that it hangs in its recess), and the held
    gate measures both there.
    Break: score/stages/assembly/made_waiting.py: `move = Gf.Vec3d(at[0] - (least[0] + most[0]) / 2, at[1] - least[1],
        at[2] - (least[2] + most[2]) / 2)` -> `move = Gf.Vec3d(*at)` (the cairn)
    Break: score/stages/assembly/made_waiting.py: `root.RemoveProperty(WAITING)` -> `pass`
    Break: score/stages/assembly/made_waiting.py: `on_pads.turned(entry, record, placement(entry, low, high), low,
        high)` -> `placement(entry, low, high)` (the ship left across its pad)
    Break: score/stages/assembly/on_pads.py: `if entry.get("on") or entry.get("fills") or entry.get("under roof"):` ->
        `if entry.get("on"):` (the crane turned), `and on_piece(footprint(turn, low, high), outline).all():` -> `:`
        (the barge turned), `if not on_piece(laid, outline).all() and` -> `if` (the cart turned), or
        `float(entry.get("low", -1.0)) >= 0.0` -> `False` (no pad)
    Break: score/stages/assembly/fitting.py: `target[side] = kept_within(foot[side], hold_low[side] + below,
        hold_high[side] - above,` -> `target[side] = kept_within(foot[side], hold_low[side], hold_high[side],`
        (garage_door_1)
    Break: score/stages/assembly/made_waiting.py: `laid_by_relations(stage, out, place, record, objects, baked)` -> `pass`
    Break: score/stages/assembly/fitting.py: `target[axis] = face + sign * half[axis]` -> `target[axis] = foot[axis]`
        (garage_door_1)
    Break: score/stages/assembly/fitting.py: `face = front_face(surface, axis, sign, side, span, (target[1], target[1]
        + size[1] * scale))` -> `face = None` (garage_door_2)
    Break: score/stages/assembly/fitting.py: `if cut is not None:` -> `if False:` (garage_door_2)
    Break: score/stages/assembly/made_waiting.py: `{model: entry.get("cuts") for model, entry in (baked or
        {}).items()}` -> `{}` (garage_door_2)
    Break: score/stages/assembly/fitting.py: `target[side] = cut[0][side] + half_wide if below > above else` ->
        `target[side] = (cut[0][side] + below + cut[1][side] - above) / 2 if True else` (garage_door_2)
    Break: score/stages/assembly/fitting.py: `target[axis] = face if cut is not None else face + sign * half[axis]` ->
        `target[axis] = face + sign * half[axis]` (garage_door_2)
    Break: score/stages/assembly/fitting.py: `**({"room": 0.0} if fitted_on.get("hung") else {})` -> `**{}`
        (garage_door_2)
    The held world (#72, so it never comes back silently; #36, street's three restaurant doors) is judged by the
    `held` gate the stage's table names: it fails by name on a door laid 1 m beside its module's face (1.0 m), a door
    on a face 0.55 m too narrow for it and its recess, a window in no opening, a lamp held by nothing, a crate left at
    the room's middle, and two doors laid on one facade face 0.58 m apart (overlapping 0.42 m); the door on its face,
    a sign above the doors, a door on the facade's other face and doors held side by side pass. Cables said under
    their desk fail laid on its top and pass held under it, laid at its foot; a box within its shelf unit laid on its
    top stands off nothing, one through its top stands off it.
    Break: score/stages/assembly/fitting.py: `if narrow > HELD_MOST:` -> `if False:` (door_3)
    Break: score/stages/assembly/fitting.py: `elif distance > HELD_MOST:` -> `elif False:` (door_2)
    Break: score/stages/assembly/fitting.py: `if entry.get("fills") and not (on and on["how"] in ("in", "face",
        "within", "top")):` -> `if False:` (window_1)
    Break: score/stages/assembly/fitting.py: placement_faults' `if wrong:` -> `if False:`; on_holder's
        `hold_low[1] if on.get("under") else` dropped (cables under a desk left up in it)
    Break: score/stages/assembly/fitting.py: off_holder's `min(max(0.0, high[1] - hold_high[1]), abs(low[1] -
        hold_high[1]))` -> `max(0.0, high[1] - hold_high[1])` (a box on its shelf unit's top off it)
    Break: score/stages/assembly/held_apart.py: `if along > fitting.HELD_MOST and tall > fitting.HELD_MOST:` -> `if
        False:` (the entries)
    Break: score/stages/__init__.py: `judge={"held": held_apart.judge_held,` -> `judge={"held": check.judge,` (the
        entries named by the relations' faults alone)
    Each world of HELD_JUDGED is judged so too, and by held_faults, held_apart.overlapping and short_doors. #36:
    hangar's and garage's shell walls stand 0.15 m behind the plan's line, so a door laid on the line hung 0.04 to 0.15
    m in front of its wall and left its jamb and sill as it swung (motion@garage grounded). A 2.4 x 2.4 x 0.2 m door in
    DOORWAY_1, 2.4 m wide and 2.66 m tall at z 0.15, the built wall's sill and lintel from z -0.276 to 0 (its jamb
    beside the opening never counts), is fitted (FIT) with its middle on the wall's room face, z 0; the held gate
    measures it there, passes it there and fails one left on the plan's line 0.15 m off. A 2 m door, narrower than its
    opening, stands against the jamb its own left edge faces, its hinge on its jamb (motion@garage: the 2.01 m round
    door, centred in its 2.41 m opening, swung on a hinge 0.2 m off its jamb), and passes there. Each is named 0.26 m
    short of its opening's height (hangar's doorway, a wall panel shrunk to 0.72 m tall) among the gate's findings,
    which never fail it: only a take made again, a paid one, mends it (coordinator, 2026-10-30). Tube (2026-11-12):
    its plan draws only its long walls; its end opening of ACROSS (middle x 0, z 0), given the left wall's way (z) 1.6
    m off, is turned onto the end wall its shell built across it (its sill and lintel along x, their line at z -0.3), a
    quarter turn; one on its own wall keeps its way. Its windows_2's cut opening (z 1.03 to 3.03) overlaps windows_1's,
    laid before it against the rib at z 1.22 (to z 1.70); of FREE_PART it is laid in the stretch windows_1 leaves free
    (1.70 to 3.03), never in one too short for it; one on the far wall, or none, leaves the opening as it is, and so
    does one that leaves no stretch it fits; its world in FITTED is fitted so and the held gate judges it in that
    stretch.
    Break: score/stages/assembly/fitting.py: `spot[axis] = face` -> `pass`
    Break: score/stages/assembly/fitting.py: `if wide is not None and abs(lined) >= 0.9` -> `if False and abs(lined)
        >= 0.9`
    Break: score/stages/assembly/fitting.py: `for way in (None, on["along"], np.negative(on["along"]))]` -> `for way in
        (None,)]`
    Break: score/stages/assembly/fitting.py: `if short > HELD_MOST:` -> `if False:`
    Break: score/stages/assembly/held_apart.py: `*(f"{name}: {words}" for name, words, _ in
        fitting.short_doors(record, laid))))` -> `))`
    Break: score/stages/assembly/fitting.py: held_faults' `held = walls if on["how"] in ("in", "ramp") else` ->
        `held = [] if on["how"] in ("in", "ramp") else`
    Break: score/stages/assembly/opening_walls.py: `if near(own) or not near(2 - own):` -> `if True:` (the collar
        door left along z), or `-> if not near(2 - own):` (the side door turned onto the sill across its wall's end)
    Break: score/stages/assembly/opening_free.py: `if not taken:` -> `if True:` (tube's windows_2 left on windows_1's
        jamb), or its `if finish - begin >= wide - 1e-9]` -> `]` (laid in the 0.23 m stretch past a box it never
        fits); fitting.py's `for key in ("middle", "along", "wide")` -> `("middle", "along")` (the gate judges it off
        its whole opening)
    Each thing of FIT is fitted by its relation: a door shrunk to its opening's height and held across its width
    alone to it (or to the clear between its built jambs, the lab's entry passage, motion@lab round 35), its foot's
    middle at the opening's middle on its sill, a narrow one against the jamb its left edge faces; a wall lamp with
    its back on its wall's face, slid along to the face's nearest point. An opening of HOLE_WALL on a slanted plan
    wall (settle@street, 2026-11-11: restaurant door 2 stood 0.15 m in wall_2) is laid along the straight wall its
    hole is cut in, turned 20.9 degrees (mirrored, along x, -20.9), and left as it is with no hole there, a post
    standing in the hole across its middle, or cut in its own slanted wall. A roller shutter's clear run stands on
    the higher of the pavement's two steps under it and ends at the nearer of the facade folding back across it and
    a wall past that. KEPT_OUT finds the holes through a wall (walkway and shiplock's screens, 2026-11-11) and the
    walls standing before its face (street's drying rack 3 stood 0.05 m in wall_8), and each thing of ON_WALL laid
    there keeps out of them.
    Break: score/stages/assembly/fitting.py: `scale[run_axis] *= (end - start) / wide` -> `pass`
    Break: score/stages/assembly/fitting.py: `            start = max(start, far)` -> `            pass`
    Break: score/stages/assembly/fitting.py: hole_wall's `if not inside:` -> `if True:` (laid in an uncut wall), or
        its `along[axis // 2] = 1.0 if` -> `along[2 - axis // 2] = 1.0 if` (turned across its wall), or its `if
        own_jambs(on, mesh, height):` -> `if False:` (moved out of its own slanted wall)
    Break: score/stages/assembly/fitting.py: opening_clear's `floor = max(` -> `floor = min(` (its sill left in the
        pavement), or its `reach.append(float(met.min())` -> `reach.append(float(met.max())` (held past the fold)
    Break: score/stages/assembly/fitting.py: `spot = start + run * along + out * deep * scale / 2` ->
        `spot = start + run * along`
    Break: score/stages/assembly/fitting.py: fitted's `clear = [*clear, *wall_holes(faces(), entry["on"], ...)]` ->
        `pass` is caught by the sweep's walkway only; wall_holes' `open_at = ~near...` -> `open_at = near...` (walkway's
        and shiplock's screens hung in the holes cut through their walls)
    Break: score/stages/assembly/fitting.py: walls_ahead's `<= deep]] = True` -> `<= 0.0]] = True` (the rack left in
        the wall folding back in front of its face), or its `taken |= alongs >= past if` -> `taken |= False if` (the
        face past the wall crossing it left free)
    held@garage, @habitat, @workshop (2026-10-30): a glass tunnel or corridor tube the concept shows meeting its
    module's wall from outside, laid against that wall, reached 0.09 to 0.30 m into the built wall; it joins the place
    through it, as a door stands in its opening, so the held gate excuses its wall, never a deck. A pipe laid against
    the same wall that reaches into it is still named (HELD_JUDGED's tunnel and pipe). Each world of PASSED is fitted
    through fitting.fitted and its things judged by held_faults where they then stand. workshop (settle@workshop,
    2026-11-10): its front glass tunnel, laid out from a chord 1.48 m inside its round wall's hatch alcove, stood
    through the alcove's walls. A tunnel laid outside its room (its middle past the walls' box) reaching into a wall is
    moved out along its `out` past each wall it reaches into, up to its own depth (3.3 m, moved 1.5 m), and held off
    the face it was moved out to; a cabinet in the room reaching into the same wall is not; past the walls 1.5 m out a
    tunnel that would reach into a deck's raised edge farther out, 4.5 m in all, more than its depth, is left.
    workshop (2026-11-11): its round room's walls' box held its tunnels outside it, so they were left across its doors.
    A tunnel past the room's floor (deck_1, z -5 to 5) inside the walls' box (z -6.2 to 5.2) reaching into wall_1 is
    outside the room and moved out past it; in a room with no deck it reads in the room and is left. settle@workshop
    (2026-11-11): its glass tunnels stood outside its twelve built walls on its plan's eight facets, 0.06 to 0.19 m off
    the nearest, touching nothing. Laid with its back on its span 0.2 m out of wall_1's outer face, a tunnel is drawn
    back along its `out` until it stands within GAP of the wall (GAP / 2 off), never in it, and the held gate judges it
    on the face it now stands on; a pipe laid so is no passage and is left; a tunnel 1.2 m off (past OUT_MOST) is left,
    as is one already within GAP.
    Break: score/stages/assembly/fitting.py: `if not (passes(entry) and static.split("_")[0] == "wall")]` -> `]`
    Break: score/stages/assembly/fitting.py: `set(str(entry.get("row") or "").split("_")) & set(PASSING))` ->
        `set(str(entry.get("row") or "").split("_")) & set(CLIMBING))`
    Break: score/stages/assembly/fitting.py: moved_past's `**laid_face({**entry["on"], ...` -> `**{}` (workshop's
        front tunnel named 1.48 m off the wall it was moved out past)
    Break: score/stages/assembly/fitting.py: in_room's `return room[0] <= point[0] <= room[2] and room[1] <=
        point[2] <= room[3]` -> `return False` (the cabinet in the room is pushed through its wall), or its `if
        len(decks):` -> `if False:` (workshop's tunnel past its round room's floor left in its wall)
    Break: score/stages/assembly/fitting.py: past_walls' `for _ in built:` -> `for _ in built[:1]:` (the second
        tunnel is moved 1.5 m into deck_2)
    Break: score/stages/assembly/fitting.py: moved_past's `max(OUT_MOST, across(entry["on"]["out"], high - low))` ->
        `OUT_MOST` (the tunnel, 1.5 m in, is left)
    Break: score/stages/assembly/fitting.py: fitted's `fits += passages.drawn_in(stage, place, walled)` dropped
        (workshop's tunnel left 0.2 m off its wall, touching nothing)
    Break: score/stages/assembly/passages.py: drawn_back's `moved += distance - GAP / 2` -> `moved += distance` (the
        tunnel drawn onto the wall's face, 0 m off it), or drawn_in's `**stood_on(...)` -> `**{}` (the drawn tunnel
        named 0.2 m off the face it was laid on), or drawn_in's `if fitting.passes(entry)` -> `if True` (the pipe
        drawn back onto the wall too)
    Each world of FITTED is fitted through fitting.fitted. #36, garage 2026-10-30: its doors swung out of the room
    clear, but pipes laid along the walls inside ran across both doorways, so nobody could walk through; street's
    drying racks, laid on their facade under its doors (hung on the facade, no opening), stood in the doors' swing
    either way. A 1 x 2 x 0.1 m door in its 1.2 m opening of a shell wall from z -0.1 to 0.1, swinging out of the room
    (to -z), hangs on the outer face against its left jamb, x -0.6 to 0.4, z -0.15 to -0.05; its passage is the
    opening's width, x -0.6 to 0.6, a person's 1.8 m from its foot, and a step (0.75 m) beyond either face, z -0.9 to
    0.85. A 3.2 m pipe laid on the wall's room face across the doorway, out of the door's swing but in its passage,
    goes to the longest stretch beside it, shrunk to 2.4 m, x -3 to -0.6; a lamp on the wall over the doorway at 1.9
    to 2.2 m, above the passage, stays. A 1 x 2 x 0.1 m shop door laid on a facade box (x -3 to 3, its face toward the
    street z 4.8), swinging to the street, stands x 1.5 to 2.5 on it; a 1.2 m drying rack laid on the facade at its
    foot goes to the nearest stretch of the face out of its swing that holds it, x 0.3 to 1.5, whole; it never hangs
    in a recess the bake cut in the facade (RECESSED), which only a thing whose relation names one (its `room`: the
    door it was cut for) hangs in (street's racks hung in its doors' recesses). #36, cockpit 2026-10-30: its rear
    doors, in an opening of a slanted wall (its boxes say nothing of its faces), stood on the plan's line 0.37 m in
    front of the built wall and swung their kind's way into its jamb. A 1 m opening at the origin along (0.6, 0.8),
    its built wall's jambs from 0.3 to 0.5 m across it the way (0.8, -0.6): a door turned so its own -z points that
    way (its kind's swing) stands with its foot middle on the far face, (0.4, -0.3), and the held gate passes it
    there; one swinging the other way on the near face, (0.24, -0.18). A deck's corner 0.9 m out beside it is
    no wall face (camp's dome door, by no built wall, was hung on its deck's corner), nor is a wall under its sill
    0.8 m out (greenhouse's door, in its dome, was hung on the tops of the walls under it, motion round 34).
    Break: score/stages/assembly/fitting.py: `recess_of(recesses, axis, sign, foot, box) if "room" in on else None` ->
        `recess_of(recesses, axis, sign, foot, box)`
    Break: score/stages/assembly/fitting.py: `return swing_box(stage, path), passage_box(*world_box(stage, path),
        by_name[leaf]["on"], built)` -> `return (swing_box(stage, path),)`
    Break: score/stages/assembly/fitting.py: `low[axis], high[axis] = min([low[axis], *faces]) - STEP,
        max([high[axis], *faces]) + STEP` -> `low[axis], high[axis] = min([low[axis], *faces]), max([high[axis],
        *faces])`
    Break: score/stages/assembly/fitting.py: `high[1] = low[1] + PASSAGE_TALL` -> `pass` (the passage as tall as the
        door: the lamp over it moved)
    Break: score/stages/assembly/fitting.py: `walled = how in ("wall", "face") and name not in leaves` -> `walled =
        how == "wall" and name not in leaves`
    Break: score/stages/assembly/fitting.py: `entry["on"]["how"] in ("in", "face") and swings(entry["row"])` ->
        `entry["on"]["how"] == "in" and swings(entry["row"])`
    Break: score/stages/assembly/fitting.py: `scale, target, face = on_face(low, high, on, box, surface, recesses,
        [*clear, *mounted])` -> `scale, target, face = on_face(low, high, on, box, surface, recesses)`
    Break: score/stages/assembly/fitting.py: `surface = wall_points(stage, place)` -> `surface = None`
    Break: score/stages/assembly/fitting.py: `or wall[beside, 1].max() < head - WALL_REACH:` -> `or False:`
    Break: score/stages/assembly/fitting.py: `spot[[0, 2]] += way * float(max(faces))` -> `spot[[0, 2]] += way *
        float(min(faces))`
    Break: score/stages/assembly/fitting.py: `return float(np.linalg.norm(off - normal * np.clip(off @ normal, -2 *
        WALL_REACH, 2 * WALL_REACH)))` -> `return float(np.linalg.norm(off))`
    Each toy of GROUNDED is made through make_from_seed: each mesh of its terrain's made ground is bound in the taken
    (read-only) ground layer to the surface its row's kind takes from the library of the scene holding that row (its
    own, else one read beside: ground_scenes, the base, its ground's top scene; none for the base itself), laid under
    its own Library where it lacks it, its missing note gone, so the placeholder gate passes it; a row no library gives
    a surface (the sea) keeps its finish named missing. Each row of GROUND_SURFACE takes what the square's library
    gives it.
    Break: score/stages/assembly/__init__.py: `finish_ground(inputs, out / root.name, folder.name)` -> `None`
    Break: score/stages/assembly/ground_finish.py: `prim.RemoveProperty("score:surface:missing")` -> `None`
    Break: score/stages/assembly/ground_finish.py: `found |= set(next(([top] for top in sorted(ground["tops"])` ->
        `found |= set(next(([top] for top in []`
    Break: score/stages/assembly/ground_finish.py: `lay_surface(stage, place, surface, library)` -> `None`
    Break: score/stages/assembly/ground_finish.py: `return palette_library.shell_surface("deck", library) if made else
        None` -> `return None`"""
    for case, low, high, on, holders, left, scale, foot, words in FIT:
        laid_scale, laid_at, said, _ = fitting.fit(low, high, on, holders, left=left)
        assert (laid_scale == scale if isinstance(scale, float) else np.allclose(laid_scale, scale)), \
            f"{case}: scaled {laid_scale}"
        assert np.allclose(laid_at, foot) and (words is None or words in said), f"{case}: laid at {laid_at}, {said}"
    for case, opening, piece, mesh, walled, degrees, within in HOLE_WALL:
        laid_along, turned = fitting.hole_wall(opening, [piece], mesh)
        assert laid_along == walled and abs(turned - degrees) <= within, f"{case}: {laid_along}, {turned} degrees"
    from score.stages.assembly import opening_free, opening_walls
    for case, opening, ends, along, middle, degrees in ACROSS:
        turned, turn = opening_walls.across(opening, 0.0, ends)
        assert turned["along"] == along and np.allclose(turned["middle"], middle) and abs(turn) == degrees and \
            (turned == opening) == (degrees == 0.0), f"{case}: {turned}, {turn} degrees"
    for case, before, middle, wide in FREE_PART:
        free = opening_free.free_part(TUBE_WINDOW, *TUBE_OWN, before)
        assert (free is TUBE_WINDOW if middle is None else np.allclose(free["middle"], middle)
                and free["wide"] == wide), f"{case}: {free}"
    shutter = trimesh.creation.box(bounds=[(-1.5, 0.0, -0.175), (1.5, 3.0, 0.175)])  # 3 m along x, 0.35 m deep
    around = built_of([(-2.0, 0.0, 0.0), (2.0, 0.2, 1.0)], [(-2.0, 0.0, -1.0), (2.0, 0.1, 0.0)],  # pavement, a step
                      [(1.2, 0.0, 0.0), (1.3, 3.0, 1.0)], [(1.6, 0.0, -1.0), (1.7, 3.0, 0.0)])  # the fold, a wall past
    floor, start, end = fitting.opening_clear(np.asarray(shutter.vertices), {"along": [1.0, 0.0]}, around)
    assert abs(floor - 0.2) < 1e-6 and abs(end - 1.2) < 1e-6 and start == -np.inf, (floor, start, end)
    kept_out = {}
    for case, mesh, deep, spans in KEPT_OUT:
        band = (1.0, 1.5)
        kept_out[case] = (fitting.wall_holes(mesh, ALONG, band) if deep is None
                          else fitting.walls_ahead(mesh, ALONG, band, deep))
        found = [(round(float(run[:, 2].min()), 3), round(float(run[:, 2].max()), 3)) for run in kept_out[case]]
        assert found == spans, f"{case}: {found}"
    for case, low, high, keeping, foot in ON_WALL:
        _, laid_at = fitting.on_wall(np.array(low), np.array(high), ALONG, kept_out[keeping] if keeping else ())
        assert np.allclose(laid_at, foot), f"{case}: laid at {laid_at}"
    for case, prims, things, boxes, unfitted, held, near, passage, near_face, openings in FITTED:
        stage = a_fitted_world(prims)
        entries = [{"name": name, "row": kind, "on": on} for name, kind, on in things]
        fits = {fit["name"]: fit for fit in fitting.fitted(stage, TOY, entries, {name for name, _, _ in things})}
        for name, (scale, foot, size) in boxes.items():
            low, high = np.array(fits[name]["low"]), np.array(fits[name]["high"])
            stood = fitting.foot_middle(low, high)
            assert (scale is None or fits[name]["scale"] == scale) and abs(stood[1] - foot[1]) < 1e-6 \
                and np.allclose(stood[[0, 2]], np.array(foot)[[0, 2]], atol=near) \
                and (size is None or np.allclose(high - low, size, atol=near)), f"{case}: {name} fitted {fits[name]}"
        assert not set(unfitted) & set(fits), f"{case}: moved {sorted(set(unfitted) & set(fits))}"
        record = {"objects": [{"name": name, "on": on, "fills": True} for name, _, on in things if name in held]}
        laid = {"walls": [{"name": wall, "low": list(low), "high": list(high)}
                          for wall, (low, high) in fitting.walls(stage, TOY)],
                "objects": [{"name": name, "low": fits[name]["low"], "high": fits[name]["high"]} for name in held],
                "fitted": list(fits.values())}
        assert fitting.held_faults(record, laid) == [], f"{case}: not held in their openings"
        for name, wide in openings.items():
            assert (fits[name].get("opening") or {}).get("wide") == wide, f"{case}: {name} held in {fits[name]}"
        if passage:
            name, low, high = passage
            [on] = [on for thing, _, on in things if thing == name]
            found = fitting.passage_box(*fitting.world_box(stage, f"/{TOY}/Objects/{name}"), on,
                                        [box for _, box in fitting.walls(stage, TOY)])
            assert np.allclose(found[0], low) and np.allclose(found[1], high), f"{case}: {name}'s passage {found}"
        if near_face:
            opens, wall, spot = near_face
            [on] = [on for _, _, on in things if on["how"] == "in"]
            found = fitting.opening_spot(on, opens=opens, points=[np.array(prims[wall][1])])
            assert np.allclose(found, spot), f"{case}: the near face's spot {found}"
    from pxr import Usd
    for case, prims, things, passed, highs, held in PASSED:
        stage = Usd.Stage.CreateInMemory()
        for path, (low, high) in prims.items():
            a_solid_box(stage, f"/{TOY}/{path}", low, high)
        entries = [{"name": name, "row": kind, "on": on} for name, kind, on in things]
        fits = fitting.fitted(stage, TOY, entries, {name for name, _, _ in things})
        found = {fit["name"]: (fit["how"], fit["moved"], fit["holder"]) for fit in fits
                 if fit["how"] in ("past", "drawn")}
        assert found == passed, f"{case}: {fits}"
        stood = {name: fitting.world_box(stage, f"/{TOY}/Objects/{name}") for name in highs}
        for name, high in highs.items():
            assert np.allclose(stood[name][1], high, atol=1e-6), f"{case}: {name} stands {stood[name]}"
        laid = {"objects": [{"name": name, "low": list(stood[name][0]), "high": list(stood[name][1])} for name in held],
                "fitted": fits}
        record = {"objects": [entry for entry in entries if entry["name"] in held]}
        assert fitting.held_faults(record, laid) == [], f"{case}: {fitting.held_faults(record, laid)}"
    facade_box = (np.array([-3.0, 0.0, 4.8]), np.array([3.0, 3.0, 5.2]))
    recess = (np.array([1.5, 0.0, 4.8]), np.array([2.5, 2.1, 5.0]))
    for case, on, hangs in RECESSED:
        hung = fitting.on_face(np.array([1.4, 0.0, 4.4]), np.array([2.6, 0.1, 4.8]), on, facade_box, None,
                               [recess])[2][1]
        assert bool(hung) == hangs, f"{case}: hangs {hung}"
    for case in LAYERED:
        name = case["name"]
        output, inputs = layered(tmp_path / "layered", case)
        if case["design"] is not None:
            needs = assembly.needed_layers(case["design"], KINDS)
            assert needs == case["needs"], f"{name}: needs {needs}"
        verdict = assembly.judge_layers(output, inputs, None)
        assert verdict.answer == case["answer"], f"{name}: {verdict.answer}, {verdict.reason}, {verdict.findings}"
        if "waits" in case:
            assert verdict.findings == case["waits"], f"{name}: waits on {verdict.findings}"
    assert neighbours.record_of("nowhere") == {}
    with monkeypatch.context() as patched:
        patched.setattr(neighbours, "record_of", lambda place: RECORDS.get(place, {}))
        patched.setattr(neighbours.scene_record, "written", lambda place: place in ("square", "launch"))
        for query, place, answer in ASKED:
            got = getattr(neighbours, query)(place)
            assert (bool(got) if isinstance(answer, bool) else got) == answer, f"{query}({place}): {got}"
    for case in NEIGHBOURED:
        name = case["name"]
        root = tmp_path / "neighboured" / name.replace(" ", "_")
        inputs = the_neighbours(root, case)
        if "seed" in case:
            before = neighbours.judge_neighbours(the_seed_s_way(root, case, inputs), {}, None)
            assert before.answer == checks.FAIL and before.measures["faults"] == case["seed"]["faults"], \
                f"{name}, the seed's way: {before}"
            if "a finding" in case["seed"]:
                assert any(case["seed"]["a finding"] in finding for finding in before.findings), \
                    f"{name}, the seed's way: {before.findings}"
            if "every finding" in case["seed"]:
                assert all(case["seed"]["every finding"] in finding for finding in before.findings), \
                    f"{name}, the seed's way: {before.findings}"
        out = root / "out"
        out.mkdir()
        neighbours.make(inputs, out, 0, {})
        shutil.rmtree(root / "kept")
        verdict = neighbours.judge_neighbours(out, {}, None)
        assert verdict.answer == checks.PASS, f"{name}: {verdict}"
        if "shown" in case:
            assert verdict.measures["shown"] == case["shown"], f"{name}: {verdict.measures}"
        if "gap" in case:
            lost = f"/{case['place']}/Places/{case['gap']}"
            found = json.loads((out / neighbours.GAPS).read_text())["gaps"]
            assert [entry["objects"] for entry in found] == [[lost]], f"{name}: gaps {found}"
            assert f"{case['gap']}: shown by the plan" in verdict.reason, f"{name}: {verdict.reason}"
            assert verdict.findings and all(finding.startswith(lost) for finding in verdict.findings), \
                f"{name}: {verdict.findings}"
        stage = opened(out / f"{case['place']}.usda")
        for path, active in case.get("active", {}).items():
            assert stage.GetPrimAtPath(path).IsActive() == active, f"{name}: {path} active {not active}"
        if "removed" in case:
            shutil.rmtree(out / "places" / case["removed"])
            assert neighbours.judge_neighbours(out, {}, None).answer == checks.FAIL, f"{name}: {case['removed']} gone"
    for number, case in enumerate(YARDS):
        name = case["name"]
        root = tmp_path / str(number)
        output, inputs = the_yard(root, case)
        if "crates" in case:
            stage = opened(output / "yard.usda")
            stood = {path: crate_at(stage, path) for path in case["crates"]}
            assert stood == case["crates"], f"{name}: crates stand at {stood}"
        if "copied" in case:
            copied = sorted(path.name for path in (output / "scenes").iterdir())
            assert copied == case["copied"], f"{name}: copied {copied}"
        verdict = scene_tree.judge_children(output, inputs, None)
        assert verdict.answer == case["answer"], f"{name}: {verdict.answer}, {verdict.reason}, {verdict.findings}"
        if "children" in case:
            assert verdict.measures["children"] == case["children"], f"{name}: {verdict.measures}"
        if "reason" in case:
            assert verdict.reason == case["reason"], f"{name}: {verdict.reason}"
        if "findings" in case:
            assert verdict.findings == case["findings"], f"{name}: {verdict.findings}"
        if "finding" in case:
            assert case["finding"] in verdict.findings, f"{name}: {verdict.findings}"
    kept = tmp_path / "0" / "plans"  # the whole tree's plans: the yard's, shed's, hut's and nook's
    monkeypatch.setattr(scene_tree, "KEPT", kept)
    assert scene_tree.files("yard") == {"plan": "{home}/design/plans/yard.json",
                                        "plan hut": "{home}/design/plans/hut.json",
                                        "plan shed": "{home}/design/plans/shed.json"}
    assert scene_tree.files("nook") == {"plan": "{home}/design/plans/nook.json"}
    (kept / "nook.json").unlink()
    assert scene_tree.plan_path("nook") is None and scene_tree.held("shed") == ["nook"]
    (kept / "nook.json").write_text(json.dumps({**NOOK, "holds": [{"place": "yard"}]}))
    with pytest.raises(ValueError, match="cannot hold itself"):
        scene_tree.held("yard")
    for case in TRIAGED:
        found = {row["id"]: row.get("support")
                 for row in assembly.resting_rows(case["inventory"], case["record"])["rows"]}
        assert found == case["supports"], f"{case['name']}: {found}"
    from score import stages
    from score.stages import earth_seed
    laid_from = pathlib.Path(earth_seed.design_files("hub")["design inventory"])
    assert str(laid_from.parent) == assembly.FILES["inventories"], (laid_from, assembly.FILES["inventories"])
    judge_resting = {check.name: inspect.unwrap(check.judge) for check in stages.ASSEMBLY.checks}["resting"]
    for number, case in enumerate(RESTED):
        name = case["name"]
        output, world = a_resting_place(tmp_path / "rested" / str(number), case)
        evidence = output.parent / "settled.json"
        evidence.write_text(json.dumps({"objects": {}}))
        verdict = judge_resting(output, world, evidence)
        assert verdict.answer == case["answer"], f"{name}: {verdict.answer}, {verdict.reason}, {verdict.findings}"
        if "finding" in case:
            assert case["finding"] in " ".join(verdict.findings), f"{name}: {verdict.findings}"
        if "reason" in case:
            assert case["reason"] in verdict.reason, f"{name}: {verdict.reason}"
    for name, walls, middle, (axis, sign, moved) in HUNG:
        hung = fitting.hung_back(SUIT, np.array(walls), SUIT.min(axis=0), SUIT.max(axis=0), room_middle=middle)
        assert hung is not None and hung[:2] == (axis, sign) and abs(hung[2] - moved) < 1e-9, f"{name}: {hung}"
    import picks
    from pxr import Sdf
    baked_stage, inventory, hashes = a_baked_place(tmp_path / "baked")
    base = baked_stage.parent / assembly.BASE_LAYER
    assembly.lay_fixtures_baked(base, "rocket")
    assembly.stamp_baked_hash(base, "box", tmp_path / "baked/models/plank.gltf")
    with pytest.raises(ValueError, match="moved the model's frame"):
        assembly.lay_fixtures_baked(base, "tower")
    held_stage = opened(baked_stage)
    crate = held_stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
    assert crate.GetAttribute("score:model_sha256").Get() == hashes["plank"]
    assert crate.GetAttribute("score:repaint_of").Get() == hashes["box"]
    assert picks.check(baked_stage, inventory) == ([], 1)
    spec = Sdf.Layer.FindOrOpen(str(base)).GetPrimAtPath(f"/{PLACE}/Fixtures/rocket")
    assert [ref.assetPath for ref in spec.referenceList.prependedItems] == ["../assets/rocket.usdc"]
    assert spec.attributes["score:model"].default == "rocket"
    spec = spec.layer.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
    spec.RemoveProperty(spec.attributes["score:repaint_of"])
    spec.layer.Save()
    found, _ = picks.check(baked_stage, inventory)
    assert len(found) == 1 and "not the owner's pick" in found[0]["why"], found
    import export
    from score.stages.assembly import grounded
    recorded = tmp_path / "recorded"
    seed, inputs = the_recorded_toy(recorded)
    before = assembly.judge_collision(seed.parent, {}, None)
    assert before.answer == checks.FAIL and before.measures == {"uncolliding": 1, "models without collider": 0}, before
    assert before.findings[0].startswith(f"/{TOY}/Structure/seed_floor: "), before.findings
    assert assembly.take_record(inputs, seed.parent, TOY) == f"scene-record@{TOY}"
    after = assembly.judge_collision(seed.parent, {}, None)
    assert after.answer == checks.PASS and after.measures == {"uncolliding": 0, "models without collider": 0}, \
        after.findings
    stage = opened(seed)
    for path, stands in (("Structure/old_wall", False), ("Lights/old_lamp", False), ("Lights/light_1", True),
                         ("Objects/fan_1", True), ("Structure/wall", True), ("Structure/steps", True),
                         ("Fixtures/cairn", False)):
        assert bool(stage.GetPrimAtPath(f"/{TOY}/{path}")) == stands, f"the recorded toy: {path} stands {not stands}"
    waits = [f"objects {entry['name']}: {entry['waiting']}" for entry in WAITING_OBJECTS]
    assert list(stage.GetPrimAtPath(f"/{TOY}").GetAttribute(assembly.WAITING).Get()) == waits
    for model in ("bench_1", "rock_1"):
        a_box_asset(seed.parent / f"assets/{model}.usdc", (-1.0, 0.0, -1.0), (1.0, 1.0, 1.0))
    assert made_waiting.joined_rows(inputs) == {"rock"} and made_waiting.joined_rows({}) == frozenset()
    taken, laid = [], []
    lay = made_waiting.lay
    with monkeypatch.context() as patched:  # the bakes' own export stubbed: only what is laid, and from where, is read
        patched.setattr(baked, "take_bake", lambda *args: taken.append(args))
        patched.setattr(made_waiting, "lay", lambda *args: laid.extend(lay(*args)) or laid)
        grounded.take_bakes(inputs, seed.parent, TOY)
    assert laid == ["bench_1"], laid  # the made model lay reports laid, never rock_1 (joined) or rail_1 (unmade)
    assert taken == [(recorded / "bake", recorded / "paint", seed.parent),
                     (recorded / "old_station", recorded / "paint_old_station", seed.parent,
                      {"parts_rack_1": "parts_rack"}),
                     (recorded / "workshop", recorded / "paint_workshop", seed.parent,
                      {"wrench_1": "wrench_1", "wrench_2": "wrench_2", "wrench_9": "wrench_1"})], taken
    stage = opened(seed)
    lamp = stage.GetPrimAtPath(f"/{TOY}/Objects/lamp_1")
    assert lamp.GetChild("geo").IsValid() and lamp.GetAttribute("score:row").Get() == "lamp", lamp
    assert lamp.GetAttribute("score:model").Get() == "bench_1" and not stage.GetPrimAtPath(f"/{TOY}/Fixtures")
    import stage_inputs
    assert lamp.GetAttribute("score:model_sha256").Get() == stage_inputs.model_hash(recorded / "bake/made/bench_1.gltf")
    assert not stage.GetPrimAtPath(f"/{TOY}/Objects/rock_1")
    assert list(stage.GetPrimAtPath(f"/{TOY}").GetAttribute(assembly.WAITING).Get()) == [waits[0], waits[2]]
    other = a_toy(tmp_path / "unrecorded")
    said = assembly.take_record({"scene": recorded / f"record/record/{TOY}.json", "kit": inputs["kit"]},
                                other.parent, TOY)
    assert "unverified" in said and opened(other).GetPrimAtPath(f"/{TOY}/Structure/old_wall"), said
    monkeypatch.setattr(baked, "DESIGN_SURFACES", recorded / "surfaces")
    assert baked.claiming_places(TOY) == ["old_station", "workshop"] and baked.claiming_places("nook") == []
    made = recorded / "old_station/made"
    renamed = assembly.renamed_model(made, "parts_rack", "parts_rack_1", recorded / "renamed")
    geometry = export.model_geometry(export.model_file(renamed, "parts_rack_1"))
    assert len(geometry["positions"]) == 3, geometry
    assert assembly.renamed_model(made, "parts_rack", "parts_rack", recorded / "x") == made
    from pxr import UsdMedia
    layered_seed, inputs = a_layered_seed(tmp_path / "layered_seed")
    sums = {name: hashlib.sha256((inputs[name] / f"layers/{name}.usda").read_bytes()).hexdigest()
            for name in ("light", "motion")}
    out = tmp_path / "layered_seed/out"
    out.mkdir()
    assembly.make_from_seed(inputs, out, layered_seed.parent, {})
    root = out / f"{TOY}.usda"
    held = Sdf.Layer.FindOrOpen(str(root))
    held.Reload()
    assert list(held.subLayerPaths) == [f"./layers/{name}.usda" for name in (
        "edit", "characters", "sound", "motion_keys", "light", "motion", "effects", "base")], list(held.subLayerPaths)
    assert held.endTimeCode == 480.0 and (out / "assets/light/earth.png").read_bytes() == b"png", held.endTimeCode
    assert all(path.stat().st_mode & 0o200 for path in out.rglob("*") if path.is_file())
    for name, digest in sums.items():
        for folder in (inputs[name], out):
            assert hashlib.sha256((folder / f"layers/{name}.usda").read_bytes()).hexdigest() == digest, (name, folder)
    stage = opened(root)
    assert stage.GetPrimAtPath(f"/{TOY}/Lights/light_1") and not stage.GetPrimAtPath(f"/{TOY}/Structure/old_wall")
    cycle = stage.GetPrimAtPath(f"/{TOY}/Lights/cycle").GetAttribute("inputs:intensity")
    assert cycle.GetNumTimeSamples() == 2 and cycle.Get(12) == 50.0, cycle.Get(12)
    assert stage.GetPrimAtPath(f"/{TOY}/Lights/steady").GetAttribute("inputs:intensity").Get() == 20.0
    tone = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{TOY}/Sound/Room/tone"))
    assert tone.GetFilePathAttr().Get().path == "../assets/sound/tone.ogg"
    assert (out / "assets/sound/tone.ogg").read_bytes() == b"tone"
    assert stage.GetPrimAtPath(f"/{TOY}/Objects/fan_1/Sound")
    door = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{TOY}/Objects/door_1/Sound_0"))
    assert door.GetStartTimeAttr().Get().GetValue() == 2.5 * stage.GetTimeCodesPerSecond()
    unplaced = json.loads((out / "origin.json").read_text())["unplaced sounds"]
    assert unplaced == ["hum (object): no prim of the row or name pump on the stage",
                        f"hum (motion): no moving prim /{TOY}/Objects/door_2 on the stage"], unplaced
    live = tmp_path / "layered_seed/live"
    (live / "layers").mkdir(parents=True)
    (live / "layers/light.usda").write_text("#usda 1.0\n")
    assembly.take_layer(live, root, "layers/light.usda", "assets/light")
    assert not (out / "assets/light").exists()
    tube = {"bay": 2.0, "pieces": [{"kind": "tube_bay", "tube_part": "bay"}]}
    bays = assembly.laid_pieces(tube, {"tube_length": 6.0})
    assert len(bays) == 3 and all("spot" in piece for piece in bays), bays
    assert assembly.laid_pieces({"pieces": tube["pieces"]}, {}) == tube["pieces"]
    laid_toy, laid = a_laid_toy(tmp_path / "laid")
    assert laid == ["cairn", "ship", "crane", "barge", "cart", "module_1", "door_1", "module_2", "door_2"], laid
    stage = opened(laid_toy)
    for name, (scope, low, high, tolerance) in LAID_AT.items():
        stood = fitting.world_box(stage, f"/{TOY}/{scope}/{name}")
        assert np.allclose(stood, (low, high), atol=tolerance), f"the laid toy: {name} stands {stood}"
    assert stage.GetPrimAtPath(f"/{TOY}/Fixtures/cairn").GetAttribute("score:row").Get() == "cairn"
    assert not stage.GetPrimAtPath(f"/{TOY}").HasAttribute(assembly.WAITING)
    fits = {fit["name"]: fit for fit in json.loads((laid_toy.parent / made_waiting.LAID).read_text())["fitted"]}
    assert sorted(fits) == ["garage_door_1", "garage_door_2"], fits
    assert fits["garage_door_1"]["how"] == "face" and fits["garage_door_1"]["scale"] == 1.0, fits
    assert fits["garage_door_2"]["scale"] == 0.75 and fits["garage_door_2"]["face"] == 38.8125 and \
        fits["garage_door_2"]["hung"], fits
    held = assembly.judge_held(laid_toy.parent, {}, None)
    assert held.answer == checks.PASS and held.measures == {"not held": 0, "worst off": 0.0}, held
    from score.stages.assembly import held_apart
    [judge_held] = [check.judge for check in stages.ASSEMBLY.checks if check.name == "held"]
    for number, (case, (held_record, held_laid), answer, measures, faults, short) in enumerate(HELD_JUDGED):
        held_out = tmp_path / f"held_{number}"
        (held_out / assembly.RECORD).parent.mkdir(parents=True)
        (held_out / assembly.RECORD).write_text(json.dumps(held_record))
        (held_out / made_waiting.LAID).write_text(json.dumps(held_laid))
        verdict = judge_held(held_out, {}, None)
        assert verdict.answer == answer and verdict.measures == measures, f"{case}: {verdict}"
        assert verdict.findings == tuple(f"{name}: {words}" for name, words, _ in (*faults, *short)), \
            f"{case}: {verdict.findings}"
        measured = [*fitting.held_faults(held_record, held_laid), *held_apart.overlapping(held_record, held_laid)]
        assert measured == faults and fitting.short_doors(held_record, held_laid) == short, f"{case}: {measured}"
    apart = {**HELD_LAID, "objects": [{"name": "entry_1", **at_facade(42.0, 0.0)},
                                      {"name": "entry_2", **at_facade(43.2, 0.0)}]}
    assert held_apart.overlapping(HELD_RECORD, apart) == []
    rows = {"desk": {"id": "desk"}, "cables": {"id": "cables", "anchor": "on:desk", "where": "under desk"}}
    for case, on, faults in PLACED:
        found = fitting.placement_faults({"objects": [{"name": "cables_1", "row": "cables", "on": on}]}, rows)
        assert found == faults, f"{case}: {found}"
    for case, low, high, on, holder, off, within, at_foot in OFF:
        low, high = np.array(low), np.array(high)
        stands = fitting.off_holder(low, high, "within", on, holder)
        assert abs(stands - off) <= within, f"{case}: stands {stands} off"
        if at_foot:
            scale, foot = fitting.on_holder(low, high, "within", on, holder)
            assert scale == 1.0 and abs(foot[1]) < 1e-9, f"{case}: laid {scale} at {foot}"
    import placeholders
    from pxr import UsdShade
    for row, surface in GROUND_SURFACE:
        assert assembly.ground_surface(row, SQUARE) == surface, row
    for case in GROUNDED:
        root = tmp_path / "grounded" / case["name"].replace(" ", "_")
        inputs = a_grounded_toy(root, case, monkeypatch)
        beside = (assembly.ground_scenes(TOY), assembly.ground_scenes("base"))
        assert beside == (case["beside"], case["base beside"]), f"{case['name']}: reads {beside} beside"
        out = root / "out"
        out.mkdir()
        assembly.make_from_seed(inputs, out, inputs["seed"], {})
        stage = opened(out / f"{TOY}.usda")
        for name in case["bound"]:
            prim = stage.GetPrimAtPath(f"/{TOY}/Outside/{name}")
            bound = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
            assert bound.GetPath() == f"/{TOY}/Library/lunar_regolith" and \
                not prim.HasAttribute("score:surface:missing"), f"{case['name']}: {name} bound to {bound}"
            if "recipe" in case:
                assert bound.GetPrim().GetAttribute("score:recipe").Get() == case["recipe"], case["name"]
        water = stage.GetPrimAtPath(f"/{TOY}/Outside/water")
        assert bool(water) == case["sea"], case["name"]
        if case["sea"]:
            assert not UsdShade.MaterialBindingAPI(water).ComputeBoundMaterial()[0]
            assert water.GetAttribute("score:surface:missing").Get()
        faults = [fault["prim"] for fault in placeholders.check(out / f"{TOY}.usda")]
        assert faults == case["faults"], f"{case['name']}: {faults}"
