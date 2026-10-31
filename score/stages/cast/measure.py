"""The cast's people measured against the place's geometry: what each stands on, and what each body runs into.

A person's body is a standing cylinder BODY_RADIUS wide from KNEE to HEAD over their feet (tools/characters/
cast_check.py's own sizes), tested against every triangle of the place's base layer (its objects, structure,
ground, water and the places it shows; not its sky, lights or old characters) with the collision library FCL
(trimesh's CollisionManager). What a person stands on is the first triangle a ray from their knee down meets.
Plain numbers out, so the gates judge them without opening the stage again.
"""
import pathlib
import sys

import numpy as np
import trimesh
from pxr import Usd, UsdGeom

REPO = pathlib.Path(__file__).resolve().parents[3]
CHARACTERS = REPO / "tools/characters"
# tools/characters/cast_check.py's body sizes (test_people_stand_clear_or_are_named.py checks they agree), metres.
BODY_RADIUS, KNEE, HEAD = 0.25, 0.3, 1.7
# A body's top by its clip where it is not a head's height (top_of).
TOPS = {"sitting": 1.0, "lying": None}
# Scopes that hold nothing a person stands on or walks into.
NOT_SOLID = ("Sky", "Lights", "Characters", "Sound", "Environment", "Library")
WATER = "Water"
# How far down from the knee a ray looks for what a person stands on, metres.
LOOK_DOWN = 3.0
# A walk's body is tested every this many metres along it.
WALK_STEP = 0.25
# A person's two feet and their stance lie inside their body's footprint (BODY_RADIUS round their middle, turned any
# way), tested at its middle and RIM points round its edge; the ground under it is even when none of them lies more
# than FOOT_STEP off one plane through them (a deck's 5.8 cm edge lies 2.2 cm or more off it wherever it crosses the
# footprint: camp's astronauts sank into it in sim-body, round 33).
RIM = 12
FOOT_STEP = 0.01


def characters():
    """tools/characters' cast and cast_check modules, imported only when a cast is made or judged: once imported (or
    their folder on the path), the `import cast_check` of tools/usd/reach.py resolves and joins the assembly's code
    version, which would move every place's assembly key. The stage declares both files as inputs instead."""
    if str(CHARACTERS) not in sys.path:
        sys.path.insert(0, str(CHARACTERS))
    import cast
    import cast_check
    return cast, cast_check


def triangles(prim, cache):
    """A mesh prim's triangles in world metres, (n, 3, 3); its faces fanned."""
    mesh = UsdGeom.Mesh(prim)
    points = np.asarray(mesh.GetPointsAttr().Get() or [], dtype=float)
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get() or [], dtype=int)
    indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get() or [], dtype=int)
    if not len(points) or not len(counts):
        return np.zeros((0, 3, 3))
    matrix = np.asarray(cache.GetLocalToWorldTransform(prim))
    world = points @ matrix[:3, :3] + matrix[3, :3]
    starts = np.concatenate(([0], np.cumsum(counts)[:-1]))
    fans = [(starts[counts >= step + 2], step) for step in range(1, int(counts.max()) - 1)]
    corners = [np.stack((indices[first], indices[first + step], indices[first + step + 1]), axis=1)
               for first, step in fans]
    return world[np.concatenate(corners)] if corners else np.zeros((0, 3, 3))


def solids(base, place, ground=None):
    """{prim path under the place: its triangles} of every visible mesh of the base layer, on its made ground (the
    terrain row's layer, `ground`, held in the session as the assembly sublayers it) where it has one, that is solid,
    grouped by the place's scopes' children (`Objects/desk_1`); the water's apart under `Water`."""
    stage = Usd.Stage.Open(str(base))
    if ground:
        stage.GetSessionLayer().subLayerPaths.append(str(ground))
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    found = {}
    for scope in stage.GetPrimAtPath(f"/{place}").GetChildren():
        if scope.GetName() in NOT_SOLID:
            continue
        for holder in scope.GetChildren() or [scope]:
            parts = [part for part in map(lambda prim: triangles(prim, cache), meshes(holder)) if len(part)]
            if parts:
                found[f"{scope.GetName()}/{holder.GetName()}"] = np.concatenate(parts)
    return found


def meshes(holder):
    """Every drawn mesh under a prim: a point instancer's prototypes left out (they stand only where it copies them,
    far off: shortcut: the copies themselves are not tested, which only the far city's towers are today; test them
    once a crowd stands among instanced things), and a guide or proxy mesh too (export.py's collision is a convex
    hull round each model, a guide never drawn: a ring's hull is a solid disc across the tube's walkway)."""
    walk = iter(Usd.PrimRange(holder, Usd.TraverseInstanceProxies()))
    for prim in walk:
        if prim.IsA(UsdGeom.PointInstancer):
            walk.PruneChildren()
        elif (prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility() != UsdGeom.Tokens.invisible
              and UsdGeom.Imageable(prim).ComputePurpose() not in (UsdGeom.Tokens.guide, UsdGeom.Tokens.proxy)):
            yield prim


def mesh_of(tris):
    return trimesh.Trimesh(vertices=tris.reshape(-1, 3), faces=np.arange(len(tris) * 3).reshape(-1, 3), process=False)


def ground_under(spots, found):
    """For each spot (x, feet, z): the gap from the feet down to the first solid a ray from the knee meets (metres;
    negative when the feet are under it, None when nothing is within LOOK_DOWN), what it is, and whether water is
    over it there."""
    ground = {name: tris for name, tris in found.items() if not name.startswith(WATER)}
    if not ground:  # a base layer with no solid (an earth seed whose plan lays no shell): nobody stands on anything
        return [{"gap": None, "on": None, "water": False} for _ in spots]
    names = np.repeat(np.arange(len(ground)), [len(tris) for tris in ground.values()])
    mesh = mesh_of(np.concatenate(list(ground.values())))
    spots = np.asarray(spots, dtype=float)
    origins = spots + [0.0, KNEE, 0.0]
    downs = np.tile([0.0, -1.0, 0.0], (len(spots), 1))
    hits, rays, faces = mesh.ray.intersects_location(origins, downs, multiple_hits=False)
    water = [tris for name, tris in found.items() if name.startswith(WATER)]
    wet = set(mesh_of(np.concatenate(water)).ray.intersects_location(origins, downs, multiple_hits=False)[1].tolist()
              if water else [])
    under = [None] * len(spots)
    keys = list(ground)
    for hit, ray, face in zip(hits, rays, faces):
        if spots[ray][1] - hit[1] <= LOOK_DOWN:
            under[ray] = {"gap": round(float(spots[ray][1] - hit[1]), 4), "on": keys[names[face]]}
    return [dict(stand or {"gap": None, "on": None}, water=ray in wet) for ray, stand in enumerate(under)]


def level_under(spots, found):
    """For each spot (x, feet, z): whether the ground under its whole footprint (its middle and RIM points round it,
    BODY_RADIUS out) is solid and lies within FOOT_STEP of one plane through it: a slope is (wreck's made ground, a
    third as steep as it is long under a foot), a step's edge is not."""
    turns = np.linspace(0.0, 2 * np.pi, RIM, endpoint=False)
    ring = np.stack((BODY_RADIUS * np.cos(turns), np.zeros(RIM), BODY_RADIUS * np.sin(turns)), axis=1)
    offsets = np.vstack(([0.0, 0.0, 0.0], ring))
    points = (np.asarray(spots, dtype=float)[:, None, :] + offsets).reshape(-1, 3)
    gaps = np.array([np.nan if ground["gap"] is None else ground["gap"] for ground in ground_under(points, found)])
    plane = np.column_stack((offsets[:, [0, 2]], np.ones(RIM + 1)))
    off_plane = gaps.reshape(-1, RIM + 1) @ (np.eye(RIM + 1) - plane @ np.linalg.pinv(plane)).T
    return [bool(np.all(np.abs(row) <= FOOT_STEP)) for row in off_plane]  # a nan (nothing under) is never level


def body(top):
    """One person's body: a cylinder from knee to `top` over feet at the origin."""
    return trimesh.creation.cylinder(radius=BODY_RADIUS, segment=[[0.0, KNEE, 0.0], [0.0, top, 0.0]], sections=16)


def top_of(doing):
    """How high a body reaches doing a clip, metres: a head's height, a seated one's on the ground (the clips'
    sitting has the knees drawn up), or None for one lying, whose body lies along the ground in a way this
    upright body does not stand for."""
    return TOPS.get(doing, HEAD)


def run_into(spots, found, tops=None):
    """For each spot (x, feet, z): the solids its body (to its top, HEAD by default) runs into, by name; None for a
    body whose top is None (not measured)."""
    manager = trimesh.collision.CollisionManager()
    for name, tris in found.items():
        manager.add_object(name, mesh_of(tris))
    shapes = {}
    clashes = []
    for (x, feet, z), top in zip(spots, tops or [HEAD] * len(spots)):
        if top is None:
            clashes.append(None)
            continue
        matrix = trimesh.transformations.translation_matrix([x, feet, z])
        person = shapes.setdefault(top, body(top))
        hit, names = manager.in_collision_single(person, transform=matrix, return_names=True)
        clashes.append(sorted(names) if hit else [])
    return clashes


def walk_spots(path):
    """Spots every WALK_STEP metres along a walk's points."""
    spots = []
    for start, end in zip(path, path[1:]):
        steps = max(1, int(np.ceil(np.linalg.norm(np.subtract(end, start)) / WALK_STEP)))
        spots += [list(np.add(start, np.subtract(end, start) * step / steps)) for step in range(steps)]
    return spots + [list(path[-1])]
