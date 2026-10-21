"""The late-bake stage's gates on a small made folder, without a card or Blender."""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))
from score import checks  # noqa: E402
from score.stages import late_bake  # noqa: E402


def made_folder(root, slots):
    (root / "made").mkdir()
    (root / "plan.json").write_text(json.dumps({"models": {"tube_1": {}, "lamp_1": {}}}))
    (root / "made" / "tube_1.gltf").write_text("{}")
    report = {"pieces": {"tube_1": {"triangles": 10, "slots": slots}}}
    (root / "made" / "report-late.json").write_text(json.dumps(report))


def test_gates():
    with tempfile.TemporaryDirectory() as folder:
        root = pathlib.Path(folder)
        made_folder(root, ["painted_panel", "made_up_paint"])
        made = late_bake.judge_made(root, {}, None)
        assert made.answer == checks.FAIL and made.findings == ("lamp_1",)
        surfaces = late_bake.judge_surfaces(root, {}, None)
        # the library holds no surface since every old one was retired (2026-10-21): each slot is named
        assert surfaces.answer == checks.FAIL
        assert surfaces.findings == ("tube_1: made_up_paint", "tube_1: painted_panel"), surfaces.findings
        kept = late_bake.library_names
        late_bake.library_names = lambda: {"painted_panel"}  # a library that holds the panel's surface
        try:
            assert late_bake.judge_surfaces(root, {}, None).findings == ("tube_1: made_up_paint",)
            (root / "made" / "report-late.json").write_text(json.dumps(
                {"pieces": {"tube_1": {"triangles": 10, "slots": ["painted_panel"]},
                            "lamp_1": {"triangles": 4, "slots": ["painted_panel"]}}}))
            (root / "made" / "lamp_1.gltf").write_text("{}")
            assert late_bake.judge_made(root, {}, None).answer == checks.PASS
            assert late_bake.judge_surfaces(root, {}, None).answer == checks.PASS
        finally:
            late_bake.library_names = kept


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    test_gates()
    print("late_bake: 1 test passes")
