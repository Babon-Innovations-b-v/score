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
  (`assembly/mounted.py`'s `holder_kind`, imported inside its function). It imports prepare's `groups` (`built_rows`: a wall
  thing parted at `groups.made_size`, its hand-in size), so `groups.py` is in those keys too. Never import it from `plans.py`,
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
  behind it (`recess_of`: as deep as its swing sweeps and widened on its hinge side by its thickness, or its thickness deep with its width and thickness of slide room); several on one item each get a spot their width, room and OPENING_ROOM apart (`spots`, `face_spots`: street's three restaurant doors, #36), the scene record laying each there; a static one sits flush. A door or window cut where no plan opening is left goes on the nearest wall with room for it beside the openings already on it (`cut_in`, `has_room`; an empty nearest wall is taken as it is): street's second roller shutter and its restaurant window, cut on the 4.61 m wall its restaurant door stands in (7.5 m of openings), 2026-11-06. Different things on one face that meet at their built sizes, along it and in height, are spread along it in the order the plan draws them, OPENING_ROOM apart and inside its ends (`face_spread`; whether they meet is judged with each kept inside the face's built ends as the assembly keeps it, `kept_on_face`: hub's three monitors drawn past its console's 4.5 m end, #36; each moved one given `spots`, a moving door its recess there: street's window, stairwell entrance and shutters, #36); a face too short for them turns each thing the plan draws outside its holder's box on another side to that side (`turned_toward`: storage's three pillar pipes, drawn N, S and E of the pillar, all on its S side, 2026-11-07), and one still too short is named `crowded`, its things kept as drawn.
- **Each piece its own spot, at its built size** (2026-11-04 audit): a wall relation goes on the nearest wall long
  enough for its row's pieces at their built length (`run_needed`; a run of several round corners along the wall's
  chain, `chain_of`; one piece round a round wall's facets, its face the chord it covers), else the longest, named
  `short`; an item laying several pieces gives each its own wall relation (`pieces`, `wall_pieces`, packed their
  length and `PIECE_GAP` apart, each flat along one straight run of its walls, never bent round a corner: one not
  fitting before a corner starts past it, `flat_alongs`, and a wall chosen for several only where they fit so,
  `holds_flat`; 2026-11-06: hangar's second pipe, galley's cabinets, hub's panels laid as chords across corners), one row's items at one spot on one wall at one height packed along it where it
  holds them, else stood one over another up it, their tall and `PIECE_GAP` apart (`parted_on_wall`: garage's three
  10 m pipes at one spot, 2026-11-06), every wall thing at the size it is made at (`built_rows`: prepare's
  `groups.made_size`, the hand-in's; the stairwell's 12 m conduits made 3 m pieces, the cockpit's red pipes 6.6 m, 2026-11-07), any wall thing laid as an object (no `structure` or arched row) whose built box (`wall_box`, as the assembly lays it) still meets one laid before it on the walls, any row's, round a corner too, or a thing hung from the roof (`hung_boxes`, never moved: storage's second wall pipe stood up into its ceiling light, 2026-11-07), by more than `WALL_TOUCH` slid along its wall to the nearest clear spot, else stood the nearest clear height up or down inside its band (`wall_band`: one on the floor stays there, a high one never under `HIGH_LEAST`, its top under its wall's) (`apart_on_walls`: hangar's eight 32 m pipes at 10 m in one another, 2026-11-06); brought down under its wall's top where its plan stands it over it (one taller than its wall on the floor: the stairwell's conduits at 12 and 24 m); with no room on its own wall, moved to the nearest other place on the walls with room (`walled_clear`: another wall long enough, or a stretch of a straight run of walls, `run_chords`; habitat's 18 pipes, three on one wall; never a spot and height one of its row holds on the wall's other face, which the scene record lays at one spot: habitat's pipes 12 and 17 back to back on an inner wall stretch, 2026-11-07); a passage laid first and never moved, its stretch of wall its own (`passage`: workshop's monitors in its glass tunnel's chord); one stuck behind smaller things laid before them in a second go (`laid_apart`: the stairwell's conduits behind its lamps), 2026-11-07, one row's floor items at one spot at one height each after the first moved the shortest way clear of the others, inside the outline and onto no other floor thing, kept where there is no room (`parted_on_floor`: engineroom's railings 3 and 4 on one box, 2026-11-06), each item counting the pieces the scene record lays at it, the row's count its items fall short of one more an item from the first (`pieces_at` as `writer.pieces_of`: hangar's 8 pipes on 7 items, 2026-11-06), a row the plan places on an item of its own given no walls-item relation, which the record never lays (`items_of` as `writer.item_rows`: street's doors and shutters, 2026-11-06), a walls-item floor row's pieces where their concept boxes project; a wall thing the
  plan gives no base its mount `height` (`mount_height`: high words or a light, else a small thing at `EYE_MOUNT`); a
  wall row whose words say it spans the room under the roof (`spans`) is held by the ceiling, and a ceiling row hung
  from it (`under_roof`) is marked `to roof`; a seat its words put at, by or around a holder row (`beside_holder`)
  stands before that holder's built side, `SEAT_GAP` clear, facing it (`seats_beside`); a stair's railings share its
  sides (`rails_along`).
- **Every opening on a built wall** (`loose_openings`): a plan opening on no wall the shell builds (its outline's or an
  inner one, design_shell.on_a_wall) is listed in the file's `loose`, the plan-side check (camp's airlock door in its
  dome's gap, street's stairwell opening, 2026-10-31).
- **A placement word past `on` is kept** (`placement`, 2026-11-04): a row its reading's `where` says is under its
  holder is `within` it with `under` (the assembly lays it at the holder's foot), one on its shelves `within` it, its `why`
  starting "on the shelves of" (the assembly lays it on its holder's built boards, `fitting.on_boards`, which reads
  those words: keep them), one on its holder's side never on its top; a flat row (`lies_flat`) the plan stands at its holder's top (`stands_on_top`) on that top, never against its side (galley's stove top and sink, drawn half past their counter's edge, 2026-11-11); the assembly's held gate
  fails a relation that disagrees (`fitting.placement_faults`). One anchor for a row whose `where` names several
  holders (quarters' books on "desk, window sill, top bunk") is the reading's limit, not mended here.
- **The assembly lays by it** at built sizes (`score/stages/assembly/fitting.py`), and the plan page shows what it laid
  (`dashboard/state/local.laid_on_plan`). A relation it cannot state is `unheld` with why, never guessed.
- Test: `test_each_plan_item_names_what_holds_it.py`.
- **Nothing on the floor floats** (2026-11-06, laid-as-designed's floor part): a floor row whose words say it stands
  round a holder row (`AROUND_WORDS`: engineroom's railings "around engines") is laid round that row's items' sides,
  one a side, the least crowded first (`around_holders`, `side_crowding`), at the holder's foot; a floor row whose words
  say it hangs over the floor (`HUNG_WORDS`: square's lantern strings "above plaza") laid over half its height up is
  `hung` between the two standing things nearest its ends that reach its top (`hung_between`), the gate's
  `hung_faults` checking they stand; a floor item its plan stands over half its height up on nothing (no level,
  flight or other thing's top under its box; people hold nothing; its own row's only where it piles) gets the
  `height` of what is under it (`stood_under`: square's stage screen at its deck's 3.3 m behind it, street's and
  engineroom's things the old plan fix piled), which the scene record lays it at. The relations file keys the
  surfaces bake (`route_bake.bake_files`): a change here re-keys that place's bake.
- **Leaning and attached (#94)**: a row whose reading's `where` says "leaning against" or "attached to" (`rests`,
  LEAN_WORDS, ATTACH_WORDS) has `rests` on each of its relations, carried to the scene record's objects for the
  settle; a leaning one stands against a side (never on a top, within, or at a mount height), and one read on the
  floor leans against the nearest wall where the plan has walls.
