"""Check painting by parts (job paint, 2026-10-08): the patchiness check (patchy.py) passes clean paint and fails
blotches, and labels.py gives every face one part and every part one material, however noisy the splitter's vote.

It needs numpy, scipy and trimesh, which only the prop environment has. Run by the gate with the system python, this
hands itself to the prop environment when the box has one, and says it skipped when it does not.
Run: python3 tools/props/library/paint_test.py
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
    if PROPS_PYTHON.exists() and os.environ.get("PAINT_TEST_HANDED") != "1":
        os.environ["PAINT_TEST_HANDED"] = "1"
        os.execv(str(PROPS_PYTHON), [str(PROPS_PYTHON), __file__])
    print("skipped: no prop environment on this box")
    sys.exit(0)

sys.path.insert(0, str(HERE))
import labels  # noqa: E402
import patchy  # noqa: E402
import route  # noqa: E402


def seat():
    """A seat-sized box, finely divided (about 12,000 faces)."""
    box = trimesh.creation.box(extents=(0.5, 0.1, 0.5))
    for _ in range(5):
        box = box.subdivide()
    return box


def test_one_material_passes():
    mesh = seat()
    assert patchy.score(mesh, np.zeros(len(mesh.faces), dtype=int))["pass"]


def test_blotches_through_the_paint_fail():
    """The greenhouse chair's seat: one paint with dark blotches scattered through it."""
    mesh = seat()
    painted = np.zeros(len(mesh.faces), dtype=int)
    rng = np.random.default_rng(1)
    for middle in mesh.triangles_center[rng.choice(len(mesh.faces), 40, replace=False)]:
        painted[np.linalg.norm(mesh.triangles_center - middle, axis=1) < 0.02] = 1
    found = patchy.score(mesh, painted)
    assert not found["pass"] and found["stray"] > patchy.STRAY_LIMIT, found


def test_a_separate_small_piece_is_a_part_not_a_blotch():
    """A knob of its own (a separate piece of the shape) in another material is not stray paint."""
    body, knob = seat(), trimesh.creation.icosphere(subdivisions=2, radius=0.01)
    knob.apply_translation((0.0, 0.07, 0.0))
    mesh = trimesh.util.concatenate([body, knob])
    painted = np.r_[np.zeros(len(body.faces), dtype=int), np.ones(len(knob.faces), dtype=int)]
    assert patchy.score(mesh, painted)["stray"] == 0.0


def two_blocks():
    """Two blocks standing on each other, joined into one surface: a base and a smaller lid on it."""
    base = trimesh.creation.box(extents=(0.4, 0.2, 0.4))
    lid = trimesh.creation.box(extents=(0.3, 0.05, 0.3))
    lid.apply_translation((0.0, 0.125, 0.0))
    mesh = trimesh.util.concatenate([base, lid])
    for _ in range(4):
        mesh = mesh.subdivide()
    return labels.welded(mesh)


def test_a_noisy_vote_settles_into_whole_parts():
    """Every face gets one part; the splitter's vote, wrong on a fifth of the faces at random, settles to the true
    parts on the model's own surfaces, with no crumbs left."""
    mesh = two_blocks()
    truth = (mesh.triangles_center[:, 1] > 0.1).astype(int)
    rng = np.random.default_rng(2)
    noisy = np.where(rng.random(len(truth)) < 0.2, 1 - truth, truth)
    scores = np.eye(2)[noisy]
    part_of, clear = labels.by_regions(mesh, scores, labels.smoothed_parts(scores, labels.neighbour_matrix(mesh)))
    part_of = labels.without_crumbs(mesh, part_of)
    assert clear > labels.CLEAR_LEAST
    wrong = mesh.area_faces[part_of != truth].sum() / mesh.area
    assert wrong < 0.02, wrong
    assert patchy.score(mesh, part_of)["stray"] == 0.0


def test_every_part_takes_one_material_by_its_lit_colour():
    """A part in light and shade takes one material, the one its lit side shows; no face leaves it."""
    mesh = two_blocks()
    part_of = (mesh.triangles_center[:, 1] > 0.1).astype(int)
    blue = labels.lab(np.array([0.2, 0.3, 0.6]))
    grey = labels.lab(np.array([0.55, 0.55, 0.55]))
    colours = np.where(part_of[:, None] == 1, blue, grey).astype(float)
    shaded = np.random.default_rng(3).random(len(colours)) < 0.5
    colours[shaded, 0] *= 0.35  # half of every part in deep shade: the lighter LIT_SHARE is read
    materials = {"seat": {"colour": [0.03, 0.06, 0.32]}, "steel": {"colour": [0.27, 0.27, 0.27]},
                 "rubber": {"colour": [0.01, 0.01, 0.01]}}
    chosen, about, names = labels.paint_parts(mesh, colours, part_of, materials)
    assert [names[index] for index in chosen] == ["steel", "seat"], [names[index] for index in chosen]


def test_the_route_refuses_patchy_labels():
    with tempfile.TemporaryDirectory() as folder:
        clean, patchy_folder = pathlib.Path(folder) / "clean", pathlib.Path(folder) / "patchy"
        for path, passed in ((clean, True), (patchy_folder, False)):
            path.mkdir()
            (path / "labels.json").write_text(json.dumps({"patchy": {"pass": passed, "faults": [] if passed else
                                                                     ["stray 0.173 > 0.03"]}}))
        found = route.painted_badly({"chair": patchy_folder, "desk": clean}, {"chair", "desk"})
    assert found == {"chair": ["stray 0.173 > 0.03"]}


def main():
    tests = [value for name, value in globals().items() if name.startswith("test_")]
    for test in tests:
        test()
    print(f"{len(tests)} checks passed")


if __name__ == "__main__":
    main()
