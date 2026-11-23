"""The calibration pass's command line (see `__init__.py`): every set object calibrated side by side, one process an
object, into job scratch; the spread per split written beside them; the folder stored as one run-store object, its
blobs in the store bucket, and the scratch emptied.

    python3 -m tools.props.bench.calibrate run [--only <id> ...] [--workers N] [--keep-scratch]

Prints one JSON line: {stored, objects, failed, scratch (only when kept)}.
"""
import argparse
import concurrent.futures
import json
import os
import pathlib
import shutil
import tempfile
import traceback

from tools.props.bench import calibrate
from tools.props.bench import truth as bench_truth


def one(item, mates, folder):
    """One object calibrated into folder/objects/<id>.json; None, or its failure."""
    try:
        record = calibrate.calibrated(item, mates)
    except Exception:  # an object that cannot be calibrated is a reported gap, never a silent skip
        return f"{item['address']}: {traceback.format_exc()[-1500:]}"
    name = item["address"].split("/", 1)[1].split("@")[0]
    (folder / "objects" / f"{name}.json").write_text(json.dumps(record, indent=1))
    return None


def stored(folder):
    """The folder as one run-store object, its blobs pushed to the store bucket; its hash."""
    from score.store import Store, offload
    offload.install()
    store, bucket = Store.default(), offload.open_bucket()
    output = store.put_tree(folder)
    for sha in sorted(set(store.listing(output).values())):
        offload.push(store.objects.path(f"blobs/{sha}"), sha, bucket)
    return output


def run(arguments):
    objects = bench_truth.the_set()["objects"]
    chosen = [item for item in objects if not arguments.only
              or item["address"].split("/", 1)[1].split("@")[0].removeprefix("simready_") in arguments.only
              or item["address"].split("/", 1)[1].split("@")[0] in arguments.only]
    folder = pathlib.Path(tempfile.mkdtemp(prefix="bench163-calibrate-"))
    (folder / "objects").mkdir()
    failed = []
    with concurrent.futures.ProcessPoolExecutor(arguments.workers) as pool:
        waiting = [pool.submit(one, item, [mate for mate in objects
                                           if mate["kind"] == item["kind"] and mate is not item], folder)
                   for item in chosen]
        failed = [found for found in (job.result() for job in waiting) if found]
    records = [json.loads(path.read_text()) for path in sorted((folder / "objects").glob("*.json"))]
    (folder / "spread.json").write_text(json.dumps({split: calibrate.spread(records, split)
                                                    for split in ("tune", "held-out")}, indent=1))
    (folder / "failed.json").write_text(json.dumps(failed, indent=1))
    output = stored(folder)
    told = {"stored": output, "objects": len(records), "failed": len(failed)}
    if arguments.keep_scratch:
        told["scratch"] = str(folder)
    else:
        shutil.rmtree(folder)
    print(json.dumps(told))


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    running = commands.add_parser("run")
    running.add_argument("--only", nargs="*")
    running.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    running.add_argument("--keep-scratch", action="store_true")
    arguments = parser.parse_args()
    run(arguments)


if __name__ == "__main__":
    main()
