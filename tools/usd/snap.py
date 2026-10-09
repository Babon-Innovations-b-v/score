"""Snap an object of a place into place instead of laying it by hand: straight down onto what is under it, along a way
until it meets a wall or a neighbour, or onto a free spot of a rectangle found by trying seeded spots.

    .venv/bin/python tools/usd/snap.py <stage.usda> <object> down [--write]
    .venv/bin/python tools/usd/snap.py <stage.usda> <object> to <x,z> [<x,z> ...] [--write]
    .venv/bin/python tools/usd/snap.py <stage.usda> <object> free <xmin,zmin,xmax,zmax> [--seed N] [--write]

The object is named as under `/<place>/Objects` (`crate_2`); the stage is read as composed, in its frame (metres, y
up). What it meets is the place's ground (`/<place>/Ground`, or y = 0 on a flat place), the other objects (not the
ones it carries: its child prims move with it), and the scene record's Structure and Fixtures meshes.

    down   drops the object straight down until its lowest point rests CLEARANCE over the first surface under its
           footprint (an object sunk a little into its support is lifted the same way).
    to     slides it along each horizontal way in turn (front to back, then side to side) until it stops CLEARANCE short
           of a wall or a neighbour; the ground is not in its way and its height is kept.
    free   tries seeded random spots in the rectangle, the object's middle on each, dropped as `down` does, and keeps
           the first that collides with nothing (collide.py) and passes the floor support rule (triage.py: four contacts
           and its weight inside them); its turn is kept.

Every move is a plain shift in the stage's frame. By default the proposed pose is printed as JSON (the shift, the new
matrix, and the spot as the layout would say it); with --write it is written into the place's layout
(data/inventory/<place>.json and data/kit/<place>.json) the way settle.py writes a settled pose: spot `x`, `z`, lift
`y` and a `rotation` quaternion in the piece's own seat frame. Export the stage again after, and run the resting check.

The idea of placing by snapping (dropping onto a support, sliding until contact, rejection sampling of free spots)
is ProcFunc's (Raistrick et al., arXiv 2604.26943, BSD-3-Clause), whose released code (v0.37.0, checked 2026-10-09)
does not include it; this is a small version on python-fcl and trimesh through collide.py.
"""
import argparse
import json
import pathlib
import re
import sys

import numpy as np
import trimesh
from pxr import Usd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import collide  # noqa: E402
import ground as grounds  # noqa: E402
import resting  # noqa: E402
import settle  # noqa: E402
import triage  # noqa: E402

# How far over its support, or short of what it slides against, a snapped object is left (metres): within the 1 cm
# a snap promises, and clear of the surface so the collision test does not count the contact.
CLEARANCE = 0.002
# How far behind each point a ray starts, so a point bedded a little into a surface still finds it.
RAY_BACK = resting.RAY_START
# How many points of the object's surface join its vertices in looking for what it meets.
SAMPLES = 4000
# How many spots `free` tries, and how high over the ground under a tried spot the object starts its drop.
TRIES = 200
START_LIFT = 0.05
# The flat place's ground: a square this far out each way at y = 0.
FLAT_REACH = 1000.0
DOWN = np.array([0.0, -1.0, 0.0])
# A list of numbers on the command line (x,z or xmin,zmin,xmax,zmax), which may start with a minus.
NUMBER_LIST = re.compile(r"-?[\d.]+(,-?[\d.]+)+")


def flat_ground():
    """The ground of a flat place: a wide square at y = 0."""
    corners = [[-FLAT_REACH, 0.0, -FLAT_REACH], [FLAT_REACH, 0.0, -FLAT_REACH], [FLAT_REACH, 0.0, FLAT_REACH],
               [-FLAT_REACH, 0.0, FLAT_REACH]]
    return trimesh.Trimesh(corners, [[0, 2, 1], [0, 3, 2]], process=False)


def read_place(stage_path):
    """A place's stage as the snap needs it: its name, every object's mesh and matrix in the stage's frame, the scene
    record's static meshes, the ground's mesh, and the ground's height under any (x, z)."""
    stage = Usd.Stage.Open(str(stage_path))
    place = stage.GetDefaultPrim().GetName()
    meshes, matrices = {}, {}
    for path, prim in resting.objects_of(stage, place).items():
        name = path.removeprefix(f"/{place}/Objects/")
        points, triangles = resting.in_stage(prim.GetChild("geo"))
        meshes[name] = trimesh.Trimesh(points, triangles, process=False)
        matrices[name] = settle.laid_matrix(stage, place, name)
    ground_prim = stage.GetPrimAtPath(f"/{place}/Ground")
    ground_mesh = trimesh.Trimesh(*resting.in_stage(ground_prim), process=False) if ground_prim.IsValid() \
        else flat_ground()
    return {"place": place, "objects": meshes, "matrices": matrices, "statics": triage.static_meshes(stage, place),
            "ground": ground_mesh, "height": resting.ground_height(stage, place)}


def obstacles_of(laid, name, with_ground=True):
    """Everything an object can meet: {name: mesh in the stage's frame}, leaving out the object and what it carries."""
    found = {other: mesh for other, mesh in laid["objects"].items()
             if other != name and not other.startswith(name + "/")}
    found.update(laid["statics"])
    if with_ground:
        found["Ground"] = laid["ground"]
    return found


class Obstacles:
    """What an object can meet, ready for rays: one collide.Scene and every obstacle's points."""

    def __init__(self, meshes):
        self.scene = collide.Scene()
        for name, mesh in meshes.items():
            self.scene.add(name, name, mesh.vertices, mesh.faces, np.eye(4))
        self.points = np.vstack([np.asarray(mesh.vertices) for mesh in meshes.values()]) if meshes \
            else np.zeros((0, 3))


def surface_points(mesh):
    """An object's vertices and a seeded sample of its surface."""
    if mesh.area <= 0:
        return np.asarray(mesh.vertices)
    return np.vstack([np.asarray(mesh.vertices), mesh.sample(SAMPLES, seed=0)])


def poking_points(points, mesh, way):
    """The obstacle points that lie in the object's path along the way: inside its outline seen along the way and
    not behind it."""
    own = surface_points(mesh)
    along_own, along = own @ way, points @ way
    across_own, across = own - np.outer(along_own, way), points - np.outer(along, way)
    inside = np.all((across >= across_own.min(axis=0) - 1e-9) & (across <= across_own.max(axis=0) + 1e-9), axis=1)
    return points[inside & (along >= along_own.min() - RAY_BACK)]


def free_run(mesh, obstacles, way):
    """How far the object can move along the way (a unit vector) before its surface meets an obstacle's: rays from
    its points forward into the obstacles, and from the obstacles' points in its path back into it (inf when nothing
    is in the way)."""
    if not obstacles.scene.objects:
        return np.inf
    own = surface_points(mesh)
    forward, _ = obstacles.scene.raycast(own - way * RAY_BACK, np.tile(way, (len(own), 1)))
    run = float(forward.min()) - RAY_BACK
    poking = poking_points(obstacles.points, mesh, way)
    if len(poking):
        hits, rays, _ = trimesh.ray.ray_triangle.RayMeshIntersector(mesh).intersects_location(
            poking + way * RAY_BACK, np.tile(-way, (len(poking), 1)), multiple_hits=False)
        if len(hits):
            run = min(run, float(np.linalg.norm(hits - (poking[rays] + way * RAY_BACK), axis=1).min()) - RAY_BACK)
    return run


def shifted(mesh, offset):
    """A copy of a mesh moved by the offset."""
    moved = mesh.copy()
    moved.apply_translation(offset)
    return moved


def drop_offset(mesh, obstacles):
    """The shift that drops a mesh straight down to rest CLEARANCE over the first surface under it."""
    run = free_run(mesh, obstacles, DOWN)
    if not np.isfinite(run):
        raise ValueError("nothing is under it to rest on")
    return DOWN * (run - CLEARANCE)


def snap_down(laid, name):
    """The shift that drops the object onto the first surface under its footprint."""
    return drop_offset(laid["objects"][name], Obstacles(obstacles_of(laid, name)))


def snap_to(laid, name, ways):
    """The shift that slides the object along each horizontal way (x, z) in turn until it stops CLEARANCE short of a
    wall or a neighbour."""
    obstacles = Obstacles(obstacles_of(laid, name, with_ground=False))
    mesh, total = laid["objects"][name], np.zeros(3)
    for across, along in ways:
        way = np.array([across, 0.0, along], dtype=float)
        way /= np.linalg.norm(way)
        run = free_run(shifted(mesh, total), obstacles, way)
        if not np.isfinite(run):
            raise ValueError(f"nothing along the way ({across}, {along}) to slide against")
        total = total + way * max(0.0, run - CLEARANCE)
    return total


def collides(scene, name, offset, mesh):
    """Whether the object, moved by the offset, meets any other object of the scene."""
    low, high = mesh.bounds + offset
    for other, (other_low, other_high) in scene.bounds.items():
        if other == name or np.any(other_low > high) or np.any(other_high < low):
            continue
        if scene.intersection_test(name, other, offset):
            return True
    return False


def supported(mesh, height, surfaces, statics):
    """Whether a mesh standing on the floor passes the floor support rule (triage.py: no real floating or tipping
    fault)."""
    entry = {"name": "snapped", "row_id": None, "model": None, "support": "floor", "mesh": mesh}
    found = triage.standing(entry, height, surfaces, set(), statics)
    return not any(item["real"] for item in triage.held_up_faults(entry, found))


def place_free(laid, name, rectangle, seed=0, tries=TRIES):
    """The shift that puts the object on the first of seeded random spots in the rectangle (xmin, zmin, xmax, zmax)
    where, dropped onto what is under it, it collides with nothing and passes the floor support rule."""
    mesh = laid["objects"][name]
    meshes = obstacles_of(laid, name)
    obstacles = Obstacles(meshes)
    scene = collide.Scene()  # the obstacles' ray scene must not hold the object itself
    for other, other_mesh in {**meshes, name: mesh}.items():
        scene.add(other, other, other_mesh.vertices, other_mesh.faces, np.eye(4))
    surfaces = triage.Surfaces(meshes)
    statics = {number for number, other in enumerate(surfaces.names) if other not in laid["objects"]}
    random = np.random.default_rng(seed)
    low, high = np.asarray(rectangle[:2], dtype=float), np.asarray(rectangle[2:], dtype=float)
    middle = mesh.bounds.mean(axis=0)[[0, 2]]
    for _ in range(tries):
        spot = random.uniform(low, high)
        across, along = spot - middle
        corners = mesh.bounds[:, [0, 2]] + spot - middle
        under = np.nan_to_num(height_under(laid["height"], corners), nan=0.0)
        lift = float(under.max()) + START_LIFT - mesh.bounds[0][1]
        start = np.array([across, lift, along])
        try:
            offset = start + drop_offset(shifted(mesh, start), obstacles)
        except ValueError:
            continue
        if not collides(scene, name, offset, mesh) and supported(shifted(mesh, offset), laid["height"], surfaces,
                                                                 statics):
            return offset
    raise ValueError(f"no free spot found in {tries} tries")


def height_under(height, corners):
    """The ground's height under each corner of a footprint box ((low x, low z), (high x, high z))."""
    flat = np.array([[corners[0][0], corners[0][1]], [corners[1][0], corners[0][1]], [corners[0][0], corners[1][1]],
                     [corners[1][0], corners[1][1]]])
    return np.asarray(height(flat), dtype=float)


def moved_matrix(matrix, offset):
    """An object's matrix (column vectors) shifted by the offset in the stage's frame."""
    after = np.array(matrix, dtype=float)
    after[:3, 3] += offset
    return after


def proposed_pose(laid, name, offset, ground):
    """The pose a shift gives the object: the shift, its new matrix, and its spot as the layout says it."""
    after = moved_matrix(laid["matrices"][name], offset)
    scale = float(np.cbrt(abs(np.linalg.det(after[:3, :3]))))
    across, along, lift, turn = settle.layout_pose(after, ground, scale)
    return {"object": name, "offset": [round(float(value), 4) for value in offset],
            "matrix": np.round(after, 6).tolist(), "spot": settle.settled_spot({}, across, along, lift, turn)}


def write_pose(name, after, ground, inventory_path, kit_path):
    """An object's new matrix written into its inventory spot and its kit piece, as settle.py writes a settled pose
    (a stale `unrested` mark is dropped: the pose it judged is gone)."""
    if "/" in name:
        raise ValueError(f"{name} is a child: its pose is its parent's composite's, not the layout's")
    inventory = json.loads(pathlib.Path(inventory_path).read_text())
    kit = json.loads(pathlib.Path(kit_path).read_text())
    row, number = name.rsplit("_", 1)
    index = int(number) - 1
    spot = next(entry for entry in inventory["rows"] if entry["id"] == row)["at"]
    piece = [entry for entry in kit["pieces"] if entry["row"] == row][index]
    across, along, lift, turn = settle.layout_pose(after, ground, float(piece.get("scale", 1.0)))
    spot[index] = settle.settled_spot(spot[index], across, along, lift, turn)
    piece.update(settle.settled_spot(piece, across, along, lift, turn))
    for marked in (spot[index], piece):
        marked.pop("tilt", None)
        marked.pop("unrested", None)
    pathlib.Path(inventory_path).write_text(json.dumps(inventory, indent=1, ensure_ascii=False) + "\n")
    pathlib.Path(kit_path).write_text(json.dumps(kit, indent="\t", ensure_ascii=False) + "\n")


def numbers(text):
    """A comma-separated list of numbers."""
    return [float(value) for value in text.split(",")]


def with_negatives(arguments):
    """The command line with every list of numbers led by a space, so argparse never reads one that starts with a
    minus as an option."""
    return [" " + argument if NUMBER_LIST.fullmatch(argument) else argument for argument in arguments]


def offset_for(laid, options):
    """The shift the command line asks for."""
    if options.mode == "down":
        return snap_down(laid, options.object)
    if options.mode == "to":
        return snap_to(laid, options.object, [numbers(way) for way in options.values])
    return place_free(laid, options.object, numbers(options.values[0]), options.seed)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("object", help="the object's name under /<place>/Objects, e.g. crate_2")
    parser.add_argument("mode", choices=("down", "to", "free"))
    parser.add_argument("values", nargs="*", help="to: one or more ways x,z; free: xmin,zmin,xmax,zmax")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--write", action="store_true", help="write the pose into the place's layout")
    options = parser.parse_args(with_negatives(sys.argv[1:]))
    laid = read_place(options.stage)
    if options.object not in laid["objects"]:
        raise SystemExit(f"{options.object}: no such object in {options.stage}")
    kit_path, inventory_path = settle.KITS / f"{laid['place']}.json", settle.INVENTORIES / f"{laid['place']}.json"
    kit = json.loads(kit_path.read_text()) if kit_path.exists() else {}
    ground = grounds.place_ground(laid["place"], kit.get("on_seat", [0.0, 0.0])) if kit else None
    try:
        offset = offset_for(laid, options)
    except ValueError as problem:
        raise SystemExit(f"{options.object}: {problem}")
    pose = proposed_pose(laid, options.object, offset, ground)
    print(json.dumps(pose, indent=1))
    if options.write:
        write_pose(options.object, np.asarray(pose["matrix"]), ground, inventory_path, kit_path)
        print(f"written into {inventory_path} and {kit_path}; export the stage again")


if __name__ == "__main__":
    main()
