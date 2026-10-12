"""The finish-map re-test's rows hold together: the surface stage's method rows on round 4's six takes, round 4's
turntable read back for free, every paid row with its estimate. No spend.

Run: .venv/bin/python score/stages/finishmap/finishmap_test.py
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from score.stages.finishmap import trial  # noqa: E402


def test_the_rows_hold_together():
    rows = trial.stages()
    assert [stage.name for stage in rows] == ["fm-inputs", "fm-turntable", "fm-lists", "fm-maps", "fm-names", "fm-segvigen",
                                              "fm-parts"]
    assert all(stage.euros for stage in rows if stage.paid) and not any(stage.paid for stage in rows[:2])
    assert all(stage.grain == "world" for stage in rows)


if __name__ == "__main__":
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
