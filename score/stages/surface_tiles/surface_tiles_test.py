"""Check the surface-tiles stage without a bake: a place's tiles are its shell's library surfaces less the see-through
and glowing ones, a place with no scene record has no row, and the contract and gate name what a tiles output lacks.
The scene record is one written here (the old seed records were retired, 2026-10-21).

Run: make tests TESTS=score/stages/surface_tiles/surface_tiles_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score import checks  # noqa: E402
from score.stages import surface_tiles  # noqa: E402

SHELL = ("painted_panel", "roof_steel_paint", "potting_soil", "clear_glass")


def recorded(folder):
    """surface_tiles.scene_path pointed at a scene record of the shed in `folder`, its shell's structure SHELL."""
    record = folder / "shed.json"
    record.write_text(json.dumps({"structure": [{"name": f"part_{number}", "surface": surface}
                                                for number, surface in enumerate(SHELL)]}))
    surface_tiles.scene_path = lambda place: folder / f"{place}.json"
    return record


def shell_specs(place):
    """A stand-in library holding the place's shell surfaces (glass for clear_glass, paint for the rest): every old
    surface was retired on 2026-10-21, so the tiling rules are checked on these."""
    return {name: {"family": "glass" if name == "clear_glass" else "paint"}
            for name in surface_tiles.shell_surfaces(place)}


def check_the_tiled_surfaces():
    shell = surface_tiles.shell_surfaces("shed")
    tiled = surface_tiles.tiled("shed", shell_specs("shed"))
    assert tiled and set(tiled) <= set(shell), (tiled, shell)
    assert "clear_glass" in shell and "clear_glass" not in tiled
    assert not surface_tiles.applies("no_such_place")
    # the library holds none of the shell's surfaces until they are made again: nothing to tile, no row
    assert surface_tiles.tiled("shed", surface_tiles.place_specs("shed")) == []
    assert not surface_tiles.applies("shed")


def check_the_contract_and_gate(folder, record):
    inputs = {"scene": str(record)}
    wanted = surface_tiles.tiled("shed", shell_specs("shed"))
    assert surface_tiles.tile_faults(folder) == ["no tiles.json"]
    (folder / "tiles.json").write_text(json.dumps({name: {"metres": 2.0, "side": 1024} for name in wanted[1:]}))
    assert len(surface_tiles.tile_faults(folder)) == 3 * len(wanted[1:])
    for name in wanted[1:]:
        for role in surface_tiles.ROLES:
            (folder / f"{name}_{role}.png").write_bytes(b"")
    assert surface_tiles.tile_faults(folder) == []
    kept = surface_tiles.place_specs
    surface_tiles.place_specs = shell_specs
    try:
        verdict = surface_tiles.judge_tiles(folder, inputs, {})
    finally:
        surface_tiles.place_specs = kept
    assert verdict.answer == checks.FAIL and verdict.findings == (wanted[0],), verdict


def main():
    held = surface_tiles.scene_path
    with tempfile.TemporaryDirectory() as records, tempfile.TemporaryDirectory() as temporary:
        record = recorded(pathlib.Path(records))
        try:
            check_the_tiled_surfaces()
            check_the_contract_and_gate(pathlib.Path(temporary), record)
        finally:
            surface_tiles.scene_path = held
    print("surface_tiles_test: ok")


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
