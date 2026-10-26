"""scene.py's invariants: nothing is rented for a plan without its scene's approved inventory (#121), a scene whose
concept is not locked, an object with no cut-out, a target whose words come from the plan, or a target plan that also
asks for other steps; a plan's steps run in their order (target alone; else cut-out, depth, redraw), the target and
the redraws worded in the place's style (the environment's line, then the locked concept's look); a plan view's
picture goes up and its folder is mapped into the room; the batch list is the redraw report's objects at a single
seed; every step runs with the machine's own home and its local models; the cluster job runs the same steps in the
same order on the room's copy and brings the room back.

Break that turns it red: in `check` drop the `place.unread` call (an unlocked scene runs) or the `none:` refusal; in
`steps` put the depth step before the cut-out; or in `place_of` skip `approved_inventory` and read the file's place.
"""
import json
import pathlib
import shlex
import sys
import tempfile

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scene  # noqa: E402
from paths import HOME, WORK  # noqa: E402  (the run's sandbox home, conftest.py)

_SANDBOX = HOME
ROOM = WORK / "scene" / "lab"
LOCK = "d" * 64
LOOK = "worn white composite panels"
# The lab's scene's design in the sandbox's store: its locked concept and that concept's look, read once before.
_PICKS = _SANDBOX / "store" / "objects" / "concepts" / "labscene" / "picks"
_PICKS.mkdir(parents=True)
(_PICKS / "0001.json").write_text(json.dumps({"place": "labscene", "sha": LOCK, "by": "owner", "at": "2026-10-21",
                                              "environment": None}))
# The sandbox's design/ is the real home's, linked read-only: the look goes in a folder of the test's own.
scene.place.LOOKS = pathlib.Path(tempfile.mkdtemp()) / "looks"
(scene.place.LOOKS / "labscene").mkdir(parents=True)
(scene.place.LOOKS / "labscene" / f"{LOCK}.json").write_text(json.dumps(
    {"scene": "labscene", "concept": LOCK, "look": LOOK, "model": "m", "euros": 0.03, "at": "2026-10-21"}))
INVENTORY = _SANDBOX / "lab.json"
INVENTORY.write_text(json.dumps({
    "scene": "lab", "place": "labscene", "plan": {"world": "w1", "seed": 7, "views": [{"id": "v1"}]},
    "approved": "2026-10-05", "migrated": "",
    "room": {"shell": "", "light": "place", "backdrop": "", "wall_fill": []},
    "rows": [{"id": "r1", "view": "v1", "box": [0, 0, 300, 300], "name": "bench", "kind": "generate",
              "anchor": "floor", "size": [1.6, 0.7, 0.9], "count": 1, "thing": "prop:bench"}]}))


def planned(**keys):
    """A plan for the lab, built from its approved inventory."""
    return {"room": "lab", "inventory": str(INVENTORY), **keys}


def inventory_like(name, **changes):
    path = _SANDBOX / f"{name}.json"
    path.write_text(json.dumps(dict(json.loads(INVENTORY.read_text()), **changes)))
    return str(path)


@pytest.mark.parametrize("plan, why", [
    ({"room": "lab", "names": ["bench"]}, "approved inventory"),
    (planned(inventory=str(_SANDBOX / "nowhere.json"), names=["bench"]), "no inventory"),
    (planned(inventory=inventory_like("workshop", scene="workshop", approved=""), names=["bench"]), "not approved"),
    (planned(inventory=inventory_like("shed", scene="shed", place="shed"), names=["bench"]), "no locked concept"),
    (planned(objects=["none:lamp:a globe lamp"]), "no box, no row"),
    (planned(target={"sentence": "a lab"}), "its design"),
    (planned(target={"takes": 2}, names=["bench"]), "pick one"),
])
def test_a_plan_that_may_not_run_is_refused_before_anything_is_rented(plan, why):
    with pytest.raises(SystemExit, match=why):
        scene.steps(plan)


def test_a_target_plan_draws_takes_alone_in_the_places_words():
    plan = planned(target={"refs": ["/refs/one.png"], "takes": 2})
    [(step, arguments)] = scene.steps(plan)
    assert step == "target"
    assert arguments == ["tools/props/scene/target.py", "--list", "/root/props/inputs/targets.json",
                         "--takes", "2", "--refs-on", "2"]
    [job] = scene.target_jobs(plan)
    assert job["refs"] == ["/root/props/inputs/1-one.png"] and job["scene"] == "lab"
    assert job["sentence"].endswith(f". {LOOK}")
    assert job["sentence"].startswith(scene.place.environment_style(scene.place.design()[2].default()).rstrip("."))


def test_the_steps_run_in_order_in_the_places_style():
    plan = planned(names=["bench", "desk@0.4"], depth=True, objects=["bench-1:bench", "desk-2:desk"])
    found = scene.steps(plan)
    assert [step for step, _ in found] == ["cutout", "depth", "redraw"]
    assert found[0][1] == ["tools/props/scene/cutout.py", "lab", "bench", "desk@0.4"]
    assert found[2][1][:4] == ["tools/props/scene/redraw.py", "lab", "bench-1:bench", "desk-2:desk"]
    redraw = found[2][1]
    assert redraw[redraw.index("--style") + 1].endswith(LOOK) and redraw[redraw.index("--seeds") + 1] == "7"


def test_a_plan_view_is_uploaded_and_its_folder_mapped():
    plan = planned(view={"picture": "/views/east.png", "out": str(ROOM / "east")},
                   names=["bench"], objects=["bench-1:bench"])
    assert scene.uploads(plan) == [(pathlib.Path("/views/east.png"), scene.REMOTE_INPUTS / "1-east.png")]
    view = ["--picture", "/root/props/inputs/1-east.png", "--out", "/root/props/work/scene/lab/east"]
    found = dict(scene.steps(plan))
    assert found["cutout"][-4:] == view and found["redraw"][-4:] == view


def test_the_batch_list_comes_from_the_redraw_report_at_one_seed():
    plan = {"room": "lab", "objects": ["bench-1:bench", "desk-1:desk"],
            "build": {"faces": 12000, "options": {"bench": "--feet --long"}}}
    lines = scene.batch_lines(plan, {"build": ["bench", "desk"]})
    assert [shlex.split(line) for line in lines] == [
        ["lab-bench", str(ROOM / "redraw" / "bench.png"), "--faces", "12000", "--feet", "--long"],
        ["lab-desk", str(ROOM / "redraw" / "desk.png"), "--faces", "12000"]]
    with pytest.raises(SystemExit, match="single seed"):
        scene.steps(dict(plan, seeds="7,8"))
    with pytest.raises(SystemExit, match="objects"):
        scene.steps({"room": "lab", "build": {}})


def test_every_step_may_load_models_only_up_there():
    line = scene.command(["tools/props/scene/depth.py", "lab"])
    assert "FARM_LOCAL_MODELS=1" in line and "PROPS_HOME=/root/props" in line
    assert line.startswith("cd /root/repo && ")


def test_the_cluster_runs_the_same_steps_on_the_rooms_copy():
    ROOM.mkdir(parents=True, exist_ok=True)
    plan = planned(names=["bench"], depth=True, objects=["bench-1:bench"])
    job = scene.cluster_job(plan, _SANDBOX / "targets.json")
    line = job["command"][2]
    assert line.index("cutout.py lab bench") < line.index("depth.py") < line.index("redraw.py")
    assert {"local": str(ROOM.resolve()), "path": "/root/props/work/scene/lab"} in job["inputs"]
    assert job["outputs"] == [{"path": "/root/props/work/scene/lab", "local": str(ROOM)}]
    assert job["env"]["PROPS_HOME"] == "/root/props"
