"""scene.py's invariants: nothing is rented for a plan without its scene's approved inventory (#121), a scene whose
concept is not locked, an object with no cut-out, a target whose words come from the plan, or a target plan that also
asks for other steps; a plan's steps run in their order (target alone; else cut-out, depth, redraw), the target and
the redraws worded in the place's style (the environment's line, then the locked concept's look); a plan view's
picture goes up and its folder is mapped into the room; the batch list is the redraw report's objects at a single
seed; every step runs with the machine's own home and its local models; the cluster job runs the same steps in the
same order on the room's copy and brings the room back.

One test runs every plan row of the lab's one world through `scene.steps` and, for a plan that may run, also through
`uploads`, `target_jobs`, `batch_lines`, `command` and `cluster_job`, comparing each with the row's expected outcome.

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
# The place's words: the environment's line, then the locked concept's look.
STYLE = f"{scene.place.environment_style(scene.place.design()[2].default()).rstrip('.')}. {LOOK}"
ROOM.mkdir(parents=True, exist_ok=True)
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


def redraw(*objects, view=()):
    """redraw.py's arguments for the lab's objects in the place's style at the inventory's single seed."""
    return ["tools/props/scene/redraw.py", "lab", *objects, "--style", STYLE, "--seeds", "7", "--side", "1536",
            *view]


EAST = ["--picture", "/root/props/inputs/1-east.png", "--out", "/root/props/work/scene/lab/east"]

# Each row: a plan, and either the refusal it meets before anything is rented or what it runs: its steps in order,
# its uploads, its target list, and (with a redraw report) its batch list.
CASES = [
    ("no inventory named", {"room": "lab", "names": ["bench"]}, "approved inventory", None),
    ("inventory missing", planned(inventory=str(_SANDBOX / "nowhere.json"), names=["bench"]), "no inventory", None),
    ("inventory not approved", planned(inventory=inventory_like("workshop", scene="workshop", approved=""),
                                       names=["bench"]), "not approved", None),
    ("concept not locked", planned(inventory=inventory_like("shed", scene="shed", place="shed"), names=["bench"]),
     "no locked concept", None),
    ("object with no cut-out", planned(objects=["none:lamp:a globe lamp"]), "no box, no row", None),
    ("target worded by the plan", planned(target={"sentence": "a lab"}), "its design", None),
    ("target with other steps", planned(target={"takes": 2}, names=["bench"]), "pick one", None),
    ("build at several seeds", planned(objects=["bench-1:bench"], build={}, seeds="7,8"), "single seed", None),
    ("build with no objects", {"room": "lab", "build": {}}, "objects", None),
    ("target alone", planned(target={"refs": ["/refs/one.png"], "takes": 2}), None, {
        "steps": [("target", ["tools/props/scene/target.py", "--list", "/root/props/inputs/targets.json",
                              "--takes", "2", "--refs-on", "2"])],
        "uploads": [(pathlib.Path("/refs/one.png"), scene.REMOTE_INPUTS / "1-one.png")],
        "targets": [{"scene": "lab", "sentence": STYLE, "shot": "inside", "refs": ["/root/props/inputs/1-one.png"]}]}),
    ("cut-out, depth, redraw", planned(names=["bench", "desk@0.4"], depth=True, objects=["bench-1:bench", "desk-2:desk"]),
     None, {"steps": [("cutout", ["tools/props/scene/cutout.py", "lab", "bench", "desk@0.4"]),
                      ("depth", ["tools/props/scene/depth.py", "lab"]),
                      ("redraw", redraw("bench-1:bench", "desk-2:desk"))],
            "uploads": []}),
    ("plan view", planned(view={"picture": "/views/east.png", "out": str(ROOM / "east")}, names=["bench"],
                          objects=["bench-1:bench"]), None, {
        "steps": [("cutout", ["tools/props/scene/cutout.py", "lab", "bench", *EAST]),
                  ("redraw", redraw("bench-1:bench", view=EAST))],
        "uploads": [(pathlib.Path("/views/east.png"), scene.REMOTE_INPUTS / "1-east.png")]}),
    ("batch list from the redraw report", planned(objects=["bench-1:bench", "desk-1:desk"],
                                                  build={"faces": 12000, "options": {"bench": "--feet --long"}}),
     None, {"steps": [("redraw", redraw("bench-1:bench", "desk-1:desk"))], "uploads": [],
            "report": {"build": ["bench", "desk"]},
            "batch": [["lab-bench", str(ROOM / "redraw" / "bench.png"), "--faces", "12000", "--feet", "--long"],
                      ["lab-desk", str(ROOM / "redraw" / "desk.png"), "--faces", "12000"]]}),
]


@pytest.mark.parametrize("plan, refusal, runs", [case[1:] for case in CASES], ids=[case[0] for case in CASES])
def test_scene_runs_only_an_approved_locked_plan_in_order(plan, refusal, runs):
    if refusal:
        with pytest.raises(SystemExit, match=refusal):
            scene.steps(plan)
        return
    found = scene.steps(plan)
    assert found == runs["steps"]
    assert scene.uploads(plan) == runs["uploads"]
    if "target" in plan:
        assert scene.target_jobs(plan) == runs["targets"]
    if "report" in runs:
        assert [shlex.split(line) for line in scene.batch_lines(plan, runs["report"])] == runs["batch"]
    for _, arguments in found:
        line = scene.command(arguments)
        assert "FARM_LOCAL_MODELS=1" in line and "PROPS_HOME=/root/props" in line
        assert line.startswith("cd /root/repo && ")
    job = scene.cluster_job(plan, _SANDBOX / "targets.json")
    assert job["command"][2].split(" && ")[1:] == [f"sam-run {shlex.join(arguments)}" for _, arguments in found]
    assert {"local": str(ROOM.resolve()), "path": "/root/props/work/scene/lab"} in job["inputs"]
    assert job["outputs"] == [{"path": "/root/props/work/scene/lab", "local": str(ROOM)}]
    assert job["env"]["PROPS_HOME"] == "/root/props"
