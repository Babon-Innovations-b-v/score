"""Where a proposal is kept and how it is read: one layout in the dashboard's home (local mode) and in the state
export (hosted mode), so both sides read it with these functions. Plain files only: no store, no stages.

    <root>/index.json                          [each proposal's summary (SUMMARY), newest first]
    <root>/<branch>/<place>/proposal.json      the proposal
    <root>/<branch>/<place>/web3d/<place>.json, <place>-light.glb, <place>.glb    its 3D web copy (web3d/convert.py)
    <root>/<branch>/<place>/stills/<view>.jpg  small stills from the scene record's cameras
    <root>/<branch>/<place>/before/<view>.jpg  the same cameras on the place as it stands now (finish.py)
    <root>/<branch>/<place>/media/<name>       draft films and sounds the branch made
"""
import json
import pathlib
import re
import shutil

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
FILE = re.compile(r"^(web3d|stills|before|media)/[A-Za-z0-9][A-Za-z0-9._-]{0,159}$")
INDEX = "index.json"
RECORD = "proposal.json"
# How a proposal took each node (assemble.py names the same three; tests/proposals_test.py holds them equal).
AS_NOW, MADE, PAID = "as now", "made", "needs the paid batch"
SUMMARY = ("branch", "place", "commit", "change", "made_at", "needs_paid_batch", "hero", "has_3d")
# The words a department gives its proposal for the owner (`python -m score.dashboard proposal-words`): kept when the
# proposal is made again, so they are never lost to a rerun.
WORDS = ("sentence", "question", "recommended")


class BadName(ValueError):
    """A branch, place or file name a proposal cannot have."""


def checked(name):
    """The name, when it is a plain branch or place name (no path, no dots in front); BadName otherwise."""
    if not NAME.match(name or "") or ".." in name:
        raise BadName(f"{name!r} is not a branch or place name")
    return name


def folder(root, branch, place):
    """The folder of one branch's proposal for one place."""
    return pathlib.Path(root) / checked(branch) / checked(place)


def read(root, branch, place):
    """One proposal, or None."""
    path = folder(root, branch, place) / RECORD
    return json.loads(path.read_text()) if path.is_file() else None


def listing(root):
    """Every proposal's summary, newest first ([] when none is made yet)."""
    path = pathlib.Path(root) / INDEX
    return json.loads(path.read_text()) if path.is_file() else []


def summary(proposal):
    return {field: proposal.get(field) for field in SUMMARY}


def summaries(root):
    """The summary of every proposal.json under `root`, newest first."""
    found = [summary(json.loads(path.read_text())) for path in pathlib.Path(root).glob(f"*/*/{RECORD}")]
    return sorted(found, key=lambda item: item["made_at"] or "", reverse=True)


def write_index(root):
    """Write index.json from the proposals under `root`; its summaries."""
    found = summaries(root)
    partial = pathlib.Path(root) / f"{INDEX}.partial"
    partial.write_text(json.dumps(found, indent=1))
    partial.replace(pathlib.Path(root) / INDEX)
    return found


def put(root, partial, proposal):
    """Swap the finished proposal folder `partial` in for the branch's old one at its place, write its
    proposal.json, then the index; the proposal's folder."""
    target = folder(root, proposal["branch"], proposal["place"])
    (partial / RECORD).write_text(json.dumps(proposal, indent=1))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(target, ignore_errors=True)
    partial.rename(target)
    write_index(root)
    return target


def amend(root, branch, place, fields):
    """Write `fields` into a made proposal's proposal.json (swapped in whole), then the index; the proposal, or None
    when there is none."""
    found = read(root, branch, place)
    if found is None:
        return None
    found.update(fields)
    path = folder(root, branch, place) / RECORD
    partial = path.with_name(f"{RECORD}.partial")
    partial.write_text(json.dumps(found, indent=1))
    partial.replace(path)
    write_index(root)
    return found


def file_path(root, branch, place, name):
    """A proposal's file (web3d/, stills/, before/ or media/), or None when it has no such file."""
    if not FILE.match(name or "") or ".." in name:
        return None
    path = folder(root, branch, place) / name
    return path if path.is_file() else None
