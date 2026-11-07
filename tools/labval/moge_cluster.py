"""MoGe-2 on LabValidation's videos on the Kubernetes cluster (SCORE_CLOUD=k8s, #98): the floor each static camera
sees, for `_floor`. Each video's frames go through on_moge.py at GEM-X's own field of view (its K, read from the
video's GEM-X result), in jobs of --per-job videos, each video read from the job store as GEM-X's were
(tools/cloud/gemx/cluster.py), never through this PC.

    .venv/bin/python tools/labval/moge_cluster.py <out> --gemx <gemx out> --who "<session>" [--subjects ...] \
        [--trials 'squats*,...'] [--cameras Cam1,...] [--per-job 40] [--name <run>] [--dry-run] [--detach]

Each video comes back as <out>/<subject>_<trial>_<camera>/moge.npz (on_moge.py's) with its done file; a video whose
done file is there is no job, and one with no GEM-X result is not asked. Spending as every cluster run: only inside a
cleared run (SCORE_SPEND_TICKET, or the owner's override)."""
import argparse
import importlib.util
import math
import pathlib
import shlex
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "tools" / "cloud"))
sys.path.insert(0, str(REPO / "tools" / "cloud" / "k8s"))

import detached  # noqa: E402

# GEM-X's cluster path, by its file (tools/labval holds a cluster.py of its own): its videos, store copy and folders.
_SPEC = importlib.util.spec_from_file_location("gemx_cluster", REPO / "tools" / "cloud" / "gemx" / "cluster.py")
gemx = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gemx)

KIND = gemx.KIND  # the same cards as GEM-X: one model on one card, its Python the node's GEM-X folder
ENV = "/cache/moge-env"
CODE = ["tools/cloud/gemx", "tools/labval/on_moge.py", "tools/labval/moge_env.sh"]
# A pod's minutes: GEM-X's folder when the node has none (gemx.MINUTES), MoGe's 1.3 GB, then about 20 s a video.
MINUTES = 45


def fov_of(raw):
    """GEM-X's horizontal field of view (deg) of a video, from its result's K and image size (W, H)."""
    with np.load(raw) as result:
        focal, width = float(result["K"][0, 0, 0]), float(result["image_size"][0])
    return float(np.degrees(2.0 * np.arctan(width / 2.0 / focal)))


def folder_of(out, subject, trial, camera):
    return out / f"{subject}_{trial}_{camera}"


def asked(found, out, gemx_out):
    """[(the video, its out folder, GEM-X's fov)] of the videos with a GEM-X result and no MoGe result back yet."""
    left = []
    for subject, trial, camera, key in found:
        raw = gemx.folder_of(gemx_out, subject, trial, camera) / "raw.npz"
        folder = folder_of(out, subject, trial, camera)
        if raw.exists() and not (folder / "moge.done.json").exists():
            left.append(((subject, trial, camera, key), folder, fov_of(raw)))
    return left


def job(videos):
    """One job: its videos through MoGe-2 in one process (the model loaded once), each folder brought back."""
    python = f"{gemx.ENV}/bin/python"
    given = [f"--video={folder}/moge.npz={gemx.VIDEOS}/{video[3][len(gemx.PREFIX):]}={fov:.6f}"
             for video, folder, fov in videos]
    command = " && ".join([f"bash tools/cloud/gemx/gemx_env.sh {gemx.ENV}", f"bash tools/labval/moge_env.sh {ENV}",
                           shlex.join([python, "tools/labval/on_moge.py", ENV, *given])])
    return {"command": ["sh", "-c", command], "code": CODE,
            "inputs": [{"key": video[3], "path": f"{gemx.VIDEOS}/{video[3][len(gemx.PREFIX):]}"}
                       for video, _, _ in videos],
            "outputs": [str(folder) for _, folder, _ in videos], "minutes": MINUTES}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--gemx", type=pathlib.Path, required=True, help="GEM-X's out folder (its cluster.py's)")
    parser.add_argument("--who", required=True)
    parser.add_argument("--subjects", default="")
    parser.add_argument("--trials", default="*", help="trial name patterns, comma separated")
    parser.add_argument("--cameras", default="Cam0,Cam1,Cam2,Cam3,Cam4")
    parser.add_argument("--per-job", type=int, default=40)
    parser.add_argument("--classes", default=",".join(gemx.CLASSES))
    parser.add_argument("--name", help="the cluster run's name: the same name resumes it")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(detached.FLAG, action="store_true", help="progress to a log, one result line at the end")
    options = parser.parse_args()
    out = options.out.resolve()
    if options.detach:
        detached.relaunch(sys.argv, "moge-cluster", [out])
    found = gemx.videos(gemx.manifest_of(), [name for name in options.subjects.split(",") if name],
                        options.trials.split(","), options.cameras.split(","))
    left = asked(found, out, options.gemx.resolve())
    count = math.ceil(len(left) / options.per_job) if left else 0
    jobs = [job(left[start::count]) for start in range(count)]
    print(f"moge on the cluster: {len(found)} videos asked, {len(left)} still to make in {len(jobs)} jobs", flush=True)
    if not jobs or options.dry_run:
        return 0
    import keyed_jobs

    store = keyed_jobs.submitter.runtime().cloud_store()
    print(f"moge: {gemx.copied(store, [video[3] for video, _, _ in left])} videos copied into the job store", flush=True)
    failed = keyed_jobs.run(KIND, gemx.IMAGE, jobs, options.who, options.classes.split(","), name=options.name)
    made = sum((folder / "moge.done.json").exists() for _, folder, _ in left)
    print(f"moge: {made} of {len(left)} videos made, {len(failed)} jobs failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
