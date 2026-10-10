# tools/characters/maker/

The character maker: one entry point (`make.py`) for a person or an animal, from a picture or a short description to a
rigged, clothed, textured, animated character as glTF and UsdSkel, with its far level for crowds and its clips. Specs
are `data/characters/makes/<name>.json` (`spec.py` says what they hold); what a make produces lives outside the repo in
`~/.farm-factory-motion/made/<name>/`. People go through the person chain here; animals through `../animals/`.

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
  `--measurements` drapes a kept look's own sized pattern 1:1 instead). `newton_drape.py` (the default, Newton's
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
