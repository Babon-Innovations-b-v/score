"""The cast stands every person and crowd copy on something solid, clear of every solid and of each other, or leaves
them out by name; a look with no usable dressed body is an accepted gap named down the line, never a stand-in
(cast/__init__.py, measure.py, spread.py, layer.py); a person whose place's sim body ran plays its simulated motion,
its feet on its sim body's, and one without keeps its clip, named (driven.py).

Measured on a toy place made here (a 10 m floor and a 1 m crate), small crowds and plans written here, and the
characters layer made with no dressed body at all. The hub's round-three seed and the motion work's built body the
old tests needed went with the old disk (2026-10-19): those tests only ever skipped, so their rules are held here on
geometry of the test's own.

Breaks that turn it red (each applied once and seen red, then reverted):
- `spread.grounded`: `or next(clashes)` dropped  -> the toy place test (the member stays in the crate).
- `spread.grounded`: `or not next(level)` dropped  -> the deck edge test (the member stays over the edge).
- `measure.level_under`: `np.abs(row) <= FOOT_STEP` read as `<= 1.0`  -> the deck edge test.
- `measure.level_under`: `- plane @ np.linalg.pinv(plane)` dropped (the gaps judged off the feet, not off a plane)
  -> the deck edge test (the person on the slope is left out).
- `measure.run_into`: `sorted(names) if hit else []` read as `[]`  -> the toy place test.
- `cast.overlaps`: `< measure.KNEE` read as `< 100`  -> the overlap test (bodies on two levels overlap).
- `cast.off_ground`: `> STAND_SLACK` read as `> 1.0`  -> the standing test.
- `cast.short_of`: the packed `not crowd["copies"]` branch dropped  -> the packed crowd test.
- `cast.made_row`: `row if row in inputs else None` read as `row`  -> the made test (a look with no dress row made).
- `spread.on_ground`: `not grounds or` read as `True or`  -> the grounds test (spots between the two grounds).
- `spread.far_enough`: `< FAR_SHARE` read as `<= 1.0`  -> the views test (the copy before the door kept).
- `cast.plan_views`: the `unaimed` refusal dropped  -> the unaimed-spot test.
- `cast.on_levels`: `at[1] + min(heights)` read as `at[1]`  -> the levels test.
- `cast.on_made_ground`: `ground > at[1]` read as `False`  -> the made ground rise test (the one under it found
  nothing under it).
- `layer.make`: `if row is None or row not in inputs:` read as `if row is None:`  -> the layer test (it reaches for
  a body that is not there instead of naming the gap).
- `driven.size_over_sim`: `/ float(body["size"]["of the rig"])` dropped  -> the sim body test (the 1.1 body's sim
  hips raised 10% again: feet off).
- `driven.write_driven`: Hips' simulated translation not written  -> the sim body test (the clip's path kept).
- `driven.lay_sim_body`: the Turned transform not set  -> the sim body test (the sim body mirrored off the skin).
- `driven.judge_on_its_sim_body`: `> FEET_WITHIN` read as `> 1.0`  -> the feet-leave test.
- tools/characters/cast_check.py `repeated_people`: `len(names) > 1` read as `> 9`  -> the variants test.
"""
import json
import pathlib
import sys

import numpy as np
import pytest
from pxr import Usd, UsdGeom

from score import checks
from score.stages import cast
from score.stages.cast import driven, layer, measure, spread
from score.stages.scene_record import writer

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACES = REPO / "data/definitions/place.json"


def mesh(stage, path, corners, faces):
    shape = UsdGeom.Mesh.Define(stage, path)
    shape.CreatePointsAttr(corners)
    shape.CreateFaceVertexCountsAttr([len(face) for face in faces])
    shape.CreateFaceVertexIndicesAttr([index for face in faces for index in face])


def toy_place(folder):
    """base.usda of place `camp`: a 10 m floor from -5 to 5 at height 0 and a 1 m crate from 0 to 1 on it."""
    stage = Usd.Stage.CreateNew(str(folder / "base.usda"))
    UsdGeom.Xform.Define(stage, "/camp")
    mesh(stage, "/camp/Ground/floor", [(-5, 0, -5), (5, 0, -5), (5, 0, 5), (-5, 0, 5)], [(0, 1, 2, 3)])
    corners = [(x, y, z) for x in (0, 1) for y in (0, 1) for z in (0, 1)]
    mesh(stage, "/camp/Objects/crate", corners,
         [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    stage.Save()
    return measure.solids(folder / "base.usda", "camp")


def off_the_crate(spot):
    """How far a spot stands from the crate's footprint, sideways, metres."""
    dx = max(0.0 - spot[0], 0.0, spot[0] - 1.0)
    dz = max(0.0 - spot[2], 0.0, spot[2] - 1.0)
    return (dx * dx + dz * dz) ** 0.5


def test_a_person_dealt_into_a_thing_is_stood_clear_round_it_or_left_out(tmp_path):
    found = toy_place(tmp_path)
    assert set(found) == {"Ground/floor", "Objects/crate"}
    assert measure.run_into([[0.5, 0.0, 0.5], [3.0, 0.0, 3.0]], found) == [["Objects/crate"], []]
    assert measure.ground_under([[3.0, 0.0, 3.0]], found)[0] == {"gap": 0.0, "on": "Ground/floor", "water": False}
    inside = {"name": "worker_1", "at": [0.5, 0.0, 0.5], "doing": "standing"}
    lost = {"name": "worker_2", "at": [20.0, 0.0, 20.0], "doing": "standing"}  # off the floor, 15 m from it
    placed, copies = spread.stand_every([inside, lost], {"worker_1", "worker_2"},
                                        [{"at": [0.5, 0.0, 0.5]}, {"at": [3.0, 0.0, 3.0]}], 2, found)
    assert [person["name"] for person in placed] == ["worker_1"], placed
    spot = placed[0]["at"]
    # the body's 16-sided cylinder is BODY_RADIUS to its corners, BODY_RADIUS cos(pi/16) to its flat sides
    assert spot[1] == 0.0 and off_the_crate(spot) >= 0.245, spot
    assert [copy["at"] for copy in copies] == [[3.0, 0.0, 3.0]]  # the crowd copy on the crate is not stood


def test_a_base_with_no_solid_stands_nobody_and_runs_into_nothing():
    """An earth seed whose plan lays no shell: every body stands on nothing, for the standing gate to name, instead
    of failing the make."""
    spots = [[0.0, 0.0, 0.0], [1.0, 0.0, 1.0]]
    assert measure.ground_under(spots, {}) == [{"gap": None, "on": None, "water": False}] * 2
    assert measure.run_into(spots, {}) == [[], []]


def test_a_body_stands_on_the_places_made_ground(tmp_path):
    """The terrain row's made ground (places/<place>.usdc) is measured with a base that has no solid of its own."""
    base = Usd.Stage.CreateNew(str(tmp_path / "base.usda"))
    UsdGeom.Xform.Define(base, "/camp")
    base.Save()
    ground = Usd.Stage.CreateNew(str(tmp_path / "world/places/camp.usdc"))
    mesh(ground, "/camp/Ground/patch", [(-5, 0, -5), (5, 0, -5), (5, 0, 5), (-5, 0, 5)], [(0, 1, 2, 3)])
    ground.Save()
    made = cast.made_ground({"terrain": str(tmp_path)}, "camp")
    assert made == tmp_path / "world/places/camp.usdc" and cast.made_ground({}, "camp") is None
    assert measure.solids(tmp_path / "base.usda", "camp") == {}
    found = measure.solids(tmp_path / "base.usda", "camp", made)
    assert [stood["on"] for stood in measure.ground_under([[0.0, 0.0, 0.0]], found)] == ["Ground/patch"]


def test_a_person_under_a_rise_of_the_made_ground_stands_on_it(tmp_path):
    """Wreck's astronaut_3 (round 33, 2026-10-30): its plan spot at 0 lay under a 3.9 m rise of the made ground, the
    knee's ray down found nothing and it was left out. Raised onto the ground it stands; one over a hollow stays."""
    base = Usd.Stage.CreateNew(str(tmp_path / "base.usda"))
    UsdGeom.Xform.Define(base, "/camp")
    base.Save()
    ground = Usd.Stage.CreateNew(str(tmp_path / "world/places/camp.usdc"))
    mesh(ground, "/camp/Ground/rise", [(-5, 2, -5), (0, 2, -5), (0, 2, 5), (-5, 2, 5)], [(0, 1, 2, 3)])
    mesh(ground, "/camp/Ground/hollow", [(0, -1, -5), (5, -1, -5), (5, -1, 5), (0, -1, 5)], [(0, 1, 2, 3)])
    ground.Save()
    inputs = {"terrain": str(tmp_path)}
    found = measure.solids(tmp_path / "base.usda", "camp", cast.made_ground(inputs, "camp"))
    record = {"people": [{"name": "up", "at": [-2.0, 0.0, 0.0]}, {"name": "down", "at": [2.0, 0.0, 0.0]}]}
    assert spread.grounded([person["at"] for person in record["people"]], found)[0] is None
    raised = cast.on_made_ground(record, writer.ground_under(inputs, "camp"))["people"]
    assert [person["at"] for person in raised] == [[-2.0, 2.0, 0.0], [2.0, 0.0, 0.0]]
    assert spread.grounded([person["at"] for person in raised], found) == [[-2.0, 2.0, 0.0], [2.0, -1.0, 0.0]]
    assert cast.on_made_ground(record, None) == record


def test_a_person_by_a_decks_edge_is_stood_where_the_ground_under_both_feet_is_level(tmp_path):
    """Camp's astronaut_1 and astronaut_2_1 (round 33, 2026-10-30) stood within 0.15 m of a 5.8 cm deck's edge, their
    middles on one level and a foot over the other, and sank into it in sim-body. Nudged, each stands BODY_RADIUS
    clear of the edge; one in the deck's middle stays, and so does one on an even slope (wreck's made ground)."""
    stage = Usd.Stage.CreateNew(str(tmp_path / "base.usda"))
    UsdGeom.Xform.Define(stage, "/camp")
    mesh(stage, "/camp/Ground/floor", [(-5, 0, -5), (5, 0, -5), (5, 0, 5), (-5, 0, 5)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Shell/deck", [(0, 0.058, -5), (5, 0.058, -5), (5, 0.058, 5), (0, 0.058, 5)], [(0, 1, 2, 3)])
    mesh(stage, "/camp/Ground/slope", [(-5, 0, 6), (5, 0, 6), (5, 2.4, 10), (-5, 2.4, 10)], [(0, 1, 2, 3)])
    stage.Save()
    found = measure.solids(tmp_path / "base.usda", "camp")
    assert measure.level_under([[0.1, 0.058, 0.0], [-0.1, 0.0, 0.0], [2.0, 0.058, 0.0], [0.0, 1.8, 9.0]], found) == [
        False, False, True, True]
    members = [{"name": "edge", "at": [0.1, 0.0, 0.0]}, {"name": "middle", "at": [2.0, 0.0, 1.0]}]
    placed = spread.nudged(members, found, spread.Kept())
    edge, middle = (person["at"] for person in placed)
    assert abs(edge[0]) >= measure.BODY_RADIUS and edge[1] == (0.058 if edge[0] > 0 else 0.0), edge
    assert middle == [2.0, 0.058, 1.0]


def test_standing_bodies_nearer_than_two_widths_on_one_level_overlap():
    singles = [dict(person, doing="standing") for person in (
        {"name": "a", "at": [0.0, 0.0, 0.0]}, {"name": "b", "at": [0.3, 0.0, 0.0]},
        {"name": "c", "at": [3.0, 0.0, 0.0]}, {"name": "d", "at": [3.1, 3.0, 0.0]})]  # d a landing over c
    assert cast.overlaps(singles, None) == [["a", "b"]]


def test_feet_stand_within_the_slack_and_never_in_water():
    assert cast.off_ground({"gap": 0.03, "on": "Ground/floor", "water": False}) is None
    assert "+0.10 m off" in cast.off_ground({"gap": 0.1, "on": "Ground/floor", "water": False})
    assert cast.off_ground({"gap": 0.0, "on": "Ground/floor", "water": True}) == "standing in the water"
    assert "nothing solid" in cast.off_ground({"gap": None, "on": None, "water": False})


def test_a_designs_crowd_without_ground_is_named_short():
    unread = {"look": "kit_m_avg/coat-grey", "asked": None, "grounds": None, "copies": []}
    assert "not read from the plan yet" in cast.short_of({"left_out": [], "crowd": unread})[0]
    assert cast.short_of({"left_out": [], "crowd": dict(unread, grounds=[])}) == [
        "the crowd's row makes no item on the plan, so it has no ground (kit_m_avg/coat-grey)"]


def test_a_crowd_asks_its_count_else_its_ground_packed_and_is_short_only_when_none_fit():
    """SAM 3 counted: that many; one mass it could not part: every lattice spot of its ground, then the copies that
    fit (a lattice spot on a stall is no copy short; none fitting is); no ground: nothing."""
    assert cast.asked_of({"count": 40, "spread": [0, 0, 5, 5]}, [{}] * 90) == 40
    assert cast.asked_of({"count": None, "spread": [0, 0, 5, 5]}, [{}] * 90) == 90
    assert cast.asked_of({"count": 3, "spread": None}, []) is None
    packed = {"look": "crowd/made", "asked": 90, "packed": True, "grounds": [[0, 0, 5, 5]], "copies": [{}] * 90}
    stood = cast.stood_crowd(packed, [{}] * 70)
    assert (stood["asked"], stood["spots"], len(stood["copies"])) == (70, 90, 70)
    assert cast.short_of({"left_out": [], "crowd": stood}) == []
    assert cast.short_of({"left_out": [], "crowd": cast.stood_crowd(packed, [])}) == [
        "none of the crowd's 90 spots on its ground fit (crowd/made)"]
    counted = cast.stood_crowd(dict(packed, asked=40, packed=False), [{}] * 30)
    assert cast.short_of({"left_out": [], "crowd": counted}) == ["30 of the crowd's 40 fit"]


CROWD = {"seed": 3, "count": None, "facing_to": [0.0, 0.0, -10.0], "turn_jitter": 0.1, "height_jitter": 0.0,
         "doing": ["standing"], "shares": [1.0], "phases": 1, "palettes": [0], "palette_shares": [1.0]}


def test_a_crowd_lattice_stands_only_on_its_grounds_and_keeps_bodies_apart():
    """Two grounds 2 m wide, 6 m apart: no spot between them; on an open 6 m square no two closer than two widths."""
    grounds = dict(CROWD, spread=[0.0, 0.0, 10.0, 4.0], grounds=[[0.0, 0.0, 2.0, 4.0], [8.0, 0.0, 2.0, 4.0]])
    spots = [copy["at"] for copy in spread.lattice(grounds, [])]
    assert all(spot[0] <= 2.0 or spot[0] >= 8.0 for spot in spots), spots
    assert any(spot[0] <= 2.0 for spot in spots) and any(spot[0] >= 8.0 for spot in spots)
    spots = [copy["at"] for copy in spread.lattice(dict(CROWD, spread=[0.0, 0.0, 6.0, 6.0]), [])]
    nearest = min(((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 for number, a in enumerate(spots)
                  for b in spots[number + 1:])
    assert len(spots) > 100 and nearest >= 2 * measure.BODY_RADIUS, (len(spots), nearest)


def plan_views_of(tmp_path, plan):
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    return cast.plan_views({"plan": tmp_path, "places": PLACES})


ROOM = {"inside": True, "floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [],
        "doorways": [{"name": "door-1", "middle": [0.0, 0.0, 5.0], "inward": [0.0, 0.0, -1.0], "wide": 1.0,
                      "sill": 0.0, "head": 2.1, "to": None}],
        "standing": [{"at": [3.0, 3.0], "level": 0.0, "looks_at": None}]}


def test_a_crowd_keeps_clear_of_its_plans_views(tmp_path):
    """The views are its plan's (the plan row's output), never a hand-written record's: a room's one inside its door
    and one from its standing spot, an outdoor plan's from its standing spot only, no plan row none; a copy right
    before a view is dropped, one far down it or behind it kept."""
    eye = json.loads(PLACES.read_text())["shared"]["scale"]["eye_height"]
    views = plan_views_of(tmp_path, ROOM)
    assert [(view["name"], view["eye"]) for view in views] == [("from-door-1", [0.0, eye, 4.0]),
                                                              ("spot-1", [3.0, eye, 3.0])]
    assert [view["name"] for view in plan_views_of(tmp_path, dict(ROOM, inside=False))] == ["spot-1"]
    assert cast.plan_views({"places": PLACES}) == []
    view = {"eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, -10.0], "fov": 70}
    near, far, behind = {"at": [0.0, 0.0, -4.0]}, {"at": [0.0, 0.0, -20.0]}, {"at": [0.0, 0.0, 4.0]}
    assert spread.far_enough([near, far, behind], [view]) == [far, behind]


def test_a_plan_spot_aimed_off_its_items_stops_only_a_crowd_with_ground(tmp_path):
    """The camp's accepted plan (2026-10-21) has spots looking at its kit's objects, no plan items: refused by name,
    never a bare StopIteration; a cast with no crowd, or a crowd with no ground, never reads them."""
    plan = {"place": "camp", "inside": True, "floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [],
            "doors": [], "standing": [{"at": [1.0, 4.0], "level": 0.0, "looks_at": "SEFA'S BUNK"}]}
    with pytest.raises(ValueError, match="SEFA'S BUNK"):
        plan_views_of(tmp_path, plan)
    inputs = {"plan": tmp_path, "places": PLACES}
    crowd = {"name": "crowd", "character": "kit_m_avg", "look": "kit_m_avg_far", "doing": ["idle"], "count": None}
    assert cast.crowd_of({"people": []}, [], inputs) is None
    assert cast.crowd_of({"people": [], "crowd": crowd}, [], inputs)["copies"] == []


def test_a_spot_on_a_raised_level_stands_at_its_height():
    """The stairwell's walkway people on its 3 m landing (Batch 1, 2026-10-25); one outside every level stays down."""
    plan = {"w": 4.0, "d": 4.0, "frame": {"anchor": {"plan": [0.0, 0.0], "place": [10.0, 0.0, -5.0]}},
            "levels": [{"height": 3.0, "points": [[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]]}]}
    record = {"people": [{"name": "up", "at": [11.0, 0.0, -4.0]}, {"name": "down", "at": [13.0, 0.0, -2.0]}]}
    assert [person["at"] for person in cast.on_levels(record, plan)["people"]] == [[11.0, 3.0, -4.0],
                                                                                  [13.0, 0.0, -2.0]]


def test_a_look_is_made_only_by_its_own_usable_dress_row():
    """The plain dress row, `-in-<surface>` for a row's own fabric, `-v<n>` for a person's own variant; none other."""
    look = cast.look_of({"character": "bram", "look": "bram_work"})
    assert look == ("bram", "work")
    assert cast.made_row(look, None, 0, {"people-dress-bram-work": "accepted"}) == "people-dress-bram-work"
    assert cast.made_row(look, None, 0, {}) is None
    assert cast.made_row(look, "jacket_blue", 0, {"people-dress-bram-work": "accepted"}) is None
    assert cast.made_row(look, "jacket_blue", 0, {"people-dress-bram-work-in-jacket_blue": "a"}) == \
        "people-dress-bram-work-in-jacket_blue"
    assert cast.made_row(look, "jacket_blue", 2, {"people-dress-bram-work-in-jacket_blue": "a"}) is None
    assert cast.made_row(look, "jacket_blue", 2, {"people-dress-bram-work-in-jacket_blue-v2": "a"}) == \
        "people-dress-bram-work-in-jacket_blue-v2"
    assert layer.dressed_of("people-dress-bram-work-in-jacket_blue-v2") == ("bram-work", "jacket_blue", 2)
    assert layer.dressed_of("people-dress-astronaut-made") == ("astronaut-made", None, 0)
    assert cast.made_row(None, None, 0, {}) is None
    worn = {"character": "kit_m_avg", "worn": ["plain_coat_grey", "head_f1"]}
    assert cast.look_of(worn) == ("kit_m_avg", "coat-grey")
    assert layer.body_row("bram/work", "jacket_blue") == "people-dress-bram-work-in-jacket_blue"
    assert layer.body_row(None, "jacket_blue") is None


def test_a_person_with_no_dressed_body_is_left_out_and_named_never_laid_in_a_stand_in(tmp_path):
    """The characters layer with no dress row given: nobody laid, each named, the gate passing with the gaps as
    findings, and complete's people check (tools/usd/contents.py) failing each by name."""
    (tmp_path / "cast").mkdir()
    bram = {"name": "bram", "character": "bram", "look": "bram/work", "at": [1.0, 0.0, 2.0], "turn": 90.0,
            "doing": "standing", "start": 0.0}
    (tmp_path / "cast/cast.json").write_text(json.dumps({"place": "hub", "characters": [bram, dict(bram, name="nev")],
                                                         "crowd": None}))
    (tmp_path / "rows.json").write_text(json.dumps({"places": {"hub": {"concept": "a test", "rows": {}}}, "new": {}}))
    inputs = {"cast": tmp_path / "cast", "design": tmp_path / "rows.json"}
    out = tmp_path / "out"
    out.mkdir()
    layer.make(inputs, out, 0, {})
    assert layer.layer_faults(out) == []
    stage = Usd.Stage.Open(str(out / layer.LAYER))
    assert not stage.GetPrimAtPath("/hub/Characters").GetChildren()
    verdict = layer.judge_laid(out, inputs, None)
    assert verdict.answer == checks.PASS and verdict.measures["missing"] == 2, verdict
    assert verdict.findings[0] == "bram (bram/work): no accepted body of its look (people-dress-bram-work)"
    sys.path.insert(0, str(REPO / "tools/usd"))
    import contents
    assert [fault for fault in contents.layer_faults(out) if fault.startswith("nev (bram/work)")]


def test_a_crowd_variant_with_no_body_is_named_and_never_worn_by_another():
    crowd = {"name": "crowd", "look": "crowd/made", "copies": [{"palette": 0}, {"palette": 1}]}
    looks = layer.laid_crowd(None, "/square/Characters", crowd, {"palettes": [0, 1]}, {}, None, {})
    assert looks["crowd-v0"]["missing"] == "no accepted body of its look (people-dress-crowd-made)"
    assert looks["crowd-v1"]["missing"] == "no accepted body of its look (people-dress-crowd-made-v1)"
    assert looks["crowd"]["missing"] == "no variant of its look has an accepted body"
    unstood = layer.laid_crowd(None, "/square/Characters", dict(crowd, copies=[]), {"palettes": [0]}, {}, None, {})
    assert "no copy of the crowd stood" in unstood["crowd"]["missing"]


def test_the_cast_check_judges_each_person_where_they_were_stood_and_one_variant_twice_is_one_person_twice():
    """A person dealt a spot on another's walk is judged where they were stood (cast_check, 9cc854cf); each person of
    a look its own variant (owner, 2026-10-25: "Each one looks different"), the same variant twice the same person."""
    walker = {"name": "walker", "character": "bram", "doing": "walking", "at": [0.0, 0.0, 0.0],
              "facing_to": [4.0, 0.0, 0.0], "path": [[0.0, 0.0, 0.0], [4.0, 0.0, 0.0]]}
    standing = {"name": "worker", "character": "worker", "doing": "standing", "at": [2.0, 0.0, 0.0],
                "facing_to": [0.0, 0.0, 9.0]}
    assert cast.checked_cast({"people": [walker, standing]}, []) != []
    assert cast.checked_cast({"people": [walker, standing]}, [{"name": "worker", "at": [2.0, 0.0, 5.0]}]) == []
    copy = {"character": "worker", "look": "worker_made", "doing": "standing", "facing_to": [0.0, 0.0, 9.0]}
    record = {"people": [dict(copy, name="worker_1", at=[0.0, 0.0, 0.0], variant=0),
                         dict(copy, name="worker_2", at=[3.0, 0.0, 0.0], variant=1)]}
    assert cast.checked_cast(record, []) == []
    same = {"people": [dict(person, variant=0) for person in record["people"]]}
    assert cast.checked_cast(same, []) == ["worker_1 and worker_2 are the same person (worker)"]


def test_a_group_wears_only_its_kit_and_the_copied_body_sizes_agree():
    """measure.py copies cast_check's body sizes so tools/characters stays off the import path (the overlay's rule)."""
    cast_rules, cast_check = measure.characters()
    kit = {"builds": ["m_avg", "w_slim"], "plain": ["uniform_olive"]}
    mixes = [cast_rules.kit_mix(seed, kit) for seed in range(200)]
    assert {mix["character"] for mix in mixes} == {"kit_m_avg", "kit_w_slim"}
    assert {mix["worn"]["plain"][0] for mix in mixes} == {"plain_uniform_olive"}
    assert (measure.BODY_RADIUS, measure.KNEE, measure.HEAD) == (cast_check.BODY_RADIUS, cast_check.KNEE,
                                                                 cast_check.HEAD)


# --- a person driven by its sim body (driven.py) -------------------------------------------------------------------

TOY_JOINTS = ("Root", "Root/Hips", "Root/Hips/LeftLeg", "Root/Hips/LeftLeg/LeftFoot", "Root/Hips/RightLeg",
              "Root/Hips/RightLeg/RightFoot", "Root/Hips/HeadEnd")
TOY_PARENTS = np.array([-1, 0, 1, 2, 1, 4, 1])
TOY_PLACES = ((0, 0, 0), (0, 1.0, 0), (0.1, 0.9, 0), (0.1, 0.05, 0), (-0.1, 0.9, 0), (-0.1, 0.05, 0), (0, 1.7, 0))
TOY_SIZE, TOY_LIFT, TOY_FRAMES = 1.1, -0.005, 10


def moved(x=0.0, y=0.0, z=0.0, turn=0.0):
    """A 4 x 4 turned `turn` degrees about z and moved by (x, y, z)."""
    from scipy.spatial.transform import Rotation
    found = np.eye(4)
    found[:3, :3], found[:3, 3] = Rotation.from_euler("z", turn, degrees=True).as_matrix(), (x, y, z)
    return found


def chained(locals_):
    worlds = []
    for joint, local in enumerate(locals_):
        worlds.append(local if TOY_PARENTS[joint] < 0 else worlds[TOY_PARENTS[joint]] @ local)
    return worlds


def toy_rig():
    """The mean rig: TOY_JOINTS at TOY_PLACES, its standing clip TOY_FRAMES frames of the bind pose."""
    bind = np.array([moved(*place) for place in TOY_PLACES])
    rest = [bind[0]] + [np.linalg.inv(bind[TOY_PARENTS[joint]]) @ bind[joint] for joint in range(1, len(bind))]
    return {"names": np.array([path.rpartition("/")[2] for path in TOY_JOINTS]), "parents": TOY_PARENTS,
            "bind": bind, "clip_standing": np.repeat(np.array(rest)[None], TOY_FRAMES, axis=0)}


def toy_asset(folder, rig):
    """A dressed body as skel_usd writes one, TOY_SIZE times the rig, turned about up as the people's bodies are, its
    standing clip two frames longer than the sim's, its Hips lifted TOY_LIFT."""
    from pxr import Gf, Sdf, UsdSkel, Vt
    folder.mkdir(parents=True)
    path = folder / "toy.usdc"
    stage = Usd.Stage.CreateNew(str(path))
    stage.SetTimeCodesPerSecond(30)
    root = UsdSkel.Root.Define(stage, "/Character")
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.Xform.Define(stage, "/Character/Turned").AddTransformOp().Set(Gf.Matrix4d().SetRotate(
        Gf.Rotation(Gf.Vec3d(0, 1, 0), 180)))
    UsdGeom.Scope.Define(stage, "/Character/Turned/Body")
    skeleton = UsdSkel.Skeleton.Define(stage, "/Character/Turned/Skeleton")
    skeleton.CreateJointsAttr(Vt.TokenArray(TOY_JOINTS))
    bind = [Gf.Matrix4d(moved(*(np.array(place) * TOY_SIZE)).T.tolist()) for place in TOY_PLACES]
    skeleton.CreateBindTransformsAttr(Vt.Matrix4dArray(bind))
    skeleton.CreateRestTransformsAttr(Vt.Matrix4dArray(bind))
    clip = UsdSkel.Animation.Define(stage, "/Character/Animations/standing")
    clip.CreateJointsAttr(Vt.TokenArray(TOY_JOINTS))
    clip.CreateScalesAttr(Vt.Vec3hArray([Gf.Vec3h(1, 1, 1)] * len(TOY_JOINTS)))
    local = rig["clip_standing"][0]
    places = [local[joint, :3, 3] * (1 if joint else 0) * TOY_SIZE for joint in range(len(TOY_JOINTS))]
    places[1] = places[1] + (0, TOY_LIFT, 0)
    for frame in range(TOY_FRAMES + 2):
        clip.CreateRotationsAttr().Set(Vt.QuatfArray([Gf.Quatf(1, 0, 0, 0)] * len(TOY_JOINTS)), frame)
        clip.CreateTranslationsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(*map(float, place)) for place in places]), frame)
    root.GetPrim().SetCustomDataByKey("score:clip_seconds", {"standing": (TOY_FRAMES + 1) / 30})
    UsdSkel.BindingAPI.Apply(skeleton.GetPrim()).CreateAnimationSourceRel().SetTargets(
        [Sdf.Path("/Character/Animations/standing")])
    stage.GetRootLayer().Save()
    return path


def toy_sim(folder, rig):
    """A sim-body output for bram, built at his own size (TOY_SIZE times the rig, as sim_body.person_rig builds it):
    its hips walked 0.3 m along x and let down 2 cm, its left leg swung 20 degrees, each segment's pose a frame
    (measures/bram.json) and keyed on its guide prim (layers/sim_bodies.usda)."""
    from pxr import Gf, Sdf
    from scipy.spatial.transform import Rotation
    segments = ["Hips", "LeftLeg", "LeftFoot", "RightLeg", "RightFoot"]
    frames = []
    for frame in range(TOY_FRAMES):
        local = [np.array(matrix) for matrix in rig["clip_standing"][frame]]
        for matrix in local:
            matrix[:3, 3] *= TOY_SIZE
        local[1] = moved(0.3 * frame / TOY_FRAMES, -0.02) @ local[1]
        local[2] = local[2] @ moved(turn=20.0)
        worlds = dict(zip([path.rpartition("/")[2] for path in TOY_JOINTS], chained(local)))
        frames.append({"poses": [[*worlds[name][:3, 3], *Rotation.from_matrix(worlds[name][:3, :3]).as_quat()]
                                 for name in segments], "worlds": worlds})
    (folder / "measures").mkdir(parents=True)
    (folder / "measures/bram.json").write_text(json.dumps([{"poses": frame["poses"]} for frame in frames]))
    (folder / "sim_bodies.json").write_text(json.dumps({"bodies": {"bram": {
        "segments": {name: 1.0 for name in segments}, "size": {"of the rig": TOY_SIZE}}}}))
    (folder / "layers").mkdir()
    stage = Usd.Stage.CreateNew(str(folder / "layers/sim_bodies.usda"))
    for name in segments:
        op = UsdGeom.Xform.Define(stage, f"/hub/Characters/bram/SimBody/{name}").AddTransformOp()
        for frame, entry in enumerate(frames):
            op.Set(Gf.Matrix4d(entry["worlds"][name].T.tolist()), frame)
    stage.GetRootLayer().Save()
    return Sdf


def laid_driven(tmp_path, people):
    """The characters layer's people laid and driven as driven.make does, on the toy body, rig and sim body."""
    from pxr import Sdf
    rig = toy_rig()
    out = tmp_path / "out"
    asset = toy_asset(out / layer.ASSETS, rig)
    np.savez(tmp_path / "rig.npz", **rig)
    toy_sim(tmp_path / "sim", rig)
    inputs = {driven.SIM_ROW: tmp_path / "sim", driven.CLIPS_ROW: tmp_path}
    (out / "layers").mkdir()
    stage = Usd.Stage.Open(Sdf.Layer.CreateNew(str(out / layer.LAYER)))
    sim = driven.sim_of(inputs, out)
    looks = {}
    for single in people:
        layer.lay_person(stage, "/hub/Characters", single, asset)
        looks[single["name"]] = {"look": single["look"]}
    driven.drive_people(stage, out / layer.LAYER, "hub", people, looks, sim)
    stage.GetRootLayer().Save()
    (out / layer.RECORD).write_text(json.dumps({"place": "hub", "looks": looks}))
    return out, Usd.Stage.Open(str(out / layer.LAYER))


TOY_PERSON = {"name": "bram", "character": "bram", "look": "bram/work", "at": [1.0, 0.0, 2.0], "turn": 90.0,
              "doing": "standing", "start": 0.2}


def test_a_person_moves_by_its_sim_body_its_feet_on_its_sim_bodys_and_one_without_keeps_its_clip(tmp_path):
    """Bram's sim body walked his hips 0.3 m and swung his left leg: his skeleton plays it (his feet within FEET_WITHIN
    of the sim body's, which stands beside him in his skeleton's frame, both from his clip's start), the joints with
    no segment and the frames after the sim's keep the clip's; nev has no sim body and keeps his clip, named."""
    out, stage = laid_driven(tmp_path, [TOY_PERSON, dict(TOY_PERSON, name="nev", character="nev")])
    record = json.loads((out / layer.RECORD).read_text())["looks"]
    assert record["bram"]["motion"]["by"] == "its sim body"
    assert sorted(record["bram"]["motion"]["clip keeps"]) == ["HeadEnd", "Root"]
    assert record["nev"]["motion"] == {"by": "its clip", "why": "its sim body was not run (sim_bodies.json's "
                                                                "`left out` says why)"}
    assert stage.GetPrimAtPath("/hub/Characters/nev").GetCustomDataByKey("score:motion").startswith("its clip")
    off = driven.feet_off(out / layer.LAYER, "hub", "bram", record["bram"]["motion"])
    # the sim body is bram's own size (1.1 times the rig): his feet stand on its (3.9 cm off at the rig's size)
    assert off == pytest.approx(0.0, abs=0.002)
    from pxr import UsdSkel
    played = UsdSkel.Animation(stage.GetPrimAtPath("/hub/Characters/bram/SimDriven"))
    start = record["bram"]["motion"]["start"]
    assert played.GetTranslationsAttr().Get(TOY_FRAMES - 1 - start)[1][0] == pytest.approx(0.27, abs=1e-4)
    assert played.GetTranslationsAttr().Get(TOY_FRAMES + 1 - start)[1][0] == pytest.approx(0.0)  # the clip's again
    verdict = driven.judge_on_its_sim_body(out, {}, None)
    assert verdict.answer == checks.PASS and verdict.measures["driven"] == 1, verdict
    assert verdict.findings == ("nev keeps its clip: its sim body was not run (sim_bodies.json's `left out` says why)",)


def test_a_person_whose_feet_leave_its_sim_bodys_fails(tmp_path):
    """A skeleton that kept its clip's hips while its sim body walked off fails `on its sim body` by name."""
    out, stage = laid_driven(tmp_path, [TOY_PERSON])
    stage.GetPrimAtPath("/hub/Characters/bram/Turned/Skeleton").GetRelationship("skel:animationSource").SetTargets(
        ["/hub/Characters/bram/Animations/standing"])
    stage.GetRootLayer().Save()
    verdict = driven.judge_on_its_sim_body(out, {}, None)
    assert verdict.answer == checks.FAIL and verdict.measures["worst foot m"] > 0.3, verdict
    assert verdict.findings[0].startswith("bram: a foot"), verdict
