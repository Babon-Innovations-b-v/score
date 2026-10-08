"""Checks for the unlit-copy runner's list and estimate, without renting anything."""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import delight  # noqa: E402


def test_a_picture_with_its_unlit_copy_already_made_is_skipped():
    with tempfile.TemporaryDirectory() as folder:
        folder = pathlib.Path(folder)
        made, new = folder / "made.png", folder / "new.png"
        made.write_bytes(b"")
        new.write_bytes(b"")
        kept = delight.UNLIT
        delight.UNLIT = folder / "unlit"
        try:
            delight.UNLIT.mkdir()
            (delight.UNLIT / "made.png").write_bytes(b"")
            assert delight.to_make([made, new]) == [new]
        finally:
            delight.UNLIT = kept


def test_a_missing_picture_is_refused_before_anything_is_rented():
    try:
        delight.to_make([os.devnull + "-not-there.png"])
    except SystemExit as refused:
        assert "no picture" in str(refused)
    else:
        raise AssertionError("a missing picture was accepted")


def test_the_estimate_counts_setup_and_each_picture():
    assert delight.expected_minutes(0) == delight.SETUP_MINUTES
    assert delight.expected_minutes(4) == delight.SETUP_MINUTES + 4 * delight.SECONDS_A_PICTURE / 60


if __name__ == "__main__":
    for name, check in sorted(globals().items()):
        if name.startswith("test_") and callable(check):
            check()
            print(f"ok  {name}")
