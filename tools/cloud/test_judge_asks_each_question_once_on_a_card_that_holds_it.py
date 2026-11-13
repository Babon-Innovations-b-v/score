"""judge.py's invariants: a question whose answer file is there is never asked (or paid for) again; the judge only
takes cards that hold its 27B FP8 weights (48 GB or more: a 24 GB card ran out of memory); and a cluster share is
self-contained: its question list goes up at the path the command reads, every picture a question names goes up once
at the name the uploaded list gives it, and the answers come back into the answers folder.

One world drives both entry points: a question list of three, one already answered, read by `to_ask`, and what it
returns shared out by `cluster_job`, on the judge kind's machine classes.

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


def test_judge_asks_each_question_once_on_a_card_that_holds_it(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    answers = tmp_path / "answers"
    answers.mkdir()
    crate, lamp = tmp_path / "a" / "crate.png", tmp_path / "b" / "lamp.png"
    crate.write_text("png")
    lamp.write_text("png")
    listing = tmp_path / "questions.json"
    listing.write_text(json.dumps([
        {"name": "done", "text": "Answered before?", "images": [], "seed": 1},
        {"name": "crate-shape", "text": "Is it a crate?", "images": [str(crate)], "seed": 1},
        {"name": "pair", "text": "Same thing?", "images": [str(crate), str(lamp)], "seed": 1}]))
    (answers / "done.txt").write_text("{}")

    jobs = judge.to_ask(listing, answers)
    assert [job["name"] for job in jobs] == ["crate-shape", "pair"]
    assert min(provider.card_gb(machine_class) for machine_class in capacity.classes_for(judge.KIND)) >= 48

    job = judge.cluster_job(0, jobs, tmp_path / "jobs-0.json", tmp_path / "out-0")
    up = {item["path"]: item["local"] for item in job["inputs"]}
    assert up[job["command"][-1]] == str(tmp_path / "jobs-0.json")
    sent = json.loads((tmp_path / "jobs-0.json").read_text())
    assert [question["name"] for question in sent] == ["crate-shape", "pair"]
    named = {image for question in sent for image in question["images"]}
    assert {f"/root/judge/in/{name}" for name in named} == set(up) - {job["command"][-1]}
    assert sorted(up.values()) == sorted([str(tmp_path / "jobs-0.json"), str(crate), str(lamp)])
    assert [output["local"] for output in job["outputs"]] == [str(tmp_path / "out-0")]
