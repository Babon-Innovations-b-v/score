"""A review walkthrough camera's path through a place at eye height that never passes through a wall: an RRT* path
from a start to a goal, or a loop through waypoints, smoothed and laid out as the review walk's frames.

    .venv/bin/python tools/usd/camera_paths.py <stage.usda> (--start x,z --goal x,z | --loop x,z x,z ...)
        [--bounds xmin,zmin,xmax,zmax] [--seed N] [--eye 1.6] [--clearance 0.25] [--frames 60] [--out walk.json]

Every point of the path is an eye EYE_HEIGHT over the floor under it (the first surface a ray down meets: the place's
ground, or y = 0 on a flat place, the scene record's Structure meshes, a deck, a stepped floor, and the objects, a kit
room's floor plates; never a person), the ray starting CLIMB over the eye height above the ground there; the tree's new
points look from CLIMB over the eye they grow from, so a path that starts on a balcony or a stair stays on it, and a
point more than STEP_RISE over or under that eye (a table top, a ledge, a pit) is not taken, nor an edge with no floor
under it somewhere along it (edges_floored). A start and goal joined by a walkable straight edge are that edge. An edge
between two eyes is valid only when every point of it, its ends too, keeps the clearance (CLEARANCE) from every object,
Structure or Fixtures mesh, the ground and every person (a ball of that radius swept along it meets none of them in
FCL: the meshes as one bounding volume tree, the people and the moving things as solid boxes, so an eye inside one counts), and
a ray along it and two along the walker's body under it (BODY: its knee and its waist, so it never steps over a railing
or a table) meet nothing before its end. The people are the place's characters, and the moving things what the stage's motion
layer moves (tools/usd/motion_layer.py: the garage's rover, a hatch's leaf, a crane's trolley), as boxes where they stand at
the moments asked for (the stage's first when none is), so one who walks or drives is followed over them: the garage's
rover once drove through a film's camera, its path planned on the stage at rest (2026-10-18). `clearances` measures
how far an eye stands from the meshes and from the people and moving things, as the demo's film checks measure every frame. The tree is grown by RRT* (Karaman and
Frazzoli, 2011: each new point joined to the cheapest valid parent near it, then the near points rewired through it
when that is shorter), seeded, so the same place and seed give the same path. The path found is cut short wherever a straight valid edge skips
points, then laid out evenly as `--frames` views, each aimed LOOK_AHEAD metres further along it.

The output is a JSON list of views in the review walk's format (tools/review/renders.py: name `walk-NNN`, eye, aim, up,
fov, look_only), which renders.render_stage and walk_video take as they take the walk renders.py makes; renders.py
itself does not read it. The demo's place films (tools/review/demo.py) walk their shots with `leg`. The bounds default
to the extent of the place's objects and Structure and Fixtures meshes.
"""
import argparse
import itertools
import json
import pathlib
import sys

import fcl
import numpy as np
import trimesh

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "review"))
import renders  # noqa: E402
import snap  # noqa: E402

# A standing eye over the floor (renders.py's walk inside a room), and how far over it a ray down for the floor starts.
EYE_HEIGHT = renders.STANDING
CLIMB = 0.5
# The most one step of the path (STEP along) may rise or drop (metres): a stair's at its steepest, about 37 degrees;
# more is a table top, a ledge or a pit, not a step.
STEP_RISE = 0.6
# How often along an edge the floor under it is looked for (metres).
FLOOR_STEP = 0.25
# How far round an edge's line it must be clear (metres), checked by four rays offset that far.
CLEARANCE = 0.25
# Heights over the floor (metres) the walker's body must be clear at too, under its eye: its knee and its waist.
BODY = (0.4, 1.0)
# RRT*: how many points are tried, how far a new point reaches from the nearest, how near another point must be to
# be weighed as its parent or rewired through it, and how often the goal itself is tried.
ITERATIONS = 900
STEP = 0.8
NEAR = 1.8
GOAL_BIAS = 0.1
# Where each frame looks: this far further along the path, at eye height.
LOOK_AHEAD = 2.0
FOV = 75.0
# How finely a view keeps its eye (renders.looking rounds to 0.1 mm), as a clearance measure's tolerance (metres).
KEPT_TO = 1e-4
# A triangle with less area than this (square metres) is taken for a line.
FLAT_AREA = 1e-9
# What a stage moves that is no solid to keep clear of: its people, boxed by people_corners, and its particles.
NOT_SOLID = ("Characters", "Effects")
# A box's corners, from its low corner (0) along z (1), y (2) and x (4).
UNIT_CORNERS = np.array(list(itertools.product((0.0, 1.0), repeat=3)))
# A still view (a look the light is rendered and judged on) stands in free air: its eye outside every solid and
# CLEARANCE from every mesh, and its picture meets no surface nearer than LOOK_CLEAR along its middle nor over more
# than NEAR_MOST of a PICTURE_RAYS grid of rays through its picture. A surface nearer than a doorway eye stands in
# from its door (scene_record's VIEW_IN) fills an 80 degree picture, 1.7 m across at 1 m (2026-11-02: flat's spot-2
# all wardrobe, street's views in its police car, square's spot-2 one black blob, base's spot-2 all link tube).
LOOK_CLEAR = 1.0
NEAR_MOST = 0.25
PICTURE_RAYS = (16, 9)
# An eye is inside a solid when at least this share of the rays it sends every way (INSIDE_WAYS) meet a surface from
# behind first, of a model whose box holds the eye (or the ground): from inside a closed mesh every one does, from a
# room none. A model whose box does not hold the eye cannot hold it, whichever way its faces turn: the shell's dome
# faces out and its wall pieces' sides in (tools/usd/builders.dome, slab), so from inside lab's domed round room 17 of
# 26 rays met a face from behind and every view was left out (2026-11-12).
INSIDE_SHARE = 0.5
INSIDE_WAYS = np.array([way for way in itertools.product((-1.0, 0.0, 1.0), repeat=3) if any(way)])
INSIDE_WAYS = INSIDE_WAYS / np.linalg.norm(INSIDE_WAYS, axis=1)[:, None]
# A view that is not clear turns about its eye this many degrees a try, either way, up to all the way round; else its
# eye moves out in rings this far apart, at this many headings, up to MOVE_MOST (metres), its aim moved with it.
TURN_STEP = 15
MOVE_STEP = 0.25
MOVE_MOST = 1.5
MOVE_HEADINGS = 16


def people(stage_path, times=None):
    """The place's characters (tools/characters/cast.py) as box meshes where they stand at each time code given (the
    stage's first moment when none is), each box once: a character who walks is followed over the times."""
    return [corners_mesh(corners) for corners in people_boxes(stage_path, times)]


def people_boxes(stage_path, times=None):
    """people's boxes as (count, 8, 3) corners, each box once."""
    found = people_corners(stage_path, times)
    return np.unique(np.round(np.concatenate([np.zeros((0, 8, 3)), *found.values()]), 4), axis=0)


def people_corners(stage_path, times=None):
    """Each person's box at each time code (the stage's first moment when none is given): {time: (count, 8, 3)
    corners}, a character's own box (Usd's bound of it, aligned with the stage's axes) and each of a crowd's instances
    its prototype's box turned and moved where the instancer stands it."""
    from pxr import Usd, UsdGeom, UsdSkel
    stage = Usd.Stage.Open(str(stage_path))
    found = stage.GetDefaultPrim().GetChild("Characters")
    times = [stage.GetStartTimeCode()] if times is None else sorted(set(times))
    if not found.IsValid():
        return {time: np.zeros((0, 8, 3)) for time in times}
    crowds, singles, prims = [], [], iter(Usd.PrimRange(found))
    for prim in prims:
        if prim.IsA(UsdGeom.PointInstancer):
            crowds.append(UsdGeom.PointInstancer(prim))
            prims.PruneChildren()
        elif prim.IsA(UsdSkel.Root):
            singles.append(prim)
            prims.PruneChildren()
    return {time: np.concatenate([np.zeros((0, 8, 3)), *(crowd_corners(crowd, Usd.TimeCode(time)) for crowd in crowds),
                                  single_corners(singles, Usd.TimeCode(time))]) for time in times}


def moves(stage):
    """The prims a stage moves over its time (its motion layer's: tools/usd/motion_layer.py and motion.py), each the topmost
    whose own transform may change, so a moving prim's children move with it; the people (people_corners) and the
    particles (NOT_SOLID) aside."""
    from pxr import Usd, UsdGeom
    found, prims = [], iter(Usd.PrimRange(stage.GetDefaultPrim()))
    for prim in prims:
        if prim.GetName() in NOT_SOLID:
            prims.PruneChildren()
        elif prim.IsA(UsdGeom.Xformable) and UsdGeom.Xformable(prim).TransformMightBeTimeVarying():
            found.append(prim)
            prims.PruneChildren()
    return found


def thing_corners(stage_path, times=None):
    """Each moving thing's box (Usd's bound of it, aligned with the stage's axes) at each time code (the stage's first moment
    when none is given): {time: (count, 8, 3) corners}."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_path))
    times = [stage.GetStartTimeCode()] if times is None else sorted(set(times))
    moving = moves(stage)
    return {time: single_corners(moving, Usd.TimeCode(time)) for time in times}


def moving_corners(stage_path, times=None):
    """The people's and the moving things' boxes at each time code: {time: (count, 8, 3) corners}."""
    people_found, moves_found = people_corners(stage_path, times), thing_corners(stage_path, times)
    return {time: np.concatenate([people_found[time], moves_found[time]]) for time in people_found}


def moving_boxes(stage_path, times=None):
    """moving_corners's boxes over every time code asked for, each box once: (count, 8, 3) corners."""
    found = moving_corners(stage_path, times)
    return np.unique(np.round(np.concatenate([np.zeros((0, 8, 3)), *found.values()]), 4), axis=0)


def single_corners(prims, time):
    """Each character's own box at a time code, as (count, 8, 3) corners."""
    from pxr import UsdGeom
    cache = UsdGeom.BBoxCache(time, [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    boxes = [cache.ComputeWorldBound(prim).ComputeAlignedRange() for prim in prims]
    return np.array([box_corners(box.GetMin(), box.GetMax()) for box in boxes if not box.IsEmpty()]).reshape(-1, 8, 3)


def crowd_corners(instancer, time):
    """Each instance of a crowd at a time code as its prototype's own box, turned and moved where the instancer
    stands it: (count, 8, 3) corners."""
    from pxr import UsdGeom
    stage = instancer.GetPrim().GetStage()
    cache = UsdGeom.BBoxCache(time, [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    sizes = [cache.ComputeUntransformedBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
             for path in instancer.GetPrototypesRel().GetTargets()]
    world = np.array(UsdGeom.Xformable(instancer.GetPrim()).ComputeLocalToWorldTransform(time))
    matrices = np.array(instancer.ComputeInstanceTransformsAtTime(time, time)).reshape(-1, 4, 4) @ world
    if not len(matrices) or not sizes:
        return np.zeros((0, 8, 3))
    kinds = np.asarray(instancer.GetProtoIndicesAttr().Get(time), dtype=int)[:len(matrices)]
    shapes = np.array([np.column_stack([box_corners(size.GetMin(), size.GetMax()), np.ones(8)])
                       if not size.IsEmpty() else np.full((8, 4), np.nan) for size in sizes])
    found = np.einsum("bij,bjk->bik", shapes[kinds], matrices)[:, :, :3]  # USD's matrices act on row vectors
    return found[~np.isnan(found).any(axis=(1, 2))]


def box_corners(low, high):
    """A box's 8 corners, low to high (UNIT_CORNERS' order)."""
    low = np.asarray(low, dtype=float)
    return low + UNIT_CORNERS * (np.asarray(high, dtype=float) - low)


def corners_mesh(corners):
    """A box given by its 8 corners as a closed mesh."""
    return boxes_mesh(np.asarray(corners)[None])


def boxes_mesh(boxes):
    """Boxes ((count, 8, 3) corners) as one mesh of closed boxes."""
    unit = trimesh.creation.box(bounds=[[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]])
    origin, edges = box_axes(np.asarray(boxes, dtype=float).reshape(-1, 8, 3))
    vertices = origin[:, None] + np.einsum("vj,bjk->bvk", np.asarray(unit.vertices), edges)
    faces = np.asarray(unit.faces)[None] + (np.arange(len(origin)) * len(unit.vertices))[:, None, None]
    return trimesh.Trimesh(vertices.reshape(-1, 3), faces.reshape(-1, 3), process=False)


def box_axes(corners):
    """Boxes' first corners and their three edges from it, along x, y and z before any turn: (count, 3) and
    (count, 3, 3), an edge a row."""
    return corners[:, 0], corners[:, [4, 2, 1]] - corners[:, :1]


def box_distances(corners, point):
    """How far a point lies from each box (count, 8, 3): 0 inside it."""
    origin, edges = box_axes(corners)
    lengths = np.linalg.norm(edges, axis=2)
    along = np.einsum("bij,bj->bi", edges / np.maximum(lengths, 1e-12)[..., None], np.asarray(point) - origin)
    outside = np.maximum(-along, 0.0) + np.maximum(along - lengths, 0.0)
    return np.linalg.norm(outside, axis=1)


def place_scenes(stage_path, times=None):
    """A place for the camera: one mesh of everything an edge must not cross and an eye may stand over (the ground, the
    Structure and Fixtures meshes, the objects, and the people and moving things at the time codes given, cast at by trimesh's rays:
    Embree's when embreex is installed, as the framework's environment has it), the same as solids for the clearance
    (`solid`: the meshes as one tree and each person's and moving thing's box), the ground's height under any (x, z), and the
    place's extent (x, z) without the ground."""
    laid = snap.read_place(stage_path)
    return scenes_of({**laid["objects"], **laid["statics"]}, laid["ground"], laid["height"],
                     moving_boxes(stage_path, times))


def scenes_of(shown, ground, height, boxes):
    """A place for the camera (place_scenes) from its models ({name: mesh in the place's frame}), its ground's mesh,
    the ground's height under any (x, z) and the people's and moving things' boxes; `owners` numbers the model each
    face of the mesh the rays meet comes from (-1 the ground's): models_round."""
    meshes = list(shown.values())
    still = trimesh.util.concatenate([*meshes, ground])
    owners = np.concatenate([np.full(len(mesh.faces), number) for number, mesh in enumerate(meshes)] +
                            [np.full(len(ground.faces), -1)]).astype(np.int64)
    if len(owners) != len(still.faces):
        raise ValueError(f"the place's mesh has {len(still.faces)} faces, its models {len(owners)}")
    corners = np.vstack([mesh.bounds for mesh in meshes]) if meshes else np.zeros((2, 3))
    extent = (corners[:, 0].min(), corners[:, 2].min(), corners[:, 0].max(), corners[:, 2].max())
    scenes = {"still": still, "tree": mesh_tree(still), "owners": owners, "model_bounds": model_bounds(meshes),
              "height": height, "extent": extent}
    return with_people(scenes, boxes)


def model_bounds(meshes):
    """Each model's box ((count + 1, 2, 3): its lowest and highest corner), in the order `owners` numbers them, and
    last (`owners`' -1) the ground's, unbounded: the ground's faces always count (inside_solid)."""
    return np.array([mesh.bounds for mesh in meshes] + [[[-np.inf] * 3, [np.inf] * 3]]).reshape(-1, 2, 3)


def with_people(scenes, boxes):
    """The place with these people's and moving things' boxes ((count, 8, 3) corners) standing in it: in the mesh the rays
    meet and among the solids."""
    solid = fcl.DynamicAABBTreeCollisionManager()
    solid.registerObjects([scenes["tree"], *(box_solid(corners) for corners in boxes)])
    solid.setup()
    return dict(scenes, boxes=boxes, blocking=trimesh.util.concatenate([scenes["still"], boxes_mesh(boxes)]),
                solid=solid)


def mesh_tree(mesh):
    """A mesh as one FCL collision object (its bounding volume tree), its triangles with no area left out: FCL takes
    an eye anywhere to touch one (measured on the workshop's wall pieces, 2026-10-10), and its edges are its
    neighbours' too."""
    faces = np.asarray(mesh.faces, dtype=np.int64)[np.asarray(mesh.area_faces) > FLAT_AREA]
    model = fcl.BVHModel()
    model.beginModel(len(mesh.vertices), len(faces))
    model.addSubModel(np.asarray(mesh.vertices, dtype=np.float64), faces)
    model.endModel()
    return fcl.CollisionObject(model, fcl.Transform())


def box_solid(corners):
    """A person's box (8 corners) as a solid FCL box: inside it counts as meeting it."""
    origin, edges = box_axes(np.asarray(corners)[None])
    lengths = np.linalg.norm(edges[0], axis=1)
    turn = (edges[0] / np.maximum(lengths, 1e-12)[:, None]).T
    if np.linalg.det(turn) < 0:  # a mirrored box is the same box turned
        turn[:, 0] = -turn[:, 0]
    return fcl.CollisionObject(fcl.Box(*np.maximum(lengths, 1e-6)),
                               fcl.Transform(turn, origin[0] + edges[0].sum(axis=0) / 2.0))


def eyes_over(scenes, flat, eye, tops=None):
    """The eye over the floor under each (x, z): (count, 3) points, the height -inf where no floor is under it. The ray
    down starts CLIMB over `tops` (an eye height at each point; the eye over the ground there when not given) and
    meets the place's meshes only: nobody stands on a person."""
    flat = np.atleast_2d(np.asarray(flat, dtype=float))
    if tops is None:
        tops = np.nan_to_num(np.asarray(scenes["height"](flat), dtype=float), nan=0.0) + eye
    start = np.broadcast_to(np.asarray(tops, dtype=float), (len(flat),)) + CLIMB
    origins = np.column_stack([flat[:, 0], start, flat[:, 1]])
    distances = first_hits(scenes["still"], origins, np.tile(snap.DOWN, (len(origins), 1)))
    return np.column_stack([flat[:, 0], start - distances + eye, flat[:, 1]])


def first_hits(mesh, origins, directions):
    """How far each ray goes before it meets the mesh: inf where it meets nothing."""
    distances = np.full(len(origins), np.inf)
    locations, rays, _ = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    distances[rays] = np.linalg.norm(locations - origins[rays], axis=1)
    return distances


def edges_clear(scenes, starts, ends, clearance):
    """Whether each edge (start to end) is clear: every point of it at least the clearance from every mesh and every
    person's box, its ends too (swept_clear), its own ray meets nothing before its end and neither do the body's under
    the eye."""
    starts, ends = np.atleast_2d(starts), np.atleast_2d(ends)
    spans = ends - starts
    lengths = np.linalg.norm(spans, axis=1)
    ways = spans / np.maximum(lengths, 1e-9)[:, None]
    offsets = [np.zeros(3)] + [np.array([0.0, height - EYE_HEIGHT, 0.0]) for height in BODY]
    origins = np.vstack([starts + offset for offset in offsets])
    distances = first_hits(scenes["blocking"], origins, np.tile(ways, (len(offsets), 1)))
    clear = np.all(distances.reshape(len(offsets), -1) > lengths, axis=0)
    if clearance > 0:
        clear &= np.array([swept_clear(scenes["solid"], start, end, clearance) for start, end in zip(starts, ends)])
    return clear


def swept_clear(solid, start, end, radius):
    """Whether a ball of the radius swept from start to end (a capsule) meets none of the solids."""
    span = np.asarray(end, dtype=float) - start
    length = float(np.linalg.norm(span))
    way = span / length if length > 1e-9 else np.array([0.0, 0.0, 1.0])
    swept = fcl.CollisionObject(fcl.Capsule(radius, max(length, 1e-9)),
                                fcl.Transform(turned_to(way), (np.asarray(start, dtype=float) + end) / 2.0))
    found = fcl.CollisionData(request=fcl.CollisionRequest())
    solid.collide(swept, found, fcl.defaultCollisionCallback)
    return not found.result.is_collision


def turned_to(way):
    """A turn taking z onto the unit vector `way`."""
    axis = np.cross([0.0, 0.0, 1.0], way)
    sine, cosine = float(np.linalg.norm(axis)), float(way[2])
    if sine < 1e-9:
        return np.eye(3) if cosine > 0 else np.diag([1.0, -1.0, -1.0])
    axis /= sine
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    return np.eye(3) + sine * cross + (1.0 - cosine) * cross @ cross


def frame_clearances(scenes, stage_path, views):
    """Each view's eye's distance from the place's meshes and from the people's and moving things' boxes at the view's own
    moment of the stage's time (its `frame`): two arrays, metres (clearances)."""
    boxes = moving_corners(stage_path, [view.get("frame", 0) for view in views])
    measured = [clearances(scenes, view["eye"], boxes[view.get("frame", 0)]) for view in views]
    return np.array([walls[0] for walls, _ in measured]), np.array([persons[0] for _, persons in measured])


def stands_clear(walls, persons):
    """Whether eyes measured this far from the meshes and the people (clearances) keep the clearance: an eye's
    position is kept to 0.1 mm, so that much nearer still counts."""
    return (np.asarray(walls) >= CLEARANCE - KEPT_TO) & (np.asarray(persons) >= CLEARANCE - KEPT_TO)


def clearances(scenes, eyes, boxes=None):
    """How far each eye stands from the nearest mesh of the place and from the nearest of the people's and moving things' boxes
    ((count, 8, 3) corners; the scenes' own when not given; 0 inside one, a closed mesh too: inside_solid; FCL
    measures an eye inside a wardrobe by its walls, 2026-11-04): two arrays, metres, inf where there is nothing."""
    boxes = scenes["boxes"] if boxes is None else boxes
    walls = np.array([0.0 if inside_solid(scenes, eye) else
                      fcl.distance(scenes["tree"], fcl.CollisionObject(fcl.Sphere(1e-6), fcl.Transform(eye)),
                                   fcl.DistanceRequest(), fcl.DistanceResult()) + 1e-6 for eye in np.atleast_2d(eyes)])
    persons = np.array([box_distances(boxes, eye).min() if len(boxes) else np.inf for eye in np.atleast_2d(eyes)])
    return walls, persons


def picture_ways(view, size):
    """The unit ways from a view's eye through a PICTURE_RAYS grid of its picture (`size` [wide, tall] pixels, its
    fov across), the middle first."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(forward, np.asarray(view.get("up", [0.0, 1.0, 0.0]), dtype=float))
    right /= np.linalg.norm(right)
    upward = np.cross(right, forward)
    half = np.tan(np.radians(view["fov"]) / 2.0)
    across = (np.arange(PICTURE_RAYS[0]) + 0.5) / PICTURE_RAYS[0] * 2.0 - 1.0
    down = ((np.arange(PICTURE_RAYS[1]) + 0.5) / PICTURE_RAYS[1] * 2.0 - 1.0) * size[1] / size[0]
    sideways, upwards = np.meshgrid(across * half, down * half)
    ways = forward + sideways.reshape(-1, 1) * right + upwards.reshape(-1, 1) * upward
    return np.vstack([forward, ways / np.linalg.norm(ways, axis=1)[:, None]])


def inside_solid(scenes, eye):
    """Whether an eye stands inside a solid of the place (scenes_of): at least INSIDE_SHARE of the ways round it
    (INSIDE_WAYS) meet first a face from behind of a model whose box holds the eye, or of the ground."""
    eye = np.asarray(eye, dtype=float)
    mesh = scenes["still"]
    origins = np.tile(eye, (len(INSIDE_WAYS), 1))
    _, rays, faces = mesh.ray.intersects_location(origins, INSIDE_WAYS, multiple_hits=False)
    behind = np.einsum("ij,ij->i", mesh.face_normals[faces], INSIDE_WAYS[rays]) > 0
    bounds = scenes["model_bounds"][scenes["owners"][faces]]
    holds = np.all((bounds[:, 0] <= eye) & (eye <= bounds[:, 1]), axis=1)
    return int((behind & holds).sum()) >= INSIDE_SHARE * len(INSIDE_WAYS)


def models_round(scenes, eye):
    """The models (their numbers in the scenes' `owners`) an eye stands within, open or closed: at least INSIDE_SHARE
    of the ways round it (INSIDE_WAYS) meet that one model first, from either side. An eye in an open tunnel stands
    within it though no face is behind it (inside_solid); an eye in a room meets its walls, floor and things by
    turns (2026-11-11: workshop's from-door-2 moved out through its door into glass_tunnel_left_1)."""
    origins = np.tile(np.asarray(eye, dtype=float), (len(INSIDE_WAYS), 1))
    _, _, faces = scenes["still"].ray.intersects_location(origins, INSIDE_WAYS, multiple_hits=False)
    met = scenes["owners"][faces]
    counts = np.bincount(met[met >= 0])
    return set(np.flatnonzero(counts >= INSIDE_SHARE * len(INSIDE_WAYS)).tolist())


def steps_in(scenes, view, spot, inside, within):
    """Whether a still view's eye may move to the spot: a straight line reaches it (reached), into no model the eye
    did not already stand within (models_round: `within`, the eye's own), and an eye `inside` a solid steps no way
    back from its look, into the room it looks across, never out through the door behind it (2026-11-11: workshop's
    from-door-2 moved 1.25 m back out of its desk into the tunnel outside its door, its picture the desk's unlit
    back)."""
    eye = np.asarray(view["eye"], dtype=float)
    look = np.asarray(view["aim"], dtype=float) - eye
    backward = inside and float(np.dot((np.asarray(spot) - eye)[[0, 2]], look[[0, 2]])) < -KEPT_TO
    return not backward and reached(scenes, eye, spot, inside) and models_round(scenes, spot) <= within


def view_faults(scenes, view, size):
    """Why a still view would not see the place, [] when it does: its eye inside a solid, nearer than CLEARANCE to a
    mesh, a person or a moving thing, its middle meeting a surface nearer than LOOK_CLEAR, or more than NEAR_MOST of
    its picture doing so."""
    eye = np.asarray(view["eye"], dtype=float)
    if inside_solid(scenes, eye):
        return ["its eye stands inside a solid"]
    walls, persons = clearances(scenes, eye)
    found = [] if stands_clear(walls, persons)[0] else \
        [f"its eye stands {min(walls[0], persons[0]):.2f} m from a surface, nearer than {CLEARANCE:g} m"]
    ways = picture_ways(view, size)
    distances = first_hits(scenes["blocking"], np.tile(eye, (len(ways), 1)), ways)
    if distances[0] < LOOK_CLEAR:
        found.append(f"its look meets a surface {distances[0]:.2f} m ahead, nearer than {LOOK_CLEAR:g} m")
    near = float(np.mean(distances[1:] < LOOK_CLEAR))
    if near > NEAR_MOST:
        found.append(f"{near:.0%} of its picture is a surface nearer than {LOOK_CLEAR:g} m (at most {NEAR_MOST:.0%})")
    return found


def turned(view, eye, degrees):
    """The view with its eye at `eye`, its aim moved with it and turned about it by `degrees` round the up axis."""
    eye = np.asarray(eye, dtype=float)
    way = np.asarray(view["aim"], dtype=float) - np.asarray(view["eye"], dtype=float)
    cosine, sine = np.cos(np.radians(degrees)), np.sin(np.radians(degrees))
    way = np.array([way[0] * cosine - way[2] * sine, way[1], way[0] * sine + way[2] * cosine])
    return dict(view, eye=[round(float(value), 4) for value in eye],
                aim=[round(float(value), 4) for value in eye + way])


def reached(scenes, eye, spot, inside):
    """Whether a straight line from the eye reaches the spot through no surface (but the one it leaves when the eye
    stands `inside` a solid)."""
    span = np.asarray(spot, dtype=float) - eye
    length = float(np.linalg.norm(span))
    locations, _, _ = scenes["still"].ray.intersects_location([eye], [span / length], multiple_hits=True)
    crossed = int((np.linalg.norm(locations - eye, axis=1) < length).sum()) if len(locations) else 0
    return crossed <= int(inside)


def cleared_view(scenes, view, size):
    """(view, why): the view as it is when it sees the place (view_faults); else the nearest change that does, a turn
    about its eye of TURN_STEP or a move of its eye MOVE_STEP out (to a spot it steps in to: steps_in, its aim moved
    with it) weighing one step each, up to all the way round and MOVE_MOST out: a door's view keeps looking into the
    room where a short move clears it rather than turning to a wall; the change said in its `cleared`. (None, why)
    when nothing within reach clears it."""
    faults = view_faults(scenes, view, size)
    if not faults:
        return view, None
    eye = np.asarray(view["eye"], dtype=float)
    inside = inside_solid(scenes, eye)
    headings = np.linspace(0.0, 2.0 * np.pi, MOVE_HEADINGS, endpoint=False)
    rings = np.arange(1, int(round(MOVE_MOST / MOVE_STEP)) + 1)
    spots = [(0, eye)] + [(ring, eye + ring * MOVE_STEP * np.array([np.cos(heading), 0.0, np.sin(heading)]))
                          for ring in rings for heading in headings]
    within = models_round(scenes, eye)
    spots = [(ring, spot) for ring, spot in spots if ring == 0 or steps_in(scenes, view, spot, inside, within)]
    turns = [0] + [side * step for step in range(TURN_STEP, 181, TURN_STEP) for side in (1, -1)]
    tries = sorted(((ring + abs(degrees) // TURN_STEP, number, degrees) for number, (ring, _) in enumerate(spots)
                    for degrees in turns), key=lambda tried: tried[0])
    for _, number, degrees in tries:
        tried = turned(view, spots[number][1], degrees)
        if not view_faults(scenes, tried, size):
            moved = float(np.linalg.norm(spots[number][1] - eye))
            return dict(tried, cleared=f"moved {moved:.2f} m and turned {degrees:+d} degrees: "
                                       f"{'; '.join(faults)}"), None
    return None, "; ".join(faults) + f", every way it turns within {MOVE_MOST:g} m"


def edges_floored(scenes, starts, ends, eye=EYE_HEIGHT):
    """Whether a floor lies under each edge all along it: at every FLOOR_STEP the eye over the floor under the edge
    (looked for from CLIMB over the edge) stands within STEP_RISE of the edge there, so no edge crosses a pit, a
    stairwell's void or the drop off a balcony."""
    starts, ends = np.atleast_2d(starts), np.atleast_2d(ends)
    counts = np.maximum(np.ceil(np.linalg.norm((ends - starts)[:, [0, 2]], axis=1) / FLOOR_STEP).astype(int), 1)
    edge = np.repeat(np.arange(len(starts)), counts + 1)
    share = np.concatenate([np.linspace(0.0, 1.0, count + 1) for count in counts])
    spots = starts[edge] + (ends[edge] - starts[edge]) * share[:, None]
    found = eyes_over(scenes, spots[:, [0, 2]], eye, spots[:, 1])
    good = np.isfinite(found[:, 1]) & (np.abs(found[:, 1] - spots[:, 1]) <= STEP_RISE)
    return np.array([good[edge == index].all() for index in range(len(starts))])


def edges_walkable(scenes, starts, ends, clearance, eye=EYE_HEIGHT):
    """Whether each edge is clear (edges_clear) and has a floor under it all along (edges_floored)."""
    starts, ends = np.atleast_2d(starts), np.atleast_2d(ends)
    walkable = edges_clear(scenes, starts, ends, clearance)
    if walkable.any():
        walkable[walkable] = edges_floored(scenes, starts[walkable], ends[walkable], eye)
    return walkable


def descendants(parents, root):
    """Every point whose path to the start runs through the root, the root first."""
    found, waiting = [], [root]
    while waiting:
        node = waiting.pop()
        found.append(node)
        waiting += [child for child, parent in enumerate(parents) if parent == node]
    return found


def rewire(points, parents, costs, new, near, clear):
    """The near points that are cheaper reached through the new point re-parented to it, the cost of everything
    under them brought up to date."""
    for node, free in zip(near, clear):
        through = costs[new] + float(np.linalg.norm(points[node] - points[new]))
        if not free or node == parents[new] or through >= costs[node] - 1e-9:
            continue
        change = through - costs[node]
        parents[node] = new
        for below in descendants(parents, node):
            costs[below] += change


def rrt_star(scenes, start, goal, bounds, seed, eye=EYE_HEIGHT, clearance=CLEARANCE, iterations=ITERATIONS):
    """The shortest path RRT* finds between two eyes in the bounds (xmin, zmin, xmax, zmax): a list of eyes from start
    to goal, or None when none was found."""
    random = np.random.default_rng(seed)
    low, high = np.asarray(bounds[:2], dtype=float), np.asarray(bounds[2:], dtype=float)
    points, parents, costs = [np.asarray(start, dtype=float)], [-1], [0.0]
    for _ in range(iterations):
        target = goal[[0, 2]] if random.random() < GOAL_BIAS else random.uniform(low, high)
        flat = np.array(points)[:, [0, 2]]
        nearest = int(np.argmin(np.linalg.norm(flat - target, axis=1)))
        reach = target - flat[nearest]
        length = np.linalg.norm(reach)
        if length < 1e-6:
            continue
        new = eyes_over(scenes, flat[nearest] + reach * min(1.0, STEP / length), eye, [points[nearest][1]])[0]
        if not np.isfinite(new[1]) or abs(points[nearest][1] - new[1]) > STEP_RISE:
            continue
        near = [int(index) for index in np.flatnonzero(np.linalg.norm(flat - new[[0, 2]], axis=1) <= NEAR)]
        near = near if nearest in near else near + [nearest]
        clear = edges_walkable(scenes, np.array(points)[near], np.tile(new, (len(near), 1)), clearance, eye)
        if not clear.any():
            continue
        through = [costs[node] + float(np.linalg.norm(points[node] - new)) if free else np.inf
                   for node, free in zip(near, clear)]
        points.append(new)
        parents.append(near[int(np.argmin(through))])
        costs.append(float(min(through)))
        rewire(points, parents, costs, len(points) - 1, near, clear)
    return path_to_goal(scenes, points, parents, costs, goal, clearance, eye)


def path_to_goal(scenes, points, parents, costs, goal, clearance, eye=EYE_HEIGHT):
    """The cheapest path from the start through a point that reaches the goal by a walkable edge no longer than STEP,
    or None."""
    flat = np.array(points)
    close = np.flatnonzero(np.linalg.norm(flat - goal, axis=1) <= STEP)
    if len(close) == 0:
        return None
    clear = edges_walkable(scenes, flat[close], np.tile(goal, (len(close), 1)), clearance, eye)
    if not clear.any():
        return None
    ends = close[clear]
    node = int(ends[np.argmin([costs[index] + np.linalg.norm(points[index] - goal) for index in ends])])
    path = [goal]
    while node != -1:
        path.append(points[node])
        node = parents[node]
    return path[::-1]


def shortcut(scenes, path, clearance, eye=EYE_HEIGHT):
    """The path with every run of points a walkable straight edge can skip cut out, from the start on."""
    kept, index = [path[0]], 0
    while index < len(path) - 1:
        reachable = edges_walkable(scenes, np.tile(path[index], (len(path) - index - 1, 1)),
                                   np.array(path[index + 1:]), clearance, eye)
        index += int(np.flatnonzero(reachable).max()) + 1 if reachable.any() else 1
        kept.append(path[index])
    return kept


def leg(scenes, start, goal, bounds, seed, eye=EYE_HEIGHT, clearance=CLEARANCE):
    """The path from one eye to another: the straight edge when it is walkable, else RRT*'s path cut short; None when
    none was found."""
    if edges_walkable(scenes, start, goal, clearance, eye)[0]:
        return [np.asarray(start, dtype=float), np.asarray(goal, dtype=float)]
    found = rrt_star(scenes, start, goal, bounds, seed, eye, clearance)
    return None if found is None else shortcut(scenes, found, clearance, eye)


def laid_out(path, count, closed):
    """Count points spread evenly along the path (round it back to its start when it is closed), and the
    distance along it of each."""
    corners = np.array(list(path) + ([path[0]] if closed else []))
    along = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(corners, axis=0), axis=1))])
    spots = np.linspace(0.0, along[-1], count, endpoint=closed is False)
    return np.column_stack([np.interp(spots, along, corners[:, axis]) for axis in range(3)]), corners, along


def walk_views(path, count, closed):
    """The path as the review walk's frames: count eyes spread evenly along it, each looking LOOK_AHEAD further on
    (past the end straight on, round a closed loop from its start again)."""
    eyes, corners, along = laid_out(path, count, closed)
    total = along[-1]
    spots = np.linspace(0.0, total, count, endpoint=closed is False) + LOOK_AHEAD
    if closed:
        spots = spots % total
    ahead = np.column_stack([np.interp(spots, along, corners[:, axis]) for axis in range(3)])
    last_way = corners[-1] - corners[-2]
    last_way = last_way / max(np.linalg.norm(last_way), 1e-9)
    past = spots > total
    ahead[past] = corners[-1] + np.outer(spots[past] - total, last_way)
    return [renders.looking(f"walk-{number:03d}", eye, aim, fov=FOV, look_only=True)
            for number, (eye, aim) in enumerate(zip(eyes, ahead))]


def walk(stage_path, waypoints, closed=False, bounds=None, seed=0, eye=EYE_HEIGHT, clearance=CLEARANCE,
         frames=renders.WALK_FRAMES):
    """A walkthrough through the waypoints ((x, z), in order; round back to the first when closed) as the review
    walk's views."""
    scenes = place_scenes(stage_path)
    eyes = eyes_over(scenes, waypoints, eye)
    if not np.all(np.isfinite(eyes[:, 1])):
        raise ValueError("a waypoint has no floor under it")
    legs = list(zip(eyes, eyes[1:])) + ([(eyes[-1], eyes[0])] if closed else [])
    path = [eyes[0]]
    for number, (start, goal) in enumerate(legs):
        found = leg(scenes, start, goal, bounds or scenes["extent"], seed + number, eye, clearance)
        if found is None:
            raise ValueError(f"no clear path found from {start[[0, 2]]} to {goal[[0, 2]]}")
        path += found[1:]
    if closed:
        path = path[:-1]
    return walk_views(path, frames, closed)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("--start", type=snap.numbers)
    parser.add_argument("--goal", type=snap.numbers)
    parser.add_argument("--loop", type=snap.numbers, nargs="+", help="waypoints x,z walked round in order")
    parser.add_argument("--bounds", type=snap.numbers, help="xmin,zmin,xmax,zmax the path keeps inside")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--eye", type=float, default=EYE_HEIGHT)
    parser.add_argument("--clearance", type=float, default=CLEARANCE)
    parser.add_argument("--frames", type=int, default=renders.WALK_FRAMES)
    parser.add_argument("--out", type=pathlib.Path)
    options = parser.parse_args(snap.with_negatives(sys.argv[1:]))
    if options.loop is None and (options.start is None or options.goal is None):
        parser.error("give --start and --goal, or --loop")
    waypoints = options.loop or [options.start, options.goal]
    try:
        views = walk(options.stage, waypoints, options.loop is not None, options.bounds, options.seed, options.eye,
                     options.clearance, options.frames)
    except ValueError as problem:
        raise SystemExit(str(problem))
    text = json.dumps(views, indent=1)
    if options.out:
        options.out.write_text(text + "\n")
    else:
        print(text)


if __name__ == "__main__":
    main()
