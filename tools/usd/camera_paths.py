"""A review walkthrough camera's path through a place at eye height that never passes through a wall: an RRT* path
from a start to a goal, or a loop through waypoints, smoothed and laid out as the review walk's frames.

    .venv/bin/python tools/usd/camera_paths.py <stage.usda> (--start x,z --goal x,z | --loop x,z x,z ...)
        [--bounds xmin,zmin,xmax,zmax] [--seed N] [--eye 1.6] [--clearance 0.25] [--frames 60] [--out walk.json]

Every point of the path is an eye EYE_HEIGHT over the floor under it (the place's ground, or y = 0 on a flat place, and
the scene record's Structure meshes: a deck, a stepped floor), found by a ray down from CLIMB over the eye height
above the ground there. An edge between two eyes is valid only when a ray along it, and four more offset by the
clearance radius (left, right, up, down), meet nothing before its end: no object, Structure or Fixtures mesh and no
ground in between. The tree is grown by RRT* (Karaman and Frazzoli, 2011: each new point joined to the cheapest valid
parent near it, then the near points rewired through it when that is shorter), seeded, so the same place and seed
give the same path. The path found is cut short wherever a straight valid edge skips points, then laid out evenly as
`--frames` views, each aimed LOOK_AHEAD metres further along it.

The output is a JSON list of views in the review walk's format (tools/review/renders.py: name `walk-NNN`, eye, aim,
up, fov, look_only), which renders.render_stage and walk_video take as they take the walk renders.py makes;
renders.py itself does not read it. The bounds default to the extent of the place's objects and Structure and
Fixtures meshes.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "review"))
import collide  # noqa: E402
import renders  # noqa: E402
import snap  # noqa: E402

# A standing eye over the floor (renders.py's walk inside a room), and how far over it a ray down for the floor starts.
EYE_HEIGHT = renders.STANDING
CLIMB = 0.5
# How far round an edge's line it must be clear (metres), checked by four rays offset that far.
CLEARANCE = 0.25
# RRT*: how many points are tried, how far a new point reaches from the nearest, how near another point must be to
# be weighed as its parent or rewired through it, and how often the goal itself is tried.
ITERATIONS = 900
STEP = 0.8
NEAR = 1.8
GOAL_BIAS = 0.1
# Where each frame looks: this far further along the path, at eye height.
LOOK_AHEAD = 2.0
FOV = 75.0


def place_scenes(stage_path):
    """A place for the camera: a collide.Scene of everything an edge must not cross, one of the floors (the ground and
    the Structure meshes), the ground's height under any (x, z), and the place's extent (x, z) without the ground."""
    laid = snap.read_place(stage_path)
    blocking, floors = collide.Scene(), collide.Scene()
    shown = {**laid["objects"], **laid["statics"]}
    for name, mesh in {**shown, "Ground": laid["ground"]}.items():
        blocking.add(name, name, mesh.vertices, mesh.faces, np.eye(4))
    for name, mesh in laid["statics"].items():
        if name.startswith(f"/{laid['place']}/Structure"):
            floors.add(name, name, mesh.vertices, mesh.faces, np.eye(4))
    floors.add("Ground", "Ground", laid["ground"].vertices, laid["ground"].faces, np.eye(4))
    corners = np.vstack([mesh.bounds for mesh in shown.values()]) if shown else np.zeros((2, 3))
    extent = (corners[:, 0].min(), corners[:, 2].min(), corners[:, 0].max(), corners[:, 2].max())
    return {"blocking": blocking, "floors": floors, "height": laid["height"], "extent": extent}


def eyes_over(scenes, flat, eye):
    """The eye over the floor under each (x, z): (count, 3) points, the height -inf where no floor is under it."""
    flat = np.atleast_2d(np.asarray(flat, dtype=float))
    start = np.nan_to_num(np.asarray(scenes["height"](flat), dtype=float), nan=0.0) + eye + CLIMB
    origins = np.column_stack([flat[:, 0], start, flat[:, 1]])
    distances, _ = scenes["floors"].raycast(origins, np.tile(snap.DOWN, (len(origins), 1)))
    return np.column_stack([flat[:, 0], start - distances + eye, flat[:, 1]])


def edges_clear(blocking, starts, ends, clearance):
    """Whether each edge (start to end) is clear: its own ray and four offset by the clearance meet nothing before
    its end."""
    starts, ends = np.atleast_2d(starts), np.atleast_2d(ends)
    spans = ends - starts
    lengths = np.linalg.norm(spans, axis=1)
    ways = spans / np.maximum(lengths, 1e-9)[:, None]
    sides = np.cross(ways, [0.0, 1.0, 0.0])
    sides /= np.maximum(np.linalg.norm(sides, axis=1), 1e-9)[:, None]
    ups = np.cross(sides, ways)
    offsets = [np.zeros_like(sides), sides * clearance, -sides * clearance, ups * clearance, -ups * clearance]
    origins = np.vstack([starts + offset for offset in offsets])
    distances, _ = blocking.raycast(origins, np.tile(ways, (len(offsets), 1)))
    return np.all(distances.reshape(len(offsets), -1) > lengths, axis=0)


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
        new = eyes_over(scenes, flat[nearest] + reach * min(1.0, STEP / length), eye)[0]
        if not np.isfinite(new[1]):
            continue
        near = [int(index) for index in np.flatnonzero(np.linalg.norm(flat - new[[0, 2]], axis=1) <= NEAR)]
        near = near if nearest in near else near + [nearest]
        clear = edges_clear(scenes["blocking"], np.array(points)[near], np.tile(new, (len(near), 1)), clearance)
        if not clear.any():
            continue
        through = [costs[node] + float(np.linalg.norm(points[node] - new)) if free else np.inf
                   for node, free in zip(near, clear)]
        points.append(new)
        parents.append(near[int(np.argmin(through))])
        costs.append(float(min(through)))
        rewire(points, parents, costs, len(points) - 1, near, clear)
    return path_to_goal(scenes, points, parents, costs, goal, clearance)


def path_to_goal(scenes, points, parents, costs, goal, clearance):
    """The cheapest path from the start through a point that reaches the goal by a clear edge no longer than STEP,
    or None."""
    flat = np.array(points)
    close = np.flatnonzero(np.linalg.norm(flat - goal, axis=1) <= STEP)
    if len(close) == 0:
        return None
    clear = edges_clear(scenes["blocking"], flat[close], np.tile(goal, (len(close), 1)), clearance)
    if not clear.any():
        return None
    ends = close[clear]
    node = int(ends[np.argmin([costs[index] + np.linalg.norm(points[index] - goal) for index in ends])])
    path = [goal]
    while node != -1:
        path.append(points[node])
        node = parents[node]
    return path[::-1]


def shortcut(blocking, path, clearance):
    """The path with every run of points a clear straight edge can skip cut out, from the start on."""
    kept, index = [path[0]], 0
    while index < len(path) - 1:
        reachable = edges_clear(blocking, np.tile(path[index], (len(path) - index - 1, 1)),
                                np.array(path[index + 1:]), clearance)
        index += int(np.flatnonzero(reachable).max()) + 1 if reachable.any() else 1
        kept.append(path[index])
    return kept


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
        found = rrt_star(scenes, start, goal, bounds or scenes["extent"], seed + number, eye, clearance)
        if found is None:
            raise ValueError(f"no clear path found from {start[[0, 2]]} to {goal[[0, 2]]}")
        path += shortcut(scenes["blocking"], found, clearance)[1:]
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
