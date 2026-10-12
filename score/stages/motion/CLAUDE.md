# score/stages/motion/

The motion stage (the paper's Methods, "The canonical scene": motion; experimental, PRD #6): a place's motion layer,
the game's own timed motions (`data/motion/<place>.json`) and the movers SCORE gives the things that move there
(`data/movers/<place>.json`), written by `tools/usd/movers.py` over the place's seed stage. `__init__.py`'s docstring
has the make and the gates; `space.py` the measures of space (hulls, still surfaces, heights under a spot).

- **Motion that fits the place.** A mover's numbers are measured, not typed by eye: its path stays in its free space
  (`clear`), its speed in the cited range of its kind (`data/checks/motion.json`, every range with its source), its
  loop joins (`loops`), and it stays on what it moves on (`grounded`). Never widen a kind's range to pass a gate: find
  a better source, or put the path right.
- **Every moving kind moves, or says why not.** `covered` fails a prim of a moving kind the layer leaves standing
  unless the movers record's `still` gives the reason (the street's car parked with its driver waiting).
- **The game's timed motions stay the game's.** Their records (`data/motion`) are read as they are; the effects stage
  reads them too, so editing one moves the effects rows' keys. A place's movers record may set the layer's
  `seconds` so the game's loops also fit it whole.
- **A thing it starts inside is its mount** (a boom's rail, a hatch's frame), named in `clear`'s findings and not
  judged; a mover on a `rail` must keep touching one of them.
- **Only places with a movers record have the row.** The assembly does not take the layer yet: the final assembly of
  each place takes it in place of the seed's `layers/motion.usda`.
- Effects tied to motion (dust, exhaust) are the effects stage's (`follows`, `on`).
- `motion_test.py` makes a small stage of its own, writes a path, a swing and a slide, and breaks each gate once.
