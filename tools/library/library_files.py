"""The files an environment's records name, from the creator's library (score_lib): the one way a tool reaches a made
model's or a sound's bytes.

A record names a file of the library by a library reference, `<kind>/<id>@<version>/<file in the entry>`
(`sound/habitat.recordings@1/audio/recordings/places/habitat.ogg`, `model/rover.gltf@1/gltf/rover.glb`), and a file
kept in git by its path from the repository's root (`data/ground/moon_plan_relief.png`). A name that is neither, or a
reference to an entry or file the library does not hold, is a hole: `resolve` gives None and the caller leaves the
thing out (the remake fills it, #19), never a crash.

    files.resolve(name)               # the file on disk, or None for a hole
    files.reference(address, file)    # the name a record gives a library entry's file

A referenced file is fetched once into the cache (`$PROPS_HOME/cache/library/score_lib/<kind>/<id>/<version>/<file>`)
by the library's own command (`<SCORE_LIB_COMMAND> --root <SCORE_LIB_ROOT> fetch <address> --file <file> --into
<cache>`; score never imports the library's code) and checked against the sha256 the entry records, every time it is
resolved. The library's settings are the SCORE_LIB_* environment variables; when they are not set, `defaults()` gives
the score_lib checkout beside score's own and its command, and when no blob store is set (SCORE_LIB_BLOBS_DIR,
SCORE_LIB_S3_*), `blob_store()` gives the cloud backend's object store (provider.py object_store(): its endpoint,
region and bucket, the prefix score_lib, and the runtime key from the backend's secret store), read once a run and
handed to the command through its environment only, never written or printed. No settings file holds any of it
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

REPO = pathlib.Path(__file__).resolve().parents[2]
REFERENCE = re.compile(r"^(?P<address>(?P<kind>[a-z]+)/(?P<id>[a-z0-9_]+(?:\.[a-z0-9_]+)?)@(?P<version>[1-9][0-9]*))"
                       r"/(?P<file>[^@]+)$")
DEFAULT_COMMAND = "score-lib"
CLOUD = REPO / "tools/props/cloud"
# The library's blobs sit under this prefix of the cloud backend's bucket (blobs/<sha[:2]>/<sha>).
STORE_PREFIX = "score_lib"
# Either of these set means the blob store is chosen already, and the cloud's is not read.
BLOB_STORE = ("SCORE_LIB_BLOBS_DIR", "SCORE_LIB_S3_ENDPOINT")
# One file's fetch may take this long (a large model over a slow link).
TIMEOUT = 600
# The holes already named on this run.
SAID = set()


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


@functools.lru_cache(maxsize=1)
def cloud_store():
    """The blob store's variables of the library's command for the cloud backend's object store, its key from the
    backend's secret store; read once a run, held in memory only."""
    for folder in (CLOUD / "backends", CLOUD):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    from provider import cloud

    store = cloud.object_store()
    return {"SCORE_LIB_S3_ENDPOINT": store["endpoint"], "SCORE_LIB_S3_REGION": store["region"],
            "SCORE_LIB_S3_BUCKET": store["bucket"], "SCORE_LIB_S3_PREFIX": STORE_PREFIX,
            "AWS_ACCESS_KEY_ID": store["access_key"], "AWS_SECRET_ACCESS_KEY": store["secret_key"]}


def blob_store(values):
    """The command's environment `values`, with the cloud's object store added when no blob store is set in it."""
    return values if any(values.get(name) for name in BLOB_STORE) else {**values, **cloud_store()}


def reference(address, file):
    """The name a record gives one file of a library entry."""
    return f"{address}/{file}"


def parsed(name):
    """The reference's parts (address, kind, id, version, file), or None when the name is no library reference."""
    found = REFERENCE.match(name)
    return found.groupdict() if found else None


def stage_name(name):
    """The name a file takes in a stage's or an output's own folder: a reference's address as folders
    (`sound/habitat.recordings/1/audio/...`), since an OpenUSD asset path holds no '@'; any other name as it is."""
    parts = parsed(name)
    return "/".join((parts["kind"], parts["id"], parts["version"], parts["file"])) if parts else name


def sha256(path):
    """A file's sha256, read in blocks."""
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def recorded_sha(root, parts):
    """The sha256 the library's entry records for the file, or None when the library holds no such entry or file."""
    path = pathlib.Path(root) / "entries" / parts["kind"] / parts["id"] / parts["version"] / "entry.json"
    if not path.is_file():
        return None
    described = json.loads(path.read_text())["files"].get(parts["file"])
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
    """A referenced file from the cache, fetched when missing or changed and hash-checked; None for a hole."""
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
        return target
    fetched(values, parts, target)
    if not target.is_file() or sha256(target) != expected:
        raise LibraryUnreachable(f"{name}: the fetched file does not hash to the entry's sha256 {expected}")
    return target


def from_folder(name, folder):
    """A file under its record name in a folder of one's own, or None when it is not there."""
    path = pathlib.Path(folder) / name
    return path if path.is_file() else None


def resolve(name, folder=None):
    """The file a record names on disk: a repository file (`data/...`), else from `folder` (or SCORE_LIB_FILES) when
    given, else from the library; None when it is a hole (no library reference, or one the library does not hold).
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


def say_hole(name, what):
    """One line naming a hole, once per name and run."""
    if name not in SAID:
        SAID.add(name)
        print(f"hole: {what} names {name}, which the library does not hold (left out)", flush=True)
