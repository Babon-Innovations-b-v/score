"""A job runs to done.json once, on weights checked by sha256 and fetched once a node, its failures recorded and
retried only up to its limit; its compiled kernels are paid once a card; its outputs come back whole.

Against a folder store, no cloud and no card. Each invariant with the break that turns it red (each applied once
and seen red):

- A job uploads its outputs and writes done.json last; a job with done.json is never run again; a failure is
  recorded per attempt (with its log's tail) and retried up to its limit, then refused; a command past its minutes,
  one that cannot start, or one that leaves a declared output unmade fails with its stage named.
  Break: drop the done.json check at the top of `run_job`. Break: `attempt > limit + 1` in `run_job`.
  Break: no time limit in `run_command`. Break: skip a missing output in `upload_outputs`.
- A tree of code bundles to one key by content (times and caches left out). Break: put mtimes into `bundle`.
- A model is seeded once from its source and then taken from the store, its tar's sha256 checked before use and
  never written whole to the disk; jobs side by side on one node fetch it once; room is made from the least
  recently used model no job holds; a model not for commercial use serves only a tool.
  Break: skip the sha256 comparison in `fetch_into`. Break: drop the node lock in `ready`.
  Break: drop the `use` lock in `evict`.
  Break: drop `make_room` before the unpack in `fetch_into`. Break: `refusal` always None.
- A Hugging Face token never follows a redirect; a repo's files are narrowed to the job's globs.
  Break: `request.add_header` for `add_unredirected_header` in `authorised`.
- Kernel caches: a first node uploads what it compiled, a new node restores it before its command, a node whose
  caches are no larger than the store's uploads nothing, a processor node has none.
  Break: drop the restore in `kernel_caches`. Break: upload whatever the size in `kernels.keep`.
- A handed hf: model is linked as its repository's snapshot at its revision (refs/main and its tag pointing at it);
  a url: model or one not handed is left out; linking again replaces the link.
  Break: skip the `ref` file in `link_model`. Break: do not replace an existing link.
- The store: a large tar's multipart parts stay within the 1,000 parts S3 allows (a 15 GB tar failed at 8 MB
  parts); an object read in ranges side by side comes out whole and in order, a broken range asked again; a bucket
  store is refused without its bucket. Break: `part_size` always 8 MB. Break: no retry of a short range.
"""
import hashlib
import io
import json
import os
import pathlib
import sys
import tempfile
import threading
import time
import urllib.request

import pytest

ROOT = pathlib.Path(tempfile.mkdtemp())
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import hf_cache  # noqa: E402
import job as jobs  # noqa: E402
import kernels  # noqa: E402
import store as stores  # noqa: E402
import submit  # noqa: E402
import weights  # noqa: E402

PYTHON = sys.executable
MEGABYTE = 1024 * 1024


@pytest.fixture(autouse=True)
def roomy_disk(monkeypatch, tmp_path):
    """The job's work folder and the node cache in the test's own folder, never /work or /cache; the tests' own disk
    always has room, so this machine's free space cannot fail them (the eviction test passes its own); each test's
    holds on its models end with it."""
    monkeypatch.setattr(jobs, "WORK", tmp_path / "work")
    monkeypatch.setattr(weights, "CACHE", tmp_path / "cache")
    real_all_ready = weights.all_ready  # its cache's default was bound at import
    monkeypatch.setattr(weights, "all_ready", lambda store, names, models, tool_only, cache=None: real_all_ready(
        store, names, models, tool_only, cache or weights.CACHE))
    real = weights.make_room
    monkeypatch.setattr(weights, "make_room", lambda cache, needed, free=lambda: 1 << 50: real(cache, needed, free))
    weights.real_make_room = real
    yield
    let_go()


def let_go():
    """End this process's hold on its models, as a job's end does."""
    for use in weights.IN_USE:
        use.close()
    weights.IN_USE.clear()


# ==== a job runs once ===============================================================================================

def a_repo():
    """A small repo with one script and one image folder's models.json naming a model to seed from a file."""
    repo = pathlib.Path(tempfile.mkdtemp())
    (repo / "tools").mkdir()
    (repo / "tools/echo.py").write_text(
        "import os, pathlib, sys\n"
        "text = pathlib.Path(sys.argv[1]).read_text()\n"
        "model = (pathlib.Path(os.environ['SCORE_MODEL_TINY']) / 'model.bin').read_text()\n"
        "out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)\n"
        "(out / 'a.txt').write_text(text.upper() + ' ' + model)\n"
        "(out / 'sub').mkdir(exist_ok=True); (out / 'sub/b.txt').write_text(os.environ['SCORE_JOB'])\n"
        "print('echoed')\n")
    (repo / "tools/__pycache__").mkdir()
    (repo / "tools/__pycache__/junk.pyc").write_text("x")
    source = repo / "model.bin"
    source.write_text("weights")
    images = repo / "tools/cloud/images/echo"
    images.mkdir(parents=True)
    (images / "models.json").write_text(json.dumps([{"name": "tiny", "source": f"url:{source.as_uri()}",
                                                     "revision": "v1", "licence": "MIT", "commercial_use": True}]))
    return repo


def submitted(store, run, job, command, up=ROOT / "up", **extra):
    """A job of the echo kind in the store, its input uploaded; its spec."""
    repo = a_repo()
    local = pathlib.Path(tempfile.mkdtemp()) / "in.txt"
    local.write_text("hello")
    spec = {"kind": "echo", "image": "registry/score-echo:1@sha256:x",
            "code": submit.upload_code(store, ["tools"], kind="echo", repo=repo),
            "inputs": [submit.upload_input(store, run, job, local, str(up / "in.txt"))],
            "outputs": [{"path": str(up / "out"), "key": submit.output_key(run, job, "out")}],
            "command": command, "models": ["tiny"], "minutes": 1, **extra}
    submit.write_job(store, run, job, spec)
    return spec


def test_a_job_runs_and_its_outputs_come_back_and_a_done_job_never_runs_again(tmp_path):
    store = stores.FolderStore(tmp_path / "store")
    submitted(store, "r1", "j1", [PYTHON, "tools/echo.py", str(ROOT / "up/in.txt"), str(ROOT / "up/out")])
    assert submit.state(store, "r1", "j1") == "waiting"
    assert jobs.run_job(store, "r1", "j1") == 0
    assert submit.state(store, "r1", "j1") == "done"
    record = submit.done(store, "r1", "j1")
    assert list(record["timings"]) == ["pod_start", "weights_ready", "inputs_ready", "first_result", "uploaded"]
    local = tmp_path / "back"
    submit.fetch_outputs(store, "r1", "j1", {str(ROOT / "up/out"): local / "out"})
    assert (local / "out/a.txt").read_text() == "HELLO weights"  # the input upper-cased, the model's bytes
    assert (local / "out/sub/b.txt").read_text() == "j1"

    submitted(store, "r1", "j2", [PYTHON, "-c", "import sys; sys.exit(9)"], up=ROOT / "up-2")
    stores.write_json(store, "runs/r1/j2/done.json", {"attempt": 1})
    assert jobs.run_job(store, "r1", "j2") == 0
    assert not store.keys("runs/r1/j2/failed-")


def test_failures_are_recorded_per_attempt_and_retried_only_up_to_the_limit(tmp_path):
    store = stores.FolderStore(tmp_path / "store")
    submitted(store, "r1", "j1", [PYTHON, "-c", "print('boom'); raise SystemExit(4)"], attempt_limit=2)
    assert jobs.run_job(store, "r1", "j1") == 1
    assert jobs.run_job(store, "r1", "j1") == 1
    assert jobs.run_job(store, "r1", "j1") == jobs.EXIT_NO_ATTEMPTS
    failed = submit.failures(store, "r1", "j1")
    assert [record["attempt"] for record in failed] == [1, 2]
    assert failed[0]["stage"] == "command" and "boom" in "\n".join(failed[0]["log_tail"])
    assert submit.state(store, "r1", "j1") == "failed"


def test_a_command_past_its_minutes_unable_to_start_or_missing_an_output_fails_by_stage(tmp_path):
    store = stores.FolderStore(tmp_path / "store")
    submitted(store, "r1", "slow", [PYTHON, "-c", "import time; time.sleep(60)"], up=ROOT / "up-slow", minutes=0.02)
    assert jobs.run_job(store, "r1", "slow") == 1
    assert "minutes" in submit.failures(store, "r1", "slow")[0]["error"]

    submitted(store, "r1", "empty", [PYTHON, "-c", "pass"], up=ROOT / "up-empty")
    assert jobs.run_job(store, "r1", "empty") == 1
    assert submit.failures(store, "r1", "empty")[0]["stage"] == "outputs"

    script = tmp_path / "not-executable.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o644)
    for job, command in (("denied", [str(script)]), ("missing", ["/no/such/program"])):
        submitted(store, "r1", job, command, up=ROOT / f"up-{job}")
        assert jobs.run_job(store, "r1", job) == 1
        failed = submit.failures(store, "r1", job)[0]
        assert failed["stage"] == "command" and "could not start" in failed["error"]
        assert store.exists(f"runs/r1/{job}/log-1.txt")


def test_one_tree_bundles_to_one_key_without_caches(tmp_path):
    repo = a_repo()
    first = submit.bundle(["tools"], repo)
    os.utime(repo / "tools/echo.py", (1, 1))  # another time, the same content
    assert submit.bundle(["tools"], repo) == first
    store = stores.FolderStore(tmp_path / "store")
    key = submit.upload_code(store, ["tools"], kind="echo", repo=repo)
    assert key.startswith("code/") and store.exists(key)
    assert all("__pycache__" not in str(name) for name in submit.bundled_files(["tools"], repo))


# ==== weights =======================================================================================================

def a_source(folder, text="weights", name="tiny"):
    """A file to seed from, as a url: entry of its own."""
    path = folder / f"{name}.bin"
    path.write_text(text)
    return {"name": name, "source": f"url:{path.as_uri()}", "revision": "v1", "licence": "MIT",
            "commercial_use": True}


def test_a_model_is_seeded_once_then_taken_from_the_store_unpacked_without_its_tar(tmp_path):
    store = stores.FolderStore(tmp_path / "store")
    entry = a_source(tmp_path, "x" * (3 * weights.CHUNK + 5))
    first = weights.ready(store, entry, tmp_path / "node-a")
    assert (first / "tiny.bin").read_text() == "x" * (3 * weights.CHUNK + 5) and (first / weights.READY).exists()
    tar = store.read_bytes("weights/tiny@v1.tar")
    assert store.read_bytes("weights/tiny@v1.tar.sha256").decode().split()[0] == hashlib.sha256(tar).hexdigest()
    (tmp_path / "tiny.bin").unlink()  # the source is gone: a second node must take it from the store
    store.download = lambda *arguments: (_ for _ in ()).throw(AssertionError("the tar was downloaded to the disk"))
    second = weights.ready(store, entry, tmp_path / "node-b")
    assert (second / "tiny.bin").read_text() == "x" * (3 * weights.CHUNK + 5)
    assert not list((tmp_path / "node-b" / "partial").iterdir())

    other = stores.FolderStore(tmp_path / "other")
    (tmp_path / "tiny.bin").write_text("x" * (3 * weights.CHUNK + 5))
    weights.ready(other, entry, tmp_path / "node-c")
    assert other.read_bytes("weights/tiny@v1.tar") == tar  # one source gives one tar, one sha256


def test_a_tar_that_does_not_match_or_has_no_sha256_is_refused(tmp_path):
    store = stores.FolderStore(tmp_path / "store")
    with pytest.raises(RuntimeError, match="sha256"):
        weights.ready(store, {**a_source(tmp_path), "sha256": "0" * 64}, tmp_path / "node")
    assert not (tmp_path / "node" / "weights" / "tiny@v1").exists()

    good = a_source(tmp_path, name="good")
    weights.ready(store, good, tmp_path / "node-good")
    let_go()
    store.write_bytes("weights/good@v1.tar", store.read_bytes("weights/good@v1.tar")[:-1] + b"!")  # damaged in store
    with pytest.raises(RuntimeError, match="sha256"):
        weights.ready(store, good, tmp_path / "node-next")
    assert not (tmp_path / "node-next" / "weights" / "good@v1").exists()

    entry = a_source(tmp_path, name="other")
    weights.ready(store, entry, tmp_path / "node-a")
    (tmp_path / "store" / "weights" / "other@v1.tar.sha256").unlink()
    store.reader = lambda key: (_ for _ in ()).throw(AssertionError("the store was read with no sha256 to check"))
    with pytest.raises(FileNotFoundError):
        weights.ready(store, entry, tmp_path / "node-b")


def test_jobs_side_by_side_on_one_node_fetch_once(tmp_path, monkeypatch):
    store = stores.FolderStore(tmp_path / "store")
    entry = a_source(tmp_path)
    fetched = []
    real_fetch = weights.fetch_into

    def slow_fetch(*arguments):
        fetched.append(1)
        time.sleep(0.2)  # long enough for every other job to ask meanwhile
        return real_fetch(*arguments)
    monkeypatch.setattr(weights, "fetch_into", slow_fetch)
    threads = [threading.Thread(target=weights.ready, args=(store, entry, tmp_path / "node")) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(fetched) == 1


def test_room_is_made_from_the_least_recently_used_model_no_job_holds_and_beside_a_seeded_tar(tmp_path, monkeypatch):
    store = stores.FolderStore(tmp_path / "store")
    node = tmp_path / "node"
    old, held, recent = (a_source(tmp_path, name=name) for name in ("old", "held", "recent"))
    for entry in (old, recent):
        weights.ready(store, entry, node)
    let_go()
    weights.ready(store, held, node)
    os.utime(node / "weights" / "old@v1" / weights.READY, (1, 1))
    os.utime(node / "weights" / "held@v1" / weights.READY, (0, 0))
    room = lambda: weights.RESERVE if (node / "weights" / "old@v1").exists() else 2 * weights.RESERVE  # noqa: E731
    weights.real_make_room(node, weights.RESERVE, free=room)
    assert not (node / "weights" / "old@v1").exists()
    assert (node / "weights" / "held@v1" / weights.READY).exists(), "a model a job holds was evicted"
    assert (node / "weights" / "recent@v1" / weights.READY).exists()
    let_go()

    asked = []
    monkeypatch.setattr(weights, "make_room", lambda cache, needed: asked.append(
        (needed, sorted(cache.glob("partial/*/model.tar")))))
    weights.ready(store, a_source(tmp_path, name="fresh"), tmp_path / "node-fresh")
    [(needed, tars)] = asked
    assert needed == store.size("weights/fresh@v1.tar") and len(tars) == 1  # room for the unpack beside its tar


def test_a_model_not_for_commercial_use_serves_only_a_tool():
    entry = {"name": "nc", "commercial_use": False, "licence": "CC-BY-NC-4.0"}
    assert weights.refusal(entry, tool_only=False)
    assert weights.refusal(entry, tool_only=True) is None
    with pytest.raises(SystemExit, match="commercial"):
        weights.all_ready(None, ["nc"], {"nc": entry}, tool_only=False)


def test_a_hugging_face_token_never_follows_a_redirect_and_files_are_narrowed(monkeypatch):
    request = weights.authorised("https://huggingface.co/x", "secret")
    assert request.unredirected_hdrs.get("Authorization") == "Bearer secret" and not request.headers
    listing = {"siblings": [{"rfilename": name} for name in ("model.safetensors", "README.md", "config.json")]}
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: io.BytesIO(json.dumps(listing).encode()))
    assert weights.hf_files("org/repo", "abc", ["*.safetensors", "*.json"]) == ["model.safetensors", "config.json"]
    assert len(weights.hf_files("org/repo", "abc")) == 3
    assert weights.environment_name("sam2.1-large") == "SCORE_MODEL_SAM2_1_LARGE"


# ==== kernel caches =================================================================================================

CARD = "sm90-580.178.04"
# The command stands in for a first render: it says whether the cache was there and compiles (writes) it if not.
COMPILES = [PYTHON, "-c",
            "import os, pathlib; cache = pathlib.Path(os.environ['CUDA_CACHE_PATH']); "
            "print('warm' if (cache / 'k.bin').exists() else 'cold'); cache.mkdir(parents=True, exist_ok=True); "
            "(cache / 'k.bin').write_bytes(b'x' * 1000)"]


def test_a_first_node_uploads_its_kernels_and_a_new_node_restores_them(tmp_path, monkeypatch):
    store = stores.FolderStore(tmp_path / "store")
    monkeypatch.setattr(kernels, "card_key", lambda: CARD)
    for node, job in (("node-a", "one"), ("node-b", "two")):
        monkeypatch.setattr(weights, "CACHE", tmp_path / node)
        submit.write_job(store, "r", job, {"kind": "blender", "image": "i", "command": COMPILES,
                                           "kernel_cache": "blender-5.0.1", "minutes": 1})
        assert jobs.run_job(store, "r", job) == 0
    first, second = (submit.done(store, "r", job)["kernel_cache"] for job in ("one", "two"))
    assert first == {"name": "blender-5.0.1", "card": CARD, "restored": False, "uploaded_bytes": 1000}
    assert "cold" in store.read_bytes("runs/r/one/log-1.txt").decode()
    assert second["restored"] and second["uploaded_bytes"] == 0  # no larger than the store's: nothing uploaded
    assert "warm" in store.read_bytes("runs/r/two/log-1.txt").decode()

    monkeypatch.setattr(kernels, "card_key", lambda: None)
    submit.write_job(store, "r", "cpu", {"kind": "blender", "image": "i", "kernel_cache": "blender-5.0.1",
                                         "command": [PYTHON, "-c", "pass"]})
    assert jobs.run_job(store, "r", "cpu") == 0
    assert "kernel_cache" not in submit.done(store, "r", "cpu")
    found = kernels.environment(pathlib.Path("/cache"), "blender-5.0.1", CARD)
    assert found["CUDA_CACHE_PATH"] == f"/cache/kernels/blender-5.0.1/{CARD}/cuda"


# ==== the hub cache of links ========================================================================================

REVISION = "3648707b69e1b1dcf14c473e30613266b786b9f1"


def test_a_handed_hf_model_is_its_repositorys_snapshot_and_linking_again_replaces_it(tmp_path):
    (tmp_path / "models.json").write_text(json.dumps([
        {"name": "soma-x-assets", "source": "hf:nvidia/SOMA-X", "revision": REVISION, "ref": "v0.3.3"},
        {"name": "absent", "source": "hf:org/absent", "revision": "abc"},
        {"name": "plain", "source": "url:https://example.org/plain.bin", "revision": "v1"}]))
    model = tmp_path / "weights" / f"soma-x-assets@{REVISION}"
    model.mkdir(parents=True)
    (model / "SOMA_neutral.npz").write_text("assets")
    environment = {"SCORE_MODEL_SOMA_X_ASSETS": str(model), "SCORE_MODEL_PLAIN": str(tmp_path)}
    made = hf_cache.link_all(tmp_path / "models.json", tmp_path / "hub", environment)
    place = tmp_path / "hub" / "models--nvidia--SOMA-X"
    assert made == [place / "snapshots" / REVISION]
    assert (place / "snapshots" / REVISION / "SOMA_neutral.npz").read_text() == "assets"
    assert (place / "refs" / "main").read_text() == REVISION and (place / "refs" / "v0.3.3").read_text() == REVISION
    assert sorted(path.name for path in (tmp_path / "hub").iterdir()) == ["models--nvidia--SOMA-X"]

    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    hf_cache.link_model(tmp_path / "hub", "org/name", "abc", first)
    assert hf_cache.link_model(tmp_path / "hub", "org/name", "abc", second).resolve() == second.resolve()


# ==== the store =====================================================================================================

def test_a_large_tar_fits_the_parts_allowed_and_a_small_file_keeps_eight_megabyte_parts():
    assert stores.part_size(1) == 8 * MEGABYTE
    assert stores.part_size(5 * 1024 * MEGABYTE) == 8 * MEGABYTE
    for size in (8 * 1024 * MEGABYTE, 15 * 1024 * MEGABYTE, 200 * 1024 * MEGABYTE + 7):
        part = stores.part_size(size)
        assert part % MEGABYTE == 0 and -(-size // part) <= 1000  # S3's limit on parts


class Body:
    def __init__(self, data):
        self.data = data

    def read(self):
        return self.data


class FlakyBucket:
    """A bucket client whose object breaks off the first read of every range."""

    def __init__(self, data):
        self.data = data
        self.broken = set()

    def get_object(self, Bucket, Key, Range):  # noqa: N803 - boto3's names
        first, last = (int(number) for number in Range.removeprefix("bytes=").split("-"))
        if first not in self.broken:
            self.broken.add(first)
            return {"Body": Body(self.data[first:last])}
        return {"Body": Body(self.data[first:last + 1])}


def test_ranges_read_side_by_side_give_the_object_whole_and_in_order(monkeypatch, tmp_path):
    data = os.urandom(5 * 1024 * 1024 + 3)
    monkeypatch.setattr(stores, "RANGE_SIZE", 64 * 1024)
    reader = io.BufferedReader(stores.RangeReader(FlakyBucket(data), "bucket", "key", len(data)), 1 << 20)
    assert reader.read() == data
    reader.close()

    folder = stores.FolderStore(tmp_path)
    folder.write_bytes("weights/a.tar", b"abc")
    assert folder.size("weights/a.tar") == 3
    with folder.reader("weights/a.tar") as whole:
        assert whole.read() == b"abc"


def test_the_store_is_named_by_the_environment_and_a_bucket_store_needs_its_bucket():
    assert isinstance(stores.from_environment({"SCORE_STORE_ENDPOINT": f"file://{ROOT}/s"}), stores.FolderStore)
    spec = {"endpoint": "https://s3.example", "region": "r", "bucket": "b", "access_key": "a", "secret_key": "s"}
    assert stores.environment(spec)["SCORE_STORE_BUCKET"] == "b"
    with pytest.raises(SystemExit, match="SCORE_STORE_BUCKET"):
        stores.from_environment({"SCORE_STORE_ENDPOINT": "https://s3.example"})
