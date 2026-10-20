"""The shell-split row, free and local: a shell's plan split into inside places that tile its inside, are reached
through doors and keep their plan's bounds; each gate fails a broken split by name; an inside place's plan reads its
shell's split beside it; a shell with no split is a hole of its own. And the ship's shell (its hull at 46 m, the room
list of its floor plan, plan v7's lengths as bounds) split by the stage against the hand-made
data/definitions/ship_floor.json, every difference stated, never tuned away.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/shell_split/shell_split_test.py
"""
import copy
import dataclasses
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks, contracts, graph, stages  # noqa: E402
from score.stages import shell_split  # noqa: E402
from score.stages.complete.holes import fill, route  # noqa: E402
from score.store import PROPS_HOME, Store  # noqa: E402

# A box-shaped shell 20 m long, 8 m across, 3 m clear; a nose 1 m deep too low to stand in.
OUTLINE = [[0.0, 4.0, 4.0, 1.0], [0.9, 4.0, 4.0, 1.0], [1.0, 4.0, 4.0, 3.0], [21.0, 4.0, 4.0, 3.0]]
TOY = {"outline": OUTLINE, "least": {"clear": 2.2, "wide": 1.5}, "door": {"wide": 0.9, "tall": 2.0},
       "partition": 0.1, "spine": {"place": "hall", "wide": 1.5, "hall": 1.0},
       "rooms": [{"place": "bridge", "name": "bridge", "side": "whole", "long": [3.0, 4.0]},
                 {"place": "bunks", "side": "left", "long": [4.0, 7.0]},
                 {"place": "mess", "side": "left", "long": [4.0, 7.0]},
                 {"place": "stores", "side": "right", "long": [4.0, 7.0]},
                 {"place": "lab", "side": "right", "long": [4.0, 7.0]},
                 {"place": "engines", "side": "whole", "long": [3.0, 5.0]}]}


def folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))


def shell_plan(root, split, name="toyship"):
    """A shell's plan with its split in a plans folder of its own; the plan's path."""
    plans = root / "plans"
    plans.mkdir(exist_ok=True)
    (plans / f"{name}.json").write_text(json.dumps({"title": name.upper(), "split": split}))
    return plans / f"{name}.json"


def made(split):
    """The row's output for a shell plan with this split, and its inputs."""
    root = folder()
    inputs = {shell_split.SHELL_PLAN: shell_plan(root, split)}
    out = root / "out"
    out.mkdir()
    shell_split.make(inputs, out, 0, {})
    assert shell_split.CONTRACT.faults(out) == []
    return out, inputs


def verdicts(out, inputs):
    return {check.name: checks.judge(check, out, inputs, None) for check in shell_split.CHECKS}


def layout(out):
    return json.loads((out / "split.json").read_text())


def rewritten(out, change):
    """The output with its split.json changed by `change` (a broken split for a gate to find)."""
    found = layout(out)
    change(found)
    (out / "split.json").write_text(json.dumps(found))
    return out


def test_a_shell_splits_into_inside_places_that_tile_are_reached_and_keep_their_bounds():
    out, inputs = made(TOY)
    found = verdicts(out, inputs)
    assert {name: verdict.answer for name, verdict in found.items()} == {
        "tiled": "pass", "reached": "pass", "bounded": "pass"}, found
    split = layout(out)
    assert split["span"] == [1.0, 21.0] and split["left_out"] == [[0.0, 1.0]]
    by_place = {item["place"]: item for item in split["places"]}
    assert sorted(by_place) == ["bridge", "bunks", "engines", "hall", "lab", "mess", "stores"]
    for place in by_place:
        definition = json.loads((out / "places" / f"{place}.json").read_text())
        assert definition["outside_shell"] == "toyship" and definition["along"] == by_place[place]["along"]
    assert by_place["bunks"]["narrowest"] == round(4.0 - 0.75 - 0.1, 3)  # from the spine's partition to the shell
    assert by_place["bridge"]["narrowest"] == 8.0 and by_place["hall"]["narrowest"] == 1.5


def test_the_split_is_the_same_every_time():
    first, _ = made(TOY)
    second, _ = made(copy.deepcopy(TOY))
    assert (first / "split.json").read_text() == (second / "split.json").read_text()


def test_overlapping_shapes_fail_tiled_by_name():
    out, inputs = made(TOY)
    rewritten(out, lambda split: split["places"][2]["along"].__setitem__(1, split["places"][2]["along"][1] + 1.0))
    verdict = verdicts(out, inputs)["tiled"]
    assert verdict.answer == checks.FAIL and any("overlap" in finding for finding in verdict.findings), verdict


def test_a_room_with_no_door_fails_reached_by_name():
    def shut(split):
        for item in split["places"]:
            item["doors"] = [door for door in item["doors"] if "lab" not in (door["leads"], item["place"])]
    out, inputs = made(TOY)
    verdict = verdicts(rewritten(out, shut), inputs)["reached"]
    assert verdict.answer == checks.FAIL and verdict.findings == ("lab: no way in through the doors",), verdict


def test_a_door_on_no_shared_wall_fails_reached():
    def moved(split):
        bunks = next(item for item in split["places"] if item["place"] == "bunks")
        bunks["doors"][0]["leads"] = "engines"
    out, inputs = made(TOY)
    verdict = verdicts(rewritten(out, moved), inputs)["reached"]
    assert verdict.answer == checks.FAIL and any("no wall it shares with engines" in finding
                                                 for finding in verdict.findings), verdict


def test_a_side_longer_than_the_other_can_grow_fails_bounded_by_name():
    tight = copy.deepcopy(TOY)
    tight["rooms"][3]["long"] = [2.0, 2.5]  # stores and lab at most 5.5 m against the left side's 8 m at least
    tight["rooms"][4]["long"] = [2.0, 3.0]
    out, inputs = made(tight)
    verdict = verdicts(out, inputs)["bounded"]
    assert verdict.answer == checks.FAIL, verdict
    assert {finding.split(":")[0] for finding in verdict.findings} == {"stores", "lab"}, verdict.findings


def test_rooms_that_cannot_fit_the_shell_are_refused():
    crowded = copy.deepcopy(TOY)
    crowded["rooms"][0]["long"] = [15.0, 16.0]
    try:
        made(crowded)
    except ValueError as refused:
        assert "do not fit" in str(refused)
    else:
        raise AssertionError("rooms longer than the shell were split")


def test_the_runner_makes_and_accepts_a_shells_split_after_its_plan():
    """Through the runner, as `score run` makes it: the shell's plan file and the plan row's output are two inputs."""
    root = folder()
    shell_plan(root, TOY)

    def make_plan(inputs, out, seed, params):
        (out / "plan.json").write_text((inputs["plan"]).read_text())

    plan_row = graph.Stage("plan", "place", make_plan, contracts.Contract("place-plan", 2, lambda out: []),
                           (checks.Check("mapped", lambda output, inputs, evidence: checks.Verdict(
                               "mapped", checks.PASS, "a toy plan")),), files={"plan": "{data}/plans/{place}.json"})
    row = dataclasses.replace(stages.SHELL_SPLIT, applies=None)
    world = graph.Environment("toy", 7, {"data": root})
    runner = graph.Runner((plan_row, row), world, Store.in_folder(folder()), model_record=lambda kind: {"kind": kind})
    found = runner.run(["toyship"])
    assert found["shell-split@toyship"] == "made: pass, accepted automatically", found


def with_plans(plans, check):
    """`check()` with shell_split reading `plans` as the environment's plans folder."""
    saved = shell_split.PLANS
    shell_split.PLANS = plans
    try:
        return check()
    finally:
        shell_split.PLANS = saved


def test_an_inside_place_reads_its_shells_split_beside_its_plan():
    plans = shell_plan(folder(), TOY).parent
    runner = stages.runner(store=Store.in_folder(folder()))
    plan_row = runner.stages["plan"]
    assert with_plans(plans, lambda: shell_split.shell_of("bunks")) == ["toyship"]
    assert with_plans(plans, lambda: shell_split.shell_of("hall")) == ["toyship"]
    assert with_plans(plans, lambda: shell_split.shell_of("toyship")) == []
    assert with_plans(plans, lambda: list(runner.besides(plan_row, "bunks"))) == ["shell-split@toyship"]
    names = [row.name for row in stages.STAGES]
    assert names.index("plan") < names.index("rough-model") < names.index("shell-split")  # plan, rough model, split
    assert runner.stages["shell-split"].after == {"plan": ("place-plan", 2)} and not runner.stages["shell-split"].paid


def test_a_place_that_holds_itself_is_refused():
    root = folder()
    loop = copy.deepcopy(TOY)
    loop["rooms"][0]["place"] = "outer"
    shell_plan(root, loop, "inner")
    outer = copy.deepcopy(TOY)
    outer["rooms"] = [{"place": "inner", "side": "whole", "long": [3.0, 4.0]}]
    del outer["spine"]
    shell_plan(root, outer, "outer")
    try:
        with_plans(root / "plans", lambda: shell_split.shell_of("inner"))
    except ValueError as refused:
        assert "holds itself" in str(refused)
    else:
        raise AssertionError("a shell inside its own inside place was read")


def test_one_bad_shell_plan_stops_only_the_places_it_names():
    root = folder()
    plans = shell_plan(root, TOY).parent
    shell_plan(root, {"outline": []}, "broken")  # no room list: its own node fails, no one else's plan
    twice = copy.deepcopy(TOY)
    twice["rooms"] = [{"place": "bridge", "side": "whole", "long": [3.0, 4.0]}]
    del twice["spine"]
    shell_plan(root, twice, "second")
    assert with_plans(plans, lambda: shell_split.shell_of("bunks")) == ["toyship"]
    try:
        with_plans(plans, lambda: shell_split.shell_of("bridge"))
    except ValueError as refused:
        assert "more than one shell" in str(refused)
    else:
        raise AssertionError("a place split from two shells was read")


def test_a_shell_without_its_split_is_a_hole_filled_by_the_row():
    plans = shell_plan(folder(), TOY).parent
    store = Store.in_folder(folder())
    missing = with_plans(plans, lambda: route.missing(store, "toyship", None, None))
    assert fill.SHELL_SPLIT in missing, missing
    assert with_plans(plans, lambda: fill.place_step(fill.SHELL_SPLIT, "toyship", True)) == (
        "shell-split@toyship", None)
    assert fill.SHELL_SPLIT not in with_plans(plans, lambda: route.missing(store, "bunks", None, None))


# --- the ship's shell against its hand-made floor plan ------------------------------------------------------------

# Within this of the hand plan, at each end, a room counts as reproduced.
TOLERANCE = 0.5
# Every room the stage does not reproduce, and why: the hand plan's own choices the split's rules do not make.
DIFFERS = {
    "cockpit": "the hand plan starts the inside at 13.5 m, its note saying the hull is under 2.6 m over the deck "
               "ahead of it; measured from the hull at the deck (lining off) the 2.6 m clear starts at 11.7 m, where "
               "the split starts, and the cockpit is sized inside plan v7's bounds",
    "walkway": "it opens behind the cockpit, which ends 2.7 m sooner (above)",
    "navigation": "the hand plan sizes each side room by its story; the split grows every room the same share of "
                  "its bounds and starts 2.7 m sooner",
    "quarters": "as navigation", "galley": "as navigation", "storage": "as navigation",
    "shiplock": "the hand plan stands it behind the side ring; the split knows no ring, only the room list's order",
    "engineroom": "the hand plan steps its floor up over the rising keel to 42.4 m; the split lays one deck, which "
                  "ends where the keel rises into the floor (35.9 m), and keeps the room inside plan v7's bounds",
}


def ship_outline(floor, ship, ship_floor):
    """The hull's inside at the deck, every 0.1 m: the inner half width each side, the clear height to the hull's
    inner top, none where the keel rises into the floor's structure (ship_floor.py's own measures)."""
    hull, deck = ship_floor.hull_plan(ship, floor), floor["deck"]
    stations = []
    for tenth in range(int(floor["length"] * 10) + 1):
        along = tenth / 10
        half = ship_floor.inner_half(hull, floor, along, deck)
        keel_in = ship_floor.station_at(hull, along)["keel"] > deck - floor["floor_depth"]
        clear = 0.0 if keel_in else ship_floor.inner_top(hull, floor, along) - deck
        stations.append([along, round(half, 3), round(half, 3), round(clear, 3)])
    return stations


def ship_split_plan():
    """The ship's shell as a split's input: its hull's outline at 46 m; the floor plan's room list (names, sides,
    order front to back, the walkway as the spine) without its lengths; each room's bounds plan v7's length, least as
    drawn (people keep their size) and most scaled with the hull (46 / 31 m); the airlock of v7 is the ship's lock."""
    sys.path.insert(0, str(REPO / "tools/props/scene"))
    import ship_floor
    floor, ship = ship_floor.read_floor(), json.loads(ship_floor.SHIP.read_text())
    drawn = {room["name"]: room["long"] for room in ship["rooms"]}
    drawn["ship's lock"] = drawn["airlock"]
    scale = ship["length"] / ship["drawn_length"]
    sides = {"whole": "whole", "port": "left", "starboard": "right"}
    rooms = [{"place": room["place"], "name": room["name"], "side": sides[room["side"]],
              "long": [drawn[room["name"]], round(drawn[room["name"]] * scale, 3)]}
             for room in sorted(floor["rooms"], key=lambda room: room["y"][0])]
    hall = floor["walkway"]["hall"]
    return floor, {"outline": ship_outline(floor, ship, ship_floor),
                   "least": {"clear": floor["ceiling"], "wide": ship_floor.LEAST_DEEP},
                   "door": {"wide": floor["door"]["wide"], "tall": floor["door"]["tall"]},
                   "partition": floor["partition"],
                   "spine": {"place": "walkway", "name": "walkway", "wide": floor["walkway"]["wide"],
                             "hall": hall[1] - hall[0]},
                   "rooms": rooms}


def test_the_ships_shell_splits_into_its_hand_plans_rooms_and_says_where_it_differs():
    floor, plan = ship_split_plan()
    out, inputs = made(plan)
    by_place = {item["place"]: item for item in layout(out)["places"]}
    hand = {space["place"]: space for space in floor["rooms"] + [floor["walkway"]]}
    assert sorted(by_place) == sorted(hand)
    sides = {"whole": "whole", "port": "left", "starboard": "right"}
    assert all(by_place[room["place"]]["side"] == sides[room["side"]] for room in floor["rooms"])
    places_by_name = {space.get("name", place): place for place, space in hand.items()}
    hand_doors = {place: sorted(places_by_name[door["leads"]] for door in space["doors"] if door["wall"] != "hull")
                  for place, space in hand.items() if place != "walkway"}
    split_doors = {place: sorted(door["leads"] for door in item["doors"])
                   for place, item in by_place.items() if place != "walkway"}
    assert split_doors == hand_doors, (split_doors, hand_doors)
    differs = {place: (hand[place]["y"], by_place[place]["along"]) for place in hand
               if any(abs(end - mine) > TOLERANCE for end, mine in zip(hand[place]["y"], by_place[place]["along"]))}
    for place, (theirs, mine) in sorted(differs.items()):
        print(f"{place}: hand {theirs}, split {mine}: {DIFFERS.get(place, 'NOT STATED')}")
    assert set(differs) == set(DIFFERS), sorted(set(differs) ^ set(DIFFERS))
    found = verdicts(out, inputs)
    assert found["tiled"].answer == checks.PASS and found["reached"].answer == checks.PASS, found
    # The side band runs from port's least (12 m) to starboard's most (12.91 m), so every room keeps plan v7's
    # bounds and the bands, at most 23.45 m, still fill the 22.7 m the span has less the hall.
    assert found["bounded"].answer == checks.PASS, found["bounded"]


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(REPO / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
