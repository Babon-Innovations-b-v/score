"""The run registry: every `score run` that drives lines leaves runs/<id>.json in $PROPS_HOME (its arguments, commit,
worktree, pid, start time and state), so a run a reboot or a closed session cut off can be started again from its own
worktree (C9: PC reboots and session restarts lost runs).

    .venv/bin/python -m score resume [--dry]     # start again every run whose process is gone and that never ended

A run is `running` while it drives, `ended` once its drive returned (every line done or stopped), `crashed` when the
runner itself raised (starting it again would only raise again), `stopped` when a signal stopped it that was not a
shutdown's (Ctrl-C's SIGINT, a closed session's SIGHUP, a SIGTERM while the machine is up: the owner chose to stop it,
so it is never bought again unasked), `resumed` once `score resume` started it again, and `unresumable` when resume
would not or could not start it (its `why` says which; `score status` lists them, and resume never tries one again).
A run a reboot cut off stays `running`: a shutdown's SIGTERM, or no signal at all (wsl --shutdown). Resume takes only
`running` runs of an earlier boot (each entry keeps /proc/sys/kernel/random/boot_id), so a live run, or one killed
since this boot, is never started twice; it holds a lock while it runs, so two resumes at once start a run once, and
it removes the .partial files an earlier boot's writes left in the store. It starts a run only from the code that
registered it: its worktree still there, at the entry's commit, with nothing uncommitted. And only a run alive shortly
before this boot: a driving run touches its entry every HEARTBEAT seconds, and one silent for over RESUME_WINDOW
before this boot began died some other way (an OOM kill, a SIGKILL) and is never started again unasked. The systemd
user unit `.claude/scripts/score-resume.service` runs `score resume` at boot; installing it is the owner's step.

One commit per store (C10), in the same folder: every `score run` claims the store (`claim`), recording its commit,
worktree, pid, the pid's start time and the nodes it would make in runs/active.json (which `entries` leaves out),
under a lock on runs/active.lock, and is refused while a live run from another commit holds a claim (the refusal names
that run, its commit and its worktree). A run at the same commit joins only when none of the nodes it would make is
one the other would make: a node that stands accepted (the environment nodes every place reads, once made) is not
made, so one `score run world1 --place <place>` per place runs side by side. A claim whose pid is gone, or whose pid
now belongs to a process started at another time (a reused pid), is dropped as if it were never there.

A run from a worktree with tracked changes not committed (an untracked scratch file is not one) that would buy a
paid row is refused unless given --uncommitted; a free run goes on as it is. Either registers as its commit
"uncommitted in <worktree>", so it never joins a run of another worktree or of the clean commit.

Fault (2026-10-17): two runs at different code over one store, each re-keying and re-making the other's rows, about
6 hours of clashes.
"""
import contextlib
import datetime
import fcntl
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import threading
import time

from score.graph import node_name
from score.store import PROPS_HOME, Store, locked
from score.store.durable import write_whole

REPO = pathlib.Path(__file__).resolve().parents[2]
RUNS = PROPS_HOME / "runs"
LOGS = PROPS_HOME / "logs"
RUNNING, ENDED, CRASHED, STOPPED, RESUMED = "running", "ended", "crashed", "stopped", "resumed"
UNRESUMABLE = "unresumable"
HEARTBEAT = 60  # seconds between a driving run's touches of its entry
RESUME_WINDOW = 12 * 3600  # a run silent longer than this before the boot began is not a reboot's
DETACH = "--detach"
BOOT_ID = pathlib.Path("/proc/sys/kernel/random/boot_id")
PARTIAL = "*.partial"
ACTIVE, ACTIVE_LOCK = "active.json", "active.lock"  # the claims (C10), not run entries


def log_path(name):
    """A fresh log path for one detached run, under $PROPS_HOME/logs (a reboot empties /tmp)."""
    LOGS.mkdir(parents=True, exist_ok=True)
    return LOGS / f"{name}-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000000:06d}.log"


def commit_of(worktree):
    """The commit a worktree has checked out, or None outside git."""
    done = subprocess.run(["git", "-C", str(worktree), "rev-parse", "HEAD"], capture_output=True, text=True)
    return done.stdout.strip() if done.returncode == 0 else None


def uncommitted(worktree):
    """True when a worktree has changes not committed (untracked files too, as a finish record counts them) or git
    cannot tell."""
    done = subprocess.run(["git", "-C", str(worktree), "status", "--porcelain"], capture_output=True, text=True)
    return done.returncode != 0 or bool(done.stdout.strip())


def boot_id():
    """This boot's id: a new one each time the machine starts."""
    return BOOT_ID.read_text().strip()


def boot_time():
    """When this boot began, in seconds since the epoch (/proc/stat's btime)."""
    line = next(line for line in pathlib.Path("/proc/stat").read_text().splitlines() if line.startswith("btime "))
    return int(line.split()[1])


def new_entry(argv, worktree=REPO):
    """This process's run (`argv`: score's own arguments, --detach left out) as a running entry, not written yet."""
    started = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return {"id": f"{started.replace(':', '').replace('-', '')[:15]}-{os.getpid()}",
            "argv": [word for word in argv if word != DETACH], "commit": commit_of(worktree),
            "worktree": str(worktree), "pid": os.getpid(), "boot": boot_id(), "started": started, "state": RUNNING}


def entry_path(entry, folder=None):
    """Where a run's entry is kept in the registry."""
    return pathlib.Path(folder or RUNS) / f"{entry['id']}.json"


def written(path, entry):
    """Write a run's entry whole into the registry; its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    write_whole(path, json.dumps(entry, indent=1).encode())
    return path


def register(argv, folder=None, worktree=REPO):
    """Record this process's run as running; its entry's path."""
    entry = new_entry(argv, worktree)
    return written(entry_path(entry, folder), entry)


def mark(path, state, why=None):
    """Set a registered run's state (and why, for an unresumable one)."""
    entry = json.loads(pathlib.Path(path).read_text())
    entry["state"] = state
    if why:
        entry["why"] = why
    write_whole(pathlib.Path(path), json.dumps(entry, indent=1).encode())


@contextlib.contextmanager
def beating(path):
    """Touch a registered run's entry every HEARTBEAT seconds while the block runs: its last sign of life."""
    done = threading.Event()

    def beat():
        while not done.wait(HEARTBEAT):
            with contextlib.suppress(FileNotFoundError):  # its registry folder removed under it (a test's)
                os.utime(path)
    beater = threading.Thread(target=beat, name="run-heartbeat", daemon=True)
    beater.start()
    try:
        yield
    finally:
        done.set()


def shutting_down():
    """True while the machine is going down (systemd says `stopping`); False when it is up or cannot tell."""
    try:
        done = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return done.stdout.strip() == "stopping"


def stopped_by(path, number):
    """Mark a run a stopping signal ended: `stopped` unless it is a shutdown's SIGTERM (then it stays `running`, for
    resume after the reboot). Unsure counts as the owner's stop: a run is never bought again on a guess."""
    if number == signal.SIGTERM and shutting_down():
        return
    mark(path, STOPPED)


def entries(folder=RUNS):
    """{path: entry} of every readable registered run, oldest first; an unreadable one is named on stderr."""
    found = {}
    for path in sorted(pathlib.Path(folder).glob("*.json")):
        if path.name == ACTIVE:
            continue
        try:
            found[path] = json.loads(path.read_text())
        except ValueError:
            print(f"runs: {path} is unreadable, left out", file=sys.stderr, flush=True)
    return found


def node_times(store):
    """Every make's start and end as the store's finish records log them (graph.finish_record, written as each make
    ends, local and paid rows alike): [{node, stage, place, key, started, finished, minutes, machine}], oldest first.
    A make that raised wrote no record, and a record carried over without a make is no make, so neither is here. tools/costs/per_unit.py --store reads them into the
    per-unit file's `node_minutes`, which the runner's schedule times a row by."""
    records = [store.read(key) for key in store.objects.keys("records/") if key.endswith(".json")]
    return sorted(({name: record.get(name) for name in ("node", "stage", "place", "key", "started", "finished",
                                                         "minutes", "machine")}
                   for record in records if record.get("minutes") is not None and not record.get("carried")), key=lambda made: made["finished"])


def stranded(folder=RUNS):
    """{path: entry} of every run an earlier boot cut off: still `running` and registered under another boot id."""
    this_boot = boot_id()
    return {path: entry for path, entry in entries(folder).items()
            if entry.get("state") == RUNNING and entry.get("boot") not in (None, this_boot)}


def restart_command(entry):
    """The command that starts a run again, detached, with its worktree's own Python when it has one."""
    python = pathlib.Path(entry["worktree"]) / ".venv/bin/python"
    return [str(python) if python.exists() else sys.executable, "-m", "score", *entry["argv"], DETACH]


def describe(entry):
    """One line naming a stranded run: its id, worktree, commit and arguments."""
    return (f"{entry['id']}: worktree={entry['worktree']} commit={(entry.get('commit') or '-')[:12]} "
            f"argv={' '.join(entry['argv'])}")


def refusal(path, entry):
    """Why a stranded run must not be started again, or None: it was silent too long before this boot, or its
    worktree is gone, on another commit or has changes not committed (the code that would run is not the code that
    registered it)."""
    if pathlib.Path(path).stat().st_mtime < boot_time() - RESUME_WINDOW:
        return f"its last sign of life was over {RESUME_WINDOW // 3600} h before this boot: not a reboot's cut"
    worktree = pathlib.Path(entry["worktree"])
    if not worktree.is_dir():
        return "its worktree is gone"
    head = commit_of(worktree)
    if not entry.get("commit") or head != entry["commit"]:
        return f"its worktree is at {(head or 'no commit')[:12]}, not the commit that registered it"
    if uncommitted(worktree):
        return "its worktree has changes not committed"
    return None


def restart(path, entry, say):
    """Start one stranded run again from its own worktree and mark it resumed; one it must not start (refusal), or
    whose start fails, is marked unresumable with why, so the owner sees it (score status) and no boot tries again."""
    why = refusal(path, entry)
    if why:
        mark(path, UNRESUMABLE, why)
        say(f"skipped {describe(entry)}: {why}")
        return
    done = subprocess.run(restart_command(entry), cwd=entry["worktree"], stdin=subprocess.DEVNULL,
                          capture_output=True, text=True)
    if done.returncode != 0:
        why = f"its restart failed: exit={done.returncode} {done.stderr.strip()[-400:]}"
        mark(path, UNRESUMABLE, why)
        say(f"failed {describe(entry)}: {why}")
        return
    mark(path, RESUMED)
    say(f"resumed {describe(entry)}: {done.stdout.strip()}")


def unresumable(folder=RUNS):
    """One line per run resume would not or could not start: its id, worktree, commit, arguments and why."""
    return [f"{describe(entry)}: {entry.get('why', '')}" for entry in entries(folder).values()
            if entry.get("state") == UNRESUMABLE]


def stale_partials(roots, before):
    """Every .partial file or folder under `roots` last written before `before` (seconds since the epoch)."""
    return [path for root in roots if pathlib.Path(root).is_dir() for path in sorted(pathlib.Path(root).rglob(PARTIAL))
            if path.lstat().st_mtime < before]


def removed(path):
    """Delete a left-over partial file or folder."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def store_roots():
    """Where the framework store's writes leave .partial files: its objects and its checkouts."""
    store = Store.default()
    return store.objects.root, store.cache / "checkouts"


def resume(dry, say, folder=RUNS, swept=None):
    """Start again every stranded run (with `dry`, only list them), one resume at a time, and remove the partial files
    an earlier boot left under `swept` (the store's roots by default); the number of runs found."""
    folder = pathlib.Path(folder)
    with locked(folder / ".resume.lock"):
        found = stranded(folder)
        for path, entry in found.items():
            if not dry:
                restart(path, entry, say)
                continue
            why = refusal(path, entry)
            say(f"would skip {describe(entry)}: {why}" if why else f"would resume {describe(entry)}")
        if not found:
            say("no run to resume")
        if not dry:
            for path in stale_partials((folder, *(store_roots() if swept is None else swept)), boot_time()):
                removed(path)
                say(f"removed {path}: an earlier boot's cut write")
    return len(found)


# --- one commit per store (C10) --------------------------------------------------------------------------------------

def tracked_changes(repo=REPO):
    """True when a tracked file of the worktree has changes not committed (untracked files do not count)."""
    found = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True, check=True)
    return bool(found.stdout.strip())


def identity(commit, dirty, worktree):
    """The commit a run registers as: the commit itself, or one of its own when the worktree has changes."""
    return f"{commit} uncommitted in {worktree}" if dirty else commit


def dirty_refusal(dirty, uncommitted, paid):
    """Why a run may not start from this worktree (changes not committed, a paid row to buy and no --uncommitted), or
    None."""
    if dirty and paid and not uncommitted:
        return (f"refused: {REPO} has changes not committed and this run would buy paid rows; commit them, or give "
                "--uncommitted to run them as they are (no other commit's run may then share the store)")
    return None


def would_make(runner, nodes):
    """The names of the `nodes` ((stage, place)) a drive would make: those that do not stand accepted now."""
    with runner.still():
        return [node_name(stage, place) for stage, place in nodes if runner.standing(stage, place) is not None]


def start_time(pid):
    """The process's start time (/proc/<pid>/stat field 22, in clock ticks since boot), or None when it is gone."""
    try:
        stat = pathlib.Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return stat.rpartition(")")[2].split()[19]  # fields from the 3rd on follow the name's closing bracket


def live(entries):
    """The registrations whose process still runs: its pid is there and started when the registered one did."""
    return {pid: entry for pid, entry in entries.items()
            if entry.get("started") is not None and start_time(int(pid)) == entry["started"]}


def clash(entries, commit, nodes):
    """Why a run at `commit` that would make `nodes` may not join the live `entries`, naming the run it clashes with,
    or None."""
    for pid, entry in entries.items():
        if entry["commit"] != commit:
            return (f"refused: run pid {pid} from commit {entry['commit']} in {entry['worktree']} is live on this "
                    f"store; this run is at {commit}. Wait for it to end or stop it.")
        shared = sorted(set(entry["nodes"]) & set(nodes))
        if shared:
            return (f"refused: run pid {pid} at the same commit in {entry['worktree']} would also make "
                    f"{len(shared)} of these nodes ({', '.join(shared[:5])}{', ...' if len(shared) > 5 else ''})")
    return None


@contextlib.contextmanager
def claims_locked(folder):
    """The live registrations in `folder`, held under its lock; what the caller leaves in the dict is written back."""
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / ACTIVE_LOCK, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = folder / ACTIVE
        entries = live(json.loads(path.read_text())) if path.exists() else {}
        yield entries
        partial = folder / f"{ACTIVE}.{os.getpid()}.partial"
        partial.write_text(json.dumps(entries, indent=1, sort_keys=True))
        os.replace(partial, path)


def claim(commit, nodes, pid, worktree=REPO, folder=RUNS):
    """Record this run (commit, worktree, pid and its start time, the nodes it would make) unless it clashes with a
    live one; the refusal, or None when registered."""
    with claims_locked(folder) as entries:
        refused = clash(entries, commit, nodes)
        if not refused:
            entries[str(pid)] = {"commit": commit, "worktree": str(worktree), "nodes": sorted(nodes),
                                 "started": start_time(pid)}
    return refused


def claim_refusal(commit, nodes, folder=RUNS):
    """The refusal a run would get now, registering nothing (before detaching: the detached run registers itself)."""
    with claims_locked(folder) as entries:
        return clash(entries, commit, nodes)


def unclaim(pid, folder=RUNS):
    """Drop this run's registration."""
    with claims_locked(folder) as entries:
        entries.pop(str(pid), None)
