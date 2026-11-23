"""The calibration pass holds a known-good copy to pass and a wrong object to fail (#163 step 3): one table on a small
box truth (0.5 x 0.4 x 0.8 m, its top one material and its sides another, 10 kg, its hull its collider), every answer
worked by hand: the box with each triangle split in four is still the box, upright (F-score 1, each material held
whole), and cut to half its triangles still its shape (F-score 1); 10 kg in
0.16 m3 is 62.5 kg/m3, plausible, 2000 kg is 12 500 kg/m3 (heavier than steel through) and 0.1 kg 0.6 kg/m3, both
flagged; a box whose top slopes 5 degrees fails straight.py's 2 degrees in a square kind and is not judged in another;
a spread over one known-good copy at 0.9 and two wrong objects at 0.6 and 0.95 against a 0.75 bar passes all the
good and fails half the wrong; the copy's triangle density is the truth's own, read as their ratio, 1.

Breaks (each applied once, seen red, reverted), in tools/props/bench/calibrate/__init__.py:
- remeshed tiling the materials where each face's four repeat it: the copy's finish no longer holds its top.
- tools/props/bench/measures/_align.py TIE back at 0.01: the box cut to half its triangles stands on its head.
- mass_check without DENSITY_MOST: the 2000 kg box passes as plausible.
- route_checks judging straight.py on every kind: the sloped box fails as a chair.
- spread counting a wrong row that passes as failed: the share of wrong failing reads 1.
- compared reading a relative bar's raw value: the triangle density reads 1000, not 1.
"""
import numpy as np
import pytest
import trimesh

from tools.props.bench import calibrate

SIDES = (0.5, 0.4, 0.8)


def standing(mesh):
    low, high = mesh.bounds
    mesh.apply_translation((-(low[0] + high[0]) / 2, -(low[1] + high[1]) / 2, -low[2]))
    return mesh


def truth_of(mesh, mass=10.0, name="simready_box_test_a01"):
    mesh = standing(mesh)
    return {"id": name, "vertices": np.asarray(mesh.vertices, dtype=float), "faces": np.asarray(mesh.faces),
            "face_material": (mesh.face_normals[:, 2] > 0.5).astype(np.int32),
            "face_prim": np.zeros(len(mesh.faces), dtype=np.int32), "box": mesh.bounds, "size": mesh.extents,
            "mass": mass, "colliders": [{"vertices": mesh.vertices, "faces": None}], "friction": 0.5}


def box(mass=10.0):
    return truth_of(trimesh.creation.box(SIDES).subdivide().subdivide(), mass)


def sloped():
    """The box with its top tipped 5 degrees: one side 3.5 cm higher than the other."""
    mesh = trimesh.creation.box(SIDES).subdivide().subdivide()
    top = mesh.vertices[:, 2] > 0
    mesh.vertices[top, 2] += mesh.vertices[top, 0] * np.tan(np.radians(5))
    return truth_of(mesh)


def copy_found(copy):
    import measures
    truth = box()
    found = measures.measured(truth, copy(truth))
    return {"f_score": found["shape"]["f_score"], "held_least": found["finish"]["held_least"],
            "up_error": round(found["alignment"]["up_error"] / 10)}


def spread_found():
    shape = lambda value: {"shape": {"ring": value}, "truth_clean": {"triangles_per_m2": 1000.0},
                           "truth_sides": [0.5, 0.4, 0.8]}
    record = {"split": "tune", "good": shape(0.9), "cut": shape(0.8),
              "wrong": [{"other": "a", "found": shape(0.6)}, {"other": "b", "found": shape(0.95)}]}
    found = calibrate.spread([record], "tune")
    return {"good": found["shape.ring"]["good"]["passed"], "wrong": found["shape.ring"]["wrong"]["failed"],
            "density": found["clean.triangles_per_m2"]["good"]["median"]}


CASES = [
    ("the box cut again", lambda: copy_found(calibrate.remeshed), {"f_score": 1.0, "held_least": 1.0, "up_error": 0}),
    ("the box cut to half its triangles", lambda: copy_found(calibrate.cut), {"f_score": 1.0, "up_error": 0}),
    ("10 kg in its 0.16 m3", lambda: calibrate.mass_check(box())["plausible"], True),
    ("2000 kg in its 0.16 m3", lambda: calibrate.mass_check(box(2000.0))["plausible"], False),
    ("0.1 kg in its 0.16 m3", lambda: calibrate.mass_check(box(0.1))["plausible"], False),
    ("the straight box as a box", lambda: calibrate.route_checks(box(), "box")["straight"]["pass"], True),
    ("its top sloped 5 degrees as a box", lambda: calibrate.route_checks(sloped(), "box")["straight"]["pass"],
     False),
    ("its top sloped 5 degrees as a chair",
     lambda: calibrate.route_checks(sloped(), "chair / stool")["straight"]["pass"], True),
    ("a spread of one good and two wrong", spread_found, {"good": 1.0, "wrong": 0.5, "density": 1.0}),
]


@pytest.mark.parametrize("name, found, expected", CASES, ids=[case[0] for case in CASES])
def test_a_known_good_copy_passes_and_a_wrong_object_fails(name, found, expected):
    value = found()
    if isinstance(expected, dict):
        assert {key: round(value[key], 3) for key in expected} == expected, (name, value)
    else:
        assert value is expected, (name, value)
