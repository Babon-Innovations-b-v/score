# score/stages/terrain/

The terrain stage (the paper's Methods, "Terrain"): one environment node, `terrain`, that makes every ground of the environment
from its plan in `data/ground/plan/<ground>.json`, and one place row, `ground-fit@<place>` (`fit.py`), that judges each
seated place's own stage standing on it. `__init__.py`'s and `fit.py`'s docstrings have the makes and the gates.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`.
- **Terrain is a model layer (owner, 2026-10-20; CONTEXT.md "layer adapter").** Its shape comes from the place's rough
  model and its detail areas (outcrops, craters, cliffs, the ground round an outside building) from close-ups made into
  models through the prop pipeline, the same shapes-first loop as a building, joined into one continuous ground with
  collision and library finishes. The adapter (#27): `areas.py` works out each outdoor place's detail areas from its
  ground plan alone (a landform reaching into its fine patch) and lands them (`python -m score.stages.terrain.areas
  write <place>`) as scene inventory rows of the prop route, prop objects and surface takes, so the shared pipeline
  makes them; until landed each is a `missing` hole of the prop route (`needs.py`), priced through the pipeline's own
  units. `join.py`'s `ground-join@<place>` (free, only where area rows are landed) cuts the code ground under each
  made piece, seats its rim into it, gives each face its library surface and the mesh itself as collider, gated on
  `seam`; the assembly takes its layer in place of terrain's (`stages.joined_ground`), and ground-fit judges the
  whole. A piece the pipeline did not make leaves the code ground there, named. Never add another way of making ground (a picture
  model, a depth reading, a height field from anything but the plan's code): the plan's code shape here is the named
  fallback, said so in every ground's `measures.json` (`made_by`, `MADE_BY`). The diorama pictures and their depth
  (Qwen-Image-Edit, Depth Anything) were retired on 2026-10-20 for this rule.
- **Free and from the repository alone.** Terrain reads the plans, the copied grounds beside them, the library, the
  design tokens and the seated places' scene records and kits; never the work folder (its round-three seeds were lost
  with the old disk, 2026-10-19, and blocked every line behind it). Its place layers carry the ground only: a place's
  shown places are its own stage's and the neighbours row's.
- **The plan is the input; the method is here.** A plan lists its steps (`shape`) and its landforms' settings; the
  builders (`landforms.py`) and the step runner (`plan.py`) are code. A new landform kind is a builder here and a step
  name in `plan.LANDFORMS`, never numbers typed into a stage run.
- **The Moon's and Mars's builders are the game 2099's, moved unchanged in what they compute**, so the stage makes
  the grounds the game laid from the same plans: `terrain_test.py` holds that every copied rock comes back to the
  centimetre and the large shape lies within the old fine relief of the copied heights. Change a builder only with a
  measured before and after on those.
- **Never picture colours.** Every zone of the ground takes exactly one library surface (`record.py`, the plan's
  `zones` rules), coloured by its design token.
- **A levelled yard `on_seat`** (the hangar, 2026-10-12) is held `height` under the flat plane of the seat it is
  `for`, not at one height: a room 46 m long on the Moon's 220 m ball stands on its seat's tangent plane, which rises
  off the ball towards its ends (`record.seat_plane`). A yard and its bank are the level's, not the base's held flats: the
  slope gate measures the flats off every level's box grown by its blend (`measures.yards`).
- **Its layout inputs are keyed on what it reads only** (`inputs.py`, 2026-10-12): of `data/scene` and `data/kit` only
  each seated place's fields terrain's make reads (floor, water mirror, seat offset, pieces' spots), so a light, view,
  door, machine or people edit moves no ground. A new read of those records here needs its field added in `inputs.py`.
- **The place gates measure the place's own stage, not pictures** (`ground-fit`, free): its neighbours output where
  it shows other places, else its assembly, which takes `places/<place>.usdc` over its old ground. `under` compares
  every object that stood on the old ground with the made one; `floating` fails an object hanging over the ground;
  `continuous` casts rays straight down round the place for holes; `openings` casts rays from inside (`sight.py`). On a
  small environment the horizon dips with a viewer's height: a ray between level and that dip sees sky, not a void.
- **`terrain-look@<place>` (`look.py`, experimental, paid)** renders the place before (its seed) and after (the
  assembly output) on its round-three review cameras and gates on `horizon`. Only `look.LOOKED` places have the row
  until the owner has reviewed them; it still reads the lost seed and views copy (#27).
