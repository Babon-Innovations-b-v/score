"""The ship-kit stage keeps only a layout's code pieces and lays the kit from the design, without a card or Blender.
(The test of the old cockpit's deck round its grate went with its filed plan and inventory, retired 2026-10-21.)"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from score.stages import ship_kits  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402


def test_the_kit_keeps_only_the_named_pipeline_failures():
    # #19: the inventory's own kind routes nothing; only a kind the pipeline-failure record names is kept (a toy
    # record naming the thrust indicator; with none on file, the old one retired on 2026-10-21, the kit keeps none).
    kinds = ["cockpit_wall_lower_plain", "cockpit_thrust_indicator", "cockpit_door_leaf"]
    layout = {"room": "cockpit", "pieces": [{"kind": kind} for kind in kinds],
              "kinds": {kind: {} for kind in kinds}, "counts": {kind: 1 for kind in kinds}}
    with prop_data.tools("props/library"):
        import sorter
    on_file = sorter.failures
    sorter.failures = lambda: {}
    try:
        assert not ship_kits.code_only(layout)["pieces"]
        sorter.failures = lambda: {"cockpit_thrust_indicator": {"failure": "every take failed"}}
        kept = ship_kits.code_only(layout)
    finally:
        sorter.failures = on_file
    assert [piece["kind"] for piece in kept["pieces"]] == ["cockpit_thrust_indicator"]
    assert set(kept["kinds"]) == set(kept["counts"]) == {"cockpit_thrust_indicator"}


def test_the_kit_reads_the_creators_kept_design():
    """The kit lays from his kept plan and scene inventory ({home}/design), never a filed one (retired 2026-10-21);
    the picked concept is no input of it."""
    found = ship_kits.STAGE.files("quarters")
    assert found["plan"] == "{home}/design/plans/quarters.json", found
    assert found["inventory"] == "{home}/design/inventory/quarters.json", found
    assert "concept" not in found and not any("{data}/plans" in str(path) or "{data}/inventory" in str(path)
                                              for path in found.values()), found


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    test_the_kit_keeps_only_the_named_pipeline_failures()
    test_the_kit_reads_the_creators_kept_design()
    print("ship_kits: 2 tests pass")
