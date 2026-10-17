"""Which rows a change moves, before it is pushed: a row moves when its code version differs, or when a repository
file it declares (Stage.files: "blender runner": blender_cloud.py, a data folder) keys differently, hashed as the
runner keys it (the part a (pattern, part) declaration reads), a file it starts or stops declaring included. A
code-only check missed the second (8b402226, 2026-10-14: blender_cloud.py is outside every code version, yet the
turntable rows declare it, and every place's turntable was rendered again); a check of changed paths alone missed a
new file in the working tree and a file a row starts declaring (the gap files of 1f90a0fe, 2026-10-15).

    .venv/bin/python -m score.stages.moved <base> [<head>]     # head: a commit, default the working tree
    .venv/bin/python -m score.stages.moved <base> <head> --json   # the same as one JSON object (the cockpit prices it)

Prints each moved row (paid marked), why, and for a declared file the places it moves in, then a warning for each
file the change moves into FRAMEWORK and edits too (the rows that read it are made again, not kept). With --json,
every moved row as {paid, code, files: {path: [places]}, places: [every place the row is declared at, "None" for a
world row]}.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

from score.graph import _code

REPO = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT = """import json, pathlib, sys
sys.path.insert(0, ".")
from score import graph, stages
from score.graph import _code
from score.store import file_hash, listing_hash, text_hash
runner = stages.runner(world=stages.WORLDS["world1"]())
places = stages.places(runner.world)
repo = pathlib.Path(".").resolve()
found = {}
for row in stages.STAGES:
    declared = {}
    for place in ([None] if row.grain == "world" else places):
        if row.applies and place is not None and not row.applies(place):
            continue
        try:
            names = runner.files_of(row, place)
        except Exception:  # a row whose files cannot be listed for a place (its data missing) declares none there
            continue
        keys = {}
        for name, pattern in names.items():
            path = runner.file_path(row, name, place).resolve()
            if path.is_relative_to(repo):
                keys[path.relative_to(repo).as_posix()] = ("missing" if not path.exists() else
                    text_hash(pattern[1](path)) if isinstance(pattern, tuple) else graph.source_hash(path))
        declared[str(place)] = keys
    found[row.name] = {"paid": bool(row.paid), "declared": declared,
                       "code": listing_hash(_code.code_version(graph.code_functions(row), file_hash))}
print(json.dumps(found))"""


def snapshot_here(folder):
    """{row: {"paid", "code", "declared": {place: {repository path: its key}}}} as the tree at `folder` works it
    out."""
    done = subprocess.run([sys.executable, "-c", SNAPSHOT], cwd=folder, capture_output=True, text=True, check=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    return json.loads(done.stdout.strip().splitlines()[-1])


def snapshot(commit):
    """The snapshot of a commit, in a checkout of its own (removed); of the working tree when `commit` is None."""
    if commit is None:
        return snapshot_here(REPO)
    folder = pathlib.Path(tempfile.mkdtemp(prefix="moved-", dir=REPO.parent)) / "tree"
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", str(folder), commit], check=True)
    try:
        return snapshot_here(folder)
    finally:
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", str(folder)], check=True)
        folder.parent.rmdir()


def moved(base, head=None):
    """{row: {"paid", "code": its code version moved, "files": {declared path: [places]}, "places": [every place it
    is declared at]}} of every row the change from `base` to `head` moves, by its code or by a file it declares that
    keys differently (or is newly declared or no longer)."""
    before, after = snapshot(base), snapshot(head)
    found = {}
    for name, row in after.items():
        code = name not in before or before[name]["code"] != row["code"]
        files = {}
        for place, keys in row["declared"].items():
            earlier = before.get(name, {}).get("declared", {}).get(place, {})
            for path in sorted(set(keys) | set(earlier)):
                if keys.get(path) != earlier.get(path):
                    files.setdefault(path, []).append(place)
        if code or files:
            found[name] = {"paid": row["paid"], "code": code, "files": files, "places": sorted(row["declared"])}
    return found


def edited_into_framework(base, head=None):
    """The repository files the change from `base` to `head` (default: the working tree) moves into FRAMEWORK and
    edits too. A plain move keeps the outputs of the rows that read it (graph's narrowing carry); an edit in the same
    change makes them again (they may be paid), so each is named."""
    before = _code.framework_at(base)
    after = _code.FRAMEWORK if head is None else _code.framework_at(head)
    if before is None or after is None:  # a tree that declares no FRAMEWORK: nothing moved into one
        return []
    paths = sorted(path.relative_to(_code.REPO).as_posix() for path in after - before)
    if not paths:
        return []
    found = subprocess.run(["git", "-C", str(_code.REPO), "diff", "--name-only", base, *([head] if head else []), "--",
                            *paths], capture_output=True, text=True, check=True)
    return sorted(found.stdout.split())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("base")
    parser.add_argument("head", nargs="?", help="a commit (default: the working tree)")
    parser.add_argument("--json", action="store_true", help="every moved row as one JSON object")
    options = parser.parse_args(argv)
    found = moved(options.base, options.head)
    if options.json:
        print(json.dumps(found))
        return
    for name, row in sorted(found.items()):
        why = (["code"] if row["code"] else []) + [f"{path} ({len(places)} places)" for path, places in
                                                   sorted(row["files"].items())]
        print(f"{name}{' (paid)' if row['paid'] else ''}: {', '.join(why)}")
    print(f"{len(found)} rows moved, {sum(row['paid'] for row in found.values())} of them paid")
    for path in edited_into_framework(options.base, options.head):
        print(f"warning: {path} moves into FRAMEWORK and is edited in the same change: the rows that read it are "
              f"made again")


if __name__ == "__main__":
    main()
