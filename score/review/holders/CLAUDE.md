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
- **In two stages' code keys.** `plans_pass` derives the file; two stages import this package, so any edit here
  re-keys them and every row after them (check `python -m score moved` before pushing): the scene record
  (`scene_record/writer.py`, for `outlines_room`), and so everything laid from it, and the assembly
  (`assembly/mounted.py`'s `holder_kind`, imported inside its function). Never import it from `plans.py`,
  `plan_writing.py`, `plan_fixes.py`, `plan_checks.py` or another stage. Both read the relations from the file,
  never derive them again.
- **Every door and window in an opening, every item placed** (#72, owner 2026-10-29: "this is still not good"): a
  door the plan's openings do not hold gets one cut for it (`cut_in`, cut by the earth seed's and the scene record's
  walls, kept inside its wall's ends); a window takes only a window opening, a door only a door's (camp's dome window
  stood in its door's swing, #36); each piece the scene record lays at an item its own opening (cockpit's four rear
  doors, #36); a wall row the plan writer left unplaced where the plan draws no wall stands past the plan's edge
  (`at_edge`); a stair row at the plan's stair, a railing along its sides; a ramp on the floor up to the nearest raised level's
  edge (`up_to_level`: airlock's ramp to its porch deck); a thing against a wall on the room's side even when drawn past the outline, a passage (tunnel, tube) outside (`past_outline`: hangar's back-wall pipes); things the concept shows on several holders
  of one kind on the nearest (`seen_holders`). The assembly's `held` gate fails on any that comes back. A door that
  moves on a built model's face (its kind's motion rule, served) names the `recess` its holder model's bake cuts
  behind it (`recess_of`: as deep as its swing sweeps and widened on its hinge side by its thickness, or its thickness deep with its width and thickness of slide room); several on one item each get a spot their width, room and OPENING_ROOM apart (`spots`, `face_spots`: street's three restaurant doors, #36), the scene record laying each there; a static one sits flush. Different things on one face that meet at their built sizes, along it and in height, are spread along it in the order the plan draws them, OPENING_ROOM apart and inside its ends (`face_spread`; whether they meet is judged with each kept inside the face's built ends as the assembly keeps it, `kept_on_face`: hub's three monitors drawn past its console's 4.5 m end, #36; each moved one given `spots`, a moving door its recess there: street's window, stairwell entrance and shutters, #36); a face too short for them is named `crowded`, its things kept as drawn.
- **The assembly lays by it** at built sizes (`score/stages/assembly/fitting.py`), and the plan page shows what it laid
  (`dashboard/state/local.laid_on_plan`). A relation it cannot state is `unheld` with why, never guessed.
- Test: `test_each_plan_item_names_what_holds_it.py`.
