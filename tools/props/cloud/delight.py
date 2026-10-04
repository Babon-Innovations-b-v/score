"""Make an unlit paint copy of pictures on one rented Scaleway card, then delete the machine.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/delight.py <picture.png>... [--dry-run]

A picture asked for "studio light" carries that light in its pixels, and Pixel Match copies those
pixels onto every surface the picture sees: a lit front on an unlit back. Marigold-IID appearance
v1-1 (prs-eth, CreativeML Open RAIL++-M, commercial use allowed) takes the light out and gives the
paint alone, aligned with the picture pixel for pixel. Each copy comes back as
WORK/unlit/<stem>.png, with its roughness and metal beside it; `clean_finish.unlit_views` then
puts one into a model's camera folder, so Pixal3D still builds from the shaded picture and only
the paint comes from the unlit one. Renting, the owner's limits and deleting are batch.py's.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import scaleway  # noqa: E402
from paths import WORK  # noqa: E402

UNLIT = WORK / "unlit"
# First guesses until a run is measured: setup (a Python, then the model's weights) and a picture
# worked at 1024 with four predictions averaged, on an L4.
SETUP_MINUTES = 8
SECONDS_A_PICTURE = 30


def to_make(paths):
    """The pictures asked for that have no unlit copy yet, checked to exist."""
    wanted = []
    for path in map(pathlib.Path, paths):
        if not path.is_file():
            raise SystemExit(f"no picture at {path}")
        if not (UNLIT / path.name).exists():
            wanted.append(path)
    return wanted


def expected_minutes(count):
    return SETUP_MINUTES + count * SECONDS_A_PICTURE / 60


def price(count, project):
    """Print the estimate and refuse what passes the owner's limits; the offers, and the minutes
    the machine may run."""
    found = batch.offers(list(batch.TYPES[:1]))
    if not found:
        raise SystemExit("no L4 card is sold in the zones used")
    minutes = expected_minutes(count)
    dearest = max(offer[0] for offer in found)
    spent = max(scaleway.month_spend(project), ledger.month_total(ledger.this_month(), ledger.entries()))
    batch.say(f"{count} unlit copies on one card: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest):.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest, spent)


def set_up(folder, host, wanted):
    """Put the pictures and the scripts on the machine, and install the model."""
    batch.remote(folder, host, "mkdir -p /root/unlit/in /root/unlit/out", check=True)
    batch.copy(folder, wanted, f"root@{host}:/root/unlit/in/")
    batch.copy(folder, [HERE / "delight_worker.py", HERE / "delight_setup.sh"], f"root@{host}:/root/unlit/")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, "bash /root/unlit/delight_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def work(run, machine, wanted):
    """Run the machine from boot to delete: set it up, make the copies, bring them back."""
    import pictures  # loads the picture model's libraries, so only once a machine is rented
    folder = machine["folder"]
    stop = threading.Event()
    try:
        host = batch.wait_for_machine(folder, machine["id"], machine["zone"])
        batch.arm_self_delete(folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(folder, host, stop), daemon=True).start()
        set_up(folder, host, wanted)
        batch.say(f"{folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        with (folder / "unlit.log").open("w") as log:
            batch.remote(folder, host, "/root/venv/bin/python /root/unlit/delight_worker.py",
                         check=True, stdout=log, stderr=subprocess.STDOUT)
        UNLIT.mkdir(parents=True, exist_ok=True)
        batch.copy(folder, [f"root@{host}:/root/unlit/out/"], UNLIT)
        machine["made"] = sum((UNLIT / path.name).exists() for path in wanted)
    except Exception as error:  # noqa: BLE001 - the machine is deleted below whatever failed
        batch.say(f"{folder.name} failed: {error}")
    finally:
        stop.set()
        batch.delete_machine(machine)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pictures", nargs="+")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    wanted = to_make(options.pictures)
    if not wanted:
        raise SystemExit(f"every picture already has its unlit copy in {UNLIT}")
    project = scaleway.project_id()
    batch.sweep(project)
    found, allowed_minutes = price(len(wanted), project)
    if options.dry_run:
        return
    import pictures  # loads the picture model's libraries, so only once something will be rented
    scaleway.allow_key(project, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"unlit-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = pictures.Run(folder, started + allowed_minutes * 60)
    machines = []
    try:
        machines = pictures.rent_machines(run, project, found, 1)
        if machines:
            work(run, machines[0], wanted)
    finally:
        for machine in machines:
            batch.delete_machine(machine)
        pictures.record(run, machines, wanted, started)


if __name__ == "__main__":
    main()
