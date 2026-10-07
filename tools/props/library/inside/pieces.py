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
                   "roof_light_fixture": 90.0}
FLOOR_PIPE_RADIUS = 0.038  # pipe_straight's: min(tall, deep) * 0.38 at 0.1


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
             shapes.cylinder((0.0, mouth - 0.006, 0.0), (0.0, mouth, 0.0), radius - 0.015, "glass_frosted", 40, "lens"),
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
    axis_z = -deep / 2 - 0.05  # the pipe's axis: the straight pipes stand on the bracket's front, 0.1 thick
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
    the run's axis (5 cm off the valve's back, where the straight pipes run), flanged stubs either side, a bonnet
    standing out of the body toward the room, the stem through a yoke, a red handwheel with spokes on its front, and
    a foot plate on the wall behind the body."""
    wide, tall, deep = size
    axis_y = tall / 2
    axis_z = deep / 2 - 0.05
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


def furn_louvres(plate, x, y, wide, tall, front, back, slats, material, name="louvre"):
    """Pressed louvres set into `plate` (front face at depth `front`, its back at `back`): a real hole through it, a
    dark back plate behind the hole and slanted hoods across it, standing a little proud of the face."""
    furn_cut_box(plate, (x - wide / 2, y - tall / 2, front - 0.05), (x + wide / 2, y + tall / 2, back))
    parts = [shapes.box((x - wide / 2, y - tall / 2, back - 0.003), (x + wide / 2, y + tall / 2, back),
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


BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "backer", "cable_bundle", "cable_drop", "lattice_diamond_strut", "lattice_hip_rib", "lattice_node_plate",
    "lattice_ring_rib", "machine_bay_plate", "pipe_straight", "pit_floor_plate", "pit_wall_panel",
    "ring_floor_plate", "roof_face_panel", "stair_stringer", "under_floor_box", "wall_corner_post", "wall_cornice",
    "wall_lower_plain", "wall_skirting", "wall_upper_plain",
    # method B's fittings (hub round five)
    "hatch_frame", "hatch_leaf", "hatch_wheel", "hatch_window", "hatch_hinge", "hatch_wall_surround", "porthole_panel",
    "wall_lower_vent", "notice_board", "radio", "screwdriver", "talllocker", "rack", "comms", "console", "labbench", "toolboard", "waste_bin", "monitor", "keyboard", "glovebox", "floor_grating", "floor_access_hatch", "tread_mat", "ceiling_cable_tray", "ceiling_duct", "roof_apex_hub", "roof_light_fixture", "pipe_bracket", "pipe_elbow", "pipe_valve", "pit_junction_box", "wall_lower_patched", "wall_upper_patched", "wall_upper_cables", "wall_upper_pipes", "wall_upper_screen_recess", "status_display", "wall_screen_cluster", "intercom_panel", "small_readout", "door_control_box", "conduit_box", "wall_cage_lamp", "door_strip_lamp", "grab_bar")}


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
