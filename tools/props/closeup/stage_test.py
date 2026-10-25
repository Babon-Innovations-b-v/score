"""Checks for the close-up stage's plain steps: the crops, the rows from an inventory, the batches' lists, the cards
a batch takes and the record of what each row cost, without a model, a cloud machine or Nano Banana Pro.

Plain python: python3 tools/props/closeup/stage_test.py
"""
import json
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
    # #19: a row's own kind routes nothing: a `code` wall is the loop's and gets a close-up; a mechanic row (made on
    # its own line) does not; a row with no box gets none.
    inventory = {"scene": "cockpit", "plan": {"views": [{"id": "v1", "picture": "concept.png"}]},
                 "rows": [{"id": "cabinet", "view": "v1", "box": [1, 2, 3, 4], "name": "a steel cabinet",
                           "kind": "generate", "size": [1.2, 0.7, 1.0]},
                          {"id": "wall", "view": "v1", "box": [1, 2, 3, 4], "name": "a wall", "kind": "code",
                           "size": [3, 0.2, 2.8]},
                          {"id": "thrust_indicator", "view": "v1", "box": [1, 2, 3, 4], "name": "a dial",
                           "kind": "mechanic", "size": [0.2, 0.2, 0.1]},
                          {"id": "trim", "view": "v1", "name": "a trim", "kind": "code", "size": [3, 0.1, 0.1]}]}
    assert [row["id"] for row in stage.rows_from_inventory(inventory)] == ["cabinet", "wall"]
    assert stage.rows_from_inventory(inventory)[0] == {
        "id": "cabinet", "scene": "cockpit", "words": "a steel cabinet", "size": [1.2, 0.7, 1.0],
        "concept": "concept.png", "box": [1, 2, 3, 4]}


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


def test_pro_draws_a_take_and_strict_retries_worded_before_it_is_drawn():
    """The room is chosen free, from the crop's size, not as a second paid take for what the crop alone failed; a
    rejected picture's retries ask the same more strictly, the later ones firmer and on their own seeds, so each
    request is a new one; the first two are asked as before, so a kept picture reads back from the cache (owner,
    2026-10-24 and 2026-10-25)."""
    assert stage.PRO_TAKES == ("pro", "retry", "retry-2", "retry-3")
    assert "Image 2" not in stage.PRO_WORDINGS["crop"] and "Image 2" in stage.PRO_WORDINGS["room"]
    row, out = a_place()
    row = dict(row, pro_wording="crop")
    stage.make_crops([row], out)
    asks = [stage.pro_ask(row, out, take) for take in stage.PRO_TAKES]
    assert asks[1][0] == asks[0][0] + stage.RETRY and "ONLY the object" in asks[1][0]
    assert asks[2][0] == asks[3][0] == asks[1][0] + stage.FIRMER and "Exactly one copy" in asks[2][0]
    assert [ask[3] for ask in asks] == [None, None, 2, 3]
    bodies = [stage.pro.request_body(*ask) for ask in asks]
    assert len({json.dumps(body, sort_keys=True) for body in bodies}) == 4
    assert "seed" not in bodies[0]["generationConfig"] and bodies[3]["generationConfig"]["seed"] == 3
    assert bodies[0] == stage.pro.request_body(*asks[0][:3])  # the first two requests as they were


def test_the_close_up_is_asked_for_and_checked_at_the_objects_own_size_from_the_checks_view():
    """Owner, 2026-10-24: a plan's item is the footprint an object is laid in (2 to 8 times a small thing's size), so
    the request, the judge and the measurements take its reading's size; and the request states the check's look-down
    angle, so a flat object is drawn as the check expects it."""
    row, out = a_place()
    own = dict(row, read_size=[0.3, 0.2, 0.4])
    assert stage.object_size(own) == [0.3, 0.2, 0.4] and stage.object_size(row) == row["size"]
    assert "0.30 m wide, 0.20 m deep and 0.40 m tall" in stage.wording(own, stage.PRO_WORDINGS["crop"])
    for words in stage.PRO_WORDINGS["crop"], stage.PRO_WORDINGS["room"]:
        assert f"looking down on it from about {stage.check.LOOK_DOWN_DEGREES:.0f} degrees above level" in words
        assert f"turned about {stage.check.TURN_DEGREES:.0f} degrees" in words
    stage.make_crops([own], out)
    (out / "qwen").mkdir()
    Image.new("RGB", (8, 8)).save(out / "qwen/cabinet.png")
    assert "0.30 m wide" in stage.judge_questions([own], out, "qwen")[0]["text"]
    body = stage.pro.request_body("words", Image.new("RGB", (8, 8)))
    assert len(body["contents"][0]["parts"]) == 2
    row, _ = a_place()
    assert stage.pro_wording(row) == "room"  # a 100 by 50 box: 140 pixels with its margin, under SHORTEST_CROP
    assert stage.pro_wording(dict(row, box=[100, 100, 600, 400])) == "crop"
    assert stage.with_pro_wordings([dict(row, pro_wording="crop")])[0]["pro_wording"] == "crop"  # chosen once


def test_a_person_is_drawn_alone_front_on_in_the_rigs_a_pose_never_the_concepts_pose():
    """The people layer's own close-up wording (CONTEXT.md "layer adapter"): one member of a crowd row, front on,
    arms and legs apart, whatever the crop shows; it needs no size (the rig sizes the body)."""
    row, _ = a_place()
    person = dict(row, words="crowd", layer="people", size=None)
    assert stage.pro_wording(person) == "person"
    words = stage.wording(person, stage.PRO_WORDINGS["person"])
    assert "The person: crowd." in words and "A-pose" in words and "never their pose" in words
    assert "Image 2" not in words and "three quarters" not in words


def a_picture_answer():
    """A generateContent answer holding one small picture, priced as a 2K picture."""
    import base64
    import io
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, "PNG")
    return {"candidates": [{"content": {"parts": [{"inlineData": {"data": base64.b64encode(buffer.getvalue())
                                                                  .decode()}}]}}],
            "usageMetadata": {"promptTokenCount": 600, "candidatesTokenCount": 1120, "serviceTier": "standard",
                              "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1120}]}}


def test_pro_draws_a_step_as_one_batch_job_at_half_price_cached_and_an_unanswered_one_is_a_gap():
    """Owner, 2026-10-24 ("Make close-ups really use the batch rate"): a step's Pro close-ups go to Google as one
    Batch API job with the same request each would have been sent alone, priced at the batch tier on the Google
    ledger and cached; an answer with no picture, or one the batch did not give, is a gap; one asked before is free."""
    folder = pathlib.Path(tempfile.mkdtemp())
    spend, batch = stage.pro.google_spend, stage.pro.google_batch
    sent = []

    def send(model, request, api_key):
        sent.append(request)
        return {"name": f"batches/{len(sent)}"}

    def status(name, api_key):
        requests = sent[int(name.split("/")[1]) - 1]["batch"]["input_config"]["requests"]["requests"]
        answers = {"a": a_picture_answer(), "b": {"candidates": []}}
        inlined = [{"metadata": item["metadata"], "response": answers[pathlib.Path(item["metadata"]["key"]).stem]}
                   for item in requests if not item["metadata"]["key"].endswith("c.png")]
        return {"name": name, "done": True, "metadata": {"state": "JOB_STATE_SUCCEEDED"},
                "response": {"inlinedResponses": {"inlinedResponses": inlined}}}
    kept = (stage.pro.compute.require_cleared, spend.LEDGER, spend.CACHE, batch.send, batch.status)
    stage.pro.compute.require_cleared = lambda what: None
    spend.LEDGER, spend.CACHE, batch.send, batch.status = folder / "ledger.jsonl", folder / "cache", send, status
    try:
        asks = {folder / f"{name}.png": (f"words {name}", Image.new("RGB", (8, 8)), None) for name in "abc"}
        drawn = stage.pro.draw("key", asks)
        assert drawn == {folder / "a.png": True, folder / "b.png": False, folder / "c.png": False}, drawn
        assert len(sent) == 1 and (folder / "a.png").exists() and not (folder / "b.png").exists()
        requests = sent[0]["batch"]["input_config"]["requests"]["requests"]
        assert [item["request"] for item in requests] == [stage.pro.request_body(*asks[path]) for path in sorted(asks)]
        lines = [json.loads(line) for line in spend.LEDGER.read_text().splitlines()]
        assert [line["state"] for line in lines].count("started") == 3
        finished = [line for line in lines if line["state"] == "finished"]
        assert [line["tier"] for line in finished] == ["batch", "batch"]
        assert all(line["caller"] == "pro" for line in lines)
        full = spend.dollars(stage.pro.MODEL, a_picture_answer()["usageMetadata"])
        assert finished[0]["dollars"] == round(full * 0.5, 6), finished  # half the standard tier's price
        assert [line["state"] for line in lines].count("failed") == 1  # c: unanswered, maybe billed
        (folder / "a.png").unlink()
        assert stage.pro.draw("key", {folder / "a.png": asks[folder / "a.png"]}) == {folder / "a.png": True}
        assert len(sent) == 1  # asked before: read back from the cache, free
        stage.pro.draw("key", {folder / "b.png": asks[folder / "b.png"]})
        assert len(sent) == 2  # no picture came back: dropped from the cache, a new batch may ask again
    finally:
        stage.pro.compute.require_cleared, spend.LEDGER, spend.CACHE, batch.send, batch.status = kept


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
    kept = stage.pro.google_batch.send
    ticket = os.environ.pop(stage.pro.compute.TICKET, None)
    stage.pro.google_batch.send = lambda *arguments, **options: sent.append(arguments)
    try:
        path = pathlib.Path(tempfile.mkdtemp()) / "a.png"
        stage.pro.draw("key", {path: ("words", Image.new("RGB", (8, 8)), None)})
    except stage.pro.compute.Refused as refusal:
        assert "nothing rents outside a cleared run" in str(refusal)
    else:
        raise AssertionError("a Nano Banana Pro picture was asked for outside a cleared run")
    finally:
        stage.pro.google_batch.send = kept
        if ticket is not None:
            os.environ[stage.pro.compute.TICKET] = ticket
    assert sent == []


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("stage_test: ok")
