"""Runs inside Blender: the ship rooms' plain pieces (the ship as a world 1 place, 2026-10-14, the bridge first), in the
kit frame of pieces.py and shapes.py (wide along x, tall along y, deep along z, the front toward -z), each part naming
its library variant. Only plain plates and trims (sorter.PLAIN, the overseer's list of 2026-10-14 by the paper's rule):
the windows' frames and panes, light strips and panels, the floor grate, the frame ribs and the command spot's dais and
step. Glowing lenses are content plates, which make_kit splits off as the piece's glowing part. pieces.py takes
BUILDERS in.

The bridge's surfaces (data/definitions/place.json `bridge`): dark_panel and hammertone_grey steel, clear_glass,
perforated_steel, deck, bare_steel; indicator_amber and screen_teal for the lit strips, glass_frosted for a panel's lens.
"""
import shapes
import pieces

EDGE = 0.004
RIM = 0.05  # a window frame's or panel's border


def surround(wide, tall, deep, rim, material, name):
    """A rectangular frame `rim` wide round an opening, its front at -deep/2: four bevelled bars."""
    front, back = -deep / 2, deep / 2
    bars = (((-wide / 2, 0.0), (-wide / 2 + rim, tall)), ((wide / 2 - rim, 0.0), (wide / 2, tall)),
            ((-wide / 2 + rim, 0.0), (wide / 2 - rim, rim)), ((-wide / 2 + rim, tall - rim), (wide / 2 - rim, tall)))
    return [shapes.bevelled(shapes.box((*low, front), (*high, back), material, name), EDGE) for low, high in bars]


def window_frame(size, laid):
    """The steel surround of one window light: four bars round the glass, bolted along its sill and head."""
    wide, tall, deep = size
    parts = surround(wide, tall, deep, RIM + 0.02, "dark_panel", "frame")
    for y in (RIM / 2 + 0.01, tall - RIM / 2 - 0.01):
        parts += [pieces.bolt(x, y, -deep / 2) for x in (-wide / 2 + 0.12, 0.0, wide / 2 - 0.12)]
    return parts


def window_pane(size, laid):
    """One light of the windshield: a thick plain sheet of clear glass the size of its box."""
    wide, tall, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "clear_glass",
                                       "glass"), 0.002)]


def light_strip(size, lens, name):
    """A long shallow steel channel with a lit lens along its front: the housing and the glowing strip."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    housing = shapes.bevelled(shapes.box((-wide / 2, 0.0, front + 0.006), (wide / 2, tall, back), "dark_panel",
                                         "housing"), 0.002)
    glow = shapes.content_plate((-wide / 2 + 0.01, tall * 0.2, front), (wide / 2 - 0.01, tall * 0.8, front + 0.006),
                                lens, name)
    return [housing, glow]


def edge_light_strip(size, laid):
    """The warm amber light strip along the ceiling's edge."""
    return light_strip(size, "indicator_amber", "lens")


def dash_light_bar(size, laid):
    """The cyan light bar along the top of the main console."""
    return light_strip(size, "screen_teal", "lens")


def ceiling_light_panel(size, laid):
    """A light panel set in the ceiling, seen from below (pieces.FLOOR_SEEN_TURN): a shallow steel housing, a rim
    round its underside and the lens lit cyan inside the rim."""
    wide, tall, deep = size
    lens = 0.006
    parts = [shapes.bevelled(shapes.box((-wide / 2, lens, -deep / 2), (wide / 2, tall, deep / 2), "dark_panel",
                                        "housing"), 0.002)]
    rims = (((-wide / 2, -deep / 2), (wide / 2, -deep / 2 + RIM)), ((-wide / 2, deep / 2 - RIM), (wide / 2, deep / 2)),
            ((-wide / 2, -deep / 2 + RIM), (-wide / 2 + RIM, deep / 2 - RIM)),
            ((wide / 2 - RIM, -deep / 2 + RIM), (wide / 2, deep / 2 - RIM)))
    parts += [shapes.box((x0, 0.0, z0), (x1, lens, z1), "dark_panel", "rim") for (x0, z0), (x1, z1) in rims]
    parts.append(shapes.content_plate((-wide / 2 + RIM, 0.0, -deep / 2 + RIM), (wide / 2 - RIM, lens, deep / 2 - RIM),
                                      "screen_teal", "lens"))
    return parts


def floor_grate(size, laid):
    """A steel grating set in the deck between the seats, its front up: a bolted frame round a perforated plate."""
    wide, long, deep = size
    top, bottom = -deep / 2, deep / 2
    parts = pieces.floor_frame((-wide / 2, 0.0), (wide / 2, long), top, bottom, 0.03, "bare_steel", "frame")
    parts.append(shapes.box((-wide / 2 + 0.03, 0.03, top + 0.004), (wide / 2 - 0.03, long - 0.03, bottom),
                            "perforated_steel", "grate"))
    parts += [pieces.screw(x, y, top) for x in (-wide / 2 + 0.015, wide / 2 - 0.015) for y in (0.015, long - 0.015)]
    return parts


def frame_rib(size, laid):
    """A heavy frame rib: a hammertone steel box section, bolted at its foot and head."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "hammertone_grey",
                                        "rib"), 0.01)]
    parts += [pieces.bolt(0.0, y, -deep / 2) for y in (0.08, tall - 0.08)]
    return parts


def command_platform(size, laid):
    """The command spot's dais: a box of deck plate with a steel nosing round its top edge."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall - 0.02, deep / 2), "dark_panel",
                                        "dais"), EDGE),
             shapes.bevelled(shapes.box((-wide / 2, tall - 0.02, -deep / 2), (wide / 2, tall, deep / 2), "deck",
                                        "top"), 0.002)]
    parts.append(shapes.bevelled(shapes.box((-wide / 2, tall - 0.03, -deep / 2 - 0.006), (wide / 2, tall, -deep / 2),
                                            "bare_steel", "nosing"), 0.002))
    return parts


def platform_step(size, laid):
    """The step up onto the command spot: a deck-topped block with a steel nosing along its front."""
    return command_platform(size, laid)


# The thrust indicator's proportions, shares of an arm's reach read off its close-up: the hub's and a rod's half width,
# where the ribbed head starts, and the head's half width at its inner and outer end.
HUB, ROD, HEAD_FROM, HEAD_NARROW, HEAD_WIDE = 0.09, 0.07, 0.48, 0.16, 0.21


def thrust_indicator(size, laid):
    """The cockpit's thrust indicator (the overseer, 2026-10-15: built in code once both its Pixal3D take's outlines
    failed, 0.335 against 0.5): a plus-shaped gauge set in a slot of the dash, its face toward -z. A square hub, and on
    each of its four arms a dark rod with an amber lit bar along its front, ending in a ribbed head of chevron-like
    plates that widen outward, as the close-up's arms do. The slot, a shallow dark plate behind the hub, is the part
    set into the console."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    middle = tall / 2
    reach = min(wide, tall) / 2
    hub, rod, ribs = HUB * reach, ROD * reach, 5
    head_from = HEAD_FROM * reach
    parts = [shapes.bevelled(shapes.box((-hub, middle - hub, back - deep * 0.25), (hub, middle + hub, back),
                                        "dark_panel", "slot"), 0.003),
             shapes.bevelled(shapes.box((-hub, middle - hub, front + deep * 0.15),
                                        (hub, middle + hub, back - deep * 0.25), "hammertone_grey", "hub"), 0.003)]
    for across, up in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        def spot(along, side, depth_from, depth_to):
            """A box from the hub outward `along` (from, to) and `side` (half width) across the arm."""
            (start, end), half = along, side
            low = (min(across * start, across * end) if across else -half,
                   middle + (min(up * start, up * end) if up else -half))
            high = (max(across * start, across * end) if across else half,
                    middle + (max(up * start, up * end) if up else half))
            return (low[0], low[1], depth_from), (high[0], high[1], depth_to)
        low, high = spot((hub, head_from), rod, front + deep * 0.3, back - deep * 0.3)
        parts.append(shapes.box(low, high, "dark_panel", "arm"))
        low, high = spot((hub, head_from), rod * 0.6, front + deep * 0.25, front + deep * 0.3)
        parts.append(shapes.content_plate(low, high, "indicator_amber", "lens"))
        step = (reach - head_from) / ribs
        for index in range(ribs):
            half = (HEAD_NARROW + (HEAD_WIDE - HEAD_NARROW) * index / (ribs - 1)) * reach
            low, high = spot((head_from + step * index + 0.002, head_from + step * (index + 1) - 0.002), half,
                             front + deep * 0.1, back - deep * 0.15)
            parts.append(shapes.bevelled(shapes.box(low, high, "dark_panel", "rib"), 0.004))
    return parts


BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "window_frame", "window_pane", "edge_light_strip", "dash_light_bar", "ceiling_light_panel", "floor_grate",
    "frame_rib", "command_platform", "platform_step", "thrust_indicator")}
