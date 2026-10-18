"""The demo-turntables row with no Blender and no spend: its shots frame every model at every heading on its own, the
gate `drawn` passes drawn pictures and fails a missing or blank one by name, and the row declares the record and every
model file.

Run: .venv/bin/python score/stages/demo_turntable/demo_turntable_test.py
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
from score.stages import demo_turntable  # noqa: E402
from score.store import PROPS_HOME  # noqa: E402

TURNTABLES = {"headings": [35, 215],
              "objects": [{"id": "wheel", "models": {"generated": ["g.glb"], "code": ["c.gltf", "c.bin"]}}]}


def folder():
    (PROPS_HOME / "store-tests").mkdir(parents=True, exist_ok=True)
    return pathlib.Path(tempfile.mkdtemp(dir=PROPS_HOME / "store-tests"))


def drawn_model():
    picture = Image.new("RGB", (256, 256), (33, 33, 36))
    ImageDraw.Draw(picture).ellipse((40, 40, 216, 216), (150, 140, 130))
    return picture


def test_every_model_at_every_heading_is_its_own_group():
    inputs = {"wheel generated 0": "/m/g.glb", "wheel code 0": "/m/c.gltf", "wheel code 1": "/m/c.bin"}
    groups = demo_turntable.shots(TURNTABLES, inputs)["groups"]
    assert [group["name"] for group in groups] == ["wheel--generated--035", "wheel--generated--215",
                                                   "wheel--code--035", "wheel--code--215"]
    assert all(len(group["members"]) == 1 and group["members"][0]["name"] == group["name"] for group in groups)
    assert groups[2]["members"][0]["files"] == [{"path": "/m/c.gltf"}] and groups[3]["heading"] == 215


def test_drawn_passes_every_picture_and_fails_a_missing_or_blank_one_by_name():
    root = folder()
    try:
        groups = demo_turntable.shots(TURNTABLES, {"wheel generated 0": "g", "wheel code 0": "c"})["groups"]
        (root / "shots.json").write_text(json.dumps({"groups": groups}))
        (root / "renders").mkdir()
        for group in groups:
            drawn_model().save(root / "renders" / f"{group['name']}.png")
        assert demo_turntable.judge_drawn(root, {}, {}).answer == checks.PASS
        (root / "renders/wheel--code--035.png").unlink()
        Image.new("RGB", (256, 256), (33, 33, 36)).save(root / "renders/wheel--code--215.png")
        verdict = demo_turntable.judge_drawn(root, {}, {})
        found = " ".join(verdict.findings)
        assert verdict.answer == checks.FAIL
        assert "wheel--code--035: no picture came back" in found and "wheel--code--215: blank" in found, found
    finally:
        shutil.rmtree(root)


def test_the_row_declares_its_record_script_and_every_model_file():
    found = demo_turntable.files()
    assert found["turntables"] == "{data}/definitions/demo_turntables.json"
    assert found["model script"] == "{repo}/score/stages/demo_turntable/turntable_models.py"
    assert found["drawer"] == "{repo}/tools/blender/inside/review_models.py"
    for item in demo_turntable.record()["objects"]:
        for what, patterns in item["models"].items():
            assert [found[f"{item['id']} {what} {number}"] for number in range(len(patterns))] == patterns


def test_the_drawer_still_ends_with_the_call_the_wrapper_holds_back():
    """turntable_models.py runs review_models.py without its last line, main(), to widen its frame first."""
    assert (REPO / demo_turntable.DRAWER).read_text().rstrip().endswith("\nmain()")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
