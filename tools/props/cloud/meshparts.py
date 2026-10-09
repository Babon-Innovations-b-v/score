"""Split our own Pixal3D models into parts with SegviGen and GeoSAM2 on rented cards, spread over machines
(spread.py), bring the splits back, delete the machines (job parts-test, 2026-10-09: does a splitter of our own model
give better parts than PartCrafter's split of the picture laid onto it?).

    ~/.farm-factory-props/env/bin/python tools/props/cloud/meshparts.py <run folder> --who "<session>" \
        [--takes a,b] [--hold] [--dry-run]

The run folder is ../library/split_compare.py's: each <take>/up/ (raw.glb, map.png, mesh.glb, seed_points.npz) goes up,
and <take>/down/ comes back with SegviGen's predicted voxels unguided and guided (segvigen_auto.npz,
segvigen_guided.npz), GeoSAM2's face labels (geosam2.npz), their timings and any error. A take with all three back is
skipped. `--hold` keeps the last machine after its work until the run folder holds a file named `release` (for work
over ssh while a setup is new).

Pinned (each read at its source on 2026-10-09): SegviGen (Nelipot-Lee/SegviGen, MIT) and its weights
(fenghora/SegviGen, MIT); TRELLIS.2-4B's weights (microsoft/TRELLIS.2-4B, MIT) and TRELLIS.2's published wheels of
cumesh, flex_gemm and o_voxel (MIT); DINOv3 ViT-L/16 (DINOv3 Licence: worldwide, royalty-free, no commercial bar; from
an open copy, its weights file checked against the sha256 six copies share, since Meta's own is gated); GeoSAM2
(VAST-AI-Research/GeoSAM2, Apache-2.0) and its weights (VAST-AI/GeoSAM2, Apache-2.0); Blender 4.0.2 (GPL, a tool
run on the machine). Left out: briaai/RMBG-2.0 and nvdiffrast, both non-commercial (meshparts_setup.sh). The owner's
limits, the self-delete, the watchdog and the delete are batch.py's.
"""
import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import batch  # noqa: E402
import capacity  # noqa: E402
import ledger  # noqa: E402
import spread  # noqa: E402
from provider import cloud  # noqa: E402

REMOTE = pathlib.PurePosixPath("/root/mp")
KIND = "meshparts"
PINS = {
    "SEGVIGEN": "81ec99ede1fbe566c73322dd968cd64bb508f5f7",
    "SEGVIGEN_WEIGHTS": "73326b77a17b5194bcc918dbf13d8d5cefb1cca5",
    "TRELLIS_WEIGHTS": "af44b45f2e35a493886929c6d786e563ec68364d",
    "DINOV3": "camenduru/dinov3-vitl16-pretrain-lvd1689m",
    "DINOV3_REVISION": "3c276edd87d6f6e569ff0c4400e086807d0f3881",
    "DINOV3_SHA256": "dcb2e45127cccbf1601e5f42fef165eea275c8e5213197e8dcf3f48822718179",
    "GEOSAM2": "b5de23c60ab487d407b623d394a1614f9714761c",
    "GEOSAM2_WEIGHTS": "ba92f5f50418f2fe9af1078448b63176df13b1ee",
    "WHEELS": "https://github.com/JeffreyXiang/Storages/releases/download/Space_Wheels_251210",
    "UTILS3D": "9a4eb15e4021b67b12c460c7057d642626897ec8",
    "BLENDER_URL": "https://download.blender.org/release/Blender4.0/blender-4.0.2-linux-x64.tar.xz",
}
SETUP_MINUTES = 15
SHARE_SIZE = 3
# A first guess for one take: SegviGen's encode, render and two samplings, GeoSAM2's twelve views and inference.
MINUTES_A_TAKE = 6
BROUGHT_BACK = ["segvigen_auto.npz", "segvigen_guided.npz", "geosam2.npz", "*_timing.json", "*_error.txt",
                "render.png", "seed.npy", "result/inference.log"]


# What each splitter brings back, by the name --methods takes.
RESULTS = {"segvigen": ["segvigen_auto.npz", "segvigen_guided.npz"], "geosam2": ["geosam2.npz"]}


def to_split(run, takes=None, methods=tuple(RESULTS)):
    """The takes whose uploads are written and whose splits by `methods` are not all back."""
    found = [path.parent.parent.name for path in sorted(run.glob("*/up/raw.glb"))]
    wanted = [take for take in found if not takes or take in takes]
    return [take for take in wanted if not all((run / take / "down" / name).exists()
                                               for method in methods for name in RESULTS[method])]


def price(shares, account, hold):
    """Print the estimate and refuse what passes the owner's limits; the offers, the machines, the minutes allowed."""
    found = batch.offers(list(capacity.classes_for(KIND)))
    if not found:
        raise SystemExit("no card that holds SegviGen is sold by the backend")
    each = SHARE_SIZE * MINUTES_A_TAKE
    count = capacity.machines_for(len(shares), each, SETUP_MINUTES)
    minutes = SETUP_MINUTES + max(each, len(shares) * each / count) + (60 if hold else 0)
    dearest = max(offer[0] for offer in found)
    spent = batch.month_spent(account)
    batch.say(f"{len(shares)} shares of takes on {count} machine{'s' if count > 1 else ''}: about {minutes:.0f} min, "
              f"€{ledger.cost(minutes, dearest) * count:.2f}; €{spent:.2f} spent this month")
    refused = ledger.refusal(minutes, dearest * count, spent)
    if refused:
        raise SystemExit(f"refused: {refused}")
    return found, count, ledger.minutes_allowed(dearest * count, spent)


def set_up(machine, run, hold):
    """Both splitters and their weights onto one machine; with `hold`, a failed setup waits for `release` first."""
    log_folder, host = machine["folder"], machine["host"]
    batch.remote(log_folder, host, f"mkdir -p {REMOTE}", check=True)
    batch.copy(log_folder, [HERE / "meshparts_setup.sh", HERE / "segvigen_worker.py", HERE / "geosam2_worker.py"],
               f"root@{host}:{REMOTE}/")
    pins = " ".join(f"{key}={shlex.quote(value)}" for key, value in PINS.items())
    with (log_folder / "setup.log").open("w") as log:
        done = batch.remote(log_folder, host, f"env {pins} bash {REMOTE}/meshparts_setup.sh", stdout=log,
                            stderr=subprocess.STDOUT)
    if done.returncode:
        held(run, machine, hold, "setup failed")
        raise RuntimeError(f"setup failed ({log_folder / 'setup.log'})")


def held(run, machine, hold, why):
    """With `hold`, keep the machine until the run folder holds `release`."""
    if not hold:
        return
    batch.say(f"holding {machine['folder'].name} at {machine['host']} ({why}) until {run / 'release'} exists")
    while not (run / "release").exists():
        time.sleep(20)


def split(machine, number, takes, card, run, methods=tuple(RESULTS)):
    """One share of takes on a machine: uploaded, split by SegviGen then GeoSAM2, brought back. A worker that fails
    raises spread.JobFailed once both have run."""
    log_folder, host = machine["folder"], machine["host"]
    place, out = REMOTE / "in" / str(number), REMOTE / "out" / str(number)
    batch.remote(log_folder, host, f"mkdir -p {place} {out}", check=True)
    for take in takes:
        batch.copy(log_folder, [f"{run / take / 'up'}/"], f"root@{host}:{place}/{take}/")
    environment = f"CUDA_VISIBLE_DEVICES={card or 0} PYTHONUNBUFFERED=1"
    lines = {"segvigen": f"cd /root/sv/SegviGen && {environment} ATTN_BACKEND=xformers SPARSE_ATTN_BACKEND=xformers "
                         f"/root/sv/venv/bin/python {REMOTE}/segvigen_worker.py {place} {out} /root/sv/dinov3",
             "geosam2": f"cd /root/gs/GeoSAM2 && {environment} PATH=/root/gs/venv/bin:$PATH /root/gs/venv/bin/python {REMOTE}/geosam2_worker.py "
                        f"{place} {out} /root/gs/blender/blender"}
    codes = {}
    for name, line in ((name, line) for name, line in lines.items() if name in methods):
        began = time.time()
        with (log_folder / f"{name}{number}.log").open("w") as log:
            codes[name] = batch.remote(log_folder, host, line, stdout=log, stderr=subprocess.STDOUT).returncode
        batch.say(f"{name} share {number} on {log_folder.name}: {(time.time() - began) / 60:.1f} min, "
                  f"exit {codes[name]}")
    bring_back(log_folder, host, out, takes, run)
    machine.setdefault("unit_seconds", []).append(round(time.time() - machine.get("share_began", time.time()), 1))
    for name, code in codes.items():
        spread.raise_for(code, f"{name} share {number} ({log_folder / f'{name}{number}.log'})")


def bring_back(log_folder, host, out, takes, run):
    """Each take's results into <run>/<take>/down/."""
    patterns = [argument for name in BROUGHT_BACK for argument in ("--include", name)]
    for take in takes:
        down = run / take / "down"
        down.mkdir(parents=True, exist_ok=True)
        batch.copy(log_folder, [f"root@{host}:{out}/{take}/"], f"{down}/", "--include", "result/", *patterns,
                   "--exclude", "*")


def record(run, started, folder, takes):
    entry = {"started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)), "batch": run.folder.name,
             "kind": KIND, "folder": str(folder), "takes": takes,
             **ledger.machines_record(run.machines, run.attempts, started),
             "wall_minutes": (time.time() - started) / 60}
    ledger.record(entry)
    batch.say(f"meshparts: {entry['wall_minutes']:.0f} min on {len(entry['machines'])} machines, €{entry['euros']:.2f}")
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("run", type=pathlib.Path, help="split_compare.py's run folder")
    parser.add_argument("--who", required=True, help="the session asking")
    parser.add_argument("--takes", default="", help="only these takes, by comma")
    parser.add_argument("--hold", action="store_true", help="keep the machine for ssh work until <run>/release")
    parser.add_argument("--dry-run", action="store_true", help="check and price, rent nothing")
    parser.add_argument("--methods", default=",".join(RESULTS), help="the splitters to run, by comma (segvigen, "
                        "geosam2)")
    options = parser.parse_args()
    methods = tuple(method for method in options.methods.split(",") if method)
    takes = to_split(options.run, [take for take in options.takes.split(",") if take], methods)
    if not takes:
        batch.say("every take in the run folder is split already")
        return
    shares = [takes[start:start + SHARE_SIZE] for start in range(0, len(takes), SHARE_SIZE)]
    account = cloud.account()
    batch.sweep(account)
    found, count, allowed_minutes = price(shares, account, options.hold)
    if options.dry_run:
        return
    cloud.allow_key(account, "farm-factory-batch", batch.ssh_key())
    batch.stop_on_signals()
    import pictures as picture_runs
    (options.run / "release").unlink(missing_ok=True)
    started = time.time()
    run_folder = batch.BATCHES / (time.strftime("meshparts-%Y%m%d-%H%M%S") + f"-{os.getpid()}")
    run_folder.mkdir(parents=True)
    run = picture_runs.Run(run_folder, started + allowed_minutes * 60)
    queue = spread.Shares(enumerate(shares), deadline=run.deadline)

    def work(machine, share, card):
        machine["share_began"] = time.time()
        try:
            split(machine, *share, card, options.run, methods)
        finally:
            if queue.queued() <= 0:
                held(options.run, machine, options.hold, "its work is done")

    try:
        spread.on_machines(run, account, found, count, KIND, queue,
                           lambda machine: set_up(machine, options.run, options.hold), work)
        if not run.machines:
            raise SystemExit("no card could be rented")
    finally:
        for machine in run.machines:
            batch.delete_machine(machine)
        entry = record(run, started, options.run, takes)
        (run_folder / "cloud.json").write_text(json.dumps(entry, indent=1))
        (options.run / f"cloud-{run_folder.name}.json").write_text(json.dumps(entry, indent=1))
    left = to_split(options.run, takes, methods)
    if left:
        raise SystemExit(f"{len(left)} takes not fully split: {', '.join(left)} (logs under {run_folder})")


if __name__ == "__main__":
    main()
