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
    python3 tools/cloud/backends/card_queue.py measured

`run` waits for a share, runs the command in a session of its own while it holds it, and when its share is asked back
stops the command's session (SIGTERM, SIGKILL after STOP_SECONDS), gives the share back, waits for one again and starts
the command again: a side job given way to must resume from its own checkpoints (sim body's level 1 tuning does). The
command ends with `run` (its parent's death signal), so it never holds the card outside the queue. `status` is the
PC's one line (the card's shares, what waits, each container's memory) with a line a share and a waiter after it.
A watched share (every `run`, and every claim of the run's container) is measured while held (watch): the card's
highest reading less the desktop, alone or beside other shares, with its cores and memory, one line in measures.jsonl
when it is given back; `measured` gives each job's highest, the card only from takes alone on it.
Standard library only, so any Python runs it (the Newton venv's too).
"""
import argparse
import contextlib
import ctypes
import fcntl
import json
import os
import pathlib
import resource
import signal
import subprocess
import sys
import threading
import time
import uuid

QUEUE = pathlib.Path(os.environ.get("SCORE_CARD_QUEUE", pathlib.Path.home() / ".score-card"))
# The RTX 5080's 16303 MiB less what the Windows desktop holds on it (2.4 GB, measured 2026-10-31 beside the astronaut's
# makes: tools/cloud/characters.py STEP_NEED).
BUDGET_GB = 13.5
DESKTOP_GB = 2.4
# Memory GiB this PC keeps from the shares (8 for WSL, 8 for the run's own steps beside its containers; the same as
# backends/local.py's HOST_RESERVE_GB); the rest is MEMORY_GB, which the shares' memory never passes together.
HOST_RESERVE_GB = 16
# The card's memory read twice a second while a watched share is held (watch); its highest less DESKTOP_GB is the
# share's measured card GB, kept in QUEUE's measures.jsonl with its cores and memory when known (`measured` sums them).
SAMPLER = json.loads(os.environ.get("SCORE_CARD_SAMPLER") or "null") or [
    "nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits", "-lms", "500"]
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


def memory_gb():
    """The memory GiB the shares may hold together: this PC's (/proc/meminfo's MemTotal) less HOST_RESERVE_GB, at
    least 8."""
    line = next(line for line in pathlib.Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal"))
    return max(8, int(line.split()[1]) // 2**20 - HOST_RESERVE_GB)


def memory_free():
    """The memory GiB no live share holds now (memory_gb less their memory_gb)."""
    with queue_lock():
        return memory_gb() - sum(share.get("memory_gb", 0) for share in live("held"))


def entry(folder, job, need, priority, group, memory=0):
    """A new entry in `folder`, its flock held: its open file."""
    path = QUEUE / folder / f"{uuid.uuid4().hex[:12]}.json"
    handle = path.open("w")
    fcntl.flock(handle, fcntl.LOCK_EX)
    handle.write(json.dumps({"id": path.stem, "job": job, "card_gb": need, "memory_gb": memory, "priority": priority,
                             "group": group, "pid": os.getpid(), "since": time.time()}))
    handle.flush()
    return handle


def take(job, card_gb=None, priority="film", group=None, memory=0):
    """A share of the card for `job` (`card_gb` measured, else the whole BUDGET_GB) and of the PC's memory (`memory`
    GiB; None: unmeasured, the whole memory_gb), held until `release`: its open entry file; None, with this process's
    waiting entry written or refreshed, while it does not fit or a waiter before it waits (an earlier priority, or the
    same one asking since earlier)."""
    need = min(card_gb or BUDGET_GB, BUDGET_GB)
    rank = ORDER.index(priority)
    with queue_lock():
        now = time.time()
        room = memory_gb()
        memory = room if memory is None else min(memory, room)
        mine = WAITING.get((job, priority))
        since = json.loads(pathlib.Path(mine.name).read_text())["since"] if mine else now
        ahead = [waiter for waiter in live("waiting", now) if (ORDER.index(waiter["priority"]), waiter["since"])
                 < (rank, since) and (mine is None or waiter["id"] != pathlib.Path(mine.name).stem)]
        held = live("held")
        if ahead or in_use(held, group, need) > BUDGET_GB or sum(
                share.get("memory_gb", 0) for share in held) + memory > room:
            if mine is None:
                WAITING[(job, priority)] = mine = entry("waiting", job, need, priority, group, memory)
            else:
                os.utime(mine.name)
            if not ahead and now - since >= YIELD_SECONDS:
                ask_back([share for share in held if ORDER.index(share["priority"]) > rank])
            return None
        if mine is not None:
            release(WAITING.pop((job, priority)))
        return entry("held", job, need, priority, group, memory)


def resize(handle, memory):
    """The memory GiB the share `handle` holds set to `memory` (a claim that let some of its work go)."""
    with queue_lock():
        held = json.loads(pathlib.Path(handle.name).read_text())
        handle.seek(0)
        handle.truncate()
        handle.write(json.dumps({**held, "memory_gb": memory}))
        handle.flush()


def ask_back(shares):
    """A mark under `yield/` for each of `shares`, which its `run` reads as its share asked back."""
    for share in shares:
        (QUEUE / "yield" / f"{share['id']}.json").touch()


def asked_back(handle):
    """Whether the share whose open entry is `handle` was asked back (ask_back)."""
    return (QUEUE / "yield" / pathlib.Path(handle.name).name).exists()


def watch(handle):
    """The share `handle` measured while it is held: SAMPLER read in a thread for the card's highest memory and whether
    any other share was held at a reading (nothing when this PC has no nvidia-smi); `handle`."""
    handle.card_peak, handle.alone, handle.began = 0.0, True, time.time()
    try:
        handle.reader = subprocess.Popen(SAMPLER, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except OSError:
        return handle
    handle.reading = threading.Thread(target=read_card, args=(handle,), daemon=True)
    handle.reading.start()
    return handle


def read_card(handle):
    """watch's thread: each reading of the card's MiB into `handle`'s card_peak (GiB) and alone."""
    for line in handle.reader.stdout:
        if line.strip().isdigit():
            handle.card_peak = max(handle.card_peak, int(line) / 1024)
            handle.alone = handle.alone and len(list((QUEUE / "held").glob("*.json"))) <= 1


def record(handle, cores=None, memory_gb=None):
    """A watched share's measure appended to measures.jsonl: its job, seconds, card GB (its highest reading less
    DESKTOP_GB), whether it was alone on the card, and the `cores` and `memory_gb` its holder measured."""
    handle.reader.terminate()
    handle.reader.wait()
    handle.reading.join()
    held = json.loads(pathlib.Path(handle.name).read_text())
    line = {"job": held["job"], "at": time.time(), "seconds": round(time.time() - handle.began, 1),
            "card_gb": round(max(0.0, handle.card_peak - DESKTOP_GB), 2), "alone": handle.alone, "cores": cores,
            "memory_gb": memory_gb}
    with (QUEUE / "measures.jsonl").open("a") as measures:
        measures.write(json.dumps(line) + "\n")


def measured():
    """One line a job of measures.jsonl: its takes, the highest card GB of those alone on the card (others' shares
    beside it would count in a reading), and the highest cores and memory GB."""
    rows = {}
    path = QUEUE / "measures.jsonl"
    for line in path.read_text().splitlines() if path.exists() else []:
        item = json.loads(line)
        row = rows.setdefault(item["job"], {"takes": 0, "alone": [], "cores": [], "memory_gb": []})
        row["takes"] += 1
        row["alone"] += [item["card_gb"]] if item["alone"] else []
        row["cores"] += [item["cores"]] if item["cores"] is not None else []
        row["memory_gb"] += [item["memory_gb"]] if item["memory_gb"] is not None else []
    return "\n".join(f"{job}: {row['takes']} takes, card {max(row['alone'], default='unmeasured')} GB "
                     f"({len(row['alone'])} alone), cores {max(row['cores'], default='unmeasured')}, memory "
                     f"{max(row['memory_gb'], default='unmeasured')} GB" for job, row in sorted(rows.items()))


def release(handle, cores=None, memory_gb=None):
    """A share (or a waiting entry) given back: its measure recorded when it was watched, its file and its ask-back
    mark removed, its flock let go."""
    if getattr(handle, "reader", None):
        record(handle, cores, memory_gb)
    pathlib.Path(handle.name).unlink(missing_ok=True)
    (QUEUE / "yield" / pathlib.Path(handle.name).name).unlink(missing_ok=True)
    handle.close()


def status():
    """The PC's line (the card's shares against BUDGET_GB, what waits, its free memory, each running container's
    memory), then one
    line a live share and a live waiter."""
    with queue_lock():
        held, waiting = live("held"), live("waiting", time.time())
    memory = sum(share.get("memory_gb", 0) for share in held)
    lines = [f"card {in_use(held, None, 0):.1f} of {BUDGET_GB} GB held, memory {memory:.1f} of {memory_gb()} GiB, "
             f"{len(waiting)} waiting; {free_memory()}; {containers()}"]
    lines += [f"{name} {item['job']} {item['card_gb']} GB card {item.get('memory_gb', 0)} GiB memory "
              f"{item['priority']} pid {item['pid']}"
              for name, items in (("held", held), ("waits", waiting)) for item in items]
    return "\n".join(lines)


def free_memory():
    """This PC's available memory (/proc/meminfo's MemAvailable), as "<GB> GB free"."""
    line = next(line for line in pathlib.Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable"))
    return f"{int(line.split()[1]) * 1024 / 1e9:.1f} GB free"


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


def share_for(job, card_gb, priority, memory=0):
    """`job`'s share, waited for (said once on stderr while it waits)."""
    said = False
    while (handle := take(job, card_gb, priority, memory=memory)) is None:
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


def run(job, card_gb, priority, command, memory=0):
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
        handle = watch(share_for(job, card_gb, priority, memory))
        before = resource.getrusage(resource.RUSAGE_CHILDREN)
        child = subprocess.Popen(command, start_new_session=True, preexec_fn=ends_with_parent)
        while child.poll() is None and not asked_back(handle):
            with contextlib.suppress(subprocess.TimeoutExpired):
                child.wait(LOOK_SECONDS)
        if child.poll() is not None:
            release(handle, *used_since(before, handle.began))
            return child.returncode
        print(f"card_queue: {job} gives the card way to a waiting film claim; it starts again after",
              file=sys.stderr, flush=True)
        stop(child)
        release(handle, *used_since(before, handle.began))


def used_since(before, began):
    """(Cores, memory GB) of the commands `run` waited for since `before` (getrusage of its children) and `began`:
    their processor seconds over the wall seconds, and the highest resident memory of one of them."""
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    seconds = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
    return round(seconds / max(time.time() - began, 1e-3), 2), round(after.ru_maxrss * 1024 / 1e9, 2)


def main(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="action", required=True)
    runs = commands.add_parser("run", help="run the command while it holds a share of the card")
    runs.add_argument("--job", required=True)
    runs.add_argument("--card-gb", type=float, help="the job's measured card GB; unmeasured takes the whole card")
    runs.add_argument("--priority", choices=ORDER, default="side")
    runs.add_argument("--memory-gb", type=float, default=0,
                      help="memory it holds of the run's room (0: it lives in the PC's own reserve, its scope capped)")
    runs.add_argument("command", nargs=argparse.REMAINDER)
    commands.add_parser("status", help="the PC's line: what holds the card, what waits, the containers' memory")
    commands.add_parser("measured", help="each job's measured card GB, cores and memory")
    parsed = parser.parse_args(arguments)
    if parsed.action in ("status", "measured"):
        print(status() if parsed.action == "status" else measured())
        return
    command = parsed.command[1:] if parsed.command[:1] == ["--"] else parsed.command
    if not command:
        parser.error("run needs a command after --")
    sys.exit(run(parsed.job, parsed.card_gb, parsed.priority, command, parsed.memory_gb))


if __name__ == "__main__":
    main()
