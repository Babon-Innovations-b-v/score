# tools/characters/people

The people route's own pieces (`../maker/` runs them): the body model and its skeleton (`body.py`: SOMA-X, shaped
through MHR where SAM 3D Body read a person's build; `person.py` the look's settings, `paths.py` where its files
lie), the clips' sentences and how Kimodo is asked for each (`clips.py`), the feet brought in to hip width
(`stance.py`), the glTF writer (`glb.py`), which part of the body a joint belongs to (`regions.py`) and the join and
stance measures over every frame of every clip (`joins.py`). It moved from 2099's `tools/crew` on 2026-10-08 with
its history; the crew builder that dressed the old looks there was retired on 2026-10-21.

## The one rule here

**Look at the geometry, do not only measure it.** The first attempt at moving a body onto a
different skeleton passed every check there was, bone counts and bounding boxes and height
stability, while producing twisted wreckage (#36, 2026-09-20). Numbers here tell you something
changed; only a picture tells you it is right.

## The sentence is the animation

`clips.py` holds a sentence per clip and nothing else decides what a person does. Changing a word
changes the walk, so a clip nobody can remake is a clip nobody can change. Keep the sentences
here, keep the generated files outside the repo, and keep the set small: this is the movement a
moon base needs, not a library. The suit walk is the sixth take, and the five before it are kept
on the box as the record of what "too wide" looked like. Every clip is made with one fixed seed
(`clips.CLIP_SEED`, owner 2026-10-21, #26) and its record (`<clip>.record.json`: sentence, seconds,
model, seed) is written beside it, so a lost clip is made again the same.

## What a clip gets, and why

A clip has the travel taken off and the body moved back over its node, is cut to a stretch that runs round (except
the clips in `clips.ONCE`, which play once and are kept whole), drops the fingers into the wrist, and has its feet
brought in to hip width (`stance.py`: Kimodo stands people twice as wide). Each of those is a decision with a reason,
and each reason is in `body.py`'s header. Undoing one is fine; undoing one without reading why is how the walk ends
up going through a wall again.

## The joins are measured

Only the head and hands of the body are drawn, so a hand or boot that does not reach into its sleeve or
trouser leg shows the background (owner, 2026-10-09). `joins.py` measures every wrist and ankle in every frame of
every clip, and the standing clip's stance, from the built file; the maker's chain keeps its record in
`checks/`. It measures; the pictures still decide.

## Licences

Recorded here because the repo is public and the body file ships:

- **Body and skeleton**: NVIDIA SOMA-X (Apache 2.0), shaped through Meta's MHR body (Apache 2.0).
- **The body's build**: read off a picture by SAM 3D Body (Meta SAM License, 19 Nov 2025: commercial use allowed;
  not for military or trade-controlled uses, no reverse engineering, and the licence ends for anyone who sues Meta).
  Its weights are not shipped; only the measured body shape is.
- **Motion**: Kimodo clips, as `docs/bible.md` `workflow/bootstrap` sets out.

## What the gate can run

`regions_test.py`, `glb_test.py`, `joins_test.py` and `stance_test.py`. The gate runs the tools' checks on a box with
no graphics card and no tool chain built, so nothing it runs may import torch or soma.
