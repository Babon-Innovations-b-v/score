"""The moved-rows check reads every row's declared files, not only its code version: on 8b402226 (blender_cloud.py,
outside every code version but declared by the turntables) it names the turntable rows in every place.

Run: .venv/bin/python -m pytest score/stages/moved_test.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score.stages import moved  # noqa: E402


def test_a_declared_file_or_folder_holds_a_changed_path():
    assert moved.holds("tools/props/cloud/blender_cloud.py", "tools/props/cloud/blender_cloud.py")
    assert moved.holds("data/library", "data/library/materials.json")
    assert not moved.holds("data/library", "data/library_old/x.json")


def test_8b402226_moves_the_turntables_by_the_file_they_declare():
    found = moved.moved("8b402226^", "8b402226")
    assert {"surfaces-turntable", "people-turntable", "crops-surfaces-turntable"} <= set(found), sorted(found)
    turntable = found["surfaces-turntable"]
    assert not turntable["code"] and len(turntable["files"]["tools/props/cloud/blender_cloud.py"]) >= 17
