"""The test rule's guard (tools/test_rule/check.py) finds every way a repository breaks the rule and nothing else: one
test file a module, named test_<invariant>.py, its docstring naming the break that turns it red, and one test function
a file (owner, 2026-11-01). ONE TEST, parametrized: each case builds a small git repository in a temp folder and lists
by hand the faults the rule says it has; nothing reads this repository.

Breaks (each applied once, seen red, reverted), in tools/test_rule/check.py:
- one file a module: faults' `if len(files) > 1:` -> `if len(files) > 2:` (two files in one module pass).
- a tests/ folder is its parent's: module_of's `if folder.name == "tests":` -> `if False:`.
- named for its invariant: file_faults' `if not path.name.startswith("test_"):` -> `if False:`.
- the break line: file_faults' `elif not BREAK_LINE.search(...)` -> `elif False:`; and BREAK_LINE's `.{0,200}?` ->
  `.*?` (a "break" and a "red" pages apart pass).
- flat tool folders: module_of's `if str(path.parent) in FLAT_TOOL_FOLDERS:` -> `if False:`.
- a tool named as a script before a bare name: named_tool's patterns tried bare name first (`r"\\b(\\w+)\\b"` moved to
  the front).
- the allowlist: faults' `if allowlisted(path):` -> `if False:`.
- vendor/ and ignored files left out, new files counted: is_test_file's vendor clause dropped; test_files'
  `"--exclude-standard"` dropped; test_files' `"--others"` dropped.
- only the named modules: faults' `if wanted and not wanted & ...:` -> `if False:`.
- one function a file: count_faults' `if count > 1 and not SECOND_TEST...` -> `if False:`; test_count's `Test*` class
  branch dropped; SECOND_TEST's `second test:` -> `xsecond test:`.
- the function debt only shrinks: count_faults' `if count > owed:`, `if count <= 1:` and `if count < owed:` each ->
  `if False:`; faults' stale-entry list dropped.
"""
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check  # noqa: E402

GOOD = '"""A sum adds up.\n\nBreaks (each applied once, seen red, reverted): `+` -> `-`.\n"""\n'
FAR = '"""A break in the code.\n\n' + "Some words go here. " * 20 + '\n\nIt goes red.\n"""\n'
TOOL = '"""{}\n\nBreaks (each applied once, seen red, reverted): `+` -> `-`.\n"""\n'
THREE = GOOD + "def test_a():\n    pass\n\n\ndef test_b():\n    pass\n\n\nclass TestC:\n    def test_c(self):\n        pass\n"
EXCUSED = GOOD.replace("A sum adds up.", "A sum adds up.\n\nsecond test: two ports, one each") + (
    "def test_a():\n    pass\n\n\ndef test_b():\n    pass\n")
ONE = GOOD + "def test_a():\n    pass\n"

# id: (files, untracked new files, .gitignore, named files, function debt, the faults the rule says it has)
CASES = {
    "one named file with its break, a tests/ folder its parent's": (
        {"score/graph/__init__.py": "", "score/graph/test_a_key_is_made_once.py": GOOD,
         ".claude/hooks/guard.py": "", ".claude/hooks/tests/test_hooks_fail_open.py": GOOD}, {}, "", (), {}, []),
    "two files in one module are one fault naming both": (
        {"score/graph/test_a.py": GOOD, "score/graph/test_b.py": GOOD, "score/store/test_c.py": GOOD}, {}, "", (), {},
        ["score/graph: 2 test files, one a module: score/graph/test_a.py, score/graph/test_b.py"]),
    "a tests/ folder is its parent's module": (
        {".claude/scripts/test_a.py": GOOD, ".claude/scripts/tests/test_b.py": GOOD}, {}, "", (), {},
        [".claude/scripts: 2 test files, one a module: .claude/scripts/test_a.py, .claude/scripts/tests/test_b.py"]),
    "a file named for its module": (
        {"score/graph/graph_test.py": GOOD}, {}, "", (), {},
        ["score/graph/graph_test.py: named for its module, not its invariant (rename to test_<invariant>.py)"]),
    "a docstring without its break": (
        {"score/graph/test_a.py": '"""A sum adds up."""\n', "score/store/test_b.py": FAR,
         "score/review/test_c.py": "x = 1\n",
         "score/checks/test_d.py": '"""The break that turns it\nred: `+` -> `-`."""\n'}, {}, "", (), {},
        ["score/graph/test_a.py: its docstring has no line naming the break that turns it red",
         "score/review/test_c.py: its docstring has no line naming the break that turns it red",
         "score/store/test_b.py: its docstring has no line naming the break that turns it red"]),
    "each flat folder tool is its own module": (
        {"tools/cloud/pool.py": "", "tools/cloud/batch.py": "", "tools/cloud/spread.py": "",
         "tools/cloud/test_pool_books.py": TOOL.format("Invariant of pool.py: every card booked."),
         "tools/cloud/test_batch_pays.py": TOOL.format("The pool's cards, as batch.py rents them."),
         "tools/cloud/test_spread_runs.py": TOOL.format("Invariant of tools/cloud/spread.py."),
         "tools/cloud/test_pool_deletes.py": TOOL.format("The cards pool.py deletes."),
         "tools/cloud/test_nothing.py": TOOL.format("A machine is deleted.")}, {}, "", (), {},
        ["tools/cloud/pool: 2 test files, one a module: tools/cloud/test_pool_books.py, tools/cloud/test_pool_deletes.py",
         "tools/cloud/test_nothing.py: its docstring names none of tools/cloud's tool scripts"]),
    "allowlisted, vendored and ignored files left out, new ones counted": (
        {"tools/usd/a_test.py": "", "tools/usd/b_test.py": "", "vendor/tool/x_test.py": "", "data/out/test_a.py": "",
         "score/graph/test_a.py": GOOD}, {"score/graph/test_new.py": GOOD}, "data/\n", (), {},
        ["score/graph: 2 test files, one a module: score/graph/test_a.py, score/graph/test_new.py"]),
    "named files check only their own modules": (
        {"score/graph/test_a.py": GOOD, "score/graph/test_b.py": GOOD, "score/store/store_test.py": GOOD}, {}, "",
        ("score/store/store_test.py",), {},
        ["score/store/store_test.py: named for its module, not its invariant (rename to test_<invariant>.py)"]),
    "three functions, a class's method among them": (
        {"score/graph/test_a.py": THREE}, {}, "", (), {},
        ["score/graph/test_a.py: 3 test functions, one a file (merge them into one test of the answer that matters)"]),
    "a second test: line excuses a second function": (
        {"score/graph/test_a.py": EXCUSED}, {}, "", (), {}, []),
    "a debt file at its count": (
        {"score/graph/test_a.py": THREE}, {}, "", (), {"score/graph/test_a.py": 3}, []),
    "a debt file that grew": (
        {"score/graph/test_a.py": THREE}, {}, "", (), {"score/graph/test_a.py": 2},
        ["score/graph/test_a.py: 3 test functions, its FUNCTION_DEBT entry allows 2 (a debt file may not grow)"]),
    "a debt file that shrank": (
        {"score/graph/test_a.py": THREE}, {}, "", (), {"score/graph/test_a.py": 5},
        ["score/graph/test_a.py: 3 test functions now, lower its FUNCTION_DEBT entry from 5 to 3"]),
    "a debt file down to one, and an entry whose file is gone": (
        {"score/graph/test_a.py": ONE}, {}, "", (), {"score/graph/test_a.py": 4, "score/store/test_gone.py": 2},
        ["score/graph/test_a.py: 1 test function now, delete its FUNCTION_DEBT entry",
         "score/store/test_gone.py: on FUNCTION_DEBT but not in the tree, delete its entry"]),
}


def world(root, files, new, ignore):
    """A git repository at `root` holding `files` (path: text) in its index and `new` beside them, untracked."""
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    if ignore:
        (root / ".gitignore").write_text(ignore)
    for batch in (files, new):
        for name, text in batch.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text)
        if batch is files:
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return root


@pytest.mark.parametrize("case", sorted(CASES))
def test_the_guard_lists_exactly_the_faults_the_rule_names(tmp_path, case):
    files, new, ignore, named, debt, expected = CASES[case]
    assert check.faults(world(tmp_path, files, new, ignore), named, debt) == sorted(expected)
