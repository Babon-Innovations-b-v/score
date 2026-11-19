# score/stages/walker_route/

A walker's route and its motion (#128, owner 2026-11-17: "we need like a path finding algorithm, that can splice the
path into kimodo makable clips, and fills it then"). `__init__.py`'s docstring has the route, the pieces, what each
piece is asked, the join and the measures; `__main__.py` plans a place_build scene's walkers and assembles the
scene-clips output (cast, scene_clips.json) that sim body and cast/driven read; `tools/characters/clips/walker_route.py`
makes the pieces with Kimodo, free on this PC's card.

- **The route is the physics check's.** Routes come from place_build/ready `route` on its walkers' floor (a shut door
  a solid, one marked `score:opens` swung open, every solid's footprint off, a WALKWAY wide), never a line drawn between spots. A route that cannot be found is
  refused there, never straightened through a wall.
- **Travel is the clips' own.** Each piece is made by Kimodo along its own stretch of route; a clip is never slid,
  stretched or looped along a line. A later piece starts from the pose the piece before stood in (fullbody keyframes
  on its first OVERLAP frames), so the join matches pose and velocity.
- **A door a walker goes through opens** (owner 2026-11-18: she "does just walk through the door"): only a door
  marked `score:opens` is a way; `doors` times its swing from the plan (open OPEN_AHEAD before each crossing, shut
  SHUT_AFTER past it) and writes it on the door's prim in scene.usda's root layer, the film's own timeline.
- **The measures are the limits**: foot skate per stance at most SKATE_MOST (2 cm), the root within ROUTE_MOST
  (10 cm) of its route, the body at least BODY_RADIUS from every solid between knee and head, the standing foot within
  GROUND_MOST (3 cm) of the ground under it. Never widen one to pass.
- **A step a tread, left and right** (owner, 2026-11-19: "the step planning is just no where, like it would need an
  actual left or right step per step"; then "it needs to be through kimodo, otherwise it will just be warped
  motion"): `footholds` plans one foot on every tread from the solids under the route (`levels`), alternating, each
  sole whole on its tread NOSING_BACK back from its nosing, landings walked at Kimodo's cadence, and the route's
  height is the footholds' (`stood_roots`), never the floor cells' (a cell over a riser takes the upper tread's).
  The footholds drive Kimodo itself: each is a left- or right-foot keyframe whose rest pose sets that sole on it
  (`hips_over`, `sided`), Kimodo's post-processing on for climbs too (it pins their height; without it the soles
  missed by 7 cm along, 6 across and 2 up). Never move a made motion's legs onto them. `foothold_faults` is the check
  (a stair rule: the ball and toes on one tread within ON_TREAD_MOST, the ball back from the nosing, nothing through
  the riser above or into the tread, a climbing heel hanging over the nosing at most HEEL_OVERHANG_MOST, a
  descending sole whole; one stance a tread, alternating); its stances come from the joints, since a climb's
  foot_contacts mark none. `ground` stands the made motion's standing foot on the scene's ground on every frame
  before the rig is made, since Kimodo's climb walks on up past a flight's last tread, a stance on a planned
  foothold on the tread that foothold names (`held_gaps`: a toe over the next riser once lifted her a riser).
- **A flat piece walks upright** (owner, 2026-11-18: the street walker "rlly walks like a monkey"): its knees straighten
  within KNEE_STRAIGHT and each hand swings at least SWING_LEAST (`posture`, `slouched`), else it is made again from the
  next of SEED_TRIES seeds and refused after the last; the sentence alone did not hold it (a third of seeds crouched
  under every sentence tried).
- **The top of `__init__.py` holds numpy, json and math alone**: Kimodo's program loads the file by path in Kimodo's
  environment. Import place_build, cast or anything heavier inside the function that needs it.
- Test: `test_a_walker_keeps_off_every_solid_and_its_pieces_join.py` (a room with a wall in the way and one stair
  flight, its footholds planted and checked both ways; Kimodo itself is not run there).
