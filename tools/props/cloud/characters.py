"""Make people with the character maker's person route on rented cards: one machine a person, every model step of the
person (the A-pose picture, the body read off it, the clips, the drapes, the hair, the face, the build) run up there
one after another, the made person brought back, the machines deleted (job characters-full, 2026-10-09: no model runs
on the owner's PC, and the character model steps had no cloud runner).

    .venv/bin/python tools/props/cloud/characters.py <make folder> [<make folder> ...] --who "<session>"
        [--classes gpu-24gb,gpu-80gb] [--hold] [--dry-run]

A make folder is ~/.farm-factory-motion/made/<name>/, written by tools/characters/maker/make.py: `in/` holds the spec
and every file the chain reads (the pictures, the shared look parts, the clips already made). Up there the chain is
tools/characters/maker/chain.py; what it makes comes back into the folder's `out/`, with `out/make.json` saying what
each step did and how long it took. The people are spread over machines (spread.py), one person a machine at a
time; characters_setup.sh sets each machine up once (about half an hour: six environments side by side).

--hold keeps the first machine after its people, for hands-on work over ssh, until the run folder holds `release`.
The owner's limits, the self-delete, the watchdog, the delete and the ledger are batch.py's.
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
import pictures  # noqa: E402
import secret_store  # noqa: E402
import spread  # noqa: E402
from paths import REPO  # noqa: E402
from provider import cloud  # noqa: E402

KIND = "characters"
REMOTE = pathlib.PurePosixPath("/root/make")
# What of the repository the chain needs up there.
SHIPPED = ("tools", "vendor/kimodo", "vendor/sam3dbody-cpp", "data/characters")
SETUP_MINUTES = 40
# One person's chain, a first guess before the first measured run: the picture, the body, two drapes, the hair, the
# face drawings and the build.
PERSON_MINUTES = 60
# Room for six environments, CUDA, the Llama 3 encoder, the picture models and Hi3DGen's weights.
DISK_GB = 200
POLL_SECONDS = 30


def price(makes, account, classes):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines and the minutes
    allowed."""
    found = batch.offers(list(classes or capacity.classes_for(KIND)))
    if not found:
        raise SystemExit("no card that holds the character chain is sold by the backend")
    count = capacity.machines_for(len(makes), PERSON_MINUTES, SETUP_MINUTES)
    minutes = SETUP_MINUTES + max(PERSON_MINUTES, len(makes) * PERSON_MINUTES / count)
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{len(makes)} people on {count} machine{'s' if count > 1 else ''}: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * count:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * count, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, count, ledger.minutes_allowed(dearest * count, spent)


def set_up(machine):
    """The repository's tools, the token and every environment onto one machine."""
    folder, host = machine["folder"], machine["host"]
    batch.remote(folder, host, f"mkdir -p /root/score/vendor /root/score/data {REMOTE}", check=True)
    for part in SHIPPED:
        batch.copy(folder, [REPO / part], f"root@{host}:/root/score/{pathlib.PurePosixPath(part).parent}/",
                   "--exclude", "__pycache__")
    token = folder / "hf-token"
    token.write_text(secret_store.secret("hf-read-token"))
    try:
        batch.copy(folder, [token], f"root@{host}:/root/hf-token")
    finally:
        token.unlink()
    began = time.time()
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, "bash /root/score/tools/props/cloud/characters_setup.sh", check=True, stdout=log,
                     stderr=subprocess.STDOUT)
    machine["setup_minutes"] = round((time.time() - began) / 60, 1)
    batch.say(f"{folder.name} set up in {machine['setup_minutes']} min")


def chain_line(name):
    """The detached command that runs one person's chain and leaves its exit code beside its log."""
    place = REMOTE / name
    run = (f"cd {place} && /root/envs/motion/bin/python /root/score/tools/characters/maker/chain.py {place} "
           f"> {place}/chain.log 2>&1; echo $? > {place}/exit")
    return f"setsid -f bash -c {shlex.quote(run)} < /dev/null > /dev/null 2>&1"


def exit_code(folder, host, name):
    """The chain's exit code, or None while it runs (or while a busy machine refuses one ssh)."""
    answer = batch.remote(folder, host, f"cat {REMOTE / name}/exit 2>/dev/null", capture_output=True, text=True)
    return int(answer.stdout) if answer.stdout.strip().lstrip("-").isdigit() else None


def bring_back(folder, host, make):
    """The chain's out folder and log back into the make folder."""
    (make / "out").mkdir(exist_ok=True)
    batch.copy(folder, [f"root@{host}:{REMOTE / make.name}/out/"], f"{make / 'out'}/")
    batch.copy(folder, [f"root@{host}:{REMOTE / make.name}/chain.log"], f"{make / 'out'}/")


def make_one(run, machine, make, card):
    """One person's chain on a machine, from its inputs up to its out folder back; a chain that fails raises
    spread.JobFailed (what it made still comes back)."""
    folder, host = machine["folder"], machine["host"]
    batch.remote(folder, host, f"rm -rf {REMOTE / make.name} && mkdir -p {REMOTE / make.name}", check=True)
    batch.copy(folder, [make / "in"], f"root@{host}:{REMOTE / make.name}/")
    began = time.time()
    batch.remote(folder, host, f"CUDA_VISIBLE_DEVICES={card or 0} {chain_line(make.name)}", check=True)
    code = None
    while time.time() < run.deadline and (code := exit_code(folder, host, make.name)) is None:
        time.sleep(POLL_SECONDS)
    bring_back(folder, host, make)
    minutes = (time.time() - began) / 60
    machine.setdefault("unit_seconds", []).append(round(minutes * 60, 1))
    batch.say(f"{make.name} ended with {code} on {folder.name} ({machine.get('type')}) after {minutes:.0f} min")
    spread.raise_for(code if code is not None else 1, f"{make.name} ({make / 'out' / 'chain.log'})")


def hold(run, host):
    """Keep the machine for hands-on work until the run folder holds `release` or the time limit."""
    batch.say(f"holding the machine at root@{host} (key {batch.KEY}); touch {run.folder / 'release'} to let it go")
    while not (run.folder / "release").exists() and time.time() < run.deadline:
        time.sleep(POLL_SECONDS)


def held(run, machine, makes):
    """One machine kept for hands-on work: set up, its people made in turn, then held until `release`."""
    folder = machine["folder"]
    stop = threading.Event()
    try:
        host = machine["host"]
        batch.arm_self_delete(folder, host, run.deadline + batch.WATCHDOG_GRACE_MINUTES * 60)
        threading.Thread(target=pictures.keep_beating, args=(folder, host, stop), daemon=True).start()
        (run.folder / "host").write_text(host)
        try:
            set_up(machine)
            for make in makes:
                try:
                    make_one(run, machine, make, 0)
                except spread.JobFailed as failure:
                    batch.say(f"{make.name} failed: {failure}")
        except subprocess.CalledProcessError as failure:
            batch.say(f"the setup failed ({failure}; see {folder / 'setup.log'}); holding the machine to mend it")
        hold(run, host)
    finally:
        stop.set()
        batch.delete_machine(machine)


def record(run, makes):
    """Write the run to the ledger, with each machine's card type, set-up minutes and chain minutes."""
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(run.started)), "batch": run.folder.name,
             "kind": KIND, "makes": [make.name for make in makes],
             **ledger.machines_record(run.machines, run.attempts, run.started),
             "setup_minutes": {machine["folder"].name: machine.get("setup_minutes") for machine in run.machines},
             "wall_minutes": (time.time() - run.started) / 60}
    ledger.record(entry)
    batch.say(f"characters: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machines, "
              f"€{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("makes", nargs="+", type=pathlib.Path, help="make folders, each holding in/spec.json")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--classes", help="capability classes to take, comma separated (default: the kind's)")
    parser.add_argument("--hold", action="store_true", help="keep one machine for ssh work until `release`")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()
    makes = [make.resolve() for make in options.makes]
    for make in makes:
        if not (make / "in" / "spec.json").exists():
            raise SystemExit(f"{make} holds no in/spec.json (tools/characters/maker/make.py writes it)")
    classes = options.classes.split(",") if options.classes else None
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(makes, account, classes)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    run = pictures.Run(batch.BATCHES / (time.strftime("characters-%Y%m%d-%H%M%S") + f"-{os.getpid()}"),
                       time.time() + allowed_minutes * 60)
    run.started = time.time()
    run.folder.mkdir(parents=True)
    batch.say(f"run folder {run.folder} ({options.who})")
    try:
        if options.hold:
            machine = batch.claim(run, account, found, 1, KIND, DISK_GB)
            if machine is None:
                raise SystemExit("no card could be rented")
            held(run, machine, makes)
        else:
            queue = spread.Shares(makes, deadline=run.deadline)
            spread.on_machines(run, account, found, count, KIND, queue, set_up,
                               lambda machine, make, card: make_one(run, machine, make, card), DISK_GB, at_once=1)
            if not run.machines:
                raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        if run.machines or run.attempts:
            (run.folder / "cloud.json").write_text(json.dumps(record(run, makes), indent=1, default=str))


if __name__ == "__main__":
    main()
