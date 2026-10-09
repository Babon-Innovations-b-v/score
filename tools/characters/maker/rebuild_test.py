"""rebuild.py's plain pieces: who drapes for whom, which kept pattern folder a drape was sized from, and the old beside
new numbers. Plain Python on folders the test writes; nothing is draped or built."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "props/cloud"))

import characters  # noqa: E402
import rebuild  # noqa: E402


def look(root, name, cloth="cloth", identity="body"):
    folder = root / name
    (folder / "work_drape").mkdir(parents=True)
    (folder / "identity.npz").write_text(identity)
    (folder / "work_drape/w_sim.obj").write_text(cloth)
    (folder / "work_drape/w_specification.json").write_text("{}")
    (folder / "person.json").write_text(f'{{"name": "{name}"}}')
    return folder


def test_people_wearing_byte_copies_of_a_drape_are_draped_once(tmp_path):
    looks = {"kit": look(tmp_path, "kit"), "guard": look(tmp_path, "guard"),
             "other": look(tmp_path, "other", cloth="another cloth"),
             "twin": look(tmp_path, "twin", identity="another body")}
    assert rebuild.groups_of(looks) == {"kit": ["kit", "guard"], "other": ["other"], "twin": ["twin"]}


def test_a_drape_is_sized_from_the_pattern_folder_holding_its_specification(tmp_path):
    kept = look(tmp_path, "kit") / "work_drape/w_specification.json"
    same = tmp_path / "rnd/a/patterns/w"
    named = tmp_path / "rnd/b/patterns/w"
    for folder, text in ((same, "{}"), (named, '{"other": 1}')):
        folder.mkdir(parents=True)
        (folder / "w_specification.json").write_text(text)
        (folder / "body_measurements.yaml").write_text("body: {}")
    index = rebuild.patterns_by_digest(tmp_path / "rnd")
    assert rebuild.sized_with(kept, *index) == same
    (same / "w_specification.json").write_text('{"changed": 1}')
    by_digest, by_tag = rebuild.patterns_by_digest(tmp_path / "rnd")
    assert rebuild.sized_with(kept, by_digest, by_tag) in (same, named)


def test_names_are_read_off_the_folders():
    assert rebuild.kind_of("look/nev/space_drape") == "space"
    assert rebuild.tag_of("space_drape/space_2_specification.json") == "space_2"
    assert set(rebuild.DESIGNS) == {"work", "space", "jacket", "coat", "trousers"}


def test_the_results_set_new_beside_old():
    row = rebuild.results_row({"hem_cm": 4.0, "drape": "a"}, {"hem_cm": 6.5, "drape": "b", "balloon_cm": 1.0})
    assert row["change"] == {"hem_cm": 2.5}


def test_a_make_folder_names_its_program(tmp_path):
    (tmp_path / "in").mkdir()
    (tmp_path / "in/spec.json").write_text('{"program": "rebuild.py"}')
    assert characters.program_of(tmp_path) == "rebuild.py run"
    (tmp_path / "in/spec.json").write_text("{}")
    assert characters.program_of(tmp_path) == "chain.py"


def test_drapes_that_did_not_hold_and_sleeves_off_the_arm_are_flagged():
    log = "built work\nLeft sleeve: does not reach past the elbow; left as it is (redo the drape)\nok\n"
    warnings = rebuild.warnings_in(log)
    assert warnings == ["Left sleeve: does not reach past the elbow; left as it is (redo the drape)"]
    assert rebuild.flags_of({"work_drape": False, "space_drape": True}, warnings) == [
        "work_drape did not hold on the body", warnings[0]]


def test_trousers_are_not_judged_by_the_arms_they_leave_bare():
    bare = {"came_to_rest": True, "bare_arm": {"left_arm": [0.3, 0.31], "right_arm": []}}
    assert rebuild.held_newton(bare, "trousers")
    assert not rebuild.held_newton(bare, "jacket")
    assert not rebuild.held_newton(dict(bare, came_to_rest=False), "trousers")
