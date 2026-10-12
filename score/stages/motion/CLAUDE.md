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
- **Designed pass-throughs are written, never assumed.** A motion that passes through a still thing by its design (the
  airlock's doors sinking through a floor whose slot the stage does not cut, a door's edges in its wall's track) is
  the movers record's `through` ({motion: {prim pattern: why}}), shown in `clear`'s findings. A thing standing in a
  track by layout (the garage's pressure gauge in the big door's way) is a fault of the place, not a pass-through.
- **Hatches are fitted by the gate.** A hatch opens into its room as far as `clear` allows (100 degrees down to 60);
  one that strikes at every angle stays shut with the strike as its `still` reason.
- **A thing it starts inside is its mount** (a boom's rail, a hatch's frame), named in `clear`'s findings and not
  judged; a mover on a `rail` must keep touching one of them.
- **Over the place's accepted scene record, the place alone.** Where the place has a scene-record row the layer is
  written over its accepted record as the assembly writes it, else over the seed; the places it shows are left out
  (but their prims that move), since neighbours show each other. A game prim the new record names otherwise is the
  movers record's `renamed`; one the record dropped fails `covered`, never written to nothing, unless the movers
  record's `removed` gives the concept's reason (the workshop's robot turntable: concept K10 shows no robot).
- **Only places with a movers record have the row.** The assembly does not take the layer yet: the final assembly of
  each place takes it in place of the seed's `layers/motion.usda`.
- Effects tied to motion (dust, exhaust) are the effects stage's (`follows`, `on`).
- `motion_test.py` makes a small stage of its own, writes a path, a swing and a slide, and breaks each gate once.
