"""The demo-film row with no Blender and no spend: only the places the record names have the row, which declares its
tools; demo.py plans look-only frames at the row's size; a look-only plan cuts into a video of that size; and the gate
`film` fails a film with no sound and still frames by name.

Run: .venv/bin/python score/stages/demo_film/demo_film_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from PIL import Image  # noqa: E402

from score import checks  # noqa: E402
from score.stages import demo_film  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

SMALL = (64, 36)


def folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))


def test_only_the_named_places_have_the_row_and_it_declares_its_tools():
    named = demo_film.record()["places"]
    assert all(demo_film.applies(place) for place in named) and not demo_film.applies("no such place")
    found = demo_film.files("hub")
    assert found["scene"] == "{data}/scene/hub.json" and found["films"] == "{data}/definitions/demo_films.json"
    assert all((REPO / path).exists() for path in demo_film.TOOLS)
    assert found["tool tools/review/demo.py"] == "{repo}/tools/review/demo.py"


def test_the_plan_asks_look_only_frames_at_its_size():
    demo, _ = demo_film.film_tools()
    root = folder()
    try:
        (root / "views").mkdir()
        (root / "jobs").mkdir()
        views = [{"name": f"shot0-{number:03d}", "eye": [0, 1.6, 0], "aim": [0, 1.6, -1], "fov": 70}
                 for number in range(4)]
        written = demo.film_jobs(root, "hall", root / "hall/hall.usda", [], views, "look", 2, demo_film.SIZE, False)
        assert len(written) == 2
        asked = json.loads((root / "views/hall-0.json").read_text())
        assert asked["size"] == list(demo_film.SIZE)
        assert all(view["look_only"] and "ink" not in view for view in asked["views"])
    finally:
        shutil.rmtree(root)


def look_only_film(root):
    """A planned look-only film of one shot whose frames are all one colour, cut by demo.py: its video."""
    demo, _ = demo_film.film_tools()
    frames = root / "frames/hall"
    frames.mkdir(parents=True)
    count = round(demo.SHOT_SECONDS * demo.RATE)
    views = [{"name": f"shot0-{number:03d}"} for number in range(count)]
    for view in views:
        Image.new("RGB", SMALL, (90, 110, 130)).save(frames / f"{view['name']}-look.png")
    (root / "views").mkdir()
    (root / "views/hall.json").write_text(json.dumps({"size": list(SMALL), "ink": False, "views": views}))
    demo.cut(root, ["hall"])
    return root / "videos/hall.mp4"


def test_a_look_only_plan_cuts_into_a_video_of_its_size():
    _, film_checks = demo_film.film_tools()
    root = folder()
    try:
        video = look_only_film(root)
        measured = film_checks.video_checks(video, demo_film.LEAST, demo_film.MOST, 2.0, SMALL)
        assert measured["size"] == list(SMALL) and not any("size" in fault for fault in measured["failures"])
        assert demo_film.LEAST <= measured["seconds"] <= demo_film.MOST, measured
    finally:
        shutil.rmtree(root)


def test_the_gate_fails_a_silent_still_film_by_name():
    demo, film_checks = demo_film.film_tools()
    root = folder()
    clearance, size = film_checks.clearance_checks, demo_film.SIZE
    try:
        video = look_only_film(root / "cut")
        out = root / "out"
        out.mkdir()
        shutil.copy(video, out / "film.mp4")
        (out / "views.json").write_text(json.dumps({"views": []}))
        (root / "stage").mkdir()
        (root / "stage/hall.usda").write_text("#usda 1.0\n")
        film_checks.clearance_checks = lambda stage, views: ({}, [])
        demo_film.SIZE = SMALL
        verdict = demo_film.judge_film(out, {"assembly": root / "stage"}, {})
        found = " ".join(verdict.findings)
        assert verdict.answer == checks.FAIL and "no sound track" in found and "frozen" in found, found
    finally:
        film_checks.clearance_checks, demo_film.SIZE = clearance, size
        shutil.rmtree(root)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
