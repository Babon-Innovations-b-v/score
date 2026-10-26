"""A kept reading fixed where a row is a part of another row's thing (score/review/reading_fixes.py): the part merged
into it, free, as a new reading of the same lock; a reading holding none, and rows only overlapping, left alone."""
import pytest

from score.adapters import compute
from score.review import reading, reading_fixes
from score.review.reading_test import picked_place, row
from score.store import Store

SIZE = (1000, 1000)
# camp, 2026-10-26: a "door" Gemini put where the fridge is, SAM 3's box of it the fridge's glass door
FRIDGE = row("fridge", "fridge", [200, 810, 360, 870], [[810, 200, 870, 360]], part="object")
DOOR = row("door", "door", [210, 820, 340, 870], [[825, 220, 860, 330]], part="object")
HANDLE = row("handle", "handle", [250, 830, 260, 840], [[830, 250, 840, 260]], anchor="on:door", part="object")


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(compute, "require_books", lambda what: None)
    return Store.in_folder(tmp_path / "store")


def test_only_a_row_both_readers_put_inside_another_rows_thing_is_a_part_of_it():
    rows = [FRIDGE, DOOR,
            row("chair", "chair", [500, 500, 700, 700], [[500, 500, 700, 700]]),  # a person sits in it: 60% inside
            row("person", "person", [480, 500, 680, 700], [[500, 480, 700, 600]]),
            row("desk", "desk", [0, 0, 100, 100], [[0, 0, 100, 100]]),
            row("laptop", "laptop", [0, 0, 90, 90], [[10, 10, 50, 50]], anchor="on:desk")]  # stands on it: its own
    kept, merged = reading_fixes.parts_apart(rows, SIZE)
    assert [item["id"] for item in kept] == ["fridge", "chair", "person", "desk", "laptop"]
    assert merged == [{"name": "door", "row": "door", "into": "fridge"}]


def test_a_reading_holding_a_part_is_fixed_once_free_its_children_moved(store, tmp_path):
    sha = picked_place(store, tmp_path)
    reading.kept(store, {"place": "wreck", "concept": sha, "at": "2026-01-01T08:00:00+00:00", "by": "joey",
                         "method": reading.METHOD, "parts_version": reading.PARTS_VERSION, "size": list(SIZE),
                         "inventory": {"rows": [FRIDGE, DOOR, HANDLE]}, "gaps": [], "skipped": [], "merged": [],
                         "euros": {"rows": 0.03, "boxes": 0.1, "total": 0.13}, "seconds": {}})
    assert reading_fixes.to_fix(store, ["wreck"]) == ["wreck"]
    [record] = reading_fixes.fix(store, ["wreck"], "test")
    assert reading.reading_of(store, "wreck") == record and record["from"].startswith("inventory-readings/wreck/")
    assert [(item["id"], item["anchor"]) for item in record["inventory"]["rows"]] == [
        ("fridge", "floor"), ("handle", "on:fridge")]
    assert record["merged"] == [{"name": "door", "row": "door", "into": "fridge"}]
    assert record["euros"]["total"] == 0.0 and record["parts_version"] == reading.PARTS_VERSION
    assert reading_fixes.to_fix(store, ["wreck"]) == [] and reading_fixes.fix(store, ["wreck"], "test") == []
    assert reading_fixes.said([record]) == "readings fixed: wreck" and reading_fixes.said([]) == "readings: none to fix"
