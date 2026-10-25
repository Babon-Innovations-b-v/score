"""The plan review (score/review/plans.py) on stand-in data, with a stand-in for Gemini and for the plan stage's run
(no call is made, nothing is spent, no row runs): a plan is drawn from the picked concept's inventory, each item tied
to its row; none before the inventory counts; his edits are kept as his own and checked; an inside place has its
holder, row and shape once the layer above's plan is made; his inside places and their rows redo what follows; a
reading in the store is the inventory; the plan stage reads his plan; a correction runs only inside his yes."""
import json
import subprocess

import pytest
from PIL import Image

from score import graph, review, stages
from score.adapters import compute
from score.review import concepts, plans, web
from score.store import Store

PICK = "a" * 64


# Each place's scene inventory as its reading of the pick gives it (score/review/reading.py): the design alone, no
# filed plan or inventory (retired with the old concepts, 2026-10-21).
ROWS = {"shed": [{"id": "bench", "name": "a bench", "anchor": "floor", "size": [2.0, 0.6, 0.9], "count": 1,
                  "at": [{"x": 0.0, "z": -1.0, "facing": 0}]},
                 {"id": "crate", "name": "a crate", "anchor": "floor", "size": [0.5, 0.5, 0.5], "count": 2, "at": []},
                 {"id": "vice", "name": "a vice", "anchor": "bench", "size": [0.2, 0.2, 0.2], "count": 1},
                 {"id": "lamp", "name": "a wall lamp", "anchor": "wall", "size": [0.3, 0.2, 0.3], "count": 1}],
        "yard": []}


@pytest.fixture
def data(tmp_path):
    """A holder `yard` holding `shed` (data/places/within.json, the one data file a design reads here)."""
    folder = tmp_path / "data"
    (folder / "places").mkdir(parents=True)
    (folder / "places/within.json").write_text(json.dumps({"within": {"shed": {"within": "yard"}}, "shells": {}}))
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


def read(store, place, rows, at=None, size=None):
    """A reading of the place's pick by today's method: its scene inventory (`rows`), its picture `size` in pixels
    where given (a row's boxes are pixels of it)."""
    from score.review import reading
    reading.kept(store, {"place": place, "concept": PICK, "at": at or concepts.now(), "method": reading.METHOD,
                         **({"size": size} if size else {}),
                         "inventory": {"concept_pick": {"sha256": PICK}, "rows": rows}})


def picked(store, place, rows=None, size=None):
    """The place's draw picked and read: `rows` its reading's rows, else ROWS' (none for a place it does not name)."""
    store.write_once(f"concepts/{place}/draws/1.json", {"place": place, "sha": PICK, "at": "2026-10-21T00:00"})
    concepts.pick(store, place, PICK, "joey")
    read(store, place, ROWS.get(place, []) if rows is None else rows, at="2026-10-21T00:01", size=size)


def written(store, place, plan):
    """The place's plan as plan_writing keeps a writing of its reading."""
    from score.review import plan_writing
    plan_writing.kept(store, {"place": place, "concept": PICK, "reading": plan_writing.reading_at(store, place),
                              "method": plan_writing.METHOD, "by": "test", "at": concepts.now(), "plan": plan})


def test_no_plan_before_the_inventory_counts_then_each_item_tied_to_its_row(store, data):
    assert plans.current(store, "shed") is None  # not picked: no inventory counts
    picked(store, "yard")  # the plan above lays the shed's room
    picked(store, "shed")
    shown = plans.current(store, "shed")
    plan = shown["plan"]
    # no filed plan (retired 2026-10-21): a bare one in its room on the plan above, 6 x 6 m with no plan of its own
    assert shown["how"] == "derived" and (plan["w"], plan["d"]) == (6.0, 6.0) and plan["doors"] == []
    names = {item[0]: item for item in plan["items"]}
    assert plan["rows"]["BENCH 1"] == ["bench", "vice"] and plan["rows"]["CRATE 2"] == ["crate"]
    assert names["BENCH 1"][1:5] == [2.0, 1.7, 2.0, 0.6]  # laid at its spot: its middle 1 m south of the room's
    assert plan["rows"][plans.WALLS_ITEM] == ["lamp"]
    assert plan["people"] == [[3.0, 3.0]]
    assert plan["elements"][0] == {"element": "a bench", "rows": ["bench"]}


def test_his_edit_is_kept_as_his_own_and_checked(store):
    picked(store, "yard")
    picked(store, "shed")
    written(store, "shed", {**plans.current(store, "shed")["plan"], "doors": [["S", 2.0, 0.9, "DOOR to the yard"]]})
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
    assert [hold["place"] for hold in holds] == ["shed", "tool_hut"] and holds[0]["w"] == 6.0  # no plan of its own
    assert plans.made(store, "yard")  # its plan shown is its plan made
    _, path = plans.shape_sent(store, "shed")[0]
    assert Image.open(path).size[0] > 100
    assert plans.holder_of(store, "shed") == {"holder": "yard", "row": None, "box": None, "view": None,
                                              "outline": [0.3, 0.3, 6.0, 6.0]}  # the yard's own ground holds it


def test_his_inside_places_and_rows_redo_what_follows(store, data):
    rows = [{"id": "barn", "name": "a barn", "anchor": "floor", "size": [8.0, 6.0, 5.0], "count": 1, "at": [],
             "box": [10, 20, 300, 200], "view": "v1"}]
    picked(store, "yard", rows)
    plan = plans.current(store, "yard")["plan"]
    plan["holds"] = [{**plan["holds"][0], "place": "loft", "row": "barn", "x": 2.0}]
    plans.edited(store, "yard", plan, "joey")
    assert plans.tree(store)["within"].get("loft") == "yard" and "shed" not in plans.tree(store)["within"]
    # the concept review reads the same: the loft's draw waits on the yard, its holder now
    assert concepts.above("loft", store) == "yard" and concepts.inside_of("yard", store) == ["loft"]
    assert concepts.step_refusal(store, "loft", "draw") is None  # the yard read and planned: the loft may be drawn
    assert plans.holder_of(store, "loft") == {"holder": "yard", "row": "barn", "box": [10, 20, 300, 200],
                                              "view": "v1", "outline": [2.0, 0.3, 6.0, 6.0]}
    with pytest.raises(plans.Refused, match="no inventory row"):
        plans.edited(store, "yard", {**plan, "holds": [{**plan["holds"][0], "row": "silo"}]}, "joey")


def test_a_room_adjoining_rooms_a_row_holds_is_held_by_that_row_over_one_it_only_overlaps(store, data):
    """Owner, 2026-10-21: the docking airlock just behind the engine room, its box over the crane, "is still part of
    the ship"; a room its row names (the hub's central_hub) or on its own floor keeps its own."""
    rows = [{"id": row, "name": row, "anchor": "floor", "size": [8.0, 6.0, 5.0], "count": 1, "at": []}
            for row in ("ship", "crane", "loft")]
    picked(store, "yard", rows)
    plan = plans.current(store, "yard")["plan"]
    room = {"x": 2.0, "y": 2.0, "w": 4.0, "d": 3.0}
    plan["holds"] = [{**room, "place": "shed", "row": "ship"}, {**room, "place": "cabin", "row": "ship", "y": -1.0},
                     {**room, "place": "dock", "row": "crane", "x": 3.0, "y": 5.15, "w": 2.0},  # 0.15 m behind it
                     {**room, "place": "loft", "row": "loft", "x": 6.1},  # beside it, its own row by its name
                     {**room, "place": "hut", "row": None, "y": 5.0, "x": 0.0, "w": 1.0}]
    held = {hold["place"]: hold["row"] for hold in plans.edited(store, "yard", plan, "joey")["plan"]["holds"]}
    assert held == {"shed": "ship", "cabin": "ship", "dock": "ship", "loft": "loft", "hut": None}


def test_a_room_changed_on_the_holders_plan_puts_draws_on_it_out_of_date_and_flags_its_pick(store, data, monkeypatch):
    """Owner, 2026-10-21: a merge, move or resize of a room on the plan above means the room is drawn again; a place
    the plan no longer lays out is removed, never an outside place, and has no stage line."""
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
    assert drawn["room"]["w"] == 6.0 and not concepts.plan_changed(store, "shed")
    assert plans.moved_draws(store, "shed") == set()
    plans.edited(store, "yard", {**plan, "holds": [{**plan["holds"][0], "w": 8.0}]}, "joey")  # resized
    assert concepts.plan_changed(store, "shed")
    assert plans.moved_draws(store, "shed") == {PICK, "c" * 64, "d" * 64}  # the older one: a plan above made since
    assert plans.removed(store, plans.within_file()[0]) == []
    read(store, "shed", ROWS["shed"])
    plans.edited(store, "shed", plans.current(store, "shed")["plan"], "joey")  # its design done: a place of the build
    world = graph.Environment("world1", 3, {"data": str(data)})
    assert stages.places(world, store) == ["yard", "shed"]  # the scene tree's order: the parent scene first
    plans.edited(store, "yard", {**plan, "holds": []}, "joey")  # merged away
    assert plans.removed(store, plans.within_file()[0]) == ["shed"]
    assert stages.places(world, store) == ["yard"]  # the build follows him: no stage line for it


def test_rewriting_a_parent_keeps_its_locked_childrens_rooms_and_only_his_edit_moves_them_or_hides(store, monkeypatch):
    """Owner, 2026-10-21: "get my concepts back ... i had alr locked them": a plan written again (its inventory read
    again) never moves a locked scene's room nor shows over his own edit; only his edit moves the room."""
    from score.review import plan_writing
    monkeypatch.setattr(concepts, "step_refusal", lambda store, place, step: None)
    picked(store, "yard")
    room = plans.room_of(store, "shed")
    store.write_once("concepts/shed/draws/1.json", {"place": "shed", "sha": PICK, "at": concepts.now(), "room": room})
    concepts.pick(store, "shed", PICK, "joey")
    plan = plans.current(store, "yard")["plan"]
    moved = {**plan, "holds": [{**room, "x": room["x"] + 3.0, "w": 9.0}]}
    plan_writing.kept(store, {"place": "yard", "concept": PICK, "reading": plan_writing.reading_at(store, "yard"),
                              "method": plan_writing.METHOD, "by": "test", "at": concepts.now(), "plan": moved})
    assert plans.current(store, "yard")["how"] == "written" and plans.room_of(store, "shed") == room
    assert not concepts.plan_changed(store, "shed")
    store.write_once("concepts/shed/draws/0.json", {"place": "shed", "sha": "d" * 64, "at": "2026-10-01T00:00"})
    concepts.pick(store, "shed", "d" * 64, "joey")  # locked on a draw from before rooms were recorded
    assert not concepts.plan_changed(store, "shed")  # a writing since moves no locked room
    plans.edited(store, "yard", {**plan, "holds": [{**room, "w": 6.0}]}, "joey")
    assert concepts.plan_changed(store, "shed")  # his edit does
    plan_writing.kept(store, {"place": "yard", "concept": PICK, "reading": plan_writing.reading_at(store, "yard"),
                              "method": plan_writing.METHOD, "by": "test", "at": concepts.now(), "plan": moved})
    shown = plans.current(store, "yard")
    assert shown["how"] == "edited" and shown["plan"]["holds"][0]["w"] == 6.0  # his edit over a newer writing
    assert shown["plan"]["gaps"][-1]["kind"] == "edited"


def test_a_scene_he_added_in_the_app_is_a_place_once_its_design_is_done(store, data, tmp_path):
    """A child scene he added on a plan (no file of it in the data) is a scene in design, no place, until its concept
    is locked, its inventory read and its plan written or edited; then the build lists it and its plan row reads its
    kept plan, with no hand edit (owner, 2026-10-21). Every scene is one: no plan is filed in the data (2026-10-21)."""
    picked(store, "yard")
    plan = plans.current(store, "yard")["plan"]
    plans.edited(store, "yard", {**plan, "holds": [*plan["holds"], {**plan["holds"][0], "place": "hut", "x": 0.0}]},
                 "joey")
    world = graph.Environment("world1", 3, {"data": str(data)})
    assert stages.places(world, store) == ["yard"]  # the shed and the hut in design: their concepts not locked
    picked(store, "hut")
    shown = plans.current(store, "hut")
    assert shown["how"] == "derived" and stages.places(world, store) == ["yard"]  # its plan not written
    assert plans.keep(store, ["hut"]) == ([], []) and not stages.plan_written("hut")
    plans.edited(store, "hut", shown["plan"], "joey")
    assert stages.places(world, store) == ["yard", "hut"]
    assert plans.keep(store, ["hut"]) == (["hut"], []) and (tmp_path / "kept/hut.json").is_file()  # kept at his edit
    assert stages.plan_written("hut") and stages.PLAN.files("hut")["plan"] == "{home}/design/plans/{place}.json"


def test_a_parent_scene_with_no_data_of_its_own_is_a_place_once_its_design_is_done(store, data, tmp_path):
    """A parent scene holding others with no file of its own in the data (the Moon base, a shell) is a place of the
    batch once its design is done, listed before the scenes it holds, and the sync keeps its plan where the plan stage
    and the scene tree read it."""
    (data / "places/within.json").write_text(json.dumps({"within": {"shed": {"within": "yard"},
                                                                    "yard": {"within": "farm"}},
                                                         "shells": {"farm": {"name": "Farm"}}}))
    world = graph.Environment("world1", 3, {"data": str(data)})
    picked(store, "yard")
    plans.edited(store, "yard", plans.current(store, "yard")["plan"], "joey")
    assert stages.places(world, store) == ["yard"]  # the farm in design: no place yet
    picked(store, "farm")
    shown = plans.current(store, "farm")
    assert shown["how"] == "derived" and [hold["place"] for hold in shown["plan"]["holds"]] == ["yard"]
    assert stages.places(world, store) == ["yard"]  # its plan not written
    plans.edited(store, "farm", shown["plan"], "joey")
    assert stages.places(world, store) == ["farm", "yard"]  # the parent scene first
    assert plans.keep(store, ["farm"]) == (["farm"], []) and (tmp_path / "kept/farm.json").is_file()  # at his edit


def test_overlapped_rooms_are_one_shared_room_and_a_box_dropped_in_a_room_a_thing_in_it(store):
    """Owner, 2026-10-21: two rooms overlapped on the plan above are one shared room named from both; the add-scene
    box dropped inside a room is a thing kept with that room, no scene of its own, named with its spot in the room's
    draw wording; either changes the room, so its draws are drawn again. A room he left alone stays as it was."""
    plans.name_inside(store, "yard", ["tool hut"], "joey")
    picked(store, "yard")
    plan = plans.current(store, "yard")["plan"]
    shed = plans.room_of(store, "shed")
    plans.edited(store, "yard", plan, "joey")  # kept as laid: no key added to a room he did not touch
    assert plans.room_of(store, "shed") == shed
    store.write_once("concepts/shed/draws/1.json", {"place": "shed", "sha": PICK, "at": concepts.now(), "room": shed})
    merged = {**shed, "w": 8.0, "d": 3.0, "name": "Shed and tool hut",
              "things": [{"name": "workbench", "x": 3.0, "y": 1.0, "w": 2.0, "d": 1.0},
                         {"name": "lathe", "x": 6.5, "y": 0.2, "w": 1.0, "d": 0.6}]}
    plans.edited(store, "yard", {**plan, "holds": [merged]}, "joey")
    assert plans.tree(store)["within"] == {"shed": "yard"}  # the tool hut is no scene any more
    assert plans.room_of(store, "shed")["things"][0] == {"name": "workbench", "x": 3.0, "y": 1.0, "w": 2.0, "d": 1.0}
    assert plans.moved_draws(store, "shed") == {PICK}
    assert concepts.room_name(store, "shed") == "shed and tool hut"
    assert concepts.thing_words(store, "shed") == ("Standing in it: workbench in the middle; lathe in the north-east "
                                                   "corner.")
    assert plans.room_edits(plan, plans.current(store, "yard")["plan"])[0] == \
        "made the scene shed one shared room called Shed and tool hut"
    with pytest.raises(plans.Refused, match="has no name"):
        plans.edited(store, "yard", {**plan, "holds": [{**merged, "things": [{"x": 1, "y": 1, "w": 1, "d": 1}]}]}, "joey")


def test_a_reading_of_the_pick_is_the_inventory_its_rows_on_their_parents_and_its_boxes_the_holders(store, data):
    store.write_once("concepts/yard/draws/1.json", {"place": "yard", "sha": PICK, "at": "2026-10-21T00:00"})
    concepts.pick(store, "yard", PICK, "joey")  # picked, not read yet: no inventory, no plan
    assert plans.current(store, "yard") is None and not plans.made(store, "yard")
    rows = [{"id": "barn", "name": "a barn", "kind": "generate", "anchor": "ground", "size": "two storeys",
             "count": 1, "boxes": [[5, 6, 70, 80], [1, 1, 2, 2]]},
            {"id": "bell", "name": "a bell", "kind": "generate", "anchor": "on:barn", "size": "small", "count": 1}]
    read(store, "yard", rows)
    plan = plans.current(store, "yard")["plan"]
    assert plan["rows"]["BARN 1"] == ["barn", "bell"] and plan["items"][0][3:5] == [1.0, 1.0]  # sizes in words: 1 m
    plan["holds"][0]["row"] = "barn"
    plans.edited(store, "yard", plan, "joey")
    assert plans.holder_of(store, "shed")["box"] == [5, 6, 70, 80]  # its surest SAM box
    assert plans.made(store, "yard") and concepts.holding_row(store, "shed") == "barn"  # the concept review's


def test_items_are_sized_by_their_reading_and_ordered_by_their_boxes_and_what_has_no_size_or_row_is_a_gap(store, data):
    rows = [{"id": "barn", "name": "a barn", "anchor": "ground", "size": [3.0, 2.0, 5.0], "size_words": "two storeys",
             "count": 1, "boxes": [[10, 10, 60, 35]]},
            {"id": "cart", "name": "a cart", "anchor": "ground", "size": [1.5, 1.0, 1.2],
             "size_words": "two strides long", "count": 1, "boxes": []},
            {"id": "rock", "name": "a rock", "anchor": "ground", "size": None, "size_words": "waist high",
             "count": 1, "boxes": [[0, 40, 50, 50]]}]
    picked(store, "yard", rows, size=[100, 50])
    plan = plans.current(store, "yard")["plan"]
    items = {item[0]: item for item in plan["items"]}
    assert items["ROCK 1"][1:3] == [0.3, 0.3] and items["BARN 1"][1:5] == [1.6, 0.3, 3.0, 2.0]  # its metres, laid
    # along the walls after the rock, whose box stands left of its: a box orders, it is never projected (owner, 2026-10-21)
    assert items["CART 1"][3:5] == [1.5, 1.0]  # its metres, laid along the walls: no box
    assert items["ROCK 1"][3:5] == [1.0, 1.0]  # a box but no metres: SAM 3 gives where, never size
    assert [gap["words"] for gap in plan["gaps"]] == ["Rock 1: no size"]
    plan["items"] = [[*item[:3], 2.0, 2.0, *item[5:]] if item[0] == "ROCK 1" else item for item in plan["items"]]
    plans.edited(store, "yard", plan, "joey")  # he sized the rock: its gap is gone
    assert plans.current(store, "yard")["plan"]["gaps"] == []


def test_the_plan_stage_reads_his_plan_and_drops_it_once_the_pick_goes(store, tmp_path):
    picked(store, "yard")
    picked(store, "shed")
    written(store, "shed", plans.current(store, "shed")["plan"])  # its plan written: its design done
    assert plans.keep(store, ["shed", "yard"]) == (["shed"], ["shed"])  # the yard's plan only derived: none kept
    kept = tmp_path / "kept/shed.json"
    kept_plan = json.loads(kept.read_text())
    assert kept_plan == {**plans.current(store, "shed")["plan"], "concept": {**kept_plan["concept"], "pick": PICK}}
    assert kept_plan["concept"]["picture"] == "{home}/design/concepts/shed.png"  # the picked concept, its input
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
    picked(store, "yard")
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


def test_a_correction_with_no_note_sends_his_kept_edits_and_with_none_is_refused_before_any_spend(store, monkeypatch):
    picked(store, "yard")
    picked(store, "shed")
    monkeypatch.setattr(plans, "revise_euros", lambda: 0.05)
    bare = {"marks": [], "context_marks": [], "note": ""}
    with pytest.raises(plans.Refused, match="no note to correct the plan by"):
        web.plan_revise(store, "shed", bare, 0.05, "joey", run=None)  # nothing changed: no yes written
    assert not list((store.cache / plans.AREA / "asked").glob("*.json"))
    plan = plans.current(store, "shed")["plan"]
    plan["items"] = [[item[0], item[1] + 1.0, *item[2:]] for item in plan["items"][:1]] + plan["items"][1:]
    plans.edited(store, "shed", plan, "joey")
    note = plans.note_of(store, "shed", bare)
    assert note.startswith("I changed the plan by hand: item ") and plan["items"][0][0] in note
    assert plans.note_of(store, "shed", {**bare, "note": "wider door"}) == "wider door"


def test_a_holder_with_no_outline_of_its_own_gets_one_round_its_inside_places_before_its_items(store, data):
    from score.review import reading
    # a holder with no outline of its own (the base): the shed, 6 x 6 m with no plan of its own, is inside it
    assert plans.outline_from_inside(store, "yard") == (6.6, 6.6)
    assert reading.outline_of(store, "yard") == (6.6, 6.6)  # the reading sizes its rows against it
    assert reading.outline_of(store, "nowhere") is None
    picked(store, "yard")
    assert plans.current(store, "yard")["plan"]["w"] == 6.6


def test_a_spot_takes_its_child_scenes_own_plan_size_centred_where_it_sat_and_says_so(store):
    """Owner, 2026-10-25 ("the framework should be able to solve [it] agnosticly"): a child scene's own plan is drawn
    from its own concept at its own scale, the holder's spot says where it sits; they agree before any paid work."""
    rows = [{"id": "barn", "name": "a barn", "anchor": "floor", "size": [8.0, 6.0, 5.0], "count": 1, "at": []},
            {"id": "cart", "name": "a cart", "anchor": "floor", "size": [1.0, 1.0, 1.0], "count": 1, "at": []}]
    picked(store, "yard", rows)
    plan = plans.current(store, "yard")["plan"]
    plan["w"] = plan["d"] = 30.0
    plan["holds"] = [{"place": "shed", "row": None, "x": 10.0, "y": 10.0, "w": 6.0, "d": 6.0}]
    plan["items"] = [["CART 1", 13.0, 7.5, 1.0, 1.0, None, "item"]]  # clear of the spot, not of the shed's own size
    plans.edited(store, "yard", plan, "joey")
    held = plans.current(store, "yard")["plan"]
    assert held["holds"][0]["w"] == 6.0 and not [gap for gap in held["gaps"] if gap["kind"] == "held"]
    store.write_once("concepts/shed/draws/0.json", {"place": "shed", "sha": "b" * 64, "at": "2026-10-20T00:00",
                                                    "room": held["holds"][0]})  # drawn on the spot as it was
    picked(store, "shed")
    written(store, "shed", {**plans.current(store, "shed")["plan"], "w": 4.0, "d": 10.0})
    fitted = plans.current(store, "yard")["plan"]
    assert {key: fitted["holds"][0][key] for key in "xywd"} == {"x": 11.0, "y": 8.0, "w": 4.0, "d": 10.0}
    assert fitted["items"][0][1:5] == [13.0, 7.0, 1.0, 1.0]  # pushed north off the shed, the shortest way
    assert [gap["item"] for gap in fitted["gaps"] if gap["kind"] == "held"] == ["shed", "CART 1"]
    assert plans.moved_draws(store, "shed") == set()  # its own size is no move of its room
