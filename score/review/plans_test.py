"""The plan review (score/review/plans.py) on stand-in data, with a stand-in for Gemini and for the plan stage's run
(no call is made, nothing is spent, no row runs): a plan is drawn from the picked concept's inventory, each item tied
to its row; none before the inventory counts; his edits are kept as his own and checked; an inside place has its
holder, row and shape once the layer above's plan is made; his inside places and their rows redo what follows; a
reading in the store is the inventory; the plan stage reads his plan; a correction runs only inside his yes."""
import json
import subprocess

import pytest
from PIL import Image

from score import review
from score.adapters import compute
from score.review import concepts, plans, web
from score.store import Store

PICK = "a" * 64


@pytest.fixture
def data(tmp_path):
    """A holder `yard` (a plan with no leads: no plan row) holding `shed` (a plan row: it says where its door leads)."""
    folder = tmp_path / "data"
    for name in ("plans", "inventory", "places"):
        (folder / name).mkdir(parents=True)
    (folder / "plans/yard.json").write_text(json.dumps({"title": "YARD", "shell": "outdoor", "w": 20.0, "d": 12.0,
                                                        "height": "", "doors": [], "items": []}))
    (folder / "plans/shed.json").write_text(json.dumps({
        "title": "SHED", "shell": "kit", "w": 4.0, "d": 3.0, "height": "ceiling 2.5 m",
        "doors": [["S", 2.0, 0.9, "DOOR to the yard"]], "leads": {"S": {"to": "yard", "why": "its one door"}},
        "items": [], "people": []}))
    (folder / "places/within.json").write_text(json.dumps({"within": {"shed": {"within": "yard"}}, "shells": {}}))
    rows = [{"id": "bench", "name": "a bench", "anchor": "floor", "size": [2.0, 0.6, 0.9], "count": 1,
             "at": [{"x": 0.0, "z": -1.0, "facing": 0}]},
            {"id": "crate", "name": "a crate", "anchor": "floor", "size": [0.5, 0.5, 0.5], "count": 2, "at": []},
            {"id": "vice", "name": "a vice", "anchor": "bench", "size": [0.2, 0.2, 0.2], "count": 1},
            {"id": "lamp", "name": "a wall lamp", "anchor": "wall", "size": [0.3, 0.2, 0.3], "count": 1}]
    (folder / "inventory/shed.json").write_text(json.dumps({"concept_pick": {"sha256": PICK}, "rows": rows}))
    (folder / "inventory/yard.json").write_text(json.dumps({"concept_pick": {"sha256": PICK}, "rows": []}))
    return folder


@pytest.fixture
def store(tmp_path, monkeypatch, data):
    monkeypatch.setattr(compute, "require_books", lambda what: None)
    monkeypatch.delenv("SCORE_SPEND_TICKET", raising=False)
    monkeypatch.setattr(concepts, "handed_over", lambda store, place: "library: stand-in")
    monkeypatch.setattr(plans, "DATA", data)
    monkeypatch.setattr(plans, "KEPT", tmp_path / "kept")
    monkeypatch.setattr(plans, "KEPT_INVENTORY", tmp_path / "kept-inventory")
    monkeypatch.setattr(plans, "KEPT_CONCEPT", tmp_path / "kept-concepts")
    found = Store.in_folder(tmp_path / "store")
    picture = tmp_path / "pick.png"
    Image.new("RGB", (64, 40), (40, 90, 160)).save(picture)
    found.put_blob(picture, PICK)
    return found


def picked(store, place):
    store.write_once(f"concepts/{place}/draws/1.json", {"place": place, "sha": PICK, "at": "2026-10-21T00:00"})
    concepts.pick(store, place, PICK, "joey")


def test_no_plan_before_the_inventory_counts_then_each_item_tied_to_its_row(store, data):
    assert plans.current(store, "shed") is None  # not picked: no inventory counts
    picked(store, "shed")
    shown = plans.current(store, "shed")
    plan = shown["plan"]
    assert shown["how"] == "derived" and plan["leads"]["S"]["to"] == "yard"
    names = {item[0]: item for item in plan["items"]}
    assert plan["rows"]["BENCH 1"] == ["bench", "vice"] and plan["rows"]["CRATE 2"] == ["crate"]
    assert names["BENCH 1"][1:5] == [1.0, 0.2, 2.0, 0.6]  # laid at its spot: its middle 2 m east, 0.5 m south
    assert plan["rows"][plans.WALLS_ITEM] == ["lamp"]
    assert names["KEEP CLEAR S 2"][6] == "zone" and plan["people"] == [[2.0, 1.5]]
    assert plan["elements"][0] == {"element": "a bench", "rows": ["bench"]}


def test_a_doors_leaf_on_a_row_this_concept_lacks_is_a_gap_and_its_door_keeps_its_lead(store, data):
    shed = json.loads((data / "plans/shed.json").read_text())
    leads = {"S": {**shed["leads"]["S"], "leaf": {"row": "door_leaf", "name": "shed_door"}},
             "N": {"to": "sealed", "why": "a blind wall", "leaf": {"row": "crate", "name": "crate_door"}}}
    (data / "plans/shed.json").write_text(json.dumps({**shed, "leads": leads}))
    picked(store, "shed")
    plan = plans.current(store, "shed")["plan"]
    assert plan["leads"]["S"] == {"to": "yard", "why": "its one door"}  # its leaf dropped: the plan stage maps it
    assert plan["leads"]["N"]["leaf"] == {"row": "crate", "name": "crate_door"}  # a row the reading holds stays
    assert [(gap["kind"], gap["row"]) for gap in plan["gaps"]] == [("leaf", "door_leaf")]


def test_his_edit_is_kept_as_his_own_and_checked(store):
    picked(store, "shed")
    plan = plans.current(store, "shed")["plan"]
    plan["items"][0][1] = 0.5
    plan["doors"][0] = ["E", 1.0, 0.9, "moved"]
    plans.edited(store, "shed", plan, "joey")
    shown = plans.current(store, "shed")
    assert shown["how"] == "edited" and shown["plan"]["items"][0][1] == 0.5
    assert shown["plan"]["doors"][0] == ["E", 1.0, 0.9, "DOOR to the yard"]  # moved, its words kept
    with pytest.raises(plans.Refused, match="keeps its doors"):
        plans.edited(store, "shed", {**plan, "doors": []}, "joey")
    with pytest.raises(plans.Refused, match="not a number"):
        plans.edited(store, "shed", {**plan, "items": [["X", "far", 0, 1, 1, None, "item"]]}, "joey")
    concepts.pick(store, "shed", None, "joey")  # unlocked: no plan counts
    assert plans.current(store, "shed") is None


def test_an_inside_place_waits_for_the_holders_plan_then_gets_its_shape_and_its_row(store):
    assert plans.holder_of(store, "shed") is None and not plans.made(store, "yard")
    plans.name_inside(store, "yard", ["Tool Hut"], "joey")
    picked(store, "yard")  # the pick is the approval: its inventory read, its plan is made
    holds = plans.current(store, "yard")["plan"]["holds"]
    assert [hold["place"] for hold in holds] == ["shed", "tool_hut"] and holds[0]["w"] == 4.0
    assert plans.made(store, "yard")  # the yard has no plan row: its plan shown is its plan made
    _, path = plans.shape_sent(store, "shed")[0]
    assert Image.open(path).size[0] > 100
    assert plans.holder_of(store, "shed") == {"holder": "yard", "row": None, "box": None, "view": None,
                                              "outline": [0.3, 0.3, 4.0, 3.0]}  # the yard's own ground holds it


def test_his_inside_places_and_rows_redo_what_follows(store, data):
    rows = [{"id": "barn", "name": "a barn", "anchor": "floor", "size": [8.0, 6.0, 5.0], "count": 1, "at": [],
             "box": [10, 20, 300, 200], "view": "v1"}]
    (data / "inventory/yard.json").write_text(json.dumps({"concept_pick": {"sha256": PICK}, "rows": rows}))
    picked(store, "yard")
    plan = plans.current(store, "yard")["plan"]
    plan["holds"] = [{**plan["holds"][0], "place": "loft", "row": "barn", "x": 2.0}]
    plans.edited(store, "yard", plan, "joey")
    assert plans.tree(store)["within"].get("loft") == "yard" and "shed" not in plans.tree(store)["within"]
    # the concept review reads the same: the loft's draw waits on the yard, its holder now
    assert concepts.above("loft", store) == "yard" and concepts.inside_of("yard", store) == ["loft"]
    assert concepts.step_refusal(store, "loft", "draw") == "waits for yard's scene inventory to be read"
    assert plans.holder_of(store, "loft") == {"holder": "yard", "row": "barn", "box": [10, 20, 300, 200],
                                              "view": "v1", "outline": [2.0, 0.3, 4.0, 3.0]}
    with pytest.raises(plans.Refused, match="no inventory row"):
        plans.edited(store, "yard", {**plan, "holds": [{**plan["holds"][0], "row": "silo"}]}, "joey")


def test_a_room_changed_on_the_holders_plan_puts_draws_on_it_out_of_date_and_flags_its_pick(store, monkeypatch):
    """Owner, 2026-10-21: a merge, move or resize of a room on the plan above means the room is drawn again; a place
    the plan no longer lays out is removed, never an outside place."""
    monkeypatch.setattr(concepts, "step_refusal", lambda store, place, step: None)
    picked(store, "yard")
    plan = plans.current(store, "yard")["plan"]
    drawn = {"place": "shed", "sha": PICK, "at": concepts.now(), "room": plans.room_of(store, "shed")}
    store.write_once("concepts/shed/draws/1.json", drawn)
    concepts.pick(store, "shed", PICK, "joey")
    store.write_once("concepts/shed/draws/2.json", {"place": "shed", "sha": "c" * 64, "base": PICK,
                                                    "at": concepts.now()})  # a Redraw with notes on it
    store.write_once("concepts/shed/draws/0.json", {"place": "shed", "sha": "d" * 64,
                                                    "at": "2026-10-01T00:00"})  # from before rooms were recorded
    assert drawn["room"]["w"] == 4.0 and not concepts.plan_changed(store, "shed")
    assert plans.moved_draws(store, "shed") == set()
    plans.edited(store, "yard", {**plan, "holds": [{**plan["holds"][0], "w": 6.0}]}, "joey")  # resized
    assert concepts.plan_changed(store, "shed")
    assert plans.moved_draws(store, "shed") == {PICK, "c" * 64, "d" * 64}  # the older one: a plan above made since
    assert plans.removed(store, plans.within_file()[0]) == []
    plans.edited(store, "yard", {**plan, "holds": []}, "joey")  # merged away
    assert plans.removed(store, plans.within_file()[0]) == ["shed"]


def test_a_reading_of_the_pick_is_the_inventory_its_rows_on_their_parents_and_its_boxes_the_holders(store, data):
    from score.review import reading
    (data / "inventory/yard.json").unlink()  # no file: the reading in the store is the inventory
    picked(store, "yard")
    assert plans.current(store, "yard") is None and not plans.made(store, "yard")
    rows = [{"id": "barn", "name": "a barn", "kind": "generate", "anchor": "ground", "size": "two storeys",
             "count": 1, "boxes": [[5, 6, 70, 80], [1, 1, 2, 2]]},
            {"id": "bell", "name": "a bell", "kind": "generate", "anchor": "on:barn", "size": "small", "count": 1}]
    reading.kept(store, {"place": "yard", "concept": PICK, "at": concepts.now(), "method": reading.METHOD,
                         "inventory": {"concept_pick": {"sha256": PICK}, "rows": rows}})
    plan = plans.current(store, "yard")["plan"]
    assert plan["rows"]["BARN 1"] == ["barn", "bell"] and plan["items"][0][3:5] == [1.0, 1.0]  # sizes in words: 1 m
    plan["holds"][0]["row"] = "barn"
    plans.edited(store, "yard", plan, "joey")
    assert plans.holder_of(store, "shed")["box"] == [5, 6, 70, 80]  # its surest SAM box
    assert plans.made(store, "yard") and concepts.holding_row(store, "shed") == "barn"  # the concept review's


def test_items_are_sized_by_their_reading_and_ordered_by_their_boxes_and_what_has_no_size_or_row_is_a_gap(store, data):
    from score.review import reading
    yard = json.loads((data / "plans/yard.json").read_text())
    (data / "plans/yard.json").write_text(json.dumps({**yard, "lamps": [{"name": "post", "row": "lamp_post"}],
                                                      "beams": [{"name": "far", "row": "mast", "place": "camp"}]}))
    (data / "inventory/yard.json").unlink()
    picked(store, "yard")
    rows = [{"id": "barn", "name": "a barn", "anchor": "ground", "size": [8.0, 6.0, 5.0], "size_words": "two storeys",
             "count": 1, "boxes": [[10, 10, 60, 35]]},
            {"id": "cart", "name": "a cart", "anchor": "ground", "size": [1.5, 1.0, 1.2],
             "size_words": "two strides long", "count": 1, "boxes": []},
            {"id": "rock", "name": "a rock", "anchor": "ground", "size": None, "size_words": "waist high",
             "count": 1, "boxes": [[0, 40, 50, 50]]}]
    reading.kept(store, {"place": "yard", "concept": PICK, "at": concepts.now(), "method": reading.METHOD,
                         "size": [100, 50], "inventory": {"concept_pick": {"sha256": PICK}, "rows": rows}})
    plan = plans.current(store, "yard")["plan"]
    items = {item[0]: item for item in plan["items"]}
    assert items["ROCK 1"][1:3] == [0.3, 0.3] and items["BARN 1"][1:5] == [1.6, 0.3, 8.0, 6.0]  # its metres, laid
    # along the walls after the rock, whose box stands left of its: a box orders, it is never projected (owner, 2026-10-21)
    assert items["CART 1"][3:5] == [1.5, 1.0]  # its metres, laid along the walls: no box
    assert items["ROCK 1"][3:5] == [1.0, 1.0]  # a box but no metres: SAM 3 gives where, never size
    assert [gap["words"] for gap in plan["gaps"]] == ["lamp post: no lamp post in this concept", "Rock 1: no size"]
    assert plan["lamps"] == [] and plan["beams"] == [{"name": "far", "row": "mast", "place": "camp"}]
    plan["items"] = [[*item[:3], 2.0, 2.0, *item[5:]] if item[0] == "ROCK 1" else item for item in plan["items"]]
    plans.edited(store, "yard", plan, "joey")  # he sized the rock: its gap is gone
    assert [gap["kind"] for gap in plans.current(store, "yard")["plan"]["gaps"]] == ["lamp"]


def test_the_plan_stage_reads_his_plan_and_drops_it_once_the_pick_goes(store, tmp_path):
    picked(store, "shed")
    assert plans.keep(store, ["shed", "yard"]) == (["shed"], ["shed"])  # the yard has no plan row: none kept
    kept = tmp_path / "kept/shed.json"
    written = json.loads(kept.read_text())
    assert written == {**plans.current(store, "shed")["plan"], "concept": {**written["concept"], "pick": PICK}}
    assert written["concept"]["picture"] == "{home}/design/concepts/shed.png"  # the picked concept, its input
    assert (tmp_path / "kept-concepts/shed.png").read_bytes() == store.objects.read_bytes(f"blobs/{PICK}")
    assert json.loads((tmp_path / "kept-inventory/shed.json").read_text())["rows"][0]["id"] == "bench"
    plan = plans.current(store, "shed")["plan"]
    plan["people"] = [[3.0, 2.0]]
    plans.edited(store, "shed", plan, "joey")
    assert json.loads(kept.read_text())["people"] == [[3.0, 2.0]]  # his edit, at once
    concepts.pick(store, "shed", None, "joey")
    assert plans.keep(store, ["shed"]) == ([], ["shed"]) and not kept.exists()
    assert not (tmp_path / "kept-inventory/shed.json").exists()
    assert not (tmp_path / "kept-concepts/shed.png").exists()


def test_a_correction_runs_only_inside_his_yes_and_keeps_the_answer_as_his_edit(store, monkeypatch):
    picked(store, "shed")
    asked = []

    def gemini(question, pictures):
        asked.append((question, len(pictures)))
        return 'Here: {"people": [[1.0, 1.0]]}'

    request = {"marks": [{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2, "note": "stand by the bench"}], "note": ""}
    with pytest.raises(compute.Refused):
        plans.revised(store, "shed", request, "joey", reviser=gemini)
    monkeypatch.setattr(plans, "revise_euros", lambda: 0.05)

    def run(argv, env, **named):
        monkeypatch.setenv("SCORE_SPEND_TICKET", env["SCORE_SPEND_TICKET"])
        record = plans.revised(store, argv[-3], json.loads(open(argv[-2]).read()), argv[-1], reviser=gemini)
        return subprocess.CompletedProcess(argv, 0, json.dumps({"how": record["how"]}) + "\n", "")

    assert web.plan_revise(store, "shed", request, 0.05, "joey", run=run) == {"how": "revised"}
    assert asked[0][1] == 2 and "stand by the bench" in asked[0][0]
    assert plans.current(store, "shed")["plan"]["people"] == [[1.0, 1.0]]
    with pytest.raises(review.Refused, match="not today's measured price"):
        web.plan_revise(store, "shed", request, 0.04, "joey", run=run)


def test_a_holder_with_no_outline_of_its_own_gets_one_round_its_inside_places_before_its_items(store, data):
    from score.review import reading
    (data / "plans/yard.json").unlink()  # a shell with no plan (the base): the shed, 4 x 3 m, is inside it
    assert plans.outline_from_inside(store, "yard") == (4.6, 3.6)
    assert reading.outline_of(store, "yard") == (4.6, 3.6)  # the reading sizes its rows against it
    assert reading.outline_of(store, "nowhere") is None
    picked(store, "yard")
    assert plans.current(store, "yard")["plan"]["w"] == 4.6
