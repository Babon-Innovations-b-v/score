"""A scene record is written from its design alone, on a plan of its own (a small shed beside a yard on a site): its
plan maps, and an item with no rows, a door that says nowhere it leads and a sealed door the layout leaves open each
fail `mapped`; a written plan with no corner takes its outline; the record holds the shell cut round its door, its
stair, a light over its lamp, the sky from the physics, the places its doors lead to and its backdrop rows are shown
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
from score.stages.scene_record import plan  # noqa: E402

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


def made(folder, record):
    """plan@shed made into `folder` from `record`, as the table hands it (its kit the plan itself: plan_as_kit)."""
    folder = pathlib.Path(folder)
    plans = folder / "plans"
    plans.mkdir()
    (plans / "yard.json").write_text(json.dumps({"title": "YARD", "w": 20.0, "d": 12.0, "leads": {}}))
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
        `found.append(f"{name} is sealed but the room layout leaves it open (no leaf shuts it)")` -> `pass`"""
    with tempfile.TemporaryDirectory() as folder:
        out, inputs = made(folder, SHED)
        found = plan.judge_mapped(out, inputs, None)
        assert found.answer == checks.PASS, (found.reason, found.findings)
        assert [door["leads"] for door in json.loads((out / "plan.json").read_text())["doors"]] == ["yard", "outside"]
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
                         "head": 2.1, "to": "yard"}],
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
SITE = {"title": "SITE", "w": 40.0, "d": 20.0, "leads": {},
        "holds": [{"place": "shed", "row": "shed", "x": 2.0, "y": 2.0, "w": 8.0, "d": 6.0},
                  {"place": "yard", "row": "yard", "x": 12.0, "y": 2.0, "w": 20.0, "d": 12.0}]}
# The batch's hand-in (prepare's handin.py): the bench a model of its own take, the lamp sharing the bench's take, the
# shed's floor the plan's own shell.
HANDIN = {"rows": [{"id": "bench", "route": "prop", "size": [2.0, 0.6, 0.9], "count": 1},
                   {"id": "ceiling_lamp", "route": "prop", "size": [1.0, 1.0, 0.2], "count": 1},
                   {"id": "shed_floor", "route": "plan", "part": "floor"}],
          "objects": {"bench": {"rows": ["bench", "ceiling_lamp"]}}}
# The base's site at its scene time (data/physics/setting.json): the Sun stands over its horizon then.
SKY = {"site": {"on": "moon", "latitude": 55.0, "longitude": 0.0, "height_m": 0.0}, "time": "2099-10-01T14:00:00Z"}


def written(folder, design):
    """scene-record@shed written into `folder` from its design `design`: (the record's output, the writer's inputs)."""
    from score.review import setting
    from score.stages.scene_record import writer
    folder = pathlib.Path(folder)
    out, inputs = made(folder, design)
    (folder / "plans/site.json").write_text(json.dumps(SITE))
    (folder / "inventory.json").write_text(json.dumps({**INVENTORY, "rows": [*INVENTORY["rows"], LAMP_ROW]}))
    (folder / "sky.json").write_text(json.dumps({**SKY, "place": "shed", "top": "site", "setting": setting.now()}))
    (folder / "hand-in.json").write_text(json.dumps(HANDIN))
    inputs = {**inputs, "plan": out, "sky": folder / "sky.json", "hand-in": folder / "hand-in.json",
              "row kinds": REPO / "data/checks/row-kinds.json",
              "lamp library": REPO / "data/library/lamps.json", "places": REPO / "data/definitions/place.json"}
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
    Break: score/stages/scene_record/gates.py:
        `found.append(f"opening {number} ({opening.get('kind')}) at {opening['at']} is filled by {filled}")` -> `pass`
    Break: score/stages/scene_record/gates.py: `found.append(f"the light of plan item {name!r} stands off its
        footprint")`
        -> `pass`
    Break: score/stages/scene_record/gates.py:
        `found.append(f"opening {number} leads to {to!r}, no place of the design nor a row of its inventory")`
        -> `pass`"""
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
        assert yard["name"] == "yard" and yard["at"] == [16.0, 0.0, 3.0] and yard["rotation"] == [0, 0, 0, 1], yard
        assert [view["name"] for view in record["views"]] == ["from-door-1", "spot-1"], record["views"]
        assert [view["name"] for view in record["views_left_out"]] == ["spot-2"], record["views_left_out"]
        assert record["ceiling"] == 3.0, record
        for check in gates.CHECKS:
            verdict = check.judge(output, inputs, {})
            assert verdict.answer == checks.PASS, (verdict.check, verdict.reason, verdict.findings)
        path = output / "record/shed.json"
        filled = {**record, "structure": record["structure"] + [
            {"name": "plug", "builder": "slab", "points": [[-0.8, -3.5], [0.8, -3.5], [0.8, -3.0], [-0.8, -3.0]],
             "low": 0.0, "high": 3.0}]}
        path.write_text(json.dumps(filled))
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.FAIL and "filled by ['plug']" in " ".join(verdict.findings), verdict.findings
        path.write_text(json.dumps({**record, "lights": [{**lamp, "at": [3.0, 2.7, 0.0]}]}))
        verdict = gates.judge_plan_matched(output, inputs, {})
        assert verdict.answer == checks.FAIL and "'LAMP' stands off" in " ".join(verdict.findings), verdict.findings
    nowhere = json.loads(json.dumps(WRITTEN))
    nowhere["openings"][0]["to"] = "moon_city"
    with tempfile.TemporaryDirectory() as folder:
        output, inputs = written(folder, nowhere)
        verdict = gates.judge_openings(output, inputs, {})
        assert verdict.answer == checks.FAIL and "'moon_city'" in " ".join(verdict.findings), verdict.findings


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
        assert by_name["site"]["at"] == [14.0, 0.0, 5.0] and "palm_tree" in by_name["site"]["from"], by_name["site"]


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
        -> `return [along(path, 0.5) for number in range(pieces)]`"""
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


def test_each_object_carries_what_holds_it_from_the_place_s_relations(tmp_path):
    """Issue #72: the record carries each object's relation (score/review/holders) for the assembly to lay it by. On a
    20 by 20 m plan (place (x, z) is plan (x - 10, y - 10)): the door the plan writer left on the walls item stands in
    its opening at plan (5, 0), place (-5, -10), turned along its wall, `in` with its 1.4 m width and 2.2 m height;
    the garage door against its module's S face names the module's object and points out +z; the wall lamp against
    the west wall's room face, the face 0.1 m in at x -9.9, pointing out +x. Relations derived from another plan
    than the kept one are left out, with why.
    Break: score/stages/scene_record/writer.py: `spot, way, base, on = related(design, relation, spot, way, base,
        size, piece)` -> `pass`
    Break: score/stages/scene_record/writer.py: `on["holder"] = names` -> `pass`"""
    from score.stages.scene_record import writer
    design = {"w": 20.0, "d": 20.0, "items": [["ON THE WALLS AND CEILING", 0.0, 0.0, 20.0, 20.0, None, "item"],
                                              ["MODULE 1", 8.0, 2.0, 6.0, 6.0, None, "item"],
                                              ["GARAGE DOOR 1", 4.0, 9.0, 3.0, 3.0, None, "item"]],
              "rows": {"ON THE WALLS AND CEILING": ["door", "lamp"], "MODULE 1": ["module"],
                       "GARAGE DOOR 1": ["garage_door"]}}
    rows = [{"id": name, "anchor": "floor", "route": "prop", "size": size}
            for name, size in (("door", [1.2, 0.1, 2.1]), ("lamp", [0.3, 0.2, 0.3]), ("module", [6.0, 6.0, 6.0]),
                               ("garage_door", [3.0, 0.2, 3.0]))]
    relations = {"relations": [
        {"item": "ON THE WALLS AND CEILING", "row": "door", "how": "in", "why": "in the plan's door opening 1",
         "opening": {"at": [5.0, 0.0], "wide": 1.4, "sill": 0.0, "head": 2.2},
         "wall": {"from": [0.0, 0.0], "to": [20.0, 0.0], "thick": 0.2}},
        {"item": "ON THE WALLS AND CEILING", "row": "lamp", "how": "wall", "why": "against the wall nearest",
         "wall": {"from": [0.0, 20.0], "to": [0.0, 0.0], "thick": 0.2}, "side": 1, "spot": [0.0, 10.0]},
        {"item": "GARAGE DOOR 1", "row": "garage_door", "how": "face", "holder": "MODULE 1", "face": "S",
         "why": "against module's side"}]}
    found = {entry["row"]: entry for entry in writer.design_objects(design, {"rows": rows, "objects": {}}, relations)}
    door, lamp, garage = found["door"], found["lamp"], found["garage_door"]
    assert door["at"] == [-5.0, 0.0, -10.0] and door["on"]["how"] == "in", door
    assert door["on"]["middle"] == [-5.0, 0.0, -10.0] and door["on"]["wide"] == 1.4 and door["on"]["tall"] == 2.2
    assert door["rotation"] == writer.yaw_turn(design, (1.0, 0.0), rows[0]["size"]), door
    assert garage["on"]["holder"] == ["module_1"] and garage["on"]["out"] == [0.0, 1.0], garage
    assert lamp["on"]["span"] == [[-9.9, 10.0], [-9.9, -10.0]] and lamp["on"]["out"] == [1.0, 0.0], lamp
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
        (the row reads its concept light where plans.keep keeps none)"""
    from score.review import plans
    from score.stages.scene_record import concept_light, writer
    assert concept_light.KEPT_LIGHT == plans.KEPT_LIGHT
    design = {**WRITTEN, "items": [["CORE", 3.0, 2.0, 1.0, 1.0, None, "item"], ["ENGINE", 1.0, 1.0, 2.0, 1.0, None,
                                                                                  "item"],
                                   ["SKY", 0.0, 0.0, 1.0, 1.0, None, "item"]],
              "rows": {"CORE": ["core"], "ENGINE": ["engine"], "SKY": ["sky"]},
              "shapes": {"CORE": {"shape": "rect", "tall": 3.0, "base": 0.0}}}
    rows = [{"id": "core", "name": "energy core", "noun": "core", "anchor": "floor", "size": [1.0, 1.0, 3.0]},
            {"id": "engine", "name": "engine", "noun": "engine", "anchor": "floor", "size": [2.0, 1.0, 1.0]},
            {"id": "sky", "name": "starfield", "noun": "sky", "anchor": "sky"}]
    dark = {"glows": False, "glowing": "", "colour": "", "brightness": 0}
    light = {"rows": {"core": {"glows": True, "glowing": "its column", "colour": "#44aaff", "brightness": 0.5},
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
        [lamp] = writer.lights(design, {**inputs, "concept light": folder / "light.json"})
        full = writer.item_lamp(design["items"][0], {**rows[0], "row_kind": "machine"}, rows, design,
                                writer.library_lamps(), inputs["lamp library"])
    assert lamp["colour"] == "#44aaff" and "its column" in lamp["from"] and "core" in lamp["from"], lamp
    assert lamp["energy"] == round(full["energy"] / 2, 4) and lamp["at"] == full["at"]


def test_the_shell_and_stairs_take_the_scene_librarys_surfaces():
    """Each shell part and stair takes the variant the scene's surface library gives its kind (a stair the floor's
    when the library names no stair), and a part it gives none, or every part while no library is made, carries no
    surface and says why; the scene builder names that on the mesh and binds nothing.
    Break: score/stages/scene_record/writer.py: `    return dict(entry, surface=surface)` -> `    return dict(entry,
        surface="deck_plate")`
    Break: score/stages/earth_seed/design_shell.py: `return f"{place}: the scene's surface library is not made (run
        surface-library first): its {kind} has none"`
        -> `return f"{place}: no surface"`"""
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
    assert roof["surface"] is None and "names no surface for the kinds a roof takes" in roof["surface_missing"], roof
    assert all(entry["surface"] is None and "not made" in entry["surface_missing"] for entry in painted.values()), \
        painted  # no library row read: every part named missing, none painted another way
    stage = Usd.Stage.CreateInMemory()
    scene.write_structure(stage, "shed", [roof])
    mesh = stage.GetPrimAtPath("/shed/Structure/roof_1")
    assert "roof takes" in mesh.GetAttribute("score:surface:missing").Get(), mesh
    assert not mesh.HasRelationship("material:binding"), mesh
