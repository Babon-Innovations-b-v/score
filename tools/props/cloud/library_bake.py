"""Bake the material library onto kit pieces, and render its swatches, on one rented Scaleway card; bring the
results back; delete the machine (job robust-exp, 2026-10-06: after a local bake took every core and WSL crashed, the
coordinator moved every Blender bake to the cloud).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/library_bake.py <job.json> [<job.json> ...] \
        --who "<session>" [--dry-run]

Each job is one of tools/props/library/inside/'s: it names its `script` (make_kit.py, make_chunky.py, show.py or
swatch.py) and its `out` folder; a make_chunky job's pieces name their `parts` folders (labels.py). Up there Blender
5.0.1 (the version this repo's tools pin, checked against blender.org's sha256) runs each job with `-b` and Cycles on
the card (FARM_CYCLES_GPU), with ProcFunc and infinigen2's shaders from the repo's vendored copies; each job's `out`
comes back to where it says. The owner's limits, the self-delete, the watchdog and the delete are batch.py's.
"""
import argparse
import json
import pathlib
import shlex
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import scaleway  # noqa: E402
from paths import REPO  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/lib")
SETUP_MINUTES = 10
# Processor machines tried in turn when no card is in stock (their stock moves by the minute, 2026-10-06).
PROCESSORS = ("POP2-32C-128G", "POP2-HC-32C-64G", "POP2-HM-32C-256G", "POP2-16C-64G")
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


def machine_offers(processor):
    """Where the job can run: an L4 card, or (with --processor, when no card is in stock) a 32-core processor
    machine, where Cycles bakes on the processor at about a third of a card's speed."""
    if processor:
        import infinigen

        return [offer for machine in PROCESSORS for offer in infinigen.offers(machine)]
    return batch.offers(list(batch.TYPES[:1]))


def price(jobs, project, processor):
    """Print the estimate and refuse what passes the owner's limits; the offers and allowed minutes."""
    found = machine_offers(processor)
    if not found:
        raise SystemExit(f"no {'processor machine' if processor else 'L4 card'} is sold in the zones used")
    minutes = SETUP_MINUTES + sum(card_minutes(job) for job in jobs) * (PROCESSOR_SLOWER if processor else 1)
    dearest = max(offer[0] for offer in found)
    spent = max(scaleway.month_spend(project), ledger.month_total(ledger.this_month(), ledger.entries()))
    batch.say(f"{len(jobs)} library jobs on one card: about {minutes:.0f} min, €{ledger.cost(minutes, dearest):.2f}; "
              f"€{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest, spent)


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


def run_line(script, job_path, processor):
    blender = ["/root/blender/blender", "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
               str(REMOTE / "repo/tools/props/library/inside" / script), "--", str(job_path)]
    card = "" if processor else "FARM_CYCLES_GPU=1 "
    return f"cd /root && env {card}PROPS_HOME=/root/props {shlex.join(blender)}"


def work_on(run, machine, jobs, processor):
    """One machine from boot to delete: Blender and the library up, every job run, every out folder back."""
    import pictures
    log_folder = machine["folder"]
    stop = threading.Event()
    try:
        host = batch.wait_for_machine(log_folder, machine["id"], machine["zone"])
        batch.arm_self_delete(log_folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(log_folder, host, stop), daemon=True).start()
        for shipped in SHIPPED:
            parent = (REMOTE / "repo" / shipped).parent
            batch.remote(log_folder, host, f"mkdir -p {parent}", check=True)
            batch.copy(log_folder, [REPO / shipped], f"root@{host}:{parent}/", "--exclude", "__pycache__")
        batch.copy(log_folder, [HERE / "library_setup.sh"], f"root@{host}:{REMOTE}/")
        with (log_folder / "setup.log").open("w") as log:
            batch.remote(log_folder, host, f"bash {REMOTE}/library_setup.sh", check=True, stdout=log,
                         stderr=subprocess.STDOUT)
        batch.say(f"{log_folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        for number, job in enumerate(jobs):
            moved, sends = remote_job(job, number)
            for local, place in sends:
                batch.remote(log_folder, host, f"mkdir -p {place}", check=True)
                files = local if isinstance(local, list) else sorted(
                    found for found in local.iterdir() if found.is_file() and found.name != "labels.json")
                batch.copy(log_folder, files, f"root@{host}:{place}/")
            job_path = REMOTE / f"job{number}.json"
            # Paths into this checkout (a variant's picture) point into the machine's copy of it.
            (log_folder / f"job{number}.json").write_text(json.dumps(moved).replace(str(REPO), str(REMOTE / "repo")))
            batch.copy(log_folder, [log_folder / f"job{number}.json"], f"root@{host}:{job_path}")
            began = time.time()
            try:
                with (log_folder / f"job{number}.log").open("w") as log:
                    batch.remote(log_folder, host, run_line(job["script"], job_path, processor), check=True, stdout=log,
                                 stderr=subprocess.STDOUT)
            finally:
                pathlib.Path(job["out"]).mkdir(parents=True, exist_ok=True)
                batch.copy(log_folder, [f"root@{host}:{moved['out']}/"], f"{job['out']}/")
                batch.say(f"library job {number} ({job['script']}): {(time.time() - began) / 60:.1f} min")
    finally:
        stop.set()
        batch.delete_machine(machine)


def record(run, machines, started, jobs):
    rows = [{"type": machine["type"], "zone": machine["zone"],
             "minutes": (machine["deleted"] - machine["created"]) / 60,
             "euros": ledger.cost((machine["deleted"] - machine["created"]) / 60, machine["price"])}
            for machine in machines]
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": "library", "jobs": [job["out"] for job in jobs], "machines": rows,
             "euros": sum(row["euros"] for row in rows), "machine_minutes": sum(row["minutes"] for row in rows),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"library: {entry['wall_minutes']:.0f} min on {len(rows)} machine, €{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("jobs", nargs="+", type=pathlib.Path)
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    parser.add_argument("--processor", action="store_true", help="a processor machine, when no card is in stock")
    options = parser.parse_args()
    jobs = [json.loads(path.read_text()) for path in options.jobs]
    project = scaleway.project_id()
    batch.sweep(project)
    found, allowed_minutes = price(jobs, project, options.processor)
    if options.dry_run:
        return
    scaleway.allow_key(project, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures
    started = time.time()
    run_folder = batch.BATCHES / time.strftime("library-%Y%m%d-%H%M%S")
    run_folder.mkdir(parents=True)
    run = pictures.Run(run_folder, started + allowed_minutes * 60)
    machines = []
    try:
        machines = pictures.rent_machines(run, project, found, 1)
        if not machines:
            raise SystemExit("no card could be rented")
        work_on(run, machines[0], jobs, options.processor)
    finally:
        for machine in machines:
            batch.delete_machine(machine)
        entry = record(run, machines, started, jobs)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        print(json.dumps(entry))


if __name__ == "__main__":
    main()
