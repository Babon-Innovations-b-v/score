"""Everything that reads a raw model or its camera folder reads them facing Pixal3D's own -Z (pixal.facing_back): a
raw model image-to-3dlab 0.3.9+ turned half round to face +Z comes back, its camera folder with it, once; a raw model
it never turned is left byte for byte as it was.

The raw model is a small lopsided box, turned and stamped by the vendored lab's own glb_turn, as its generator turns
every model it writes, so the case is the real stamp and the real turn; the answer (the box's own points before the
turn) is known apart from the code.

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_a_turned_raw_model_comes_back_to_minus_z_with_its_camera: pixal.model_turned_back's
  `glb_file.turned(document, views, HALF_TURN)` dropped; and, apart, cameras_turned_back's `VIEW_TURN @` dropped.
- test_an_unturned_raw_model_is_left_as_it_is: facing_back's `if not turned_by_lab(raw):` made `if False:`.
- test_turning_back_twice_turns_once: model_turned_back's `extras.pop(FACING_KEY)` made `extras.get(FACING_KEY)` (the
  stamp stays, so a second call turns it again).
"""
import json
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
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


def test_a_turned_raw_model_comes_back_to_minus_z_with_its_camera(tmp_path):
    raw = raw_model(tmp_path)
    before = positions(raw)
    camera = json.loads((raw.with_suffix(".svviews") / "transforms.json").read_text())
    turned_as_the_lab_turns(raw)
    assert np.allclose(positions(raw), before * [-1, 1, -1])  # the lab's turn, as the case needs it
    assert pixal.facing_back(raw) is True
    assert np.allclose(positions(raw), before)
    document, _ = glb_file.read(raw)
    assert FACING_KEY not in (document["asset"].get("extras") or {})
    found = json.loads((raw.with_suffix(".svviews") / "transforms.json").read_text())
    assert CAMERA_KEY not in found
    assert np.allclose(found["frames"][0]["transform_matrix"], camera["frames"][0]["transform_matrix"])


def test_an_unturned_raw_model_is_left_as_it_is(tmp_path):
    raw = raw_model(tmp_path)
    model = raw.read_bytes()
    cameras = (raw.with_suffix(".svviews") / "transforms.json").read_text()
    assert pixal.facing_back(raw) is False
    assert raw.read_bytes() == model
    assert (raw.with_suffix(".svviews") / "transforms.json").read_text() == cameras


def test_turning_back_twice_turns_once(tmp_path):
    raw = raw_model(tmp_path)
    before = positions(raw)
    turned_as_the_lab_turns(raw)
    pixal.facing_back(raw)
    assert pixal.facing_back(raw) is False
    assert np.allclose(positions(raw), before)
