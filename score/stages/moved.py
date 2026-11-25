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

`python -m score moved` asks the dearer question of every world: which paid rows with an accepted output a drive
would buy again (rebuy.buys, scratch remakes), each at its price and why; a run asks it before it starts (rebuy.py's
refusal over EUR 5). Neither is asked at a push (owner, 2026-11-16: the push-time check was removed).

    found = moved.rebuys(runner, nodes)          # [rebuy.Buy] of the re-buys, priced
    moved.listing({"world1": found})             # the lines `score moved` prints, with the total
    found = moved.moved(base)                    # every row the working tree moves against `base`

Why: about EUR 65 of re-buys (view maps, turntables, the
cockpit library push) came from code and data changes nobody saw would move a paid row's key, 2026-10-17.
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

from score.graph import _code, node_name

from score.graph import rebuy

REPO = pathlib.Path(__file__).resolve().parents[2]
SNAPSHOT = """import contextlib, importlib.util, json, pathlib, sys
sys.path.insert(0, ".")
from score import stages
spec = importlib.util.spec_from_file_location("moved_now", %r)  # this tree's row_entry, whichever tree is snapshot
now = importlib.util.module_from_spec(spec)
spec.loader.exec_module(now)
repo = pathlib.Path(".").resolve()
tables = getattr(stages, "TABLES", {})
found = {}
for world, make in sorted(getattr(stages, "WORLDS", {"world1": stages.world1}).items()):
    runner = stages.runner(world=make())
    with getattr(runner, "still", contextlib.nullcontext)():  # each node's files worked out once a run, not once a
        # path (files_of outside a pass listed them again for every file_path: 19 min, 2026-11-06), the places too
        places = stages.places(runner.world)
        if world == "world1" and not places:  # no place row could move by a declared file (2026-10-28)
            sys.exit(f"moved: the home {stages.PROPS_HOME} holds no place: run it with PROPS_HOME the run's home")
        for row in tables.get(world, stages.STAGES):
            found[now.row_name(world, row.name)] = now.row_entry(runner, row, places, repo)
print(json.dumps(found))""" % str(pathlib.Path(__file__).resolve())
MOVED_EXIT = 3


def row_name(world, row):
    """A row's name in a snapshot: its own in environment 1, `<world>:<row>` in another (the images world)."""
    return row if world == "world1" else f"{world}:{row}"


def row_entry(runner, row, places, repo):
    """{"paid", "euros": its estimate (0 for a free row), "declared": {place: {repository path: its key}}, "code": its code version, "table": the hash of what
    the stage table gives its key (contract, params, after, beside, models; Runner.own_parts)}: one row of a snapshot.
    The table part moves a row whose own files did not change (a params edit in the framework's table)."""
    from score import graph
    from score.store import file_hash, listing_hash, text_hash
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
    table = {"contract": row.contract.stamp_of(), "params": runner.params_of(row), "after": row.after,
             "beside": row.beside, "models": {kind: runner.model_record(kind) for kind in row.models}}
    euros = row.euros if row.paid and isinstance(row.euros, (int, float)) else 0
    return {"paid": bool(row.paid), "euros": euros, "declared": declared, "table": text_hash(json.dumps(table, sort_keys=True,
                                                                                         default=str)),
            "code": listing_hash(_code.code_version(graph.code_functions(row), file_hash))}


def snapshot_here(folder, script=SNAPSHOT):
    """What `script` prints last, as JSON, run by the tree at `folder` (SNAPSHOT: {row: {"paid", "code", "declared":
    {place: {repository path: its key}}}})."""
    done = subprocess.run([sys.executable, "-c", script], cwd=folder, capture_output=True, text=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if done.returncode:
        print(done.stderr.strip(), file=sys.stderr)  # the reason, which the error alone does not show
        raise subprocess.CalledProcessError(done.returncode, done.args, done.stdout, done.stderr)
    return json.loads(done.stdout.strip().splitlines()[-1])


def snapshot(commit, script=SNAPSHOT):
    """The snapshot of a commit, in a checkout of its own (removed, with its folder, whatever happened); of the
    working tree when `commit` is None."""
    if commit is None:
        return snapshot_here(REPO, script)
    holder = pathlib.Path(tempfile.mkdtemp(prefix="moved-"))
    folder = holder / "tree"
    try:
        subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", str(folder), commit],
                       check=True, capture_output=True)
        try:
            return snapshot_here(folder, script)
        finally:
            subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", str(folder)], check=True)
    finally:
        shutil.rmtree(holder)


def moved(base, head=None):
    """{row: {"paid", "code": its code version moved, "files": {declared path: [places]}, "places": [every place it
    is declared at]}} of every row the change from `base` to `head` moves, by its code or by a file it declares that
    keys differently (or is newly declared or no longer)."""
    return moved_rows(snapshot(base), snapshot(head))


def moved_rows(before, after):
    """moved()'s answer from two snapshots: a row moves by its code version, its stage table part or a declared
    file's key (its code marked for the first two)."""
    found = {}
    for name, row in after.items():
        code = (name not in before or before[name]["code"] != row["code"]
                or before[name].get("table") != row.get("table"))
        files = {}
        for place, keys in row["declared"].items():
            earlier = before.get(name, {}).get("declared", {}).get(place, {})
            for path in sorted(set(keys) | set(earlier)):
                if keys.get(path) != earlier.get(path):
                    files.setdefault(path, []).append(place)
        if code or files:
            found[name] = {"paid": row["paid"], "euros": row.get("euros", 0), "code": code, "files": files,
                           "places": sorted(row["declared"])}
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


def rebuys(runner, nodes, kept=None):
    """[rebuy.Buy] of every paid node among `nodes` that has an accepted output and that a drive would buy again;
    `kept`, a set given, gets each paid node among them whose key moved but which a drive keeps as it is (rebuy.KEPT:
    a phase lock, a proof, a content carry), so `score moved` says apart what would truly change and what is only
    re-keyed (#107)."""
    held = set()
    found = [buy for buy in rebuy.buys(runner, nodes, held) if buy.again]
    if kept is not None:
        paid = {node_name(stage, place) for stage, place in nodes if stage.paid}
        kept.update(paid & held)
    return found


def total(rows_by_world):
    """The euros of every moved row in every world."""
    return sum(row.euros for rows in rows_by_world.values() for row in rows)


def listing(rows_by_world, what="paid rows with an accepted output this tree would buy again", kept_by_world=None):
    """The lines `score moved` prints: the count and total, then each row with its price and why it moved; with
    `kept_by_world` ({world: paid nodes re-keyed only, rebuys' `kept`}), then those, which a drive keeps as they are."""
    count = sum(len(rows) for rows in rows_by_world.values())
    lines = [f"moved rows: {count} {what}, about EUR {total(rows_by_world):.2f}"]
    for world, rows in rows_by_world.items():
        lines += [f"  {world} {row.node}: EUR {row.euros:.2f}, {row.why}" for row in rows]
    if kept_by_world is not None:
        lines.append(f"re-keyed only: {sum(len(nodes) for nodes in kept_by_world.values())} paid rows whose key moved, "
                     "kept as they are (a phase lock, a proof or the same content)")
        lines += [f"  {world} {node}" for world, nodes in kept_by_world.items() for node in sorted(nodes)]
    return "\n".join(lines)


def moved_listing(found):
    """moved()'s answer as lines: each moved row (paid marked) and why, then the count."""
    lines = []
    for name, row in sorted(found.items()):
        why = (["code"] if row["code"] else []) + [f"{path} ({len(places)} places)" for path, places in
                                                   sorted(row["files"].items())]
        lines.append(f"{name}{' (paid)' if row['paid'] else ''}: {', '.join(why)}")
    lines.append(f"{len(found)} rows moved, {sum(row['paid'] for row in found.values())} of them paid")
    return "\n".join(lines)


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
    print(moved_listing(found))
    for path in edited_into_framework(options.base, options.head):
        print(f"warning: {path} moves into FRAMEWORK and is edited in the same change: the rows that read it are "
              f"made again")


if __name__ == "__main__":
    main()
