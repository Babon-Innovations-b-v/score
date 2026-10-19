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


DETAILS = {"console_body": console_details, "station_module": lambda size: []}


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
