"""The crew's colours, painted after the owner's drawing of them (#100): every small part takes one
flat colour picked from the drawing, and the parts that carry a pattern are painted texel by
texel by rules placed on the body: the work suit's grey yokes and red piping, the zip line, the
flag on the pocket's flap and on the space suit's chest, and the lines of the nose and mouth.

A painter takes a part split along its texture seams (`dress.split_part`: points, faces, uv,
normals, and each point's source point on the unsplit part) and gives back its picture as bytes.
"""
import json

import fit
from person import WHO
import numpy as np
import texels
from paths import FACE
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.spatial import cKDTree

# The work suit's palette, lit side, picked from the drawing (medians of patches).
NAVY = (50, 57, 78)
GREY = (138, 136, 132)
RED = (178, 58, 44)
FLAG = (184, 48, 38)
STAR = (246, 206, 92)
BLACK = (30, 31, 34)
BOOT = (32, 34, 34)
STEEL = (150, 152, 156)
SKIN = WHO["skin"]
HAIR = WHO["hair"]
BROW = WHO["brow"]
IRIS = WHO["iris"]
EYE_WHITE = (232, 228, 218)
WORK_FLAT = {"work_belt": BLACK, "work_buckle": STEEL, "work_boot_Left": BOOT,
             "work_boot_Right": BOOT, "work_collar": NAVY, "work_lining": NAVY,
             "skin_hands": SKIN, "eyes": EYE_WHITE, "irises": IRIS, "eyebrows": BROW,
             "glasses": (58, 58, 62)}
# The American indoor suit's flat parts (#112): a fabric belt in the darker blue, white sneakers.
SNEAKER = (226, 224, 218)
WORK_FLAT_AMERICAN = dict(WORK_FLAT, work_belt=(92, 124, 160), work_boot_Left=SNEAKER,
                          work_boot_Right=SNEAKER, work_collar=(128, 164, 198),
                          work_lining=(128, 164, 198))

# The space suit's, the same way. A part takes the colour of the first name it starts with.
WHITE = (228, 224, 212)
PACK = (220, 216, 202)
LIGHT_GREY = (190, 192, 186)
PAD = (150, 155, 148)
STRAP = (150, 154, 150)
RING = (132, 134, 132)
MITT = (118, 120, 118)
MOON_BOOT = (140, 141, 137)
KNOB = (70, 72, 74)
SUIT_RED = (200, 58, 40)
GOLD = (228, 174, 40)
VISOR = (14, 14, 18)
LAMP = (205, 72, 50)
SUIT_FLAT = [("band_green", (58, 128, 64)), ("band_red", SUIT_RED), ("band_gold", GOLD), ("knee_pad", PAD), ("elbow_pad", PAD),
             ("wrist_ring", RING), ("mitt", MITT), ("boot", MOON_BOOT), ("strap", STRAP),
             ("belt", STRAP), ("waist_light", LAMP), ("waist_box", LIGHT_GREY),
             ("chest_knobs", KNOB), ("chest_box", LIGHT_GREY), ("pack", PACK),
             ("visor_rim", GOLD), ("visor", VISOR), ("helmet", WHITE), ("neck_ring", LIGHT_GREY),
             ("cloth", WHITE)]

# The hair's highlight, where the drawing's hair catches the light: one flat lighter shape where
# the hair faces this way (up, forward and to his left), inside this much of a turn.
HAIR_SHINE = WHO["hair_shine"]
HAIR_SHINE_TOWARD = (0.35, 0.75, 0.55)
HAIR_SHINE_WITHIN = 0.93
HAIR_SHINE_SMOOTHING = 40
HAIR_PICTURE = 512
# The one-piece's picture, across, before supersampling; the smaller parts' pictures.
CLOTH_PICTURE = 2048
PLACKET_PICTURE = 1024
POCKET_PICTURE = 512
HEAD_PICTURE = 1024
# Piping and the yokes, in metres on the bind pose (+x the body's left).
PIPING = 0.007
# Front yoke: a line from beside the collar down to the front of the armpit; grey on its outer side.
# Both yokes were drawn a little smaller than the first take had them (the owner's notes, #100).
FRONT_YOKE = (fit.xy(0.090, 1.478), fit.xy(0.195, 1.350))
# Back yoke: from beside the collar down to the arm at the height of the back's cross seam.
BACK_YOKE = (fit.xy(0.085, 1.470), fit.xy(0.205, 1.330))
BACK_SEAM_Y = float(fit.y(1.330))
BACK_SEAM_TOP = float(fit.y(1.47))
# The sleeve is grey down to this far along the arm from the shoulder joint.
SLEEVE_CAP = 0.062 * fit.arm_share()
# The trouser legs' piping stops under the waist.
WAIST_TOP = float(fit.y(1.085))
# The patch on the outside of each upper sleeve: how far down the arm from the shoulder joint it
# starts, how long it is, its half width round the arm, and its two white stripes as shares of
# its length.
PATCH_START = 0.085 * fit.arm_share()
PATCH_LENGTH = 0.075 * fit.arm_share()
PATCH_HALF = 0.024
PATCH_STRIPES = ((0.30, 0.44), (0.56, 0.70))
PATCH_WHITE = (232, 228, 218)
# The two welt pockets on the seat: their height, their span out from the middle, how tall the
# slit is, and its colour, a darker navy.
SEAT_POCKET_Y = float(fit.y(0.955))
SEAT_POCKET_SPAN = (float(fit.x(0.045, 0.955)), float(fit.x(0.140, 0.955)))
SEAT_POCKET_TALL = 0.006
SLIT = (26, 30, 42)
# The zip line's piping: how far in from each long edge the red starts.
PLACKET_RED = 0.006
# The star on the pocket's flag: its middle and its outer radius, in metres on the bind pose.
POCKET_STAR = (*fit.xy(0.058, 1.327), 0.016)
# The face: which drawn lines are kept (pixel boxes round the nose, and the mouth and chin), how
# dark a pixel must be to count, the smallest speck kept, how far a texel may face away from the
# front and how far behind the front-most surface it may sit and still take a line.
LINE = WHO["line"]
KEEP = [(466, 603, 564, 655), (410, 690, 612, 782)]
DARK = 95
LEAST_SPECK = 25
FACING = 0.05
DEPTH_SLACK = 0.006


def texel_places(part, size):
    """The part rasterised at `size` times the supersampling: which texels are on it, and each
    one's point, normal and triangle."""
    owner, shares = texels.rasterise(part["uv"], part["faces"], size * texels.SUPERSAMPLE)
    on = owner >= 0
    points = texels.at_texels(part["points"], part["faces"], owner, shares)[on]
    normals = texels.at_texels(part["normals"], part["faces"], owner, shares)[on]
    normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-9)
    return on, owner, shares, points, normals


def picture_of(on, colours):
    picture = np.zeros(on.shape + (3,))
    picture[on] = colours
    return texels.finished(picture, on)


def tangential(gradient, normals):
    """How fast a field changes along the surface, from its gradient in space."""
    along = gradient - (gradient * normals).sum(axis=-1, keepdims=True) * normals
    return np.maximum(np.linalg.norm(along, axis=-1), 0.25)


def line_side(front_view, line):
    """Signed distance in the front view from a yoke line, positive on its outer (upper) side,
    and the line's outward normal."""
    (start_x, start_y), (end_x, end_y) = line
    direction = np.array([end_x - start_x, end_y - start_y])
    normal = np.array([-direction[1], direction[0]]) / np.linalg.norm(direction)
    if normal[0] < 0:
        normal = -normal
    return (front_view - np.array([start_x, start_y])) @ normal, normal


def along_chain(points, joints, names):
    """For each point: how far along a chain of joints it is from the first, the chain's
    direction there, and the nearest point on the chain."""
    places = [joints[name] for name in names]
    best = np.full(len(points), np.inf)
    distance_along = np.zeros(len(points))
    axis_out = np.zeros((len(points), 3))
    foot_out = np.zeros((len(points), 3))
    start = 0.0
    for first, second in zip(places[:-1], places[1:]):
        length = np.linalg.norm(second - first)
        axis = (second - first) / length
        reach = np.clip((points - first) @ axis, 0, length)
        foot = first + reach[:, None] * axis
        distance = np.linalg.norm(points - foot, axis=1)
        closer = distance < best
        best[closer] = distance[closer]
        distance_along[closer] = start + reach[closer]
        axis_out[closer] = axis
        foot_out[closer] = foot[closer]
        start += length
    return distance_along, axis_out, foot_out


def outer_line(points, normals, joints, chain, side_sign):
    """How far along a limb each point is, and its distance round the limb from the line down
    its outside (the side facing away from the body in a front view); inf on the inner half."""
    distance_along, axis, foot = along_chain(points, joints, chain)
    lateral = np.array([side_sign, 0.0, 0.0])
    outward = lateral - (axis @ lateral)[:, None] * axis
    outward /= np.linalg.norm(outward, axis=1, keepdims=True)
    across = np.cross(axis, outward)
    radial = points - foot
    distance = (radial * across).sum(axis=1) / tangential(across, normals)
    distance[(radial * outward).sum(axis=1) <= 0] = np.inf
    return distance_along, distance


def panel_of_each_texel(part, panels, owner, on):
    """Each texel's pattern panel: the panel most of its triangle's corners carry."""
    corner_panels = panels[part["source"]][part["faces"]]
    face_panel = np.where(corner_panels[:, 1] == corner_panels[:, 2], corner_panels[:, 1],
                          corner_panels[:, 0])
    return face_panel[owner[on]].astype(str)


def work_cloth(part, panels, joints):
    """The one-piece: navy, grey yokes front and back and grey sleeve caps, red piping on the
    yoke lines, across and up the back yoke, and down the outside of each arm and each leg."""
    on, owner, _, points, normals = texel_places(part, CLOTH_PICTURE)
    panel = panel_of_each_texel(part, panels, owner, on)
    x_side = np.abs(points[:, 0])
    sign = np.sign(points[:, 0])
    front = (np.char.find(panel, "ftorso") >= 0) | (np.char.find(panel, "collar_front") >= 0)
    back = (np.char.find(panel, "btorso") >= 0) | (np.char.find(panel, "collar_back") >= 0)
    sleeve_all = np.char.find(panel, "sleeve") >= 0
    sleeve = sleeve_all & (np.char.find(panel, "cuff") < 0)
    leg = np.char.startswith(panel, "pant")
    colour = np.tile(np.array(NAVY, float), (len(points), 1))
    red = np.zeros(len(points), bool)
    patches = []
    front_view = np.stack([x_side, points[:, 1]], axis=1)
    for mask, line in ((front, FRONT_YOKE), (back, BACK_YOKE)):
        distance, normal = line_side(front_view, line)
        gradient = np.stack([normal[0] * sign, np.full(len(points), normal[1]), np.zeros(len(points))], axis=1)
        across_the_line = distance / tangential(gradient, normals)
        colour[mask & (distance > 0) & (points[:, 1] > line[1][1] - 0.03)] = GREY
        red |= (mask & (np.abs(across_the_line) < PIPING / 2) & (points[:, 1] < line[0][1] + 0.02)
                & (points[:, 1] > line[1][1] - 0.012))
    for side, sign_value in (("Left", 1.0), ("Right", -1.0)):
        mine = np.where(sleeve_all & (sign == sign_value))[0]
        along, outside = outer_line(points[mine], normals[mine], joints,
                                    (f"{side}Arm", f"{side}ForeArm", f"{side}Hand"), sign_value)
        colour[mine[(along < SLEEVE_CAP) & sleeve[mine]]] = GREY
        red[mine[(np.abs(outside) < PIPING / 2) & (along >= SLEEVE_CAP - 0.004) & sleeve[mine]]] = True
        patches.append((mine, along, outside))
        mine = np.where(leg & (sign == sign_value))[0]
        _, outside = outer_line(points[mine], normals[mine], joints,
                                (f"{side}Leg", f"{side}Shin", f"{side}Foot"), sign_value)
        red[mine[(np.abs(outside) < PIPING / 2) & (points[mine, 1] < WAIST_TOP - 0.01)]] = True
    # The back: a cross seam between the yokes and a centre seam up from it to the collar.
    inside_back = back & ~(colour == GREY).all(axis=1)
    upward = np.tile([0.0, 1.0, 0.0], (len(points), 1))
    red |= inside_back & (np.abs((points[:, 1] - BACK_SEAM_Y) / tangential(upward, normals)) < PIPING / 2)
    sideways = np.tile([1.0, 0.0, 0.0], (len(points), 1))
    red |= (back & (np.abs(points[:, 0] / tangential(sideways, normals)) < PIPING / 2)
            & (points[:, 1] > BACK_SEAM_Y) & (points[:, 1] < BACK_SEAM_TOP))
    colour[red] = RED
    for (mine, along, outside), side in zip(patches, ("Left", "Right")):
        if side == "Left" and WHO["botanist"]:
            botanist_band(colour, mine, along, outside)
        else:
            arm_patch(colour, mine, along, outside)
    seat_pockets(colour, np.char.startswith(panel, "pant_b"), points, normals)
    return picture_of(on, colour)


# The botanist's sleeve (#112, Nev): a green band round the left upper arm where take C has his
# red patch, and under it, on the outside of the arm, a green square patch with a pale leaf.
BOTANIST = (58, 128, 64)
LEAF = (170, 214, 120)
LEAF_VEIN = (40, 92, 46)
BAND_LENGTH = 0.030
LEAF_PATCH = (0.012, 0.042, 0.021)


def botanist_band(colour, mine, along, outside):
    """The band all round the sleeve, and the leaf patch below it on the outside."""
    start = PATCH_START
    colour[mine[(along > start) & (along < start + BAND_LENGTH * fit.arm_share())]] = BOTANIST
    gap, length, half = (value * fit.arm_share() for value in LEAF_PATCH)
    top = start + BAND_LENGTH * fit.arm_share() + gap
    down = (along - top) / length
    patch = (down >= 0) & (down <= 1) & (np.abs(outside) < half)
    colour[mine[patch]] = BOTANIST
    colour[mine[patch & leaf_inside(outside / half, down * 2 - 1)]] = LEAF
    vein = patch & (np.abs(outside / half + (down * 2 - 1)) < 0.09) & (np.abs(down * 2 - 1) < 0.62)
    colour[mine[vein]] = LEAF_VEIN


def leaf_inside(across, down):
    """A pointed leaf on a square patch (both from -1 to 1), lying corner to corner."""
    first = (across - down) / np.sqrt(2)
    second = (across + down) / np.sqrt(2)
    length, width = 0.95, 0.42
    return (second / length) ** 2 + (first / width) ** 2 * (1 + 1.4 * np.abs(second / length)) < 1.0


# The American expedition's indoor suit (#112): one light blue all over, the
# zip line's edges a darker blue, a US flag patch on the left upper sleeve, and the pocket's flap
# a white name tag.
LIGHT_BLUE = (128, 164, 198)
DARK_BLUE = (92, 124, 160)
US_RED = (178, 52, 48)
US_WHITE = (236, 232, 222)
US_BLUE = (40, 52, 104)
TAG_WHITE = (236, 234, 226)
TAG_LETTERS = (36, 44, 80)
US_PATCH = (0.050, 0.020)


def work_cloth_american(part, panels, joints):
    on, owner, _, points, normals = texel_places(part, CLOTH_PICTURE)
    panel = panel_of_each_texel(part, panels, owner, on)
    sign = np.sign(points[:, 0])
    colour = np.tile(np.array(LIGHT_BLUE, float), (len(points), 1))
    # The knit cuffs stay the suit's blue: coloured by pattern panel their edges came out ragged.
    mine = np.where((np.char.find(panel, "sleeve") >= 0) & (sign > 0))[0]
    along, outside = outer_line(points[mine], normals[mine], joints,
                                ("LeftArm", "LeftForeArm", "LeftHand"), 1.0)
    length, half = US_PATCH[0] * fit.arm_share(), US_PATCH[1] * fit.arm_share()
    down = (along - PATCH_START) / length
    across = outside / half
    patch = (down >= 0) & (down <= 1) & (np.abs(across) < 1)
    colour[mine[patch]] = us_flag((1 - down[patch]), (across[patch] + 1) / 2)
    return picture_of(on, colour)


def us_flag(up, along):
    """The US flag, simplified to read small: seven stripes, the blue canton with white dots.
    `along` 0 at the hoist, `up` 0 at the bottom, both 0 to 1."""
    stripe = np.floor(up * 7).astype(int)
    colour = np.where((stripe % 2 == 0)[:, None], np.array(US_RED, float), np.array(US_WHITE, float))
    canton = (along < 0.42) & (up > 3 / 7)
    colour[canton] = US_BLUE
    dot_x = (along / 0.42 * 3) % 1.0
    dot_y = ((up - 3 / 7) / (4 / 7) * 2) % 1.0
    dots = canton & (np.hypot(dot_x - 0.5, dot_y - 0.5) < 0.22)
    colour[dots] = US_WHITE
    return colour


def work_placket_american(part, across):
    on, owner, shares, _, _ = texel_places(part, PLACKET_PICTURE)
    across_here = texels.at_texels(across[part["source"]], part["faces"], owner, shares)[on]
    colour = np.tile(np.array(LIGHT_BLUE, float), (on.sum(), 1))
    colour[np.abs(across_here) < 0.0025] = DARK_BLUE
    return picture_of(on, colour)


def work_pocket_american(part, flap_from):
    """The chest pocket: light blue, its flap the white name tag with the name in dark letters."""
    on, owner, _, points, _ = texel_places(part, POCKET_PICTURE)
    flap = (part["source"][part["faces"]] >= flap_from).all(axis=1)[owner[on]]
    colour = np.tile(np.array(LIGHT_BLUE, float), (len(points), 1))
    colour[flap] = TAG_WHITE
    flap_points = part["points"][np.unique(part["faces"][(part["source"][part["faces"]] >= flap_from).all(axis=1)])]
    letters = name_letters(points[:, 0], points[:, 1], flap_points)
    colour[flap] = colour[flap] * (1 - letters[flap, None]) + np.array(TAG_LETTERS, float) * letters[flap, None]
    return picture_of(on, colour)


NAME_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NAME_MARGIN = 0.14
NAME_SIDE_MARGIN = 0.20


def name_letters(x_values, y_values, plate_points):
    """How much of each point is inside a letter of the name, written across the plate's front
    view with a margin, read smoothly off a drawn mask."""
    x_low, x_high = plate_points[:, 0].min(), plate_points[:, 0].max()
    y_low, y_high = plate_points[:, 1].min(), plate_points[:, 1].max()
    width, height = 1024, int(1024 * (y_high - y_low) / (x_high - x_low))
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    size = int(height * (1 - 2 * NAME_MARGIN))
    font = ImageFont.truetype(NAME_FONT, size)
    while draw.textlength(WHO["name"], font=font) > width * (1 - 2 * NAME_SIDE_MARGIN):
        size -= 2
        font = ImageFont.truetype(NAME_FONT, size)
    draw.text((width / 2, height / 2), WHO["name"], fill=255, font=font, anchor="mm")
    array = np.asarray(mask, dtype=float) / 255.0
    # The wearer faces +z, so their left (+x) is the picture's right as seen from the front.
    column = (x_values - x_low) / (x_high - x_low) * width - 0.5
    row = (y_high - y_values) / (y_high - y_low) * height - 0.5
    return ndimage.map_coordinates(array, [row, column], order=1, mode="constant")


def arm_patch(colour, mine, along, outside):
    """The patch on one upper sleeve, over the piping: red, two white stripes across it."""
    share = (along - PATCH_START) / PATCH_LENGTH
    patch = (share >= 0) & (share <= 1) & (np.abs(outside) < PATCH_HALF)
    colour[mine[patch]] = FLAG
    for low, high in PATCH_STRIPES:
        colour[mine[patch & (share > low) & (share < high)]] = PATCH_WHITE


def seat_pockets(colour, on_the_back, points, normals):
    """The two welt pockets on the seat: a dark slit each side of the middle."""
    upward = np.tile([0.0, 1.0, 0.0], (len(points), 1))
    across = np.abs((points[:, 1] - SEAT_POCKET_Y) / tangential(upward, normals))
    slit = (on_the_back & (points[:, 2] < 0) & (across < SEAT_POCKET_TALL / 2)
            & (np.abs(points[:, 0]) > SEAT_POCKET_SPAN[0]) & (np.abs(points[:, 0]) < SEAT_POCKET_SPAN[1]))
    colour[slit] = SLIT


def work_placket(part, across):
    """The zip line: navy, a red line down each long edge. The edges are read off where each
    point sat across the zip line when it was laid out, so they run straight however the
    cloth under it folds."""
    on, owner, shares, _, _ = texel_places(part, PLACKET_PICTURE)
    across_here = texels.at_texels(across[part["source"]], part["faces"], owner, shares)[on]
    half = np.abs(across).max()
    colour = np.tile(np.array(NAVY, float), (on.sum(), 1))
    colour[np.abs(across_here) > half - PLACKET_RED] = RED
    return picture_of(on, colour)


def smoothed_normals(part, rounds):
    """The part's point normals averaged with their neighbours' `rounds` times across the whole
    part (its seams too), so a rule on them paints broad shapes rather than every bump."""
    whole_faces = part["source"][part["faces"]]
    count = part["source"].max() + 1
    normals = np.zeros((count, 3))
    normals[part["source"]] = part["normals"]
    edges = np.concatenate([whole_faces[:, [0, 1]], whole_faces[:, [1, 2]], whole_faces[:, [2, 0]]])
    for _ in range(rounds):
        total = normals.copy()
        np.add.at(total, edges[:, 0], normals[edges[:, 1]])
        np.add.at(total, edges[:, 1], normals[edges[:, 0]])
        normals = total / np.linalg.norm(total, axis=1, keepdims=True)
    return normals[part["source"]]


def hair(part):
    """The hair: near black, with one flat lighter shape where it catches the light, read off
    its normals smoothed so the shape is one piece rather than a spot on every clump."""
    smooth = dict(part, normals=smoothed_normals(part, HAIR_SHINE_SMOOTHING))
    on, _, _, points, normals = texel_places(smooth, HAIR_PICTURE)
    toward = np.array(HAIR_SHINE_TOWARD) / np.linalg.norm(HAIR_SHINE_TOWARD)
    colour = np.tile(np.array(HAIR, float), (len(points), 1))
    colour[normals @ toward > HAIR_SHINE_WITHIN] = HAIR_SHINE
    return picture_of(on, colour)


def star_inside(x_values, y_values, centre_x, centre_y, radius):
    """Whether each point is inside a five-point star, one point up."""
    angle = np.arctan2(x_values - centre_x, y_values - centre_y)
    reach = np.hypot(x_values - centre_x, y_values - centre_y)
    fold = np.abs(np.mod(angle + np.pi / 5, 2 * np.pi / 5) - np.pi / 5)
    folded_x, folded_y = reach * np.sin(fold), reach * np.cos(fold)
    inner = radius * 0.382
    tip = np.array([0.0, radius])
    corner = np.array([inner * np.sin(np.pi / 5), inner * np.cos(np.pi / 5)])
    edge = corner - tip
    return (edge[0] * (folded_y - tip[1]) - edge[1] * (folded_x - tip[0])) <= 0


def work_pocket(part, flap_from):
    """The chest pocket: navy, its flap the flag, red with the yellow star at the hoist."""
    on, owner, _, points, _ = texel_places(part, POCKET_PICTURE)
    flap = (part["source"][part["faces"]] >= flap_from).all(axis=1)[owner[on]]
    colour = np.tile(np.array(NAVY, float), (len(points), 1))
    colour[flap] = FLAG
    colour[flap & star_inside(points[:, 0], points[:, 1], *POCKET_STAR)] = STAR
    return picture_of(on, colour)


def suit_flag(part):
    """The space suit's chest flag: red, the big yellow star near the hoist (the wearer's right,
    the viewer's left)."""
    on, _, _, points, _ = texel_places(part, POCKET_PICTURE)
    x_low, x_high = part["points"][:, 0].min(), part["points"][:, 0].max()
    y_low, y_high = part["points"][:, 1].min(), part["points"][:, 1].max()
    height = y_high - y_low
    colour = np.tile(np.array(FLAG, float), (len(points), 1))
    star = star_inside(points[:, 0], points[:, 1], x_low + 0.22 * (x_high - x_low),
                       y_low + 0.62 * height, 0.30 * height)
    colour[star] = STAR
    return picture_of(on, colour)


def face_lines():
    """The nose and mouth lines of the drawn face, as a mask on the drawing's pixels: dark
    pixels inside the kept boxes, specks dropped."""
    drawn = np.asarray(Image.open(FACE / "drawn.png").convert("L")).astype(float)
    dark = drawn < DARK
    keep = np.zeros_like(dark)
    # A person's own drawing names its own boxes in view.json (#112); take C's are KEEP.
    boxes = json.loads((FACE / "view.json").read_text()).get("keep", KEEP)
    for left, top, right, bottom in boxes:
        keep[top:bottom, left:right] = True
    mask = dark & keep
    labels, count = ndimage.label(mask)
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    for index, size in enumerate(sizes, start=1):
        if size < LEAST_SPECK:
            mask[labels == index] = False
    return mask


def skin_head(part):
    """The head's skin: flat skin, and the drawing's nose and mouth lines projected straight on
    from the front onto texels that face the front and are the front-most surface there.

    Only the lines are taken from the drawing, never its colour or shading; the drawing was made
    on this head's own front depth view (FLUX.2 klein with a depth guide, kept in the look), so
    the lines land on the nose and lips they were drawn on."""
    on, _, _, points, normals = texel_places(part, HEAD_PICTURE)
    view = json.loads((FACE / "view.json").read_text())
    x_low, x_high, y_low, y_high = view["window"]
    pixels = view["size"]
    depth = np.load(FACE / "depth.npy")
    mask = face_lines().astype(float)
    column = (points[:, 0] - x_low) / (x_high - x_low) * pixels - 0.5
    row = (y_high - points[:, 1]) / (y_high - y_low) * pixels - 0.5
    inside = (column >= 0) & (column < pixels - 1) & (row >= 0) & (row < pixels - 1)
    nearest_row = np.clip(np.round(row).astype(int), 0, pixels - 1)
    nearest_column = np.clip(np.round(column).astype(int), 0, pixels - 1)
    in_front = (inside & (normals[:, 2] > FACING)
                & (points[:, 2] > depth[nearest_row, nearest_column] - DEPTH_SLACK))
    # How much of each texel the line covers, read smoothly, so the line's edge is soft by the
    # drawing's own antialiasing.
    cover = ndimage.map_coordinates(mask, [row, column], order=1, mode="constant")
    cover = np.where(in_front, cover, 0.0)[:, None]
    skin = np.tile(np.array(SKIN, float), (len(points), 1))
    if WHO["beard"] is not None:
        skin[beard(points)] = WHO["beard"]
    if WHO["painted_mouth"]:
        skin[mouth_line(points) & (normals[:, 2] > FACING)] = LINE
    if WHO["freckles"] is not None:
        skin[freckles(points) & (normals[:, 2] > FACING)] = WHO["freckles"]
    return picture_of(on, skin * (1 - cover) + np.array(LINE, float) * cover)


# A short full beard and moustache, by rules on the head (#112, Bram and Sefa), in take C's
# head measures moved with the eyes: how far under the eyes the beard's top edge runs, by
# distance from the middle (x, drop): under the nose in the middle, rising to a sideburn at the
# ear; the mouth left clear as an ellipse (its middle's drop under the eyes, half width, half
# height); and nothing lower than BEARD_LOWEST under the eyes or behind the ear.
BEARD_TOP = {
    # A full beard (Bram): over the lower cheeks, the moustache under the nose, a sideburn at the ear.
    "full": np.array([[0.0, 0.056], [0.016, 0.058], [0.030, 0.062], [0.042, 0.058], [0.052, 0.046],
                      [0.062, 0.028], [0.070, 0.010], [0.076, 0.0]]),
    # A short beard (Sefa): the jaw and the chin, the cheeks clear, and a thin moustache.
    "short": np.array([[0.0, 0.076], [0.022, 0.078], [0.036, 0.080], [0.048, 0.072], [0.058, 0.058],
                       [0.066, 0.036], [0.072, 0.012], [0.076, 0.0]]),
}
# The short beard's moustache: a band under the nose (drop from, to) out to this half width.
MOUSTACHE = (0.061, 0.067, 0.024)
BEARD_MOUTH = (0.0725, 0.020, 0.0048)
BEARD_LOWEST = 0.120
BEARD_BEHIND = 0.012


def mouth_line(points):
    """The line between the lips, a single line turned up a little at the corners: painted where
    the drawing's mouth is not kept, on a bearded face or where the drawn one read grim."""
    eye = fit.eye(1.0)
    scale = fit.head_scale()
    across = np.abs(points[:, 0]) / scale[0]
    drop = (eye[1] - points[:, 1]) / scale[1]
    bow = BEARD_MOUTH[0] - 0.0025 * (across / BEARD_MOUTH[1]) ** 2
    return (np.abs(drop - bow) < 0.0011) & (across < BEARD_MOUTH[1] * 0.85) & (points[:, 2] > fit.THEIRS["LeftEye"][2] - 0.01)


def beard(points):
    """Which head points the beard covers."""
    eye = fit.eye(1.0)
    scale = fit.head_scale()
    across = np.abs(points[:, 0]) / scale[0]
    drop = (eye[1] - points[:, 1]) / scale[1]
    table = BEARD_TOP[WHO["beard_style"]]
    top = np.interp(across, table[:, 0], table[:, 1])
    head_z = fit.THEIRS["Head"][2] + BEARD_BEHIND
    mouth = ((across / BEARD_MOUTH[1]) ** 2 + ((drop - BEARD_MOUTH[0]) / BEARD_MOUTH[2]) ** 2) < 1.0
    moustache = (drop > MOUSTACHE[0]) & (drop < MOUSTACHE[1]) & (across < MOUSTACHE[2])
    lowest = BEARD_LOWEST * WHO["beard_length"]
    return ((drop > top) | moustache) & (drop < lowest) & (points[:, 2] > head_z) & ~mouth


# Freckles (#112, Oona): small dots over the cheeks and the bridge of the nose, placed by a fixed
# seed so every build is the same: how many, their radius, and the region (drop under the eyes,
# half height; half width from the middle).
FRECKLES = 70
FRECKLE_RADIUS = 0.0011
FRECKLE_REGION = (0.028, 0.014, 0.048)


def freckles(points):
    """Which head points are in a freckle."""
    eye = fit.eye(1.0)
    scale = fit.head_scale()
    generator = np.random.default_rng(7)
    spots = np.column_stack([generator.uniform(-1, 1, FRECKLES * 3), generator.uniform(-1, 1, FRECKLES * 3)])
    spots = spots[np.hypot(spots[:, 0], spots[:, 1]) < 1.0][:FRECKLES]
    across = spots[:, 0] * FRECKLE_REGION[2] * scale[0]
    height = eye[1] - (FRECKLE_REGION[0] + spots[:, 1] * FRECKLE_REGION[1]) * scale[1]
    distance, _ = cKDTree(np.column_stack([across, height])).query(points[:, :2])
    return (distance < FRECKLE_RADIUS) &(points[:, 2] > fit.THEIRS["LeftEye"][2] - 0.02)


def far_colour(region):
    """One colour zone of the bare distant body (`regions.py`) in this person's colours (#112):
    their skin, their work suit's cloth and its boots."""
    american = WHO["work"] == "american"
    return {"skin": SKIN, "clothes": LIGHT_BLUE if american else NAVY,
            "boots": SNEAKER if american else BOOT}[region]


def suit_colour(name):
    for prefix, colour in SUIT_FLAT:
        if name.startswith(prefix):
            return colour
    raise ValueError(f"no colour for the space suit's {name}")


# The American suit's colours (#112), picked from Oona, Bram and Sefa's drawings. A part takes
# the colour of the first name it starts with.
SUIT_BLUE = (52, 84, 164)
GOLD_VISOR = (214, 164, 52)
AMERICAN_FLAT = [("band_blue", SUIT_BLUE), ("helmet_rim", (216, 214, 206)),
                 ("helmet_bearing", (170, 172, 168)), ("helmet", (236, 234, 226)),
                 ("visor", GOLD_VISOR), ("chest_screen", (238, 238, 232)),
                 ("chest_knobs", (70, 72, 74)), ("chest_box", (150, 152, 146)),
                 ("hose", (120, 122, 120)), ("pack", (224, 220, 208)),
                 ("strap", (170, 172, 160)), ("belt", (170, 172, 160)),
                 ("thigh_pocket", (224, 220, 208)), ("wrist_ring", (190, 192, 188)),
                 ("mitt", (232, 230, 222)), ("boot", (226, 224, 216)),
                 ("neck_ring", (200, 202, 198)), ("cloth", WHITE)]


def american_colour(name):
    for prefix, colour in AMERICAN_FLAT:
        if name.startswith(prefix):
            return colour
    raise ValueError(f"no colour for the American suit's {name}")


def arm_flag(part, grid):
    """The US flag on the arm plate: `grid` holds each point's place down the arm (0 at the
    shoulder end) and round it (-1 to 1)."""
    on, owner, shares, _, _ = texel_places(part, POCKET_PICTURE)
    here = texels.at_texels(grid[part["source"]], part["faces"], owner, shares)[on]
    return picture_of(on, us_flag(1 - here[:, 0], (here[:, 1] + 1) / 2))


def name_tag(part):
    """The chest name tag: white, the name in dark letters across its front."""
    on, _, _, points, _ = texel_places(part, POCKET_PICTURE)
    front = part["points"][part["points"][:, 2] > part["points"][:, 2].max() - 0.004]
    letters = name_letters(points[:, 0], points[:, 1], front)
    colour = np.array(TAG_WHITE, float) * (1 - letters[:, None]) + np.array(TAG_LETTERS, float) * letters[:, None]
    return picture_of(on, colour)
