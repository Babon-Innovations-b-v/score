"""The turn the finish stands a Pixal3D model up by (pixal.py stand_and_pad): glb_file.upright_turn, except a default
stand of a shape its tightest box would tip, which keeps the picture's up and is only squared (glb_file.squared).
tools/props/library/labels.py finish_turn replays it."""
import numpy as np
import trimesh

import glb_file

# The default stand trusts the tightest box's upright side unless the shape fills under BOX_FILL of that box and the
# side is over NEAR_UP_DEGREES off the picture's up; such a shape keeps the picture's up (2026-11-08: workshop's lamp,
# tilt 37.7, fill 0.35, was tipped by its angled box, outline 0.706 -> 0.255, galley's utensils 41.7, 0.47, 0.524 ->
# 0.296, and their retakes again). Measured on 79 takes over 25 places: no passing take is caught, the nearest a low
# fill rocket rear at 28.8 degrees and a palm tree at fill 0.52.
BOX_FILL = 0.5
NEAR_UP_DEGREES = 33.0


def kept_up(points):
    """Whether the default stand keeps the picture's up (only squared, as upright_turn ends) instead of the box side
    nearest up: a shape that fills under BOX_FILL of its tightest box, whose side nearest up is over NEAR_UP_DEGREES
    off the picture's up."""
    sides = glb_file.box_sides(points)
    side = sides[np.argmax(np.abs(sides[:, 1]))]
    tilt = np.degrees(np.arccos(np.clip(abs(side[1]) / np.linalg.norm(side), 0.0, 1.0)))
    _, extents = trimesh.bounds.oriented_bounds(points)
    fill = trimesh.convex.convex_hull(points).volume / float(np.prod(extents))
    return tilt > NEAR_UP_DEGREES and fill < BOX_FILL


def stood_turn(points, long, feet, tube, flat):
    """The turn the finish stands a model up by: glb_file.upright_turn, except a default stand of a shape `kept_up`
    holds, which keeps the picture's up and is only squared."""
    if not (long or feet or tube or flat) and kept_up(points):
        return glb_file.squared(points)
    return glb_file.upright_turn(points, long=long, feet=feet, tube=tube, flat=flat)
