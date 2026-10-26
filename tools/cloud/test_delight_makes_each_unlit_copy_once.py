"""delight.py's invariants: a picture whose unlit copy is already made is not sent (or paid for) again; a picture
that is not there is refused before anything is rented; and the time estimate pays the set-up once and the same for
each further picture.

Break that turns it red: in `to_make` drop the `not (UNLIT / path.name).exists()` test, or its `is_file` refusal.
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import delight  # noqa: E402


def test_a_picture_with_its_unlit_copy_already_made_is_skipped(tmp_path, monkeypatch):
    made, new = tmp_path / "made.png", tmp_path / "new.png"
    made.write_bytes(b"")
    new.write_bytes(b"")
    monkeypatch.setattr(delight, "UNLIT", tmp_path / "unlit")
    delight.UNLIT.mkdir()
    (delight.UNLIT / "made.png").write_bytes(b"")
    assert delight.to_make([made, new]) == [new]


def test_a_missing_picture_is_refused_before_anything_is_rented(tmp_path):
    with pytest.raises(SystemExit, match="no picture"):
        delight.to_make([tmp_path / "not-there.png"])


def test_the_estimate_pays_set_up_once_and_each_picture_alike():
    none, one, four = (delight.expected_minutes(count) for count in (0, 1, 4))
    assert none > 0
    assert four - none == pytest.approx(4 * (one - none)) and one > none
