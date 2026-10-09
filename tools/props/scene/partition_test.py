"""Checks for the partition stage: tiles cover the picture, proposals come back on the whole picture, the agent's
mapping is refused when it leaves a proposal or a row unaccounted for, applied boxes are the proposals' own, and a
pointer only picks proposals, never becomes a box.

Plain python: python3 tools/props/scene/partition_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import partition  # noqa: E402


def a_place():
    return {"rows": [{"id": "desk", "view": "v1", "box": None, "unseen": "x"},
                     {"id": "lamp", "view": "v1", "box": None, "unseen": "x"},
                     {"id": "wall", "view": "v1", "box": None, "unseen": "x", "repeats": "across the room"}]}


PROPOSALS = [{"id": "v1.1", "view": "v1", "box": [100, 100, 500, 400], "area": 90000, "share": 0.02},
             {"id": "v1.2", "view": "v1", "box": [120, 120, 200, 200], "area": 5000, "share": 0.001},
             {"id": "v1.3", "view": "v1", "box": [800, 50, 900, 150], "area": 8000, "share": 0.002},
             {"id": "v1.4", "view": "v1", "box": [1500, 900, 1900, 1300], "area": 120000, "share": 0.03}]


def test_tiles_cover_the_picture():
    boxes = [box for _, _, box in partition.tile_boxes((2752, 1536))]
    assert min(box[0] for box in boxes) == 0 and max(box[2] for box in boxes) == 2752
    assert min(box[1] for box in boxes) == 0 and max(box[3] for box in boxes) == 1536


def test_a_mapping_must_account_for_every_proposal_and_row():
    place = a_place()
    for row in place["rows"]:
        row.pop("unseen")
    problems = partition.mapping_problems(place, PROPOSALS, {"v1.1": {"row": "desk"}, "v1.3": {"drop": ""}})
    assert any("v1.4 is neither" in line for line in problems), problems   # a big proposal left out
    assert not any("v1.2" in line for line in problems), problems           # a part of v1.1 needs no entry
    assert any("dropped without a reason" in line for line in problems), problems
    assert any("row lamp has no proposal" in line for line in problems), problems


def test_applied_boxes_are_the_proposals_own():
    place = a_place()
    new = partition.apply(place, PROPOSALS, {"v1.1": {"row": "desk"}, "v1.3": {"rows": ["lamp", "wall"]},
                                              "v1.4": {"new": "a crate"}})
    rows = {row["id"]: row for row in place["rows"]}
    assert rows["desk"]["box"] == [100, 100, 500, 400] and rows["desk"]["box_from"] == ["v1.1"]
    assert "unseen" not in rows["lamp"] and rows["wall"]["box"] == [800, 50, 900, 150]
    assert new[0]["words"] == "a crate" and new[0]["box"] == [1500, 900, 1900, 1300]


def test_a_pointer_picks_proposals_and_is_never_kept():
    mapping, matched = partition.snap(a_place(), PROPOSALS, {"desk": [90, 90, 520, 420], "lamp": [790, 40, 910, 160]})
    assert matched["desk"]["proposals"] == ["v1.1", "v1.2"] and matched["lamp"]["proposals"] == ["v1.3"]
    assert mapping["v1.1"] == {"rows": ["desk"]}
    place = a_place()
    partition.apply(place, PROPOSALS, mapping)
    assert {row["id"]: row["box"] for row in place["rows"]}["desk"] == [100, 100, 500, 400]


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
