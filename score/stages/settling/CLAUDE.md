# score/stages/settling/

The settle stage (the paper's Methods, "The canonical scene": settling and resting; experimental, PRD #6): where a
place's objects come to rest on its made ground, laid as `layers/settle.usda` (an over of each moved object's
transform), which the assembly stage puts over the seed's base. `__init__.py`'s docstring has the make and the gates;
the method is `tools/usd/settle.py` (drop_job, rest_poses), `held.py` (held_rests, fixed_let_down: snap.py kept out of
settle.py, whose readers a snap edit would otherwise move) and the drop: `tools/usd/drop.py` (simulate, drop_key: kept
out of settle.py for the same reason) runs `inside/settle_drop.py` in Newton, in the physics trial's own pinned Python
(`../physics/inside/newton_env.sh`, one Python for both), on the trial's card class or this PC's card.
settle.py's own `simulate`, `drop_key` and `DROP_CLASSES` still name the deleted Blender script: dead, left until an
edit there moves its ~90 rows anyway (2026-10-27); never call them.

- **Only `SETTLED` places have the row** (`score/stages/__init__.py`): a place joins once its settle row has passed;
  any other place's assembly lays the seed's poses. A stage reading this one reads without it where it does not apply.
- **Three steps, one method each.** Loose floor objects are dropped (physics: stood upright first, meeting what they
  are stacked on, a hollow one by its convex parts, `convex_parts.py`, written beside the dropped stage); held objects are snapped down onto their holders as they rest, onto a level spot within 30 cm when
  the straight snap leaves them leaning (a convex hull of a shelf unit spans its shelves, so they are not dropped);
  fixed objects the triage finds floating are let straight down. Nothing turns or moves past the settle's limits,
  but for one that falls into a hollow piece (owner's rule, 2026-10-26): when its one support is dropped as convex
  parts and rests, and its middle comes to rest inside that support's box, it is laid where it lands
  (`landed_in_hollows`, here: settle.py sits in about 90 rows' code), not kept as "would not rest as laid".
- **The seed's models are dropped, not the bakes**, so the row does not wait on the paint. A tip onto uneven feet is
  stood upright on its lowest foot and named for the paint, which levels a take's feet before its bake; the
  assembly's own drop and triage judge the baked model. A model whose base is one sloping or uneven piece (the
  hangar's racks: legs ending 22 cm over a part under their middle) is no tip onto uneven feet: its tilted rest stays
  the triage's fault, the model's to fix.
- **The gates block only what this stage breaks**: a broken drop (`rested`) or an object resting worse with the layer
  than without it (`resting`). What is left is named on the page; the assembly's resting gate is the final judge.
  Two loose objects inside each other are judged at the poses the layer lays (the drop's loose-to-loose collision is
  off): a pair already crossing as laid is kept as laid, "laid inside" the other, as one laid inside a static is;
  only a pair the layer brings to cross is a broken drop (settle@airlock's sandbags, 2026-10-30). One stacked on a
  loose support the layer leaves unrested is left as laid with it (`kept_with_their_supports`): its rest was found
  on the support where the drop left it (settle@airlock's sandbags_18, 52 cm down a ramp kept as laid, 2026-10-30).
- **Held on a wall or ceiling row is mounted** (`holders.holder_kind`): never snapped down; its laid pose stands.
- **Spend.** A drop is bought only when something loose is to be stood up or unstacked or the triage finds a fault on
  it (free, first); a drop already paid for is read back from `DROPS` (the same job, drop script, trial script, Python
  pins and stage). A drop is one rented card (`drop.DROP_CLASSES`, the trial's), its Python built once on it; on this
  PC's RTX 5080 the six-object toy drops in about 8 s, a 20-object one in about 17 s (2026-10-27). Bullet's on a
  processor machine was about 30 minutes for the hangar (EUR 0.59 on 2026-10-12); Newton's on a real place is not yet
  timed.
- Run the proof with `python -m score run world1 --place <place> --stage settle --detach` in the background; it reads
  only terrain. `test_the_settle_layer_lays_and_its_gate_fails_a_broken_drop.py` checks the layer and the drop gate
  without a drop.
