# score/stages/place_build/ready/

Physics ready (#128, owner 2026-11-16: "this is alll very much not physics ready env's"): the placing agent's check of
a place_build scene for the walkers (sim body) and pushed objects, and its `on` helper. The CLI is place_build's
(`check`, `on`); this module tells, it never moves anything but what `on` is asked to lay.

- **Roles come from the scene**: `score:role` when set, else the object's marks, kind, name and library address
  (`role_of`). A role word list is not a judgement of quality: when a role reads wrong, set `score:role`, never widen
  a tolerance.
- **Reuse, no new physics**: resting.py's tolerances, weight and footprint; reach.py's Recast-style walker floor
  (spans, steps, pieces) with the walkway's own erosion; MuJoCo (settle_mujoco.py) for the settle. The settle runs in
  the physics trial's own Python (score/stages/physics/inside/newton_env.sh, MuJoCo as pinned there, the one sim
  body's walkers use), one small mjSpec model an object, free on this PC's CPU.
- **An adopted asset settles by its own MuJoCo physics** (#155, 2026-11-23): its mass and its colliders are read with
  its MuJoCo physics variant chosen in the session layer and put back after (`mujoco_chosen`), each collider by its
  authored approximation (`collider_of`: `convexHull` a hull, else its triangles), never its drawn shape; the
  workshop's adopted desk collides by an `sdf` (PhysX only) in its default variant and by its hull in MuJoCo's.
- **The walkers' ground and routes** (#128, 2026-11-16): `solids` is what a walker stands on and runs into (every
  object the check reads, every door as it stands for the walkers: shut, or swung open when marked `score:opens`
  (`swing_of`: into the shell it is set in, on the hinge that keeps the walkers' floor most whole, `floor_kept`), no characters), the ground sim body and scene clips read for a place_build
  scene (their input `place-build`, INPUT); `route` (`place_build route --through`) is a walker's way through spots on
  the check's own walkers' floor (WALKWAY wide): the shortest way over standing spans, its corners kept by line of
  sight and rounded over ROUND, so a walk path never leaves the floor the check judged. `route_on` walks a Place already read (area/:
  two joined places round their doorway, seated, every doorway open).
- **A joined leaf's far side is the area's** (2099 #161): the walkway check sends the walkers to both sides of every
  door, but a door leaf a join was recorded from (place.json `joins`, `from` "the door leaf <name>") leads into its
  neighbour on its far side, so that side is left to area/'s joins check (which walks a way through it, seated), never
  failed alone (the pad's walkway hatch opens onto the capsule, not onto the pad's floor). Seated among its neighbours
  (`check`'s `neighbours`) both sides are judged, their floor lent in.
- **The ground is read near the place**: a ground's faces more than GROUND_REACH past the laid objects' box are left
  out (`near_ground`), so a terrain to the horizon (800 000 faces) fits the 8 GB check; walkers' ground included.
- **A query reaches only what lies near it** (2026-11-16: camp's 660 rocks, 7 million faces, ran the check out of 14
  GB): every ray query and the settle's statics gather the faces of the objects whose box meets the query's own box
  (`Place.triangles_in`, `ray_box`), never one ray structure of the whole scene; only props are free bodies in the
  settle, static against static is never computed. A sky dome laid as an object (`score:kind` light) is no solid.
- **Every ray goes through `cast`** (#128, 2026-11-20): embree (trimesh's mesh.ray) drops a ray whose first face
  lies along it, and every later hit with it (engineroom's looks read open past a 45-degree bevel), so `cast` casts
  again, with trimesh's exact ray_triangle RAYS at a time, every ray embree still meets something past its last kept
  hit. ray_triangle alone takes ~30 ms a ray in the hangar (hours for its looks), so it is the fallback, never the pass.
- **Far scenery is no physics prop** (#128, 2026-11-17): a ground or fixed piece wholly more than GROUND_REACH past
  every walker's reach (the people and everything a walker meets) is `scenery` (`out_of_reach`), left out of every
  measure, so a far shore with no faces near the place or the horizon's mesas laid into their talus are never told.
  It is read from where the thing lies, never from a mark the agent sets.
- **A closed inside** (owner 2026-11-19: a concept's cut is the camera's, never the building's): `open_faults` casts
  rays from points LOOK_HEIGHTS over the walkers' floor; a point under a roof, slab or flight whose looks mostly meet
  a solid is inside, and a look of it that meets nothing within SEES is `open to the outside` (ready.json `open`),
  a gap no door (as laid, shut), window or glass closes. The fix is a wall built and, for the concept's cut-away, a
  camera cut (place.json `cut`, place_build `cut`), never a wider tolerance. The looks start from the walkers' floor
  with every door as laid for them (`look_floor`: shut, or swung open), never the walkway check's doors-open floor,
  whose doorways put points inside a shut door's own frame (storage, 2026-11-20), and reach SEES or, across a bigger
  place, its box's diagonal (`sight`: the hangar's 40 m looks fell short of its far walls). An outside place (place.json `kind`
  outside, place_build `kind`; a place without one is inside) is judged only in its structures' rooms (`rooms`: the
  object over the point closes it round on the level, itself, a door or what is mounted on it), so a street's awnings,
  arcades and overhangs are no inside (#128, 2026-11-20: the street read 711 points open, 15 after, at its shop fronts). An
  inside place with less than ROOFED of its walkers' floor under a roof, slab or flight is told `no roof`, never passed
  with nothing judged (#128, 2026-11-20: the stored engineroom@1, roofless, read open 0).
- **A seated place is checked among its neighbours** (`check <folder> --among <place>=<folder>`, `seated_among`;
  2099's prologue, 2026-11-22: the street's block hollowed round the seated stairwell and flat left the street's
  stair_door in no wall and the flat's room open where the stairwell stands): the place's backdrop left out, as its
  seated package leaves it, and every neighbour's objects but its props, people and backdrop laid in, seated into
  its frame (both place.json `seat`s, one area), named `<place>__<object>`, never judged here; only a neighbour's object
  within the place's sight is laid in (`within_sight`: its walkers' objects' box grown by `sight`; the flat among the
  square's 848 objects cast its looks at all of them and ran past 12 GB). Only the place's own
  objects are told, and its looks start only on its own floor under its own roof (`own_spots`, the two cast apart so
  a floor flush with a neighbour's reads as the neighbour's): a stretch on a neighbour's floor or under its roof is
  the neighbour's own check's. A door set in a neighbour's wall is judged in that wall, so its leaf fits that opening.
- **Memory is bounded** (2026-11-19: the Hong Kong square, its walkers' grid 1.6 km across, took 33 GB and froze the
  owner's PC): a surface's points are read CHUNK at a time (reach.surface_chunks, the very points sample_surface
  draws), and before the walkers' floor and the settle the check works out what they need and refuses past MEMORY
  (`within_memory`), naming what stretches it; the settle runs as many models side by side as fit. The nearest surface
  to a set of points (`nearest_to_surface`: a door's swing room, a connector's end ring) weighs at most PAIRS point and
  face pairs at once (2026-11-22: the capsule's hatch beside 1.2 million faces of dense models took a package past 12 GB). A
  ray query casts CAST_AT_ONCE rays at a time (`Place.hits`, `met`), each batch against the faces its own box meets
  (2026-11-22: the square's looks, cast all at once against the whole plaza, held past 12 GB), and a cast over
  COLLECTED faces frees its ray structure at once (`gc.collect`: a Trimesh holds itself round, so each batch's stayed). A new phase that
  grows with the scene gets its estimate there; never loosen a measure to fit.
- **Standing at a wrong angle** (`tilted`, 2099 #161, owner 2026-11-26: objects "stand at wrong angles in every
  place"): a prop's base (`base_of`: its convex hull's largest flat face looking down and holding its lowest point, a
  crate's bottom or the face its legs' ends span) turned past TILT off level; `floating` takes only the nearest foot,
  so a lamp made leaning on one edge passed before. An object with no flat base (a round bottom) is not judged. The fix
  is `on ... --upright` (its turn stands the base level, then it is laid at rest), never a wider TILT.
- **A planted fault per measure** is in the test fixture; a new measure gets its fault there, seen caught.
- Test: `test_every_planted_physics_fault_is_told_by_name.py` (its MuJoCo part prints skipped in a sandbox home with
  no newton_env; link `$PROPS_HOME/envs/newton_env` to run it whole).
