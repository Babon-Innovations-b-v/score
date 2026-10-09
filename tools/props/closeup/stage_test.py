"""Checks for the close-up stage's plain steps: the crops, the rows from an inventory, the batches' lists, the cards
a batch takes and the record of what each row cost, without a model, a cloud machine or Nano Banana Pro.

Plain python: python3 tools/props/closeup/stage_test.py
"""
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


def test_rows_come_from_the_inventory_s_generated_rows():
    inventory = {"scene": "lab", "plan": {"views": [{"id": "v1", "picture": "concept.png"}]},
                 "rows": [{"id": "cabinet", "view": "v1", "box": [1, 2, 3, 4], "name": "a steel cabinet",
                           "kind": "generate", "size": [1.2, 0.7, 1.0]},
                          {"id": "wall", "view": "v1", "box": [1, 2, 3, 4], "name": "a wall", "kind": "code",
                           "size": [3, 0.2, 2.8]}]}
    assert stage.rows_from_inventory(inventory) == [{"id": "cabinet", "scene": "lab", "words": "a steel cabinet",
                                                     "size": [1.2, 0.7, 1.0], "concept": "concept.png",
                                                     "box": [1, 2, 3, 4]}]


def test_rows_whose_boxes_the_gate_has_not_passed_are_not_drawn():
    problems = stage.gate_problems([{"id": "cabinet", "words": "a cabinet"},
                                    {"id": "galley", "scene": "camp", "words": "a galley"}])
    assert problems[0].startswith("cabinet: names no scene"), problems
    assert problems[1].startswith("camp.galley: the box gate says"), problems
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
    for take in ("qwen", "pro", "pro-room"):
        (out / take).mkdir(parents=True)
        Image.new("RGB", (8, 8)).save(out / take / "cabinet.png")
    by_qwen = stage.accepted(row, out, {"qwen": []}, 0.12)
    assert by_qwen["accepted"] == "qwen-edit" and by_qwen["pro_dollars"] == 0 and by_qwen["euros"] == 0.12
    by_room = stage.accepted(row, out, {"qwen": ["judge: fail"], "pro": ["judge: fail"], "pro-room": []}, 0.2)
    assert by_room["accepted"] == "nano-banana-pro" and by_room["take"] == "pro-room"
    assert by_room["pro_dollars"] == 2 * stage.pro.DOLLARS_A_PICTURE
    unresolved = stage.accepted(row, out, {"qwen": ["judge: fail"], "pro": ["judge: fail"],
                                           "pro-room": ["judge: fail"]}, 0.2)
    assert unresolved["accepted"] is None and unresolved["picture"] is None
    totals = stage.summary([by_qwen, by_room, unresolved], {"qwen": {"euros": 1.0}, "judge-qwen": {"euros": 0.5}})
    assert totals["by_qwen"] == 1 and totals["by_pro"] == 1 and totals["for_review"] == 1
    assert totals["pro_pictures"] == 4 and totals["cloud_euros_per_accepted"] == 0.75


def test_pro_s_first_take_leaves_the_room_out():
    assert "Image 2" not in stage.PRO_TAKES["pro"] and "Image 2" in stage.PRO_TAKES["pro-room"]
    body = stage.pro.request_body("words", Image.new("RGB", (8, 8)))
    assert len(body["contents"][0]["parts"]) == 2


def test_a_step_s_cost_is_kept_for_a_run_that_is_run_again():
    path = pathlib.Path(tempfile.mkdtemp()) / "batch.json"
    assert stage.kept_entry(None, path) is None
    assert stage.kept_entry({"euros": 1.4}, path)["euros"] == 1.4
    assert stage.kept_entry(None, path)["euros"] == 1.4
    assert stage.kept_entry({"euros": 0.6}, path)["euros"] == 2.0


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
    print("stage_test: ok")
