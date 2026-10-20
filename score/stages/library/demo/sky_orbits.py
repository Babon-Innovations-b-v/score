"""The sky over one Moon place: where `tools/usd/orbits.py` puts the Sun and Earth over one turn of the Moon, and the
game's star field (`builders.stars`) turned as the game turns it, seen from the place looking up (the middle is
straight up, the rim the horizon, north at the top). The slider moves the base minute."""
import json
import math
import sys

import numpy as np

ALGORITHM = "sky_orbits"
PLACE = "wreck"  # an outside Moon place whose stars the sky record turns on its seat
MOMENTS = 10  # the slider's minutes over one turn, beside the place's own


def sky_point(way):
    """A way in the place's frame on the sky chart: degrees from straight up, toward its compass bearing."""
    way = np.asarray(way, dtype=float) / np.linalg.norm(way)
    from_up = math.degrees(math.acos(max(-1.0, min(1.0, way[1]))))
    level = math.hypot(way[0], way[2]) or 1.0
    return [round(float(from_up * way[0] / level), 1), round(float(-from_up * way[2] / level), 1)]


def track(points):
    """A track cut where it dips well below the horizon, as path shapes' point lists."""
    pieces, piece = [], []
    for point in points:
        if math.hypot(*point) <= 100.0:
            piece.append(point)
        elif piece:
            pieces.append(piece)
            piece = []
    return [each for each in pieces + [piece] if len(each) > 1]


def moment(orbits, minute, frame, stars):
    """The stars above the horizon, the Sun and Earth at one minute."""
    turned = stars @ orbits.stars_turn(minute, frame).T
    shown = [sky_point(way) for way in turned if way[1] > 0.0]
    sun, earth = sky_point(orbits.sun_way(minute, frame)), sky_point(orbits.earth_way(minute, frame))
    return [{"kind": "dots", "points": shown, "r": 1.2, "tone": "ghost", "label": f"{len(shown)} stars above"},
            {"kind": "dots", "points": [sun], "r": 6, "tone": "accent", "label": "the Sun"},
            {"kind": "dots", "points": [earth], "r": 7, "tone": "c2", "label": "Earth"}]


def made(inputs):
    sys.path.insert(0, str(inputs.repo / "tools/usd"))
    import builders
    import effects
    import orbits
    entry = json.loads((inputs.repo / "data/definitions/sky.json").read_text())["moon"]["outdoor"]["environment"]["stars"]
    frame = effects.place_ground(PLACE).frame
    built = builders.stars(int(entry["count"]), int(entry["seed"]), float(entry["sky_distance"]),
                           float(entry["distance"]), float(entry["radius"]), float(entry["size"][0]),
                           float(entry["size"][1]), None)
    stars = built["points"].reshape(-1, 6, 3).mean(axis=1)  # each star drawn as an octahedron: its middle
    lap = 2.0 * math.pi / orbits.MOON_RATE / orbits.REAL_SECONDS_PER_MINUTE
    own = float(entry["turn"]["minute"])
    minutes = sorted({round(float(each), 2) for each in np.linspace(0.0, lap, MOMENTS, endpoint=False)} | {own})
    samples = np.linspace(0.0, lap, 240)
    horizon = [[round(90 * math.cos(angle), 1), round(90 * math.sin(angle), 1)]
               for angle in np.linspace(0.0, 2 * math.pi, 73)]
    return {
        "example": f"the sky over the {PLACE.replace('_', ' ')} on the Moon",
        "view": "plan", "bounds": [-100, -100, 100, 100],
        "steps": [
            {"label": "The sky from the place: the rim is the horizon, the middle straight up",
             "shapes": [{"kind": "line", "points": horizon, "tone": "ground", "label": "horizon"},
                        *[{"kind": "text", "points": [point], "tone": "ghost", "label": name} for name, point in
                          (("N", [0, 95]), ("E", [95, 0]), ("S", [0, -95]), ("W", [-95, 0]), ("up", [0, 0]))]]},
            {"label": "The Sun's way over one turn of the Moon",
             "shapes": [{"kind": "path", "points": piece, "tone": "accent", "label": "the Sun's way"}
                        for piece in track([sky_point(orbits.sun_way(minute, frame)) for minute in samples])]},
            {"label": "Earth's way: it hardly moves, the Moon keeps one face to it",
             "shapes": [{"kind": "path", "points": piece, "tone": "c2", "label": "Earth's way"}
                        for piece in track([sky_point(orbits.earth_way(minute, frame)) for minute in samples])]},
            {"label": f"The stars, Sun and Earth at the place's minute ({own:g})",
             "shapes": moment(orbits, own, frame, stars)}],
        "slider": {"label": "time", "unit": "game minutes", "values": minutes, "at": minutes.index(own),
                   "shapes": [moment(orbits, minute, frame, stars) for minute in minutes]},
        "numbers": [{"label": "one turn", "value": round(lap), "unit": "min",
                     "tip": "game minutes the stars take to wheel once round"},
                    {"label": "stars", "value": int(entry["count"]), "unit": "", "tip": "the game's star field"}]}
