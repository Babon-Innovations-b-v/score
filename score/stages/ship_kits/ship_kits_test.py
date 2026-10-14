"""The ship-kit stage keeps only a layout's code pieces, without a card or Blender."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score.stages import ship_kits  # noqa: E402


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


if __name__ == "__main__":
    test_the_made_rows_pieces_are_left_to_their_takes()
    print("ship_kits: 1 test passes")
