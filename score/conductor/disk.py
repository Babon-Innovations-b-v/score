"""The data disk under $PROPS_HOME: what fills it, the floor under which no run starts, and the sweep of frozen copies
no run needs any more (2026-10-26 23:45 UTC: 0.24 GB free of 91 GB, Batch 1 died with "No space left on device";
about twelve runs had started that day, and the copies of the ones stopped, failed or cut off stayed on the disk).

    python -m score.conductor disk           # one summary line, the biggest folders, the whole list in conductor/disk.json
    python -m score.conductor clean-frozen   # remove every frozen copy no run needs; what it freed, one line a copy
    python -m score.conductor clean-cache [--making-only]   # checkouts relinked; with no run live, the cache cleared
    python -m score.conductor clean-kept     # with no run live, the kept jobs no current key asks for, one line
    python -m score.conductor relink-pixal   # work/pixal's files the store holds made links to its blobs, one line
    python -m score.conductor offload-pixal  # with no run live, work/pixal's takes into the library, freed once read back

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
"""
import datetime
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

from score import conductor
from score.conductor import size
from score.graph import frozen, runs
from score.store import PROPS_HOME, Store, file_hash, linked_read_only, partial_of

FLOOR_GB = 10  # under this many GB free no run starts, and the Machine card warns
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
    """{root: depth} measured: the home two levels down (frozen/<copy>, store/objects, store/cache, ...), DEEP three
    levels down, and the checkout and the user's cache (the backup's restic cache) when they are on the home's disk."""
    home = pathlib.Path(home or PROPS_HOME)
    device = home.stat().st_dev
    extra = [REPO, pathlib.Path.home() / ".cache"]
    return {home: 2, **{home / deep: 3 for deep in DEEP if (home / deep).is_dir()},
            **{root: 1 for root in extra if root.is_dir() and root.stat().st_dev == device
               and not root.is_relative_to(home)}}


def report(home=None, out=None):
    """Measure the disk (roots), write every folder's size to `out` (conductor/disk.json), biggest first; (summary
    line, the SHOWN biggest lines)."""
    home = pathlib.Path(home or PROPS_HOME)
    sizes = sorted({pair for root, depth in roots(home).items() for pair in du(root, depth)}, reverse=True)
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
    inside = [(count, path) for count, path in sizes if any(
        pathlib.Path(path).is_relative_to(home / deep) and pathlib.Path(path) != home / deep for deep in DEEP)]
    return summary, [f"{count / 1024 ** 3:8.2f} GB  {path}" for count, path in sizes[:SHOWN]] + \
        [f"inside {' and '.join(DEEP)}, three levels down:"] + \
        [f"{count / 1024 ** 3:8.2f} GB  {path}" for count, path in inside[:SHOWN]]


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


def relink_pixal(home=None, now=None):
    """Every work/pixal file whose bytes the store holds as a blob, untouched for YOUNG_SECONDS, made a hard link to
    that blob; {relinked, freed_gb, kept: {why: files}}."""
    home = pathlib.Path(home or PROPS_HOME)
    blobs = Store.in_folder(home / "store").objects.path("blobs")
    now = time.time() if now is None else now
    relinked, freed, kept = 0, 0, {}
    for path in sorted((home / "work" / "pixal").rglob("*")):
        if path.is_dir() and not path.is_symlink():
            continue
        size = path.lstat().st_size
        why = relinked_or_why(path, blobs, now)
        if why:
            kept[why] = kept.get(why, 0) + 1
        else:
            relinked, freed = relinked + 1, freed + size
    return {"relinked": relinked, "freed_gb": round(freed / 1024 ** 3, 2), "kept": kept}


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
