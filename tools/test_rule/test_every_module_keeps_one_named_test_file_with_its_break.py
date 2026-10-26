"""The test rule's guard (tools/test_rule/check.py) finds every way a repository breaks the rule and nothing else: one
test file a module, named test_<invariant>.py, its docstring naming the break that turns it red. Each case builds a
small git repository in a temp folder and lists by hand the faults the rule says it has; nothing reads this repository.

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
"""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check  # noqa: E402

GOOD = '"""A sum adds up.\n\nBreaks (each applied once, seen red, reverted): `+` -> `-`.\n"""\n'


def world(root, files, tracked=True, ignore=""):
    """A git repository at `root` holding `files` (path: text), added to its index unless `tracked` is False."""
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text)
    if ignore:
        (root / ".gitignore").write_text(ignore)
    if tracked:
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    return root


def test_a_module_with_one_named_test_file_and_its_break_has_no_fault(tmp_path):
    world(tmp_path, {"score/graph/__init__.py": "", "score/graph/test_a_key_is_made_once.py": GOOD,
                     ".claude/hooks/guard.py": "", ".claude/hooks/tests/test_hooks_fail_open.py": GOOD})
    assert check.faults(tmp_path) == []


def test_two_test_files_in_one_module_are_one_fault_naming_both(tmp_path):
    world(tmp_path, {"score/graph/test_a.py": GOOD, "score/graph/test_b.py": GOOD, "score/store/test_c.py": GOOD})
    assert check.faults(tmp_path) == [
        "score/graph: 2 test files, one a module: score/graph/test_a.py, score/graph/test_b.py"]


def test_a_tests_folder_is_its_parents_module(tmp_path):
    world(tmp_path, {".claude/scripts/test_a.py": GOOD, ".claude/scripts/tests/test_b.py": GOOD})
    assert check.faults(tmp_path) == [
        ".claude/scripts: 2 test files, one a module: .claude/scripts/test_a.py, .claude/scripts/tests/test_b.py"]


def test_a_file_named_for_its_module_is_a_fault(tmp_path):
    world(tmp_path, {"score/graph/graph_test.py": GOOD})
    assert check.faults(tmp_path) == [
        "score/graph/graph_test.py: named for its module, not its invariant (rename to test_<invariant>.py)"]


def test_a_docstring_without_its_break_is_a_fault(tmp_path):
    far = '"""A break in the code.\n\n' + "Some words go here. " * 20 + '\n\nIt goes red.\n"""\n'
    world(tmp_path, {"score/graph/test_a.py": '"""A sum adds up."""\n', "score/store/test_b.py": far,
                     "score/review/test_c.py": "x = 1\n",
                     "score/checks/test_d.py": '"""The break that turns it\nred: `+` -> `-`."""\n'})
    assert check.faults(tmp_path) == [
        "score/graph/test_a.py: its docstring has no line naming the break that turns it red",
        "score/review/test_c.py: its docstring has no line naming the break that turns it red",
        "score/store/test_b.py: its docstring has no line naming the break that turns it red"]


def test_each_flat_folder_tool_is_its_own_module(tmp_path):
    doc = '"""{}\n\nBreaks (each applied once, seen red, reverted): `+` -> `-`.\n"""\n'
    world(tmp_path, {"tools/cloud/pool.py": "", "tools/cloud/batch.py": "", "tools/cloud/spread.py": "",
                     "tools/cloud/test_pool_books.py": doc.format("Invariant of pool.py: every card booked."),
                     "tools/cloud/test_batch_pays.py": doc.format("The pool's cards, as batch.py rents them."),
                     "tools/cloud/test_spread_runs.py": doc.format("Invariant of tools/cloud/spread.py."),
                     "tools/cloud/test_pool_deletes.py": doc.format("The cards pool.py deletes."),
                     "tools/cloud/test_nothing.py": doc.format("A machine is deleted.")})
    assert check.faults(tmp_path) == [
        "tools/cloud/pool: 2 test files, one a module: tools/cloud/test_pool_books.py, tools/cloud/test_pool_deletes.py",
        "tools/cloud/test_nothing.py: its docstring names none of tools/cloud's tool scripts"]


def test_allowlisted_vendored_and_ignored_files_are_left_out_and_new_ones_counted(tmp_path):
    world(tmp_path, {"tools/usd/a_test.py": "", "tools/usd/b_test.py": "", "vendor/tool/x_test.py": "",
                     "data/out/test_a.py": "", "score/graph/test_a.py": GOOD}, ignore="data/\n")
    (tmp_path / "score/graph/test_new.py").write_text(GOOD)
    assert check.faults(tmp_path) == [
        "score/graph: 2 test files, one a module: score/graph/test_a.py, score/graph/test_new.py"]


def test_named_files_check_only_their_own_modules(tmp_path):
    world(tmp_path, {"score/graph/test_a.py": GOOD, "score/graph/test_b.py": GOOD, "score/store/store_test.py": GOOD})
    assert check.faults(tmp_path, ["score/store/store_test.py"]) == [
        "score/store/store_test.py: named for its module, not its invariant (rename to test_<invariant>.py)"]
