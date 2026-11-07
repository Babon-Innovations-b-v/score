"""LabValidation's reference joint moments made again with OpenSim, every trial with the lab's ID setup, read from
SCORE's store directly (labvalidation/<subject>/: its scaled model, ID setups, ID .sto, ik/ and forces/) into a
temporary folder deleted at the end, each trial run by on_opensim.py in the OpenSim environment opensim_env.sh builds,
two at a time (a light CPU job: about a second a trial). One summary line; the per-trial npz and run.log under <out>.

    .venv/bin/python -m tools.labval.opensim_reference <out> --env <opensim_env.sh's folder>"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import numpy as np

PREFIX = "labvalidation/"
HERE = pathlib.Path(__file__).resolve().parent
FETCHES = 8  # files fetched at once (one at a time took 13 minutes for 811)


def trials_of(keys):
    """{subject: [trial]} of every trial whose lab ID setup is in the store's `keys`."""
    found = {}
    for key in keys:
        parts = key[len(PREFIX):].split("/")
        if len(parts) == 5 and parts[1:4] == ["OpenSimData", "Mocap", "ID"] and parts[4].endswith("_setup_id.xml"):
            found.setdefault(parts[0], []).append(parts[4][:-len("_setup_id.xml")])
    return {subject: sorted(trials) for subject, trials in sorted(found.items())}


def fetched(bucket, keys, subject, trials, folder):
    """The subject's files the trials need fetched from the store into `folder` (its own layout kept)."""
    stem = f"{PREFIX}{subject}/"
    wanted = [key for key in keys if key.startswith(stem) and (
        "/OpenSimData/Mocap/Model/" in key and key.endswith("_scaled.osim")
        or any(key.endswith(ending) for trial in trials for ending in (
            f"/Mocap/ID/{trial}_setup_id.xml", f"/Mocap/ID/{trial}_setup_externalLoads.xml", f"/Mocap/ID/{trial}.sto",
            f"/ik/{trial}.mot", f"/forces/{trial}.mot")))]
    def one(key):
        destination = folder / key[len(PREFIX):]
        destination.parent.mkdir(parents=True, exist_ok=True)
        bucket.fetch(key, destination)

    with concurrent.futures.ThreadPoolExecutor(FETCHES) as pool:
        list(pool.map(one, wanted))  # a failed fetch raises here
    return folder / subject


def run_one(python, library, subject_folder, trial, out):
    """One trial through on_opensim.py; (name, error or None)."""
    name = f"{subject_folder.name}_{trial}"
    lab_id = subject_folder / "OpenSimData" / "Mocap" / "ID" / f"{trial}.sto"
    command = [python, "-I", str(HERE / "on_opensim.py"), str(subject_folder), trial, str(out / f"{name}.npz")]
    if lab_id.exists():
        command.append(str(lab_id))
    with open(out / f"{name}.log", "w") as log:
        done = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT,
                              env={**os.environ, "LD_LIBRARY_PATH": library})
    return name, None if done.returncode == 0 else f"exit {done.returncode}, see {name}.log"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--env", required=True, type=pathlib.Path)
    parser.add_argument("--workers", type=int, default=2)
    options = parser.parse_args()
    from score.store import offload

    bucket = offload.open_bucket()
    keys = [key if isinstance(key, str) else key[0] for key in bucket.listed(PREFIX)]
    trials = trials_of(keys)
    options.out.mkdir(parents=True, exist_ok=True)
    python, library = str(options.env / "venv" / "bin" / "python"), str(options.env / "lib")
    failed, worst = {}, {}
    with tempfile.TemporaryDirectory() as work:
        folders = {subject: fetched(bucket, keys, subject, names, pathlib.Path(work))
                   for subject, names in trials.items()}
        with concurrent.futures.ThreadPoolExecutor(options.workers) as pool:
            jobs = [pool.submit(run_one, python, library, folders[subject], trial, options.out)
                    for subject, names in trials.items() for trial in names]
            for job in concurrent.futures.as_completed(jobs):
                name, error = job.result()
                if error:
                    failed[name] = error
                    continue
                with np.load(options.out / f"{name}.npz") as saved:
                    if "reproduced" in saved.files:
                        worst[name] = float(saved["reproduced"].max())
    total = sum(len(names) for names in trials.values())
    (options.out / "summary.json").write_text(json.dumps({"trials": total, "failed": failed,
                                                          "largest ID difference N m": worst}, indent=1))
    print(f"{options.out}: {total - len(failed)} of {total} trials remade, {len(failed)} failed; the lab's own ID "
          f"reproduced within {max(worst.values(), default=float('nan')):.3g} N m on {len(worst)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
