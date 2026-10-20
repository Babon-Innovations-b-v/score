"""Mars's day sky: `tools/usd/mars_sky.py` `picture` itself, for the camp's sky record and its sun (data/scene/
camp.json), the dome unrolled flat (across: the bearing all the way round; up: the height above the horizon). The
slider runs it again with the sun lower or higher on the same bearing; every picture is shown at the camp's own
brightness (its 98th percentile, as `write` saves it), so a low sun's sky is darker."""
import json
import math
import sys

import numpy as np

ALGORITHM = "mars_sky"
PLACE = "camp"
WIDTH = 96  # the picture's width here; its top half (the sky above the horizon) is shown
HEIGHTS = (5, 15, 30, 50, 70)  # the slider: the sun's height above the horizon, degrees


def sun_of(scene):
    """The place's sun way (where it shines toward), as write_sky_dome picks it."""
    return next(light for light in scene["lights"] if light.get("type") == "sun" and not light.get("name"))["toward"]


def raised(toward, degrees):
    """The same sun turned to stand `degrees` above the horizon on its own bearing (a `toward`)."""
    back = -np.asarray(toward, dtype=np.float64)
    flat = np.array([back[0], 0.0, back[2]]) / math.hypot(back[0], back[2])
    up = math.radians(degrees)
    return list(-(flat * math.cos(up) + np.array([0.0, 1.0, 0.0]) * math.sin(up)))


def sky_rows(sky, entry, toward, strength):
    """The sky above the horizon as rows of sRGB colours, top (overhead) first, at `strength`."""
    light = sky.picture(entry, toward, WIDTH)[: WIDTH // 4]
    shown = np.clip(sky.linear_to_srgb(light / strength), 0.0, 1.0)
    return [[[round(float(channel), 2) for channel in cell] for cell in row] for row in shown]


def sun_mark(toward):
    """The sun's place on the unrolled dome: [bearing, height] in degrees, as mars_sky.ways lays them."""
    back = -np.asarray(toward, dtype=np.float64)
    bearing = math.degrees(math.atan2(back[0], -back[2])) % 360.0
    return [round(bearing, 1), round(math.degrees(math.asin(back[1] / np.linalg.norm(back))), 1)]


def frame(sky, entry, toward, strength):
    return [{"kind": "raster", "points": [[0, 90], [360, 0]], "grid": sky_rows(sky, entry, toward, strength),
             "label": "the sky's colour each way"},
            {"kind": "text", "points": [sun_mark(toward)], "tone": "accent", "label": "sun"}]


def made(inputs):
    sys.path.insert(0, str(inputs.repo / "tools/usd"))
    import mars_sky as sky
    scene = json.loads((inputs.repo / "data/scene" / f"{PLACE}.json").read_text())
    entry, toward = scene["environment"]["sky_dome"], sun_of(scene)
    strength = float(np.percentile(sky.picture(entry, toward, WIDTH), 98.0))
    real = sun_mark(toward)[1]
    values = sorted({*HEIGHTS, round(real)})
    return {
        "example": f"the {PLACE}'s afternoon sky, the sun {real:.0f}° up",
        "view": "side", "bounds": [0, 0, 360, 90],
        "axes": {"x": "bearing round the dome, degrees", "y": "height above the horizon, degrees"},
        "steps": [{"label": "Dust scatters the sun's light: paler toward the horizon, brightest round the sun",
                   "shapes": frame(sky, entry, toward, strength)}],
        "slider": {"label": "sun height", "unit": "°", "values": values, "at": values.index(round(real)),
                   "shapes": [frame(sky, entry, toward if value == round(real) else raised(toward, value), strength)
                              for value in values]},
        "numbers": [{"label": "dust depth", "value": entry["depth"], "unit": "", "tip": "the dust layer's optical "
                     "depth, from the camp's sky record"},
                    {"label": "forward throw", "value": entry["forward"], "unit": "", "tip": "how much the dust "
                     "throws light forward, from the camp's sky record"}]}
