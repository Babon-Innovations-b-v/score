"""Make a whole list of pictures on rented Scaleway graphics cards, then delete the machines.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/pictures.py <jobs.json> [--cards 5] [--dry-run]

The list is picture.py's own (--list): a JSON array of {"name", "sentence", "seed", "form", "refs"}.
Every job is worded here by picture.wording, at picture.py's steps and guidance, so a picture made
up there is the one the owner's card would make. The list is split evenly over --cards machines; each
installs the picture model from Hugging Face, holds it on its card whole (no offloading) and draws
its share, and the pictures come back into WORK/pictures. A picture already there is skipped.
Renting, the owner's limits and deleting are batch.py's.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import picture  # noqa: E402
import scaleway  # noqa: E402
from paths import PICTURES  # noqa: E402

CARDS = 5
# First guesses for the estimate, until a run is measured: setup (a Python, then 15 GB of weights)
# and a picture drawn with the model held whole on an L4.
SETUP_MINUTES = 8
SECONDS_A_PICTURE = 4


class Run:
    """What `batch.rent` needs of a run: its folder and when every machine must be gone."""

    def __init__(self, folder, deadline):
        self.folder = folder
        self.deadline = deadline


def jobs_to_make(path):
    """The list's pictures not yet made, each worded as picture.py would word it."""
    jobs = []
    for job in json.loads(pathlib.Path(path).read_text()):
        if (PICTURES / f"{job['name']}.png").exists():
            continue
        # A job may carry its whole wording, for a picture that is not an object on its own (a
        # flat facade to tile); otherwise it is worded as picture.py words an object.
        jobs.append({"name": job["name"],
                     "wording": job.get("wording")
                     or picture.wording(job["sentence"], job.get("form") or picture.FORM),
                     "seed": job.get("seed", 7), "steps": picture.STEPS, "guidance": picture.GUIDANCE,
                     "refs": [str(ref) for ref in job.get("refs", [])]})
    return jobs


def expected_minutes(count, cards):
    return SETUP_MINUTES + count / cards * SECONDS_A_PICTURE / 60


def price(jobs, cards, project):
    """Print the estimate and refuse what passes the owner's limits; the offers, and the minutes the
    machines may run."""
    found = batch.offers(list(batch.TYPES[:1]))
    if not found:
        raise SystemExit("no L4 card is sold in the zones used")
    minutes = expected_minutes(len(jobs), cards)
    dearest = max(offer[0] for offer in found)
    spent = max(scaleway.month_spend(project), ledger.month_total(ledger.this_month(), ledger.entries()))
    batch.say(f"{len(jobs)} pictures on {cards} cards: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * cards:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * cards, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest * cards, spent)


def rent_machines(run, project, found, cards):
    """Rent up to `cards` machines, cheapest offer first; the machines rented."""
    machines, remaining = [], list(found)
    for number in range(1, cards + 1):
        machine = None
        while machine is None and remaining:
            machine = batch.rent(run, project, remaining[0], number)
            if machine is None:
                remaining.pop(0)
        if machine is None:
            break
        machines.append(machine)
    return machines


def set_up(folder, host, share):
    """Put the share, its reference photos and the scripts on the machine, and install the model."""
    batch.remote(folder, host, "mkdir -p /root/pics/refs /root/pics/out", check=True)
    refs = sorted({ref for job in share for ref in job["refs"]})
    if refs:
        batch.copy(folder, refs, f"root@{host}:/root/pics/refs/")
    up = [dict(job, refs=[pathlib.Path(ref).name for ref in job["refs"]]) for job in share]
    (folder / "jobs.json").write_text(json.dumps(up))
    batch.copy(folder, [folder / "jobs.json", HERE / "picture_worker.py", HERE / "picture_setup.sh"],
               f"root@{host}:/root/pics/")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, "bash /root/pics/picture_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def draw_share(machine, share):
    """Run one machine from boot to delete: set it up, draw its share, bring the pictures back."""
    folder = machine["folder"]
    try:
        host = batch.wait_for_machine(folder, machine["id"], machine["zone"])
        set_up(folder, host, share)
        batch.say(f"{folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        with (folder / "draw.log").open("w") as log:
            batch.remote(folder, host, "/root/venv/bin/python /root/pics/picture_worker.py "
                         "/root/pics/jobs.json", check=True, stdout=log, stderr=subprocess.STDOUT)
        batch.copy(folder, [f"root@{host}:/root/pics/out/"], folder / "out")
        for made in (folder / "out").glob("*.png"):
            shutil.copy2(made, PICTURES / made.name)
        machine["made"] = len(list((folder / "out").glob("*.png")))
    except Exception as error:  # noqa: BLE001 - one machine failing must not stop the others
        batch.say(f"{folder.name} failed: {error}")
    finally:
        batch.delete_machine(machine)


def record(run, machines, jobs, started):
    """Write the run to the ledger and say what it made and cost."""
    rows = [{"type": machine["type"], "zone": machine["zone"],
             "minutes": (machine["deleted"] - machine["created"]) / 60,
             "euros": ledger.cost((machine["deleted"] - machine["created"]) / 60, machine["price"]),
             "made": machine.get("made", 0)} for machine in machines]
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
             "batch": run.folder.name, "kind": "pictures", "machines": rows, "pictures": len(jobs),
             "euros": sum(row["euros"] for row in rows),
             "machine_minutes": sum(row["minutes"] for row in rows),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"{sum(row['made'] for row in rows)} of {len(jobs)} pictures in "
              f"{entry['wall_minutes']:.0f} min on {len(rows)} machines, €{entry['euros']:.2f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("list")
    parser.add_argument("--cards", type=int, default=CARDS)
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    jobs = jobs_to_make(options.list)
    if not jobs:
        raise SystemExit("every picture in the list is already made")
    project = scaleway.project_id()
    batch.sweep(project)
    cards = min(options.cards, len(jobs))
    found, allowed_minutes = price(jobs, cards, project)
    if options.dry_run:
        return
    scaleway.allow_key(project, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"pictures-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = Run(folder, started + allowed_minutes * 60)
    machines = []
    try:
        machines = rent_machines(run, project, found, cards)
        threads = [threading.Thread(target=draw_share, args=(machine, jobs[index::len(machines)]))
                   for index, machine in enumerate(machines)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        for machine in machines:
            batch.delete_machine(machine)
        record(run, machines, jobs, started)


if __name__ == "__main__":
    main()
