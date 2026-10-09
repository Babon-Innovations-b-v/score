"""The greenhouse's kit layout (world 1 place job, 2026-10-07): room_kit's capsule room (its lined walls, doors, wall
gear, pipe runs and composites) with what only the greenhouse has. The concept (K09) lines its walls to the dome and
glazes only the dome, so the walls are room_kit's; then:

- the glass dome: no plates, a frame of ribs up it and hoops round it (lattice kinds) on the shell's own rings
  (ModuleShell.roof_rings, room_kit.roof_profile), a node plate where they meet; the shell's roof sheet is the glass;
- the floor's rises (SteppedFloor for the greenhouse: the north dais either side of the aisle with its three steps,
  the ledges along the east, west and south walls broken at each door spot with a half step, the east doorway's step):
  a deck top or a ledge cover on each, a face panel on every side that stands over its neighbour, the rounded corners
  a fan at the rise's height; the floor's deck plates only where nothing rises and the plot does not lie;
- the home plot's robot station (PlotField's spots: each bay's dock pad and charge post, the seed bin, the soil bin
  and the crop crate), laid where the game draws its live fills inside them;
- the grow-light gantry over the plot (GreenhouseRig's spots): a light bar and its lit lens over each quarter of the
  plot in four lengths, two rails across them, hangers up to the dome, an irrigation boom beside each bar, and the
  main from the tank on the dais.

    python3 tools/props/scene/greenhouse_kit.py <out.json>

Frame: the room's middle on its floor, x east, z south, y up (room_kit's).
"""
import json
import math
import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import hub_kit  # noqa: E402
import room_kit  # noqa: E402
from room_kit import piece  # noqa: E402

ROOM = "greenhouse"
HALF = np.array([8.0, 9.0])  # ModuleFloors: 16 x 18 m inside
CORNER = 1.2
# SteppedFloor's numbers for the greenhouse (sim/base/stepped_floor.gd).
LEDGE_HIGH, LEDGE_DEEP, LEDGE_STEP_DEEP = 0.42, 1.0, 0.35
DAIS_HIGH, DAIS_DEEP, DAIS_STEPS, STEP_DEEP = 0.9, 2.0, 3, 0.35
AISLE_WIDE = 2.4
DOOR_STEP_HIGH, DOOR_STEP_DEEP, DOOR_WIDE = 0.18, 0.5, 2.2
OPEN_WALLS = ("east",)  # SteppedFloor.STARTING_DOORS: the greenhouse joins the west corridor by its east door
# The home plot (HomePlot, PlotField): its beds from -6 to 6 across and -7 to 5 along, its near wall to the south;
# PlotField stands at (-5.7, 4.7) on the room's floor, the middle of bed (0, 0).
PLOT = (-6.0, 6.0, -7.0, 5.0)
FIELD = np.array([-5.7, 4.7])
BED = 0.6
WALL_GAP, WALL_THICK = 0.22, 0.06  # PlotField: the low wall round the beds
BAYS, ENTRY_SPACING = 3, 2  # RobotHub.BAYS, RobotRecord.ENTRY_SPACING
PAD = (1.0, 0.04, 0.9)  # PlotField.PAD
PAD_OFF_WALL = 0.08
BAR_FRAME = (0.1, 0.62, 0.06)  # PlotField.BAR_FRAME
BINS_FROM, BIN_SPACING = 1.2, 1.05
BINS = (("seed_bin", (0.55, 0.8, 0.6)), ("soil_bin", (0.9, 0.45, 0.7)), ("crop_crate", (0.8, 0.55, 0.7)))
PADS = ("dock_pad_one", "dock_pad_two", "dock_pad_three")
# GreenhouseRig: a bar over each quarter of the plot, its housing's foot BAR_FOOT up; the boom BOOM_OFF east of it.
BAR_FOOT = 3.15
BAR_PIECES = 4
BOOM_OFF = 0.32
LENS_UP = 0.004  # the lens's foot over the bar's foot: set into the housing's recess, its face just inside it
RAILS_AT = (-4.0, 2.0)  # along: where the two rails cross the bars, at the joins of their lengths
HANGERS_AT = (-4.5, 0.0, 4.5)
MAIN_ALONG = -7.45  # the irrigation main runs across north of the plot
TANK = (-5.0, -8.05)  # the water tank on the west dais (its inventory spot), the main comes down into it
TANK_TOP = DAIS_HIGH + 1.6
# How far a rise's top or face stands back from a wall: the lining's depth, so no plate runs into a wall panel.
LINING = 0.06
FACE_DEEP = 0.04  # a rise's face panel, set into the rise so its front is flush with the rise's side
FLOOR_PIECE = 1.25  # deck plates and covers at most this long
RIB_EVERY = 2.4  # the dome's ribs about this far apart along a main wall
RIB, HOOP, NODE = (0.12, 0.12), (0.1, 0.1), (0.26, 0.26, 0.05)
RIB_UNDER = 0.03  # the frame's back this far under the glass sheet
CORNICE_DEEP = 0.16  # the wall cornice's depth (its inventory row): the dome's frame starts on its inner edge


# --- the floor's rises ---------------------------------------------------------------------------------------------

def rect(x0, x1, z0, z1, top, part):
    return {"x": (min(x0, x1), max(x0, x1)), "z": (min(z0, z1), max(z0, z1)), "top": top, "part": part}


def rises():
    """SteppedFloor.rises_of for the greenhouse, as rectangles on the room's floor: the dais and its steps, the
    ledges and their half steps, the open door's step."""
    found = []
    cut = AISLE_WIDE / 2 + STEP_DEEP * DAIS_STEPS
    for side in (-1, 1):
        found.append(rect(cut * side, HALF[0] * side, -HALF[1], -HALF[1] + DAIS_DEEP, DAIS_HIGH, "dais"))
        for step in range(DAIS_STEPS):
            inner, outer = (AISLE_WIDE / 2 + STEP_DEEP * step) * side, (AISLE_WIDE / 2 + STEP_DEEP * (step + 1)) * side
            found.append(rect(inner, outer, -HALF[1], -HALF[1] + DAIS_DEEP,
                              DAIS_HIGH * (step + 1) / (DAIS_STEPS + 1), "dais_step"))
    gap = AISLE_WIDE / 2
    for wall in ("east", "west", "south"):
        half = HALF[1] if wall != "south" else HALF[0]
        start = -half + DAIS_DEEP if wall != "south" else -half
        spans = [(start, -gap - LEDGE_STEP_DEEP), (gap + LEDGE_STEP_DEEP, half)]
        for low, high in spans:
            found.append(against(wall, low, high, LEDGE_DEEP, LEDGE_HIGH, "ledge"))
        for side in (-1, 1):
            found.append(against(wall, gap * side, (gap + LEDGE_STEP_DEEP) * side, LEDGE_DEEP, LEDGE_HIGH / 2,
                                 "ledge_step"))
    for wall in OPEN_WALLS:
        found.append(against(wall, -DOOR_WIDE / 2, DOOR_WIDE / 2, DOOR_STEP_DEEP, DOOR_STEP_HIGH, "door_step"))
    return found


def against(wall, start, end, deep, top, part):
    """SteppedFloor._against: a rectangle against the inside of a wall, `start` to `end` along it (across for a north
    or south wall, along for an east or west one), `deep` into the room."""
    if wall == "north":
        return rect(start, end, -HALF[1], -HALF[1] + deep, top, part)
    if wall == "south":
        return rect(start, end, HALF[1] - deep, HALF[1], top, part)
    if wall == "east":
        return rect(HALF[0] - deep, HALF[0], start, end, top, part)
    return rect(-HALF[0], -HALF[0] + deep, start, end, top, part)


def top_at(found, x, z):
    """How high the floor stands at a place: the highest rise over it, or the floor."""
    return max([0.0] + [rise["top"] for rise in found if rise["x"][0] <= x <= rise["x"][1] and
                        rise["z"][0] <= z <= rise["z"][1]])


def in_corner(x, z):
    """Whether a place lies in one of the rounded corners' squares (outside the cross the corners leave)."""
    return abs(x) > HALF[0] - CORNER and abs(z) > HALF[1] - CORNER


def inside_room(x, z, margin=0.0):
    """Whether a place is inside the room's rounded outline, `margin` in from it."""
    if abs(x) > HALF[0] - margin or abs(z) > HALF[1] - margin:
        return False
    if not in_corner(x, z):
        return True
    middle = np.array([math.copysign(HALF[0] - CORNER, x), math.copysign(HALF[1] - CORNER, z)])
    return float(np.linalg.norm(np.array([x, z]) - middle)) <= CORNER - margin


def lying(kind, low, high, top, deep):
    """A piece lying flat with its face up, over the rectangle low..high (x, z), its face at `top`: its width along x,
    its length along z (room_kit's floor plates' frame: y along the floor, z down)."""
    wide, long = high[0] - low[0], high[1] - low[1]
    origin = np.array([(low[0] + high[0]) / 2, top - deep / 2, low[1]])
    laid = piece(ROOM, kind, origin, (np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]), np.array([0.0, -1.0, 0.0])),
                 (wide, long, deep))
    laid["taper"] = 1.0
    return laid


def tiles(low, high, longest=FLOOR_PIECE):
    """A rectangle cut into equal pieces at most `longest` each way."""
    counts = [max(1, math.ceil((high[axis] - low[axis]) / longest - 1e-6)) for axis in range(2)]
    step = [(high[axis] - low[axis]) / counts[axis] for axis in range(2)]
    for across in range(counts[0]):
        for along in range(counts[1]):
            start = (low[0] + step[0] * across, low[1] + step[1] * along)
            yield start, (start[0] + step[0], start[1] + step[1])


def clear_of_walls(low, high):
    """A rectangle pulled in from any wall it reaches by the lining's depth."""
    low, high = list(low), list(high)
    for axis in range(2):
        if low[axis] <= -HALF[axis] + 1e-6:
            low[axis] = -HALF[axis] + LINING
        if high[axis] >= HALF[axis] - 1e-6:
            high[axis] = HALF[axis] - LINING
    return low, high


def corner_fan(signs, top, kind, deep):
    """A rounded corner's floor at `top`: a fan of triangles to the corner's middle (room_kit.floor's, raised and
    pulled in by the lining)."""
    found = []
    reach = CORNER - LINING
    middle = np.array(signs) * (HALF - CORNER)
    for step in range(room_kit.CORNER_STEPS):
        angles = [math.pi / 2 * step / room_kit.CORNER_STEPS, math.pi / 2 * (step + 1) / room_kit.CORNER_STEPS]
        ends = [middle + np.array(signs) * np.array([math.sin(angle), math.cos(angle)]) * reach for angle in angles]
        chord = (ends[0] + ends[1]) / 2
        toward = middle - chord
        tall = float(np.linalg.norm(toward))
        toward /= tall
        y = np.array([toward[0], 0.0, toward[1]])
        z = np.array([0.0, -1.0, 0.0])
        laid = piece(ROOM, kind, np.array([chord[0], top - deep / 2, chord[1]]), (np.cross(y, z), y, z),
                     (float(np.linalg.norm(ends[1] - ends[0])), tall, deep))
        laid["taper"] = 0.0
        found.append(laid)
    return found


def rise_tops(found_rises, kinds):
    """Every rise's top: deck plates on the dais, its steps and the door step, ledge covers on the ledges; a corner's
    square at the rise's height as a fan."""
    laid = []
    plate = room_kit.size_of(kinds, "ring_floor_plate")[2]
    cover = room_kit.size_of(kinds, "ledge_cover")[2]
    fans = set()
    for rise in found_rises:
        kind, deep = ("ledge_cover", cover) if rise["part"] == "ledge" else ("ring_floor_plate", plate)
        for low, high in split_off_corners(rise):
            low, high = clear_of_walls(low, high)
            if high[0] - low[0] < 0.02 or high[1] - low[1] < 0.02:
                continue
            longest = 1.3 if kind == "ledge_cover" else FLOOR_PIECE
            for piece_low, piece_high in tiles(low, high, longest):
                laid.append(lying(kind, piece_low, piece_high, rise["top"], deep))
        for signs in corner_signs(rise):
            if signs not in fans:
                fans.add(signs)
                laid += corner_fan(signs, rise["top"], "ring_floor_plate", plate)
    return laid


def corner_signs(rise):
    """The rounded corners whose square a rise covers."""
    found = []
    for signs in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
        corner_x = sorted((signs[0] * (HALF[0] - CORNER), signs[0] * HALF[0]))
        corner_z = sorted((signs[1] * (HALF[1] - CORNER), signs[1] * HALF[1]))
        if rise["x"][0] <= corner_x[0] + 1e-6 and rise["x"][1] >= corner_x[1] - 1e-6 and \
                rise["z"][0] <= corner_z[0] + 1e-6 and rise["z"][1] >= corner_z[1] - 1e-6:
            found.append(signs)
    return found


def split_off_corners(rise):
    """A rise's rectangle less the rounded corners' squares it covers, as rectangles (low, high) of (x, z)."""
    xs = sorted({rise["x"][0], rise["x"][1]} | {value for value in (-(HALF[0] - CORNER), HALF[0] - CORNER)
                                                 if rise["x"][0] < value < rise["x"][1]})
    zs = sorted({rise["z"][0], rise["z"][1]} | {value for value in (-(HALF[1] - CORNER), HALF[1] - CORNER)
                                                 if rise["z"][0] < value < rise["z"][1]})
    cells = []
    for x0, x1 in zip(xs, xs[1:]):
        for z0, z1 in zip(zs, zs[1:]):
            if not in_corner((x0 + x1) / 2, (z0 + z1) / 2):
                cells.append(((x0, z0), (x1, z1)))
    return merged(cells)


def merged(cells):
    """Grid cells joined along x where they line up into rows, then rows along z where they line up."""
    rows = {}
    for low, high in sorted(cells):
        rows.setdefault((low[1], high[1]), []).append((low[0], high[0]))
    strips = []
    for (z0, z1), spans in rows.items():
        spans.sort()
        start, end = spans[0]
        for x0, x1 in spans[1:]:
            if abs(x0 - end) < 1e-6:
                end = x1
            else:
                strips.append(((start, z0), (end, z1)))
                start, end = x0, x1
        strips.append(((start, z0), (end, z1)))
    return strips


def rise_faces(found_rises, kinds):
    """A face panel on every side of a rise that stands over what is beside it, from that height to the rise's top,
    set in so its front is flush with the rise's side; never against a wall."""
    laid = []
    deep = FACE_DEEP
    for rise in found_rises:
        for edge, outward in rise_edges(rise):
            for start, end, below in exposed_runs(found_rises, rise, edge, outward):
                high = rise["top"] - below
                if high < 0.02:
                    continue
                length = float(np.linalg.norm(np.asarray(end) - np.asarray(start)))
                count = max(1, math.ceil(length / FLOOR_PIECE - 1e-6))
                along = (np.asarray(end) - np.asarray(start)) / length
                for index in range(count):
                    middle = np.asarray(start) + along * length * (index + 0.5) / count
                    origin = np.array([middle[0], below, middle[1]]) - np.array([outward[0], 0.0, outward[1]]) * deep / 2
                    front = np.array([outward[0], 0.0, outward[1]])
                    laid.append(piece(ROOM, "wall_lower_plain", origin, room_kit.frame_facing(front, (0, 1, 0)),
                                      (length / count, high, deep)))
    return laid


def rise_edges(rise):
    """A rise's four sides, each as its two ends (x, z) and its outward direction."""
    (x0, x1), (z0, z1) = rise["x"], rise["z"]
    return [(((x0, z0), (x1, z0)), (0.0, -1.0)), (((x0, z1), (x1, z1)), (0.0, 1.0)),
            (((x0, z0), (x0, z1)), (-1.0, 0.0)), (((x1, z0), (x1, z1)), (1.0, 0.0))]


def exposed_runs(found_rises, rise, edge, outward, step=0.05):
    """The runs along a rise's side where what is beside it stands lower, inside the room and off the walls: (start,
    end, the height beside it)."""
    start, end = np.asarray(edge[0], dtype=float), np.asarray(edge[1], dtype=float)
    length = float(np.linalg.norm(end - start))
    if length < 1e-6:
        return []
    along = (end - start) / length
    count = max(1, round(length / step))
    runs, current = [], None
    for index in range(count):
        share = (index + 0.5) / count
        point = start + along * length * share
        outside = point + np.asarray(outward) * 0.01
        beside = top_at(found_rises, *outside) if inside_room(*outside, LINING) else None
        if beside is not None and beside < rise["top"] - 0.02 and inside_room(*point, LINING):
            key = round(beside, 3)
            if current and current[2] == key:
                current[1] = start + along * length * (index + 1) / count
            else:
                if current:
                    runs.append(current)
                current = [start + along * length * index / count, start + along * length * (index + 1) / count, key]
        elif current:
            runs.append(current)
            current = None
    if current:
        runs.append(current)
    return [(tuple(run[0]), tuple(run[1]), run[2]) for run in runs]


def floor(found_rises, kinds):
    """The deck plates at floor height: wherever nothing rises and the plot's beds do not lie (the plot draws its own
    soil, and its low wall stands on these plates)."""
    plate = room_kit.size_of(kinds, "ring_floor_plate")[2]
    blocks = [(rise["x"], rise["z"]) for rise in found_rises] + [((PLOT[0], PLOT[1]), (PLOT[2], PLOT[3]))]
    xs = sorted({-HALF[0], HALF[0], -(HALF[0] - CORNER), HALF[0] - CORNER} |
                {value for block in blocks for value in block[0]})
    zs = sorted({-HALF[1], HALF[1], -(HALF[1] - CORNER), HALF[1] - CORNER} |
                {value for block in blocks for value in block[1]})
    cells = []
    for x0, x1 in zip(xs, xs[1:]):
        for z0, z1 in zip(zs, zs[1:]):
            middle = ((x0 + x1) / 2, (z0 + z1) / 2)
            if in_corner(*middle) or x1 - x0 < 1e-6 or z1 - z0 < 1e-6:
                continue
            if any(block[0][0] <= middle[0] <= block[0][1] and block[1][0] <= middle[1] <= block[1][1]
                   for block in blocks):
                continue
            cells.append(((x0, z0), (x1, z1)))
    laid = []
    for low, high in merged(cells):
        for piece_low, piece_high in tiles(low, high):
            laid.append(lying("ring_floor_plate", piece_low, piece_high, 0.0, plate))
    return laid


# --- the glass dome's frame ----------------------------------------------------------------------------------------

def ring_points(inset):
    """The points the dome's ribs rise from on one ring: the outline's corner steps, and each main wall's run cut
    into lengths about RIB_EVERY (the same count on every ring, so a rib runs straight up)."""
    points = room_kit.outline(2 * HALF, CORNER, inset)
    per_corner = room_kit.CORNER_STEPS + 1
    found = []
    for index, start in enumerate(points):
        found.append(np.asarray(start))
        if index % per_corner == per_corner - 1:
            end = np.asarray(points[(index + 1) % len(points)])
            wall = room_kit.WALLS[index // per_corner]
            length = 2 * HALF[1 if wall in ("east", "west") else 0] - 2 * CORNER
            cuts = max(1, round(length / RIB_EVERY))
            for cut in range(1, cuts):
                found.append(start + (end - start) * cut / cuts)
    return found


def dome(layout):
    """The dome's frame: a rib up the dome from every ring point to the next ring's, a hoop round every ring between
    its points, a node plate where they meet; and across the flat top, ribs from each north point to its south
    point. All on the roof's layer, their backs RIB_UNDER under the glass."""
    profile = room_kit.roof_profile(layout)
    rings = []
    for index, (inset, high, under) in enumerate(profile):
        if index == 0:  # the frame stands on the cornice's inner edge, not in the wall under the glass's foot
            inset, high = CORNICE_DEEP, layout["wall"]
        points = ring_points(inset)
        inward = [np.asarray(point) - np.asarray(other) for point, other in zip(ring_points(inset + 0.01), points)]
        rings.append([(np.array([point[0], high, point[1]]),
                       np.array([way[0], 0.0, way[1]]) / max(np.linalg.norm(way), 1e-9), under)
                      for point, way in zip(points, inward)])
    found, ribs, nodes = [], set(), set()
    for lower, upper in zip(rings, rings[1:]):
        for (low, way, under), (high, _, upper_under) in zip(lower, upper):
            key = (spot_key(low), spot_key(high))
            if key not in ribs:  # a rounded corner's points meet once the dome has come in past its radius
                ribs.add(key)
                found.append(strut("lattice_hip_rib", low, high, way, under, RIB))
    for ring in rings[1:]:
        for index, (point, way, under) in enumerate(ring):
            following = ring[(index + 1) % len(ring)][0]
            if np.linalg.norm(following - point) > 0.05:
                found.append(strut("lattice_ring_rib", point, following, way, under, HOOP))
    for ring in rings[1:]:
        for point, way, under in ring:
            if spot_key(point) not in nodes:
                nodes.add(spot_key(point))
                found.append(node(point, way, under))
    top = rings[-1]
    norths = sorted((entry for entry in top if entry[0][2] < -0.1 and abs(entry[0][0]) < HALF[0] - layout["run"]),
                    key=lambda entry: entry[0][0])
    for point, way, under in norths:
        south = next((entry for entry in top if abs(entry[0][0] - point[0]) < 0.01 and entry[0][2] > 0.1), None)
        if south is not None:
            found.append(strut("lattice_ring_rib", point, south[0], np.array([0.0, 0.0, 0.0]), under, HOOP))
    return found


def spot_key(point):
    """A point on the dome to the centimetre, so two points that meet count once."""
    return tuple(round(float(value), 2) for value in point)


def frame_under(under, way):
    """The direction from the glass into the room at a ring point, in 3D: the profile's (inset, height) direction."""
    return way * under[0] + np.array([0.0, under[1], 0.0]) if np.linalg.norm(way) > 0 else np.array([0.0, -1.0, 0.0])


def strut(kind, start, end, way, under, section):
    """A rib or a hoop from `start` to `end` on the glass, hanging RIB_UNDER under it: its length along its frame's y
    for a rib, along x for a hoop; its front into the room."""
    into = frame_under(under, way)
    into /= np.linalg.norm(into)
    run = end - start
    length = float(np.linalg.norm(run))
    run /= length
    into = into - run * (into @ run)
    into /= np.linalg.norm(into)
    middle = (start + end) / 2 + into * (RIB_UNDER + section[1] / 2)
    z = -into
    if kind == "lattice_hip_rib":
        y = run
        x = np.cross(y, z)
        origin = middle - y * length / 2
        return piece(ROOM, kind, origin, (x, y, z), (section[0], length, section[1]), room_kit.ROOF_LAYER)
    x = run
    y = np.cross(z, x)
    origin = middle - y * section[0] / 2
    return piece(ROOM, kind, origin, (x, y, z), (length, section[0], section[1]), room_kit.ROOF_LAYER)


def node(point, way, under):
    into = frame_under(under, way)
    into /= np.linalg.norm(into)
    z = -into
    # Near the dome's top z is nearly up: across is then east, squared to z (left as east, the plate's frame was up
    # to 8% off square there).
    across = np.cross(np.array([0.0, 1.0, 0.0]), z) if abs(z[1]) < 0.99 else np.array([1.0, 0.0, 0.0]) - z * z[0]
    across /= np.linalg.norm(across)
    y = np.cross(z, across)
    origin = point + into * (RIB_UNDER + RIB[1] + NODE[2] / 2) - y * NODE[1] / 2
    return piece(ROOM, "lattice_node_plate", origin, (across, y, z), NODE, room_kit.ROOF_LAYER)


def dome_height(layout, x, z):
    """How high the glass is over a place, the frame's underside under it (GreenhouseRig.dome_height's way)."""
    profile = room_kit.roof_profile(layout)
    inward = min(HALF[0] - abs(x), HALF[1] - abs(z))
    for (low_in, low_high, _), (high_in, high_high, _) in zip(profile, profile[1:]):
        if inward <= high_in:
            share = min(max((inward - low_in) / max(high_in - low_in, 1e-3), 0.0), 1.0)
            return low_high + (high_high - low_high) * share - RIB_UNDER - RIB[1]
    return profile[-1][1] - RIB_UNDER - RIB[1]


# --- the robot station and the gantry ------------------------------------------------------------------------------

def standing(kind, x, y, z, size, facing, layer=1):
    """A piece standing on its foot at (x, y, z), its front looking toward `facing` (degrees from north)."""
    bearing = math.radians(facing)
    front = np.array([math.sin(bearing), 0.0, -math.cos(bearing)])
    return piece(ROOM, kind, np.array([x, y, z]), room_kit.frame_facing(front, (0, 1, 0)), size, layer)


def bay_spot(bay):
    """PlotField._bay_local: a bay's pad middle on the room's floor."""
    along = BED / 2 + WALL_GAP + WALL_THICK + PAD_OFF_WALL + PAD[2] / 2
    return FIELD + np.array([bay * ENTRY_SPACING * BED, along])


def station():
    """Each bay's dock pad and charge post, and the three bins, where PlotField stands them."""
    found = []
    for bay in range(BAYS):
        pad = bay_spot(bay)
        found.append(lying(PADS[bay], (pad[0] - PAD[0] / 2, pad[1] - PAD[2] / 2), (pad[0] + PAD[0] / 2, pad[1] + PAD[2] / 2),
                           PAD[1], PAD[1]))
        bar = pad + np.array([PAD[0] / 2 + BAR_FRAME[0] / 2 + 0.02, PAD[2] / 2 - BAR_FRAME[2]])
        found.append(standing("charge_post", bar[0], 0.0, bar[1], (0.14, 0.7, 0.16), 180))
    last = bay_spot(BAYS - 1)
    for index, (kind, size) in enumerate(BINS):
        spot = last + np.array([BINS_FROM + index * BIN_SPACING, 0.0])
        found.append(standing(kind, spot[0], 0.0, spot[1], size, 180))
    return found


def along_pieces(start, end, count):
    step = (end - start) / count
    return [(start + step * index, start + step * (index + 1)) for index in range(count)]


def bar_spots():
    """GreenhouseRig.bar_spots: one bar over each quarter of the plot, across."""
    share = (PLOT[1] - PLOT[0]) / BAR_PIECES
    return [PLOT[0] + share * (index + 0.5) for index in range(BAR_PIECES)]


def lengthwise(kind, x, z0, z1, foot, size, layer=room_kit.ROOF_LAYER):
    """A piece built along its x laid north-south from z0 to z1, its foot at `foot`, its front west (its x runs north,
    so the frame is right-handed: a mirrored frame draws its faces inside out)."""
    axes = (np.array([0.0, 0.0, -1.0]), np.array([0.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0]))
    return piece(ROOM, kind, np.array([x, foot, (z0 + z1) / 2]), axes, (z1 - z0, size[1], size[2]), layer)


def crosswise(kind, x0, x1, z, foot, size, layer=room_kit.ROOF_LAYER):
    """A piece built along its x laid west-east from x0 to x1, its foot at `foot`, its front south."""
    axes = (np.array([-1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, -1.0]))
    return piece(ROOM, kind, np.array([(x0 + x1) / 2, foot, z]), axes, (x1 - x0, size[1], size[2]), layer)


def gantry(layout, kinds):
    """The grow-light gantry: over each bar spot a housing and its lit lens in BAR_PIECES lengths, an irrigation
    boom beside it, two rails across the bars at RAILS_AT, hangers from each rail up to the dome, and the main
    across north of the plot coming down into the tank."""
    found = []
    bar = room_kit.size_of(kinds, "grow_light_bar")
    lens = room_kit.size_of(kinds, "grow_light_glow")
    rail = room_kit.size_of(kinds, "rig_rail")
    boom = room_kit.size_of(kinds, "irrigation_boom")
    pipe = room_kit.size_of(kinds, "pipe_straight")
    for x in bar_spots():
        for z0, z1 in along_pieces(PLOT[2], PLOT[3], BAR_PIECES):
            found.append(lengthwise("grow_light_bar", x, z0, z1, BAR_FOOT, bar))
            found.append(lengthwise("grow_light_glow", x, z0 + 0.05, z1 - 0.05, BAR_FOOT + LENS_UP, lens))
            found.append(lengthwise("irrigation_boom", x + BOOM_OFF, z0, z1, BAR_FOOT + bar[1] - boom[1], boom))
    rail_foot = BAR_FOOT + bar[1]
    for z in RAILS_AT:
        for x0, x1 in along_pieces(PLOT[0], PLOT[1], BAR_PIECES):
            found.append(crosswise("rig_rail", x0, x1, z, rail_foot, rail))
        for x in HANGERS_AT:
            foot = rail_foot + rail[1]
            top = dome_height(layout, x, z)
            found.append(standing("rig_hanger", x, foot, z, (0.1, top - foot, 0.1), 180, room_kit.ROOF_LAYER))
    main_foot = BAR_FOOT
    found.append(crosswise("pipe_straight", TANK[0], bar_spots()[-1] + BOOM_OFF + 0.05, MAIN_ALONG, main_foot,
                           (1.0, pipe[1], pipe[2])))
    drop_top = main_foot
    drop = drop_top - TANK_TOP
    axes = (np.array([0.0, 1.0, 0.0]), np.array([-1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]))
    found.append(piece(ROOM, "pipe_straight", np.array([TANK[0] + pipe[1] / 2, TANK_TOP + drop / 2, MAIN_ALONG]), axes,
                       (drop, pipe[1], pipe[2]), room_kit.ROOF_LAYER))
    return found


def laid_out(inventory):
    """Every piece of the greenhouse, room_kit's way with the greenhouse's own: no roof plates (the dome is glass on
    a frame), the floor's rises surfaced, the station and the gantry."""
    layout = inventory["room"]["layout"]
    kinds = {row["id"]: row for row in inventory["rows"] if row.get("made") == "kit piece"}
    found_rises = rises()
    found = room_kit.walls(ROOM, layout, kinds) + floor(found_rises, kinds) + rise_tops(found_rises, kinds)
    found += rise_faces(found_rises, kinds) + room_kit.doors(ROOM, layout, kinds) + dome(layout)
    found += room_kit.placed_rows(ROOM, layout, kinds, inventory) + room_kit.flat_rows(ROOM, inventory, kinds)
    found += station() + gantry(layout, kinds)
    found += room_kit.pipe_brackets(ROOM, kinds, found) + room_kit.under_floor(ROOM, kinds, found)
    found = hub_kit.split_at_fittings(found)
    return [laid for laid in room_kit.cut_openings(ROOM, found + room_kit.children(ROOM, found))
            if not room_kit.covered(laid)]


FLOORS = {"ring_floor_plate", "ledge_cover", "dock_pad_one", "dock_pad_two", "dock_pad_three"}


def kinds_table(inventory):
    """room_kit's table, the ledge covers and the dock pads floors too."""
    table = room_kit.kinds_table(ROOM, inventory)
    for kind in FLOORS:
        if f"{ROOM}_{kind}" in table:
            table[f"{ROOM}_{kind}"]["group"] = "floors"
    return table


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    inventory = json.loads((REPO / f"data/inventory/{ROOM}.json").read_text())
    pieces = laid_out(inventory)
    counts = {}
    for found in pieces:
        counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    pathlib.Path(sys.argv[1]).write_text(json.dumps(
        {"room": ROOM, "frame": "the room's own: its middle on its floor, x east, z south, y up", "counts": counts,
         "kinds": kinds_table(inventory), "pieces": pieces}, indent="\t") + "\n")
    print(len(pieces), "pieces of", len(counts), "kinds")


if __name__ == "__main__":
    main()
