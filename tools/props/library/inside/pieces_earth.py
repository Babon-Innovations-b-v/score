"""Runs inside Blender: the Earth places' code-built pieces (world 1, 2026-10-07: the prologue's street, its square and
the launch view), in the kit frame of pieces.py and shapes.py, each part naming its library variant. Plain plates,
pipes and trims (sorter.PLAIN), and the fittings whose build shows every part their clean close-up shows
(data/library/fittings.json; the close-ups in the place job's pictures). pieces.py takes BUILDERS in.

Earth's surfaces: render in facade paint, concrete, wet asphalt and paving for the street; painted mild steel rusting
where the rain gets in (grille_paint) for cages, shutters and brackets; galvanized posts; enamel white boxes; lit
glass glowing (window_lit, sign_lit, lamp_lens) split off by make_kit as the piece's glowing part.
"""
import math

import shapes
import pieces

EDGE = 0.004


def plate(size, material, laid, name="plate", edge=0.006):
    """A plain plate the size of its box, with the openings the layout cut through it (a window's, a shop's, a
    door's): real holes, so what is set in them sits in a reveal of the plate's own depth."""
    wide, tall, deep = size
    slab = shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), material, name), edge)
    return pieces.with_openings([slab], laid, deep)


# --- the street's plain plates, pipes and trims ----------------------------------------------------------------------

def ground_asphalt(size, laid):
    """A stretch of the road: wet asphalt, its top the front."""
    return plate(size, "wet_asphalt", laid, "slab", 0.003)


def ground_paving(size, laid):
    """A stretch of pavement: concrete paving slabs in their grout (the paving_stone recipe draws the joints)."""
    return plate(size, "paving_stone", laid, "slab", 0.004)


def kerb_stone(size, laid):
    """A kerb stone: a concrete block with its top road edge rounded."""
    wide, tall, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "concrete", "kerb"),
                            0.02)]


def render_upper(size, laid):
    """A storey's bay of rendered wall, its window's opening cut through it, in its face's paint (laid `material`)."""
    return plate(size, laid.get("material", "facade_paint"), laid, "render")


def render_lower(size, laid):
    """A ground floor bay of rendered wall, any door's or window's opening cut through it."""
    return plate(size, laid.get("material", "facade_paint"), laid, "render")


def render_shop(size, laid):
    """A ground floor bay with its shop's opening: the render, and a concrete pier strip at its foot."""
    wide, tall, deep = size
    parts = plate(size, laid.get("material", "facade_paint"), laid, "render")
    parts += pieces.with_openings([shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 - 0.01),
                                                              (wide / 2, 0.25, deep / 2), "concrete", "plinth"),
                                                   0.004)], laid, deep + 0.02)
    return parts


def facade_band(size, laid):
    """The band along a floor: a render string course with a drip under its front edge."""
    wide, tall, deep = size
    paint = laid.get("material", "facade_paint")
    band = shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), paint, "band"), 0.008)
    drip = shapes.box((-wide / 2, -0.012, -deep / 2), (wide / 2, 0.0, -deep / 2 + 0.02), paint, "drip")
    return [band, drip]


# A parapet's concrete coping: how tall, and how far it stands out over the parapet's face (its drip edge).
COPING = (0.06, 0.04)


def parapet(size, laid):
    """A stretch of the parapet round a block's roof (tenement.gd's PARAPET), as the street sees it from below: the
    render wall in its face's paint (laid `material`), flush with the facade's plates under it, and the concrete
    coping along its top standing out over its face, a drip groove under that edge."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    high, out = COPING
    wall = shapes.bevelled(shapes.box((-wide / 2, 0.0, front + out), (wide / 2, tall - high, back),
                                      laid.get("material", "facade_paint"), "wall"), 0.006)
    coping = shapes.bevelled(shapes.box((-wide / 2, tall - high, front), (wide / 2, tall, back), "concrete",
                                        "coping"), 0.008)
    drip = shapes.box((-wide / 2, tall - high - 0.012, front), (wide / 2, tall - high, front + 0.015), "concrete",
                      "drip")
    return [wall, coping, drip]


def block_roof(size, laid):
    """A stretch of a block's flat roof: the concrete deck rendered and whitewashed (laid `material`), its top the
    front."""
    return plate(size, laid.get("material", "whitewash"), laid, "deck", 0.004)


def drainpipe(size, laid):
    """A drainpipe down a face: the grey pipe, a clamp to the wall every two metres, a shoe at its foot."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2
    parts = [shapes.cylinder((0.0, 0.0, 0.0), (0.0, tall, 0.0), radius * 0.8, "plastic_grey", 16, "pipe")]
    for at in [tall * (step + 0.5) / max(1, round(tall / 2.0)) for step in range(max(1, round(tall / 2.0)))]:
        parts.append(shapes.cylinder((0.0, at - 0.03, 0.0), (0.0, at + 0.03, 0.0), radius * 0.95, "galvanized_dull",
                                     16, "clamp"))
        parts.append(shapes.box((-0.012, at - 0.02, 0.0), (0.012, at + 0.02, deep / 2), "galvanized_dull", "clamp"))
    parts.append(shapes.cylinder((0.0, 0.0, 0.0), (0.0, 0.12, -radius * 0.6), radius * 0.85, "plastic_grey", 16,
                                 "shoe"))
    return parts


# --- the street's fittings -----------------------------------------------------------------------------------------

def bars_round(left, bottom, right, top, bar, depth_from, depth_to, material, name):
    """Four plain bars round a rectangle (a frame), `bar` wide, between two depths."""
    return [shapes.box((left, bottom, depth_from), (right, bottom + bar, depth_to), material, name),
            shapes.box((left, top - bar, depth_from), (right, top, depth_to), material, name),
            shapes.box((left, bottom + bar, depth_from), (left + bar, top - bar, depth_to), material, name),
            shapes.box((right - bar, bottom + bar, depth_from), (right, top - bar, depth_to), material, name)]


# How deep a tenement window's frame is, from its box's back (the frame, its casements and their panes).
WINDOW_FRAME_DEEP = 0.14


def tenement_window(size, laid, pane):
    """An old block's window, as its close-up shows it: a concrete sill along its foot standing out, a steel frame in
    the reveal, two side-hung casements under a fixed top light (a transom between), their panes (`pane`: dark
    glass, or lit from inside), and a handle on each casement. Plain bars, no bevels: a city's blocks hold
    thousands."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    sill_tall = 0.08
    parts = [shapes.box((-wide / 2, 0.0, front), (wide / 2, sill_tall, back), "concrete", "sill")]
    rim = 0.05
    # The frame takes the box's back WINDOW_FRAME_DEEP: a deeper box sets it further back behind its sill, so a
    # window laid deep into its plate's reveal shows the reveal and its sill standing out of the face.
    frame_front = back - WINDOW_FRAME_DEEP
    low, high = sill_tall, tall
    left_edge, right_edge = -wide / 2 + 0.01, wide / 2 - 0.01
    parts += bars_round(left_edge, low, right_edge, high, rim, frame_front, back, "grille_paint", "frame")
    transom = low + (high - low) * 0.72
    inner_left, inner_right = left_edge + rim, right_edge - rim
    parts.append(shapes.box((inner_left, transom - 0.025, frame_front), (inner_right, transom + 0.025, back - 0.01),
                            "grille_paint", "transom"))
    glass_at = frame_front + 0.03
    sash = 0.035
    for left, right in ((inner_left, -0.012), (0.012, inner_right)):
        parts += bars_round(left, low + rim, right, transom - 0.025, sash, frame_front - 0.01, glass_at,
                            "grille_paint", "casement")
        parts.append(shapes.box((left + sash, low + rim + sash, glass_at), (right - sash, transom - 0.025 - sash,
                                                                            glass_at + 0.006), pane, "glass"))
        handle_x = right - 0.06 if left < 0 else left + 0.06
        middle = (low + rim + transom) / 2
        parts.append(shapes.box((handle_x - 0.008, middle - 0.06, frame_front - 0.035),
                                (handle_x + 0.008, middle + 0.06, frame_front - 0.01), "bare_steel", "handle"))
    parts.append(shapes.box((inner_left, transom + 0.025, glass_at), (inner_right, high - rim, glass_at + 0.006),
                            pane, "glass"))
    return parts


def window_dark(size, laid):
    return tenement_window(size, laid, "glass")


def window_lit(size, laid):
    return tenement_window(size, laid, "window_lit")


def air_conditioner(size, laid, grille_bars=9, segments=32):
    """A window air conditioner's outdoor box, as its close-up shows it: the enamelled steel casing, the round fan
    behind its grille on the left of the front, louvres down the right, the steel brackets it stands on out from the
    wall, and its pipes into the wall."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    bracket = 0.045
    case_low = bracket
    case_back = back - 0.04
    parts = [shapes.bevelled(shapes.box((-wide / 2, case_low, front), (wide / 2, tall, case_back), "enamel_white",
                                        "casing"), 0.012)]
    fan_x, fan_y = -wide * 0.17, case_low + (tall - case_low) / 2
    radius = min(wide * 0.3, (tall - case_low) * 0.42)
    parts.append(shapes.cylinder((fan_x, fan_y, front), (fan_x, fan_y, front - 0.004), radius * 0.95, "rubber",
                                 segments, "fan"))
    parts.append(shapes.ring((fan_x, fan_y, front - 0.004), (fan_x, fan_y, front - 0.014), radius, radius - 0.018,
                             "bare_steel", segments, "fan_grille"))
    half = grille_bars // 2
    for step in range(-half, half + 1):
        y = fan_y + step * radius / (half + 1)
        reach = math.sqrt(max(radius ** 2 - (y - fan_y) ** 2, 0.0)) - 0.01
        if reach > 0.02:
            parts.append(shapes.cylinder((fan_x - reach, y, front - 0.01), (fan_x + reach, y, front - 0.01), 0.003,
                                         "bare_steel", 6, "fan_grille"))
    louvre_left = fan_x + radius + 0.06
    for step in range(9):
        y = case_low + 0.06 + step * (tall - case_low - 0.12) / 8
        parts.append(pieces.tilted(shapes.box((louvre_left, y - 0.008, front - 0.012), (wide / 2 - 0.04, y + 0.008,
                                                                                          front + 0.004),
                                              "enamel_white", "louvre"), (y, front), 30.0))
    for x in (-wide * 0.33, wide * 0.33):
        parts.append(shapes.box((x - 0.02, 0.0, front + 0.02), (x + 0.02, bracket, back), "grille_paint", "bracket"))
        parts.append(shapes.box((x - 0.015, -0.18, back - 0.03), (x + 0.015, bracket, back), "grille_paint",
                                "bracket"))
    for offset in (0.0, 0.035):
        y = case_low + 0.08 + offset
        parts.append(shapes.cylinder((wide / 2 - 0.02, y, front + 0.1), (wide / 2 + 0.03, y, front + 0.1), 0.011,
                                     "cable_black", 10, "pipe"))
        parts.append(shapes.cylinder((wide / 2 + 0.03, y, front + 0.1), (wide / 2 + 0.03, y, back), 0.011,
                                     "cable_black", 10, "pipe"))
    return parts



def ac_unit(size, laid):
    return air_conditioner(size, laid)

def window_cage(size, laid):
    """A steel window cage, as its close-up shows it: a box of upright bars out from the wall round the window, a
    frame round its front, side bars back to the wall, a flat top and a shelf at its foot, and the brackets that fix
    it to the wall."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    bar = 0.018
    parts = bars_round(-wide / 2, 0.0, wide / 2, tall, 0.035, front, front + 0.03, "grille_paint", "frame")
    count = 9
    for step in range(1, count):
        x = -wide / 2 + wide * step / count
        parts.append(shapes.box((x - bar / 2, 0.03, front + 0.006), (x + bar / 2, tall - 0.03, front + 0.024),
                                "grille_paint", "bars"))
    for x in (-wide / 2 + 0.017, wide / 2 - 0.017):
        for y in (0.3, tall / 2, tall - 0.3):
            parts.append(shapes.box((x - bar / 2, y - bar / 2, front + 0.03), (x + bar / 2, y + bar / 2, back),
                                    "grille_paint", "sides"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2 - 0.02, tall, front - 0.02), (wide / 2 + 0.02, tall + 0.02,
                                                                                       back), "grille_paint", "top"),
                                 0.003))
    parts.append(shapes.bevelled(shapes.box((-wide / 2, 0.0, front + 0.03), (wide / 2, 0.025, back),
                                            "grille_paint", "shelf"), 0.003))
    for x in (-wide / 2 + 0.03, wide / 2 - 0.03):
        for y in (0.05, tall - 0.05):
            parts.append(shapes.box((x - 0.025, y - 0.025, back - 0.008), (x + 0.025, y + 0.025, back),
                                    "galvanized_dull", "brackets"))
    return parts


def shop_shutter(size, laid):
    """A roller shutter pulled down, as its close-up shows it: the slatted curtain, the roll box over it, the two
    guide rails it runs in, the bottom rail with its handle, and a padlock at its foot."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    box_tall = 0.3
    guide = 0.07
    curtain_top = tall - box_tall
    paint = laid.get("material", "grille_paint")
    parts = [shapes.bevelled(shapes.box((-wide / 2, curtain_top, front), (wide / 2, tall, back), paint, "roll_box"),
                             0.01)]
    for x in (-wide / 2 + guide / 2, wide / 2 - guide / 2):
        parts.append(shapes.bevelled(shapes.box((x - guide / 2, 0.0, front + 0.06), (x + guide / 2, curtain_top,
                                                                                      back), "galvanized_dull",
                                                "guide"), 0.003))
    pitch = 0.075
    slats = int((curtain_top - 0.08) / pitch)
    for step in range(slats):
        y = 0.08 + step * pitch
        parts.append(shapes.box((-wide / 2 + guide, y + 0.004, front + 0.08),
                                (wide / 2 - guide, y + pitch - 0.004, front + 0.1), paint, "curtain"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + guide, 0.0, front + 0.065), (wide / 2 - guide, 0.08,
                                                                                       front + 0.11), "gate_grey",
                                            "bottom_bar"), 0.005))
    parts.append(shapes.box((-0.12, 0.03, front + 0.035), (0.12, 0.05, front + 0.065), "bare_steel", "handle"))
    for x in (-0.12, 0.12):
        parts.append(shapes.box((x - 0.01, 0.03, front + 0.035), (x + 0.01, 0.05, front + 0.065), "bare_steel",
                                "handle"))
    lock_x = wide / 2 - guide - 0.12
    parts.append(shapes.bevelled(shapes.box((lock_x - 0.03, 0.0, front + 0.03), (lock_x + 0.03, 0.06, front + 0.06),
                                            "bare_steel", "padlock"), 0.004))
    parts.append(shapes.ring((lock_x, 0.08, front + 0.045), (lock_x, 0.08, front + 0.05), 0.022, 0.014,
                             "bare_steel", 16, "padlock"))
    return parts


def lit_front(size, laid, door_side):
    """A glazed shopfront lit from inside (the tea restaurant's, an open shop's), as the close-up shows it: an
    aluminium frame of posts, a head and a transom, lit glass, a glass door with its handle at `door_side`, a tiled
    stall riser under the windows and a step at the door."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    riser = 0.45
    post = 0.06
    door_wide = 0.9
    door_left = wide / 2 - door_wide - post if door_side > 0 else -wide / 2 + post
    parts = [shapes.bevelled(pieces.rounded_ring((-wide / 2, 0.0), (wide / 2, tall), 0.003, post, front + 0.08,
                                                 front + 0.16, "galvanized_dull", "frame"), 0.002)]
    transom = tall - 0.45
    parts.append(shapes.box((-wide / 2 + post, transom - 0.03, front + 0.08), (wide / 2 - post, transom + 0.03,
                                                                                front + 0.16), "galvanized_dull",
                            "frame"))
    jamb = door_left - post if door_side > 0 else door_left + door_wide
    parts.append(shapes.box((jamb, 0.0, front + 0.08), (jamb + post, transom, front + 0.16), "galvanized_dull",
                            "frame"))
    glass_z = front + 0.12
    window_left, window_right = (-wide / 2 + post, jamb) if door_side > 0 else (jamb + post, wide / 2 - post)
    parts.append(shapes.bevelled(shapes.box((window_left, 0.0, front + 0.06), (window_right, riser, back),
                                            "wall_tile_white", "riser"), 0.004))
    parts.append(shapes.box((window_left, riser, glass_z), (window_right, transom - 0.03, glass_z + 0.008),
                            "window_lit", "glass"))
    parts.append(shapes.box((-wide / 2 + post, transom + 0.03, glass_z), (wide / 2 - post, tall - post,
                                                                          glass_z + 0.008), "window_lit", "glass"))
    door_low = 0.0
    parts.append(shapes.bevelled(pieces.rounded_ring((door_left, door_low), (door_left + door_wide, transom - 0.03),
                                                     0.003, 0.07, front + 0.09, front + 0.15, "galvanized_dull",
                                                     "door"), 0.002))
    parts.append(shapes.box((door_left + 0.07, door_low + 0.07, glass_z), (door_left + door_wide - 0.07,
                                                                           transom - 0.1, glass_z + 0.008),
                            "window_lit", "glass"))
    handle_x = door_left + 0.12 if door_side > 0 else door_left + door_wide - 0.12
    parts.append(shapes.cylinder((handle_x, 0.85, front + 0.04), (handle_x, 1.25, front + 0.04), 0.012, "bare_steel",
                                 10, "handle"))
    for y in (0.9, 1.2):
        parts.append(shapes.cylinder((handle_x, y, front + 0.04), (handle_x, y, front + 0.09), 0.008, "bare_steel", 8,
                                     "handle"))
    parts.append(shapes.bevelled(shapes.box((door_left - 0.05, -0.0, front), (door_left + door_wide + 0.05, 0.03,
                                                                              front + 0.16), "concrete", "step"),
                                 0.006))
    return parts


def tea_front(size, laid):
    return lit_front(size, laid, 1.0)


def shop_open(size, laid):
    return lit_front(size, laid, -1.0)


def shop_sign(size, laid):
    """A shop's sign over its door, as its close-up shows it: a flat board in a narrow steel frame, its words printed
    across it (the layout's `label`), and two lamps on arms over it, out from the wall."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    board_tall = tall * 0.72
    board_front = back - 0.08
    parts = [shapes.bevelled(shapes.box((-wide / 2 + 0.025, 0.025, board_front), (wide / 2 - 0.025,
                                                                                  board_tall - 0.025, back),
                                        "enamel_white", "board"), 0.003),
             shapes.bevelled(pieces.rounded_ring((-wide / 2, 0.0), (wide / 2, board_tall), 0.004, 0.025,
                                                 board_front - 0.01, back, "galvanized_dull", "frame"), 0.002)]
    parts.append(pieces.label(0.0, board_tall / 2, wide - 0.12, board_tall - 0.1, board_front, laid.get("label",
                                                                                                        "sign_store"),
                              0.0, 0.005, "label"))
    for x in (-wide * 0.3, wide * 0.3):
        parts.append(shapes.cylinder((x, board_tall, back - 0.02), (x, tall - 0.04, back - 0.02), 0.01,
                                     "post_dark", 8, "arm"))
        parts.append(shapes.cylinder((x, tall - 0.04, back - 0.02), (x, tall - 0.04, front + 0.06), 0.01, "post_dark",
                                     8, "arm"))
        parts.append(shapes.cylinder((x, tall - 0.02, front + 0.06), (x, tall - 0.1, front + 0.03), 0.045,
                                     "post_dark", 16, "lamp_shade"))
        parts.append(shapes.cylinder((x, tall - 0.1, front + 0.03), (x, tall - 0.105, front + 0.03), 0.04,
                                     "lamp_lens", 16, "lamp_shade"))
    return parts


def neon_sign(size, laid):
    """A neon sign hung out over a shop, as its close-up shows it: a dark box in a steel frame, a glowing neon tube
    round its edge, its words in neon (the layout's `label`, a lit print) on its face, and the two rods it hangs
    from to the wall."""
    wide, full, deep = size
    front, back = -deep / 2, deep / 2
    box_front = front + 0.04
    hang = 0.15
    tall = full - hang
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.01, box_front), (wide / 2, tall - 0.01, back - 0.05),
                                        "post_dark", "box"), 0.006),
             shapes.bevelled(pieces.rounded_ring((-wide / 2, 0.0), (wide / 2, tall), 0.01, 0.03, box_front - 0.01,
                                                 box_front + 0.03, "galvanized_dull", "frame"), 0.002)]
    inset = 0.07
    tube = 0.009
    corners = [(-wide / 2 + inset, inset), (wide / 2 - inset, inset), (wide / 2 - inset, tall - inset),
               (-wide / 2 + inset, tall - inset)]
    for at in range(4):
        (x0, y0), (x1, y1) = corners[at], corners[(at + 1) % 4]
        parts.append(shapes.cylinder((x0, y0, box_front - 0.02), (x1, y1, box_front - 0.02), tube, "sign_lit", 8,
                                     "neon"))
    parts.append(pieces.label(0.0, tall / 2, wide - 2 * inset - 0.08, tall - 2 * inset - 0.06, box_front,
                              laid.get("label", "sign_tea_restaurant"), 0.0, 0.005, "label"))
    for x in (-wide * 0.35, wide * 0.35):
        parts.append(shapes.cylinder((x, tall - 0.01, (box_front + back) / 2), (x, full - 0.012,
                                                                               (box_front + back) / 2), 0.012,
                                     "galvanized_dull", 8, "hanger"))
        parts.append(shapes.cylinder((x, full - 0.012, (box_front + back) / 2), (x, full - 0.012, back), 0.012,
                                     "galvanized_dull", 8, "hanger"))
    return parts


def door_canopy(size, laid):
    """A concrete canopy over a block's door, as its close-up shows it: the slab out from the wall, a drip edge
    round its front, two steel brackets under it to the wall, and a tube lamp in its fitting under it."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    slab_low = tall - 0.12
    parts = [shapes.bevelled(shapes.box((-wide / 2, slab_low, front), (wide / 2, tall, back), "concrete", "slab"),
                             0.01),
             shapes.bevelled(shapes.box((-wide / 2, slab_low - 0.04, front), (wide / 2, slab_low, front + 0.04),
                                        "concrete", "drip"), 0.004)]
    for x in (-wide / 2 + 0.12, wide / 2 - 0.12):
        parts.append(shapes.box((x - 0.015, slab_low - 0.04, front + 0.08), (x + 0.015, slab_low, back),
                                "grille_paint", "bracket"))
        parts.append(shapes.cylinder((x, slab_low - 0.02, front + 0.1), (x, slab_low - (back - front) * 0.8,
                                                                         back - 0.01), 0.014, "grille_paint", 8,
                                     "bracket"))
    parts.append(shapes.bevelled(shapes.box((-wide * 0.3, slab_low - 0.06, -0.06), (wide * 0.3, slab_low, 0.06),
                                            "plastic_white", "lamp"), 0.004))
    parts.append(shapes.box((-wide * 0.28, slab_low - 0.065, -0.04), (wide * 0.28, slab_low - 0.06, 0.04),
                            "lamp_lens", "lamp"))
    return parts


def street_lamp(size, laid):
    """A street lamp, as its close-up shows it: a square base plate with its bolts, a tapered pole with a service door
    near its foot, a curved arm out over the road and the flat lamp head on it with its glass lens under it. Its
    pole stands at the box's -x end, its arm reaching toward +x."""
    wide, tall, deep = size
    pole_x = -wide / 2 + 0.12
    parts = [shapes.bevelled(shapes.box((pole_x - 0.12, 0.0, -0.12), (pole_x + 0.12, 0.025, 0.12), "galvanized_dull",
                                        "base_plate"), 0.004)]
    for dx in (-0.09, 0.09):
        for dz in (-0.09, 0.09):
            parts.append(shapes.cylinder((pole_x + dx, 0.025, dz), (pole_x + dx, 0.045, dz), 0.012, "bare_steel", 8,
                                         "base_plate"))
    pole_top = tall - 0.35
    sections = 6
    for step in range(sections):
        y0, y1 = pole_top * step / sections, pole_top * (step + 1) / sections
        radius = 0.075 - 0.035 * (step + 0.5) / sections
        parts.append(shapes.cylinder((pole_x, y0 + 0.02, 0.0), (pole_x, y1 + 0.02, 0.0), radius, "galvanized_dull",
                                     20, "pole"))
    parts.append(shapes.bevelled(shapes.box((pole_x - 0.035, 0.45, -0.082), (pole_x + 0.035, 0.75, -0.06),
                                            "galvanized_dull", "door"), 0.003))
    arm_radius = 0.03
    points = [(pole_x, pole_top)]
    for step in range(1, 7):
        angle = math.radians(90 * step / 6)
        points.append((pole_x + 0.3 * (1 - math.cos(angle)), pole_top + 0.3 * math.sin(angle)))
    head_x = wide / 2 - 0.3
    points.append((head_x - 0.2, pole_top + 0.3))
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        parts.append(shapes.cylinder((x0, y0, 0.0), (x1, y1, 0.0), arm_radius, "galvanized_dull", 12, "arm"))
    head_low = pole_top + 0.22
    parts.append(shapes.bevelled(shapes.box((head_x - 0.3, head_low, -0.14), (head_x + 0.3, head_low + 0.12, 0.14),
                                            "gate_grey", "lamp_head"), 0.03))
    parts.append(shapes.box((head_x - 0.24, head_low - 0.02, -0.1), (head_x + 0.24, head_low, 0.1), "lamp_lens",
                            "lens"))
    return parts


def notice_case(size, laid):
    """A free-standing neighbourhood notice board, as its close-up shows it: a shallow wooden case under a small
    roof, its notices pinned on the board inside, on two steel posts. Its glazing is left out: glass in the ink look
    is a dark pane that hid the notices from every side."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    case_low = tall * 0.48
    case_top = tall - 0.1
    post = 0.05
    parts = []
    for x in (-wide / 2 + 0.12, wide / 2 - 0.12):
        parts.append(shapes.bevelled(shapes.box((x - post / 2, 0.0, -post / 2), (x + post / 2, case_low + 0.2,
                                                                                post / 2), "post_dark", "posts"),
                                     0.004))
    parts.append(shapes.bevelled(pieces.rounded_ring((-wide / 2, case_low), (wide / 2, case_top), 0.006, 0.06,
                                                     front + 0.01, back, "varnished_wood", "case"), 0.004))
    parts.append(shapes.box((-wide / 2 + 0.06, case_low + 0.06, back - 0.03), (wide / 2 - 0.06, case_top - 0.06,
                                                                                back - 0.01), "varnished_wood",
                            "board"))
    parts.append(pieces.label(0.0, (case_low + case_top) / 2, wide - 0.36, case_top - case_low - 0.4, back - 0.03,
                              "notices_street", 0.0, 0.005, "sheet"))
    roof = [(-wide / 2 - 0.05, case_top), (wide / 2 + 0.05, case_top), (wide / 2 + 0.05, case_top + 0.04),
            (0.0, tall), (-wide / 2 - 0.05, case_top + 0.04)]
    parts.append(shapes.bevelled(shapes.prism(roof, front - 0.04, back + 0.02, "varnished_wood", "roof"), 0.004))
    return parts


def poster_stand(size, laid):
    """A steel A-frame poster stand, as its close-up shows it: two frames hinged at the top, the launch poster in the
    front one (its clear cover left out: glass in the ink look is a dark pane over the poster), the legs it stands on
    and the brace that holds them apart."""
    wide, tall, deep = size
    lean = deep / 2 - 0.03
    rim = 0.03
    parts = []
    for side, name in ((-1.0, "frame"), (1.0, "frame")):
        outline_low, outline_high = (-wide / 2, 0.06), (wide / 2, tall - 0.02)
        frame = pieces.rounded_ring(outline_low, outline_high, 0.006, rim, -0.012, 0.012, "grille_paint", name)
        parts.append(_leaned(shapes.bevelled(frame, 0.002), side * lean, tall))
        if side < 0:
            print_on = pieces.label(0.0, tall / 2 + 0.03, wide - 2 * rim - 0.02, tall - 0.08 - 2 * rim, 0.004,
                                    laid.get("label", "poster_launch"), 0.0, 0.005, "poster")
            parts.append(_leaned(print_on, side * lean, tall))
    for x in (-wide / 2 + 0.015, wide / 2 - 0.015):
        for side in (-1.0, 1.0):
            parts.append(shapes.cylinder((x, 0.0, side * lean), (x, 0.08, side * lean * 0.97), 0.012, "rubber", 8,
                                         "leg"))
        parts.append(shapes.cylinder((x, tall * 0.35, -lean * 0.65), (x, tall * 0.35, lean * 0.65), 0.006,
                                     "bare_steel", 6, "brace"))
        parts.append(shapes.cylinder((x - 0.01, tall - 0.01, 0.0), (x + 0.01, tall - 0.01, 0.0), 0.014,
                                     "bare_steel", 10, "hinge"))
    return parts


def _leaned(part, foot_z, tall):
    """A part drawn standing upright at z = 0, leaned so its foot stands at `foot_z` and its top at z = 0 (one side of
    an A-frame)."""
    from mathutils import Matrix
    angle = math.atan2(foot_z, tall)
    # Turn about the kit's x axis through the top (y = tall): Blender's x axis through Blender z = tall.
    pivot = shapes.to_blender((0.0, tall, 0.0))
    part.data.transform(Matrix.Translation(pivot) @ Matrix.Rotation(angle, 4, "X") @ Matrix.Translation(-pivot))
    return part


# --- the square and the launch view (seen from the balcony: `far_` kinds take the distant texel density) ------------

def far_paving(size, laid):
    """A stretch of the square's paving: pale stone slabs in their joints."""
    return plate(size, "square_paving", laid, "slab", 0.01)


def far_terrace(size, laid):
    """One of the square's terraces: a block of concrete, paved on top."""
    wide, tall, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 + 0.04), (wide / 2, tall, deep / 2), "concrete",
                                       "block"), 0.02),
            shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, -deep / 2 + 0.04), "square_paving", "paving")]


def far_road(size, laid):
    """A stretch of the roads round the square: wet asphalt."""
    return plate(size, "wet_asphalt", laid, "slab", 0.01)


def far_promenade(size, laid):
    """A stretch of the harbour promenade: concrete paving."""
    return plate(size, "paving_stone", laid, "slab", 0.01)


def far_pad(size, laid):
    """A stretch of the launch pad's apron on the water: concrete."""
    return plate(size, "concrete", laid, "slab", 0.03)


def bay_balcony_slab(size, laid):
    """A balcony's concrete slab with its drip edge."""
    return plate(size, "concrete", laid, "slab", 0.01)


def far_cable(size, laid):
    """A length of the cable the lanterns hang from."""
    wide, tall, deep = size
    return [shapes.cylinder((0.0, 0.0, 0.0), (0.0, tall, 0.0), min(wide, deep) / 2, "cable_black", 6, "cable")]


def rail_run(size, material, bars):
    """A run of rail: a post at each end, a top rail, a middle rail, and `bars` upright bars between (a trim)."""
    wide, tall, deep = size
    parts = []
    for x in (-wide / 2 + 0.03, wide / 2 - 0.03):
        parts.append(shapes.box((x - 0.03, 0.0, -0.03), (x + 0.03, tall, 0.03), material, "post"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2, tall - 0.05, -0.03), (wide / 2, tall, 0.03), material, "rail"),
                                 0.005))
    parts.append(shapes.box((-wide / 2, tall / 2 - 0.02, -0.02), (wide / 2, tall / 2 + 0.02, 0.02), material, "rail"))
    for step in range(1, bars + 1):
        x = -wide / 2 + wide * step / (bars + 1)
        parts.append(shapes.cylinder((x, 0.06, 0.0), (x, tall - 0.05, 0.0), 0.011, material, 6, "bar"))
    parts.append(shapes.box((-wide / 2, 0.05, -0.02), (wide / 2, 0.09, 0.02), material, "rail"))
    return parts


def far_promenade_rail(size, laid):
    """A run of the harbour promenade's railing: steel posts, a top and two lower rails."""
    return rail_run(size, "rail_green", 0)


def bay_balcony_rail(size, laid):
    """A run of a balcony's steel balustrade: posts, top and middle rails and upright bars."""
    return rail_run(size, "grille_paint", max(2, round(size[0] / 0.14)))


def far_stage(size, laid):
    """The rally stage, as its close-up shows it: a dark deck as high as a man and a half, a red skirt round its front
    and its sides, and steps up its -x end."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    parts = [shapes.bevelled(shapes.box((-wide / 2, tall - 0.12, front), (wide / 2, tall, back), "post_dark", "deck"),
                             0.02),
             shapes.box((-wide / 2 + 0.2, 0.0, front + 0.2), (wide / 2 - 0.2, tall - 0.12, back), "post_dark",
                        "frame")]
    pleats = int(wide / 0.4)
    for step in range(pleats):
        x0 = -wide / 2 + wide * step / pleats
        x1 = x0 + wide / pleats
        parts.append(shapes.prism([(x0, 0.0), (x1, 0.0), (x1, tall - 0.12), (x0, tall - 0.12)],
                                  front - 0.04 * (step % 2), front + 0.02, "flag_red", "skirt"))
    for x in (-wide / 2, wide / 2):
        parts.append(shapes.box((x - 0.02, 0.0, front), (x + 0.02, tall - 0.12, back), "flag_red", "skirt"))
    rise, tread, steps_wide = tall / 7, 0.45, 2.0
    for step in range(6):
        high = tall - rise * (step + 1)
        x_from = -wide / 2 - tread * (step + 1)
        parts.append(shapes.bevelled(shapes.box((x_from, 0.0, front + deep * 0.3 - steps_wide / 2),
                                                (x_from + tread, high, front + deep * 0.3 + steps_wide / 2),
                                                "post_dark", "steps"), 0.006))
    return parts


def far_backdrop(size, laid):
    """The backdrop behind the stage, as the close-up shows it: a red wall in a dark frame, red curtains hung down its
    two ends, and the first sign across its top (`label`)."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    parts = [shapes.box((-wide / 2, 0.0, front + 0.1), (wide / 2, tall, back), "flag_red", "wall"),
             shapes.bevelled(pieces.rounded_ring((-wide / 2 - 0.2, 0.0), (wide / 2 + 0.2, tall + 0.2), 0.02, 0.2,
                                                 front, back, "post_dark", "frame"), 0.01)]
    for side in (-1.0, 1.0):
        x_from, x_to = side * (wide / 2 - 2.6), side * (wide / 2 - 0.2)
        low, high = min(x_from, x_to), max(x_from, x_to)
        folds = 10
        for step in range(folds):
            x0 = low + (high - low) * step / folds
            parts.append(shapes.cylinder((x0 + (high - low) / folds / 2, 0.0, front + 0.05),
                                         (x0 + (high - low) / folds / 2, tall - 0.4, front + 0.05),
                                         (high - low) / folds / 2 + 0.02, "flag_red", 10, "curtain"))
    parts.append(pieces.label(0.0, tall - 1.8, wide * 0.7, 2.2, front + 0.1, laid.get("label", "banner_first"), 0.0,
                              0.02, "label"))
    return parts


def far_podium(size, laid):
    """The podium the leader stands on: a low platform draped in red to the deck."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, tall - 0.08, -deep / 2), (wide / 2, tall, deep / 2), "post_dark",
                                        "top"), 0.01)]
    folds = 14
    for step in range(folds):
        x = -wide / 2 + wide * (step + 0.5) / folds
        parts.append(shapes.cylinder((x, 0.0, -deep / 2 + 0.06), (x, tall - 0.08, -deep / 2 + 0.06), wide / folds / 2,
                                     "flag_red", 8, "drape"))
    parts.append(shapes.box((-wide / 2 + 0.05, 0.0, -deep / 2 + 0.06), (wide / 2 - 0.05, tall - 0.08, deep / 2),
                            "flag_red", "drape"))
    return parts


def far_lectern(size, laid):
    """The lectern: a slanted reading top on a dark column with a gold emblem on its front."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide * 0.3, 0.0, -deep * 0.3), (wide * 0.3, tall - 0.15, deep * 0.3),
                                        "varnished_wood", "column"), 0.01),
             shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, 0.05, deep / 2), "varnished_wood",
                                        "foot"), 0.005)]
    top = shapes.bevelled(shapes.box((-wide / 2, tall - 0.15, -deep / 2), (wide / 2, tall - 0.08, deep / 2),
                                     "varnished_wood", "top"), 0.005)
    parts.append(pieces.tilted(top, (tall - 0.12, 0.0), -15.0))
    parts.append(shapes.cylinder((0.0, tall * 0.6, -deep * 0.3), (0.0, tall * 0.6, -deep * 0.3 - 0.01), 0.1,
                                 "anodized_gold", 24, "emblem"))
    return parts


def far_banner(size, laid):
    """A red banner down a steel pole either side of the stage, its words read down it (`label`)."""
    wide, tall, deep = size
    cloth_top, cloth_low = tall - 0.4, tall - 0.4 - 7.0
    parts = [shapes.cylinder((-wide / 2 - 0.08, 0.0, 0.0), (-wide / 2 - 0.08, tall, 0.0), 0.08, "galvanized_dull", 12,
                             "pole"),
             shapes.cylinder((-wide / 2 - 0.08, cloth_top + 0.05, 0.0), (wide / 2, cloth_top + 0.05, 0.0), 0.03,
                             "galvanized_dull", 8, "arm"),
             shapes.box((-wide / 2, cloth_low, -0.02), (wide / 2, cloth_top, 0.02), "flag_red", "cloth")]
    parts.append(pieces.label(0.0, (cloth_top + cloth_low) / 2, wide * 0.8, 6.6, -0.02, laid.get("label",
                                                                                               "banner_second"),
                              0.0, 0.005, "label"))
    return parts


# A banner held up in the crowd on two poles (the square's concept K06): its cloth across the poles' tops, clear over
# the heads of the people holding it, its words printed at the picture's own proportions (four wide to one tall).
CROWD_CLOTH = 0.5
CROWD_POLE = 0.025
CROWD_WORDS_SHAPE = 4.0


def crowd_banner(size, laid):
    """A red cloth banner held up in the crowd between two steel poles, its gold words printed across it (`label`)."""
    wide, tall, deep = size
    pole_x = wide / 2 - CROWD_POLE
    cloth_top, cloth_low = tall - 0.05, tall - 0.05 - CROWD_CLOTH
    parts = [shapes.cylinder((side * pole_x, 0.0, 0.0), (side * pole_x, tall, 0.0), CROWD_POLE, "galvanized_dull", 10,
                             "poles") for side in (-1.0, 1.0)]
    parts.append(shapes.box((-pole_x + CROWD_POLE, cloth_low, -0.01), (pole_x - CROWD_POLE, cloth_top, 0.01), "flag_red",
                            "cloth"))
    words_tall = CROWD_CLOTH * 0.8
    parts.append(pieces.label(0.0, (cloth_top + cloth_low) / 2, min((wide - 4 * CROWD_POLE) * 0.9,
                                                                    words_tall * CROWD_WORDS_SHAPE),
                              words_tall, -0.01, laid.get("label", "banner_crowd"), 0.0, 0.005, "label"))
    return parts


def lattice_mast(wide, tall, deep, material, spike, top_width_share=1.0):
    """A square steel lattice mast: four legs, a horizontal ring and crossed braces every bay, tapering to
    `top_width_share` of its foot at the top, a spike over it."""
    parts = []
    bay = max(1.5, wide * 1.2)
    bays = max(1, int(tall / bay))

    def corner(index, y):
        share = 1.0 - (1.0 - top_width_share) * y / tall
        sx = (1 if index in (1, 2) else -1) * wide / 2 * share
        sz = (1 if index in (2, 3) else -1) * deep / 2 * share
        return (sx, y, sz)

    for index in range(4):
        parts.append(shapes.cylinder(corner(index, 0.0), corner(index, tall), wide * 0.03, material, 6, "legs"))
    for step in range(bays + 1):
        y = tall * step / bays
        for index in range(4):
            parts.append(shapes.cylinder(corner(index, y), corner((index + 1) % 4, y), wide * 0.015, material, 4,
                                         "braces"))
        if step < bays:
            y1 = tall * (step + 1) / bays
            for index in range(4):
                parts.append(shapes.cylinder(corner(index, y), corner((index + 1) % 4, y1), wide * 0.012, material, 4,
                                             "braces"))
    if spike:
        parts.append(shapes.cylinder((0.0, tall, 0.0), (0.0, tall + spike, 0.0), wide * 0.03, material, 6, "spike"))
    return parts


def far_floodlight_tower(size, laid):
    """A floodlight tower, as its close-up shows it: a steel lattice mast, a platform with a rail on top, a bank of
    square floodlights on a frame facing front, and a ladder up its side."""
    wide, tall, deep = size
    mast_top = tall - 3.0
    parts = lattice_mast(1.2, mast_top, 1.2, "galvanized_dull", 0.0, 0.8)
    parts.append(shapes.box((-wide / 2, mast_top, -deep / 2), (wide / 2, mast_top + 0.1, deep / 2), "galvanized_dull",
                            "platform"))
    parts.append(shapes.box((-wide / 2, mast_top + 0.1, -deep / 2 + 0.6), (wide / 2, mast_top + 2.8, -deep / 2 + 0.7),
                            "galvanized_dull", "frame"))
    for row in range(2):
        for column in range(3):
            x = -wide / 2 + wide * (column + 0.5) / 3
            y = mast_top + 0.8 + row * 1.1
            parts.append(shapes.bevelled(shapes.box((x - 0.45, y - 0.45, -deep / 2 + 0.15),
                                                    (x + 0.45, y + 0.45, -deep / 2 + 0.6), "gate_grey", "floodlight"),
                                         0.02))
            parts.append(shapes.box((x - 0.38, y - 0.38, -deep / 2 + 0.12), (x + 0.38, y + 0.38, -deep / 2 + 0.15),
                                    "floodlight_lens", "lens"))
    parts.append(shapes.box((0.62, 0.0, -0.25), (0.66, mast_top, -0.22), "galvanized_dull", "ladder"))
    parts.append(shapes.box((0.62, 0.0, 0.22), (0.66, mast_top, 0.25), "galvanized_dull", "ladder"))
    for step in range(int(mast_top / 0.6)):
        y = 0.3 + step * 0.6
        parts.append(shapes.box((0.62, y, -0.22), (0.66, y + 0.03, 0.22), "galvanized_dull", "ladder"))
    return parts


def far_square_lamp(size, laid):
    """A lamp post round the square, as its close-up shows it: a slim dark post on a base, one short arm at its top
    and a flat lamp head with its lens under it; its post at the box's -x end, its arm toward +x."""
    wide, tall, deep = size
    pole_x = -wide / 2 + 0.1
    head_x = wide / 2 - 0.35
    parts = [shapes.cylinder((pole_x, 0.0, 0.0), (pole_x, 0.6, 0.0), 0.11, "post_dark", 12, "base"),
             shapes.cylinder((pole_x, 0.0, 0.0), (pole_x, tall - 0.2, 0.0), 0.06, "post_dark", 12, "post"),
             shapes.cylinder((pole_x, tall - 0.25, 0.0), (head_x, tall - 0.2, 0.0), 0.035, "post_dark", 8, "arm"),
             shapes.bevelled(shapes.box((head_x - 0.35, tall - 0.3, -0.18), (head_x + 0.35, tall - 0.15, 0.18),
                                        "post_dark", "head"), 0.02),
             shapes.box((head_x - 0.3, tall - 0.32, -0.14), (head_x + 0.3, tall - 0.3, 0.14), "lamp_lens", "lens")]
    return parts


def far_lantern(size, laid):
    """A red paper lantern, as its close-up shows it: a round ribbed body, a gold cap top and bottom, the hook it
    hangs from and a red tassel under it."""
    wide, tall, deep = size
    radius = wide / 2
    middle = tall * 0.55
    parts = []
    ribs = 8
    for step in range(ribs):
        y0 = middle - radius * 0.85 + radius * 1.7 * step / ribs
        y1 = y0 + radius * 1.7 / ribs
        mid = (y0 + y1) / 2
        r = radius * (1 - ((mid - middle) / radius) ** 2) ** 0.5
        parts.append(shapes.cylinder((0.0, y0, 0.0), (0.0, y1, 0.0), r, "lantern_glow", 16, "body"))
    for y in (middle - radius * 0.9, middle + radius * 0.85):
        parts.append(shapes.cylinder((0.0, y - 0.025, 0.0), (0.0, y + 0.025, 0.0), radius * 0.45, "anodized_gold", 16, "cap"))
    parts.append(shapes.cylinder((0.0, middle + radius * 0.87, 0.0), (0.0, tall, 0.0), 0.008, "anodized_gold", 6, "hook"))
    parts.append(shapes.cylinder((0.0, 0.0, 0.0), (0.0, middle - radius * 0.92, 0.0), 0.02, "flag_red", 8, "tassel"))
    return parts


def far_neon_column(size, laid):
    """A neon sign hung out from a block's face, read down it: a dark board in a steel frame, a neon tube round the
    edge of both faces, its words in neon on its front (`label`, the face the balcony sees), on an arm to the wall at
    its top."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2 + 0.15, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "post_dark",
                                        "board"), 0.01)]
    for z in (-deep / 2, deep / 2):
        parts.append(shapes.box((-wide / 2 + 0.15, 0.0, z - 0.02), (wide / 2, tall, z + 0.02), "galvanized_dull",
                                "frame"))
    for z, sign in ((-deep / 2 - 0.02, -1.0), (deep / 2 + 0.02, 1.0)):
        inset = 0.12
        corners = [(-wide / 2 + 0.15 + inset, inset), (wide / 2 - inset, inset), (wide / 2 - inset, tall - inset),
                   (-wide / 2 + 0.15 + inset, tall - inset)]
        for at in range(4):
            (x0, y0), (x1, y1) = corners[at], corners[(at + 1) % 4]
            parts.append(shapes.cylinder((x0, y0, z), (x1, y1, z), 0.02, "sign_lit", 6, "neon"))
    parts.append(pieces.label(0.07, tall / 2, wide - 0.6, tall - 0.4, -deep / 2 - 0.02, laid.get("label",
                                                                                               "sign_column_store"),
                              0.0, 0.005, "label"))
    parts.append(shapes.cylinder((-wide / 2 + 0.15, tall + 0.08, 0.0), (wide / 2, tall + 0.08, 0.0), 0.04,
                                 "galvanized_dull", 8, "arm"))
    return parts


def far_lightning_mast(size, laid):
    """A lightning mast round the launch pad, as its close-up shows it: a tall square steel lattice tower tapering to
    a thin spike, red warning lamps up it."""
    wide, tall, deep = size
    parts = lattice_mast(wide, tall - 6.0, deep, "galvanized_dull", 6.0, 0.35)
    for y in (tall * 0.33, tall * 0.66, tall - 6.0):
        parts.append(shapes.box((-0.15, y, -deep / 2 - 0.2), (0.15, y + 0.3, -deep / 2), "lantern_glow", "lamps"))
    return parts


def far_pad_floodlight(size, laid):
    """A floodlight at the launch pad's edge, as its close-up shows it: a short steel lattice mast and a bank of six
    square floodlights on a frame at its top, facing front."""
    wide, tall, deep = size
    mast_top = tall - 2.2
    parts = lattice_mast(0.8, mast_top, 0.8, "galvanized_dull", 0.0, 0.9)
    parts.append(shapes.box((-wide / 2, mast_top, -0.1), (wide / 2, mast_top + 0.1, 0.1), "galvanized_dull", "frame"))
    for row in range(2):
        for column in range(3):
            x = -wide / 2 + wide * (column + 0.5) / 3
            y = mast_top + 0.6 + row * 0.85
            parts.append(shapes.bevelled(shapes.box((x - 0.35, y - 0.35, -deep / 2 + 0.1), (x + 0.35, y + 0.35, 0.3),
                                                    "gate_grey", "floodlight"), 0.02))
            parts.append(shapes.box((x - 0.3, y - 0.3, -deep / 2 + 0.07), (x + 0.3, y + 0.3, -deep / 2 + 0.1),
                                    "floodlight_lens", "lens"))
    return parts


# The far blocks' fittings are the street's own, built alike (the same close-ups and parts), baked at the distant
# density: the square's far tenements.
def far_render_upper(size, laid):
    return render_upper(size, laid)


def far_render_lower(size, laid):
    return render_lower(size, laid)


def far_render_shop(size, laid):
    return render_shop(size, laid)


def far_facade_band(size, laid):
    return facade_band(size, laid)


def far_drainpipe(size, laid):
    return drainpipe(size, laid)


def far_window_dark(size, laid):
    return window_dark(size, laid)


def far_window_lit(size, laid):
    return window_lit(size, laid)


def far_ac_unit(size, laid):
    """The street's air conditioner for a far block: the same parts, its fan and grille drawn with fewer sides."""
    return air_conditioner(size, laid, grille_bars=5, segments=12)


def far_window_cage(size, laid):
    return window_cage(size, laid)


def far_shop_shutter(size, laid):
    return shop_shutter(size, laid)


def far_shop_sign(size, laid):
    return shop_sign(size, laid)


# --- the street's density pass (the owner's concept density rule, 2026-10-08) ---------------------------------------

def road_line(size, laid):
    """A painted line on the road by the kerb: yellow road paint, a hair thick (a plain plate)."""
    return plate(size, "road_line_paint", laid, "line", 0.0)


def facade_pipe(size, laid):
    """A gas pipe or a cable run along a face: the pipe on clips standing it off the wall (a plain pipe), along x."""
    wide, tall, deep = size
    radius = min(tall, deep) / 2
    parts = [shapes.cylinder((-wide / 2, tall / 2, 0.0), (wide / 2, tall / 2, 0.0), radius * 0.8, "galvanized_dull", 12,
                             "pipe")]
    for step in range(max(2, round(wide / 1.5)) + 1):
        x = -wide / 2 + 0.1 + (wide - 0.2) * step / max(2, round(wide / 1.5))
        parts.append(shapes.box((x - 0.012, 0.0, -radius * 0.2), (x + 0.012, tall, deep / 2), "galvanized_dull",
                                "clip"))
    return parts


def end_wall(size, laid):
    """The harbour wall across the street's end: a concrete parapet with its coping (a plain wall)."""
    wide, tall, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall - 0.08, deep / 2), "concrete",
                                       "wall"), 0.01),
            shapes.bevelled(shapes.box((-wide / 2, tall - 0.08, -deep / 2 - 0.03), (wide / 2, tall, deep / 2 + 0.03),
                                       "concrete", "coping"), 0.01)]


def end_fence(size, laid):
    """The wire fence on the harbour wall: steel posts, a top and a bottom rail and the wire mesh between (a plain
    trim), the concept's chain-link drawn as a fine grid of wires."""
    wide, tall, deep = size
    parts = []
    posts = max(2, round(wide / 2.5)) + 1
    for step in range(posts):
        x = -wide / 2 + wide * step / (posts - 1)
        parts.append(shapes.cylinder((x, 0.0, 0.0), (x, tall, 0.0), 0.03, "galvanized_dull", 8, "post"))
    for y in (0.05, tall - 0.03):
        parts.append(shapes.cylinder((-wide / 2, y, 0.0), (wide / 2, y, 0.0), 0.02, "galvanized_dull", 8, "rail"))
    for step in range(int(wide / 0.15)):
        x = -wide / 2 + 0.075 + step * 0.15
        parts.append(shapes.box((x - 0.002, 0.05, -0.003), (x + 0.002, tall - 0.03, 0.003), "galvanized_dull", "wire"))
    for step in range(int(tall / 0.15)):
        y = 0.1 + step * 0.15
        parts.append(shapes.box((-wide / 2, y - 0.002, -0.003), (wide / 2, y + 0.002, 0.003), "galvanized_dull",
                                "wire"))
    return parts


def window_awning(size, laid):
    """A sheet-metal awning over a window, as the concept shows it: a corrugated sheet sloping out from the wall, its
    ribs, and the two steel brackets it rests on."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    # The sheet laid level through the box's middle height, then tilted down toward its front.
    middle = tall / 2 + 0.04
    angle = math.degrees(math.atan2(tall - 0.12, deep))
    parts = []
    ribs = max(4, round(wide / 0.12))
    for step in range(ribs):
        x0 = -wide / 2 + wide * step / ribs
        lift = 0.012 if step % 2 else 0.0
        sheet = shapes.box((x0, middle + lift - 0.004, front - 0.02), (x0 + wide / ribs, middle + lift + 0.004,
                                                                      back + 0.02), "grille_paint",
                           "panel" if step % 2 == 0 else "rib")
        parts.append(pieces.tilted(sheet, (middle, 0.0), -angle))
    for x in (-wide / 2 + 0.08, wide / 2 - 0.08):
        parts.append(shapes.cylinder((x, 0.08, front + 0.02), (x, tall * 0.2, back), 0.012, "grille_paint", 6,
                                     "bracket"))
    return parts


def drying_rack(size, laid):
    """A drying rack out from a window, as the concept shows it: two steel arms bracketed to the wall under the sill
    and the poles across them that the washing hangs from."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    parts = []
    for x in (-wide / 2 + 0.05, wide / 2 - 0.05):
        parts.append(shapes.box((x - 0.015, tall - 0.04, front), (x + 0.015, tall, back), "grille_paint", "arm"))
        parts.append(shapes.cylinder((x, 0.0, back - 0.01), (x, tall - 0.02, front + deep * 0.4), 0.01,
                                     "grille_paint", 6, "bracket"))
    for z in (front + 0.04, front + deep * 0.5):
        parts.append(shapes.cylinder((-wide / 2, tall + 0.015, z), (wide / 2, tall + 0.015, z), 0.012, "bare_steel", 8,
                                     "pole"))
    return parts


def vent_louvre(size, laid):
    """A louvred vent in a shop's wall, as the concept shows it: a steel frame and its slanted louvres."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    parts = bars_round(-wide / 2, 0.0, wide / 2, tall, 0.04, front, back, "grille_paint", "frame")
    for step in range(int((tall - 0.1) / 0.07)):
        y = 0.07 + step * 0.07
        parts.append(pieces.tilted(shapes.box((-wide / 2 + 0.04, y - 0.004, front + 0.01),
                                              (wide / 2 - 0.04, y + 0.004, back - 0.01), "grille_paint", "louvre"),
                                   (y, 0.0), 35.0))
    return parts


def meter_box(size, laid):
    """An electricity meter box by a shop front, as the concept shows it: a grey steel case, its door with a hinge
    side and a latch, and the conduit up out of its top."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    case_top = tall - 0.25
    paint = laid.get("material", "gate_grey")
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front + 0.01), (wide / 2, case_top, back), paint, "case"),
                             0.006),
             shapes.bevelled(shapes.box((-wide / 2 + 0.015, 0.015, front), (wide / 2 - 0.015, case_top - 0.015,
                                                                             front + 0.01), paint, "door"),
                             0.003),
             shapes.box((wide / 2 - 0.05, case_top / 2 - 0.03, front - 0.012), (wide / 2 - 0.035, case_top / 2 + 0.03,
                                                                               front), "bare_steel", "latch"),
             shapes.cylinder((0.0, case_top, back - 0.03), (0.0, tall, back - 0.03), 0.018, "galvanized_dull", 8,
                             "conduit")]
    return parts


def barber_pole(size, laid):
    """A barber's pole by the shop's door, as the concept shows it: a glass cylinder over the red, white and blue
    stripes (a printed sleeve), a chrome cap and base, on a bracket to the wall."""
    wide, tall, deep = size
    radius = min(wide, deep) * 0.3
    middle_z = -deep / 2 + radius + 0.01
    parts = [shapes.cylinder((0.0, 0.1, middle_z), (0.0, tall - 0.1, middle_z), radius, "lamp_lens", 20, "glass"),
             shapes.cylinder((0.0, 0.0, middle_z), (0.0, 0.1, middle_z), radius * 1.25, "bare_steel", 20, "base"),
             shapes.cylinder((0.0, tall - 0.1, middle_z), (0.0, tall, middle_z), radius * 1.25, "bare_steel", 20,
                             "cap"),
             shapes.box((-0.02, tall / 2 - 0.03, middle_z), (0.02, tall / 2 + 0.03, deep / 2), "bare_steel",
                        "bracket")]
    parts.append(pieces.label(0.0, tall / 2, radius * 1.4, tall - 0.3, middle_z - radius * 0.95,
                              laid.get("label", "stripes_barber"), 0.0, 0.005, "stripes"))
    return parts


def menu_board(size, laid):
    """A tea restaurant's A-frame menu board on the pavement (the poster stand's frame, its menu printed on)."""
    return poster_stand(size, dict(laid, label=laid.get("label", "menu_tea")))


BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "ground_asphalt", "ground_paving", "kerb_stone", "render_upper", "render_lower", "render_shop",
    "facade_band", "drainpipe", "window_dark", "window_lit", "ac_unit", "window_cage",
    "shop_shutter", "tea_front", "shop_open", "shop_sign", "neon_sign", "door_canopy",
    "street_lamp", "notice_case", "poster_stand", "far_paving", "far_terrace", "far_road",
    "far_promenade", "far_pad", "bay_balcony_slab", "far_cable", "far_promenade_rail", "bay_balcony_rail",
    "far_render_upper", "far_render_lower", "far_render_shop", "far_facade_band", "far_drainpipe", "far_stage",
    "far_backdrop", "far_podium", "far_lectern", "far_banner", "crowd_banner", "far_floodlight_tower",
    "far_square_lamp",
    "far_lantern", "far_neon_column", "far_lightning_mast", "far_pad_floodlight", "far_window_dark", "far_window_lit",
    "far_ac_unit", "far_window_cage", "far_shop_shutter", "far_shop_sign", "road_line", "facade_pipe", "end_wall", "end_fence", "window_awning", "drying_rack", "vent_louvre",
    "meter_box", "barber_pole", "menu_board", "parapet", "block_roof")}
