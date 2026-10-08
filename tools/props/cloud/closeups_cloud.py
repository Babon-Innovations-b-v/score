"""Render and cut a world's item close-ups on one rented Scaleway card (scene/closeups.py plans them here, the card
does scene/closeups_gpu.py), then bring the pictures back and delete the machine.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/closeups_cloud.py <closeups folder> --splats <splats.ply> \
        --who "<session>" [--matte <pictures folder>] [--dry-run]

The closeups folder holds cameras.json (closeups.py); the pictures land beside it in renders/. --matte also cuts every
picture in a folder out with image-to-3dlab's own remover on the same machine (the object maker's input, made clean
by a picture model first), each coming back beside it as <name>__matted.png. No model is made: the
close-ups are page A's review material and the object maker's input, so this needs no approved inventory, but the
owner's limits, the self-delete, the watchdog and the delete are batch.py's, as for every machine.
"""
import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import scaleway  # noqa: E402
from local_models import ALLOW  # noqa: E402
from paths import REPO  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/closeups")
# The SAM 3 weights the scene steps use (scene.py): the gated facebook/sam3 is not open to the account.
SAM3_WEIGHTS = os.environ.get("SAM3_WEIGHTS", "jetjodh/sam3")
# First guesses until measured: renting and installing torch, gsplat and SAM 2.1; then a camera every few seconds.
SETUP_MINUTES = 15
SECONDS_A_CAMERA = 12
SECONDS_A_MATTE = 3


def price(cameras, project, mattes=0):
    """Print the estimate and refuse what passes the owner's limits; the offers and allowed minutes."""
    found = batch.offers(list(capacity.types_for("closeups")))
    if not found:
        raise SystemExit("no card that holds this job is sold in the zones used")
    minutes = SETUP_MINUTES + (cameras * SECONDS_A_CAMERA + mattes * SECONDS_A_MATTE) / 60
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(project)
    batch.say(f"{cameras} close-ups on one card: about {minutes:.0f} min, €{ledger.cost(minutes, dearest):.2f}; "
              f"€{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, ledger.minutes_allowed(dearest, spent)


def step_line(python, arguments):
    environment = f"{ALLOW}=1 PYTHONUNBUFFERED=1 SAM3_WEIGHTS={shlex.quote(SAM3_WEIGHTS)} IMAGE_TO_3DLAB={REMOTE}/lab"
    return f"cd {REMOTE}/repo && env {environment} {python} {shlex.join(arguments)}"


def work_on(run, machine, folder, splats, pictures_folder=None):
    """One machine from boot to delete: set it up, render and cut, bring the pictures back."""
    import pictures
    log_folder = machine["folder"]
    stop = threading.Event()
    try:
        host = machine["host"]
        batch.arm_self_delete(log_folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(log_folder, host, stop), daemon=True).start()
        batch.remote(log_folder, host, f"mkdir -p {REMOTE}/repo/tools {REMOTE}/out", check=True)
        batch.copy(log_folder, [REPO / "tools" / "props"], f"root@{host}:{REMOTE}/repo/tools/", "--exclude", "__pycache__")
        batch.copy(log_folder, [splats, folder / "cameras.json"], f"root@{host}:{REMOTE}/")
        batch.remote(log_folder, host, f"mkdir -p {REMOTE}/lab {REMOTE}/pictures", check=True)
        batch.copy(log_folder, [batch.LAB / "image_to_3dlab"], f"root@{host}:{REMOTE}/lab/", "--exclude", "__pycache__")
        if pictures_folder:
            batch.copy(log_folder, sorted(pathlib.Path(pictures_folder).glob("*.png")), f"root@{host}:{REMOTE}/pictures/")
        with (log_folder / "setup.log").open("w") as log:
            batch.remote(log_folder, host, f"env SAM3_WEIGHTS={shlex.quote(SAM3_WEIGHTS)} bash "
                         f"{REMOTE}/repo/tools/props/cloud/closeups_setup.sh", check=True, stdout=log, stderr=subprocess.STDOUT)
        batch.say(f"{log_folder.name} ready after {(time.time() - machine['created']) / 60:.1f} min")
        gpu = "tools/props/scene/closeups_gpu.py"
        steps = [("render", "/root/venv/bin/python", [gpu, "render", f"{REMOTE}/{pathlib.Path(splats).name}",
                                                     f"{REMOTE}/cameras.json", f"{REMOTE}/out"]),
                 ("segment", "/root/venv2/bin/python", [gpu, "segment", f"{REMOTE}/cameras.json", f"{REMOTE}/out"])]
        if pictures_folder:
            steps.append(("matte", "/root/venv2/bin/python", [gpu, "matte", f"{REMOTE}/pictures"]))
        try:
            for name, python, arguments in steps:
                batch.say(f"close-ups: {name}")
                with (log_folder / f"{name}.log").open("w") as log:
                    batch.remote(log_folder, host, step_line(python, arguments), check=True, stdout=log,
                                 stderr=subprocess.STDOUT)
        finally:
            (folder / "renders").mkdir(exist_ok=True)
            batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{folder / 'renders'}/", "--exclude", "*.npy")
            if pictures_folder:
                batch.copy(log_folder, [f"root@{host}:{REMOTE}/pictures/"], f"{pictures_folder}/", "--include",
                           "*__matted.png", "--exclude", "*")
    finally:
        stop.set()
        batch.delete_machine(machine)


def record(run, machines, folder, started, cameras):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": "closeups", "folder": str(folder), "cameras": cameras,
             **ledger.machines_record(machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"close-ups: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machine, "
              f"€{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("folder", type=pathlib.Path, help="the closeups folder holding cameras.json")
    parser.add_argument("--splats", type=pathlib.Path, required=True)
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--matte", type=pathlib.Path, help="a folder of pictures to cut out with image-to-3dlab's remover")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    cameras = len(json.loads((options.folder / "cameras.json").read_text())["cameras"])
    project = scaleway.project_id()
    batch.sweep(project)
    mattes = len(list(options.matte.glob("*.png"))) if options.matte else 0
    found, allowed_minutes = price(cameras, project, mattes)
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
        work_on(run, machines[0], options.folder, options.splats, options.matte)
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, run.machines, options.folder, started, cameras)
        (options.folder / "cloud.json").write_text(json.dumps(entry, indent=1))


if __name__ == "__main__":
    main()
