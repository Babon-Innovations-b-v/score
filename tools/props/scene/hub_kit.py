"""The hub's kit layout: where every made piece of the C12 room stands (job hubkit, the owner 2026-10-05: code only lays
out, every visible surface is a made piece placed like a kit).

    python3 tools/props/scene/hub_kit.py <out.json>   # writes the laid-out room and prints the partition score

The laid-out room is the robust route's input (tools/props/library/route.py), which makes a model for every piece and
writes the game's layout, data/kit/hub.json, from it.

The room's numbers are the shell's (ModuleShell.KIT for the hub, ModuleFloors: twelve walls whose inside faces stand
APOTHEM from the middle, WALL_HIGH tall under a pyramid roof rising RISE, a pit PIT_R round and PIT_DEEP deep with a
stair down into it from the north and from the south and no rail round it, the doors on their walls). Frame: the Habitat node's own, x east, z south, y up from the ring floor; a wall's
bearing is clockwise from north (-z).

Every piece is laid out in its kind's own frame: as wide as x, as tall as y, as deep as z, standing on its origin at the
middle of its foot, its front toward -z. A piece is written as its kind (a prop kind, `hub_<id>`), where its origin
stands, the three axes of its frame (x, y, z, unit) and the size it is laid out at; the game turns the made model
into its kind's frame and fits it to that size (HubKit).

The partition score (Point2Part's, arXiv 2609.38180, applied to the room's surfaces): every visible surface of the
room should belong to exactly one piece. The surfaces (the walls less their doorways, the roof, the ring floor, the
pit's wall and floor) are sampled on a grid; each sample is owned by the pieces whose box holds it. Reported: the share
owned by a piece (coverage), the share owned by more than one (overlap) and the largest uncovered patch.
"""
import json
import math
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "library"))
import sorter  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
GAME_LAYOUT = REPO / "data/kit/hub.json"
INVENTORY = REPO / "data/inventory/hub.json"

APOTHEM = 4.5
FACETS = 12
FACET_WIDE = 2 * APOTHEM * math.tan(math.pi / FACETS)
WALL_HIGH = 3.1
RISE = 1.7
PIT_R = 2.33
PIT_DEEP = 0.9
STAIR_HALF = 0.6
# The pit's stairs, by bearing, and no rail round its edge (the owner, 2026-10-06, after playing the kit hub: "remove the
# railings, would look a lot cleaner and more open"); one stair: a second, opposite, pushed the console out of the pit,
# and the owner chose one stair after the in-game test. The sim's pit (SteppedFloor) has the same one.
STAIRS = (0,)
# The fittings stand where the room's systems run (hub round four, 2026-10-07: placed at fixed bearings that served
# nothing, the owner found them random). The air system: a supply duct on the roof face over each of AIR_WALLS, a
# louvred vent low on that wall, and a return grating in the ring floor before it, AIR_GRATE_RADIUS out, with a duct
# box under it. The two walls are the only lower walls with no door and no furniture before them. The service runs:
# an access hatch in the ring floor at the facets of the pit wall's junction boxes (JUNCTION_BOXES, each in the facet
# it lies nearest), HATCH_RADIUS out by the pit's lip, a cable trough under it.
AIR_WALLS = (60, 210)
AIR_GRATE_RADIUS = 3.85
SERVICE_FACETS = (30, 210, 270)
HATCH_RADIUS = 2.95
# What lies under a set-in floor fitting's opening, how deep: a duct box under a grating, a trough under a hatch. Code
# builds them: plain plates (under_floor_box).
UNDER_FLOOR = {"floor_grating": 0.18, "floor_access_hatch": 0.18}  # deeper, they ran into the deck's structure (scene check)
# How far an under-floor box reaches past its opening each way, so its walls hang under the plate's rim.
UNDER_LIP = 0.03
# How far a set-in fitting's cut reaches past its edges, and how far below its host's face its own face lies: flush.
SET_IN_GAP = 0.004
SET_IN_DOWN = 0.0
STAIR_CLEAR = 20  # degrees either side of a stair's bearing where the pit's edge and wall leave its way open
STRINGER = 0.03
LATTICE_UNDER = 0.14
# The roof's panels reach this far past the wall's top down their slope (widening on as their faces do), and are this
# much wider again, so no look up between the wall and the roof, or between two roof faces, finds a seam.
EAVE = 0.15
# The cable runs' foot: above the tallest wall gear (the status display's top, 2.73 m) and under the cornice.
CABLE_HIGH = 2.76
EAVE_WIDER = 1.01
JUNCTION_BOXES = (30, 220, 260)
STAIR_TREADS = 4
STAIR_RISE = 0.18
STAIR_FOOT = 1.42  # how far from the middle the stair reaches the pit's floor
LATTICE_RINGS = (0.0, 0.44, 0.88)
DOORS = {0: "hatch", 90: "hatch", 180: "hatch", 270: "hatch", 330: "airlock"}
OPEN_DOORS = (90, 270, 330)  # the tube hatches east and west and the airlock stand open onto what is joined there
SWING = 100.0
# A door leaf's size (wide, tall, deep) from the hatch design, for a door whose leaf the room does not show (the
# airlock's: its own inner door shuts that doorway), so its hinges still stand where the leaf hangs.
LEAVES = {"hatch": (2.0, 2.6, 0.12), "airlock": (2.1, 2.7, 0.16)}
DOORWAY = (2.2, 2.6)  # wide, tall: the shell's doorway (ModuleDoors.WIDE, ModuleShell.DOOR_HEIGHT)
LOWER = 1.1
LAP = 0.04  # two panels side by side lap this much where they meet, so no look slips through their seam
BAND_LAP = 0.06  # the lower band reaches this far up behind the upper one: its top edge is a lip, not a line
PORTHOLE = (300, 2.35)
ROOF_LAYER = 2
# The wall panel kinds, lower and upper band, by wall: varied as the plan shows them (pipes and cables up high, vents and
# patched plates low, the screen recess on the lab bench's wall); a wall not named takes the plain ones.
LOWER_PANELS = {60: "wall_lower_vent", 120: "wall_lower_patched", 210: "wall_lower_vent"}
UPPER_PANELS = {30: "wall_upper_cables", 150: "wall_upper_cables", 210: "wall_upper_pipes", 240: "wall_upper_pipes",
                120: "wall_upper_screen_recess", 60: "wall_upper_patched"}


def bearing_vectors(bearing):
    """A wall's outward normal and its along (clockwise) direction in the room's frame."""
    angle = math.radians(bearing)
    return np.array([math.sin(angle), 0.0, -math.cos(angle)]), np.array([math.cos(angle), 0.0, math.sin(angle)])


def frame_facing(front, up):
    """The piece's axes (x, y, z) for a front looking along `front` with its height along `up`."""
    z = -np.asarray(front, dtype=np.float64)
    z /= np.linalg.norm(z)
    y = np.asarray(up, dtype=np.float64)
    y = y - z * (y @ z)
    y /= np.linalg.norm(y)
    x = np.cross(y, z)
    return x, y, z


def piece(kind, origin, axes, size, layer=1):
    x, y, z = axes
    return {"kind": f"hub_{kind}", "at": [round(float(value), 4) for value in origin],
            "x": [round(float(value), 5) for value in x], "y": [round(float(value), 5) for value in y],
            "z": [round(float(value), 5) for value in z], "size": [round(float(value), 4) for value in size], "layer": layer}


def on_wall(kind, bearing, across, bottom, size, out=0.0):
    """A piece against a wall, its back on the wall's inside face (or `out` from it), facing into the room."""
    normal, along = bearing_vectors(bearing)
    wide, tall, deep = size
    origin = normal * (APOTHEM - out - deep / 2) + along * across + np.array([0.0, bottom, 0.0])
    return piece(kind, origin, frame_facing(-normal, (0, 1, 0)), size)


def on_lining(kinds, kind, bearing, across, bottom, size, out=0.0):
    """A piece hung on a wall's lining: its back on the face of the wall panels behind it (or `out` from it)."""
    return on_wall(kind, bearing, across, bottom, size, out=out + lining(kinds, bearing, bottom, bottom + size[1]))


def lining(kinds, bearing, low, high):
    """How far the wall panels behind a span of a wall's height stand out of the wall: the deepest of them."""
    if bearing in DOORS:
        return depth(kinds, "hatch_wall_surround")
    found = []
    if low < LOWER:
        found.append(depth(kinds, LOWER_PANELS.get(bearing, "wall_lower_plain")))
    if high > LOWER:
        found.append(depth(kinds, UPPER_PANELS.get(bearing, "wall_upper_plain")))
    return max(found)


def lapped(found, own):
    """A wall panel laid bigger than its share of the wall so it laps its neighbours: the partition scores it by its
    own share (`own`: wide, tall), the lap being its edge tucked behind the next panel."""
    found["scored"] = [round(float(own[0]), 4), round(float(own[1]), 4), found["size"][2]]
    return found


def off_bearing(first, second):
    """How far apart two bearings are, in degrees (0 to 180)."""
    return abs(((first - second + 180) % 360) - 180)


def near_a_stair(bearing, within):
    return any(off_bearing(bearing, stair) < within for stair in STAIRS)


def in_a_joint(bearing, across):
    """Whether a point along a wall lies in the end left to a joined module's shell (clear_of_a_joint)."""
    for side in (-1, 1):
        if (bearing + 30 * side) % 360 in JOINED_MODULE and side * across > FACET_WIDE / 2 - JOINT_CLEAR:
            return True
    return False


def clear_of_a_joint(bearing, side, middle, wide):
    """A panel's middle and width along its wall, narrowed by JOINT_CLEAR at the end that meets a joined module's
    wall (whose shell reaches into the hub's wall there): +1 is the end toward the next wall clockwise."""
    neighbour = (bearing + 30 * side) % 360
    if neighbour not in JOINED_MODULE:
        return middle, wide
    return middle - side * JOINT_CLEAR / 2, wide - JOINT_CLEAR


def walls(kinds):
    """Every wall's panels: a door's wall is one surround round its doorway; the others a lower and an upper band of
    two panels each, the porthole's wall its porthole panel in the middle of the upper band; a corner post where two
    walls meet, a skirting at the foot and a cornice at the top of every wall."""
    found = []
    half = FACET_WIDE / 2
    for index in range(FACETS):
        bearing = index * 30
        if bearing in DOORS:
            found.append(on_wall("hatch_wall_surround", bearing, 0.0, 0.0, (FACET_WIDE, WALL_HIGH, depth(kinds, "hatch_wall_surround"))))
            continue
        lower = LOWER_PANELS.get(bearing, "wall_lower_plain")
        upper = UPPER_PANELS.get(bearing, "wall_upper_plain")
        for side in (-1, 1):
            middle, wide = clear_of_a_joint(bearing, side, side * half / 2, half + LAP)
            found.append(lapped(on_wall(lower, bearing, middle, 0.0, (wide, LOWER + BAND_LAP, depth(kinds, lower))),
                                (wide - LAP, LOWER)))
        if bearing == PORTHOLE[0]:
            porthole = size_of(kinds, "porthole_panel")
            filler = (FACET_WIDE - porthole[0]) / 2
            found.append(on_wall("porthole_panel", bearing, 0.0, PORTHOLE[1] - porthole[1] / 2, porthole))
            below = PORTHOLE[1] - porthole[1] / 2 - LOWER
            above = WALL_HIGH - PORTHOLE[1] - porthole[1] / 2
            for side in (-1, 1):
                middle, wide = clear_of_a_joint(bearing, side, side * (porthole[0] / 2 + filler / 2), filler)
                found.append(on_wall(upper, bearing, middle, LOWER, (wide, WALL_HIGH - LOWER, depth(kinds, upper))))
            found.append(on_wall(upper, bearing, 0.0, LOWER, (porthole[0], below, depth(kinds, upper))))
            found.append(on_wall(upper, bearing, 0.0, WALL_HIGH - above, (porthole[0], above, depth(kinds, upper))))
        else:
            for side in (-1, 1):
                middle, wide = clear_of_a_joint(bearing, side, side * half / 2, half + LAP)
                found.append(lapped(on_wall(upper, bearing, middle, LOWER, (wide, WALL_HIGH - LOWER, depth(kinds, upper))),
                                    (wide - LAP, WALL_HIGH - LOWER)))
    for index in range(FACETS):
        bearing = index * 30
        if bearing not in DOORS:  # a doorway reaches the floor: a skirting across it is a sill in the way
            found.append(on_wall("wall_skirting", bearing, 0.0, 0.0, (FACET_WIDE, size_of(kinds, "wall_skirting")[1], depth(kinds, "wall_skirting")), out=-0.0))
        cornice = size_of(kinds, "wall_cornice")
        found.append(on_wall("wall_cornice", bearing, 0.0, WALL_HIGH - cornice[1], (FACET_WIDE, cornice[1], cornice[2])))
        if bearing in JOINED_MODULE or (bearing + 30) % 360 in JOINED_MODULE:
            continue  # the corner beside a joined module's wall is inside that module's shell
        corner = math.radians(bearing + 15)
        post = size_of(kinds, "wall_corner_post")
        reach = APOTHEM / math.cos(math.pi / FACETS) - post[2] / 2
        origin = np.array([math.sin(corner) * reach, 0.0, -math.cos(corner) * reach])
        found.append(piece("wall_corner_post", origin, frame_facing(-origin / np.linalg.norm(origin), (0, 1, 0)), post))
    return found


def roof(kinds):
    """A ribbed panel on every face of the pyramid roof, its foot on the top of its wall, its height up the slope to
    the apex; and the lattice under it: three rings, a hip rib from every corner, a diamond on every face, a gusset
    plate at every joint, the hub at the top, on the roof's layer so the operations view sees through it."""
    found = []
    slope = math.hypot(APOTHEM, RISE)
    for index in range(FACETS):
        bearing = index * 30
        normal, along = bearing_vectors(bearing)
        foot = normal * APOTHEM + np.array([0.0, WALL_HIGH, 0.0])
        up_slope = (np.array([0.0, WALL_HIGH + RISE, 0.0]) - foot) / slope
        inward_down = np.cross(along, up_slope)
        if inward_down[1] > 0:
            inward_down = -inward_down
        size = (FACET_WIDE * (slope + EAVE) / slope * EAVE_WIDER, slope + EAVE, depth(kinds, "roof_face_panel"))
        laid = piece("roof_face_panel", foot - up_slope * EAVE - inward_down * size[2] / 2, frame_facing(inward_down, up_slope),
                     size, ROOF_LAYER)
        laid["taper"] = 0.0  # a triangle: as wide as its wall at its foot, to a point at the apex
        found.append(laid)
    inside = APOTHEM - LATTICE_UNDER
    corners = [np.array([math.sin(math.radians(index * 30 + 15)), 0.0, -math.cos(math.radians(index * 30 + 15))])
               * inside / math.cos(math.pi / FACETS) for index in range(FACETS)]

    def at(point, share):
        return point * (1 - share) + np.array([0.0, WALL_HIGH + RISE * share - LATTICE_UNDER, 0.0])

    joints = []
    for share in LATTICE_RINGS:
        for index in range(FACETS):
            found.append(bar("lattice_ring_rib", at(corners[index], share), at(corners[(index + 1) % FACETS], share), kinds))
            joints.append(at(corners[index], share))
    for index in range(FACETS):
        corner, following = corners[index], corners[(index + 1) % FACETS]
        found.append(bar("lattice_hip_rib", at(corner, 0.0), at(corner, 0.96), kinds))
        middle = (corner + following) / 2
        for end in (corner, following):
            found.append(bar("lattice_diamond_strut", at(middle, LATTICE_RINGS[0]), at(end, LATTICE_RINGS[1]), kinds))
            found.append(bar("lattice_diamond_strut", at(end, LATTICE_RINGS[1]), at(middle, LATTICE_RINGS[2]), kinds))
    plate = size_of(kinds, "lattice_node_plate")
    for joint in joints:
        inward = -joint * np.array([1.0, 0.0, 1.0])
        inward = inward / max(np.linalg.norm(inward), 1e-6)
        found.append(piece("lattice_node_plate", joint - inward * plate[1] / 2,
                           frame_facing((0, -1, 0), inward), plate, ROOF_LAYER))
    apex = size_of(kinds, "roof_apex_hub")
    found.append(piece("roof_apex_hub", np.array([0.0, WALL_HIGH + RISE - LATTICE_UNDER - apex[1], 0.0]),
                       frame_facing((0, 0, -1), (0, 1, 0)), apex, ROOF_LAYER))
    for bar_piece in found:
        if bar_piece["kind"] in ("hub_lattice_ring_rib", "hub_lattice_hip_rib", "hub_lattice_diamond_strut"):
            bar_piece["layer"] = ROOF_LAYER
    return found


def bar(kind, start, end, kinds, layer=ROOF_LAYER):
    """A beam of a kind from one point to another, its front looking down into the room, as thick as the kind. A kind
    whose length is its width (a pipe, a ring beam) lies along the beam on its x, standing on the beam's middle line;
    one whose length is its height (a rib, a post) along its y from `start`."""
    length = float(np.linalg.norm(end - start))
    along = (end - start) / length
    down = np.array([0.0, -1.0, 0.0])
    front = down - along * (down @ along)
    if np.linalg.norm(front) < 1e-6:
        front = np.array([0.0, 0.0, -1.0])
    wide, tall, deep = size_of(kinds, kind)
    if wide >= tall:
        z = -front / np.linalg.norm(front)
        y = np.cross(z, along)
        origin = (start + end) / 2 - y * tall / 2
        return piece(kind, origin, (along, y, z), (length, tall, deep), layer)
    return piece(kind, start, frame_facing(front, along), (wide, length, deep), layer)


def on_roof(kind, bearing, share, size):
    """A piece lying flush on a roof face's underside, its length along the face's foot, its foot (y 0) on the roof
    and its height hanging down into the room, `share` of the way up the slope from the eave. The owner saw trays laid
    radially at the corners, their length sticking out across the lattice (2026-10-06); flush on one face, a piece
    cannot."""
    normal, along = bearing_vectors(bearing)
    foot = normal * APOTHEM * (1 - share) + np.array([0.0, WALL_HIGH + RISE * share, 0.0])
    up_slope = np.array([0.0, RISE, 0.0]) - normal * APOTHEM
    up_slope /= np.linalg.norm(up_slope)
    into_room = np.cross(up_slope, along)
    if into_room[1] > 0:
        into_room = -into_room
    z = np.cross(along, into_room)
    return piece(kind, foot, (along, into_room, z), size, ROOF_LAYER)


# The roof faces trays and ducts lie on, and how far up the slope: low enough that their length fits the face.
TRAY_FACES = (0, 120, 180, 240, 300)
DUCT_FACES = AIR_WALLS
ROOF_GEAR_SHARE = 0.1


def ceiling_gear(kinds):
    """Cable trays and ducts flush on roof faces, and the roof's flood lamps hung under the lattice's lowest ring."""
    found = []
    for bearing in TRAY_FACES:
        found.append(on_roof("ceiling_cable_tray", bearing, ROOF_GEAR_SHARE, size_of(kinds, "ceiling_cable_tray")))
    for bearing in DUCT_FACES:
        found.append(on_roof("ceiling_duct", bearing, ROOF_GEAR_SHARE, size_of(kinds, "ceiling_duct")))
    for bearing in (45, 135, 225, 315):
        normal, along = bearing_vectors(bearing)
        lamp = size_of(kinds, "roof_light_fixture")
        found.append(piece("roof_light_fixture", normal * 2.6 + np.array([0.0, WALL_HIGH + 0.45 - lamp[1], 0.0]),
                           frame_facing((0, 0, -1), (0, 1, 0)), lamp))
    return found


def floor(kinds, inventory):
    """The ring floor's plates, a sector of each wall's width between the pit's lip and the wall; the air system's
    return gratings and the service runs' access hatches set into some (flush, in openings cut_openings cuts, with
    what lies under each: under_floor), and a tread mat set in before every hatch. A fitting under furniture stops the
    layout: where to move it is the owner's call (the layout rule)."""
    found = []
    ring = (PIT_R + 0.06, APOTHEM)
    for index in range(FACETS):
        bearing = index * 30
        normal, along = bearing_vectors(bearing)
        middle = (ring[0] + ring[1]) / 2
        plate = (FACET_WIDE, ring[1] - ring[0], depth(kinds, "ring_floor_plate"))
        laid = piece("ring_floor_plate", normal * APOTHEM, frame_facing((0, 1, 0), -normal), plate)
        laid["taper"] = round(ring[0] / APOTHEM, 4)  # a trapezoid: as wide as its wall at its foot, narrowing to the lip
        found.append(laid)
    fittings = []
    for kind, bearings, radius in (("floor_grating", AIR_WALLS, AIR_GRATE_RADIUS),
                                   ("floor_access_hatch", SERVICE_FACETS, HATCH_RADIUS)):
        for bearing in bearings:
            normal, along = bearing_vectors(bearing)
            fittings.append(set_in(flat(kind, normal * radius, along, size_of(kinds, kind), 0.0)))
    for spot in spots(inventory, "tread_mat"):
        normal, along = bearing_vectors(spot["facet"])
        fittings.append(set_in(flat("tread_mat", np.array([spot["x"], 0.0, spot["z"]]), along, size_of(kinds, "tread_mat"), 0.0)))
    blocked = [laid for laid in fittings if laid not in clear_of_furniture(fittings, inventory)]
    if blocked:
        raise SystemExit("floor fittings under furniture, for the owner to place: "
                         + ", ".join(f"{laid['kind']} at {laid['at']}" for laid in blocked))
    return found + fittings + under_floor(fittings, depth(kinds, "ring_floor_plate"))


def under_floor(fittings, plate):
    """What lies under each set-in floor fitting's opening (UNDER_FLOOR): an open box of plates as wide and long as the
    opening, from the floor plate's underside down, so a look through a grating meets a duct, not the void."""
    found = []
    for fitting in fittings:
        kind = fitting["kind"].removeprefix("hub_")
        if kind not in UNDER_FLOOR:
            continue
        wide, long, _ = fitting["size"]
        middle = box_corners(fitting).mean(axis=0)
        along = np.asarray(fitting["x"])
        size = (wide + 2 * UNDER_LIP, long + 2 * UNDER_LIP, UNDER_FLOOR[kind])
        found.append(flat("under_floor_box", (middle[0], 0.0, middle[2]), along, size, -plate - UNDER_FLOOR[kind]))
    return found


def set_in(laid):
    """Marks a fitting as set into its host (sorter.SET_IN): cut_openings cuts its opening and sets it flush."""
    laid["set_in"] = True
    return laid


def flat(kind, middle, along, size, lift):
    """A piece lying on the floor with its front up, as wide as `along` and as long as across it."""
    wide, long, thick = size
    across = np.cross(np.array([0.0, 1.0, 0.0]), along)
    origin = np.asarray(middle, dtype=np.float64) - across * long / 2 + np.array([0.0, lift + thick / 2, 0.0])
    return piece(kind, origin, frame_facing((0, 1, 0), across), (wide, long, thick))


def pit(kinds):
    """The pit's wall round the ring's lip in panels facing in, its floor in plates, the conduit runs and boxes on its
    wall, and the two machine bays' plates."""
    found = []
    panels = 10
    panel = size_of(kinds, "pit_wall_panel")
    pipe = size_of(kinds, "pipe_straight")
    for index in range(panels):
        bearing = index * 36 + 18
        normal, along = bearing_vectors(bearing)
        wide = 2 * math.pi * PIT_R / panels
        found.append(piece("pit_wall_panel", normal * (PIT_R - panel[2] / 2) + np.array([0.0, -PIT_DEEP, 0.0]),
                           frame_facing(-normal, (0, 1, 0)), (wide, PIT_DEEP, panel[2])))
        if not near_a_stair(bearing, STAIR_CLEAR + 5):
            # The conduit runs along the pit's wall: two pipe lengths per panel, at the two heights the plan shows.
            for high in (-0.35, -0.55):
                for start in (bearing - 17, bearing - 17 + 34 / 3, bearing - 17 + 68 / 3):
                    if any(abs(((box_bearing - start - 17 / 3 + 180) % 360) - 180) < 17 / 3 + 4 for box_bearing in JUNCTION_BOXES):
                        continue  # a junction box stands on the pit wall here
                    points = [np.array([math.sin(math.radians(angle)), 0.0, -math.cos(math.radians(angle))])
                              * (PIT_R - panel[2] - pipe[1] / 2) + np.array([0.0, high, 0.0])
                              for angle in (start, start + 34 / 3)]
                    found.append(bar("pipe_straight", points[0], points[1], kinds, layer=1))
    for bearing in JUNCTION_BOXES:
        normal, along = bearing_vectors(bearing)
        box = size_of(kinds, "pit_junction_box")
        found.append(piece("pit_junction_box", normal * (PIT_R - panel[2] - box[2] / 2) + np.array([0.0, -0.63, 0.0]),
                           frame_facing(-normal, (0, 1, 0)), box))
    plate = size_of(kinds, "pit_floor_plate")
    for across in (-2.0, -1.0, 0.0, 1.0, 2.0):
        for along in (-2.0, -1.0, 0.0, 1.0, 2.0):
            if math.hypot(max(abs(across) - 0.5, 0.0), max(abs(along) - 0.5, 0.0)) < PIT_R:
                found.append(flat("pit_floor_plate", (across, -PIT_DEEP, along), np.array([1.0, 0.0, 0.0]), plate, 0.0))
    for middle in ((1.0, 0.0), (-1.0, 0.0)):
        found.append(flat("machine_bay_plate", (middle[0], -PIT_DEEP, middle[1]), np.array([1.0, 0.0, 0.0]),
                          size_of(kinds, "machine_bay_plate"), 0.004))
    return found


def stairs(kinds):
    """The stairs down into the pit, built of the kit's own pieces (the stair and handrail models came out as blobs
    twice), at the sim's tread heights (SteppedFloor's pit): a floor grating for each tread, a pit floor plate standing
    as each riser, and a stepped side plate either side, so the stair reads as one solid flight; no handrails."""
    found = []
    grating = size_of(kinds, "floor_grating")
    riser = size_of(kinds, "pit_floor_plate")
    run = PIT_R - STAIR_FOOT
    depth_each = run / STAIR_TREADS
    inner = 2 * (STAIR_HALF - STRINGER)
    for bearing in STAIRS:
        normal, along = bearing_vectors(bearing)
        for step in range(STAIR_TREADS):
            middle = normal * (PIT_R - depth_each * (step + 0.5))
            top = -STAIR_RISE * (step + 1)
            found.append(flat("floor_grating", middle + np.array([0.0, top - grating[2], 0.0]), along,
                              (inner, depth_each, grating[2]), 0.0))
            near = normal * (PIT_R - depth_each * (step + 1) + riser[2] / 2)
            found.append(piece("pit_floor_plate", near + np.array([0.0, top - STAIR_RISE, 0.0]),
                               frame_facing(-normal, (0, 1, 0)), (inner, STAIR_RISE, riser[2])))
        inward = -normal
        up = np.array([0.0, 1.0, 0.0])
        for side in (-1, 1):
            middle = normal * (PIT_R - run / 2) + along * side * (STAIR_HALF - STRINGER / 2)
            laid = piece("stair_stringer", middle + np.array([0.0, -PIT_DEEP, 0.0]), (inward, up, np.cross(inward, up)),
                         (run, PIT_DEEP, STRINGER))
            laid["treads"] = STAIR_TREADS
            found.append(laid)
    return found


LEAF_OVER = 0.06
SHELL_WALL = 0.3  # the shell's wall thickness (ModuleShell.WALL)
# A wall where another module is joined into the hub's wall (the airlock, turned onto its 330-degree wall): that
# module's shell reaches into the hub's wall there and brings its own doorway, frame and door, so the kit lays no
# frame, hinges or corner posts on it.
JOINED_MODULE = (330,)
JOINT_CLEAR = 0.3


# How much wider and taller than the doorway a door's frame is: its two posts and its header.
FRAME_POSTS = 0.2
FRAME_HEADER = 0.093


def framed(kinds, kind):
    """A door's frame laid so its opening is exactly the shell's doorway."""
    return (DOORWAY[0] + FRAME_POSTS, DOORWAY[1] + FRAME_HEADER, depth(kinds, f"{kind}_frame"))


def doors(kinds, inventory):
    """Every hatch: its frame round the doorway, its leaf on two hinges at its left (three for the airlock), its
    locking wheel and (a tube hatch's) window on the leaf. A sealed hatch's leaf is shut; an open one's stands swung
    back SWING degrees on its hinges, the parts on it going with it (the airlock's own inner door shuts that
    doorway). The strip lamp over each, the control box and grab bar beside each, where the inventory places them.
    An open door's leaf stands swung into the tube it opens on, out of the room (swung into the room it filled the
    ring's walkway), so the room shows its frame and hinges only."""
    found = []
    for bearing, kind in DOORS.items():
        if bearing in JOINED_MODULE:
            continue  # the joined module's own doorway, frame and door stand here
        frame = framed(kinds, kind)
        found.append(on_wall(f"{kind}_frame", bearing, 0.0, 0.0, frame, out=0.0))
        if bearing in OPEN_DOORS:
            # A second frame lines the doorway through the wall's thickness, so a look out through the open door
            # meets the frame and not the inside of the wall.
            found.append(on_wall(f"{kind}_frame", bearing, 0.0, 0.0, (frame[0], frame[1], SHELL_WALL), out=-SHELL_WALL))
        leaf = size_of(kinds, f"{kind}_leaf") if f"{kind}_leaf" in kinds else LEAVES[kind]
        if bearing not in OPEN_DOORS:
            leaf = (DOORWAY[0] + LEAF_OVER, DOORWAY[1] + LEAF_OVER, leaf[2])  # a shut leaf closes the whole doorway
        normal, along = bearing_vectors(bearing)
        hinge_line = normal * (APOTHEM - frame[2] - leaf[2]) + along * (-leaf[0] / 2)
        swing = math.radians(SWING if bearing in OPEN_DOORS else 0.0)
        # The leaf's frame turned about the hinge line: its across runs from the hinge, its front faces the room.
        leaf_across = along * math.cos(swing) - normal * math.sin(swing)
        leaf_front = -normal * math.cos(swing) - along * math.sin(swing)

        def on_leaf(part, across, bottom, size, out):
            origin = hinge_line + leaf_across * across + leaf_front * (out + size[2] / 2) + np.array([0.0, bottom, 0.0])
            return piece(part, origin, frame_facing(leaf_front, (0, 1, 0)), size)

        if bearing not in OPEN_DOORS:
            found.append(on_leaf(f"{kind}_leaf", leaf[0] / 2, 0.0, leaf, -leaf[2]))
            wheel = size_of(kinds, f"{kind}_wheel")
            found.append(on_leaf(f"{kind}_wheel", leaf[0] / 2, 1.15 - wheel[1] / 2, wheel, 0.0))
            if kind == "hatch":
                window = size_of(kinds, "hatch_window")
                found.append(on_leaf("hatch_window", leaf[0] / 2, 1.85 - window[1] / 2, window, -window[2] / 2))
        hinge = size_of(kinds, f"{kind}_hinge")
        for high in (0.5, 2.0) if kind == "hatch" else (0.4, 1.3, 2.2):
            found.append(on_wall(f"{kind}_hinge", bearing, -leaf[0] / 2 - hinge[0] / 2, high, hinge, out=frame[2]))
    for kind in ("door_strip_lamp", "door_control_box", "grab_bar"):
        size = size_of(kinds, kind)
        for spot in spots(inventory, kind):
            middle_high = spot["y"]
            laid = on_lining(kinds, kind, spot["facet"], spot["across"], middle_high - size[1] / 2, size)
            found.append(set_in(laid) if kind in sorter.SET_IN else laid)
    return found


def wall_gear(kinds, inventory):
    """The pieces the inventory places on the walls (display, screens, notice board, porthole is a wall panel) and the
    pipe runs, cables, lamps and small screens laid along the walls the plan shows them on."""
    found = []
    for kind in ("status_display", "wall_screen_cluster", "notice_board"):
        size = size_of(kinds, kind)
        for spot in spots(inventory, kind):
            bottom = max(spot["y"] - size[1] / 2, LOWER + 0.03)  # on the upper panels, clear of the lower band's top
            found.append(on_lining(kinds, kind, spot["facet"], spot["across"], bottom, size))
    straight, elbow, valve, bracket = (size_of(kinds, name) for name in ("pipe_straight", "pipe_elbow", "pipe_valve", "pipe_bracket"))
    for bearing, highs in ((210, (0.75, 1.35, 1.95)), (330, (2.74,)), (300, (0.55,)), (240, (2.6,))):
        for high in highs:
            for across in (-0.6, 0.6):
                found.append(on_lining(kinds, "pipe_straight", bearing, across, high - straight[1] / 2,
                                     (FACET_WIDE / 2 - 0.02, straight[1], straight[2]), out=PIPE_AXIS - straight[2] / 2))
            found.append(on_lining(kinds, "pipe_bracket", bearing, -0.6, high - bracket[1] / 2, bracket))
            found.append(on_lining(kinds, "pipe_bracket", bearing, 0.6, high - bracket[1] / 2, bracket))
    for bearing, across, high in ((210, -0.3, 1.35), (210, -0.3, 0.75), (300, -0.5, 0.55)):  # each on a pipe laid
        found.append(on_lining(kinds, "pipe_valve", bearing, across, high - valve[1] / 2, valve))
    for bearing in (210, 240, 300):  # not the airlock's wall: its doorway reaches the corners
        for side in (-1, 1):
            found.append(on_lining(kinds, "pipe_elbow", bearing, side * (FACET_WIDE / 2 - elbow[0] / 2), 0.4, elbow, out=bracket[2]))
    cable = size_of(kinds, "cable_bundle")
    for bearing in (30, 60, 120, 150, 240, 300):
        for across in (-0.6, 0.6):
            found.append(on_lining(kinds, "cable_bundle", bearing, across, CABLE_HIGH, (FACET_WIDE / 2 - 0.02, cable[1], cable[2]), out=0.0))
    drop = size_of(kinds, "cable_drop")
    for bearing, across in ((30, 1.0), (60, -1.0), (120, 1.0), (150, -1.0), (240, 1.0), (300, -1.0)):
        found.append(on_lining(kinds, "cable_drop", bearing, across, CABLE_HIGH - drop[1], drop))
    box = size_of(kinds, "conduit_box")
    for bearing, across in ((30, 0.0), (60, 0.0), (120, 0.0), (150, 0.0), (240, -0.3), (300, 0.9), (210, 1.0)):
        found.append(on_lining(kinds, "conduit_box", bearing, across, WALL_HIGH - 0.75, box, out=0.0))
    lamp = size_of(kinds, "wall_cage_lamp")
    for bearing in (30, 120, 150, 210, 240, 300):
        found.append(on_lining(kinds, "wall_cage_lamp", bearing, 0.0 if bearing != 300 else 0.9, 2.45, lamp))
    readout = size_of(kinds, "small_readout")
    for bearing, across in ((210, 0.9), (300, -0.6)):  # the spots clear of pipes, door fittings and furniture
        found.append(on_lining(kinds, "small_readout", bearing, across, 1.35, readout))
    intercom = size_of(kinds, "intercom_panel")
    for bearing, across in ((60, -0.9),):  # one: every other free wall at hand height has furniture or door fittings
        found.append(on_lining(kinds, "intercom_panel", bearing, across, 1.2, intercom))
    bin_size = size_of(kinds, "waste_bin")
    normal, along = bearing_vectors(240)
    found.append(piece("waste_bin", normal * (APOTHEM - lining(kinds, 240, 0.0, bin_size[1]) - bin_size[2] / 2 - 0.02)
                       + along * 0.95, frame_facing(-normal, (0, 1, 0)), bin_size))
    return found


# A pipe run's inline fitting carries the run through its own stub (pieces.pipe_valve: its axis VALVE_AXIS_BACK off
# its back), so the straight pipe stops at either end of it (step 0 of the modules round, 2026-10-07: the
# hub's pipes ran on through their valves); a length shorter than SHORTEST_PIPE left over is dropped.
INLINE = ("pipe_valve",)
# How far a wall pipe run's axis stands off the wall lining (pieces.PIPE_AXIS): a short stand-off, so its brackets
# visibly hold it (step 0: at 20 cm the clamp's arm hid behind the pipe and the bracket read as not reaching it).
PIPE_AXIS = 0.08
VALVE_AXIS_BACK = PIPE_AXIS
SHORTEST_PIPE = 0.05
ON_RUN = 0.02


def axis_point(laid):
    """A laid pipe piece's axis: its middle on the pipe's line (a straight pipe's middle; an inline fitting's stub)."""
    origin = np.asarray(laid["at"], dtype=np.float64) + np.asarray(laid["y"]) * laid["size"][1] / 2
    if laid["kind"].split("_", 1)[1] in INLINE:
        origin = origin + np.asarray(laid["z"]) * (laid["size"][2] / 2 - VALVE_AXIS_BACK)
    return origin


def split_at_fittings(found):
    """The laid pieces with every straight pipe that runs through an inline fitting cut into the lengths either side
    of it, and every pipe bracket that would stand on the fitting moved off it along the run."""
    inline = [laid for laid in found if laid["kind"].split("_", 1)[1] in INLINE]
    pipes = []
    for laid in found:
        if laid["kind"].split("_", 1)[1] == "pipe_straight":
            pipes += cut_pipe(laid, inline)
        elif laid["kind"].split("_", 1)[1] != "pipe_bracket":
            pipes.append(laid)
    return pipes + [clear_bracket(laid, inline) for laid in found if laid["kind"].split("_", 1)[1] == "pipe_bracket"]


def on_run(pipe, fitting):
    """Where an inline fitting's middle stands along a pipe's run (metres from the pipe's middle), or None when the
    fitting is not on that run."""
    along = np.asarray(pipe["x"])
    if abs(abs(float(along @ np.asarray(fitting["x"]))) - 1.0) > 1e-3:
        return None
    offset = axis_point(fitting) - axis_point(pipe)
    shift = float(offset @ along)
    return shift if np.linalg.norm(offset - along * shift) < ON_RUN else None


def cut_pipe(pipe, inline):
    """A straight pipe as the lengths of it left either side of the inline fittings on its run."""
    half = pipe["size"][0] / 2
    spans = [(-half, half)]
    for fitting in inline:
        shift = on_run(pipe, fitting)
        if shift is None or abs(shift) >= half + fitting["size"][0] / 2:
            continue
        low, high = shift - fitting["size"][0] / 2, shift + fitting["size"][0] / 2
        spans = [piece_span for start, end in spans
                 for piece_span in ((start, min(end, low)), (max(start, high), end)) if piece_span[1] > piece_span[0]]
    found = []
    for start, end in spans:
        if end - start < SHORTEST_PIPE:
            continue
        length = dict(pipe, size=[round(end - start, 4)] + list(pipe["size"][1:]))
        length["at"] = [round(float(value), 4)
                        for value in np.asarray(pipe["at"]) + np.asarray(pipe["x"]) * (start + end) / 2]
        found.append(length)
    return found


def clear_bracket(bracket, inline):
    """A pipe bracket moved along its run off any inline fitting it would stand on."""
    for fitting in inline:
        along = np.asarray(fitting["x"])
        offset = np.asarray(bracket["at"]) - np.asarray(fitting["at"])
        if abs(float(offset @ np.asarray(fitting["y"]))) > fitting["size"][1] / 2:
            continue  # not at the fitting's height
        if np.linalg.norm(offset - along * float(offset @ along) - np.asarray(fitting["z"]) * float(
                offset @ np.asarray(fitting["z"]))) > 0.01:
            continue
        shift = float(offset @ along)
        reach = (fitting["size"][0] + bracket["size"][0]) / 2 + 0.02
        if abs(shift) < reach:
            moved = dict(bracket)
            moved["at"] = [round(float(value), 4) for value in
                           np.asarray(fitting["at"]) + offset - along * shift + along * (reach if shift >= 0 else -reach)]
            return moved
    return bracket


FURNITURE = ("talllocker", "rack", "comms", "labbench", "toolboard", "status_display", "wall_screen_cluster",
             "notice_board")
CLEARANCE = 0.01


def clear_of_furniture(pieces, inventory):
    """The wall gear that stands clear of the room's furniture and of the screens and board the inventory hangs: a pipe,
    cable or box laid along a wall behind a locker, the comms desk, the lab bench or the status display would stand
    inside it, so it is left out there."""
    boxes = [furniture_box(row, spot) for row in inventory["rows"] if row["id"] in FURNITURE for spot in row.get("at", [])]
    return [found for found in pieces if found["kind"].removeprefix("hub_") in FURNITURE
            or not any(overlapping(piece_box(found), box) for box in boxes)]


def piece_box(found):
    """A laid piece's box in the room as (low, high) corners."""
    origin = np.asarray(found["at"])
    x, y, z = (np.asarray(found[axis]) for axis in ("x", "y", "z"))
    wide, tall, deep = found["size"]
    corners = [origin + x * a * wide / 2 + y * b * tall + z * c * deep / 2 for a in (-1, 1) for b in (0, 1) for c in (-1, 1)]
    return np.min(corners, axis=0), np.max(corners, axis=0)


def furniture_box(row, spot):
    """A furniture row's box at one of its spots: its footprint turned to its facing, from its foot (or round its
    middle, on a wall) up."""
    wide, deep, tall = row["size"]
    bearing = math.radians(spot["facing"])
    front = np.array([math.sin(bearing), 0.0, -math.cos(bearing)])
    side = np.array([math.cos(bearing), 0.0, math.sin(bearing)])
    middle = np.array([spot["x"], 0.0, spot["z"]])
    corners = [middle + side * a * wide / 2 + front * c * deep / 2 for a in (-1, 1) for c in (-1, 1)]
    low, high = np.min(corners, axis=0), np.max(corners, axis=0)
    bottom = spot["y"] if row["anchor"] == "floor" else spot["y"] - tall / 2
    low[1], high[1] = bottom, bottom + tall
    return low, high


def overlapping(first, second):
    return bool(np.all(first[0] < second[1] - CLEARANCE) and np.all(second[0] < first[1] - CLEARANCE))


def size_of(kinds, kind):
    """A kind's size in its frame: wide (x), tall (y), deep (z)."""
    wide, deep, tall = kinds[kind]["size"]
    return (wide, tall, deep)


def depth(kinds, kind):
    return size_of(kinds, kind)[2]


def spots(inventory, kind):
    for row in inventory["rows"]:
        if row["id"] == kind:
            return row.get("at", [])
    return []


def kit_kinds(inventory):
    """The kit's kinds from the inventory: every row made as a kit piece, by its row id."""
    return {row["id"]: row for row in inventory["rows"] if row.get("made") == "kit piece"}


def laid_out(inventory):
    kinds = kit_kinds(inventory)
    found = (walls(kinds) + roof(kinds) + ceiling_gear(kinds) + floor(kinds, inventory) + pit(kinds) + stairs(kinds)
             + doors(kinds, inventory) + split_at_fittings(clear_of_furniture(wall_gear(kinds, inventory), inventory)))
    return cut_openings(found)


def cut_openings(found):
    """Every set-in fitting's opening cut in its host piece (the host's `openings`: rectangles in its own frame, x and
    y, low then high), and the fitting moved along its host's front so its face lies SET_IN_DOWN below the host's."""
    for fitting in (laid for laid in found if laid.get("set_in")):
        host = host_of(fitting, found)
        corners = box_corners(fitting)
        origin, axes = np.asarray(host["at"]), [np.asarray(host[axis]) for axis in ("x", "y", "z")]
        local = (corners - origin) @ np.array(axes[:2]).T
        low, high = local.min(axis=0) - SET_IN_GAP, local.max(axis=0) + SET_IN_GAP
        host.setdefault("openings", []).append([round(float(value), 4) for value in (*low, *high)])
        sink = front_offset(fitting, host) + SET_IN_DOWN
        fitting["at"] = [round(float(value), 4) for value in np.asarray(fitting["at"]) + axes[2] * sink]
    return found


def host_of(fitting, found):
    """The piece a set-in fitting is set into: of its host kind, the one whose face its middle lies over."""
    kind = "hub_" + sorter.SET_IN[fitting["kind"].removeprefix("hub_")]
    middle = box_corners(fitting).mean(axis=0)
    hosts = [laid for laid in found if laid["kind"] == kind and over_face(middle, laid)]
    if len(hosts) != 1:
        raise SystemExit(f"{fitting['kind']} at {fitting['at']} lies over {len(hosts)} {kind} pieces; it must lie in one")
    return hosts[0]


def over_face(point, laid):
    """Whether a point lies over a piece's front face: inside its x and y, and within a hand's breadth of its face."""
    local = (point - np.asarray(laid["at"])) @ np.array([laid["x"], laid["y"], laid["z"]]).T
    wide, tall, deep = laid["size"]
    return abs(local[0]) <= wide / 2 and 0.0 <= local[1] <= tall and abs(local[2]) <= deep / 2 + 0.2


def front_offset(fitting, host):
    """How far a fitting's face stands out of its host's face, along the host's front (positive: proud)."""
    front = -np.asarray(host["z"])
    face_of = lambda laid: np.asarray(laid["at"]) - np.asarray(laid["z"]) * laid["size"][2] / 2
    return float((face_of(fitting) - face_of(host)) @ front)


def box_corners(laid):
    origin = np.asarray(laid["at"])
    x, y, z = (np.asarray(laid[axis]) for axis in ("x", "y", "z"))
    wide, tall, deep = laid["size"]
    return np.array([origin + x * a * wide / 2 + y * b * tall + z * c * deep / 2
                     for a in (-1, 1) for b in (0, 1) for c in (-1, 1)])


def standing_proud(found):
    """Every set-in fitting that stands out of its host's face or has no opening cut round it, as a line each."""
    problems = []
    for fitting in (laid for laid in found if laid.get("set_in")):
        host = host_of(fitting, found)
        if front_offset(fitting, host) > 1e-4:
            problems.append(f"{fitting['kind']} at {fitting['at']} stands {front_offset(fitting, host):.4f} m proud")
        local = (box_corners(fitting) - np.asarray(host["at"])) @ np.array([host["x"], host["y"]]).T
        if not any(cut[0] <= local[:, 0].min() and cut[1] <= local[:, 1].min() and local[:, 0].max() <= cut[2]
                   and local[:, 1].max() <= cut[3] for cut in host.get("openings", [])):
            problems.append(f"{fitting['kind']} at {fitting['at']} has no opening cut round it in its {host['kind']}")
    return problems


# --- the partition score -----------------------------------------------------------------------------------------

SAMPLE_M = 0.05
TOUCH_M = 0.03


def surface_samples():
    """Points over the room's visible surfaces, by surface, each with the surface's inward normal."""
    samples = {}
    points, normals = [], []
    for index in range(FACETS):
        bearing = index * 30
        normal, along = bearing_vectors(bearing)
        for across in np.arange(-FACET_WIDE / 2 + SAMPLE_M / 2, FACET_WIDE / 2, SAMPLE_M):
            for high in np.arange(SAMPLE_M / 2, WALL_HIGH, SAMPLE_M):
                if bearing in DOORS and abs(across) < DOORWAY[0] / 2 and high < DOORWAY[1]:
                    continue
                if in_a_joint(bearing, across):
                    continue  # the joined module's shell is the wall here
                points.append(normal * APOTHEM + along * across + np.array([0.0, high, 0.0]))
                normals.append(-normal)
    samples["walls"] = (np.array(points), np.array(normals))
    points, normals = [], []
    for radius in np.arange(PIT_R + SAMPLE_M, APOTHEM, SAMPLE_M):
        steps = max(12, int(2 * math.pi * radius / SAMPLE_M))
        for step in range(steps):
            angle = 2 * math.pi * step / steps
            point = np.array([math.sin(angle) * radius, 0.0, -math.cos(angle) * radius])
            bearing = math.degrees(angle) % 360
            facet = round(bearing / 30) * 30 % 360
            normal, _ = bearing_vectors(facet)
            if point @ normal > APOTHEM - SAMPLE_M / 2:
                continue
            if radius < PIT_R + 0.9 and near_a_stair(bearing, 15):
                continue  # a stair's head
            points.append(point)
            normals.append(np.array([0.0, 1.0, 0.0]))
    samples["ring floor"] = (np.array(points), np.array(normals))
    points, normals = [], []
    steps = int(2 * math.pi * PIT_R / SAMPLE_M)
    for step in range(steps):
        angle = 2 * math.pi * step / steps
        if near_a_stair(math.degrees(angle), 15):
            continue  # behind a stair
        outward = np.array([math.sin(angle), 0.0, -math.cos(angle)])
        for high in np.arange(-PIT_DEEP + SAMPLE_M / 2, 0.0, SAMPLE_M):
            points.append(outward * PIT_R + np.array([0.0, high, 0.0]))
            normals.append(-outward)
    samples["pit wall"] = (np.array(points), np.array(normals))
    points, normals = [], []
    for x in np.arange(-PIT_R, PIT_R, SAMPLE_M):
        for z in np.arange(-PIT_R, PIT_R, SAMPLE_M):
            if math.hypot(x, z) < PIT_R - SAMPLE_M:
                points.append(np.array([x, -PIT_DEEP, z]))
                normals.append(np.array([0.0, 1.0, 0.0]))
    samples["pit floor"] = (np.array(points), np.array(normals))
    points, normals = [], []
    for index in range(FACETS):
        bearing = index * 30
        normal, along = bearing_vectors(bearing)
        for share in np.arange(SAMPLE_M / 2, 1.0, SAMPLE_M / 4):
            wide = FACET_WIDE * (1 - share)
            for across in np.arange(-wide / 2 + SAMPLE_M / 2, wide / 2, SAMPLE_M):
                point = normal * APOTHEM * (1 - share) + along * across + np.array([0.0, WALL_HIGH + RISE * share, 0.0])
                points.append(point)
                normals.append(np.array([0.0, -1.0, 0.0]))
    samples["roof"] = (np.array(points), np.array(normals))
    return samples


def owners(points, normals, pieces):
    """How many pieces own each sample: the sample lies within the piece's footprint across the surface and the
    piece's back is within its depth plus TOUCH_M of the surface."""
    count = np.zeros(len(points), dtype=np.int32)
    for found in pieces:
        origin = np.asarray(found["at"])
        x, y, z = (np.asarray(found[axis]) for axis in ("x", "y", "z"))
        wide, tall, deep = found.get("scored", found["size"])
        local = points - origin
        across, up, out = local @ x, local @ y, local @ z
        half = wide / 2 * (1 - (1 - found.get("taper", 1.0)) * np.clip(up / tall, 0.0, 1.0))
        inside = (np.abs(across) <= half + 1e-6) & (up >= -1e-6) & (up <= tall + 1e-6) & (np.abs(out) <= deep / 2 + TOUCH_M)
        count += inside
    return count


def partition_score(pieces):
    """Point2Part's three numbers per surface: coverage, overlap and the gaps, in shares of the surface."""
    report = {}
    flat_kinds = [found for found in pieces if found["kind"] not in LAYERED]
    for name, (points, normals) in surface_samples().items():
        # The roof's eaves lap over the walls' top by design (EAVE): there they are the roof's, not the wall's.
        own = [found for found in flat_kinds if not (name == "walls" and found["kind"] == "hub_roof_face_panel")]
        count = owners(points, normals, own)
        report[name] = {"samples": int(len(points)), "coverage": round(float((count >= 1).mean()), 4),
                        "overlap": round(float((count >= 2).mean()), 4), "gaps": round(float((count == 0).mean()), 4)}
    total = sum(entry["samples"] for entry in report.values())
    report["all"] = {key: round(sum(entry[key] * entry["samples"] for entry in report.values()) / total, 4)
                     for key in ("coverage", "overlap", "gaps")}
    return report


# Pieces that stand on top of a surface's own piece rather than being the surface (the partition counts the surface's
# pieces only: a pipe in front of a wall panel is not an overlap of the wall).
LAYERED = {f"hub_{kind}" for kind in (
    "pipe_straight", "pipe_elbow", "pipe_valve", "pipe_bracket", "cable_bundle", "cable_drop", "conduit_box",
    "wall_cage_lamp", "small_readout", "intercom_panel", "status_display", "wall_screen_cluster", "notice_board",
    "door_strip_lamp", "door_control_box", "grab_bar", "floor_grating", "floor_access_hatch",
    "tread_mat", "pit_conduit", "pit_junction_box", "machine_bay_plate", "lattice_ring_rib", "lattice_hip_rib",
    "lattice_diamond_strut", "lattice_node_plate", "roof_apex_hub", "ceiling_cable_tray", "ceiling_duct",
    "roof_light_fixture", "stair_stringer",
    "hatch_frame", "hatch_leaf", "hatch_wheel", "hatch_hinge", "hatch_window", "airlock_frame", "airlock_leaf",
    "airlock_wheel", "airlock_hinge", "wall_skirting", "wall_cornice", "wall_corner_post", "waste_bin")}


# The lamps the kit carries (a real light each, tuned in the engine under the game's lighting setup): kind -> its
# light's strength (Lamp's share of LAMP_ENERGY), reach in metres and how high up the piece it sits as a share of its
# height. What glows is the made model's (tools/props/library/route.py: a screen's content, a lamp's lens).
LIGHTS = {"roof_light_fixture": {"strength": 0.16, "reach": 6.0, "high": 0.1},
          "door_strip_lamp": {"strength": 0.05, "reach": 3.0, "high": 0.5},
          "wall_cage_lamp": {"strength": 0.05, "reach": 3.5, "high": 0.5}}
# What each piece is to the scene check (resting.gd): the room's floors other things rest on, and what hangs from the
# wall, the roof or a door it touches rather than standing.
FLOORS = {"ring_floor_plate", "floor_grating", "floor_access_hatch", "tread_mat", "pit_floor_plate",
          "machine_bay_plate", "roof_face_panel",  # the roof's faces are its surface, as a floor is
          "stair_stringer"}  # a stair's sides carry its treads: part of the steps, as ShellSteps are
HANGING_GROUPS = {"wall", "ceiling", "door", "pipe", "sign", "screen", "light", "vent", "pit",
                  "under floor"}  # a duct or trough hung under a floor plate's opening


def kinds_table(inventory):
    """Every kit kind's light and group, for HubKit and the scene check."""
    table = {}
    for ident, row in kit_kinds(inventory).items():
        about = {}
        if ident in LIGHTS:
            about["light"] = LIGHTS[ident]
        if ident in FLOORS:
            about["group"] = "floors"
        elif row["group"].removeprefix("kit: ") in HANGING_GROUPS:
            about["group"] = "hangs"
        table[f"hub_{ident}"] = about
    return table


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    inventory = json.loads(INVENTORY.read_text())
    pieces = laid_out(inventory)
    counts = {}
    for found in pieces:
        counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    score = partition_score(pieces)
    pathlib.Path(sys.argv[1]).write_text(json.dumps({"room": "hub", "frame": "the Habitat node's own: x east, z south, y up from the ring floor",
                               "counts": counts, "partition": score, "kinds": kinds_table(inventory), "pieces": pieces},
                              indent="\t") + "\n")
    print(len(pieces), "pieces of", len(counts), "kinds")
    for name, entry in score.items():
        print(f"  {name:10s} coverage {entry['coverage']:.3f}  overlap {entry['overlap']:.3f}  gaps {entry['gaps']:.3f}")


if __name__ == "__main__":
    main()
