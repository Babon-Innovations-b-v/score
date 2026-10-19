"""The code-built bodies of big objects seen up close, in plain Python (numpy only), read by their builders
(pieces_bodies.py, in Blender) and by the bake (make_chunky.py, which keeps a take's details over a body) alike.

The owner's rule (PRD #10, 2026-10-18): a big object seen up close gets a code-built body for its clean main shapes;
the picture-made model's geometry is kept only for its details, and every finish is the shared library's. A body's
numbers are read off its take in the kit frame (the take turned and fitted to its laid size, as make_chunky lays it)
and given here as shares of the laid size (wide, tall, deep), so the body and the kept details meet at any size.

Which takes are built over a body is BODIES, by take (a take is painted and baked by one place only): its builder,
the library surfaces kept wherever they are, and the turn its take is laid with when the place's data has it wrong.
It lives here, in the bake's own declared folder, so a body re-keys only the bake: the place's data
(data/surfaces/<place>.json) is read by every row of its line, and an edit there would repaint the place. `kept`
says which of the take's faces stay: those in a kept surface, and every face standing in front of the body inside
one of its detail boxes (`detail_boxes`: the console's bays, where the model's controls sit). Everything else of the
take is the body's. The bake writes the model's surfaces as it laid them beside it (`<model>.parts`), which the bake
check and the scene's export read in place of the take's labelled parts.
"""
import numpy as np

# The takes built over a body. The console's place data lays its take unturned (base the identity), so its long side,
# the model's glTF z, went into the console's depth and its screens faced sideways (the bake of 2026-10-16): its
# turn here brings the screens to the front.
BODIES = {
    "main_console-s1": {"builder": "console_body", "keep": ["screen_amber", "indicator_amber", "led_red", "led_white"],
                        "turn": [0.0, 0.0, -1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0]},
    "first_module-r1": {"builder": "station_module", "keep": []},
    # The power core's take came out with its side canister toward -z and its box toward +z; the turn brings them to
    # the sides, the canister to +x (the viewer's left, as the concept shows it) and the box to -x.
    "power_core-s1": {"builder": "power_core", "keep": [],
                      "turn": [0.0, 0.0, -1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0]},
    # The engine room's fuel tank keeps its model's gauge, valve and top pipe fittings by place (FUEL_DETAILS).
    "fuel_tank-s1": {"builder": "fuel_tank", "keep": []},
    # The greenhouse's water tank: the place's base [0, 0, -1, 0, 1, 0, 1, 0, 0] lays its model 18.5 degrees off
    # square in plan (its stand's and boxes' least boxes, 2026-10-18); its turn here is that base turned back square.
    "water_tank-r1": {"builder": "water_tank", "keep": [],
                      "turn": [-0.3173, 0.0, -0.94832, 0.0, 1.0, 0.0, 0.94832, 0.0, -0.3173]},
    "lander-r1": {"builder": "lander_body", "keep": []},
    "kit5-rover-3": {"builder": "rover_body", "keep": []},
    "crane-r1": {"builder": "crane_body", "keep": []},
}

# The cockpit's main console (main_console-s1, laid 3.6 x 1.0 x 0.65 m), read off its take turned front to -z
# (turn [0, 0, -1, 0, 1, 0, 1, 0, 0]: the model's long side is its glTF z, its screens face -x). Depths are shares of
# the laid depth from its middle (front -0.5), heights of its height, widths of its width from its middle.
CONSOLE_SHOULDER = 0.5  # where the outline's rounded upper corners start, up its outer sides
CONSOLE_CROWN = 0.28  # the half width where the rounded corners reach the top
CONSOLE_TOP = 0.98
CONSOLE_FACE = -0.24  # the console's front face round its bays
CONSOLE_BAY_FLOOR = -0.15  # a bay's floor, where the model's screens and buttons stand in front of it
CONSOLE_BACK = 0.5
CONSOLE_UNDER = ((0.2, 0.0), (0.5, 0.25))  # the underside's slope at the back, from the foot up to the back face
CONSOLE_TOP_BACK = ((0.3, 1.0), (0.5, 0.82))  # the chamfer along the top's back edge
# The bays (x0, x1, y0, y1): the two wing screens with their control rows under them, and the middle screen.
CONSOLE_BAYS = {"left_bay": (-0.461, -0.222, 0.1, 0.68), "middle_bay": (-0.156, 0.156, 0.1, 0.76),
                "right_bay": (0.222, 0.461, 0.1, 0.68)}
# The hood over each wing's screen, the crown block over the middle (its light strip comes from the model) and the
# pillars between the bays: (x0, x1, y0, y1, front depth).
CONSOLE_HOODS = ((-0.43, -0.217, 0.68, 0.74, -0.28), (0.217, 0.43, 0.68, 0.74, -0.28))
CONSOLE_CROWN_BLOCK = (-0.172, 0.172, 0.78, 0.98, -0.44)
CONSOLE_PILLARS = ((-0.217, -0.161, 0.06, 0.78, -0.31), (0.161, 0.217, 0.06, 0.78, -0.31))
CONSOLE_KICK = (0.08, -0.34)  # the kick plinth along its foot: its height and its front depth
# A kept detail box reaches this far behind the body's face it stands on, so a control set into its bay is kept whole.
DETAIL_BEHIND = 0.004

# The old station's first module (first_module-r1, laid 6.5 x 4.308 x 3.783 m, its axis along x), read off its take
# turned with its kind's turn [0, 0, 1, 0, 1, 0, -1, 0, 0]: a straight hull where the model's wanders (its middle 2.17
# to 2.63 m up from slice to slice), its radius the clean slices' median.
MODULE_AXIS = 0.534  # the hull's axis, a share of the height
MODULE_RADIUS = 0.46  # a share of the depth (1.74 m)
MODULE_HULL = (-0.392, 0.377)  # the straight hull's ends along x, shares of the width
MODULE_SKIN = 0.008  # the hull's wall, a share of its radius (14 mm)
# The tapered ends (x shares of the width, radii shares of the radius): the aft end tapers to a berthing drum, a lip
# round its rim and a white end plate inside the lip; the front end tapers to a white bulkhead and a docking ring
# standing out of it with its white hatch inside.
MODULE_AFT = {"taper": (-0.437, 0.833), "drum": -0.469, "lip": (-0.492, 0.575), "plate": (-0.477, 0.575)}
MODULE_FORE = {"taper": (0.431, 0.718), "ring": (0.5, 0.546, 0.431), "hatch": (0.454, 0.469, 0.431)}
# The ring frames round the hull (x shares of the width; the model's grey bands peak there).
MODULE_FRAMES = (-0.392, -0.246, -0.123, 0.077, 0.346)
MODULE_FRAME = (0.012, 0.012)  # a frame's width (share of the width) and how proud it stands (share of the radius)
# The cradles under it (x shares), their half width (share of the depth) and thickness along x (share of the width);
# the rails they stand on run between MODULE_RAILS along x.
MODULE_CRADLES = (-0.315, 0.223)
MODULE_CRADLE = (0.4, 0.038, 0.035)  # half width, thickness, the foot's height (a share of the height)
MODULE_RAILS = (-0.362, 0.269)
MODULE_STAND = (-0.462, 0.4, 0.21)  # the access stand at the aft end: x, z (share of the depth), height (of height)
# The insulation blankets: the model's majority finish on its hull, in cells of 30 degrees round (from +z toward up)
# by a tenth of the straight hull along x; S silver, G gold, . bare hull (the foil torn off), o a hole through it.
MODULE_FOIL = ("SSSSSSSS.G", "SSSSooSSSG", "SSSSSSSSSS", "SSSS..SSSS", "SSSSSGSSS.", ".SSSGGGGG.",
               "..SSSSGGGG", ".....GGG.G", "....GGG..G", "....GG..GG", "...S..GG.G", "S..SSSGGGG")
MODULE_FOIL_SURFACES = {"S": "mli_silver", "G": "mli_gold"}
MODULE_FOIL_PROUD = (0.003, 0.012)  # a blanket's inside and outside, over the hull's radius (shares of the radius)

# A glowing band or a stripe stands this far proud of what it wraps (metres): laid 2 mm proud, a band reads to the
# model check as a 2 mm wall.
BAND_PROUD = 0.004

# The engine room's power core (power_core-s1, laid 1.4 x 2.3 x 1.4 m, upright), read off its take turned with its
# canister to +x (BODIES), from the concept where the take is lumpy: heights are shares of the height, radii and
# reaches shares of the width (its depth is the same). The plinth: its height, the dark top plate's thickness, the
# hazard band's height under it (the take's hazard paint from 0.02 to 0.12 m up its sides).
CORE_PLINTH = (0.0587, 0.013, (0.0065, 0.0457))
# The column from the plinth up: (from, to, radius, surface), its drums dark, its flanges steel (take: base drum 0.43
# m, flanges 0.355 m, the column 0.30 m round its middle; the concept's stepped base and paired flanges).
CORE_PROFILE = ((0.0587, 0.087, 0.3357, "dark_panel"), (0.087, 0.1565, 0.2857, "dark_panel"),
                (0.1565, 0.1739, 0.2643, "bare_steel"), (0.1739, 0.1957, 0.2357, "dark_panel"),
                (0.1957, 0.213, 0.2571, "bare_steel"), (0.213, 0.2522, 0.2357, "dark_panel"),
                (0.2522, 0.2696, 0.2571, "bare_steel"), (0.2696, 0.3043, 0.2357, "dark_panel"),
                (0.3043, 0.4304, 0.2143, "dark_panel"), (0.4304, 0.4739, 0.2036, "dark_panel"),
                (0.4739, 0.6087, 0.2143, "dark_panel"), (0.6087, 0.6261, 0.2571, "bare_steel"),
                (0.6261, 0.687, 0.2357, "dark_panel"), (0.687, 0.7043, 0.2571, "bare_steel"),
                (0.7043, 0.7478, 0.2357, "dark_panel"), (0.7478, 0.7739, 0.25, "bare_steel"),
                (0.7739, 0.7826, 0.2286, "dark_panel"))
# The amber-lit rings (from, to): two between the lower flanges, four round the column's middle band, three between
# the upper flanges and one at the hood's foot (the take's led_white bands at 0.48 to 0.57, 1.0 to 1.08 and 1.53 to
# 1.6 m; the concept's lines). Each wraps the drum its height falls on.
CORE_LAMPS = ((0.2196, 0.2283), (0.237, 0.2457), (0.437, 0.443), (0.4465, 0.4525), (0.456, 0.462),
              (0.4655, 0.4715), (0.6348, 0.6435), (0.6522, 0.6609), (0.6696, 0.6783), (0.7826, 0.7891))
# The hood on top: its foot, radius, and its top cut on a slope from the full height at +x down to its low side at -x;
# the cowl standing at its -x side (x from, x to, half its depth, from, to) and the hatch plate on its front (x from,
# x to, from, to).
CORE_HOOD = (0.7826, 0.2214, 1.0, 0.9217)
CORE_COWL = (-0.2571, -0.1571, 0.1214, 0.7913, 0.9739)
CORE_HATCH = (-0.0857, 0.0429, 0.8478, 0.913)
# The four brackets round the base, at the diagonals: their profile out from the axis (reach, height) pairs, and half
# their thickness.
CORE_BRACKET = (((0.2571, 0.0587), (0.3857, 0.0587), (0.3857, 0.087), (0.3286, 0.1435), (0.2571, 0.1435)), 0.0429)
# The coolant canister at +x: its axis' reach, radius, body (from, to), its end cones' tips and their radius, its two
# straps (heights) and the two brackets holding it to the column (heights, half their height and depth).
CORE_CANISTER = {"at": 0.3, "radius": 0.0786, "body": (0.3043, 0.5913), "tips": (0.2783, 0.6174), "tip": 0.05,
                 "straps": (0.3391, 0.5565), "brackets": (0.3913, 0.5), "bracket": (0.0109, 0.0286)}
# The pump box at -x: (outer x, inner x inside the column, half its depth, from, to), its two round pipe ports on its
# outer face (heights, radius, how far they stand) and the amber lamp on its front (x from, x to, from, to).
CORE_BOX = (-0.3143, -0.1571, 0.1071, 0.3043, 0.5652)
CORE_PORTS = ((0.4957, 0.3652), 0.0357, 0.0429)
CORE_BOX_LAMP = (-0.2857, -0.2571, 0.4, 0.4348)
# The coolant pipes (the take paints them clear_glass; the concept's are teal paint): their radius and bend radius,
# and each run's points (x reach, height) in the plane through the axis: canister top into the hood, canister foot
# down into the plinth, the hood's cowl out and down into the box's upper port, the lower port out and down into the
# plinth; and the collars where they meet the plinth (radius, height over it).
CORE_PIPE = (0.025, 0.04)
CORE_PIPES = (((0.3, 0.6141), (0.3, 0.9217), (0.2143, 0.9217)),
              ((0.3, 0.2816), (0.3, 0.2174), (0.4286, 0.2174), (0.4286, 0.0587)),
              ((-0.25, 0.9217), (-0.4286, 0.9217), (-0.4286, 0.4957), (-0.3536, 0.4957)),
              ((-0.3536, 0.3652), (-0.4286, 0.3652), (-0.4286, 0.0587)))
CORE_PIPE_COLLAR = (0.0393, 0.013)
# The notched plates on the column's front and back at the ends of its middle (the concept's chevrons): each
# (from, to, half width at its foot, half width at its top), the upper narrowing down, the lower narrowing up.
CORE_CHEVRONS = ((0.5478, 0.6, 0.0214, 0.0429), (0.313, 0.3652, 0.0429, 0.0214))
CORE_PIPE_SURFACE = "bay_one_paint"  # the library's teal paint, nearest the concept's pipes

# The engine room's fuel tank (fuel_tank-s1, laid 0.9 x 1.8 x 0.9 m, unturned), read off its take: a round upright
# tank where the model's is squashed front to back (0.86 m across, 0.74 m deep); its radius is the model's depth, its
# axis the model's middle in depth, so the model's gauge (on its +z side) and its top pipes meet the body.
FUEL_AXIS = -0.072  # the tank's axis from the middle in depth, a share of the depth (6.5 cm toward the front)
FUEL_RADIUS = 0.406  # the tank's radius, a share of the depth (0.365 m)
# The tank's outline up its axis, heights shares of the height: its lower dome's foot, the straight shell's ends, the
# top dome's crown (high enough that the model's pipes stand on it, their feet 1.56 to 1.6 m up).
FUEL_FOOT, FUEL_SHELL, FUEL_CROWN = 0.056, (0.167, 0.789), 0.922
FUEL_BANDS = ((0.239, 0.294), (0.656, 0.722))  # the two dark bands, heights shares of the height
FUEL_BAND_PROUD = 0.04  # how far a band stands out of the shell, a share of the radius (15 mm, the model's)
# The cradle: a square frame on the floor, a post at each corner up to the lower band and a bracket from each post
# to the band. Its outer half side (round the tank's axis) and its bars' side are shares of the width, the floor
# frame's height a share of the height (the model's: 0.8 m square, 5 cm bars).
FUEL_CRADLE = (0.433, 0.056, 0.025)
FUEL_DRAIN = 0.028  # the drain stub under the lower dome, its radius a share of the width
# Where the tank keeps its model's details (x0, x1, y0, y1, z0, z1; shares of width, height, depth from the middle):
# the gauge and valve on its +z side, from just outside the model's shell (0.302 m) out, and the pipe fittings on
# its top dome, from 1.585 m up (the model's dome under them lies inside the body's). FUEL_DETAIL_SURFACES is the
# surface the current take paints most in each (sampled points: gauge 484 of 486 perforated_steel; fittings 984
# perforated_steel, 849 hull_white_gloss, that white the model's dome, buried in the body's).
FUEL_DETAILS = {"gauge": (-0.067, 0.111, 0.389, 0.544, 0.34, 0.511),
                "fittings": (-0.3, 0.367, 0.881, 1.006, -0.178, 0.233)}
FUEL_DETAIL_SURFACES = {"gauge": "perforated_steel", "fittings": "perforated_steel"}

# The greenhouse's water tank (water_tank-r1, laid 1.6 m each way), read off its take turned square (its BODIES turn):
# a cream tank of two stacked boxes on a steel stand. Half sides are shares of the width (the tank is square in plan),
# heights shares of the height.
WATER_LEGS = (0.481, 0.0625)  # the stand's legs: their outer half side and their side
WATER_APRON = (0.281, 0.35, 0.075)  # the stand's top frame: its foot, its top, its beams' width (under the tank's edge)
WATER_LOWER = (0.35, 0.6375, 0.419)  # the lower box: foot, top, half side
WATER_LIP = (0.625, 0.6875, 0.45)  # the lip between the boxes: foot, top, half side
WATER_UPPER = (0.6875, 1.0, 0.406)  # the upper box: foot, top (the rim), half side
WATER_RIM = (0.975, 0.4125)  # the rim's band round the upper box's top: its foot and half side
WATER_WALL = 0.031  # the upper box's wall round its open top (5 cm)
WATER_LEVEL = 0.9  # the water's face, a share of the height (1.44 m, the model's)
# The overflow box in the rim's back corner on the -x side (the right seen from in front, as in the picture and the
# take): x0, x1, z0, z1.
WATER_OVERFLOW = (-0.375, -0.263, 0.275, 0.375)
# The steel plate low on the lower box's front at that same end (the picture's and the take's): x0, x1, y0, y1.
WATER_PLATE = (-0.375, -0.28, 0.375, 0.49)

# The campgrounds' landed lander (lander-r1, laid 8.649 x 19.0 x 10.597 m), read off its take laid with its place's
# base turn (its hull then still stands about 14 degrees round from square, its fins on a skewed line; the body
# stands square, fins across x, door to the front) and off its concept picture. Its whole take is one surface,
# stainless, lumpy everywhere: the body keeps none of it. Widths and radii are shares of the laid width, heights of
# the height, depths of the depth.
LANDER_AXIS = 0.059  # the hull's axis behind the middle, a share of the depth (0.62 m: the circle fits' median)
LANDER_RADIUS = 0.236  # the hull's radius (2.04 m: the circle fits from 2.5 to 14 m up)
LANDER_FOOT = 0.108  # the hull's flat bottom (2.05 m, where the take's bottom disc lies)
LANDER_SHOULDER = 0.763  # where the ogive nose starts (14.5 m); the take's slices fit a tangent ogive within 5 cm
LANDER_NOSE_STEPS = 16  # points along the ogive's profile
# The weld seams round the hull (its concept's lines a metre apart): first and last height (of height) and how many,
# then one seam's height (of height, 2 cm) and how proud it stands (of radius, 6 mm).
LANDER_SEAMS = (0.263, 0.737, 10)
LANDER_SEAM = (0.001, 0.003)
# The two aft fins, flat across x either side: root heights along the hull and the outer edge's heights at the laid
# width's edge (the take's 2.2 to 5.4 m, its slanted top edge back to the hull at 9.3 m), and thickness (of depth).
LANDER_AFT_FIN = {"root": (0.116, 0.489), "edge": (0.116, 0.284), "thick": 0.016}
# The two forward flaps on the nose, across x: root heights along the nose (14.4 to 17.4 m, the concept's), the outer
# edge's heights (14.6 to 15.9 m), how far out from the axis (of width, 3.2 m: the take's 3.1 to 3.5) and thickness.
LANDER_FORE_FLAP = {"root": (0.758, 0.916), "edge": (0.768, 0.837), "reach": 0.37, "thick": 0.013}
# The four legs at the diagonals between the fins (the take has three and the ramp, the concept four): each a main
# strut from the hull's side and a lower strut from its bottom edge, splayed out to a round pad.
LANDER_LEG_ANGLES = (45.0, 135.0, 225.0, 315.0)  # round from +x toward +z, degrees
LANDER_LEG_REACH = 0.4625  # a pad's middle from the axis (4.0 m: the take's pads 3.8 m out)
LANDER_LEG_TOP = 0.242  # where the main strut meets the hull (4.6 m, the take's)
LANDER_STRUTS = (0.015, 0.0104)  # the main and lower struts' radii (0.13 and 0.09 m)
# A pad: its radius (of width, 0.55 m: the take's discs), its thickness and its hub's top (of height, 0.12 and
# 0.35 m), the hub's radius (of width, 0.18 m).
LANDER_PAD = {"radius": 0.064, "thick": 0.0063, "hub_top": 0.0184, "hub": 0.021}
# The three engine bells under the hull (the concept's; the take's rings under its bottom): how far out from the axis
# (of width, 0.8 m), their angles, exit and throat radii (of width, 0.38 and 0.2 m), their mouths' height (of height,
# 1.25 m) and their wall (of width, 3 cm).
LANDER_BELLS = {"out": 0.0925, "angles": (90.0, 210.0, 330.0), "exit": 0.044, "throat": 0.023, "mouth": 0.066,
                "wall": 0.0035}
# The cargo door at its foot, to the front: its half width (of width, 0.75 m), sill and top (of height, 2.25 and
# 4.05 m: the concept's door just over the hull's bottom), the bay's back wall in front of the axis (of radius,
# 0.5 m) and its lining's thickness (of width, 3 cm).
LANDER_DOOR = {"half": 0.0867, "sill": 0.118, "top": 0.213, "back": 0.245, "lining": 0.0035}
LANDER_DOOR_RIBS = 4  # the upright ribs on the bay's back wall (the concept's ribbed bay)
# The ramp from the sill down to the ground at the laid box's front: half width (of width, 0.68 m), deck thickness
# (of height, 0.1 m), its tread ribs and their width and height (of height, 4 and 3 cm), its edge rails' width (of
# width, 6 cm) and height (of height, 6 cm).
LANDER_RAMP = {"half": 0.0786, "thick": 0.0053, "ribs": 14, "rib": (0.0021, 0.0016), "rail": (0.0069, 0.0032)}
# The two pipes along its side (the concept's pair over the door, set round toward +x so the decal stencil's flat
# spot at [0, 7.5] stays clear): their angle from the front toward +x, the gap between them (of width, 0.27 m), their
# radius and how far their middles stand off the hull (of width, 6 and 12 cm), their low and high ends (of height,
# 4.9 and 11.3 m) and how many brackets hold them.
LANDER_PIPES = {"angle": 35.0, "gap": 0.031, "radius": 0.0069, "standoff": 0.0139, "ends": (0.258, 0.595),
                "brackets": 3}
# The flat stencil panel the decal (stencil_spacexcitement, 1.2 x 0.3 m at [0, 7.5]) is laid on: the hull cut flat
# across its front out to this x either side (of width, 0.62 m) between these heights (of height, 7.15 to 7.85 m).
LANDER_PANEL = (0.0717, 0.376, 0.413)

# The garage's open two-seat rover (kit5-rover-3, laid 1.72 x 1.66 x 3.03 m, unturned), read off its take: x shares
# of the width from its middle, y of the height from its foot, z of the depth from its middle. Its take is laid with
# its nose toward +z (the battery box and the front wheels at +z, the cargo tray at -z), as the garage places it, so
# its numbers keep that. Every tyre is one size, the shares of the height of its middle and its radius.
ROVER_WHEEL = (0.235, 0.232)  # the wheels' middle above the foot and the tyre's radius (0.39 m, 0.385 m)
ROVER_AXLES = (0.343, -0.231)  # the front and rear axles along z (the tyres' middles, both sides averaged)
ROVER_TYRE = (0.5, 0.157)  # a tyre's outer face and its width, shares of the width (out to the laid side)
ROVER_TYRE_CARCASS = 0.955  # the tyre's smooth carcass under its lugs, a share of its radius
ROVER_RIM = (0.61, 0.56)  # the rim's outer and inner radius, shares of the tyre's radius (the take's spoked rims)
ROVER_HUB = (0.15, 0.05)  # the hub's radius (of the tyre's radius) and how far inside the tyre's face it ends (of width)
ROVER_SPOKES = 16  # the wire spokes round a rim (the concept's spoked wheels)
ROVER_LUGS = 28  # the tread lugs round each of a tyre's two rows (the concept's big knobbly tyres)
ROVER_FRAME = (0.302, 0.0145)  # the frame's side rails out from the middle and a tube's radius, shares of the width
ROVER_FLOOR = (0.253, 0.0075, -0.205, 0.396)  # the floor pan's height, its thickness, and its ends along z
# The tube frame's side, as (z, y) points along each side rail: the lower rail along the floor that steps up to the
# cargo tray's foot, and the upper rail rising from the front bumper to the tray's top front corner.
ROVER_LOWER_RAIL = ((0.396, 0.253), (-0.205, 0.253), (-0.281, 0.41), (-0.488, 0.41))
ROVER_UPPER_RAIL = ((0.396, 0.373), (-0.281, 0.59), (-0.488, 0.59))
ROVER_POSTS = ((0.396, 0.253, 0.373), (-0.281, 0.41, 0.59), (-0.384, 0.41, 0.59), (-0.488, 0.41, 0.59))  # z, y0, y1
# The tubes across the frame (z, y): the bumper and the floor's cross members, the tray's foot and top at both ends.
ROVER_CROSS = ((0.396, 0.253), (0.396, 0.373), (0.079, 0.253), (-0.205, 0.253), (-0.281, 0.41), (-0.281, 0.59),
               (-0.488, 0.41), (-0.488, 0.59))
ROVER_TRAY = (-0.488, -0.281, 0.41, 0.006)  # the cargo tray's floor: from, to along z, its height, its thickness
ROVER_FITTING = 0.022  # the cast corner fittings at the tray's eight corners, their half size (a share of the width)
# The battery box at the front (x0, x1, y0, y1, z0, z1) on its carrier plate, its grille on its front face.
ROVER_BATTERY = (-0.174, 0.087, 0.393, 0.59, 0.281, 0.389)
ROVER_CARRIER = (0.386, 0.271, 0.403)  # the carrier plate's height and its ends along z (across the frame)
ROVER_GRILLE = (0.15, 0.2)  # the grille's inset from the box's sides and its top and foot (shares of the box)
# The console box ahead of the seats: its sides along x and its profile from the side as (z, y) points, the face
# toward the seats (where the take's screens are) upright, the top running forward and sloping down to its front.
# (A centimetre outside the take's shell all round but its seat-side face, so the take's own shell stays inside.)
ROVER_CONSOLE_SIDES = (-0.198, 0.148)
ROVER_CONSOLE_PROFILE = ((0.0776, 0.253), (0.0776, 0.774), (0.121, 0.774), (0.245, 0.578), (0.245, 0.253))
ROVER_MAST = (-0.249, -0.348, 0.416, 0.873, 0.007)  # the antenna mast's pole: x, z, from the tray floor up, radius
# The seats' risers on the floor under the take's two seats (x from, x to; z from, z to; their top).
ROVER_RISERS = ((0.052, 0.180), (-0.248, -0.099), 0.458)
# The white mudguards over each tyre: their inside radius and thickness (shares of the height), their first and
# last angle (degrees from +z, the nose, toward up), and their inner and outer side (shares of the width).
ROVER_MUDGUARD = (0.283, 0.009, 20.0, 160.0, 0.334, 0.502)
# Where the rover keeps its take's details (x0, x1, y0, y1, z0, z1, shares): the seats, the console's screens and
# switches, the antenna mast with its dish behind the seats, the lamp beside the console, the whip on the battery box
# and the box on the tray; each with the surface the take paints most inside it (kept by place, never by name).
ROVER_DETAILS = {"seats": (-0.244, 0.244, 0.446, 0.819, -0.284, -0.059),
                 "console": (-0.204, 0.151, 0.446, 0.873, 0.036, 0.251),
                 "mast": (-0.36, -0.163, 0.801, 1.0, -0.409, -0.33),
                 "lamp": (-0.372, -0.233, 0.482, 1.0, 0.017, 0.112),
                 "whip": (-0.244, -0.192, 0.59, 0.783, 0.363, 0.396),
                 "tray_box": (-0.14, 0.209, 0.422, 0.53, -0.363, -0.264)}
ROVER_DETAIL_SURFACES = {"seats": "plastic_grey", "console": "enamel_white", "mast": "bare_steel",
                         "lamp": "bare_steel", "whip": "bare_steel", "tray_box": "plastic_grey"}

# The campgrounds' small cargo crane (crane-r1, laid 1.811 x 3.2 x 1.065 m, turned by its base [0.4131, 0, -0.91069,
# 0, 1, 0, 0.91069, 0, 0.4131] as the place lays it). Its arm stands in one upright plane that runs across the laid
# box at a slant, so its numbers are read in that plane (along it, toward the boom's tip; across it; up) and the
# body is built there and turned into the laid frame; they are shares of the height alone (the take was fitted
# about evenly on every axis), from the slewing base's middle.
CRANE_HEADING = 27.4  # the arm's plane, degrees from the kit's +x turned toward -z (the take's points' main line)
CRANE_MIDDLE = (0.009, -0.0125)  # the slewing base's middle along and across the arm's plane from the laid middle
CRANE_LEGS = (-10.0, 4)  # the first outrigger's angle from along the arm (degrees, toward across) and how many
CRANE_LEG_BEAM = (0.056, 0.084, 0.0125, 0.062)  # a leg's beam: its foot and top, half width, where it starts out
CRANE_JACK = (0.17, 0.014, 0.0125, 0.103)  # the jack at a leg's end: how far out, half width, its foot and top
CRANE_PAD = (0.019, 0.0037, 0.011)  # a foot pad's half size, its rubber sole's top and its steel plate's top
CRANE_GEAR = (0.069, 0.009, 0.047, 24)  # the geared drum under the hub: radius, foot, top, its teeth round it
CRANE_HUB = (0.094, 0.047, 0.094)  # the six-sided hub the legs come out of: corner radius, foot, top
CRANE_DRUM = (0.069, 0.094, 0.156, 0.073, 0.009)  # the slewing drum: radius, foot, top; its lip's radius and depth
CRANE_COLUMN = (-0.041, 0.047, 0.031, 0.156, 0.2125)  # the block on the drum: along from, to, half across, foot, top
CRANE_ARM_ACROSS = -0.0094  # the arm's middle across its plane (the post, boom and knuckle stand on it)
CRANE_POST = ((0.006, 0.194), (-0.281, 0.359), 0.056, 0.044)  # the post: its root, the elbow, depth, width
CRANE_KNUCKLE = (0.034, 0.047)  # the knuckle at the elbow: its radius and width across
# The boom from the elbow to its tip, in two parts: the base part's depth and width, the fly part's depth and width,
# where the fly part comes out of the base part (a share of the boom's length) and the collar round the joint.
CRANE_BOOM_TIP = (0.266, 0.9625)
CRANE_BOOM = (0.066, 0.041, 0.047, 0.031, 0.58)
CRANE_COLLAR = (0.025, 0.012)  # the collar's length along the boom and how far it stands out of the base part
# The lifting ram beside the post: its foot and its head (under the boom), how far across from the arm's middle,
# its barrel's and rod's radius, and how much of its length is barrel.
CRANE_RAM = ((0.006, 0.169), (-0.154, 0.452), -0.0453, 0.0125, 0.0069, 0.55)
# The extension ram along the boom's top (stainless in the take): where it starts and ends along the boom (shares of
# its length), its radius and how far its axis stands over the boom's top.
CRANE_TOP_RAM = (0.15, 0.93, 0.0069, 0.012)
CRANE_WINCH = (-0.031, 0.225, 0.034, 0.022, 0.053)  # the winch drum on the post's side: along, up, radius, b from, to
# The hook: the sheave at the tip (radius, width), the cable's drop below the tip, the block (radius, width) and
# the hook's radius under it.
CRANE_SHEAVE = (0.021, 0.022)
CRANE_HOOK = (0.15, 0.016, 0.019, 0.013)


def console_outline(size, segments=12):
    """The console seen from in front: its foot, its sides up to the shoulder, the rounded upper corners and its top,
    as (x, y) points round it."""
    wide, tall, _ = size
    half = wide / 2
    shoulder, top, crown = CONSOLE_SHOULDER * tall, CONSOLE_TOP * tall, CONSOLE_CROWN * wide
    corner = [(crown + (half - crown) * np.cos(angle), shoulder + (top - shoulder) * np.sin(angle))
              for angle in np.linspace(0.0, np.pi / 2, segments)]
    right = [(half, 0.0)] + corner
    left = [(-x, y) for x, y in reversed(right)]
    return [(float(x), float(y)) for x, y in right + left]


def console_bays(size):
    """The console's bays as boxes in the kit frame: {name: (low corner, high corner)}, from in front of the face to
    the bay's floor."""
    wide, tall, deep = size
    return {name: ((x0 * wide, y0 * tall, CONSOLE_FACE * deep - deep), (x1 * wide, y1 * tall, CONSOLE_BAY_FLOOR * deep))
            for name, (x0, x1, y0, y1) in CONSOLE_BAYS.items()}


def console_details(size):
    """Where the console keeps its model's details: its bays down to their floors, and the crown's front (its light
    strip), each reaching DETAIL_BEHIND behind the face it stands on."""
    wide, tall, deep = size
    boxes = [(low, (high[0], high[1], high[2] + DETAIL_BEHIND)) for low, high in console_bays(size).values()]
    x0, x1, y0, y1, front = CONSOLE_CROWN_BLOCK
    boxes.append(((x0 * wide, y0 * tall, -deep), (x1 * wide, y1 * tall, front * deep + DETAIL_BEHIND)))
    return boxes


def fuel_details(size):
    """Where the fuel tank keeps its model's details: its gauge and valve, and its top pipe fittings, as boxes in the
    kit frame."""
    wide, tall, deep = size
    return [((x0 * wide, y0 * tall, z0 * deep), (x1 * wide, y1 * tall, z1 * deep))
            for x0, x1, y0, y1, z0, z1 in FUEL_DETAILS.values()]


def lander_profile(size):
    """The lander's hull seen from its side, about its axis: (radius, height) from the middle of its flat bottom out
    to its side, up to the shoulder, then the tangent ogive closing to a point at the top."""
    wide, tall, _ = size
    radius, foot, shoulder = LANDER_RADIUS * wide, LANDER_FOOT * tall, LANDER_SHOULDER * tall
    length = tall - shoulder
    bend = (radius ** 2 + length ** 2) / (2 * radius)
    nose = [(float(np.sqrt(bend ** 2 - (step / LANDER_NOSE_STEPS * length) ** 2) + radius - bend),
             float(shoulder + step / LANDER_NOSE_STEPS * length)) for step in range(1, LANDER_NOSE_STEPS)]
    return [(0.0, foot), (radius, foot), (radius, shoulder)] + nose + [(0.0, float(tall))]


def lander_radius_at(size, height):
    """The hull's radius at a height, read off its profile."""
    profile = lander_profile(size)[1:]
    return float(np.interp(height, [up for _, up in profile], [out for out, _ in profile]))


def rover_details(size):
    """Where the rover keeps its take's details (ROVER_DETAILS) as boxes in the kit frame."""
    wide, tall, deep = size
    return [((x0 * wide, y0 * tall, z0 * deep), (x1 * wide, y1 * tall, z1 * deep))
            for x0, x1, y0, y1, z0, z1 in ROVER_DETAILS.values()]


DETAILS = {"console_body": console_details, "station_module": lambda size: [], "power_core": lambda size: [],
           "fuel_tank": fuel_details, "water_tank": lambda size: [], "lander_body": lambda size: [],
           "rover_body": rover_details, "crane_body": lambda size: []}


def body_of(take):
    """The body a take is built over (BODIES), or None."""
    return BODIES.get(take)


def laid_turn(take, base):
    """The turn a take is laid into the kit frame with: its body's own when BODIES gives one, else the entry's."""
    return BODIES.get(take, {}).get("turn", base)


def detail_boxes(builder, size):
    """The boxes (low, high corners in the kit frame) where a body keeps its take's faces whatever their surface."""
    return DETAILS[builder](size)


def kept(builder, size, middles, surfaces, keep):
    """Which of a take's faces stay over its body: each face's middle in the kit frame (N x 3) and its surface name;
    kept when its surface is one of `keep`, or its middle lies in one of the body's detail boxes."""
    middles = np.asarray(middles, dtype=float).reshape(-1, 3)
    found = np.isin(np.asarray(surfaces), list(keep))
    for low, high in detail_boxes(builder, size):
        found |= np.all((middles >= np.asarray(low)) & (middles <= np.asarray(high)), axis=1)
    return found


def module_foil(size):
    """The module's blankets: (surface, first angle, last angle in degrees from +z toward up, x from, x to), each run of
    one finish along a row of MODULE_FOIL joined into one blanket."""
    wide = size[0]
    start, end = MODULE_HULL[0] * wide, MODULE_HULL[1] * wide
    step = (end - start) / len(MODULE_FOIL[0])
    found = []
    for row, cells in enumerate(MODULE_FOIL):
        column = 0
        while column < len(cells):
            letter = cells[column]
            run = column
            while run < len(cells) and cells[run] == letter:
                run += 1
            if letter in MODULE_FOIL_SURFACES:
                found.append((MODULE_FOIL_SURFACES[letter], row * 30.0, row * 30.0 + 30.0,
                              start + column * step, start + run * step))
            column = run
    return found


def module_holes(size):
    """The holes through the module's hull, where the model has no hull at all: (first angle, last angle, x from, x
    to), each run of `o` along a row of MODULE_FOIL."""
    wide = size[0]
    start, end = MODULE_HULL[0] * wide, MODULE_HULL[1] * wide
    step = (end - start) / len(MODULE_FOIL[0])
    found = []
    for row, cells in enumerate(MODULE_FOIL):
        columns = [index for index, letter in enumerate(cells) if letter == "o"]
        if columns:
            found.append((row * 30.0, row * 30.0 + 30.0, start + columns[0] * step, start + (columns[-1] + 1) * step))
    return found
