"""GEM-X Body Motion (NVlabs/GEM-X, the newest upstream release) on OpenCap LabValidation's videos, on rented cards
(#98), through blender_cloud.py's machine path (the owner's limits, the clearance, the watchdog, the self-delete, the
delete and the ledger are its and batch.py's): one job a trial, its cameras in turn (on_machine.py), in the Python
gemx_env.sh builds on the machine, kind `gemx` (capacity.py: one card, an L4 first).

    ~/.farm-factory-props/env/bin/python tools/cloud/gemx/cloud.py <LabValidation root> <out> --who "<session>" \
        [--cameras Cam1[,Cam2...]] [--subjects subject2,...] [--trials 'walking*,...'] \
        [--classes gpu-24gb,...] [--dry-run] [--detach]

<LabValidation root> is SimTK's release as it unpacks (the public OpenCap LabValidation dataset, healthy subjects):
<root>/<subject>/VideoData/<session>/<camera>/<trial>/<trial>.avi (or .mp4), or SCORE's store copy's
<root>/<subject>/<camera>/<trial>.mp4 (cluster.py --fetch-to writes it); the extrinsics trials (a checkerboard,
no person) are left out. Each trial comes back to <out>/<subject>/<trial>/<camera>/ (on_machine.py says what is in
it); a camera with its done.json there is not asked again, and a trial with every asked camera done is no job. The
job files are written to <out>/jobs/.

Spending: it rents only inside a cleared run (SCORE_SPEND_TICKET, or the owner's spend yes under `override`), as every
renting call. --dry-run checks and prices the call and rents nothing. The minutes a job are an estimate
(VIDEO_MINUTES a video) until a batch measured them: each done.json carries its seconds and the card's peak memory,
from which capacity.py's runs a card for `gemx` are set (unmeasured, one at a time).
"""
import argparse
import fnmatch
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import blender_cloud  # noqa: E402

KIND = "gemx"
CLASSES = ("gpu-24gb", "gpu-48gb", "gpu-80gb")
ENV = HERE / "gemx_env.sh"
LAUNCHER = HERE / "on_machine.py"
SUFFIXES = (".avi", ".mp4", ".mov")
LEFT_OUT = ("extrinsics*",)
# Unmeasured: a video's detection, features and motion, plus its share of the folder's first build (torch, about
# 7.5 GB of weights) on the machine's first job.
VIDEO_MINUTES = 6
JOB_MINUTES = 2


def trials(root, cameras, subjects=None, patterns=("*",)):
    """{(subject, trial): {camera: video}} for the asked cameras, subjects and trial name patterns."""
    found = {}
    for video, (trial, camera, subject) in [
            *((video, (video.parent.name, video.parent.parent.name, video.parents[4].name))
              for video in sorted(root.glob("*/VideoData/*/*/*/*"))),
            *((video, (video.stem, video.parent.name, video.parents[1].name))  # SCORE's store copy (cluster.py)
              for video in sorted(root.glob("*/Cam*/*")))]:
        if (video.suffix.lower() not in SUFFIXES or video.stem != trial or camera not in cameras
                or (subjects and subject not in subjects) or any(fnmatch.fnmatch(trial, left) for left in LEFT_OUT)
                or not any(fnmatch.fnmatch(trial, pattern) for pattern in patterns)):
            continue
        found.setdefault((subject, trial), {})[camera] = video
    return found


def still_to_make(found, out):
    """The trials with an asked camera that has no done.json in `out`, each with only those cameras."""
    left = {}
    for (subject, trial), videos in found.items():
        missing = {camera: video for camera, video in videos.items()
                   if not (out / subject / trial / camera / "done.json").exists()}
        if missing:
            left[(subject, trial)] = missing
    return left


def job(subject, trial, videos, out):
    """One trial's job for blender_cloud.py: on_machine.py in GEM-X's env, its folder brought back."""
    folder = out / subject / trial
    arguments = [folder, *(f"--video={camera}={video}" for camera, video in sorted(videos.items()))]
    return blender_cloud.job_of(LAUNCHER, arguments, sorted(videos.values()), [folder],
                                JOB_MINUTES + VIDEO_MINUTES * len(videos), env=ENV)


def written(left, out):
    """Each job's file in <out>/jobs/, named for its subject and trial."""
    folder = out / "jobs"
    folder.mkdir(parents=True, exist_ok=True)
    paths = []
    for (subject, trial), videos in sorted(left.items()):
        path = folder / f"{subject}-{trial}.json"
        path.write_text(json.dumps(job(subject, trial, videos, out), indent=1))
        paths.append(path)
    return paths


def command(paths, options):
    """blender_cloud.py's call for the job files."""
    return [str(blender_cloud.cloud_python()), str(blender_cloud.HERE / "blender_cloud.py"), *map(str, paths),
            "--who", options.who, "--classes", options.classes, "--kind", KIND,
            *(["--dry-run"] if options.dry_run else []), *(["--detach"] if options.detach else [])]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("root", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--who", required=True)
    parser.add_argument("--cameras", default="Cam1")
    parser.add_argument("--subjects", default="")
    parser.add_argument("--trials", default="*", help="trial name patterns, comma separated")
    parser.add_argument("--classes", default=",".join(CLASSES))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--detach", action="store_true")
    options = parser.parse_args()
    root, out = options.root.resolve(), options.out.resolve()
    found = trials(root, options.cameras.split(","), [name for name in options.subjects.split(",") if name],
                   options.trials.split(","))
    if not found:
        raise SystemExit(f"no videos of {options.cameras} under {root}/<subject>/VideoData/<session>/<camera>/<trial>/")
    left = still_to_make(found, out)
    print(f"gemx: {len(found)} trials of {options.cameras}, {len(left)} still to make "
          f"({sum(map(len, left.values()))} videos)", flush=True)
    if not left:
        return 0
    return subprocess.run(command(written(left, out), options)).returncode


if __name__ == "__main__":
    sys.exit(main())
