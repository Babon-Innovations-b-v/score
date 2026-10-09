"""Checks for the hub cache of links: an hf: model the job was handed is linked in as its repository's snapshot at
its pinned revision with refs/main (and its tag) pointing at it, a url: model or one the job was not handed is left
out, and linking again replaces the old link.

Run: .venv/bin/python tools/cloud/runtime/hf_cache_test.py   (make tests runs it)
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import hf_cache  # noqa: E402

REVISION = "3648707b69e1b1dcf14c473e30613266b786b9f1"


def a_manifest(folder):
    """A models.json with an hf: model carrying a tag, an hf: model not handed to the job, and a url: model."""
    path = folder / "models.json"
    path.write_text(json.dumps([
        {"name": "soma-x-assets", "source": "hf:nvidia/SOMA-X", "revision": REVISION, "ref": "v0.3.3"},
        {"name": "absent", "source": "hf:org/absent", "revision": "abc"},
        {"name": "plain", "source": "url:https://example.org/plain.bin", "revision": "v1"}]))
    return path


def test_a_handed_model_is_its_repositorys_snapshot():
    with tempfile.TemporaryDirectory() as scratch:
        scratch = pathlib.Path(scratch)
        model = scratch / "weights" / f"soma-x-assets@{REVISION}"
        model.mkdir(parents=True)
        (model / "SOMA_neutral.npz").write_text("assets")
        environment = {"SCORE_MODEL_SOMA_X_ASSETS": str(model), "SCORE_MODEL_PLAIN": str(scratch)}
        made = hf_cache.link_all(a_manifest(scratch), scratch / "hub", environment)
        place = scratch / "hub" / "models--nvidia--SOMA-X"
        assert made == [place / "snapshots" / REVISION]
        assert (place / "snapshots" / REVISION / "SOMA_neutral.npz").read_text() == "assets"
        assert (place / "refs" / "main").read_text() == REVISION
        assert (place / "refs" / "v0.3.3").read_text() == REVISION
        assert sorted(path.name for path in (scratch / "hub").iterdir()) == ["models--nvidia--SOMA-X"]


def test_linking_again_replaces_the_link():
    with tempfile.TemporaryDirectory() as scratch:
        scratch = pathlib.Path(scratch)
        first, second = scratch / "first", scratch / "second"
        first.mkdir()
        second.mkdir()
        hf_cache.link_model(scratch / "hub", "org/name", "abc", first)
        snapshot = hf_cache.link_model(scratch / "hub", "org/name", "abc", second)
        assert snapshot.resolve() == second.resolve()


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
