"""A planet's gravity and orbits: a moon and the world it goes round, each round their shared middle where their
pulls balance, from the environment concept's physics (score/review/setting.py: each body a real one of the
reference table, data/physics/bodies.json), seen from above with the pair's middle held still, each round drawn as a
circle at the pair's mean distance; the slider runs through one of its months."""
import math

import numpy as np

from score.review import setting as settings
from score.stages.library.demos import NoExample

ALGORITHM = "planet_gravity"
TRACK = 72  # points round a month
MOMENTS = 13  # the slider's moments over a month


def plan_point(way):
    return [round(float(way[0]), 1), round(float(way[1]), 1)]


def pair_of(setting):
    """(moon, world) of the setting: the first body going round a body that itself goes round another; NoExample
    with none."""
    bodies = {body["body"]: body for body in setting["bodies"]}
    for body in bodies.values():
        world = bodies.get(body.get("around"))
        if world is not None and world.get("around"):
            return body, world
    raise NoExample("no physics for a moon: the environment concept's setting holds no body going round a world")


def made(inputs):
    moon, world = pair_of(settings.now())
    apart = moon["distance_km"]
    moon_out = apart * world["mass_kg"] / (world["mass_kg"] + moon["mass_kg"])
    world_out = apart - moon_out
    month = moon["period_days"]

    def around(out, day, opposite):
        angle = 2 * math.pi * day / month + (math.pi if opposite else 0.0)
        return np.array([out * math.cos(angle), out * math.sin(angle)])

    def at_moment(day):
        near, far = around(world_out, day, True), around(moon_out, day, False)
        return [{"kind": "line", "tone": "ghost", "id": "pull", "label": f"{np.linalg.norm(far - near):.0f} km apart",
                 "points": [plan_point(near), plan_point(far)]},
                {"kind": "dots", "points": [plan_point(near)], "r": world["radius_km"], "tone": "c1", "id": "world",
                 "label": world["name"]},
                {"kind": "dots", "points": [plan_point(far)], "r": moon["radius_km"], "tone": "c2", "id": "moon",
                 "label": moon["name"]}]

    days = [month * step / TRACK for step in range(TRACK + 1)]
    moments = [month * step / (MOMENTS - 1) for step in range(MOMENTS)]
    reach = moon_out * 1.25
    return {
        "example": f"{world['name']} and {moon['name']} of the environment concept's physics, at their true scale",
        "view": "plan", "bounds": [round(-reach), round(-reach), round(reach), round(reach)],
        "steps": [
            {"label": "The pair's shared middle, where their pulls balance",
             "shapes": [{"kind": "dots", "points": [[0, 0]], "r": world["radius_km"] / 4, "tone": "base",
                         "label": "the shared middle"}]},
            {"label": f"{world['name']}'s small round about it, {world_out:.0f} km out",
             "shapes": [{"kind": "path", "tone": "c1", "label": f"{world['name']}'s round",
                         "points": [plan_point(around(world_out, day, True)) for day in days]}]},
            {"label": f"{moon['name']}'s round, {moon_out:.0f} km out, once every {month:.1f} days",
             "shapes": [{"kind": "path", "tone": "c2", "label": f"{moon['name']}'s round",
                         "points": [plan_point(around(moon_out, day, False)) for day in days]}]},
            {"label": "Both at one moment", "shapes": at_moment(0.0)}],
        "slider": {"label": "into the month", "unit": "days", "values": [round(day, 1) for day in moments],
                   "at": 0, "shapes": [at_moment(day) for day in moments]},
        "numbers": [
            {"label": f"{moon['name']}'s pull", "value": moon["gravity"], "unit": "m/s²", "tip": "at its face"},
            {"label": f"{world['name']}'s pull", "value": world["gravity"], "unit": "m/s²", "tip": "at its face"},
            {"label": "apart", "value": round(apart), "unit": "km",
             "tip": f"{world['name']} to {moon['name']}, the reference table's mean distance"},
            {"label": "month", "value": round(month, 2), "unit": "days", "tip": f"one round of {moon['name']}"}]}
