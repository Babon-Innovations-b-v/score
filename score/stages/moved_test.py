"""The moved-rows check reads every row's declared files, not only its code version: on 8b402226 (blender_cloud.py,
outside every code version but declared by the turntables) it names the turntable rows in every place.

Run: .venv/bin/python -m pytest score/stages/moved_test.py
"""
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.graph import _code  # noqa: E402
from score.stages import moved  # noqa: E402


def test_8b402226_moves_the_turntables_by_the_file_they_declare():
    found = moved.moved("8b402226^", "8b402226")
    assert {"surfaces-turntable", "people-turntable", "crops-surfaces-turntable"} <= set(found), sorted(found)
    turntable = found["surfaces-turntable"]
    assert not turntable["code"] and len(turntable["files"]["tools/props/cloud/blender_cloud.py"]) >= 17


def test_1f90a0fe_moves_the_rows_its_new_gap_files_reach():
    """A new data file a row declares: the gap files of 1f90a0fe re-keyed the paid paint at three places, which a check
    of changed paths alone missed in the working tree."""
    found = moved.moved("1f90a0fe^", "1f90a0fe")
    assert sorted(found["surfaces-paint"]["files"]) == [f"data/checks/gaps/{place}.json"
                                                        for place in ("launch", "square", "street")], found
    assert "demo-film" not in found


def test_a_file_moved_into_framework_and_edited_in_the_same_change_is_named():
    """A module moved into FRAMEWORK and edited in the same change makes the rows that read it again (no narrowing
    carry): it is named, a plain move is not."""
    repo = pathlib.Path(tempfile.mkdtemp(prefix="moved_repo_")).resolve()
    (repo / "score" / "graph").mkdir(parents=True)
    declared = repo / "score" / "graph" / "_code.py"

    def commit(framework, helpers):
        declared.write_text(f"FRAMEWORK = {{REPO / name for name in {framework!r}}}\n")
        for name, text in helpers.items():
            (repo / name).write_text(text)
        for command in (["add", "."], ["-c", "user.name=test", "-c", "user.email=test@test", "commit", "-qm", "step"],
                        ["rev-parse", "HEAD"]):
            done = subprocess.run(["git", "-C", str(repo), *command], check=True, capture_output=True, text=True)
        return done.stdout.strip()

    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    saved = _code.REPO
    _code.REPO = repo
    try:
        first = commit((), {"plain.py": "A = 1\n", "edited.py": "B = 1\n"})
        second = commit(("plain.py", "edited.py"), {"edited.py": "B = 2\n"})
        assert moved.edited_into_framework(first, second) == ["edited.py"]
    finally:
        _code.REPO = saved
