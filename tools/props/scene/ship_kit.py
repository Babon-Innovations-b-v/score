"""The kit layout of a ship room: where every piece of a room in the crew's shuttle stands (the ship as a world 1 place,
2026-10-14; the bridge first), as the route's input (tools/props/library/route.py plan, then layout and install,
which write data/kit/<room>.json once the pieces are made and baked).

    python3 tools/props/scene/ship_kit.py <room> <out.json> [<plan.json> <inventory.json>]

The room's numbers are its plan's (data/plans/<room>.json): its inside wide and deep (`w`, `d`, the plan's frame: x
east, y south from its north-west corner), its ceiling (`ceiling <n> m` in its height words), its doors, and its
`kit` block: `nose_cut` (how far the nose's two front corners are cut each way; 0 for a square room), and the
windows' `sill`, `head` and `pillar` (the cut corners and the front wall between them are glazed). Frame: the room's
middle on its floor, x east, z south, y up; the nose is south.

What is laid, and from what:
- walls: every wall round the room's outline (north, east, the east cut, the front, the west cut, west) in a lower and
  an upper band of plain plates about PANEL wide, a doorway left clear in its wall; a glazed wall's lower band runs to
  its sill and a header plate fills it from its head to the ceiling;
- windows: on each glazed wall a frame and a pane per light between its pillars (the front wall two lights, each cut
  corner one), from sill to head;
- the floor and the ceiling: deck plates and ceiling plates in a grid over the room's square part, the nose's strip
  between the cut corners in a grid, and each cut corner one triangle (`taper` 0);
- the rows the inventory places by their spots (room_kit.placed_rows): the made pieces (seats, consoles, the door's
  frame and leaf) and the code-built trims and lamps.

Code builds only what the sorter's allow-list names plain (tools/props/library/sorter.py PLAIN): the wall bands,
deck and ceiling plates take its names (wall_lower_plain, wall_upper_plain, ring_floor_plate, roof_face_panel); any
other kind laid here goes the prop route unless the owner names it plain.
"""
import json
import math
import pathlib
import re
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import room_kit  # noqa: E402

REPO = HERE.parents[2]
PANEL = room_kit.PANEL
CELL = room_kit.FLOOR_CELL
LAP = room_kit.LAP
PLATE_DEEP = 0.04  # a deck or ceiling plate's thickness when the inventory gives none
WALL_DEEP = 0.06
CEILING = re.compile(r"ceiling (\d+(?:\.\d+)?) m")
DOOR_SIZE = re.compile(r"(\d+(?:\.\d+)?) x (\d+(?:\.\d+)?) m")
UP = np.array([0.0, 1.0, 0.0])
DOWN = -UP


def ceiling_of(plan):
    """The room's ceiling height from its plan's height words."""
    found = CEILING.search(plan["height"])
    if found is None:
        raise ValueError(f"{plan['title']}: its height names no ceiling ({plan['height']!r})")
    return float(found.group(1))


def outline(plan):
    """The room's outline from above, (x, z) points in the room's frame, clockwise from the north-west corner: the
    north wall, the east wall, the east cut, the front, the west cut, the west wall (a cut of 0 leaves a square)."""
    half_w, half_d, cut = plan["w"] / 2, plan["d"] / 2, plan["kit"]["nose_cut"]
    if cut <= 0:
        return [np.array(point) for point in ((-half_w, -half_d), (half_w, -half_d), (half_w, half_d),
                                              (-half_w, half_d))]
    return [np.array(point) for point in ((-half_w, -half_d), (half_w, -half_d), (half_w, half_d - cut),
                                          (half_w - cut, half_d), (-half_w + cut, half_d), (-half_w, half_d - cut))]


WALL_NAMES = {6: ("north", "east", "east_cut", "front", "west_cut", "west"), 4: ("north", "east", "front", "west")}
GLAZED = ("east_cut", "front", "west_cut")
SIDE_WALL = {"N": "north", "E": "east", "S": "front", "W": "west"}


def sides(plan):
    """Every wall round the room: its name, its two ends (x, z), its outward normal and whether it is glazed, in the
    shape room_kit's on_side reads."""
    points = outline(plan)
    found = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        along = (end - start) / np.linalg.norm(end - start)
        outward = np.array([along[1], -along[0]])  # clockwise from above (x east, z south): the outside is on the left
        name = WALL_NAMES[len(points)][index]
        found.append({"name": name, "start": start, "end": end, "outward": outward, "main": True,
                      "glazed": name in GLAZED})
    return found


def doorways(plan, side):
    """The doorways in a wall, each (across from the wall's middle toward its end, wide, tall)."""
    found = []
    for door_side, at, wide, what, *level in plan["doors"]:
        if SIDE_WALL[door_side] != side["name"]:
            continue
        sized = DOOR_SIZE.search(what)
        if sized is None:
            raise ValueError(f"door {door_side} ({what}): its words give no size")
        start_at = {"north": -plan["w"] / 2, "front": -plan["w"] / 2}.get(side["name"], -plan["d"] / 2)
        along = (side["end"] - side["start"]) / np.linalg.norm(side["end"] - side["start"])
        point = np.array([start_at + at, side["start"][1]]) if side["name"] in ("north", "front") else \
            np.array([side["start"][0], start_at + at])
        middle = (side["start"] + side["end"]) / 2
        found.append((float((point - middle) @ along), float(wide), float(sized.group(2))))
    return found


def runs(length, openings):
    """A wall's runs between its doorways, as (middle, length) from the wall's middle along it."""
    edges, start = [], -length / 2
    for across, wide, _ in sorted(openings):
        edges.append((start, across - wide / 2))
        start = across + wide / 2
    edges.append((start, length / 2))
    return [((low + high) / 2, high - low) for low, high in edges if high - low > 0.01]


def band(room, kind, side, middle, run, bottom, tall):
    """A run of plain plates about PANEL wide along a wall, their foot `bottom` up."""
    count = max(1, round(run / PANEL))
    wide = run / count
    return [room_kit.on_side(room, kind, side, middle - run / 2 + wide * (index + 0.5), bottom,
                             (wide + LAP, tall, WALL_DEEP)) for index in range(count)]


def walls(room, plan, ceiling):
    """Every wall's two bands of plain plates; a glazed wall's lower band to its sill and its header over its head; a
    doorway's wall runs round it, with a header plate over the doorway."""
    found = []
    sill, head = plan["kit"]["sill"], plan["kit"]["head"]
    for side in sides(plan):
        length = float(np.linalg.norm(side["end"] - side["start"]))
        openings = doorways(plan, side)
        if side["glazed"]:
            found += band(room, "wall_lower_plain", side, 0.0, length, 0.0, sill)
            found += band(room, "wall_upper_plain", side, 0.0, length, head, ceiling - head)
            continue
        for middle, run in runs(length, openings):
            found += band(room, "wall_lower_plain", side, middle, run, 0.0, room_kit.LOWER)
            found += band(room, "wall_upper_plain", side, middle, run, room_kit.LOWER, ceiling - room_kit.LOWER)
        for across, wide, tall in openings:
            found += band(room, "wall_upper_plain", side, across, wide, tall, ceiling - tall)
    return found


def windows(room, plan):
    """On each glazed wall, a frame and a pane per light: the front wall split by its pillar into two, a cut corner
    one; each from sill to head, the pane set in its frame."""
    found = []
    sill, head, pillar = plan["kit"]["sill"], plan["kit"]["head"], plan["kit"]["pillar"]
    for side in sides(plan):
        if not side["glazed"]:
            continue
        length = float(np.linalg.norm(side["end"] - side["start"]))
        lights = 2 if side["name"] == "front" else 1
        wide = (length - pillar * (lights + 1)) / lights
        for index in range(lights):
            across = -length / 2 + pillar + (wide + pillar) * index + wide / 2
            found.append(room_kit.on_side(room, "window_frame", side, across, sill,
                                          (wide + 2 * pillar, head - sill, 0.12)))
            found.append(room_kit.on_side(room, "window_pane", side, across, sill + pillar / 2,
                                          (wide, head - sill - pillar, 0.04), out=0.04))
    return found


def plate(room, kind, foot_middle, along, face, size, taper=1.0):
    """A plate lying flat, laid as room_kit lays its deck plates: from the middle of its foot edge, `along` the way it
    runs, its front `face` (up for a floor, down for a ceiling); `taper` its head's width over its foot's."""
    y_axis = np.asarray(along, dtype=float)
    z_axis = -np.asarray(face, dtype=float)
    laid = room_kit.piece(room, kind, foot_middle, (np.cross(y_axis, z_axis), y_axis, z_axis), size)
    laid["taper"] = taper
    return laid


def grid(room, kind, low, high, level, face, deep):
    """A rectangle (x, z) of plates about CELL across at `level`, each laid from its north edge."""
    size = np.array(high) - np.array(low)
    counts = [max(1, round(value / CELL)) for value in size]
    cell = size / counts
    found = []
    for across in range(counts[0]):
        for along in range(counts[1]):
            corner = np.array(low) + cell * np.array([across, along])
            found.append(plate(room, kind, np.array([corner[0] + cell[0] / 2, level, corner[1]]), (0.0, 0.0, 1.0),
                               face, (cell[0], cell[1], deep)))
    return found


def deck(room, plan, kind, level, face, deep):
    """A floor or ceiling over the outline: the square part and the nose's strip between the cut corners in grids,
    each cut corner one triangle from its long edge to its square corner."""
    half_w, half_d, cut = plan["w"] / 2, plan["d"] / 2, plan["kit"]["nose_cut"]
    found = grid(room, kind, (-half_w, -half_d), (half_w, half_d - cut), level, face, deep)
    if cut <= 0:
        return found
    found += grid(room, kind, (-half_w + cut, half_d - cut), (half_w - cut, half_d), level, face, deep)
    for sign in (-1.0, 1.0):
        foot = np.array([sign * (half_w - cut / 2), level, half_d - cut / 2])
        toward = np.array([-sign, 0.0, -1.0]) / math.sqrt(2)  # from the cut's middle in to the square corner
        found.append(plate(room, kind, foot, toward, face, (cut * math.sqrt(2), cut / math.sqrt(2), deep), taper=0.0))
    return found


def size_of(kinds, kind, fallback):
    return room_kit.size_of(kinds, kind)[2] if kind in kinds else fallback


def laid_out(room, plan, inventory):
    """Every piece of the room: its walls, windows, floor, ceiling and the rows its inventory places."""
    ceiling = ceiling_of(plan)
    kinds = {row["id"]: row for row in inventory["rows"] if row.get("made") == "kit piece"}
    floor_deep = size_of(kinds, "ring_floor_plate", PLATE_DEEP)
    roof_deep = size_of(kinds, "roof_face_panel", PLATE_DEEP)
    found = walls(room, plan, ceiling) + windows(room, plan)
    found += deck(room, plan, "ring_floor_plate", -floor_deep / 2, UP, floor_deep)
    found += deck(room, plan, "roof_face_panel", ceiling + roof_deep / 2, DOWN, roof_deep)
    return found + room_kit.placed_rows(room, None, kinds, inventory)


def layout(room, plan, inventory):
    """The kit layout the route reads: the room, its frame, its kinds' counts and table, its pieces."""
    pieces = laid_out(room, plan, inventory)
    counts = {}
    for found in pieces:
        counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    return {"room": room, "frame": "the room's own: its middle on its floor, x east, z south, y up (the nose south)",
            "counts": counts, "kinds": room_kit.kinds_table(room, inventory), "pieces": pieces}


def main():
    if len(sys.argv) not in (3, 5):
        raise SystemExit(__doc__)
    room = sys.argv[1]
    plan_path, inventory_path = (sys.argv[3], sys.argv[4]) if len(sys.argv) == 5 else (
        REPO / f"data/plans/{room}.json", REPO / f"data/inventory/{room}.json")
    found = layout(room, json.loads(pathlib.Path(plan_path).read_text()),
                   json.loads(pathlib.Path(inventory_path).read_text()))
    pathlib.Path(sys.argv[2]).write_text(json.dumps(found, indent="\t") + "\n")
    print(len(found["pieces"]), "pieces of", len(found["counts"]), "kinds")


if __name__ == "__main__":
    main()
