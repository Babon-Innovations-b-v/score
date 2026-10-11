"""What can be seen from inside a place: its OpenUSD stage (with the places it references) gathered into one triangle
mesh, and rays cast from where a viewer stands to find where the view runs out into nothing.

A ray that meets nothing and points below the horizon is a void: a hole in the world where ground, water, a wall or a
neighbouring place should be (the flat's front door onto blue, the garage's big door onto brown). A ray that meets
nothing above the horizon is sky, which is drawn there. Rays within HORIZON_BAND of the horizon are not counted: the
sky's haze ring sits there. On a small world the horizon dips below level with the viewer's height, and the band is
taken under that dip.

    scene = sight.gathered(stage)                   # one trimesh of everything drawn, the sky and lights left out
    found = sight.voids(scene, probes, up, ball=(middle, radius))   # the void rays from each probe, and their share

Doors are judged open: every moving leaf (a motion record's sliding prim, a kit piece whose kind ends in `_leaf`) is
left out of the gathered mesh, so an opening is judged as it stands when the door is open.
"""
import numpy as np
import trimesh
from pxr import Usd, UsdGeom

# What is not a surface a viewer sees as the world: the sky and its haze ring, lights, effects' particles.
NOT_SEEN = ("Sky", "Lights", "Environment", "Effects", "Library")
# Rays within this many degrees of the horizon are not judged (the haze ring; a ball's ground falling away).
HORIZON_BAND = 1.0
# How many directions a probe casts, spread evenly over the whole sphere.
DIRECTIONS = 4096


def even_directions(count=DIRECTIONS):
    """`count` unit directions spread evenly over the sphere (a Fibonacci lattice), y up."""
    index = np.arange(count) + 0.5
    height = 1.0 - 2.0 * index / count
    around = np.pi * (1.0 + 5.0 ** 0.5) * index
    flat = np.sqrt(1.0 - height ** 2)
    return np.column_stack([flat * np.cos(around), height, flat * np.sin(around)])


def is_seen(prim, skipped):
    """Whether a geometry prim is drawn world: visible, a render or default purpose, under none of the left-out
    groups and not a moving leaf."""
    path = str(prim.GetPath())
    parts = path.strip("/").split("/")
    if any(part in NOT_SEEN for part in parts[1:3]):
        return False
    if any(path == leaf or path.startswith(leaf + "/") for leaf in skipped):
        return False
    imageable = UsdGeom.Imageable(prim)
    if imageable.ComputeVisibility() == UsdGeom.Tokens.invisible:
        return False
    return imageable.ComputePurpose() in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render)


def mesh_triangles(prim, cache):
    """A Mesh prim's triangles in the stage's frame (its faces fanned), or None when it has none."""
    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()
    counts = mesh.GetFaceVertexCountsAttr().Get()
    indices = mesh.GetFaceVertexIndicesAttr().Get()
    if not points or not counts or indices is None:
        return None
    points = np.asarray(points, dtype=np.float64)
    counts, indices = np.asarray(counts), np.asarray(indices)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    fans = [np.column_stack([np.full(count - 2, start), start + np.arange(1, count - 1), start + np.arange(2, count)])
            for start, count in zip(starts, counts) if count >= 3]
    if not fans:
        return None
    triangles = indices[np.concatenate(fans)]
    matrix = np.asarray(cache.GetLocalToWorldTransform(prim))
    return points @ matrix[:3, :3] + matrix[3, :3], triangles


def sphere_triangles(prim, cache):
    """A Sphere prim as an icosphere in the stage's frame."""
    radius = UsdGeom.Sphere(prim).GetRadiusAttr().Get()
    ball = trimesh.creation.icosphere(subdivisions=5, radius=radius)
    matrix = np.asarray(cache.GetLocalToWorldTransform(prim))
    return np.asarray(ball.vertices) @ matrix[:3, :3] + matrix[3, :3], np.asarray(ball.faces)


def box_triangles(low, high, matrix):
    """An axis box (low, high) in a prim's own frame, as triangles in the stage's frame."""
    box = trimesh.creation.box(bounds=[low, high])
    return np.asarray(box.vertices) @ matrix[:3, :3] + matrix[3, :3], np.asarray(box.faces)


def instancer_triangles(prim, cache):
    """A PointInstancer's copies, each as its prototype's box (a far city's towers): triangles in the stage's
    frame."""
    instancer = UsdGeom.PointInstancer(prim)
    transforms = instancer.ComputeInstanceTransformsAtTime(Usd.TimeCode.Default(), Usd.TimeCode.Default())
    indices = instancer.GetProtoIndicesAttr().Get()
    if transforms is None or indices is None:
        return None
    bounds = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    boxes = []
    for target in instancer.GetPrototypesRel().GetTargets():
        found = bounds.ComputeUntransformedBound(prim.GetStage().GetPrimAtPath(target)).ComputeAlignedRange()
        boxes.append((np.asarray(found.GetMin()), np.asarray(found.GetMax())))
    outer = np.asarray(cache.GetLocalToWorldTransform(prim))
    parts = [box_triangles(*boxes[index], np.asarray(matrix) @ outer) for matrix, index in zip(transforms, indices)
             if not np.isnan(boxes[index][0]).any() and np.all(boxes[index][1] > boxes[index][0])]
    return join(parts) if parts else None


def join(parts):
    """Many (points, triangles) as one."""
    offsets = np.cumsum([0] + [len(points) for points, _ in parts[:-1]])
    return (np.concatenate([points for points, _ in parts]),
            np.concatenate([triangles + offset for (_, triangles), offset in zip(parts, offsets)]))


def gathered(stage, skipped=()):
    """Everything drawn on the stage that a viewer sees as the world, as one trimesh in the stage's frame."""
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    parts = []
    instancers = []
    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)):
        if any(str(prim.GetPath()).startswith(str(path) + "/") for path in instancers):
            continue
        if not prim.IsA(UsdGeom.Gprim) and not prim.IsA(UsdGeom.PointInstancer):
            continue
        if not is_seen(prim, skipped):
            continue
        if prim.IsA(UsdGeom.PointInstancer):
            instancers.append(prim.GetPath())
            made = instancer_triangles(prim, cache)
        elif prim.IsA(UsdGeom.Mesh):
            made = mesh_triangles(prim, cache)
        elif prim.IsA(UsdGeom.Sphere):
            made = sphere_triangles(prim, cache)
        else:
            made = None
        if made is not None and len(made[1]):
            parts.append(made)
    points, triangles = join(parts)
    return trimesh.Trimesh(points, triangles, process=False)


def elevation(directions, up):
    """Each direction's angle above the horizon, in degrees, for a viewer whose up is `up`."""
    return np.degrees(np.arcsin(np.clip(directions @ (np.asarray(up) / np.linalg.norm(up)), -1.0, 1.0)))


def horizon(probe, up, ball):
    """A probe's up and how far (degrees) its horizon dips below level: on a world of radius r whose middle is at c,
    acos(r / |probe - c|) with its up away from the middle; level (0) on a flat world or without a ball."""
    if ball is None:
        return np.asarray(up, dtype=float) / np.linalg.norm(up), 0.0
    away = np.asarray(probe, dtype=float) - np.asarray(ball[0], dtype=float)
    out = float(np.linalg.norm(away))
    return away / out, float(np.degrees(np.arccos(min(1.0, ball[1] / out))))


def voids(scene, probes, up, directions=None, ball=None):
    """Cast every direction from every probe: {"rays": how many were judged (outside the horizon band), "void": how
    many below the horizon met nothing, "share": void / rays, "probes": [per probe: its spot and its void rays],
    "worst": the probe with most}. On a small world (`ball`: its middle and radius in the stage's frame) the horizon
    dips with a probe's height, and a ray between level and that dip sees sky past the horizon, as it should."""
    directions = even_directions() if directions is None else directions
    caster = trimesh.ray.ray_pyembree.RayMeshIntersector(scene) if trimesh.ray.has_embree else scene.ray
    per_probe, rays = [], 0
    for probe in np.atleast_2d(probes):
        local_up, dip = horizon(probe, up, ball)
        angle = elevation(directions, local_up)
        judged = (angle > HORIZON_BAND) | (angle < -(dip + HORIZON_BAND))
        below = angle < -(dip + HORIZON_BAND)
        origins = np.repeat(probe[None, :], len(directions), axis=0)
        hit = caster.intersects_any(origins, directions)
        missed = below & ~hit
        rays += int(judged.sum())
        per_probe.append({"at": np.round(probe, 2).tolist(), "void": int(missed.sum()),
                          "void_down_to": round(float(angle[missed].min()), 1) if missed.any() else None})
    void = sum(probe["void"] for probe in per_probe)
    worst = max(per_probe, key=lambda probe: probe["void"]) if per_probe else None
    return {"rays": rays, "void": void, "share": void / rays if rays else 0.0, "probes": per_probe, "worst": worst}
