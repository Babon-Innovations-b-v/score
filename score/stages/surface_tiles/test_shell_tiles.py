"""The surface-tiles stage's invariant: a place's tiles are exactly the surfaces its scene library gives the shell its
locked plan lays, less the see-through and glowing ones; a place with no such shell has no row, a shell no tile draws
rents no card, and the gate names every wanted surface that came back without its tile.

The shed below is worked out by hand: its plan lays a deck, walls and a roof (enclosed, no kit) and one flight of
stairs; the library gives the floor deck_plate (deck and stair), the wall painted_panel, the roof clear_glass (glass:
no tile). So the tiles are deck_plate and painted_panel.

One test, two tables: PLANS feeds designs through `shell_kinds` and `tiled`; RUNS drives the stage's `make` over the
shed with a stand-in card that returns the row's files, then reads the result through `tile_faults` and `judge_tiles`.

Breaks that turn these red (each applied once, seen red, reverted, 2026-10-26; re-proved on the fold 2026-11-13):
- `tiled`: drop the `not in UNTILED_FAMILIES` filter -> clear_glass is tiled (PLANS row `shed`, RUNS row
  `all glass` rents a card).
- `shell_kinds`: drop `and not design_shell.laid_for(design)` -> a kit room lists its deck, walls and roof
  (PLANS row `kit room`).
- `make`: remove the `if not wanted(inputs)[0]` early return -> a card is rented (RUNS row `all glass`).
- `judge_tiles`: `missing = []` -> the gate passes with deck_plate missing (RUNS rows `painted_panel ...`).
- `tile_faults`: skip the per-role check -> a tile with no pictures passes the contract (RUNS row
  `painted_panel, no pictures`).
"""
import json
import pathlib

from score import checks
from score.stages import surface_tiles

SHED = {"w": 8.0, "d": 6.0, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]],
        "walls": [{"from": [0.0, 0.0], "to": [8.0, 0.0], "thick": 0.2, "tall": 3.0}],
        "stairs": [{"kind": "stair", "points": [[6.0, 4.0], [7.0, 4.0], [7.0, 6.0], [6.0, 6.0]], "from": 0.0,
                    "to": 1.0}]}
LIBRARY = {"kinds": {"floor": ["deck_plate"], "wall": ["painted_panel"], "roof": ["clear_glass"]},
           "wear_levels": {"light": 0.25}}
SPECS = {"deck_plate": {"family": "metal"}, "painted_panel": {"family": "paint"}, "clear_glass": {"family": "glass"}}
ALL_GLASS = {name: {"family": "glass"} for name in SPECS}
ROLES = ("base_color", "metal_roughness", "normal")
SHELL = ["deck", "roof", "stair", "wall"]

# (row, design, scene library or None when none was made, specs, the shell's kinds, its tiles)
PLANS = [
    ("shed", SHED, LIBRARY, SPECS, SHELL, ["deck_plate", "painted_panel"]),
    ("no scene library", SHED, None, SPECS, SHELL, []),
    ("open, no stairs", {"w": 8.0, "d": 6.0}, LIBRARY, SPECS, [], []),
    # a room whose kit holds its walls is laid by the earth seed, not the record: only its stairs
    ("kit room", dict(SHED, shell="kit", inside=True), LIBRARY, SPECS, ["stair"], ["deck_plate"]),
]

# (row, specs, the card's tiles.json or None for none, surfaces it drew pictures for,
#  the tiles the rented card was asked for or None for no card, the contract's faults, the gate's (answer, findings)
#  or None where the contract already refuses the folder)
NO_PICTURES = {"painted_panel": {"metres": 2.0, "side": 1024}}
RUNS = [
    ("all glass", ALL_GLASS, None, (), None, [], (checks.PASS, ())),
    ("card returns nothing", SPECS, None, (), ["deck_plate", "painted_panel"], ["no tiles.json"], None),
    ("painted_panel, no pictures", SPECS, NO_PICTURES, (), ["deck_plate", "painted_panel"],
     [f"no painted_panel_{role}.png" for role in ROLES], (checks.FAIL, ("deck_plate",))),
    ("painted_panel with pictures", SPECS, NO_PICTURES, ("painted_panel",), ["deck_plate", "painted_panel"], [],
     (checks.FAIL, ("deck_plate",))),
]


def shed_inputs(home):
    """A row's inputs over the shed's plan, its scene library and a palette."""
    (home / "shed.json").write_text(json.dumps(SHED))
    for row in ("library", "palette"):
        (home / row).mkdir()
    (home / "library" / "materials.json").write_text(json.dumps(LIBRARY))
    (home / "palette" / "palette.json").write_text(json.dumps({"tokens": {}, "wear": {"level": "light", "dirt": 0}}))
    return {"design": str(home / "shed.json"), surface_tiles.LIBRARY_ROW: str(home / "library"),
            surface_tiles.PALETTE_ROW: str(home / "palette")}


def test_shell_tiles(tmp_path, monkeypatch):
    for row, design, library, specs, kinds, tiles in PLANS:
        assert surface_tiles.shell_kinds(design) == kinds, row
        assert surface_tiles.tiled(design, library, specs) == tiles, row
    assert not surface_tiles.applies("no_such_place")  # no locked plan: no row

    inputs = shed_inputs(tmp_path)
    for row, specs, returned, pictured, asked, faults, verdict in RUNS:
        out = tmp_path / row.replace(" ", "_").replace(",", "")
        out.mkdir()
        rented = []

        def card(command, **kwargs):
            """The rented card: records the job it was handed and returns the row's files."""
            rented.append(json.loads(pathlib.Path(command[2]).read_text())["tiles"])
            if returned is not None:
                (out / "tiles.json").write_text(json.dumps(returned))
            for surface in pictured:
                for role in ROLES:
                    (out / f"{surface}_{role}.png").write_bytes(b"")

        monkeypatch.setattr(surface_tiles, "scene_specs", lambda palette, specs=specs: specs)
        monkeypatch.setattr(surface_tiles.subprocess, "run", card)
        surface_tiles.make(inputs, out, 3, {})
        assert rented == ([] if asked is None else [asked]), row
        if returned is None and asked is None:
            assert json.loads((out / "tiles.json").read_text()) == {}, row
        assert sorted(surface_tiles.tile_faults(out)) == sorted(faults), row
        if verdict is not None:
            judged = surface_tiles.judge_tiles(out, inputs, {})
            assert (judged.answer, judged.findings) == verdict, row

