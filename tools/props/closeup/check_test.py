"""Checks for the close-up shape check: the measurements on drawn pictures, the judge's answer read from its reply,
and the faults each half finds, without a model or a cloud machine.

Plain python: python3 tools/props/closeup/check_test.py
"""
import pathlib
import sys
import tempfile

from PIL import Image, ImageDraw

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402

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


def test_the_question_names_the_object_and_its_size():
    text = check.question("a steel cabinet", (1.2, 0.7, 1.0))
    assert "a steel cabinet" in text and "1.20 m wide, 0.70 m deep and 1.00 m tall" in text


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("check_test: ok")
