"""Every current library entry ends on the review sheets as one tile (drawn from the right file, or red with its error)
or is listed with the reason it has no look; a withdrawn entry is nowhere.

Breaks (each applied once, seen red, reverted), in sheets.py: model_file ignoring the entry's USD root (a payload
layer is drawn: red); current_entries keeping withdrawn entries (red); prepare sending a kit with no piece to the
sheets as a failure instead of skipping it (red); result_of taking a render with no result as drawn (red); compose
leaving a failed render out of index.json's failures (red); surface_item drawing a surface painted for one model on a
sphere, or leaving a glass's transmission out of its job (red).
"""
import json
import pathlib
import sys

import pytest
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import sheets  # noqa: E402


def entry(kind, name, files, state="draft", **extra):
    return {"address": f"{kind}/{name}@1", "kind": kind, "state": state,
            "files": {file: {"sha256": f"{index:064x}", "bytes": 10} for index, file in enumerate(files)}, **extra}


CASES = [
    # (entry, what the machine draws it from or None, its render's result, where it ends)
    (entry("model", "fence", ["payloads/base.usda", "payloads/geometries.usd", "sm_fence.usd", "T/a.png"],
           usd={"root": "sm_fence.usd"}), "sm_fence.usd", "ok", "drawn"),
    (entry("model", "crate", ["crate.gltf", "crate.bin", "textures/crate.png"]), "crate.gltf", "ok", "drawn"),
    (entry("model", "case", ["case-14881.glb", "case-final.glb"]), "case-final.glb", "fail", "failed"),
    (entry("take", "rover", ["rover-1.glb", "rover-final.glb", "rover.json"]), "rover-final.glb", None, "failed"),
    (entry("kit", "wall", ["piece.json", "piece.usdc"]), "piece.usdc", "ok", "drawn"),
    (entry("kit", "floor_plan", ["ship_floor.json"]), None, None, "skipped"),
    (entry("character", "clips", ["motions/bench.npz"]), None, None, "skipped"),
    (entry("model", "empty", ["model.json"]), None, None, "failed"),
    (entry("model", "old", ["old.gltf"], state="withdrawn"), None, None, "absent"),
    (entry("surface", "decal", ["albedo.png", "surface.json"], record={"tiling": False, "maps": {"albedo": "albedo.png"}}),
     None, None, "skipped"),
    (entry("surface", "glass", ["surface.json"], record={"tiling": True, "maps": {}, "constants": {"opacity": 1.0},
                                                         "transmission": {"shader": "OmniGlass", "weight": 1.0}}),
     "OmniGlass", "ok", "drawn"),
    (entry("concept", "cockpit", ["concept.png", "concept.json"]), None, None, "drawn"),
    (entry("place", "square", ["scene.usda"]), None, None, "failed"),
]


@pytest.mark.parametrize("record, drawn_from, render, ends", CASES, ids=[case[0]["address"] for case in CASES])
def test_every_current_entry_is_one_tile_or_one_reason(tmp_path, monkeypatch, record, drawn_from, render, ends):
    root, work, out = tmp_path / "lib", tmp_path / "work", tmp_path / "sheets"
    kind, rest = record["address"].split("/")
    name, version = rest.split("@")
    folder = root / "entries" / kind / name / version
    folder.mkdir(parents=True)
    (folder / "entry.json").write_text(json.dumps(record))
    picture = tmp_path / "picture.png"
    Image.new("RGB", (8, 8), (120, 120, 120)).save(picture)
    monkeypatch.setattr(sheets.library_files, "settings", lambda: {"SCORE_LIB_ROOT": str(root)})
    (tmp_path / "surface.json").write_text(json.dumps(record.get("record", {})))
    monkeypatch.setattr(sheets, "local_file", lambda record, file: None if file not in record.get("files", {file: 1})
                        else tmp_path / file if file == "surface.json" else picture)
    work.mkdir()
    sheets.prepare(work, 2)
    plan = json.loads((work / "items.json").read_text())
    listings = [json.loads(path.read_text()) for path in sorted((work / "jobs").glob("*.list.json"))]
    items = [item for listing in listings for item in listing["items"]]
    assert [item["show"]["files"][0] if "show" in item else (item["surface"]["transmission"] or {}).get("shader")
            for item in items] == ([drawn_from] if drawn_from else [])
    for item in items:
        renders = work / "renders" / next(row["job"] for row in plan if row["name"] == item["name"])
        renders.mkdir(parents=True, exist_ok=True)
        if render == "ok":
            Image.new("RGB", (32, 32)).save(renders / f"{item['name']}.png")
        if render:
            (renders / f"{item['name']}.json").write_text(json.dumps(
                {"address": item["address"], "ok": render == "ok", **({"error": "boom"} if render == "fail" else {})}))
    index = sheets.compose(work, out)
    tiles = [placed for sheets_of in index["sheets"].values() for sheet in sheets_of for placed in sheet["tiles"]]
    found = {"drawn": [placed["address"] for placed in tiles if placed["ok"]],
             "failed": [failure["address"] for failure in index["failures"]],
             "skipped": [skip["address"] for skip in index["skipped"]]}
    assert {where for where, addresses in found.items() if record["address"] in addresses} == (
        set() if ends == "absent" else {ends})
    assert len(tiles) == (1 if ends in ("drawn", "failed") else 0)
    assert all((out / sheet["sheet"]).is_file() for sheets_of in index["sheets"].values() for sheet in sheets_of)
