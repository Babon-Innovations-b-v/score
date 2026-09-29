"""Make a whole batch of models on a rented Scaleway graphics card, then delete the machine.

    ~/.farm-factory-props/env/bin/python tools/props/cloud/batch.py <list.txt> --who "<session>"
        [--at-once 3] [--type L4-1-24G] [--no-finish] [--dry-run]

The list has one model a line, `<name> <picture> [pixal.py options]`, e.g.
`crate ~/pics/crate.png --faces 12000 --feet`; `#` starts a comment. The pictures must be ones the
owner approved.

Only the raw Pixal3D step runs in the cloud (#55): each picture is cut out here, the cut-outs go
up, the card builds the raw models a few at once, and they come back into WORK/pixal/ as if made
here. Then each is finished here with `pixal.py --finish-only`, so the result matches a local run.

One L4 makes about 15 models an hour (2026-09-29), so a batch holds at most about 55. A longer list
is split and its parts run as separate batch.py processes at the same time, each on its own
machine; a run's sweep leaves alone the machines of runs still going.

Before anything is rented, the price is read from Scaleway and printed, and a batch that would
pass four hours, €50, or the month's €700 is refused (ledger.py). The machine is deleted whatever
happens: at the end, on an error, on Ctrl-C, and by a watchdog process at the time limit if this
one is gone. Each run starts by deleting what a crashed run left behind.
"""
import argparse
import json
import os
import pathlib
import shlex
import signal
import socket
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import ledger  # noqa: E402
import pixal  # noqa: E402
import scaleway  # noqa: E402
from paths import HOME, REPO, VENV_PYTHON, WORK  # noqa: E402

MACHINE_TYPE = "L4-1-24G"
# 24 GB, and a bulky Pixal3D run peaks near 7.1 GB (measured on the owner's card, 2026-09-28).
AT_ONCE = 3
DISK_GB = 60
CLOUD = HOME / "cloud"
KEY = CLOUD / "ssh_key"
BATCHES = WORK / "cloud"
LAB = REPO / "vendor" / "image-to-3dlab"
# Renting, starting and installing took 2.3 min on the first batch (2026-09-29); the margin covers a
# slow download. A model's machine minutes come from the ledger once a batch has run.
SETUP_MINUTES = 5.0
MODEL_MINUTES = 5.0
# How often the runner looks at the machine and brings back what is finished.
POLL_SECONDS = 30
# How long a new machine may take to answer, and the watchdog's margin past the time limit.
BOOT_MINUTES = 10
# A booted machine that still refuses the key this long never will (measured 2026-09-29: up and
# answering in about 2 min).
REFUSED_MINUTES = 3
WATCHDOG_GRACE_MINUTES = 5


def say(line):
    print(f"[cloud] {line}", file=sys.stderr, flush=True)


def read_list(path):
    """The batch's models: name, picture and pixal.py's options for each, checked up front."""
    parser = pixal.options_parser()
    models = []
    for number, line in enumerate(pathlib.Path(path).read_text().splitlines(), 1):
        words = shlex.split(line, comments=True)
        if not words:
            continue
        if len(words) < 2:
            raise SystemExit(f"{path}:{number}: needs a name and a picture")
        name, picture, *flags = words
        options = parser.parse_args([os.path.expanduser(picture), name, "--who", "batch", *flags])
        if not pathlib.Path(options.picture).is_file():
            raise SystemExit(f"{path}:{number}: no picture at {options.picture}")
        models.append(options)
    names = [options.name for options in models]
    if len(set(names)) != len(names):
        raise SystemExit(f"{path}: a name appears twice")
    return models


def taken(models):
    """The names that already have a raw model here, which a batch would overwrite."""
    return [options.name for options in models if (pixal.OUT / f"{options.name}.glb").exists()]


def measured_minutes_per_model():
    """Minutes of machine time per model in the last measured batch, or the first guess."""
    for entry in reversed(ledger.entries()):
        if entry.get("models_done"):
            return entry["generate_minutes"] / entry["models_done"]
    return MODEL_MINUTES


def estimate_minutes(count):
    """How long a batch of `count` models is expected to keep the machine."""
    return SETUP_MINUTES + count * measured_minutes_per_model()


def process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def tag_value(tags, key):
    """The value of a `key=value` tag, or None."""
    for tag in tags:
        if tag.startswith(key + "="):
            return tag.split("=", 1)[1]
    return None


def is_leftover(tags, now):
    """Whether a machine was left by a run that is over: past its deadline, or its process gone."""
    deadline = tag_value(tags, "deadline")
    if deadline is None or float(deadline) < now:
        return True
    pid = tag_value(tags, "pid")
    return tag_value(tags, "host") == socket.gethostname() and not (pid and process_alive(int(pid)))


def sweep(project):
    """Delete every machine a finished or crashed run left in the project; the count deleted."""
    deleted = 0
    for server_id, name, tags in scaleway.ours(project):
        if is_leftover(tags, time.time()):
            say(f"deleting {name}, left by an earlier run")
            deleted += scaleway.delete(server_id)
        else:
            say(f"{name} belongs to a batch still running; left alone")
    return deleted


def ssh_key():
    """The runner's own key pair, made once; the public half."""
    if not KEY.exists():
        CLOUD.mkdir(parents=True, exist_ok=True)
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-C", "farm-factory-batch",
                        "-f", str(KEY)], check=True)
    return KEY.with_suffix(".pub").read_text().strip()


def ssh_options(folder):
    return ["-i", str(KEY), "-o", "IdentitiesOnly=yes", "-o", "StrictHostKeyChecking=accept-new",
            "-o", f"UserKnownHostsFile={folder / 'known_hosts'}", "-o", "ConnectTimeout=10",
            "-o", "ServerAliveInterval=30"]


def remote(folder, host, command, **keywords):
    """Run a shell command on the machine as root."""
    return subprocess.run(["ssh", *ssh_options(folder), f"root@{host}", command], **keywords)


def copy(folder, sources, destination):
    """Copy files or folders with rsync over the runner's ssh."""
    ssh = shlex.join(["ssh", *ssh_options(folder)])
    subprocess.run(["rsync", "-a", "--exclude", ".git", "-e", ssh, *map(str, sources), str(destination)],
                   check=True)


def wait_for_machine(folder, server_id):
    """The machine's address once it answers over ssh."""
    give_up = time.time() + BOOT_MINUTES * 60
    host, first_refused = None, None
    while time.time() < give_up:
        if host is None:
            host = scaleway.address(server_id)
            if host:
                say(f"machine address {host}; waiting for ssh")
        if host:
            answer = remote(folder, host, "true", capture_output=True, text=True)
            if answer.returncode == 0:
                return host
            if "Permission denied" in answer.stderr:
                first_refused = first_refused or time.time()
                if time.time() - first_refused > REFUSED_MINUTES * 60:
                    raise PermissionError(f"the machine at {host} refuses the runner's ssh key")
        time.sleep(10)
    raise TimeoutError(f"the machine did not answer within {BOOT_MINUTES} min "
                       f"({'at ' + host if host else 'it never got an address'})")


def cut_outs(models, folder):
    """Each picture cut out here, on the processor, copied into `folder` as <name>.png."""
    for options in models:
        cut = pathlib.Path(pixal.cut_out(options.picture))
        (folder / f"{options.name}.png").write_bytes(cut.read_bytes())


def jobs(models):
    """The generator's arguments for each model, with the machine's paths."""
    return [{"name": options.name,
             "arguments": pixal.generator_arguments(f"/root/batch/in/{options.name}.png",
                                                    f"/root/batch/out/{options.name}.glb",
                                                    options.seed)}
            for options in models]


def upload(folder, host, models):
    """The lab, the machine's scripts, the cut-outs and the job list onto the machine."""
    (folder / "jobs.json").write_text(json.dumps(jobs(models), indent=1))
    remote(folder, host, "mkdir -p /root/batch/out", check=True)
    copy(folder, [str(LAB) + "/"], f"root@{host}:/root/lab/")
    copy(folder, [HERE / "machine_setup.sh", HERE / "machine_run.py", folder / "jobs.json"],
         f"root@{host}:/root/batch/")
    copy(folder, [folder / "in"], f"root@{host}:/root/batch/")


def bring_back(folder, host):
    """Copy the machine's finished models, logs and status into the batch folder."""
    copy(folder, [f"root@{host}:/root/batch/out", f"root@{host}:/root/batch/logs",
                  f"root@{host}:/root/batch/status.json"], folder)


def follow(folder, host, stop_at):
    """Bring results back every poll until the batch finishes or `stop_at` passes; the status."""
    status = {}
    while time.time() < stop_at:
        time.sleep(POLL_SECONDS)
        try:
            bring_back(folder, host)
        except subprocess.CalledProcessError:
            continue
        status = json.loads((folder / "status.json").read_text())
        states = [job["state"] for job in status["jobs"].values()]
        say(f"{states.count('done')} done, {states.count('failed')} failed, "
            f"{states.count('running')} running, peak {status['peak_gb']:.1f} GB")
        if status["finished"]:
            return status
    say("time limit reached; stopping with what is finished")
    return status


def start_watchdog(server_id, deadline, folder):
    """A separate process that deletes the machine at `deadline` if it still exists; its pid."""
    with (folder / "watchdog.log").open("w") as log:
        watchdog = subprocess.Popen([sys.executable, __file__, "--watchdog", server_id, str(deadline)],
                                    start_new_session=True, stdout=log, stderr=subprocess.STDOUT)
    return watchdog.pid


def watchdog(server_id, deadline):
    """Sleep until the deadline, then delete the machine if the runner has not."""
    time.sleep(max(0.0, deadline - time.time()))
    if scaleway.delete(server_id):
        print(f"watchdog deleted {server_id} at the time limit", flush=True)


def stop_on_signals():
    """Turn Ctrl-C, a closed terminal and a kill into an exit, so the machine is deleted."""
    def leave(number, _frame):
        raise SystemExit(f"stopped by signal {number}")
    for number in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(number, leave)


def unpack(folder, status):
    """Move each finished raw model into WORK/pixal/, where pixal.py looks; their names."""
    finished = []
    pixal.OUT.mkdir(parents=True, exist_ok=True)
    for name, job in status.get("jobs", {}).items():
        raw = folder / "out" / f"{name}.glb"
        if job["state"] == "done" and raw.exists():
            for made in [*(folder / "out").glob(f"{name}.*"), *(folder / "out").glob(f"{name}_*")]:
                made.replace(pixal.OUT / made.name)
            finished.append(name)
    return finished


def finish_here(models, names, who):
    """Finish each brought-back model here with pixal.py --finish-only; the names that failed."""
    failed = []
    for options in models:
        if options.name not in names:
            continue
        flags = [f"--faces={options.faces}", f"--seed={options.seed}"]
        flags += [f"--{flag}" for flag in ("long", "feet", "tube") if getattr(options, flag)]
        done = subprocess.run([str(VENV_PYTHON), str(HERE.parent / "pixal.py"), options.picture,
                               options.name, "--who", who, "--finish-only", *flags])
        if done.returncode:
            failed.append(options.name)
    return failed


def rent_and_run(models, options, project, price, stop_minutes, folder):
    """Rent the machine, make the raw models, bring them back and delete it; the ledger entry."""
    started = time.time()
    deadline = started + stop_minutes * 60
    tags = [f"pid={os.getpid()}", f"host={socket.gethostname()}",
            f"deadline={deadline + WATCHDOG_GRACE_MINUTES * 60:.0f}"]
    scaleway.allow_key(project, "farm-factory-batch", ssh_key())
    server_id = scaleway.create(project, options.type, folder.name, tags, DISK_GB)
    watchdog_pid = start_watchdog(server_id, deadline + WATCHDOG_GRACE_MINUTES * 60, folder)
    say(f"rented {options.type} {server_id}; deleted by {time.strftime('%H:%M', time.localtime(deadline))} at the latest")
    status, setup_seconds, generate_minutes = {}, None, 0.0
    try:
        host = wait_for_machine(folder, server_id)
        upload(folder, host, models)
        setup_began = time.time()
        with (folder / "setup.log").open("w") as log:
            remote(folder, host, "bash /root/batch/machine_setup.sh", check=True, stdout=log,
                   stderr=subprocess.STDOUT)
        setup_seconds = time.time() - setup_began
        say(f"machine ready after {(time.time() - started) / 60:.1f} min (install {setup_seconds / 60:.1f})")
        generate_began = time.time()
        # setsid -f detaches the run whole; a trailing & would keep the ssh session open until it ends.
        remote(folder, host, f"cd /root/batch; setsid -f /root/venv/bin/python machine_run.py "
               f"jobs.json {options.at_once} > run.log 2>&1 < /dev/null", check=True)
        status = follow(folder, host, deadline)
        generate_minutes = (time.time() - generate_began) / 60
    finally:
        try:
            scaleway.delete(server_id)
            os.kill(watchdog_pid, signal.SIGTERM)
        finally:
            minutes = (time.time() - started) / 60
            say(f"machine time {minutes:.1f} min")
            entry = ledger_entry(folder, options, models, started, minutes, price, setup_seconds,
                                 status, generate_minutes)
            ledger.record(entry)
    return entry, status


def ledger_entry(folder, options, models, started, minutes, price, setup_seconds, status,
                 generate_minutes):
    """The ledger's record of one batch: its machine time, cost, and each model's seconds."""
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
             "batch": folder.name, "type": options.type, "at_once": options.at_once,
             "machine_minutes": minutes, "euros": ledger.cost(minutes, price),
             "models": len(models), "setup_seconds": setup_seconds,
             "models_done": 0, "generate_minutes": generate_minutes,
             "peak_gb": status.get("peak_gb")}
    if status:
        entry["models_done"] = sum(job["state"] == "done" for job in status["jobs"].values())
        entry["job_seconds"] = {name: job.get("seconds") for name, job in status["jobs"].items()}
    return entry


def report(entry):
    """The batch's speed and cost, the numbers #55 records against the owner's card."""
    done = entry["models_done"]
    say(f"{done} of {entry['models']} models, {entry['machine_minutes']:.1f} machine minutes, "
        f"€{entry['euros']:.2f}")
    if done:
        say(f"{done / (entry['generate_minutes'] / 60):.1f} models an hour while generating, "
            f"€{entry['euros'] / done:.3f} a model with setup, peak {entry['peak_gb']:.1f} GB")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("list")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--at-once", type=int, default=AT_ONCE)
    parser.add_argument("--type", default=MACHINE_TYPE)
    parser.add_argument("--no-finish", action="store_true", help="bring back raw models only")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    options = parser.parse_args()

    models = read_list(options.list)
    if taken(models):
        raise SystemExit(f"raw models already here, pick new names: {', '.join(taken(models))}")
    project = scaleway.project_id()
    sweep(project)
    price = scaleway.euros_per_minute(options.type)
    say(f"{options.type} in {scaleway.ZONE}: €{price:.6f} a minute, €{price * 60:.2f} an hour "
        "(Scaleway's price list)")
    spent = max(scaleway.month_spend(project), ledger.month_total(ledger.this_month(), ledger.entries()))
    estimate = estimate_minutes(len(models))
    say(f"{len(models)} models, {options.at_once} at once: about {estimate:.0f} min, "
        f"€{ledger.cost(estimate, price):.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(estimate, price, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    if not scaleway.in_stock(options.type):
        raise SystemExit(f"{options.type} is out of stock in {scaleway.ZONE}")
    if options.dry_run:
        return

    folder = BATCHES / time.strftime(f"batch-%Y%m%d-%H%M%S-{os.getpid()}")
    (folder / "in").mkdir(parents=True)
    cut_outs(models, folder / "in")
    stop_on_signals()
    entry, status = rent_and_run(models, options, project, price,
                                 ledger.minutes_allowed(price, spent), folder)
    report(entry)
    names = unpack(folder, status)
    missing = sorted({model.name for model in models} - set(names))
    if missing:
        say(f"not made: {', '.join(missing)} (logs in {folder / 'logs'})")
    if not options.no_finish:
        failed = finish_here(models, names, options.who)
        if failed:
            say(f"finishing failed: {', '.join(failed)}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--watchdog"]:
        watchdog(sys.argv[2], float(sys.argv[3]))
    else:
        main()
