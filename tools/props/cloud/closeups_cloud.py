"""Render and cut a world's item close-ups on one rented Scaleway card (scene/closeups.py plans them here, the card
does scene/closeups_gpu.py), then bring the pictures back and delete the machine.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/closeups_cloud.py <closeups folder> --splats <splats.ply> \
        --who "<session>" [--dry-run]

The closeups folder holds cameras.json (closeups.py); the pictures land beside it in renders/. No model is made: the
close-ups are page A's review material and the object maker's input, so this needs no approved inventory, but the
owner's limits, the self-delete, the watchdog and the delete are batch.py's, as for every machine.
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
from local_models import ALLOW  # noqa: E402
from paths import REPO  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/closeups")
# First guesses until measured: renting and installing torch, gsplat and SAM 2.1; then a camera every few seconds.
SETUP_MINUTES = 15
SECONDS_A_CAMERA = 6


def price(cameras, project):
    """Print the estimate and refuse what passes the owner's limits; the offers and allowed minutes."""
    found = batch.offers(list(batch.TYPES[:1]))
    if not found:
        raise SystemExit("no L4 card is sold in the zones used")
    minutes = SETUP_MINUTES + cameras * SECONDS_A_CAMERA / 60
    dearest = max(offer[0] for offer in found)
    spent = max(scaleway.month_spend(project), ledger.month_total(ledger.this_month(), ledger.entries()))
    batch.say(f"{cameras} close-ups on one card: about {minutes:.0f} min, €{ledger.cost(minutes, dearest):.2f}; "
              f"€{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest, spent)


def work_on(run, machine, folder, splats):
    """One machine from boot to delete: set it up, render and cut, bring the pictures back."""
    import pictures
    log_folder = machine["folder"]
    stop = threading.Event()
    try:
        host = batch.wait_for_machine(log_folder, machine["id"], machine["zone"])
        batch.arm_self_delete(log_folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(log_folder, host, stop), daemon=True).start()
        batch.remote(log_folder, host, f"mkdir -p {REMOTE}/repo/tools {REMOTE}/out", check=True)
        batch.copy(log_folder, [REPO / "tools" / "props"], f"root@{host}:{REMOTE}/repo/tools/", "--exclude", "__pycache__")
        batch.copy(log_folder, [splats, folder / "cameras.json"], f"root@{host}:{REMOTE}/")
        with (log_folder / "setup.log").open("w") as log:
            batch.remote(log_folder, host, f"bash {REMOTE}/repo/tools/props/cloud/closeups_setup.sh", check=True,
                         stdout=log, stderr=subprocess.STDOUT)
        batch.say(f"{log_folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        step = ["tools/props/scene/closeups_gpu.py", f"{REMOTE}/{pathlib.Path(splats).name}",
                f"{REMOTE}/cameras.json", f"{REMOTE}/out"]
        line = f"cd {REMOTE}/repo && env {ALLOW}=1 PYTHONUNBUFFERED=1 /root/venv/bin/python {shlex.join(step)}"
        try:
            with (log_folder / "closeups.log").open("w") as log:
                batch.remote(log_folder, host, line, check=True, stdout=log, stderr=subprocess.STDOUT)
        finally:
            (folder / "renders").mkdir(exist_ok=True)
            batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{folder / 'renders'}/")
    finally:
        stop.set()
        batch.delete_machine(machine)


def record(run, machines, folder, started, cameras):
    rows = [{"type": machine["type"], "zone": machine["zone"],
             "minutes": (machine["deleted"] - machine["created"]) / 60,
             "euros": ledger.cost((machine["deleted"] - machine["created"]) / 60, machine["price"])}
            for machine in machines]
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": "closeups", "folder": str(folder), "cameras": cameras, "machines": rows,
             "euros": sum(row["euros"] for row in rows), "machine_minutes": sum(row["minutes"] for row in rows),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"close-ups: {entry['wall_minutes']:.0f} min on {len(rows)} machine, €{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=pathlib.Path, help="the closeups folder holding cameras.json")
    parser.add_argument("--splats", type=pathlib.Path, required=True)
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    cameras = len(json.loads((options.folder / "cameras.json").read_text())["cameras"])
    project = scaleway.project_id()
    batch.sweep(project)
    found, allowed_minutes = price(cameras, project)
    if options.dry_run:
        return
    scaleway.allow_key(project, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures
    started = time.time()
    run_folder = batch.BATCHES / time.strftime("closeups-%Y%m%d-%H%M%S")
    run_folder.mkdir(parents=True)
    run = pictures.Run(run_folder, started + allowed_minutes * 60)
    machines = []
    try:
        machines = pictures.rent_machines(run, project, found, 1)
        if not machines:
            raise SystemExit("no card could be rented")
        work_on(run, machines[0], options.folder, options.splats)
    finally:
        for machine in machines:
            batch.delete_machine(machine)
        entry = record(run, machines, options.folder, started, cameras)
        (options.folder / "cloud.json").write_text(json.dumps(entry, indent=1))


if __name__ == "__main__":
    main()
