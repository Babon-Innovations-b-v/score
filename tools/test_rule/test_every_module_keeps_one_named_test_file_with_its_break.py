"""The test rule's guard (tools/test_rule/check.py) finds every way a repository breaks the rule and nothing else: one
test file a module, named test_<invariant>.py, its docstring naming the break that turns it red, and one test function
a file (owner, 2026-11-01), a script's checks counted, a note never growing a file, pytest finding every file's test,
no SyntaxWarning, the allowlist only shrinking and a run that printed skipped not passing (2026-11-07). ONE TEST,
parametrized: each case builds a small git repository in a temp folder and lists by hand the faults the rule says it
has; nothing reads this repository.

Breaks (each applied once, seen red, reverted), in tools/test_rule/check.py:
- one file a module: faults' `if len(files) > 1:` -> `if len(files) > 2:` (two files in one module pass).
- a tests/ folder is its parent's: module_of's `if folder.name == "tests":` -> `if False:`.
- named for its invariant: file_faults' `if not path.name.startswith("test_"):` -> `if False:`.
- the break line: file_faults' `elif not BREAK_LINE.search(...)` -> `elif False:`; and BREAK_LINE's `.{0,200}?` ->
  `.*?` (a "break" and a "red" pages apart pass).
- flat tool folders: module_of's `if str(path.parent) in FLAT_TOOL_FOLDERS:` -> `if False:`.
- a tool named as a script before a bare name: named_tool's patterns tried bare name first (`r"\\b(\\w+)\\b"` moved to
  the front).
- the allowlist: faults' `if allowlisted(path, allowlist):` -> `if False:`; allowlist_faults' `if not covered:`,
  `elif count[0] > owed[0] or ...:` and `elif count != tuple(owed):` each -> `if False:`/`elif False:`.
- vendor/ and ignored files left out, new files counted: is_test_file's vendor clause dropped; test_files'
  `"--exclude-standard"` dropped; test_files' `"--others"` dropped.
- only the named modules: faults' `if wanted and not wanted & ...:` -> `if False:`.
- one function a file: count_faults' `if count > 1 and not SECOND_TEST...` -> `if False:`; test_count's `Test*` class
  branch dropped; SECOND_TEST's `second test:` -> `xsecond test:`.
- the function debt only shrinks: count_faults' `if count > owed:`, `if count <= 1:` and `if count < owed:` each ->
  `if False:`; faults' stale-entry list dropped.
- a script's checks count: script_checks returns `set()`; its `check_` -> `xcheck_`; its `CHECKS` -> `XCHECKS`.
- a note never grows a file: count_faults' `if count > before:` -> `if False:`; base_count's `{base}:` -> `HEAD:`.
- pytest finds every file's test: main_faults' `if only and str(path) not in main_only:` -> `if False:`; its
  `if not only and ...` -> `if False:`; runs_only_under_main's `if tree is None or pytest_tests(tree):` ->
  `if tree is None:`; stale_faults' MAIN_ONLY pair dropped.
- no SyntaxWarning: file_faults' warning list -> `[]`.
- no stacked fold: walked_tests' `if len(found) > 1 and any(...)` -> `if False:` (a loop over old tests passes);
  its parametrize branch's `return listed_names(literal) & asserting ...` -> `return set()`; asserting_functions'
  `isinstance(inner, ast.Assert)` -> `False`.
- modules from the tree (#121): owed_faults' first list -> `[]` (a module or group with no test passes); its
  `owed & tested` -> `set()`; its `owed - present - tested` -> `set()`; tree_modules' empty-__init__ clause dropped
  (an empty package is a module); code_module's conftest clause dropped; code_module's flat-folder line ->
  `return path.parent` (tools/cloud's tools are one module); module_groups' `count > 1` -> `count > 0`.
- UNTESTED and UNGROUPED only shrink: owed_faults' first list -> `[]` (an entry not on origin/main's list passes);
  base_lists' `{base}:` -> `HEAD:`.
- a run that printed skipped fails: ran_faults' `skipped = any(...)` -> `skipped = False`; ONLY_SKIPS' ` skipped\\b`
  -> ` xskipped\\b`; the MAY_SKIP `fnmatch` -> `False`.
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
TWO = GOOD.replace("A sum adds up.", "A sum adds up.\n\nsecond test: two ports, one each") + (
    "def test_a():\n    pass\n")
SCRIPT = GOOD + ("def check_a():\n    pass\n\n\ndef check_c():\n    pass\n\n\ndef b():\n    pass\n\n\nCHECKS = (check_a, b, lambda: None)\n\n\n"
                 "if __name__ == \"__main__\":\n    print([check() for check in CHECKS])\n")
MAIN = "\n\nif __name__ == \"__main__\":\n    test_a()\n"
ESCAPE = GOOD + "PATTERN = \"\\d+\"\n"
CHECKED = "def a():\n    assert 1\n\n\ndef b():\n    assert 2\n\n\n"
STACKED = GOOD + CHECKED + "OLD = (a, b)\n\n\ndef test_all():\n    for name, check in enumerate(OLD):\n        check()\n"
PARAMETRIZED = GOOD + "import pytest\n\n\n" + CHECKED + (
    "@pytest.mark.parametrize(\"check\", [pytest.param(a), pytest.param(b)])\ndef test_all(check):\n    check()\n")
HELPERS = GOOD + CHECKED + "def test_all():\n    for value in (a, b, 3):\n        print(value)\n"
SKIPPED = {"score/graph/test_a.py": "skipped: no Newton env built\n",
           "score/stages/sim_body/inside/fit/test_b.py": "skipped: no Newton env built\n",
           "score/store/test_c.py": "sss\n3 skipped in 0.12s\n", "score/checks/test_d.py": "..s\n2 passed, 1 skipped in 0.1s\n",
           "score/review/test_e.py": "ok\n"}

# id: (files, untracked new files, .gitignore, named files, function debt, the faults the rule says it has, and
# optionally {"base": files committed as origin/main, "allowlist": ..., "main_only": ..., "ran": {file: its output},
# "tree": (UNTESTED, UNGROUPED), which adds the tree's faults})
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
        ["score/graph: 2 test files, one a module: score/graph/test_a.py, score/graph/test_new.py"],
        {"allowlist": {"tools/usd/*": (2, 0)}}),
    "named files check only their own modules": (
        {"score/graph/test_a.py": GOOD, "score/graph/test_b.py": GOOD, "score/store/store_test.py": GOOD}, {}, "",
        ("score/store/store_test.py",), {},
        ["score/store/store_test.py: named for its module, not its invariant (rename to test_<invariant>.py)"]),
    "three functions, a class's method among them": (
        {"score/graph/test_a.py": THREE}, {}, "", (), {},
        ["score/graph/test_a.py: 3 test functions, one a file (merge them into one test of the answer that matters)"]),
    "a second test: line excuses the second function origin/main has": (
        {"score/graph/test_a.py": EXCUSED}, {}, "", (), {}, [], {"base": {"score/graph/test_a.py": EXCUSED}}),
    "a second test: line grows no file, on origin/main or new": (
        {"score/graph/test_a.py": EXCUSED, "score/store/test_b.py": EXCUSED}, {}, "", (), {},
        ["score/graph/test_a.py: 2 test functions, its `second test:` note covers the 1 it has on origin/main"
         " (a note never grows a file)",
         "score/store/test_b.py: 2 test functions, its `second test:` note covers the 1 it has on origin/main"
         " (a note never grows a file)"], {"base": {"score/graph/test_a.py": TWO}}),
    "a script's CHECKS and check_ functions count, and pytest must find its test": (
        {"score/graph/test_a.py": SCRIPT, "score/store/test_b.py": ONE + MAIN}, {}, "", (), {},
        ["score/graph/test_a.py: 4 test functions, one a file (merge them into one test of the answer that matters)",
         "score/graph/test_a.py: its tests run only under __main__, pytest finds none (make them one test_ function)"]),
    "a MAIN_ONLY file at its debt passes; an entry pytest now finds, or gone, must go": (
        {"score/graph/test_a.py": SCRIPT, "score/store/test_b.py": ONE}, {}, "", (), {"score/graph/test_a.py": 4}, [
            "score/store/test_b.py: pytest finds its test now, delete its MAIN_ONLY entry",
            "score/review/test_gone.py: on MAIN_ONLY but not in the tree, delete its entry"],
        {"main_only": ("score/graph/test_a.py", "score/store/test_b.py", "score/review/test_gone.py")}),
    "a SyntaxWarning is a fault, seen again on every run": (
        {"score/graph/test_a.py": ESCAPE}, {}, "", (), {},
        ["score/graph/test_a.py: raises a SyntaxWarning on line 5 (python3 -m py_compile shows it)"]),
    "the allowlist only shrinks": (
        {"tools/usd/test_a.py": THREE, "tools/usd/test_b.py": ONE, "score/stages/settling/test_c.py": ONE,
         "score/stages/physics/test_d.py": ONE}, {}, "", (), {},
        ["ALLOWLIST score/stages/closeup/*: covers no test file, delete its entry",
         "ALLOWLIST score/stages/physics/*: covers 1 test files, 1 test functions, its entry allows 1, 0"
         " (an allowlisted module may not grow)",
         "ALLOWLIST score/stages/settling/*: covers 1 test files, 1 test functions now, lower its entry from (2, 5)"
         " to (1, 1)",
         "ALLOWLIST tools/usd/*: covers 2 test files, 4 test functions, its entry allows 1, 9"
         " (an allowlisted module may not grow)"],
        {"allowlist": {"tools/usd/*": (1, 9), "score/stages/settling/*": (2, 5), "score/stages/physics/*": (1, 0),
                       "score/stages/closeup/*": (1, 1)}}),
    "a run that printed skipped did not run, unless MAY_SKIP names it": (
        {"score/graph/test_a.py": ONE}, {}, "", (), {},
        ["score/graph/test_a.py: printed skipped, so it did not run (run it where it can, or name it in MAY_SKIP"
         " with the reason)",
         "score/store/test_c.py: printed skipped, so it did not run (run it where it can, or name it in MAY_SKIP"
         " with the reason)"], {"ran": SKIPPED}),
    "old tests called from a list or a parametrize are stacked; helpers in a list are not": (
        {"score/graph/test_a.py": STACKED, "score/store/test_b.py": PARAMETRIZED, "score/review/test_c.py": HELPERS},
        {}, "", (), {},
        ["score/graph/test_a.py: stacks 2 old tests called from a list (a, b): fold their checks into rows of one table",
         "score/store/test_b.py: stacks 2 old tests called from a list (a, b): fold their checks into rows of one"
         " table"]),
    "every module and group of the tree has its test, or is on its list till it does": (
        {"score/graph/__init__.py": "X = 1\n", "score/graph/test_a.py": ONE, "score/store/__init__.py": "X = 1\n",
         "score/review/web.py": "", "score/review/test_c.py": ONE, "score/empty/__init__.py": "\n",
         "conftest.py": "", "tools/cloud/pool.py": "", "tools/cloud/batch.py": "",
         "tools/cloud/test_pool_books.py": TOOL.format("Invariant of pool.py.") + "def test_a():\n    pass\n",
         "tools/props/one.py": ""}, {}, "", (), {},
        ["score/store: a module with no test (write its test_<invariant>.py there)",
         "tools/cloud/batch: a module with no test (write its test_<invariant>.py there)",
         "score: a module group with no test (write its test_<invariant>.py there)",
         "tools: a module group with no test (write its test_<invariant>.py there)",
         "score/review: on UNTESTED but has its test now, delete its entry",
         "score/gone: on UNTESTED but no module of the tree, delete its entry"],
        {"tree": (("score/review", "score/gone", "tools/props/one"), ("tools/cloud",))}),
    "an UNTESTED or UNGROUPED entry not on origin/main's list is a fault: they only shrink": (
        {"score/store/__init__.py": "X = 1\n", "tools/cloud/pool.py": "", "tools/cloud/batch.py": ""}, {}, "", (), {},
        ["tools/cloud/batch: on UNTESTED but not on origin/main's, the list only shrinks (write its"
         " test_<invariant>.py)",
         "tools: on UNGROUPED but not on origin/main's, the list only shrinks (write its test_<invariant>.py)"],
        {"base": {"tools/test_rule/check.py": 'UNTESTED = ("score/store", "tools/cloud/pool")\n'
                                              'UNGROUPED = ("tools/cloud",)\n'},
         "tree": (("score/store", "tools/cloud/pool", "tools/cloud/batch"), ("tools/cloud", "tools"))}),
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


def world(root, files, new, ignore, base):
    """A git repository at `root` holding `files` (path: text) in its index and `new` beside them, untracked, its
    origin/main a commit of `base` (none when `base` is empty)."""
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    if base:
        for name, text in base.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text)
        git = ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(git + ["add", "-A"], check=True)
        subprocess.run(git + ["commit", "-q", "-m", "base"], check=True)
        subprocess.run(git + ["update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
        subprocess.run(git + ["checkout", "-q", "--orphan", "work"], check=True)
        subprocess.run(git + ["rm", "-q", "-r", "--cached", "."], check=True)
        for name in base:
            (root / name).unlink()
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
    files, new, ignore, named, debt, expected, *extra = CASES[case]
    extra = extra[0] if extra else {}
    root = world(tmp_path, files, new, ignore, extra.get("base", {}))
    found = check.faults(root, named, debt, extra.get("allowlist", {}), extra.get("main_only", ()))
    if "tree" in extra:
        found += check.tree_faults(root, *extra["tree"], extra.get("allowlist", {}))
    for path, output in sorted(extra.get("ran", {}).items()):
        found += check.ran_faults(path, output, {"score/stages/sim_body/inside/*": "needs a GPU"})
    assert found == sorted(expected)
