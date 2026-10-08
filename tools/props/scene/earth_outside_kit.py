"""The prologue's outdoor places laid out as made pieces (world 1, 2026-10-07): the street at the foot of the block, and
in time the square and the launch view, each a kit room the robust route makes (tools/props/library/route.py) and
HubKit draws, the hub's way (hub_kit.py): code only lays out, every visible piece is a made model.

    python3 tools/props/scene/earth_outside_kit.py street <out.json>     # writes the laid-out place, prints its counts

Frame: EarthSite's own metres (x across the block, the street at +x, the square at -x; z along the street, +z
towards the capsule; y up from the street). The numbers are read from earth_site.gd and street_fittings.gd themselves
(`constants`), so a wall moved there moves its pieces here.

Every piece is written as the hub's are: its kind (`<room>_<name>`), where its origin stands (the middle of its foot),
its frame's three axes (x, y, z: its front looks along -z) and the size it is laid at. HubKit fits each made model
into that box.

The tenement faces the street sees (the player's own block either side of the stairwell's bay, the bay's street face
and the block across the road) are dealt the way game/prologue/tenement/tenement.gd deals them, from one seed a face:
a render plate on every bay of every storey with its window's opening cut through it, the window set in its reveal
(a share lit), an air conditioner beside some and a cage round others, a band along each floor, drainpipes, and along
the ground floor a shop in each bay behind its shutter with its sign over it.
"""
import json
import pathlib
import random
import re
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
SITE = REPO / "game/prologue/earth_site/earth_site.gd"
FITTINGS = REPO / "game/prologue/street_fittings/street_fittings.gd"
UP = np.array([0.0, 1.0, 0.0])

# A storey of the blocks (Tenement.STOREY) and how wide a bay is meant to be along a face (Tenement.BAY).
STOREY = 3.0
BAY = 3.8
# A window's box (its sill, frame and panes), the opening cut for it in its plate, and how high its foot (the sill's)
# stands over its storey's floor (Tenement's window: 1.5 x 1.4 of glass in a 0.07 frame over a sill at 0.9).
WINDOW = (1.64, 1.62, 0.2)
WINDOW_FOOT = 0.75
# A face's render plates: how thick (the window's reveal); their back lies on the block's own face.
PLATE_DEEP = 0.15
# The band along each floor (Tenement.BAND), a drainpipe (every PIPE_EVERY bays, from PIPE_FOOT up, PIPE thick, off the
# bands).
BAND = (0.16, 0.08)
PIPE = 0.1
PIPE_EVERY = 3
PIPE_FOOT = 3.7
# What is dealt on each window (Tenement's shares): lit, an air conditioner beside it, a cage round it.
LIT_SHARE = 0.3
AC_SHARE = 0.45
CAGE_SHARE = 0.22
AC = (0.8, 0.55, 0.32)
AC_GAP = 0.2
AC_UNDER = 0.25
CAGE = (1.88, 1.78, 0.38)
# A shop on the ground floor: the opening in its plate (its shutter or its front fills it), the sign over it.
SHOP_OPENING = (2.8, 2.3)
SHUTTER_DEEP = 0.18
FRONT_DEEP = 0.25
SIGN = (2.4, 0.75, 0.3)
NEON = (2.4, 0.75, 0.2)
SIGN_GAP = 0.06
# The street: the pavements raised over the road behind their kerbs (the concept, K03: wet asphalt between raised
# pavements), as EarthSite stands them (PAVEMENT_NEAR, PAVEMENT_FAR across x, PAVEMENT_HIGH over the road).
KERB = (0.15, 0.14)
ROAD_TOP = 0.02  # the street's floor (EarthSite._build_the_street: a 0.04 box at 0)
PAVED_TOP = ROAD_TOP + 0.12  # EarthSite.PAVEMENT_HIGH; checked against it in street()
TILE = 2.0
SLAB = 0.08
# The water-filled barriers across each end of the road and its pavements, red and white in turn: one barrier's size.
BARRIER = (1.45, 0.8, 0.55)
# The street lamps (the poles of EarthSite's StreetLamps, which stay the light): the box of one, its pole at its -x end
# POLE_IN from the box's edge, its lamp's lens just over the light.
LAMP = (1.0, 5.25, 0.3)
POLE_IN = 0.12
LAMP_POLE_X = 6.5  # EarthSite.LAMP_POLE_X
LAMPS_Z = (-5.0, 3.0, 10.0)  # earth_site.tscn's StreetLamps
# The neighbourhood's notice board and the poster stand on the near pavement, out from the bay's face: their boxes,
# and where each stands along the street (z).
NOTICE = (0.95, 1.85, 0.14)
NOTICE_Z = -7.2
POSTER = (0.62, 1.15, 0.6)
POSTER_Z = -3.4
# The canopy over the street door: across the door, how high, how far out.
CANOPY = (1.8, 0.3, 0.9)
CANOPY_HIGH = 2.65
# Shops along the ground floors, by face, from the bay whose middle is nearest each z (the concept's picked street, K03
# and K06: the grain and oil shop, the barber's open and lit, the hardware shop across the road; the tea restaurant on
# the player's own block, by the car).
SHOP_WORDS = ("sign_grain_oil", "sign_barber", "sign_hardware", "sign_pharmacy", "sign_laundry", "sign_store",
              "sign_watches", "sign_books", "sign_electric")
SHOPS = {"across": {-4.0: "sign_grain_oil", 2.5: "sign_barber", 8.5: "sign_hardware"},
         "own_south": {5.2: "tea"}}
OPEN_SHOPS = {"across": (2.5,)}
SEEDS = {"own_north": 104, "own_south": 105, "across": 103, "bay": 106}
# The density pass (the owner's concept density rule, 2026-10-08; concepts K03 and K06): awnings and drying racks at the
# uncaged windows of the street's faces (their shares and boxes), the gas pipe along each face over the shop signs, the
# meter box beside each shop, the vent and the barber's pole, the menu board, the road's yellow lines, the harbour wall
# and its fence across both ends of the street.
AWNING_SHARE = 0.35
RACK_SHARE = 0.4
AWNING = (WINDOW[0] + 0.3, 0.45, 0.6)
RACK = (WINDOW[0] + 0.1, 0.3, 0.75)
GAS_PIPE = (0.12, 0.1)
GAS_PIPE_HIGH = 3.45
METER = (0.35, 0.95, 0.15)
VENT = (0.6, 0.6, 0.05)
BARBER_POLE = (0.24, 0.9, 0.3)
MENU = (0.55, 1.0, 0.55)
LINE = (0.12, 0.004)
END_WALL = (1.0, 0.35)
END_FENCE = 1.6


# --- the site's own numbers ----------------------------------------------------------------------------------------

NUMBER = r"-?\d+(?:\.\d+)?"


def _numbers(text):
    """The numbers inside a constructor's brackets (`Vector3(1, 2, 3)`: never the 3 of its name)."""
    inside = text[text.index("(") + 1:text.rindex(")")] if "(" in text else text
    return [float(value) for value in re.findall(NUMBER, inside)]


def _joined_lines(script):
    """A script with every constant written over several lines (an array whose brackets close lines later) on one."""
    lines, joined = script.splitlines(), []
    while lines:
        line = lines.pop(0)
        while line.startswith("const ") and line.count("[") > line.count("]") and lines:
            line += " " + lines.pop(0).strip()
        joined.append(line)
    return "\n".join(joined)


def constants(path):
    """A script's plain constants: numbers, Vector2/3, Rect2, arrays of numbers, of Vector3 and of AABBs, by name; a
    name of a number constant written earlier inside one is read as its value (`Vector3(-45.5, BIG_STAGE_DECK, -3.5)`);
    anything else is left out."""
    found = {}
    script = pathlib.Path(path).read_text()
    script = _joined_lines(script)
    # Twice, so a constant written with the name of one declared after it is read on the second pass.
    for name, value in re.findall(r"^const (\w+)\s*(?::\s*[^=]+)?:?=\s*(.+)$", script, re.MULTILINE) * 2:
        value = value.split("##")[0].strip()
        value = re.sub(r"\b[A-Z][A-Z0-9_]+\b", lambda named: str(found[named.group(0)])
                       if isinstance(found.get(named.group(0)), float) else named.group(0), value)
        if re.fullmatch(NUMBER, value):
            found[name] = float(value)
        elif re.fullmatch(rf"(Vector2|Vector3|Rect2)\(\s*{NUMBER}(\s*,\s*{NUMBER})*\s*\)", value):
            found[name] = _numbers(value)
        elif re.fullmatch(rf"\[(\s*Vector3\(\s*{NUMBER}(\s*,\s*{NUMBER}){{2}}\s*\)\s*,?)+\s*\]", value):
            found[name] = [_numbers(item) for item in re.findall(r"Vector3\([^)]*\)", value)]
        elif re.fullmatch(rf"\[(\s*{NUMBER}\s*,?)+\]", value):
            found[name] = [float(item) for item in re.findall(NUMBER, value)]
        elif value.startswith("[") and value.count("AABB(") > 0:
            found[name] = [_numbers(first) + _numbers(second) for first, second in
                           re.findall(r"AABB\((Vector3\([^)]*\)),\s*(Vector3\([^)]*\))\)", value)]
    return found


def square_blocks_at(path=SITE):
    """EarthSite.BLOCKS: each tenement down the square's sides, where it stands and how it is turned (+1 for a
    quarter turn, -1 for a quarter turn back)."""
    text = pathlib.Path(path).read_text()
    listed = text[text.index("const BLOCKS := ["):text.index("\n]", text.index("const BLOCKS := ["))]
    return [(_numbers(at), -1.0 if minus else 1.0)
            for at, minus in re.findall(r"\[(Vector3\([^)]*\)),\s*(-?)PI / 2\.0", listed)]


def site():
    """EarthSite's numbers, with the street fittings' under their own names (prefixed FITTINGS_)."""
    found = constants(SITE)
    found.update({f"FITTINGS_{name}": value for name, value in constants(FITTINGS).items()})
    for letter, (at, _) in zip("ABCD", square_blocks_at()):
        found[f"BLOCK_{letter}"] = at
    return found


# --- laying a piece ------------------------------------------------------------------------------------------------

def frame_facing(front, up):
    """A piece's axes (x, y, z) for a front looking along `front` with its height along `up` (hub_kit.frame_facing)."""
    z = -np.asarray(front, dtype=np.float64)
    z /= np.linalg.norm(z)
    y = np.asarray(up, dtype=np.float64)
    y = y - z * (y @ z)
    y /= np.linalg.norm(y)
    return np.cross(y, z), y, z


def piece(room, kind, origin, axes, size, **shown):
    """One laid piece, as the hub's are written, with what its model shows beyond its size (`openings`, `label`)."""
    x, y, z = axes
    found = {"kind": f"{room}_{kind}", "at": [round(float(value), 4) for value in origin],
             "x": [round(float(value), 5) for value in x], "y": [round(float(value), 5) for value in y],
             "z": [round(float(value), 5) for value in z], "size": [round(float(value), 4) for value in size],
             "layer": 1}
    found.update(shown)
    return found


def cut(left, foot, wide, tall):
    """An opening in a plate's own frame: [x0, y0, x1, y1]."""
    return [round(left, 4), round(foot, 4), round(left + wide, 4), round(foot + tall, 4)]


class Face:
    """A face of a block, as Tenement's: a plane out along `out` through `middle` (on the ground), `length` long and
    `tall` high, its ground (where its ground floor stands) at `ground`. `along` runs as a piece's own x on it: seen
    from in front, to the viewer's left."""

    def __init__(self, middle, out, length, tall, ground=0.0):
        self.middle = np.asarray(middle, dtype=np.float64)
        self.out = np.asarray(out, dtype=np.float64)
        self.along = np.cross(self.out, UP)
        self.length = length
        self.tall = tall
        self.ground = ground

    def on(self, room, kind, along, up, size, proud=0.0, **shown):
        """A piece with its back `proud` off the face, its foot's middle `along` the face and `up` from y = 0,
        facing out."""
        origin = self.middle + self.along * along + UP * up + self.out * (proud + size[2] / 2)
        return piece(room, kind, origin, frame_facing(self.out, UP), size, **shown)

    def along_of(self, point_z):
        """Where a z on the face lies along it (the street's faces run along z)."""
        return float((np.array([0.0, 0.0, point_z]) - self.middle) @ self.along)

    def bays(self):
        count = max(1, round(self.length / BAY))
        wide = self.length / count
        return [(-self.length / 2 + wide * (index + 0.5), wide) for index in range(count)]


def flat(room, kind, middle, along, size, top):
    """A piece lying with its front up, `size` (wide along `along`, long across it, thick), its top at `top`."""
    wide, long, thick = size
    along = np.asarray(along, dtype=np.float64)
    across = np.cross(UP, along)
    origin = np.asarray([middle[0], 0.0, middle[1]], dtype=np.float64) - across * long / 2 \
        + UP * (top - thick / 2)
    return piece(room, kind, origin, frame_facing(UP, across), size)


# --- the tenement faces ---------------------------------------------------------------------------------------------

def storeys(room, face, rng, from_storey=1, prefix=""):
    """A face's storeys over the ground floor (from `from_storey`), Tenement's way: a render plate per bay and storey
    with its window's opening, the window (dark or lit) set in it, an air conditioner beside some and a cage round
    others, a band along each floor; on the street's own faces an awning or a drying rack at some uncaged windows."""
    found = []
    gear = random.Random(round(float(np.abs(face.middle).sum()) * 1000))
    for along, wide in face.bays():
        for storey in range(from_storey, int(face.tall // STOREY)):
            floor = storey * STOREY
            found.append(face.on(room, f"{prefix}render_upper", along, floor, (wide, STOREY, PLATE_DEEP),
                                 openings=[cut(-WINDOW[0] / 2, WINDOW_FOOT, WINDOW[0], WINDOW[1])]))
            lit = rng.random() < LIT_SHARE
            found.append(face.on(room, f"{prefix}window_lit" if lit else f"{prefix}window_dark", along,
                                 floor + WINDOW_FOOT, WINDOW))
            middle = floor + WINDOW_FOOT + 0.08 + (WINDOW[1] - 0.08) / 2
            room_beside = (wide - WINDOW[0]) / 2
            if rng.random() < AC_SHARE and room_beside > AC[0] + AC_GAP:
                side = 1.0 if rng.random() < 0.5 else -1.0
                found.append(face.on(room, f"{prefix}ac_unit", along + side * (WINDOW[0] / 2 + AC_GAP + AC[0] / 2),
                                     middle - AC_UNDER - AC[1] / 2, AC, proud=PLATE_DEEP))
            caged = rng.random() < CAGE_SHARE
            if caged:
                found.append(face.on(room, f"{prefix}window_cage", along, middle - CAGE[1] / 2, CAGE, proud=PLATE_DEEP))
            found.append(face.on(room, f"{prefix}facade_band", along, floor - BAND[0] / 2, (wide, BAND[0], BAND[1]),
                                 proud=PLATE_DEEP))
            if not prefix and not caged:
                found += window_gear(room, face, along, floor, gear)
    return found


def window_gear(room, face, along, floor, gear):
    """What the concept hangs at an uncaged window (K03: the street's own faces): a sheet-metal awning over some, a
    drying rack under the sill of others; dealt from a generator of its own, so the windows' dealing stands."""
    found = []
    top = floor + WINDOW_FOOT + WINDOW[1]
    if gear.random() < AWNING_SHARE:
        found.append(face.on(room, "window_awning", along, top + 0.04, AWNING, proud=PLATE_DEEP))
    elif gear.random() < RACK_SHARE:
        found.append(face.on(room, "drying_rack", along, floor + WINDOW_FOOT - RACK[1] - 0.02, RACK,
                             proud=PLATE_DEEP))
    return found


def drainpipes(room, face, foot=PIPE_FOOT, prefix=""):
    """A drainpipe down the face at every PIPE_EVERY'th bay's edge, from `foot` to its top."""
    bays = face.bays()
    return [face.on(room, f"{prefix}drainpipe", bays[index][0] - bays[index][1] / 2, foot, (PIPE, face.tall - foot, PIPE),
                    proud=PLATE_DEEP + BAND[1])
            for index in range(PIPE_EVERY, len(bays), PIPE_EVERY)]


def shop_front(room, face, along, wide, named, is_open, prefix=""):
    """A bay's shop on the ground floor: its plate with the shop's opening, the shutter pulled down (or the tea
    restaurant's lit front, or an open shop's lit window) and the sign over it (the tea restaurant's in neon)."""
    ground = face.ground
    found = [face.on(room, f"{prefix}render_shop", along, ground, (wide, STOREY - ground, PLATE_DEEP),
                     openings=[cut(-SHOP_OPENING[0] / 2, 0.0, SHOP_OPENING[0], SHOP_OPENING[1])])]
    sign_foot = ground + SHOP_OPENING[1] + SIGN_GAP
    if named == "tea":
        found.append(face.on(room, "tea_front", along, ground, (SHOP_OPENING[0], SHOP_OPENING[1], FRONT_DEEP)))
        found.append(face.on(room, "neon_sign", along, sign_foot, NEON, proud=PLATE_DEEP + BAND[1],
                             label="sign_tea_restaurant"))
        return found
    if is_open:
        found.append(face.on(room, f"{prefix}shop_open", along, ground, (SHOP_OPENING[0], SHOP_OPENING[1], FRONT_DEEP)))
    else:
        found.append(face.on(room, f"{prefix}shop_shutter", along, ground, (SHOP_OPENING[0], SHOP_OPENING[1],
                                                                   SHUTTER_DEEP)))
    found.append(face.on(room, f"{prefix}shop_sign", along, sign_foot, SIGN, proud=PLATE_DEEP + BAND[1], label=named))
    return found


def shop_face(room, face, seed, shops, open_shops, prefix=""):
    """A tenement face with a shop in every ground floor bay (`shops`: z -> its sign, or "tea"; `open_shops`: the z of
    the ones still open), its storeys and its drainpipes."""
    found = []
    for index, (along, wide) in enumerate(face.bays()):
        named = next((what for at, what in shops.items() if abs(face.along_of(at) - along) < wide / 2), None)
        is_open = any(abs(face.along_of(at) - along) < wide / 2 for at in open_shops)
        found += shop_front(room, face, along, wide, named or SHOP_WORDS[(seed + index * 4) % len(SHOP_WORDS)],
                            is_open, prefix)
    found += storeys(room, face, random.Random(seed), prefix=prefix)
    if not prefix:
        found += shop_gear(room, face, open_shops)
    return found + drainpipes(room, face, prefix=prefix)


def shop_gear(room, face, open_shops):
    """Along a street face's shops: the gas pipe over the signs, a meter box beside each shop's opening, and the
    barber's pole beside the open shop's door (the concept's K06)."""
    found = []
    for along, wide in face.bays():
        found.append(face.on(room, "facade_pipe", along, GAS_PIPE_HIGH, (wide, GAS_PIPE[0], GAS_PIPE[1]),
                             proud=PLATE_DEEP))
        found.append(face.on(room, "meter_box", along + SHOP_OPENING[0] / 2 + 0.3, face.ground + 1.1, METER,
                             proud=PLATE_DEEP))
        if any(abs(face.along_of(at) - along) < wide / 2 for at in open_shops):
            found.append(face.on(room, "barber_pole", along - SHOP_OPENING[0] / 2 - 0.3, face.ground + 1.6,
                                 BARBER_POLE, proud=PLATE_DEEP))
    return found


# --- the street -----------------------------------------------------------------------------------------------------

def street_faces(numbers):
    """The tenement faces the street sees: the player's own block north and south of the stairwell's bay, the bay's
    own street face, and the block across the road; each one's ground floor on the pavement."""
    own_x = numbers["OWN_BLOCKS_AT"][0][0] + numbers["OWN_BLOCK_SIZE"][0] / 2
    own_long = numbers["OWN_BLOCK_SIZE"][2]
    tall = numbers["BUILDING_TOP"]
    faces = {}
    for name, block in zip(("own_north", "own_south"), numbers["OWN_BLOCKS_AT"]):
        faces[name] = Face((own_x, 0.0, block[2]), (1.0, 0.0, 0.0), own_long, tall, PAVED_TOP)
    across = numbers["ACROSS_BLOCK_AT"]
    across_x = across[0] - numbers["BLOCK_SIZE"][0] / 2
    faces["across"] = Face((across_x, 0.0, across[2]), (-1.0, 0.0, 0.0), numbers["BLOCK_SIZE"][2], tall, PAVED_TOP)
    stairs = numbers["STAIRWELL_GROUND"]
    wall = numbers["WALL"]
    bay_x = stairs[0] + stairs[2] + wall
    bay_from, bay_to = stairs[1] - wall, stairs[1] + stairs[3] + wall
    faces["bay"] = Face((bay_x, 0.0, (bay_from + bay_to) / 2), (1.0, 0.0, 0.0), bay_to - bay_from, tall, PAVED_TOP)
    return faces


def kerb_lines(numbers):
    """The two kerbs' road edges: x of the near and the far one (EarthSite's pavements end there)."""
    return numbers["PAVEMENT_NEAR"][1], numbers["PAVEMENT_FAR"][0]


def street_ground(room, numbers, faces):
    """The road between its kerbs, the raised pavements either side up to the faces, the kerbs: from one end of the
    block across the road to the other."""
    kerb_near, kerb_far = kerb_lines(numbers)
    near_face = float(faces["bay"].middle[0])
    far_face = float(faces["across"].middle[0])
    across = faces["across"]
    start, end = float(across.middle[2] - across.length / 2), float(across.middle[2] + across.length / 2)
    tiles = max(1, round((end - start) / TILE))
    long = (end - start) / tiles
    along = np.array([0.0, 0.0, 1.0])
    found = []
    for low, high, kind, top in ((kerb_near + KERB[0], kerb_far - KERB[0], "ground_asphalt", ROAD_TOP),
                                 (near_face, kerb_near, "ground_paving", PAVED_TOP),
                                 (kerb_far, far_face, "ground_paving", PAVED_TOP)):
        for index in range(tiles):
            middle = ((low + high) / 2, start + long * (index + 0.5))
            found.append(flat(room, kind, middle, along, (long, high - low, SLAB), top))
    for edge, facing in ((kerb_near, 1.0), (kerb_far, -1.0)):
        face = Face((edge, 0.0, 0.0), (facing, 0.0, 0.0), end - start, KERB[1])
        for index in range(tiles):
            middle_z = start + long * (index + 0.5)
            found.append(face.on(room, "kerb_stone", face.along_of(middle_z), PAVED_TOP - KERB[1],
                                 (long, KERB[1], KERB[0]), proud=-KERB[0]))
    return found


def street_barriers(room, numbers, faces):
    """The water-filled barriers across both ends of the street, red and white in turn: three across the road between
    its kerbs and one on each pavement."""
    street = numbers["STREET_GROUND"]
    wall = numbers["WALL"]
    kerb_near, kerb_far = kerb_lines(numbers)
    near_face = float(faces["own_north"].middle[0]) + PLATE_DEEP
    far_face = float(faces["across"].middle[0]) - PLATE_DEEP
    road = kerb_far - kerb_near - 2 * KERB[0]
    spots = [(kerb_near + KERB[0] + road * (index + 0.5) / 3, ROAD_TOP) for index in range(3)]
    spots += [((near_face + kerb_near) / 2, PAVED_TOP), ((kerb_far + far_face) / 2, PAVED_TOP)]
    found = []
    for end_z, facing in ((street[1] - wall / 2, 1.0), (street[1] + street[3] + wall / 2, -1.0)):
        for index, (x, foot) in enumerate(sorted(spots)):
            kind = "water_barrier_red" if index % 2 == 0 else "water_barrier_white"
            found.append(piece(room, kind, (x, foot, end_z), frame_facing((0.0, 0.0, facing), UP), BARRIER))
    return found


def bay_face(room, numbers, face):
    """The stairwell's bay seen from the street: up to the flat's roof one rendered plate with the street door's and
    the half landings' windows cut through it (the stairwell's own glass and bars stand in them), an air conditioner
    under each window, the canopy over the door; over it the storeys of the block like the rest."""
    stair_top = numbers["FLAT_LEVEL"] + numbers["FLAT_HEIGHT"] + numbers["WALL"]
    door_along = face.along_of(numbers["FRONT_DOOR_Z"])
    door = numbers["STREET_DOORWAY"]
    window_along = face.along_of(numbers["FITTINGS_WINDOW_Z"])
    window = numbers["FITTINGS_WINDOW"]
    sill = numbers["FITTINGS_WINDOW_SILL"]
    rise = numbers["FLIGHT_RISE"]
    half_landings = [rise * step for step in range(1, int(numbers["FLAT_LEVEL"] / rise), 2)]
    openings = [cut(door_along - door[0] / 2, 0.0, door[0], door[1] - face.ground)]
    openings += [cut(window_along - window[0] / 2, level + sill - face.ground, window[0], window[1])
                 for level in half_landings]
    # In storeys' plates, cut between the half landings' windows, so no one plate takes a whole picture set.
    found = []
    bands = [face.ground] + [level + sill - 0.25 for level in half_landings] + [stair_top]
    for low, high in zip(bands, bands[1:]):
        own = [[x0, y0 - (low - face.ground), x1, y1 - (low - face.ground)] for x0, y0, x1, y1 in openings
               if y0 + face.ground < high and y1 + face.ground > low]
        found.append(face.on(room, "render_lower", 0.0, low, (face.length, high - low, PLATE_DEEP),
                             **({"openings": own} if own else {})))
    for level in half_landings:
        found.append(face.on(room, "ac_unit", window_along, level + sill - 0.15 - AC[1], AC, proud=PLATE_DEEP))
    found.append(face.on(room, "door_canopy", door_along, CANOPY_HIGH, CANOPY, proud=PLATE_DEEP))
    found.append(face.on(room, "vent_louvre", door_along + 1.6, face.ground + 1.2, VENT, proud=PLATE_DEEP))
    found.append(face.on(room, "shop_sign", door_along, CANOPY_HIGH + CANOPY[1] + 0.1, SIGN, proud=PLATE_DEEP,
                         label="sign_block_name"))
    found += storeys(room, face, random.Random(SEEDS["bay"]), from_storey=int(round(stair_top / STOREY)))
    return found


def street_furniture(room, numbers, faces):
    """What stands on the near pavement: the street lamps on their poles, the notice board and the poster stand."""
    found = []
    pavement = PAVED_TOP
    for at_z in LAMPS_Z:
        origin = (LAMP_POLE_X - (-LAMP[0] / 2 + POLE_IN), pavement, at_z)
        found.append(piece(room, "street_lamp", origin, frame_facing((0.0, 0.0, -1.0), UP), LAMP))
    face_x = float(faces["bay"].middle[0]) + PLATE_DEEP
    found.append(piece(room, "notice_case", (face_x + 0.25, pavement, NOTICE_Z), frame_facing((1.0, 0.0, 0.0), UP),
                       NOTICE))
    found.append(piece(room, "poster_stand", (face_x + 0.1 + POSTER[2] / 2, pavement, POSTER_Z),
                       frame_facing((1.0, 0.0, 0.0), UP), POSTER))
    tea_z = next(at for at, what in SHOPS["own_south"].items() if what == "tea")
    own_face = float(faces["own_south"].middle[0]) + PLATE_DEEP
    found.append(piece(room, "menu_board", (own_face + 0.4 + MENU[2] / 2, pavement, tea_z + 1.9),
                       frame_facing((1.0, 0.0, 0.0), UP), MENU))
    return found


def street_ends(room, numbers, faces):
    """The road's yellow lines along both kerbs, and the harbour wall with its fence across each end of the street,
    where the block across the road ends (the concept's runner-up K06 closes the street with them)."""
    kerb_near, kerb_far = kerb_lines(numbers)
    across = faces["across"]
    start, end = float(across.middle[2] - across.length / 2), float(across.middle[2] + across.length / 2)
    along = np.array([0.0, 0.0, 1.0])
    found = []
    for x in (kerb_near + KERB[0] + 0.15, kerb_far - KERB[0] - 0.15):
        tiles = max(1, round((end - start) / TILE))
        long = (end - start) / tiles
        for index in range(tiles):
            found.append(flat(room, "road_line", (x, start + long * (index + 0.5)), along, (long, LINE[0], LINE[1]),
                              ROAD_TOP + LINE[1]))
    near_face = float(faces["bay"].middle[0])
    far_face = float(across.middle[0])
    middle_x = (near_face + far_face) / 2
    for end_z, facing in ((start, 1.0), (end, -1.0)):
        wall = Face((middle_x, 0.0, end_z), (0.0, 0.0, facing), far_face - near_face, END_WALL[0])
        found.append(wall.on(room, "end_wall", 0.0, 0.0, (far_face - near_face, END_WALL[0], END_WALL[1]),
                             proud=-END_WALL[1]))
        found.append(wall.on(room, "end_fence", 0.0, END_WALL[0], (far_face - near_face, END_FENCE, 0.06),
                             proud=-END_WALL[1] / 2 - 0.03))
    return found


def street(numbers):
    """The street's kit: its ground, its barriers, the faces it sees and what stands on its pavement."""
    room = "street"
    if abs(numbers["PAVEMENT_HIGH"] - (PAVED_TOP - ROAD_TOP)) > 1e-6:
        raise SystemExit("EarthSite.PAVEMENT_HIGH moved: PAVED_TOP here must follow it")
    faces = street_faces(numbers)
    found = street_ground(room, numbers, faces)
    found += street_barriers(room, numbers, faces)
    for name in ("own_north", "own_south", "across"):
        found += shop_face(room, faces[name], SEEDS[name], SHOPS.get(name, {}), OPEN_SHOPS.get(name, ()))
    found += bay_face(room, numbers, faces["bay"])
    found += street_furniture(room, numbers, faces)
    found += street_ends(room, numbers, faces)
    return found



# --- the square ------------------------------------------------------------------------------------------------------
# Everything here is seen from the balcony, 10 to 120 m off and never walked: its kinds are `far_` ones (route.py's
# DISTANT texels a metre), but for the player's own block's faces either side of the balcony, seen close.

SQUARE_TILE = 10.0
TERRACE_TOP_SKIN = 0.04
ROAD_SLAB = 0.1
PROMENADE = (-110.0, -96.0)  # x: the harbour's edge (EarthSite.HARBOUR_EDGE) to the far road's outer edge
PROMENADE_REACH = 100.0  # how far along z either way the promenade runs
RAIL = (4.0, 1.1, 0.08)
PALM_EVERY = 10.0
PALM = (3.6, 7.0, 3.6)
FLAG = (0.9, 6.0, 0.3)
FLAG_EVERY = 6.0
FLAG_IN = 2.5  # how far in from the square's long edges the rows of flags stand
LANTERN = (0.45, 0.65, 0.45)
LANTERN_EVERY = 4.0
# The flags held up through the crowd, and the crowd rail out in front of the stage (the density pass).
CROWD_FLAGS = 40
CROWD_FLAG_SEED = 1031
CROWD_RAIL_OUT = 1.5
LANTERN_HIGH = 7.5  # where the strings hang, under the lamps' heads
LANTERN_SAG = 1.5
CABLE = 0.03
TOWER = (3.4, 20.0, 1.6)
SQUARE_LAMP = (1.6, 6.2, 0.4)
BLOCK_SEED = 113
BANNER = (2.2, 9.0, 0.3)
PODIUM = (5.0, 0.94, 3.72)
LECTERN = (0.7, 1.15, 0.5)
NEON_COLUMN = (1.8, 4.6, 0.3)
NEON_WORDS = ("sign_column_restaurant", "sign_column_store")
BALCONY_SLAB = 0.2
BALCONY_RAIL_HIGH = 1.1


def square_blocks(numbers):
    """The tenements down the square's long sides as faces: each block's face to the square and its two ends, with
    its shops on the face to the square (Tenement's shop face, the square side)."""
    size = numbers["BLOCK_SIZE"]
    faces = []
    for at, turn in ((numbers["BLOCK_A"], 1.0), (numbers["BLOCK_B"], 1.0), (numbers["BLOCK_C"], -1.0),
                     (numbers["BLOCK_D"], -1.0)):
        middle = np.array([at[0], 0.0, at[2]])
        toward = np.array([0.0, 0.0, turn])  # the face to the square
        along_long = np.array([1.0, 0.0, 0.0])
        faces.append(("shops", Face(middle + toward * size[0] / 2, toward, size[2], size[1])))
        for end in (1.0, -1.0):
            faces.append(("plain", Face(middle + along_long * end * size[2] / 2, along_long * end, size[0],
                                        size[1])))
    return faces


def plain_face(room, face, seed, prefix):
    """A tenement face with no shops: a render plate along its ground floor, its storeys and drainpipes."""
    found = []
    for along, wide in face.bays():
        found.append(face.on(room, f"{prefix}render_lower", along, face.ground,
                             (wide, STOREY - face.ground, PLATE_DEEP)))
    found += storeys(room, face, random.Random(seed), prefix=prefix)
    return found + drainpipes(room, face, prefix=prefix)


def square_ground(room, numbers):
    """The square's paving, its three terraces (each a block of stone paved on top, its half steps round it), the
    roads round three sides of it, the promenade along the harbour with its rail and its palms."""
    found = []
    square = numbers["SQUARE_GROUND"]
    along = np.array([1.0, 0.0, 0.0])
    for x0 in np.arange(square[0], square[0] + square[2] - 1e-6, SQUARE_TILE):
        for z0 in np.arange(square[1], square[1] + square[3] - 1e-6, SQUARE_TILE):
            wide = min(SQUARE_TILE, square[0] + square[2] - x0)
            long = min(SQUARE_TILE, square[1] + square[3] - z0)
            found.append(flat(room, "far_paving", (x0 + wide / 2, z0 + long / 2), along, (wide, long, ROAD_SLAB),
                              ROAD_TOP - 0.02))
    for low, high in terraces(numbers):
        # Each terrace in blocks no more than a paving tile's reach across, so no one block takes a picture set.
        across = max(1, int(np.ceil((high[0] - low[0]) / SQUARE_TILE)))
        down = max(1, int(np.ceil((high[2] - low[2]) / SQUARE_TILE)))
        wide, long = (high[0] - low[0]) / across, (high[2] - low[2]) / down
        for column in range(across):
            for row in range(down):
                middle = (low[0] + wide * (column + 0.5), low[2] + long * (row + 0.5))
                found.append(flat(room, "far_terrace", middle, along, (wide, long, high[1] + 0.02), high[1]))
    out, wide = numbers["ROAD_OFF_THE_PAVING"], numbers["ROAD_WIDTH"]
    far_end = square[0] - out - wide
    long_way = square[0] + square[2] - far_end
    for side_z in (square[1] - out - wide / 2, square[1] + square[3] + out + wide / 2):
        for x0 in np.arange(far_end, far_end + long_way - 1e-6, SQUARE_TILE):
            length = min(SQUARE_TILE, far_end + long_way - x0)
            found.append(flat(room, "far_road", (x0 + length / 2, side_z), along, (length, wide, ROAD_SLAB),
                              ROAD_TOP - 0.03))
    across = square[3] + 2 * (out + wide)
    for z0 in np.arange(square[1] - out - wide, square[1] - out - wide + across - 1e-6, SQUARE_TILE):
        length = min(SQUARE_TILE, square[1] - out - wide + across - z0)
        found.append(flat(room, "far_road", (far_end + wide / 2, z0 + length / 2), np.array([0.0, 0.0, 1.0]),
                          (length, wide, ROAD_SLAB), ROAD_TOP - 0.03))
    edge, inner = PROMENADE
    for z0 in np.arange(-PROMENADE_REACH, PROMENADE_REACH - 1e-6, SQUARE_TILE):
        found.append(flat(room, "far_promenade", ((edge + inner) / 2, z0 + SQUARE_TILE / 2),
                          np.array([0.0, 0.0, 1.0]), (SQUARE_TILE, inner - edge, ROAD_SLAB), ROAD_TOP - 0.02))
    rail_face = Face((edge, 0.0, 0.0), (1.0, 0.0, 0.0), 2 * PROMENADE_REACH, RAIL[1])
    for z0 in np.arange(-PROMENADE_REACH, PROMENADE_REACH - 1e-6, RAIL[0]):
        found.append(rail_face.on(room, "far_promenade_rail", rail_face.along_of(z0 + RAIL[0] / 2), ROAD_TOP - 0.02,
                                  RAIL, proud=0.1))
    for z0 in np.arange(-PROMENADE_REACH + PALM_EVERY / 2, PROMENADE_REACH, PALM_EVERY):
        found.append(piece(room, "far_palm", ((edge + inner) / 2, ROAD_TOP - 0.02, z0),
                           frame_facing((1.0, 0.0, 0.0), UP), PALM))
    return found


def terraces(numbers):
    """The square's raised ground, as EarthSite.square_ground() builds it: each terrace and the half step a tread wide
    round its balcony side and its two long sides, as [low, high] corners."""
    tread, half = numbers["TIER_TREAD"], numbers["TIER_HALF_STEP"]
    found = []
    for tier in numbers["SQUARE_TIERS"]:
        (x, y, z), (sx, sy, sz) = tier[:3], tier[3:]
        found.append(([x, 0.0, z - tread], [x + sx + tread, y + sy - half, z + sz + tread]))
        found.append(([x, 0.0, z], [x + sx, y + sy, z + sz]))
    return found


def stage(room, numbers):
    """The stage: its deck with the red skirt and the steps, the red backdrop behind it with the first sign across its
    top, the podium and the lectern the leader stands at, the two banners either side down their poles."""
    ground = numbers["BIG_STAGE_GROUND"]
    deck = numbers["BIG_STAGE_DECK"]
    found = []
    middle_z = ground[1] + ground[3] / 2
    toward_balcony = (1.0, 0.0, 0.0)
    found.append(piece(room, "far_stage", (ground[0] + ground[2] / 2, 0.0, middle_z),
                       frame_facing(toward_balcony, UP), (ground[3], deck, ground[2])))
    backdrop = numbers["BACKDROP"]
    found.append(piece(room, "far_backdrop", (ground[0] - backdrop[0] / 2, 0.0, middle_z),
                       frame_facing(toward_balcony, UP), (ground[3], backdrop[1], backdrop[0]),
                       label="banner_first"))
    podium = numbers["PODIUM_AT"]
    found.append(piece(room, "far_podium", (podium[0], deck, podium[2]), frame_facing(toward_balcony, UP),
                       (PODIUM[0], PODIUM[1], PODIUM[2])))
    leader = numbers["LEADER_ON_THE_STAGE"]
    lectern_x = podium[0] + leader[0] + numbers["LECTERN_OUT"]
    found.append(piece(room, "far_lectern", (lectern_x, deck + PODIUM[1], podium[2] + leader[2]),
                       frame_facing(toward_balcony, UP), LECTERN))
    for at, words in ((numbers["SIGN_AT"][1], "banner_second"), (numbers["SIGN_AT"][2], "banner_third")):
        found.append(piece(room, "far_banner", (at[0], 0.0, at[2]), frame_facing(toward_balcony, UP), BANNER,
                           label=words))
    return found


def square_furniture(room, numbers):
    """The floodlight towers behind the stage, the lamps down both long sides of the square, the rows of flags along
    its edges and the strings of lanterns hung across it from lamp to lamp."""
    found = []
    for at in numbers["FLOODLIGHT_TOWERS"]:
        found.append(piece(room, "far_floodlight_tower", (at[0], 0.0, at[2]), frame_facing((1.0, 0.0, 0.0), UP),
                           TOWER))
    square = numbers["SQUARE_GROUND"]
    lamps = []
    along = square[0] + numbers["LAMP_EVERY"] / 2
    while along < square[0] + square[2]:
        for z, toward in ((square[1] - numbers["LAMP_OFF_THE_PAVING"], 1.0),
                          (square[1] + square[3] + numbers["LAMP_OFF_THE_PAVING"], -1.0)):
            # The lamp's pole at its box's -x end, its arm out over the paving: its frame's x along +z or -z.
            origin = np.array([along, ROAD_TOP, z]) + np.array([0.0, 0.0, toward]) * (SQUARE_LAMP[0] / 2 - 0.1)
            found.append(piece(room, "far_square_lamp", origin, frame_facing((toward, 0.0, 0.0), UP),
                               SQUARE_LAMP))
        lamps.append(along)
        along += numbers["LAMP_EVERY"]
    for z in (square[1] + FLAG_IN, square[1] + square[3] - FLAG_IN):
        x = square[0] + FLAG_EVERY / 2
        while x < square[0] + square[2] - 4.0:
            found.append(piece(room, "far_flag_pole", (x, ROAD_TOP, z), frame_facing((1.0, 0.0, 0.0), UP), FLAG))
            x += FLAG_EVERY
    for x in lamps:
        found += lantern_string(room, x, square[1] - numbers["LAMP_OFF_THE_PAVING"],
                                square[1] + square[3] + numbers["LAMP_OFF_THE_PAVING"])
    return found + crowd_flags(room, numbers) + crowd_rail(room, numbers)


def crowd_flags(room, numbers):
    """Red flags held up all through the crowd (the concept K04), dealt from one seed over the crowd's ground, each
    standing on the terrace it falls on, none on the stage's ground."""
    rng = random.Random(CROWD_FLAG_SEED)
    spread = numbers["CROWD_SPREAD"]
    stage = numbers["BIG_STAGE_GROUND"]
    found = []
    while len(found) < CROWD_FLAGS:
        x = spread[0] + rng.random() * spread[2]
        z = spread[1] + rng.random() * spread[3]
        if stage[0] - 2.0 < x < stage[0] + stage[2] + 2.0 and stage[1] - 2.0 < z < stage[1] + stage[3] + 2.0:
            continue
        foot = max([high[1] for low, high in terraces(numbers) if low[0] <= x <= high[0] and low[2] <= z <= high[2]],
                   default=ROAD_TOP - 0.02)
        found.append(piece(room, "far_flag_pole", (x, foot, z), frame_facing((1.0, 0.0, rng.uniform(-0.3, 0.3)), UP),
                           FLAG))
    return found


def crowd_rail(room, numbers):
    """The crowd rail along the stage's front, between the crowd and the stage (the concept's steel barriers)."""
    stage = numbers["BIG_STAGE_GROUND"]
    face = Face((stage[0] + stage[2] + CROWD_RAIL_OUT, 0.0, stage[1] + stage[3] / 2), (1.0, 0.0, 0.0), stage[3], 1.1)
    return [face.on(room, "far_promenade_rail", along, ROAD_TOP - 0.02, (wide, RAIL[1], RAIL[2]))
            for along, wide in [(-stage[3] / 2 + RAIL[0] * (index + 0.5), RAIL[0])
                                for index in range(int(stage[3] // RAIL[0]))]]


def lantern_string(room, x, from_z, to_z):
    """A string of lanterns hung across the square from one lamp to the one opposite: the cable in straight runs from
    lantern to lantern, sagging LANTERN_SAG at its middle, a lantern hung at every LANTERN_EVERY."""
    count = int((to_z - from_z) / LANTERN_EVERY)
    points = []
    for index in range(count + 1):
        share = index / count
        z = from_z + (to_z - from_z) * share
        points.append(np.array([x, LANTERN_HIGH - LANTERN_SAG * 4 * share * (1 - share), z]))
    found = []
    for start, end in zip(points, points[1:]):
        run = end - start
        length = float(np.linalg.norm(run))
        # A cable run lies along its own y (a plain pipe's frame), from `start`.
        found.append(piece(room, "far_cable", start, frame_facing(np.cross(run / length, (1.0, 0.0, 0.0)), run),
                           (CABLE, length, CABLE)))
    for point in points[1:-1]:
        found.append(piece(room, "far_lantern", point - UP * LANTERN[1], frame_facing((1.0, 0.0, 0.0), UP),
                           LANTERN))
    return found


def own_block_west(room, numbers):
    """The player's own block either side of the bay, seen from the balcony along its face to the square: shops along
    its ground floor, its storeys, drainpipes, and the two neon signs hung out from it."""
    found = []
    own_x = numbers["OWN_BLOCKS_AT"][0][0] - numbers["OWN_BLOCK_SIZE"][0] / 2
    for index, block in enumerate(numbers["OWN_BLOCKS_AT"]):
        face = Face((own_x, 0.0, block[2]), (-1.0, 0.0, 0.0), numbers["OWN_BLOCK_SIZE"][2], numbers["BUILDING_TOP"])
        found += shop_face(room, face, BLOCK_SEED + index, {}, (), prefix="")
    for index, at in enumerate(numbers["NEON_SIGNS_AT"]):
        board = NEON_COLUMN
        origin = (own_x - PLATE_DEEP - board[0] / 2, at[1] - board[1] / 2, at[2])
        toward_the_balcony = 1.0 if numbers["BALCONY_SPOT"][2] > at[2] else -1.0
        found.append(piece(room, "far_neon_column", origin, frame_facing((0.0, 0.0, toward_the_balcony), UP), board,
                           label=NEON_WORDS[index % len(NEON_WORDS)]))
    return found


def bay_stack(room, numbers):
    """The bay the flat is in seen from its balcony: the same balcony on every other floor (its slab, its rail round
    the three open sides) with its window behind it, and a shop's shutter at the foot of the bay."""
    flat = numbers["FLAT_GROUND"]
    balcony = numbers["BALCONY_GROUND"]
    wall = numbers["WALL"]
    face_x = flat[0] - wall
    middle_z = balcony[1] + balcony[3] / 2
    out = np.array([-1.0, 0.0, 0.0])
    found = []
    slab_wide = balcony[3] + 2 * wall
    slab_out = face_x - (balcony[0] - wall)
    for level in numbers["BAY_LEVELS"]:
        found.append(flat_slab(room, (face_x - slab_out / 2, middle_z), (slab_out, slab_wide), level))
        front = Face((balcony[0] - wall / 2, 0.0, middle_z), out, balcony[3] + wall, BALCONY_RAIL_HIGH)
        found.append(front.on(room, "balcony_rail", 0.0, level, (balcony[3] + wall, BALCONY_RAIL_HIGH, 0.06)))
        for side in (-1.0, 1.0):
            side_face = Face((face_x - slab_out / 2 + wall / 4, 0.0, middle_z + side * (balcony[3] + wall) / 2),
                             (0.0, 0.0, side), slab_out - wall / 2, BALCONY_RAIL_HIGH)
            found.append(side_face.on(room, "balcony_rail", 0.0, level, (slab_out - wall / 2, BALCONY_RAIL_HIGH, 0.06),
                                      proud=-0.03))
        window = numbers["BAY_WINDOW"]
        face = Face((face_x, 0.0, middle_z), out, slab_wide, 3.0)
        found.append(face.on(room, "window_dark", 0.0, level + 0.3, (window[0], window[1], WINDOW[2])))
    # The flat's own small windows either side of its balcony door, the drainpipe down the bay's corner and the
    # shop's shutter at its foot.
    spot = numbers["BALCONY_SPOT"]
    face = Face((face_x, 0.0, spot[2]), out, slab_wide, 3.0)
    small = (window[0] * 0.6, window[1] * 0.6, WINDOW[2])
    for along in numbers["FLAT_WALL_WINDOWS"]:
        found.append(face.on(room, "window_dark", face.along_of(spot[2] + along), numbers["FLAT_LEVEL"] + 1.3
                             - small[1] / 2, small))
    pipe = numbers["DRAINPIPE_THICKNESS"]
    found.append(face.on(room, "drainpipe", face.along_of(numbers["DRAINPIPE_Z"]), 0.0,
                         (pipe, numbers["BUILDING_TOP"], pipe), proud=pipe / 2))
    shutter = numbers["BAY_SHUTTER"]
    found.append(face.on(room, "shop_shutter", face.along_of(spot[2]), 0.0, (shutter[0], shutter[1], SHUTTER_DEEP)))
    return found


def flat_slab(room, middle, size, top):
    """A balcony's concrete slab, its top at `top` (a plain plate lying flat)."""
    return flat(room, "balcony_slab", middle, np.array([0.0, 0.0, 1.0]), (size[1], size[0], BALCONY_SLAB), top)


def square(numbers):
    """The square's kit: its ground, the stage, its furniture, the blocks round it, the player's own block's face to
    it and the bay's stack of balconies."""
    room = "square"
    found = square_ground(room, numbers)
    found += stage(room, numbers)
    found += square_furniture(room, numbers)
    for index, (what, face) in enumerate(square_blocks(numbers)):
        if what == "shops":
            found += shop_face(room, face, BLOCK_SEED + 10 + index, {}, (), prefix="far_")
        else:
            found += plain_face(room, face, BLOCK_SEED + 10 + index, "far_")
    found += own_block_west(room, numbers)
    found += bay_stack(room, numbers)
    return found


# --- the launch view -----------------------------------------------------------------------------------------------

PAD_TOP = 1.2
PAD_TILE = 10.0
MAST = (3.0, 75.0, 3.0)
MAST_IN = 6.0
PAD_LIGHT = (2.6, 12.0, 1.2)
FERRY = (6.0, 7.0, 32.0)
# Where the ferries are on the water, their keels FERRY_DRAUGHT under it, and which way each is heading (degrees about
# up from +x).
FERRY_DRAUGHT = 0.6
FERRIES = (((-170.0, -FERRY_DRAUGHT, 35.0), 15.0), ((-215.0, -FERRY_DRAUGHT, -125.0), 170.0),
           ((-240.0, -FERRY_DRAUGHT, 95.0), 200.0))


def launch(numbers):
    """The launch view's kit: the pad on the water, the four lightning masts round it, its floodlights, and the
    ferries out on the harbour."""
    room = "launch"
    pad = numbers["LAUNCH_PAD"]
    found = []
    along = np.array([1.0, 0.0, 0.0])
    for x0 in np.arange(pad[0], pad[0] + pad[2] - 1e-6, PAD_TILE):
        for z0 in np.arange(pad[1], pad[1] + pad[3] - 1e-6, PAD_TILE):
            wide, long = min(PAD_TILE, pad[0] + pad[2] - x0), min(PAD_TILE, pad[1] + pad[3] - z0)
            found.append(flat(room, "far_pad", (x0 + wide / 2, z0 + long / 2), along, (wide, long, PAD_TOP + 2.0),
                              PAD_TOP))
    corners = [(pad[0] + MAST_IN, pad[1] + MAST_IN), (pad[0] + pad[2] - MAST_IN, pad[1] + MAST_IN),
               (pad[0] + MAST_IN, pad[1] + pad[3] - MAST_IN), (pad[0] + pad[2] - MAST_IN, pad[1] + pad[3] - MAST_IN)]
    for x, z in corners:
        found.append(piece(room, "far_lightning_mast", (x, PAD_TOP, z), frame_facing((1.0, 0.0, 0.0), UP), MAST))
    rocket = numbers["ROCKET_AT"]
    for x, z in ((pad[0] + pad[2] - 3.0, rocket[2] - 14.0), (pad[0] + pad[2] - 3.0, rocket[2] + 14.0),
                 (rocket[0], pad[1] + 3.0), (rocket[0], pad[1] + pad[3] - 3.0)):
        toward = np.array([rocket[0] - x, 0.0, rocket[2] - z])
        found.append(piece(room, "far_pad_floodlight", (x, PAD_TOP, z),
                           frame_facing(toward / np.linalg.norm(toward), UP), PAD_LIGHT))
    for at, heading in FERRIES:
        angle = np.radians(heading)
        found.append(piece(room, "far_ferry", at, frame_facing((np.sin(angle), 0.0, np.cos(angle)), UP), FERRY))
    return found


PLACES = {"street": street, "square": square, "launch": launch}
FLOORS = ("ground_asphalt", "ground_paving", "kerb_stone", "road_line", "far_paving", "far_terrace", "far_road", "far_promenade",
          "balcony_slab", "far_pad")
STANDING = ("water_barrier_red", "water_barrier_white", "street_lamp", "notice_case", "poster_stand", "menu_board",
            "end_wall", "end_fence", "far_palm",
            "far_flag_pole", "far_floodlight_tower", "far_square_lamp", "far_stage", "far_backdrop", "far_podium",
            "far_lectern", "far_banner", "far_lightning_mast", "far_pad_floodlight", "far_ferry", "far_promenade_rail")


# What glows at night, by own name (EarthNight reads `night_glow`): the parts of its picture at least this bright, in
# linear light as the shader reads it, give off their own colour (a sign's white board and a lit window, never a grey
# frame; a banner's gold words at 0.49, never its red cloth at 0.15; a lantern's red paper).
NIGHT_GLOW = {"shop_sign": 0.5, "far_shop_sign": 0.5, "neon_sign": 0.2, "far_neon_column": 0.2, "far_backdrop": 0.3,
              "far_banner": 0.3, "window_lit": 0.4, "far_window_lit": 0.4, "tea_front": 0.4, "shop_open": 0.4,
              "far_lantern": 0.2, "street_lamp": 0.5, "far_square_lamp": 0.5, "far_floodlight_tower": 0.5,
              "far_pad_floodlight": 0.5, "door_canopy": 0.5}


def kinds_table(pieces):
    """Every kind's group for the scene check (floors for what is walked on, hangs for what hangs on a face, nothing
    for what stands on the ground), and from how bright a part of it glows at night when it is a light (NIGHT_GLOW)."""
    table = {}
    for laid in pieces:
        own = laid["kind"].split("_", 1)[1]
        table[laid["kind"]] = {} if own in STANDING else {"group": "floors" if own in FLOORS else "hangs"}
        if own in NIGHT_GLOW:
            table[laid["kind"]]["night_glow"] = NIGHT_GLOW[own]
    return table


def layout_of(room):
    """A place's laid-out kit, as the route reads it."""
    pieces = PLACES[room](site())
    counts = {}
    for laid in pieces:
        counts[laid["kind"]] = counts.get(laid["kind"], 0) + 1
    return {"room": room, "place": f"prologue_{room}", "frame": "EarthSite's own: x across the block (the street "
            "+x, the square -x), z along the street (+z to the capsule), y up from the street",
            "counts": counts, "kinds": kinds_table(pieces), "pieces": pieces}


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in PLACES:
        raise SystemExit(__doc__)
    layout = layout_of(sys.argv[1])
    pathlib.Path(sys.argv[2]).write_text(json.dumps(layout, indent="\t") + "\n")
    print(len(layout["pieces"]), "pieces of", len(layout["counts"]), "kinds")
    for kind, count in sorted(layout["counts"].items()):
        print(f"  {count:5d} {kind}")


if __name__ == "__main__":
    main()
