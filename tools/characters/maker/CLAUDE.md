# tools/characters/maker/

The character maker: one entry point (`make.py`) for a person or an animal, from a picture or a short description to a
rigged, clothed, textured, animated character as glTF and UsdSkel, with its far level for crowds and its clips. Specs
are `data/people/specs/<name>.json` (`spec.py` says what they hold; each written from a design's person row by
`score/stages/people_rows.py`); what a make produces lives outside the repo in `~/.farm-factory-motion/made/<name>/`.
People go through the prop route here; animals through `../animals/`.

- **Experimental, refused unless asked for** (docs/bible.md, `architecture/experimental`): the prop route and the
  animal route run only with `make.py --experimental`, and refuse when started round it (`prop_person.py` wants
  `--experimental` too, `route.make` its `experimental=True`). Proven: the prop route when the player and Nev pass
  tucks, pokes and skin-through-cloth on every clip and he picks them.
- **The shipped person chain is retired** (owner, 2026-10-21: all old stuff is retired): the A-pose picture, the body
  at rest, GarmentCode's drapes (`drape_garment.py`, `garment.py`, `newton_drape.py`, `cloth_drape.py`) on the garment
  designs of `data/characters/garments`, the head, the Hi3DGen hair, the depth-LoRA face, the build and its review,
  and `rebuild.py`, which draped kept looks again, went with the designs and the two hand-written makes
  (`data/characters/makes`). `make.py` refuses a person spec on no route; `chain.py` keeps only what the prop route's
  chain (`prop_chain.py`) runs on: the make's timed record (`Chain`) and the clips step (Kimodo). `drape_measure.py`
  and `sewing.py` stay: `pokes.py` measures cloth through cloth with them.
- **Nothing here runs a model on the owner's PC.** `prop_person.py` bundles a spec's files and hands them to
  `tools/props/cloud/characters.py`, which rents one card a person and runs `prop_chain.py` up there; the files it
  runs are each a step on that machine, each in its own environment (`characters_setup.sh` says which). A step is
  tried on a held machine (`characters.py --hold`), never here.
- **A make must be asked for.** A spec without `approved` (who asked, when) is refused before anything is rented.
- **Every step is timed.** `out/make.json` records each step's minutes and the card it ran on; those are the paper's
  numbers, never typed in by hand.
- **Look at the result.** As in `../people/`: the numbers say something changed, only a render says it is right.
- Licences of every piece are in the paper's models table and in `docs/bible.md`; a new model goes there before it is
  used.
- **The prop route** (`prop_person.py`, a spec's `"route": "prop"`; experimental, a trial, #5, owner 2026-10-10: "soma
  is for the rig, not the mesh"): Pixal3D's mesh from a klein close-up drawn in SOMA-X's bind pose (`batch.py
  --characters`, as the animals'), stood level (head over the feet), thinned part by part to the shipped outfit's
  triangles (borders kept, so the parts stay shut), SOMA-X's skeleton placed inside it from the mesh's limbs at the mean
  bone lengths times the look's scale (an arm the slices barely find is laid from its shoulder to its hand part;
  `prop_rig.py`; its weights moved on by RSWT, the SOMA surface only their hidden source), GeoSAM2 parts and the
  close-up's SAM 2.1 finish regions named by the judge in one run (three seeds; an unnamed part takes its mirror image's
  answers; a region's answer far from its own colour is not believed), tucks under the joins (`tucks.py`), built by
  `prop_build.py` (every hard thing, the hair and the bare hands on one joint, the cloth next to it eased onto that
  joint; the face cut from the close-up and the flag drawn are the only pictures, `prop_prints.py`; piping cut in as
  thin strips down the outside of the sleeves and trouser legs, `piping.py`), then the people route on the built body
  (below; it replaced the Newton garment settle and its baked shapes, deleted 2026-10-21, #26), and checked by
  `joins.py`, `pokes.py` (tucks, cloth through cloth against the shipped body's record, hard parts' stretch),
  `outline.py` and the reviewer's skin-through-cloth count; `blender_shots.py` renders it beside today's body. No
  SAM3DBody-cpp and no SOMA surface: nothing but Pixal3D's mesh is drawn or shapes it. Takes land only in
  `~/.farm-factory-motion/candidates/prop-people/`. Its numbers are `checks.txt` beside each take. A held machine keeps
  each make under its folder's name, so make folders carry the person and outfit (`make_place`). A close-up whose arms
  touch the body is refused before Pixal3D (`arm_gap_share`); klein copies a reference's pose over the words, so a spec
  may give a `pose_picture` to take the pose from.
- **The people route** (`route_*.py`, owner's pick of 2026-10-18, #10; experimental): every full body's binding
  since 2026-10-21 (#26: `prop_person.py route`, `prop_chain.py`'s identity and route steps on the body's held
  machine, after its build; the body row `people-body-<look>` runs build then route). Its clips and the mean rig
  come from the row `people-clips-made` (`prop_person.clips_rig`: `prop_chain.py`'s clips step, Kimodo with
  `clips.CLIP_SEED`, then rig). The built body rebuilt on the SOMA-X base laid under its look (`route_base.py`,
  with SOMA-X's pose correctives per clip), each garment region weighted from its own limb only and the arm and leg
  webs cut and closed (`route_bind.py`), the base drawn in the suit's cloth under the cut webs so the gap where an
  arm lifts off the side shows cloth (`route_build.py under_layer`), the head by one setting, `route_head.FACE`
  (the owner's choice, #26; until he decides `made`: the face Pixal3D made with its print from the close-up, no old
  body read; `drawn`: the made hair on the old SOMA-X head with its drawn face, `--old`), no settle shapes, the
  correctives as shared morph targets (`route_build.py`). The base's body under the clothes is SAM 3D Body's read of
  the take's close-up (`prop_person.py --stages identity`; the A-pose pictures were lost on 2026-10-19).
  Measured by `route_stretch.py` (longest triangle edge growth per clip) and `pokes.py`; pictured by
  `blender_route_shots.py` with the same cameras before and after. Plain CPU: SOMA-X's body model and its small
  correctives network on 4 threads in the motion environment (`route_base.py`), the rest numpy, run on the body's
  held characters machine (its motion environment; the PC's was lost on 2026-10-19).
  Proven: the player and Nev pass tucks and pokes on every clip and the owner picks the side-by-side.
