"""A job runs to done.json once, on weights checked by sha256 and fetched once a node, its failures recorded and
retried only up to its limit; its compiled kernels are paid once a card; its outputs come back whole.

Against a folder store, no cloud and no card. Each invariant with the break that turns it red (each applied once
to the one merged test and seen red, 2026-11-13):

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
CARD = "sm90-580.178.04"
REVISION = "3648707b69e1b1dcf14c473e30613266b786b9f1"
# The command stands in for a first render: it says whether the cache was there and compiles (writes) it if not.
COMPILES = [PYTHON, "-c",
            "import os, pathlib; cache = pathlib.Path(os.environ['CUDA_CACHE_PATH']); "
            "print('warm' if (cache / 'k.bin').exists() else 'cold'); cache.mkdir(parents=True, exist_ok=True); "
            "(cache / 'k.bin').write_bytes(b'x' * 1000)"]
ABSENT = object()  # a done.json without a kernel_cache


@pytest.fixture(autouse=True)
def roomy_disk(monkeypatch, tmp_path):
    """The job's work folder and the node cache in the test's own folder, never /work or /cache; the tests' own disk
    always has room, so this machine's free space cannot fail them (the eviction drive passes its own); the test's
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


def submitted(store, repo, job, command, **extra):
    """A job of the echo kind in run r of the store, its input uploaded to its own up folder; its spec."""
    up = ROOT / f"up-{job}"
    local = pathlib.Path(tempfile.mkdtemp()) / "in.txt"
    local.write_text("hello")
    spec = {"kind": "echo", "image": "registry/score-echo:1@sha256:x",
            "code": submit.upload_code(store, ["tools"], kind="echo", repo=repo),
            "inputs": [submit.upload_input(store, "r", job, local, str(up / "in.txt"))],
            "outputs": [{"path": str(up / "out"), "key": submit.output_key("r", job, "out")}],
            "command": command, "models": ["tiny"], "minutes": 1, **extra}
    submit.write_job(store, "r", job, spec)
    return spec


def a_source(folder, text="weights", name="tiny"):
    """A file to seed from, as a url: entry of its own."""
    path = folder / f"{name}.bin"
    path.write_text(text)
    return {"name": name, "source": f"url:{path.as_uri()}", "revision": "v1", "licence": "MIT",
            "commercial_use": True}


def raised(call, *arguments, **keywords):
    """'<error type>: <message>' of what the call raised, '' when it returned."""
    try:
        call(*arguments, **keywords)
    except (SystemExit, RuntimeError, FileNotFoundError) as error:
        return f"{type(error).__name__}: {error}"
    return ""


def stopped(call, *arguments, **keywords):
    """The message the call stopped the process with (SystemExit), '' when it did not."""
    found = raised(call, *arguments, **keywords)
    return found.removeprefix("SystemExit: ") if found.startswith("SystemExit:") else ""


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


def read_whole(reader):
    """Everything a raw reader gives through a buffered reader of 1 MB."""
    with io.BufferedReader(reader, 1 << 20) as buffered:
        return buffered.read()


def test_a_job_runs_once_on_checked_weights(tmp_path, monkeypatch):
    # ---- one run of jobs in one store: each row a job, its runs' exit codes, its failures and its done record ----
    store = stores.FolderStore(tmp_path / "store")
    repo = a_repo()
    script = tmp_path / "not-executable.sh"
    script.write_text("#!/bin/sh\necho hi\n")
    script.chmod(0o644)
    echo = [PYTHON, "tools/echo.py", str(ROOT / "up-j1/in.txt"), str(ROOT / "up-j1/out")]
    blender = {"kind": "blender", "image": "i", "kernel_cache": "blender-5.0.1", "minutes": 1}
    no_start = [("command", "error", "could not start")]
    rows = [  # job, its spec (echo command and extras, or a whole spec), the node and card it runs on, what follows
        {"job": "j1", "echo": (echo, {}), "exits": [0], "state": "done",
         "back": {"a.txt": "HELLO weights", "sub/b.txt": "j1"},  # the input upper-cased, the model's bytes
         "timings": ["pod_start", "weights_ready", "inputs_ready", "first_result", "uploaded"]},
        {"job": "already-done", "echo": ([PYTHON, "-c", "import sys; sys.exit(9)"], {}), "done_before": True,
         "exits": [0], "state": "done"},
        {"job": "limited", "echo": ([PYTHON, "-c", "print('boom'); raise SystemExit(4)"], {"attempt_limit": 2}),
         "exits": [1, 1, jobs.EXIT_NO_ATTEMPTS], "state": "failed",
         "failed": [("command", "log_tail", "boom"), ("command", "log_tail", "boom")]},
        {"job": "slow", "echo": ([PYTHON, "-c", "import time; time.sleep(60)"], {"minutes": 0.02}),
         "exits": [1], "state": "waiting", "failed": [(None, "error", "minutes")]},
        {"job": "empty", "echo": ([PYTHON, "-c", "pass"], {}), "exits": [1], "state": "waiting",
         "failed": [("outputs", None, "")]},
        {"job": "denied", "echo": ([str(script)], {}), "exits": [1], "state": "waiting", "failed": no_start,
         "log": ""},
        {"job": "missing", "echo": (["/no/such/program"], {}), "exits": [1], "state": "waiting", "failed": no_start,
         "log": ""},
        {"job": "one", "spec": {**blender, "command": COMPILES}, "node": "node-a", "card": CARD, "exits": [0],
         "state": "done", "log": "cold",
         "kernel": {"name": "blender-5.0.1", "card": CARD, "restored": False, "uploaded_bytes": 1000}},
        {"job": "two", "spec": {**blender, "command": COMPILES}, "node": "node-b", "card": CARD, "exits": [0],
         "state": "done", "log": "warm",  # no larger than the store's: nothing uploaded
         "kernel": {"name": "blender-5.0.1", "card": CARD, "restored": True, "uploaded_bytes": 0}},
        {"job": "cpu", "spec": {**blender, "command": [PYTHON, "-c", "pass"]}, "node": "node-b", "card": None,
         "exits": [0], "state": "done", "kernel": ABSENT},
    ]
    for row in rows:
        job = row["job"]
        monkeypatch.setattr(weights, "CACHE", tmp_path / row.get("node", "cache"))
        monkeypatch.setattr(kernels, "card_key", lambda card=row.get("card"): card)
        if "spec" in row:
            submit.write_job(store, "r", job, row["spec"])
        else:
            submitted(store, repo, job, row["echo"][0], **row["echo"][1])
        if row.get("done_before"):
            stores.write_json(store, f"runs/r/{job}/done.json", {"attempt": 1})
        assert submit.state(store, "r", job) == ("done" if row.get("done_before") else "waiting"), job
        assert [jobs.run_job(store, "r", job) for _ in row["exits"]] == row["exits"], job
        assert submit.state(store, "r", job) == row["state"], job
        failed = submit.failures(store, "r", job)
        assert [record["attempt"] for record in failed] == list(range(1, len(row.get("failed", [])) + 1)), job
        for record, (stage, field, text) in zip(failed, row.get("failed", [])):
            assert stage is None or record["stage"] == stage, (job, record)
            assert field is None or text in "\n".join(record[field] if field == "log_tail" else [record[field]]), job
        if "log" in row:
            assert row["log"] in store.read_bytes(f"runs/r/{job}/log-1.txt").decode(), job
        if "kernel" in row:
            assert submit.done(store, "r", job).get("kernel_cache", ABSENT) == row["kernel"], job
        if "timings" in row:
            assert list(submit.done(store, "r", job)["timings"]) == row["timings"], job
        if "back" in row:
            submit.fetch_outputs(store, "r", job, {str(ROOT / f"up-{job}/out"): tmp_path / "back" / job})
            assert {name: (tmp_path / "back" / job / name).read_text() for name in row["back"]} == row["back"], job

    # the code those jobs ran: one key by content, times and caches left out
    first = submit.bundle(["tools"], repo)
    os.utime(repo / "tools/echo.py", (1, 1))  # another time, the same content
    assert submit.bundle(["tools"], repo) == first
    code = stores.read_json(store, "runs/r/j1/job.json")["code"]
    assert code.startswith("code/") and store.exists(code)
    assert all("__pycache__" not in str(name) for name in submit.bundled_files(["tools"], repo))

    # ---- one model, six jobs side by side on a node: seeded once into the store, room made beside its tar ----
    weights_store = stores.FolderStore(tmp_path / "weights-store")
    content = "x" * (3 * weights.CHUNK + 5)
    big = a_source(tmp_path, content, name="big")
    fetched, room_asked = [], []
    real_fetch = weights.fetch_into

    def slow_fetch(*arguments):
        fetched.append(1)
        time.sleep(0.2)  # long enough for every other job to ask meanwhile
        return real_fetch(*arguments)
    monkeypatch.setattr(weights, "fetch_into", slow_fetch)
    monkeypatch.setattr(weights, "make_room", lambda cache, needed: room_asked.append(
        (cache.name, needed, len(list(cache.glob("partial/*/model.tar"))))))
    folders = []
    threads = [threading.Thread(target=lambda: folders.append(weights.ready(weights_store, big, tmp_path / "node-a")))
               for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(fetched) == 1 and len(folders) == 6
    assert (folders[0] / "big.bin").read_text() == content and (folders[0] / weights.READY).exists()
    tar = weights_store.read_bytes("weights/big@v1.tar")
    assert weights_store.read_bytes("weights/big@v1.tar.sha256").decode().split()[0] == hashlib.sha256(tar).hexdigest()
    (tmp_path / "big.bin").unlink()  # the source is gone: a second node must take it from the store
    weights_store.download = lambda *arguments: (_ for _ in ()).throw(AssertionError("the tar was downloaded"))
    second = weights.ready(weights_store, big, tmp_path / "node-b")
    assert (second / "big.bin").read_text() == content
    assert not list((tmp_path / "node-b" / "partial").iterdir())
    size = weights_store.size("weights/big@v1.tar")
    assert room_asked == [("node-a", size, 1), ("node-b", size, 0)]  # room for the unpack, beside a seeded tar
    other = stores.FolderStore(tmp_path / "other")
    (tmp_path / "big.bin").write_text(content)
    weights.ready(other, big, tmp_path / "node-c")
    assert other.read_bytes("weights/big@v1.tar") == tar  # one source gives one tar, one sha256
    monkeypatch.setattr(weights, "fetch_into", real_fetch)
    let_go()

    # room is made from the least recently used model no job holds
    node = tmp_path / "node-full"
    for name in ("old", "recent"):
        weights.ready(weights_store, a_source(tmp_path, name=name), node)
    let_go()
    weights.ready(weights_store, a_source(tmp_path, name="held"), node)
    os.utime(node / "weights" / "old@v1" / weights.READY, (1, 1))
    os.utime(node / "weights" / "held@v1" / weights.READY, (0, 0))
    room = lambda: weights.RESERVE if (node / "weights" / "old@v1").exists() else 2 * weights.RESERVE  # noqa: E731
    weights.real_make_room(node, weights.RESERVE, free=room)
    assert sorted(path.parent.name for path in (node / "weights").glob(f"*/{weights.READY}")) == [
        "held@v1", "recent@v1"], "the least recently used free model goes, never one a job holds"
    let_go()

    # ---- a tar refused: each row a model, how its store goes wrong after seeding, what a new node is told ----
    def damage(each_store, name):
        each_store.write_bytes(f"weights/{name}@v1.tar", each_store.read_bytes(f"weights/{name}@v1.tar")[:-1] + b"!")

    def unsummed(each_store, name):
        (each_store.root / "weights" / f"{name}@v1.tar.sha256").unlink()
        each_store.reader = lambda key: (_ for _ in ()).throw(AssertionError("read with no sha256 to check"))
    refusals = [  # name, its entry's own sha256, seeded first, the damage, what ready raises
        ("wrong-sum", "0" * 64, False, None, "RuntimeError", "sha256"),
        ("damaged", None, True, damage, "RuntimeError", "sha256"),
        ("unsummed", None, True, unsummed, "FileNotFoundError", ""),
    ]
    for name, expected_sum, seeded, spoil, error, message in refusals:
        each_store = stores.FolderStore(tmp_path / f"store-{name}")
        entry = {**a_source(tmp_path, name=name), **({"sha256": expected_sum} if expected_sum else {})}
        if seeded:
            weights.ready(each_store, entry, tmp_path / f"seed-{name}")
            let_go()
            spoil(each_store, name)
        found = raised(weights.ready, each_store, entry, tmp_path / f"node-{name}")
        assert found.startswith(error + ":") and message in found, (name, found)
        assert not (tmp_path / f"node-{name}" / "weights" / f"{name}@v1").exists(), name

    # ---- the hub cache: each row a manifest entry, whether it was handed, whether it is linked ----
    entries = [  # name, source, revision, ref, handed, the repository it links to
        ("soma-x-assets", "hf:nvidia/SOMA-X", REVISION, "v0.3.3", True, "models--nvidia--SOMA-X"),
        ("absent", "hf:org/absent", "abc", None, False, None),
        ("plain", "url:https://example.org/plain.bin", "v1", None, True, None),
    ]
    (tmp_path / "models.json").write_text(json.dumps([
        {"name": name, "source": source, "revision": revision, **({"ref": ref} if ref else {})}
        for name, source, revision, ref, _, _ in entries]))
    environment = {}
    for name, _, revision, _, handed, _ in entries:
        if handed:
            model = tmp_path / "weights" / f"{name}@{revision}"
            model.mkdir(parents=True)
            (model / "model.npz").write_text(name)
            environment[weights.environment_name(name)] = str(model)
    hub = tmp_path / "hub"
    made = hf_cache.link_all(tmp_path / "models.json", hub, environment)
    linked = [(place, revision, ref, name) for name, _, revision, ref, _, place in entries if place]
    assert made == [hub / place / "snapshots" / revision for place, revision, _, _ in linked]
    assert sorted(path.name for path in hub.iterdir()) == sorted(place for place, _, _, _ in linked)
    for place, revision, ref, name in linked:
        assert (hub / place / "snapshots" / revision / "model.npz").read_text() == name
        assert (hub / place / "refs" / "main").read_text() == revision
        assert (hub / place / "refs" / ref).read_text() == revision
    again = tmp_path / "again"
    again.mkdir()
    assert hf_cache.link_model(hub, "nvidia/SOMA-X", REVISION, again).resolve() == again.resolve()

    # ---- answers of pure rules and of the store's readers: each row a question, its answer, the right one ----
    not_commercial = {"name": "nc", "commercial_use": False, "licence": "CC-BY-NC-4.0"}
    token = weights.authorised("https://huggingface.co/x", "secret")
    listing = {"siblings": [{"rfilename": name} for name in ("model.safetensors", "README.md", "config.json")]}
    monkeypatch.setattr(urllib.request, "urlopen", lambda request, timeout: io.BytesIO(json.dumps(listing).encode()))
    monkeypatch.setattr(stores, "RANGE_SIZE", 64 * 1024)
    data = os.urandom(5 * 1024 * 1024 + 3)
    folder = stores.FolderStore(tmp_path / "folder")
    folder.write_bytes("weights/a.tar", b"abc")
    bucket = {"endpoint": "https://s3.example", "region": "r", "bucket": "b", "access_key": "a", "secret_key": "s"}

    def fits(size):
        part = stores.part_size(size)
        return part % MEGABYTE == 0 and -(-size // part) <= 1000  # S3's limit on parts
    stopping = {"a bucket store without its bucket is refused", "a job's pipeline naming it stops on the licence"}
    answers = [
        ("a small file keeps 8 MB parts", lambda: stores.part_size(1), 8 * MEGABYTE),
        ("a 5 GB file keeps 8 MB parts", lambda: stores.part_size(5 * 1024 * MEGABYTE), 8 * MEGABYTE),
        *[(f"{size} bytes fit whole-megabyte parts within 1,000", lambda size=size: fits(size), True)
          for size in (8 * 1024 * MEGABYTE, 15 * 1024 * MEGABYTE, 200 * 1024 * MEGABYTE + 7)],
        ("ranges side by side, each broken range asked again, give the object whole and in order",
         lambda: read_whole(stores.RangeReader(FlakyBucket(data), "bucket", "key", len(data))) == data, True),
        ("a folder store's size", lambda: folder.size("weights/a.tar"), 3),
        ("a folder store's reader", lambda: read_whole(folder.reader("weights/a.tar")), b"abc"),
        ("a file:// endpoint is a folder store",
         lambda: type(stores.from_environment({"SCORE_STORE_ENDPOINT": f"file://{ROOT}/s"})), stores.FolderStore),
        ("a bucket store's environment names its bucket",
         lambda: stores.environment(bucket)["SCORE_STORE_BUCKET"], "b"),
        ("a bucket store without its bucket is refused",
         lambda: stopped(stores.from_environment, {"SCORE_STORE_ENDPOINT": "https://s3.example"}),
         "SCORE_STORE_BUCKET"),
        ("a model not for commercial use is refused a pipeline",
         lambda: bool(weights.refusal(not_commercial, tool_only=False)), True),
        ("a model not for commercial use serves a tool", lambda: weights.refusal(not_commercial, tool_only=True), None),
        ("a job's pipeline naming it stops on the licence", lambda: stopped(
            weights.all_ready, None, ["nc"], {"nc": not_commercial}, tool_only=False), "commercial"),
        ("a token rides only on the first request, never a redirect",
         lambda: (token.unredirected_hdrs.get("Authorization"), token.headers), ("Bearer secret", {})),
        ("a repo's files narrowed to the job's globs",
         lambda: weights.hf_files("org/repo", "abc", ["*.safetensors", "*.json"]), ["model.safetensors", "config.json"]),
        ("a repo's files unnarrowed", lambda: len(weights.hf_files("org/repo", "abc")), 3),
        ("a model's environment name", lambda: weights.environment_name("sam2.1-large"), "SCORE_MODEL_SAM2_1_LARGE"),
        ("a card's kernel cache folder", lambda: kernels.environment(pathlib.Path("/cache"), "blender-5.0.1", CARD)[
            "CUDA_CACHE_PATH"], f"/cache/kernels/blender-5.0.1/{CARD}/cuda"),
    ]
    for question, answer, right in answers:
        found = answer()
        assert (right in found) if question in stopping else found == right, (question, found)
