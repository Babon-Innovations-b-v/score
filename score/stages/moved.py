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
refusal over EUR 5). The push gate asks only the cheap one (owner, 2026-11-07: "shouldnt the rebuy check just be
before a buy"; the dearer one took 15 to 20 minutes a push): `python -m score moved --pre-push`
(.claude/hooks/local/pre-push-moved) refuses a push to main whose commit moves a paid row of any world (by its code,
its stage table part or a declared file, against main's commit, the remote's sha) unless a pushed commit's
"Moved-rows: <row or node> ...: <reason>" trailer names it; main's commit unknown (a new ref) refuses.

    found = moved.rebuys(runner, nodes)          # [rebuy.Buy] of the re-buys, priced
    moved.listing({"world1": found})             # the lines `score moved` prints, with the total
    pushes = moved.main_pushes(push_lines)       # (local sha, remote sha) of each push line to main, deletions left out
    found = moved.moved(remote)                  # every row the working tree moves against main's commit
    moved.unnamed_paid(found, moved.pushed_reasons(pushes))   # the paid rows no "Moved-rows:" trailer names

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

from score.graph import _code

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
TRAILER = "Moved-rows"
MOVED_EXIT = 3
ZERO = "0" * 40
MAIN = "refs/heads/main"


def row_name(world, row):
    """A row's name in a snapshot: its own in environment 1, `<world>:<row>` in another (the images world)."""
    return row if world == "world1" else f"{world}:{row}"


def row_entry(runner, row, places, repo):
    """{"paid", "declared": {place: {repository path: its key}}, "code": its code version, "table": the hash of what
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
    return {"paid": bool(row.paid), "declared": declared, "table": text_hash(json.dumps(table, sort_keys=True,
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
    holder = pathlib.Path(tempfile.mkdtemp(prefix="moved-", dir=REPO.parent))
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


def rebuys(runner, nodes):
    """[rebuy.Buy] of every paid node among `nodes` that has an accepted output and that a drive would buy again."""
    return [buy for buy in rebuy.buys(runner, nodes) if buy.again]


def total(rows_by_world):
    """The euros of every moved row in every world."""
    return sum(row.euros for rows in rows_by_world.values() for row in rows)


def listing(rows_by_world, what="paid rows with an accepted output this tree would buy again"):
    """The lines `score moved` prints: the count and total, then each row with its price and why it moved."""
    count = sum(len(rows) for rows in rows_by_world.values())
    lines = [f"moved rows: {count} {what}, about EUR {total(rows_by_world):.2f}"]
    for world, rows in rows_by_world.items():
        lines += [f"  {world} {row.node}: EUR {row.euros:.2f}, {row.why}" for row in rows]
    return "\n".join(lines)


def main_pushes(push_lines):
    """(local sha, remote sha) of each of git's pre-push lines ("<local ref> <local sha> <remote ref> <remote sha>")
    that updates main; a deletion (local sha all zeros), a tag and any other branch are left out."""
    words = [line.split() for line in push_lines if line.strip()]
    return [(local, remote) for _, local, ref, remote in words if ref == MAIN and local != ZERO]


def git_lines(*words):
    """The non-empty output lines of a git command run in this repository."""
    found = subprocess.run(["git", "-C", str(REPO), *words], capture_output=True, text=True, check=True)
    return [line.strip() for line in found.stdout.splitlines() if line.strip()]


def pushed_commits(local, remote):
    """The commits a push of `local` over `remote` sends: those after the remote's commit, or for a new remote ref
    those on no remote yet."""
    return git_lines("rev-list", *([local, "--not", "--remotes"] if remote == ZERO else [f"{remote}..{local}"]))


def trailer_reasons(commit):
    """The non-empty "Moved-rows: <...>" trailer values of one commit's message."""
    return git_lines("log", "-1", f"--format=%(trailers:key={TRAILER},valueonly)", commit)


def pushed_reasons(pushes):
    """Every Moved-rows trailer value carried by a commit the pushes send."""
    return [reason for push in pushes for commit in pushed_commits(*push) for reason in trailer_reasons(commit)]


def trailer_nodes(reason):
    """The nodes a trailer value "<node> ...: <reason>" lists before its colon (spaces or commas between them); none
    when it gives no reason."""
    listed, colon, why = reason.partition(":")
    return set(listed.replace(",", " ").split()) if colon and why.strip() else set()


def row_named(row, reasons):
    """True when a trailer value lists the row, with a reason: by its name (an environment's prefix,
    "images:", left off or not) or a node of it ("bake@hangar: why" names bake, "bake2@hangar: why", "bake" alone
    with no reason, nor "film: it reads bake" do not)."""
    names = {row, row.rpartition(":")[2]}
    return any(node in names or node.partition("@")[0] in names for reason in reasons
               for node in trailer_nodes(reason))


def unnamed_paid(found, reasons):
    """The paid rows of `found` (moved's answer) no Moved-rows trailer names, sorted."""
    return sorted(name for name, row in found.items() if row["paid"] and not row_named(name, reasons))


def tree_is_at(commit):
    """True when this repository's checkout is `commit` with nothing changed or untracked: what is checked is what
    is pushed."""
    head = git_lines("rev-parse", "HEAD")
    return head == [git_lines("rev-parse", commit)[0]] and not git_lines("status", "--porcelain")


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
