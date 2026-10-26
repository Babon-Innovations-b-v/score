"""film_preview.py without Blender or the store: the frames it picks of each shot, a work stage that never writes the
stage it was made from, and the before-and-after picture laid out from pictures made here.

Breaks (each applied once, seen red, reverted), in tools/review/film_preview.py:
- first and last frame: shot_moments keeps only each shot's first frame.
- a one-frame shot once: shot_moments lists first and last as a list, not a set.
- the stage left alone: work_stage links every entry, the root layer and scene record too.
- rows one under the other: sheet makes the canvas one row tall.
"""
import pathlib
import sys

from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import film_preview  # noqa: E402


def test_each_shot_gives_its_first_and_last_frame():
    views = [{"name": f"shot0-{number:03d}"} for number in range(5)] + [{"name": f"shot1-{number:03d}"}
                                                                          for number in range(4)]
    picked = [view["name"] for _, view in film_preview.shot_moments(views)]
    assert picked == ["shot0-000", "shot0-004", "shot1-000", "shot1-003"]
    assert [number for number, _ in film_preview.shot_moments(views)] == [0, 4, 5, 8]


def test_one_frame_shot_is_picked_once():
    assert len(film_preview.shot_moments([{"name": "shot0-000"}])) == 1


def test_work_stage_copies_what_the_planner_writes_and_links_the_rest(tmp_path):
    stage = tmp_path / "store" / "garage"
    (stage / "assets").mkdir(parents=True)
    (stage / "assets" / "big.usdc").write_text("big")
    (stage / "garage.usda").write_text("#usda 1.0\n")
    (stage / "scene.json").write_text("{}")
    copy = film_preview.work_stage(stage, "garage", tmp_path / "work")
    assert (copy / "assets").is_symlink() and (copy / "assets" / "big.usdc").read_text() == "big"
    assert not (copy / "garage.usda").is_symlink() and not (copy / "scene.json").is_symlink()
    (copy / "garage.usda").write_text("#usda 1.0\nover \"x\" {}\n")
    (copy / "scene.json").write_text('{"views": []}')
    assert (stage / "garage.usda").read_text() == "#usda 1.0\n"
    assert (stage / "scene.json").read_text() == "{}"


def test_sheet_lays_the_rows_one_under_the_other(tmp_path):
    pictures = []
    for number in range(3):
        path = tmp_path / f"frame{number}.png"
        Image.new("RGB", (64, 36), (40 * number, 0, 0)).save(path)
        pictures.append((f"shot0-00{number}", path))
    before = film_preview.labelled_row("Before", pictures[:1])
    after = film_preview.labelled_row("After", pictures)
    film_preview.sheet([before, after], tmp_path / "sheet.jpg")
    made = Image.open(tmp_path / "sheet.jpg")
    assert made.width == 3 * film_preview.SIZE[0] + 2 * film_preview.GAP
    assert made.height == 2 * (film_preview.LABEL_HEIGHT + film_preview.SIZE[1]) + film_preview.GAP
    assert made.width % 2 == 0 and made.height % 2 == 0
