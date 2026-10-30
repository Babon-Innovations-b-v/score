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
from score.stages.assembly import baked, made_waiting, neighbours, record, scene_tree, sounds  # noqa: E402

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
    return assembly.judge_resting(output, inputs, evidence)


def test_the_resting_gate_judges_the_world_files_the_stage_declares(tmp_path):
    """Fault (review of step 0, 2026-10-11): the judge read the repository's resting.json, so a world whose rules were
    elsewhere was judged on files its key did not cover. The sunk plate passes where the world's rules name its kit
    group, fails by name where they name none, and a seed naming no inventory in the folder is unknown.
    Break: score/stages/assembly/__init__.py: `rules_file=inputs["resting rules"]` -> `rules_file=REPO /
        "data/checks/resting.json"`"""
    output, place = a_sunk_plate(tmp_path)
    kit_floor = world_data(tmp_path / "kept", place, ["kit: floor"])
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
    kind (settling.held.mounted), so it judges them by touching; a row on a floor or an object, or naming its own
    support, keeps what the triage gives it.
    Break: score/stages/assembly/__init__.py: `if row["id"] in on_walls and not row.get("support")` -> `if False`"""
    inventory = {"rows": [{"id": "left_wall", "part": "wall"}, {"id": "ceiling_panels", "part": "roof"},
                          {"id": "floor_plates", "part": "floor"}, {"id": "locker", "part": "object"},
                          {"id": "wall_pipes", "anchor": "on:left_wall"},
                          {"id": "ceiling_rails", "anchor": "on:ceiling_panels"},
                          {"id": "fixed_pipe", "anchor": "on:left_wall", "support": "fixed"},
                          {"id": "crate", "anchor": "on:floor_plates"}, {"id": "suit", "anchor": "on:locker"}]}
    found = {row["id"]: row.get("support") for row in assembly.resting_rows(inventory)["rows"]}
    assert found == {"left_wall": None, "ceiling_panels": None, "floor_plates": None, "locker": None,
                     "wall_pipes": "wall", "ceiling_rails": "ceiling", "fixed_pipe": "fixed", "crate": None,
                     "suit": None}, found


def test_a_row_the_record_hangs_within_its_holder_is_judged_hanging():
    """Round 32's docking airlock: its spacesuits, laid within their lockers at the plan's 0.1 m base, were judged as
    standing on the lockers' insides and leaned 12 degrees. A row whose every object the scene record lays within its
    holder off the holder's foot is given `hanging` (judged by touching: one touching nothing still hangs free); one
    within at its holder's foot, one of a row with another object laid otherwise, or a row naming its own support,
    keeps what the triage gives it.
    Break: score/stages/assembly/__init__.py: `float(entry["at"][1]) > float(holder["at"][1])` -> `True`
    Break: score/stages/assembly/__init__.py: `if all(hung)}` -> `if any(hung)}`"""
    inventory = {"rows": [{"id": "locker", "part": "object"}, {"id": "suit", "anchor": "on:locker"},
                          {"id": "crate", "anchor": "on:locker"}, {"id": "box", "anchor": "on:locker"},
                          {"id": "fixed_suit", "anchor": "on:locker", "support": "fixed"}]}

    def laid(name, row, height, how=None):
        return {"name": name, "row": row, "at": [0.0, height, 0.0],
                **({"on": {"how": how, "holder": ["locker_1"]}} if how else {})}
    record = {"objects": [laid("locker_1", "locker", 0.0), laid("suit_1", "suit", 0.1, "within"),
                          laid("suit_2", "suit", 0.1, "within"), laid("crate_1", "crate", 0.0, "within"),
                          laid("box_1", "box", 0.1, "within"), laid("box_2", "box", 0.1, "face"),
                          laid("fixed_suit_1", "fixed_suit", 0.1, "within")]}
    found = {row["id"]: row.get("support") for row in assembly.resting_rows(inventory, record)["rows"]}
    assert found == {"locker": None, "suit": "hanging", "crate": None, "box": None, "fixed_suit": "fixed"}, found


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
        boxes] if on["how"] != "in" else walls` -> `... else []`"""
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


def test_the_held_gate_names_each_object_not_where_what_holds_it_puts_it():
    """#72, so it never comes back silently: the `held` gate fails by name on a door laid 1 m beside its module's
    face (its measure 1.0 m), a door or window in no opening and on no holder, one held by nothing and one left at the
    room's middle, and a 6 m door on a 6 m face with 0.55 m of recess room beside it (0.55 m too narrow); the door
    laid on the face passes.
    Break: score/stages/assembly/fitting.py: `if narrow > HELD_MOST:` -> `if False:`
    Break: score/stages/assembly/fitting.py: `elif distance > HELD_MOST:` -> `elif False:`
    Break: score/stages/assembly/fitting.py: `if entry.get("fills") and not (on and on["how"] in ("in", "face",
        "within", "top")):` -> `if False:`"""
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
    bundle across a 0.14 m wall 0.34 m past the wall's near side (tube's, 2026-10-30), never more than 1 m (a ship
    2.5 m from clear of a wall is left as laid, and named); a lamp in the
    roof's box, a crate in a slanted wall's 5 m box and a stair reaching into its loft deck are left (a roof's and a
    slanted wall's box hold the room, a stair climbs into its level). The held gate
    fails one left inside a deck by name and its depth, never a door the record lays in its opening.
    Break: score/stages/assembly/fitting.py: `return pivot, np.cross(way, [0.0, 1.0, 0.0]),` -> `return pivot,
        np.cross([0.0, 1.0, 0.0], way),`
    Break: score/stages/assembly/fitting.py: `return fits + moved_out(stage, place, [entry` -> `return fits + ([entry`
    Break: score/stages/assembly/fitting.py: `and not climbs(entry)])` (moved_out's) -> `])`
    Break: score/stages/assembly/fitting.py: `moves = np.where(ahead <= back, ahead, -back)` -> `moves = ahead`
    Break: score/stages/assembly/fitting.py: `return [(name, box) for name, box in built if name.split("_")[0] in
        STATICS]` -> `return built`
    Break: score/stages/assembly/fitting.py: `if not held_in(on) and not climbs(entry):` -> `if True:`
    Break: score/stages/assembly/fitting.py: `back[1] = np.inf` -> `pass`
    Break: score/stages/assembly/fitting.py: `if not left or moved > OUT_MOST:` -> `if not left:`
    Break: score/stages/assembly/fitting.py: `<= WALL_THICKEST)]` -> `<= 99.0)]`
    Break: score/stages/assembly/fitting.py: `if depths(low, high, box).min() > HELD_MOST]` -> `if False]`"""
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
                            ("cable_bundles_1", (29.8, 0.0, 31.0), (34.0, 2.0, 31.5)),
                            ("spaceship_1", (27.0, 0.0, 30.5), (33.0, 2.0, 32.5))):
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
    ship = fitting.world_box(stage, f"/{TOY}/Objects/spaceship_1")
    assert np.allclose(ship[0], (27.0, 0.0, 30.5)), ship  # 2.5 m from clear of the wall: left as laid, named
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


def test_a_tunnel_against_its_wall_passes_into_it_and_a_pipe_does_not():
    """held@garage, @habitat, @workshop (2026-10-30): a glass tunnel or corridor tube the concept shows meeting its
    module's wall from outside, laid against that wall, reached 0.09 to 0.30 m into the built wall; it joins the place
    through it, as a door stands in its opening, so the held gate excuses its wall, never a deck. A pipe laid against
    the same wall that reaches into it is still named.
    Break: score/stages/assembly/fitting.py: `if not (passes(entry) and static.split("_")[0] == "wall")]` -> `]`
    Break: score/stages/assembly/fitting.py: `set(str(entry.get("row") or "").split("_")) & set(PASSING))` ->
        `set(str(entry.get("row") or "").split("_")) & set(CLIMBING))`"""
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


def test_a_door_goes_in_its_opening_narrowed_to_fit():
    """A 1.4 x 0.1 x 2.4 m door laid off its wall goes in its 1.2 m wide, 2.1 m tall opening: shrunk to 1.2 / 1.4,
    its foot's middle on the opening's middle at its sill.
    Break: score/stages/assembly/fitting.py: `scale = min(1.0, float(on["wide"]) / max(across(on["along"], size),
        1e-9), float(on["tall"]) / size[1])` -> `scale = 1.0`"""
    from score.stages.assembly import fitting
    opening = {"how": "in", "middle": [5.0, 0.0, 0.0], "along": [1.0, 0.0], "wide": 1.2, "tall": 2.1}
    scale, target, words, _ = fitting.fit((0.3, 0.0, 2.95), (1.7, 2.4, 3.05), opening)
    assert abs(scale - 1.2 / 1.4) < 1e-9 and np.allclose(target, (5.0, 0.0, 0.0)), (scale, target)
    assert "shrunk to 86%" in words, words


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
        `for name in by_name:`"""
    from pxr import Gf, Usd, UsdGeom
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
                                 ("Objects/door_1", (1.0, 2.0, 0.1), 180.0, (0.0, 1.0, 3.0)),
                                 ("Shell/wall_2", (1.2, 0.1, 0.2), 0.0, (0.0, -0.05, 0.0))):
        xform = UsdGeom.Xform.Define(stage, f"/{TOY}/{name}")
        cube = UsdGeom.Cube.Define(stage, f"/{TOY}/{name}/geo")
        cube.AddScaleOp().Set(Gf.Vec3f(*(side / 2 for side in size)))
        xform.AddTransformOp().Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), turn))
                                   * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*at)))
    wall = {"how": "wall", "span": [[-3.0, 0.1], [3.0, 0.1]], "out": [0.0, 1.0]}
    entries = [{"name": "pipe_1", "row": "pipe", "on": wall}, {"name": "lamp_1", "row": "lamp", "on": wall},
               {"name": "door_1", "row": "door", "on": {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [1.0, 0.0],
                                                          "wide": 1.2, "tall": 2.2}}]
    fits = {fit["name"]: fit for fit in fitting.fitted(stage, TOY, entries, {"pipe_1", "lamp_1", "door_1"})}
    assert sorted(fits) == ["door_1", "pipe_1"], fits
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
        band[1])]`"""
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


def test_a_door_in_a_slanted_wall_hangs_on_the_face_it_swings_to():
    """#36, cockpit 2026-10-30: its rear doors, in an opening of a slanted wall (its boxes say nothing of its faces),
    stood on the plan's line 0.37 m in front of the built wall and swung their kind's way into its jamb. A 1 m opening
    at the origin along (0.6, 0.8), its built wall's jambs from 0.3 to 0.5 m across it the way (0.8, -0.6): a door
    turned so its own -z points that way (its kind's swing) stands with its foot middle on the far face, (0.4, -0.3);
    one swinging the other way on the near face, (0.24, -0.18); the held gate passes it there. A deck's corner 0.9 m
    out beside it is no wall face (camp's dome door, by no built wall, was hung on its deck's corner).
    Break: score/stages/assembly/fitting.py: `surface = wall_points(stage, place)` -> `surface = None`
    Break: score/stages/assembly/fitting.py: `if high[1] - low[1] >= 2 * WALL_REACH])` -> `])`
    Break: score/stages/assembly/fitting.py: `spot[[0, 2]] += way * float(across_off[near].max())` -> `spot[[0, 2]]
        += way * float(across_off[near].min())`
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
    xform = UsdGeom.Xform.Define(stage, f"/{TOY}/Objects/door_1")
    UsdGeom.Cube.Define(stage, f"/{TOY}/Objects/door_1/geo").AddScaleOp().Set(Gf.Vec3f(0.5, 1.0, 0.05))
    xform.AddTransformOp().Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), -53.130102))
                               * Gf.Matrix4d().SetTranslate(Gf.Vec3d(0.0, 1.0, 2.0)))
    opening = {"how": "in", "middle": [0.0, 0.0, 0.0], "along": [0.6, 0.8], "wide": 1.0, "tall": 2.0}
    fits = fitting.fitted(stage, TOY, [{"name": "door_1", "row": "door", "on": opening}], {"door_1"})
    middle = (np.array(fits[0]["low"]) + np.array(fits[0]["high"])) / 2
    assert np.allclose(middle[[0, 2]], (0.4, -0.3), atol=1e-3) and abs(fits[0]["low"][1]) < 1e-6, fits
    assert np.allclose(fitting.opening_spot(opening, opens=-normal, points=points), (0.24, 0.0, -0.18)), "near face"
    record = {"objects": [{"name": "door_1", "on": opening, "fills": True}]}
    assert fitting.held_faults(record, {"walls": [], "objects": [{"name": "door_1", "low": fits[0]["low"],
                                                                  "high": fits[0]["high"]}]}) == [], fits


def test_a_monitor_goes_on_its_console_s_top_within_its_span():
    """A 0.5 x 0.4 x 0.1 m monitor laid 2 m off its 3 x 1 x 0.8 m console (x 0 to 3, top at 1 m) stands on its top,
    moved in to x 3 - 0.25 = 2.75, z kept at 0.4, its foot at 1 m; a console narrower than it shrinks it to fit.
    Break: score/stages/assembly/fitting.py: `target[1] = hold_high[1] if how == "top" else` -> `target[1] = foot[1]
        if how == "top" else`"""
    from score.stages.assembly import fitting
    console = (np.array([0.0, 0.0, 0.0]), np.array([3.0, 1.0, 0.8]))
    on = {"how": "top", "holder": ["console_1"]}
    scale, target, _, _ = fitting.fit((4.5, 0.0, 0.35), (5.0, 0.4, 0.45), on, [console])
    assert scale == 1.0 and np.allclose(target, (2.75, 1.0, 0.4)), target
    narrow = (np.array([0.0, 0.0, 0.0]), np.array([0.4, 1.0, 0.8]))
    scale, target, _, _ = fitting.fit((4.5, 0.0, 0.35), (5.0, 0.4, 0.45), on, [narrow])
    assert abs(scale - 0.8) < 1e-9 and np.allclose(target, (0.2, 1.0, 0.4)), (scale, target)


def test_a_wall_item_stands_on_its_named_face():
    """A 1 x 0.6 x 0.2 m wall lamp laid at the room's middle (the walls item) stands with its back on its wall's face
    (z 0.1 to 6.1 at x 2, the room to +x), 0.1 m out from it, slid along to the face's nearest point.
    Break: score/stages/assembly/fitting.py: `spot = start + run * along + out * across(out, size) * scale / 2` ->
        `spot = start + run * along`"""
    from score.stages.assembly import fitting
    on = {"how": "wall", "span": [[2.0, 0.1], [2.0, 6.1]], "out": [1.0, 0.0]}
    scale, target, _, _ = fitting.fit((4.4, 0.0, 2.9), (4.6, 0.6, 3.9), on)
    assert scale == 1.0 and np.allclose(target, (2.1, 0.0, 3.4)), target


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


def test_the_settle_s_seed_is_laid_from_a_read_only_seed_with_no_assets_folder(tmp_path):
    """The settle's grounded seed of a store checkout (read-only, no assets/ folder: Batch 1, 2026-10-25, every
    settle) is laid with its record written over the copied base and an assets folder of its own.
    Break: score/stages/assembly/grounded.py: `(folder / "assets").mkdir()` -> `pass`"""
    from score.stages.assembly.grounded import grounded_seed
    read_only_toy(tmp_path / "store" / TOY)
    root = grounded_seed({"seed": tmp_path / "store" / TOY, **a_record(tmp_path, ONE_LAMP)}, tmp_path / "settle")
    stage = opened(root)
    assert stage.GetPrimAtPath(f"/{TOY}/Lights/light_1") and (root.parent / "assets").is_dir()


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


def the_yard(root, hut_plan=HUT, children=("shed", "hut")):
    """The yard's tree over the shed's tree (holding the nook's) and the hut's."""
    nook, _ = tree_of(root, "nook", a_scene(root / "made", "nook", (0.0, 0.0, 0.0)), NOOK, {})
    shed, _ = tree_of(root, "shed", a_scene(root / "made", "shed", (6.0, 0.0, -1.0)), SHED, {"nook": (nook, NOOK)})
    hut, _ = tree_of(root, "hut", a_scene(root / "made", "hut", (-1.0, 0.0, 2.0)), HUT, {})
    trees = {"shed": (shed, SHED), "hut": (hut, hut_plan)}
    return tree_of(root, "yard", a_scene(root / "made", "yard", (0.0, 0.0, 0.0)), YARD,
                   {child: trees[child] for child in children})


def test_opening_the_yard_opens_the_whole_tree_each_child_at_its_hold(tmp_path):
    """The shed's crate at (6, 0, -1) of its frame is plan (1, 1) on the shed, (3, 4) on the yard: (-7, 0, -2). The
    nook's crate at its middle is plan (1, 0.5) on the nook, (2, 1.5) on the shed, (4, 4.5) on the yard: (-6, 0, -1.5).
    The hut's crate at (-1, 0, 2) is plan (2, 1) on the turned hut, (12, 6) on the yard: (2, 0, 0). The gate passes
    and a scene holding none says so.
    Break: score/stages/assembly/scene_tree.py: `matrix[:3, :3] = turn.T` -> `matrix[:3, :3] = turn`
    Break: score/stages/assembly/scene_tree.py: `shift = corner + east * across + south * along - turn @ child_corner`
        -> `shift = corner + east * across + south * along`"""
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


def test_a_child_laid_out_and_not_stood_fails_by_name(tmp_path):
    """The yard's plan lays out the hut; a run with no hut read stands the shed alone and fails on the hut.
    Break: score/stages/assembly/scene_tree.py: `children = sorted(set(holds(plan)) | read | standing)` -> `children =
        sorted(read | standing)`"""
    yard, inputs = the_yard(tmp_path, children=("shed",))
    verdict = scene_tree.judge_children(yard, inputs, None)
    assert verdict.answer == checks.FAIL
    assert verdict.findings == ("/yard/Scenes/hut: laid out on yard's plan, not in the stage (no scene of the "
                                "batch: its design is not done)",)


def test_a_child_whose_plan_is_not_its_hold_s_size_fails(tmp_path):
    """A hut planned 5 m wide in a 4 m hold fails on its size.
    Break: score/stages/assembly/scene_tree.py: `if abs(child_plan["w"] - hold["w"]) > SIZED` -> `if False`"""
    yard, inputs = the_yard(tmp_path, hut_plan={**HUT, "w": 5.0})
    verdict = scene_tree.judge_children(yard, inputs, None)
    assert verdict.answer == checks.FAIL
    assert "/yard/Scenes/hut: its plan is 5.0 x 3.0 m, its hold 4.0 x 3.0 m" in verdict.findings


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
