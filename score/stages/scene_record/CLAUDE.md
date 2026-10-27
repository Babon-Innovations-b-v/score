# score/stages/scene_record/

The scene-record stage (experimental, PRD #6): a place's scene record made by SCORE from its design alone (the owner,
2026-10-21: every stage builds from the creator's design; nothing old is read). `__init__.py`'s docstring has the rows;
`plan.py`, `writer.py` and `gates.py` theirs.

- **The design is the only input**: the place's kept plan (`{home}/design/plans/<place>.json`: his edit, else the
  written plan, in plan_writing's schema: outline, walls, openings, levels, stairs, roofs, items with their shapes and
  rows, person spots, holds), the plan row's plan.json (the same plan in the place's frame, its `doorways` and
  `standing`), its scene inventory (row kinds: which rows glow), the library's lamp (`data/library/lamps.json`) and
  its sky inputs (`{home}/design/sky/<place>.json`, scene_sky.keep's: the environment concept's physics, its site and
  scene time). No kit, game file, filed definition (`sky.json`, `base.json`: retired), old record or made ground is
  read; a missing design file is a named missing input, never a crash.
- **The shell is the plan's**, built by `earth_seed/design_shell.pieces` (each level's deck, the outline's walls with
  every opening cut, the roofs, BACKING behind the plan's inside line) and stood in the place's frame as the builders'
  `slab`, `gable` and `dome` entries (`tools/usd/builders.py`, plain numbers, `plain: shell`). It is the record's for an
  inside place (walls or roofs drawn, no terrain spots) whose base does not lay it already (`design_shell.laid_for`: a
  room whose plan says its kit holds its walls, laid by earth-seed); an open place has none. Every stair or ramp the
  plan draws is a flight of `stairs`; the walls cut each opening a door or window row of the hand-in fills at its
  plan item (`design_shell.cut_for`); each plan item of an arched structure row of the hand-in
  (`design_shell.arched`: a tube's ribs) an `arch` at the row's size, painted as a wall, named its row. Each entry's surface is the scene's surface library's for its kind
  (surface-library@<place>, an `after`; `design_shell.PART_KINDS`, as earth-seed paints), else none and its
  `surface_missing` says why; tools/usd/scene.py names that on the mesh and binds nothing (no fixed surface name).
- **Objects from the plan's items** (2026-10-25: the record laid none, so no designed place's model was placed): one
  at each plan item of each prop or shell row of the batch's hand-in (`{home}/design/props/<place>.json`, prepare's
  handin.py: each row's route and the take that makes its model), `<row>_<n>`, on its spot at its shape's base,
  turned along its item; an item counting several, or a run the plan draws once, lays that many pieces along its
  path (a polygon's outline, else its box's long line). A row on the ground the plan lays only against its edge
  (`shapes_first/floor_fit.past_edge`: a building round a square, its face the item) stands with its face on that
  edge's line, its body out past it off the floor, facing in (`writer.past_edge_spot`; at a corner the edge its item
  runs furthest along; 2026-10-26: the square's 30 m buildings on 2 to 7 m strips). Each waits on its take's bake model (`bake`, `<first row>_1`)
  and the assembly lays it under /<place>/Objects once baked (`assembly/made_waiting.py`); a row with no take or no
  size stays named on the root's score:waiting. People are the cast's; a row the plan's shell lays itself (route
  `plan`) is named on a shell piece of its part (`row`).
- **Far objects** (`far.py`; the owner, 2026-10-26: the skyline is the environment's own scenes where its plan puts
  them, and ordinary objects for anything that is no scene): each prop row of the hand-in marked `far` (prepare's
  groups.far_made) stands where its concept box is seen, along its bearing off the plan fixes' projection (up the
  picture is away), at the distance its read tall rises to its box's height in the framework's view (VIEW_FOV), its
  `far` pieces square to that bearing, waiting on its take's model like every object; one with no projection or box
  is named in `far_unplaced`, never placed by guess.
- **Lamps from the row kinds and the concept**: a light at each plan item of a glowing row (its row kind, or its
  concept showing it glow: `{home}/design/light/<place>.json`, the reading's concept light, its colour and brightness
  there; a row of the sky is the physics', no lamp), over its middle, as high on it as the library's lamp for the
  row's mount says, numbered by that lamp. No lamp list per place.
- **The sky is the physics'**: the record's environment says inside or not and what overhead.py sees at the site at
  the scene time (lights over the horizon, bodies, backdrops); the light layer draws it (`score/stages/light/sky.py`).
  The record holds no air, haze or glow the design does not give.
- **Views** from inside each doorway and from each person spot; an inside place's view whose eye stands outside its
  outline is left out with why (`views_left_out`), never written to see the walls from behind.
- **Places** are the design's: each place a door or opening leads to that its holder's plan holds beside it, stood
  where the holder holds it, and each place of its scene a backdrop row of its hand-in is `shown` from
  (prepare's groups.shown_from: the holder at its own plan's corner, a place it holds beside where it holds it).
  A top place has none (its children are its scene tree's).
- **Gates**: `game-free` (no game file or name: a date of the year 2099 is a scene time, not the game), `plan-matched`
  (every wall of the outline in the shell, every opening cut through it, every stair laid, every lamp over its
  item), `openings` (each doorway leads to a place of the design, outside, sealed, a row of the inventory or into its
  holder; a door to a neighbour has it stood; every view of an inside place inside its outline). Whether the made
  ground fits round the doorways is ground-fit's.
- Run the proof with `python -m score run world1 --place <place> --stage scene-record --detach`; the test is
  `test_a_scene_record_is_written_from_its_design.py` (a shed of its own: its plan maps, its record is written from a written plan, and a filled
  door, a moved lamp and a door to no place fail by name; its shell and stairs take the scene library's surfaces, or
  name why not).
