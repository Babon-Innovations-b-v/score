"""Checks for the kernel caches against a folder store, no card: a job naming a kernel_cache gets the CUDA and OptiX
caches in the node cache, a first node uploads what it compiled, a new node restores it before its command, and a
node whose caches are no larger than the store's uploads nothing.

Run: .venv/bin/python tools/cloud/runtime/kernels_test.py   (make tests runs it)
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(tempfile.mkdtemp())
os.environ["SCORE_WORK"] = str(ROOT / "work")
os.environ["SCORE_CACHE"] = str(ROOT / "node-a")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import job as jobs  # noqa: E402
import kernels  # noqa: E402
import store as stores  # noqa: E402
import submit  # noqa: E402
import weights  # noqa: E402

CARD = "sm90-580.178.04"
# The command stands in for a first render: it says whether the cache was there and compiles (writes) it if not.
COMMAND = [sys.executable, "-c",
           "import os, pathlib; cache = pathlib.Path(os.environ['CUDA_CACHE_PATH']); "
           "print('warm' if (cache / 'k.bin').exists() else 'cold'); cache.mkdir(parents=True, exist_ok=True); "
           "(cache / 'k.bin').write_bytes(b'x' * 1000)"]


def a_job(store, job):
    submit.write_job(store, "r", job, {"kind": "blender", "image": "i", "command": COMMAND,
                                       "kernel_cache": "blender-5.0.1", "minutes": 1})


def on_node(name, check):
    """Run `check` with the runtime's node cache at ROOT/<name> and the card faked."""
    kept = weights.CACHE, kernels.card_key
    weights.CACHE, kernels.card_key = ROOT / name, lambda: CARD
    try:
        check()
    finally:
        weights.CACHE, kernels.card_key = kept


def test_a_first_node_uploads_and_a_new_node_restores():
    store = stores.FolderStore(ROOT / "store")

    def first():
        a_job(store, "one")
        assert jobs.run_job(store, "r", "one") == 0
        record = submit.done(store, "r", "one")["kernel_cache"]
        assert record == {"name": "blender-5.0.1", "card": CARD, "restored": False, "uploaded_bytes": 1000}
        assert "cold" in store.read_bytes("runs/r/one/log-1.txt").decode()
        assert store.exists(f"kernels/blender-5.0.1/{CARD}.tar")
    on_node("node-a", first)

    def second():
        a_job(store, "two")
        assert jobs.run_job(store, "r", "two") == 0
        record = submit.done(store, "r", "two")["kernel_cache"]
        assert record["restored"] and record["uploaded_bytes"] == 0
        assert "warm" in store.read_bytes("runs/r/two/log-1.txt").decode()
        assert "kernels_ready" in submit.done(store, "r", "two")["timings"]
    on_node("node-b", second)


def test_a_processor_node_runs_without_kernel_caches():
    store = stores.FolderStore(ROOT / "store-cpu")
    kept = kernels.card_key
    kernels.card_key = lambda: None
    try:
        submit.write_job(store, "r", "cpu", {"kind": "blender", "image": "i", "kernel_cache": "blender-5.0.1",
                                             "command": [sys.executable, "-c", "pass"]})
        assert jobs.run_job(store, "r", "cpu") == 0
        assert "kernel_cache" not in submit.done(store, "r", "cpu")
    finally:
        kernels.card_key = kept


def test_the_caches_point_into_the_node_cache():
    found = kernels.environment(pathlib.Path("/cache"), "blender-5.0.1", CARD)
    assert found["CUDA_CACHE_PATH"] == f"/cache/kernels/blender-5.0.1/{CARD}/cuda"
    assert found["OPTIX_CACHE_PATH"].endswith("/optix") and int(found["CUDA_CACHE_MAXSIZE"]) >= 1 << 30


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("kernels_test: ok")
