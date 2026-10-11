"""The relative depth of pictures on rented cloud cards, then delete the machines.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/depth.py <out folder> <picture.png>... [--dry-run]

Depth Anything V2 Small (depth-anything/Depth-Anything-V2-Small-hf at a pinned revision, Apache-2.0, code and
weights) reads each picture's relative inverse depth (larger is nearer); each comes back as <out folder>/<stem>.npy
at the picture's own size. The terrain stage reads the fine relief of a ground's diorama picture from it, seen
straight down (score/stages/terrain). A long list is cut into shares over as many cards as make it in about the
setup's time (spread.py). Renting, the owner's limits and deleting are batch.py's; nothing rents outside a cleared
run (score.adapters.compute).
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
import spread  # noqa: E402
from provider import cloud  # noqa: E402

KIND = "depth"
# First guesses until a run is measured: setup (a Python, torch, the 100 MB model) and a picture at 1036 px on an L4.
SETUP_MINUTES = 6
SECONDS_A_PICTURE = 4


def machines_for(count):
    """How many cards a list of `count` pictures is spread over."""
    return capacity.machines_for(count, SECONDS_A_PICTURE / 60, SETUP_MINUTES, capacity.slots_for(KIND))


def price(count, account):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and the minutes
    they may run."""
    found = batch.offers(list(capacity.classes_for(KIND)))
    if not found:
        raise SystemExit("no card that holds this job is sold in the zones used")
    machines = machines_for(count)
    minutes = capacity.spread_minutes(count, SECONDS_A_PICTURE / 60, SETUP_MINUTES, machines)
    what = f"{count} depth maps on {machines} card{'s' if machines > 1 else ''}"
    return found, machines, batch.priced(found, minutes, machines, what, account)


def set_up(machine):
    """The model and the scripts onto one machine."""
    folder, host = machine["folder"], machine["host"]
    batch.remote(folder, host, "mkdir -p /root/depth/out", check=True)
    batch.copy(folder, [HERE / "depth_worker.py", HERE / "depth_setup.sh"], f"root@{host}:/root/depth/")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, "bash /root/depth/depth_setup.sh", check=True, stdout=log, stderr=subprocess.STDOUT)


def share_maker(out):
    """The per-share function for spread.on_machines, bringing every depth map back into `out`."""
    def make_share(machine, share, card):
        number, wanted = share
        folder, host = machine["folder"], machine["host"]
        batch.remote(folder, host, f"mkdir -p /root/depth/in-{number}", check=True)
        batch.copy(folder, wanted, f"root@{host}:/root/depth/in-{number}/")
        try:
            with (folder / f"depth-{number}.log").open("w") as log:
                done = batch.remote(folder, host, f"CUDA_VISIBLE_DEVICES={card} /root/venv/bin/python "
                                    f"/root/depth/depth_worker.py /root/depth/in-{number}", stdout=log,
                                    stderr=subprocess.STDOUT)
        finally:
            batch.copy(folder, [f"root@{host}:/root/depth/out/"], out)
        machine["made"] = machine.get("made", 0) + sum((out / f"{path.stem}.npy").exists() for path in wanted)
        spread.raise_for(done.returncode, f"share {number} ({folder / f'depth-{number}.log'})")
    return make_share


def measure(pictures, out, dry_run=False):
    """Every picture's depth into `out` (<stem>.npy), those already there skipped; the ledger entry, or None when
    nothing was rented."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = [pathlib.Path(path) for path in pictures if not (out / f"{pathlib.Path(path).stem}.npy").exists()]
    if not wanted:
        return None
    account = cloud.account()
    batch.sweep(account)
    found, machines, allowed_minutes = price(len(wanted), account)
    if dry_run:
        return None
    import pictures as picture_runs  # its Run and record, loaded only once something will be rented
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"depth-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = picture_runs.Run(folder, started + allowed_minutes * 60)
    parts = min(len(wanted), machines * capacity.slots_for(KIND))
    shares = spread.Shares([(number, wanted[number::parts]) for number in range(parts)], deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, machines, KIND, shares, set_up, share_maker(out))
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = picture_runs.record(run, run.machines, wanted, started, kind=KIND)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("pictures", nargs="+")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    measure(options.pictures, options.out, options.dry_run)


if __name__ == "__main__":
    main()
