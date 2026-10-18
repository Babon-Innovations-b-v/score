# The bible

The single source of truth for how this system works. One file, chaptered. A chapter ID is the
slug after the `##` (for example `architecture/system-context`), and the chapter map in root
[`CLAUDE.md`](../CLAUDE.md) points at it; link to a chapter as `docs/bible.md#architecturesystem-context`.

**How to use it.** Read the chapter the work touches, never the whole file. When you learn
something load-bearing that a future reader would otherwise have to re-derive from code, write it
into its chapter in the same session. When a chapter contradicts the code, the code wins and the
chapter gets fixed on the spot.

**What does not go here.** Vocabulary goes in [`CONTEXT.md`](../CONTEXT.md). Decisions that were
hard to reverse go in [`docs/adr/`](adr/). Status of ongoing work goes on its GitHub issue. The
bible holds how the thing works, not what we are doing about it.

A chapter that is still a placeholder says so in one line. An empty chapter is honest; an invented
one is not.

---

## architecture/system-context

<The big picture in one screen: what this system is, who or what talks to it, what it talks to.
Placeholder until the first real component exists.>

## architecture/components

The framework moved here from the game 2099 on 2026-10-08 (JoeyKardolus/2099#129), with its history (git
filter-repo on the moved paths). Two sides: the coordinating machine runs plain Python (plans, labels, checks, the
scene package; `.venv` from `pyproject.toml`), and every step that loads a model, bakes or renders runs on a rented
cloud machine that deletes itself (`tools/props/cloud/`, through the provider interface `provider.py`; Scaleway is
the current backend). No model runs on the coordinating machine.

- `tools/props/`: the prop pipeline (close-up to Pixal3D in a cloud batch, `cloud/batch.py`; finish; `pixal.py`),
  the scene tools (`scene/`: concepts, the world step, close-ups, inventories, layouts), the surface library and its
  piece making (`library/`: recipes, labels by parts, `make_chunky`/`make_kit` baked in the cloud, `route.py` for kit
  rooms, `place_route.py` for outdoor places, `package.py` for the scene package) and the gates (`gates/`). Each directory's rules are in its overlay.
- `tools/characters/`: the characters stage. `people/` builds each person's skinned, animated glTF (SOMA-X body
  shaped by SAM 3D Body, clips written by Kimodo from sentences, GarmentCode patterns draped by the cloth solver the
  spec names, the drapes being experimental;
  moved from 2099's `tools/crew` with its history). `maker/` is the character maker, one entry (`make.py`) for a
  person or an animal from a picture or a few words (`data/characters/makes/<name>.json`): a person's whole chain
  (picture, body by SAM3DBody-cpp, clips by Kimodo, drapes, head, hair by Hi3DGen, face by klein with a depth LoRA,
  build, UsdSkel, review renders) runs on one rented card (`tools/props/cloud/characters.py`), an animal's through
  `animals/` (experimental). A person spec with `"route": "prop"` takes the prop route instead
  (`maker/prop_person.py`, experimental, a trial whose takes stay in
  `~/.farm-factory-motion/candidates/prop-people/`): Pixal3D's mesh, SOMA-X's skeleton placed inside it
  and its weights moved on by Robust Skin Weights Transfer (MIT reference code, ported without libigl, whose
  bindings carry GPL-3.0). `skel_usd.py` turns a body into a UsdSkel asset;
  `cast.py` writes a place's characters layer (`<stage>/layers/characters.usda`, between the edit layer and the
  base) from its cast in `data/characters/<place>.json`: named people, kit groups mixed by seed, and a crowd as one
  PointInstancer. The review page draws them (`tools/review/characters.py`).
- `tools/blender/`: the headless Blender launcher (never a window on the owner's screen).
- `tools/sound/`: the sound picker and the loudness rule; MOSS takes are made in the cloud.
- `data/library/`: the surface library (materials, fittings, composites, details per kind, printed pictures);
  `data/fonts/`: the fonts printed labels use (SIL OFL).
- The first world's data, the game 2099's, read as the example world: `data/definitions/place.json` (each place's
  style, palette, materials, wear), `design/tokens/tokens.json` (the palette), `data/inventory/` (scene
  inventories), `data/kit/` (laid kit rooms), `data/sound/` (the sound catalogue, briefs, licences and loudness).
- `tools/assets/`: the world's heavy files (made models, sounds) as a release of this repository, named with their
  sha256, source and licence by `data/assets/world1.json`; `world.py` fetches, checks, packs and publishes them, and
  every record names a file by its name there or by its path in git. The framework reads nothing from the game's
  checkout (2026-10-09, the owner: the game and SCORE are fully separate); `game_free_test.py` holds it so. An
  engine's own import of the package (the game 2099's Godot scenes for a kit) is that engine's adapter, kept in the
  engine's repository.
- `vendor/`: third-party tools as released, each pinned with its licence (ADR-0002).
- `score/`: the layered framework's core, its skeleton built in step 0 of PRD #6 (2026-10-11) in Infinigen's run_stage
  shape; `tools/` moves in stage by stage as each stage is built. A stage table in code (`score/stages`); one runner
  (`score/graph`) that keys every node (a stage for one place, or for the world) on its computed code version,
  contract, parameters, a seed derived from the world's (`data/definitions/world.json`), pinned models and every
  input, and makes a node only when its key has no finish record; contracts (`score/contracts`): every output
  stamped with its schema and version in the house units (metres, seconds, degrees, Y up), nothing off its contract
  stored, and a reader blocked on an input of another schema or version; one store (`score/store`, over
  `tools/cloud/runtime/store.py`, a folder at `$PROPS_HOME/store`) keeping outputs by content hash, never
  overwritten; gates (`score/checks`) that answer pass, fail or unknown, unknown on missing evidence, and block on
  both; a review page per output (`score/review`). The framework decides, not a typed yes (the owner's answers of
  2026-10-11: his picks are made, from concept and style on everything runs automatically, no spend limit, spend
  logically). The runner accepts an output by itself when every gate passed and no score got worse than the accepted
  one, its accept marked as the runner's; it clears a paid run when every gate on its inputs passed (unknown blocks)
  and the ledger's month ceiling (`tools/props/cloud/ledger.py`) has room for its estimate, and keeps the clearance
  in the store. The owner keeps a reject, from the page's command in his terminal: the accepted output moves back to
  the one accepted before, every later node that read it is stale, and the runner never takes it again. He also
  keeps his own accept, for a worse output with his reason; a waiver (one check, one key, with his reason); and an
  override, his yes for a run outside the runner. None is needed for a run. Agents are kept from giving those, and
  from writing accepts or clearances by hand, by a barrier, not a lock: the commands want his terminal, the store
  refuses those writes in any process Claude Code started (the runner's automatic accept excepted), and
  `.claude/hooks/accept_guard.py` blocks the other routes; an agent set on getting round them can (by editing the
  framework's code, say), and every accept names who gave it and when. Adapters for models, compute and engines
  (`score/adapters`) refuse a paid run without the runner's clearance. A node runs only on outputs that passed (or
  whose failed checks he waived) and stand accepted. Step 0's worked example: `python -m score.stages run hangar
  hdoor` brings the round-three stages in as unverified seeds; the hangar fails on its code-built ship and the door answers unknown with no drop run, so
  neither completes. Every place that spends (`batch.rent`, the k8s submitter and the cluster's `up`, Nano Banana
  Pro's `pro.draw`, Marble's `generate` and `paint`) refuses unless SCORE_SPEND_TICKET names a node the runner
  cleared or the owner's override (`compute.require_cleared`), so the old paid entry points (blender_cloud.py,
  detached.py, the runners, demo.py, the close-up stage, marble.py) cannot spend round the runner. The job images
  are rebuilt the same way, as a world of their own (the `images` world, experimental below). Step 0 still
  lacks the layout stage's scene-record gates (every drawn mesh a plan shell piece or an inventory row, shell pieces
  bounded by the plan, a plain tag measured plain). Step 1, the surface stage (`score/stages/surfaces`, its
  overlay), is each place's own line of rows in world 1's table (`python -m score run world1 --place <place>`), no
  world-wide barrier: the method's rows (the finish-map method, owner 2026-10-12: Gemini's finish list of the
  close-up, Nano Banana Pro's finish maps of the close-up and of the raw model's sides and back, SegviGen guided by
  the close-up's map, the maps' votes laid on the raw model) end in its interface, each model's parts with the
  library surface named for each; the framework's rows paint every part from the library, bake and check it, and put
  a new library surface the method proposed in the finish registry (an append-only store item, `registry/` in the
  store) for the owner. Every model is repainted, the owner's picks included (a pick chooses the model, never its
  paint), each by one place only: a place reads a model another place claims from that place's bake. What each place
  paints and bakes is world data, `data/surfaces/<place>.json`. The in-progress directions are in
  `architecture/experimental`.
  The overlay `score/CLAUDE.md` has the rules.

**Everything from the library (invariant, owner's hard rule of 2026-10-18).** Everything a place shows comes from
score_lib, the creator's library: every finish, model, kit, effect, light, sound, character, ground and algorithm.
Every finish on every surface is a library surface (`data/library`: the ProcFunc recipes coloured from palette
tokens), on made props, picture-made models (their geometry is kept, their finish replaced), code-built objects,
ground and walls alike; never a picture's own texture, a model's baked-in colour, a default grey or anything else.
What is not from the library is a written exception in `data/checks/library-exceptions.json` (the place, the prim or
pattern, what it is, why, who allowed it and when, an optional expiry), read by the check, so an exception is wired,
never only written; one without a reason or an owner is refused. The library check (`score/stages/complete/library`,
its overlay) traces every bound material, referenced model or file, emitter, light, sound source and character of a
place's accepted assembly to a library entry, by content hash or by a recorded provenance attribute, and the
cockpit lists what does not trace as the place's problems.

**The library handover** (`score/stages/library`, its overlay): two free rows at the end of the stage table hand every
accepted output of a world to the creator's library, so what is in a world is in the library by construction.
`library@<place>` reads every place row of its line (the showcase renders, demo films and looks, only once they
stand) and `library-world` every world row; each runs the library's own handover command once (configured by
`SCORE_LIB_*` environment variables, else `$PROPS_HOME/library.env`; score never imports the library's code) and keeps
the report it writes, `handover.json` (contract `library-handover` v1). Its gate fails when no library is configured
(unless the owner named the world in `data/checks/library-free.json`), when an output read is not covered by an entry
or a written exception, when the library refused or did not commit, and answers unknown on a missing 3D copy or
quality score. A place is complete when its library node stands accepted, the world when every one does (`python -m
score status` prints that line); `complete@<place>` keeps its meaning and its key, so no paid row moves.

**The output** of a place is its scene package (`package.py`): `objects/<name>.gltf` per object as baked, and
`scene.json` (`score.scene` v1: metres, y up, each copy's transform, its inventory row, its model check). The game's
Godot adapter stays in 2099. OpenUSD as the canonical scene format is the next task.

## architecture/lifecycles

**One outdoor place, end to end** (the wreck is the worked example; commands in the README):

1. The place's record: its picked concept, its scene inventory (`data/inventory/<place>.json`, one row per object
   with its size and spots), each kind's turn and allowed materials in `data/library/details.json`, and one close-up
   per generated row. Recorded inputs live in the work folder (`PROPS_WORK`), not in git (the pictures are large).
   The close-ups come from the close-up stage (`tools/props/closeup/stage.py`): Qwen-Image-Edit-2511 draws every
   one in a cloud batch, a shape check (cheap measurements and an open vision-language judge, tuned to fail rather
   than pass a wrong shape) accepts or fails each, and Nano Banana Pro draws only the failures.
2. Pixal3D models from the close-ups, one cloud batch (`cloud/batch.py`, refused without the approved inventory).
3. PartCrafter parts from each model's cut-out (`cloud/parts.py`), the painting unit.
4. Labels: every part one allowed library material (`library/labels.py`), checked for patchy paint; a take too long
   for one piece is split (`place_route.py split`).
5. The plan and the bake jobs (`place_route.py plan`), baked in the cloud (`cloud/library_bake.py`, `--processor`
   when no card is in stock).
6. The model gate and straightness (`place_route.py check`).
7. The scene package and its check (`package.py`).
8. The stage (`tools/usd/export.py`, then the cast, motion, effects and sound layers), the completion gate's checks
   (`tools/usd/complete.py check`, the resting check after a drop run, `settle.py --dry-run`), the review page
   (`tools/review/page.py --cloud`) and the place's manifest (`complete.py done`).

**Which stages are current.** Every round of stages is a new folder of the work folder, never written over. No set
is canonical: a place's stage becomes canonical only when the owner accepts it on its review page, and none is
accepted yet. World 1's latest measured set is `WORK/usd-r3/<place>` with its review pages in `WORK/review-r3/<place>`
(the completion gate's rounds 1 and 2, 2026-10-10: round 2 exported again, into the same folders, only the places
whose inputs it changed; `usd-r3/inputs.json` names each place's commit and model folders). In it 3 of 18 places
pass the gate (flat, stairwell, habitat), 14 fail and the tube is unknown, measured with that day's placeholder
check, which passed the hangar's code-built ship, and with the reach check counted (it failed 8 places). The owner
has reviewed none of them: he reviewed the hub, the old station and the wreck on earlier rounds, and on 2026-10-11
the demo built from this set, finding the same painting faults and a placeholder. The earlier sets (`usd`,
`usd-complete`, `usd-r2-final`, `usd-rr`, the night's group sets) are kept beside it as they were. A later round
exports into a new folder and moves this line.

## architecture/experimental

The in-progress directions, in one place (PRD #6; the owner, 2026-10-11: nothing is taken out, each stays marked
experimental until its own phase of research, plan, integration into its stage and proof on its fault proves it).
Experimental means: the code and its overlay say so, and where it would run or cost money by default it is off until
a flag or a spec asks for it. Nothing here is a result; the paper's gaps name the same items. Each entry says what it
is meant to fix, where it is marked, and what proves it.

- **The people stage** (#5; `score/stages/people`, its overlay; `tools/characters/maker/prop_person.py`'s steps,
  specs `data/characters/makes/<name>_prop.json`, takes in `data/people/surfaces.json`). For bloated clothes on
  SOMA-made people: people made like every prop (owner, 2026-10-11), the clothing painted through the surface
  stage's own rows, SOMA-X only for the rig, Kimodo's clips swung clear of the body's own bulk (`clearance.py`).
  World rows run only when asked for by name (`--stage people-...`). Proven when the player and Nev pass every body
  gate (joins, tucks, cloth and body through cloth, rigid, outline, likeness, triangles) on every clip, the clothing
  passes the surface stage's paint gates on library surfaces, and the owner picks them on the review page.
- **The cast stage** (`score/stages/cast`, row `cast@<place>`, design 5 of 2026-10-12; its overlay). For places whose
  concept shows people but whose cast is unmeasured: each cast record dealt into its people, its groups and crowd
  stood on the seed's geometry, gated on `counted` (against `concept_people`, now in world 1's table), `standing`,
  `clear`, `made` and `drapes`. Nothing reads it yet. Proven when a place's cast passes all five with the people
  route's made looks and the owner has seen the characters layer written from it.
- **The drapes** (`drape_garment.py`, `newton_drape.py`, `cloth_drape.py`, `rebuild.py`; the drapes-fix,
  drapes-perlook and drapes-uipc branches stay off main). For the non-commercial Warp fork and drapes that slid or
  left arms bare. No default simulator: a person is made only when its spec names `drape_simulator`. The shipped
  Newton drapes are rejected by the owner (2026-10-10) and fail `drape_measure` (2 to 6 of 10 cuts; dense cuts 34 to
  50 of 64 to 69). Proven when a route passes drape_measure's dense check on all four looks, then the owner's eye.
- **The joins and stance checks** for people (hands under cuffs, boots in trousers). Numbers only so far. Proven by
  one before and after render pair per joint fault on the player and Nev, owner-checked.
- **The animal route** (`tools/characters/animals/`). For places with no animals. Runs only with `make.py
  --experimental`. Proven when an animal it made moves in a place's stage (#1: a fish swimming, a school as an
  instancer) and the owner has seen it.
- **The reach check** (`tools/usd/reach.py`). For rows a walker cannot reach. Run and shown on the manifest, not
  counted in the verdict (`complete.py`'s `EXPERIMENTAL`): it fails backdrop rows nobody walks to. Counted once the
  owner sets the scenery rule and it has caught a real unreachable row that was then fixed.
- **The painting after round four, the split spread and the surface check's dark rule** (`tools/props/library`: the
  two-way split fit, round five's 3D split, `--face-parts` and `finish_masks.py`, `split_spread.py`; 5c66c2e). For
  black, stripped and one-colour paint. No owner-accepted before and after on a world model. Settled in step 1, the
  surface stage, on the hangar and the six named models, with numbers and his review.
- **The surface stage's method, the finish map** (`score/stages/surfaces`, its overlay; the six-model re-test rows
  `score/stages/finishmap/trial.py`). The owner chose it on 2026-10-12 ("finish map seed 1 looks great"); it replaced
  g-texture (its record: branch `surface-first` and main before 6266414). Gemini lists the close-up's finishes as
  library surfaces, Nano Banana Pro draws the close-up's finish map and then maps of the raw model's sides and back
  against it, SegviGen is guided by the close-up's map, and every map votes on the faces its view sees. Re-test
  2026-10-12 on round 4's six models: every close-up map settled (the power unit's on its stricter third draw, 95%
  on a label colour), agreement with the maps 84 to 99% on the close-up and 89 to 100% on the back (the greenhouse chair's one side map 54%), no part mixing
  two finishes, 6 to 24 parts a model (the aft section had ~9,600). Each finish's surface is checked against its
  colour in the close-up (dE 32, set on the six: right surfaces up to 29.7, wrong from 33.2; a nearer surface of its
  family is taken, else the paint's gate fails it with a tinted proposal); a finish whose words name another
  material than its surface's family, or far off its colour, is named once more (`surfaces-names`). First real line,
  greenhouse 2026-10-12: every surface row passed through bake and check on all 8 models, with four library surfaces
  added overnight for the owner to review (grey_painted_steel, translucent_blue_plastic, printed_paper, tank_water).
  The owner walked it and found the water tank unpainted and crooked (2026-10-12): its cream paint, steel and water
  baked as three greys within dE 10 (tank_water on the deck's grey), and its uneven legs tipped it 7.5 degrees in the
  settle, which the checks passed. Since then the check fails a model whose surfaces bake to one grey look its
  close-up does not have (`bake_check.one_look_faults`; the tank and the crop crate) or whose lightness order it
  reverses (`order_faults`), the paint stretches a loose
  take's short legs onto one level plane before its bake and fails a missing leg by name (`feet.py`), the triage fails
  a foot off its support and an up axis leaning over 3 degrees, and the settle never writes a tip onto uneven feet;
  cream_paint is added for the owner to review, tank_water moved to tarp.
  The assembly takes the bake, each laid object carrying the baked file's hash (`score:model_sha256`) and the
  seed's as the model it repainted (`score:repaint_of`, which the pick lock reads). Proven when a place's line ends accepted at its checks and the owner
  reviews the baked models.
- **The scene-record stage** (`score/stages/scene_record`, its overlay; `data/plans/<place>.json`,
  `data/definitions/sky.json`). For the 18 scene records that are the game transcribed (every `from` a game line)
  and for doors that lead nowhere. `plan@<place>` brings the dimensioned plan into the store (`place-plan` v1),
  gated on `mapped` (every plan item names inventory rows, every concept element rows, a door or a drop, every door
  says where it leads and why); `scene-record@<place>` writes the record (`scene-record` v1, today's schema) from the
  plan, the inventory, the made ground's seats and the sky record, gated on `game-free`, `plan-matched`, `openings`
  (the record composed over the made ground: every doorway onto a floor, no view into nothing, every door's place
  standing in it) and `seed-matched` (the old record an unverified seed: each entry matched or left out with a
  written reason). Only places whose plan has `leads` have the rows; the assembly writes the accepted record over its
  seed's record prims (the final assembly, below). Two shell
  writers: domed rooms, and kit shells (`kit_shell.py`, 2026-10-12: the Earth's flat, stairwell, street, square and
  launch view, whose kits hold their walls; the record adds the block round a room, the lamps of the sky record's
  lamp rows where the kit lays them, the Earth's night, moon, glow and harbour, the plan's released models and the
  far city it shows; `plan-matched` holds the plan's doors to the kit's doorways), and outdoor places (`outdoor.py`,
  2026-10-12: the wreck, the old station, the camp grounds and the camp, whose kit holds its domes and whose
  furniture is the released camp models as plan objects; no walls of the record's; the body's outdoor sky in `sky.json` with
  its ways in the body's own frame, and the plan's lamps, decals and beams on their rows over the made ground). The
  wreck's supply rocket, cargo lift and landing dust are out, as its concept C2 shows none. A domed plan's `shape` adds the faceted hub and the walkway tube, a
  glass dome, the airlock's ramp and the greenhouse's plot (2026-10-12: the Moon base's airlock, workshop, lab,
  habitat, greenhouse, hub and tube; the lab and the habitat stand beside the hub in `data/definitions/base.json`).
  A domed plan's `shape: flat` is the hangar's flat roof (2026-10-12): four slabs on the walls' top round its door
  opening, its two roof leaves (the `hdoor` stage) shut over it; the hangar has its own seat on the Moon ground plan,
  north of the greenhouse, its tube joined to the greenhouse's north hatch, its yard held on its seat's flat plane
  (a level `on_seat`). An inventory row naming a world release model (`release_model`: the airlock's suit) stands as
  an object at its spots. The sky record's numbers are the
  old records' shared ones, unverified. Proven when the garage's record passes its gates and the owner has seen it
  built; then each domed room, and a shell writer for each other kind of place.
- **The final assembly** (`score/stages/assembly`: `make_from_seed`, `sounds.py`, the `layers` gate; 2026-10-12). For
  assemblies that copied the round-three seed's own record, sound and layers: each place is assembled once, from every
  layer stage's accepted output (`assembly.READS`: scene record, sound, effects, motion, light, machines, crops), each
  joining the assembly's reads the day its row joins the table (`stages.layered`), and the `layers` gate answers
  unknown while a layer the place needs (`data/checks/contents.json`; sound and light everywhere) has none, never
  letting the seed's stand in. The neighbours stage reads the record the assembly built from (`scene.json` beside the
  stage). Proven when every place's assembly passes `layers` and complete passes on it.
- **The made ground in each place's stage, and its look** (`score/stages/assembly` `take_ground`,
  `score/stages/terrain/look.py`, its overlay). For Earth's flat 320 m disc and the grounds the game laid: the
  terrain stage makes every ground from its plan; the assembly stage now sublayers the place's made ground over its
  seed, and `terrain-look@launch` and `@street` (paid, only the places in `look.LOOKED`) render the place before and after on its
  review cameras, gated on `horizon` (no view looks out under the horizon onto nothing). Run with `python -m score
  run world1 --place launch --stage terrain-look`. Proven when the owner has seen the launch's and the street's before and after;
  then the other Earth places, and the Moon's and Mars's plans (still the game's plans in `data/ground/plan/`, made by
  the game's builders moved here) drawn again from their concepts.
- **The settle stage** (`score/stages/settling`, its overlay; `tools/usd/settle.py`'s drop_job and rest_poses, the
  stage's held.py). For the resting faults no other track covered (2026-10-12): desks, shelves and chairs an old
  settle had left tipped onto uneven feet, a crate stacked on a crate that fell through it in the drop, monitors and
  boxes laid tipped or in the air on what holds them, and the triage's own false faults (a side wall's sparse points
  read as feet; a made ground read as y = 0, so the drop fell onto a plane there too). `settle@<place>` drops the
  seed's loose objects on the made ground once (each stood upright first, meeting what it is stacked on), snaps held
  ones onto their holders as they rest, lets floating fixed ones down, and lays where each rests as
  `layers/settle.usda`, which the assembly takes; gated on `rested` (the drop did not break) and `resting` (nothing
  rests worse with the layer than without). Only the places in `SETTLED` (`score/stages/__init__.py`) have the row.
  Proven when a place's assembly passes its own drop and triage with the layer, and the owner has seen its racks
  stand.
- **The effects stage and its look** (`score/stages/effects`, its overlay; `data/effects/launch.json`). For the 15 of
  18 places with no effects, the launch first: its lift-off had no flame, cloud, steam or light. `effects-layer@<place>`
  makes the place's effects layer from its record (emitters riding a prim, following a motion's climb, or played once;
  lights on a prim), gated on `attached` (read off the composed stage), `footage` (each measure of the baked particles
  within the range read off real footage, NASA's photographs of Falcon Heavy lift-offs, in rocket heights; elsewhere
  in metres at the place's own seconds), `light` (the flame lights the pad at least twice the place's lamps; a
  record that lights nothing says why, `no_light`) and `outside` (no open-sky particle inside the record's `interiors`);
  the assembly takes the layer in place of the seed's.
  `effects-look@launch` (paid) renders the review cameras before and after at four moments round lift-off, gated on
  `shown` and `lit`. `effects.STAGED` holds the launch, airlock, garage, hangar, greenhouse, habitat, flat, camp
  and campgrounds;
  `look.LOOKED` the launch only. Run
  with `python -m score run world1 --place launch --stage effects-look`. Proven when the owner has seen the launch's
  stills; then each place's record (pump-downs, steam, dust) from footage, and films on his go. 2026-10-12: all five
  gates pass on the launch (the `loose` footage check added after the first stills showed lone flakes: 10 % of the
  cloud's particles then, 0.2 % now). The same day the old local `effects` branch's records came over (pump-down
  fog and the door's vented ice and veil in the airlock, garage and hangar; the greenhouse's humidifier mist; the
  habitat's kettle and pot steam), each checked against photographs and reports of shuttle water dumps, a Soyuz
  leak, vacuum-chamber demonstrations, humidifiers, kettles and pots; the vent's speed, the pot's height, the
  kettle's gap and the mist's width put right to them. All three gates pass on each; the branch is deleted. No
  footage was found for a pump-down fog's size or fineness, a humidifier's exit speed, or any upper bound on a
  plume running off its photograph's frame. Later on 2026-10-12 (the owner: every place gets the effects its concept
  and machines imply) three places joined `STAGED`, each measured on footage: the flat's cigarette smoke (Commons photographs,
  breath papers: 3,000 and 4,000 fine cards where the game had 40 and 220), the camp's and its grounds' dust devils
  (Spirit's Gusev films, Greeley's counts: one see-through column about 10 m across, not the game's 1.2 m specks)
  over the game's drift, and the launch's liquid oxygen venting before ignition (a fuelled Falcon 9 at night: the
  steam at the rocket's base the concepts show; on 2026-10-14 the owner kept the launch's accepted smoke, f83dbfab22df,
  so its record went back to the content that made it, without the venting). A fourth gate, `outside`, keeps open-sky emitters out of a record's
  `interiors` (the camp's drift blew through its domes); `over_ground` measures over the planned ground, and
  reach and height are measured in the anchor emitter's own frame (a devil stands along the curved ground's up).
  Waiting on movers: wheel dust (the rovers stand), the hangar ship's exhaust (it never lifts), boot dust (nobody walks
  on regolith in any cast); none is staged until its motion exists, since a record that cannot pass would stop the
  place's assembly. The wreck's landing dust was measured on the Apollo landing papers and brought back, then taken
  out again: its concept shows no landing, and the concept decides (the captain, 2026-10-12; the veil is in e9e8cc8).
- **The motion stage** (`score/stages/motion`, its overlay; `tools/usd/movers.py`; `data/movers/`,
  `data/checks/motion.json`). For the things that stood still only because the game never moved them (2026-10-12:
  motion on 4 of 18 places). `motion@<place>` writes one motion layer over the place's seed from the game's timed
  motions (`data/motion`, unchanged) and its movers record: each mover a closed path (a ferry's harbour lane), a
  swing on a hinge (a hatch), a spin (a fan) or a slide on a rail (a boom, a crane trolley), its kind's speed range
  cited in `data/checks/motion.json`, and every prim of a moving kind that stays still says why (`still`). Gated on
  `clear` (no mover reaches into a still thing or another mover over the layer, read off the composed stage),
  `speeds`, `loops` (rounds join and fit the layer's seconds whole), `grounded` (on water or ground, on its rail, or
  in the air) and `covered`. The assembly does not take the layer yet; the final assembly of each place does. Proven
  when the owner has seen the launch's ferries and the greenhouse's booms and hatches move.
- **The light stage** (`score/stages/light`, its overlay; 2026-10-12). For lamps at the game's numbers, the cartoon
  Earth, the flat Mars sky with no sun, the camp's night windows in the record's afternoon and the floodlight heads
  read as white grids (paper-vs-world-1 items 9 and 17). `light-layer@<place>` (free) writes `layers/light.usda` over
  the round-three seed from today's scene record with `tools/usd/scene.py`'s own writers (lamps where the record puts
  them, the Earth with NASA's surface, the day dome and the sun's disc, the shafts); `light-passes@<place>` (paid,
  about EUR 2) renders it once on the demo's views with every lamp in a Cycles light group of its own;
  `light@<place>` (free) mixes the passes at any strengths with no render again, takes the scale that brings the
  place's brightness to its concept's, turns a blown-out lamp down, writes the strengths into the layer and judges
  brightness, lamps (unlit, blown), sky elements, floodlight heads, the Earth, the Mars sky and stage_no_worse. The
  layer holds live lights (the owner, 2026-10-12: no baked per-lamp layers this month); the passes are that idea on
  the views only. The strengths are measured on the round-three seeds' layouts with the layer, not on the final
  assembly, which does not take the layer yet; the measurement moves there once it does. The light stage's own
  additions live in `data/light/<place>.json` (the launch: concept K01's two pad floodlights on the far side with
  their lamps and the night glow). Measured cost: one L4 render a place, EUR 0.10 to 0.26. Proven when a place's line
  ends accepted on its gates and the owner has seen its looks.
- **The neighbours stage** (`score/stages/assembly/neighbours.py`). A place's views looked out onto empty space: the
  seeds' references to the places they show (`../../launch/launch.usda`) resolve to nothing once each place is its own
  node, so the launch's accepted assembly showed the square and the far city with no children. `neighbours@<place>`
  copies the place's accepted assembly and each neighbour's (read beside, `Stage.beside`: versioned and waited on like
  `after`; a neighbour is its assembly alone, so places that show each other make no cycle) and points the references
  there; the far city, which no stage makes yet, comes from its seed folder. Gated on `neighbours` (every shown place
  of the scene record stands, resolves and has children); `complete` reads it (2026-10-12: a place whose shown places
  do not stand is not complete, so the hub's failing assembly stops every place that shows the hub). Proven when the
  square's and the
  flat's views show the launch with its effects.
- **The physics stage** (F11, the paper's "responsive"; `score/stages/physics`, `tools/usd/physics.py`). The stage
  carried a convex hull per object and no mass or material, so nothing in it could react. `physics-layer@<place>`
  (free) writes the place's physics in OpenUSD's own schema (UsdPhysics: collision by each mesh's triangles, mass from
  each model's surface area, a sheet thickness and its material's density, friction and restitution per material in
  `data/physics/materials.json`, the pull of the place's body) and a trial from `data/physics/<place>.json` (drops,
  a hinge with limits and a motor, kinematic pushes), gated on `laid`; `physics-trial@<place>` (paid) runs the trial
  on Blender's Bullet from that schema on a rented machine, writes its motion back as time samples, renders the
  record's views at its moments, and gates on `reacted`, `at rest`, `hinge` and `energy`. Only the habitat has a
  record. Proven when its trial passes the four gates on the habitat's accepted assembly and the owner has seen the
  strip; until then the paper states responsiveness as this trial, not as a property of every place. Mass by sheet
  thickness and one material for models without labelled parts are assumptions, said so in the data.
- **The sound stage** (`score/stages/sound`, its overlay). For a sound layer no one had reviewed, carried from the
  game's table, with the camp silent, the launch with no loop, the square with no PA or speech, and no car, rover or
  ship heard. `sound@<place>` answers every source the place names (room tones, the suit, objects, inventory rows,
  motions, the surface bank) with a sound: the world's picked file, or MOSS takes of its brief made in the moss image on
  one rented card (paid), chosen by the picker's rule; gated on `sources`, `level` (loudness and length, measured),
  `likeness` (CLAP to its prompt at least 0.30, the tenth percentile of the world's MOSS picks) and `no freesound`
  (the owner's 2026-10-06 recordings excepted, listed). The layer is data (`sound.json` and its files); the assembly
  does not read it yet. Proven when every place passes and the owner has heard the new sounds.
- **The render-and-compare** (`tools/usd/compare.py`). A candidate check: no gate reads it. Proven when it ranks a
  model from the fault corpus worst.
- **The style measure** (`tools/review/style.py`). For style coherence. Proven when it ranks the models the owner
  flagged worse than those he accepted.
- **The films' past-fade ink rule** (0e68b5e, `film_checks.py --ink-past-fade`). For far views the game draws
  without lines. Off by default, so a frame with no line at half strength fails. Proven by the owner's look at such
  a shot.
- **The demo films** (`WORK/demo/world1-r3`, `world1-r4`) and their technical checks. Cited nowhere; nobody reviewed
  them. They come back as the evidence step, on places the owner accepted.
- **The Kubernetes path and 06cf411's image pins** (`tools/cloud/`). For setup time and stock. Opt-in
  (SCORE_CLOUD=k8s), not used for world 1. Proven when a stage's paid node runs through it end to end.
- **The images world** (`score/stages/images`, its overlay; `python -m score run images`, `python -m score images
  publish <kind>`). For maintenance image builds that needed the owner's override: each image kind with a proof plan
  (`tools/cloud/images/<kind>/prove.json`) is a world of its own stage table, no places, no world 1 node reads it. A
  free `image-pins-<kind>` (pins exact and hashed, resolved by uv, `build_test.py`, models, licences and Dockerfile
  instructions as the published build's) gates a paid `image-proof-<kind>` cleared against the month's ceiling
  (build.py, then prove.py on real jobs, the kind's own output check), and publish writes the accepted record into
  images.json. Proved so far (2026-10-12): moss and characters-motion built, proved and published through it (two
  real MOSS takes at the build before's CLAP scores; a 5 s Kimodo walking clip), closing 30 Dependabot alerts (64 open to 34) with
  no world 1 key moved. Proven fully when parts, sam and pixal run through it too, after the world 1 run, and the
  pins gate checks each pin's hashes against the index the build installs from (a triton hash from the wrong index
  passed it and failed a paid build).
- **Unreviewed world data**: the far city's towers and lit windows (3 of 5 kinds made, no owner pick), the street
  blocks (about 81 models only in a local package, not in the release), the rows made fixed so the drop leaves them
  (square lamp posts, street lamps and notice board, launch masts and floodlights: a count fell, nothing moved), the
  settled rest poses written back into the kit and scene records, the wreck re-laid after its review (e5d829c), and
  the coordinator's removal of the supply rocket, the cargo lift and the wreck's landing dust (dc6c284; the pad's
  removal was the owner's ask). Each enters the new stages as an unverified seed and waits for the owner's look, or
  his yes or no on the removals.
- **The motion, sound and effects layers.** Built, not reviewed: nobody has heard the sound. Proven by the owner's
  review of one place per layer, render and audio.
- **The machines stage** (`score/stages/machines`, its overlay; `data/machines/<place>.json`). For the machines that
  were absent or stood in: no rover in the garage, a code cylinder for the hangar's ship, primitive shapes for the
  workshop's robot. `machines-layer@<place>` (free) lays each machine's made model (the prop route's take, painted and
  baked by the place's surface line) on what holds it up, as a layer the assembly takes, gated on `outline` (the
  likeness gate's free half against its close-up), `parts present` (its close-up's finishes in its split) and
  `resting` (resting.py on the composed stage). Its motion and effects are the motion and effects stages'. Only the
  garage's rover has a record. Proven when the garage's rover ends accepted and the owner sees it; the ship and the
  ship is the hangar's `ship` inventory row, grounded by `machines-boxes@hangar` (paid, SAM 3) and made by the prop
  route on the hangar's own surface line (its take `ship-s1` in `data/surfaces/hangar.json`); the workshop has no robot row: its concept K10 shows none, and
  the concept decides (captain, 2026-10-12).
- **The crops stage** (`score/stages/crops`, its overlay; `data/crops/greenhouse*.json`). For the greenhouse's bare
  beds under a concept of planted ones. `crops-concept@greenhouse` (paid) measures each kind on the concept with SAM 3
  on 2x tiles: its patches' share of the plot and its spacing in plant widths (2026-10-12: lettuce 49 plants 1.06
  widths apart, potato 65 at 1.57, herb 28 at 1.27, the parsley and kale one canopy, `greens`; seedlings dropped with
  the reason in the data). The crop kinds are inventory rows made by the prop route and painted by the surface stage
  on a line of their own (`crops-boxes`, `crops-props-inputs` ... `crops-surfaces-check`), so the greenhouse's own line
  and its reviewed models do not move; `crops-layer` (free) lays each baked kind on its beds at the measured spacing,
  one point instancer a kind, gated on `on beds` and `spacing`, and the assembly takes it; `crops-look` (paid) renders
  the beds at the concept's slant and counts them with SAM 3 again (`seen`, `density`). Proven when the look's gates
  pass and the owner has seen it; the crop state (mid-season beds, not the game's bare start) is his open decision.

## architecture/trust-boundaries

<Where untrusted input crosses into trusted code, how it is authenticated, where secrets live and
who can read them. Placeholder.>

## architecture/failure

<What breaks when each piece breaks, what the blast radius is, and how to recover. Placeholder.>

## build/release

Nothing is released yet but the paper. Commands, run locally (there is no CI and no GitHub Actions):

- `make paper`: builds the paper from `paper/source/score.md` with pandoc into `paper/out/score.tex`
  and `score.pdf` (citeproc, IEEE style) and into the arXiv tree `paper/arxiv/` (`main.tex`,
  `content/`, `figures/`, `refs.bib`, `main.bbl`, `main.pdf`). PDF engine: xelatex if installed,
  else tectonic. The build writes `paper/out/stamp.json`, the sha256 of every input (draft,
  bibliography, style, filter, figures, the build script) and every output.
- `make check`: the gate. `gate-scope.py` decides whether tests run (`paper/` counts as a build
  input, not a document); the tests include `paper/build/test_paper_current.py`, which fails when
  the files on disk no longer match the stamp, so a draft changed without a rebuild, or a
  generated file edited by hand, is red. Then the ADR index check.
- `make env` builds the framework's Python environment (`.venv`, `uv sync`); `make tests` runs every framework
  check (`tools/**/*_test.py` and `score/**/*_test.py`, plain scripts, or under pytest when a file has `test_`
  functions and no `__main__` block, each under a 16 GB memory cap), or only the
  ones named with `TESTS="..."`. Each runs in a sandbox home (`.claude/scripts/sandbox-home.py`: a fresh
  `PROPS_HOME` in the temp folder linking the real home's world data, with the real home mounted read-only by
  bubblewrap; its cloud ledger, store, locks and logs never linked), and the root `conftest.py` refuses a pytest run
  whose `PROPS_HOME` is not such a folder (a test unlinked the real cloud ledger, 2026-10-17). `make check` runs them when code changed. While working, run only the checks your change touches.
  Render checks run Blender headless on a cloud machine, never here; nothing here runs Godot.
- `.githooks/pre-commit` (installed by `bootstrap.sh` as `core.hooksPath`) runs the same check on
  any commit that touches `paper/`. A green run means the committed PDF is the draft's.

**Scope the gate.** Running every test on every push stops scaling once several sessions work
side by side on one machine. The project's test command asks
`python3 .claude/scripts/gate-scope.py` first and reads its `MODE` line: `none` when the change
touches only documents and working notes (`.md`, `docs/`, `.claude/`), so nothing runs; `full`
otherwise. When the full run grows slow, grow the script into a graph that picks only the suites
a change can reach, and keep its rules:

- **Unknown means full.** A path the scope does not recognise, a file that went away and could
  have been named by something, no origin/main to compare with, `--full`, `GATE_FULL=1`, or a run
  on CI: everything runs. A new kind of path goes to full, never to "none".
- **A change to the gate itself runs everything**: the test runner, its config, vendored test
  frameworks, the CI workflow.
- **CI always runs everything.** It is the net under a test the scope misses, so it stays
  unscoped.
- **The scope has its own check against the real tree**: every suite is chosen when the file it
  is named after changes, and an exception is written down with the reason.
- **Print the reasons**, one line each, so whoever reads the gate's output sees what was skipped.

A grown version to copy from: the game 2099's `tools/test/scope/` (Godot scripts, scenes and
its resource paths).

## workflow/loop

The working loop, and the mechanisms that keep it from drifting.

**The loop.** Every conversation in this repo is a task, and it runs the same four steps.

1. **grill** — the first message in any conversation goes here, enforced by the `SessionStart`
   hook. Grill orients silently (the prompt, `.claude/soul.md`, root `CLAUDE.md`, the `CONTEXT.md`
   glossary, the bible chapters the prompt touches, the related GitHub issues), then interviews the
   plan one question at a time until the plan and the domain model agree. Facts get looked up, not
   asked. Decisions get asked, not assumed.
2. **to-prd** — the aligned plan becomes one PRD epic: a GitHub issue with a goal, a scope, a task
   list and a verifiable definition of done. No re-interviewing. A task that is independently
   grabbable, or that is going to an agent, is carved out as a natively linked sub-issue; everything
   else stays a checklist line.
3. **code** — the work itself, against the PRD.
4. **close** — ship what is done, write where the PRD stands, park every loose end under a parent
   PRD, and close the issue only when its acceptance list is genuinely met.

Two branches off step 1. A **brain dump** (several open questions at once, visionary thinking, a
pasted conversation) goes to `brain-dump`, which sorts it into claims, questions, decisions and
vision, sweeps and refutes, and lands each result in its own home. An effort that is **too big and
too fogged** for one session goes to `wayfinder`, which charts it as a PRD whose route is unknown
and breaks the fog into investigation sub-issues, one resolved per session.

**The mechanism stack.** Four types, one job each. Mixing them makes harness behaviour
unpredictable.

- **Skills** (`.claude/skills/<name>/SKILL.md`) hold methodology. Invoked by name (`/grill`) or by
  the model when the description matches.
- **Overlays** (`<area>/CLAUDE.md`) hold the rules for one directory and auto-load when a file in
  it is touched. A new code directory gets one without asking; it is the mechanism, not a document.
- **Hooks** (`.claude/settings.json`) hold automation that must fire on a harness event, not on the
  model remembering. Today: the grill protocol on `SessionStart`, the soul rules on every prompt,
  `md_guard`, `issue_guard` and `accept_guard` (only the owner rejects, accepts by hand, waives or overrides; the runner accepts and clears by
  the gates) on
  `PreToolUse`, and the memory commit-and-push on `Stop`.
- **GitHub issues** hold the durable backlog. Anything that must survive the chat lives there.

**Session roles.** One coordinating session, the overseer, runs the work directly with many
parallel agents; the owner reviews and buys changes in the creator cockpit (score.babon.eu). The
captain, a second session that ran one effort under the overseer, was retired on 2026-10-18 (owner:
it did not work); records that cite "the captain" name decisions taken in that role, and they
stand. Terms in `CONTEXT.md`.

- **Overseer.** The one coordinating session. Plans each effort as stages from the paper; proves
  each stage on one place before fanning out; splits the work across parallel agents, briefs each
  one, checks what it returns against the brief and merges it. Starts in this repository, so its
  hooks, tools and memory reach every agent. Guards drift: holds the paper, the owner's vision, the
  distilled owner prompts and every standing rule, and checks every result against them; corrects
  briefly and cites the rule or paper section, never steers by taste. Lets measured checks decide,
  never its own look; keeps code that paid steps hash frozen during a fan-out; never ships half-done
  work to main, pages, the paper or films. Spends nothing without the owner, and approves nothing
  on an agent's word (only the owner rejects, accepts by hand, waives or overrides). Reports to the
  owner in plain words: what changed in the result, what drifted, what it did. Keeps the full
  handover current, so a new overseer starts knowing everything.
- **Agent.** One job, one written brief, its own worktree. Tests what it touched, pushes when its
  checks pass, reports what changed in the result with a before and after, and stops. Waits in the
  background, never in a sleep loop. Takes on no scope beyond its brief.
- **Sub-agent.** One narrow step for its parent agent. Returns data, not prose; reads only what the
  step needs; never pushes to main on its own, reports to the owner or widens its step.

**One agent, one job.** Work is split across parallel agents by default: each independent job gets
its own agent with its own brief, and jobs run side by side unless one needs another's result.

**Hard rule: a clear role, then a handoff and a close** (owner, 2026-10-18). Every agent starts with one clear role in its brief. When the role is done, or the work would change role, the agent commits what is useful, writes a handoff (its role, what is done with commits, what is half done and where, known faults, exact next steps, file paths) and closes. New work always goes to a fresh agent with its own role brief; an agent is never handed a second job mid-run. The coordinating session closes the same way at the end of its run. Coordinating sessions start inside this repository, so every agent gets its hooks, its code map and its skills; a session started elsewhere runs without them.

**Sub-agents.** Independent steps go to sub-agents, and a sub-agent may split its own work over
sub-agents again (owner, 2026-10-09; heavy work runs in the cloud, so the old local-load cap is
gone). The parent writes each brief (task, scope, the rules that apply, where the result goes),
checks what comes back against the brief, and merges it; a sub-agent's word is never taken as
done. Each agent is short and scoped: one job, a clean context, and it ends when the job ends.
Waits run in the background, never as an idle agent. The overseer watches every agent's age
and tokens and restarts, splits or stops a stale one without being asked (an agent alive for hours
or at hundreds of thousands of tokens on a small job is stale). Checked 2026-10-10: a session's
sub-agent spawned its own sub-agent and got its answer back; a sub-agent started by a workflow
script is not given the Agent tool and cannot nest.

**The board.** One GitHub project, created by `.claude/scripts/setup-github.py --board`. Status is
a board column, never a label: `LowPriority`, `Not started`, `In Progress`, `Review`, `Done`. Set it
with `python3 .claude/scripts/board-status.py <issue> "In Progress"`. Triage state is a label
(`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) and is a different
axis from the column; do not confuse them.

**Before you push.** Run the project's own test command (scoped by
`.claude/scripts/gate-scope.py`, see build/release), and
`python3 docs/adr/tools/check_index.py`. Both must exit clean. The push is the ship: this repo
works on `main` only (ADR-0001), so a push is visible to everyone immediately and there is no PR
step to catch anything you skipped.

**Commits.** Imperative and scoped: `module: description`. The scope is the module or area, not the
file. A commit that needs "and" in its subject line is two commits.

**Memory.** Claude's memory folder is linked into `.claude/memory` by
`.claude/scripts/bootstrap.sh`, and that folder is git-ignored: this repository is public, and
memory is private working notes. The `Stop` hook's memory commit finds nothing to commit. Memory
therefore does not survive a wiped machine; anything load-bearing goes into the bible, the
glossary or an issue instead.

## workflow/module-standard

The house standard for a module in this repo. It exists so that a reader can predict the shape of
code they have not seen yet.

- **One interface, one directory.** A module is a directory with an obvious way in. Callers import
  the way in, never a file inside it. Files that are not part of the interface are private
  (`_prefix` in Python, not exported in TypeScript, package-private in Java).
- **Deep over shallow.** A module earns its existence by hiding more than it exposes. If its
  interface is nearly as complicated as its implementation, it is a shallow module and belongs
  inlined into its caller. Vocabulary and the full argument:
  [`.claude/skills/improve-codebase-architecture/LANGUAGE.md`](../.claude/skills/improve-codebase-architecture/LANGUAGE.md).
- **One function, one purpose.** If the docstring needs "and" between two concerns, it is two
  functions.
- **Tests sit with the module** they test, named for the invariant rather than the function
  (`test_<invariant>`), and drive the module through its public interface. A test that reaches into
  the implementation freezes the implementation.
- **Failures propagate.** A write that can fail raises; it does not log and continue. The two tiers
  are: a failure the caller can do something about (raise a typed error) and a failure nothing can
  be done about (crash loudly). Swallowing is neither.
- **Every directory carries its overlay** (`CLAUDE.md`) once it has rules of its own.

<Extend this chapter with the specifics this project needs: the layer names, the test command, the
directory layout. The rules above hold whatever the language is.>

## workflow/bootstrap

Getting a fresh machine, or a wiped one, back to working.

1. Clone the repo, and install the GitHub CLI so `gh auth status` is green. The skills that touch
   issues and the board go through `gh`; without it, `to-prd`, `triage`, `close` and `my-issues`
   cannot run.
2. `bash .claude/scripts/bootstrap.sh`. It links `~/.claude/projects/<encoded-repo-path>/memory` to
   the repo's git-ignored `.claude/memory` (private, never pushed), runs
   `.claude/scripts/install-agent-tools.sh` (the agent tools in root `CLAUDE.md`: the pinned
   codebase-memory-mcp binary and Bun, each checked against its SHA-256; claude-mem's settings in
   `~/.claude-mem`; the vendored claude-mem plugin installed for this project; the repo indexed into
   `~/.cache/codebase-memory-mcp`), builds the framework's Python from `uv.lock` (`.venv`, and
   `PROPS_HOME`'s `env/` when missing, below), and reports anything else that is missing. It needs `node`,
   `python3`, `curl`, `uv` and the `claude` CLI. It is safe to re-run; every step skips what is already done.
3. `python3 .claude/scripts/setup-github.py --board` on a fresh repo only. Labels and the board are
   GitHub-side state and are not copied by "Use this template", so a repo spawned from the template
   starts without them.

**The framework's runtime** lives outside the repo, under `PROPS_HOME` (default `~/.farm-factory-props`, the first
world's name, kept so the cloud ledger, keys and work carry over): `cloud/` (the runner's ssh key, the self-delete
key, the spend ledger), `work/` (`PROPS_WORK`: takes, pictures, places' runs), `env/` (the interpreter the cloud
machine runner, `blender_cloud.py`'s `CLOUD_PYTHON`, and the animal route call; `bootstrap.sh` builds it from
`uv.lock` without dev tools when it is missing; no model runs in it). The machines need `uv`, `make env`,
and the cloud backend's tools: for Scaleway, the current backend, the `scw` CLI logged in to the project named by
`SCORE_SCALEWAY_PROJECT` (by name, never an id).

**The character maker** (`tools/characters/maker/`) needs nothing installed here: every environment it runs is set up
on the rented card by `tools/props/cloud/characters_setup.sh` (about half an hour). It reads the secret
`hf-read-token` (a HuggingFace read token whose account accepted Meta's terms for `meta-llama/Meta-Llama-3-8B-Instruct`,
the base of Kimodo's text encoder), and from `MOTION_HOME` (default `~/.farm-factory-motion`) what every person shares:
the two boots (`look/work_boot.npz`, `look/space_boot.npz`), MakeHuman's CC0 base mesh and low-poly eyes, and the clips
already made (`work/motions/`); `make.py` names each (`SHARED`). A fresh box without them makes the clips again from
their sentences; the boots and the eyes' source files must be copied over.

**What survives a wipe:** everything in git. **What does not:** Claude's memory (git-ignored,
because the repository is public), `gh` auth, any local toolchain, and anything a session left
uncommitted.

## Identifiers

<The names and numbers a session needs and cannot derive: repository, board number, hosts, service
IDs, secret names. Keep it a table. Anything secret goes in a secret store, and only its name goes
here.>

| What | Value |
|---|---|
| Repository | `Babon-Innovations-b-v/score` |
| Project board | `9` (org project) |
| First user | the game 2099, `JoeyKardolus/2099` (paused 2026-10-08) |
| Cloud | backend chosen by `SCORE_CLOUD` (default `scaleway`); Scaleway: the project named by `SCORE_SCALEWAY_PROJECT` (default `farm-factory`), machines tagged `farm-factory-batch`; month ceiling `SCORE_MONTH_EUROS` (default 1500) |
| Secrets | read by name with `secret_store.secret(name)`: the environment variable `SCORE_SECRET_<NAME>`, else the backend's store (Scaleway Secret Manager in that project): `worldlabs-api-key`, `gemini-api-key`, `freesound-api-key` (optional) |
