"""Rig finished models with UniRig on rented cards, spread over machines (spread.py), bring the rigged models back,
delete the machines (job characters-full, 2026-10-09: the character maker's animal route rigs a quadruped or a bird
it has no skeleton for).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/unirig.py <model.glb> [...] --out <folder> --who "<session>"
        [--seed 12345] [--dry-run]

Each model comes back as <out>/<name>-unirig.glb (the model as it went up, with UniRig's skeleton and skin weights)
and <out>/<name>-skeleton.fbx; a model already rigged there is skipped. UniRig (VAST-AI-Research/UniRig, MIT code;
VAST-AI/UniRig weights, MIT) runs through unirig_worker.py at the commit and weights pinned here; the owner's limits,
the self-delete, the watchdog and the delete are batch.py's.
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

REMOTE = pathlib.PurePosixPath("/root/rig")
KIND = "unirig"
# Pinned: VAST-AI-Research/UniRig's main on 2026-10-09 (last commit 2026-06-04), and its weights repository's revision.
UNIRIG = "6793c6640ff01c8fb389f3993434124bb43d2933"
WEIGHTS = "VAST-AI/UniRig"
WEIGHTS_REVISION = "36842e2b5947e9e60f89275b83208c8e74071c63"
SETUP_MINUTES = 15
# Minutes a model takes (skeleton, skin and merge), a first guess.
MINUTES_A_MODEL = 4


def to_rig(models, out):
    """The models with no rigged copy in `out` yet."""
    return [model for model in models if not (out / f"{model.stem}-unirig.glb").exists()]


def price(count_models, account):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and the minutes
    allowed."""
    found = batch.offers(list(capacity.classes_for(KIND)))
    if not found:
        raise SystemExit("no card that holds UniRig is sold by the backend")
    count = capacity.machines_for(count_models, MINUTES_A_MODEL, SETUP_MINUTES)
    minutes = capacity.spread_minutes(count_models, MINUTES_A_MODEL, SETUP_MINUTES, count)
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{count_models} models on {count} machine{'s' if count > 1 else ''}: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * count:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * count, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, count, ledger.minutes_allowed(dearest * count, spent)


def set_up(machine):
    """UniRig and its weights onto one machine."""
    log_folder, host = machine["folder"], machine["host"]
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}", check=True)
    batch.copy(log_folder, [HERE / "unirig_setup.sh", HERE / "unirig_worker.py"], f"root@{host}:{REMOTE}/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"env UNIRIG={UNIRIG} UNIRIG_WEIGHTS={WEIGHTS} "
                     f"UNIRIG_WEIGHTS_REVISION={WEIGHTS_REVISION} bash {REMOTE}/unirig_setup.sh",
                     check=True, stdout=log, stderr=subprocess.STDOUT)


def rig(machine, number, model, card, out, seed):
    """One model on a machine: up, rigged, back. A worker that fails raises spread.JobFailed."""
    log_folder, host = machine["folder"], machine["host"]
    place, made = REMOTE / "in" / str(number), REMOTE / "out" / str(number)
    batch.remote(log_folder, host, f"mkdir -p {place} {made}", check=True)
    batch.copy(log_folder, [model], f"root@{host}:{place}/")
    worker = ["/root/venv/bin/python", str(REMOTE / "unirig_worker.py"), str(place), str(made), "--seed", str(seed)]
    began = time.time()
    try:
        with (log_folder / f"model{number}.log").open("w") as log:
            done = batch.remote(log_folder, host, f"CUDA_VISIBLE_DEVICES={card or 0} {shlex.join(worker)}",
                                stdout=log, stderr=subprocess.STDOUT)
    finally:
        out.mkdir(parents=True, exist_ok=True)
        batch.copy(log_folder, [f"root@{host}:{made}/"], f"{out}/")
        batch.say(f"unirig {model.stem} on {log_folder.name}: {(time.time() - began) / 60:.1f} min")
    spread.raise_for(done.returncode, f"{model.stem} ({log_folder / f'model{number}.log'})")
    machine.setdefault("unit_seconds", []).append(round(time.time() - began, 1))


def record(run, started, out, models, who):
    """The run's ledger entry: its machines, minutes and euros."""
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": KIND, "who": who, "folder": str(out), "models": models,
             **ledger.machines_record(run.machines, run.attempts, started), "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"unirig: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machines, €{entry['euros']:.2f}")
    return entry


def run_on_machines(models, out, seed, who, account, found, count, allowed_minutes):
    """Rig `models` on `count` machines; every machine deleted after; the run's ledger entry."""
    import pictures as picture_runs
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime("unirig-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = picture_runs.Run(run_folder, started + allowed_minutes * 60)
    queue = spread.Shares(enumerate(models), deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, count, KIND, queue, set_up,
                           lambda machine, share, card: rig(machine, *share, card, out, seed))
        if not run.machines:
            raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, started, out, [model.stem for model in models], who)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("models", type=pathlib.Path, nargs="+", help="finished models, <name>.glb")
    parser.add_argument("--out", type=pathlib.Path, required=True, help="where the rigged models land")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--seed", type=int, default=12345, help="UniRig's skeleton seed")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    models = to_rig(options.models, options.out)
    if not models:
        batch.say("every model is rigged already")
        return
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(len(models), account)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    run_on_machines(models, options.out, options.seed, options.who, account, found, count, allowed_minutes)
    left = to_rig(models, options.out)
    if left:
        raise SystemExit(f"{len(left)} models not rigged: {', '.join(model.stem for model in left)}")


if __name__ == "__main__":
    main()
