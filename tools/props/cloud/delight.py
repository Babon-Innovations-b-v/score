"""Make an unlit paint copy of pictures on rented cloud cards, then delete the machines.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/delight.py <picture.png>... [--dry-run]

A picture asked for "studio light" carries that light in its pixels, and Pixel Match copies those
pixels onto every surface the picture sees: a lit front on an unlit back. Marigold-IID appearance
v1-1 (prs-eth, CreativeML Open RAIL++-M, commercial use allowed) takes the light out and gives the
paint alone, aligned with the picture pixel for pixel. Each copy comes back as
WORK/unlit/<stem>.png, with its roughness and metal beside it; `clean_finish.unlit_views` then
puts one into a model's camera folder, so Pixal3D still builds from the shaded picture and only
the paint comes from the unlit one. A long list is cut into shares over as many cards as make it in about the
setup's time (spread.py). Renting, the owner's limits and deleting are batch.py's.
"""
import argparse
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import spread  # noqa: E402
from provider import cloud  # noqa: E402
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


def machines_for(count):
    """How many cards a list of `count` pictures is spread over."""
    return capacity.machines_for(count, SECONDS_A_PICTURE / 60, SETUP_MINUTES, capacity.slots_for("unlit"))


def expected_minutes(count, machines=1):
    return capacity.spread_minutes(count, SECONDS_A_PICTURE / 60, SETUP_MINUTES, machines)


def price(count, account):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and the minutes
    they may run."""
    found = batch.offers(list(capacity.classes_for("unlit")))
    if not found:
        raise SystemExit("no card that holds this job is sold in the zones used")
    machines = machines_for(count)
    minutes = expected_minutes(count, machines)
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{count} unlit copies on {machines} card{'s' if machines > 1 else ''}: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * machines:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * machines, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, machines, ledger.minutes_allowed(dearest * machines, spent)


def set_up(machine):
    """The model and the scripts onto one machine."""
    folder, host = machine["folder"], machine["host"]
    batch.remote(folder, host, "mkdir -p /root/unlit/out", check=True)
    batch.copy(folder, [HERE / "delight_worker.py", HERE / "delight_setup.sh"], f"root@{host}:/root/unlit/")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, "bash /root/unlit/delight_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def make_share(machine, share, card):
    """One share of the pictures on one card: up into a folder of its own, every copy made, the copies back. A worker
    that fails raises spread.JobFailed (what it made still comes back)."""
    number, wanted = share
    folder, host = machine["folder"], machine["host"]
    batch.remote(folder, host, f"mkdir -p /root/unlit/in-{number}", check=True)
    batch.copy(folder, wanted, f"root@{host}:/root/unlit/in-{number}/")
    try:
        with (folder / f"unlit-{number}.log").open("w") as log:
            done = batch.remote(folder, host, f"CUDA_VISIBLE_DEVICES={card} /root/venv/bin/python "
                                f"/root/unlit/delight_worker.py /root/unlit/in-{number}", stdout=log,
                                stderr=subprocess.STDOUT)
    finally:
        UNLIT.mkdir(parents=True, exist_ok=True)
        batch.copy(folder, [f"root@{host}:/root/unlit/out/"], UNLIT)
    machine["made"] = machine.get("made", 0) + sum((UNLIT / path.name).exists() for path in wanted)
    spread.raise_for(done.returncode, f"share {number} ({folder / f'unlit-{number}.log'})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pictures", nargs="+")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    wanted = to_make(options.pictures)
    if not wanted:
        raise SystemExit(f"every picture already has its unlit copy in {UNLIT}")
    account = cloud.account()
    batch.sweep(account)
    found, machines, allowed_minutes = price(len(wanted), account)
    if options.dry_run:
        return
    import pictures  # loads the picture model's libraries, so only once something will be rented
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"unlit-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = pictures.Run(folder, started + allowed_minutes * 60)
    parts = min(len(wanted), machines * capacity.slots_for("unlit"))
    shares = spread.Shares([(number, wanted[number::parts]) for number in range(parts)], deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, machines, "unlit", shares, set_up, make_share)
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        pictures.record(run, run.machines, wanted, started, kind="unlit")


if __name__ == "__main__":
    main()
