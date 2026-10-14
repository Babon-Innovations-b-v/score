"""Which rows a change moves, before it is pushed: a row moves when its code version differs, or when a repository
file it declares (Stage.files: "blender runner": blender_cloud.py, a data folder) holds a changed path. A code-only
check missed the second (8b402226, 2026-10-14: blender_cloud.py is outside every code version, yet the turntable rows
declare it, and every place's turntable was rendered again).

    .venv/bin/python -m score.stages.moved <base> [<head>]     # head: a commit, default the working tree

Prints each moved row (paid marked), why, and for a declared file the places it moves in.
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT = """import json, pathlib, sys
sys.path.insert(0, ".")
from score import graph, stages
from score.graph import _code
from score.store import file_hash, listing_hash
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
        paths = []
        for name in names:
            path = runner.file_path(row, name, place).resolve()
            if path.is_relative_to(repo):
                paths.append(path.relative_to(repo).as_posix())
        declared[str(place)] = sorted(set(paths))
    found[row.name] = {"paid": bool(row.paid), "declared": declared,
                       "code": listing_hash(_code.code_version(graph.code_functions(row), file_hash))}
print(json.dumps(found))"""


def snapshot_here(folder):
    """{row: {"paid", "code", "declared": {place: [repository paths]}}} as the tree at `folder` works it out."""
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


def changed_paths(base, head):
    """The repository paths that differ from `base` to `head` (the working tree when None)."""
    span = [base] if head is None else [base, head]
    return subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", *span], capture_output=True, text=True,
                          check=True).stdout.split()


def holds(declared, changed):
    """True when a declared repository file or folder is or holds a changed path."""
    return changed == declared or changed.startswith(declared.rstrip("/") + "/")


def moved(base, head=None):
    """{row: {"paid", "code": its code version moved, "files": {changed path: [places]}}} of every row the change
    from `base` to `head` moves, by its code or by a file it declares."""
    before, after = snapshot(base), snapshot(head)
    changed = changed_paths(base, head)
    found = {}
    for name, row in after.items():
        code = name not in before or before[name]["code"] != row["code"]
        files = {}
        for place, paths in row["declared"].items():
            for path in changed:
                if any(holds(declared, path) for declared in paths):
                    files.setdefault(path, []).append(place)
        if code or files:
            found[name] = {"paid": row["paid"], "code": code, "files": files}
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("base")
    parser.add_argument("head", nargs="?", help="a commit (default: the working tree)")
    options = parser.parse_args(argv)
    found = moved(options.base, options.head)
    for name, row in sorted(found.items()):
        why = (["code"] if row["code"] else []) + [f"{path} ({len(places)} places)" for path, places in
                                                   sorted(row["files"].items())]
        print(f"{name}{' (paid)' if row['paid'] else ''}: {', '.join(why)}")
    print(f"{len(found)} rows moved, {sum(row['paid'] for row in found.values())} of them paid")


if __name__ == "__main__":
    main()
