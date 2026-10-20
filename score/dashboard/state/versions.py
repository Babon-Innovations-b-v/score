"""The versions a state export is keyed on, light enough for a hosted process (hashlib only).

FORMAT is the shape of the export's records: the store's machine writes it into the manifest, and the hosted side
refuses to swap in an export of a format it cannot read (sync/endpoints.py), so a mismatch shows in the sync log and
the pages keep the last export they could read. Raise it when a record the hosted pages validate changes shape.
A code version is the sha256 of the Python files of the code that makes a piece, so every cached piece made by that
code is made again when it changes (owner, 2026-10-18: old place bundles outlived the code that read them).
"""
import functools
import hashlib
import pathlib

FORMAT = 3  # 1: gaps and stopped steps as lines of words; 2: as records; 3: holes are gaps, gaps accepted gaps
READABLE = (FORMAT,)
DASHBOARD = pathlib.Path(__file__).resolve().parents[1]
EXPORTING = ("state", "previews", "sync")  # the code that builds an export and its pictures
SHORT = 12


def code_version(paths):
    """The sha256 of every .py file under `paths` (folders or files), names and bytes, in a fixed order."""
    digest = hashlib.sha256()
    for root in paths:
        root = pathlib.Path(root)
        files = sorted(root.rglob("*.py")) if root.is_dir() else [root]
        for path in files:
            digest.update(path.relative_to(DASHBOARD).as_posix().encode() + b"\0")
            digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


@functools.cache
def exporting():
    """The code version of what builds an export: score/dashboard/state, previews and sync."""
    return code_version([DASHBOARD / folder for folder in EXPORTING])[:SHORT]
