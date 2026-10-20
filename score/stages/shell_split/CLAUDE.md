# score/stages/shell_split/

The shell-split row (CONTEXT.md "shell split", issue #16): an outside shell's plan split into the shapes of its inside
places, one free, local place node per shell, deterministic. `__init__.py`'s docstring has the input (a plan's
`split`) and the output; `_split.py`'s the cutting rules; `_gates.py`'s the gates (`tiled`, `reached`, `bounded`).
Bible: `architecture/lifecycles` (shapes first).

- **Generic, never one shell's.** A place is a shell when its plan has a `split`; nothing here names a ship, a hull
  or environment 1. A shell's own measures (its outline) are numbers in its plan, measured by whoever writes the plan
  (its rough model, when that stage stands): no shell's reader is imported here.
- **The route's order is in the table.** shell-split reads the shell's `plan`; every inside place's `plan` reads its
  shell's split beside it (`PLAN` in `score/stages/__init__.py`: `beside`, `neighbours=shell_of`, `nested`). A nested
  read goes up to the shell, never back down, so the table's loop check leaves it out (`graph.Stage.nested`);
  `shell_of` refuses a place that holds itself. A place named by two shells' splits is refused too.
- **Writes the store, never the hand data.** Each inside place's definition is `places/<place>.json` in the output;
  turning it into the inside place's plan is the plan row's next step, not a hand edit.
- **A rule, never a tuned number.** Where the split differs from a hand-made plan, the difference is stated (the ship
  test's `DIFFERS`), not cut away by bending a rule to match it.
- **Limits today:** one spine (one run of side rooms) per shell; one deck (no stepped floors); doors only inside the
  shell (a way out through the shell's wall is the inside place's plan's).
- Test: `PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/shell_split/shell_split_test.py` (seconds).
