"""Check the surface-tiles stage without a bake: a place's tiles are the surfaces its scene library gives the shell its
locked plan lays (less the see-through and glowing ones), a place with no locked plan or no shell has no row, and the
contract and gate name what a tiles output lacks. The plan, the scene library and the palette are written here.

Run: make tests TESTS=score/stages/surface_tiles/surface_tiles_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score import checks  # noqa: E402
from score.stages import surface_tiles  # noqa: E402

# A shed's locked plan (plan_writing's schema): walls round its outline, a flat roof, one flight of stairs.
SHED = {"w": 8.0, "d": 6.0, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]],
        "walls": [{"from": [0.0, 0.0], "to": [8.0, 0.0], "thick": 0.2, "tall": 3.0}],
        "stairs": [{"kind": "stair", "points": [[6.0, 4.0], [7.0, 4.0], [7.0, 6.0], [6.0, 6.0]], "from": 0.0,
                    "to": 1.0}]}
# The scene library's kinds (its materials.json `kinds`): the floor, wall and roof parts' surfaces; the stair takes
# the floor's (palette_library.SHELL_KINDS).
LIBRARY = {"kinds": {"floor": ["deck_plate"], "wall": ["painted_panel"], "roof": ["clear_glass"]}}


def stand_in_specs(palette):
    """A stand-in for the scene library's specs: glass for clear_glass, paint for the rest (no recipe is read)."""
    return {"deck_plate": {"family": "metal"}, "painted_panel": {"family": "paint"}, "clear_glass": {"family": "glass"}}


def written(folder):
    """The row's inputs over a plan, scene library and palette written in `folder`."""
    (folder / "shed.json").write_text(json.dumps(SHED))
    for row in ("library", "palette"):
        (folder / row).mkdir()
    (folder / "library" / "materials.json").write_text(json.dumps(LIBRARY))
    (folder / "palette" / "palette.json").write_text(json.dumps({"tokens": {}, "wear": {"level": "light", "dirt": 0}}))
    return {"design": str(folder / "shed.json"), surface_tiles.LIBRARY_ROW: str(folder / "library"),
            surface_tiles.PALETTE_ROW: str(folder / "palette")}


def check_the_tiled_surfaces():
    assert surface_tiles.shell_kinds(SHED) == ["deck", "roof", "stair", "wall"], surface_tiles.shell_kinds(SHED)
    specs = stand_in_specs(None)
    assert surface_tiles.tiled(SHED, LIBRARY, specs) == ["deck_plate", "painted_panel"]
    # no scene library made: nothing to tile
    assert surface_tiles.tiled(SHED, None, specs) == []
    # an open place with no stairs lays no shell of the record's: no row
    assert surface_tiles.shell_kinds({"w": 8.0, "d": 6.0}) == []
    # a room whose kit holds its walls is laid by the earth seed, not the record: only its stairs
    assert surface_tiles.shell_kinds(dict(SHED, shell="kit", inside=True)) == ["stair"]
    assert not surface_tiles.applies("no_such_place")


def check_the_contract_and_gate(folder, inputs):
    wanted = surface_tiles.tiled(SHED, LIBRARY, stand_in_specs(None))
    assert surface_tiles.tile_faults(folder) == ["no tiles.json"]
    (folder / "tiles.json").write_text(json.dumps({name: {"metres": 2.0, "side": 1024} for name in wanted[1:]}))
    assert len(surface_tiles.tile_faults(folder)) == 3 * len(wanted[1:])
    for name in wanted[1:]:
        for role in surface_tiles.ROLES:
            (folder / f"{name}_{role}.png").write_bytes(b"")
    assert surface_tiles.tile_faults(folder) == []
    verdict = surface_tiles.judge_tiles(folder, inputs, {})
    assert verdict.answer == checks.FAIL and verdict.findings == (wanted[0],), verdict


def check_a_shell_no_tile_draws_rents_no_card(folder, inputs):
    """A shell whose every surface is seen through writes an empty tiles.json, its gate passes, and nothing is run."""
    kept = surface_tiles.subprocess.run
    surface_tiles.subprocess.run = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("a card was rented"))
    surface_tiles.scene_specs = lambda palette: {name: {"family": "glass"} for name in stand_in_specs(None)}
    try:
        surface_tiles.make(inputs, folder, 3, {})
    finally:
        surface_tiles.subprocess.run, surface_tiles.scene_specs = kept, stand_in_specs
    assert json.loads((folder / "tiles.json").read_text()) == {} and surface_tiles.tile_faults(folder) == []
    surface_tiles.scene_specs = lambda palette: {name: {"family": "glass"} for name in stand_in_specs(None)}
    try:
        assert surface_tiles.judge_tiles(folder, inputs, {}).answer == checks.PASS
    finally:
        surface_tiles.scene_specs = stand_in_specs


def main():
    kept = surface_tiles.scene_specs
    surface_tiles.scene_specs = stand_in_specs
    try:
        with tempfile.TemporaryDirectory() as records, tempfile.TemporaryDirectory() as temporary, \
                tempfile.TemporaryDirectory() as empty:
            check_the_tiled_surfaces()
            inputs = written(pathlib.Path(records))
            check_the_contract_and_gate(pathlib.Path(temporary), inputs)
            check_a_shell_no_tile_draws_rents_no_card(pathlib.Path(empty), inputs)
    finally:
        surface_tiles.scene_specs = kept
    print("surface_tiles_test: ok")


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
