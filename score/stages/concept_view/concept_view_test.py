"""The concept-views row on stand-in pictures and a stand-in Pro (no spend): the make draws one picture a view and
records each, and the gate `drawn` passes the promised picture and fails one missing, too small, of the wrong shape
or blank, each by name.

Run: .venv/bin/python score/stages/concept_view/concept_view_test.py
"""
import json
import pathlib
import shutil
import sys
import tempfile
import types

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from PIL import Image, ImageDraw  # noqa: E402

from score import checks  # noqa: E402
from score.stages import concept_view  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402


def folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))


def drawing(size):
    """A picture with something on it: a dark wedge on white."""
    picture = Image.new("RGB", size, "white")
    ImageDraw.Draw(picture).polygon([(10, size[1] // 2), (size[0] - 10, 10), (size[0] - 10, size[1] - 10)], "black")
    return picture


def judged(pictures, shape="landscape"):
    root = folder()
    try:
        views = []
        for name, picture in pictures.items():
            if picture is not None:
                picture.save(root / f"{name}.png")
            views.append({"id": name, "shape": shape, "drawn": picture is not None})
        (root / "views.json").write_text(json.dumps({"views": views}))
        return concept_view.judge_drawn(root, {}, {})
    finally:
        shutil.rmtree(root)


def test_the_promised_picture_passes():
    assert judged({"ship": drawing((2048, 1152))}).answer == checks.PASS


def test_a_missing_small_wrong_shaped_or_blank_picture_fails_by_name():
    verdict = judged({"gone": None, "small": drawing((800, 450)), "tall": drawing((1152, 2048)),
                      "blank": Image.new("RGB", (2048, 1152), "white")})
    assert verdict.answer == checks.FAIL
    found = " ".join(verdict.findings)
    for words in ("gone: no picture came back", "small: 800 x 450 px", "tall: portrait, its request promises landscape",
                  "blank: blank"):
        assert words in found, (words, found)


def test_the_make_draws_one_picture_a_view_with_its_reference_and_wording():
    root = folder()
    asked = []

    def draw(key, wording, crop, concept, path):
        asked.append((key, wording, crop.size, concept))
        drawing((2048, 1152)).save(path)
        return True

    stand_ins = {"pro": types.SimpleNamespace(KEY_SECRET="a-secret", draw=draw),
                 "secret_store": types.SimpleNamespace(secret=lambda name: f"key of {name}")}
    real = concept_view.pro_tools
    concept_view.pro_tools = lambda: (stand_ins["pro"], stand_ins["secret_store"])
    try:
        drawing((775, 420)).save(root / "reference.png")
        views = [{"id": "ship_top", "reference": "x", "wording": "the ship from above", "shape": "landscape"}]
        (root / "views-record.json").write_text(json.dumps({"views": views}))
        (root / "out").mkdir()
        concept_view.make({"views": root / "views-record.json", "reference ship_top": root / "reference.png"},
                          root / "out", 0, {})
        assert asked == [("key of a-secret", "the ship from above", (775, 420), None)], asked
        written = json.loads((root / "out/views.json").read_text())["views"]
        assert written[0]["drawn"] and (root / "out/ship_top.png").exists()
        assert concept_view.judge_drawn(root / "out", {}, {}).answer == checks.PASS
    finally:
        concept_view.pro_tools = real
        shutil.rmtree(root)


def test_the_row_declares_its_record_and_every_reference():
    found = concept_view.files()
    assert found["views"] == "{data}/definitions/concept_views.json"
    assert all(f"reference {view['id']}" in found for view in concept_view.record()["views"])


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
