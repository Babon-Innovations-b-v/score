# score/review/holders/

What holds each plan item (issue #72; bible `architecture/layers`, assembly: "plan and assembly need to be aligned to
each other", owner 2026-10-29). `__init__.py`'s docstring has the relations (top, within, face, in, wall, floor,
ceiling) and how each is read.

- **Derived free, never asked.** From the kept plan, the scene inventory's anchors and the concept's SAM boxes: no
  model call, no machine. Same plan and inventory in, same file out.
- **A file of its own.** `{home}/design/relations/<place>.json`, written by `keep` from the sync pass's plans pass
  (`plans_pass.main`, after the plans are kept), read by the scene record (`scene_record/writer.relations_input`).
  Never in `design/plans/`: the kept plan keys props-inputs (the paid close-ups) and the surface library (the bake).
  It names the kept plan's sha; the scene record lays by it only while the plan is that one.
- **In no stage's code key.** Only `plans_pass` imports this package; never import it from `plans.py`,
  `plan_writing.py`, `plan_fixes.py`, `plan_checks.py` or a stage (an edit there re-keys paid rows,
  `python -m score moved`). The scene record reads the file, not this code.
- **The assembly lays by it** at built sizes (`score/stages/assembly/fitting.py`), and the plan page shows what it laid
  (`dashboard/state/local.laid_on_plan`). A relation it cannot state is `unheld` with why, never guessed.
- Test: `test_each_plan_item_names_what_holds_it.py`.
