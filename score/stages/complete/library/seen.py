"""Whether a film frame's camera sees a thing, not only frames it: the place's drawn geometry gathered into one
trimesh (score/stages/terrain/sight.py's triangles, each triangle's prim kept), rays cast from the camera's eye to
points on the thing.

    scene = seen.gathered(stage)
    seen.sees(scene, view, thing_path, box)     # True when a ray from the eye meets the thing first

A thing with triangles is seen when a ray to one of its triangles meets that thing first; one without (a light, a
sound source) when nothing stands between the eye and its box's middle. The place's neighbours are not in the scene:
a thing behind a neighbour's wall may pass as seen.
"""
import numpy as np
import trimesh
from pxr import Usd, UsdGeom

from score.stages.terrain import sight

TARGETS = 6  # the triangles of a thing a ray is aimed at
CLEAR = 0.3  # metres in front of a target a hit may stand and still count as the target


class Scene:
    """Everything drawn on a stage as one trimesh, with each triangle's prim path."""

    def __init__(self, mesh, prims, prim_of):
        self.mesh, self.prims, self.prim_of = mesh, prims, prim_of
        self.aimed = {}  # thing path: the points rays are aimed at


def triangles_of(prim, cache):
    if prim.IsA(UsdGeom.Mesh):
        return sight.mesh_triangles(prim, cache)
    if prim.IsA(UsdGeom.Sphere):
        return sight.sphere_triangles(prim, cache)
    return None


def gathered(stage):
    """Every drawn mesh and sphere of the stage a viewer sees as the environment (sight.is_seen), one Scene."""
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    parts, prims, prim_of = [], [], []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Gprim) or not sight.is_seen(prim, ()):
            continue
        made = triangles_of(prim, cache)
        if made is None or not len(made[1]):
            continue
        parts.append(made)
        prim_of.append(np.full(len(made[1]), len(prims)))
        prims.append(str(prim.GetPath()))
    if not parts:
        return Scene(None, [], np.zeros(0, dtype=int))
    points, triangles = sight.join(parts)
    return Scene(trimesh.Trimesh(points, triangles, process=False), prims, np.concatenate(prim_of))


def within(path, thing):
    return path == thing or path.startswith(thing + "/")


def targets(scene, thing):
    """Up to TARGETS middles of the thing's own triangles, spread through them (worked out once a thing)."""
    if thing not in scene.aimed:
        scene.aimed[thing] = aimed_at(scene, thing)
    return scene.aimed[thing]


def aimed_at(scene, thing):
    owners = [number for number, path in enumerate(scene.prims) if within(path, thing)]
    faces = np.flatnonzero(np.isin(scene.prim_of, owners)) if owners else np.zeros(0, dtype=int)
    if not len(faces):
        return np.zeros((0, 3))
    chosen = faces[np.linspace(0, len(faces) - 1, min(TARGETS, len(faces))).astype(int)]
    return scene.mesh.triangles_center[chosen]


def first_hits(scene, eye, points):
    """The first triangle each ray from the eye to a point meets, or -1."""
    ways = points - eye
    ways /= np.linalg.norm(ways, axis=1)[:, None]
    return scene.mesh.ray.intersects_first(np.repeat(eye[None], len(points), axis=0), ways)


def sees(scene, view, thing, box):
    """True when a ray from the view's eye meets the thing first."""
    if scene.mesh is None:
        return True
    eye = np.asarray(view["eye"], dtype=float)
    points = targets(scene, thing)
    if len(points):
        hits = first_hits(scene, eye, points)
        return any(hit >= 0 and within(scene.prims[scene.prim_of[hit]], thing) for hit in hits)
    middle = (np.asarray(box[0], dtype=float) + np.asarray(box[1], dtype=float)) / 2
    distance = np.linalg.norm(middle - eye)
    found, _, _ = scene.mesh.ray.intersects_location([eye], [(middle - eye) / distance], multiple_hits=False)
    return not len(found) or np.linalg.norm(found[0] - eye) >= distance - CLEAR
