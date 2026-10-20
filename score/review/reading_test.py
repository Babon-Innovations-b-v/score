"""The scene inventory reading (score/review/reading.py) with stand-ins for Gemini and SAM 3 (no call, nothing
spent): a picked place is read once inside the reading's clearance, its rows carry SAM 3's boxes, and every
disagreement is a named gap; an unpicked place, or one already read from its pick, is not read; the running total sums
every reading."""
import hashlib
import io

import pytest
from PIL import Image

from score.adapters import compute
from score.review import concepts, reading
from score.store import Store

ROWS = [{"id": "drum", "name": "rusted fuel drum", "noun": "drum", "kind": "generate", "count": 3,
         "size": "waist high", "anchor": "ground", "where": "left", "region": [0, 0, 300, 350]},
        {"id": "drum_right", "name": "blue drum", "noun": "drum", "kind": "generate", "count": 1,
         "size": "waist high", "anchor": "ground", "where": "right", "region": [0, 600, 500, 1000]},
        {"id": "mast", "name": "radio mast", "noun": "mast", "kind": "code", "count": 1, "size": "ten people tall",
         "anchor": "ground", "where": "centre", "region": [0, 400, 1000, 600]},
        {"id": "lamp", "name": "lamp", "noun": "lamp", "kind": "code", "count": 1, "size": "a hand", "anchor": "on:mast",
         "where": "top of the mast", "region": [0, 450, 100, 550]}]


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(compute, "require_books", lambda what: None)
    monkeypatch.setattr(compute, "books_refusal", lambda: None)
    monkeypatch.delenv(compute.GRANT, raising=False)
    return Store.in_folder(tmp_path / "store")


def picked_place(store, tmp_path, place="wreck"):
    """A place with one draw, picked: its sha."""
    buffer = io.BytesIO()
    Image.new("RGB", (200, 100), (90, 60, 40)).save(buffer, "PNG")
    sha = hashlib.sha256(buffer.getvalue()).hexdigest()
    (tmp_path / "draw.png").write_bytes(buffer.getvalue())
    store.put_blob(tmp_path / "draw.png", sha)
    store.write_once(f"concepts/{place}/draws/1.json", {"place": place, "sha": sha, "name": "d.png"})
    concepts.pick(store, place, sha, "joey")
    return sha


def stand_in_rows(store, place, folder):
    path = reading.picture_path(store, concepts.picked(store, place), folder)
    return [dict(row) for row in ROWS], 0.03, 12.0, path, (200, 100)


def stand_in_boxes(jobs, folder):
    """SAM 3 finds two drums on the left (one twice), one on the right, one where no drum row stands, the mast, no
    lamp, and a crate no row names."""
    drum = [{"box": [0, 0, 20, 20]}, {"box": [1, 1, 20, 20]}, {"box": [40, 0, 60, 20]}, {"box": [150, 10, 170, 30]},
            {"box": [100, 60, 110, 70]}]
    return ({"wreck.=drum": drum, "wreck.=mast": [{"box": [90, 0, 110, 100]}], "wreck.=lamp": [],
             "wreck.~object": [{"box": [150, 50, 180, 80]}, {"box": [0, 0, 20, 20]}], "wreck.~person": []},
            {"euros": 0.12, "wall_minutes": 10.0, "machines": [{"unit_seconds": [60.0]}]})


def test_a_picked_place_is_read_once_with_its_boxes_and_gaps(store, tmp_path, monkeypatch):
    sha = picked_place(store, tmp_path)
    cleared = []
    monkeypatch.setattr(compute, "READING_GEMINI_EUROS", 0.05)

    def clear(store, places, euros):
        cleared.append((places, euros))
        return compute.reading_clearance(store, places, euros)
    [record] = reading.read(store, ["wreck", "lab"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes)
    assert cleared == [(["wreck"], 0.05)]  # the lab has no pick: not read
    assert record["concept"] == sha and record["inventory"]["concept_pick"]["sha256"] == sha
    rows = {row["id"]: row for row in record["inventory"]["rows"]}
    assert rows["drum"]["boxes"] == [[0, 0, 20, 20], [40, 0, 60, 20]] and rows["drum"]["box"] == [0, 0, 20, 20]
    assert rows["drum_right"]["boxes"] == [[150, 10, 170, 30]]  # one noun asked once, each instance to its region
    assert rows["lamp"]["anchor"] == "on:mast" and rows["lamp"]["size_words"] == "a hand"
    kinds = sorted((gap["kind"], gap["row"] or "") for gap in record["gaps"])
    assert kinds == [("count", "drum"), ("not found", "lamp"), ("outside", ""), ("unnamed", "")]
    assert [gap["box"] for gap in record["gaps"] if gap["kind"] == "outside"] == [[100, 60, 110, 70]]
    assert [gap["box"] for gap in record["gaps"] if gap["kind"] == "unnamed"] == [[150, 50, 180, 80]]
    assert record["euros"] == {"rows": 0.03, "boxes": 0.12, "total": 0.15}
    assert record["seconds"] == {"rows": 12.0, "boxes": 60.0, "card": 540.0}
    assert reading.reading_of(store, "wreck") == record and reading.spent(store, ["wreck", "lab"]) == 0.15
    assert reading.read(store, ["wreck"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes) == []
    assert len(cleared) == 1  # read from this pick already: nothing asked, nothing cleared


def test_a_new_pick_has_no_reading_until_read(store, tmp_path):
    picked_place(store, tmp_path)
    reading.read(store, ["wreck"], "joey", ask=stand_in_rows, boxes=stand_in_boxes)
    concepts.pick(store, "wreck", None, "joey")
    assert reading.reading_of(store, "wreck") is None and reading.to_read(store, ["wreck"]) == []


def test_rows_off_the_schema_are_refused():
    good = '{"rows": [{"id": "a", "name": "a", "noun": "a", "kind": "code", "count": 1, "size": "s", ' \
           '"anchor": "floor", "where": "w", "terrain": false}]}'
    assert reading.rows_of(good)[0]["id"] == "a" and reading.rows_of(good)[0]["region"] is None
    for wrong, said in (('"count": 1', '"count": 0'), ('"kind": "code"', '"kind": "mechanic"'),
                        ('"terrain": false', '"terrain": "no"')):
        with pytest.raises(concepts.Refused, match=said.split(":")[0].strip('"')):
            reading.rows_of(good.replace(wrong, said))
    assert reading.rows_of(good.replace('"floor"', '"on:b"'))[0]["anchor"] is None  # a gap of its row, not a refusal
    assert reading.anchor_of("a", ["a", "b"]) == "on:a" and reading.region_of([10, 20, 5, 30]) is None
    assert reading.region_of([10, 20, 500, 300]) == [10, 20, 500, 300]
    assert [gap["kind"] for gap in reading.gaps([{"id": "a", "anchor": None, "region": None, "noun": "a", "count": 1,
                                                  "boxes": [[0, 0, 1, 1]]}], [])] == ["anchor", "region"]
    with pytest.raises(concepts.Refused, match="no JSON"):
        reading.rows_of("rows: none")


def test_a_rows_answer_off_the_schema_is_kept_with_its_cost_and_read_again(store, tmp_path):
    picked_place(store, tmp_path)
    off = lambda store, place, folder: ("row 'earth' has no valid anchor", 0.02, 9.0, None, None)  # noqa: E731
    assert reading.read(store, ["wreck"], "joey", ask=off, boxes=stand_in_boxes) == []
    [refused] = reading.readings(store, "wreck")
    assert "anchor" in refused["refused"] and reading.spent(store, ["wreck"]) == 0.02
    assert reading.reading_of(store, "wreck") is None and reading.to_read(store, ["wreck"]) == ["wreck"]
