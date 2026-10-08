"""The prologue's people in plain clothes (#112): the crowd's edge bodies' outfits, the leader on
his podium, and the launch-day guard, driver and two technicians. Each outfit is a list of Parts,
as the crew's are (`dress.py`), built by `plain.py` on a kit build and painted flat in a few
colours, or with lines drawn on (the driver's shirt and tie, the leader's seams and pockets).

    MOTION_PERSON=guard python body.py      (run.sh builds each of them)

Who somebody is comes from their look's `person.json`: `prologue` (leader, guard, driver,
tech_man or tech_woman), and their kit `face` and `hair_style`. Their file holds `person`,
everything they wear with their head and hair, and `person_cap`, a cap on its own so the game can
keep its peak from throwing a jagged shadow across the face. The crowd's plain outfits go into the
kit files as `plain_<outfit>` nodes (`kit.py`). The leader is his second build (leader2,
2026-09-30); the first was turned down.
"""
import numpy as np
import trimesh

import dress
import faces
import fit
import kit
import paint
import plain
import shapes
import skin
import work_suit
import texels
from scipy.spatial import cKDTree
from paths import COAT_DRAPE, JACKET_DRAPE, TROUSERS_DRAPE
from person import WHO

SKIN = paint.SKIN
BLACK = (26, 26, 28)
SHOE = (22, 22, 24)
BRASS = (196, 160, 70)
WHITE_GLOVE = (236, 234, 228)
# The crowd's plain outfits: jacket or coat colour, trousers, buttons.
PLAIN = {
    "jacket_blue": {"top": "jacket", "cloth": (58, 82, 124), "trousers": (40, 42, 48), "buttons": (30, 34, 44)},
    "coat_grey": {"top": "coat", "cloth": (120, 120, 118), "trousers": (52, 52, 56), "buttons": (40, 40, 42)},
    "uniform_olive": {"top": "jacket", "cloth": (86, 94, 58), "trousers": (86, 94, 58), "buttons": BRASS},
}
TOPS = {"jacket": JACKET_DRAPE, "coat": COAT_DRAPE}
GUARD_OLIVE = (86, 94, 58)
GUARD_RED = (176, 34, 32)
GUARD_BELT = (92, 56, 34)
DRIVER_SUIT = (52, 52, 56)
SHIRT_WHITE = (232, 230, 224)
TIE = (30, 30, 34)
TECH_WHITE = (226, 222, 210)
CLIPBOARD = (132, 94, 56)
PAPER = (236, 234, 226)
PIN_RED = (196, 32, 30)


# Leader B's suit, from the drawing (takes/leader_b_19.png): a mid grey sampled off its lit
# cloth, the trousers a shade under the jacket; darker grey seams and pocket lines drawn on the
# cloth, near black where one piece of cloth ends over another.
LEADER_JACKET = (86, 87, 86)
LEADER_TROUSERS = (78, 79, 78)
LEADER_SEAM = (52, 53, 54)
LEADER_CREASE = (58, 59, 59)
LEADER_INK = (24, 24, 26)
LEADER_FLAP = (76, 77, 76)
LEADER_BUTTON = (26, 26, 28)
LEADER_SOLE = (66, 64, 62)
# His hair: silver combed straight back, dark comb lines, a darker grey where it turns away.
LEADER_HAIR = (190, 190, 188)
LEADER_HAIR_SHINE = (224, 224, 222)
LEADER_HAIR_SHADE = (146, 146, 148)
LEADER_HAIR_LINE = (122, 122, 126)
# Comb lines: one every this many degrees round the head, this share of the gap wide, climbing
# this many radians per metre run back.
HAIR_LINE_EVERY = 10.0
HAIR_LINE_SHARE = 0.16
HAIR_SWEEP = 2.2
# The comb lines run full width over the front part of the head, thinning to nothing at the back.
HAIR_LINES_REACH = 0.55
# Line widths on the cloth, whole (metres).
SEAM_WIDTH = 0.0022
HEM_WIDTH = 0.0045
POCKET_LINE = 0.002
CREASE_WIDTH = 0.0022
# The four patch pockets: centre x and the flap's centre height (template), the flap's width and
# height, how far the pocket runs down under it.
LEADER_POCKETS = [(0.095, 1.325, 0.10, 0.032, 0.105), (-0.095, 1.325, 0.10, 0.032, 0.105),
                  (0.10, 1.04, 0.12, 0.04, 0.13), (-0.10, 1.04, 0.12, 0.04, 0.13)]
JACKET_PICTURE = 2048
TROUSER_PICTURE = 1024


def near(points, samples, width):
    """Which points lie within half of `width` of any of the samples."""
    distance, _ = cKDTree(samples).query(points, distance_upper_bound=width / 2)
    return distance < width / 2


def pocket_lines(points, normals, pockets):
    """Texels on a pocket's outline (sides and bottom, below its flap) and on the shadow line
    under each flap, in the front view."""
    outline = np.zeros(len(points), bool)
    shadow = np.zeros(len(points), bool)
    facing = (normals[:, 2] > 0.35) & (points[:, 2] > 0)
    across_x = paint.tangential(np.tile([1.0, 0.0, 0.0], (len(points), 1)), normals)
    across_y = paint.tangential(np.tile([0.0, 1.0, 0.0], (len(points), 1)), normals)
    for x_centre, y_flap, width, flap, depth in pockets:
        top = y_flap - flap / 2
        bottom = top - depth
        left, right = x_centre - width / 2, x_centre + width / 2
        inside_y = (points[:, 1] > bottom) & (points[:, 1] < top)
        inside_x = (points[:, 0] > left) & (points[:, 0] < right)
        sides = inside_y & ((np.abs(points[:, 0] - left) * across_x < POCKET_LINE / 2)
                            | (np.abs(points[:, 0] - right) * across_x < POCKET_LINE / 2))
        base = inside_x & (np.abs(points[:, 1] - bottom) * across_y < POCKET_LINE / 2)
        outline |= facing & (sides | base)
        shadow |= facing & inside_x & (points[:, 1] < top) & (points[:, 1] > top - 0.004)
    return outline, shadow


def leader_jacket_picture(split, made, pockets):
    """The jacket: mid grey, its seams in darker grey, the centre front edge, hem and cuffs in
    near black, the four pockets outlined under their flaps."""
    on, _, _, points, normals = paint.texel_places(split, JACKET_PICTURE)
    colour = np.tile(np.array(LEADER_JACKET, float), (len(points), 1))
    seams = made["seams"]
    front_edge = (np.abs(seams[:, 0]) < 0.02) & (seams[:, 2] > 0)
    colour[near(points, seams[~front_edge], SEAM_WIDTH)] = LEADER_SEAM
    outline, shadow = pocket_lines(points, normals, pockets)
    colour[outline] = LEADER_SEAM
    colour[shadow] = LEADER_INK
    colour[near(points, seams[front_edge], SEAM_WIDTH * 1.4)] = LEADER_INK
    mesh = made["mesh"]
    colour[near(points, plain.open_edges(np.asarray(mesh.vertices), np.asarray(mesh.faces)), HEM_WIDTH)] = LEADER_INK
    return paint.picture_of(on, colour)


def trouser_creases(points, normals, leg_points):
    """Texels on the crease down the front of each leg: through the front-most point of the
    leg at each height, below the crotch."""
    crease = np.zeros(len(points), bool)
    crotch = leg_points[np.abs(leg_points[:, 0]) < 0.01][:, 1].min()
    across_x = paint.tangential(np.tile([1.0, 0.0, 0.0], (len(points), 1)), normals)
    for sign in (1.0, -1.0):
        mine = leg_points[(np.sign(leg_points[:, 0]) == sign) & (leg_points[:, 1] < crotch)]
        heights = np.arange(mine[:, 1].min(), crotch, 0.01)
        front_x, found = [], []
        for height in heights:
            band = mine[np.abs(mine[:, 1] - height) < 0.01]
            if len(band):  # the straight hem's rows are further apart than a band
                front_x.append(band[np.argmax(band[:, 2]), 0])
                found.append(height)
        front_x = np.interp(heights, found, front_x)
        front_x = np.convolve(np.pad(front_x, 4, mode="edge"), np.ones(9) / 9, mode="valid")
        here = (np.sign(points[:, 0]) == sign) & (points[:, 1] < crotch - 0.03) & (normals[:, 2] > 0.4)
        line_x = np.interp(points[:, 1], heights, front_x)
        crease |= here & (np.abs(points[:, 0] - line_x) * across_x < CREASE_WIDTH / 2)
    return crease


def leader_trouser_picture(split, lines):
    on, _, _, points, normals = paint.texel_places(split, TROUSER_PICTURE)
    colour = np.tile(np.array(LEADER_TROUSERS, float), (len(points), 1))
    colour[near(points, lines["seams"], SEAM_WIDTH)] = LEADER_SEAM
    colour[trouser_creases(points, normals, split["points"])] = LEADER_CREASE
    colour[near(points, plain.open_edges(split["points"], split["faces"]), HEM_WIDTH)] = LEADER_INK
    return paint.picture_of(on, colour)


def edged_picture(split, colour, edge_colour, width, size=512):
    """A part in one colour with its open edges drawn round in another."""
    on, _, _, points, _ = paint.texel_places(split, size)
    colours = np.tile(np.array(colour, float), (len(points), 1))
    colours[near(points, plain.open_edges(split["points"], split["faces"]), width)] = edge_colour
    return paint.picture_of(on, colours)


def opening_picture(split, across, colour):
    """The front opening strip: cloth-coloured, the jacket's front edge a near-black line down
    its wearer's-right side."""
    on, owner, shares, _, _ = paint.texel_places(split, 512)
    across_here = texels.at_texels(across[split["source"]], split["faces"], owner, shares)[on]
    half = np.abs(across).max()
    colours = np.tile(np.array(colour, float), (on.sum(), 1))
    colours[across_here < -half + 0.003] = LEADER_INK
    return paint.picture_of(on, colours)


def painted_with_inside(name, shaped, painter, inside_colour):
    """A painted outside and a flat inside (the same cloth, faces turned in)."""
    points, part_faces, weights = shaped
    split = dress.split_part(f"leader_{name}", points, part_faces, weights)
    inside = dress.flat(f"{name}_inside", points, part_faces[:, ::-1].copy(), weights, inside_colour)
    return [dress.painted(name, split, painter(split)), inside]


def leader_shoes(body):
    """Black shoes with a dark grey sole along their foot, and the pair for the trousers."""
    pair = plain.low_shoes(body)
    parts = []
    for side, (points, part_faces) in zip(("Left", "Right"), pair):
        weights = plain.boots.weights(points, side, body)
        split = dress.split_part(f"leader_shoe_{side}", points, part_faces, weights)
        on, _, _, texel_points, _ = paint.texel_places(split, 256)
        colour = np.tile(np.array(SHOE, float), (len(texel_points), 1))
        colour[texel_points[:, 1] < points[:, 1].min() + 0.011] = LEADER_SOLE
        parts.append(dress.painted(f"shoe_{side}", split, paint.picture_of(on, colour)))
    return parts, pair


def leader_hair(split):
    """Silver hair combed straight back: dark comb lines running front to back over the crown
    and along the sides, a darker grey where the hair turns down and away, one light shape on
    top where it catches the light."""
    smooth = dict(split, normals=paint.smoothed_normals(split, paint.HAIR_SHINE_SMOOTHING))
    on, _, _, points, normals = paint.texel_places(smooth, 1024)
    hair_points = split["points"]
    centre_x, centre_z = hair_points[:, 0].mean(), hair_points[:, 2].mean()
    centre_y = hair_points[:, 1].max() - 0.10
    colour = np.tile(np.array(LEADER_HAIR, float), (len(points), 1))
    toward = np.array(paint.HAIR_SHINE_TOWARD) / np.linalg.norm(paint.HAIR_SHINE_TOWARD)
    colour[normals @ toward > 0.95] = LEADER_HAIR_SHINE
    colour[(normals[:, 1] < -0.2) | (normals[:, 2] < -0.6)] = LEADER_HAIR_SHADE
    front = hair_points[:, 2].max()
    around = np.arctan2(points[:, 0] - centre_x, points[:, 1] - centre_y)
    # Swept: along the sides a line climbs as it runs back, from the temple up over the ear.
    around = around - np.sign(around) * HAIR_SWEEP * (front - points[:, 2])
    period = np.radians(HAIR_LINE_EVERY)
    line = np.floor(around / period)
    wobble = 0.12 * period * np.sin((points[:, 2] - centre_z) * 24.0 + line * 1.9)
    place = np.mod((around + wobble) / period, 1.0)
    # The lines start a little back from the front edge, as a comb's teeth do, and fade out
    # toward the nape.
    # Each line its own width, and some left out, so the lines read as combed hair, not stripes.
    share = HAIR_LINE_SHARE * (0.55 + 0.9 * np.mod(np.abs(line) * 0.618, 1.0))
    kept = np.mod(np.abs(line) * 0.382 + 0.1, 1.0) > 0.25
    # Toward the back they would all run together at the crown, so they thin out and stop
    # behind it, as the drawing's do.
    back = hair_points[:, 2].min()
    reach = np.clip((points[:, 2] - back) / (front - back) / HAIR_LINES_REACH, 0.0, 1.0)
    comb = ((np.abs(place - 0.5) < share * reach / 2) & kept & (points[:, 2] < front - 0.012)
            & (normals[:, 1] > -0.35))
    colour[comb] = LEADER_HAIR_LINE
    return paint.picture_of(on, colour)


def hair_split(part):
    """A painted part taken back apart as a painter takes it."""
    return {"points": part.points, "faces": part.faces, "weights": part.weights, "uv": part.uv,
            "normals": part.normals, "source": np.arange(len(part.points))}


def flap_picture(split, pockets):
    """The pocket flaps: a shade under the cloth, each drawn round in near black."""
    on, _, _, points, normals = paint.texel_places(split, 512)
    colour = np.tile(np.array(LEADER_FLAP, float), (len(points), 1))
    centres = np.array([[x, y] for x, y, *_ in pockets])
    mine = np.argmin(np.linalg.norm(points[:, None, :2] - centres[None], axis=2), axis=1)
    half = np.array([[width / 2, flap / 2] for _, _, width, flap, _ in pockets])[mine]
    inset = np.min(half - np.abs(points[:, :2] - centres[mine]), axis=1)
    colour[(inset < 0.0022) | (normals[:, 2] < 0.3)] = LEADER_INK
    return paint.picture_of(on, colour)


def seated(pieces, made):
    """Small pieces lying on the cloth as one part, each weighted from the cloth under it (one
    set of weights for all of them would sink the belly's buttons into it as he bends)."""
    points, part_faces = plain.joined(pieces)
    weights = np.vstack([plain.lying_on(piece_points, made["mesh"], made["weights"]) for piece_points, _ in pieces])
    return points, part_faces, weights


def flat(name, shaped, colour, both_sides=False):
    points, part_faces, weights = shaped
    return dress.flat(name, points, part_faces, weights, colour, both_sides=both_sides)


def rigid(points, names, joint="Head"):
    return skin.on_one_joint(len(points), names, joint)


def footwear(body, kind):
    """Shoes or tall boots, as flat parts with their weights, and the pair for the trousers."""
    pair = plain.low_shoes(body) if kind == "shoes" else plain.tall_boots(body, 1.75)
    parts = []
    for side, (points, part_faces) in zip(("Left", "Right"), pair):
        parts.append(dress.flat(f"shoe_{side}", points, part_faces,
                                plain.boots.weights(points, side, body), SHOE))
    return parts, pair


def jacket_and_trousers(body, top, trousers_colour, cloth_colour, feet="shoes"):
    """A jacket or coat over trousers over shoes (or tucked into boots): the parts, and the
    jacket's layout numbers."""
    parts, pair = footwear(body, feet)
    legs = plain.trousers(body, TROUSERS_DRAPE, pair, into_boots=feet == "boots")
    parts.append(flat("trousers", legs, trousers_colour))
    under = trimesh.Trimesh(legs[0], legs[1], process=False)
    shaped, made = plain.jacket(body, TOPS[top], under)
    parts.append(flat("jacket", shaped["cloth"], cloth_colour, both_sides=True))
    parts.append(flat("collar", shaped["collar"], cloth_colour, both_sides=True))
    parts.append(dress.flat("skin_hands", *skin.bare_hands(body), SKIN))
    return parts, made


def front_buttons(made, count, low, high, colour, x=0.0):
    """Buttons down the front between two of take C's heights."""
    heights = np.linspace(float(fit.y(high)), float(fit.y(low)), count)
    points, part_faces = plain.buttons(made, heights, x)
    return dress.flat("buttons", points, part_faces, plain.lying_on(points, made["mesh"], made["weights"]), colour)


def opening_part(made, low, colour):
    """The jacket's front opening, down to one of take C's heights."""
    points, part_faces, weights, _ = plain.opening(made, float(fit.y(low)))
    return dress.flat("opening", points, part_faces, weights, colour)


def pocket_flaps(made, across, height, size, colour):
    """A pocket flap each side of the chest, at a place on take C."""
    places = [fit.xy(across, height), fit.xy(-across, height)]
    points, part_faces = plain.flaps(made, places, size)
    return dress.flat("flaps", points, part_faces, plain.lying_on(points, made["mesh"], made["weights"]), colour)


def plain_outfit(body, name):
    """One of the crowd's plain outfits on a build: a list of Parts."""
    spec = PLAIN[name]
    parts, made = jacket_and_trousers(body, spec["top"], spec["trousers"], spec["cloth"])
    darker = tuple(int(value * 0.8) for value in spec["cloth"])
    low = 0.62 if spec["top"] == "coat" else 0.86
    parts.append(opening_part(made, low, darker))
    parts.append(front_buttons(made, 5 if spec["top"] == "coat" else 4, low + 0.1, 1.40, spec["buttons"]))
    if name == "uniform_olive":
        parts.append(pocket_flaps(made, 0.085, 1.30, (0.09, 0.035), GUARD_OLIVE))
    return parts


# ---- a whole person ---------------------------------------------------------------------------

def head_and_hair(body, reference):
    """This person's kit face on the build and their hair on it: Parts, the worn head's points
    (for fitting a cap), the eyes' middles and the skin's points (for fitting glasses)."""
    shaped, worn, carry = kit.head_parts(body, WHO["face"], reference)
    parts = kit.paint_head(shaped, WHO["face"], body, f"{WHO['face']}_")
    points, part_faces, weights, _ = kit.hair_part(WHO["hair_style"], worn, carry, body.joint_names)
    parts.append(kit.paint_hair(WHO["hair_style"], WHO["face"], points, part_faces, weights, f"{WHO['face']}_"))
    head_points = np.vstack([shaped["skin_head"][0], points])
    irises = shaped["irises"][0]
    eyes = np.array([irises[irises[:, 0] > 0].mean(axis=0), irises[irises[:, 0] < 0].mean(axis=0)])
    return parts, head_points, eyes, shaped["skin_head"][0]


def cap_parts(head_points, eyes, colours, names, peaked=True):
    """A cap on the head: crown, band and peak, each flat, fixed on the Head."""
    made = plain.cap(head_points, eyes[:, 1].mean() + 0.02, peaked)
    parts = []
    for key, colour in colours.items():
        points, part_faces = made[key]
        parts.append(dress.flat(key, points, part_faces, rigid(points, names), colour))
    return parts


def leader(body, reference):
    """The leader on his podium (leader B, redone 2026-09-30): a mid grey state suit with its
    seams, pockets and creases drawn on, a red pin, dark glasses and silver hair combed back."""
    parts, pair = leader_shoes(body)
    lines = {}
    legs = plain.trousers(body, TROUSERS_DRAPE, pair, lines=lines)
    split = dress.split_part("leader_trousers", *legs)
    parts.append(dress.painted("trousers", split, leader_trouser_picture(split, lines)))
    under = trimesh.Trimesh(legs[0], legs[1], process=False)
    shaped, made = plain.jacket(body, JACKET_DRAPE, under)
    pockets = [(float(fit.x(x, y)), float(fit.y(y)), width, flap, depth) for x, y, width, flap, depth in LEADER_POCKETS]
    parts += painted_with_inside("jacket", shaped["cloth"], lambda split: leader_jacket_picture(split, made, pockets),
                                 LEADER_JACKET)
    parts += painted_with_inside("collar", shaped["collar"],
                                 lambda split: edged_picture(split, LEADER_JACKET, LEADER_INK, 0.004), LEADER_JACKET)
    parts.append(dress.flat("skin_hands", *skin.bare_hands(body), SKIN))
    points, part_faces, weights, across = plain.opening(made, float(fit.y(0.84)))
    split = dress.split_part("leader_opening", points, part_faces, weights)
    parts.append(dress.painted("opening", split, opening_picture(split, across, LEADER_JACKET)))
    heights = np.linspace(float(fit.y(1.405)), float(fit.y(0.92)), 5)
    # The strip is lifted over the belly's folds, so the buttons are seated on it, not on the
    # cloth under it (where the strip would cover them).
    strip = trimesh.Trimesh(np.vstack([made["mesh"].vertices, split["points"]]),
                            np.vstack([made["mesh"].faces, split["faces"] + len(made["mesh"].vertices)]), process=False)
    buttons = [plain.buttons(dict(made, mesh=strip), [height], 0.0, radius=0.010) for height in heights]
    parts.append(dress.flat("buttons", *seated(buttons, made), LEADER_BUTTON))
    flaps = [plain.flaps(made, [(x, y)], (width, flap)) for x, y, width, flap, _ in pockets]
    points, part_faces, weights = seated(flaps, made)
    split = dress.split_part("leader_flaps", points, part_faces, weights)
    parts.append(dress.painted("flaps", split, flap_picture(split, pockets)))
    hit, normal = plain.front_hit(made["mesh"], pockets[0][0] - 0.01, pockets[0][1] + 0.032)
    pin_points, pin_faces = plain.disc(hit, normal, 0.009, 0.005, 16)
    parts.append(dress.flat("pin", pin_points, pin_faces, plain.lying_on(pin_points, made["mesh"], made["weights"]),
                            PIN_RED))
    head, head_points, eyes, skin_points = head_and_hair(body, reference)
    parts += head[:-1]
    split = hair_split(head[-1])
    parts.append(dress.painted("hair", split, leader_hair(split)))
    points, part_faces = plain.glasses(eyes, skin_points)
    parts.append(dress.flat("glasses", points, part_faces, rigid(points, body.joint_names), BLACK))
    return parts


def guard(body, reference):
    """The guard at the door on launch day: an olive uniform with red shoulder boards and cap
    band, a belt, tall boots (takes/guard_a_7.png)."""
    parts, made = jacket_and_trousers(body, "jacket", GUARD_OLIVE, GUARD_OLIVE, feet="boots")
    parts.append(opening_part(made, 0.86, (72, 78, 48)))
    parts.append(front_buttons(made, 4, 1.02, 1.39, BRASS))
    parts.append(pocket_flaps(made, 0.088, 1.31, (0.09, 0.035), (78, 86, 52)))
    points, part_faces = plain.shoulder_boards(made, body)
    parts.append(dress.flat("shoulder_boards", points, part_faces, skin.at_the_nearest_point(
        points, np.asarray(made["mesh"].vertices), made["weights"]), GUARD_RED))
    parts += guard_belt(made)
    head, head_points, eyes, _ = head_and_hair(body, reference)
    parts += head
    parts += cap_parts(head_points, eyes, {"cap_crown": GUARD_OLIVE, "cap_band": GUARD_RED, "cap_peak": BLACK},
                       body.joint_names)
    return parts


def guard_belt(made):
    """The guard's belt round the jacket and its brass buckle."""
    waist = float(fit.y(1.06))
    belt_points, belt_faces, belt_front = work_suit.belt(made["mesh"], waist)
    belt_weights = skin.averaged(skin.at_the_nearest_point(belt_points, np.asarray(made["mesh"].vertices), made["weights"]),
                                 belt_faces, work_suit.BELT_SMOOTHING)
    buckle_points, buckle_faces = work_suit.buckle(waist, belt_front)
    front = belt_points[:, 2] > belt_points[:, 2].max() - 0.02
    one = belt_weights[front].mean(axis=0)
    return [dress.flat("belt", belt_points, belt_faces, belt_weights, GUARD_BELT),
            dress.flat("buckle", buckle_points, buckle_faces, np.tile(one / one.sum(), (len(buckle_points), 1)), BRASS)]


def driver_jacket_picture(split, neck_front):
    """The driver's jacket: charcoal, with his white shirt and dark tie showing in a V from the
    collar down the chest, and the lapels' edges drawn dark."""
    on, _, _, points, normals = paint.texel_places(split, 1024)
    colour = np.tile(np.array(DRIVER_SUIT, float), (len(points), 1))
    bottom = float(fit.y(1.24))
    share = np.clip((points[:, 1] - bottom) / (neck_front - bottom), 0.0, 1.0)
    half = 0.065 * share * float(fit.width_share(1.40))
    front = (points[:, 2] > 0) & (normals[:, 2] > 0.2) & (points[:, 1] > bottom) & (points[:, 1] < neck_front + 0.01)
    shirt = front & (np.abs(points[:, 0]) < half)
    colour[shirt] = SHIRT_WHITE
    tie_half = 0.011 + 0.006 * (1 - share)
    colour[shirt & (np.abs(points[:, 0]) < tie_half)] = TIE
    edge = front & (np.abs(np.abs(points[:, 0]) - half) < 0.004) & (share > 0.02)
    colour[edge] = (30, 30, 32)
    return paint.picture_of(on, colour)


def driver(body, reference):
    """The driver on launch day: a dark suit over a white shirt and tie, white gloves and a
    peaked cap (takes/driver_b_113.png)."""
    parts, pair = footwear(body, "shoes")
    legs = plain.trousers(body, TROUSERS_DRAPE, pair)
    parts.append(flat("trousers", legs, DRIVER_SUIT))
    under = trimesh.Trimesh(legs[0], legs[1], process=False)
    shaped, made = plain.jacket(body, JACKET_DRAPE, under)
    points, part_faces, weights = shaped["cloth"]
    split = dress.split_part("driver_jacket", points, part_faces, weights)
    parts.append(dress.painted("jacket", split, driver_jacket_picture(split, made["neck_front"])))
    parts.append(flat("collar", shaped["collar"], DRIVER_SUIT, both_sides=True))
    parts.append(front_buttons(made, 2, 1.06, 1.16, (30, 30, 32)))
    parts.append(dress.flat("gloves", *skin.bare_hands(body), WHITE_GLOVE))
    head, head_points, eyes, _ = head_and_hair(body, reference)
    parts += head
    parts += cap_parts(head_points, eyes, {"cap_crown": DRIVER_SUIT, "cap_band": BLACK, "cap_peak": BLACK},
                       body.joint_names)
    return parts


def technician(body, reference):
    """A launch-day technician (takes/techs_a_5.png): the crew's work suit shape in white, white
    boots, a soft cap, and what they hold: the man a clipboard, the woman a spare glove."""
    paint.WORK_FLAT.update(work_boot_Left=TECH_WHITE, work_boot_Right=TECH_WHITE, work_belt=TECH_WHITE)
    parts = kit.work_suits(body, [{"cloth": TECH_WHITE, "piping": TECH_WHITE, "yoke": TECH_WHITE,
                                   "slit": (170, 166, 156)}])["work_own"]
    head, head_points, eyes, _ = head_and_hair(body, reference)
    parts += head
    parts += cap_parts(head_points, eyes, {"cap_crown": TECH_WHITE, "cap_band": TECH_WHITE, "cap_peak": TECH_WHITE},
                       body.joint_names, peaked=False)
    if WHO["prologue"] == "tech_man":
        for key, colour in (("clipboard", CLIPBOARD), ("paper", PAPER), ("clip", (160, 160, 164))):
            points, part_faces = plain.clipboard(body, "Left")[key]
            parts.append(dress.flat(key, points, part_faces, rigid(points, body.joint_names, "LeftHand"), colour))
    else:
        points, part_faces = held_glove(body)
        parts.append(dress.flat("glove", points, part_faces, rigid(points, body.joint_names, "RightHand"),
                                (206, 204, 198)))
    return parts


def held_glove(body):
    """A spare space-suit glove held in the right hand, fingers down: the mitt's block, thumb and
    cuff, as the space suit builds them, hung below the hand."""
    hand = body.joints["RightHand"]
    fore = body.joints["RightForeArm"]
    down = (hand - fore) / np.linalg.norm(hand - fore)
    axes = shapes.frame(down, [0.0, 0.0, 1.0])
    block = shapes.placed(shapes.rounded_box((0.07, 0.055, 0.035), 0.03, 8), hand + down * 0.14 + axes[:, 1] * 0.035, axes)
    cuff = shapes.placed(shapes.rounded_box((0.05, 0.06, 0.05), 0.03, 8), hand + down * 0.05 + axes[:, 1] * 0.035, axes)
    thumb = shapes.placed(shapes.rounded_box((0.035, 0.02, 0.02), 0.018, 6),
                          hand + down * 0.11 + axes[:, 1] * 0.085, shapes.frame(down * 0.7 + axes[:, 1] * 0.7, axes[:, 2]))
    mesh = shapes.joined([block, cuff, thumb])
    return np.asarray(mesh.vertices), np.asarray(mesh.faces)


DRESSERS = {"leader": leader, "guard": guard, "driver": driver, "tech_man": technician, "tech_woman": technician}


def outfits(body):
    """This prologue person's nodes: {"person": parts, "person_cap": parts}."""
    reference = kit.TemplateHead(faces.template_body())
    parts = DRESSERS[WHO["prologue"]](body, reference)
    print(f"{WHO['prologue']}: {sum(len(part.faces) for part in parts)} triangles over {len(parts)} surfaces", flush=True)
    nodes = {"person": [part for part in parts if not part.surface.startswith("cap_")],
             "person_cap": [part for part in parts if part.surface.startswith("cap_")]}
    # Somebody with no cap (the leader) has no cap node: a node with nothing in it is a mesh
    # Godot cannot draw.
    return {name: kept for name, kept in nodes.items() if kept}
