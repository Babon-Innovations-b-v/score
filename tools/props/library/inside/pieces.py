"""Runs inside Blender: the hub's plain plates, pipes and trims built in code (the sorter's allow-list, sorter.PLAIN:
the owner, 2026-10-07, code builds nothing with detail), each at the size the layout lays it, its parts naming their
library material.

    import pieces; whole = pieces.build("wall_upper_plain", (1.2, 2.0, 0.06), {"taper": 1.0})

Sizes are (wide, tall, deep) in metres in the kit frame (shapes.py): front toward -z, the back on the wall. Openings
are real holes at the shell's own sizes (the doorway 2.2 x 2.6 m, the porthole 0.6 m across), never a picture of
one.
"""

import numpy as np

import bpy
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


BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "backer", "cable_bundle", "cable_drop", "lattice_diamond_strut", "lattice_hip_rib", "lattice_node_plate",
    "lattice_ring_rib", "machine_bay_plate", "pipe_straight", "pit_floor_plate", "pit_wall_panel",
    "ring_floor_plate", "roof_face_panel", "stair_stringer", "under_floor_box", "wall_corner_post", "wall_cornice",
    "wall_lower_plain", "wall_skirting", "wall_upper_plain")}


def build(kind, size, laid, name):
    """One code-built piece of `kind` at `size`, as one object whose material slots name library materials."""
    return shapes.joined(BUILDERS[kind](tuple(size), laid), name)
