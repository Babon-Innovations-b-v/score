"""A home's manifest, what a backup must bring back whole: the store's listing hash over store/objects (its listing
kept, so a mismatch names the objects), and the sha256 and size of every file in MANIFEST_FOLDERS, each dashboard
database as its consistent copy (_staging). Two homes match when both are equal; `differences` names every file that
is not.
"""
import fnmatch
import pathlib
import tempfile

from score.store import listing_hash, tree_listing
from score.store.backup import _staging

MANIFEST_FOLDERS = ("design", "cloud", "runs", "dashboard", "work")
OBJECTS = "store/objects"
# Files no backup holds, so no manifest counts them: a write still landing.
NEVER_BACKED_UP = ("*.partial",)


def kept(name):
    """True for a relative path a backup holds."""
    return not any(fnmatch.fnmatch(pathlib.PurePosixPath(name).name, pattern) for pattern in NEVER_BACKED_UP)


def store_part(home):
    """{listing_hash, objects, listing} of the home's store objects (an empty listing when there is no store)."""
    folder = pathlib.Path(home) / OBJECTS
    listing = {name: sha for name, sha in tree_listing(folder).items() if kept(name)} if folder.is_dir() else {}
    return {"listing_hash": listing_hash(listing), "objects": len(listing), "listing": listing}


def folder_files(home, folder, copies):
    """{relative path: {sha256, bytes}} of one manifest folder, a database's copy standing for it and its side files
    left out."""
    root = pathlib.Path(home) / folder
    if not root.is_dir():
        return {}
    side = {name for database in copies for name in _staging.side_files(database)}
    files = {}
    for name, sha in tree_listing(root).items():
        relative = f"{folder}/{name}"
        if not kept(name) or relative in side:
            continue
        source = copies.get(relative)
        if source is not None:  # a database by its content: two copies of one state differ in header bytes
            files[relative] = {"sha256": _staging.content_hash(source), "bytes": None}
            continue
        files[relative] = {"sha256": sha, "bytes": (root / name).stat().st_size}
    return files


def manifest(home, copies=None):
    """The manifest of `home`. `copies` ({relative path: staged copy}) are its databases' copies when the caller staged
    them already; otherwise they are copied into a temporary folder for the reading."""
    if copies is not None:
        return build(home, copies)
    with tempfile.TemporaryDirectory(prefix="score-manifest-") as scratch:
        return build(home, _staging.stage(home, pathlib.Path(scratch) / "copies"))


def build(home, copies):
    """The manifest of `home`, its databases read from `copies`."""
    files = {}
    for folder in MANIFEST_FOLDERS:
        files.update(folder_files(home, folder, copies))
    return {"home": str(home), "store": store_part(home), "files": dict(sorted(files.items()))}


def differences(expected, found):
    """Every difference of `found` from `expected`, one line each, sorted: a file missing, extra or changed, and each
    store object that differs when the store's listing hash does not match."""
    lines = []
    for name in sorted(set(expected["files"]) | set(found["files"])):
        if name not in found["files"]:
            lines.append(f"missing: {name}")
        elif name not in expected["files"]:
            lines.append(f"extra: {name}")
        elif expected["files"][name] != found["files"][name]:
            lines.append(f"changed: {name}")
    if expected["store"]["listing_hash"] != found["store"]["listing_hash"]:
        before, after = expected["store"]["listing"], found["store"]["listing"]
        for key in sorted(set(before) | set(after)):
            if before.get(key) != after.get(key):
                state = "missing" if key not in after else "extra" if key not in before else "changed"
                lines.append(f"{state}: {OBJECTS}/{key}")
    return lines
