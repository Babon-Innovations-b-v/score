"""The stair core algorithm (#128, the stairwell: no kit piece is a walkable stair of real size): a switchback
stairwell `storeys` storeys tall, written as one mesh with named parts, every piece a closed solid of real thickness
so a walker climbs it and the physics check reads it as solids.

Its own frame (metres, y up): the flights run along x, the front wall's inner face is z = 0 (glazed over every
landing and flight, so the concept's look into the shaft is a look through its windows), the back wall stands at
z = DEEP. Each storey k (floor height h = k * STOREY) has a floor landing at x 0 to
LANDING, a front flight from it up along +x to a half landing at h + STOREY / 2 (x from LANDING + RUN to LONG) and a
back flight from there up along -x to the next floor landing. Each step is RISE high and TREAD deep (9 risers a half
storey: 0.167 m by 0.28 m, a building code's stair), each flight WIDE wide with a WELL between them, its underside a
waist parallel to its pitch (so the flight under it keeps a full head height).

Parts, for their library surfaces (place_build.surface --part):

- `slab`: the ground slab (with the pavement round the entrance), floor and half landings, the roof (SLAB thick);
- `steps`: the flights;
- `wall`: the left, right and back walls (WALL thick) with the doorways cut in them, and each flat's hall stub (a
  floor, two side walls, an end wall and a ceiling behind its door, so both sides of every door are floor);
- `dado`: the painted band DADO high along the walls over every floor line and flight (DADO_SKIN proud of the wall);
- `block`, `glass` and `frame`: the flats' blocks either side of the shaft (BLOCK wide, a floor each storey, the
  facade FACADE out with WINDOWS cut, each a pane in a frame with mullions; the entrance opens into the left one's
  ground floor, and with `street` that ground floor is the lobby a street door in its facade opens onto the street
  through, in place of its window nearest the shaft), and the shaft's own front wall with a window over each landing
  and flight;
- `balusters` and `handrail`: the railings along the open front and the well, BALUSTER bars every BALUSTER_STEP and a
  rail RAIL high over the pitch line (LANDING_RAIL over a landing).

    core(path, storeys=STOREYS, mirror=False, curtain=False, cut=False, one_block=False, joined=(), street=False)
                                  the core written as a USD file at `path` (`mirror`: the other hand,
                                  `curtain`: a storey-high glazed front, `cut`: the front wall left to its own
                                  file (front_alone), so the camera can cut it at render, `one_block`: the
                                  entrance's flats' block alone, `joined`: the storeys whose flat door opens
                                  onto a place of its own, with no hall stub behind it, `street`: a street
                                  door in the entrance block's facade); its doorways [(wall, along from,
                                  along to, sill, head)] in the unmirrored frame
    front_alone(path, storeys=STOREYS, mirror=False, curtain=False)
                                  the shaft's front wall alone (parts `wall`, `glass`, `frame`) at `path`
    doorways(storeys=STOREYS, street=False)
                                  the doorways alone, for the doors laid in them
    doorway_spots(storeys=STOREYS, mirror=False, street=False)
                                  each doorway's sill middle, inward way (into the place) and width in the
                                  core's own frame and hand, by name (`door0` the entrance, `door<k>` storey k's,
                                  `street` the street door)
"""
import math
import pathlib
import sys

import numpy as np

from score.stages.place_build import dome_shell

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "tools/usd"))
import builders  # noqa: E402

STOREYS = 3  # storeys climbed: floor landings at 0, 3, 6 and 9 m
STOREY = 3.0  # floor to floor
STEPS = 9  # risers a flight (a half storey)
RISE = STOREY / 2 / STEPS
TREAD = 0.28
RUN = STEPS * TREAD
WIDE = 1.2  # a flight's width
WELL = 0.2  # the gap between the two flights
DEEP = 2 * WIDE + WELL  # the shaft's inside depth (z)
LANDING = 1.6  # a floor landing's length (x)
HALF = 1.4  # a half landing's length (x)
LONG = LANDING + RUN + HALF  # the shaft's inside length (x)
SLAB = 0.2
WALL = 0.2
WAIST = 0.2  # a flight's underside under its pitch line, measured upright
HEADROOM = 2.8  # the shaft's top over the top landing
DOOR = (1.02, 1.96)  # a doorway's width and height (the library's apartment door, 1.01 by 1.94, with its play)
DOOR_AT = 0.3  # a back wall doorway's near edge from the left wall
ENTRY_AT = 0.8  # the entrance's near edge from the open front, in the left wall
HALL = 1.4  # a flat's hall stub: its width and depth behind its door
HALL_HIGH = 2.6
DADO = 1.2
DADO_SKIN = 0.008
BALUSTER = 0.018
BALUSTER_STEP = 0.12
RAIL = 0.9  # a flight's handrail over its pitch line
LANDING_RAIL = 1.0
RAIL_SIZE = (0.06, 0.05)  # the handrail's width and height
RAIL_INSET = 0.05  # a railing's line in from the edge it guards
NEWEL = 0.08  # a newel post's side: where a flight's handrail meets its landings' railings
TILE = 1.5  # the ground slab's pieces, metres each way
PAVEMENT = 2.2  # the ground slab's reach past the block (the street side) and in front of the cut
BLOCK = 5.0  # the flats' block beside the shaft, past its left wall: its width (x)
FACADE = 0.4  # the block's facade front, out in front of the cut (z = -FACADE)
WINDOWS = (1.3, 3.7)  # a storey's windows' middles in from the shaft's left wall
WINDOW = (1.2, 0.9, 2.4)  # a window's width, sill and head over its floor
STREET = WINDOWS[0]  # the street door's middle in from the shaft's side wall: in place of the ground floor's window
FRAME_BAR = (0.05, 0.06)  # a window frame bar's face and depth
PANE = 0.7  # a window's panes no wider than this between mullions
CURTAIN_PIER = 0.15  # a curtain front's corner piers, in from the shaft's side walls
CURTAIN_SPANDREL = 0.05  # a curtain front's opening's clearance over its floor and under the slab over it
CURTAIN_PANE = 1.4  # a curtain front's mullions no further apart than this


def top(storeys):
    return storeys * STOREY + HEADROOM


def box(low, high):
    """A closed axis-aligned box from `low` to `high` (x, y, z): its points and quad faces."""
    (x0, y0, z0), (x1, y1, z1) = low, high
    points = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
              (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 4, 7, 3), (1, 2, 6, 5), (3, 7, 6, 2), (0, 1, 5, 4)]
    return points, [list(face) for face in faces]


def tiled(low, high, size=TILE):
    """A slab from `low` to `high` laid as boxes no wider than `size` each way (a pavement's slabs; a contact solver
    meets a few metres of face, never one face across the whole place)."""
    xs = np.linspace(low[0], high[0], int(np.ceil((high[0] - low[0]) / size)) + 1)
    zs = np.linspace(low[2], high[2], int(np.ceil((high[2] - low[2]) / size)) + 1)
    return [box((x0, low[1], z0), (x1, high[1], z1)) for x0, x1 in zip(xs, xs[1:]) for z0, z1 in zip(zs, zs[1:])]


def beam(start, end, wide, high):
    """A closed bar from `start` to `end` (a rail along a slope), `wide` across level and `high` across upright."""
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    along = (end - start) / np.linalg.norm(end - start)
    side = np.cross(along, (0.0, 1.0, 0.0))
    side = side / np.linalg.norm(side) if np.linalg.norm(side) > 1e-9 else np.array([1.0, 0.0, 0.0])
    up = np.cross(side, along)
    corners = [point + side * sx * wide / 2 + up * sy * high / 2
               for point in (start, end) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return [tuple(map(float, point)) for point in corners], [list(face) for face in faces]


def prism(profile, near, far):
    """A closed solid of an upright outline `profile` [(x, y)] (convex or not) from z `near` to `far`."""
    outline = [[float(x), float(y)] for x, y in profile]
    if builders.turning(outline) < 0:
        outline = outline[::-1]
    count = len(outline)
    points = [(x, y, near) for x, y in outline] + [(x, y, far) for x, y in outline]
    faces = [list(triangle) for triangle in builders.ear_clipped(outline)]
    faces += [[count + c, count + b, count + a] for a, b, c in builders.ear_clipped(outline)]
    faces += [[one, count + one, count + (one + 1) % count, (one + 1) % count] for one in range(count)]
    return points, faces


def holed(low, high, axis, holes):
    """A wall slab from `low` to `high` lying across `axis` (0: along x, 2: along z), with rectangular `holes`
    [(along from, along to, y from, y to)] cut through it: its closed boxes, one a column between the cuts."""
    cuts = sorted({low[axis], high[axis], *[edge for hole in holes for edge in hole[:2]]})
    pieces = []
    for first, second in zip(cuts, cuts[1:]):
        middle = (first + second) / 2
        over = sorted((hole[2], hole[3]) for hole in holes if hole[0] <= middle <= hole[1])
        bottom = low[1]
        for hole_low, hole_high in over + [(high[1], high[1])]:
            if hole_low > bottom + 1e-6:
                piece_low, piece_high = list(low), list(high)
                piece_low[axis], piece_high[axis] = first, second
                piece_low[1], piece_high[1] = bottom, hole_low
                pieces.append(box(piece_low, piece_high))
            bottom = max(bottom, hole_high)
    return pieces


def flight_profile(foot_x, foot_y, way):
    """A flight's side outline (x, y): its steps up from (`foot_x`, `foot_y`) along `way` (+1 or -1) to the landing a
    half storey up, then its waist back down under the pitch line."""
    outline = [(foot_x, foot_y)]
    for step in range(STEPS):
        y = foot_y + RISE * (step + 1)
        outline += [(foot_x + way * TREAD * step, y), (foot_x + way * TREAD * (step + 1), y)]
    outline += [(foot_x + way * RUN, foot_y + STOREY / 2 - WAIST), (foot_x, foot_y - WAIST)]
    return outline


def pitch(foot_x, foot_y, way, x):
    """The pitch line's height (through the step noses) over `x` on a flight."""
    return foot_y + RISE + (x - foot_x) * way * RISE / TREAD


def flights(storeys):
    """Each flight: (foot x, foot y, way, near z, far z)."""
    found = []
    for storey in range(storeys):
        floor = storey * STOREY
        found.append((LANDING, floor, 1, 0.0, WIDE))
        found.append((LANDING + RUN, floor + STOREY / 2, -1, WIDE + WELL, DEEP))
    return found


def doorways(storeys=STOREYS, street=False):
    """The doorways: the entrance in the left wall at the ground, each flat's door in the back wall on each floor
    landing above it, and with `street` the street door in the left block's facade (along x) at the ground; [(wall,
    along from, along to, sill, head)]."""
    found = [("left", ENTRY_AT, ENTRY_AT + DOOR[0], 0.0, DOOR[1])]
    for storey in range(1, storeys + 1):
        floor = storey * STOREY
        found.append(("back", DOOR_AT, DOOR_AT + DOOR[0], floor, floor + DOOR[1]))
    if street:
        middle = -WALL - STREET
        found.append(("facade", middle - DOOR[0] / 2, middle + DOOR[0] / 2, 0.0, DOOR[1]))
    return found


def doorway_spots(storeys=STOREYS, mirror=False, street=False):
    """{name: {"middle", "inward", "wide", "sill", "head"}}: each doorway's sill middle (in the middle of its wall),
    the level way into the place (the shaft, the street door's into the lobby) and its width, in the core's own frame
    and hand (`mirror`: x taken as LONG - x, as `mirrored`); `door0` the entrance, `door<k>` storey k's flat door,
    `street` the street door. place_build's `stairs` records them in the scene's frame, so a place joined at one
    (area/) meets it there."""
    found = {}
    for wall, start, end, sill, head in doorways(storeys, street):
        along = (start + end) / 2
        middle, inward = {"left": ([-WALL / 2, sill, along], [1.0, 0.0, 0.0]),
                          "back": ([along, sill, DEEP + WALL / 2], [0.0, 0.0, -1.0]),
                          "facade": ([along, sill, -FACADE + WALL / 2], [0.0, 0.0, 1.0])}[wall]
        if mirror:
            middle, inward = [LONG - middle[0], middle[1], middle[2]], [-inward[0], 0.0, inward[2]]
        name = "street" if wall == "facade" else f"door{round(sill / STOREY)}"
        found[name] = {"middle": middle, "inward": inward, "wide": end - start, "sill": sill, "head": head}
    return found


def structure(storeys, joined=()):
    """The slabs, flights, walls and hall stubs: [(part, (points, faces))]; a `joined` storey's flat door opens onto
    a place of its own (area/: the flat seated at it), so no hall stub stands behind it to wall the walker off."""
    high = top(storeys)
    pieces = [("slab", made) for made in tiled((-2 * WALL - BLOCK - PAVEMENT, -0.3, -PAVEMENT),
                                                (LONG + 2 * WALL + BLOCK + PAVEMENT, 0.0, DEEP + WALL))]
    for storey in range(1, storeys + 1):
        floor = storey * STOREY
        pieces.append(("slab", box((0.0, floor - SLAB, 0.0), (LANDING, floor, DEEP))))
    for storey in range(storeys):
        half = storey * STOREY + STOREY / 2
        pieces.append(("slab", box((LANDING + RUN, half - SLAB, 0.0), (LONG, half, DEEP))))
    pieces.append(("slab", box((-WALL, high, 0.0), (LONG + WALL, high + SLAB, DEEP + WALL))))
    for foot_x, foot_y, way, near, far in flights(storeys):
        pieces.append(("steps", prism(flight_profile(foot_x, foot_y, way), near, far)))
    doors = doorways(storeys)
    left = [(start, end, sill, head) for wall, start, end, sill, head in doors if wall == "left"]
    back = [(start, end, sill, head) for wall, start, end, sill, head in doors if wall == "back"]
    pieces += [("wall", made) for made in holed((-WALL, 0.0, 0.0), (0.0, high, DEEP + WALL), 2, left)]
    pieces += [("wall", made) for made in holed((-WALL, 0.0, DEEP), (LONG + WALL, high, DEEP + WALL), 0, back)]
    pieces.append(("wall", box((LONG, 0.0, 0.0), (LONG + WALL, high, DEEP))))
    for start, end, sill, _ in back:
        if round(sill / STOREY) in joined:
            continue
        middle = (start + end) / 2
        x0, x1 = middle - HALL / 2, middle + HALL / 2
        z0, z1 = DEEP + WALL, DEEP + WALL + HALL
        pieces += [("wall", box((x0 - WALL, sill - SLAB, z0), (x1 + WALL, sill, z1 + WALL))),
                   ("wall", box((x0 - WALL, sill, z0), (x0, sill + HALL_HIGH, z1))),
                   ("wall", box((x1, sill, z0), (x1 + WALL, sill + HALL_HIGH, z1))),
                   ("wall", box((x0 - WALL, sill, z1), (x1 + WALL, sill + HALL_HIGH, z1 + WALL))),
                   ("wall", box((x0 - WALL, sill + HALL_HIGH, z0), (x1 + WALL, sill + HALL_HIGH + SLAB, z1 + WALL)))]
    return pieces


def windows(storeys, inner, way):
    """A block's windows, its inner side at x `inner` and running `way` (-1 or 1) from it: [(x from, x to, sill,
    head)]."""
    found = []
    for storey in range(storeys + 1):
        for middle in WINDOWS:
            centre = inner + way * middle
            found.append((centre - WINDOW[0] / 2, centre + WINDOW[0] / 2, storey * STOREY + WINDOW[1],
                          storey * STOREY + WINDOW[2]))
    return found


def front_windows(storeys, curtain=False):
    """The shaft's own windows in its front wall: over each floor landing, each flight and each half landing, clear
    of the slabs behind them; with `curtain` one storey-high glazed opening a storey across the whole shaft, the wall
    left only as the slab edges and corner piers (a glazed stair tower, so the look in reads as the concept's cut):
    [(x from, x to, sill, head)]."""
    if curtain:
        return [(CURTAIN_PIER, LONG - CURTAIN_PIER, storey * STOREY + CURTAIN_SPANDREL,
                 min((storey + 1) * STOREY, top(storeys)) - SLAB - CURTAIN_SPANDREL)
                for storey in range(storeys + 1)]
    found = []
    for storey in range(storeys + 1):
        floor = storey * STOREY
        found.append((0.25, LANDING - 0.25, floor + 0.9, floor + 2.5))
        found.append((LANDING + 0.25, LANDING + RUN - 0.25, floor + 0.7, floor + 2.6))
        if storey < storeys:
            found.append((LANDING + RUN + 0.2, LONG - 0.2, floor + STOREY / 2 + 0.9, floor + STOREY / 2 + 2.5))
    return found


def glazed(holes, middle_z, pane=PANE):
    """A pane (one face: the preview draws a see-through look as a thin skin, and a closed pane's two skins ring
    with light) and its frame (a bar round it and mullions no more than PANE apart) in each hole: [(part, solid)]."""
    bar, depth = FRAME_BAR
    z0, z1 = middle_z - depth / 2, middle_z + depth / 2
    pieces = []
    for x0, x1, sill, head in holes:
        pieces.append(("glass", ([(x0, sill, middle_z), (x1, sill, middle_z), (x1, head, middle_z),
                                  (x0, head, middle_z)], [[0, 1, 2, 3]])))
        pieces += [("frame", box((x0, sill, z0), (x1, sill + bar, z1))),
                   ("frame", box((x0, head - bar, z0), (x1, head, z1))),
                   ("frame", box((x0, sill + bar, z0), (x0 + bar, head - bar, z1))),
                   ("frame", box((x1 - bar, sill + bar, z0), (x1, head - bar, z1)))]
        panes = max(2, round((x1 - x0) / pane))
        for number in range(1, panes):
            x = x0 + (x1 - x0) * number / panes
            pieces.append(("frame", box((x - bar / 2, sill + bar, z0), (x + bar / 2, head - bar, z1))))
    return pieces


def block(storeys, inner, way, street=False):
    """A flats' block beside the shaft, its inner side at x `inner` (the shaft's side wall's outer face) and BLOCK
    wide `way` from it: its facade with windows, outer side and back walls, a floor each storey, its roof and the
    corner pier closing the facade onto the shaft's side wall (without it a slot WALL wide and FACADE deep stood
    open the building's full height; owner, 2026-11-17: "big ass gap in the corner"); with `street` its ground floor
    a lobby, a street door's doorway (DOOR) cut in its facade STREET in from the shaft in place of that floor's window
    there (#154: the entrance opened into the block and the stairwell met no street): [(part, (points, faces))]."""
    high = top(storeys) + SLAB
    near, far = sorted((inner, inner + way * BLOCK))
    outer = (far, far + WALL) if way > 0 else (near - WALL, near)
    holes = windows(storeys, inner, way)
    door = []
    if street:
        middle = inner + way * STREET
        holes = [hole for hole in holes if not (hole[2] < STOREY and hole[0] < middle < hole[1])]
        door = [(middle - DOOR[0] / 2, middle + DOOR[0] / 2, 0.0, DOOR[1])]
    pieces = [("block", made) for made in holed((near, 0.0, -FACADE), (far, high, -FACADE + WALL), 0, holes + door)]
    pieces += [("block", box((outer[0], 0.0, -FACADE), (outer[1], high, DEEP + WALL))),
               ("block", box((near, 0.0, DEEP), (far, high - SLAB, DEEP + WALL))),
               ("block", box((min(near, outer[0]), high - SLAB, -FACADE), (max(far, outer[1]), high, DEEP + WALL)))]
    pieces += [("block", box((near, storey * STOREY - SLAB, -FACADE + WALL), (far, storey * STOREY, DEEP)))
               for storey in range(1, storeys + 1)]
    pier = sorted((inner, inner - way * WALL))  # the shaft's side wall carried out to the facade's front
    pieces.append(("block", box((pier[0], 0.0, -FACADE), (pier[1], high, 0.0))))
    return pieces + glazed(holes, -FACADE + WALL / 2)


def front(storeys, curtain=False):
    """The shaft's front wall (z -WALL to 0) with its windows glazed (`curtain`: a storey-high curtain wall, its
    mullions CURTAIN_PANE apart): [(part, solid)]."""
    holes = front_windows(storeys, curtain)
    walls = [("wall", made) for made in holed((-WALL, 0.0, -WALL), (LONG + WALL, top(storeys), 0.0), 0, holes)]
    return walls + glazed(holes, -WALL / 2, CURTAIN_PANE if curtain else PANE)


def band(line, cuts=()):
    """The dado's upright outlines (along, y) over a floor line [(along, y)], DADO high, split round `cuts`
    [(along from, along to)] (the doorways it stops at)."""
    edges = sorted({line[0][0], line[-1][0], *[edge for cut in cuts for edge in cut]})
    outlines = []
    for first, second in zip(edges, edges[1:]):
        if any(cut[0] <= (first + second) / 2 <= cut[1] for cut in cuts):
            continue
        inner = [point for point in line if first < point[0] < second]
        lower = [(first, np.interp(first, *zip(*line))), *inner, (second, np.interp(second, *zip(*line)))]
        outlines.append(lower + [(along, y + DADO) for along, y in reversed(lower)])
    return outlines


def dado(storeys):
    """The dado bands on the back, left and right walls' inner faces: [(part, (points, faces))]."""
    pieces = []
    doors = doorways(storeys)
    back_cuts = {round(sill / STOREY): (start, end) for wall, start, end, sill, _ in doors if wall == "back"}
    for storey in range(storeys + 1):
        floor = storey * STOREY
        if storey == 0:
            line = [(0.0, 0.0), (LONG, 0.0)]
        else:
            line = [(0.0, floor), (LANDING, floor), (LANDING + RUN, floor - STOREY / 2), (LONG, floor - STOREY / 2)]
        cuts = [back_cuts[storey]] if storey in back_cuts else []
        for outline in band(line, cuts):
            pieces.append(("dado", prism(outline, DEEP - DADO_SKIN, DEEP)))
    entry = [(start, end) for wall, start, end, *_ in doors if wall == "left"]
    for storey in range(storeys + 1):
        floor = storey * STOREY
        for outline in band([(0.0, floor), (DEEP, floor)], entry if storey == 0 else ()):
            points, faces = prism(outline, 0.0, DADO_SKIN)
            pieces.append(("dado", ([(z, y, x) for x, y, z in points], faces)))
    for storey in range(storeys):
        floor = storey * STOREY + (STOREY / 2 if storey else 0.0)
        for level in ([0.0, STOREY / 2] if storey == 0 else [floor]):
            points, faces = prism([(0.0, level), (DEEP, level), (DEEP, level + DADO), (0.0, level + DADO)],
                                  LONG - DADO_SKIN, LONG)
            pieces.append(("dado", ([(z, y, x) for x, y, z in points], faces)))
    return pieces


def railing(points_along, height_of, rail_high, z, handrail=True):
    """A railing at depth `z` along x from the first of `points_along` to the last: balusters every BALUSTER_STEP
    from the floor (`height_of(x)`) to the rail, a handrail `rail_high` over the floor line (unless `handrail` is
    False: a flight's, laid by newelled) and a bottom bar."""
    start, end = points_along
    count = max(2, int(abs(end - start) / BALUSTER_STEP) + 1)
    pieces = []
    for number in range(count):
        x = start + (end - start) * number / (count - 1)
        floor = height_of(x)
        pieces.append(("balusters", box((x - BALUSTER / 2, floor, z - BALUSTER / 2),
                                        (x + BALUSTER / 2, floor + rail_high - RAIL_SIZE[1] / 2, z + BALUSTER / 2))))
    if handrail:
        pieces.append(("handrail", beam((start, height_of(start) + rail_high, z),
                                        (end, height_of(end) + rail_high, z), *RAIL_SIZE)))
    pieces.append(("balusters", beam((start, height_of(start) + 0.1, z), (end, height_of(end) + 0.1, z),
                                     0.03, 0.02)))
    return pieces


def cross_railing(x, z_from, z_to, floor):
    """A short landing railing across z at `x` (where a landing ends over the well or a flight below)."""
    pieces = []
    count = max(2, int(abs(z_to - z_from) / BALUSTER_STEP) + 1)
    for number in range(count):
        z = z_from + (z_to - z_from) * number / (count - 1)
        pieces.append(("balusters", box((x - BALUSTER / 2, floor, z - BALUSTER / 2),
                                        (x + BALUSTER / 2, floor + LANDING_RAIL - RAIL_SIZE[1] / 2, z + BALUSTER / 2))))
    pieces.append(("handrail", beam((x, floor + LANDING_RAIL, z_from), (x, floor + LANDING_RAIL, z_to), *RAIL_SIZE)))
    return pieces


def newelled(foot_x, foot_y, way, z, reach):
    """A flight's handrail at depth `z` run on to the landing railings it meets, `reach` in from the flight's foot
    and head along x (where the landing's railing ends), with a newel post at each end from its landing up past both
    rails, so the flight's rail and the landing's join (2099 judge, 2026-11-23: the rails stopped in mid-air, two
    stubs at different heights with a gap at every turn)."""
    pieces = []
    for x, floor in ((foot_x - way * reach, foot_y), (foot_x + way * (RUN + reach), foot_y + STOREY / 2)):
        rail = pitch(foot_x, foot_y, way, x) + RAIL
        top = max(rail, floor + LANDING_RAIL) + RAIL_SIZE[1] / 2 + 0.02
        pieces.append(("handrail", box((x - NEWEL / 2, floor, z - NEWEL / 2), (x + NEWEL / 2, top, z + NEWEL / 2))))
    start, end = foot_x - way * reach, foot_x + way * (RUN + reach)
    pieces.append(("handrail", beam((start, pitch(foot_x, foot_y, way, start) + RAIL, z),
                                    (end, pitch(foot_x, foot_y, way, end) + RAIL, z), *RAIL_SIZE)))
    return pieces


def railings(storeys):
    """The railings of the open front, the well and the top landing: [(part, (points, faces))]. Each flight's
    handrail runs on to the landing railings at its foot and head and meets them at a newel post (newelled): the
    open front's rail to the landing's end (x LANDING, LANDING + RUN), the well's to its cross railing (RAIL_INSET
    further)."""
    pieces = []
    inset = RAIL_INSET
    for foot_x, foot_y, way, near, far in flights(storeys):
        ends = (foot_x + way * 0.05, foot_x + way * (RUN - 0.05))
        on_flight = lambda x, foot_x=foot_x, foot_y=foot_y, way=way: pitch(foot_x, foot_y, way, x)  # noqa: E731
        if way > 0:
            pieces += railing(ends, on_flight, RAIL, near + inset, handrail=False)
            pieces += newelled(foot_x, foot_y, way, near + inset, 0.0)
            pieces += railing(ends, on_flight, RAIL, far - inset, handrail=False)
            pieces += newelled(foot_x, foot_y, way, far - inset, inset)
        else:
            pieces += railing(ends, on_flight, RAIL, near + inset, handrail=False)
            pieces += newelled(foot_x, foot_y, way, near + inset, inset)
    for storey in range(1, storeys + 1):
        floor = storey * STOREY
        pieces += railing((inset, LANDING), lambda x, floor=floor: floor, LANDING_RAIL, inset)
    for storey in range(storeys):
        half = storey * STOREY + STOREY / 2
        pieces += railing((LANDING + RUN, LONG - inset), lambda x, half=half: half, LANDING_RAIL, inset)
        pieces += cross_railing(LANDING + RUN + inset, WIDE - inset, WIDE + WELL + inset, half)
    for storey in range(1, storeys):
        pieces += cross_railing(LANDING - inset, WIDE - inset, WIDE + WELL + inset, storey * STOREY)
    pieces += cross_railing(LANDING - inset, inset, WIDE + WELL + inset, storeys * STOREY)
    return pieces


def mirrored(piece):
    """A piece turned the other hand: x taken as LONG - x."""
    part, (points, faces) = piece
    return part, ([(LONG - x, y, z) for x, y, z in points], faces)


def outward(piece):
    """A closed piece (a single face is left as it is) with its faces turned to look out (its signed volume positive), so the walkers' floor reads a
    top as a floor and never as a slab's underside."""
    part, (points, faces) = piece
    if len(faces) < 4:
        return piece
    corners = np.asarray(points, dtype=float)
    volume = sum(np.dot(corners[face[0]], np.cross(corners[face[number]], corners[face[number + 1]]))
                 for face in faces for number in range(1, len(face) - 1))
    return part, (points, faces if volume > 0 else [list(reversed(face)) for face in faces])


def core(path, storeys=STOREYS, mirror=False, curtain=False, cut=False, one_block=False, joined=(), street=False):
    """The stair core written at `path`: /stair_core with its mesh `geo` and its parts (the module's list); with
    `mirror` the other hand (floor landings at x LONG - LANDING to LONG, the flights rising towards -x), with
    `curtain` its front a storey-high curtain wall instead of a window over each landing and flight, with `cut` the
    front wall left to its own file (front_alone: laid as its own object, the building stays closed and the camera
    cuts it at render), with `one_block` only the
    flats' block the entrance opens into, the shaft's far side wall standing free to the street, with `joined` no
    hall stub behind those storeys' flat doors, with `street` a street door in that block's facade onto its lobby."""
    pieces = structure(storeys, joined) + ([] if cut else front(storeys, curtain)) + block(storeys, -WALL, -1, street) \
        + ([] if one_block else block(storeys, LONG + WALL, 1)) \
        + dado(storeys) + railings(storeys)
    pieces = [mirrored(piece) for piece in pieces] if mirror else pieces
    dome_shell.written(path, "stair_core", [outward(piece) for piece in pieces], flat=True)
    return doorways(storeys, street)


def front_alone(path, storeys=STOREYS, mirror=False, curtain=False):
    """The shaft's front wall alone written at `path` (/stair_front, parts `wall`, `glass`, `frame`), in the core's
    own frame and hand: the wall a `cut` core leaves to its own object."""
    pieces = front(storeys, curtain)
    pieces = [mirrored(piece) for piece in pieces] if mirror else pieces
    dome_shell.written(path, "stair_front", [outward(piece) for piece in pieces], flat=True)
