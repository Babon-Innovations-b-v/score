"""Warm an image's GPU kernel caches for card classes, and measure the first render before and after: one rented
machine a class, side by side, each deleted at the end. Run it once after a new Blender version or a new driver,
so no job pays the first-use compile (tools/cloud/runtime/kernels.py).

    .venv/bin/python tools/cloud/images/warm.py --classes gpu-24gb,gpu-80gb --who "<session>" [--kind blender]

On each machine the kind's image (images.json) is pulled with plain docker, and Blender renders
tools/blender/inside/warm_kernels.py's scenes three times, each in a fresh node cache: `before`, without a kernel
cache (what every job paid until now); `first-node`, with the kernel cache, which compiles and uploads it when the
store has none for this card and driver yet; `new-node`, with the kernel cache restored from the store. The seconds
of each render go into images.json under the kind's "first_render", by card. The machines are claimed through
batch.py (the limits, watchdog, self-delete, ledger row and delete).
"""
import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import threading
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build  # noqa: E402
from build import batch, ledger, spread, stores, submit  # noqa: E402
from provider import cloud  # noqa: E402

KIND = "warm"
SETUP_MINUTES = 6
RENDER_MINUTES = 25
DISK_GB = 80
# Docker and the NVIDIA container toolkit, when the machine's image lacks them.
GPU_SETUP = """set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
if ! command -v docker >/dev/null; then apt-get update -qq; apt-get install -y -qq docker.io >/dev/null; fi
if ! command -v nvidia-ctk >/dev/null; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list
  apt-get update -qq; apt-get install -y -qq nvidia-container-toolkit >/dev/null
fi
nvidia-ctk runtime configure --runtime=docker >/dev/null
systemctl restart docker
"""
OUT = "/work/warm.json"
RUNS = (("before", None), ("first-node", "blender-5.0.1"), ("new-node", "blender-5.0.1"))


def set_up(machine, registry, store_spec):
    folder, host = machine["folder"], machine["host"]
    with (folder / "setup.log").open("w") as log:
        batch.remote(folder, host, GPU_SETUP, check=True, stdout=log, stderr=subprocess.STDOUT)
    build.log_in(machine, registry)
    build.send_store_environment(machine, store_spec)


def warm_job(store, run, job, image, kernel_cache, code):
    spec = {"kind": "blender", "image": image, "code": code, "kernel_cache": kernel_cache, "minutes": RENDER_MINUTES,
            "command": ["/opt/blender/blender", "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
                        "tools/blender/inside/warm_kernels.py", "--", OUT],
            "outputs": [{"path": OUT, "key": submit.output_key(run, job, "warm.json")}]}
    if not kernel_cache:
        del spec["kernel_cache"]
    submit.write_job(store, run, job, spec)


def measure(machine, image, store_spec, results):
    """Pull the image and run the three warm jobs on the machine, each in a fresh node cache; their numbers into
    `results` under the card."""
    folder = machine["folder"]
    store = stores.open_store(store_spec)
    run = time.strftime(f"warm-%Y%m%d-%H%M%S-{folder.name}")
    code = submit.upload_code(store, ["tools/blender/inside"])
    numbers = {"class": machine["class"], "type": machine["type"],
               "pull_seconds": build.remote_seconds(machine, f"docker pull -q {shlex.quote(image)}")}
    for job, kernel_cache in RUNS:
        warm_job(store, run, job, image, kernel_cache, code)
        wall = build.remote_seconds(machine, shlex.join([
            "docker", "run", "--rm", "--gpus", "all", "--env-file", "/root/smoke/store.env",
            "-e", f"SCORE_NODE={folder.name}", "-v", f"/var/lib/score-cache-{job}:/cache", image, run, job]))
        record = submit.done(store, run, job)
        local = folder / f"{job}.json"
        store.download(submit.output_key(run, job, "warm.json"), local)
        renders = json.loads(local.read_text())
        numbers["card"] = record["card"]
        numbers[job] = {"container_seconds": wall, "renders": renders["renders"],
                        "kernel_cache": record.get("kernel_cache")}
        batch.say(f"{folder.name} {job}: first render {renders['renders'][0]['seconds']} s, "
                  f"second {renders['renders'][1]['seconds']} s, container {wall} s")
    results[numbers["card"]] = numbers


def measure_class(machine_class, image, registry, store_spec, who, results):
    """One machine of the class, measured and deleted; its ledger entry recorded."""
    import pictures as picture_runs

    account = cloud.account()
    found = batch.offers([machine_class])
    minutes = SETUP_MINUTES + RENDER_MINUTES
    spent = batch.month_spent(account)
    refused = ledger.refusal(minutes, max([offer.price for offer in found] or [0]), spent) if found else "no offer"
    if refused:
        batch.say(f"{machine_class}: refused: {refused}")
        return
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime(f"warm-{machine_class}-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = picture_runs.Run(run_folder, started + ledger.minutes_allowed(max(offer.price for offer in found), spent) * 60)
    shares = spread.Shares([machine_class], deadline=run.deadline)
    try:
        spread.on_machines(run, account, found, 1, KIND, shares,
                           lambda machine: set_up(machine, registry, store_spec),
                           lambda machine, _share, _card: measure(machine, image, store_spec, results),
                           disk_gb=DISK_GB)
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run_folder.name,
                 "kind": KIND, "who": who, "class": machine_class,
                 **ledger.machines_record(run.machines, run.attempts, started),
                 "wall_minutes": (time.time() - started) / 60}
        ledger.record(entry)
        batch.say(f"{machine_class}: {entry['wall_minutes']:.0f} min, €{entry['euros']:.2f} (logs under {run_folder})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--classes", required=True, help="card classes, comma separated (one machine each)")
    parser.add_argument("--kind", default="blender")
    parser.add_argument("--who", required=True, help="the session asking")
    options = parser.parse_args()
    image = submit.image(options.kind)
    account = cloud.account()
    batch.sweep(account)
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    registry, store_spec = cloud.registry(), cloud.object_store()
    batch.stop_on_signals()
    results = {}
    threads = [threading.Thread(target=measure_class, args=(machine_class, image, registry, store_spec, options.who,
                                                           results))
               for machine_class in options.classes.split(",")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    built = build.saved()
    built[options.kind].setdefault("first_render", {}).update(results)
    build.save(built)
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
