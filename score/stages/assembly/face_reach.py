"""A thing laid against its holder's side that still touches nothing of it, pushed straight in along its face's `out`
until its own surface meets the holder's built surface (fitting.fitted, after fitting.touching): on_face stands its
back on the frontmost of the holder's surface across its span and height (front_face), which can be a lip the thing's
own back never comes near, and fitting.touching closes a gap of FACE_REACH at most.

assembly@base, 2026-11-12: ramp_front_left_1, a platform on legs at its two ends laid against its square module's
front, was stood on the toe of the module's own built ramp, a lip 0.1 to 0.3 m up reaching 3 m out of its face; the
platform's back legs stand beside that lip and its deck over the slope, 0.15 m from the module at the nearest, so it
hung free. Pushed in, it meets the module where the first of its points does.

    gap_in(own, surface, out)              metres the thing (`own`) moves along -`out` before it meets `surface`
    met(stage, path, on, surface, face, words)   (words, face) of a face thing pushed in to meet its holder
"""
import pathlib
import sys

import numpy as np

from score.stages.assembly import fitting

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# Points of each surface beside its vertices the sweep casts from: its sides between them, not only its corners.
SAMPLES = 20000
# How far over the holder's surface, metres, the thing is left once it meets it: touching, never in it.
CLEAR = 0.005


def gap_in(own, surface, out):
    """How far the thing (`own`, its world triangles) moves along -`out` (a unit vector) before any point of it meets
    the holder's `surface`, or any point of the holder meets it: the least ray of either sweep; inf where none
    meets."""
    out = np.asarray(out, float)
    least = np.inf
    for mesh, other, way in ((own, surface, -out), (surface, own, out)):
        points = np.vstack([np.asarray(mesh.vertices, float), mesh.sample(SAMPLES, seed=0)])
        hits, rays, _ = other.ray.intersects_location(points, np.tile(way, (len(points), 1)), multiple_hits=False)
        if len(rays):
            least = min(least, float(np.min(np.einsum("ij,j->i", hits - points[rays], way))))
    return least


def met(stage, path, on, surface, face, words):
    """(its `words`, face) of the face thing at `path` (its relation `on`) pushed in along -out by its gap to its
    holder's `surface` less CLEAR (gap_in), when it touches nothing of it within the resting check's TOLERANCE and
    that gap is within the holder's depth along out; its `face` ((the plane its back is on, hung)) then the plane it
    is pushed to, which the held gate measures it off. Both as they are when it touches, meets nothing or is out of
    that reach."""
    import resting
    import trimesh
    own = fitting.surface_mesh(stage, path)
    if own is None or surface is None or face is None:
        return words, face
    if float(np.min(trimesh.proximity.closest_point(surface, np.asarray(own.vertices, float))[1])) <= resting.TOLERANCE:
        return words, face
    axis, _, sign = fitting.face_axes(on)
    out = np.zeros(3)
    out[axis] = sign
    gap = gap_in(own, surface, out) - CLEAR
    depth = float(surface.bounds[1][axis] - surface.bounds[0][axis])
    if not fitting.MOVE_LEAST < gap <= depth:
        return words, face
    foot = fitting.foot_middle(*fitting.world_box(stage, path))
    fitting.moved_by(stage.GetPrimAtPath(path), foot, 1.0, foot - out * gap)
    return words + f"; pushed {gap:.2f} m in to meet its holder", (float(face[0] - sign * gap), face[1])
