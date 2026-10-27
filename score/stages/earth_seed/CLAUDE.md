# score/stages/earth_seed/

The earth seed row (#27): each designed scene's base stage made from its design and the rows' own outputs, in place of
the round-three folders (`usd-r3/<place>`, the ship's `usd-ship/<place>`) the old disk took (2026-10-19), and of the
old kits (data/kit) retired with the old concepts on 2026-10-21. `__init__.py`'s docstring has the row, the output and
the gates.

- **Every designed scene's base is its own design's** (the owner, 2026-10-21: "remove all old, all old stuff is
  retired"; every stage builds from the creator's design only). The row runs for every place with a locked plan
  (`{home}/design/plans`) and a style (`styled`): the Earth's and the ship's rooms, a scene added in the app, a top
  scene place.json does not name (the Base: the environment concept's style, its library entries its own name's,
  `style_of`); a part of another scene's outside (the launch) has none (`stages.earth_place`). It lays no kit piece:
  `kit.json` in the output is the design's kit (no piece, its style, the shell parts laid, the plan's box in the
  place's frame, `footprint`, and `room` where the plan writes no ground of its own), which every reader of an old kit
  reads.
- **Each shell is laid once, from the plan** (`design_shell.py`, one set of pieces for both layers): the earth seed
  lays a room whose kit holds its walls (shell `kit` and inside, or, its inside not said, one that writes walls:
  `laid_for`) as deck, walls with every opening cut and roof (a dome a sphere's cap, another rising roof a closed gable), BACKING behind the plan's
  line, and an open place's raised levels (a plan that encloses nothing, `encloses`: a deck up to a storey solid from
  the ground, a balcony a slab); the scene record lays every other enclosed place's shell from the same pieces and
  every stair and ramp (scene_record.writer), and each arched structure row's band at its plan items
  (`arched`, `arches`: a rib, arch or hoop, thin across; owner, 2026-10-26: the framework may build structure pieces
  as the earth seed builds shells). Each wall cuts the plan's openings and those its door and window rows fill at
  their plan items (`cut_for`, `row_openings`: the earth seed's from the design inventory, the scene record's from
  the hand-in; the library holds no door or window, so their models come by the prop route). No special case by
  place name.
- **Which parts a shell lays is named without building it** (`score/stages/shell_parts.py`: `laid_for`, `encloses`,
  `parts`, held equal to the pieces by the test). A row that only asks which parts there are (the scene library's
  `shell_kinds`, the surface tiles) reads that, never `design_shell`, so a change to how a part is built keys only
  the rows that build or measure it (2026-10-27: the dome change keyed the people, sound and palette rows through
  such imports). Keep it so: check `python -m score.stages.moved` before an import of this folder elsewhere.
- **Each part's surface is the scene's own surface library's** (surface-library@<place>, its `materials.json`, read
  as an `after`; a place with no surface line reads without it): the first variant its `kinds` gives the part's kind
  (`PART_KINDS`, palette_library.SHELL_KINDS: a deck the floor's, a wall the wall's, a roof the roof's else the
  ceiling's), laid under /<place>/Library and bound; none, and the part names why (`score:surface:missing`), never
  painted another way. A prop's paint takes the same shell surfaces (palette_library.shell_surfaces). Every part is a
  static collider (kind structure, `score:plain shell`), so the collision gate holds it and the placeholder gate reads
  it as the scene's own shell.
- **The surface data is the design's** (`surface_data.pattern`, its design's where designed): earth-seed declares it
  and claims models from its `elsewhere` (`earth_seed.claiming_places`).
- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json`.
- **The kit is a layer on the shared loop** (#41, `shapes_first.KIT`, layer `kit`): a scene's shell pieces and
  fittings as inventory rows, made by the loop like any row, nothing after the model. The old kits' rows (`earth-kit`,
  its code fallbacks; `kit-sections`, the plan's shell sections) went with the old kits.
- **Readers are rewired in the table, not here.** `stages.earth_seeded` turns every declared `{seeds}/usd-r3/<place>`
  and `{data}/kit/<place>.json` of an earth place into a read of `earth-seed` (the place's own as an `after`, another's
  beside): the seed's stage folder, the design's kit (`kit_in`), under their old names; `stages.EARTH_SEEDED` lists
  the rows and `test_a_scene_s_base_stands_from_its_design.py` holds it to the declared files.
- `earth-seed` is free. Test: `test_a_scene_s_base_stands_from_its_design.py` (no spend).
