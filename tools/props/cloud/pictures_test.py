"""Checks for the picture runner's models: each job carries its model's settings, and each model runs only on
cards that hold it, without renting anything."""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import capacity  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402


def test_a_job_carries_its_model_s_steps_and_settings():
    with tempfile.TemporaryDirectory() as folder:
        listing = pathlib.Path(folder) / "jobs.json"
        listing.write_text(json.dumps([{"name": "openpics-check-never-made", "wording": "a crate", "refs": ["a.png"]}]))
        for model, settings in pictures.MODELS.items():
            [job] = pictures.jobs_to_make(listing, model)
            assert job["steps"] == settings["steps"] and job["call"] == settings["call"], model
            assert job["wording"] == "a crate" and job["refs"] == ["a.png"]


def test_every_model_runs_on_cards_that_hold_it():
    # A card smaller than the model whole moves it on and off part by part; nothing smaller than these was tried.
    smallest = {"klein": 24, "qwen-edit": 48}
    for model, settings in pictures.MODELS.items():
        classes = capacity.classes_for(settings["kind"])
        assert min(provider.card_gb(machine_class) for machine_class in classes) >= smallest[model], model


def test_the_estimate_follows_the_model():
    assert pictures.expected_minutes(10, 1, "qwen-edit") > pictures.expected_minutes(10, 1, "klein")


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
    print("pictures_test: ok")


def test_a_share_on_the_cluster_draws_with_the_named_model(tmp_path):
    import json
    import pictures

    ref = tmp_path / "photo.jpg"
    ref.write_text("jpg")
    jobs = [{"name": "crate", "wording": "a crate", "seed": 7, "steps": 4, "call": {}, "refs": [str(ref)]}]
    job = pictures.cluster_job(1, jobs, tmp_path / "jobs-1.json", tmp_path / "out-1", "qwen-edit")
    assert json.loads((tmp_path / "jobs-1.json").read_text())[0]["refs"] == ["photo.jpg"]
    assert job["command"][:3] == ["pictures-run", "tools/props/cloud/picture_worker.py", "/root/pics/jobs-1.json"]
    assert job["command"][3] == "QwenImageEditPlusPipeline" and job["models"] == ["qwen-image-edit-2511"]
    assert {"local": str(ref), "path": "/root/pics/refs/photo.jpg"} in job["inputs"]
    assert job["outputs"] == [{"path": "/root/pics/out", "local": str(tmp_path / "out-1")}]
