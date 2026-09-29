# tools/crew

Builds the one file every person in the game is drawn from: `game/people/person_model/person_body.glb`.
It is the prop chain's sibling. Run it with `bash tools/crew/run.sh`; the chain itself is
installed once per box (`docs/bible.md`, `workflow/bootstrap`).

## The one rule here

**Look at the geometry, do not only measure it.** The first attempt at moving a body onto a
different skeleton passed every check there was, bone counts and bounding boxes and height
stability, while producing twisted wreckage (#36, 2026-09-20). Numbers here tell you something
changed; only a picture tells you it is right. Every run prints what it did to each clip and how
far Godot's skinning lands from the body model's own, and none of that is a substitute for
opening the game and looking at somebody.

## The sentence is the animation

`clips.py` holds a sentence per clip and nothing else decides what a person does. Changing a word
changes the walk, so a clip nobody can remake is a clip nobody can change. Keep the sentences
here, keep the generated files outside the repo, and keep the set small: this is the movement a
moon base needs, not a library. The suit walk is the sixth take, and the five before it are kept
on the box as the record of what "too wide" looked like.

## What comes out, and what deliberately does not

The build takes the travel off every clip and moves the body back over its node, cuts each one to
a stretch that runs round (except the clips in `clips.ONCE`, which play once and are kept whole),
drops the fingers into the wrist, dresses the body in the crew's two outfits (`dress.py`), and
gives only the outfits' parts a material, each carrying its painted picture. Each of those is a
decision with a reason, and each reason is in `body.py`'s or `dress.py`'s own header. Undoing one
is fine; undoing one without reading why is how the walk ends up going through a wall again.

## The look is kept, the outfits are rebuilt

The crew's look is the owner's drawing of them (#100). What offline tools made for it lives in
`~/.farm-factory-motion/look/` and is never remade by a run: the body's build, the two drapes,
the boots, the hair, the eyes and the drawn face (`paths.py` names each, the bible's
`workflow/bootstrap` says how each was made). Everything after that is code here and runs every
time: `work_suit.py`, `boots.py`, `face.py` and `space_suit.py` build the parts on the body,
`skin.py` weights them, `paint.py` paints them, `blender.py` has Blender thin and unwrap them. Two
runs from the same look write the same file byte for byte; keep it that way (a tie between two
labels is settled by sorting, never by a set's order). A change to a part's shape or colour is a
change here and a rebuild, then a picture of it, never a hand edit of the file.

## Licences of what the look is made from

Recorded here because the repo is public and the body file ships:

- **Body and skeleton**: NVIDIA SOMA-X (Apache 2.0), shaped through Meta's MHR body (Apache 2.0).
- **The body's build**: read off the owner's drawing by SAM 3D Body (Meta SAM License, 19 Nov
  2025: commercial use allowed; not for military or trade-controlled uses, no reverse engineering,
  and the licence ends for anyone who sues Meta). Its weights are not shipped; only the measured
  body shape is.
- **Clothing**: draped by GarmentCode and its NVIDIA Warp fork (both MIT), offline only.
- **Boots and hair**: Hi3DGen (MIT) from drawings by FLUX.2 klein 4B (Apache 2.0), as the prop
  chain uses them.
- **Eyes**: MakeHuman system assets (CC0, from the CC0 system pack). MakeHuman's base mesh was used
  only as a fitting reference and does not ship; none of MakeHuman's AGPL software is in the build.
- **Motion**: Kimodo clips, as `docs/bible.md` `workflow/bootstrap` sets out.

## Two chains, one graphics card

Two runs on one card do not queue, they break, and on this box one has taken the whole machine
down. There is one card so there is one claim on it, and it is the prop chain's
(`tools/props/card.py`), loaded here by its path rather than by name, because that directory has
a `paths.py` of its own that would shadow this one's.

## What the gate can run

`regions_test.py` and `glb_test.py`, and nothing else. The gate runs the tools' checks with the
system python on a box with no graphics card and no tool chain built, so nothing it runs may
import numpy, torch or soma. That is why the two pieces worth pinning, which part of the body a
joint belongs to and whether a written file is well formed, live in modules with no dependencies
at all.
