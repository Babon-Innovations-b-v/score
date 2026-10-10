"""Checks for prove.py without the cloud: a job's marks are seconds from the container's start, a plan's job becomes
a job.json with its inputs uploaded and its outputs keyed under the run, and the numbers land in images.json under the
kind's proof, by card.

Run: .venv/bin/python tools/cloud/images/prove_test.py   (make tests runs it)
"""
import json
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import prove  # noqa: E402
from build import stores, submit  # noqa: E402


def test_marks_are_seconds_from_the_start():
    timings = {"pod_start": "2026-10-09T14:00:00.000000Z", "weights_ready": "2026-10-09T14:01:30.500000Z",
               "first_result": "2026-10-09T14:05:00.000000Z", "node": "n1"}
    assert prove.seconds_of(timings) == {"weights_ready": 90.5, "first_result": 300.0}


def test_a_plan_job_becomes_a_job_spec():
    folder = pathlib.Path(tempfile.mkdtemp())
    store = stores.open_store({"endpoint": (folder / "store").as_uri()})
    local = folder / "jobs.json"
    local.write_text("[]")
    job = {"kind": "judge", "name": "first-node", "cache": "a", "models": ["qwen3.8-27b-fp8"], "minutes": 40,
           "command": ["judge-run", "x.py"], "kernel_cache": "judge-vllm-0.31.0",
           "outputs": [{"path": "/root/judge/out", "to": str(folder / "out")}]}
    prove.job_spec(store, "run1", "judge-first-node", "image@sha256:1", "code/1.tar.gz",
                   [{"from": str(local), "path": "/root/judge/jobs.json"}], job)
    spec = stores.read_json(store, "runs/run1/judge-first-node/job.json")
    assert spec["inputs"][0]["path"] == "/root/judge/jobs.json"
    assert spec["outputs"] == [{"path": "/root/judge/out", "key": submit.output_key("run1", "judge-first-node", "out")}]
    assert spec["kernel_cache"] == "judge-vllm-0.31.0" and spec["models"] == ["qwen3.8-27b-fp8"]


def test_results_land_under_the_kind_s_proof_by_card():
    folder = pathlib.Path(tempfile.mkdtemp())
    prove.build.IMAGES_JSON = folder / "images.json"
    prove.build.IMAGES_JSON.write_text(json.dumps({"judge": {"image": "x"}}))
    prove.save_results({"judge": [{"type": "H100-1-80G", "jobs": {"first-node": {"card": "nvidia-h100-580"}}}]})
    saved = json.loads(prove.build.IMAGES_JSON.read_text())
    assert saved["judge"]["proof"]["nvidia-h100-580"]["type"] == "H100-1-80G"


def test_no_offer_is_no_machine_and_a_proof_records_its_run():
    import build_test

    seen, restore = build_test.renting("gpu-80gb", None)
    plan = {"classes": ["gpu-80gb"], "minutes": 30, "runs": [{"kind": "judge", "jobs": []}]}
    proved = []
    kept = prove.set_up, prove.prove_on, prove.batch.offers
    prove.set_up = lambda machine, registry, store_spec: None
    prove.prove_on = lambda machine, plan, store_spec, results: proved.append(machine["class"])
    try:
        prove.batch.offers = lambda classes: []
        assert prove.one_attempt(plan, "account", {}, {}, "tester", {}) is False
        prove.batch.offers = kept[2]
        assert prove.one_attempt(plan, "account", {}, {}, "tester", {}) is True
    finally:
        prove.set_up, prove.prove_on, prove.batch.offers = kept
        restore()
    assert proved == ["gpu-80gb"] and [machine["class"] for machine in seen["deleted"]] == ["gpu-80gb"]
    assert seen["ledger"][0]["kind"] == "prove" and seen["ledger"][0]["runs"] == ["judge"]


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("prove_test: ok")
