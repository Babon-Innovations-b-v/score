"""score_lib's file cache ($PROPS_HOME/cache/library, filled by library_files.from_library) kept within a cap (owner,
2026-11-19: a machine's disk holds only caches with a size cap; 2026-11-24 this PC held 59 GB in its own home's cache
and 41 GB in its run home's, with no cap).

    PROPS_HOME=<home> .venv/bin/python tools/library/library_cache.py cap [GB]   # one summary line

Past CACHE_GB (SCORE_LIB_CACHE_GB) the least recently read files go (`capped`) until the rest fits, each only once its
bytes hash to the sha256 its entry records and the library's public copy answers a HEAD for that blob with its size
and sha256 (X-Linked-Size, X-Linked-ETag); never one read in the last RECENT_SECONDS (a run may still hold its path),
one of a withdrawn entry (its bytes may be gone: score/stages/demo_film reads a withdrawn bed from the cache), or one
linked elsewhere (it frees nothing). Each evicted file is written first to EVICTED beside the cache with its size and
mtime, so this PC's pull names it (`evicted_lines`) and the door does not send it again; library_files.resolve
fetches it back on its next read. this_pc.py runs it after every push, the prop benchmark at the end of each run.

A module of its own, not library_files.py: that file is in every library-reading stage's code version
(score/graph/_code.py), and the cache's upkeep shapes no output.
"""
import concurrent.futures
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import library_files  # noqa: E402

CACHE_GB = float(os.environ.get("SCORE_LIB_CACHE_GB") or 20)  # the file cache's cap, GB of 1e9 bytes
RECENT_SECONDS = 24 * 3600  # a file read this recently is never evicted (a run may hold its path; relatime is daily)
EVICTED = "library-evicted.jsonl"  # beside the cache (never pulled): one line {path, size, mtime} a file evicted
# A blob of the public copy (score_lib's hub store: blobs/<sha[:2]>/<sha>); its HEAD answers X-Linked-Size and
# X-Linked-ETag, the blob's sha256.
HUB_BLOB = "https://huggingface.co/datasets/{repo}/resolve/main/blobs/{head}/{sha}"
WORKERS = 16  # files proven at once (each a hash and one HEAD)


class Unfollowed(urllib.request.HTTPRedirectHandler):
    """The public copy's 302 to its bytes kept as the answer: its headers name the blob."""

    def redirect_request(self, *args, **kwargs):
        return None


def public_holds(values, sha, size):
    """Whether the library's public copy answers for the blob with this size and this sha256 (one HEAD, redirects not
    followed); False when another blob store is set, which this cannot ask."""
    if any(values.get(name) for name in library_files.BLOB_STORE):
        return False
    request = urllib.request.Request(HUB_BLOB.format(repo=library_files.HUB_REPO, head=sha[:2], sha=sha),
                                     method="HEAD")
    try:
        answer = urllib.request.build_opener(Unfollowed).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        answer = error  # the 302 to the bytes carries the headers; a 404 carries none
    linked = (answer.headers.get("X-Linked-Size"), (answer.headers.get("X-Linked-ETag") or "").strip('"'))
    return linked == (str(size), sha)


def cached_files():
    """(last read, path, its reference's parts) of every file in the cache, the least recently read first."""
    root = library_files.cache_folder() / "score_lib"
    found = []
    for path in root.rglob("*") if root.is_dir() else []:
        relative = path.relative_to(root).parts
        if path.is_file() and not path.is_symlink() and len(relative) >= 4:
            parts = library_files.parsed(f"{relative[0]}/{relative[1]}@{relative[2]}/{'/'.join(relative[3:])}")
            found.append((path.stat().st_atime, path, parts))
    return sorted(found, key=lambda item: item[0])


def unread_sha256(path):
    """A file's sha256, read without moving its last-read time (O_NOATIME, as score/conductor/disk.py's unread), so
    proving a file leaves the order `capped` evicts by as the runs' reads left it; a plain read where the kernel
    refuses the flag (a file another user owns)."""
    try:
        source = os.fdopen(os.open(path, os.O_RDONLY | os.O_NOATIME), "rb")
    except PermissionError:
        source = open(path, "rb")
    digest = hashlib.sha256()
    with source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def evict_why(values, path, parts, now):
    """Why the cached file at `path` stays, or None once it may go: read long enough ago, linked nowhere else, its
    entry not withdrawn, its bytes the entry's sha256 and the public copy holding them."""
    status = path.stat()
    if now - status.st_atime < RECENT_SECONDS:
        return "read recently"
    if status.st_nlink > 1:
        return "linked elsewhere too"
    record = library_files.entry_record(values["SCORE_LIB_ROOT"], parts) if parts else None
    if record is None or record.get("state") == "withdrawn":
        return "no entry, or a withdrawn one"
    expected = (record.get("files") or {}).get(parts["file"], {}).get("sha256")
    if expected is None or unread_sha256(path) != expected:
        return "not the bytes its entry records"
    if not public_holds(values, expected, status.st_size):
        return "the public copy did not answer with its size and sha256"
    return None


def evicted(path):
    """The cached file at `path` written to EVICTED (its path in the cache, size and mtime), then removed; its size."""
    status = path.stat()
    line = {"path": path.relative_to(library_files.cache_folder()).as_posix(), "size": status.st_size,
            "mtime": int(status.st_mtime)}
    with open(library_files.cache_folder().parent / EVICTED, "a") as marks:
        marks.write(json.dumps(line) + "\n")
    path.unlink()
    return status.st_size


def capped(values=None, cap_gb=None, now=None):
    """The file cache brought within `cap_gb` (CACHE_GB): the least recently read files that may go (evict_why,
    WORKERS at a time, in that order) evicted until the rest fits; {evicted, freed_gb, kept: {why: count}}."""
    values, cap_gb = values or library_files.settings(), CACHE_GB if cap_gb is None else cap_gb
    now = time.time() if now is None else now
    files = cached_files()
    over = sum(path.stat().st_size for _, path, _ in files) - cap_gb * 1e9
    done = {"evicted": 0, "freed_gb": 0.0, "kept": {}}
    if not values.get("SCORE_LIB_ROOT"):
        return done
    with concurrent.futures.ThreadPoolExecutor(WORKERS) as pool:
        for start in range(0, len(files), WORKERS):
            if over <= 0:
                break
            batch = files[start:start + WORKERS]
            answers = pool.map(lambda item: evict_why(values, item[1], item[2], now), batch)
            for (_, path, _), why in zip(batch, list(answers)):
                if why:
                    done["kept"][why] = done["kept"].get(why, 0) + 1
                elif over > 0:
                    size = evicted(path)
                    over -= size
                    done["evicted"], done["freed_gb"] = done["evicted"] + 1, done["freed_gb"] + size / 1e9
    done["freed_gb"] = round(done["freed_gb"], 2)
    return done


def evicted_lines(home):
    """`size<TAB>mtime<TAB>cache/library/<path>` manifest lines of each file evicted from `home`'s cache and not
    fetched back: the door then leaves it out of a pull."""
    marks, lines = pathlib.Path(home) / "cache" / EVICTED, {}
    for text in marks.read_text().splitlines() if marks.is_file() else []:
        mark = json.loads(text)
        if not (pathlib.Path(home) / "cache" / "library" / mark["path"]).exists():
            lines[mark["path"]] = f"{mark['size']}\t{mark['mtime']}\tcache/library/{mark['path']}\n"
    return "".join(lines.values())


if __name__ == "__main__":
    if sys.argv[1:2] != ["cap"]:
        raise SystemExit("usage: library_cache.py cap [GB]   # $PROPS_HOME's score_lib file cache within its cap")
    done = capped(cap_gb=float(sys.argv[2]) if sys.argv[2:] else None)
    print(f"library cache: evicted {done['evicted']} files, {done['freed_gb']} GB; kept {done['kept']}", flush=True)
