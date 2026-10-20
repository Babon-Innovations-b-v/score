# score/stages/earth_seed/

The earth seed rows (#27): each kit-laid earth place's base stage made again from the repository and the rows' own
outputs, in place of the round-three `usd-r3/<place>` folder the old disk took (2026-10-19). `__init__.py`'s docstring
has the rows, the output and the gates.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json`. The kit's code pieces are baked with the material library (make_kit), the
  generated pieces come from the place's surface line; nothing else is laid.
- **Every model from a row.** `earth-kit@<place>` (paid, one shot: late-plan's make_kit jobs once on one card class,
  no retry) makes the kit's code-built models; a generated piece's model is its place's `surfaces-bake` (or the bake
  of the place that paints it, read beside). A piece whose model no row made is left out and named (`laid` fails by
  name), never stood in for.
- **Readers are rewired in the table, not here.** `stages.earth_seeded` turns every declared `{seeds}/usd-r3/<place>`
  of a kit-laid earth place into a read of `earth-seed` (the place's own as an `after`, another's beside) and hands
  the make, judges and gatherers the seed folder under its old name; `stages.EARTH_SEEDED` lists the rows and
  `earth_seed_test.py` holds it to the declared files; no row reads the round-three seed (`terrain-look`, the last,
  was retired on 2026-10-20, #27).
- **Priced warm** (`tools/costs/per_unit.py` `earth-kit`): a make_kit job at the library jobs' measured warm seconds
  on L4; its units are forecast free from the installed kit (`kit_jobs`). `earth-seed` is free.
- Test: `earth_seed_test.py` (no spend).
