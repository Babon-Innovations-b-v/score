"""Generate a picking page's sound takes with MOSS-SoundEffect v2.0 on rented cloud cards, bring them back, and
delete the machines (job soundtool, 2026-10-06: the owner heard the trial and found it "sounds good", where the CC0
recordings were "pretty bad").

    ~/.farm-factory-props/env/bin/python tools/props/cloud/moss_sound.py <page> --who "<session>" [--dry-run]

The jobs come from the repo's data: every sound on the page whose brief in data/sound/sounds.json has `prompts`
gets each prompt at `seeds` seeds (its `seconds` long). The takes land in the picker's cache
(`~/.cache/farm-factory/sound-picker/moss/<page>/`) with `manifest.json` naming each file's sound, prompt, seed and
model, which is its credit; the picker's MOSS source offers them, levelled by the loudness rule like every take.
MOSS-SoundEffect v2.0 is Apache-2.0, code and weights, both pinned below. Measured on the trial: about 6.3 s a clip
on an H100 whatever its length, 15.6 GB of card memory, so an L4 (24 GB) fits. A long page is cut into shares over
as many cards as make it in about the setup's time (spread.py), each share's scores joined into scores.json here.
Under SCORE_CLOUD=k8s the shares go to the Kubernetes cluster as Jobs of the moss image
(tools/cloud/k8s/cluster_jobs.py); the machines stay the default.
"""
import argparse
import json
import pathlib
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
    """The offers, the machines and the minutes allowed; refused when over the owner's limits or this tool's
    budget."""
    found = batch.offers(list(capacity.classes_for("moss-sound")))
    if not found:
        raise SystemExit("no card is sold in the zones used")
    count = capacity.machines_for(len(jobs), MINUTES_A_CLIP, SETUP_MINUTES, capacity.slots_for("moss-sound"))
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    # Each card more pays one more setup: fewer cards while the spread would pass this tool's budget.
    while True:
        minutes = capacity.spread_minutes(len(jobs), MINUTES_A_CLIP, SETUP_MINUTES, count)
        euros = ledger.cost(minutes, dearest) * count
        if euros <= BUDGET_EUROS or count == 1:
            break
        count -= 1
    batch.say(f"{len(jobs)} MOSS takes on {count} card{'s' if count > 1 else ''}: about {minutes:.0f} min, at most "
              f"€{euros:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * count, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    if euros > BUDGET_EUROS:
        raise SystemExit(f"refused: €{euros:.2f} is over this run's €{BUDGET_EUROS:.2f}")
    budget_minutes = BUDGET_EUROS / (dearest * count)
    return found, count, min(ledger.minutes_allowed(dearest * count, spent), budget_minutes)


def set_up(machine):
    """MOSS onto one machine."""
    log_folder, host = machine["folder"], machine["host"]
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}/out", check=True)
    batch.copy(log_folder, [HERE / "moss_setup.sh", HERE / "moss_generate.py"], f"root@{host}:{REMOTE}/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"env MOSS_SHA={MOSS_SHA} MOSS_MODEL_REVISION={MOSS_MODEL_REVISION} "
                     f"bash {REMOTE}/moss_setup.sh", check=True, stdout=log, stderr=subprocess.STDOUT)


def make_share(machine, share, card, out):
    """One share of the takes on one card, the takes back into `out`. A generator that fails raises
    spread.JobFailed (what it made still comes back)."""
    number, jobs = share
    log_folder, host = machine["folder"], machine["host"]
    (log_folder / f"jobs-{number}.json").write_text(json.dumps(jobs))
    batch.copy(log_folder, [log_folder / f"jobs-{number}.json"], f"root@{host}:{REMOTE}/")
    try:
        with (log_folder / f"generate-{number}.log").open("w") as log:
            done = batch.remote(log_folder, host, f"cd {REMOTE} && CUDA_VISIBLE_DEVICES={card} TORCHDYNAMO_DISABLE=1 "
                                f"PYTHONUNBUFFERED=1 /root/venv/bin/python moss_generate.py {REMOTE}/jobs-{number}.json "
                                f"{number}", stdout=log, stderr=subprocess.STDOUT)
    finally:
        out.mkdir(parents=True, exist_ok=True)
        batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{out}/")
    spread.raise_for(done.returncode, f"share {number} ({log_folder / f'generate-{number}.log'})")


def join_scores(out):
    """Every share's CLAP scores in out/scores.json, where the picker reads them."""
    scores = {}
    for path in sorted(out.glob("scores-*.json")):
        scores.update(json.loads(path.read_text()))
    if scores:
        (out / "scores.json").write_text(json.dumps(scores, indent=1))


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


# The Kubernetes path (SCORE_CLOUD=k8s): each share a Kubernetes Job of the moss image (tools/cloud/images/moss/, its
# moss-run wrapper runs moss_generate.py from the job's code with MOSS and CLAP from the node cache), through
# tools/cloud/k8s/cluster_jobs.py; the takes come back into the picker's cache as the machines' do.
CLUSTER_SHARES = 8
CLUSTER_MODELS = ["moss-soundeffect-v2", "clap-larger-general"]


def cluster_job(number, jobs, share_file, out):
    """One share as the cluster runs it: its jobs file (written to `share_file` here) up, its takes back into
    `out`."""
    share_file.write_text(json.dumps(jobs))
    return {"command": ["moss-run", f"{REMOTE}/jobs-{number}.json", str(number)],
            "code": ["tools/props/cloud/moss_generate.py"], "models": CLUSTER_MODELS,
            "inputs": [{"local": str(share_file), "path": f"{REMOTE}/jobs-{number}.json"}],
            "outputs": [{"path": f"{REMOTE}/out", "local": str(out)}],
            "minutes": max(15.0, SETUP_MINUTES + MINUTES_A_CLIP * len(jobs) * 2)}


def main_on_cluster(options, jobs):
    """main() under SCORE_CLOUD=k8s: the page's takes in up to CLUSTER_SHARES shares as one run of the cluster on the
    moss-sound kind's classes (capacity.py), then the scores and the manifest as the machines' run writes them."""
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import cluster_jobs

    parts = min(len(jobs), CLUSTER_SHARES)
    if options.dry_run:
        batch.say(f"{len(jobs)} takes in {parts} shares for the cluster")
        return
    folder = batch.BATCHES / time.strftime("moss-k8s-%Y%m%d-%H%M%S")
    folder.mkdir(parents=True)
    out = OUT / options.page
    work = [cluster_job(number, jobs[number::parts], folder / f"jobs-{number}.json", out) for number in range(parts)]
    failed = cluster_jobs.run("moss-sound", work, options.who, image="moss")
    if out.exists():
        join_scores(out)
        made = write_manifest(out, jobs)
        batch.say(f"moss: {len(made)} takes on the cluster" + (f"; shares {failed} failed" if failed else ""))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("page")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    jobs = jobs_for(options.page)
    if not jobs:
        raise SystemExit(f"no sound on the '{options.page}' page has prompts in data/sound/sounds.json")
    if provider.on_cluster():
        main_on_cluster(options, jobs)
        return
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(jobs, account)
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
    made = []
    try:
        parts = min(len(jobs), count * capacity.slots_for("moss-sound"))
        shares = spread.Shares([(number, jobs[number::parts]) for number in range(parts)], deadline=run.deadline)
        spread.on_machines(run, account, found, count, "moss-sound", shares, set_up,
                           lambda machine, share, card: make_share(machine, share, card, out))
        if not run.machines:
            raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        if out.exists():
            join_scores(out)
            made = write_manifest(out, jobs)
        entry = record(run, run.machines, started, out, made)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        print(json.dumps(entry))


if __name__ == "__main__":
    main()
