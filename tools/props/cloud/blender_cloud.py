"""Run headless Blender scripts on a rented cloud machine: send their input files, run each, bring their outputs back,
delete the machine. The generic Blender job (2026-10-08, BLENDER IN THE CLOUD): the local Blender lock lets one
Blender run on the owner's PC at a time, so renders, settling and review pages run here, many machines at once.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/blender_cloud.py <job.json> [<job.json> ...] \
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
     "minutes": 5}   about how long it runs on the machine

Every input and output lies at the same absolute path on the machine as here, so a script, its arguments and the paths
inside its input files (a review page's shots.json names the model files) need no change to run up there. The script's own
folder and tools/blender/inside go up with it. The jobs of one call are spread over as many machines as finish them
in about the setup and the longest job (spread.py, capacity.machines_for): one machine for a short list, one a job for
a long one, each set up once and taking the next job as it ends one.
Classes: a processor machine for physics (settling: cpu-32c-128gb first,
the default), a card for renders (`--classes gpu-24gb`, Cycles on the card; on a processor machine Cycles renders on
its cores: FARM_CYCLES_GPU or FARM_CYCLES_CPU is set for the script). Blender is 5.0.1 from
blender.org, set up by library_setup.sh. The owner's limits, the self-delete, the watchdog, the delete and the ledger
are batch.py's.

Under SCORE_CLOUD=k8s the same calls run each job as a Kubernetes Job of the blender image on the cluster
(tools/cloud/k8s/cluster_jobs.py), inputs and outputs at the same paths; the machines stay the default.
"""
import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import detached  # noqa: E402
import ledger  # noqa: E402
import park  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402
from paths import HOME, REPO  # noqa: E402
from provider import cloud  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/lib")
SETUP_MINUTES = 8
KIND = "blender"
# Settling and other physics: the processor machines, tried in turn as their stock moves.
DEFAULT_CLASSES = ("cpu-32c-128gb", "cpu-32c-64gb", "cpu-32c-256gb", "cpu-16c-64gb")
ALWAYS_SHIPPED = ("tools/blender/inside",)
# A held machine (--serve): the chain's expected minutes for the owner's limits, and how long it waits for the next job.
SERVE_MINUTES = 60
IDLE_MINUTES = 10


def run_line(job, card):
    """The command that runs a job's script on the machine."""
    arguments = [str(argument) for argument in job.get("args", ())]
    blender = ["/root/blender/blender", "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
               str(REMOTE / "repo" / job["script"]), "--", *arguments]
    engine = "FARM_CYCLES_GPU=1" if card else "FARM_CYCLES_CPU=1"
    return f"cd /root && env {engine} PROPS_HOME=/root/props {shlex.join(blender)}"


def shipped(jobs):
    """The repo folders the jobs' scripts need: tools/blender/inside and each script's own folder."""
    return sorted({*ALWAYS_SHIPPED, *(str(pathlib.PurePosixPath(job["script"]).parent) for job in jobs)})


def plan(jobs):
    """How many machines the jobs are spread over (capacity.machines_for), and how long they keep them."""
    minutes = [float(job.get("minutes", 10)) for job in jobs]
    count = capacity.machines_for(len(jobs), sum(minutes) / len(minutes), SETUP_MINUTES)
    return count, SETUP_MINUTES + max(max(minutes), sum(minutes) / count)


def price(jobs, account, classes):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and the minutes
    allowed."""
    found = [offer for offer in batch.offers(list(classes)) if offer.stock_word != "shortage"]
    if not found:
        raise SystemExit(f"no machine of {', '.join(classes)} is in stock at the {cloud.NAME} backend")
    count, minutes = plan(jobs)
    what = f"{len(jobs)} Blender jobs on {count} machine{'s' if count > 1 else ''}"
    return found, count, batch.priced(found, minutes, count, what, account)


def send(log_folder, host, local):
    """One input (file or folder) to its place on the machine."""
    local = pathlib.Path(local).resolve()
    batch.remote(log_folder, host, f"mkdir -p {shlex.quote(str(local.parent))}", check=True)
    batch.copy(log_folder, [local], f"root@{host}:{local.parent}/")


def bring_back(log_folder, host, local):
    """One output (file or folder) from the machine to its own place here; a missing one is said, not raised."""
    local = pathlib.Path(local).resolve()
    local.parent.mkdir(parents=True, exist_ok=True)
    try:
        batch.copy(log_folder, [f"root@{host}:{local}"], f"{local.parent}/")
    except subprocess.CalledProcessError:
        batch.say(f"the machine wrote no {local}")


def ship(log_folder, host, jobs):
    """The repo folders the jobs need, to their places on the machine (rsync sends only what changed)."""
    for folder in shipped(jobs):
        parent = (REMOTE / "repo" / folder).parent
        batch.remote(log_folder, host, f"mkdir -p {parent}", check=True)
        batch.copy(log_folder, [REPO / folder], f"root@{host}:{parent}/", "--exclude", "__pycache__")


def set_up(log_folder, host, jobs):
    ship(log_folder, host, jobs)
    batch.copy(log_folder, [HERE / "library_setup.sh"], f"root@{host}:{REMOTE}/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"bash {REMOTE}/library_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def run_job(log_folder, host, number, job, card):
    """One job: its inputs up, its output folders made, the script run, its outputs back (also when it fails)."""
    for local in job.get("inputs", ()):
        send(log_folder, host, local)
    for local in job.get("outputs", ()):
        batch.remote(log_folder, host, f"mkdir -p {shlex.quote(str(pathlib.Path(local).resolve().parent))}",
                     check=True)
    began = time.time()
    try:
        with (log_folder / f"job{number}.log").open("w") as log:
            batch.remote(log_folder, host, run_line(job, card), check=True, stdout=log, stderr=subprocess.STDOUT)
    finally:
        for local in job.get("outputs", ()):
            bring_back(log_folder, host, local)
        batch.say(f"Blender job {number} ({job['script']}): {(time.time() - began) / 60:.1f} min")
    return round(time.time() - began, 1)


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
                seconds = run_job(log_folder, host, int(waiting[0].stem), job, card)
                machine.setdefault("unit_seconds", []).append(seconds)
                waiting[0].with_suffix(".done").write_text(str(seconds))
            except subprocess.CalledProcessError as failed:
                waiting[0].with_suffix(".failed").write_text(f"{failed}; log: {log_folder}/job{waiting[0].stem}.log")
            last = time.time()


def one_job(machine, share, card):
    """One of a spread run's jobs on a machine: a script that fails raises spread.JobFailed, a machine that stops
    answering a ConnectionError."""
    number, job = share
    log_folder, host = machine["folder"], machine["host"]
    touched(machine, job)
    try:
        machine.setdefault("unit_seconds", []).append(run_job(log_folder, host, number, job, card is not None))
    except subprocess.CalledProcessError as failed:
        spread.raise_for(failed.returncode, f"job {number} ({job['script']}, {log_folder / f'job{number}.log'})")


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


def job_of(script, arguments, inputs, outputs, minutes):
    """A job as this file takes it."""
    return {"script": str(pathlib.Path(script).resolve().relative_to(REPO)),
            "args": [str(argument) for argument in arguments],
            "inputs": [str(path) for path in inputs], "outputs": [str(path) for path in outputs], "minutes": minutes}


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

    def run(self, script, arguments, inputs, outputs, minutes=10):
        """One job on the held machine; returns when its outputs are back, raises when it or the machine failed."""
        self.count += 1
        job = self.queue / f"{self.count}.json"
        job.write_text(json.dumps(job_of(script, arguments, inputs, outputs, minutes), indent=1))
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
    blender = ["/opt/blender/blender", "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
               job["script"], "--", *[str(argument) for argument in job.get("args", ())]]
    line = (f"mkdir -p {shlex.join(parents)} && " if parents else "") + shlex.join(blender)
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
    if left:
        raise SystemExit(f"Blender jobs {', '.join(map(str, left))} failed on the cluster")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("jobs", nargs="*", type=pathlib.Path)
    parser.add_argument("--serve", type=pathlib.Path, help="hold one machine for the jobs written to this queue folder")
    parser.add_argument("--minutes", type=float, default=SERVE_MINUTES, help="--serve: the chain's expected minutes")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    parser.add_argument("--classes", help="capability classes in the order to try, comma separated")
    parser.add_argument(detached.FLAG, action="store_true", help="progress to a log, one result line at the end")
    options = parser.parse_args()
    jobs = [json.loads(path.read_text()) for path in options.jobs] or [{"minutes": options.minutes}]
    if options.detach:
        detached.relaunch(sys.argv, "blender-cloud", [output for job in jobs for output in job.get("outputs", [])])
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
