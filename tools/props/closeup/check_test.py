"""Checks for the close-up shape check: the measurements on drawn pictures, the judge's answer read from its reply,
and the faults each half finds, without a model or a cloud machine.

Plain python: python3 tools/props/closeup/check_test.py
"""
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
GREY = (205, 205, 205)
SIZE = (0.6, 0.5, 1.0)


def drawn(boxes, side=512, background=GREY):
    """A picture of dark boxes on a plain background, saved to a temporary file; its path."""
    picture = Image.new("RGB", (side, side), background)
    draw = ImageDraw.Draw(picture)
    for box in boxes:
        draw.rectangle(box, fill=(60, 70, 80))
    path = pathlib.Path(tempfile.mkdtemp()) / "closeup.png"
    picture.save(path)
    return path


def a_box_of(size, side=512, fill=0.7):
    """A box whose outline has the proportions the check expects of an object of `size`."""
    tall = check.expected_proportion(size)
    height = fill * side if tall >= 1 else fill * side * tall
    width = height / tall
    left, top = (side - width) / 2, (side - height) / 2
    return (left, top, left + width, top + height)


def test_a_single_object_on_a_plain_background_passes_the_measurements():
    measures = check.measure(drawn([a_box_of(SIZE)]), SIZE)
    assert measures["border_clean"] > 0.99 and measures["one_piece"] > 0.99
    assert abs(measures["fill"] - 0.7) < 0.02 and measures["proportion_error"] < 0.05
    assert check.measured_faults(measures) == []


def test_a_small_object_is_faulted():
    assert "object small in the frame" in check.measured_faults(check.measure(drawn([a_box_of(SIZE, fill=0.3)]), SIZE))


def test_two_objects_are_faulted():
    path = drawn([(60, 150, 220, 400), (290, 150, 450, 400)])
    assert "more than one object" in check.measured_faults(check.measure(path, (1.0, 0.5, 1.0)))


def test_an_object_cut_by_the_edge_is_faulted():
    path = drawn([(0, 100, 300, 512)])
    assert "background not plain to the edge" in check.measured_faults(check.measure(path, SIZE))


def test_a_wrong_proportion_is_faulted():
    path = drawn([(56, 200, 456, 300)])
    assert "proportions off the row's box" in check.measured_faults(check.measure(path, (0.4, 0.4, 1.2)))


def test_an_object_is_held_to_its_one_stated_look_down():
    """A low cabinet drawn as seen from 45 degrees is faulted: the check holds the one stated look-down, no best fit."""
    cabinet = (4.0, 5.0, 1.0)
    assert not check.lies_flat(cabinet) and check.look_down(cabinet) == check.LOOK_DOWN_DEGREES
    height = 0.7 * 512 * check.expected_proportion(cabinet, 45.0)
    assert "proportions off the row's box" in check.measured_faults(
        check.measure(drawn([(77, 256 - height / 2, 435, 256 + height / 2)]), cabinet))
    height = 0.7 * 512 * check.expected_proportion(cabinet)
    assert check.measured_faults(check.measure(drawn([(77, 256 - height / 2, 435, 256 + height / 2)]), cabinet)) == []


def test_a_row_that_lies_flat_is_held_to_its_face_from_straight_above():
    """Batch 1 try 4 (2026-10-25): from the stated look-down a rug's outline is nearly all view. A row that lies flat
    (the model gate's flat class, its height its thinnest side) is drawn and checked from straight above, square to
    the frame: its face is its outline, either way round, so a 1 x 3 m rug drawn 1 x 3 or 3 x 1 passes, drawn square
    or a 2 x 3 m one as the old 15 degree view shows it is faulted. A poster sized thin in depth stands on its edge and keeps the
    stated view; a pipe is slender, not flat."""
    rug = (1.0, 3.0, 0.02)
    assert check.lies_flat(rug) and check.look_down(rug) == check.TOP_DOWN_DEGREES
    assert not check.lies_flat((0.4, 0.01, 0.6)) and not check.lies_flat((0.1, 0.1, 4.0))
    assert not check.lies_flat((0.6, 0.5, 0.8))
    faulted = lambda box: "proportions off the row's box" in check.measured_faults(check.measure(drawn([box]), rug))
    assert not faulted((196, 76, 316, 436)) and not faulted((76, 196, 436, 316))
    assert faulted((106, 106, 406, 406))
    wide_rug = (2.0, 3.0, 0.02)  # its outline at the old view, 0.28, is no face of it (1.5 or 0.67)
    height = 358 * check.expected_proportion(wide_rug)
    assert "proportions off the row's box" in check.measured_faults(
        check.measure(drawn([(77, 256 - height / 2, 435, 256 + height / 2)]), wide_rug))


def shaded_backdrop(side):
    """A studio backdrop as Nano Banana Pro draws it: grey at the edges, about 20 lighter behind the figure."""
    rows, columns = np.mgrid[0:side, 0:side] / side - 0.5
    light = 200 + 22 * np.clip(1 - 2 * np.hypot(rows, columns), 0, 1)
    return Image.fromarray(np.repeat(light[..., None], 3, axis=2).astype(np.uint8))


def a_person(arms_out, side=512, shaded=False):
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
        hand = shoulder + side_sign * arms_out
        draw.line([(shoulder, 108), (hand, 240)], fill=dark, width=14)
    path = pathlib.Path(tempfile.mkdtemp()) / "person.png"
    picture.save(path)
    return path


def test_a_persons_close_up_needs_its_arms_clear_of_the_body_not_a_box_s_proportions():
    """The people layer's close-up (stage.PERSON): drawn in the rig's A-pose, so no box's outline holds it; arms
    hanging against the torso (Pixal3D fuses them, Nev 2026-10-10) fail it."""
    assert check.person_faults(a_person(arms_out=70)) == []
    assert any(fault.startswith("arms not clear of the body") for fault in check.person_faults(a_person(arms_out=0)))
    assert check.measure(a_person(arms_out=70), None)["proportion_error"] is None


def test_a_persons_arms_are_found_apart_on_a_backdrop_lighter_behind_the_figure():
    """Nano Banana Pro's backdrop is lighter in the middle than at the edges; the first people benchmark's two
    close-ups (#26, 2026-10-21, arms well apart) scored 0.00 when the backdrop came from the edges alone."""
    for picture in ("pro-player_wide-work.jpg", "pro-kit_m_avg-coat-grey.jpg"):
        assert check.person_faults(FIXTURES / picture) == [], picture
    assert check.person_faults(a_person(arms_out=70, shaded=True)) == []
    assert any(fault.startswith("arms not clear of the body")
               for fault in check.person_faults(a_person(arms_out=0, shaded=True)))


def test_the_answer_is_the_last_json_object_in_the_reply():
    reply = 'thinking about {"a": 1} ... done.\n{"one_object": true, "verdict": "fail"}'
    assert check.answer_of(reply) == {"one_object": True, "verdict": "fail"}
    assert check.answer_of("no json here") is None


def test_the_judge_passes_only_a_clean_yes():
    good = {"one_object": True, "clean": True, "whole": True, "same_object": True, "proportions": True,
            "missing_parts": [], "added_parts": [], "shape_score": 8, "verdict": "pass"}
    assert check.judged_faults(good) == []
    assert check.judged_faults(dict(good, added_parts=["armrests"])) == ["judge: adds armrests"]
    assert check.judged_faults(dict(good, shape_score=check.SCORE_MIN - 1)) == [f"judge: shape score {check.SCORE_MIN - 1}"]
    assert "judge: not clean" in check.judged_faults(dict(good, clean=False))
    assert check.judged_faults(None) == ["the judge gave no answer"]


def test_most_of_the_judge_s_answers_decide():
    good = {"one_object": True, "clean": True, "whole": True, "same_object": True, "proportions": True,
            "missing_parts": [], "added_parts": [], "shape_score": 8, "verdict": "pass"}
    bad = dict(good, verdict="fail")
    assert check.voted_faults([good, good, bad]) == []
    assert check.voted_faults([good, bad, None]) == ["judge: fail", "judge: 1 of 3 answers passed"]
    assert check.faults({"border_clean": 1.0, "fill": 0.7, "one_piece": 1.0, "proportion_error": 0.1},
                        [good, bad, good]) == []


def test_the_question_names_the_object_and_its_size():
    text = check.question("a steel cabinet", (1.2, 0.7, 1.0))
    assert "a steel cabinet" in text and "1.20 m wide, 0.70 m deep and 1.00 m tall" in text


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("check_test: ok")
