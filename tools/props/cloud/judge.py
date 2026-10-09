"""Ask a vision-language model a list of questions about pictures on rented cards, then delete the machines.

    .venv/bin/python tools/props/cloud/judge.py <questions.json> <answers folder> [--dry-run]

The list is a JSON array of {"name", "text", "images"}, the images local paths; each answer comes back whole as
<answers folder>/<name>.txt. A question already answered there is skipped. The model (MODEL, Qwen3.8-27B in FP8,
Apache-2.0, 30 GB of weights) runs through vLLM on one 48 or 80 GB card with its thinking on (judge_worker.py),
every question of a machine's share at once; a long list is cut into shares over as many machines as answer it in
about the setup's time (spread.py), one machine for a short one. Its first use is the close-up shape check (../closeup/check.py). Renting, the owner's limits
and deleting are batch.py's, through pictures.py's helpers.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import pictures  # noqa: E402
import spread  # noqa: E402
from provider import cloud  # noqa: E402

MODEL = "Qwen/Qwen3.8-27B-FP8"
KIND = "judge"
DISK_GB = 100
# First guesses for the estimate, until a run is measured: installing vLLM and fetching 30 GB, then the questions,
# answered side by side.
SETUP_MINUTES = 12
SECONDS_A_QUESTION = 6


def to_ask(path, answers):
    """The list's questions not yet answered in `answers`."""
    return [job for job in json.loads(pathlib.Path(path).read_text())
            if not (answers / f"{job['name']}.txt").exists()]


def price(jobs, account, cards=None):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines (at most `cards` when
    given) and the minutes allowed."""
    found = batch.offers(list(capacity.classes_for(KIND)))
    if not found:
        raise SystemExit("no card that holds the judge is sold in the zones used")
    count = capacity.machines_for(len(jobs), SECONDS_A_QUESTION / 60, SETUP_MINUTES, capacity.slots_for(KIND))
    count = min(count, cards or count)
    minutes = capacity.spread_minutes(len(jobs), SECONDS_A_QUESTION / 60, SETUP_MINUTES, count,
                                      capacity.slots_for(KIND))
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{len(jobs)} questions on {count} card{'s' if count > 1 else ''}: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * count:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * count, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, count, ledger.minutes_allowed(dearest * count, spent)


def set_up(machine):
    """The model and the scripts onto one machine."""
    folder, host = machine["folder"], machine["host"]
    batch.remote(folder, host, "mkdir -p /root/judge/in /root/judge/out", check=True)
    batch.copy(folder, [HERE / "judge_worker.py", HERE / "judge_setup.sh"], f"root@{host}:/root/judge/")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, f"bash /root/judge/judge_setup.sh {MODEL}", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def answer_share(machine, share, card, answers):
    """One share of the questions on one card: its pictures up, every question asked, the answers back. A worker
    that fails raises spread.JobFailed (what it answered still comes back)."""
    number, jobs = share
    folder, host = machine["folder"], machine["host"]
    batch.copy(folder, sorted({image for job in jobs for image in job["images"]}), f"root@{host}:/root/judge/in/")
    listing = folder / f"jobs-{number}.json"
    listing.write_text(json.dumps([dict(job, images=[pathlib.Path(image).name for image in job["images"]])
                                   for job in jobs]))
    batch.copy(folder, [listing], f"root@{host}:/root/judge/")
    began = time.time()
    try:
        with (folder / f"judge-{number}.log").open("w") as log:
            done = batch.remote(folder, host, f"CUDA_VISIBLE_DEVICES={card} /root/venv/bin/python "
                                f"/root/judge/judge_worker.py /root/judge/{listing.name}", stdout=log,
                                stderr=subprocess.STDOUT)
    finally:
        batch.copy(folder, [f"root@{host}:/root/judge/out/"], folder / "out")
        for answer in (folder / "out").glob("*.txt"):
            shutil.copy2(answer, answers / answer.name)
        machine["made"] = len(list((folder / "out").glob("*.txt")))
    machine.setdefault("unit_seconds", []).append(round(time.time() - began, 1))
    spread.raise_for(done.returncode, f"share {number} ({folder / f'judge-{number}.log'})")


def record(run, jobs, started):
    """Write the run to the ledger and say what it answered and cost; the ledger entry."""
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": KIND, **ledger.machines_record(run.machines, run.attempts, started), "questions": len(jobs),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"{sum(row.get('made', 0) for row in entry['machines'])} of {len(jobs)} questions answered in "
              f"{entry['wall_minutes']:.0f} min, €{entry['euros']:.2f}")
    return entry


def ask(path, answers, dry_run=False, cards=None):
    """Answer the list's open questions into `answers` on rented cards (at most `cards`: each card's setup costs
    about SETUP_MINUTES, so a list that may wait runs cheaper on fewer); the run's ledger entry, or None when nothing
    was rented."""
    answers.mkdir(parents=True, exist_ok=True)
    jobs = to_ask(path, answers)
    if not jobs:
        batch.say("every question in the list is already answered")
        return None
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(jobs, account, cards)
    if dry_run:
        return None
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"judge-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = pictures.Run(folder, started + allowed_minutes * 60)
    parts = min(len(jobs), count * capacity.slots_for(KIND))
    shares = spread.Shares([(number, jobs[number::parts]) for number in range(parts)], deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, count, KIND, shares, set_up,
                           lambda machine, share, card: answer_share(machine, share, card, answers), DISK_GB)
        if not run.machines:
            raise SystemExit("no card for the judge answered")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, jobs, started)
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("questions")
    parser.add_argument("answers", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    parser.add_argument("--cards", type=int, help="rent at most this many cards")
    options = parser.parse_args()
    ask(options.questions, options.answers, options.dry_run, options.cards)


if __name__ == "__main__":
    main()
