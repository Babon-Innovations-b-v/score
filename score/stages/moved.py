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

The push gate (`python -m score moved [--pre-push]`, .claude/hooks/local/pre-push-moved) asks the dearer question of every world:
which paid rows with an accepted output a drive would buy again (rebuy.buys), each at its price and why.

    found = moved.rebuys(runner, nodes)          # [rebuy.Buy] of the re-buys, priced
    moved.listing({"world1": found})             # the lines `score moved` prints, with the total
    pushes = moved.main_pushes(push_lines)       # (local sha, remote sha) of each push line to main, deletions left out
    base = moved.base_rebuys(remote)             # {world: [node]} re-bought at main's commit; None when unknown
    pushed, drift = moved.split(found_by_world, base)   # rows this push moves; drift already on main
    moved.unexplained(pushed, moved.pushed_reasons(pushes))   # the paid rows no "Moved-rows:" trailer names

A push moves a row when the pushed commit would buy it again and main's commit (the remote's sha, worked out in a
checkout of its own) would not, whatever moved its key: code, a declared file, or the stage table's params,
contract, models and after, which no file of the row's own names. Rows main already re-buys print as a warning.
When main's commit cannot be worked out (a new ref, a commit not here, one from before the stage table it runs),
every moved row counts as the push's: the gate fails closed. A pushed row goes when a pushed commit's "Moved-rows:
<node> ...: <reason>" trailer lists it before the colon and gives a reason. A row priced EUR 0 (a Google ask its
cache answers) is listed, never
refused. The price is the row's estimate (Stage.euros). Why: about EUR 65 of re-buys (view maps, turntables, the
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
SNAPSHOT = """import json, pathlib, sys
sys.path.insert(0, ".")
from score import graph, stages
from score.graph import _code
from score.store import file_hash, listing_hash, text_hash
runner = stages.runner(world=stages.WORLDS["world1"]())
places = stages.places(runner.world)
if not places:  # every place row would declare nothing, so none could move by a declared file (2026-10-28)
    sys.exit(f"moved: the home {stages.PROPS_HOME} holds no place: run it with PROPS_HOME the run's home")
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


REBUYS = """import json, sys
sys.path.insert(0, ".")
from score import stages
from score.graph import rebuy
found = {}
for name, make in sorted(stages.WORLDS.items()):
    runner = stages.runner(world=make())
    nodes = runner.line_nodes(stages.places(runner.world), True)
    found[name] = [buy.node for buy in rebuy.buys(runner, nodes) if buy.again]
print(json.dumps(found))"""
TRAILER = "Moved-rows"
MOVED_EXIT = 3
ZERO = "0" * 40
MAIN = "refs/heads/main"


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


def base_rebuys(remote):
    """{world: [node]} of the rows main's commit `remote` would buy again, worked out in a checkout of it; None when
    it cannot be (a new ref, a commit not here, a tree whose stage table does not run the check)."""
    if remote == ZERO:
        return None
    try:
        return snapshot(remote, REBUYS)
    except subprocess.CalledProcessError:
        return None


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


def named_in(node, reasons):
    """True when a trailer value lists the node among its nodes, with a reason ("render@hangar: why", not
    "render@hangar2: why", "render@hangar" alone, nor "film@hangar: it reads render@hangar")."""
    return any(node in trailer_nodes(reason) for reason in reasons)


def split(rows_by_world, base):
    """({world: rows the push moved}, {world: rows main's commit buys again too}); with `base` None (main's commit
    not worked out) every row counts as moved by the push."""
    known = base or {}
    pushed = {world: [row for row in rows if base is None or row.node not in known.get(world, [])]
              for world, rows in rows_by_world.items()}
    drift = {world: [row for row in rows if base is not None and row.node in known.get(world, [])]
             for world, rows in rows_by_world.items()}
    return pushed, drift


def unexplained(pushed, reasons):
    """{world: rows} of the pushed rows that cost money and that no Moved-rows trailer names."""
    return {world: [row for row in rows if row.euros > 0 and not named_in(row.node, reasons)]
            for world, rows in pushed.items()}


def tree_is_at(commit):
    """True when this repository's checkout is `commit` with nothing changed or untracked: what is checked is what
    is pushed."""
    head = git_lines("rev-parse", "HEAD")
    return head == [git_lines("rev-parse", commit)[0]] and not git_lines("status", "--porcelain")


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
