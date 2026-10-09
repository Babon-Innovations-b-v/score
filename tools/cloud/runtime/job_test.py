"""Checks for the job entrypoint and its submit side against a folder store, no cloud: a job submitted with code,
an input and a model runs, uploads its outputs and done.json last; a done job is not run again; a failure is
recorded per attempt and retried up to its limit; a command past its minutes is stopped.

Run: .venv/bin/python tools/cloud/runtime/job_test.py   (make tests runs it)
"""
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(tempfile.mkdtemp())
os.environ["SCORE_WORK"] = str(ROOT / "work")
os.environ["SCORE_CACHE"] = str(ROOT / "cache")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import job as jobs  # noqa: E402
import store as stores  # noqa: E402
import submit  # noqa: E402

PYTHON = sys.executable


def a_repo():
    """A small repo with one script and one image folder's models.json naming a model to seed from a file."""
    repo = pathlib.Path(tempfile.mkdtemp())
    (repo / "tools").mkdir()
    (repo / "tools/echo.py").write_text(
        "import os, pathlib, sys\n"
        "text = pathlib.Path(sys.argv[1]).read_text()\n"
        "model = (pathlib.Path(os.environ['SCORE_MODEL_TINY']) / 'model.bin').read_text()\n"
        "out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'a.txt').write_text(text.upper() + ' ' + model)\n"
        "(out / 'sub').mkdir(exist_ok=True); (out / 'sub/b.txt').write_text(os.environ['SCORE_JOB'])\n"
        "print('echoed')\n")
    (repo / "tools/__pycache__").mkdir()
    (repo / "tools/__pycache__/junk.pyc").write_text("x")
    source = repo / "model.bin"
    source.write_text("weights")
    images = repo / "tools/cloud/images/echo"
    images.mkdir(parents=True)
    (images / "models.json").write_text(json.dumps([{"name": "tiny", "source": f"url:{source.as_uri()}",
                                                     "revision": "v1", "licence": "MIT", "commercial_use": True}]))
    return repo


def submitted(store, run, job, command, up=ROOT / "up", **extra):
    """A job of the echo kind in the store, its input uploaded; its spec."""
    repo = a_repo()
    local = pathlib.Path(tempfile.mkdtemp()) / "in.txt"
    local.write_text("hello")
    spec = {"kind": "echo", "image": "registry/score-echo:1@sha256:x",
            "code": submit.upload_code(store, ["tools"], kind="echo", repo=repo),
            "inputs": [submit.upload_input(store, run, job, local, str(up / "in.txt"))],
            "outputs": [{"path": str(up / "out"), "key": submit.output_key(run, job, "out")}],
            "command": command, "models": ["tiny"], "minutes": 1, **extra}
    submit.write_job(store, run, job, spec)
    return spec


def test_a_job_runs_and_its_outputs_come_back():
    store = stores.FolderStore(ROOT / "store-a")
    submitted(store, "r1", "j1", [PYTHON, "tools/echo.py", str(ROOT / "up/in.txt"), str(ROOT / "up/out")])
    assert submit.state(store, "r1", "j1") == "waiting"
    assert jobs.run_job(store, "r1", "j1") == 0
    assert submit.state(store, "r1", "j1") == "done"
    record = submit.done(store, "r1", "j1")
    assert list(record["timings"]) == ["pod_start", "weights_ready", "inputs_ready", "first_result", "uploaded"]
    assert record["image"] == "registry/score-echo:1@sha256:x" and record["card"] and record["node"]
    local = pathlib.Path(tempfile.mkdtemp())
    submit.fetch_outputs(store, "r1", "j1", {str(ROOT / "up/out"): local / "out"})
    assert (local / "out/a.txt").read_text() == "HELLO weights"
    assert (local / "out/sub/b.txt").read_text() == "j1"
    assert "echoed" in store.read_bytes("runs/r1/j1/log-1.txt").decode()


def test_a_done_job_is_not_run_again():
    store = stores.FolderStore(ROOT / "store-b")
    submitted(store, "r1", "j1", [PYTHON, "-c", "import sys; sys.exit(9)"])
    stores.write_json(store, "runs/r1/j1/done.json", {"attempt": 1})
    assert jobs.run_job(store, "r1", "j1") == 0
    assert not store.keys("runs/r1/j1/failed-")


def test_failures_are_recorded_and_retried_up_to_the_limit():
    store = stores.FolderStore(ROOT / "store-c")
    submitted(store, "r1", "j1", [PYTHON, "-c", "print('boom'); raise SystemExit(4)"], attempt_limit=2)
    assert jobs.run_job(store, "r1", "j1") == 1
    assert jobs.run_job(store, "r1", "j1") == 1
    assert jobs.run_job(store, "r1", "j1") == jobs.EXIT_NO_ATTEMPTS
    failed = submit.failures(store, "r1", "j1")
    assert [record["attempt"] for record in failed] == [1, 2]
    assert failed[0]["stage"] == "command" and "boom" in "\n".join(failed[0]["log_tail"])
    assert submit.state(store, "r1", "j1") == "failed"


def test_a_command_past_its_minutes_is_stopped():
    store = stores.FolderStore(ROOT / "store-d")
    submitted(store, "r1", "j1", [PYTHON, "-c", "import time; time.sleep(60)"], minutes=0.02)
    assert jobs.run_job(store, "r1", "j1") == 1
    assert "minutes" in submit.failures(store, "r1", "j1")[0]["error"]


def test_a_missing_output_fails_the_job():
    store = stores.FolderStore(ROOT / "store-e")
    submitted(store, "r1", "j1", [PYTHON, "-c", "pass"], up=ROOT / "up-e")
    assert jobs.run_job(store, "r1", "j1") == 1
    assert submit.failures(store, "r1", "j1")[0]["stage"] == "outputs"


def test_a_command_that_cannot_start_is_a_recorded_failure():
    store = stores.FolderStore(ROOT / "store-g")
    script = pathlib.Path(tempfile.mkdtemp()) / "not-executable.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o644)
    for job, command in (("denied", [str(script)]), ("missing", ["/no/such/program"])):
        submitted(store, "r1", job, command, up=ROOT / f"up-{job}")
        assert jobs.run_job(store, "r1", job) == 1
        failed = submit.failures(store, "r1", job)[0]
        assert failed["stage"] == "command" and "could not start" in failed["error"]
        assert store.exists(f"runs/r1/{job}/log-1.txt")


def test_one_tree_bundles_to_one_key_without_caches():
    repo = a_repo()
    first = submit.bundle(["tools"], repo)
    (repo / "tools/echo.py").touch()  # a newer time, the same content
    assert submit.bundle(["tools"], repo) == first
    store = stores.FolderStore(ROOT / "store-f")
    key = submit.upload_code(store, ["tools"], kind="echo", repo=repo)
    assert key.startswith("code/") and store.exists(key)
    assert all("__pycache__" not in str(name) for name in submit.bundled_files(["tools"], repo))


def test_the_store_is_named_by_the_environment():
    folder = stores.from_environment({"SCORE_STORE_ENDPOINT": f"file://{ROOT}/s"})
    assert isinstance(folder, stores.FolderStore)
    spec = {"endpoint": "https://s3.example", "region": "r", "bucket": "b", "access_key": "a", "secret_key": "s"}
    assert stores.environment(spec)["SCORE_STORE_BUCKET"] == "b"
    try:
        stores.from_environment({"SCORE_STORE_ENDPOINT": "https://s3.example"})
    except SystemExit as refusal:
        assert "SCORE_STORE_BUCKET" in str(refusal)
    else:
        raise AssertionError("a bucket store opened without its bucket")


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("job_test: ok")
