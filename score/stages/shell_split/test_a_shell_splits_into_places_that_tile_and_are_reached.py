"""The shell-split row, free and local: a shell's plan split into inside places that tile its inside, are reached
through doors and keep their plan's bounds; each gate fails a broken split by name; an inside place's plan reads its
shell's split beside it; a shell with no split is a gap of its own. And the ship's shell (its hull at 46 m, the room
list of its floor plan, plan v7's lengths as bounds) split by the stage against the hand-made
data/definitions/ship_floor.json, every difference stated, never tuned away.

One test: one plans folder (the toy ship, a broken shell plan, a second shell naming the bridge, two shells holding
each other) read by shell_of, the plan row's `besides`, the gap route and the runner; then a table of splits (the toy
ship, broken copies of its split, a shell too tight for its sides, one too crowded for its rooms, the ship) each
judged by all three gates against the faults its row names.

Breaks, each applied once and seen red:
- The toy row's narrowest bunks (4 m less half the spine less the partition):
  score/stages/shell_split/_split.py:
    `widths = [interpolated(stations, along, column_of) - spine["wide"] / 2 - partition for along in alongs]`
    -> `widths = [interpolated(stations, along, column_of) for along in alongs]`
- Every toy-ship split byte for byte the same: score/stages/shell_split/_split.py:
    `"left_out": [span for span in left_out if span[1] - span[0] > 10 ** -ROUND], "places": laid}`
    -> `"left_out": [__import__("time").perf_counter()], "places": laid}`
- The "overlap" row: score/stages/shell_split/_gates.py: `if start < along - EPSILON:` -> `if False:`
- The "gap at the back" row: score/stages/shell_split/_gates.py: `elif along < back - EPSILON:` -> `elif False:`
- The "lab shut" row: score/stages/shell_split/_gates.py: `todo += [door["leads"] for door in by_place[place]["doors"]]`
    -> `todo += list(by_place)`
- The "door on no shared wall" row: score/stages/shell_split/_gates.py:
    `elif not shared_wall(item, other, door["along"]):` -> `elif False:`
- The "sides too short" row: score/stages/shell_split/_gates.py:
    `faults.append(f"{item['place']}: {item['long']} m long, outside its plan's {low} to {high} m")` -> `pass`
- The "crowded" row: score/stages/shell_split/_split.py: `if room_for < least - 1e-9:` -> `if False:`
- The runner's split made and accepted: score/stages/shell_split/__init__.py:
    `(out / "places" / f"{item['place']}.json").write_text(json.dumps({"outside_shell": shell, **item}, indent=1))`
    -> `pass`
- The bunks reading the toy ship's split: score/stages/shell_split/__init__.py:
    `return shell_chain(place, *shells_in(plans_read(PLANS)))[:1]` -> `return []`
- inner and outer refused: score/stages/shell_split/__init__.py:
    `raise ValueError(f"{place} holds itself through its shells: {[start, *chain, place]}")` -> `return chain`
- The bridge, named by two shells, refused: score/stages/shell_split/__init__.py: `        if place in twice:`
    -> `        if False:`
- The toy ship's missing split a gap: score/stages/complete/gaps/route.py: `    if shell_split.applies(place):`
    -> `    if False:`
- Rooms grown by their bounds (the runner's toy split tiles, the ship row): score/stages/shell_split/_split.py:
    `fraction = (length - least) / (most - least)` -> `fraction = 0.0`

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
    score/stages/shell_split/test_a_shell_splits_into_places_that_tile_and_are_reached.py
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
from score.stages.complete.gaps import fill, route  # noqa: E402
from score.store import Store  # noqa: E402

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


# The toy ship's sides too short for each other: stores and lab at most 5.5 m against the left side's 8 m at least.
TIGHT = {**TOY, "rooms": [*TOY["rooms"][:3], {**TOY["rooms"][3], "long": [2.0, 2.5]},
                          {**TOY["rooms"][4], "long": [2.0, 3.0]}, TOY["rooms"][5]]}
# A 15 m bridge and the rest at least do not fit the 20 m inside.
CROWDED = {**TOY, "rooms": [{**TOY["rooms"][0], "long": [15.0, 16.0]}, *TOY["rooms"][1:]]}
# The shells beside the toy ship in the plans folder: a plan with no room list, a second shell naming the bridge, and
# inner and outer, each split into the other.
BESIDE = {"broken": {"outline": []},
          "second": {**TOY, "rooms": [{"place": "bridge", "side": "whole", "long": [3.0, 4.0]}], "spine": None},
          "inner": {**TOY, "rooms": [{"place": "outer", "side": "whole", "long": [3.0, 4.0]}], "spine": None},
          "outer": {**TOY, "rooms": [{"place": "inner", "side": "whole", "long": [3.0, 4.0]}], "spine": None}}


def grown(split):
    """A shape grown 1 m into the next."""
    split["places"][2]["along"][1] += 1.0


def shortened(split):
    """The last shape of a lane stopped 1 m short of the inside's end."""
    max(split["places"], key=lambda item: item["along"][1])["along"][1] -= 1.0


def shut(split):
    """Every door to or from the lab taken out."""
    for item in split["places"]:
        item["doors"] = [door for door in item["doors"] if "lab" not in (door["leads"], item["place"])]


def moved(split):
    """The bunks' door led to the engines, which share no wall with it."""
    next(item for item in split["places"] if item["place"] == "bunks")["doors"][0]["leads"] = "engines"


def refusal(call):
    """The ValueError's words when `call` is refused, else None."""
    try:
        call()
    except ValueError as refused:
        return str(refused)
    return None


def folder():
    """A folder of the test's own in the run's temp folder (conftest's own_temp removes it at the run's end)."""
    return pathlib.Path(tempfile.mkdtemp())


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


# --- the ship's shell against its hand-made floor plan ------------------------------------------------------------

# Within this of the hand plan, at each end, a room counts as reproduced.
TOLERANCE = 0.5
# Every room the stage does not reproduce, and why: the hand plan's own choices the split's rules do not make.
DIFFERS = {
    "cockpit": "the hand plan starts the inside at 9.7 m, as far forward as 2.2 m clear (the owner's cockpit at the "
               "nose, 2026-10-21); the split starts where 2.6 m clear does, measured from the hull at the deck (lining "
               "off) at 11.7 m, and sizes the cockpit inside plan v7's bounds",
    "walkway": "it opens behind the cockpit, which ends sooner (above)",
    "storage": "the hand plan sizes each side room by its story; the split grows every room the same share of "
               "its bounds and starts sooner",
    "quarters": "as storage", "galley": "as storage",
    "engineroom": "the hand plan steps its floor up over the rising keel to 42.4 m; the split lays one deck, which "
                  "ends where the keel rises into the floor (35.9 m), and keeps the room inside plan v7's bounds",
}


def ship_outline(floor, ship_floor):
    """The hull's inside at the deck, every 0.1 m: the inner half width each side, the clear height to the hull's
    inner top, none where the keel rises into the floor's structure (ship_floor.py's own measures)."""
    hull, deck = ship_floor.hull_of(floor), floor["deck"]
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
    floor = ship_floor.read_floor()
    drawn = dict(floor["hull"]["drawn"]["rooms"])  # plan v7's rooms as drawn, carried with its hull
    drawn["ship's lock"] = drawn["airlock"]
    # navigation merged into the cockpit, storage reaching forward over its old place (the owner, 2026-10-21)
    drawn["cockpit and nav"] = drawn["cockpit"] + drawn["navigation room"]
    drawn["storage"] = drawn["storage"] + drawn["navigation room"]
    scale = floor["length"] / floor["hull"]["drawn"]["length"]
    sides = {"whole": "whole", "port": "left", "starboard": "right"}
    rooms = [{"place": room["place"], "name": room["name"], "side": sides[room["side"]],
              "long": [drawn[room["name"]], round(drawn[room["name"]] * scale, 3)]}
             for room in sorted(floor["rooms"], key=lambda room: room["y"][0])]
    hall = floor["walkway"].get("hall", [0.0, 0.0])  # none since navigation merged into the cockpit
    return floor, {"outline": ship_outline(floor, ship_floor),
                   "least": {"clear": floor["ceiling"], "wide": ship_floor.LEAST_DEEP},
                   "door": {"wide": floor["door"]["wide"], "tall": floor["door"]["tall"]},
                   "partition": floor["partition"],
                   "spine": {"place": "walkway", "name": "walkway", "wide": floor["walkway"]["wide"],
                             "hall": hall[1] - hall[0]},
                   "rooms": rooms}


def test_a_shell_splits_into_places_that_tile_and_are_reached(monkeypatch):
    """A shell's split tiles its inside, is reached and keeps its bounds; each gate names what a broken split breaks;
    rooms that cannot fit are refused; an inside place reads its shell's split beside its plan, a shell without its
    split is a gap the runner fills, and the ship's split states where it differs from the hand plan."""
    # One plans folder: the toy ship and the shells beside it, read as the environment's plans.
    root = folder()
    (root / "design").mkdir()
    plans = shell_plan(root / "design", TOY).parent
    for name, split in BESIDE.items():
        shell_plan(root / "design", {key: value for key, value in split.items() if value is not None}, name)
    monkeypatch.setattr(shell_split, "PLANS", plans)
    assert {place: shell_split.shell_of(place) for place in ("bunks", "hall", "toyship")} == {
        "bunks": ["toyship"], "hall": ["toyship"], "toyship": []}
    assert "holds itself" in (refusal(lambda: shell_split.shell_of("inner")) or "read")
    assert "more than one shell" in (refusal(lambda: shell_split.shell_of("bridge")) or "read")
    runner = stages.runner(store=Store.in_folder(folder()))
    assert list(runner.besides(runner.stages["plan"], "bunks")) == ["shell-split@toyship"]
    names = [row.name for row in stages.STAGES]
    assert names.index("plan") < names.index("rough-model") < names.index("shell-split")
    store = Store.in_folder(folder())
    assert fill.SHELL_SPLIT in route.missing(store, "toyship", None, None)
    assert fill.SHELL_SPLIT not in route.missing(store, "bunks", None, None)
    assert fill.place_step(fill.SHELL_SPLIT, "toyship", True) == ("shell-split@toyship", None)

    # The runner makes the gap's split after the shell's plan (the plan file and the plan row's output, two inputs).
    def make_plan(inputs, out, seed, params):
        (out / "plan.json").write_text((inputs["plan"]).read_text())

    plan_row = graph.Stage("plan", "place", make_plan, contracts.Contract("place-plan", 2, lambda out: []),
                           (checks.Check("mapped", lambda output, inputs, evidence: checks.Verdict(
                               "mapped", checks.PASS, "a toy plan")),), files={"plan": "{data}/plans/{place}.json"})
    world = graph.Environment("toy", 7, {"data": root / "design", "home": root})
    found = graph.Runner((plan_row, dataclasses.replace(stages.SHELL_SPLIT, applies=None)), world, store,
                         model_record=lambda kind: {"kind": kind}).run(["toyship"])
    assert found["shell-split@toyship"] == "made: pass, accepted automatically", found

    # Each split judged by every gate: (row, the shell's split, a break made in its split.json, the refusal's words,
    # {gate: words naming each of its faults}); a gate the row does not name passes.
    floor, ship = ship_split_plan()
    cases = [("toy", TOY, None, None, {}),
             ("overlap", TOY, grown, None, {"tiled": ("overlap",)}),
             ("gap at the back", TOY, shortened, None, {"tiled": ("nothing stands",)}),
             ("lab shut", TOY, shut, None, {"reached": ("lab: no way in through the doors",)}),
             ("door on no shared wall", TOY, moved, None,
              {"reached": ("no wall it shares with engines", "hall: its door to bunks has no door back")}),
             ("sides too short", TIGHT, None, None, {"tiled": ("nothing stands",), "bounded": ("stores:", "lab:")}),
             ("crowded", CROWDED, None, "do not fit", {}),
             ("ship", ship, None, None, {})]
    made_by_row, first = {}, None
    for row, split, broken, refused, faults in cases:
        if refused:
            assert refused in (refusal(lambda: made(copy.deepcopy(split))) or "split"), row
            continue
        out, inputs = made(copy.deepcopy(split))
        if split is TOY:
            first = first or (out / "split.json").read_text()
            assert (out / "split.json").read_text() == first, f"{row}: the same plan split differently"
        if broken:
            rewritten(out, broken)
        for name, verdict in verdicts(out, inputs).items():
            words = faults.get(name, ())
            assert verdict.answer == (checks.FAIL if words else checks.PASS), (row, verdict)
            assert all(any(word in finding for finding in verdict.findings) for word in words), (row, verdict)
            assert all(any(word in finding for word in words) for finding in verdict.findings), (row, verdict)
        made_by_row[row] = out

    # The toy ship: its inside from 1 m (the nose, 0.9 m in, too low) to 21 m; seven places, each defined with its
    # shell; a side room's narrowest the shell's 4 m half width less half the 1.5 m spine and the 0.1 m partition, a
    # whole room's the 8 m across, the spine its own 1.5 m.
    toy = layout(made_by_row["toy"])
    assert toy["span"] == [1.0, 21.0] and toy["left_out"] == [[0.0, 1.0]]
    by_place = {item["place"]: item for item in toy["places"]}
    assert sorted(by_place) == ["bridge", "bunks", "engines", "hall", "lab", "mess", "stores"]
    for place in by_place:
        definition = json.loads((made_by_row["toy"] / "places" / f"{place}.json").read_text())
        assert definition["outside_shell"] == "toyship" and definition["along"] == by_place[place]["along"]
    assert by_place["bunks"]["narrowest"] == round(4.0 - 0.75 - 0.1, 3)
    assert by_place["bridge"]["narrowest"] == 8.0 and by_place["hall"]["narrowest"] == 1.5

    # The ship against the hand plan: the same rooms on the same sides with the same doors, and exactly the rooms
    # DIFFERS states differing past TOLERANCE (every room still in its bounds: the ship row above).
    by_place = {item["place"]: item for item in layout(made_by_row["ship"])["places"]}
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
