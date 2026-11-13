"""The vendored tools' table against the repository, and its checks on a stand-in repository.

    the real table    every vendor/ folder has a row, every wired tool's callers name it, its image and stages exist
    a new tool        a vendor/ folder with no row is refused by name
    a stale caller    a caller that never names its tool, or is gone, is refused
    a gone image      a wired tool's image with no folder is refused
    no why            a row without its reason is refused

One test, test_every_vendored_tool_is_accounted_for, runs the real table and a case table of stand-in
repositories (each row: what is changed in the stand-in, and the faults that must come back) through `faults`.

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


CALLER = "tools/run/call.py"

# name, what the stand-in changes, the faults `faults` must give; None runs the real table on the real repository
CASES = [
    ("the real table", None, []),
    ("the stand-in as made", {}, []),
    ("a new tool without a row", {"add": ("vendor/newtool",)},
     ["vendor/newtool is vendored but has no row in score/adapters/vendored"]),
    ("a caller that never names its tool", {"caller": "print('moved on')\n"},
     ["toolkit: caller tools/run/call.py never names toolkit"]),
    ("a caller that is gone", {"caller": None}, ["toolkit: caller tools/run/call.py is not there"]),
    ("a gone image and stage", {"remove": ("tools/cloud/images/toolbox", "score/stages/shaping")},
     ["toolkit: image toolbox has no folder in tools/cloud/images",
      "toolkit: stage package score/stages/shaping is not there"]),
    ("no why", {"why": ""}, ["toolkit: no why"]),
]


def stand_in(root, change):
    """A repository of one vendored tool, its caller, its image and its stage, with `change` applied; its table."""
    for folder in ("vendor/toolkit", "tools/cloud/images/toolbox", "score/stages/shaping", "tools/run",
                   *change.get("add", ())):
        (root / folder).mkdir(parents=True)
    caller = change.get("caller", "subprocess.run(['vendor/toolkit/run'])\n")
    if caller is not None:
        (root / CALLER).write_text(caller)
    for folder in change.get("remove", ()):
        shutil.rmtree(root / folder)
    row = {"use": vendored.WIRED, "image": "toolbox", "names": ("toolkit",), "callers": (CALLER,),
           "stages": ("shaping",), "why": change.get("why", "a stand-in")}
    return {"toolkit": row}


def test_every_vendored_tool_is_accounted_for():
    for name, change, expected in CASES:
        if change is None:
            found = vendored.faults()
        else:
            with tempfile.TemporaryDirectory(prefix="vendored-test-") as folder:
                root = pathlib.Path(folder)
                found = vendored.faults(stand_in(root, change), root)
        assert found == expected, f"{name}: {found}"


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[3] / "conftest.py"))["refuse_outside_sandbox"]()
    test_every_vendored_tool_is_accounted_for()
    print(f"vendored_test: {len(CASES)} cases passed")
