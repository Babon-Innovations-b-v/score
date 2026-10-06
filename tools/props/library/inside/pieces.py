"""Runs inside Blender: the hub's flat, slender, opening and repeat pieces built in code (the sorter's code classes,
sorter.py), each at the size the layout lays it, its parts naming their library material.

    import pieces; whole = pieces.build("wall_upper_plain", (1.2, 2.0, 0.06), {"taper": 1.0})

Sizes are (wide, tall, deep) in metres in the kit frame (shapes.py): front toward -z, the back on the wall. Openings
are real holes at the shell's own sizes (the doorway 2.2 x 2.6 m, the porthole 0.6 m across), never a picture of
one. Labels and signs are not here: they go on as decals.
"""
import math

import numpy as np

import shapes

DOORWAY = (2.2, 2.6)  # ModuleDoors.WIDE, ModuleShell.DOOR_HEIGHT
PORTHOLE_RADIUS = 0.3  # ModuleShell.KIT's porthole_wide / 2
BOLT = 0.011
EDGE = 0.004


def bolt(x, y, front, material="bare_steel"):
    """A bolt head standing out of a face at depth `front` (toward -z)."""
    return shapes.cylinder((x, y, front), (x, y, front - 0.007), BOLT, material, 12, "bolt")


def bolts_round(low, high, front, spacing=0.32, inset=0.03):
    """Bolt heads round a rectangle's border, about `spacing` apart."""
    found = []
    (left, bottom), (right, top) = low, high
    across = max(2, round((right - left - 2 * inset) / spacing) + 1)
    up = max(2, round((top - bottom - 2 * inset) / spacing) + 1)
    for at in range(across):
        x = left + inset + (right - left - 2 * inset) * at / (across - 1)
        found += [bolt(x, bottom + inset, front), bolt(x, top - inset, front)]
    for at in range(1, up - 1):
        y = bottom + inset + (top - bottom - 2 * inset) * at / (up - 1)
        found += [bolt(left + inset, y, front), bolt(right - inset, y, front)]
    return found


def bolted_plate(low, high, deep, material):
    """A wall plate between two (x, y) corners: a backing slab, a raised face plate inset from its edges, a stiffener
    across a tall one, and bolt heads round the face plate; its front at -deep/2, its back at +deep/2."""
    (left, bottom), (right, top) = low, high
    front = -deep / 2
    face = front + 0.007
    parts = [shapes.bevelled(shapes.box((left, bottom, face + 0.008), (right, top, deep / 2), material, "slab"), EDGE)]
    inset = 0.045
    if right - left > 2 * inset + 0.05 and top - bottom > 2 * inset + 0.05:
        parts.append(shapes.bevelled(shapes.box((left + inset, bottom + inset, face), (right - inset, top - inset,
                                                                                        face + 0.008), material,
                                                "face"), EDGE))
        if top - bottom > 1.4:
            middle = (bottom + top) / 2
            parts.append(shapes.bevelled(shapes.box((left + inset, middle - 0.025, front + 0.001),
                                                    (right - inset, middle + 0.025, face), material, "rib"), 0.003))
        parts += bolts_round((left + inset, bottom + inset), (right - inset, top - inset), face)
    return parts


def wall_panel(size, laid, material):
    wide, tall, deep = size
    return bolted_plate((-wide / 2, 0.0), (wide / 2, tall), deep, material)


def wall_lower_plain(size, laid):
    return wall_panel(size, laid, "dark_panel")


def wall_upper_plain(size, laid):
    return wall_panel(size, laid, "painted_panel")


def label(x, y, wide, tall, surface, variant):
    """A printed label plate 4 mm thick (the model check's thinnest wall is 3 mm) on a surface at depth `surface`,
    its middle at (x, y): a picture variant of the library's print family, never baked into the surface's own
    material."""
    return shapes.bevelled(shapes.content_plate((x - wide / 2, y - tall / 2, surface - 0.004),
                                                (x + wide / 2, y + tall / 2, surface), variant, "label"), 0.001)


def screw(x, y, surface):
    """A small screw head on a surface."""
    return shapes.cylinder((x, y, surface), (x, y, surface - 0.004), 0.006, "bare_steel", 10, "screw")


def screen_part(x, y, wide, tall, surface, variant="screen"):
    """A screen set in a surface: a black anodized bezel 1.5 cm wide and the glass inside it, its content a
    picture variant of the library's screen family."""
    rim = 0.015
    bezel = shapes.box((x - wide / 2, y - tall / 2, surface - 0.012), (x + wide / 2, y + tall / 2, surface),
                       "anodized_black", "bezel")
    shapes.cut(bezel, shapes.box((x - wide / 2 + rim, y - tall / 2 + rim, surface - 0.02),
                                 (x + wide / 2 - rim, y + tall / 2 - rim, surface + 0.01), "anodized_black"))
    glass = shapes.content_plate((x - wide / 2 + rim, y - tall / 2 + rim, surface - 0.006),
                                 (x + wide / 2 - rim, y + tall / 2 - rim, surface), variant, "glass")
    return [shapes.bevelled(bezel, 0.002), glass]


def keypad(x, y, wide, tall, surface):
    """A keypad: a black bezel round a printed key face, the keys' outlines and figures in its print."""
    return screen_part(x, y, wide, tall, surface, "keypad_print")


DETAIL_PARTS = {"label": label, "screw": screw, "screen": screen_part, "keypad": keypad}


def hatch_wall_surround(size, laid):
    """A door's wall: plates round the doorway (two jambs and a header), the doorway itself left open; the hatch's
    name on a label plate over it."""
    wide, tall, deep = size
    half = DOORWAY[0] / 2
    parts = bolted_plate((-wide / 2, 0.0), (-half, tall), deep, "painted_panel")
    parts += bolted_plate((half, 0.0), (wide / 2, tall), deep, "painted_panel")
    parts += bolted_plate((-half, DOORWAY[1]), (half, tall), deep, "painted_panel")
    parts.append(label(0.0, (DOORWAY[1] + tall) / 2, 0.72, 0.18, -deep / 2 + 0.007, "label_west_hatch"))
    return parts


def porthole_panel(size, laid):
    """A plate with the porthole's real hole through it, a bolted dark flange round it; open, its glass the
    engine's."""
    wide, tall, deep = size
    middle = (0.0, tall / 2)
    plate = shapes.box((-wide / 2, 0.0, -deep / 2 + 0.03), (wide / 2, tall, deep / 2), "painted_panel", "plate")
    shapes.cut(plate, shapes.cylinder((0.0, middle[1], -deep), (0.0, middle[1], deep), PORTHOLE_RADIUS,
                                      "painted_panel", 64, "hole"))
    parts = [shapes.bevelled(plate, EDGE)]
    flange = shapes.ring((0.0, middle[1], -deep / 2 + 0.03), (0.0, middle[1], -deep / 2 + 0.008), 0.43,
                         PORTHOLE_RADIUS, "dark_panel", 64, "flange")
    parts.append(shapes.bevelled(flange, 0.004))
    for at in range(12):
        angle = 2 * math.pi * at / 12
        parts.append(bolt(0.37 * math.cos(angle), middle[1] + 0.37 * math.sin(angle), -deep / 2 + 0.008))
    parts.append(label(0.0, 0.09, 0.39, 0.13, -deep / 2 + 0.03, "label_porthole"))
    return parts


def wall_skirting(size, laid):
    wide, tall, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "rubber",
                                       "skirting"), 0.006)]


def wall_cornice(size, laid):
    """An L along the wall's top: a band down the wall and a shelf standing out under the roof."""
    wide, tall, deep = size
    band = shapes.box((-wide / 2, 0.0, deep / 2 - 0.04), (wide / 2, tall, deep / 2), "painted_panel", "band")
    shelf = shapes.box((-wide / 2, tall - 0.05, -deep / 2), (wide / 2, tall, deep / 2 - 0.04), "painted_panel",
                       "shelf")
    lip = shapes.box((-wide / 2, tall - 0.09, -deep / 2), (wide / 2, tall - 0.05, -deep / 2 + 0.025), "painted_panel",
                     "lip")
    return [shapes.bevelled(part, EDGE) for part in (band, shelf, lip)]


def wall_corner_post(size, laid):
    wide, tall, deep = size
    post = shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "dark_panel", "post")
    parts = [shapes.bevelled(post, 0.012)]
    for y in (0.3, tall / 2, tall - 0.3):
        parts.append(bolt(0.0, y, -deep / 2))
    return parts


def roof_face_panel(size, laid):
    """A roof face: a triangular slab from its foot to the apex, stiffeners across it on the room's side every half
    metre up the slope, as a ribbed roof panel."""
    wide, tall, deep = size
    outline = [(-wide / 2, 0.0), (wide / 2, 0.0), (0.0, tall)]
    parts = [shapes.bevelled(shapes.prism(outline, -deep / 2 + 0.015, deep / 2, "painted_panel", "face"), EDGE)]
    for share in [step / tall for step in np.arange(0.4, tall * 0.85, 0.5)]:
        y = tall * share
        half = wide / 2 * (1 - share) - 0.08
        parts.append(shapes.bevelled(shapes.box((-half, y - 0.03, -deep / 2), (half, y + 0.03, -deep / 2 + 0.015),
                                                "painted_panel", "stiffener"), 0.003))
    return parts


def i_beam(size, along_y, material="dark_panel"):
    """A steel I-beam filling its box, its length along x (or y)."""
    wide, tall, deep = size
    flange = 0.012
    if along_y:
        return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, -deep / 2 + flange),
                                           material, "flange"), 0.003),
                shapes.bevelled(shapes.box((-wide / 2, 0.0, deep / 2 - flange), (wide / 2, tall, deep / 2),
                                           material, "flange"), 0.003),
                shapes.box((-0.006, 0.0, -deep / 2 + flange), (0.006, tall, deep / 2 - flange), material, "web")]
    return [shapes.bevelled(shapes.box((-wide / 2, tall - flange, -deep / 2), (wide / 2, tall, deep / 2), material,
                                       "flange"), 0.003),
            shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, flange, deep / 2), material,
                                       "flange"), 0.003),
            shapes.box((-wide / 2, flange, -0.006), (wide / 2, tall - flange, 0.006), material, "web")]


def lattice_ring_rib(size, laid):
    return i_beam(size, along_y=False)


def lattice_hip_rib(size, laid):
    return i_beam(size, along_y=True)


def lattice_diamond_strut(size, laid):
    wide, tall, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "dark_panel",
                                       "strut"), 0.008)]


def lattice_node_plate(size, laid):
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 + 0.008), (wide / 2, tall, deep / 2),
                                        "dark_panel", "plate"), EDGE)]
    for x in (-wide / 2 + 0.05, wide / 2 - 0.05):
        for y in (0.05, tall - 0.05):
            parts.append(bolt(x, y, -deep / 2 + 0.008))
    return parts


def ceiling_cable_tray(size, laid):
    """A ladder tray along x: two side rails, rungs, and three cables lying in it."""
    wide, tall, deep = size
    parts = []
    for z in (-deep / 2, deep / 2 - 0.012):
        parts.append(shapes.bevelled(shapes.box((-wide / 2, 0.0, z), (wide / 2, tall, z + 0.012), "bare_steel",
                                                "rail"), 0.002))
    rungs = max(2, round(wide / 0.25))
    for at in range(rungs):
        x = -wide / 2 + 0.05 + (wide - 0.1) * at / (rungs - 1)
        parts.append(shapes.box((x - 0.01, 0.0, -deep / 2 + 0.012), (x + 0.01, 0.012, deep / 2 - 0.012), "bare_steel",
                                "rung"))
    for at, z in enumerate((-0.07, 0.0, 0.07)):
        radius = 0.022 if at != 1 else 0.028
        parts.append(shapes.cylinder((-wide / 2, 0.012 + radius, z), (wide / 2, 0.012 + radius, z), radius, "rubber",
                                     16, "cable"))
    return parts


def ceiling_duct(size, laid):
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.02, -deep / 2 + 0.02), (wide / 2, tall - 0.02, deep / 2 - 0.02),
                                        "painted_panel", "duct"), 0.006)]
    for x in (-wide / 2 + 0.03, 0.0, wide / 2 - 0.03):
        parts.append(shapes.bevelled(shapes.box((x - 0.025, 0.0, -deep / 2), (x + 0.025, tall, deep / 2),
                                                "painted_panel", "flange"), 0.004))
    return parts


def ring_floor_plate(size, laid):
    """A deck plate as the ring's real trapezoid: its wall's width at its foot, narrowing to the pit's lip."""
    wide, tall, deep = size
    taper = float(laid.get("taper", 1.0))
    outline = [(-wide / 2, 0.0), (wide / 2, 0.0), (taper * wide / 2, tall), (-taper * wide / 2, tall)]
    parts = [shapes.bevelled(shapes.prism(outline, -deep / 2 + 0.007, deep / 2, "deck", "plate"), EDGE)]
    for share in (0.12, 0.5, 0.88):
        y = tall * share
        half = wide / 2 * (1 - (1 - taper) * share) - 0.06
        for x in (-half, half):
            parts.append(bolt(x, y, -deep / 2 + 0.007))
    return parts


def floor_grating(size, laid):
    """A bar grating in a frame."""
    wide, tall, deep = size
    parts = []
    for low, high in (((-wide / 2, 0.0), (-wide / 2 + 0.03, tall)), ((wide / 2 - 0.03, 0.0), (wide / 2, tall)),
                      ((-wide / 2, 0.0), (wide / 2, 0.03)), ((-wide / 2, tall - 0.03), (wide / 2, tall))):
        parts.append(shapes.bevelled(shapes.box((*low, -deep / 2), (*high, deep / 2), "bare_steel", "frame"), 0.003))
    bars = round((wide - 0.06) / 0.04)
    for at in range(1, bars):
        x = -wide / 2 + 0.03 + (wide - 0.06) * at / bars
        parts.append(shapes.box((x - 0.004, 0.03, -deep / 2), (x + 0.004, tall - 0.03, deep / 2), "bare_steel", "bar"))
    for y in (tall / 3, 2 * tall / 3):
        parts.append(shapes.box((-wide / 2 + 0.03, y - 0.004, -deep / 2 + 0.02), (wide / 2 - 0.03, y + 0.004,
                                                                                    deep / 2), "bare_steel", "cross"))
    return parts


def tread_mat(size, laid):
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 + 0.006), (wide / 2, tall, deep / 2), "rubber",
                                        "mat"), 0.003)]
    ribs = round(tall / 0.07)
    for at in range(1, ribs):
        y = tall * at / ribs
        parts.append(shapes.box((-wide / 2 + 0.04, y - 0.012, -deep / 2), (wide / 2 - 0.04, y + 0.012,
                                                                           -deep / 2 + 0.006), "rubber", "rib"))
    return parts


def hatch_frame(size, laid):
    """The frame lining a doorway: two posts and a header round the shell's real opening, a rubber seal inside."""
    wide, tall, deep = size
    half = DOORWAY[0] / 2
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (-half, tall, deep / 2), "dark_panel", "post"),
                             0.01),
             shapes.bevelled(shapes.box((half, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "dark_panel", "post"),
                             0.01),
             shapes.bevelled(shapes.box((-half, DOORWAY[1], -deep / 2), (half, tall, deep / 2), "dark_panel",
                                        "header"), 0.01)]
    seal = 0.02
    parts += [shapes.box((-half, 0.0, -0.03), (-half + seal, DOORWAY[1], 0.03), "rubber", "seal"),
              shapes.box((half - seal, 0.0, -0.03), (half, DOORWAY[1], 0.03), "rubber", "seal"),
              shapes.box((-half, DOORWAY[1] - seal, -0.03), (half, DOORWAY[1], 0.03), "rubber", "seal")]
    return parts


def hatch_hinge(size, laid):
    """A heavy hinge: two leaves and the knuckle between them on a pin."""
    wide, tall, deep = size
    radius = min(wide, deep) * 0.3
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.02, deep / 2 - 0.03), (wide / 2, tall - 0.02, deep / 2),
                                        "dark_panel", "leaf"), 0.004)]
    for low, high in ((0.0, tall * 0.48), (tall * 0.52, tall)):
        parts.append(shapes.cylinder((0.0, low, -deep / 2 + radius), (0.0, high, -deep / 2 + radius), radius,
                                     "bare_steel", 24, "knuckle"))
    parts.append(shapes.box((-0.008, 0.05, -deep / 2 + radius), (0.008, tall - 0.05, deep / 2 - 0.03), "dark_panel",
                            "web"))
    return parts


def door_strip_lamp(size, laid):
    wide, tall, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 + 0.02), (wide / 2, tall, deep / 2), "dark_panel",
                                       "housing"), 0.004),
            shapes.box((-wide / 2 + 0.03, 0.015, -deep / 2), (wide / 2 - 0.03, tall - 0.015, -deep / 2 + 0.02),
                       "lamp_lens", "lens")]


def cable_bundle(size, laid):
    """Three cables along the wall, clamped to it."""
    wide, tall, deep = size
    parts = []
    radius = min(tall / 6.5, deep / 2.6)
    for at in range(3):
        y = tall / 2 + (at - 1) * radius * 2.1
        parts.append(shapes.cylinder((-wide / 2, y, 0.0), (wide / 2, y, 0.0), radius, "rubber", 16, "cable"))
    clamps = max(2, round(wide / 0.45) + 1)
    for at in range(clamps):
        x = -wide / 2 + 0.04 + (wide - 0.08) * at / (clamps - 1)
        parts.append(shapes.bevelled(shapes.box((x - 0.015, 0.0, -deep / 2), (x + 0.015, tall, deep / 2),
                                                "bare_steel", "clamp"), 0.002))
    return parts


def cable_drop(size, laid):
    """Two cables down the wall, clamped."""
    wide, tall, deep = size
    parts = []
    radius = min(wide / 4.5, deep / 2.6)
    for at in range(2):
        x = (at - 0.5) * radius * 2.2
        parts.append(shapes.cylinder((x, 0.0, 0.0), (x, tall, 0.0), radius, "rubber", 16, "cable"))
    for y in (0.08, tall / 2, tall - 0.08):
        parts.append(shapes.bevelled(shapes.box((-wide / 2, y - 0.015, -deep / 2), (wide / 2, y + 0.015, deep / 2),
                                                "bare_steel", "clamp"), 0.002))
    return parts


def backer(size, laid):
    """The sealed dark sheet behind a wall's kit, with the wall's real openings cut through it."""
    wide, tall, deep = size
    sheet = shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "rubber", "sheet")
    opening = laid.get("opening")
    if opening == "doorway":
        shapes.cut(sheet, shapes.box((-DOORWAY[0] / 2, -0.1, -deep), (DOORWAY[0] / 2, DOORWAY[1], deep), "rubber"))
    elif opening == "porthole":
        high = float(laid["opening_high"])
        shapes.cut(sheet, shapes.cylinder((0.0, high, -deep), (0.0, high, deep), PORTHOLE_RADIUS, "rubber", 64))
    return [sheet]


def inset_screen(size, laid):
    """A screen alone, to be laid on another piece's face: bezel and glass filling its laid size; its content is
    the `screen` named in `laid` (a variant of the screen family), and its kind glows."""
    wide, tall, deep = size
    return screen_part(0.0, tall / 2, wide, tall, deep / 2, laid.get("screen", "screen"))


def wall_screen(size, laid):
    """A screen hung on a wall: a dark housing with a screen in its front."""
    wide, tall, deep = size
    housing = shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 + 0.012), (wide / 2, tall, deep / 2),
                                         "dark_panel", "housing"), 0.006)
    return [housing] + screen_part(0.0, tall / 2, wide - 0.04, tall - 0.04, -deep / 2 + 0.012,
                                   laid.get("screen", "screen")) + [
        screw(side * (wide / 2 - 0.012), y, -deep / 2 + 0.012) for side in (-1, 1) for y in (0.012, tall - 0.012)]


BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "inset_screen", "wall_screen",
    "wall_lower_plain", "wall_upper_plain", "hatch_wall_surround", "porthole_panel", "wall_skirting", "wall_cornice",
    "wall_corner_post", "roof_face_panel", "lattice_ring_rib", "lattice_hip_rib", "lattice_diamond_strut",
    "lattice_node_plate", "ceiling_cable_tray", "ceiling_duct", "ring_floor_plate", "floor_grating", "tread_mat",
    "hatch_frame", "hatch_hinge", "door_strip_lamp", "cable_bundle", "cable_drop", "backer")}


def build(kind, size, laid, name):
    """One code-built piece of `kind` at `size`, as one object whose material slots name library materials."""
    return shapes.joined(BUILDERS[kind](tuple(size), laid), name)
