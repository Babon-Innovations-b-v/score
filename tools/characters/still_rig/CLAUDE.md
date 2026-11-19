# tools/characters/still_rig/

A still picture-made model (a TRELLIS.2 mesh, no skeleton) rigged as a player model on a dressed body's own skeleton
(#128, owner 2026-11-18: the paper's TRELLIS.2 astronaut for the walkers). `still_rig.py`'s docstring has the steps;
`blender_walk.py` renders its check frames on the processor.

- **The skeleton and clips are the dressed body's** (people-dress-<look>'s body.glb), only its arms turned onto the
  still's at the bind, so cast/driven, the walker peel and lay_walkers play it like the body it stands in for.
- **The still keeps its geometry**: stood, sized and thinned only; its outer surface alone (TRELLIS.2's thin shell
  has an inner layer facing the hollow, which no inside test or normal match can read).
- **Its finish is library surfaces** (root rule): each part a palette variant (`FINISHES`) in its own token or the one
  `TOKENS` names (a neutral white suit, a dark visor), its recipe entry's address on the look; the still's baked texture
  only finds the visor (its largest dark piece in a helmet reaching 0.25 m) and is dropped. The paper figure's seams
  and panel lines are that baked texture, not relief: the rig keeps the relief the geometry has.
- **Hard parts ride one joint**: helmet and visor the head, backpack the chest, the cloth round them eased by distance
  over the surface (never across a gap: an arm beside the backpack keeps its own joint) and the helmet and backpack
  shared at their seam. The outer cut's holes are closed (`closed`, after the fit) and the cloth round any weight cliff
  (the crotch, the shoulders) smoothed (`eased_cliffs`). Measure (`rig.json` stretch, open edges) and look at the
  frames: a number says something changed, only a picture says it is right.
- Plain CPU here; any GPU render goes to the cloud, never this PC's card.
- Test: `test_a_rigged_still_rides_its_joints_without_a_crack.py`.
