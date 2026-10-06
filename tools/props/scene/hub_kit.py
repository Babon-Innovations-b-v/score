"""The hub's kit layout: where every made piece of the C12 room stands (job hubkit, the owner 2026-10-05: code only lays
out, every visible surface is a made piece placed like a kit).

    python3 tools/props/scene/hub_kit.py            # writes data/kit/hub.json and prints the partition score

The room's numbers are the shell's (ModuleShell.KIT for the hub, ModuleFloors: twelve walls whose inside faces stand
APOTHEM from the middle, WALL_HIGH tall under a pyramid roof rising RISE, a pit PIT_R round and PIT_DEEP deep behind a
rail, the doors on their walls). Frame: the Habitat node's own, x east, z south, y up from the ring floor; a wall's
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

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
OUT = REPO / "data/kit/hub.json"
INVENTORY = REPO / "data/inventory/hub.json"

APOTHEM = 4.5
FACETS = 12
FACET_WIDE = 2 * APOTHEM * math.tan(math.pi / FACETS)
WALL_HIGH = 3.1
RISE = 1.7
PIT_R = 2.33
PIT_DEEP = 0.9
RAIL_R = 2.45
STAIR_HALF = 0.6
LATTICE_UNDER = 0.14
# The roof's panels reach this far past the wall's top down their slope (widening on as their faces do), and are this
# much wider again, so no look up between the wall and the roof, or between two roof faces, finds a seam.
EAVE = 0.15
# The cable runs' foot: above the tallest wall gear (the status display's top, 2.73 m) and under the cornice.
CABLE_HIGH = 2.76
EAVE_WIDER = 1.01
JUNCTION_BOXES = (30, 200, 260)
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
LOWER_PANELS = {60: "wall_lower_vent", 120: "wall_lower_patched", 240: "wall_lower_vent"}
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
TRAY_FACES = (0, 60, 120, 180, 240, 300)
DUCT_FACES = (30, 150, 270)
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
    """The ring floor's plates, a sector of each wall's width between the pit's lip and the wall; gratings and access
    hatches set in some, cable covers across the walkway, a tread mat before every hatch and the lip round the pit."""
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
    for bearing in (45, 105, 165, 225, 285, 345):
        normal, along = bearing_vectors(bearing)
        found.append(flat("floor_grating", normal * 3.4, along, size_of(kinds, "floor_grating"), 0.003))
    for bearing in (75, 135, 195, 255):
        normal, along = bearing_vectors(bearing)
        found.append(flat("floor_access_hatch", normal * 3.9, along, size_of(kinds, "floor_access_hatch"), 0.003))
    for bearing in (20, 140, 200, 320):
        normal, along = bearing_vectors(bearing)
        found.append(flat("floor_cable_cover", normal * 2.9, along, size_of(kinds, "floor_cable_cover"), 0.006))
    for spot in spots(inventory, "tread_mat"):
        normal, along = bearing_vectors(spot["facet"])
        found.append(flat("tread_mat", np.array([spot["x"], 0.0, spot["z"]]), along, size_of(kinds, "tread_mat"), 0.006))
    lip = size_of(kinds, "pit_lip_segment")
    for index in range(10):
        bearing = index * 36 + 18
        if abs(((bearing + 180) % 360) - 180) < 20:
            continue  # the stair's opening
        normal, along = bearing_vectors(bearing)
        found.append(flat("pit_lip_segment", normal * (PIT_R + lip[1] / 2), along, (2 * math.pi * PIT_R / 10, lip[1], lip[2]), 0.0))
    return found


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
        if abs(((bearing + 180) % 360) - 180) > 25:
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


def rail(kinds):
    """The rail round the pit: a post every 15 degrees, a section between each two, open at the stair (north) with
    heavier end posts either side; the stair and its two handrails."""
    found = []
    opening = math.degrees(math.asin((STAIR_HALF + 0.05) / RAIL_R))
    bearings = [bearing for bearing in range(0, 360, 15) if abs(((bearing + 180) % 360) - 180) > opening + 1]
    post = size_of(kinds, "rail_post")
    for bearing in bearings:
        normal, _ = bearing_vectors(bearing)
        found.append(piece("rail_post", normal * RAIL_R, frame_facing(-normal, (0, 1, 0)), post))
    for start, end in zip(bearings, bearings[1:]):
        if end - start != 15:
            continue
        middle = (start + end) / 2
        normal, along = bearing_vectors(middle)
        chord = 2 * RAIL_R * math.sin(math.radians(7.5)) - post[0]
        section = size_of(kinds, "rail_section")
        found.append(piece("rail_section", normal * RAIL_R * math.cos(math.radians(7.5)), frame_facing(-normal, (0, 1, 0)),
                           (chord, section[1], section[2])))
    end_post = size_of(kinds, "rail_end_post")
    for side in (-1, 1):
        bearing = side * opening
        normal, _ = bearing_vectors(bearing)
        found.append(piece("rail_end_post", normal * RAIL_R, frame_facing(-normal, (0, 1, 0)), end_post))
    found += stair(kinds)
    return found


def stair(kinds):
    """The stair down into the pit at the north, built of the kit's own pieces (the stair and handrail models came out
    as blobs twice): a floor grating for each of its four treads at the sim's tread heights (StepFloor's pit), a pit
    floor plate standing as each riser, a pipe for each stringer under the treads' ends and for each handrail from
    the rail's top down to the pit floor's."""
    found = []
    normal, along = bearing_vectors(0)
    grating = size_of(kinds, "floor_grating")
    pipe = size_of(kinds, "pipe_straight")
    depth_each = (PIT_R - STAIR_FOOT) / STAIR_TREADS
    for step in range(STAIR_TREADS):
        middle = normal * (PIT_R - depth_each * (step + 0.5))
        top = -STAIR_RISE * (step + 1)
        found.append(flat("floor_grating", middle + np.array([0.0, top - grating[2], 0.0]), along,
                          (2 * STAIR_HALF, depth_each, grating[2]), 0.0))
        riser = size_of(kinds, "pit_floor_plate")
        near = normal * (PIT_R - depth_each * (step + 1) + riser[2] / 2)
        found.append(piece("pit_floor_plate", near + np.array([0.0, top - STAIR_RISE, 0.0]), frame_facing(-normal, (0, 1, 0)),
                           (2 * STAIR_HALF, STAIR_RISE, riser[2])))
    for side in (-1, 1):
        edge = along * side * (STAIR_HALF - pipe[1] / 2)
        found.append(bar("pipe_straight", normal * PIT_R + edge + np.array([0.0, -STAIR_RISE / 2, 0.0]),
                         normal * STAIR_FOOT + edge + np.array([0.0, -PIT_DEEP + 0.02, 0.0]), kinds, layer=1))
        rail_side = along * side * (STAIR_HALF + 0.03)
        found.append(bar("pipe_straight", normal * PIT_R + rail_side + np.array([0.0, 1.0, 0.0]),
                         normal * STAIR_FOOT + rail_side + np.array([0.0, -PIT_DEEP + 1.0, 0.0]), kinds, layer=1))
    return found


LEAF_OVER = 0.06
SHELL_WALL = 0.3  # the shell's wall thickness (ModuleShell.WALL)
# A wall where another module is joined into the hub's wall (the airlock, turned onto its 330-degree wall): that
# module's shell reaches into the hub's wall there and brings its own doorway, frame and door, so the kit lays no
# frame, hinges or corner posts on it.
JOINED_MODULE = (330,)
JOINT_CLEAR = 0.3


def framed(kinds, kind):
    """A door's frame laid so its opening (PICTURED's hole) is exactly the shell's doorway, as wide as it was made."""
    hole = PICTURED[f"{kind}_frame"]
    wide, tall, deep = size_of(kinds, f"{kind}_frame")
    return (DOORWAY[0] / (hole[2] - hole[0]), DOORWAY[1] / hole[3], deep)


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
            found.append(on_lining(kinds, kind, spot["facet"], spot["across"], middle_high - size[1] / 2, size))
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
    for bearing, highs in ((210, (0.75, 1.35, 1.95)), (330, (2.6,)), (300, (0.55,)), (240, (2.6,))):
        for high in highs:
            for across in (-0.6, 0.6):
                found.append(on_lining(kinds, "pipe_straight", bearing, across, high - straight[1] / 2,
                                     (FACET_WIDE / 2 - 0.02, straight[1], straight[2]), out=bracket[2]))
            found.append(on_lining(kinds, "pipe_bracket", bearing, -0.6, high - bracket[1] / 2, bracket))
            found.append(on_lining(kinds, "pipe_bracket", bearing, 0.6, high - bracket[1] / 2, bracket))
    for bearing, across, high in ((210, 0.3, 1.35), (210, -0.3, 0.75), (330, 0.8, 2.6), (300, -0.5, 0.55)):
        found.append(on_lining(kinds, "pipe_valve", bearing, across, high - valve[1] / 2, valve, out=bracket[2]))
    for bearing in (210, 240, 300, 330):
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
    for bearing, across in ((30, 0.0), (60, 0.0), (120, 0.0), (150, 0.0), (240, -0.3), (300, 0.0), (210, 1.0), (330, -1.0)):
        found.append(on_lining(kinds, "conduit_box", bearing, across, WALL_HIGH - 0.75, box, out=0.0))
    lamp = size_of(kinds, "wall_cage_lamp")
    for bearing in (30, 120, 150, 210, 240, 300):
        found.append(on_lining(kinds, "wall_cage_lamp", bearing, 0.0 if bearing != 300 else 0.9, 2.45, lamp))
    readout = size_of(kinds, "small_readout")
    for bearing, across in ((150, -0.7), (240, 0.8), (60, 0.8), (210, -0.9)):
        found.append(on_lining(kinds, "small_readout", bearing, across, 1.35, readout))
    intercom = size_of(kinds, "intercom_panel")
    for bearing, across in ((60, -0.9),):  # one: every other free wall at hand height has furniture or door fittings
        found.append(on_lining(kinds, "intercom_panel", bearing, across, 1.2, intercom))
    bin_size = size_of(kinds, "waste_bin")
    normal, along = bearing_vectors(240)
    found.append(piece("waste_bin", normal * (APOTHEM - lining(kinds, 240, 0.0, bin_size[1]) - bin_size[2] / 2 - 0.02)
                       + along * 0.95, frame_facing(-normal, (0, 1, 0)), bin_size))
    return found


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
    return (walls(kinds) + roof(kinds) + ceiling_gear(kinds) + floor(kinds, inventory) + pit(kinds) + rail(kinds)
            + doors(kinds, inventory) + clear_of_furniture(wall_gear(kinds, inventory), inventory))


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
            if radius < PIT_R + 0.9 and abs(((bearing + 180) % 360) - 180) < 15:
                continue  # the stair's head
            points.append(point)
            normals.append(np.array([0.0, 1.0, 0.0]))
    samples["ring floor"] = (np.array(points), np.array(normals))
    points, normals = [], []
    steps = int(2 * math.pi * PIT_R / SAMPLE_M)
    for step in range(steps):
        angle = 2 * math.pi * step / steps
        if abs(((math.degrees(angle) + 180) % 360) - 180) < 15:
            continue  # behind the stair
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
    "door_strip_lamp", "door_control_box", "grab_bar", "floor_grating", "floor_access_hatch", "floor_cable_cover",
    "tread_mat", "pit_conduit", "pit_junction_box", "machine_bay_plate", "lattice_ring_rib", "lattice_hip_rib",
    "lattice_diamond_strut", "lattice_node_plate", "roof_apex_hub", "ceiling_cable_tray", "ceiling_duct",
    "roof_light_fixture", "rail_post", "rail_section", "rail_end_post", "stair_flight", "stair_handrail",
    "hatch_frame", "hatch_leaf", "hatch_wheel", "hatch_hinge", "hatch_window", "airlock_frame", "airlock_leaf",
    "airlock_wheel", "airlock_hinge", "wall_skirting", "wall_cornice", "wall_corner_post", "waste_bin", "pit_lip_segment")}


# The lamps the kit carries (a real light each, tuned in the engine under the game's lighting setup) and the screens
# that glow: kind -> its light's strength (Lamp's share of LAMP_ENERGY), reach in metres and how high up the piece it
# sits as a share of its height.
LIGHTS = {"roof_light_fixture": {"strength": 0.16, "reach": 6.0, "high": 0.1},
          "door_strip_lamp": {"strength": 0.05, "reach": 3.0, "high": 0.5},
          "wall_cage_lamp": {"strength": 0.05, "reach": 3.5, "high": 0.5}}
GLOWS = {"status_display", "wall_screen_cluster", "small_readout"}
# What each piece is to the scene check (resting.gd): the room's floors other things rest on, and what hangs from the
# wall, the roof or a door it touches rather than standing.
FLOORS = {"ring_floor_plate", "floor_grating", "floor_access_hatch", "floor_cable_cover", "tread_mat", "pit_floor_plate",
          "machine_bay_plate", "pit_lip_segment", "roof_face_panel"}  # the roof's faces are its surface, as a floor is
HANGING_GROUPS = {"wall", "ceiling", "door", "pipe", "sign", "screen", "light", "vent", "pit"}
# Pieces Pixal3D cannot make, drawn as their clean front picture on a box less the doorway (HubKit.pictured_mesh): a
# frame round a doorway came out with its hole filled, the porthole's panel as a blob. Kind -> the hole in shares of
# its face seen from in front, [left, bottom, right, top]; none for the porthole.
PICTURED = {"hatch_frame": [0.0417, 0.0, 0.9583, 0.9655],
            "hatch_wall_surround": [0.0436, 0.0, 0.9564, 0.869], "porthole_panel": []}
# The roof's faces, drawn as their clean picture on a triangle (HubKit.pictured_triangle): the made model came out a
# right triangle, half a face, and left the roof open between its faces (seen from the room, 2026-10-06).
TRIANGLES = {"roof_face_panel"}
MODELS = REPO / "game/base/models"


# Kinds whose front the flat-back test reads the wrong way round (checked by eye on the kit's front sheet).
FLIPPED = {"door_control_box"}


def base_for(kind, size, mesh):
    """The turn that stands a made model in its kind's frame (wide x, tall y, deep z, front toward -z). Rows of a 3x3.
    A flat piece (a panel, a plate, a board, a frame, a door) was made from a picture of its face, stood up: its
    height is the model's up (y) and its width the longer of its ground sides; the other ground side is the depth
    Pixal3D guessed, however thick it came out. A model lying flat (its up the thinnest by far) has its face on the
    ground instead. Any other piece has its sides matched to the kind's by length. Then the flat back goes away from
    the room (or the kind is FLIPPED), and a flat piece turned in its own face is squared to its frame."""
    extents = mesh.extents
    turn = np.zeros((3, 3))
    flat = size[2] < 0.25 * min(size[0], size[1])
    if flat and extents[1] > 0.25 * max(extents[0], extents[2]):
        wide_axis, deep_axis = (0, 2) if facing_axis(mesh) == 2 else (2, 0)
        turn[0, wide_axis] = turn[1, 1] = turn[2, deep_axis] = 1.0
        if size[1] > size[0]:  # a kind taller than wide: its face's longer side is its height
            if extents[1] < max(extents[0], extents[2]):
                turn = np.zeros((3, 3))
                turn[1, wide_axis] = turn[0, 1] = turn[2, deep_axis] = 1.0
    elif flat:
        wide_axis, tall_axis = (0, 2) if extents[0] >= extents[2] else (2, 0)
        if (size[0] >= size[1]) != (extents[wide_axis] >= extents[tall_axis]):
            wide_axis, tall_axis = tall_axis, wide_axis
        turn[0, wide_axis] = turn[1, tall_axis] = turn[2, 1] = 1.0
    else:
        for model_axis, kind_axis in zip(np.argsort(extents), np.argsort(np.asarray(size))):
            turn[kind_axis, model_axis] = 1.0
    if np.linalg.det(turn) < 0:
        turn[0] *= -1
    if flat:
        turn = squared_in_its_face(mesh, turn, size) @ turn
    if flat_side_ahead(mesh, turn) != (kind in FLIPPED):
        turn = np.diag([-1.0, 1.0, -1.0]) @ turn
    return [round(float(value), 6) for value in turn.ravel()]


def facing_axis(mesh):
    """Which ground axis (0 x or 2 z) a stood-up flat model faces along: the one its surface looks along most (its
    face and back), by area. Its extents cannot tell when Pixal3D made it nearly as deep as it is wide."""
    looks = np.abs(mesh.face_normals) * mesh.area_faces[:, None]
    return 0 if looks[:, 0].sum() >= looks[:, 2].sum() else 2


# A flat piece's outline fills at least this share of the smallest rectangle round it when it is a rectangle at all.
SQUARE_FILL = 0.8


def squared_in_its_face(mesh, turn, size):
    """The turn about the depth axis that squares a flat piece's outline to its frame: the model came out turned in
    its own face (a plate on its corner), so its box is filled least; the smallest rectangle round its outline in the
    face gives the angle, its longer side laid along the kind's longer face side."""
    points = (mesh.vertices @ turn.T)[:, :2]
    hull = points[_hull(points)]
    area = 0.5 * abs(np.dot(hull[:, 0], np.roll(hull[:, 1], 1)) - np.dot(hull[:, 1], np.roll(hull[:, 0], 1)))
    best = (math.inf, 0.0)
    for index in range(len(hull)):
        edge = hull[(index + 1) % len(hull)] - hull[index]
        angle = math.atan2(edge[1], edge[0])
        turned = hull @ np.array([[math.cos(-angle), -math.sin(-angle)], [math.sin(-angle), math.cos(-angle)]]).T
        extent = turned.max(axis=0) - turned.min(axis=0)
        if extent[0] * extent[1] < best[0]:
            best = (extent[0] * extent[1], angle if (extent[0] >= extent[1]) == (size[0] >= size[1]) else angle + math.pi / 2)
    if area < SQUARE_FILL * best[0]:
        return np.eye(3)  # not a rectangle (a roof face's triangle): its box already holds it as made
    angle = -best[1]
    return np.array([[math.cos(angle), -math.sin(angle), 0.0], [math.sin(angle), math.cos(angle), 0.0], [0.0, 0.0, 1.0]])


def _hull(points):
    """The convex hull's corners of 2D points, in order (monotone chain)."""
    order = np.lexsort((points[:, 1], points[:, 0]))
    def cross(origin, first, second):
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (first[1] - origin[1]) * (second[0] - origin[0])
    lower, upper = [], []
    for index in order:
        while len(lower) >= 2 and cross(points[lower[-2]], points[lower[-1]], points[index]) <= 0:
            lower.pop()
        lower.append(index)
    for index in order[::-1]:
        while len(upper) >= 2 and cross(points[upper[-2]], points[upper[-1]], points[index]) <= 0:
            upper.pop()
        upper.append(index)
    return lower[:-1] + upper[:-1]


def flat_side_ahead(mesh, turn):
    """Whether the model, turned, has its flat back toward -z: the side with more surface lying flat at its far end."""
    vertices = mesh.vertices @ turn.T
    normals = mesh.face_normals @ turn.T
    centres = mesh.triangles_center @ turn.T
    low, high = vertices[:, 2].min(), vertices[:, 2].max()
    band = (high - low) * 0.03 + 1e-4
    ahead = mesh.area_faces[(normals[:, 2] < -0.9) & (centres[:, 2] < low + band)].sum()
    behind = mesh.area_faces[(normals[:, 2] > 0.9) & (centres[:, 2] > high - band)].sum()
    return ahead > behind * 1.3


def kinds_table(inventory):
    """Every kit kind's model turn, light and glow, for HubKit."""
    import trimesh
    table = {}
    for ident, row in kit_kinds(inventory).items():
        about = {}
        glb = MODELS / f"hub_{ident}" / f"hub_{ident}.glb"
        if ident in PICTURED:
            about["picture"] = f"res://game/base/hub_kit/pictures/hub_{ident}.png"
            about["hole"] = PICTURED[ident]
        elif ident in TRIANGLES:
            about["picture"] = f"res://game/base/hub_kit/pictures/hub_{ident}.png"
            about["shape"] = "triangle"
        elif glb.exists():
            wide, deep, tall = row["size"]
            about["base"] = base_for(ident, (wide, tall, deep), trimesh.load(glb, force="mesh"))
        if ident in LIGHTS:
            about["light"] = LIGHTS[ident]
        if ident in GLOWS:
            about["glows"] = True
        if ident in FLOORS:
            about["group"] = "floors"
        elif row["group"].removeprefix("kit: ") in HANGING_GROUPS:
            about["group"] = "hangs"
        table[f"hub_{ident}"] = about
    return table


def main():
    inventory = json.loads(INVENTORY.read_text())
    pieces = laid_out(inventory)
    counts = {}
    for found in pieces:
        counts[found["kind"]] = counts.get(found["kind"], 0) + 1
    score = partition_score(pieces)
    OUT.write_text(json.dumps({"room": "hub", "frame": "the Habitat node's own: x east, z south, y up from the ring floor",
                               "counts": counts, "partition": score, "kinds": kinds_table(inventory), "pieces": pieces},
                              indent="\t") + "\n")
    print(len(pieces), "pieces of", len(counts), "kinds")
    for name, entry in score.items():
        print(f"  {name:10s} coverage {entry['coverage']:.3f}  overlap {entry['overlap']:.3f}  gaps {entry['gaps']:.3f}")


if __name__ == "__main__":
    main()
