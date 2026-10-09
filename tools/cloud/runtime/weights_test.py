"""Checks for the node's weights cache against a folder store, no cloud: a model is seeded once from its source and
then taken from the store, checked by sha256, fetched once per node however many jobs ask at once, and a model not
for commercial use serves only a tool's output.

Run: .venv/bin/python tools/cloud/runtime/weights_test.py   (make tests runs it)
"""
import hashlib
import io
import json
import pathlib
import sys
import tempfile
import threading
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import store as stores  # noqa: E402
import weights  # noqa: E402


def a_source(folder, text="weights"):
    """A file to seed from, as a url: entry of its own."""
    path = folder / "model.bin"
    path.write_text(text)
    return {"name": "tiny", "source": f"url:{path.as_uri()}", "revision": "v1", "licence": "MIT",
            "commercial_use": True}


def test_a_model_is_seeded_once_then_taken_from_the_store():
    folder = pathlib.Path(tempfile.mkdtemp())
    store = stores.FolderStore(folder / "store")
    entry = a_source(folder)
    first = weights.ready(store, entry, folder / "node-a")
    assert (first / "model.bin").read_text() == "weights" and (first / weights.READY).exists()
    assert store.exists("weights/tiny@v1.tar") and store.exists("weights/tiny@v1.tar.sha256")
    (folder / "model.bin").unlink()  # the source is gone: a second node must take it from the store
    second = weights.ready(store, entry, folder / "node-b")
    assert (second / "model.bin").read_text() == "weights"
    assert not list((folder / "node-b" / "partial").iterdir())


def test_one_source_gives_one_sha256():
    folder = pathlib.Path(tempfile.mkdtemp())
    entry = a_source(folder)
    digests = []
    for name in ("one", "two"):
        store = stores.FolderStore(folder / name)
        weights.ready(store, entry, folder / f"node-{name}")
        digests.append(store.read_bytes("weights/tiny@v1.tar.sha256"))
    assert digests[0] == digests[1]


def test_a_tar_that_does_not_match_its_sha256_is_refused():
    folder = pathlib.Path(tempfile.mkdtemp())
    store = stores.FolderStore(folder / "store")
    entry = {**a_source(folder), "sha256": "0" * 64}
    try:
        weights.ready(store, entry, folder / "node")
    except RuntimeError as refusal:
        assert "sha256" in str(refusal)
    else:
        raise AssertionError("a wrong sha256 was taken")
    assert not (folder / "node" / "weights" / "tiny@v1").exists()


def test_jobs_side_by_side_on_one_node_fetch_once():
    folder = pathlib.Path(tempfile.mkdtemp())
    store = stores.FolderStore(folder / "store")
    entry = a_source(folder)
    seeded = []
    real_seed = weights.seed
    weights.seed = lambda *arguments: (seeded.append(1), real_seed(*arguments))
    try:
        threads = [threading.Thread(target=weights.ready, args=(store, entry, folder / "node")) for _ in range(6)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        weights.seed = real_seed
    assert len(seeded) == 1


def test_a_model_not_for_commercial_use_serves_only_a_tool():
    entry = {"name": "nc", "commercial_use": False, "licence": "CC-BY-NC-4.0"}
    assert weights.refusal(entry, tool_only=False)
    assert weights.refusal(entry, tool_only=True) is None
    try:
        weights.all_ready(None, ["nc"], {"nc": entry}, tool_only=False)
    except SystemExit as refusal:
        assert "commercial" in str(refusal)
    else:
        raise AssertionError("a non-commercial model ran for a shipped output")


def test_hugging_face_files_are_narrowed_to_the_globs():
    listing = {"siblings": [{"rfilename": name} for name in ("model.safetensors", "README.md", "config.json")]}
    real = urllib.request.urlopen
    urllib.request.urlopen = lambda request, timeout: io.BytesIO(json.dumps(listing).encode())
    try:
        assert weights.hf_files("org/repo", "abc", ["*.safetensors", "*.json"]) == ["model.safetensors",
                                                                                     "config.json"]
        assert len(weights.hf_files("org/repo", "abc")) == 3
    finally:
        urllib.request.urlopen = real


def test_the_token_never_follows_a_redirect():
    request = weights.authorised("https://huggingface.co/x", "secret")
    assert request.unredirected_hdrs.get("Authorization") == "Bearer secret" and not request.headers


def test_the_model_folder_is_named_for_the_command():
    assert weights.environment_name("sam2.1-large") == "SCORE_MODEL_SAM2_1_LARGE"
    assert hashlib.sha256(b"").hexdigest() == weights.sha256_of(pathlib.Path(tempfile.mkstemp()[1]))


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("weights_test: ok")
