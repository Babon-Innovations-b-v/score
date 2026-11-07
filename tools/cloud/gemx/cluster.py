"""GEM-X Body Motion on LabValidation's videos on the Kubernetes cluster (SCORE_CLOUD=k8s, #98): one job a video, many
cards at once, each video read from the job store, never through this PC (the store copy's
labvalidation/<subject>/<Cam>/<trial>.mp4, copied once from SCORE's store bucket inside the provider). The cluster's
twin of cloud.py, which stays the machine path and the fallback when the cluster's cards are short.

    .venv/bin/python tools/cloud/gemx/cluster.py <out> --who "<session>" [--subjects subject2,...] \
        [--trials 'walking*,...'] [--cameras Cam0,...,Cam4] [--classes gpu-24gb,...] [--fov-from <moge out>] \
        [--name <run>] [--dry-run] [--detach]

Each video comes back to <out>/<subject>/<trial>/<camera>/ as on_machine.py writes it (motion.pt, raw.npz,
contact_ik.npz, done.json) and soma.npz beside them (tools/labval/on_gemx.py: the SOMA body tools/labval prepares
from), and a copy of that soma.npz as <out>/soma/<subject>_<trial>_<camera>.npz, the name `python -m tools.labval
prepare` reads. A video whose soma.npz is there is no job. --fetch-to <root> instead downloads the videos still to make
into <root>/<subject>/<Cam>/<trial>.mp4, for cloud.py's machine path (the fallback) to read, and runs nothing. Only trials with the lab's IK (LabValidation's 144
non-static trials; the manifest's `ik`) are asked.

On the card (the base image: CUDA's base, uv and Python 3.12): gemx_env.sh builds GEM-X's Python, weights and SOMA
assets into the node's cache (/cache, a folder every pod on the node mounts) once a node under its lock, then
on_machine.py and on_gemx.py run in it. Spending: as every cluster run, only inside a cleared run (SCORE_SPEND_TICKET,
or the owner's override); the submitter holds the run to the batch cap (ledger.BATCH_EUROS)."""
import argparse
import fnmatch
import json
import pathlib
import shlex
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "k8s"))

import detached  # noqa: E402

KIND = "gemx"
IMAGE = "base"
CLASSES = ("gpu-24gb", "gpu-48gb", "gpu-80gb")
PREFIX = "labvalidation/"
MANIFEST = PREFIX + "manifest.json"
ENV = "/cache/gemx-env"  # the node's GEM-X Python (gemx_env.sh's folder), kept between its pods
VIDEOS = "/work/labvalidation"  # where a job's video lands in its pod
CODE = ["tools/cloud/gemx", "tools/labval/on_gemx.py"]
# A pod's minutes: the node's first builds GEM-X's folder (torch, about 7.5 GB of weights), then the video, about
# cloud.VIDEO_MINUTES unmeasured.
MINUTES = 30


def videos(manifest, subjects, patterns, cameras):
    """[(subject, trial, camera, store key)] of the asked trials that have the lab's IK."""
    found = []
    for detail in manifest["subjects_detail"]:
        if subjects and detail["subject"] not in subjects:
            continue
        for trial in detail["trials"]:
            if not trial["files"].get("ik") or not any(fnmatch.fnmatch(trial["trial"], pattern)
                                                        for pattern in patterns):
                continue
            found += [(detail["subject"], trial["trial"], camera, PREFIX + trial["files"][camera])
                      for camera in cameras if camera in trial["files"]]
    return found


def folder_of(out, subject, trial, camera):
    return out / subject / trial / camera


def made_from(folder):
    """The video (its store key) a camera folder's result was made from, by its done.json; None when there is none."""
    done = folder / "done.json"
    if not done.exists():
        return None
    return PREFIX + json.loads(done.read_text())["video"][len(VIDEOS) + 1:]


def still_to_make(found, out):
    """The videos whose soma.npz is not back in `out`, or came back from another video (2026-11-06: a resumed run's
    jobs named by place brought 148 of 720 folders another video's result, #98)."""
    return [video for video in found if not (folder_of(out, *video[:3]) / "soma.npz").exists()
            or made_from(folder_of(out, *video[:3])) not in (None, video[3])]


def command(trial_folder, camera, video, fov_x=None):
    """The pod's command: GEM-X's folder built (or found) in the node cache, the video through GEM-X (at `fov_x` when
    given), its SOMA body."""
    camera_folder = trial_folder / camera
    python = f"{ENV}/bin/python"
    fov = [f"--fov-x={camera}={fov_x:.6f}"] if fov_x is not None else []
    return " && ".join([
        f"bash tools/cloud/gemx/gemx_env.sh {ENV}",
        shlex.join([python, "tools/cloud/gemx/on_machine.py", str(trial_folder), f"--video={camera}={video}", *fov]),
        shlex.join([python, "tools/labval/on_gemx.py", str(camera_folder / "motion.pt"),
                    str(camera_folder / "soma.npz"), "--soma-assets", f"{ENV}/soma"])])


def fov_of(moge, subject, trial, camera):
    """A video's horizontal field of view (deg) as MoGe-2 estimates it: the median over its frames
    (tools/labval/moge_cluster.py's <moge>/<subject>_<trial>_<camera>/moge.npz); a video MoGe-2 has not read raises."""
    import numpy as np

    with np.load(moge / f"{subject}_{trial}_{camera}" / "moge.npz") as found:
        return float(np.median(found["fov_x"]))


def job(out, subject, trial, camera, key, moge=None):
    """One video's cluster job: its video from the job store (at MoGe-2's field of view when `moge` is given), its
    camera folder brought back."""
    trial_folder = out / subject / trial
    video = f"{VIDEOS}/{key[len(PREFIX):]}"
    fov_x = fov_of(moge, subject, trial, camera) if moge else None
    return {"command": ["sh", "-c", command(trial_folder, camera, video, fov_x)], "code": CODE,
            "inputs": [{"key": key, "path": video}], "outputs": [str(folder_of(out, subject, trial, camera))],
            "minutes": MINUTES}


def copied(store, keys):
    """The videos in the job store: each key missing there copied from SCORE's store bucket inside the provider (no
    byte through this PC); how many were copied."""
    sys.path.insert(0, str(REPO))
    from score.store import offload

    missing = [key for key in keys if not store.exists(key)]
    if missing:
        source = offload.open_bucket()
        for key in missing:
            store.client.copy_object(Bucket=store.bucket, Key=key, CopySource={"Bucket": source.name, "Key": key})
    return len(missing)


def manifest_of():
    """LabValidation's manifest in SCORE's store bucket."""
    sys.path.insert(0, str(REPO))
    from score.store import offload

    source = offload.open_bucket()
    return json.loads(source.client.get_object(Bucket=source.name, Key=MANIFEST)["Body"].read())


def fetched(left, root):
    """The videos still to make downloaded from SCORE's store bucket to <root>/<subject>/<Cam>/<trial>.mp4 (the
    machine path's input); how many were downloaded."""
    sys.path.insert(0, str(REPO))
    from score.store import offload

    source = offload.open_bucket()
    count = 0
    for *_, key in left:
        local = root / key[len(PREFIX):]
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            source.client.download_file(source.name, key, str(local))
            count += 1
    return count


def named_copies(out, made):
    """Each made video's soma.npz also as <out>/soma/<subject>_<trial>_<camera>.npz (tools.labval prepare's name)."""
    folder = out / "soma"
    folder.mkdir(parents=True, exist_ok=True)
    for subject, trial, camera, _ in made:
        soma = folder_of(out, subject, trial, camera) / "soma.npz"
        if soma.exists():
            (folder / f"{subject}_{trial}_{camera}.npz").write_bytes(soma.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--who", required=True)
    parser.add_argument("--subjects", default="")
    parser.add_argument("--trials", default="*", help="trial name patterns, comma separated")
    parser.add_argument("--cameras", default="Cam0,Cam1,Cam2,Cam3,Cam4")
    parser.add_argument("--classes", default=",".join(CLASSES))
    parser.add_argument("--fov-from", type=pathlib.Path,
                        help="MoGe-2's out folder (tools/labval/moge_cluster.py): each video at its field of view")
    parser.add_argument("--name", help="the cluster run's name: the same name resumes it")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fetch-to", type=pathlib.Path, help="download the videos still to make here; run nothing")
    parser.add_argument(detached.FLAG, action="store_true", help="progress to a log, one result line at the end")
    options = parser.parse_args()
    out = options.out.resolve()
    if options.detach:
        detached.relaunch(sys.argv, "gemx-cluster", [out])
    found = videos(manifest_of(), [name for name in options.subjects.split(",") if name],
                   options.trials.split(","), options.cameras.split(","))
    left = still_to_make(found, out)
    print(f"gemx on the cluster: {len(found)} videos asked, {len(left)} still to make", flush=True)
    if not left or options.dry_run:
        return 0
    if options.fetch_to:
        print(f"gemx: {fetched(left, options.fetch_to.resolve())} videos downloaded to {options.fetch_to}", flush=True)
        return 0
    import keyed_jobs

    store = keyed_jobs.submitter.runtime().cloud_store()
    print(f"gemx: {copied(store, [video[3] for video in left])} videos copied into the job store", flush=True)
    failed = keyed_jobs.run(KIND, IMAGE, [job(out, *video, moge=options.fov_from) for video in left], options.who,
                            options.classes.split(","), name=options.name)
    named_copies(out, left)
    print(f"gemx: {len(left) - len(failed)} of {len(left)} videos made", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
