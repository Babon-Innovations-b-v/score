"""judge.py's invariants: a question whose answer file is there is never asked (or paid for) again; the judge only
takes cards that hold its 27B FP8 weights (48 GB or more: a 24 GB card ran out of memory); and a cluster share is
self-contained: its question list goes up at the path the command reads, every picture a question names goes up once
at the name the uploaded list gives it, and the answers come back into the answers folder.

Break that turns it red: in `to_ask` drop the `not` (answered questions are asked again); add "gpu-24gb" to the judge
kind's classes in capacity.py; or in `cluster_job` leave the images' full local paths in the uploaded list.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import capacity  # noqa: E402
import judge  # noqa: E402
import provider  # noqa: E402


def test_an_answered_question_is_not_asked_again(tmp_path):
    listing = tmp_path / "questions.json"
    listing.write_text(json.dumps([{"name": "a", "text": "?", "images": []}, {"name": "b", "text": "?", "images": []}]))
    (tmp_path / "a.txt").write_text("{}")
    assert [job["name"] for job in judge.to_ask(listing, tmp_path)] == ["b"]


def test_the_judge_runs_only_on_cards_that_hold_its_weights():
    assert min(provider.card_gb(machine_class) for machine_class in capacity.classes_for(judge.KIND)) >= 48


def test_a_cluster_share_carries_every_picture_its_questions_name(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    crate, lamp = tmp_path / "a" / "crate.png", tmp_path / "b" / "lamp.png"
    crate.write_text("png")
    lamp.write_text("png")
    jobs = [{"name": "crate-shape", "text": "Is it a crate?", "images": [str(crate)], "seed": 1},
            {"name": "pair", "text": "Same thing?", "images": [str(crate), str(lamp)], "seed": 1}]
    job = judge.cluster_job(0, jobs, tmp_path / "jobs-0.json", tmp_path / "out-0")
    up = {item["path"]: item["local"] for item in job["inputs"]}
    assert up[job["command"][-1]] == str(tmp_path / "jobs-0.json")
    sent = json.loads((tmp_path / "jobs-0.json").read_text())
    named = {image for question in sent for image in question["images"]}
    assert {f"/root/judge/in/{name}" for name in named} == set(up) - {job["command"][-1]}
    assert sorted(up.values()) == sorted([str(tmp_path / "jobs-0.json"), str(crate), str(lamp)])
    assert [output["local"] for output in job["outputs"]] == [str(tmp_path / "out-0")]
