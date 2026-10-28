"""moss_sound.py's invariants: a page's run asks one take of each sound briefed for that page (its first prompt, seed
1, its seconds or 8), and nothing for another page's sounds or a brief with no prompt (#29); after a run, the manifest
credits (model, code, weights, licence) exactly the takes that came back, and the picker's scores.json holds every
share's scores; a cluster share's jobs file, the one that goes up, holds exactly that share's jobs; MOSS goes to the
card a model at a time on this PC's machine only, and that measured need is one this PC's 16 GB card takes.

Break that turns it red: in `write_manifest` drop `if (out / job["file"]).exists()` (takes that never came back are
credited), or in `jobs_for` drop the `brief.get("page") == page` test (another page's sounds are paid for), or in
`here_only` drop `if machine.get("here")` (a rented card's takes made another way), or set THIS_PC_NEED's card_gb
past local.CARD_GB (this PC refuses the claim, as before).
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import moss_sound  # noqa: E402


def test_a_page_asks_one_take_of_each_of_its_briefed_sounds(tmp_path):
    sounds = tmp_path / "sounds.json"
    sounds.write_text(json.dumps({"sounds": {
        "door": {"pick": {"page": "hub", "prompts": ["a heavy door", "a creaky door"], "seconds": 3}},
        "wind": {"pick": {"page": "hub", "prompts": ["wind over a roof"]}},
        "bird": {"pick": {"page": "camp", "prompts": ["a crow"]}},
        "hum": {"pick": {"page": "hub", "prompts": []}},
        "rain": {}}}))
    assert moss_sound.jobs_for("hub", sounds) == [
        {"file": "door__p1__s1.wav", "sound": "door", "prompt": "a heavy door", "seconds": 3, "seed": 1},
        {"file": "wind__p1__s1.wav", "sound": "wind", "prompt": "wind over a roof", "seconds": 8, "seed": 1}]


def test_the_manifest_credits_only_the_takes_that_came_back_and_scores_join(tmp_path):
    jobs = [{"file": "door__p1__s1.wav", "sound": "door"}, {"file": "wind__p1__s1.wav", "sound": "wind"}]
    (tmp_path / "door__p1__s1.wav").write_bytes(b"RIFF")
    (tmp_path / "scores-0.json").write_text(json.dumps({"door__p1__s1.wav": 0.31}))
    (tmp_path / "scores-1.json").write_text(json.dumps({"wind__p1__s1.wav": 0.12}))
    made = moss_sound.write_manifest(tmp_path, jobs)
    assert [take["file"] for take in made] == ["door__p1__s1.wav"]
    assert json.loads((tmp_path / "manifest.json").read_text()) == made
    assert made[0]["licence"] == "Apache-2.0" and made[0]["code"] and made[0]["weights"]
    moss_sound.join_scores(tmp_path)
    assert json.loads((tmp_path / "scores.json").read_text()) == {"door__p1__s1.wav": 0.31, "wind__p1__s1.wav": 0.12}


def test_a_cluster_shares_jobs_file_holds_its_jobs_and_takes_come_back_to_out(tmp_path):
    jobs = [{"sound": "door", "prompt": "a heavy door", "seed": 1, "seconds": 2, "file": "door-1.wav"}]
    job = moss_sound.cluster_job(2, jobs, tmp_path / "jobs-2.json", tmp_path / "out")
    sent = pathlib.Path(job["inputs"][0]["local"])
    assert json.loads(sent.read_text()) == jobs
    assert job["inputs"][0]["path"] == job["command"][1]
    assert [output["local"] for output in job["outputs"]] == [str(tmp_path / "out")]


def test_moss_goes_a_model_at_a_time_only_on_this_pcs_card_and_fits_its_claim_there():
    import local
    assert moss_sound.here_only({"here": True}) == "MOSS_ONE_AT_A_TIME=1 "
    assert moss_sound.here_only({"host": "10.0.0.2"}) == ""
    assert moss_sound.THIS_PC_NEED["card_gb"] < local.TOO_BIG["moss-sound"]  # under all of MOSS on the card at once
    assert local.refusal("moss-sound", {"card_gb": moss_sound.THIS_PC_NEED["card_gb"]}) is None
