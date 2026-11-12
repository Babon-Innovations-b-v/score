"""A place's assembly stands from its accepted outputs, never from the seed's own parts: each layer stage's output in
its place in the root's order, the accepted record over the seed's record prims, the bakes over the seed's models
(carrying their hash and the owner's pick), the sound stage's layer, the neighbours it shows read from their own
assemblies, each child scene at its hold on the plan, and each design object laid by what holds it at its built size
(base's garage door on its module's front, a door in its opening, a monitor on its console, a lamp on its wall); its
gates (layers, collision, resting, neighbours, child
scenes) fail or wait on what is missing. Every expected point and name is worked out by hand from the toy places
below. No spend, no machine: toy stages made here, a drop run in which nothing moved.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

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
from score.stages.assembly import (baked, fitting, made_waiting, neighbours, record, resting_within,  # noqa: E402
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

def a_window_in_its_door(root):
    """A place of a door and a window laid 30 cm into it, both 1 m boxes on the floor, as the stage's output, its
    inventory of the two rows in the world's declared folder; the output and that folder's world data."""
    (root / "made").mkdir(parents=True)
    rows = [row("door"), row("window")]
    stage = place_of(root / "made", [("door", "box", (6, 0, 0)), ("window", "box", (6.3, 0, 0))], rows)
    output = root / "output"
    shutil.copytree(stage.parent, output)
    inputs_record = json.loads((output / "inputs.json").read_text())
    (output / "inputs.json").write_text(json.dumps(
        {**inputs_record, "inventory": str(root / f"home/design/inventory/{stage.stem}.json")}))
    inputs = world_data(root / "world", stage.stem, [])
    (inputs["inventories"] / f"{stage.stem}.json").write_text(json.dumps({"rows": rows}))
    return output, inputs


def a_sunk_plate(root):
    """A place holding one floor plate sunk 40 cm (a kit piece's false alarm under the repository's rules), as the
    stage's output, its inputs record naming the design inventory by full path as earth-seed lays it."""
    (root / "made").mkdir()
    stage = place_of(root / "made", [("plate", "box", (6, -0.4, 0))], [row("plate", group="kit: floor")])
    output = root / "output"
    shutil.copytree(stage.parent, output)
    inputs_record = json.loads((output / "inputs.json").read_text())
    (output / "inputs.json").write_text(json.dumps(
        {**inputs_record, "inventory": str(root / f"home/design/inventory/{stage.stem}.json")}))
    return output, stage.stem


def world_data(root, place, fixed_in_kit):
    """The world's data the stage declares: rules (the kit groups as given), kit and inventory."""
    data = root / "data"
    for part in ("checks", "kit", "inventory"):
        (data / part).mkdir(parents=True)
    rules = json.loads((REPO / "data/checks/resting.json").read_text())
    (data / "checks/resting.json").write_text(json.dumps({**rules, "fixed_in_kit": fixed_in_kit}))
    (data / "kit" / f"{place}.json").write_text(json.dumps({"kinds": {}}))
    (data / "inventory" / f"{place}.json").write_text(json.dumps({"rows": [row("plate", group="kit: floor")]}))
    return {"resting rules": data / "checks/resting.json", "kit": data / "kit" / f"{place}.json",
            "inventories": data / "inventory"}


def resting(output, inputs):
    evidence = output.parent / "settled.json"
    evidence.write_text(json.dumps({"objects": {}}))
    return resting_within.judge_resting(output, inputs, evidence)


def test_the_resting_gate_judges_the_world_files_the_stage_declares(tmp_path):
    """Fault (review of step 0, 2026-10-11): the judge read the repository's resting.json, so a world whose rules were
    elsewhere was judged on files its key did not cover. The sunk plate passes where the world's rules name its kit
    group, fails by name where they name none, and a seed naming no inventory in the folder is unknown.
    Break: score/stages/assembly/resting_within.py: `rules_file=inputs["resting rules"]` -> `rules_file=assembly.REPO /
        "data/checks/resting.json"`
    Round 32's docking airlock (2026-11-11): its door's window and its suit in its locker, laid within their holders by
    the plan, failed as overlaps "still inside after the nudge". A window the record lays within its door passes; the
    same pair with no planned relation, or laid on it, still fails as overlapping; the table's assembly row judges
    resting so.
    Break: score/stages/__init__.py: `"resting": resting_within.judge_resting` -> `"resting": assembly.judge_resting`
    Break: score/stages/assembly/resting_within.py: `and not planned_overlap(fault, within)]` -> `]`
    Break: score/stages/assembly/resting_within.py: laid_within's `== "within"}` -> `in ("within", "top")}`"""
    output, place = a_sunk_plate(tmp_path)
    kit_floor = world_data(tmp_path / "kept", place, ["kit: floor"])
    pair, pair_world = a_window_in_its_door(tmp_path / "pair")
    (pair / record.RECORD).write_text(json.dumps({"objects": [{"name": "door_1", "row": "door"}]}))
    alone = resting(pair, pair_world)
    assert alone.answer == checks.FAIL and any("overlaps" in finding for finding in alone.findings), alone
    for how, answer in (("within", checks.PASS), ("top", checks.FAIL)):
        laid = {"name": "window_1", "row": "window", "on": {"how": how, "holder": ["door_1"]}}
        (pair / record.RECORD).write_text(json.dumps({"objects": [{"name": "door_1", "row": "door"}, laid]}))
        assert resting(pair, pair_world).answer == answer, (how, resting(pair, pair_world))
    from score import stages
    judges = {check.name: inspect.unwrap(check.judge) for check in stages.ASSEMBLY.checks}
    assert judges["resting"] is resting_within.judge_resting, judges
    assert resting(output, kit_floor).answer == checks.PASS
    verdict = resting(output, world_data(tmp_path / "changed", place, []))
    assert verdict.answer == checks.FAIL and "plate" in " ".join(verdict.findings), verdict
    inputs_record = json.loads((output / "inputs.json").read_text())
    (output / "inputs.json").chmod(0o644)
    (output / "inputs.json").write_text(json.dumps({**inputs_record, "inventory": "/elsewhere/rows.json"}))
    assert resting(output, kit_floor).answer == checks.UNKNOWN


def test_a_row_on_a_wall_or_ceiling_row_is_judged_mounted_there():
    """Round 32's docking airlock (2026-10-30): its wall pipes on its left wall and ceiling rails on its ceiling panels
    were judged as standing on them, leaning and tipping. The triage is given each such row's support as its holder's
    kind (assembly/mounted.py), so it judges them by touching; a row on a floor or an object, or naming its own
    support, keeps what the triage gives it. Tube's wall lamps on its ribs (a structure row built into its wall) were
    judged standing on the ribs' curve (settle@tube, 2026-11-12): a wall thing on a built-in row is mounted with it; a
    cup on it still stands.
    Break: score/stages/assembly/__init__.py: `if row["id"] in on_walls and not row.get("support")` -> `if False`
    Break: score/stages/assembly/mounted.py: `return {**found, **on_built_in(rows, holders, found, built_in)}` ->
        `return found`, or structure_mounted.py's `and holder_kind(rows[row_id]) in ("wall", "ceiling")` -> `` (the
        cup mounted)"""
    inventory = {"rows": [{"id": "left_wall", "part": "wall"}, {"id": "ceiling_panels", "part": "roof"},
                          {"id": "floor_plates", "part": "floor"}, {"id": "locker", "part": "object"},
                          {"id": "wall_pipes", "anchor": "on:left_wall"},
                          {"id": "ceiling_rails", "anchor": "on:ceiling_panels"},
                          {"id": "fixed_pipe", "anchor": "on:left_wall", "support": "fixed"},
                          {"id": "crate", "anchor": "on:floor_plates"}, {"id": "suit", "anchor": "on:locker"},
                          {"id": "ribs", "part": "structure", "anchor": "on:left_wall"},
                          {"id": "wall_lamps", "anchor": "on:ribs"}, {"id": "cup", "anchor": "on:ribs"}]}
    found = {row["id"]: row.get("support") for row in assembly.resting_rows(inventory)["rows"]}
    assert found == {"left_wall": None, "ceiling_panels": None, "floor_plates": None, "locker": None,
                     "wall_pipes": "wall", "ceiling_rails": "ceiling", "fixed_pipe": "fixed", "crate": None,
                     "suit": None, "ribs": "wall", "wall_lamps": "wall", "cup": None}, found


def test_a_row_the_record_hangs_within_its_holder_is_judged_hanging():
    """Round 32's docking airlock: its spacesuits, laid within their lockers at the plan's 0.1 m base, were judged as
    standing on the lockers' insides and leaned 12 degrees. A row whose every object the scene record lays within its
    holder hanging (its relation's `hangs`, fitting.hangs_in) is given `hanging` (judged by touching: one touching
    nothing still hangs free); one within not hanging, one filling its holder (a door's window), one of a row with
    another object laid otherwise, or a row naming its own support, keeps what the triage gives it.
    settle@street (2026-11-11): its red paper lanterns, laid on the side of their lantern string 24 m up, were judged
    floating 23.8 m over the street. A row whose every object the record lays on its holder's side (`face`) is
    `hanging` too; the box, one within and one on a face, is not.
    Break: score/stages/assembly/fitting.py: `and bool(on.get("hangs"))` -> `` (every one within hung)
    Break: score/stages/assembly/__init__.py: `if all(hung)}` -> `if any(hung)}`
    Break: score/stages/assembly/mounted.py: on_faces' `if all(faced)}` -> `if any(faced)}`, or resting_rows'
        `**on_faces(record or {}), ` dropped"""
    inventory = {"rows": [{"id": "locker", "part": "object"}, {"id": "suit", "anchor": "on:locker"},
                          {"id": "crate", "anchor": "on:locker"}, {"id": "box", "anchor": "on:locker"},
                          {"id": "lantern", "anchor": "on:locker"}, {"id": "window", "anchor": "on:locker"},
                          {"id": "fixed_suit", "anchor": "on:locker", "support": "fixed"}]}

    def laid(name, row, how=None, hung=False, **more):
        on = {"how": how, "holder": ["locker_1"], **({"hangs": True} if hung else {})}
        return {"name": name, "row": row, "at": [0.0, 0.1, 0.0], **({"on": on} if how else {}), **more}
    record = {"objects": [laid("locker_1", "locker"), laid("suit_1", "suit", "within", True),
                          laid("suit_2", "suit", "within", True), laid("crate_1", "crate", "within"),
                          laid("box_1", "box", "within", True), laid("box_2", "box", "face"),
                          laid("window_1", "window", "within", True, fills=True),
                          laid("fixed_suit_1", "fixed_suit", "within", True), laid("lantern_1", "lantern", "face"),
                          laid("lantern_2", "lantern", "face")]}
    found = {row["id"]: row.get("support") for row in assembly.resting_rows(inventory, record)["rows"]}
    assert found == {"locker": None, "suit": "hanging", "crate": None, "box": None, "lantern": "hanging",
                     "window": None, "fixed_suit": "fixed"}, found


def test_a_hanging_one_is_hung_on_its_holder_s_inside_back_face():
    """Round 32's docking airlock: spacesuit_left_1, laid within its locker at the plan's base, hung 4.1 cm off the
    locker's back and touched nothing (hangs free). A hanging one moves along its holder's back way until its built
    surface meets the holder's inside back face, its height and its place across kept (hung_back): the back is
    opposite the side the holder's surface leaves open across it (an open-fronted locker, +x), else opposite the side
    toward the room's middle (a closed one).
    Break: score/stages/assembly/fitting.py: back_way's `return axis, -sign` -> `return axis, sign`
    Break: score/stages/assembly/fitting.py: back_way's `if not np.any(across & (sign * (points[:, axis] -
        middle[axis]) > 0)):` -> `if False:` (an open front read as closed, the room's middle behind the back)"""
    steps = np.linspace(0.0, 2.0, 41)
    across = np.linspace(0.0, 0.8, 17)
    back = np.array([[0.0, up, side] for up in steps for side in across])
    sides = np.array([[deep, up, side] for deep in np.linspace(0.0, 1.0, 21) for up in steps for side in (0.0, 0.8)])
    front = np.array([[1.0, up, side] for up in steps for side in across])
    suit = np.array([[deep, up, side] for deep in (0.2, 0.6) for up in np.linspace(0.1, 1.9, 37)
                     for side in np.linspace(0.2, 0.6, 9)])
    low, high = suit.min(axis=0), suit.max(axis=0)
    opened = fitting.hung_back(suit, np.concatenate([back, sides]), low, high, room_middle=[-5.0, 0.4])
    assert opened[:2] == (0, -1.0) and abs(opened[2] - 0.2) < 1e-9, opened
    closed = np.concatenate([back, sides, front])
    assert fitting.hung_back(suit, closed, low, high, room_middle=[5.0, 0.4])[:2] == (0, -1.0)
    toward_back = fitting.hung_back(suit, closed, low, high, room_middle=[-5.0, 0.4])
    assert toward_back[:2] == (0, 1.0) and abs(toward_back[2] - 0.4) < 1e-9, toward_back


def test_the_declared_inventory_folder_is_the_one_earth_seed_lays_from(tmp_path):
    """Fault (Buy of 2026-10-24): the assembly declared {data}/inventory while every designed seed is laid from
    {home}/design/inventory and records that full path, so no resting gate was judged and every drop run raised after
    its clearance. The seed's recorded file is found by name in the declared folder; a seed naming none has none.
    Break: score/stages/assembly/__init__.py: `"inventories": "{home}/design/inventory"` -> `"inventories":
        "{data}/inventory"`
    Break: score/stages/assembly/__init__.py: `return pathlib.Path(inventories) / pathlib.Path(named).name if named else
        None` -> `return pathlib.Path(named) if named else None`"""
    from score.stages import earth_seed
    laid_from = pathlib.Path(earth_seed.design_files("hub")["design inventory"])
    assert str(laid_from.parent) == assembly.FILES["inventories"], (laid_from, assembly.FILES["inventories"])
    (tmp_path / "inputs.json").write_text(json.dumps({"inventory": str(tmp_path / "home/design/inventory/hub.json")}))
    assert assembly.declared_inventory(tmp_path, tmp_path / "world") == tmp_path / "world/hub.json"
    (tmp_path / "inputs.json").write_text(json.dumps({}))
    assert assembly.declared_inventory(tmp_path, tmp_path / "world") is None


# --- the bakes ------------------------------------------------------------------------------------------------------

def test_a_baked_model_carries_its_hash_and_keeps_the_owner_s_pick(tmp_path):
    """After the assembly takes a bake, the object carries the baked file's hash (sha256 of its .gltf and its buffer's
    hex digest, worked out here) and the seed's as `repaint_of`, so the owner's pick of the seed's model still holds;
    the same hash without the seed's beside it breaks the pick (the greenhouse's water tank, 2026-10-12).
    Break: score/stages/assembly/baked.py: `before.get("score:repaint_of") or before.get("score:model_sha256")` ->
        `None`"""
    import picks
    from pxr import Sdf
    (tmp_path / "models").mkdir()
    box_gltf(tmp_path / "models")
    box_gltf(tmp_path / "models", "plank")  # stands for the bake of the box: another file, another hash

    def sha(gltf):
        digest = hashlib.sha256(gltf.read_bytes())
        digest.update(hashlib.sha256(gltf.with_suffix(".bin").read_bytes()).hexdigest().encode())
        return digest.hexdigest()
    seed_hash = sha(tmp_path / "models/box.gltf")
    pick = {"model": "box", "sha256": seed_hash, "decided": "owner, 2026-10-09: this take"}
    stage = place_of(tmp_path, [("crate", "box", (0, 0, 0))], [row("crate", pick=pick)])
    inventory = json.loads((tmp_path / "inventory.json").read_text())
    assembly.stamp_baked_hash(stage.parent / assembly.BASE_LAYER, "box", tmp_path / "models/plank.gltf")
    held = opened(stage)
    prim = held.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
    assert prim.GetAttribute("score:model_sha256").Get() == sha(tmp_path / "models/plank.gltf")
    assert prim.GetAttribute("score:repaint_of").Get() == seed_hash
    assert picks.check(stage, inventory) == ([], 1)
    layer = Sdf.Layer.FindOrOpen(str(stage.parent / assembly.BASE_LAYER))
    spec = layer.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
    spec.RemoveProperty(spec.attributes["score:repaint_of"])
    layer.Save()
    found, _ = picks.check(stage, inventory)
    assert len(found) == 1 and "not the owner's pick" in found[0]["why"], found


def test_a_fixture_laid_from_a_released_file_takes_the_bake_of_its_model(tmp_path):
    """Fault (complete@launch, 2026-10-15): the rocket, laid from the released models/rockets/rocket.gltf, kept the
    seed's paint, the bake matched only by name. It now references the baked asset, named by its model; a bake that
    moved the frame (a 3 m cube for a 2 m one) is refused.
    Break: score/stages/assembly/baked.py: `abs(old_box[end][axis] - new_box[end][axis]) > BOX_TOLERANCE` -> `False`"""
    from pxr import Sdf, Usd, UsdGeom
    out = tmp_path
    (out / "assets").mkdir()
    (out / "layers").mkdir()
    a_cube_asset(out / "assets/fixture_rocket.usdc", 2.0)
    a_cube_asset(out / "assets/rocket.usdc", 2.0)
    base = Usd.Stage.CreateNew(str(out / "layers/base.usda"))
    prim = UsdGeom.Xform.Define(base, "/toy/Fixtures/rocket").GetPrim()
    prim.GetReferences().AddReference("../assets/fixture_rocket.usdc")
    prim.CreateAttribute("score:model", Sdf.ValueTypeNames.String).Set("models/rockets/rocket.gltf")
    base.GetRootLayer().Save()
    assembly.lay_fixtures_baked(out / assembly.BASE_LAYER, "rocket")
    spec = Sdf.Layer.FindOrOpen(str(out / assembly.BASE_LAYER)).GetPrimAtPath("/toy/Fixtures/rocket")
    assert [ref.assetPath for ref in spec.referenceList.prependedItems] == ["../assets/rocket.usdc"]
    assert spec.attributes["score:model"].default == "rocket"
    spec.referenceList.prependedItems = [Sdf.Reference("../assets/fixture_rocket.usdc")]
    spec.attributes["score:model"].default = "models/rockets/rocket.gltf"
    spec.layer.Save()
    a_cube_asset(out / "assets/rocket.usdc", 3.0)
    with pytest.raises(ValueError, match="moved the model's frame"):
        assembly.lay_fixtures_baked(out / assembly.BASE_LAYER, "rocket")


def test_a_claimed_model_is_laid_from_the_name_its_place_bakes_it_under(tmp_path):
    """The hangar (2026-10-15) lays parts_rack_1, which old_station bakes as parts_rack: the claim's baked name comes
    from the hangar's own bake (elsewhere.json, baked_as), and the model is read under the hangar's name (its three
    points intact); a model baked under its own name is read where it is.
    Break: score/stages/assembly/baked.py: `else claims[model]["baked_as"]` -> `else model`
    Break: score/stages/assembly/baked.py: `if baked_as == model:` -> `if True:`"""
    import export
    folder = tmp_path
    (folder / "surfaces.json").write_text(json.dumps(
        {"elsewhere": {"parts_rack_1": {"take": "parts_rack-r1", "place": "old_station"}}}))
    (folder / "bake").mkdir()
    (folder / "bake/elsewhere.json").write_text(json.dumps({"parts_rack_1": {
        "take": "parts_rack-r1", "place": "old_station", "node": "surfaces-bake@old_station",
        "baked_as": "parts_rack"}}))
    (folder / "old").mkdir()
    (folder / "old/baked.json").write_text(json.dumps({"parts_rack": {"parts": "parts_rack-r1"}}))
    inputs = {"surfaces": folder / "surfaces.json", "surfaces-bake": folder / "bake",
              "surfaces-bake@old_station": folder / "old", "surfaces-paint@old_station": folder / "paint"}
    [(bake, _, _, models)] = assembly.claimed_bakes(inputs, folder / "out")
    assert bake == folder / "old" and models == {"parts_rack_1": "parts_rack"}, models
    a_baked_triangle(folder / "old/made", "parts_rack")
    found = assembly.renamed_model(folder / "old/made", "parts_rack", "parts_rack_1", folder / "out/renamed")
    geometry = export.model_geometry(export.model_file(found, "parts_rack_1"))
    assert len(geometry["positions"]) == 3, geometry
    assert assembly.renamed_model(folder / "old/made", "parts_rack", "parts_rack", folder / "x") == folder / "old/made"


def test_a_claimed_model_its_place_bakes_under_its_own_name_is_laid_from_its_own_bake(tmp_path):
    """assembly@hub (2026-10-15): workshop bakes wrench_1 and wrench_2 from one take (wrench-r6), each its own size,
    and the hub's elsewhere.json names wrench_1 as every wrench's baked_as; wrench_2 stood as wrench_1's bake. A model
    the claimed place bakes under its own name with the claimed take is read under it; wrench_9, which it does not
    bake, falls back to baked_as.
    Break: score/stages/assembly/baked.py: `baked.get(model, {}).get("parts") == claim["take"]` -> `False`"""
    folder = tmp_path
    elsewhere = {name: {"take": "wrench-r6", "place": "workshop"} for name in ("wrench_1", "wrench_2", "wrench_9")}
    (folder / "surfaces.json").write_text(json.dumps({"elsewhere": elsewhere}))
    (folder / "bake").mkdir()
    (folder / "bake/elsewhere.json").write_text(json.dumps(
        {name: dict(claim, baked_as="wrench_1") for name, claim in elsewhere.items()}))
    (folder / "workshop").mkdir()
    (folder / "workshop/baked.json").write_text(json.dumps(
        {"wrench_1": {"parts": "wrench-r6"}, "wrench_2": {"parts": "wrench-r6"}}))
    inputs = {"surfaces": folder / "surfaces.json", "surfaces-bake": folder / "bake",
              "surfaces-bake@workshop": folder / "workshop", "surfaces-paint@workshop": folder / "paint"}
    [(_, _, _, models)] = assembly.claimed_bakes(inputs, folder / "out")
    assert models == {"wrench_1": "wrench_1", "wrench_2": "wrench_2", "wrench_9": "wrench_1"}, models


def test_the_places_claiming_a_bake_are_read_from_the_design_s_surface_data(tmp_path, monkeypatch):
    """claiming_places reads the scene's design surface data (`elsewhere`): the yard lays models the barn and the shed
    bake; a place with no surface data claims none.
    Break: score/stages/assembly/baked.py: `return sorted({claim["place"] for claim in elsewhere.values()})` -> `return
        sorted({claim["take"] for claim in elsewhere.values()})`"""
    monkeypatch.setattr(baked, "DESIGN_SURFACES", tmp_path)
    (tmp_path / "yard.json").write_text(json.dumps({"elsewhere": {"rack_1": {"place": "shed", "take": "rack"},
                                                                  "lamp_1": {"place": "barn", "take": "lamp"}}}))
    assert baked.claiming_places("yard") == ["barn", "shed"]
    assert baked.claiming_places("nook") == []


# --- layers, record and sound ---------------------------------------------------------------------------------------

def test_a_layer_is_held_in_its_place_and_the_root_plays_as_long_as_it(tmp_path):
    """A layer stage's layer goes between the others in record.ORDER (light over motion over effects), replacing the
    seed's of the same name, and the root's range grows to the layer's 480 frames; the light stage's live lamps (a
    layer and no assets, 2026-10-13) leave no stale assets/light behind.
    Break: score/stages/assembly/record.py: `return ORDER.index(stem) if stem in ORDER else ORDER.index("base") - 0.5`
        -> `return 0`
    Break: score/stages/assembly/__init__.py: `stage_root.endTimeCode = max(taken.endTimeCode, stage_root.endTimeCode if
        stage_root.HasEndTimeCode() else 0)` -> `pass`
    Break: score/stages/assembly/__init__.py: `shutil.rmtree(root.parent / assets, ignore_errors=True)` -> `pass`"""
    from pxr import Sdf
    root = a_toy(tmp_path / "out")
    made = tmp_path / "motion"
    (made / "layers").mkdir(parents=True)
    layer = Sdf.Layer.CreateNew(str(made / "layers/motion.usda"))
    layer.timeCodesPerSecond, layer.startTimeCode, layer.endTimeCode = 24.0, 0.0, 480.0
    layer.Save()
    assembly.take_layer(made, root, "layers/motion.usda", None)
    (made / "layers/light.usda").write_text("#usda 1.0\n")
    (made / "assets/light").mkdir(parents=True)
    (made / "assets/light/earth.png").write_bytes(b"png")
    assembly.take_layer(made, root, "layers/light.usda", "assets/light")
    found = Sdf.Layer.FindOrOpen(str(root))
    found.Reload()
    assert list(found.subLayerPaths) == [f"./layers/{name}.usda" for name in
                                         ("edit", "characters", "sound", "light", "motion", "effects", "base")]
    assert found.endTimeCode == 480.0 and (root.parent / "assets/light/earth.png").exists()
    live = tmp_path / "live"
    (live / "layers").mkdir(parents=True)
    (live / "layers/light.usda").write_text("#usda 1.0\n")
    assembly.take_layer(live, root, "layers/light.usda", "assets/light")
    assert not (root.parent / "assets/light").exists()


def test_a_light_the_motion_layer_animates_plays_its_keyframes(tmp_path):
    """A lamp whose strength the motion layer keys (0 then 50 at frame 12) and the light layer sets (20) plays the
    motion's keys on the assembled stage (the airlock's cycle light, 2026-10-16); a lamp the motion leaves alone keeps
    20. Both taken layers come in read-only and neither file changes (the store's files are never edited).
    Break: score/stages/assembly/__init__.py: `held.insert(held.index(f"./{LAYERS['light'][1]}"), f"./{MOTION_KEYS}")`
        -> `held.append(f"./{MOTION_KEYS}")`"""
    from pxr import Usd, UsdLux
    root = a_toy(tmp_path / "out")
    sums = {}
    for name, keyed in (("light", False), ("motion", True)):
        made = tmp_path / name
        (made / "layers").mkdir(parents=True)
        stage = Usd.Stage.CreateNew(str(made / f"layers/{name}.usda"))
        for lamp in ("cycle", "steady"):
            if keyed and lamp == "steady":
                continue
            strength = UsdLux.SphereLight.Define(stage, f"/{TOY}/Lights/{lamp}").CreateIntensityAttr()
            if keyed:
                strength.Set(0.0, 0)
                strength.Set(50.0, 12)
            else:
                strength.Set(20.0)
        stage.GetRootLayer().Save()
        (made / f"layers/{name}.usda").chmod(0o444)
        assembly.take_layer(made, root, f"layers/{name}.usda", None)
        sums[name] = hashlib.sha256((made / f"layers/{name}.usda").read_bytes()).hexdigest()
    assert opened(root).GetPrimAtPath(f"/{TOY}/Lights/cycle").GetAttribute(
        "inputs:intensity").GetNumTimeSamples() == 0  # the plain light value hides the keys before
    assembly.motion_over_light(root)
    stage = opened(root)
    cycle = stage.GetPrimAtPath(f"/{TOY}/Lights/cycle").GetAttribute("inputs:intensity")
    assert cycle.GetNumTimeSamples() == 2 and cycle.Get(12) == 50.0, cycle.Get(12)
    assert stage.GetPrimAtPath(f"/{TOY}/Lights/steady").GetAttribute("inputs:intensity").Get() == 20.0
    for name, digest in sums.items():
        for folder in (tmp_path / name, root.parent):
            assert hashlib.sha256((folder / f"layers/{name}.usda").read_bytes()).hexdigest() == digest, (name, folder)


def test_the_accepted_record_replaces_the_seed_s_and_a_place_without_one_keeps_its_seed_record(tmp_path):
    """The accepted scene record's prims stand in the base in place of the old record's (the wall and the lamp gone,
    the objects kept, its one lamp laid); a place with no record row keeps the seed's and says it is unverified.
    Break: score/stages/assembly/record.py: `edit.Add(f"/{place}/{name}", Sdf.Path.emptyPath)` -> `pass`"""
    root = a_toy(tmp_path / "out")
    inputs = a_record(tmp_path, ONE_LAMP)
    said = assembly.take_record(inputs, root.parent, TOY)
    stage = opened(root)
    assert said == f"scene-record@{TOY}"
    assert not stage.GetPrimAtPath(f"/{TOY}/Structure/old_wall") and not stage.GetPrimAtPath(f"/{TOY}/Lights/old_lamp")
    assert stage.GetPrimAtPath(f"/{TOY}/Lights/light_1") and stage.GetPrimAtPath(f"/{TOY}/Objects/fan_1")
    other = a_toy(tmp_path / "other")
    said = assembly.take_record({"scene": tmp_path / f"record/record/{TOY}.json", "kit": inputs["kit"]},
                                other.parent, TOY)
    kept = opened(other)
    assert "unverified" in said and kept.GetPrimAtPath(f"/{TOY}/Structure/old_wall")


def test_the_collision_gate_fails_a_seed_s_bare_wall_and_passes_the_record_written_again(tmp_path):
    """A seed's floor drawn with no collision (as round three wrote every wall, floor and stair) fails the collision
    gate by name, one uncolliding; the accepted record written over it (a wall and a flight of stairs) collides.
    Break: score/stages/assembly/__init__.py: `solid = sum(fault["what"] != "model" for fault in faults)` -> `solid =
        0`"""
    from pxr import Sdf, Usd, UsdGeom, UsdShade
    root = a_toy(tmp_path / "out")
    base = Usd.Stage.Open(str(root.parent / "layers/base.usda"))
    UsdShade.Material.Define(base, f"/{TOY}/Library/concrete")
    bare = UsdGeom.Mesh.Define(base, f"/{TOY}/Structure/seed_floor")
    bare.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("structure")
    base.GetRootLayer().Save()
    before = assembly.judge_collision(root.parent, {}, None)
    assert before.answer == checks.FAIL and before.measures == {"uncolliding": 1, "models without collider": 0}
    assert before.findings[0].startswith(f"/{TOY}/Structure/seed_floor: "), before.findings
    walls = {"structure": [
        {"name": "wall", "builder": "box", "centre": [0, 1.5, -4], "size": [8, 3, 0.2], "surface": "concrete"},
        {"name": "steps", "builder": "stairs", "foot": [2, 0, 0], "top": [2, 1.2, -1.8], "wide": 1.0, "steps": 6,
         "surface": "concrete"}]}
    assembly.take_record(a_record(tmp_path, walls), root.parent, TOY)
    after = assembly.judge_collision(root.parent, {}, None)
    assert after.answer == checks.PASS and after.measures == {"uncolliding": 0, "models without collider": 0}, \
        after.findings
    stage = opened(root)
    assert all(stage.GetPrimAtPath(f"/{TOY}/Structure/{name}") for name in ("wall", "steps"))


def test_a_tube_s_lamps_hang_on_every_bay_of_its_way():
    """A walkway tube 6 m long with 2 m bays lays its bay piece three times, each with its spot, as the exporter lays
    them; a room's pieces stand as laid.
    Break: score/stages/assembly/record.py: `if "bay" not in kit or not record.get("tube_length"):` -> `if True:`"""
    kit = {"bay": 2.0, "pieces": [{"kind": "tube_bay", "tube_part": "bay"}]}
    laid = assembly.laid_pieces(kit, {"tube_length": 6.0})
    assert len(laid) == 3 and all("spot" in piece for piece in laid), laid
    assert assembly.laid_pieces({"pieces": kit["pieces"]}, {}) == kit["pieces"]


def test_an_entry_waiting_on_its_model_lays_nothing_and_is_named(tmp_path):
    """Fault (2026-10-12): the campgrounds' record names its cairn, whose model is not released yet, and the assembly
    errored on it. An entry marked `waiting` lays nothing; the root prim names it for the completion gate.
    Break: score/stages/assembly/record.py: `laid, waiting = without_waiting(record)` -> `laid, waiting = record, []`"""
    root = a_toy(tmp_path / "out")
    cairn = {"objects": [{"name": "cairn", "model": "models/none/none.glb", "at": [0, 0, 0],
                          "waiting": "its model comes through the next batch"}]}
    assembly.take_record(a_record(tmp_path, cairn), root.parent, TOY)
    stage = opened(root)
    assert not stage.GetPrimAtPath(f"/{TOY}/Fixtures/cairn")
    assert list(stage.GetPrimAtPath(f"/{TOY}").GetAttribute(assembly.WAITING).Get()) == [
        "objects cairn: its model comes through the next batch"]


def test_a_waiting_entry_whose_row_the_bake_made_is_laid_on_its_spot_and_no_longer_named(tmp_path):
    """The camp grounds' cairn (2026-10-13): once the surface line has baked its row, the assembly lays that model
    where the entry stands. The baked cairn spans 2 x 2 x 0.5 m; turned 90 degrees about y it spans 0.5 x 2 x 2, its
    foot at the spot's 0.5, its middle over (3, -2).
    Break: score/stages/assembly/made_waiting.py: `move = Gf.Vec3d(at[0] - (least[0] + most[0]) / 2, at[1] - least[1],
        at[2] - (least[2] + most[2]) / 2)` -> `move = Gf.Vec3d(*at)`
    Break: score/stages/assembly/made_waiting.py: `root.RemoveProperty(WAITING)` -> `pass`"""
    from pxr import Gf, UsdGeom
    root = a_toy(tmp_path / "out")
    cairn = {"objects": [{"name": "cairn", "model": "models/none/none.glb", "row": "cairn", "at": [3.0, 0.5, -2.0],
                          "rotation": [0.0, 0.7071068, 0.0, 0.7071068], "waiting": "no released model"}]}
    assembly.take_record(a_record(tmp_path, cairn), root.parent, TOY)
    an_asset(root.parent / "assets/cairn.usdc",
             [(-1.0, -1.0, -0.25), (1.0, -1.0, -0.25), (1.0, 1.0, 0.25), (-1.0, 1.0, 0.25)], [4], [0, 1, 2, 3])
    (tmp_path / "bake").mkdir()
    (tmp_path / "bake/baked.json").write_text(json.dumps({"cairn": {}}))
    assert made_waiting.lay(root.parent, TOY, tmp_path / "bake") == ["cairn"]
    stage = opened(root)
    prim = stage.GetPrimAtPath(f"/{TOY}/Fixtures/cairn")
    box = UsdGeom.BBoxCache(0, [UsdGeom.Tokens.default_]).ComputeWorldBound(prim).ComputeAlignedRange()
    middle = (box.GetMin() + box.GetMax()) / 2
    assert Gf.IsClose(box.GetMin()[1], 0.5, 1e-5) and Gf.IsClose(middle[0], 3.0, 1e-5), box
    assert Gf.IsClose(middle[2], -2.0, 1e-5) and Gf.IsClose(box.GetSize()[2], 2.0, 1e-4), box
    assert prim.GetAttribute("score:row").Get() == "cairn"
    assert not stage.GetPrimAtPath(f"/{TOY}").HasAttribute(assembly.WAITING)


def test_a_design_object_is_laid_under_objects_with_its_take_model_and_its_own_row(tmp_path):
    """Fault (2026-10-25): a designed place's record laid no object, so settle, physics and motion found none. A
    design's object (`bake` its take's model, `row` its inventory row) is laid with the baked model at
    /<place>/Objects/<name>, its score:row the inventory row; one whose model the bake has not made stays named.
    Break: score/stages/assembly/made_waiting.py: `scope = f"/{place}/Objects" if "bake" in entry else
        f"/{place}/Fixtures"` -> `scope = f"/{place}/Fixtures"`"""
    root = a_toy(tmp_path / "out")
    entries = [{"name": name, "row": row_id, "bake": bake, "at": [1.0, 0.0, 1.0], "rotation": [0.0, 0.0, 0.0, 1.0],
                "kind": "object", "waiting": "its model comes from the bake"}
               for name, row_id, bake in (("lamp_1", "lamp", "bench_1"), ("rail_1", "rail", "rail_1"))]
    assembly.take_record(a_record(tmp_path, {"objects": entries}), root.parent, TOY)
    an_asset(root.parent / "assets/bench_1.usdc", [(-1.0, 0.0, -0.25), (1.0, 0.0, -0.25), (1.0, 1.0, 0.25)], [3],
             [0, 1, 2])
    (tmp_path / "bake").mkdir()
    (tmp_path / "bake/baked.json").write_text(json.dumps({"bench_1": {}}))
    assert made_waiting.lay(root.parent, TOY, tmp_path / "bake") == ["bench_1"]
    stage = opened(root)
    prim = stage.GetPrimAtPath(f"/{TOY}/Objects/lamp_1")
    assert prim.GetChild("geo").IsValid() and prim.GetAttribute("score:row").Get() == "lamp", prim
    assert prim.GetAttribute("score:model").Get() == "bench_1" and not stage.GetPrimAtPath(f"/{TOY}/Fixtures")
    assert list(stage.GetPrimAtPath(f"/{TOY}").GetAttribute(assembly.WAITING).Get()) == [
        "objects rail_1: its model comes from the bake"]


def test_a_row_ground_join_joined_is_the_ground_s_and_is_not_laid_again_as_an_object(tmp_path):
    """Fault (2026-10-30): camp's rocks stood twice at one spot, an object at /camp/Objects/rock_1_1 and a piece of
    the ground ground-join cut and seated at /camp/Outside/Detail/rock_1. A record entry whose row ground-join joined
    (its join.json pieces) is laid by the ground alone: no object, and no longer named waiting.
    Break: score/stages/assembly/made_waiting.py: `if entry.get("waiting") and entry.get("row") in joined:` ->
        `if False:`
    Break: score/stages/assembly/made_waiting.py: `return frozenset(json.loads(...)["pieces"])` -> `return frozenset()`"""
    root = a_toy(tmp_path / "out")
    entries = [{"name": f"{row_id}_1", "row": row_id, "bake": f"{row_id}_1", "at": [1.0, 0.0, 1.0],
                "rotation": [0.0, 0.0, 0.0, 1.0], "kind": "object", "waiting": "its model comes from the bake"}
               for row_id in ("rock", "bench")]
    assembly.take_record(a_record(tmp_path, {"objects": entries}), root.parent, TOY)
    for model in ("rock_1", "bench_1"):
        a_box_asset(root.parent / f"assets/{model}.usdc", (-1.0, 0.0, -1.0), (1.0, 1.0, 1.0))
    (tmp_path / "bake").mkdir()
    (tmp_path / "bake/baked.json").write_text(json.dumps({"rock_1": {}, "bench_1": {}}))
    (tmp_path / "join").mkdir()
    (tmp_path / "join/join.json").write_text(json.dumps({"place": TOY, "pieces": {"rock": {}}, "code ground": {}}))
    joined = made_waiting.joined_rows({"ground-join": tmp_path / "join"})
    assert joined == {"rock"} and made_waiting.joined_rows({}) == frozenset()
    assert made_waiting.lay(root.parent, TOY, tmp_path / "bake", joined) == ["bench_1"]
    stage = opened(root)
    assert not stage.GetPrimAtPath(f"/{TOY}/Objects/rock_1") and stage.GetPrimAtPath(f"/{TOY}/Objects/bench_1")
    assert not stage.GetPrimAtPath(f"/{TOY}").HasAttribute(assembly.WAITING)


def test_the_settle_s_seed_leaves_out_a_row_ground_join_joined(tmp_path, monkeypatch):
    """The settle drops the place as the assembly lays it (grounded.take_bakes): a row ground-join joined is no object
    there either, so no drop moves it and no settle over names a prim the assembly no longer lays (camp's rocks, loose
    on the ground, 2026-10-30). The bakes' own export is stubbed: only what is laid is read.
    Break: score/stages/assembly/grounded.py: `made_waiting.lay(folder, place, bake, made_waiting.joined_rows(inputs))`
        -> `made_waiting.lay(folder, place, bake)`"""
    from score.stages.assembly import grounded
    root = a_toy(tmp_path / "out")
    entry = {"name": "rock_1", "row": "rock", "bake": "rock_1", "at": [1.0, 0.0, 1.0],
             "rotation": [0.0, 0.0, 0.0, 1.0], "kind": "object", "waiting": "its model comes from the bake"}
    assembly.take_record(a_record(tmp_path, {"objects": [entry]}), root.parent, TOY)
    a_box_asset(root.parent / "assets/rock_1.usdc", (-1.0, 0.0, -1.0), (1.0, 1.0, 1.0))
    (tmp_path / "bake").mkdir()
    (tmp_path / "bake/baked.json").write_text(json.dumps({"rock_1": {}}))
    (tmp_path / "join").mkdir()
    (tmp_path / "join/join.json").write_text(json.dumps({"place": TOY, "pieces": {"rock": {}}, "code ground": {}}))
    monkeypatch.setattr(baked, "take_bake", lambda *args, **kwargs: None)
    monkeypatch.setattr(baked, "claimed_bakes", lambda *args: [])
    grounded.take_bakes({"surfaces-bake": tmp_path / "bake", "surfaces-paint": tmp_path / "paint",
                         "ground-join": tmp_path / "join"}, root.parent, TOY)
    assert not opened(root).GetPrimAtPath(f"/{TOY}/Objects/rock_1")


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


def test_base_s_garage_door_lands_on_its_module_s_front_face(tmp_path):
    """Fault (motion@base, 2026-10-29): base's garage door stood 0.17 m off its module's front and 4.7 m of its 6 m
    past the module's corner, laid at its plan item's middle; its motion check failed it. Laid by its relation (on the
    module's S face, `out` +z) at their built sizes, the 12 m module from 26.254 to 38.254 across and to 39.4 in front,
    the 6 x 8 x 0.5 m door stands with its back on z 39.4, its foot on the floor; at the module's corner it is shifted
    in so its recess's 0.55 m of room on its hinge side (-x) fits the face too: its middle from 24.5585 to 26.254 +
    0.55 + 3 = 29.804 (score, 2026-10-29: never swinging round the corner); LAID names the fit.
    Break: score/stages/assembly/fitting.py: `target[side] = kept_within(foot[side], hold_low[side] + below,
        hold_high[side] - above,` -> `target[side] = kept_within(foot[side], hold_low[side], hold_high[side],`
    Break: score/stages/assembly/made_waiting.py: `laid_by_relations(stage, out, place, record, objects, baked)` -> `pass`
    Break: score/stages/assembly/fitting.py: `target[axis] = face + sign * half[axis]` -> `target[axis] = foot[axis]`"""
    root = a_toy(tmp_path / "out")
    entries = [{"name": "square_module_front_right_1", "row": "square_module_front_right", "bake": "module_1",
                "at": [32.254, 0.0, 33.4], "rotation": [0.0, 0.0, 0.0, 1.0], "kind": "object", "waiting": "bake"},
               {"name": "garage_door_1", "row": "garage_door", "bake": "door_1", "at": [24.5585, 0.0, 39.8395],
                "rotation": [0.0, 0.0, 0.0, 1.0], "kind": "object", "waiting": "bake",
                "on": {"how": "face", "holder": ["square_module_front_right_1"], "out": [0.0, 1.0], "room": 0.55,
                       "room_way": [-1.0, 0.0],
                       "why": "against its module's side the concept shows it on"}}]
    assembly.take_record(a_record(tmp_path, {"objects": entries}), root.parent, TOY)
    a_box_asset(root.parent / "assets/module_1.usdc", (-6.0, 0.0, -6.0), (6.0, 12.0, 6.0))
    a_box_asset(root.parent / "assets/door_1.usdc", (-3.0, 0.0, -0.25), (3.0, 8.0, 0.25))
    (tmp_path / "bake").mkdir()
    (tmp_path / "bake/baked.json").write_text(json.dumps({"module_1": {}, "door_1": {}}))
    made_waiting.lay(root.parent, TOY, tmp_path / "bake")
    from score.stages.assembly import fitting
    low, high = fitting.world_box(opened(root), f"/{TOY}/Objects/garage_door_1")
    assert np.allclose(low, (26.804, 0.0, 39.4), atol=1e-4) and np.allclose(high, (32.804, 8.0, 39.9), atol=1e-4), (
        low, high)
    [fit] = json.loads((root.parent / made_waiting.LAID).read_text())["fitted"]
    assert fit["name"] == "garage_door_1" and fit["how"] == "face" and fit["scale"] == 1.0, fit
    held = assembly.judge_held(root.parent, {}, None)
    assert held.answer == checks.PASS and held.measures == {"not held": 0, "worst off": 0.0}, held


def test_base_s_built_garage_door_goes_in_its_recess_on_the_face_round_it(tmp_path):
    """#36, motion@base: the module's box reaches z 39.43 only by a 0.39 m lip above the doorway, its face round the
    recess at 39.039, so the door laid on the box's side hung in the air; and the bake cut the recess from the row's
    6 m (6.6 with its room), while the built door, 8.30 m, covered solid wall past it. Here the module's face stands at
    z 39.0 below 8 m and its lip at 39.4 above, the bake's recess runs x 26.304 to 32.904 (its own -5.95 to 0.65) at
    the module's corner, 8 m tall, and the 8 x 8 x 0.5 m door with 0.6 m of room on its hinge side (-x) is shrunk to
    6 / 8 = 0.75 to fit the recess less its room. It hangs in the recess as a door in its opening does (motion@base,
    round 32: hung 0.6 m off the jamb, its back on the face, the shrunk door touched nothing once it swung): its hinge
    edge at the recess's -x jamb (x 26.304 to 32.304, no room left beside it on the face, none needed), its middle on
    the face, z 39.0 (38.8125 to 39.1875), from the recess's foot; LAID names the plane its back is on and that it
    hangs in its recess, and the held gate measures it there.
    Break: score/stages/assembly/fitting.py: `face = front_face(surface, axis, sign, side, span, (target[1], target[1]
        + size[1] * scale))` -> `face = None`
    Break: score/stages/assembly/fitting.py: `if cut is not None:` -> `if False:`
    Break: score/stages/assembly/made_waiting.py: `{model: entry.get("cuts") for model, entry in (baked or
        {}).items()}` -> `{}`
    Break: score/stages/assembly/fitting.py: `target[side] = cut[0][side] + half_wide if below > above else` ->
        `target[side] = (cut[0][side] + below + cut[1][side] - above) / 2 if True else`
    Break: score/stages/assembly/fitting.py: `target[axis] = face if cut is not None else face + sign * half[axis]` ->
        `target[axis] = face + sign * half[axis]`
    Break: score/stages/assembly/fitting.py: `**({"room": 0.0} if fitted_on.get("hung") else {})` -> `**{}`"""
    root = a_toy(tmp_path / "out")
    entries = [{"name": "square_module_front_right_1", "row": "square_module_front_right", "bake": "module_1",
                "at": [32.254, 0.0, 33.4], "rotation": [0.0, 0.0, 0.0, 1.0], "kind": "object", "waiting": "bake"},
               {"name": "garage_door_1", "row": "garage_door", "bake": "door_1", "at": [24.5585, 0.0, 39.8395],
                "rotation": [0.0, 0.0, 0.0, 1.0], "kind": "object", "waiting": "bake",
                "on": {"how": "face", "holder": ["square_module_front_right_1"], "out": [0.0, 1.0], "room": 0.6,
                       "room_way": [-1.0, 0.0], "why": "against its module's side the concept shows it on"}}]
    assembly.take_record(a_record(tmp_path, {"objects": entries}), root.parent, TOY)
    an_asset(root.parent / "assets/module_1.usdc", *boxes_mesh([
        ((-6.0, 0.0, -6.0), (-5.95, 8.0, 5.6)), ((0.65, 0.0, -6.0), (6.0, 8.0, 5.6)),  # the body beside the recess
        ((-5.95, 0.0, -6.0), (0.65, 8.0, -0.05)), ((-6.0, 8.0, -6.0), (6.0, 12.0, 6.0))]))  # its back, the lip
    a_box_asset(root.parent / "assets/door_1.usdc", (-4.0, 0.0, -0.25), (4.0, 8.0, 0.25))
    (tmp_path / "bake").mkdir()
    (tmp_path / "bake/baked.json").write_text(json.dumps(
        {"module_1": {"cuts": [{"recess": [[-5.95, 0.0, -0.05], [0.65, 8.0, 6.05]]}]}, "door_1": {"cuts": []}}))
    made_waiting.lay(root.parent, TOY, tmp_path / "bake")
    from score.stages.assembly import fitting
    low, high = fitting.world_box(opened(root), f"/{TOY}/Objects/garage_door_1")
    assert np.allclose(low, (26.304, 0.0, 38.8125), atol=1e-4) and np.allclose(high, (32.304, 6.0, 39.1875),
                                                                                atol=1e-4), (low, high)
    [fit] = json.loads((root.parent / made_waiting.LAID).read_text())["fitted"]
    assert fit["scale"] == 0.75 and fit["face"] == 38.8125 and fit["hung"], fit
    held = assembly.judge_held(root.parent, {}, None)
    assert held.answer == checks.PASS and held.measures == {"not held": 0, "worst off": 0.0}, held


def test_a_door_stands_on_its_built_wall_s_face_and_one_short_of_its_opening_is_named(tmp_path):
    """#36: hangar's and garage's shell walls stand 0.15 m behind the plan's line, so a door laid on the line hung 0.04
    to 0.15 m in front of its wall and left its jamb and sill as it swung (motion@garage grounded). A 2.4 x 2.4 x 0.2 m
    door in its 2.4 m wide, 2.66 m tall opening at z 0.15, the built wall's sill and lintel from z -0.276 to 0 (its
    jamb beside the opening never counts), stands with its middle on the wall's room face, z 0; the held gate measures
    it there, passes it there and fails one left on the plan's line 0.15 m off. A 2 m door, narrower than its opening,
    stands against the jamb its own left edge faces, its hinge on its jamb (motion@garage: the 2.01 m round door,
    centred in its 2.41 m opening, swung on a hinge 0.2 m off its jamb), and passes there. Each is named 0.26 m short
    of its opening's height (hangar's doorway, a wall panel shrunk to 0.72 m tall) among the gate's findings, which
    never fail it: only a take made again, a paid one, mends it (coordinator, 2026-10-30).
    Break: score/stages/assembly/fitting.py: `spot[axis] = face` -> `pass`
    Break: score/stages/assembly/fitting.py: `if wide is not None and abs(lined) >= 0.9` -> `if False and abs(lined)
        >= 0.9`
    Break: score/stages/assembly/fitting.py: `for way in (None, on["along"], np.negative(on["along"]))]` -> `for way in
        (None,)]`
    Break: score/stages/assembly/fitting.py: `if short > HELD_MOST:` -> `if False:`
    Break: score/stages/assembly/held_apart.py: `*(f"{name}: {words}" for name, words, _ in
        fitting.short_doors(record, laid))))` -> `))`
    Break: score/stages/assembly/fitting.py: `held = [boxes[name] for name in on.get("holder") or [] if name in
        boxes] if on["how"] != "in" else walls` -> `... else []`
    Break: score/stages/assembly/opening_walls.py: `if near(own) or not near(2 - own):` -> `if True:` (the collar
        door left along z), or `-> if not near(2 - own):` (the side door turned onto the sill across its wall's end)"""
    from score import stages
    from score.stages.assembly import fitting
    walls = [{"name": "wall_1", "low": [-5.0, -0.2, -0.276], "high": [-1.2, 4.6, 0.0]},
             {"name": "wall_1_2", "low": [-1.2, -0.2, -0.276], "high": [1.2, 0.0, 0.0]},
             {"name": "wall_1_3", "low": [-1.2, 2.66, -0.276], "high": [1.2, 4.6, 0.0]}]
    on = {"how": "in", "middle": [0.0, 0.0, 0.15], "along": [1.0, 0.0], "wide": 2.4, "tall": 2.66, "why": "opening 1"}
    scale, target, _, _ = fitting.fit((-1.2, 0.0, 0.05), (1.2, 2.4, 0.25), on,
                                      [(wall["low"], wall["high"]) for wall in walls])
    assert scale == 1.0 and np.allclose(target, (0.0, 0.0, 0.0)), (scale, target)
    _, target, _, _ = fitting.fit((-1.0, 0.0, 0.05), (1.0, 2.4, 0.25), on,
                                  [(wall["low"], wall["high"]) for wall in walls], left=(-1.0, 0.0))
    assert np.allclose(target, (-0.2, 0.0, 0.0)), target  # its own left edge, its hinge, on the -x jamb
    narrow = {"objects": [{"name": "door_3", "on": on, "fills": True}]}
    assert fitting.held_faults(narrow, {"walls": walls, "objects": [
        {"name": "door_3", "low": [-1.2, 0.0, -0.1], "high": [0.8, 2.4, 0.1]}]}) == []
    record = {"objects": [{"name": "door_1", "on": on, "fills": True}, {"name": "door_2", "on": on, "fills": True}]}
    laid = {"walls": walls, "objects": [{"name": "door_1", "low": [-1.2, 0.0, -0.1], "high": [1.2, 2.4, 0.1]},
                                        {"name": "door_2", "low": [-1.2, 0.0, 0.05], "high": [1.2, 2.4, 0.25]}]}
    assert fitting.held_faults(record, laid) == [("door_2", "0.15 m off where it is laid in (opening 1)", 0.15)], \
        fitting.held_faults(record, laid)
    short = "too small for its opening: 0.26 m short of its 2.66 m height"
    assert fitting.short_doors(record, laid) == [("door_1", short, 0.26), ("door_2", short, 0.26)]
    one = {"objects": record["objects"][:1]}
    (tmp_path / made_waiting.LAID).write_text(json.dumps({**laid, "objects": laid["objects"][:1]}))
    (tmp_path / assembly.RECORD).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / assembly.RECORD).write_text(json.dumps(one))
    [held] = [check.judge for check in stages.ASSEMBLY.checks if check.name == "held"]
    verdict = held(tmp_path, {}, None)
    assert verdict.answer == checks.PASS and f"door_1: {short}" in verdict.findings, verdict
    # tube (2026-11-12): its plan draws only its long walls; its end opening (middle x 0, z 0), given the left wall's
    # way (z) 1.6 m off, is turned onto the end wall its shell built across it (its sill and lintel along x, their
    # line at z -0.3), a quarter turn; one on its own wall keeps its way.
    from score.stages.assembly import opening_walls
    ends = [((-1.1, -0.2, -0.45), (1.1, 0.0, -0.15)), ((-1.1, 2.6, -0.45), (1.1, 3.0, -0.15)),
            ((-1.668, -0.2, -0.45), (-1.532, 3.2, 10.49))]
    collar = {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [0.0, 1.0], "wide": 2.2, "tall": 2.6}
    turned, degrees = opening_walls.across(collar, 0.0, ends)
    assert turned["along"] == [1.0, 0.0] and np.allclose(turned["middle"], (0.0, 0.0, -0.3)) and \
        abs(degrees) == 90.0, (turned, degrees)
    side = {**collar, "middle": [-1.6, 0.0, 5.0]}
    assert opening_walls.across(side, 0.0, ends) == (side, 0.0)


def test_the_held_gate_names_each_object_not_where_what_holds_it_puts_it():
    """#72, so it never comes back silently: the `held` gate fails by name on a door laid 1 m beside its module's
    face (its measure 1.0 m), a door or window in no opening and on no holder, one held by nothing and one left at the
    room's middle, and a 6 m door on a 6 m face with 0.55 m of recess room beside it (0.55 m too narrow); the door
    laid on the face passes.
    Break: score/stages/assembly/fitting.py: `if narrow > HELD_MOST:` -> `if False:`
    Break: score/stages/assembly/fitting.py: `elif distance > HELD_MOST:` -> `elif False:`
    Break: score/stages/assembly/fitting.py: `if entry.get("fills") and not (on and on["how"] in ("in", "face",
        "within", "top")):` -> `if False:`
    Break: score/stages/assembly/fitting.py: placement_faults' `if wrong:` -> `if False:`; on_holder's
        `hold_low[1] if on.get("under") else` dropped (cables under a desk left up in it)
    Break: score/stages/assembly/fitting.py: off_holder's `above = min(max(0.0, high[1] - hold_high[1]), abs(low[1] -
        hold_high[1]))` -> `above = max(0.0, high[1] - hold_high[1])` (a box on its shelf unit's top off it)"""
    from score.stages.assembly import fitting
    face = {"how": "face", "holder": ["module_1"], "out": [0.0, 1.0]}
    narrow = {"how": "face", "holder": ["shed_1"], "out": [0.0, 1.0], "room": 0.55, "room_way": [1.0, 0.0]}
    record = {"objects": [{"name": "door_1", "on": face}, {"name": "door_2", "on": face}, {"name": "door_3", "on": narrow},
                          {"name": "window_1", "fills": True}, {"name": "lamp_1", "unheld": "its holder lays nothing"},
                          {"name": "crate_1", "unplaced": "left on the walls item"}]}
    box = {"low": [0.0, 0.0, 0.0], "high": [1.0, 2.0, 0.0]}
    laid = {"objects": [{"name": "module_1", "low": [-6.0, 0.0, -6.0], "high": [6.0, 12.0, 6.0]},
                        {"name": "door_1", "low": [-3.0, 0.0, 6.0], "high": [3.0, 8.0, 6.5]},
                        {"name": "door_2", "low": [-3.0, 0.0, 7.0], "high": [3.0, 8.0, 7.5]},
                        {"name": "shed_1", "low": [20.0, 0.0, 0.0], "high": [26.0, 9.0, 4.0]},
                        {"name": "door_3", "low": [20.0, 0.0, 4.0], "high": [26.0, 8.0, 4.5]},
                        *[{"name": name, **box} for name in ("window_1", "lamp_1", "crate_1")]]}
    faults = {name: (words, distance) for name, words, distance in fitting.held_faults(record, laid)}
    assert sorted(faults) == ["crate_1", "door_2", "door_3", "lamp_1", "window_1"], faults
    assert ("door_3", "its holder's face is 0.55 m too narrow for it and its recess", 0.55) in \
        fitting.held_faults(record, laid), faults
    assert faults["door_2"][1] == 1.0 and faults["window_1"][0].startswith("a door or window in no opening"), faults
    assert faults["crate_1"][0].startswith("at the room middle") and faults["lamp_1"][0].startswith("held by nothing")
    # its relation against its reading's placement word: cables said under the desk, laid on its top, fail; held
    # under it, laid at its foot, they pass (quarters, 2026-11-04)
    rows = {"desk": {"id": "desk"}, "cables": {"id": "cables", "anchor": "on:desk", "where": "under desk"}}
    top = {"how": "top", "holder": ["desk_1"], "holder row": "desk"}
    under = {"how": "within", "under": True, "holder": ["desk_1"], "holder row": "desk"}
    assert fitting.placement_faults({"objects": [{"name": "cables_1", "row": "cables", "on": top}]}, rows) == [
        ("cables_1", "laid top desk, though its reading says 'under desk' (under)", None)]
    assert fitting.placement_faults({"objects": [{"name": "cables_1", "row": "cables", "on": under}]}, rows) == []
    desk = (np.array([0.0, 0.0, 0.0]), np.array([1.2, 0.75, 0.6]))
    scale, foot = fitting.on_holder(np.array([0.2, 0.5, 0.1]), np.array([0.6, 0.6, 0.3]), "within", under, desk)
    assert scale == 1.0 and abs(foot[1]) < 1e-9, foot  # at the desk's foot, never left 0.5 m up in it
    assert fitting.off_holder(np.array([0.2, 0.5, 0.1]), np.array([0.6, 0.6, 0.3]), "within", under, desk) == 0.5
    # one within its shelf unit laid on its top stands off nothing (on_boards); one through the top, its foot inside
    # 0.2 m under it, stands off it
    unit = (np.array([0.0, 0.0, 0.0]), np.array([1.0, 2.0, 0.5]))
    assert fitting.off_holder(np.array([0.3, 2.0, 0.1]), np.array([0.7, 2.404, 0.5]), "within", {}, unit) == 0.0
    assert abs(fitting.off_holder(np.array([0.3, 1.8, 0.1]), np.array([0.7, 2.204, 0.5]), "within", {}, unit)
               - 0.2) < 1e-9


def test_the_held_gate_names_two_objects_overlapping_on_one_face(tmp_path):
    """#36, street's three restaurant doors: two 1 m doors laid on one facade's +z face 0.58 m apart overlap by
    0.42 m and fail by name; a third 0.58 m further on overlaps only the second; a sign above the doors (no height
    shared) and a door on the facade's -z face at the same spot pass, as do doors held side by side.
    Break: score/stages/assembly/held_apart.py: `if along > fitting.HELD_MOST and tall > fitting.HELD_MOST:` -> `if False:`
    Break: score/stages/__init__.py: `judge=held_apart.judge_held` -> `judge=check.judge`"""
    from score import stages
    from score.stages.assembly import held_apart
    front, back = ({"how": "face", "holder": ["facade_1"], "out": [0.0, way]} for way in (1.0, -1.0))
    names = ("door_1", "door_2", "door_3", "sign_1", "door_4")
    record = {"objects": [{"name": name, "on": back if name == "door_4" else front} for name in names]}
    door = lambda along, z: {"low": [along - 0.5, 0.0, z], "high": [along + 0.5, 2.1, z + 0.1]}  # noqa: E731
    laid = {"holders": [{"name": "facade_1", "low": [0.0, 0.0, -1.0], "high": [10.0, 9.0, 0.0]}],
            "objects": [{"name": "door_1", **door(2.609, 0.0)}, {"name": "door_2", **door(3.189, 0.0)},
                        {"name": "door_3", **door(3.769, 0.0)}, {"name": "door_4", **door(2.609, -1.1)},
                        {"name": "sign_1", "low": [2.0, 2.5, 0.0], "high": [4.0, 3.0, 0.1]}]}
    assert held_apart.overlapping(record, laid) == [
        ("door_1", "overlaps door_2 by 0.42 m along their holder's face", 0.42),
        ("door_2", "overlaps door_3 by 0.42 m along their holder's face", 0.42)], held_apart.overlapping(record, laid)
    (tmp_path / made_waiting.LAID).write_text(json.dumps(laid))
    (tmp_path / assembly.RECORD).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / assembly.RECORD).write_text(json.dumps(record))
    [held] = [check.judge for check in stages.ASSEMBLY.checks if check.name == "held"]
    verdict = held(tmp_path, {}, None)
    assert verdict.answer == checks.FAIL and verdict.measures["overlapping"] == 2, verdict
    assert "door_1: overlaps door_2 by 0.42 m along their holder's face" in verdict.findings, verdict
    apart = {**laid, "objects": [{"name": "door_1", **door(2.0, 0.0)}, {"name": "door_2", **door(3.2, 0.0)}]}
    assert held_apart.overlapping(record, apart) == []


def a_built_box(stage, path, low, high):
    """An Xform at `path` (one transform op) holding a box mesh from `low` to `high`."""
    from pxr import Gf, UsdGeom
    UsdGeom.Xform.Define(stage, path).AddTransformOp().Set(Gf.Matrix4d(1.0))
    mesh = UsdGeom.Mesh.Define(stage, f"{path}/geo")
    mesh.CreatePointsAttr([(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    mesh.CreateExtentAttr([low, high])


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
        float(np.linalg.norm(shift)) <= fitting.MOVE_LEAST:` -> `if True:`"""
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


def test_a_tunnel_against_its_wall_passes_into_it_and_a_pipe_does_not():
    """held@garage, @habitat, @workshop (2026-10-30): a glass tunnel or corridor tube the concept shows meeting its
    module's wall from outside, laid against that wall, reached 0.09 to 0.30 m into the built wall; it joins the place
    through it, as a door stands in its opening, so the held gate excuses its wall, never a deck. A pipe laid against
    the same wall that reaches into it is still named.
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
        drawn back onto the wall too)"""
    from score.stages.assembly import fitting
    against = {"how": "wall", "span": [[0.0, 6.4685], [7.0, 6.4685]], "out": [0.0, 1.0], "why": "against the wall"}
    record = {"objects": [{"name": "glass_tunnel_1", "row": "glass_tunnel", "on": against},
                          {"name": "pipe_1", "row": "pipe", "on": against}]}
    laid = {"walls": [{"name": "wall_3", "low": [0.0, -0.242, 6.4805], "high": [7.0, 4.6, 6.7565]},
                      {"name": "deck_1", "low": [0.0, -0.242, 0.0], "high": [7.0, -0.042, 6.4]}],
            "objects": [{"name": "glass_tunnel_1", "low": [1.0, 0.0, 6.4685], "high": [5.0, 2.5, 9.0]},
                        {"name": "pipe_1", "low": [5.5, 0.0, 6.4685], "high": [6.0, 2.5, 6.9685]}]}
    assert fitting.held_faults(record, laid) == [
        ("pipe_1", "laid 0.28 m inside wall_3, nothing holding it there", 0.276)], fitting.held_faults(record, laid)
    # workshop (settle@workshop, 2026-11-10): its front glass tunnel, laid out from a chord 1.48 m inside its round
    # wall's hatch alcove, stood through the alcove's walls. A tunnel laid outside its room (its middle past the
    # walls' box) reaching into a wall is moved out along its `out` past each wall it reaches into, up to its own
    # depth (3.3 m, moved 1.5 m); a cabinet in the room reaching into the same wall is left as fitted.
    from pxr import Usd
    stage = Usd.Stage.CreateInMemory()
    a_built_box(stage, f"/{TOY}/Structure/wall_1", (-1.0, 0.0, -6.2), (1.0, 3.0, -5.9))
    a_built_box(stage, f"/{TOY}/Structure/wall_2", (0.8, 0.0, -6.2), (1.0, 3.0, -5.6))
    a_built_box(stage, f"/{TOY}/Structure/wall_3", (-5.0, 0.0, 5.0), (5.0, 3.0, 5.2))
    out = {"how": "wall", "span": [[-2.5, -4.7], [2.5, -4.7]], "out": [0.0, -1.0], "why": "against the wall"}
    for name, low, high in (("glass_tunnel_1", (-2.0, 0.0, -8.0), (2.0, 2.5, -4.7)),
                            ("cabinet_1", (-0.5, 0.0, -6.0), (0.5, 2.0, -5.0))):
        a_built_box(stage, f"/{TOY}/Objects/{name}", low, high)
    entries = [{"name": "glass_tunnel_1", "row": "glass_tunnel", "on": out},
               {"name": "cabinet_1", "row": "cabinet", "on": {**out, "out": [0.0, 1.0]}}]
    fits = fitting.moved_past(stage, TOY, entries)
    assert [(fit["name"], fit["how"], fit["moved"], fit["holder"]) for fit in fits] == [
        ("glass_tunnel_1", "past", 1.5, ["wall_1", "wall_2"])], fits
    assert np.allclose(fitting.world_box(stage, f"/{TOY}/Objects/glass_tunnel_1")[1], (2.0, 2.5, -6.2))
    walled = {"objects": [{"name": "glass_tunnel_1", **dict(zip(("low", "high"), fitting.world_box(
        stage, f"/{TOY}/Objects/glass_tunnel_1")))}], "fitted": fits}  # held off the face it was moved out to
    assert fitting.held_faults({"objects": entries[:1]}, walled) == [], fitting.held_faults({"objects": entries[:1]},
                                                                                            walled)
    assert np.allclose(fitting.world_box(stage, f"/{TOY}/Objects/cabinet_1")[0], (-0.5, 0.0, -6.0))
    # past the walls 1.5 m out it would reach into a deck's raised edge farther out, 4.5 m in all: more than its
    # depth, left
    a_built_box(stage, f"/{TOY}/Structure/deck_2", (-1.0, -0.2, -9.2), (1.0, 0.1, -9.0))
    a_built_box(stage, f"/{TOY}/Objects/glass_tunnel_2", (-2.0, 0.0, -8.0), (2.0, 2.5, -4.7))
    assert fitting.moved_past(stage, TOY, [{**entries[0], "name": "glass_tunnel_2"}]) == []
    # workshop (2026-11-11): its round room's walls' box held its tunnels outside it, so they were left across its
    # doors. A tunnel past the room's floor (deck_1, z -5 to 5) inside the walls' box (z -6.2 to 5.2) reaching into
    # wall_1 is outside the room and moved out past it; on a stage with no deck it reads in the room and is left.
    from pxr import UsdGeom
    for decked in (True, False):
        room = Usd.Stage.CreateInMemory()
        a_built_box(room, f"/{TOY}/Structure/wall_1", (-5.0, 0.0, -6.2), (5.0, 3.0, -5.9))
        a_built_box(room, f"/{TOY}/Structure/wall_3", (-5.0, 0.0, 5.0), (5.0, 3.0, 5.2))
        if decked:
            a_built_box(room, f"/{TOY}/Structure/deck_1", (-5.0, -0.2, -5.0), (5.0, 0.0, 5.0))
            floor = UsdGeom.Mesh(room.GetPrimAtPath(f"/{TOY}/Structure/deck_1/geo"))
            floor.CreateFaceVertexCountsAttr([4])
            floor.CreateFaceVertexIndicesAttr([2, 3, 7, 6])  # its top
        a_built_box(room, f"/{TOY}/Objects/glass_tunnel_1", (-1.0, 0.0, -7.0), (1.0, 2.5, -5.0))
        moved = fitting.moved_past(room, TOY, entries[:1])
        assert [fit["name"] for fit in moved] == (["glass_tunnel_1"] if decked else []), (decked, moved)
    # workshop (settle@workshop, 2026-11-11): its glass tunnels stood outside its twelve built walls on its plan's
    # eight facets, 0.06 to 0.19 m off the nearest, touching nothing. Laid with its back on its span 0.2 m out of
    # wall_1's outer face, a tunnel is drawn back along its `out` until it stands within GAP of the wall, never in it,
    # and the held gate judges it on the face it now stands on; a pipe laid so is no passage and is left; a tunnel
    # 1.2 m off (past OUT_MOST) is left, as is one already within GAP.
    from pxr import Gf
    from score.stages.assembly import passages

    def solid(stage, path, low, high):
        """A box mesh from `low` to `high` with its faces, under an Xform at `path`."""
        box = trimesh.creation.box(bounds=[low, high])
        UsdGeom.Xform.Define(stage, path).AddTransformOp().Set(Gf.Matrix4d(1.0))
        mesh = UsdGeom.Mesh.Define(stage, f"{path}/geo")
        mesh.CreatePointsAttr([tuple(map(float, point)) for point in box.vertices])
        mesh.CreateFaceVertexCountsAttr([3] * len(box.faces))
        mesh.CreateFaceVertexIndicesAttr([int(index) for index in box.faces.reshape(-1)])
        mesh.CreateExtentAttr([low, high])

    for off, name, row, moved in ((0.2, "glass_tunnel_1", "glass_tunnel", 0.2), (0.2, "pipe_1", "pipe", None),
                                  (1.2, "glass_tunnel_2", "glass_tunnel", None),
                                  (0.004, "glass_tunnel_3", "glass_tunnel", None)):
        room = Usd.Stage.CreateInMemory()
        solid(room, f"/{TOY}/Structure/wall_1", (-5.0, 0.0, -6.2), (5.0, 3.0, -5.9))
        solid(room, f"/{TOY}/Structure/wall_3", (-5.0, 0.0, 5.0), (5.0, 3.0, 5.2))
        solid(room, f"/{TOY}/Objects/{name}", (-2.0, 0.0, -9.2 - off), (2.0, 2.5, -6.2 - off))
        entry = {"name": name, "row": row, "on": {"how": "wall", "span": [[-2.5, -6.2 - off], [2.5, -6.2 - off]],
                                                  "out": [0.0, -1.0], "why": "against the wall"}}
        fits = [fit for fit in fitting.fitted(room, TOY, [entry], {name}) if fit["how"] == "drawn"]
        far = -6.2 - float(fitting.world_box(room, f"/{TOY}/Objects/{name}")[1][2])
        if moved is None:
            assert not fits and abs(far - off) < 1e-6, (name, fits, far)
            continue
        assert [(fit["name"], round(fit["moved"], 2)) for fit in fits] == [(name, moved)] and \
            0.0 < far <= passages.GAP, (fits, far)
        laid = {"objects": [{"name": name, **dict(zip(("low", "high"), fitting.world_box(
            room, f"/{TOY}/Objects/{name}")))}], "fitted": fits}
        assert fitting.held_faults({"objects": [entry]}, laid) == [], fitting.held_faults({"objects": [entry]}, laid)


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


def test_a_door_goes_in_its_opening_narrowed_to_fit():
    """A 1.4 x 0.1 x 2.4 m door laid off its wall goes in its 1.2 m wide, 2.1 m tall opening: shrunk to 2.1 / 2.4 for
    its height, then held across its width alone to the opening's 1.2 m (1.2 / 1.4 of its own), its foot's middle on
    the opening's middle at its sill. Between built jambs 0.3 m thick centred on the opening's ends (the lab's entry
    passage, motion@lab round 35: 1.264 m clear in a 1.896 m opening) it is held to the 0.9 m clear between them, and
    a 0.6 m door there stands against the jamb its own left edge faces, not the plan's opening end.
    Break: score/stages/assembly/fitting.py: `scale[run_axis] *= (end - start) / wide` -> `pass`
    Break: score/stages/assembly/fitting.py: `            start = max(start, far)` -> `            pass`
    Break: score/stages/assembly/fitting.py: hole_wall's `if not inside:` -> `if True:` (laid in an uncut wall), or
        its `along[axis // 2] = 1.0 if` -> `along[2 - axis // 2] = 1.0 if` (turned across its wall), or its `if
        own_jambs(on, mesh, height):` -> `if False:` (moved out of its own slanted wall)
    Break: score/stages/assembly/fitting.py: opening_clear's `floor = max(` -> `floor = min(` (its sill left in the
        pavement), or its `reach.append(float(met.min())` -> `reach.append(float(met.max())` (held past the fold)"""
    from score.stages.assembly import fitting
    opening = {"how": "in", "middle": [5.0, 0.0, 0.0], "along": [1.0, 0.0], "wide": 1.2, "tall": 2.1}
    scale, target, words, _ = fitting.fit((0.3, 0.0, 2.95), (1.7, 2.4, 3.05), opening)
    assert np.allclose(scale, (1.2 / 1.4, 2.1 / 2.4, 2.1 / 2.4)), scale
    assert np.allclose(target, (5.0, 0.0, 0.0)), target
    assert "narrowed to 86% across" in words, words
    jambs = [((4.25, -0.2, -1.0), (4.55, 2.8, 1.0)), ((5.45, -0.2, -1.0), (5.75, 2.8, 1.0))]
    scale, target, _, _ = fitting.fit((0.3, 0.0, 2.95), (1.7, 2.1, 3.05), opening, jambs)
    assert np.allclose(scale, (0.9 / 1.4, 1.0, 1.0)) and np.allclose(target, (5.0, 0.0, 0.0)), (scale, target)
    _, target, _, _ = fitting.fit((0.3, 0.0, 2.95), (0.9, 2.1, 3.05), opening, jambs, left=(-1.0, 0.0))
    assert np.allclose(target, (4.85, 0.0, 0.0)), target
    # settle@street (2026-11-11): its restaurant door 2's plan opening lies on a slanted plan wall, 0.67 m off the
    # straight wall_2 the kit's shell cut its 1 m hole in (z -3.2 to -2.2 at x -2.85 to -2.55); laid slanted across
    # it, it stood 0.15 m in the wall. It is laid along that wall in its hole, turned 20.9 degrees; with no hole cut
    # there, as it is.
    def boxes(*found):
        return trimesh.util.concatenate([trimesh.creation.box(bounds=bounds) for bounds in found])
    holed = boxes([(-2.85, 0.0, -4.4), (-2.55, 3.5, -3.2)], [(-2.85, 0.0, -2.2), (-2.55, 3.5, -1.1)],
                  [(-2.85, 0.0, -3.2), (-2.55, 0.2, -2.2)], [(-2.85, 2.7, -3.2), (-2.55, 3.5, -2.2)])
    piece = (np.array([-2.85, 0.0, -4.4]), np.array([-2.55, 3.5, -1.1]))
    slanted = {"how": "in", "middle": [-2.032, 0.2, -2.7], "along": [0.356, -0.934], "wide": 1.0, "tall": 2.5}
    walled, degrees = fitting.hole_wall(slanted, [piece], holed)
    assert np.allclose(walled["middle"], (-2.7, 0.2, -2.7)) and walled["along"] == [0.0, -1.0], walled
    assert abs(degrees - 20.87) < 0.05, degrees
    solid = boxes([(-2.85, 0.0, -4.4), (-2.55, 3.5, -1.1)])
    assert fitting.hole_wall(slanted, [piece], solid) == (slanted, 0.0)
    # one cut in its own slanted wall (a wall stands on its line just past its end) stays in it
    jamb = boxes([(-1.9, 0.0, -3.4), (-1.7, 3.5, -3.1)])
    own = trimesh.util.concatenate([holed, jamb])
    assert fitting.hole_wall(slanted, [piece], own) == (slanted, 0.0)
    # ... and its roller shutters, 0.35 m deep: one cut with its sill 0.2 m under the pavement before it, the facade
    # folding back across its far end. A 3 m shutter along x: its floor is the pavement's top, its clear run ends at
    # the fold 1.2 m along, and nothing stands the other way.
    shutter = trimesh.creation.box(bounds=[(-1.5, 0.0, -0.175), (1.5, 3.0, 0.175)])
    around = boxes([(-2.0, 0.0, 0.0), (2.0, 0.2, 1.0)], [(1.2, 0.0, -1.0), (1.3, 3.0, 1.0)])
    floor, start, end = fitting.opening_clear(np.asarray(shutter.vertices), {"along": [1.0, 0.0]}, around)
    assert abs(floor - 0.2) < 1e-6 and abs(end - 1.2) < 1e-6 and start == -np.inf, (floor, start, end)


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


def test_nothing_laid_stands_in_a_doorway_s_passage_or_a_facade_door_s_swing():
    """#36, garage 2026-10-30: its doors swung out of the room clear, but pipes laid along the walls inside ran across
    both doorways, so nobody could walk through; street's drying racks, laid on their facade under its doors (hung on
    the facade, no opening), stood in the doors' swing either way. A 1 x 2 x 0.1 m door in its 1.2 m opening of a
    shell wall from z -0.1 to 0.1, swinging out of the room (to -z), hangs on the outer face against its left jamb,
    x -0.6 to 0.4, z -0.15 to -0.05; its
    passage is the opening's width, x -0.6 to 0.6, a person's 1.8 m from its foot, and a step (0.75 m) beyond either
    face, z -0.9 to 0.85. A 3.2 m pipe laid on the wall's room face across the doorway, out of the door's swing but in
    its passage, goes to the longest stretch beside it, shrunk to 2.4 m, x -3 to -0.6; a lamp on the wall over the
    doorway at 1.9 to 2.2 m, above the passage, stays. A 1 x 2 x 0.1 m shop door laid on a facade box (x -3 to 3, its
    face toward the street z 4.8), swinging to the street, stands x 1.5 to 2.5 on it; a 1.2 m drying rack laid on the
    facade at its foot goes to the nearest stretch of the face out of its swing that holds it, x 0.3 to 1.5, whole;
    it never hangs in a recess the bake cut in the facade, which only a thing whose relation names one (its `room`:
    the door it was cut for) hangs in (street's racks hung in its doors' recesses).
    Break: score/stages/assembly/fitting.py: `recess_of(recesses, axis, sign, foot, box) if "room" in on else None` ->
        `recess_of(recesses, axis, sign, foot, box)`
    Break: score/stages/assembly/fitting.py: `return swing_box(stage, path), passage_box(*world_box(stage, path),
        by_name[leaf]["on"], built)` -> `return (swing_box(stage, path),)`
    Break: score/stages/assembly/fitting.py: `low[axis], high[axis] = min([low[axis], *faces]) - STEP,
        max([high[axis], *faces]) + STEP` -> `low[axis], high[axis] = min([low[axis], *faces]), max([high[axis],
        *faces])`
    Break: score/stages/assembly/fitting.py: `high[1] = low[1] + PASSAGE_TALL` -> `pass` (the passage as tall as the
        door: the lamp over it moved)
    Break: score/stages/assembly/fitting.py: `if how in ("wall", "face") and name not in leaves else ()` -> `if how ==
        "wall" and name not in leaves else ()`
    Break: score/stages/assembly/fitting.py: `entry["on"]["how"] in ("in", "face") and swings(entry["row"])` ->
        `entry["on"]["how"] == "in" and swings(entry["row"])`
    Break: score/stages/assembly/fitting.py: `scale, target, face = on_face(low, high, on, box, surface, recesses,
        clear)` -> `scale, target, face = on_face(low, high, on, box, surface, recesses)`"""
    from pxr import Gf, Usd, UsdGeom
    from score.stages.assembly import fitting
    stage = Usd.Stage.CreateInMemory()
    for name, size, at in (("Objects/pipe_1", (3.2, 1.0, 0.32), (0.0, 0.5, 2.0)),
                           ("Objects/lamp_1", (0.4, 0.3, 0.1), (0.0, 2.05, 0.15)),
                           ("Objects/door_1", (1.0, 2.0, 0.1), (0.0, 1.0, 3.0)),
                           ("Shell/wall_2", (1.2, 0.1, 0.2), (0.0, -0.05, 0.0)),
                           ("Objects/facade_1", (6.0, 3.0, 0.4), (0.0, 1.5, 5.0)),
                           ("Objects/shop_door_1", (1.0, 2.0, 0.1), (2.0, 1.0, 3.0)),
                           ("Objects/drying_rack_1", (1.2, 0.1, 0.4), (2.0, 0.05, 3.0))):
        xform = UsdGeom.Xform.Define(stage, f"/{TOY}/{name}")
        cube = UsdGeom.Cube.Define(stage, f"/{TOY}/{name}/geo")
        cube.AddScaleOp().Set(Gf.Vec3f(*(side / 2 for side in size)))
        xform.AddTransformOp().Set(Gf.Matrix4d().SetTranslate(Gf.Vec3d(*at)))
    wall = {"how": "wall", "span": [[-3.0, 0.1], [3.0, 0.1]], "out": [0.0, 1.0]}
    facade = {"how": "face", "holder": ["facade_1"], "out": [0.0, -1.0]}
    doorway = {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [1.0, 0.0], "wide": 1.2, "tall": 2.2}
    entries = [{"name": "pipe_1", "row": "pipe", "on": wall}, {"name": "lamp_1", "row": "lamp", "on": wall},
               {"name": "drying_rack_1", "row": "drying_rack", "on": facade},
               {"name": "shop_door_1", "row": "shop_door", "on": facade},
               {"name": "door_1", "row": "door", "on": doorway}]
    fits = {fit["name"]: fit for fit in fitting.fitted(stage, TOY, entries, {entry["name"] for entry in entries})}
    assert np.allclose(fits["door_1"]["low"], (-0.6, 0.0, -0.15)) and np.allclose(fits["door_1"]["high"],
                                                                                   (0.4, 2.0, -0.05)), fits
    passage = fitting.passage_box(*fitting.world_box(stage, f"/{TOY}/Objects/door_1"), doorway,
                                  [box for _, box in fitting.walls(stage, TOY)])
    assert np.allclose(passage[0], (-0.6, 0.0, -0.9)) and np.allclose(passage[1], (0.6, 1.8, 0.85)), passage
    assert fits["pipe_1"]["scale"] == 0.75 and np.allclose(fits["pipe_1"]["low"], (-3.0, 0.0, 0.1)) \
        and np.allclose(fits["pipe_1"]["high"], (-0.6, 0.75, 0.34)), fits
    assert "lamp_1" not in fits, fits
    assert np.allclose(fits["shop_door_1"]["low"], (1.5, 0.0, 4.7)), fits
    assert fits["drying_rack_1"]["scale"] == 1.0 and np.allclose(fits["drying_rack_1"]["low"], (0.3, 0.0, 4.4)) \
        and np.allclose(fits["drying_rack_1"]["high"], (1.5, 0.1, 4.8)), fits
    box, recess = (np.array([-3.0, 0.0, 4.8]), np.array([3.0, 3.0, 5.2])), (np.array([1.5, 0.0, 4.8]),
                                                                              np.array([2.5, 2.1, 5.0]))
    rack = (np.array([1.4, 0.0, 4.4]), np.array([2.6, 0.1, 4.8]))
    assert not fitting.on_face(*rack, facade, box, None, [recess])[2][1]  # a rack never hangs in a door's recess
    assert fitting.on_face(*rack, dict(facade, room=0.0), box, None, [recess])[2][1]  # the door it was cut for does


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
    one already in front of the tube stays.
    Break: score/stages/assembly/face_spots.py: met's `if face is None:` -> `if True:` (the valve left on the box's
        side, touching nothing), or fitting.py's `target = face_spots.met(surface, on, box, size * scale, target,
        clear)` dropped"""
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


def test_a_door_in_a_slanted_wall_hangs_on_the_face_it_swings_to():
    """#36, cockpit 2026-10-30: its rear doors, in an opening of a slanted wall (its boxes say nothing of its faces),
    stood on the plan's line 0.37 m in front of the built wall and swung their kind's way into its jamb. A 1 m opening
    at the origin along (0.6, 0.8), its built wall's jambs from 0.3 to 0.5 m across it the way (0.8, -0.6): a door
    turned so its own -z points that way (its kind's swing) stands with its foot middle on the far face, (0.4, -0.3);
    one swinging the other way on the near face, (0.24, -0.18); the held gate passes it there. A deck's corner 0.9 m
    out beside it is no wall face (camp's dome door, by no built wall, was hung on its deck's corner), nor is a wall
    under its sill 0.8 m out (greenhouse's door, in its dome, was hung on the tops of the walls under it, motion round 34).
    Break: score/stages/assembly/fitting.py: `surface = wall_points(stage, place)` -> `surface = None`
    Break: score/stages/assembly/fitting.py: `or wall[beside, 1].max() < head - WALL_REACH:` -> `or False:`
    Break: score/stages/assembly/fitting.py: `spot[[0, 2]] += way * float(max(faces))` -> `spot[[0, 2]] += way *
        float(min(faces))`
    Break: score/stages/assembly/fitting.py: `return float(np.linalg.norm(off - normal * np.clip(off @ normal, -2 *
        WALL_REACH, 2 * WALL_REACH)))` -> `return float(np.linalg.norm(off))`"""
    from pxr import Gf, Usd, UsdGeom
    from score.stages.assembly import fitting
    run, normal = np.array([0.6, 0.8]), np.array([0.8, -0.6])
    jambs = [run * along + normal * deep for along in (-1.5, -0.5, 0.5, 1.5) for deep in (0.3, 0.5)]
    points = np.array([[x, y, z] for x, z in jambs for y in (0.0, 2.0)])
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.Mesh.Define(stage, f"/{TOY}/Shell/wall_1").GetPointsAttr().Set([Gf.Vec3f(*point) for point in points])
    corner = normal * 0.9  # a deck's corner beside the opening, no wall
    UsdGeom.Mesh.Define(stage, f"/{TOY}/Shell/deck_1").GetPointsAttr().Set(
        [Gf.Vec3f(corner[0], y, corner[1]) for y in (-0.2, 0.0)] + [Gf.Vec3f(-5.0, y, -5.0) for y in (-0.2, 0.0)])
    under = [run * along + normal * 0.8 for along in (-0.5, 0.5)]  # a wall under the sill, out beside it
    UsdGeom.Mesh.Define(stage, f"/{TOY}/Shell/wall_2").GetPointsAttr().Set(
        [Gf.Vec3f(x, y, z) for x, z in under for y in (-2.0, 0.0)])
    xform = UsdGeom.Xform.Define(stage, f"/{TOY}/Objects/door_1")
    UsdGeom.Cube.Define(stage, f"/{TOY}/Objects/door_1/geo").AddScaleOp().Set(Gf.Vec3f(0.5, 1.0, 0.05))
    xform.AddTransformOp().Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), -53.130102))
                               * Gf.Matrix4d().SetTranslate(Gf.Vec3d(0.0, 1.0, 2.0)))
    opening = {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [0.6, 0.8], "wide": 1.0, "tall": 2.0}
    fits = fitting.fitted(stage, TOY, [{"name": "door_1", "row": "door", "on": opening}], {"door_1"})
    middle = (np.array(fits[0]["low"]) + np.array(fits[0]["high"])) / 2
    assert np.allclose(middle[[0, 2]], (0.4, -0.3), atol=1e-3) and abs(fits[0]["low"][1]) < 1e-6, fits
    assert np.allclose(fitting.opening_spot(opening, opens=-normal, points=[points]), (0.24, 0.0, -0.18)), "near face"
    record = {"objects": [{"name": "door_1", "on": opening, "fills": True}]}
    assert fitting.held_faults(record, {"walls": [], "objects": [{"name": "door_1", "low": fits[0]["low"],
                                                                  "high": fits[0]["high"]}]}) == [], fits


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
        fitting.MOVE_LEAST and stands(...):` -> `if False:` (the pile resting on the crest laid again)"""
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


def test_a_wall_item_stands_on_its_named_face():
    """A 1 x 0.6 x 0.2 m wall lamp laid at the room's middle (the walls item) stands with its back on its wall's face
    (z 0.1 to 6.1 at x 2, the room to +x), 0.1 m out from it, slid along to the face's nearest point.
    Break: score/stages/assembly/fitting.py: `spot = start + run * along + out * across(out, size) * scale / 2` ->
        `spot = start + run * along`
    Break: score/stages/assembly/fitting.py: fitted's `clear = [*clear, *wall_holes(faces(), entry["on"], ...)]` ->
        `pass` is caught by the sweep's walkway only; wall_holes' `open_at = ~near...` -> `open_at = near...` (walkway's
        and shiplock's screens hung in the holes cut through their walls)
    Break: score/stages/assembly/fitting.py: walls_ahead's `<= deep]] = True` -> `<= 0.0]] = True` (the rack left in
        the wall folding back in front of its face), or its `taken |= alongs >= past if` -> `taken |= False if` (the
        face past the wall crossing it left free)"""
    from score.stages.assembly import fitting
    on = {"how": "wall", "span": [[2.0, 0.1], [2.0, 6.1]], "out": [1.0, 0.0]}
    scale, target, _, _ = fitting.fit((4.4, 0.0, 2.9), (4.6, 0.6, 3.9), on)
    assert scale == 1.0 and np.allclose(target, (2.1, 0.0, 3.4)), target
    # walkway and shiplock (2026-11-11): screens hung in holes cut through their walls. A wall with a 1 m hole (z 2 to
    # 3) at the thing's height: the hole is found and a 0.5 m screen laid in it goes beside it; with nothing to keep
    # out of it stays.
    import trimesh
    holed = trimesh.util.concatenate([trimesh.creation.box(bounds=[(0.0, 0.0, 0.0), (0.1, 3.0, 2.0)]),
                                      trimesh.creation.box(bounds=[(0.0, 0.0, 3.0), (0.1, 3.0, 6.0)])])
    along = {"how": "wall", "span": [[0.1, 0.0], [0.1, 6.0]], "out": [1.0, 0.0]}
    holes = fitting.wall_holes(holed, along, (1.0, 1.5))
    assert [(round(float(hole[:, 2].min()), 3), round(float(hole[:, 2].max()), 3)) for hole in holes] == [
        (1.975, 3.025)]  # a step's margin past its outermost open rays
    screen = (np.array([0.1, 1.0, 2.25]), np.array([0.2, 1.5, 2.75]))
    assert np.allclose(fitting.on_wall(*screen, along, holes)[1], (0.15, 1.0, 1.725))
    assert np.allclose(fitting.on_wall(*screen, along, ())[1], (0.15, 1.0, 2.5))
    # settle@street (2026-11-11): its drying rack 3, on its slanted wall_7 where wall_8 folds back in front of it,
    # stood 0.05 m in wall_8. A wall 0.2 m in front of the face from z 4 to 6: the run it stands before is found, and
    # a 1 m rack 0.5 m deep laid at z 5 goes before it.
    ahead = trimesh.creation.box(bounds=[(0.3, 0.0, 4.0), (0.4, 3.0, 6.0)])
    taken = fitting.walls_ahead(ahead, along, (1.0, 1.5), 0.5)
    assert [(round(float(run[:, 2].min()), 3), round(float(run[:, 2].max()), 3)) for run in taken] == [
        (3.975, 6.025)], taken
    rack = (np.array([0.1, 1.0, 4.5]), np.array([0.6, 1.5, 5.5]))
    assert np.allclose(fitting.on_wall(*rack, along, taken)[1], (0.35, 1.0, 3.475))
    assert fitting.walls_ahead(ahead, along, (1.0, 1.5), 0.1) == []
    # ... and past where a wall crosses the face itself (wall_8 folding back across wall_7's end): outside the room
    across = trimesh.creation.box(bounds=[(0.0, 0.0, 5.0), (0.5, 3.0, 5.1)])
    assert [(round(float(run[:, 2].min()), 3), round(float(run[:, 2].max()), 3))
            for run in fitting.walls_ahead(across, along, (1.0, 1.5), 0.5)] == [(4.975, 6.025)]


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


def test_the_sound_layer_is_the_sound_stage_s_and_a_sound_placed_nowhere_is_said(tmp_path):
    """Fault (2026-10-12): the assembly kept the seed's sound layer, so camp, launch and square failed complete's sound
    check. The layer is written from the accepted output: the room tone under Sound/Room, the hum at the fan's row, the
    door's sound at its own second (2.5 s, 2.5 x the stage's rate in frames), each file under its world name, the layer
    in the sound's slot of ORDER; a hum on a row the stage lacks is named.
    Break: score/stages/assembly/sounds.py: `start=float(use["at"]) * rate` -> `start=float(use["at"])`
    Break: score/stages/assembly/sounds.py: `if not target or not target.IsActive():` -> `if not target:`
    Break: score/stages/assembly/sounds.py: `unplaced.append(f"{use['sound']} (object): no prim of the row or name
        {use['on']} on the stage")` -> `pass`"""
    from pxr import UsdMedia
    root = a_toy(tmp_path / "out")
    uses = [{"sound": "tone", "role": "room", "on": None, "from": "places.json"},
            {"sound": "hum", "role": "object", "on": "fan", "from": "row fan"},
            {"sound": "hum", "role": "motion", "on": f"/{TOY}/Objects/door_1", "at": 2.5, "loops_until": None,
             "from": "door"},
            {"sound": "hum", "role": "object", "on": "pump", "from": "row pump"}]
    unplaced = sounds.take(a_sound_output(tmp_path / "sound", uses), root, {"sounds": tmp_path / "none.json"})
    assert unplaced == ["hum (object): no prim of the row or name pump on the stage"], unplaced
    stage = opened(root)
    tone = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{TOY}/Sound/Room/tone"))
    assert tone.GetFilePathAttr().Get().path == "../assets/sound/tone.ogg"
    assert (root.parent / "assets/sound/tone.ogg").read_bytes() == b"tone"
    assert stage.GetPrimAtPath(f"/{TOY}/Objects/fan_1/Sound")
    door = UsdMedia.SpatialAudio(stage.GetPrimAtPath(f"/{TOY}/Objects/door_1/Sound_0"))
    assert door.GetStartTimeAttr().Get().GetValue() == 2.5 * stage.GetTimeCodesPerSecond()
    assert stage.GetRootLayer().subLayerPaths[2] == "./layers/sound.usda"
    # hangar (2026-11-11): its second crane, left out by the fitting (inactive), crashed the assembly defining its
    # motion's sound under it; it is a sound placed nowhere, named
    left = a_toy(tmp_path / "left")
    held = opened(left)
    held.GetPrimAtPath(f"/{TOY}/Objects/door_1").SetActive(False)
    held.GetRootLayer().Save()
    unplaced = sounds.take(a_sound_output(tmp_path / "left-sound", uses[2:3]), left, {"sounds": tmp_path / "none.json"})
    assert unplaced == [f"hum (motion): no moving prim /{TOY}/Objects/door_1 on the stage"], unplaced


def test_the_assembly_of_a_read_only_seed_saves_its_copied_base_and_takes_a_read_only_layer(tmp_path):
    """A seed from the store is read-only; its copy takes the record's save over the base and a layer stage's
    read-only layer in place of the seed's (Batch 1, 2026-10-25: every assembly refused the save).
    Break: score/stages/assembly/__init__.py: `shutil.copytree(source, out / part, copy_function=shutil.copyfile)` ->
        `shutil.copytree(source, out / part)`"""
    read_only_toy(tmp_path / "store" / TOY)
    effects = tmp_path / "effects"
    (effects / "layers").mkdir(parents=True)
    (effects / "layers/effects.usda").write_text("#usda 1.0\n")
    (effects / "layers/effects.usda").chmod(0o444)
    (tmp_path / "surfaces.json").write_text(json.dumps({}))
    out = tmp_path / "out"
    out.mkdir()
    assembly.make_from_seed({"seed": tmp_path / "store" / TOY, "effects-layer": effects,
                             "surfaces": tmp_path / "surfaces.json", **a_record(tmp_path, ONE_LAMP)},
                            out, tmp_path / "store" / TOY, {})
    stage = opened(out / f"{TOY}.usda")
    assert stage.GetPrimAtPath(f"/{TOY}/Lights/light_1") and not stage.GetPrimAtPath(f"/{TOY}/Structure/old_wall")
    assert all(path.stat().st_mode & 0o200 for path in out.rglob("*") if path.is_file())


def test_a_place_s_made_ground_takes_the_surface_its_scene_library_gives_its_row(tmp_path):
    """Hub (#36, assembly@hub placeholders): the terrain's made ground came in as /<place>/Outside/near and far, its
    finish named missing, drawn with no material. Each mesh of it is bound in the taken (read-only) ground layer to
    the surface the scene's surface library gives its row's kind (lunar_surface, a ground: lunar_regolith, laid under
    the place's Library by the earth seed), its missing note gone, so the placeholder gate passes it; a row the
    library gives none (the sea) keeps its finish named missing.
    Break: score/stages/assembly/__init__.py: `finish_ground(inputs, out / root.name, folder.name)` -> `None`
    Break: score/stages/assembly/ground_finish.py: `prim.RemoveProperty("score:surface:missing")` -> `None`"""
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
    from score.stages.terrain import outside
    import placeholders
    a_toy(tmp_path / "store" / TOY)
    base = Usd.Stage.Open(str(tmp_path / "store" / TOY / "layers/base.usda"))
    shader = UsdShade.Shader.Define(base, f"/{TOY}/Library/lunar_regolith/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.34, 0.28, 0.22))
    UsdShade.Material.Define(base, f"/{TOY}/Library/lunar_regolith").CreateSurfaceOutput().ConnectToSource(
        shader.ConnectableAPI(), "surface")
    base.GetRootLayer().Save()
    for path in (tmp_path / "store" / TOY).rglob("*"):
        if path.is_file():
            path.chmod(0o444)
    inputs = a_record(tmp_path, ONE_LAMP)
    (tmp_path / "terrain/moon/places").mkdir(parents=True)
    ground = Usd.Stage.CreateNew(str(tmp_path / "terrain/moon/places" / f"{TOY}.usdc"))
    points, triangles = np.array([[0, 0, 0], [1, 0, 0], [0, 0, 1]], float), np.array([[0, 2, 1]])
    outside.write(ground, TOY, {"near": (points, triangles), "far": (points, triangles)}, "lunar_surface",
                  ["regolith", "the test's"], (points, triangles, "sea", ["ocean", "the test's"]))
    ground.GetRootLayer().Save()
    (tmp_path / "terrain/moon/places" / f"{TOY}.usdc").chmod(0o444)
    (tmp_path / "inventory").mkdir()
    (tmp_path / "inventory" / f"{TOY}.json").write_text(json.dumps({"rows": [
        {"id": "lunar_surface", "noun": "ground", "terrain": True}, {"id": "sea", "noun": "sea", "terrain": True}]}))
    (tmp_path / "library").mkdir()
    (tmp_path / "library/materials.json").write_text(json.dumps({"kinds": {"ground": ["lunar_regolith"],
                                                                           "wall": ["hull_paint"]}}))
    (tmp_path / "surfaces.json").write_text(json.dumps({}))
    out = tmp_path / "out"
    out.mkdir()
    assembly.make_from_seed({"seed": tmp_path / "store" / TOY, "surfaces": tmp_path / "surfaces.json",
                             "inventories": tmp_path / "inventory", "surface-library": tmp_path / "library",
                             **inputs}, out, tmp_path / "store" / TOY, {})
    stage = opened(out / f"{TOY}.usda")
    for name in ("near", "far"):
        prim = stage.GetPrimAtPath(f"/{TOY}/Outside/{name}")
        bound = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
        assert bound.GetPath() == f"/{TOY}/Library/lunar_regolith" and not prim.HasAttribute("score:surface:missing")
    water = stage.GetPrimAtPath(f"/{TOY}/Outside/water")
    assert not UsdShade.MaterialBindingAPI(water).ComputeBoundMaterial()[0]
    assert water.GetAttribute("score:surface:missing").Get()
    faults = [fault["prim"] for fault in placeholders.check(out / f"{TOY}.usda")]
    assert faults == [f"/{TOY}/Outside/water"], faults


def test_a_room_s_made_ground_takes_the_surface_of_the_scene_holding_its_row(tmp_path, monkeypatch):
    """Airlock (#36): a room the base holds stands on the base's made ground, its row base's lunar_surface, which the
    room's own inventory and surface library lack, so it stayed drawn with no material. The assembly reads beside the
    surface library of the scene holding the row (ground_scenes: the base, its ground's top scene; none for the base
    itself), lays that library's surface under the room's own Library (it has none of that name) and binds the
    ground to it, so the placeholder gate passes. The flat's ground is the square's plaza, a made ground the
    square's library was asked no kind for: it takes that library's floor, the ground people walk on; a natural
    ground the library names no kind for takes none.
    Break: score/stages/assembly/ground_finish.py: `found |= set(next(([top] for top in sorted(ground["tops"])` ->
        `found |= set(next(([top] for top in []`
    Break: score/stages/assembly/ground_finish.py: `lay_surface(stage, place, surface, library)` -> `None`
    Break: score/stages/assembly/ground_finish.py: `return palette_library.shell_surface("deck", library) if made else
        None` -> `return None`"""
    square = {"kinds": {"floor": ["plaza_floor_tiles"], "sea": ["bay_water"]}}
    assert assembly.ground_surface({"id": "plaza", "name": "main plaza", "noun": "plaza"}, square) == \
        "plaza_floor_tiles"
    assert assembly.ground_surface({"id": "sea", "name": "sea", "noun": "sea"}, square) == "bay_water"
    assert assembly.ground_surface({"id": "dunes", "name": "red dunes", "noun": "dunes"}, square) is None
    from pxr import Usd, UsdShade
    from score.stages import design_layers
    from score.stages.terrain import outside
    import placeholders
    design = tmp_path / "home/design"
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
    (design / f"inventory/{TOY}.json").write_text(json.dumps({"rows": [{"id": "hatch", "noun": "hatch"}]}))
    monkeypatch.setattr(design_layers, "KEPT", design / "inventory")
    assert assembly.ground_scenes(TOY) == ["base"] and assembly.ground_scenes("base") == []
    read_only_toy(tmp_path / "store" / TOY)
    inputs = a_record(tmp_path, ONE_LAMP)
    (tmp_path / "terrain/moon/places").mkdir(parents=True)
    ground = Usd.Stage.CreateNew(str(tmp_path / "terrain/moon/places" / f"{TOY}.usdc"))
    points, triangles = np.array([[0, 0, 0], [1, 0, 0], [0, 0, 1]], float), np.array([[0, 2, 1]])
    outside.write(ground, TOY, {"near": (points, triangles)}, "lunar_surface", ["regolith", "the test's"])
    ground.GetRootLayer().Save()
    (tmp_path / "base-library").mkdir()
    (tmp_path / "base-library/materials.json").write_text(json.dumps({
        "recipes": {"regolith": {"roughness": 0.95}}, "tokens": {"regolith-tan": "#8a7350"},
        "families": {"regolith": {"variants": {"lunar_regolith": {"recipe": "regolith", "token": "regolith-tan"}}}},
        "kinds": {"ground": ["lunar_regolith"]}}))
    (tmp_path / "surfaces.json").write_text(json.dumps({}))
    out = tmp_path / "out"
    out.mkdir()
    assembly.make_from_seed({"seed": tmp_path / "store" / TOY, "surfaces": tmp_path / "surfaces.json",
                             "inventories": design / "inventory", "surface-library@base": tmp_path / "base-library",
                             **inputs}, out, tmp_path / "store" / TOY, {})
    stage = opened(out / f"{TOY}.usda")
    near = stage.GetPrimAtPath(f"/{TOY}/Outside/near")
    bound = UsdShade.MaterialBindingAPI(near).ComputeBoundMaterial()[0]
    assert bound.GetPath() == f"/{TOY}/Library/lunar_regolith", bound
    assert bound.GetPrim().GetAttribute("score:recipe").Get() == "regolith"
    assert placeholders.check(out / f"{TOY}.usda") == []


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
    Break: score/stages/assembly/even_feet.py: `if foot - lowest > triage.TOLERANCE and not` -> `if False and not`
    Break: score/stages/assembly/even_feet.py: `or os.stat(path).st_nlink != 1` -> `` (a write through a link)
    Break: score/stages/assembly/even_feet.py: `and not said("score:fixed")` -> ``
    Break: score/stages/assembly/grounded.py: `even_feet.evened(folder, place)` -> `pass`
    Break: score/stages/assembly/big_bases.py: levelled's `stood = footing.cut_at(points, cut) if cut else ...` ->
        `stood = np.asarray(points, dtype=np.float64)` (the hub left on its post's foot, the tower on its slope)
    Break: score/stages/assembly/big_bases.py: upright's `stood = (points - middle) @ turn.T` -> `stood = points -
        middle` (the beam left leaning)
    Break: score/stages/assembly/big_bases.py: deep_cut's `deepest = DEEP * float(np.ptp(points[:, 1]))` -> `deepest
        = 9.0` (the 4 m post cut level), or levelled's `stood, sole = sole_cut(stood, triangles)` -> `sole = []` (the
        hall left on its corners), or sole_cut's `SOLE * float(np.ptp(points[:, 1]))` -> `1.0` (the shed cut level)
    Break: score/stages/assembly/big_bases.py: outlines's within `return any(...)` -> `return True` (the foot beside
        the sole read inside it)
    Break: score/stages/assembly/footing.py: cut_at's `points[points[:, 1] <= lowest + cut, 1] = lowest` dropped (the
        hub's legs left 0.15 m up)
    Break: score/stages/assembly/even_feet.py: `laid_flat.flattened(stage, folder, place)` -> `pass` (the slab left
        standing), or laid_flat's `if axis is None or footing.stands(...)` -> `if axis is None` (the board laid down),
        or clear_side's `if all(not meets(...))` -> `if True` (the slab laid down into the crate)
    Break: score/stages/assembly/grounded.py: `on_ground.stood(folder, seed.name)` -> `pass`
    Break: score/stages/assembly/on_ground.py: `if record.get("inside") or not` -> `if not`, `if over_deck(pivot,
        decks):` -> `if False:`, `and at_floor(entry)` -> `` (square's podium let down off its stage), `for one in
        (name, *held):` -> `for one in (name,):`, `turn = turn_onto(up, normal)` -> `turn = np.eye(4)`, `if leans <=
        LEAN_MOST and abs(` -> `if False and abs(`, or `laid_path.write_text(json.dumps(laid, indent=1))` -> `pass`"""
    from pxr import Sdf
    from score.stages.assembly import grounded, made_waiting, on_ground, parting
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
    read_only_toy(tmp_path / "store" / TOY)
    parted, stood = [], []
    monkeypatch.setattr(parting, "parted", lambda folder, place: parted.append((folder, place)) or [])
    restore = on_ground.stood
    monkeypatch.setattr(on_ground, "stood", lambda folder, place: stood.append((folder, place)) or [])
    root = grounded.grounded_seed({"seed": tmp_path / "store" / TOY, **a_record(tmp_path, ONE_LAMP)},
                                  tmp_path / "settle")
    stage = opened(root)
    assert stage.GetPrimAtPath(f"/{TOY}/Lights/light_1") and (root.parent / "assets").is_dir()
    assert parted == [(tmp_path / "settle", TOY)], parted  # parted as the assembly's make parts (wired.make)
    assert stood == [(tmp_path / "settle", TOY)], stood  # on its made ground, as the assembly's make stands them
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


def test_a_place_needs_the_layers_its_design_shows():
    """The person needs its characters layer, the kettle its effects, the door its motion, the plants on the planter
    their crops; no loose row, so no settle; light and sound always. A bare room needs light and sound only, and a
    crate on the floor its settle.
    Break: score/stages/assembly/__init__.py: `"physics": "settle", ` -> ``"""
    assert assembly.needed_layers(DESIGN, KINDS) == ["characters-layer", "crops-layer", "effects-layer", "motion",
                                                     "light", "sound"]
    bare = {"rows": [{"id": "wall", "noun": "wall", "kind": "code", "anchor": "floor"}]}
    assert assembly.needed_layers(bare, KINDS) == ["light", "sound"]
    crate = {"id": "crate", "noun": "crate", "kind": "generate", "anchor": "floor"}
    assert assembly.needed_layers({"rows": [*bare["rows"], crate]}, KINDS) == ["settle", "light", "sound"]


def test_a_place_waits_on_every_layer_it_needs(tmp_path):
    """The layers gate: unknown while a layer the design needs has no accepted output taken (the person's and the
    plants' here), naming each; pass once all are; fail on a sound placed nowhere; unknown for a place with no design.
    Break: score/stages/assembly/__init__.py: `waiting = [f"{name}@{place}" for name in needed if name not in
        origin["layers"]]` -> `waiting = []`
    Break: score/stages/assembly/__init__.py: `if origin["unplaced sounds"]:` -> `if False:`"""
    output = tmp_path
    (output / f"{TOY}.usda").write_text("#usda 1.0\n")
    (output / "design.json").write_text(json.dumps(DESIGN))
    (output / "row-kinds.json").write_text(json.dumps({"kinds": KINDS}))
    designed = {"design": output / "design.json", "row kinds": output / "row-kinds.json"}

    def judged(layers, unplaced=(), inputs=designed):
        (output / "origin.json").write_text(json.dumps({"layers": dict.fromkeys(layers, "x"), "record": "r",
                                                        "unplaced sounds": list(unplaced)}))
        return assembly.judge_layers(output, inputs, None)

    every = ["characters-layer", "crops-layer", "effects-layer", "motion", "light", "sound"]
    waiting = judged(["sound", "effects-layer", "motion", "light"])
    assert waiting.answer == checks.UNKNOWN and waiting.findings == (f"characters-layer@{TOY}",
                                                                     f"crops-layer@{TOY}"), waiting
    assert judged(every).answer == checks.PASS
    assert judged(every, ["hum"]).answer == checks.FAIL
    assert judged(every, inputs={"row kinds": output / "row-kinds.json"}).answer == checks.UNKNOWN


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


def judged(output):
    return neighbours.judge_neighbours(output, {}, None)


def test_a_place_shows_its_neighbours_from_their_own_outputs(tmp_path, monkeypatch):
    """Fault (2026-10-12): the launch's assembly showed Places/square and Places/far_city with no children, its
    references pointing at round-three seed files the store does not hold. Away from its neighbours the launch fails
    on both shown places (no file, no children: four faults); made, each stands from its own copied output after the
    originals are gone. A shown place no stage makes is a gap, and a part of another scene's outside (the launch,
    data/places/within.json) is no neighbour.
    Break: score/stages/assembly/neighbours.py: `layer.UpdateCompositionAssetDependency(f"../../{other}/{other}.usda",
        f"../{PLACES}/{other}/{other}.usda")` -> `pass`
    Break: score/stages/assembly/neighbours.py: `if scene_record.written(other) and other not in parts()]` -> `if
        scene_record.written(other)]`"""
    records = {"launch": {"places": [{"name": "square", "stage": "square"}, {"name": "far_city", "stage": "far_city"}]},
               "square": {"places": [{"name": "launch", "stage": "launch"}]}}
    assert neighbours.record_of("nowhere") == {}
    with monkeypatch.context() as patched:
        patched.setattr(neighbours, "record_of", lambda place: records.get(place, {}))
        patched.setattr(neighbours.scene_record, "written", lambda place: place in ("square", "launch"))
        assert neighbours.shown("launch") == ["far_city", "square"] and neighbours.neighbours("launch") == ["square"]
        assert neighbours.lost("launch") == ["far_city"] and neighbours.files("launch") == {}
        assert neighbours.applies("square") and not neighbours.applies("nowhere")
        assert neighbours.neighbours("square") == [], "the launch is a part of an outside, no place of the build"
    launch = a_place(tmp_path / "kept", "launch", ("square", "wreck"))
    shows(launch, "square", "wreck")
    inputs = {"assembly@square": a_place(tmp_path / "kept", "square"),
              "assembly@wreck": a_place(tmp_path / "kept", "wreck")}
    shutil.move(str(launch), tmp_path / "alone")  # away from its neighbours, as the store keeps it
    alone = judged(tmp_path / "alone")
    assert alone.answer == checks.FAIL and alone.measures["faults"] == 4, alone
    assert any("resolves to no file" in finding for finding in alone.findings), alone.findings
    out = tmp_path / "out"
    out.mkdir()
    neighbours.make({**inputs, "assembly": tmp_path / "alone"}, out, 0, {})
    shutil.rmtree(tmp_path / "kept")
    verdict = judged(out)
    assert verdict.answer == checks.PASS and verdict.measures["shown"] == 2, verdict


def test_a_lost_shown_place_is_the_place_s_gap_and_any_other_fault_still_fails(tmp_path):
    """No stage makes the far city: the make stands the rest and names it a gap (gaps.json), and the gate moves only
    its faults to the completion gate; a fault no gap names (the square's copy removed) still fails.
    Break: score/stages/assembly/neighbours.py: `left.append(lost_gap(stage_file(out).stem, other))` -> `pass`"""
    launch = a_place(tmp_path / "kept", "launch", ("square", "far_city"))
    shows(launch, "square", "far_city")
    out = tmp_path / "out"
    out.mkdir()
    neighbours.make({"assembly": launch, "assembly@square": a_place(tmp_path / "kept", "square")}, out, 0, {})
    found = json.loads((out / neighbours.GAPS).read_text())["gaps"]
    assert [entry["objects"] for entry in found] == [["/launch/Places/far_city"]], found
    verdict = judged(out)
    assert verdict.answer == checks.PASS and "far_city: shown by the plan" in verdict.reason, verdict
    assert verdict.findings and all(finding.startswith("/launch/Places/far_city") for finding in verdict.findings)
    shutil.rmtree(out / "places" / "square")
    assert judged(out).answer == checks.FAIL


def test_a_shown_place_the_terrain_added_points_at_its_copy(tmp_path):
    """Fault (2026-10-15): the stairwell's Places/flat, which its seed lacks and the terrain's ground layer adds, kept
    its reference ../../flat/flat.usda: only the base layer's references were pointed at the copies.
    Break: score/stages/assembly/neighbours.py: `glob("*.usd*")` -> `glob("*.usda")`"""
    stairwell = a_place(tmp_path / "kept", "stairwell", ("street",), ("flat",))
    shows(stairwell, "street", "flat")
    inputs = {"assembly": stairwell, "assembly@street": a_place(tmp_path / "kept", "street"),
              "assembly@flat": a_place(tmp_path / "kept", "flat", ("stairwell",))}
    out = tmp_path / "out"
    out.mkdir()
    neighbours.make(inputs, out, 0, {})
    shutil.rmtree(tmp_path / "kept")
    verdict = judged(out)
    assert verdict.answer == checks.PASS and verdict.measures["shown"] == 2, verdict


def test_a_place_with_its_own_ground_shows_its_neighbours_without_theirs(tmp_path):
    """Fault (2026-10-18): the old station's film looked through a flat grey slab, the shown places' own made grounds:
    the seed's way fails on both (two faults, each its own ground); made, both are left out and its own stays.
    Break: score/stages/assembly/neighbours.py: `if owns:` -> `if False:`"""
    station = a_place(tmp_path / "kept", "old_station", ("wreck",), ("garage",))
    shows(station, "wreck", "garage")
    inputs = {"assembly": station, "assembly@wreck": a_place(tmp_path / "kept", "wreck"),
              "assembly@garage": a_place(tmp_path / "kept", "garage")}
    out = tmp_path / "out"
    out.mkdir()
    neighbours.make(inputs, out, 0, {})
    shutil.copytree(inputs["assembly"], tmp_path / "before")  # the seed's way, as it stood before
    for other in ("wreck", "garage"):
        shutil.copytree(inputs[f"assembly@{other}"], tmp_path / other)
    before = judged(tmp_path / "before")
    assert before.answer == checks.FAIL and before.measures["faults"] == 2, before
    assert all("its own ground" in finding for finding in before.findings), before.findings
    verdict = judged(out)
    assert verdict.answer == checks.PASS and verdict.measures["shown"] == 2, verdict
    stage = opened(out / "old_station.usda")
    assert stage.GetPrimAtPath("/old_station/Outside/near").IsActive()
    assert not stage.GetPrimAtPath("/old_station/Places/wreck/Outside").IsActive()


def test_a_room_with_no_ground_of_its_own_keeps_its_neighbours_grounds(tmp_path):
    """The airlock has no made ground of its own: through its doors the ground is the one its shown garage draws, so
    it stays.
    Break: score/stages/assembly/neighbours.py: `owns = has_own_ground(layers, place)` -> `owns = True`"""
    from pxr import Sdf, Usd
    airlock = a_place(tmp_path / "kept", "airlock", ("garage",))
    layer = Sdf.Layer.FindOrOpen(str(airlock / "layers" / "ground.usdc"))
    Usd.Stage.Open(layer).RemovePrim("/airlock/Outside")
    layer.Save()
    shows(airlock, "garage")
    out = tmp_path / "out"
    out.mkdir()
    neighbours.make({"assembly": airlock, "assembly@garage": a_place(tmp_path / "kept", "garage")}, out, 0, {})
    assert judged(out).answer == checks.PASS
    assert opened(out / "airlock.usda").GetPrimAtPath("/airlock/Places/garage/Outside").IsActive()


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


def the_yard(root, hut_plan=HUT, children=("shed", "hut"), shed_plan=SHED):
    """The yard's tree over the shed's tree (holding the nook's) and the hut's."""
    nook, _ = tree_of(root, "nook", a_scene(root / "made", "nook", (0.0, 0.0, 0.0)), NOOK, {})
    shed, _ = tree_of(root, "shed", a_scene(root / "made", "shed", (6.0, 0.0, -1.0)), shed_plan,
                      {"nook": (nook, NOOK)})
    hut, _ = tree_of(root, "hut", a_scene(root / "made", "hut", (-1.0, 0.0, 2.0)), hut_plan, {})
    trees = {"shed": (shed, shed_plan), "hut": (hut, hut_plan)}
    return tree_of(root, "yard", a_scene(root / "made", "yard", (0.0, 0.0, 0.0)), YARD,
                   {child: trees[child] for child in children})


def test_opening_the_yard_opens_the_whole_tree_each_child_at_its_hold(tmp_path):
    """The shed's crate at (6, 0, -1) of its frame is plan (1, 1) on the shed, (3, 4) on the yard: (-7, 0, -2). The
    nook's crate at its middle is plan (1, 0.5) on the nook, (2, 1.5) on the shed, (4, 4.5) on the yard: (-6, 0, -1.5).
    The hut's crate at (-1, 0, 2) is plan (2, 1) on the turned hut, (12, 6) on the yard: (2, 0, 0). The gate passes
    and a scene holding none says so. A shed door to the hut 2.5 m up, the hut's door back on its floor, stands the
    hut 2.5 m up (the square's flat under its stairwell door, 2026-11-04), and the gate holds it there.
    Break: score/stages/assembly/scene_tree.py: `matrix[:3, :3] = turn.T` -> `matrix[:3, :3] = turn`
    Break: score/stages/assembly/scene_tree.py:
        `shift = corner + east * start[0] + south * start[1] + up * level - turn @ child_corner`
        -> `shift = corner + east * start[0] + south * start[1] + up * level`
    Break: score/stages/assembly/scene_tree.py: `+ up * level` -> ``
    The yard holding the hut twice (#72: a place held several times stands once a hold), its second instance turned 90 degrees
    at (2, 7) 3 x 4 m: its crate at plan (2, 1) of the hut is (4, 9) on the yard, (-6, 0, 3), under /yard/Scenes/hut_2,
    the hut's one tree copied once; the gate passes it.
    A third instance turned 45 degrees (#72: the base's tubes off the hub's diagonal facets) in its 4.95 m box at (14, 0):
    its crate at plan (2, 1) is (16.83, 2.12) on the yard, (6.83, 0, -3.88).
    Break: score/stages/scene_record/plan.py: `return round(math.cos(turn), 12), round(math.sin(turn), 12)` ->
        `return round(math.cos(turn)), round(math.sin(turn))`
    Break: score/stages/assembly/scene_tree.py: `standing = sorted(child for child, hold in laid.items() if hold["place"] in children)` ->
        `standing = sorted(child for child in laid if child in children)`"""
    yard, inputs = the_yard(tmp_path)
    stage = opened(yard / "yard.usda")
    assert crate_at(stage, "/yard/Scenes/shed/Objects/crate_1") == [-7.0, 0.0, -2.0]
    assert crate_at(stage, "/yard/Scenes/shed/Scenes/nook/Objects/crate_1") == [-6.0, 0.0, -1.5]
    assert crate_at(stage, "/yard/Scenes/hut/Objects/crate_1") == [2.0, 0.0, 0.0]
    assert crate_at(stage, "/yard/Objects/crate_1") == [0.0, 0.0, 0.0]
    verdict = scene_tree.judge_children(yard, inputs, None)
    assert verdict.answer == checks.PASS and verdict.measures["children"] == 2, verdict.findings
    nook = scene_tree.judge_children(tmp_path / "trees/nook", {"plan": tmp_path / "plans/nook.json"}, None)
    assert nook.answer == checks.PASS and nook.reason == "its plan lays out no child scene"
    door = {"kind": "door", "wide": 1.0, "sill": 0.0}
    raised, inputs = the_yard(tmp_path / "raised", {**HUT, "openings": [{**door, "at": [0.0, 1.5], "to": "shed"}]},
                              shed_plan={**SHED, "openings": [{**door, "at": [4.0, 1.5], "sill": 2.5, "to": "hut"}]})
    stage = opened(raised / "yard.usda")
    assert crate_at(stage, "/yard/Scenes/hut/Objects/crate_1") == [2.0, 2.5, 0.0]
    assert crate_at(stage, "/yard/Scenes/shed/Objects/crate_1") == [-7.0, 0.0, -2.0]
    verdict = scene_tree.judge_children(raised, inputs, None)
    assert verdict.answer == checks.PASS, verdict.findings
    twice = {**YARD, "holds": [{**YARD["holds"][1], "instance": "hut#1"},
                               {"place": "hut", "instance": "hut#2", "turn": 90, "x": 2.0, "y": 7.0, "w": 3.0, "d": 4.0},
                               {"place": "hut", "instance": "hut#3", "turn": 45, "x": 14.0, "y": 0.0, "w": 4.949747,
                                "d": 4.949747}]}
    root = tmp_path / "twice"
    hut, _ = tree_of(root, "hut", a_scene(root / "made", "hut", (-1.0, 0.0, 2.0)), HUT, {})
    yard, inputs = tree_of(root, "yard", a_scene(root / "made", "yard", (0.0, 0.0, 0.0)), twice, {"hut": (hut, HUT)})
    stage = opened(yard / "yard.usda")
    assert crate_at(stage, "/yard/Scenes/hut_1/Objects/crate_1") == [2.0, 0.0, 0.0]
    assert crate_at(stage, "/yard/Scenes/hut_2/Objects/crate_1") == [-6.0, 0.0, 3.0]
    assert crate_at(stage, "/yard/Scenes/hut_3/Objects/crate_1") == [6.8284, 0.0, -3.8787]
    assert sorted(path.name for path in (yard / "scenes").iterdir()) == ["hut"]
    verdict = scene_tree.judge_children(yard, inputs, None)
    assert verdict.answer == checks.PASS and verdict.measures["children"] == 3, verdict.findings


def test_a_child_laid_out_and_not_stood_fails_by_name(tmp_path):
    """The yard's plan lays out the hut; a run with no hut read stands the shed alone and fails on the hut.
    Break: score/stages/assembly/scene_tree.py: `children = sorted(set(laid) | read | standing)` -> `children =
        sorted(read | standing)`"""
    yard, inputs = the_yard(tmp_path, children=("shed",))
    verdict = scene_tree.judge_children(yard, inputs, None)
    assert verdict.answer == checks.FAIL
    assert verdict.findings == ("/yard/Scenes/hut: laid out on yard's plan, not in the stage (no scene of the "
                                "batch: its design is not done)",)


def test_a_child_whose_plan_is_not_its_hold_s_size_fails(tmp_path):
    """A hut planned 5 m wide in a 4 m hold fails on its size.
    Break: score/stages/assembly/scene_tree.py: `if abs(wide - hold["w"]) > SIZED` -> `if False`"""
    yard, inputs = the_yard(tmp_path, hut_plan={**HUT, "w": 5.0})
    verdict = scene_tree.judge_children(yard, inputs, None)
    assert verdict.answer == checks.FAIL
    assert "/yard/Scenes/hut: its plan laid in its hold is 5 x 3 m, its hold 4.0 x 3.0 m" in verdict.findings


def test_a_child_standing_where_the_plan_lays_out_nothing_fails(tmp_path):
    """The yard's plan edited to hold the shed only, its tree still standing the hut: the hut fails by name.
    Break: score/stages/assembly/scene_tree.py: `return [f"/{scene}/{SCENES}/{child}: read as a child scene, laid out
        nowhere on {scene}'s plan"]` -> `return []`"""
    yard, inputs = the_yard(tmp_path)
    inputs["plan"].write_text(json.dumps({**YARD, "holds": YARD["holds"][:1]}))
    verdict = scene_tree.judge_children(yard, inputs, None)
    assert verdict.findings == ("/yard/Scenes/hut: read as a child scene, laid out nowhere on yard's plan",)


def test_a_scene_with_no_plan_read_is_unknown_not_passed(tmp_path):
    """The yard's tree made with no plan read stands no child, and what it should hold cannot be told: unknown.
    Break: score/stages/assembly/scene_tree.py: `if plan is None:` -> `if False:`"""
    yard, inputs = tree_of(tmp_path, "yard", a_scene(tmp_path / "made", "yard", (0.0, 0.0, 0.0)), None, {})
    verdict = scene_tree.judge_children(yard, inputs, None)
    assert verdict.answer == checks.UNKNOWN
    assert verdict.reason == "no plan of yard read: which child scenes it holds cannot be told"


def test_the_plans_read_are_the_creator_s_kept_ones_and_a_scene_holding_itself_is_refused(tmp_path, monkeypatch):
    """The plan read is the creator's kept one, none without it; each child's plan is declared; a plan laying out a
    scene above it (the nook holding the yard) is refused.
    Break: score/stages/assembly/scene_tree.py: `if above:` -> `if False:`
    Break: score/stages/assembly/scene_tree.py: `named.update({f"plan {child}": plan_pattern(child) for child in
        held(place)})` -> `pass`"""
    monkeypatch.setattr(scene_tree, "KEPT", tmp_path)
    for scene, plan in (("yard", YARD), ("shed", SHED), ("hut", HUT), ("nook", NOOK)):
        (tmp_path / f"{scene}.json").write_text(json.dumps(plan))
    assert scene_tree.files("yard") == {"plan": "{home}/design/plans/yard.json",
                                        "plan hut": "{home}/design/plans/hut.json",
                                        "plan shed": "{home}/design/plans/shed.json"}
    assert scene_tree.files("nook") == {"plan": "{home}/design/plans/nook.json"}
    (tmp_path / "nook.json").unlink()
    assert scene_tree.plan_path("nook") is None and scene_tree.held("shed") == ["nook"]
    (tmp_path / "nook.json").write_text(json.dumps({**NOOK, "holds": [{"place": "yard"}]}))
    with pytest.raises(ValueError, match="cannot hold itself"):
        scene_tree.held("yard")
