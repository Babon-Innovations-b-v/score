"""Check that a raw model image-to-3dlab 0.3.9+ turned to face +Z comes back to Pixal3D's -Z before the finish, its
camera folder with it, and that a raw model it never turned is left byte for byte as it was.

The raw model here is a small made shape, turned and stamped by the vendored lab's own glb_turn, as its generator turns
every model it writes, so the case is the real stamp and the real turn.

Needs numpy and trimesh, which only the prop environment has; hands itself over like the others.

Run: PROPS_HOME=$(mktemp -d) python3 tools/props/pixal_test.py
"""
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROPS_PYTHON = pathlib.Path(os.environ.get("PROPS_PYTHON", pathlib.Path.home() / ".farm-factory-props/env/bin/python"))

try:
    import numpy as np
    import trimesh
except ImportError:
    if PROPS_PYTHON.exists() and os.environ.get("PIXAL_TEST_HANDED") != "1":
        os.environ["PIXAL_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import clean_finish  # noqa: E402
import glb_file  # noqa: E402
import pixal  # noqa: E402
from image_to_3dlab.glb_turn import CAMERA_KEY, FACING_KEY, turn_cameras, turn_glb  # noqa: E402


def raw_model(folder):
    """A lopsided box written as a raw model with its camera folder (the camera pixal3d.cpp stages), so a half turn
    shows in every coordinate."""
    shape = trimesh.creation.box(extents=(0.4, 0.2, 0.1))
    shape.vertices += (0.3, 0.05, -0.2)
    raw = folder / "take.glb"
    raw.write_bytes(shape.export(file_type="glb"))
    views = raw.with_suffix(".svviews")
    views.mkdir()
    (views / "transforms.json").write_text(json.dumps(
        {"camera_angle_x": clean_finish.GAUGE_FOV, "mesh_scale": 1,
         "frames": [{"file_path": "input.png", "transform_matrix": clean_finish.GAUGE_CAMERA}]}, indent=2))
    return raw


def turned_as_the_lab_turns(raw):
    """The raw model and its camera folder as image-to-3dlab 0.3.9+'s generator leaves them (face_front)."""
    raw.write_bytes(turn_glb(raw.read_bytes()))
    cameras = raw.with_suffix(".svviews") / "transforms.json"
    cameras.write_text(json.dumps(turn_cameras(json.loads(cameras.read_text())), indent=2))


def positions(raw):
    document, views = glb_file.read(raw)
    return glb_file.positions(document, views)


def test_a_turned_raw_model_comes_back_to_minus_z_with_its_camera():
    with tempfile.TemporaryDirectory() as folder:
        raw = raw_model(pathlib.Path(folder))
        before = positions(raw)
        camera = json.loads((raw.with_suffix(".svviews") / "transforms.json").read_text())
        turned_as_the_lab_turns(raw)
        assert pixal.turned_by_lab(raw)
        assert np.allclose(positions(raw), before * [-1, 1, -1])
        assert pixal.facing_back(raw) is True
        assert np.array_equal(positions(raw), before)
        document, _ = glb_file.read(raw)
        assert FACING_KEY not in (document["asset"].get("extras") or {})
        assert json.loads((raw.with_suffix(".svviews") / "transforms.json").read_text()) == camera
        assert CAMERA_KEY not in camera


def test_an_unturned_raw_model_is_left_as_it_is():
    with tempfile.TemporaryDirectory() as folder:
        raw = raw_model(pathlib.Path(folder))
        model = raw.read_bytes()
        cameras = (raw.with_suffix(".svviews") / "transforms.json").read_text()
        assert pixal.facing_back(raw) is False
        assert raw.read_bytes() == model
        assert (raw.with_suffix(".svviews") / "transforms.json").read_text() == cameras


def test_turning_back_twice_turns_once():
    with tempfile.TemporaryDirectory() as folder:
        raw = raw_model(pathlib.Path(folder))
        before = positions(raw)
        turned_as_the_lab_turns(raw)
        pixal.facing_back(raw)
        assert pixal.facing_back(raw) is False
        assert np.array_equal(positions(raw), before)


def test_the_steps_default_to_the_lock_and_a_run_takes_its_own():
    parsed = pixal.options_parser().parse_args(["in.png", "crate", "--who", "test"])
    assert parsed.steps == pixal.STEPS == 12
    arguments = pixal.generator_arguments("cut.png", "raw.glb", 3)
    assert arguments[arguments.index("--steps") + 1] == "12"
    lowered = pixal.generator_arguments("cut.png", "raw.glb", 3, 8)
    assert lowered[lowered.index("--steps") + 1] == "8" and lowered[lowered.index("--gss") + 1] == str(pixal.GUIDANCE)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, check in sorted(globals().items()):
        if name.startswith("test_") and callable(check):
            check()
            print(f"ok  {name}")
