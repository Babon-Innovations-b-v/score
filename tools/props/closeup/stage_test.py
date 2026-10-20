"""Checks for the close-up stage's plain steps: the crops, the rows from an inventory, the batches' lists, the cards
a batch takes and the record of what each row cost, without a model, a cloud machine or Nano Banana Pro.

Plain python: python3 tools/props/closeup/stage_test.py
"""
import os
import pathlib
import sys
import tempfile

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import stage  # noqa: E402

ROW = {"id": "cabinet", "words": "a steel cabinet", "size": [1.2, 0.7, 1.0], "box": [100, 100, 200, 150]}


def a_place():
    """A folder with a concept picture, the row pointing at it, and the stage's out folder."""
    folder = pathlib.Path(tempfile.mkdtemp())
    Image.new("RGB", (800, 600), (120, 120, 120)).save(folder / "concept.png")
    return dict(ROW, concept=str(folder / "concept.png")), folder / "out"


def test_a_crop_has_its_margin_and_is_scaled_up():
    cut = stage.crop(Image.new("RGB", (800, 600)), [100, 100, 200, 150])
    assert cut.size == (512, 329)
    assert stage.crop(Image.new("RGB", (800, 600)), [0, 0, 800, 600]).size == (800, 600)


def test_rows_come_from_the_inventory_s_loop_rows_whatever_their_own_kind():
    # #19: the sorter routes a row, not its own kind: a `code` wall with no named failure is the loop's and gets a
    # close-up; the cockpit's thrust indicator, a named pipeline failure, does not; a row with no box gets none.
    inventory = {"scene": "cockpit", "plan": {"views": [{"id": "v1", "picture": "concept.png"}]},
                 "rows": [{"id": "cabinet", "view": "v1", "box": [1, 2, 3, 4], "name": "a steel cabinet",
                           "kind": "generate", "size": [1.2, 0.7, 1.0]},
                          {"id": "wall", "view": "v1", "box": [1, 2, 3, 4], "name": "a wall", "kind": "code",
                           "size": [3, 0.2, 2.8]},
                          {"id": "thrust_indicator", "view": "v1", "box": [1, 2, 3, 4], "name": "a dial",
                           "kind": "code", "size": [0.2, 0.2, 0.1]},
                          {"id": "trim", "view": "v1", "name": "a trim", "kind": "code", "size": [3, 0.1, 0.1]}]}
    assert [row["id"] for row in stage.rows_from_inventory(inventory)] == ["cabinet", "wall"]
    assert stage.rows_from_inventory(inventory)[0] == {"id": "cabinet", "scene": "cockpit", "words": "a steel cabinet",
                                                       "size": [1.2, 0.7, 1.0], "concept": "concept.png",
                                                       "box": [1, 2, 3, 4]}


def test_rows_whose_boxes_the_gate_has_not_passed_are_not_drawn():
    problems = stage.gate_problems([{"id": "cabinet", "words": "a cabinet"},
                                    {"id": "no_such_row", "scene": "camp", "words": "a thing"}])
    assert problems[0].startswith("cabinet: names no scene"), problems
    assert problems[1].startswith("camp.no_such_row: the box gate says no row"), problems
    try:
        stage.run([{"id": "cabinet", "words": "a cabinet"}], pathlib.Path(tempfile.mkdtemp()))
    except SystemExit as stopped:
        assert "box gate" in str(stopped)
    else:
        raise AssertionError("an ungated row was drawn")


def test_the_picture_batch_skips_rows_already_drawn():
    row, out = a_place()
    stage.make_crops([row], out)
    [job] = stage.picture_jobs([row], out)
    assert job["name"] == "closeup-cabinet" and job["refs"] == [str(out / "crops/cabinet.jpg"), row["concept"]]
    assert "a steel cabinet" in job["wording"] and "1.20 m wide" in job["wording"]
    (out / "qwen").mkdir()
    Image.new("RGB", (8, 8)).save(out / "qwen/cabinet.png")
    assert stage.picture_jobs([row], out) == []
    questions = stage.judge_questions([row], out, "qwen")
    assert [question["name"] for question in questions] == [f"cabinet~{seed}" for seed in stage.check.SEEDS]
    assert questions[0]["images"] == [str(out / "crops/cabinet.jpg"), str(out / "qwen/cabinet.png")]


def test_a_row_takes_the_first_picture_that_passed_and_records_its_cost():
    row, out = a_place()
    for take in ("qwen", "pro"):
        (out / take).mkdir(parents=True)
        Image.new("RGB", (8, 8)).save(out / take / "cabinet.png")
    by_qwen = stage.accepted(row, out, {"qwen": []}, 0.12)
    assert by_qwen["accepted"] == "qwen-edit" and by_qwen["pro_dollars"] == 0 and by_qwen["euros"] == 0.12
    by_pro = stage.accepted(dict(row, pro_wording="crop"), out, {"qwen": ["judge: fail"], "pro": []}, 0.2)
    assert by_pro["accepted"] == "nano-banana-pro" and by_pro["take"] == "pro" and by_pro["pro_wording"] == "crop"
    assert by_pro["pro_dollars"] == stage.pro.DOLLARS_A_PICTURE
    gap = stage.accepted(row, out, {"qwen": ["judge: fail"], "pro": ["judge: fail"]}, 0.2)
    assert gap["accepted"] is None and gap["picture"] is None
    totals = stage.summary([by_qwen, by_pro, gap], {"qwen": {"euros": 1.0}, "judge-qwen": {"euros": 0.5}})
    assert totals["by_qwen"] == 1 and totals["by_pro"] == 1 and totals["for_review"] == 1
    assert totals["pro_pictures"] == 2 and totals["cloud_euros_per_accepted"] == 0.75


def test_pro_draws_one_take_a_row_worded_before_it_is_drawn():
    """A batch draws each row once (CONTEXT.md, owner 2026-10-20): the room is chosen free, from the crop's size, not
    as a second paid take for what the crop alone failed."""
    assert stage.PRO_TAKES == ("pro",)
    assert "Image 2" not in stage.PRO_WORDINGS["crop"] and "Image 2" in stage.PRO_WORDINGS["room"]
    body = stage.pro.request_body("words", Image.new("RGB", (8, 8)))
    assert len(body["contents"][0]["parts"]) == 2
    row, _ = a_place()
    assert stage.pro_wording(row) == "room"  # a 100 by 50 box: 140 pixels with its margin, under SHORTEST_CROP
    assert stage.pro_wording(dict(row, box=[100, 100, 600, 400])) == "crop"
    assert stage.with_pro_wordings([dict(row, pro_wording="crop")])[0]["pro_wording"] == "crop"  # chosen once


def test_pro_asks_again_only_for_a_free_refusal_and_an_empty_answer_is_a_gap():
    import urllib.error
    asked, waits = [], []
    answers = [urllib.error.HTTPError("u", 429, "Too Many Requests", {}, None), {"candidates": []}]

    def generate(*arguments, **options):
        asked.append(1)
        answer = answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer
    kept = stage.pro.compute.require_cleared, stage.pro.google_spend.generate, stage.pro.time.sleep
    stage.pro.compute.require_cleared = lambda what: None
    stage.pro.google_spend.generate, stage.pro.time.sleep = generate, waits.append
    try:
        path = pathlib.Path(tempfile.mkdtemp()) / "a.png"
        assert stage.pro.draw("key", "words", Image.new("RGB", (8, 8)), None, path) is False
        assert len(asked) == 2 and len(waits) == 1 and not path.exists()  # the empty answer is not asked again
        answers[:] = [urllib.error.HTTPError("u", 503, "Service Unavailable", {}, None), {"candidates": []}]
        assert stage.pro.draw("key", "words", Image.new("RGB", (8, 8)), None, path) is False
        assert len(asked) == 4 and len(waits) == 2  # an overloaded service bills nothing: asked again after a wait
        answers[:] = [urllib.error.HTTPError("u", 400, "Bad Request", {}, None), {"candidates": []}]
        assert stage.pro.draw("key", "words", Image.new("RGB", (8, 8)), None, path) is False
        assert len(asked) == 5 and len(waits) == 2  # any other refusal is a gap at once
    finally:
        stage.pro.compute.require_cleared, stage.pro.google_spend.generate, stage.pro.time.sleep = kept


def test_a_step_s_cost_is_kept_for_a_run_that_is_run_again():
    path = pathlib.Path(tempfile.mkdtemp()) / "batch.json"
    assert stage.kept_entry(None, path) is None
    assert stage.kept_entry({"euros": 1.4}, path)["euros"] == 1.4
    assert stage.kept_entry(None, path)["euros"] == 1.4
    assert stage.kept_entry({"euros": 0.6}, path)["euros"] == 2.0


def test_pro_draws_nothing_outside_a_cleared_run():
    """Fault (design of 2026-10-11, section 6): pro.draw sent a paid request (USD 0.134 a picture) for any caller,
    outside the runner's gate and the owner's yes."""
    sent = []
    kept = stage.pro.urllib.request.urlopen
    ticket = os.environ.pop(stage.pro.compute.TICKET, None)
    stage.pro.urllib.request.urlopen = lambda *arguments, **options: sent.append(arguments)
    try:
        stage.pro.draw("key", "words", Image.new("RGB", (8, 8)), None, pathlib.Path(tempfile.mkdtemp()) / "a.png")
    except stage.pro.compute.Refused as refusal:
        assert "nothing rents outside a cleared run" in str(refusal)
    else:
        raise AssertionError("a Nano Banana Pro picture was asked for outside a cleared run")
    finally:
        stage.pro.urllib.request.urlopen = kept
        if ticket is not None:
            os.environ[stage.pro.compute.TICKET] = ticket
    assert sent == []


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("stage_test: ok")
