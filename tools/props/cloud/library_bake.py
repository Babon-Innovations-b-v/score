"""Bake the material library onto kit pieces, and render its swatches, on rented cloud cards; bring the
results back; delete the machines (job robust-exp, 2026-10-06: after a local bake took every core and WSL crashed, the
coordinator moved every Blender bake to the cloud).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/library_bake.py <job.json> [<job.json> ...] \
        --who "<session>" [--classes gpu-48gb] [--dry-run]

Each job is one of tools/props/library/inside/'s: it names its `script` (make_kit.py, make_chunky.py, show.py or
swatch.py) and its `out` folder; a make_chunky job's pieces name their `parts` folders (labels.py). Up there Blender
5.0.1 (the version this repo's tools pin, checked against blender.org's sha256) runs each job with `-b` and Cycles on
the card (FARM_CYCLES_GPU), with ProcFunc and infinigen2's shaders from the repo's vendored copies; each job's `out`
comes back to where it says. The jobs are spread over as many machines as finish them in about the setup and one
job's time (spread.py), each taking the next job as it finishes one; one machine for a short list. The owner's
limits, the self-delete, the watchdog and the delete are batch.py's. Under SCORE_CLOUD=k8s the same jobs run as
Kubernetes Jobs of the blender image on the cluster (tools/cloud/k8s/cluster_jobs.py); the machines stay the default.
"""
import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import park  # noqa: E402
import provider  # noqa: E402
import spread  # noqa: E402
from provider import cloud  # noqa: E402
from paths import REPO  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/lib")
SETUP_MINUTES = 10
# Processor machines tried in turn when no card is in stock (their stock moves by the minute, 2026-10-06).
PROCESSORS = ("cpu-32c-128gb", "cpu-32c-64gb", "cpu-32c-256gb", "cpu-16c-64gb")
# Card minutes each thing a job holds takes, measured on an L4 (2026-10-06): a swatch variant at three wears and two
# views, a code-built piece, a generated piece cut down and detailed, a row of pictured pieces. A processor machine
# took about three times as long.
MINUTES_EACH = {"materials": 0.1, "pieces": 0.3, "chunky": 1.5, "rows": 0.2}
PROCESSOR_SLOWER = 3
# What of the repo the Blender side reads.
SHIPPED = ("tools/props/library", "data/library", "vendor/procfunc/src", "vendor/infinigen2")


def card_minutes(job):
    """A job's expected minutes on a card, from what it holds."""
    return sum(len(job.get(key, ())) * minutes for key, minutes in MINUTES_EACH.items())


def machine_offers(processor, classes):
    """Where the job can run: any card that holds a bake (capacity.py) or the `classes` asked for, or (with
    --processor, when no card is in stock) a 32-core processor machine, where Cycles bakes on the processor at
    about a third of a card's speed."""
    if processor:
        import infinigen

        return [offer for machine in PROCESSORS for offer in infinigen.offers(machine)]
    return batch.offers(classes or list(capacity.classes_for("library")))


def price(jobs, account, processor, classes):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and the allowed
    minutes."""
    found = machine_offers(processor, classes)
    if not found:
        raise SystemExit(f"no {'processor machine' if processor else 'card that holds a bake'} is sold by the {cloud.NAME} backend")
    slower = PROCESSOR_SLOWER if processor else 1
    each = [card_minutes(job) * slower for job in jobs]
    count = capacity.machines_for(len(jobs), sum(each) / len(each), SETUP_MINUTES)
    minutes = SETUP_MINUTES + max(max(each), sum(each) / count)
    what = f"{len(jobs)} library jobs on {count} machine{'s' if count > 1 else ''}"
    return found, count, batch.priced(found, minutes, count, what, account)


def remote_job(job, number):
    """The job with its folders moved to the machine's; the local folders to send and to bring back."""
    moved = dict(job, out=str(REMOTE / "out" / str(number)))
    sends = []
    if "chunky" in job:
        moved["chunky"] = []
        for entry in job["chunky"]:
            place = REMOTE / "in" / str(number) / entry["name"]
            sends.append((pathlib.Path(entry["parts"]), place))
            moved["chunky"].append(dict(entry, parts=str(place)))
    if "rows" in job:
        moved["rows"] = []
        for row_number, row in enumerate(job["rows"]):
            place = REMOTE / "in" / str(number) / f"row{row_number}"
            files = []
            for path in map(pathlib.Path, row["models"]):
                files.append(path)
                if path.suffix == ".gltf":  # its .bin and its shared pictures go with it
                    files += [path.with_suffix(".bin"), path.parent / "textures"]
            sends.append((sorted(set(files)), place))
            moved["rows"].append(dict(row, models=[str(place / pathlib.Path(path).name) for path in row["models"]]))
    return moved, sends


def files_of(local):
    """The files one of remote_job's sends puts up: a row's list as it is, a parts folder's files but its labels."""
    if isinstance(local, list):
        return local
    return sorted(found for found in local.iterdir() if found.is_file() and found.name != "labels.json")


def run_line(script, job_path, card):
    """The command that runs one job's script, Cycles on card number `card`, or on the processor when it is None."""
    blender = ["/root/blender/blender", "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
               str(REMOTE / "repo/tools/props/library/inside" / script), "--", str(job_path)]
    on_card = "" if card is None else f"FARM_CYCLES_GPU=1 CUDA_VISIBLE_DEVICES={card} "
    return f"cd /root && env {on_card}PROPS_HOME=/root/props {shlex.join(blender)}"


def set_up(machine):
    """Blender and the library onto one machine."""
    log_folder, host = machine["folder"], machine["host"]
    for shipped in SHIPPED:
        parent = (REMOTE / "repo" / shipped).parent
        batch.remote(log_folder, host, f"mkdir -p {parent}", check=True)
        batch.copy(log_folder, [REPO / shipped], f"root@{host}:{parent}/", "--exclude", "__pycache__")
    batch.copy(log_folder, [HERE / "library_setup.sh"], f"root@{host}:{REMOTE}/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"bash {REMOTE}/library_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def bake(machine, number, job, card):
    """One job on a machine: its inputs up, its script run, its out folder back (also when it fails). A script that
    fails raises spread.JobFailed."""
    log_folder, host = machine["folder"], machine["host"]
    moved, sends = remote_job(job, number)
    for local, place in sends:
        batch.remote(log_folder, host, f"mkdir -p {place}", check=True)
        batch.copy(log_folder, files_of(local), f"root@{host}:{place}/")
    job_path = REMOTE / f"job{number}.json"
    # Paths into this checkout (a variant's picture) point into the machine's copy of it.
    (log_folder / f"job{number}.json").write_text(json.dumps(moved).replace(str(REPO), str(REMOTE / "repo")))
    batch.copy(log_folder, [log_folder / f"job{number}.json"], f"root@{host}:{job_path}")
    began = time.time()
    try:
        with (log_folder / f"job{number}.log").open("w") as log:
            done = batch.remote(log_folder, host, run_line(job["script"], job_path, card), stdout=log,
                                stderr=subprocess.STDOUT)
    finally:
        pathlib.Path(job["out"]).mkdir(parents=True, exist_ok=True)
        batch.copy(log_folder, [f"root@{host}:{moved['out']}/"], f"{job['out']}/")
        batch.say(f"library job {number} ({job['script']}) on {log_folder.name}: {(time.time() - began) / 60:.1f} min")
    spread.raise_for(done.returncode, f"job {number} ({log_folder / f'job{number}.log'})")
    machine.setdefault("unit_seconds", []).append(round(time.time() - began, 1))


def cleanup(_machine):
    """The command that removes a run's own files from its machine before it is parked (park.py): its inputs,
    outputs and job files. Blender and the shipped repo folders stay (rsync sends only what changed)."""
    return f"rm -rf {REMOTE / 'in'} {REMOTE / 'out'} {REMOTE}/job*.json"


park.CLEANUPS["library"] = cleanup


def record(run, machines, started, jobs):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": "library", "jobs": [job["out"] for job in jobs],
             **ledger.machines_record(machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"library: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machines, "
              f"€{entry['euros']:.2f}")
    return entry


# The Kubernetes path (SCORE_CLOUD=k8s): each job a Kubernetes Job of the blender image (one environment for every
# Blender job), through tools/cloud/k8s/cluster_jobs.py; the job's files at the machine's paths, its out folder back.
CLUSTER_REPO = "/work/repo"


def cluster_job(job, number, card, job_file):
    """One bake as the cluster runs it: its inputs and job file at the machine's paths (written to `job_file` here),
    its out folder back to where the job says, Cycles on the card (with the image's kernel cache) or the cores."""
    moved, sends = remote_job(job, number)
    job_path = REMOTE / f"job{number}.json"
    job_file.write_text(json.dumps(moved).replace(str(REPO), CLUSTER_REPO))
    inputs = [{"local": str(job_file), "path": str(job_path)}]
    for local, place in sends:
        inputs += [{"local": str(file), "path": str(place / pathlib.Path(file).name)} for file in files_of(local)]
    blender = ["/opt/blender/blender", "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
               f"tools/props/library/inside/{job['script']}", "--", str(job_path)]
    found = {"command": ["sh", "-c", f"mkdir -p {moved['out']} && {shlex.join(blender)}"], "code": list(SHIPPED),
             "inputs": inputs, "outputs": [{"path": moved["out"], "local": job["out"]}],
             "minutes": max(10.0, card_minutes(job) * (1 if card else PROCESSOR_SLOWER) * 2),
             "env": {"FARM_CYCLES_GPU" if card else "FARM_CYCLES_CPU": "1"}}
    if card:
        found["kernel_cache"] = "blender-5.0.1"
    return found


def main_on_cluster(options, jobs):
    """main() under SCORE_CLOUD=k8s: the bakes as one run of the cluster, on the library's classes in its order
    (capacity.py), or a processor class with --processor, or the classes asked for."""
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import cluster_jobs

    classes = (options.classes.split(",") if options.classes else
               list(PROCESSORS) if options.processor else None)
    card = not options.processor and not (classes and not any(provider.cards(name) for name in classes))
    if options.dry_run:
        batch.say(f"{len(jobs)} library jobs for the cluster")
        return
    folder = batch.BATCHES / (time.strftime("library-k8s-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    folder.mkdir(parents=True)
    work = [cluster_job(job, number, card, folder / f"job{number}.json") for number, job in enumerate(jobs)]
    left = cluster_jobs.run("library", work, options.who, classes, image="blender")
    if left:
        raise SystemExit(f"library jobs {', '.join(map(str, left))} failed on the cluster")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("jobs", nargs="+", type=pathlib.Path)
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    parser.add_argument("--processor", action="store_true", help="a processor machine, when no card is in stock")
    parser.add_argument("--classes", help="only these capability classes, comma separated (a measuring run)")
    options = parser.parse_args()
    jobs = [json.loads(path.read_text()) for path in options.jobs]
    if provider.on_cluster():
        main_on_cluster(options, jobs)
        return
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(jobs, account, options.processor,
                                          options.classes and options.classes.split(","))
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures
    started = time.time()
    # The process number too: two bakes started in the same second (one a room, at once) took one folder and the
    # second stopped (modules round, 2026-10-08).
    run_folder = batch.BATCHES / (time.strftime("library-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = pictures.Run(run_folder, started + allowed_minutes * 60)
    shares = spread.Shares(enumerate(jobs), deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, count, "library", shares, set_up,
                           lambda machine, share, card: bake(machine, *share, card))
        if not run.machines:
            raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, run.machines, started, jobs)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        print(json.dumps(entry))
    left = sorted(number for number, _ in [*shares.failed, *shares.waiting])
    if left:
        raise SystemExit(f"library jobs {', '.join(map(str, left))} failed or never ran (logs under {run_folder})")


if __name__ == "__main__":
    main()
