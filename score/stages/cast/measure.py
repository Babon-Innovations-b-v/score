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
# tools/characters/cast_check.py's body sizes (cast_test.py checks they agree), metres.
BODY_RADIUS, KNEE, HEAD = 0.25, 0.3, 1.7
# Scopes that hold nothing a person stands on or walks into.
NOT_SOLID = ("Sky", "Lights", "Characters", "Sound", "Environment", "Library")
WATER = "Water"
# How far down from the knee a ray looks for what a person stands on, metres.
LOOK_DOWN = 3.0
# A walk's body is tested every this many metres along it.
WALK_STEP = 0.25


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


def solids(base, place):
    """{prim path under the place: its triangles} of every visible mesh of the base layer that is solid, grouped by
    the place's scopes' children (`Objects/desk_1`); the water's apart under `Water`."""
    stage = Usd.Stage.Open(str(base))
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
    """Every visible mesh under a prim, a point instancer's prototypes left out (they stand only where it copies
    them, far off: shortcut: the copies themselves are not tested, which only the far city's towers are today;
    test them once a crowd stands among instanced things)."""
    walk = iter(Usd.PrimRange(holder, Usd.TraverseInstanceProxies()))
    for prim in walk:
        if prim.IsA(UsdGeom.PointInstancer):
            walk.PruneChildren()
        elif prim.IsA(UsdGeom.Mesh) and UsdGeom.Imageable(prim).ComputeVisibility() != UsdGeom.Tokens.invisible:
            yield prim


def mesh_of(tris):
    return trimesh.Trimesh(vertices=tris.reshape(-1, 3), faces=np.arange(len(tris) * 3).reshape(-1, 3), process=False)


def ground_under(spots, found):
    """For each spot (x, feet, z): the gap from the feet down to the first solid a ray from the knee meets (metres;
    negative when the feet are under it, None when nothing is within LOOK_DOWN), what it is, and whether water is
    over it there."""
    ground = {name: tris for name, tris in found.items() if not name.startswith(WATER)}
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


def body():
    """One person's body: a cylinder from knee to head over feet at the origin."""
    return trimesh.creation.cylinder(radius=BODY_RADIUS, segment=[[0.0, KNEE, 0.0], [0.0, HEAD, 0.0]], sections=16)


def run_into(spots, found):
    """For each spot (x, feet, z): the solids its body runs into, by name."""
    manager = trimesh.collision.CollisionManager()
    for name, tris in found.items():
        manager.add_object(name, mesh_of(tris))
    person = body()
    clashes = []
    for x, feet, z in spots:
        matrix = trimesh.transformations.translation_matrix([x, feet, z])
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
