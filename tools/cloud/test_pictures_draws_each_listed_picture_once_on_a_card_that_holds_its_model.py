"""pictures.py's invariants: a listed picture already made is not drawn (or paid for) again; a job naming its scene
is worded in that scene's style and one naming none is worded as listed; each model runs only on cards that hold it
(klein 24 GB, the 20B Qwen-Image-Edit 48 GB: nothing smaller was tried); each job carries the settings of the model
it is drawn with, never the other's; and a cluster share is self-contained: every reference photo its list names goes
up at the name the uploaded list gives it, the pictures back into `out`.

Break that turns it red: in `listed` drop the `not` (made pictures drawn again); in `jobs_to_make` drop the place's
style; or in `cluster_job` leave the refs' full local paths in the uploaded list.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import capacity  # noqa: E402
import pictures  # noqa: E402
import provider  # noqa: E402


def test_a_made_picture_is_not_drawn_again(tmp_path, monkeypatch):
    monkeypatch.setattr(pictures, "PICTURES", tmp_path / "pictures")
    pictures.PICTURES.mkdir()
    (pictures.PICTURES / "crate.png").write_bytes(b"png")
    listing = tmp_path / "jobs.json"
    listing.write_text(json.dumps([{"name": "crate", "wording": "a crate"}, {"name": "tile", "wording": "a tile"}]))
    assert [job["name"] for job in pictures.jobs_to_make(listing)] == ["tile"]


def test_a_job_naming_its_scene_is_worded_in_that_scenes_style(tmp_path, monkeypatch):
    monkeypatch.setattr(pictures, "PICTURES", tmp_path / "pictures")
    listing = tmp_path / "jobs.json"
    listing.write_text(json.dumps([{"name": "crate", "wording": "a crate", "place": "galley"},
                                   {"name": "tile", "wording": "a tile"}]))
    assert pictures.scenes_of(pictures.listed(listing)) == ["galley"]
    crate, tile = pictures.jobs_to_make(listing, "klein", {"galley": "Style line. Its look."})
    assert crate["wording"] == "a crate, in the look of this place: Style line. Its look."
    assert tile["wording"] == "a tile"


def test_each_job_carries_the_settings_of_its_own_model(tmp_path, monkeypatch):
    monkeypatch.setattr(pictures, "PICTURES", tmp_path / "pictures")
    listing = tmp_path / "jobs.json"
    listing.write_text(json.dumps([{"name": "crate", "wording": "a crate", "refs": ["a.png"]}]))
    [klein], [qwen] = (pictures.jobs_to_make(listing, model) for model in ("klein", "qwen-edit"))
    assert qwen["steps"] == 40 and "true_cfg_scale" in qwen["call"] and "true_cfg_scale" not in klein["call"]
    assert klein["refs"] == qwen["refs"] == ["a.png"]


def test_every_model_runs_on_cards_that_hold_it():
    smallest = {"klein": 24, "qwen-edit": 48}
    for model, settings in pictures.MODELS.items():
        classes = capacity.classes_for(settings["kind"])
        assert min(provider.card_gb(machine_class) for machine_class in classes) >= smallest[model], model
    assert pictures.expected_minutes(10, 1, "qwen-edit") > pictures.expected_minutes(10, 1, "klein")


def test_a_cluster_share_carries_every_reference_its_list_names(tmp_path):
    (tmp_path / "a").mkdir()
    ref, other = tmp_path / "photo.jpg", tmp_path / "a" / "back.jpg"
    ref.write_text("jpg")
    other.write_text("jpg")
    jobs = [{"name": "crate", "wording": "a crate", "seed": 7, "steps": 4, "call": {}, "refs": [str(ref), str(other)]},
            {"name": "lamp", "wording": "a lamp", "seed": 7, "steps": 4, "call": {}, "refs": [str(ref)]}]
    job = pictures.cluster_job(1, jobs, tmp_path / "jobs-1.json", tmp_path / "out-1", "qwen-edit")
    up = {item["path"]: item["local"] for item in job["inputs"]}
    assert up[job["command"][2]] == str(tmp_path / "jobs-1.json")
    sent = json.loads((tmp_path / "jobs-1.json").read_text())
    named = {name for entry in sent for name in entry["refs"]}
    assert {f"/root/pics/refs/{name}" for name in named} == set(up) - {job["command"][2]}
    assert sorted(up.values()) == sorted([str(tmp_path / "jobs-1.json"), str(ref), str(other)])
    assert [output["local"] for output in job["outputs"]] == [str(tmp_path / "out-1")]
