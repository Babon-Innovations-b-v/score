"""Run headless Blender scripts on a rented cloud machine: send their input files, run each, bring their outputs back,
delete the machine. The generic Blender job (2026-10-08, BLENDER IN THE CLOUD): the local Blender lock lets one
Blender run on the owner's PC at a time, so renders, settling and review pages run here, many machines at once.

    ~/.farm-factory-props/env/bin/python tools/cloud/blender_cloud.py <job.json> [<job.json> ...] \
        --who "<session>" [--classes cpu-32c-128gb[,...]] [--dry-run] [--detach]

--detach runs the same call with its progress in a log and prints one result line at the end (detached.py): start it
with run_in_background and never poll it.

A tool on this PC calls `run_elsewhere` for one job (tools/usd/settle.py --cloud), or holds one machine for a chain
of jobs with `Machine` (tools/review/page.py --cloud: model shots, every stage's views and the walk on one machine):

    with blender_cloud.Machine(classes, who) as machine:
        machine.run(script, arguments, inputs, outputs, minutes)   # as many as the tool needs

which runs this file with --serve on a queue folder: it rents once, runs each job written to the queue in turn, and
deletes the machine when the tool closes the queue or after IDLE_MINUTES with nothing to do. A job:
    {"script": "tools/blender/inside/settle_stage.py",   a Blender script in this repo
     "args": ["/abs/stage.usda", "/abs/job.json", "/abs/out.json"],   what follows its `--`
     "inputs": ["/abs/folder", "/abs/file"],   files and folders it reads (sent as they are)
     "outputs": ["/abs/out.json", "/abs/folder"],   files and folders it writes (brought back)
     "minutes": 5,   about how long it runs on the machine
     "env": "score/stages/physics/inside/newton_env.sh"}   optional: the script is no Blender script but runs in the
                                    Python this script beside it builds (once) at the folder it is given

Every input and output lies at the same absolute path on the machine as here, so a script, its arguments and the paths
inside its input files (a review page's shots.json names the model files) need no change to run up there. An input of
8 MB or more goes up once to the object store and the machine pulls it from there (inputs.py); the rest is sent
directly, as is any input the store path fails to bring. The script's own
folder and tools/blender/inside go up with it. The jobs of one call are spread over as many machines as finish them
in about the setup and the longest job (spread.py, capacity.machines_for): one machine for a short list, one a job for
a long one, each set up once and taking the next job as it ends one. Every job runs once (a batch, CONTEXT.md, owner
2026-10-20): one that fails, or whose machine is lost, is a gap (spread.py).
Classes: a processor machine for physics (settling: cpu-32c-128gb first,
the default), a card for renders (`--classes gpu-24gb`, Cycles on the card; on a processor machine Cycles renders on
its cores: FARM_CYCLES_GPU or FARM_CYCLES_CPU is set for the script). One class is fixed for the whole call at price
time (batch.one_class_in_stock: the first asked that the run's warm pool holds, else the first in stock, else the
first sold), never another class or a processor machine for a card job; no stock never makes a gap (owner,
2026-10-23): under a run's warm pool every claim takes a pool card, else it waits for stock. Blender is 5.0.1 from blender.org, set up by
library_setup.sh. The owner's limits, the self-delete, the watchdog, the delete and the ledger
are batch.py's.

Under SCORE_CLOUD=k8s the same calls run each job as a Kubernetes Job of the blender image on the cluster
(tools/cloud/k8s/cluster_jobs.py), inputs and outputs at the same paths; the machines stay the default.
"""
import argparse
import contextlib
import functools
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "props"))

import batch  # noqa: E402
import capacity  # noqa: E402
import detached  # noqa: E402
import inputs  # noqa: E402
import kept  # noqa: E402
import ledger  # noqa: E402
import park  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402
from paths import HOME, REPO  # noqa: E402
from provider import cloud  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/lib")
SETUP_MINUTES = 8
KIND = "blender"
# Settling and other physics: the processor machines, in the order the stock read at price time picks one class from.
DEFAULT_CLASSES = ("cpu-32c-128gb", "cpu-32c-64gb", "cpu-32c-256gb", "cpu-16c-64gb")
ALWAYS_SHIPPED = ("tools/blender/inside",)
# A held machine (--serve): the chain's expected minutes for the owner's limits, and how long it waits for the next job.
SERVE_MINUTES = 60
IDLE_MINUTES = 10
# One job's outputs brought back, and kept, at a time on each machine (by host): jobs side by side on one (this PC's,
# backends/local.py RUNS_AT_ONCE) can share an output folder (a bake row's `made`), which a copy must not read while
# another job's outputs are still arriving into it.
BRINGING = {}
# The jobs started on each machine (by host) and not yet brought back: what one job's copy back may carry besides its
# own files (kept.py's peers).
ACTIVE = {}
# The lines of a failed job's log and its machine's set-up log its error carries: the fault report shows the error,
# not the log, and the job's folder can be gone by then (settle@airlock, 2026-10-29: failed blind).
LOG_TAIL_LINES = 40
# A job's memory, predicted from its inputs before it starts: every input picture decoded (width x height x 4 bytes,
# from its header alone) plus PREDICTED_BASE for Blender and the scene. Round 23: base's light passes (271 full-size
# maps, 27.3 GB decoded) needed about 29 GB and filled this PC's container in 35 s. On this PC a job predicted past
# the container's whole memory is refused by name before anything runs (too_big_here); each take's prediction and
# whether it wrote its outputs go in its mark under TAKE_MARKS, which the runner's memory reserve reads (score/graph
# take_peak).
PREDICTED_BASE = 2 * 10**9
PICTURE_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".tga", ".bmp")
TAKE_MARKS = HOME / "cloud" / "this-pc.takes"


def script_line(job, repo, blender):
    """The script's own command: in Blender, or in the Python its job's `env` script builds beside the repo."""
    arguments = [str(argument) for argument in job.get("args", ())]
    script = str(pathlib.PurePosixPath(repo) / job["script"])
    if not job.get("env"):
        return shlex.join([blender, "-b", "-setaudio", "None", "--python-exit-code", "1", "--python", script, "--",
                           *arguments])
    folder = pathlib.PurePosixPath(repo).parent / "envs" / pathlib.PurePosixPath(job["env"]).stem
    return (f"bash {shlex.quote(str(pathlib.PurePosixPath(repo) / job['env']))} {shlex.quote(str(folder))} && "
            + shlex.join([str(folder / "bin/python"), script, *arguments]))


def run_line(job, card):
    """The command that runs a job's script on the machine."""
    engine = "FARM_CYCLES_GPU=1" if card else "FARM_CYCLES_CPU=1"
    return (f"cd /root && export {engine} PROPS_HOME=/root/props && "
            + script_line(job, REMOTE / "repo", "/root/blender/blender"))


def shipped(jobs):
    """The repo folders the jobs' scripts need: tools/blender/inside, each script's own folder and its env script's."""
    return sorted({*ALWAYS_SHIPPED, *(str(pathlib.PurePosixPath(job[field]).parent)
                                      for job in jobs for field in ("script", "env") if job.get(field))})


def plan(jobs):
    """How many machines the jobs are spread over (capacity.machines_for), and how long they keep them."""
    minutes = [float(job.get("minutes", 10)) for job in jobs]
    count = capacity.machines_for(len(jobs), sum(minutes) / len(minutes), SETUP_MINUTES)
    return count, SETUP_MINUTES + max(max(minutes), sum(minutes) / count)


def price(jobs, account, classes):
    """Print the estimate and refuse what passes the owner's limits; the offers of the call's one class
    (batch.one_class_in_stock), the machines and the minutes allowed."""
    found = batch.one_class_in_stock(classes)
    if not found:
        raise SystemExit(f"the {cloud.NAME} backend sells no machine of {', '.join(classes)}")
    count, minutes = plan(jobs)
    what = f"{len(jobs)} Blender jobs on {count} machine{'s' if count > 1 else ''}"
    return found, count, batch.priced(found, minutes, count, what, account)


def send(log_folder, host, local):
    """One input (file or folder) to its place on the machine."""
    local = pathlib.Path(local).resolve()
    batch.remote(log_folder, host, f"mkdir -p {shlex.quote(str(local.parent))}", check=True)
    batch.copy(log_folder, [local], f"root@{host}:{local.parent}/")


def send_inputs(log_folder, host, locals_):
    """A job's inputs to their places on the machine: the big ones pulled from the object store (inputs.py), the
    rest, and any the store path could not bring, sent directly."""
    began = time.time()
    arrived = inputs.through_store(log_folder, host, locals_)
    direct = [local for local in locals_ if str(pathlib.Path(local).resolve()) not in arrived]
    for local in direct:
        send(log_folder, host, local)
    batch.say(f"inputs on {host}: {len(arrived)} from the store, {len(direct)} sent directly, "
              f"{time.time() - began:.0f} s")


def copy_back(log_folder, source, destination):
    """batch.copy's rsync from the machine, saying each file it wrote (relative to `destination`). Here, not in
    batch.py: rows declare batch.py as a file, so an edit there moves their keys."""
    ssh = shlex.join(["ssh", *batch.ssh_options(log_folder)])
    return subprocess.run(["rsync", "-a", "--exclude", ".git", "--out-format=%n", "-e", ssh, source, destination],
                          check=True, capture_output=True, text=True, errors="replace").stdout


def bring_back(log_folder, host, local):
    """One output (file or folder) from the machine to its own place here; a missing one is said, not raised.
    The files this copy wrote here (rsync's list: a job keeps only these, kept.py), or None when it did not come."""
    local = pathlib.Path(local).resolve()
    local.parent.mkdir(parents=True, exist_ok=True)
    try:
        said = copy_back(log_folder, f"root@{host}:{local}", f"{local.parent}/")
    except subprocess.CalledProcessError:
        batch.say(f"the machine wrote no {local}")
        return None
    return {local.parent / name for name in said.splitlines() if name and not name.endswith("/")}


def ship(log_folder, host, jobs):
    """The repo folders the jobs need, to their places on the machine (rsync sends only what changed)."""
    for folder in shipped(jobs):
        parent = (REMOTE / "repo" / folder).parent
        batch.remote(log_folder, host, f"mkdir -p {parent}", check=True)
        batch.copy(log_folder, [REPO / folder], f"root@{host}:{parent}/", "--exclude", "__pycache__")


def set_up(log_folder, host, jobs):
    """The jobs' repo folders and Blender onto the machine; on this PC's machine, shared across claims, one claim's
    set-up at a time (backends/local.py setting_up), so no library_setup.sh replaces a Blender another one runs."""
    with getattr(cloud, "setting_up", contextlib.nullcontext)():
        set_up_alone(log_folder, host, jobs)


def set_up_alone(log_folder, host, jobs):
    ship(log_folder, host, jobs)
    batch.copy(log_folder, [HERE / "library_setup.sh"], f"root@{host}:{REMOTE}/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"bash {REMOTE}/library_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def run_job(log_folder, host, number, job, card):
    """One job: its inputs up, its output folders made (reached through the links its paths are named through, as
    its inputs are: inputs.link_named), the script run, its outputs back (also when it fails); its seconds, how
    many of its outputs came back and what kept.keep keeps of it ({"brought": the files its copies wrote, "peers":
    the jobs sharing its folders still to come back from this machine, whose files those copies may carry})."""
    send_inputs(log_folder, host, job.get("inputs", ()))
    inputs.link_named(log_folder, host, job.get("outputs", ()))
    for local in job.get("outputs", ()):
        batch.remote(log_folder, host, f"mkdir -p {shlex.quote(str(pathlib.Path(local).resolve().parent))}",
                     check=True)
    began, running, mine = time.time(), ACTIVE.setdefault(host, {}), object()
    running[mine] = job
    try:
        with (log_folder / f"job{number}.log").open("w") as log:
            batch.remote(log_folder, host, run_line(job, card), check=True, stdout=log, stderr=subprocess.STDOUT)
    finally:
        with BRINGING.setdefault(host, threading.Lock()):
            running.pop(mine)
            others = list(running.values())
            copies = [bring_back(log_folder, host, local) for local in job.get("outputs", ())]
        batch.say(f"Blender job {number} ({job['script']}): {(time.time() - began) / 60:.1f} min")
    came = sum(found is not None for found in copies)
    return round(time.time() - began, 1), came, {"brought": set().union(*(found or () for found in copies)),
                                                 "peers": kept.peers_of(job, others, system())}


def log_tail(log_folder, number):
    """The last LOG_TAIL_LINES of job `number`'s log and of the machine's set-up log, each headed by its path."""
    found = []
    for log in (log_folder / "setup.log", log_folder / f"job{number}.log"):
        if log.exists():
            lines = log.read_text(errors="replace").strip().splitlines()[-LOG_TAIL_LINES:]
            found.append(f"\nthe end of {log}:\n" + "\n".join(lines))
    return "".join(found)


def killed_in(log):
    """Whether a job's log ends with a step it ran killed by signal 9 (subprocess's 'died with <Signals.SIGKILL: 9>'):
    paint_bake.py runs make_chunky in a Blender of its own, so the job's own exit is a plain failure."""
    return log.exists() and "Signals.SIGKILL" in log.read_text(errors="replace")[-LOG_TAIL_CHARS:]


LOG_TAIL_CHARS = 4000


def touched(machine, job):
    """Note the job's inputs and outputs on the machine, for its clean-up before it is parked."""
    machine.setdefault("paths", set()).update(str(pathlib.Path(local).resolve())
                                              for local in (*job.get("inputs", ()), *job.get("outputs", ())))


def cleanup(machine):
    """The command that removes a run's own files from its machine before it is parked (park.py): every job's inputs
    and outputs at their paths. Blender and the shipped repo folders stay (rsync sends only what changed)."""
    paths = sorted(path for path in machine.get("paths", ()) if path != "/" and not path.startswith("/root"))
    return f"rm -rf {shlex.join(paths)}"


park.CLEANUPS[KIND] = cleanup


def waiting_jobs(queue):
    """The job files in a --serve queue not yet done or failed, in the order they were written."""
    return sorted((path for path in queue.glob("*.json") if not path.with_suffix(".done").exists()
                   and not path.with_suffix(".failed").exists()), key=lambda path: int(path.stem))


def serve(run, machine, queue, idle_minutes):
    """One machine for a chain: Blender up, then each job file written to `queue` run in turn (`<n>.done` or
    `<n>.failed` beside it), until the queue is closed (`close`) and empty or nothing came for `idle_minutes`."""
    log_folder = machine["folder"]
    with spread.tended(run, machine) as host:
        set_up(log_folder, host, [])
        (queue / "ready").write_text(machine.get("class", ""))
        card = machine.get("class", "").startswith("gpu")
        last = time.time()
        while time.time() < run.deadline:
            waiting = waiting_jobs(queue)
            if not waiting:
                if (queue / "close").exists() or time.time() - last > idle_minutes * 60:
                    return
                time.sleep(2)
                continue
            job = json.loads(waiting[0].read_text())
            try:
                # Every job's folders go up again, so a script edited during a chain runs as it is now.
                ship(log_folder, host, [job])
                touched(machine, job)
                seconds = run_job(log_folder, host, int(waiting[0].stem), job, card)[0]
                machine.setdefault("unit_seconds", []).append(seconds)
                waiting[0].with_suffix(".done").write_text(str(seconds))
            except subprocess.CalledProcessError as failed:
                waiting[0].with_suffix(".failed").write_text(f"{failed}{log_tail(log_folder, waiting[0].stem)}")
            last = time.time()


@functools.cache
def picture_bytes(path):
    """What the picture at `path` takes decoded: width x height x 4, read from its header alone (a PNG's IHDR, else
    PIL's lazy open, its pixel limit off: a 16k map is no bomb here and nothing is decoded)."""
    with open(path, "rb") as picture:
        head = picture.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n" and head[12:16] == b"IHDR":
        return int.from_bytes(head[16:20], "big") * int.from_bytes(head[20:24], "big") * 4
    from PIL import Image

    Image.MAX_IMAGE_PIXELS = None
    with Image.open(path) as opened:
        return opened.width * opened.height * 4


def input_pictures(job):
    """Every picture file (PICTURE_SUFFIXES) among a job's inputs, in its input folders too."""
    found = []
    for local in map(pathlib.Path, job.get("inputs", ())):
        for path in [local] if local.is_file() else (local.rglob("*") if local.is_dir() else ()):
            if path.suffix.lower() in PICTURE_SUFFIXES and path.is_file():
                found.append(path)
    return found


def predicted_bytes(job):
    """A job's memory, predicted from its inputs: PREDICTED_BASE plus each input picture decoded (picture_bytes)."""
    return PREDICTED_BASE + sum(map(picture_bytes, input_pictures(job)))


def too_big_here(jobs):
    """On this PC (SCORE_CLOUD=local) why the jobs cannot start, naming each one predicted (predicted_bytes) past the
    container's whole memory (local.memory_cap); None when every one fits, or off this PC."""
    if cloud.NAME != "local":
        return None
    room = int(cloud.memory_cap()[:-1]) * 2**30
    over = [(number, job, predicted_bytes(job)) for number, job in enumerate(jobs)]
    lines = [f"Blender job {number} ({job['script']}) is predicted to need {need / 1e9:.1f} GB "
             f"({len(input_pictures(job))} input pictures decoded, plus {PREDICTED_BASE / 1e9:.0f} GB) and this PC's "
             f"machine has {room / 1e9:.1f} GB: not started; it needs a bigger machine, a priced ask"
             for number, job, need in over if need > room]
    return "\n".join(lines) or None


def take_key(arguments):
    """A take's key: the hash of its script's arguments, the same as score/graph take_key's (which reads them from
    the take's command line in the container)."""
    return hashlib.sha256("\0".join(arguments).encode()).hexdigest()[:16]


def mark_take(job, **ended):
    """On this PC, the job's take mark for the runner's memory reserve (TAKE_MARKS/<take_key>.json): its kind, its
    predicted bytes and, once it ended, `ended` (wrote: whether every output came back)."""
    if cloud.NAME != "local":
        return
    TAKE_MARKS.mkdir(parents=True, exist_ok=True)
    mark = TAKE_MARKS / f"{take_key([str(argument) for argument in job.get('args', ())])}.json"
    spare = mark.with_suffix(f".{os.getpid()}")
    spare.write_text(json.dumps({"kind": pathlib.PurePosixPath(job["script"]).name, "predicted": predicted_bytes(job),
                                 **ended}))
    os.replace(spare, mark)


def one_job(machine, share, card):
    """One of a spread run's jobs on a machine: a script that fails raises spread.JobFailed, a machine that stops
    answering a ConnectionError; a script that ended well and brought none of its outputs back failed too (it wrote
    them somewhere nothing reads: surfaces-bake@campgrounds, 2026-10-27, twelve such jobs counted done)."""
    number, job = share
    log_folder, host = machine["folder"], machine["host"]
    log = log_folder / f"job{number}.log"
    touched(machine, job)
    mark_take(job)
    try:
        seconds, came, keeping = run_job(log_folder, host, number, job, card is not None)
    except subprocess.CalledProcessError as failed:
        mark_take(job, wrote=False)
        spread.raise_for(failed.returncode, f"job {number} ({job['script']}){log_tail(log_folder, number)}",
                         killed=killed_in(log))
    mark_take(job, wrote=came == len(job.get("outputs", ())))
    machine.setdefault("unit_seconds", []).append(seconds)
    if job.get("outputs") and not came:
        raise spread.JobFailed(f"job {number} ({job['script']}, {log}): its script ended well but none of its "
                               "outputs came back")
    with BRINGING.setdefault(host, threading.Lock()):
        kept.keep(job, system(), **keeping)


@functools.cache
def system():
    """What this call's jobs run on, in each kept job's content (kept.py): the machine image (this PC's container
    image by its id, a cloud's images by name, the cluster's Blender image by its digest) and the Blender set-up."""
    if provider.on_cluster():
        image = json.dumps(json.loads((HERE / "images/images.json").read_text())[KIND], sort_keys=True)
    else:
        image = cloud.image_identity()
    return f"{image}\n{(HERE / 'library_setup.sh').read_text()}"


def still_to_run(jobs):
    """The jobs no earlier run finished with the same content; each it did is put back in place (kept.py) and not
    bought again."""
    waiting = kept.missing(jobs, system())
    if len(waiting) < len(jobs):
        batch.say(f"{len(jobs) - len(waiting)} of {len(jobs)} Blender jobs finished earlier with the same inputs, code "
                  "and system: put back, not bought again")
    return waiting


def run_spread(run, account, found, count, jobs):
    """Spread the jobs over `count` machines, each set up once and taking the next job as it ends one; the numbers
    of the jobs that failed or never ran."""
    shares = spread.Shares(enumerate(jobs), deadline=run.deadline)
    spread.on_machines(run, account, found, count, KIND, shares,
                       lambda machine: set_up(machine["folder"], machine["host"], jobs), one_job)
    return sorted(number for number, _ in [*shares.failed, *shares.waiting])


# The machine runner's Python: PROPS_HOME's env (default ~/.farm-factory-props), the one bootstrap.sh builds.
CLOUD_PYTHON = HOME / "env/bin/python"


def cloud_python():
    """The Python a call of this file runs in: the machine runner's, or under SCORE_CLOUD=k8s the repo's own
    environment, which has boto3 for the object store."""
    from paths import VENV_PYTHON

    return VENV_PYTHON if provider.on_cluster() else CLOUD_PYTHON


def job_of(script, arguments, inputs, outputs, minutes, env=None):
    """A job as this file takes it."""
    found = {"script": str(pathlib.Path(script).resolve().relative_to(REPO)),
             "args": [str(argument) for argument in arguments],
             "inputs": [str(path) for path in inputs], "outputs": [str(path) for path in outputs], "minutes": minutes}
    if env:
        found["env"] = str(pathlib.Path(env).resolve().relative_to(REPO))
    return found


class Machine:
    """One rented machine held for a chain of jobs from one tool run (this file's --serve on a queue folder)."""

    def __init__(self, classes, who, minutes=SERVE_MINUTES):
        self.classes, self.who, self.minutes = classes, who, minutes
        self.queue = batch.BATCHES / "queues" / f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"
        self.process, self.count = None, 0

    def __enter__(self):
        self.queue.mkdir(parents=True)
        self.process = subprocess.Popen([str(cloud_python()), str(HERE / "blender_cloud.py"), "--serve",
                                         str(self.queue),
                                         "--who", self.who, "--classes", ",".join(self.classes),
                                         "--minutes", str(self.minutes)])
        return self

    def run(self, script, arguments, inputs, outputs, minutes=10, env=None):
        """One job on the held machine (a Blender script, or with `env` a script in the Python that env script
        builds); returns when its outputs are back, raises when it or the machine failed."""
        self.count += 1
        job = self.queue / f"{self.count}.json"
        job.write_text(json.dumps(job_of(script, arguments, inputs, outputs, minutes, env), indent=1))
        while True:
            if job.with_suffix(".done").exists():
                return
            if job.with_suffix(".failed").exists():
                raise RuntimeError(f"the cloud Blender job failed: {job.with_suffix('.failed').read_text()}")
            if self.process.poll() is not None:
                raise RuntimeError(f"the cloud Blender machine for {self.queue} ended before {job.name} ran")
            time.sleep(2)

    def __exit__(self, *_):
        (self.queue / "close").write_text("")
        self.process.wait()


def run_elsewhere(script, arguments, inputs, outputs, classes, who, minutes=10):
    """For a tool on this PC: run one Blender script on a rented machine (a call of this file), its outputs back
    where they belong; raises when the run fails."""
    folder = batch.BATCHES / "requests"
    folder.mkdir(parents=True, exist_ok=True)
    job_path = folder / f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}-{threading.get_ident()}.json"
    job_path.write_text(json.dumps(job_of(script, arguments, inputs, outputs, minutes), indent=1))
    command = [str(cloud_python()), str(HERE / "blender_cloud.py"), str(job_path), "--who", who,
               "--classes", ",".join(classes)]
    if subprocess.run(command).returncode != 0:
        raise RuntimeError(f"the cloud Blender run failed: {shlex.join(command)}")


# The Kubernetes path (SCORE_CLOUD=k8s): the same jobs run as Kubernetes Jobs of the blender image
# (tools/cloud/images/blender/), through tools/cloud/k8s/cluster_jobs.py, with the outputs at the same paths.
CLUSTER_KERNELS = "blender-5.0.1"


def cluster_job(job, classes):
    """One job as the cluster runs it: the script in the image's Blender from the job's code, its output folders
    made first, Cycles on the card on card classes (with the image's kernel cache), on the cores otherwise."""
    card = any(provider.cards(name) for name in classes)
    parents = sorted({str(pathlib.Path(local).resolve().parent) for local in job.get("outputs", ())})
    line = (f"mkdir -p {shlex.join(parents)} && " if parents else "") + script_line(job, ".", "/opt/blender/blender")
    found = {"command": ["sh", "-c", line], "code": shipped([job]), "inputs": list(job.get("inputs", ())),
             "outputs": list(job.get("outputs", ())), "minutes": float(job.get("minutes", 10)),
             "env": {"FARM_CYCLES_GPU" if card else "FARM_CYCLES_CPU": "1"}}
    if card:
        found["kernel_cache"] = CLUSTER_KERNELS
    return found


def cluster_jobs_module():
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import cluster_jobs

    return cluster_jobs


def run_on_cluster(jobs, classes, who):
    """The jobs on the cluster as one run; the numbers of those that failed."""
    return cluster_jobs_module().run(KIND, [cluster_job(job, classes) for job in jobs], who, classes,
                                     image="blender")


def serve_on_cluster(queue, classes, who, idle_minutes):
    """--serve on the cluster: each job written to `queue` run in turn as a run of its own (`<n>.done` or
    `<n>.failed` beside it), until the queue is closed and empty or nothing came for `idle_minutes`. The cluster's
    node stays warm between them while they come within its scale-down time."""
    (queue / "ready").write_text(",".join(classes))
    last = time.time()
    while True:
        waiting = waiting_jobs(queue)
        if not waiting:
            if (queue / "close").exists() or time.time() - last > idle_minutes * 60:
                return
            time.sleep(2)
            continue
        began = time.time()
        if run_on_cluster([json.loads(waiting[0].read_text())], classes, who):
            waiting[0].with_suffix(".failed").write_text("the cluster job failed; its log is in the store")
        else:
            waiting[0].with_suffix(".done").write_text(str(round(time.time() - began, 1)))
        last = time.time()


def main_on_cluster(options, jobs, classes):
    """main() under SCORE_CLOUD=k8s."""
    if options.dry_run:
        batch.say(f"{len(jobs)} Blender jobs for the cluster, classes {', '.join(classes)}")
        return
    if options.serve:
        serve_on_cluster(options.serve, classes, options.who, IDLE_MINUTES)
        return
    left = run_on_cluster(jobs, classes, options.who)
    for number, job in enumerate(jobs):
        if number not in left:  # the run brings every output back at once: a job's peers are all that share one
            kept.keep(job, system(), peers=kept.peers_of(job, [other for other in jobs if other is not job], system()))
    if left:
        raise SystemExit(f"Blender jobs {', '.join(map(str, left))} failed on the cluster")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("jobs", nargs="*", type=pathlib.Path)
    parser.add_argument("--serve", type=pathlib.Path, help="hold one machine for the jobs written to this queue folder")
    parser.add_argument("--minutes", type=float, default=SERVE_MINUTES, help="--serve: the chain's expected minutes")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    parser.add_argument("--classes", help="capability classes in order, comma separated: the first the "
                        "run's warm pool holds, else the first in stock, else the first sold")
    parser.add_argument(detached.FLAG, action="store_true", help="progress to a log, one result line at the end")
    options = parser.parse_args()
    if not options.jobs and not options.serve and not options.dry_run:
        # a caller with nothing left to send (surfaces-bake@people, every take a gap, 2026-10-22) rented a card
        # that failed its set-up on the held machine's job, which has no script
        batch.say("no jobs: nothing rented")
        return
    jobs = [json.loads(path.read_text()) for path in options.jobs] or [{"minutes": options.minutes}]
    if options.detach:
        detached.relaunch(sys.argv, "blender-cloud", [output for job in jobs for output in job.get("outputs", [])])
    if options.jobs:
        jobs = still_to_run(jobs)
        if not jobs:
            return
        refused = too_big_here(jobs)
        if refused:
            raise SystemExit(refused)
    classes = options.classes.split(",") if options.classes else DEFAULT_CLASSES
    if provider.on_cluster():
        main_on_cluster(options, jobs, classes)
        return
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(jobs, account, classes)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime("blender-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = pictures.Run(run_folder, started + allowed_minutes * 60)
    left = []
    try:
        if options.serve:
            machines = pictures.rent_machines(run, account, found, 1, kind=KIND)
            if not machines:
                (options.serve / "failed").write_text("no machine could be rented")
                raise SystemExit("no machine could be rented")
            serve(run, machines[0], options.serve, IDLE_MINUTES)
        else:
            left = run_spread(run, account, found, count, jobs)
            if not run.machines:
                raise SystemExit("no machine could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run_folder.name,
                 "kind": KIND, "who": options.who, "jobs": [job.get("script", "a held machine") for job in jobs],
                 "classes": list(classes), "class": found[0].machine_class,
                 **ledger.machines_record(run.machines, run.attempts, started),
                 "wall_minutes": (time.time() - started) / 60}
        ledger.record(entry)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        batch.say(f"blender: {len(jobs)} jobs in {entry['wall_minutes']:.1f} min on {len(entry['machines'])} machines, "
                  f"€{entry['euros']:.2f}")
    if left:
        raise SystemExit(f"Blender jobs {', '.join(map(str, left))} failed or never ran (logs under {run_folder})")


if __name__ == "__main__":
    main()
