"""Segment clean close-ups into regions with SAM 2.1 on rented cards, spread over machines (spread.py), bring the masks
back, delete the machines (job repaint, 2026-10-08: the regions a close-up shows, a foil patch, a seat on its frame,
are what a generated model is painted by; PartCrafter's parts do not follow them).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/segment.py <folder of pictures> --who "<session>" [--dry-run]

Each picture (<take>.png, a cut-out) comes back as <folder>/masks/<take>.npz (segment_worker.py says what it holds).
A picture already segmented is skipped. SAM 2 (facebookresearch/sam2, code and SAM 2.1 weights Apache-2.0) runs
through segment_worker.py; the owner's limits, the self-delete, the watchdog and the delete are batch.py's. Under
SCORE_CLOUD=k8s the shares go to the Kubernetes cluster as Jobs of the sam image (tools/cloud/k8s/cluster_jobs.py);
the machines stay the default.
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
import provider  # noqa: E402
import spread  # noqa: E402
from paths import REPO  # noqa: E402
from provider import cloud  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/seg")
KIND = "segment"
# Pinned: facebookresearch/sam2's main on 2026-10-08 (last commit 2024-12-16), and the SAM 2.1 large weights.
SAM2 = "2b90b9f5ceec907a1c18123530e92e794ad901a4"
WEIGHTS = "facebook/sam2.1-hiera-large"
SETUP_MINUTES = 12
# Pictures a machine takes at once (the model loads once a share) and the minutes each takes, a first guess.
SHARE_SIZE = 8
MINUTES_A_PICTURE = 0.5


def to_segment(folder):
    """The folder's pictures with no masks yet."""
    return [path for path in sorted(folder.glob("*.png")) if not (folder / "masks" / f"{path.stem}.npz").exists()]


def price(shares, account, cards=None):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and the minutes
    allowed."""
    found = batch.offers(list(capacity.classes_for(KIND)))
    if not found:
        raise SystemExit("no card that holds SAM 2 is sold by the backend")
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
    """SAM 2 and its weights onto one machine."""
    log_folder, host = machine["folder"], machine["host"]
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}", check=True)
    batch.copy(log_folder, [HERE / "segment_setup.sh", HERE / "segment_worker.py"], f"root@{host}:{REMOTE}/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"env SAM2={SAM2} SAM2_WEIGHTS={WEIGHTS} bash {REMOTE}/segment_setup.sh",
                     check=True, stdout=log, stderr=subprocess.STDOUT)


def segment(machine, number, pictures, card, folder):
    """One share of pictures on a machine: up, segmented, their masks back. A worker that fails raises
    spread.JobFailed."""
    log_folder, host = machine["folder"], machine["host"]
    place = REMOTE / "in" / str(number)
    batch.remote(log_folder, host, f"mkdir -p {place} {REMOTE}/out", check=True)
    batch.copy(log_folder, pictures, f"root@{host}:{place}/")
    worker = ["/root/venv/bin/python", str(REMOTE / "segment_worker.py"), WEIGHTS, str(place), str(REMOTE / "out")]
    began = time.time()
    try:
        with (log_folder / f"share{number}.log").open("w") as log:
            done = batch.remote(log_folder, host, f"CUDA_VISIBLE_DEVICES={card or 0} {shlex.join(worker)}",
                                stdout=log, stderr=subprocess.STDOUT)
    finally:
        (folder / "masks").mkdir(exist_ok=True)
        batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{folder / 'masks'}/")
        batch.say(f"segment share {number} on {log_folder.name}: {(time.time() - began) / 60:.1f} min")
    spread.raise_for(done.returncode, f"share {number} ({log_folder / f'share{number}.log'})")
    machine.setdefault("unit_seconds", []).append(round(time.time() - began, 1))


def record(run, started, folder, pictures):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": KIND, "folder": str(folder), "pictures": pictures,
             **ledger.machines_record(run.machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"segment: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machines, €{entry['euros']:.2f}")
    return entry


def cluster_job(pictures, folder):
    """One share as the cluster runs it (SCORE_CLOUD=k8s): its pictures up, segment_worker.py through the sam image's
    sam-run with SAM 2.1 from the node cache, the masks back into <folder>/masks/ as the machines bring them."""
    return {"command": ["sam-run", "tools/props/cloud/segment_worker.py", WEIGHTS, "/work/in", "/work/out"],
            "code": ["tools/props/cloud/segment_worker.py"], "models": ["sam2.1-hiera-large"],
            "inputs": [{"local": str(picture.resolve()), "path": f"/work/in/{picture.name}"} for picture in pictures],
            "outputs": [{"path": "/work/out", "local": str((folder / "masks").resolve())}],
            "minutes": SETUP_MINUTES + MINUTES_A_PICTURE * len(pictures) * 2}


def main_on_cluster(options, shares):
    """main() under SCORE_CLOUD=k8s: the shares as one run of the cluster on the segment kind's classes in its order
    (capacity.py)."""
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import cluster_jobs

    if options.dry_run:
        batch.say(f"{len(shares)} shares for the cluster")
        return
    cluster_jobs.run(KIND, [cluster_job(share, options.folder) for share in shares], options.who, image="sam")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=pathlib.Path, help="a folder of cut-out pictures")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    parser.add_argument("--cards", type=int, help="rent at most this many machines (each one's setup is paid)")
    options = parser.parse_args()
    pictures = to_segment(options.folder)
    if not pictures:
        batch.say("every picture in the folder is segmented already")
        return
    shares = [pictures[start:start + SHARE_SIZE] for start in range(0, len(pictures), SHARE_SIZE)]
    if provider.on_cluster():
        main_on_cluster(options, shares)
        left = to_segment(options.folder)
        if left and not options.dry_run:
            raise SystemExit(f"{len(left)} pictures not segmented on the cluster")
        return
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(shares, account, options.cards)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures as picture_runs
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime("segment-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = picture_runs.Run(run_folder, started + allowed_minutes * 60)
    queue = spread.Shares(enumerate(shares), deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, count, KIND, queue, set_up,
                           lambda machine, share, card: segment(machine, *share, card, options.folder))
        if not run.machines:
            raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, started, options.folder, len(pictures))
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
    left = to_segment(options.folder)
    if left:
        raise SystemExit(f"{len(left)} pictures not segmented (logs under {run_folder})")


if __name__ == "__main__":
    main()
