# score/stages/terrain/

The terrain stage (the paper's Methods, "Terrain"): one world node, `terrain`, that makes every ground of the world
from its plan in `data/ground/plan/<ground>.json`. `__init__.py`'s docstring has the make and the gates.

- **The plan is the input; the method is here.** A plan lists its steps (`shape`) and its landforms' settings; the
  builders (`landforms.py`) and the step runner (`plan.py`) are code. A new landform kind is a builder here and a step
  name in `plan.LANDFORMS`, never numbers typed into a stage run.
- **The Moon's and Mars's builders are the game 2099's, moved unchanged in what they compute**, so the stage makes
  the grounds the game laid from the same plans: `terrain_test.py` holds that every copied rock comes back to the
  centimetre and the large shape lies within the old fine relief of the copied heights. Change a builder only with a
  measured before and after on those.
- **Never picture colours.** The diorama picture (Qwen-Image-Edit-2511, drawn straight down over the plan's drawing)
  gives relief only, through its depth (Depth Anything V2 Small); every zone of the ground takes exactly one library
  surface (`record.py`, the plan's `zones` rules), coloured by its design token.
- **A candidate is chosen by measurement**: the one whose smoothed depth follows the plan's large shape best
  (`relief.chosen`), its correlations kept in the ground's `measures.json`.
- **Paid, through the runner only.** `make` rents (pictures and depth, `tools/props/cloud/pictures.py` and
  `depth.py`) inside the runner's clearance; run it with `python -m score.stages run` (no places: the world's nodes),
  in the background.
- **A levelled yard `on_seat`** (the hangar, 2026-10-12) is held `height` under the flat plane of the seat it is
  `for`, not at one height: a room 46 m long on the Moon's 220 m ball stands on its seat's tangent plane, which rises
  off the ball towards its ends (`record.seat_plane`).
- **Its layout inputs are keyed on what it reads only** (`inputs.py`, 2026-10-12): of `data/scene`, `data/kit` and
  `data/motion` only each seated place's fields terrain's make and gates read, so a light, machine or people edit
  moves no ground. A new read of those records here needs its field added in `inputs.py`.
- **The gates measure places, not pictures**: `openings` composes each judged place's round-three stage with the made
  ground and its record's missing neighbours (`outside.py`) and casts rays (`sight.py`); `under` compares every object
  that stood on the old ground with the made one. On a small world the horizon dips with a viewer's height: a ray
  between level and that dip sees sky, not a void.
- Each ground's `places/<place>.usdc` is the layer a place's stage takes over its old ground (its neighbours reached as
  a stage folder's `layers/` reaches them, its water mirroring as the place's scene record has it); the assembly
  stage reads the terrain output and sublayers it as `layers/ground.usdc` just over the seed's base (experimental).
- **`terrain-look@<place>` (`look.py`, experimental, paid)** renders the place before (its seed) and after (the
  assembly output) on its round-three review cameras and gates on `horizon`: no view looks out under the horizon onto
  nothing. Only `look.LOOKED` places have the row (the proof place, launch, and the street, where the ground fills the view) until the owner has reviewed them. Run it
  with `python -m score run world1 --place launch --stage terrain-look --detach`, which drives terrain, assembly
  and the look and leaves the line's surface rows alone.
