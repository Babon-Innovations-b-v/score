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

# Per model: the smallest card that holds it, its steps, whether its call carries Qwen's true CFG, and the model
# it must be slower than on the same list.
MODELS = {
    "klein": {"card_gb": 24, "steps": pictures.picture.STEPS, "true_cfg": False, "slower_than": None},
    "qwen-edit": {"card_gb": 48, "steps": 40, "true_cfg": True, "slower_than": "klein"},
}


def test_pictures_draws_each_listed_picture_once_on_a_card_that_holds_its_model(tmp_path, monkeypatch):
    monkeypatch.setattr(pictures, "PICTURES", tmp_path / "pictures")
    pictures.PICTURES.mkdir()
    (pictures.PICTURES / "barrel.png").write_bytes(b"png")
    (tmp_path / "a").mkdir()
    ref, other = tmp_path / "photo.jpg", tmp_path / "a" / "back.jpg"
    ref.write_text("jpg")
    other.write_text("jpg")
    listing = tmp_path / "jobs.json"
    listing.write_text(json.dumps([
        {"name": "barrel", "wording": "a barrel", "place": "attic"},
        {"name": "crate", "wording": "a crate", "place": "galley", "refs": [str(ref), str(other)]},
        {"name": "lamp", "wording": "a lamp", "refs": [str(ref)]},
        {"name": "tile", "wording": "a tile"}]))
    assert pictures.scenes_of(pictures.listed(listing)) == ["galley"]
    assert set(MODELS) == set(pictures.MODELS)
    for model, expect in MODELS.items():
        jobs = pictures.jobs_to_make(listing, model, {"galley": "Style line. Its look."})
        assert [job["name"] for job in jobs] == ["crate", "lamp", "tile"], model
        crate, lamp, tile = jobs
        assert crate["wording"] == "a crate, in the look of this place: Style line. Its look.", model
        assert (lamp["wording"], tile["wording"]) == ("a lamp", "a tile"), model
        assert crate["refs"] == [str(ref), str(other)] and lamp["refs"] == [str(ref)] and tile["refs"] == [], model
        assert all(job["steps"] == expect["steps"] for job in jobs), model
        assert all(("true_cfg_scale" in job["call"]) == expect["true_cfg"] for job in jobs), model
        classes = capacity.classes_for(pictures.MODELS[model]["kind"])
        assert min(provider.card_gb(machine_class) for machine_class in classes) >= expect["card_gb"], model
        if expect["slower_than"]:
            assert pictures.expected_minutes(10, 1, model) > pictures.expected_minutes(10, 1, expect["slower_than"])

        share = pictures.cluster_job(1, jobs, tmp_path / f"jobs-{model}.json", tmp_path / f"out-{model}", model)
        up = {item["path"]: item["local"] for item in share["inputs"]}
        assert up[share["command"][2]] == str(tmp_path / f"jobs-{model}.json"), model
        sent = json.loads((tmp_path / f"jobs-{model}.json").read_text())
        named = {name for entry in sent for name in entry["refs"]}
        assert {f"/root/pics/refs/{name}" for name in named} == set(up) - {share["command"][2]}, model
        assert sorted(up.values()) == sorted([str(tmp_path / f"jobs-{model}.json"), str(ref), str(other)]), model
        assert [output["local"] for output in share["outputs"]] == [str(tmp_path / f"out-{model}")], model
