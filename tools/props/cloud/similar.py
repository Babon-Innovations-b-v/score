"""DINOv2's likeness of pairs of pictures on one rented card, then delete the machine (the render-and-compare,
tools/usd/compare.py: each object rendered alone beside its close-up).

    .venv/bin/python tools/props/cloud/similar.py <pairs.json> <out.json> --who "<session>" [--dry-run]

pairs.json: {name: [first picture, second picture]}, local paths; out.json: {name: likeness}, the cosine of DINOv2's
class tokens (similar_worker.py). DINOv2 (facebookresearch/dinov2, code and weights Apache-2.0; facebook/dinov2-base
through transformers) runs on any card, or on a processor machine when no card is in stock; the owner's limits, the
self-delete, the watchdog and the delete are batch.py's.
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

REMOTE = pathlib.PurePosixPath("/root/similar")
KIND = "similar"
WEIGHTS = "facebook/dinov2-base"
SETUP_MINUTES = 8
MINUTES_A_PAIR = 0.02
# After the cards: processor machines, which run DINOv2 in minutes for a few hundred pairs when no card is in stock.
PROCESSORS = ("cpu-16c-64gb", "cpu-32c-64gb", "cpu-32c-128gb")


def price(pairs, account):
    """Print the estimate and refuse what passes the owner's limits; the offers and the minutes allowed."""
    found = batch.offers(list(capacity.classes_for(KIND)) + list(PROCESSORS))
    if not found:
        raise SystemExit("no machine for DINOv2 is sold by the backend")
    minutes = SETUP_MINUTES + len(pairs) * MINUTES_A_PAIR
    return found, batch.priced(found, minutes, 1, f"{len(pairs)} pairs on one machine", account)


def set_up(machine):
    """DINOv2 and its weights onto one machine."""
    log_folder, host = machine["folder"], machine["host"]
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}/in", check=True)
    batch.copy(log_folder, [HERE / "similar_setup.sh", HERE / "similar_worker.py"], f"root@{host}:{REMOTE}/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"env DINO_WEIGHTS={WEIGHTS} bash {REMOTE}/similar_setup.sh", check=True,
                     stdout=log, stderr=subprocess.STDOUT)


def uploaded(pairs, folder):
    """The pairs as the machine sees them: each picture under a name of its own in one folder; {name: [a, b]} and
    the local files to send."""
    names, files = {}, {}
    for name, both in pairs.items():
        names[name] = []
        for path in both:
            path = pathlib.Path(path).resolve()
            key = files.setdefault(str(path), f"{len(files):05d}{path.suffix}")
            names[name].append(key)
    staged = folder / "in"
    staged.mkdir(parents=True, exist_ok=True)
    for source, key in files.items():
        (staged / key).write_bytes(pathlib.Path(source).read_bytes())
    (folder / "pairs.json").write_text(json.dumps(names, indent=1))
    return staged


def compare(machine, pairs, card, out):
    """Every pair on the machine, the likenesses back into out. A worker that fails raises spread.JobFailed."""
    log_folder, host = machine["folder"], machine["host"]
    staged = uploaded(pairs, log_folder)
    batch.copy(log_folder, [f"{staged}/", str(log_folder / "pairs.json")], f"root@{host}:{REMOTE}/in/")
    worker = ["/root/venv/bin/python", str(REMOTE / "similar_worker.py"), WEIGHTS, str(REMOTE / "in/pairs.json"),
              str(REMOTE / "in"), str(REMOTE / "out.json")]
    with (log_folder / "similar.log").open("w") as log:
        done = batch.remote(log_folder, host, f"CUDA_VISIBLE_DEVICES={card or 0} {shlex.join(worker)}", stdout=log,
                            stderr=subprocess.STDOUT)
    spread.raise_for(done.returncode, f"similar ({log_folder / 'similar.log'})")
    batch.copy(log_folder, [f"root@{host}:{REMOTE}/out.json"], str(out))


def likeness(pairs, out, who):
    """DINOv2's likeness of every pair, rented, run and deleted: {name: likeness}, also written to out."""
    out = pathlib.Path(out)
    account = cloud.account()
    batch.sweep(account)
    found, allowed_minutes = price(pairs, account)
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures as picture_runs
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime("similar-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = picture_runs.Run(run_folder, started + allowed_minutes * 60)
    queue = spread.Shares([0], deadline=run.deadline)  # one share: every pair
    try:
        spread.on_machines(run, account, found, 1, KIND, queue, set_up,
                           lambda machine, _share, card: compare(machine, pairs, card, out))
        if not run.machines:
            raise SystemExit("no machine could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run_folder.name,
                 "kind": KIND, "who": who, "pairs": len(pairs),
                 **ledger.machines_record(run.machines, run.attempts, started),
                 "wall_minutes": (time.time() - started) / 60}
        ledger.record(entry)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        batch.say(f"similar: {entry['wall_minutes']:.0f} min, €{entry['euros']:.2f}")
    if not out.exists():
        raise SystemExit(f"no likenesses came back (logs under {run_folder})")
    return json.loads(out.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("pairs", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    pairs = json.loads(options.pairs.read_text())
    if options.dry_run:
        price(pairs, cloud.account())
        return
    likeness(pairs, options.out, options.who)


if __name__ == "__main__":
    main()
