# tools/test_rule/

The guard on the test rule (`docs/bible.md` `workflow/module-standard`; owner, 2026-10-26: the one-test-file-a-module
rule had drifted). `check.py` is the way in; `make tests` runs it first and fails on any fault.

- **What it refuses**: a module with more than one test file, a test file not named `test_<invariant>.py`, a test file
  whose docstring names no break that turns it red. Its docstring gives the exact reading (what a module is, the flat
  tool folders, the break line).
- **One test function a file** (owner, 2026-11-01): a second `test_*` function is a fault unless the docstring has a
  line `second test: <why>`. `FUNCTION_DEBT` holds the files over it that day with their count: a debt file may not
  grow, lowers its entry when it shrinks and loses it at one. Merge checks into one test; never add an entry.
- **Script-style checks count** (2026-11-07): each `CHECKS` entry and `def check_*` is a test function, a `second
  test:` note covers at most the count the file has on origin/main, a file pytest finds no test in (its checks only
  under `__main__`) is a fault unless on `MAIN_ONLY`, and a SyntaxWarning is a fault.
- **The allowlist is dated and only shrinks.** It holds the modules other agents' sweeps were still reworking on
  2026-10-26, each with the (test files, test functions) it covered on 2026-11-07; a pattern may not grow, lowers its
  entry when it shrinks, and a sweep removes its own entries when it lands. Never add a module to dodge a fault.
- **A run that printed skipped did not run** (`check.py --ran`, asked by `make tests`): it fails unless `MAY_SKIP`
  names the file with the reason. `make tests` runs the guard over the whole tree, TESTS given or not.
- **A flat tool folder** (`FLAT_TOOL_FOLDERS`: tools/cloud, tools/props, tools/review, tools/usd) counts each top-level
  tool script as a module, and a top-level test file belongs to the script its docstring names first: name the driven
  script first.
