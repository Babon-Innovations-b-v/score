"""An image is built again only when what goes into it changed, and every machine the builder, the prover or the
warmer rents is deleted and its run recorded, however the work ends.

Offline: the cloud (batch, the provider, spread.on_machines, the ledger) is stubbed; nothing is rented. Each invariant
with the break that turns it red (each applied once and seen red):

- The tag is IMAGE_VERSION and a hash of the build context with each file's mode, the runtime's files (its tests
  left out), and the parent's digest; models.json (the weights list, fetched at run time) is not in it.
  Break: drop `if name != "models.json"` in `tag`. Break: drop the mode from `tag`'s hash.
  Break: drop the parent digest from `tag`. Break: drop either test-name filter in `context_files`.
- Only what changed is built: a kind at its tag is skipped, a child is built with its new parent, `force` builds all;
  the parent comes first. Break: drop `parent_new` in `stale`. Break: `image_kinds` returns plain `sorted(kinds)`.
- The staged context keeps each file's mode (a script the Dockerfile copies stays executable).
  Break: `shutil.copy` for `shutil.copy2` in `staged_context`.
- buildx pushes with the registry as its layer cache and the parent's digest as BASE.
  Break: drop `"--push"` in `build_command`.
- A failed build still deletes its machine, records the run in the ledger and stops with an error.
  Break: move `batch.delete_machine` out of `rent_one`'s `finally`. Break: drop the `shares.failed` check in `build`.
- A proof or a warm-up with no offer rents nothing; with one, its single machine is deleted and recorded by kind.
  Break: `return True` at the top of `one_attempt`. Break: drop `if refused: ... return` in `measure_class`.
- A proof's job is a job.json with its inputs uploaded and outputs keyed under the run; its marks are seconds from
  the container's start; its numbers land in images.json under the kind's proof, by card.
  Break: drop the kernel cache in `job_spec`. Break: key the proof by `numbers["type"]` always in `save_results`.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import build  # noqa: E402
import prove  # noqa: E402
import warm  # noqa: E402
from build import stores, submit  # noqa: E402


@pytest.fixture
def images(tmp_path, monkeypatch):
    """The builder pointed at a scratch images folder: a base, a child of it, and a runtime with a test file."""
    for kind, text in (("base", "# platforms: linux/amd64,linux/arm64\nFROM x\n"),
                       ("child", "ARG BASE\nFROM ${BASE}\n")):
        (tmp_path / kind).mkdir()
        (tmp_path / kind / "Dockerfile").write_text(text)
        (tmp_path / kind / "models.json").write_text("[]")
    (tmp_path / "runtime").mkdir()
    (tmp_path / "runtime/job.py").write_text("print()")
    (tmp_path / "runtime/job_test.py").write_text("print()")
    (tmp_path / "runtime/test_job.py").write_text("print()")
    monkeypatch.setattr(build, "HERE", tmp_path)
    monkeypatch.setattr(build, "RUNTIME", tmp_path / "runtime")
    return tmp_path


PARENT_A = {"base": {"digest": "sha256:a"}}


def test_the_tag_follows_the_context_its_modes_and_the_parent_but_not_the_weights_list(images):
    first = build.tag("base", {})
    assert first.startswith(build.IMAGE_VERSION + "-")
    (images / "base/models.json").write_text('[{"name": "x"}]')
    assert build.tag("base", {}) == first
    (images / "runtime/job_test.py").write_text("print(2)")
    (images / "runtime/test_job.py").write_text("print(2)")
    assert build.tag("base", {}) == first  # the runtime's tests are not in the image
    (images / "runtime/job.py").write_text("print(1)")
    assert build.tag("base", {}) != first

    child = build.tag("child", PARENT_A)
    assert build.tag("child", {"base": {"digest": "sha256:b"}}) != child
    script = images / "child/run.sh"
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    executable = build.tag("child", PARENT_A)
    script.chmod(0o644)
    assert build.tag("child", PARENT_A) != executable


def test_only_what_changed_is_built_the_parent_first(images):
    assert build.image_kinds() == ["base", "child"]
    built = {"base": {"tag": build.tag("base", {}), "digest": "sha256:a"}}
    built["child"] = {"tag": build.tag("child", built)}
    assert build.stale(["base", "child"], built, force=False) == []
    assert build.stale(["base", "child"], built, force=True) == ["base", "child"]
    assert build.stale(["child"], {}, force=False) == ["child"]
    assert build.stale(["base", "child"], {**built, "base": {**built["base"], "tag": "old"}}, force=False) == [
        "base", "child"]


def test_the_staged_context_keeps_modes_and_buildx_pushes_with_a_registry_cache(images):
    script = images / "child/run.sh"
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    staged = build.staged_context("child", images)
    assert (staged / "run.sh").stat().st_mode & 0o777 == 0o755
    assert (staged / "runtime/job.py").read_text() == "print()" and not (staged / "runtime/job_test.py").exists()

    command = build.build_command("child", "reg/score-child:1-x", "reg/score-child:buildcache", "reg/base@sha256:a")
    assert "--push" in command and "BASE=reg/base@sha256:a" in command
    assert "type=registry,ref=reg/score-child:buildcache" in command
    assert any(part.startswith("type=registry,ref=reg/score-child:buildcache,mode=max") for part in command)
    assert build.platforms("base") == "linux/amd64,linux/arm64" and build.platforms("child") == "linux/amd64"


@pytest.fixture
def renting(tmp_path, monkeypatch):
    """renting(machine_class, work): batch, the provider and spread.on_machines stood in for by one machine of
    `machine_class` that runs `work(machine, kind)` on each share; what was deleted, recorded and said."""
    seen = {"deleted": [], "ledger": [], "said": []}

    def start(machine_class, work=None):
        def on_machines(run, _account, _found, _count, _kind, shares, prepare, do, disk_gb=None):
            machine = {"folder": run.folder / "m1", "host": "h", "class": machine_class, "type": "T", "zone": "z",
                       "created": 0.0}
            machine["folder"].mkdir(parents=True)
            run.machines.append(machine)
            prepare(machine)
            while shares.waiting:
                share = shares.waiting.popleft()
                try:
                    do(machine, share, None)
                except RuntimeError:
                    shares.failed.append(share)

        class Offer:
            price = 0.01
        for owner, name, value in (
                (build.batch, "BATCHES", tmp_path / "batches"), (build.batch, "offers", lambda classes: [Offer()]),
                (build.batch, "month_spent", lambda account: 0.0), (build.batch, "sweep", lambda account: None),
                (build.batch, "ssh_key", lambda: "key"), (build.batch, "stop_on_signals", lambda: None),
                (build.batch, "remote", lambda *arguments, **keywords: None),
                (build.batch, "delete_machine", seen["deleted"].append), (build.batch, "say", seen["said"].append),
                (build.ledger, "record", seen["ledger"].append),
                (build.ledger, "machines_record", lambda machines, attempts, started: {"euros": 0.5}),
                (build.spread, "on_machines", on_machines), (build.cloud, "account", lambda: "account"),
                (build.cloud, "registry", lambda: {"endpoint": "reg/ns", "username": "u", "password": "p"}),
                (build.cloud, "allow_key", lambda account, name, key: None),
                (build, "build_one", lambda machine, kind, registry, built: work(machine, kind))):
            monkeypatch.setattr(owner, name, value)
        return seen
    return start


def test_a_failed_build_still_deletes_its_machine_and_records_the_run(images, renting, monkeypatch, tmp_path):
    def work(_machine, kind):
        if kind == "child":
            raise RuntimeError("buildx exited with 1")
    seen = renting("cpu-16c-64gb", work)
    with pytest.raises(SystemExit, match="did not finish"):
        build.build(["base", "child"], "tester", smoke_test=False)
    assert [machine["class"] for machine in seen["deleted"]] == ["cpu-16c-64gb"]
    entry = seen["ledger"][0]
    assert entry["kind"] == "images" and entry["who"] == "tester" and entry["images"] == ["base", "child"]
    assert entry["euros"] == 0.5

    def stopped(_machine, kind):
        raise KeyboardInterrupt  # a stop mid-build leaves the spread runner itself
    seen = renting("cpu-16c-64gb", stopped)
    monkeypatch.setattr(build.batch, "BATCHES", tmp_path / "batches-stopped")  # the run folder is named by the second
    with pytest.raises(KeyboardInterrupt):
        build.build(["base"], "tester", smoke_test=False)
    assert len(seen["deleted"]) == 2 and len(seen["ledger"]) == 2


def test_a_proof_or_warm_up_with_no_offer_rents_nothing_and_with_one_its_machine_goes(renting, monkeypatch):
    seen = renting("gpu-80gb")
    offers = build.batch.offers
    plan = {"classes": ["gpu-80gb"], "minutes": 30, "runs": [{"kind": "judge", "jobs": []}]}
    proved, measured = [], []
    monkeypatch.setattr(prove, "set_up", lambda machine, registry, store_spec: None)
    monkeypatch.setattr(prove, "prove_on", lambda machine, plan, store_spec, results: proved.append(machine["class"]))
    monkeypatch.setattr(warm, "set_up", lambda machine, registry, store_spec: None)
    monkeypatch.setattr(warm, "measure", lambda machine, image, store_spec, results: measured.append(machine["class"]))
    monkeypatch.setattr(build.batch, "offers", lambda classes: [])
    assert prove.one_attempt(plan, "account", {}, {}, "tester", {}) is False
    warm.measure_class("gpu-80gb", "image", {}, {}, "tester", {})
    assert proved == measured == [] and seen["deleted"] == [] and seen["ledger"] == []
    assert "gpu-80gb: refused: no offer" in seen["said"]
    monkeypatch.setattr(build.batch, "offers", offers)
    assert prove.one_attempt(plan, "account", {}, {}, "tester", {}) is True
    warm.measure_class("gpu-80gb", "image", {}, {}, "tester", {})
    assert proved == measured == ["gpu-80gb"] and len(seen["deleted"]) == 2
    assert [entry["kind"] for entry in seen["ledger"]] == ["prove", "warm"]
    assert seen["ledger"][0]["runs"] == ["judge"] and seen["ledger"][1]["class"] == "gpu-80gb"


def test_a_proofs_job_spec_marks_and_results(tmp_path, monkeypatch):
    store = stores.open_store({"endpoint": (tmp_path / "store").as_uri()})
    local = tmp_path / "jobs.json"
    local.write_text("[]")
    job = {"kind": "judge", "name": "first-node", "models": ["qwen3.8-27b-fp8"], "minutes": 40,
           "command": ["judge-run", "x.py"], "kernel_cache": "judge-vllm-0.31.0",
           "outputs": [{"path": "/root/judge/out", "to": str(tmp_path / "out")}]}
    prove.job_spec(store, "run1", "judge-first-node", "image@sha256:1", "code/1.tar.gz",
                   [{"from": str(local), "path": "/root/judge/jobs.json"}], job)
    spec = stores.read_json(store, "runs/run1/judge-first-node/job.json")
    assert spec["inputs"][0]["path"] == "/root/judge/jobs.json"
    assert spec["outputs"] == [{"path": "/root/judge/out", "key": "runs/run1/judge-first-node/out/out"}]
    assert spec["kernel_cache"] == "judge-vllm-0.31.0" and spec["models"] == ["qwen3.8-27b-fp8"]

    timings = {"pod_start": "2026-10-09T14:00:00.000000Z", "weights_ready": "2026-10-09T14:01:30.500000Z",
               "first_result": "2026-10-09T14:05:00.000000Z", "node": "n1"}
    assert prove.seconds_of(timings) == {"weights_ready": 90.5, "first_result": 300.0}

    monkeypatch.setattr(build, "IMAGES_JSON", tmp_path / "images.json")
    build.IMAGES_JSON.write_text(json.dumps({"judge": {"image": "x"}}))
    prove.save_results({"judge": [{"type": "H100-1-80G", "jobs": {"first-node": {"card": "nvidia-h100-580"}}},
                                  {"type": "L4-1-24G", "jobs": {"first-node": {}}}]})
    proof = json.loads(build.IMAGES_JSON.read_text())["judge"]["proof"]
    assert proof["nvidia-h100-580"]["type"] == "H100-1-80G" and proof["L4-1-24G"]["type"] == "L4-1-24G"
