"""A scene record is written from its design alone, on a plan of its own (a small shed beside a yard on a site): its
plan maps, and an item with no rows, a door that says nowhere it leads and a sealed door the layout leaves open each
fail `mapped`; a written plan with no corner takes its outline; the record holds the shell cut round its door, its
stair, a light over its lamp, the sky from the physics (on Mars its dusty day sky, inside too), the places its doors lead to and its backdrop rows are shown
from, every object at its plan item waiting on its model, a row the plan lays only against its edge past it, a far
row far off, each object carrying what holds it (its opening, its wall, its holder), an arched rib as a band, a light where a tower or a glowing row stands, and each part the scene
library's surface; its gates fail a filled door, a moved lamp and a door to no place. Every spot is worked out by hand from the plans below.

Each test names the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest
    score/stages/scene_record/test_a_scene_record_is_written_from_its_design.py
"""
import json
import math
import pathlib
import sys
import tempfile
import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
from score.stages.scene_record import gates, plan  # noqa: E402

SHED = {"title": "SHED", "w": 8.0, "d": 6.0, "corner": 1.0, "height": "walls 3 m, dome rising 1 m",
        "doors": [["N", 4.0, 1.2, "HATCH N, 1.2 x 2.1 m"], ["S", 4.0, 2.0, "BIG DOOR, 2 x 3 m"]],
        "items": [["BENCH", 1.0, 1.0, 2.0, 0.6, None, "item"], ["DRIVE LANE", 3.0, 3.0, 2.0, 2.0, None, "zone"]],
        "people": [[4.0, 3.0]],
        "leads": {"N": {"to": "yard", "why": "a hatch onto the yard"}, "S": {"to": "outside", "why": "the big door"}},
        "rows": {"BENCH": ["bench"], "DRIVE LANE": []},
        "elements": [{"element": "a bench", "rows": ["bench"]}]}
INVENTORY = {"scene": "shed", "rows": [{"id": "bench", "name": "a bench", "anchor": "floor", "size": [2.0, 0.6, 0.9],
                                        "count": 1}],
             "room": {"layout": {"open": ["north", "south"]}}}


# The yard: 20 x 12 m, its gate on its south wall leading to the shed.
YARD = {"title": "YARD", "w": 20.0, "d": 12.0, "leads": {},
        "openings": [{"kind": "gate", "at": [10.0, 12.0], "wide": 1.2, "angle": 0.0, "sill": 0.0, "to": "shed"}]}


def made(folder, record, yard=YARD):
    """plan@shed made into `folder` from `record`, as the table hands it (its kit the plan itself: plan_as_kit)."""
    folder = pathlib.Path(folder)
    plans = folder / "plans"
    plans.mkdir()
    (plans / "yard.json").write_text(json.dumps(yard))
    (plans / "shed.json").write_text(json.dumps(record))
    (folder / "inventory.json").write_text(json.dumps(INVENTORY))
    inputs = {"plan": plans / "shed.json", "kit": plans / "shed.json", "plans": plans,
              "inventory": folder / "inventory.json"}
    out = folder / "plan"
    out.mkdir()
    plan.make(inputs, out, 0, {})
    assert plan.plan_faults(out) == []
    return out, inputs


def test_a_plan_maps_and_faults_fail():
    """The shed's plan maps, its doors leading to the yard and outside; an item with no rows, a door that says nowhere
    it leads and a sealed door the layout leaves open each fail `mapped` by name.
    Break: score/stages/scene_record/plan.py: `return [f"{name} says nowhere it leads, or not why"]` -> `return []`
    Break: score/stages/scene_record/plan.py:
        `found.append(f"{name} is sealed but the room layout leaves it open (no leaf shuts it)")` -> `pass`
    Its `held` gate passes it, and fails a person spot or an item drawn outside its box (the hangar's workers 3.8 m
    past its wall, the garage's pipes 5 m out: the audit of 2026-11-04), never a pipe drawn on its wall's line; two
    overlapping holds and a place held once that more doors lead to than lead back (the base's one tube) fail too.
    Break: score/stages/scene_record/plan.py: `if not within([float(spot[0]), float(spot[1]), 0.0, 0.0], outer):` ->
        `if False:`
    Break: score/stages/scene_record/plan.py: `return within([x + reach, y + reach,` -> `return True or within([x + reach, y + reach,`
    Break: score/stages/scene_record/plan.py: `if depth > EDGE:` -> `if False:`
    Break: score/stages/scene_record/plan.py: `if leading > back:` -> `if False:`
    A place held several times stands once a hold, each instance by itself (#72, the base's tubes): a tube held
    turned and stretched meets the hub's door and the lab's at its two ends, its own leads renamed by its hold; a
    door naming the tube and not its instance, a hold another size than its plan laid in it, and a turn of 360 degrees
    fail by name. A hold turns any angle the concept needs (the base's tubes off the hub's diagonal facets): a tube
    turned 315 degrees from the hub's corner door to the lab's, its box over the hub's box and the lab's but its
    outline over neither (overlaps judged on outlines), the hub's two doors to `tube` each named by its spot; the lab,
    every door of it on a floor 1 m over its lower one, sunk 1 m so its door meets the tube's.
    Break: score/stages/scene_record/plan.py: `laid = [laid_outline(hold, (held.get(name_of(hold)) or (None, None))[1]) for hold in holds]` ->
        `laid = [laid_outline(hold) for hold in holds]`
    Break: score/stages/scene_record/plan.py: `return round(math.cos(turn), 12), round(math.sin(turn), 12)` ->
        `return round(math.cos(turn)), round(math.sin(turn))`
    Break: score/stages/scene_record/plan.py: `return f"{opening.get('to')}@{float(opening['at'][0]):g},{float(opening['at'][1]):g}"` ->
        `return None`
    Break: score/stages/scene_record/plan.py: `sunk = {name: -sunk_by(plan) for name, (_, plan) in held.items()}` ->
        `sunk = {name: 0.0 for name in held}`
    Break: score/stages/scene_record/plan.py: `return middle + np.array([cos * across - sin * along, sin * across + cos * along])` ->
        `return middle + np.array([across, along])`
    Break: score/stages/scene_record/plan.py: `found[name_of(hold)] = (hold, as_held(hold, read(path)))` ->
        `found[name_of(hold)] = (hold, read(path))`
    Break: score/stages/scene_record/plan.py: `if opening.get("kind") in DOORWAYS and to in instances and to not in held:` -> `if False:`
    Break: score/stages/scene_record/plan.py: `if abs(wide - hold["w"]) > EDGE or abs(deep - hold["d"]) > EDGE:` -> `if False:`
    Break: score/stages/scene_record/writer.py: `own = np.asarray(met[0]["door"]["at"], float) + unturned(hold, there - met[0]["spot"])` ->
        `own = np.asarray(met[0]["door"]["at"], float)`
    Two doors on one wall lead each by its own lead, `<side>:<along>` over its side's (the walkway's galley and
    quarters doors, 2026-11-05), and the openings gate finds each its doorway nearest along.
    Break: score/stages/scene_record/plan.py: `return leads.get(f"{side}:{float(at):g}") or leads.get(` ->
        `return leads.get(`
    Break: score/stages/scene_record/gates.py: `key=lambda pair: abs(float(pair[1]["at"][0 if where in ("N", "S") else 1]) - float(along)))` ->
        `key=lambda pair: 0.0)`
    A record's doorways lead where its own hold leads them, and its neighbours' doors lead back to its hold's name
    (2026-11-06: the base's tube, the airlock).
    Break: score/stages/scene_record/writer.py held_design: `return (place_plan.as_held(own, design), place_plan.name_of(own)) if own else (design, place)` ->
        `return design, place`"""
    with tempfile.TemporaryDirectory() as folder:
        out, inputs = made(folder, SHED)
        found = plan.judge_mapped(out, inputs, None)
        assert found.answer == checks.PASS, (found.reason, found.findings)
        assert [door["leads"] for door in json.loads((out / "plan.json").read_text())["doors"]] == ["yard", "outside"]
        assert plan.judge_held(out, inputs, None).answer == checks.PASS
        (pathlib.Path(folder) / "plans/shed.json").write_text(json.dumps(
            {**SHED, "people": [[4.0, 3.0], [9.5, 3.0]], "items": [*SHED["items"], ["PIPE", -5.0, 3.0, 10.0, 0.1, None,
                                                                                     "item"],
                                                                 ["DUCT", -0.1, 4.0, 0.2, 1.0, None, "item"]]}))
        found = plan.judge_held(out, inputs, None)
        assert found.answer == checks.FAIL and found.findings == (
            "shed's person spot 2 [9.5, 3.0] lies outside its 8.0 x 6.0 m plan",
            "shed's item 'PIPE' [-5.0, 3.0, 10.0, 0.1] lies outside its 8.0 x 6.0 m plan"), found.findings
    holds = [{"place": "hub", "x": 0.0, "y": 0.0, "w": 10.0, "d": 10.0}, {"place": "tube", "x": 9.0, "y": 2.0, "w": 4.0,
                                                                          "d": 4.0}]
    assert plan.overlap_faults({"holds": holds}) == ["the outlines of hub and tube overlap, 0.97 m thick"]
    door = {"kind": "door", "at": [0.0, 0.0], "to": "tube"}
    held = {"hub": (holds[0], {"openings": [door, door]}), "tube": (holds[1], {"openings": [{**door, "to": "hub"}]})}
    assert plan.once_faults(held) == ["tube is held once, but 2 doors of its siblings lead to it and 1 of its own "
                                      "lead back"]
    with tempfile.TemporaryDirectory() as folder:
        plans, out = pathlib.Path(folder) / "plans", pathlib.Path(folder) / "out"
        plans.mkdir(), out.mkdir()
        (out / "plan.json").write_text(json.dumps({"place": "base"}))
        # the tube's plan: 2 x 4 m, its north end to the hub, its south end to the greenhouse; held turned 90 degrees
        # (north to east) and stretched to 6 m, its hub end leading to the lab (east, x 16) and its greenhouse end to
        # the hub (west, x 10), both at y 5
        tube = {"w": 2.0, "d": 4.0, "shape": "tube", "openings": [{"kind": "opening", "at": [1.0, 0.0], "to": "hub"},
                                                                  {"kind": "opening", "at": [1.0, 4.0], "to": "greenhouse"}]}
        hub = {"w": 10.0, "d": 10.0, "openings": [{"kind": "door", "at": [10.0, 5.0], "to": "tube#1"}]}
        lab = {"w": 4.0, "d": 4.0, "openings": [{"kind": "door", "at": [0.0, 2.0], "to": "tube#1"}]}
        instance = {"place": "tube", "instance": "tube#1", "turn": 90, "leads": {"hub": "lab", "greenhouse": "hub"},
                    "x": 10.0, "y": 4.0, "w": 6.0, "d": 2.0}
        base = {"w": 20.0, "d": 10.0, "holds": [{"place": "hub", "x": 0.0, "y": 0.0, "w": 10.0, "d": 10.0}, instance,
                                                {"place": "lab", "x": 16.0, "y": 3.0, "w": 4.0, "d": 4.0}]}
        for name, own in (("tube", tube), ("hub", hub), ("lab", lab), ("base", base)):
            (plans / f"{name}.json").write_text(json.dumps(own))
        found = plan.judge_held(out, {"plans": plans}, None)
        assert found.answer == checks.PASS, found.findings
        assert plan.on_holder(instance, tube, [1.0, 0.0]).tolist() == [16.0, 5.0]
        # the hub's record stands the instance its place's stage, its middle 3 m east of the hub's door, stretched
        stood = gates.writer.sibling("hub", hub, base, "tube#1", plans)
        assert (stood["name"], stood["stage"], stood["instance"], stood["at"], stood["scale"]) == (
            "tube_1", "tube", "tube#1", [8.0, 0.0, 0.0], [1.0, 1.0, 1.5]), stood
        hub["openings"].append({"kind": "door", "at": [5.0, 10.0], "to": "tube"})
        (plans / "hub.json").write_text(json.dumps(hub))
        base["holds"][1] = {**instance, "d": 3.0}
        (plans / "base.json").write_text(json.dumps(base))
        assert plan.judge_held(out, {"plans": plans}, None).findings[:2] == (  # then its doors, 0.5 m off
            "tube#1's hold is 6 x 3 m, its plan laid in it 6 x 2 m (turned 90)",
            "hub's door to tube at [5.0, 10.0] names no instance of it (tube#1)")
        base["holds"][1] = {**instance, "turn": 360}
        (plans / "base.json").write_text(json.dumps(base))
        try:
            plan.judge_held(out, {"plans": plans}, None)
            raise AssertionError("a hold turned 360 degrees was judged")
        except ValueError as refused:
            assert "turns 360 degrees" in str(refused)
        # the tube turned 315 degrees (its run south-east) from the hub's corner door (10, 10) 4 m to the lab's door at
        # its corner; its box is 4.24 m square round its middle (11.41, 11.41)
        hub = {"w": 10.0, "d": 10.0, "openings": [{"kind": "door", "at": [10.0, 10.0], "to": "tube"},
                                                  {"kind": "door", "at": [0.0, 5.0], "to": "tube"}]}
        lab = {"w": 4.0, "d": 4.0, "levels": [{"height": 0.0}, {"height": 1.0}],
               "openings": [{"kind": "door", "at": [0.0, 0.0], "sill": 1.0, "to": "tube"}]}
        side = 6.0 / math.sqrt(2.0)
        instance = {"place": "tube", "instance": "tube#1", "turn": 315, "leads": {"greenhouse": "lab"},
                    "x": 10.0 + 2.0 ** 0.5 - side / 2, "y": 10.0 + 2.0 ** 0.5 - side / 2, "w": side, "d": side}
        corner = 10.0 + 4.0 / math.sqrt(2.0)
        base = {"w": 20.0, "d": 20.0, "holds": [
            {"place": "hub", "x": 0.0, "y": 0.0, "w": 10.0, "d": 10.0, "leads": {"tube@10,10": "tube#1", "tube@0,5": "outside"}},
            instance, {"place": "lab", "x": corner, "y": corner, "w": 4.0, "d": 4.0, "leads": {"tube": "tube#1"}}]}
        for name, own in (("hub", hub), ("lab", lab), ("base", base)):
            (plans / f"{name}.json").write_text(json.dumps(own))
        assert np.allclose(plan.on_holder(instance, tube, [1.0, 4.0]), [corner, corner])
        assert len(plan.overlap_faults(base)) == 2  # by their boxes the tube overlaps both
        assert plan.levels_of(plan.held_plans(base, plans)) == {"hub": 0.0, "tube#1": 0.0, "lab": -1.0}
        found = plan.judge_held(out, {"plans": plans}, None)
        assert found.answer == checks.PASS, found.findings
        # each record leads its doorways where its own hold leads them, its neighbours' doors leading back to that
        # hold's name: the tube stands the hub and the lab, the lab and the hub each tube#1, every door met (2026-11-06:
        # the base's tube met no door of the greenhouse or the hub back, which lead to its instance, and the airlock
        # stood the hub, which its hold leads past it to tube#3)
        (pathlib.Path(folder) / "inventory.json").write_text(json.dumps({"rows": []}))
        given = {"plans": plans, "inventory": pathlib.Path(folder) / "inventory.json"}
        for name, own, neighbours in (("tube", tube, {"hub", "lab"}), ("lab", lab, {"tube#1"}), ("hub", hub, {"tube#1"})):
            record = {"place": name, "places": gates.writer.places_of(name, {"doors": []}, own, plans)}
            assert {entry.get("instance", entry["name"]) for entry in record["places"]} == neighbours, record["places"]
            assert gates.pair_faults(record, own, given) == gates.lead_faults(record, own, given) == [], name
    walled = {**SHED, "doors": [["E", 1.5, 0.9, "DOOR to the galley 0.9 x 2.0 m"], ["E", 4.5, 0.9, "DOOR to the yard"]],
              "leads": {"E": {"to": "sealed", "why": "shut"}, "E:4.5": {"to": "yard", "why": "the yard's door"}},
              "openings": [{"kind": "door", "at": [8.0, 4.5], "wide": 0.9, "sill": 0.0, "to": "yard"},
                           {"kind": "door", "at": [8.0, 1.5], "wide": 0.9, "sill": 0.0, "to": "sealed"}]}
    assert [door["leads"] for door in plan.doors_of(walled, INVENTORY)] == ["sealed", "yard"]
    assert gates.door_faults(walled) == []
    for change, said in ((lambda record: record["rows"].pop("BENCH"), "BENCH"),
                         (lambda record: record["leads"].pop("S"), "door S"),
                         (lambda record: record["leads"].update(N={"to": "sealed", "why": "test"}), "leaves it open")):
        record = json.loads(json.dumps(SHED))
        change(record)
        with tempfile.TemporaryDirectory() as folder:
            out, inputs = made(folder, record)
            found = plan.judge_mapped(out, inputs, None)
            assert found.answer == checks.FAIL and said in " ".join(found.findings), (said, found.findings)


def test_a_written_plan_with_no_corner_takes_its_outline():
    """A written plan (plan_writing's: an outline, no corner) makes its plan with square corners, its outline drawing
    every corner; a plan with neither is refused by name.
    Break: score/stages/scene_record/plan.py: `    if plan.get("outline"):` -> `    if False:`
    Break: score/stages/scene_record/plan.py: `raise ValueError(f"{plan['title']}: the plan gives no corner and no
        outline")`
        -> `return 0.0`"""
    record = {key: value for key, value in SHED.items() if key != "corner"}
    with tempfile.TemporaryDirectory() as folder:
        out, _ = made(folder, {**record, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]})
        walls = json.loads((out / "plan.json").read_text())["walls"]
        assert walls["corner"] == 0.0 and (walls["wide"], walls["deep"]) == (8.0, 6.0), walls
    with tempfile.TemporaryDirectory() as folder:
        try:
            made(folder, record)
        except ValueError as refused:
            assert "no corner and no outline" in str(refused), refused
        else:
            raise AssertionError("a plan with no corner and no outline was made")


# A written plan (plan_writing's schema): the shed's outline, walls, a door in its north wall to the yard beside it,
# its floor, a flat roof, a stair, a bench and a ceiling lamp; one person spot inside, one outside its walls. Its
# holder (the site) holds it and the yard.
WRITTEN = {**SHED, "outline": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]],
           "walls": [{"from": [0.0, 0.0], "to": [8.0, 0.0], "thick": 0.2, "tall": 3.0},
                     {"from": [8.0, 0.0], "to": [8.0, 6.0], "thick": 0.2, "tall": 3.0},
                     {"from": [8.0, 6.0], "to": [0.0, 6.0], "thick": 0.2, "tall": 3.0},
                     {"from": [0.0, 6.0], "to": [0.0, 0.0], "thick": 0.2, "tall": 3.0}],
           "openings": [{"kind": "door", "at": [4.0, 0.0], "wide": 1.2, "angle": 0.0, "swing": "slide", "sill": 0.0,
                         "head": 2.1, "to": "yard"},
                        {"kind": "door", "at": [4.0, 6.0], "wide": 2.0, "angle": 180.0, "swing": "slide", "sill": 0.0,
                         "head": 3.0, "to": "outside"}],
           "levels": [{"name": "floor", "height": 0.0, "points": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]]}],
           "roofs": [{"kind": "flat", "points": [[0.0, 0.0], [8.0, 0.0], [8.0, 6.0], [0.0, 6.0]], "eave": 3.0,
                      "top": 3.0}],
           "stairs": [{"kind": "stair", "points": [[6.0, 4.0], [7.0, 4.0], [7.0, 6.0], [6.0, 6.0]], "from": 0.0,
                       "to": 1.0, "angle": 90.0, "steps": 5}],
           "items": [*SHED["items"], ["LAMP", 3.5, 2.5, 1.0, 1.0, None, "item"]],
           "rows": {**SHED["rows"], "LAMP": ["ceiling_lamp"]},
           "shapes": {"LAMP": {"shape": "rect", "tall": 0.2, "base": 2.7}},
           "people": [[4.0, 3.0, None, None], [20.0, 3.0, None, None]], "terrain": {}}
LAMP_ROW = {"id": "ceiling_lamp", "name": "ceiling lamp", "noun": "lamp", "anchor": "ceiling", "size": [1.0, 1.0, 0.2],
            "count": 1}
# The site holds the yard at its north-west corner and the shed south of it, the shed's north door on the yard's gate
# at (10, 12); its items for both rows are their holds.
SITE = {"title": "SITE", "w": 40.0, "d": 20.0, "leads": {},
        "holds": [{"place": "shed", "row": "shed", "x": 6.0, "y": 12.0, "w": 8.0, "d": 6.0},
                  {"place": "yard", "row": "yard", "x": 0.0, "y": 0.0, "w": 20.0, "d": 12.0}],
        "items": [["SHED", 6.0, 12.0, 8.0, 6.0, None, "item"], ["YARD", 0.0, 0.0, 20.0, 12.0, None, "zone"]],
        "rows": {"SHED": ["shed"], "YARD": ["yard"]}}
# The batch's hand-in (prepare's handin.py): the bench a model of its own take, the lamp sharing the bench's take, the
# shed's floor the plan's own shell.
HANDIN = {"rows": [{"id": "bench", "route": "prop", "size": [2.0, 0.6, 0.9], "count": 1},
                   {"id": "ceiling_lamp", "route": "prop", "size": [1.0, 1.0, 0.2], "count": 1},
                   {"id": "shed_floor", "route": "plan", "part": "floor"}],
          "objects": {"bench": {"rows": ["bench", "ceiling_lamp"]}}}
# The base's site at its scene time (data/physics/setting.json): the Sun stands over its horizon then.
SKY = {"site": {"on": "moon", "latitude": 55.0, "longitude": 0.0, "height_m": 0.0}, "time": "2099-10-01T14:00:00Z"}


def written(folder, design, yard=YARD, site=SITE):
    """scene-record@shed written into `folder` from its design `design`: (the record's output, the writer's inputs)."""
    from score.review import setting
    from score.stages.scene_record import writer
    folder = pathlib.Path(folder)
    out, inputs = made(folder, design, yard)
    (folder / "plans/site.json").write_text(json.dumps(site))
    (folder / "inventory.json").write_text(json.dumps({**INVENTORY, "rows": [*INVENTORY["rows"], LAMP_ROW]}))
    (folder / "sky.json").write_text(json.dumps({**SKY, "place": "shed", "top": "site", "setting": setting.now()}))
    (folder / "hand-in.json").write_text(json.dumps(HANDIN))
    inputs = {**inputs, "plan": out, "sky": folder / "sky.json", "hand-in": folder / "hand-in.json",
              "row kinds": REPO / "data/checks/row-kinds.json",
              "lamp library": REPO / "data/library/lamps.json", "places": REPO / "data/definitions/place.json",
              "dust": REPO / "data/physics/dust.json"}
    record = folder / "record"
    record.mkdir()
    writer.make(inputs, record, 0, {})
    assert writer.record_faults(record) == []
    return record, inputs


def test_the_record_is_written_from_the_design():
    """The shed's record holds its shell with the north door cut, its stair, a light over its lamp, its sky from the
    physics, the yard its door leads to where the site holds it, and only the view standing inside its walls; its
    gates pass, and a door filled, a lamp moved off its item and a door to no place each fail by name. The lamp item
    (3.5, 2.5) 1 m square on the 8 x 6 m shed is at the shed's middle, its base 2.7 m, the light 5% up its 0.2 m.
    The yard stands with its gate on the shed's door, (0, 0, -9) from the shed's middle (the base's airlock opened
    21.8 m from the hub's door, the flat stood 9 m under its stairwell door: the audit of 2026-11-04): held 2 m off
    its gate it still stands there and the site's `held` gate fails on the hold and the door; its gate 3 m up stands
    the shed 3 m over it, the yard 3 m down; the yard moved 5 m off fails `openings`.
    Break: score/stages/scene_record/writer.py: `there = there + met[0]["spot"] - met[0]["there"]` -> `pass`
    Break: score/stages/scene_record/writer.py: `round(floor - other_floor + other_level - level, 4)` ->
        `round(floor - other_floor, 4)`
    Break: score/stages/scene_record/gates.py:
        `if along > writer.place_plan.DOORS_MET or up > writer.place_plan.LEVEL_MET:` -> `if False:`
    Break: score/stages/scene_record/plan.py: `elif pair["gap"] > DOORS_MET:` -> `elif False:`
    Break: score/stages/scene_record/plan.py: `if not sized or middle > HOLD_MIDDLE:` -> `if False:`
    Break: score/stages/scene_record/gates.py:
        `found.append(f"opening {number} ({opening.get('kind')}) at {opening['at']} is filled by {filled}")` -> `pass`
    Break: score/stages/scene_record/gates.py: `found.append(f"the light of plan item {name!r} stands off its
        footprint")`
        -> `pass`
    Break: score/stages/scene_record/gates.py: `if row_id in tied and made.get(row_id, 0) < int(row.get("count") or
        1)]` -> `if False]` (a glowing row with fewer lamps than its reading counts passes)
    Break: score/stages/scene_record/gates.py:
        `found.append(f"opening {number} leads to {to!r}, no place of the design nor a row of its inventory")`
        -> `pass`
    Break: score/stages/scene_record/gates.py: unbuilt_rows' `if row_id not in named]` -> `if False]` (a shell row
        the shell cannot build dropped without a word: the hangar's landing pad, 2026-11-04)
    Break: score/stages/scene_record/writer.py stair: the `if high < low:` swap dropped (a flight drawn from 1 m down
        to 0 m stands its foot at its high end, which the builder lays as a flat block, its treads underneath)
    And (2026-11-04 audit) a doorway is its door row's: one drawn 0.3 m wide for the 1.2 m hatch row, or leading
    elsewhere than its lead, fails `openings` by name; a row laid another number of times than its scene inventory
    counts, the plan giving no reason, fails `plan-matched`; laid as often as the plan's doorways lead to its child
    scene's instances (base's seven tubes, 2026-11-06) it passes. A row the plan also leaves on its walls item, once its
    fixes placed it on an item of its own, is laid once, at its own item (camp's airlock door, 2026-11-06).
    Break: score/stages/scene_record/writer.py item_rows: `if name != WALLS_ITEM or row not in placed]` -> `]`
    Break: score/stages/scene_record/gates.py: `and row["id"] not in said and counted.get(row["id"], 0) !=
        led.get(row["id"])]` -> `and row["id"] not in said]` (the instances the doorways lead to are no reason)
    Break: score/stages/scene_record/gates.py: led_instances' `if hold.get("instance") in led:` -> `if
        hold.get("instance"):` (an instance no doorway leads to counts as a reason)
    Break: score/stages/scene_record/gates.py: `if abs(wide - metres) > DOOR_SHARE * metres or wide < PASSABLE:` ->
        `if False:`
    Break: score/stages/scene_record/gates.py: `if lead is not None and opening.get("to") != lead:` -> `if False:`
    Break: score/stages/scene_record/gates.py: `stair_faults(record, design) + lamp_faults(record, design) + \\
        count_faults(record, design, inputs) + row_count_faults(record, design, inputs)` -> `... + \\
        count_faults(record, design, inputs)`
    2026-11-02, round 44: the day sky's dust left with the old records (eb01c402) and every outdoor Mars place's
    sky was black, campgrounds' 192.8 levels off its concept's. An open place on Mars carries Mars's dusty air
    (data/physics/dust.json: depth 0.6, albedo 0.975, 0.93, 0.86, forward 0.67, diffuse 0.25, its source said) with
    the gain measured against the camp's old concept, and mars_sky draws it butterscotch, its red over its blue; an
    enclosed place on Mars carries it too (2026-11-04: camp's glass domes showed black space in a Mars afternoon), an
    open one on the Moon (no dust) none; the file is a declared input.
    Break: score/stages/scene_record/writer.py: `return found if dome is None else {**found, "sky_dome": dome}` ->
        `return found`
    Break: score/stages/scene_record/writer.py: `if not found:` -> `if inside(design) or not found:` (camp's domes)"""
    from score.review import overhead
    from score.stages.scene_record import gates, writer
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, WRITTEN)
        place, record = writer.record_in(output)
        names = {entry["name"] for entry in record["structure"]}
        assert place == "shed" and record["inside"] and {"wall_1", "deck_1", "roof_1", "stair_1"} <= names, names
        assert len([name for name in names if name.startswith("wall_1")]) == 4, names  # cut round the door
        [lamp] = record["lights"]
        assert lamp["at"] == [0.0, 2.71, 0.0] and "ceiling_lamp" in lamp["from"], lamp  # 5% up the fitting
        seen = overhead.seen(json.loads((pathlib.Path(folder) / "sky.json").read_text())["setting"], SKY["site"],
                             SKY["time"])
        sun = next(light for light in seen["lights"] if light["name"] == "Sun")
        [up] = record["environment"]["sky"]["lights"]
        assert up["name"] == "Sun" and up["altitude"] == sun["altitude"] > 0, (up, sun)
        [yard] = record["places"]
        assert yard["name"] == "yard" and yard["at"] == [0.0, 0.0, -9.0] and yard["rotation"] == [0, 0, 0, 1], yard
        assert [view["name"] for view in record["views"]] == ["from-door-1", "from-door-2", "spot-1"], record["views"]
        assert [view["name"] for view in record["views_left_out"]] == ["spot-2"], record["views_left_out"]
        assert record["ceiling"] == 3.0, record
        stair = next(entry for entry in record["structure"] if entry["name"] == "stair_1")
        down = writer.stair(1, {**WRITTEN["stairs"][0], "from": 1.0, "to": 0.0}, WRITTEN)
        assert down["foot"][1] < down["top"][1] and (down["foot"], down["top"]) == (
            [stair["top"][0], stair["foot"][1], stair["top"][2]], [stair["foot"][0], stair["top"][1], stair["foot"][2]]
        ), (down, stair)  # a flight drawn from its high end stands its foot at its low end: its treads face up
        for check in gates.CHECKS:
            verdict = check.judge(output, inputs, {})
            assert verdict.answer == checks.PASS, (verdict.check, verdict.reason, verdict.findings)
        path = output / "record/shed.json"
        filled = {**record, "structure": record["structure"] + [
            {"name": "plug", "builder": "slab", "points": [[-0.8, -3.1], [0.8, -3.1], [0.8, -2.9], [-0.8, -2.9]],
             "low": 0.0, "high": 3.0}]}
        path.write_text(json.dumps(filled))
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.FAIL and "filled by ['plug']" in " ".join(verdict.findings), verdict.findings
        path.write_text(json.dumps({**record, "lights": [{**lamp, "at": [3.0, 2.7, 0.0]}]}))
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.FAIL and "'LAMP' stands off" in " ".join(verdict.findings), verdict.findings
        path.write_text(json.dumps({**record, "lights": []}))
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.FAIL and "glowing row ceiling_lamp has 0 lamps, its reading counts 1" in \
            verdict.findings, verdict.findings
        path.write_text(json.dumps(record))
        handin = json.loads(pathlib.Path(inputs["hand-in"]).read_text())
        pathlib.Path(inputs["hand-in"]).write_text(json.dumps({**handin, "rows": [
            *handin["rows"], {"id": "landing_pad", "part": "floor", "route": "plan"}]}))
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.FAIL and verdict.findings == (
            "shell row landing_pad (floor) is built by no piece of the shell",), verdict.findings
    nowhere = json.loads(json.dumps(WRITTEN))
    nowhere["openings"][0]["to"] = "moon_city"
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, nowhere)
        verdict = gates.judge_openings(output, inputs, {})
        assert verdict.answer == checks.FAIL and "'moon_city'" in " ".join(verdict.findings), verdict.findings
        assert "opening 1 leads to 'moon_city', its door row 'HATCH N, 1.2 x 2.1 m' to 'yard'" in verdict.findings
    narrow = json.loads(json.dumps(WRITTEN))
    narrow["openings"][0]["wide"] = 0.3  # the drawing's width, not its door row's 1.2 m (habitat's 0.237 m hatches)
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, narrow)
        verdict = gates.judge_openings(output, inputs, {})
        assert verdict.findings == ("opening 1 is 0.3 m wide for door row 'HATCH N, 1.2 x 2.1 m' of 1.2 m",), verdict
        pathlib.Path(inputs["inventory"]).write_text(json.dumps({**INVENTORY, "rows": [
            {**INVENTORY["rows"][0], "count": 2}, LAMP_ROW]}))  # the plan re-counted the benches, saying no reason
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.findings == ("row bench: 2 in the scene inventory, 1 laid, and the plan says no reason",), verdict
        kept = pathlib.Path(inputs["plans"]) / "shed.json"
        held = {**json.loads(kept.read_text()), "holds": [{"place": "bench", "row": "bench", "instance": "bench#1"}]}
        kept.write_text(json.dumps(held))  # a child scene's instance no doorway leads to: no reason
        assert gates.judge_plan_matched(output, inputs, {}).findings == verdict.findings
        kept.write_text(json.dumps({**held, "holds": held["holds"] + [
            {"place": "yard", "row": "yard", "leads": {"bench": "bench#1"}}]}))  # its one instance the yard's door meets
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.PASS, verdict.findings
    walled = {**WRITTEN, "items": [*WRITTEN["items"], [writer.WALLS_ITEM, 0.0, 0.0, 8.0, 6.0, None, "item"]],
              "rows": {**WRITTEN["rows"], writer.WALLS_ITEM: ["bench", "ceiling_lamp"]}}  # camp's door, 2026-11-06
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, walled)
        place, record = writer.record_in(output)
        laid = [entry["name"] for entry in record["objects"] if entry["row"] in ("bench", "ceiling_lamp")]
        assert laid == ["bench_1", "ceiling_lamp_1"] and len(record["lights"]) == 1, (laid, record["lights"])
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.PASS, verdict.findings
    off = {**SITE, "holds": [SITE["holds"][0], {**SITE["holds"][1], "x": 2.0}]}  # the yard held 2 m off its gate
    raised = {**YARD, "openings": [{**YARD["openings"][0], "sill": 3.0}]}  # the yard's gate 3 m up: the shed 3 m up
    for yard, site, at in ((YARD, off, [0.0, 0.0, -9.0]), (raised, SITE, [0.0, -3.0, -9.0])):
        with tempfile.TemporaryDirectory() as folder:
            output, inputs = written(folder, WRITTEN, yard, site)
            place, record = writer.record_in(output)
            [stood] = record["places"]
            assert stood["at"] == at, (stood, at)  # on the door back, at its height, whatever the hold
            verdict = gates.judge_openings(output, inputs, {})
            assert verdict.answer == checks.PASS, verdict.findings
            (output / "record/shed.json").write_text(json.dumps({**record, "places": [{**stood, "at": [5.0, *at[1:]]}]}))
            verdict = gates.judge_openings(output, inputs, {})
            assert verdict.answer == checks.FAIL and "opens 5.00 m along the floor" in " ".join(verdict.findings)
            holder = pathlib.Path(folder) / "site-plan"
            holder.mkdir()
            (holder / "plan.json").write_text(json.dumps({"place": "site"}))
            verdict = plan.judge_held(holder, inputs, None)
            if site is off:
                said = " | ".join(verdict.findings)
                assert verdict.answer == checks.FAIL and "yard's hold is 20.0 x 12.0 m, its yard item 20.0 x 12.0 m, " \
                    "their middles 2.0 m apart" in said and "shed's door to yard at [4.0, 0.0] opens 2.0 m from " \
                    "yard's nearest door back" in said, verdict.findings
            else:
                assert verdict.answer == checks.PASS and verdict.measures["held places"] == 2, verdict.findings
    # a place on mars inside or out has its dusty day sky and one on the moon none
    sys.path.insert(0, str(REPO / "tools" / "usd"))
    import mars_sky
    from score.review import setting
    dust = json.loads((REPO / "data/physics/dust.json").read_text())
    on_mars = {"site": {"on": "mars", "latitude": 30.0, "longitude": 130.0, "height_m": 0.0},
               "time": "2099-10-01T16:00:00Z", "setting": setting.now()}
    yard = {"title": "YARD", "outline": [[0, 0], [10, 0], [10, 10], [0, 10]], "terrain": {"spots": [[5, 5]]}}
    dome = writer.environment(yard, on_mars, dust)["sky_dome"]
    assert {key: dome[key] for key in ("depth", "albedo", "forward", "diffuse", "gain")} == {
        "depth": 0.6, "albedo": [0.975, 0.93, 0.86], "forward": 0.67, "diffuse": 0.25,
        "gain": list(writer.SKY_GAIN)}, dome
    assert "Wolff et al. 2009" in dome["from"] and "cited" not in dome, dome
    picture = mars_sky.picture(dome, [0.0, -0.5, -0.866], 64)
    red, _, blue = picture[: picture.shape[0] // 2].reshape(-1, 3).mean(axis=0)
    assert red > blue > 0, (red, blue)
    assert writer.environment(WRITTEN, on_mars, dust)["sky_dome"] == dome  # seen through its glass and openings
    assert "sky_dome" not in writer.environment(yard, {**on_mars, "site": {**on_mars["site"], "on": "moon"}}, dust)
    assert writer.files("yard")["dust"] == "{data}/physics/dust.json"


def test_an_open_place_s_view_eye_stands_a_person_s_height_over_its_made_ground(tmp_path):
    """A standing spot at the floor of an open place stands on the terrain row's made ground under it: a ground
    rising 0.5 m a metre east puts the eye at (4, 2) 2 + 1.6 m up; a spot on a 1 m deck stays on its deck, and a
    place the terrain made no ground for stands on its level (wreck's spot-3 and spot-6 eyes stood 2.6 and 4.3 m
    under its ground, their views black, 2026-10-30).
    Break: score/stages/scene_record/writer.py: `return spot["level"] if under is None else under` ->
        `return spot["level"]`"""
    from pxr import Usd, UsdGeom
    from score.stages.scene_record import writer
    ground = Usd.Stage.CreateNew(str(tmp_path / "moon/places/yard.usdc"))
    UsdGeom.Xform.Define(ground, "/yard")
    slope = UsdGeom.Mesh.Define(ground, "/yard/Outside/near")
    slope.CreatePointsAttr([(-10, -5, -10), (10, 5, -10), (10, 5, 10), (-10, -5, 10)])
    slope.CreateFaceVertexCountsAttr([4])
    slope.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
    ground.Save()
    yard = {"floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [], "doorways": [],
            "standing": [{"at": [4.0, 2.0], "level": 0.0, "looks_at": None},
                         {"at": [4.0, 2.0], "level": 1.0, "looks_at": None}]}
    under = writer.ground_under({"terrain": str(tmp_path)}, "yard")
    assert [view["eye"][1] for view in writer.views(yard, 1.6, under)] == [3.6, 2.6]
    assert writer.ground_under({"terrain": str(tmp_path)}, "shed") is None and writer.ground_under({}, "yard") is None
    assert [view["eye"][1] for view in writer.views(yard, 1.6)] == [1.6, 2.6]


def test_a_view_eye_where_a_person_would_stand_in_a_thing_moves_out_with_its_look_kept():
    """Wreck's spot-5, 2026-10-30: a view's eye stands where a person would. On a 10 m plan (frame: its middle at the
    origin) a doorway's eye 1 m in lands in a 2 m crate, and a person spot stands against it: each eye moves to the
    nearest floor where a 0.5 m person stands in nothing, its aim moved by the same offset; a spot clear of the crate
    stays where it is, and its own person spot never counts against it.
    Break: score/stages/scene_record/writer.py: `if not standing.stands_in(spot, size, walls_things, grid, others):`
        -> `if True:`; and `eye, aim = eye + [offset[0], 0.0, offset[1]], aim + offset` -> `eye = eye + [offset[0],
        0.0, offset[1]]`"""
    from score.stages.scene_record import writer
    design = {"w": 10.0, "d": 10.0, "items": [["CRATE 1", 4.0, 1.5, 2.0, 2.0, None, "item"]],
              "rows": {"CRATE 1": ["crate"]}, "people": [[5.0, 3.6], [8.0, 8.0]]}
    inventory = {"rows": [{"id": "crate", "anchor": "floor", "size": [2.0, 2.0, 1.0], "count": 1}]}
    record = {"floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [],
              "doorways": [{"name": "door-1", "middle": [0.0, 0.0, -4.5], "inward": [0.0, 0.0, 1.0], "wide": 1.0,
                            "to": "yard"}],
              "standing": [{"at": [0.0, -1.4], "level": 0.0, "looks_at": None},
                           {"at": [3.0, 3.0], "level": 0.0, "looks_at": None}]}
    found = writer.views(record, 1.6, clear=writer.clear_of(design, inventory))
    door, against, clear = found
    assert door["eye"][2] <= -3.5 - 0.25 + 0.05 or door["eye"][2] >= -1.5 + 0.25 - 0.05 or abs(door["eye"][0]) >= 1.2
    offset = np.subtract(door["eye"], [0.0, 1.6, -3.5])
    assert math.hypot(offset[0], offset[2]) < 1.5 and door["aim"] == [round(offset[0], 3), 1.0,
                                                                       round(4.5 + offset[2], 3)], door
    assert against["eye"][2] >= -1.5 + 0.25 - 0.05 and abs(against["eye"][0]) < 0.05, against
    assert against["aim"] == [against["eye"][0], 1.0, round(against["eye"][2] + 1.4, 3)], against
    assert clear["eye"] == [3.0, 1.6, 3.0] and clear["aim"] == [0.0, 1.0, 0.0]
    assert [view["eye"] for view in writer.views(record, 1.6)][1:] == [[0.0, 1.6, -1.4], [3.0, 1.6, 3.0]]


def test_a_view_looking_into_a_thing_close_by_turns_to_the_nearest_clear_way_or_is_left_out():
    """Flat's spot-2, 2026-10-31: its eye 0.45 m off its wardrobe, aimed at the middle, saw only the wardrobe. On a
    10 m plan (frame: its middle at the origin) a spot 0.15 m west of a 2 m tall wardrobe looking east at the middle
    turns to the nearest way clear for a metre (+-15 degrees will not do: the wardrobe is 2 m deep), its eye kept; a
    spot boxed in by wardrobes on every side is left out with why; a low bench in its look does not block it, nor
    does anything for an eye off the plan (galley's and hangar's spots past their plans, 2026-10-31).
    Break: score/stages/scene_record/writer.py: `if hit is None:` -> `if True:`; and `if (cell >= 0).all() and (cell
        < grid.shape).all() and point[1] - base < tops[tuple(cell)]:` -> `if point[1] - base < tops[grid.cell_of(spot)]:`"""
    from score.stages.scene_record import writer
    wardrobe = ["WARDROBE 1", 3.9, 4.0, 0.6, 2.0, None, "item"]
    design = {"w": 10.0, "d": 10.0, "items": [wardrobe, ["BENCH 1", 1.2, 1.9, 0.6, 0.4, None, "item"]],
              "rows": {"WARDROBE 1": ["wardrobe"], "BENCH 1": ["bench"]},
              "shapes": {"WARDROBE 1": {"tall": 2.0}, "BENCH 1": {"tall": 0.45}}}
    inventory = {"rows": [{"id": "wardrobe", "anchor": "floor", "size": [0.6, 2.0, 2.0], "count": 1},
                          {"id": "bench", "anchor": "floor", "size": [1.0, 0.4, 0.45], "count": 1}]}
    record = {"floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [], "doorways": [],
              "standing": [{"at": [-1.25, 0.0], "level": 0.0, "looks_at": None},
                           {"at": [-4.0, -3.2], "level": 0.0, "looks_at": None}]}
    beside, over_bench = writer.views(record, 1.6, sight=writer.sight_of(design, inventory))
    assert beside["eye"] == [-1.25, 1.6, 0.0] and beside["aim"] != [0.0, 1.0, 0.0], beside
    sight = writer.sight_of(design, inventory)
    assert sight(np.array(beside["eye"]), np.array([0.0, 1.0, 0.0]), 0.0) < 0.2
    assert sight(np.array(beside["eye"]), np.array(beside["aim"]), 0.0) is None and "turned" in beside["from"]
    assert over_bench["aim"] == [0.0, 1.0, 0.0], over_bench
    walled = writer.sight_of(dict(design, walls=[{"from": [0.0, 0.0], "to": [10.0, 0.0]}]), inventory)
    assert walled(np.array([0.0, 1.6, -20.0]), np.array([0.0, 1.0, -30.0]), 0.0) is None  # off its plan: nothing
    boxed = dict(design, items=[["WARDROBE 1", 4.3, 4.3, 1.4, 0.3, None, "item"], ["WARDROBE 2", 4.3, 4.3, 0.3, 1.4, None, "item"],
                                ["WARDROBE 3", 5.4, 4.3, 0.3, 1.4, None, "item"], ["WARDROBE 4", 4.3, 5.4, 1.4, 0.3, None, "item"]],
                 rows={f"WARDROBE {number}": ["wardrobe"] for number in range(1, 5)},
                 shapes={f"WARDROBE {number}": {"tall": 2.0} for number in range(1, 5)})
    alone = dict(record, standing=[{"at": [0.0, 0.0], "level": 0.0, "looks_at": None}])
    kept, left = writer.views_inside(writer.views(dict(alone, floor=[[-5.0, -5.0], [5.0, 4.0]]), 1.6,
                                                  sight=writer.sight_of(boxed, inventory)), boxed, False)
    assert kept == [] and left[0]["name"] == "spot-1" and "every way it turns" in left[0]["why"], left


def test_a_place_a_backdrop_row_is_shown_from_stands_in_the_record_where_its_holder_holds_it():
    """The stairwell's palm seen through its window is the square's (prepare's groups.shown_from: `shown`): the record
    stands the holder at its own plan's middle, a place it holds beside where it holds it, each once.
    Break: score/stages/scene_record/writer.py: `if name in stood_already or name == place:` -> `if name == place:`"""
    from score.stages.scene_record import writer
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, WRITTEN)
        plan_record = json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text())
        handin = {"rows": [{"id": "palm_tree", "route": "skyline", "shown": {"place": "site", "row": "palm_tree"}},
                           {"id": "far_shed", "route": "skyline", "shown": {"place": "yard", "row": "shed"}}]}
        found = writer.places_of("shed", plan_record, WRITTEN, inputs["plans"], handin)
        by_name = {entry["name"]: entry for entry in found}
        assert [entry["name"] for entry in found] == ["yard", "site"], found  # the yard already stood by its door
        assert by_name["site"]["at"] == [10.0, 0.0, -5.0] and "palm_tree" in by_name["site"]["from"], by_name["site"]


def test_a_far_row_stands_far_off_where_its_concept_box_is_seen_as_a_run_of_its_pieces():
    """2026-10-26: the square's city skyline had no maker; no scene of the environment stands there, so it is ordinary
    objects (prepare's groups.far_made): laid along the bearing its box is seen at (the plan fixes' projection: up
    the picture is away), at the distance its read tall rises to its box's height in the framework's view, its
    pieces square to that bearing; one with no projection to stand it by is named, never placed by guess. The city's
    50 m read tall over its 50 px box at the view's focal length is its distance; its two pieces 100 m apart on its
    200 m.
    Break: score/stages/scene_record/far.py: `distance = max(float(size[2]) * focal(picture) / (box[3] - box[1]),`
        -> `distance = max(0.0,`
    Break: score/stages/scene_record/writer.py:
        `spot = np.asarray(placed["at"]) + way * length * ((number - 0.5) / pieces - 0.5)`
        -> `spot = np.asarray(placed["at"])`"""
    from score.stages.scene_record import far, writer
    rows = [{"id": name, "anchor": "floor", "noun": name, "count": 1, "size": [1, 1, 1], "boxes": [box]}
            for name, box in (("crate", [240, 700, 260, 750]), ("drum", [740, 700, 760, 750]),
                              ("bench", [490, 200, 510, 250]))]
    plan = {"w": 20.0, "d": 20.0, "items": [["CRATE 1", 4.5, 14.5, 1, 1, None, "item"],
                                            ["DRUM 1", 14.5, 14.5, 1, 1, None, "item"],
                                            ["BENCH 1", 9.5, 4.5, 1, 1, None, "item"]],
            "rows": {"CRATE 1": ["crate"], "DRUM 1": ["drum"], "BENCH 1": ["bench"]}}
    city = {"id": "city", "anchor": "ground", "part": "backdrop", "route": "prop", "size": [100.0, 100.0, 50.0],
            "box": [450, 100, 550, 150], "far": {"pieces": 2, "length": 200.0}}
    inventory = {"picture": [1000, 1000], "rows": [*rows, city]}
    assert far.far_object(city, set()) and not far.far_object({**city, "terrain": True}, set())
    focal = 500 / math.tan(math.radians(far.VIEW_FOV / 2))
    spot = far.spot(plan, inventory, city)
    assert abs(spot["distance"] - 50 * focal / 50) < 0.1 and np.allclose(spot["at"], [10.0, 10.0 - spot["distance"]],
                                                                          atol=0.1), spot
    with tempfile.TemporaryDirectory() as folder:
        path = pathlib.Path(folder) / "inventory.json"
        path.write_text(json.dumps(inventory))
        laid, unplaced = writer.far_objects({**plan, "corner": [0.0, 0.0, 0.0]}, {"rows": [city], "objects": {
            "city": {"rows": ["city"]}}}, path)
        assert unplaced == [] and [entry["name"] for entry in laid] == ["city_1", "city_2"]
        assert sorted(round(abs(entry["at"][0] - laid[0]["at"][0]), 3) for entry in laid) == [0.0, 100.0]
        assert all(entry["bake"] == "city_1" and "far off" in entry["from"] for entry in laid)
        path.write_text(json.dumps({**inventory, "rows": [city]}))  # no rows to fit the projection on
        assert writer.far_objects(plan, {"rows": [city]}, path)[1][0]["row"] == "city"
    laid_too = {**plan, "corner": [0.0, 0.0, 0.0], "items": [*plan["items"], ["CITY 1", 9.5, 1.0, 2, 2, None, "item"]],
                "rows": {**plan["rows"], "CITY 1": ["city"]}}  # its plan laid it here too: laid far off alone
    assert {entry["row"] for entry in writer.design_objects(laid_too, {"rows": [*rows, city], "objects": {}})} == {
        "crate", "drum", "bench"}


def test_every_object_of_the_design_stands_at_its_plan_item_waiting_on_its_model():
    """Fault (2026-10-25): the record laid no object of a designed place, so the assembly placed none of its models.
    Each prop row's plan item gets its object `<row>_<n>` over its middle at its shape's base, waiting on its take's
    model (`<first row>_1`); a run the plan draws once as a polygon counting three lays three pieces along it, each
    its long side along the path; a row with no size waits named; the plan's own floor is named on its deck. The
    bench item (1, 1) 2 x 0.6 m is at (-2, -1.7) on the shed centred on its 8 x 6 m; the lamp's at its 2.7 m base.
    Break: score/stages/scene_record/writer.py: `            base = float(shape.get("base") or 0.0)` ->
        `            base = 0.0`
    Break: score/stages/scene_record/writer.py: `return [along(path, (number + 0.5) / pieces) for number in
        range(pieces)]`
        -> `return [along(path, 0.5) for number in range(pieces)]`
    2026-11-04: the lab's 10 pipes on 6 plan items laid 6. A row counting 5 on two items lays 3 and 2.
    Break: score/stages/scene_record/writer.py pieces_of: `for turn in range(max(short, 0)):` -> `for turn in
        range(0):` (two pipes laid for five)
    Break: score/stages/scene_record/writer.py design_objects: `pieces_of(counted(row, design), laid)` ->
        `pieces_of(row, laid)` (the five laid again where the plan dropped three)"""
    from score.stages.scene_record import writer
    design = {**WRITTEN, "items": [*WRITTEN["items"], ["RAIL", 1.0, 4.0, 3.0, 1.0, None, "item"]],
              "rows": {**WRITTEN["rows"], "RAIL": ["rail"]},
              "shapes": {**WRITTEN["shapes"], "RAIL": {"shape": "polygon", "points": [[0, 0], [1, 0], [1, 1], [0, 1]],
                                                       "count": 3, "base": 0.5}}}
    handin = {"rows": [*HANDIN["rows"], {"id": "rail", "route": "prop", "size": [1.0, 0.1, 1.0]}],
              "objects": {**HANDIN["objects"], "rail": {"rows": ["rail"]}}}
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, design)
        (pathlib.Path(folder) / "hand-in.json").write_text(json.dumps(handin))
        record = writer.record_of(json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text()), design,
                                  inputs)
    found = {entry["name"]: entry for entry in record["objects"]}
    assert sorted(found) == ["bench_1", "ceiling_lamp_1", "rail_1", "rail_2", "rail_3"], sorted(found)
    bench = found["bench_1"]
    assert bench["at"] == [-2.0, 0.0, -1.7] and bench["bake"] == "bench_1" and bench["row"] == "bench", bench
    assert bench["rotation"] == [0.0, 0.0, 0.0, 1.0] and "surface line's bake" in bench["waiting"], bench
    lamp = found["ceiling_lamp_1"]
    assert lamp["bake"] == "bench_1" and lamp["at"] == [0.0, 2.7, 0.0], lamp  # the bench's take, at its base
    rails = [found[f"rail_{number}"] for number in (1, 2, 3)]
    assert all(rail["at"][1] == 0.5 for rail in rails) and len({tuple(rail["at"]) for rail in rails}) == 3, rails
    assert rails[0]["at"] == [-1.6667, 0.5, 1.0] and rails[0]["rotation"] == [0.0, 0.0, 0.0, 1.0], rails[0]
    deck = next(entry for entry in record["structure"] if entry.get("row"))
    assert deck["name"].startswith("deck") and deck["row"] == "shed_floor", deck
    unsized = {**handin, "rows": [{**row, "size": None} if row["id"] == "rail" else row for row in handin["rows"]]}
    [rail] = [entry for entry in writer.design_objects(design, unsized) if entry["name"] == "rail_1"]
    assert "row rail has no size" in rail["waiting"], rail
    pipes = {**design, "items": [*design["items"], ["PIPE 1", 5.0, 1.0, 1.0, 0.2, None, "item"],
                                 ["PIPE 2", 5.0, 3.0, 1.0, 0.2, None, "item"]],
             "rows": {**design["rows"], "PIPE 1": ["pipe"], "PIPE 2": ["pipe"]}}
    piped = {"rows": [*handin["rows"], {"id": "pipe", "route": "prop", "size": [1.0, 0.1, 0.1], "count": 5}],
             "objects": {**handin["objects"], "pipe": {"rows": ["pipe"]}}}
    laid = writer.design_objects(pipes, piped)
    assert [entry["from"].split(",")[0] for entry in laid if entry["row"] == "pipe"] == \
        ["plan item 'PIPE 1'"] * 3 + ["plan item 'PIPE 2'"] * 2, laid
    # settle@engineroom, 2026-11-09: a plan that took pieces off where its floor holds no more says how many it lays
    dropped = {**pipes, "dropped": [{"item": "pipe", "why": "3 more of it than the place's free floor holds",
                                     "laid": 2}]}
    assert [entry["from"].split(",")[0] for entry in writer.design_objects(dropped, piped)
            if entry["row"] == "pipe"] == ["plan item 'PIPE 1'", "plan item 'PIPE 2'"]


def test_a_row_the_plan_lays_only_against_its_edge_stands_past_it_facing_in():
    """2026-10-26: the square's 30 by 30 m buildings, laid by its plan only as 2 to 7 m strips at its edges
    (floor_fit.past_edge), stood centred on those strips over the plaza. Such a row stands with its face on the
    edge's line and its body out past it, facing in. On a 20 by 20 m plan (centred: plan (x, y) is place (x - 10,
    y - 10)): the 30 x 30 m building's strip at the right edge, (18, 0) 2 x 10 m (a corner: it runs along the right
    edge), stands at plan (35, 5), its body 20 to 50 m east, facing west; the 40 x 20 m one's strip at the foot,
    (5, 18) 10 x 2 m, at plan (10, 30), 20 to 40 m south, facing north; a kiosk on the ground off the edge stays
    centred on its item.
    Break: score/stages/scene_record/writer.py: `spot, way = past_edge_spot(item, design, spot, size)` -> `pass`"""
    from score.stages.scene_record import writer
    design = {"w": 20.0, "d": 20.0, "items": [["RIGHT 1", 18.0, 0.0, 2.0, 10.0, "W", "item"],
                                              ["FRONT 1", 5.0, 18.0, 10.0, 2.0, "N", "item"],
                                              ["KIOSK 1", 9.0, 9.0, 2.0, 2.0, "N", "item"]],
              "rows": {"RIGHT 1": ["right"], "FRONT 1": ["front"], "KIOSK 1": ["kiosk"]}}
    rows = [{"id": name, "anchor": "ground", "route": "shell", "size": size}
            for name, size in (("right", [30.0, 30.0, 20.0]), ("front", [40.0, 20.0, 15.0]), ("kiosk", [2, 2, 3]))]
    found = {entry["row"]: entry for entry in writer.design_objects(design, {"rows": rows, "objects": {}})}
    assert found["right"]["at"] == [25.0, 0.0, -5.0], found["right"]
    assert found["right"]["rotation"] == writer.yaw_turn(design, writer.FACING_WAY["W"], rows[0]["size"])
    assert found["front"]["at"] == [0.0, 0.0, 20.0], found["front"]
    assert found["front"]["rotation"] == writer.yaw_turn(design, writer.FACING_WAY["N"], rows[1]["size"])
    assert found["kiosk"]["at"] == [0.0, 0.0, 0.0], found["kiosk"]


def test_a_run_lies_along_its_item_s_long_side_whatever_its_facing():
    """#36, 2026-10-31: the walkway's two 12 m ceiling ducts (0.5 by 12 m), each on a 0.14 by 12 m item along the hall
    facing S, were turned by their facing across the hall. A row long on the ground at an item long the other way to
    its facing lies along the item (its facing's way turned a quarter, writer.item_way); a chair, not long, keeps its
    facing on its box a little deeper than wide.
    Break: score/stages/scene_record/writer.py: `return np.array([-way[1], way[0]])` -> `return way`"""
    from score.stages.scene_record import writer
    design = {"w": 2.0, "d": 12.0, "items": [["DUCT 1", 0.5, 0.0, 0.14, 12.0, "S", "item"],
                                             ["CHAIR 1", 1.2, 5.0, 0.5, 0.6, "S", "item"]],
              "rows": {"DUCT 1": ["duct"], "CHAIR 1": ["chair"]}}
    rows = [{"id": "duct", "route": "prop", "size": [0.5, 12.0, 0.3]},
            {"id": "chair", "route": "prop", "size": [0.5, 0.55, 0.9]}]
    found = {entry["row"]: entry for entry in writer.design_objects(design, {"rows": rows, "objects": {}})}

    def same(one, two):  # one turn: a quaternion and its negative
        return bool(np.isclose(abs(np.dot(one, two)), 1.0))
    assert same(found["duct"]["rotation"], writer.yaw_turn(design, (0.0, -1.0), rows[0]["size"])), found["duct"]
    assert not same(found["duct"]["rotation"], writer.yaw_turn(design, writer.FACING_WAY["S"], rows[0]["size"]))
    assert same(found["chair"]["rotation"], writer.yaw_turn(design, writer.FACING_WAY["S"], rows[1]["size"]))


def test_an_opening_row_names_its_own_cut_and_a_thing_on_a_low_deck_stands_on_it():
    """2026-10-30: the shell named each opening row on the first free wall piece (the workshop's doorway on wall_2,
    hangar's floor hatch on wall 1's lintel), and laid airlock's sandbags at 0 inside its 0.2 m porch deck. An opening
    row is named on the lintel over the cut its plan item makes (the shed's door at plan (4, 0) cuts wall 1 into its
    foot wall_1, the foot under the door wall_1_2, the lintel wall_1_3 and the rest wall_1_4), and one with no item is
    named on no piece; a crate at the floor on a 0.2 m deck stands on it at 0.2 m, a box at the floor under a 2.5 m
    loft stays at 0 (things may stand under it).
    Break: score/stages/scene_record/writer.py: `return f"wall_{index + 1}" if over[-1] == 0` ->
        `return f"wall_{index + 1}" if over[0] == 0`, and the next `over[-1] + 1` -> `over[0] + 1`
    Break: score/stages/scene_record/writer.py: `height = base or deck_height(design, spot)` -> `height = base`
    Break: score/stages/scene_record/writer.py: `0.0 < float(level.get("height") or 0.0) <= design_shell.SLAB +
        DECK_BELOW and` -> `0.0 < float(level.get("height") or 0.0) and`
    A piece whose plan base lies below the floor-lying level at its spot stands on that level (settle@airlock,
    checkout 67: its sandbags' -0.2 m ground base buried them in the 0 m floor deck): -0.2 m bags on the 0.2 m deck
    stand at 0.2, under the loft on the floor at 0, off every deck on the ground at -0.2.
    Break: score/stages/scene_record/writer.py: `height = floor_lift(design, spot, base) if base else` ->
        `height = base if base else`
    Break: score/stages/scene_record/writer.py floor_lift: `return max([base] + [` -> `return max([0.0] + [`
    An opening row with no plan item of its own (2026-11-05) is named by its words on a free piece at an opening the
    shell cuts: the lab's corridor openings on the lintel over the plan's own door (wall_1_3), the hangar's floor
    hatch on the flight going down through its deck's hatch (stair_2), its roof opening on a roof cut round its
    openings, and on nothing while its roof has none; the shell's own pillars stand in the place's frame, named
    their row, painted (here named missing: no library), and none where the earth seed lays the shell.
    Break: score/stages/scene_record/writer.py: `if words & FLOOR_WORDS:` -> `if False:`
    Break: score/stages/scene_record/writer.py: `name_open_cuts(design, shelled + flights, (rows or {}).get("opening",
        []))` -> `pass`
    Break: score/stages/scene_record/writer.py: `if not inside(design) or design_shell.laid_for(design):` ->
        `if not inside(design):`
    A roof with both its panels row and an opening names the opening on its cut (hangar's roof_opening, 2026-11-06).
    Break: score/stages/scene_record/writer.py shell: `name_open_cuts(design, found, (rows or {}).get("opening", []))`
        -> `pass`"""
    from score.stages.scene_record import writer
    down = {**WRITTEN, "stairs": [*WRITTEN["stairs"], {"kind": "stair", "points": [[1.0, 4.0], [2.0, 4.0], [2.0, 5.0],
                                                                                  [1.0, 5.0]],
                                                        "from": 0.0, "to": -1.0, "angle": 90.0, "steps": 5}]}
    openings = {"opening": ["corridor_opening", "floor_hatch", "roof_opening"]}
    named = {entry.get("row"): entry["name"] for entry in writer.structure({"place": "shed"}, down, None, openings)}
    assert (named.get("corridor_opening"), named.get("floor_hatch"), "roof_opening" in named) == \
        ("wall_1_3", "stair_2", False), named
    holed = {**down, "roofs": [{**WRITTEN["roofs"][0], "openings": [{"points": [[5, 1], [7, 1], [7, 2], [5, 2]]}]}]}
    named = {entry.get("row"): entry["name"] for entry in writer.structure({"place": "shed"}, holed, None, openings)}
    assert named.get("roof_opening") == "roof_1", named
    paneled = {**openings, "roof": ["roof_panels"]}  # the roof's own panels row takes no piece its opening is named on
    named = {entry.get("row"): entry["name"] for entry in writer.structure({"place": "shed"}, holed, None, paneled)}
    assert named.get("roof_opening") == "roof_1", named
    pillars = {"rows": [{"id": "posts", "route": "plan", "part": "structure", "name": "posts", "size": [0.2, 0.2, 2.0],
                         "count": 2}]}
    own = writer.row_entries(WRITTEN, "shed", None, pillars)
    assert [(entry["name"], entry["row"], entry["plain"], entry["surface"]) for entry in own] == [
        ("posts_1", "posts", "shell", None), ("posts_2", "posts", "shell", None)] and \
        all(entry["surface_missing"] for entry in own), own
    assert writer.row_entries({**WRITTEN, "shell": "kit", "inside": True}, "shed", None, pillars) == []
    design = {**WRITTEN, "items": [*WRITTEN["items"], ["DOORWAY 1", 3.4, 0.0, 1.2, 0.2, None, "item"],
                                   ["CRATE 1", 6.0, 4.0, 1.0, 1.0, None, "item"],
                                   ["BOX 1", 1.0, 4.0, 1.0, 1.0, None, "item"],
                                   ["BAGS 1", 6.0, 4.0, 1.0, 1.0, None, "item"],
                                   ["BAGS 2", 1.0, 4.0, 1.0, 1.0, None, "item"],
                                   ["BAGS 3", 9.0, 4.0, 1.0, 1.0, None, "item"]],
              "shapes": {**WRITTEN["shapes"], **{f"BAGS {number}": {"shape": "rect", "tall": 0.2, "base": -0.2}
                                                 for number in (1, 2, 3)}},
              "rows": {**WRITTEN["rows"], "DOORWAY 1": ["doorway"], "CRATE 1": ["crate"], "BOX 1": ["box"],
                       "BAGS 1": ["bag_deck"], "BAGS 2": ["bag_floor"], "BAGS 3": ["bag_ground"]},
              "levels": [*WRITTEN["levels"],
                         {"name": "porch deck", "height": 0.2, "points": [[5.0, 3.0], [8.0, 3.0], [8.0, 6.0], [5.0, 6.0]]},
                         {"name": "loft", "height": 2.5, "points": [[0.0, 3.0], [4.0, 3.0], [4.0, 6.0], [0.0, 6.0]]}]}
    named = {entry["name"]: entry.get("row") for entry in
             writer.shell(design, "shed", None, {"wall": ["wall_panels"], "opening": ["doorway", "hatch"]})}
    assert named["wall_1_3"] == "doorway" and named["wall_1"] == "wall_panels", named
    assert "hatch" not in named.values() and list(named.values()).count("doorway") == 1, named
    rows = [{"id": name, "route": "prop", "size": [1.0, 1.0, 0.5]}
            for name in ("crate", "box", "bag_deck", "bag_floor", "bag_ground")]
    found = {entry["row"]: entry for entry in writer.design_objects(design, {"rows": rows, "objects": {}})}
    assert found["crate"]["at"] == [2.5, 0.2, 1.5] and found["box"]["at"] == [-2.5, 0.0, 1.5], found
    assert [found[row]["at"][1] for row in ("bag_deck", "bag_floor", "bag_ground")] == [0.2, 0.0, -0.2], found


def test_each_object_carries_what_holds_it_from_the_place_s_relations(tmp_path):
    """Issue #72: the record carries each object's relation (score/review/holders) for the assembly to lay it by. On a
    20 by 20 m plan (place (x, z) is plan (x - 10, y - 10)): the door the plan writer left on the walls item stands in
    its opening at plan (5, 0), place (-5, -10), turned along its wall, `in` with its 1.4 m width and 2.2 m height;
    the garage door against its module's S face names the module's object and points out +z; the wall lamp against
    the west wall's room face, the face 0.1 m in at x -9.9, pointing out +x. Relations derived from another plan
    than the kept one are left out, with why.
    Break: score/stages/scene_record/writer.py: `spot, way, base, on = related(design, relation, spot, way, base,
        size, piece)` -> `pass`
    Break: score/stages/scene_record/writer.py: `on["holder"] = names` -> `pass`
    Break: score/stages/scene_record/writer.py: `found["room"] = float(recess["room"])` -> `pass`
    Break: score/stages/scene_record/writer.py: `**({"hangs": True} if relation.get("hangs") else {})}` -> `}` (the
        docking airlock's spacesuit, hanging in its locker, laid as standing in it)
    And the 2026-11-04 audit's laid-as-designed gate: the wall lamp's front faces out of its wall into the room (it
    was laid with its back to the room), at its relation's 2 m height; a lamp hung from the roof has its top 0.01 m
    under the place's 3 m ceiling; a chair before the module stands at its piece's spot, naming the module; the
    gate passes on them and fails, by name, on the lamp turned to its wall, two lamps at one spot, the hung lamp
    1 m lower and the chair 1.2 m off its holder.
    Break: score/stages/scene_record/writer.py: `along = np.subtract(wall["to"], wall["from"]) * -float(relation["side"])`
        -> `along = np.subtract(wall["to"], wall["from"])`
    Break: score/stages/scene_record/writer.py: `base = roof_under(design, spot) - float(size[2]) - ROOF_CLEAR` -> `pass`
    Break: score/stages/scene_record/gates.py: `found.append(f"{entry['name']} faces its wall, its back to the room")`
        -> `pass`
    A wall's face ends at the faces of the walls meeting its ends, never at their middle lines (storage's 7.7 m pipes
    on its 7.52 m east line went 0.084 m into its north and south walls, 2026-11-10): the east wall of a 20 m square
    of 0.2 m walls holds its things from z -9.9 to 9.9, and a facet meeting it straight on trims nothing.
    Break: score/stages/scene_record/writer.py: `first, last = holders.corner_trims(design, start, end)` ->
        `first, last = 0.0, 0.0`
    Break: score/stages/scene_record/gates.py: `found.append(f"{one['name']} and {other['name']} of row {row} stand
        at one spot")` -> `pass`
    Break: score/stages/scene_record/gates.py: `if abs(height + size[2] - under) > TOLERANCE:` -> `if False:`
    Break: score/stages/scene_record/gates.py: `if not -TOLERANCE <= gap <= SEAT_REACH:` -> `if False:`
    2026-11-06 (the engine room's railings piled 1 to 4 m over one another, passing every gate): a crate its relation
    stands on the floor passes on the floor, on the module's 6 m top, on a 1 m deck under it and half way up a flight
    rising 0 to 2 m, and fails 1 m up over nothing, and 1 m up on a crate of its own row, unless its row piles.
    Break: score/stages/scene_record/gates.py: `and not ground_under(spots, height, design)}` -> `and False}`
    Break: score/stages/scene_record/gates.py: `(other["row"] != checked[name][0]["row"] or` -> `(True or`
    Break: score/stages/scene_record/gates.py: `holders.piles(rows.get(other["row"]) or {})))}` -> `False))}`
    Break: score/stages/scene_record/gates.py: `and any(design_shell.inside(spot, level["points"]) for spot in
        spots)] + [` -> `and False] + [`
    Break: score/stages/scene_record/gates.py: `min(max(height, float(stair["from"])), float(stair["to"]))` ->
        `float(stair["from"])`
    2026-11-06 (hangar's second 32 m pipe laid as a chord across its left and front walls' corner, passing every
    gate): a wall thing whose face runs from one wall round their corner onto the other fails; one flat along a wall
    passes, and so does a chord over two walls meeting 20 degrees apart (a round wall's facets).
    Break: score/stages/scene_record/gates.py: `if at[0] != at[1]:` -> `if False:`
    Break: score/review/holders/__init__.py: `if turn > ROUND_BEND:` -> `if False:` (the chord over facets fails)
    2026-11-07 (laid-as-designed@habitat): a chord over its facets round a closed room passes too, its far end placed
    where its face runs on from its near one, never on the chain's other pass round the room.
    Break: score/stages/scene_record/gates.py: `holders.chain_along(chain, ends[1], near=first)` ->
        `holders.chain_along(chain, ends[1])`
    2026-11-06 (the square's lantern strings 6 m over its plaza): a thing hung between holders (holders' `hung`)
    passes while both of them stand as high as it hangs, and fails hung over the top of one; a floor relation's
    `height` (holders.stood_under: the square's stage screen stood at its deck's 3.3 m behind it) is where the
    record stands its object, over its plan base.
    Break: score/stages/scene_record/gates.py: `if len(held) < 2:` -> `if False:`
    Break: score/stages/scene_record/gates.py: `hung_faults(objects, design, sizes, relations, standing)` -> `[]`
    Break: score/stages/scene_record/writer.py: `base = float(relation.get("height", base))` -> `pass`
    2026-11-06 (hangar's 32 m pipes at 10 m in one another on its left and front walls, passing every gate): a second
    lamp on the west wall 0.1 m along from the first fails, inside it; one just its length and 0.02 m along, touching,
    passes, and so does one 0.1 m along stood its tall and a gap over it.
    Break: score/stages/scene_record/gates.py: `for depth in [holders.boxes_meet(box, other)] if depth >
        holders.WALL_TOUCH]` -> `for depth in [holders.boxes_meet(box, other)] if False]`
    Break: score/review/holders/__init__.py: `return min(ground, min(first[6], second[6]) - max(first[5], second[5]))`
        -> `return ground` (the lamp stood over the first fails)
    #94: the garage door its relation says rests leaning carries `rests` leaning for the settle to lean it by; the
    door, resting as the others lay it, carries none.
    Break: score/stages/scene_record/writer.py: `**({"rests": relation["rests"]} if relation and relation.get("rests")
        else {})` -> `**{}`"""
    from score.stages.scene_record import gates, writer
    design = {"w": 20.0, "d": 20.0, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 20.0, 20.0, None, "item"],
                                              ["MODULE 1", 8.0, 2.0, 6.0, 6.0, None, "item"],
                                              ["GARAGE DOOR 1", 4.0, 9.0, 3.0, 3.0, None, "item"],
                                              ["SUIT 1", 9.0, 3.0, 0.5, 0.5, None, "item"],
                                              ["HUNG 1", 2.0, 2.0, 1.0, 1.0, None, "item"],
                                              ["CHAIR 1", 10.0, 12.0, 2.0, 2.0, None, "item"]],
              "rows": {"ON THE WALLS AND CEILING": ["door", "lamp"], "MODULE 1": ["module"],
                       "GARAGE DOOR 1": ["garage_door"], "SUIT 1": ["suit"], "HUNG 1": ["hung"],
                       "CHAIR 1": ["chair"]}}
    rows = [{"id": name, "anchor": "floor", "route": "prop", "size": size}
            for name, size in (("door", [1.2, 0.1, 2.1]), ("lamp", [0.3, 0.2, 0.3]), ("module", [6.0, 6.0, 6.0]),
                               ("garage_door", [3.0, 0.2, 3.0]), ("suit", [0.5, 0.4, 1.8]), ("hung", [0.4, 0.4, 0.5]),
                               ("chair", [0.6, 0.6, 1.0]), ("crate", [1.0, 1.0, 1.0]))]
    relations = {"relations": [
        *[{"item": f"CRATE {number}", "row": "crate", "how": "floor", "why": "on the place's floor"}
          for number in (1, 2)],
        {"item": "ON THE WALLS AND CEILING", "row": "door", "how": "in", "why": "in the plan's door opening 1",
         "opening": {"at": [5.0, 0.0], "wide": 1.4, "sill": 0.0, "head": 2.2},
         "wall": {"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}},
        {"item": "ON THE WALLS AND CEILING", "row": "lamp", "how": "wall", "why": "against the wall nearest",
         "wall": {"from": [0.0, 20.0], "to": [0.0, 0.0], "thick": 0.2}, "side": 1, "spot": [0.0, 10.0],
         "height": 2.0},
        {"item": "HUNG 1", "row": "hung", "how": "ceiling", "to roof": True, "why": "on the place's ceiling"},
        {"item": "CHAIR 1", "row": "chair", "how": "floor", "beside": "MODULE 1", "holder row": "module",
         "pieces": [{"how": "floor", "spot": [11.0, 8.4], "way": [1.0, 0.0], "why": "before module's S side"}],
         "why": "before module"},
        {"item": "GARAGE DOOR 1", "row": "garage_door", "how": "face", "holder": "MODULE 1", "face": "S",
         "why": "against module's side", "recess": {"room": 0.55, "room_way": [-1.0, 0.0]}, "rests": "leaning"},
        {"item": "SUIT 1", "row": "suit", "how": "within", "holder": "MODULE 1", "why": "within module", "hangs": True}]}
    found = {entry["row"]: entry for entry in writer.design_objects(design, {"rows": rows, "objects": {}}, relations)}
    door, lamp, garage = found["door"], found["lamp"], found["garage_door"]
    assert door["at"] == [-5.0, 0.0, -10.0] and door["on"]["how"] == "in", door
    assert door["on"]["middle"] == [-5.0, 0.0, -10.0] and door["on"]["wide"] == 1.4 and door["on"]["tall"] == 2.2
    assert door["rotation"] == writer.yaw_turn(design, (1.0, 0.0), rows[0]["size"]), door
    assert garage["on"]["holder"] == ["module_1"] and garage["on"]["out"] == [0.0, 1.0], garage
    assert garage["rests"] == "leaning" and "rests" not in door, (garage, door)
    assert (garage["on"]["room"], garage["on"]["room_way"]) == (0.55, [-1.0, 0.0]), garage  # kept within the face
    assert lamp["on"]["span"] == [[-9.9, 10.0], [-9.9, -10.0]] and lamp["on"]["out"] == [1.0, 0.0], lamp
    assert lamp["rotation"] == writer.yaw_turn(design, (0.0, 1.0), rows[1]["size"]) and lamp["at"][1] == 2.0, lamp
    assert found["hung"]["at"][1] == round(3.0 - 0.5 - writer.ROOF_CLEAR, 4), found["hung"]
    assert found["chair"]["at"] == [1.0, 0.0, -1.6] and found["chair"]["beside"]["holder"] == ["module_1"], found
    objects = [entry for entry in found.values() if entry["kind"] == "object"]
    sizes, by_id = {row["id"]: row["size"] for row in rows}, {row["id"]: row for row in rows}

    def faults(laid, kinds=by_id, plan=design):
        return (gates.spot_faults(laid) + gates.held_wall_faults(laid, plan, sizes, kinds) +
                gates.wall_overlap_faults(laid, plan, sizes) +
                gates.roof_faults(laid, plan, sizes, relations, {**kinds, "hung": {"anchor": "ceiling"}}) +
                gates.seat_faults(laid, sizes, {**kinds, "chair": {"id": "chair", "noun": "chair",
                                                                   "where": "at the module"}}, plan) +
                gates.floor_faults(laid, plan, sizes, relations, kinds))
    assert faults(objects) == [], faults(objects)
    turned = [{**entry, "rotation": writer.yaw_turn(design, (0.0, -1.0), None)} if entry is lamp else entry
              for entry in objects]
    assert faults(turned) == ["lamp_1 faces its wall, its back to the room"], faults(turned)
    assert "lamp_1 and lamp_2 of row lamp stand at one spot" in faults(objects + [{**lamp, "name": "lamp_2"}])
    lowered = [{**entry, "at": [entry["at"][0], entry["at"][1] - 1.0, entry["at"][2]]} if entry["row"] == "hung"
               else entry for entry in objects]
    assert faults(lowered) == ["hung_1's top stands 1.99 m up, its roof's underside 3.00 m over it"], faults(lowered)

    def along(by, up=0.0):  # a second lamp `by` metres along the west wall from the first, `up` metres over it
        return {**lamp, "name": "lamp_9", "at": [lamp["at"][0], lamp["at"][1] + up, lamp["at"][2] + by]}
    assert faults(objects + [along(0.1)]) == [
        "lamp_1 and lamp_9 on the walls stand 0.20 m inside each other at their built sizes"], faults(objects + [along(0.1)])
    assert faults(objects + [along(0.32)]) == [] and faults(objects + [along(0.1, 0.35)]) == []
    away = [{**entry, "at": [1.0, 0.0, -0.5]} if entry["row"] == "chair" else entry for entry in objects]
    assert faults(away) == ["chair_1 stands 1.20 m from MODULE 1, its words 'at the module'"], faults(away)

    def crate(number, x, y, height):  # a crate at plan (x, y), `height` over the floor
        return {"name": f"crate_{number}", "row": "crate", "kind": "object", "at": [x - 10.0, height, y - 10.0],
                "rotation": writer.yaw_turn(design, (1.0, 0.0), [1.0, 1.0, 1.0]),
                "from": f"plan item 'CRATE {number}', inventory row crate: piece {number} of the row"}
    over = "stands 1.00 m over the floor with nothing under it, its row on the floor"
    assert faults(objects + [crate(1, 15.0, 15.0, 0.0), crate(2, 11.0, 5.0, 6.0)]) == []  # floor, the module's top
    assert faults(objects + [crate(1, 15.0, 15.0, 1.0)]) == [f"crate_1 {over}"]
    stacked = objects + [crate(1, 15.0, 15.0, 0.0), crate(2, 15.0, 15.0, 1.0)]
    assert faults(stacked) == [f"crate_2 {over}"], faults(stacked)
    assert faults(stacked, {**by_id, "crate": {"id": "crate", "size_words": "a stack of crates"}}) == []
    raised = {**design, "levels": [{"height": 1.0, "points": [[14.0, 14.0], [18.0, 14.0], [18.0, 18.0], [14.0, 18.0]]}],
              "stairs": [{"points": [[14.0, 1.0], [18.0, 1.0], [18.0, 3.0], [14.0, 3.0]], "from": 0.0, "to": 2.0}]}
    assert faults(objects + [crate(1, 16.0, 16.0, 1.0), crate(2, 16.0, 2.0, 1.0)], plan=raised) == []
    walled = {**design, "walls": [{"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2},
                                  {"from": [0.0, 0.0], "to": [0.0, 20.0], "thick": 0.2},
                                  {"from": [10.0, 20.0], "to": [15.0, 20.0], "thick": 0.2},
                                  {"from": [15.0, 20.0], "to": [19.698, 21.71], "thick": 0.2}]}

    def on_wall(name, first, second):  # a wall thing whose face runs from plan `first` to `second`
        return {"name": name, "on": {"how": "wall", "span": [[first[0] - 10.0, first[1] - 10.0],
                                                             [second[0] - 10.0, second[1] - 10.0]]}}
    assert gates.bent_faults([on_wall("flat_1", (0.1, 2.0), (0.1, 6.0)), on_wall("chord_1", (12.0, 19.9), (18.0, 21.0)),
                              on_wall("bent_1", (0.1, 4.0), (4.0, 0.1))], walled) == [
        "bent_1 is laid round a corner of its walls, its ends on two of their straight runs"]
    ring = [[0.0, 2.757], [2.757, 0.0], [6.829, 0.0], [9.823, 2.994], [9.823, 6.592], [7.906, 9.101], [4.308, 9.823],
            [2.757, 9.101], [1.325, 7.669], [0.0, 5.989]]  # habitat's walls round its room, 2026-11-07
    ringed = {**design, "walls": [{"from": start, "to": end, "thick": 0.2}
                                  for start, end in zip(ring, ring[1:] + ring[:1])]}
    assert gates.bent_faults([on_wall("pipe_8", (3.285, 9.056), (1.043, 7.062))], ringed) == []  # its facets' chord
    strung = {"relations": [{"item": "CRATE 3", "row": "crate", "how": "hung", "holders": ["MODULE 1", "CRATE 4"],
                              "why": "hung between them"}, {"item": "CRATE 4", "row": "crate", "how": "floor",
                                                           "why": "on the place's floor"}]}
    assert gates.floor_faults(objects + [crate(3, 15.0, 15.0, 0.5), crate(4, 16.0, 2.0, 0.0)], design, sizes, strung,
                              by_id) == []
    assert gates.floor_faults(objects + [crate(3, 15.0, 15.0, 3.0), crate(4, 16.0, 2.0, 0.0)], design, sizes, strung,
                              by_id) == ["crate_3 hangs 3.00 m over the floor between MODULE 1 and CRATE 4, 1 of them "
                                         "standing that high"]
    assert writer.related(design, {"how": "floor", "height": 0.0, "why": "on what is under it"}, [1.0, 1.0],
                          [1.0, 0.0], 3.3, [1.0, 1.0, 1.0])[2] == 0.0
    assert found["suit"]["on"]["hangs"] is True and found["suit"]["on"]["holder"] == ["module_1"], found["suit"]
    square = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
    boxed = {**design, "walls": [{"from": start, "to": end, "thick": 0.2}
                                 for start, end in zip(square, square[1:] + square[:1])]}
    ends, out = writer.wall_face(boxed, {"from": [20.0, 0.0], "to": [20.0, 20.0], "thick": 0.2}, 1)
    assert np.allclose(sorted(map(list, ends)), [[9.9, -9.9], [9.9, 9.9]]) and np.allclose(out, [-1.0, 0.0]), ends
    straight = {**design, "walls": [{"from": [20.0, 0.0], "to": [20.0, 20.0], "thick": 0.2},
                                    {"from": [20.0, 20.0], "to": [20.0, 30.0], "thick": 0.2}]}
    assert np.allclose(sorted(map(list, writer.wall_face(straight, straight["walls"][0], 1)[0])),
                       [[9.9, -10.0], [9.9, 10.0]])
    (tmp_path / "plans").mkdir()
    (tmp_path / "plans/hut.json").write_text(json.dumps(design))
    (tmp_path / "relations.json").write_text(json.dumps({**relations, "plan": "another plan's sha"}))
    assert writer.relations_input({"plans": tmp_path / "plans", "relations": tmp_path / "relations.json"}, "hut") == (
        None, "the relations were derived from another plan than the kept one (score/review/holders keep)")
    from score.review import holders
    assert writer.design_shell.KEPT_RELATIONS == holders.KEPT  # the row reads its relations where holders.keep keeps them


def test_a_facade_stands_past_its_edge_and_what_is_left_unplaced_is_marked():
    """Street (2026-10-29): on a 6 x 30 m plan (place (x, z) is plan (x - 3, y - 15)) its 3 m deep facade the plan
    writer left on the walls item stands past the W edge, its middle 1.5 m out, at place (-4.5, 0), its long side
    along the edge; the AC unit on it names the facade's object alone of the walls item's (its holder row), not the
    crate also left there, which stands marked unplaced; a door with no relation is marked as filling an opening; a
    row its relations name nothing holding is marked unheld.
    Break: score/stages/scene_record/writer.py: `return np.asarray(relation["spot"], float) + out * depth / 2,
        np.array([out[1], -out[0]]), base, None` -> `return spot, way, base, None`
    Break: score/stages/scene_record/writer.py: `if rows.get(name) == on.get("holder row", rows.get(name))]` -> `]`
    Break: score/stages/scene_record/writer.py: `if item[0] == WALLS_ITEM and not placed:` -> `if False:`"""
    from score.stages.scene_record import writer
    design = {"w": 6.0, "d": 30.0, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 6.0, 30.0, None, "item"],
                                             ["AC 1", 0.5, 10.0, 0.8, 0.4, None, "item"],
                                             ["DOOR 1", 5.0, 5.0, 1.0, 0.1, None, "item"],
                                             ["LAMP 1", 2.0, 2.0, 0.3, 0.3, None, "item"]],
              "rows": {"ON THE WALLS AND CEILING": ["facade", "crate"], "AC 1": ["ac"], "DOOR 1": ["door"],
                       "LAMP 1": ["lamp"]}}
    rows = [{"id": name, "anchor": "floor", "route": "prop", "size": size, "noun": noun}
            for name, size, noun in (("facade", [3.0, 36.0, 24.0], "facade"), ("crate", [1.0, 1.0, 1.0], "crate"),
                                     ("ac", [0.8, 0.4, 0.6], "air conditioner"), ("door", [1.0, 0.1, 2.1], "door"),
                                     ("lamp", [0.3, 0.3, 0.3], "lamp"))]
    relations = {"relations": [
        {"item": "ON THE WALLS AND CEILING", "row": "facade", "how": "edge", "edge": "W", "spot": [0.0, 15.0],
         "why": "past the plan's W edge"},
        {"item": "AC 1", "row": "ac", "how": "face", "holder": "ON THE WALLS AND CEILING", "holder row": "facade",
         "face": "E", "why": "against facade's face toward the place"}],
        "unheld": [{"item": "LAMP 1", "row": "lamp", "why": "its holder stage is neither laid nor a wall"}]}
    found = {entry["row"]: entry for entry in writer.design_objects(design, {"rows": rows, "objects": {}}, relations)}
    assert found["facade"]["at"] == [-4.5, 0.0, 0.0] and "unplaced" not in found["facade"], found["facade"]
    assert found["facade"]["rotation"] == writer.yaw_turn(design, (0.0, 1.0), rows[0]["size"]), found["facade"]
    assert found["ac"]["on"]["holder"] == ["facade_1"] and found["ac"]["on"]["out"] == [1.0, 0.0], found["ac"]
    assert found["crate"]["unplaced"].startswith("the plan writer left it"), found["crate"]
    assert found["door"]["fills"] is True and found["lamp"]["unheld"].startswith("its holder stage"), found


def test_each_door_on_a_face_stands_at_the_spot_its_relation_gives():
    """Street (#36): its three restaurant doors on one 1.74 m item were laid evenly along it, 0.58 m apart, their
    recesses in one another. Where the relation gives each piece its `spots` (score/review/holders face_spots), each
    door stands at its own: on a 6 x 30 m plan (place (x, z) is plan (x - 3, y - 15)) at place z -1.4, 0, 1.4.
    Break: score/stages/scene_record/writer.py: `spot = np.asarray(relation["spots"][min(piece,
        len(relation["spots"]) - 1)], float)` -> `pass`"""
    from score.stages.scene_record import writer
    design = {"w": 6.0, "d": 30.0, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 6.0, 30.0, None, "item"],
                                             ["DOOR 1", 1.8, 14.13, 0.5, 1.74, "E", "item"]],
              "rows": {"ON THE WALLS AND CEILING": ["facade"], "DOOR 1": ["door"]}}
    rows = [{"id": "facade", "anchor": "floor", "route": "prop", "size": [3.0, 36.0, 24.0], "noun": "facade"},
            {"id": "door", "anchor": "on:facade", "route": "prop", "size": [1.0, 0.1, 2.1], "noun": "door",
             "count": 3}]
    relations = {"relations": [
        {"item": "ON THE WALLS AND CEILING", "row": "facade", "how": "edge", "edge": "W", "spot": [0.0, 15.0],
         "why": "past the plan's W edge"},
        {"item": "DOOR 1", "row": "door", "how": "face", "holder": "ON THE WALLS AND CEILING", "holder row": "facade",
         "face": "E", "why": "against facade's face toward the place",
         "spots": [[2.05, 13.6], [2.05, 15.0], [2.05, 16.4]]}]}
    doors = [entry for entry in writer.design_objects(design, {"rows": rows, "objects": {}}, relations)
             if entry["row"] == "door"]
    assert [round(door["at"][2], 3) for door in doors] == [-1.4, 0.0, 1.4], doors


def test_a_ramp_stands_up_its_way_to_its_level_s_edge():
    """Airlock (settle@airlock, 2026-10-30): its ramp stood at its plan item, along its porch deck's edge, its end in
    the deck. With its relation (score/review/holders up_to_level), on a 20 by 20 m plan (place (x, z) is plan
    (x - 10, y - 10)) it stands at the relation's spot, plan (8.9, 12), place (-1.1, 2), its long side turned up the
    way east, and its `on` gives the assembly the level's edge at place x -0.1, the way up +x and the level's 0.2 m
    top.
    Break: score/stages/scene_record/writer.py: `return (np.asarray(relation["spot"], float),
        np.asarray(relation["way"], float), base,` -> `return (spot, way, base,`"""
    from score.stages.scene_record import writer
    design = {"w": 20.0, "d": 20.0, "items": [["RAMP 1", 8.0, 9.0, 1.2, 2.0, None, "item"]],
              "rows": {"RAMP 1": ["ramp"]}}
    rows = [{"id": "ramp", "anchor": "ground", "route": "shell", "size": [1.2, 2.0, 0.2], "noun": "ramp"}]
    relations = {"relations": [{"item": "RAMP 1", "row": "ramp", "how": "ramp", "spot": [8.9, 12.0], "way": [1.0, 0.0],
                                "edge": [[9.9, 14.0], [9.9, 8.0]], "height": 0.2, "why": "up to the porch deck"}]}
    [ramp] = writer.design_objects(design, {"rows": rows, "objects": {}}, relations)
    assert ramp["at"] == [-1.1, 0.0, 2.0] and ramp["rotation"] == writer.yaw_turn(design, (1.0, 0.0), rows[0]["size"])
    assert ramp["on"] == {"how": "ramp", "edge": [[-0.1, 4.0], [-0.1, -2.0]], "up": [1.0, 0.0], "top": 0.2,
                          "why": "up to the porch deck"}, ramp


def test_an_arched_rib_is_laid_as_the_shell_s_band_at_each_of_its_plan_items():
    """Batch 1's retry: the tube's ribs, their box the whole picture, framed no close-up. The shell lays an arched
    structure row (design_shell.arched) as an `arch` at each plan item tied to it, at the row's size, named its row,
    painted as a wall; a block of no band, or a row of no structure, is not arched. The first rib's item (0, 1) 8 x
    0.2 m lies east-west across the shed: its 3.2 m span centred at plan x 4, its feet at -1.6 and 1.6, z -1.9.
    Break: score/stages/scene_record/writer.py: `way = np.array([1.0, 0.0]) if wide >= deep else np.array([0.0, 1.0])`
        -> `way = np.array([0.0, 1.0])`"""
    from pxr import Usd
    from score.stages.earth_seed import design_shell
    from score.stages.scene_record import writer
    sys.path.insert(0, str(REPO / "tools/usd"))
    import scene
    rib = {"id": "structural_ribs", "name": "arched structural ribs", "noun": "ribs", "part": "structure",
           "route": "plan", "size": [3.2, 0.2, 3.2], "count": 2}
    assert design_shell.arched(rib) and not design_shell.arched({**rib, "size": [3.2, 2.0, 3.2]})
    assert not design_shell.arched({**rib, "part": "object"})
    design = {**WRITTEN, "items": [*WRITTEN["items"], ["RIBS 1", 0.0, 1.0, 8.0, 0.2, None, "item"],
                                   ["RIBS 2", 0.0, 4.0, 8.0, 0.2, None, "item"]],
              "rows": {**WRITTEN["rows"], "RIBS 1": ["structural_ribs"], "RIBS 2": ["structural_ribs"]}}
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, design)
        (pathlib.Path(folder) / "hand-in.json").write_text(json.dumps({**HANDIN, "rows": [*HANDIN["rows"], rib]}))
        record = writer.record_of(json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text()), design,
                                  inputs)
    ribs = [entry for entry in record["structure"] if entry["builder"] == "arch"]
    assert [entry["name"] for entry in ribs] == ["structural_ribs_1", "structural_ribs_2"], ribs
    assert all(entry["row"] == "structural_ribs" and entry["plain"] == "shell" for entry in ribs), ribs
    assert ribs[0]["feet"] == [[-1.6, -1.9], [1.6, -1.9]] and ribs[0]["low"] == 0.0, ribs[0]  # the item's middle
    assert "structural_ribs" not in {entry["row"] for entry in record["objects"]}  # no model take waits for it
    stage = Usd.Stage.CreateInMemory()
    scene.write_structure(stage, "tube", ribs)
    built = scene.built_meshes(ribs[0])[0]["points"]
    assert np.allclose(built.min(0), [-1.6, 0.0, -2.0]) and np.allclose(built.max(0), [1.6, 3.2, -1.8]), built
    mesh = stage.GetPrimAtPath("/tube/Structure/structural_ribs_1")
    assert mesh.GetAttribute("score:row").Get() == "structural_ribs", mesh


def test_a_floodlight_tower_read_as_a_tower_gets_a_light_at_its_head():
    """A yard with a 1 by 1 by 10 m floodlight tower (a stem by its metres) read as a tower (the reading's noun) and a
    light switch: the tower's plan
    item gets one library lamp near its top over its middle, the switch none (score/stages/row_kinds.py held_by).
    Break: score/stages/scene_record/writer.py: `high = base + tall * share` -> `high = base + share`"""
    from score.stages.scene_record import writer
    design = {**WRITTEN, "items": [["TOWER", 3.0, 2.0, 1.0, 1.0, None, "item"], ["SWITCH", 1.0, 1.0, 0.1, 0.1, None,
                                                                                    "item"]],
              "rows": {"TOWER": ["floodlight_tower"], "SWITCH": ["light_switch"]},
              "shapes": {"TOWER": {"shape": "rect", "tall": 10.0, "base": 0.0}}}
    rows = [{"id": "floodlight_tower", "name": "floodlight tower", "noun": "tower", "anchor": "on:yard",
             "size": [1.0, 1.0, 10.0]},
            {"id": "light_switch", "name": "light switch", "noun": "switch", "anchor": "wall"}]
    with tempfile.TemporaryDirectory() as folder:
        (pathlib.Path(folder) / "inventory.json").write_text(json.dumps({"scene": "shed", "rows": rows}))
        [lamp] = writer.lights(design, {"inventory": pathlib.Path(folder) / "inventory.json",
                                        "row kinds": REPO / "data/checks/row-kinds.json",
                                        "lamp library": REPO / "data/library/lamps.json"})
    assert lamp["at"][1] == 9.5 and "floodlight_tower" in lamp["from"] and lamp["range"] == 14.25, lamp


def test_a_row_its_concept_shows_glowing_gets_a_light_in_its_colour():
    """An engine room's core (a machine: its row kind does not glow) its concept shows glowing blue at half the
    brightest light gets the library's lamp over its plan item in that blue at half the lamp's strength; the engine
    its concept shows dark and the starry sky (the physics') get none (reading.concept_light, kept as
    {home}/design/light/<place>.json).
    Break: score/stages/scene_record/writer.py:
        `"energy": round(energy * light["strength"] * (float(glow["brightness"]) if glow else 1.0), 4),`
        -> `"energy": round(energy * light["strength"], 4),`
    Break: score/stages/scene_record/writer.py:
        `for row in inventory["rows"] if row["id"] in shown and row.get("anchor") != "sky"}`
        -> `for row in inventory["rows"] if row["id"] in shown}`
    Break: score/stages/scene_record/concept_light.py: `PROPS_HOME / "design" / "light"` -> `PROPS_HOME / "light"`
        (the row reads its concept light where plans.keep keeps none)
    Break: score/stages/scene_record/writer.py: `counts[number % len(counts)] += 1` -> `pass` (four counted screens
        on two items lay two lamps)
    Break: score/stages/scene_record/writer.py: `return (float(emitter["share"]), "emitter") if said & set(emitter[
        "words"]) else (1.0, "source")` -> `return 1.0, "source"` (a screen throws a lamp's light)
    Break: score/stages/scene_record/writer.py: `set(emitter["words"]) | CONTROL_FACES` -> `set(emitter["words"])`
        (a door's keypad throws a lamp's light: shiplock, 2026-11-10)"""
    from score.review import plans
    from score.stages.scene_record import concept_light, writer
    assert concept_light.KEPT_LIGHT == plans.KEPT_LIGHT
    design = {**WRITTEN, "items": [["CORE", 3.0, 2.0, 1.0, 1.0, None, "item"], ["ENGINE", 1.0, 1.0, 2.0, 1.0, None,
                                                                                  "item"],
                                   ["SKY", 0.0, 0.0, 1.0, 1.0, None, "item"],
                                   ["SCREENS", 1.0, 4.0, 3.0, 0.5, None, "item"],
                                   ["SCREENS 2", 5.0, 4.0, 2.0, 0.5, None, "item"]],
              "rows": {"CORE": ["core"], "ENGINE": ["engine"], "SKY": ["sky"], "SCREENS": ["screens"],
                       "SCREENS 2": ["screens"]},
              "shapes": {"CORE": {"shape": "rect", "tall": 3.0, "base": 0.0}}}
    rows = [{"id": "core", "name": "energy core", "noun": "core", "anchor": "floor", "size": [1.0, 1.0, 3.0]},
            {"id": "engine", "name": "engine", "noun": "engine", "anchor": "floor", "size": [2.0, 1.0, 1.0]},
            {"id": "sky", "name": "starfield", "noun": "sky", "anchor": "sky"},
            {"id": "screens", "name": "wall monitors", "noun": "monitor", "anchor": "floor", "count": 4}]
    dark = {"glows": False, "glowing": "", "colour": "", "brightness": 0}
    light = {"rows": {"core": {"glows": True, "glowing": "its column", "colour": "#44aaff", "brightness": 0.5},
                      "screens": {"glows": True, "glowing": "screens", "colour": "#44aaff", "brightness": 0.5},
                      "engine": dark,
                      "sky": {"glows": True, "glowing": "stars", "colour": "#ffffff", "brightness": 0.4}},
             "scene": {"daylight": False, "unseen": False, "unseen_colour": ""}}
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "inventory.json").write_text(json.dumps({"scene": "shed", "rows": rows}))
        (folder / "light.json").write_text(json.dumps(light))
        inputs = {"inventory": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
                  "lamp library": REPO / "data/library/lamps.json"}
        assert writer.lights(design, inputs) == []  # its row kinds alone light nothing
        lamp, *screens = writer.lights(design, {**inputs, "concept light": folder / "light.json"})
        [full] = writer.item_lamps(design["items"][0], {**rows[0], "row_kind": "machine"}, rows, design,
                                   writer.library_lamps(), inputs["lamp library"])
        [bulb] = writer.item_lamps(design["items"][3], {**rows[3], "id": "bulbs", "name": "bulbs", "noun": "bulb"},
                                   rows, design, writer.library_lamps(), inputs["lamp library"],
                                   {**light["rows"]["screens"], "glowing": "bulbs"})
    assert lamp["colour"] == "#44aaff" and "its column" in lamp["from"] and "core" in lamp["from"], lamp
    assert lamp["energy"] == round(full["energy"] / 2, 4) and lamp["at"] == full["at"]
    # four counted screens on two items (3 m from x 1, 2 m from x 5): two lamps along each, at 1.75, 3.25, 5.5 and
    # 6.5 m (x -2.25, -0.75, 1.5, 2.5 on the shed's 8 m), each a faint emitter at 0.1 of the lamp (lamps.json
    # `glowing`), never one lamp an item as a room light
    assert [screen["at"][0] for screen in screens] == [-2.25, -0.75, 1.5, 2.5], screens
    assert all(screen["row"] == "screens" and "faint emitter" in screen["from"] and
               abs(screen["energy"] - bulb["energy"] * 0.1) <= 1e-4 for screen in screens), (screens, bulb)
    # a door whose concept shows its keypad glowing is a faint emitter, its light a lamp still
    door = {"id": "sliding_door", "name": "sliding door", "noun": "door"}
    assert writer.glow_share(door, {"glowing": "keypad"}, inputs["lamp library"]) == (0.1, "emitter")
    assert writer.glow_share(door, {"glowing": "light panel"}, inputs["lamp library"]) == (1.0, "source")


def test_a_glowing_panel_drawn_as_the_whole_room_has_its_lamp_on_its_wall():
    """Engineroom (#36): a glowing wall panel the plan draws as the whole room (7 x 5 m of the 8 x 6 m shed), held on
    the east wall at its middle (plan 8, 3), has its lamp on that wall's face (x 7.9) 0.1 m out into the room, at
    plan (7.8, 3), as high as the wall mount says on the shed's 3 m walls (1.5 m), never over the room's middle; the
    plan-matched gate takes it there, off its item's box, and fails it moved off its wall.
    Break: score/stages/scene_record/writer.py: `walled = relation is not None and relation.get("how") == "wall" and
        holders.outlines_room(item, design)` -> `walled = False`
    Break: score/stages/scene_record/gates.py: `if light.get("against"):` -> `if False:`
    Break: score/stages/scene_record/writer.py: `if pieces == 1 else length * (piece + 0.5) / pieces` -> `if True
        else 0.0` (three panels' lamps on one spot)"""
    from score.stages.scene_record import gates, writer
    design = {**WRITTEN, "items": [["PANEL", 0.5, 0.5, 7.0, 5.0, None, "item"]], "rows": {"PANEL": ["wall_panel"]},
              "shapes": {}}
    rows = [{"id": "wall_panel", "name": "wall panel", "noun": "panel", "anchor": "wall", "size": [8.0, 6.0, 3.0]}]
    light = {"rows": {"wall_panel": {"glows": True, "glowing": "its lamps", "colour": "#ffeedd", "brightness": 1.0}}}
    relations = {"relations": [{"item": "PANEL", "row": "wall_panel", "how": "wall", "side": 1, "spot": [8.0, 3.0],
                                "wall": {"from": [8.0, 0.0], "to": [8.0, 6.0], "thick": 0.2}, "why": "its free wall"}]}
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "inventory.json").write_text(json.dumps({"scene": "shed", "rows": rows}))
        (folder / "light.json").write_text(json.dumps(light))
        [lamp] = writer.lights(design, {"inventory": folder / "inventory.json", "concept light": folder / "light.json",
                                        "row kinds": REPO / "data/checks/row-kinds.json",
                                        "lamp library": REPO / "data/library/lamps.json"}, relations)
    (spot,), floor = writer.in_frame(design, [[7.8, 3.0]], 1.5)
    assert lamp["at"] == [spot[0], floor, spot[1]], lamp
    assert gates.lamp_faults({"lights": [lamp]}, design) == []
    moved = {**lamp, "at": [lamp["at"][0] - 1.0, *lamp["at"][1:]]}
    assert gates.lamp_faults({"lights": [moved]}, design) == ["the light of plan item 'PANEL' stands off its wall"]
    # read as three panels: three lamps spread along the face, at the middles of its thirds (plan y 1, 3 and 5)
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        (folder / "inventory.json").write_text(json.dumps({"scene": "shed", "rows": [{**rows[0], "count": 3}]}))
        (folder / "light.json").write_text(json.dumps(light))
        three = writer.lights(design, {"inventory": folder / "inventory.json", "concept light": folder / "light.json",
                                       "row kinds": REPO / "data/checks/row-kinds.json",
                                       "lamp library": REPO / "data/library/lamps.json"}, relations)
    spots, _ = writer.in_frame(design, [[7.8, 1.0], [7.8, 3.0], [7.8, 5.0]], 1.5)
    assert [[found["at"][0], found["at"][2]] for found in three] == [list(spot) for spot in spots], three
    assert gates.lamp_faults({"lights": three}, design) == []


def test_the_shell_and_stairs_take_the_scene_librarys_surfaces():
    """Each shell part and stair takes the variant the scene's surface library gives its kind (a stair the floor's
    when the library names no stair), and a part it gives none, or every part while no library is made, carries no
    surface and says why; the scene builder names that on the mesh and binds nothing.
    Break: score/stages/scene_record/writer.py: `    return dict(entry, surface=surface)` -> `    return dict(entry,
        surface="deck_plate")`
    Break: score/stages/earth_seed/design_shell.py: `return f"{place}: the scene's surface library is not made (run
        surface-library first): its {kind} has none"`
        -> `return f"{place}: no surface"`
    Break: score/stages/earth_seed/design_shell.py: `return next((name for name in found if set(name.split("_")) &
        set(words)), found[0])` -> `return found[0]` (docking_airlock's floor painted with its ochre edging)"""
    from pxr import Usd
    from score.stages.scene_record import writer
    sys.path.insert(0, str(REPO / "tools/usd"))
    import scene
    with tempfile.TemporaryDirectory() as folder:
        made_library = pathlib.Path(folder) / "library"
        made_library.mkdir()
        (made_library / "materials.json").write_text(json.dumps({"kinds": {"wall": ["painted_panel"],
                                                                          "floor": ["deck_plate"]}}))
        (pathlib.Path(folder) / "with").mkdir()
        output, inputs = written(pathlib.Path(folder) / "with", WRITTEN)
        painted = {entry["name"]: entry for entry in writer.record_in(output)[1]["structure"]}
        record = writer.record_of(json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text()), WRITTEN,
                                  {**inputs, writer.LIBRARY_ROW: made_library})
        surfaces = {entry["name"]: entry for entry in record["structure"]}
    assert {surfaces["wall_1"]["surface"], surfaces["deck_1"]["surface"], surfaces["stair_1"]["surface"]} == \
        {"painted_panel", "deck_plate"} and surfaces["stair_1"]["surface"] == "deck_plate", surfaces
    roof = surfaces["roof_1"]
    from score.stages.earth_seed import design_shell
    edged = {"kinds": {"floor": ["hazard_frame_paint", "deck_floor_plate", "floor_vent_grate"],
                       "wall": ["hull_panel", "hull_recess"]}}
    assert design_shell.surface_for("deck", edged) == "deck_floor_plate"  # the floor's own, never its edging
    assert design_shell.surface_for("wall", edged) == "hull_panel"  # none named after it: its first
    assert design_shell.surface_for("roof", edged) is None
    assert roof["surface"] is None and "names no surface for the kinds a roof takes" in roof["surface_missing"], roof
    assert all(entry["surface"] is None and "not made" in entry["surface_missing"] for entry in painted.values()), \
        painted  # no library row read: every part named missing, none painted another way
    stage = Usd.Stage.CreateInMemory()
    scene.write_structure(stage, "shed", [roof])
    mesh = stage.GetPrimAtPath("/shed/Structure/roof_1")
    assert "roof takes" in mesh.GetAttribute("score:surface:missing").Get(), mesh
    assert not mesh.HasRelationship("material:binding"), mesh


def test_a_spot_looking_straight_down_is_given_the_floors_long_axis_as_its_up():
    """Round 33's spot-1 at shiplock looked straight down at the item under it with the world's up (0, 1, 0), so its
    picture had no sideways and every light measure was NaN (2026-10-30).

    Break: score/stages/scene_record/writer.py: `return [upright(view, plan["floor"]) for view in found]` ->
    `return found`"""
    from score.stages.scene_record import writer
    plan = {"floor": [[0.0, 0.0], [8.0, 6.0]], "floor_height": 0.0,
            "items": [{"name": "HATCH", "box": [3.0, 2.0, 5.0, 4.0]}],
            "standing": [{"at": [4.0, 3.0], "level": 3.0, "looks_at": "HATCH"},
                         {"at": [1.0, 1.0], "level": 0.0, "looks_at": None}]}
    down, level = writer.views(plan, 1.6)
    assert down["up"] == [1.0, 0.0, 0.0], down
    assert "up" not in level, level
    deep = writer.views(dict(plan, floor=[[0.0, 0.0], [6.0, 8.0]], standing=plan["standing"][:1]), 1.6)[0]
    assert deep["up"] == [0.0, 0.0, 1.0], deep
