"""Generate a picking page's sound takes with MOSS-SoundEffect v2.0 on one rented cloud card, bring them back, and
delete the machine (job soundtool, 2026-10-06: the owner heard the trial and found it "sounds good", where the CC0
recordings were "pretty bad").

    ~/.farm-factory-props/env/bin/python tools/props/cloud/moss_sound.py <page> --who "<session>" [--dry-run]

The jobs come from the repo's data: every sound on the page whose brief in data/sound/sounds.json has `prompts`
gets each prompt at `seeds` seeds (its `seconds` long). The takes land in the picker's cache
(`~/.cache/farm-factory/sound-picker/moss/<page>/`) with `manifest.json` naming each file's sound, prompt, seed and
model, which is its credit; the picker's MOSS source offers them, levelled by the loudness rule like every take.
MOSS-SoundEffect v2.0 is Apache-2.0, code and weights, both pinned below. Measured on the trial: about 6.3 s a clip
on an H100 whatever its length, 15.6 GB of card memory, so an L4 (24 GB) fits.
"""
import argparse
import json
import pathlib
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
from provider import cloud  # noqa: E402
from paths import REPO  # noqa: E402

MOSS_SHA = "934d6826b084c46a0d033402174d5f8ac4ed2519"
MOSS_MODEL_REVISION = "e35df4d82fbe87fcd5d14e5d100e349c0c3c076d"
MODEL = "MOSS-SoundEffect v2.0"
MODEL_PAGE = "https://huggingface.co/OpenMOSS-Team/MOSS-SoundEffect-v2.0"
REMOTE = pathlib.PurePosixPath("/root/sfx")
SOUNDS = REPO / "data" / "sound" / "sounds.json"
OUT = pathlib.Path.home() / ".cache" / "farm-factory" / "sound-picker" / "moss"
SETUP_MINUTES = 8
MINUTES_A_CLIP = 0.4
## The most this tool spends on one run, in euros (the budget for the whole game's sound in one go, 2026-10-06).
BUDGET_EUROS = 8.0


def jobs_for(page, sounds_path=SOUNDS):
    """Every take to make for a page: each briefed prompt at each of its seeds."""
    jobs = []
    for name, entry in json.loads(pathlib.Path(sounds_path).read_text())["sounds"].items():
        brief = entry.get("pick", {})
        if brief.get("page") != page:
            continue
        for number, prompt in enumerate(brief.get("prompts", []), start=1):
            for seed in range(1, int(brief.get("seeds", 2)) + 1):
                jobs.append({"file": f"{name}__p{number}__s{seed}.wav", "sound": name, "prompt": prompt,
                             "seconds": int(brief.get("seconds", 8)), "seed": seed})
    return jobs


def price(jobs, account):
    """The offers and the minutes allowed; refused when over the owner's limits or this tool's budget."""
    found = batch.offers(list(capacity.classes_for("moss-sound")))
    if not found:
        raise SystemExit("no card is sold in the zones used")
    minutes = SETUP_MINUTES + len(jobs) * MINUTES_A_CLIP
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    euros = ledger.cost(minutes, dearest)
    batch.say(f"{len(jobs)} MOSS takes on one card: about {minutes:.0f} min, at most €{euros:.2f}; "
              f"€{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    if euros > BUDGET_EUROS:
        raise SystemExit(f"refused: €{euros:.2f} is over this run's €{BUDGET_EUROS:.2f}")
    budget_minutes = BUDGET_EUROS / dearest * 60
    return found, min(ledger.minutes_allowed(dearest, spent), budget_minutes)


def work_on(run, machine, jobs, out):
    """One machine from boot to delete: MOSS up, every take made, the takes back."""
    import pictures
    log_folder = machine["folder"]
    stop = threading.Event()
    try:
        host = machine["host"]
        batch.arm_self_delete(log_folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(log_folder, host, stop), daemon=True).start()
        batch.remote(log_folder, host, f"mkdir -p {REMOTE}/out", check=True)
        (log_folder / "jobs.json").write_text(json.dumps(jobs))
        batch.copy(log_folder, [HERE / "moss_setup.sh", HERE / "moss_generate.py", log_folder / "jobs.json"],
                   f"root@{host}:{REMOTE}/")
        with (log_folder / "setup.log").open("w") as log:
            batch.remote(log_folder, host, f"env MOSS_SHA={MOSS_SHA} MOSS_MODEL_REVISION={MOSS_MODEL_REVISION} "
                         f"bash {REMOTE}/moss_setup.sh", check=True, stdout=log, stderr=subprocess.STDOUT)
        batch.say(f"{log_folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        try:
            with (log_folder / "generate.log").open("w") as log:
                batch.remote(log_folder, host, f"cd {REMOTE} && TORCHDYNAMO_DISABLE=1 PYTHONUNBUFFERED=1 "
                             "/root/venv/bin/python moss_generate.py", check=True, stdout=log,
                             stderr=subprocess.STDOUT)
        finally:
            out.mkdir(parents=True, exist_ok=True)
            batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{out}/")
    finally:
        stop.set()
        batch.delete_machine(machine)


def write_manifest(out, jobs):
    """Each take that came back with its credit: the sound, the prompt, the seed and the model."""
    made = [dict(job, model=MODEL, model_page=MODEL_PAGE, code=f"OpenMOSS/MOSS-TTS@{MOSS_SHA}",
                 weights=f"OpenMOSS-Team/MOSS-SoundEffect-v2.0@{MOSS_MODEL_REVISION}", licence="Apache-2.0")
            for job in jobs if (out / job["file"]).exists()]
    (out / "manifest.json").write_text(json.dumps(made, indent=1))
    return made


def record(run, machines, started, out, made):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": "moss-sound", "folder": str(out), "takes": len(made),
             **ledger.machines_record(machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"moss: {len(made)} takes, {entry['wall_minutes']:.0f} min, €{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("page")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    jobs = jobs_for(options.page)
    if not jobs:
        raise SystemExit(f"no sound on the '{options.page}' page has prompts in data/sound/sounds.json")
    account = cloud.account()
    batch.sweep(account)
    found, allowed_minutes = price(jobs, account)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures
    started = time.time()
    run_folder = batch.BATCHES / time.strftime("moss-%Y%m%d-%H%M%S")
    run_folder.mkdir(parents=True)
    run = pictures.Run(run_folder, started + allowed_minutes * 60)
    out = OUT / options.page
    machines, made = [], []
    try:
        machines = pictures.rent_machines(run, account, found, 1)
        if not machines:
            raise SystemExit("no card could be rented")
        work_on(run, machines[0], jobs, out)
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        if out.exists():
            made = write_manifest(out, jobs)
        entry = record(run, run.machines, started, out, made)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        print(json.dumps(entry))


if __name__ == "__main__":
    main()
