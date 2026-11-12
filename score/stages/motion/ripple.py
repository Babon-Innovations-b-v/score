"""The library's ripple (RECIPE, a motion recipe kept here in code: data/library is hashed whole by 44 paid rows, so a
file there re-keys them all): open water heaving in a few long-crested waves, written as
its sheet's own points keyed over time in the motion layer, so the film's renderer (Blender's OpenUSD import reads a
mesh whose points are keyed as a mesh sequence and plays it at each frame) shows the sea moving and its light moving
with it. The surface finish stays the ocean surface recipe's; the ripple only moves the sheet it is laid on.

Each wave is a deep-water wave: its period a whole share of the layer's seconds (so the layer loops), its length from
the period by deep water's dispersion on the body the place stands on (omega^2 = g k: 39 m for 5 s on the Earth), its
height (crest to trough) the recipe's, coming in toward the place (from the sheet's middle toward the place's own
origin) turned by the recipe's heading. A sheet carries a wave only where its edges are short enough to draw it: none
where its longest edge at a point is a quarter of the wave's length or more (`edges_least`), all of it where that edge
is an eighth or less (`edges_full`), a smooth step between; so the coarse far ground's water lies still rather than
showing a wave its triangles would break into noise.

    waves(settings, gravity, seconds, toward)         [{period, height, length, heading, number, omega, phase}]
    longest_edges(points, indices)                    each point's longest edge (metres)
    heights(points, edges, waves, second, settings)   each point's rise over its rest at one second
    keyed(points, edges, waves, seconds, rate, settings)  [(time code, points)] every `step` of the layer
    write(layer, path, keys, why)                     the keys into the layer as an over of the sheet's points
"""
import math

import numpy as np

LIBRARY = "score/stages/motion/ripple.py RECIPE"
NAME = "ripple"
# Each wave's `period` (seconds, a whole share of the layer's 20 s round, so it loops), `height` (crest to trough,
# metres) and `heading` (degrees from the way in toward the place); `edges_least` and `edges_full`, how many of a
# sheet's longest edges a wave's length must span to show at all and wholly; `step`, seconds between the layer's keys.
RECIPE = {
    "waves": [{"period": 5.0, "height": 0.2, "heading": 0.0}, {"period": 4.0, "height": 0.12, "heading": 35.0},
              {"period": 2.5, "height": 0.06, "heading": -40.0}],
    "edges_least": 4.0, "edges_full": 8.0, "step": 0.25,
    "sources": {
        "height": "WMO sea state code (WMO-No. 306, code table 3700): state 2, smooth (wavelets), 0.1 to 0.5 m; the "
                  "three waves' heights add to 0.38 m",
        "period": "whole shares of the layer's 20 s round (5, 4 and 2.5 s), a short-fetch wind sea's periods; chosen, "
                  "not read off a measured harbour spectrum",
        "length": "linear (Airy) deep-water dispersion, omega^2 = g k (Holthuijsen 2007, Waves in Oceanic and Coastal "
                  "Waters, ch. 5): 39 m for 5 s, 25 m for 4 s, 9.8 m for 2.5 s on the Earth; each wave's steepness "
                  "(height over length) about 0.005 to 0.006, far under breaking's 1/7"}}
# The golden turn: each wave's phase this share of a turn on from the last, so no two waves crest together at the start.
GOLDEN = (math.sqrt(5.0) - 1.0) / 2.0


def waves(settings, gravity, seconds, toward):
    """Each wave of the recipe on a body pulling `gravity` m/s/s over a layer of `seconds`, coming in along `toward`
    (an [x, z] way) turned by its own heading; a period that does not fit the layer a whole number of times refuses."""
    toward = np.asarray(toward, dtype=float)
    base = math.atan2(toward[1], toward[0]) if np.linalg.norm(toward) > 1e-9 else 0.0
    found = []
    for index, wave in enumerate(settings["waves"]):
        period = float(wave["period"])
        rounds = seconds / period
        if abs(rounds - round(rounds)) > 1e-6:
            raise ValueError(f"the ripple's {period:g} s wave fits the layer's {seconds:g} s {rounds:.3f} times")
        omega = 2.0 * math.pi / period
        number = omega * omega / float(gravity)
        heading = base + math.radians(float(wave["heading"]))
        found.append({"period": period, "height": float(wave["height"]), "length": round(2.0 * math.pi / number, 4),
                      "heading": round((math.degrees(heading) + 180.0) % 360.0 - 180.0, 4), "number": number,
                      "omega": omega, "phase": 2.0 * math.pi * ((index * GOLDEN) % 1.0)})
    return found


def longest_edges(points, indices):
    """Each point's longest edge among the triangles it is a corner of (metres); 0 for a point no triangle uses."""
    corners = np.asarray(indices, dtype=np.int64).reshape(-1, 3)
    points = np.asarray(points, dtype=float)
    lengths = np.linalg.norm(points[corners] - points[np.roll(corners, 1, axis=1)], axis=2).max(axis=1)
    found = np.zeros(len(points))
    np.maximum.at(found, corners.reshape(-1), np.repeat(lengths, 3))
    return found


def carried(edges, length, settings):
    """How much of a wave of `length` each point carries by its longest edge (module docstring): 1 where its edge is
    at most length / edges_full, 0 from length / edges_least, a smooth step between."""
    many = length / np.maximum(edges, 1e-9)
    share = np.clip((many - float(settings["edges_least"])) /
                    (float(settings["edges_full"]) - float(settings["edges_least"])), 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def heights(points, edges, waves_of, second, settings):
    """Each point's rise over its rest (metres) at one second: the sum of its waves, each as much as its edges carry."""
    points = np.asarray(points, dtype=float)
    rise = np.zeros(len(points))
    for wave in waves_of:
        way = np.radians(wave["heading"])
        along = points[:, 0] * math.cos(way) + points[:, 2] * math.sin(way)
        rise += carried(edges, wave["length"], settings) * wave["height"] / 2.0 * \
            np.sin(wave["number"] * along - wave["omega"] * second + wave["phase"])
    return rise


def keyed(points, edges, waves_of, seconds, rate, settings):
    """[(time code, points)] of the sheet every `step` seconds of the recipe from 0 to the layer's end, the last
    key the first again (the waves' periods fit the layer), each point risen over its rest."""
    step = float(settings["step"])
    count = int(round(seconds / step))
    points = np.asarray(points, dtype=float)
    found = []
    for index in range(count + 1):
        second = index * step
        moved = points.copy()
        moved[:, 1] += heights(points, edges, waves_of, second, settings)
        found.append((round(second * rate, 6), moved.astype(np.float32)))
    return found


def write(layer, path, keys, why):
    """The keyed points (keyed) written into the Sdf layer as an over of the sheet at `path`, its extent keyed with
    them, and where the move comes from (`score:motion:from`, `score:motion:recipe`)."""
    from pxr import Gf, Sdf, Vt
    spec = Sdf.CreatePrimInLayer(layer, path)
    points = Sdf.AttributeSpec(spec, "points", Sdf.ValueTypeNames.Point3fArray)
    extent = Sdf.AttributeSpec(spec, "extent", Sdf.ValueTypeNames.Float3Array)
    for code, moved in keys:
        layer.SetTimeSample(points.path, code, Vt.Vec3fArray.FromNumpy(moved))
        layer.SetTimeSample(extent.path, code, Vt.Vec3fArray([Gf.Vec3f(*moved.min(axis=0).tolist()),
                                                               Gf.Vec3f(*moved.max(axis=0).tolist())]))
    for name, value in (("score:motion:from", why), ("score:motion:recipe", f"{LIBRARY} {NAME}")):
        Sdf.AttributeSpec(spec, name, Sdf.ValueTypeNames.String, Sdf.VariabilityVarying, True).default = value
