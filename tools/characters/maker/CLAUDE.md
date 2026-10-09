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
- **Drapes** (`drape_garment.py`, run by `chain.py`): `garment.py` (GarmentCode's environment) sizes a design of
  `data/characters/garments/` to the body and makes its pattern and box mesh at two spacings, cut back into panels;
  `cloth_drape.py` (Blender 4.2 or 5.0) sews the coarse panels round the body, trying the design's sewing forces until
  no panel sags off it, settles it, and carries the fine panels onto it to settle; the folder it writes is read by
  `../people/drape.py` as GarmentCode's Warp drapes were. The cloth's settings are each design's `cloth.json`.
  Compared with the Warp drapes (Nev, 2026-10-09): more small crumples, a gathered waist on the space suit, wider
  sleeves standing off the arm, trousers a few centimetres shorter. Look at a new design's drape before it is used.
