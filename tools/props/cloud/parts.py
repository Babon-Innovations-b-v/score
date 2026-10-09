"""Split pictured objects into parts with PartCrafter on rented cloud cards, bring the parts back, delete the
machines (job robust-exp, 2026-10-06: the part splitter tried against labelling parts from the clean picture).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/parts.py <folder of pictures> --who "<session>" \
        [--parts 4,6] [--dry-run]

PartCrafter (wgsxm/PartCrafter, MIT code and weights, arXiv 2506.05573) makes a model of N separate parts from one
picture. Each picture in the folder (a cut-out on white) is run once for every part count; the parts come back as
<folder>/parts/<picture>-<n>/part_XX.glb. The runs are spread over as many cards as finish them in about the setup
and one run's time (spread.py), each card taking the next run as it finishes one. Its optional background remover (briaai/RMBG-1.4) is non-commercial: it is
never downloaded or used; the pictures are cut out already. The owner's limits, the self-delete, the watchdog and
the delete are batch.py's, as for every machine. No model of ours is made: these parts only say where a model's
part boundaries are (labels.py). Under SCORE_CLOUD=k8s the same runs go to the Kubernetes cluster as Jobs of the
parts image (tools/cloud/k8s/cluster_jobs.py); the machines stay the default.
"""
import argparse
import json
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

REMOTE = pathlib.PurePosixPath("/root/parts")
# Pinned: PartCrafter's main on 2026-10-06 (last push 2026-04-16).
PARTCRAFTER = "main"
SETUP_MINUTES = 20
MINUTES_A_RUN = 2


def price(runs, account):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and allowed minutes."""
    found = batch.offers(list(capacity.classes_for("parts")))
    if not found:
        raise SystemExit("no card that holds this job is sold in the zones used")
    count = capacity.machines_for(runs, MINUTES_A_RUN, SETUP_MINUTES, capacity.slots_for("parts"))
    minutes = capacity.spread_minutes(runs, MINUTES_A_RUN, SETUP_MINUTES, count, capacity.slots_for("parts"))
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{runs} PartCrafter runs on {count} card{'s' if count > 1 else ''}: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * count:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * count, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, count, ledger.minutes_allowed(dearest * count, spent)


def run_line(picture, parts, card=0):
    tag = f"{pathlib.Path(picture).stem}-{parts}"
    arguments = ["scripts/inference_partcrafter.py", "--image_path", f"{REMOTE}/in/{picture}", "--num_parts",
                 str(parts), "--tag", tag, "--output_dir", f"{REMOTE}/out"]
    # Its src/ is imported from the checkout; its render helpers load OpenGL and pyglet at import, headless here.
    environment = (f"CUDA_VISIBLE_DEVICES={card} PYTHONPATH=. PYOPENGL_PLATFORM=egl PYGLET_HEADLESS=true "
                   "PYTHONUNBUFFERED=1")
    return f"cd {REMOTE}/PartCrafter && {environment} /root/venv/bin/python {shlex.join(arguments)}"


def set_up(machine, folder):
    """PartCrafter and every picture onto one machine."""
    log_folder, host = machine["folder"], machine["host"]
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}/in {REMOTE}/out {REMOTE}/repo/tools/props/cloud", check=True)
    batch.copy(log_folder, [HERE / "parts_setup.sh"], f"root@{host}:{REMOTE}/repo/tools/props/cloud/")
    batch.copy(log_folder, sorted(folder.glob("*.png")), f"root@{host}:{REMOTE}/in/")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"env PARTCRAFTER={PARTCRAFTER} bash "
                     f"{REMOTE}/repo/tools/props/cloud/parts_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def split_one(machine, share, card, folder, timings):
    """One picture at one part count on a machine, its parts back; a run that fails raises spread.JobFailed."""
    picture, parts = share
    log_folder, host = machine["folder"], machine["host"]
    began = time.time()
    try:
        with (log_folder / f"{pathlib.Path(picture).stem}-{parts}.log").open("w") as log:
            done = batch.remote(log_folder, host, run_line(picture, parts, card), stdout=log, stderr=subprocess.STDOUT)
    finally:
        (folder / "parts").mkdir(exist_ok=True)
        batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{folder / 'parts'}/", "--exclude", "*.gif")
    timings[f"{picture}-{parts}"] = {"seconds": round(time.time() - began, 1), "ok": done.returncode == 0,
                                     "machine": log_folder.name}
    batch.say(f"parts: {picture} x{parts} {timings[f'{picture}-{parts}']}")
    if done.returncode == 0:
        machine.setdefault("unit_seconds", []).append(timings[f"{picture}-{parts}"]["seconds"])
    spread.raise_for(done.returncode, f"{picture} x{parts}")


def record(run, machines, folder, started, runs):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": "parts", "folder": str(folder), "runs": runs,
             **ledger.machines_record(machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"parts: {entry['wall_minutes']:.1f} min on {len(entry['machines'])} machines, "
              f"€{entry['euros']:.2f}")
    return entry


# The Kubernetes path (SCORE_CLOUD=k8s): each run a Kubernetes Job of the parts image (tools/cloud/images/parts/, its
# parts-run wrapper and PartCrafter's weights from the node cache), through tools/cloud/k8s/cluster_jobs.py.
CLUSTER_MINUTES = 20


def cluster_job(picture, parts):
    """One picture at one part count as the cluster runs it: the parts back to <folder>/parts/<picture>-<n>/ as the
    machine runner brings them, without the preview GIFs."""
    tag = f"{picture.stem}-{parts}"
    line = (f"mkdir -p /work/out && parts-run scripts/inference_partcrafter.py --image_path /work/in/{picture.name} "
            f"--num_parts {parts} --tag {tag} --output_dir /work/out && rm -f /work/out/{tag}/*.gif")
    return {"command": ["bash", "-c", line], "inputs": [{"local": str(picture), "path": f"/work/in/{picture.name}"}],
            "outputs": [{"path": f"/work/out/{tag}", "local": str(picture.parent / "parts" / tag)}],
            "models": ["partcrafter"], "minutes": CLUSTER_MINUTES}


def main_on_cluster(options, counts):
    """main() under SCORE_CLOUD=k8s: every picture at every part count as one run of the cluster, on the parts kind's
    classes (capacity.py); timings.json says which came back."""
    sys.path.insert(0, str(REPO / "tools/cloud/k8s"))
    import cluster_jobs

    shares = [(picture, parts) for picture in sorted(options.folder.resolve().glob("*.png")) for parts in counts]
    if options.dry_run:
        batch.say(f"{len(shares)} PartCrafter runs for the cluster")
        return
    failed = set(cluster_jobs.run("parts", [cluster_job(*share) for share in shares], options.who))
    (options.folder / "parts").mkdir(exist_ok=True)
    timings = {f"{picture.name}-{parts}": {"ok": number not in failed, "machine": "k8s"}
               for number, (picture, parts) in enumerate(shares)}
    (options.folder / "parts" / "timings.json").write_text(json.dumps(timings, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=pathlib.Path, help="a folder of cut-out pictures on white")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--parts", default="4,6", help="the part counts to try, comma separated")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    counts = [int(value) for value in options.parts.split(",")]
    runs = len(list(options.folder.glob("*.png"))) * len(counts)
    if provider.on_cluster():
        main_on_cluster(options, counts)
        return
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(runs, account)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures
    started = time.time()
    run_folder = batch.BATCHES / time.strftime("parts-%Y%m%d-%H%M%S")
    run_folder.mkdir(parents=True)
    run = pictures.Run(run_folder, started + allowed_minutes * 60)
    shares = spread.Shares([(picture, parts) for picture in sorted(path.name for path in options.folder.glob("*.png"))
                            for parts in counts], deadline=run.deadline)
    timings = {}
    try:
        spread.on_machines(run, account, found, count, "parts", shares,
                           lambda machine: set_up(machine, options.folder),
                           lambda machine, share, card: split_one(machine, share, card, options.folder, timings))
        if not run.machines:
            raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        (options.folder / "parts").mkdir(exist_ok=True)
        (options.folder / "parts" / "timings.json").write_text(json.dumps(timings, indent=1))
        entry = record(run, run.machines, options.folder, started, runs)
        (options.folder / "cloud.json").write_text(json.dumps(entry, indent=1))


if __name__ == "__main__":
    main()
