"""Checks for the inventory box check: the measured half on made-up inventories (the camp's guessed boxes among them),
the judge's pictures and questions, and its majority vote, without a model or a cloud machine.

Plain python: python3 tools/props/scene/box_check_test.py
"""
import pathlib
import sys
import tempfile

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import box_check  # noqa: E402

SIZE = (2752, 1536)


def a_row(name, box, **changes):
    row = {"id": name, "view": "v1", "box": box, "name": f"the {name}", "kind": "generate", "anchor": "floor",
           "size": [1.0, 0.5, 1.2], "count": 1, "thing": f"prop:{name}"}
    row.update(changes)
    return row


def an_inventory(rows, picture="WORK/v1.png"):
    return {"plan": {"views": [{"id": "v1", "picture": picture}]}, "rows": rows}


def spread_over_the_picture():
    """Twelve boxes drawn over the whole picture, as a partition drawn on the concept leaves them."""
    return [a_row(f"r{index}", [100 + 200 * index, 200 + 90 * (index % 4), 380 + 200 * index, 620 + 200 * (index % 4)])
            for index in range(12)]


def test_boxes_spread_over_their_picture_pass():
    assert box_check.measured_problems(an_inventory(spread_over_the_picture()), {"v1": SIZE}) == []


def test_guessed_boxes_crowded_into_one_corner_fail():
    # The camp's door dome as it was: round numbers reaching only x 1600, y 900 of the concept.
    rows = [a_row(f"r{index}", [100 + 100 * (index % 6), 100 + 100 * (index // 6), 600 + 150 * (index % 6),
                                400 + 100 * (index // 6)]) for index in range(24)]
    problems = box_check.measured_problems(an_inventory(rows), {"v1": SIZE})
    assert any("one quarter" in problem for problem in problems), problems
    assert any("span only" in problem for problem in problems), problems


def test_too_little_covered_for_its_rows_fails():
    rows = [a_row(f"r{index}", [200 + 400 * index, 700, 240 + 400 * index, 740]) for index in range(6)]
    problems = box_check.measured_problems(an_inventory(rows), {"v1": SIZE})
    assert any("cover" in problem and "its rows suggest" in problem for problem in problems), problems
    few = box_check.measured_problems(an_inventory(rows[:4]), {"v1": SIZE})
    assert not any("its rows suggest" in problem for problem in few), few  # a few far things may be small


def test_a_box_outside_its_picture_fails():
    rows = spread_over_the_picture() + [a_row("over", [2600, 1400, 2900, 1600])]
    problems = box_check.measured_problems(an_inventory(rows), {"v1": SIZE})
    assert any("row over" in problem and "not inside" in problem for problem in problems), problems


def test_the_whole_picture_is_a_box_only_for_the_room_wide_kit_pieces():
    whole = [0, 0, SIZE[0], SIZE[1]]
    rows = spread_over_the_picture() + [a_row("wall_lower", whole, group="kit: wall"),
                                        a_row("desk", whole, group="kit: furniture"), a_row("rack", whole)]
    problems = box_check.measured_problems(an_inventory(rows), {"v1": SIZE})
    named = {problem.split(":")[0] for problem in problems if "whole picture" in problem}
    assert named == {"row desk", "row rack"}, problems


def test_an_unseen_row_and_a_missing_picture():
    rows = spread_over_the_picture() + [a_row("hidden", None, unseen="behind the camera")]
    assert box_check.measured_problems(an_inventory(rows), {"v1": SIZE}) == []
    assert box_check.measured_problems(an_inventory(rows), {"v1": None}) == ["view v1: its picture is missing"]


def test_the_judge_sees_the_whole_picture_and_the_crop_once_a_seed():
    folder = pathlib.Path(tempfile.mkdtemp())
    picture = folder / "concept.png"
    Image.new("RGB", SIZE, (90, 90, 90)).save(picture)
    rows = spread_over_the_picture()[:2] + [a_row("wall", [0, 0, SIZE[0], SIZE[1]], group="kit: wall")]
    jobs = box_check.judge_jobs("camp", an_inventory(rows, str(picture)), {"v1": SIZE}, folder / "judge",
                                box_check.SEEDS)
    assert len(jobs) == 2 * len(box_check.SEEDS)  # the kit wall's whole picture is not asked about
    assert {job["seed"] for job in jobs} == set(box_check.SEEDS)
    whole, cut = (pathlib.Path(path) for path in jobs[0]["images"])
    assert Image.open(whole).width == box_check.OVERVIEW_WIDE
    assert max(Image.open(cut).size) >= box_check.SHORTEST_CROP
    assert "the r0" in jobs[0]["text"]


def test_the_majority_of_the_judges_answers_decides():
    shown = 'thinking... {"shows": true, "main": true, "what": "a locker"}'
    beside = '{"shows": true, "main": false, "what": "the wall beside a locker"}'
    assert box_check.verdict([shown, shown, beside])["passes"]
    failed = box_check.verdict([shown, beside, "no answer at all"])
    assert not failed["passes"] and failed["passed"] == 1 and failed["what"] == "the wall beside a locker"


def test_the_third_seed_is_asked_only_where_the_first_two_disagree():
    folder = pathlib.Path(tempfile.mkdtemp())
    shown = '{"shows": true, "main": true, "what": "a locker"}'
    beside = '{"shows": false, "main": false, "what": "a wall"}'
    first, second, third = box_check.SEEDS
    jobs = [{"name": f"{key}~{seed}", "seed": seed, "text": "", "images": []} for key in ("agreed", "split", "unasked")
            for seed in (first, second)]
    for name, text in ((f"agreed~{first}", beside), (f"agreed~{second}", beside), (f"split~{first}", shown),
                       (f"split~{second}", beside)):
        (folder / f"{name}.txt").write_text(text)
    assert [job["name"] for job in box_check.deciding_jobs(jobs, folder)] == [f"split~{third}"]
    found = box_check.verdicts(jobs, folder)
    assert set(found) == {"agreed"} and not found["agreed"]["passes"] and found["agreed"]["of"] == 2
    (folder / f"split~{third}.txt").write_text(shown)
    assert box_check.verdicts(jobs, folder)["split"] == {"passes": True, "passed": 2, "of": 3, "what": "a wall"}


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
