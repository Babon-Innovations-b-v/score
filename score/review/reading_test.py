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
         "size": "waist high", "metres": [0.6, 0.6, 0.9], "anchor": "ground", "where": "left",
         "region": [0, 0, 300, 350]},
        {"id": "drum_right", "name": "blue drum", "noun": "drum", "kind": "generate", "count": 1,
         "size": "waist high", "metres": [0.6, 0.6, 0.9], "anchor": "ground", "where": "right",
         "region": [0, 600, 500, 1000]},
        {"id": "mast", "name": "radio mast", "noun": "mast", "kind": "code", "count": 1, "size": "ten people tall",
         "metres": [0.4, 0.4, 18], "anchor": "ground", "where": "centre", "region": [0, 400, 1000, 600]},
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
    return [{"terrain": False, **row} for row in ROWS], 0.03, 12.0, path, (200, 100)


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
    with pytest.raises(concepts.Refused, match="lab: no picked concept"):  # read only after its own pick
        reading.read(store, ["wreck", "lab"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes)
    assert cleared == []
    [record] = reading.read(store, ["wreck"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes)
    assert cleared == [(["wreck"], 0.05)]
    assert record["concept"] == sha and record["inventory"]["concept_pick"]["sha256"] == sha
    rows = {row["id"]: row for row in record["inventory"]["rows"]}
    assert rows["drum"]["boxes"] == [[0, 0, 20, 20], [40, 0, 60, 20]] and rows["drum"]["box"] == [0, 0, 20, 20]
    assert rows["drum"]["count"] == 2  # read as 3, found twice: the instances found count
    assert rows["drum_right"]["boxes"] == [[150, 10, 170, 30]]  # one noun asked once, each instance to its region
    assert rows["drum"]["size"] == [0.6, 0.6, 0.9] and rows["mast"]["size"] == [0.4, 0.4, 18.0]  # its metres
    assert "lamp" not in rows and record["gaps"] == []  # only Gemini named it: skipped, no gap
    assert [(item["name"], item["why"], item["box"]) for item in record["skipped"]] == [
        ("lamp", reading.ONLY_GEMINI, [90.0, 0.0, 110.0, 10.0]), ("drum", reading.ONLY_SAM, [100, 60, 110, 70]),
        ("object", reading.ONLY_SAM, [150, 50, 180, 80])]
    assert [row["id"] for row in record["answered"]] == ["drum", "drum_right", "mast", "lamp"]  # kept as answered
    assert record["euros"] == {"rows": 0.03, "boxes": 0.12, "total": 0.15}
    assert record["seconds"] == {"rows": 12.0, "boxes": 60.0, "card": 540.0}
    assert reading.reading_of(store, "wreck") == record and reading.spent(store, ["wreck", "lab"]) == 0.15
    assert reading.read(store, ["wreck"], "joey", clear=clear, ask=stand_in_rows, boxes=stand_in_boxes) == []
    assert len(cleared) == 1  # read from this pick already: nothing asked, nothing cleared
    assert reading.row_boxes(store, "wreck", "drum_right") == [[150, 10, 170, 30]]
    assert reading.row_boxes(store, "wreck", "lamp") is None and reading.row_boxes(store, "wreck", "nothing") is None
    assert reading.row_boxes(store, "lab", "drum") is None


def test_a_new_pick_has_no_reading_until_read(store, tmp_path):
    picked_place(store, tmp_path)
    reading.read(store, ["wreck"], "joey", ask=stand_in_rows, boxes=stand_in_boxes)
    concepts.pick(store, "wreck", None, "joey")
    assert reading.reading_of(store, "wreck") is None and reading.to_read(store, ["wreck"]) == []


def row(row_id, noun, region, boxes, **more):
    """An inventory row as boxed_rows gives it, for the agreement's tests."""
    return {"id": row_id, "name": more.pop("name", noun), "noun": noun, "kind": "generate", "count": 1, "terrain": False,
            "anchor": "floor", "region": region, "boxes": boxes, "box": boxes[0] if boxes else None, "size": [1, 1, 1],
            **more}


def test_only_what_both_readers_agree_on_is_a_row_and_the_structure_stays():
    rows = [row("wall", "wall", None, []), row("dome", "building", None, [], inside_place=True),
            row("rock", "rock", None, [], terrain=True), row("crate", "crate", [0, 0, 500, 500], []),
            row("chair", "chair", [0, 0, 500, 500], [[0, 0, 10, 10], [20, 0, 30, 10]]),
            row("cup", "cup", None, [], anchor="on:crate")]
    kept, skipped, merged = reading.agreed(rows, [], [{"word": "machine", "box": [50, 50, 60, 60]}], (100, 100))
    assert [(item["id"], item["count"]) for item in kept] == [("wall", 1), ("dome", 1), ("rock", 1), ("chair", 2)]
    assert [(item["name"], item["why"]) for item in skipped] == [
        ("crate", reading.ONLY_GEMINI), ("cup", reading.ONLY_GEMINI), ("machine", reading.ONLY_SAM)]
    assert merged == []
    inside = [row("hangar", "building", None, []), row("ship", "spacecraft", None, [], anchor="on:hangar"),
              row("hatch", "door", None, [], anchor="on:ship"), row("cup", "cup", None, [])]
    assert reading.inside_rows(inside, {"hangar"}) == {"hangar", "ship", "hatch"}  # an inside place's own, kept


def test_duplicates_go_one_box_one_row():
    size = (100, 100)
    # one instance boxed twice on one row: one box
    [only], _, _ = reading.agreed([row("chair", "chair", None, [[0, 0, 10, 10], [0, 0, 10, 11]])], [], [], size)
    assert only["boxes"] == [[0, 0, 10, 10]] and only["count"] == 1
    # one box held by two rows: the one whose region it fits
    kept, skipped, _ = reading.agreed([row("locker", "locker", [500, 500, 1000, 1000], [[0, 0, 10, 10]]),
                                       row("chest", "chest", [0, 0, 200, 200], [[0, 0, 10, 10], [40, 40, 50, 50]])],
                                      [], [], size)
    assert {item["id"]: item["boxes"] for item in kept} == {"chest": [[0, 0, 10, 10], [40, 40, 50, 50]]}
    assert [item["name"] for item in skipped] == ["locker"]
    # two rows of one thing: one row, the instances of both counted once, a child on the merged one moved
    kept, _, merged = reading.agreed([row("cabinet", "cabinet", None, [[0, 0, 10, 10]]),
                                      row("storage", "storage cabinets", None, [[0, 0, 10, 11], [60, 0, 70, 10]]),
                                      row("cup", "cup", None, [[62, 0, 64, 2]], anchor="on:storage")], [], [], size)
    assert [(item["id"], item["count"]) for item in kept] == [("cabinet", 2), ("cup", 1)]
    assert merged == [{"name": "storage cabinets", "row": "storage", "into": "cabinet"}]
    assert kept[1]["anchor"] == "on:cabinet"


def test_a_row_is_found_by_its_own_words_first_and_an_older_reading_is_read_again_by_sam_only(store, tmp_path):
    sha = picked_place(store, tmp_path)
    old = [{**dict(ROWS[2]), "view": "v1", "box": None, "boxes": [], "size": [0.4, 0.4, 18.0], "size_words": "tall",
            "thing": "", "name": "glass greenhouse dome", "noun": "building", "id": "greenhouse", "terrain": False,
            "kind": "generate", "anchor": "ground", "where": "left", "region": [0, 0, 1000, 1000]}]
    reading.kept(store, {"place": "wreck", "concept": sha, "at": "2026-01-01T08:00:00+00:00", "by": "joey",
                         "method": 4, "size": [200, 100], "inventory": {"rows": old}, "gaps": [],
                         "euros": {"rows": 0.03, "boxes": 0.1, "total": 0.13}, "seconds": {}})
    asked = []

    def boxes(jobs, folder):
        asked.append([item["nouns"] for item in jobs[0]["rows"]])
        return {"wreck.#greenhouse": [{"box": [10, 10, 90, 90]}], "wreck.=building": []}, {
            "euros": 0.08, "wall_minutes": 5.0, "machines": []}
    never = lambda store, place, folder: pytest.fail("Gemini asked again")  # noqa: E731
    [record] = reading.read(store, ["wreck"], "joey", ask=never, boxes=boxes)
    assert asked[0][:2] == [["glass greenhouse dome"], ["building"]]  # its own words, then its noun
    assert record["inventory"]["rows"][0]["boxes"] == [[10, 10, 90, 90]] and record["from"].startswith(
        "inventory-readings/wreck/")
    assert record["euros"] == {"rows": 0.0, "boxes": 0.08, "total": 0.08} and record["answered"][0]["metres"] == [
        0.4, 0.4, 18.0]
    assert reading.spent(store, ["wreck"]) == 0.21 and reading.cost(store, record)["euros"] == 0.21


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
    assert [gap["kind"] for gap in reading.gaps([{"id": "a", "anchor": None, "region": None, "terrain": False, "count": 1,
                                                  "size": None, "boxes": [[0, 0, 1, 1]]}])] == ["size", "anchor"]
    assert reading.gaps([{"id": "g", "anchor": "ground", "terrain": True, "size": None}]) == []  # the plan sizes it
    assert reading.metres_of([4.8, 1.9, 1.5]) == [4.8, 1.9, 1.5]
    assert [reading.metres_of(wrong) for wrong in ([4.8, 1.9], [4.8, 0, 1.5], "4.8 m", [True, 1, 1])] == [None] * 4
    with pytest.raises(concepts.Refused, match="no JSON"):
        reading.rows_of("rows: none")


def test_a_rows_answer_off_the_schema_is_kept_with_its_cost_and_read_again(store, tmp_path):
    picked_place(store, tmp_path)
    off = lambda store, place, folder: ("row 'earth' has no valid anchor", 0.02, 9.0, None, None)  # noqa: E731
    assert reading.read(store, ["wreck"], "joey", ask=off, boxes=stand_in_boxes) == []
    [refused] = reading.readings(store, "wreck")
    assert "anchor" in refused["refused"] and reading.spent(store, ["wreck"]) == 0.02
    assert reading.reading_of(store, "wreck") is None and reading.to_read(store, ["wreck"]) == ["wreck"]
