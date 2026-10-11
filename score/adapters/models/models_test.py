"""The model adapter keys a node only on pinned images and models.

Run: .venv/bin/python score/adapters/models/models_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

from score.adapters import models  # noqa: E402

MODEL = {"name": "m", "source": "hf:x/m", "revision": "abc", "sha256": "f" * 64, "licence": "Apache-2.0",
         "commercial_use": True}


def images_folder(built, listed):
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "images.json").write_text(json.dumps(built))
    (folder / "kind").mkdir()
    (folder / "kind" / "models.json").write_text(json.dumps(listed))
    return folder


def refused(call):
    try:
        call()
    except models.NotPinned as refusal:
        return str(refusal)
    raise AssertionError("taken")


def test_every_built_kind_in_the_repo_gives_a_pinned_record():
    built = json.loads((models.IMAGES / "images.json").read_text())
    for kind in built:
        found = models.record(kind, tool_only=True)
        assert found["digest"].startswith("sha256:"), kind
        assert all(model["revision"] and model["licence"] for model in found["models"]), kind


def test_an_image_without_a_digest_or_a_model_without_a_pin_is_refused():
    loose_image = images_folder({"kind": {"image": "x:1"}}, [MODEL])
    assert "digest" in refused(lambda: models.record("kind", images=loose_image))
    loose_model = images_folder({"kind": {"image": "x:1", "digest": "sha256:1"}}, [{**MODEL, "revision": ""}])
    assert "revision" in refused(lambda: models.record("kind", images=loose_model))
    assert "no image" in refused(lambda: models.record("other", images=loose_model))


def test_a_model_not_for_commercial_use_needs_a_tool_only_kind():
    folder = images_folder({"kind": {"image": "x:1", "digest": "sha256:1"}}, [{**MODEL, "commercial_use": False}])
    assert "commercial" in refused(lambda: models.record("kind", images=folder))
    assert models.record("kind", tool_only=True, images=folder)["models"][0]["name"] == "m"


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
