"""Light rig: the greenhouse's lamps where its light layer placed them (`layer/light.greenhouse` lamps.json), each
lamp's strength as a ring, and the sweep that scaled every lamp until the place was as bright as its concept
(measures.json: the views' brightness before and after, the scale it chose). The slider shows the two strengths the
record holds: the seed's and the swept one."""
import json
import math

ALGORITHM = "light_rig"
PLACE = "greenhouse"
RING_PER_ROOT = 0.25  # a ring's radius, metres, per square root of the lamp's strength: it shows strength, not reach
SIDES = 32


def plan_point(east, south):
    return [round(east, 2), round(-south, 2)]


def rect(low, high):
    (x0, z0), (x1, z1) = low, high
    return [plan_point(x0, z0), plan_point(x1, z0), plan_point(x1, z1), plan_point(x0, z1)]


def box_outline(item):
    (east, _, south), (wide, _, deep) = item["centre"], item["size"]
    return rect((east - wide / 2, south - deep / 2), (east + wide / 2, south + deep / 2))


def ring(spot, radius):
    return [plan_point(spot[0] + radius * math.cos(turn), spot[2] + radius * math.sin(turn))
            for turn in (step / SIDES * 2 * math.pi for step in range(SIDES + 1))]


def rings(lamps, scale):
    return [{"kind": "line", "points": ring(lamp["spot"], RING_PER_ROOT * math.sqrt(lamp["intensity"] * scale)),
             "tone": "accent", "label": f"{lamp['path'].rsplit('/', 1)[-1]}: strength {lamp['intensity'] * scale:.0f}"}
            for lamp in lamps]


def mean(values):
    return round(sum(values) / len(values), 3)


def made(inputs):
    held = inputs.json(f"layer/light.{PLACE}@1", "lamps.json")
    brightness = inputs.json(f"layer/light.{PLACE}@1", "measures.json")["brightness"]
    scene = json.loads((inputs.repo / "data/scene" / f"{PLACE}.json").read_text())
    lamps = [lamp for lamp in held["lamps"] if lamp.get("spot")]
    swept = brightness["swept_scale"]
    low, high = scene["floor"]
    beds = [item for item in scene["structure"] if item["name"].startswith("bed_")]
    return {
        "example": f"the {PLACE}'s {len(lamps)} lamps",
        "view": "plan", "bounds": [low[0] - 3, -high[1] - 3, high[0] + 3, -low[1] + 3],
        "steps": [
            {"label": "The room's floor, from its scene record",
             "shapes": [{"kind": "area", "points": rect(low, high), "tone": "ground", "label": "floor"},
                        *[{"kind": "area", "points": box_outline(bed), "tone": "ghost", "label": "bed"}
                          for bed in beds]]},
            {"label": "Lamps placed where the scene record puts them",
             "shapes": [{"kind": "dots", "points": [plan_point(lamp["spot"][0], lamp["spot"][2]) for lamp in lamps],
                         "r": 0.35, "tone": "made", "label": "lamp"}]},
            {"label": "Every lamp's strength scaled until the place is as bright as its concept (ring: strength)",
             "shapes": rings(lamps, swept)}],
        "slider": {"label": "lamp strength", "unit": "x the seed's", "values": [1.0, round(swept, 2)], "at": 1,
                   "shapes": [rings(lamps, 1.0), rings(lamps, swept)]},
        "numbers": [
            {"label": "lamps", "value": len(lamps), "unit": "", "tip": "lamps with a spot (the sun has none)"},
            {"label": "concept", "value": brightness["concept"], "unit": "",
             "tip": "the concept picture's brightness, 0 dark to 1 white"},
            {"label": "before", "value": mean(list(brightness["before"].values())), "unit": "",
             "tip": "the views' mean brightness at the seed's strengths"},
            {"label": "after", "value": mean(list(brightness["after"].values())), "unit": "",
             "tip": f"the views' mean brightness with every lamp x{swept:.2f}"}]}
