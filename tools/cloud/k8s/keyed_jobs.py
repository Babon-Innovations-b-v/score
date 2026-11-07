"""cluster_jobs.run for many jobs that read the same big inputs, or inputs already in the job store: each local input
named in `shared` is uploaded once for the whole run (cluster_jobs uploads every job's own inputs again), and an input
given as {"key": "<job store key>", "path": "/up/there"} is taken from the store as it is, never through this PC.

    import keyed_jobs
    failed = keyed_jobs.run("gemx", "base", jobs, who, classes, shared=["/abs/model"], name="gemx-...")

`jobs` are cluster_jobs' (command, code, inputs, outputs, minutes, env, ...); `name` makes the run resumable: a job
whose done.json is in the store is not run again (submitter.submit), and its outputs are brought back all the same.
A job's id in its run is its own content (`job_id`), never its place in `jobs`: a run resumed with fewer jobs (the
done ones left out by the runner) would otherwise take an earlier job's done.json for another job and bring that
job's outputs back as its own. Returns the numbers (places in `jobs`) of the jobs that did not finish, as
cluster_jobs.run does."""
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import cluster_jobs  # noqa: E402
import submitter  # noqa: E402


def stored(entry):
    """Whether an input entry is already in the job store (a {"key", "path"} mapping)."""
    return isinstance(entry, dict) and "key" in entry


def spec_with(helper, store, run_name, job_id, kind, image, classes, job, common):
    """One job.json (cluster_jobs.spec_of) with its stored inputs and the run's shared ones added; with where its
    outputs come back."""
    local = [entry for entry in job.get("inputs", ()) if not stored(entry)]
    spec, back = cluster_jobs.spec_of(helper, store, run_name, job_id, kind, image, classes, {**job, "inputs": local})
    spec["inputs"] += [*common, *(entry for entry in job.get("inputs", ()) if stored(entry))]
    return spec, back


def job_id(job):
    """A job's id in its run: its description's hash, as a number (cluster_jobs reports a job by its number), so the
    same job keeps its id however many jobs a resumed run asks (2026-11-06: ids by place gave 148 of 720 GEM-X
    videos another video's result, #98)."""
    return str(int(hashlib.sha256(json.dumps(job, sort_keys=True, default=str).encode()).hexdigest()[:12], 16))


def run(kind, image, jobs, who, classes, shared=(), name=None, parallel=None):
    """The jobs on the cluster as one run (`kind` capacity.py's, `image` an images.json kind), `shared` uploaded once
    and given to every job; the numbers of those that did not finish."""
    helper = submitter.runtime()
    store = helper.cloud_store()
    run_name = name or cluster_jobs.run_id(kind)
    common = cluster_jobs.upload_inputs(store, list(shared)) if shared else []
    ids = [job_id(job) for job in jobs]
    if len(set(ids)) != len(ids):
        raise ValueError("two of the run's jobs are the same job")
    specs, backs = {}, {}
    for key, job in zip(ids, jobs):
        specs[key], backs[key] = spec_with(helper, store, run_name, key, kind, image, classes, job, common)
        helper.write_job(store, run_name, key, specs[key])
    try:
        submitter.submit(run_name, specs, store, wait_scale_down=False, who=who, parallel=parallel)
    except BaseException:  # a watch that failed or a stop: what finished still comes back, then the error goes on
        cluster_jobs.bring_back(helper, store, run_name, specs, backs)
        raise
    return [ids.index(str(key)) for key in cluster_jobs.bring_back(helper, store, run_name, specs, backs)]
