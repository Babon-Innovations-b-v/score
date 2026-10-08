"""The prologue's rooms as kit layouts: where every made piece of the flat and the stairwell stands (the prologue build,
2026-10-07: the hub's route for Earth, code only lays out, every visible piece is a made model).

    python3 tools/props/scene/earth_kit.py <room> <out.json>      # room: flat or stairwell

The laid-out room is the robust route's input (tools/props/library/route.py plan and layout), which makes a model for
every piece and writes the game's layout, data/kit/<room>.json, which EarthSite draws through HubKit at the room's
origin (ORIGINS). The numbers are EarthSite's (game/prologue/earth_site/earth_site.gd; earth_kit_test.py reads them
there), so a wall that moves in the game moves here. Frame: the Earth block's, x across, z along the street, y up from
the room's own floor (the flat's floor is FLAT_LEVEL up; the stairwell's is the street's).

Every piece is laid in its kind's own frame (HubKit): as wide as x, as tall as y, as deep as z, standing on its origin
at the middle of its foot, its front toward -z; a piece is written as its kind (`<room>_<own name>`), where its origin
stands, its frame's three axes and its size. `back` below is the way the piece's back faces (a wall plate's back is on
its wall).
"""
import json
import pathlib
import sys

import numpy as np

# EarthSite's numbers (earth_kit_test.py checks them against the script).
FLAT_LEVEL = 9.0
FLAT_HEIGHT = 2.8
WALL = 0.2
FLOOR_THICKNESS = 0.04
FLAT_GROUND = (-3.0, -6.0, 6.0, 5.0)  # x, z, wide, deep
BALCONY_GROUND = (-5.2, -5.5, 2.2, 4.0)
STAIRWELL_GROUND = (3.0, -6.0, 3.0, 5.0)
BALCONY_DOORWAY = (1.4, 2.2)
FRONT_DOORWAY = (1.0, 2.2)
FRONT_DOOR_Z = -1.6
STREET_DOORWAY = (1.0, 2.2)
STAIR_LANE_A = (3.2, 4.55)
STAIR_LANE_B = (4.65, 6.0)
LANDING_DEPTH = 1.2
FLIGHT_RISE = 1.5
DADO_HEIGHT = 1.2
RAIL_HEIGHT = 1.1
BALCONY_SPOT_Z = -3.5
# Where the game hangs each room's kit (HubKit's own origin) in the Earth block.
ORIGINS = {"flat": (0.0, FLAT_LEVEL, 0.0), "stairwell": (0.0, 0.0, 0.0)}
PLACES = {"flat": "prologue_flat", "stairwell": "prologue_stairwell"}
FLOOR_TOP = FLOOR_THICKNESS / 2  # a floor's top over its level
# The street kit's rendered plates on the block's street face and its pavement's top (earth_outside_kit.py).
STREET_PLATE = 0.15
STREET_PAVED_TOP = 0.14
# How far out of the street face's plates the open street gate's spot stands (its made box then clears them by 5 mm).
GATE_CLEAR = 0.14
LINING = 0.03  # a wall lining's depth
UP = np.array([0.0, 1.0, 0.0])
DOWN = -UP
EAST, WEST, SOUTH, NORTH = (np.array(value) for value in ((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
                                                           (0.0, 0.0, -1.0)))


def piece(room, own, at, back, size, up=UP, **extra):
    """One laid piece: its kind, its origin, its frame (y up, z its back, x = y cross z) and size, and what it shows."""
    y_axis, z_axis = np.asarray(up, dtype=float), np.asarray(back, dtype=float)
    x_axis = np.cross(y_axis, z_axis)
    found = {"kind": f"{room}_{own}", "at": [round(float(value), 4) for value in at],
             "x": [round(float(value), 5) + 0.0 for value in x_axis],
             "y": [round(float(value), 5) + 0.0 for value in y_axis],
             "z": [round(float(value), 5) + 0.0 for value in z_axis],
             "size": [round(float(value), 4) for value in size], "layer": 1}
    found.update(extra)
    return found


def lying(room, own, at, along, back, size, **extra):
    """A plate lying flat, laid as a wall plate is (its front its seen face, its back on what holds it): `at` the
    middle of its edge it starts from, `along` the way it runs from there, `back` up for a ceiling, down for a floor;
    so the bake gives its unseen back a twentieth (the hub's floors are laid so)."""
    return piece(room, own, at, back, size, up=along, **extra)


def wall_lining(room, face, back, middle_along, wide, bottom, tall, openings=(), dado=DADO_HEIGHT, **extra):
    """A plaster wall plate on a wall's face: `face` the face's place on its axis, the plate's back on it."""
    back = np.asarray(back, dtype=float)
    across = np.cross(UP, back)
    at = back * (face - LINING / 2 * 1.0) if back.any() else None
    origin = np.zeros(3)
    axis = int(np.argmax(np.abs(back)))
    origin[axis] = face - back[axis] * LINING / 2
    along_axis = int(np.argmax(np.abs(across)))
    origin[along_axis] = middle_along
    origin[1] = bottom
    del at
    return piece(room, "plaster_wall", origin, back, (wide, tall, LINING), dado=dado,
                 openings=[list(map(lambda value: round(value, 4), opening)) for opening in openings], **extra)


def along_in_kit(back, middle_along, world_along):
    """Where a point along a wall (its world coordinate along the wall) lies on the plate's kit x."""
    across = np.cross(UP, np.asarray(back, dtype=float))
    sign = across[np.argmax(np.abs(across))]
    return (world_along - middle_along) * sign


def doorway(back, middle_along, centre, wide, high, bottom=0.0):
    """A doorway's opening in a wall plate's kit frame: [x0, y0, x1, y1]."""
    middle = along_in_kit(back, middle_along, centre)
    return [middle - wide / 2, bottom, middle + wide / 2, bottom + high]


def flat():
    """The flat: its four walls, floor and ceiling, the balcony (slab, rails, the outside wall, the door), the front
    door, the furniture and what stands on it, and the prints on the walls. Frame y from the flat's floor level."""
    room = "flat"
    x0, z0, wide, deep = FLAT_GROUND
    x1, z1 = x0 + wide, z0 + deep
    middle_x, middle_z = x0 + wide / 2, z0 + deep / 2
    top = FLOOR_TOP
    found = [
        wall_lining(room, z0, NORTH, middle_x, wide, top, FLAT_HEIGHT - top),
        wall_lining(room, z1, SOUTH, middle_x, wide, top, FLAT_HEIGHT - top),
        wall_lining(room, x0, WEST, middle_z, deep, top, FLAT_HEIGHT - top,
                    [doorway(WEST, middle_z, BALCONY_SPOT_Z, *BALCONY_DOORWAY)]),
        wall_lining(room, x1, EAST, middle_z, deep, top, FLAT_HEIGHT - top,
                    [doorway(EAST, middle_z, FRONT_DOOR_Z, *FRONT_DOORWAY)]),
        lying(room, "floorboards", (middle_x, top - 0.015, z0), SOUTH, DOWN, (wide, deep, 0.03)),
        lying(room, "plaster_ceiling", (middle_x, FLAT_HEIGHT + 0.015, z0), SOUTH, UP, (wide, deep, 0.03)),
    ]
    found += balcony(room)
    found += front_door(room)
    found += furniture(room)
    return found


def balcony(room):
    """The balcony's slab and rails, the flat's outside wall over it and the door out to it."""
    bx, bz, bwide, bdeep = BALCONY_GROUND
    slab_x0, slab_x1 = bx - WALL, FLAT_GROUND[0] - WALL
    slab_z0, slab_z1 = bz - WALL, bz + bdeep + WALL
    outer_x, near_z, far_z = bx - WALL / 2, bz - WALL / 2, bz + bdeep + WALL / 2
    face = FLAT_GROUND[0] - WALL
    middle_z = (slab_z0 + slab_z1) / 2
    return [
        piece(room, "balcony_slab", ((slab_x0 + slab_x1) / 2, FLOOR_TOP - 0.2, middle_z), EAST,
              (slab_z1 - slab_z0, 0.2, slab_x1 - slab_x0)),
        piece(room, "balcony_rail", (outer_x, FLOOR_TOP, (near_z + far_z) / 2), EAST, (far_z - near_z, RAIL_HEIGHT, 0.06)),
        piece(room, "balcony_rail", ((outer_x + face) / 2, FLOOR_TOP, near_z), SOUTH, (face - outer_x, RAIL_HEIGHT, 0.06)),
        piece(room, "balcony_rail", ((outer_x + face) / 2, FLOOR_TOP, far_z), NORTH, (face - outer_x, RAIL_HEIGHT, 0.06)),
        piece(room, "render_wall", (face - LINING / 2, FLOOR_TOP, middle_z), EAST, (slab_z1 - slab_z0, 3.0 - FLOOR_TOP, LINING),
              openings=[doorway(EAST, middle_z, BALCONY_SPOT_Z, *BALCONY_DOORWAY)]),
        piece(room, "balcony_door_frame", (face - 0.04, FLOOR_TOP, BALCONY_SPOT_Z), EAST, (1.54, 2.62, 0.08)),
        # The sliding leaf is drawn by the game's own moving door (EarthSite.balcony_door), not the kit.
        piece(room, "sliding_glass_leaf", (FLAT_GROUND[0] + 0.05, FLOOR_TOP, BALCONY_SPOT_Z), WEST, (1.44, 2.2, 0.04),
              node="BalconyDoor"),
    ]


def front_door(room):
    """The front door's frame through the wall, and its leaf standing open against the inside of the wall."""
    x1 = FLAT_GROUND[0] + FLAT_GROUND[2]
    hinge_z = FRONT_DOOR_Z - FRONT_DOORWAY[0] / 2
    return [
        piece(room, "timber_door_frame", (x1 + WALL / 2, FLOOR_TOP, FRONT_DOOR_Z), EAST, (1.14, 2.28, 0.24)),
        piece(room, "timber_door_leaf", (x1 - 0.03, FLOOR_TOP, hinge_z - 0.47), EAST, (0.94, 2.17, 0.045)),
    ]


def furniture(room):
    """The furniture against the walls by the room's plan (concepts-world1/flat/plan), and what stands on it."""
    x0, z0, wide, deep = FLAT_GROUND
    z1 = z0 + deep
    top = FLOOR_TOP
    back_wall, front_wall = z0 + LINING, z1 - LINING
    found = [
        piece(room, "wardrobe", (-0.05, top, back_wall + 0.275), NORTH, (1.0, 1.9, 0.55)),
        piece(room, "bedside_table", (0.75, top, back_wall + 0.18), NORTH, (0.4, 0.58, 0.36)),
        piece(room, "bed_frame", (1.955, top, back_wall + 0.475), NORTH, (1.95, 0.9, 0.95)),
        piece(room, "table", (-0.85, top, -4.25), NORTH, (0.9, 0.76, 0.7)),
        piece(room, "timber_chair", (-0.85, top, -4.85), NORTH, (0.42, 0.9, 0.45)),
        piece(room, "timber_chair", (-0.85, top, -3.65), SOUTH, (0.42, 0.9, 0.45)),
        # The TV stands beside the balcony door, as the picked concept has it (the door's open leaf parks on the
        # wall's other side of the doorway).
        piece(room, "tv_cabinet", (x0 + LINING + 0.21, top, -5.1), WEST, (1.0, 0.5, 0.42)),
        piece(room, "washbasin_stand", (-0.95, top, front_wall - 0.225), SOUTH, (0.45, 0.82, 0.45)),
        piece(room, "kitchen_counter", (0.65, top, front_wall - 0.3), SOUTH, (1.9, 1.45, 0.6)),
        piece(room, "wall_shelf", (0.65, 1.6, front_wall - 0.11), SOUTH, (1.2, 0.25, 0.22)),
        piece(room, "ceiling_fan", (0.0, FLAT_HEIGHT - 0.55, BALCONY_SPOT_Z), NORTH, (1.2, 0.55, 1.2)),
        piece(room, "tube_light", (1.6, FLAT_HEIGHT - 0.09, BALCONY_SPOT_Z), NORTH, (1.25, 0.09, 0.12)),
        piece(room, "wall_print", (2.2, 1.45, back_wall + 0.015), NORTH, (0.3, 0.4, 0.03),
              print="flat_family_photo", frame=True),
        piece(room, "wall_print", (1.3, 1.3, back_wall + 0.004), NORTH, (0.34, 0.5, 0.004), print="flat_calendar",
              frame=False),
        piece(room, "wall_print", (-2.2, 1.75, front_wall - 0.004), SOUTH, (1.0, 0.36, 0.004),
              print="flat_poster_red", frame=False),
        piece(room, "wall_print", (2.25, 1.15, front_wall - 0.004), SOUTH, (0.5, 0.71, 0.007),
              print="flat_astronaut_poster", frame=False),
    ]
    return found + on_furniture(room)


# What stands on the furniture: the sizes are the made models' own proportions (their finished Pixal3D boxes),
# set once the models are back (ON_FURNITURE_SIZES); where each stands is read off its holder's plan above.
ON_FURNITURE = [
    # own, at (x, y over the floor, z), back, size (wide, tall, deep: each generated model at its own proportions)
    ("mattress", (1.955, 0.37, -5.495), NORTH, (1.86, 0.14, 0.88)),
    ("quilt", (2.55, 0.51, -5.495), NORTH, (0.5, 0.276, 0.488)),
    ("pillow", (1.25, 0.51, -5.495), NORTH, (0.6, 0.211, 0.43)),
    ("bedside_lamp", (0.75, 0.6, -5.79), NORTH, (0.233, 0.42, 0.229)),
    ("crt_tv", (-2.75, 0.52, -5.1), WEST, (0.52, 0.346, 0.444)),
    ("enamel_basin", (-0.95, 0.74, -1.255), SOUTH, (0.42, 0.128, 0.417)),
    ("gas_stove", (1.15, 0.87, -1.33), SOUTH, (0.62, 0.21, 0.466)),
    ("kettle", (0.98, 1.08, -1.33), SOUTH, (0.26, 0.264, 0.232)),
    ("thermos", (0.15, 1.85, -1.14), SOUTH, (0.175, 0.36, 0.129)),
    ("thermos", (-0.62, 0.78, -4.38), SOUTH, (0.175, 0.36, 0.129)),
    ("tea_tin", (1.0, 1.85, -1.14), SOUTH, (0.09, 0.13, 0.09)),
    ("tea_tin", (1.12, 1.85, -1.14), SOUTH, (0.09, 0.13, 0.09)),
    ("storage_box", (-0.05, 1.92, -5.75), NORTH, (0.45, 0.24, 0.38)),
    ("hanging_towel", (1.42, 1.0, -1.05), SOUTH, (0.28, 0.55, 0.04)),
    ("cooking_pot", (1.32, 1.08, -1.33), SOUTH, (0.32, 0.17, 0.28)),
    ("plate", (-1.0, 0.78, -4.2), SOUTH, (0.22, 0.025, 0.22)),
    ("bowl_stack", (0.42, 1.85, -1.14), SOUTH, (0.15, 0.139, 0.149)),
    ("sauce_bottle", (0.68, 1.85, -1.14), SOUTH, (0.077, 0.27, 0.076)),
    ("sauce_bottle", (0.78, 1.85, -1.14), SOUTH, (0.077, 0.27, 0.076)),
    ("sauce_bottle", (0.88, 1.85, -1.14), SOUTH, (0.077, 0.27, 0.076)),
]


def on_furniture(room):
    return [piece(room, own, at, back, size) for own, at, back, size in ON_FURNITURE]


def stairwell():
    """The stairwell: its walls in storey bands with the green band at each landing, the middle wall, the ceiling, the
    landings and the six flights, the handrails, the neighbours' doors with their gates and couplets, the lamps, the
    meter cabinets, the lobby's letterboxes, notice board and exit sign, the street gate, the posters, the floor names,
    the cables and the extinguishers. Frame y from the street."""
    room = "stairwell"
    sx0, sz0, swide, sdeep = STAIRWELL_GROUND
    west, east = STAIR_LANE_A[0], sx0 + swide
    far, door = sz0, sz0 + sdeep
    top = FLAT_LEVEL + FLAT_HEIGHT
    middle_z = (far + door) / 2
    middle_x = (west + east) / 2
    found = []
    storeys = [(0.0, 3.0), (3.0, 3.0), (6.0, 3.0), (9.0, top - 9.0)]
    for bottom, tall in storeys:
        west_openings = [doorway(WEST, middle_z, FRONT_DOOR_Z, *FRONT_DOORWAY)] if bottom == FLAT_LEVEL else []
        east_openings = [doorway(EAST, middle_z, FRONT_DOOR_Z, *STREET_DOORWAY)] if bottom == 0.0 else []
        found += [wall_lining(room, west, WEST, middle_z, sdeep, bottom, tall, west_openings, near=True),
                  wall_lining(room, east, EAST, middle_z, sdeep, bottom, tall, east_openings, near=True),
                  wall_lining(room, door, SOUTH, middle_x, east - west, bottom, tall, near=True)]
    far_bands = [(0.0, 1.5, 1.2), (1.5, 3.0, 1.2), (4.5, 3.0, 1.2), (7.5, 3.0, 1.2), (10.5, top - 10.5, 0.6)]
    for bottom, tall, dado in far_bands:
        found.append(wall_lining(room, far, NORTH, middle_x, east - west, bottom, tall, dado=dado, near=True))
    run_far, run_door = far + LANDING_DEPTH, door - LANDING_DEPTH
    lane_wall = (STAIR_LANE_A[1], STAIR_LANE_B[0])
    for bottom, tall in storeys:
        for face, back in ((lane_wall[0], EAST), (lane_wall[1], WEST)):
            found.append(wall_lining(room, face, back, (run_far + run_door) / 2, run_door - run_far, bottom, tall,
                                     near=True))
    found.append(lying(room, "plaster_ceiling", (middle_x, top + 0.015, far), SOUTH, UP, (east - west, sdeep, 0.03)))
    found += landings(room, west, east, far, door)
    found += flights(room, run_far, run_door)
    found += stair_fittings(room, west, east, far, door)
    return found


def landings(room, west, east, far, door):
    """The ground floor's slab and the landings: the storeys' at the door end, the half landings at the far end."""
    middle_x = (west + east) / 2
    found = [piece(room, "landing", (middle_x, FLOOR_TOP - 0.25, (far + door) / 2), SOUTH, (east - west, 0.25, door - far),
                   near=True, foot=0.0)]
    for level in (3.0, 6.0, 9.0):
        found.append(piece(room, "landing", (middle_x, level + FLOOR_TOP - 0.25, door - LANDING_DEPTH / 2), SOUTH,
                           (east - west, 0.25, LANDING_DEPTH), near=True, foot=0.0))
    for level in (1.5, 4.5, 7.5):
        found.append(piece(room, "landing", (middle_x, level + FLOOR_TOP - 0.25, far + LANDING_DEPTH / 2), NORTH,
                           (east - west, 0.25, LANDING_DEPTH), near=True, foot=0.0))
    return found


def flights(room, run_far, run_door):
    """Six flights from the flat down to the street, switching back: the even ones down lane A away from the doors,
    the odd ones back down lane B; each rises toward its back. Their handrails on the outer walls."""
    found = []
    middle_z = (run_far + run_door) / 2
    for flight in range(round(FLAT_LEVEL / FLIGHT_RISE)):
        upper = FLAT_LEVEL - FLIGHT_RISE * flight
        foot = upper - FLIGHT_RISE + FLOOR_TOP
        lane, back, wall_x, wall_back = ((STAIR_LANE_A, SOUTH, STAIR_LANE_A[0], WEST) if flight % 2 == 0
                                         else (STAIR_LANE_B, NORTH, STAIR_LANE_B[1], EAST))
        found.append(piece(room, "stair_flight", ((lane[0] + lane[1]) / 2, foot, middle_z), back,
                           (lane[1] - lane[0], FLIGHT_RISE, run_door - run_far), near=True, foot=0.0))
        rail_x = wall_x - wall_back[0] * 0.04
        found.append(piece(room, "stair_rail", (rail_x, foot, middle_z), wall_back, (run_door - run_far, 2.45, 0.08),
                           near=True, foot=0.9))
    found.append(piece(room, "balcony_rail", ((STAIR_LANE_B[0] + STAIR_LANE_B[1]) / 2, FLAT_LEVEL + FLOOR_TOP,
                                              run_door + 0.05), SOUTH, (STAIR_LANE_B[1] - STAIR_LANE_B[0], RAIL_HEIGHT, 0.06),
                       near=True, foot=0.0))
    return found


FLOOR_NAMES = {9.0: "floor_3", 6.0: "floor_2", 3.0: "floor_1", 0.0: "floor_g"}


def stair_fittings(room, west, east, far, door):
    """What hangs and stands on the stairwell's walls and floors."""
    found = []
    for level in (6.0, 3.0):  # the neighbours' doors under the flat's, shut behind their gates
        found += [piece(room, "timber_door_frame", (west - 0.09, level + FLOOR_TOP, FRONT_DOOR_Z), WEST, (1.14, 2.28, 0.24),
                        near=True),
                  piece(room, "timber_door_leaf", (west + 0.02, level + FLOOR_TOP, FRONT_DOOR_Z), WEST, (0.94, 2.17, 0.045),
                        near=True),
                  piece(room, "security_gate", (west + 0.1, level + FLOOR_TOP, FRONT_DOOR_Z), WEST, (0.95, 2.1, 0.06),
                        near=True, foot=0.0)]
    for level in (9.0, 6.0, 3.0):  # couplets round each storey's door, its luck over it
        found += [piece(room, "wall_print", (west + LINING + 0.004, level + 0.45, FRONT_DOOR_Z - 0.68), WEST, (0.2, 1.5, 0.003),
                        print="couplet_left", near=True),
                  piece(room, "wall_print", (west + 0.15, level + 0.45, door - LINING - 0.004), SOUTH, (0.2, 1.5, 0.003),
                        print="couplet_right", near=True),
                  piece(room, "wall_print", (west + LINING + 0.004, level + 2.33, FRONT_DOOR_Z), WEST, (0.8, 0.22, 0.003),
                        print="couplet_top", near=True)]
    for level, name in FLOOR_NAMES.items():
        found.append(piece(room, "wall_print", (4.9, level + 1.55, door - LINING - 0.004), SOUTH, (0.5, 0.19, 0.002),
                           print=name, near=True))
    landing_levels = [(9.0, True), (7.5, False), (6.0, True), (4.5, False), (3.0, True), (1.5, False), (0.0, True)]
    for level, at_door in landing_levels:
        x, wall_z, back = (5.3, door, SOUTH) if at_door else (4.6, far, NORTH)
        found.append(piece(room, "cage_bulkhead", (x, level + 2.25, wall_z - back[2] * 0.08), back, (0.2, 0.2, 0.16),
                           near=True))
    for level in (9.0, 6.0, 3.0):
        found.append(piece(room, "meter_cabinet", (east - 0.09, level + 1.2, FRONT_DOOR_Z), EAST, (0.5, 0.7, 0.18),
                           near=True))
    found += [
        piece(room, "letterboxes", (3.95, 0.95, door - 0.11), SOUTH, (0.8, 0.75, 0.22), near=True),
        piece(room, "lobby_notice", (west + 0.025, 1.2, -4.2), WEST, (0.9, 0.7, 0.05), near=True),
        piece(room, "exit_sign", (east - 0.04, 2.3, FRONT_DOOR_Z), EAST, (0.36, 0.14, 0.08), near=True),
        # The street door's gate stands open outward against the block's street face (inside, the bottom flight
        # rises beside the doorway): on the street kit's rendered plates and its raised pavement
        # (earth_outside_kit.PLATE_DEEP, PAVED_TOP). Its made model's box stands 8 cm behind the spot's middle and a
        # shop's render plate is made 16 mm proud of the plan, so the spot is GATE_CLEAR out: at 3 cm the gate stood
        # 9 cm inside the plate, which the scene check read as sunk.
        piece(room, "street_gate", (east + WALL + STREET_PLATE + GATE_CLEAR, STREET_PAVED_TOP, FRONT_DOOR_Z + 1.0), WEST,
              (1.0, 2.2, 0.05), near=True, foot=0.0),
        piece(room, "wall_print", (3.95, 9.0 - 0.5, far + LINING + 0.004), NORTH, (0.75, 1.05, 0.003),
              print="poster_moon_flight", near=True),
        piece(room, "wall_print", (3.95, 4.5 + 1.0, far + LINING + 0.004), NORTH, (0.75, 1.05, 0.003),
              print="notice_residents", near=True),
        piece(room, "extinguisher", (5.75, 6.0 + FLOOR_TOP, door - 0.15), SOUTH, (0.289, 0.6, 0.186), near=True,
              foot=0.0),
        piece(room, "extinguisher", (5.75, 3.0 + FLOOR_TOP, door - 0.15), SOUTH, (0.289, 0.6, 0.186), near=True,
              foot=0.0),
        piece(room, "cable_drop", (east - 0.06, FLOOR_TOP, door - 0.12), EAST, (0.15, FLAT_LEVEL + FLAT_HEIGHT - 0.1, 0.08),
              near=True),
    ]
    for level in (7.5, 1.5):  # a fire hose cabinet on the half landings' far wall, beside the lamp
        found.append(piece(room, "fire_hose_cabinet", (5.4, level + 0.75, far + LINING + 0.1), NORTH, (0.45, 0.7, 0.2),
                           near=True))
    found += conduits(room, west, east, far)
    return found


CONDUIT = 0.05  # a conduit's bore and its clips: the hub's plain pipe, its own name `pipe_straight`


def conduits(room, west, east, far):
    """The wiring the concept's walls carry: a junction box by each storey's meter cabinet, a conduit up from the
    cabinet to the storey's ceiling and along the outside wall to the far end, and one riser up the far corner."""
    found = []
    face = east - LINING - CONDUIT / 2
    for level in (9.0, 6.0, 3.0):
        found.append(piece(room, "wiring_box", (east - LINING - 0.04, level + 1.55, FRONT_DOOR_Z - 0.55), EAST,
                           (0.18, 0.22, 0.08), near=True))
        rise = 2.75 - 1.92
        found.append(piece(room, "pipe_straight", (face, level + 1.92 + rise / 2, FRONT_DOOR_Z + 0.1 - CONDUIT / 2),
                           EAST, (rise, CONDUIT, CONDUIT), up=SOUTH, near=True))
        found.append(piece(room, "pipe_straight", (face, level + 2.75, (FRONT_DOOR_Z + far) / 2), EAST,
                           (FRONT_DOOR_Z - far - 0.3, CONDUIT, CONDUIT), up=UP, near=True))
    lane_wall = (STAIR_LANE_A[1], STAIR_LANE_B[0])
    # The middle wall's own length, between the landings (a run past it hung over the door end's landing).
    run_far, run_door = far + LANDING_DEPTH, STAIRWELL_GROUND[1] + STAIRWELL_GROUND[3] - LANDING_DEPTH
    # Along lane B's face of the middle wall under each ceiling (lane A's face and the west wall carry the flights'
    # rails, which a run would cross).
    for level in (0.0, 3.0, 6.0, 9.0):
        high = level + 2.72
        found.append(piece(room, "pipe_straight", (lane_wall[1] + LINING + CONDUIT / 2, high, (run_far + run_door) / 2),
                           WEST, (run_door - run_far - 0.2, CONDUIT, CONDUIT), up=UP, near=True))
    for level in (0.0, 3.0, 6.0, 9.0):  # a conduit drop from each run to a junction box
        for face, back, sign in ((lane_wall[1] + LINING, WEST, 1.0),):
            drop = 2.72 - 1.62
            found.append(piece(room, "pipe_straight", (face + sign * CONDUIT / 2, level + 1.62 + drop / 2,
                                                       -2.75 - CONDUIT / 2), back, (drop, CONDUIT, CONDUIT),
                               up=SOUTH if back is EAST else NORTH, near=True))
            found.append(piece(room, "wiring_box", (face + sign * 0.04, level + 1.4, -2.75), back,
                               (0.18, 0.22, 0.08), near=True))
    found += [piece(room, "wall_print", (lane_wall[1] + LINING + 0.004, 6.0 + 1.3, -3.27), WEST, (0.75, 1.05, 0.003),
                    print="poster_moon_flight", near=True),
              piece(room, "wall_print", (lane_wall[0] - LINING - 0.004, 3.0 + 1.0, -4.0), EAST, (0.75, 1.05, 0.003),
                    print="notice_residents", near=True)]
    riser = FLAT_LEVEL + FLAT_HEIGHT - 0.1
    found.append(piece(room, "pipe_straight", (west + LINING + CONDUIT / 2, riser / 2, far + LINING + 0.08 - CONDUIT / 2),
                       WEST, (riser, CONDUIT, CONDUIT), up=NORTH, near=True))
    return found


ROOMS = {"flat": flat, "stairwell": stairwell}
# The furniture the player walks round, each piece a box the game makes solid (HubKit `solid`); the walls, floors and
# stairs are EarthSite's own collision.
SOLID = ("wardrobe", "bed_frame", "table", "timber_chair", "tv_cabinet", "washbasin_stand", "kitchen_counter",
         "bedside_table", "extinguisher")


def layout(room):
    """The room's kit layout: its pieces and the kinds' groups (what a wall hangs, what a floor holds)."""
    pieces = ROOMS[room]()
    kinds = {}
    for found in pieces:
        own = found["kind"].split("_", 1)[1]
        group = "floors" if own in ("floorboards", "landing", "balcony_slab", "stair_flight") else "hangs"
        kinds.setdefault(found["kind"], dict({"group": group}, **({"solid": True} if own in SOLID else {})))
    return {"room": room, "place": PLACES[room], "origin": list(ORIGINS[room]),
            "frame": "the Earth block's: x across, z along the street, y up from the room's own floor",
            "kinds": kinds, "pieces": pieces}


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ROOMS:
        raise SystemExit(__doc__)
    found = layout(sys.argv[1])
    pathlib.Path(sys.argv[2]).write_text(json.dumps(found, indent=1))
    print(len(found["pieces"]), "pieces,", len(found["kinds"]), "kinds")


if __name__ == "__main__":
    main()
