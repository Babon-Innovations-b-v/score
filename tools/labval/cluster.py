"""A LabValidation measure folder's sim body runs on the Kubernetes cluster (SCORE_CLOUD=k8s, #98): its trials
(trials/<name>/job.json, as `prepare` writes them) in jobs of --per-job trials each, every job on its own card, side by
side, in the newton image (newton_env.sh's pins). The model (MyoFullBody, the same for every trial) goes up once for
the run; each trial folder comes back whole, with its run's out.json, out.npz and run.log. A trial whose out.json is
here is no job. The cluster's twin of the measure folder's scripts/go.sh through tools/cloud/sim_measure, which stays
the machine path and the fallback when the cluster's cards are short.

    .venv/bin/python -m tools.labval.cluster <folder> --who "<session>" [--per-job 15] [--classes gpu-24gb,...] \
        [--gpus 24] [--name <run>] [--clip-minutes 2.5] [--dry-run]

In the pod each trial runs inside/sim_body.py on its own (`newton-run`), one after another; a trial that fails says so
in its run.log and the next one still runs. Spending: as every cluster run, only inside a cleared run
(SCORE_SPEND_TICKET, or the owner's override); the submitter holds the run to the batch cap (ledger.BATCH_EUROS)."""
import argparse
import json
import math
import pathlib
import shlex
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools/cloud/k8s"))

KIND = "sim-body"
IMAGE = "newton"
CLASSES = ("gpu-24gb", "gpu-48gb", "gpu-80gb")
SCRIPT = "score/stages/sim_body/inside/sim_body.py"
CODE = ["score/stages/sim_body/inside", "score/stages/physics/inside"]
PER_JOB = 15
# At most this many of the run's jobs (one card each) on the cluster at once, so a run leaves cards for env1's Buy (#98)
GPUS = 24
# A job's minutes: the measured clip at its high (sim_body.CLIP_HIGH_MINUTES, 2.5 on an L4, a 6 s clip of CLIP_FRAMES)
# a trial, a longer trial in proportion to its frames, the node's first kernel compile (COMPILE_MINUTES, 3) and the
# pod's start. By count alone six sit-to-stands of 550 to 656 frames had a job's 20 minutes (#98, 2026-11-07: 18 of
# the 36 trials of six capped jobs).
CLIP_MINUTES, START_MINUTES, CLIP_FRAMES = 2.5, 5, 180


def waiting(folder):
    """The measure folder's trial folders whose out.json is not here, by name."""
    return sorted(path.parent for path in pathlib.Path(folder).glob("trials/*/job.json")
                  if not (path.parent / "out.json").exists())


def batches(trials, per_job):
    """The trials in jobs of at most `per_job`, evenly."""
    count = math.ceil(len(trials) / per_job) if trials else 0
    return [trials[start::count] for start in range(count)]


def line(trial):
    """One trial's run in the pod: sim_body.py in the newton image's Python, its log beside it; a failure said."""
    run = shlex.join(["newton-run", SCRIPT, str(trial / "job.json"), str(trial / "out.json")])
    return f"{run} > {shlex.quote(str(trial / 'run.log'))} 2>&1 || echo {shlex.quote(f'failed: {trial.name}')}"


def clips(trial):
    """How many measured clips a trial's frames make (its people's targets' frames over CLIP_FRAMES), at least one."""
    import numpy as np

    frames = sum(np.load(person["targets"])["world"].shape[0]
                 for person in json.loads((trial / "job.json").read_text())["people"])
    return max(1.0, frames / CLIP_FRAMES)


def job(trials, clip_minutes=CLIP_MINUTES):
    """One job: its trials' runs in turn, each trial folder sent up and brought back, its minutes by their frames
    (`clip_minutes` a measured clip's: more for a run that does more, MOTOR's stage A)."""
    targets = {pathlib.Path(person["targets"]).parent for trial in trials
               for person in json.loads((trial / "job.json").read_text())["people"]}
    if not targets <= set(trials):
        raise SystemExit(f"a trial's targets lie outside its folder: {sorted(map(str, targets - set(trials)))}")
    return {"command": ["sh", "-c", "; ".join(line(trial) for trial in trials)], "code": CODE,
            "inputs": [str(trial) for trial in trials], "outputs": [str(trial) for trial in trials],
            "minutes": START_MINUTES + clip_minutes * sum(clips(trial) for trial in trials)}


def model_of(trials):
    """The one model folder every trial's job.json names."""
    models = {json.loads((trial / "job.json").read_text())["model"] for trial in trials}
    if len(models) != 1:
        raise SystemExit(f"the trials name {len(models)} models: {sorted(models)}")
    return models.pop()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("--who", required=True)
    parser.add_argument("--per-job", type=int, default=PER_JOB)
    parser.add_argument("--classes", default=",".join(CLASSES))
    parser.add_argument("--gpus", type=int, default=GPUS, help="at most this many cards (jobs) at once")
    parser.add_argument("--name", help="the cluster run's name: the same name resumes it")
    parser.add_argument("--clip-minutes", type=float, default=CLIP_MINUTES,
                        help="a measured clip's minutes at its high (MOTOR's stage A takes more)")
    parser.add_argument("--dry-run", action="store_true")
    options = parser.parse_args()
    trials = waiting(options.folder.resolve())
    jobs = batches(trials, options.per_job)
    print(f"sim body on the cluster: {len(trials)} trials to run in {len(jobs)} jobs", flush=True)
    if not jobs or options.dry_run:
        return 0
    import keyed_jobs

    failed = keyed_jobs.run(KIND, IMAGE, [job(part, options.clip_minutes) for part in jobs], options.who, options.classes.split(","),
                            shared=[model_of(trials)], name=options.name, parallel=options.gpus)
    made = [trial for trial in trials if (trial / "out.json").exists()]
    print(f"sim body: {len(made)} of {len(trials)} trials ran, {len(failed)} jobs did not finish", flush=True)
    return 0 if len(made) == len(trials) else 1


if __name__ == "__main__":
    sys.exit(main())
