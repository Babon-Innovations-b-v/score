"""Check the surface-tiles stage without a bake: a place's tiles are its shell's library surfaces less the see-through
and glowing ones, a place with no scene record has no row, and the contract and gate name what a tiles output lacks.

Run: make tests TESTS=score/stages/surface_tiles/surface_tiles_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score import checks  # noqa: E402
from score.stages import surface_tiles  # noqa: E402


def check_the_tiled_surfaces():
    specs = surface_tiles.place_specs("greenhouse")
    shell = surface_tiles.shell_surfaces("greenhouse")
    tiled = surface_tiles.tiled("greenhouse", specs)
    assert tiled and set(tiled) <= set(shell), (tiled, shell)
    assert all(specs[name].get("family") not in surface_tiles.UNTILED_FAMILIES for name in tiled)
    assert "clear_glass" in shell and "clear_glass" not in tiled
    assert not surface_tiles.applies("no_such_place")


def check_the_contract_and_gate(folder):
    inputs = {"scene": str(surface_tiles.REPO / "data/scene/greenhouse.json")}
    wanted = surface_tiles.tiled("greenhouse", surface_tiles.place_specs("greenhouse"))
    assert surface_tiles.tile_faults(folder) == ["no tiles.json"]
    (folder / "tiles.json").write_text(json.dumps({name: {"metres": 2.0, "side": 1024} for name in wanted[1:]}))
    assert len(surface_tiles.tile_faults(folder)) == 3 * len(wanted[1:])
    for name in wanted[1:]:
        for role in surface_tiles.ROLES:
            (folder / f"{name}_{role}.png").write_bytes(b"")
    assert surface_tiles.tile_faults(folder) == []
    verdict = surface_tiles.judge_tiles(folder, inputs, {})
    assert verdict.answer == checks.FAIL and verdict.findings == (wanted[0],), verdict


def main():
    check_the_tiled_surfaces()
    with tempfile.TemporaryDirectory() as temporary:
        check_the_contract_and_gate(pathlib.Path(temporary))
    print("surface_tiles_test: ok")


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
