"""The surface-tiles stage's invariant: a place's tiles are exactly the surfaces its scene library gives the shell its
locked plan lays, less the see-through and glowing ones; a place with no such shell has no row, a shell no tile draws
rents no card, and the gate names every wanted surface that came back without its tile.

The shed below is worked out by hand: its plan lays a deck, walls and a roof (enclosed, no kit) and one flight of
stairs; the library gives the floor deck_plate (deck and stair), the wall painted_panel, the roof clear_glass (glass:
no tile). So the tiles are deck_plate and painted_panel.

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26):
- `tiled`: drop the `not in UNTILED_FAMILIES` filter -> clear_glass is tiled (test_the_tiles_are_the_shells_surfaces).
- `shell_kinds`: drop `and not design_shell.laid_for(design)` -> a kit room lists its deck, walls and roof
  (test_a_place_with_no_record_shell_has_no_tiles).
- `make`: remove the `if not wanted(inputs)[0]` early return -> a card is rented (test_nothing_to_tile_rents_no_card).
- `judge_tiles`: `missing = []` -> the gate passes with deck_plate missing (test_the_gate_names_a_missing_tile).
- `tile_faults`: skip the per-role check -> a tile with no pictures passes the contract (same test).
"""
import json

import pytest

from score import checks
from score.stages import surface_tiles

SHED = {"w": 8.0, "d": 6.0, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]],
        "walls": [{"from": [0.0, 0.0], "to": [8.0, 0.0], "thick": 0.2, "tall": 3.0}],
        "stairs": [{"kind": "stair", "points": [[6.0, 4.0], [7.0, 4.0], [7.0, 6.0], [6.0, 6.0]], "from": 0.0,
                    "to": 1.0}]}
LIBRARY = {"kinds": {"floor": ["deck_plate"], "wall": ["painted_panel"], "roof": ["clear_glass"]}}
SPECS = {"deck_plate": {"family": "metal"}, "painted_panel": {"family": "paint"}, "clear_glass": {"family": "glass"}}


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    """A row's inputs over the shed's plan, its scene library and a palette; the specs stand in for the library's."""
    monkeypatch.setattr(surface_tiles, "scene_specs", lambda palette: SPECS)
    (tmp_path / "shed.json").write_text(json.dumps(SHED))
    for row in ("library", "palette"):
        (tmp_path / row).mkdir()
    (tmp_path / "library" / "materials.json").write_text(json.dumps(LIBRARY))
    (tmp_path / "palette" / "palette.json").write_text(json.dumps({"tokens": {}, "wear": {"level": "light",
                                                                                          "dirt": 0}}))
    return {"design": str(tmp_path / "shed.json"), surface_tiles.LIBRARY_ROW: str(tmp_path / "library"),
            surface_tiles.PALETTE_ROW: str(tmp_path / "palette")}


def test_the_tiles_are_the_shells_surfaces():
    assert surface_tiles.shell_kinds(SHED) == ["deck", "roof", "stair", "wall"]
    assert surface_tiles.tiled(SHED, LIBRARY, SPECS) == ["deck_plate", "painted_panel"]
    assert surface_tiles.tiled(SHED, None, SPECS) == []  # no scene library made: nothing to tile


def test_a_place_with_no_record_shell_has_no_tiles():
    assert surface_tiles.shell_kinds({"w": 8.0, "d": 6.0}) == []  # open, no stairs
    # a room whose kit holds its walls is laid by the earth seed, not the record: only its stairs
    assert surface_tiles.shell_kinds(dict(SHED, shell="kit", inside=True)) == ["stair"]
    assert not surface_tiles.applies("no_such_place")  # no locked plan: no row


def test_nothing_to_tile_rents_no_card(inputs, tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(surface_tiles, "scene_specs", lambda palette: {name: {"family": "glass"} for name in SPECS})
    monkeypatch.setattr(surface_tiles.subprocess, "run",
                        lambda *args, **kwargs: pytest.fail("a card was rented for a shell no tile draws"))
    surface_tiles.make(inputs, out, 3, {})
    assert json.loads((out / "tiles.json").read_text()) == {}
    assert surface_tiles.tile_faults(out) == []
    assert surface_tiles.judge_tiles(out, inputs, {}).answer == checks.PASS


def test_the_gate_names_a_missing_tile(inputs, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    assert surface_tiles.tile_faults(out) == ["no tiles.json"]
    (out / "tiles.json").write_text(json.dumps({"painted_panel": {"metres": 2.0, "side": 1024}}))
    assert sorted(surface_tiles.tile_faults(out)) == sorted(f"no painted_panel_{role}.png"
                                                            for role in ("base_color", "metal_roughness", "normal"))
    for role in ("base_color", "metal_roughness", "normal"):
        (out / f"painted_panel_{role}.png").write_bytes(b"")
    assert surface_tiles.tile_faults(out) == []
    verdict = surface_tiles.judge_tiles(out, inputs, {})
    assert verdict.answer == checks.FAIL and verdict.findings == ("deck_plate",)
