"""The character maker's pure pieces: the spec check, the face's kept boxes and the hair shell's grid. Nothing here
loads a model or needs numpy beyond the grid's own maths."""
import json
import pathlib
import subprocess
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
    """A prop route spec carries its person's name (its takes go to that person's candidates folder), in a file named
    <name>_prop.json."""
    for path in sorted((REPO / "data/characters/makes").glob("*.json")):
        found = spec.read(path)
        assert found["name"] + ("_prop" if found.get("route") == "prop" else "") == path.stem


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


def test_experimental_routes_and_drapes_run_only_when_asked_for():
    """Fault (audit of 2026-10-11, items 1-3): make.py over data/characters/makes/*.json started paid prop-route runs
    (the player fails tucks and pokes, Nev is not made), the animal route had never run on a world, and every person
    was draped by Newton, the drapes the owner rejected, with no one asking."""
    import make

    prop = dict(PERSON, name="player_prop", route="prop", outfit_words={"work": "a work suit"})
    animal = {"name": "fish", "kind": "animal", "approved": "the owner", "description": "a fish"}
    undraped = dict(PERSON, name="nev")
    draped = dict(PERSON, name="ama", drape_simulator="newton")
    refused = make.refusals([prop, animal, undraped, draped], experimental=False)
    assert [line.split(":")[0] for line in refused] == ["player_prop", "fish", "nev"], refused
    assert [line.split(":")[0] for line in make.refusals([prop, animal, draped], experimental=True)] == []
    assert "drape_simulator 'warp'" in spec.problems_of(dict(PERSON, drape_simulator="warp"))[0]


def test_the_experimental_routes_refuse_when_started_round_make(tmp_path):
    """Fault (review of 2026-10-11): --experimental was checked only in make.py, so prop_person.py run by hand and
    route.make called directly made a prop-route person or an animal without it."""
    import subprocess
    started = subprocess.run([sys.executable, str(REPO / "tools/characters/maker/prop_person.py"),
                              str(REPO / "data/characters/makes/player_prop.json"), "--who", "a check", "--dry-run"],
                             capture_output=True, text=True)
    assert started.returncode != 0 and "only with --experimental" in started.stderr
    sys.path.insert(0, str(REPO / "tools/characters/animals"))
    import route
    with pytest.raises(SystemExit, match="only with make.py --experimental"):
        route.make({"name": "fish_tang"}, tmp_path, "a check", dry_run=True)
    assert not (tmp_path / "work").exists()

def test_a_drape_has_no_default_simulator(tmp_path):
    """Fault (audit of 2026-10-11, item 1): drape_garment.py and rebuild.py draped with Newton by default, the drapes
    the owner rejected and drape_measure fails."""
    import drape_garment

    with pytest.raises(ValueError, match="no default simulator"):
        drape_garment.drape(tmp_path / "body", "work_suit", tmp_path / "out", "work")
    assert not (tmp_path / "out").exists()


def test_a_spec_bind_pose_is_written_over_the_measured_pose(tmp_path):
    """A wider A-pose (2026-10-13): the spec's numbers replace the measured ones, the rest stay; an unknown number is
    refused."""
    import prop_chain
    pose = tmp_path / "pose.json"
    pose.write_text(json.dumps({"arm_degrees": 67.3, "hands_forward_m": 0.04, "ankles_m": 0.21}))
    prop_chain.widened(pose, {"arm_degrees": 45, "ankles_m": 0.35})
    assert json.loads(pose.read_text()) == {"arm_degrees": 45, "hands_forward_m": 0.04, "ankles_m": 0.35}
    with pytest.raises(SystemExit):
        prop_chain.widened(pose, {"elbow_degrees": 10})


def test_the_pose_picture_words_name_no_one_by_pronoun():
    """The pose picture's words said "her own face" for every look, the player's too (read from the file: its module
    needs the picture environment)."""
    words = (pathlib.Path(__file__).resolve().parent / "prop_closeup.py").read_text()
    words = words[words.index("POSE_PICTURE = ("):words.index("def wording")]
    assert " her " not in words and " his " not in words


def test_an_outfit_without_a_palette_can_name_shoes_as_boots():
    """2026-10-13: with no shoe to choose, the judge gave kit_m_broad's shoes the belt's material."""
    props_python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    if not props_python.exists():
        pytest.skip("no props environment on this box")
    ask = ("import prop_parts; shoes = [name for name in prop_parts.palette_of('uniform-olive') "
           "if name in prop_parts.BOOTS]; print(shoes)")
    found = subprocess.run([str(props_python), "-B", "-c", ask], capture_output=True, text=True,
                           cwd=pathlib.Path(__file__).resolve().parent)
    assert found.returncode == 0 and "black leather shoe" in found.stdout


def test_a_far_surface_with_no_faces_is_left_out_not_crashed_on(tmp_path):
    """2026-10-13: kit_m_broad's wide take has no boot part, and the build crashed on the far body's empty boots."""
    prop_build = pytest.importorskip("prop_build")
    far = tmp_path / "far.npz"
    np.savez(far, points=np.eye(3), faces=np.array([[0, 1, 2]]), surface_of_face=np.array([1]),
             weights=np.ones((3, 27)) / 27, surfaces=np.array(["skin", "clothes", "boots"]),
             colours=np.zeros((3, 3)))
    assert [item[0] for item in prop_build.far_body(far)] == ["clothes"]


def test_any_outfit_with_words_can_be_split_and_one_without_is_refused_on_the_pc(tmp_path):
    """2026-10-13: the parts step refused a kit's uniform-olive after 4 machine-minutes; now an outfit with words takes
    the work suit's material names for its roles, and one with no words is refused by `check` before any machine."""
    props_python = pathlib.Path.home() / ".farm-factory-props/env/bin/python"
    if not props_python.exists():
        pytest.skip("no props environment on this box")
    script = pathlib.Path(__file__).resolve().parent / "prop_parts.py"
    spec_file = tmp_path / "spec.json"
    spec_file.write_text(json.dumps({"outfit_words": {"uniform-olive": "an olive uniform"}}))
    ask = [str(props_python), "-B", str(script), "check", str(tmp_path), "take", str(spec_file), "--outfit"]
    assert subprocess.run(ask + ["uniform-olive"], capture_output=True).returncode == 0
    refused = subprocess.run(ask + ["driver-suit"], capture_output=True, text=True)
    assert refused.returncode != 0 and "no outfit_words" in refused.stderr


def test_pixal3d_is_bought_for_the_one_passing_close_up_with_its_arms_furthest_apart(tmp_path, monkeypatch):
    """#21: two close-up seeds by default, each drawn once, and Pixal3D on one take a look: of the passing close-ups, the one whose arms
    stand furthest apart; none passing, none bought."""
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path)
    folder = prop_person.folder_of(PERSON, "work") / "closeup"
    folder.mkdir(parents=True)
    checked = {"pp-a_s1": {"arm_rows_apart": 0.31, "pass": True}, "pp-a_s2": {"arm_rows_apart": 0.52, "pass": True},
               "pp-a_s3": {"arm_rows_apart": 0.9, "pass": False}}
    for take in checked:
        (folder / f"{take}.png").write_bytes(b"")
    (folder / "checks.json").write_text(json.dumps(checked))
    assert prop_person.closeups(PERSON, "work") == ["pp-a_s2"]
    for entry in checked.values():
        entry["pass"] = False
    (folder / "checks.json").write_text(json.dumps(checked))
    assert prop_person.closeups(PERSON, "work") == []
    words = (pathlib.Path(__file__).resolve().parent / "prop_person.py").read_text()
    assert 'spec.get("closeup_seeds", [1, 2])' in words


def test_a_failed_tucks_record_predicts_a_gap_only_on_the_same_inputs(tmp_path, monkeypatch):
    """#21: the settled pokes.json with a tuck over the gate in every clip writes a record on the hash of the take,
    spec, parts and the maker's and people tools' code, which predicts the same failure (nothing bought); a clip
    that passed writes none, and any changed input, the people tools' code included, predicts nothing."""
    import prop_person
    monkeypatch.setattr(prop_person, "CANDIDATES", tmp_path)
    folder = prop_person.folder_of(PERSON, "work")
    (folder / "parts" / "pp-a_s1").mkdir(parents=True)
    (folder / "checks").mkdir()
    (folder / "take.txt").write_text("pp-a_s1")
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"first parts")
    clips = {"walk": {"worst_tuck_out_mm": 9.32, "frames_tuck_over": 40},
             "idle": {"worst_tuck_out_mm": 6.1, "frames_tuck_over": 0}}
    (folder / "checks" / "pokes.json").write_text(json.dumps({"clips": clips}))
    assert prop_person.tucks_record(PERSON, "work") is None and prop_person.predicted_tucks(PERSON, "work") is None
    clips["idle"]["frames_tuck_over"] = 3
    (folder / "checks" / "pokes.json").write_text(json.dumps({"clips": clips}))
    record = prop_person.tucks_record(PERSON, "work")
    assert record["worst_tuck_out_mm"] == 9.32 and record["clips"] == 2, record
    assert prop_person.predicted_tucks(PERSON, "work") == record
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"new parts")
    assert prop_person.predicted_tucks(PERSON, "work") is None
    (folder / "parts" / "pp-a_s1" / "parts.npz").write_bytes(b"first parts")
    people = tmp_path / "tools" / "people"
    people.mkdir(parents=True)
    (people / "joins.py").write_text("# joins")
    (people / "joins_test.py").write_text("# a test")
    monkeypatch.setattr(prop_person, "HERE", tmp_path / "tools" / "maker")
    (tmp_path / "tools" / "maker").mkdir()
    prop_person.tucks_record(PERSON, "work")
    assert prop_person.predicted_tucks(PERSON, "work") is not None
    (people / "joins_test.py").write_text("# a test, edited")
    assert prop_person.predicted_tucks(PERSON, "work") is not None, "a test edit moved the hash"
    (people / "joins.py").write_text("# joins, fixed")
    assert prop_person.predicted_tucks(PERSON, "work") is None, "a people tools fix left the old prediction"
