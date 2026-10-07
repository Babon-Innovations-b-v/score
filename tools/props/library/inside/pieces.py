"""Runs inside Blender: the hub's flat, slender, opening and repeat pieces built in code (the sorter's code classes,
sorter.py), each at the size the layout lays it, its parts naming their library material.

    import pieces; whole = pieces.build("wall_upper_plain", (1.2, 2.0, 0.06), {"taper": 1.0})

Sizes are (wide, tall, deep) in metres in the kit frame (shapes.py): front toward -z, the back on the wall. Openings
are real holes at the shell's own sizes (the doorway 2.2 x 2.6 m, the porthole 0.6 m across), never a picture of
one. Labels, screens and notices are printed parts (a picture variant of the library's print or screen family on a
plate), never a picture of the piece.
"""
import math

import numpy as np

import bpy
from mathutils import Matrix
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


def bolted_plate(low, high, deep, material, back=None):
    """A wall plate between two (x, y) corners: a backing slab, a raised face plate inset from its edges, a stiffener
    across a tall one, and bolt heads round the face plate; its back at `back` (+deep/2 unless given), its front
    `deep` in front of it."""
    (left, bottom), (right, top) = low, high
    back = deep / 2 if back is None else back
    front = back - deep
    face = front + 0.007
    parts = [shapes.bevelled(shapes.box((left, bottom, face + 0.008), (right, top, back), material, "slab"), EDGE)]
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


def with_openings(parts, laid, deep):
    """The parts with the openings the layout cut for its set-in fittings (laid["openings"]: [x0, y0, x1, y1] in the
    piece's frame) taken out of them: a part reaching into an opening is cut through, a part wholly inside one (a bolt
    head) is left out. A fitting then sits in its opening flush with the face round it (the owner, 2026-10-06)."""
    kept = []
    for part in parts:
        corners = [(vertex.co.x, vertex.co.z) for vertex in part.data.vertices]  # the kit frame's x and y
        low = (min(corner[0] for corner in corners), min(corner[1] for corner in corners))
        high = (max(corner[0] for corner in corners), max(corner[1] for corner in corners))
        inside = False
        for x0, y0, x1, y1 in laid.get("openings", []):
            if high[0] <= x0 or x1 <= low[0] or high[1] <= y0 or y1 <= low[1]:
                continue
            if x0 <= low[0] and high[0] <= x1 and y0 <= low[1] and high[1] <= y1:
                inside = True
                break
            shapes.cut(part, shapes.box((x0, y0, -deep - 0.05), (x1, y1, deep + 0.05), "bare_steel", "cutter"))
        if inside:
            bpy.data.objects.remove(part, do_unlink=True)
        else:
            kept.append(part)
    return kept


def hatch_wall_surround(size, laid):
    """A door's wall: plates round the doorway (two jambs and a header), the doorway itself left open; the hatch's
    name on a label plate over it."""
    wide, tall, deep = size
    half = DOORWAY[0] / 2
    parts = bolted_plate((-wide / 2, 0.0), (-half, tall), deep, "painted_panel")
    parts += bolted_plate((half, 0.0), (wide / 2, tall), deep, "painted_panel")
    parts += bolted_plate((-half, DOORWAY[1]), (half, tall), deep, "painted_panel")
    parts = with_openings(parts, laid, deep)
    parts.append(label(0.0, (DOORWAY[1] + tall) / 2, 0.72, 0.18, -deep / 2 + 0.007,
                       laid.get("label", "label_west_hatch")))
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
    return with_openings(parts, laid, deep)


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


# --- round three (2026-10-06): the rest of the hub's code-built kinds --------------------------------------------
PLATE_DEEP = 0.06


VENT_RIM = 0.025
VENT_POCKET = 0.024


def louvred_vent(x, y, wide, tall, front, hosts):
    """A louvred vent set in a face at depth `front`: its opening cut through `hosts` (the parts the face belongs to)
    as a pocket VENT_POCKET deep, a dark plate at the pocket's bottom, slats across the opening with dark gaps between,
    and a bolted frame round it on the face. Round three laid the slats and the dark plate inside the host's solid with
    no hole cut, so only an empty frame showed (every locker and wall vent, the detail-loss diagnosis, 2026-10-07)."""
    rim = VENT_RIM
    left, right, bottom, top = x - wide / 2 + rim, x + wide / 2 - rim, y - tall / 2 + rim, y + tall / 2 - rim
    for host in hosts:
        shapes.cut(host, shapes.box((left, bottom, front - 0.02), (right, top, front + VENT_POCKET), "bare_steel",
                                    "cutter"))
    parts = [shapes.box((left - 0.004, bottom - 0.004, front + VENT_POCKET - 0.004),
                        (right + 0.004, top + 0.004, front + VENT_POCKET), "anodized_black", "vent_back")]
    slats = max(3, round((top - bottom) / 0.03))
    pitch = (top - bottom) / slats
    for at in range(slats):
        low = bottom + pitch * at + pitch * 0.3
        parts.append(shapes.bevelled(shapes.box((left, low, front + 0.003), (right, low + pitch * 0.45, front + 0.012),
                                                "bare_steel", "slat"), 0.0015))
    for low, high in (((x - wide / 2, y - tall / 2), (left, y + tall / 2)),
                      ((right, y - tall / 2), (x + wide / 2, y + tall / 2)),
                      ((left, y - tall / 2), (right, bottom)), ((left, top), (right, y + tall / 2))):
        parts.append(shapes.bevelled(shapes.box((*low, front - 0.006), (*high, front + 0.002), "bare_steel",
                                                "vent_frame"), 0.002))
    for corner_x in (x - wide / 2 + rim / 2, x + wide / 2 - rim / 2):
        for corner_y in (y - tall / 2 + rim / 2, y + tall / 2 - rim / 2):
            parts.append(screw(corner_x, corner_y, front - 0.006))
    return parts


def wall_lower_vent(size, laid):
    """A lower wall plate with a louvred vent in its middle."""
    wide, tall, deep = size
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), deep, "dark_panel")
    hosts = [part for part in parts if not part.name.startswith("bolt")]
    return parts + louvred_vent(0.0, tall * 0.45, min(0.6, wide - 0.3), 0.32, -deep / 2 + 0.007, hosts)


def patch(x, y, wide, tall, front, material="hammertone_grey"):
    """A repair plate bolted over a face at depth `front`."""
    plate = shapes.bevelled(shapes.box((x - wide / 2, y - tall / 2, front - 0.006), (x + wide / 2, y + tall / 2, front),
                                       material, "patch"), 0.003)
    return [plate] + bolts_round((x - wide / 2, y - tall / 2), (x + wide / 2, y + tall / 2), front - 0.006,
                                 spacing=0.16, inset=0.025)


def wall_lower_patched(size, laid):
    """A lower wall plate with a repair plate bolted over one corner of it."""
    wide, tall, deep = size
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), deep, "dark_panel")
    return parts + patch(wide * 0.12, tall * 0.38, 0.42, 0.3, -deep / 2 + 0.007)


def wall_upper_patched(size, laid):
    """An upper wall plate with a repair plate and a stencilled number."""
    wide, tall, deep = size
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), deep, "painted_panel")
    parts += patch(-wide * 0.1, tall * 0.62, 0.36, 0.44, -deep / 2 + 0.007)
    parts.append(label(wide * 0.18, tall * 0.25, 0.24, 0.12, -deep / 2 + 0.007, "stencil_number"))
    return parts


def wall_upper_cables(size, laid):
    """An upper wall plate set back to make room for three cables run across it in clamps."""
    wide, tall, deep = size
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), PLATE_DEEP, "painted_panel", back=deep / 2)
    front = deep / 2 - PLATE_DEEP + 0.007
    radius = 0.014
    for at, (high, colour) in enumerate(((0.62, "cable_black"), (0.66, "cable_orange"), (0.70, "cable_grey"))):
        y = tall * high
        parts.append(shapes.cylinder((-wide / 2, y, front - radius), (wide / 2, y, front - radius), radius, colour, 14,
                                     "cable"))
    for x in (-wide / 2 + 0.15, 0.0, wide / 2 - 0.15):
        parts.append(shapes.bevelled(shapes.box((x - 0.018, tall * 0.6, -deep / 2), (x + 0.018, tall * 0.72, front),
                                                "bare_steel", "clamp"), 0.002))
    return parts


def wall_upper_pipes(size, laid):
    """An upper wall plate set back behind two pipes run across it on brackets."""
    wide, tall, deep = size
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), PLATE_DEEP, "painted_panel", back=deep / 2)
    front = deep / 2 - PLATE_DEEP + 0.007
    radius = 0.024
    for high in (0.55, 0.7):
        y = tall * high
        parts.append(shapes.cylinder((-wide / 2, y, -deep / 2 + radius), (wide / 2, y, -deep / 2 + radius), radius,
                                     "pipe_steel", 20, "pipe"))
    for x in (-wide / 2 + 0.2, wide / 2 - 0.2):
        parts.append(shapes.bevelled(shapes.box((x - 0.02, tall * 0.5, -deep / 2 + radius), (x + 0.02, tall * 0.75,
                                                                                           front), "dark_panel",
                                                "bracket"), 0.002))
    return parts


def wall_upper_screen_recess(size, laid):
    """An upper wall plate with a recess in it and a screen set in the recess's back."""
    wide, tall, deep = size
    middle, screen = tall * 0.42, (min(0.8, wide - 0.3), 0.48)
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, middle - screen[1] / 2 - 0.05), deep, "painted_panel")
    parts += bolted_plate((-wide / 2, middle + screen[1] / 2 + 0.05), (wide / 2, tall), deep, "painted_panel")
    for side in (-1, 1):
        parts += bolted_plate((side * (screen[0] / 2 + 0.05), middle - screen[1] / 2 - 0.05),
                              (side * wide / 2, middle + screen[1] / 2 + 0.05), deep, "painted_panel")
    parts.append(shapes.box((-screen[0] / 2 - 0.05, middle - screen[1] / 2 - 0.05, deep / 2 - 0.02),
                            (screen[0] / 2 + 0.05, middle + screen[1] / 2 + 0.05, deep / 2), "dark_panel", "recess"))
    return parts + screen_part(0.0, middle, screen[0], screen[1], deep / 2 - 0.02, laid.get("screen", "screen_amber"))


def hatch_leaf(size, laid):
    """A hatch's door leaf: a thick slab with a raised border, a round hole for its window, the wheel's boss."""
    wide, tall, deep = size
    window = (0.0, 1.85)
    slab = shapes.box((-wide / 2, 0.0, -deep / 2 + 0.015), (wide / 2, tall, deep / 2), "painted_panel", "slab")
    shapes.cut(slab, shapes.cylinder((window[0], window[1], -deep), (window[0], window[1], deep), 0.15,
                                     "painted_panel", 48))
    parts = [shapes.bevelled(slab, 0.01)]
    rim = 0.09
    for low, high in (((-wide / 2, 0.0), (-wide / 2 + rim, tall)), ((wide / 2 - rim, 0.0), (wide / 2, tall)),
                      ((-wide / 2 + rim, 0.0), (wide / 2 - rim, rim)), ((-wide / 2 + rim, tall - rim),
                                                                        (wide / 2 - rim, tall))):
        parts.append(shapes.bevelled(shapes.box((*low, -deep / 2), (*high, -deep / 2 + 0.015), "dark_panel", "border"),
                                     0.004))
    parts += bolts_round((-wide / 2 + rim / 2, rim / 2), (wide / 2 - rim / 2, tall - rim / 2), -deep / 2,
                         spacing=0.4, inset=0.0)
    return parts


def hatch_wheel(size, laid):
    """The locking wheel: a rim, four spokes and a boss, standing off the leaf."""
    wide, tall, deep = size
    middle = (0.0, tall / 2)
    radius = min(wide, tall) / 2
    parts = [shapes.bevelled(shapes.ring((*middle, -deep / 2 + 0.03), (*middle, -deep / 2), radius, radius - 0.035,
                                         "bare_steel", 48, "rim"), 0.004)]
    for angle in (0.0, math.pi / 2):
        along = (math.cos(angle) * (radius - 0.02), math.sin(angle) * (radius - 0.02))
        parts.append(shapes.cylinder((middle[0] - along[0], middle[1] - along[1], -deep / 2 + 0.015),
                                     (middle[0] + along[0], middle[1] + along[1], -deep / 2 + 0.015), 0.012,
                                     "bare_steel", 12, "spoke"))
    parts.append(shapes.cylinder((*middle, -deep / 2 + 0.005), (*middle, deep / 2), 0.05, "dark_panel", 24, "boss"))
    return parts


def hatch_window(size, laid):
    """A hatch's round window: a bolted flange and its glass, set through the leaf."""
    wide, tall, deep = size
    middle = (0.0, tall / 2)
    outer = min(wide, tall) / 2
    parts = [shapes.bevelled(shapes.ring((*middle, -deep / 2), (*middle, deep / 2), outer, 0.13, "dark_panel", 48,
                                         "flange"), 0.004),
             shapes.cylinder((*middle, -0.006), (*middle, 0.006), 0.135, "glass_tinted", 48, "glass")]
    for at in range(8):
        angle = 2 * math.pi * at / 8
        parts.append(bolt(outer * 0.82 * math.cos(angle), middle[1] + outer * 0.82 * math.sin(angle), -deep / 2))
    return parts


def floor_access_hatch(size, laid):
    """A square access hatch lying in the deck, its front up: a chequer plate lid in a steel frame, a flush lift
    handle and a bolt at each corner."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 + 0.004), (wide / 2, tall, deep / 2),
                                        "galvanized_steel", "frame"), 0.003),
             shapes.bevelled(shapes.box((-wide / 2 + 0.04, 0.04, -deep / 2), (wide / 2 - 0.04, tall - 0.04,
                                                                             -deep / 2 + 0.004),
                                        "chequer_plate_deck", "lid"), 0.002),
             shapes.box((-0.08, tall - 0.14, -deep / 2 - 0.002), (0.08, tall - 0.11, -deep / 2 + 0.002), "bare_steel",
                        "handle")]
    for x in (-wide / 2 + 0.02, wide / 2 - 0.02):
        for y in (0.02, tall - 0.02):
            parts.append(screw(x, y, -deep / 2 + 0.004))
    return parts


def pit_wall_panel(size, laid):
    """A panel of the pit's wall: a bolted plate with a seam down its middle."""
    wide, tall, deep = size
    parts = bolted_plate((-wide / 2, 0.0), (-0.004, tall), deep, "dark_panel")
    parts += bolted_plate((0.004, 0.0), (wide / 2, tall), deep, "dark_panel")
    parts.append(shapes.box((-0.006, 0.0, -deep / 2 + 0.012), (0.006, tall, deep / 2), "anodized_black", "seam"))
    return parts


def pit_floor_plate(size, laid):
    """A chequer floor plate of the pit, a bolt at each corner (also the stairs' risers, stood up)."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "chequer_plate_deck",
                                        "plate"), EDGE)]
    inset = min(0.04, tall / 4)
    for x in (-wide / 2 + inset, wide / 2 - inset):
        for y in (inset, tall - inset):
            parts.append(screw(x, y, -deep / 2))
    return parts


def machine_bay_plate(size, laid):
    """A machine bay's deck plate in the pit, its front up: a heavy plate in a steel frame with a tie-down ring at
    each corner."""
    wide, tall, deep = size
    rim = 0.06
    parts = [shapes.bevelled(shapes.box((-wide / 2 + rim, rim, -deep / 2 + 0.006), (wide / 2 - rim, tall - rim,
                                                                                    deep / 2), "deck", "plate"),
                             EDGE)]
    for low, high in (((-wide / 2, 0.0), (-wide / 2 + rim, tall)), ((wide / 2 - rim, 0.0), (wide / 2, tall)),
                      ((-wide / 2 + rim, 0.0), (wide / 2 - rim, rim)), ((-wide / 2 + rim, tall - rim),
                                                                        (wide / 2 - rim, tall))):
        parts.append(shapes.bevelled(shapes.box((*low, -deep / 2), (*high, deep / 2), "galvanized_steel", "frame"),
                                     0.004))
    for x in (-wide / 2 + 0.2, wide / 2 - 0.2):
        for y in (0.2, tall - 0.2):
            parts.append(shapes.ring((x, y, -deep / 2 + 0.006), (x, y, -deep / 2 - 0.01), 0.04, 0.025, "bare_steel",
                                     20, "tie_down"))
    return parts


def screen_housing(wide, tall, deep):
    """The dark housing a wall screen stands in, screwed to the wall at its corners."""
    housing = shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 + 0.012), (wide / 2, tall, deep / 2), "dark_panel",
                                         "housing"), 0.006)
    return [housing] + [screw(side * (wide / 2 - 0.015), y, -deep / 2 + 0.012) for side in (-1, 1)
                        for y in (0.015, tall - 0.015)]


def status_display(size, laid):
    """The big status display: a housing and one screen filling it."""
    wide, tall, deep = size
    return screen_housing(wide, tall, deep) + screen_part(0.0, tall / 2, wide - 0.06, tall - 0.06, -deep / 2 + 0.012,
                                                          laid.get("screen", "screen"))


def wall_screen_cluster(size, laid):
    """Three screens in one housing: a big one and two small ones stacked beside it."""
    wide, tall, deep = size
    front = -deep / 2 + 0.012
    big = wide * 0.6
    parts = screen_housing(wide, tall, deep)
    parts += screen_part(-wide / 2 + 0.03 + big / 2, tall / 2, big - 0.02, tall - 0.06, front, "screen")
    small = wide - big - 0.08
    for at, variant in enumerate(("screen_amber", "screen")):
        y = tall * (0.27 + 0.46 * at)
        parts += screen_part(wide / 2 - 0.03 - small / 2, y, small, tall * 0.4, front, variant)
    return parts


def intercom_panel(size, laid):
    """An intercom: a plastic plate with a speaker grille, a call button and its printed label."""
    wide, tall, deep = size
    front = -deep / 2 + 0.01
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front), (wide / 2, tall, deep / 2), "plastic_grey", "plate"),
                             0.006),
             shapes.box((-wide / 2 + 0.04, tall * 0.5, front - 0.004), (wide / 2 - 0.04, tall - 0.04, front),
                        "perforated_steel", "grille"),
             shapes.cylinder((0.0, tall * 0.3, front), (0.0, tall * 0.3, front - 0.012), 0.025, "anodized_red", 20,
                             "button"),
             label(0.0, tall * 0.12, wide - 0.08, 0.05, front, "intercom_print")]
    return parts


def grab_bar(size, laid):
    """A grab bar up the wall beside a door: a round bar on two stand-offs from screwed foot plates."""
    wide, tall, deep = size
    radius = min(wide, deep) * 0.17
    bar_z = -deep / 2 + radius
    parts = [shapes.cylinder((0.0, 0.06, bar_z), (0.0, tall - 0.06, bar_z), radius, "brushed_steel_fine", 20, "bar")]
    for y in (0.06, tall - 0.06):
        parts.append(shapes.cylinder((0.0, y, bar_z), (0.0, y, deep / 2 - 0.008), radius * 0.9, "brushed_steel_fine",
                                     16, "stand_off"))
        parts.append(shapes.cylinder((0.0, y, deep / 2 - 0.008), (0.0, y, deep / 2), wide / 2 - 0.005,
                                     "brushed_steel_fine", 20, "foot"))
    return parts


def pipe_straight(size, laid):
    """A pipe length along x with a flange at each end."""
    wide, tall, deep = size
    radius = min(tall, deep) * 0.38
    middle = (tall / 2, 0.0)
    parts = [shapes.cylinder((-wide / 2, middle[0], middle[1]), (wide / 2, middle[0], middle[1]), radius, "pipe_steel",
                             24, "pipe")]
    for end in (-1, 1):
        x = end * (wide / 2 - 0.012)
        parts.append(shapes.bevelled(shapes.cylinder((x - 0.012, middle[0], middle[1]), (x + 0.012, middle[0],
                                                                                         middle[1]),
                                                     min(tall, deep) / 2, "pipe_steel", 24, "flange"), 0.002))
    return parts


def notice_board(size, laid):
    """A notice board: a framed board with printed sheets pinned on it."""
    wide, tall, deep = size
    front = -deep / 2 + 0.012
    rim = 0.03
    parts = [shapes.box((-wide / 2 + rim, rim, front + 0.004), (wide / 2 - rim, tall - rim, deep / 2), "canvas_beige",
                        "board")]
    for low, high in (((-wide / 2, 0.0), (-wide / 2 + rim, tall)), ((wide / 2 - rim, 0.0), (wide / 2, tall)),
                      ((-wide / 2 + rim, 0.0), (wide / 2 - rim, rim)), ((-wide / 2 + rim, tall - rim),
                                                                        (wide / 2 - rim, tall))):
        parts.append(shapes.bevelled(shapes.box((*low, -deep / 2), (*high, deep / 2), "dark_panel", "frame"), 0.004))
    parts.append(label(0.0, tall / 2, wide - 2 * rim - 0.02, tall - 2 * rim - 0.02, front + 0.004, "notice_sheets"))
    return parts


def stair_stringer(size, laid):
    """A stair's stepped side plate, as long as the stair runs (x, from the pit's edge at -x to its foot at +x) and as
    tall as the pit is deep, its top stepping down tread by tread; bolts along it."""
    wide, tall, deep = size
    treads = int(laid.get("treads", 4))
    run = wide / treads
    rise = tall / (treads + 1)
    outline = [(-wide / 2, 0.0), (wide / 2, 0.0)]
    for step in range(treads, 0, -1):
        x = wide / 2 - run * (treads - step)
        outline += [(x, rise * (treads - step + 1)), (x - run, rise * (treads - step + 1))]
    parts = [shapes.bevelled(shapes.prism(outline, -deep / 2, deep / 2, "dark_panel", "stringer"), 0.004)]
    for step in range(treads):
        x = wide / 2 - run * (step + 0.5)
        parts.append(bolt(x, rise * (step + 1) - 0.05, -deep / 2))
    return parts



# --- the hub's furniture (2026-10-06, after the owner's in-game test: the console, lockers, lab bench, comms desk,
# toolboard and chair were still old assets; every visible thing in the room is now made by the route) -------------
DESK_HIGH = 0.78
DESK_THICK = 0.04
# The console's screens: as Workstation and its scene place them (five along its back, the outer ones turned in, the
# middle three the Workstation's own live glass, which the route writes as screen plates; tools/props/library/route.py).
SCREENS = 5
LIVE_SCREENS = (1, 2, 3)
SCREEN_FRAME = (0.48, 0.3)
SCREEN_BORDER = 0.02
SCREEN_MIDDLE = 1.03
SCREEN_BACK = 0.16
SCREEN_TURN = 12.0
FRAME_DEPTH = 0.04


def moved(parts, offset):
    """The parts moved by a kit-frame offset."""
    shift = Matrix.Translation(shapes.to_blender(offset))
    for part in parts:
        part.data.transform(shift)
    return parts


def turned(parts, degrees):
    """The parts turned about the kit frame's up through the origin (right-handed, as Godot's Basis(UP, angle))."""
    spin = Matrix.Rotation(math.radians(degrees), 4, "Z")
    for part in parts:
        part.data.transform(spin)
    return parts


def keyboard(x, y, z):
    """A keyboard on a desk top at height y, its middle at (x, z): a black housing and rows of grey keys."""
    wide, deep = 0.45, 0.15
    parts = [shapes.bevelled(shapes.box((x - wide / 2, y, z - deep / 2), (x + wide / 2, y + 0.018, z + deep / 2),
                                        "anodized_black", "housing"), 0.004)]
    columns, rows = 14, 5
    key = (wide - 0.03) / columns
    for row in range(rows):
        for column in range(columns):
            left = x - wide / 2 + 0.015 + column * key
            near = z - deep / 2 + 0.015 + row * (deep - 0.03) / rows
            parts.append(shapes.box((left + 0.002, y + 0.018, near + 0.002),
                                    (left + key - 0.002, y + 0.026, near + (deep - 0.03) / rows - 0.002),
                                    "plastic_grey", "key"))
    return parts


def screen_mount(variant=None):
    """A screen at the origin, its glass facing -z: a black frame, its stand down to the desk and a foot, and (a
    screen of the console's own) its bezel and lit content (screen_part); a live screen's glass is the Workstation's."""
    wide, tall = SCREEN_FRAME
    parts = [shapes.bevelled(shapes.box((-wide / 2, -tall / 2, -FRAME_DEPTH / 2), (wide / 2, tall / 2, FRAME_DEPTH / 2),
                                        "anodized_black", "frame"), 0.004)]
    stand = SCREEN_MIDDLE - tall / 2 - DESK_HIGH
    parts.append(shapes.box((-0.025, -tall / 2 - stand, FRAME_DEPTH / 2), (0.025, -tall / 2, FRAME_DEPTH / 2 + 0.03),
                            "bare_steel", "stand"))
    parts.append(shapes.bevelled(shapes.box((-0.09, -tall / 2 - stand, -0.03), (0.09, -tall / 2 - stand + 0.012, 0.09),
                                            "bare_steel", "foot"), 0.003))
    if variant is not None:
        parts += screen_part(0.0, 0.0, wide - 2 * SCREEN_BORDER, tall - 2 * SCREEN_BORDER, -FRAME_DEPTH / 2, variant)
    return parts


def console(size, laid):
    """The operations console: a dark steel top on four legs with round feet, a louvred panel set back under it, two
    keyboards, and five screens on stands along its back, the outer ones turned in; the outer two show their own
    content, the middle three are frames for the Workstation's live glass."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, DESK_HIGH - DESK_THICK, -deep / 2), (wide / 2, DESK_HIGH, deep / 2),
                                        "dark_panel", "top"), EDGE)]
    back = -deep / 2 + 0.15
    panel = shapes.bevelled(shapes.box((-wide / 2 + 0.05, 0.08, back), (wide / 2 - 0.05, DESK_HIGH - DESK_THICK,
                                                                       back + 0.03), "painted_panel", "panel"), EDGE)
    parts.append(panel)
    for x in (-wide / 3, 0.0, wide / 3):
        parts += louvred_vent(x, 0.42, 0.42, 0.24, back, [panel])
    for x in (-wide / 2 + 0.12, -wide / 6, wide / 6, wide / 2 - 0.12):
        parts.append(shapes.box((x - 0.025, 0.02, -deep / 2 + 0.075), (x + 0.025, DESK_HIGH - DESK_THICK, -deep / 2 + 0.125),
                                "bare_steel", "leg"))
        parts.append(shapes.cylinder((x, 0.0, -deep / 2 + 0.1), (x, 0.02, -deep / 2 + 0.1), 0.1, "bare_steel", 20, "foot"))
    for x in (-0.25, 0.55):
        parts += keyboard(x, DESK_HIGH, -deep / 2 + 0.15)
    for index in range(SCREENS):
        out = index - (SCREENS - 1) / 2
        screen = screen_mount(None if index in LIVE_SCREENS else "screen")
        parts += moved(turned(screen, out * SCREEN_TURN), (out * wide / SCREENS * 0.98, SCREEN_MIDDLE, deep / 2 - SCREEN_BACK))
    return parts


def locker(size, doors):
    """A steel locker of `doors` doors: its carcass on a dark plinth, door plates standing proud with louvred vents top
    and bottom and a handle each."""
    wide, tall, deep = size
    carcass = shapes.bevelled(shapes.box((-wide / 2, 0.08, -deep / 2 + 0.012), (wide / 2, tall, deep / 2), "painted_panel",
                                         "carcass"), EDGE)
    parts = [shapes.box((-wide / 2 + 0.02, 0.0, -deep / 2 + 0.03), (wide / 2 - 0.02, 0.08, deep / 2), "dark_panel", "plinth"),
             carcass]
    door_wide = (wide - 0.04 - 0.01 * (doors - 1)) / doors
    for door in range(doors):
        left = -wide / 2 + 0.02 + door * (door_wide + 0.01)
        middle = left + door_wide / 2
        door_plate = shapes.bevelled(shapes.box((left, 0.1, -deep / 2), (left + door_wide, tall - 0.02, -deep / 2 + 0.012),
                                                "painted_panel", "door"), 0.003)
        parts.append(door_plate)
        for high in (tall - 0.22, 0.32):
            parts += louvred_vent(middle, high, door_wide * 0.55, 0.12, -deep / 2, [door_plate, carcass])
        handle_x = left + door_wide - 0.06 if door % 2 == 0 else left + 0.06
        parts.append(shapes.bevelled(shapes.box((handle_x - 0.012, tall * 0.48, -deep / 2 - 0.025),
                                                (handle_x + 0.012, tall * 0.56, -deep / 2), "bare_steel", "handle"), 0.004))
    return parts


def talllocker(size, laid):
    """The tall double locker."""
    return locker(size, 2)


def rack(size, laid):
    """A single steel locker."""
    return locker(size, 1)


def drawer_unit(left, right, top, front, back):
    """A painted drawer unit from the floor to `top`, three drawers with a pull each."""
    parts = [shapes.bevelled(shapes.box((left, 0.04, front + 0.012), (right, top, back), "painted_panel", "unit"), EDGE)]
    step = (top - 0.06) / 3
    for drawer in range(3):
        low = 0.06 + drawer * step
        parts.append(shapes.bevelled(shapes.box((left + 0.015, low + 0.008, front), (right - 0.015, low + step - 0.008,
                                                                                     front + 0.012), "painted_panel",
                                                "drawer"), 0.003))
        middle = low + step / 2
        parts.append(shapes.box(((left + right) / 2 - 0.06, middle - 0.01, front - 0.02), ((left + right) / 2 + 0.06,
                                                                                          middle + 0.01, front),
                                "bare_steel", "pull"))
    return parts


def labbench(size, laid):
    """The lab bench: a steel top on legs over a drawer unit, a glovebox (a painted box with a tinted glass front and
    two glove ports) and a microscope."""
    wide, tall, deep = size
    top = 0.9
    parts = [shapes.bevelled(shapes.box((-wide / 2, top - 0.04, -deep / 2), (wide / 2, top, deep / 2), "brushed_steel_fine",
                                        "top"), EDGE)]
    for x in (-wide / 2 + 0.05, wide / 2 - 0.05):
        for z in (-deep / 2 + 0.05, deep / 2 - 0.05):
            parts.append(shapes.box((x - 0.025, 0.0, z - 0.025), (x + 0.025, top - 0.04, z + 0.025), "bare_steel", "leg"))
    parts += drawer_unit(wide / 2 - 0.55, wide / 2 - 0.08, top - 0.05, -deep / 2 + 0.03, deep / 2 - 0.03)
    box_left, box_right, box_top = -wide / 2 + 0.1, 0.15, tall - 0.02
    box_front, box_back = -deep / 2 + 0.08, deep / 2 - 0.04
    parts.append(shapes.bevelled(shapes.box((box_left, top, box_front + 0.01), (box_right, box_top, box_back),
                                            "hull_white_gloss", "glovebox"), EDGE))
    parts.append(shapes.box((box_left + 0.04, top + 0.06, box_front), (box_right - 0.04, box_top - 0.06, box_front + 0.01),
                            "glass_tinted", "window"))
    port_high = top + (box_top - top) * 0.42
    for x in (box_left + (box_right - box_left) * 0.3, box_left + (box_right - box_left) * 0.7):
        parts.append(shapes.ring((x, port_high, box_front - 0.025), (x, port_high, box_front + 0.005), 0.085, 0.065,
                                 "gasket_black", 32, "port"))
    scope_x, scope_z = wide / 2 - 0.35, 0.0
    parts.append(shapes.bevelled(shapes.box((scope_x - 0.1, top, scope_z - 0.12), (scope_x + 0.1, top + 0.035, scope_z + 0.12),
                                            "dark_panel", "scope_base"), 0.004))
    parts.append(shapes.bevelled(shapes.box((scope_x - 0.035, top + 0.035, scope_z + 0.05), (scope_x + 0.035, top + 0.34,
                                                                                         scope_z + 0.11), "hull_white_gloss",
                                            "scope_arm"), 0.006))
    parts.append(shapes.box((scope_x - 0.07, top + 0.12, scope_z - 0.07), (scope_x + 0.07, top + 0.135, scope_z + 0.05),
                            "anodized_black", "stage"))
    parts.append(shapes.bevelled(shapes.box((scope_x - 0.05, top + 0.28, scope_z - 0.06), (scope_x + 0.05, top + 0.36,
                                                                                       scope_z + 0.08), "hull_white_gloss",
                                            "scope_head"), 0.008))
    parts.append(shapes.cylinder((scope_x, top + 0.28, scope_z - 0.02), (scope_x, top + 0.17, scope_z - 0.02), 0.018,
                                 "anodized_black", 20, "objective"))
    for x in (scope_x - 0.025, scope_x + 0.025):
        parts.append(shapes.cylinder((x, top + 0.34, scope_z - 0.04), (x, top + 0.42, scope_z - 0.1), 0.014,
                                     "anodized_black", 16, "eyepiece"))
    return parts


def chair(size, laid):
    """The operations chair: five legs on casters round a gas column, a padded seat and back, two armrests."""
    wide, tall, deep = size
    parts = [shapes.cylinder((0.0, 0.07, 0.0), (0.0, 0.42, 0.0), 0.028, "bare_steel", 20, "column")]
    for leg in range(5):
        spoke = [shapes.bevelled(shapes.box((-0.02, 0.05, -0.27), (0.02, 0.085, -0.02), "anodized_black", "leg"), 0.006),
                 shapes.cylinder((-0.022, 0.025, -0.255), (0.022, 0.025, -0.255), 0.025, "rubber", 16, "caster")]
        parts += turned(spoke, leg * 72.0)
    seat = 0.45
    parts.append(shapes.bevelled(shapes.box((-wide * 0.4, seat, -deep * 0.38), (wide * 0.4, seat + 0.08, deep * 0.36),
                                            "vinyl_seat", "seat"), 0.025))
    parts.append(shapes.box((-0.03, seat + 0.02, deep * 0.3), (0.03, seat + 0.2, deep * 0.36), "anodized_black", "spine"))
    parts.append(shapes.bevelled(shapes.box((-wide * 0.37, seat + 0.14, deep * 0.32), (wide * 0.37, tall, deep * 0.4),
                                            "vinyl_seat", "back"), 0.025))
    for side in (-1, 1):
        x = side * wide * 0.42
        parts.append(shapes.box((x - 0.015, seat + 0.04, -0.03), (x + 0.015, seat + 0.22, 0.01), "anodized_black", "arm_post"))
        parts.append(shapes.bevelled(shapes.box((x - 0.035, seat + 0.22, -deep * 0.3), (x + 0.035, seat + 0.25, deep * 0.15),
                                                "rubber", "armrest"), 0.01))
    return parts


def radio(x, y, z, wide, tall, deep):
    """A radio set on a surface at height y, its middle at (x, z), its face to -z: a grey case, a dark face with a
    frequency window, dials and a lit lamp."""
    front = z - deep / 2
    parts = [shapes.bevelled(shapes.box((x - wide / 2, y, front), (x + wide / 2, y + tall, z + deep / 2), "hammertone_grey",
                                        "case"), 0.006),
             shapes.box((x - wide / 2 + 0.015, y + 0.015, front - 0.004), (x + wide / 2 - 0.015, y + tall - 0.015, front),
                        "dark_panel", "face"),
             shapes.box((x - wide * 0.35, y + tall * 0.58, front - 0.006), (x + wide * 0.1, y + tall * 0.82, front - 0.004),
                        "glass_tinted", "window")]
    for at in (0.2, 0.45, 0.7):
        dial_x = x - wide / 2 + wide * at
        parts.append(shapes.cylinder((dial_x, y + tall * 0.3, front - 0.004), (dial_x, y + tall * 0.3, front - 0.024),
                                     0.016, "anodized_black", 20, "dial"))
    parts.append(shapes.cylinder((x + wide * 0.32, y + tall * 0.7, front - 0.004), (x + wide * 0.32, y + tall * 0.7,
                                                                                    front - 0.012), 0.008, "led_green",
                                 12, "lamp"))
    return parts


def comms(size, laid):
    """The comms desk: a steel desk with a modesty panel, two radio sets, a headset on a hook at its side and a desk
    lamp."""
    wide, tall, deep = size
    top = 0.75
    parts = [shapes.bevelled(shapes.box((-wide / 2, top - 0.035, -deep / 2), (wide / 2, top, deep / 2), "dark_panel", "top"), EDGE),
             shapes.box((-wide / 2 + 0.05, 0.12, deep / 2 - 0.05), (wide / 2 - 0.05, top - 0.035, deep / 2 - 0.03),
                        "painted_panel", "modesty")]
    for x in (-wide / 2 + 0.04, wide / 2 - 0.04):
        parts.append(shapes.box((x - 0.02, 0.0, -deep / 2 + 0.03), (x + 0.02, top - 0.035, deep / 2 - 0.03), "bare_steel", "side"))
    parts += radio(-0.38, top, 0.12, 0.42, 0.18, 0.3)
    parts += radio(0.12, top, 0.14, 0.36, 0.15, 0.28)
    parts += radio(-0.38, top + 0.18, 0.14, 0.38, 0.13, 0.26)
    # The headset hangs on a hook on the outside of the right side panel, as the reference has it (round three hung it
    # under the desk top between the side panels, where no view saw it: the detail-loss diagnosis, 2026-10-07).
    side_face = wide / 2 - 0.02
    band_top = top - 0.06
    cups = band_top - 0.135
    parts.append(shapes.cylinder((side_face, band_top + 0.008, 0.0), (side_face + 0.03, band_top + 0.008, 0.0), 0.006,
                                 "bare_steel", 12, "hook"))
    parts.append(shapes.box((side_face + 0.002, band_top - 0.015, -0.075), (side_face + 0.014, band_top, 0.075),
                            "anodized_black", "band"))
    for z in (-0.075, 0.06):
        parts.append(shapes.box((side_face + 0.002, cups + 0.02, z), (side_face + 0.014, band_top, z + 0.015),
                                "anodized_black", "band"))
        parts.append(shapes.cylinder((side_face + 0.002, cups, z + 0.0075), (side_face + 0.03, cups, z + 0.0075), 0.04,
                                     "gasket_black", 20, "ear"))
    lamp_x, lamp_z = wide / 2 - 0.2, 0.15
    parts.append(shapes.cylinder((lamp_x, top, lamp_z), (lamp_x, top + 0.02, lamp_z), 0.07, "anodized_black", 24, "lamp_base"))
    parts.append(shapes.cylinder((lamp_x, top + 0.02, lamp_z), (lamp_x - 0.02, top + 0.3, lamp_z + 0.02), 0.009,
                                 "bare_steel", 12, "lamp_arm"))
    parts.append(shapes.cylinder((lamp_x - 0.02, top + 0.3, lamp_z + 0.02), (lamp_x - 0.2, top + 0.38, lamp_z - 0.05),
                                 0.009, "bare_steel", 12, "lamp_arm"))
    parts.append(shapes.cylinder((lamp_x - 0.2, top + 0.38, lamp_z - 0.05), (lamp_x - 0.24, top + 0.3, lamp_z - 0.07),
                                 0.055, "machine_orange", 24, "shade"))
    return parts


def wrench(x, y, long, front):
    """A flat open-end wrench hanging upright on a board at depth `front`."""
    width = long * 0.12
    outline = [(x - width / 2, y), (x + width / 2, y), (x + width / 2, y + long * 0.82), (x + width, y + long * 0.86),
               (x + width * 0.6, y + long), (x + width * 0.15, y + long * 0.92), (x - width * 0.15, y + long * 0.92),
               (x - width * 0.6, y + long), (x - width, y + long * 0.86), (x - width / 2, y + long * 0.82)]
    return [shapes.prism(outline, front - 0.006, front, "brushed_steel_fine", "wrench")]


def toolboard(size, laid):
    """A pegboard of hand tools: a perforated board in a steel frame, wrenches, hammers and screwdrivers on hooks."""
    wide, tall, deep = size
    back = deep / 2
    face = back - 0.02
    parts = [shapes.box((-wide / 2 + 0.02, 0.02, face), (wide / 2 - 0.02, tall - 0.02, back), "perforated_blue_board", "board")]
    for low, high in (((-wide / 2, 0.0), (wide / 2, 0.025)), ((-wide / 2, tall - 0.025), (wide / 2, tall)),
                      ((-wide / 2, 0.0), (-wide / 2 + 0.025, tall)), ((wide / 2 - 0.025, 0.0), (wide / 2, tall))):
        parts.append(shapes.bevelled(shapes.box((*low, face - 0.01), (*high, back), "bare_steel", "frame"), 0.003))
    for at, long in enumerate((0.22, 0.26, 0.3, 0.34)):
        parts += wrench(-wide / 2 + 0.12 + at * 0.08, tall * 0.42, long, face)
    for at in range(2):
        x = 0.05 + at * 0.16
        parts.append(shapes.cylinder((x, tall * 0.2, face - 0.02), (x, tall * 0.62, face - 0.02), 0.014, "vinyl_orange", 16, "handle"))
        parts.append(shapes.bevelled(shapes.box((x - 0.06, tall * 0.62, face - 0.04), (x + 0.06, tall * 0.68, face),
                                                "cast_iron_dark", "head"), 0.006))
    for at in range(3):
        x = wide / 2 - 0.3 + at * 0.09
        parts.append(shapes.cylinder((x, tall * 0.62, face - 0.02), (x, tall * 0.78, face - 0.02), 0.016, "anodized_red", 16, "grip"))
        parts.append(shapes.cylinder((x, tall * 0.3, face - 0.02), (x, tall * 0.62, face - 0.02), 0.004, "bare_steel", 8, "shaft"))
    for x in (-wide / 2 + 0.15, -wide / 2 + 0.31, 0.05, 0.21, wide / 2 - 0.3, wide / 2 - 0.12):
        parts.append(shapes.cylinder((x, tall * 0.8, face), (x, tall * 0.8, face - 0.04), 0.004, "bare_steel", 8, "hook"))
    return parts

BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "inset_screen", "wall_screen",
    "wall_lower_plain", "wall_upper_plain", "hatch_wall_surround", "porthole_panel", "wall_skirting", "wall_cornice",
    "wall_corner_post", "roof_face_panel", "lattice_ring_rib", "lattice_hip_rib", "lattice_diamond_strut",
    "lattice_node_plate", "ceiling_cable_tray", "ceiling_duct", "ring_floor_plate", "floor_grating", "tread_mat",
    "hatch_frame", "hatch_hinge", "door_strip_lamp", "cable_bundle", "cable_drop", "backer",
    "wall_lower_vent", "wall_lower_patched", "wall_upper_cables", "wall_upper_pipes", "wall_upper_screen_recess",
    "wall_upper_patched", "hatch_leaf", "hatch_wheel", "hatch_window", "floor_access_hatch",
    "pit_wall_panel", "pit_floor_plate", "machine_bay_plate", "status_display",
    "wall_screen_cluster", "intercom_panel", "grab_bar", "pipe_straight", "notice_board", "stair_stringer",
    "console", "talllocker", "rack", "labbench", "chair", "comms", "toolboard")}


def build(kind, size, laid, name):
    """One code-built piece of `kind` at `size`, as one object whose material slots name library materials."""
    return shapes.joined(BUILDERS[kind](tuple(size), laid), name)
