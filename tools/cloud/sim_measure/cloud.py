"""Sim body measure folders (#70) on one rented card machine instead of this PC (owner, 2026-11-04: every sim body
run in the cloud, never on his PC), through level 1's route (tools/cloud/level1/cloud.py: blender_cloud.py's machine
path, kind sim-body-l1, the Newton env): one job that runs each folder's scripts/go.sh in turn on the machine
(on_machine.py), the folders brought back every --bring-every minutes and at its end.

    ~/.farm-factory-props/env/bin/python tools/cloud/sim_measure/cloud.py <folder> [<folder> ...] --who "<session>" \
        [--carry <path> ...] [--minutes 170] [--bring-every 20] [--classes gpu-80gb-x2-48c,...] [--dry-run] [--detach]

Spending: as level 1's, it rents only inside a cleared run (SCORE_SPEND_TICKET, or the owner's spend yes under
`override`); a job past the owner's limits (4 h, EUR 60) is refused. --minutes is the job's; blender_cloud adds its
SETUP_MINUTES, and the go scripts are stopped level1.STOP_EARLY minutes before the job's end so the folders come back.

A measure folder: scripts/go.sh, which skips what its own done markers say is made, runs its jobs `xargs -P ${LANES}`
wide in `${PY}` through the card queue (`${REPO}/tools/cloud/backends/card_queue.py`) and `systemd-run --user
--scope`, with PYTHONPATH `${REPO}` (PY, REPO and LANES set on the machine). A folder's script that names a repo
checkout's path itself is refused before anything is rented (`hard_coded`; 2026-11-04: a go.sh naming the main
checkout's card queue ran from a worktree, whose path alone went up, and every job died in its first second).
- Carried up, at the same absolute paths: the folders, every --carry path (what the go scripts read outside their
  folders), every path a job*.json under those names (level1.named_paths: the targets, the model folders), and this
  repo's REPO_CARRIED (the score package for PYTHONPATH, the card queue, level 1's on_machine.py, which this one runs
  on).
- Brought back: the folders (rsync: only what changed comes).
"""
import argparse
import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent


def loaded(name, path):
    """A module from its file, under its own name (level 1's cloud.py and on_machine.py share their names with ours)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


level1 = loaded("level1_cloud", HERE.parent / "level1" / "cloud.py")
blender_cloud, detached = level1.blender_cloud, level1.detached
LAUNCHER = HERE / "on_machine.py"
REPO_CARRIED = ("score", "tools/cloud/backends", "tools/cloud/level1")
MINUTES = 170  # with blender_cloud's SETUP_MINUTES (8) under three hours
BRING_EVERY = 20


def carried(folders, carries):
    """What the machine reads, each at its path: the folders, the carries, the paths their job*.json files name that
    lie outside them, and REPO_CARRIED."""
    given = [*folders, *carries]
    named = {path for root in given for job in sorted(root.rglob("job*.json")) for path in
             level1.named_paths(level1.json.loads(job.read_text()))}
    outside = {path for path in named if not any(path.is_relative_to(root) for root in given)}
    return [*given, *sorted(outside), *(blender_cloud.REPO / part for part in REPO_CARRIED)]


def checkouts():
    """This repo's path and, when it is a worktree under .claude/worktrees, its main checkout's."""
    repo = blender_cloud.REPO
    main = repo.parents[2] if repo.parent.name == "worktrees" and repo.parents[1].name == ".claude" else repo
    return {repo, main}


def hard_coded(folders):
    """The folders' scripts that name a repo checkout's path instead of ${REPO}."""
    roots = sorted(str(root) for root in checkouts())
    return [script for folder in folders for script in sorted((folder / "scripts").rglob("*")) if script.is_file()
            and any(root in script.read_text(errors="replace") for root in roots)]


STOCK_RANK = {"available": 0, "parked": 0, "scarce": 1}  # any other word (shortage): last


def in_stock_order(classes, found):
    """`classes` with those a zone sells as available first, then scarce, then the rest, each group in the order
    given: blender_cloud fixes one class for the call (batch.one_class_in_stock), and a scarce H100 picked first waited
    hours with the L4 free (2026-11-05)."""
    rank = {name: min((STOCK_RANK.get(offer.stock_word, 2) for offer in found if offer.machine_class == name),
                      default=2) for name in classes}
    return sorted(classes, key=lambda name: rank[name])


def uncarried(folders, carries):
    """The paths the folders' scripts name that exist here but would not go up: under none of the folders or carries
    (2026-11-05: a measure's go.sh read the mean body's clips, never carried, and the job ended at once with 0 of 6)."""
    given = [*folders, *carries]
    named = {pathlib.Path(word.rstrip(";,)}'\"")) for folder in folders
             for script in sorted((folder / "scripts").rglob("*")) if script.is_file()
             for word in re.findall(r"(?<!:-)/(?:home|tmp)/[^\s\"'$]+", script.read_text(errors="replace"))}
    return sorted(str(path) for path in named
                  if path.exists() and not any(path.is_relative_to(root) for root in given))


def job(folders, carries, minutes, bring_every):
    """The one job for blender_cloud.py: on_machine.py in the Newton env over the folders in order."""
    arguments = [*folders, "--minutes", minutes - level1.STOP_EARLY, "--repo", blender_cloud.REPO]
    found = blender_cloud.job_of(LAUNCHER, arguments, carried(folders, carries), folders, minutes, env=level1.ENV)
    return {**found, "bring_every": bring_every}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("folders", type=pathlib.Path, nargs="+", help="measure folders, each with scripts/go.sh")
    parser.add_argument("--who", required=True)
    parser.add_argument("--carry", type=pathlib.Path, action="append", default=[],
                        help="a path the go scripts read outside their folders")
    parser.add_argument("--minutes", type=float, default=MINUTES, help="the job's minutes")
    parser.add_argument("--bring-every", type=float, default=BRING_EVERY)
    parser.add_argument("--classes", default=",".join(level1.CLASSES))
    parser.add_argument("--dry-run", action="store_true", help="price the job, rent nothing")
    parser.add_argument(detached.FLAG, action="store_true", help="progress to a log, one result line at the end")
    options = parser.parse_args()
    folders = [folder.resolve() for folder in options.folders]
    if options.detach:
        detached.relaunch(sys.argv, "sim-measure-cloud", folders)
    lacking = [str(folder) for folder in folders if not (folder / "scripts" / "go.sh").is_file()]
    if lacking:
        raise SystemExit(f"no scripts/go.sh in {', '.join(lacking)}")
    written = hard_coded(folders)
    if written:
        raise SystemExit(f"a repo path written in {', '.join(map(str, written))}: name it from ${{REPO}}, set on the "
                         "machine to the carried repo")
    left = uncarried(folders, [carry.resolve() for carry in options.carry])
    if left:
        raise SystemExit(f"the scripts read {', '.join(left)}, which would not go up: --carry it")
    folder = folders[0] / "cloud"
    folder.mkdir(exist_ok=True)
    path = folder / f"{level1.time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(level1.json.dumps(job(folders, [carry.resolve() for carry in options.carry], options.minutes,
                                          options.bring_every), indent=1))
    asked = options.classes.split(",")
    classes = in_stock_order(asked, blender_cloud.batch.offers(asked))
    command = [str(blender_cloud.cloud_python()), str(blender_cloud.HERE / "blender_cloud.py"), str(path), "--who",
               options.who, "--classes", ",".join(classes), "--kind", level1.KIND,
               *(["--dry-run"] if options.dry_run else [])]
    sys.exit(level1.subprocess.run(command).returncode)


if __name__ == "__main__":
    main()
