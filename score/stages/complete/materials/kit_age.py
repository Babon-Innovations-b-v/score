"""Kit bakes older than the bake code that made them: a place's kit pieces come into its assembly from its seed (the
audit of 2026-10-18: still the 10-10 bake), so a later change to the kit bake code reaches no place until its kit is
baked again.

Measured: each kit piece the place lays (an inventory row made as a "kit piece"), its route (a code-built kind is
baked by tools/props/library/inside/make_kit.py, a generated one by make_chunky.py) and the latest time its bake can
have been made: the commit that first released its file in the environment's asset manifest, else the time its file was
written as the seed recorded it (inputs.json). Both come after the bake itself, so a piece older than a code change by
them is older for certain. A piece the surface line repainted (score:repaint_of) is the runner's own, keyed by its
code, and is left out. The bake code is each route's script and the files it imports (`bake_files`), less the piece
builders, which are the pieces' shapes rather than their bake (BODIES). Judged: the kit pieces of one route baked
before a commit to its bake code are one finding a place, naming the commits since.
"""
import datetime
import functools
import json
import pathlib
import subprocess

from score.graph import _code

RULE = "kit baked before its bake code"
REPO = pathlib.Path(__file__).resolve().parents[4]
INSIDE = REPO / "tools/props/library/inside"
ROUTES = {"code": INSIDE / "make_kit.py", "generate": INSIDE / "make_chunky.py"}
ROUTE_WORDS = {"code": "code-built", "generate": "generated"}
# Where a route's bare imports are found when it runs (inside/runtime.py's PATHS, the repository's own).
FOLDERS = (INSIDE, INSIDE.parent)
BODIES = {"pieces.py", "pieces_ship.py", "pieces_earth.py", "shapes.py"}
MANIFEST = "data/assets/world1.json"


def bake_files(script):
    """The route script and every repository file it imports, followed import by import, less the piece builders."""
    pending, found = [pathlib.Path(script)], set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        found.add(path)
        for name in _code.imported_names(path.read_text(), path, ""):
            pending += [folder / f"{name}.py" for folder in FOLDERS if (folder / f"{name}.py").is_file()]
    return sorted(path for path in found if path.name not in BODIES)


def git(*arguments):
    """A git command's output in the repository."""
    return subprocess.run(["git", "-C", str(REPO), *arguments], capture_output=True, text=True, check=True).stdout


@functools.cache
def code_commits(route):
    """[{commit, at, subject}] of every commit to a route's bake code, newest first (committed time)."""
    relatives = [path.relative_to(REPO).as_posix() for path in bake_files(ROUTES[route])]
    lines = git("log", "--format=%h%x09%cI%x09%s", "--", *relatives).splitlines()
    return [dict(zip(("commit", "at", "subject"), line.split("\t", 2))) for line in lines if line]


@functools.cache
def released_at(sha256):
    """When the environment's asset manifest first named a file of this hash (its commit's time), or None."""
    found = git("log", "--reverse", "--format=%cI", "-S", sha256, "--", MANIFEST).split()
    return found[0] if found else None


def written_at(entry):
    """The time a seed's model file was written, from its recorded mtime (nanoseconds)."""
    return datetime.datetime.fromtimestamp(entry["mtime"] / 1e9, datetime.timezone.utc).isoformat(timespec="seconds")


def baked_by(entry):
    """(latest time the model's bake was made, how that is known) of a seed's model record, or (None, why)."""
    if not entry:
        return None, "its seed records no file for it"
    released = released_at(entry["sha256"]) if entry.get("sha256") else None
    if released:
        return released, "released in the world's asset manifest"
    if entry.get("mtime"):
        return written_at(entry), f"its file written ({pathlib.Path(entry['file']).name})"
    return None, "its seed records no time for it"


def kit_models(objects, rows, seed_models):
    """[{model, prims, route, baked_by, known_by}] of the place's kit pieces the surface line did not repaint."""
    found = {}
    for entry in objects:
        row = rows.get(entry["row"], {})
        if row.get("made") != "kit piece" or row.get("kind") not in ROUTES or entry["repainted"]:
            continue
        kept = found.setdefault(entry["model"], {"model": entry["model"], "prims": [], "route": row["kind"]})
        kept["prims"].append(entry["prim"])
    for model in found.values():
        model["baked_by"], model["known_by"] = baked_by(seed_models.get(model["model"]))
    return sorted(found.values(), key=lambda model: model["model"])


def later(commits, moment):
    """The commits made after a moment (ISO times, any offset)."""
    when = datetime.datetime.fromisoformat(moment)
    return [commit for commit in commits if datetime.datetime.fromisoformat(commit["at"]) > when]


def sentence(route, stale, since):
    """A finding in words."""
    oldest = min(model["baked_by"] for model in stale)[:10]
    newest = since[0]
    many = len(stale) > 1
    return (f"{len(stale)} {ROUTE_WORDS[route]} kit piece{'s were' if many else ' was'} baked on or before "
            f"{oldest} and the kit bake code changed in {len(since)} commit{'s' if len(since) > 1 else ''} since "
            f"(the latest {newest['at'][:10]} {newest['commit']}: {newest['subject'][:90]})")


def findings(evidence):
    """One finding a route whose kit pieces in this place were baked before a commit to its bake code."""
    found = []
    for route in ROUTES:
        commits = evidence["bake_code"].get(route, [])
        stale = [model for model in evidence["kit"] if model["route"] == route and model["baked_by"]
                 and later(commits, model["baked_by"])]
        if not stale:
            continue
        since = later(commits, min(model["baked_by"] for model in stale))
        found.append({"rule": RULE, "prim": stale[0]["prims"][0], "route": route,
                      "models": [model["model"] for model in stale], "commits": [commit["commit"] for commit in since],
                      "sentence": sentence(route, stale, since)})
    return found
