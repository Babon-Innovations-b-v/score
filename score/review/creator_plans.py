"""Creator data wins (the owner, 2026-10-21): where the creator has approved a plan of a thing a place holds, the plan
writer lays that plan as given, scaled and placed, and never reinvents it. Today one: the ship's floor plan
(data/definitions/ship_floor.json, its rooms inside its own hull, the owner's plan v7's at its 46 m), held by
the row of the hangar that holds its rooms. Its hull outline from above (the nose spike and the hull at its waist,
as tools/props/scene/ship_floor.py draws it) and every room's outline come from tools/props/scene/ship_floor.py, in
the ship's frame: x across (starboard positive), y back from the nose spike's tip, metres.

`planned(holds)` finds the row a creator's plan belongs to; `laid(found, middle, facing)` places it on a plan: its
middle where the drawing puts the thing, its nose the way the drawing points it, at its own size."""
import functools
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENE = REPO / "tools/props/scene"
# the plan-writing facing (the way a thing's front points) as a unit step on the plan: x east, y south
WAYS = {"N": (0.0, -1.0), "E": (1.0, 0.0), "S": (0.0, 1.0), "W": (-1.0, 0.0)}


@functools.lru_cache(maxsize=1)
def ship():
    """The ship's floor plan: {what, places, outline [[x, y]], rooms {place: [[x, y]]}, length, base, tall} in the
    ship's frame (metres), its base the keel's lowest over the ground and its tall the hull's top."""
    if str(SCENE) not in sys.path:
        sys.path.insert(0, str(SCENE))
    import ship_floor
    floor = ship_floor.read_floor()
    hull, spike = ship_floor.hull_of(floor), floor["hull"]["spike"]
    side = [(row["half"], row["y"]) for row in hull]
    outline = [(spike["tip"], 0.0)] + side + [(-half, along) for half, along in reversed(side)] + [(-spike["tip"], 0.0)]
    rooms = {space["place"]: ship_floor.outline_points(hull, floor, space) for space in ship_floor.spaces(floor)}
    return {"what": f"the ship's floor plan (data/definitions/ship_floor.json, {floor['length']:g} m)",
            "places": sorted(rooms), "outline": [list(point) for point in outline],
            "rooms": {place: [list(point) for point in points] for place, points in rooms.items()},
            "length": floor["length"], "wide": round(2 * max(row["half"] for row in hull), 3),
            "base": round(min(row["keel"] for row in hull), 3), "tall": round(max(row["top"] for row in hull), 3)}


PLANS = (ship,)


def planned(holds):
    """(row, the creator's plan) of the row holding every place of a creator's plan (`holds`: a plan's inside places,
    each with its row), else None."""
    for plan in PLANS:
        found = plan()
        rows = {hold.get("row") for hold in holds if hold["place"] in found["places"]}
        held = {hold["place"] for hold in holds}
        if len(rows) == 1 and None not in rows and set(found["places"]) <= held:
            return rows.pop(), found
    return None


def box_of(points):
    """[x, y, wide, deep] round `points`."""
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]


def turned(found, middle, facing):
    """A function taking a point of the creator's frame to plan metres: the plan's box middle at `middle`, its nose
    (y = 0) toward `facing` (N, E, S or W), its starboard on the right of one looking that way."""
    ahead = WAYS[facing]
    right = (-ahead[1], ahead[0])  # y runs south: looking north, the right is east
    x, y, wide, deep = box_of(found["outline"])
    across_middle, along_middle = x + wide / 2, y + deep / 2

    def placed(point):
        across, back = point[0] - across_middle, point[1] - along_middle
        return [round(middle[0] + across * right[0] - back * ahead[0], 3),
                round(middle[1] + across * right[1] - back * ahead[1], 3)]
    return placed


def laid(found, middle, facing):
    """(item box [x, y, wide, deep], its shape {polygon in 0..1 of the box, tall, base}, {place: [x, y, w, d]}) of
    the creator's plan laid on a plan with its middle at `middle`, nose toward `facing`."""
    placed = turned(found, middle, facing)
    outline = [placed(point) for point in found["outline"]]
    x, y, wide, deep = box_of(outline)
    shape = {"shape": "polygon", "points": [[round((px - x) / wide, 4), round((py - y) / deep, 4)] for px, py in outline],
             "tall": found["tall"], "base": found["base"], "planned": found["what"]}
    rooms = {place: [round(value, 3) for value in box_of([placed(point) for point in points])]
             for place, points in found["rooms"].items()}
    return [round(value, 3) for value in (x, y, wide, deep)], shape, rooms
