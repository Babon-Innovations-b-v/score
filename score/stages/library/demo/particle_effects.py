"""Particle effects: the garage's air leaving through its big door as it opens (data/effects/garage.json: the ice
specks and the veil of mist), seen from the side. Each line is one particle's flight from `tools/usd/effects.py`
`flight` (Godot's particle steps, the record's own seed), sampled; the slider flies them again with the same code at
other spreads."""
import json
import sys

import numpy as np

ALGORITHM = "particle_effects"
PLACE = "garage"
EMITTERS = {"door_vent": "c1", "door_vent_veil": "c2"}
SHOWN = 30  # particles drawn an emitter
SPREADS = (10.0, 25.0, 40.0)  # the slider, degrees either side; the record's is 25


def effects_module(repo):
    sys.path.insert(0, str(repo / "tools/usd"))
    import effects
    return effects


def side_point(origin, spot):
    """(metres along the place's z, height) of a spot in the emitter's frame (an emitter on Places is unturned)."""
    return [round(float(origin[2] + spot[2]), 2), round(float(origin[1] + spot[1]), 2)]


def above_ground(points):
    """A flight up to where it goes under the floor's level: the bake does not stop a particle there, the ground
    hides it."""
    under = next((rank for rank, point in enumerate(points) if point[1] < 0), len(points))
    return points[:max(under, 2)]


def flights(effects, entry, spread):
    """SHOWN particles' paths of one emitter at `spread`, as path shapes."""
    emitter = dict(entry, spread=spread)
    draws = np.random.default_rng([int(entry["seed"]), 0]).random((int(entry["count"]), effects.DRAWS))
    track, _ = effects.flight(emitter, draws, int(entry["seed"]))
    origin = entry["placement"]["offset"]
    every = max(1, track.shape[1] // SHOWN)
    steps = range(0, track.shape[0], 3)
    return [{"kind": "path", "points": above_ground([side_point(origin, track[step, particle]) for step in steps]),
             "tone": EMITTERS[entry["name"]], "label": f"{entry['name'].replace('_', ' ')}: one particle"}
            for particle in range(0, track.shape[1], every)][:SHOWN]


def made(inputs):
    effects = effects_module(inputs.repo)
    record = json.loads((inputs.repo / "data/effects" / f"{PLACE}.json").read_text())
    chosen = [entry for entry in record["effects"] if entry["name"] in EMITTERS]
    door = chosen[0]
    (x, y, z), (_, half_high, half_deep) = door["placement"]["offset"], door["emitter"]["extents"]
    at = SPREADS.index(float(door["spread"]))
    variants = [[shape for entry in chosen for shape in flights(effects, entry, spread)] for spread in SPREADS]
    points = [point for shapes in variants for shape in shapes for point in shape["points"]]
    reach, lowest = max(point[0] for point in points), min(point[1] for point in points)
    return {
        "example": "the garage's big door opening onto the Moon",
        "view": "side", "bounds": [z - 2, min(lowest, 0.0) - 0.3, reach + 2, y + half_high + 3],
        "axes": {"x": "metres out through the door", "y": "height, metres"},
        "steps": [
            {"label": "The floor and the door's seam the air leaves from",
             "shapes": [{"kind": "line", "points": [[z - 2, 0.0], [round(reach + 2, 1), 0.0]], "tone": "ground",
                         "label": "floor and ground"},
                        {"kind": "area", "points": [[z - half_deep, y - half_high], [z + half_deep, y - half_high],
                                                    [z + half_deep, y + half_high], [z - half_deep, y + half_high]],
                         "tone": "base", "label": "the seam, where the particles start"}]},
            {"label": "Each particle flies out at 16 to 30 m/s and falls under the Moon's pull",
             "shapes": variants[at]}],
        "slider": {"label": "spread", "unit": "degrees either side", "values": list(SPREADS), "at": at,
                   "shapes": variants},
        "numbers": [{"label": entry["name"].replace("_", " "), "value": entry["count"], "unit": "particles",
                     "tip": f"{entry['count']} particles, each living {entry['lifetime']} s; {SHOWN} drawn"}
                    for entry in chosen]}
