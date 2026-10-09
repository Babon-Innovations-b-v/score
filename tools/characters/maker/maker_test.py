"""The character maker's pure pieces: the spec check, the face's kept boxes and the hair shell's grid. Nothing here
loads a model or needs numpy beyond the grid's own maths."""
import json
import pathlib
import sys

import numpy as np
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import face_pick  # noqa: E402
import hair_shell  # noqa: E402
import spec  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
PERSON = {"name": "someone", "kind": "person", "approved": "the owner", "description": "a person",
          "hair": "short hair", "face": "a face"}


def test_the_checked_in_specs_can_be_made():
    for path in sorted((REPO / "data/characters/makes").glob("*.json")):
        found = spec.read(path)
        assert found["name"] == path.stem


def test_a_spec_without_approval_is_refused():
    assert "no approved" in spec.problems_of(dict(PERSON, approved=""))


def test_a_spec_needs_a_picture_or_words():
    problems = spec.problems_of(dict(PERSON, description=None))
    assert "neither a picture nor a description" in problems


def test_a_relative_picture_is_refused_and_one_from_home_is_kept():
    assert any("not an absolute path" in problem for problem in spec.problems_of(dict(PERSON, picture="a.png")))
    assert not spec.problems_of(dict(PERSON, picture="~/a.png"))
    assert spec.inputs_of(dict(PERSON, picture="~/a.png"))["picture"].is_absolute()


def test_an_unknown_outfit_is_refused():
    assert any("outfit 'gown'" in problem for problem in spec.problems_of(dict(PERSON, outfits=["gown"])))


def test_reading_raises_with_every_problem(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"name": "bad", "kind": "robot"}))
    with pytest.raises(spec.SpecError, match="no approved.*kind 'robot'"):
        spec.read(path)


def test_take_c_keeps_his_own_face_boxes():
    joints = {"LeftEye": [0.031, 1.649, 0.06], "HeadEnd": [0.0, 1.757, 0.0]}
    view = {"window": [-0.145, 0.145, 1.495, 1.785], "size": 1024}
    nose, mouth = face_pick.boxes(joints, view, 0.0, False)
    # The nose box sits between 35 and 50 mm under the eyes, centred a little to his left.
    assert nose[1] < nose[3] and mouth[1] < mouth[3]
    assert nose[3] < mouth[1]
    assert abs((nose[0] + nose[2]) / 2 - 512) < 5
    assert face_pick.boxes(joints, view, 0.0, True) == [nose]


def test_the_hair_grid_runs_from_the_crown_to_the_hairline():
    dirs = hair_shell.directions(8, 16)
    assert dirs.shape == (9, 16, 3)
    assert np.allclose(np.linalg.norm(dirs, axis=-1), 1.0)
    assert np.allclose(dirs[0], [0.0, 1.0, 0.0])
    assert (dirs[-1][:, 1] < dirs[1][:, 1]).all()


def test_the_hair_mesh_closes_every_row():
    grid = np.random.default_rng(1).normal(size=(5, 12, 3))
    points, faces = hair_shell.mesh(grid, grid[-1] * 0.9)
    assert len(points) == 1 + 4 * 12 + 12
    assert faces.max() == len(points) - 1
    assert len(faces) == 12 + 2 * 12 * 3 + 2 * 12
