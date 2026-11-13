"""Invariant of blender_cloud.py: a Blender job runs on the rented machine (or the cluster) exactly as written: its
arguments reach the script unchanged (its files lie at the same paths up there), the script runs from the machine's
copy of the repo with its folder and tools/blender/inside sent up, Cycles runs on the card on a card machine and on
the cores otherwise; one machine class is fixed for the call at price time; a held machine runs a chain in order and
raises on a failed job; and a rerun of a cut-off run buys only the jobs it lacks (audit, 2026-10-22).

No machine is rented: each test reads the command, job or offers the module builds. The break that turns each red
(applied once, seen red, reverted):

- test_a_job_reaches_the_machine_and_the_cluster_as_written: in `run_line`, `"FARM_CYCLES_GPU=1" if card else
  "FARM_CYCLES_CPU=1"` -> `"FARM_CYCLES_GPU=1"`; or in `script_line`, `str(pathlib.PurePosixPath(repo) /
  job["script"])` -> `job["script"]`; or in `shipped`, `{*ALWAYS_SHIPPED, *(` -> `{*(`; or in `script_line`,
  `if not job.get("env"):` -> `if True:`; or in `shipped`, `("script", "env")` -> `("script",)`; or in
  `cluster_job`, `card = any(provider.cards(name) for name in classes)` -> `card = True`; or in `cluster_line`,
  `if not job.get("env"):` -> `if True:` (a Newton drop run in the blender image, which has no Newton); or in
  `run_on_cluster`, `numbers[index]` -> `index` (a failed drop reported as another job); or in `cluster_kind`,
  `return kind` for every call (settling's drops not their own kind for SCORE_CLOUD_KINDS); or in `cloud_python`,
  `provider.on_cluster()` (the kind dropped).
- test_a_held_machine_runs_a_chain_in_order_and_raises_on_a_failed_job: in `Machine.run`, the `.failed` branch's
  `raise RuntimeError(...)` -> `return`; or in `Machine.__exit__`, `(self.queue / "close").write_text("")` -> `pass`.
- test_a_failed_held_job_raises_with_the_end_of_its_logs: in `serve`, `{log_tail(log_folder, waiting[0].stem)}` ->
  `; log: {log_folder}/job{waiting[0].stem}.log`; or in `log_tail`, `[-LOG_TAIL_LINES:]` -> `[-LOG_TAIL_LINES - 1:]`;
  or in `serve`, drop the `except BaseException` (a job ended by anything but its script's exit leaves no .failed,
  and the fault says only "ended before 1.json ran": settle@hangar, 2026-11-03).
- test_the_runner_python_follows_props_home: `CLOUD_PYTHON = HOME / "env/bin/python"` -> `CLOUD_PYTHON =
  pathlib.Path.home() / ".farm-factory-props/env/bin/python"`.
- test_one_class_is_fixed_at_price_time_and_no_stock_keeps_the_first: in batch.py `one_class_in_stock`, `next(iter(stocked
  + sold), None)` -> `next(iter(sold), None)` (the first class asked though another is in stock).
- test_a_rerun_of_a_cut_off_run_buys_only_the_jobs_it_lacks: in `one_job`, `    kept.keep(job, system(), **keeping)`
  -> `    pass` (`kept.keep(job, system(False), **keeping)`).
- test_a_job_that_brought_none_of_its_outputs_back_failed: in `one_job`, `if
  job.get("outputs") and not came:` -> `if False:`; or in `run_job`, drop `inputs.link_named(log_folder, host,
  job.get("outputs", ()))`.
- test_jobs_side_by_side_on_one_machine_bring_their_outputs_back_one_at_a_time: in `run_job`, drop `with
  BRINGING.setdefault(host, threading.Lock()):` (bring the outputs back unguarded) -> three copies at once.
  Or drop the `bring_while` thread's start in `run_job` -> a job asking `bring_every` brings its outputs back only at
  its end (one copy).
- test_a_job_keeps_only_the_files_its_copy_back_wrote: in `copy_back`, drop `"--out-format=%n"` (no list of what
  the copy wrote).
- test_jobs_this_pc_cannot_run_are_refused_by_name_before_any_starts: in `shared_outputs`, `if
  one.is_relative_to(two) or two.is_relative_to(one)]` -> `if one == two]` (a take's folder inside the row's `made`
  starts); or in `main`, drop the `if shared_outputs(jobs):` refusal; or in `too_big_here`, `for number, job, need
  in over if need > room]` -> `for number, job, need in over if False]` (the big job starts); or in `picture_bytes`,
  `* int.from_bytes(head[20:24], "big") * 4` -> `* 4` (a map counts one row); or `cloud.alone_cap()` ->
  `cloud.memory_cap()` in `too_big_here` (a job past the shared container but within its room alone is refused
  too); or `max(map(predicted_bytes, jobs))` -> `min(...)` in `alone_need` (the claim asks the small job's room);
  or in `alone_need`, `**({"card_gb": max(cards)} if cards else {})` -> `**{}` (a light-passes claim books only the
  bakes' Blender card share; round 45's flat failed to make its CUDA context); or `job.get("script", "")` ->
  `job["script"]` in `alone_need` (a --serve chain's job: KeyError).
"""
import json
import os
import pathlib
import shlex
import struct
import subprocess
import sys
import threading
import zlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_cloud  # noqa: E402
import kept  # noqa: E402
import provider  # noqa: E402


SETTLE = "tools/blender/inside/settle_stage.py"
NEWTON = "score/stages/physics/inside/newton_env.sh"
NEWTON_PYTHON = "/root/lib/envs/newton_env"
# Each job as written, the class it runs on and where it must arrive: the words that end its command on a rented
# machine and on the cluster, the repo folders sent up with it, its cluster image and its SCORE_CLOUD_KINDS kind.
WRITTEN = [
    ("settling on the cores", SETTLE, None, "cpu-32c-128gb",
     ["/w/stage/place.usda", "/w/out/x.json", "--fast", "12"], ["/w/out/x.json"],
     ["--python", f"/root/lib/repo/{SETTLE}", "--", "/w/stage/place.usda", "/w/out/x.json", "--fast", "12"],
     ["--python", SETTLE, "--", "/w/stage/place.usda", "/w/out/x.json", "--fast", "12"],
     ["tools/blender/inside"], "blender", "settle"),
    ("settling on a card", SETTLE, None, "gpu-24gb",
     ["/w/stage.usda", "/w/out/x.json"], ["/w/out/x.json"],
     ["--python", f"/root/lib/repo/{SETTLE}", "--", "/w/stage.usda", "/w/out/x.json"],
     ["--python", SETTLE, "--", "/w/stage.usda", "/w/out/x.json"],
     ["tools/blender/inside"], "blender", "settle"),
    ("a script with its own folder", "tools/props/library/inside/show.py", None, "gpu-48gb",
     ["/w/props/crate.usda"], ["/w/shots/crate.png"],
     ["--python", "/root/lib/repo/tools/props/library/inside/show.py", "--", "/w/props/crate.usda"],
     ["--python", "tools/props/library/inside/show.py", "--", "/w/props/crate.usda"],
     ["tools/blender/inside", "tools/props/library/inside"], "blender", "blender"),
    ("a Newton trial in its env's Python", "score/stages/physics/inside/physics_trial.py", NEWTON, "gpu-24gb",
     ["/w/toy.usda", "/w/sim/out.json"], ["/w/sim/out.json"],
     ["bash", f"/root/lib/repo/{NEWTON}", NEWTON_PYTHON, "&&", f"{NEWTON_PYTHON}/bin/python",
      "/root/lib/repo/score/stages/physics/inside/physics_trial.py", "/w/toy.usda", "/w/sim/out.json"],
     ["&&", "newton-run", "score/stages/physics/inside/physics_trial.py", "/w/toy.usda", "/w/sim/out.json"],
     ["score/stages/physics/inside", "tools/blender/inside"], "newton", "blender"),
    # a script elsewhere in that Python takes the env script's folder up too (settle@garage, 2026-10-28: exit 127)
    ("a settling drop in Newton's Python", "score/stages/settling/inside/settle_drop.py", NEWTON, "cpu-32c-128gb",
     ["/w/stage.usda", "/w/out/x.json"], ["/w/out/x.json"],
     ["bash", f"/root/lib/repo/{NEWTON}", NEWTON_PYTHON, "&&", f"{NEWTON_PYTHON}/bin/python",
      "/root/lib/repo/score/stages/settling/inside/settle_drop.py", "/w/stage.usda", "/w/out/x.json"],
     ["&&", "newton-run", "score/stages/settling/inside/settle_drop.py", "/w/stage.usda", "/w/out/x.json"],
     ["score/stages/physics/inside", "score/stages/settling/inside", "tools/blender/inside"], "newton", "blender"),
]


def test_a_job_reaches_the_machine_and_the_cluster_as_written(monkeypatch):
    """Each WRITTEN job, made by job_of, runs on a rented machine and on the cluster with its arguments unchanged, its
    script from the copy of the repo (Blender's, or its env script's Python), Cycles on the card on card classes and
    on the cores otherwise; settling's drops alone go to the cluster as kind `settle`, in the repo's Python."""
    from paths import VENV_PYTHON
    monkeypatch.setenv("SCORE_CLOUD", "k8s")
    monkeypatch.setenv("SCORE_CLOUD_KINDS", "settle")
    jobs = []
    for name, script, env, machine_class, args, outputs, on_machine, on_cluster, folders, image, kind in WRITTEN:
        job = blender_cloud.job_of(blender_cloud.REPO / script, args, [args[0]], outputs, 4,
                                   env=env and blender_cloud.REPO / env)
        jobs.append(job)
        card = bool(provider.cards(machine_class))
        engine = "FARM_CYCLES_GPU" if card else "FARM_CYCLES_CPU"
        words = shlex.split(blender_cloud.run_line(job, card))
        assert words[-len(on_machine):] == on_machine, (name, words)
        assert f"{engine}=1" in words and len({"FARM_CYCLES_GPU=1", "FARM_CYCLES_CPU=1"} & set(words)) == 1, name
        assert ("/root/blender/blender" in words) == (env is None), (name, words)
        assert blender_cloud.shipped([job]) == folders, name
        sent = blender_cloud.cluster_job(job, [machine_class])
        words = shlex.split(sent["command"][2])
        assert words[:3] == ["mkdir", "-p", str(pathlib.Path(outputs[0]).parent)], (name, words)
        assert words[-len(on_cluster):] == on_cluster and (env is None or words[3:] == on_cluster), (name, words)
        assert (sent["code"], sent["inputs"], sent["outputs"], sent["minutes"]) == (folders, [args[0]], outputs, 4)
        assert sent["env"] == {engine: "1"}, name
        assert sent.get("kernel_cache") == ("blender-5.0.1" if card and env is None else None), name
        assert blender_cloud.cluster_image(job) == image, name
        assert blender_cloud.cluster_kind([job]) == kind, name
        assert blender_cloud.cloud_python(kind) == (VENV_PYTHON if kind == "settle" else blender_cloud.CLOUD_PYTHON)
    assert blender_cloud.cluster_kind(jobs) == "blender"  # with other Blender jobs, settling's are blender's
    images = [row[9] for row in WRITTEN]
    sent, failing = [], {"newton": [0], "blender": []}
    monkeypatch.setattr(blender_cloud, "cluster_jobs_module", lambda: type("Jobs", (), {"run": staticmethod(
        lambda kind, jobs, who, classes, image: sent.append((image, len(jobs))) or failing[image])}))
    assert blender_cloud.run_on_cluster(jobs, ["gpu-24gb"], "test") == [images.index("newton")]  # its own number
    assert sorted(sent) == [("blender", images.count("blender")), ("newton", images.count("newton"))]


class Answering:
    """A stand-in for the --serve process: it answers each job file in the queue as told, without renting."""

    def __init__(self, queue, answer):
        self.queue, self.answer, self.stop = queue, answer, threading.Event()
        threading.Thread(target=self.watch, daemon=True).start()

    def watch(self):
        while not self.stop.wait(0.05):
            for job in self.queue.glob("*.json"):
                if not job.with_suffix(".done").exists() and not job.with_suffix(".failed").exists():
                    job.with_suffix(f".{self.answer}").write_text("answered")

    def poll(self):
        return None

    def wait(self):
        self.stop.set()


def held(queue, answer, monkeypatch):
    """A Machine whose --serve process is an Answering stand-in on `queue`."""
    monkeypatch.setattr(blender_cloud.time, "sleep", lambda seconds: threading.Event().wait(0.02))
    machine = blender_cloud.Machine(["cpu-32c-128gb"], "test")
    machine.queue = queue
    queue.mkdir()
    machine.process = Answering(queue, answer)
    return machine


def test_a_held_machine_runs_a_chain_in_order_and_raises_on_a_failed_job(tmp_path, monkeypatch):
    script = blender_cloud.REPO / "tools/blender/inside/usd_views.py"
    done = held(tmp_path / "done", "done", monkeypatch)
    done.run(script, ["a"], [], [])
    done.run(script, ["b"], [], [])
    done.__exit__(None, None, None)
    assert sorted(path.name for path in done.queue.glob("*.json")) == ["1.json", "2.json"]
    assert (done.queue / "close").exists()
    failed = held(tmp_path / "failed", "failed", monkeypatch)
    try:
        failed.run(script, ["a"], [], [])
        raise AssertionError("a failed job did not raise")
    except RuntimeError as error:
        assert "failed" in str(error)
    failed.__exit__(None, None, None)
    assert (failed.queue / "close").exists()


def test_a_failed_held_job_raises_with_the_end_of_its_logs(tmp_path, monkeypatch):
    """settle@airlock (2026-10-29): the drop failed on this PC's container and the fault report named only its job
    log, whose folder was gone by then. The error carries the end of the job's log and the set-up log."""
    import contextlib
    import types
    queue, logs = tmp_path / "queue", tmp_path / "logs"
    queue.mkdir()
    logs.mkdir()
    (logs / "setup.log").write_text("blender ready\n")
    (queue / "1.json").write_text('{"script": "score/stages/settling/inside/settle_drop.py"}')
    (queue / "close").write_text("")

    def failing(log_folder, host, number, job, card):
        (log_folder / f"job{number}.log").write_text("".join(f"line {index}\n" for index in range(60))
                                                     + "RuntimeError: the drop met 832 contacts\n")
        raise subprocess.CalledProcessError(1, "ssh")
    monkeypatch.setattr(blender_cloud.spread, "tended", lambda run, machine: contextlib.nullcontext("host"))
    monkeypatch.setattr(blender_cloud, "set_up", lambda *args: None)
    monkeypatch.setattr(blender_cloud, "ship", lambda *args: None)
    monkeypatch.setattr(blender_cloud, "run_job", failing)
    blender_cloud.serve(types.SimpleNamespace(deadline=float("inf")), {"folder": logs}, queue, 1)
    failed = held(tmp_path / "held", "failed", monkeypatch)
    (tmp_path / "held/1.failed").write_text((queue / "1.failed").read_text())
    with pytest.raises(RuntimeError) as error:
        failed.run(blender_cloud.REPO / "tools/blender/inside/usd_views.py", [], [], [])
    failed.__exit__(None, None, None)
    said = str(error.value)
    assert "blender ready" in said and said.endswith("RuntimeError: the drop met 832 contacts"), said
    assert "line 21" in said and "line 20\n" not in said  # the job log's last 40 lines, no more
    # a job ended by anything else (an error past its script, a stop signal) still leaves its .failed with its logs
    (queue / "1.failed").unlink()

    def stopped(log_folder, host, number, job, card):
        (log_folder / f"job{number}.log").write_text("Blender: settling\n")
        raise SystemExit("stopped by signal 15")
    monkeypatch.setattr(blender_cloud, "run_job", stopped)
    with pytest.raises(SystemExit):
        blender_cloud.serve(types.SimpleNamespace(deadline=float("inf")), {"folder": logs}, queue, 1)
    kept = (queue / "1.failed").read_text()
    assert kept.startswith("the job ended: SystemExit: stopped by signal 15") and "Blender: settling" in kept, kept


def runner_python_under(props_home):
    """CLOUD_PYTHON as a fresh import sees it with PROPS_HOME set to `props_home` (None: unset)."""
    environment = {key: value for key, value in os.environ.items() if key != "PROPS_HOME"}
    if props_home is not None:
        environment["PROPS_HOME"] = str(props_home)
    return subprocess.run([sys.executable, "-c", "import blender_cloud; print(blender_cloud.CLOUD_PYTHON)"],
                          cwd=pathlib.Path(__file__).resolve().parent, env=environment, capture_output=True,
                          text=True, check=True).stdout.strip()


def test_the_runner_python_follows_props_home(tmp_path):
    assert runner_python_under(tmp_path) == f"{tmp_path}/env/bin/python"
    assert runner_python_under(None) == str(pathlib.Path.home() / ".farm-factory-props/env/bin/python")


def test_one_class_is_fixed_at_price_time_and_no_stock_keeps_the_first(monkeypatch):
    """A call runs every job on the class fixed before it (CONTEXT.md, owner 2026-10-20): with cards short a 32-core
    machine was rented instead and claims moved between classes as stock moved. No stock keeps the first class
    asked, its claims waiting: no stock never makes a gap (owner, 2026-10-23)."""
    stock = {"cpu-32c-128gb": "available"}
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)  # no warm pool
    monkeypatch.setattr(blender_cloud.batch, "offers", lambda classes: [
        provider.Offer(0.01, 0, f"{name}-type", "zone-a", 0.01, name, 0, stock.get(name, "shortage"))
        for name in classes])
    monkeypatch.setattr(blender_cloud.batch, "month_spent", lambda account: 0.0)
    monkeypatch.setattr(blender_cloud.batch, "say", lambda line: None)
    cards = ["gpu-24gb", "gpu-48gb", "gpu-80gb"]
    found, _, _ = blender_cloud.price([{"minutes": 5}], "account", cards)
    assert [offer.machine_class for offer in found] == ["gpu-24gb"]
    stock.update({"gpu-48gb": "available", "gpu-80gb": "available"})
    found, _, _ = blender_cloud.price([{"minutes": 5}], "account", cards)
    assert [offer.machine_class for offer in found] == ["gpu-48gb"]


def test_a_rerun_of_a_cut_off_run_buys_only_the_jobs_it_lacks(tmp_path, monkeypatch):
    """Audit (2026-10-22): kept.py was never called here, so a cut-off run paid again for every finished job."""
    making = tmp_path / "making"
    making.mkdir()
    jobs = [{"script": "tools/blender/inside/usd_views.py", "args": [str(number)], "inputs": [],
             "outputs": [str(making / f"shot{number}.png")], "minutes": 1} for number in range(2)]
    monkeypatch.setenv(kept.CODE, "turntable row code")
    monkeypatch.setattr(blender_cloud, "system", lambda cluster=None: "this test's machine")
    monkeypatch.setenv(kept.STORE, str(tmp_path / "store"))
    monkeypatch.setenv(kept.MAKING, str(making))
    monkeypatch.setattr(blender_cloud.batch, "say", lambda line: None)

    def run_job(log_folder, host, number, job, card):
        pathlib.Path(job["outputs"][0]).write_text(f"shot {number}")
        return 1.0, 1, {"brought": None}
    monkeypatch.setattr(blender_cloud, "run_job", run_job)
    blender_cloud.one_job({"folder": tmp_path, "host": "host"}, (0, jobs[0]), None)  # cut off before job 1
    (making / "shot0.png").unlink()  # the next attempt's folder starts empty
    assert blender_cloud.still_to_run(jobs) == [jobs[1]]
    assert (making / "shot0.png").read_text() == "shot 0"


def test_a_job_that_brought_none_of_its_outputs_back_failed(tmp_path, monkeypatch):
    """surfaces-bake@campgrounds (2026-10-27): twelve paint and bake jobs ended well, wrote their outputs through a
    path the machine did not link as this side does, and counted done with nothing back; the row raised for all."""
    import spread
    making = tmp_path / "making"
    making.mkdir()
    job = {"script": "score/stages/surfaces/inside/paint_bake.py", "args": [], "inputs": [],
           "outputs": [str(making / "labelled" / "crate"), str(making / "made")], "minutes": 1}
    monkeypatch.setenv(kept.CODE, "surfaces-bake row code")
    monkeypatch.setattr(blender_cloud, "system", lambda cluster=None: "this test's machine")
    monkeypatch.setenv(kept.STORE, str(tmp_path / "store"))
    monkeypatch.setenv(kept.MAKING, str(making))
    said, linked = [], []
    monkeypatch.setattr(blender_cloud.batch, "say", said.append)
    monkeypatch.setattr(blender_cloud.batch, "remote", lambda *args, **keywords: None)
    monkeypatch.setattr(blender_cloud, "send_inputs", lambda *args: None)
    monkeypatch.setattr(blender_cloud.inputs, "link_named", lambda folder, host, paths: linked.extend(paths))

    def nothing_back(folder, source, destination):
        raise subprocess.CalledProcessError(23, "rsync")
    monkeypatch.setattr(blender_cloud, "copy_back", nothing_back)
    with pytest.raises(spread.JobFailed, match="none of its outputs came back"):
        blender_cloud.one_job({"folder": tmp_path, "host": "host"}, (3, job), None)
    assert linked == job["outputs"], linked  # its outputs reached through the links its paths are named through
    assert blender_cloud.kept.missing([job], "this test's machine") == [job]  # nothing kept as done


def test_jobs_side_by_side_on_one_machine_bring_their_outputs_back_one_at_a_time(tmp_path, monkeypatch):
    """This PC runs a bake row's takes side by side (backends/local.py RUNS_AT_ONCE), all bringing back the row's one
    `made` folder: a copy into it while another job's copy reads it would keep a file caught mid-write."""
    import time
    monkeypatch.setattr(blender_cloud.batch, "say", lambda line: None)
    monkeypatch.setattr(blender_cloud.batch, "remote", lambda *args, **keywords: None)
    monkeypatch.setattr(blender_cloud, "send_inputs", lambda *args: None)
    monkeypatch.setattr(blender_cloud.inputs, "link_named", lambda *args: None)
    bringing, most, guard = [0], [0], threading.Lock()

    def bring_back(log_folder, host, local):
        with guard:
            bringing[0] += 1
            most[0] = max(most[0], bringing[0])
        time.sleep(0.05)
        with guard:
            bringing[0] -= 1
        return set()
    monkeypatch.setattr(blender_cloud, "bring_back", bring_back)
    monkeypatch.setattr(blender_cloud, "system", lambda cluster=None: "this test's machine")
    job = {"script": "score/stages/surfaces/inside/paint_bake.py", "args": [], "inputs": [],
           "outputs": [str(tmp_path / "made")], "minutes": 1}
    slots = [threading.Thread(target=blender_cloud.run_job, args=(tmp_path, "this-pc", number, job, True))
             for number in range(3)]
    for slot in slots:
        slot.start()
    for slot in slots:
        slot.join()
    assert most[0] == 1
    calls = []  # a long job that asks brings its outputs back while it runs, not only at its end
    monkeypatch.setattr(blender_cloud, "bring_back", lambda log_folder, host, local: calls.append(time.time()))
    monkeypatch.setattr(blender_cloud.batch, "remote", lambda *args, **keywords: time.sleep(0.5))
    blender_cloud.run_job(tmp_path, "cloud", 9, {**job, "bring_every": 0.002}, True)
    assert len(calls) >= 3  # every 0.12 s of its 0.5 s run, then at its end


def test_a_job_keeps_only_the_files_its_copy_back_wrote(tmp_path, monkeypatch):
    """env1 (2026-10-29): a take's kept copy of a whole output folder held what else lay there; it keeps only what its
    own copy back wrote."""
    making = tmp_path / "making"
    (making / "made").mkdir(parents=True)
    monkeypatch.setenv(kept.MAKING, str(making))
    monkeypatch.setenv(kept.CODE, "surfaces-bake row code")
    monkeypatch.setenv(kept.STORE, str(tmp_path / "store"))
    monkeypatch.setattr(blender_cloud, "system", lambda cluster=None: "this test's machine")
    for name in ("say", "remote"):
        monkeypatch.setattr(blender_cloud.batch, name, lambda *args, **keywords: None)
    monkeypatch.setattr(blender_cloud, "send_inputs", lambda *args: None)
    monkeypatch.setattr(blender_cloud.inputs, "link_named", lambda *args: None)

    def take(name):
        return {"script": "score/stages/surfaces/inside/paint_bake.py", "args": [name], "inputs": [],
                "outputs": [str(making / "labelled" / name), str(making / "made")], "minutes": 1}
    crate = take("crate")

    def rsync(command, **keywords):
        said = "made/\nmade/crate.gltf\n" if command[-2].endswith("/made") else "crate/\ncrate/labels.json\n"
        return subprocess.CompletedProcess(command, 0, said if "--out-format=%n" in command else "", "")
    monkeypatch.setattr(blender_cloud.subprocess, "run", rsync)
    _, came, keeping = blender_cloud.run_job(tmp_path, "this-pc", 0, crate, True)
    assert came == 2
    assert keeping == {"brought": {making / "made" / "crate.gltf", making / "labelled" / "crate" / "labels.json"}}


def a_png(path, width, height):
    """A PNG at `path` whose header says width x height (an empty IDAT: nothing to decode, which nothing does)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", b"") + chunk(b"IEND", b""))


class Priced(Exception):
    """The call got past every refusal to pricing (this PC's account())."""


def bake(name, made):
    return {"script": "score/stages/surfaces/inside/paint_bake.py", "args": [name], "inputs": [],
            "outputs": [f"{{root}}/labelled/{name}", made], "minutes": 1}


LIGHT = {"script": "score/stages/light/inside/light_passes.py", "args": ["/a", "/s"], "inputs": ["{root}/tree/garage"],
         "outputs": ["{root}/o2"], "minutes": 4}
BIG_LIGHT = {**LIGHT, "args": ["/a", "/b"], "inputs": ["{root}/tree/base", "{root}/tree/garage"], "outputs": ["{root}/o"]}
BASE = 2 * 10**9
LAMP = 1024 * 1024 * 4  # the 1k map decoded
MAPS = 4 * 16384 * 8192 * 4  # four 16k by 8k maps decoded: 2.147 GB


@pytest.mark.parametrize("jobs, refused, kept_read, heaviest, card_gb, mark", [
    pytest.param([bake("crate", "{root}/made"), bake("barrel", "{root}/made/barrel")],
                 "Blender jobs 0 and 1 both write into {root}/made: each job brings back into an output of its own",
                 False, BASE, None, "e8bbe6423a622988", id="two takes writing into one made folder"),
    pytest.param([bake("crate", "{root}/.bake-crate-made"), bake("barrel", "{root}/.bake-barrel-made")],
                 None, True, BASE, None, "e8bbe6423a622988", id="each take bringing back into its own"),
    pytest.param([LIGHT, BIG_LIGHT],
                 "Blender job 1 (score/stages/light/inside/light_passes.py) is predicted to need 4.2 GB (5 input "
                 "pictures decoded, plus 2 GB) and this PC's machine has 3.2 GB with the job alone: not started; it "
                 "needs a bigger machine, a priced ask",
                 True, BASE + MAPS + LAMP, 13.0, "148c32fbefbb40c1", id="a light job past this PC's machine alone"),
    pytest.param([LIGHT], None, True, BASE + LAMP, 13.0, "8ede7e0dba1610b1",
                 id="a light job past the shared container but within its room alone"),
    # a held machine's chain (--serve) names no script until its jobs come: its need is the base alone, never the
    # KeyError that ended the serve before 1.json ran (2026-11-10: settle@garage and sim-body@base)
    pytest.param([{"minutes": 30}], None, True, BASE, None, None, id="a held chain naming no script yet"),
])
def test_jobs_this_pc_cannot_run_are_refused_by_name_before_any_starts(jobs, refused, kept_read, heaviest, card_gb,
                                                                        mark, tmp_path, monkeypatch):
    """Round 23: base's light passes (271 full-size maps, 27.3 GB decoded) filled this PC's container in 35 s; #36
    (2026-10-30): a bake row's takes all brought back into one `made` folder, so each kept take named the others as
    peers and was baked again whenever one of them was. On this PC (a machine of 3 GiB alone, 1 GiB shared) a call
    whose jobs write into one output (the same folder, or one inside another) stops naming both before any kept job
    is put back; one whose job is predicted (2 GB plus its input pictures decoded) past the machine with the job alone
    stops naming that job, its GB and a bigger machine, before it prices or claims anything (round 31: base's light
    passes were refused by the shared container though a job alone had room). The rest reach pricing, their claim
    asking the most one job is predicted to take in GiB and the card its script measured; each take's mark carries
    its prediction and whether every output came back, keyed as score/graph take_key keys the take's command line."""
    for name in ("wall.png", "floor.PNG", "roof.png", "door.png"):
        a_png(tmp_path / "tree" / "base" / "assets" / "textures" / name, 16384, 8192)
    a_png(tmp_path / "tree" / "garage" / "assets" / "textures" / "lamp.png", 1024, 1024)
    (tmp_path / "tree" / "base" / "base.usda").write_text("#usda 1.0\n")
    jobs = json.loads(json.dumps(jobs).replace("{root}", str(tmp_path)))
    paths = []
    for number, job in enumerate(jobs):
        paths.append(tmp_path / f"job-{number}.json")
        paths[-1].write_text(json.dumps(job))

    def priced():
        raise Priced()
    machine = type("ThisPC", (), {"NAME": "local", "memory_cap": staticmethod(lambda: "1g"),
                                  "alone_cap": staticmethod(lambda: "3g"), "account": staticmethod(priced)})
    monkeypatch.setattr(blender_cloud, "cloud", machine)
    monkeypatch.delenv("SCORE_CLOUD", raising=False)
    read = []
    monkeypatch.setattr(blender_cloud, "still_to_run", lambda jobs, cluster=None: read.append(jobs) or jobs)
    monkeypatch.setattr(blender_cloud, "TAKE_MARKS", tmp_path / "marks")
    monkeypatch.setattr(sys, "argv", ["blender_cloud.py", *map(str, paths), "--who", "a test"])
    with pytest.raises(SystemExit if refused else Priced) as ended:
        blender_cloud.main()
    assert (str(ended.value) if refused else None) == (refused and refused.replace("{root}", str(tmp_path)))
    assert bool(read) == kept_read, read
    assert blender_cloud.alone_need(jobs) == {"memory_gb": heaviest / 2**30, **({"card_gb": card_gb} if card_gb else {})}
    if mark:  # a held chain's job names no script to mark
        blender_cloud.mark_take(jobs[-1], wrote=True)
        assert json.loads((tmp_path / "marks" / f"{mark}.json").read_text()) == {
            "kind": pathlib.PurePosixPath(jobs[-1]["script"]).name, "predicted": heaviest, "wrote": True}
