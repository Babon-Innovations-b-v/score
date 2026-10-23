# score/stages/terrain/

The terrain stage (the paper's Methods, "Terrain"): one environment node, `terrain`, that makes every ground of the
environment from its design (`design.py`), and one place row, `ground-fit@<place>` (`fit.py`), that judges each place
standing on it. `__init__.py`'s and `fit.py`'s docstrings have the makes and the gates.

- **Everything in a place comes from the library (owner's hard rule, 2026-10-18).** Every finish, model, kit, effect,
  light, sound, character, ground and algorithm a place shows comes from score_lib, or is a written exception in
  `data/checks/library-exceptions.json` that names the place, the prim or pattern, what it is, why it is not from the
  library, who allowed it and when. Every finish is a library surface (`data/library`, the ProcFunc recipes and
  palette tokens): never a picture's own texture, a model's baked-in colour, a default grey or anything else; a
  picture-made model keeps its geometry and gets its finish replaced. The library check
  (`score/stages/complete/library`) lists what does not trace; bible `architecture/components`. The code ground
  names its row (its top scene's terrain row), the natural ground its finish is made with by rule
  (`score/stages/natural_grounds.py`: the row's words, else its body's physics; `recipe` in ground.json,
  `score:ground:recipe` on its meshes) and its finish as missing (`score:surface:missing`) until the surface
  line makes it: never painted another way.
- **The design is the only input** (the owner, 2026-10-21: everything old is retired; the game's ground plans, copied
  grounds, seats, landforms and rocks, `data/ground`, went with it). A ground is one body or plot of the environment
  concept's setting: each top scene stands at its site (its kept sky, `{home}/design/sky/<scene>.json`), each scene
  its plan holds where it holds it, unturned, its floor on the top's; the body's true sphere (its radius the
  setting's) or the plot's plane, raised by each kept plan's terrain spots (a thin-plate
  spline faded past the farthest spot). A scene no ground stands is no row of ground-fit; an outdoor one is a seat
  gap (`needs.py`) until its top scene has a site.
- **Terrain is a model layer (owner, 2026-10-20; CONTEXT.md "layer adapter").** Its detail (craters, tracks,
  outcrops) is the scene inventory's terrain rows, made by the shared loop like any row and joined into the ground by
  `join.py`'s `ground-join@<place>` (free, only where the place handed terrain rows), which cuts the code ground under
  each made piece, seats its rim into it and draws it as the object layer's assets are, gated on `seam`; the assembly
  takes its layer in place of terrain's (`stages.joined_ground`), and ground-fit judges the whole. Never add another
  way of making ground: the design's ground here is the named fallback, said so in every ground's `measures.json`
  (`made_by`, `MADE_BY`).
- **Each place's layer** (`places/<place>.usdc`, `outside.py`): the ground in its own frame under `/<place>/Outside`,
  `near` (its plan's box grown by NEAR_MARGIN, 0.5 m apart) and `far` (out past the horizon an eye 12 m up sees, at
  least 1.5 km), static colliders; the place's old `Ground`, `Terrain` and `Water` made inactive.
- **Gates**: `spots` (the drawn ground passes through every plan's terrain spot) and `curve` (the far ground has
  fallen by the body's true sagitta from the top scene's site). The place gates measure the place's own stage, not
  pictures (`ground-fit`, free): `under` (the ground under every object standing on it level enough), `floating`,
  `continuous` (rays straight down round the place for holes) and `openings` (its scene record's doorways onto a
  floor, no view ray into nothing: `sight.py`, the body's horizon dipping with the viewer's height).
- Test: `terrain_test.py` (a design of its own on the Moon: its ground, its gates both ways, the fit measures).
