"""Sky dust, stars, haze and beams: the camp's sky as seen from its middle at eye height, a chart of bearing round
the horizon against height above it. The stars are `tools/usd/builders.py` `stars` from the camp's record (its seed
and count), the dust grains `tools/usd/scene.py` `dust_points` (on flat ground: the code's own way without a
ground), the mast's beam its record's column; the slider makes the star field again with the same code at other
counts."""
import json
import math
import sys

import numpy as np

ALGORITHM = "sky_dust_stars_haze"
PLACE = "camp"
EYE = 1.6  # metres over the place's middle the chart is seen from
STAR_COUNTS = (600, 1800, 3600)  # the slider; the record's is 1800
DUST_SHOWN = 1500


def tools(repo):
    sys.path.insert(0, str(repo / "tools/usd"))
    import builders
    import scene
    return builders, scene


def sky_point(spot):
    """[bearing from north clockwise, height above the horizon], degrees, of a spot seen from the eye."""
    x, y, z = (float(value) for value in spot)
    return [round(math.degrees(math.atan2(x, -z)) % 360, 2),
            round(math.degrees(math.atan2(y - EYE, math.hypot(x, z))), 2)]


def stars(builders, entry, count):
    """The star field at `count` stars: one dot a star above the horizon."""
    built = builders.stars(count, int(entry["seed"]), float(entry["sky_distance"]), float(entry["distance"]),
                           float(entry["radius"]), float(entry["size"][0]), float(entry["size"][1]), None)
    middles = np.asarray(built["points"]).reshape(-1, 6, 3).mean(axis=1)
    shown = [point for point in map(sky_point, middles) if point[1] > 0]
    return [{"kind": "dots", "points": shown, "r": 0.8, "tone": "accent", "label": f"stars: {len(shown)} above the "
             "horizon"}]


def made(inputs):
    builders, scene = tools(inputs.repo)
    environment = json.loads((inputs.repo / "data/scene" / f"{PLACE}.json").read_text())["environment"]
    dust, haze = environment["dust"], environment["haze"]
    grains = scene.dust_points(dust, None)
    grains = grains[:: max(1, len(grains) // DUST_SHOWN)]
    beams = [{"kind": "line", "tone": "made", "label": f"{beam['name'].replace('_', ' ')}: a column of light",
              "points": [sky_point(np.asarray(beam["foot"]) + np.asarray(beam["way"]) * float(reach))
                         for reach in (beam["low"], beam["high"])]} for beam in environment.get("beams", [])]
    star_sets = [stars(builders, environment["stars"], count) for count in STAR_COUNTS]
    at = STAR_COUNTS.index(int(environment["stars"]["count"]))
    return {
        "example": "the camp's sky, seen from its middle",
        "view": "side", "bounds": [0, -20, 360, 90],
        "axes": {"x": "bearing, degrees from north", "y": "height above the horizon, degrees"},
        "steps": [
            {"label": "The horizon, seen from eye height",
             "shapes": [{"kind": "line", "points": [[0, 0], [360, 0]], "tone": "ground", "label": "horizon"},
                        {"kind": "text", "points": [[180, 80]], "tone": "ghost",
                         "label": f"haze: air {haze['size'][0]:.0f} m across ({haze['shape']}), "
                                  f"density {haze['density']} a metre"}]},
            {"label": f"Dust grains hanging up to {dust['high']} m over the ground, {dust['side']:.0f} m round",
             "shapes": [{"kind": "dots", "points": [sky_point(grain) for grain in grains], "r": 0.5, "tone": "c1",
                         "label": f"dust: {DUST_SHOWN} of its {dust['count']} grains"}]},
            {"label": "The mast's beam of light standing into the sky", "shapes": beams},
            {"label": "Stars, from the game's seeded star field", "shapes": star_sets[at]}],
        "slider": {"label": "stars", "unit": "in the field", "values": list(STAR_COUNTS), "at": at,
                   "shapes": star_sets},
        "numbers": [{"label": "stars", "value": environment["stars"]["count"], "unit": "", "tip": "stars in the field"},
                    {"label": "dust", "value": dust["count"], "unit": "grains", "tip": "grains of the calm day's drift"}]}
