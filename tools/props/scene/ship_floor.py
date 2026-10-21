"""The ship's floor plan inside its hull (the owner's loop, 2026-10-19: the outside's plan split into the inside's
rooms, each measured from the hull), read from data/definitions/ship_floor.json and the hull's own numbers
(../library/inside/ship_outline.py over data/definitions/ship.json, at the floor plan's length).

    python3 tools/props/scene/ship_floor.py <out folder>           # ship-floor.png and ship-floor.json; faults exit 1

Needs the hull's reader, ../library/inside/ship_outline.py, which lands with the 46 m hull (fix-ship-hull); until then
run it with that file's folder on PYTHONPATH (git show fix-ship-hull:tools/props/library/inside/ship_outline.py).

Plain Python (matplotlib only for the picture). Frame as the ship plan's, built metres: y back from the spike's tip, x
across (starboard positive), z up from the ground the ship stands on.
"""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE.parent / "library" / "inside"))
# The hull's reader comes with the 46 m hull (branch fix-ship-hull, in the owner's basket): it sits in the bake's
# declared folder, so landing it alone would re-buy every place's bake. Until then this module does not import.
import ship_outline  # noqa: E402

SHIP = REPO / "data/definitions/ship.json"
FLOOR = REPO / "data/definitions/ship_floor.json"
PLACES = REPO / "data/definitions/place.json"
# How far apart the hull is read along a room (metres).
STEP = 0.1
# The least clear height a person walks under, and the least depth a side room may have.
LEAST_CLEAR, LEAST_DEEP = 2.2, 1.5


def read_floor(path=FLOOR):
    """The floor plan as data/definitions/ship_floor.json holds it."""
    return json.loads(pathlib.Path(path).read_text())


def hull_plan(ship, floor):
    """The hull's stations front to back (ship_outline.stations), the ship plan built at the floor plan's length:
    plan v7 is drawn at its `drawn_length` (its `length` until the hull branch lands)."""
    built = {**ship, "drawn_length": ship.get("drawn_length", ship["length"]), "length": floor["length"]}
    return ship_outline.stations(built)


def station_at(hull, along):
    """The hull's station `along` metres from the tip, straight between its stations."""
    return {key: ship_outline.interpolated([(row["y"], row[key]) for row in hull], along)
            for key in ("half", "keel", "top")} | {"y": along}


def samples(span):
    """Stations from one end of a span to the other, STEP apart, both ends kept."""
    count = max(1, round((span[1] - span[0]) / STEP))
    return [span[0] + (span[1] - span[0]) * index / count for index in range(count + 1)]


def floor_at(room, floor, along):
    """A room's floor height at `along`: the deck, or the last of its `floors` steps at or before it."""
    height = floor["deck"]
    for start, step in room.get("floors", []):
        if along >= start - 1e-9:
            height = step
    return height


def inner_half(hull, floor, along, height):
    """The hull's inner half width at `along` for a floor at `height`: the narrower of its floor and a person's head
    over it, less the lining."""
    here = station_at(hull, along)
    return min(ship_outline.side_x(here, height), ship_outline.side_x(here, height + floor["head"])) - floor["lining"]


def inner_top(hull, floor, along):
    """The hull's inner top at `along`."""
    return station_at(hull, along)["top"] - floor["lining"]


def across(hull, floor, room, along):
    """A room's width at `along`: the hull's inner width for a whole-width room, else from the walkway's partition
    to the hull."""
    if room["side"] == "middle":
        return room["wide"]
    half = inner_half(hull, floor, along, floor_at(room, floor, along))
    if room["side"] == "whole":
        return 2 * half
    return half - floor["walkway"]["wide"] / 2 - floor["partition"]


def clear(hull, floor, room, along):
    """A room's clear height at `along`: its ceiling, or the hull's inner top for a room roofed by the hull."""
    base, ceiling = floor_at(room, floor, along), room.get("ceiling", floor["ceiling"])
    under_hull = inner_top(hull, floor, along) - base
    return under_hull if ceiling == "hull" else min(ceiling, under_hull)


def measured(hull, floor, room):
    """A room's measures from the hull: its span, length, width and clear height front and back, floor heights,
    floor area and the hull's waist over its floor (where its outer wall stops leaning out and leans in)."""
    front, back = room["y"]
    stations = samples(room["y"])
    widths = [across(hull, floor, room, along) for along in stations]
    middle = station_at(hull, (front + back) / 2)
    waist = ship_outline.section(middle)[2][1] - floor_at(room, floor, (front + back) / 2)
    return {"name": room["name"], "place": room["place"], "side": room["side"], "y": [front, back],
            "long": round(back - front, 2), "wide": [round(widths[0], 2), round(widths[-1], 2)],
            "narrowest": round(min(widths), 2), "widest": round(max(widths), 2),
            "clear": [round(clear(hull, floor, room, front), 2), round(clear(hull, floor, room, back), 2)],
            "floors": sorted({round(floor_at(room, floor, along), 2) for along in stations}),
            "area": round(sum(widths) / len(widths) * (back - front), 1), "waist_over_floor": round(waist, 2)}


def spaces(floor):
    """Every room of the plan and the walkway as one, the walkway a whole-ship room down the middle line."""
    walkway = {**floor["walkway"], "name": "walkway", "side": "middle"}
    return floor["rooms"] + [walkway]


def overlap(first, second):
    """Whether two spaces share floor: their spans overlap and their sides meet."""
    meet = {first["side"], second["side"]}
    sides_meet = "whole" in meet or len(meet) == 1 or meet == {"middle", "whole"}
    return sides_meet and first["y"][0] < second["y"][1] - 1e-9 and second["y"][0] < first["y"][1] - 1e-9


def overlap_faults(floor):
    """Spaces that share floor."""
    found, every = [], spaces(floor)
    for index, first in enumerate(every):
        for second in every[index + 1:]:
            if overlap(first, second):
                found.append(f"{first['name']} and {second['name']} overlap")
    return found


def hull_faults(hull, floor, room):
    """Where a room does not fit the hull: its keel over the deck's structure, a ceiling a person cannot walk under or
    over the hull, a side room too shallow."""
    found = []
    for along in samples(room["y"]):
        base, here = floor_at(room, floor, along), station_at(hull, along)
        if here["keel"] > base - floor["floor_depth"]:
            found.append(f"{room['name']}: the keel at {along:.1f} m is {here['keel']:.2f} m, over its floor's structure")
        if clear(hull, floor, room, along) < LEAST_CLEAR:
            found.append(f"{room['name']}: {clear(hull, floor, room, along):.2f} m clear at {along:.1f} m")
        if room["side"] in ("port", "starboard") and across(hull, floor, room, along) < LEAST_DEEP:
            found.append(f"{room['name']}: {across(hull, floor, room, along):.2f} m deep at {along:.1f} m")
    return found


def door_faults(floor, ship):
    """Doors that lead nowhere or stand outside their room, rooms with no door to the walkway, and a hull door that is
    not the side ring."""
    found, names = [], {space["name"] for space in spaces(floor)}
    for space in spaces(floor):
        doors = space.get("doors", [])
        for door in doors:
            if not space["y"][0] - 1e-9 <= door["y"] <= space["y"][1] + 1e-9:
                found.append(f"{space['name']}: a door at {door['y']} m stands outside it")
            if door["wall"] != "hull" and door["leads"] not in names:
                found.append(f"{space['name']}: a door leads to {door['leads']}, no space of the plan")
            if door["wall"] == "hull" and (space["side"] != side_ring(ship)["side"]
                                           or abs(door["y"] - ring_y(ship, floor)) > 0.01):
                found.append(f"{space['name']}: a hull door that is not the side ring")
        if space["name"] != "walkway" and not any(door["leads"] == "walkway" for door in doors):
            found.append(f"{space['name']}: no door to the walkway")
    return found


def side_ring(ship):
    """The ship plan's side ring (named `hull_detail` until the hull branch lands, the record it corrects)."""
    return ship.get("side_ring") or ship["hull_detail"]


def ring_y(ship, floor):
    """Where the side ring stands along the ship built at the floor plan's length."""
    return round(side_ring(ship)["y"] * floor["length"] / ship.get("drawn_length", ship["length"]), 2)


def place_faults(floor, path=PLACES):
    """Spaces whose place is no place of the environment (data/definitions/place.json); a place's plan is its
    design's (the old filed plans in data/plans were retired, 2026-10-21)."""
    places = json.loads(pathlib.Path(path).read_text())
    return [f"{space['name']}: {space['place']} is no place in data/definitions/place.json" for space in spaces(floor)
            if space["place"] not in places]


def faults(ship, floor):
    """Everything wrong with the floor plan against the hull, its doors and the places it names."""
    hull = hull_plan(ship, floor)
    return (overlap_faults(floor) + [fault for space in spaces(floor) for fault in hull_faults(hull, floor, space)]
            + door_faults(floor, ship) + place_faults(floor))


def rooms_measured(ship, floor):
    """Every space's measures, front to back."""
    hull = hull_plan(ship, floor)
    return sorted((measured(hull, floor, space) for space in spaces(floor)), key=lambda found: found["y"][0])


def wide_words(size):
    """A room's width in words: one number, or narrowest to widest when they differ by more than a door's width."""
    if size["widest"] - size["narrowest"] < 0.9:
        return f"{size['narrowest']:.1f}"
    return f"{size['narrowest']:.1f} to {size['widest']:.1f}"


def outline_points(hull, floor, space):
    """A space's outline seen from above as (x, y) points: its walkway-side edge and its hull-side edge."""
    stations = samples(space["y"])
    if space["side"] == "middle":
        half = space["wide"] / 2
        return [(-half, stations[0]), (half, stations[0]), (half, stations[-1]), (-half, stations[-1])]
    outer = [inner_half(hull, floor, along, floor_at(space, floor, along)) for along in stations]
    if space["side"] == "whole":
        return [(half, along) for half, along in zip(outer, stations)] + [
            (-half, along) for half, along in reversed(list(zip(outer, stations)))]
    sign, inner = (1 if space["side"] == "starboard" else -1), floor["walkway"]["wide"] / 2 + floor["partition"]
    return ([(sign * inner, stations[0])] + [(sign * half, along) for half, along in zip(outer, stations)]
            + [(sign * inner, stations[-1])])


def picture(ship, floor, destination):
    """The plan drawing: the ship from above with its rooms, doors and side ring, and from the side with its decks,
    ceilings and hull, each room named with its size."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot

    hull, found = hull_plan(ship, floor), {room["name"]: room for room in rooms_measured(ship, floor)}
    stations = hull
    figure, (above, side) = pyplot.subplots(2, 1, figsize=(16, 11), gridspec_kw={"height_ratios": [1.5, 1]})
    colours = pyplot.get_cmap("tab10")
    ys = [row["y"] for row in stations]
    above.plot(ys, [row["half"] for row in stations], color="0.2", lw=1.5)
    above.plot(ys, [-row["half"] for row in stations], color="0.2", lw=1.5, label="hull at its waist")
    deck = [inner_half(hull, floor, along, floor["deck"]) for along in ys]
    above.plot(ys, deck, color="0.6", lw=0.8, ls="--")
    above.plot(ys, [-half for half in deck], color="0.6", lw=0.8, ls="--", label="inside at the deck")
    for index, space in enumerate(spaces(floor)):
        points = outline_points(hull, floor, space)
        colour = "0.85" if space["side"] == "middle" else colours(index)
        above.fill([y for _, y in points], [x for x, _ in points], color=colour, alpha=0.55, lw=1, ec="0.3")
        size = found[space["name"]]
        label = f"{space['name']}\n{size['long']:.1f} m long, {wide_words(size)} m wide\n{min(size['clear']):.1f} m clear"
        middle_x = sum(x for x, _ in points) / len(points) if space["side"] != "middle" else 0.0
        above.text(sum(space["y"]) / 2, middle_x, label, ha="center", va="center", fontsize=7)
        for door in space.get("doors", []):
            above.plot([door["y"]], [door_x(floor, space, door, hull)], marker="s", color="black", ms=5)
    ring = ring_y(ship, floor)
    above.plot([ring], [inner_half(hull, floor, ring, floor["deck"]) + floor["lining"]], marker="o", ms=11,
               mfc="none", mec="darkorange", mew=2.5, label="side ring: docking hatch and people airlock")
    above.plot([], [], marker="s", color="black", ls="none", label="door")
    above.set_title(f"The ship from above, {floor['length']:.0f} m (nose left, starboard up): rooms, doors, side ring")
    above.set_xlabel("metres back from the nose spike's tip")
    above.set_ylabel("metres across")
    above.set_aspect("equal")
    above.legend(loc="lower left", fontsize=8)
    side.fill_between(ys, [row["keel"] for row in stations], [row["top"] for row in stations], color="0.92")
    side.plot(ys, [row["keel"] for row in stations], color="0.2", lw=1.5, label="keel")
    side.plot(ys, [row["top"] for row in stations], color="0.2", lw=1.5, label="hull top")
    for index, space in enumerate(spaces(floor)):
        alongs = samples(space["y"])
        bases = [floor_at(space, floor, along) for along in alongs]
        tops = [base + clear(hull, floor, space, along) for base, along in zip(bases, alongs)]
        colour = "0.6" if space["side"] == "middle" else colours(index)
        side.fill_between(alongs, bases, tops, color=colour, alpha=0.45 if space["side"] == "whole" else 0.25,
                          step="post")
    side.axhline(0, color="saddlebrown", lw=1)
    side.set_title("From the side: one deck at 2.4 m over the ground, the rooms' clear height, the hull round them")
    side.set_xlabel("metres back from the nose spike's tip")
    side.set_ylabel("metres over the ground")
    side.set_aspect("equal")
    side.legend(loc="upper left", fontsize=8)
    figure.tight_layout()
    figure.savefig(destination, dpi=110)
    pyplot.close(figure)


def door_x(floor, space, door, hull):
    """Where a door stands across the ship, seen from above."""
    if space["side"] == "middle" or door["wall"] in ("forward", "aft"):
        return 0.0
    sign = 1 if space["side"] == "starboard" else -1
    if door["wall"] == "hull":
        return sign * inner_half(hull, floor, door["y"], floor_at(space, floor, door["y"]))
    return sign * (floor["walkway"]["wide"] / 2)


def main(arguments):
    out = pathlib.Path(arguments[0])
    out.mkdir(parents=True, exist_ok=True)
    ship, floor = ship_outline.read_plan(SHIP), read_floor()
    found = faults(ship, floor)
    rooms = rooms_measured(ship, floor)
    (out / "ship-floor.json").write_text(json.dumps({"rooms": rooms, "faults": found}, indent=1))
    picture(ship, floor, out / "ship-floor.png")
    print(f"{len(rooms)} spaces, {len(found)} faults; wrote {out}/ship-floor.png, ship-floor.json")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
