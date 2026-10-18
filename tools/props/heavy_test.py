"""Check that a heavy step is refused on this PC and runs where the cloud runner's mark is set.

Run: python3 tools/props/heavy_test.py
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import heavy  # noqa: E402
import local_models  # noqa: E402


def test_refused_here_and_run_on_a_marked_machine():
    kept = os.environ.pop(local_models.ALLOW, None)
    try:
        try:
            heavy.refuse_here("the paint")
        except SystemExit as refused:
            assert str(refused) == "refused: the paint runs on a cloud machine; submit it as a batch", refused
        else:
            raise AssertionError("a heavy step ran on this PC")
        os.environ[local_models.ALLOW] = "1"
        heavy.refuse_here("the paint")
    finally:
        os.environ.pop(local_models.ALLOW, None)
        if kept is not None:
            os.environ[local_models.ALLOW] = kept


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    test_refused_here_and_run_on_a_marked_machine()
    print("heavy_test: ok")
