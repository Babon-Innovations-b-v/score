"""delight.py's invariant: of the pictures asked for, only those without an unlit copy are sent and priced; a
picture that is not there is refused before anything is rented; and the time estimate of what is left pays the
set-up once and the same for each further picture.

Each row is a folder of pictures (some with their unlit copy made) and the pictures asked for; the one test runs
`to_make` on it and prices what it leaves with `expected_minutes`.

Break that turns it red: in `to_make` drop the `not (UNLIT / path.name).exists()` test (row "made-is-skipped"
and "all-made" leave too much), or its `is_file` refusal (row "missing-is-refused"); or make `expected_minutes`
grow other than by one set-up plus the same for each picture (row "four-new" prices off the line).
"""
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import delight  # noqa: E402

MISSING = "no picture"


@pytest.mark.parametrize("pictures, unlit, asked, left", [
    pytest.param(["made.png", "new.png"], ["made.png"], ["made.png", "new.png"], ["new.png"], id="made-is-skipped"),
    pytest.param(["made.png"], ["made.png"], ["made.png"], [], id="all-made"),
    pytest.param(["a.png", "b.png", "c.png", "d.png"], [], ["a.png", "b.png", "c.png", "d.png"],
                 ["a.png", "b.png", "c.png", "d.png"], id="four-new"),
    pytest.param([], [], ["not-there.png"], MISSING, id="missing-is-refused"),
])
def test_delight_makes_each_unlit_copy_once(tmp_path, monkeypatch, pictures, unlit, asked, left):
    monkeypatch.setattr(delight, "UNLIT", tmp_path / "unlit")
    delight.UNLIT.mkdir()
    for name in pictures:
        (tmp_path / name).write_bytes(b"")
    for name in unlit:
        (delight.UNLIT / name).write_bytes(b"")
    paths = [tmp_path / name for name in asked]
    if left == MISSING:
        with pytest.raises(SystemExit, match=MISSING):
            delight.to_make(paths)
        return
    wanted = delight.to_make(paths)
    assert wanted == [tmp_path / name for name in left]
    none, one = delight.expected_minutes(0), delight.expected_minutes(1)
    assert none > 0 and one > none
    assert delight.expected_minutes(len(wanted)) - none == pytest.approx(len(wanted) * (one - none))
