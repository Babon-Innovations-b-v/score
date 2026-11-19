# tools/characters/still_rig/

A still picture-made model (a TRELLIS.2 mesh, no skeleton) rigged as a player model on a dressed body's own skeleton
(#128, owner 2026-11-18: the paper's TRELLIS.2 astronaut for the walkers). `still_rig.py`'s docstring has the steps;
`blender_walk.py` renders its check frames on the processor.

- **The skeleton and clips are the dressed body's** (people-dress-<look>'s body.glb), only its arms turned onto the
  still's at the bind, so cast/driven, the walker peel and lay_walkers play it like the body it stands in for.
- **The still keeps its geometry**: stood, sized and thinned only; its outer surface alone (TRELLIS.2's thin shell
  has an inner layer facing the hollow, which no inside test or normal match can read).
- **Its finish is its own paint, graded** (owner 2026-11-19: "this pure trellis is just so much better ... the
  segmentation of the visor isnt perf and the seams"; the library rule's written exception for player models,
  `data/checks/library-exceptions.json`): the rigged still is laid flat on one map (`unwrapped`) and every texel reads
  the still's own base colour and metal and roughness nearest it on the outer faces (`Source`, `own_maps`), the base
  colour graded toward the place palette's tokens by the made props' grade (`place_build/maker/grade.py`, loaded by
  file). The parts only choose joints; the visor's dark is the still's own. A large colour group far from every token
  is named in `rig.json`'s `grade` (`mismatch`).
- **Hard parts ride one joint**: helmet and visor the head, backpack the chest, the cloth round them eased by distance
  over the surface (never across a gap: an arm beside the backpack keeps its own joint) and the helmet and backpack
  shared at their seam. The outer cut's holes are closed (`closed`, after the fit) and the cloth round any weight cliff
  (the crotch, the shoulders) smoothed (`eased_cliffs`). Measure (`rig.json` stretch, open edges) and look at the
  frames: a number says something changed, only a picture says it is right.
- Plain CPU here; any GPU render goes to the cloud, never this PC's card.
- Test: `test_a_rigged_still_rides_its_joints_without_a_crack.py`.
