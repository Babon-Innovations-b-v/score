"""Mask every inventory row's thing on its view's picture with SAM 3 on one rented card, for the box check, then
delete the machine.

    .venv/bin/python tools/props/cloud/box_masks_cloud.py <jobs.json> <out.json> [--dry-run]

The jobs are box_masks.py's ([{"picture": <a picture path here>, "rows": [{"key", "noun", "box"}]}], written by
box_check.py --masks); the pictures go up with them and the measured instances come back as <out.json>. Renting,
the owner's limits, the self-delete and deleting are batch.py's, as for the judge (judge.py).
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
import pictures  # noqa: E402
import spread  # noqa: E402
from local_models import ALLOW  # noqa: E402
from paths import REPO  # noqa: E402
from provider import cloud  # noqa: E402

KIND = "segment"
REMOTE = pathlib.PurePosixPath("/root/masks")
# The SAM 3 weights the scene steps use (scene.py): the gated facebook/sam3 is not open to the account.
SAM3_WEIGHTS = os.environ.get("SAM3_WEIGHTS", "jetjodh/sam3")
# First guesses until a run is measured: installing torch and fetching SAM 3, then each picture's nouns.
SETUP_MINUTES = 10
SECONDS_A_PICTURE = 20


def price(jobs, account):
    """Print the estimate and refuse what passes the owner's limits; the offers and the minutes allowed."""
    found = batch.offers(list(capacity.classes_for(KIND)))
    if not found:
        raise SystemExit("no card for SAM 3 is sold in the zones used")
    minutes = SETUP_MINUTES + len(jobs) * SECONDS_A_PICTURE / 60
    return found, batch.priced(found, minutes, 1, f"{len(jobs)} pictures on 1 card", account)


def set_up(machine):
    """The scene tools, the setup and SAM 3 onto one machine."""
    folder, host = machine["folder"], machine["host"]
    batch.remote(folder, host, f"mkdir -p {REMOTE}/repo/tools {REMOTE}/in", check=True)
    batch.copy(folder, [REPO / "tools" / "props"], f"root@{host}:{REMOTE}/repo/tools/", "--exclude", "__pycache__")
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, f"env SAM3_WEIGHTS={shlex.quote(SAM3_WEIGHTS)} bash "
                     f"{REMOTE}/repo/tools/props/cloud/box_masks_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)


def run_jobs(machine, share, card, jobs, out):
    """Every picture's rows on the card, the measured instances back as `out`."""
    folder, host = machine["folder"], machine["host"]
    listing = folder / "jobs.json"
    listing.write_text(json.dumps([dict(job, picture=f"{number}-{pathlib.Path(job['picture']).name}")
                                   for number, job in enumerate(jobs)]))
    for number, job in enumerate(jobs):
        batch.copy(folder, [job["picture"]], f"root@{host}:{REMOTE}/in/{number}-{pathlib.Path(job['picture']).name}")
    batch.copy(folder, [listing], f"root@{host}:{REMOTE}/in/")
    began = time.time()
    environment = f"{ALLOW}=1 PYTHONUNBUFFERED=1 SAM3_WEIGHTS={shlex.quote(SAM3_WEIGHTS)}"
    try:
        with (folder / "masks.log").open("w") as log:
            done = batch.remote(folder, host, f"cd {REMOTE}/repo && CUDA_VISIBLE_DEVICES={card} env {environment} "
                                f"/root/venv/bin/python tools/props/scene/box_masks.py {REMOTE}/in/jobs.json "
                                f"{REMOTE}/out.json", stdout=log, stderr=subprocess.STDOUT)
    finally:
        batch.copy(folder, [f"root@{host}:{REMOTE}/out.json"], str(out))
        machine["made"] = len(jobs)
    machine.setdefault("unit_seconds", []).append(round(time.time() - began, 1))
    spread.raise_for(done.returncode, f"SAM 3 masks ({folder / 'masks.log'})")


def mask(jobs_path, out, dry_run=False):
    """Run box_masks.py over the jobs on one rented card; the run's ledger entry, or None when nothing was rented."""
    jobs = json.loads(pathlib.Path(jobs_path).read_text())
    account = cloud.account()
    batch.sweep(account)
    found, allowed_minutes = price(jobs, account)
    if dry_run:
        return None
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    started = time.time()
    folder = batch.BATCHES / time.strftime(f"masks-%Y%m%d-%H%M%S-{os.getpid()}")
    folder.mkdir(parents=True)
    run = pictures.Run(folder, started + allowed_minutes * 60)
    shares = spread.Shares([(0, jobs)], deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, 1, KIND, shares, set_up,
                           lambda machine, share, card: run_jobs(machine, share, card, jobs, pathlib.Path(out)))
        if not run.machines:
            raise SystemExit("no card for SAM 3 answered")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": folder.name,
                 "kind": KIND, **ledger.machines_record(run.machines, run.attempts, started), "pictures": len(jobs),
                 "wall_minutes": (time.time() - started) / 60}
        ledger.record(entry)
        batch.say(f"SAM 3 masks of {len(jobs)} pictures in {entry['wall_minutes']:.0f} min, €{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("jobs")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    mask(options.jobs, options.out, options.dry_run)


if __name__ == "__main__":
    main()
