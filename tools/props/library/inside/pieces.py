"""Runs inside Blender: the hub's plain plates, pipes and trims built in code (the sorter's allow-list, sorter.PLAIN:
the owner, 2026-10-07, code builds nothing with detail), each at the size the layout lays it, its parts naming their
library material.

    import pieces; whole = pieces.build("wall_upper_plain", (1.2, 2.0, 0.06), {"taper": 1.0})

Sizes are (wide, tall, deep) in metres in the kit frame (shapes.py): front toward -z, the back on the wall. Openings
are real holes at the shell's own sizes (the doorway 2.2 x 2.6 m, the porthole 0.6 m across), never a picture of
one.
"""

import json
import math

import numpy as np

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

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


def screw(x, y, surface):
    """A small screw head on a surface."""
    return shapes.cylinder((x, y, surface), (x, y, surface - 0.004), 0.006, "bare_steel", 10, "screw")


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
    """A roof face: a slab from its foot up the slope, a triangle to the apex (the hub's pyramid, `taper` 0) or a
    trapezoid whose head is `taper` of its foot (a dome's ring, modules batch one), stiffeners across it on the room's
    side every half metre up the slope, as a ribbed roof panel."""
    wide, tall, deep = size
    taper = float(laid.get("taper", 0.0))
    outline = [(-wide / 2, 0.0), (wide / 2, 0.0), (0.0, tall)] if taper <= 0.0 else \
        [(-wide / 2, 0.0), (wide / 2, 0.0), (taper * wide / 2, tall), (-taper * wide / 2, tall)]
    parts = [shapes.bevelled(shapes.prism(outline, -deep / 2 + 0.015, deep / 2, "painted_panel", "face"), EDGE)]
    for share in [step / tall for step in np.arange(0.4, tall * 0.85, 0.5)]:
        y = tall * share
        half = wide / 2 * (1 - (1 - taper) * share) - 0.08
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


def under_floor_box(size, laid):
    """An open box of plates under a set-in floor fitting's opening, its open side up (the kit frame's front, -z): the
    duct a grating breathes into, the trough a hatch covers. Dark inside, so a look through a grating meets depth."""
    wide, long, deep = size
    sheet = 0.006
    parts = [shapes.box((-wide / 2, 0.0, deep / 2 - sheet), (wide / 2, long, deep / 2), "dark_panel", "bottom")]
    for low, high in (((-wide / 2, 0.0), (-wide / 2 + sheet, long)), ((wide / 2 - sheet, 0.0), (wide / 2, long)),
                      ((-wide / 2, 0.0), (wide / 2, sheet)), ((-wide / 2, long - sheet), (wide / 2, long))):
        parts.append(shapes.box((*low, -deep / 2), (*high, deep / 2 - sheet), "dark_panel", "side"))
    return parts


# ---- Method B (hub round five, a test for the owner's pick, 2026-10-07): the room's shell and the fittings that repeat
# or join it, built in code with library surfaces so every copy matches the room exactly, each with every part its
# close-up shows (data/library/fittings.json lists them by the part names below; `parts_seen` reports which of them
# the room can see, and sorter.route sends a fitting to code only when all of them are). Print is a few label plates
# placed on purpose, never a picture's own colours.

WINDOW_HIGH = 1.85  # a hatch leaf's window middle over its foot (hub_kit.py doors)


def rounded_outline(low, high, radius, steps=6):
    """A rectangle's outline in the kit frame's x-y plane with its corners rounded to `radius`."""
    (left, bottom), (right, top) = low, high
    found = []
    for x, y, start in ((right - radius, top - radius, 0), (left + radius, top - radius, 90),
                        (left + radius, bottom + radius, 180), (right - radius, bottom + radius, 270)):
        for step in range(steps + 1):
            angle = math.radians(start + 90 * step / steps)
            found.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
    return found


def rounded_ring(low, high, radius, inset, depth_from, depth_to, material, name):
    """A raised border: a rounded rectangle `inset` wide round an opening of its own shape."""
    ring = shapes.prism(rounded_outline(low, high, radius), depth_from, depth_to, material, name)
    inner = rounded_outline((low[0] + inset, low[1] + inset), (high[0] - inset, high[1] - inset),
                            max(0.008, radius - inset))
    shapes.cut(ring, shapes.prism(inner, depth_from - 0.05, depth_to + 0.05, material, "cutter"))
    return ring


def turned(part, middle, degrees):
    """A part turned `degrees` about the kit frame's depth axis through `middle` (x, y): a sheet pinned askew."""
    centre = shapes.to_blender((middle[0], middle[1], 0.0))
    part.data.transform(Matrix.Translation(centre) @ Matrix.Rotation(math.radians(degrees), 4, "Y")
                        @ Matrix.Translation(-centre))
    return part


def tilted(part, middle, degrees):
    """A part tilted `degrees` about the kit frame's x axis through `middle` (y, z): a louvre's slat."""
    centre = shapes.to_blender((0.0, middle[0], middle[1]))
    part.data.transform(Matrix.Translation(centre) @ Matrix.Rotation(math.radians(degrees), 4, "X")
                        @ Matrix.Translation(-centre))
    return part


def label(x, y, wide, tall, surface, variant, turn=0.0, thick=0.004, name="label"):
    """A printed plate (a label, a sheet, a note) on a surface at depth `surface`, its middle at (x, y): a picture
    variant of the library's print family, placed on purpose; `turn` sets it askew."""
    plate = shapes.content_plate((x - wide / 2, y - tall / 2, surface - thick), (x + wide / 2, y + tall / 2, surface),
                                 variant, name)
    return turned(shapes.bevelled(plate, 0.0008), (x, y), turn) if turn else shapes.bevelled(plate, 0.0008)


def bolts_along(points, front, material="bare_steel"):
    return [bolt(x, y, front, material) for x, y in points]


def hatch_frame(size, laid):
    """The frame lining a doorway, as its close-up shows it: posts and a header in one piece with chamfered outer
    corners, a stepped lip round the opening, a rubber seal inside it, bolts down the posts and along the header."""
    wide, tall, deep = size
    half, top = DOORWAY[0] / 2, DOORWAY[1]
    front = -deep / 2
    chamfer = min(0.08, (wide / 2 - half) * 0.8)
    outline = [(-wide / 2, 0.0), (-half, 0.0), (-half, top), (half, top), (half, 0.0), (wide / 2, 0.0),
               (wide / 2, tall - chamfer), (wide / 2 - chamfer, tall), (-wide / 2 + chamfer, tall),
               (-wide / 2, tall - chamfer)]
    parts = [shapes.bevelled(shapes.prism(outline, front + 0.012, deep / 2, "dark_panel", "frame"), 0.006)]
    lip = 0.03
    lip_outline = [(-half - lip, 0.0), (-half, 0.0), (-half, top), (half, top), (half, 0.0), (half + lip, 0.0),
                   (half + lip, top + lip), (-half - lip, top + lip)]
    parts.append(shapes.bevelled(shapes.prism(lip_outline, front, front + 0.012, "dark_panel", "lip"), 0.003))
    seal = 0.018
    parts += [shapes.box((-half, 0.0, front + 0.03), (-half + seal, top, front + 0.09), "rubber", "seal"),
              shapes.box((half - seal, 0.0, front + 0.03), (half, top, front + 0.09), "rubber", "seal"),
              shapes.box((-half, top - seal, front + 0.03), (half, top, front + 0.09), "rubber", "seal")]
    post = (half + lip + wide / 2) / 2
    ys = [0.2 + step * (top - 0.3) / 7 for step in range(8)]
    points = [(side * post, y) for side in (-1, 1) for y in ys]
    points += [(x, (top + lip + tall) / 2) for x in np.linspace(-half + 0.2, half - 0.2, 6)]
    parts += bolts_along(points, front + 0.012)
    return parts


def hatch_leaf(size, laid):
    """A hatch's door leaf, as its close-up shows it: a thick slab with rounded corners, a raised border round its
    face and a lower lip inside that, a framed name plate, a sticker, and the round hole its window is set in (its
    window and wheel are fittings of their own, laid on it)."""
    wide, tall, deep = size
    front = -deep / 2
    low, high = (-wide / 2, 0.0), (wide / 2, tall)
    slab = shapes.prism(rounded_outline(low, high, 0.14), front + 0.02, deep / 2, "painted_panel", "slab")
    shapes.cut(slab, shapes.cylinder((0.0, WINDOW_HIGH, -deep), (0.0, WINDOW_HIGH, deep), 0.15, "painted_panel", 48,
                                     "cutter"))
    parts = [shapes.bevelled(slab, 0.008)]
    parts.append(shapes.bevelled(rounded_ring(low, high, 0.14, 0.09, front, front + 0.02, "painted_panel", "rim"),
                                 0.004))
    parts.append(shapes.bevelled(rounded_ring((-wide / 2 + 0.14, 0.14), (wide / 2 - 0.14, tall - 0.14), 0.06, 0.022,
                                              front + 0.011, front + 0.02, "painted_panel", "lip"), 0.002))
    plate_x, plate_y = -0.48, 2.22
    parts.append(shapes.bevelled(rounded_ring((plate_x - 0.2, plate_y - 0.11), (plate_x + 0.2, plate_y + 0.11), 0.02,
                                              0.025, front + 0.008, front + 0.02, "painted_panel", "plate_frame"),
                                 0.002))
    parts.append(label(plate_x, plate_y, 0.33, 0.15, front + 0.02, "label_pressure_door"))
    parts.append(label(0.52, 1.6, 0.26, 0.09, front + 0.02, "label_check_seal", turn=-2.0, name="sticker"))
    return parts


def hatch_wheel(size, laid):
    """The locking wheel, as its close-up shows it: a round rim, four spokes and a boss with a hole through it,
    standing off the leaf on a stem."""
    wide, tall, deep = size
    middle = (0.0, tall / 2)
    radius = min(wide, tall) / 2
    front = -deep / 2
    parts = [shapes.bevelled(shapes.ring((*middle, front + 0.03), (*middle, front), radius, radius - 0.035,
                                         "bare_steel", 48, "rim"), 0.006)]
    for angle in (0.0, math.pi / 2):
        along = (math.cos(angle) * (radius - 0.02), math.sin(angle) * (radius - 0.02))
        parts.append(shapes.cylinder((middle[0] - along[0], middle[1] - along[1], front + 0.015),
                                     (middle[0] + along[0], middle[1] + along[1], front + 0.015), 0.013,
                                     "bare_steel", 12, "spoke"))
    parts.append(shapes.bevelled(shapes.ring((*middle, front + 0.03), (*middle, front + 0.002), 0.055, 0.018,
                                             "bare_steel", 32, "boss"), 0.003))
    parts.append(shapes.cylinder((*middle, front + 0.03), (*middle, deep / 2), 0.03, "dark_panel", 24, "stem"))
    return parts


def hatch_window(size, laid):
    """A hatch's round window, as its close-up shows it: a flange ringed with bolts, a raised inner ring and the
    glass, set through the leaf."""
    wide, tall, deep = size
    middle = (0.0, tall / 2)
    outer = min(wide, tall) / 2
    front = -deep / 2
    parts = [shapes.bevelled(shapes.ring((*middle, front + 0.008), (*middle, deep / 2), outer, 0.13, "dark_panel", 48,
                                         "flange"), 0.004),
             shapes.bevelled(shapes.ring((*middle, front + 0.008), (*middle, front), 0.155, 0.13, "dark_panel", 48,
                                         "inner_ring"), 0.002),
             shapes.cylinder((*middle, -0.004), (*middle, 0.004), 0.135, "glass_tinted", 48, "glass")]
    for at in range(12):
        angle = 2 * math.pi * at / 12
        parts.append(bolt(outer * 0.86 * math.cos(angle), middle[1] + outer * 0.86 * math.sin(angle), front + 0.008))
    return parts


def hatch_hinge(size, laid):
    """A heavy hinge, as its close-up shows it: a leaf screwed to the frame, two knuckles on a pin with caps, a web
    joining them."""
    wide, tall, deep = size
    radius = min(wide, deep) * 0.3
    knuckle_z = -deep / 2 + radius
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.02, deep / 2 - 0.03), (wide / 2, tall - 0.02, deep / 2),
                                        "dark_panel", "leaf"), 0.004)]
    for low, high in ((0.03, tall * 0.48), (tall * 0.52, tall - 0.03)):
        parts.append(shapes.bevelled(shapes.cylinder((0.0, low, knuckle_z), (0.0, high, knuckle_z), radius,
                                                     "bare_steel", 24, "knuckle"), 0.003))
    for low, high in ((0.012, 0.03), (tall - 0.03, tall - 0.012)):
        parts.append(shapes.cylinder((0.0, low, knuckle_z), (0.0, high, knuckle_z), radius * 0.6, "bare_steel", 16,
                                     "pin"))
    parts.append(shapes.box((-0.008, 0.05, knuckle_z), (0.008, tall - 0.05, deep / 2 - 0.03), "dark_panel", "web"))
    for x in (-wide / 2 + 0.022, wide / 2 - 0.022):
        for y in (0.06, tall / 2, tall - 0.06):
            parts.append(screw(x, y, deep / 2 - 0.03))
    return parts


def hatch_wall_surround(size, laid):
    """A door's wall, as its close-up shows it: bolted plates round the doorway (two jambs and a header), a seam strip
    down each jamb's edges, the hatch's name on a label over the doorway."""
    wide, tall, deep = size
    half = DOORWAY[0] / 2
    parts = bolted_plate((-wide / 2, 0.0), (-half, tall), deep, "painted_panel")
    parts += bolted_plate((half, 0.0), (wide / 2, tall), deep, "painted_panel")
    parts += bolted_plate((-half, DOORWAY[1]), (half, tall), deep, "painted_panel")
    front = -deep / 2
    for x in (-wide / 2 + 0.012, -half - 0.012, half + 0.012, wide / 2 - 0.012):
        parts.append(shapes.bevelled(shapes.box((x - 0.012, 0.0, front - 0.006), (x + 0.012, tall, front + 0.02),
                                                "dark_panel", "seam"), 0.003))
    parts = with_openings(parts, laid, deep)
    parts.append(label(0.0, (DOORWAY[1] + tall) / 2, 0.72, 0.18, front + 0.007, laid.get("label", "label_west_hatch")))
    return parts


def porthole_panel(size, laid):
    """A wall plate with the porthole's real hole through it, as its close-up shows it: bolts round its border, a
    dark flange ringed with bolts round the hole and a raised inner ring, a small name plate under it; open, its
    glass the shell's."""
    wide, tall, deep = size
    middle = tall / 2
    front = -deep / 2
    face = front + 0.03
    plate = shapes.prism(rounded_outline((-wide / 2, 0.0), (wide / 2, tall), 0.03), face, deep / 2, "painted_panel",
                         "plate")
    shapes.cut(plate, shapes.cylinder((0.0, middle, -deep), (0.0, middle, deep), PORTHOLE_RADIUS, "painted_panel", 64,
                                      "cutter"))
    parts = [shapes.bevelled(plate, EDGE)]
    across = np.linspace(-wide / 2 + 0.05, wide / 2 - 0.05, 6)
    parts += bolts_along([(x, y) for x in across for y in (0.05, tall - 0.05)]
                         + [(x, y) for x in (-wide / 2 + 0.05, wide / 2 - 0.05) for y in across[1:-1] + tall / 2],
                         face)
    parts.append(shapes.bevelled(shapes.ring((0.0, middle, face), (0.0, middle, face - 0.016), 0.43, PORTHOLE_RADIUS,
                                             "dark_panel", 64, "flange"), 0.004))
    parts.append(shapes.bevelled(shapes.ring((0.0, middle, face - 0.016), (0.0, middle, front), 0.36,
                                             PORTHOLE_RADIUS, "dark_panel", 64, "inner_ring"), 0.003))
    for at in range(12):
        angle = 2 * math.pi * at / 12
        parts.append(bolt(0.395 * math.cos(angle), middle + 0.395 * math.sin(angle), face - 0.016))
    parts.append(shapes.bevelled(shapes.box((-0.15, 0.065, face - 0.004), (0.15, 0.135, face), "bare_steel",
                                            "name_plate"), 0.001))
    parts.append(label(0.0, 0.1, 0.22, 0.05, face - 0.004, "label_porthole"))
    parts += [screw(x, 0.1, face - 0.004) for x in (-0.13, 0.13)]
    return parts


def wall_lower_vent(size, laid):
    """A lower wall plate with an air return, as its close-up shows it: a slab with a raised face plate and bolts
    round it, the opening cut through it with a bolted flange and an inner frame round it, louvres slanting down
    across it in front of a dark back, a small label; the louvres sit in a real pocket, nothing over them."""
    wide, tall, deep = size
    back, front = deep / 2, -deep / 2
    face = front + 0.007
    vent_wide, vent_tall, vent_high = min(0.62, wide - 0.45), 0.38, tall * 0.5
    opening = ((-vent_wide / 2, vent_high - vent_tall / 2), (vent_wide / 2, vent_high + vent_tall / 2))
    slab = shapes.box((-wide / 2, 0.0, face + 0.008), (wide / 2, tall, back), "dark_panel", "slab")
    face_plate = shapes.box((-wide / 2 + 0.03, 0.03, face), (wide / 2 - 0.03, tall - 0.03, face + 0.008), "dark_panel",
                            "face")
    for part in (slab, face_plate):
        shapes.cut(part, shapes.box((*opening[0], front - 0.05), (*opening[1], back - 0.006), "dark_panel", "cutter"))
    parts = [shapes.bevelled(slab, EDGE), shapes.bevelled(face_plate, EDGE)]
    across = np.linspace(-wide / 2 + 0.06, wide / 2 - 0.06, 8)
    up = np.linspace(0.06, tall - 0.06, 7)
    parts += bolts_along([(x, y) for x in across for y in (up[0], up[-1])]
                         + [(x, y) for x in (across[0], across[-1]) for y in up[1:-1]], face)
    (left, bottom), (right, top) = opening
    flange = rounded_ring((left - 0.09, bottom - 0.09), (right + 0.09, top + 0.09), 0.02, 0.09, face - 0.01, face,
                          "dark_panel", "vent_flange")
    parts.append(shapes.bevelled(flange, 0.003))
    parts += bolts_along([(x, y) for x in np.linspace(left - 0.045, right + 0.045, 5)
                          for y in (bottom - 0.045, top + 0.045)]
                         + [(x, (bottom + top) / 2) for x in (left - 0.045, right + 0.045)], face - 0.01)
    parts.append(shapes.bevelled(rounded_ring((left - 0.025, bottom - 0.025), (right + 0.025, top + 0.025), 0.01,
                                              0.025, face - 0.018, face - 0.01, "dark_panel", "vent_frame"), 0.002))
    parts.append(shapes.box((left, bottom, back - 0.006), (right, top, back), "anodized_black", "vent_back"))
    slats = 9
    for at in range(slats):
        y = bottom + (top - bottom) * (at + 0.5) / slats
        slat = shapes.box((left + 0.002, y - 0.004, face - 0.004), (right - 0.002, y + 0.004, face + 0.03),
                          "dark_panel", "slat")
        parts.append(tilted(shapes.bevelled(slat, 0.0015), (y, face + 0.013), -38.0))
    parts.append(label(wide / 2 - 0.2, tall - 0.16, 0.2, 0.06, face, "label_air_return"))
    return parts


def notice_board(size, laid):
    """A notice board, as its close-up shows it: a steel tray frame round a cork board, sheets and notes pinned on it
    in two tidy rows, a pin at each sheet's head."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    rim = 0.035
    parts = [shapes.bevelled(rounded_ring((-wide / 2, 0.0), (wide / 2, tall), 0.02, rim, front, back, "painted_panel",
                                          "frame"), 0.004),
             shapes.box((-wide / 2 + rim, rim, front + 0.016), (wide / 2 - rim, tall - rim, back - 0.004),
                        "wood_board", "board"),
             shapes.box((-wide / 2, 0.0, back - 0.004), (wide / 2, tall, back), "painted_panel", "back")]
    board = front + 0.016
    sheets = (("sheet_eva", 0.235, 0.395, 0.19, 0.25, 1.2), ("sheet_roster", 0.0, 0.40, 0.19, 0.25, -0.8),
              ("sheet_log", -0.235, 0.39, 0.19, 0.25, 0.6), ("sheet_plan", 0.13, 0.155, 0.27, 0.18, -0.5))
    for variant, x, y, sheet_wide, sheet_tall, turn in sheets:
        parts.append(label(x, y, sheet_wide, sheet_tall, board, variant, turn, 0.004, "sheet"))
        parts.append(shapes.cylinder((x, y + sheet_tall / 2 - 0.02, board - 0.003),
                                     (x, y + sheet_tall / 2 - 0.02, board - 0.011), 0.007, "anodized_red", 12, "pin"))
    for variant, x, y, turn in (("note_filter", -0.12, 0.16, 3.0), ("note_link", -0.26, 0.15, -2.5)):
        parts.append(label(x, y, 0.09, 0.09, board, variant, turn, 0.004, "note"))
    return parts


def parts_seen(parts, samples=80, views=((0.0, 0.0), (35.0, 0.0), (-35.0, 0.0), (0.0, 30.0), (0.0, -30.0))):
    """Per part name (an object's name before Blender's .001), the share of its front-facing surface the room can see
    from in front of the piece (five views, straight on and 35/30 degrees off): a slat buried in its plate reads 0.
    Sampled at points spread over its surface by area (a face's middle alone hid a spoke behind the boss it runs
    through), a point seen when nothing of the piece lies between it and a view it faces."""
    together = bmesh.new()
    for part in parts:
        together.from_mesh(part.data)
    tree = BVHTree.FromBMesh(together)
    together.free()
    directions = []
    for across, up in views:
        turn = Matrix.Rotation(math.radians(across), 3, "Z") @ Matrix.Rotation(math.radians(up), 3, "X")
        directions.append((turn @ Vector((0.0, 1.0, 0.0))).normalized())  # the kit's front (-z) is Blender's +y
    counts = {}
    for part in parts:
        seen = shown = 0
        for point, normal in surface_points(part, samples):
            facing = [direction for direction in directions if normal.dot(direction) > 0.1]
            if not facing:
                continue
            shown += 1
            start = point + normal * 0.0003
            seen += any(tree.ray_cast(start, direction, 10.0)[0] is None for direction in facing)
        total = counts.setdefault(part.name.split(".")[0], [0, 0])
        total[0] += seen
        total[1] += shown
    return {name: round(seen / shown, 3) if shown else 0.0 for name, (seen, shown) in sorted(counts.items())}


def surface_points(part, count):
    """`count` points on a part's surface, spread by area (a fixed seed, so a build reads the same each time), each
    with its triangle's normal."""
    mesh = part.data
    mesh.calc_loop_triangles()
    triangles = list(mesh.loop_triangles)
    if not triangles:
        return []
    areas = np.array([triangle.area for triangle in triangles])
    chosen = np.random.default_rng(7).choice(len(triangles), size=count, p=areas / areas.sum())
    weights = np.random.default_rng(11).dirichlet((1.0, 1.0, 1.0), size=count)
    found = []
    for index, weight in zip(chosen, weights):
        triangle = triangles[index]
        corners = [mesh.vertices[vertex].co for vertex in triangle.vertices]
        found.append((sum((corner * float(share) for corner, share in zip(corners, weight)), Vector()),
                      triangle.normal))
    return found


# ---- Round six, method B: the hub's wall fittings built in code with library surfaces, each with every part its
# close-up shows (data/library/fittings.json), print as a few label plates on clear flat areas.

def wall_rivet(x, y, front, radius=0.0055, material="bare_steel"):
    """A small round rivet head standing out of a face at depth `front`."""
    return shapes.cylinder((x, y, front), (x, y, front - 0.004), radius, material, 10, "rivet")


def wall_sphere(middle, radius, material, name, segments=24):
    """A ball at a kit-frame point (a lamp's dome, a bar's bend)."""
    built = bmesh.new()
    bmesh.ops.create_uvsphere(built, u_segments=segments, v_segments=segments // 2, radius=radius)
    bmesh.ops.translate(built, verts=built.verts, vec=shapes.to_blender(middle))
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def wall_pocket(part, low, high, depth_from, depth_to):
    """A real pocket cut into a part: a box between two (x, y) corners from `depth_from` to `depth_to`."""
    shapes.cut(part, shapes.box((*low, depth_from), (*high, depth_to), "rubber", "cutter"))
    return part


def wall_screen_part(x, y, wide, tall, surface, variant="screen", rim=0.012, name="screen"):
    """A screen set in a face at depth `surface`: an anodized bezel standing proud round it and the glass inside, its
    content a picture variant of the library's screen family (make_kit splits the glowing glass off)."""
    bezel = shapes.box((x - wide / 2, y - tall / 2, surface - 0.008), (x + wide / 2, y + tall / 2, surface),
                       "anodized_black", "bezel")
    shapes.cut(bezel, shapes.box((x - wide / 2 + rim, y - tall / 2 + rim, surface - 0.02),
                                 (x + wide / 2 - rim, y + tall / 2 - rim, surface + 0.01), "anodized_black", "cutter"))
    glass = shapes.content_plate((x - wide / 2 + rim, y - tall / 2 + rim, surface - 0.004),
                                 (x + wide / 2 - rim, y + tall / 2 - rim, surface), variant, name)
    return [shapes.bevelled(bezel, 0.002), glass]


def wall_button(x, y, wide, tall, front, material="dark_panel", name="button"):
    return shapes.bevelled(shapes.box((x - wide / 2, y - tall / 2, front - 0.006), (x + wide / 2, y + tall / 2, front),
                                      material, name), 0.0015)


def wall_patch(outline, front, material, rivet_spacing, inset):
    """A repair plate (a polygon outline) riveted over a face at depth `front`, rivets along its edges."""
    plate = shapes.bevelled(shapes.prism(outline, front - 0.006, front, material, "patch"), 0.002)
    rivets = []
    count = len(outline)
    middle = np.mean(np.array(outline), axis=0)
    for at in range(count):
        start, end = np.array(outline[at]), np.array(outline[(at + 1) % count])
        start = start + (middle - start) / np.linalg.norm(middle - start) * inset
        end = end + (middle - end) / np.linalg.norm(middle - end) * inset
        steps = max(1, int(np.linalg.norm(end - start) / rivet_spacing))
        for step in range(steps):
            x, y = start + (end - start) * step / steps
            rivets.append(wall_rivet(float(x), float(y), front - 0.006))
    return [plate] + rivets


def wall_lower_patched(size, laid):
    """A lower wall plate with a repair, as its close-up shows it: the bolted plate, a stencilled KEEP CLEAR /
    SERVICE PANEL high on its open side, and a riveted repair plate with a cut corner over its lower right."""
    wide, tall, deep = size
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), deep, "dark_panel")
    face = -deep / 2 + 0.007
    right, left, top = -wide / 2 + 0.1, 0.1, tall * 0.56
    corner = 0.09
    outline = [(right, 0.11), (left, 0.11), (left, top - corner), (left - corner, top), (right, top)]
    parts += wall_patch(outline, face, "hammertone_grey", 0.05, 0.02)
    parts.append(label(0.2, tall * 0.84, 0.46, 0.11, face, "stencil_keep_clear", thick=0.004, name="stencil"))
    parts.append(label(0.2, tall * 0.72, 0.56, 0.11, face, "stencil_service_panel", thick=0.004,
                       name="stencil"))
    return parts


def wall_upper_patched(size, laid):
    """An upper wall plate with a repair, as its close-up shows it: the bolted plate and a bolted repair plate high
    on it."""
    wide, tall, deep = size
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), deep, "painted_panel")
    face = -deep / 2 + 0.007
    low, high = (-wide * 0.36, tall * 0.68), (wide * 0.36, tall * 0.92)
    plate = shapes.bevelled(shapes.box((*low, face - 0.008), (*high, face), "hammertone_grey", "patch"), 0.003)
    parts.append(plate)
    across = np.linspace(low[0] + 0.035, high[0] - 0.035, 4)
    parts += [bolt(float(x), y, face - 0.008) for x in across for y in (low[1] + 0.035, high[1] - 0.035)]
    parts += [bolt(x, (low[1] + high[1]) / 2, face - 0.008) for x in (low[0] + 0.035, high[0] - 0.035)]
    return parts


def wall_upper_cables(size, laid):
    """An upper wall plate with a cable run, as its close-up shows it: the plate set back, three cables along its top
    in clamps, two of them dropping down one side into a junction box, a label and a note beside the drop."""
    wide, tall, deep = size
    plate_deep = 0.06
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), plate_deep, "painted_panel", back=deep / 2)
    face = deep / 2 - plate_deep + 0.007
    radius = 0.011
    drop_x = wide / 2 - 0.13
    box_low, box_high = (drop_x - 0.07, tall * 0.42), (drop_x + 0.07, tall * 0.42 + 0.14)
    for at, colour in enumerate(("cable_black", "cable_grey", "cable_black")):
        y = tall - 0.1 - at * 0.026
        z = face - radius - 0.002
        parts.append(shapes.cylinder((-wide / 2, y, z), (wide / 2, y, z), radius, colour, 14, "cable"))
        if at < 2:
            x = drop_x + (at - 0.5) * 0.03
            parts.append(shapes.cylinder((x, y, z), (x, box_high[1], z), radius, colour, 14, "cable"))
            parts.append(wall_sphere((x, y, z), radius, colour, "cable", 12))
    for x in (-wide / 2 + 0.2, 0.0, drop_x - 0.12):
        parts.append(shapes.bevelled(shapes.box((x - 0.015, tall - 0.18, face - 0.03), (x + 0.015, tall - 0.06, face),
                                                "bare_steel", "clamp"), 0.002))
    parts.append(shapes.bevelled(shapes.box((drop_x - 0.015, tall * 0.7, face - 0.03), (drop_x + 0.015,
                                                                                    tall * 0.7 + 0.04, face),
                                            "bare_steel", "clamp"), 0.002))
    parts.append(shapes.bevelled(shapes.box((*box_low, face - 0.05), (*box_high, face), "dark_panel",
                                            "junction_box"), 0.004))
    parts += [screw(x, y, face - 0.05) for x in (box_low[0] + 0.015, box_high[0] - 0.015)
              for y in (box_low[1] + 0.015, box_high[1] - 0.015)]
    parts.append(label(drop_x - 0.32, tall * 0.62, 0.26, 0.06, face, "label_cable_run"))
    parts.append(label(drop_x - 0.27, tall * 0.53, 0.1, 0.1, face, "note_link", turn=-4.0, thick=0.004, name="note"))
    return parts


def wall_upper_pipes(size, laid):
    """An upper wall plate with a pipe run, as its close-up shows it: the plate set back, three pipes along its top in
    two strap clamps, a caution label under them."""
    wide, tall, deep = size
    plate_deep = 0.06
    parts = bolted_plate((-wide / 2, 0.0), (wide / 2, tall), plate_deep, "painted_panel", back=deep / 2)
    face = deep / 2 - plate_deep + 0.007
    radius = 0.022
    z = face - radius - 0.008
    ys = [tall - 0.09 - at * 0.06 for at in range(3)]
    for y in ys:
        parts.append(shapes.cylinder((-wide / 2, y, z), (wide / 2, y, z), radius, "pipe_steel", 20, "pipe"))
    for x in (-wide / 2 + 0.25, wide / 2 - 0.25):
        parts.append(shapes.bevelled(shapes.box((x - 0.016, ys[-1] - radius - 0.02, face - 0.004),
                                                (x + 0.016, ys[0] + radius + 0.02, face), "bare_steel", "bracket"),
                                     0.002))
        parts.append(shapes.bevelled(shapes.box((x - 0.014, ys[-1] - radius - 0.006, z - radius - 0.006),
                                                (x + 0.014, ys[0] + radius + 0.006, z - radius), "bare_steel",
                                                "strap"), 0.002))
        parts += [screw(x, y, face - 0.004) for y in (ys[-1] - radius - 0.01, ys[0] + radius + 0.01)]
    parts.append(label(wide / 2 - 0.22, ys[-1] - 0.12, 0.26, 0.06, face, "label_caution_hot"))
    return parts


def wall_upper_screen_recess(size, laid):
    """An upper wall plate with a recess, as its close-up shows it: a plate with a deep pocket in its upper part, a
    dark back to the pocket, a small screen unit fixed to the pocket's back, a label on the plate below."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    low, high = (-wide / 2 + 0.12, tall * 0.56), (wide / 2 - 0.1, tall * 0.94)
    plate = shapes.box((-wide / 2, 0.0, front + 0.006), (wide / 2, tall, back), "painted_panel", "plate")
    wall_pocket(plate, low, high, front - 0.05, back - 0.012)
    rim = rounded_ring((low[0] - 0.03, low[1] - 0.03), (high[0] + 0.03, high[1] + 0.03), 0.015, 0.03, front,
                       front + 0.006, "painted_panel", "rim")
    parts = [shapes.bevelled(plate, EDGE), shapes.bevelled(rim, 0.002),
             shapes.box((*low, back - 0.017), (*high, back - 0.012), "dark_panel", "recess")]
    unit_x, unit_y = high[0] - 0.24, low[1] + 0.17
    surface = back - 0.017
    parts.append(shapes.bevelled(shapes.box((unit_x - 0.15, unit_y - 0.1, surface - 0.025),
                                            (unit_x + 0.15, unit_y + 0.1, surface), "dark_panel", "unit"), 0.003))
    parts += wall_screen_part(unit_x, unit_y + 0.015, 0.22, 0.13, surface - 0.025, "screen")
    parts += [wall_button(unit_x - 0.1 + 0.05 * at, unit_y - 0.075, 0.03, 0.018, surface - 0.025) for at in range(5)]
    parts.append(label(-wide / 2 + 0.3, low[1] - 0.12, 0.24, 0.06, front + 0.006, "label_storage_a"))
    return parts


def status_display(size, laid):
    """The big status display, as its close-up shows it: a housing with cut corners, a raised bezel round one big
    screen, a guard plate over each corner, screws, a maker's plate under the screen."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    cut = 0.08
    outline = [(-wide / 2 + cut, 0.0), (wide / 2 - cut, 0.0), (wide / 2, cut), (wide / 2, tall - cut),
               (wide / 2 - cut, tall), (-wide / 2 + cut, tall), (-wide / 2, tall - cut), (-wide / 2, cut)]
    face = front + 0.022
    parts = [shapes.bevelled(shapes.prism(outline, face, back, "dark_panel", "housing"), 0.006)]
    rim = 0.07
    parts.append(shapes.bevelled(rounded_ring((-wide / 2 + 0.03, 0.03), (wide / 2 - 0.03, tall - 0.03), 0.03,
                                              rim - 0.03, front + 0.008, face, "dark_panel", "bezel"), 0.003))
    parts.append(shapes.content_plate((-wide / 2 + rim, rim, face - 0.004), (wide / 2 - rim, tall - rim, face),
                                      laid.get("screen", "screen"), "screen"))
    for sx in (-1, 1):
        for up in (1, -1):
            x, y = sx * (wide / 2 - 0.05), 0.05 if up == 1 else tall - 0.05
            guard = [(x, y), (x - sx * 0.07, y), (x, y + up * 0.07)]
            parts.append(shapes.bevelled(shapes.prism(guard, front, front + 0.008, "bare_steel", "corner"), 0.002))
            parts.append(screw(x - sx * 0.02, y + up * 0.02, front))
    parts.append(label(0.0, 0.05, 0.3, 0.03, front + 0.008, "label_life_support"))
    return parts


def wall_screen_cluster(size, laid):
    """Three screens in one housing, as its close-up shows it: a wide housing with a tab under its middle, three boxy
    monitors with deep bezels, a label strip over them, buttons under each, a small status screen in the tab and a
    handle at each end."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    face = front + 0.04
    tab = 0.18
    outline = [(-wide / 2 + 0.045, tab), (-wide * 0.18, tab), (-wide * 0.15, 0.0), (wide * 0.15, 0.0), (wide * 0.18, tab),
               (wide / 2 - 0.045, tab), (wide / 2 - 0.045, tall), (-wide / 2 + 0.045, tall)]
    parts = [shapes.bevelled(shapes.prism(outline, face, back, "painted_panel", "housing"), 0.005)]
    monitor = 0.29
    middle_y = tab + (tall - tab) * 0.47
    for at, variant in enumerate(("screen", "screen_amber", "screen")):
        x = (at - 1) * 0.33
        low, high = (x - monitor / 2, middle_y - monitor / 2 + 0.02), (x + monitor / 2, middle_y + monitor / 2 - 0.02)
        parts.append(shapes.bevelled(rounded_ring(low, high, 0.03, 0.045, front, face, "painted_panel", "monitor"),
                                     0.004))
        parts.append(shapes.content_plate((low[0] + 0.045, low[1] + 0.045, face - 0.004),
                                          (high[0] - 0.045, high[1] - 0.045, face), variant, "screen"))
        parts += [wall_button(x - 0.06 + 0.06 * step, tab + 0.04, 0.035, 0.02, face) for step in range(3)]
    for at, variant in enumerate(("label_air", "label_power", "label_water")):
        parts.append(label((at - 1) * 0.33, tall - 0.04, 0.16, 0.04, face, variant))
    parts += wall_screen_part(0.0, tab * 0.48, 0.22, 0.12, face, "screen_amber", name="status_screen")
    for side in (-1, 1):
        x = side * (wide / 2 - 0.012)
        parts.append(shapes.cylinder((x, tab + 0.05, face - 0.03), (x, tall - 0.05, face - 0.03), 0.012,
                                     "bare_steel", 16, "handle"))
        for y in (tab + 0.05, tall - 0.05):
            parts.append(shapes.cylinder((x, y, face - 0.03), (x - side * 0.04, y, face - 0.03), 0.011, "bare_steel",
                                         16, "handle"))
            parts.append(wall_sphere((x, y, face - 0.03), 0.012, "bare_steel", "handle", 12))
    return parts


def intercom_panel(size, laid):
    """An intercom, as its close-up shows it: a box with a raised rim, a screw at each corner, a round speaker grille
    of slots set into its face, a call button, and its two labels."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    face = front + 0.008
    housing = shapes.box((-wide / 2, 0.0, face), (wide / 2, tall, back), "dark_panel", "housing")
    grille_y, radius = tall * 0.7, min(0.075, wide * 0.32)
    shapes.cut(housing, shapes.cylinder((0.0, grille_y, face - 0.02), (0.0, grille_y, face + 0.016), radius,
                                        "rubber", 40, "cutter"))
    parts = [shapes.bevelled(housing, 0.004),
             shapes.bevelled(rounded_ring((-wide / 2, 0.0), (wide / 2, tall), 0.012, 0.014, front, face, "dark_panel",
                                          "rim"), 0.002),
             shapes.cylinder((0.0, grille_y, face + 0.012), (0.0, grille_y, face + 0.016), radius, "anodized_black",
                             40, "grille")]
    for step in range(-4, 5):
        y = grille_y + step * radius * 0.21
        half = math.sqrt(max(0.0, radius ** 2 - (y - grille_y) ** 2)) - 0.004
        if half > 0.01:
            parts.append(shapes.box((-half, y - 0.0045, face + 0.002), (half, y + 0.0045, face + 0.012), "dark_panel",
                                    "slat"))
    parts += [screw(x, y, face) for x in (-wide / 2 + 0.022, wide / 2 - 0.022) for y in (0.022, tall - 0.022)]
    parts.append(label(0.012, tall * 0.33, wide * 0.6, 0.04, face, "intercom_print"))
    parts.append(label(0.03, tall * 0.2, wide * 0.52, 0.04, face, "label_handset"))
    parts.append(shapes.cylinder((-wide * 0.3, tall * 0.2, face), (-wide * 0.3, tall * 0.2, face - 0.01), 0.016,
                                 "brushed_steel_fine", 20, "button"))
    return parts


def small_readout(size, laid):
    """A small readout, as its close-up shows it: a box with rounded corners and a screw at each, a framed screen,
    four buttons down its side and three under the screen, a knob, a TEMP label."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    face = front + 0.016
    parts = [shapes.bevelled(shapes.prism(rounded_outline((-wide / 2, 0.0), (wide / 2, tall), 0.015), face, back,
                                          "painted_panel", "housing"), 0.003)]
    screen_x, screen_y = wide * 0.1, tall * 0.55
    parts += wall_screen_part(screen_x, screen_y, wide * 0.58, tall * 0.5, face, "screen_amber")
    parts += [wall_button(-wide * 0.36, tall * (0.35 + 0.13 * at), 0.04, 0.018, face) for at in range(4)]
    parts += [wall_button(wide * (0.28 - 0.18 * at), tall * 0.13, 0.04, 0.018, face) for at in range(3)]
    parts.append(shapes.bevelled(shapes.cylinder((-wide * 0.36, tall * 0.13, face), (-wide * 0.36, tall * 0.13,
                                                                                   face - 0.016), 0.022,
                                                 "anodized_black", 24, "knob"), 0.002))
    parts += [screw(x, y, face) for x in (-wide / 2 + 0.015, wide / 2 - 0.015) for y in (0.015, tall - 0.015)]
    parts.append(label(wide * 0.28, tall * 0.9, 0.08, 0.03, face, "label_temp"))
    return parts


def door_control_box(size, laid):
    """A door's control box, as its close-up shows it: a steel box with a door on hinges down one side, a keypad in a
    bezel with a small screen over it, a status lamp, a label, a caution sticker and a MAIN BOX sheet."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    face = front + 0.012
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, face), (wide / 2, tall, back), "painted_panel", "housing"),
                             0.004),
             shapes.bevelled(shapes.box((-wide / 2 + 0.012, 0.012, front + 0.004), (wide / 2 - 0.012, tall - 0.012,
                                                                                    face), "painted_panel", "door"),
                             0.003)]
    for y in (tall * 0.2, tall * 0.8):
        parts.append(shapes.cylinder((wide / 2 - 0.004, y - 0.03, front + 0.006), (wide / 2 - 0.004, y + 0.03,
                                                                                    front + 0.006), 0.006,
                                     "bare_steel", 12, "hinge"))
    door = front + 0.004
    pad_x, pad_y = -wide * 0.2, tall * 0.55
    parts.append(shapes.bevelled(shapes.box((pad_x - 0.04, pad_y - 0.06, door - 0.008), (pad_x + 0.04, pad_y + 0.03,
                                                                                         door), "anodized_black",
                                            "keypad"), 0.002))
    parts.append(shapes.content_plate((pad_x - 0.032, pad_y - 0.052, door - 0.01), (pad_x + 0.032, pad_y + 0.015,
                                                                                     door - 0.008), "keypad_print",
                                      "keys"))
    parts += wall_screen_part(pad_x, pad_y + 0.075, 0.1, 0.05, door, "screen_amber", rim=0.008)
    parts.append(shapes.cylinder((pad_x, tall * 0.9, door), (pad_x, tall * 0.9, door - 0.006), 0.007, "led_green", 12,
                                 "led"))
    parts.append(label(wide * 0.18, tall * 0.88, 0.11, 0.03, door, "label_control_box"))
    parts.append(label(wide * 0.2, tall * 0.55, 0.07, 0.05, door, "label_check_seal", turn=3.0, thick=0.004,
                       name="sticker"))
    parts.append(label(0.0, tall * 0.2, 0.14, 0.11, door, "sheet_main_box", thick=0.004, name="sheet"))
    return parts


def conduit_box(size, laid):
    """A conduit box, as its close-up shows it: a cast box with a lid on a raised lip, a screw at each corner of the
    lid, cable glands out of its side and its bottom."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    body = 0.16
    left, bottom = -wide / 2 + 0.04, tall - body
    right, top = left + body, tall
    parts = [shapes.bevelled(shapes.box((left, bottom, front + 0.02), (right, top, back), "cast_steel", "body"),
                             0.006),
             shapes.bevelled(shapes.box((left + 0.008, bottom + 0.008, front + 0.008), (right - 0.008, top - 0.008,
                                                                                        front + 0.02), "cast_steel",
                                        "lid"), 0.004),
             shapes.bevelled(rounded_ring((left + 0.004, bottom + 0.004), (right - 0.004, top - 0.004), 0.01, 0.01,
                                          front + 0.015, front + 0.02, "cast_steel", "lip"), 0.0015)]
    parts += [screw(x, y, front + 0.008) for x in (left + 0.02, right - 0.02) for y in (bottom + 0.02, top - 0.02)]
    middle_z = (front + 0.02 + back) / 2
    for x in (left + 0.04, right - 0.04):
        parts.append(shapes.cylinder((x, bottom, middle_z), (x, bottom - 0.02, middle_z), 0.017, "bare_steel", 6,
                                     "gland"))
        parts.append(shapes.ring((x, bottom - 0.02, middle_z), (x, bottom - 0.035, middle_z), 0.014, 0.008,
                                 "bare_steel", 16, "gland"))
    for y in (bottom + 0.045, top - 0.045):
        parts.append(shapes.cylinder((right, y, middle_z), (right + 0.02, y, middle_z), 0.017, "bare_steel", 6,
                                     "gland"))
        parts.append(shapes.ring((right + 0.02, y, middle_z), (right + 0.035, y, middle_z), 0.014, 0.008,
                                 "bare_steel", 16, "gland"))
    return parts


def wall_capsule(top, radius, length, material, name, segments=32):
    """One sealed glass capsule standing up from a kit-frame point `top` (its upper dome's middle): a ball whose
    lower half is drawn down by `length`, so its sides run straight."""
    built = bmesh.new()
    bmesh.ops.create_uvsphere(built, u_segments=segments, v_segments=segments // 2, radius=radius)
    for vertex in built.verts:
        if vertex.co.z < -1e-6:
            vertex.co.z -= length
    bmesh.ops.translate(built, verts=built.verts, vec=shapes.to_blender(top))
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def wall_cage_lamp(size, laid):
    """A caged bulkhead lamp, as its close-up shows it: a back plate screwed to the wall, a collar at its foot, a
    glass dome standing out of the wall with a cage of bars and hoops over it."""
    wide, tall, deep = size
    back = deep / 2
    plate = 0.012
    radius, cage = 0.044, 0.051
    z = back - plate - cage - 0.002
    parts = [shapes.bevelled(shapes.prism(rounded_outline((-wide / 2, 0.0), (wide / 2, tall - 0.005), 0.04),
                                          back - plate, back, "dark_panel", "back_plate"), 0.003)]
    parts.append(shapes.bevelled(shapes.cylinder((0.0, 0.015, z), (0.0, 0.06, z), cage + 0.006, "dark_panel", 32,
                                                 "collar"), 0.003))
    top = tall - 0.015 - radius
    parts.append(wall_capsule((0.0, top, z), radius, top - 0.06, "lamp_lens", "glass"))
    for angle in (-75, -35, 0, 35, 75):
        x = cage * math.sin(math.radians(angle))
        bar_z = z - cage * math.cos(math.radians(angle))
        parts.append(shapes.cylinder((x, 0.06, bar_z), (x, top, bar_z), 0.0035, "dark_panel", 8, "bar"))
    for y in (0.1, 0.15):
        parts.append(shapes.ring((0.0, y, z), (0.0, y + 0.007, z), cage + 0.003, cage - 0.003, "dark_panel", 32,
                                 "hoop"))
    parts.append(shapes.ring((-0.0035, top, z), (0.0035, top, z), cage + 0.003, cage - 0.003, "dark_panel", 32, "hoop"))
    parts += [screw(x, y, back - plate) for x in (-wide / 2 + 0.03, wide / 2 - 0.03) for y in (0.025, tall - 0.04)]
    return parts


def door_strip_lamp(size, laid):
    """A strip lamp over a door, as its close-up shows it: a long steel housing, its lens set in a pocket along its
    front, a mounting tab with screws at each end, a small circuit label."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    tab = 0.04
    housing = shapes.box((-wide / 2 + tab, 0.0, front), (wide / 2 - tab, tall, back), "painted_panel", "housing")
    lens_low, lens_high = (-wide / 2 + tab + 0.03, 0.01), (wide / 2 - tab - 0.03, 0.045)
    wall_pocket(housing, lens_low, lens_high, front - 0.02, front + 0.008)
    parts = [shapes.bevelled(housing, 0.003),
             shapes.content_plate((*lens_low, front + 0.004), (*lens_high, front + 0.008), "lamp_strip", "lens")]
    for side in (-1, 1):
        x0, x1 = sorted((side * (wide / 2 - tab), side * wide / 2))
        parts.append(shapes.bevelled(shapes.box((x0, 0.008, back - 0.006), (x1, tall - 0.008, back), "painted_panel",
                                                "tab"), 0.0015))
        parts.append(screw((x0 + x1) / 2, tall / 2, back - 0.006))
    parts.append(label(wide / 2 - tab - 0.12, 0.062, 0.14, 0.024, front, "label_circuit"))
    return parts


def grab_bar(size, laid):
    """A grab bar beside a door, as its close-up shows it: a round bar standing off the wall on two bent legs, each on
    a square foot plate screwed to the wall."""
    wide, tall, deep = size
    back = deep / 2
    radius = 0.016
    bar_z = -deep / 2 + radius
    ends = (0.04, tall - 0.04)
    parts = [shapes.cylinder((0.0, ends[0], bar_z), (0.0, ends[1], bar_z), radius, "brushed_steel_fine", 20, "bar")]
    for y in ends:
        parts.append(wall_sphere((0.0, y, bar_z), radius, "brushed_steel_fine", "bend", 16))
        parts.append(shapes.cylinder((0.0, y, bar_z), (0.0, y, back - 0.008), radius, "brushed_steel_fine", 20,
                                     "stand_off"))
        across, up = wide / 2 - 0.005, 0.04
        parts.append(shapes.bevelled(shapes.box((-across, y - up, back - 0.008), (across, y + up, back),
                                                "brushed_steel_fine", "foot"), 0.002))
        parts += [screw(side * (across - 0.018), y, back - 0.008) for side in (-1, 1)]
    return parts


# ---- Method B, round six: the hub's floor, roof and pipe fittings, built in code with library surfaces, each with
# every part its clean close-up shows (data/library/fittings.json). Floor fittings lie in the deck with their kit
# front (-z) up; roof gear hangs under the roof with its height (y) reaching down into the room, so the room sees its
# +y side (a duct, a tray) or its underside (the apex hub, the flood lamps): checked_from_the_room turns such a piece so
# the side the room sees faces the check's front before it counts.

# Degrees about the kit's x axis that bring the side the room sees round to the kit front (-z), by kind: a tray or
# duct is seen on its +y side, the apex hub and a flood lamp from below (their -y side).
FLOOR_SEEN_TURN = {"ceiling_cable_tray": -90.0, "ceiling_duct": -90.0, "roof_apex_hub": 90.0,
                   "roof_light_fixture": 90.0, "light_ring": 90.0}
FLOOR_PIPE_RADIUS = 0.038  # pipe_straight's: min(tall, deep) * 0.38 at 0.1
# How far a wall pipe run's axis stands off the wall (hub_kit.PIPE_AXIS): a bracket's base plate and a valve's foot plate
# are on the wall, their clamp and body on the run (step 0 of the modules round, 2026-10-07: at 20 cm the clamp's arm
# hid behind the pipe and the bracket read as not reaching it).
PIPE_AXIS = 0.08


def floor_bent_tube(centre, across, up, radius, thick, start, end, material, name, steps=16, sides=16):
    """A round tube bent along an arc: `radius` round `centre` in the plane of the kit vectors `across` and `up`, from
    angle `start` to `end` (degrees, 0 along `across`), `thick` its own radius; capped at both ends."""
    centre, across, up = (Vector(value) for value in (centre, across, up))
    side = across.cross(up).normalized()
    built = bmesh.new()
    rings = []
    for step in range(steps + 1):
        angle = math.radians(start + (end - start) * step / steps)
        out = across * math.cos(angle) + up * math.sin(angle)
        middle = centre + out * radius
        rings.append([built.verts.new(shapes.to_blender(middle + (out * math.cos(turn) + side * math.sin(turn)) * thick))
                      for turn in (2 * math.pi * at / sides for at in range(sides))])
    for first, second in zip(rings, rings[1:]):
        for at in range(sides):
            built.faces.new([first[at], first[(at + 1) % sides], second[(at + 1) % sides], second[at]])
    built.faces.new(rings[0])
    built.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def floor_frame(low, high, z_from, z_to, rim, material, name):
    """A square frame of four bars `rim` wide round the rectangle between two (x, y) corners, between two depths."""
    (left, bottom), (right, top) = low, high
    return [shapes.bevelled(shapes.box(corner_low + (z_from,), corner_high + (z_to,), material, name), 0.002)
            for corner_low, corner_high in (((left, bottom), (left + rim, top)), ((right - rim, bottom), (right, top)),
                                            ((left + rim, bottom), (right - rim, bottom + rim)),
                                            ((left + rim, top - rim), (right - rim, top)))]


def floor_label_under(x, z, wide, long, under, variant, name="label"):
    """A printed plate on a piece's underside at height `under` (its +y face, the side a roof piece shows the room),
    reading upright to someone below it with its top toward the piece's +z."""
    plate = label(x, 0.0, wide, long, 0.0, variant, name=name)
    return floor_moved(tilted(plate, (0.0, 0.0), 90.0), (0.0, under, z))


def floor_moved(part, offset):
    part.data.transform(Matrix.Translation(shapes.to_blender(offset)))
    return part


def floor_grating(size, laid):
    """A floor grating lying in the deck, its front up, as its close-up shows it: a square bar grid (bearing bars one
    way, cross bars the other, real gaps between them over the duct below) in a bolted frame."""
    wide, long, deep = size
    top, bottom = -deep / 2, deep / 2
    rim = 0.03
    parts = floor_frame((-wide / 2, 0.0), (wide / 2, long), top, bottom, rim, "galvanized_steel", "frame")
    pitch = 0.08
    inner_wide, inner_long = wide - 2 * rim, long - 2 * rim
    bars = max(1, round(inner_wide / pitch))
    for at in range(1, bars):
        x = -wide / 2 + rim + inner_wide * at / bars
        parts.append(shapes.box((x - 0.004, rim, top), (x + 0.004, long - rim, top + 0.035), "galvanized_steel",
                                "bearing_bar"))
    crosses = max(1, round(inner_long / pitch))
    for at in range(1, crosses):
        y = rim + inner_long * at / crosses
        parts.append(shapes.box((-wide / 2 + rim, y - 0.003, top + 0.001), (wide / 2 - rim, y + 0.003, top + 0.02),
                                "galvanized_steel", "cross_bar"))
    corners = [(x, y) for x in (-wide / 2 + rim / 2, wide / 2 - rim / 2) for y in (rim / 2, long - rim / 2)]
    parts += [screw(x, y, top) for x, y in corners]
    return parts


def floor_access_hatch(size, laid):
    """A square access hatch lying in the deck, its front up, as its close-up shows it: a frame bolted all round, a
    lid inset in it with a groove round its border, and a ring pull lying flat in a round recess at its middle."""
    wide, long, deep = size
    top, bottom = -deep / 2, deep / 2
    rim = 0.05
    parts = floor_frame((-wide / 2, 0.0), (wide / 2, long), top, bottom, rim, "galvanized_steel", "frame")
    lid = shapes.box((-wide / 2 + rim + 0.004, rim + 0.004, top), (wide / 2 - rim - 0.004, long - rim - 0.004,
                                                                    bottom - 0.004), "deck", "lid")
    middle = long / 2
    shapes.cut(lid, shapes.cylinder((0.0, middle, top - 0.01), (0.0, middle, top + 0.005), 0.065, "deck", 40, "cutter"))
    parts.append(shapes.bevelled(lid, 0.002))
    inset = rim + 0.045
    parts.append(shapes.bevelled(rounded_ring((-wide / 2 + inset, inset), (wide / 2 - inset, long - inset), 0.01, 0.012,
                                              top - 0.0035, top, "deck", "border"), 0.001))
    parts.append(shapes.cylinder((0.0, middle, top + 0.0015), (0.0, middle, top + 0.005), 0.062, "dark_panel", 40,
                                 "recess"))
    parts.append(shapes.bevelled(shapes.ring((0.0, middle - 0.01, top + 0.0015), (0.0, middle - 0.01, top - 0.0025),
                                             0.045, 0.034, "bare_steel", 32, "ring_pull"), 0.001))
    parts.append(shapes.cylinder((-0.03, middle + 0.036, top - 0.0015), (0.03, middle + 0.036, top - 0.0015), 0.003,
                                 "bare_steel", 12, "pin"))
    side = np.linspace(rim / 2 + 0.03, long - rim / 2 - 0.03, 5)
    points = [(x, y) for x in (-wide / 2 + rim / 2, wide / 2 - rim / 2) for y in side]
    points += [(x, y) for x in np.linspace(-wide / 2 + rim / 2 + 0.03, wide / 2 - rim / 2 - 0.03, 5)[1:-1]
               for y in (rim / 2, long - rim / 2)]
    parts += [screw(x, y, top) for x, y in points]
    return parts


def tread_mat(size, laid):
    """A tread plate set in the deck, its front up, as its close-up shows it: one chequer steel plate (the lugs are
    the library surface's relief) with bevelled edges."""
    wide, long, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, long, deep / 2), "chequer_plate_steel",
                                       "plate"), 0.004)]


def ceiling_cable_tray(size, laid):
    """A cable tray under the roof, its length along x and its pan hanging down into the room (y), as its close-up
    shows it: a pan with rows of real slots in its bottom and sides, its sides' top edges turned in, cables lying in it
    seen through the slots, and hanger straps up to the roof."""
    wide, tall, deep = size
    sheet = 0.004
    pan = shapes.box((-wide / 2, tall - sheet, -deep / 2), (wide / 2, tall, deep / 2), "galvanized_steel", "pan")
    walls = [shapes.box((-wide / 2, 0.014, z), (wide / 2, tall, z + sheet), "galvanized_steel", "side")
             for z in (-deep / 2, deep / 2 - sheet)]
    slots = max(2, round(wide / 0.16))
    for at in range(slots):
        x = -wide / 2 + (wide / slots) * (at + 0.5)
        for z in (-deep / 4, deep / 4):
            shapes.cut(pan, shapes.box((x - 0.05, tall - 0.02, z - 0.03), (x + 0.05, tall + 0.02, z + 0.03),
                                       "galvanized_steel", "cutter"))
        for wall in walls:
            shapes.cut(wall, shapes.box((x - 0.04, 0.04, -deep), (x + 0.04, tall - 0.025, deep), "galvanized_steel",
                                        "cutter"))
    parts = [shapes.bevelled(pan, 0.0015)] + [shapes.bevelled(wall, 0.0015) for wall in walls]
    for z, inward in ((-deep / 2, 1), (deep / 2, -1)):
        lip = (z, z + inward * 0.02)
        parts.append(shapes.box((-wide / 2, 0.014, min(lip)), (wide / 2, 0.014 + sheet, max(lip)), "galvanized_steel",
                                "lip"))
    for at, (z, material) in enumerate(((-0.08, "cable_black"), (-0.03, "cable_grey"), (0.025, "cable_black"),
                                         (0.08, "cable_grey"))):
        radius = 0.018 if at % 2 else 0.022
        parts.append(shapes.cylinder((-wide / 2 + 0.002, tall - sheet - radius, z), (wide / 2 - 0.002,
                                                                                    tall - sheet - radius, z),
                                     radius, material, 16, "cable"))
    for x in (-wide / 2 + 0.25, 0.0, wide / 2 - 0.25):
        parts.append(shapes.box((x - 0.015, 0.0, -deep / 2), (x + 0.015, 0.014, deep / 2), "dark_panel", "hanger"))
    return parts


def ceiling_duct(size, laid):
    """An air duct under the roof, its length along x and its height (y) hanging into the room, as its close-up shows
    it: a square sheet duct, open at both ends, a bolted flange round each end, hanger straps round it up to the roof,
    and its name stencilled on the side the room sees."""
    wide, tall, deep = size
    sheet = 0.008
    flange = 0.022
    body = (0.012, tall - 0.012)  # the duct's top and underside (y), inside its flanges
    near, far = -deep / 2 + 0.012, deep / 2 - 0.012
    parts = [shapes.box((-wide / 2, body[1] - sheet, near), (wide / 2, body[1], far), "painted_panel", "wall"),
             shapes.box((-wide / 2, body[0], near), (wide / 2, body[0] + sheet, far), "painted_panel", "wall"),
             shapes.box((-wide / 2, body[0], near), (wide / 2, body[1], near + sheet), "painted_panel", "wall"),
             shapes.box((-wide / 2, body[0], far - sheet), (wide / 2, body[1], far), "painted_panel", "wall")]
    parts = [shapes.bevelled(part, 0.002) for part in parts]
    for x in (-wide / 2, wide / 2 - flange):
        outline = (x, x + flange)
        ring = shapes.box((outline[0], 0.0, -deep / 2), (outline[1], tall - 0.006, deep / 2), "painted_panel", "flange")
        shapes.cut(ring, shapes.box((x - 0.05, body[0], near), (x + flange + 0.05, body[1], far), "painted_panel",
                                    "cutter"))
        parts.append(shapes.bevelled(ring, 0.002))
        middle = x + flange / 2
        for z in np.linspace(-deep / 2 + 0.006, deep / 2 - 0.006, 4):
            parts.append(shapes.cylinder((middle, tall - 0.006, z), (middle, tall, z), 0.005, "bare_steel", 10, "bolt"))
    for x in (-wide / 4, wide / 4):
        parts.append(shapes.box((x - 0.02, body[1], near - 0.004), (x + 0.02, body[1] + 0.005, far + 0.004),
                                "dark_panel", "strap"))
        for z in (near - 0.004, far):
            parts.append(shapes.box((x - 0.02, 0.0, z), (x + 0.02, body[1] + 0.005, z + 0.004), "dark_panel", "strap"))
    parts.append(floor_label_under(0.0, 0.0, 0.42, 0.12, body[1], "label_air_return"))
    return parts


def floor_dome_profile(rim, height, rim_high, steps):
    """The (radius, height) points of a dome hanging below a rim at `rim_high`, from its rim to its middle."""
    return [(rim * math.cos(math.radians(90 * at / steps)), rim_high - height * math.sin(math.radians(90 * at / steps)))
            for at in range(steps + 1)]


def floor_dome(rim, height, rim_high, material, name, sides=40, steps=12):
    """A dome hanging below a round rim, closed across its rim: its shell from the profile turned round the kit y."""
    built = bmesh.new()
    rows = []
    for radius, high in floor_dome_profile(rim, height, rim_high, steps)[:-1]:
        rows.append([built.verts.new(shapes.to_blender((radius * math.cos(2 * math.pi * at / sides), high,
                                                         radius * math.sin(2 * math.pi * at / sides))))
                     for at in range(sides)])
    tip = built.verts.new(shapes.to_blender((0.0, rim_high - height, 0.0)))
    for first, second in zip(rows, rows[1:]):
        for at in range(sides):
            built.faces.new([first[at], first[(at + 1) % sides], second[(at + 1) % sides], second[at]])
    for at in range(sides):
        built.faces.new([rows[-1][at], rows[-1][(at + 1) % sides], tip])
    built.faces.new(rows[0])
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def roof_apex_hub(size, laid):
    """The hub where the roof's ribs meet, hanging under the apex, as its close-up shows it: a dome bulging down into
    the room, ribs running over it from its rim to its middle, a thick ring round its rim, a boss at its middle and a
    flange plate up against the lattice."""
    wide, tall, deep = size
    rim, height, rim_high = min(wide, deep) / 2 - 0.035, tall - 0.08, tall - 0.035
    parts = [floor_dome(rim, height, rim_high, "painted_panel", "dome")]
    outer, inner = floor_dome_profile(rim + 0.016, height + 0.016, rim_high, 16), floor_dome_profile(rim - 0.004,
                                                                                                        height - 0.004,
                                                                                                        rim_high, 16)
    outline = [(radius, high) for radius, high in outer[:14]] + [(radius, high) for radius, high in reversed(inner[:14])]
    for at in range(12):
        rib = shapes.prism(outline, -0.007, 0.007, "dark_panel", "rib")
        rib.data.transform(Matrix.Rotation(2 * math.pi * at / 12, 4, "Z"))
        parts.append(rib)
    parts.append(shapes.bevelled(shapes.ring((0.0, rim_high - 0.012, 0.0), (0.0, rim_high + 0.012, 0.0), rim + 0.03,
                                             rim - 0.02, "dark_panel", 48, "rim"), 0.004))
    parts.append(shapes.bevelled(shapes.ring((0.0, rim_high + 0.012, 0.0), (0.0, tall, 0.0), min(wide, deep) / 2,
                                             0.06, "dark_panel", 48, "flange"), 0.003))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, 0.0, 0.0), (0.0, rim_high - height + 0.01, 0.0), 0.045,
                                                 "dark_panel", 24, "boss"), 0.004))
    return parts


def roof_light_fixture(size, laid):
    """A flood lamp hung under the lattice, its lens facing down into the room, as its close-up shows it: a mount
    plate, a yoke down both sides to pivot bolts on a round housing, the lens across its mouth, and a wire cage of
    rings and spokes over the lens."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2 - 0.03
    mouth, back = 0.093, 0.22  # the cage's tip reaches the box's foot (y 0)
    parts = [shapes.bevelled(shapes.cylinder((0.0, mouth, 0.0), (0.0, back, 0.0), radius, "bare_steel", 40, "housing"),
                             0.006),
             shapes.bevelled(shapes.cylinder((0.0, back, 0.0), (0.0, back + 0.03, 0.0), radius * 0.6, "bare_steel", 32,
                                             "housing"), 0.004),
             shapes.cylinder((0.0, mouth - 0.006, 0.0), (0.0, mouth, 0.0), radius - 0.015, "lamp_lens", 40, "lens"),
             shapes.bevelled(shapes.ring((0.0, mouth - 0.008, 0.0), (0.0, mouth + 0.006, 0.0), radius + 0.004,
                                         radius - 0.014, "bare_steel", 40, "bezel"), 0.002),
             shapes.bevelled(shapes.box((-0.06, tall - 0.012, -deep / 2), (0.06, tall, deep / 2), "dark_panel", "mount"),
                             0.002)]
    arm = wide / 2 - 0.015
    pivot = (mouth + back) / 2
    for side in (-1, 1):
        parts.append(shapes.bevelled(shapes.box((side * arm - 0.012, pivot, -0.02), (side * arm + 0.012, tall - 0.012,
                                                                                   0.02), "dark_panel", "yoke"), 0.002))
        parts.append(shapes.cylinder((side * (radius - 0.005), pivot, 0.0), (side * (arm + 0.014), pivot, 0.0), 0.014,
                                     "bare_steel", 16, "pivot"))
    parts.append(shapes.bevelled(shapes.box((-arm - 0.012, tall - 0.035, -0.02), (arm + 0.012, tall - 0.012, 0.02),
                                            "dark_panel", "yoke"), 0.002))
    rings = ((mouth - 0.025, radius), (mouth - 0.06, radius * 0.75), (mouth - 0.085, radius * 0.4))
    for high, across in rings:
        parts.append(shapes.ring((0.0, high - 0.003, 0.0), (0.0, high + 0.003, 0.0), across, across - 0.006,
                                 "dark_panel", 40, "cage"))
    points = [(mouth - 0.008, radius)] + list(rings) + [(mouth - 0.09, 0.0)]
    for at in range(8):
        angle = 2 * math.pi * at / 8
        for (high_a, across_a), (high_b, across_b) in zip(points, points[1:]):
            parts.append(shapes.cylinder((across_a * math.cos(angle), high_a, across_a * math.sin(angle)),
                                         (across_b * math.cos(angle), high_b, across_b * math.sin(angle)), 0.003,
                                         "dark_panel", 8, "cage"))
    return parts


def pipe_bracket(size, laid):
    """A pipe bracket on the wall, as its close-up shows it: a base plate bolted to the wall, a stand-off arm, and a
    two-part clamp round the pipe in front of it, bolted through its ears."""
    wide, tall, deep = size
    back = deep / 2
    middle_y = tall / 2
    axis_z = back - PIPE_AXIS  # the pipe run's axis, PIPE_AXIS off the wall the base plate is bolted to
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, back - 0.012), (wide / 2, tall, back), "dark_panel", "base"),
                             0.003)]
    parts += bolts_along([(x, y) for x in (-wide / 2 + 0.018, wide / 2 - 0.018) for y in (0.018, tall - 0.018)],
                         back - 0.012)
    clear = FLOOR_PIPE_RADIUS + 0.0085  # just outside the clamp: the arm and the ears stop here, no sliver inside it
    arm = shapes.box((-0.02, middle_y - 0.03, axis_z), (0.02, middle_y + 0.03, back - 0.012), "dark_panel", "arm")
    shapes.cut(arm, shapes.cylinder((-0.05, middle_y, axis_z), (0.05, middle_y, axis_z), clear, "dark_panel", 32,
                                    "cutter"))
    parts.append(arm)
    clamp = shapes.ring((-0.02, middle_y, axis_z), (0.02, middle_y, axis_z), FLOOR_PIPE_RADIUS + 0.008,
                        FLOOR_PIPE_RADIUS + 0.001, "bare_steel", 32, "clamp")
    parts.append(shapes.bevelled(clamp, 0.002))
    for side in (-1, 1):
        y = middle_y + side * (FLOOR_PIPE_RADIUS + 0.014)
        ear = shapes.box((-0.02, y - 0.008, axis_z - 0.004), (0.02, y + 0.008, axis_z + 0.004), "bare_steel", "ear")
        shapes.cut(ear, shapes.cylinder((-0.05, middle_y, axis_z), (0.05, middle_y, axis_z), clear, "bare_steel", 32,
                                        "cutter"))
        parts.append(ear)
        parts.append(shapes.cylinder((0.0, y + side * 0.0015, axis_z - 0.012), (0.0, y + side * 0.0015, axis_z + 0.012),
                                     0.003, "bare_steel", 10, "bolt"))
    return parts


def floor_flange(centre, axis, radius, material="pipe_steel", bolts=6):
    """A pipe flange: a disc `radius` round `centre` along the unit kit vector `axis` (its thickness), bolts round it."""
    centre, axis = Vector(centre), Vector(axis)
    parts = [shapes.bevelled(shapes.cylinder(centre - axis * 0.006, centre + axis * 0.006, radius, material, 32,
                                             "flange"), 0.0015)]
    across = axis.orthogonal().normalized()
    other = axis.cross(across)
    for at in range(bolts):
        angle = 2 * math.pi * at / bolts
        spot = centre + (across * math.cos(angle) + other * math.sin(angle)) * (radius - 0.0065)
        parts.append(shapes.cylinder(spot - axis * 0.01, spot + axis * 0.01, 0.004, "bare_steel", 8, "bolt"))
    return parts


def pipe_elbow(size, laid):
    """A pipe elbow on the wall, as its close-up shows it: a bend through a right angle in the wall's plane, its
    legs ending in bolted flanges, one opening down and one to the side."""
    wide, tall, deep = size
    flange = min(0.05, deep / 2)
    bend = min(wide, tall) - flange - 0.0
    centre = (-wide / 2, 0.0, 0.0)
    parts = [floor_bent_tube(centre, (1, 0, 0), (0, 1, 0), bend, FLOOR_PIPE_RADIUS, 0.0, 90.0, "pipe_steel", "bend",
                             steps=20)]
    parts += floor_flange((-wide / 2 + bend, 0.006, 0.0), (0, 1, 0), flange)
    parts += floor_flange((-wide / 2 + 0.006, bend, 0.0), (1, 0, 0), flange)
    return parts


def pipe_valve(size, laid):
    """A gate valve on a pipe run, as its close-up shows it, its handwheel facing the room: a body round the pipe on
    the run's axis (PIPE_AXIS off the valve's back, where the straight pipes run), flanged stubs either side, a bonnet
    standing out of the body toward the room, the stem through a yoke, a red handwheel with spokes on its front, and
    a foot plate on the wall behind the body."""
    wide, tall, deep = size
    axis_y = tall / 2
    axis_z = deep / 2 - PIPE_AXIS  # on the run's axis, its foot plate on the wall
    stub = FLOOR_PIPE_RADIUS
    parts = [shapes.cylinder((-wide / 2, axis_y, axis_z), (wide / 2, axis_y, axis_z), stub, "pipe_steel", 24, "stub")]
    for x in (-0.065, 0.065):
        parts += floor_flange((x, axis_y, axis_z), (1, 0, 0), 0.05)
    body = 0.046
    parts.append(shapes.bevelled(shapes.cylinder((-0.055, axis_y, axis_z), (0.055, axis_y, axis_z), body,
                                                 "cast_steel", 24, "body"), 0.004))
    front = -deep / 2
    parts.append(shapes.bevelled(shapes.box((-0.035, axis_y - 0.032, front + 0.075), (0.035, axis_y + 0.032, axis_z),
                                            "cast_steel", "bonnet"), 0.004))
    parts.append(shapes.bevelled(shapes.box((-0.045, axis_y - 0.04, front + 0.063), (0.045, axis_y + 0.04,
                                                                                    front + 0.075), "cast_steel",
                                            "bonnet"), 0.002))
    for x in (-0.03, 0.03):
        parts.append(shapes.box((x - 0.006, axis_y - 0.006, front + 0.035), (x + 0.006, axis_y + 0.006, front + 0.063),
                                "cast_steel", "yoke"))
    parts.append(shapes.box((-0.036, axis_y - 0.008, front + 0.027), (0.036, axis_y + 0.008, front + 0.035),
                            "cast_steel", "yoke"))
    wheel_z = front + 0.008
    parts.append(shapes.cylinder((0.0, axis_y, front + 0.004), (0.0, axis_y, front + 0.063), 0.007, "bare_steel", 12,
                                 "stem"))
    wheel = 0.075
    parts.append(shapes.bevelled(shapes.ring((0.0, axis_y, front), (0.0, axis_y, front + 0.016), wheel, wheel - 0.013,
                                             "anodized_red", 40, "handwheel"), 0.003))
    for at in range(5):
        angle = 2 * math.pi * at / 5
        parts.append(shapes.cylinder((0.0, axis_y, wheel_z), ((wheel - 0.008) * math.cos(angle),
                                                             axis_y + (wheel - 0.008) * math.sin(angle), wheel_z),
                                     0.005, "anodized_red", 8, "handwheel"))
    parts.append(shapes.cylinder((0.0, axis_y, front), (0.0, axis_y, front + 0.016), 0.016, "anodized_red", 16,
                                 "handwheel"))
    back = deep / 2
    parts.append(shapes.bevelled(shapes.box((-0.04, 0.0, back - 0.0035), (0.04, tall, back), "dark_panel", "foot"),
                                 0.001))
    # The saddle from the foot plate to the body: the body stands PIPE_AXIS off the wall, clear of it.
    parts.append(shapes.bevelled(shapes.box((-0.03, axis_y - 0.025, axis_z), (0.03, axis_y + 0.025, back - 0.0035),
                                            "dark_panel", "foot"), 0.002))
    parts += bolts_along([(0.0, 0.025), (0.0, tall - 0.025)], back - 0.0035)
    return parts


def pit_junction_box(size, laid):
    """A junction box on the pit's wall, as its close-up shows it: a steel box with a hood over its top, a lid on two
    hinges at its left with a latch at its right, its name on the lid, and two cables leaving through glands in its
    floor and bending back into the wall."""
    wide, tall, deep = size
    back, front = deep / 2, -deep / 2
    bottom = 0.07
    parts = [shapes.bevelled(shapes.box((-wide / 2 + 0.01, bottom, front + 0.012), (wide / 2 - 0.01, tall - 0.025,
                                                                                    back), "painted_panel", "body"),
                             0.004),
             shapes.bevelled(shapes.box((-wide / 2 + 0.016, bottom + 0.006, front + 0.002),
                                        (wide / 2 - 0.016, tall - 0.031, front + 0.012), "painted_panel", "lid"), 0.003),
             shapes.bevelled(shapes.box((-wide / 2, tall - 0.025, front), (wide / 2, tall, back), "painted_panel",
                                        "hood"), 0.003)]
    for y in (bottom + 0.05, tall - 0.08):
        parts.append(shapes.cylinder((wide / 2 - 0.016, y - 0.03, front + 0.004), (wide / 2 - 0.016, y + 0.03,
                                                                                  front + 0.004), 0.007, "bare_steel",
                                     12, "hinge"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + 0.02, (bottom + tall) / 2 - 0.03, front - 0.0015),
                                            (-wide / 2 + 0.034, (bottom + tall) / 2 + 0.03, front + 0.002),
                                            "bare_steel", "latch"), 0.001))
    parts.append(label(0.0, (bottom + tall) / 2 + 0.03, wide - 0.1, 0.06, front + 0.002, "label_junction"))
    for x in (-0.06, 0.06):
        parts.append(shapes.cylinder((x, bottom - 0.018, 0.0), (x, bottom + 0.002, 0.0), 0.017, "rubber", 16, "gland"))
        bend = min(0.04, back - 0.0)
        parts.append(shapes.cylinder((x, bend + 0.011, 0.0), (x, bottom - 0.016, 0.0), 0.011, "cable_red", 12, "cable"))
        parts.append(floor_bent_tube((x, bend + 0.011, bend), (0, 0, -1), (0, 1, 0), bend, 0.011, 0.0, -90.0, "cable_red",
                                     "cable", steps=10, sides=12))
        parts.append(shapes.cylinder((x, 0.0 + 0.011, bend - 0.001), (x, 0.0 + 0.011, back), 0.011, "cable_red", 12,
                                     "cable"))
    return parts


# ---- Round six (2026-10-07): the hub's furniture holders and their plain children, built in code with library
# surfaces as method B's parts check allows. A holder leaves clear, flat spots for its children (radios, a phone, a
# lamp, monitors, keyboards, a glovebox, a microscope, tools) and never carries them: each child is a model of its own,
# placed on purpose on its holder. Helpers are prefixed `furn_`.

FURN_DESK_TOP = 0.76  # the comms desk's and the console's working height (the Workstation's screens stand on it)
FURN_BENCH_TOP = 0.85  # the lab bench's
# The console's screens (children): the Workstation's live glass centres in the console's kit frame and their turns
# about the up axis, and the two outer screens of its own.
FURN_LIVE_SCREENS = ((0.0, 0.187, 0.0), (0.492, 0.138, 12.0), (-0.511, 0.174, -12.0))
FURN_OUTER_SCREENS = ((1.0, 0.0, 24.0), (-1.0, 0.0, -24.0))
# A monitor's opening (the live glass's size) and how high its middle stands over the monitor's foot.
FURN_SCREEN_OPENING = (0.44, 0.26)
FURN_SCREEN_MIDDLE = 0.225
FURN_SCREEN_FACE = -0.02


def furn_prism(outline, axis, depth_from, depth_to, material, name):
    """A flat shape solid between two depths along a kit axis: `outline` in the plane across it, as (x, y) for 'z',
    (x, z) for 'y' and (z, y) for 'x' (a glovebox's side profile, a bin's rounded plan)."""
    def point(first, second, depth):
        if axis == "z":
            return (first, second, depth)
        if axis == "y":
            return (first, depth, second)
        return (depth, second, first)
    built = bmesh.new()
    near = [built.verts.new(shapes.to_blender(point(a, b, depth_from))) for a, b in outline]
    far = [built.verts.new(shapes.to_blender(point(a, b, depth_to))) for a, b in outline]
    built.faces.new(near)
    built.faces.new(list(reversed(far)))
    count = len(outline)
    for at in range(count):
        following = (at + 1) % count
        built.faces.new([near[at], far[at], far[following], near[following]])
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def furn_spun(parts, pivot, degrees):
    """Parts turned `degrees` about the kit frame's up through `pivot` (x, z); positive brings +x toward the front
    (-z)."""
    centre = shapes.to_blender((pivot[0], 0.0, pivot[1]))
    turn = Matrix.Translation(centre) @ Matrix.Rotation(math.radians(degrees), 4, "Z") @ Matrix.Translation(-centre)
    for part in parts:
        part.data.transform(turn)
    return parts


def furn_cut_box(part, low, high):
    """A box (kit-frame corners) taken out of a part: a pocket or a hole."""
    shapes.cut(part, shapes.box(low, high, "rubber", "cutter"))
    return part


def furn_louvres(plate, x, y, wide, tall, front, back, slats, material, name="louvre", back_thick=0.003):
    """Pressed louvres set into `plate` (front face at depth `front`, its back at `back`): a real hole through it, a
    dark back plate behind the hole and slanted hoods across it, standing a little proud of the face."""
    furn_cut_box(plate, (x - wide / 2, y - tall / 2, front - 0.05), (x + wide / 2, y + tall / 2, back))
    parts = [shapes.box((x - wide / 2, y - tall / 2, back - back_thick), (x + wide / 2, y + tall / 2, back),
                        "anodized_black", f"{name}_back")]
    pitch = tall / slats
    for at in range(slats):
        middle = y - tall / 2 + pitch * (at + 0.5)
        hood = shapes.box((x - wide / 2 + 0.004, middle - 0.0025, front - 0.006),
                          (x + wide / 2 - 0.004, middle + 0.0025, min(back - 0.004, front + pitch * 0.9)), material,
                          name)
        parts.append(tilted(shapes.bevelled(hood, 0.001), (middle, front), -40.0))
    return parts


def furn_pull(x, y, long, front, upright=True, name="handle"):
    """A bar pull on two standoffs, on a face at depth `front`: upright or lying along x."""
    stand = 0.028
    if upright:
        ends = [(x, y - long / 2), (x, y + long / 2)]
        bar = shapes.cylinder((x, y - long / 2 - 0.01, front - stand), (x, y + long / 2 + 0.01, front - stand), 0.008,
                              "bare_steel", 12, name)
    else:
        ends = [(x - long / 2, y), (x + long / 2, y)]
        bar = shapes.cylinder((x - long / 2 - 0.01, y, front - stand), (x + long / 2 + 0.01, y, front - stand), 0.008,
                              "bare_steel", 12, name)
    parts = [bar]
    for end_x, end_y in ends:
        parts.append(shapes.cylinder((end_x, end_y, front), (end_x, end_y, front - stand), 0.006, "bare_steel", 10,
                                     "standoff"))
    return parts


def furn_locker(size, doors, labels, sheet=None):
    """A steel locker of `doors` doors: a dark plinth, the carcass, door plates with pressed louvres top and bottom in
    real pockets, a pull and hinge pins each, a label per door between its top louvres and its pull (and a taped
    sheet under one); every face square, as a made locker is."""
    wide, tall, deep = size
    front = -deep / 2
    face = front + 0.014
    parts = [shapes.box((-wide / 2 + 0.02, 0.0, front + 0.03), (wide / 2 - 0.02, 0.08, deep / 2), "dark_panel",
                        "plinth"),
             shapes.bevelled(shapes.box((-wide / 2, 0.08, face), (wide / 2, tall, deep / 2), "painted_panel",
                                        "carcass"), EDGE)]
    gap, margin = 0.008, 0.015
    door_wide = (wide - 2 * margin - gap * (doors - 1)) / doors
    for door in range(doors):
        right = -wide / 2 + margin + door * (door_wide + gap)  # the door's -x edge (the viewer's right)
        left = right + door_wide
        middle = (left + right) / 2
        plate = shapes.box((right, 0.1, front), (left, tall - 0.02, face), "painted_panel", "door")
        vents = []
        for high in (tall - 0.24, 0.3):
            vents += furn_louvres(plate, middle, high, door_wide * 0.5, 0.14, front, face, 4, "painted_panel")
        parts += [shapes.bevelled(plate, 0.002)] + vents
        # Two doors meet in the middle, their pulls by the meeting edges; one door pulls on the viewer's left.
        inner_left = doors == 1 or door == 0
        pull_x = left - 0.055 if inner_left else right + 0.055
        hinge_x = right - 0.004 if inner_left else left + 0.004
        parts += furn_pull(pull_x, tall * 0.51, 0.16, front)
        for high in (0.35, tall - 0.35):
            parts.append(shapes.cylinder((hinge_x, high - 0.04, front + 0.004), (hinge_x, high + 0.04, front + 0.004),
                                         0.007, "bare_steel", 12, "hinge"))
        label_high = tall - 0.42
        parts.append(label(middle, label_high, min(0.2, door_wide * 0.6), 0.06, front, labels[door]))
        if sheet is not None and door == 0 and doors > 1:
            parts.append(label(middle, label_high - 0.24, 0.15, 0.2, front, sheet, turn=2.0, thick=0.003,
                               name="sheet"))
    return parts


def talllocker(size, laid):
    """The tall double locker, as its close-up shows it: plinth, carcass, two doors with pressed louvres top and
    bottom, a pull and hinge pins each, LOCKER A and LOCKER B labels and a taped sheet."""
    return furn_locker(size, 2, ("label_locker_b", "label_locker_a"), "sheet_spares")


def rack(size, laid):
    """A single steel locker, as its close-up shows it: plinth, carcass, one door with pressed louvres top and
    bottom, a pull, hinge pins and a stencilled number."""
    return furn_locker(size, 1, ("stencil_number",))


def comms(size, laid):
    """The comms desk, as its close-up shows it: a steel top with a lip, a door pedestal (viewer's left) and a drawer
    and door pedestal (viewer's right), a centre drawer, short legs, a modesty panel, a hook on its right side for the
    headset; its top left clear for the radios, the telephone and the lamp (children of their own)."""
    wide, tall, deep = size
    top = FURN_DESK_TOP
    front = -deep / 2
    body = front + 0.02  # the pedestals' and drawers' carcass front
    parts = [shapes.bevelled(shapes.box((-wide / 2, top - 0.035, front), (wide / 2, top, deep / 2), "painted_panel",
                                        "top"), EDGE),
             shapes.bevelled(shapes.box((-wide / 2, top - 0.06, front - 0.004), (wide / 2, top - 0.035, front + 0.02),
                                        "painted_panel", "lip"), 0.003)]
    pedestal = 0.4
    spans = ((wide / 2 - 0.02 - pedestal, wide / 2 - 0.02), (-wide / 2 + 0.02, -wide / 2 + 0.02 + pedestal))
    for right, left in spans:
        parts.append(shapes.bevelled(shapes.box((right, 0.08, body), (left, top - 0.06, deep / 2 - 0.02),
                                                "painted_panel", "pedestal"), EDGE))
        for x in (right + 0.04, left - 0.04):
            for z in (front + 0.06, deep / 2 - 0.06):
                parts.append(shapes.box((x - 0.022, 0.0, z - 0.022), (x + 0.022, 0.08, z + 0.022), "dark_panel",
                                        "leg"))
    # The viewer's left pedestal: one door.
    right, left = spans[0]
    parts.append(shapes.bevelled(shapes.box((right + 0.015, 0.1, front + 0.006), (left - 0.015, top - 0.08, body),
                                            "painted_panel", "door"), 0.002))
    parts += furn_pull(right + 0.055, 0.36, 0.12, front + 0.006)
    parts.append(label((right + left) / 2 + 0.03, 0.58, 0.2, 0.06, front + 0.006, "label_comms"))
    # The viewer's right pedestal: a drawer over a door.
    right, left = spans[1]
    parts.append(shapes.bevelled(shapes.box((right + 0.015, top - 0.2, front + 0.006), (left - 0.015, top - 0.08, body),
                                            "painted_panel", "drawer"), 0.002))
    parts += furn_pull((right + left) / 2, top - 0.14, 0.12, front + 0.006, upright=False, name="pull")
    parts.append(shapes.bevelled(shapes.box((right + 0.015, 0.1, front + 0.006), (left - 0.015, top - 0.215, body),
                                            "painted_panel", "door"), 0.002))
    parts += furn_pull(left - 0.055, 0.28, 0.12, front + 0.006)
    parts.append(label((right + left) / 2 - 0.03, 0.44, 0.2, 0.06, front + 0.006, "label_radio"))
    # The centre drawer between the pedestals, its box behind, the knee hole under it.
    inner = (-wide / 2 + 0.02 + pedestal + 0.01, wide / 2 - 0.02 - pedestal - 0.01)
    parts.append(shapes.box((inner[0], top - 0.16, body), (inner[1], top - 0.06, deep / 2 - 0.04), "painted_panel",
                            "drawer_box"))
    parts.append(shapes.bevelled(shapes.box((inner[0] + 0.01, top - 0.155, front + 0.006),
                                            (inner[1] - 0.01, top - 0.065, body), "painted_panel", "drawer"), 0.002))
    parts += furn_pull(0.0, top - 0.11, 0.14, front + 0.006, upright=False, name="pull")
    parts.append(shapes.box((inner[0], 0.22, deep / 2 - 0.045), (inner[1], top - 0.16, deep / 2 - 0.025),
                            "painted_panel", "modesty"))
    # The headset's hook on the desk's side (the viewer's right, -x).
    side = -wide / 2 + 0.02
    parts.append(shapes.box((side - 0.006, 0.56, -0.03), (side, 0.66, 0.03), "dark_panel", "hook_plate"))
    parts.append(shapes.cylinder((side - 0.006, 0.62, 0.0), (side - 0.05, 0.62, 0.0), 0.006, "bare_steel", 12, "hook"))
    parts.append(shapes.cylinder((side - 0.05, 0.615, 0.0), (side - 0.05, 0.65, 0.0), 0.006, "bare_steel", 12, "hook"))
    return parts


def furn_console_top(left_x, right_x, front, back, top):
    """One length of the console: its top, a recessed skirt under it with three louvred vents in real pockets, a
    pillar with a round foot under each end."""
    skirt_z = front + 0.1
    parts = [shapes.bevelled(shapes.box((right_x, top - 0.035, front), (left_x, top, back), "dark_panel", "top"),
                             EDGE),
             shapes.bevelled(shapes.box((right_x, top - 0.06, front - 0.004), (left_x, top - 0.035, front + 0.02),
                                        "bare_steel", "edge_trim"), 0.002)]
    skirt = shapes.box((right_x + 0.02, 0.14, skirt_z), (left_x - 0.02, top - 0.035, skirt_z + 0.02), "painted_panel",
                       "skirt")
    span = left_x - right_x
    vents = []
    for at in (0.25, 0.5, 0.75):
        vents += furn_louvres(skirt, right_x + span * at, 0.45, min(0.22, span * 0.22), 0.2, skirt_z, skirt_z + 0.02, 6,
                              "dark_panel", "vent")
    parts += [shapes.bevelled(skirt, 0.002)] + vents
    for x in (right_x + 0.12, left_x - 0.12):
        parts.append(shapes.cylinder((x, 0.02, 0.0), (x, top - 0.035, 0.0), 0.035, "bare_steel", 20, "pillar"))
        parts.append(shapes.bevelled(shapes.cylinder((x, 0.0, 0.0), (x, 0.02, 0.0), 0.11, "dark_panel", 32, "foot"),
                                     0.004))
    return parts


def console(size, laid):
    """The operations console, as its close-up shows it: a straight centre desk and two wings turned toward the
    operator, dark tops on pillars with round feet, recessed skirts with louvred vents, a cable tray along the back
    and the screens' cables running down into it and to the floor; its top left clear for the monitors and the
    keyboards (children of their own)."""
    wide, tall, deep = size
    top = FURN_DESK_TOP
    half = 0.525
    wing = (wide / 2 - half) / math.cos(math.radians(12.0)) + 0.02
    wing_deep = 0.5
    parts = furn_console_top(half, -half, -deep / 2, deep / 2, top)
    parts += furn_spun(furn_console_top(half + wing, half - 0.02, deep / 2 - wing_deep, deep / 2, top),
                       (half, deep / 2), 12.0)
    parts += furn_spun(furn_console_top(-half + 0.02, -half - wing, deep / 2 - wing_deep, deep / 2, top),
                       (-half, deep / 2), -12.0)
    tray = (deep / 2 - 0.09, deep / 2 - 0.01)
    parts += [shapes.box((-half, 0.6, tray[0]), (half, 0.608, tray[1]), "galvanized_steel", "cable_tray"),
              shapes.box((-half, 0.608, tray[0]), (half, 0.66, tray[0] + 0.004), "galvanized_steel", "cable_tray"),
              shapes.box((-half, 0.608, tray[1] - 0.004), (half, 0.66, tray[1]), "galvanized_steel", "cable_tray")]
    behind = deep / 2 + 0.012
    for x, _, _ in FURN_LIVE_SCREENS:
        drop = max(-half + 0.05, min(half - 0.05, x))
        parts.append(shapes.cylinder((drop, top + 0.12, behind), (drop, top - 0.01, behind), 0.006, "rubber", 10,
                                     "cable"))
        parts.append(shapes.cylinder((drop, top - 0.01, behind), (drop, 0.63, tray[1] - 0.03), 0.006, "rubber", 10,
                                     "cable"))
    parts.append(shapes.cylinder((-0.05, 0.63, tray[1] - 0.03), (-0.05, 0.0, tray[1] - 0.03), 0.012, "rubber", 12,
                                 "cable"))
    parts.append(shapes.cylinder((0.0, 0.63, tray[1] - 0.025), (0.0, 0.0, tray[1] - 0.025), 0.009, "rubber", 12,
                                 "cable"))
    return parts


def labbench(size, laid):
    """The lab bench, as its close-up shows it: a steel top on a square-tube frame with a foot rail, a drawer and
    cupboard pedestal at each end, two centre drawers, pulls and drawer labels; its top left clear for the glovebox
    (viewer's right) and the microscope (viewer's left), children of their own."""
    wide, tall, deep = size
    top = FURN_BENCH_TOP
    front = -deep / 2
    tube = 0.04
    parts = [shapes.bevelled(shapes.box((-wide / 2, top - 0.035, front), (wide / 2, top, deep / 2),
                                        "brushed_steel_fine", "top"), EDGE)]
    for x in (-wide / 2 + 0.01, wide / 2 - 0.01 - tube):
        for z in (front + 0.02, deep / 2 - 0.02 - tube):
            parts.append(shapes.box((x, 0.0, z), (x + tube, top - 0.035, z + tube), "bare_steel", "leg"))
    parts += [shapes.box((-wide / 2 + 0.01, top - 0.075, front + 0.02), (wide / 2 - 0.01, top - 0.035, front + 0.02 + tube),
                         "bare_steel", "rail"),
              shapes.box((-wide / 2 + 0.05, 0.1, deep / 2 - 0.02 - tube), (wide / 2 - 0.05, 0.1 + tube, deep / 2 - 0.02),
                         "bare_steel", "foot_rail")]
    for x in (-wide / 2 + 0.01, wide / 2 - 0.01 - tube):
        parts.append(shapes.box((x, 0.1, front + 0.06), (x + tube, 0.1 + tube, deep / 2 - 0.06), "bare_steel",
                                "foot_rail"))
    body = front + 0.035
    pedestal = 0.46
    for right, left, variant in ((wide / 2 - 0.06 - pedestal, wide / 2 - 0.06, "label_samples"),
                                 (-wide / 2 + 0.06, -wide / 2 + 0.06 + pedestal, "label_tools")):
        parts.append(shapes.bevelled(shapes.box((right, 0.14, body), (left, top - 0.075, deep / 2 - 0.06),
                                                "painted_panel", "pedestal"), EDGE))
        parts.append(shapes.bevelled(shapes.box((right + 0.015, top - 0.23, front + 0.02),
                                                (left - 0.015, top - 0.09, body), "painted_panel", "drawer"), 0.002))
        parts += furn_pull((right + left) / 2, top - 0.185, 0.14, front + 0.02, upright=False, name="pull")
        parts.append(label((right + left) / 2, top - 0.125, 0.16, 0.045, front + 0.02, variant))
        parts.append(shapes.bevelled(shapes.box((right + 0.015, 0.16, front + 0.02), (left - 0.015, top - 0.245, body),
                                                "painted_panel", "door"), 0.002))
        parts += furn_pull(left - 0.05 if right > 0 else right + 0.05, 0.42, 0.12, front + 0.02)
    inner = (-wide / 2 + 0.06 + pedestal + 0.02, wide / 2 - 0.06 - pedestal - 0.02)
    middle = (inner[0] + inner[1]) / 2
    for low, high in ((inner[0], middle - 0.005), (middle + 0.005, inner[1])):
        parts.append(shapes.box((low, top - 0.2, body), (high, top - 0.075, deep / 2 - 0.08), "painted_panel",
                                "drawer_box"))
        parts.append(shapes.bevelled(shapes.box((low + 0.01, top - 0.195, front + 0.02), (high - 0.01, top - 0.08, body),
                                                "painted_panel", "drawer"), 0.002))
        parts += furn_pull((low + high) / 2, top - 0.14, 0.12, front + 0.02, upright=False, name="pull")
    return parts


# The toolboard's default layout (the hook grid until the made tools give theirs): each tool hangs from its top middle
# (x, y on the board), `long` metres long. Seen from the front +x is the viewer's left.
FURN_TOOLS = ([{"tool": "wrench", "x": 0.53 - 0.05 * at, "y": 0.74, "long": 0.24 - 0.012 * at} for at in range(10)]
              + [{"tool": "hammer", "x": x, "y": 0.74, "long": 0.3} for x in (-0.04, -0.17, -0.30)]
              + [{"tool": "pump_pliers", "x": -0.46, "y": 0.74, "long": 0.25}]
              + [{"tool": "wrench", "x": 0.52, "y": 0.4, "long": 0.3}]
              + [{"tool": "pliers", "x": 0.41 - 0.09 * at, "y": 0.4, "long": 0.2} for at in range(6)]
              + [{"tool": "screwdriver", "x": -0.2 - 0.07 * at, "y": 0.3, "long": 0.22} for at in range(5)])
# How far apart a tool's pair of pegs stands, and how far under its top.
FURN_PEGS = {"wrench": (0.026, 0.035), "hammer": (0.05, 0.06), "pump_pliers": (0.04, 0.05), "pliers": (0.04, 0.045)}


def toolboard(size, laid):
    """A wooden tool board, as its close-up shows it: the board with a thin edge, a pair of pegs for every hanging
    tool and a rack bar with a hole for every screwdriver, laid by the tools' own layout (laid["tools"]), and the
    printed plate of the tools' outlines on its face; the tools are children of their own."""
    wide, tall, deep = size
    back = deep / 2
    face = back - 0.022
    rim = 0.015
    tools = laid.get("tools", FURN_TOOLS)
    parts = [shapes.box((-wide / 2 + rim, rim, face), (wide / 2 - rim, tall - rim, back), "wood_board", "board"),
             shapes.content_plate((-wide / 2 + rim, rim, face - 0.0015), (wide / 2 - rim, tall - rim, face),
                                  laid.get("outlines", "label_sign_out"), "outlines")]
    for low, high in (((-wide / 2, 0.0), (wide / 2, rim)), ((-wide / 2, tall - rim), (wide / 2, tall)),
                      ((-wide / 2, rim), (-wide / 2 + rim, tall - rim)), ((wide / 2 - rim, rim), (wide / 2, tall - rim))):
        parts.append(shapes.bevelled(shapes.box((*low, face - 0.004), (*high, back), "wood_board", "edge"), 0.002))
    for tool in tools:
        if tool["tool"] == "screwdriver":
            continue
        apart, under = FURN_PEGS[tool["tool"]]
        for side in (-1, 1):
            peg_x, peg_y = tool["x"] + side * apart / 2, tool["y"] - under
            parts.append(shapes.cylinder((peg_x, peg_y, face - 0.0015), (peg_x, peg_y + 0.006, face - 0.04), 0.0035,
                                         "bare_steel", 10, "peg"))
    drivers = [tool for tool in tools if tool["tool"] == "screwdriver"]
    if drivers:
        xs = [tool["x"] for tool in drivers]
        bar_y = drivers[0]["y"] - 0.07
        rack_bar = shapes.box((min(xs) - 0.05, bar_y - 0.012, face - 0.05), (max(xs) + 0.05, bar_y + 0.012, face - 0.0015),
                              "wood_board", "rack")
        for x in xs:
            shapes.cut(rack_bar, shapes.cylinder((x, bar_y - 0.05, face - 0.025), (x, bar_y + 0.05, face - 0.025), 0.007,
                                                 "rubber", 12, "cutter"))
        parts.append(shapes.bevelled(rack_bar, 0.002))
        for side in (min(xs) - 0.04, max(xs) + 0.04):
            parts.append(shapes.box((side - 0.008, bar_y - 0.012, face - 0.05), (side + 0.008, bar_y + 0.04, face - 0.0015),
                                    "wood_board", "rack_bracket"))
    return parts


def waste_bin(size, laid):
    """A pedal bin, as its close-up shows it: a square body with rounded corners on a base tray, a rolled rim, a
    domed lid on a hinge at the back, a ribbed foot pedal and a label."""
    wide, tall, deep = size
    corner = 0.03
    body_half = (wide / 2 - 0.012, deep / 2 - 0.012)
    plan = rounded_outline((-body_half[0], -body_half[1]), body_half, corner)
    parts = [shapes.bevelled(furn_prism(plan, "y", 0.03, tall - 0.04, "brushed_steel_fine", "body"), 0.003),
             shapes.bevelled(furn_prism(rounded_outline((-wide / 2, -deep / 2), (wide / 2, deep / 2), corner + 0.01),
                                        "y", 0.0, 0.035, "cast_iron_dark", "base_tray"), 0.004),
             shapes.bevelled(furn_prism(rounded_outline((-body_half[0] - 0.006, -body_half[1] - 0.006),
                                                        (body_half[0] + 0.006, body_half[1] + 0.006), corner + 0.006),
                                        "y", tall - 0.055, tall - 0.04, "bare_steel", "rim"), 0.003),
             shapes.bevelled(furn_prism(rounded_outline((-wide / 2 + 0.006, -deep / 2 + 0.04),
                                                        (wide / 2 - 0.006, deep / 2 - 0.004), corner + 0.01),
                                        "y", tall - 0.04, tall - 0.012, "brushed_steel_fine", "lid"), 0.01),
             shapes.box((-0.06, tall - 0.045, deep / 2 - 0.004), (0.06, tall - 0.02, deep / 2 + 0.006), "bare_steel",
                        "hinge"),
             shapes.box((-0.04, 0.015, -deep / 2 - 0.02), (0.04, 0.03, -deep / 2 + 0.035), "cast_iron_dark", "pedal_arm")]
    pedal = shapes.bevelled(shapes.box((-0.055, 0.03, -deep / 2 - 0.075), (0.055, 0.045, -deep / 2 - 0.015),
                                       "cast_iron_dark", "pedal"), 0.003)
    parts.append(pedal)
    for at in range(4):
        z = -deep / 2 - 0.068 + at * 0.015
        parts.append(shapes.box((-0.045, 0.045, z), (0.045, 0.049, z + 0.006), "cast_iron_dark", "pedal_rib"))
    parts.append(label(0.03, tall * 0.62, 0.11, 0.05, -body_half[1], "label_waste"))
    return parts


def monitor(size, laid):
    """A console monitor on its stand, as its close-up shows it: a black bezel round an opening the live glass (the
    Workstation's) or its own glowing screen sits in, a back case, a neck and a round foot; its foot middle at the
    origin."""
    wide, tall, deep = size
    open_wide, open_tall = FURN_SCREEN_OPENING
    border = 0.03
    middle = FURN_SCREEN_MIDDLE
    low = (-open_wide / 2 - border, middle - open_tall / 2 - border)
    high = (open_wide / 2 + border, middle + open_tall / 2 + border)
    parts = [shapes.bevelled(rounded_ring(low, high, 0.012, border, FURN_SCREEN_FACE, 0.004, "anodized_black", "bezel"),
                             0.003),
             shapes.box((-open_wide / 2, middle - open_tall / 2, 0.0), (open_wide / 2, middle + open_tall / 2, 0.004),
                        "anodized_black", "panel"),
             shapes.bevelled(shapes.box((low[0] + 0.02, low[1] + 0.02, 0.004), (high[0] - 0.02, high[1] - 0.02, 0.05),
                                        "anodized_black", "case"), 0.006),
             shapes.box((-0.025, 0.015, 0.02), (0.025, low[1] + 0.03, 0.045), "anodized_black", "neck"),
             shapes.bevelled(shapes.cylinder((0.0, 0.0, 0.02), (0.0, 0.015, 0.02), 0.085, "anodized_black", 32, "foot"),
                             0.004)]
    if not laid.get("live"):
        parts.append(shapes.content_plate((-open_wide / 2, middle - open_tall / 2, -0.006),
                                          (open_wide / 2, middle + open_tall / 2, -0.002), laid.get("screen", "screen"),
                                          "glass"))
    return parts


def radio(size, laid):
    """A field radio set, as its close-up shows it: a case with carry handles at its front corners, a dark face in
    two panels (a meter, a display window and a tuning dial over three knobs, three toggle switches and a slotted
    speaker grille), and the handset in its cradle on the right side (round six: its Pixal3D model came back leaning
    eleven degrees, so it is built square)."""
    wide, tall, deep = size
    front = -deep / 2
    cradle = 0.06
    case_right = -wide / 2 + cradle  # the handset stands at the viewer's right (-x)
    parts = [shapes.bevelled(shapes.box((case_right, 0.0, front + 0.012), (wide / 2, tall, deep / 2), "painted_panel",
                                        "case"), 0.008)]
    face = front + 0.012
    middle_x = (case_right + wide / 2) / 2
    span = wide / 2 - case_right
    for low, high in ((0.02, tall * 0.5 - 0.004), (tall * 0.5 + 0.004, tall - 0.02)):
        parts.append(shapes.bevelled(shapes.box((case_right + 0.03, low, face - 0.006),
                                                (wide / 2 - 0.03, high, face), "dark_panel", "panel"), 0.002))
    panel = face - 0.006
    top_middle = tall * 0.75
    parts.append(shapes.box((middle_x + span * 0.28, top_middle - 0.03, panel - 0.004),
                            (middle_x + span * 0.42, top_middle + 0.03, panel), "glass_frosted", "meter"))
    parts.append(shapes.box((middle_x - span * 0.16, top_middle - 0.032, panel - 0.004),
                            (middle_x + span * 0.2, top_middle + 0.032, panel), "glass_tinted", "display"))
    parts.append(shapes.bevelled(shapes.cylinder((middle_x - span * 0.32, top_middle, panel),
                                                 (middle_x - span * 0.32, top_middle, panel - 0.022), 0.032,
                                                 "rubber", 24, "dial"), 0.003))
    low_middle = tall * 0.32
    for share in (0.3, 0.12, -0.06):
        x = middle_x + span * share
        parts.append(shapes.bevelled(shapes.cylinder((x, low_middle + 0.02, panel), (x, low_middle + 0.02, panel - 0.02),
                                                     0.016, "rubber", 16, "knob"), 0.002))
        parts.append(shapes.cylinder((x, low_middle - 0.05, panel), (x, low_middle - 0.05, panel - 0.016), 0.004,
                                     "bare_steel", 8, "switch"))
    grille = (middle_x - span * 0.42, low_middle - 0.075, middle_x - span * 0.14, low_middle + 0.07)
    parts.append(shapes.bevelled(rounded_ring((grille[0], grille[1]), (grille[2], grille[3]), 0.008, 0.008,
                                              panel - 0.006, panel, "bare_steel", "grille_frame"), 0.001))
    for at in range(7):
        y = grille[1] + 0.014 + (grille[3] - grille[1] - 0.028) * at / 6
        parts.append(shapes.box((grille[0] + 0.01, y - 0.0025, panel - 0.004), (grille[2] - 0.01, y + 0.0025, panel),
                                "rubber", "grille"))
    for x in (case_right + 0.012, wide / 2 - 0.012):
        parts.append(shapes.cylinder((x, 0.03, front - 0.012), (x, tall - 0.03, front - 0.012), 0.006, "bare_steel", 12,
                                     "handle"))
        for y in (0.03, tall - 0.03):
            parts.append(shapes.cylinder((x, y, front - 0.012), (x, y, face), 0.006, "bare_steel", 12, "handle_post"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2, 0.02, -deep / 4), (case_right, tall * 0.85, deep / 4),
                                            "dark_panel", "cradle"), 0.004))
    parts.append(shapes.bevelled(shapes.box((-wide / 2 - 0.0, tall * 0.18, -deep / 4 - 0.025),
                                            (case_right - 0.008, tall * 0.92, -deep / 4 + 0.012), "rubber", "handset"),
                                 0.01))
    return parts


def screwdriver(size, laid):
    """A flat screwdriver standing handle up in its rack, as its close-up shows it: a fluted handle, a ferrule, a
    round shaft and a flat tip (round six: its Pixal3D model came back with a bent shaft, so it is built straight)."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2
    handle = tall * 0.42
    parts = [shapes.bevelled(shapes.cylinder((0.0, tall - handle, 0.0), (0.0, tall, 0.0), radius, "warning_paint", 6,
                                             "handle"), 0.002),
             shapes.cylinder((0.0, tall - handle - 0.012, 0.0), (0.0, tall - handle, 0.0), radius * 0.45, "bare_steel",
                             12, "ferrule"),
             shapes.cylinder((0.0, 0.012, 0.0), (0.0, tall - handle - 0.012, 0.0), radius * 0.2, "bare_steel", 10,
                             "shaft")]
    parts.append(shapes.box((-radius * 0.35, 0.0, -radius * 0.08), (radius * 0.35, 0.014, radius * 0.08), "bare_steel",
                            "tip"))
    return parts


def keyboard(size, laid):
    """A console keyboard, as its close-up shows it: a housing, rows of keys, a palm pad and a cable out of its
    back."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, 0.022, deep / 2), "anodized_black",
                                        "housing"), 0.004),
             shapes.box((-0.06, 0.022, -deep / 2 + 0.01), (0.06, 0.025, -deep / 2 + 0.04), "rubber", "pad")]
    columns, rows = 15, 5
    key_w = (wide - 0.03) / columns
    key_d = (deep - 0.06) / rows
    for row in range(rows):
        for column in range(columns):
            x = -wide / 2 + 0.015 + column * key_w
            z = -deep / 2 + 0.05 + row * key_d
            parts.append(shapes.box((x + 0.002, 0.022, z + 0.002), (x + key_w - 0.002, 0.03, z + key_d - 0.002),
                                    "plastic_grey", "key"))
    parts.append(shapes.cylinder((0.12, 0.011, deep / 2), (0.12, 0.011, deep / 2 + 0.04), 0.004, "rubber", 8, "cable"))
    return parts


def glovebox(size, laid):
    """A glovebox, as its close-up shows it: a box whose front slopes back at the top, a framed sloped window with
    two glove ports, gloves hanging from them, latches, a service box on its side and a label."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    knee = 0.4  # where the front turns from upright to sloped
    ridge = front + deep * 0.48  # where the slope meets the top
    profile = [(front, 0.0), (back, 0.0), (back, tall), (ridge, tall), (front, knee)]
    parts = [shapes.bevelled(furn_prism(profile, "x", -wide / 2, wide / 2, "painted_panel", "body"), EDGE)]
    # The slope as a line in the side profile (z, y), its unit direction up it and its outward normal.
    run = (ridge - front, tall - knee)
    length = math.hypot(*run)
    along = (run[0] / length, run[1] / length)
    out = (-along[1], along[0])

    def on_slope(share, offset):
        return (front + run[0] * share + out[0] * offset, knee + run[1] * share + out[1] * offset)

    band = [on_slope(0.1, -0.01), on_slope(0.9, -0.01), on_slope(0.9, 0.014), on_slope(0.1, 0.014)]
    frame = furn_prism(band, "x", -wide / 2 + 0.04, wide / 2 - 0.04, "dark_panel", "window_frame")
    opening = [on_slope(0.16, -0.05), on_slope(0.84, -0.05), on_slope(0.84, 0.05), on_slope(0.16, 0.05)]
    shapes.cut(frame, furn_prism(opening, "x", -wide / 2 + 0.1, wide / 2 - 0.1, "rubber", "cutter"))
    glass = furn_prism([on_slope(0.12, 0.002), on_slope(0.88, 0.002), on_slope(0.88, 0.007), on_slope(0.12, 0.007)],
                       "x", -wide / 2 + 0.08, wide / 2 - 0.08, "glass_tinted", "glass")
    port_z, port_y = on_slope(0.3, 0.004)
    port_out = (out[0] * 0.025, out[1] * 0.025)
    for x in (-0.19, 0.19):
        shapes.cut(glass, shapes.cylinder((x, port_y - out[1] * 0.05, port_z - out[0] * 0.05),
                                          (x, port_y + out[1] * 0.05, port_z + out[0] * 0.05), 0.064, "rubber", 32,
                                          "cutter"))
    parts += [shapes.bevelled(frame, 0.003), glass]
    for x in (-0.19, 0.19):
        parts.append(shapes.bevelled(shapes.ring((x, port_y, port_z), (x, port_y + port_out[1], port_z + port_out[0]),
                                                 0.085, 0.064, "gasket_black", 32, "port"), 0.003))
        cuff = (x, port_y + port_out[1] * 0.6, port_z + port_out[0] * 0.6)
        parts.append(shapes.cylinder(cuff, (x, port_y - 0.06, front - 0.06), 0.045, "rubber", 16, "glove"))
        parts.append(shapes.cylinder((x, port_y - 0.06, front - 0.06), (x, 0.12, front - 0.05), 0.038, "rubber", 16,
                                     "glove"))
    for x in (-wide / 2 + 0.12, wide / 2 - 0.12):
        parts.append(shapes.bevelled(shapes.box((x - 0.025, knee - 0.06, front - 0.014), (x + 0.025, knee - 0.02, front),
                                                "bare_steel", "latch"), 0.002))
    side = -wide / 2
    parts.append(shapes.bevelled(shapes.box((side - 0.06, 0.28, -0.08), (side, 0.52, 0.08), "painted_panel",
                                            "service_box"), 0.004))
    parts.append(shapes.cylinder((side - 0.03, 0.52, 0.0), (side - 0.03, tall - 0.04, 0.0), 0.012, "pipe_steel", 12,
                                 "conduit"))
    parts.append(label(0.0, 0.22, 0.16, 0.05, front, "label_glovebox"))
    return parts


# ---- Modules round (2026-10-07): the habitat's sleep pods, locker bank, food store shelf, medical cabinet and hygiene
# cubicle, built in code with library surfaces as method B's parts check allows, and the plain objects on them (food
# jugs, tubs and ration boxes, medical boxes and bottles, the berths' pillows) as children of their own. A holder leaves
# clear flat spots for its children and never carries them. Helpers are prefixed `hab_a_`. Seen from in front, the
# kit's +x is the viewer's left.

# The sleep pod's two berth cavities (bottom, top over the pod's foot) and the stripe band between them.
HAB_A_BERTHS = ((0.12, 0.76), (0.94, 1.58))
HAB_A_POD_STRIPE = (0.795, 0.905)
# The berths' opening across the pod (x, low then high): the control column takes the viewer's right.
HAB_A_POD_OPENING = (-0.62, 0.96)
HAB_A_POD_COLUMN = (-1.01, -0.70)
HAB_A_MATTRESS = 0.11
# The food shelf's shelf tops over its foot (the base and four shelves), its bays across it (x, low then high) and the
# divider between them.
HAB_A_SHELF_TOPS = tuple(round(0.10 + 0.366 * level, 3) for level in range(5))
HAB_A_WIDE_BAY = (-0.265, 0.83)
HAB_A_NARROW_BAY = (-0.83, -0.305)
# The medical cabinet's lower cupboard top and its upper glass case's inside floor and shelf.
HAB_A_MED_SPLIT = 0.8
HAB_A_MED_FLOOR = 0.845
HAB_A_MED_SHELF = 1.30


def hab_a_moved(parts, offset):
    """Parts moved by a kit-frame offset."""
    for part in parts:
        floor_moved(part, offset)
    return parts


def hab_a_rounded_cut(part, low, high, radius, depth_from, depth_to):
    """A rounded-rectangle hole (x, y corners) cut through a part between two depths."""
    shapes.cut(part, shapes.prism(rounded_outline(low, high, radius), depth_from, depth_to, "rubber", "cutter"))
    return part


def hab_a_vent(x, y, wide, tall, surface, slats, material="dark_panel"):
    """A small slotted vent plate on a face at depth `surface`: a plate with slats standing proud of it."""
    parts = [shapes.bevelled(shapes.box((x - wide / 2, y - tall / 2, surface - 0.004), (x + wide / 2, y + tall / 2,
                                                                                        surface), material, "vent"),
                             0.001)]
    pitch = tall / slats
    for at in range(slats):
        middle = y - tall / 2 + pitch * (at + 0.5)
        parts.append(shapes.box((x - wide / 2 + 0.008, middle - 0.003, surface - 0.009),
                                (x + wide / 2 - 0.008, middle + 0.003, surface - 0.004), "anodized_black", "vent"))
    return parts


def sleep_pod(size, laid):
    """A sleep pod of two berths stacked, as its close-up shows it: a pale panelled shell, a rounded opening into each
    berth with a raised rim and a copper seal, a mattress on each berth's floor, a small screen and a gooseneck
    reading lamp on each berth's back wall, a strip lamp under each berth's ceiling and a vent beside it, a control
    column on the viewer's right with a keypad, a small display and a light switch, a blue stripe round the shell
    between the berths, and its labels; the pillows are children of their own."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    shell = shapes.box((-wide / 2, 0.0, front), (wide / 2, tall, back), "enamel_white", "shell")
    low_x, high_x = HAB_A_POD_OPENING
    for bottom, top in HAB_A_BERTHS:
        hab_a_rounded_cut(shell, (low_x, bottom), (high_x, top), 0.09, front - 0.05, back - 0.04)
    parts = [shapes.bevelled(shell, EDGE)]
    for bottom, top in HAB_A_BERTHS:
        parts.append(shapes.bevelled(rounded_ring((low_x - 0.035, bottom - 0.035), (high_x + 0.035, top + 0.035), 0.12,
                                                  0.05, front - 0.012, front + 0.002, "enamel_white", "rim"), 0.003))
        parts.append(rounded_ring((low_x - 0.004, bottom - 0.004), (high_x + 0.004, top + 0.004), 0.092, 0.012,
                                  front + 0.002, front + 0.05, "anodized_gold", "seal"))
        inner_back = back - 0.04
        parts.append(shapes.bevelled(shapes.box((low_x + 0.03, bottom, front + 0.06),
                                                (high_x - 0.03, bottom + HAB_A_MATTRESS, inner_back - 0.01),
                                                "quilted_beige", "mattress"), 0.02))
        parts += wall_screen_part(high_x - 0.2, bottom + 0.37, 0.2, 0.15, inner_back, "screen", name="screen")
        parts.append(shapes.bevelled(shapes.box((high_x - 0.32, bottom + 0.24, inner_back - 0.03),
                                                (high_x - 0.08, bottom + 0.285, inner_back), "dark_panel",
                                                "screen_unit"), 0.002))
        lamp_x = high_x - 0.48
        parts.append(shapes.cylinder((lamp_x, bottom + 0.30, inner_back), (lamp_x, bottom + 0.30, inner_back - 0.006),
                                     0.022, "anodized_gold", 20, "reading_lamp"))
        parts.append(shapes.cylinder((lamp_x, bottom + 0.30, inner_back - 0.006), (lamp_x, bottom + 0.42,
                                                                                   inner_back - 0.07), 0.006,
                                     "anodized_gold", 10, "reading_lamp"))
        parts.append(shapes.cylinder((lamp_x, bottom + 0.42, inner_back - 0.07), (lamp_x, bottom + 0.40,
                                                                                  inner_back - 0.13), 0.022,
                                     "anodized_gold", 16, "reading_lamp"))
        parts.append(shapes.cylinder((lamp_x, bottom + 0.398, inner_back - 0.133), (lamp_x, bottom + 0.394,
                                                                                    inner_back - 0.137), 0.017,
                                     "lamp_lens", 16, "reading_lamp_lens"))
        ceiling = top - 0.004
        parts.append(shapes.bevelled(shapes.box((low_x + 0.35, ceiling - 0.035, front + 0.12),
                                                (low_x + 0.85, ceiling, front + 0.2), "bare_steel", "strip_lamp"),
                                     0.002))
        parts.append(shapes.box((low_x + 0.37, ceiling - 0.04, front + 0.13), (low_x + 0.83, ceiling - 0.035,
                                                                                 front + 0.19), "lamp_strip",
                                "strip_lamp_lens"))
        parts += hab_a_vent(low_x + 0.22, bottom + 0.45, 0.14, 0.1, inner_back, 4, "enamel_white")
    col_low, col_high = HAB_A_POD_COLUMN
    middle = (col_low + col_high) / 2
    plate = shapes.bevelled(shapes.box((col_low, 0.2, front - 0.008), (col_high, tall - 0.2, front), "enamel_white",
                                       "control_panel"), 0.002)
    parts.append(plate)
    parts += wall_screen_part(middle, 1.25, 0.12, 0.08, front - 0.008, "screen_amber", name="display")
    parts.append(label(middle, 1.12, 0.12, 0.13, front - 0.008, "keypad_print", name="keypad"))
    parts.append(wall_button(middle, 0.98, 0.04, 0.06, front - 0.008, "anodized_black", "switch"))
    parts.append(label(middle, 1.42, 0.16, 0.045, front - 0.008, "label_control"))
    parts.append(label(middle, 0.62, 0.16, 0.045, front - 0.008, "label_berth_2"))
    parts.append(label(middle, 1.62, 0.16, 0.045, front - 0.008, "label_berth_1"))
    band_low, band_high = HAB_A_POD_STRIPE
    for x_low, x_high in ((col_high, wide / 2), (-wide / 2, col_low)):
        parts.append(shapes.box((x_low, band_low, front - 0.003), (x_high, band_high, front), "enamel_blue", "stripe"))
    for side in (-1, 1):
        x = side * wide / 2
        parts.append(shapes.box((min(x, x + side * 0.003), band_low, front), (max(x, x + side * 0.003), band_high,
                                                                               back), "enamel_blue", "stripe"))
    parts.append(label(high_x - 0.2, 1.675, 0.26, 0.06, front, "label_sleep_pod"))
    return parts


def pillow(size, laid):
    """A berth's pillow, as its close-up shows it: one plump rounded cushion."""
    wide, tall, deep = size
    return [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "quilted_grey",
                                       "pillow"), min(tall, deep) * 0.4)]


def locker_bank(size, laid):
    """The crew's locker bank, as its close-up shows it: two steel cabinets of two lockers side by side, each door with
    pressed louvres top and bottom, a pull and hinge pins, a hasp for a padlock at each pair's meeting edges, a crew
    name label each and a few stickers."""
    wide, tall, deep = size
    half = wide / 2
    parts = []
    names = (("label_crew_lkr_2", "label_crew_lkr_1"), ("label_crew_lkr_4", "label_crew_lkr_3"))
    for index, side in enumerate((1, -1)):
        cabinet = furn_locker((half - 0.004, tall, deep), 2, names[index])
        parts += hab_a_moved(cabinet, (side * half / 2, 0.0, 0.0))
    front = -deep / 2
    for middle in (half / 2, -half / 2):
        parts.append(shapes.bevelled(shapes.box((middle - 0.02, tall * 0.43, front - 0.012),
                                                (middle + 0.02, tall * 0.43 + 0.05, front), "bare_steel", "hasp"),
                                     0.002))
    door = (half - 0.004 - 0.03 - 0.008) / 2
    for x, y, variant in ((half / 2 + door / 2 + 0.004, 1.32, "note_crew_keep_shut"),
                          (-half / 2 - door / 2 - 0.004, 1.18, "note_crew_keep_shut")):
        parts.append(label(x, y, 0.09, 0.06, front, variant, turn=-3.0, thick=0.004, name="sticker"))
    return parts


def food_shelf(size, laid):
    """The food store, as its close-up shows it: an open steel shelf unit with a top overhanging it, sides and a back,
    a wide bay and a narrow one either side of an upright divider, four shelves and a base each with a front lip, and
    a kick plate; its jugs, tubs and ration boxes are children of their own."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    side_t = 0.02
    parts = [shapes.bevelled(shapes.box((-wide / 2, tall - 0.04, front - 0.015), (wide / 2, tall, back), "galvanized_steel",
                                        "top"), EDGE),
             shapes.bevelled(shapes.box((-wide / 2 + 0.01, 0.0, front + 0.01), (wide / 2 - 0.01, HAB_A_SHELF_TOPS[0] - 0.025,
                                                                                back - 0.02), "galvanized_steel",
                                        "plinth"), 0.003),
             shapes.box((-wide / 2 + side_t, 0.0, back - 0.02), (wide / 2 - side_t, tall - 0.04, back), "galvanized_steel",
                        "back")]
    for x in (-wide / 2, wide / 2 - side_t):
        parts.append(shapes.bevelled(shapes.box((x, 0.0, front), (x + side_t, tall - 0.04, back), "galvanized_steel",
                                                "side"), 0.003))
    divider = (HAB_A_NARROW_BAY[1], HAB_A_WIDE_BAY[0])
    parts.append(shapes.bevelled(shapes.box((divider[0], HAB_A_SHELF_TOPS[0], front), (divider[1], tall - 0.04,
                                                                                         back - 0.02),
                                            "galvanized_steel", "divider"), 0.003))
    for level, top in enumerate(HAB_A_SHELF_TOPS):
        for low_x, high_x in (HAB_A_WIDE_BAY, HAB_A_NARROW_BAY):
            parts.append(shapes.box((low_x, top - 0.025, front + 0.01), (high_x, top, back - 0.02), "galvanized_steel",
                                    "shelf"))
            parts.append(shapes.bevelled(shapes.box((low_x, top - 0.045, front + 0.004), (high_x, top + 0.012,
                                                                                         front + 0.016),
                                                    "galvanized_steel", "lip"), 0.002))
    return parts


def food_jug(size, laid):
    """A food jerrycan, as its close-up shows it: a squared white plastic jug with rounded edges, a carry handle
    moulded across its top, a screw cap at one corner and a paper label on its front."""
    wide, tall, deep = size
    front = -deep / 2
    body_top = tall * 0.84
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front), (wide / 2, body_top, deep / 2), "plastic_white",
                                        "body"), 0.018)]
    grip = shapes.box((-wide * 0.32, body_top - 0.01, -0.01), (wide * 0.18, tall, 0.01), "plastic_white", "handle")
    furn_cut_box(grip, (-wide * 0.24, body_top + 0.008, -0.02), (wide * 0.10, tall - 0.012, 0.02))
    parts.append(shapes.bevelled(grip, 0.004))
    parts.append(shapes.cylinder((wide * 0.32, body_top - 0.005, deep * 0.2), (wide * 0.32, tall - 0.012, deep * 0.2),
                                 0.018, "plastic_grey", 20, "cap"))
    parts.append(label(0.0, body_top * 0.48, wide * 0.78, body_top * 0.5, front, "label_food_pack"))
    return parts


def food_tin(size, laid):
    """A food storage tub, as its close-up shows it: a squared white jar with rounded corners, a round blue screw lid
    and a label round its front."""
    wide, tall, deep = size
    front = -deep / 2
    body_top = tall * 0.8
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front), (wide / 2, body_top, deep / 2), "plastic_white",
                                        "body"), 0.016),
             shapes.bevelled(shapes.cylinder((0.0, body_top - 0.004, 0.0), (0.0, tall, 0.0), min(wide, deep) * 0.47,
                                             "anodized_blue", 32, "lid"), 0.004)]
    parts.append(label(0.0, body_top * 0.5, wide * 0.8, body_top * 0.48, front, "label_food_storage"))
    return parts


def ration_box(size, laid):
    """A ration box, as its close-up shows it: a low tan plastic box, a fitted lid with a lip a little wider than it
    and a label on its front."""
    wide, tall, deep = size
    front = -deep / 2
    lid = tall * 0.25
    parts = [shapes.bevelled(shapes.box((-wide / 2 + 0.006, 0.0, front + 0.006), (wide / 2 - 0.006, tall - lid,
                                                                                  deep / 2 - 0.006), "canvas_beige",
                                        "box"), 0.01),
             shapes.bevelled(shapes.box((-wide / 2, tall - lid, front), (wide / 2, tall, deep / 2), "canvas_beige",
                                        "lid"), 0.008)]
    parts.append(label(0.0, (tall - lid) * 0.5, wide * 0.62, (tall - lid) * 0.5, front + 0.006, "label_rations"))
    return parts


def med_box(size, laid):
    """A carton of medical supplies, as its close-up shows it: an upright white box, a teal band round its top and its
    foot, and a printed panel on its front."""
    wide, tall, deep = size
    front = -deep / 2
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front), (wide / 2, tall, deep / 2), "plastic_white", "box"),
                             0.003)]
    for low, high in ((tall * 0.82, tall - 0.004), (0.004, tall * 0.1)):
        parts.append(shapes.box((-wide / 2 - 0.002, low, front - 0.002), (wide / 2 + 0.002, high, deep / 2 + 0.002),
                                "enamel_blue", "band"))
    parts.append(label(0.0, tall * 0.46, wide * 0.8, tall * 0.4, front - 0.002, "label_medical_supplies"))
    return parts


def med_bottle(size, laid):
    """A medicine bottle, as its close-up shows it: a round amber glass bottle with shoulders and a neck, a white screw
    cap and a paper band round it."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2
    shoulder = tall * 0.68
    parts = [shapes.cylinder((0.0, 0.0, 0.0), (0.0, shoulder, 0.0), radius, "glass_tinted", 24, "bottle"),
             shapes.cylinder((0.0, shoulder, 0.0), (0.0, shoulder + tall * 0.08, 0.0), radius * 0.75, "glass_tinted",
                             24, "bottle"),
             shapes.cylinder((0.0, shoulder + tall * 0.08, 0.0), (0.0, tall * 0.86, 0.0), radius * 0.45,
                             "glass_tinted", 20, "bottle"),
             shapes.bevelled(shapes.cylinder((0.0, tall * 0.86, 0.0), (0.0, tall, 0.0), radius * 0.55, "plastic_white",
                                             20, "cap"), 0.002),
             shapes.cylinder((0.0, shoulder * 0.25, 0.0), (0.0, shoulder * 0.8, 0.0), radius + 0.0015, "canvas_beige",
                             24, "band")]
    return parts


def med_cabinet(size, laid):
    """The medical cabinet, as its close-up shows it: a steel cupboard of two doors under a case of two glazed doors,
    each door with a pull, the glazed doors' frames round their glass, a first aid cross on the right glazed door, a
    taped note and a scuffed stencil on the cupboard; the case's boxes and bottles are children of their own (its
    inner shelf stands behind the glass, which the parts check reads as opaque)."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    face = front + 0.015
    lower = shapes.box((-wide / 2, 0.0, face), (wide / 2, HAB_A_MED_SPLIT, back), "painted_panel", "carcass")
    upper = shapes.box((-wide / 2 + 0.01, HAB_A_MED_SPLIT + 0.01, face), (wide / 2 - 0.01, tall, back), "painted_panel",
                       "carcass")
    furn_cut_box(upper, (-wide / 2 + 0.03, HAB_A_MED_FLOOR, face - 0.05), (wide / 2 - 0.03, tall - 0.03, back - 0.02))
    parts = [shapes.bevelled(lower, EDGE), shapes.bevelled(upper, EDGE)]
    parts.append(shapes.box((-wide / 2 + 0.03, HAB_A_MED_SHELF - 0.018, face), (wide / 2 - 0.03, HAB_A_MED_SHELF,
                                                                                back - 0.02), "painted_panel", "shelf"))
    gap = 0.006
    door_wide = (wide - 0.04 - gap) / 2
    for index in range(2):
        right = -wide / 2 + 0.02 + index * (door_wide + gap)
        left = right + door_wide
        parts.append(shapes.bevelled(shapes.box((right, 0.03, front), (left, HAB_A_MED_SPLIT - 0.02, face),
                                                "painted_panel", "door"), 0.002))
        pull_x = left - 0.05 if index == 0 else right + 0.05
        parts += furn_pull(pull_x, HAB_A_MED_SPLIT * 0.62, 0.1, front)
        frame = shapes.box((right, HAB_A_MED_SPLIT + 0.03, front), (left, tall - 0.02, face), "painted_panel",
                           "glass_door")
        furn_cut_box(frame, (right + 0.05, HAB_A_MED_SPLIT + 0.08, front - 0.05), (left - 0.05, tall - 0.07, face + 0.05))
        parts.append(shapes.bevelled(frame, 0.002))
        parts.append(shapes.box((right + 0.045, HAB_A_MED_SPLIT + 0.075, front + 0.006), (left - 0.045, tall - 0.065,
                                                                                            front + 0.01), "glass",
                                "glass"))
        parts += furn_pull(pull_x, (HAB_A_MED_SPLIT + tall) / 2, 0.1, front)
    right_door = -wide / 2 + 0.02 + door_wide / 2  # the viewer's right pair of doors' middle
    left_door = -right_door
    parts.append(label(right_door - 0.12, tall - 0.2, 0.1, 0.1, front + 0.006, "label_first_aid"))
    parts.append(label(right_door - 0.04, HAB_A_MED_SPLIT * 0.8, 0.12, 0.09, front, "note_stock_check", turn=-4.0,
                       name="note"))
    parts.append(label(left_door + 0.02, HAB_A_MED_SPLIT * 0.84, 0.16, 0.045, front, "stencil_med_store"))
    return parts


def hygiene_cubicle(size, laid):
    """The hygiene cubicle, as its close-up shows it: a booth of pale vertical panels on corner posts with an open
    top rim, a doorway in its front with a sill and a sliding door standing part open on its track, a keypad unit and
    labels on the fixed panel beside the doorway, a blue stripe round the outside, a copper grab rail and taped notes
    on its side; inside, a mirror over a small shelf, a wash basin with its tap and the trap under it, WATER and WASTE
    labels, the cubicle's label and a lamp on the back wall, and a floor tray."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    wall = 0.025
    door_low, door_high = -0.36, 0.28  # the doorway across the front (the viewer's right of middle)
    sill, lintel = 0.1, 2.0
    front_panel = shapes.box((-wide / 2, 0.0, front), (wide / 2, tall - 0.04, front + wall), "enamel_white", "panel")
    furn_cut_box(front_panel, (door_low, sill, front - 0.05), (door_high, lintel, front + wall + 0.05))
    parts = [shapes.bevelled(front_panel, 0.003)]
    for x in (-wide / 2, wide / 2 - wall):
        parts.append(shapes.bevelled(shapes.box((x, 0.0, front + wall), (x + wall, tall - 0.04, back - wall),
                                                "enamel_white", "panel"), 0.003))
    parts.append(shapes.bevelled(shapes.box((-wide / 2, 0.0, back - wall), (wide / 2, tall - 0.04, back),
                                            "enamel_white", "panel"), 0.003))
    for x in (-wide / 2 - 0.006, wide / 2 - 0.034):
        for z in (front - 0.006, back - 0.034):
            parts.append(shapes.bevelled(shapes.box((x, 0.0, z), (x + 0.04, tall - 0.04, z + 0.04), "enamel_white",
                                                    "post"), 0.006))
    rim = shapes.box((-wide / 2 - 0.006, tall - 0.04, front - 0.006), (wide / 2 + 0.006, tall, back + 0.006),
                     "brushed_steel_fine", "rim")
    furn_cut_box(rim, (-wide / 2 + wall, tall - 0.06, front + wall), (wide / 2 - wall, tall + 0.02, back - wall))
    parts.append(shapes.bevelled(rim, 0.003))
    for z in (front + deep / 3, front + 2 * deep / 3):  # panel seams on the sides' outer faces
        for side_x in (-wide / 2 - 0.004, wide / 2):
            parts.append(shapes.box((side_x, 0.04, z - 0.006), (side_x + 0.004, tall - 0.06, z + 0.006),
                                    "enamel_white", "seam"))
    parts.append(shapes.box((door_low - 0.02, lintel, front - 0.02), (door_high + 0.02, lintel + 0.03, front),
                            "brushed_steel_fine", "track"))
    door = shapes.box((-wide / 2 + 0.06, sill + 0.01, front + wall + 0.004), (door_low + 0.16, lintel - 0.01,
                                                                              front + wall + 0.03),
                      "enamel_white", "door")
    parts.append(shapes.bevelled(door, 0.003))
    parts.append(shapes.cylinder((door_low + 0.12, 1.0, front + wall + 0.004), (door_low + 0.12, 1.22,
                                                                              front + wall + 0.004), 0.008,
                                 "brushed_steel_fine", 12, "handle"))
    parts.append(shapes.box((door_low, 0.0, front - 0.004), (door_high, sill, front + wall), "enamel_white", "sill"))
    inner_back = back - wall
    middle = (door_low + door_high) / 2
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + wall, 0.0, front + wall), (wide / 2 - wall, sill - 0.02,
                                                                                    back - wall), "plastic_grey",
                                            "tray"), 0.004))
    parts.append(shapes.bevelled(shapes.box((middle - 0.17, 1.28, inner_back - 0.01), (middle + 0.17, 1.72,
                                                                                       inner_back), "glass",
                                            "mirror"), 0.004))
    parts.append(shapes.bevelled(shapes.box((middle - 0.2, 1.2, inner_back - 0.1), (middle + 0.2, 1.22, inner_back),
                                            "brushed_steel_fine", "shelf"), 0.002))
    basin = shapes.box((middle - 0.2, 0.72, inner_back - 0.36), (middle + 0.2, 0.86, inner_back), "enamel_white",
                       "sink")
    furn_cut_box(basin, (middle - 0.16, 0.76, inner_back - 0.32), (middle + 0.16, 0.9, inner_back - 0.04))
    parts.append(shapes.bevelled(basin, 0.01))
    parts.append(shapes.cylinder((middle, 0.86, inner_back - 0.03), (middle, 0.97, inner_back - 0.03), 0.012,
                                 "bare_steel", 12, "tap"))
    parts.append(shapes.cylinder((middle, 0.96, inner_back - 0.03), (middle, 0.96, inner_back - 0.14), 0.01,
                                 "bare_steel", 12, "tap"))
    parts.append(shapes.cylinder((middle, 0.72, inner_back - 0.18), (middle, 0.42, inner_back - 0.18), 0.02,
                                 "bare_steel", 14, "trap"))
    parts.append(shapes.cylinder((middle, 0.44, inner_back - 0.18), (middle, 0.44, inner_back), 0.02, "bare_steel", 14,
                                 "trap"))
    parts.append(label(middle + 0.28, 0.98, 0.12, 0.05, inner_back, "label_water"))
    parts.append(label(middle + 0.28, 0.9, 0.12, 0.05, inner_back, "label_waste"))
    parts.append(label(middle - 0.28, 1.62, 0.2, 0.09, inner_back, "label_hygiene"))
    parts.append(label(middle - 0.28, 1.42, 0.1, 0.1, inner_back, "note_clean_daily", turn=3.0, name="note"))
    parts.append(shapes.bevelled(shapes.box((middle - 0.12, 1.9, inner_back - 0.06), (middle + 0.12, 1.98,
                                                                                      inner_back), "bare_steel",
                                            "lamp"), 0.003))
    parts.append(shapes.box((middle - 0.1, 1.9 - 0.004, inner_back - 0.055), (middle + 0.1, 1.9, inner_back - 0.005),
                            "lamp_lens", "lamp_lens"))
    fixed = (door_high + wide / 2) / 2  # the fixed panel's middle, the viewer's left of the doorway
    parts.append(shapes.bevelled(shapes.box((fixed - 0.09, 1.08, front - 0.05), (fixed + 0.09, 1.34, front),
                                            "plastic_white", "keypad_unit"), 0.008))
    parts += wall_screen_part(fixed, 1.285, 0.11, 0.045, front - 0.05, "screen", rim=0.008, name="keypad_screen")
    parts.append(label(fixed, 1.16, 0.12, 0.1, front - 0.05, "keypad_print", name="keypad"))
    parts.append(label(fixed, 1.56, 0.16, 0.08, front, "sheet_log", name="sheet"))
    stripe = (0.93, 1.03)
    for low_x, high_x in ((door_high, wide / 2), (-wide / 2, door_low)):
        parts.append(shapes.box((low_x, stripe[0], front - 0.003), (high_x, stripe[1], front), "enamel_blue",
                                "stripe"))
    for side in (-1, 1):
        x = side * wide / 2
        parts.append(shapes.box((min(x, x + side * 0.003), stripe[0], front), (max(x, x + side * 0.003), stripe[1],
                                                                                back), "enamel_blue", "stripe"))
    parts.append(shapes.box((-wide / 2, stripe[0], back), (wide / 2, stripe[1], back + 0.003), "enamel_blue", "stripe"))
    side = -wide / 2  # the side the close-up shows: its grab rail
    rail_z = (front + back) / 2
    parts.append(shapes.cylinder((side - 0.05, 1.45, rail_z - 0.3), (side - 0.05, 1.45, rail_z + 0.3), 0.016,
                                 "anodized_gold", 16, "grab_rail"))
    for z in (rail_z - 0.3, rail_z + 0.3):
        parts.append(shapes.cylinder((side, 1.45, z), (side - 0.05, 1.45, z), 0.014, "anodized_gold", 14,
                                     "grab_rail"))
    # The taped notes on the fixed panel's clear lower half (a print lies on a face the room sees from in front).
    parts.append(label(fixed - 0.04, 0.74, 0.16, 0.12, front, "note_clean_daily", turn=-3.0, name="note"))
    parts.append(label(fixed + 0.06, 0.56, 0.12, 0.12, front, "note_use_sparingly", turn=4.0, name="note"))
    return parts


# ---- Modules round (2026-10-07), block hab_b: the habitat's galley counter, mess table, stools, exam couch and light
# ring, built in code with library surfaces as method B's parts check allows, each as its clean close-up shows it. A
# holder never carries the loose objects on it: the pot and the kettle on the galley counter, the pillow and the
# blanket on the exam couch are children of their own, placed on purpose (composites). Helpers are prefixed `hab_b_`.

HAB_B_COUNTER_TOP = 0.04  # the galley counter's stainless top
HAB_B_PLINTH = 0.08
# The galley counter's fittings across its width (x of their middles, the kit's +x is the viewer's left): the
# induction plate (where the pot stands) at the viewer's left, the hob in the middle, the sink at the viewer's right.
HAB_B_INDUCTION_X = 0.95
HAB_B_HOB_X = 0.12
HAB_B_SINK_X = -0.72
# The exam couch's raised back: how long it is and how steeply it rises.
HAB_B_COUCH_BACK = 0.55
HAB_B_COUCH_SLOPE = 20.0
HAB_B_COUCH_PAD = 0.09  # the pads' thickness
HAB_B_COUCH_FRAME_TOP = 0.56  # the frame's top, the pads lie on it


def hab_b_spun_ring(middle_y, outer, inner, high, material, name, segments=64):
    """A flat round ring lying level (its axis up), from `middle_y` up by `high`."""
    return shapes.ring((0.0, middle_y, 0.0), (0.0, middle_y + high, 0.0), outer, inner, material, segments, name)


def hab_b_latch(x, y, front, name="latch"):
    """A small drawer latch on a face at depth `front`: a plate and a lever standing out of it."""
    return [shapes.bevelled(shapes.box((x - 0.022, y - 0.03, front - 0.006), (x + 0.022, y + 0.03, front), "bare_steel",
                                       name), 0.0015),
            shapes.bevelled(shapes.box((x - 0.009, y - 0.022, front - 0.022), (x + 0.009, y + 0.012, front - 0.006),
                                       "bare_steel", name), 0.002)]


def hab_b_hinge(x, y, front, name="hinge"):
    """A small butt hinge on a door's edge: a leaf on the face and its knuckle."""
    return [shapes.box((x - 0.012, y - 0.03, front - 0.004), (x + 0.012, y + 0.03, front), "bare_steel", name),
            shapes.cylinder((x, y - 0.032, front - 0.006), (x, y + 0.032, front - 0.006), 0.0055, "bare_steel", 10,
                            name)]


def hab_b_unit(right, left, top, front, back, label_variant):
    """One cabinet unit of the galley counter between x `right` and `left`: its carcass, a drawer across its top with a
    latch and two hinges, two doors under it with bar handles and hinges, and a STORAGE label on one door."""
    face = front + 0.016
    parts = [shapes.bevelled(shapes.box((right, HAB_B_PLINTH, face), (left, top, back), "painted_panel", "carcass"),
                             EDGE)]
    drawer_top = top - 0.02
    drawer_low = top - 0.2
    parts.append(shapes.bevelled(shapes.box((right + 0.015, drawer_low, front), (left - 0.015, drawer_top, face),
                                            "painted_panel", "drawer"), 0.002))
    middle = (right + left) / 2
    parts += hab_b_latch(middle, (drawer_low + drawer_top) / 2 + 0.01, front)
    parts += hab_b_hinge(right + 0.04, drawer_low + 0.03, front)
    parts += hab_b_hinge(left - 0.04, drawer_low + 0.03, front)
    door_top = drawer_low - 0.012
    gap = 0.008
    for door_right, door_left, hinge_x, handle_x in ((middle + gap / 2, left - 0.015, left - 0.03, middle + 0.11),
                                                     (right + 0.015, middle - gap / 2, right + 0.03, middle - 0.11)):
        parts.append(shapes.bevelled(shapes.box((door_right, HAB_B_PLINTH + 0.02, front), (door_left, door_top, face),
                                                "painted_panel", "door"), 0.002))
        parts += furn_pull(handle_x, door_top - 0.1, 0.14, front, upright=False, name="handle")
        for high in (HAB_B_PLINTH + 0.1, door_top - 0.06):
            parts += hab_b_hinge(hinge_x, high, front)
    parts.append(label(middle - 0.2 if middle > 0 else middle + 0.2, door_top - 0.04, 0.16, 0.045, front,
                       label_variant))
    return parts


def galley_counter(size, laid):
    """The galley counter, as its close-up shows it: two steel cabinet units on a dark plinth, each with a latched
    drawer over a pair of doors with bar handles and hinges and a STORAGE label; a stainless top with a splashback in
    two lengths along its back; set into the top, a sink with its tap and drain (viewer's right) and a two-ring
    electric hob (middle) with its label; an induction plate at the viewer's left. Its top is left clear round them for
    the pot and the kettle (children of their own)."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    top = tall
    under_top = top - HAB_B_COUNTER_TOP
    parts = [shapes.box((-wide / 2 + 0.03, 0.0, front + 0.06), (wide / 2 - 0.03, HAB_B_PLINTH, back), "dark_panel",
                        "plinth")]
    joint = 0.004
    parts += hab_b_unit(-wide / 2 + 0.01, -joint / 2, under_top, front + 0.02, back, "label_storage")
    parts += hab_b_unit(joint / 2, wide / 2 - 0.01, under_top, front + 0.02, back, "label_storage")
    worktop = shapes.box((-wide / 2, under_top, front - 0.005), (wide / 2, top, back), "brushed_steel_fine", "top")
    # The sink's basin, cut down through the top and the carcass under it.
    sink_wide, sink_deep, sink_low = 0.56, 0.38, top - 0.13
    sink_z = 0.0
    low = (HAB_B_SINK_X - sink_wide / 2, sink_low, sink_z - sink_deep / 2)
    high = (HAB_B_SINK_X + sink_wide / 2, top + 0.01, sink_z + sink_deep / 2)
    furn_cut_box(worktop, low, high)
    parts.append(shapes.bevelled(worktop, EDGE))
    for part in parts:
        if part.name.split(".")[0] == "carcass":
            furn_cut_box(part, (low[0] - 0.006, low[1] - 0.006, low[2] - 0.006), (high[0] + 0.006, top, high[2] + 0.006))
    basin = shapes.box((low[0] - 0.005, sink_low - 0.005, low[2] - 0.005), (high[0] + 0.005, top - 0.001, high[2] + 0.005),
                       "brushed_steel_fine", "sink")
    furn_cut_box(basin, (low[0], sink_low, low[2]), (high[0], top + 0.01, high[2]))
    parts.append(basin)
    # The basin's rim round it on the top.
    for rim_low, rim_high in (((low[0] - 0.03, low[2] - 0.03), (high[0] + 0.03, low[2])),
                              ((low[0] - 0.03, high[2]), (high[0] + 0.03, high[2] + 0.03)),
                              ((low[0] - 0.03, low[2]), (low[0], high[2])),
                              ((high[0], low[2]), (high[0] + 0.03, high[2]))):
        parts.append(shapes.bevelled(shapes.box((rim_low[0], top, rim_low[1]), (rim_high[0], top + 0.006, rim_high[1]),
                                                "brushed_steel_fine", "sink"), 0.002))
    parts.append(shapes.cylinder((HAB_B_SINK_X + 0.08, sink_low - 0.002, 0.11), (HAB_B_SINK_X + 0.08, sink_low + 0.006,
                                                                                 0.11), 0.032, "bare_steel", 20, "drain"))
    # The tap behind the basin: a pillar, a swan neck over the basin, and two lever handles.
    tap_x, tap_z = HAB_B_SINK_X, high[2] + 0.06
    parts.append(shapes.cylinder((tap_x, top, tap_z), (tap_x, top + 0.2, tap_z), 0.012, "bare_steel", 16, "tap"))
    parts.append(floor_bent_tube((tap_x, top + 0.2, tap_z - 0.06), (0, 0, 1), (0, 1, 0), 0.06, 0.011, 0.0, 180.0,
                                 "bare_steel", "tap", steps=12, sides=12))
    parts.append(shapes.cylinder((tap_x, top + 0.2, tap_z - 0.12), (tap_x, top + 0.16, tap_z - 0.12), 0.011,
                                 "bare_steel", 12, "tap"))
    for side in (-1, 1):
        parts.append(shapes.cylinder((tap_x + side * 0.07, top, tap_z), (tap_x + side * 0.07, top + 0.05, tap_z), 0.012,
                                     "bare_steel", 12, "tap_handle"))
        parts.append(shapes.box((tap_x + side * 0.07 - 0.006, top + 0.045, tap_z - 0.06),
                                (tap_x + side * 0.07 + 0.006, top + 0.055, tap_z), "bare_steel", "tap_handle"))
    parts.append(label(HAB_B_SINK_X + 0.15, top - HAB_B_COUNTER_TOP / 2, 0.12, 0.03, front - 0.005, "label_sink"))
    # The hob: a plate standing proud of the top with two rings, each a coil of three red loops round a hub.
    hob_wide, hob_deep = 0.46, 0.36
    parts.append(shapes.bevelled(shapes.box((HAB_B_HOB_X - hob_wide / 2, top, -hob_deep / 2 + 0.02),
                                            (HAB_B_HOB_X + hob_wide / 2, top + 0.012, hob_deep / 2 + 0.02),
                                            "brushed_steel_fine", "hob"), 0.002))
    for ring_x, ring_z in ((HAB_B_HOB_X + 0.11, -0.05), (HAB_B_HOB_X - 0.11, 0.09)):
        parts.append(shapes.cylinder((ring_x, top + 0.012, ring_z), (ring_x, top + 0.016, ring_z), 0.1, "dark_panel",
                                     40, "burner"))
        for outer in (0.092, 0.068, 0.044):
            parts.append(shapes.ring((ring_x, top + 0.016, ring_z), (ring_x, top + 0.024, ring_z), outer, outer - 0.012,
                                     "anodized_red", 40, "burner"))
        parts.append(shapes.cylinder((ring_x, top + 0.016, ring_z), (ring_x, top + 0.024, ring_z), 0.014, "bare_steel",
                                     16, "burner"))
    parts.append(label(HAB_B_HOB_X - 0.05, top - HAB_B_COUNTER_TOP / 2, 0.24, 0.03, front - 0.005, "label_electric_hob"))
    # The induction plate: a dark glass slab lying on the top, the pot's spot, its touch keys printed on.
    plate_low = (HAB_B_INDUCTION_X - 0.17, top, -0.17)
    plate_high = (HAB_B_INDUCTION_X + 0.17, top + 0.012, 0.11)
    parts.append(shapes.bevelled(shapes.box(plate_low, plate_high, "anodized_black", "induction_plate"), 0.002))
    # The splashback along the back, in two lengths as the close-up shows it (a step where they meet).
    parts.append(shapes.bevelled(shapes.box((-wide / 2, top, back - 0.02), (0.55, top + 0.26, back), "brushed_steel_fine",
                                            "splashback"), 0.002))
    parts.append(shapes.bevelled(shapes.box((0.57, top, back - 0.02), (wide / 2, top + 0.2, back), "brushed_steel_fine",
                                            "splashback"), 0.002))
    return parts


def mess_table(size, laid):
    """The mess table, as its close-up shows it: a stainless top with a turned-down edge all round, four round legs
    with rubber feet, and its labels (MESS TABLE, CLEAN AFTER USE, BASE PROPERTY) on the edge's front."""
    wide, tall, deep = size
    top_thick, edge = 0.025, 0.06
    parts = [shapes.bevelled(shapes.box((-wide / 2, tall - top_thick, -deep / 2), (wide / 2, tall, deep / 2),
                                        "brushed_steel_fine", "top"), 0.006)]
    for low, high in (((-wide / 2, -deep / 2), (wide / 2, -deep / 2 + 0.012)),
                      ((-wide / 2, deep / 2 - 0.012), (wide / 2, deep / 2)),
                      ((-wide / 2, -deep / 2 + 0.012), (-wide / 2 + 0.012, deep / 2 - 0.012)),
                      ((wide / 2 - 0.012, -deep / 2 + 0.012), (wide / 2, deep / 2 - 0.012))):
        parts.append(shapes.bevelled(shapes.box((low[0], tall - edge, low[1]), (high[0], tall - top_thick, high[1]),
                                                "brushed_steel_fine", "edge"), 0.003))
    for x in (-wide / 2 + 0.14, wide / 2 - 0.14):
        for z in (-deep / 2 + 0.1, deep / 2 - 0.1):
            parts.append(shapes.cylinder((x, 0.025, z), (x, tall - edge, z), 0.025, "brushed_steel_fine", 24, "leg"))
            parts.append(shapes.cylinder((x, 0.0, z), (x, 0.025, z), 0.029, "rubber", 24, "foot"))
    front = -deep / 2
    middle = tall - (edge + top_thick) / 2
    parts.append(label(wide / 2 - 0.3, middle, 0.26, 0.026, front, "label_mess_table"))
    parts.append(label(0.0, middle, 0.3, 0.026, front, "label_clean_after_use"))
    parts.append(label(-wide / 2 + 0.3, middle, 0.3, 0.026, front, "label_base_property"))
    return parts


def stool(size, laid):
    """A mess stool, as its close-up shows it: a round padded cushion in a steel seat pan, a column down to a spun
    base with a collar where they meet, and a foot ring held by three stays from the column."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2
    pan_low = tall - 0.07
    parts = [shapes.bevelled(shapes.cylinder((0.0, pan_low, 0.0), (0.0, tall - 0.02, 0.0), radius * 0.86, "bare_steel",
                                             48, "seat_pan"), 0.006),
             shapes.bevelled(shapes.cylinder((0.0, tall - 0.03, 0.0), (0.0, tall, 0.0), radius * 0.8, "vinyl_seat", 48,
                                             "cushion"), 0.012)]
    parts.append(shapes.cylinder((0.0, 0.03, 0.0), (0.0, pan_low, 0.0), 0.028, "bare_steel", 24, "column"))
    base = furn_prism([(radius * math.cos(2 * math.pi * at / 48), radius * math.sin(2 * math.pi * at / 48))
                       for at in range(48)], "y", 0.0, 0.012, "bare_steel", "base")
    parts.append(shapes.bevelled(base, 0.003))
    # The spun cone from the base plate up to the column.
    cone = bmesh.new()
    bmesh.ops.create_cone(cone, cap_ends=True, cap_tris=False, segments=48, radius1=radius * 0.9, radius2=0.05,
                          depth=0.05)
    bmesh.ops.translate(cone, verts=cone.verts, vec=Vector((0.0, 0.0, 0.012 + 0.025)))
    data = bpy.data.meshes.new("base")
    cone.to_mesh(data)
    cone.free()
    parts.append(shapes.mesh_object("base", data, "bare_steel"))
    parts.append(shapes.cylinder((0.0, 0.06, 0.0), (0.0, 0.085, 0.0), 0.045, "bare_steel", 24, "collar"))
    ring_high = 0.17
    ring_radius = radius * 0.7
    parts.append(floor_bent_tube((0.0, ring_high, 0.0), (1, 0, 0), (0, 0, 1), ring_radius, 0.011, 0.0, 360.0,
                                 "bare_steel", "foot_ring", steps=40, sides=12))
    for at in range(3):
        angle = math.radians(90 + 120 * at)
        parts.append(shapes.cylinder((0.028 * math.cos(angle), ring_high, -0.028 * math.sin(angle)),
                                     ((ring_radius - 0.008) * math.cos(angle), ring_high,
                                      -(ring_radius - 0.008) * math.sin(angle)), 0.008, "bare_steel", 10, "stay"))
    return parts


def exam_couch(size, laid):
    """The medical exam couch, as its close-up shows it: a square-tube steel frame with a side rail all round on four
    legs with feet and stretchers between them, a padded vinyl seat pad and a back pad raised on struts at the viewer's
    right, and its labels (MEDICAL EXAM COUCH, CLEAN AFTER USE) on the front rail. The pillow and the blanket on it
    are children of their own."""
    wide, tall, deep = size
    rail_high = 0.08
    frame_top = HAB_B_COUCH_FRAME_TOP
    half_wide, half_deep = wide / 2, deep / 2 - 0.03
    parts = []
    for low, high in (((-half_wide, -half_deep), (half_wide, -half_deep + 0.03)),
                      ((-half_wide, half_deep - 0.03), (half_wide, half_deep)),
                      ((-half_wide, -half_deep + 0.03), (-half_wide + 0.03, half_deep - 0.03)),
                      ((half_wide - 0.03, -half_deep + 0.03), (half_wide, half_deep - 0.03))):
        parts.append(shapes.bevelled(shapes.box((low[0], frame_top - rail_high, low[1]), (high[0], frame_top, high[1]),
                                                "painted_panel", "frame"), 0.003))
    leg_x, leg_z = half_wide - 0.1, half_deep - 0.05
    for x in (-leg_x, leg_x):
        for z in (-leg_z, leg_z):
            parts.append(shapes.bevelled(shapes.box((x - 0.02, 0.02, z - 0.02), (x + 0.02, frame_top - rail_high, z + 0.02),
                                                    "galvanized_steel", "leg"), 0.002))
            parts.append(shapes.box((x - 0.022, 0.0, z - 0.022), (x + 0.022, 0.02, z + 0.022), "rubber", "foot"))
        parts.append(shapes.bevelled(shapes.box((x - 0.015, 0.16, -leg_z + 0.02), (x + 0.015, 0.19, leg_z - 0.02),
                                                "galvanized_steel", "stretcher"), 0.002))
    parts.append(shapes.bevelled(shapes.box((-leg_x + 0.02, 0.16, leg_z - 0.015), (leg_x - 0.02, 0.19, leg_z + 0.015),
                                            "galvanized_steel", "stretcher"), 0.002))
    # The seat pad, from the viewer's left end to the back pad's hinge.
    hinge_x = -half_wide + HAB_B_COUCH_BACK
    parts.append(shapes.bevelled(shapes.box((hinge_x + 0.01, frame_top, -half_deep + 0.01),
                                            (half_wide - 0.01, frame_top + HAB_B_COUCH_PAD, half_deep - 0.01),
                                            "vinyl_cabin", "pad"), 0.02))
    # The back pad raised about the hinge, on two struts from the frame.
    back = shapes.bevelled(shapes.box((-half_wide + 0.01, frame_top, -half_deep + 0.01),
                                      (hinge_x, frame_top + HAB_B_COUCH_PAD, half_deep - 0.01), "vinyl_cabin",
                                      "back_pad"), 0.02)
    pivot = shapes.to_blender((hinge_x, frame_top, 0.0))
    back.data.transform(Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(HAB_B_COUCH_SLOPE), 4, "Y")
                        @ Matrix.Translation(-pivot))
    parts.append(back)
    lift = HAB_B_COUCH_BACK * 0.75 * math.sin(math.radians(HAB_B_COUCH_SLOPE))
    for z in (-half_deep + 0.08, half_deep - 0.08):
        parts.append(shapes.cylinder((-half_wide + 0.13, frame_top - 0.02, z), (-half_wide + 0.13, frame_top + lift - 0.01,
                                                                                 z), 0.009, "galvanized_steel", 12,
                                     "back_strut"))
    front = -half_deep
    middle = frame_top - rail_high / 2
    parts.append(label(0.2, middle, 0.4, 0.05, front, "label_exam_couch"))
    parts.append(label(-0.45, middle, 0.26, 0.05, front, "label_clean_after_use"))
    return parts


def light_ring(size, laid):
    """The ring light over the mess table, as its close-up shows it: a heavy steel ring with a raised bead round its
    outside and bolt heads along it, a ring of lamps under it (a socket and a glowing lens each), and four hanging rods
    from shackles on the ring up to a canopy plate under the roof (the laid box's top)."""
    wide, tall, deep = size
    outer = min(wide, deep) / 2
    inner = outer - 0.12
    ring_high = 0.09
    parts = [shapes.bevelled(hab_b_spun_ring(0.03, outer, inner, ring_high, "dark_panel", "ring", 96), 0.004)]
    parts.append(hab_b_spun_ring(0.03 + ring_high * 0.35, outer + 0.008, outer - 0.01, 0.02, "dark_panel", "bead", 96))
    for at in range(24):
        angle = 2 * math.pi * (at + 0.5) / 24
        out = Vector((math.cos(angle), 0.0, math.sin(angle)))
        middle = Vector((0.0, 0.03 + ring_high * 0.75, 0.0)) + out * outer
        parts.append(shapes.cylinder(tuple(middle), tuple(middle + out * 0.008), 0.009, "bare_steel", 10, "bolt"))
    middle_radius = (outer + inner) / 2
    for at in range(14):
        angle = 2 * math.pi * at / 14
        x, z = middle_radius * math.cos(angle), middle_radius * math.sin(angle)
        parts.append(shapes.cylinder((x, 0.022, z), (x, 0.03, z), 0.042, "bare_steel", 24, "socket"))
        dome = bmesh.new()
        bmesh.ops.create_uvsphere(dome, u_segments=16, v_segments=8, radius=0.04)
        bmesh.ops.delete(dome, geom=[vertex for vertex in dome.verts if vertex.co.z > 0.0001], context="VERTS")
        bmesh.ops.contextual_create(dome, geom=[edge for edge in dome.edges if edge.is_boundary])
        bmesh.ops.translate(dome, verts=dome.verts, vec=shapes.to_blender((x, 0.03, z)))
        data = bpy.data.meshes.new("lens")
        dome.to_mesh(data)
        dome.free()
        parts.append(shapes.mesh_object("lens", data, "lamp_lens"))
    canopy_y = tall - 0.03
    parts.append(shapes.bevelled(shapes.cylinder((0.0, canopy_y, 0.0), (0.0, tall, 0.0), 0.16, "dark_panel", 32,
                                                 "canopy"), 0.004))
    for at in range(4):
        angle = 2 * math.pi * at / 4 + math.pi / 4
        out = Vector((math.cos(angle), 0.0, math.sin(angle)))
        # The shackle: a clevis plate bolted on the ring's outside, standing over its top, the rod's eye through it.
        foot = Vector((0.0, 0.03 + ring_high * 0.4, 0.0)) + out * (outer + 0.012)
        side = Vector((-out.z, 0.0, out.x))
        corners = [foot + side * 0.022 + out * 0.012, foot - side * 0.022 + out * 0.012,
                   foot - side * 0.022 - out * 0.012, foot + side * 0.022 - out * 0.012]
        plate = bmesh.new()
        low = [plate.verts.new(shapes.to_blender(corner)) for corner in corners]
        high = [plate.verts.new(shapes.to_blender(corner + Vector((0.0, ring_high * 0.6 + 0.05, 0.0)))) for corner in corners]
        plate.faces.new(low)
        plate.faces.new(list(reversed(high)))
        for at in range(4):
            plate.faces.new([low[at], high[at], high[(at + 1) % 4], low[(at + 1) % 4]])
        bmesh.ops.recalc_face_normals(plate, faces=plate.faces)
        data = bpy.data.meshes.new("shackle")
        plate.to_mesh(data)
        plate.free()
        parts.append(shapes.mesh_object("shackle", data, "bare_steel"))
        eye = foot + Vector((0.0, ring_high * 0.6 + 0.035, 0.0))
        parts.append(shapes.cylinder(tuple(eye - side * 0.03), tuple(eye + side * 0.03), 0.009, "bare_steel", 12,
                                     "shackle"))
        head = Vector((0.0, canopy_y, 0.0)) + out * 0.12
        parts.append(shapes.cylinder(tuple(eye), tuple(head), 0.006, "cast_iron_dark", 10, "rod"))
    return parts


def pot(size, laid):
    """A steel cooking pot, as its close-up shows it: a straight-sided body with a floor, its rolled rim, and two
    loop handles on riveted plates either side."""
    wide, tall, deep = size
    radius = min(deep, wide - 0.08) / 2
    body = shapes.cylinder((0.0, 0.0, 0.0), (0.0, tall - 0.008, 0.0), radius, "brushed_steel_fine", 40, "body")
    shapes.cut(body, shapes.cylinder((0.0, 0.006, 0.0), (0.0, tall + 0.05, 0.0), radius - 0.005, "brushed_steel_fine",
                                     40, "cutter"))
    parts = [body,
             shapes.bevelled(shapes.ring((0.0, tall - 0.012, 0.0), (0.0, tall, 0.0), radius + 0.006, radius - 0.004,
                                         "brushed_steel_fine", 40, "rim"), 0.002)]
    for side in (-1, 1):
        x = side * radius
        parts.append(shapes.box((x - 0.006 if side < 0 else x - 0.002, tall * 0.62, -0.03),
                                (x + 0.002 if side < 0 else x + 0.006, tall * 0.82, 0.03), "bare_steel", "handle_plate"))
        parts.append(floor_bent_tube((x + side * 0.004, tall * 0.72, 0.0), (0, 0, 1), (side, 0, 0), 0.028, 0.004, 0.0,
                                     180.0, "bare_steel", "handle", steps=10, sides=8))
    return parts


def couch_pillow(size, laid):
    """The exam couch's pillow, as its close-up shows it: a flat pale vinyl pillow with a welted seam round its edge,
    lying on the couch's raised back pad (tilted as the pad is, its foot the pad's face)."""
    wide, tall, deep = size
    thick = 0.07
    run = (wide - 0.02) / math.cos(math.radians(HAB_B_COUCH_SLOPE))
    pillow = shapes.bevelled(shapes.box((-run / 2, 0.0, -deep / 2 + 0.01), (run / 2, thick, deep / 2 - 0.01),
                                        "vinyl_cabin", "pillow"), 0.025)
    seam = shapes.bevelled(shapes.box((-run / 2 - 0.006, thick / 2 - 0.006, -deep / 2 + 0.004),
                                      (run / 2 + 0.006, thick / 2 + 0.006, deep / 2 - 0.004), "vinyl_cabin", "seam"),
                           0.004)
    parts = [pillow, seam]
    # Lying on the raised back: its high end at the viewer's right (-x), as the couch's back rises.
    pivot = shapes.to_blender((0.0, 0.0, 0.0))
    for part in parts:
        part.data.transform(Matrix.Translation(pivot) @ Matrix.Rotation(math.radians(HAB_B_COUCH_SLOPE), 4, "Y")
                            @ Matrix.Translation(-pivot))
    low = min(vertex.co.z for part in parts for vertex in part.data.vertices)
    for part in parts:
        part.data.transform(Matrix.Translation(Vector((0.0, 0.0, -low))))
    return parts


# ---- Modules round (2026-10-07): the airlock's and the walkway tube's fittings and furniture, built in code with
# library surfaces as method B's parts check allows, each with every part its clean close-up shows
# (data/library/fittings.json). The suit-up alcove's hose reel is a child of its own (one model per real-world object);
# the dust vacuum goes to the prop pipeline. Helpers are prefixed `lock_tube_`.

LOCK_TUBE_STRIPE = 0.12  # a hazard stripe's width, measured along the frame's diagonal (x + y)


def lock_tube_area(polygon):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(polygon, polygon[1:] + polygon[:1])) / 2


def lock_tube_ccw(polygon):
    """A polygon's (x, y) points counter-clockwise."""
    return list(polygon) if lock_tube_area(polygon) >= 0 else list(reversed(polygon))


def lock_tube_clip(polygon, clipper):
    """A convex polygon clipped to a convex clipper (Sutherland-Hodgman), both as (x, y) lists; empty when they do not
    meet."""
    found = lock_tube_ccw(polygon)
    clipper = lock_tube_ccw(clipper)
    for (ax, ay), (bx, by) in zip(clipper, clipper[1:] + clipper[:1]):
        def inside(point):
            return (bx - ax) * (point[1] - ay) - (by - ay) * (point[0] - ax) >= -1e-9

        def crossing(p, q):
            dx, dy = q[0] - p[0], q[1] - p[1]
            ex, ey = bx - ax, by - ay
            share = (ex * (p[1] - ay) - ey * (p[0] - ax)) / (ey * dx - ex * dy)
            return (p[0] + dx * share, p[1] + dy * share)
        before, found = found, []
        for at, point in enumerate(before):
            previous = before[at - 1]
            if inside(point):
                if not inside(previous):
                    found.append(crossing(previous, point))
                found.append(point)
            elif inside(previous):
                found.append(crossing(previous, point))
        if len(found) < 3:
            return []
    return found if abs(lock_tube_area(found)) > 1e-5 else []


def lock_tube_chamfered(low, high, top_cut, bottom_cut):
    """A rectangle's outline (x, y) with its top corners cut `top_cut` and its bottom ones `bottom_cut` at 45 degrees,
    counter-clockwise."""
    (left, bottom), (right, top) = low, high
    found = []
    for x, y, cut, along in ((right, bottom, bottom_cut, "up"), (right, top, top_cut, "left"),
                             (left, top, top_cut, "down"), (left, bottom, bottom_cut, "right")):
        if cut <= 0:
            found.append((x, y))
            continue
        if along == "up":
            found += [(x - cut, y), (x, y + cut)]
        elif along == "left":
            found += [(x, y - cut), (x - cut, y)]
        elif along == "down":
            found += [(x + cut, y), (x, y - cut)]
        else:
            found += [(x, y + cut), (x + cut, y)]
    return lock_tube_ccw(found)


def lock_tube_bar(start, end, half):
    """A flat bar's outline from one (x, y) point to another, `half` its width either side."""
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length * half, dx / length * half
    return lock_tube_ccw([(start[0] + nx, start[1] + ny), (end[0] + nx, end[1] + ny), (end[0] - nx, end[1] - ny),
                          (start[0] - nx, start[1] - ny)])


def lock_tube_ring(outer, inner, depth_from, depth_to, material, name):
    """A flat ring of any outline: the outer outline solid between two depths with the inner one cut through."""
    ring = shapes.prism(outer, depth_from, depth_to, material, name)
    shapes.cut(ring, shapes.prism(inner, depth_from - 0.05, depth_to + 0.05, material, "cutter"))
    return ring


def lock_tube_stripes(band, surface, thick=0.004):
    """Black hazard stripes over a yellow band (a convex (x, y) outline) standing on a face at depth `surface`: the
    band's yellow plate, and diagonal black stripes clipped to it, one stripe width apart."""
    parts = [shapes.prism(band, surface - thick, surface + 0.002, "hazard_paint", "stripe")]
    sums = [x + y for x, y in band]
    start = math.floor(min(sums) / (2 * LOCK_TUBE_STRIPE)) * 2 * LOCK_TUBE_STRIPE
    reach = 4.0
    at = start
    while at < max(sums):
        def point(along, across):
            return (along / 2 + across, along / 2 - across)
        stripe = [point(at, -reach), point(at, reach), point(at + LOCK_TUBE_STRIPE, reach),
                  point(at + LOCK_TUBE_STRIPE, -reach)]
        clipped = lock_tube_clip(stripe, band)
        if clipped:
            parts.append(shapes.prism(clipped, surface - thick - 0.004, surface - thick, "anodized_black",
                                      "stripe"))
        at += 2 * LOCK_TUBE_STRIPE
    return parts


def door_frame(size, laid):
    """The airlock's heavy door frame, as its close-up shows it: a bolted back flange, the frame round the doorway
    with its outer corners cut, a stepped lip round the opening and a band of black-and-yellow hazard stripes on the
    frame's face; the opening is exactly the shell's doorway (the door leaf, the game's own moving node, sinks into
    the floor in it)."""
    wide, tall, deep = size
    half, top = DOORWAY[0] / 2, DOORWAY[1]
    front, back = -deep / 2, deep / 2
    opening = [(half, 0.0), (half, top), (-half, top), (-half, 0.0)]
    flange_outline = lock_tube_chamfered((-wide / 2, 0.0), (wide / 2, tall), 0.22, 0.08)
    frame_outline = lock_tube_chamfered((-wide / 2 + 0.045, 0.0), (wide / 2 - 0.045, tall - 0.045), 0.19, 0.06)
    door_hole = [(half + 0.001, -0.01), (half + 0.001, top + 0.001), (-half - 0.001, top + 0.001),
                 (-half - 0.001, -0.01)]
    parts = [shapes.bevelled(lock_tube_ring(flange_outline, door_hole, back - 0.03, back, "dark_panel", "flange"),
                             0.004)]
    frame_face = front + 0.04
    parts.append(shapes.bevelled(lock_tube_ring(frame_outline, door_hole, frame_face, back - 0.03, "painted_panel",
                                                "frame"), 0.006))
    lip = 0.05
    lip_outline = [(half + lip, 0.0), (half + lip, top + lip), (-half - lip, top + lip), (-half - lip, 0.0)]
    parts.append(shapes.bevelled(lock_tube_ring(lip_outline, door_hole, front, frame_face, "bare_steel", "lip"),
                                 0.004))
    # The stripe band on the frame's face: down each post and across the header, inside the cut outer corners.
    margin = 0.02
    outer = lock_tube_chamfered((-wide / 2 + 0.045 + margin, margin), (wide / 2 - 0.045 - margin,
                                                                       tall - 0.045 - margin), 0.19 - margin * 0.6,
                                0.06 - margin * 0.6)
    inner_x, inner_top = half + lip + 0.012, top + lip + 0.012
    bands = [[(inner_x, 0.0), (wide, 0.0), (wide, inner_top), (inner_x, inner_top)],
             [(-wide, 0.0), (-inner_x, 0.0), (-inner_x, inner_top), (-wide, inner_top)],
             [(-wide, inner_top), (wide, inner_top), (wide, tall), (-wide, tall)]]
    for band in bands:
        clipped = lock_tube_clip(band, outer)
        if clipped:
            parts += lock_tube_stripes(clipped, frame_face)
    # Bolts round the flange's exposed rim.
    rim = (wide / 2 - 0.0225)
    for y in np.linspace(0.15, tall - 0.3, 8):
        parts += [bolt(side * rim, float(y), back - 0.03) for side in (-1, 1)]
    for x in np.linspace(-wide / 2 + 0.35, wide / 2 - 0.35, 6):
        parts.append(bolt(float(x), tall - 0.0225, back - 0.03))
    return parts


def door_leaf(size, laid):
    """The airlock's door leaf (the game's InnerDoor and OuterDoor draw it; it sinks into the floor), as its
    close-up shows it: a thick slab with its top corners cut, a raised rim round its face, eight raised ribs from a
    bolted ring at its middle out to the rim with recessed panels between them, a lock hub in the ring, two latch arms
    on its side and an AIRLOCK sticker."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    outline = lock_tube_chamfered((-wide / 2, 0.0), (wide / 2, tall), 0.3, 0.0)
    face = front + 0.035
    parts = [shapes.bevelled(shapes.prism(outline, face, back, "painted_panel", "slab"), 0.008)]
    rim_width = 0.1
    inner = lock_tube_chamfered((-wide / 2 + rim_width, rim_width), (wide / 2 - rim_width, tall - rim_width),
                                0.3 - rim_width * 0.6, 0.0)
    parts.append(shapes.bevelled(lock_tube_ring(outline, inner, front + 0.005, face + 0.005, "painted_panel", "rim"),
                                 0.005))
    middle = (0.0, tall / 2)
    ring_outer, ring_inner = 0.24, 0.16
    for angle in range(0, 360, 45):
        reach = 3.0
        end = (middle[0] + reach * math.cos(math.radians(angle)), middle[1] + reach * math.sin(math.radians(angle)))
        start = (middle[0] + ring_outer * 0.9 * math.cos(math.radians(angle)),
                 middle[1] + ring_outer * 0.9 * math.sin(math.radians(angle)))
        bar = lock_tube_clip(lock_tube_bar(start, end, 0.045), inner)
        if bar:
            parts.append(shapes.bevelled(shapes.prism(bar, front + 0.012, face + 0.005, "painted_panel", "rib"),
                                         0.004))
    parts.append(shapes.bevelled(shapes.ring((*middle, front - 0.005), (*middle, face + 0.005), ring_outer,
                                             ring_inner, "bare_steel", 48, "hub_ring"), 0.004))
    for at in range(8):
        angle = 2 * math.pi * (at + 0.5) / 8
        parts.append(bolt(middle[0] + 0.2 * math.cos(angle), middle[1] + 0.2 * math.sin(angle), front - 0.005))
    hub = shapes.cylinder((*middle, front + 0.01), (*middle, face + 0.005), ring_inner + 0.002, "cast_steel", 40,
                          "hub")
    parts.append(shapes.bevelled(hub, 0.003))
    parts.append(shapes.bevelled(shapes.box((-0.025, middle[1] - 0.12, front - 0.005), (0.025, middle[1] + 0.12,
                                                                                       front + 0.01), "cast_steel",
                                            "lock_bar"), 0.003))
    # Two latch arms on the viewer's right (the kit's -x): a bolted plate on the leaf and an arm out to its edge.
    for y in (middle[1] + 0.3, middle[1] - 0.3):
        plate = shapes.box((-wide / 2 + 0.2, y - 0.05, front - 0.002), (-wide / 2 + 0.52, y + 0.05, face + 0.002),
                           "bare_steel", "latch")
        parts.append(shapes.bevelled(plate, 0.003))
        parts.append(shapes.bevelled(shapes.box((-wide / 2 + 0.04, y - 0.025, front - 0.03),
                                                (-wide / 2 + 0.24, y + 0.025, front - 0.002), "bare_steel", "latch"),
                                     0.003))
        parts += [bolt(x, y + dy, front - 0.002) for x in (-wide / 2 + 0.26, -wide / 2 + 0.46) for dy in (-0.028, 0.028)]
    parts.append(label(0.72, 1.05, 0.3, 0.18, face, "label_airlock_leaf", name="sticker"))
    return parts


def suit_alcove(size, laid):
    """The suit-up alcove the suit hangs in (the game's SuitLocker stands in it with the suit), as its close-up shows
    it: an open-fronted steel carcass with its top corners cut and a raised frame round its mouth, a three-cushion
    back pad, a grab rail on each side wall, a strip lamp under its top, a deck plate and a foot rail on its floor, and
    a hook on its top; its hose reel is a child of its own beside it."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    outline = lock_tube_chamfered((-wide / 2, 0.0), (wide / 2, tall), 0.2, 0.0)
    carcass = shapes.prism(outline, front + 0.03, back, "painted_panel", "carcass")
    side, roof, floor_high, back_wall = 0.07, 0.14, 0.08, 0.04
    mouth = lock_tube_chamfered((-wide / 2 + side, floor_high), (wide / 2 - side, tall - roof), 0.14, 0.0)
    shapes.cut(carcass, shapes.prism(mouth, front - 0.05, back - back_wall, "painted_panel", "cutter"))
    parts = [shapes.bevelled(carcass, 0.006)]
    parts.append(shapes.bevelled(lock_tube_ring(outline, mouth, front, front + 0.03, "bare_steel", "frame"), 0.004))
    pad_back = back - back_wall
    for at in range(3):
        bottom = 0.85 + at * 0.36
        parts.append(shapes.bevelled(shapes.box((-0.28, bottom, pad_back - 0.07), (0.28, bottom + 0.34, pad_back),
                                                "quilted_grey", "pad"), 0.02))
    for x in (-wide / 2 + side, wide / 2 - side):
        inward = 0.035 if x < 0 else -0.035
        rail_x = x + inward
        parts.append(shapes.cylinder((rail_x, 0.75, front + 0.14), (rail_x, 1.75, front + 0.14), 0.014, "anodized_gold",
                                     16, "rail"))
        for y in (0.75, 1.75):
            parts.append(shapes.cylinder((x, y, front + 0.14), (rail_x, y, front + 0.14), 0.012, "anodized_gold", 12,
                                         "rail"))
    lamp_y = tall - roof
    parts.append(shapes.bevelled(shapes.box((-0.3, lamp_y - 0.05, front + 0.06), (0.3, lamp_y, front + 0.16),
                                            "bare_steel", "lamp_housing"), 0.003))
    parts.append(shapes.content_plate((-0.27, lamp_y - 0.056, front + 0.075), (0.27, lamp_y - 0.05, front + 0.145),
                                      "lamp_strip", "lens"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + side, floor_high, front + 0.05),
                                            (wide / 2 - side, floor_high + 0.012, pad_back), "chequer_plate_steel",
                                            "floor"), 0.002))
    parts.append(shapes.cylinder((-wide / 2 + side, floor_high + 0.06, front + 0.1),
                                 (wide / 2 - side, floor_high + 0.06, front + 0.1), 0.014, "bare_steel", 16,
                                 "foot_rail"))
    for x in (-wide / 2 + side + 0.03, wide / 2 - side - 0.03):
        parts.append(shapes.box((x - 0.015, floor_high, front + 0.08), (x + 0.015, floor_high + 0.06, front + 0.12),
                                "bare_steel", "foot_rail"))
    parts.append(shapes.bevelled(shapes.box((-0.03, tall, -0.03), (0.03, tall + 0.012, 0.03), "bare_steel", "hook"),
                                 0.002))
    parts.append(shapes.cylinder((0.0, tall + 0.012, 0.0), (0.0, tall + 0.09, 0.0), 0.009, "bare_steel", 12, "hook"))
    parts.append(shapes.cylinder((0.0, tall + 0.09, 0.0), (0.0, tall + 0.09, -0.06), 0.009, "bare_steel", 12, "hook"))
    parts.append(shapes.cylinder((0.0, tall + 0.09, -0.06), (0.0, tall + 0.055, -0.06), 0.009, "bare_steel", 12, "hook"))
    return parts


def hose_reel(size, laid):
    """A wall hose reel, as its close-up shows it: the air hose wound on a drum between two round flanges on an
    axle, a hub nut and a crank on one flange, two arms out from a wall bracket to the axle's ends, and the hose's end
    hanging down with its fitting."""
    wide, tall, deep = size
    back = deep / 2
    radius = min(tall / 2 - 0.02, deep / 2 - 0.02)
    axis_y, axis_z = tall - radius - 0.01, 0.0
    flange_x = wide / 2 - 0.065
    arm_x = wide / 2 - 0.03
    parts = []
    for side in (-1, 1):
        x = side * flange_x
        parts.append(shapes.bevelled(shapes.cylinder((x - 0.005, axis_y, axis_z), (x + 0.005, axis_y, axis_z), radius,
                                                     "dark_panel", 40, "flange"), 0.002))
    turns = 7
    pitch = (2 * flange_x - 0.012) / turns
    for at in range(turns):
        x0 = -flange_x + 0.006 + pitch * at
        parts.append(shapes.bevelled(shapes.ring((x0 + 0.001, axis_y, axis_z), (x0 + pitch - 0.001, axis_y, axis_z),
                                                 radius * 0.72, radius * 0.4, "rubber", 32, "hose"), 0.004))
    hose_x = flange_x - 0.04
    parts.append(shapes.cylinder((hose_x, axis_y - radius * 0.66, axis_z - 0.03), (hose_x, 0.07, axis_z - 0.06),
                                 0.011, "rubber", 12, "hose"))
    parts.append(shapes.cylinder((hose_x, 0.07, axis_z - 0.06), (hose_x, 0.0, axis_z - 0.06), 0.014, "bare_steel", 6,
                                 "nozzle"))
    parts.append(shapes.cylinder((-arm_x, axis_y, axis_z), (arm_x, axis_y, axis_z), 0.02,
                                 "bare_steel", 16, "axle"))
    for side in (-1, 1):
        x = side * arm_x
        parts.append(shapes.cylinder((x + side * 0.01, axis_y, axis_z), (x + side * 0.025, axis_y, axis_z), 0.026,
                                     "bare_steel", 6,
                                     "hub"))
        parts.append(shapes.bevelled(shapes.box((x - 0.01, axis_y - 0.02, axis_z), (x + 0.01, axis_y + 0.02,
                                                                                     back - 0.012), "dark_panel",
                                                "arm"), 0.002))
        parts.append(shapes.bevelled(shapes.box((x - 0.035, axis_y - 0.09, back - 0.012), (x + 0.035, axis_y + 0.09,
                                                                                            back), "dark_panel",
                                                "bracket"), 0.002))
    crank_x = flange_x + 0.012
    parts.append(shapes.bevelled(shapes.box((crank_x, axis_y - 0.012, axis_z - radius * 0.8),
                                            (crank_x + 0.012, axis_y + 0.012, axis_z - 0.02), "bare_steel", "crank"),
                                 0.002))
    parts.append(shapes.cylinder((crank_x + 0.012, axis_y, axis_z - radius * 0.75),
                                 (crank_x + 0.03, axis_y, axis_z - radius * 0.75), 0.011, "anodized_black", 12,
                                 "crank"))
    return parts


def suit_bench(size, laid):
    """The suit-up bench, as its close-up shows it: a steel box with a lid lapping over its top, two dark seat pads
    on the lid, SUIT-UP BENCH stencilled on its front, a label and a taped note."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    lid = 0.05
    parts = [shapes.bevelled(shapes.box((-wide / 2 + 0.012, 0.0, front + 0.012), (wide / 2 - 0.012, tall - lid,
                                                                                    back - 0.012), "galvanized_dull",
                                        "body"), 0.004),
             shapes.bevelled(shapes.box((-wide / 2, tall - lid, front), (wide / 2, tall, back), "galvanized_dull",
                                        "lid"), 0.004)]
    for x in (-wide / 4 - 0.03, wide / 4 + 0.03):
        parts.append(shapes.bevelled(shapes.box((x - 0.27, tall - 0.004, front + 0.05), (x + 0.27, tall + 0.03,
                                                                                         back - 0.05), "vinyl_cabin",
                                                "pad"), 0.01))
    body_face = front + 0.012
    parts.append(label(-wide / 4, (tall - lid) * 0.45, 0.52, 0.11, body_face, "stencil_suit_up_bench", thick=0.004,
                       name="stencil"))
    parts.append(label(wide / 2 - 0.2, (tall - lid) * 0.72, 0.17, 0.07, body_face, "label_suit_up", name="label"))
    parts.append(label(wide / 2 - 0.42, (tall - lid) * 0.55, 0.1, 0.1, body_face, "note_bench", turn=4.0,
                       thick=0.004, name="note"))
    return parts


def status_panel(size, laid):
    """The airlock's cycle status panel, as its close-up shows it: a steel housing with a framed main screen, a small
    readout and a printed cycle plate, a row of round and square gauges, a keypad, buttons and a red stop button,
    two small monitors on a mount over it, a meter box at its side with a reading window, a taped note, and its
    cables out of glands under it back into the wall."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    housing_top = tall * 0.76
    housing_left, housing_right = wide / 2 - 0.1, -wide / 2  # the kit's +x is the viewer's left
    face = front + 0.03
    parts = [shapes.bevelled(shapes.box((housing_right, 0.1, face), (housing_left, housing_top, back), "painted_panel",
                                        "housing"), 0.004)]
    # The main screen and its bezel, the readout and the printed cycle plate beside it.
    parts += [part for part in wall_screen_part(housing_right + 0.17, housing_top - 0.14, 0.24, 0.17, face, "screen",
                                                rim=0.015)]
    parts += [part for part in wall_screen_part(housing_right + 0.355, housing_top - 0.165, 0.09, 0.07, face,
                                                "screen_amber", rim=0.01, name="readout")]
    parts.append(label(housing_right + 0.355, housing_top - 0.06, 0.09, 0.06, face, "label_cycle"))
    parts.append(label(housing_right + 0.355, housing_top - 0.255, 0.075, 0.075, face, "note_cycle", turn=3.0,
                       thick=0.004, name="note"))
    # The gauge row: two round dials and three square meters, each with its needle.
    gauge_y = 0.38
    for x in (housing_left - 0.04, housing_left - 0.11):
        parts.append(shapes.bevelled(shapes.ring((x, gauge_y, face), (x, gauge_y, face - 0.012), 0.03, 0.024,
                                                 "bare_steel", 32, "bezel"), 0.001))
        parts.append(shapes.cylinder((x, gauge_y, face), (x, gauge_y, face - 0.006), 0.025, "enamel_white", 32,
                                     "gauge"))
        parts.append(turned(shapes.box((x - 0.002, gauge_y, face - 0.01), (x + 0.002, gauge_y + 0.02, face - 0.0055),
                                       "anodized_red", "needle"), (x, gauge_y), 35.0))
    for at in range(3):
        x = housing_left - 0.18 - at * 0.065
        parts.append(shapes.bevelled(shapes.box((x - 0.028, gauge_y - 0.03, face - 0.012), (x + 0.028, gauge_y + 0.03,
                                                                                           face), "bare_steel",
                                                "bezel"), 0.002))
        parts.append(shapes.box((x - 0.022, gauge_y - 0.024, face - 0.016), (x + 0.022, gauge_y + 0.024, face - 0.011),
                                "enamel_white", "gauge"))
        parts.append(turned(shapes.box((x - 0.002, gauge_y - 0.018, face - 0.0195), (x + 0.002, gauge_y + 0.01,
                                                                                        face - 0.0155),
                                       "anodized_red", "needle"), (x, gauge_y - 0.018), -30.0 + 25.0 * at))
    # The keypad, the buttons and the stop button.
    pad_x, pad_y = housing_left - 0.11, 0.2
    parts.append(shapes.bevelled(shapes.box((pad_x - 0.09, pad_y - 0.06, face - 0.008), (pad_x + 0.09, pad_y + 0.06,
                                                                                        face), "anodized_black",
                                            "keypad"), 0.002))
    parts.append(shapes.content_plate((pad_x - 0.082, pad_y - 0.052, face - 0.012), (pad_x + 0.082, pad_y + 0.052,
                                                                                     face - 0.007), "keypad_print",
                                      "keys"))
    for x, y, material in ((housing_right + 0.17, 0.25, "anodized_red"), (housing_right + 0.17, 0.16, "anodized_red"),
                           (housing_right + 0.12, 0.25, "anodized_black"), (housing_right + 0.12, 0.16,
                                                                             "anodized_black")):
        parts.append(shapes.bevelled(shapes.cylinder((x, y, face), (x, y, face - 0.012), 0.014, material, 20,
                                                     "button"), 0.002))
    stop_x = housing_right + 0.05
    parts.append(shapes.bevelled(shapes.box((stop_x - 0.035, 0.15, face - 0.008), (stop_x + 0.035, 0.24, face),
                                            "hazard_paint", "estop"), 0.002))
    parts.append(shapes.bevelled(shapes.cylinder((stop_x, 0.195, face - 0.008), (stop_x, 0.195, face - 0.03), 0.024,
                                                 "anodized_red", 24, "estop"), 0.004))
    # Two small monitors on a mount over the housing.
    mount_z = back - 0.03
    parts.append(shapes.bevelled(shapes.box((housing_right + 0.06, housing_top, mount_z - 0.03),
                                            (housing_left - 0.06, housing_top + 0.04, back), "dark_panel", "mount"),
                                 0.003))
    for x in (housing_right + 0.105, housing_left - 0.105):
        low, high = (x - 0.095, housing_top + 0.035), (x + 0.095, tall - 0.005)
        parts.append(shapes.bevelled(shapes.box((*low, front + 0.012), (*high, mount_z - 0.01), "plastic_grey",
                                                "monitor"), 0.006))
        parts.append(shapes.bevelled(rounded_ring(low, high, 0.012, 0.022, front, front + 0.012, "plastic_grey",
                                                  "monitor"), 0.002))
        parts.append(shapes.content_plate((low[0] + 0.022, low[1] + 0.022, front + 0.008),
                                          (high[0] - 0.022, high[1] - 0.022, front + 0.012), "screen", "screen"))
    # The meter box at the side, with its reading window and label.
    box_left = wide / 2
    parts.append(shapes.bevelled(shapes.box((housing_left + 0.005, 0.18, front + 0.04), (box_left, 0.62, back),
                                            "grey_green_panel", "side_box"), 0.004))
    parts.append(shapes.box((housing_left + 0.025, 0.47, front + 0.034), (box_left - 0.02, 0.56, front + 0.04),
                            "glass_frosted", "meter"))
    parts.append(label((housing_left + box_left) / 2 + 0.002, 0.33, 0.06, 0.05, front + 0.04, "label_meter"))
    # Cables out of glands under the housing, down and back into the wall.
    for x in np.linspace(housing_right + 0.08, housing_left - 0.08, 4):
        x = float(x)
        parts.append(shapes.cylinder((x, 0.1, front + 0.07), (x, 0.075, front + 0.07), 0.013, "bare_steel", 6,
                                     "gland"))
        parts.append(shapes.cylinder((x, 0.075, front + 0.07), (x, 0.03, front + 0.07), 0.009, "cable_black", 12,
                                     "cable"))
        parts.append(wall_sphere((x, 0.03, front + 0.07), 0.009, "cable_black", "cable", 12))
        parts.append(shapes.cylinder((x, 0.03, front + 0.07), (x, 0.03, back), 0.009, "cable_black", 12, "cable"))
    return parts


def fan_unit(size, laid):
    """The airlock's fan unit, as its close-up shows it: a steel case, a square plate on its front with the fan's
    round mouth through it, the fan's blades and hub in a dark shroud behind a wire grille of rings and spokes, screws
    at the plate's corners, louvres in its side, and its FAN UNIT plate, a danger sticker and a maintenance sheet."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front + 0.01), (wide / 2, tall, back), "hammertone_grey",
                                        "case"), 0.006)]
    middle_x, middle_y = wide * 0.08, tall * 0.53
    plate_half = min(wide * 0.36, tall * 0.4)
    radius = plate_half * 0.86
    plate = shapes.box((middle_x - plate_half, middle_y - plate_half, front), (middle_x + plate_half,
                                                                              middle_y + plate_half, front + 0.01),
                       "dark_panel", "plate")
    shapes.cut(plate, shapes.cylinder((middle_x, middle_y, front - 0.02), (middle_x, middle_y, front + 0.03), radius,
                                      "dark_panel", 48, "cutter"))
    parts.append(shapes.bevelled(plate, 0.003))
    shroud_z = front + 0.06
    shapes.cut(parts[0], shapes.cylinder((middle_x, middle_y, front), (middle_x, middle_y, shroud_z + 0.003), radius,
                                         "hammertone_grey", 48, "cutter"))
    parts.append(shapes.cylinder((middle_x, middle_y, shroud_z), (middle_x, middle_y, shroud_z + 0.006), radius,
                                 "anodized_black", 48, "shroud"))
    parts.append(shapes.ring((middle_x, middle_y, front + 0.01), (middle_x, middle_y, shroud_z), radius + 0.004,
                             radius - 0.004, "anodized_black", 48, "shroud"))
    for at in range(5):
        angle = 2 * math.pi * at / 5
        blade = lock_tube_bar((middle_x + 0.04 * math.cos(angle), middle_y + 0.04 * math.sin(angle)),
                              (middle_x + (radius - 0.015) * math.cos(angle),
                               middle_y + (radius - 0.015) * math.sin(angle)), 0.035)
        parts.append(shapes.prism(blade, shroud_z - 0.018, shroud_z - 0.012, "bare_steel", "blade"))
    parts.append(shapes.cylinder((middle_x, middle_y, shroud_z - 0.035), (middle_x, middle_y, shroud_z), 0.045,
                                 "dark_panel", 32, "hub"))
    grille_z = front - 0.006
    for share in (0.25, 0.42, 0.59, 0.76, 0.93):
        ring_radius = radius * share
        parts.append(shapes.ring((middle_x, middle_y, grille_z - 0.002), (middle_x, middle_y, grille_z + 0.002),
                                 ring_radius + 0.0025, ring_radius - 0.0025, "bare_steel", 40, "grille"))
    for at in range(8):
        angle = 2 * math.pi * at / 8
        parts.append(shapes.cylinder((middle_x, middle_y, grille_z), (middle_x + radius * math.cos(angle),
                                                                     middle_y + radius * math.sin(angle), grille_z),
                                     0.0025, "bare_steel", 8, "grille"))
    parts.append(shapes.cylinder((middle_x, middle_y, grille_z + 0.002), (middle_x, middle_y, grille_z - 0.004), 0.04,
                                 "bare_steel", 24, "grille"))
    parts += [screw(middle_x + sx * (plate_half - 0.02), middle_y + sy * (plate_half - 0.02), front)
              for sx in (-1, 1) for sy in (-1, 1)]
    # The labels on the strip of case beside the plate (the viewer's right, the kit's -x).
    strip = (-wide / 2 + middle_x - plate_half) / 2 - 0.005
    case_face = front + 0.01
    parts.append(label(strip, tall * 0.8, 0.11, 0.06, case_face, "label_fan_unit"))
    parts.append(label(strip, tall * 0.62, 0.1, 0.08, case_face, "label_high_voltage", name="sticker"))
    parts.append(label(strip, tall * 0.38, 0.1, 0.15, case_face, "sheet_maintenance", thick=0.004, name="sheet"))
    # Louvres in the case's side (the kit's -x face), built facing front and turned onto it.
    louvre_wide, louvre_tall = min(0.24, deep * 0.55), 0.16
    side_plate = shapes.box((-louvre_wide / 2 - 0.02, 0.08, -0.012), (louvre_wide / 2 + 0.02, 0.08 + louvre_tall + 0.04,
                                                                       0.0), "hammertone_grey", "louvre_frame")
    side = furn_louvres(side_plate, 0.0, 0.1 + louvre_tall / 2, louvre_wide, louvre_tall, -0.012, 0.0, 6,
                        "hammertone_grey", back_thick=0.006)
    louvre_parts = [shapes.bevelled(side_plate, 0.002)] + side
    furn_spun(louvre_parts, (0.0, 0.0), 90.0)
    for part in louvre_parts:
        floor_moved(part, (-wide / 2, 0.0, (front + back) / 2 + 0.03))
    return parts + louvre_parts


def crown_strip_lamp(size, laid):
    """A walkway tube's strip lamp along its crown, as its close-up shows it: a long steel housing, the lens set in a
    pocket down its middle, a mounting tab with a screw at each end, and a small circuit label by one end."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    tab = 0.05
    housing = shapes.box((-wide / 2 + tab, 0.0, front), (wide / 2 - tab, tall, back), "painted_panel", "housing")
    lens_low, lens_high = (-wide / 2 + tab + 0.03, tall * 0.25), (wide / 2 - tab - 0.18, tall * 0.75)
    wall_pocket(housing, lens_low, lens_high, front - 0.02, front + 0.01)
    parts = [shapes.bevelled(housing, 0.003),
             shapes.content_plate((*lens_low, front + 0.006), (*lens_high, front + 0.01), "lamp_strip", "lens")]
    for side in (-1, 1):
        x0, x1 = sorted((side * (wide / 2 - tab), side * wide / 2))
        parts.append(shapes.bevelled(shapes.box((x0, tall * 0.2, back - 0.008), (x1, tall * 0.8, back),
                                                "painted_panel", "tab"), 0.0015))
        parts.append(screw((x0 + x1) / 2, tall / 2, back - 0.008))
    parts.append(label(-wide / 2 + tab + 0.09 + (wide - 2 * tab - 0.21) + 0.0, tall / 2, 0.12, tall * 0.5, front,
                       "label_circuit"))
    return parts


def hull_patch(size, laid):
    """A repair patch on a tube's hull plate, as its close-up shows it: a plate laid over the hull, a weld bead round
    an inner panel of it, and strips of tape across its edges."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    plate_face = back - 0.016
    parts = [shapes.bevelled(shapes.box((-wide / 2 + 0.02, 0.02, plate_face), (wide / 2 - 0.02, tall - 0.02, back),
                                        "galvanized_dull", "plate"), 0.003)]
    inner = rounded_outline((-wide / 2 + 0.11, 0.1), (wide / 2 - 0.11, tall - 0.1), 0.03)
    bead = rounded_outline((-wide / 2 + 0.125, 0.115), (wide / 2 - 0.125, tall - 0.115), 0.02)
    parts.append(shapes.bevelled(lock_tube_ring(inner, bead, plate_face - 0.007, plate_face + 0.002, "cast_steel",
                                                "weld"), 0.0025))
    for x, y, along in ((-wide / 2 + 0.02, tall * 0.75, False), (wide / 2 - 0.02, tall * 0.3, False),
                        (wide * 0.25, tall - 0.02, True), (-wide * 0.2, 0.02, True)):
        if along:
            low, high = (x - 0.025, y - 0.06), (x + 0.025, y + 0.06)
        else:
            low, high = (x - 0.06, y - 0.025), (x + 0.06, y + 0.025)
        parts.append(shapes.bevelled(shapes.box((*low, plate_face - 0.004), (*high, back), "plastic_grey", "tape"),
                                     0.0015))
    return parts


def sign_plate(size, laid):
    """A sign at a walkway tube's end, as its close-up shows it: a yellow plate with rounded corners, a bolt at each
    corner, the name of where the tube leads printed across it (laid `label`, a sign_* print)."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    plate = shapes.prism(rounded_outline((-wide / 2, 0.0), (wide / 2, tall), 0.02), front + 0.004, back,
                         "hazard_paint", "plate")
    parts = [shapes.bevelled(plate, 0.002)]
    parts.append(label(0.0, tall / 2, wide - 0.08, tall - 0.05, front + 0.004, laid.get("label", "sign_pressure_hatch")))
    parts += [bolt(sx * (wide / 2 - 0.022), y, front + 0.004, "cast_iron_dark") for sx in (-1, 1)
              for y in (0.022, tall - 0.022)]
    return parts


def end_mat(size, laid):
    """The dust grating at a walkway tube's end, set in its deck, its front up, as its close-up shows it: a frame
    round a solid base plate, bars across it in a grid with gaps down to the base, and a DO NOT COVER stencil along
    the frame."""
    wide, long, deep = size
    top, bottom = -deep / 2, deep / 2
    rim = 0.04
    parts = floor_frame((-wide / 2, 0.0), (wide / 2, long), top, bottom, rim, "galvanized_steel", "frame")
    parts.append(shapes.box((-wide / 2 + rim, rim, bottom - 0.005), (wide / 2 - rim, long - rim, bottom),
                            "dark_panel", "base"))
    pitch = 0.045
    bars = max(1, round((wide - 2 * rim) / pitch))
    for at in range(1, bars):
        x = -wide / 2 + rim + (wide - 2 * rim) * at / bars
        parts.append(shapes.box((x - 0.003, rim, top + 0.001), (x + 0.003, long - rim, bottom - 0.005),
                                "galvanized_steel", "bar"))
    crosses = max(1, round((long - 2 * rim) / 0.11))
    for at in range(1, crosses):
        y = rim + (long - 2 * rim) * at / crosses
        parts.append(shapes.box((-wide / 2 + rim, y - 0.003, top + 0.003), (wide / 2 - rim, y + 0.003,
                                                                             bottom - 0.005), "galvanized_steel",
                                "bar"))
    parts.append(label(wide / 2 - 0.3, rim / 2, 0.36, rim - 0.01, top, "stencil_do_not_cover", name="stencil"))
    return parts


def arc_points(radius, deep, start, end):
    """An annular sector of a tube's section in the kit frame's x-y plane about the tube's axis: from `start` to `end`
    (degrees from the crown, toward +x), between `radius - deep` and `radius` from the axis."""
    steps = max(2, round(abs(end - start) / 4))
    angles = [np.radians(start + (end - start) * step / steps) for step in range(steps + 1)]
    outer = [(radius * np.sin(angle), radius * np.cos(angle)) for angle in angles]
    inner = [((radius - deep) * np.sin(angle), (radius - deep) * np.cos(angle)) for angle in reversed(angles)]
    return outer + inner


def standing(points, reference):
    """Points moved so the reference outline's box stands on its own foot's middle (as every piece stands on its
    origin)."""
    middle = (min(x for x, _ in reference) + max(x for x, _ in reference)) / 2
    foot = min(y for _, y in reference)
    return [(x - middle, y - foot) for x, y in points]


def hull_plate(size, laid):
    """A walkway tube's hull plate between two hoops: a curved band of its section (`arc`: radius, depth, start and end
    angles from the crown in degrees) as long as its bay (the kit frame's z)."""
    wide, tall, long = size
    outline = arc_points(*laid["arc"])
    return [shapes.bevelled(shapes.prism(standing(outline, outline), -long / 2, long / 2,
                                         laid.get("material", "painted_panel"), "plate"), EDGE)]


def hoop(size, laid):
    """A walkway tube's hoop: a steel rib round its section (`arc` as hull_plate's), as thick as its box is long,
    a flange along its inner edge."""
    wide, tall, long = size
    radius, deep, start, end = laid["arc"]
    outline = arc_points(radius, deep, start, end)
    flange = arc_points(radius - deep + 0.02, 0.02, start, end)
    return [shapes.bevelled(shapes.prism(standing(outline, outline), -long / 2 + 0.02, long / 2 - 0.02,
                                         laid.get("material", "dark_panel"), "web"), 0.004),
            shapes.bevelled(shapes.prism(standing(flange, outline), -long / 2, long / 2,
                                         laid.get("material", "dark_panel"), "flange"), 0.003)]


# --- the expedition camp's grounds (mars-build, 2026-10-07) -----------------------------------------------------------

MAST_COLUMN_TOP = 11.0  # CampMast's lattice legs up to the lamp's housing
MAST_LEGS_APART = 0.5
MAST_GUY_FROM = 8.0
MAST_HOUSING = (0.6, 0.7, 0.6)
MAST_LAMP_HIGH = 11.4  # CampMast.LAMP_HEIGHT_M
MAST_GUY_OUT = 3.2  # how far out the guys' anchors stand from the column


def mast(size, laid):
    """The camp's guyed radio mast, as its close-up shows it: four legs of a square lattice column braced across and
    diagonally every metre, the lamp's housing on top with its lens, the aerial to the full height, and three guy wires
    from high on the column down to anchor plates on the ground MAST_GUY_OUT away, a third of the way round from each
    other, the first straight ahead. Its foot is the column's; its box is the guys' reach and the mast's height."""
    wide, tall, deep = size
    half = MAST_LEGS_APART / 2
    corners = [(-half, -half), (half, -half), (half, half), (-half, half)]
    parts = [shapes.cylinder((x, 0.0, z), (x, MAST_COLUMN_TOP, z), 0.03, "anodized_natural", 10, "leg")
             for x, z in corners]
    level = 1.0
    while level < MAST_COLUMN_TOP:
        for side, (x0, z0) in enumerate(corners):
            x1, z1 = corners[(side + 1) % 4]
            parts.append(shapes.cylinder((x0, level, z0), (x1, level, z1), 0.018, "anodized_natural", 8, "brace"))
            parts.append(shapes.cylinder((x0, level - 1.0, z0), (x1, level, z1), 0.016, "anodized_natural", 8, "brace"))
        level += 1.0
    hw, hh, hd = MAST_HOUSING
    parts.append(shapes.bevelled(shapes.box((-hw / 2, MAST_COLUMN_TOP, -hd / 2),
                                            (hw / 2, MAST_COLUMN_TOP + hh, hd / 2), "dust_coated_paint", "housing"), 0.01))
    for x, z in ((0.0, -hd / 2 - 0.02), (0.0, hd / 2 + 0.02), (-hw / 2 - 0.02, 0.0), (hw / 2 + 0.02, 0.0)):
        parts.append(shapes.cylinder((x * 0.97, MAST_LAMP_HIGH, z * 0.97), (x * 1.08, MAST_LAMP_HIGH, z * 1.08), 0.09,
                                     "lamp_lens", 16, "lens"))
    parts.append(shapes.cylinder((0.0, MAST_COLUMN_TOP + hh, 0.0), (0.0, tall, 0.0), 0.025, "stainless_lander", 10,
                                 "aerial"))
    reach = MAST_GUY_OUT
    for index in range(3):
        angle = 2 * math.pi * index / 3 + math.pi / 2
        way = (math.cos(angle), math.sin(angle))
        top = (way[0] * half, MAST_GUY_FROM, way[1] * half)
        foot = (way[0] * reach, 0.06, way[1] * reach)
        parts.append(shapes.cylinder(top, foot, 0.0125, "galvanized_dull", 8, "guy"))
        parts.append(shapes.bevelled(shapes.box((foot[0] - 0.14, 0.0, foot[2] - 0.14), (foot[0] + 0.14, 0.06, foot[2] + 0.14),
                                                "galvanized_steel", "anchor"), 0.006))
    return parts


def ground_cable(size, laid):
    """A length of heavy power cable lying on the ground along x, as the concept shows the camp's cables: one round
    sheathed cable, a little slack, its middle a few millimetres higher than its ends where it lies over grit."""
    wide, tall, deep = size
    radius = min(tall, deep) / 2
    steps = 6
    points = [(-wide / 2 + wide * step / steps, radius + 0.004 * math.sin(math.pi * step / steps), 0.0)
              for step in range(steps + 1)]
    return [shapes.cylinder(start, end, radius, "cable_black", 12, "cable") for start, end in zip(points, points[1:])]


BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "backer", "cable_bundle", "cable_drop", "lattice_diamond_strut", "lattice_hip_rib", "lattice_node_plate",
    "lattice_ring_rib", "machine_bay_plate", "pipe_straight", "pit_floor_plate", "pit_wall_panel",
    "ring_floor_plate", "roof_face_panel", "stair_stringer", "under_floor_box", "wall_corner_post", "wall_cornice",
    "wall_lower_plain", "wall_skirting", "wall_upper_plain", "hull_plate", "hoop",
    # method B's fittings (hub round five)
    "hatch_frame", "hatch_leaf", "hatch_wheel", "hatch_window", "hatch_hinge", "hatch_wall_surround", "porthole_panel",
    "wall_lower_vent", "notice_board", "door_frame", "door_leaf", "suit_alcove", "hose_reel", "suit_bench", "status_panel", "fan_unit", "crown_strip_lamp", "hull_patch", "sign_plate", "end_mat", "galley_counter", "mess_table", "stool", "exam_couch", "light_ring", "pot", "couch_pillow", "sleep_pod", "pillow", "locker_bank", "food_shelf", "food_jug", "food_tin", "ration_box", "med_cabinet", "med_box", "med_bottle", "hygiene_cubicle", "radio", "screwdriver", "talllocker", "rack", "comms", "console", "labbench", "toolboard", "waste_bin", "monitor", "keyboard", "glovebox", "floor_grating", "floor_access_hatch", "tread_mat", "ceiling_cable_tray", "ceiling_duct", "roof_apex_hub", "roof_light_fixture", "pipe_bracket", "pipe_elbow", "pipe_valve", "pit_junction_box", "wall_lower_patched", "wall_upper_patched", "wall_upper_cables", "wall_upper_pipes", "wall_upper_screen_recess", "status_display", "wall_screen_cluster", "intercom_panel", "small_readout", "door_control_box", "conduit_box", "wall_cage_lamp", "door_strip_lamp", "grab_bar",
    # the expedition camp's grounds (mars-build)
    "mast", "ground_cable")}


def build(kind, size, laid, name):
    """One code-built piece of `kind` at `size`, as one object whose material slots name library materials; which of
    its parts the room can see (parts_seen) rides on it as the custom property `parts_seen`, as JSON."""
    parts = BUILDERS[kind](tuple(size), laid)
    seen, off = checked_from_the_room(kind, parts)
    whole = shapes.joined(parts, name)
    whole["parts_seen"] = json.dumps(seen)
    whole["prints_off"] = json.dumps(off)
    return whole


def checked_from_the_room(kind, parts):
    """parts_seen and prints_off from the side the room sees the kind from (FLOOR_SEEN_TURN: roof gear is seen from
    below or its side): the parts turned so that side faces the checks' front, checked, and turned back."""
    degrees = FLOOR_SEEN_TURN.get(kind, 0.0)
    there = Matrix.Rotation(math.radians(degrees), 4, "X")
    for part in parts:
        part.data.transform(there)
    found = parts_seen(parts), prints_off(parts)
    for part in parts:
        part.data.transform(there.inverted())
    return found


PRINT_PARTS = ("label", "sticker", "sheet", "note", "decal", "outlines")
# How far the face under a print may step in or out across its footprint before the print counts as lying over a
# part (a vent's hood, a handle, a bolt): a flat clear area reads under 2 mm.
FLAT_UNDER = 0.002


def prints_off(parts):
    """The prints (labels, stickers, sheets, notes) that do not lie on a clear flat area (round six: a decal is placed
    by rule, never over a vent, a handle or a tool): for each, rays from just in front of its back face straight back
    on a 4 x 4 grid over its footprint, against the rest of the piece; a ray meeting nothing, or the hits stepping
    more than FLAT_UNDER, puts the print off. Their part names, numbered."""
    found = []
    for index, part in enumerate(parts):
        if part.name.split(".")[0] not in PRINT_PARTS:
            continue
        others = [other for other in parts if other is not part]
        together = bmesh.new()
        for other in others:
            together.from_mesh(other.data)
        tree = BVHTree.FromBMesh(together)
        together.free()
        points = [vertex.co for vertex in part.data.vertices]
        back = min(point.y for point in points)  # Blender's +y is the kit's front: the back face has the least y
        middle_x = sorted(point.x for point in points)
        middle_z = sorted(point.z for point in points)
        span_x, span_z = (middle_x[0], middle_x[-1]), (middle_z[0], middle_z[-1])
        depths = []
        for across in np.linspace(0.15, 0.85, 4):
            for up in np.linspace(0.15, 0.85, 4):
                start = Vector((span_x[0] + (span_x[1] - span_x[0]) * across, back + 0.0005,
                                span_z[0] + (span_z[1] - span_z[0]) * up))
                hit = tree.ray_cast(start, Vector((0.0, -1.0, 0.0)), 0.05)[0]
                depths.append(None if hit is None else hit.y)
        if None in depths or max(depths) - min(depths) > FLAT_UNDER:
            found.append(f"{part.name.split('.')[0]}#{index}")
    return found
