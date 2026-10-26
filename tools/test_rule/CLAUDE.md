# tools/test_rule/

The guard on the test rule (`docs/bible.md` `workflow/module-standard`; owner, 2026-10-26: the one-test-file-a-module
rule had drifted). `check.py` is the way in; `make tests` runs it first and fails on any fault.

- **What it refuses**: a module with more than one test file, a test file not named `test_<invariant>.py`, a test file
  whose docstring names no break that turns it red. Its docstring gives the exact reading (what a module is, the flat
  tool folders, the break line).
- **The allowlist is dated and only shrinks.** It holds the modules other agents' sweeps were still reworking on
  2026-10-26; a sweep removes its own entries when it lands. Never add a module to dodge a fault: fix the tests.
- **A flat tool folder** (`FLAT_TOOL_FOLDERS`: tools/cloud, tools/props, tools/review) counts each top-level tool script
  as a module, and a top-level test file belongs to the script its docstring names first: name the driven script first.
