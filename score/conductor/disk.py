"""The data disk under $PROPS_HOME: what fills it, the floor under which no run starts, and the sweep of frozen copies
no run needs any more (2026-10-26 23:45 UTC: 0.24 GB free of 91 GB, Batch 1 died with "No space left on device";
about twelve runs had started that day, and the copies of the ones stopped, failed or cut off stayed on the disk).

    python -m score.conductor disk           # one summary line, the biggest folders, the whole list in conductor/disk.json
    python -m score.conductor clean-frozen   # remove every frozen copy no run needs; what it freed, one line a copy

launch_refusal() is `score run`'s check before it makes its copy: a run is refused while the disk has under FLOOR_GB
free. health.read() carries FLOOR_GB and warning() (a note on the Machine card).

A frozen copy (graph/frozen.py: the worktree <name> and its home <name>.home under $PROPS_HOME/frozen) is dead when
no registered run needs it (`needed`: a waiting run, a running one this boot whose process lives, a running one of an
earlier boot that resume may still start, a live claim in runs/active.json), no process works in it (its working
folder in it, SCORE_FROZEN naming it, or its path on its command line) and it is over YOUNG_SECONDS old (a run makes
its copy before it chdirs into it and registers). clean-frozen refuses everything while it cannot tell: a run entry or
the claims file that does not parse, or a process of this user whose command line it cannot read (a non-dumpable
one, systemd --user say, keeps its environment and folder closed even to its own user: it is judged by its command
line, and is never a run). It
removes a dead copy's worktree with `git worktree remove --force` from the checkout it was made from (frozen.remove: a
copy git cannot remove is deleted and pruned), closes its home (frozen.home_closed: an entry the run made at its top level moves into the real
home) and removes the home, which by then holds links only; never the store, the design or anything a link points
at. `score resume` (boot) and the sync pass run it.
"""
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import time

from score import conductor
from score.conductor import size
from score.graph import frozen, runs
from score.store import PROPS_HOME

FLOOR_GB = 10  # under this many GB free no run starts, and the Machine card warns
YOUNG_SECONDS = 15 * 60  # a copy younger than this may be one a run is still making
SHOWN = 20  # folders `disk` prints; the rest are in its file
REPO = pathlib.Path(__file__).resolve().parents[2]  # the checkout, measured when on the home's disk


class Unprovable(Exception):
    """clean-frozen cannot tell which copies are dead: it removes none."""


def free_gb(path=None):
    """The free GB on the disk holding `path` (PROPS_HOME), read at its nearest existing folder."""
    path = pathlib.Path(path or PROPS_HOME)
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free / 1024 ** 3


def warning(free, floor=None):
    """The Machine card's note while the data disk has under `floor` (FLOOR_GB) GB free, else None."""
    floor = FLOOR_GB if floor is None else floor
    return None if free >= floor else (f"disk: {free:.1f} GB free, under the {floor} GB floor: no run starts; "
                                       "free room with the door's clean-frozen")


def launch_refusal(path=None, floor=None):
    """Why `score run` must not start now (under `floor`, FLOOR_GB, GB free on PROPS_HOME's disk), or None."""
    floor = FLOOR_GB if floor is None else floor
    free = free_gb(path)
    return None if free >= floor else (f"refused: {free:.1f} GB free on the data disk ({path or PROPS_HOME}), under "
                                       f"the {floor} GB floor a run needs; free room first (the door's disk and "
                                       "clean-frozen)")


# --- disk: what fills it ---------------------------------------------------------------------------------------------

def du(root, depth):
    """[(bytes, path)] of `root` and its folders down to `depth`, on its own filesystem (`du -x`), links not followed."""
    done = subprocess.run(["du", "-x", "-B1", f"--max-depth={depth}", str(root)], capture_output=True, text=True)
    found = []
    for line in done.stdout.splitlines():
        count, _, path = line.partition("\t")
        found.append((int(count), path))
    return found


def roots(home=None):
    """{root: depth} measured: the home two levels down (frozen/<copy>, store/objects, store/cache, ...), and the
    checkout and the user's cache (the backup's restic cache) when they are on the home's disk."""
    home = pathlib.Path(home or PROPS_HOME)
    device = home.stat().st_dev
    extra = [REPO, pathlib.Path.home() / ".cache"]
    return {home: 2, **{root: 1 for root in extra if root.is_dir() and root.stat().st_dev == device
                        and not root.is_relative_to(home)}}


def report(home=None, out=None):
    """Measure the disk (roots), write every folder's size to `out` (conductor/disk.json), biggest first; (summary
    line, the SHOWN biggest lines)."""
    home = pathlib.Path(home or PROPS_HOME)
    sizes = sorted((pair for root, depth in roots(home).items() for pair in du(root, depth)), reverse=True)
    usage = shutil.disk_usage(home)
    out = pathlib.Path(out or conductor.HOME / "disk.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                               "free_gb": round(usage.free / 1024 ** 3, 2), "total_gb": round(usage.total / 1024 ** 3, 2),
                               "folders": [{"path": path, "gb": round(count / 1024 ** 3, 3)}
                                           for count, path in sizes]}, indent=1))
    copies = [count for count, path in sizes if pathlib.Path(path).parent == home / "frozen"]
    summary = (f"disk: {usage.free / 1024 ** 3:.1f} GB free of {usage.total / 1024 ** 3:.0f} GB; "
               f"{len(copies)} frozen copies and homes hold {sum(copies) / 1024 ** 3:.1f} GB; every folder in {out}")
    return summary, [f"{count / 1024 ** 3:8.2f} GB  {path}" for count, path in sizes[:SHOWN]]


# --- clean-frozen: the copies no run needs ---------------------------------------------------------------------------

def needed(runs_folder):
    """The worktrees a registered run still needs (the module's docstring); Unprovable when an entry or the claims
    file does not parse."""
    folder = pathlib.Path(runs_folder)
    found, this_boot = set(), runs.boot_id()
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            entry = json.loads(path.read_text())
        except ValueError:
            raise Unprovable(f"{path} does not parse: a run it names may need its copy") from None
        if path.name == runs.ACTIVE:
            found |= {claim["worktree"] for claim in runs.live(entry).values()}
        elif entry.get("state") == runs.WAITING or entry.get("state") == runs.RUNNING and (
                entry.get("boot") != this_boot or size.entry_alive(entry)):
            found.add(entry.get("worktree"))
    return {str(pathlib.Path(worktree).resolve()) for worktree in found if worktree}


def working(folder):
    """{copy name: [pid]} of every process working in a copy under `folder`: its working folder in it (frozen.users),
    SCORE_FROZEN naming it, or its path on its command line; this process and its ancestors left out. Unprovable when
    a process of this user cannot be read."""
    folder, spare, found = pathlib.Path(folder), frozen.ancestors(), {}
    for pid, name in frozen.users(folder).items():
        found.setdefault(name, []).append(pid)
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) in spare:
            continue
        try:
            if entry.stat().st_uid != os.getuid():
                continue
            said = said_by(entry)
        except FileNotFoundError:
            continue  # it ended meanwhile
        for word in said.decode(errors="replace").split("\0"):
            name = copy_named(folder, word.partition("=")[2] if "=" in word and not word.startswith("/") else word)
            if name and int(entry.name) not in found.get(name, []):
                found.setdefault(name, []).append(int(entry.name))
    return found


def said_by(process):
    """A process's command line and environment as bytes; a non-dumpable one's (systemd --user, ssh-agent: closed
    even to its own user, and never a run) its command line alone. Unprovable when the command line cannot be read."""
    try:
        said = (process / "cmdline").read_bytes()
    except PermissionError as error:
        raise Unprovable(f"process {process.name} cannot be read ({error}): it may work in a copy") from None
    try:
        return said + b"\0" + (process / "environ").read_bytes()
    except PermissionError:
        return said


def copy_named(folder, word):
    """The name of the copy a path in `folder` lies in (its home's counting as the copy's), else None."""
    path = pathlib.Path(word)
    return path.relative_to(folder).parts[0].removesuffix(".home") \
        if path.is_absolute() and path.is_relative_to(folder) and path != folder else None


def copies(folder):
    """The names of the copies under `folder`, a lone home's too."""
    folder = pathlib.Path(folder)
    return sorted({entry.name.removesuffix(".home") for entry in folder.iterdir()}) if folder.is_dir() else []


def age(folder, name):
    """Seconds since the copy `name` or its home last changed."""
    times = [path.lstat().st_mtime for path in (folder / name, folder / f"{name}.home") if os.path.lexists(path)]
    return time.time() - max(times)


def kept(folder, name, need, busy):
    """Why the copy `name` must stay, or None when it is dead."""
    if str((folder / name).resolve()) in need:
        return "a registered run needs it"
    if busy.get(name):
        return f"processes work in it: {', '.join(map(str, busy[name]))}"
    if age(folder, name) < YOUNG_SECONDS:
        return f"made under {YOUNG_SECONDS // 60} minutes ago"
    return None


def remove_home(path):
    """Remove the closed home of the copy at `path` (frozen.remove closes it: it then holds links only); RuntimeError
    when it still holds something of its own."""
    own = frozen.home_of(path)
    if not own.is_dir():
        return
    left = [entry.name for entry in own.iterdir() if not entry.is_symlink()]
    if left:
        raise RuntimeError(f"{own} still holds {', '.join(left)}: left there")
    for entry in own.iterdir():
        entry.unlink()  # a link only: what it points at stays
    own.rmdir()


def clean(home=None, runs_folder=None, say=print):
    """Remove every dead copy under `home`/frozen (the module's docstring), each said in one line;
    {removed, kept, failed, freed_gb}. Unprovable, removing nothing, when it cannot tell."""
    home = pathlib.Path(home or PROPS_HOME)
    folder = (home / "frozen").resolve()  # the kernel names working folders resolved
    need, busy = needed(runs_folder or home / "runs"), working(folder)
    before, done = free_gb(home), {"removed": [], "kept": [], "failed": []}
    for name in copies(folder):
        why = kept(folder, name, need, busy)
        if why:
            done["kept"].append(name)
            say(f"kept {name}: {why}")
            continue
        try:
            frozen.remove(folder / name, home)
            remove_home(folder / name)
        except (OSError, RuntimeError) as error:
            done["failed"].append(name)
            say(f"failed {name}: {error}")
            continue
        done["removed"].append(name)
        say(f"removed {name}")
    done["freed_gb"] = round(free_gb(home) - before, 2)
    return done
