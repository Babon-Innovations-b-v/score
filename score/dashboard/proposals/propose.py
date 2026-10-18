"""The propose command: one fix branch's proposal for one place, made for free on this machine.

    .venv/bin/python -m score.dashboard propose <branch> <place> [--media DIR] [--no-stills]

The rows the branch moves come from score.stages.moved (its merge base with main against its newest commit). The
branch is checked out in a scratch folder and assemble.py runs there, on the branch's own code and data over the
store's accepted outputs, read only; its scratch store sits in the dashboard's home (proposals-work/store) and is kept
across runs, so a rerun on the same commit makes nothing again. Then the 3D web copy (web3d/convert.py), the stills
(pictures.py) and the branch's draft films and sounds (DIR/<branch>/, default $SCORE_PROPOSAL_MEDIA) go into the
proposal's folder (records.py), swapped in whole; then finish.py prices its paid part and draws the same cameras on
the place as it stands now. The words a department gave it (records.WORDS) are kept. Nothing is bought, nothing in
the store is written.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

from score.dashboard.checkout import pricing
from score.dashboard.proposals import branch as branch_git
from score.dashboard.proposals import drawing, finish, pictures, records
from score.dashboard.web3d import convert

REPO = pathlib.Path(__file__).resolve().parents[3]
WORK = "proposals-work"
ASSEMBLE = pathlib.Path(__file__).with_name("assemble.py")
THREADS = "4"
# Run with the branch's checkout first on the path: assemble.py is loaded by its file, so the `score` it imports
# is the branch's.
LAUNCH = ("import importlib.util, sys; sys.path[0:0] = [sys.argv[1]]; "
          "spec = importlib.util.spec_from_file_location('score_proposal_assemble', sys.argv[2]); "
          "module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); module.main(sys.argv[3:])")
MOVED = ("import json, sys; from score.stages import moved; "
         "print(json.dumps(moved.moved(sys.argv[1], sys.argv[2])))")


class Refused(Exception):
    """A proposal that cannot be made, in words."""


def moved_rows(since, commit):
    """{row: {paid, code, files}} of every row the commits from `since` to `commit` move (score.stages.moved)."""
    done = subprocess.run([sys.executable, "-c", MOVED, since, commit], cwd=REPO, capture_output=True, text=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if done.returncode != 0:
        raise RuntimeError(f"the moved-rows check failed: {done.stderr[-2000:]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def assembled(tree, place, real_store, work, job, moved):
    """assemble.py's result for the place, run in the branch's checkout `tree` over the scratch store in `work`
    (shared by every proposal), its own files in `job` (its stage linked into job/stage/)."""
    stage_folder = job / "stage"
    shutil.rmtree(stage_folder, ignore_errors=True)
    job.mkdir(parents=True, exist_ok=True)
    (job / "moved.json").write_text(json.dumps(moved))
    command = [sys.executable, "-c", LAUNCH, str(tree), str(ASSEMBLE), "--place", place, "--store",
               str(real_store), "--scratch", str(work / "store"), "--moved", str(job / "moved.json"),
               "--out", str(job / "result.json"), "--folder", str(stage_folder)]
    environment = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "OMP_NUM_THREADS": THREADS}
    with open(job / "assemble.log", "w") as log:
        done = subprocess.run(command, cwd=tree, stdout=log, stderr=subprocess.STDOUT, env=environment)
    if done.returncode != 0:
        raise RuntimeError(f"assembling {place} on the branch failed; its log: {job / 'assemble.log'}")
    return json.loads((job / "result.json").read_text())


def web_copy(place, stage_file, partial, views, origin):
    """The stage's 3D web copy into partial/web3d/; the sidecar's facts the proposal keeps, or {"error": why} when
    the copy cannot be made (a place with its neighbours can pass glTF's 2 GB), said on the proposal."""
    try:
        sidecar = convert.write_copies(place, pathlib.Path(stage_file).parent, partial, origin,
                                       [{key: view[key] for key in ("name", "eye", "aim", "fov")} for view in views])
    except (RuntimeError, ValueError, OverflowError) as failed:
        return {"error": str(failed)[-1000:]}
    (partial / place).rename(partial / "web3d")
    return {"triangles": sidecar["triangles"], "bytes": sidecar["bytes"], "light_bytes": sidecar["light_bytes"],
            "files": {"sidecar": f"web3d/{place}.json", "light": f"web3d/{place}-light.glb",
                      "whole": f"web3d/{place}.glb"}}


def still_pictures(stage_file, drawn, partial):
    """The stills into partial/stills/, or [{"error": why}] when Blender could not draw them (said on the page)."""
    try:
        return pictures.stills(pathlib.Path(stage_file), drawn, partial / "stills")
    except RuntimeError as failed:
        return [{"error": str(failed)[-1000:]}]


def drawing_for(tree, place, assembled_now, moved, job):
    """The proposal's drawing (drawing.py): the branch's own cameras, its film plan where it moves the film, and the
    assembled stage's time span; a film plan that fails is said on the drawing and the rest is drawn."""
    stage_file = pathlib.Path(assembled_now["stage"])
    try:
        film, film_error = pictures.film_views(tree, place, moved, job), None
    except RuntimeError as failed:
        film, film_error = [], str(failed)[-600:]
    planned = drawing.plan(assembled_now["taken"], pictures.record_views(stage_file.parent, tree, place), film,
                           pictures.time_span(stage_file))
    return {**planned, "film_error": film_error} if film_error else planned


def proposal_record(found, assembled_now, pictured, started):
    """The proposal.json of a made proposal: `found` the branch's facts, `assembled_now` assemble.py's result,
    `pictured` its web copy, stills and media."""
    taken = assembled_now["taken"]
    return {**found, "made_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "seconds": round(time.monotonic() - started, 1),
            "target": assembled_now.get("target"), "assembly": assembled_now["assembly"],
            "blocked": assembled_now.get("blocked"),
            "layers": taken,
            "made": sorted({item["stage"] for item in taken if item["how"] == records.MADE}),
            "needs_paid_batch": sorted({item["stage"] for item in taken if item["how"] == records.PAID}),
            **pictured, "has_3d": bool(pictured["web3d"]) and "error" not in pictured["web3d"],
            "hero": next((still["file"] for still in pictured["stills"] if "file" in still), None)}


def branch_facts(branch, place):
    """The branch's commit, base, commits and one-sentence change; Refused when it adds nothing over main."""
    commit = branch_git.tip(REPO, branch)
    since = branch_git.base(REPO, commit)
    listed = branch_git.commits(REPO, since, commit)
    if not listed:
        raise Refused(f"{branch} has no commits past main: nothing to propose")
    return {"branch": branch, "place": place, "commit": commit, "base": since, "commits": listed,
            "change": branch_git.change_sentence(listed)}


def pictured(tree, place, assembled_now, partial, drafts, with_stills, moved, job):
    """The proposal's drawing, 3D web copy, stills and media (the branch's own drafts folder, or None) into
    `partial`."""
    made = assembled_now["assembly"] is not None
    drawn = drawing_for(tree, place, assembled_now, moved, job) if made else None
    cameras = [view for view in (drawn or {}).get("views", []) if "frame" not in view]
    origin = {"from_output": assembled_now["assembly"], "proposal": True}
    return {"drawing": drawn,
            "web3d": web_copy(place, assembled_now["stage"], partial, cameras, origin) if made else None,
            "stills": still_pictures(assembled_now["stage"], drawn, partial) if made and with_stills else [],
            "media": pictures.media(drafts, place, partial / "media")}


def propose(branch, place, home, real_store, drafts=None, with_stills=True):
    """Make and keep the branch's proposal for the place; its folder."""
    started = time.monotonic()
    found = branch_facts(records.checked(branch), records.checked(place))
    root = pathlib.Path(home) / "proposals"
    work = pathlib.Path(home) / WORK
    root.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    moved = moved_rows(found["base"], found["commit"])
    found["moved_rows"] = [{"row": name, "paid": row["paid"]} for name, row in sorted(moved.items())]
    found["moved_paid"] = pricing.paid_nodes(moved)
    partial = pathlib.Path(tempfile.mkdtemp(prefix=f".{branch}@{place}-", dir=root))
    try:
        with branch_git.scratch_tree(REPO, found["commit"], work / "trees") as tree:
            job = work / "jobs" / f"{branch}@{place}"
            assembled_now = assembled(tree, place, real_store, work, job, moved)
            shown = pictured(tree, place, assembled_now, partial, pathlib.Path(drafts) / branch if drafts else None,
                             with_stills, moved, job)
        words = {field: value for field, value in (records.read(root, branch, place) or {}).items()
                 if field in records.WORDS}
        records.put(root, partial, {**proposal_record(found, assembled_now, shown, started), **words})
    finally:
        shutil.rmtree(partial, ignore_errors=True)
    finish.finish(root, branch, place, real_store, with_stills)
    return records.folder(root, branch, place)
