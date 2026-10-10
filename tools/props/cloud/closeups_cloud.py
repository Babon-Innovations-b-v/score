"""Render and cut a world's item close-ups on rented cloud cards (scene/closeups.py plans them here, the cards
do scene/closeups_gpu.py), then bring the pictures back and delete the machines.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/closeups_cloud.py <closeups folder> --splats <splats.ply> \
        --who "<session>" [--matte <pictures folder>] [--dry-run]

The closeups folder holds cameras.json (closeups.py); the pictures land beside it in renders/. --matte also cuts every
picture in a folder out with image-to-3dlab's own remover on one of the machines (the object maker's input, made clean
by a picture model first), each coming back beside it as <name>__matted.png. No model is made: the
close-ups are page A's review material and the object maker's input, so this needs no approved inventory, but the
owner's limits, the self-delete, the watchdog and the delete are batch.py's, as for every machine. Many cameras are
cut into shares over as many cards as render them in about the setup's time (spread.py), each card rendering and
cutting the next share as it finishes one.
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
from local_models import ALLOW  # noqa: E402
from paths import REPO  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/closeups")
# The SAM 3 weights the scene steps use (scene.py): the gated facebook/sam3 is not open to the account.
SAM3_WEIGHTS = os.environ.get("SAM3_WEIGHTS", "jetjodh/sam3")
# First guesses until measured: renting and installing torch, gsplat and SAM 2.1; then a camera every few seconds.
SETUP_MINUTES = 15
SECONDS_A_CAMERA = 12
SECONDS_A_MATTE = 3


def price(cameras, account, mattes=0):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and allowed minutes."""
    found = batch.offers(list(capacity.classes_for("closeups")))
    if not found:
        raise SystemExit("no card that holds this job is sold in the zones used")
    count = capacity.machines_for(cameras, SECONDS_A_CAMERA / 60, SETUP_MINUTES, capacity.slots_for("closeups"))
    minutes = capacity.spread_minutes(cameras, SECONDS_A_CAMERA / 60, SETUP_MINUTES, count) + mattes * SECONDS_A_MATTE / 60
    what = f"{cameras} close-ups on {count} card{'s' if count > 1 else ''}"
    return found, count, batch.priced(found, minutes, count, what, account)


def step_line(python, arguments):
    environment = f"{ALLOW}=1 PYTHONUNBUFFERED=1 SAM3_WEIGHTS={shlex.quote(SAM3_WEIGHTS)} IMAGE_TO_3DLAB={REMOTE}/lab"
    return f"cd {REMOTE}/repo && env {environment} {python} {shlex.join(arguments)}"


def set_up(machine, splats):
    """The scripts, the splats, the lab's remover and the models onto one machine."""
    log_folder, host = machine["folder"], machine["host"]
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}/repo/tools {REMOTE}/out", check=True)
    batch.copy(log_folder, [REPO / "tools" / "props"], f"root@{host}:{REMOTE}/repo/tools/", "--exclude", "__pycache__")
    batch.copy(log_folder, [splats], f"root@{host}:{REMOTE}/")
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}/lab {REMOTE}/pictures", check=True)
    batch.copy(log_folder, [batch.LAB / "image_to_3dlab"], f"root@{host}:{REMOTE}/lab/", "--exclude", "__pycache__")
    with (log_folder / "setup.log").open("w") as log:
        batch.remote(log_folder, host, f"env SAM3_WEIGHTS={shlex.quote(SAM3_WEIGHTS)} bash "
                     f"{REMOTE}/repo/tools/props/cloud/closeups_setup.sh", check=True, stdout=log, stderr=subprocess.STDOUT)


def run_step(machine, name, python, arguments, card):
    """One step on a card of the machine; a step that fails raises spread.JobFailed."""
    log_folder, host = machine["folder"], machine["host"]
    batch.say(f"close-ups on {log_folder.name}: {name}")
    with (log_folder / f"{name}.log").open("w") as log:
        done = batch.remote(log_folder, host, f"CUDA_VISIBLE_DEVICES={card} " + step_line(python, arguments),
                            stdout=log, stderr=subprocess.STDOUT)
    spread.raise_for(done.returncode, f"{name} ({log_folder / f'{name}.log'})")


def do_share(machine, share, card, folder, splats, pictures_folder):
    """One share: a set of cameras rendered and cut, or the folder of pictures matted; what it made comes back."""
    log_folder, host = machine["folder"], machine["host"]
    gpu = "tools/props/scene/closeups_gpu.py"
    try:
        if share[0] == "matte":
            batch.copy(log_folder, sorted(pathlib.Path(pictures_folder).glob("*.png")), f"root@{host}:{REMOTE}/pictures/")
            run_step(machine, "matte", "/root/venv2/bin/python", [gpu, "matte", f"{REMOTE}/pictures"], card)
            return
        _, number, plan = share
        cameras = f"{REMOTE}/cameras-{number}.json"
        (log_folder / f"cameras-{number}.json").write_text(json.dumps(plan))
        batch.copy(log_folder, [log_folder / f"cameras-{number}.json"], f"root@{host}:{cameras}")
        run_step(machine, f"render-{number}", "/root/venv/bin/python",
                 [gpu, "render", f"{REMOTE}/{pathlib.Path(splats).name}", cameras, f"{REMOTE}/out"], card)
        run_step(machine, f"segment-{number}", "/root/venv2/bin/python", [gpu, "segment", cameras, f"{REMOTE}/out"],
                 card)
    finally:
        (folder / "renders").mkdir(exist_ok=True)
        batch.copy(log_folder, [f"root@{host}:{REMOTE}/out/"], f"{folder / 'renders'}/", "--exclude", "*.npy")
        if share[0] == "matte":
            batch.copy(log_folder, [f"root@{host}:{REMOTE}/pictures/"], f"{pictures_folder}/", "--include",
                       "*__matted.png", "--exclude", "*")


def shares_of(plan, machines, pictures_folder):
    """The cameras cut into a share for each machine, each a copy of the plan holding its cameras, and the matting as
    a share of its own."""
    cameras = plan["cameras"]
    parts = max(1, min(len(cameras), machines))
    shares = [("cameras", number, dict(plan, cameras=cameras[number::parts])) for number in range(parts)]
    return shares + ([("matte",)] if pictures_folder else [])


def record(run, machines, folder, started, cameras):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": "closeups", "folder": str(folder), "cameras": cameras,
             **ledger.machines_record(machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"close-ups: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machines, "
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
    account = cloud.account()
    batch.sweep(account)
    mattes = len(list(options.matte.glob("*.png"))) if options.matte else 0
    found, count, allowed_minutes = price(cameras, account, mattes)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures
    started = time.time()
    run_folder = batch.BATCHES / time.strftime("closeups-%Y%m%d-%H%M%S")
    run_folder.mkdir(parents=True)
    run = pictures.Run(run_folder, started + allowed_minutes * 60)
    plan = json.loads((options.folder / "cameras.json").read_text())
    shares = spread.Shares(shares_of(plan, count, options.matte), deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, count, "closeups", shares,
                           lambda machine: set_up(machine, options.splats),
                           lambda machine, share, card: do_share(machine, share, card, options.folder, options.splats,
                                                                 options.matte))
        if not run.machines:
            raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, run.machines, options.folder, started, cameras)
        (options.folder / "cloud.json").write_text(json.dumps(entry, indent=1))


if __name__ == "__main__":
    main()
