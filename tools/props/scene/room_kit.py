"""The kit layout of a rounded module room: where every made piece of a capsule module stands (modules batch one,
2026-10-07: the habitat and the airlock; batch two's rooms take it too). The hub, the one faceted room, has its own
(hub_kit.py).

    python3 tools/props/scene/room_kit.py <room> <out.json>   # writes the laid-out room

The room's numbers are its inventory's (data/inventory/<room>.json, `room.layout`), which are the shell's
(ModuleShell.KIT and ModuleFloors for its kind): the inside's width and depth, how far in from each wall its rounded
corners start, its walls' height, its dome's rise and run, and its door spots. The outline is the shell's own
(ModuleShell.outline: each rounded corner drawn in CORNER_STEPS straight steps), so the kit lines exactly the walls the
shell collides with. Frame: the room's middle on its floor, x east, z south, y up; a wall is named for the way it
faces out (north is -z).

Every piece is laid out as hub_kit.py lays its own: in its kind's frame (as wide as x, as tall as y, as deep as z,
standing on its origin at the middle of its foot, its front toward -z), as its kind (`<room>_<id>`, a row of the
inventory), where its origin stands, its three axes and its size. The route (tools/props/library/route.py) makes a
model for every piece and writes the game's layout, data/kit/<room>.json.

What is laid, and from what:
- walls: every straight run and every step of a rounded corner, a lower band and an upper band of panels about
  PANEL wide (a main wall's featured kinds from `features`), a skirting at the foot and a cornice at the top; a door
  spot's wall leaves its doorway clear;
- the dome: the shell's roof rings (ModuleShell.roof_rings) lined with plates a hand's breadth under the hull, a
  main wall's run in plates about PANEL long, a corner step's as its trapezoid, the flat top in a grid;
- the floor: the cross of the room in a grid of deck plates, each rounded corner a fan of triangles to its middle;
  the mats before the doors set into it (their openings cut through every plate they lie over);
- the side ledges a room's layout names (`ledges`: the lab's, SteppedFloor's 0.42 m rises along its east and west
  walls): their tops in deck plates out to the curved wall, their room edges in riser plates;
- the doors: each door spot's frame, and a tube hatch's leaf, hinges, wheel and window (an airlock door's moving leaf
  is the game's own node, InnerDoor or OuterDoor, which draws its made model); a shut hatch's leaf, wheel and window
  name their door (`door`), so the game hides them when a tube is joined there (HubKit.open_doors);
- the rows the inventory places: furniture on the floor, gear on the walls and the roof, each by its spot.
"""
import json
import math
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hub_kit  # noqa: E402

COMPOSITES = REPO / "data/library/composites.json"
# A pipe run's brackets: the end ones this far in from its ends, the rest at most BRACKET_EVERY apart.
BRACKET_END = 0.25
BRACKET_EVERY = 1.5
# The kinds that run along a wall as a pipe: laid with their axis hub_kit.PIPE_AXIS off the lining (a valve is built
# with its axis there from its back, so it stands on the lining).
PIPE_RUN = {"pipe_straight", "pipe_elbow"}
CORNER_STEPS = 4  # ModuleShell.CORNER_STEPS
ROOF_RINGS = 6  # ModuleShell.ROOF_RINGS
SHELL_WALL = 0.3  # ModuleShell.WALL
ROOF_LAYER = 2  # ModuleShell.ROOF_LAYER
DOORWAY = (2.2, 2.6)  # ModuleDoors.WIDE, ModuleShell.DOOR_HEIGHT
PANEL = 1.2
LOWER = 1.1
LAP = 0.04
BAND_LAP = 0.06
# The dome's plates lie this far under the shell's hull sheet, so no look between them meets the sheet's edge.
ROOF_UNDER = 0.02
FLOOR_CELL = 1.2
# How much wider and taller than the doorway a door's frame is (its posts and header), as the hub's.
FRAME_POSTS = 0.2
FRAME_HEADER = 0.093
LEAF_OVER = 0.06
SET_IN_GAP = 0.004
WALLS = ("east", "north", "west", "south")
# How deep a side ledge is (SteppedFloor.LEDGE_DEEP); its height is the room's (`layout.ledges`).
LEDGE_DEEP = 1.0


def piece(room, kind, origin, axes, size, layer=1):
    x, y, z = axes
    return {"kind": f"{room}_{kind}", "at": [round(float(value), 4) for value in origin],
            "x": [round(float(value), 5) for value in x], "y": [round(float(value), 5) for value in y],
            "z": [round(float(value), 5) for value in z], "size": [round(float(value), 4) for value in size],
            "layer": layer}


def frame_facing(front, up):
    """A piece's axes (x, y, z) for a front looking along `front` with its height along `up`."""
    z = -np.asarray(front, dtype=np.float64)
    z /= np.linalg.norm(z)
    y = np.asarray(up, dtype=np.float64)
    y = y - z * (y @ z)
    y /= np.linalg.norm(y)
    return np.cross(y, z), y, z


def outline(inside, corner, inset=0.0):
    """The room's outline from above as (x, z) points, the shell's own (ModuleShell.outline for a ROUND corner): round
    from the south-east, each corner CORNER_STEPS straight steps, pushed in by `inset`."""
    half = np.asarray(inside, dtype=np.float64) / 2 - inset
    reach = min(max(corner - inset, 0.0), half[0], half[1])
    points = []
    for which, signs in enumerate(((1, 1), (1, -1), (-1, -1), (-1, 1))):
        middle = np.array(signs) * (half - reach)
        start = math.radians(90.0 - 90.0 * which)
        for step in range(CORNER_STEPS + 1):
            angle = start - math.pi / 2 * step / CORNER_STEPS
            points.append(middle + np.array([math.cos(angle), math.sin(angle)]) * reach)
    return points


def sides(layout):
    """Every wall round the room in the outline's order: its name (a main wall's direction, a corner step's
    `corner<n>`), its two ends (x, z) and its outward normal."""
    points = outline(layout["inside"], layout["corner"])
    per_corner = CORNER_STEPS + 1
    found = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        if np.linalg.norm(end - start) < 0.01:
            continue
        main = index % per_corner == per_corner - 1
        along = (end - start) / np.linalg.norm(end - start)
        outward = np.array([along[1], -along[0]])  # the outline runs with the outside on its left
        if outward @ ((start + end) / 2) < 0:
            outward = -outward
        found.append({"name": WALLS[index // per_corner] if main else f"corner{index}", "start": start, "end": end,
                      "outward": outward, "main": main})
    return found


def side_named(layout, name):
    return next(side for side in sides(layout) if side["name"] == name)


def on_side(room, kind, side, across, bottom, size, out=0.0, layer=1):
    """A piece against a wall's inside face (or `out` in front of it), `across` from the wall's middle along it (toward
    its end), its foot `bottom` up, facing into the room."""
    middle = (side["start"] + side["end"]) / 2
    along = (side["end"] - side["start"]) / np.linalg.norm(side["end"] - side["start"])
    wide, tall, deep = size
    flat = middle + along * across - side["outward"] * (out + deep / 2)
    origin = np.array([flat[0], bottom, flat[1]])
    inward = np.array([-side["outward"][0], 0.0, -side["outward"][1]])
    return piece(room, kind, origin, frame_facing(inward, (0, 1, 0)), size, layer)


def spans(length, door):
    """A wall's runs left of its doorway and right of it, as (middle, length) along the wall; the whole wall when it
    has no doorway."""
    if not door:
        return [(0.0, length)]
    side = (length - DOORWAY[0]) / 2
    return [(-length / 2 + side / 2, side), (length / 2 - side / 2, side)]


def size_of(kinds, kind):
    """A kind's size in its frame (wide, tall, deep) from its row's (wide, deep, tall)."""
    wide, deep, tall = kinds[kind]["size"]
    return wide, tall, deep


def walls(room, layout, kinds):
    """Every wall's two bands of panels, its skirting and its cornice."""
    found = []
    high = layout["wall"]
    for side in sides(layout):
        length = float(np.linalg.norm(side["end"] - side["start"]))
        door = side["main"] and side["name"] in layout["doors"]
        featured = layout.get("features", {}).get(side["name"], {}) if side["main"] else {}
        lower = featured.get("lower", "wall_lower_plain")
        upper = featured.get("upper", "wall_upper_plain")
        for middle, run in spans(length, door):
            count = max(1, round(run / PANEL))
            wide = run / count
            for index in range(count):
                across = middle - run / 2 + wide * (index + 0.5)
                found.append(on_side(room, lower, side, across, 0.0, (wide + LAP, LOWER + BAND_LAP,
                                                                      size_of(kinds, lower)[2])))
                found.append(on_side(room, upper, side, across, LOWER, (wide + LAP, high - LOWER, size_of(kinds, upper)[2])))
            skirting = size_of(kinds, "wall_skirting")
            found.append(on_side(room, "wall_skirting", side, middle, 0.0, (run, skirting[1], skirting[2]),
                                 out=size_of(kinds, lower)[2]))
        cornice = size_of(kinds, "wall_cornice")
        found.append(on_side(room, "wall_cornice", side, 0.0, high - cornice[1], (length + LAP, cornice[1], cornice[2])))
    return found


def roof_profile(layout):
    """The dome's rings as (inset from the walls' inside face, height above the floor), the hull sheet's
    (ModuleShell.roof_rings: the sheet starts over the walls' middle line) pushed ROOF_UNDER plus the plates' depth
    under it, square to the sheet."""
    half = min(layout["inside"]) / 2
    run = min(layout["run"], half - 0.3)
    sheet = [(-SHELL_WALL / 2 + run * (1 - math.cos(math.pi / 2 * step / ROOF_RINGS)),
              layout["wall"] + layout["rise"] * math.sin(math.pi / 2 * step / ROOF_RINGS))
             for step in range(ROOF_RINGS + 1)]
    found = []
    for index, (inset, high) in enumerate(sheet):
        before = sheet[max(index - 1, 0)]
        after = sheet[min(index + 1, len(sheet) - 1)]
        slope = np.array([after[0] - before[0], after[1] - before[1]])
        slope /= np.linalg.norm(slope)
        under = np.array([slope[1], -slope[0]])  # in (inset, height): further in and lower
        if under[1] > 0:
            under = -under
        found.append((inset + under[0] * ROOF_UNDER, high + under[1] * ROOF_UNDER, under))
    return found


def roof(room, layout, kinds):
    """The dome lined with plates between every two of its rings: a main wall's run in plates about PANEL long, each
    corner step's as one trapezoid; and its flat top in a grid."""
    found = []
    deep = size_of(kinds, "roof_face_panel")[2]
    profile = roof_profile(layout)
    for low, high in zip(profile, profile[1:]):
        low_points = outline(layout["inside"], layout["corner"], low[0])
        high_points = outline(layout["inside"], layout["corner"], high[0])
        for index in range(len(low_points)):
            following = (index + 1) % len(low_points)
            a, b = low_points[index], low_points[following]
            c, d = high_points[index], high_points[following]
            bottom = float(np.linalg.norm(b - a))
            if bottom < 0.01:
                continue
            main = index % (CORNER_STEPS + 1) == CORNER_STEPS
            pieces = max(1, round(bottom / PANEL)) if main else 1
            for part in range(pieces):
                share = (part / pieces, (part + 1) / pieces)
                foot = [a + (b - a) * share[0], a + (b - a) * share[1]]
                head = [c + (d - c) * share[0], c + (d - c) * share[1]]
                found.append(roof_plate(room, foot, head, low[1], high[1], low[2], deep))
    top = profile[-1]
    top_points = outline(layout["inside"], layout["corner"], top[0])
    low_corner = np.min(top_points, axis=0)
    high_corner = np.max(top_points, axis=0)
    size = high_corner - low_corner
    counts = [max(1, round(value / (2 * PANEL))) for value in size]
    cell = size / counts
    for across in range(counts[0]):
        for along in range(counts[1]):
            middle = low_corner + cell * (np.array([across, along]) + 0.5)
            origin = np.array([middle[0], top[1], middle[1] - cell[1] / 2])
            found.append(piece(room, "roof_face_panel", origin + np.array([0.0, -deep / 2, 0.0]),
                               (np.array([-1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), np.array([0.0, 1.0, 0.0])),
                               (cell[0], cell[1], deep), ROOF_LAYER))
            found[-1]["taper"] = 1.0
    return found


def roof_plate(room, foot, head, low_high, high_high, under, deep):
    """One plate of the dome between two rings: its foot on the lower ring, its head on the upper, its front down into
    the room, its back ROOF_UNDER under the hull; laid as a trapezoid (`taper`: its head's width over its foot's)."""
    foot3 = [np.array([point[0], low_high, point[1]]) for point in foot]
    head3 = [np.array([point[0], high_high, point[1]]) for point in head]
    foot_middle = (foot3[0] + foot3[1]) / 2
    head_middle = (head3[0] + head3[1]) / 2
    across = foot3[1] - foot3[0]
    wide = float(np.linalg.norm(across))
    across /= wide
    up = head_middle - foot_middle
    up -= across * (up @ across)
    tall = float(np.linalg.norm(up))
    up /= tall
    front = np.cross(up, across)
    if front[1] > 0 or (abs(front[1]) < 1e-6 and front @ np.array([foot_middle[0], 0.0, foot_middle[2]]) > 0):
        front = -front
    z = -front
    laid = piece(room, "roof_face_panel", foot_middle + front * deep / 2, (np.cross(up, z), up, z), (wide, tall, deep),
                 ROOF_LAYER)
    laid["taper"] = round(float(np.linalg.norm(head3[1] - head3[0])) / wide, 4)
    return laid


def floor(room, layout, kinds):
    """The floor: the room's cross (its full width between the corners' ends, its full depth between them) in a grid
    of deck plates about FLOOR_CELL across, and each rounded corner a fan of triangles to the corner's middle."""
    found = []
    deep = size_of(kinds, "ring_floor_plate")[2]
    half = np.asarray(layout["inside"], dtype=np.float64) / 2
    reach = layout["corner"]
    for low, high in (((-half[0], -(half[1] - reach)), (half[0], half[1] - reach)),
                      ((-(half[0] - reach), -half[1]), (half[0] - reach, -(half[1] - reach))),
                      ((-(half[0] - reach), half[1] - reach), (half[0] - reach, half[1]))):
        size = np.array(high) - np.array(low)
        counts = [max(1, round(value / FLOOR_CELL)) for value in size]
        cell = size / counts
        for across in range(counts[0]):
            for along in range(counts[1]):
                corner = np.array(low) + cell * np.array([across, along])
                origin = np.array([corner[0] + cell[0] / 2, -deep / 2, corner[1]])
                laid = piece(room, "ring_floor_plate", origin,
                             (np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), np.array([0.0, -1.0, 0.0])),
                             (cell[0], cell[1], deep))
                laid["taper"] = 1.0
                found.append(laid)
    for signs in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        middle = np.array(signs) * (half - reach)
        for step in range(CORNER_STEPS):
            angles = [math.pi / 2 * step / CORNER_STEPS, math.pi / 2 * (step + 1) / CORNER_STEPS]
            ends = [middle + np.array(signs) * np.array([math.sin(angle), math.cos(angle)]) * reach for angle in angles]
            chord_middle = (ends[0] + ends[1]) / 2
            toward = middle - chord_middle
            tall = float(np.linalg.norm(toward))
            toward /= tall
            y = np.array([toward[0], 0.0, toward[1]])
            z = np.array([0.0, -1.0, 0.0])  # its front up
            x = np.cross(y, z)
            laid = piece(room, "ring_floor_plate", np.array([chord_middle[0], -deep / 2, chord_middle[1]]), (x, y, z),
                         (float(np.linalg.norm(ends[1] - ends[0])), tall, deep))
            laid["taper"] = 0.0
            found.append(laid)
    return found


def doors(room, layout, kinds):
    """Every door spot's frame round its doorway; a tube hatch's leaf, wheel and window shut in it (open ones swung
    out of the room into what joins there) and its two hinges; an airlock door (`door` kind) only its frame, its leaf
    being the game's moving node."""
    found = []
    for name, kind in layout["doors"].items():
        side = side_named(layout, name)
        # A tube hatch's frame is the hub's door kit's, fitted round the doorway; an airlock door's heavy frame is as
        # its row is sized (as wide as its wall's run, its stripes round the doorway).
        frame = (DOORWAY[0] + FRAME_POSTS, DOORWAY[1] + FRAME_HEADER, size_of(kinds, f"{kind}_frame")[2]) \
            if kind == "hatch" else size_of(kinds, f"{kind}_frame")
        found.append(on_side(room, f"{kind}_frame", side, 0.0, 0.0, frame))
        if kind != "hatch":
            continue
        leaf = (DOORWAY[0] + LEAF_OVER, DOORWAY[1] + LEAF_OVER, size_of(kinds, "hatch_leaf")[2])
        if name not in layout.get("open", ()):
            out = frame[2]
            found.append(on_side(room, "hatch_leaf", side, 0.0, 0.0, leaf, out=out - leaf[2]))
            wheel = size_of(kinds, "hatch_wheel")
            found.append(on_side(room, "hatch_wheel", side, 0.0, 1.15 - wheel[1] / 2, wheel, out=out))
            window = size_of(kinds, "hatch_window")
            found.append(on_side(room, "hatch_window", side, 0.0, 1.85 - window[1] / 2, window, out=out - window[2] / 2))
            # The shut leaf's pieces name their door, so the game hides them once a tube is joined there and the
            # shell opens that doorway (HubKit.open_doors; a module placed with the building tool, the lab).
            for shut in found[-3:]:
                shut["door"] = name
        hinge = size_of(kinds, "hatch_hinge")
        for high in (0.5, 2.0):
            found.append(on_side(room, "hatch_hinge", side, -leaf[0] / 2 - hinge[0] / 2, high, hinge, out=frame[2]))
    return found


LEDGE_STRIPS = 8  # strips a ledge's top is laid in where it runs into a rounded corner


def ledges(room, layout, kinds):
    """The side ledges (SteppedFloor: LEDGE_DEEP deep along a wall, `layout.ledges` names each wall and its top): the
    top in deck plates, where the wall runs straight one plate a PANEL or so, and into each rounded corner strips
    reaching the curved wall (their outer ends go behind the wall's panels, as the shell clips its ledge), and the
    riser along the ledge's room edge in riser plates (`pit_wall_panel`), each facing into the room."""
    found = []
    if not layout.get("ledges"):
        return found
    half = np.asarray(layout["inside"], dtype=np.float64) / 2
    reach = layout["corner"]
    plate = size_of(kinds, "ring_floor_plate")[2]
    riser = size_of(kinds, "pit_wall_panel")[2]
    for name, top in layout.get("ledges", {}).items():
        sign = 1.0 if name == "east" else -1.0  # a ledge runs along an east or a west wall
        inner = sign * (half[0] - LEDGE_DEEP)
        straight = half[1] - reach
        middle = sign * (half[0] - LEDGE_DEEP / 2)
        tops = [(middle, -straight + straight * 2 * (index + 0.5) / max(1, round(2 * straight / PANEL)),
                 LEDGE_DEEP, 2 * straight / max(1, round(2 * straight / PANEL)))
                for index in range(max(1, round(2 * straight / PANEL)))]
        ends = []
        for end in (-1.0, 1.0):
            for strip in range(LEDGE_STRIPS):
                near = straight + (reach * strip / LEDGE_STRIPS)
                far = straight + (reach * (strip + 1) / LEDGE_STRIPS)
                # The corner's arc: centre (half - reach) on both axes; its x at the strip's nearer z, where it is widest.
                across = half[0] - reach + math.sqrt(max(reach ** 2 - (near - straight) ** 2, 0.0))
                wide = across - (half[0] - LEDGE_DEEP)
                if wide <= 0.02:
                    continue
                tops.append((sign * (half[0] - LEDGE_DEEP + wide / 2), end * (near + far) / 2, wide, far - near))
                ends.append(end * far)
        for across, along, wide, long in tops:
            origin = np.array([across, top - plate / 2, along - long / 2])
            laid = piece(room, "ring_floor_plate", origin,
                         (np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), np.array([0.0, -1.0, 0.0])),
                         (wide, long, plate))
            laid["taper"] = 1.0
            found.append(laid)
        # The riser along the room edge, from corner arc to corner arc (where the arc meets the ledge's inner line).
        span = straight + math.sqrt(max(reach ** 2 - (reach - LEDGE_DEEP) ** 2, 0.0))
        count = max(1, round(2 * span / PANEL))
        inward = np.array([-sign, 0.0, 0.0])
        for index in range(count):
            along = -span + 2 * span * (index + 0.5) / count
            origin = np.array([inner - sign * riser / 2, 0.0, along])
            found.append(piece(room, "pit_wall_panel", origin, frame_facing(inward, (0, 1, 0)),
                               (2 * span / count, top, riser)))
    return found


def lining(layout, kinds, side_name, low, high):
    """How far the wall panels behind a span of a wall's height stand out of it: the deepest of them."""
    featured = layout.get("features", {}).get(side_name, {})
    found = []
    if low < LOWER:
        found.append(size_of(kinds, featured.get("lower", "wall_lower_plain"))[2])
    if high > LOWER:
        found.append(size_of(kinds, featured.get("upper", "wall_upper_plain"))[2])
    return max(found)


def placed_rows(room, layout, kinds, inventory):
    """Every row the inventory places by its spots: on a wall (`wall`, `across`, `bottom`: against the wall's panels,
    `out` further), on the floor or hung from the roof (`x`, `y`, `z`, `facing`: its foot's middle and the bearing its
    front looks toward), or on another row's piece (`on`: the same, its foot `y` up)."""
    found = []
    for row in inventory["rows"]:
        if row.get("made") != "kit piece" or row.get("lies") == "floor":
            continue
        size = size_of(kinds, row["id"])
        for spot in row.get("at", []):
            spot_size = tuple(spot.get("size", size))
            if "wall" in spot:
                side = side_named(layout, spot["wall"])
                behind = lining(layout, kinds, spot["wall"], spot["bottom"], spot["bottom"] + spot_size[1])
                if row["id"] in PIPE_RUN:
                    behind += hub_kit.PIPE_AXIS - spot_size[2] / 2
                laid = on_side(room, row["id"], side, spot["across"], spot["bottom"], spot_size,
                               out=behind + spot.get("out", 0.0), layer=spot.get("layer", 1))
            else:
                bearing = math.radians(spot["facing"])
                front = np.array([math.sin(bearing), 0.0, -math.cos(bearing)])
                laid = piece(room, row["id"], np.array([spot["x"], spot["y"], spot["z"]]), frame_facing(front, (0, 1, 0)),
                             spot_size, spot.get("layer", 1))
            if spot.get("set_in"):
                laid["set_in"] = True
            # What a composite parent's own build shows (a tool board's tools and their outlines), made with it.
            parent_shows = composites().get(f"{room}_{row['id']}", {}).get("laid")
            if parent_shows:
                laid["shows"] = parent_shows
            found.append(laid)
    return found


def flat_rows(room, inventory, kinds):
    """The rows that lie flat on the floor, front up (a mat), by their spots' middle and `facing` (the bearing their
    width runs square to)."""
    found = []
    for row in inventory["rows"]:
        if row.get("made") != "kit piece" or row.get("lies") != "floor":
            continue
        wide, tall, deep = size_of(kinds, row["id"])
        for spot in row.get("at", []):
            bearing = math.radians(spot["facing"])
            front = np.array([math.sin(bearing), 0.0, -math.cos(bearing)])
            across = np.cross(np.array([0.0, 1.0, 0.0]), front)
            origin = np.array([spot["x"], deep / 2 - deep, spot["z"]]) - front * tall / 2
            laid = piece(room, row["id"], origin, (across, front, np.array([0.0, -1.0, 0.0])), (wide, tall, deep))
            laid["set_in"] = True
            found.append(laid)
    return found


def box_corners(laid):
    origin = np.asarray(laid["at"])
    x, y, z = (np.asarray(laid[axis]) for axis in ("x", "y", "z"))
    wide, tall, deep = laid["size"]
    return np.array([origin + x * a * wide / 2 + y * b * tall + z * c * deep / 2
                     for a in (-1, 1) for b in (0, 1) for c in (-1, 1)])


def cut_openings(room, found):
    """Every set-in fitting's opening cut through each floor plate it lies over (the plate's `openings`: rectangles in
    its own frame, x and y, low then high, clipped to the plate), the fitting's face flush with the plates' faces."""
    plates = [laid for laid in found if laid["kind"] == f"{room}_ring_floor_plate"]
    for fitting in (laid for laid in found if laid.get("set_in")):
        corners = box_corners(fitting)
        hosts = 0
        for plate in plates:
            origin = np.asarray(plate["at"])
            axes = np.array([plate["x"], plate["y"]])
            local = (corners - origin) @ axes.T
            low, high = local.min(axis=0) - SET_IN_GAP, local.max(axis=0) + SET_IN_GAP
            wide, tall, _ = plate["size"]
            low = np.maximum(low, [-wide / 2, 0.0])
            high = np.minimum(high, [wide / 2, tall])
            if np.any(high - low <= 0.01):
                continue
            plate.setdefault("openings", []).append([round(float(value), 4) for value in (*low, *high)])
            hosts += 1
        if not hosts:
            raise SystemExit(f"{fitting['kind']} at {fitting['at']} lies over no floor plate")
    return found


def own(laid):
    """A laid piece's kind without its room's prefix."""
    return laid["kind"].split("_", 1)[1]


def pipe_brackets(room, kinds, found):
    """A bracket on every wall pipe run (the round-six route's pipe runs, as the hub's): one near each end and one at
    least every BRACKET_EVERY between, the base on the wall and the clamp round the pipe (pieces.pipe_bracket); the
    layout's split moves any that would stand on a valve."""
    if "pipe_bracket" not in kinds:
        return []
    bracket = size_of(kinds, "pipe_bracket")
    brackets = []
    for pipe in (laid for laid in found if own(laid) == "pipe_straight"):
        length = pipe["size"][0]
        count = max(2, math.ceil(length / BRACKET_EVERY) + 1)
        along = np.asarray(pipe["x"])
        back = np.asarray(pipe["z"])
        # The pipe's axis, back to the wall's lining, then the bracket's own frame standing on the lining there.
        axis = np.asarray(pipe["at"]) + np.asarray(pipe["y"]) * pipe["size"][1] / 2
        wall = axis + back * hub_kit.PIPE_AXIS
        for index in range(count):
            shift = -length / 2 + BRACKET_END + (length - 2 * BRACKET_END) * index / (count - 1)
            foot = wall + along * shift - back * bracket[2] / 2 - np.asarray(pipe["y"]) * bracket[1] / 2
            brackets.append(piece(room, "pipe_bracket", foot, (pipe["x"], pipe["y"], pipe["z"]), bracket))
    return brackets


def under_floor(room, kinds, found):
    """The duct or trough under every set-in grating or hatch (hub_kit.UNDER_FLOOR), as the hub's: an open box of
    plates as wide and long as the opening and its lip, from under the deck plates down; the shell opens its deck over
    each (HubKit.floor_openings)."""
    if "under_floor_box" not in kinds:
        return []
    plate = size_of(kinds, "ring_floor_plate")[2]
    boxes = []
    for fitting in (laid for laid in found if laid.get("set_in") and own(laid) in hub_kit.UNDER_FLOOR):
        wide, long, _ = fitting["size"]
        middle = box_corners(fitting).mean(axis=0)
        size = (wide + 2 * hub_kit.UNDER_LIP, long + 2 * hub_kit.UNDER_LIP, hub_kit.UNDER_FLOOR[own(fitting)])
        across = np.asarray(fitting["y"])
        origin = np.array([middle[0], -plate - size[2] / 2, middle[2]]) - across * size[1] / 2
        boxes.append(piece(room, "under_floor_box", origin, (fitting["x"], fitting["y"], fitting["z"]), size))
    return boxes


def composites():
    """data/library/composites.json: every composite's children and what its own build shows."""
    return json.loads(COMPOSITES.read_text()) if COMPOSITES.exists() else {}


def children(room, found):
    """Every composite's children (data/library/composites.json), one model per real-world object, laid as kit pieces
    of their own kinds on their parent: a child's `at` is its foot's middle in the parent's frame, `turn` its turn
    about the parent's up (as route.child_transform places a furniture prop's children)."""
    placed = []
    for parent in found:
        for child in composites().get(parent["kind"], {}).get("children", []):
            axes = [np.asarray(parent[axis]) for axis in ("x", "y", "z")]
            angle = math.radians(child.get("turn", 0.0))
            x = axes[0] * math.cos(angle) - axes[2] * math.sin(angle)
            z = axes[0] * math.sin(angle) + axes[2] * math.cos(angle)
            origin = np.asarray(parent["at"]) + sum(axis * value for axis, value in zip(axes, child["at"]))
            laid = piece(room, child["kind"].split("_", 1)[1], origin, (x, axes[1], z), child["size"],
                         parent.get("layer", 1))
            laid["child_of"] = parent["kind"]
            if child.get("laid"):  # what this child shows (a monitor's screen, a tool's solid tip)
                laid["shows"] = child["laid"]
            placed.append(laid)
    return placed


def laid_out(room, inventory):
    layout = inventory["room"]["layout"]
    kinds = {row["id"]: row for row in inventory["rows"] if row.get("made") == "kit piece"}
    found = walls(room, layout, kinds) + floor(room, layout, kinds) + ledges(room, layout, kinds) + doors(room, layout, kinds)
    if layout.get("rise"):
        found += roof(room, layout, kinds)
    found += placed_rows(room, layout, kinds, inventory) + flat_rows(room, inventory, kinds)
    found += pipe_brackets(room, kinds, found) + under_floor(room, kinds, found)
    found = hub_kit.split_at_fittings(found)
    return cut_openings(room, found + children(room, found))


# What each piece is to the scene check (resting.gd) and to the game: the floors other things rest on, what hangs
# from a wall or the roof, what is solid (furniture the player walks round: RoomKit gives it a box that collides),
# and what lights (a real lamp each).
FLOORS = {"ring_floor_plate", "roof_face_panel"}
HANGING_GROUPS = {"wall", "ceiling", "door", "pipe", "sign", "screen", "light", "vent"}


def kinds_table(room, inventory):
    """Every kind's light, group and solidity, for RoomKit and the scene check."""
    table = {}
    for row in inventory["rows"]:
        if row.get("made") != "kit piece":
            continue
        about = {}
        if "light" in row:
            about["light"] = row["light"]
        if row["id"] in FLOORS:
            about["group"] = "floors"
        elif row.get("group", "").removeprefix("kit: ") in HANGING_GROUPS:
            about["group"] = "hangs"
        if row.get("solid"):
            about["solid"] = True
        if row.get("anchor") == "roof":  # stands on the roof, outside the shell (the airlock's beacon)
            about["outside"] = True
        table[f"{room}_{row['id']}"] = about
    return table


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    room = sys.argv[1]
    inventory = json.loads((REPO / f"data/inventory/{room}.json").read_text())
    pieces = laid_out(room, inventory)
    counts = {}
    for found in pieces:
        counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    pathlib.Path(sys.argv[2]).write_text(json.dumps(
        {"room": room, "frame": "the room's own: its middle on its floor, x east, z south, y up", "counts": counts,
         "kinds": kinds_table(room, inventory), "pieces": pieces}, indent="\t") + "\n")
    print(len(pieces), "pieces of", len(counts), "kinds")


if __name__ == "__main__":
    main()
