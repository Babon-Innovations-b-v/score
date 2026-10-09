"""Find each finish of each clean close-up with SAM 3 asked by text, on rented cards spread over machines (spread.py),
bring the masks back, delete the machines (job repaint, 2026-10-09: SAM 2.1's automatic masks cut a close-up by look,
each lit face of a case, highlights, the picture on a screen; a split seeded by them carried every needless cut onto
the mesh. One seed per finish, asked for by name).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/finish_masks.py <folder> --who "<session>" [--dry-run]

The folder holds <take>.png (the close-up on white) and <take>.json ({"phrases": {code: phrase}}, the judge's names
for the parts of each finish); each comes back as <folder>/masks/<take>.npz (finish_masks_worker.py says what it
holds). A picture already done is skipped. SAM 3 (Meta, SAM License, commercial use allowed) from the open copy of its
weights scene.py uses; the owner's limits, the self-delete, the watchdog and the delete are batch.py's.
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
import spread  # noqa: E402
from provider import cloud  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/finish")
KIND = "finish-masks"
# The open copy of SAM 3's weights (scene.py's SAM3_WEIGHTS).
WEIGHTS = "jetjodh/sam3"
SETUP_MINUTES = 12
# Pictures a machine takes at once (the model loads once a share) and the minutes each takes, a first guess.
SHARE_SIZE = 8
MINUTES_A_PICTURE = 0.5


def to_find(folder):
    """The folder's close-ups with no finish masks yet."""
    return [path for path in sorted(folder.glob("*.png")) if not (folder / "masks" / f"{path.stem}.npz").exists()]


def price(shares, account, cards=None):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and the minutes
    allowed."""
    found = batch.offers(list(capacity.classes_for(KIND)))
    if not found:
        raise SystemExit("no card that holds SAM 3 is sold by the backend")
    each = SHARE_SIZE * MINUTES_A_PICTURE
    count = capacity.machines_for(len(shares), each, SETUP_MINUTES)
    count = min(count, cards or count)
    minutes = SETUP_MINUTES + max(each, len(shares) * each / count)
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{len(shares)} shares of pictures on {count} machine{'s' if count > 1 else ''}: "
              f"about {minutes:.0f} min, €{ledger.cost(minutes, dearest) * count:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * count, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, count, ledger.minutes_allowed(dearest * count, spent)


def set_up(machine):
    """SAM 3 and its weights onto one machine."""
    log_folder, host = machine["folder"], machine["host"]
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}", check=True)
    batch.copy(log_folder, [HERE / "finish_masks_setup.sh", HERE / "finish_masks_worker.py"],
               f"root@{host}:{REMOTE}/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"env SAM3_WEIGHTS={WEIGHTS} bash {REMOTE}/finish_masks_setup.sh",
                     check=True, stdout=log, stderr=subprocess.STDOUT)


def find_finishes(machine, number, pictures, card, folder):
    """One share of close-ups on a machine: up, each finish asked for, the masks back. A worker that fails raises
    spread.JobFailed."""
    log_folder, host = machine["folder"], machine["host"]
    place = REMOTE / "in" / str(number)
    batch.remote(log_folder, host, f"mkdir -p {place} {REMOTE}/out", check=True)
    batch.copy(log_folder, pictures + [path.with_suffix(".json") for path in pictures], f"root@{host}:{place}/")
    worker = ["/root/venv/bin/python", str(REMOTE / "finish_masks_worker.py"), WEIGHTS, str(place),
              str(REMOTE / "out")]
    began = time.time()
    try:
        with (log_folder / f"share{number}.log").open("w") as log:
            done = batch.remote(log_folder, host, f"CUDA_VISIBLE_DEVICES={card or 0} {shlex.join(worker)}",
                                stdout=log, stderr=subprocess.STDOUT)
    finally:
        (folder / "masks").mkdir(exist_ok=True)
        batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{folder / 'masks'}/")
        batch.say(f"finish masks share {number} on {log_folder.name}: {(time.time() - began) / 60:.1f} min")
    spread.raise_for(done.returncode, f"share {number} ({log_folder / f'share{number}.log'})")
    machine.setdefault("unit_seconds", []).append(round(time.time() - began, 1))


def record(run, started, folder, pictures):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": KIND, "folder": str(folder), "pictures": pictures,
             **ledger.machines_record(run.machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"finish masks: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machines, "
              f"€{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=pathlib.Path, help="a folder of cut-out pictures")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    parser.add_argument("--cards", type=int, help="rent at most this many machines (each one's setup is paid)")
    options = parser.parse_args()
    pictures = to_find(options.folder)
    if not pictures:
        batch.say("every close-up in the folder has its finish masks already")
        return
    shares = [pictures[start:start + SHARE_SIZE] for start in range(0, len(pictures), SHARE_SIZE)]
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(shares, account, options.cards)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures as picture_runs
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime("finishmasks-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = picture_runs.Run(run_folder, started + allowed_minutes * 60)
    queue = spread.Shares(enumerate(shares), deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, count, KIND, queue, set_up,
                           lambda machine, share, card: find_finishes(machine, *share, card, options.folder))
        if not run.machines:
            raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, started, options.folder, len(pictures))
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
    left = to_find(options.folder)
    if left:
        raise SystemExit(f"{len(left)} close-ups without finish masks (logs under {run_folder})")


if __name__ == "__main__":
    main()
