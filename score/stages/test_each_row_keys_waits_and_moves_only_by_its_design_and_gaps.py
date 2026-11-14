"""Each row of the stage table (score/stages, its top-level modules) keys, waits on and moves only what its design and
its gaps say: its code version moves with its own code alone, the layers a scene has are read off its design, a row's
kind off its own words, every designed person is a look of the people line, a ground follows its words then its
physics, a layer's copy of a read-only seed takes a save, an accepted gap or a batch gap moves only the faults it
names, and the push gate names the paid rows a change would buy again. One section a top-level module below, each
test under its section's heading in the code; the fixtures are each section's own, small, in temporary folders.

--- rows key and wait only on what they read ---

The stage table wires every row to key and wait on exactly what it reads (score/stages/__init__.py): a row's code
version moves with its own code and what it imports, never with another line's module, the runner, the table or the
run machinery (warm pool, provider, ledgers, money guards, cockpit), so an edit there buys nothing again; the rows a
layer or the light waits on are its real reads, and no base or layer row waits on the prop route; a design's dress
rows apply where its people wear them; a place is a scene whose design is done, a parent before its children; the
plan row and the cast read their design and plan, never a kit or a hand-written record; the environment data names no
path into the work folder.

The worked example on environment 1's round-three seeds (the hangar's) went with the old disk (2026-10-19) and only
ever skipped since; the runner's own make-twice-and-rerun-on-change rules are held by score/graph's test.

Breaks (each applied once, seen red, reverted), in score/stages/__init__.py and score/graph/_code.py:
- score/graph/_code.py `FRAMEWORK` without `score/stages/__init__.py`  -> the terrain key test (the table moves
  terrain's key).
- `FRAMEWORK` without `tools/cloud/provider.py`, or without `tools/cloud/secret_store.py`  -> the KEYED machinery rows.
- `broken_ask`: `return None` first  -> the Claude ask of test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (a
  Claude stream with no result line kept as the row's gap, surface-library@galley 2026-11-12);
  `startswith("no result line")` -> `True`  -> the same ask (an answer's own "no structured answer" raised as broken);
  `asking_claude(unbroken_asks(row.make))` -> `unbroken_asks(asking_claude(row.make))`  -> the KEYED claude rows
  (their keys lose claude_asks.py).
- the light layer no longer given the body faces' reads (`FACE_READS`)  -> the light-layer WIRED rows.
- `worn`: `applies` true at every place  -> the PER_PLACE dress rows (the square, the hold, nowhere).
- `people.dress_row`: the surface or variant left out of its params  -> the dress rows' params WIRED rows.
- `held_scenes`: the batch's places not intersected  -> the scene-tree rows of the places world (the dome counts).
- `filmed_places`: the batch's places listed with `places(world1())` again, not `plans.once`  -> the same rows
  (two listings a moment; a drive pass rebuilt all 81 plans per call, 2026-11-11).
- `batch_places`: the listing not kept across moments (`kept_while_read_stands` -> `make()`), or kept whatever it read
  (`all(...)` -> `True`), or `heard` hearing no folder listed (`os.scandir` dropped)  -> the places world's
  kept listing (each drive pass listed all 81 plans again, 35 s, 2026-11-11; a new record kept the old listing).
- `places`: the `merged` scenes not taken out  -> the places world's merged row.
- `ship_place`: always False  -> the PER_PLACE ship_place rows.
- `seen_from_record`: `ship_place(place)` alone (`or scene_record.written(place)` dropped)  -> the PER_PLACE
  surfaces-check neighbours rows (an earth place's surfaces-check read no scene record, so 46 of env1's models had no
  view distance, 2026-11-12); `True`  -> the same rows (a place the scene-record row writes nothing for would wait on
  it).
- score/stages/earth_seed/__init__.py: surface_data imported through its package (`from score.stages.surfaces import
  surface_data`)  -> the KEYED earth-seed rows.
- score/stages/surfaces/scene_library.py judge_library: `from score.stages.assembly import stage_file` added  -> the KEYED surface-library rows.
- score/stages/surfaces/route_views.py: `import place_line` added  -> the KEYED place_line.py row.
- score/stages/assembly/baked.py: `import complete as stage_inputs`  -> the KEYED completion gate rows of
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps, and its GAPPED_GATES rows.
- score/stages/shapes_first/__init__.py: the palette's optional Pixal3D read dropped (`optional=row.optional`)  ->
  the finish-route-palette WIRED row of test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps.
- `creator_plan`: the concept declared whether it is kept or not (`if True:`)  -> the plan row's code version in
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps.
- `plan_as_kit`: the plan not handed over as its kit (`{**arguments[position]}`)  -> the plan row's make with no
  kit.
- `remade_same`: always True (`return True`)  -> the plan row's make (its own plan redrawn still carries); its
  `runner.foreseen[...] = ...` dropped  -> the same (the redrawn plan not foreseen).
- `part_moved`: the part compared whole (`old, new = store.listing(then), listing`)  ->
  test_terrain_s_code_version_moves_with_its_own_code_only (hub's light passes made again); `part_standing`: a moved
  read with no part rule let through (`any(...)` dropped)  -> the same test (scene-record moved, still kept);
  score/graph/rebuy.py `to_make`: the foreseen reads not let through (`foreseen = []`)  -> the same test (rebuy's hub).
- score/graph/rebuy.py `to_make`: the `remade` hook not asked (`if False and ...`), or `remade_over_foreseen` lending no
  terrain (`runner.kept_as.update(then)` -> `pass`)  -> test_terrain_s_code_version_moves_with_its_own_code_only (the
  scene record made the same re-bought); `remade_kept.carries`: remade_same dropped  -> the same test (surfaces-parts);
  `part_foreseen`: a place row's remake not read (`placed = False`)  -> the same test (the sound over moves.json).
- `stamp_read`: the stamp compared whole (`return found or ...`)  -> the same test (the seed remade elsewhere made
  again); its inputs' hashes dropped, or `seed_kept` comparing no layer (`any(...)` dropped)  -> the same test (a seed
  of another inventory or layer kept).
- `made_again`: the store's cache not read (`if False and kept is not None ...`)  -> the same test (a key remade in
  each run).
- `made_again`: its scratch made in /tmp (`dir=scratch_home(...)` dropped), or `linkable` copying nothing
  (`return dict(inputs)`)  -> the same test (a remake linking an input of another device).
- `ahead_workers`: the room not counted (`int(ROOM() // REMAKE_PEAK)` -> `jobs`), or `made_again` starting a remake
  past the floor (`if ROOM() < REMAKE_PEAK` -> `if False`)  -> the same test (the capped remakes side by side, or made
  with no room).
- the surfaces-check row's `"stance rules"` file dropped  -> the check_step reads (every key surfaces-check hands).
- `earth_seeded.declared`: the seed-read filter dropped (`return dict(found)`)  -> the PER_PLACE cast kit rows of
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (stale: green on a04dfcd33's own cast test too,
  2026-11-14; the sandbox home has no earth seed, so nothing is read from one).
- `earth_place`: always True  -> the PER_PLACE cast kit rows (the cockpit's cast declares no kit of its own).
- data/checks/row-kinds.json: its "about" naming `{home}/work/old`  -> the data's work-folder paths (a wording
  check guarding the rule above).
- `MOTION_LAYER`: growth's `crops-layer` written `crops`  -> the motion layer patterns that name no row.
- score/graph/_code.py `source_files`: FRAMEWORK not left out (`set()`)  -> the terrain test and the KEYED rows above, and the push
  gate's TREE_EDITS framework-only row.
- `scripts_declared`: the row returned as it was  -> the started-scripts check (every
  row that starts a script, surfaces-bake's recipes.py among them); score/graph/_code.py `script_imports`: the files
  beside a script dropped  -> the same test (make_chunky.py's bake.py, pieces.py ...); `STARTED_LEFT` with a row that
  starts nothing  -> the same test; `reads_recipes` always False  -> the dress row's vendored-recipes WIRED row of
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps.
- `set_aside`: `if not aside.exists():` -> `if True:`  -> the rejected takes (the retake set aside again over the
  old); `retake_pending` without `and not retake_handed(...)`, or retake_handed's `!=` on the size made `==`  -> the
  handed-record rows; set_aside's `objects[name]["take"] if name in objects else name` made `name`  -> the reject
  naming the object (checkout 66, 2026-11-09).
- `parts_reseeded`: `stamp.read_text() == str(seed)` made `True`, or its folder kept without a stamp  -> the look's
  parts bought again at a new seed.
- `retaking`: `pixal_row.seed_of = lambda take: ...` -> `pass`  -> the retake's seeds (2, 3) asked; `sheet_remakes(seeds,
  inputs, out)` -> `pass`  -> the sheet's take not built in code.
- `leaving_out`: `batch_gaps.write(out, [*found, *left_out_gaps(inputs, found)])` -> `pass`  -> the likeness's
  left-out gaps; `LEFT_OUT = ("likeness", "motion")` -> `("likeness",)`  -> the motion WRAPPED row.
- `designed_motion`: `found = {**found, "props": prop_data.keyed(place)}` -> `pass`  -> motion's files at a
  designed place.
- `gap_moved`: `carried = tied(batch_gaps.of(inputs, output), inputs) if batch else []` -> `carried =
  batch_gaps.of(inputs, output) if batch else []`  -> the lean gate's counter row; score/stages/gaps.py moved: `if not
  said:` -> `if True:`  -> the lean gate's mixed faults row.
- score/stages/surfaces/route_views.py `view_take`: a read of a file no argument names added (`(REPO /
  "data/library/materials.json").read_text()`)  -> test_each_per_take_function_opens_only_its_arguments_its_code_and_python
  (kept.call would hand back a take made from that file's old bytes); the same in route_split.py `split_take` or
  route_parts.py `parts_take`  -> the same test.

--- a scenes layers are read off its design, and a rows kind comes from its own words ---

The cases of test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps, the one test these two sections and the accepted-gap
section below fold into.
Which layers a scene has is read off its design alone, and the stage table and the assembly's layers gate give one
answer (design_layers.py): each row shows the layer its kind does, crops are plants on a bed and never a potted plant,
every scene with a design has light and sound, a place with no kept design has no layer at all, and for a design kept
where the plan stage keeps it every layer row the assembly's gate waits on is a row the table holds for the place, and
no other. On designs and row-kind rules written here.

Breaks (each applied once, seen red, reverted), in score/stages/design_layers.py:
- `DOES`: `"loose": "physics"` dropped  -> the kettle row (it shows no physics).
- `on_bed`: `or "grows" in ...` dropped  -> the plants-on-a-rack row (its greens are no crops).
- `plants_of`: the beds kept among the plants (`if row["id"] not in beds` dropped)  -> the plants-and-beds row.
- `has_layer`: `if place is None or not path.is_file(): return False` read as returning True  ->
  the barn's has_layer row.
- `kinds_of`: `set(EVERY_SCENE)` read as `set()`  -> the opening gives no motion row (no light).
- score/stages/__init__.py: the sound row's `designed("sound")` written `designed("sounds")`  ->
  the hangar's table check.
- data/checks/row-kinds.json: "tree" dropped from the plant nouns  -> the house plant: tree row.

A scene inventory row's kind comes from its own reading words alone (row_kinds.py): its reading noun first, matched
whole, its name's last word only for a row read with no noun, else the kind its name says holds it; a scene's
emitting, moving and loose rows are picked out by what their kind does; a row's objects are found on a stage by name,
outside the layers' own scopes, and a prim no row's object has is a stranger. On rules written here and on the house
rules (data/checks/row-kinds.json, where the expected kinds are read off the file's own nouns by hand).

Breaks (each applied once, seen red, reverted), in score/stages/row_kinds.py:
- `said_nouns`: the noun ignored (`noun = words(row.get("noun"))` read as `noun = ""`)  -> the floor plate row.
- `kind_of`: `wanted in rule["nouns"]` read as any noun inside the words  -> the door panel row.
- `held_kind`: `said[-2] in rule["nouns"]` dropped  -> the fence post row (read as a lamp).
- `kind_of`: `if row.get("part") == "opening":` read as `if False:`  -> the opening rows (workshop's doorway, a hole
  read with the noun "door", swings and its scene needs motion).
- `objects_of`: the NOT_OBJECTS prune dropped  -> the toy door objects (/toy/Effects/door_3 found).
- `of_row`: `(_\\d+)?` read as `.*`  -> the toy door objects (door_frame_1 found) and the strangers.
- `does`: only a kind's first deed read (`["does"][:1]`)  ->
  the loose-rows row (the kettle not picked), the kettle row and the hangar's table check.
- data/checks/row-kinds.json: "tv" dropped from the screen nouns  -> the house: tv row.

--- every designed person is a look of the line ---

Every person a picked design shows is a look of the shared people line, written from the design alone
(people_rows.py, data/people/rows.json, #26): every people row maps to looks the line holds, one look (one body) for
the people the rows say are and wear the same, written from its largest standing row (its spec and take); a crowd to
one far look read off its words, standing on the plan items its row makes, in a few variants of its body; each person
stood on the plan's people spots, each of a look its own variant; the line's data is exactly what rows.json maps,
each look baked at its person row's size and drawn from the person that maps it; a refresh keeps a hand-made choice
only while its concept stands; a row wears the fabric its words name nearest its measured torso.

Breaks (each applied once, seen red, reverted), in score/stages/people_rows.py:
- `look_of`: the pose and colour words kept in the look's name  -> the JUDGED look rows (seated astronaut).
- `crowd_ground`: every plan item taken, not only the row's  -> the CROWD_GROUNDS rows (the bench is crowd ground).
- `persons`: every person given variant 0  -> the deck's cast ("each its own variant").
- `placed_spots`: a spot's two plan coordinates swapped  -> the deck's cast (the spot (1, 1) of a 20 x 10 plan
  stands at (-9, 0, -4)).
- `placed_spots`: the row tag dropped  -> the swapped cast (the pilot dealt the officer's spot, its row id first).
- `dealt_spots`: `own = tagged.get(person["row"]) or untagged` read as `own = untagged`  -> the deck's cast (the
  pilots on the place's middle).
- `refreshed_place`: a kept pick taken with no `why`  -> the refresh rows (a pick with no why kept).
- `crowd_look`: `needed = 0` (the crowd word alone decides)  -> the CROWD_LOOKS rows ("crowd of aliens").
- `mapping_rows`: `if look not in mapped or ...` read as `if look in mapped and ...` (no look mapped)  -> the home's
  people rows mapping the astronaut, the designed specs and the line's data.
- `mapping_rows`: a sitting row ranked like a standing one  -> the designed specs (the pilot drawn from the seated
  copilot).
- score/stages/complete/prepare/groups.py `stood_beyond`: `and anchors[row_id] not in found` dropped  -> the deck's
  beyond rows (the man on its own stairs left out).
- `mapping_rows`: `said` left out of `rank` (`return standing, fields.get("share") or 0.0`)  -> the designed specs
  (the astronaut drawn from the "person in spacesuit").
- `size_of`: `person_sized` not asked (`if origin:`)  -> the line's crowd look (the crowd's extent as one person).
- score/stages/people_refresh.py `drawn_from`: the tallest box read with `min`  -> the toy kept inventories' astronaut
  (drawn from SAM 3's tallest instance).
- `described`: the spec's description left out (`"name": clothes`)  -> the line's data (no longer as rows.json
  writes it).
- score/stages/props/closeup_row.py `inventory_rows`: the words the clothes alone (`row.get("clothes", row["name"])`)
  -> the line's close-up words.
- score/stages/people_clothes.py `worn`: the nearest fabric read with `max`  -> the DRESSED rows.
- score/stages/people_clothes.py `said_colour`: `return []`  -> the DRESSED shaded white suit row (dressed in the dark
  seam cloth).
- score/stages/people_clothes.py `worn`: drop the `if not candidates:` return  -> the DRESSED names no fabric row (a
  measured torso whose words name no fabric wears its look's own paint).
- score/stages/people_clothes.py `fabrics_of`: `if not lab_of:` -> `if False:` (an empty library answers {})  -> the
  library with no fabric (NoFabrics).
- `worn_by`: `IMPLIED.get(who, ())` -> `()` (astronaut_suit-made), or `wearers = []` (person_spacesuit-made)  ->
  the JUDGED look rows (astronaut in spacesuit, person in spacesuit).

--- a ground follows its words then its physics ---

A natural ground's recipe follows its row's own words first, else its body's physics against water's phases, and
never a body's name (natural_grounds.py). The expected recipes are worked out by hand from each made-up body's
pressure and its zero-albedo temperature, T = T_star sqrt(R_star / 2d): at 1 AU from a 5772 K star of 695,700 km,
278 K; at 0.2 AU, 622 K (over water's boiling at 101.3 kPa, 373 K); at 5.2 AU, 122 K (under ICE_K); at 1.52 AU,
226 K (no liquid at 0.6 kPa, under the triple point's 273 K, but an air over WIND_KPA).

Breaks (each applied once, seen red, reverted), in score/stages/natural_grounds.py:
- `warmth_k`: `2.0 * child["distance_km"]` read as `child["distance_km"]`  -> the JUDGED ground rows (the hot world,
  880 K, is still rock, but the wet one at 393 K boils to rock).
- `of_body`: `kelvin <= boils` read as `kelvin <= WATER_TRIPLE_K`  -> the ground: wet row (it reads rock).
- `of_body`: the `kelvin < ICE_K` rule dropped  -> the ground: frozen row (it reads regolith).
- `of_row`: the MADE words not read  -> the ground: plaza row (it takes its body's sand).
- `pressure_kpa`: the reference table not read  -> the ground: the table's pressure row (no pressure).

--- a copy of a read only seed takes a save ---

The copy of a seed a layer is written over takes a save, though the store's seed is read-only and copies keep its
modes (layer_base.py `writable`).

Breaks (each applied once, seen red, reverted), in score/stages/layer_base.py:
- `writable`: its chmod left out (the function body made `return`)  -> a PermissionError on the seed's save.

--- an accepted gap moves only its named faults ---

An accepted gap moves only the faults it names down the line, never loosens a gate (gaps.py): a failing gate passes
only when every finding is a named object's (of the entry's kind when it says one; by its row for a JSON finding),
keeping the findings; any other fault still fails it; a named unknown moves and another stays; complete fails every
gap by name with its numbers, the owner's and the ones a row wrote in its output; a gap is an input of complete and of
the row it names alone, and only complete's code version holds gaps.py, so moving a verdict re-makes nothing paid.

The owner's gap decisions of the old concepts were retired with them (2026-10-21), so the test writes each decision it
judges, in the file's own form, into a gaps folder of its own.

Breaks (each applied once, seen red, reverted), in score/stages/gaps.py:
- `moved`: `if not all(any(covers(...)) ...)` read with `any` over the findings  -> the MOVED named-faults
  rows (another fault moves too).
- `covers`: `and entry.get("contains", "") in finding` dropped  -> the MOVED order rows (a colour fault moves).
- `object_of`: the JSON branch dropped  -> the MOVED rows and boxes rows.
- `moved`: the unknown branch dropped  -> the MOVED named-unknown row.
- `files`: the `row is not None and ...` narrowing dropped  -> the GAP_READERS rows (the paint reads the
  street's gaps).
- `judge_accepted`: `written(inputs)` left out  -> the far city's written gap (FAR_CITY).
- `entries`: the row and check filter dropped (`return list(found)`)  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (the wreck's decision file).
- `judge_accepted`: a finding without its gap's name (`f"{fault}"`)  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (its crane, and the batch section's line test).
- score/stages/people_gaps.py `judge_accepted`: every batch gap kept (`whose = False`); or `of_people` reading a
  model's row from any name (`number.isdigit()` dropped); or `all` read as `any` over a gap's objects  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (its people batch gaps).
- score/stages/__init__.py `gap_moved`: `judged.__wrapped__ = check.judge` dropped  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (its GAPPED_GATES rows; its Pixal3D take and its
  paint's table moves).
- data/checks/gaps/garage.json: its pipe entry deleted; or this file's `dropped`: `if entry.get("passed")` dropped  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (its DROPPED rows and the tree's own records;
  2026-10-29: 37aa882c dropped the owner's pipe gap by itself).

--- a failed paid take is a gap carried down its line ---

A take whose paid step failed inside the batch is a gap carried down its place's line, never a stop and never a
loosened gate (batch_gaps.py, the table's `accepted_gaps` mover): the row whose step failed names the take in its
batch-gaps.json, its gate still fails it and the table moves exactly that fault; the rows after it leave the take out
and carry its gap on; the line runs on to complete, which lists the gap with the batch run that decided it; a fault
no batch gap names still stops the line. The Pixal3D batch and the check's step are faked at their subprocess and
hand-over; the takes are written under the sandbox home.

Fault (#10, 2026-10-21): a failed close-up or Pixal3D job failed the next free gate, and the place's line waited for
the owner, though his yes to the batch had already decided that a failure is a gap.

Breaks (each applied once, seen red, reverted), in score/stages/batch_gaps.py:
- `batch_gaps.read`: `found.setdefault(...)` read as `found[entry["name"]] = ...` with `decided` dropped  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (its Pixal3D take: no `decided`).
- `batch_gaps.of`: the inputs' folders left out (only `output`)  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (its views and its fixture line: the gap is not
  carried, so complete has nothing to list).
- `batch_gaps.objects`: returns an empty set  -> test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (its
  Pixal3D take: the table no longer moves the hatch's fault).
- `batch_gaps.write`: writes `{"gaps": []}`  -> test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (every
  written gap it reads).
- score/stages/surfaces/route_paint.py: `if found:` read as `if True:` (a gaps file written always)  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (its clean paint).
- a fault no batch gap names, and a take lost with none: the gaps section's `moved` break (`all` read as `any`)  ->
  test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps (the changed crate take; the LINES lost-crate row).

--- push gate names the paid rows it moves ---

The push gate (moved.py, `score moved --pre-push`, .claude/hooks/local/pre-push-moved) asks only the cheap question, in
about a minute: the rows the pushed commit moves against main's (code, stage table part, declared files, every world),
refusing a push to main only for a moved paid row no Moved-rows trailer names with a reason; a move no file explains
(a params, contract or model change) is refused like any other, and the hook leaves no process or checkout behind.
`score moved` (no --pre-push) still names the paid rows a change would buy again, each with its price and why: a
run's question before it starts (owner, 2026-11-07: "shouldnt the rebuy check just be before a buy"; asked at every
push it took 15 to 20 minutes).

A toy git repository stands in for this one (moved.REPO, _code.REPO): a paid render whose make sits in it and imports
a framework file, a paid bake, each reading a data file of its own, and a paid film reading an unpaid drawing of a
third data file. The hook itself is run against a toy repository whose score package only records what it was given.

Faults it guards (2026-10-17): about EUR 65 of re-buys (view maps, turntables, the cockpit library push) came from
code and data changes nobody saw would move a paid row's key before they were pushed (8b402226: blender_cloud.py,
outside every code version but declared by the turntables; 1f90a0fe: new gap files a paid row declares). The first
hook refused every push over drift already on main, refused branch deletions and took any trailer as leave for every
row; its second form let a framework-only push through unchecked and only warned of a move no file explains. On
2026-11-07 cb8b4557 moved a paid images row through images.json, a world the snapshot did not cover.

Its checks are the push-gate part of test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps: TREE_EDITS rows
on the toy's working tree, its trailer commit and pre-push check, its framework move, PUSH_LINES, ROW_NAMED and the
hook's HOOK_CASES rows.

Breaks (each applied once, seen red, reverted), in score/stages/moved.py and .claude/hooks/local/pre-push-moved:
- `total`: `sum(row.euros ...)` read as `sum(0 * row.euros ...)`  -> the TREE_EDITS file-one-paid-row-reads row
  ("about EUR 3.00").
- `main_pushes`: `ref == MAIN and` dropped  -> the PUSH_LINES rows.
- `trailer_nodes`: `and why.strip()` dropped  -> the ROW_NAMED rows ("bake@hangar:  ").
- `unnamed_paid`: `not row_named(...)` read as `row_named(...)`  -> the trailer commit (render let go, bake refused);
  its `row["paid"] and` dropped  -> the TREE_EDITS row moved through what it reads (the free draw row refused).
- `row_named`: `node.partition("@")[0] in names` read as `node.startswith(row)`  -> the ROW_NAMED rows (bake2 names
  bake).
- `moved_rows`: its `before[name].get("table") != row.get("table")` dropped  -> the TREE_EDITS move no file explains.
- `edited_into_framework`: `after - before` read as `before - after`  -> the framework move.
- .claude/hooks/local/pre-push-moved: its `trap '... worktree remove ...' EXIT` line made a no-op  -> the HOOK_CASES
  changed-tree row (the checkout is left behind).
- score/__main__.py `moved_check`: `> 0` read as `>= 0`  -> the TREE_EDITS nothing-changed row.
- score/graph/_code.py `source_files`: FRAMEWORK not left out  -> the TREE_EDITS framework-only row.
- score/graph/rebuy.py `buys`: `if remade[name]` read as `if not remade[name]`  -> the TREE_EDITS row moved through
  what it reads.
- score/__main__.py `pre_push_check`: `if remote == moved.ZERO` check dropped  -> the pre-push check of an unknown
  main.
- `snapshot`: `shutil.rmtree(holder)` made `pass`, or its `worktree remove` made `pass`  -> the snapshot of an unknown
  commit or a failing tree, and the HOOK_CASES out-of-time row.
- `tree_is_at`: the `git status --porcelain` check dropped  -> the pre-push check of a changed tree.
- the hook's `= true ] || exit 0` read as `|| true`  -> the HOOK_CASES off row.
- the hook's `[ ! -d "$home/store/objects" ]` dropped, or its candidate loop's `break` dropped (this PC's run home
  read over a default home holding a store)  -> the HOOK_CASES home rows.
- the hook's `[ "$remote_ref" = refs/heads/main ] &&` dropped  -> the HOOK_CASES tag and other-branch rows.
- the hook's `rm -rf "$checkout"` dropped  -> the HOOK_CASES no-worktree row (its TMPDIR not empty).
- the hook's `grep -qs -- "--pre-push"` read as `grep -qs -- ""`  -> the HOOK_CASES before-score-moved row.
- the hook's `|| echo 3600` read as `|| echo 900`  -> every HOOK_CASES row that runs the check.
- the hook's main-checkout python (`$(git rev-parse --git-common-dir)/..`) read as `$repo`  -> the HOOK_CASES
  worktree row.
"""

import ast
import contextlib
import dataclasses
import errno
import fnmatch
import functools
import hashlib
import importlib
import inspect
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import types
from unittest import mock

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
# The script's own folder (score/stages) off the path: on it, tools/usd's `import motion` also finds the motion
# stage, and the code versions measured here take in its imports (feet.py, triage.py) as `python -m score` never does.
HERE = pathlib.Path(__file__).resolve().parent
sys.path[:] = [entry for entry in sys.path if pathlib.Path(entry or ".").resolve() != HERE]
sys.path.insert(0, str(REPO))

from pxr import Usd, UsdGeom  # noqa: E402
from score import checks, contracts, graph, review, stages  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.graph import _code, rebuy  # noqa: E402
from score.stages import (batch_gaps, design_layers, gaps, layer_base, moved, natural_grounds,  # noqa: E402
                          people_gaps, people_refresh, people_rows, row_kinds)
from score.stages.surfaces import claude_asks, route_views  # noqa: E402
from score.store import PROPS_HOME, Store, file_hash, tree_hash as store_tree_hash  # noqa: E402
import score.stages.props.pixal_row as pixal_row  # noqa: E402


# --- rows key and wait only on what they read ---

@functools.cache
def code_hashed(functions):
    """The runner's code version of these functions and {file: its hash} of each file it hashed, worked out once a
    process: the import walk parses every module behind a row, and the tests below ask it hundreds of times."""
    hashed = {}
    version = graph._code.code_version(list(functions), lambda path: hashed.setdefault(path, file_hash(path)))
    return version, hashed


@pytest.fixture(autouse=True)
def room_for_remakes(monkeypatch):
    """Every remake here fits the memory room (stages.ROOM): no verdict hangs on this PC's free memory."""
    monkeypatch.setattr(stages, "ROOM", lambda: 64 * 2**30)


def code_after_editing(stage, edited):
    """A stage's code version, as the runner works it out, as if the repository file `edited` had changed (its hash
    moved; nothing written)."""
    functions = (stage.make, stage.contract.faults, *(check.judge for check in stage.checks),
                 *([stage.files] if callable(stage.files) else []), *([stage.neighbours] if stage.neighbours else []))
    version, hashed = code_hashed(functions)
    path = REPO / edited
    return [part + "+edit" if path in hashed and part == f"{edited} {hashed[path]}" else part for part in version]


def terrain_code_after_editing(edited):
    """Terrain's code version as if the repository file `edited` had changed."""
    return code_after_editing(stages.TERRAIN, edited)


PAINT_BLIND = ["finish-route-views", "finish-route-list", "finish-route-split", "finish-route-recheck", "terrain"]
MACHINERY = ("tools/cloud/pool.py", "tools/cloud/spread.py", "tools/cloud/provider.py", "tools/cloud/backends/scaleway.py",
             "tools/cloud/ledger.py", "tools/cloud/google_spend.py", "tools/cloud/preflight.py",
             "tools/cloud/secret_store.py", "score/adapters/compute/guard.py", "score/dashboard/__init__.py")
EVERY = "every row asked"
# (the file edited, the rows asked (name patterns, "*" the whole table), the rows of those its edit moves): a row's code
# version moves with its own code and what it imports alone
KEYED = [
    # earth-seed reads a place's surface data through surface_data.py alone, never the surface line's package (its
    # __init__ pulled the whole line in, 2026-10-21)
    *[(edited, ["earth-seed"], set()) for edited in ("score/stages/surfaces/__init__.py",
                                                     "score/stages/surfaces/place_line.py")],
    ("score/stages/surfaces/surface_data.py", ["earth-seed"], EVERY),
    # surface-library's key holds no assembly (the library check's import through the assembly package re-keyed all
    # 27 rows on each fitting.py edit, 2026-10-30); its own check (judge_library) moves it
    *[(edited, ["surface-library*"], set()) for edited in ("score/stages/assembly/fitting.py",
                                                           "score/stages/assembly/__init__.py")],
    ("score/stages/surfaces/scene_library.py", ["surface-library*"], EVERY),
    # the table's Claude-ask wrapper keys no claude row
    ("score/stages/__init__.py", list(claude_asks.ROWS), set()),
    # the surface line's paint, bake and check code, the resting triage, the settle and the pick check leave the
    # finish route's paid rows and terrain alone (each re-bought on the water tank's fix, 2026-10-12, through the
    # surfaces __init__ and complete.py); the paint and bake rows move with place_line.py, the check with bake_check.py
    ("score/stages/surfaces/place_line.py", [*PAINT_BLIND, "surfaces-paint", "surfaces-bake"],
     {"surfaces-paint", "surfaces-bake"}),
    ("score/stages/surfaces/bake_check.py", [*PAINT_BLIND, "surfaces-check"], {"surfaces-check"}),
    *[(edited, PAINT_BLIND, set()) for edited in ("tools/props/library/feet.py", "tools/usd/triage.py",
                                                  "tools/usd/settle.py", "tools/usd/picks.py")],
    # what only decides where and how a job runs (the warm pool, spreading, the provider and its backend, the ledgers,
    # forecasts, money guards, the cockpit) moves no row (a body made again for EUR 0.30 by warm-pool edits, owner
    # 2026-10-23); a maker's own code and a runner module that sends its scripts up still do
    *[(edited, ["*"], set()) for edited in MACHINERY],
    *[(edited, ["people-body-*"], EVERY) for edited in ("score/stages/people_bodies/bodies.py",
                                                        "tools/cloud/similar.py")],
    # the completion gate moves the complete row and no other: the assembly, neighbours and likeness read the inputs
    # record's helpers from stage_inputs.py (each re-made by a gate edit before 2026-10-12); snap.py is the settle's
    # too (settling/held.py) and the light rows' (camera_paths.place_scenes reads each place's meshes with read_place)
    *[(edited, ["*"], {"complete"}) for edited in ("tools/usd/complete.py", "tools/usd/contents.py",
                                                   "tools/usd/reach.py", "score/stages/complete/__init__.py")],
    ("tools/usd/snap.py", ["*"], {"complete", "settle", "light", "light-layer", "light-passes"}),
]


def test_terrain_s_code_version_moves_with_its_own_code_only():
    """Another line's edits to the runner, the stage table or another stage's module leave terrain's key alone (they
    re-made terrain under the effects line, 2026-10-12); its own module and what it imports move it. And terrain made
    again elsewhere than a place's own layer moves none of that place's readers: its light passes keep their accepted
    output (made, or foreseen by rebuy before terrain is made), and its sound keeps over a motion whose moves.json
    stands; a place whose layer changed, or a read with no part rule moved, is made again (the square redrawn listed
    every place's light passes and sound, 2026-11-07)."""
    before = terrain_code_after_editing("nothing")
    for unrelated in ("score/stages/__init__.py", "score/graph/__init__.py", "score/review/__init__.py",
                      "score/adapters/compute/__init__.py", "score/stages/effects/__init__.py",
                      "score/stages/assembly/__init__.py", "score/stages/surfaces/__init__.py"):
        assert terrain_code_after_editing(unrelated) == before, unrelated
    for own in ("score/stages/terrain/__init__.py", "score/stages/terrain/design.py",
                "score/stages/terrain/outside.py"):
        assert terrain_code_after_editing(own) != before, own
    rows = {row.name: row for row in stages.STAGES}
    listings = {"T0": {"moon/ground.json": "g0", "moon/places/hub.usdc": "h", "moon/places/base.usdc": "b0"},
                "T1": {"moon/ground.json": "g1", "moon/places/hub.usdc": "h", "moon/places/base.usdc": "b1"},
                "M0": {"moves.json": "m", "layer.usda": "l0"}, "M1": {"moves.json": "m", "layer.usda": "l1"}}
    own = {"code": "c", "contract": "s", "expects": {}, "params": {}, "seed": 1, "files": {}, "models": {}}
    record = {**own, "key": "k0", "output": "out", "after": {"terrain": "T0", "scene-record": "S0", "motion": "M0"}}
    store = types.SimpleNamespace(accepted=lambda node: "out", records=lambda node: [record], listing=listings.get)

    def key(stage, place):
        if stage.name != "terrain":
            raise graph.Blocked("terrain is not made on its key yet")
        return {"key": "KT"}
    runner = types.SimpleNamespace(store=store, stages=rows, key=key, own_parts=lambda stage, place: own)
    passes = rows["light-passes"]
    for moved_after, place, kept in (({"terrain": "T1"}, "hub", True), ({"terrain": "T1"}, "base", False),
                                     ({"terrain": "T1", "scene-record": "S1"}, "hub", False)):
        keyed = {**own, "key": "k1", "after": {**record["after"], **moved_after}}
        assert passes.files.carries(runner, passes, place, keyed) is kept, (moved_after, place)
    assert rows["sound"].files.carries(runner, rows["sound"], "hub", {**own, "after": {**record["after"],
                                                                                        "motion": "M1"}})
    assert not rows["ground-fit"].files.__dict__.get("carries")  # it reads its body's whole ground.json
    stages.FORESIGHTS["terrain", "KT"] = listings["T1"]
    try:
        assert rebuy.to_make(runner, passes, "hub", ["terrain"], {"terrain": True}) is rebuy.KEPT
        assert rebuy.to_make(runner, passes, "base", ["terrain"], {"terrain": True}) == {}
        # A free row whose code moved (0fcfc2b2's triage.py), made again over the terrain it read (its place's layer
        # foreseen the same), keeps when it gives its accepted output; a motion made otherwise keeps the sound while
        # its moves.json stands (883d65f2 listed every place's light passes and sound, 2026-11-07).
        with tempfile.TemporaryDirectory() as folder:
            made = pathlib.Path(folder)
            contracts.stamp(TOY, made)
            (made / "record.json").write_text("{}")
            accepted = store_tree_hash(made)

            def make(written):
                def made_now(inputs, out, seed, params):
                    (out / "record.json").write_text(written)
                return made_now
            lent = {**own, "code": "c2"}
            same_store = types.SimpleNamespace(accepted=lambda node: accepted, records=lambda node: [
                {**record, "output": accepted}], listing=listings.get)

            def worked_out(stage, place):
                if lending.kept_as.get("terrain") != "T0":
                    raise graph.Blocked("terrain is not made on its key yet")
                return {**lent, "key": "k2", "after": {**record["after"]}}
            lending = types.SimpleNamespace(store=same_store, stages=rows, key=key, own_parts=lambda stage, place: lent,
                                            worked_out_key=worked_out, input_paths=lambda stage, place, keyed: {},
                                            kept_as={}, foreseen={}, foreseen_listing={})
            for written, kept in (("{}", True), ('{"moved": 1}', False)):
                row = dataclasses.replace(rows["scene-record"], make=make(written), contract=TOY)
                assert (rebuy.to_make(lending, row, "hub", ["terrain"], {"terrain": True}) is rebuy.KEPT) is kept
                assert lending.kept_as == {}, "the lent terrain is handed back"
            assert rows["surfaces-parts"].files.carries(lending, dataclasses.replace(
                rows["surfaces-parts"], make=make("{}"), contract=TOY), "hub", {**lent, "key": "k2", "after": {}})
        # The earth seed made again keeps where only its inputs.json's stamp of when and where differs (fcc59e40's
        # seed code moved every place's scene record and light passes); another inventory or layer is made again.
        def stamp(at, home, sha):
            return {"at": at, "inventory": f"{home}/inventory/hub.json", "inputs": {f"{home}/inventory/hub.json": sha},
                    "models": {"crate": {"file": f"{home}/crate.gltf", "sha256": "c", "mtime": at}}}

        def seed_make(layer, written):
            def made_now(inputs, out, seed, params):
                (out / "hub").mkdir()
                (out / "hub/base.usda").write_text(layer)
                (out / "hub/inputs.json").write_text(json.dumps(written))
            return made_now
        with tempfile.TemporaryDirectory() as folder:
            made = pathlib.Path(folder)
            seed_make("ground", stamp(1, "/frozen", "i"))({}, made, 0, {})
            contracts.stamp(TOY, made)
            accepted = store_tree_hash(made)
            listed = {name: hashlib.sha256((made / name).read_bytes()).hexdigest() for name in
                      ("hub/base.usda", "hub/inputs.json", contracts.STAMP)}
            seed_store = types.SimpleNamespace(accepted=lambda node: accepted, listing=lambda output: listed,
                                               read_file=lambda output, name: json.loads((made / name).read_text()))
            seeding = types.SimpleNamespace(store=seed_store, input_paths=lambda stage, place, keyed: {})
            for number, (layer, written, kept) in enumerate((("ground", stamp(2, "/home/pc", "i"), True),
                                                             ("ground", stamp(2, "/home/pc", "j"), False),
                                                             ("decks", stamp(1, "/frozen", "i"), False))):
                seed = dataclasses.replace(rows["earth-seed"], make=seed_make(layer, written), contract=TOY)
                assert seed.files.carries(seeding, seed, "hub", {"key": f"s{number}", "seed": 0, "params": {}}) is kept
            # A remake is kept in the store's cache by node and key: a later run asks it of the cache, never makes it
            # again (each run made them all again: score moved 45 s -> 10 min, 2026-11-07); a failed one is not kept.
            makes = []

            def counted(inputs, out, seed, params):
                makes.append(1)
                seed_make("ground", stamp(2, "/home/pc", "i"))(inputs, out, seed, params)

            def failing(inputs, out, seed, params):
                raise RuntimeError("no memory")
            with tempfile.TemporaryDirectory() as cache:
                for run, make in enumerate((failing, counted, counted, failing)):
                    stages.SEEDS_KEPT.clear()
                    stages.FAILED.clear()
                    cached = types.SimpleNamespace(store=types.SimpleNamespace(**vars(seed_store), cache=cache),
                                                   input_paths=seeding.input_paths)
                    seed = dataclasses.replace(rows["earth-seed"], make=make, contract=TOY)
                    assert seed.files.carries(cached, seed, "hub", {"key": "cached", "seed": 0, "params": {}}) is \
                        (run > 0), run
                assert makes == [1], makes
            # Side by side only as many remakes as fit the memory room (a scope's cap counted); a small cap makes
            # them one at a time, every one made, none failed; none is started past the floor (the conductor's 10 GB
            # scope was killed twice by this pass's remakes, 2026-11-07).
            for room, workers, made in ((3 * 2**30, 1, 2), (2**30, 0, 0)):
                makes.clear()
                stages.FAILED.clear()
                stages.ROOM = lambda: room
                with tempfile.TemporaryDirectory() as cache:
                    ahead = types.SimpleNamespace(
                        store=types.SimpleNamespace(**vars(seed_store), cache=cache, record=lambda node, key: None),
                        remembered=None, kept_as={}, read_nodes=lambda stage, place, every=False: [],
                        worked_out_key=lambda stage, place: {"key": f"ahead-{place}", "seed": 0, "params": {}},
                        input_paths=seeding.input_paths)
                    seed = dataclasses.replace(rows["earth-seed"], make=counted, contract=TOY)
                    assert stages.ahead_workers(2) == workers, room
                    stages.remakes_ahead(ahead, [(seed, "hub"), (seed, "base")])
                    assert (len(makes), stages.FAILED) == (made, set()), room
                    assert len(list(pathlib.Path(cache).rglob("ahead-*.json"))) == made, room
            # A remake hard-linking an input (the light rows' `cp -al` of their seed) is made beside the store's
            # cache, and an input no link reaches from there (another device) is copied: made in /tmp, every such
            # remake failed with EXDEV on the conductor and this PC and counted as moved (2026-11-07).
            stages.ROOM = lambda: 64 * 2**30
            real_link = os.link
            with tempfile.TemporaryDirectory() as cache, tempfile.TemporaryDirectory() as elsewhere:
                def device_link(source, target):
                    if str(source).startswith(cache) != str(target).startswith(cache):
                        raise OSError(errno.EXDEV, "Invalid cross-device link")
                    real_link(source, target)
                for there in (cache, elsewhere):
                    (pathlib.Path(there) / "seed").mkdir()
                    (pathlib.Path(there) / "seed/base.usda").write_text("ground")
                    stages.FAILED.clear()

                    def linking(inputs, out, seed, params):
                        os.link(pathlib.Path(inputs["seed"]) / "base.usda", out / "base.usda")
                    linked = types.SimpleNamespace(
                        store=types.SimpleNamespace(cache=cache, record=lambda node, key: None),
                        input_paths=lambda stage, place, keyed: {"seed": str(pathlib.Path(there) / "seed")})
                    row = dataclasses.replace(rows["earth-seed"], make=linking, contract=TOY)
                    with mock.patch.object(os, "link", device_link):
                        made = stages.made_again(linked, row, "hub", {"key": f"linked-{there == cache}", "seed": 0,
                                                                     "params": {}})
                    assert made is not None and "base.usda" in made["listing"], there
                    assert (pathlib.Path(there) / "seed/base.usda").read_text() == "ground"
                assert not any((pathlib.Path(cache) / "remaking").iterdir()), "the scratch is cleaned after"
        sound = rows["sound"]
        for moves, kept in (("m", True), ("m2", False)):
            runner.foreseen_listing = {"motion@hub": {"moves.json": moves, "layer.usda": "l2"}}
            assert (rebuy.to_make(runner, sound, "hub", ["motion@hub"], {"motion@hub": True}) is rebuy.KEPT) is kept
    finally:
        del stages.FORESIGHTS["terrain", "KT"]


LOOK = "person_uniform-made"
FACES = {row.name for row in stages.BODY_FACES}
WORN = {row.name for row in stages.STAGES if row.name.startswith("people-dress-") and "-in-" in row.name}
DRESS = next(row.name for row in stages.STAGES if row.name.startswith("people-dress-"))
PROP_ROUTE = {"closeup", "pixal"}
KIT = ["{data}/kit/{place}.json"]
# (row (a table row's name, or a dress row's (look, surface, variant)), field, relation, expected): what a row waits
# on, reads beside, declares and keys its neighbours by. A field is the row's own, "waits" every row it waits on
# through reads that are not optional, "files" what it declares for no place; "holds" every member of a set or item
# of a map, "lacks" each of a set, "==" the very value, "is" the very function
WIRED = [
    # light-layer@hub, 2026-10-23: read as optional, the face rows were in no place's line and the layer failed its
    # sky-elements gate with no face drawn
    ("light-layer", "after", "holds", FACES),
    ("light-layer", "optional", "lacks", FACES),
    # Buy of 2026-10-24: the scene palette, which the surface library and so the base read, waited on Pixal3D, so one
    # crashed close-up stopped the square's earth seed, scene record, light and tiles
    ("finish-route-palette", "optional", "holds", {"pixal"}),
    # every place the scene-record row writes a record for reads it beside for its surfaces-check's view distance
    ("surfaces-check", "beside", "==", {"scene-record": ("scene-record", 1)}),
    ("surfaces-check", "neighbours", "is", stages.own_record),
    # every place's cast, the ship's and the earth's alike, takes its views from its plan row, never a hand-written
    # record; it waits on each look worn in a fabric (the base's astronauts in white suits, 2026-11-04)
    ("cast", "after", "holds", {"plan": ("place-plan", 2), "scene-record": ("scene-record", 1)}),
    ("cast", "after", "holds", WORN),
    # Buy of 2026-10-24: through every read that is not optional, neither the earth seed nor the scene record reaches
    # the prop route's rows. The light rows do, on purpose since 2026-10-29: they light the place as the assembly lays
    # it, its bakes in (light/passes.LAID), so they wait on the bake as the assembly does
    ("earth-seed", "waits", "lacks", PROP_ROUTE),
    ("scene-record", "waits", "lacks", PROP_ROUTE),
    # recipes.py imports the vendored ProcFunc and Infinigen2 in Blender; a row declaring the library's code (the dress
    # rows: tools/props/library) declares both, so re-vendoring makes its bakes again
    (DRESS, "files", "holds", set(stages.VENDORED_RECIPES.values())),
    # the row a design would add for a look worn in a fabric carries the fabric, a person's own variant its number
    ((LOOK, "jacket_blue", 0), "params", "==", {"surface": "jacket_blue"}),
    ((LOOK, None, 1), "params", "==", {"variant": 1}),
    # owner, 2026-10-28 (a failing object remade once, free): pixal retakes a take his reject names
    ("pixal", "retakes", "==", True),
]
# Today's designs dress no line look in a fabric of its own, so the made-up world below dresses the uniformed look:
# in a blue jacket on the deck, in its own paint in the hold, as two persons in the hall; it writes a scene record for
# the hub alone (the dress row read where a design dresses its look so; captain, 2026-10-13: the concept decides the
# clothes, no hand-kept list of coloured places)
TOY_DRESSED = {"deck": {(LOOK, "jacket_blue", 0)}, "hold": {(LOOK, None, 0)},
               "hall": {(LOOK, None, 0), (LOOK, None, 1)}}
TOY_RECORDS = {"hub"}
# (world, row (a table row's name, a dress row's (look, surface, variant), or None for the table itself, or the cast
# stage's own module), the question asked of it, the place, its answer). Every place's cast, the ship's and the
# earth's alike, declares no old scene record (data/scene/<place>.json, the game's shots) and no views file under
# work/; its kit is its own place's, which earth_seeded reads from its earth seed once it has one (the design's kit,
# for its scene record): the sandbox home has none, so each declares its kit
PER_PLACE = [
    ("design", f"people-dress-{LOOK}", "applies", "tube", True),  # the tube's "person in uniform" names no fabric
    ("design", f"people-dress-{LOOK}", "applies", "square", False),
    ("design", None, "ship_place", "cockpit", True),  # by its place.json mark, on a home with no work folder
    ("design", None, "ship_place", "hub", False),
    ("toy", (LOOK, "jacket_blue", 0), "applies", "deck", True),
    ("toy", (LOOK, "jacket_blue", 0), "applies", "hold", False),
    ("toy", (LOOK, "jacket_blue", 0), "applies", "nowhere", False),
    ("toy", (LOOK, None, 0), "applies", "hold", True),
    ("toy", (LOOK, None, 0), "applies", "deck", False),
    ("toy", (LOOK, None, 1), "applies", "hall", True),  # a person's own variant where they stand
    ("toy", (LOOK, None, 1), "applies", "hold", False),
    ("toy", "surfaces-check", "neighbours", "hub", ["hub"]),
    ("toy", "surfaces-check", "neighbours", "cockpit", ["cockpit"]),  # a ship place reads its own still
    ("toy", "surfaces-check", "neighbours", "people", []),  # no scene record written: nothing to wait on
    *[("design", row, question, place, answer) for place in ("cockpit", "square", "hub")
      for row, question, answer in (("cast", "old records", []), ("cast", "kit", KIT), (stages.cast, "kit", KIT))],
]


def declared_paths(row, place):
    """The path patterns a row (or a stage module) declares for a place; a (path, part) pattern counts by its path."""
    return [str(pattern[0] if isinstance(pattern, tuple) else pattern) for pattern in row.files(place).values()]


def waits(table, name, seen=None):
    """Every row `name` waits on through reads that are not optional."""
    seen = set() if seen is None else seen
    for before in table[name].after:
        if before not in table[name].optional and before not in seen:
            seen.add(before)
            waits(table, before, seen)
    return seen


# what each PER_PLACE question asks of its row at a place
ASKED = {
    "applies": lambda row, place: bool(row.applies(place)),
    "ship_place": lambda row, place: bool(row.ship_place(place)),
    "neighbours": lambda row, place: row.neighbours(place),
    "kit": lambda row, place: [path for path in declared_paths(row, place) if path.startswith("{data}/kit")],
    "old records": lambda row, place: [path for path in declared_paths(row, place)
                                       if path.startswith("{data}/scene") or "world1-r4" in path],
}


def designed(store, place):
    """`place`'s design done in `store`: a concept locked, its scene inventory read from it and its plan written from
    that reading (plans.design_done)."""
    from score.review import concepts, plan_writing, reading
    sha = place.ljust(64, "0")
    concepts.recorded(store, f"concepts/{place}/picks/2026-10-20T09-00-00.json",
                      {"place": place, "sha": sha, "by": "joey", "at": "2026-10-20T09:00:00+00:00"})
    reading.kept(store, {"place": place, "concept": sha, "at": "2026-10-20T09:10:00+00:00", "method": reading.METHOD,
                         "inventory": {"rows": [{"id": "desk", "name": "desk", "count": 1}]}})
    plan_writing.kept(store, {"place": place, "concept": sha, "reading": "2026-10-20T09:10:00+00:00",
                              "method": plan_writing.METHOD, "at": "2026-10-20T09:30:00+00:00", "by": "test",
                              "euros": 0.0,
                              "plan": {"title": place.upper(), "w": 3.0, "d": 3.0, "items": [], "doors": []}})


def inputs_read(function):
    """The constant keys a function reads as inputs["<key>"]."""
    import ast
    tree = ast.parse(inspect.getsource(function))
    return {node.slice.value for node in ast.walk(tree) if isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name) and node.value.id == "inputs" and isinstance(node.slice, ast.Constant)}


@functools.cache
def parsed(path):
    return ast.parse(path.read_text(), str(path))


@functools.cache
def named_scripts(path):
    """The repository .py files a source file names by a string path (repository-relative, or beside the file): a
    nested Blender's --python, a cloud or env job's script, a subprocess of a repo script."""
    found = set()
    for node in ast.walk(parsed(path)):
        text = node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else ""
        if text.endswith(".py") and not text.startswith("/") and not any(each.isspace() or each in "{}" for each in text):
            found |= {candidate.resolve() for candidate in (REPO / text, path.parent / text)
                      if candidate.is_file() and _code.in_repo(candidate)}
    return found


@functools.cache
def started_imports(path):
    """What a script run apart imports: its repository imports and the files beside it it imports by bare name (a
    script run apart has its own folder on its path)."""
    beside = {path.parent / (name.split(".")[0] + ".py") for name in _code.imported_names(path.read_text(), path, "")}
    return _code.imports_of(path, pathlib.Path.is_file, pathlib.Path.read_text) | \
        {found.resolve() for found in beside if found.is_file()}


@functools.cache
def repo_declarations(path):
    """The repository paths a source file's "{repo}/..." patterns name (a declared folder holds its files)."""
    return {(REPO / node.value[len("{repo}/"):]).resolve() for node in ast.walk(parsed(path))
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("{repo}/")
            and node.value != "{repo}/"}  # a bare prefix is a path built at run time, no declaration


def files_sources(files):
    """The source files of a row's file map and of every function the stage table wrapped it round (closures), and
    the patterns of any literal map among them."""
    modules, patterns, pending = set(), [], [files]
    while pending:
        found = pending.pop()
        if isinstance(found, dict):
            patterns += list(found.values())
        elif callable(found) and hasattr(found, "__code__"):
            modules.add(pathlib.Path(inspect.getsourcefile(found)).resolve())
            pending += [cell.cell_contents for cell in found.__closure__ or ()]
    return modules, patterns


def unkeyed_scripts(row):
    """(script, the file naming or importing it) of every script the row's code starts by path, followed through
    what those import, that neither its code version nor a "{repo}/" declaration of its code or of the stage table
    (which wraps rows' files) keys. Static: a script built from parts at run time (`HERE / "gates" / "model.py"`)
    is not seen."""
    version = set(_code.source_files(graph.code_functions(row)))
    own, listed = files_sources(row.files)
    table = REPO / "score/stages/__init__.py"
    near = own.union(*(_code.live_imports(path) for path in own - {table})) | {table}
    declared = set().union(*map(repo_declarations, near)) | {
        (REPO / pattern[len("{repo}/"):]).resolve() for pattern in listed
        if isinstance(pattern, str) and pattern.startswith("{repo}/")}
    pending, seen, unkeyed = [(path, False) for path in version], set(version), set()
    while pending:
        path, started = pending.pop()
        if _code.in_framework(path, _code.FRAMEWORK):  # what runs a job, not what a job runs
            continue
        for script, its_start in [(found, True) for found in named_scripts(path)] + \
                [(found, True) for found in (started_imports(path) if started else ())]:
            if script in seen or _code.in_framework(script, _code.FRAMEWORK):
                continue
            seen.add(script)
            pending.append((script, its_start))
            if not any(script == folder or script.is_relative_to(folder) for folder in declared):
                unkeyed.add((script.relative_to(REPO).as_posix(), path.relative_to(REPO).as_posix()))
    return unkeyed


def left(row):
    """True for a row the table leaves without its started scripts declared (stages.STARTED_LEFT)."""
    return any(fnmatch.fnmatch(row.name, pattern) for pattern in stages.STARTED_LEFT)


# (row name pattern, the table's wrapper round its make): each row the table wraps keeps its code version as it was,
# and its make runs through the wrapper. The owner's reject retakes pixal's takes (retaking) and a look's parts at a
# new seed (parts_reseeded); a take the surface line left out is a batch gap of the likeness and of motion (leaving_out;
# motion@hangar, 2026-10-29: the crane's left-out take stopped `designed` on a missing object)
WRAPPED = [("people-look-parts-*", stages.parts_reseeded), ("pixal", stages.retaking),
           ("likeness", stages.leaving_out), ("motion", stages.leaving_out)]
# one place's hand-in, read by the likeness's left-out gaps and its lean gate: the crane's take left out for patchy
# paint, the hatch's not baked, the counter's named alone by a split gap, the crate with no gap
HANDIN = {"objects": {"crane": {"route": "prop", "take": "crane_7", "rows": ["crane"]},
                      "hatch": {"route": "prop", "take": "hatch_2"},
                      "counter": {"route": "prop", "take": "counter_7", "rows": ["counter"]},
                      "crate": {"route": "prop", "take": "crate_2"}}}


# --- a scenes layers are read off its design, and a rows kind comes from its own words ---

KINDS = {"person": {"nouns": ["astronaut", "crowd"], "does": ["acts"]},
         "kettle": {"nouns": ["kettle"], "does": ["emits", "loose"]},
         "door": {"nouns": ["door"], "does": ["moves"]}, "vehicle": {"nouns": ["rover"], "does": ["moves"]},
         "plant": {"nouns": ["plant", "plants", "planter", "rack"], "does": ["grows"]},
         "loose": {"nouns": ["chair"], "does": ["loose"]}}
RULES = {"door": {"nouns": ["door", "hatch"], "does": ["moves"]},
         "kettle": {"nouns": ["kettle"], "does": ["emits", "loose"]},
         "loose": {"nouns": ["chair", "cylinder"], "does": ["loose"]}}
LAMPS = {"lamp": {"nouns": ["light", "floodlight"], "does": ["glows"], "held_by": ["tower", "frame", "post"]}}
PLATES = {"loose": {"nouns": ["plate"], "does": ["loose"]}}
HOUSE = "the house rules"  # data/checks/row-kinds.json, read in the test


def row(row_id, noun, kind="generate", anchor="floor"):
    return {"id": row_id, "noun": noun, "kind": kind, "anchor": anchor}


def named(name, noun):
    """A row read from a scene's words, its id its name's."""
    return {"id": name.replace(" ", "_"), "name": name, "noun": noun}


HOLE = {"id": "doorway", "name": "doorway", "noun": "door", "part": "opening"}  # workshop's doorway (2026-10-30)
SWING = {"id": "doorway", "name": "closed metal door", "noun": "door", "part": "structure"}  # hangar's
INVENTORY = {"rows": [{"id": "kettle", "noun": "kettle"}, {"id": "stool", "noun": "chair"},
                      {"id": "front_door", "noun": "door"}, {"id": "wall", "noun": "wall"}]}
SCENE = {"rows": [row("planter", "planter") | {"count": 11}, row("greens", "plants", anchor="on:planter") | {"count": 5},
                  row("pot", "plant") | {"count": 2}, row("desk", "desk")]}
EMPTY_PLANTS = {"rows": 0, "objects": 0, "crops": 0, "beds": 0}
ONE_PLANT = {"rows": 1, "objects": 1, "crops": 0, "beds": 0}

STAR = {"body": "star", "name": "Star", "kelvin": 5772.0, "radius_km": 695700.0}
AU = 149597870.7


def world(name, kpa, distance_km, around="star"):
    return {"body": name, "name": name.title(), "around": around, "distance_km": distance_km,
            "surface_pressure_kpa": kpa}


def person(name, row_id="row"):
    """A people row of the deck as a design names it."""
    return {"id": row_id, "name": name, "noun": "person"}


# made-up worlds round a 5772 K star (the module docstring works out their zero-albedo temperatures by hand)
WET, HOT = world("wet", 101.3, AU), world("hot", 101.3, 0.2 * AU)
FROZEN, WINDY = world("frozen", 0.0, 5.2 * AU), world("windy", 0.6, 1.52 * AU)
AIRLESS = world("airless", 0.0, 384400.0, around="wet")  # a moon: its planet's distance from the star
BODIES = [STAR, WET, HOT, FROZEN, WINDY, AIRLESS]
UNPRESSED = {"body": "x", "name": "X", "around": "star", "distance_km": AU}

# (case, judge, what it reads, its answer): a row's kind, a scene's layers, its plants, the rows picked by what their
# kind does, a person's look and a natural ground, each read off the words and design (and a ground's physics) alone;
# HOUSE among what it reads stands for the house rules
JUDGED = [
    # the noun decides before the name; with no noun the name's last word; a two-word noun is matched whole
    ("door panel is a panel", row_kinds.kind_of, ({"id": "door_panel", "name": "door panel", "noun": "panel"}, RULES),
     None),
    ("airlock door", row_kinds.kind_of, (named("airlock door", "door"), RULES), "door"),
    ("gas cylinder by its name", row_kinds.kind_of, ({"id": "gas_cylinder", "name": "gas cylinder"}, RULES), "loose"),
    ("round hatch by its id", row_kinds.kind_of, ({"id": "round_hatch"}, RULES), "door"),
    ("floor plate is no plate", row_kinds.kind_of, (named("floor plate", "floor plate"), PLATES), None),
    # an opening is a hole that does nothing of its noun; a door read as structure still swings
    ("opening is no door", row_kinds.kind_of, (HOLE, RULES), None),
    ("structure door swings", row_kinds.kind_of, (SWING, RULES), "door"),
    ("opening moves nothing", row_kinds.rows_that, ({"rows": [HOLE]}, "moves", RULES), []),
    ("opening gives no motion", design_layers.kinds_of, ({"rows": [HOLE]}, RULES), {"light", "sound"}),
    ("structure door gives motion", design_layers.kinds_of, ({"rows": [SWING]}, RULES), {"motion", "light", "sound"}),
    # a lamp read as what holds it is still a lamp; a switch and a fence post are none
    ("floodlight tower", row_kinds.kind_of, (named("floodlight tower", "tower"), LAMPS), "lamp"),
    ("grow light frame", row_kinds.kind_of, ({"id": "grow_light_frame", "noun": "frame"}, LAMPS), "lamp"),
    ("light switch", row_kinds.kind_of, (named("light switch", "switch"), LAMPS), None),
    ("fence post", row_kinds.kind_of, (named("fence post", "post"), LAMPS), None),
    # a scene's rows are picked by what their kind does, and a kind can do more than one thing
    ("loose rows", row_kinds.rows_that, (INVENTORY, "loose", RULES),
     [{"id": "kettle", "noun": "kettle", "row_kind": "kettle"}, {"id": "stool", "noun": "chair", "row_kind": "loose"}]),
    ("emitting rows", row_kinds.rows_that, (INVENTORY, "emits", RULES),
     [{"id": "kettle", "noun": "kettle", "row_kind": "kettle"}]),
    ("moving rows", row_kinds.rows_that, (INVENTORY, "moves", RULES),
     [{"id": "front_door", "noun": "door", "row_kind": "door"}]),
    # the house rules read real words
    *[(f"house: {name}", row_kinds.kind_of, (named(name, noun), HOUSE), kind) for name, noun, kind in (
        ("stove", "stove", "cooker"), ("table lamp", "lamp", "lamp"), ("tracked rover", "rover", "vehicle"),
        ("ceiling light", "light", "lamp"), ("dining chair", "chair", "loose"), ("tv", "tv", "screen"),
        ("laptop", "laptop", "computer"), ("planter bed", "planter", "plant"), ("hatch", "hatch", "door"),
        ("door mat", "mat", None), ("outer wall", "wall", None))],
    # each row shows the layer its kind does: a kettle emits and is loose, a rover and a door built as code move, a
    # crowd acts, and a bare room still has its light and sound
    ("kettle", design_layers.kinds_of, ({"rows": [row("kettle", "kettle")]}, KINDS),
     {"effects", "physics", "light", "sound"}),
    ("rover", design_layers.kinds_of, ({"rows": [row("rover", "rover")]}, KINDS), {"motion", "light", "sound"}),
    ("code door", design_layers.kinds_of, ({"rows": [row("door", "door", kind="code")]}, KINDS),
     {"motion", "light", "sound"}),
    ("crowd", design_layers.kinds_of, ({"rows": [row("crowd", "crowd")]}, KINDS), {"people", "light", "sound"}),
    ("bare room", design_layers.kinds_of, ({"rows": [row("wall", "wall", kind="code")]}, KINDS), {"light", "sound"}),
    # crops are plants on a raised planter (a row that grows itself), on a rack, or on a bed by its noun; a potted
    # plant on the floor or on a desk is not
    ("plants on a planter", design_layers.kinds_of,
     ({"rows": [row("planter", "planter"), row("greens", "plants", anchor="on:planter")]}, KINDS),
     {"crops", "light", "sound"}),
    ("plants on a rack", design_layers.kinds_of,
     ({"rows": [row("rack", "rack"), row("greens", "plants", anchor="on:rack")]}, KINDS), {"crops", "light", "sound"}),
    ("plants on a bed", design_layers.kinds_of,
     ({"rows": [row("bed", "bed", kind="code"), row("greens", "plants", anchor="on:bed")]}, KINDS),
     {"crops", "light", "sound"}),
    ("potted plants", design_layers.kinds_of,
     ({"rows": [row("desk", "desk"), row("pot", "plant", anchor="on:desk"), row("fern", "plant")]}, KINDS),
     {"light", "sound"}),
    # plants are every growing row, and the planter under crops is their bed
    ("plants and beds", design_layers.plants_of, (SCENE, KINDS), {"rows": 2, "objects": 7, "crops": 1, "beds": 11}),
    ("no plants", design_layers.plants_of, ({"rows": [row("desk", "desk")]}, KINDS), EMPTY_PLANTS),
    *[(f"house plant: {noun}", design_layers.plants_of, ({"rows": [row("green", noun)]}, HOUSE), ONE_PLANT)
      for noun in ("tree", "palm", "shrub", "bush", "moss", "fern", "flower")],
    # one body a look (owner, 2026-10-22): a row's words before where it stands or what it holds, its pose and colour
    # words left out (its clip and its dress vary it); a garment its who wears, or that says who wears it, is no look
    *[(f"look: {name}", people_rows.look_of, ("deck", person(name), False), look) for name, look in (
        ("seated astronaut", "astronaut-made"), ("astronaut standing", "astronaut-made"),
        ("astronauts", "astronaut-made"), ("astronaut in white suit", "astronaut-made"),
        ("astronaut in spacesuit", "astronaut-made"), ("person in spacesuit", "astronaut-made"),
        ("person sitting at a table", "person-made"), ("people on walkway", "person-made"),
        ("person holding an umbrella", "person-made"), ("person", "person-made"),
        ("worker in blue jumpsuit", "worker_jumpsuit-made"), ("worker in grey jumpsuit", "worker_jumpsuit-made"),
        ("person in uniform", "person_uniform-made"))],
    # a crowd's look by who it is; a named person or the player is a look of its own
    ("look: crowd of people", people_rows.look_of, ("deck", person("crowd of people"), True), "crowd-made"),
    ("look: crowd of aliens", people_rows.look_of, ("deck", person("crowd of aliens"), True), "alien-made"),
    ("look: the player", people_rows.look_of, ("deck", person("the player in a work suit", "hero"), False),
     "deck_hero-made"),
    ("look: Nev", people_rows.look_of, ("deck", person("Nev at the console", "hero"), False), "deck_hero-made"),
    # a body's ground by its physics against water's phases, never its name
    ("ground: wet", natural_grounds.of_body, (WET, BODIES, {}),
     ("ocean", "Wet: 101 kPa, 278 K at zero albedo: liquid water stands (boiling at 373 K there)")),
    ("ground: hot", natural_grounds.of_body, (HOT, BODIES, {}),
     ("rock", "Hot: 101 kPa, 622 K at zero albedo: over water's boiling at 373 K there, dry to the rock")),
    ("ground: frozen", natural_grounds.of_body, (FROZEN, BODIES, {}),
     ("ice", "Frozen: 0 kPa, 122 K at zero albedo: under 150 K, water ice lasts")),
    ("ground: windy", natural_grounds.of_body, (WINDY, BODIES, {}),
     ("sand", "Windy: 0.6 kPa, 226 K at zero albedo: an air of at least 0.1 kPa drifts its dust")),
    ("ground: airless moon", natural_grounds.of_body, (AIRLESS, BODIES, {}),
     ("regolith", "Airless: 0 kPa, 278 K at zero albedo: airless, its dust ground by impacts")),
    # a body with no pressure is named so, unless the reference table holds the value the setting lacks
    ("ground: no pressure", natural_grounds.of_body, (UNPRESSED, [STAR], {}),
     (None, "X: no surface pressure in the setting")),
    ("ground: the table's pressure", natural_grounds.of_body,
     (UNPRESSED, [STAR], {"bodies": {"x": {"surface_pressure_kpa": 0.0}}}),
     ("regolith", "X: 0 kPa, 278 K at zero albedo: airless, its dust ground by impacts")),
    # a row's words come first; a made ground's word is no natural one; with no words, its body's physics
    ("ground: red dunes", natural_grounds.of_row, ({"id": "dunes", "name": "red dunes", "noun": "ground"}, None, [], {}),
     ("sand", "the row dunes says dunes")),
    ("ground: sea", natural_grounds.of_row, ({"id": "sea", "noun": "sea"}, WINDY, [STAR, WINDY], {}),
     ("ocean", "the row sea says sea")),
    ("ground: plaza", natural_grounds.of_row, ({"id": "plaza", "name": "main plaza", "noun": "plaza"}, WINDY,
                                               [STAR, WINDY], {}),
     (None, "the row plaza says plaza: a made ground, no natural one")),
    ("ground: martian ground", natural_grounds.of_row,
     ({"id": "g", "name": "martian ground", "noun": "ground"}, WINDY, [STAR, WINDY], {}),
     ("sand", "Windy: 0.6 kPa, 226 K at zero albedo: an air of at least 0.1 kPa drifts its dust")),
    ("ground: a plot", natural_grounds.of_row, ({"id": "g", "noun": "ground"}, None, [], {}),
     (None, "the row g names no ground and stands on no body of the setting")),
]

# a place has a layer only by its kept design: the shed keeps one astronaut, the hangar every layer kind, the barn none
KEPT = {"shed": {"rows": [row("pilot", "astronaut")]},
        "hangar": {"rows": [row("pilot", "astronaut"), row("kettle", "kettle"), row("hatch", "door", kind="code"),
                            row("planter", "planter"), row("greens", "plants", anchor="on:planter")]}}
HAS_LAYER = [("shed", "people", True), ("shed", "light", True), ("shed", "effects", False),
             ("barn", "light", False), (None, "sound", False)]


def test_each_row_keys_waits_and_moves_only_by_its_design_and_gaps(tmp_path, monkeypatch):
    """Each row's kind, a person's look and a natural ground are read off its own words (a ground then its body's
    physics) and each scene's layers off its kept design, and the stage table holds a row for exactly the layers the
    assembly's gate waits on; a row's objects are found outside the layers' scopes, anything else a stranger. An
    accepted gap moves only the faults it names and is read only by complete and the row it names; complete fails
    each by name, and an owner's gap is never dropped unless retired on a passing output. A failed paid take is a gap
    carried down its line. The push gate names the paid rows a change moves, refuses a push to main only for those no
    trailer names, and its hook runs the check from the right checkout, home and python and leaves nothing behind.
    A row's code version moves with its own code alone, and a Claude ask cut short is never a row's output; each row waits on, reads beside and applies where its design and its reads
    say, and no base row waits on the prop route. A row's key holds every script it starts; a place is a scene whose
    design is done, a parent before its children; a take the owner rejected is set aside once and retaken, and one
    the surface line left out is a batch gap by its reason, never a missing model."""
    from score.stages import assembly
    for edited, asked, moving in KEYED:
        scope = [stage for stage in stages.STAGES if any(fnmatch.fnmatch(stage.name, name) for name in asked)]
        assert scope, (edited, asked)
        found = {stage.name for stage in scope
                 if code_after_editing(stage, edited) != code_after_editing(stage, "nothing")}
        assert found == ({stage.name for stage in scope} if moving == EVERY else moving), (edited, asked, found)
    # a script a row's make starts by path (a nested Blender's --python, a cloud or env job's script, a subprocess of
    # a repo script) is run apart, so no import keys it: it is a declared file of the row, with every file it imports,
    # or an output accepted on old code stays (make_chunky's bake scripts' recipes.py, 2026-10-28); a STARTED_LEFT
    # row, left because its re-make would buy again in the cloud, still has one (else it leaves the list)
    started = {(stage.name, script, by) for stage in stages.STAGES for script, by in unkeyed_scripts(stage)
               if "{repo}/" + script not in getattr(stage.files, "started", dict)()}
    unkeyed = [f"{name}: {script} (named by {by})" for name, script, by in sorted(started)
               if not left(next(stage for stage in stages.STAGES if stage.name == name))]
    assert not unkeyed, "scripts run apart that no key follows (declare them in the row's files):\n" + "\n".join(unkeyed)
    unheld = [stage.name for stage in stages.STAGES if left(stage) and not any(name == stage.name
                                                                               for name, _, _ in started)]
    assert not unheld, f"STARTED_LEFT rows with nothing left undeclared: {unheld}"
    # a row the table wraps keeps its code version as it was, and its make runs through the wrapper
    for pattern, wrapper in WRAPPED:
        wrapped = next(stage for stage in stages.STAGES if fnmatch.fnmatch(stage.name, pattern))
        assert graph.stage_code(wrapped) == graph.stage_code(dataclasses.replace(wrapped,
                                                                                 make=inspect.unwrap(wrapped.make)))
        chain, make = [], wrapped.make
        while make is not None:
            chain.append(getattr(make, "__code__", None))
            make = getattr(make, "__wrapped__", None)
        assert wrapper(len).__code__ in chain, (pattern, wrapper.__name__)
    # the claude rows hold their ask's own code; the plan row is the scene record's plan step as it stands (its code
    # version kept), reading no kit: its files are the step's own
    for stage in (stage for stage in stages.STAGES if stage.name.split("@")[0] in claude_asks.ROWS):
        own = _code.start_files(graph.code_functions(stage))
        assert REPO / "score/stages/surfaces/claude_asks.py" in own, stage.name
    plain = graph.Stage("plan", "place", stages.scene_record.plan.make, stages.scene_record.plan.PLACE_PLAN,
                        stages.scene_record.plan.CHECKS, files=stages.scene_record.plan.files)
    assert code_after_editing(stages.PLAN, "nothing") == code_after_editing(plain, "nothing")
    assert stages.earth_seed.locked_plan("launch") is None
    assert stages.PLAN.files("launch") == stages.scene_record.plan.files("launch")
    assert "kit" not in stages.PLAN.files("launch")
    # with no kit laid, the plan row's make names the place by its plan and its `mapped` gate judges it; made again on
    # a moved key (another place's plan redrawn) it is the same output while its own plan stands, so its readers key
    # as before; its own plan redrawn, it is not, and the remake that differs is foreseen, so the rows reading what it
    # kept (the floor, carry.CONTENT_RULES) keep
    drawn = tmp_path / "plan_row"
    (drawn / "plans").mkdir(parents=True)
    (drawn / "out").mkdir()
    plan = {"title": "NEW ROOM", "w": 3.0, "d": 3.0, "corner": 0.0, "height": "walls 2.5 m", "doors": [],
            "items": [["DESK", 1.0, 1.0, 1.0, 0.6, "S", "item"]], "rows": {"DESK": ["desk"]}, "leads": {},
            "elements": [{"element": "a desk", "rows": ["desk"]}, {"element": "a poster", "drop": "printed"}]}
    (drawn / "plans/new_room.json").write_text(json.dumps(plan))
    (drawn / "inventory.json").write_text(json.dumps({"rows": [{"id": "desk"}], "room": {"layout": {}}}))
    plan_inputs = {"plan": str(drawn / "plans/new_room.json"), "inventory": str(drawn / "inventory.json"),
                   "plans": str(drawn / "plans")}
    stages.PLAN.make(plan_inputs, drawn / "out", 0, {})
    assert json.loads((drawn / "out/plan.json").read_text())["place"] == "new_room"
    verdict = stages.PLAN.checks[0].judge(drawn / "out", plan_inputs, {})
    assert verdict.answer == checks.PASS, verdict.reason
    contracts.stamp(stages.PLAN.contract, drawn / "out")
    plan_output = store_tree_hash(drawn / "out")
    planner = types.SimpleNamespace(store=types.SimpleNamespace(accepted=lambda node: plan_output),
                                    input_paths=lambda stage, place, keyed: plan_inputs, foreseen={})
    assert stages.PLAN.files.carries(planner, stages.PLAN, "new_room", {"seed": 0, "params": {}})
    assert planner.foreseen == {}
    (drawn / "plans/new_room.json").write_text(json.dumps({**plan, "w": 4.0}))
    assert not stages.PLAN.files.carries(planner, stages.PLAN, "new_room", {"seed": 0, "params": {}})
    assert planner.foreseen["plan@new_room"]["plan.json"]["place"] == "new_room"
    table = {stage.name: stage for stage in stages.STAGES}
    assert all(hasattr(table[name].files, "same_reads") for name in ("rough-model", "rough-align"))
    assert hasattr(table["props-inputs"].files, "carries")

    # the table wires each row to wait on, read beside, declare and apply where its design and its reads say
    from score.stages import people

    def row_of(name):
        return (stages if name is None else table[name] if isinstance(name, str)
                else stages.worn(people.dress_row(*name)) if isinstance(name, tuple) else name)
    for name, field, relation, expected in WIRED:
        value = (waits(table, name) if field == "waits" else set(row_of(name).files(None).values())
                 if field == "files" else getattr(row_of(name), field))
        if relation == "is":
            assert value is expected, (name, field, value)
            continue
        assert expected, (name, field, "the case names nothing")
        if relation == "==":
            assert value == expected, (name, field, value)
        elif relation == "lacks":
            assert not set(expected) & set(value), (name, field, set(expected) & set(value))
        else:
            assert (expected.items() <= dict(value).items() if isinstance(expected, dict)
                    else set(expected) <= set(value)), (name, field, value)
    # surfaces-check hands check_step every key it reads (the crops' twin's stance rules were missing, 2026-10-16:
    # KeyError at greenhouse), shortened as the prop environment hands them over (prop_env.short); only the keys
    # matter: a declared file may be (path, part), the part the runner reads
    bake_check, prop_env = sys.modules["bake_check"], sys.modules["prop_env"]
    read = inputs_read(bake_check.check_step) | inputs_read(bake_check.data_of)
    handed = prop_env.short(dict.fromkeys([*table["surfaces-check"].files("greenhouse"),
                                           *table["surfaces-check"].after], "."))
    assert read <= set(handed), read - set(handed)
    # the table and the data name only what stands: every motion layer pattern a row of the table, no row under the
    # old machines name (the motion layer's models now), and no environment data file a path into the work folder,
    # which is no store (it went with the old disk, 2026-10-19; the last ones went with the old hand-ins, 2026-10-21)
    empty = [pattern for patterns in stages.MOTION_LAYER.values() for pattern in patterns
             if not fnmatch.filter(table, pattern)]
    assert not empty, f"motion layer patterns that name no row of the table: {empty}"
    old = [name for name in table if name.startswith("machines")]
    assert not old, f"rows under the old machines name (the motion layer's models now): {old}"
    into_work = subprocess.run(["git", "grep", "-l", "-E", r"\{home\}/work/|score-coordinator", "--", "data"],
                               cwd=REPO, capture_output=True, text=True).stdout.split()
    assert not into_work, f"paths into the work folder (make them a row's output, or a gap): {into_work}"
    assert not (PROPS_HOME / "work/usd-ship/cockpit").exists()
    for world in ("design", "toy"):
        with contextlib.ExitStack() as patches:
            if world == "toy":
                patches.enter_context(mock.patch.object(stages.characters_layer, "dressed_looks",
                                                        lambda place: TOY_DRESSED.get(place, set())))
                patches.enter_context(mock.patch.object(stages.scene_record, "written",
                                                        lambda place: place in TOY_RECORDS))
            for case_world, name, question, place, answer in PER_PLACE:
                if case_world == world:
                    found = ASKED[question](row_of(name), place)
                    assert found == answer, (world, name, question, place, found)
    # a worn row of the table carries the fabric and variant its name says
    for name in WORN:
        _, surface, variant = stages.characters_layer.dressed_of(name)
        assert table[name].params == {"surface": surface, **({"variant": variant} if variant else {})}, \
            (name, table[name].params)

    # a place is a scene of the design whose concept is locked, its inventory read and its plan written (no filed kit
    # or plan names one since 2026-10-21); one only drawn is still in design, and a scene merged into another or a
    # part of another scene's outside has no line (the scene it is part of builds it, the owner, 2026-10-21)
    root = tmp_path / "places_world"
    store = Store.in_folder(root / "store")
    for part in ("kit/old.json", "plans/old.json"):
        (root / part).parent.mkdir(parents=True, exist_ok=True)
        (root / part).write_text("{}")
    designed(store, "laid")
    designed(store, "new")
    from score.review import concepts
    concepts.recorded(store, "concepts/drawn/draws/2026-10-20T08-00-00.json",
                      {"place": "drawn", "sha": "d" * 64, "by": "joey", "at": "2026-10-20T08:00:00+00:00"})
    environment = graph.Environment("world1", 3, {"data": str(root)})
    within = root / "places/within.json"
    for written_within, listed in ((None, ["laid", "new"]), ({"merged": {"new": {"into": "laid"}}}, ["laid"]),
                                   ({"parts": {"new": {"of": "laid", "as": "far off"}}}, ["laid"])):
        if written_within is not None:
            within.parent.mkdir(exist_ok=True)
            within.write_text(json.dumps(written_within))
        assert stages.places(environment, store) == listed, written_within
    # scene-tree@<scene> reads its own assembly and, beside, the tree of each child scene its plan lays out that is a
    # scene of the batch (one in design is none: the tree's gate names it); a place of every scene but a line no
    # place owns; the library reads it, so a scene is complete once its tree stands
    tree_row = table["scene-tree"]
    assert tree_row.downward and tree_row.after == {"assembly": ("openusd-stage", 1)}
    assert tree_row.beside == {"scene-tree": ("openusd-stage", 1)} and tree_row.neighbours is stages.held_scenes
    assert not tree_row.applies("people") and tree_row.applies("hangar") and "scene-tree" in table["library"].after
    # the batch's places are listed once a moment, however many rows' reads ask (filmed_places), and kept across
    # moments until a file or folder the listing read changes
    listings = []
    with monkeypatch.context() as patch:
        patch.setattr(stages.scene_tree, "held", lambda place: {"base": ["hangar", "lab", "dome"]}.get(place, []))
        patch.setattr(stages, "places", lambda world, store=None: listings.append(1) or ["base", "hangar", "lab"])
        patch.setattr(stages, "world1", lambda: None)
        patch.setattr(stages.demo_film_final, "shown_places", lambda place=None: ["lab", "dome"])
        patch.setattr(stages.demo_film_final, "peeled_places", lambda place=None: ["hangar"])
        assert stages.held_scenes("base") == ["hangar", "lab"] and stages.held_scenes("lab") == []
        stages.KEPT_LISTINGS.clear()
        try:
            with stages.plans.one_moment():
                assert stages.filmed_places() == ["hangar", "lab"] and stages.filmed_places() == ["hangar", "lab"]
                assert stages.held_scenes("base") == ["hangar", "lab"] and len(listings) == 2, listings
            with stages.plans.one_moment():  # the next moment: nothing the listing read changed (it read nothing)
                assert stages.held_scenes("base") == ["hangar", "lab"] and len(listings) == 2, listings
        finally:
            stages.KEPT_LISTINGS.clear()
    # a listing reading the places world's within.json and its folder of plans, as places() does
    records, listed_again = root / "plans" / "base" / "edits", []
    records.mkdir(parents=True)

    def listing():
        listed_again.append(1)
        return (within.read_text() if within.exists() else None,
                sorted(path.name for path in (root / "plans").rglob("*")))
    try:
        first = stages.kept_while_read_stands("toy", listing)
        (root / "unread.txt").write_text("a write beside, never read")
        assert stages.kept_while_read_stands("toy", listing) is first and len(listed_again) == 1, \
            "read again though nothing changed"
        for change in (lambda: within.write_text('{"merged": {}}'), lambda: (records / "e1.json").write_text("{}"),
                       lambda: (root / "plans" / "lab").mkdir(), within.unlink):
            change()
            stages.kept_while_read_stands("toy", listing)
        assert len(listed_again) == 5, \
            f"a changed file, a new record, a new place's folder or a gone file kept the listing: {listed_again}"
        assert stages.kept_while_read_stands("toy", listing) == (
            None, ["base", "e1.json", "edits", "lab", "old.json"]) and len(listed_again) == 5
    finally:
        stages.KEPT_LISTINGS.clear()
    # a parent scene comes before its children
    assert stages.parent_first({"cockpit", "hangar", "base", "hub", "wreck", "camp"},
                               {"cockpit": "hangar", "hangar": "base", "hub": "base", "camp": "campgrounds"}) == [
        "base", "hangar", "cockpit", "hub", "camp", "wreck"]

    # a Claude ask whose stream ends without its result line is never the row's output: the make raises AskBroken (a
    # ConnectionError), the adapter keeps nothing and a later run asks again, while a real answer is kept and read
    # back and the model's own "no structured answer" stays the take's gap (surface-library@galley, 2026-11-12, was
    # kept as a fail and never asked again)
    from score.adapters.models import claude_code
    with monkeypatch.context() as patch:  # subprocess.run is everyone's: the git calls below run unpatched
        patch.setattr(claude_code, "CACHE", tmp_path / "asks")
        patch.setattr(claude_code, "LEDGER", tmp_path / "ledger.jsonl")
        patch.setattr(claude_code.shutil, "which", lambda name: "/usr/bin/claude")
        cut = json.dumps({"type": "assistant", "request_id": "req_cut", "message": {"content": []}})
        streams = {"kept": json.dumps({"type": "result", "is_error": False, "structured_output": {"surfaces": []},
                                       "usage": {}}), "cut": cut,
                   "unstructured": json.dumps({"type": "result", "is_error": True,
                                               "subtype": "error_during_execution", "result": "schema not met"})}
        patch.setattr(claude_code.subprocess, "run", lambda command, input, **_: subprocess.CompletedProcess(
            command, 0, streams[json.loads(input)["message"]["content"][0]["text"]] + "\n", ""))

        def asking(inputs, out, seed, params):
            out.update(claude_code.asked({text: {"contents": [{"parts": [{"text": text}]}], "generationConfig": {
                "responseSchema": {"type": "OBJECT", "properties": {}}}} for text in inputs}, "surface-library"))
        asked = {}
        stages.unbroken_asks(asking)(["kept", "unstructured"], asked, 0, {})
        answer = json.dumps({"surfaces": []})
        assert asked["kept"] == answer and isinstance(asked["unstructured"], claude_code.Unanswered)
        assert [path.read_text() for path in (tmp_path / "asks").iterdir()] == [asked["kept"]]
        with pytest.raises(stages.AskBroken, match="no result line"):
            stages.unbroken_asks(asking)(["kept", "cut"], {}, 0, {})
        assert len(list((tmp_path / "asks").iterdir())) == 1 and claude_code.asked.__name__ == "asked"
        streams["kept"] = cut  # read back from the cache, never asked again
        assert stages.unbroken_asks(asking)(["kept"], asked, 0, {}) is None and asked["kept"] == answer

    house = row_kinds.table()
    for case, judge, read, answer in JUDGED:
        assert judge(*(house if value is HOUSE else value for value in read)) == answer, case

    monkeypatch.setattr(design_layers, "KEPT", tmp_path)
    for place, design in KEPT.items():
        (tmp_path / f"{place}.json").write_text(json.dumps(design))
    for place, layer, has in HAS_LAYER:
        assert design_layers.has_layer(place, layer) is has, (place, layer)
    needed = assembly.needed_layers(KEPT["hangar"], house)
    rows = {stage.name for stage in stages.STAGES if stage.grain == "place" and stage.name in assembly.NEEDS.values()
            and stage.applies is not None and stage.applies("hangar")}
    assert needed == ["characters-layer", "crops-layer", "effects-layer", "motion", "settle", "light", "sound"]
    assert rows == set(needed), rows

    stage = Usd.Stage.CreateInMemory()
    for path in ("/toy", "/toy/Fixtures", "/toy/Fixtures/door_1", "/toy/Fixtures/door_1/door_1", "/toy/Objects",
                 "/toy/Objects/door_2", "/toy/Objects/door_frame_1", "/toy/Effects", "/toy/Effects/door_3"):
        UsdGeom.Xform.Define(stage, path)
    for scene, noun, found in (("toy", "door", ["/toy/Fixtures/door_1", "/toy/Objects/door_2"]), ("toy", "window", []),
                               ("elsewhere", "door", [])):
        assert row_kinds.objects_of(stage, scene, noun) == found, (scene, noun)
    assert row_kinds.strangers(["Objects/door_2", "Objects/kettle", "Objects/door_frame_1", "Objects/doormat"],
                               {"rows": [{"id": "door"}, {"id": "kettle"}]}) == ["Objects/door_frame_1",
                                                                                "Objects/doormat"]

    # an accepted gap moves only its named faults, keeping its findings; anything else is left as it was
    for case, verdict, found, answer, said in MOVED:
        kept = gaps.moved(verdict, found)
        if answer is None:
            assert kept == verdict, (case, kept)
            continue
        assert (kept.answer, kept.findings) == (answer, verdict.findings) and found[0]["name"] in kept.reason, \
            (case, kept)
        if answer == checks.FAIL:  # still failing, the gap of its own faults named beside the other fault
            assert kept.measures == verdict.measures and kept.reason.startswith(verdict.reason), (case, kept)
        else:
            assert kept.measures["moved"] == said, (case, kept)
    for case, after, lost in DROPPED:
        assert dropped({"garage": {"gaps": [PIPE]}}, after) == lost, case
    # an owner's gap stays in the tree's own records since the commit it branched from main
    base = subprocess.run(["git", "merge-base", "HEAD", "origin/main"], cwd=REPO, capture_output=True, text=True)
    commit = base.stdout.strip() if base.returncode == 0 else "HEAD"
    tree = {path.stem: json.loads(path.read_text()) for path in sorted((REPO / "data/checks/gaps").glob("*.json"))}
    assert dropped(git_gaps(commit), tree) == [], f"owner's gaps dropped since {commit[:12]}"

    # the owner's decision files of four places, each read by its row and check
    with decided({"wreck": [RESTING, ORDER], "street": [NAMED_UNKNOWN], "campgrounds": [CRANE],
                  "lab": [entry("chairs", "assembly", "placeholders", ["chair_1"], [])]}):
        assert gaps.entries(recorded("wreck"), "assembly", "resting") == [RESTING]
        for place, name, reads in GAP_READERS:
            assert (gaps.NAME in ROWS[name].files(place)) is reads, (place, name)
        assert not gaps.files("nowhere") and not gaps.files("nowhere", "assembly")
        crane = gaps.judge_accepted(None, recorded("campgrounds"), None)
        crane_people = people_gaps.judge_accepted(None, recorded("campgrounds"), None)
    # complete fails each accepted gap by name with its numbers, and its people gate gives the same answer
    assert crane.answer == checks.FAIL and CRANE["name"] in crane.reason
    assert crane.findings == ("crane: a foot off the floor: /campgrounds/Objects/crane_1: foot 2 3.2 cm off the floor",)
    assert (crane_people.answer, crane_people.reason, crane_people.findings) == (crane.answer, crane.reason,
                                                                                 crane.findings)
    assert gaps.judge_accepted(None, {}, None).answer == checks.PASS
    # a gap a row it reads wrote in its own output is listed by name
    (tmp_path / "neighbours").mkdir()
    (tmp_path / "neighbours" / gaps.WRITTEN).write_text(json.dumps({"gaps": [FAR_CITY]}))
    lost = gaps.judge_accepted(None, {"neighbours": tmp_path / "neighbours"}, None)
    assert lost.answer == checks.FAIL and FAR_CITY["name"] in lost.reason, lost
    # complete's people gate leaves out a batch gap of the place's own take of a people row alone, never one naming
    # another object too (cockpit, 2026-11-12: the pilot's and officer's takes were two of eleven gap objects)
    handin = written(tmp_path, "handin.json", {
        "rows": [{"id": "pilot", "route": "people"}, {"id": "seat", "route": "prop"}],
        "objects": {"pilot": {"take": "toy_pilot_1", "rows": ["pilot"]}, "seat": {"take": "toy_seat_1", "rows": ["seat"]}},
        "takes": {"toy_pilot_1": {"route": "people"}, "toy_seat_1": {"route": "prop"}}})
    batch = tmp_path / "check"
    batch.mkdir()
    batch_gaps.write(batch, [batch_gaps.gap(f"{name}: off", "surfaces-check", "baked", objects, [f"{name}: off"], "x")
                             for name, objects in (("toy_pilot_1", ["toy_pilot_1"]), ("pilot_1", ["toy_pilot_1", "pilot_1"]),
                                                   ("seat_1", ["toy_seat_1", "seat_1"]), ("lamp", ["pilot_lamp"]),
                                                   ("both", ["toy_pilot_1", "toy_seat_1"]))])
    people = people_gaps.judge_accepted(None, {"hand-in": handin, "check": batch}, None)
    assert people.answer == checks.FAIL and people.measures["people takes' gaps"] == 2, people
    assert [finding.split(":")[0] for finding in people.findings] == ["seat_1", "lamp", "both"], people.findings
    assert "pilot_1: off" in people.reason.split("left out, the people line's")[1], people.reason
    batch_gaps.write(batch, [batch_gaps.gap("pilot_1: off", "surfaces-check", "baked", ["pilot_1"], ["off"], "x")])
    assert people_gaps.judge_accepted(None, {"hand-in": handin, "check": batch}, None).answer == checks.PASS
    assert people_gaps.judge_accepted(None, {"check": batch}, None).answer == checks.FAIL  # no hand-in: no people row

    # the table wraps each gate in the gap mover, and only complete's code version holds gaps.py
    assert graph.GAPPED == "accepted gaps" and graph.GAPPED in [check.name for check in ROWS["complete"].checks]
    for name, gate in GAPPED_GATES:
        check = next(check for check in ROWS[name].checks if check.name == gate)
        assert hasattr(check.judge, "__wrapped__"), (name, gate)
    hashing = {name for name in ("assembly", "surfaces-check", "surfaces-paint", "complete")
               if _code.REPO / "score/stages/gaps.py" in _code.source_files(graph.code_functions(ROWS[name]))}
    assert hashing == {"complete"}, hashing  # moving a verdict re-makes nothing, the paid paint above all

    # a failed paid take is a gap carried down its line: the batch brought the crate's take back and not the hatch's;
    # its row names the gap, its gate still fails it and the table moves exactly that fault
    out, inputs = pixal_made({"crate-s1"})
    found = batch_gaps.read([out])
    assert [entry["name"] for entry in found] == ["hatch: Pixal3D made no model"], found
    assert set(found[0]["objects"]) == {"hatch", "hatch-s1"} and found[0]["row"] == "pixal"
    assert found[0]["decided"] == f"the batch run (pixal, output {out.name})"
    takes = next(check for check in ROWS["pixal"].checks if check.name == "takes")
    raw = takes.judge.__wrapped__(out, inputs, None)
    assert raw.answer == checks.FAIL and all(finding.startswith("hatch: ") for finding in raw.findings), raw
    gated = takes.judge(out, inputs, None)
    assert gated.answer == checks.PASS and gated.findings == raw.findings, gated
    assert "moved to complete as accepted gaps: hatch: Pixal3D made no model (the batch run" in gated.reason
    # the views leave the gap's take out and carry its gap on
    views = out.parent / "views"
    views.mkdir()
    route_views.make_views({"surfaces": inputs["surfaces"], "pixal": out}, views, 0, {})
    assert list(json.loads((views / "views.json").read_text())) == ["crate-s1"]
    assert [entry["name"] for entry in batch_gaps.read([views])] == ["hatch: Pixal3D made no model"]
    # a fault no batch gap names still fails the gate: the made take changed since
    pixal_row.take_files("crate-s1")[1].write_text("changed since it was made")
    assert takes.judge(out, inputs, None).answer == checks.FAIL
    # every take a batch gap: the views pass with their gaps carried (finish-route-views@people, 2026-10-21, failed it
    # as "no take to work on"), and the same empty views with no gap still fail
    for path in [path for entry in OBJECTS.values() for path in pixal_row.take_files(entry["take"])]:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    out, inputs = pixal_made(set())
    views = out.parent / "views"
    views.mkdir()
    route_views.make_views({"surfaces": inputs["surfaces"], "pixal": out}, views, 0, {})
    assert json.loads((views / "views.json").read_text()) == {}
    verdict = route_views.judge_views(views, {}, None)
    assert verdict.answer == checks.PASS and verdict.measures["left_out"] == 2, verdict
    assert "crate: Pixal3D made no model" in verdict.reason and "hatch: Pixal3D made no model" in verdict.reason
    assert {entry["name"] for entry in batch_gaps.read([views])} == {"crate: Pixal3D made no model",
                                                                     "hatch: Pixal3D made no model"}
    (views / batch_gaps.FILE).write_text(json.dumps({"gaps": []}))
    assert route_views.judge_views(views, {}, None).answer == checks.FAIL

    # a take the owner rejected is set aside once and retaken (owner, 2026-10-28: a failing object remade once,
    # free): its files moved aside once (the other takes, and a take its name starts, kept), named by its take or its
    # object (checkout 66, 2026-11-09), and out of takes_back until its retake is made: its mark, or the library's
    # newest record holding another raw model than the one set aside (checkout 18, 2026-11-04); a code build's take
    # is refused
    rejected = tmp_path / "rejected"
    rejected.mkdir()
    for name in ("stool_1.glb", "stool_1-final.glb", "stool_1-5000.glb", "stool_1.json", "stool_10.glb", "seat_1.glb"):
        (rejected / name).write_text("old")
    (rejected / "stool_1.svviews").mkdir()
    (rejected / "pipe_1.svviews").mkdir()
    (rejected / "pipe_1.svviews" / "code.json").write_text("{}")
    objects = {"stool": {"take": "stool_1"}, "seat": {"take": "seat_1"}, "pipe": {"take": "pipe_1"}}
    retake = {"takes": ["stool_1"], "attempt": 1, "after": "k"}
    assert stages.set_aside(retake, objects, rejected) == {"stool_1": 2}
    aside = rejected / stages.RETAKEN / "stool_1-r1"
    assert sorted(path.name for path in aside.iterdir()) == [
        "stool_1-5000.glb", "stool_1-final.glb", "stool_1.glb", "stool_1.json", "stool_1.svviews"]
    assert sorted(path.name for path in rejected.glob("*.glb")) == ["seat_1.glb", "stool_10.glb"]
    assert stages.retake_pending("stool_1", rejected) and not stages.retake_pending("stool_10", rejected)
    (rejected / "stool_1.glb").write_text("new")
    stages.set_aside(retake, objects, rejected)
    assert (rejected / "stool_1.glb").read_text() == "new" and (aside / "stool_1.glb").read_text() == "old"
    for raw, pending in ((b"old", True), (None, True), (b"new", False), (b"olD", False)):
        handed = {} if raw is None else {"files": {"stool_1.glb": {"bytes": len(raw),
                                                                   "sha256": hashlib.sha256(raw).hexdigest()}}}
        assert stages.retake_pending("stool_1", rejected, handed) is pending, raw
    (aside / stages.RETAKE_MADE).touch()
    assert not stages.retake_pending("stool_1", rejected)
    with pytest.raises(ValueError, match="pipe_1"):
        stages.set_aside({**retake, "takes": ["pipe_1"]}, objects, rejected)
    assert stages.set_aside({**retake, "takes": ["stool"]}, objects, rejected) == {"stool_1": 2}
    # the pixal make under a retake (retaking) asks Pixal3D's seed of a named take as set_aside gave it and of any
    # other take as its name gives it, its own seed_of put back after; a sheet's take (flat_sheet.sheet: a paper
    # pinned to a wall) is remade in code from its own close-up before the make runs, never a new seed, its mark
    # saying why; each retake made is marked so; with no retake the make runs as it is
    import score.stages.props.flat_sheet as flat_sheet
    import score.stages.props.thin_straight as thin_straight
    from PIL import Image
    pixal = pixal_row.take_files("-")[0].parent
    pixal.mkdir(parents=True, exist_ok=True)
    for suffix in ("-final.glb", "-4000.glb", ".glb"):
        pixal.joinpath(f"note_3{suffix}").write_text("old")
    pixal.joinpath("note_3.svviews").mkdir(exist_ok=True)
    retaken = tmp_path / "retaken"
    (retaken / "closeup/closeups").mkdir(parents=True)
    picture = Image.new("RGB", (100, 140), (120, 120, 120))
    picture.paste((240, 235, 220), (20, 20, 80, 120))
    picture.save(retaken / "closeup/closeups/note.png")
    retake_inputs = {
        "props": written(retaken, "handin.json", {"objects": {"crate": {"route": "prop", "take": "crate_7"},
                                                              "seat": {"route": "prop", "take": "seat-s3"},
                                                              "note": {"route": "prop", "take": "note_3"}}}),
        "inventory": written(retaken, "inventory.json", {"rows": [{"id": "crate", "size": [0.5, 0.5, 0.5]},
                                                                  {"id": "note", "size": [0.2, 0.01, 0.3]}]}),
        "surfaces": written(retaken, "surfaces.json", {"bake": {"models": {"note_1": "note_3"},
                                                                "entries": {"note_1": {"faces": 4000}}}}),
        "closeup": retaken / "closeup"}
    asked = []

    def retake_make(inputs, out, seed, params):
        asked.append((pixal_row.seed_of("crate_7"), pixal_row.seed_of("seat-s3"), flat_sheet.built("note_3", pixal)))
        for suffix in pixal_row.SUFFIXES:
            pixal.joinpath(f"crate_7{suffix}").write_text("new")
    stages.retaking(retake_make)(retake_inputs, retaken, 1, {"retake": {"takes": ["crate_7", "note_3"], "attempt": 1,
                                                                        "after": "k"}})
    assert asked == [(2, 3, True)] and pixal_row.seed_of("crate_7") == 1 and pixal_row.finished("note_3", 4000)
    for take in ("crate_7", "note_3"):
        assert (pixal / stages.RETAKEN / f"{take}-r1" / stages.RETAKE_MADE).exists(), take
    assert "reject" in json.loads((pixal / "note_3.svviews" / thin_straight.MARK).read_text())["why"]
    stages.retaking(retake_make)(retake_inputs, retaken, 1, {})
    assert asked[-1] == (1, 3, True)
    # so is a look's parts made at a new seed (the owner's reject, a free remake): its candidate parts folder is set
    # aside and bought again, never copied out as it was (people-look-parts-man_stair-made gave its rejected bdb60d93
    # again, checkout 89, 2026-11-11), and a make at its own seed keeps it
    bought = []

    def parts_make(inputs, out, seed, params):
        made = retaken / "candidates" / "man" / params["outfit"] / "parts" / "take"
        if not (made / "parts.npz").exists():
            made.mkdir(parents=True, exist_ok=True)
            (made / "parts.npz").write_text(f"seed {seed}")
            bought.append(seed)
    old_parts = retaken / "candidates" / "man" / "made" / "parts" / "take"
    old_parts.mkdir(parents=True)
    (old_parts / "parts.npz").write_text("rejected")
    sys.path.insert(0, str(stages.people.bodies.MAKER))
    import prop_person
    with mock.patch.object(prop_person, "CANDIDATES", retaken / "candidates"):
        for seed in (5, 5, 6):
            stages.parts_reseeded(parts_make)({"spec": str(written(retaken, "man.json", {"name": "man"}))}, retaken,
                                              seed, {"outfit": "made"})
    assert bought == [5, 6] and (old_parts / "parts.npz").read_text() == "seed 6"
    assert (old_parts.parent.with_name("parts.misfit") / "take" / "parts.npz").read_text() == "seed 5"

    # a take the surface line left out never vanishes silently (owner, 2026-10-29): the likeness make names each
    # left-out take a batch gap with its reason and the rows it stands for, once, beside the gaps it carries; a take a
    # gap already names is not named again
    handin = written(tmp_path, "left_out_handin.json", HANDIN)
    bake = tmp_path / "left_out_bake"
    bake.mkdir()
    written(bake, "painted.json", {"takes": {}, "left_out": {"crane_7": "patchy paint: stray 0.031 > 0.03",
                                                             "hatch_2": "hatch_2: not baked"}})

    def likeness_make(inputs, out, seed, params):
        batch_gaps.write(out, [batch_gaps.gap("hatch_2: not baked", "surfaces-bake", "baked", ("hatch_2", "hatch"),
                                              [], "its bake job failed")])
    likeness = tmp_path / "left_out_likeness"
    likeness.mkdir()
    stages.leaving_out(likeness_make)({"surfaces-bake": bake, "props": handin}, likeness, 1, {})
    found = {entry["name"]: entry for entry in batch_gaps.read([likeness])}
    assert sorted(found) == ["crane_7: left out: patchy paint: stray 0.031 > 0.03", "hatch_2: not baked"], found
    assert found["crane_7: left out: patchy paint: stray 0.031 > 0.03"]["objects"] == ["crane", "crane_7"]
    # the likeness's lean gate ties each carried gap's take to the rows the hand-in says it stands for, so a gap
    # naming a take alone moves its row's fault (likeness@camp, 2026-10-30); a fault no gap's take stands for still
    # fails, its reason naming the gap of the fault that is one (likeness@quarters, 2026-11-08)
    lean = next(check for check in ROWS["likeness"].checks if check.name == "lean")
    split = tmp_path / "left_out_split"
    split.mkdir()
    batch_gaps.write(split, [batch_gaps.gap("counter_7: not one finish a face", "finish-route-split",
                                            "one finish a face", ("counter_7",), [], "patchy paint")])
    missing = {"missing": "no model", "route": "prop"}
    for faults, answer, findings in (({"counter": missing}, checks.PASS, None),
                                     ({"counter": missing, "crate": missing}, checks.FAIL, 2)):
        written(likeness, "likeness.json", {"objects": faults})
        judged = lean.judge(likeness, {"finish-route-split": split, "props": handin}, None)
        assert judged.answer == answer, (faults, judged)
        if findings:  # the crate's fault and the counter's both still shown
            assert "counter_7: not one finish a face" in judged.reason and len(judged.findings) == findings, judged
    # motion reads a designed place's hand-in and its accepted plan where it stands, so it names its left-out takes
    # too; a place without either keeps its files
    bare = ROWS["motion"].files("toy")
    with monkeypatch.context() as patch:
        patch.setattr(stages.prop_data, "designed", lambda place: True)
        patch.setattr(stages, "plan_written", lambda place: True)
        motion_files, designed_handin = ROWS["motion"].files("toy"), stages.prop_data.keyed("toy")
    assert motion_files["props"] == designed_handin, motion_files
    assert motion_files["plan"] == "{home}/design/plans/toy.json", motion_files
    assert "props" not in bare and "plan" not in bare, bare

    # the fixture line runs on to complete apart from the batch's gap, which complete lists with the batch run that
    # decided it; a take lost with no batch gap still stops the line
    for brief, says in LINES:
        runner = fixture_line(brief)
        found = runner.drive(["dock"], say=lambda line: None)
        assert {node: found[node] for node in says} == says, (brief, found)
        if brief == "the batch":
            assert found["complete@dock"].startswith("made: fail, accepted automatically"), found
            assert runner.status(["dock"])["complete@dock"] == "complete apart from accepted gaps (1), accepted"
            judgement = review.newest_judgement(runner.store, review.record_of(runner.store, "complete@dock"))
            listed = judgement["verdicts"][graph.GAPPED]
            assert "hatch: Pixal3D made no model (the Pixal3D job ran once and failed; the batch run (pixal, output" \
                in listed["reason"] and listed["findings"] == ["hatch: Pixal3D made no model: hatch: no hatch-s1.glb"]

    # a take the paint fails is a gap and the table moves its fault alone; the check's model over its budget a gap of
    # it and its take; a fault no gap names still stops; a clean paint writes no gaps file
    from score.stages.surfaces import route_check
    measured_clean(monkeypatch)
    surfaces = tmp_path / "surfaces"
    surfaces.mkdir()
    baked, records = painted(surfaces)
    inputs = {"surfaces-bake": baked}
    paint = surfaces / "paint"
    paint.mkdir()
    ROWS["surfaces-paint"].make(inputs, paint, 0, {})
    found = batch_gaps.read([paint])
    assert [entry["name"] for entry in found] == ["crate-s1: colour against the close-up"], found
    colour = next(check for check in ROWS["surfaces-paint"].checks if check.name == "colour against the close-up")
    assert colour.judge.__wrapped__(paint, inputs, None).answer == checks.FAIL
    gated = colour.judge(paint, inputs, None)
    assert gated.answer == checks.PASS and "moved to complete" in gated.reason, gated
    monkeypatch.setattr(route_check.prop_env, "handover",
                        lambda module, step, given, out: written(out, "checks.json", records))
    check = surfaces / "check"
    check.mkdir()
    route_check.make_check({**inputs, "surfaces-paint": paint}, check, 0, {})
    names = {entry["name"]: entry for entry in batch_gaps.read([check])}
    assert set(names) == {"crate-s1: colour against the close-up", "crate: triangles within budget"}, names
    assert set(names["crate: triangles within budget"]["objects"]) == {"crate", "crate-s1"}
    budget = next(check for check in ROWS["surfaces-check"].checks if check.name == "triangles within budget")
    assert budget.judge(check, {**inputs, "surfaces-paint": paint}, None).answer == checks.PASS
    written(check, "checks.json", {**records, "hatch": dict(records["hatch"], triangles=5000)})
    assert budget.judge(check, {**inputs, "surfaces-paint": paint}, None).answer == checks.FAIL
    written(baked, "painted.json", {"takes": {"hatch-s1": {"unnamed_parts": 0, "unnamed_share": 0.0, "finishes": [],
                                                           "feet": {}}}, "left_out": {}})
    clean = surfaces / "clean-paint"
    clean.mkdir()
    ROWS["surfaces-paint"].make({"surfaces-bake": baked}, clean, 0, {})
    assert not (clean / batch_gaps.FILE).exists()

    # the push gate: on a toy repository with every row made and accepted, each working-tree edit is listed by
    # `score moved` as the paid rows it buys again, with price and why, and refused at a push only for a paid row moved
    main = command()
    with toy() as repo:
        store = made(repo)
        before = snap(repo, store)
        for case, files, table, buys, moved_now, refusal in TREE_EDITS:
            for name, text in files.items():
                (repo / name).write_text(text)
            if buys is not None:
                found = rebought(repo, store, **table)
                assert [(row.node, row.euros, row.why) for row in found["toy"]] == buys, (case, found)
                printed, code = exit_code(main.moved_check, found)
                assert code == (moved.MOVED_EXIT if buys else 0), (case, printed)
                assert f"about EUR {sum(euros for _, euros, _ in buys):.2f}" in printed, (case, printed)
                assert all(f"toy {node}: EUR {euros:.2f}, {why}" in printed for node, euros, why in buys), printed
            found = moved.moved_rows(before, snap(repo, store, **table))
            assert moves(found) == moved_now, (case, found)
            printed, code = exit_code(main.pushed_check, found, [])
            assert code == (moved.MOVED_EXIT if refusal else 0), (case, printed)
            assert all(said in printed for said in refusal), (case, printed)
            git(repo, "checkout", "--", ".")
        # an unknown commit, or one whose tree cannot work out a snapshot (the toy has no score), raises and leaves
        # no checkout behind
        checkouts = set(repo.parent.glob("moved-*"))
        for commit in ("f" * 40, git(repo, "rev-parse", "HEAD")):
            with pytest.raises(subprocess.CalledProcessError):
                moved.snapshot(commit)
        assert set(repo.parent.glob("moved-*")) == checkouts and len(git(repo, "worktree", "list").splitlines()) == 1
        # a pushed commit's trailer lets only the rows it names go; the pre-push check works it out on a clean
        # checkout of the pushed commit against main's, never on a changed tree or an unknown main
        line, tip = pushed(repo, "data: a brighter hall and a new make\n\nMoved-rows: bake@hangar: the owner asked",
                           {"bake.txt": "a hall's brighter light", "toy_render.py": RENDER_MAKE + "\n# moved\n"})
        sys.modules.pop("toy_render", None)
        found = moved.moved_rows(before, snap(repo, store))
        assert sorted(found) == ["bake", "render"], found
        reasons = moved.pushed_reasons(moved.main_pushes([line]))
        assert reasons == ["bake@hangar: the owner asked"]
        assert moved.pushed_reasons([(tip, moved.ZERO)]) == reasons  # a new remote ref: commits on no remote yet
        bases = []
        moved.moved = lambda base, head=None: bases.append((base, head)) or found
        (repo / "draw.txt").write_text("not committed")
        printed, code = exit_code(main.pre_push_check, [line])
        assert code != 0 and "clean checkout" in printed and bases == [], printed
        git(repo, "checkout", "--", "draw.txt")
        printed, code = exit_code(main.pre_push_check, [f"refs/heads/main {tip} refs/heads/main {moved.ZERO}"])
        assert code != 0 and "not known" in printed and bases == [], printed
        printed, code = exit_code(main.pre_push_check, [line])
        assert code == moved.MOVED_EXIT and "Moved-rows: render: <why>" in printed, printed
        assert bases == [(line.split()[3], None)]
        printed, code = exit_code(main.pushed_check, found, reasons + ["render: a new make"])
        assert code == 0 and "Moved-rows: bake@hangar: the owner asked" in printed, printed
        # a module moved into FRAMEWORK and edited in the same change makes the rows that read it again (no narrowing
        # carry): it is named, a plain move is not
        (repo / "score/graph").mkdir(parents=True)
        declared = repo / "score/graph/_code.py"
        declared.write_text("FRAMEWORK = {REPO / name for name in ()}\n")
        first = pushed(repo, "helpers", {"plain.py": "A = 1\n", "edited.py": "B = 1\n"})[1]
        declared.write_text("FRAMEWORK = {REPO / name for name in ('plain.py', 'edited.py')}\n")
        second = pushed(repo, "helpers into the framework", {"edited.py": "B = 2\n"})[1]
        assert moved.edited_into_framework(first, second) == ["edited.py"]
    for lines, pushes in PUSH_LINES:
        assert moved.main_pushes(lines) == pushes, lines
    printed, code = exit_code(main.pre_push_check, NOT_MAIN)
    assert code == 0 and "nothing pushed to main" in printed, printed
    for row_name, reasons, is_named in ROW_NAMED:
        assert moved.row_named(row_name, reasons) is is_named, (row_name, reasons)

    # the hook runs the check only for a push to main once the owner turned it on, from the right checkout, home and
    # python, within its time, and leaves no checkout, process or temporary file behind
    hooks = hook_world()
    for case, name, where, line, on, limit, loose, exit_with, env, code, said, record, timeout in HOOK_CASES:
        repo = hooks[name]
        values = {**hooks, "tip": git(repo, "rev-parse", "HEAD")}
        configured(repo, "score.movedCheck", "true" if on else None)
        configured(repo, "score.movedTimeout", limit)
        trees = git(repo, "worktree", "list")
        if loose:
            (repo / "loose.txt").write_text("not committed")
        line = placed(line, values)
        ran, printed, wrote, given, temp = hook(values[where], [line], exit_with,
                                                   {key: placed(value, values) for key, value in env.items()})
        assert ran == code and (said in printed if said else printed == ""), (case, ran, printed)
        assert given == timeout, (case, given)
        if record is None:
            assert wrote is None, (case, wrote)
        elif record == ENDED:
            assert isinstance(wrote, int) and gone(wrote), (case, wrote)
        else:
            for key, value in record.items():
                if value == GONE:
                    assert wrote[key] != str(repo) and not pathlib.Path(wrote[key]).exists(), (case, wrote)
                else:
                    assert wrote[key] == placed(value, values), (case, key, wrote)
        assert list(temp.iterdir()) == [] and git(repo, "worktree", "list") == trees, case
        assert sorted(path.name for path in repo.parent.iterdir()) == ["repo"], case
        if loose:
            (repo / "loose.txt").unlink()

    # every designed person is a look of the people line, written from the design alone: every people row of the
    # home's designs maps to looks the line holds, one look (one body) for the camp's, the garage's and the airlock's
    # astronauts, each look asking for the drawn face
    sys.path.insert(0, str(REPO / "tools/characters/maker"))
    import spec as specs
    import copy
    import numpy as np
    from score.stages import people_clothes
    from score.stages.complete.prepare import groups
    from score.stages.props import closeup_row
    found = people_rows.read()
    line = people_rows.line_looks()
    for place, held_entry in found["places"].items():
        for row_id, fields in held_entry["rows"].items():
            if "crowd" in fields:
                assert fields["crowd"] in line, (place, row_id)
            else:
                assert len(fields["looks"]) == fields["count"], (place, row_id)  # a look for each person
                assert all(look in line for look in fields["looks"]), (place, row_id)  # every person can be made
    assert people_rows.mapping_rows(found)["astronaut-made"]
    assert {fields["looks"][0] for place in ("camp", "garage", "airlock") for fields in
            found["places"][place]["rows"].values()} == {"astronaut-made"}
    assert all(look.endswith(f"-{people_rows.OUTFIT}") for look in line), "a row asks for the drawn face"

    # the line's data is exactly what rows.json maps (run python -m score.stages.people_refresh), each look baked at
    # its person row's size: kept inventories holding the boxes the line already draws from give the line back
    records = {name: json.loads(path.read_text()) for name, path in people_rows.LINE_FILES.items()}
    held = {}
    for line_row in records["inventory"]["rows"]:
        if line_row.get("view"):
            place, row_id = people_rows.size_of(line_row["id"])[1].split("/", 1)
            held.setdefault(place, []).append({"id": row_id, "box": line_row["box"]})
    props, inventory, surfaces = people_refresh.line_rows(
        found, *copy.deepcopy([records["props"], records["inventory"], records["surfaces"]]),
        kept_inventories(tmp_path / "kept-line", held))
    assert (props, inventory, surfaces) == (records["props"], records["inventory"], records["surfaces"]), \
        "the line's data is not written from rows.json: run python -m score.stages.people_refresh"
    assert set(props["objects"]) == people_rows.every_look()  # every look the designs map, each on the line
    assert set(surfaces["bake"]["entries"]) == set(surfaces["bake"]["models"]) == set(props["objects"])
    assert all(entry["spec"].startswith("data/people/specs/") for entry in surfaces["takes"].values()), \
        "every look on the line is written from a design's row (the hand-made makes were retired, 2026-10-21)"
    assert people_rows.size_of("person_uniform-made")[1] == "tube/person_right"  # the larger of the tube's two rows
    size, origin = people_rows.size_of("crowd-made")
    assert people_rows.person_sized(size) and origin == "square/crowd"  # one member, never the crowd's extent
    # each close-up's words say who the look is (#26: the first people benchmark drew its player, a Chinese man in
    # his thirties by his spec, as someone else): its spec's description, then its clothes
    rows = {row["id"]: row for row in inventory["rows"]}
    words = {row["id"]: row["words"] for row in closeup_row.inventory_rows(inventory, people_rows.every_look())}
    assert words["person_uniform-made"].startswith("person in uniform, an average build")
    for look, said in words.items():
        assert said == f"{people_rows.description_of(look)}; {rows[look]['clothes']}", look
    # each line row is drawn from the picked design's person row that maps it (its view the kept concept, its box SAM
    # 3's tallest instance, grounded), so no take row and no work folder stands before the line; the line is approved
    # by those picks
    boxes = [[number, 0, number + 1, 2 + number % 3] for number in range(5)]
    props, inventory, _ = people_refresh.line_rows(
        found, *copy.deepcopy([records["props"], records["inventory"], records["surfaces"]]),
        kept_inventories(tmp_path / "kept-toy", {"tube": [{"id": "person_right", "box": [1, 2, 3, 4]}],
                                                 "garage": [{"id": "astronaut", "box": boxes[0], "boxes": boxes}]}))
    rows = {row["id"]: row for row in inventory["rows"]}
    right = rows["person_uniform-made"]
    assert (right["view"], right["box"], right["prop"]) == ("tube", [1, 2, 3, 4], "person_uniform-made") and \
        right["grounded"], right
    assert rows["crowd-made"]["view"] is None, "the square keeps no inventory here"
    assert (rows["astronaut-made"]["view"], rows["astronaut-made"]["box"]) == ("garage", boxes[2])  # its tallest
    assert inventory["plan"]["views"] == [{"id": place, "picture": f"{{home}}/design/concepts/{place}.png"}
                                          for place in ("garage", "tube")]
    assert inventory["approved"]["by"] == "the creator's pick" and inventory["approved"]["places"] == ["garage", "tube"]
    assert "closeup" not in props["objects"]["person_uniform-made"]
    # a design's person is made from its row, never a hand-written character file: who by the row's words, the build
    # by its metres, a spec the maker takes, and a take on the line
    specs_made = people_rows.designed_specs(DESIGNED, records["surfaces"])
    assert set(specs_made) == {"pilot_suit-made", "guest-made", "crowd-made"}
    pilot = specs_made["pilot_suit-made"]
    assert pilot["name"] == "pilot_suit" and pilot["outfits"] == ["made"] and "abcdef01" in pilot["approved"]
    assert pilot["description"] == "pilot in a red suit, a slim build, as drawn in the deck concept", pilot
    assert people_rows.size_of("pilot_suit-made", DESIGNED) == ([0.3, 0.4, 1.7], "deck/pilot")
    assert "a broad build" in specs_made["guest-made"]["description"]  # seated: its narrower side, 0.7 m
    assert specs_made["crowd-made"]["description"].startswith("one person of the crowd of people, an average build")
    assert all(not specs.problems_of(spec) for spec in specs_made.values()), \
        [specs.problems_of(spec) for spec in specs_made.values()]
    redesigned = copy.deepcopy(DESIGNED)
    deck = redesigned["places"]["deck"]["rows"]
    # a row read into a look by its garment wears it and draws it only where no row's words name it
    deck["suited"] = {"name": "person in spacesuit", "noun": "person", "count": 1, "size": [0.5, 0.5, 1.8],
                      "share": 0.9, "looks": ["astronaut-made"]}
    assert people_rows.origin_of("astronaut-made", redesigned)[1] == "suited"
    deck["astronaut"] = {"name": "astronaut", "noun": "astronaut", "count": 1, "size": [0.6, 0.4, 1.8], "share": 0.1,
                         "looks": ["astronaut-made"]}
    assert people_rows.origin_of("astronaut-made", redesigned)[1] == "astronaut", \
        "drawn from the lab's bare-headed bust"
    assert people_rows.member_size("crowd-made", redesigned) == ([0.55, 0.55, 1.8], "deck/crowd")
    # five people standing apart on 10 x 30 m are baked at one member's size
    deck["walkway_crowd"] = {"name": "people on walkway", "noun": "people", "count": 5, "size": [10.0, 30.0, 1.8],
                             "share": 0.06, "looks": ["person-made"] * 5}
    size, origin = people_rows.size_of("person-made", redesigned)
    assert people_rows.person_sized(size) and origin == "deck/walkway_crowd", (size, origin)
    props, inventory, lined = people_rows.with_designed(specs_made, {"objects": {}}, {"rows": []}, records["surfaces"])
    take = lined["bake"]["models"]["pilot_suit-made"]
    assert take == "pilot_suit-made-s1" and props["objects"]["pilot_suit-made"]["take"] == take
    assert lined["takes"][take]["spec"] == "data/people/specs/pilot_suit.json"
    assert lined["takes"][take]["outfit"] == "made" and {row["id"] for row in inventory["rows"]} == set(specs_made)

    # the deck's refresh: a people row the plan shows beyond the place is not its own unless it stands on a row laid
    # here; a crowd stands on the plan items its row makes; each person on its row's own plan spot, each of one look its
    # own variant (owner, 2026-10-25: "Each one looks different"); the worker wears the fabric its words name nearest
    # its torso, the pilot, naming none, its look's own paint
    labels = people_clothes.labels()

    def lab(srgb):
        return [float(value) for value in labels.lab(np.array(srgb, dtype=float)[None] / 255)[0]]
    beyond = groups.stood_beyond(DECK_ROWS, set(DECK_PLAN["beyond"]))
    assert beyond == {"far_crowd", "far_stage", "singer"}, beyond  # the man stands on the place's own stairs
    reading = {"concept_pick": {"sha256": "0badcafe"}, "rows": [groups.routed(row, set(), beyond) for row in DECK_ROWS]}
    fabrics = {name: lab(srgb) for name, srgb in FABRICS.items()}
    deck_entry = people_rows.refreshed_place("deck", reading, DECK_PLAN, None, fabrics, a_concept(BLUE))
    assert set(deck_entry["rows"]) == {"crowd", "pilot", "worker", "man"}, set(deck_entry["rows"])
    assert deck_entry["rows"]["crowd"]["crowd"] == "crowd-made", "a crowd takes no look drawn from another scene's row"
    for plan, row_id, ground in CROWD_GROUNDS:
        assert people_rows.crowd_ground(plan, row_id) == ground, (row_id, ground)
    deck = {"places": {"deck": deck_entry}}
    cast = people_rows.cast_record("deck", deck)
    assert {person["name"]: (person["at"], person["look"], person["variant"], person["surface"])
            for person in cast["people"]} == {
        "man": ([0.0, 0.0, 0.0], "man_made", 0, None),
        "pilot_1": ([-9.0, 0.0, -4.0], "person_uniform_made", 0, None),
        "pilot_2": ([-7.0, 0.0, -3.0], "person_uniform_made", 1, None),
        "pilot_3": ([-5.0, 0.0, -2.0], "person_uniform_made", 2, None),
        "worker": ([0.0, 0.0, 0.0], "worker_jumpsuit_made", 0, "jacket_blue")}, cast["people"]
    crowd = cast["crowd"]
    assert crowd["spread"] == CROWD_SPREAD and crowd["grounds"] == [CROWD_SPREAD], crowd
    assert crowd["seed"] == 0x0badcafe and crowd["facing_to"] == deck_entry["middle"], crowd
    assert sum(crowd["palette_shares"]) == 1.0, crowd
    for count, counted, palettes in CROWD_COUNTS:
        record = people_rows.crowd_record("crowd", {**deck_entry["rows"]["crowd"], "count": count}, deck_entry)
        assert (record["count"], record["palettes"]) == (counted, palettes), (count, record)
    variants = {("crowd-made", None, variant) for variant in range(people_rows.CROWD_VARIANTS)}
    assert people_rows.dressed_looks("deck", deck) == {
        ("man-made", None, 0), ("worker_jumpsuit-made", "jacket_blue", 0),
        *{("person_uniform-made", None, variant) for variant in range(3)}, *variants}
    dressed = {("worker_jumpsuit-made", "jacket_blue", 0), ("person_uniform-made", None, 1),
               ("person_uniform-made", None, 2), *(variants - {("crowd-made", None, 0)})}
    assert people_rows.every_dressed(deck) == dressed
    twice = copy.deepcopy(deck)
    twice["places"]["deck"]["rows"]["worker"]["looks"] = ["worker_jumpsuit-made"] * 2
    assert people_rows.every_dressed(twice) == dressed | {("worker_jumpsuit-made", "jacket_blue", 1)}, \
        "two people, two variants"
    # a tagged spot reaches its own row whatever the order of the row ids; an untagged (view) spot only a row with
    # none tagged (the cockpit's pilot and officer swapped, the street's diner on the pavement, 2026-11-04)
    spots, _ = people_rows.placed_spots({"w": 20.0, "d": 10.0, "people": [[11.0, 6.0, 0, "b_officer"],
                                                                         [19.0, 14.0], [12.0, 7.0, 0, "a_pilot"]]})
    swapped = {"concept": "one", "spots": spots,
               "rows": {row_id: {"looks": ["person_uniform-made"]} for row_id in ("b_officer", "a_pilot", "c_guest")}}
    assert {person["name"]: person["at"] for person in
            people_rows.cast_record("deck", {"places": {"deck": swapped}})["people"]} == {
        "a_pilot": [2.0, 0.0, 2.0], "b_officer": [1.0, 0.0, 1.0], "c_guest": [9.0, 0.0, 9.0]}
    # a refresh keeps a hand-made choice (one recorded with its why) only while its concept stands
    old = copy.deepcopy(deck_entry)
    old["rows"]["pilot"]["looks"] = ["deck_pilot-made", "person_uniform-made", "person_uniform-made"]
    for why, concept, look in ((None, "0badcafe", "person_uniform-made"), ("the owner's pick: the player", "0badcafe",
                                                                           "deck_pilot-made"),
                               ("the owner's pick: the player", "two", "person_uniform-made")):
        if why:
            old["rows"]["pilot"]["why"] = why
        again = people_rows.refreshed_place("deck", {**reading, "concept_pick": {"sha256": concept}}, DECK_PLAN, old,
                                            fabrics, None)
        assert again["rows"]["pilot"]["looks"][0] == look, (why, concept, again["rows"]["pilot"])
    # the fabrics are the people line's own library's (surface-library@people): its fabric family alone, and an
    # empty one is refused (the repository's, read until 2026-11-04, held none, so no row's clothes were chosen)
    library = {"jacket_blue": {"family": "fabric", "colour": [0.02, 0.05, 0.3]},
               "boot": {"family": "rubber", "colour": [0.1, 0.1, 0.1]}}
    assert set(people_clothes.fabrics_of(library)) == {"jacket_blue"}
    with pytest.raises(people_clothes.NoFabrics):
        people_clothes.fabrics_of({"boot": library["boot"]})
    for case, dress_row, given, torso, surface, near in DRESSED:
        dress = people_rows.refreshed_place("deck", {**reading, "rows": [dress_row]}, None, None,
                                            {name: lab(srgb) for name, srgb in given.items()},
                                            a_concept(torso))["rows"][dress_row["id"]]["dress"]
        measured = (None if dress["de"] is None else "near" if dress["de"] < 1
                    else "far" if dress["de"] > people_clothes.WITHIN else "between")
        assert (dress["surface"], measured) == (surface, near), (case, dress)
        assert (dress["torso_lab"] is None) is (torso is None), (case, dress)
    worker, pilot = deck_entry["rows"]["worker"]["dress"], deck_entry["rows"]["pilot"]["dress"]
    assert worker["figures"] == 1 and "suit_light_blue" in worker["named"] and not any(
        "light" in name and "blue" not in name for name in worker["named"]), worker
    assert pilot["surface"] is None and pilot["named"] == [], pilot
    # a crowd's look is read off its words (no city square's coats on every crowd)
    (tmp_path / "citizen.json").write_text(json.dumps({"description": "a man in his thirties, an ordinary citizen in the "
                                                                      "crowd"}))
    (tmp_path / "astronaut.json").write_text(json.dumps({"description": "a man in his thirties, an astronaut of a Moon "
                                                                        "base"}))
    (tmp_path / "drawn.json").write_text(json.dumps({"description": "one person of the crowd of people, as drawn in "
                                                                    "the square concept"}))
    plain_line = {"citizen-coat": {"object": "a person in a plain mid grey coat", "far_only": True,
                                   "spec": str(tmp_path / "citizen.json")},
                  "astronaut-work": {"object": "a person in a dark navy one-piece work suit",
                                     "spec": str(tmp_path / "astronaut.json")}}
    square = {"square_crowd-drawn": {"object": "one person of the crowd of people", "far_only": True,
                                     "spec": str(people_rows.SPECS / "square_crowd.json")},
              "people-made": {"object": "one person of the crowd of people", "far_only": True,
                              "spec": str(tmp_path / "drawn.json")}}
    lines = {"line": plain_line, "square": square, "both": {**plain_line, **square}}
    for name, noun, read, look in CROWD_LOOKS:
        assert people_rows.crowd_look("moon", {"id": "crowd", "name": name, "noun": noun}, lines[read]) == look, \
            (name, noun, read)

    # the copy of a seed a layer is written over takes a save, though the store's seed is read-only
    folder = tmp_path / "seed"
    (folder / "layers").mkdir(parents=True)
    (folder / "layers" / "base.usda").write_text("#usda 1.0\n")
    for path in (folder / "layers" / "base.usda", folder / "layers", folder):
        path.chmod(0o555 if path.is_dir() else 0o444)
    layer_base.writable(folder)
    (folder / "layers" / "base.usda").write_text("#usda 1.0\n")
    (folder / "layers" / "new.usda").write_text("#usda 1.0\n")


# --- every designed person is a look of the line ---

TORSO = [20, 10, 60, 90]  # the box of the worker's torso in a 100 x 100 concept
FAR_ROWS = [{"id": "far_crowd", "name": "crowd of people", "noun": "crowd", "count": 3, "route": "people",
             "anchor": "ground"},
            {"id": "stairs", "route": "prop", "anchor": "floor"},
            {"id": "man", "name": "man on the stairs", "noun": "man", "count": 1, "route": "people",
             "anchor": "on:stairs"},
            {"id": "far_stage", "route": "prop", "anchor": "ground"},
            {"id": "singer", "name": "singer on the far stage", "noun": "singer", "count": 1, "route": "people",
             "anchor": "on:far_stage"}]
# the deck as its design reads: a crowd on the plan item its row makes, three people in uniform on their own plan
# spots, a worker in a blue jumpsuit whose torso the concept paints, a chair, and the rows the plan shows beyond the
# place (a man on the deck's own stairs is the deck's; 2026-10-26: the stairwell's man and woman were made by nothing)
DECK_ROWS = [{"id": "crowd", "name": "crowd of people", "noun": "people", "count": 1, "route": "people"},
             {"id": "pilot", "name": "person in uniform", "noun": "person", "count": 3, "size": [0.5, 0.3, 1.8],
              "route": "people"},
             {"id": "worker", "name": "worker in blue jumpsuit", "where": "near the light", "noun": "worker",
              "count": 1, "size": [0.5, 0.3, 1.8], "route": "people", "boxes": [TORSO]},
             {"id": "chair", "name": "chair", "noun": "chair", "count": 1, "route": "prop", "anchor": "floor"},
             *FAR_ROWS]
DECK_PLAN = {"w": 20.0, "d": 10.0, "items": [["CROWD 1", 2.0, 1.0, 6.0, 4.0, None, "item"],
                                             ["BENCH 1", 0.0, 0.0, 1.0, 1.0, "N", "item"]],
             "rows": {"CROWD 1": ["crowd"], "BENCH 1": ["bench"]},
             "beyond": ["far_crowd", "man", "far_stage", "singer"],
             "people": [[1.0, 1.0, 0, "pilot"], [3.0, 2.0, 0, "pilot"], [5.0, 3.0, 0, "pilot"]]}
CROWD_SPREAD = [-8.0, -4.0, 6.0, 4.0]  # the CROWD item's box in the place's frame (unframed: the plan's middle at 0)
# (plan, row, its crowd ground): the plan items the row makes, none for another row or no plan
CROWD_GROUNDS = [(DECK_PLAN, "crowd", [CROWD_SPREAD]), (DECK_PLAN, "pilot", []), (None, "crowd", [])]
# (the crowd row's count, the crowd's count, its palettes): SAM 3's people when it told them apart, and never more
# variants of its look's body than it counted
CROWD_COUNTS = [(1, None, list(range(people_rows.CROWD_VARIANTS))), (30, 30, list(range(people_rows.CROWD_VARIANTS))),
                (3, 3, [0, 1, 2])]
# the people line's fabrics as sRGB stand-ins (every old surface retired on 2026-10-21)
BLUE = [38, 64, 150]
FABRICS = {"jacket_blue": BLUE, "suit_light_blue": [150, 180, 220], "suit_grey": [128, 128, 128]}
WHITES = {"white_suit": [235, 235, 235], "suit_seam": [60, 60, 60]}
WHITE = {"id": "astronaut", "name": "astronaut in white suit", "noun": "astronaut", "count": 1,
         "size": [0.5, 0.3, 1.8], "route": "people", "boxes": [TORSO]}
# (case, the row, the fabrics, the torso's sRGB or None for no concept kept, the fabric worn, its dE: "near" under 1,
# "far" over people_clothes.WITHIN, "between" within it, None unmeasured): the fabric its words name nearest the torso
# within WITHIN, a colour the words say theirs (a white suit in a dim concept is the white fabric, never the dark one
# nearer); a row naming none wears its look's own paint though its torso (one `box`) is measured
DRESSED = [("blue torso", DECK_ROWS[2], FABRICS, BLUE, "jacket_blue", "near"),
           ("orange torso", DECK_ROWS[2], FABRICS, [230, 90, 20], None, "far"),
           ("no concept", DECK_ROWS[2], FABRICS, None, None, None),
           ("shaded white suit", WHITE, WHITES, [70, 70, 72], "white_suit", "between"),
           ("names no fabric", {"id": "pilot", "name": "person", "noun": "person", "count": 1,
                                "size": [0.5, 0.3, 1.8], "route": "people", "box": TORSO}, FABRICS, BLUE, None, None)]
# (the crowd's words, its noun, the line it reads, its look): the look sharing the most of the row's words, a crowd
# word only between looks that share no other, a new look when none shares one; who the row names decides, never its
# crowd word alone; a look drawn from another scene's crowd row is that row's own, however its words match
CROWD_LOOKS = [("crowd of people", "people", "line", "citizen-coat"),  # "an ordinary citizen in the crowd"
               ("crowd of astronauts", "crowd", "line", "astronaut-work"),  # "an astronaut of a Moon base"
               ("flock of penguins", "penguin", "line", "flock_penguin-made"),  # its own words' (designed_specs)
               ("crowd of aliens", "crowd", "line", "alien-made"),
               ("crowd of martian colonists", "crowd", "line", "martian_colonist-made"),
               ("crowd of shoppers in grey coats", "crowd", "line", "citizen-coat"),
               ("crowd of people", "crowd", "square", "crowd-made"),
               ("crowd of people", "crowd", "both", "citizen-coat")]
# a design's people as people_rows.read() gives them, made into specs from the rows alone (#26): the pilot drawn from
# its largest standing person, never the bigger seated one
DESIGNED = {"places": {"deck": {"concept": "abcdef0123", "rows": {
    "pilot": {"name": "pilot in a red suit", "noun": "person", "count": 2, "size": [0.3, 0.4, 1.7],
              "where": "standing at the console", "share": 0.2, "looks": ["pilot_suit-made"] * 2},
    "guest": {"name": "seated guest", "noun": "person", "count": 1, "size": [0.7, 0.9, 1.3],
              "where": "sitting on a sofa", "looks": ["guest-made"]},
    "copilot": {"name": "seated pilot in a suit", "noun": "person", "count": 1, "size": [0.7, 0.9, 1.3],
                "where": "sitting at the console", "share": 0.5, "looks": ["pilot_suit-made"]},
    "crowd": {"name": "crowd of people", "noun": "crowd", "count": 1, "size": [8.0, 9.0, 1.8],
              "crowd": "crowd-made"}}}}}


def a_concept(srgb):
    """A 100 x 100 concept, dark, the torso box painted the given sRGB (0..255); None stays None (no concept kept)."""
    import numpy as np
    if srgb is None:
        return None
    picture = np.full((100, 100, 3), 20, dtype=np.uint8)
    left, top, right, bottom = TORSO
    picture[top:bottom, left:right] = srgb
    return picture


def kept_inventories(folder, rows):
    """A folder of kept inventories, {place: [rows]} each written as <place>.json."""
    folder.mkdir()
    for place, held in rows.items():
        (folder / f"{place}.json").write_text(json.dumps({"rows": held}))
    return folder


# --- an accepted gap moves only its named faults ---

ROWS = {row.name: row for row in stages.STAGES}


DECIDED = "owner, 2026-10-14 08:40"


def entry(name, row, check, objects, faults, **more):
    """One accepted gap in the file's form."""
    return {"name": name, "row": row, "check": check, "objects": objects, "reason": "a test's decision",
            "decided": DECIDED, "faults": faults, **more}


@contextlib.contextmanager
def decided(place_gaps):
    """gaps.FOLDER a folder of its own holding {place: [gap]} as the owner's files, for the length of a `with`."""
    held = gaps.FOLDER
    with tempfile.TemporaryDirectory() as folder:
        gaps.FOLDER = pathlib.Path(folder)
        for place, found in place_gaps.items():
            (gaps.FOLDER / f"{place}.json").write_text(json.dumps({"gaps": found}))
        try:
            yield
        finally:
            gaps.FOLDER = held


def recorded(place):
    return {gaps.NAME: str(gaps.FOLDER / f"{place}.json")}


def failed(check, findings):
    return checks.Verdict(check, checks.FAIL, f"{len(findings)} faults", {"faults": len(findings)},
                          {"faults": "lower"}, tuple(findings))


RESTING = entry("fragments: resting in the regolith", "assembly", "resting",
                [f"/wreck/Objects/fragment_{number}" for number in (1, 2)],
                [f"/wreck/Objects/fragment_{number}: sunk 0.05 under its contact points" for number in (1, 2)])


SHIP = entry("ship: no made model", "assembly", "placeholders",
             ["/hangar/Structure/ship", "/hangar/Structure/ship_legs"],
             [f"/hangar/Structure/{name}: plain: drawn by the record's {name} builder (a made piece's stand-in)"
              for name in ("ship", "ship_legs")])


ORDER = entry("fluid shelves: order", "surfaces-check", "baked matches its surfaces", ["fluid_shelves_1"],
              ["fluid_shelves_1: plastic_grey baked over galvanized_steel: the close-up's order reversed"],
              contains="order")


ROWS_GAP = entry("far ferry: no stage makes it", "complete", "rows", ["far_ferry"],
                 [json.dumps({"row": "far_ferry", "why": "no object of this row"})])


BOXES_GAP = entry("wall screen: its box", "complete", "boxes", ["wall_screen"],
                  [json.dumps({"row": "wall_screen", "result": "fail", "why": "judge: no screen in the box"})])


GAME = entry("launch: layout taken from the source game", "complete", "game", ["data/scene/launch.json"],
             ["data/scene/launch.json: 12 entries take their numbers from the game (source), 4 positions placed"])


CASES = {  # gap, another fault of the same gate no gap names
    "plain objects": (RESTING, "/wreck/Objects/fragment_3: floats 0.04: nothing under it"),
    "placeholders": (SHIP, "/hangar/Structure/crate: plain: drawn by the record's box builder (a made piece's "
                           "stand-in)"),
    "of its kind only": (ORDER, "fluid_shelves_1: crane_yellow_paint baked [70.1, 5.0, 60.2] against [74.0, 4.1, "
                                "70.3] (dE 36.4)"),
    "rows by row": (ROWS_GAP, json.dumps({"row": "far_tower", "why": "no object of this row"})),
    "boxes by row": (BOXES_GAP, json.dumps({"row": "bunk", "result": "fail", "why": "judge: x"})),
    "a record by its path": (GAME, "scene-record output x/record/launch.json: 1 entries take their numbers from the "
                                   "game (source), 1 positions placed from it"),
}
NAMED_UNKNOWN = entry("launch: no likeness output", "complete", "likeness", [], [],
                      unknown="no accepted likeness@street")  # the overseer, 2026-10-15: no props file answers it


def unknown(check, reason):
    return checks.Verdict(check, checks.UNKNOWN, reason)


# (case, the gate's verdict, the gaps it is judged against, the answer after the move or None when it is left alone,
# the faults it says it moved): only the named faults move and any other still stops the line; a named unknown moves
# and another unknown, or one no gap names, stays
MOVED = [
    *[(f"{case}: its named faults", failed(gap["check"], gap["faults"]), [gap], checks.PASS, len(gap["faults"]))
      for case, (gap, _) in CASES.items()],
    *[(f"{case}: another fault beside them", failed(gap["check"], [*gap["faults"], other]), [gap], checks.FAIL, None)
      for case, (gap, other) in CASES.items()],
    ("a named unknown", unknown("likeness", "no accepted likeness@street"), [NAMED_UNKNOWN], checks.PASS, 1),
    ("another unknown", unknown("likeness", "2 generated rows and no accepted likeness@launch"), [NAMED_UNKNOWN], None,
     None),
    ("an unknown no gap names", unknown("resting", "no drop run"), [RESTING], None, None),
]

# the owner's pipe gap at the garage (#36, 2026-10-29: 37aa882c deleted it): (case, the record after, what it dropped)
PIPE = {"name": "pipe: its path build cannot match", "row": "likeness", "check": "outline"}
DROPPED = [
    ("kept", {"garage": {"gaps": [PIPE]}}, []),
    ("the file deleted", {}, ["garage: pipe: its path build cannot match"]),
    ("emptied", {"garage": {"gaps": []}}, ["garage: pipe: its path build cannot match"]),
    ("retired on no output", {"garage": {"gaps": [], "retired": [dict(PIPE, passed="")]}},
     ["garage: pipe: its path build cannot match"]),
    ("retired on a passing output", {"garage": {"gaps": [], "retired": [dict(PIPE, passed="likeness@garage 1a2b3c")]}},
     []),
]

# (place, row, whether the row reads the place's gaps): a street's gaps (complete's alone) made the paid paint at three
# places run again (the overseer, 2026-10-15)
GAP_READERS = [("street", "assembly", False), ("street", "surfaces-check", False), ("street", "surfaces-paint", False),
               ("street", "complete", True), ("lab", "assembly", True), ("lab", "surfaces-paint", False)]

# the gates the table wraps in the gap mover
GAPPED_GATES = [("assembly", "placeholders"), ("assembly", "resting"), ("surfaces-check", "stands level"),
                ("surfaces-check", "baked matches its surfaces"), ("surfaces-paint", "colour against the close-up"),
                ("complete", "people"), ("complete", "likeness"), ("complete", "motion"), ("complete", "rows"),
                ("complete", "game"), ("complete", "boxes")]

CRANE = entry("crane: a foot off the floor", "complete", "resting", ["/campgrounds/Objects/crane_1"],
              ["/campgrounds/Objects/crane_1: foot 2 3.2 cm off the floor"])
FAR_CITY = {"name": "far_city: shown by the plan, not stood", "row": "neighbours", "check": "neighbours",
            "objects": ["/flat/Places/far_city"], "reason": "its seed went with the old disk",
            "decided": "lost input, 2026-10-19 (the old disk)", "faults": []}  # lost with the old disk, #10


def dropped(before, after):
    """The owner's gaps in `before` ({place: its gaps file's record}) that `after` no longer lists, in its `gaps` or
    as `retired` with the output its item passed on (`passed`): a deleted file or an emptied entry counts."""
    found = []
    for place, record in before.items():
        kept = after.get(place) or {}
        listed = {entry.get("name") for entry in kept.get("gaps", [])}
        retired = {entry.get("name") for entry in kept.get("retired", []) if entry.get("passed")}
        found += [f"{place}: {entry['name']}" for entry in record.get("gaps", [])
                  if entry["name"] not in listed | retired]
    return found


def git_gaps(commit):
    """data/checks/gaps as `commit` holds it ({place: record})."""
    listing = subprocess.run(["git", "ls-tree", "--name-only", commit, "data/checks/gaps/"], cwd=REPO, check=True,
                             capture_output=True, text=True).stdout.split()
    return {pathlib.Path(name).stem: json.loads(subprocess.run(["git", "show", f"{commit}:{name}"], cwd=REPO,
                                                               check=True, capture_output=True, text=True).stdout)
            for name in listing if name.endswith(".json")}


# --- a failed paid take is a gap carried down its line ---

OBJECTS = {"crate": {"route": "prop", "take": "crate-s1"},
           "hatch": {"route": "prop", "take": "hatch-s1", "rows": ["hatch"]}}


def written(folder, name, found):
    path = folder / name
    path.write_text(json.dumps(found))
    return path


def fake_batch(made):
    """subprocess.run as the Pixal3D batch would answer: only the takes in `made` come back (raw model and camera
    folder; the batch exits 0 and names the rest gaps), and the finish here writes each job's finished models."""
    def run(command, **options):
        pixal = pixal_row.take_files("any")[0].parent
        pixal.mkdir(parents=True, exist_ok=True)
        if command[1].endswith("batch.py"):
            for line in pathlib.Path(command[2]).read_text().splitlines():
                take = line.split()[0]
                if take in made:
                    (pixal / f"{take}.glb").write_text("raw")
                    (pixal / f"{take}.svviews").mkdir(exist_ok=True)
        else:  # every finish one blender_cloud.py call of job files, each bringing its outputs back (484e538e)
            for job in (json.loads(pathlib.Path(path).read_text()) for path in command[2:] if path.endswith(".json")):
                for output in job["outputs"]:
                    pathlib.Path(output).write_text("finished")
        return subprocess.CompletedProcess(command, 0, "", "")
    return run


def pixal_made(made):
    """A Pixal3D row's output from a batch that brought back `made` only, and its inputs."""
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "closeup" / "closeups").mkdir(parents=True)
    for row in OBJECTS:
        (folder / "closeup" / "closeups" / f"{row}.png").write_text("close-up")
    # the close-up row's record of the rows it worked on, which the takes gate narrows to (a8ebe414)
    written(folder / "closeup", "closeups.json", {"objects": {row: {"drawn_by": "drawn"} for row in OBJECTS}})
    entries = {row: {"faces": 1000} for row in OBJECTS}
    inputs = {"closeup": folder / "closeup",
              "props": written(folder, "props.json", {"place": "toy", "objects": OBJECTS}),
              "surfaces": written(folder, "surfaces.json", {
                  "place": "toy", "takes": {entry["take"]: {} for entry in OBJECTS.values()},
                  "bake": {"models": {row: entry["take"] for row, entry in OBJECTS.items()}, "entries": entries}}),
              # each object's reading row: its size says how its close-up was drawn (pixal_row.lies_flat)
              "inventory": written(folder, "inventory.json", {"rows": [{"id": row, "size": [0.6, 0.6, 0.6]}
                                                                       for row in OBJECTS]})}
    out = folder / "pixal"
    out.mkdir()
    running, pixal_row.subprocess.run = pixal_row.subprocess.run, fake_batch(made)
    try:
        pixal_row.make_pixal(inputs, out, 0, {})
    finally:
        pixal_row.subprocess.run = running
    return out, inputs


# The fixture batch: the prop route's rows by their table names, each a toy make, wrapped by the table's own gap
# mover (stages.accepted_gaps) as the real rows are.
TOY = contracts.Contract("toy", 1, lambda folder: [])


def make_pixal(inputs, out, seed, params):
    """Two takes asked; the batch brought the crate back and not the hatch (its job failed: a gap), unless the brief
    says it lost the crate too and named no gap for it."""
    brief = inputs["brief"].read_text()
    (out / "takes.json").write_text(json.dumps({"crate": "lost" not in brief, "hatch": False}))
    batch_gaps.write(out, [batch_gaps.gap("hatch: Pixal3D made no model", "pixal", "takes", ("hatch", "hatch-s1"),
                                          ["hatch: no hatch-s1.glb"], "the Pixal3D job ran once and failed")])


def judge_takes(output, inputs, evidence):
    takes = json.loads((output / "takes.json").read_text())
    failing = [f"{row}: no {row}-s1.glb" for row, made in sorted(takes.items()) if not made]
    return checks.Verdict("takes", checks.FAIL if failing else checks.PASS, f"{len(failing)} takes not made",
                          {"faults": len(failing)}, {"faults": "lower"}, tuple(failing))


def make_carried(inputs, out, seed, params):
    """A row after the take: works on the made takes, the batch gaps' left out and carried on."""
    batch_gaps.write(out, batch_gaps.of(inputs))
    (out / "made.json").write_text(json.dumps(["crate"]))


def judge_cast(output, inputs, evidence):
    """The views judge only the takes they worked on (the real row's: a left-out take is not in its views.json)."""
    return checks.Verdict("views cast", checks.PASS, f"{len(json.loads((output / 'made.json').read_text()))} cast")


def judge_rows(name):
    """A gate that fails each object of the place's two with no made model by name (as likeness and complete do)."""
    def judge(output, inputs, evidence):
        made = json.loads((output / "made.json").read_text())
        failing = [f"{row}: no model" for row in ("crate", "hatch") if row not in made]
        return checks.Verdict(name, checks.FAIL if failing else checks.PASS, f"{len(failing)} not made",
                              {"faults": len(failing)}, {"faults": "lower"}, tuple(failing))
    return judge


def fixture_line(brief):
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "dock").mkdir()
    (data / "dock" / "brief.txt").write_text(brief)
    rows = (graph.Stage("pixal", "place", make_pixal, TOY, (checks.Check("takes", judge_takes),),
                        files={"brief": "{data}/{place}/brief.txt"}),
            graph.Stage("finish-route-views", "place", make_carried, TOY,
                        (checks.Check("views cast", judge_cast),), after={"pixal": ("toy", 1)}),
            graph.Stage("likeness", "place", make_carried, TOY, (checks.Check("outline", judge_rows("outline")),),
                        after={"finish-route-views": ("toy", 1)}),
            graph.Stage("complete", "place", make_carried, TOY, (checks.Check("rows", judge_rows("rows")),),
                        after={"likeness": ("toy", 1)}))
    world = graph.Environment("toy", 7, {"data": data})
    return graph.Runner(tuple(map(stages.accepted_gaps, rows)), world, Store.in_folder(tempfile.mkdtemp()),
                        model_record=lambda kind: {})


# (brief, what the line says at its nodes): the batch's gap carried on to complete; a take lost with no gap stops it
LINES = [("the batch", {"pixal@dock": "made: pass, accepted automatically",
                        "likeness@dock": "made: pass, accepted automatically"}),
         ("the batch lost the crate", {"likeness@dock": "not run: its line stopped at pixal@dock"})]


def painted(folder):
    """A surfaces-bake output whose take `crate-s1` has a finish off its close-up's colour and `hatch-s1` none, with
    the bake's entries (each take's models) and checks.json as the check's step writes it: `crate` over its budget."""
    baked = folder / "surfaces-bake"
    clean = {"unnamed_parts": 0, "unnamed_share": 0.0, "finishes": [], "feet": {}}
    off = dict(clean, finishes=[{"finish": "lid", "by": "off its colour", "measured_lab": [30.0, 0.0, 0.0],
                                 "surface": "panel", "delta_e": 40.0, "new_surface": {"name": "panel_dark"}}])
    (baked / "labelled" / "crate-s1").mkdir(parents=True)
    (baked / "entries").mkdir()
    written(baked, "painted.json", {"takes": {"crate-s1": off, "hatch-s1": clean}, "left_out": {}})
    written(baked / "entries", "crate-s1.json", {"crate": {}})
    written(baked / "entries", "hatch-s1.json", {"hatch": {}})
    written(baked, "baked.json", {"crate": {"parts": "crate-s1"}, "hatch": {"parts": "hatch-s1"}})
    written(baked, "specs.json", {})
    record = {"missing_maps": [], "surfaces": {}, "triangles": 100, "budget": 1000, "stands": False}
    return baked, {"crate": dict(record, triangles=5000), "hatch": record}


def measured_clean(monkeypatch):
    """The paint's bake measure (baked_colour.py, the prop environment's) run here, every baked model clean."""
    import baked_colour
    monkeypatch.setattr(baked_colour, "measure_model", lambda model, entry, bake, specs: {})
    monkeypatch.setattr(baked_colour, "measured",
                        lambda inputs, out: baked_colour.measure_step(baked_colour.prop_env.short(inputs), out))


# --- push gate names the paid rows it moves ---

TEXT = contracts.Contract("toy-text", 1, lambda folder: [])


RENDER_MAKE = """import toy_frame


def make(inputs, out, seed, params):
    (out / "text.txt").write_text(toy_frame.WORD + inputs["brief"].read_text())
"""


def make_copy(inputs, out, seed, params):
    (out / "text.txt").write_text(inputs["brief"].read_text())


def make_film(inputs, out, seed, params):
    (out / "text.txt").write_text((inputs["draw"] / "text.txt").read_text())


def judge_said(output, inputs, evidence):
    return checks.Verdict("said", checks.PASS, "a text was written")


SAID = (checks.Check("said", judge_said),)


def git(repo, *words):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=toy", "-c", "user.email=toy@example.com",
                           *words], capture_output=True, text=True, check=True).stdout.strip()


def committed(repo, message="toy"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def command():
    from score import __main__
    return __main__


@contextlib.contextmanager
def toy():
    """A git repository standing in for this one (the render's make, a framework file it imports, three data files)
    for the time of a `with`; the framework's globals and the command's hooks are put back afterwards."""
    main = command()
    kept = (_code.REPO, _code.FRAMEWORK, moved.REPO, list(sys.path), compute.books_refusal,
            moved.moved)
    repo = pathlib.Path(tempfile.mkdtemp()).resolve()
    git(repo, "init", "-q")
    (repo / "toy_render.py").write_text(RENDER_MAKE)
    (repo / "toy_frame.py").write_text('WORD = "made: "\n')
    (repo / ".gitignore").write_text("__pycache__/\n")  # an import's bytecode is no change to the tree
    (repo / "render.txt").write_text("a hall")
    (repo / "bake.txt").write_text("a hall's light")
    (repo / "draw.txt").write_text("a hall's plan")
    committed(repo)
    _code.REPO = moved.REPO = repo
    _code.FRAMEWORK = _code.FRAMEWORK | {repo / "toy_frame.py"}
    compute.books_refusal = lambda: None  # the month's books are compute_test's; not this one's
    sys.path.insert(0, str(repo))
    _code.search_folders.cache_clear()
    sys.modules.pop("toy_render", None)
    sys.modules.pop("toy_frame", None)
    try:
        yield repo
    finally:
        (_code.REPO, _code.FRAMEWORK, moved.REPO, sys.path[:], compute.books_refusal,
         moved.moved) = kept
        _code.search_folders.cache_clear()


def a_runner(repo, store, bake_params=None):
    render = graph.Stage("render", "place", importlib.import_module("toy_render").make, TEXT, SAID,
                         files={"brief": "{data}/render.txt"}, paid=True, euros=4.0)
    bake = graph.Stage("bake", "place", make_copy, TEXT, SAID, files={"brief": "{data}/bake.txt"}, paid=True,
                       euros=3.0, params=bake_params or {})
    draw = graph.Stage("draw", "place", make_copy, TEXT, SAID, files={"brief": "{data}/draw.txt"})
    film = graph.Stage("film", "place", make_film, TEXT, SAID, after={"draw": ("toy-text", 1)}, paid=True, euros=2.0)
    return graph.Runner([render, bake, draw, film], graph.Environment("toy", 1, {"data": repo}), store,
                        model_record=lambda kind: {"kind": kind})


def made(repo):
    """Every row made and accepted at the toy repository's commit; their store."""
    store = Store.in_folder(tempfile.mkdtemp())
    runner = a_runner(repo, store)
    for stage in runner.stages.values():
        assert "accepted automatically" in runner.run_node(stage, "hangar"), stage.name
    return store


def rebought(repo, store, **table):
    runner = a_runner(repo, store, **table)
    return {"toy": moved.rebuys(runner, list(runner.nodes(["hangar"])))}


def exit_code(call, *args):
    """What `call` printed and its exit code (0 when it returned)."""
    with contextlib.redirect_stdout(io.StringIO()) as printed, contextlib.redirect_stderr(io.StringIO()) as said:
        try:
            call(*args)
        except SystemExit as stop:  # sys.exit("message") prints its message and exits 1
            message = stop.code if isinstance(stop.code, str) else ""
            return printed.getvalue() + said.getvalue() + message, 1 if message else stop.code
    return printed.getvalue() + said.getvalue(), 0


def pushed(repo, message, files):
    """Commit `files` ({name: text}) over the toy repository's tip; (the git push line to main, tip)."""
    base = git(repo, "rev-parse", "HEAD")
    for name, text in files.items():
        (repo / name).write_text(text)
    tip = committed(repo, message)
    return f"refs/heads/main {tip} refs/heads/main {base}", tip


def snap(repo, store, **table):
    """moved.row_entry of every toy row: the snapshot the toy's working tree gives."""
    runner = a_runner(repo, store, **table)
    return {row.name: moved.row_entry(runner, row, ["hangar"], repo) for row in runner.stages.values()}


def moves(found):
    """moved.moved_rows' answer as {row: (paid, its code moved, its moved files)}."""
    return {name: (row["paid"], row["code"], row["files"]) for name, row in found.items()}


# (case, files written over the toy's commit, the table's change, the paid rows `score moved` lists (node, euros, why),
# the rows the push gate finds moved, what its refusal says (none: the push goes)): a declared file moves its paid
# row; a framework-only edit nothing; a free row's file the paid row reading it (a run's re-buy question before it
# starts, never the push's); a table edit (a row's params here; a contract, a model or an after alike) moves the row
# with no file of its own changed, refused like any other
TREE_EDITS = [
    ("nothing changed", {}, {}, [], {}, []),
    ("a file one paid row reads", {"bake.txt": "a hall's brighter light"}, {}, [("bake@hangar", 3.0, "brief changed")],
     {"bake": (True, False, {"bake.txt": ["hangar"]})}, ["bake (paid): bake.txt (1 places)", "Moved-rows: bake: <why>"]),
    ("a framework-only edit", {"toy_frame.py": 'WORD = "made by the framework: "\n'}, {}, [], {}, []),
    ("a row moved through what it reads", {"draw.txt": "a hall's new plan"}, {}, [("film@hangar", 2.0, "reads draw@hangar")],
     {"draw": (False, False, {"draw.txt": ["hangar"]})}, []),
    ("a move no file explains", {}, {"bake_params": {"light": 2}}, None, {"bake": (True, True, {})},
     ["Moved-rows: bake: <why>"]),
]

# (git's pre-push lines, the (local sha, remote sha) pushes to main among them): a deletion, a tag and another branch
# are none
TIP, BASE = "a" * 40, "b" * 40
NOT_MAIN = [f"refs/heads/main {moved.ZERO} refs/heads/main {BASE}", f"refs/tags/v1 {TIP} refs/tags/v1 {moved.ZERO}",
            f"refs/heads/side {TIP} refs/heads/side {BASE}"]
PUSH_LINES = [(NOT_MAIN, []), (NOT_MAIN + [f"HEAD {TIP} refs/heads/main {BASE}"], [(TIP, BASE)])]

# (row, Moved-rows trailer values, named): "<row or node> ...: <reason>" names a row by its name or a node of it, an
# environment's prefix left off or not; never with no reason, only in another row's reason, or by another row's prefix
ROW_NAMED = [("bake", ["bake@hangar film@hangar: the owner asked"], True), ("film", ["bake, film: the owner asked"], True),
             ("images:image-proof-runner", ["image-proof-runner: a new build"], True),
             ("bake", ["bake@hangar"], False), ("bake", ["bake@hangar:  "], False),
             ("bake", ["film@hangar: it reads bake@hangar"], False), ("bake", ["bake2@hangar: another row"], False)]

HOOK = REPO / ".claude/hooks/local/pre-push-moved"


RECORDER = """import json, os, pathlib, sys
pathlib.Path(os.environ["HOOK_RECORD"]).write_text(json.dumps({"cwd": os.getcwd(), "argv": sys.argv[1:],
    "stdin": sys.stdin.read(), "python": sys.executable, "home": os.environ.get("PROPS_HOME")}))
sys.exit(int(os.environ.get("HOOK_EXIT", "0")))  # stands in for: score moved --pre-push
"""


STALLED = """import os, pathlib, sys
del sys.modules["score"]  # this toy package: the real score command is loaded in its place
sys.path.insert(0, os.environ["SCORE_REPO"])
from score import __main__ as real
from score.stages import moved
moved.REPO = pathlib.Path.cwd()
sleeper = "import os, pathlib, time; pathlib.Path(%r).write_text(str(os.getpid())); time.sleep(600)"
moved.moved = lambda base, head=None: moved.snapshot("HEAD", sleeper % os.environ["HOOK_RECORD"])
real.main(["moved", "--pre-push"])  # never --pre-push --again
"""


def hook_repo(command_text=RECORDER):
    """A toy repository whose score package records how the hook ran it (or runs `command_text`), with its own .venv
    python; it sits alone in a folder of its own, where moved.snapshot puts its checkouts."""
    repo = pathlib.Path(tempfile.mkdtemp()).resolve() / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "score").mkdir()
    (repo / "score/__init__.py").write_text("")
    (repo / "score/__main__.py").write_text(command_text)
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n")
    (repo / ".venv/bin").mkdir(parents=True)
    (repo / ".venv/bin/python").symlink_to(sys.executable)
    committed(repo)
    return repo


def stalled_repo():
    """A hook repository whose score command works out a commit in a checkout of its own while its child sleeps,
    with this environment's own python (a bare link to it would leave the venv)."""
    repo = hook_repo(STALLED)
    python = repo / ".venv/bin/python"
    python.unlink()
    python.write_text(f'#!/usr/bin/env bash\nexec {sys.executable} "$@"\n')
    python.chmod(0o755)
    return repo


def hook(where, push_lines, exit_with=0, env=None):
    """Run .claude/hooks/local/pre-push-moved in `where` (with `env` added to its environment, a None value taken out
    of it; PROPS_HOME a home holding a store unless `env` names one; TMPDIR an empty folder of its own; `timeout` a
    shim recording the limit it was given); (its exit code, its output, the recorder's record or None, the timeout's
    limit or None, its TMPDIR)."""
    scratch = pathlib.Path(tempfile.mkdtemp())
    record, limit, temp, shim, home = (scratch / "record.json", scratch / "limit.txt", scratch / "tmp", scratch / "shim",
                                       scratch / "home")
    for folder in (temp, shim, home / "store/objects"):
        folder.mkdir(parents=True)
    (shim / "timeout").write_text(f'#!/usr/bin/env bash\necho "$1" > "$TIMEOUT_RECORD"\n'
                                  f'exec {shutil.which("timeout")} "$@"\n')
    (shim / "timeout").chmod(0o755)
    environment = {**os.environ, "PROPS_HOME": str(home), "HOOK_RECORD": str(record), "HOOK_EXIT": str(exit_with),
                   "TMPDIR": str(temp), "PATH": f"{shim}:{os.environ['PATH']}", "TIMEOUT_RECORD": str(limit),
                   **(env or {})}
    ran = subprocess.run(["bash", str(HOOK), "origin", "toy"], cwd=where, input="\n".join(push_lines) + "\n",
                         capture_output=True, text=True,
                         env={name: value for name, value in environment.items() if value is not None})
    return (ran.returncode, ran.stdout + ran.stderr, json.loads(record.read_text()) if record.exists() else None,
            limit.read_text().strip() if limit.exists() else None, temp)


def gone(pid):
    """True once process `pid` has ended (waited for up to 10 s)."""
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.1)
    return False


GONE = "a checkout of the pushed commit, removed afterwards"
ENDED = "the pid of a child that has ended"
MAIN_LINE = "refs/heads/main {tip} refs/heads/main {zero}"

# (case, repository, run in, its push line, score.movedCheck, score.movedTimeout, a loose file, the score command's
# exit, environment, the hook's exit, what it says (empty: nothing), the record its score command wrote, the
# timeout's limit): the hook is off until the owner turns it on and passes deletions, tags and other branches at once;
# it runs the command in this checkout at the pushed commit, else in a worktree of it, removed afterwards, and
# refuses when none can be made; a commit made before score moved is not checked; it reads the places from PROPS_HOME,
# else the default home once it holds a store, else this PC's run home, and with none goes on, said; a worktree runs
# the main checkout's python; the check has an hour unless told otherwise, and one that runs out of time ends its child
HOOK_CASES = [
    ("off", "repo", "repo", MAIN_LINE, False, None, False, 0, {}, 0, "", None, None),
    ("on", "repo", "repo", MAIN_LINE, True, None, False, 0, {}, 0, "",
     {"cwd": "{repo}", "argv": ["moved", "--pre-push"], "stdin": MAIN_LINE + "\n",
      "python": "{repo}/.venv/bin/python"}, "3600"),
    ("its exit passed on", "repo", "repo", MAIN_LINE, True, None, False, 3, {}, 3, "", {"cwd": "{repo}"}, "3600"),
    ("a deletion", "repo", "repo", "(delete) {zero} refs/heads/main {tip}", True, None, False, 3, {}, 0, "", None, None),
    ("a tag", "repo", "repo", "refs/tags/v1 {tip} refs/tags/v1 {zero}", True, None, False, 3, {}, 0, "", None, None),
    ("another branch", "repo", "repo", "refs/heads/side {tip} refs/heads/side {zero}", True, None, False, 3, {}, 0, "",
     None, None),
    ("a changed tree", "repo", "repo", MAIN_LINE, True, None, True, 0, {}, 0, "", {"cwd": GONE}, "3600"),
    ("no worktree can be made", "repo", "repo", "refs/heads/main {unknown} refs/heads/main {zero}", True, None, False,
     0, {}, 1, "refused", None, None),
    ("before score moved", "repo", "repo", "refs/heads/main {older} refs/heads/main {zero}", True, None, False, 0, {}, 0,
     "predates score moved", None, None),
    ("no home with a store", "repo", "repo", MAIN_LINE, True, None, False, 0, {"PROPS_HOME": "{bare}"}, 0,
     "no home with a store", None, None),
    ("this PC's run home", "repo", "repo", MAIN_LINE, True, None, False, 0,
     {"PROPS_HOME": None, "HOME": "{bare}", "SCORE_THIS_PC_HOME": "{pulled}"}, 0, "", {"home": "{pulled}"}, "3600"),
    ("the default home first", "repo", "repo", MAIN_LINE, True, None, False, 0,
     {"PROPS_HOME": None, "HOME": "{homed}", "SCORE_THIS_PC_HOME": "{pulled}"}, 0, "",
     {"home": "{homed}/.farm-factory-props"}, "3600"),
    ("a worktree", "repo", "tree", MAIN_LINE, True, None, False, 0, {}, 0, "",
     {"cwd": "{tree}", "python": "{repo}/.venv/bin/python"}, "3600"),
    ("out of time", "stalled", "stalled", "refs/heads/main {tip} refs/heads/main {tip}", True, "15", False, 0,
     {"SCORE_REPO": str(REPO)}, 124, "ran past 15 s", ENDED, "15"),
]


def placed(value, world):
    """`value` with every {name} of `world` filled in (a list's items alike)."""
    if isinstance(value, list):
        return [placed(item, world) for item in value]
    return value.format(**world) if isinstance(value, str) else value


def hook_world():
    """The hook's two repositories, the worktree of the first, its commit made before score moved, and the homes the
    hook reads from: no store, this PC's run home and a default home holding a store; {name: path or commit}."""
    repo, stalled = hook_repo(), stalled_repo()
    folders = {name: pathlib.Path(tempfile.mkdtemp()).resolve() for name in ("bare", "pulled", "homed", "trees")}
    (folders["pulled"] / "store/objects").mkdir(parents=True)
    (folders["homed"] / ".farm-factory-props/store/objects").mkdir(parents=True)
    tree = folders.pop("trees") / "tree"
    git(repo, "worktree", "add", "-q", "--detach", str(tree))
    tip = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "-b", "older")
    (repo / "score/__main__.py").write_text(RECORDER.replace("score moved --pre-push", "an older command"))
    older = committed(repo, "before score moved")
    git(repo, "checkout", "-q", "-")
    return {"repo": repo, "stalled": stalled, "tree": tree, "tip": tip, "older": older, "zero": moved.ZERO,
            "unknown": "f" * 40, **folders}


def configured(repo, key, value):
    """Set git config `key` to `value` in `repo`, or take it out when None."""
    words = ["config", key, value] if value is not None else ["config", "--unset-all", key]
    subprocess.run(["git", "-C", str(repo), *words], capture_output=True, check=value is not None)


# --- a per-take function the table keeps reads only what its key holds -------------------------------------------------

OPENED = []  # the paths opened while a traced per-take call runs (TRACING): sys.audit's hook cannot be taken off
TRACING = []
PYTHON_HOMES = tuple(pathlib.Path(folder).resolve() for folder in {sys.prefix, sys.base_prefix, sys.exec_prefix})
SYSTEM_FOLDERS = tuple(pathlib.Path(folder) for folder in ("/proc", "/sys", "/dev"))


def opened_hook(event, arguments):
    if event == "open" and TRACING and isinstance(arguments[0], (str, bytes, os.PathLike)):
        OPENED.append(os.fsdecode(arguments[0]))


def argument_paths(value):
    """Every file or folder a per-take call's arguments name."""
    if isinstance(value, dict):
        return [path for item in value.values() for path in argument_paths(item)]
    if isinstance(value, (list, tuple)):
        return [path for item in value for path in argument_paths(item)]
    if isinstance(value, pathlib.PurePath) or isinstance(value, str) and value.startswith("/"):
        return [pathlib.Path(value).resolve()]
    return []


def outside_its_key(path, named):
    """Whether a file a per-take call opened is none of: a file or folder its arguments name, the repository's Python
    (the row's code), or Python's own installation and the system's own files."""
    path = pathlib.Path(path).resolve()
    return not (any(path == folder or path.is_relative_to(folder) for folder in (*named, *PYTHON_HOMES,
                                                                                  *SYSTEM_FOLDERS))
                or path.is_relative_to(REPO) and (path.suffix in (".py", ".pyc") or "__pycache__" in path.parts))


def test_each_per_take_function_opens_only_its_arguments_its_code_and_python(tmp_path, monkeypatch):
    """kept.call hands a take back whenever its function, its arguments and the files they name, the row's code and
    this Python are the same (the table's PER_TAKE, owner, 2026-10-29), so each function it keeps must read nothing
    else: run on the surface line's own fixtures (views, list, split and parts of its two boxes), every file each
    per-take call opens is one its arguments name, the repository's Python or Python's own."""
    fixtures_path = REPO / "score/stages/surfaces/test_every_part_takes_a_library_surface_and_is_held_to_it.py"
    spec = importlib.util.spec_from_file_location("surface_line_fixtures", fixtures_path)
    fixtures = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixtures)
    if not getattr(sys, "per_take_hook", False):
        sys.addaudithook(opened_hook)
        sys.per_take_hook = True
    rows = {row.name: row for row in stages.STAGES}
    called, opened = [], {}
    for name, (function_name, _) in stages.PER_TAKE.items():
        namespace = inspect.unwrap(rows[name].make).__globals__
        function = namespace[function_name]

        def traced(*arguments, function=function, function_name=function_name):
            called.append(function_name)
            OPENED.clear()
            TRACING.append(function_name)
            try:
                return function(*arguments)
            finally:
                TRACING.clear()
                found = list(OPENED)
                opened[function_name] = opened.get(function_name, 0) + len(found)
                strays = [path for path in found if outside_its_key(path, argument_paths(list(arguments)))]
                assert not strays, f"{function_name} opened files its key does not hold: {strays}"
        monkeypatch.setitem(namespace, function_name, traced)
    rows_made, _ = fixtures.listed(tmp_path, lambda views, take: fixtures.two_finish_answer(views))
    fixtures.parted(tmp_path, fixtures.split(tmp_path, rows_made))
    assert set(called) == {"view_take", "split_take", "parts_take"}, called
    assert all(opened.values()), opened  # each read its inputs through the traced opens
