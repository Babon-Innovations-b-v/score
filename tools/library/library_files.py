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
resolved. The library's settings are the SCORE_LIB_* environment variables, else the lines of `$PROPS_HOME/library.env`
(score/stages/library/backend.py), which may also hold the blob store's variables the command needs.

A test or a check with its own files gives `folder` (or SCORE_LIB_FILES): a folder holding each file under the name
the records give, read instead of the library.

Files a tool makes for an environment (route.py install, the sound tools) go to `made_folder()`; `score-lib take-in`
takes them into the library, and the records then name their references.
"""
import hashlib
import json
import os
import pathlib
import re
import shlex
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[2]
REFERENCE = re.compile(r"^(?P<address>(?P<kind>[a-z]+)/(?P<id>[a-z0-9_]+(?:\.[a-z0-9_]+)?)@(?P<version>[1-9][0-9]*))"
                       r"/(?P<file>[^@]+)$")
SETTINGS_FILE = "library.env"
DEFAULT_COMMAND = "score-lib"
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


def file_settings():
    """{KEY: VALUE} of $PROPS_HOME/library.env (blank lines and # comments skipped); empty when it is not there."""
    path = props_home() / SETTINGS_FILE
    if not path.is_file():
        return {}
    found = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            found[key.strip()] = value.strip().strip("'\"")
    return found


def settings():
    """The library's settings: library.env's lines with this process's environment over them."""
    return {**file_settings(), **os.environ}


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
        done = subprocess.run(words, env=values, cwd=values["SCORE_LIB_ROOT"], capture_output=True, text=True,
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
        raise LibraryUnreachable(f"{name}: no library is configured (SCORE_LIB_ROOT, or {props_home() / SETTINGS_FILE})")
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
