"""Make a whole list of pictures on rented cloud graphics cards, then delete the machines.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/pictures.py <jobs.json> [--cards N] [--model klein] [--dry-run]

The list is picture.py's own (--list): a JSON array of {"name", "sentence", "seed", "form", "refs"},
and "place" to word a scene's object in its place's style text (place.json).
Every job is worded here by picture.wording, at picture.py's steps and guidance, so a picture made
up there is the one the owner's card would make. The list is cut into a share for each card of as many machines as
draw it in about the setup's time (spread.py, capacity.machines_for; --cards caps them); each machine installs the
picture model from Hugging Face once, holds it on its card whole when the card is big enough, and takes the next
share as it finishes one, so a share whose machine never came is drawn by another. The pictures come back into
WORK/pictures. A picture already there is skipped.
--model picks the picture model (MODELS): FLUX.2 klein 4B by default, or Qwen-Image-Edit-2511, the
open image-edit model that came closest to Nano Banana Pro on the lab's ten close-ups after klein
(job openpics, 2026-10-08). Renting, the owner's limits and deleting are batch.py's.
"""
import argparse
import concurrent.futures
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
sys.path.insert(0, str(HERE.parent / "scene"))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import picture  # noqa: E402
import place  # noqa: E402
import spread  # noqa: E402
from provider import cloud  # noqa: E402
from paths import PICTURES  # noqa: E402

# The picture models a list can be drawn with, each open with commercial use allowed (Apache-2.0: code,
# weights and text encoder): its Hugging Face repository, its diffusers pipeline, the job kind that
# names the cards it runs on (capacity.py), the root disk its weights need, the card memory it is held
# whole in (a smaller card moves it on and off part by part), its own steps and settings, and the
# estimate's setup minutes and seconds a picture. The seconds were measured with two reference pictures
# on 2026-10-08: klein about 9 s on an L4, Qwen-Image-Edit 56 s on an H100 SXM and 82 s on a PCIe H100.
MODELS = {
    "klein": {"repository": "black-forest-labs/FLUX.2-klein-4B", "pipeline": "Flux2KleinPipeline",
              "kind": "pictures", "disk_gb": batch.DISK_GB, "whole_gb": 20, "steps": picture.STEPS,
              "call": {"guidance_scale": picture.GUIDANCE}, "setup_minutes": 8, "seconds": 9},
    "qwen-edit": {"repository": "Qwen/Qwen-Image-Edit-2511", "pipeline": "QwenImageEditPlusPipeline",
                  "kind": "pictures-20b", "disk_gb": 150, "whole_gb": 70, "steps": 40,
                  "call": {"true_cfg_scale": 4.0, "guidance_scale": 1.0, "negative_prompt": " "},
                  "setup_minutes": 10, "seconds": 82},
}


class Run:
    """What `batch.claim` needs of a run: its folder, when every machine must be gone, its machines, and the
    starts that failed on the way."""

    def __init__(self, folder, deadline):
        self.folder = folder
        self.deadline = deadline
        self.machines = []
        self.attempts = []
        # Machines claimed side by side choose their offers one at a time, each counting those being rented.
        self.choosing = threading.Lock()
        self.pending = []
        self.dropped = set()


def jobs_to_make(path, model="klein"):
    """The list's pictures not yet made, each worded as picture.py would word it, with `model`'s settings."""
    jobs = []
    for job in json.loads(pathlib.Path(path).read_text()):
        if (PICTURES / f"{job['name']}.png").exists():
            continue
        # A job may carry its whole wording, for a picture that is not an object on its own (a
        # flat facade to tile); otherwise it is worded as picture.py words an object. A job naming
        # its place (place.json) is worded in that place's style text as well.
        wording = job.get("wording") or picture.wording(job["sentence"], job.get("form") or picture.FORM)
        if job.get("place"):
            wording = f"{wording}, in the look of this place: {place.style_text(job['place'])}"
        jobs.append({"name": job["name"],
                     "wording": wording,
                     "seed": job.get("seed", 7), "steps": MODELS[model]["steps"], "call": MODELS[model]["call"],
                     "refs": [str(ref) for ref in job.get("refs", [])],
                     **{side: job[side] for side in ("width", "height") if side in job}})
    return jobs


def machines_for(count, model="klein", most=None):
    """How many machines a list of `count` pictures is drawn on (capacity.machines_for), at most `most`."""
    kind = MODELS[model]["kind"]
    planned = capacity.machines_for(count, MODELS[model]["seconds"] / 60, MODELS[model]["setup_minutes"],
                                    capacity.slots_for(kind))
    return min(planned, most) if most else planned


def expected_minutes(count, machines, model="klein"):
    return capacity.spread_minutes(count, MODELS[model]["seconds"] / 60, MODELS[model]["setup_minutes"], machines,
                                   capacity.slots_for(MODELS[model]["kind"]))


def price(jobs, machines, account, model="klein"):
    """Print the estimate and refuse what passes the owner's limits; the offers, and the minutes the
    machines may run."""
    found = batch.offers(list(capacity.classes_for(MODELS[model]["kind"])))
    if not found:
        raise SystemExit("no card that holds this job is sold in the zones used")
    minutes = expected_minutes(len(jobs), machines, model)
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{len(jobs)} pictures on {machines} machine{'s' if machines > 1 else ''}: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * machines:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * machines, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest * machines, spent)


def rent_machines(run, account, found, cards, kind=None, disk_gb=batch.DISK_GB):
    """Claim up to `cards` machines side by side for jobs of `kind`, each with a root disk of `disk_gb`, from the
    first offer that gives one that answers (batch.claim); the machines that answered."""
    with concurrent.futures.ThreadPoolExecutor(cards) as claims:
        claimed = list(claims.map(lambda number: batch.claim(run, account, found, number, kind, disk_gb),
                                  range(1, cards + 1)))
    return [machine for machine in claimed if machine]


def set_up(machine, model):
    """The picture model and its worker onto one machine."""
    folder, host = machine["folder"], machine["host"]
    batch.remote(folder, host, "mkdir -p /root/pics/refs /root/pics/out", check=True)
    batch.copy(folder, [HERE / "picture_worker.py", HERE / "picture_setup.sh"], f"root@{host}:/root/pics/")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, f"bash /root/pics/picture_setup.sh {MODELS[model]['repository']}",
                     check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def keep_beating(folder, host, stop):
    """Touch the machine's heartbeat every minute until `stop`, so its watcher knows this PC lives."""
    while not stop.wait(60):
        # A busy machine can refuse one ssh (connection timed out under a load of 78 on 16 cores, 2026-10-06);
        # a beat that fails must not end the beating, or the machine deletes itself 15 min later with its work.
        try:
            batch.heartbeat(folder, host)
        except subprocess.CalledProcessError as error:
            batch.say(f"{folder.name}: a heartbeat failed ({error.returncode}); trying again in a minute")


def draw_share(machine, share, card, model):
    """Draw one share on one card of a machine: its reference photos and list up, the worker run, its pictures back
    into WORK/pictures. A worker that fails raises spread.JobFailed (what it drew still comes back)."""
    number, jobs = share
    folder, host = machine["folder"], machine["host"]
    refs = sorted({ref for job in jobs for ref in job["refs"]})
    if refs:
        batch.copy(folder, refs, f"root@{host}:/root/pics/refs/")
    listing = folder / f"jobs-{number}.json"
    listing.write_text(json.dumps([dict(job, refs=[pathlib.Path(ref).name for ref in job["refs"]]) for job in jobs]))
    batch.copy(folder, [listing], f"root@{host}:/root/pics/")
    try:
        with (folder / f"draw-{number}.log").open("w") as log:
            done = batch.remote(folder, host, f"CUDA_VISIBLE_DEVICES={card} /root/venv/bin/python "
                                f"/root/pics/picture_worker.py /root/pics/{listing.name} {MODELS[model]['pipeline']} "
                                f"{MODELS[model]['whole_gb']}", stdout=log, stderr=subprocess.STDOUT)
    finally:
        batch.copy(folder, [f"root@{host}:/root/pics/out/"], folder / "out")
        for made in (folder / "out").glob("*.png"):
            shutil.copy2(made, PICTURES / made.name)
        machine["made"] = len(list((folder / "out").glob("*.png")))
    seconds = [float(line.split()[-1]) for line in (folder / f"draw-{number}.log").read_text().splitlines()
               if len(line.split()) == 2 and line.split()[0] in {job["name"] for job in jobs}]
    machine.setdefault("unit_seconds", []).extend(seconds)
    spread.raise_for(done.returncode, f"share {number} ({folder / f'draw-{number}.log'})")


def shares_of(jobs, machines, model):
    """The list cut into a share for each card the machines are planned to hold, in turn so each share is alike."""
    count = min(len(jobs), machines * capacity.slots_for(MODELS[model]["kind"]))
    return [(number, jobs[number::count]) for number in range(count)]


def record(run, machines, jobs, started, kind="pictures"):
    """Write the run to the ledger and say what it made and cost; the ledger entry."""
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
             "batch": run.folder.name, "kind": kind, **ledger.machines_record(machines, run.attempts, started),
             "pictures": len(jobs), "wall_minutes": (time.time() - started) / 60}
    rows = entry["machines"]
    ledger.record(entry)
    batch.say(f"{sum(row.get('made', 0) for row in rows)} of {len(jobs)} pictures in "
              f"{entry['wall_minutes']:.0f} min on {len(rows)} machines, €{entry['euros']:.2f}")
    return entry


def draw_list(path, model="klein", cards=None, dry_run=False):
    """Draw the list's pictures not yet made with `model`, spread over rented machines (at most `cards`), into
    WORK/pictures; the run's ledger entry, or None when nothing was rented."""
    jobs = jobs_to_make(path, model)
    if not jobs:
        batch.say("every picture in the list is already made")
        return None
    account = cloud.account()
    batch.sweep(account)
    machines = machines_for(len(jobs), model, cards)
    found, allowed_minutes = price(jobs, machines, account, model)
    if dry_run:
        return None
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"pictures-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = Run(folder, started + allowed_minutes * 60)
    shares = spread.Shares(shares_of(jobs, machines, model), deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, machines, MODELS[model]["kind"], shares,
                           lambda machine: set_up(machine, model),
                           lambda machine, share, card: draw_share(machine, share, card, model),
                           MODELS[model]["disk_gb"])
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, run.machines, jobs, started, MODELS[model]["kind"])
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("list")
    parser.add_argument("--cards", type=int, help="machines to rent at most (default: as many as draw the list in "
                        "about the setup's time, capacity.machines_for)")
    parser.add_argument("--model", choices=tuple(MODELS), default="klein", help="the picture model (MODELS)")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    draw_list(options.list, options.model, options.cards, options.dry_run)


if __name__ == "__main__":
    main()
