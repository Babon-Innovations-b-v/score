"""Split pictured objects into parts with PartCrafter on one rented Scaleway card, bring the parts back, delete the
machine (job robust-exp, 2026-10-06: the part splitter tried against labelling parts from the clean picture).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/parts.py <folder of pictures> --who "<session>" \
        [--parts 4,6] [--dry-run]

PartCrafter (wgsxm/PartCrafter, MIT code and weights, arXiv 2506.05573) makes a model of N separate parts from one
picture. Each picture in the folder (a cut-out on white) is run once for every part count; the parts come back as
<folder>/parts/<picture>-<n>/part_XX.glb. Its optional background remover (briaai/RMBG-1.4) is non-commercial: it is
never downloaded or used; the pictures are cut out already. The owner's limits, the self-delete, the watchdog and
the delete are batch.py's, as for every machine. No model of ours is made: these parts only say where a model's
part boundaries are (labels.py).
"""
import argparse
import json
import pathlib
import shlex
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import ledger  # noqa: E402
import scaleway  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/parts")
# Pinned: PartCrafter's main on 2026-10-06 (last push 2026-04-16).
PARTCRAFTER = "main"
SETUP_MINUTES = 20
MINUTES_A_RUN = 2


def price(runs, project):
    """Print the estimate and refuse what passes the owner's limits; the offers and allowed minutes."""
    found = batch.offers(list(batch.TYPES[:1]))
    if not found:
        raise SystemExit("no L4 card is sold in the zones used")
    minutes = SETUP_MINUTES + runs * MINUTES_A_RUN
    dearest = max(offer[0] for offer in found)
    spent = max(scaleway.month_spend(project), ledger.month_total(ledger.this_month(), ledger.entries()))
    batch.say(f"{runs} PartCrafter runs on one card: about {minutes:.0f} min, €{ledger.cost(minutes, dearest):.2f}; "
              f"€{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest, spent)


def run_line(picture, parts):
    tag = f"{pathlib.Path(picture).stem}-{parts}"
    arguments = ["scripts/inference_partcrafter.py", "--image_path", f"{REMOTE}/in/{picture}", "--num_parts",
                 str(parts), "--tag", tag, "--output_dir", f"{REMOTE}/out"]
    # Its src/ is imported from the checkout; its render helpers load OpenGL and pyglet at import, headless here.
    environment = "PYTHONPATH=. PYOPENGL_PLATFORM=egl PYGLET_HEADLESS=true PYTHONUNBUFFERED=1"
    return f"cd {REMOTE}/PartCrafter && {environment} /root/venv/bin/python {shlex.join(arguments)}"


def work_on(run, machine, folder, counts):
    """One machine from boot to delete: set it up, split every picture at every part count, bring the parts back."""
    import pictures
    log_folder = machine["folder"]
    stop = threading.Event()
    try:
        host = batch.wait_for_machine(log_folder, machine["id"], machine["zone"])
        batch.arm_self_delete(log_folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(log_folder, host, stop), daemon=True).start()
        batch.remote(log_folder, host, f"mkdir -p {REMOTE}/in {REMOTE}/out {REMOTE}/repo/tools/props/cloud", check=True)
        batch.copy(log_folder, [HERE / "parts_setup.sh"], f"root@{host}:{REMOTE}/repo/tools/props/cloud/")
        batch.copy(log_folder, sorted(folder.glob("*.png")), f"root@{host}:{REMOTE}/in/")
        with (log_folder / "setup.log").open("w") as log:
            batch.remote(log_folder, host, f"env PARTCRAFTER={PARTCRAFTER} bash "
                         f"{REMOTE}/repo/tools/props/cloud/parts_setup.sh", check=True, stdout=log,
                         stderr=subprocess.STDOUT)
        batch.say(f"{log_folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        timings = {}
        try:
            for picture in sorted(path.name for path in folder.glob("*.png")):
                for parts in counts:
                    began = time.time()
                    with (log_folder / f"{pathlib.Path(picture).stem}-{parts}.log").open("w") as log:
                        done = batch.remote(log_folder, host, run_line(picture, parts), stdout=log,
                                            stderr=subprocess.STDOUT)
                    timings[f"{picture}-{parts}"] = {"seconds": round(time.time() - began, 1),
                                                     "ok": done.returncode == 0}
                    batch.say(f"parts: {picture} x{parts} {timings[f'{picture}-{parts}']}")
        finally:
            (folder / "parts").mkdir(exist_ok=True)
            batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{folder / 'parts'}/", "--exclude", "*.gif")
            (folder / "parts" / "timings.json").write_text(json.dumps(timings, indent=1))
    finally:
        stop.set()
        batch.delete_machine(machine)


def record(run, machines, folder, started, runs):
    rows = [{"type": machine["type"], "zone": machine["zone"],
             "minutes": (machine["deleted"] - machine["created"]) / 60,
             "euros": ledger.cost((machine["deleted"] - machine["created"]) / 60, machine["price"])}
            for machine in machines]
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": "parts", "folder": str(folder), "runs": runs, "machines": rows,
             "euros": sum(row["euros"] for row in rows), "machine_minutes": sum(row["minutes"] for row in rows),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"parts: {entry['wall_minutes']:.0f} min on {len(rows)} machine, €{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=pathlib.Path, help="a folder of cut-out pictures on white")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--parts", default="4,6", help="the part counts to try, comma separated")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    counts = [int(value) for value in options.parts.split(",")]
    runs = len(list(options.folder.glob("*.png"))) * len(counts)
    project = scaleway.project_id()
    batch.sweep(project)
    found, allowed_minutes = price(runs, project)
    if options.dry_run:
        return
    scaleway.allow_key(project, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures
    started = time.time()
    run_folder = batch.BATCHES / time.strftime("parts-%Y%m%d-%H%M%S")
    run_folder.mkdir(parents=True)
    run = pictures.Run(run_folder, started + allowed_minutes * 60)
    machines = []
    try:
        machines = pictures.rent_machines(run, project, found, 1)
        if not machines:
            raise SystemExit("no card could be rented")
        work_on(run, machines[0], options.folder, counts)
    finally:
        for machine in machines:
            batch.delete_machine(machine)
        entry = record(run, machines, options.folder, started, runs)
        (options.folder / "cloud.json").write_text(json.dumps(entry, indent=1))


if __name__ == "__main__":
    main()
