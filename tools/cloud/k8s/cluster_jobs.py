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
a declared output the command did not make fails the job. A run whose watch fails or that is stopped (submitter.py
books its rows first) still brings back what its done jobs made before the error goes on.

Under SCORE_K8S_QUEUE (#76, build spec step S6) a run goes to the box's queue (`job_queue/`), which chains it on warm
workers of its image beside every other run of the box: the namespace and Secrets made (`submitter.prepare`), the
run enqueued with its stop line (the queue's euros so far and the batch cap), then waited on. A queue that is not
fresh at submit time is started for later runs and this run goes on today's path (`submitter.submit`); a queue that
goes stale while the run waits (`job_queue.Stale`) gives the run back: it is cancelled there, so a restarted queue never
assigns it, and its jobs not done are adopted by `submitter.submit`, which resumes from their Jobs' labels.
"""
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import job_queue  # noqa: E402
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


def framework_store():
    """The framework's store on this machine (score.store's Store.default): the listings a checkout's files are read
    from by sha256."""
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from score.store import Store

    return Store.default()


def checkout_files(kept, local):
    """{relative path: sha256} of an input inside one of the store's checkouts, read from its output's listing (no
    file read, the checkout need not be on disk); None for any other input."""
    checkouts = (kept.cache / "checkouts").resolve()
    if not local.is_relative_to(checkouts) or local == checkouts:
        return None
    output, *inside = local.relative_to(checkouts).parts
    if not kept.objects.exists(f"outputs/{output}.json"):
        return None
    under = "/".join(inside)
    listing = kept.listing(output)
    if under in listing:
        return {"": listing[under]}
    return {name[len(under) + 1:] if under else name: sha for name, sha in listing.items()
            if not under or name.startswith(under + "/")}


def hashed_files(local):
    """{relative path: sha256} of an input outside the store, each file hashed ("" for a plain file)."""
    from score.store import file_hash

    if local.is_file():
        return {"": file_hash(local)}
    return {str(found.relative_to(local)): file_hash(found) for found in sorted(local.rglob("*")) if found.is_file()}


def send_input(store, kept, sha, file):
    """One input's bytes in the job store under inputs/<sha256>, once for every run (asked first): from this machine
    when it holds them (the store's blob, else `file`), else copied inside the object storage from the store bucket
    (an evicted blob, never fetched back here); its key."""
    key = f"inputs/{sha}"
    if store.exists(key):
        return key
    blob = kept.objects.root / "blobs" / sha
    source = blob if blob.is_file() else file if file.is_file() else None
    if source is None:
        from score.store import offload

        offload.copy_blob(sha, store, key)
    else:
        store.upload(source, key)
    return key


def upload_inputs(store, inputs, kept=None):
    """A job's inputs (a folder as one key a file) in the job store, each file keyed by its sha256 so a file goes up
    once whichever runs read it; the job's input entries. A file of a store checkout takes its sha256 from the output's
    listing and its bytes from the store's blob (`kept`, the framework's store by default)."""
    kept = kept or framework_store()
    entries = []
    for entry in inputs:
        local, remote = placed(entry, "local", "path")
        listed = checkout_files(kept, local)
        files = listed if listed is not None else hashed_files(local) if local.exists() else {}
        if not files:
            raise SystemExit(f"the input {local} is missing or empty")
        for relative, sha in files.items():
            entries.append({"key": send_input(store, kept, sha, local / relative if relative else local),
                            "path": str(pathlib.PurePosixPath(remote) / relative) if relative else remote})
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
            "inputs": upload_inputs(store, job.get("inputs", ())),
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
    classes = classes or submitter.kind_classes(kind)
    run_name = name or run_id(kind)
    specs, backs = {}, {}
    for number, job in enumerate(jobs):
        job_id = str(number)
        specs[job_id], backs[job_id] = spec_of(helper, store, run_name, job_id, kind, image, classes, job)
        helper.write_job(store, run_name, job_id, specs[job_id])
    try:
        if queued():
            through_queue(helper, store, run_name, image, classes, specs, who, parallel)
        else:
            submitter.submit(run_name, specs, store, wait_scale_down=False, who=who, parallel=parallel)
    except BaseException:  # a watch that failed or a stop: what finished still comes back, then the error goes on
        bring_back(helper, store, run_name, specs, backs)
        raise
    return bring_back(helper, store, run_name, specs, backs)


def queued():
    """Whether runs go through the box's queue (SCORE_K8S_QUEUE set, not 0)."""
    return os.environ.get("SCORE_K8S_QUEUE", "") not in ("", "0")


def through_queue(helper, store, run_name, image, classes, specs, who, parallel):
    """The run on the box's queue to its end; on today's path (submitter.submit) when the queue is not fresh, the queue
    started for later runs; its jobs not done adopted by submitter.submit when the queue went stale while it waited."""
    if not job_queue.fresh():
        job_queue.start()
        submitter.say("the box's queue is not running (one is started for later runs): this run goes on by itself")
        submitter.submit(run_name, specs, store, wait_scale_down=False, who=who, parallel=parallel)
        return
    cluster = submitter.cluster_module()
    submitter.prepare(submitter.cluster_kubectl(cluster), cluster)
    first = next(iter(specs.values()))
    job_queue.enqueue(run_name, image, first["image"], classes, specs,
                      stop_line=job_queue.spent() + submitter.ledger.batch_cap()[0], who=who)
    try:
        job_queue.wait(run_name)
    except job_queue.Stale as stale:
        job_queue.cancel(run_name)
        left = {job_id: spec for job_id, spec in specs.items() if helper.state(store, run_name, job_id) != "done"}
        submitter.say(f"{stale}: its {len(left)} jobs not done are adopted here")
        submitter.submit(run_name, left, store, wait_scale_down=False, who=who, parallel=parallel)


def bring_back(helper, store, run_name, specs, backs):
    """The outputs of every done job of the run put where the runner wants them; the numbers of the jobs not done,
    each one's failure said."""
    failed = []
    for job_id in specs:
        if helper.state(store, run_name, job_id) == "done":
            helper.fetch_outputs(store, run_name, job_id, backs[job_id])
        else:
            report_failure(helper, store, run_name, job_id)
            failed.append(int(job_id))
    return failed
