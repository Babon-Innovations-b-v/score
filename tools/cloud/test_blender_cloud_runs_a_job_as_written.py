"""Invariant of blender_cloud.py: a Blender job runs on the rented machine (or the cluster) exactly as written: its
arguments reach the script unchanged (its files lie at the same paths up there), the script runs from the machine's
copy of the repo with its folder and tools/blender/inside sent up, Cycles runs on the card on a card machine and on
the cores otherwise; one machine class is fixed for the call at price time; a held machine runs a chain in order and
raises on a failed job with the end of its logs; a job counts done only by the outputs its own copy back brought, one
copy back at a time on a machine; a rerun of a cut-off run buys only the jobs it lacks (audit, 2026-10-22); and a call
this PC cannot run is refused by name before any job starts.

No machine is rented. One test asks it of three worlds: the jobs as WRITTEN (the commands and cluster jobs the module
builds from them), the calls of CALLS through `main` up to pricing, and one machine side (this test's Transport: ssh
commands and rsync copies answered here) that one spread run's jobs, three takes side by side, a job that brings back
while it runs and a held machine's chain (`Machine` on a `serve` of its queue) all run on. The break that turns it red
(each applied once, seen red, reverted):

- in `run_line`, `"FARM_CYCLES_GPU=1" if card else "FARM_CYCLES_CPU=1"` -> `"FARM_CYCLES_GPU=1"`; or in
  `script_line`, `str(pathlib.PurePosixPath(repo) / job["script"])` -> `job["script"]`; or in `shipped`,
  `{*ALWAYS_SHIPPED, *(` -> `{*(`; or in `script_line`, `if not job.get("env"):` -> `if True:`; or in `shipped`,
  `("script", "env")` -> `("script",)`; or in `cluster_job`, `card = any(provider.cards(name) for name in classes)`
  -> `card = True`; or in `cluster_line`, `if not job.get("env"):` -> `if True:` (a Newton drop run in the blender
  image, which has no Newton); or in `run_on_cluster`, `numbers[index]` -> `index` (a failed drop reported as another
  job); or in `cluster_kind`, `return kind` for every call (settling's drops not their own kind for
  SCORE_CLOUD_KINDS); or in `cloud_python`, `provider.on_cluster()` (the kind dropped).
- `CLOUD_PYTHON = HOME / "env/bin/python"` -> `CLOUD_PYTHON = pathlib.Path.home() /
  ".farm-factory-props/env/bin/python"` (the runner Python no longer follows PROPS_HOME).
- in `Machine.run`, the `.failed` branch's `raise RuntimeError(...)` -> `return`; or in `Machine.__exit__`,
  `(self.queue / "close").write_text("")` -> `pass`.
- in `serve`, `{log_tail(log_folder, waiting[0].stem)}` -> `; log: {log_folder}/job{waiting[0].stem}.log`; or in
  `log_tail`, `[-LOG_TAIL_LINES:]` -> `[-LOG_TAIL_LINES - 1:]`; or in `serve`, drop the `except BaseException` (a job
  ended by anything but its script's exit leaves no .failed, and the fault says only "ended before 4.json ran":
  settle@hangar, 2026-11-03).
- in batch.py `one_class_in_stock`, `next(iter(stocked + sold), None)` -> `next(iter(sold), None)` (the first class
  asked though another is in stock).
- in `one_job`, `    kept.keep(job, system(), **keeping)` -> `    pass` (`kept.keep(job, system(False),
  **keeping)`): the rerun buys the cut-off run's finished shot again.
- in `one_job`, `if job.get("outputs") and not came:` -> `if False:`; or in `run_job`, drop
  `inputs.link_named(log_folder, host, job.get("outputs", ()))` (a take that brought nothing back counts done).
- in `run_job`, drop `with BRINGING.setdefault(host, threading.Lock()):` (bring the outputs back unguarded) -> three
  copies at once. Or drop the `bring_while` thread's start in `run_job` -> a job asking `bring_every` brings its
  outputs back only at its end (one copy).
- in `copy_back`, drop `"--out-format=%n"` (no list of what the copy wrote: a take keeps nothing, or another take's
  file in its `made` folder).
- in `shared_outputs`, `if one.is_relative_to(two) or two.is_relative_to(one)]` -> `if one == two]` (a take's folder
  inside the row's `made` starts); or in `main`, drop the `if shared_outputs(jobs):` refusal; or in `too_big_here`,
  `for number, job, need in over if need > room]` -> `for number, job, need in over if False]` (the big job starts);
  or in `picture_bytes`, `* int.from_bytes(head[20:24], "big") * 4` -> `* 4` (a map counts one row); or
  `cloud.alone_cap()` -> `cloud.memory_cap()` in `too_big_here` (a job past the shared container but within its room
  alone is refused too); or `max(map(predicted_bytes, jobs))` -> `min(...)` in `alone_need` (the claim asks the small
  job's room); or in `alone_need`, `**({"card_gb": max(cards)} if cards else {})` -> `**{}` (a light-passes claim
  books only the bakes' Blender card share; round 45's flat failed to make its CUDA context); or
  `job.get("script", "")` -> `job["script"]` in `alone_need` (a --serve chain's job: KeyError).
"""
import contextlib
import json
import os
import pathlib
import shlex
import struct
import subprocess
import sys
import threading
import time
import types
import zlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import blender_cloud  # noqa: E402
import kept  # noqa: E402
import provider  # noqa: E402


SETTLE = "tools/blender/inside/settle_stage.py"
NEWTON = "score/stages/physics/inside/newton_env.sh"
NEWTON_PYTHON = "/root/lib/envs/newton_env"
VIEWS = "tools/blender/inside/usd_views.py"
PAINT = "score/stages/surfaces/inside/paint_bake.py"
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


def bake(name, made):
    return {"script": PAINT, "args": [name], "inputs": [], "outputs": [f"{{root}}/labelled/{name}", made], "minutes": 1}


LIGHT = {"script": "score/stages/light/inside/light_passes.py", "args": ["/a", "/s"], "inputs": ["{root}/tree/garage"],
         "outputs": ["{root}/o2"], "minutes": 4}
BIG_LIGHT = {**LIGHT, "args": ["/a", "/b"], "inputs": ["{root}/tree/base", "{root}/tree/garage"], "outputs": ["{root}/o"]}
BASE = 2 * 10**9
LAMP = 1024 * 1024 * 4  # the 1k map decoded
MAPS = 4 * 16384 * 8192 * 4  # four 16k by 8k maps decoded: 2.147 GB
CARDS = "gpu-24gb,gpu-48gb,gpu-80gb"
# Each call on this PC (a machine of 3 GiB alone, 1 GiB shared): its jobs, its --classes and the classes in stock;
# its refusal (None: it reaches pricing, on the class it names), whether kept jobs were read, the most one job is
# predicted to take, the card its script measured and its take mark's key (None: a held chain names no script).
CALLS = [
    ("two takes writing into one made folder", [bake("crate", "{root}/made"), bake("barrel", "{root}/made/barrel")],
     None, (), "Blender jobs 0 and 1 both write into {root}/made: each job brings back into an output of its own",
     False, BASE, None, "e8bbe6423a622988"),
    # no stock keeps the first class asked, its claims waiting: no stock never makes a gap (owner, 2026-10-23)
    ("each take bringing back into its own, no card in stock",
     [bake("crate", "{root}/.bake-crate-made"), bake("barrel", "{root}/.bake-barrel-made")],
     CARDS, ("cpu-32c-128gb",), "gpu-24gb", True, BASE, None, "e8bbe6423a622988"),
    ("a light job past this PC's machine alone", [LIGHT, BIG_LIGHT], None, (),
     "Blender job 1 (score/stages/light/inside/light_passes.py) is predicted to need 4.2 GB (5 input pictures decoded, "
     "plus 2 GB) and this PC's machine has 3.2 GB with the job alone: not started; it needs a bigger machine, a priced "
     "ask", True, BASE + MAPS + LAMP, 13.0, "148c32fbefbb40c1"),
    # one class fixed before the call, the first in stock (CONTEXT.md, owner 2026-10-20: with cards short a 32-core
    # machine was rented instead and claims moved between classes as stock moved)
    ("a light job past the shared container but within its room alone, the second card in stock", [LIGHT],
     CARDS, ("cpu-32c-128gb", "gpu-48gb", "gpu-80gb"), "gpu-48gb", True, BASE + LAMP, 13.0, "8ede7e0dba1610b1"),
    # a held machine's chain (--serve) names no script until its jobs come: its need is the base alone, never the
    # KeyError that ended the serve before 1.json ran (2026-11-10: settle@garage and sim-body@base)
    ("a held chain naming no script yet", [{"minutes": 30}], None, ("cpu-32c-128gb",), "cpu-32c-128gb", True, BASE,
     None, None),
]


def a_png(path, width, height):
    """A PNG at `path` whose header says width x height (an empty IDAT: nothing to decode, which nothing does)."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                     + chunk(b"IDAT", b"") + chunk(b"IEND", b""))


def runner_python_under(props_home):
    """CLOUD_PYTHON as a fresh import sees it with PROPS_HOME set to `props_home` (None: unset)."""
    environment = {key: value for key, value in os.environ.items() if key != "PROPS_HOME"}
    if props_home is not None:
        environment["PROPS_HOME"] = str(props_home)
    return subprocess.run([sys.executable, "-c", "import blender_cloud; print(blender_cloud.CLOUD_PYTHON)"],
                          cwd=pathlib.Path(__file__).resolve().parent, env=environment, capture_output=True,
                          text=True, check=True).stdout.strip()


class Priced(Exception):
    """The call got past every refusal to pricing, on the one class its offers are of."""


class Transport:
    """This test's machines: an ssh command answered by what its job's first argument asks (`fails`: 60 log lines
    and a failed exit; `stopped`: a stop signal; `slow`: half a second), and an rsync copy back bringing what
    `wrote` says lies at its source (rsync's names relative to the source's parent), or failing as rsync does on
    a missing source."""

    def __init__(self):
        self.wrote, self.ran, self.copies, self.copying, self.most = {}, [], [], 0, 0
        self.guard = threading.Lock()

    def remote(self, log_folder, host, command, check=True, stdout=None, stderr=None):
        if "library_setup.sh" in command:
            stdout.write("blender ready\n")
        if command.startswith(("mkdir", "bash ")):
            return
        words = shlex.split(command)
        asked = words[words.index("--") + 1:]
        self.ran.append(asked)
        if asked[:1] == ["fails"]:
            stdout.write("".join(f"line {index}\n" for index in range(60)) + "RuntimeError: the drop met 832 contacts\n")
            raise subprocess.CalledProcessError(1, "ssh")
        if asked[:1] == ["stopped"]:
            stdout.write("Blender: settling\n")
            raise SystemExit("stopped by signal 15")
        if asked[:1] == ["slow"]:
            threading.Event().wait(0.5)

    def run(self, command, **keywords):
        host, source = command[-2].removeprefix("root@").split(":", 1)
        with self.guard:
            self.copying += 1
            self.most = max(self.most, self.copying)
        threading.Event().wait(0.05)
        with self.guard:
            self.copying -= 1
            self.copies.append(source)
        if source not in self.wrote:
            raise subprocess.CalledProcessError(23, "rsync")
        for name in self.wrote[source]:
            path = pathlib.Path(command[-1]) / name
            path.mkdir(parents=True, exist_ok=True) if name.endswith("/") else path.write_text(f"{name} from {host}")
        said = "".join(f"{name}\n" for name in self.wrote[source])
        return subprocess.CompletedProcess(command, 0, said if "--out-format=%n" in command else "", "")


class Serving:
    """A held machine's --serve process, as a thread serving its queue on the Transport: what ended it, once it has."""

    def __init__(self, queue, logs):
        self.ended = None
        self.thread = threading.Thread(target=self.serve, args=(queue, logs), daemon=True)
        self.thread.start()

    def serve(self, queue, logs):
        try:
            blender_cloud.serve(types.SimpleNamespace(deadline=float("inf")), {"folder": logs, "class": "cpu-32c-128gb"},
                                queue, 1)
        except BaseException as ended:  # noqa: BLE001 - kept for the test to read
            self.ended = ended

    def poll(self):
        return None if self.thread.is_alive() else 0

    def wait(self):
        self.thread.join(10)


def test_blender_cloud_runs_a_job_as_written(tmp_path, monkeypatch):
    from paths import VENV_PYTHON
    # The jobs as written: on a rented machine and on the cluster, arguments unchanged, the script from the copy of
    # the repo (Blender's, or its env script's Python), Cycles on the card on card classes and on the cores otherwise;
    # settling's drops alone go to the cluster as kind `settle`, in the repo's Python.
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
    # the machine runner's Python follows PROPS_HOME
    for props_home, python in ((tmp_path, f"{tmp_path}/env/bin/python"),
                               (None, str(pathlib.Path.home() / ".farm-factory-props/env/bin/python"))):
        assert runner_python_under(props_home) == python, props_home

    # The calls on this PC, through main up to pricing. Round 23: base's light passes (271 full-size maps, 27.3 GB
    # decoded) filled this PC's container in 35 s; #36 (2026-10-30): a bake row's takes all brought back into one
    # `made` folder, so each kept take named the others as peers and was baked again whenever one of them was. A call
    # whose jobs write into one output (the same folder, or one inside another) stops naming both before any kept job
    # is put back; one whose job is predicted (2 GB plus its input pictures decoded) past the machine with the job
    # alone stops naming that job, its GB and a bigger machine, before it prices or claims anything (round 31: base's
    # light passes were refused by the shared container though a job alone had room). The rest reach pricing on one
    # class, their claim asking the most one job is predicted to take in GiB and the card its script measured; each
    # take's mark carries its prediction and whether every output came back, keyed as score/graph take_key keys it.
    monkeypatch.delenv("SCORE_CLOUD", raising=False)
    monkeypatch.delenv("SCORE_CLOUD_KINDS", raising=False)
    monkeypatch.delenv("SCORE_RUN_ID", raising=False)  # no warm pool
    for name in ("wall.png", "floor.PNG", "roof.png", "door.png"):
        a_png(tmp_path / "tree" / "base" / "assets" / "textures" / name, 16384, 8192)
    a_png(tmp_path / "tree" / "garage" / "assets" / "textures" / "lamp.png", 1024, 1024)
    (tmp_path / "tree" / "base" / "base.usda").write_text("#usda 1.0\n")
    machine = type("ThisPC", (), {"NAME": "local", "memory_cap": staticmethod(lambda: "1g"),
                                  "alone_cap": staticmethod(lambda: "3g"), "account": staticmethod(lambda: "account")})
    monkeypatch.setattr(blender_cloud, "cloud", machine)
    monkeypatch.setattr(blender_cloud, "TAKE_MARKS", tmp_path / "marks")
    monkeypatch.setattr(blender_cloud.batch, "sweep", lambda account: None)

    def priced(found, minutes, count, what, account):
        raise Priced(*{offer.machine_class for offer in found})
    monkeypatch.setattr(blender_cloud.batch, "priced", priced)
    for number, (name, written, classes, stock, ending, kept_read, heaviest, card_gb, mark) in enumerate(CALLS):
        monkeypatch.setattr(blender_cloud.batch, "offers", lambda asked, stock=stock: [
            provider.Offer(0.01, 0, f"{one}-type", "zone-a", 0.01, one, 0,
                           "available" if one in stock else "shortage") for one in asked])
        calls = json.loads(json.dumps(written).replace("{root}", str(tmp_path)))
        paths = []
        for index, job in enumerate(calls):
            paths.append(tmp_path / "calls" / f"{number}-{index}.json")
            paths[-1].parent.mkdir(exist_ok=True)
            paths[-1].write_text(json.dumps(job))
        read = []
        monkeypatch.setattr(blender_cloud, "still_to_run", lambda jobs, cluster=None: read.append(jobs) or jobs)
        monkeypatch.setattr(sys, "argv", ["blender_cloud.py", *map(str, paths), "--who", "a test", "--dry-run",
                                          *(["--classes", classes] if classes else [])])
        refused = " " in ending
        with pytest.raises(SystemExit if refused else Priced) as ended:
            blender_cloud.main()
        assert str(ended.value) == ending.replace("{root}", str(tmp_path)), name
        assert bool(read) == kept_read, (name, read)
        assert blender_cloud.alone_need(calls) == {"memory_gb": heaviest / 2**30,
                                                   **({"card_gb": card_gb} if card_gb else {})}, name
        if mark:  # a held chain's job names no script to mark
            blender_cloud.mark_take(calls[-1], wrote=True)
            assert json.loads((tmp_path / "marks" / f"{mark}.json").read_text()) == {
                "kind": pathlib.PurePosixPath(calls[-1]["script"]).name, "predicted": heaviest, "wrote": True}, name
    monkeypatch.undo()

    # One machine side, every job of a spread run, side by side or in a held chain running on it.
    transport = Transport()
    making, logs = tmp_path / "making", tmp_path / "logs"
    (making / "made").mkdir(parents=True)
    logs.mkdir()
    (making / "made" / "barrel.gltf").write_text("another take's")
    monkeypatch.setattr(blender_cloud, "cloud", machine)
    monkeypatch.setattr(blender_cloud, "TAKE_MARKS", tmp_path / "marks")
    monkeypatch.setenv(kept.CODE, "surfaces-bake row code")
    monkeypatch.setenv(kept.STORE, str(tmp_path / "store"))
    monkeypatch.setenv(kept.MAKING, str(making))
    monkeypatch.setattr(blender_cloud, "system", lambda cluster=None: "this test's machine")
    monkeypatch.setattr(blender_cloud.batch, "say", lambda line: None)
    monkeypatch.setattr(blender_cloud.batch, "remote", transport.remote)
    monkeypatch.setattr(blender_cloud.batch, "copy", lambda *args: None)
    monkeypatch.setattr(blender_cloud, "subprocess", types.SimpleNamespace(
        run=transport.run, CalledProcessError=subprocess.CalledProcessError, STDOUT=subprocess.STDOUT))
    monkeypatch.setattr(blender_cloud, "send_inputs", lambda *args: None)
    linked = []
    monkeypatch.setattr(blender_cloud.inputs, "link_named", lambda folder, host, paths: linked.append(list(paths)))
    monkeypatch.setattr(blender_cloud.spread, "tended", lambda run, machine: contextlib.nullcontext("held"))
    monkeypatch.setattr(blender_cloud, "time", types.SimpleNamespace(
        time=time.time, strftime=time.strftime, sleep=lambda seconds: threading.Event().wait(0.02)))
    rented = {"folder": logs, "host": "rented"}

    # Audit (2026-10-22): kept.py was never called here, so a cut-off run paid again for every finished job.
    shots = [{"script": VIEWS, "args": [str(number)], "inputs": [], "outputs": [str(making / f"shot{number}.png")],
              "minutes": 1} for number in range(2)]
    transport.wrote[str(making / "shot0.png")] = ["shot0.png"]
    blender_cloud.one_job(rented, (0, shots[0]), None)  # cut off before job 1
    (making / "shot0.png").unlink()  # the next attempt's folder starts empty
    assert blender_cloud.still_to_run(shots) == [shots[1]]
    assert (making / "shot0.png").read_text() == "shot0.png from rented"

    # surfaces-bake@campgrounds (2026-10-27): twelve paint and bake jobs ended well, wrote their outputs through a path
    # the machine did not link as this side does, and counted done with nothing back; the row raised for all.
    lost = {"script": PAINT, "args": ["lost"], "inputs": [], "minutes": 1,
            "outputs": [str(making / "labelled" / "lost"), str(making / ".bake-lost-made")]}
    with pytest.raises(blender_cloud.spread.JobFailed, match="none of its outputs came back"):
        blender_cloud.one_job(rented, (3, lost), None)
    assert linked[-1] == lost["outputs"], linked  # its outputs reached through the links its paths are named through
    assert kept.missing([lost], "this test's machine") == [lost]  # nothing kept as done

    # This PC runs a bake row's takes side by side (backends/local.py RUNS_AT_ONCE), all bringing back into the row's
    # `made` folder: a copy into it while another job's copy reads it would keep a file caught mid-write. env1
    # (2026-10-29): a take's kept copy of a whole output folder held what else lay there; it keeps only what its own
    # copy back wrote, never the other take's barrel.gltf.
    crate = {"script": PAINT, "args": ["crate"], "inputs": [], "minutes": 1,
             "outputs": [str(making / "labelled" / "crate"), str(making / "made")]}
    transport.wrote[str(making / "made")] = ["made/", "made/crate.gltf"]
    transport.wrote[str(making / "labelled" / "crate")] = ["crate/", "crate/labels.json"]
    came = []
    slots = [threading.Thread(target=lambda number: came.append(
        blender_cloud.run_job(logs, "this-pc", number, crate, True)[1:]), args=(number,)) for number in range(3)]
    for slot in slots:
        slot.start()
    for slot in slots:
        slot.join()
    assert transport.most == 1
    assert came == 3 * [(2, {"brought": {making / "made" / "crate.gltf", making / "labelled" / "crate" / "labels.json"}})]
    # a long job that asks brings its outputs back while it runs, not only at its end
    views = str(making / "views")
    transport.wrote[views] = ["views/", "views/front.png"]
    blender_cloud.run_job(logs, "cloud", 9, {"script": VIEWS, "args": ["slow"], "inputs": [], "outputs": [views],
                                             "minutes": 1, "bring_every": 0.002}, True)
    assert transport.copies.count(views) >= 3  # every 0.12 s of its 0.5 s run, then at its end

    # A held machine runs its chain in order; a failed job raises with the end of its job log and the set-up log
    # (settle@airlock, 2026-10-29: the fault named only the job log, whose folder was gone by then), and a job ended
    # by anything else (an error past its script, a stop signal) still leaves its .failed with its logs.
    held = blender_cloud.Machine(["cpu-32c-128gb"], "test")
    held.queue = tmp_path / "queue"
    held.queue.mkdir()
    held_logs = tmp_path / "held-logs"
    held_logs.mkdir()
    held.process = Serving(held.queue, held_logs)
    script = blender_cloud.REPO / VIEWS
    ran = len(transport.ran)
    held.run(script, ["a"], [], [])
    held.run(script, ["b"], [], [])
    assert transport.ran[ran:] == [["a"], ["b"]]
    with pytest.raises(RuntimeError) as error:
        held.run(script, ["fails"], [], [])
    said = str(error.value)
    assert "failed" in said and "blender ready" in said, said
    assert said.endswith("RuntimeError: the drop met 832 contacts"), said
    assert "line 21" in said and "line 20\n" not in said  # the job log's last 40 lines, no more
    with pytest.raises(RuntimeError):
        held.run(script, ["stopped"], [], [])
    held.__exit__(None, None, None)
    stopped = (held.queue / "4.failed").read_text()
    assert stopped.startswith("the job ended: SystemExit: stopped by signal 15") and "Blender: settling" in stopped
    assert isinstance(held.process.ended, SystemExit), held.process.ended
    assert sorted(path.name for path in held.queue.glob("*.json")) == ["1.json", "2.json", "3.json", "4.json"]
    assert (held.queue / "close").exists()
