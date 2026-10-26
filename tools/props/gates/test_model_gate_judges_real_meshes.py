"""The model gate (G5, model.py) passes a real mesh in the proportions it is laid at and fails one that is not: a
cube laid as a panel, a hollow shell laid thinner than its walls; and room.py places every laid piece's own model as
HubKit does (fitted into a unit box on its foot, then scaled, turned and moved by the piece), never its box.

Every answer is worked out by hand from the case's sizes (in each comment).

Breaks that turn each test red (each applied once and seen red, 2026-10-26):
- test_a_model_is_fitted_into_a_unit_box_on_its_foot: room.unit_fit's `foot` made the box's centre
  (`(low + high) / 2`).
- test_a_laid_piece_is_its_own_model_placed_as_hubkit_places_it: room.piece_matrix's `* np.array(laid["size"])` dropped.
- test_a_model_in_its_laid_proportions_passes_and_a_cube_laid_as_a_panel_fails: model.check's `found["spread"] <=
  SPREAD_LIMIT and` dropped.
- test_a_kind_laid_thinner_than_the_least_wall_passes_solid_through_and_fails_hollow: model.least_wall returns
  THINNEST_LIMIT always; and, apart, `return SOLID_SHARE * thinnest_side - RAY_START` made `return 0.0`.
- test_a_kind_s_shape_class_comes_from_its_name_and_box: shape_class's `if middle / largest < SLENDER_SHARE: return
  "slender"` made `"chunky"`.
"""
import json
import pathlib
import sys

import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model  # noqa: E402
import room  # noqa: E402


def test_a_model_is_fitted_into_a_unit_box_on_its_foot():
    fitted = room.unit_fit(trimesh.creation.box(extents=(2.0, 4.0, 1.0)), np.eye(3))
    assert np.allclose(fitted.bounds, [[-0.5, 0.0, -0.5], [0.5, 1.0, 0.5]])


def test_a_laid_piece_is_its_own_model_placed_as_hubkit_places_it(tmp_path):
    """A 2 x 4 x 1 model laid 1 wide, 2 tall, 3 deep at (5, 0, 0), unturned: it spans x 4.5..5.5, y 0..2, z -1.5..1.5;
    a piece whose model is in no folder is left out."""
    (tmp_path / "crate.glb").write_bytes(trimesh.creation.box(extents=(2.0, 4.0, 1.0)).export(file_type="glb"))
    layout = {"kinds": {"crate": {}, "missing": {}},
              "pieces": [{"kind": "crate", "at": [5.0, 0.0, 0.0], "size": [1.0, 2.0, 3.0],
                          "x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]},
                         {"kind": "missing", "at": [0.0, 0.0, 0.0], "size": [1.0, 1.0, 1.0],
                          "x": [1, 0, 0], "y": [0, 1, 0], "z": [0, 0, 1]}]}
    found = room.placed(json.loads(json.dumps(layout)), room.models_in(tmp_path))
    assert [(index, kind) for index, kind, _ in found] == [(0, "crate")]
    assert np.allclose(found[0][2].bounds, [[4.5, 0.0, -1.5], [5.5, 2.0, 1.5]])


def test_a_model_in_its_laid_proportions_passes_and_a_cube_laid_as_a_panel_fails():
    """A panel laid 1.2 x 2.0 x 0.06 is flat: judged on its face, 1.2 : 2.0. A cube's face is 1 : 1, so its error is
    (2.0 / 1.2) - 1 = 0.67, over the 20% rule."""
    panel = model.check("hub_wall_upper_plain", trimesh.creation.box(extents=(1.2, 2.0, 0.06)), (1.2, 2.0, 0.06))
    cube = model.check("hub_wall_upper_plain", trimesh.creation.box(extents=(1.0, 1.0, 1.0)), (1.2, 2.0, 0.06))
    assert panel["pass"] and panel["watertight"] and abs(panel["thinnest"] - 0.06) < 0.005
    assert abs(cube["spread"] - 2.0 / 1.2 + 1) < 0.01 and not cube["pass"]


def test_a_kind_laid_thinner_than_the_least_wall_passes_solid_through_and_fails_hollow():
    """A 1 mm sticky note can never have a 3 mm wall: held instead to being solid through its own thickness. A shell
    with 0.2 mm walls laid 1 mm fails, and laid 10 mm (its walls then 2 mm) fails the 3 mm wall (2026-10-26)."""
    note = (0.129, 0.001, 0.281)
    solid = trimesh.creation.box(extents=note)
    hollow = trimesh.util.concatenate([solid, trimesh.creation.box(extents=(0.12, 0.0006, 0.27))])
    hollow.faces[len(solid.faces):] = hollow.faces[len(solid.faces):, ::-1]  # the inner box faces in: 0.2 mm walls
    assert model.check("note", solid, note)["pass"]
    assert not model.check("note", hollow, note)["pass"]
    assert not model.check("note", hollow, (0.129, 0.01, 0.281))["pass"]
    assert model.least_wall((1.2, 2.0, 0.06)) == 0.003


def test_a_kind_s_shape_class_comes_from_its_name_and_box():
    assert model.shape_class("hub_lattice_hip_rib", (0.12, 4.6, 0.12)) == "slender"  # 0.12 / 4.6 under a quarter
    assert model.shape_class("hub_porthole_panel", (1.2, 1.2, 0.1)) == "opening"  # its name says so
    assert model.shape_class("hub_wall_upper_plain", (1.2, 2.0, 0.06)) == "flat"  # 0.06 / 2.0 thin, 1.2 / 2.0 wide
