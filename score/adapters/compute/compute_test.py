"""Nothing reaches the job store without a runner's key for a node whose prerequisites passed and are accepted, and
the owner's yes to that run. No cloud: the job store is a folder.

Run: .venv/bin/python score/adapters/compute/compute_test.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score import checks, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.store import Store  # noqa: E402


def make_brief(inputs, out, seed, params):
    (out / "brief.txt").write_text(inputs["brief"].read_text())


def judge_brief(output, inputs, evidence):
    text = (output / "brief.txt").read_text()
    return checks.Verdict("said", checks.PASS if text.strip() else checks.FAIL, "a brief was written")


def make_nothing(inputs, out, seed, params):
    raise AssertionError("a paid stage's make is not run by these tests")


BRIEF = graph.Stage("brief", "place", make_brief, (checks.Check("said", judge_brief),),
                    files={"brief": "{data}/{place}.txt"})
RENDER = graph.Stage("render", "place", make_nothing, after=("brief",), paid=True)


def a_runner(text):
    data, store = pathlib.Path(tempfile.mkdtemp()), Store.in_folder(tempfile.mkdtemp())
    (data / "hangar.txt").write_text(text)
    runner = graph.Runner([BRIEF, RENDER], graph.World("toy", 1, {"data": data}), store)
    runner.run_node(BRIEF, "hangar")
    return runner


def accept_brief(runner):
    output = runner.store.records("brief@hangar")[-1]["output"]
    runner.store.write_accept("brief@hangar", {"output": output, "at": graph.now()})


def refused(call):
    try:
        call()
    except compute.Refused as refusal:
        return str(refusal)
    raise AssertionError("taken")


def a_job(runner):
    job_store = compute.job_contract.stores.FolderStore(tempfile.mkdtemp())
    spec = {"kind": "blender", "image": "img", "command": ["true"]}
    return job_store, lambda: compute.submit(runner, "render@hangar", job_store, "run1", "job1", spec)


def test_a_node_whose_prerequisite_failed_or_is_not_accepted_is_refused():
    failed = a_runner("   ")
    assert "brief@hangar answered fail" in refused(a_job(failed)[1])
    unaccepted = a_runner("a hall")
    assert "is not accepted by the owner" in refused(a_job(unaccepted)[1])


def test_a_cleared_node_without_the_owners_yes_is_refused_and_with_it_is_submitted():
    runner = a_runner("a hall")
    accept_brief(runner)
    job_store, send = a_job(runner)
    assert "has not said yes" in refused(send)
    assert job_store.keys("") == []
    key = runner.ticket("render@hangar")["key"]
    runner.store.write_spend_yes("render@hangar", key, {"euros": 1.0, "at": graph.now()})
    written = send()
    job = compute.job_contract.stores.read_json(job_store, written)
    assert job["node"] == "render@hangar" and job["node_key"] == key


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
