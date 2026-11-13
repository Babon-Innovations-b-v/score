"""film_preview.py without Blender or the store: one stage whose scene record holds a five-frame, a four-frame and a
one-frame shot is copied to a work stage, the frames picked from the copy's views, the planner's edits written to the
copy, and the before-and-after picture laid out from pictures made here of the picked frames.

Breaks (each applied once, seen red, reverted), in tools/review/film_preview.py:
- first and last frame: shot_moments keeps only each shot's first frame.
- a one-frame shot once: shot_moments lists first and last as a list, not a set.
- the stage left alone: work_stage links every entry, the root layer and scene record too.
- rows one under the other: sheet makes the canvas one row tall.
"""
import json
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import film_preview  # noqa: E402

FRAMES = {"shot0": 5, "shot1": 4, "shot2": 1}


def test_a_preview_shows_each_shots_ends_and_leaves_the_stage_alone(tmp_path):
    views = [{"name": f"{shot}-{number:03d}"} for shot, count in FRAMES.items() for number in range(count)]
    stage = tmp_path / "store" / "garage"
    (stage / "assets").mkdir(parents=True)
    (stage / "assets" / "big.usdc").write_text("big")
    (stage / "garage.usda").write_text("#usda 1.0\n")
    (stage / "scene.json").write_text(json.dumps({"views": views}))

    copy = film_preview.work_stage(stage, "garage", tmp_path / "work")
    moments = film_preview.shot_moments(json.loads((copy / "scene.json").read_text())["views"])
    (copy / "garage.usda").write_text("#usda 1.0\nover \"x\" {}\n")
    (copy / "scene.json").write_text('{"views": []}')

    assert [(number, view["name"]) for number, view in moments] == [
        (0, "shot0-000"), (4, "shot0-004"), (5, "shot1-000"), (8, "shot1-003"), (9, "shot2-000")]
    assert (copy / "assets").is_symlink() and (copy / "assets" / "big.usdc").read_text() == "big"
    assert not (copy / "garage.usda").is_symlink() and not (copy / "scene.json").is_symlink()
    assert (stage / "garage.usda").read_text() == "#usda 1.0\n"
    assert json.loads((stage / "scene.json").read_text()) == {"views": views}

    pictures = []
    for number, view in moments:
        path = tmp_path / f"{view['name']}.png"
        Image.new("RGB", (64, 36), (20 * number, 0, 0)).save(path)
        pictures.append((view["name"], path))
    before = film_preview.labelled_row("Before", pictures[:1])
    after = film_preview.labelled_row("After", pictures)
    film_preview.sheet([before, after], tmp_path / "sheet.jpg")
    made = Image.open(tmp_path / "sheet.jpg")
    assert made.width == len(moments) * film_preview.SIZE[0] + (len(moments) - 1) * film_preview.GAP
    assert made.height == 2 * (film_preview.LABEL_HEIGHT + film_preview.SIZE[1]) + film_preview.GAP
    assert made.width % 2 == 0 and made.height % 2 == 0
