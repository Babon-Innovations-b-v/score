# tools/characters/maker/

The character maker: a person's rigged, clothed, animated body as glTF and UsdSkel, with its far level for crowds,
from the look the people line drew (the prop route and the people route, `prop_person.py`, run by the people's body
rows in `score/stages/people_bodies`), and its clips and the mean rig (`prop_person.clips_rig`, the row
`people-clips-made`); by hand, `make.py` takes a person's spec to the same route and an animal's to `../animals/`.
Specs are `data/people/specs/<name>.json` (`spec.py` says what they hold; each written from a design's person row by
`score/stages/people_rows.py`). The shipped person chain (the A-pose picture, GarmentCode's drapes, the head, the
Hi3DGen hair, the depth-LoRA face, `rebuild.py`) and the prop route's own close-up drawing were retired on 2026-10-21
(owner: all old stuff is retired).

- **Experimental, refused unless asked for** (docs/bible.md, `architecture/experimental`): by hand the prop route and
  the animal route run only with `make.py --experimental`, and refuse when started round it (`prop_person.py` wants
  `--experimental` too, `route.make` its `experimental=True`). Proven: the prop route when the player and Nev pass
  tucks, pokes and skin-through-cloth on every clip and the owner picks them.
- **Nothing here runs a model on the owner's PC.** `prop_person.py` writes a make folder and hands it to
  `tools/props/cloud/characters.py`, which runs `prop_chain.py` (its steps through `chain.py`'s runner) on a rented
  card, set up by `characters_setup.sh` (Kimodo with SOMA-X, SAM3DBody-cpp). A step is tried on a held machine
  (`characters.py --hold`), never here; only plain CPU geometry runs here.
- **A make must be asked for.** A spec without `approved` (who asked, when) is refused before anything is rented.
- **Every step is timed.** `out/make.json` records each step's minutes and the card it ran on; those are the paper's
  numbers, never typed in by hand.
- **Look at the result.** As in `../people/`: the numbers say something changed, only a render says it is right.
- Licences of every piece are in the paper's models table and in `docs/bible.md`; a new model goes there before it is
  used.
- **The prop route** (`prop_person.py`, a spec's `"route": "prop"`; experimental, a trial, #5, owner 2026-10-10: "soma is for the
  rig, not the mesh"): Pixal3D's mesh of the people line's close-up of the look (the shared loop's take, laid in the
  props' work folder by the body row), stood level (head over the feet), thinned part by part to the shipped outfit's triangles (borders
  kept, so the parts stay shut), SOMA-X's skeleton placed inside it from the mesh's limbs at the mean bone lengths
  times the look's scale (an arm the slices barely find is laid from its shoulder to its hand part; `prop_rig.py`; its
  weights moved on by RSWT, the SOMA surface only their hidden source), GeoSAM2 parts and the close-up's SAM 2.1
  finish regions named by the judge in one run (three seeds; an unnamed part takes its mirror image's answers; a
  region's answer far from its own colour is not believed), tucks under the joins (`tucks.py`), built by
  `prop_build.py` (every hard thing, the hair and the bare hands on one joint, the cloth next to it eased onto that joint; the face cut from the
  close-up and the flag drawn are the only pictures, `prop_prints.py`; piping cut in as thin strips down the outside
  of the sleeves and trouser legs, `piping.py`), then the people route on the built body (below; it replaced the
  Newton garment settle and its baked shapes, deleted 2026-10-21, #26), and checked by `joins.py`, `pokes.py`
  (tucks, cloth through cloth against the shipped body's record, hard parts' stretch), `outline.py` and the
  reviewer's skin-through-cloth count, side by side on a rented processor machine (`inside/body_checks.py`); the
  people stage's look row renders it (`blender_shots.py`). Nothing but Pixal3D's mesh is drawn or shapes the look.
  Takes land only in `~/.farm-factory-motion/candidates/prop-people/`. Its numbers are `checks.txt` beside each take.
  A held machine keeps each make under its folder's name, so make folders carry the person and outfit
  (`make_place`).
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
