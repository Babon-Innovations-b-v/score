"""A vault standing behind a place's walls, read as no roof over them and no wall in their holes (fitting.through_roof
calls roof_over, fitting.fitted wall_holes).

    roof_over(points, triangles)        [n] the height of the roof face over each point a thing would pass up through
    wall_holes(built, walls, on, band)  the holes cut through a wall's face, read on its walls, not the vault behind

Tube's vault (roof_1) springs from its walls' room faces at the floor and bulges out behind them, 1.96 m from its
middle at 1.2 m up, over the walls' 1.53 m: over a spot just behind a wall's face the vault has two faces, its foot a
few centimetres up and its arc 2.46 m up. The lowest of them (fitting.roof_under) read the screens, panels, sign board
and pipe bundles laid flat on the walls as passing 0.5 to 2 m up through the vault where their backs touch the wall,
so fitting.moved_in stood each 5 cm into the room, touching nothing; and the rays fitting.wall_holes casts through
its walls' 2 m window holes met the vault 0.42 m behind them, so its screens and panels were hung over the holes
(settle@tube, 2026-11-12).
"""
import numpy as np


def heights(points, triangles):
    """[n, m] the height of each of the `triangles` [m, 3, 3] over each point's [n, 3] spot on the floor (x, z), NaN
    where a triangle is not over it; a standing face lies over no spot."""
    corner, first, second = triangles[:, 0], triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    to = points[:, None, :] - corner[None, :, :]
    both = first[:, 0] * second[:, 2] - first[:, 2] * second[:, 0]
    level = np.abs(both) > 1e-12
    both = np.where(level, both, 1.0)
    along = (to[..., 0] * second[None, :, 2] - to[..., 2] * second[None, :, 0]) / both
    across = (first[None, :, 0] * to[..., 2] - first[None, :, 2] * to[..., 0]) / both
    over = level & (along >= 0) & (across >= 0) & (along + across <= 1)
    return np.where(over, corner[None, :, 1] + along * first[None, :, 1] + across * second[None, :, 1], np.nan)


def roof_over(points, triangles):
    """[n] the height of the lowest roof face (`triangles` [m, 3, 3]) over each of a thing's surface points [n, 3]
    that the thing could pass up through, NaN where none is: a face lower than the thing's lowest point is left out
    where another face of the roof stands over the same spot at or above it (the vault's foot under its arc); a face
    lower than the thing with none over it so still counts (a dome's side the thing reaches out over)."""
    found = heights(np.asarray(points, float), np.asarray(triangles, float))
    if not found.size:
        return np.full(len(points), np.nan)
    foot = float(np.asarray(points, float)[:, 1].min())
    arched = (np.where(np.isfinite(found), found, -np.inf) >= foot).any(axis=1)
    kept = np.where(arched[:, None] & (found < foot), np.nan, found)
    lowest = np.nanmin(np.where(np.isfinite(kept), kept, np.inf), axis=1)
    return np.where(np.isfinite(lowest), lowest, np.nan)


def wall_holes(built, walls, on, band):
    """fitting.wall_holes of a wall relation's face (`on`) within a height `band` read on the place's built walls
    without its roofs (`walls`, wall_clear.face_walls): a roof standing behind a hole is not the wall it is cut in;
    read on all its built structure (`built`, fitting.built_walls) where no wall stands on the face at all (one hole
    the face's whole length: a dome that is its own wall)."""
    from score.stages.assembly import fitting
    found = fitting.wall_holes(walls, on, band)
    start, run, _, length = fitting.wall_line(on)
    for hole in found:
        alongs = (np.asarray(hole, float)[:, [0, 2]] - start) @ run
        if alongs.min() <= 0.0 and alongs.max() >= length:
            return fitting.wall_holes(built, on, band)
    return found
