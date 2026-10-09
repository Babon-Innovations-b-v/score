# tools/characters/people

Builds a file for each person a world draws (`paths.PEOPLE`, the game 2099's #112), each
`$MOTION_WORK/bodies/<person>.glb`: the crew with bodies of their own (take C, Nev,
Oona, Bram, Sefa: two outfits each, `dress.py`), the crew kit's six builds (every part a seed
mixes, `kit.py`), and the prologue's named people (the leader, the guard, the driver, the two
technicians: plain clothes, `prologue.py` and `plain.py`). `--crowd` bakes the prologue's far
crowd as an animation texture (`crowd_vat.py`), which the game 2099 draws its crowd from. Every
file has the same skeleton and clips. It is the prop chain's sibling. Run it with
`bash tools/characters/people/run.sh`; the chain itself is installed once per box (the game
2099's bible, `workflow/bootstrap` step 9, until it moves here). It moved from 2099's
`tools/crew` on 2026-10-08 with its history; the "game" below is 2099, the first world it built
people for, and `../skel_usd.py` is how its files reach a place's OpenUSD stage.

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
drops the fingers into the wrist, brings the feet in to hip width (`stance.py`: Kimodo stands
people twice as wide), dresses the body in the crew's two outfits (`dress.py`), and
gives only the outfits' parts a material, each carrying its painted picture. Each of those is a
decision with a reason, and each reason is in `body.py`'s or `dress.py`'s own header. Undoing one
is fine; undoing one without reading why is how the walk ends up going through a wall again.

## The look is kept, the outfits are rebuilt

Each person's look is the owner's drawing of them (#100, #112). What offline tools made for it
lives in `~/.farm-factory-motion/look/<person>/` and is never remade by a run: the body's build,
the two drapes, the boots, the hair, the eyes and the drawn face, and for everybody after take C
where their joints sit (`joints.json`) and what sets them apart (`person.json`, read by
`person.py`: colours, which outfits, glasses, a botanist's band, a name tag, a beard) (`paths.py`
names each, the bible's `workflow/bootstrap` says how each was made). One run builds one person,
because every module reads the look on import; `run.sh` runs one per person.

The parts were first placed on take C, and their numbers are places on his body. `fit.py` moves
each onto another person's body by their own joints, so a pocket stays the same share of the way
from belt to collar; a new number is written as take C's and passed through `fit`. Take C himself
is still built on the average body he was approved on (`average_body` in his `person.json`): his
own body is right for the clips, but redraped on it his drawn mouth doubled and his flag lost its
star, so that waits until his face and drapes are redone.

The crew kit's faces were read off one sheet of faces and are carried onto each build by the
body's own points (`faces.py`): a face's head is stood on the build's neck, and what was made on
take C's head (the eyes, the hairstyles, the brows' and irises' places) follows the points round
it. Those are measured on take C in take C's own numbers (`face.TAKE_C_BROW`, `skin.TAKE_C_NECK_CUT`),
never through `fit`. The kit's builds carry their torso's width up the body in `joints.json`,
because slim and broad builds differ by girth more than by where their joints are; a hard part is
widened with the torso only so far (`fit.hard_part_share`), and the chest pocket keeps its size.
One build takes about fifty minutes on this box's processor; build one at a time, never several
at once (two parallel runs took the machine down on 2026-09-30).

Everything after the look is code here and runs every time: `work_suit.py`, `boots.py`, `face.py` and `space_suit.py` build the parts on the body,
`skin.py` weights them, `paint.py` paints them, `blender.py` has Blender thin and unwrap them. Two
runs from the same look write the same file byte for byte; keep it that way (a tie between two
labels is settled by sorting, never by a set's order). A change to a part's shape or colour is a
change here and a rebuild, then a picture of it, never a hand edit of the file.

## The joins are measured

Only the head and hands of the body are drawn, so a hand or boot that does not reach into its sleeve or
trouser leg shows the background (owner, 2026-10-09). The bare hand runs half the forearm up under the cuff
(`skin.bare_hands`), a short sleeve is drawn to the wrist (`work_suit.sleeves_to_the_wrists`) and a short
trouser leg into its boot (`boots.lengthened`). `joins.py` measures every wrist and ankle in every frame of
every clip, and the standing clip's stance, from the built file; the maker's chain keeps its record in
`out/checks/`. It measures; the pictures still decide.

## Licences of what the look is made from

Recorded here because the repo is public and the body file ships:

- **Body and skeleton**: NVIDIA SOMA-X (Apache 2.0), shaped through Meta's MHR body (Apache 2.0).
- **The body's build**: read off the owner's drawing by SAM 3D Body (Meta SAM License, 19 Nov
  2025: commercial use allowed; not for military or trade-controlled uses, no reverse engineering,
  and the licence ends for anyone who sues Meta). Its weights are not shipped; only the measured
  body shape is.
- **Clothing**: sewing patterns by GarmentCode (MIT). The looks kept before 2026-10-09 were draped with its NVIDIA
  Warp fork, whose licence allows non-commercial research only; drapes from then on are Newton's cloth solver
  on upstream NVIDIA Warp (`../maker/newton_drape.py`; both Apache-2.0), or Blender's cloth as a second route
  (`../maker/cloth_drape.py`; Blender is GPL, its output is ours). Every built body's report names the simulator of each
  drape it wears (`cloth_licence.py`), and `../cast.py` refuses a cast that draws a body whose drapes are not
  commercial-OK; `python3 cloth_licence.py` checks every person's body.
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

`regions_test.py`, `glb_test.py` and `cloth_licence_test.py`, and nothing else. The gate runs the tools' checks with the
system python on a box with no graphics card and no tool chain built, so nothing it runs may
import numpy, torch or soma. That is why the two pieces worth pinning, which part of the body a
joint belongs to and whether a written file is well formed, live in modules with no dependencies
at all.
