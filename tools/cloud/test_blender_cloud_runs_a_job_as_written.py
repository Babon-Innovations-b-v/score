"""Invariant of blender_cloud.py: a Blender job runs on the rented machine (or the cluster) exactly as written: its
arguments reach the script unchanged (its files lie at the same paths up there), the script runs from the machine's
copy of the repo with its folder and tools/blender/inside sent up, Cycles runs on the card on a card machine and on
the cores otherwise; one machine class is fixed for the call at price time; a held machine runs a chain in order and
raises on a failed job; and a rerun of a cut-off run buys only the jobs it lacks (audit, 2026-10-22).

No machine is rented: each test reads the command, job or offers the module builds. The break that turns each red
(applied once, seen red, reverted):

- test_the_arguments_and_script_reach_the_machine_as_written: in `run_line`, `"FARM_CYCLES_GPU=1" if card else
  "FARM_CYCLES_CPU=1"` -> `"FARM_CYCLES_GPU=1"`; or `str(REMOTE / "repo" / job["script"])` -> `job["script"]`.
- test_a_scripts_folder_and_the_blender_helpers_go_up: in `shipped`, `{*ALWAYS_SHIPPED, *(` -> `{*(`.
- test_a_job_naming_an_env_runs_in_that_python_not_blender: in `script_line`, `if not job.get("env"):` -> `if True:`;
  or in `shipped`, `("script", "env")` -> `("script",)`.
- test_a_held_machine_runs_a_chain_in_order_and_raises_on_a_failed_job: in `Machine.run`, the `.failed` branch's
  `raise RuntimeError(...)` -> `return`; or in `Machine.__exit__`, `(self.queue / "close").write_text("")` -> `pass`.
- test_a_failed_held_job_raises_with_the_end_of_its_logs: in `serve`, `{log_tail(log_folder, waiting[0].stem)}` ->
  `; log: {log_folder}/job{waiting[0].stem}.log`; or in `log_tail`, `[-LOG_TAIL_LINES:]` -> `[-LOG_TAIL_LINES - 1:]`.
- test_a_cluster_job_keeps_the_paths_and_the_engine_follows_the_class: in `cluster_job`, `card = any(provider.cards(name)
  for name in classes)` -> `card = True`.
- test_the_runner_python_follows_props_home: `CLOUD_PYTHON = HOME / "env/bin/python"` -> `CLOUD_PYTHON =
  pathlib.Path.home() / ".farm-factory-props/env/bin/python"`.
- test_one_class_is_fixed_at_price_time_and_no_stock_keeps_the_first: in batch.py `one_class_in_stock`, `next(iter(stocked
  + sold), None)` -> `next(iter(sold), None)` (the first class asked though another is in stock).
- test_a_rerun_of_a_cut_off_run_buys_only_the_jobs_it_lacks: in `one_job`, `    kept.keep(job, system(), **keeping)`
  -> `    pass`.
- test_a_job_that_brought_none_of_its_outputs_back_failed: in `one_job`, `if
  job.get("outputs") and not came:` -> `if False:`; or in `run_job`, drop `inputs.link_named(log_folder, host,
  job.get("outputs", ()))`.
- test_jobs_side_by_side_on_one_machine_bring_their_outputs_back_one_at_a_time: in `run_job`, drop `with
  BRINGING.setdefault(host, threading.Lock()):` (bring the outputs back unguarded) -> three copies at once.
- test_a_job_keeps_only_the_files_its_copy_back_wrote_and_names_the_jobs_beside_it: in `copy_back`, drop
  `"--out-format=%n"` (no list of what the copy wrote); or in `run_job`, `others = list(running.values())` ->
  `others = []` (no peers named).
"""
import os
import pathlib
import shlex
import subprocess
import sys
import threading

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_cloud  # noqa: E402
import kept  # noqa: E402
import provider  # noqa: E402


def test_the_arguments_and_script_reach_the_machine_as_written(tmp_path):
    job = {"script": "tools/blender/inside/settle_stage.py", "inputs": [str(tmp_path / "stage")],
           "outputs": [str(tmp_path / "out.json")],
           "args": [str(tmp_path / "stage/place.usda"), str(tmp_path / "out.json"), "--fast", "12"]}
    processor = shlex.split(blender_cloud.run_line(job, card=False))
    assert processor[processor.index("--") + 1:] == [f"{tmp_path}/stage/place.usda", f"{tmp_path}/out.json",
                                                     "--fast", "12"]
    assert processor[processor.index("--python") + 1] == "/root/lib/repo/tools/blender/inside/settle_stage.py"
    assert "FARM_CYCLES_CPU=1" in processor and "FARM_CYCLES_GPU=1" not in processor
    on_card = shlex.split(blender_cloud.run_line(job, card=True))
    assert "FARM_CYCLES_GPU=1" in on_card and "FARM_CYCLES_CPU=1" not in on_card


def test_a_scripts_folder_and_the_blender_helpers_go_up():
    found = blender_cloud.shipped([{"script": "tools/props/library/inside/show.py"}])
    assert found == ["tools/blender/inside", "tools/props/library/inside"]


def test_a_job_naming_an_env_runs_in_that_python_not_blender(tmp_path):
    job = blender_cloud.job_of(blender_cloud.REPO / "score/stages/physics/inside/physics_trial.py",
                               [tmp_path / "toy.usda", tmp_path / "out.json"], [], [tmp_path / "out.json"], 5,
                               env=blender_cloud.REPO / "score/stages/physics/inside/newton_env.sh")
    line = blender_cloud.run_line(job, card=True)
    assert "blender" not in line and "FARM_CYCLES_GPU=1" in line
    folder = "/root/lib/envs/newton_env"
    assert line.endswith(f"bash /root/lib/repo/score/stages/physics/inside/newton_env.sh {folder} && {folder}/bin/python "
                         f"/root/lib/repo/score/stages/physics/inside/physics_trial.py {tmp_path}/toy.usda "
                         f"{tmp_path}/out.json"), line
    assert blender_cloud.shipped([job]) == ["score/stages/physics/inside", "tools/blender/inside"]
    # a script elsewhere in that Python takes the env script's folder up too (settle@garage, 2026-10-28: exit 127)
    drop = blender_cloud.job_of(blender_cloud.REPO / "score/stages/settling/inside/settle_drop.py", [], [], [], 5,
                                env=blender_cloud.REPO / "score/stages/physics/inside/newton_env.sh")
    assert blender_cloud.shipped([drop]) == ["score/stages/physics/inside", "score/stages/settling/inside",
                                             "tools/blender/inside"]


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


def test_a_cluster_job_keeps_the_paths_and_the_engine_follows_the_class():
    """Under SCORE_CLOUD=k8s: the same arguments, the script from the job's code, its output folders made first."""
    job = {"script": "tools/blender/inside/settle_stage.py", "args": ["/w/stage.usda", "/w/out/x.json"],
           "inputs": ["/w/stage.usda"], "outputs": ["/w/out/x.json"], "minutes": 4}
    card = blender_cloud.cluster_job(job, ["gpu-24gb"])
    words = shlex.split(card["command"][2])
    assert words[:3] == ["mkdir", "-p", "/w/out"] and words[words.index("--") + 1:] == ["/w/stage.usda",
                                                                                         "/w/out/x.json"]
    assert words[words.index("--python") + 1] == "tools/blender/inside/settle_stage.py"
    assert card["code"] == ["tools/blender/inside"]
    assert card["env"] == {"FARM_CYCLES_GPU": "1"} and card["kernel_cache"] == "blender-5.0.1"
    processor = blender_cloud.cluster_job(job, ["cpu-32c-128gb"])
    assert processor["env"] == {"FARM_CYCLES_CPU": "1"} and "kernel_cache" not in processor
    assert (card["inputs"], card["outputs"], card["minutes"]) == (job["inputs"], job["outputs"], 4)


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
    monkeypatch.setattr(blender_cloud, "system", lambda: "this test's machine")
    monkeypatch.setenv(kept.STORE, str(tmp_path / "store"))
    monkeypatch.setenv(kept.MAKING, str(making))
    monkeypatch.setattr(blender_cloud.batch, "say", lambda line: None)

    def run_job(log_folder, host, number, job, card):
        pathlib.Path(job["outputs"][0]).write_text(f"shot {number}")
        return 1.0, 1, {"brought": None, "peers": {}}
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
    monkeypatch.setattr(blender_cloud, "system", lambda: "this test's machine")
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
    monkeypatch.setattr(blender_cloud, "system", lambda: "this test's machine")
    job = {"script": "score/stages/surfaces/inside/paint_bake.py", "args": [], "inputs": [],
           "outputs": [str(tmp_path / "made")], "minutes": 1}
    slots = [threading.Thread(target=blender_cloud.run_job, args=(tmp_path, "this-pc", number, job, True))
             for number in range(3)]
    for slot in slots:
        slot.start()
    for slot in slots:
        slot.join()
    assert most[0] == 1


def test_a_job_keeps_only_the_files_its_copy_back_wrote_and_names_the_jobs_beside_it(tmp_path, monkeypatch):
    """env1 (2026-10-29): a bake row's takes share one `made` folder, so a take's kept copy of all of it held the
    other takes' models; it keeps only what its own copy back wrote, and names the takes still running beside it,
    whose files that copy may carry (kept.py's peers)."""
    making = tmp_path / "making"
    (making / "made").mkdir(parents=True)
    monkeypatch.setenv(kept.MAKING, str(making))
    monkeypatch.setenv(kept.CODE, "surfaces-bake row code")
    monkeypatch.setenv(kept.STORE, str(tmp_path / "store"))
    monkeypatch.setattr(blender_cloud, "system", lambda: "this test's machine")
    for name in ("say", "remote"):
        monkeypatch.setattr(blender_cloud.batch, name, lambda *args, **keywords: None)
    monkeypatch.setattr(blender_cloud, "send_inputs", lambda *args: None)
    monkeypatch.setattr(blender_cloud.inputs, "link_named", lambda *args: None)

    def take(name):
        return {"script": "score/stages/surfaces/inside/paint_bake.py", "args": [name], "inputs": [],
                "outputs": [str(making / "labelled" / name), str(making / "made")], "minutes": 1}
    crate, barrel = take("crate"), take("barrel")

    def rsync(command, **keywords):
        said = "made/\nmade/crate.gltf\n" if command[-2].endswith("/made") else "crate/\ncrate/labels.json\n"
        return subprocess.CompletedProcess(command, 0, said if "--out-format=%n" in command else "", "")
    monkeypatch.setattr(blender_cloud.subprocess, "run", rsync)
    monkeypatch.setitem(blender_cloud.ACTIVE, "this-pc", {"the barrel's turn": barrel})  # running beside it
    _, came, keeping = blender_cloud.run_job(tmp_path, "this-pc", 0, crate, True)
    assert came == 2
    assert keeping["brought"] == {making / "made" / "crate.gltf", making / "labelled" / "crate" / "labels.json"}
    assert keeping["peers"] == dict([kept.identity(barrel, "this test's machine")])
    assert blender_cloud.ACTIVE["this-pc"] == {"the barrel's turn": barrel}  # the crate's turn is over
