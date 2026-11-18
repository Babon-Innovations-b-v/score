# tools/characters/still_rig/

A still picture-made model (a TRELLIS.2 mesh, no skeleton) rigged as a player model on a dressed body's own skeleton
(#128, owner 2026-11-18: the paper's TRELLIS.2 astronaut for the walkers). `still_rig.py`'s docstring has the steps;
`blender_walk.py` renders its check frames on the processor.

- **The skeleton and clips are the dressed body's** (people-dress-<look>'s body.glb), only its arms turned onto the
  still's at the bind, so cast/driven, the walker peel and lay_walkers play it like the body it stands in for.
- **The still keeps its geometry**: stood, sized and thinned only; its outer surface alone (TRELLIS.2's thin shell
  has an inner layer facing the hollow, which no inside test or normal match can read).
- **Its finish is library surfaces** (root rule): each part a palette variant (`FINISHES`), its recipe entry's address
  on the look; the still's baked texture only finds the visor and is dropped.
- **Hard parts ride one joint**: helmet and visor the head, backpack the chest, the cloth round them eased by distance
  and the helmet and backpack shared at their seam. Measure (`rig.json` stretch) and look at the frames: a number
  says something changed, only a picture says it is right.
- Plain CPU here; any GPU render goes to the cloud, never this PC's card.
- Test: `test_a_rigged_still_rides_its_joints_without_a_crack.py`.
