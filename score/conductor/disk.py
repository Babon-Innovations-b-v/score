"""The data disk under $PROPS_HOME: what fills it, the floor under which no run starts, and the sweep of frozen copies
no run needs any more (2026-10-26 23:45 UTC: 0.24 GB free of 91 GB, Batch 1 died with "No space left on device";
about twelve runs had started that day, and the copies of the ones stopped, failed or cut off stayed on the disk).

    python -m score.conductor disk           # one summary line, the biggest folders, the whole list in conductor/disk.json
    python -m score.conductor clean-frozen   # remove every frozen copy no run needs; what it freed, one line a copy
    python -m score.conductor clean-cache [--making-only]   # checkouts relinked; with no run live, the cache cleared
    python -m score.conductor clean-kept     # with no run live, the kept jobs no current key asks for, one line
    python -m score.conductor relink-pixal   # work/pixal's files the store holds made links to its blobs, one line
    python -m score.conductor offload-pixal  # with no run live, work/pixal's takes into the library, freed once read back
    python -m score.conductor store-gc [--dry]  # with no run live, the store's blobs nothing names removed
    python -m score.conductor store-evict [--dry]  # with no run live, blobs into the store bucket, proven ones evicted
    python -m score.conductor sweep [--force]   # the routine (every sync pass); every step under WARN_GB on a conductor

launch_refusal() is `score run`'s check before it makes its copy: a run is refused while store-evict runs (its lock
held) and while the disk has under FLOOR_GB free. health.read() carries FLOOR_GB and warning() (a note on the Machine card). When free is short it counts the
GB store-evict could free (evictable_gb) and names them: when that is enough, it says to run store-evict first.

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

clean-cache (2026-10-27: 0.2 GB free, store/cache 37.5 GB) removes the store cache's folders that are made again for
free (CLEARED, each with why) and keeps the rest (KEPT: paid drops, the convex parts a paid drop's key reads; the
review areas' yes tickets, logs and locks and any folder it does not know). It runs only with no run live: none
`needed`, no process working in a frozen copy or in a folder it would clear, nothing in making/ touched for
YOUNG_SECONDS; otherwise it refuses with the reason and removes nothing. work/pixal is never touched: it holds the paid
Pixal3D takes (raw model, close-up and camera, finished model) that the pixal row's gate counts and the surface line
reads as declared inputs, kept nowhere else, so a removed take is bought again. The sync pass runs it --making-only.
Before any of that, and with a run live too, it makes every checkout's copies of stored blobs hard links to them
(Store.relink, 2026-10-27: checkouts grew 16 GB in an hour while a run walked its rows): the same bytes under the same
names, so no reader can tell; a checkout is never removed while a run is live, since a node holds its input paths
across a cloud wait with no file open, and one removed under it would fail it.

clean-kept (2026-10-29), only with no run live (cache_refusal), drops each kept job and per-take call
(tools/cloud/kept.py: they outlive the outputs they were made for, so a re-keyed row makes only what changed) that no
current key could ask for: its node gone from the table, or that node's row code (Runner.making_code) moved, its
system (this Python's, blender_cloud.system) not a current one, or one of its inputs no longer current (a checkout of
an output its node no longer reads, a file with other bytes). A node whose key cannot be worked out now keeps its
entries. A dropped entry's blobs go only when no stored output and no other entry holds them. Never by age. The sync
pass runs it.

relink-pixal (2026-10-28: 16 GB free of 91, work/pixal 20.5 GB) does the same for work/pixal, with a run live too:
each regular file there whose bytes the store holds as a blob (the store's own sha256, sizes equal) is replaced by a
hard link to that read-only blob, renamed over it so no reader sees it missing. A file changed in the last
YOUNG_SECONDS (a take a run may still be writing or turning) or changed while it was hashed is kept, as is every
file the store does not hold: nothing is removed, so a take kept nowhere else stays whole.

offload-pixal, only with no run live (cache_refusal), commits each whole take of work/pixal (its raw and final models,
untouched for YOUNG_SECONDS, not every file a store link already) to the library as a `take` entry through score-lib
take-in --save (tools/library/pixal_takes.py), and removes a take's files here only once its entry is in the library's
pushed history and the blob store hands every file back at its size and sha256. Every reader of work/pixal puts a
missing take back from the library first (pixal_takes.take_back, wired in score/stages/__init__.py).

`disk` accounts for the whole data disk too (2026-10-30: 0.01 GB free of 91, about 25 GB not in PROPS_HOME's
folders): from its mount point three levels down when the home is not its top, the files deleted but still held open
by a process (/proc/<pid>/fd), the blocks kept for root and what du cannot read or see.

store-gc (2026-10-30), only with no run live (cache_refusal), removes each blob that nothing names: no file or link
under the home (records, listings, accepts, concepts, kept jobs, the design, the cockpit's links; the prop
environment, git and venv folders and the checkouts, links to blobs read through their listings, left out) or in the
checkout's data/, and no text-like blob so named (a listing kept as a blob), followed to its end; a blob linked
elsewhere too (frees nothing) or written in the last day is kept. collectable_why is the one guard every removal
passes. It refuses, removing nothing, when a file cannot be read.

sweep (2026-10-30, the owner: "this should be routine") runs on its own timer (score-sweep.timer) and as the sync
pass's first step, one at a time (alone): every pass the routine
(clean-frozen, clean-cache's making/, clean-kept); on a conductor under WARN_GB, before the floor, every step in
order: clean-cache whole, relink-pixal, run logs past LOG_DAYS and tmp/ past SCRATCH_DAYS, store-gc,
offload-pixal last (its read-back needs the room the others freed). Each step's line says what it freed; one refused or failed is
said and the next runs. Still under FLOOR_GB, it names what fills the disk and prices the bigger data volume
(Scaleway's catalog, machine.py's read): conductor/sweep.json, which the Machine card's note reads; only then is the
owner asked. Never the store's named blobs, the paid caches (cloud/google-cache, drops), the design or a take kept
nowhere else.

store-evict (#74, 2026-11-04: store/objects 138 GB, store-gc freed 0, Batch 1 died with ENOSPC), only with no run live
(cache_refusal, asked again before each BATCH of blobs: a run that became live stops it, the rest kept; with no run
live, no run has pinned an input) and one at a time (alone: `score run` refuses while it holds its lock), sends every local blob the store bucket does not list
into it (score/store/offload: a conditional put, a 412 meaning the same bytes are there) and removes the local copy
of a blob only once the bucket answers for it with its size and sha256 (offload.proven), and only a blob that has one
link (no checkout, kept mark or work/pixal link), is named by nothing under the home but the output listings (records,
concepts, kept jobs, the design and cockpit links keep theirs), is in no listing of an output a node stands on (each
node's current accept and its newest record's output: what the next run reads), and is no text naming other blobs
(store-gc follows those). Its mark (store/evicted/<sha>) is written first; the runner and the review fetch a marked
blob back on its first read. Never cloud/google-cache, never anything outside store/objects/blobs. Only its own
command and the door's verb run it, never the sweep: a first eviction sends about 138 GB, hours a pass would wait.
"""
import concurrent.futures
import contextlib
import datetime
import fcntl
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

from score import conductor
from score.conductor import size
from score.graph import frozen, runs
from score.store import PROPS_HOME, Store, file_hash, linked_read_only, offload, partial_of

FLOOR_GB = 10  # under this many GB free no run starts, and the Machine card warns
WRITTEN_MARGIN = 1.25  # the most a run was measured to take off the disk, a quarter more, is what a new one needs free
RAN_OUT_GB = 0.5  # a run whose lowest free fell under this ran the disk out: it needed more than it had
YOUNG_SECONDS = 15 * 60  # a copy younger than this may be one a run is still making
SHOWN = 20  # folders `disk` prints; the rest are in its file
DEEP = ("store/cache", "work/pixal")  # measured three levels down: what fills them (2026-10-27: 37.5 and 20.5 GB)
# The store cache's folders made again for free, and why; `tmp*` is a gate's scratch (settling's TemporaryDirectory).
CLEARED = {"making": "makes in progress, orphaned once no run lives (a make removes its own as it ends)",
           "checkouts": "read-only copies of stored outputs, made again from store/objects on the next read",
           "evidence": "copies of evidence kept in store/objects, fetched again on the next read",
           "pages": "review pages, written again each time one is opened",
           "tmp*": "a gate's scratch, removed by the gate as it ends"}
KEPT = {"drops": "paid drops read back so a drop is never bought twice",
        "convex-parts": "CoACD's parts are seeded, but a paid drop's key hashes them: a recompute not byte-equal buys "
                        "the drop again"}
REPO = pathlib.Path(__file__).resolve().parents[2]  # the checkout: its data named blobs, the tools it runs
EVICT_LOCK = "store-evict"  # alone's lock name: one store-evict at a time, and no run starts while it is held
BATCH = 256  # store-evict asks cache_refusal again before each this many blobs


class Unprovable(Exception):
    """clean-frozen cannot tell which copies are dead: it removes none."""


def free_gb(path=None):
    """The free GB on the disk holding `path` (PROPS_HOME), read at its nearest existing folder."""
    path = pathlib.Path(path or PROPS_HOME)
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free / 1024 ** 3


def warning(free, floor=None, swept=None):
    """The Machine card's note while the data disk has under `floor` (FLOOR_GB) GB free, else None: what the last
    sweep (conductor/sweep.json) freed and, when it could not reach the floor, what fills the disk and the bigger
    data volume it needs, priced: only then is it the owner's."""
    floor = FLOOR_GB if floor is None else floor
    if free >= floor:
        return None
    path = pathlib.Path(swept or conductor.HOME / "sweep.json")
    last = json.loads(path.read_text()) if path.is_file() else None
    said = f"disk: {free:.1f} GB free, under the {floor} GB floor: no run starts; "
    if not last or last.get("free_after_gb", 0) >= floor:
        return said + "the routine sweep (every sync pass; the door's sweep) frees room"
    return said + (f"the sweep at {last['at']} freed {last['freed_gb']} GB and could not reach it; it is filled by "
                   f"{last['fills']}; it needs a bigger data volume: {last['bigger']}")


def written_most(runs_folder=None):
    """The most GB one registered run took off the disk (its entry's `disk_start` less `disk_lowest`, graph/runs.noted),
    times WRITTEN_MARGIN; a run that ran the disk out (under RAN_OUT_GB left) counts as all it had and FLOOR_GB more."""
    most = 0.0
    for entry in pathlib.Path(runs_folder or PROPS_HOME / "runs").glob("*.json"):
        with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
            found = json.loads(entry.read_text())
            start, lowest = float(found["disk_start"]), float(found["disk_lowest"])
            most = max(most, start + FLOOR_GB if lowest < RAN_OUT_GB else start - lowest)
    return most * WRITTEN_MARGIN


def evicting(home):
    """True while a store-evict process holds home/conductor/store-evict.lock (alone's)."""
    path = pathlib.Path(home) / "conductor" / f"{EVICT_LOCK}.lock"
    if not path.is_file():
        return False
    with open(path) as held:
        try:
            fcntl.flock(held, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(held, fcntl.LOCK_UN)
    return False


def launch_refusal(path=None, floor=None, runs_folder=None):
    """Why `score run` must not start now, or None: while store-evict runs (it evicts blobs a run would read), or under
    `floor` GB free on PROPS_HOME's disk, FLOOR_GB or the most a run was measured to write (written_most), whichever is
    more; the GB store-evict could free named beside it."""
    if evicting(path or PROPS_HOME):
        return "refused: store-evict is running (it evicts blobs a run may read); start again once it has ended"
    floor = max(FLOOR_GB, round(written_most(runs_folder), 1)) if floor is None else floor
    free = free_gb(path)
    if free >= floor:
        return None
    said = (f"refused: {free:.1f} GB free on the data disk ({path or PROPS_HOME}), under the {floor} GB floor a run "
            "needs; free room first (the door's disk and sweep)")
    try:
        evictable = evictable_gb(pathlib.Path(path or PROPS_HOME))
    except (Unprovable, OSError) as why:
        return f"{said}; what store-evict could free is unread ({why})"
    if evictable < 0.05:
        return said
    if free + evictable >= floor:
        return (f"{said}; store-evict frees up to {evictable:.1f} GB of blobs the store bucket takes, enough: run the "
                "door's store-evict first, then start again")
    return f"{said}; store-evict frees up to {evictable:.1f} GB, not enough alone"


# --- disk: what fills it ---------------------------------------------------------------------------------------------

def du(root, depth, unread=None):
    """[(bytes, path)] of `root` and its folders down to `depth`, on its own filesystem (`du -x`), links not followed;
    each folder du could not read appended to `unread` when given."""
    done = subprocess.run(["du", "-x", "-B1", f"--max-depth={depth}", str(root)], capture_output=True, text=True)
    found = []
    for line in done.stdout.splitlines():
        count, _, path = line.partition("\t")
        found.append((int(count), path))
    if unread is not None:
        unread += [line for line in done.stderr.splitlines() if line.strip()]
    return found


def mount_of(path):
    """The mount point of the filesystem holding `path`: the data disk's top folder (PROPS_HOME on the conductor)."""
    path = pathlib.Path(path).resolve()
    while path != path.parent and path.parent.stat().st_dev == path.stat().st_dev:
        path = path.parent
    return path


def roots(home=None):
    """{root: depth} measured: the home two levels down (frozen/<copy>, store/objects, store/cache, ...), DEEP three
    levels down, and the whole disk from its mount point three levels down when the home is not its top (it then
    holds the checkout and the user's cache when they are on it)."""
    home = pathlib.Path(home or PROPS_HOME)
    mount = mount_of(home)
    return {home: 2, **{home / deep: 3 for deep in DEEP if (home / deep).is_dir()},
            **({mount: 3} if mount != home.resolve() else {})}


def deleted_open(device):
    """{process: bytes} of the files on `device` that are deleted but still held open (their room comes back only when
    the process closes them or ends); another user's processes cannot be read and are left out."""
    held, seen = {}, set()
    for handle in pathlib.Path("/proc").glob("[0-9]*/fd/*"):
        try:
            if not os.readlink(handle).endswith(" (deleted)"):
                continue
            status = handle.stat()
            name = (handle.parent.parent / "comm").read_text().strip()
        except OSError:
            continue  # closed meanwhile, or not ours to read
        if status.st_dev != device or status.st_nlink or (status.st_ino in seen):
            continue
        seen.add(status.st_ino)
        process = f"{name} (pid {handle.parent.parent.name})"
        held[process] = held.get(process, 0) + status.st_blocks * 512
    return held


def accounted(home, sizes, unread):
    """The whole data disk accounted for: {mount, used_gb, folders_gb (what du sees from the mount point),
    outside_gb (of that, outside the home), deleted_open {process: gb}, reserved_gb (kept for root), unseen_gb (what
    du could not read or see: unreadable folders, the filesystem's own), unread (du's errors)}."""
    home = pathlib.Path(home)
    mount = mount_of(home)
    status = os.statvfs(mount)
    used = (status.f_blocks - status.f_bfree) * status.f_frsize
    seen = max((count for count, path in sizes if pathlib.Path(path) == mount), default=0)
    inside = max((count for count, path in sizes if pathlib.Path(path) == home), default=0)
    held = deleted_open(home.stat().st_dev)
    gb = 1024 ** 3
    return {"mount": str(mount), "used_gb": round(used / gb, 2), "folders_gb": round(seen / gb, 2),
            "outside_gb": round((seen - inside) / gb, 2) if mount != home.resolve() else 0.0,
            "deleted_open": {process: round(count / gb, 3) for process, count in
                             sorted(held.items(), key=lambda pair: -pair[1])},
            "reserved_gb": round((status.f_bfree - status.f_bavail) * status.f_frsize / gb, 2),
            "unseen_gb": round(max(used - seen - sum(held.values()), 0) / gb, 2), "unread": unread}


def report(home=None, out=None):
    """Measure the disk (roots) and account for all of it (accounted), write every folder's size and the account to
    `out` (conductor/disk.json), biggest first; (summary line, the SHOWN biggest lines)."""
    home = pathlib.Path(home or PROPS_HOME)
    unread, largest = [], {}
    for root, depth in roots(home).items():
        for count, path in du(root, depth, unread):
            largest[path] = max(count, largest.get(path, 0))  # hard links count where du met them first
    sizes = sorted(((count, path) for path, count in largest.items()), reverse=True)
    whole = accounted(home, sizes, unread)
    usage = shutil.disk_usage(home)
    out = pathlib.Path(out or conductor.HOME / "disk.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                               "free_gb": round(usage.free / 1024 ** 3, 2), "total_gb": round(usage.total / 1024 ** 3, 2),
                               "whole": whole, "folders": [{"path": path, "gb": round(count / 1024 ** 3, 3)}
                                                           for count, path in sizes]}, indent=1))
    copies = [count for count, path in sizes if pathlib.Path(path).parent == home / "frozen"]
    held = sum(whole["deleted_open"].values())
    summary = (f"disk: {usage.free / 1024 ** 3:.1f} GB free of {usage.total / 1024 ** 3:.0f} GB; "
               f"{len(copies)} frozen copies and homes hold {sum(copies) / 1024 ** 3:.1f} GB; the whole disk at "
               f"{whole['mount']}: {whole['used_gb']} GB used, {whole['folders_gb']} GB in folders "
               f"({whole['outside_gb']} GB outside {home}), {held:.2f} GB in deleted files still open, "
               f"{whole['reserved_gb']} GB kept for root, {whole['unseen_gb']} GB du cannot see "
               f"({len(unread)} folders unreadable); every folder in {out}")
    within = [(count, path) for count, path in sizes if any(
        pathlib.Path(path).is_relative_to(home / deep) and pathlib.Path(path) != home / deep for deep in DEEP)]
    outside = [(count, path) for count, path in sizes if not pathlib.Path(path).is_relative_to(home)
               and not home.is_relative_to(path)]
    return summary, [f"{count / 1024 ** 3:8.2f} GB  {path}" for count, path in sizes[:SHOWN]] + \
        [f"inside {' and '.join(DEEP)}, three levels down:"] + \
        [f"{count / 1024 ** 3:8.2f} GB  {path}" for count, path in within[:SHOWN]] + \
        [f"outside {home} on the same disk, three levels down from {whole['mount']}:"] + \
        [f"{count / 1024 ** 3:8.2f} GB  {path}" for count, path in outside[:SHOWN]] + \
        [f"{gb:8.2f} GB  deleted, still open in {process}" for process, gb in
         list(whole["deleted_open"].items())[:SHOWN]] + [f"unreadable: {line}" for line in unread[:5]]


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
    except ProcessLookupError:  # it ended between the listing and the read: as its folder gone (callers skip it)
        raise FileNotFoundError(f"process {process.name} ended") from None
    try:
        return said + b"\0" + (process / "environ").read_bytes()
    except PermissionError:
        return said
    except ProcessLookupError:
        raise FileNotFoundError(f"process {process.name} ended") from None


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


# --- clean-cache: the store cache's folders made again for free -----------------------------------------------------

def newest(folder):
    """Seconds since anything under `folder` last changed (itself included); None when it is not there."""
    folder = pathlib.Path(folder)
    if not folder.is_dir():
        return None
    return time.time() - max([folder.lstat().st_mtime, *(path.lstat().st_mtime for path in folder.rglob("*"))])


def cleared(cache, names):
    """[(path, why)] of the cache's top folders matching one of `names` (CLEARED's keys)."""
    return [(path, CLEARED[name]) for name in names for path in sorted(pathlib.Path(cache).glob(name))
            if path.is_dir() and not path.is_symlink()]


def cache_refusal(home, runs_folder, cache, targets):
    """Why the cache may not be cleared now (a run may be live, a make in progress), or None; Unprovable when a run
    entry, the claims file or a process cannot be read."""
    need = needed(runs_folder)
    if need:
        return f"a registered run needs {', '.join(sorted(need))}"
    busy = working((home / "frozen").resolve())
    if busy:
        return f"processes work in frozen copies: {busy}"
    names = {path.name for path, _ in targets}
    busy = {name: pids for name, pids in working(cache.resolve()).items() if name in names}
    if busy:
        return f"processes work in the cache: {busy}"
    touched = newest(cache / "making")
    if touched is not None and touched < YOUNG_SECONDS:
        return f"{cache / 'making'} changed {touched / 60:.0f} minutes ago: a make may be in progress"
    return None


@contextlib.contextmanager
def alone(home, name):
    """True while this process holds home/conductor/<name>.lock, False when another does: one sweep and one
    offload-pixal at a time (2026-10-31: the door's offload-pixal beside the sync pass's sweep removed a take's files
    under the other's stat, FileNotFoundError, and the sweep timer's runs overlap a pass's)."""
    path = pathlib.Path(home) / "conductor" / f"{name}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as held:
        try:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        yield True


def remove_tree(path):
    """Remove a folder whatever its folders' modes (a make may copy a read-only one); links are not followed."""
    for folder in [path, *path.rglob("*")]:
        if folder.is_dir() and not folder.is_symlink():
            folder.chmod(0o755)
    shutil.rmtree(path)


def clean_cache(home=None, runs_folder=None, names=tuple(CLEARED), say=print):
    """With no run live (cache_refusal), remove the store cache's folders in `names` (CLEARED's), each said with why,
    and say each one kept (KEPT's, or not known); {removed, refused, freed_gb}. Unprovable when it cannot tell."""
    home = pathlib.Path(home or PROPS_HOME)
    cache = home / "store" / "cache"
    relinked = relink_checkouts(home, say) if "checkouts" in names else 0.0
    targets = cleared(cache, names)
    refused = cache_refusal(home, pathlib.Path(runs_folder or home / "runs"), cache, targets)
    if refused:
        return {"removed": [], "refused": refused, "freed_gb": 0.0, "relinked_gb": relinked}
    before, removed = free_gb(home), []
    for path, why in targets:
        remove_tree(path)
        removed.append(path.name)
        say(f"removed {path}: {why}")
    known = {path.name for path, _ in cleared(cache, CLEARED)}
    for path in sorted(cache.iterdir()) if cache.is_dir() else []:
        if path.name not in known:
            say(f"kept {path}: {KEPT.get(path.name, 'not known to be made again for free')}")
    return {"removed": removed, "refused": None, "freed_gb": round(free_gb(home) - before, 2), "relinked_gb": relinked}


def relink_checkouts(home, say=print):
    """Every checkout's whole copies of stored blobs made hard links to them (Store.relink: safe while runs read
    them, so it runs even with a run live); the GB freed, said in one line."""
    store = Store.in_folder(pathlib.Path(home) / "store")
    folder = store.cache / "checkouts"
    outputs = [path.name for path in sorted(folder.iterdir()) if path.is_dir() and not path.name.endswith(".partial")
               ] if folder.is_dir() else []
    freed = round(sum(store.relink(output) for output in outputs if store.objects.exists(f"outputs/{output}.json"))
                  / 1024 ** 3, 2)
    say(f"relinked {len(outputs)} checkouts to the stored blobs: {freed} GB of copies freed")
    return freed


# A people look's take files (people_bodies/bodies.laid_take copies them from the store into work/pixal over what is
# there): kept plain copies, never links. 2026-11-03: linked to the very blob the store's checkout links, the copy was
# a file onto itself (SameFileError) and three looks' lines stopped in Batch 1's try.
LAID = re.compile(r"^[A-Za-z0-9_]+-made-s\d+")


def laid_by_a_row(path, pixal):
    """Whether the work/pixal file at `path` is one a row writes again in place: a people look's take file, which a
    row copies over (LAID), or a code build's (code_built)."""
    return bool(LAID.match(path.relative_to(pixal).parts[0])) or code_built(path, pixal)


# A code build's take files (score/stages/props/thin_straight.py `rebuilt`: every run of the Pixal3D row makes each
# build again from its own crop, writing its input.png, raw, slimmed and final models and code.json in place): kept
# plain copies, never links. 2026-11-05: linked to their read-only blobs, every place's pixal row stopped on
# input.png, Permission denied, in Batch 1's try.
CODE_MARK = "code.json"  # thin_straight.MARK, spelled here so no stage module is imported
TAKE_FILE = re.compile(r"^(?P<take>.+?)(?:-final|-\d+)?\.glb$")


def code_built(path, pixal):
    """Whether the work/pixal file at `path` belongs to a take built in code: its take's .svviews holds CODE_MARK."""
    top = path.relative_to(pixal).parts[0]
    if top.endswith(".svviews"):
        take = top[:-len(".svviews")]
    else:
        named = TAKE_FILE.match(top)
        if named is None:
            return False
        take = named["take"]
    return (pixal / f"{take}.svviews" / CODE_MARK).is_file()


def relink_pixal(home=None, now=None):
    """Every work/pixal file whose bytes the store holds as a blob, untouched for YOUNG_SECONDS, made a hard link to
    that blob, but a people look's take file (laid_by_a_row), which is kept a plain copy and made one again if it
    was linked before; {relinked, freed_gb, kept: {why: files}, copied}."""
    home = pathlib.Path(home or PROPS_HOME)
    blobs = Store.in_folder(home / "store").objects.path("blobs")
    now = time.time() if now is None else now
    relinked, freed, kept, copied = 0, 0, {}, 0
    pixal = home / "work" / "pixal"
    for path in sorted(pixal.rglob("*")):
        if path.is_dir() and not path.is_symlink():
            continue
        if laid_by_a_row(path, pixal):
            copied += plain_again(path)
            kept["a people look's take, copied over by its row"] = kept.get(
                "a people look's take, copied over by its row", 0) + 1
            continue
        size = path.lstat().st_size
        why = relinked_or_why(path, blobs, now)
        if why:
            kept[why] = kept.get(why, 0) + 1
        else:
            relinked, freed = relinked + 1, freed + size
    return {"relinked": relinked, "freed_gb": round(freed / 1024 ** 3, 2), "kept": kept, "copied": copied}


def laid_plain(home=None):
    """Every people look's take file in work/pixal (laid_by_a_row) made a plain copy again where it is a link; {copied}.
    The sweep's every pass runs it, so a take linked before the rule is put right without a low disk."""
    home = pathlib.Path(home or PROPS_HOME)
    pixal = home / "work" / "pixal"
    files = [path for path in sorted(pixal.rglob("*")) if path.is_file() and laid_by_a_row(path, pixal)] \
        if pixal.is_dir() else []
    return {"copied": sum(plain_again(path) for path in files)}


def plain_again(path):
    """The file at `path` made a plain, writable copy of itself when it shares its bytes with another link (a blob);
    1 when it did, else 0. The copy is written beside it and renamed over it, so nothing is lost on the way."""
    if path.is_symlink() or not path.is_file() or path.stat().st_nlink < 2:
        return 0
    spare = partial_of(path)
    shutil.copyfile(path, spare)
    os.chmod(spare, 0o644)
    spare.replace(path)
    return 1


def relinked_or_why(path, blobs, now):
    """The work/pixal file at `path` made a hard link to the stored blob of its bytes (made beside it, renamed over
    it: linked_read_only), None; else why it is kept as it is."""
    if path.is_symlink() or not path.is_file() or path.name.endswith(".partial"):
        return "not a regular file"
    status = path.stat()
    if now - status.st_mtime < YOUNG_SECONDS:
        return "changed in the last 15 minutes"
    blob = blobs / file_hash(path)
    if not blob.is_file():
        return "not held in the store"
    if path.samefile(blob):
        return "already a link to its blob"
    after = path.stat()
    if (after.st_mtime_ns, after.st_size) != (status.st_mtime_ns, status.st_size) or blob.stat().st_size != after.st_size:
        return "changed while it was hashed"
    spare = partial_of(path)
    if not linked_read_only(blob, spare):
        return "its blob cannot be linked (writable, another disk or at the link limit)"
    spare.replace(path)
    return None



# --- offload-pixal: the takes the library holds, freed here ----------------------------------------------------------

def pixal_takes():
    """tools/library/pixal_takes.py, imported off the path again (a tool folder left on it moves code versions)."""
    import sys
    kept = list(sys.path)
    sys.path.insert(0, str(REPO / "tools" / "library"))
    try:
        import pixal_takes as module
    finally:
        sys.path[:] = kept
    return module


def offload_pixal(home=None, runs_folder=None, now=None, commit=None):
    """With no run live (cache_refusal), every work/pixal take committed to the library (pixal_takes.taken_in) and,
    once the library's pushed entry hands every file back at its size and hash (read_back), its files removed here:
    a reader gets them back from the library (pixal_takes.take_back). {freed, freed_gb, refused, kept: {why: takes}}."""
    home = pathlib.Path(home or PROPS_HOME)
    with alone(home, "offload-pixal") as first:
        if not first:
            return {"freed": 0, "freed_gb": 0.0, "refused": "another offload-pixal is running", "kept": {}}
        return offloaded(home, runs_folder, now, commit)


def offloaded(home, runs_folder, now, commit):
    """offload_pixal's work, its one process holding the lock."""
    folder, takes = home / "work" / "pixal", pixal_takes()
    refused = cache_refusal(home, pathlib.Path(runs_folder or home / "runs"), home / "store" / "cache", [])
    if refused:
        return {"freed": 0, "freed_gb": 0.0, "refused": refused, "kept": {}}
    now = time.time() if now is None else now
    kept, ready = {}, []
    for take in painted_takes(home):
        why = take_kept_why(takes, take, folder, now)
        if why:
            kept.setdefault(why, []).append(take)
        else:
            ready.append(take)
    report = takes.taken_in(ready, folder, commit or repo_commit(), home / "tmp" / "offload-pixal") if ready else {}
    for row in report.get("refused", []):
        kept.setdefault(f"refused by the library: {row['why']}", []).append(row["id"].split("/", 1)[-1])
    written = {address for status in ("new", "changed draft", "new version") for address in report.get(status, [])}
    freed, count = 0, 0
    for take in ready:
        why = held_whole_why(takes, take, folder, home, report, written)
        if why:
            kept.setdefault(why, []).append(take)
            continue
        freed, count = freed + removed_take(takes, take, folder), count + 1
    return {"freed": count, "freed_gb": round(freed / 1024 ** 3, 2), "refused": None, "kept": kept}


def painted_takes(home):
    """Every take a place's surface data paints (its design's, else the repository's): the takes the stage table puts
    back before a row reads them (score/stages/__init__.py takes_back), so only those may leave work/pixal."""
    files = {}
    for folder in (REPO / "data" / "surfaces", pathlib.Path(home) / "design" / "surfaces"):  # the design's last: it wins
        files.update({path.stem: path for path in folder.glob("*.json")} if folder.is_dir() else {})
    return sorted({take for path in files.values() for take in json.loads(path.read_text()).get("takes", {})})


def take_kept_why(takes, take, folder, now):
    """Why the take stays as it is, unoffered to the library, or None."""
    if takes.take_id(take) is None:
        return "its name makes no library id"
    names = takes.take_names(take, folder)
    if not all(f"{take}{suffix}" in names for suffix in (".glb", "-final.glb")):
        return "not whole (no raw or final model)"
    gone = [name for name in names if not (folder / name).exists()]
    if gone:
        return f"a file is gone or a link to nothing: {', '.join(gone)}"
    statuses = [(folder / name).stat() for name in names]
    if any(now - status.st_mtime < YOUNG_SECONDS for status in statuses):
        return "changed in the last 15 minutes"
    if all(status.st_nlink > 1 for status in statuses):
        return "every file a link to the store already"
    record = takes.newest_record(take)
    entry = takes.library_files.settings().get("SCORE_LIB_ROOT")
    other = pathlib.Path(entry or ".") / "entries" / takes.KIND / takes.take_id(take)
    if record is None and other.is_dir():
        return "its library id is another take's"
    return None


def held_whole_why(takes, take, folder, home, report, written):
    """Why the take may not be freed yet (its entry not pushed, or not handed back whole), or None."""
    record = takes.newest_record(take)
    if record is None:
        return "not taken in"
    if record["address"] in written and not (report.get("saved") or {}).get("pushed"):
        return f"not pushed: {(report.get('saved') or {}).get('why', 'nothing saved')}"
    if not takes.upstream_holds(take):
        return "its entry is not in the library's pushed history"
    scratch = home / "tmp" / "offload-pixal"
    scratch.mkdir(parents=True, exist_ok=True)
    why = takes.read_back(take, folder, scratch)
    return f"read back: {why}" if why else None


def removed_take(takes, take, folder):
    """The take's files removed from `folder` (its emptied camera folders too); the bytes freed (a file another link
    still holds frees none)."""
    freed = 0
    for name in takes.take_names(take, folder):
        status = (folder / name).stat()
        freed += status.st_size if status.st_nlink == 1 else 0
        (folder / name).unlink()
    for camera in takes.CAMERAS:
        path = folder / f"{take}{camera}"
        for inner in sorted(path.rglob("*"), reverse=True) if path.is_dir() else []:
            inner.rmdir()
        if path.is_dir():
            path.rmdir()
    return freed


def repo_commit():
    """The checkout's commit, the one the take-in names."""
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


# --- clean-kept: the kept jobs no current key asks for ----------------------------------------------------------------

CHECKOUTS = "/store/cache/checkouts/"


def blender_system():
    """blender_cloud.system() worked out in a process of its own: tools/cloud on this process's import path would give
    a same-named module to the rows whose keys the sweep works out (graph/_code.py search_folders)."""
    done = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tools/cloud'); import blender_cloud; "
                           "print(blender_cloud.system(), end='')"], cwd=REPO, capture_output=True, text=True,
                          check=True)
    return done.stdout


def input_stands(path, sha, held, home, kept):
    """Whether a kept entry's input (its stand-in path and hash) is still the current one: a checkout of an output its
    node reads now, or a file there with the same bytes; one made inside the attempt's folder is the row's code's."""
    if path.startswith("{making}") or sha == "missing":
        return True
    real = path.replace("{home}", str(home)).replace("{repo}", str(REPO))
    if CHECKOUTS in real:
        return real.split(CHECKOUTS, 1)[1].split("/", 1)[0] in held
    found = pathlib.Path(real)
    return found.is_file() and kept.file_hash(found, kept.stand_ins()) == sha


def asked_by(runner, systems, home, kept):
    """entry -> whether a current key could still ask for it: its node in the table, that node's row code now its
    own, its system a current one and each of its inputs current (input_stands). A node whose key cannot be worked out
    now (Blocked) keeps its entries: it may ask once it stands."""
    from score import graph

    def asked(entry):
        node = entry["code"].split(" ", 1)[0]
        name, _, place = node.partition("@")
        stage = runner.stages.get(name)
        if stage is None:
            return False
        try:
            keyed = runner.key(stage, place or None)
            code = runner.making_code(stage, place or None, keyed)
        except graph.Blocked:
            return True
        held = {*keyed["after"].values(), *keyed.get("beside", {}).values()}
        return code == entry["code"] and entry["system"] in systems and \
            all(input_stands(path, sha, held, home, kept) for path, sha in entry["inputs"])
    return asked


def clean_kept(home=None, runs_folder=None, runner=None, systems=None, say=print):
    """With no run live (cache_refusal), every kept job and per-take call no current key asks for dropped (kept.sweep,
    asked_by), with the blobs only it held; {dropped, refused, freed_gb}. Never by age."""
    home = pathlib.Path(home or PROPS_HOME)
    refused = cache_refusal(home, pathlib.Path(runs_folder or home / "runs"), home / "store" / "cache", [])
    if refused:
        return {"dropped": 0, "refused": refused, "freed_gb": 0.0}
    from score import stages
    kept = stages.kept_module()
    runner = runner or stages.runner(Store.in_folder(home / "store"))
    systems = systems or {kept.digest(kept.python_system()), kept.digest(blender_system())}
    return {**kept.sweep(asked_by(runner, systems, home, kept), say), "refused": None}


# --- store-gc: the blobs nothing names -------------------------------------------------------------------------------

SHA = re.compile(rb"[0-9a-f]{64}")
SCAN_SKIPPED = {".git", ".venv", "node_modules", "__pycache__"}
CHUNK = 8 * 1024 ** 2
GC_YOUNG_SECONDS = 24 * 3600  # a blob this new may be one a write in progress (a put_tree, a concept) names next


def shas_in(path):
    """Every 64-hex word in the file at `path` (read in chunks, a word across two chunks too)."""
    found, tail = set(), b""
    with open(path, "rb") as source:
        while chunk := source.read(CHUNK):
            found |= {word.decode() for word in SHA.findall(tail + chunk)}
            tail = chunk[-63:]
    return found


def text_like(path):
    """Whether the file's first 8 KB hold no NUL byte: a listing, a record, a page, never a model or a picture."""
    with open(path, "rb") as source:
        return b"\0" not in source.read(8192)


def named_outside(home, repo, blobs, also=()):
    """Every 64-hex word any file or link under `home` and the checkout's data names, the blobs themselves, the prop
    environment, checkouts (links to blobs, read through their listings), git and venv folders and the folders `also`
    names left out."""
    found = set()
    skipped = {blobs.resolve(), (home / "env").resolve(), (home / "store/cache/checkouts").resolve(),
               *(pathlib.Path(folder).resolve() for folder in also)}
    for root in (home, repo / "data"):
        for folder, folders, files in os.walk(root):
            folders[:] = [name for name in folders if name not in SCAN_SKIPPED
                          and (pathlib.Path(folder) / name).resolve() not in skipped]
            for name in files + [name for name in folders if (pathlib.Path(folder) / name).is_symlink()]:
                path = pathlib.Path(folder) / name
                try:
                    if path.is_symlink():
                        found |= {word.decode() for word in SHA.findall(os.fsencode(os.readlink(path)))}
                    elif path.is_file():  # never a socket or a pipe: reading one would wait
                        found |= shas_in(path)
                except OSError as error:
                    raise Unprovable(f"{path} cannot be read ({error}): it may name a blob") from None
    return found


def referenced(home, repo=None):
    """Every blob a file, a link or a referenced text-like blob names (a listing kept as a blob), followed until no new
    one: the blobs store-gc must keep."""
    home, repo = pathlib.Path(home), pathlib.Path(repo or REPO)
    blobs = home / "store" / "objects" / "blobs"
    held = named_outside(home, repo, blobs)
    todo = held
    while todo:
        named = set()
        for sha in todo:
            path = blobs / sha
            if path.is_file() and text_like(path):
                named |= shas_in(path)
        todo, held = named - held, held | named
    return held


def collectable_why(blob, held, now):
    """Why the blob at `blob` stays, or None when store-gc may remove it. The one guard every removal passes."""
    if not SHA.fullmatch(blob.name.encode()):
        return "not a blob's name"
    if blob.name in held:
        return "named by a file, a link or a listing"
    status = blob.stat()
    if status.st_nlink > 1:
        return "linked elsewhere too (a checkout, work/pixal): removing it frees nothing"
    if now - status.st_mtime < GC_YOUNG_SECONDS:
        return "written in the last day"
    return None


def store_gc(home=None, runs_folder=None, dry=False, now=None, repo=None, say=print):
    """With no run live (cache_refusal), every blob no file, link or listing names (referenced) removed, or with `dry`
    only counted; {removed, freed_gb, kept: {why: count}, refused, dry}. Unprovable when a file cannot be read."""
    home = pathlib.Path(home or PROPS_HOME)
    refused = cache_refusal(home, pathlib.Path(runs_folder or home / "runs"), home / "store" / "cache", [])
    if refused:
        return {"removed": 0, "freed_gb": 0.0, "kept": {}, "refused": refused, "dry": dry}
    blobs, now = home / "store" / "objects" / "blobs", time.time() if now is None else now
    held, removed, freed, kept = referenced(home, repo), 0, 0, {}
    for blob in sorted(blobs.iterdir()) if blobs.is_dir() else []:
        why = collectable_why(blob, held, now)
        if why:
            kept[why] = kept.get(why, 0) + 1
            continue
        size = blob.stat().st_size
        if not dry:
            blob.unlink()
        removed, freed = removed + 1, freed + size
    say(f"store-gc: {'would remove' if dry else 'removed'} {removed} blobs nothing names, {freed / 1024 ** 3:.2f} GB")
    return {"removed": removed, "freed_gb": round(freed / 1024 ** 3, 2), "kept": kept, "refused": None, "dry": dry}


# --- store-evict: blobs into the store bucket, the proven ones evicted ----------------------------------------------

UNPROVEN = "the bucket did not answer with its size and sha256"


def read_object(path):
    """One JSON object of the store; Unprovable when it cannot be read (it may name what must stay)."""
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise Unprovable(f"{path} cannot be read ({error}): it may name an output a node stands on") from None


def read_folder(folder):
    """Every JSON object in one folder of the store; [] when the folder is missing."""
    return [read_object(path) for path in sorted(folder.glob("*.json"))] if folder.is_dir() else []


def standing_outputs(objects):
    """Every output a node of the store stands on: its current accepted output, the newest that no later reject of
    the same output undid (as Store.current_accept), and its newest finish record's output."""
    outputs = set()
    for folder in sorted((objects / "accepts").iterdir()) if (objects / "accepts").is_dir() else []:
        undone = {item["output"]: item["at"]
                  for item in sorted(read_folder(objects / "rejects" / folder.name), key=lambda item: item["at"])}
        standing = [item for item in sorted(read_folder(folder), key=lambda item: item["at"])
                    if item["at"] > undone.get(item["output"], "")]
        outputs |= {standing[-1]["output"]} if standing else set()
    for folder in sorted((objects / "records").iterdir()) if (objects / "records").is_dir() else []:
        found = read_folder(folder)
        outputs |= {max(found, key=lambda record: record["finished"])["output"]} if found else set()
    return outputs


def evict_keep(home, repo):
    """Every blob store-evict keeps here: named by a file or link under the home other than an output listing (the
    records, concepts, kept jobs, design, cockpit links), in the listing of an output a node stands on, or named by a
    text-like blob so kept, followed to its end."""
    objects = home / "store" / "objects"
    held = named_outside(home, repo, objects / "blobs", also=(objects / "outputs",))
    for output in standing_outputs(objects):
        listing = objects / "outputs" / f"{output}.json"
        held |= set(read_object(listing).values()) if listing.is_file() else set()
    todo = held
    while todo:
        named = set()
        for sha in todo:
            path = objects / "blobs" / sha
            if path.is_file() and text_like(path):
                named |= shas_in(path)
        todo, held = named - held, held | named
    return held


def evict_why(blob, held):
    """Why the blob at `blob` stays local, or None when store-evict may evict it once the bucket proves it holds it."""
    if not SHA.fullmatch(blob.name.encode()):
        return "not a blob's name"
    if blob.name in held:
        return "named outside the listings, or read by an output a node stands on"
    if blob.stat().st_nlink > 1:
        return "linked (a checkout, a kept mark, work/pixal)"
    if text_like(blob) and shas_in(blob):
        return "a text naming blobs (store-gc follows it)"
    return None


def evict_candidates(home, repo=None):
    """([(sha, size)] of the blobs store-evict may evict, {why kept: count}); Unprovable when a file cannot be read."""
    home = pathlib.Path(home)
    blobs, held = home / "store" / "objects" / "blobs", evict_keep(home, pathlib.Path(repo or REPO))
    candidates, kept = [], {}
    for blob in sorted(blobs.iterdir()) if blobs.is_dir() else []:
        why = evict_why(blob, held)
        if why:
            kept[why] = kept.get(why, 0) + 1
        else:
            candidates.append((blob.name, blob.stat().st_size))
    return candidates, kept


def evictable_gb(home):
    """The GB store-evict could free in this home (its candidates); 0 with no blobs folder."""
    if not (pathlib.Path(home) / "store" / "objects" / "blobs").is_dir():
        return 0.0
    return sum(size for _, size in evict_candidates(home)[0]) / 1024 ** 3


def pushed_and_evicted(objects, bucket, listed, sha, size, evictable):
    """One blob: sent unless the bucket lists it, then, when `evictable`, evicted once the bucket proves it holds it;
    (how it went: sent, there, listed or unproven; whether it was evicted)."""
    went = "listed" if offload.blob_key(sha) in listed else offload.push(objects / "blobs" / sha, sha, bucket)
    if not evictable:
        return went, False
    if not offload.proven(bucket, sha, size):
        return "unproven", False
    offload.evict(objects, sha, size)
    return went, True


def store_evict(home=None, runs_folder=None, dry=False, repo=None, bucket=None, say=print):
    """One at a time (alone), store_evicted below; refused while another store-evict holds the lock."""
    home = pathlib.Path(home or PROPS_HOME)
    with alone(home, EVICT_LOCK) as first:
        if not first:
            return {"sent": 0, "there": 0, "evicted": 0, "freed_gb": 0.0, "kept": {}, "failed": {},
                    "refused": "another store-evict is running", "stopped": None, "dry": dry}
        return store_evicted(home, pathlib.Path(runs_folder or home / "runs"), dry, repo, bucket, say)


def store_evicted(home, runs_folder, dry, repo, bucket, say):
    """With no run live (cache_refusal, asked again before each BATCH: a run that became live stops it, `stopped`
    saying why), every local blob sent to the store bucket (the evictable first) and each evictable one
    (evict_candidates) evicted once the bucket proves it holds it; with `dry` the evictable counted only, nothing sent.
    {sent, there, evicted, freed_gb, kept, failed: {kind: count}, refused, stopped, dry}, and first_failure when a blob
    failed; Unprovable when a file cannot be read."""
    refused = cache_refusal(home, runs_folder, home / "store" / "cache", [])
    done = {"sent": 0, "there": 0, "evicted": 0, "freed_gb": 0.0, "kept": {}, "failed": {}, "refused": refused,
            "stopped": None, "dry": dry}
    if refused:
        return done
    candidates, done["kept"] = evict_candidates(home, repo)
    if dry:
        gb = sum(size for _, size in candidates) / 1024 ** 3
        say(f"store-evict: would evict {len(candidates)} blobs once the bucket holds them, {gb:.2f} GB")
        return {**done, "evicted": len(candidates), "freed_gb": round(gb, 2)}
    objects, bucket = home / "store" / "objects", bucket or offload.open_bucket()
    listed, chosen = bucket.listed(offload.BLOBS), {sha for sha, _ in candidates}
    rest = [(path.name, path.stat().st_size) for path in sorted((objects / "blobs").iterdir())
            if SHA.fullmatch(path.name.encode()) and path.name not in chosen]
    freed, todo = 0, [*candidates, *rest]
    with concurrent.futures.ThreadPoolExecutor(offload.WORKERS) as pool:
        for start in range(0, len(todo), BATCH):
            done["stopped"] = cache_refusal(home, runs_folder, home / "store" / "cache", [])
            if done["stopped"]:
                break
            work = {pool.submit(pushed_and_evicted, objects, bucket, listed, sha, size, sha in chosen): size
                    for sha, size in todo[start:start + BATCH]}
            for future in concurrent.futures.as_completed(work):
                try:
                    went, evicted = future.result()
                except Exception as error:  # one blob's fault keeps the rest going; counted and said, never hidden
                    kind = type(error).__name__
                    done["failed"][kind] = done["failed"].get(kind, 0) + 1
                    done.setdefault("first_failure", f"{kind}: {error}")
                    continue
                if went in ("sent", "there"):
                    done[went] += 1
                if went == "unproven":
                    done["kept"][UNPROVEN] = done["kept"].get(UNPROVEN, 0) + 1
                done["evicted"], freed = done["evicted"] + evicted, freed + work[future] * evicted
    done["freed_gb"] = round(freed / 1024 ** 3, 2)
    stopped = f"; stopped, the rest kept: {done['stopped']}" if done["stopped"] else ""
    say(f"store-evict: sent {done['sent']}, there {done['there']}, evicted {done['evicted']} blobs, "
        f"{done['freed_gb']} GB; failed {sum(done['failed'].values())}{stopped}")
    return done


# --- sweep: the routine that keeps the disk above its floor ----------------------------------------------------------

WARN_GB = 20  # under this the sweep goes past its routine steps, before the floor is reached
LOG_DAYS = 30  # run logs older than this go
SCRATCH_DAYS = 1  # the home's tmp/ entries untouched this long go, with no run live
MOTION_SCRATCH = "work/motion-scratch"  # score/stages/layer_base.py SCRATCH: a make's own copies, none kept after it
STEP_GB = 50  # a bigger data volume is asked in these steps


def old_logs(home, runs_folder, now=None):
    """The run logs untouched LOG_DAYS removed, and, with no run live, the home's tmp/ entries untouched SCRATCH_DAYS;
    {removed, refused}."""
    home, now = pathlib.Path(home), time.time() if now is None else now
    removed = 0
    for path in sorted((home / "logs").rglob("*")) if (home / "logs").is_dir() else []:
        if path.is_file() and now - path.lstat().st_mtime > LOG_DAYS * 86400:
            path.unlink()
            removed += 1
    refused = cache_refusal(home, pathlib.Path(runs_folder), home / "store" / "cache", [])
    for path in sorted((home / "tmp").iterdir()) if not refused and (home / "tmp").is_dir() else []:
        if (newest(path) if path.is_dir() else now - path.lstat().st_mtime) > SCRATCH_DAYS * 86400:
            remove_tree(path) if path.is_dir() and not path.is_symlink() else path.unlink()
            removed += 1
    return {"removed": removed, "refused": refused and f"tmp/ kept: {refused}"}


def score_commands():
    """The pids of every `python -m score ...` process but this one and its ancestors: a plan, a price, a preflight or
    a moved check registers no run, yet builds layer_base's copies in work/motion-scratch while it judges gates."""
    spare, found = frozen.ancestors(), []
    for entry in pathlib.Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) in spare:
            continue
        try:
            words = (entry / "cmdline").read_bytes().split(b"\0")
        except (FileNotFoundError, ProcessLookupError):
            continue  # it ended meanwhile
        if any(words[at:at + 2] == [b"-m", b"score"] for at in range(len(words) - 1)):
            found.append(int(entry.name))
    return sorted(found)


def clean_scratch(home=None, runs_folder=None):
    """With no run live (cache_refusal) and no `score` command live (score_commands), every entry of
    work/motion-scratch removed: layer_base's copies of a seed, each a make's own and removed as that make ends, left
    there only by a make killed mid-way (2026-11-04: 3.3 GB, the disk at 7.3 GB free and no run could start). A
    command registers no run: on 2026-11-11 the sync pass's sweep cleared the copies a Buy's whole-world `score plan`
    was judging campgrounds' motion gates on (FileNotFoundError writing a texture), and every Buy was refused;
    {removed, refused}."""
    home = pathlib.Path(home or PROPS_HOME)
    refused = cache_refusal(home, pathlib.Path(runs_folder or home / "runs"), home / "store" / "cache", [])
    live = [] if refused else score_commands()
    refused = refused or (live and f"score commands are live: {live}") or None
    scratch = home / MOTION_SCRATCH
    if refused or not scratch.is_dir():
        return {"removed": 0, "refused": refused}
    removed = 0
    for path in sorted(scratch.iterdir()):
        remove_tree(path) if path.is_dir() and not path.is_symlink() else path.unlink()
        removed += 1
    return {"removed": removed, "refused": None}


def steps(home, runs_folder, say, escalated):
    """[(name, call)] of the sweep's steps in order: the routine (copies, makes left behind, kept jobs no key asks
    for), then under WARN_GB everything else made again for free or held elsewhere, offload last (its read-back needs
    room the others freed)."""
    routine = [("clean-frozen", lambda: clean(home, runs_folder, say)),
               ("clean-cache", lambda: clean_cache(home, runs_folder, tuple(CLEARED) if escalated else ("making",),
                                                   say)),
               ("clean-kept", lambda: clean_kept(home, runs_folder, say=say)),
               ("laid-plain", lambda: laid_plain(home)),
               ("clean-scratch", lambda: clean_scratch(home, runs_folder))]
    return routine + ([("relink-pixal", lambda: relink_pixal(home)),
                       ("old-logs", lambda: old_logs(home, runs_folder)),
                       ("store-gc", lambda: store_gc(home, runs_folder, say=say)),
                       ("offload-pixal", lambda: offload_pixal(home, runs_folder))] if escalated else [])


def summed(result):
    """A step's result in words: each figure, each list by its count, each tally of whys whole."""
    return ", ".join(f"{name} {len(value) if isinstance(value, list) else value}" for name, value in result.items()
                     if name != "refused") or "done"


def bigger(more_gb, zone):
    """`more_gb` more on the data volume, priced from Scaleway's catalog (machine.py's own read, free, in a process of
    its own: tools/cloud never joins this one's import path); its words."""
    code = ("import sys; sys.path.insert(0, 'tools/cloud/conductor'); import machine; "
            f"print(machine.unit_price(machine.catalog('block_storage', 'zone={zone}'), "
            f"'/storage/block/volume-low-latency-5k/{zone}') * machine.HOURS_A_MONTH, end='')")
    done = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True)
    if done.returncode != 0:
        return f"{more_gb} GB more (price unread: {(done.stderr.strip().splitlines() or ['no output'])[-1]})"
    return f"{more_gb} GB more, EUR {float(done.stdout) * more_gb:.2f} a month at Scaleway's catalog price"


def fills(home, out):
    """What fills the disk, in words: the home's biggest folders, the deleted files still open and what du cannot see
    (report's account, written to `out`)."""
    report(home, out)
    measured = json.loads(pathlib.Path(out).read_text())
    whole, home = measured["whole"], pathlib.Path(home)
    top = [row for row in measured["folders"] if pathlib.Path(row["path"]).parent == home][:5]
    held, holders = sum(whole["deleted_open"].values()), ", ".join(list(whole["deleted_open"])[:3])
    return ", ".join([f"{row['path']} {row['gb']:.1f} GB" for row in top] +
                     [f"{held:.1f} GB deleted but still open ({holders})"] * (held > 0.5) +
                     [f"{whole['unseen_gb']} GB du cannot see"] * (whole["unseen_gb"] > 0.5))


def sweep(home=None, runs_folder=None, force=False, say=print):
    """The routine steps every time; under WARN_GB on a conductor (or `force`) every step (steps), each said with
    what it freed; still under FLOOR_GB, what fills the disk and the bigger volume it needs, priced. Written to
    conductor/sweep.json, which the Machine card's note reads (warning); the record."""
    home = pathlib.Path(home or PROPS_HOME)
    with alone(home, "sweep") as first:
        if not first:
            return {"refused": "another sweep is running", "steps": [], "escalated": False, "freed_gb": 0.0,
                    "free_after_gb": round(free_gb(home), 2), "bigger": None}
        return swept_once(home, pathlib.Path(runs_folder or home / "runs"), force, say)


def swept_once(home, runs_folder, force, say):
    """sweep's work, its one process holding the lock."""
    record = json.loads((home / "machine.json").read_text()) if (home / "machine.json").is_file() else None
    start = free_gb(home)
    escalated = force or (record is not None and start < WARN_GB)
    done = []
    for name, call in steps(home, runs_folder, say, escalated):
        before = free_gb(home)
        try:
            result = call()
            words = result.get("refused") or summed(result)
        except Unprovable as why:
            result, words = {}, f"refused: {why}"
        except Exception as error:  # one step's fault must not keep the next from freeing room; said, never hidden
            result, words = {}, f"failed: {type(error).__name__}: {error}"
        freed = round(free_gb(home) - before, 2)
        done.append({"step": name, "freed_gb": freed, "said": words})
        say(f"sweep {name}: freed {freed} GB; {words}")
    after = free_gb(home)
    swept = {"at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "free_before_gb": round(start, 2), "free_after_gb": round(after, 2), "escalated": escalated,
             "freed_gb": round(after - start, 2), "steps": done, "fills": None, "bigger": None, "refused": None}
    if escalated and after < FLOOR_GB:
        more = STEP_GB * math.ceil((WARN_GB - after) / STEP_GB)
        swept["fills"] = fills(home, home / "conductor" / "disk.json")
        swept["bigger"] = bigger(more, (record or {}).get("zone", "fr-par-2"))
    out = home / "conductor" / "sweep.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(swept, indent=1))
    return swept
