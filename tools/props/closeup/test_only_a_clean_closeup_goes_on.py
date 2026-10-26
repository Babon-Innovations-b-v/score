"""Only a clean close-up goes on to the 3D step, and it is asked for the way the check judges it: the shape check
(check.py) faults a picture that is not one whole object on a plain ground at the row's own proportions from the one
stated view (from straight above for a row that lies flat; a person by arms clear of the body, never a box), and the
judge's answers pass it only by a majority of clean yeses; the stage (stage.py) crops each row from its concept, draws
only the rows the box gate passed and not drawn yet, asks every Pro take as a new request on the crop alone where the
room would be drawn, and Pro (pro.py) sends a step's close-ups as one half-price batch, caches what it got and draws
nothing outside a cleared run.

No model, no cloud machine and no Nano Banana Pro: pictures are drawn here with known boxes, the batch is faked at
google_batch's send and status, the ledger and cache are this test's own.

Wording checks guarding owner rules (they say so where they stand): the request states the object's own size and the
check's view (owner, 2026-10-24), a person is drawn in the rig's A-pose (CONTEXT.md "layer adapter").

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_one_object_on_a_plain_background_passes_the_measurements: check.measure's `"fill": float(max(` made `min(`.
- test_a_small_object_is_faulted: frame_faults' `if measures["fill"] < FILL_MIN:` made `if False:`.
- test_two_objects_are_faulted: measure's `"one_piece": float(max(sizes) / ...)` made `float(1.0)`.
- test_an_object_cut_by_the_edge_is_faulted: frame_faults' `if measures["border_clean"] < BORDER_CLEAN:` made
  `if False:`.
- test_a_wrong_proportion_is_faulted: measured_faults' `> PROPORTION_LIMIT` made `> 5`.
- test_an_object_is_held_to_its_one_stated_look_down: proportion_error's last line made a best fit over 6 to 60
  degrees (`min(abs(math.log(seen / expected_proportion(size, down))) for down in range(6, 61))`, the range 9ef3c78c
  tried and 2026-10-25 took out).
- test_a_row_that_lies_flat_is_held_to_its_face_from_straight_above: proportion_error's `if lies_flat(size):` made
  `if False:`; and, apart, lies_flat's `tall == smallest and ` dropped (the poster on its edge then lies flat).
- test_a_persons_close_up_needs_its_arms_clear_of_the_body: person_faults' `if share < ARMS_APART:` made `if False:`.
- test_a_persons_arms_are_found_apart_on_a_backdrop_lighter_behind_the_figure: figure_of's `for _ in range(3):` made
  `range(1)` (the backdrop fitted to the edges alone, #26's 0.00).
- test_the_answer_is_the_last_json_object_in_the_reply: answer_of stops at the first object (`break` after it).
- test_the_judge_passes_only_a_clean_yes: judged_faults' `faults += [f"judge: adds {part}" ...]` dropped.
- test_most_of_the_judges_answers_decide: voted_faults' `len(failing) * 2 < len(answers)` made
  `len(failing) < len(answers)`.
- test_a_crop_has_its_margin_and_is_scaled_up: crop_bounds' `margin = MARGIN * max(...)` made `margin = 0`.
- test_rows_come_from_the_inventorys_loop_rows_whatever_their_own_kind: rows_from_inventory's
  `row.get("kind") != "mechanic"` made `row.get("kind") == "generate"`.
- test_rows_whose_boxes_the_gate_has_not_passed_are_not_drawn: run's `if problems:` made `if False:`.
- test_the_picture_batch_skips_rows_already_drawn: picture_jobs' `if not (out / "qwen" / ...).exists()` dropped.
- test_a_row_takes_the_first_picture_that_passed_and_records_its_cost: accepted's `if not faults[take]` made
  `if faults[take]`.
- test_every_pro_take_is_a_new_request_and_a_gaps_later_takes_stand_upright_on_the_crop: pro_ask's
  `index if index > 1 else None` made `None` (retry-2 and retry-3 then the same request); and, apart, pro_ask's
  `named = "crop" if later else named` made `named = named`.
- test_the_close_up_is_asked_for_and_checked_at_the_objects_own_size: object_size returns `row["size"]`; and, apart,
  pro_wording's `if row.get("far"): return "crop"` dropped.
- test_a_person_is_drawn_alone_front_on_in_the_rigs_a_pose: pro_wording's `if row.get("layer") == "people": return
  "person"` dropped.
- test_pro_draws_a_step_as_one_batch_job_cached_and_a_pictureless_answer_is_a_gap: pro.saved's no-picture branch
  `return False` made `return True`; and, apart, pro.draw sending one batch a request (`google_batch.generate(MODEL,
  {path: body}, ...)` per path).
- test_pro_draws_nothing_outside_a_cleared_run: pro.draw's `compute.require_cleared(...)` dropped.
- test_a_steps_cost_is_kept_for_a_run_that_is_run_again: kept_entry's `path.write_text(...)` dropped.
"""
import base64
import io
import json
import pathlib
import sys

import numpy as np
import pytest
from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import stage  # noqa: E402

FIXTURES = HERE / "fixtures"
GREY = (205, 205, 205)
SIZE = (0.6, 0.5, 1.0)
ROW = {"id": "cabinet", "words": "a steel cabinet", "size": [1.2, 0.7, 1.0], "box": [100, 100, 200, 150]}
GOOD = {"one_object": True, "clean": True, "whole": True, "same_object": True, "proportions": True,
        "missing_parts": [], "added_parts": [], "shape_score": 8, "verdict": "pass"}
FAULT = "proportions off the row's box"


def drawn(folder, boxes, side=512, background=GREY):
    """A picture of dark boxes on a plain background, saved in `folder`; its path."""
    picture = Image.new("RGB", (side, side), background)
    draw = ImageDraw.Draw(picture)
    for box in boxes:
        draw.rectangle(box, fill=(60, 70, 80))
    path = folder / f"closeup-{len(list(folder.glob('*.png')))}.png"
    picture.save(path)
    return path


def centred(height_share_of_width, side=512, fill=0.7):
    """A box whose outline is `height_share_of_width` tall for its width, its longer side `fill` of the frame."""
    if height_share_of_width >= 1:
        height = fill * side
        width = height / height_share_of_width
    else:
        width = fill * side
        height = width * height_share_of_width
    left, top = (side - width) / 2, (side - height) / 2
    return (left, top, left + width, top + height)


def faulted(folder, box, size):
    return check.measured_faults(check.measure(drawn(folder, [box]), size))


def test_one_object_on_a_plain_background_passes_the_measurements(tmp_path):
    measures = check.measure(drawn(tmp_path, [centred(check.expected_proportion(SIZE))]), SIZE)
    assert measures["border_clean"] > 0.99 and measures["one_piece"] > 0.99
    assert abs(measures["fill"] - 0.7) < 0.02 and measures["proportion_error"] < 0.05
    assert check.measured_faults(measures) == []


def test_a_small_object_is_faulted(tmp_path):
    box = centred(check.expected_proportion(SIZE), fill=0.3)
    assert "object small in the frame" in faulted(tmp_path, box, SIZE)


def test_two_objects_are_faulted(tmp_path):
    one = check.measured_faults(check.measure(drawn(tmp_path, [(60, 150, 220, 400)]), (1.0, 0.5, 1.0)))
    two = check.measured_faults(check.measure(drawn(tmp_path, [(60, 150, 220, 400), (290, 150, 450, 400)]),
                                              (1.0, 0.5, 1.0)))
    assert "more than one object" not in one and "more than one object" in two


def test_an_object_cut_by_the_edge_is_faulted(tmp_path):
    assert "background not plain to the edge" in faulted(tmp_path, (0, 100, 300, 512), SIZE)


def test_a_wrong_proportion_is_faulted(tmp_path):
    """A 400 x 100 px bar (0.25 tall for its width) for a box 1.2 m tall on a 0.4 m square: about 2.3 expected."""
    assert FAULT in faulted(tmp_path, (56, 200, 456, 300), (0.4, 0.4, 1.2))


def test_an_object_is_held_to_its_one_stated_look_down(tmp_path):
    """A low cabinet 4 wide, 5 deep, 1 tall, turned 35 degrees: its outline is 4 cos 35 + 5 sin 35 = 6.14 wide and
    cos d + (4 sin 35 + 5 cos 35) sin d tall, so 0.43 tall for its width from 15 degrees down and 0.85 from 45. The
    45 degree picture is faulted, the 15 degree one passes: no best fit over a range of views."""
    cabinet = (4.0, 5.0, 1.0)
    assert not check.lies_flat(cabinet)
    for down, share, passes in ((45, 0.85, False), (15, 0.43, True)):
        height = 358 * share
        assert (FAULT not in faulted(tmp_path, (77, 256 - height / 2, 435, 256 + height / 2), cabinet)) is passes, down


def test_a_row_that_lies_flat_is_held_to_its_face_from_straight_above(tmp_path):
    """Batch 1 try 4 (2026-10-25): from the stated look-down a rug's outline is nearly all view. A row that lies flat
    is checked from straight above: a 1 x 3 m rug drawn 1 x 3 or 3 x 1 passes, drawn square it is faulted, and a
    2 x 3 m one drawn as the old 15 degree view shows it (0.28 tall for its width, no face of it) is faulted. A poster
    sized thin in depth stands on its edge, a pipe is slender, a cabinet is chunky: none lies flat."""
    rug = (1.0, 3.0, 0.02)
    assert check.lies_flat(rug) and check.look_down(rug) == 90.0
    assert not check.lies_flat((0.4, 0.01, 0.6)) and not check.lies_flat((0.1, 0.1, 4.0))
    assert not check.lies_flat((0.6, 0.5, 0.8))
    assert FAULT not in faulted(tmp_path, (196, 76, 316, 436), rug)
    assert FAULT not in faulted(tmp_path, (76, 196, 436, 316), rug)
    assert FAULT in faulted(tmp_path, (106, 106, 406, 406), rug)
    height = 358 * 0.28
    assert FAULT in faulted(tmp_path, (77, 256 - height / 2, 435, 256 + height / 2), (2.0, 3.0, 0.02))


def shaded_backdrop(side):
    """A studio backdrop as Nano Banana Pro draws it: grey at the edges, about 20 lighter behind the figure."""
    rows, columns = np.mgrid[0:side, 0:side] / side - 0.5
    light = 200 + 22 * np.clip(1 - 2 * np.hypot(rows, columns), 0, 1)
    return Image.fromarray(np.repeat(light[..., None], 3, axis=2).astype(np.uint8))


def a_person(folder, arms_out, side=512, shaded=False):
    """A dark figure on the grey (`shaded`: lighter behind the figure): head, torso and legs apart, its arms angled
    down `arms_out` pixels clear of the torso at the hands (0: hanging against it); its path."""
    picture = shaded_backdrop(side) if shaded else Image.new("RGB", (side, side), GREY)
    draw = ImageDraw.Draw(picture)
    dark = (60, 70, 80)
    draw.ellipse((236, 60, 276, 100), fill=dark)  # head
    draw.rectangle((226, 100, 286, 260), fill=dark)  # torso
    draw.polygon([(226, 260), (256, 260), (236, 450), (206, 450)], fill=dark)  # legs, apart
    draw.polygon([(256, 260), (286, 260), (306, 450), (276, 450)], fill=dark)
    for side_sign, shoulder in ((-1, 226), (1, 286)):
        draw.line([(shoulder, 108), (shoulder + side_sign * arms_out, 240)], fill=dark, width=14)
    path = folder / f"person-{arms_out}-{shaded}.png"
    picture.save(path)
    return path


def arms_fused(faults):
    return any(fault.startswith("arms not clear of the body") for fault in faults)


def test_a_persons_close_up_needs_its_arms_clear_of_the_body(tmp_path):
    """The people layer's close-up: drawn in the rig's A-pose, so no box's outline holds it; arms hanging against the
    torso (Pixal3D fuses them, Nev 2026-10-10) fail it."""
    assert check.person_faults(a_person(tmp_path, arms_out=70)) == []
    assert arms_fused(check.person_faults(a_person(tmp_path, arms_out=0)))
    assert check.measure(a_person(tmp_path, arms_out=70), None)["proportion_error"] is None


def test_a_persons_arms_are_found_apart_on_a_backdrop_lighter_behind_the_figure(tmp_path):
    """Nano Banana Pro's backdrop is lighter in the middle than at the edges; the first people benchmark's two
    close-ups (#26, 2026-10-21, arms well apart) scored 0.00 when the backdrop came from the edges alone."""
    for picture in ("pro-player_wide-work.jpg", "pro-kit_m_avg-coat-grey.jpg"):
        assert check.person_faults(FIXTURES / picture) == [], picture
    assert check.person_faults(a_person(tmp_path, arms_out=70, shaded=True)) == []
    assert arms_fused(check.person_faults(a_person(tmp_path, arms_out=0, shaded=True)))


def test_the_answer_is_the_last_json_object_in_the_reply():
    reply = 'thinking about {"a": 1} ... done.\n{"one_object": true, "verdict": "fail"}'
    assert check.answer_of(reply) == {"one_object": True, "verdict": "fail"}
    assert check.answer_of("no json here") is None


def test_the_judge_passes_only_a_clean_yes():
    assert check.judged_faults(GOOD) == []
    assert check.judged_faults(dict(GOOD, added_parts=["armrests"])) == ["judge: adds armrests"]
    assert check.judged_faults(dict(GOOD, shape_score=6)) == ["judge: shape score 6"]  # the pass needs 7
    assert "judge: not clean" in check.judged_faults(dict(GOOD, clean=False))
    assert check.judged_faults(None) == ["the judge gave no answer"]


def test_most_of_the_judges_answers_decide():
    bad = dict(GOOD, verdict="fail")
    assert check.voted_faults([GOOD, GOOD, bad]) == []
    assert check.voted_faults([GOOD, bad, None]) == ["judge: fail", "judge: 1 of 3 answers passed"]
    assert check.faults({"border_clean": 1.0, "fill": 0.7, "one_piece": 1.0, "proportion_error": 0.1},
                        [GOOD, bad, GOOD]) == []


def a_place(folder):
    """A concept picture, the row pointing at it, and the stage's out folder."""
    Image.new("RGB", (800, 600), (120, 120, 120)).save(folder / "concept.png")
    return dict(ROW, concept=str(folder / "concept.png")), folder / "out"


def test_a_crop_has_its_margin_and_is_scaled_up():
    """A 100 x 50 box gets a fifth of 100 all round, 140 x 90, scaled to 512 long: 512 x 329. A box as large as the
    picture keeps the picture's size (its margin clipped, nothing to scale)."""
    assert stage.crop(Image.new("RGB", (800, 600)), [100, 100, 200, 150]).size == (512, 329)
    assert stage.crop(Image.new("RGB", (800, 600)), [0, 0, 800, 600]).size == (800, 600)


def test_rows_come_from_the_inventorys_loop_rows_whatever_their_own_kind():
    """#19: a row's own kind routes nothing: a `code` wall is the loop's and gets a close-up; a mechanic row (made on
    its own line) does not; a row with no box gets none."""
    inventory = {"scene": "cockpit", "plan": {"views": [{"id": "v1", "picture": "concept.png"}]},
                 "rows": [{"id": "cabinet", "view": "v1", "box": [1, 2, 3, 4], "name": "a steel cabinet",
                           "kind": "generate", "size": [1.2, 0.7, 1.0]},
                          {"id": "wall", "view": "v1", "box": [1, 2, 3, 4], "name": "a wall", "kind": "code",
                           "size": [3, 0.2, 2.8]},
                          {"id": "thrust_indicator", "view": "v1", "box": [1, 2, 3, 4], "name": "a dial",
                           "kind": "mechanic", "size": [0.2, 0.2, 0.1]},
                          {"id": "trim", "view": "v1", "name": "a trim", "kind": "code", "size": [3, 0.1, 0.1]}]}
    rows = stage.rows_from_inventory(inventory)
    assert [row["id"] for row in rows] == ["cabinet", "wall"]
    assert rows[0] == {"id": "cabinet", "scene": "cockpit", "words": "a steel cabinet", "size": [1.2, 0.7, 1.0],
                       "concept": "concept.png", "box": [1, 2, 3, 4]}


def test_rows_whose_boxes_the_gate_has_not_passed_are_not_drawn(tmp_path):
    problems = stage.gate_problems([{"id": "cabinet", "words": "a cabinet"},
                                    {"id": "no_such_row", "scene": "camp", "words": "a thing"}])
    assert problems[0].startswith("cabinet: names no scene"), problems
    assert problems[1].startswith("camp.no_such_row: the box gate says"), problems
    with pytest.raises(SystemExit, match="box gate"):
        stage.run([{"id": "cabinet", "words": "a cabinet"}], tmp_path)
    assert not (tmp_path / "crops").exists()


def test_the_picture_batch_skips_rows_already_drawn(tmp_path):
    row, out = a_place(tmp_path)
    stage.make_crops([row], out)
    [job] = stage.picture_jobs([row], out)
    assert job["name"] == "closeup-cabinet" and job["refs"] == [str(out / "crops/cabinet.jpg"), row["concept"]]
    (out / "qwen").mkdir()
    Image.new("RGB", (8, 8)).save(out / "qwen/cabinet.png")
    assert stage.picture_jobs([row], out) == []
    questions = stage.judge_questions([row], out, "qwen")
    assert [question["name"] for question in questions] == ["cabinet~7", "cabinet~8", "cabinet~9"]
    assert questions[0]["images"] == [str(out / "crops/cabinet.jpg"), str(out / "qwen/cabinet.png")]


def test_a_row_takes_the_first_picture_that_passed_and_records_its_cost(tmp_path):
    row, out = a_place(tmp_path)
    for take in ("qwen", "pro"):
        (out / take).mkdir(parents=True)
        Image.new("RGB", (8, 8)).save(out / take / "cabinet.png")
    by_qwen = stage.accepted(row, out, {"qwen": []}, 0.12)
    assert by_qwen["accepted"] == "qwen-edit" and by_qwen["pro_dollars"] == 0 and by_qwen["euros"] == 0.12
    by_pro = stage.accepted(dict(row, pro_wording="crop"), out, {"qwen": ["judge: fail"], "pro": []}, 0.2)
    assert by_pro["accepted"] == "nano-banana-pro" and by_pro["take"] == "pro"
    assert by_pro["pro_dollars"] == pytest.approx(0.067)  # one 2K picture, USD 0.134, at the batch's half
    gap = stage.accepted(row, out, {"qwen": ["judge: fail"], "pro": ["judge: fail"]}, 0.2)
    assert gap["accepted"] is None and gap["picture"] is None
    totals = stage.summary([by_qwen, by_pro, gap], {"qwen": {"euros": 1.0}, "judge-qwen": {"euros": 0.5}})
    assert totals["by_qwen"] == 1 and totals["by_pro"] == 1 and totals["for_review"] == 1
    assert totals["pro_pictures"] == 2 and totals["cloud_euros_per_accepted"] == 0.75  # 1.5 euros over 2 accepted


def test_every_pro_take_is_a_new_request_and_a_gaps_later_takes_stand_upright_on_the_crop(tmp_path):
    """Owner, 2026-10-24 and 2026-10-25: a rejected picture's retries ask the same more strictly, the later ones on
    their own seeds, so each request is a new one, and the first two carry no seed (kept pictures read back from the
    cache under them). A gap's step bought again goes on past the four takes (retry-4 on) from the crop alone, told to
    stand upright, never the room (Batch 1 try 4, 2026-10-26); a row that lies flat is never told to stand."""
    row, out = a_place(tmp_path)
    row = dict(row, pro_wording="crop")
    stage.make_crops([row], out)
    asks = [stage.pro_ask(row, out, take) for take in stage.PRO_TAKES]
    assert len(asks) == 4 and [ask[3] for ask in asks] == [None, None, 2, 3]
    assert asks[1][0].startswith(asks[0][0]) and asks[2][0].startswith(asks[1][0]) and asks[2][0] == asks[3][0]
    bodies = [stage.pro.request_body(*ask) for ask in asks]
    assert len({json.dumps(body, sort_keys=True) for body in bodies}) == 4
    assert [stage.take_index(stage.take_at(index)) for index in range(9)] == list(range(9))
    later = stage.pro_ask(row, out, "retry-4")
    assert later[3] == 4 and "upright" in later[0] and later[2] is None
    room = dict(row, pro_wording="room")
    assert stage.pro_ask(room, out, "retry-3")[2] is not None  # its first four takes as they were: with the room
    assert stage.pro_ask(room, out, "retry-4")[2] is None and stage.pro_ask(room, out, "retry-4")[0] == later[0]
    assert "upright" not in stage.pro_ask(dict(row, read_size=[2.0, 3.0, 0.02]), out, "retry-4")[0]
    person = dict(row, pro_wording="person")
    assert "A-pose" in stage.pro_ask(person, out, "retry-4")[0]
    assert "upright as it stands" not in stage.pro_ask(person, out, "retry-4")[0]


def test_the_close_up_is_asked_for_and_checked_at_the_objects_own_size(tmp_path):
    """Owner, 2026-10-24: a plan's item is the footprint an object is laid in, so the request, the judge and the
    measurements take its reading's size; and the request states the check's view, from above for a row that lies
    flat (wording checks guarding that owner rule). A small crop is asked with the room beside it, a large one or a
    row laid far off (a speck of the painting: Pro drew the street) with the crop alone."""
    row, out = a_place(tmp_path)
    own = dict(row, read_size=[0.3, 0.2, 0.4])
    for text in stage.PRO_WORDINGS["crop"], stage.PRO_WORDINGS["room"]:
        words = stage.wording(own, text)
        assert "0.30 m wide, 0.20 m deep and 0.40 m tall" in words
        assert "turned about 35 degrees" in words and "about 15 degrees above level" in words
        flat = stage.wording(dict(row, read_size=[2.0, 3.0, 0.02]), text)
        assert "seen from straight above" in flat and "turned about 35 degrees" not in flat
    stage.make_crops([own], out)
    (out / "qwen").mkdir()
    Image.new("RGB", (8, 8)).save(out / "qwen/cabinet.png")
    assert "0.30 m wide, 0.20 m deep and 0.40 m tall" in stage.judge_questions([own], out, "qwen")[0]["text"]
    assert stage.pro_wording(row) == "room"  # a 100 by 50 box: 140 pixels with its margin, under 512
    assert stage.pro_wording(dict(row, box=[100, 100, 600, 400])) == "crop"
    assert stage.pro_wording(dict(row, far={"pieces": 1, "length": 0.0})) == "crop"
    assert stage.with_pro_wordings([dict(row, pro_wording="crop")])[0]["pro_wording"] == "crop"  # chosen once


def test_a_person_is_drawn_alone_front_on_in_the_rigs_a_pose(tmp_path):
    """The people layer's own close-up wording (CONTEXT.md "layer adapter"; a wording check guarding that rule): one
    member of a crowd row, front on, arms and legs apart, never the concept's pose and never the room."""
    row, _ = a_place(tmp_path)
    person = dict(row, words="crowd", layer="people", size=None)
    assert stage.pro_wording(person) == "person"
    words = stage.wording(person, stage.PRO_WORDINGS[stage.pro_wording(person)])
    assert "The person: crowd." in words and "A-pose" in words and "never their pose" in words
    assert "Image 2" not in words and "three quarters" not in words


def a_picture_answer():
    """A generateContent answer holding one small picture, priced as a 2K picture."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8)).save(buffer, "PNG")
    picture = {"inlineData": {"data": base64.b64encode(buffer.getvalue()).decode()}}
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [picture]}}],
            "usageMetadata": {"promptTokenCount": 600, "candidatesTokenCount": 1120, "serviceTier": "standard",
                              "candidatesTokensDetails": [{"modality": "IMAGE", "tokenCount": 1120}]}}


@pytest.fixture
def faked_batch(tmp_path, monkeypatch):
    """google_batch's send and status faked (a answers with a picture, b with none, c not at all), the ledger and the
    cache this test's own, the cleared-run gate open; the requests sent."""
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
    monkeypatch.setattr(stage.pro.compute, "require_cleared", lambda what: None)
    monkeypatch.setattr(spend, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(spend, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(batch, "send", send)
    monkeypatch.setattr(batch, "status", status)
    return sent


def test_pro_draws_a_step_as_one_batch_job_cached_and_a_pictureless_answer_is_a_gap(tmp_path, faked_batch):
    """Owner, 2026-10-24 ("Make close-ups really use the batch rate"): a step's Pro close-ups go to Google as one
    Batch API job with the same request each would have been sent alone, priced at half the standard tier on the
    ledger and cached; an answer with no picture, or one the batch did not give, is a gap; one asked before is free."""
    spend = stage.pro.google_spend
    asks = {tmp_path / f"{name}.png": (f"words {name}", Image.new("RGB", (8, 8)), None) for name in "abc"}
    drawn_now = stage.pro.draw("key", asks)
    assert drawn_now == {tmp_path / "a.png": True, tmp_path / "b.png": False, tmp_path / "c.png": False}, drawn_now
    assert len(faked_batch) == 1 and (tmp_path / "a.png").exists() and not (tmp_path / "b.png").exists()
    requests = faked_batch[0]["batch"]["input_config"]["requests"]["requests"]
    assert [item["request"] for item in requests] == [stage.pro.request_body(*asks[path]) for path in sorted(asks)]
    lines = [json.loads(line) for line in spend.LEDGER.read_text().splitlines()]
    finished = [line for line in lines if line["state"] == "finished"]
    assert [line["state"] for line in lines].count("started") == 3
    assert [line["tier"] for line in finished] == ["batch", "batch"]
    full = spend.dollars(stage.pro.MODEL, a_picture_answer()["usageMetadata"])
    assert finished[0]["dollars"] == round(full * 0.5, 6), finished
    assert [line["state"] for line in lines].count("failed") == 1  # c: unanswered, maybe billed
    (tmp_path / "a.png").unlink()
    assert stage.pro.draw("key", {tmp_path / "a.png": asks[tmp_path / "a.png"]}) == {tmp_path / "a.png": True}
    assert len(faked_batch) == 1  # asked before: read back from the cache, free
    stage.pro.draw("key", {tmp_path / "b.png": asks[tmp_path / "b.png"]})
    assert len(faked_batch) == 2  # no picture came back: dropped from the cache, a new batch may ask again


def test_pro_draws_nothing_outside_a_cleared_run(tmp_path, monkeypatch):
    """Fault (design of 2026-10-11, section 6): pro.draw sent a paid request (USD 0.134 a picture) for any caller,
    outside the runner's gate and the owner's yes."""
    sent = []
    monkeypatch.delenv(stage.pro.compute.TICKET, raising=False)
    monkeypatch.setattr(stage.pro.google_batch, "send", lambda *arguments, **options: sent.append(arguments))
    with pytest.raises(stage.pro.compute.Refused, match="nothing rents outside a cleared run"):
        stage.pro.draw("key", {tmp_path / "a.png": ("words", Image.new("RGB", (8, 8)), None)})
    assert sent == []


def test_a_steps_cost_is_kept_for_a_run_that_is_run_again(tmp_path):
    path = tmp_path / "batch.json"
    assert stage.kept_entry(None, path) is None
    assert stage.kept_entry({"euros": 1.4}, path)["euros"] == 1.4
    assert stage.kept_entry(None, path)["euros"] == 1.4
    assert stage.kept_entry({"euros": 0.6}, path)["euros"] == 2.0
