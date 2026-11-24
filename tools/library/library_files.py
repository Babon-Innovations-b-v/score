"""The files an environment's records name, from the creator's library (score_lib): the one way a tool reaches a made
model's or a sound's bytes.

A record names a file of the library by a library reference, `<kind>/<id>@<version>/<file in the entry>`
(`sound/habitat@1/audio/recordings/places/habitat.ogg`, `model/rover.gltf@1/gltf/rover.glb`), and a file
kept in git by its path from the repository's root (`data/library/lamps.json`). A name that is neither, or a
reference to an entry or file the library does not hold, is a gap: `resolve` gives None and the caller leaves the
thing out (the remake fills it, #19), never a crash.

    files.resolve(name)               # the file on disk, or None for a gap
    files.reference(address, file)    # the name a record gives a library entry's file

A referenced file is fetched once into the cache (`$PROPS_HOME/cache/library/score_lib/<kind>/<id>/<version>/<file>`)
by the library's own command (`<SCORE_LIB_COMMAND> --root <SCORE_LIB_ROOT> fetch <address> --file <file> --into
<cache>`; score never imports the library's code) and checked against the sha256 the entry records, every time it is
resolved. The cache is capped (owner, 2026-11-19: a machine's disk holds only capped caches): past CACHE_GB
(SCORE_LIB_CACHE_GB) the least recently read files go after every fetch (`capped`, by hand `library_files.py cap`),
each only once its bytes hash to the entry's sha256 and the public copy answers for it with that size and sha256, none
read in the last RECENT_SECONDS (a run may still hold its path), none of a withdrawn entry (its bytes may be gone), none
linked elsewhere; each one evicted is written to EVICTED with its size and mtime, so this PC's pull names it and is not
sent it again, and a resolve fetches it back. The library's settings are the SCORE_LIB_* environment variables; when they are not set, `defaults()` gives
the score_lib checkout beside score's own and its command, and when no blob store is set (SCORE_LIB_BLOBS_DIR,
SCORE_LIB_S3_*, or SCORE_LIB_HUB_REPO), `blob_store()` gives the library's public Hugging Face copy (HUB_REPO), read
with no key; a take-in's write token comes from STORE_BACKEND's secret store, read once a run and handed to the
command through its environment only, never written or printed. The library's bucket was retired on 2026-11-22, its
blobs all on the public copy. No settings file holds any of it
(owner, 2026-10-20).

A test or a check with its own files gives `folder` (or SCORE_LIB_FILES): a folder holding each file under the name
the records give, read instead of the library.

Files a tool makes for an environment (route.py install, the sound tools) go to `made_folder()`; `score-lib take-in`
takes them into the library, and the records then name their references.
"""
import functools
import hashlib
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[2]
REFERENCE = re.compile(r"^(?P<address>(?P<kind>[a-z]+)/(?P<id>[a-z0-9_]+(?:\.[a-z0-9_]+)?)@(?P<version>[1-9][0-9]*))"
                       r"/(?P<file>[^@]+)$")
DEFAULT_COMMAND = "score-lib"
CLOUD = REPO / "tools/cloud"
# The backend whose secret store holds the public copy's write token, whichever backend SCORE_CLOUD sends the compute
# to (this PC's, the cluster's).
STORE_BACKEND = "scaleway"
# The library's public copy, read with no key (score #141), and the secret holding its write token.
HUB_REPO = "Babon-Innovations-b-v/score-lib"
HUB_TOKEN_SECRET = "hf-write-token"
# Either of these set means the blob store is chosen already, and the public copy is not added.
BLOB_STORE = ("SCORE_LIB_BLOBS_DIR", "SCORE_LIB_S3_ENDPOINT", "SCORE_LIB_HUB_REPO")
# One file's fetch may take this long (a large model over a slow link).
TIMEOUT = 600
# The gaps already named on this run.
SAID = set()
CACHE_GB = float(os.environ.get("SCORE_LIB_CACHE_GB") or 20)  # the file cache's cap, GB of 1e9 bytes
RECENT_SECONDS = 24 * 3600  # a file read this recently is never evicted (a run may hold its path; relatime is daily)
EVICTED = "library-evicted.jsonl"  # beside the cache (never pulled): one line {path, size, mtime} a file evicted
# A blob of the public copy (score_lib's hub store: blobs/<sha[:2]>/<sha>); its HEAD answers X-Linked-Size and
# X-Linked-ETag, the blob's sha256.
HUB_BLOB = "https://huggingface.co/datasets/{repo}/resolve/main/blobs/{head}/{sha}"


class LibraryUnreachable(RuntimeError):
    """A referenced file the library holds but could not be fetched, or came back with other bytes."""


def props_home():
    return pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props"))


def made_folder():
    """Where a tool writes the files it makes for an environment, before score-lib take-in takes them in."""
    return props_home() / "made"


def cache_folder():
    return props_home() / "cache" / "library"


def default_root():
    """score_lib's checkout beside score's main checkout (found from a worktree too), or None when there is none."""
    found = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           capture_output=True, text=True)
    root = pathlib.Path(found.stdout.strip()).parent.parent / "score_lib" if found.returncode == 0 else None
    return root if root and (root / "entries").is_dir() else None


def defaults():
    """SCORE_LIB_ROOT and SCORE_LIB_COMMAND when no variable sets them: the checkout beside score's and its own
    command (its .venv's score-lib, else score-lib on the PATH); empty when there is no such checkout."""
    root = default_root()
    if root is None:
        return {}
    command = root / ".venv/bin/score-lib"
    return {"SCORE_LIB_ROOT": str(root), "SCORE_LIB_COMMAND": str(command) if command.is_file() else DEFAULT_COMMAND}


def settings():
    """The library's settings: the defaults with this process's environment over them."""
    return {**defaults(), **os.environ}


def blob_store(values, write=False):
    """The command's environment `values`, with the library's public Hugging Face copy (HUB_REPO, read with no key)
    added when no blob store is set in it; `write` (a take-in) adds its write token from STORE_BACKEND's secret store
    (HUB_TOKEN_SECRET) when the environment holds none, handed to the command only, never written or printed. The
    library's bucket was retired for it (owner, 2026-11-19: "agree and retire, we use the same lib as everyone
    else")."""
    found = values if any(values.get(name) for name in BLOB_STORE) else {**values, "SCORE_LIB_HUB_REPO": HUB_REPO}
    if write and found.get("SCORE_LIB_HUB_REPO") and not found.get("HF_TOKEN"):
        found = {**found, "HF_TOKEN": hub_token()}
    return found


@functools.lru_cache(maxsize=1)
def hub_token():
    """The write token of the library's Hugging Face copy from STORE_BACKEND's secret store; read once a run, held in
    memory only."""
    for folder in (CLOUD / "backends", CLOUD):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    import provider

    return provider.load(STORE_BACKEND).secret(HUB_TOKEN_SECRET)


def reference(address, file):
    """The name a record gives one file of a library entry."""
    return f"{address}/{file}"


def parsed(name):
    """The reference's parts (address, kind, id, version, file), or None when the name is no library reference."""
    found = REFERENCE.match(name)
    return found.groupdict() if found else None


def stage_name(name):
    """The name a file takes in a stage's or an output's own folder: a reference's address as folders
    (`sound/habitat/1/audio/...`), since an OpenUSD asset path holds no '@'; any other name as it is."""
    parts = parsed(name)
    return "/".join((parts["kind"], parts["id"], parts["version"], parts["file"])) if parts else name


def sha256(path):
    """A file's sha256, read in blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def entry_record(root, parts):
    """The library's entry record the reference's parts name, or None when the library holds no such entry."""
    path = pathlib.Path(root) / "entries" / parts["kind"] / parts["id"] / parts["version"] / "entry.json"
    return json.loads(path.read_text()) if path.is_file() else None


def recorded_sha(root, parts):
    """The sha256 the library's entry records for the file, or None when the library holds no such entry or file."""
    described = (entry_record(root, parts) or {"files": {}})["files"].get(parts["file"])
    return described["sha256"] if described else None


def fetched(values, parts, target):
    """The file fetched into the cache by the library's own command; LibraryUnreachable when it fails."""
    words = shlex.split(values.get("SCORE_LIB_COMMAND") or DEFAULT_COMMAND) + [
        "--root", values["SCORE_LIB_ROOT"], "fetch", parts["address"], "--file", parts["file"],
        "--into", str(cache_folder())]
    if target.exists():
        target.unlink()  # its bytes no longer match the entry: fetched again
    try:
        done = subprocess.run(words, env=blob_store(values), cwd=values["SCORE_LIB_ROOT"], capture_output=True, text=True,
                              timeout=TIMEOUT)
    except (FileNotFoundError, subprocess.TimeoutExpired) as failed:
        raise LibraryUnreachable(f"{shlex.join(words)}: {failed}") from failed
    if done.returncode != 0:
        raise LibraryUnreachable(f"{shlex.join(words)} exited {done.returncode}: {done.stderr.strip()[-400:]}")


def from_library(name, parts):
    """A referenced file from the cache, fetched when missing or changed and hash-checked; None for a gap."""
    values = settings()
    root = values.get("SCORE_LIB_ROOT")
    if not root:
        raise LibraryUnreachable(f"{name}: no library is configured (SCORE_LIB_ROOT, and no score_lib checkout "
                                 "beside score's)")
    expected = recorded_sha(root, parts)
    if expected is None:
        return None
    target = cache_folder() / "score_lib" / parts["kind"] / parts["id"] / parts["version"] / parts["file"]
    if target.is_file() and sha256(target) == expected:
        return read_now(target)
    fetched(values, parts, target)
    if not target.is_file() or sha256(target) != expected:
        raise LibraryUnreachable(f"{name}: the fetched file does not hash to the entry's sha256 {expected}")
    capped(values)
    return target


def read_now(path):
    """`path` with its last-read time set to now (its mtime kept: the pull's manifest reads that), the order `capped`
    evicts by; relatime alone moves it once a day at most."""
    try:
        os.utime(path, (time.time(), path.stat().st_mtime))
    except PermissionError:  # a file another user owns keeps the order relatime gives it
        pass
    return path


def public_holds(values, sha, size):
    """Whether the library's public copy answers for the blob with this size and this sha256 (one HEAD, redirects not
    followed); False when another blob store is set, which this cannot ask."""
    if any(values.get(name) for name in BLOB_STORE):
        return False

    class Kept(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    request = urllib.request.Request(HUB_BLOB.format(repo=HUB_REPO, head=sha[:2], sha=sha), method="HEAD")
    try:
        answer = urllib.request.build_opener(Kept).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        answer = error  # the 302 to the bytes carries the headers; a 404 carries none
    linked = (answer.headers.get("X-Linked-Size"), (answer.headers.get("X-Linked-ETag") or "").strip('"'))
    return linked == (str(size), sha)


def cached_files():
    """(last read, path, its reference's parts) of every file in the cache, the least recently read first."""
    root = cache_folder() / "score_lib"
    found = []
    for path in root.rglob("*") if root.is_dir() else []:
        relative = path.relative_to(root).parts
        if path.is_file() and not path.is_symlink() and len(relative) >= 4:
            parts = parsed(f"{relative[0]}/{relative[1]}@{relative[2]}/{'/'.join(relative[3:])}")
            found.append((path.stat().st_atime, path, parts))
    return sorted(found, key=lambda item: item[0])


def evict_why(values, path, parts, now):
    """Why the cached file at `path` stays, or None once it may go: read long enough ago, linked nowhere else, its
    entry not withdrawn, its bytes the entry's sha256 and the public copy holding them."""
    status = path.stat()
    if now - status.st_atime < RECENT_SECONDS:
        return "read recently"
    if status.st_nlink > 1:
        return "linked elsewhere too"
    record = entry_record(values["SCORE_LIB_ROOT"], parts) if parts else None
    if record is None or record.get("state") == "withdrawn":
        return "no entry, or a withdrawn one"
    expected = (record.get("files") or {}).get(parts["file"], {}).get("sha256")
    if expected is None or sha256(path) != expected:
        return "not the bytes its entry records"
    if not public_holds(values, expected, status.st_size):
        return "the public copy did not answer with its size and sha256"
    return None


def capped(values=None, cap_gb=None, now=None):
    """The file cache brought within `cap_gb` (CACHE_GB): the least recently read files that may go (evict_why)
    evicted, each written to EVICTED first, until the rest fits; {evicted, freed_gb, kept: {why: count}}."""
    values, cap_gb = values or settings(), CACHE_GB if cap_gb is None else cap_gb
    now = time.time() if now is None else now
    files = cached_files()
    over = sum(path.stat().st_size for _, path, _ in files) - cap_gb * 1e9
    done = {"evicted": 0, "freed_gb": 0.0, "kept": {}}
    for _, path, parts in files:
        if over <= 0 or not values.get("SCORE_LIB_ROOT"):
            break
        why = evict_why(values, path, parts, now)
        if why:
            done["kept"][why] = done["kept"].get(why, 0) + 1
            continue
        status = path.stat()
        line = {"path": path.relative_to(cache_folder()).as_posix(), "size": status.st_size,
                "mtime": int(status.st_mtime)}
        with open(cache_folder().parent / EVICTED, "a") as marks:
            marks.write(json.dumps(line) + "\n")
        path.unlink()
        over -= status.st_size
        done["evicted"], done["freed_gb"] = done["evicted"] + 1, done["freed_gb"] + status.st_size / 1e9
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


def from_folder(name, folder):
    """A file under its record name in a folder of one's own, or None when it is not there."""
    path = pathlib.Path(folder) / name
    return path if path.is_file() else None


def resolve(name, folder=None):
    """The file a record names on disk: a repository file (`data/...`), else from `folder` (or SCORE_LIB_FILES) when
    given, else from the library; None when it is a gap (no library reference, or one the library does not hold).
    A repository file that is not there raises FileNotFoundError."""
    if name.startswith("data/"):
        path = REPO / name
        if not path.exists():
            raise FileNotFoundError(f"{name}: not in the repository ({path})")
        return path
    folder = folder or os.environ.get("SCORE_LIB_FILES")
    if folder:
        return from_folder(name, folder)
    parts = parsed(name)
    return from_library(name, parts) if parts else None


def say_gap(name, what):
    """One line naming a gap, once per name and run."""
    if name not in SAID:
        SAID.add(name)
        print(f"gap: {what} names {name}, which the library does not hold (left out)", flush=True)


if __name__ == "__main__":
    if sys.argv[1:2] != ["cap"]:
        raise SystemExit("usage: library_files.py cap [cap GB]   # $PROPS_HOME's file cache brought within its cap")
    done = capped(cap_gb=float(sys.argv[2]) if sys.argv[2:] else None)
    print(f"library cache: evicted {done['evicted']} files, {done['freed_gb']} GB; kept {done['kept']}", flush=True)
