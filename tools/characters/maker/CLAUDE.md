# tools/characters/maker/

The character maker: one entry point (`make.py`) for a person or an animal, from a picture or a short description to a
rigged, clothed, textured, animated character as glTF and UsdSkel, with its far level for crowds and its clips. Specs
are `data/characters/makes/<name>.json` (`spec.py` says what they hold); what a make produces lives outside the repo in
`~/.farm-factory-motion/made/<name>/`. People go through the person chain here; animals through `../animals/`.

- **Experimental, refused unless asked for** (docs/bible.md, `architecture/experimental`): the prop route and the
  animal route run only with `make.py --experimental`, and refuse when started round it (`prop_person.py` wants
  `--experimental` too, `route.make` its `experimental=True`); the drapes have no default simulator, so a person is made
  only when its spec names `drape_simulator` (`drape_garment.py --simulator` and `rebuild.py bundle --simulator` are
  required). The owner rejected the Newton drapes (2026-10-10) and `drape_measure.py` fails them; the joins and
  stance checks (`rebuild.py`'s old-beside-new renders, the wrist and boot numbers) have no owner-checked before and
  after yet. Proven: a drape route passing drape_measure's dense check on all four looks and the owner's eye; the
  prop route when the player and Nev pass tucks, pokes and skin-through-cloth on every clip and he picks them.
- **Nothing here runs a model on the owner's PC.** `make.py` bundles a spec's files and hands people to
  `tools/props/cloud/characters.py`, which rents one card a person and runs `chain.py` up there; every other file in
  this folder is a step `chain.py` runs on that machine, each in its own environment (`characters_setup.sh` says
  which). A step is tried on a held machine (`characters.py --hold`), never here.
- **A make must be asked for.** A spec without `approved` (who asked, when) is refused before anything is rented.
- **The steps are the hand-made looks' steps, automated** (#100, #112, moved from the nev_mars job's scripts): the
  A-pose picture, the body read off it (SAM3DBody-cpp), the body at rest, the clips (Kimodo), the drapes (GarmentCode's
  pattern, Blender's cloth: GarmentCode's Warp fork is non-commercial and is never used), the head and eyes, the hair
  (klein clay picture, Hi3DGen, the shell fit), the face (klein base with the refcontrol depth LoRA), and the build
  (`../people/body.py`, `../skel_usd.py`). Where a person picked by eye (a seed, a hair option) the chain takes the
  first seed and keeps every take in `out/steps/` for the review page; the spec's `hair_options` and `face_options`
  carry what a person needed by hand.
- **Every step is timed.** `out/make.json` records each step's minutes and the card it ran on; those are the paper's
  numbers, never typed in by hand.
- **Look at the result.** As in `../people/`: the numbers say something changed, only a render says it is right.
- Licences of every piece are in the paper's models table and in `docs/bible.md`; a new model goes there before it is
  used.
- **Drapes** (`drape_garment.py`, run by `chain.py` and `rebuild.py`): `garment.py` (GarmentCode's environment)
  sizes a design of `data/characters/garments/` to the body and makes its pattern and box mesh (`--pattern` with
  `--measurements` drapes a kept look's own sized pattern 1:1 instead). `newton_drape.py` (experimental, as every drape route is; Newton's
  SolverVBD on upstream NVIDIA Warp, both Apache-2.0, the newton environment on a card) drapes it as GarmentCode's own
  run did, written anew: the box mesh welded, each triangle and edge resting at its flat panel's shape, so the seams
  sew themselves; no gravity for 10 frames, light gravity (the design's `gravity`, 2 m/s^2) while the waist and
  collars are held, then the earth's 9.81 m/s^2 for the final settle until the cloth is still (the space suit's waist
  stays held, as its belt holds it). Its record is the drape's `newton_cloth.json`. Judge a drape change by
  `drape_measure.py --reference <Warp drape>` and its `verdict`, never by looking: the silhouette (width and stand-off
  against the Warp drape at the named cuts and at dense ones, the torso every centimetre, the shoulder with the
  sleeves' caps from the armpit up, the arms every 5 %, tolerances from the Warp drapes' own left-right spread) and
  the belt band; only pass lets a drape through, unknown blocks. The shipped Newton drapes the owner called bloated
  (2026-10-10) fail it; the Warp drapes pass against themselves, the work suits only as far as the silhouette: their
  torso ends above the belt band, so their belt reads unknown. Never copy or port code from
  GarmentCode's Warp fork (non-commercial); GarmentCode itself (MIT) may be read. Measured with `drape_measure.py`
  against the Warp drapes on Nev, Ama and the player (2026-10-09): crumples within 0.6 degrees on the work suit and
  1 degree on the space suit (Blender's were 4 to 6 times Warp's), the work suit's trousers 1 to 2 cm longer because
  the settle is at full gravity where Warp's ran at a hundredth of it. `cloth_drape.py` (Blender's cloth,
  `--simulator blender`) stays as a second route; its tries are in `blender_cloth.json`.
- **Rebuilding kept looks** (`rebuild.py`): the looks kept before 2026-10-09 carry drapes from GarmentCode's Warp fork;
  `rebuild.py bundle` makes a make folder for each group of people sharing drapes, `characters.py` runs it up there
  (each drape again from its own kept pattern on the look's rest body, the people built, old and new rendered with the
  same cameras), and `rebuild.py land` copies it into `~/.farm-factory-motion/rebuild/`. It never writes the kept
  looks or bodies; whoever judges the pictures swaps them.
- **The prop route** (`prop_person.py`, a spec's `"route": "prop"`; experimental, a trial, #5, owner 2026-10-10: "soma is for the
  rig, not the mesh"): Pixal3D's mesh from a klein close-up drawn in SOMA-X's bind pose (`batch.py --characters`, as
  the animals'), stood level (head over the feet), thinned part by part to the shipped outfit's triangles (borders
  kept, so the parts stay shut), SOMA-X's skeleton placed inside it from the mesh's limbs at the mean bone lengths
  times the look's scale (an arm the slices barely find is laid from its shoulder to its hand part; `prop_rig.py`; its
  weights moved on by RSWT, the SOMA surface only their hidden source), GeoSAM2 parts and the close-up's SAM 2.1
  finish regions named by the judge in one run (three seeds; an unnamed part takes its mirror image's answers; a
  region's answer far from its own colour is not believed), tucks under the joins (`tucks.py`), built by
  `prop_build.py` (every hard thing, the hair and the bare hands on one joint, the cloth next to it eased onto that joint; the face cut from the
  close-up and the flag drawn are the only pictures, `prop_prints.py`; piping cut in as thin strips down the outside
  of the sleeves and trouser legs, `piping.py`), the garments settled through every clip by Newton against the
  person's own posed surface with the cloth over each tuck held on its skinned place (`garment_settle.py`) and baked
  on the card as corrective shapes each clip keys, as many as keep every point within 4 mm of the settle, a frame's
  shapes eased off where they would put the cloth through the body more than unsettled (`garment_bake.py`; glTF morph
  targets, which `joins.py` and `pokes.py` read, and UsdSkel blend shapes), and checked by `joins.py`, `pokes.py`
  (tucks, cloth through cloth against the shipped body's record, hard parts' stretch), `outline.py` and the
  reviewer's skin-through-cloth count; `blender_shots.py` renders it beside today's body. No SAM3DBody-cpp and no SOMA
  surface: nothing but Pixal3D's mesh is drawn or shapes it. Takes land only in
  `~/.farm-factory-motion/candidates/prop-people/`; every other person keeps the shipped route. Its numbers are
  `checks.txt` beside each take. A held machine keeps each make under its folder's name, so make folders carry the
  person and outfit (`make_place`). A close-up whose arms touch the body is refused before Pixal3D (`arm_gap_share`);
  klein copies a reference's pose over the words, so a spec may give a `pose_picture` to take the pose from.
- **The people route** (`route_*.py`, owner's pick of 2026-10-18, #10; experimental, a free prototype on the PC, not
  wired into any row yet): the accepted made body rebuilt on the SOMA-X base laid under its look (`route_base.py`,
  with SOMA-X's pose correctives per clip), each garment region weighted from its own limb only and the arm and leg
  webs cut and closed (`route_bind.py`), the base drawn in the suit's cloth under the cut webs so the gap where an
  arm lifts off the side shows cloth (`route_build.py under_layer`), the made hair on the old SOMA-X head with its
  drawn face (`route_head.py`), no settle shapes, the correctives as shared morph targets (`route_build.py`).
  Measured by `route_stretch.py` (longest triangle edge growth per clip) and `pokes.py`; pictured by
  `blender_route_shots.py` with the same cameras before and after. Plain CPU: SOMA-X's body model and its small
  correctives network on 4 threads in the motion environment (`route_base.py`), the rest numpy; no card.
  Proven: the player and Nev pass tucks and pokes on every clip and the owner picks the side-by-side.
