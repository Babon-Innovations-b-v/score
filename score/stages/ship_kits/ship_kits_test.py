"""The ship-kit stage keeps only a layout's code pieces, and a ship deck leaves no seam round a set-in grate, without a
card or Blender."""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from score.stages import ship_kits  # noqa: E402
import score.stages.props.prop_data as prop_data  # noqa: E402


def test_the_made_rows_pieces_are_left_to_their_takes():
    layout = {"room": "galley", "pieces": [{"kind": "galley_wall_lower_plain"}, {"kind": "galley_galley_counter"},
                                           {"kind": "galley_locker"}, {"kind": "galley_door_leaf"}],
              "kinds": {"galley_wall_lower_plain": {}, "galley_galley_counter": {}, "galley_locker": {},
                        "galley_door_leaf": {}},
              "counts": {"galley_wall_lower_plain": 1, "galley_galley_counter": 1, "galley_locker": 1,
                         "galley_door_leaf": 1}}
    inventory = {"rows": [{"id": "wall_lower_plain", "kind": "code"}, {"id": "galley_counter", "kind": "generate"},
                          {"id": "locker", "kind": "generate", "reuse": "shiplock:locker"},
                          {"id": "door_leaf", "kind": "code"}]}
    kept = ship_kits.code_only(layout, inventory)
    assert [piece["kind"] for piece in kept["pieces"]] == ["galley_wall_lower_plain", "galley_door_leaf"]
    assert set(kept["kinds"]) == set(kept["counts"]) == {"galley_wall_lower_plain", "galley_door_leaf"}


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
    holes = [sorted((piece["at"][2] + piece["y"][2] * low, piece["at"][2] + piece["y"][2] * high))
             for piece in pieces if piece["kind"] == "cockpit_ring_floor_plate"
             for _, low, _, high in piece.get("openings", [])]
    return span, holes


def test_a_ship_deck_has_no_seam_round_a_grate():
    """Both ways (the cockpit's 3 view rays into nothing, 2026-10-15): with room_kit's 4 mm gap the openings run past
    the grate's ends, a seam the ground-free ship shows nothing under; the ship kit cuts them to the grate itself."""
    span, holes = grate_openings(lambda room_kit, cut: cut)
    assert round(min(low for low, _ in holes), 4) == round(span[0], 4), (span, holes)
    assert round(max(high for _, high in holes), 4) == round(span[1], 4), (span, holes)
    span, holes = grate_openings(lambda room_kit, cut: lambda room, found, gap=None: cut(room, found))
    assert round(span[0] - min(low for low, _ in holes), 4) == 0.004, (span, holes)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    test_the_made_rows_pieces_are_left_to_their_takes()
    test_a_ship_deck_has_no_seam_round_a_grate()
    print("ship_kits: 2 tests pass")
