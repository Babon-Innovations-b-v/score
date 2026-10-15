"""The moved-rows check reads every row's declared files, not only its code version: on 8b402226 (blender_cloud.py,
outside every code version but declared by the turntables) it names the turntable rows in every place.

Run: .venv/bin/python -m pytest score/stages/moved_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

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
