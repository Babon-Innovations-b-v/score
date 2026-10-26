"""The vendored tools' table against the repository, and its checks on a stand-in repository.

    the real table    every vendor/ folder has a row, every wired tool's callers name it, its image and stages exist
    a new tool        a vendor/ folder with no row is refused by name
    a stale caller    a caller that never names its tool, or is gone, is refused
    a gone image      a wired tool's image with no folder is refused
    no why            a row without its reason is refused

Breaks (each applied once, seen red, reverted), in score/adapters/vendored/__init__.py:
- the real table, a gone image: row_faults looks for the image one folder too deep (`images / "x" / row["image"]`).
- a new tool: folder_faults reports no folder without a row.
- a stale caller: caller_faults' never-names check becomes `elif False:`.
- a gone stage: row_faults' stage check never fires (`if False`).
- no why: row_faults starts from `faults = []`.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python score/adapters/vendored/test_every_vendored_tool_is_accounted_for.py
"""
import pathlib
import shutil
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(REPO))

from score.adapters import vendored  # noqa: E402


def stand_in():
    """A repository of one vendored tool, its caller, its image and its stage."""
    root = pathlib.Path(tempfile.mkdtemp(prefix="vendored-test-"))
    for folder in ("vendor/toolkit", "tools/cloud/images/toolbox", "score/stages/shaping", "tools/run"):
        (root / folder).mkdir(parents=True)
    (root / "tools/run/call.py").write_text("subprocess.run(['vendor/toolkit/run'])\n")
    row = {"use": vendored.WIRED, "image": "toolbox", "names": ("toolkit",), "callers": ("tools/run/call.py",),
           "stages": ("shaping",), "why": "a stand-in"}
    return root, {"toolkit": row}


def test_the_real_table():
    assert vendored.faults() == [], vendored.faults()


def test_a_new_tool_without_a_row():
    root, tools = stand_in()
    (root / "vendor/newtool").mkdir()
    assert vendored.faults(tools, root) == ["vendor/newtool is vendored but has no row in score/adapters/vendored"]
    shutil.rmtree(root)


def test_a_stale_caller():
    root, tools = stand_in()
    assert vendored.faults(tools, root) == []
    (root / "tools/run/call.py").write_text("print('moved on')\n")
    assert vendored.faults(tools, root) == ["toolkit: caller tools/run/call.py never names toolkit"]
    (root / "tools/run/call.py").unlink()
    assert vendored.faults(tools, root) == ["toolkit: caller tools/run/call.py is not there"]
    shutil.rmtree(root)


def test_a_gone_image_and_stage():
    root, tools = stand_in()
    shutil.rmtree(root / "tools/cloud/images/toolbox")
    shutil.rmtree(root / "score/stages/shaping")
    assert vendored.faults(tools, root) == ["toolkit: image toolbox has no folder in tools/cloud/images",
                                            "toolkit: stage package score/stages/shaping is not there"]
    shutil.rmtree(root)


def test_no_why():
    root, tools = stand_in()
    tools["toolkit"]["why"] = ""
    assert vendored.faults(tools, root) == ["toolkit: no why"]
    shutil.rmtree(root)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
    print(f"vendored_test: {len(tests)} passed")
