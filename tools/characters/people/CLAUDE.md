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

The build takes the travel off every clip, cuts each one to a stretch that runs round, drops the
fingers into the wrist, and writes no material of any kind. Each of those is a decision with a
reason, and each reason is in `body.py`'s own header. Undoing one is fine; undoing one without
reading why is how the walk ends up going through a wall again.

## Two chains, one graphics card

Two runs on one card do not queue, they break, and on this box one has taken the whole machine
down. There is one card so there is one claim on it, and it is the prop chain's
(`tools/props/card.py`), loaded here by its path rather than by name, because that directory has
a `paths.py` of its own that would shadow this one's.

## What the gate can run

`regions_test.py` only. The gate runs the tools' checks with the system python on a box with no
graphics card and no tool chain built, so nothing it runs may import numpy, torch or soma. That
is why which part of the body a joint belongs to lives in its own module with no dependencies:
it is the part of this chain that can be pinned.
