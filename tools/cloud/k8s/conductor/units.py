"""The VM's always-on units as one process in the conductor's pod (a pod has no systemd): the listener kept running,
each timer's commands at its interval, resume at the start and every RESUME_SECONDS. The sync pass and the backups are CronJobs beside
it (`__init__.CRONJOBS`), so a pass never blocks a timer here.

    python3 -I tools/cloud/k8s/conductor/units.py      # the conductor container's last step (score-conductor-start)

Each command runs as its unit ran it: the env file's NAME=value lines in its environment (EnvironmentFile), the free-
only latch's file too for the commands the VM gave it, through /bin/sh, its output into this process's (the pod's
log, read by `score.conductor logs` and `kubectl logs`) prefixed with the unit's name. A failed command is said and
its timer goes on (the VM's `ExecStart=-`); the listener is started again `RESTART_SECONDS` after it ends. SIGTERM
(the pod's stop) is passed on to every command still running, which then has the pod's grace to end.
"""
import os
import pathlib
import signal
import subprocess
import sys
import time

HOME = pathlib.Path(os.environ.get("HOME", "/home/score"))
REPO = HOME / "projects" / "score"
PY = f"{REPO}/.venv/bin/python"
ENV_FILE = pathlib.Path(os.environ.get("SCORE_ENV_FILE", HOME / ".config/score/dashboard.env"))
LATCH = pathlib.Path(os.environ.get("PROPS_HOME", HOME / ".farm-factory-props")) / "conductor" / "free-only"
RESTART_SECONDS = 30
# Resume at the start and every few minutes after: a drive pod cut at this boot (its memory limit, a SIGKILL) leaves
# its run `running`, and resume starts it again once (score/graph/runs.cut_at_this_boot; the rehearsal of 2026-11-07).
RESUME_SECONDS = 300
TICK_SECONDS = 5
TOKEN = 'SCORE_SYNC_TOKEN="$("$SCORE_SECRET_READER" score-cockpit-sync-token)" && [ -n "$SCORE_SYNC_TOKEN" ] && ' \
        "export SCORE_SYNC_TOKEN && exec "
# (unit, seconds between starts or None for the always-on one, the first start's delay, its commands)
UNITS = (
    ("listen", None, 0, (f"{TOKEN}{PY} -m score.dashboard listen",)),
    ("resume", RESUME_SECONDS, 0, (f"{PY} -m score resume",)),
    ("health", 60, 60, (f"{PY} -m score.conductor health --write",
                        f"/usr/bin/python3 -I {REPO}/tools/cloud/conductor/health_push.py")),
    ("update", 300, 180, (f"/usr/bin/python3 -I {REPO}/tools/cloud/conductor/update.py --repo {REPO}",)),
    ("secrets", 3600, 0, (f"/bin/sh {REPO}/tools/cloud/conductor/secrets.sh",)),
    ("sweep", 600, 120, (f"{PY} -m score.conductor sweep",)),
)


def env_values(path):
    """{name: value} of an env file's NAME=value lines (quotes round a value dropped); {} when there is none."""
    try:
        lines = pathlib.Path(path).read_text().splitlines()
    except OSError:
        return {}
    found = {}
    for line in lines:
        name, equals, value = line.partition("=")
        value = value.strip()
        if equals and name.strip() and not name.lstrip().startswith("#"):
            found[name.strip()] = value[1:-1] if len(value) > 1 and value[0] == value[-1] in "'\"" else value
    return found


def unit_environment(base=None, env_file=None, latch=None):
    """This unit's environment: the pod's, the env file's lines over it, the free-only latch's last."""
    return {**(os.environ if base is None else base), **env_values(env_file or ENV_FILE),
            **env_values(latch or LATCH)}


def start(unit, command, environment, popen=subprocess.Popen):
    """Start one command of a unit through /bin/sh, its output into the pod's, from the checkout."""
    print(f"[{unit}] {command}", flush=True)
    return popen(["/bin/sh", "-c", command], env=environment, cwd=str(REPO) if REPO.is_dir() else None)


class Unit:
    """One unit's state: its next start and the command of it that runs now."""

    def __init__(self, name, every, delay, commands, now):
        self.name, self.every, self.commands = name, every, commands
        self.due, self.step, self.process = now + delay, 0, None

    def tick(self, now, environment, popen=subprocess.Popen):
        """Start what is due, move on when a command ended; whether the unit is done for good."""
        if self.process is not None:
            code = self.process.poll()
            if code is None:
                return False
            if code:
                print(f"[{self.name}] ended {code}", flush=True)
            self.process, self.step = None, self.step + 1
            if self.step < len(self.commands) and (code == 0 or self.every is not None):
                self.process = start(self.name, self.commands[self.step], environment, popen)
                return False
            self.step = 0
            if self.every == 0:
                return True
            self.due = now + (RESTART_SECONDS if self.every is None else self.every)
            return False
        if now >= self.due:
            self.process = start(self.name, self.commands[0], environment, popen)
        return False


def run(units=UNITS, clock=time.monotonic, sleep=time.sleep, popen=subprocess.Popen, stopping=None):
    """Keep every unit going until a stop; then pass the stop on to what still runs."""
    stopping = stopping if stopping is not None else []
    signal.signal(signal.SIGTERM, lambda *_: stopping.append(True))
    live = [Unit(*row, clock()) for row in units]
    while not stopping:
        environment = unit_environment()
        live = [unit for unit in live if not unit.tick(clock(), environment, popen)]
        sleep(TICK_SECONDS)
    for unit in live:
        if unit.process is not None and unit.process.poll() is None:
            unit.process.terminate()
    for unit in live:
        if unit.process is not None:
            unit.process.wait()
    return 0


if __name__ == "__main__":
    sys.exit(run())
