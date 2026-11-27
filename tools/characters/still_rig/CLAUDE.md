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
- **A person** (`--person`, the stairwell woman, the street man and the crowd; 2026-11-19): its still is made on a
  cloud card (`score/stages/place_build/maker/cloud.py`) from its people-line close-up; it is stood at the body's own
  height (a slimmer person than the SOMA mean leaves most of the mean's skin outside her at every height, and the fit
  stretched the woman to 1.88 m), and its parts are its head and its clothes, neither rigid (a rigid head eased over
  hair resting on the shoulders hung her sleeves from her head). Its shoes are laid heel to toe on the body's foot skin
  (`feet_fitted`): the sim body stands, lifts and clears each step by the body's soles, and the woman's TRELLIS.2 shoes,
  3.4 cm past her toes, stood 2 cm in every tread. Each arm of the bind is turned onto the line from its
  shoulder through the middle of the still's sleeve (`arms_turned`): turned only parallel to it, the woman's arms
  hung 10 cm behind her sleeves, whose upper half took her chest's weights and bulged at the shoulder.
  Nothing above a foot's ankle hangs from that foot (`off_the_feet`, 2026-11-26): the generated stairwell woman's
  wide jeans, inpainted up from their hem, hung a quarter of their calf points from the foot and finned back at
  every push-off; nothing well over a knee hangs from that shin (`off_the_shins`, 2026-11-27: the same jeans hung
  thigh points 27 cm over the knee from the shin and spiked 18 cm off the thigh at every stride). A person whose arms
  lie against the trunk all the way down (no slice parts them: the hoodie man in an open overshirt, the older woman in
  a long coat, 2026-11-27) has each arm read as the sleeve at its side's outer edge (`fused_landmarks`): its axis for
  the turn, its points for the arm-only weight match. A person's clips never bring an arm in nearer its trunk than
  the still's own arm hangs at the bind (`arms_kept_out`, a soft floor on the arm's angle out across the trunk,
  only while it hangs down on its own side; 2026-11-27: the dressed body's walk swung the hands 3 to 6 degrees off
  the trunk while the older woman's coat and the hoodie man's overshirt hang their sleeves 9 to 20 out, and the hands
  went into the coat and the thighs). The arm's new local turns are written over the dressed body's keys.
- **The place clips** (2099 #161: the places' people had only the dressed body's five clips): `place_clips.py` makes
  the prologue's clips (talking, stairs up and down, the rail lean, looking out, waving, swaying) and makes again the
  work bodies' (leaning, pointing, checking, clipboard, cheering, waiting, clapping, shifting) from their own sentences
  in people/clips.py, read and never edited (the paid people rows key that folder), free on this PC's card through the
  card queue, Kimodo's text encoder on the processor; `../maker/prop_skeleton.py` rigs them (MOTION_WORK=<out>) and
  `clips_added.py` lays every clip a body's file lacks on its own skeleton by prop_build's steps, a climb's height run
  taken off (the game carries the body up the flight). The clips it had stay byte for byte. Look at the frames.
- Plain CPU here; any GPU render goes to the cloud, never this PC's card.
- Test: `test_a_rigged_still_rides_its_joints_without_a_crack.py`.
