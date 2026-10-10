"""Pins the small shapes the outfits are built from (`work_suit.py`'s plates, `face.py`'s brow slab, `plain.py`'s cap,
shoulder boards and joined pieces, `work_suit.collar`) and the space suits' colour tables (`paint.py`), on shapes made
here, so a change to how they are written is caught before a build: each output is held to a digest of its numbers.
The look is an empty folder, so every place is take C's. Numpy, scipy, trimesh and PIL; runs as a script or under
pytest."""
import hashlib
import os
import pathlib
import sys
import tempfile

import numpy as np

os.environ["MOTION_LOOK"] = tempfile.mkdtemp(prefix="people-parts-test-")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import face  # noqa: E402
import paint  # noqa: E402
import plain  # noqa: E402
import trimesh  # noqa: E402
import work_suit  # noqa: E402


def digest(*arrays):
    """A short digest of arrays' shapes and numbers, rounded to a nanometre."""
    hashed = hashlib.sha256()
    for array in arrays:
        array = np.asarray(array, dtype=np.float64)
        hashed.update(str(array.shape).encode())
        hashed.update(np.round(array, 9).tobytes())
    return hashed.hexdigest()[:16]


def test_a_plate_is_a_grid_with_walls_round_its_rim():
    assert work_suit.grid_faces(2, 3) == [[0, 1, 4], [0, 4, 3], [1, 2, 5], [1, 5, 4]]
    assert work_suit.rim_of(3, 3) == [0, 1, 2, 5, 8, 7, 6, 3]
    assert work_suit.walls([0, 1, 2], 3) == [[0, 4, 1], [0, 3, 4], [1, 5, 2], [1, 4, 5], [2, 3, 0], [2, 5, 3]]


def test_a_brow_slab_is_the_plate_on_the_skin():
    plane = trimesh.Trimesh([[-1.0, -1.0, 0.0], [1.0, -1.0, 0.0], [1.0, 1.0, 0.0], [-1.0, 1.0, 0.0]],
                            [[0, 1, 2], [0, 2, 3]], process=False)
    grid = np.array([[x_place, y_place] for y_place in (0.0, 0.01, 0.02) for x_place in (0.0, 0.01, 0.02, 0.03)])
    points, faces = face.slab(plane, grid, 3, 4)
    assert len(points) == 24 and len(faces) == 12 + 2 * 10
    assert digest(points, faces) == "f5b42c0461ce4837"


def test_pieces_are_joined_with_their_faces_renumbered():
    first = (np.zeros((3, 3)), np.array([[0, 1, 2]]))
    second = (np.ones((4, 3)), np.array([[0, 1, 2], [0, 2, 3]]))
    for joined in (face.joined, plain.joined):
        points, faces = joined([first, second])
        assert points.shape == (7, 3)
        assert faces.tolist() == [[0, 1, 2], [3, 4, 5], [3, 5, 6]]


def head_points():
    """Points over a head-sized sphere."""
    sphere = trimesh.creation.icosphere(subdivisions=3, radius=0.09)
    return np.asarray(sphere.vertices) + [0.0, 1.62, 0.0]


def test_a_cap_is_its_crown_band_and_peak():
    head = head_points()
    for peaked, expected in ((True, "35298ffb172609c2"), (False, "0a770ff5da698c54")):
        made = plain.cap(head, 1.64, peaked)
        assert sorted(made) == ["cap_band", "cap_crown", "cap_peak"]
        assert digest(*(array for key in sorted(made) for array in made[key])) == expected


class Shoulders:
    """What shoulder boards are laid on: the arms' joints."""

    joints = {"LeftArm": np.array([0.161, 1.401, -0.063]), "RightArm": np.array([-0.161, 1.401, -0.063])}


def test_shoulder_boards_lie_on_the_shoulders():
    box = trimesh.creation.box(extents=(0.5, 0.2, 0.3))
    box.apply_translation([0.0, 1.35, -0.06])
    points, faces = plain.shoulder_boards({"mesh": box}, Shoulders())
    assert digest(points, faces) == "c600d7bde86a41e5"


def test_a_collar_stands_round_the_neck():
    neck = trimesh.creation.cylinder(radius=0.06, height=0.4, sections=48)
    neck.apply_translation([0.0, 1.5, work_suit.NECK_CENTRE[1]])
    angles = np.linspace(-np.pi, np.pi, work_suit.ANGLES, endpoint=False)
    line = (angles, np.full(work_suit.ANGLES, 1.45), np.full(work_suit.ANGLES, 0.07), np.full(work_suit.ANGLES, 0.065))
    points, faces = work_suit.collar(neck, line)
    assert digest(points, faces) == "185465f4581259d8"


def test_a_suit_part_takes_the_colour_of_the_first_name_it_starts_with():
    assert paint.suit_colour("band_red_arm_l") == paint.SUIT_RED
    assert paint.suit_colour("visor_rim") == paint.GOLD
    assert paint.american_colour("helmet_rim") == (216, 214, 206)
    assert paint.american_colour("helmet") == (236, 234, 226)
    for colour_of in (paint.suit_colour, paint.american_colour):
        try:
            colour_of("no_such_part")
        except ValueError:
            continue
        raise AssertionError(f"{colour_of.__name__} gave a colour to a part it does not know")


if __name__ == "__main__":
    for name, check in list(globals().items()):
        if name.startswith("test_"):
            check()
            print("ok", name)
