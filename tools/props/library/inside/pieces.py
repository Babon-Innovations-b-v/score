"""Runs inside Blender: the hub's plain plates, pipes and trims built in code (the sorter's allow-list, sorter.PLAIN:
the owner, 2026-10-07, code builds nothing with detail), each at the size the layout lays it, its parts naming their
library material.

    import pieces; whole = pieces.build("wall_upper_plain", (1.2, 2.0, 0.06), {"taper": 1.0})

Sizes are (wide, tall, deep) in metres in the kit frame (shapes.py): front toward -z, the back on the wall. Openings
are real holes at the shell's own sizes (the doorway 2.2 x 2.6 m, the porthole 0.6 m across), never a picture of
one.
"""

import importlib
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
    # Laid out on the hub's 0.8 x 0.6 board; a smaller board takes them scaled to it (the airlock's caution board).
    across, up = min(1.0, wide / 0.8), min(1.0, tall / 0.6)
    sheets = (("sheet_eva", 0.235, 0.395, 0.19, 0.25, 1.2), ("sheet_roster", 0.0, 0.40, 0.19, 0.25, -0.8),
              ("sheet_log", -0.235, 0.39, 0.19, 0.25, 0.6), ("sheet_plan", 0.13, 0.155, 0.27, 0.18, -0.5))
    for variant, x, y, sheet_wide, sheet_tall, turn in sheets:
        x, y, sheet_wide, sheet_tall = x * across, y * up, sheet_wide * across, sheet_tall * up
        parts.append(label(x, y, sheet_wide, sheet_tall, board, variant, turn, 0.004, "sheet"))
        parts.append(shapes.cylinder((x, y + sheet_tall / 2 - 0.02, board - 0.003),
                                     (x, y + sheet_tall / 2 - 0.02, board - 0.011), 0.007, "anodized_red", 12, "pin"))
    for variant, x, y, turn in (("note_filter", -0.12, 0.16, 3.0), ("note_link", -0.26, 0.15, -2.5)):
        parts.append(label(x * across, y * up, 0.09 * across, 0.09 * up, board, variant, turn, 0.004, "note"))
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
FLOOR_SEEN_TURN = {"floor_socket": -90.0, "bay_mark": -90.0, "ceiling_cable_tray": -90.0, "ceiling_duct": -90.0, "roof_apex_hub": 90.0,
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
    # The outlines' plate: 1.5 mm, or as deep as a room that model-checks its board asks (the workshop's, 4 mm: the
    # check fails a wall under 3 mm).
    print_deep = laid.get("print_deep", 0.0015)
    parts = [shapes.box((-wide / 2 + rim, rim, face), (wide / 2 - rim, tall - rim, back), "wood_board", "board"),
             shapes.content_plate((-wide / 2 + rim, rim, face - print_deep), (wide / 2 - rim, tall - rim, face),
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
    tip_half = radius * 0.08
    if laid.get("solid_tip"):
        # A room that model-checks its tools (the workshop's): the tip 4 mm thick and the shaft standing on it rather
        # than through it, so no wall reads under the check's 3 mm.
        tip_half = 0.002
        parts[-1] = shapes.cylinder((0.0, 0.014, 0.0), (0.0, tall - handle - 0.012, 0.0), radius * 0.2, "bare_steel",
                                    10, "shaft")
    parts.append(shapes.box((-radius * 0.35, 0.0, -tip_half), (radius * 0.35, 0.014, tip_half), "bare_steel", "tip"))
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
        parts.append(shapes.bevelled(shapes.box((low_x + 0.03, bottom - 0.005, front + 0.06),
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
        parts.append(shapes.box((x_low, band_low, front - 0.005), (x_high, band_high, front), "enamel_blue", "stripe"))
    for side in (-1, 1):
        x = side * wide / 2
        parts.append(shapes.box((min(x, x + side * 0.005), band_low, front), (max(x, x + side * 0.005), band_high,
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
                                             "enamel_blue", 32, "lid"), 0.004)]
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
        parts.append(shapes.box((-wide / 2 - 0.004, low, front - 0.004), (wide / 2 + 0.004, high, deep / 2 + 0.004),
                                "enamel_blue", "band"))
    parts.append(label(0.0, tall * 0.46, wide * 0.8, tall * 0.4, front, "label_medical_supplies"))
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
             shapes.cylinder((0.0, shoulder * 0.25, 0.0), (0.0, shoulder * 0.8, 0.0), radius + 0.004, "canvas_beige",
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
    parts = [shapes.prism(band, surface - thick, surface, "hazard_paint", "stripe")]
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
    shapes.cut(parts[0], shapes.cylinder((middle_x, middle_y, front), (middle_x, middle_y, shroud_z + 0.006), radius,
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
        parts.append(shapes.ring((middle_x, middle_y, grille_z - 0.004), (middle_x, middle_y, grille_z),
                                 ring_radius + 0.0025, ring_radius - 0.0025, "bare_steel", 40, "grille"))
    for at in range(8):
        angle = 2 * math.pi * at / 8
        parts.append(shapes.cylinder((middle_x, middle_y, grille_z + 0.0025), (middle_x + radius * math.cos(angle),
                                                                              middle_y + radius * math.sin(angle),
                                                                              grille_z + 0.0025),
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
    side = furn_louvres(side_plate, 0.0, 0.1 + louvre_tall / 2, louvre_wide, louvre_tall, -0.012, 0.0, 4,
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
    parts.append(shapes.bevelled(lock_tube_ring(inner, bead, plate_face - 0.007, plate_face, "cast_steel",
                                                "weld"), 0.0025))
    for x, y, along in ((-wide / 2 + 0.02, tall * 0.75, False), (wide / 2 - 0.02, tall * 0.3, False),
                        (wide * 0.25, tall - 0.02, True), (-wide * 0.2, 0.02, True)):
        if along:
            low, high = (x - 0.025, y - 0.06), (x + 0.025, y + 0.06)
        else:
            low, high = (x - 0.06, y - 0.025), (x + 0.06, y + 0.025)
        parts.append(shapes.bevelled(shapes.box((*low, plate_face - 0.004), (*high, plate_face), "plastic_grey",
                                                "tape"), 0.0015))
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

# --- the expedition camp habitat (mars-build, 2026-10-07): the domes' lining and shell, their fittings and the
# furniture holders method B builds; an American company's inflatable domes (quilted fabric between anodised ribs,
# a soft-goods shell banded by straps over a padded foot ring, rigid frames). Curved pieces carry their numbers in
# laid["arc"] (tools/props/scene/camp_kit.py writes them from the game's camp_habitat.gd and camp_lining.gd).

CAMP_QUILT = "quilted_white"
CAMP_PAD = "quilted_grey"
CAMP_RIB = "anodized_natural"
CAMP_BAND = "carbon_fibre"
CAMP_SKIRT = "rubber"
CAMP_DARK_GLASS = "glass_tinted"
CAMP_SHELL = "beta_cloth"
CAMP_DECK = "deck"
CAMP_LENS = "lamp_lens"
CAMP_HOUSING = "plastic_white"
CAMP_PANEL = "composite_grey"
CAMP_EDGE = 0.004
# CampLining's numbers (game/world/mars/expedition_camp/camp_lining/camp_lining.gd).
CAMP_SKIN = 0.08
CAMP_SKIRTING_TALL = 0.22
CAMP_SKIRTING_IN = 0.05
CAMP_BAND_TALL = 0.3
CAMP_BAND_IN = 0.06
CAMP_WINDOW_LOW = 1.7
CAMP_WINDOW_HIGH = 3.0
CAMP_WINDOW_INSET = 0.35
CAMP_FRAME = 0.1
CAMP_FRAME_IN = 0.06
CAMP_TINT_BEHIND = 0.05
CAMP_RIB_WIDE = 0.14
CAMP_RIB_IN = 0.06
CAMP_STRAP_WIDE = 0.08
CAMP_STRAP_PROUD = 0.012
CAMP_SHELL_THICK = 0.04


def camp_solid_from(points, faces, material, name):
    """A closed mesh from kit-frame points and faces (each a list of point indices), its normals made consistent."""
    built = bmesh.new()
    verts = [built.verts.new(shapes.to_blender(point)) for point in points]
    for face in faces:
        try:
            built.faces.new([verts[index] for index in face])
        except ValueError:  # a face named twice (a degenerate strip) is left out
            pass
    bmesh.ops.remove_doubles(built, verts=built.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def camp_sheet(grid, normals, thick, material, name):
    """A curved plate: a grid of kit-frame points (rows x columns) as its front, thickened `thick` along each point's
    normal, closed round its four edges."""
    grid = np.asarray(grid, dtype=np.float64)
    normals = np.asarray(normals, dtype=np.float64)
    rows, columns = grid.shape[:2]
    back = grid + normals * thick
    points = [tuple(point) for point in grid.reshape(-1, 3)] + [tuple(point) for point in back.reshape(-1, 3)]
    count = rows * columns

    def front(row, column):
        return row * columns + column

    faces = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            quad = [front(row, column), front(row, column + 1), front(row + 1, column + 1), front(row + 1, column)]
            faces.append(quad)
            faces.append([index + count for index in reversed(quad)])
    edge = ([front(0, column) for column in range(columns)] + [front(row, columns - 1) for row in range(1, rows)]
            + [front(rows - 1, column) for column in range(columns - 2, -1, -1)]
            + [front(row, 0) for row in range(rows - 2, 0, -1)])
    for at in range(len(edge)):
        one, two = edge[at], edge[(at + 1) % len(edge)]
        faces.append([one, two, two + count, one + count])
    return camp_solid_from(points, faces, material, name)


def camp_arc_of(laid):
    return laid.get("arc", {})


# --- the lining inside ---------------------------------------------------------------------------------------------

def camp_lining_layers(wide, parts, with_skirting=True, top=3.4):
    """The skirting along the deck and the dark band along the wall's top, standing into the room."""
    if with_skirting:
        parts.append(shapes.bevelled(shapes.box((-wide / 2, 0.0, -CAMP_SKIRTING_IN), (wide / 2, CAMP_SKIRTING_TALL, 0.0), CAMP_SKIRT,
                                                "skirting"), 0.006))
    parts.append(shapes.bevelled(shapes.box((-wide / 2, top - CAMP_BAND_TALL, -CAMP_BAND_IN), (wide / 2, top, 0.0), CAMP_BAND, "band"),
                                 CAMP_EDGE))
    return parts


def camp_quilt_box(low, high, name="quilt"):
    return shapes.bevelled(shapes.box(low, high, CAMP_QUILT, name), 0.01)


def dome_wall_panel(size, laid):
    """A plain lining panel: quilted fabric over the deck to the wall's top, skirting and top band."""
    wide, tall, deep = size
    return camp_lining_layers(wide, [camp_quilt_box((-wide / 2, -0.05, 0.0), (wide / 2, tall, CAMP_SKIN))], top=tall)


def dome_window_panel(size, laid):
    """A lining panel round its window: quilted fabric round the hole, a rigid frame standing into the room, the glass
    in it, dark glass close behind, skirting and top band."""
    wide, tall, deep = size
    inner = wide - CAMP_WINDOW_INSET * 2.0
    quilt = shapes.box((-wide / 2, -0.05, 0.0), (wide / 2, tall, CAMP_SKIN), CAMP_QUILT, "quilt")
    shapes.cut(quilt, shapes.box((-inner / 2, CAMP_WINDOW_LOW, -0.2), (inner / 2, CAMP_WINDOW_HIGH, 0.3), CAMP_QUILT, "cutter"))
    parts = [shapes.bevelled(quilt, 0.01)]
    outline = camp_window_outline(-inner / 2 - CAMP_FRAME, CAMP_WINDOW_LOW - CAMP_FRAME, inner / 2 + CAMP_FRAME, CAMP_WINDOW_HIGH + CAMP_FRAME, 0.12)
    hole = camp_window_outline(-inner / 2, CAMP_WINDOW_LOW, inner / 2, CAMP_WINDOW_HIGH, 0.08)
    frame = shapes.prism(outline, -CAMP_FRAME_IN, CAMP_SKIN, CAMP_RIB, "frame")
    shapes.cut(frame, shapes.prism(hole, -CAMP_FRAME_IN - 0.1, CAMP_SKIN + 0.1, CAMP_RIB, "cutter"))
    parts.append(shapes.bevelled(frame, 0.006))
    parts.append(shapes.prism(hole, CAMP_SKIN * 0.5 - 0.01, CAMP_SKIN * 0.5 + 0.01, CAMP_DARK_GLASS, "glass"))
    parts.append(shapes.prism(outline, CAMP_SKIN + CAMP_TINT_BEHIND, CAMP_SKIN + CAMP_TINT_BEHIND + 0.03, CAMP_DARK_GLASS, "glass"))
    return camp_lining_layers(wide, parts, top=tall)


def camp_window_outline(left, bottom, right, top, radius, steps=5):
    """A rectangle with rounded corners in the x-y plane, as a polygon."""
    found = []
    for (x, y), start in (((right - radius, top - radius), 0.0), ((left + radius, top - radius), 90.0),
                          ((left + radius, bottom + radius), 180.0), ((right - radius, bottom + radius), 270.0)):
        for step in range(steps + 1):
            angle = math.radians(start + 90.0 * step / steps)
            found.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
    return found


def dome_rib(size, laid):
    """An anodised rib over a panel join, from the deck to the wall's top, rivets up it."""
    wide, tall, deep = size
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), CAMP_RIB, "rib"), 0.008)]
    for y in np.linspace(0.4, tall - 0.4, 6):
        parts.append(shapes.cylinder((0.0, y, -deep / 2), (0.0, y, -deep / 2 - 0.006), 0.012, CAMP_RIB, 12, "rivet"))
    return parts


def camp_ring_points(arc, radius, height, degrees):
    """A point on a dome's ring in a piece's frame: the piece's origin at the middle of its panel's chord at the
    origin ring (arc `origin_radius`, `origin_height`), x along the chord, z out of the dome."""
    angle = math.radians(degrees)
    chord = arc["origin_radius"]
    return (radius * math.sin(angle), height - arc["origin_height"], radius * math.cos(angle) - chord)


def dome_ceiling_gore(size, laid):
    """A quilted ceiling gore from the wall's top up its rings to the flat top, its rib along its first edge."""
    arc = camp_arc_of(laid)
    half = arc["half"]
    rings = arc["rings"]
    columns = 9
    grid, normals = [], []
    for radius, height in rings:
        row, row_normals = [], []
        for column in range(columns):
            degrees = -half + 2 * half * column / (columns - 1)
            row.append(camp_ring_points(arc, radius, height, degrees))
            row_normals.append(camp_gore_normal(rings, radius, height, degrees))
        grid.append(row)
        normals.append(row_normals)
    parts = [camp_sheet(grid, normals, 0.04, CAMP_QUILT, "quilt")]
    rib_grid, rib_normals = [], []
    for radius, height in rings:
        row, row_normals = [], []
        for degrees in (-half - math.degrees(CAMP_RIB_WIDE / 2 / radius), -half + math.degrees(CAMP_RIB_WIDE / 2 / radius)):
            point = np.asarray(camp_ring_points(arc, radius, height, degrees))
            normal = np.asarray(camp_gore_normal(rings, radius, height, degrees))
            row.append(tuple(point - normal * CAMP_RIB_IN))
            row_normals.append(tuple(normal))
        rib_grid.append(row)
        rib_normals.append(row_normals)
    parts.append(camp_sheet(rib_grid, rib_normals, CAMP_RIB_IN, CAMP_RIB, "rib"))
    return parts


def camp_gore_normal(rings, radius, height, degrees):
    """The way out of the ceiling (away from the room) at a point on it: up and out from the dome's middle."""
    angle = math.radians(degrees)
    outward = np.array([math.sin(angle), 0.0, math.cos(angle)])
    found = outward * 0.35 + np.array([0.0, 1.0, 0.0])
    return tuple(found / np.linalg.norm(found))


def dome_roof_cap(size, laid):
    """The flat top over a dome: a quilted disc, an aluminium ring, the vent fan's grille and blades in the middle and
    a ring of lamp lens round them. Laid facing down: its front (-z) looks into the room."""
    wide = size[0]
    radius = wide / 2
    parts = [shapes.bevelled(shapes.ring((0.0, 0.0, 0.0), (0.0, 0.0, 0.05), radius, 0.82, CAMP_QUILT, 72, "quilt"), 0.01)]
    parts.append(shapes.bevelled(shapes.ring((0.0, 0.0, -0.05), (0.0, 0.0, 0.05), 0.82, 0.62, CAMP_RIB, 64, "ring"), 0.006))
    parts.append(shapes.ring((0.0, 0.0, -0.035), (0.0, 0.0, 0.0), 0.6, 0.42, CAMP_LENS, 64, "lens"))
    parts.append(shapes.bevelled(shapes.ring((0.0, 0.0, -0.06), (0.0, 0.0, 0.05), 0.42, 0.36, CAMP_RIB, 48, "grille"),
                                 0.004))
    for at in range(-3, 4):
        x = at * 0.1
        half = math.sqrt(max(0.36 ** 2 - x ** 2, 0.0)) - 0.01
        parts.append(shapes.box((x - 0.012, -half, -0.055), (x + 0.012, half, -0.045), CAMP_RIB, "grille"))
    parts.append(shapes.cylinder((0.0, 0.0, -0.02), (0.0, 0.0, 0.04), 0.07, CAMP_BAND, 24, "fan"))
    for at in range(5):
        angle = 2 * math.pi * at / 5
        tip = (0.3 * math.cos(angle), 0.3 * math.sin(angle))
        side = (0.07 * math.cos(angle + 0.5), 0.07 * math.sin(angle + 0.5))
        parts.append(shapes.prism([(0.0, 0.0), side, tip], 0.0, 0.006, CAMP_BAND, "fan"))
    return parts


def dome_deck_wedge(size, laid):
    """A deck plate from the dome's middle out under the wall, as a wedge, a trim strip along its outer edge. Laid
    flat with its front up; its top at the deck."""
    arc = camp_arc_of(laid)
    half = math.radians(arc["half"])
    reach = arc["reach"]
    left, right = (-reach * math.sin(half), reach * math.cos(half)), (reach * math.sin(half), reach * math.cos(half))
    parts = [shapes.bevelled(shapes.prism([(0.0, 0.0), right, left], 0.0, 0.04, CAMP_DECK, "plate"), CAMP_EDGE)]
    inner = 1.0 - 0.6 / reach
    parts.append(shapes.prism([right, left, (left[0] * inner, left[1] * inner), (right[0] * inner, right[1] * inner)],
                              -0.004, 0.0, CAMP_SKIRT, "tread"))
    for share in (0.35, 0.65):
        parts.append(shapes.cylinder((left[0] * share, left[1] * share, 0.0), (left[0] * share, left[1] * share, -0.004),
                                     0.011, CAMP_RIB, 12, "bolt"))
    return parts


def dome_opening_frame(size, laid):
    """An opening in the lining: the quilted lintel over it to the wall's top, the rigid frame round it standing into
    the room and out, a seal along its inside, the top band."""
    wide, tall, deep = size
    arc = camp_arc_of(laid)
    opening, high = arc.get("opening", (2.4, 2.6))
    parts = [camp_quilt_box((-wide / 2, high, 0.0), (wide / 2, tall, CAMP_SKIN), "quilt")]
    # Both outlines run on down under the deck, so their rounded lower corners never leave a sliver at its foot.
    outline = camp_window_outline(-opening / 2 - CAMP_FRAME, -0.3, opening / 2 + CAMP_FRAME, high + CAMP_FRAME, 0.05)
    hole = camp_window_outline(-opening / 2, -0.6, opening / 2, high, 0.03)
    frame = shapes.prism(outline, -CAMP_FRAME_IN, CAMP_SKIN + CAMP_FRAME_IN, CAMP_RIB, "frame")
    shapes.cut(frame, shapes.prism(hole, -1.0, 1.0, CAMP_RIB, "cutter"))
    parts.append(shapes.bevelled(frame, 0.006))
    for x in (-opening / 2 + 0.014, opening / 2 - 0.014):
        parts.append(shapes.box((x - 0.012, 0.0, 0.0), (x + 0.012, high - 0.04, CAMP_SKIN), CAMP_SKIRT, "seal"))
    parts.append(shapes.box((-opening / 2 + 0.04, high - 0.028, 0.0), (opening / 2 - 0.04, high - 0.004, CAMP_SKIN), CAMP_SKIRT, "seal"))
    return camp_lining_layers(wide, parts, with_skirting=False, top=tall)


def passage_lining(size, laid):
    """The way through between the domes: quilted sides and ceiling, skirting, and its deck; open at both ends. Its
    origin at the middle of its door dome end on the deck, z along it (x across)."""
    arc = camp_arc_of(laid)
    length, wide, tall = arc["length"], arc["wide"], arc["tall"]
    parts = []
    for side in (-1.0, 1.0):
        inner = side * wide / 2
        parts.append(camp_quilt_box((min(inner, inner + side * CAMP_SKIN), -0.05, 0.0), (max(inner, inner + side * CAMP_SKIN), tall,
                                                                               length), "quilt"))
        parts.append(shapes.box((min(inner, inner - side * CAMP_SKIRTING_IN), 0.0, 0.0),
                                (max(inner, inner - side * CAMP_SKIRTING_IN), CAMP_SKIRTING_TALL, length), CAMP_SKIRT, "skirting"))
    parts.append(camp_quilt_box((-wide / 2 - CAMP_SKIN, tall, 0.0), (wide / 2 + CAMP_SKIN, tall + CAMP_SKIN, length), "quilt"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2, -0.04, 0.0), (wide / 2, 0.0, length), CAMP_DECK, "deck"), CAMP_EDGE))
    return parts


def partition(size, laid):
    """The far dome's partition: composite panels either side of its doorway and over it, a rigid frame round the
    doorway, a cap along its top and skirting along both feet. Its origin at its first end on the deck, x along it."""
    arc = camp_arc_of(laid)
    length, tall, thick = arc["length"], arc["tall"], arc["thick"]
    door_at, (door_wide, door_tall) = arc["door_at"], arc["door"]
    door_from, door_to = door_at - door_wide / 2, door_at + door_wide / 2
    parts = []
    for start, end in ((0.0, door_from), (door_to, length)):
        seams = max(1, round((end - start) / 1.2))
        for index in range(seams):
            left = start + (end - start) * index / seams
            right = start + (end - start) * (index + 1) / seams
            parts.append(shapes.bevelled(shapes.box((left + 0.004, 0.0, -thick / 2), (right - 0.004, tall, thick / 2),
                                                    CAMP_PANEL, "panel"), 0.006))
    parts.append(shapes.bevelled(shapes.box((door_from, door_tall, -thick / 2), (door_to, tall, thick / 2), CAMP_PANEL,
                                            "panel"), 0.006))
    outline = camp_window_outline(door_from - 0.08, -0.01, door_to + 0.08, door_tall + 0.08, 0.04)
    hole = camp_window_outline(door_from, -0.2, door_to, door_tall, 0.02)
    frame = shapes.prism(outline, -thick / 2 - 0.04, thick / 2 + 0.04, CAMP_RIB, "frame")
    shapes.cut(frame, shapes.prism(hole, -1.0, 1.0, CAMP_RIB, "cutter"))
    parts.append(shapes.bevelled(frame, 0.005))
    parts.append(shapes.bevelled(shapes.box((0.0, tall, -thick / 2 - 0.02), (length, tall + 0.06, thick / 2 + 0.02),
                                            CAMP_RIB, "cap"), 0.005))
    for start, end in ((0.0, door_from - 0.08), (door_to + 0.08, length)):
        for side in (-1.0, 1.0):
            low, high = sorted((side * thick / 2, side * (thick / 2 + 0.03)))
            parts.append(shapes.box((start, 0.0, low), (end, 0.16, high), CAMP_SKIRT, "skirting"))
    return parts


def rod_lamp(size, laid):
    """A lamp on a rod from the ceiling: the rod, a round housing and its lens underneath. Its origin under the lens."""
    wide, tall, deep = size
    housing = 0.12
    parts = [shapes.cylinder((0.0, housing, 0.0), (0.0, tall, 0.0), 0.015, CAMP_RIB, 12, "rod")]
    parts.append(shapes.bevelled(shapes.cylinder((0.0, 0.02, 0.0), (0.0, housing, 0.0), wide / 2, CAMP_HOUSING, 32, "housing"),
                                 0.01))
    parts.append(shapes.cylinder((0.0, 0.0, 0.0), (0.0, 0.02, 0.0), wide / 2 - 0.03, CAMP_LENS, 32, "lens"))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, tall - 0.02, 0.0), (0.0, tall, 0.0), 0.05, CAMP_RIB, 16, "rose"), 0.004))
    return parts


# --- the shell outside ---------------------------------------------------------------------------------------------

def camp_shell_profile(arc):
    """The shell's profile from its foot up the wall and over the roof to its top, as (out, up) over the deck."""
    out, foot, shoulder, rise = arc["out"], arc["foot"], arc["shoulder"], arc["rise"]
    found = [(out, arc.get("from", foot)), (out, (arc.get("from", foot) + shoulder) / 2), (out, shoulder)]
    for step in range(1, 9):
        angle = math.pi / 2 * step / 8
        found.append((max(out * math.cos(angle), 0.02), shoulder + rise * math.sin(angle)))
    return found


def camp_shell_point(arc, out, up, degrees):
    """A point on the shell in a gore's frame: origin at the middle of its foot chord, x along, z into the dome."""
    angle = math.radians(degrees)
    return (out * math.sin(angle), up - arc["origin_height"], -(out * math.cos(angle) - arc["origin_radius"]))


def camp_shell_normal(degrees, rising):
    angle = math.radians(degrees)
    outward = np.array([math.sin(angle), 0.0, -math.cos(angle)])
    found = outward * (1.0 - rising) + np.array([0.0, rising, 0.0])
    return found / np.linalg.norm(found)


def camp_shell_sheet(arc, profile, low_degrees, high_degrees, thick, material, name, proud=0.0, columns=7):
    grid, normals = [], []
    top = arc["shoulder"]
    for out, up in profile:
        rising = 0.0 if up <= top + 1e-6 else min(1.0, (up - top) / max(arc["rise"], 0.1))
        row, row_normals = [], []
        for column in range(columns):
            degrees = low_degrees + (high_degrees - low_degrees) * column / (columns - 1)
            normal = camp_shell_normal(degrees, rising)
            row.append(tuple(np.asarray(camp_shell_point(arc, out, up, degrees)) + normal * proud))
            row_normals.append(tuple(-normal))
        grid.append(row)
        normals.append(row_normals)
    return camp_sheet(grid, normals, thick, material, name)


def shell_gore(size, laid):
    """A gore of the soft-goods shell from its foot (or over an opening, from `from`) over the roof to its top: woven
    fabric, a strap down its first edge and strap bands round it, and where the lining has a window, a rigid frame and
    dark glass in the window band."""
    arc = camp_arc_of(laid)
    half = arc["half"]
    profile = camp_shell_profile(arc)
    parts = []
    window = arc.get("window", False)
    if window:
        below = [point for point in profile if point[1] <= CAMP_WINDOW_LOW] + [(arc["out"], CAMP_WINDOW_LOW)]
        above = [(arc["out"], CAMP_WINDOW_HIGH)] + [point for point in profile if point[1] > CAMP_WINDOW_HIGH]
        parts.append(camp_shell_sheet(arc, below, -half, half, CAMP_SHELL_THICK, CAMP_SHELL, "fabric"))
        parts.append(camp_shell_sheet(arc, above, -half, half, CAMP_SHELL_THICK, CAMP_SHELL, "fabric"))
        inset = math.degrees(CAMP_WINDOW_INSET / arc["out"])
        band = [(arc["out"], CAMP_WINDOW_LOW), (arc["out"], CAMP_WINDOW_HIGH)]
        for low, high in ((-half, -half + inset), (half - inset, half)):
            parts.append(camp_shell_sheet(arc, band, low, high, CAMP_SHELL_THICK, CAMP_SHELL, "fabric", columns=3))
        parts.append(camp_shell_sheet(arc, band, -half + inset, half - inset, 0.02, CAMP_DARK_GLASS, "glass", proud=-0.02))
        rim = math.degrees(CAMP_FRAME / arc["out"])
        for low, high in ((-half + inset - rim, -half + inset), (half - inset, half - inset + rim)):
            parts.append(camp_shell_sheet(arc, [(arc["out"], CAMP_WINDOW_LOW - CAMP_FRAME), (arc["out"], CAMP_WINDOW_HIGH + CAMP_FRAME)], low, high,
                                     0.05, CAMP_RIB, "frame", proud=0.03, columns=2))
        for low, high in ((CAMP_WINDOW_LOW - CAMP_FRAME, CAMP_WINDOW_LOW), (CAMP_WINDOW_HIGH, CAMP_WINDOW_HIGH + CAMP_FRAME)):
            parts.append(camp_shell_sheet(arc, [(arc["out"], low), (arc["out"], high)], -half + inset - rim,
                                     half - inset + rim, 0.05, CAMP_RIB, "frame", proud=0.03, columns=5))
    else:
        parts.append(camp_shell_sheet(arc, profile, -half, half, CAMP_SHELL_THICK, CAMP_SHELL, "fabric"))
    strap = math.degrees(CAMP_STRAP_WIDE / 2 / arc["out"])
    parts.append(camp_shell_sheet(arc, profile[:-1], -half, -half + 2 * strap, 0.01, CAMP_PAD, "strap", proud=CAMP_STRAP_PROUD,
                             columns=2))
    for height in arc.get("bands", (0.9, 3.3)):
        if height < profile[0][1] or (window and CAMP_WINDOW_LOW - CAMP_FRAME < height < CAMP_WINDOW_HIGH + CAMP_FRAME):
            continue
        parts.append(camp_shell_sheet(arc, [(arc["out"], height - CAMP_STRAP_WIDE / 2), (arc["out"], height + CAMP_STRAP_WIDE / 2)],
                                 -half, half, 0.01, CAMP_PAD, "strap", proud=CAMP_STRAP_PROUD))
    return parts


def shell_gore_window(size, laid):
    laid = dict(laid, arc=dict(camp_arc_of(laid), window=True))
    return shell_gore(size, laid)


def shell_gore_open(size, laid):
    return shell_gore(size, laid)


def foot_ring(size, laid):
    """A stretch of the padded tube round a dome's foot, strap bands round it every metre."""
    arc = camp_arc_of(laid)
    half, middle, high, thick = arc["half"], arc["middle"], arc["high"], arc["thick"]
    around = 12
    columns = max(3, int(2 * half / 4) + 2)
    points, faces = [], []
    for column in range(columns):
        degrees = -half + 2 * half * column / (columns - 1)
        for step in range(around):
            turn = 2 * math.pi * step / around
            out = middle + thick * math.cos(turn)
            points.append(camp_shell_point(dict(arc, origin_height=arc["origin_height"]), out, high + thick * math.sin(turn),
                                      degrees))
    for column in range(columns - 1):
        for step in range(around):
            one = column * around + step
            two = column * around + (step + 1) % around
            faces.append([one, two, two + around, one + around])
    faces.append(list(range(around)))
    faces.append([(columns - 1) * around + step for step in reversed(range(around))])
    parts = [shapes.bevelled(camp_solid_from(points, faces, CAMP_PAD, "pad"), 0.0)]
    length = math.radians(2 * half) * middle
    bands = max(1, round(length / 1.0))
    for band in range(bands):
        degrees = -half + 2 * half * (band + 0.5) / bands
        points, faces = [], []
        for side, width in enumerate((-CAMP_STRAP_WIDE / 2, CAMP_STRAP_WIDE / 2)):
            shift = math.degrees(width / middle)
            for step in range(around):
                turn = 2 * math.pi * step / around
                out = middle + (thick + CAMP_STRAP_PROUD) * math.cos(turn)
                points.append(camp_shell_point(arc, out, high + (thick + CAMP_STRAP_PROUD) * math.sin(turn), degrees + shift))
        for step in range(around):
            following = (step + 1) % around
            faces.append([step, following, following + around, step + around])
        inner = [(middle + (thick - 0.03) * math.cos(2 * math.pi * step / around),
                  high + (thick - 0.03) * math.sin(2 * math.pi * step / around)) for step in range(around)]
        start = len(points)
        for side, width in enumerate((-CAMP_STRAP_WIDE / 2, CAMP_STRAP_WIDE / 2)):
            shift = math.degrees(width / middle)
            for out, up in inner:
                points.append(camp_shell_point(arc, out, up, degrees + shift))
        for step in range(around):
            following = (step + 1) % around
            faces.append([start + following, start + step, start + step + around, start + following + around])
            faces.append([step, start + step, start + following, following])
            faces.append([step + around, following + around, start + following + around, start + step + around])
        parts.append(camp_solid_from(points, faces, CAMP_PAD, "strap"))
    return parts


def passage_hull(size, laid):
    """The soft-goods hull over the way through: its two sides and roof, strap bands round it. Its origin at the
    middle of its door dome end on the deck, z along it."""
    arc = camp_arc_of(laid)
    length, half, top, foot = arc["length"], arc["half_wide"], arc["top"], arc["foot"]
    parts = []
    for side in (-1.0, 1.0):
        low, high = sorted((side * half, side * (half + CAMP_SHELL_THICK)))
        parts.append(shapes.box((low, foot, 0.0), (high, top, length), CAMP_SHELL, "fabric"))
    parts.append(shapes.box((-half - CAMP_SHELL_THICK, top, 0.0), (half + CAMP_SHELL_THICK, top + CAMP_SHELL_THICK, length), CAMP_SHELL,
                            "fabric"))
    for along in np.linspace(0.25, length - 0.25, max(2, round(length / 0.8))):
        for side in (-1.0, 1.0):
            low, high = sorted((side * (half + CAMP_SHELL_THICK), side * (half + CAMP_SHELL_THICK + CAMP_STRAP_PROUD)))
            parts.append(shapes.box((low, foot, along - CAMP_STRAP_WIDE / 2), (high, top + CAMP_SHELL_THICK, along + CAMP_STRAP_WIDE / 2),
                                    CAMP_PAD, "strap"))
        parts.append(shapes.box((-half - CAMP_SHELL_THICK - CAMP_STRAP_PROUD, top + CAMP_SHELL_THICK, along - CAMP_STRAP_WIDE / 2),
                                (half + CAMP_SHELL_THICK + CAMP_STRAP_PROUD, top + CAMP_SHELL_THICK + CAMP_STRAP_PROUD, along + CAMP_STRAP_WIDE / 2),
                                CAMP_PAD, "strap"))
    return parts


# --- the furniture code builds (method B: holders with every part their close-up shows) ----------------------------

def pedestal_table(size, laid):
    """The mess table: a stainless top with rounded edges on one round pedestal, a collar under the top and a round
    foot plate."""
    wide, tall, deep = size
    top = 0.04
    parts = [shapes.bevelled(shapes.box((-wide / 2, tall - top, -deep / 2), (wide / 2, tall, deep / 2),
                                        "brushed_steel_fine", "top"), 0.012)]
    parts.append(shapes.cylinder((0.0, 0.02, 0.0), (0.0, tall - top, 0.0), 0.06, "brushed_steel_fine", 32, "pedestal"))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, 0.0, 0.0), (0.0, 0.025, 0.0), 0.3, CAMP_BAND, 48, "foot"), 0.006))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, tall - top - 0.03, 0.0), (0.0, tall - top, 0.0), 0.12,
                                                 "brushed_steel_fine", 32, "collar"), 0.004))
    return parts


def camp_shelving(size, boards, material="anodized_natural"):
    """An open shelf: four uprights, flat boards at the given tops, a label strip on each board's front edge."""
    wide, tall, deep = size
    post = 0.035
    board = 0.025
    parts = []
    for x in (-wide / 2 + post / 2, wide / 2 - post / 2):
        for z in (-deep / 2 + post / 2, deep / 2 - post / 2):
            parts.append(shapes.bevelled(shapes.box((x - post / 2, 0.0, z - post / 2), (x + post / 2, tall, z + post / 2),
                                                    material, "upright"), 0.004))
    for top in boards:
        parts.append(shapes.bevelled(shapes.box((-wide / 2 + post, top - board, -deep / 2 + 0.005),
                                                (wide / 2 - post, top, deep / 2 - 0.005), material, "board"), 0.003))
        parts.append(shapes.box((-wide / 2 + post + 0.05, top - board + 0.004, -deep / 2 - 0.004),
                                (wide / 2 - post - 0.05, top - 0.004, -deep / 2 + 0.006), CAMP_BAND, "strip"))
    return parts


def sample_shelf(size, laid):
    return camp_shelving(size, (0.15, 0.63, 1.11, 1.59))


def stores_rack(size, laid):
    return camp_shelving(size, (0.12, 0.6, 1.08, 1.56))


def hygiene(size, laid):
    """The hygiene cubicle: composite walls with rounded upright corners, a two-leaf folding door in its front with a
    slim handle, a round vent fan on its roof and a sign plate on the door."""
    wide, tall, deep = size
    corner = 0.08
    parts = []
    for x in (-wide / 2 + corner, wide / 2 - corner):
        for z in (-deep / 2 + corner, deep / 2 - corner):
            parts.append(shapes.cylinder((x, 0.0, z), (x, tall, z), corner, CAMP_PANEL, 24, "corner"))
    parts.append(shapes.box((-wide / 2 + corner, 0.0, -deep / 2 + 0.02), (wide / 2 - corner, tall, deep / 2), CAMP_PANEL,
                            "wall"))
    parts.append(shapes.box((-wide / 2, 0.0, -deep / 2 + corner), (wide / 2, tall, deep / 2 - corner), CAMP_PANEL, "wall"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + corner, tall - 0.04, -deep / 2 + corner),
                                            (wide / 2 - corner, tall, deep / 2 - corner), CAMP_PANEL, "roof"), 0.01))
    door = wide - 2 * corner - 0.08
    for side in (-1.0, 1.0):
        left, right = sorted((0.0, side * door / 2))
        parts.append(shapes.bevelled(shapes.box((left + 0.006, 0.06, -deep / 2 - 0.004), (right - 0.006, tall - 0.12,
                                                                                         -deep / 2 + 0.02),
                                                CAMP_HOUSING, "door"), 0.004))
    parts.append(shapes.bevelled(shapes.box((-door / 2 + 0.06, 0.9, -deep / 2 - 0.03), (-door / 2 + 0.085, 1.25,
                                                                                       -deep / 2 - 0.004),
                                            CAMP_RIB, "handle"), 0.003))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, tall, 0.0), (0.0, tall + 0.08, 0.0), 0.16, CAMP_HOUSING, 32,
                                                 "vent"), 0.006))
    parts.append(shapes.ring((0.0, tall + 0.08, 0.0), (0.0, tall + 0.09, 0.0), 0.14, 0.05, CAMP_RIB, 32, "grille"))
    parts.append(label(door / 4, 1.62, 0.26, 0.07, -deep / 2 - 0.004, "label_hygiene"))
    return parts


def floor_cable(size, laid):
    """Power cables run loose over the deck, two side by side wandering a little, a plug block at one end. Laid on
    the deck, its length along x, the cables lying on it."""
    wide, tall, deep = size
    radius = 0.011
    parts = []
    for lane, phase in ((-0.025, 0.0), (0.025, 1.7)):
        steps = 14
        points = [(-wide / 2 + wide * step / steps, radius,
                   lane + 0.06 * math.sin(phase + 5.0 * step / steps) * (1.0 if step not in (0, steps) else 0.3))
                  for step in range(steps + 1)]
        parts += [shapes.cylinder(start, end, radius, "cable_black", 10, "cable") for start, end in zip(points, points[1:])]
    parts.append(shapes.bevelled(shapes.box((wide / 2 - 0.05, 0.0, -0.05), (wide / 2 + 0.05, 0.05, 0.05), CAMP_PANEL,
                                            "plug"), 0.006))
    return parts


def crate(size, laid):
    """A cargo crate: the case's build at a crate's size (body, lid, seam band, latches, handle, stencil)."""
    return case(size, laid)


def ring_lamp(size, laid):
    """A ring lamp on the ceiling, as the concept picks show them: a housing ring and a glowing lens ring under it, held
    by three short struts. Laid facing down (its front, -z, into the room)."""
    wide = size[0]
    outer, inner = wide / 2, wide / 2 - 0.07
    parts = [shapes.bevelled(shapes.ring((0.0, 0.0, -0.02), (0.0, 0.0, 0.04), outer, inner, CAMP_RIB, 48, "housing"), 0.006),
             shapes.ring((0.0, 0.0, -0.045), (0.0, 0.0, -0.02), outer - 0.015, inner + 0.015, CAMP_LENS, 48, "lens")]
    for at in range(3):
        angle = 2 * math.pi * at / 3
        x, y = (outer - 0.035) * math.cos(angle), (outer - 0.035) * math.sin(angle)
        parts.append(shapes.cylinder((x, y, 0.04), (x, y, 0.12), 0.008, CAMP_RIB, 8, "strut"))
    return parts


def wall_net(size, laid):
    """A soft storage net on the lining: a webbing frame with two rows of three fabric pockets, a few of them full.
    Its back on the wall (+z), front into the room."""
    wide, tall, deep = size
    strap = 0.035
    parts = []
    for y in (0.0, tall - strap):
        parts.append(shapes.box((-wide / 2, y, deep / 2 - 0.012), (wide / 2, y + strap, deep / 2), CAMP_PAD, "frame"))
    for x in (-wide / 2, wide / 2 - strap):
        parts.append(shapes.box((x, 0.0, deep / 2 - 0.012), (x + strap, tall, deep / 2), CAMP_PAD, "frame"))
    rows, columns = 2, 3
    for row in range(rows):
        for column in range(columns):
            left = -wide / 2 + strap + (wide - 2 * strap) * column / columns + 0.015
            right = -wide / 2 + strap + (wide - 2 * strap) * (column + 1) / columns - 0.015
            bottom = strap + (tall - 2 * strap) * row / rows + 0.02
            top = strap + (tall - 2 * strap) * (row + 1) / rows - 0.02
            full = (row + column) % 2 == 0
            front = -deep / 2 if full else -deep / 2 + deep * 0.45
            parts.append(shapes.bevelled(shapes.box((left, bottom, front), (right, top - (tall * 0.08 if full else 0.0),
                                                                            deep / 2 - 0.012), "canvas_beige" if full
                                                    else CAMP_PAD, "pocket"), 0.012))
            parts.append(shapes.box((left, top - 0.03, front - 0.006), (right, top - 0.012, front + 0.004), CAMP_PAD,
                                    "strap"))
    return parts


def crate_small(size, laid):
    """A small crate, as a bedside table or a footstool: the case's build at its size."""
    return case(size, laid)


def case(size, laid):
    """A hard cargo case: a body with rounded edges, its lid's seam band, two latches and a carry handle on the front,
    and a stencilled number on the lid's front."""
    wide, tall, deep = size
    lid = tall * 0.72
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, lid - 0.005, deep / 2), CAMP_PANEL,
                                        "body"), 0.02),
             shapes.bevelled(shapes.box((-wide / 2, lid + 0.005, -deep / 2), (wide / 2, tall, deep / 2), CAMP_PANEL,
                                        "lid"), 0.02),
             shapes.box((-wide / 2 + 0.01, lid - 0.018, -deep / 2 - 0.014), (wide / 2 - 0.01, lid + 0.018,
                                                                             -deep / 2 + 0.01), CAMP_SKIRT, "seam"),
             shapes.box((-wide / 2 + 0.01, lid - 0.018, deep / 2 - 0.01), (wide / 2 - 0.01, lid + 0.018,
                                                                           deep / 2 + 0.014), CAMP_SKIRT, "seam")]
    for side in (-1.0, 1.0):
        low, high = sorted((side * (wide / 2 - 0.01), side * (wide / 2 + 0.014)))
        parts.append(shapes.box((low, lid - 0.018, -deep / 2 + 0.01), (high, lid + 0.018, deep / 2 - 0.01), CAMP_SKIRT,
                                "seam"))
    for x in (-wide / 2 + 0.08, wide / 2 - 0.08):
        parts.append(shapes.bevelled(shapes.box((x - 0.025, lid - 0.05, -deep / 2 - 0.02), (x + 0.025, lid + 0.03,
                                                                                            -deep / 2 - 0.004),
                                                CAMP_RIB, "latch"), 0.003))
    parts.append(shapes.bevelled(shapes.box((-0.08, lid - 0.13, -deep / 2 - 0.035), (0.08, lid - 0.11, -deep / 2 - 0.004),
                                            CAMP_RIB, "handle"), 0.004))
    parts.append(label(0.0, lid + (tall - lid) / 2, 0.16, 0.06, -deep / 2 - 0.0, "stencil_case"))
    return parts


def comms_desk(size, laid):
    """The comms desk: a composite top, a cabinet of three drawers with pulls under its left end (the kit's +x, the
    viewer's left), a side panel at its right end, a modesty panel at the back and a cable grommet in the top."""
    wide, tall, deep = size
    top_thick = 0.04
    under = tall - top_thick
    cabinet = 0.45
    parts = [shapes.bevelled(shapes.box((-wide / 2, under, -deep / 2), (wide / 2, tall, deep / 2), CAMP_PANEL, "top"), 0.01)]
    left = wide / 2 - cabinet
    parts.append(shapes.bevelled(shapes.box((left, 0.0, -deep / 2 + 0.02), (left + cabinet, under, deep / 2), CAMP_PANEL,
                                            "cabinet"), 0.008))
    parts.append(shapes.bevelled(shapes.box((-wide / 2, 0.0, -deep / 2 + 0.02), (-wide / 2 + 0.04, under, deep / 2), CAMP_PANEL,
                                            "side"), 0.006))
    parts.append(shapes.box((-wide / 2 + 0.04, 0.25, deep / 2 - 0.03), (left, under, deep / 2 - 0.01), CAMP_PANEL,
                            "back"))
    drawer = (under - 0.06) / 3
    for index in range(3):
        bottom = 0.04 + drawer * index
        parts.append(shapes.bevelled(shapes.box((left + 0.02, bottom + 0.006, -deep / 2),
                                                (left + cabinet - 0.02, bottom + drawer - 0.006, -deep / 2 + 0.02),
                                                "brushed_steel_fine", "drawer"), 0.004))
        parts.append(shapes.bevelled(shapes.box((left + cabinet / 2 - 0.08, bottom + drawer - 0.06, -deep / 2 - 0.02),
                                                (left + cabinet / 2 + 0.08, bottom + drawer - 0.04, -deep / 2),
                                                CAMP_RIB, "pull"), 0.003))
    parts.append(shapes.ring((-0.3, tall - 0.0005, deep / 2 - 0.12), (-0.3, tall + 0.004, deep / 2 - 0.12), 0.035, 0.022,
                             CAMP_BAND, 24, "grommet"))
    return parts


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


# ---- Workshop round (2026-10-07), block ws_bench: the workshop's robot bench, its arm monitors, the equipment bench,
# the low cabinet run, the floor service socket and the machine bay's corner mark, built in code with library surfaces
# as method B's parts check allows, each as its clean close-up shows it. A holder never carries the loose objects on
# it: the arm monitors and the keyboard on the robot bench are children of their own (composites), and the bench's
# middle and its left end stay clear and flat for the game's turning table and parts tray. Helpers are prefixed
# `ws_bench_`.

WS_BENCH_ROBOT_TOP = 0.95  # the robot bench's working height (a standing bench)
WS_BENCH_CLAMP_X = 0.8  # the screen arms' clamp blocks, either side of the middle
WS_BENCH_CLAMP_RISE = 0.035  # how far a clamp block stands over the top (the arm's foot sits on it)
WS_BENCH_EQUIPMENT_TOP = 0.9
WS_BENCH_STRIP = 0.08  # a bay mark's strip width


def ws_bench_bar(start, end, thick, x_from, x_to, material, name):
    """A straight flat bar in the kit's side plane between two (z, y) points, `thick` across its length and running
    across x from `x_from` to `x_to`: an arm link of an articulated stand."""
    run = (end[0] - start[0], end[1] - start[1])
    length = math.hypot(*run)
    side = (-run[1] / length * thick / 2, run[0] / length * thick / 2)
    outline = [(start[0] + side[0], start[1] + side[1]), (end[0] + side[0], end[1] + side[1]),
               (end[0] - side[0], end[1] - side[1]), (start[0] - side[0], start[1] - side[1])]
    return furn_prism(outline, "x", x_from, x_to, material, name)


def ws_bench_hinge(across, high, front, name="hinge"):
    """A small butt hinge on a door's edge at depth `front`: a leaf on the face and its knuckle."""
    return [shapes.box((across - 0.012, high - 0.03, front - 0.004), (across + 0.012, high + 0.03, front),
                       "bare_steel", name),
            shapes.cylinder((across, high - 0.032, front - 0.006), (across, high + 0.032, front - 0.006), 0.0055,
                            "bare_steel", 10, name)]


def ws_bench_drawers(right, left, spans, face, front):
    """A stack of drawer fronts between x `right` and `left`, one per (low, high) span, each with a bar pull across
    it; their backs on the carcass face at depth `face`, their fronts at `front`."""
    parts = []
    for low, high in spans:
        parts.append(shapes.bevelled(shapes.box((right + 0.012, low, front), (left - 0.012, high, face),
                                                "painted_panel", "drawer"), 0.002))
        pull_y = high - min(0.06, (high - low) / 2)
        parts += furn_pull((right + left) / 2, pull_y, 0.12, front, upright=False)
    return parts


def ws_bench_pedestal(right, left, top, front, back):
    """One drawer bank of the robot bench between x `right` and `left`: a dark plinth, the carcass, a shallow pencil
    drawer under the top and four drawers, the lowest one deep."""
    face = front + 0.02
    parts = [shapes.box((right + 0.03, 0.0, face + 0.02), (left - 0.03, 0.08, back - 0.02), "dark_panel", "plinth"),
             shapes.bevelled(shapes.box((right, 0.08, face), (left, top, back), "painted_panel", "pedestal"), EDGE)]
    spans = ((0.1, 0.4), (0.405, 0.555), (0.56, 0.71), (0.715, 0.865))
    parts += ws_bench_drawers(right, left, spans, face, front)
    parts.append(shapes.bevelled(shapes.box((right + 0.012, 0.87, front), (left - 0.012, top - 0.008, face),
                                            "painted_panel", "pencil_drawer"), 0.002))
    return parts


def ws_bench_gooseneck(base_x, base_z, top):
    """The robot bench's ring lamp: a round foot plate on the cable tray at the back edge's middle, a gooseneck
    rising and bending forward over the top's middle, and a ring head there with its glowing lens under it."""
    bend_y, bend = top + 0.2, 0.18
    centre_z = base_z - bend
    parts = [shapes.bevelled(shapes.cylinder((base_x, top + 0.006, base_z), (base_x, top + 0.06, base_z), 0.032,
                                             "dark_panel", 24, "lamp_base"), 0.002),
             shapes.cylinder((base_x, top + 0.06, base_z), (base_x, bend_y, base_z), 0.012, "pipe_steel", 12,
                             "gooseneck"),
             floor_bent_tube((base_x, bend_y, centre_z), (0, 0, 1), (0, 1, 0), bend, 0.012, 0.0, 160.0, "pipe_steel",
                             "gooseneck", steps=16, sides=12)]
    end_z = centre_z + bend * math.cos(math.radians(160.0))
    end_y = bend_y + bend * math.sin(math.radians(160.0))
    head_y, head_z = end_y - 0.05, end_z - 0.1
    parts.append(shapes.cylinder((base_x, end_y, end_z), (base_x, head_y + 0.03, head_z + 0.105), 0.012, "pipe_steel",
                                 12, "gooseneck"))
    parts.append(shapes.bevelled(shapes.ring((base_x, head_y, head_z), (base_x, head_y + 0.035, head_z), 0.11, 0.07,
                                             "painted_panel", 32, "lamp_head"), 0.003))
    parts.append(shapes.cylinder((base_x, head_y + 0.006, head_z), (base_x, head_y + 0.026, head_z), 0.072,
                                 "lamp_lens", 32, "lens"))
    return parts


def ws_bench_clamp(across, top, back):
    """A screen arm's clamp block on the robot bench's back edge: a block on the top, its jaw down the top's back edge
    and two bolt heads on it (the arm's own clamp foot sits on it)."""
    rise = WS_BENCH_CLAMP_RISE
    parts = [shapes.bevelled(shapes.box((across - 0.05, top, back - 0.1), (across + 0.05, top + rise, back),
                                        "painted_panel", "clamp_block"), 0.003),
             shapes.bevelled(shapes.box((across - 0.05, top - 0.08, back), (across + 0.05, top + rise, back + 0.01),
                                        "painted_panel", "clamp_block"), 0.002)]
    for side in (-1, 1):
        parts.append(shapes.cylinder((across + side * 0.032, top + rise, back - 0.05),
                                     (across + side * 0.032, top + rise + 0.006, back - 0.05), 0.009, "bare_steel", 12,
                                     "bolt"))
    return parts


def ws_bench_cable_tray(span, top, back):
    """The cable tray along the robot bench's back edge: a pan on the top, a lip at its front and a slotted back wall
    standing up from it."""
    near = back - 0.08
    wall = shapes.box((-span, top, back - 0.006), (span, top + 0.07, back), "galvanized_steel", "cable_tray")
    count = 14
    for at in range(count):
        slot_x = -span + 0.06 + (2 * span - 0.12) * at / (count - 1)
        furn_cut_box(wall, (slot_x - 0.02, top + 0.03, back - 0.02), (slot_x + 0.02, top + 0.042, back + 0.01))
    return [shapes.box((-span, top, near), (span, top + 0.006, back), "galvanized_steel", "cable_tray"),
            shapes.box((-span, top, near), (span, top + 0.035, near + 0.006), "galvanized_steel", "cable_tray"),
            wall]


def robot_bench(size, laid):
    """The robot assembly bench, as its close-up shows it: a standing steel bench, its brushed top on a drawer bank
    at each end (a pencil drawer over four drawers with bar pulls), an open middle bay with a back panel and an apron
    under the top's front, a cable tray along the back edge, the gooseneck ring lamp rising from the back edge's middle
    over the top's middle, and two clamp blocks on the back edge for the screen arms. The top's middle (1.0 x 0.6 m)
    and its left end (+x, 0.6 m wide, from the front to 0.35 m behind the middle) stay clear and flat for the game's
    turning table and parts tray; the screen arms and the keyboard are children of their own. The lamp stands over the
    laid height: the bench is 0.95 m to its top, the lamp's bend about 1.34 m."""
    wide, tall, deep = size
    top = WS_BENCH_ROBOT_TOP
    front, back = -deep / 2, deep / 2 - 0.01
    body = front + 0.03  # the drawer fronts' face (they stand 2 cm proud of the pedestals)
    parts = [shapes.bevelled(shapes.box((-wide / 2, top - 0.04, front), (wide / 2, top, back), "brushed_steel_fine",
                                        "top"), EDGE)]
    pedestal = 0.56
    for right, left in ((wide / 2 - 0.02 - pedestal, wide / 2 - 0.02), (-wide / 2 + 0.02, -wide / 2 + 0.02 + pedestal)):
        parts += ws_bench_pedestal(right, left, top - 0.04, body, back - 0.01)
    inner = wide / 2 - 0.02 - pedestal
    parts.append(shapes.bevelled(shapes.box((-inner, 0.08, back - 0.04), (inner, top - 0.04, back - 0.015),
                                            "painted_panel", "back_panel"), 0.002))
    parts.append(shapes.bevelled(shapes.box((-inner, top - 0.1, body), (inner, top - 0.04, body + 0.03),
                                            "painted_panel", "apron"), 0.002))
    parts.append(label(0.0, top - 0.07, 0.24, 0.04, body, "label_robot_bay"))
    parts.append(label(-wide / 2 + 0.02 + pedestal / 2, 0.886, 0.14, 0.024, body, "label_tools"))
    parts.append(label(wide / 2 - 0.02 - pedestal / 2, 0.886, 0.14, 0.024, body, "label_storage_a"))
    parts += ws_bench_cable_tray(WS_BENCH_CLAMP_X - 0.08, top, back)
    parts += ws_bench_gooseneck(0.0, back - 0.04, top)
    for side in (-1, 1):
        parts += ws_bench_clamp(side * WS_BENCH_CLAMP_X, top, back)
    parts += ws_bench_table_and_tray(top)
    return parts


# Where the game's robot bench (game/base/bench/bench.tscn, on the room's middle, its front to the south) turns its
# robot and lays its parts, in the made bench's frame (its x is the room's -x, its z the room's -z): the turning table
# round the top's middle, 0.3 m to the viewer's right, and the parts tray on the left end.
WS_BENCH_TABLE = (-0.3, 0.0, 0.35, 0.04)  # x, z, radius, height over the top
WS_BENCH_TRAY = (0.68, -0.06, 0.76, 1.02, 0.03)  # x, z, wide, deep, height over the top


def ws_bench_table_and_tray(top):
    """The bench's turning table, a plain steel disc the game's robot stands on (the game turns the robot, the disc
    reads the same however it turns), and the parts tray's rubber mat with a raised lip, the game's parts lying on it."""
    table_x, table_z, radius, high = WS_BENCH_TABLE
    parts = [shapes.bevelled(shapes.cylinder((table_x, top, table_z), (table_x, top + high, table_z), radius,
                                             "bare_steel", 64, "turntable"), 0.004)]
    tray_x, tray_z, wide, deep, tall = WS_BENCH_TRAY
    low, high_corner = (tray_x - wide / 2, top, tray_z - deep / 2), (tray_x + wide / 2, top + tall, tray_z + deep / 2)
    parts.append(shapes.bevelled(shapes.box(low, high_corner, "rubber", "tray_mat"), 0.004))
    return parts


def arm_monitor(size, laid):
    """A screen on an articulated arm, as its close-up shows it: a clamp foot block with its label, a swivel collar,
    a lower link of twin flat bars with a gas spring under them, an elbow joint, an upper link to a tilt joint, a mount
    plate on the screen's back, and the screen (a steel case, its bezel and glowing glass facing -z, DATA MONITOR and a
    row of buttons on the case under it); its foot's middle at the origin."""
    wide, tall, deep = size
    front = -deep / 2
    base, elbow, head = (0.0, 0.13), (deep / 2 - 0.045, 0.42), (front + 0.085, tall - 0.19)  # (z, y)
    parts = [shapes.bevelled(shapes.box((-0.05, 0.0, -0.05), (0.05, 0.07, 0.05), "painted_panel", "clamp_foot"),
                             0.004),
             label(0.0, 0.035, 0.085, 0.034, -0.05, "label_clamp_foot"),
             shapes.bevelled(shapes.cylinder((0.0, 0.07, 0.0), (0.0, 0.1, 0.0), 0.03, "bare_steel", 24, "swivel"),
                             0.002),
             shapes.box((-0.03, 0.1, -0.025), (0.03, base[1], 0.025), "painted_panel", "swivel")]
    for x_from, x_to in ((-0.03, -0.012), (0.012, 0.03)):
        parts.append(ws_bench_bar(base, elbow, 0.035, x_from, x_to, "painted_panel", "lower_arm"))
    run = (elbow[0] - base[0], elbow[1] - base[1])
    length = math.hypot(*run)
    under = (run[1] / length * 0.03, -run[0] / length * 0.03)
    spring_from = (base[0] + run[0] * 0.15 + under[0], base[1] + run[1] * 0.15 + under[1])
    spring_to = (base[0] + run[0] * 0.85 + under[0], base[1] + run[1] * 0.85 + under[1])
    parts.append(shapes.cylinder((0.0, spring_from[1], spring_from[0]), (0.0, spring_to[1], spring_to[0]), 0.008,
                                 "bare_steel", 12, "spring"))
    parts.append(ws_bench_bar(elbow, head, 0.04, -0.022, 0.022, "painted_panel", "upper_arm"))
    for (joint_z, joint_y), radius, half in ((base, 0.032, 0.036), (elbow, 0.04, 0.04), (head, 0.03, 0.03)):
        parts.append(shapes.bevelled(shapes.cylinder((-half, joint_y, joint_z), (half, joint_y, joint_z), radius,
                                                     "bare_steel", 24, "joint"), 0.002))
        for side in (-1, 1):
            parts.append(shapes.cylinder((side * half, joint_y, joint_z), (side * (half + 0.005), joint_y, joint_z),
                                         radius * 0.4, "bare_steel", 12, "bolt"))
    case_front, case_back = front + 0.008, front + 0.05
    parts.append(shapes.box((-0.05, head[1] - 0.05, case_back), (0.05, head[1] + 0.05, head[0] - 0.02), "dark_panel",
                            "mount"))
    low = tall - 0.34
    parts.append(shapes.bevelled(shapes.box((-wide / 2, low, case_front), (wide / 2, tall, case_back), "bare_steel",
                                            "case"), 0.004))
    parts += wall_screen_part(0.0, low + 0.04 + 0.145, wide - 0.02, 0.29, case_front, "screen", rim=0.016)
    parts.append(label(0.12, low + 0.02, 0.15, 0.024, case_front, "label_data_monitor"))
    parts += [wall_button(-0.09 - 0.022 * at, low + 0.02, 0.012, 0.008, case_front) for at in range(5)]
    return parts


def ws_bench_socket(across, high, front, squared):
    """One switched power outlet on a face at depth `front`: a white plate with its round recess and two pin holes
    (or a squared outlet's slots), a rocker switch beside it and a POWER label over it."""
    plate = shapes.box((across - 0.045, high - 0.045, front - 0.012), (across + 0.045, high + 0.045, front),
                       "plastic_white", "socket")
    if squared:
        for side in (-1, 1):
            pin_x = across + side * 0.015
            furn_cut_box(plate, (pin_x - 0.004, high - 0.012, front - 0.02), (pin_x + 0.004, high + 0.012,
                                                                              front - 0.006))
    else:
        shapes.cut(plate, shapes.cylinder((across, high, front - 0.02), (across, high, front - 0.006), 0.03, "rubber",
                                          32, "cutter"))
        for side in (-1, 1):
            pin_x = across + side * 0.01
            shapes.cut(plate, shapes.cylinder((pin_x, high, front - 0.01), (pin_x, high, front - 0.002), 0.0045,
                                              "rubber", 12, "cutter"))
    switch_x = across - 0.07
    return [shapes.bevelled(plate, 0.002),
            shapes.bevelled(shapes.box((switch_x - 0.015, high - 0.025, front - 0.008), (switch_x + 0.015, high + 0.025,
                                                                                       front), "dark_panel", "switch"),
                            0.0015),
            shapes.bevelled(shapes.box((switch_x - 0.009, high - 0.016, front - 0.016), (switch_x + 0.009, high + 0.016,
                                                                                       front - 0.008), "plastic_grey",
                                       "switch"), 0.001),
            label(across, high + 0.066, 0.075, 0.022, front, "label_power")]


def equipment_bench(size, laid):
    """The equipment bench, as its close-up shows it: a thick worn steel top on a closed steel cabinet (four drawers
    at the viewer's left, a wide drawer over a pair of doors in the middle, a drawer over a door at the viewer's
    right, bar pulls and hinges, a dark plinth), and a back panel rising to 1.4 m between sloped cheeks with a copper
    bus bar bolted along it, a stepped band of six switched power outlets each under a POWER label, and a small
    readout screen at the band's right end."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    top = WS_BENCH_EQUIPMENT_TOP
    face = front + 0.04  # the carcass face; the fronts stand 2 cm proud of it
    fronts = face - 0.02
    parts = [shapes.bevelled(shapes.box((-wide / 2, top - 0.05, front), (wide / 2, top, back - 0.11), "bare_steel",
                                        "top"), 0.006),
             shapes.box((-wide / 2 + 0.03, 0.0, face + 0.03), (wide / 2 - 0.03, 0.07, back - 0.03), "dark_panel",
                        "plinth"),
             shapes.bevelled(shapes.box((-wide / 2 + 0.02, 0.07, face), (wide / 2 - 0.02, top - 0.05, back - 0.02),
                                        "painted_panel", "carcass"), EDGE)]
    bank = (wide / 2 - 0.54, wide / 2 - 0.04)
    parts += ws_bench_drawers(bank[0], bank[1], ((0.09, 0.4), (0.405, 0.56), (0.565, 0.7), (0.705, 0.83)), face,
                              fronts)
    for right, left, doors in ((-0.34, bank[0] - 0.02, 2), (-wide / 2 + 0.04, -0.36, 1)):
        parts += ws_bench_drawers(right, left, ((0.705, 0.83),), face, fronts)
        door_wide = (left - right - 0.024 - 0.006 * (doors - 1)) / doors
        for door in range(doors):
            door_right = right + 0.012 + door * (door_wide + 0.006)
            door_left = door_right + door_wide
            parts.append(shapes.bevelled(shapes.box((door_right, 0.09, fronts), (door_left, 0.69, face),
                                                    "painted_panel", "door"), 0.002))
            hinge_left = doors == 1 or door == 1  # the hinge on the door's outer edge, the pull by the other
            hinge_x = door_left - 0.012 if hinge_left else door_right + 0.012
            pull_x = door_right + 0.05 if hinge_left else door_left - 0.05
            parts += furn_pull(pull_x, 0.42, 0.12, fronts)
            for high in (0.17, 0.6):
                parts += ws_bench_hinge(hinge_x, high, fronts)
    # The back panel between its sloped cheeks, the stepped outlet band along its foot.
    panel_front = back - 0.08
    band_front = panel_front - 0.03
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + 0.04, top, panel_front), (wide / 2 - 0.04, tall - 0.02,
                                                                                    back - 0.04), "painted_panel",
                                            "back_panel"), 0.003))
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + 0.04, top, band_front), (wide / 2 - 0.04, top + 0.22,
                                                                                   panel_front), "painted_panel",
                                            "socket_band"), 0.003))
    cheek = [(back - 0.14, top), (back, top), (back, tall), (back - 0.06, tall), (back - 0.14, top + 0.1)]
    for x_from, x_to in ((-wide / 2, -wide / 2 + 0.04), (wide / 2 - 0.04, wide / 2)):
        parts.append(shapes.bevelled(furn_prism(cheek, "x", x_from, x_to, "painted_panel", "cheek"), 0.003))
    bar_y = top + 0.36
    parts.append(shapes.bevelled(shapes.box((-0.72, bar_y - 0.025, panel_front - 0.012), (0.72, bar_y + 0.025,
                                                                                           panel_front),
                                            "anodized_gold", "bus_bar"), 0.002))
    parts += [shapes.cylinder((x, bar_y, panel_front - 0.012), (x, bar_y, panel_front - 0.02), 0.014, "bare_steel", 6,
                              "bolt") for x in (-0.66, 0.0, 0.66)]
    for at in range(6):
        parts += ws_bench_socket(wide / 2 - 0.16 - 0.215 * at, top + 0.09, band_front, at == 0)
    parts += wall_screen_part(-wide / 2 + 0.2, top + 0.115, 0.24, 0.1, band_front, "screen", rim=0.012)
    return parts


def low_cabinet(size, laid):
    """The low steel cabinet run, as its close-up shows it: a carcass with a flat top on a recessed kick plate, four
    hinged doors in two pairs, each door a frame round a raised field, a recessed oval handle by the pair's meeting
    edge, hinges at each pair's outer edges, and a label on two doors."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    face = front + 0.02
    parts = [shapes.box((-wide / 2 + 0.03, 0.0, face + 0.03), (wide / 2 - 0.03, 0.08, back - 0.03), "dark_panel",
                        "kick_plate"),
             shapes.bevelled(shapes.box((-wide / 2, 0.08, face), (wide / 2, tall, back), "painted_panel", "carcass"),
                             EDGE)]
    margin, gap = 0.02, 0.008
    door_wide = (wide - 2 * margin - 3 * gap) / 4
    door_low, door_high = 0.1, tall - 0.025
    field = front - 0.006
    for door in range(4):
        right = -wide / 2 + margin + door * (door_wide + gap)  # the door's -x edge (the viewer's right)
        left = right + door_wide
        plate = shapes.bevelled(shapes.box((right, door_low, front), (left, door_high, face), "painted_panel", "door"),
                                0.002)
        panel = shapes.bevelled(shapes.box((right + 0.045, door_low + 0.045, field), (left - 0.045, door_high - 0.045,
                                                                                      front), "painted_panel",
                                           "door_panel"), 0.002)
        meets_left = door % 2 == 0  # each pair meets in its own middle: the first door's meeting edge is its +x one
        handle_x = left - 0.085 if meets_left else right + 0.085
        handle_y = (door_low + door_high) / 2
        hole = rounded_outline((handle_x - 0.028, handle_y - 0.055), (handle_x + 0.028, handle_y + 0.055), 0.024)
        for piece in (plate, panel):
            shapes.cut(piece, shapes.prism(hole, field - 0.02, face - 0.006, "rubber", "cutter"))
        parts += [plate, panel]
        parts.append(shapes.bevelled(rounded_ring((handle_x - 0.034, handle_y - 0.061),
                                                  (handle_x + 0.034, handle_y + 0.061), 0.03, 0.006, field - 0.004,
                                                  field, "bare_steel", "handle"), 0.001))
        hinge_x = right - 0.002 if meets_left else left + 0.002
        for high in (door_low + 0.12, door_high - 0.12):
            parts += ws_bench_hinge(hinge_x, high, front)
    for door, variant in ((0, "label_tools"), (3, "label_storage_a")):
        middle = -wide / 2 + margin + door * (door_wide + gap) + door_wide / 2
        parts.append(label(middle, door_high - 0.11, 0.16, 0.04, field, variant))
    return parts


def ws_bench_floor_socket_lying(size, laid):
    """A floor service socket lying on the deck like a tread mat, its front (-z) its top, its whole depth standing
    proud of the deck, as its close-up shows it shut: a bolted rim frame, the checker-plate lid flush in it with a
    finger slot by its near edge (y = 0) and its hinge knuckles along the far edge, and a POWER / COOLANT label on
    the rim's near side."""
    wide, long, deep = size
    top, bottom = -deep / 2, deep / 2
    rim = 0.035
    parts = floor_frame((-wide / 2, 0.0), (wide / 2, long), top, bottom, rim, "painted_panel", "rim")
    lid = shapes.bevelled(shapes.box((-wide / 2 + rim + 0.003, rim + 0.003, top),
                                     (wide / 2 - rim - 0.003, long - rim - 0.003, bottom), "chequer_plate_steel",
                                     "lid"), 0.002)
    slot_y = rim + 0.03
    furn_cut_box(lid, (-0.045, slot_y - 0.009, top - 0.01), (0.045, slot_y + 0.009, top + 0.012))
    parts += [lid,
              shapes.box((-0.045, slot_y - 0.009, top + 0.008), (0.045, slot_y + 0.009, top + 0.012), "dark_panel",
                         "finger_slot")]
    hinge_y = long - rim - 0.003
    for knuckle_x in (-0.08, 0.08):
        parts.append(shapes.cylinder((knuckle_x - 0.035, hinge_y, top + 0.001),
                                     (knuckle_x + 0.035, hinge_y, top + 0.001), 0.005, "bare_steel", 12, "hinge"))
    parts += [screw(x, y, top) for x in (-wide / 2 + rim / 2, wide / 2 - rim / 2) for y in (rim / 2, long - rim / 2)]
    parts.append(label(0.0, rim / 2, 0.16, 0.022, top, "label_power_coolant"))
    return parts


def ws_bench_bay_mark_lying(size, laid):
    """A machine bay's corner mark painted on the deck, lying like a tread mat (front -z up): an L of two strips
    WS_BENCH_STRIP wide running the piece's full width and length; the L's knee is the corner at +x, y = 0 (the
    viewer's left near corner), its arms running toward -x and toward +y. The layout lays four of it turned about up
    so the knees sit at the bay's corners."""
    wide, long, deep = size
    strip = WS_BENCH_STRIP
    outline = [(wide / 2, 0.0), (wide / 2, long), (wide / 2 - strip, long), (wide / 2 - strip, strip),
               (-wide / 2, strip), (-wide / 2, 0.0)]
    return [shapes.bevelled(furn_prism(outline, "z", -deep / 2, deep / 2, "enamel_white", "paint"), 0.001)]


def ws_bench_upright(parts, long, deep):
    """Parts built lying like a tread mat (their front -z up, their length along +y from 0, `deep` thick) stood up as
    a floor piece: foot on the floor at y = 0, top at `deep`, the lying near edge (y = 0) at the front (-z)."""
    stand = Matrix.Translation((0.0, long / 2, deep / 2)) @ Matrix.Rotation(math.radians(90.0), 4, "X")
    for part in parts:
        part.data.transform(stand)
    return parts


def floor_socket(size, laid):
    """The floor socket standing on the deck (size wide, tall, deep: its top `tall` over the floor), built lying."""
    wide, tall, deep = size
    return ws_bench_upright(ws_bench_floor_socket_lying((wide, deep, tall), laid), deep, tall)


def bay_mark(size, laid):
    """The bay's corner mark standing on the deck (its paint `tall` thick), built lying: its knee at the +x front
    corner, its arms toward -x and toward the back (+z)."""
    wide, tall, deep = size
    return ws_bench_upright(ws_bench_bay_mark_lying((wide, deep, tall), laid), deep, tall)


# ---- Workshop round (2026-10-07), block ws_tools: the workshop's hand-tool bench, bench vise, shop stool, spares
# shelving and the crates and boxes on it, built in code with library surfaces as method B's parts check allows, each
# as its clean close-up shows it. A holder never carries the loose objects on it: the vise and the desk lamp on the
# tool bench, the crates and boxes on the shelves are children of their own, placed on purpose (composites). Helpers
# are prefixed `ws_tools_`.

WS_TOOLS_BENCH_TOP = 0.06  # the tool bench's timber top: thick, worn boards
WS_TOOLS_LEG = 0.05  # the bench frame's square tube
WS_TOOLS_DRAWER_UNIT = 0.48  # how wide the bench's drawer unit is, under the viewer's right end
# The shelving unit's shelf tops, foot up; the last is the unit's top.
WS_TOOLS_SHELVES = (0.12, 0.565, 1.01, 1.455, 1.9)
WS_TOOLS_ANGLE = 0.04  # a shelving post's angle flange, across
WS_TOOLS_SHEET = 0.005  # the shelving's sheet and angle thickness
WS_TOOLS_SHELF_LIP = 0.035  # how far a shelf's edges turn down
WS_TOOLS_CRATE_RIM = 0.235  # the crate's rim, where its lid sits


def ws_tools_cut_all(part, cutters):
    """A part with every one of `cutters` taken out of it in one cut (a post's row of slots, a crate's hand holes)."""
    shapes.cut(part, shapes.joined(cutters, "cutter"))
    return part


def ws_tools_bench_frame(wide, deep, top):
    """The tool bench's welded frame: four square-tube legs on foot plates, a rail under the top all round and a
    stretcher round the foot."""
    under = top - WS_TOOLS_BENCH_TOP
    leg_x = wide / 2 - 0.05
    leg_z = deep / 2 - 0.05
    parts = []
    for x in (-leg_x, leg_x - WS_TOOLS_LEG):
        for z in (-leg_z, leg_z - WS_TOOLS_LEG):
            parts.append(shapes.bevelled(shapes.box((x, 0.006, z), (x + WS_TOOLS_LEG, under, z + WS_TOOLS_LEG),
                                                    "painted_panel", "leg"), 0.003))
            parts.append(shapes.bevelled(shapes.box((x - 0.01, 0.0, z - 0.01), (x + WS_TOOLS_LEG + 0.01, 0.006,
                                                                               z + WS_TOOLS_LEG + 0.01),
                                                    "dark_panel", "foot"), 0.0015))
    for low_y, high_y, name in ((under - 0.06, under, "rail"), (0.12, 0.16, "stretcher")):
        for z in (-leg_z, leg_z - 0.03):
            parts.append(shapes.bevelled(shapes.box((-leg_x + WS_TOOLS_LEG, low_y, z),
                                                    (leg_x - WS_TOOLS_LEG, high_y, z + 0.03), "painted_panel", name),
                                         0.002))
        for x in (-leg_x, leg_x - WS_TOOLS_LEG):
            parts.append(shapes.bevelled(shapes.box((x + 0.01, low_y, -leg_z + WS_TOOLS_LEG),
                                                    (x + WS_TOOLS_LEG - 0.01, high_y, leg_z - WS_TOOLS_LEG),
                                                    "painted_panel", name), 0.002))
    return parts


def ws_tools_drawer_unit(right, left, low, high, front, back, labels):
    """The bench's steel drawer unit between x `right` and `left`, hung under the top: its carcass and as many drawers
    as `labels`, top down, each with a bar pull and its label."""
    face = front + 0.015
    parts = [shapes.bevelled(shapes.box((right, low, face), (left, high, back), "painted_panel", "drawer_unit"), EDGE)]
    gap = 0.008
    drawer_tall = (high - low - 0.02 - gap * (len(labels) - 1)) / len(labels)
    middle = (right + left) / 2
    for at, variant in enumerate(labels):
        drawer_top = high - 0.01 - at * (drawer_tall + gap)
        drawer_low = drawer_top - drawer_tall
        parts.append(shapes.bevelled(shapes.box((right + 0.01, drawer_low, front), (left - 0.01, drawer_top, face),
                                                "painted_panel", "drawer"), 0.002))
        parts += furn_pull(middle, drawer_low + 0.045, 0.16, front, upright=False, name="pull")
        parts.append(label(middle, drawer_top - 0.032, 0.13, 0.036, front, variant))
    return parts


def tool_bench(size, laid):
    """The heavy hand-tool bench, as its close-up shows it: a thick worn timber top on a welded square-tube frame (legs
    on foot plates, a rail under the top all round, a stretcher round the foot), a three-drawer steel unit hung under
    the viewer's right end with bar pulls and labels, and a low sheet shelf over the stretchers under the other end.
    Its top is left clear for the vise and the desk lamp (children of their own)."""
    wide, tall, deep = size
    under = tall - WS_TOOLS_BENCH_TOP
    parts = [shapes.bevelled(shapes.box((-wide / 2, under, -deep / 2), (wide / 2, tall, deep / 2), "wood_board",
                                        "top"), 0.006)]
    parts += ws_tools_bench_frame(wide, deep, tall)
    leg_x = wide / 2 - 0.05
    leg_z = deep / 2 - 0.05
    right = -leg_x + WS_TOOLS_LEG
    parts += ws_tools_drawer_unit(right, right + WS_TOOLS_DRAWER_UNIT, 0.3, under - 0.06, -leg_z,
                                  leg_z - 0.03, ("label_tools", "label_wrenches", "label_sockets"))
    shelf_from = -0.02
    shelf_to = leg_x - WS_TOOLS_LEG
    parts += [shapes.bevelled(shapes.box((shelf_from, 0.16, -leg_z), (shelf_to, 0.166, leg_z), "painted_panel",
                                         "shelf"), 0.0015),
              shapes.bevelled(shapes.box((shelf_from - 0.006, 0.13, -leg_z + 0.03), (shelf_from, 0.166, leg_z - 0.03),
                                         "painted_panel", "shelf"), 0.0015)]
    return parts


def ws_tools_vise_base(half, middle_z):
    """The vise's swivel base: a round cast foot with a bolt lug each side (a real hole through each), the turntable
    on it and the swivel lock's boss and pin on the viewer's left."""
    parts = [shapes.bevelled(shapes.cylinder((0.0, 0.0, middle_z), (0.0, 0.03, middle_z), 0.085, "cast_iron_dark", 40,
                                             "base"), 0.003)]
    for side in (-1, 1):
        lug = shapes.bevelled(shapes.box((min(side * 0.05, side * half), 0.0, middle_z - 0.035),
                                         (max(side * 0.05, side * half), 0.016, middle_z + 0.035), "cast_iron_dark",
                                         "lug"), 0.003)
        hole_x = side * (half - 0.022)
        shapes.cut(lug, shapes.cylinder((hole_x, -0.01, middle_z), (hole_x, 0.03, middle_z), 0.009, "rubber", 20,
                                        "cutter"))
        parts.append(lug)
    parts += [shapes.bevelled(shapes.cylinder((0.0, 0.03, middle_z), (0.0, 0.045, middle_z), 0.07, "cast_steel", 40,
                                              "swivel"), 0.002),
              shapes.bevelled(shapes.box((0.062, 0.026, middle_z - 0.012), (0.094, 0.05, middle_z + 0.012),
                                         "cast_steel", "swivel_lock"), 0.002),
              shapes.cylinder((0.087, 0.038, middle_z - 0.045), (0.087, 0.038, middle_z + 0.045), 0.0045, "bare_steel",
                              12, "lock_pin")]
    parts += [wall_sphere((0.087, 0.038, middle_z + side * 0.045), 0.007, "bare_steel", "lock_pin", 12)
              for side in (-1, 1)]
    return parts


def ws_tools_vise_screw(half, front, axis_y):
    """The vise's lead screw out of the sliding jaw's boss, the handle's hub on its end and the T-bar through the hub
    with a ball at each end."""
    bar_z = front + 0.013
    parts = [shapes.cylinder((0.0, axis_y, front + 0.025), (0.0, axis_y, front + 0.06), 0.009, "bare_steel", 16,
                             "lead_screw"),
             shapes.bevelled(shapes.cylinder((0.0, axis_y, front), (0.0, axis_y, front + 0.028), 0.016, "cast_steel",
                                             20, "handle_hub"), 0.002),
             shapes.cylinder((-half + 0.0105, axis_y, bar_z), (half - 0.0105, axis_y, bar_z), 0.0055, "bare_steel",
                             12, "handle")]
    parts += [wall_sphere((side * (half - 0.0105), axis_y, bar_z), 0.0105, "bare_steel", "handle_knob", 16)
              for side in (-1, 1)]
    return parts


def vise(size, laid):
    """A cast bench vise, its jaws opening toward the front, as its close-up shows it: a swivel base with two bolt
    lugs and a swivel lock, the fixed jaw's casting with an anvil behind, the sliding jaw on its slide, a steel jaw
    plate on each jaw with its screws, and the lead screw with a T-bar handle out the front."""
    wide, tall, deep = size
    half, front, back = wide / 2, -deep / 2, deep / 2
    axis_y = 0.095  # the lead screw's height
    parts = ws_tools_vise_base(half, 0.04)
    body = furn_prism([(0.02, 0.045), (0.125, 0.045), (0.135, 0.06), (0.135, 0.15), (0.02, 0.15)], "x", -0.055, 0.055,
                      "cast_steel", "body")
    parts += [shapes.bevelled(body, 0.004),
              shapes.bevelled(shapes.box((-0.085, 0.15, 0.02), (0.085, tall - 0.005, 0.07), "cast_steel",
                                         "fixed_jaw"), 0.003),
              shapes.bevelled(shapes.box((-0.045, 0.15, 0.07), (0.045, 0.175, back), "cast_steel", "anvil"), 0.003),
              shapes.bevelled(shapes.box((-0.035, 0.07, -0.085), (0.035, 0.12, back - 0.005), "cast_steel", "slide"),
                              0.002),
              shapes.bevelled(furn_prism([(-0.1, 0.07), (-0.026, 0.07), (-0.026, 0.15), (-0.075, 0.15), (-0.1, 0.125)],
                                         "x", -0.05, 0.05, "cast_steel", "sliding_jaw"), 0.004),
              shapes.bevelled(shapes.box((-0.085, 0.15, -0.08), (0.085, tall - 0.005, -0.026), "cast_steel",
                                         "sliding_jaw"), 0.003),
              shapes.bevelled(shapes.cylinder((0.0, axis_y, -0.112), (0.0, axis_y, -0.098), 0.022, "cast_steel", 24,
                                              "screw_boss"), 0.002)]
    for near, far in ((0.012, 0.02), (-0.026, -0.018)):
        parts.append(shapes.bevelled(shapes.box((-0.08, 0.15, near), (0.08, tall, far), "bare_steel", "jaw_plate"),
                                     0.001))
    for x in (-0.05, 0.05):
        parts.append(shapes.cylinder((x, 0.178, -0.08), (x, 0.178, -0.084), 0.005, "bare_steel", 10, "plate_screw"))
    parts += ws_tools_vise_screw(half, front, axis_y)
    return parts


def ws_tools_stool_thread(bottom, top, core):
    """The stool's height adjuster: a screw column `core` thick with a thread ridge every 12 mm up it."""
    parts = [shapes.cylinder((0.0, bottom, 0.0), (0.0, top, 0.0), core, "bare_steel", 20, "screw")]
    ridges = int((top - bottom - 0.01) / 0.012)
    for at in range(ridges):
        high = bottom + 0.008 + at * 0.012
        parts.append(shapes.cylinder((0.0, high, 0.0), (0.0, high + 0.004, 0.0), core + 0.0035, "bare_steel", 20,
                                     "thread"))
    return parts


def work_stool(size, laid):
    """A steel shop stool, as its close-up shows it: a round padded seat on a steel pan, the screw height adjuster
    under it, a hub the four splayed tube legs are welded to, a foot ring round the legs and a rubber foot on each."""
    wide, tall, deep = size
    seat = min(wide, deep) / 2 - 0.03
    foot_out = min(wide, deep) / 2 - 0.022
    hub_low, hub_high = 0.36, 0.44
    parts = [shapes.bevelled(shapes.cylinder((0.0, tall - 0.05, 0.0), (0.0, tall, 0.0), seat, "vinyl_seat", 48,
                                             "cushion"), 0.012),
             shapes.bevelled(shapes.cylinder((0.0, tall - 0.072, 0.0), (0.0, tall - 0.05, 0.0), seat + 0.004,
                                             "dark_panel", 48, "seat_pan"), 0.003),
             shapes.bevelled(shapes.cylinder((0.0, tall - 0.1, 0.0), (0.0, tall - 0.072, 0.0), 0.045, "dark_panel", 24,
                                             "seat_boss"), 0.003),
             shapes.bevelled(shapes.cylinder((0.0, hub_low, 0.0), (0.0, hub_high, 0.0), 0.04, "painted_panel", 24,
                                             "hub"), 0.004)]
    parts += ws_tools_stool_thread(hub_high, tall - 0.1, 0.015)
    ring_y = 0.22
    share = (hub_low + 0.02 - ring_y) / (hub_low + 0.02 - 0.03)
    ring_out = (0.03 + (foot_out - 0.03) * share) * math.sqrt(2.0)
    parts.append(floor_bent_tube((0.0, ring_y, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0), ring_out, 0.009, 0.0, 360.0,
                                 "bare_steel", "foot_ring", steps=40, sides=12))
    for side_x in (-1, 1):
        for side_z in (-1, 1):
            parts.append(shapes.cylinder((side_x * 0.03, hub_low + 0.02, side_z * 0.03),
                                         (side_x * foot_out, 0.03, side_z * foot_out), 0.0125, "painted_panel", 16,
                                         "leg"))
            parts.append(shapes.bevelled(shapes.cylinder((side_x * foot_out, 0.0, side_z * foot_out),
                                                         (side_x * foot_out, 0.032, side_z * foot_out), 0.022,
                                                         "rubber", 20, "rubber_foot"), 0.003))
    return parts


def ws_tools_post(corner_x, corner_z, tall):
    """One shelving post at a corner: a slotted steel angle, one flange across the front or back and one along the
    side, both outside the shelves, a row of real slots up each."""
    side_x = 1 if corner_x > 0 else -1
    side_z = 1 if corner_z > 0 else -1
    inner_x = corner_x - side_x * WS_TOOLS_ANGLE
    inner_z = corner_z - side_z * WS_TOOLS_ANGLE
    skin_x = corner_x - side_x * WS_TOOLS_SHEET
    skin_z = corner_z - side_z * WS_TOOLS_SHEET
    across = shapes.box((min(corner_x, inner_x), 0.0, min(corner_z, skin_z)),
                        (max(corner_x, inner_x), tall, max(corner_z, skin_z)), "dark_panel", "post")
    along = shapes.box((min(corner_x, skin_x), 0.0, min(skin_z, inner_z)),
                       (max(corner_x, skin_x), tall, max(skin_z, inner_z)), "dark_panel", "post")
    slot_x = corner_x - side_x * WS_TOOLS_ANGLE * 0.55
    slot_z = corner_z - side_z * WS_TOOLS_ANGLE * 0.55
    rows = np.arange(0.06, tall - 0.04, 0.05)
    ws_tools_cut_all(across, [shapes.box((slot_x - 0.004, high - 0.008, corner_z - 0.02),
                                         (slot_x + 0.004, high + 0.008, corner_z + 0.02), "rubber", "cutter")
                              for high in rows])
    ws_tools_cut_all(along, [shapes.box((corner_x - 0.02, high - 0.008, slot_z - 0.004),
                                        (corner_x + 0.02, high + 0.008, slot_z + 0.004), "rubber", "cutter")
                             for high in rows])
    return [across, along]


def ws_tools_shelf(half_x, half_z, top):
    """One sheet steel shelf between the posts, its top at `top`, its edges turned down all round."""
    under = top - WS_TOOLS_SHEET
    lip = top - WS_TOOLS_SHELF_LIP
    edge = 0.004
    return [shapes.bevelled(shapes.box((-half_x, under, -half_z), (half_x, top, half_z), "painted_panel", "shelf"),
                            0.0015),
            shapes.box((-half_x, lip, -half_z), (half_x, under, -half_z + edge), "painted_panel", "shelf"),
            shapes.box((-half_x, lip, half_z - edge), (half_x, under, half_z), "painted_panel", "shelf"),
            shapes.box((-half_x, lip, -half_z + edge), (-half_x + edge, under, half_z - edge), "painted_panel",
                       "shelf"),
            shapes.box((half_x - edge, lip, -half_z + edge), (half_x, under, half_z - edge), "painted_panel",
                       "shelf")]


def ws_tools_brace(left_x, right_x, low, high, back):
    """A flat steel bar crossing the back of one bay, from its lower `left_x` corner to its upper `right_x`."""
    long = math.hypot(right_x - left_x, high - low)
    bar = shapes.box((-long / 2, -0.012, back - 0.004), (long / 2, 0.012, back), "bare_steel", "brace")
    turn = math.degrees(math.atan2(high - low, right_x - left_x))
    turned(bar, (0.0, 0.0), -turn)
    return floor_moved(bar, ((left_x + right_x) / 2, (low + high) / 2, 0.0))


def spares_shelves(size, laid):
    """A steel shelving unit, as its close-up shows it: four slotted angle posts, five sheet shelves with turned-down
    edges bolted inside them, flat bars crossed at the back of two bays, a label on the middle shelf's edge. Its
    shelves are left clear for the crates and boxes (children of their own)."""
    wide, tall, deep = size
    half_x, half_z = wide / 2, deep / 2 - 0.0055  # the bolt heads in front and the braces behind keep in the depth
    parts = []
    for corner_x in (-half_x, half_x):
        for corner_z in (-half_z, half_z):
            parts += ws_tools_post(corner_x, corner_z, tall)
    inner_x = half_x - WS_TOOLS_SHEET
    inner_z = half_z - WS_TOOLS_SHEET
    for top in WS_TOOLS_SHELVES:
        parts += ws_tools_shelf(inner_x, inner_z, top)
        for x in (-half_x + WS_TOOLS_ANGLE * 0.5, half_x - WS_TOOLS_ANGLE * 0.5):
            parts.append(bolt(x, top - WS_TOOLS_SHELF_LIP / 2, -half_z))
    back = half_z + 0.004
    for bay in (1, 3):
        low = WS_TOOLS_SHELVES[bay] + 0.01
        high = WS_TOOLS_SHELVES[bay + 1] - WS_TOOLS_SHELF_LIP - 0.01
        parts.append(ws_tools_brace(-inner_x + 0.03, inner_x - 0.03, low, high, back))
        parts.append(ws_tools_brace(inner_x - 0.03, -inner_x + 0.03, low, high, back))
    middle = WS_TOOLS_SHELVES[2]
    parts.append(label(0.0, middle - WS_TOOLS_SHELF_LIP / 2, 0.14, 0.026, -inner_z, "label_spares"))
    return parts


def ws_tools_crate_ribs(wall_x, wall_z, low, high):
    """The crate's moulded ribs: upright ribs down its long sides and its ends, and a post at each corner."""
    out = 0.006
    parts = []
    for x in (-0.21, -0.075, 0.075, 0.21):
        for face in (-wall_z, wall_z):
            parts.append(shapes.box((x - 0.006, low, min(face, face + math.copysign(out, face))),
                                    (x + 0.006, high, max(face, face + math.copysign(out, face))), "plastic_grey",
                                    "rib"))
    for z in (-0.13, 0.13):
        for face in (-wall_x, wall_x):
            parts.append(shapes.box((min(face, face + math.copysign(out, face)), low, z - 0.006),
                                    (max(face, face + math.copysign(out, face)), high, z + 0.006), "plastic_grey",
                                    "rib"))
    for side_x in (-1, 1):
        for side_z in (-1, 1):
            corner = (side_x * (wall_x + out), side_z * (wall_z + out))
            inner = (side_x * (wall_x - 0.012), side_z * (wall_z - 0.012))
            parts.append(shapes.bevelled(shapes.box((min(corner[0], inner[0]), low, min(corner[1], inner[1])),
                                                    (max(corner[0], inner[0]), high, max(corner[1], inner[1])),
                                                    "plastic_grey", "rib"), 0.002))
    return parts


def ws_tools_crate_lid(half_x, half_z, rim):
    """The crate's split lid: two hinged flaps meeting along the middle with a tab of one in a notch of the other, a
    raised lip round each flap's outer edges and the hinge knuckles along both long sides."""
    gap = 0.003
    top = rim + 0.012
    near = shapes.box((-half_x + 0.01, rim, -half_z + 0.008), (half_x - 0.01, top, -gap), "plastic_grey", "lid")
    far = shapes.box((-half_x + 0.01, rim, gap), (half_x - 0.01, top, half_z - 0.008), "plastic_grey", "lid")
    shapes.cut(far, shapes.box((-0.036, rim - 0.01, 0.0), (0.036, top + 0.01, 0.026), "rubber", "cutter"))
    parts = [shapes.bevelled(near, 0.002), shapes.bevelled(far, 0.002),
             shapes.bevelled(shapes.box((-0.03, rim, -gap), (0.03, top, 0.02), "plastic_grey", "lid"), 0.0015)]
    lip_top = top + 0.013
    for side in (-1, 1):
        outer = side * (half_z - 0.008)
        inner = side * (half_z - 0.016)
        parts.append(shapes.bevelled(shapes.box((-half_x + 0.01, top, min(outer, inner)),
                                                (half_x - 0.01, lip_top, max(outer, inner)), "plastic_grey",
                                                "lid_rim"), 0.002))
        for end in (-1, 1):
            outer_x = end * (half_x - 0.01)
            inner_x = end * (half_x - 0.018)
            parts.append(shapes.bevelled(shapes.box((min(outer_x, inner_x), top, min(side * gap, inner)),
                                                    (max(outer_x, inner_x), lip_top, max(side * gap, inner)),
                                                    "plastic_grey", "lid_rim"), 0.002))
        for x in (-0.17, 0.17):
            parts.append(shapes.cylinder((x - 0.03, rim + 0.006, side * (half_z - 0.004)),
                                         (x + 0.03, rim + 0.006, side * (half_z - 0.004)), 0.006, "plastic_grey", 12,
                                         "hinge"))
    return parts


def spares_crate(size, laid):
    """A grey stacking crate, as its close-up shows it: a moulded body with a rim, ribs and a foot band, a hand hole
    through each end, a label holder with its PARTS label on the front, and a split hinged lid with a raised lip."""
    wide, tall, deep = size
    half_x, half_z = wide / 2, deep / 2
    wall_x, wall_z = half_x - 0.01, half_z - 0.01
    rim = WS_TOOLS_CRATE_RIM
    body = shapes.bevelled(shapes.box((-wall_x, 0.0, -wall_z), (wall_x, rim, wall_z), "plastic_grey", "body"), 0.004)
    shapes.cut(body, shapes.box((-wall_x + 0.006, 0.006, -wall_z + 0.006), (wall_x - 0.006, rim + 0.05,
                                                                            wall_z - 0.006), "rubber", "cutter"))
    ws_tools_cut_all(body, [furn_prism(rounded_outline((-0.055, 0.15), (0.055, 0.19), 0.018), "x",
                                       side * (wall_x - 0.03), side * (wall_x + 0.03), "rubber", "cutter")
                            for side in (-1, 1)])
    rim_part = shapes.box((-half_x, rim - 0.022, -half_z), (half_x, rim, half_z), "plastic_grey", "rim")
    shapes.cut(rim_part, shapes.box((-wall_x + 0.006, rim - 0.05, -wall_z + 0.006),
                                    (wall_x - 0.006, rim + 0.05, wall_z - 0.006), "rubber", "cutter"))
    parts = [body, shapes.bevelled(rim_part, 0.003),
             shapes.bevelled(shapes.box((-wall_x - 0.004, 0.0, -wall_z - 0.004), (wall_x + 0.004, 0.014,
                                                                                 wall_z + 0.004), "plastic_grey",
                                        "foot"), 0.002)]
    parts += ws_tools_crate_ribs(wall_x, wall_z, 0.014, rim - 0.022)
    parts += [shapes.bevelled(rounded_ring((-0.058, 0.112), (0.058, 0.178), 0.006, 0.008, -wall_z - 0.006, -wall_z,
                                           "plastic_grey", "label_holder"), 0.001),
              label(0.0, 0.145, 0.096, 0.046, -wall_z, "label_parts")]
    parts += ws_tools_crate_lid(half_x, half_z, rim)
    return parts


def spares_box(size, laid):
    """A taped cardboard parts box, as its close-up shows it: the box, its two top flaps meeting along the middle,
    packing tape along the seam and down both ends and over a front corner, a shipping label and a part number."""
    wide, tall, deep = size
    half_x, half_z = wide / 2, deep / 2
    flaps = tall - 0.01
    parts = [shapes.bevelled(shapes.box((-half_x, 0.0, -half_z), (half_x, flaps, half_z), "canvas_beige", "body"),
                             0.003),
             shapes.bevelled(shapes.box((-half_x, flaps, -half_z), (half_x, flaps + 0.006, -0.0015), "canvas_beige",
                                        "flap"), 0.0015),
             shapes.bevelled(shapes.box((-half_x, flaps, 0.0015), (half_x, flaps + 0.006, half_z), "canvas_beige",
                                        "flap"), 0.0015),
             shapes.box((-half_x, flaps + 0.006, -0.03), (half_x, tall, 0.03), "rubber_grey", "tape")]
    for side in (-1, 1):
        parts.append(shapes.box((min(side * half_x, side * (half_x + 0.004)), flaps - 0.09, -0.03),
                                (max(side * half_x, side * (half_x + 0.004)), tall, 0.03), "rubber_grey", "tape"))
    parts += [shapes.box((half_x - 0.05, 0.0, -half_z - 0.004), (half_x, 0.07, -half_z), "rubber_grey", "tape"),
              shapes.box((half_x, 0.0, -half_z - 0.004), (half_x + 0.004, 0.07, -half_z + 0.05), "rubber_grey",
                         "tape"),
              label(-0.04, 0.083, 0.13, 0.13, -half_z, "note_ship_to"),
              label(-0.04, 0.176, 0.1, 0.05, -half_z, "stencil_part_number", name="decal")]
    return parts


# ---- Workshop round (2026-10-07), block ws_elec: the workshop's electronics bench and what stands on it (a bench
# scope, a bench multimeter, a soldering station), the parts cabinet and the pendant work lamp, built in code with
# library surfaces as method B's parts check allows, each as its clean close-up shows it. The bench never carries the
# loose instruments: they, the monitor, the keyboard and the desk lamp are children of their own, placed on purpose
# (composites) on the riser shelf and the top's back, the top's front left clear to work. Helpers are prefixed
# `ws_elec_`.

WS_ELEC_TOP = 0.71  # the electronics bench's top (a seated bench: the riser shelf over it keeps the whole 0.9 tall)
WS_ELEC_MAT = 0.004  # the anti-static mat lying on it; the instruments on the top stand on the mat
WS_ELEC_SHELF = 0.875  # the riser shelf's face, where the scope, the meter, the monitor and the lamp stand
WS_ELEC_SHELF_FRONT = 0.03  # the riser's front edge (z): under it the top is clear 0.15 m high for the keyboard
# The parts cabinet's bin drawers: eight across, five high, over a two-door cupboard this tall.
WS_ELEC_BINS = (8, 5)
WS_ELEC_CUPBOARD = 0.8
# The bins with a printed card (row from the bottom, column from the viewer's right), the rest carry blank cards.
WS_ELEC_BIN_LABELS = ((4, 1, "label_bolts"), (4, 6, "label_washers"), (3, 3, "label_nuts"), (2, 5, "label_screws"),
                      (1, 0, "label_fuses"), (0, 4, "label_resistors"))


def ws_elec_tube(points, thick, material, name, sides=8):
    """A round tube `thick` in radius swept along a path of kit-frame points (a coiled wire, a cable), capped at both
    ends; its cross-section carried along the path so it does not twist."""
    path = [Vector(point) for point in points]
    built = bmesh.new()
    rings = []
    normal = None
    for index, middle in enumerate(path):
        ahead = (path[min(index + 1, len(path) - 1)] - path[max(index - 1, 0)]).normalized()
        normal = ahead.orthogonal() if normal is None else normal - ahead * normal.dot(ahead)
        normal.normalize()
        side = ahead.cross(normal)
        rings.append([built.verts.new(shapes.to_blender(middle + (normal * math.cos(turn) + side * math.sin(turn))
                                                        * thick))
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


def ws_elec_lathe(profile, middle, material, name, sides=32):
    """A solid turned round the kit's up axis through `middle` (x, z): `profile` is a closed outline of (radius, y)
    points, a point on the axis (radius 0) turning to a single pole (a lamp's shade, a cup's bowl)."""
    built = bmesh.new()
    rows = []
    for radius, high in profile:
        if radius < 1e-6:
            rows.append([built.verts.new(shapes.to_blender((middle[0], high, middle[1])))])
            continue
        rows.append([built.verts.new(shapes.to_blender((middle[0] + radius * math.cos(2 * math.pi * at / sides), high,
                                                        middle[1] + radius * math.sin(2 * math.pi * at / sides))))
                     for at in range(sides)])
    for index, first in enumerate(rows):
        second = rows[(index + 1) % len(rows)]
        if len(first) == 1 and len(second) == 1:
            continue
        for at in range(sides):
            if len(first) == 1:
                built.faces.new([first[0], second[at], second[(at + 1) % sides]])
            elif len(second) == 1:
                built.faces.new([first[at], first[(at + 1) % sides], second[0]])
            else:
                built.faces.new([first[at], first[(at + 1) % sides], second[(at + 1) % sides], second[at]])
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def ws_elec_lying(parts, x, high, z):
    """Parts built upright facing the front (their back at depth 0, their middle at x 0, y 0) laid face up on a top
    at height `high`, their middle at (x, z), reading upright to someone in front of it."""
    for part in parts:
        floor_moved(tilted(part, (0.0, 0.0), 90.0), (x, high, z))
    return parts


def ws_elec_knob(x, y, face, radius, name="knob", material="anodized_black", reach=0.016):
    """A round control knob standing out of a face at depth `face`."""
    return shapes.bevelled(shapes.cylinder((x, y, face), (x, y, face - reach), radius, material, 14, name), 0.002)


def ws_elec_drawer(right, left, low, high, front, face):
    """One pedestal drawer of the electronics bench between x `right` and `left`: its front with a recessed finger
    pocket near its top and the pull's lip over the pocket."""
    drawer = shapes.box((right, low, front), (left, high, face), "painted_panel", "drawer")
    middle = (right + left) / 2
    furn_cut_box(drawer, (middle - 0.06, high - 0.055, front - 0.01), (middle + 0.06, high - 0.03, front + 0.007))
    return [shapes.bevelled(drawer, 0.002),
            shapes.bevelled(shapes.box((middle - 0.066, high - 0.036, front - 0.006), (middle + 0.066, high - 0.028,
                                                                                       front + 0.007),
                                       "bare_steel", "pull"), 0.0015)]


def ws_elec_power_strip(top, panel):
    """The power strip under the riser shelf on its back panel (front face at depth `panel`): its housing, three
    rocker switches (one red) at the viewer's left and seven sockets with their pin slots."""
    face = panel - 0.025
    parts = [shapes.bevelled(shapes.box((-0.62, top + 0.04, face), (0.62, top + 0.1, panel), "dark_panel",
                                        "power_strip"), 0.003)]
    for at, x in enumerate((0.56, 0.5, 0.44)):
        parts.append(wall_button(x, top + 0.07, 0.026, 0.034, face, "anodized_red" if at == 0 else "anodized_black",
                                 "switch"))
    for at in range(7):
        x = 0.33 - 0.14 * at
        plate = shapes.box((x - 0.026, top + 0.045, face - 0.008), (x + 0.026, top + 0.095, face), "plastic_white",
                           "socket")
        for side in (-1, 1):
            furn_cut_box(plate, (x + side * 0.009 - 0.0025, top + 0.066, face - 0.02),
                         (x + side * 0.009 + 0.0025, top + 0.082, face - 0.004))
        furn_cut_box(plate, (x - 0.004, top + 0.052, face - 0.02), (x + 0.004, top + 0.06, face - 0.004))
        parts.append(shapes.bevelled(plate, 0.0015))
    return parts


def elec_bench(size, laid):
    """The electronics bench, as its close-up shows it: a steel top on four square legs with rails under it, a back
    stretcher and a side stretcher, a pale grey anti-static mat with rounded corners on the top, a two-drawer
    pedestal with finger-pocket pulls under the viewer's left end, and a shelf riser across the back (end posts, a
    shelf with a lip at its back and ends, a back panel) with the power strip under it (switches, sockets) and its
    labels. The scope, the meter, the soldering station, the monitor, the keyboard and the desk lamp are children of
    their own; the top's front 0.3 m stays clear to work."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    top = WS_ELEC_TOP
    under = top - 0.03
    tube = 0.04
    parts = [shapes.bevelled(shapes.box((-wide / 2, under, front), (wide / 2, top, back), "painted_panel", "top"), EDGE)]
    leg_right, leg_left = -wide / 2 + 0.02, wide / 2 - 0.02 - tube  # the legs' -x faces
    leg_front, leg_back = front + 0.02, back - 0.02 - tube
    for x in (leg_right, leg_left):
        for z in (leg_front, leg_back):
            parts.append(shapes.bevelled(shapes.box((x, 0.0, z), (x + tube, under, z + tube), "painted_panel", "leg"),
                                         0.002))
    inner_right, inner_left = leg_right + tube, leg_left
    for z in (leg_front, leg_back + tube - 0.02):
        parts.append(shapes.bevelled(shapes.box((inner_right, under - 0.06, z), (inner_left, under, z + 0.02),
                                                "painted_panel", "rail"), 0.002))
    for x in (leg_right, leg_left + tube - 0.02):
        parts.append(shapes.bevelled(shapes.box((x, under - 0.06, leg_front + tube), (x + 0.02, under, leg_back),
                                                "painted_panel", "rail"), 0.002))
    parts.append(shapes.bevelled(shapes.box((inner_right, 0.3, leg_back + 0.005), (inner_left, 0.33, leg_back + tube - 0.005),
                                            "painted_panel", "stretcher"), 0.002))
    parts.append(shapes.bevelled(shapes.box((leg_right + 0.005, 0.12, leg_front + tube), (leg_right + tube - 0.005, 0.15,
                                                                                          leg_back),
                                            "painted_panel", "stretcher"), 0.002))
    # The pedestal under the viewer's left end (+x), hung under the rails, its two drawers' fronts proud of it.
    right, left = 0.32, inner_left - 0.005
    body = front + 0.045
    parts.append(shapes.bevelled(shapes.box((right, 0.06, body), (left, under - 0.06, back - 0.06), "painted_panel",
                                            "pedestal"), EDGE))
    parts += ws_elec_drawer(right + 0.012, left - 0.012, 0.44, under - 0.072, front + 0.033, body)
    parts += ws_elec_drawer(right + 0.012, left - 0.012, 0.072, 0.428, front + 0.033, body)
    # The anti-static mat on the top.
    parts.append(shapes.bevelled(furn_prism(rounded_outline((-0.72, front + 0.03), (0.72, 0.31), 0.03), "y", top,
                                            top + WS_ELEC_MAT, "rubber_grey", "mat"), 0.0015))
    # The riser across the back: end posts, the shelf with its lip, the back panel and the power strip under it.
    shelf_under = WS_ELEC_SHELF - 0.015
    post = 0.035
    for side in (-1, 1):
        outer = side * (wide / 2 - 0.02)
        parts.append(shapes.bevelled(shapes.box((min(outer, outer - side * post), top, WS_ELEC_SHELF_FRONT),
                                                (max(outer, outer - side * post), shelf_under, back - 0.005),
                                                "painted_panel", "riser_post"), 0.002))
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + 0.02, shelf_under, WS_ELEC_SHELF_FRONT),
                                            (wide / 2 - 0.02, WS_ELEC_SHELF, back - 0.005), "painted_panel", "shelf"),
                                 0.002))
    lip = 0.015
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + 0.02, WS_ELEC_SHELF, back - 0.005 - lip),
                                            (wide / 2 - 0.02, tall, back - 0.005), "painted_panel", "shelf_lip"), 0.002))
    for side in (-1, 1):
        outer = side * (wide / 2 - 0.02)
        parts.append(shapes.bevelled(shapes.box((min(outer, outer - side * lip), WS_ELEC_SHELF, WS_ELEC_SHELF_FRONT),
                                                (max(outer, outer - side * lip), tall, back - 0.005 - lip),
                                                "painted_panel", "shelf_lip"), 0.002))
    panel = back - 0.02
    post_inner = wide / 2 - 0.02 - post
    parts.append(shapes.box((-post_inner, top, panel), (post_inner, shelf_under, back - 0.005), "painted_panel",
                            "riser_panel"))
    parts += ws_elec_power_strip(top, panel)
    parts.append(label(0.5, top + 0.125, 0.12, 0.026, panel, "label_power"))
    parts.append(label(-0.3, top + 0.125, 0.22, 0.026, panel, "label_esd_safe"))
    return parts


def oscilloscope(size, laid):
    """A bench oscilloscope, as its close-up shows it: a steel case with a raised rim round a recessed front panel,
    the screen at the viewer's left in a bezel screwed at its corners (its traces a screen variant), three rows of
    knobs and a big time-base knob, a column of buttons, two knobs and two toggles under the screen, four probe
    sockets, a carry handle on two mounts across the top, rubber feet and its label."""
    wide, tall, deep = size
    front, back = -deep / 2 + 0.012, deep / 2  # the knobs reach the laid box's front
    foot = 0.012
    case_top = tall - 0.02
    rim = 0.012
    case = shapes.box((-wide / 2, foot, front), (wide / 2, case_top, back), "painted_panel", "case")
    furn_cut_box(case, (-wide / 2 + rim, foot + rim, front - 0.01), (wide / 2 - rim, case_top - rim, front + 0.012))
    face = front + 0.008
    parts = [shapes.bevelled(case, 0.005),
             shapes.box((-wide / 2 + rim, foot + rim, face), (wide / 2 - rim, case_top - rim, front + 0.012),
                        "painted_panel", "front_panel")]
    screen_x, screen_y, screen_wide, screen_tall = 0.086, 0.11, 0.14, 0.1
    parts += wall_screen_part(screen_x, screen_y, screen_wide, screen_tall, face, "screen", rim=0.014)
    parts += [screw(screen_x + side_x * (screen_wide / 2 - 0.007), screen_y + side_y * (screen_tall / 2 - 0.007),
                    face - 0.008) for side_x in (-1, 1) for side_y in (-1, 1)]
    # Under the screen: two knobs and two toggles.
    for x in (0.145, 0.11):
        parts.append(ws_elec_knob(x, 0.04, face, 0.01))
    for x in (0.075, 0.05):
        parts.append(shapes.bevelled(shapes.box((x - 0.005, 0.034, face - 0.012), (x + 0.005, 0.048, face),
                                                "bare_steel", "switch"), 0.001))
    # The controls at the viewer's right: three rows of knobs (the big time-base knob at the bottom right).
    for row, y in enumerate((0.127, 0.097, 0.067)):
        for x in (-0.025, -0.065, -0.105):
            big = row == 2 and x < -0.1
            parts.append(ws_elec_knob(x, y, face, 0.015 if big else 0.01, reach=0.02 if big else 0.016))
    parts += [wall_button(-0.148, y, 0.018, 0.012, face) for y in (0.135, 0.115, 0.095, 0.075)]
    for x in (-0.02, -0.06, -0.1, -0.14):
        parts.append(shapes.bevelled(shapes.ring((x, 0.036, face), (x, 0.036, face - 0.012), 0.009, 0.005,
                                                 "bare_steel", 14, "socket"), 0.001))
        parts.append(shapes.cylinder((x, 0.036, face), (x, 0.036, face - 0.006), 0.005, "anodized_black", 10, "socket"))
    parts.append(label(-0.07, 0.155, 0.12, 0.016, face, "label_oscilloscope"))
    # The carry handle across the top, front to back, on two mounts.
    for z in (-0.07, 0.07):
        parts.append(shapes.bevelled(shapes.box((-0.022, case_top, z - 0.016), (0.022, case_top + 0.012, z + 0.016),
                                                "bare_steel", "handle_mount"), 0.002))
    parts.append(shapes.bevelled(shapes.box((-0.016, case_top + 0.012, -0.088), (0.016, tall, 0.088), "anodized_black",
                                            "handle"), 0.003))
    for x in (-wide / 2 + 0.03, wide / 2 - 0.03):
        for z in (front + 0.03, back - 0.03):
            parts.append(shapes.box((x - 0.016, 0.0, z - 0.016), (x + 0.016, foot, z + 0.016), "rubber", "foot"))
    return parts


def bench_meter(size, laid):
    """A bench multimeter, as its close-up shows it: a case in two halves with a seam between them, a face plate on
    its top with the readout in a bezel at its back, a rotary dial with its bar knob in the middle and four test
    sockets (two red, one black, one red) along its front, and its label on the front."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    plate_top = tall - 0.016  # the face plate's top: the dial's knob stands over it
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front), (wide / 2, 0.044, back), "painted_panel",
                                        "lower_case"), 0.005),
             shapes.bevelled(shapes.box((-wide / 2, 0.054, front), (wide / 2, plate_top - 0.004, back), "painted_panel",
                                        "upper_case"), 0.005),
             shapes.bevelled(shapes.box((-wide / 2 + 0.012, plate_top - 0.004, front + 0.012),
                                        (wide / 2 - 0.012, plate_top, back - 0.012), "plastic_grey", "face_plate"),
                             0.0015)]
    # The seam between the halves: a dark band set 2 mm back round the case.
    inset, band = 0.002, 0.008
    for low, high in (((-wide / 2 + inset, front + inset), (wide / 2 - inset, front + inset + band)),
                      ((-wide / 2 + inset, back - inset - band), (wide / 2 - inset, back - inset)),
                      ((-wide / 2 + inset, front + inset + band), (-wide / 2 + inset + band, back - inset - band)),
                      ((wide / 2 - inset - band, front + inset + band), (wide / 2 - inset, back - inset - band))):
        # Overlapping each half by 4 mm, so no face meets another closer than the model check's 3 mm wall.
        parts.append(shapes.box((low[0], 0.040, low[1]), (high[0], 0.058, high[1]), "dark_panel", "seam"))
    parts += ws_elec_lying(wall_screen_part(0.0, 0.0, 0.15, 0.06, 0.0, "screen", rim=0.01, name="readout"), 0.0,
                           plate_top, back - 0.055)
    dial_z = -0.005
    parts.append(shapes.bevelled(shapes.cylinder((0.0, plate_top, dial_z), (0.0, plate_top + 0.006, dial_z), 0.045,
                                                 "dark_panel", 32, "dial"), 0.0015))
    knob = shapes.bevelled(shapes.box((-0.012, plate_top + 0.006, dial_z - 0.036), (0.012, tall, dial_z + 0.036),
                                      "plastic_grey", "dial_knob"), 0.003)
    parts += furn_spun([knob], (0.0, dial_z), 35.0)
    for x, material in ((0.075, "anodized_red"), (0.025, "anodized_red"), (-0.025, "rubber"), (-0.075, "anodized_red")):
        parts.append(shapes.bevelled(shapes.ring((x, plate_top, front + 0.04), (x, plate_top + 0.007, front + 0.04),
                                                 0.012, 0.0055, material, 20, "socket"), 0.001))
        parts.append(shapes.cylinder((x, plate_top, front + 0.04), (x, plate_top + 0.002, front + 0.04), 0.0056,
                                     "anodized_black", 12, "socket"))
    parts.append(label(0.0, 0.071, 0.11, 0.02, front, "label_multimeter"))
    return parts


def soldering_station(size, laid):
    """A soldering station, as its close-up shows it: a control box at the viewer's left on rubber feet with its red
    temperature readout in a bezel, a knob, a power lamp and its label; beside it a base plate carrying the iron's
    coiled wire holder on a wire frame, the iron lying in the coil with its handle out over the box, its cable back
    into the box's back, and a brass cup of brass wool at the base's front."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    box_front, box_back, box_top = -0.075, back - 0.01, 0.09
    parts = [shapes.bevelled(shapes.box((0.005, 0.008, box_front), (wide / 2, box_top, box_back), "painted_panel",
                                        "box"), 0.004)]
    for x in (0.02, wide / 2 - 0.015):
        for z in (box_front + 0.015, box_back - 0.015):
            parts.append(shapes.box((x - 0.008, 0.0, z - 0.008), (x + 0.008, 0.008, z + 0.008), "rubber", "foot"))
    parts += wall_screen_part(0.085, 0.048, 0.075, 0.032, box_front, "screen_amber", rim=0.006, name="readout")
    parts.append(ws_elec_knob(0.025, 0.048, box_front, 0.012))
    parts.append(shapes.cylinder((0.128, 0.07, box_front), (0.128, 0.07, box_front - 0.004), 0.003, "led_red", 10,
                                 "led"))
    parts.append(label(0.085, 0.077, 0.06, 0.014, box_front, "label_temp"))
    parts.append(shapes.bevelled(shapes.box((-wide / 2, 0.0, front), (0.0, 0.012, back - 0.005), "painted_panel",
                                            "base"), 0.003))
    # The coiled holder: its axis rising toward the box, its mouth at the box end.
    coil_z, coil_radius = 0.03, 0.028
    start, end = Vector((-0.13, 0.062, coil_z)), Vector((-0.04, 0.097, coil_z))
    along = (end - start).normalized()
    across = Vector((0.0, 0.0, 1.0))
    up = across.cross(along).normalized()
    turns, steps = 7, 112
    parts.append(ws_elec_tube([start + (end - start) * (at / steps)
                               + (up * math.cos(2 * math.pi * turns * at / steps)
                                  + across * math.sin(2 * math.pi * turns * at / steps)) * coil_radius
                               for at in range(steps + 1)], 0.0025, "bare_steel", "coil", 6))
    for share in (0.15, 0.85):
        middle = start + (end - start) * share
        lift = middle.y - math.sqrt(coil_radius ** 2 - 0.02 ** 2)
        for side in (-1, 1):
            parts.append(shapes.cylinder((middle.x, 0.012, coil_z + side * 0.02), (middle.x, lift, coil_z + side * 0.02),
                                         0.0025, "bare_steel", 8, "frame"))
    for side in (-1, 1):
        parts.append(shapes.cylinder((start.x + (end.x - start.x) * 0.15 - 0.003, 0.0145, coil_z + side * 0.02),
                                     (start.x + (end.x - start.x) * 0.85 + 0.003, 0.0145, coil_z + side * 0.02), 0.0025,
                                     "bare_steel", 8, "frame"))
    # The iron: its tip down the coil, its barrel at the mouth, the grip out over the box.
    parts.append(shapes.cylinder(tuple(start + along * 0.015), tuple(end), 0.003, "bare_steel", 10, "iron_tip"))
    parts.append(shapes.cylinder(tuple(end - along * 0.005), tuple(end + along * 0.03), 0.006, "bare_steel", 12,
                                 "iron"))
    grip_end = end + along * 0.09
    parts.append(shapes.bevelled(shapes.cylinder(tuple(end + along * 0.03), tuple(grip_end), 0.011, "rubber", 16,
                                                 "iron"), 0.002))
    parts.append(ws_elec_tube([grip_end, grip_end + along * 0.012, Vector((0.07, 0.122, 0.05)),
                               Vector((0.095, 0.108, 0.075)), Vector((0.11, 0.098, 0.095)),
                               Vector((0.115, 0.085, box_back + 0.004)), Vector((0.115, 0.05, box_back + 0.004))],
                              0.003, "cable_black", "cable", 8))
    # The brass cup and its wool at the base's front.
    cup = (-0.075, -0.06)
    outer, inner, middle_y = 0.042, 0.037, 0.055
    bowl = [(outer * math.cos(math.radians(-90 * at / 8)), middle_y + outer * math.sin(math.radians(-90 * at / 8)))
            for at in range(9)]
    hollow = [(inner * math.cos(math.radians(-90 * at / 8)), middle_y + inner * math.sin(math.radians(-90 * at / 8)))
              for at in range(8, -1, -1)]
    parts.append(ws_elec_lathe(bowl + hollow, cup, "anodized_gold", "cup", 32))
    parts.append(shapes.cylinder((cup[0], 0.012, cup[1]), (cup[0], 0.016, cup[1]), 0.02, "anodized_gold", 24, "cup"))
    parts.append(ws_elec_lathe([(0.0, 0.02), (0.025, 0.028), (0.034, 0.04), (0.035, 0.05), (0.0, 0.052)], cup,
                               "anodized_gold", "wool", 24))
    return parts


def parts_drawers(size, laid):
    """The parts cabinet, as its close-up shows it: a blue cabinet of forty small bin drawers (eight across, five
    high) in a frame of bars, each drawer with a steel label slot holding a card (a few printed BOLTS, NUTS, WASHERS,
    SCREWS, FUSES, RESISTORS) and a pull under it, standing on a steel two-door cupboard with a plinth, bar handles and
    hinges."""
    wide, tall, deep = size
    front, back = -deep / 2 + 0.036, deep / 2  # the door handles reach the laid box's front
    cupboard = WS_ELEC_CUPBOARD
    parts = [shapes.box((-wide / 2 + 0.02, 0.0, front + 0.03), (wide / 2 - 0.02, 0.06, back - 0.02), "dark_panel",
                        "plinth"),
             shapes.bevelled(shapes.box((-wide / 2, 0.06, front + 0.016), (wide / 2, cupboard, back), "painted_panel",
                                        "carcass"), EDGE)]
    margin, gap = 0.015, 0.008
    door_wide = (wide - 2 * margin - gap) / 2
    for door in range(2):
        right = -wide / 2 + margin + door * (door_wide + gap)
        left = right + door_wide
        parts.append(shapes.bevelled(shapes.box((right, 0.075, front), (left, cupboard - 0.015, front + 0.016),
                                                "painted_panel", "door"), 0.002))
        inner_left = door == 0  # the viewer's right door pulls by its left edge, the meeting edge
        parts += furn_pull(left - 0.06 if inner_left else right + 0.06, 0.45, 0.16, front)
        hinge_x = right - 0.004 if inner_left else left + 0.004
        for high in (0.2, cupboard - 0.14):
            parts.append(shapes.cylinder((hinge_x, high - 0.04, front + 0.004), (hinge_x, high + 0.04, front + 0.004),
                                         0.007, "bare_steel", 12, "hinge"))
    # The bin cabinet on the cupboard: its body, a frame of bars across its front, and the drawers set back in it.
    frame_front = front + 0.02
    parts.append(shapes.bevelled(shapes.box((-wide / 2, cupboard, frame_front), (wide / 2, tall, back),
                                            "overall_blue_panel", "cabinet"), EDGE))
    across, high = WS_ELEC_BINS
    bar = 0.016
    cell_wide = (wide - (across + 1) * bar) / across
    cell_tall = (tall - cupboard - (high + 1) * bar) / high
    for row in range(high + 1):
        low = cupboard + row * (cell_tall + bar)
        parts.append(shapes.box((-wide / 2, low, front), (wide / 2, low + bar, frame_front), "overall_blue_panel",
                                "frame"))
    printed = {(row, column): variant for row, column, variant in WS_ELEC_BIN_LABELS}
    for row in range(high):
        low = cupboard + bar + row * (cell_tall + bar)
        for column in range(across + 1):
            right = -wide / 2 + column * (cell_wide + bar)
            parts.append(shapes.box((right, low, front), (right + bar, low + cell_tall, frame_front),
                                    "overall_blue_panel", "frame"))
        for column in range(across):
            right = -wide / 2 + bar + column * (cell_wide + bar)
            middle_x, middle_y = right + cell_wide / 2, low + cell_tall / 2
            drawer_face = front + 0.008
            parts.append(shapes.bevelled(shapes.box((right + 0.004, low + 0.004, drawer_face),
                                                    (right + cell_wide - 0.004, low + cell_tall - 0.004, frame_front),
                                                    "overall_blue_panel", "drawer"), 0.0015))
            slot_face = drawer_face - 0.004
            parts.append(shapes.box((middle_x - 0.05, middle_y + 0.004, slot_face),
                                    (middle_x + 0.05, middle_y + 0.056, drawer_face), "bare_steel", "label_slot"))
            variant = printed.get((row, column))
            if variant:
                parts.append(label(middle_x, middle_y + 0.03, 0.088, 0.04, slot_face, variant))
            else:
                parts.append(shapes.box((middle_x - 0.044, middle_y + 0.01, slot_face - 0.004),
                                        (middle_x + 0.044, middle_y + 0.05, slot_face), "plastic_white", "card"))
            parts.append(shapes.bevelled(shapes.box((middle_x - 0.025, middle_y - 0.046, drawer_face - 0.012),
                                                    (middle_x + 0.025, middle_y - 0.034, drawer_face), "bare_steel",
                                                    "pull"), 0.0015))
    return parts


def pendant_lamp(size, laid):
    """An industrial pendant work lamp hung from the dome, as its close-up shows it: a round canopy plate under the
    roof (the laid box's top) with its cord grip, a steel rod down with its cable clipped along it, a collar and a
    neck over a round steel shade, a rolled rim round the shade's mouth and the frosted lens across it, glowing."""
    wide, tall, deep = size
    mouth = min(wide, deep) / 2 - 0.005
    shade_top = 0.234
    wall = 0.005
    steps = 12
    outside = [(0.065 + (mouth - 0.065) * math.cos(math.radians(90 * at / steps)),
                0.004 + (shade_top - 0.004) * math.sin(math.radians(90 * at / steps))) for at in range(steps + 1)]
    inside = [(0.065 - wall + (mouth - 0.065) * math.cos(math.radians(90 * at / steps)),
               0.004 + (shade_top - 0.004 - wall) * math.sin(math.radians(90 * at / steps)))
              for at in range(steps, -1, -1)]
    parts = [ws_elec_lathe(outside + inside, (0.0, 0.0), "dark_panel", "shade", 48),
             shapes.bevelled(shapes.ring((0.0, 0.0, 0.0), (0.0, 0.014, 0.0), mouth + 0.005, mouth - 0.008, "bare_steel",
                                         48, "rim"), 0.002),
             shapes.cylinder((0.0, 0.012, 0.0), (0.0, 0.018, 0.0), mouth - 0.007, "lamp_lens", 48, "lens"),
             shapes.bevelled(shapes.cylinder((0.0, shade_top - 0.008, 0.0), (0.0, 0.3, 0.0), 0.07, "dark_panel", 32,
                                             "neck"), 0.004),
             shapes.bevelled(shapes.cylinder((0.0, 0.3, 0.0), (0.0, 0.345, 0.0), 0.026, "dark_panel", 20, "collar"),
                             0.003)]
    canopy_low = tall - 0.025
    parts.append(shapes.cylinder((0.0, 0.345, 0.0), (0.0, canopy_low - 0.03, 0.0), 0.011, "pipe_steel", 16, "rod"))
    parts.append(shapes.cylinder((0.022, 0.32, 0.0), (0.022, canopy_low - 0.03, 0.0), 0.004, "cable_black", 10,
                                 "cable"))
    for high in (0.5, 0.75, 0.95):
        parts.append(shapes.bevelled(shapes.box((-0.016, high - 0.007, -0.015), (0.03, high + 0.007, 0.015),
                                                "bare_steel", "clip"), 0.002))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, canopy_low - 0.03, 0.0), (0.0, canopy_low, 0.0), 0.035,
                                                 "dark_panel", 24, "canopy"), 0.003))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, canopy_low, 0.0), (0.0, tall, 0.0), 0.085, "dark_panel", 40,
                                                 "canopy"), 0.004))
def beacon(size, laid):
    """The airlock's warning beacon on its roof, as its concept shows it (modules round): a round flange bolted to the
    roof, a grey body with a connector box on its front, a dark rim and the amber dome over the lamp, glowing."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2
    flange_top, body_top, rim_top = tall * 0.08, tall * 0.42, tall * 0.5
    parts = [shapes.bevelled(shapes.cylinder((0.0, 0.0, 0.0), (0.0, flange_top, 0.0), radius, "dark_panel", 40,
                                             "flange"), 0.004),
             shapes.bevelled(shapes.cylinder((0.0, flange_top, 0.0), (0.0, body_top, 0.0), radius * 0.74, "bare_steel",
                                             36, "body"), 0.004),
             shapes.bevelled(shapes.cylinder((0.0, body_top, 0.0), (0.0, rim_top, 0.0), radius * 0.76, "warning_paint",
                                             36, "rim"), 0.003),
             shapes.bevelled(shapes.cylinder((0.0, rim_top, 0.0), (0.0, tall, 0.0), radius * 0.66, "led_amber", 36,
                                             "dome"), 0.03),
             shapes.bevelled(shapes.box((-0.025, flange_top + 0.02, -radius * 0.74 - 0.012),
                                        (0.025, flange_top + 0.07, -radius * 0.74 + 0.01), "anodized_black", "socket"),
                             0.002)]
    for at in range(6):
        angle = 2 * math.pi * (at + 0.5) / 6
        x, z = radius * 0.87 * math.cos(angle), radius * 0.87 * math.sin(angle)
        parts.append(shapes.cylinder((x, flange_top, z), (x, flange_top + 0.008, z), 0.008, "bare_steel", 12, "bolt"))
    return parts


# ---- Modules round, concept density (owner, 2026-10-08): the habitat's smaller elements its picked concept K03 shows
# beyond the furniture, built in code with library surfaces as method B's parts check allows, each its own model: a
# storage case and a tool case on the tops, a supply cart, gas cylinders by the galley, the painted floor marking before
# each sleep pod and the slippers on it, a coiled cable hung on the wall, and the tea towels on the galley counter.
# Helpers are prefixed `hab_dense_`. Seen from in front, the kit's +x is the viewer's left.

HAB_DENSE_CART_SHELVES = (0.18, 0.78)  # the supply cart's shelf tops over its foot (its children stand on them)


def hab_dense_case(size, material, label_variant, handle):
    """A hard case: a body, a lid a little proud of it with a seam between, a latch either side on its front, a label
    on its front, and a carry handle on its lid when `handle`."""
    wide, tall, deep = size
    grip = min(0.03, tall * 0.15) if handle else 0.0  # the handle's height over the lid, kept within a low case
    front = -deep / 2
    seam = tall * 0.68
    parts = [shapes.bevelled(shapes.box((-wide / 2 + 0.004, 0.0, front + 0.004), (wide / 2 - 0.004, seam, deep / 2 - 0.004),
                                        material, "body"), 0.012),
             shapes.bevelled(shapes.box((-wide / 2, seam + 0.004, front), (wide / 2, tall - grip,
                                                                           deep / 2), material, "lid"), 0.012)]
    for x in (-wide * 0.36, wide * 0.36):
        parts.append(shapes.bevelled(shapes.box((x - 0.018, seam - 0.035, front - 0.006), (x + 0.018, seam + 0.025, front),
                                                "bare_steel", "latch"), 0.002))
    parts.append(label(0.0, seam * 0.5, wide * 0.38, seam * 0.32, front + 0.004, label_variant))
    if handle:
        top = tall - grip
        for x in (-wide * 0.22, wide * 0.22):
            parts.append(shapes.box((x - 0.012, top - 0.004, -0.012), (x + 0.012, tall, 0.012), "dark_panel", "handle"))
        parts.append(shapes.bevelled(shapes.box((-wide * 0.22 - 0.012, tall - 0.012, -0.012),
                                                (wide * 0.22 + 0.012, tall, 0.012), "dark_panel", "handle"), 0.003))
    return parts


def storage_case(size, laid):
    """A grey storage case, as its concept crop shows it on a sleep pod's and the food shelf's top: a body and a lid with
    a seam, a latch either side and a label on its front."""
    return hab_dense_case(size, "hammertone_grey", "label_storage", False)


def tool_case(size, laid):
    """A blue tool case, as its concept crop shows it on the locker bank: a body and a lid, latches, a label on its
    front and a carry handle across its lid."""
    return hab_dense_case(size, "enamel_blue", "label_tools", True)


def supply_cart(size, laid):
    """A two-shelf supply cart, as its concept crop shows it by the lockers: four steel posts, two shelves with a lip
    round each, a push handle across its back and a caster under each post; what stands on it is children."""
    wide, tall, deep = size
    caster = 0.07
    parts = []
    for x in (-wide / 2 + 0.02, wide / 2 - 0.02):
        for z in (-deep / 2 + 0.02, deep / 2 - 0.02):
            parts.append(shapes.box((x - 0.012, caster, z - 0.012), (x + 0.012, tall - 0.06, z + 0.012), "bare_steel",
                                    "post"))
            parts.append(shapes.cylinder((x - 0.016, caster * 0.5, z), (x + 0.016, caster * 0.5, z), caster * 0.5,
                                         "rubber", 16, "caster"))
            parts.append(shapes.box((x - 0.016, caster - 0.006, z - 0.016), (x + 0.016, caster + 0.006, z + 0.016),
                                    "bare_steel", "caster"))
    for top in HAB_DENSE_CART_SHELVES:
        parts.append(shapes.bevelled(shapes.box((-wide / 2 + 0.008, top - 0.012, -deep / 2 + 0.008),
                                                (wide / 2 - 0.008, top, deep / 2 - 0.008), "galvanized_steel", "shelf"),
                                     0.002))
        for z in (-deep / 2 + 0.008, deep / 2 - 0.008):
            parts.append(shapes.box((-wide / 2 + 0.008, top, z - 0.004), (wide / 2 - 0.008, top + 0.03, z + 0.004),
                                    "bare_steel", "lip"))
    parts.append(shapes.cylinder((-wide / 2 + 0.02, tall - 0.03, deep / 2 - 0.02), (wide / 2 - 0.02, tall - 0.03,
                                                                                   deep / 2 - 0.02), 0.014,
                                 "bare_steel", 16, "handle"))
    for x in (-wide / 2 + 0.02, wide / 2 - 0.02):
        parts.append(shapes.box((x - 0.012, tall - 0.06, deep / 2 - 0.032), (x + 0.012, tall - 0.03, deep / 2 - 0.008),
                                "bare_steel", "handle"))
    return parts


def gas_cylinder(size, laid):
    """A gas cylinder by the galley, as its concept crop shows it: a dark body with a rounded shoulder, a foot ring, a
    guard collar round its valve and the valve on top."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2
    shoulder = tall * 0.78
    parts = [shapes.bevelled(shapes.cylinder((0.0, 0.03, 0.0), (0.0, shoulder, 0.0), radius, "dark_panel", 32, "body"),
                             0.01),
             shapes.bevelled(shapes.cylinder((0.0, shoulder, 0.0), (0.0, shoulder + tall * 0.08, 0.0), radius * 0.78,
                                             "dark_panel", 32, "shoulder"), 0.015),
             shapes.cylinder((0.0, 0.0, 0.0), (0.0, 0.03, 0.0), radius * 0.92, "dark_panel", 32, "foot"),
             shapes.ring((0.0, shoulder + tall * 0.08, 0.0), (0.0, tall - 0.08, 0.0), radius * 0.62, radius * 0.5,
                         "bare_steel", 32, "collar")]
    # The valve stands up out of the collar, its outlet and its hand wheel above the collar's rim.
    parts.append(shapes.cylinder((0.0, shoulder + tall * 0.08, 0.0), (0.0, tall - 0.012, 0.0), radius * 0.16,
                                 "bare_steel", 16, "valve"))
    parts.append(shapes.cylinder((0.0, tall - 0.05, 0.0), (0.0, tall - 0.05, -radius * 0.7), radius * 0.09,
                                 "bare_steel", 12, "valve"))
    parts.append(shapes.cylinder((0.0, tall - 0.012, 0.0), (0.0, tall, 0.0), radius * 0.3, "anodized_black", 20,
                                 "valve"))
    return parts


def floor_marking(size, laid):
    """The painted marking on the deck before a sleep pod, as its concept crop shows it: a deck plate set into the floor
    with a white line round a rounded rectangle on it, flush with the deck (front up)."""
    wide, long, deep = size
    top, bottom = -deep / 2, deep / 2
    parts = [shapes.box((-wide / 2, 0.0, top + 0.004), (wide / 2, long, bottom), "deck", "plate")]
    # The paint stands on the plate's face, 4 mm (a thinner line reads as a wall under 3 mm in the model check).
    parts.append(rounded_ring((-wide / 2 + 0.04, 0.04), (wide / 2 - 0.04, long - 0.04), 0.12, 0.045, top, top + 0.004,
                              "enamel_white", "line"))
    return parts


def slippers(size, laid):
    """A pair of slippers on the deck before a sleep pod, as its concept crop shows them: two low rounded soles with a
    padded upper over each toe."""
    wide, tall, deep = size
    parts = []
    for x in (-wide / 4, wide / 4):
        sole = rounded_outline((x - wide * 0.2, -deep / 2), (x + wide * 0.2, deep / 2), wide * 0.12)
        parts.append(shapes.bevelled(furn_prism(sole, "y", 0.0, tall * 0.35, "rubber", "slipper"), 0.006))
        upper = rounded_outline((x - wide * 0.18, -deep / 2 + 0.01), (x + wide * 0.18, deep * 0.1), wide * 0.1)
        parts.append(shapes.bevelled(furn_prism(upper, "y", tall * 0.35, tall, "quilted_grey", "slipper"), 0.012))
    return parts


def cable_coil(size, laid):
    """A coil of cable hung on the wall beside a sleep pod, as its concept crop shows it: a steel hook bolted to the
    wall and three loose loops of black cable hanging from it."""
    wide, tall, deep = size
    back = deep / 2
    hook_y = tall - 0.04
    parts = [shapes.bevelled(shapes.box((-0.03, hook_y - 0.04, back - 0.008), (0.03, hook_y + 0.03, back), "bare_steel",
                                        "hook"), 0.002),
             shapes.box((-0.008, hook_y - 0.008, back - 0.07), (0.008, hook_y + 0.008, back - 0.008), "bare_steel",
                        "hook")]
    radius = min(wide, tall) / 2 - 0.03
    middle_y = hook_y - radius
    for index, (shift, depth) in enumerate(((-0.025, back - 0.055), (0.0, back - 0.04), (0.025, back - 0.025))):
        parts.append(floor_bent_tube((shift, middle_y - index * 0.012, depth), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                                     radius - index * 0.01, 0.009, 0.0, 359.0, "cable_black", "coil", steps=40,
                                     sides=10))
    return parts


def tea_towel(size, laid):
    """A tea towel hung over the galley counter's front, as its concept crop shows it: a folded cloth hanging down with a
    fold over at its top."""
    wide, tall, deep = size
    front = -deep / 2
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front + deep * 0.4), (wide / 2, tall, deep / 2), "quilted_grey",
                                        "cloth"), 0.006),
             shapes.bevelled(shapes.box((-wide / 2 - 0.004, tall * 0.78, front), (wide / 2 + 0.004, tall,
                                                                                  front + deep * 0.4),
                                        "quilted_grey", "cloth"), 0.006)]
    return parts


# ---- Modules round, concept density (2026-10-08): the airlock's wall gear its picked concept K02 shows beyond its
# furniture: the console over the suit-up bench, the gauge panel, a louvred vent grille, a coiled hose on its hook and
# the tool case on the bench (a child of the bench). Close-ups are crops of the concept (pics/<kind>-crop.png). Helpers
# are prefixed `lock_dense_`. Seen from in front, the kit's +x is the viewer's left.


def lock_dense_gauge(x, y, radius, face, name="gauge"):
    """A round analog gauge on a face at depth `face`: a dark rim, a pale dial standing in it and a needle across it."""
    return [shapes.bevelled(shapes.cylinder((x, y, face), (x, y, face - 0.012), radius, "anodized_black", 28, name),
                            0.002),
            shapes.cylinder((x, y, face - 0.012), (x, y, face - 0.016), radius * 0.82, "enamel_white", 28, name),
            shapes.box((x - 0.002, y - 0.002, face - 0.02), (x + 0.002, y + radius * 0.7, face - 0.016),
                       "anodized_black", "needle")]


def lock_console(size, laid):
    """The airlock's cycle console over the suit-up bench, as its concept crop shows it: a steel housing, two small
    monitors on its top, a large status screen with a readout plate and a small screen beside it, a row of five
    gauges, a keypad, round buttons and a red stop button."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    body_top = tall * 0.72
    face = front + 0.03
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, face), (wide / 2, body_top, back), "painted_panel",
                                        "housing"), 0.006)]
    # The two monitors standing on its top, their backs against the wall.
    monitor_tall = tall - body_top - 0.02
    for x in (wide * 0.22, -wide * 0.22):
        parts.append(shapes.bevelled(shapes.box((x - wide * 0.18, body_top + 0.02, front + 0.06),
                                                (x + wide * 0.18, tall, back), "dark_panel", "monitor"), 0.004))
        parts += wall_screen_part(x, body_top + 0.02 + monitor_tall / 2, wide * 0.3, monitor_tall * 0.72,
                                  front + 0.06, "screen", name="screen")
        parts.append(shapes.box((x - 0.04, body_top, front + 0.08), (x + 0.04, body_top + 0.02, back), "dark_panel",
                                "monitor"))
    # The main screen and, beside it, a readout plate over a small screen.
    parts += wall_screen_part(wide * 0.16, body_top * 0.72, wide * 0.5, body_top * 0.34, face, "screen", name="screen")
    parts.append(label(-wide * 0.28, body_top * 0.83, wide * 0.3, body_top * 0.12, face, "label_cycle",
                       name="readout"))
    parts += wall_screen_part(-wide * 0.28, body_top * 0.63, wide * 0.18, body_top * 0.16, face, "screen_amber",
                              name="screen")
    for at in range(5):
        parts += lock_dense_gauge(wide * (0.36 - 0.18 * at), body_top * 0.4, min(0.045, wide * 0.07), face)
    parts.append(label(wide * 0.16, body_top * 0.16, wide * 0.42, body_top * 0.16, face, "keypad_print",
                       name="keypad"))
    for at in range(3):
        parts.append(shapes.bevelled(shapes.cylinder((-wide * 0.12, body_top * (0.1 + 0.08 * at), face),
                                                     (-wide * 0.12, body_top * (0.1 + 0.08 * at), face - 0.012),
                                                     0.014, "anodized_red", 16, "button"), 0.002))
    parts.append(shapes.bevelled(shapes.cylinder((-wide * 0.32, body_top * 0.15, face), (-wide * 0.32, body_top * 0.15,
                                                                                      face - 0.02), 0.03,
                                                 "anodized_red", 24, "estop"), 0.004))
    return parts


def lock_gauge_panel(size, laid):
    """A gauge panel on the airlock's wall, as its concept crop shows it: a steel plate, two large analog meters, a
    column of toggle switches, two red buttons and a label strip."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    face = front + 0.02
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, face), (wide / 2, tall, back), "painted_panel", "plate"),
                             0.004)]
    for x, radius in ((wide * 0.32, tall * 0.18), (wide * 0.02, tall * 0.2)):
        parts.append(shapes.bevelled(shapes.box((x - radius - 0.012, tall * 0.48, face - 0.006),
                                                (x + radius + 0.012, tall * 0.48 + 2 * radius + 0.024, face),
                                                "anodized_black", "meter"), 0.002))
        parts.append(shapes.box((x - radius, tall * 0.48 + 0.012, face - 0.01), (x + radius, tall * 0.48 + 2 * radius
                                                                                 + 0.012, face - 0.006),
                                "enamel_white", "meter"))
        parts.append(shapes.box((x - 0.002, tall * 0.48 + 0.02, face - 0.014), (x + 0.002, tall * 0.48 + 1.6 * radius,
                                                                               face - 0.01), "anodized_black",
                                "needle"))
    for at in range(3):
        y = tall * (0.75 - 0.22 * at)
        parts.append(shapes.box((-wide * 0.34 - 0.012, y - 0.012, face - 0.006), (-wide * 0.34 + 0.012, y + 0.012,
                                                                                 face), "bare_steel", "switch"))
        parts.append(shapes.cylinder((-wide * 0.34, y, face - 0.006), (-wide * 0.34, y + 0.02, face - 0.03), 0.004,
                                     "bare_steel", 8, "switch"))
    for x in (wide * 0.3, wide * 0.15):
        parts.append(shapes.bevelled(shapes.cylinder((x, tall * 0.22, face), (x, tall * 0.22, face - 0.014), 0.018,
                                                     "anodized_red", 16, "button"), 0.002))
    parts.append(label(-wide * 0.05, tall * 0.2, wide * 0.24, tall * 0.1, face, "label_meter"))
    return parts


def vent_grille(size, laid):
    """A louvred vent grille on a wall, as its concept crop shows it: a rounded steel frame bolted at its corners
    round slanted louvres over a dark back."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    frame = shapes.prism(rounded_outline((-wide / 2, 0.0), (wide / 2, tall), 0.02), front + 0.012, back,
                         "painted_panel", "frame")
    parts = furn_louvres(frame, 0.0, tall / 2, wide - 0.06, tall - 0.06, front + 0.012, back, 6, "painted_panel",
                         back_thick=0.006)
    parts.insert(0, shapes.bevelled(frame, 0.003))
    parts += [screw(x, y, front + 0.012) for x in (-wide / 2 + 0.015, wide / 2 - 0.015) for y in (0.015, tall - 0.015)]
    return parts


def hose_coil(size, laid):
    """A coiled air hose hung on a wall hook, as its concept crop shows it: a bolted hook plate and the hose in loops
    hanging from it."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    parts = [shapes.bevelled(shapes.box((-0.04, tall - 0.1, back - 0.008), (0.04, tall, back), "bare_steel", "hook"),
                             0.002),
             shapes.bevelled(shapes.box((-0.02, tall - 0.07, back - 0.06), (0.02, tall - 0.045, back - 0.008),
                                        "bare_steel", "hook"), 0.002)]
    loops = 4
    radius = min(wide, tall) / 2 - 0.02
    for at in range(loops):
        z = back - 0.03 - at * (deep - 0.04) / loops
        middle_y = tall - 0.06 - radius * (1.0 - 0.06 * at)
        parts.append(shapes.ring((0.0, middle_y, z - 0.007), (0.0, middle_y, z + 0.007), radius * (1.0 - 0.05 * at),
                                 radius * (1.0 - 0.05 * at) - 0.016, "rubber", 32, "coil"))
    return parts


# ---- Modules round, concept density (2026-10-08): the walkway tube's handrail bracket, read off the concept K12's
# crop (pics/rail_bracket-crop.png): a foot plate bolted to the hull, a bent round arm out from it and a cradle ring
# round the rail. The rail itself is a plain pipe run (pipe_straight); the bracket never carries it.


def rail_bracket(size, laid):
    """A handrail bracket on a tube's hull, as its concept crop shows it: a foot plate bolted to the hull at its back,
    a round arm bent out from it toward the room and a cradle ring round the rail, whose axis stands RAIL_OFF (the
    box's depth less the ring's reach) in front of the foot."""
    wide, tall, deep = size
    back = deep / 2
    rail = 0.023  # the rail's radius: pipe_straight's min(tall, deep) * 0.38 at 0.06
    ring_out = rail + 0.008
    axis_y, axis_z = tall / 2, -deep / 2 + ring_out
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, back - 0.008), (wide / 2, tall, back), "dark_panel", "foot"),
                             0.002)]
    parts += bolts_along([(0.0, 0.012), (0.0, tall - 0.012)], back - 0.008)
    # The arm leaves the foot low and bends up under the rail: a flat bar out from the foot, then a bar rising from its
    # end to the ring, standing on it face to face, so no two parts cross inside each other (a crossing reads as a
    # wall under a millimetre in the model check).
    half = 0.007
    low_y = 0.014
    bend_z = axis_z
    parts.append(shapes.bevelled(shapes.box((-half, low_y - half, bend_z - half), (half, low_y + half, back - 0.008),
                                            "bare_steel", "arm"), 0.002))
    parts.append(shapes.bevelled(shapes.box((-half, low_y + half, bend_z - half),
                                            (half, axis_y - ring_out, bend_z + half), "bare_steel", "arm"), 0.002))
    parts.append(shapes.bevelled(shapes.ring((-0.012, axis_y, axis_z), (0.012, axis_y, axis_z), ring_out, rail + 0.001,
                                             "bare_steel", 32, "cradle"), 0.002))
    return parts


# ---- Greenhouse place job (2026-10-07), block gh_rig: the grow-light gantry over the plot (the light bars and their
# lit lens, the frame rails, the wire rope hangers), the irrigation boom and the service ledge's lid, built in code with
# library surfaces as method B's parts check allows, each as its clean close-up shows it. The lit lens is a kind of its
# own so the game can dim it; the bar's recess is left empty for it. Helpers are prefixed `gh_rig_`.

GH_RIG_BAR_BODY = 0.07  # the light bar's housing height under its fins
GH_RIG_LENS = (2.9, 0.03, 0.22)  # the lit lens plate (grow_light_glow's size): the bar's recess is cut to it
GH_RIG_BOOM_PIPE = 0.03  # the irrigation pipe's radius
GH_RIG_ROPE = 0.005  # the hanger's wire rope radius (10 mm thick)


def gh_rig_bolt_up(x, y, z, material="bare_steel"):
    """A bolt head standing up out of a level face at height `y`."""
    return shapes.cylinder((x, y, z), (x, y + 0.007, z), BOLT, material, 6, "bolt")


def gh_rig_hex(start, end, radius, material, name):
    """A hex nut or body between two kit points."""
    return shapes.bevelled(shapes.cylinder(start, end, radius, material, 6, name), 0.001)


def gh_rig_collar(x, inner_y, inner_z, outer_y, outer_z, wide, material, name):
    """A square collar `wide` along x round a box section: its outside from `outer_y` (low, high) and `outer_z`, its
    hole the inside's (a clamp block round the rail, an end cap's rim)."""
    collar = shapes.box((x - wide / 2, outer_y[0], outer_z[0]), (x + wide / 2, outer_y[1], outer_z[1]), material, name)
    furn_cut_box(collar, (x - wide, inner_y[0], inner_z[0]), (x + wide, inner_y[1], inner_z[1]))
    return shapes.bevelled(collar, 0.002)


def gh_rig_eye_bolt(x, z, low):
    """A lifting eye bolt screwed into a level face at height `low`: its collar and the eye standing over it (where the
    gantry rail's clamp takes the bar)."""
    return [shapes.cylinder((x, low, z), (x, low + 0.008, z), 0.009, "bare_steel", 6, "lug"),
            floor_bent_tube((x, low + 0.019, z), (1, 0, 0), (0, 1, 0), 0.0075, 0.0035, 0.0, 360.0, "bare_steel", "lug",
                            steps=20, sides=8)]


def grow_light_bar(size, laid):
    """An LED grow-light bar's housing, its length along x, as its close-up shows it: an aluminium body with a long
    shallow recess along its underside for the lit lens (grow_light_glow, a kind of its own, so the recess is left
    empty), round cooling fins along its top, a painted end box at each end (the long one at +x carries the cable
    gland and its cable), a lifting eye on each box for the gantry rail's clamp, screws, and labels."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    body_z = (front + 0.02, back - 0.02)
    long_box, short_box = (wide / 2 - 0.27, wide / 2 - 0.04), (-wide / 2, -wide / 2 + 0.1)
    box_top = GH_RIG_BAR_BODY + 0.02
    lens_wide, lens_tall, lens_deep = GH_RIG_LENS
    recess = ((-lens_wide / 2, -0.01, -lens_deep / 2), (lens_wide / 2, lens_tall, lens_deep / 2))
    body = shapes.box((short_box[1] - 0.01, 0.0, body_z[0]), (long_box[0] + 0.01, GH_RIG_BAR_BODY, body_z[1]),
                      "anodized_natural", "housing")
    box_front = front + 0.004  # the end boxes' faces: their screws and label stand on them, inside the laid box
    boxes = [shapes.box((x0, 0.0, box_front), (x1, box_top, back - 0.004), "enamel_white", "end_box")
             for x0, x1 in (long_box, short_box)]
    parts = []
    for part in [body] + boxes:
        furn_cut_box(part, *recess)
        parts.append(shapes.bevelled(part, 0.003))
    fin_ends = (short_box[1], long_box[0])
    for at in range(8):
        z = body_z[0] + 0.02 + (body_z[1] - body_z[0] - 0.04) * at / 7
        parts.append(shapes.cylinder((fin_ends[0], GH_RIG_BAR_BODY + 0.0075, z), (fin_ends[1], GH_RIG_BAR_BODY + 0.0075, z),
                                     0.0075, "anodized_black", 12, "fin"))
    for x0, x1 in (long_box, short_box):
        middle = (x0 + x1) / 2
        parts += gh_rig_eye_bolt(middle, 0.0, box_top)
        parts += [shapes.cylinder((x, y, box_front), (x, y, front), 0.0055, "bare_steel", 10, "screw")
                  for x in (x0 + 0.018, x1 - 0.018) for y in (0.018, box_top - 0.018)]
    parts += [shapes.cylinder((x, GH_RIG_BAR_BODY / 2, body_z[0]), (x, GH_RIG_BAR_BODY / 2, body_z[0] - 0.004), 0.0055,
                              "bare_steel", 10, "screw") for x in (fin_ends[0] + 0.03, fin_ends[1] - 0.03)]
    # The cable gland out of the long box's end, and the cable bending down out of it.
    gland_y = box_top * 0.55
    end = long_box[1]
    parts.append(gh_rig_hex((end, gland_y, 0.0), (end + 0.01, gland_y, 0.0), 0.02, "bare_steel", "gland"))
    parts.append(shapes.bevelled(shapes.cylinder((end + 0.01, gland_y, 0.0), (end + 0.02, gland_y, 0.0), 0.014,
                                                 "bare_steel", 16, "gland"), 0.002))
    bend = end + 0.02
    parts.append(floor_bent_tube((bend, gland_y - 0.012, 0.0), (0, 1, 0), (1, 0, 0), 0.012, 0.0075, 0.0, 90.0,
                                 "cable_black", "cable", steps=8, sides=10))
    parts.append(shapes.cylinder((bend + 0.012, gland_y - 0.012, 0.0), (bend + 0.012, 0.008, 0.0), 0.0075,
                                 "cable_black", 10, "cable"))
    parts.append(label(0.0, GH_RIG_BAR_BODY / 2 + 0.008, 0.2, 0.03, body_z[0], "label_grow_light"))
    parts.append(label((long_box[0] + long_box[1]) / 2, box_top / 2, 0.11, 0.04, box_front, "label_high_voltage"))
    return parts


def grow_light_glow(size, laid):
    """The grow-light bar's lit lens alone, the plate that sits in the bar's recess: one glowing strip (the game dims
    it on its own)."""
    wide, tall, deep = size
    return [shapes.content_plate((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "lamp_strip", "lens")]


def gh_rig_clip(x, beam_low, cable_y, cable_z):
    """A cable clip under the rail: a strap down from the rail's underside round the cable, bolted up into the rail."""
    return [shapes.bevelled(shapes.box((x - 0.012, cable_y - 0.013, cable_z - 0.014),
                                       (x + 0.012, beam_low, cable_z + 0.014), "galvanized_steel", "clip"), 0.002),
            shapes.cylinder((x, beam_low - 0.004, cable_z - 0.014), (x, beam_low - 0.004, cable_z - 0.02), 0.006,
                            "bare_steel", 6, "bolt")]


def rig_rail(size, laid):
    """One frame rail of the grow-light gantry, its length along x, as its close-up shows it: a box-section steel
    beam, open at its ends, with a slot along its top; bolted clamp blocks round it in pairs at its quarters (where the
    light bars hang under it), two bolts up out of each; a cable run along under it in clips; a HIGH VOLTAGE warning,
    a CHECK CABLES WEEKLY note and a load plate on its front."""
    wide, tall, deep = size
    clamp_wall = 0.016
    beam_y = (0.04, tall - clamp_wall - 0.007)
    beam_z = (-deep / 2 + clamp_wall, deep / 2 - clamp_wall)
    beam = shapes.box((-wide / 2, beam_y[0], beam_z[0]), (wide / 2, beam_y[1], beam_z[1]), "dark_panel", "beam")
    wall = 0.006
    furn_cut_box(beam, (-wide, beam_y[0] + wall, beam_z[0] + wall), (wide, beam_y[1] - wall, beam_z[1] - wall))
    furn_cut_box(beam, (-wide, beam_y[1] - wall - 0.01, -0.011), (wide, beam_y[1] + 0.01, 0.011))
    parts = [shapes.bevelled(beam, 0.0015)]
    clamp_y = (beam_y[0] - clamp_wall, beam_y[1] + clamp_wall)
    clamp_z = (-deep / 2, deep / 2)
    for station in (-wide / 4, 0.0, wide / 4):
        for x in (station - 0.036, station + 0.036):
            parts.append(gh_rig_collar(x, (beam_y[0] - 0.0005, beam_y[1] + 0.0005),
                                       (beam_z[0] - 0.0005, beam_z[1] + 0.0005), clamp_y, clamp_z, 0.07,
                                       "cast_iron_dark", "clamp"))
            parts += [gh_rig_bolt_up(x, clamp_y[1], z) for z in (-0.042, 0.042)]
    # The cable run under the rail, clipped between the clamp stations.
    cable_y, cable_z = 0.017, -0.01
    parts.append(shapes.cylinder((-wide / 2 + 0.01, cable_y, cable_z), (wide / 2 - 0.01, cable_y, cable_z), 0.008,
                                 "cable_grey", 12, "cable"))
    for x in (-wide * 3 / 8, -wide / 8, wide / 8, wide * 3 / 8):
        parts += gh_rig_clip(x, beam_y[0], cable_y, cable_z)
    middle = (beam_y[0] + beam_y[1]) / 2
    parts.append(label(wide / 8, middle, 0.16, 0.07, beam_z[0], "label_high_voltage"))
    parts.append(label(wide * 3 / 8 + 0.05, middle, 0.08, 0.07, beam_z[0], "note_check_cables",
                       name="note"))
    parts.append(label(-wide / 8, middle, 0.14, 0.05, beam_z[0], "label_rail_load"))
    return parts


def gh_rig_hinge(x, y, wide, face, edge_y):
    """A butt hinge at the lid's back edge (at height `edge_y`) on a face at depth `face`: a leaf screwed on the face
    and its knuckle along x at the edge."""
    leaf_low = edge_y - 0.036
    return [shapes.bevelled(shapes.box((x - wide / 2, leaf_low, face - 0.004), (x + wide / 2, edge_y, face),
                                       "bare_steel", "hinge"), 0.001),
            shapes.cylinder((x - wide / 2, edge_y, face - 0.002), (x + wide / 2, edge_y, face - 0.002), 0.006,
                            "bare_steel", 16, "hinge"),
            shapes.cylinder((x - 0.02, leaf_low + 0.018, face - 0.004), (x - 0.02, leaf_low + 0.018, face - 0.0065),
                            0.006, "bare_steel", 10, "screw"),
            shapes.cylinder((x + 0.02, leaf_low + 0.018, face - 0.004), (x + 0.02, leaf_low + 0.018, face - 0.0065),
                            0.006, "bare_steel", 10, "screw")]


def ledge_cover(size, laid):
    """A service ledge's steel lid, a floor-lying piece built standing (its top face at -z; x its width, y its length
    along the ledge, z its thickness), as its close-up shows it: a base plate under a slightly smaller lid plate with a
    raised top panel; a long bar handle in a recess along its front half; two hinges along its back edge (+y); hex
    bolts at the lid plate's corners; its SERVICE LEDGE COVER label, a taped note and an inspection sticker."""
    wide, tall, deep = size
    top, under = -deep / 2, deep / 2
    base = shapes.box((-wide / 2, 0.0, under - 0.022), (wide / 2, tall, under), "galvanized_dull", "base_plate")
    plate_face = top + 0.008
    lid = shapes.box((-wide / 2 + 0.01, 0.01, plate_face), (wide / 2 - 0.01, tall - 0.01, under - 0.022),
                     "galvanized_dull", "lid")
    face = top + 0.004  # the top panel's face: the prints stand on it, flush with the laid box's top
    panel = shapes.box((-wide / 2 + 0.05, 0.05, face), (wide / 2 - 0.05, tall - 0.05, plate_face), "galvanized_dull",
                       "panel")
    # The handle's recess: a long pocket through the panel into the lid, its bar across it at the face.
    handle_y, handle_long = 0.2, min(0.62, wide - 0.4)
    pocket = ((-handle_long / 2 - 0.03, handle_y - 0.035), (handle_long / 2 + 0.03, handle_y + 0.035))
    for part in (panel, lid):
        furn_cut_box(part, (*pocket[0], top - 0.01), (*pocket[1], top + 0.03))
    parts = [shapes.bevelled(base, 0.003), shapes.bevelled(lid, 0.003), shapes.bevelled(panel, 0.002)]
    parts.append(shapes.box((pocket[0][0], pocket[0][1], top + 0.026), (pocket[1][0], pocket[1][1], top + 0.03),
                            "anodized_black", "recess"))
    bar_z = top + 0.011
    parts.append(shapes.cylinder((-handle_long / 2 - 0.004, handle_y, bar_z), (handle_long / 2 + 0.004, handle_y, bar_z),
                                 0.009, "brushed_steel_fine", 16, "handle"))
    for x in (-handle_long / 2, handle_long / 2):
        parts.append(shapes.cylinder((x, handle_y, top + 0.026), (x, handle_y, bar_z), 0.009, "brushed_steel_fine", 16,
                                     "handle"))
    for x in (-wide * 0.3, wide * 0.3):
        parts += gh_rig_hinge(x, tall - 0.01, 0.1, plate_face, tall - 0.012)
    parts += bolts_along([(x, y) for x in (-wide / 2 + 0.03, wide / 2 - 0.03) for y in (0.03, tall - 0.03)],
                         plate_face)
    parts.append(label(wide * 0.18, tall * 0.62, 0.36, 0.12, face, "label_ledge_cover"))
    parts.append(label(-wide * 0.22, tall * 0.7, 0.2, 0.07, face, "note_ledge_cover", name="note"))
    parts.append(label(wide / 2 - 0.15, 0.13, 0.12, 0.06, face, "label_inspection", name="sticker"))
    return parts


def gh_rig_eye(middle_y, facing):
    """A hanger's end clamp, its eye at height `middle_y` opening away from the rope (`facing` +1 up, -1 down): a
    steel eye loop, its pin across the neck, the neck block down to the ferrule, and the crimped ferrule on the rope."""
    neck = middle_y - facing * 0.024
    parts = [floor_bent_tube((0.0, middle_y, 0.0), (1, 0, 0), (0, 1, 0), 0.02, 0.0065, 0.0, 360.0, "bare_steel",
                             "eye", steps=28, sides=10),
             shapes.bevelled(shapes.box((-0.011, min(neck, neck - facing * 0.02), -0.008),
                                        (0.011, max(neck, neck - facing * 0.02), 0.008), "bare_steel", "eye"),
                             0.002),
             shapes.cylinder((0.0, neck - facing * 0.008, -0.013), (0.0, neck - facing * 0.008, 0.013), 0.0045,
                             "bare_steel", 10, "pin")]
    ferrule_from = neck - facing * 0.02
    parts.append(shapes.bevelled(shapes.cylinder((0.0, ferrule_from, 0.0), (0.0, ferrule_from - facing * 0.045, 0.0),
                                                 0.0105, "brushed_steel_fine", 16, "ferrule"), 0.0015))
    return parts + gh_rig_rope_clip(ferrule_from - facing * 0.075)


def gh_rig_rope_clip(middle_y):
    """A wire rope clip on the rope at height `middle_y`, as the hanger's close-up shows one by each end: its saddle
    block round the rope and the U-bolt's two threaded legs out of its front, a hex nut on each."""
    parts = [shapes.bevelled(shapes.box((-0.026, middle_y - 0.013, -0.012), (0.026, middle_y + 0.013, 0.014),
                                        "cast_steel", "rope_clip"), 0.003)]
    for x in (-0.016, 0.016):
        parts.append(shapes.cylinder((x, middle_y, -0.012), (x, middle_y, -0.03), 0.004, "galvanized_steel", 10,
                                     "rope_clip"))
        parts.append(gh_rig_hex((x, middle_y, -0.018), (x, middle_y, -0.026), 0.0075, "bare_steel", "nut"))
    return parts


def gh_rig_turnbuckle(low):
    """The hanger's turnbuckle, a fixed 0.2 m from height `low`: a sleeve at each end, the open body between them (two
    side bars on end bosses) and the two threaded ends meeting in it."""
    parts = []
    for start, end in ((low, low + 0.06), (low + 0.14, low + 0.2)):
        parts.append(shapes.bevelled(shapes.cylinder((0.0, start, 0.0), (0.0, end, 0.0), 0.0095, "bare_steel", 16,
                                                     "turnbuckle"), 0.0015))
    for start in (low + 0.06, low + 0.13):
        parts.append(shapes.bevelled(shapes.cylinder((0.0, start, 0.0), (0.0, start + 0.01, 0.0), 0.013, "bare_steel",
                                                     6, "turnbuckle"), 0.0015))
    for side in (-1, 1):
        parts.append(shapes.bevelled(shapes.box((side * 0.017 - 0.0045, low + 0.062, -0.007),
                                                (side * 0.017 + 0.0045, low + 0.138, 0.007), "bare_steel",
                                                "turnbuckle"), 0.0015))
    parts.append(shapes.cylinder((0.0, low + 0.07, 0.0), (0.0, low + 0.097, 0.0), 0.0065, "galvanized_steel", 12,
                                 "thread"))
    parts.append(shapes.cylinder((0.0, low + 0.103, 0.0), (0.0, low + 0.13, 0.0), 0.0065, "galvanized_steel", 12,
                                 "thread"))
    return parts


def rig_hanger(size, laid):
    """A wire rope hanger of the grow-light gantry, upright, at the length the layout lays it, as its close-up shows
    it: an end at each end (an eye with its pin, its neck, a crimped ferrule on the rope and a wire rope clip), a turnbuckle near
    its foot (its own fixed size, never stretched) and the wire rope (10 mm) between them."""
    wide, tall, deep = size
    parts = gh_rig_eye(tall - 0.0265, 1) + gh_rig_eye(0.0265, -1)
    buckle_low = 0.16
    parts += gh_rig_turnbuckle(buckle_low)
    top_ferrule = tall - 0.0265 - 0.044 - 0.045
    for start, end in ((0.0265 + 0.044 + 0.045, buckle_low), (buckle_low + 0.2, top_ferrule)):
        parts.append(shapes.cylinder((0.0, start, 0.0), (0.0, end, 0.0), GH_RIG_ROPE, "cable_grey", 10, "rope"))
    return parts


def irrigation_boom(size, laid):
    """An irrigation boom over the plot, its length along x, as its close-up shows it: a grey pipe open at its ends
    behind a flange each, split saddle clamps round it every 0.6 m (two plates and a side bolt each), a drip emitter
    hanging under each clamp (a stem and a black dripper), and small rating labels on the pipe."""
    wide, tall, deep = size
    radius = GH_RIG_BOOM_PIPE - 0.004
    pipe_y = tall - 0.046
    clamp_radius = 0.043
    parts = [shapes.ring((-wide / 2 + 0.012, pipe_y, 0.0), (wide / 2 - 0.012, pipe_y, 0.0), radius, radius - 0.005,
                         "painted_panel", 32, "pipe")]
    for side in (-1, 1):
        flange = shapes.ring((side * (wide / 2 - 0.014), pipe_y, 0.0), (side * wide / 2, pipe_y, 0.0), 0.04,
                             radius - 0.005, "painted_panel", 32, "flange")
        parts.append(shapes.bevelled(flange, 0.002))
    for at in range(5):
        x = (at - 2) * 0.6
        for half in (-1, 1):
            plate = shapes.cylinder((x + half * 0.002, pipe_y, 0.0), (x + half * 0.016, pipe_y, 0.0), clamp_radius,
                                    "enamel_white", 6, "saddle")
            parts.append(shapes.bevelled(plate, 0.003))
        bolt_y = pipe_y - clamp_radius * 0.6
        parts.append(gh_rig_hex((x, bolt_y, -clamp_radius * 0.75), (x, bolt_y, -deep / 2), 0.009, "bare_steel", "bolt"))
        stem_top = pipe_y - clamp_radius * 0.85
        parts.append(shapes.cylinder((x, stem_top, 0.0), (x, 0.022, 0.0), 0.0055, "galvanized_dull", 10, "emitter"))
        parts.append(gh_rig_hex((x, 0.022, 0.0), (x, 0.008, 0.0), 0.0095, "plastic_grey", "emitter"))
        parts.append(shapes.cylinder((x, 0.008, 0.0), (x, 0.0, 0.0), 0.0045, "rubber", 10, "emitter"))
    for x in (0.3, -0.9):
        parts.append(label(x, pipe_y, 0.07, 0.014, -radius, "label_boom"))
    return parts


# ---- Greenhouse place (2026-10-07), block gh_station: the robot station's hardware, built in code with library
# surfaces as method B's parts check allows, each as its clean close-up shows it: the three docking pads (one per bay,
# each with its bay's coloured stripe), the charge post beside each pad, and the seed bin, soil bin and crop crate.
# The game (plot_field.gd) draws live fills inside these pieces, so each leaves their room exactly: a hollow channel
# in the charge post with a slot window at its front for the charge bar (0.06 x 0.56 x 0.08, rising from 0.03 m), and
# each bin a cavity (wide - 0.08) x (deep - 0.08) from 0.04 m up to its open top, its walls and floor 0.04 m thick,
# every rim, handle and label outside. Helpers are prefixed `gh_station_`.

GH_STATION_WALL = 0.04  # plot_field.gd BIN_WALL: a bin's walls and floor
# The charge post's channel round the charge bar (plot_field.gd BAR, centred in the post): a little roomier than the
# bar's 0.06 x 0.08, from just under its foot (0.03) to over its full height (0.59).
GH_STATION_CHANNEL = (0.077, 0.097)
GH_STATION_CHANNEL_FROM = 0.025
GH_STATION_CHANNEL_TO = 0.625
GH_STATION_POST_TOP = 0.64  # the post body's top, closing the channel
GH_STATION_SLOT = (0.05, 0.06, 0.575)  # the post's slot window: its width, its foot and its head
# The docking pad: its plate's face (the kit front, up once laid), the hazard border's width.
GH_STATION_PAD_FACE = -0.004
GH_STATION_PAD_RIM = 0.04
GH_STATION_STRIPE = (0.9, 0.08)  # plot_field.gd STRIPE: across x, along y, ending 0.04 in from the back edge


def gh_station_dock_pad(size, stripe_paint):
    """A robot's docking pad lying in the floor, its face up (built standing, the face toward -z, y along the floor),
    as its close-up shows it: a steel plate with rounded corners, a raised hazard-painted border round its edge, two
    low guide rails along it, the charging contact plate bolted at its middle with its slot, and the bay's coloured
    stripe across its back edge."""
    wide, long, deep = size
    face, bottom = GH_STATION_PAD_FACE, deep / 2
    paint = face - 0.004
    corner = 0.06
    parts = [shapes.bevelled(shapes.prism(rounded_outline((-wide / 2, 0.0), (wide / 2, long), corner), face, bottom,
                                          "galvanized_steel", "plate"), 0.002)]
    parts.append(shapes.bevelled(rounded_ring((-wide / 2, 0.0), (wide / 2, long), corner, GH_STATION_PAD_RIM,
                                              face - 0.008, bottom, "hazard_paint", "hazard_border"), 0.002))
    stripe_back = long - GH_STATION_PAD_RIM
    parts.append(shapes.box((-GH_STATION_STRIPE[0] / 2, stripe_back - GH_STATION_STRIPE[1], paint),
                            (GH_STATION_STRIPE[0] / 2, stripe_back, face), stripe_paint, "bay_stripe"))
    rail_top = -deep / 2
    for x in (-0.39, 0.39):
        parts.append(shapes.bevelled(shapes.box((x - 0.016, 0.07, rail_top), (x + 0.016, stripe_back - 0.1, face),
                                                "bare_steel", "guide_rail"), 0.003))
    plate_middle, half = long * 0.5, 0.08
    contact = shapes.box((-half, plate_middle - half, face - 0.008), (half, plate_middle + half, face), "bare_steel",
                         "contact_plate")
    furn_cut_box(contact, (-0.045, plate_middle - 0.012, face - 0.02), (0.045, plate_middle - 0.004, face - 0.004))
    parts.append(shapes.bevelled(contact, 0.0015))
    parts += bolts_along([(x, y) for x in (-half + 0.022, half - 0.022) for y in (plate_middle - half + 0.022,
                                                                                    plate_middle + half - 0.022)],
                         face - 0.008)
    return parts


def dock_pad_one(size, laid):
    """Bay one's docking pad, as its close-up shows it (gh_station_dock_pad), its stripe in bay one's colour."""
    return gh_station_dock_pad(size, "bay_one_paint")


def dock_pad_two(size, laid):
    """Bay two's docking pad, as its close-up shows it (gh_station_dock_pad), its stripe in bay two's colour."""
    return gh_station_dock_pad(size, "bay_two_paint")


def dock_pad_three(size, laid):
    """Bay three's docking pad, as its close-up shows it (gh_station_dock_pad), its stripe in bay three's colour."""
    return gh_station_dock_pad(size, "bay_three_paint")


def gh_station_dome(middle_y, radius, material, name):
    """The upper half of a ball standing on a level circle at height `middle_y` (the charge post's lamp cap)."""
    built = bmesh.new()
    bmesh.ops.create_uvsphere(built, u_segments=32, v_segments=16, radius=radius)
    bmesh.ops.delete(built, geom=[vertex for vertex in built.verts if vertex.co.z < -0.0001], context="VERTS")
    bmesh.ops.contextual_create(built, geom=[edge for edge in built.edges if edge.is_boundary])
    bmesh.ops.translate(built, verts=built.verts, vec=shapes.to_blender((0.0, middle_y, 0.0)))
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def charge_post(size, laid):
    """A slim charging post beside a docking pad, as its close-up shows it: a chamfered body on a foot, hollow round
    the game's charge bar (centred, rising from 0.03 m), a slot window down its front in a black frame so the bar
    shows, a CHARGE label beside it and a small indicator over it; on top a collar, the green status lamp ring and a
    domed cap; the charging cable hanging in loops from a hook on its side, its PLUG-labelled plug on the loops."""
    wide, tall, deep = size
    channel_wide, channel_deep = GH_STATION_CHANNEL
    chamfer = 0.02
    plan = [(wide / 2 - chamfer, -deep / 2), (wide / 2, -deep / 2 + chamfer), (wide / 2, deep / 2 - chamfer),
            (wide / 2 - chamfer, deep / 2), (-wide / 2 + chamfer, deep / 2), (-wide / 2, deep / 2 - chamfer),
            (-wide / 2, -deep / 2 + chamfer), (-wide / 2 + chamfer, -deep / 2)]
    parts = [shapes.bevelled(furn_prism(plan, "y", 0.0, GH_STATION_CHANNEL_FROM, "dark_panel", "foot"), 0.002)]
    inset = [(x * 0.94, z * 0.94) for x, z in plan]
    body = furn_prism(inset, "y", GH_STATION_CHANNEL_FROM, GH_STATION_POST_TOP, "hull_white_old", "body")
    furn_cut_box(body, (-channel_wide / 2, GH_STATION_CHANNEL_FROM - 0.01, -channel_deep / 2),
                 (channel_wide / 2, GH_STATION_CHANNEL_TO, channel_deep / 2))
    front = -deep / 2 * 0.94
    slot_wide, slot_low, slot_high = GH_STATION_SLOT
    furn_cut_box(body, (-slot_wide / 2, slot_low, front - 0.01), (slot_wide / 2, slot_high, -channel_deep / 2 + 0.001))
    parts.append(shapes.bevelled(body, 0.003))
    parts.append(shapes.bevelled(rounded_ring((-slot_wide / 2 - 0.007, slot_low - 0.007),
                                              (slot_wide / 2 + 0.007, slot_high + 0.007), 0.03, 0.009, front - 0.004,
                                              front + 0.001, "anodized_black", "window_frame"), 0.001))
    parts.append(label(-0.04, (slot_low + slot_high) / 2, 0.14, 0.014, front, "label_charge", turn=90.0))
    parts.append(shapes.box((-0.006, slot_high + 0.018, front - 0.004), (0.006, slot_high + 0.026, front + 0.001),
                            "led_green", "indicator"))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, GH_STATION_POST_TOP, 0.0), (0.0, GH_STATION_POST_TOP + 0.014, 0.0),
                                                 0.06, "hull_white_old", 32, "collar"), 0.002))
    parts.append(shapes.cylinder((0.0, GH_STATION_POST_TOP + 0.014, 0.0), (0.0, GH_STATION_POST_TOP + 0.024, 0.0), 0.052,
                                 "led_green", 32, "status_lamp"))
    parts.append(gh_station_dome(GH_STATION_POST_TOP + 0.024, tall - GH_STATION_POST_TOP - 0.024, "plastic_white", "cap"))
    parts += gh_station_cable_loops(-wide / 2 * 0.94, 0.5)
    return parts


def gh_station_cable_loops(side, high):
    """The charging cable on the post's -x side: a square hook boss with its tab, the cable hanging from it in two long
    loops lying along the side, and the plug clipped on the loops' front with its PLUG label."""
    out = side - 0.032
    parts = [shapes.bevelled(shapes.box((side - 0.014, high - 0.022, -0.022), (side + 0.001, high + 0.022, 0.022),
                                        "hull_white_old", "hook"), 0.002),
             shapes.bevelled(shapes.box((out, high - 0.008, -0.012), (side - 0.014, high + 0.008, 0.012), "bare_steel",
                                        "hook"), 0.0015)]
    radius, stretch = 0.062, 2.0
    for loop, x in enumerate((out + 0.006, out - 0.008)):
        middle = (x, high - radius * stretch, -0.004 + loop * 0.008)
        tube = floor_bent_tube(middle, (0, 0, 1), (0, 1, 0), radius, 0.0065, 0.0, 360.0, "cable_black", "cable",
                               steps=36, sides=10)
        centre = shapes.to_blender(middle)
        tube.data.transform(Matrix.Translation(centre) @ Matrix.Diagonal((1.0, 1.0, stretch, 1.0))
                            @ Matrix.Translation(-centre))
        parts.append(tube)
    plug_high = high - radius * stretch - 0.01
    plug_front = -radius - 0.03
    parts.append(shapes.bevelled(shapes.box((out - 0.02, plug_high - 0.04, plug_front),
                                            (out + 0.02, plug_high + 0.04, plug_front + 0.04), "hull_white_old",
                                            "plug"), 0.004))
    parts.append(label(out, plug_high, 0.05, 0.026, plug_front, "label_plug", turn=90.0))
    return parts


def gh_station_bin_shell(size, material):
    """An open bin's floor and four solid walls, each exactly GH_STATION_WALL thick, round the game's load box."""
    wide, tall, deep = size
    wall = GH_STATION_WALL
    parts = [shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, wall, deep / 2), material, "floor")]
    for low, high in (((-wide / 2, wall, -deep / 2), (wide / 2, tall, -deep / 2 + wall)),
                      ((-wide / 2, wall, deep / 2 - wall), (wide / 2, tall, deep / 2)),
                      ((-wide / 2, wall, -deep / 2 + wall), (-wide / 2 + wall, tall, deep / 2 - wall)),
                      ((wide / 2 - wall, wall, -deep / 2 + wall), (wide / 2, tall, deep / 2 - wall))):
        parts.append(shapes.box(low, high, material, "wall"))
    return parts


def gh_station_band(size, low, high, out, material, name):
    """A band round a bin's outside between two heights, `out` proud of its walls (a rim, a pressed bead): four bars
    meeting at the corners, the load box inside untouched."""
    wide, tall, deep = size
    half_x, half_z = wide / 2 + out, deep / 2 + out
    return [shapes.bevelled(shapes.box(corner_low, corner_high, material, name), min(0.003, out / 3))
            for corner_low, corner_high in (((-half_x, low, -half_z), (half_x, high, -deep / 2)),
                                            ((-half_x, low, deep / 2), (half_x, high, half_z)),
                                            ((-half_x, low, -deep / 2), (-wide / 2, high, deep / 2)),
                                            ((wide / 2, low, -deep / 2), (half_x, high, deep / 2)))]


def gh_station_pocket_handles(size, walls, high):
    """A pressed pocket handle in each end wall (+x and -x) of a bin, as the seed bin's close-up shows them: a pocket
    0.02 m into the 0.04 m wall (the cavity untouched) and a steel frame round it."""
    wide, tall, deep = size
    half_wide, half_tall = 0.07, 0.03
    for wall in walls:
        for side in (-1, 1):
            x_low, x_high = sorted((side * (wide / 2 - 0.02), side * (wide / 2 + 0.01)))
            furn_cut_box(wall, (x_low, high - half_tall, -half_wide), (x_high, high + half_tall, half_wide))
    parts = []
    for degrees in (90.0, -90.0):
        frame = rounded_ring((-half_wide - 0.012, high - half_tall - 0.012), (half_wide + 0.012, high + half_tall + 0.012),
                             0.012, 0.014, -wide / 2 - 0.006, -wide / 2, "bare_steel", "handle")
        parts += furn_spun([shapes.bevelled(frame, 0.0015)], (0.0, 0.0), degrees)
    return parts


def seed_bin(size, laid):
    """The seed bin, as its close-up shows it: a tall open galvanized bin (walls and floor 0.04 m, the seed load inside
    is the game's), a lipped rim round its top, a pressed bead round it under the rim, a pocket handle in each end and
    a SEED label on its front."""
    wide, tall, deep = size
    shell = gh_station_bin_shell(size, "galvanized_steel")
    ends = [part for part in shell[3:]]
    parts = gh_station_pocket_handles(size, ends, tall - 0.1)
    parts = [shapes.bevelled(part, 0.002) for part in shell] + parts
    parts += gh_station_band(size, tall - 0.018, tall, 0.012, "galvanized_steel", "rim")
    parts += gh_station_band(size, tall - 0.165, tall - 0.145, 0.006, "galvanized_steel", "bead")
    parts.append(label(-wide / 2 + 0.11, tall - 0.24, 0.13, 0.055, -deep / 2, "label_seed"))
    return parts


def soil_bin(size, laid):
    """The soil bin, as its close-up shows it: a low open steel tub (walls and floor 0.04 m), a rolled rim round its
    top, a wire bar handle on each end standing off it on two eyes, and a SOIL label on its front."""
    wide, tall, deep = size
    parts = [shapes.bevelled(part, 0.003) for part in gh_station_bin_shell(size, "brushed_steel_fine")]
    parts += gh_station_band(size, tall - 0.022, tall, 0.012, "brushed_steel_fine", "rim")
    high = tall - 0.1
    for side in (-1, 1):
        face = side * wide / 2
        out = face + side * 0.03
        for z in (-0.06, 0.06):
            parts.append(shapes.box((min(face, face + side * 0.012), high + 0.01, z - 0.012),
                                    (max(face, face + side * 0.012), high + 0.04, z + 0.012), "bare_steel",
                                    "handle_eye"))
            parts.append(shapes.cylinder((face, high + 0.025, z), (out, high + 0.025, z), 0.0055, "bare_steel", 10,
                                         "handle"))
            parts.append(shapes.cylinder((out, high + 0.025, z), (out, high - 0.035, z), 0.0055, "bare_steel", 10,
                                         "handle"))
        parts.append(shapes.cylinder((out, high - 0.035, -0.06), (out, high - 0.035, 0.06), 0.0055, "bare_steel", 10,
                                     "handle"))
    parts.append(label(wide * 0.12, tall * 0.55, 0.12, 0.05, -deep / 2, "label_soil"))
    return parts




def gh_station_crate_sides(size, low, high, inner, outer, material, name):
    """One band round the crop crate's four sides between two heights, between depths `inner` (into the walls from
    their outside, at most the wall) and `outer` (proud of them), each side running between the corner posts."""
    wide, tall, deep = size
    span_x, span_z = wide / 2 - GH_STATION_WALL, deep / 2 - GH_STATION_WALL
    found = []
    for side in (-1, 1):
        z_low, z_high = sorted((side * (deep / 2 - inner), side * (deep / 2 + outer)))
        found.append(shapes.box((-span_x, low, z_low), (span_x, high, z_high), material, name))
        x_low, x_high = sorted((side * (wide / 2 - inner), side * (wide / 2 + outer)))
        found.append(shapes.box((x_low, low, -span_z), (x_high, high, span_z), material, name))
    return found


def crop_crate(size, laid):
    """The crop crate, as its close-up shows it: four slatted sides (boards 0.04 m deep at most with gaps between, the
    crop load inside is the game's) in a white frame: a bottom rail notched between its corner feet, a top rail with
    a round bar along it, a square corner post at each corner with bolts down it, a floor, and a CROPS plate bolted
    across the front boards."""
    wide, tall, deep = size
    wall = GH_STATION_WALL
    rail_low, rail_top = 0.1, tall - 0.06
    floor = shapes.box((-wide / 2 + wall, 0.0, -deep / 2 + wall), (wide / 2 - wall, wall, deep / 2 - wall),
                       "galvanized_dull", "floor")
    parts = [floor]
    bottom = gh_station_crate_sides(size, 0.0, rail_low, wall, 0.015, "hull_white_old", "bottom_rail")
    for part in bottom:
        furn_cut_box(part, (-wide / 2 + 0.16, -0.01, -deep), (wide / 2 - 0.16, 0.03, deep))
        furn_cut_box(part, (-wide, -0.01, -deep / 2 + 0.16), (wide, 0.03, deep / 2 - 0.16))
    parts += [shapes.bevelled(part, 0.004) for part in bottom]
    parts += [shapes.bevelled(part, 0.004)
              for part in gh_station_crate_sides(size, rail_top, tall, wall, 0.015, "hull_white_old", "top_rail")]
    boards, gap = 4, (rail_top - rail_low - 4 * 0.06) / 3
    for board in range(boards):
        low = rail_low + board * (0.06 + gap)
        parts += [shapes.bevelled(part, 0.004)
                  for part in gh_station_crate_sides(size, low, low + 0.06, wall, -0.006, "galvanized_dull", "slat")]
    bar_y = rail_top + 0.03
    for side in (-1, 1):
        z = side * (deep / 2 + 0.022)
        parts.append(shapes.cylinder((-wide / 2 + 0.06, bar_y, z), (wide / 2 - 0.06, bar_y, z), 0.008, "hull_white_old",
                                     14, "top_bar"))
        x = side * (wide / 2 + 0.022)
        parts.append(shapes.cylinder((x, bar_y, -deep / 2 + 0.06), (x, bar_y, deep / 2 - 0.06), 0.008, "hull_white_old",
                                     14, "top_bar"))
    for x_side in (-1, 1):
        for z_side in (-1, 1):
            x_low, x_high = sorted((x_side * (wide / 2 - wall), x_side * (wide / 2 + 0.024)))
            z_low, z_high = sorted((z_side * (deep / 2 - wall), z_side * (deep / 2 + 0.024)))
            parts.append(shapes.bevelled(shapes.box((x_low, 0.0, z_low), (x_high, tall, z_high), "hull_white_old",
                                                    "corner_post"), 0.005))
            if z_side < 0:
                middle = (x_low + x_high) / 2
                parts += bolts_along([(middle, y) for y in (0.05, tall / 2, tall - 0.05)], z_low)
    plate_x, plate_y = -wide * 0.18, (rail_low + rail_top) / 2
    plate_front = -deep / 2 - 0.004
    parts.append(shapes.bevelled(shapes.box((plate_x - 0.12, plate_y - 0.07, plate_front),
                                            (plate_x + 0.12, plate_y + 0.07, -deep / 2 + 0.006), "anodized_gold",
                                            "label_plate"), 0.002))
    parts += bolts_along([(plate_x + side * 0.1, plate_y + up * 0.05) for side in (-1, 1) for up in (-1, 1)],
                         plate_front)
    parts.append(label(plate_x, plate_y, 0.16, 0.07, plate_front, "label_crops"))
    return parts


# ---- Greenhouse place job (2026-10-07), block gh_equip: the greenhouse's water tank, dosing unit, humidifier, grow
# control console, work desk and seedling shelf, built in code with library surfaces as method B's parts check allows,
# each as its clean close-up shows it. A holder never carries loose objects: the console's keyboard, the desk's lamp
# and the shelf's seedling trays are children of their own, placed on purpose (composites). Helpers are prefixed
# `gh_equip_`.

# The control console's desk: its flat top's height and depth, and the sloped switch panel rising behind it to the
# upright screen panel (its front face at z 0).
GH_EQUIP_DESK_TOP = 0.86
GH_EQUIP_DESK_BACK = -0.18
GH_EQUIP_SLOPE_TOP = 1.02


def gh_equip_slope_spot(share):
    """A point (z, y) `share` of the way up the console's sloped switch panel, from the desk's back edge."""
    return (GH_EQUIP_DESK_BACK + (0.0 - GH_EQUIP_DESK_BACK) * share,
            GH_EQUIP_DESK_TOP + (GH_EQUIP_SLOPE_TOP - GH_EQUIP_DESK_TOP) * share)


def gh_equip_slope_angle():
    """The console's sloped panel's tilt from level, in degrees."""
    return math.degrees(math.atan2(GH_EQUIP_SLOPE_TOP - GH_EQUIP_DESK_TOP, 0.0 - GH_EQUIP_DESK_BACK))


def gh_equip_on_slope(part, spot):
    """A part built standing level on the point `spot` (z, y) laid onto the console's sloped panel there."""
    return tilted(part, (spot[1], spot[0]), -gh_equip_slope_angle())


def gh_equip_slope_normal():
    """The console's sloped panel's outward normal as a kit vector (up and toward the front)."""
    angle = math.radians(gh_equip_slope_angle())
    return Vector((0.0, math.cos(angle), -math.sin(angle)))


def gh_equip_pump(x, y, front):
    """One peristaltic dosing pump on a face at depth `front`: a square mounting plate, the round rotor cover with
    its hub, and the two tubes running down out of its foot."""
    parts = [shapes.bevelled(shapes.box((x - 0.075, y - 0.075, front - 0.02), (x + 0.075, y + 0.075, front),
                                        "enamel_white", "pump"), 0.006),
             shapes.bevelled(shapes.cylinder((x, y, front - 0.02), (x, y, front - 0.055), 0.058, "enamel_white", 32,
                                             "pump"), 0.006),
             shapes.bevelled(shapes.cylinder((x, y, front - 0.055), (x, y, front - 0.07), 0.018, "bare_steel", 16,
                                             "rotor"), 0.002)]
    for side in (-1, 1):
        parts.append(shapes.cylinder((x + side * 0.03, y - 0.06, front - 0.035), (x + side * 0.03, y - 0.15,
                                                                                 front - 0.035), 0.009, "rubber_grey",
                                     12, "tube"))
    return parts


def dosing_unit(size, laid):
    """The nutrient dosing cabinet, as its close-up shows it: a cream enamel cabinet in two bodies on a dark plinth,
    a hinged lid on top, a drip tray along the front at the pumps' feet; three dosing pumps (A, B, C) with their tubes
    and labels; above them dials, a toggle switch, a small dose-meter screen with its label, a button panel with
    lamps; a gauge and a button under MAIN UNIT; tubing looped out of glands on its sides; and the HYDROPONIC
    NUTRIENT SUPPLY label on the lower body."""
    wide, tall, deep = size
    half = wide / 2 - 0.12  # the hoses loop out beside the cabinet, inside the laid width
    front, back = -deep / 2 + 0.1, deep / 2
    upper_front = front + 0.04
    parts = [shapes.box((-half + 0.02, 0.0, front + 0.03), (half - 0.02, 0.03, back - 0.02), "dark_panel", "plinth"),
             shapes.bevelled(shapes.box((-half, 0.03, front), (half, 0.62, back), "enamel_white", "cabinet"), 0.01),
             shapes.bevelled(shapes.box((-half + 0.02, 0.62, upper_front), (half - 0.02, tall - 0.04, back),
                                        "enamel_white", "cabinet"), 0.01)]
    # The lid on top and its hinge along the back.
    parts.append(shapes.bevelled(shapes.box((-half + 0.12, tall - 0.04, upper_front + 0.05),
                                            (half - 0.12, tall - 0.01, back - 0.05), "enamel_white", "lid"), 0.012))
    parts.append(shapes.cylinder((-half + 0.16, tall - 0.025, back - 0.04), (half - 0.16, tall - 0.025, back - 0.04),
                                 0.012, "bare_steel", 12, "hinge"))
    # The drip tray across the front at the pumps' feet: a floor and a lip.
    parts.append(shapes.bevelled(shapes.box((-half + 0.04, 0.6, front - 0.1), (half - 0.04, 0.615, upper_front),
                                            "enamel_white", "drip_tray"), 0.003))
    parts.append(shapes.bevelled(shapes.box((-half + 0.04, 0.615, front - 0.1), (half - 0.04, 0.67, front - 0.085),
                                            "enamel_white", "drip_tray"), 0.003))
    # The three pumps (A at the viewer's left, +x) and their labels.
    pump_y = 0.8
    for pump_x, variant in ((0.32, "label_pump_a"), (0.06, "label_pump_b"), (-0.2, "label_pump_c")):
        parts += gh_equip_pump(pump_x, pump_y, upper_front)
        parts.append(label(pump_x, pump_y + 0.13, 0.15, 0.045, upper_front, variant))
    # The upper controls: three dials and a toggle switch, the dose-meter screen, the button panel with its lamps.
    for dial_x, dial_y in ((0.36, 1.13), (0.26, 1.13), (0.26, 1.03)):
        parts.append(shapes.bevelled(shapes.cylinder((dial_x, dial_y, upper_front), (dial_x, dial_y,
                                                                                     upper_front - 0.025),
                                                     0.022, "rubber", 20, "dial"), 0.002))
    parts.append(shapes.box((0.355, 1.0, upper_front - 0.006), (0.385, 1.06, upper_front), "bare_steel", "switch"))
    parts.append(shapes.cylinder((0.37, 1.03, upper_front - 0.006), (0.37, 1.05, upper_front - 0.03), 0.004,
                                 "bare_steel", 8, "switch"))
    parts += wall_screen_part(0.06, 1.1, 0.2, 0.15, upper_front, "screen", 0.016)
    parts.append(label(0.06, 0.99, 0.18, 0.045, upper_front, "label_dose_meter"))
    parts.append(shapes.bevelled(shapes.box((-0.14, 1.03, upper_front - 0.008), (-0.06, 1.17, upper_front),
                                            "plastic_white", "button_panel"), 0.002))
    for at, variant in enumerate(("led_green", "led_amber", "led_red")):
        parts.append(shapes.cylinder((-0.12, 1.14 - at * 0.035, upper_front - 0.008),
                                     (-0.12, 1.14 - at * 0.035, upper_front - 0.014), 0.007, variant, 12, "lamp"))
        parts.append(wall_button(-0.085, 1.14 - at * 0.035, 0.022, 0.018, upper_front - 0.008, "dark_panel"))
    # MAIN UNIT: its label, a round gauge and a square button under it.
    parts.append(label(-0.4, 1.0, 0.14, 0.07, upper_front, "label_main_unit"))
    parts.append(shapes.bevelled(shapes.cylinder((-0.4, 0.86, upper_front), (-0.4, 0.86, upper_front - 0.02), 0.048,
                                                 "bare_steel", 32, "gauge"), 0.003))
    parts.append(shapes.cylinder((-0.4, 0.86, upper_front - 0.02), (-0.4, 0.86, upper_front - 0.026), 0.038,
                                 "glass_frosted", 32, "gauge"))
    parts.append(shapes.bevelled(shapes.box((-0.44, 0.69, upper_front - 0.03), (-0.36, 0.77, upper_front),
                                            "dark_panel", "button"), 0.004))
    # The lower body's label.
    parts.append(label(0.08, 0.36, 0.34, 0.16, front, "label_nutrient_supply"))
    # The glands on the viewer's left side (+x) and the tubing looped out of them.
    for gland_y in (0.34, 0.22):
        parts.append(shapes.bevelled(shapes.cylinder((half, gland_y, front + 0.12), (half + 0.03, gland_y,
                                                                                     front + 0.12),
                                                     0.035, "rubber_grey", 20, "gland"), 0.003))
    for loop_x, loop_y in ((half + 0.05, 0.28), (half + 0.09, 0.25)):
        parts.append(floor_bent_tube((loop_x, loop_y, front + 0.2), (0, 0, 1), (0, 1, 0), 0.09, 0.011, 160.0, 520.0,
                                     "rubber_grey", "hose", steps=28, sides=10))
    # Tubing out of the viewer's right side (-x), drooping in an arc down the side.
    parts.append(shapes.bevelled(shapes.cylinder((-half, 0.95, 0.05), (-half - 0.03, 0.95, 0.05), 0.03,
                                                 "rubber_grey", 20, "gland"), 0.003))
    for offset in (0.0, 0.03):
        parts.append(floor_bent_tube((-half - 0.02, 0.85, 0.035 + offset), (0, 1, 0), (-1, 0, 0), 0.1, 0.01, 0.0,
                                     180.0, "rubber_grey", "hose", steps=16, sides=10))
        parts.append(shapes.cylinder((-half - 0.02, 0.75, 0.035 + offset), (-half - 0.02, 0.02, 0.035 + offset), 0.01,
                                     "rubber_grey", 10, "hose"))
    return parts


def humidifier(size, laid):
    """The ultrasonic grow humidifier, as its close-up shows it: a lower water tank on feet with a band round its top,
    the open housing over it holding the blue water tank, a cap plate on top with a raised collar and the round fan
    grille (rings and spokes over the dark fan, four screws), a clamp over the housing's side, a mist nozzle and a
    flanged water pipe inlet on the viewer's right side, the status panel (a green lamp, a readout and three buttons)
    and the HUMIDIFIER label on the front, and a tab at the front foot. No mist is drawn."""
    wide, tall, deep = size
    half_wide, half_deep = wide / 2 - 0.05, deep / 2 - 0.03
    parts = []
    for x in (-half_wide + 0.04, half_wide - 0.04):
        for z in (-half_deep + 0.04, half_deep - 0.04):
            parts.append(shapes.box((x - 0.03, 0.0, z - 0.03), (x + 0.03, 0.03, z + 0.03), "rubber", "foot"))
    parts.append(shapes.bevelled(shapes.box((-half_wide, 0.03, -half_deep), (half_wide, 0.45, half_deep),
                                            "enamel_white", "base"), 0.006))
    parts.append(shapes.bevelled(shapes.box((-half_wide - 0.02, 0.43, -half_deep - 0.02), (half_wide + 0.02, 0.48,
                                                                                          half_deep + 0.02),
                                            "enamel_white", "band"), 0.004))
    housing_front = -half_deep + 0.01
    housing = shapes.box((-half_wide + 0.01, 0.48, housing_front), (half_wide - 0.01, 0.7, half_deep - 0.01),
                         "enamel_white", "housing")
    furn_cut_box(housing, (-half_wide + 0.03, 0.56, housing_front + 0.02), (half_wide - 0.03, 0.72, half_deep - 0.03))
    parts.append(shapes.bevelled(housing, 0.003))
    parts.append(shapes.bevelled(shapes.box((-half_wide + 0.04, 0.56, housing_front + 0.03),
                                            (half_wide - 0.04, 0.86, half_deep - 0.04), "enamel_blue", "tank"), 0.008))
    # The cap plate on the tank, its raised collar, the fan under the grille, the grille's rings and spokes, screws.
    cap_top = 0.9
    parts.append(shapes.bevelled(shapes.box((-half_wide - 0.01, 0.86, -half_deep - 0.01), (half_wide + 0.01, cap_top,
                                                                                          half_deep + 0.01),
                                            "enamel_white", "cap"), 0.008))
    parts.append(shapes.bevelled(shapes.box((-half_wide + 0.05, cap_top, -half_deep + 0.03),
                                            (half_wide - 0.05, cap_top + 0.02, half_deep - 0.03), "enamel_white",
                                            "collar"), 0.008))
    fan_y = cap_top + 0.02
    grille_radius = min(half_wide, half_deep) - 0.07
    parts.append(shapes.cylinder((0.0, cap_top, 0.0), (0.0, fan_y + 0.004, 0.0), grille_radius + 0.01,
                                 "anodized_black", 32, "fan"))
    for at in range(5):
        outer = grille_radius - at * (grille_radius - 0.03) / 4
        parts.append(shapes.ring((0.0, fan_y + 0.004, 0.0), (0.0, fan_y + 0.01, 0.0), outer, outer - 0.006,
                                 "bare_steel", 32, "grille"))
    for at in range(2):
        angle = math.pi * at / 2
        reach = Vector((math.cos(angle), 0.0, math.sin(angle))) * grille_radius
        parts.append(shapes.cylinder(tuple(Vector((0.0, fan_y + 0.007, 0.0)) - reach),
                                     tuple(Vector((0.0, fan_y + 0.007, 0.0)) + reach), 0.003, "bare_steel", 8,
                                     "grille"))
    parts.append(shapes.cylinder((0.0, fan_y + 0.004, 0.0), (0.0, fan_y + 0.012, 0.0), 0.025, "bare_steel", 16,
                                 "grille"))
    for x in (-grille_radius, grille_radius):
        for z in (-grille_radius, grille_radius):
            parts.append(shapes.cylinder((x * 0.8, fan_y, z * 0.8), (x * 0.8, fan_y + 0.006, z * 0.8), 0.007,
                                         "bare_steel", 10, "screw"))
    # The viewer's right side (-x): the clamp over the housing's edge, the mist nozzle, the flanged pipe inlet.
    side = -half_wide + 0.01
    parts.append(shapes.bevelled(shapes.box((side - 0.012, 0.6, -0.07), (side + 0.025, 0.75, -0.035),
                                            "bare_steel", "clamp"), 0.003))
    parts.append(shapes.cylinder((side, 0.62, 0.06), (side - 0.03, 0.62, 0.06), 0.024, "bare_steel", 20, "nozzle"))
    parts.append(shapes.cylinder((side - 0.03, 0.62, 0.06), (side - 0.055, 0.62, 0.06), 0.015, "bare_steel", 20,
                                 "nozzle"))
    parts += floor_flange((-half_wide - 0.006, 0.24, 0.0), (-1.0, 0.0, 0.0), 0.085, "bare_steel", 8)
    parts.append(shapes.bevelled(shapes.ring((-half_wide - 0.012, 0.24, 0.0), (-wide / 2, 0.24, 0.0), 0.055, 0.045,
                                             "pipe_steel", 32, "inlet"), 0.002))
    # The front: the status panel (green lamp, readout, buttons), the label, the tab at the foot.
    front = housing_front
    parts.append(shapes.bevelled(shapes.box((-0.25, 0.52, front - 0.008), (-0.05, 0.63, front), "bare_steel",
                                            "panel"), 0.002))
    parts.append(shapes.cylinder((-0.075, 0.58, front - 0.008), (-0.075, 0.58, front - 0.02), 0.014, "led_green", 16,
                                 "lamp"))
    parts += wall_screen_part(-0.17, 0.59, 0.11, 0.055, front - 0.008, "screen_amber", 0.01, "readout")
    for at in range(3):
        parts.append(wall_button(-0.205 + at * 0.035, 0.54, 0.025, 0.014, front - 0.008))
    parts.append(label(0.12, 0.6, 0.24, 0.06, front, "label_humidifier"))
    parts.append(shapes.bevelled(shapes.box((0.04, 0.03, -half_deep - 0.015), (0.12, 0.13, -half_deep),
                                            "enamel_white", "tab"), 0.003))
    return parts


def control_console(size, laid):
    """The built-in grow control console, as its close-up shows it: two side posts on foot plates with conduits up
    their fronts, a recessed kick panel with a vent over a plinth, a flat desk with a front fascia and its caution
    label (its keyboard spot left clear for the keyboard, a child of its own), switches, buttons, a lever and a big
    dial on the desk, a sloped switch panel of sliders, buttons and dials behind it, and the upright panel above with
    a bank of six glowing screens, a status lamp block, a vent, two taped sheets and the GROW CONTROL sign."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    post = 0.12
    inner = wide / 2 - post
    parts = []
    for side in (-1, 1):
        low_x, high_x = sorted((side * inner, side * wide / 2))
        profile = [(front + 0.04, 0.06), (back, 0.06), (back, tall), (0.0, tall), (0.0, 0.95), (front + 0.04, 0.45)]
        parts.append(shapes.bevelled(furn_prism(profile, "x", low_x, high_x, "hammertone_grey", "post"), EDGE))
        parts.append(shapes.bevelled(shapes.box((low_x, 0.0, front), (high_x, 0.06, back), "dark_panel", "foot"),
                                     0.004))
        # The conduit up the post's front: along its sloped edge, then straight up its upright front.
        middle_x = side * (inner + post / 2)
        out = Vector((0.0, 0.0 - (front + 0.04), -0.5)).normalized()  # off the sloped edge, front-and-up
        start = Vector((middle_x, 0.45, front + 0.04)) + out * 0.024
        bend = Vector((middle_x, 0.95, 0.0)) + out * 0.024
        parts.append(shapes.cylinder(tuple(start), tuple(bend), 0.018, "pipe_steel", 16, "conduit"))
        parts.append(shapes.cylinder(tuple(bend), (middle_x, tall - 0.04, bend.z), 0.018, "pipe_steel", 16, "conduit"))
        parts.append(shapes.cylinder((middle_x, 0.06, start.z), tuple(start), 0.018, "pipe_steel", 16,
                                     "conduit"))
    # The plinth and the recessed kick panel with its vent.
    parts.append(shapes.box((-inner, 0.0, 0.05), (inner, 0.08, back - 0.02), "dark_panel", "plinth"))
    kick = shapes.box((-inner, 0.08, 0.1), (inner, GH_EQUIP_DESK_TOP - 0.12, back), "hammertone_grey", "kick_panel")
    vents = furn_louvres(kick, 0.62, 0.62, 0.16, 0.1, 0.1, 0.135, 4, "dark_panel", "vent")
    parts += [kick] + vents
    # The desk: its flat top and the fascia along its front with the caution label.
    desk = GH_EQUIP_DESK_TOP
    parts.append(shapes.bevelled(shapes.box((-inner, desk - 0.04, front + 0.004), (inner, desk, GH_EQUIP_DESK_BACK + 0.01),
                                            "hammertone_grey", "desk"), 0.006))
    parts.append(shapes.bevelled(shapes.box((-inner, desk - 0.14, front + 0.004), (inner, desk - 0.04, front + 0.03),
                                            "hammertone_grey", "fascia"), 0.004))
    parts.append(label(-0.25, desk - 0.09, 0.2, 0.05, front + 0.004, "label_caution_voltage"))
    # On the desk, clear of the keyboard's spot: a button pad (viewer's left), toggles, buttons, a lever, a dial.
    pad_z = -0.29
    for at in range(3):
        parts.append(shapes.bevelled(shapes.box((0.74 + at * 0.07 - 0.022, desk, pad_z - 0.022),
                                                (0.74 + at * 0.07 + 0.022, desk + 0.015, pad_z + 0.022),
                                                "dark_panel", "button"), 0.002))
    for switch_x in (-0.05, -0.12):
        parts.append(shapes.box((switch_x - 0.025, desk, pad_z - 0.04), (switch_x + 0.025, desk + 0.008,
                                                                         pad_z + 0.04), "bare_steel", "switch"))
        parts.append(shapes.cylinder((switch_x, desk + 0.008, pad_z), (switch_x, desk + 0.06, pad_z - 0.02), 0.006,
                                     "bare_steel", 10, "switch"))
    for at, variant in enumerate(("anodized_red", "dark_panel", "anodized_red")):
        parts.append(shapes.bevelled(shapes.box((-0.24 - at * 0.08 - 0.025, desk, pad_z - 0.025),
                                                (-0.24 - at * 0.08 + 0.025, desk + 0.018, pad_z + 0.025), variant,
                                                "button"), 0.002))
    parts.append(shapes.bevelled(shapes.box((-0.52, desk, pad_z - 0.05), (-0.44, desk + 0.03, pad_z + 0.05),
                                            "dark_panel", "lever"), 0.003))
    parts.append(shapes.bevelled(shapes.box((-0.5, desk + 0.03, pad_z - 0.015), (-0.46, desk + 0.09, pad_z + 0.015),
                                            "anodized_black", "lever"), 0.004))
    parts.append(shapes.bevelled(shapes.cylinder((-0.75, desk, pad_z), (-0.75, desk + 0.045, pad_z), 0.05,
                                                 "bare_steel", 32, "dial"), 0.004))
    # The sloped switch panel: sliders in slots, rows of buttons, round dials, all standing off its face.
    slope_outline = [(GH_EQUIP_DESK_BACK, desk - 0.04), (0.06, desk - 0.04), (0.06, GH_EQUIP_SLOPE_TOP),
                     (0.0, GH_EQUIP_SLOPE_TOP), (GH_EQUIP_DESK_BACK, desk)]
    parts.append(shapes.bevelled(furn_prism(slope_outline, "x", -inner, inner, "hammertone_grey", "slope"), 0.003))
    normal = gh_equip_slope_normal()
    low_spot, high_spot = gh_equip_slope_spot(0.3), gh_equip_slope_spot(0.62)
    for slider_x in (0.2, 0.12, 0.04, -0.62, -0.7, -0.78, -0.86):
        parts.append(gh_equip_on_slope(shapes.box((slider_x - 0.012, high_spot[1], high_spot[0] - 0.06),
                                                  (slider_x + 0.012, high_spot[1] + 0.006, high_spot[0] + 0.06),
                                                  "anodized_black", "slider_slot"), high_spot))
        parts.append(gh_equip_on_slope(shapes.bevelled(shapes.box((slider_x - 0.02, high_spot[1] + 0.006,
                                                                   high_spot[0] - 0.015),
                                                                  (slider_x + 0.02, high_spot[1] + 0.04,
                                                                   high_spot[0] + 0.015), "bare_steel", "slider"),
                                                       0.003), high_spot))
    for at in range(8):
        button_x = 0.78 - at * 0.05
        variant = ("anodized_red", "led_green", "led_amber", "plastic_white")[at % 4]
        parts.append(gh_equip_on_slope(shapes.bevelled(shapes.box((button_x - 0.018, low_spot[1],
                                                                   low_spot[0] - 0.015),
                                                                  (button_x + 0.018, low_spot[1] + 0.014,
                                                                   low_spot[0] + 0.015), variant, "button"), 0.002),
                                       low_spot))
    for dial_x, spot in ((-0.2, high_spot), (-0.32, high_spot), (-0.26, low_spot)):
        foot = Vector((dial_x, spot[1], spot[0]))
        parts.append(shapes.bevelled(shapes.cylinder(tuple(foot), tuple(foot + normal * 0.03), 0.028, "rubber", 24,
                                                     "dial"), 0.003))
    # The upright panel: six screens (two rows of three), the status lamp block, a vent, two sheets and the sign.
    panel = shapes.box((-inner, GH_EQUIP_SLOPE_TOP, 0.0), (inner, tall - 0.02, back), "hammertone_grey",
                       "back_panel")
    vents = furn_louvres(panel, -0.62, 1.16, 0.22, 0.12, 0.0, 0.05, 5, "dark_panel", "vent")
    parts += [panel] + vents
    for row_y in (1.43, 1.19):
        for screen_x, variant in ((0.3, "screen"), (0.0, "screen"), (-0.3, "screen")):
            parts += wall_screen_part(screen_x, row_y, 0.26, 0.2, 0.0, variant, 0.02)
    parts.append(shapes.bevelled(shapes.box((0.6, 1.33, -0.01), (0.86, 1.53, 0.0), "anodized_black", "lamp_block"),
                                 0.002))
    for row in range(3):
        for column in range(5):
            parts.append(shapes.box((0.62 + column * 0.048, 1.36 + row * 0.055, -0.016),
                                    (0.655 + column * 0.048, 1.385 + row * 0.055, -0.01),
                                    ("led_green", "led_amber", "led_red")[row], "lamp"))
    parts += wall_screen_part(0.73, 1.17, 0.22, 0.16, 0.0, "screen_amber", 0.018, "readout")
    parts.append(label(-0.73, 1.53, 0.26, 0.06, 0.0, "label_grow_control"))
    parts.append(label(-0.78, 1.38, 0.13, 0.17, 0.0, "sheet_log", thick=0.004, name="sheet"))
    parts.append(label(-0.62, 1.37, 0.13, 0.17, 0.0, "sheet_plan", thick=0.004, name="sheet"))
    return parts


def work_desk(size, laid):
    """The steel writing desk, as its close-up shows it: a flat top with rounded edges, a three-drawer pedestal on
    short legs under the viewer's left end (a pull-out slide over the drawers, bar pulls, STATION LOG, DATA ENTRY,
    SPARE PARTS and CAUTION HOT SURFACE labels), two square legs with rubber feet and a side stretcher at the other
    end, an apron along the front and a modesty panel at the back. The lamp's spot (the back corner over the legs)
    is left clear: the lamp is a child of its own."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    top_low = tall - 0.035
    parts = [shapes.bevelled(shapes.box((-wide / 2, top_low, front), (wide / 2, tall, back), "galvanized_dull",
                                        "top"), 0.012)]
    # The pedestal under the viewer's left end (+x), on four short legs.
    ped_right, ped_left = wide / 2 - 0.46, wide / 2 - 0.02
    body = front + 0.055
    parts.append(shapes.bevelled(shapes.box((ped_right, 0.1, body), (ped_left, top_low, back - 0.03),
                                            "galvanized_dull", "pedestal"), EDGE))
    for x in (ped_right + 0.04, ped_left - 0.04):
        for z in (body + 0.04, back - 0.07):
            parts.append(shapes.box((x - 0.02, 0.0, z - 0.02), (x + 0.02, 0.1, z + 0.02), "galvanized_dull",
                                    "pedestal_leg"))
    parts.append(shapes.bevelled(shapes.box((ped_right + 0.02, top_low - 0.035, front + 0.035),
                                            (ped_left - 0.02, top_low - 0.012, body), "galvanized_dull", "slide"),
                                 0.002))
    drawer_spans = ((0.52, top_low - 0.045), (0.32, 0.505), (0.12, 0.305))
    labels = (("label_station_log", None), ("label_data_entry", "label_caution_hot"), ("label_spare_parts", None))
    middle_x = (ped_right + ped_left) / 2
    for (low, high), (first, second) in zip(drawer_spans, labels):
        parts.append(shapes.bevelled(shapes.box((ped_right + 0.015, low, front + 0.04), (ped_left - 0.015, high, body),
                                                "galvanized_dull", "drawer"), 0.003))
        parts += furn_pull(middle_x, (low + high) / 2 - 0.025, 0.14, front + 0.04, upright=False)
        parts.append(label(middle_x + 0.09, high - 0.035, 0.17, 0.04, front + 0.04, first))
        if second is not None:
            parts.append(label(middle_x - 0.11, high - 0.035, 0.13, 0.05, front + 0.04, second))
    # The legs at the other end, their feet and the side stretcher between them.
    leg_x = -wide / 2 + 0.05
    for z in (front + 0.05, back - 0.05):
        parts.append(shapes.bevelled(shapes.box((leg_x - 0.022, 0.015, z - 0.022), (leg_x + 0.022, top_low, z + 0.022),
                                                "galvanized_dull", "leg"), 0.003))
        parts.append(shapes.box((leg_x - 0.024, 0.0, z - 0.024), (leg_x + 0.024, 0.015, z + 0.024), "rubber", "foot"))
    parts.append(shapes.bevelled(shapes.box((leg_x - 0.015, 0.2, front + 0.072), (leg_x + 0.015, 0.235, back - 0.072),
                                            "galvanized_dull", "stretcher"), 0.002))
    # The apron along the front between the pedestal and the legs, the modesty panel at the back.
    parts.append(shapes.bevelled(shapes.box((leg_x + 0.022, top_low - 0.07, front + 0.03), (ped_right, top_low,
                                                                                            front + 0.05),
                                            "galvanized_dull", "apron"), 0.002))
    parts.append(shapes.bevelled(shapes.box((leg_x + 0.022, 0.32, back - 0.08), (ped_right, top_low - 0.07,
                                                                                 back - 0.06),
                                            "galvanized_dull", "modesty"), 0.002))
    return parts


GH_EQUIP_STAND = 0.55  # the water tank's stand: its top, where the tank's foot sits
# The seedling shelf's three shelves: their top faces over the foot, where the seedling trays (children) stand.
GH_EQUIP_SHELVES = (0.42, 1.04, 1.66)


def gh_equip_brace(start, end, across, middle_depth, material, name):
    """A square-tube diagonal brace in a face of the water tank's stand, from (u, y) `start` to `end` in that face:
    on a front or back face (`across` 'x', u = x, its depth middle on z) or a side face (`across` 'z', u = z, its
    depth middle on x)."""
    (start_u, start_y), (end_u, end_y) = start, end
    length = math.hypot(end_u - start_u, end_y - start_y)
    middle_u, middle_y = (start_u + end_u) / 2, (start_y + end_y) / 2
    degrees = math.degrees(math.atan2(end_y - start_y, end_u - start_u))
    if across == "x":
        bar = shapes.box((middle_u - length / 2, middle_y - 0.02, middle_depth - 0.015),
                         (middle_u + length / 2, middle_y + 0.02, middle_depth + 0.015), material, name)
        return turned(bar, (middle_u, middle_y), degrees)
    bar = shapes.box((middle_depth - 0.015, middle_y - 0.02, middle_u - length / 2),
                     (middle_depth + 0.015, middle_y + 0.02, middle_u + length / 2), material, name)
    return tilted(bar, (middle_y, middle_u), -degrees)


def gh_equip_stand(half, top, material):
    """The water tank's welded steel stand: four square corner posts, top and bottom rails round all four faces,
    crossed braces in each face, and bolt heads at the front's joints."""
    post = 0.06
    parts = []
    for x in (-half + post / 2, half - post / 2):
        for z in (-half + post / 2, half - post / 2):
            parts.append(shapes.bevelled(shapes.box((x - post / 2, 0.0, z - post / 2), (x + post / 2, top,
                                                                                        z + post / 2),
                                                    material, "post"), 0.004))
    rail = 0.05
    inner = half - post
    for low_y in (0.0, top - rail):
        for sign in (-1, 1):
            middle = sign * (half - 0.025)
            parts.append(shapes.bevelled(shapes.box((-inner, low_y, middle - 0.025), (inner, low_y + rail,
                                                                                      middle + 0.025),
                                                    material, "rail"), 0.003))
            parts.append(shapes.bevelled(shapes.box((middle - 0.025, low_y, -inner), (middle + 0.025, low_y + rail,
                                                                                      inner),
                                                    material, "rail"), 0.003))
    low, high = (-inner, rail), (inner, top - rail)
    for sign in (-1, 1):
        middle = sign * (half - 0.025)
        for across in ("x", "z"):
            parts.append(gh_equip_brace(low, high, across, middle, material, "brace"))
            parts.append(gh_equip_brace((low[0], high[1]), (high[0], low[1]), across, middle, material, "brace"))
    for x in (-half + post / 2, half - post / 2):
        for y in (rail / 2, top - rail / 2):
            parts.append(bolt(x, y, -half, "cast_iron_dark"))
    return parts


def water_tank(size, laid):
    """The water tank, as its close-up shows it: a square moulded plastic tank with rounded edges, raised ribs round
    it and up its faces, a round lid hatch on top (a collar, the screwed cover and its boss), a level sight tube up
    its front between two fittings beside a scale, the WATER label and a POTABLE WATER sticker; on a welded steel
    stand (posts, rails, crossed braces, bolts), the outlet pipe dropping from the tank's foot and out through the
    stand's front to a valve with a red lever."""
    wide, tall, deep = size
    half = min(wide, deep) / 2
    stand = GH_EQUIP_STAND
    parts = gh_equip_stand(half - 0.007, stand, "enamel_white")  # its bolt heads inside the laid box
    tank_half = half - 0.05
    top = tall - 0.08
    parts.append(shapes.bevelled(shapes.box((-tank_half, stand, -tank_half), (tank_half, top, tank_half),
                                            "plastic_white", "tank"), 0.05))
    for rib_y in (stand + 0.17, top - 0.2):
        parts.append(shapes.bevelled(shapes.box((-tank_half - 0.015, rib_y - 0.025, -tank_half - 0.015),
                                                (tank_half + 0.015, rib_y + 0.025, tank_half + 0.015),
                                                "plastic_white", "rib"), 0.012))
    for offset in (-0.42, 0.42):
        for sign in (-1, 1):
            parts.append(shapes.bevelled(shapes.box((offset - 0.03, stand + 0.06, sign * tank_half - 0.012),
                                                    (offset + 0.03, top - 0.06, sign * tank_half + 0.012),
                                                    "plastic_white", "rib"), 0.008))
            parts.append(shapes.bevelled(shapes.box((sign * tank_half - 0.012, stand + 0.06, offset - 0.03),
                                                    (sign * tank_half + 0.012, top - 0.06, offset + 0.03),
                                                    "plastic_white", "rib"), 0.008))
    # The lid hatch on top: its collar, the cover, the boss and four screws.
    parts.append(shapes.bevelled(shapes.cylinder((0.0, top - 0.01, 0.0), (0.0, top + 0.03, 0.0), 0.3,
                                                 "plastic_white", 32, "hatch"), 0.008))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, top + 0.03, 0.0), (0.0, top + 0.055, 0.0), 0.26,
                                                 "plastic_white", 32, "lid"), 0.006))
    parts.append(shapes.bevelled(shapes.cylinder((0.0, top + 0.055, 0.0), (0.0, tall, 0.0), 0.1, "plastic_white", 32,
                                                 "lid"), 0.006))
    for at in range(4):
        angle = math.pi / 4 + math.pi * at / 2
        x, z = 0.22 * math.cos(angle), 0.22 * math.sin(angle)
        parts.append(shapes.cylinder((x, top + 0.055, z), (x, top + 0.062, z), 0.012, "bare_steel", 12, "screw"))
    # The level sight tube up the front at the viewer's left, between its two fittings, its scale beside it.
    front = -tank_half
    tube_x, tube_z = tank_half - 0.2, front - 0.03
    parts.append(shapes.cylinder((tube_x, stand + 0.1, tube_z), (tube_x, top - 0.12, tube_z), 0.014, "glass", 16,
                                 "sight_tube"))
    for fitting_y in (stand + 0.07, top - 0.1):
        parts.append(shapes.bevelled(shapes.cylinder((tube_x, fitting_y - 0.035, tube_z),
                                                     (tube_x, fitting_y + 0.035, tube_z), 0.02, "plastic_white", 16,
                                                     "fitting"), 0.004))
        parts.append(shapes.cylinder((tube_x, fitting_y, front + 0.01), (tube_x, fitting_y, tube_z), 0.014,
                                     "plastic_white", 12, "fitting"))
    parts.append(shapes.box((tube_x - 0.035, stand + 0.12, front - 0.006), (tube_x - 0.02, top - 0.14, front),
                            "plastic_grey", "scale"))
    parts.append(label(-0.12, stand + 0.09, 0.24, 0.07, front, "label_water"))
    parts.append(label(-0.58, top - 0.36, 0.16, 0.12, front, "label_potable"))
    # The outlet: down out of the tank's foot, forward through the stand's front, a valve with its red lever.
    pipe_y, pipe_x, riser_z = stand - 0.16, 0.38, -0.35
    parts.append(shapes.cylinder((pipe_x, stand, riser_z), (pipe_x, pipe_y, riser_z), 0.035, "plastic_grey", 24,
                                 "pipe"))
    parts.append(wall_sphere((pipe_x, pipe_y, riser_z), 0.035, "plastic_grey", "pipe"))
    parts.append(shapes.cylinder((pipe_x, pipe_y, riser_z), (pipe_x, pipe_y, -half + 0.01), 0.035, "plastic_grey", 24,
                                 "pipe"))
    valve_z = -half + 0.14
    parts.append(shapes.bevelled(shapes.cylinder((pipe_x, pipe_y, valve_z - 0.06), (pipe_x, pipe_y, valve_z + 0.06),
                                                 0.055, "plastic_grey", 24, "valve"), 0.006))
    parts.append(shapes.bevelled(shapes.ring((pipe_x, pipe_y, -half + 0.03), (pipe_x, pipe_y, -half), 0.045, 0.026,
                                             "plastic_grey", 24, "pipe"), 0.003))
    parts.append(shapes.cylinder((pipe_x, pipe_y + 0.05, valve_z), (pipe_x, pipe_y + 0.08, valve_z), 0.012,
                                 "bare_steel", 12, "valve"))
    parts.append(shapes.bevelled(shapes.box((pipe_x - 0.015, pipe_y + 0.08, valve_z - 0.12),
                                            (pipe_x + 0.015, pipe_y + 0.1, valve_z + 0.015), "anodized_red", "lever"),
                                 0.004))
    return parts


def seedling_shelf(size, laid):
    """The open steel seedling rack, as its close-up shows it: four round-tube posts with caps and feet, three shelves
    (a plate in a frame of tube rails, clamps where the rails meet the posts), a long LED grow-light tube clipped
    under each shelf's front (a glowing lens between two end caps), and the power cable from the lamps down the
    viewer's left back post to the floor. The shelves are left empty: the seedling trays are children of their own."""
    wide, tall, deep = size
    post_x, post_z = wide / 2 - 0.02, deep / 2 - 0.02
    radius = 0.018
    parts = []
    for x in (-post_x, post_x):
        for z in (-post_z, post_z):
            parts.append(shapes.cylinder((x, 0.02, z), (x, tall - 0.02, z), radius, "galvanized_steel", 16, "post"))
            parts.append(shapes.bevelled(shapes.cylinder((x, tall - 0.02, z), (x, tall, z), radius + 0.002,
                                                         "galvanized_steel", 16, "cap"), 0.003))
            parts.append(shapes.cylinder((x, 0.0, z), (x, 0.02, z), radius + 0.002, "rubber", 16, "foot"))
    for shelf in GH_EQUIP_SHELVES:
        rail_y = shelf - 0.022
        parts.append(shapes.box((-post_x + 0.01, shelf - 0.012, -post_z + 0.01), (post_x - 0.01, shelf, post_z - 0.01),
                                "galvanized_dull", "shelf"))
        for z in (-post_z, post_z):
            parts.append(shapes.cylinder((-post_x, rail_y, z), (post_x, rail_y, z), 0.014, "galvanized_steel", 12,
                                         "rail"))
        for x in (-post_x, post_x):
            parts.append(shapes.cylinder((x, rail_y, -post_z), (x, rail_y, post_z), 0.014, "galvanized_steel", 12,
                                         "rail"))
            for z in (-post_z, post_z):
                parts.append(shapes.bevelled(shapes.cylinder((x, rail_y - 0.035, z), (x, rail_y + 0.03, z),
                                                             radius + 0.002, "bare_steel", 16, "clamp"), 0.003))
        # The grow-light tube clipped under the shelf's front.
        lamp_y, lamp_z = shelf - 0.075, -post_z + 0.06
        parts.append(shapes.cylinder((-post_x + 0.1, lamp_y, lamp_z), (post_x - 0.1, lamp_y, lamp_z), 0.022,
                                     "lamp_strip", 24, "lens"))
        for x in (-post_x + 0.1, post_x - 0.1):
            parts.append(shapes.bevelled(shapes.cylinder((x - 0.03, lamp_y, lamp_z), (x + 0.03, lamp_y, lamp_z),
                                                         0.026, "anodized_natural", 24, "lamp_cap"), 0.003))
        for x in (-0.5, 0.0, 0.5):
            parts.append(shapes.box((x - 0.02, lamp_y + 0.02, lamp_z - 0.006), (x + 0.02, shelf - 0.012,
                                                                                lamp_z + 0.006),
                                    "bare_steel", "lamp_clip"))
        # The lamp's lead back to the cable run on the viewer's left back post.
        parts.append(shapes.cylinder((post_x - 0.07, lamp_y, lamp_z), (post_x - 0.07, lamp_y, post_z - 0.03), 0.006,
                                     "cable_black", 8, "cable"))
        parts.append(shapes.cylinder((post_x - 0.07, lamp_y, post_z - 0.03), (post_x - 0.03, lamp_y, post_z - 0.03),
                                     0.006, "cable_black", 8, "cable"))
    cable_x, cable_z = post_x - 0.03, post_z - 0.03
    parts.append(shapes.cylinder((cable_x, GH_EQUIP_SHELVES[-1] - 0.075, cable_z), (cable_x, 0.12, cable_z), 0.008,
                                 "cable_black", 10, "cable"))
    parts.append(floor_bent_tube((cable_x - 0.1, 0.12, cable_z), (1, 0, 0), (0, 1, 0), 0.1, 0.008, 180.0, 360.0,
                                 "cable_black", "cable", steps=10, sides=10))
    parts.append(shapes.cylinder((cable_x - 0.2, 0.12, cable_z), (cable_x - 0.2, 0.008, cable_z), 0.008, "cable_black",
                                 10, "cable"))
    return parts


BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "backer", "cable_bundle", "cable_drop", "lattice_diamond_strut", "lattice_hip_rib", "lattice_node_plate",
    "lattice_ring_rib", "machine_bay_plate", "pipe_straight", "pit_floor_plate", "pit_wall_panel",
    "ring_floor_plate", "roof_face_panel", "stair_stringer", "under_floor_box", "wall_corner_post", "wall_cornice",
    "wall_lower_plain", "wall_skirting", "wall_upper_plain", "hull_plate", "hoop",
    # method B's fittings (hub round five)
    "hatch_frame", "hatch_leaf", "hatch_wheel", "hatch_window", "hatch_hinge", "hatch_wall_surround", "porthole_panel",
    "wall_lower_vent", "notice_board", "water_tank", "dosing_unit", "humidifier", "control_console", "work_desk", "seedling_shelf", "dock_pad_one", "dock_pad_two", "dock_pad_three", "charge_post", "seed_bin", "soil_bin", "crop_crate", "grow_light_bar", "grow_light_glow", "rig_rail", "rig_hanger", "irrigation_boom", "ledge_cover", "robot_bench", "arm_monitor", "equipment_bench", "low_cabinet", "floor_socket", "bay_mark", "tool_bench", "vise", "work_stool", "spares_shelves", "spares_crate", "spares_box", "elec_bench", "oscilloscope", "bench_meter", "soldering_station", "parts_drawers", "pendant_lamp", "door_frame", "door_leaf", "suit_alcove", "hose_reel", "suit_bench", "status_panel", "fan_unit", "crown_strip_lamp", "hull_patch", "sign_plate", "end_mat", "galley_counter", "mess_table", "stool", "exam_couch", "light_ring", "pot", "couch_pillow", "sleep_pod", "pillow", "locker_bank", "food_shelf", "food_jug", "food_tin", "ration_box", "med_cabinet", "med_box", "med_bottle", "hygiene_cubicle", "radio", "screwdriver", "talllocker", "rack", "comms", "console", "labbench", "toolboard", "waste_bin", "monitor", "keyboard", "glovebox", "floor_grating", "floor_access_hatch", "tread_mat", "ceiling_cable_tray", "ceiling_duct", "roof_apex_hub", "roof_light_fixture", "pipe_bracket", "pipe_elbow", "pipe_valve", "pit_junction_box", "wall_lower_patched", "wall_upper_patched", "wall_upper_cables", "wall_upper_pipes", "wall_upper_screen_recess", "status_display", "wall_screen_cluster", "intercom_panel", "small_readout", "door_control_box", "conduit_box", "wall_cage_lamp", "door_strip_lamp", "grab_bar",
    "wall_lower_vent", "notice_board", "rail_bracket", "lock_console", "lock_gauge_panel", "vent_grille", "hose_coil", "tool_case", "storage_case", "tool_case", "supply_cart", "gas_cylinder", "floor_marking", "slippers", "cable_coil", "tea_towel", "beacon", "door_frame", "door_leaf", "suit_alcove", "hose_reel", "suit_bench", "status_panel", "fan_unit", "crown_strip_lamp", "hull_patch", "sign_plate", "end_mat", "galley_counter", "mess_table", "stool", "exam_couch", "light_ring", "pot", "couch_pillow", "sleep_pod", "pillow", "locker_bank", "food_shelf", "food_jug", "food_tin", "ration_box", "med_cabinet", "med_box", "med_bottle", "hygiene_cubicle", "radio", "screwdriver", "talllocker", "rack", "comms", "console", "labbench", "toolboard", "waste_bin", "monitor", "keyboard", "glovebox", "floor_grating", "floor_access_hatch", "tread_mat", "ceiling_cable_tray", "ceiling_duct", "roof_apex_hub", "roof_light_fixture", "pipe_bracket", "pipe_elbow", "pipe_valve", "pit_junction_box", "wall_lower_patched", "wall_upper_patched", "wall_upper_cables", "wall_upper_pipes", "wall_upper_screen_recess", "status_display", "wall_screen_cluster", "intercom_panel", "small_readout", "door_control_box", "conduit_box", "wall_cage_lamp", "door_strip_lamp", "grab_bar",
    # the expedition camp's grounds (mars-build)
    "mast", "ground_cable",
    # the expedition camp habitat's
    "dome_wall_panel", "dome_window_panel", "dome_rib", "dome_ceiling_gore", "dome_roof_cap", "dome_deck_wedge", "dome_opening_frame", "passage_lining", "partition", "rod_lamp", "shell_gore", "shell_gore_window", "shell_gore_open", "foot_ring", "passage_hull", "pedestal_table", "sample_shelf", "stores_rack", "comms_desk", "hygiene", "case", "floor_cable", "crate", "crate_small", "ring_lamp", "wall_net")}

# Earth's rooms (the prologue build, 2026-10-07): each room's builders in a module of its own beside this one, its
# kinds shared with another room's by name (a plaster wall, a door, a print).
EARTH_ROOMS = ("earth_flat", "earth_stairwell")
for earth_room in EARTH_ROOMS:
    BUILDERS.update(importlib.import_module(earth_room).BUILDERS)

# The Earth places' plain pieces and fittings (world 1, 2026-10-07), in a module of their own; pieces_earth reads this
# module's helpers, which are all defined by here.
import pieces_earth  # noqa: E402

BUILDERS.update(pieces_earth.BUILDERS)


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
