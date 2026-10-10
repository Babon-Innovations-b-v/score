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
FCL: the meshes as one bounding volume tree, the people as solid boxes, so an eye inside one counts), and a ray along
it and two along the walker's body under it (BODY: its knee and its waist, so it never steps over a railing or a table)
meet nothing before its end. The people are the place's characters as boxes where they stand at the moments asked for
(the stage's first when none is), so one who walks is followed over them. `clearances` measures how far an eye stands
from the meshes and the people, as the demo's film checks measure every frame. The tree is grown by RRT* (Karaman and
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
# A box's corners, from its low corner (0) along z (1), y (2) and x (4).
UNIT_CORNERS = np.array(list(itertools.product((0.0, 1.0), repeat=3)))


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
    Structure and Fixtures meshes, the objects and the people at the time codes given, cast at by trimesh's rays:
    Embree's when embreex is installed, as the framework's environment has it), the same as solids for the clearance
    (`solid`: the meshes as one tree and each person's box), the ground's height under any (x, z), and the place's
    extent (x, z) without the ground."""
    laid = snap.read_place(stage_path)
    shown = {**laid["objects"], **laid["statics"]}
    still = trimesh.util.concatenate([*shown.values(), laid["ground"]])
    corners = np.vstack([mesh.bounds for mesh in shown.values()]) if shown else np.zeros((2, 3))
    extent = (corners[:, 0].min(), corners[:, 2].min(), corners[:, 0].max(), corners[:, 2].max())
    scenes = {"still": still, "tree": mesh_tree(still), "height": laid["height"], "extent": extent}
    return with_people(scenes, people_boxes(stage_path, times))


def with_people(scenes, boxes):
    """The place with these people's boxes ((count, 8, 3) corners) standing in it: in the mesh the rays meet and
    among the solids."""
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
    """Each view's eye's distance from the place's meshes and from the people's boxes at the view's own moment of the
    stage's time (its `frame`): two arrays, metres (clearances)."""
    boxes = people_corners(stage_path, [view.get("frame", 0) for view in views])
    measured = [clearances(scenes, view["eye"], boxes[view.get("frame", 0)]) for view in views]
    return np.array([walls[0] for walls, _ in measured]), np.array([persons[0] for _, persons in measured])


def stands_clear(walls, persons):
    """Whether eyes measured this far from the meshes and the people (clearances) keep the clearance: an eye's
    position is kept to 0.1 mm, so that much nearer still counts."""
    return (np.asarray(walls) >= CLEARANCE - KEPT_TO) & (np.asarray(persons) >= CLEARANCE - KEPT_TO)


def clearances(scenes, eyes, boxes=None):
    """How far each eye stands from the nearest mesh of the place and from the nearest of the people's boxes
    ((count, 8, 3) corners; the scenes' own when not given; 0 inside one): two arrays, metres, inf where there is
    nothing."""
    boxes = scenes["boxes"] if boxes is None else boxes
    walls = np.array([fcl.distance(scenes["tree"], fcl.CollisionObject(fcl.Sphere(1e-6), fcl.Transform(eye)),
                                   fcl.DistanceRequest(), fcl.DistanceResult()) + 1e-6 for eye in np.atleast_2d(eyes)])
    persons = np.array([box_distances(boxes, eye).min() if len(boxes) else np.inf for eye in np.atleast_2d(eyes)])
    return walls, persons


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
