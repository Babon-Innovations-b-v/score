"""Run Infinigen jobs on one rented Scaleway processor machine, bring their outputs back, delete the machine.
Nothing Infinigen runs on this PC (it ran here once beside a gate and a Blender, and WSL died, 2026-10-05).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/infinigen.py <job folder> [...] --who "<session>" \
        [--type POP2-32C-128G] [--hold] [--dry-run]

Each job folder holds spec.json, written by tools/props/infinigen/steer.py, and the arrays it names. Up there every
job runs side by side as `patch.py <spec.json> <out>` under Infinigen's own Python (infinigen_setup.sh builds it from
vendor/infinigen), and its out/ folder comes back into the job folder with its run.log as it finishes. --hold keeps
the machine after the jobs, for hands-on work over ssh, until the run folder holds a file named `release` (never
past the batch's time limit). The owner's limits, the watchdog, the self-delete, the sweep and the delete are
batch.py's, as for every machine.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import pictures  # noqa: E402
import scaleway  # noqa: E402
from paths import REPO  # noqa: E402

VENDORED = REPO / "vendor" / "infinigen"
REMOTE = pathlib.PurePosixPath("/root")
# 32 processors and 128 GB: four jobs of up to ~24 GB side by side (the 2023 paper: about 24 GB a whole scene).
MACHINE = "POP2-32C-128G"
# Measured 2026-10-05: renting, the packages, the bpy wheel and the terrain build.
SETUP_MINUTES = 20
# A job's estimate when its spec names none.
JOB_MINUTES = 60
POLL_SECONDS = 30


def offers(machine_type):
    """Where `machine_type` is sold, best stocked first: batch.offers' tuples."""
    found = []
    for zone in scaleway.ZONES:
        stock = scaleway.stock(machine_type, zone)
        if stock is None or stock == "shortage":
            continue
        price = scaleway.euros_per_minute(machine_type, zone)
        found.append((price, batch.STOCK_ORDER.get(stock, 3), machine_type, zone, price))
        batch.say(f"{machine_type} in {zone}: {stock}, €{price * 60:.2f} an hour (Scaleway's price list)")
    return sorted(found, key=lambda offer: (offer[1], offer[0]))


def estimate(jobs, hold, at_once):
    """Minutes the run is expected to take: the setup, then the jobs `at_once` side by side."""
    minutes = [json.loads((job / "spec.json").read_text()).get("minutes", JOB_MINUTES) for job in jobs]
    return SETUP_MINUTES + max(max(minutes, default=0), sum(minutes) / at_once) + (60 if hold else 0)


def price(jobs, machine_type, project, hold, at_once):
    """Print the estimate and refuse what passes the owner's limits; the offers and the allowed minutes."""
    found = offers(machine_type)
    if not found:
        raise SystemExit(f"no {machine_type} is in stock in {', '.join(scaleway.ZONES)}")
    minutes = estimate(jobs, hold, at_once)
    dearest = max(offer[0] for offer in found)
    spent = max(scaleway.month_spend(project), ledger.month_total(ledger.this_month(), ledger.entries()))
    batch.say(f"{len(jobs)} Infinigen jobs on one {machine_type}: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest):.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest, spent)


def set_up(folder, host):
    """Put Infinigen and our tools on the machine and build Infinigen there."""
    batch.remote(folder, host, f"mkdir -p {REMOTE}/infinigen {REMOTE}/repo/tools {REMOTE}/jobs", check=True)
    batch.copy(folder, [f"{VENDORED}/"], f"root@{host}:{REMOTE}/infinigen/")
    batch.copy(folder, [REPO / "tools" / "props"], f"root@{host}:{REMOTE}/repo/tools/", "--exclude", "__pycache__")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, f"bash {REMOTE}/repo/tools/props/cloud/infinigen_setup.sh", check=True,
                     stdout=log, stderr=subprocess.STDOUT)


def job_line(name):
    """The shell line that runs one job detached, leaving its exit code beside its log."""
    job = REMOTE / "jobs" / name
    run = (f"cd {REMOTE}/infinigen && /root/venv/bin/python {REMOTE}/repo/tools/props/infinigen/patch.py "
           f"{job}/spec.json {job}/out > {job}/run.log 2>&1; echo $? > {job}/exit")
    return f"setsid -f bash -c {json.dumps(run)} < /dev/null > /dev/null 2>&1"


def start_job(folder, host, job):
    batch.copy(folder, [job / "spec.json", *sorted(job.glob("*.npy")), *sorted(job.glob("*.npz"))],
               f"root@{host}:{REMOTE}/jobs/{job.name}/")
    batch.remote(folder, host, job_line(job.name), check=True)
    batch.say(f"started {job.name}")


def bring_back(folder, host, job, tries=3):
    """Copy a job's out folder and log back, trying again on a busy machine's refused ssh."""
    for attempt in range(tries):
        try:
            batch.copy(folder, [f"root@{host}:{REMOTE}/jobs/{job.name}/out/", ], f"{job / 'out'}/")
            batch.copy(folder, [f"root@{host}:{REMOTE}/jobs/{job.name}/run.log"], f"{job}/")
            return
        except subprocess.CalledProcessError:
            if attempt == tries - 1:
                raise
            time.sleep(POLL_SECONDS)


def exit_code(folder, host, job):
    """The job's exit code, or None while it runs."""
    answer = batch.remote(folder, host, f"cat {REMOTE}/jobs/{job.name}/exit 2>/dev/null", capture_output=True,
                          text=True)
    return int(answer.stdout) if answer.stdout.strip().lstrip("-").isdigit() else None


def run_jobs(run, folder, host, jobs, at_once):
    """Run the jobs, at most `at_once` side by side, bringing each back as it ends; their exit codes by name.
    Ten jobs at once on 16 processors (a load of 78) starved the machine's ssh, 2026-10-06."""
    ended, waiting, running = {}, list(jobs), []
    while (waiting or running) and time.time() < run.deadline:
        while waiting and len(running) < at_once:
            job = waiting.pop(0)
            start_job(folder, host, job)
            running.append(job)
        for job in list(running):
            code = exit_code(folder, host, job)
            if code is not None:
                (job / "out").mkdir(exist_ok=True)
                bring_back(folder, host, job)
                ended[job.name] = code
                running.remove(job)
                batch.say(f"{job.name} ended with {code} after {(time.time() - run.started) / 60:.0f} min")
        time.sleep(POLL_SECONDS)
    return ended


def hold(run, host):
    """Keep the machine for hands-on work until the run folder holds `release` or the time limit."""
    batch.say(f"holding the machine at root@{host} (key {batch.KEY}); touch {run.folder / 'release'} to let it go")
    while not (run.folder / "release").exists() and time.time() < run.deadline:
        time.sleep(POLL_SECONDS)


def work_on(run, machine, jobs, holding, at_once):
    """One machine from boot to delete; the jobs' exit codes."""
    folder = machine["folder"]
    stop = threading.Event()
    try:
        host = machine["host"]
        batch.arm_self_delete(folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(folder, host, stop), daemon=True).start()
        (run.folder / "host").write_text(host)
        try:
            set_up(folder, host)
        except subprocess.CalledProcessError:
            if not holding:
                raise
            batch.say(f"the setup failed (see {folder / 'setup.log'}); holding the machine to mend it by hand")
            hold(run, host)
            return {}
        batch.say(f"set up after {(time.time() - machine['created']) / 60:.1f} min")
        ended = run_jobs(run, folder, host, jobs, at_once)
        if holding:
            hold(run, host)
        return ended
    finally:
        stop.set()
        batch.delete_machine(machine)


def record(run, machine, jobs, ended):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(run.started)), "batch": run.folder.name,
             "kind": "infinigen", "jobs": {job.name: ended.get(job.name) for job in jobs},
             **ledger.machines_record([machine], run.attempts, run.started),
             "wall_minutes": (time.time() - run.started) / 60}
    ledger.record(entry)
    batch.say(f"infinigen: {entry['wall_minutes']:.0f} min, €{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("jobs", nargs="*", type=pathlib.Path, help="job folders, each holding spec.json")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--type", default=MACHINE, help="the Scaleway processor machine")
    parser.add_argument("--hold", action="store_true", help="keep the machine for ssh work until `release`")
    parser.add_argument("--at-once", type=int, default=4, help="jobs side by side (default 4)")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    jobs = [job.resolve() for job in options.jobs]
    for job in jobs:
        if not (job / "spec.json").exists():
            raise SystemExit(f"{job} holds no spec.json")
    project = scaleway.project_id()
    batch.sweep(project)
    found, allowed_minutes = price(jobs, options.type, project, options.hold, options.at_once)
    if options.dry_run:
        return
    scaleway.allow_key(project, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    run = pictures.Run(batch.BATCHES / time.strftime("infinigen-%Y%m%d-%H%M%S"), time.time() + allowed_minutes * 60)
    run.started = time.time()
    run.folder.mkdir(parents=True)
    batch.say(f"run folder {run.folder} ({options.who})")
    machine, ended = None, {}
    try:
        machine = batch.claim(run, project, found, 1)
        if machine is None:
            raise SystemExit(f"no {options.type} could be rented")
        ended = work_on(run, machine, jobs, options.hold, options.at_once)
    finally:
        for rented in run.machines:
            batch.delete_machine(rented)
        if machine:
            record(run, machine, jobs, ended)


if __name__ == "__main__":
    main()
