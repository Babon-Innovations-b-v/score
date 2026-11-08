"""PBL (pbl_env.sh, on_pbl.py) on LabValidation's single-camera videos on the Kubernetes cluster (SCORE_CLOUD=k8s,
#98): every video asked at once, in jobs of --per-job videos, one card each, side by side, each job's videos in
LANES processes sharing its card (MeTRAbs loaded once a lane); each video read from the job store as GEM-X's were
(tools/cloud/gemx/cluster.py), never through this PC.

    .venv/bin/python tools/labval/pbl/cluster.py <out> --gemx <GEM-X out> --who "<session>" [--subjects ...] \
        [--trials 'squats*,...'] [--cameras Cam1,...] [--per-job 15] [--name <run>] [--dry-run] [--detach]

The camera each video is given is the chain's own (#98): GEM-X's intrinsic matrix from its result for that video
(<GEM-X out>/<subject>/<trial>/<camera>/raw.npz, GEM-X run at MoGe-2's field of view), never the lab's calibration (a
check only). Each video comes back as <out>/<subject>_<trial>_<camera>/ (pbl.npz, pbl.done.json, on_pbl.py's) with
its log; a video whose done file is there is no job, one with no GEM-X result is not asked. Spending: as every
cluster run, only inside a cleared run (SCORE_SPEND_TICKET, or the owner's override)."""
import argparse
import importlib.util
import math
import pathlib
import shlex
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "tools" / "cloud"))
sys.path.insert(0, str(REPO / "tools" / "cloud" / "k8s"))

import detached  # noqa: E402

# GEM-X's cluster path, by its file: its videos, store copy and folders.
_SPEC = importlib.util.spec_from_file_location("gemx_cluster", REPO / "tools" / "cloud" / "gemx" / "cluster.py")
gemx = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gemx)

KIND = gemx.KIND  # the same cards as GEM-X: one model on one card
ENV = "/cache/pbl-env"
CODE = ["tools/labval/pbl/on_pbl.py", "tools/labval/pbl/pbl_env.sh"]
# A pod's minutes: the node's first builds PBL's folder (about 5 min: JAX, TensorFlow, MeTRAbs' 0.7 GB), then each
# lane's videos one after another, a video's MeTRAbs pass and 10,000 fit steps (subject2, an L4 card alone: 7 to 61 s
# and 133 to 163 s, #98, 2026-11-08), the lanes side by side on the card slower than alone.
FIRST_MINUTES, VIDEO_MINUTES = 20, 8
# PBL processes side by side on one card: one fit step takes 9 ms whether a trial has 95 frames or 480 (2026-11-08),
# so a lone fit leaves the card mostly idle; each lane loads MeTRAbs once and takes every LANES-th video.
LANES = 3


def intrinsics_of(raw):
    """GEM-X's intrinsic matrix of a video (its first frame's; GEM-X holds one camera a video), from its raw.npz."""
    with np.load(raw) as result:
        return np.asarray(result["K"][0], dtype=float)


def folder_of(out, subject, trial, camera):
    return out / f"{subject}_{trial}_{camera}"


def asked(found, out, gemx_out):
    """[(the video, its out folder, its intrinsic matrix)] of the videos with a GEM-X result and no PBL result yet."""
    left = []
    for subject, trial, camera, key in found:
        raw = gemx.folder_of(gemx_out, subject, trial, camera) / "raw.npz"
        folder = folder_of(out, subject, trial, camera)
        if raw.exists() and not (folder / "pbl.done.json").exists():
            left.append(((subject, trial, camera, key), folder, intrinsics_of(raw)))
    return left


def lane(videos):
    """One on_pbl.py process over `videos`, its videos' --video arguments."""
    given = [f"--video={folder}={gemx.VIDEOS}/{video[3][len(gemx.PREFIX):]}="
             f"{matrix[0, 0]:.4f}={matrix[1, 1]:.4f}={matrix[0, 2]:.4f}={matrix[1, 2]:.4f}"
             for video, folder, matrix in videos]
    return shlex.join([f"{ENV}/venv/bin/python", "tools/labval/pbl/on_pbl.py", ENV, *given])


def job(videos):
    """One job: PBL's folder built (or found), its videos in LANES processes side by side, the job failed when any
    lane failed; each folder brought back."""
    lanes = [videos[start::LANES] for start in range(min(LANES, len(videos)))]
    started = " ".join(f"{lane(mine)} & p{number}=$!;" for number, mine in enumerate(lanes))
    waited = " ".join(f"wait $p{number} || failed=1;" for number in range(len(lanes)))
    command = f"bash tools/labval/pbl/pbl_env.sh {ENV} && {{ failed=0; {started} {waited} exit $failed; }}"
    return {"command": ["sh", "-c", command], "code": CODE,
            "inputs": [{"key": video[3], "path": f"{gemx.VIDEOS}/{video[3][len(gemx.PREFIX):]}"}
                       for video, _, _ in videos],
            "outputs": [str(folder) for _, folder, _ in videos],
            "minutes": FIRST_MINUTES + VIDEO_MINUTES * len(lanes[0])}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--gemx", type=pathlib.Path, required=True, help="GEM-X's out folder (at MoGe-2's fov)")
    parser.add_argument("--who", required=True)
    parser.add_argument("--subjects", default="")
    parser.add_argument("--trials", default="*", help="trial name patterns, comma separated")
    parser.add_argument("--cameras", default="Cam0,Cam1,Cam2,Cam3,Cam4")
    parser.add_argument("--per-job", type=int, default=15)
    parser.add_argument("--gpus", type=int, help="at most this many cards (jobs) at once (default: every job)")
    parser.add_argument("--classes", default=",".join(gemx.CLASSES))
    parser.add_argument("--name", help="the cluster run's name: the same name resumes it")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(detached.FLAG, action="store_true", help="progress to a log, one result line at the end")
    options = parser.parse_args()
    out = options.out.resolve()
    if options.detach:
        detached.relaunch(sys.argv, "pbl-cluster", [out])
    found = gemx.videos(gemx.manifest_of(), [name for name in options.subjects.split(",") if name],
                        options.trials.split(","), options.cameras.split(","))
    left = asked(found, out, options.gemx.resolve())
    count = math.ceil(len(left) / options.per_job) if left else 0
    jobs = [job(left[start::count]) for start in range(count)]
    print(f"pbl on the cluster: {len(found)} videos asked, {len(left)} still to make in {len(jobs)} jobs", flush=True)
    if not jobs or options.dry_run:
        return 0
    import keyed_jobs

    store = keyed_jobs.submitter.runtime().cloud_store()
    print(f"pbl: {gemx.copied(store, [video[3] for video, _, _ in left])} videos copied into the job store", flush=True)
    failed = keyed_jobs.run(KIND, gemx.IMAGE, jobs, options.who, options.classes.split(","), name=options.name,
                            parallel=options.gpus)
    made = sum((folder / "pbl.done.json").exists() for _, folder, _ in left)
    print(f"pbl: {made} of {len(left)} videos made, {len(failed)} jobs failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
