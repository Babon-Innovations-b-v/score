"""Make a whole list of pictures on rented cloud graphics cards, then delete the machines.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/pictures.py <jobs.json> [--cards 5] [--model klein] [--dry-run]

The list is picture.py's own (--list): a JSON array of {"name", "sentence", "seed", "form", "refs"},
and "place" to word a scene's object in its place's style text (place.json).
Every job is worded here by picture.wording, at picture.py's steps and guidance, so a picture made
up there is the one the owner's card would make. The list is split evenly over --cards machines; each
installs the picture model from Hugging Face, holds it on its card whole when the card is big enough
and draws its share, and the pictures come back into WORK/pictures. A picture already there is skipped.
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
from provider import cloud  # noqa: E402
from paths import PICTURES  # noqa: E402

CARDS = 5
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


def expected_minutes(count, cards, model="klein"):
    return MODELS[model]["setup_minutes"] + count / cards * MODELS[model]["seconds"] / 60


def price(jobs, cards, account, model="klein"):
    """Print the estimate and refuse what passes the owner's limits; the offers, and the minutes the
    machines may run."""
    found = batch.offers(list(capacity.classes_for(MODELS[model]["kind"])))
    if not found:
        raise SystemExit("no card that holds this job is sold in the zones used")
    minutes = expected_minutes(len(jobs), cards, model)
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{len(jobs)} pictures on {cards} cards: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * cards:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * cards, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest * cards, spent)


def rent_machines(run, account, found, cards, kind=None, disk_gb=batch.DISK_GB):
    """Claim up to `cards` machines side by side for jobs of `kind`, each with a root disk of `disk_gb`, from the
    first offer that gives one that answers (batch.claim); the machines that answered."""
    with concurrent.futures.ThreadPoolExecutor(cards) as claims:
        claimed = list(claims.map(lambda number: batch.claim(run, account, found, number, kind, disk_gb),
                                  range(1, cards + 1)))
    return [machine for machine in claimed if machine]


def set_up(folder, host, share, model):
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


def draw_share(run, machine, share, model):
    """Run one machine from boot to delete: set it up, draw its share, bring the pictures back."""
    folder = machine["folder"]
    stop = threading.Event()
    try:
        host = machine["host"]
        batch.arm_self_delete(folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=keep_beating, args=(folder, host, stop), daemon=True).start()
        set_up(folder, host, share, model)
        batch.say(f"{folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        with (folder / "draw.log").open("w") as log:
            batch.remote(folder, host, "/root/venv/bin/python /root/pics/picture_worker.py /root/pics/jobs.json "
                         f"{MODELS[model]['pipeline']} {MODELS[model]['whole_gb']}", check=True, stdout=log,
                         stderr=subprocess.STDOUT)
        batch.copy(folder, [f"root@{host}:/root/pics/out/"], folder / "out")
        for made in (folder / "out").glob("*.png"):
            shutil.copy2(made, PICTURES / made.name)
        machine["made"] = len(list((folder / "out").glob("*.png")))
    except Exception as error:  # noqa: BLE001 - one machine failing must not stop the others
        batch.say(f"{folder.name} failed: {error}")
    finally:
        stop.set()
        batch.delete_machine(machine)


def record(run, machines, jobs, started, kind="pictures"):
    """Write the run to the ledger and say what it made and cost."""
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
             "batch": run.folder.name, "kind": kind, **ledger.machines_record(machines, run.attempts, started),
             "pictures": len(jobs), "wall_minutes": (time.time() - started) / 60}
    rows = entry["machines"]
    ledger.record(entry)
    batch.say(f"{sum(row.get('made', 0) for row in rows)} of {len(jobs)} pictures in "
              f"{entry['wall_minutes']:.0f} min on {len(rows)} machines, €{entry['euros']:.2f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("list")
    parser.add_argument("--cards", type=int, default=CARDS)
    parser.add_argument("--model", choices=tuple(MODELS), default="klein", help="the picture model (MODELS)")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    jobs = jobs_to_make(options.list, options.model)
    if not jobs:
        raise SystemExit("every picture in the list is already made")
    account = cloud.account()
    batch.sweep(account)
    cards = min(options.cards, len(jobs))
    found, allowed_minutes = price(jobs, cards, account, options.model)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"pictures-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = Run(folder, started + allowed_minutes * 60)
    machines = []
    try:
        machines = rent_machines(run, account, found, cards, MODELS[options.model]["kind"],
                                 MODELS[options.model]["disk_gb"])
        threads = [threading.Thread(target=draw_share,
                                    args=(run, machine, jobs[index::len(machines)], options.model))
                   for index, machine in enumerate(machines)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        record(run, run.machines, jobs, started, MODELS[options.model]["kind"])


if __name__ == "__main__":
    main()
