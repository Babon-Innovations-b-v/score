"""The split itself: an outside shell's inside cut into the shapes of its inside places, front to back along the
shell's long axis, deterministic (same plan, same split). Plain Python; the stage's docstring has the input.

    layout = split(shell, plan["split"])   # {"shell", "span", "left_out", "places": [...]}

How it cuts (each rule a choice, said here so a different answer is a different rule, never a tuned number):

- **The inside's span** is the longest run of the outline's stations where a person stands (`least.clear` clear over
  the floor) and a whole-width room fits (`least.wide` across). What lies ahead of it and behind it is left out.
- **Bands, front to back, in the room list's order.** A `whole` room is a band of its own, wall to wall. A run of
  `left` and `right` rooms is one band with the spine (the corridor joining them) down its middle; when a whole room
  stands ahead of it, the spine opens with a hall (`spine.hall` long, wall to wall) behind that room's door.
- **Lengths by one share of headroom.** Every room starts at its least length; the span left over is shared so each
  band grows the same fraction of its headroom (most less least) and the bands fill the span. A side band is as long
  as its longer side at that fraction; the shorter side's rooms share the difference the same way, past their most
  if they must (the bounds gate then fails them by name). Once every band is at its most, what is left of the span
  stays at the back, left out: the split never stretches a room past its bounds to fill the shell.
- **Doors** are the plan's `door` size: a side room's on the spine's wall at its middle; a whole room's, and the
  spine's, on the wall it shares with the shape ahead of it (the spine, else the whole room there).
"""

ROUND = 3  # millimetres: every length written
# A side room takes its side's lane, the spine the middle (its hall, `hall`, the two sides as well), a whole room all
# three.
LANES = ("left", "middle", "right")
SIDES = ("whole", "left", "right")


def interpolated(stations, along, column):
    """The outline's value in `column` (1 left, 2 right, 3 clear) at `along`, straight between stations."""
    if along <= stations[0][0]:
        return stations[0][column]
    for before, after in zip(stations, stations[1:]):
        if before[0] <= along <= after[0]:
            share = 0.0 if after[0] == before[0] else (along - before[0]) / (after[0] - before[0])
            return before[column] + (after[column] - before[column]) * share
    return stations[-1][column]


def stands(station, least):
    """Whether a person stands at an outline station and a whole-width room fits there."""
    _, left, right, clear = station
    return clear >= least["clear"] and left + right >= least["wide"]


def inside_span(stations, least):
    """(front, back) of the longest run of stations where a person stands; ValueError when there is none."""
    best, start = None, None
    for index, station in enumerate(stations):
        if stands(station, least):
            start = index if start is None else start
            run = (stations[start][0], station[0])
            if best is None or run[1] - run[0] > best[1] - best[0]:
                best = run
        else:
            start = None
    if best is None or best[1] <= best[0]:
        raise ValueError("no station of the outline has a person's clear height and a whole room's width")
    return best


def bands(rooms):
    """The room list as bands, front to back: [("whole", [room]) or ("side", [room, ...])]."""
    found = []
    for room in rooms:
        if room["side"] not in SIDES:
            raise ValueError(f"{room['place']}: side {room['side']!r} is none of {SIDES}")
        if room["side"] == "whole":
            found.append(("whole", [room]))
        elif found and found[-1][0] == "side":
            found[-1][1].append(room)
        else:
            found.append(("side", [room]))
    if sum(kind == "side" for kind, _ in found) > 1:
        raise ValueError("side rooms in two runs: one spine per shell is all the split lays")
    return found


def column(rooms, side):
    """The rooms of one side of a side band, front to back."""
    return [room for room in rooms if room["side"] == side]


def sum_bound(rooms, end):
    """The sum of the rooms' least (end 0) or most (end 1) lengths."""
    return sum(room["long"][end] for room in rooms)


def band_bounds(kind, rooms):
    """(least, most) of a band's length: a whole room's own; a side band's, its longer side's."""
    if kind == "whole":
        return tuple(rooms[0]["long"])
    sides = [column(rooms, "left"), column(rooms, "right")]
    return max(sum_bound(side, 0) for side in sides), max(sum_bound(side, 1) for side in sides)


def share(bounds, room_for):
    """The fraction of headroom each band grows so they fill `room_for`, at most 1."""
    least, most = sum(low for low, _ in bounds), sum(high for _, high in bounds)
    if room_for < least - 1e-9:
        raise ValueError(f"the rooms' least lengths, {least:.2f} m, do not fit the {room_for:.2f} m the shell has")
    return 1.0 if most - least <= 1e-9 else min(1.0, (room_for - least) / (most - least))


def side_lengths(rooms, length):
    """Each room of one side, front to back, grown the same share of its headroom so the side is `length` long
    (rooms with no headroom grow evenly)."""
    least, most = sum_bound(rooms, 0), sum_bound(rooms, 1)
    if not rooms:
        return []
    if most - least <= 1e-9:
        return [room["long"][0] + (length - least) / len(rooms) for room in rooms]
    fraction = (length - least) / (most - least)
    return [room["long"][0] + fraction * (room["long"][1] - room["long"][0]) for room in rooms]


def door(at, wall, leads, size):
    """One door: where along it stands, the wall it is in, the place it leads to, its size."""
    return {"along": round(at, ROUND), "wall": wall, "leads": leads, "wide": size["wide"], "tall": size["tall"]}


def shape(entry, front, back, lanes):
    """A placed shape: its place, name, side, span along, length and lanes (the dict the doors and measures join)."""
    return {"place": entry["place"], "name": entry.get("name", entry["place"]), "side": entry.get("side", "middle"),
            "along": [round(front, ROUND), round(back, ROUND)], "long": round(back - front, ROUND),
            "lanes": list(lanes), "doors": []}


def laid_whole(room, front, length):
    """A whole room's shape, wall to wall."""
    return shape(room, front, front + length, LANES)


def laid_side(rooms, front, length, spine, hall):
    """A side band's shapes: each side's rooms front to back and the spine down the middle, the hall (when there is
    one) wall to wall at its front."""
    laid = [shape({**spine, "side": "middle"}, front, front + hall + length, ("middle",))]
    if hall:
        laid[0]["hall"] = [round(front, ROUND), round(front + hall, ROUND)]
    for side in ("left", "right"):
        along = front + hall
        for room, long in zip(column(rooms, side), side_lengths(column(rooms, side), length)):
            laid.append(shape(room, along, along + long, (side,)))
            along += long
    return laid


def doors_into(laid, size):
    """Every door, each with its door back: a side room's onto the spine; a whole room's and the spine's onto the
    shape ahead of it (the spine, else the whole room there)."""
    spine = next((item for item in laid if item["side"] == "middle"), None)
    for index, item in enumerate(laid):
        if item["side"] in ("left", "right"):
            middle = (item["along"][0] + item["along"][1]) / 2
            item["doors"].append(door(middle, "spine", spine["place"], size))
            spine["doors"].append(door(middle, item["side"], item["place"], size))
        elif index:
            ahead = next((other for other in reversed(laid[:index]) if other["side"] in ("whole", "middle")), None)
            if ahead is None:
                continue
            item["doors"].append(door(item["along"][0], "forward", ahead["place"], size))
            ahead["doors"].append(door(item["along"][0], "aft", item["place"], size))
    return laid


def laid_bands(found, front, room_for, spine):
    """Every band's shapes, front to back from `front`, grown to fill `room_for` (the span less the hall)."""
    bounds = [band_bounds(kind, rooms) for kind, rooms in found]
    fraction = share(bounds, room_for)
    laid, along = [], front
    for index, ((kind, rooms), (least, most)) in enumerate(zip(found, bounds)):
        length = least + fraction * (most - least)
        if kind == "whole":
            laid.append(laid_whole(rooms[0], along, length))
            along += length
            continue
        hall = spine.get("hall", 0.0) if index and found[index - 1][0] == "whole" else 0.0
        laid += laid_side(rooms, along, length, spine, hall)
        along += hall + length
    return laid, along


def measured(item, stations, spine, partition):
    """A shape's widths and clear height read from the outline at its front, its back and every station between:
    a whole room wall to wall, a side room from the spine's partition to the shell, the spine its own width."""
    front, back = item["along"]
    alongs = [front, *[station[0] for station in stations if front < station[0] < back], back]
    clears = [interpolated(stations, along, 3) for along in alongs]
    if item["side"] == "middle":
        widths = [spine["wide"]] * len(alongs)
    elif item["side"] in ("left", "right"):
        column_of = 1 if item["side"] == "left" else 2
        widths = [interpolated(stations, along, column_of) - spine["wide"] / 2 - partition for along in alongs]
    else:
        widths = [interpolated(stations, along, 1) + interpolated(stations, along, 2) for along in alongs]
    return {**item, "wide": [round(widths[0], ROUND), round(widths[-1], ROUND)],
            "narrowest": round(min(widths), ROUND), "clear": round(min(clears), ROUND)}


def split(shell, plan):
    """The shell's inside split into its inside places (module docstring): its span, what is left out, every shape
    with its doors, widths and clear height."""
    stations = sorted(plan["outline"])
    front, back = inside_span(stations, plan["least"])
    found = bands(plan["rooms"])
    spine = plan.get("spine")
    if spine is None and any(kind == "side" for kind, _ in found):
        raise ValueError("side rooms need a spine to open onto")
    hall = sum(spine.get("hall", 0.0) for index, (kind, _) in enumerate(found)
               if kind == "side" and index and found[index - 1][0] == "whole") if spine else 0.0
    laid, end = laid_bands(found, front, back - front - hall, spine or {})
    laid = [measured(item, stations, spine or {}, plan.get("partition", 0.0)) for item in doors_into(laid, plan["door"])]
    left_out = [[round(stations[0][0], ROUND), round(front, ROUND)], [round(end, ROUND), round(stations[-1][0], ROUND)]]
    return {"shell": shell, "span": [round(front, ROUND), round(back, ROUND)],
            "left_out": [span for span in left_out if span[1] - span[0] > 10 ** -ROUND], "places": laid}
