"""The conductor's health record in its backup bucket (health/conductor.json), written every minute by
score-health.service, standard library only. The size function reads it before a shrink and `machine.py status` shows
it, since neither can reach the machine (it takes ssh only).

    /usr/bin/python3 -I tools/cloud/conductor/health_push.py [--print]

The record: written_at, boot_id, host, commercial_type (from the instance's metadata), the shrink guard's counts read
from PROPS_HOME (active_runs: live claims in runs/active.json; parked: paid machines in cloud/parked; frozen: frozen
worktrees under frozen/ a process works in, a waiting-for-size run's own copy left out: it waits for this very grow,
and a copy left behind by a killed run holds nothing up), and `health`, the record score.conductor's `health --write` keeps at SCORE_HEALTH_FILE
(default $PROPS_HOME/conductor/health.json) when there is one. The counts err on the side of busy: a claim whose pid
lives counts, whoever holds the pid now. It writes with user score's one credential (`scw config get`), to the bucket
SCORE_CONDUCTOR_BUCKET in SCORE_CONDUCTOR_BUCKET_REGION (the env file's, written by `machine.py up`).
"""
import datetime
import json
import os
import pathlib
import socket
import subprocess
import sys
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "size_function"))
import s3  # noqa: E402

HEALTH_KEY = "health/conductor.json"
METADATA = "http://169.254.42.42/conf?format=json"
SCW = os.environ.get("SCORE_SCW", "/usr/local/bin/scw")


def props_home():
    return pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))


def pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True
    return True


def active_runs(home):
    """The claims in runs/active.json whose pid is alive; 0 with no file. A file that cannot be read or parsed raises,
    so no record is pushed and the one in the bucket goes stale: an unknown is never an idle."""
    path = home / "runs" / "active.json"
    try:
        claims = json.loads(path.read_text())
    except FileNotFoundError:
        return 0
    return sum(1 for pid in claims if pid_alive(pid))


def entries(folder):
    """How many entries a folder holds, its hidden ones left out; 0 when there is no folder."""
    try:
        return sum(1 for entry in folder.iterdir() if not entry.name.startswith("."))
    except OSError:
        return 0


WAITING = "waiting-for-size"  # score/graph/runs.py WAITING


def processes_in(folder):
    """The pids whose working folder is under `folder` (score/conductor/size.py processes_in)."""
    found = []
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cwd = pathlib.Path(os.readlink(entry / "cwd"))
        except OSError:
            continue
        if cwd == folder or folder in cwd.parents:
            found.append(int(entry.name))
    return found


def waiting_copies(home):
    """The frozen copies of the runs registered waiting for size (runs/<id>.json, state waiting-for-size): the grow
    is what they wait for, so their own copies never refuse it."""
    found = set()
    for path in (home / "runs").glob("*.json"):
        if path.name == "active.json":
            continue
        try:
            entry = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if entry.get("state") == WAITING and entry.get("worktree"):
            found.add(pathlib.Path(entry["worktree"]))
    return found


def frozen_in_use(home, find=processes_in):
    """How many frozen copies under frozen/ a process works in, a waiting run's own copy left out."""
    folder = home / "frozen"
    if not folder.is_dir():
        return 0
    waiting = waiting_copies(home)
    return sum(1 for copy in folder.iterdir() if not copy.name.startswith(".") and copy not in waiting
               and find(copy))


def commercial_type():
    """The instance's commercial type from Scaleway's metadata service, or None off Scaleway."""
    try:
        with urllib.request.urlopen(METADATA, timeout=3) as answer:
            return json.load(answer).get("commercial_type")
    except (OSError, ValueError):
        return None


def boot_id():
    try:
        return pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return None


def conductor_health(home):
    """score.conductor's own health record, or None."""
    path = pathlib.Path(os.environ.get("SCORE_HEALTH_FILE", home / "conductor" / "health.json"))
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def record(home, now):
    """The health record as of `now`."""
    return {"written_at": now.isoformat(timespec="seconds"), "boot_id": boot_id(), "host": socket.gethostname(),
            "commercial_type": commercial_type(), "active_runs": active_runs(home),
            "parked": entries(home / "cloud" / "parked"), "frozen": frozen_in_use(home),
            "health": conductor_health(home)}


def credentials():
    """(access key, secret key) of user score's one credential, read through the scw CLI."""
    def get(name):
        return subprocess.run([SCW, "config", "get", name], capture_output=True, text=True, check=True).stdout.strip()
    return get("access-key"), get("secret-key")


def main(argv):
    now = datetime.datetime.now(datetime.timezone.utc)
    body = record(props_home(), now)
    if "--print" in argv:
        print(json.dumps(body, indent=1))
        return 0
    bucket = os.environ.get("SCORE_CONDUCTOR_BUCKET")
    region = os.environ.get("SCORE_CONDUCTOR_BUCKET_REGION", "nl-ams")
    if not bucket:
        print("health_push: SCORE_CONDUCTOR_BUCKET is not set (the env file's, from machine.py up)", file=sys.stderr)
        return 1
    access, secret = credentials()
    s3.put(bucket, HEALTH_KEY, json.dumps(body).encode(), region, access, secret)
    print(f"health_push: {HEALTH_KEY} written: {body['active_runs']} run(s), {body['parked']} parked, "
          f"{body['frozen']} frozen")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
