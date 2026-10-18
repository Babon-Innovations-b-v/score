"""The demo-stills row with no Blender and no spend: a still takes its named camera from the stage's own record (else
the seed's) at its frame of the stage's time, a camera the record lacks is refused, and the gate `drawn` fails a
missing or blank still by name.

Run: .venv/bin/python score/stages/demo_film/stills_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from PIL import Image, ImageDraw  # noqa: E402

from score import checks  # noqa: E402
import score.stages.demo_film.stills as stills  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

SEED = {"views": [{"name": "door", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1], "fov": 70}]}
OWN = {"views": [{"name": "spot-1", "eye": [1, 1.6, 1], "aim": [1, 1.6, 0], "fov": 60}]}


def folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))


def test_a_still_takes_the_stage_s_own_camera_at_its_frame():
    root = folder()
    try:
        (root / "seed.json").write_text(json.dumps(SEED))
        assert list(stills.cameras(root, root / "seed.json")) == ["door"]
        (root / "scene.json").write_text(json.dumps(OWN))
        found = stills.cameras(root, root / "seed.json")
        views = stills.still_views([{"name": "lift", "camera": "spot-1", "seconds": 2.5}], found, 24.0)
        assert views == [{"name": "lift", "eye": [1, 1.6, 1], "aim": [1, 1.6, 0], "up": [0.0, 1.0, 0.0], "fov": 60,
                          "frame": 60, "look_only": True}], views
        try:
            stills.still_views([{"name": "x", "camera": "door", "seconds": 0}], found, 24.0)
        except RuntimeError as error:
            assert "no camera door" in str(error)
        else:
            raise AssertionError("a camera the record lacks was taken")
    finally:
        shutil.rmtree(root)


def test_drawn_fails_a_missing_or_blank_still_by_name():
    root = folder()
    try:
        (root / "stills.json").write_text(json.dumps({"stills": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}))
        picture = Image.new("RGB", (64, 36), (20, 20, 20))
        ImageDraw.Draw(picture).rectangle((10, 10, 40, 30), (200, 180, 160))
        picture.save(root / "a.png")
        Image.new("RGB", (64, 36), (20, 20, 20)).save(root / "b.png")
        verdict = stills.judge_drawn(root, {}, {})
        found = " ".join(verdict.findings)
        assert verdict.answer == checks.FAIL and "b: blank" in found and "c: no picture" in found, found
        assert "a:" not in found
    finally:
        shutil.rmtree(root)


def test_only_a_place_with_a_stills_record_has_the_row():
    assert not stills.applies("no such place")
    found = stills.files("hub")
    assert found["stills"] == "{data}/definitions/demo_stills/hub.json" and found["scene"] == "{data}/scene/hub.json"


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
