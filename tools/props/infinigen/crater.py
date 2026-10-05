"""The crater's shape in numbers: a bowl inside the rim, a raised rim, its outer flank and an ejecta blanket, on a flat
patch or on a small round world. numpy only, so it is checked on this PC (crater_test.py); ground.py wraps it as an
Infinigen terrain element on the rented machine.

The profile is the Moon plan's own (the terrain job's plan.py, 2026-10-05), so the element builds what the plan drew:
inside the rim  rim - depth * (1 - (d/r)^2)^0.8      (a bowl, `depth` below the rim at the middle)
outside         rim * (1 - (d - r)/(r/2))^2           (the flank, back to the plain half a radius out)
ejecta          `ejecta_m` of blocky bumps, fading to nothing at `ejecta_reach` radii
"""
import numpy as np


def profile(distance, radius, depth_below_rim, rim_above_plain):
    """Height of a fresh crater above the plain at `distance` from its middle."""
    distance = np.asarray(distance, dtype=np.float64)
    bowl = rim_above_plain - depth_below_rim * np.clip(1 - (distance / radius) ** 2, 0, 1) ** 0.8
    flank = rim_above_plain * np.clip(1 - (distance - radius) / (radius * 0.5), 0, 1) ** 2
    return np.where(distance < radius, bowl, flank)


def ejecta_weight(distance, radius, reach):
    """How much of the ejecta's bumps show at `distance`: none inside the rim, all at it, none `reach` radii out."""
    distance = np.asarray(distance, dtype=np.float64)
    fade = np.clip(1 - (distance - radius) / ((reach - 1) * radius), 0, 1)
    return np.where(distance > radius, fade, 0.0)


def _lattice(cells, seed):
    """A repeatable value from -1 to 1 for each integer lattice point."""
    hashed = (cells[..., 0] * 73856093) ^ (cells[..., 1] * 19349663) ^ (seed * 83492791)
    return (hashed % 2003) / 1001.0 - 1.0


def lumps(xy, seed, sizes=(2.0, 0.9, 0.4)):
    """Smooth value noise over (x, y) metres, -1 to 1: lumps about `sizes` metres across, each octave half the
    last's height. The same point always gets the same value, wherever the mesher asks."""
    xy = np.asarray(xy, dtype=np.float64)
    total, weight = np.zeros(len(xy)), 0.0
    for octave, size in enumerate(sizes):
        scaled = xy / size
        corner = np.floor(scaled).astype(np.int64)
        fraction = scaled - corner
        ease = fraction * fraction * (3 - 2 * fraction)
        values = [_lattice(corner + offset, seed + octave) for offset in ((0, 0), (1, 0), (0, 1), (1, 1))]
        lower = values[0] * (1 - ease[:, 0]) + values[1] * ease[:, 0]
        upper = values[2] * (1 - ease[:, 0]) + values[3] * ease[:, 0]
        total += (lower * (1 - ease[:, 1]) + upper * ease[:, 1]) * 0.5 ** octave
        weight += 0.5 ** octave
    return total / weight


def surface_distance(points, centre, spherical_radius):
    """Distance along the ground from each point to a crater's middle: straight across a flat patch (x, y), or
    along the great circle on a round world of `spherical_radius` whose middle is the origin."""
    points = np.asarray(points, dtype=np.float64)
    if spherical_radius <= 0:
        return np.hypot(points[:, 0] - centre[0], points[:, 1] - centre[1])
    unit = points / np.maximum(np.linalg.norm(points, axis=1, keepdims=True), 1e-9)
    middle = np.asarray(centre, dtype=np.float64) / np.linalg.norm(centre)
    return spherical_radius * np.arccos(np.clip(unit @ middle, -1, 1))


def lift(points, craters, bumps, spherical_radius=-1.0):
    """Every crater's height at each point (summed), with `bumps` (one per point, about -1 to 1) as the ejecta's
    blocky ground. Craters on a round world name their middle as a point in space ("centre"), on a flat patch by
    "x" and "y" in the same metres as the points."""
    total = np.zeros(len(points))
    for crater in craters:
        centre = crater.get("centre", (crater.get("x", 0.0), crater.get("y", 0.0), 0.0))
        radius = crater["diameter"] / 2
        distance = surface_distance(points, centre, spherical_radius)
        total += profile(distance, radius, crater["depth_below_rim"], crater["rim_above_plain"])
        total += crater.get("ejecta_m", 0.0) * bumps * ejecta_weight(distance, radius, crater.get("ejecta_reach", 1.8))
    return total
