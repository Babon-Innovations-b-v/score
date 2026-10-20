"""A planet's gravity and orbits: Earth and the Moon going round their shared middle as `tools/usd/orbits.centre_at`
puts them (the distance and the month made by their pulls, `PULL`, Kepler's third law), seen from above in the game's
one space, the pair's middle held still; the slider runs through one month."""
import math
import sys

import numpy as np

ALGORITHM = "planet_gravity"
TRACK = 72  # points round a month
MOMENTS = 13  # the slider's moments over a month


def plan_point(way):
    return [round(float(way[0]), 1), round(float(-way[2]), 1)]


def made(inputs):
    sys.path.insert(0, str(inputs.repo / "tools/usd"))
    import orbits
    month = 2 * math.pi / orbits.MOON_RATE / orbits.REAL_SECONDS_PER_MINUTE  # in base minutes

    def around(body, minute):
        """The body's middle from the pair's middle (the pair's own round about the Sun taken off)."""
        seconds = minute * orbits.REAL_SECONDS_PER_MINUTE
        return orbits.centre_at(body, minute) - orbits.round_point(orbits.SUN_TO_EARTH_M, orbits.PAIR_RATE * seconds)

    def at_moment(minute):
        earth, moon = around("earth", minute), around("moon", minute)
        return [{"kind": "line", "tone": "ghost", "id": "pull", "label": f"{np.linalg.norm(moon - earth):.0f} m apart",
                 "points": [plan_point(earth), plan_point(moon)]},
                {"kind": "dots", "points": [plan_point(earth)], "r": 90, "tone": "c1", "id": "earth", "label": "Earth"},
                {"kind": "dots", "points": [plan_point(moon)], "r": 40, "tone": "c2", "id": "moon", "label": "the Moon"}]

    minutes = [month * step / TRACK for step in range(TRACK + 1)]
    moments = [month * step / (MOMENTS - 1) for step in range(MOMENTS)]
    reach = orbits.MOON_OFF_MIDDLE_M * 1.25
    return {
        "example": "Earth and the Moon in the game's one space, the game's own scale",
        "view": "plan", "bounds": [round(-reach), round(-reach), round(reach), round(reach)],
        "steps": [
            {"label": "The pair's shared middle, where their pulls balance",
             "shapes": [{"kind": "dots", "points": [[0, 0]], "r": 20, "tone": "base", "label": "the shared middle"}]},
            {"label": f"Earth's small round about it, {orbits.EARTH_OFF_MIDDLE_M:.0f} m out",
             "shapes": [{"kind": "path", "tone": "c1", "label": "Earth's round",
                         "points": [plan_point(around("earth", minute)) for minute in minutes]}]},
            {"label": f"The Moon's round, {orbits.MOON_OFF_MIDDLE_M:.0f} m out, once every "
                      f"{month * orbits.REAL_SECONDS_PER_MINUTE:.0f} s",
             "shapes": [{"kind": "path", "tone": "c2", "label": "the Moon's round",
                         "points": [plan_point(around("moon", minute)) for minute in minutes]}]},
            {"label": "Both at one moment", "shapes": at_moment(0.0)}],
        "slider": {"label": "into the month", "unit": "base minutes", "values": [round(minute) for minute in moments],
                   "at": 0, "shapes": [at_moment(minute) for minute in moments]},
        "numbers": [
            {"label": "Moon's pull", "value": orbits.PULL["moon"], "unit": "m/s²", "tip": "at its face"},
            {"label": "Earth's pull", "value": orbits.PULL["earth"], "unit": "m/s²", "tip": "at its face"},
            {"label": "apart", "value": round(orbits.EARTH_TO_MOON_M), "unit": "m",
             "tip": "Earth to the Moon, from their pulls and the month (Kepler's third law), at the game's scale"},
            {"label": "month", "value": round(month * orbits.REAL_SECONDS_PER_MINUTE), "unit": "s",
             "tip": "one round of the Moon, in the game's seconds"}]}
