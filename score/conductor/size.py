"""The conductor's two sizes: grown for a run that asks for more cores than the machine has, shrunk once idle.

    python -m score.conductor size     # score-size.timer, every 5 minutes: grow, shrink or nothing, one line

The same machine runs at two sizes (machine.json's idle_type and batch_type), keeping its volumes, IP and identity: a
grow or a shrink is the size function's (tools/cloud/conductor: a Scaleway Serverless Function that allows only those
two types and this one server, powers it off, changes its type and powers it on). It is asked with one HTTPS POST to
SCORE_CONDUCTOR_SIZE_URL, body {"action": "grow" | "shrink"}, the function's token in X-Score-Size-Token, read by name
(TOKEN_SECRET) through SCORE_SECRET_READER at the call, never kept.

A run with more jobs than cores (waits) registers as waiting for size (graph/runs.py WAITING) and waits here
(wait_for_grow), touching its entry; it starts score-size.service at once, and the timer asks again on every pass.
The grow waits for every live run to end first (a grow is a reboot: a live run would be cut, its paid steps' machines
deleted), and never happens while the kill switch's latch holds. The grow's shutdown leaves the waiting run waiting,
and `score resume` at the boot on the batch size starts it. A run started in an agent's process never grows the
machine (a bigger machine is spend, and only the owner's click says yes to spend): it is refused as on the PC.

The shrink comes after IDLE_MINUTES with no live claim (runs/active.json), no running or waiting run, no parked paid
machine and no frozen copy a process still uses (a run's releaser waits out its parked machines from it); the idle
time counts from the last pass that saw the machine busy, or from the boot.
"""
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import urllib.request

from score import conductor
from score.graph import frozen, runs, stopped
from score.store import PROPS_HOME, running_under_agent

GROW, SHRINK = "grow", "shrink"
IDLE_MINUTES = 30
GROW_WAIT = 3600  # seconds a waiting run waits for the grow's shutdown before it gives up (unresumable)
WAIT_STEP = 5
STATE = conductor.HOME / "size.json"
SERVICE = "score-size.service"
TOKEN_SECRET = "score-conductor-size-token"
HEADER = "X-Score-Size-Token"  # tools/cloud/conductor/size_function/handler.py checks it
READER = "SCORE_SECRET_READER"
PARKED = PROPS_HOME / "cloud" / "parked"  # tools/props/cloud/park.py PARKED


def waits(jobs, oversubscribe, agent=None):
    """Why a run of `jobs` waits for the batch size instead of being refused, or None: only on a conductor, outside an
    agent's process (`agent`: whether this is one, worked out when None), for more jobs than cores and at most the
    batch size's cores, and without --oversubscribe."""
    record = conductor.machine()
    agent = running_under_agent() if agent is None else agent
    if record is None or oversubscribe or agent or jobs <= conductor.cores():
        return None
    if jobs > int(record.get("batch_cores", 0)):
        return None
    return (f"{jobs} jobs on {conductor.cores()} cores: waiting for the batch size "
            f"({record.get('batch_type')}, {record['batch_cores']} cores)")


def alive(pid):
    """Whether a process is there (a zombie counts as gone)."""
    try:
        return pathlib.Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0] != "Z"
    except (OSError, IndexError):
        return False


def processes_in(folder):
    """The pids whose working folder is under `folder`."""
    found = []
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cwd = pathlib.Path(os.readlink(entry / "cwd"))
        except OSError:
            continue
        if cwd.is_relative_to(folder):
            found.append(int(entry.name))
    return found


def busy(runs_folder=None, parked=None, frozen_folder=None):
    """What keeps the machine at its size now: {claims, running, waiting, parked, frozen}, each a count."""
    runs_folder = pathlib.Path(runs_folder or runs.RUNS)
    with runs.claims_locked(runs_folder) as claims:
        live_claims = len(claims)
    entries = runs.entries(runs_folder).values()
    running = [entry for entry in entries if entry.get("state") == runs.RUNNING and alive(entry.get("pid", 0))]
    waiting = [entry for entry in entries if entry.get("state") == runs.WAITING]
    parked_folder = pathlib.Path(parked or PARKED)
    frozen_folder = pathlib.Path(frozen_folder or frozen.FOLDER)
    in_use = [copy for copy in sorted(frozen_folder.iterdir()) if processes_in(copy)] if frozen_folder.is_dir() else []
    return {"claims": live_claims, "running": len(running), "waiting": len(waiting),
            "wanted": max((entry.get("jobs", 0) for entry in waiting), default=0),
            "parked": len(list(parked_folder.glob("*.json"))) if parked_folder.is_dir() else 0, "frozen": len(in_use)}


def is_busy(view):
    """Whether anything in a busy view keeps the machine at its size."""
    return any(view[name] for name in ("claims", "running", "waiting", "parked", "frozen"))


def decide(view, cores, record, idle_since, now, latched):
    """(GROW, SHRINK or None, why) for a busy view on a machine of `cores` (machine.json's `record`), idle since
    `idle_since` (seconds since the epoch) at `now`, the kill switch's latch `latched`."""
    if view["waiting"] and view["wanted"] > cores:
        if latched:
            return None, "a run waits for size, but the kill switch's free-only latch holds: no grow"
        if view["claims"] or view["running"]:
            return None, "a run waits for size; the grow waits for the live runs to end"
        if cores >= int(record["batch_cores"]):
            return None, f"a run asks for {view['wanted']} jobs, more than the batch size's {cores} cores"
        return GROW, f"a run waits for {view['wanted']} cores, this machine has {cores}"
    if cores <= int(record["idle_cores"]):
        return None, "at the idle size"
    if is_busy(view):
        return None, "busy: " + ", ".join(f"{name} {view[name]}" for name in ("claims", "running", "waiting",
                                                                             "parked", "frozen") if view[name])
    idle = (now - idle_since) / 60
    if idle < IDLE_MINUTES:
        return None, f"idle {idle:.0f} of {IDLE_MINUTES} minutes"
    return SHRINK, f"idle {idle:.0f} minutes at the batch size"


def read_state(path=None):
    """The size timer's own record ({busy_at, asked, asked_at}), empty when none."""
    path = pathlib.Path(path or STATE)
    return json.loads(path.read_text()) if path.is_file() else {}


def keep_state(state, path=None):
    """Write the size timer's record whole."""
    path = pathlib.Path(path or STATE)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(f"{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(state, indent=1))
    os.replace(partial, path)


def token():
    """The size function's token, read by name through SCORE_SECRET_READER into this process only."""
    reader = os.environ.get(READER)
    if not reader:
        raise RuntimeError(f"no {READER}: the size function's token is read by name, never from a file")
    done = subprocess.run([reader, TOKEN_SECRET], capture_output=True, text=True, timeout=60)
    if done.returncode or not done.stdout.strip():
        raise RuntimeError(f"{TOKEN_SECRET} not read (exit {done.returncode})")
    return done.stdout.strip()


def ask(action, url=None, opener=urllib.request.urlopen):
    """Ask the size function to grow or shrink this machine; its answer's text."""
    if action not in (GROW, SHRINK):
        raise ValueError(f"{action}: only {GROW} or {SHRINK}")
    request = urllib.request.Request(url or os.environ[conductor.SIZE_URL], method="POST",
                                     data=json.dumps({"action": action}).encode(),
                                     headers={"Content-Type": "application/json", HEADER: token()})
    with opener(request, timeout=60) as answer:
        return answer.read().decode(errors="replace")[:400]


def asked(action, asker):
    """Ask for a resize with the resize mark written first (score.conductor.resizing: its power-off's SIGTERM leaves
    every run as it was), the mark taken back when the ask fails; the answer."""
    conductor.RESIZING.parent.mkdir(parents=True, exist_ok=True)
    conductor.RESIZING.write_text(json.dumps({"action": action, "at": time.time()}))
    try:
        return asker(action)
    except BaseException:
        conductor.RESIZING.unlink(missing_ok=True)
        raise


def tick(say=print, now=None, asker=ask, state_path=None, view=None):
    """One pass of the size timer: grow, shrink or nothing, said in one line; the decision ({action, why, asked})."""
    record = conductor.machine()
    if record is None:
        say("size: not a conductor (no machine.json or no SCORE_CONDUCTOR_SIZE_URL): nothing to do")
        return {"action": None, "why": "not a conductor"}
    now = time.time() if now is None else now
    view = busy() if view is None else view
    state = read_state(state_path)
    if is_busy(view):
        state["busy_at"] = now
    idle_since = max(state.get("busy_at", 0), runs.boot_time())
    action, why = decide(view, conductor.cores(), record, idle_since, now, conductor.free_only())
    answer = None
    if action:
        answer = asked(action, asker)
        state.update(asked=action, asked_at=now)
    keep_state(state, state_path)
    say(f"size: {action or 'nothing'}: {why}" + (f"; the size function said: {answer}" if answer else ""))
    return {"action": action, "why": why, "asked": bool(action)}


def start_size_service():
    """Start score-size.service now, not waiting for it; whether systemd took it (else the timer asks)."""
    try:
        done = subprocess.run(["systemctl", "--user", "start", "--no-block", SERVICE], capture_output=True,
                              timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.returncode == 0


def wait_for_grow(argv, jobs, say=print, wait=GROW_WAIT, step=WAIT_STEP, folder=None, poke=None):
    """Register this run as waiting for `jobs` cores, ask for the grow (`poke`, start_size_service by default) and
    wait for its shutdown, touching the entry; the frozen copy is left for the resumed run. A stop of the owner's marks
    it stopped (a shutdown's leaves it waiting); a wait past `wait` seconds marks it unresumable and exits 1."""
    poke = poke or start_size_service
    frozen.hand_on()
    path = runs.register_waiting(argv, jobs, folder)
    say(f"score run: waiting for size: {jobs} jobs, {conductor.cores()} cores; registered as {path.stem}; "
        "score resume starts it at the boot on the batch size")
    stopped.stop_on_signals(lambda number: say(f"score run: stopped by signal {number} while waiting for size"))
    if not poke():
        say(f"score run: {SERVICE} did not start; score-size.timer asks within 5 minutes")
    try:
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            os.utime(path)
            time.sleep(step)
    except SystemExit as stop:
        code = stop.code if isinstance(stop.code, int) else 0
        if code > 128:
            runs.stopped_by(path, code - 128)
        if json.loads(path.read_text())["state"] != runs.WAITING:  # the owner's stop: nothing resumes it
            frozen.OWNED["handed_on"] = False
        raise
    runs.mark(path, runs.UNRESUMABLE, f"the machine was not grown within {wait // 60} minutes")
    say(f"score run: the machine was not grown within {wait // 60} minutes; marked unresumable")
    frozen.OWNED["handed_on"] = False  # nothing resumes it: its copy goes with it
    sys.exit(1)


def stop_waiting(path, say=print):
    """Mark a waiting run stopped and end its waiting process (the kill switch's)."""
    entry = json.loads(pathlib.Path(path).read_text())
    runs.mark(path, runs.STOPPED)
    if alive(entry.get("pid", 0)):
        os.kill(entry["pid"], signal.SIGTERM)
    say(f"stopped waiting run {entry['id']}")
