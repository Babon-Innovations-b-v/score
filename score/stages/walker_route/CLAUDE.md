# score/stages/walker_route/

A walker's route and its motion (#128, owner 2026-11-17: "we need like a path finding algorithm, that can splice the
path into kimodo makable clips, and fills it then"). `__init__.py`'s docstring has the route, the pieces, what each
piece is asked, the join and the measures; `__main__.py` plans a place_build scene's walkers and assembles the
scene-clips output (cast, scene_clips.json) that sim body and cast/driven read; `tools/characters/clips/walker_route.py`
makes the pieces with Kimodo, free on this PC's card.

- **The route is the physics check's.** Routes come from place_build/ready `route` on its walkers' floor (doors open,
  every solid's footprint off, a WALKWAY wide), never a line drawn between spots. A route that cannot be found is
  refused there, never straightened through a wall.
- **Travel is the clips' own.** Each piece is made by Kimodo along its own stretch of route; a clip is never slid,
  stretched or looped along a line. A later piece starts from the pose the piece before stood in (fullbody keyframes
  on its first OVERLAP frames), so the join matches pose and velocity.
- **The measures are the limits**: foot skate per stance at most SKATE_MOST (2 cm), the root within ROUTE_MOST
  (10 cm) of its route, the body at least BODY_RADIUS from every solid between knee and head. Never widen one to pass.
- **The top of `__init__.py` holds numpy, json and math alone**: Kimodo's program loads the file by path in Kimodo's
  environment. Import place_build, cast or anything heavier inside the function that needs it.
- Test: `test_a_walker_keeps_off_every_solid_and_its_pieces_join.py` (a room with a wall in the way and one stair
  flight; Kimodo itself is not run there).
