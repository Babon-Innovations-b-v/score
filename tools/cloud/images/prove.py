"""Prove images on a rented card: real jobs of one or more kinds through `score-job` in plain docker, each pulled and
timed, so an image's cold start (machine answering, image pulled, weights ready, first result) can be set against
the machine runner's setup. One machine for the whole plan, deleted at the end.

    .venv/bin/python tools/cloud/images/prove.py <plan.json> --who "<session>" [--wait-minutes 90] [--dry-run]

The plan names the card classes to take (any capacity.py allows for its kinds, best stocked first, asked again every
few minutes across classes and zones while none is in stock) and the runs, each a kind's image (images.json) and its
jobs in order:

    {"classes": ["gpu-80gb", "gpu-80gb-x2"], "minutes": 90, "disk_gb": 300,
     "runs": [{"kind": "judge", "code": ["tools/props/cloud/judge_worker.py"],
               "inputs": [{"from": "<local file>", "path": "/root/judge/in/a.png"}],
               "jobs": [{"name": "first-node", "cache": "a", "models": ["qwen3.8-27b-fp8"], "minutes": 40,
                         "command": ["judge-run", "tools/props/cloud/judge_worker.py", "/root/judge/jobs.json"],
                         "env": {}, "kernel_cache": "judge-vllm-0.31.0",
                         "outputs": [{"path": "/root/judge/out", "to": "<local folder>"}]}]}]}

A job's `cache` names its node cache on the machine (/var/lib/score-cache-<cache>): a new name is a node seeing the
weights for the first time, a used one a warm node. Every job's done.json timings, its container's seconds and the
image's pull seconds go into images.json under the kind's "proof", by card; the outputs come back to `to`.
"""
import argparse
import datetime
import json
import os
import pathlib
import shlex
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
import warm  # noqa: E402
from build import batch, ledger, spread, stores, submit  # noqa: E402
from provider import cloud  # noqa: E402

KIND = "prove"
SETUP_MINUTES = 8
RETRY_SECONDS = 180


def job_spec(store, run, job_name, image, code, inputs, job):
    """One job's job.json from the plan's job: its inputs uploaded, its outputs keyed under the run."""
    spec = {"kind": job["kind"], "image": image, "code": code, "command": job["command"],
            "env": job.get("env", {}), "models": job.get("models", []), "minutes": job.get("minutes", 30),
            "inputs": [submit.upload_input(store, run, job_name, item["from"], item["path"]) for item in inputs],
            "outputs": [{"path": item["path"], "key": submit.output_key(run, job_name, pathlib.Path(item["path"]).name)}
                        for item in job.get("outputs", [])]}
    if job.get("kernel_cache"):
        spec["kernel_cache"] = job["kernel_cache"]
    submit.write_job(store, run, job_name, spec)


def seconds_of(timings):
    """Seconds from the container's start to each later mark of its done.json timings."""
    def parse(value):
        return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
    start = parse(timings["pod_start"])
    return {mark: round(parse(value) - start, 1) for mark, value in timings.items()
            if mark != "pod_start" and isinstance(value, str) and value.endswith("Z")}


def run_job(machine, store, run, kind_run, job, image):
    """One job in a container on the machine; its numbers, its outputs brought back."""
    folder = machine["folder"]
    name = f"{kind_run['kind']}-{job['name']}"
    job_spec(store, run, name, image, kind_run["code_key"], kind_run.get("inputs", []), dict(job, kind=kind_run["kind"]))
    try:
        wall = build.remote_seconds(machine, shlex.join([
            "docker", "run", "--rm", "--gpus", "all", "--ipc=host", "--env-file", "/root/smoke/store.env",
            "-e", f"SCORE_NODE={folder.name}", "-v", f"/var/lib/score-cache-{job['cache']}:/cache", image, run, name]))
    except Exception as error:  # noqa: BLE001 - one job failing is a result: its failure is recorded, the rest run
        failed = submit.failures(store, run, name)
        batch.say(f"{name} failed: {error}; {failed[-1].get('stage') if failed else ''}")
        return {"failed": str(error), "failures": [entry.get("stage") for entry in failed]}
    record = submit.done(store, run, name)
    destinations = {item["path"]: item["to"] for item in job.get("outputs", []) if item.get("to")}
    submit.fetch_outputs(store, run, name, destinations)
    numbers = {"container_seconds": wall, "marks": seconds_of(record["timings"]), "card": record.get("card"),
               "kernel_cache": record.get("kernel_cache"), "env": job.get("env", {}), "cache": job["cache"]}
    batch.say(f"{name}: {json.dumps(numbers)}")
    return numbers


def set_up(machine, registry, store_spec):
    """Docker and the NVIDIA container toolkit on the machine (warm.set_up), timed: when it answered and when it was
    set up."""
    machine["answered"] = time.time()
    warm.set_up(machine, registry, store_spec)
    machine["set_up"] = time.time()


def prove_on(machine, plan, store_spec, results):
    """Every run of the plan on the machine, in order: its image pulled, its jobs run; the numbers into `results`."""
    store = stores.open_store(store_spec)
    run = time.strftime(f"prove-%Y%m%d-%H%M%S-{machine['folder'].name}")
    answered = round((machine["answered"] - machine["created"]) / 60, 2)
    setup = round((machine["set_up"] - machine["answered"]) / 60, 2)
    for kind_run in plan["runs"]:
        kind = kind_run["kind"]
        image = submit.image(kind)
        kind_run["code_key"] = submit.upload_code(store, kind_run.get("code", []), kind)
        numbers = {"type": machine["type"], "class": machine["class"], "zone": machine["zone"],
                   "answered_minutes": answered, "docker_setup_minutes": setup,
                   "image": image,
                   "pull_seconds": build.remote_seconds(machine, f"docker pull -q {shlex.quote(image)}"), "jobs": {}}
        for job in kind_run["jobs"]:
            numbers["jobs"][job["name"]] = run_job(machine, store, run, kind_run, job, image)
        results.setdefault(kind, []).append(numbers)


def offers_for(plan):
    found = batch.offers(list(plan["classes"]))
    if not found:
        batch.say(f"no {', '.join(plan['classes'])} offer in stock")
    return found


def one_attempt(plan, account, registry, store_spec, who, results):
    """Claim one machine from the plan's classes and prove on it; True when a machine was had."""
    import pictures as picture_runs

    found = offers_for(plan)
    if not found:
        return False
    spent = batch.month_spent(account)
    dearest = max(offer.price for offer in found)
    refused = ledger.refusal(plan.get("minutes", 90), dearest, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime("prove-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = picture_runs.Run(run_folder, started + min(plan.get("minutes", 90), ledger.minutes_allowed(dearest, spent))
                           * 60)
    shares = spread.Shares([plan], deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, 1, KIND, shares,
                           lambda machine: set_up(machine, registry, store_spec),
                           lambda machine, _share, _card: prove_on(machine, plan, store_spec, results),
                           disk_gb=plan.get("disk_gb", 300))
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run_folder.name,
                 "kind": KIND, "who": who, "runs": [kind_run["kind"] for kind_run in plan["runs"]],
                 **ledger.machines_record(run.machines, run.attempts, started),
                 "wall_minutes": (time.time() - started) / 60}
        ledger.record(entry)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        batch.say(f"prove: {entry['wall_minutes']:.0f} min, €{entry['euros']:.2f} (logs under {run_folder})")
    return bool(run.machines)


def save_results(results):
    """The proof numbers into images.json under each kind's "proof", by card."""
    built = build.saved()
    for kind, entries in results.items():
        for numbers in entries:
            cards = [job["card"] for job in numbers["jobs"].values() if job.get("card")]
            built[kind].setdefault("proof", {})[cards[0] if cards else numbers["type"]] = numbers
    build.save(built)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("plan", help="the plan, a JSON file (the docstring says what it holds)")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--wait-minutes", type=float, default=90, help="how long to keep asking while out of stock")
    parser.add_argument("--dry-run", action="store_true", help="price the plan's offers, rent nothing")
    options = parser.parse_args()
    plan = json.loads(pathlib.Path(options.plan).read_text())
    for kind_run in plan["runs"]:
        submit.image(kind_run["kind"])
    if options.dry_run:
        offers_for(plan)
        return
    account = cloud.account()
    batch.sweep(account)
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    registry, store_spec = cloud.registry(), cloud.object_store()
    batch.stop_on_signals()
    results = {}
    give_up = time.time() + options.wait_minutes * 60
    while not one_attempt(plan, account, registry, store_spec, options.who, results):
        if time.time() > give_up:
            raise SystemExit(f"no machine of {', '.join(plan['classes'])} in {options.wait_minutes:.0f} min")
        batch.say(f"no machine yet; asking again in {RETRY_SECONDS // 60} min")
        time.sleep(RETRY_SECONDS)
    save_results(results)
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
