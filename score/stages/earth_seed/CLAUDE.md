# score/stages/earth_seed/

The earth seed rows (#27): each place's base stage made again from the repository, its design and the rows' own
outputs, in place of the round-three folders (`usd-r3/<place>`, the ship's `usd-ship/<place>`) the old disk took
(2026-10-19). `__init__.py`'s docstring has the rows, the output and the gates.

- **Every designed scene's base is its own design's** (the owner, 2026-10-21). The rows run for every place with a
  kit laid or a locked plan (`{home}/design/plans`) and a style (`styled`), the ship's rooms and a scene added in the
  app too (`stages.earth_place`); a top scene place.json does not name (the base's outside) has no base row, its seed
  a named lost input, until it has a style. A kit is the base's only when no design is locked for the place (`kit_is_base`; a kit laid by a
  per-place script from a filed plan is the old concept's room, whatever its size); then earth-kit bakes it as before
  (`stages.kit_based`).
  Otherwise the base lays no kit piece: `kit.json` in the output says why, the inventory is the design's, the style
  the place's own place.json entry (`known_as`) else the scene holding it (`style_of`, its holders' plans declared),
  and an inside room whose kit holds its walls (shell `kit`, `inside`) is laid from the locked plan (`design_shell.py`:
  deck, walls with their openings cut, roof, BACKING behind the plan's line as the scene record's backing shell,
  painted with its library surface, `score:plain shell`). A domed or outdoor shell is the scene record's; an open
  place (the street, the square) gets none. No special case by place name.
- **The surface data is the design's** (`surface_data.pattern`, its design's where designed, the one the finish route
  paints): earth-seed and kit-sections declare it, and earth-seed claims models from its `elsewhere`
  (`earth_seed.claiming_places`). The old scene record (`data/scene`) is declared only by a base that lays its kit
  (`kit_is_base`: no design locked), whose export still lays it; a design base never reads it.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json`. The kit's code pieces are baked with the material library (make_kit), the
  generated pieces come from the place's surface line; nothing else is laid.
- **Every model from a row.** `earth-kit@<place>` (paid, one shot: late-plan's make_kit jobs once on one card class,
  no retry) makes the kit's code-built models; a generated piece's model is its place's `surfaces-bake` (or the bake
  of the place that paints it, read beside). A piece whose model no row made is left out and named (`laid` fails by
  name), never stood in for.
- **The kit is a layer on the shared loop** (#41, `shapes_first.KIT`, layer `kit`). A kit row goes to the loop by its
  entry in the place's hand-in record (`data/props/<place>.json`, `"layer": "kit"`, and its take in the place's
  surface data, `bake.models` naming the kit's model names, so earth-seed lays the loop's bake under them). Every kit
  row not handed is named in earth-kit's `fallbacks.json` with its route (`code`, which earth-kit bakes, or `stored
  take`, a picture-made model of the old prop route earth-seed laid from `data/parts`, retired 2026-10-21) and why (`NOT_HANDED`); both
  sides read the hand-in record through the loop's own reader (`prop_data`, `closeup_row.layer_of`). A handed row is the loop's
  alone, and a model the loop makes none of is a gap (the batch rule), never a code bake here. earth-kit cannot read
  the loop's ends: `likeness` reads `surfaces-check`, which reads `scene-record` beside, which reads earth-seed.
  `earth_seed_test.py` fails on a kit row, code or stored take, that is neither handed nor named with a why. No kit row is handed yet, for the
  two core gaps `NOT_HANDED` names: the bake lays a kit take only at its turn into the kit frame
  (`data/library/details.json` `turn`), which no loop row measures, and a handed row the loop makes no model for
  fails `likeness` and stops the place's line instead of leaving a gap. Handing a row in before both close stops
  that place's line.
- **Shell sections** (CONTEXT.md "shell section"): a plan's `sections` (`data/plans/<place>.json`: name, the concept
  element it was read from; surface; rows) are laid by the kit adapter's after-step `kit-sections@<place>` (free,
  `kit_sections.py`, after the loop's ends, the place's earth seed and earth-kit; only an Earth kit place whose plan
  marks sections): one style (the section's rows, each a
  pipeline-made variant, else earth-kit's named fallback, else a gap row), one finish (the library surface over most
  of its loop-made rows' parts, each row weighted by its pieces in the section) and one wear seed a
  section, each object's place in the section (`wear_at`, metres from the section's least corner in the base stage) so
  its wear runs across the seams, written as overs on the base's objects in `layers/sections.usda`, which the
  assembly takes (`assembly.LAYERS`; `score:section`, `score:finish`, `score:wear_seed`, `score:wear_at`). Drawing the
  section's finish and wear from those attributes in the shaders is not built yet.
  The sections of 2026-10-20 were read from each plan's concept read (`elements`): an element naming the inventory's
  shell rows (group `kit: wall|floor|ceiling`, repeating across the room, plain plates and trims or wall bands) is a
  section, a row taking its first element.
- **Readers are rewired in the table, not here.** `stages.earth_seeded` turns every declared `{seeds}/usd-r3/<place>`
  of a kit-laid earth place into a read of `earth-seed` (the place's own as an `after`, another's beside) and hands
  the make, judges and gatherers the seed folder under its old name; `stages.EARTH_SEEDED` lists the rows and
  `earth_seed_test.py` holds it to the declared files; no row reads the round-three seed (`terrain-look`, the last,
  was retired on 2026-10-20, #27).
- **Priced warm** (`tools/costs/per_unit.py` `earth-kit`): a make_kit job at the library jobs' measured warm seconds
  on L4; its units are forecast free from the installed kit (`kit_jobs`). `earth-seed` is free.
- Test: `earth_seed_test.py` (no spend; kit-sections' tests too).
