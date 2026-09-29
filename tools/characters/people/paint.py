"""The crew's colours, painted after the owner's drawing of them (#100): every small part takes one
flat colour picked from the drawing, and the parts that carry a pattern are painted texel by
texel by rules placed on the body: the work suit's grey yokes and red piping, the zip line, the
flag on the pocket's flap and on the space suit's chest, and the lines of the nose and mouth.

A painter takes a part split along its texture seams (`dress.split_part`: points, faces, uv,
normals, and each point's source point on the unsplit part) and gives back its picture as bytes.
"""
import json

import numpy as np
import texels
from paths import FACE
from PIL import Image
from scipy import ndimage

# The work suit's palette, lit side, picked from the drawing (medians of patches).
NAVY = (50, 57, 78)
GREY = (138, 136, 132)
RED = (178, 58, 44)
FLAG = (184, 48, 38)
STAR = (246, 206, 92)
BLACK = (30, 31, 34)
BOOT = (32, 34, 34)
STEEL = (150, 152, 156)
SKIN = (226, 172, 138)
HAIR = (24, 24, 28)
BROW = (22, 20, 20)
IRIS = (62, 40, 30)
EYE_WHITE = (232, 228, 218)
WORK_FLAT = {"work_belt": BLACK, "work_buckle": STEEL, "work_boot_Left": BOOT,
             "work_boot_Right": BOOT, "work_collar": NAVY, "work_lining": NAVY,
             "skin_hands": SKIN, "eyes": EYE_WHITE, "irises": IRIS, "eyebrows": BROW}

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
SUIT_FLAT = [("band_red", SUIT_RED), ("band_gold", GOLD), ("knee_pad", PAD), ("elbow_pad", PAD),
             ("wrist_ring", RING), ("mitt", MITT), ("boot", MOON_BOOT), ("strap", STRAP),
             ("belt", STRAP), ("waist_light", LAMP), ("waist_box", LIGHT_GREY),
             ("chest_knobs", KNOB), ("chest_box", LIGHT_GREY), ("pack", PACK),
             ("visor_rim", GOLD), ("visor", VISOR), ("helmet", WHITE), ("neck_ring", LIGHT_GREY),
             ("cloth", WHITE)]

# The hair's highlight, where the drawing's hair catches the light: one flat lighter shape where
# the hair faces this way (up, forward and to his left), inside this much of a turn.
HAIR_SHINE = (48, 52, 62)
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
FRONT_YOKE = ((0.090, 1.478), (0.195, 1.350))
# Back yoke: from beside the collar down to the arm at the height of the back's cross seam.
BACK_YOKE = ((0.085, 1.470), (0.205, 1.330))
BACK_SEAM_Y = 1.330
BACK_SEAM_TOP = 1.47
# The sleeve is grey down to this far along the arm from the shoulder joint.
SLEEVE_CAP = 0.062
# The trouser legs' piping stops under the waist.
WAIST_TOP = 1.085
# The patch on the outside of each upper sleeve: how far down the arm from the shoulder joint it
# starts, how long it is, its half width round the arm, and its two white stripes as shares of
# its length.
PATCH_START = 0.085
PATCH_LENGTH = 0.075
PATCH_HALF = 0.024
PATCH_STRIPES = ((0.30, 0.44), (0.56, 0.70))
PATCH_WHITE = (232, 228, 218)
# The two welt pockets on the seat: their height, their span out from the middle, how tall the
# slit is, and its colour, a darker navy.
SEAT_POCKET_Y = 0.955
SEAT_POCKET_SPAN = (0.045, 0.140)
SEAT_POCKET_TALL = 0.006
SLIT = (26, 30, 42)
# The zip line's piping: how far in from each long edge the red starts.
PLACKET_RED = 0.006
# The star on the pocket's flag: its middle and its outer radius, in metres on the bind pose.
POCKET_STAR = (0.058, 1.327, 0.016)
# The face: which drawn lines are kept (pixel boxes round the nose, and the mouth and chin), how
# dark a pixel must be to count, the smallest speck kept, how far a texel may face away from the
# front and how far behind the front-most surface it may sit and still take a line.
LINE = (46, 30, 26)
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
    for mine, along, outside in patches:
        arm_patch(colour, mine, along, outside)
    seat_pockets(colour, np.char.startswith(panel, "pant_b"), points, normals)
    return picture_of(on, colour)


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
    for left, top, right, bottom in KEEP:
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
    return picture_of(on, np.array(SKIN, float) * (1 - cover) + np.array(LINE, float) * cover)


def suit_colour(name):
    for prefix, colour in SUIT_FLAT:
        if name.startswith(prefix):
            return colour
    raise ValueError(f"no colour for the space suit's {name}")
