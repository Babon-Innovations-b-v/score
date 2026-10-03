"""Check that a scene plan becomes the right steps on the machine and the right batch list, without
renting anything.

Run: python3 tools/props/cloud/scene_test.py
"""
import os
import pathlib
import shlex
import sys
import tempfile

_SANDBOX = pathlib.Path(tempfile.mkdtemp(prefix="scene-test-"))
# paths.py reads these when it is imported, so they come first.
os.environ["PROPS_HOME"] = str(_SANDBOX)
os.environ["PROPS_WORK"] = str(_SANDBOX / "work")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import scene  # noqa: E402

ROOM = _SANDBOX / "work" / "scene" / "lab"


def refused(plan, word):
    try:
        scene.steps(plan)
    except SystemExit as refusal:
        assert word in str(refusal), refusal
    else:
        raise AssertionError(f"accepted a plan that should be refused: {plan}")


def test_a_target_plan_draws_takes_alone():
    plan = {"room": "lab", "target": {"sentence": "a lab", "refs": ["/refs/one.png"], "takes": 2}}
    [(step, arguments)] = scene.steps(plan)
    assert step == "target"
    assert arguments[:3] == ["tools/props/scene/target.py", "--list", "/root/props/inputs/targets.json"]
    assert arguments[3:] == ["--takes", "2", "--refs-on", "2"]
    [job] = scene.target_jobs(plan)
    assert job["refs"] == ["/root/props/inputs/1-one.png"] and job["scene"] == "lab"
    refused(dict(plan, names=["bench"]), "pick one")


def test_the_steps_run_in_order_on_the_target():
    plan = {"room": "lab", "names": ["bench", "desk@0.4"], "depth": True,
            "objects": ["bench-1:bench", "none:lamp:a globe lamp"]}
    found = scene.steps(plan)
    assert [step for step, _ in found] == ["cutout", "depth", "redraw"]
    assert found[0][1] == ["tools/props/scene/cutout.py", "lab", "bench", "desk@0.4"]
    assert found[2][1] == ["tools/props/scene/redraw.py", "lab", "bench-1:bench", "none:lamp:a globe lamp",
                           "--seeds", "7", "--side", "1536"]


def test_a_plan_view_is_uploaded_and_its_folder_mapped():
    plan = {"room": "lab", "view": {"picture": "/views/east.png", "out": str(ROOM / "east")},
            "names": ["bench"], "objects": ["bench-1:bench"]}
    assert scene.uploads(plan) == [(pathlib.Path("/views/east.png"), scene.REMOTE_INPUTS / "1-east.png")]
    view = ["--picture", "/root/props/inputs/1-east.png", "--out", "/root/props/work/scene/lab/east"]
    found = dict(scene.steps(plan))
    assert found["cutout"][-4:] == view and found["redraw"][-4:] == view


def test_the_batch_list_comes_from_the_redraw_report():
    plan = {"room": "lab", "objects": ["bench-1:bench", "desk-1:desk"],
            "build": {"faces": 12000, "options": {"bench": "--feet --long"}}}
    lines = scene.batch_lines(plan, {"build": ["bench", "desk"]})
    assert [shlex.split(line) for line in lines] == [
        ["lab-bench", str(ROOM / "redraw" / "bench.png"), "--faces", "12000", "--feet", "--long"],
        ["lab-desk", str(ROOM / "redraw" / "desk.png"), "--faces", "12000"]]
    refused(dict(plan, seeds="7,8"), "single seed")
    refused({"room": "lab", "build": {}}, "objects")


def test_every_step_may_load_models_only_up_there():
    line = scene.command(["tools/props/scene/depth.py", "lab"])
    assert "FARM_LOCAL_MODELS=1" in line and "PROPS_HOME=/root/props" in line
    assert line.startswith("cd /root/repo && ")


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("scene_test: ok")
