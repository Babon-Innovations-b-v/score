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
- **Every door and window in an opening, every item placed** (#72, owner 2026-10-29: "this is still not good"): a
  door the plan's openings do not hold gets one cut for it (`cut_in`, cut by the earth seed's and the scene record's
  walls); a wall row the plan writer left unplaced where the plan draws no wall stands past the plan's edge
  (`at_edge`); a stair row at the plan's stair, a railing along its sides; things the concept shows on several holders
  of one kind on the nearest (`seen_holders`). The assembly's `held` gate fails on any that comes back. A door that
  moves on a built model's face (its kind's motion rule, served) names the `recess` its holder model's bake cuts
  behind it (`recess_of`: as deep as its swing sweeps and widened on its hinge side by its thickness, or its thickness deep with its width and thickness of slide room); several on one item each get a spot their width, room and OPENING_ROOM apart (`spots`, `face_spots`: street's three restaurant doors, #36), the scene record laying each there; a static one sits flush.
- **The assembly lays by it** at built sizes (`score/stages/assembly/fitting.py`), and the plan page shows what it laid
  (`dashboard/state/local.laid_on_plan`). A relation it cannot state is `unheld` with why, never guessed.
- Test: `test_each_plan_item_names_what_holds_it.py`.
