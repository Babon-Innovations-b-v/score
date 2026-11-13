"""An image is built again only when what goes into it changed, and every machine the builder, the prover or the
warmer rents is deleted and its run recorded, however the work ends.

Offline: the cloud (batch's machines and ssh, the provider, spread.on_machines, the ledger) is stood in for by one fake
machine whose remote commands answer like docker and buildx; nothing is rented. One world (a base, a child `app`, the
runner exported from a scratch repository) is built, proved and warmed through the real entry points, each way the
work can end a row; then rows of moves to that world ask what `stale` builds again. Each invariant with the break that
turns it red (each applied once and seen red):

- The tag is IMAGE_VERSION and a hash of the build context with each file's mode, the runtime's files (its tests
  left out), and the parent's digest; models.json (the weights list, fetched at run time) is not in it.
  Break: drop `if name != "models.json"` in `tag`. Break: drop the mode from `tag`'s hash.
  Break: drop the parent digest from `tag`. Break: drop either test-name filter in `context_files`.
- The runner's tag moves when uv.lock moves and stays when it does not: `export_runner` writes the lock's export,
  its sha256 (lock.sha256) and a link to each file wheel at its repository path, in a scratch repository.
  Break: leave lock.sha256 out of `tag`'s hash (`if name not in ("models.json", "lock.sha256")`).
- Only what changed is built: a kind at its tag is skipped, a child is built with its new parent, `force` builds all;
  the parent comes first. Break: drop `parent_new` in `stale`. Break: `image_kinds` returns plain `sorted(kinds)`.
- The staged context keeps each file's mode (a script the Dockerfile copies stays executable).
  Break: `shutil.copyfile` for `shutil.copy2` in `staged_context` (`shutil.copy` keeps the mode too).
- buildx pushes with the registry as its layer cache and the parent's digest as BASE.
  Break: drop `"--push"` in `build_command`.
- A failed build still deletes its machine, records the run in the ledger and stops with an error.
  Break: move `batch.delete_machine` out of `rent_one`'s `finally`. Break: drop the `shares.failed` check in `build`.
- A proof or a warm-up with no offer rents nothing; with one, its single machine is deleted and recorded by kind.
  Break: `return True` at the top of `one_attempt`. Break: drop `if refused: ... return` in `measure_class`.
  Under a runner's ticket the proof keeps its pre-flight, its jobs on one card for the minutes the card is held, where
  the runaway watch reads it; outside one it keeps none (2026-11-09: every sound row stopped at twice a one-take
  forecast). Break: drop `keep_preflight(plan, held)` in `one_attempt`. Break: drop the ticket check in
  `keep_preflight`.
- A proof's job is a job.json with its inputs uploaded and outputs keyed under the run; its marks are seconds from
  the container's start; its numbers land in images.json under the kind's proof, by card.
  Break: drop the kernel cache in `job_spec`. Break: key the proof by `numbers["type"]` always in `save_results`.
- A proof on a processor machine (the runner's) sets up docker without the NVIDIA toolkit and runs without --gpus.
  Break: `on_a_card` returns True.
"""
import json
import pathlib
import shlex
import shutil
import sys
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import build  # noqa: E402
import prove  # noqa: E402
import warm  # noqa: E402
from build import stores, submit  # noqa: E402

TYPES = {"cpu-16c-64gb": "POP2-16C-64G", "gpu-80gb": "H100-1-80G"}
CARD = "nvidia-h100-580"  # the card a card machine's done.json names; a processor machine names none
TIMINGS = {"pod_start": "2026-10-09T14:00:00.000000Z", "weights_ready": "2026-10-09T14:01:30.500000Z",
           "first_result": "2026-10-09T14:05:00.000000Z", "node": "n1"}
TICKET = "sound@lab abc"
RECORDED = object()  # the call answers the ledger entry it recorded


def world(folder):
    """The images folder: a two-platform base, a child `app` with an executable script, the runner exported from a
    scratch repository (its project, lock and file wheels), and a runtime with a test file under either name."""
    for kind, dockerfile in (("base", "# platforms: linux/amd64,linux/arm64\nFROM x\n"),
                             ("app", "ARG BASE\nFROM ${BASE}\n"), ("runner", "ARG BASE\nFROM ${BASE}\n")):
        (folder / kind).mkdir(parents=True)
        (folder / kind / "Dockerfile").write_text(dockerfile)
    for kind in ("base", "app"):
        (folder / kind / "models.json").write_text("[]")
    (folder / "app/run.sh").write_text("#!/bin/sh\n")
    (folder / "app/run.sh").chmod(0o755)
    (folder / "runtime").mkdir()
    for name in ("job.py", "job_test.py", "test_job.py"):
        (folder / "runtime" / name).write_text("print()")
    repo = folder / "repo"
    (repo / "vendor/kimodo").mkdir(parents=True)
    shutil.copy2(build.REPO / "pyproject.toml", repo)
    shutil.copy2(build.REPO / "uv.lock", repo)
    shutil.copytree(build.REPO / "vendor/kimodo/wheels", repo / "vendor/kimodo/wheels")
    return folder


def point_at(monkeypatch, folder):
    monkeypatch.setattr(build, "HERE", folder)
    monkeypatch.setattr(build, "RUNTIME", folder / "runtime")


def append_line(path):
    with path.open("a") as opened:
        opened.write("\n")


def plan_of(kind, job):
    return {"classes": ["any"], "minutes": 30, "runs": [{"kind": kind, "jobs": [job]}]}


def test_built_once_and_every_machine_deleted(tmp_path, monkeypatch):
    here = world(tmp_path / "world")
    point_at(monkeypatch, here)
    build.export_runner(here / "repo")
    wheels = build.file_wheels((here / "runner/requirements.txt").read_text())
    assert wheels and all((here / "runner" / name).resolve() == (here / "repo" / name).resolve() for name in wheels)
    assert build.image_kinds() == ["base", "app", "runner"]
    monkeypatch.setattr(build, "IMAGES_JSON", tmp_path / "images.json")
    monkeypatch.setattr(submit, "IMAGES", build.IMAGES_JSON)
    objects = stores.open_store({"endpoint": (tmp_path / "objects").as_uri()})
    store_spec = {"endpoint": (tmp_path / "objects").as_uri(), "region": "r", "bucket": "b", "access_key": "a",
                  "secret_key": "s"}
    monkeypatch.setenv(prove.preflight.STORE, str(tmp_path / "preflight"))
    (tmp_path / "jobs.json").write_text("[]")

    # The fake cloud: one machine of the row's class per rent; its commands answer like docker and buildx would.
    seen = {"deleted": [], "ledger": [], "said": [], "warmed": []}
    commands, staged = {}, {}
    row = {}

    def remote(_folder, host, command, **_options):
        commands.setdefault(host, []).append(command)
        words = shlex.split(command) if command.startswith("docker") else []
        answer = {"returncode": 0, "stdout": ""}
        if words[:3] == ["docker", "buildx", "build"]:
            ending = row["buildx"].get(pathlib.PurePosixPath(words[-1]).name, 0)
            if ending == "stop":
                raise KeyboardInterrupt  # a stop mid-build leaves the spread runner itself
            answer["returncode"] = ending
        elif command.startswith("cat ") and command.endswith(".meta.json"):
            kind = pathlib.PurePosixPath(command.split()[1]).name.removesuffix(".meta.json")
            answer["stdout"] = json.dumps({"containerimage.digest": f"sha256:{kind}"})
        elif "imagetools inspect" in command:
            answer["stdout"] = json.dumps({"layers": [{"size": 2_000_000}]})
        elif words[:3] == ["docker", "run", "--rm"]:
            run, name = words[-2:]
            card = {"card": CARD} if row["class"].startswith("gpu") else {}
            stores.write_json(objects, submit.jobs.prefix(run, name) + "done.json",
                              {"timings": TIMINGS, "outputs": [], **card})
        return types.SimpleNamespace(**answer)

    def copy(_folder, sources, destination, *_extra):
        staged[(row["id"], pathlib.PurePosixPath(destination.split(":", 1)[1]).name)] = pathlib.Path(sources[0])

    def on_machines(run, _account, _found, _count, _kind, shares, prepare, do, disk_gb=None):
        machine = {"folder": run.folder / "m1", "host": row["id"], "class": row["class"],
                   "type": TYPES[row["class"]], "zone": "z", "created": 0.0}
        machine["folder"].mkdir(parents=True)
        run.machines.append(machine)
        prepare(machine)
        while shares.waiting:
            share = shares.waiting.popleft()
            try:
                do(machine, share, None)
            except Exception:  # noqa: BLE001 - a failed share is the spread runner's gap, as on_machines keeps it
                shares.failed.append(share)

    class Offer:
        price = 0.01
    for owner, name, value in (
            (build.batch, "offers", lambda classes: [Offer()] if row["offer"] else []),
            (build.batch, "month_spent", lambda account: 0.0), (build.batch, "sweep", lambda account: None),
            (build.batch, "ssh_key", lambda: "key"), (build.batch, "stop_on_signals", lambda: None),
            (build.batch, "remote", remote), (build.batch, "copy", copy),
            (build.batch, "delete_machine", seen["deleted"].append), (build.batch, "say", seen["said"].append),
            (build.ledger, "record", seen["ledger"].append),
            (build.ledger, "machines_record", lambda machines, attempts, started: {"euros": 0.5}),
            (build.spread, "on_machines", on_machines), (build.cloud, "account", lambda: "account"),
            (build.cloud, "registry", lambda: {"endpoint": "reg/ns", "username": "u", "password": "p"}),
            (build.cloud, "allow_key", lambda account, name, key: None),
            (warm, "measure", lambda machine, image, spec, results: seen["warmed"].append(machine["class"]))):
        monkeypatch.setattr(owner, name, value)

    registry, results = build.cloud.registry(), {}
    judge_job = {"name": "first-node", "models": ["qwen3.8-27b-fp8"], "minutes": 40, "cache": "first-node",
                 "command": ["judge-run", "x.py"], "kernel_cache": "judge-vllm-0.31.0",
                 "outputs": [{"path": "/root/judge/out", "to": str(tmp_path / "out")}]}
    app_plan = plan_of("app", judge_job)
    app_plan["runs"][0]["inputs"] = [{"from": str(tmp_path / "jobs.json"), "path": "/root/judge/jobs.json"}]
    runner_plan = plan_of("runner", {"name": "takes", "cache": "takes", "command": ["score", "run"]})
    builder = {"who": "tester", "euros": 0.5}
    # Each way the work ends: (id, the call, offer in stock, the machine's class, the runner's ticket, buildx's exit
    # per kind, the answer or the exception, the classes deleted, the ledger entry's fields, what was said,
    # the pre-flight kept under the ticket: None when no pre-flight store may exist).
    rents = [
        ("built", lambda: build.build(["base", "app", "runner"], "tester", smoke_test=False), True, "cpu-16c-64gb",
         None, {}, RECORDED, ["cpu-16c-64gb"], {"kind": "images", "images": ["base", "app", "runner"], **builder},
         "app: pushed", None),
        ("build-failed", lambda: build.build(["base", "app"], "tester", smoke_test=False), True, "cpu-16c-64gb",
         None, {"app": 1}, (SystemExit, "did not finish"), ["cpu-16c-64gb"],
         {"kind": "images", "images": ["base", "app"], **builder}, "base: pushed", None),
        ("build-stopped", lambda: build.build(["base"], "tester", smoke_test=False), True, "cpu-16c-64gb",
         None, {"base": "stop"}, (KeyboardInterrupt, ""), ["cpu-16c-64gb"],
         {"kind": "images", "images": ["base"], **builder}, "", None),
        ("prove-no-offer", lambda: prove.one_attempt(app_plan, "account", registry, store_spec, "tester", results),
         False, "gpu-80gb", None, {}, False, [], None, "no any offer in stock", None),
        ("warm-no-offer", lambda: warm.measure_class("gpu-80gb", "image", registry, store_spec, "tester", {}),
         False, "gpu-80gb", None, {}, None, [], None, "gpu-80gb: refused: no offer", None),
        ("proved-on-a-card", lambda: prove.one_attempt(app_plan, "account", registry, store_spec, "tester", results),
         True, "gpu-80gb", None, {}, True, ["gpu-80gb"], {"kind": "prove", "runs": ["app"], "who": "tester"},
         "app-first-node: ", None),
        ("warmed", lambda: warm.measure_class("gpu-80gb", "image", registry, store_spec, "tester", {}),
         True, "gpu-80gb", None, {}, None, ["gpu-80gb"], {"kind": "warm", "class": "gpu-80gb", "who": "tester"},
         "gpu-80gb: ", None),
        ("proved-on-a-processor-under-a-ticket",
         lambda: prove.one_attempt(runner_plan, "account", registry, store_spec, "tester", results),
         True, "cpu-16c-64gb", TICKET, {}, True, ["cpu-16c-64gb"], {"kind": "prove", "runs": ["runner"]},
         "runner-takes: ", [(1, 1, 30)]),
    ]
    for (name, call, offer, machine_class, ticket, buildx, expected, deleted, record, said,
         preflight) in rents:
        row.update(id=name, offer=offer, **{"class": machine_class}, buildx=buildx)
        monkeypatch.setattr(build.batch, "BATCHES", tmp_path / "batches" / name)  # a run folder is named by its second
        if ticket:
            monkeypatch.setenv(prove.preflight.TICKET, ticket)
        else:
            monkeypatch.delenv(prove.preflight.TICKET, raising=False)
        deleted_before, ledger_before, said_before = len(seen["deleted"]), len(seen["ledger"]), len(seen["said"])
        if isinstance(expected, tuple):
            with pytest.raises(expected[0], match=expected[1]):
                call()
        else:
            answer = call()
            assert answer == (seen["ledger"][-1] if expected is RECORDED else expected), name
        assert [machine["class"] for machine in seen["deleted"][deleted_before:]] == deleted, name
        entries = seen["ledger"][ledger_before:]
        assert entries == [] if record is None else (len(entries) == 1 and record.items() <= entries[0].items()), name
        assert any(said in line for line in seen["said"][said_before:]), name
        if preflight is None:
            assert not (tmp_path / "preflight").exists(), name  # no ticket, no pre-flight
        else:
            assert [(flight["jobs"], flight["cards"], flight["high_minutes"])
                    for flight in prove.preflight.kept(ticket)] == preflight, name
    assert seen["warmed"] == ["gpu-80gb"]

    # What the builder sent: each context staged with its modes and without the runtime's tests, buildx pushing
    # with the registry as its layer cache and the parent's digest as BASE, on the platforms each Dockerfile names.
    built = build.saved()
    assert all(entry["tag"].startswith(build.IMAGE_VERSION + "-") for entry in built.values())
    app_staged = staged[("built", "app")]
    assert (app_staged / "run.sh").stat().st_mode & 0o777 == 0o755
    assert (app_staged / "runtime/job.py").read_text() == "print()"
    assert not (app_staged / "runtime/job_test.py").exists() and not (app_staged / "runtime/test_job.py").exists()
    buildx = {pathlib.PurePosixPath(words[-1]).name: words for words in map(shlex.split, commands["built"])
              if words[:3] == ["docker", "buildx", "build"]}
    assert "--push" in buildx["app"] and f"BASE={built['base']['image']}" in buildx["app"]
    assert built["base"]["image"] == f"reg/ns/score-base:{built['base']['tag']}@sha256:base"
    assert "type=registry,ref=reg/ns/score-app:buildcache" in buildx["app"]
    assert any(part.startswith("type=registry,ref=reg/ns/score-app:buildcache,mode=max") for part in buildx["app"])
    platforms = {kind: words[words.index("--platform") + 1] for kind, words in buildx.items()}
    assert platforms == {"base": "linux/amd64,linux/arm64", "app": "linux/amd64", "runner": "linux/amd64"}

    # What the prover sent and kept: the job.json with its inputs uploaded and outputs keyed under the run, the marks
    # in seconds from the container's start, docker set up and run with the NVIDIA toolkit and --gpus on a card
    # machine only, and the numbers in images.json under the kind's proof by card (else by machine type).
    [spec_path] = (tmp_path / "objects/runs").glob("*/app-first-node/job.json")
    run = spec_path.parent.parent.name
    spec = json.loads(spec_path.read_text())
    assert spec["inputs"][0]["path"] == "/root/judge/jobs.json"
    assert spec["outputs"] == [{"path": "/root/judge/out", "key": f"runs/{run}/app-first-node/out/out"}]
    assert spec["kernel_cache"] == "judge-vllm-0.31.0" and spec["models"] == ["qwen3.8-27b-fp8"]
    assert results["app"][0]["jobs"]["first-node"]["marks"] == {"weights_ready": 90.5, "first_result": 300.0}
    runs = {host: next(shlex.split(command) for command in commands[host] if command.startswith("docker run"))
            for host in ("proved-on-a-card", "proved-on-a-processor-under-a-ticket")}
    assert "--gpus" in runs["proved-on-a-card"] and "--gpus" not in runs["proved-on-a-processor-under-a-ticket"]
    assert commands["proved-on-a-card"][0] == warm.GPU_SETUP
    assert commands["proved-on-a-processor-under-a-ticket"][0] == prove.PROCESSOR_SETUP
    assert "nvidia" not in prove.PROCESSOR_SETUP
    prove.save_results(results)
    proofs = {kind: entry["proof"] for kind, entry in build.saved().items() if "proof" in entry}
    assert {kind: {card: numbers["type"] for card, numbers in proof.items()} for kind, proof in proofs.items()} == {
        "app": {CARD: "H100-1-80G"}, "runner": {"POP2-16C-64G": "POP2-16C-64G"}}

    # Built once: each move to the world as built, and what `stale` builds again (the parent first; a child with its
    # new parent; nothing at its tag unless forced). (id, the move to a copy of the world, the move to images.json,
    # the kinds asked, force, the kinds built.)
    every = ["base", "app", "runner"]
    moves = [
        ("nothing moved", None, None, every, False, []),
        ("forced", None, None, every, True, every),
        ("the weights list", lambda folder: (folder / "base/models.json").write_text('[{"name": "x"}]'), None,
         every, False, []),
        ("the runtime's tests", lambda folder: [(folder / "runtime" / name).write_text("print(2)")
                                                for name in ("job_test.py", "test_job.py")], None, every, False, []),
        ("the runtime's code", lambda folder: (folder / "runtime/job.py").write_text("print(1)"), None,
         every, False, every),
        ("a script's mode", lambda folder: (folder / "app/run.sh").chmod(0o644), None, every, False, ["app"]),
        ("the parent's digest", None, lambda entries: entries["base"].update(digest="sha256:b"), every, False,
         ["app", "runner"]),
        ("the parent's tag", None, lambda entries: entries["base"].update(tag="old"), every, False, every),
        ("nothing built", None, lambda entries: entries.clear(), ["app"], False, ["app"]),
        ("the lock exported again", lambda folder: build.export_runner(folder / "repo"), None, every, False, []),
        ("the lock moved", lambda folder: (append_line(folder / "repo/uv.lock"), build.export_runner(folder / "repo")),
         None, every, False, ["runner"]),  # the lock moves; its export does not
    ]
    for name, move_world, move_built, kinds, force, expected in moves:
        folder = tmp_path / "moved" / name.replace(" ", "-").replace("'", "")
        shutil.copytree(here, folder, symlinks=True)
        point_at(monkeypatch, folder)
        entries = json.loads(json.dumps(built))
        if move_world:
            move_world(folder)
        if move_built:
            move_built(entries)
        assert build.stale(kinds, entries, force=force) == expected, name
