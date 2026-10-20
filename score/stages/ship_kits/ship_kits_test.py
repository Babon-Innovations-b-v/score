"""The ship-kit stage keeps only a layout's code pieces, and a ship deck leaves no seam round a set-in grate, without a
card or Blender."""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from score.stages import ship_kits  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402


def test_the_kit_keeps_only_the_named_pipeline_failures():
    # #19: the inventory's own kind routes nothing; only the cockpit's thrust indicator names a pipeline failure.
    kinds = ["cockpit_wall_lower_plain", "cockpit_thrust_indicator", "cockpit_door_leaf"]
    layout = {"room": "cockpit", "pieces": [{"kind": kind} for kind in kinds],
              "kinds": {kind: {} for kind in kinds}, "counts": {kind: 1 for kind in kinds}}
    kept = ship_kits.code_only(layout)
    assert [piece["kind"] for piece in kept["pieces"]] == ["cockpit_thrust_indicator"]
    assert set(kept["kinds"]) == set(kept["counts"]) == {"cockpit_thrust_indicator"}


def grate_openings(cut):
    """The cockpit's floor grate's footprint along the room (z) and the openings cut for it in the deck plates under
    it, both as z spans in the room's frame, with the deck cut by `cut` (room_kit.cut_openings, its gap given)."""
    with prop_data.tools("props/scene"):
        import room_kit
        import ship_kit
        plan, inventory = (json.loads((REPO / f"data/{kind}/cockpit.json").read_text())
                           for kind in ("plans", "inventory"))
        kept = room_kit.cut_openings
        room_kit.cut_openings = cut(room_kit, kept)
        try:
            pieces = ship_kit.layout("cockpit", plan, inventory)["pieces"]
        finally:
            room_kit.cut_openings = kept
    grate = next(piece for piece in pieces if piece["kind"] == "cockpit_floor_grate")
    span = sorted((grate["at"][2], grate["at"][2] + grate["y"][2] * grate["size"][1]))
    gaps = [sorted((piece["at"][2] + piece["y"][2] * low, piece["at"][2] + piece["y"][2] * high))
             for piece in pieces if piece["kind"] == "cockpit_ring_floor_plate"
             for _, low, _, high in piece.get("openings", [])]
    return span, gaps


def test_a_ship_deck_has_no_seam_round_a_grate():
    """Both ways (the cockpit's 3 view rays into nothing, 2026-10-15): with room_kit's 4 mm gap the openings run past
    the grate's ends, a seam the ground-free ship shows nothing under; the ship kit cuts them to the grate itself."""
    span, gaps = grate_openings(lambda room_kit, cut: cut)
    assert round(min(low for low, _ in gaps), 4) == round(span[0], 4), (span, gaps)
    assert round(max(high for _, high in gaps), 4) == round(span[1], 4), (span, gaps)
    span, gaps = grate_openings(lambda room_kit, cut: lambda room, found, gap=None: cut(room, found))
    assert round(span[0] - min(low for low, _ in gaps), 4) == 0.004, (span, gaps)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    test_the_kit_keeps_only_the_named_pipeline_failures()
    test_a_ship_deck_has_no_seam_round_a_grate()
    print("ship_kits: 2 tests pass")
