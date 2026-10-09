"""The runners' one door to the Kubernetes cluster (SCORE_CLOUD=k8s, `provider.on_cluster()`): a runner that would
rent machines and ssh its work onto them describes each piece of work instead, and this runs them all as one run of
the job path and puts their outputs where the runner expects them.

    import cluster_jobs
    failed = cluster_jobs.run("blender", [
        {"command": ["sh", "-c", "..."],              run in /work/repo, the job's code unpacked there
         "code": ["tools/blender/inside"],            repo paths the command needs
         "inputs": ["/abs/file", "/abs/folder"],     sent to the same absolute path up there, or
                   {"local": "/abs/x", "path": "/up/there/x"}
         "outputs": ["/abs/out.json", "/abs/folder"], brought back from the same path, or
                    {"path": "/up/there/out", "local": "/abs/out"}
         "minutes": 10, "env": {...}, "models": [...], "cards": 1, "kernel_cache": "..."}],
        who="<session>", classes=["gpu-24gb", "gpu-48gb"], image="blender")

`image` is a kind in tools/cloud/images/images.json (default: `kind`), the job.json's `kind` (the runtime reads the
image's models.json by it); `kind` is capacity.py's job kind (`capacity_kind`), whose classes in its order are the
default `classes` and under which the ledger records the run. It returns the numbers of the jobs that did not
finish, as a machine runner's `left`. The machine runners
stay the default: nothing here runs unless the runner asks for it under SCORE_CLOUD=k8s.

One difference from the machine runners: the runtime brings a job's outputs back only when its command succeeded, and
a declared output the command did not make fails the job.
"""
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import submitter  # noqa: E402

REPO = HERE.parents[2]
ATTEMPTS = 2


def run_id(kind):
    """A run's id: the kind, the time and this process."""
    return f"{kind}-{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}"


def placed(entry, local_key, remote_key):
    """An input or output as (local path, path up there): a plain path is the same in both places."""
    if isinstance(entry, dict):
        return pathlib.Path(entry[local_key]).resolve(), entry[remote_key]
    return pathlib.Path(entry).resolve(), str(pathlib.Path(entry).resolve())


def upload_inputs(store, prefix, inputs):
    """Upload a job's inputs (a folder as one key a file) under `prefix`; the job's input entries."""
    entries = []
    for number, entry in enumerate(inputs):
        local, remote = placed(entry, "local", "path")
        files = [local] if local.is_file() else sorted(found for found in local.rglob("*") if found.is_file())
        if not files:
            raise SystemExit(f"the input {local} is missing or empty")
        for file in files:
            relative = "" if file == local else str(file.relative_to(local))
            key = f"{prefix}in/{number}/{relative or local.name}"
            store.upload(file, key)
            entries.append({"key": key, "path": str(pathlib.PurePosixPath(remote) / relative) if relative else remote})
    return entries


def output_entries(helper, run, job_id, outputs):
    """A job's output entries for job.json, and where each comes back here ({path up there: local path})."""
    entries, back = [], {}
    for number, entry in enumerate(outputs):
        local, remote = placed(entry, "local", "path")
        entries.append({"path": remote, "key": helper.output_key(run, job_id, str(number))})
        back[remote] = str(local)
    return entries, back


def spec_of(helper, store, run, job_id, kind, image, classes, job):
    """One job.json from a runner's job; with where its outputs come back."""
    outputs, back = output_entries(helper, run, job_id, job.get("outputs", ()))
    spec = {"kind": image, "capacity_kind": kind, "image": helper.image(image), "classes": list(classes),
            "code": helper.upload_code(store, job.get("code", []), kind=image, repo=REPO),
            "inputs": upload_inputs(store, helper.jobs.prefix(run, job_id), job.get("inputs", ())),
            "outputs": outputs, "command": job["command"], "env": job.get("env", {}),
            "models": job.get("models", []), "minutes": job.get("minutes", 30),
            "attempt_limit": job.get("attempt_limit", ATTEMPTS)}
    spec.update({key: job[key] for key in ("cards", "kernel_cache", "tool_only", "cpu", "memory") if key in job})
    return spec, back


def report_failure(helper, store, run, job_id):
    """Print a failed job's last failure (its stage, error and log tail)."""
    failures = helper.failures(store, run, job_id)
    if failures:
        last = failures[-1]
        submitter.say(f"job {job_id} failed at {last.get('stage')}: {last.get('error')}\n{last.get('log_tail', '')}")
    else:
        submitter.say(f"job {job_id} never finished")


def run(kind, jobs, who, classes=None, image=None, parallel=None, name=None):
    """Run the jobs on the cluster as one run and bring their outputs back; the numbers of those that failed.
    `parallel` holds the run to that many jobs at once (one card node each); `name` names the run."""
    helper = submitter.runtime()
    store = helper.cloud_store()
    image = image or kind
    classes = classes or sorted(submitter.capacity.classes_for(kind),
                                key=lambda name: submitter.capacity.speed_rank(name, kind))
    run_name = name or run_id(kind)
    specs, backs = {}, {}
    for number, job in enumerate(jobs):
        job_id = str(number)
        specs[job_id], backs[job_id] = spec_of(helper, store, run_name, job_id, kind, image, classes, job)
        helper.write_job(store, run_name, job_id, specs[job_id])
    submitter.submit(run_name, specs, store, wait_scale_down=False, who=who, parallel=parallel)
    failed = []
    for job_id in specs:
        if helper.state(store, run_name, job_id) == "done":
            helper.fetch_outputs(store, run_name, job_id, backs[job_id])
        else:
            report_failure(helper, store, run_name, job_id)
            failed.append(int(job_id))
    return failed
