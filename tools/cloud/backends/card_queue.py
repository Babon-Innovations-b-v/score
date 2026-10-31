"""This PC's one card queue (PRD #73; the owner, 2026-10-31: "go full docker ... even for local, then we can control
and manage this way better"): every user of the card, inside the run and outside it, holds a measured share of it
while it works, so no two users together pass what the card holds (2026-10-31: a SAM 3 masks job in the run's
container failed with cudaErrorDevicesUnavailable while sim body's level 1 seeds held the card outside it).

A share is an entry file in QUEUE's `held/`, its JSON the job, its card GB, its priority and its group, held by an
exclusive flock on its open file for as long as the holder lives: a holder that dies frees its share with no clean-up.
A take is admitted while the held shares (each group counted once, at its largest: the run's Blender claims share the
card's turns, card_turn.py) and its own fit BUDGET_GB, and no fresh waiter of an earlier priority (ORDER) waits; a take
that is not admitted leaves a waiting entry (`waiting/`, refreshed at each ask, stale after WAIT_SECONDS), so a film
claim the runner asks again every few seconds keeps every side job off the card until it has its share. A need not
measured takes the whole card. A film claim that has waited YIELD_SECONDS asks every side share back (a mark under
`yield/` for each): a side job on the card gives way at once rather than at its end, since a stopped process (SIGSTOP)
keeps its card memory. QUEUE is one folder for the whole PC, never under a PROPS_HOME: the run and the agents work
under different homes and share one card.

    python3 tools/cloud/backends/card_queue.py run --job <name> --card-gb <GB> [--priority side] -- <command> ...
    python3 tools/cloud/backends/card_queue.py status

`run` waits for a share, runs the command in a session of its own while it holds it, and when its share is asked back
stops the command's session (SIGTERM, SIGKILL after STOP_SECONDS), gives the share back, waits for one again and starts
the command again: a side job given way to must resume from its own checkpoints (sim body's level 1 tuning does). The
command ends with `run` (its parent's death signal), so it never holds the card outside the queue. `status` is the
PC's one line (the card's shares, what waits, each container's memory) with a line a share and a waiter after it.
Standard library only, so any Python runs it (the Newton venv's too).
"""
import argparse
import contextlib
import ctypes
import fcntl
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
import uuid

QUEUE = pathlib.Path(os.environ.get("SCORE_CARD_QUEUE", pathlib.Path.home() / ".score-card"))
# The RTX 5080's 16303 MiB less what the Windows desktop holds on it (2.4 GB, measured 2026-10-31 beside the astronaut's
# makes: tools/cloud/characters.py STEP_NEED).
BUDGET_GB = 13.5
ORDER = ("film", "side")  # earlier first: the run's work for the film, then everything else (tuning, proofs, scratch)
WAIT_SECONDS = 120  # a waiting entry not refreshed for this long waits no more (its process stopped asking)
LOOK_SECONDS = 2  # between asks of `run` while it waits, and between its looks for its share asked back
YIELD_SECONDS = 60  # a film claim waiting this long asks the side shares back
STOP_SECONDS = 30  # a side command asked back has this long after SIGTERM before SIGKILL
WAITING = {}  # {(job, priority): this process's open waiting entry}


@contextlib.contextmanager
def queue_lock():
    """The block run alone among the queue's takes, releases and readers."""
    for folder in ("held", "waiting", "yield"):
        (QUEUE / folder).mkdir(parents=True, exist_ok=True)
    with (QUEUE / "queue.lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def live(folder, now=None):
    """The entries in `folder` whose holder lives (its flock held; within WAIT_SECONDS of `now` when given); every
    other one removed."""
    found = []
    for path in sorted((QUEUE / folder).glob("*.json")):
        try:
            probe = path.open()
        except FileNotFoundError:  # given back meanwhile (release removes it outside the queue's lock)
            continue
        with probe:
            try:
                fcntl.flock(probe, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                if now is None or now - path.stat().st_mtime < WAIT_SECONDS:
                    found.append(json.loads(path.read_text()))
                continue
        path.unlink(missing_ok=True)
        (QUEUE / "yield" / path.name).unlink(missing_ok=True)
    return found


def in_use(held, group, need):
    """The card GB the `held` shares and a new one of `need` in `group` add up to, each group at its largest."""
    largest = {}
    for entry in [*held, {"id": "new", "group": group, "card_gb": need}]:
        key = entry["group"] or entry["id"]
        largest[key] = max(largest.get(key, 0), entry["card_gb"])
    return sum(largest.values())


def entry(folder, job, need, priority, group):
    """A new entry in `folder`, its flock held: its open file."""
    path = QUEUE / folder / f"{uuid.uuid4().hex[:12]}.json"
    handle = path.open("w")
    fcntl.flock(handle, fcntl.LOCK_EX)
    handle.write(json.dumps({"id": path.stem, "job": job, "card_gb": need, "priority": priority, "group": group,
                             "pid": os.getpid(), "since": time.time()}))
    handle.flush()
    return handle


def take(job, card_gb=None, priority="film", group=None):
    """A share of the card for `job` (`card_gb` measured, else the whole BUDGET_GB), held until `release`: its open
    entry file; None, with this process's waiting entry written or refreshed, while it does not fit or an earlier
    priority waits."""
    need = min(card_gb or BUDGET_GB, BUDGET_GB)
    rank = ORDER.index(priority)
    with queue_lock():
        now = time.time()
        mine = WAITING.get((job, priority))
        ahead = [waiter for waiter in live("waiting", now) if ORDER.index(waiter["priority"]) < rank]
        held = live("held")
        if ahead or in_use(held, group, need) > BUDGET_GB:
            if mine is None:
                WAITING[(job, priority)] = mine = entry("waiting", job, need, priority, group)
            else:
                os.utime(mine.name)
            if not ahead and now - json.loads(pathlib.Path(mine.name).read_text())["since"] >= YIELD_SECONDS:
                ask_back([share for share in held if ORDER.index(share["priority"]) > rank])
            return None
        if mine is not None:
            release(WAITING.pop((job, priority)))
        return entry("held", job, need, priority, group)


def ask_back(shares):
    """A mark under `yield/` for each of `shares`, which its `run` reads as its share asked back."""
    for share in shares:
        (QUEUE / "yield" / f"{share['id']}.json").touch()


def asked_back(handle):
    """Whether the share whose open entry is `handle` was asked back (ask_back)."""
    return (QUEUE / "yield" / pathlib.Path(handle.name).name).exists()


def release(handle):
    """A share (or a waiting entry) given back: its file and its ask-back mark removed, its flock let go."""
    pathlib.Path(handle.name).unlink(missing_ok=True)
    (QUEUE / "yield" / pathlib.Path(handle.name).name).unlink(missing_ok=True)
    handle.close()


def status():
    """The PC's line (the card's shares against BUDGET_GB, what waits, each running container's memory), then one
    line a live share and a live waiter."""
    with queue_lock():
        held, waiting = live("held"), live("waiting", time.time())
    lines = [f"card {in_use(held, None, 0):.1f} of {BUDGET_GB} GB held, {len(waiting)} waiting; {containers()}"]
    lines += [f"{name} {item['job']} {item['card_gb']} GB {item['priority']} pid {item['pid']}"
              for name, items in (("held", held), ("waits", waiting)) for item in items]
    return "\n".join(lines)


def containers():
    """Each running container's name and memory use against its limit, from `docker stats`; what docker said when it
    did not answer."""
    try:
        answer = subprocess.run(["docker", "stats", "--no-stream", "--format", "{{.Name}} {{.MemUsage}}"],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"containers unread ({error})"
    if answer.returncode:
        return f"containers unread ({answer.stderr.strip()[:80]})"
    return ", ".join(answer.stdout.split("\n")[:-1]) or "no container running"


def share_for(job, card_gb, priority):
    """`job`'s share, waited for (said once on stderr while it waits)."""
    said = False
    while (handle := take(job, card_gb, priority)) is None:
        if not said:
            print(f"card_queue: {job} waits for {card_gb or BUDGET_GB} GB of the card", file=sys.stderr, flush=True)
            said = True
        time.sleep(LOOK_SECONDS)
    return handle


def ends_with_parent():
    """In the command's process before it starts: SIGTERM to it when `run` dies (Linux's PR_SET_PDEATHSIG)."""
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM)


def stop(child):
    """`child`'s whole session ended: SIGTERM, then SIGKILL after STOP_SECONDS."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(STOP_SECONDS)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(child.pid, signal.SIGKILL)
        child.wait()


def run(job, card_gb, priority, command):
    """`command` run while `job` holds its share, stopped and started again each time the share is asked back; its
    exit code. A stop signal to `run` ends the command first."""
    child = None

    def end(number, _frame):
        if child is not None:
            stop(child)
        sys.exit(128 + number)

    signal.signal(signal.SIGTERM, end)
    signal.signal(signal.SIGINT, end)
    while True:
        handle = share_for(job, card_gb, priority)
        child = subprocess.Popen(command, start_new_session=True, preexec_fn=ends_with_parent)
        while child.poll() is None and not asked_back(handle):
            with contextlib.suppress(subprocess.TimeoutExpired):
                child.wait(LOOK_SECONDS)
        if child.poll() is not None:
            release(handle)
            return child.returncode
        print(f"card_queue: {job} gives the card way to a waiting film claim; it starts again after",
              file=sys.stderr, flush=True)
        stop(child)
        release(handle)


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="action", required=True)
    runs = commands.add_parser("run", help="run the command while it holds a share of the card")
    runs.add_argument("--job", required=True)
    runs.add_argument("--card-gb", type=float, help="the job's measured card GB; unmeasured takes the whole card")
    runs.add_argument("--priority", choices=ORDER, default="side")
    runs.add_argument("command", nargs=argparse.REMAINDER)
    commands.add_parser("status", help="what holds the card and what waits")
    parsed = parser.parse_args(arguments)
    if parsed.action == "status":
        print(status())
        return
    command = parsed.command[1:] if parsed.command[:1] == ["--"] else parsed.command
    if not command:
        parser.error("run needs a command after --")
    sys.exit(run(parsed.job, parsed.card_gb, parsed.priority, command))


if __name__ == "__main__":
    main()
