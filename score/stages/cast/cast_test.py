"""The cast stage's make and gates on a one-person design on the hub's seed (#26: the cast reads the picked design,
data/people/rows.json): the person stands and keeps clear and the cast holds what the design shows; one dealt into a
thing is stood clear round it or left out and named; a look with no usable dress row is not made (an accepted gap,
the gate passing), one whose dress row the runner gave is; a design's crowd with no ground is named short; a crowd's
lattice keeps two body widths apart.

Run: .venv/bin/python score/stages/cast/cast_test.py   (the two tests on the hub's round-three seed skip, saying so, without it)
"""
import json
import pathlib
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score import checks  # noqa: E402
from score.stages import cast  # noqa: E402
from score.stages.cast import measure, spread  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402


def hub_inputs(folder, design):
    """The hub's inputs with its design swapped for the given one, written into `folder`."""
    inputs = {name: pathlib.Path((pattern[0] if isinstance(pattern, tuple) else pattern).format(
        place="hub", data=str(REPO / "data"), seeds=str(PROPS_HOME / "work"), repo=str(REPO)))
        for name, pattern in cast.files("hub").items()}
    inputs["design"] = folder / "rows.json"
    inputs["design"].write_text(json.dumps({"places": {"hub": design}, "new": {}}))
    return inputs


def answers(design):
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        inputs = hub_inputs(folder, design)
        out = folder / "out"
        out.mkdir()
        cast.make(inputs, out, 0, {})
        assert cast.cast_faults(out) == []
        return {check.name: check.judge(out, inputs, None) for check in cast.CHECKS}


def hub_design(at=(-0.535, -0.407, 0.9)):
    """A one-person design on the hub's seed (the hub's own design shows nobody)."""
    return {"concept": "a test", "spots": [list(at)], "middle": [-0.606, -0.407, 1.517],
            "rows": {"bram": {"name": "person at the console", "count": 1, "size": [0.5, 0.3, 1.8],
                              "where": "at the operations console", "looks": ["bram-work"]}}}


SEED = PROPS_HOME / "work/usd-r3/hub/layers/base.usda"


def without_the_seed():
    """Whether the hub's round-three seed is missing (lost with the old disk, 2026-10-19), said so: the two tests on its
    geometry skip, the rest run."""
    if not SEED.exists():
        print(f"skipped: no hub seed at {SEED}")
    return not SEED.exists()


def test_the_hub():
    if without_the_seed():
        return
    found = answers(hub_design())
    assert found["standing"].answer == checks.PASS, found["standing"].reason
    assert found["clear"].answer == checks.PASS, found["clear"].reason
    assert found["counted"].answer == checks.PASS and found["counted"].measures["cast"] == 1
    # a look with no dressed body is an accepted gap carried down, never a stop (complete's people check fails it)
    assert found["made"].answer == checks.PASS and found["made"].measures["missing"] >= 1
    assert all("no accepted dressed body" in finding for finding in found["made"].findings)


def test_a_person_dealt_into_a_thing_is_stood_clear_or_named():
    if without_the_seed():
        return
    found = answers(hub_design(at=(-0.606, -0.407, 1.517)))  # the console itself
    assert found["clear"].answer == checks.PASS, found["clear"].reason
    assert found["counted"].answer == checks.PASS or "left out" in found["counted"].reason, found["counted"]


def test_a_designs_crowd_without_ground_is_named_short():
    crowd = {"look": "kit_m_avg/coat-grey", "asked": None, "copies": []}
    assert cast.short_of({"left_out": [], "crowd": crowd}) == [
        "the crowd's ground and count are not in the design yet (kit_m_avg/coat-grey)"]


def test_a_look_is_made_by_its_usable_dress_row():
    look = cast.look_of({"character": "bram", "look": "bram_work"})
    assert look == ("bram", "work")
    assert cast.made_row(look, "hub", {"people-dress-bram-work": "accepted"}) == "people-dress-bram-work"
    assert cast.made_row(look, "hub", {}) is None
    assert cast.made_row(look, "camp", {"people-dress-bram-work": "accepted"}) is None  # the camp's is coloured
    assert cast.made_row(look, "camp", {"people-dress-bram-work-in-camp": "a"}) == "people-dress-bram-work-in-camp"
    assert cast.made_row(None, "hub", {}) is None
    assert cast.look_of({"character": "kit_m_avg", "worn": ["plain_coat_grey", "head_f1"]}) == ("kit_m_avg", "coat-grey")


def test_a_crowd_lattice_keeps_bodies_apart():
    crowd = {"spread": [0.0, 0.0, 6.0, 6.0], "seed": 3, "count": 10, "facing_to": [0.0, 0.0, -10.0],
             "turn_jitter": 0.1, "height_jitter": 0.0, "doing": ["standing"], "shares": [1.0], "phases": 1,
             "palettes": [[0, 0, 0]], "palette_shares": [1.0]}
    spots = [copy["at"] for copy in spread.lattice(crowd, [])]
    nearest = min(((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5 for number, a in enumerate(spots)
                  for b in spots[number + 1:])
    assert len(spots) > 100 and nearest >= 2 * measure.BODY_RADIUS, (len(spots), nearest)


def test_a_crowd_keeps_clear_of_each_view():
    view = {"eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, -10.0], "fov": 70}
    near, far, behind = {"at": [0.0, 0.0, -4.0]}, {"at": [0.0, 0.0, -20.0]}, {"at": [0.0, 0.0, 4.0]}
    assert spread.frame_share(view, near["at"]) > spread.FAR_SHARE > spread.frame_share(view, far["at"])
    assert spread.far_enough([near, far, behind], [view]) == [far, behind]


def plan_views_of(plan):
    """cast.plan_views of a plan row's output holding `plan`, with the environment's eye height."""
    with tempfile.TemporaryDirectory() as folder:
        (pathlib.Path(folder) / "plan.json").write_text(json.dumps(plan))
        return cast.plan_views({"plan": folder, "places": REPO / "data/definitions/place.json"})


def test_the_crowd_keeps_clear_of_its_plans_views():
    """The views a crowd keeps clear of are its plan's (the plan row's output), never a hand-written record's: a room's
    one inside its door and one from its standing spot, an outdoor plan's from its standing spot only, a place with no
    plan row none; a copy right before the door's view is dropped, one far down it kept."""
    eye = json.loads((REPO / "data/definitions/place.json").read_text())["shared"]["scale"]["eye_height"]
    room = {"inside": True, "floor": [[-5.0, -5.0], [5.0, 5.0]], "floor_height": 0.0, "items": [],
            "doors": [{"side": "south", "level": 0.0, "middle": [0.0, 0.0, 5.0], "normal": [0.0, 0.0, 1.0],
                       "name": "S", "what": "door"}],
            "standing": [{"at": [3.0, 3.0], "level": 0.0, "looks_at": None}]}
    views = plan_views_of(room)
    assert [view["name"] for view in views] == ["from-south-door", "spot-1"]
    assert views[0]["eye"] == [0.0, eye, 4.0] and views[1]["eye"] == [3.0, eye, 3.0]
    assert [view["name"] for view in plan_views_of(dict(room, inside=False))] == ["spot-1"]
    assert cast.plan_views({"places": REPO / "data/definitions/place.json"}) == []
    near, far = {"at": [0.0, 0.0, 2.0]}, {"at": [0.0, 0.0, -40.0]}
    assert spread.far_enough([near, far], views[:1]) == [far]


def test_a_group_wears_only_its_kit():
    cast_rules, _ = measure.characters()
    kit = {"builds": ["m_avg", "w_slim"], "plain": ["uniform_olive"]}
    mixes = [cast_rules.kit_mix(seed, kit) for seed in range(200)]
    assert {mix["character"] for mix in mixes} == {"kit_m_avg", "kit_w_slim"}
    assert {mix["worn"]["plain"][0] for mix in mixes} == {"plain_uniform_olive"}


def test_copied_constants_agree():
    cast_rules, cast_check = measure.characters()
    assert (measure.BODY_RADIUS, measure.KNEE, measure.HEAD) == (cast_check.BODY_RADIUS, cast_check.KNEE,
                                                                 cast_check.HEAD)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
