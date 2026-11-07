# score/stages/scene_record/

The scene-record stage (experimental, PRD #6): a place's scene record made by SCORE from its design alone (the owner,
2026-10-21: every stage builds from the creator's design; nothing old is read). `__init__.py`'s docstring has the rows;
`plan.py`, `writer.py` and `gates.py` theirs.

- **The design is the only input**: the place's kept plan (`{home}/design/plans/<place>.json`: his edit, else the
  written plan, in plan_writing's schema: outline, walls, openings, levels, stairs, roofs, items with their shapes and
  rows, person spots, holds), the plan row's plan.json (the same plan in the place's frame, its `doorways` and
  `standing`), its scene inventory (row kinds: which rows glow), the library's lamp (`data/library/lamps.json`) and
  its sky inputs (`{home}/design/sky/<place>.json`, scene_sky.keep's: the environment concept's physics, its site and
  scene time). No kit, game file, filed definition (`sky.json`, `base.json`: retired) or old record is read; a missing
  design file is a named missing input, never a crash. The one made thing read is the terrain row's ground (made from
  the design alone), so an open place's view eye stands a person's height over the ground under it (2026-10-30:
  wreck's spot-3 and spot-6 eyes stood under its ground, their views black).
- **The shell is the plan's**, built by `earth_seed/design_shell.pieces` (each level's deck, its top at the floor, the outline's walls and every inner wall the plan writes, centred on its line, with
  every opening cut, each outline wall on its written wall's line, the roofs) and stood in the place's frame as the builders'
  `slab`, `gable`, `dome` and `tube_arc` (a vault) entries (`tools/usd/builders.py`, plain numbers, `plain: shell`). It is the record's for an
  inside place (walls or roofs drawn, no terrain spots) whose base does not lay it already (`design_shell.laid_for`: a
  room whose plan says its kit holds its walls, laid by earth-seed); an open place has none. Every stair or ramp the
  plan draws is a flight of `stairs`; the walls cut each opening a door or window row of the hand-in fills at its
  plan item (`design_shell.cut_for`); each plan item of an arched structure row of the hand-in
  (`design_shell.arched`: a tube's ribs) an `arch` at the row's size, painted as a wall, named its row. The shell's own structural rows of the hand-in are its pieces too (`design_shell.row_pieces`,
  `writer.row_entries`, 2026-11-05): pillars spaced round the walls, beams under the roof, a pad or grate at its plan
  item, each `<row>_<n>` named its row and left out of the rows named on deck, wall and roof pieces; a deck is cut
  open over each flight going down from it (`design_shell.hatches`), and an opening row no plan item of its own cuts
  is named by its id's words on a free piece at a cut (`writer.name_open_cuts`: a roof's opening on a roof cut round
  its openings, a floor hatch on the flight down through it, any other on the lintel over a plan opening), else on
  none, for `gates.unbuilt_rows` to fail. Each entry's surface is the scene's surface library's for its kind
  (surface-library@<place>, an `after`; `design_shell.PART_KINDS`, as earth-seed paints), else none and its
  `surface_missing` says why; tools/usd/scene.py names that on the mesh and binds nothing (no fixed surface name).
- **Objects from the plan's items** (2026-10-25: the record laid none, so no designed place's model was placed): one
  at each plan item of each prop or shell row of the batch's hand-in (`{home}/design/props/<place>.json`, prepare's
  handin.py: each row's route and the take that makes its model), `<row>_<n>`, on its spot at its shape's base,
  turned along its item; an item counting several, or a run the plan draws once, lays that many pieces along its
  path (a polygon's outline, else its box's long line); a row the plan leaves on its walls item and places on an
  item of its own too is laid at that item alone (`writer.item_rows`, 2026-11-06: camp's airlock door laid twice). A row on the ground the plan lays only against its edge
  (`shapes_first/floor_fit.past_edge`: a building round a square, its face the item) stands with its face on that
  edge's line, its body out past it off the floor, facing in (`writer.past_edge_spot`; at a corner the edge its item
  runs furthest along; 2026-10-26: the square's 30 m buildings on 2 to 7 m strips). Each waits on its take's bake model (`bake`, `<first row>_1`)
  and the assembly lays it under /<place>/Objects once baked (`assembly/made_waiting.py`); a row with no take or no
  size stays named on the root's score:waiting. People are the cast's; a row the plan's shell lays itself (route
  `plan`) is named on a shell piece of its part (`row`), an opening row on the lintel over the cut its plan item makes
  (none where no wall is cut at it). A thing at the floor whose spot lies on a deck lying on the floor (a level at most
  a slab and its gap high, so nothing stands under it: airlock's porch deck) stands on that deck's height.
- **Each object carries what holds it** (#72, `on`): the place's relations (`{home}/design/relations/<place>.json`,
  score/review/holders, read only while their `plan` sha is the kept plan's, else `relations_left_out` says why). A
  door or window in its opening stands at the opening's middle on its sill, along its wall (`in`: middle, along, wide,
  tall); a wall item at its relation's spot along its wall (`wall`: the face's ends and the way out into the room); one
  on, within or against a holder names the holder's objects (`holder`, and `out` for a face, with a moving door's recess `room` and `room_way` beside it, which the assembly keeps within the face's span). The assembly lays each by
  it at its built size (`assembly/fitting.py`); an item whose holder item lays no object keeps no `on` (`unheld`),
  and a holder the record lays as structure (a tube's arched rib) is named there (`holder scope`). A wall row past
  the plan's edge stands with its face on the edge's line, its body out past it, facing in (`edge`: a street's
  facade); a stair row at the plan's stair, a railing along its sides; a ramp up its way to its raised level's edge
  (`ramp`: the edge, the way up and the level's top, which the assembly pitches it onto). Each object is marked for the assembly's
  `held` gate: `fills` (a door or window), `unheld` (its relations name nothing holding it), `unplaced` (left on the
  walls item, nothing places it: it would stand at the room's middle).
- **Far objects** (`far.py`; the owner, 2026-10-26: the skyline is the environment's own scenes where its plan puts
  them, and ordinary objects for anything that is no scene): each prop row of the hand-in marked `far` (prepare's
  groups.far_made) stands where its concept box is seen, along its bearing off the plan fixes' projection (up the
  picture is away), at the distance its read tall rises to its box's height in the framework's view (VIEW_FOV), its
  `far` pieces square to that bearing, waiting on its take's model like every object; one with no projection or box
  is named in `far_unplaced`, never placed by guess.
- **Lamps from the row kinds and the concept**: a light at each plan item of a glowing row (its row kind, or its
  concept showing it glow: `{home}/design/light/<place>.json`, the reading's concept light, its colour and brightness
  there; a row of the sky is the physics', no lamp), over its middle, as high on it as the library's lamp for the
  row's mount says, numbered by that lamp; an item outlining the whole room (holders.outlines_room: engineroom's
  wall panels) held on a wall stands its lamp on that wall's face at its relation's spot, `against` naming the face
  for the gate. A row lays as many lamps as its items' pieces and at least as many as its reading counts
  (`writer.lamp_count`, spread along each item or its wall's face; 2026-11-04: 23 rows in 13 places laid one lamp
  for up to 13 things), each `row` named, and plan-matched fails a glowing row with fewer (`gates.count_faults`). A
  glowing part that shows light rather than throws it (a screen, an indicator, a keyboard, a flame: lamps.json
  `glowing`, by what the concept shows glowing, else the row's words) is a faint emitter at its share of the lamp
  (2026-11-04: the lab's screens lit its room green). No lamp list per place.
- **The sky is the physics'**: the record's environment says inside or not and what overhead.py sees at the site at
  the scene time (lights over the horizon, bodies, backdrops); the light layer draws it (`score/stages/light/sky.py`).
  The record holds no air, haze or glow the design does not give; a place on a real body with dusty
  air (data/physics/dust.json, cited: Mars), inside places too (their glass and openings show it; 2026-11-04, camp),
  carries that dust as its `sky_dome`, the day sky tools/usd/mars_sky.py
  draws (`writer.sky_dome`; 2026-11-02: left out since the old records went, every outdoor Mars sky was black). Kept
  out of data/physics/bodies.json and score/review/setting.py on purpose: those sit in about 200 rows' keys.
- **Views** from inside each doorway and from each person spot; an inside place's view whose eye stands outside its
  outline is left out with why (`views_left_out`), never written to see the walls from behind. A look that meets a wall or
  floor thing within 1 m (`CLEAR_LOOK`) turns to the nearest clear way, else is left out with why (2026-10-31: flat's
  spot-2 faced its wardrobe from 0.45 m).
- **Places** are the design's: each place a door or opening leads to that its holder's plan holds beside it, stood
  with its nearest door leading back on this place's door to it (`plan.paired`; the hold only the first guess) and
  as high as a sibling's door to it stands (`plan.levels`: the square's flat 9 m up under its stairwell door; the
  scene tree raises a child the same way), and each place of its scene a backdrop row of its hand-in is `shown` from
  (prepare's groups.shown_from: the holder at its own plan's corner, a place it holds beside where it holds it).
  A top place has none (its children are its scene tree's). Each doorway leads where the place's own hold leads it
  (`writer.held_design`: the airlock's door to the hub led to tube#3), its neighbours' doors leading back to that
  hold's name (the tube's own hold, tube#4), as the `openings` gate judges them (2026-11-06).
- **Gates**: `game-free` (no game file or name: a date of the year 2099 is a scene time, not the game), `plan-matched`
  (every wall of the outline in the shell, every opening cut through it, every stair laid, every lamp over its
  item), `openings` (each doorway leads to a place of the design, outside, sealed, a row of the inventory or into its
  holder; a door to a neighbour has it stood, meeting one of its doors leading back within `plan.DOORS_MET` along
  the floor and `LEVEL_MET` in height; every view of an inside place inside its outline; each doorway its plan's
  door row: on its side, sill or bearing, its metres within `DOOR_SHARE`, at least `PASSABLE`, leading where its lead
  does), `laid-as-designed` (2026-11-04 audit, faults every check had passed: no two pieces of one row at one spot; a
  wall-held object's front out into the room, its built length within its wall's face, never bent round a corner of
  its walls (`bent_faults`: its ends on two straight runs, 2026-11-06: hangar's pipe, galley's cabinets), never inside another wall thing of any row by more than
  `holders.WALL_TOUCH` at their built boxes as the assembly lays them (`wall_overlap_faults`, 2026-11-06: hangar's 32 m pipes at 10 m in one another), off the
  floor where its words say high or it is a light; a thing hung from the roof its top at the roof's underside over it, `writer.roof_under`;
  a seat its words put at, by or before a holder within `SEAT_REACH` of its built side; a thing its relation stands
  on the floor more than half its built height over it with nothing under its footprint, `floor_faults`: no floor,
  deck, level or flight there, and no standing object's top, never its own row's unless its row piles,
  `holders.piles`: 2026-11-06, the engine room's railings piled 1 to 4 m up; a thing hung between holders, holders'
  `hung`, with fewer than two of them standing as high as it hangs, `hung_faults`: the square's lantern strings); a
  floor relation's `height` (holders.stood_under, around_holders) is where the writer stands its object, over its
  plan base (`writer.related`); `plan-matched` also holds
  each laid row to its scene inventory's count unless the plan's `dropped` or notes say why, or it is laid as often
  as the plan's doorways lead to its child scene's instances (`row_count_faults`, `led_instances`: base's seven
  tubes, 2026-11-06).
  Whether the made ground fits round the doorways is ground-fit's. The plan row's `held` (`plan.judge_held`, the
  audit of 2026-11-04: holds and door leads were never reconciled) fails a frame anchor, person spot or item outside
  its plan's box (a passage excepted, a thing on its wall's line allowed half its thickness), and on a holder's plan
  a hold off its own item for its row (10% in size, 0.5 m in middle), two holds overlapping, a place held once more
  doors lead to than lead back, and a door of a held place meeting no door of the sibling it leads to on the
  holder's plan. A place held several times (#72: a tube on each of the base's links) is held once per
  `instance` (`tube#3`), each with its own `leads` (what the place's doorways lead to there, by lead or by one door's
  lead and spot, `tube@15.834,2.341`: the hub's five doors to `tube`) and any hold a `turn` (any angle from 0 up to
  360: the tubes off the hub's diagonal facets); a tube (`shape: tube`) is stretched along its run to its hold's
  length, the hold its box round it turned (`plan.on_holder`, `laid_size`, read alike by plans.holds_fitted, the scene
  tree and terrain, whose spots are read through it: `own_from_holder`). Overlaps and rooms inside an item are judged on
  the held plans' outlines as laid (`laid_outline`, `outlines_overlap`), never their boxes. A place whose every door
  stands on a raised floor over a lower one is sunk so its doors meet the holder's floor (`sunk_by`: the greenhouse's
  garden). `held` judges each instance by itself and fails a hold another size than its plan laid in it and a door
  naming a place held only as instances; a neighbour that is an instance stands its place's stage, named `tube_3`,
  with its `instance` and `scale`.
- **Wall, roof and seat laying** (2026-11-04 audit): a wall object's x way is its wall's run turned by its `side`, so
  its front faces `out`; it stands at its relation's `height` (holders' mount height) where the plan gives no base; a
  `ceiling` relation marked `to roof` lays its top `ROOF_CLEAR` under the roof's underside at its spot; a relation's
  `beside` (a seat before its holder) is carried as the object's `beside`, its holder's objects named.
- Run the proof with `python -m score run world1 --place <place> --stage scene-record --detach`; the test is
  `test_a_scene_record_is_written_from_its_design.py` (a shed of its own: its plan maps, its record is written from a written plan, and a filled
  door, a moved lamp and a door to no place fail by name; its shell and stairs take the scene library's surfaces, or
  name why not).
