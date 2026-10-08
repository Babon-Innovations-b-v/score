"""Runs inside Blender: the prologue flat's shell, fittings and furniture built in code (method B, round six's route),
and the shell kinds the stairwell shares (plaster_wall, plaster_ceiling, balcony_rail, timber_door_frame, timber_door_leaf,
wall_print). Each builder makes every part its clean close-up shows (prologue-build/pics/clean/<kind>.png), named
for the part (pieces.parts_seen reads the name), its material a library variant, in the kit frame (shapes.py): x
across (+x the viewer's left), y up from the foot, z from the front (-deep/2) to the back on the wall (+deep/2).

    import earth_flat; parts = earth_flat.BUILDERS["wardrobe"]((1.0, 1.9, 0.55), {})

No part is thinner than SHEET (the model check fails under 3 mm); a print is a content plate on a flat face of its
own piece, so pieces.prints_off finds a clear flat area behind it.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import shapes

EDGE = 0.003  # the bevel on a made part's edges
SHEET = 0.0035  # the thinnest any part is made: a print, a blade, a sheet of steel
SKIRTING = 0.1  # the plaster wall's dark kick band at its foot


# ---- Shared helpers ----------------------------------------------------------------------------------------------

def slab(low, high, material, name, edge=EDGE):
    """A box between two kit-frame corners with its edges bevelled."""
    return shapes.bevelled(shapes.box(low, high, material, name), edge)


def rod(start, end, radius, material, name, segments=12):
    """A round bar between two kit-frame points."""
    return shapes.cylinder(start, end, radius, material, segments, name)


def cone(start, end, radius_start, radius_end, material, name, segments=24):
    """A capped cone (a canopy, a motor's yoke) from one kit-frame point to another, its radius changing along it."""
    start, end = shapes.to_blender(start), shapes.to_blender(end)
    built = bmesh.new()
    bmesh.ops.create_cone(built, cap_ends=True, cap_tris=False, segments=segments, radius1=radius_start,
                          radius2=radius_end, depth=(end - start).length)
    turn = (end - start).to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(built, matrix=Matrix.Translation((start + end) / 2) @ turn, verts=built.verts)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def arc_tube(centre, across, up, bend, thick, start, end, material, name, steps=8, sides=12):
    """A round tube bent along an arc `bend` round `centre`, in the plane of the kit vectors `across` and `up`, from
    angle `start` to `end` (degrees, 0 along `across`); `thick` its own radius, capped at both ends."""
    centre, across, up = (Vector(value) for value in (centre, across, up))
    side = across.cross(up).normalized()
    built = bmesh.new()
    rings = []
    for step in range(steps + 1):
        angle = math.radians(start + (end - start) * step / steps)
        out = across * math.cos(angle) + up * math.sin(angle)
        middle = centre + out * bend
        rings.append([built.verts.new(shapes.to_blender(middle + (out * math.cos(turn) + side * math.sin(turn))
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


def turned(part, middle, degrees):
    """A part turned `degrees` about the kit frame's depth axis through `middle` (x, y): a sheet hung askew."""
    centre = shapes.to_blender((middle[0], middle[1], 0.0))
    part.data.transform(Matrix.Translation(centre) @ Matrix.Rotation(math.radians(degrees), 4, "Y")
                        @ Matrix.Translation(-centre))
    return part


def pitched(part, high, degrees):
    """A part tilted `degrees` about the kit frame's x axis through the height `high` (a fan blade's pitch)."""
    centre = shapes.to_blender((0.0, high, 0.0))
    part.data.transform(Matrix.Translation(centre) @ Matrix.Rotation(math.radians(degrees), 4, "X")
                        @ Matrix.Translation(-centre))
    return part


def spun(part, degrees):
    """A part turned `degrees` about the kit frame's up axis through its origin."""
    part.data.transform(Matrix.Rotation(math.radians(degrees), 4, "Z"))
    return part


def cut_box(part, low, high):
    """A box (kit-frame corners) taken out of a part: a pocket, a hole, a gap between feet."""
    shapes.cut(part, shapes.box(low, high, "rubber", "cutter"))
    return part


def kit_extent(part):
    """A part's lowest and highest kit-frame (x, y) corner."""
    points = [(vertex.co.x, vertex.co.z) for vertex in part.data.vertices]  # Blender z is the kit's y
    return ((min(point[0] for point in points), min(point[1] for point in points)),
            (max(point[0] for point in points), max(point[1] for point in points)))


def opened(parts, openings, deep):
    """The parts with the layout's openings ([x0, y0, x1, y1], kit frame) cut through them: a part reaching into an
    opening is cut, a part wholly inside one is left out."""
    kept = []
    for part in parts:
        low, high = kit_extent(part)
        inside = False
        for x0, y0, x1, y1 in openings:
            if high[0] <= x0 or x1 <= low[0] or high[1] <= y0 or y1 <= low[1]:
                continue
            if x0 <= low[0] and high[0] <= x1 and y0 <= low[1] and high[1] <= y1:
                inside = True
                break
            cut_box(part, (x0, y0, -deep - 0.05), (x1, y1, deep + 0.05))
        if inside:
            bpy.data.objects.remove(part, do_unlink=True)
        else:
            kept.append(part)
    return kept


def framed_panel(low, high, rim, front, thick, material, frame_name, panel_name):
    """A frame-and-panel leaf: a frame `rim` wide round a fielded panel set 6 mm back in it, between two (x, y)
    corners, its face at depth `front`, `thick` deep."""
    (left, bottom), (right, top) = low, high
    frame = shapes.box((left, bottom, front), (right, top, front + thick), material, frame_name)
    cut_box(frame, (left + rim, bottom + rim, front - 0.05), (right - rim, top - rim, front + thick + 0.05))
    panel = shapes.box((left + rim, bottom + rim, front + 0.006), (right - rim, top - rim, front + thick - 0.004),
                       material, panel_name)
    return [shapes.bevelled(frame, EDGE), shapes.bevelled(panel, 0.01)]


def pull(x, y, long, front, upright, name):
    """A bent iron pull on two short posts on a face at depth `front`: upright or lying along x."""
    stand = 0.022
    along = (0.0, long / 2) if upright else (long / 2, 0.0)
    ends = [(x - along[0], y - along[1]), (x + along[0], y + along[1])]
    parts = [rod((*ends[0], front - stand), (*ends[1], front - stand), 0.0055, "bare_steel", name)]
    for end_x, end_y in ends:
        parts.append(rod((end_x, end_y, front), (end_x, end_y, front - stand), 0.0055, "bare_steel", name))
    return parts


def knuckle(x, y, long, z, name="hinge"):
    """A hinge's knuckle: a short round barrel standing up at (x, z), `long` tall round `y`."""
    return rod((x, y - long / 2, z), (x, y + long / 2, z), 0.0055, "bare_steel", name, 10)


# ---- The shell -----------------------------------------------------------------------------------------------------

def plaster_wall(size, laid):
    """A plastered wall, as its close-up shows it: whitewash over a gloss dado to `dado`, a thin dark gloss line on
    the dado's top, a dark kick band at its foot; the layout's openings cut through it."""
    wide, tall, deep = size
    dado = float(laid.get("dado", 1.2))
    face = -deep / 2 + 0.008
    parts = [shapes.box((-wide / 2, dado, face), (wide / 2, tall, deep / 2), "whitewash", "plaster"),
             shapes.box((-wide / 2, SKIRTING, face), (wide / 2, dado, deep / 2), "gloss_dado", "dado"),
             shapes.box((-wide / 2, dado - 0.006, face - 0.004), (wide / 2, dado + 0.008, face), "post_dark",
                        "dado_line"),
             shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, SKIRTING, deep / 2), "gloss_dado", "skirting")]
    return [shapes.bevelled(part, 0.002) for part in opened(parts, laid.get("openings", []), deep)]


def plaster_ceiling(size, laid):
    """The flat's ceiling: one whitewashed plate (the layout lays it face down)."""
    wide, tall, deep = size
    return [slab((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "ceiling_whitewash", "ceiling", 0.002)]


def floorboards(size, laid):
    """The flat's floor: one plate of painted boards, its boards running along x (the library surface draws them)."""
    wide, tall, deep = size
    return [slab((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "painted_floorboards", "boards", 0.002)]


def render_wall(size, laid):
    """The outside face of the balcony wall: rendered and painted over a concrete plinth band at its foot; the
    layout's openings cut through it."""
    wide, tall, deep = size
    plinth = 0.15
    face = -deep / 2 + 0.008
    parts = [shapes.box((-wide / 2, plinth, face), (wide / 2, tall, deep / 2), "facade_paint", "render"),
             shapes.box((-wide / 2, 0.0, -deep / 2), (wide / 2, plinth, deep / 2), "concrete", "plinth")]
    return [shapes.bevelled(part, 0.002) for part in opened(parts, laid.get("openings", []), deep)]


def balcony_slab(size, laid):
    """The balcony's floor slab: a concrete slab, a terrazzo top and a drip strip under its outer (front) lip."""
    wide, tall, deep = size
    drip = 0.03
    top = 0.02
    return [slab((-wide / 2, drip, -deep / 2), (wide / 2, tall - top, deep / 2), "concrete", "slab", 0.006),
            slab((-wide / 2, tall - top, -deep / 2), (wide / 2, tall, deep / 2), "terrazzo_floor", "top", 0.004),
            slab((-wide / 2 + 0.03, 0.0, -deep / 2 + 0.03), (wide / 2 - 0.03, drip, -deep / 2 + 0.05), "concrete",
                 "drip", 0.003)]


def rail_posts(wide):
    """Where a balcony rail's posts stand along x: one at each end and one about every 1.6 m between."""
    spans = max(1, math.ceil((wide - 0.12) / 1.6))
    return [-wide / 2 + 0.06 + (wide - 0.12) * at / spans for at in range(spans + 1)]


def balcony_rail(size, laid):
    """A painted steel balcony rail, as its close-up shows it: square posts on base plates (one at each end and
    between), a flat top rail over them, a bottom rail near the floor and square bars between the rails about
    every 14 cm."""
    wide, tall, deep = size
    post = 0.05
    posts = rail_posts(wide)
    parts = [slab((-wide / 2, tall - 0.04, -deep / 2), (wide / 2, tall, deep / 2), "rail_green", "top_rail"),
             slab((-wide / 2 + 0.06, 0.1, -0.015), (wide / 2 - 0.06, 0.13, 0.015), "rail_green", "bottom_rail", 0.002)]
    for x in posts:
        parts.append(slab((x - post / 2, 0.008, -post / 2 + 0.005), (x + post / 2, tall - 0.04, post / 2 - 0.005),
                          "rail_green", "post"))
        parts.append(slab((x - 0.05, 0.0, -deep / 2), (x + 0.05, 0.008, deep / 2), "rail_green", "base_plate",
                          0.002))
    bars = round((wide - 0.12) / 0.14)
    for at in range(1, bars):
        x = -wide / 2 + 0.06 + (wide - 0.12) * at / bars
        if min(abs(x - spot) for spot in posts) < 0.06:
            continue
        parts.append(slab((x - 0.009, 0.13, -0.009), (x + 0.009, tall - 0.04, 0.009), "rail_green", "bar", 0.0015))
    return parts


def balcony_door_frame(size, laid):
    """The balcony door's painted steel frame, as its close-up shows it: jambs and a head round a 1.4 x 2.2 m
    opening, a transom bar over it, fixed glass over the bar split by a mullion, and the leaves' track at its foot."""
    wide, tall, deep = size
    side = (wide - 1.4) / 2
    door_top, bar = 2.2, 0.07
    head = tall - 0.07
    parts = [slab((-wide / 2, 0.0, -deep / 2), (-wide / 2 + side, tall, deep / 2), "grille_paint", "frame"),
             slab((wide / 2 - side, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "grille_paint", "frame"),
             slab((-wide / 2 + side, head, -deep / 2), (wide / 2 - side, tall, deep / 2), "grille_paint", "frame"),
             slab((-wide / 2 + side, door_top, -deep / 2 + 0.01), (wide / 2 - side, door_top + bar, deep / 2 - 0.01),
                  "grille_paint", "transom_bar"),
             slab((-0.015, door_top + bar, -0.02), (0.015, head, 0.02), "grille_paint", "mullion", 0.002),
             shapes.box((-wide / 2 + side, door_top + bar, -0.003), (wide / 2 - side, head, 0.003), "glass",
                        "transom_glass"),
             slab((-wide / 2 + side, 0.0, -deep / 2), (wide / 2 - side, 0.02, deep / 2), "grille_paint", "track", 0.002)]
    for z in (-0.02, 0.02):
        parts.append(slab((-wide / 2 + side, 0.02, z - 0.003), (wide / 2 - side, 0.034, z + 0.003), "bare_steel",
                          "track", 0.001))
    return parts


def sliding_glass_leaf(size, laid):
    """A sliding glass door leaf, as its close-up shows it: slim painted steel stiles and rails round one pane, a
    pull on its closing stile (the viewer's right, -x)."""
    wide, tall, deep = size
    stile, top_rail, bottom_rail = 0.05, 0.05, 0.07
    parts = [slab((-wide / 2, 0.0, -deep / 2), (-wide / 2 + stile, tall, deep / 2), "grille_paint", "stile"),
             slab((wide / 2 - stile, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "grille_paint", "stile"),
             slab((-wide / 2 + stile, tall - top_rail, -deep / 2), (wide / 2 - stile, tall, deep / 2), "grille_paint",
                  "rail"),
             slab((-wide / 2 + stile, 0.0, -deep / 2), (wide / 2 - stile, bottom_rail, deep / 2), "grille_paint",
                  "rail"),
             shapes.box((-wide / 2 + stile, bottom_rail, -0.003), (wide / 2 - stile, tall - top_rail, 0.003), "glass",
                        "glass")]
    parts += pull(-wide / 2 + stile / 2, tall * 0.46, 0.14, -deep / 2, True, "handle")
    return parts


def timber_door_frame(size, laid):
    """A timber door frame lining a 1.0 x 2.2 m doorway through a 0.2 m wall: jamb linings either side, a head
    lining over it and an architrave round its front."""
    wide, tall, deep = size
    half, top = 0.5, 2.2
    lining = 0.025
    front = -deep / 2
    face = front + 0.02  # the wall's face, where the architrave sits
    parts = [slab((half, 0.0, face), (half + lining, top + lining, deep / 2), "varnished_wood", "jamb"),
             slab((-half - lining, 0.0, face), (-half, top + lining, deep / 2), "varnished_wood", "jamb"),
             slab((-half, top, face), (half, top + lining, deep / 2), "varnished_wood", "head")]
    for side in (-1, 1):
        x0, x1 = sorted((side * (half + 0.005), side * wide / 2))
        parts.append(slab((x0, 0.0, front), (x1, top + 0.005, face), "varnished_wood", "architrave"))
    parts.append(slab((-wide / 2, top + 0.005, front), (wide / 2, tall, face), "varnished_wood", "architrave"))
    return parts


def timber_door_leaf(size, laid):
    """A painted timber flush door, as its close-up shows it: the flush leaf, a lever handle on a back plate with a
    keyhole, a barrel bolt over it, three hinges on its +x edge."""
    wide, tall, deep = size
    front = -deep / 2
    lock_x = -wide / 2 + 0.06
    parts = [slab((-wide / 2, 0.0, front), (wide / 2, tall, deep / 2), "enamel_white", "panel", 0.004),
             slab((lock_x - 0.022, 0.92, front - 0.005), (lock_x + 0.022, 1.12, front), "bare_steel", "lock", 0.002),
             rod((lock_x, 0.96, front - 0.005), (lock_x, 0.96, front - 0.0085), 0.0045, "rubber", "lock", 10),
             rod((lock_x, 1.07, front - 0.005), (lock_x, 1.07, front - 0.03), 0.009, "bare_steel", "handle"),
             rod((lock_x - 0.004, 1.07, front - 0.03), (lock_x + 0.12, 1.07, front - 0.03), 0.008, "bare_steel",
                 "handle"),
             slab((lock_x - 0.02, 1.27, front - 0.005), (lock_x + 0.06, 1.31, front), "bare_steel", "bolt", 0.001),
             rod((lock_x - 0.035, 1.29, front - 0.011), (lock_x + 0.06, 1.29, front - 0.011), 0.006, "bare_steel",
                 "bolt"),
             rod((lock_x + 0.02, 1.29, front - 0.011), (lock_x + 0.02, 1.29, front - 0.035), 0.004, "bare_steel",
                 "bolt", 8)]
    for y in (0.2, tall / 2, tall - 0.2):
        parts.append(knuckle(wide / 2, y, 0.1, front + 0.004))
    return parts


# ---- The furniture -------------------------------------------------------------------------------------------------

def wardrobe(size, laid):
    """A varnished wardrobe, as its close-up shows it: a plinth with bracket feet, the carcass, two frame-and-panel
    doors with bent iron handles at their meeting edges and a keyhole, small hinges, a drawer under them with two
    handles, and a stepped cornice."""
    wide, tall, deep = size
    front = -deep / 2
    body = front + 0.025  # the carcass's front, the doors and the drawer lie on it
    plinth, cornice = 0.1, tall - 0.12
    base = shapes.box((-wide / 2, 0.0, front), (wide / 2, plinth, deep / 2), "varnished_wood", "plinth")
    cut_box(base, (-wide / 2 + 0.07, -0.01, front - 0.05), (wide / 2 - 0.07, 0.035, deep / 2 - 0.05))
    parts = [shapes.bevelled(base, EDGE),
             slab((-wide / 2 + 0.02, plinth, body), (wide / 2 - 0.02, cornice, deep / 2), "varnished_wood", "carcass"),
             slab((-wide / 2 + 0.008, cornice, front + 0.01), (wide / 2 - 0.008, cornice + 0.04, deep / 2),
                  "varnished_wood", "cornice"),
             slab((-wide / 2, cornice + 0.04, front), (wide / 2, tall, deep / 2), "varnished_wood", "cornice")]
    parts.append(slab((-wide / 2 + 0.05, plinth + 0.02, front + 0.004), (wide / 2 - 0.05, plinth + 0.24, body),
                      "varnished_wood", "drawer"))
    for x in (-0.24, 0.24):
        parts += pull(x, plinth + 0.13, 0.1, front + 0.004, False, "drawer_handle")
    gap = 0.004
    door_bottom, door_top = plinth + 0.27, cornice - 0.02
    for side in (-1, 1):
        x0, x1 = sorted((side * gap / 2, side * (wide / 2 - 0.05)))
        parts += framed_panel((x0, door_bottom), (x1, door_top), 0.07, front + 0.003, body - front - 0.003,
                              "varnished_wood", "door", "door_panel")
        parts += pull(side * 0.035, door_bottom + 0.62, 0.11, front + 0.003, True, "handle")
        for y in (door_bottom + 0.15, door_top - 0.15):
            parts.append(knuckle(side * (wide / 2 - 0.05), y, 0.05, front + 0.006))
    parts.append(slab((-0.018, door_bottom + 0.5, front - 0.001), (-0.006, door_bottom + 0.53, front + 0.003),
                      "bare_steel", "keyhole", 0.001))
    return parts


def table(size, laid):
    """A varnished wooden table, as its close-up shows it: a top over four square legs joined by an apron."""
    wide, tall, deep = size
    top = 0.03
    leg = 0.05
    inset = 0.03
    under = tall - top
    parts = [slab((-wide / 2, under, -deep / 2), (wide / 2, tall, deep / 2), "varnished_wood", "top", 0.004)]
    corners = [(x, z) for x in (-wide / 2 + inset, wide / 2 - inset - leg) for z in (-deep / 2 + inset,
                                                                                     deep / 2 - inset - leg)]
    parts += [slab((x, 0.0, z), (x + leg, under, z + leg), "varnished_wood", "leg") for x, z in corners]
    left, right = wide / 2 - inset - leg, -wide / 2 + inset + leg
    near, far = -deep / 2 + inset + leg, deep / 2 - inset - leg
    apron = (under - 0.1, under)
    parts += [slab((right, apron[0], near - leg + 0.008), (left, apron[1], near - leg + 0.028), "varnished_wood",
                   "apron"),
              slab((right, apron[0], far + leg - 0.028), (left, apron[1], far + leg - 0.008), "varnished_wood", "apron"),
              slab((right - leg + 0.008, apron[0], near), (right - leg + 0.028, apron[1], far), "varnished_wood",
                   "apron"),
              slab((left + leg - 0.028, apron[0], near), (left + leg - 0.008, apron[1], far), "varnished_wood", "apron")]
    return parts


def timber_chair(size, laid):
    """A wooden timber_chair, as its close-up shows it: a seat at 0.45 m on an apron, two front legs, the back legs running
    up into the back posts, a top rail and a lower back rail with three slats between, side and front stretchers."""
    wide, tall, deep = size
    seat_top = 0.45
    seat = seat_top - 0.022
    leg = 0.034
    front, back = -deep / 2 + 0.01, deep / 2 - 0.01
    left, right = wide / 2 - 0.01, -wide / 2 + 0.01
    parts = [slab((-wide / 2, seat, -deep / 2), (wide / 2, seat_top, deep / 2 - 0.035), "varnished_wood", "seat", 0.005)]
    for x in (left - leg, right):
        parts.append(slab((x, 0.0, front), (x + leg, seat, front + leg), "varnished_wood", "leg"))
        parts.append(slab((x, 0.0, back - leg), (x + leg, seat, back), "varnished_wood", "leg"))
        parts.append(slab((x, seat, back - leg), (x + leg, tall, back), "varnished_wood", "back_post"))
        parts.append(slab((x + 0.006, 0.14, front + leg), (x + leg - 0.006, 0.165, back - leg), "varnished_wood",
                          "stretcher", 0.002))
        parts.append(slab((x + 0.008, seat - 0.06, front + leg), (x + leg - 0.008, seat, back - leg), "varnished_wood",
                          "apron", 0.002))
    parts.append(slab((right + leg, 0.2, front + 0.008), (left - leg, 0.225, front + leg - 0.008), "varnished_wood",
                      "stretcher", 0.002))
    parts.append(slab((right + leg, seat - 0.06, front + 0.006), (left - leg, seat, front + 0.026), "varnished_wood",
                      "apron", 0.002))
    rail_z = (back - leg + 0.008, back - 0.008)
    parts.append(slab((right + leg, tall - 0.075, rail_z[0]), (left - leg, tall - 0.005, rail_z[1]), "varnished_wood",
                      "back_rail"))
    parts.append(slab((right + leg, 0.6, rail_z[0]), (left - leg, 0.635, rail_z[1]), "varnished_wood", "back_rail"))
    for x in (-0.055, 0.0, 0.055):
        parts.append(slab((x - 0.012, 0.635, rail_z[0] + 0.003), (x + 0.012, tall - 0.075, rail_z[1] - 0.003),
                          "varnished_wood", "back_slat", 0.002))
    return parts


def tv_cabinet(size, laid):
    """A low varnished cabinet the television stands on, as its close-up shows it: a recessed plinth, the body, a
    top, two doors in a border with bent iron handles at their meeting edges, small hinges."""
    wide, tall, deep = size
    front = -deep / 2
    body = front + 0.02
    plinth, top = 0.05, tall - 0.03
    parts = [slab((-wide / 2 + 0.03, 0.0, front + 0.04), (wide / 2 - 0.03, plinth, deep / 2 - 0.02), "varnished_wood",
                  "plinth"),
             slab((-wide / 2, plinth, body), (wide / 2, top, deep / 2), "varnished_wood", "body"),
             slab((-wide / 2, top, front), (wide / 2, tall, deep / 2), "varnished_wood", "top")]
    for side in (-1, 1):
        x0, x1 = sorted((side * 0.003, side * (wide / 2 - 0.025)))
        parts.append(slab((x0, plinth + 0.02, front + 0.002), (x1, top - 0.02, body), "varnished_wood", "door"))
        parts += pull(side * 0.035, (plinth + top) / 2, 0.08, front + 0.002, True, "handle")
        for y in (plinth + 0.07, top - 0.07):
            parts.append(knuckle(side * (wide / 2 - 0.025), y, 0.04, front + 0.004))
    return parts


def kitchen_counter(size, laid):
    """The flat's kitchen counter, as its close-up shows it: two masonry piers faced with white tiles and a concrete
    back between them, a concrete worktop, a steel sink with a ribbed drainer in its right part (-x) and a swan-neck
    tap behind it, the sink's trap under it, an open timber shelf between the piers and a tiled splashback with a
    concrete cap; the worktop's left part (x 0.15 to 0.85) clear for the stove."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    worktop, tiles_top, splash = 0.85, 0.8, back - 0.03
    pier = 0.22
    parts = []
    for side in (-1, 1):
        x0, x1 = sorted((side * (wide / 2 - 0.008), side * (wide / 2 - pier)))
        parts.append(slab((x0, 0.0, front + 0.04), (x1, tiles_top, back), "concrete", "base"))
        parts.append(slab((x0, 0.0, front + 0.032), (x1, tiles_top, front + 0.04), "wall_tile_white", "tiles", 0.002))
        outer = sorted((side * (wide / 2 - 0.008), side * wide / 2))
        parts.append(slab((outer[0], 0.0, front + 0.032), (outer[1], tiles_top, back), "wall_tile_white", "tiles", 0.002))
    inner = wide / 2 - pier
    parts.append(slab((-inner, 0.0, back - 0.06), (inner, tiles_top, back), "concrete", "base"))
    top = shapes.box((-wide / 2, tiles_top, front), (wide / 2, worktop, splash), "concrete", "worktop")
    sink = (-0.72, -0.3, front + 0.1, splash - 0.13)  # x0, x1, z0, z1 of the bowl's opening
    cut_box(top, (sink[0], tiles_top - 0.05, sink[2]), (sink[1], worktop + 0.05, sink[3]))
    parts.append(shapes.bevelled(top, 0.006))
    parts += sink_bowl(sink, worktop)
    parts += drainer((sink[1], 0.08), (sink[2], sink[3]), worktop)
    parts += swan_tap((sink[0] + sink[1]) / 2, worktop, (sink[3] + splash) / 2, sink[3] - 0.04)
    parts += sink_trap((sink[0] + sink[1]) / 2, (sink[2] + sink[3]) / 2, worktop - 0.2, back - 0.06)
    parts.append(slab((-inner, 0.3, front + 0.08), (inner, 0.33, back - 0.06), "varnished_wood", "shelf"))
    parts.append(slab((-wide / 2, worktop, splash), (wide / 2, tall - 0.03, back), "wall_tile_white", "splashback",
                      0.002))
    parts.append(slab((-wide / 2, tall - 0.03, splash - 0.01), (wide / 2, tall, back), "concrete", "cap"))
    return parts


def sink_bowl(opening, worktop):
    """A pressed steel sink: an open bowl hanging under the worktop's hole, its rim lying on the worktop."""
    x0, x1, z0, z1 = opening
    bottom = worktop - 0.2
    wall = 0.004
    parts = [shapes.box((x0, bottom, z0), (x1, bottom + wall, z1), "bare_steel", "sink"),
             shapes.box((x0, bottom, z0), (x0 + wall, worktop, z1), "bare_steel", "sink"),
             shapes.box((x1 - wall, bottom, z0), (x1, worktop, z1), "bare_steel", "sink"),
             shapes.box((x0, bottom, z0), (x1, worktop, z0 + wall), "bare_steel", "sink"),
             shapes.box((x0, bottom, z1 - wall), (x1, worktop, z1), "bare_steel", "sink")]
    rim = shapes.box((x0 - 0.02, worktop, z0 - 0.02), (x1 + 0.0, worktop + 0.004, z1 + 0.02), "bare_steel", "sink")
    cut_box(rim, (x0 + wall, worktop - 0.01, z0 + wall), (x1 - wall, worktop + 0.01, z1 - wall))
    parts.append(shapes.bevelled(rim, 0.0015))
    return parts


def drainer(span_x, span_z, worktop):
    """The sink's drainer: a steel plate on the worktop beside the bowl with ribs running toward it."""
    (x0, x1), (z0, z1) = span_x, span_z
    parts = [slab((x0, worktop, z0 - 0.02), (x1, worktop + 0.004, z1 + 0.02), "bare_steel", "drainer", 0.0015)]
    for at in range(7):
        z = z0 + 0.02 + (z1 - z0 - 0.04) * at / 6
        parts.append(slab((x0 + 0.01, worktop + 0.004, z - 0.004), (x1 - 0.03, worktop + 0.009, z + 0.004),
                          "bare_steel", "drainer", 0.0015))
    return parts


def swan_tap(x, worktop, base_z, spout_z):
    """A swan-neck tap standing behind the sink: a foot, a riser, a bend over toward the bowl, the spout's tip and a
    lever on its side."""
    bend = (base_z - spout_z) / 2
    middle_z = (base_z + spout_z) / 2
    neck = worktop + 0.2
    return [rod((x, worktop, base_z), (x, worktop + 0.02, base_z), 0.022, "bare_steel", "tap", 16),
            rod((x, worktop + 0.02, base_z), (x, neck, base_z), 0.011, "bare_steel", "tap", 12),
            arc_tube((x, neck, middle_z), (0, 0, 1), (0, 1, 0), bend, 0.011, 0.0, 180.0, "bare_steel", "tap"),
            rod((x, neck, spout_z), (x, neck - 0.04, spout_z), 0.011, "bare_steel", "tap", 12),
            rod((x, worktop + 0.06, base_z), (x + 0.07, worktop + 0.075, base_z), 0.006, "bare_steel", "tap", 8)]


def sink_trap(x, z, bottom, wall_z):
    """The sink's trap under its bowl: a pipe down, a bulb and a pipe back into the wall."""
    low = bottom - 0.15
    return [rod((x, bottom, z), (x, low, z), 0.02, "plastic_white", "trap", 16),
            rod((x, low + 0.02, z), (x, low + 0.02, wall_z), 0.02, "plastic_white", "trap", 16),
            rod((x, bottom - 0.05, z), (x, bottom - 0.11, z), 0.03, "plastic_white", "trap", 16)]


def wall_shelf(size, laid):
    """A timber shelf, as its close-up shows it: a board on two steel brackets, each a strap screwed to the wall, an
    arm under the board and a brace between them."""
    wide, tall, deep = size
    board = 0.028
    under = tall - board
    back = deep / 2
    parts = [slab((-wide / 2, under, -deep / 2), (wide / 2, tall, back), "varnished_wood", "board", 0.004)]
    for x in (-wide / 2 + 0.2, wide / 2 - 0.2):
        parts.append(slab((x - 0.012, 0.0, back - 0.005), (x + 0.012, under, back), "bare_steel", "bracket", 0.001))
        parts.append(slab((x - 0.012, under - 0.005, -deep / 2 + 0.05), (x + 0.012, under, back - 0.005), "bare_steel",
                          "bracket", 0.001))
        reach, rise = deep - 0.07, under - 0.065
        brace = shapes.box((x - 0.006, -0.004, -math.hypot(reach, rise)), (x + 0.006, 0.004, 0.0), "bare_steel",
                           "bracket")
        brace.data.transform(Matrix.Rotation(math.atan2(rise, reach), 4, "X"))
        brace.data.transform(Matrix.Translation(shapes.to_blender((0.0, 0.06, back - 0.005))))
        parts.append(brace)
        parts.append(rod((x, 0.03, back - 0.005), (x, 0.03, back - 0.009), 0.004, "rubber", "screw", 8))
    return parts


def washbasin_stand(size, laid):
    """A wooden washbasin stand, as its close-up shows it: a top board with the round hole an enamel basin sits in
    (inner radius 0.19), an apron under it, four slender legs, a round towel rail on its +x side, and a low shelf of
    slats on two rails."""
    wide, tall, deep = size
    top = tall - 0.025
    leg = 0.034
    inset = 0.015
    board = shapes.box((-wide / 2, top, -deep / 2), (wide / 2, tall, deep / 2), "varnished_wood", "top")
    shapes.cut(board, shapes.cylinder((0.0, top - 0.05, 0.0), (0.0, tall + 0.05, 0.0), 0.19, "rubber", 40, "cutter"))
    parts = [shapes.bevelled(board, 0.004)]
    xs = (-wide / 2 + inset, wide / 2 - inset - leg)
    zs = (-deep / 2 + inset, deep / 2 - inset - leg)
    parts += [slab((x, 0.0, z), (x + leg, top, z + leg), "varnished_wood", "leg") for x in xs for z in zs]
    apron = (top - 0.07, top)
    parts += [slab((xs[0] + leg, apron[0], z + 0.006), (xs[1], apron[1], z + 0.026), "varnished_wood", "apron", 0.002)
              for z in (zs[0], zs[1] + leg - 0.032)]
    parts += [slab((x + 0.006, apron[0], zs[0] + leg), (x + 0.026, apron[1], zs[1]), "varnished_wood", "apron", 0.002)
              for x in (xs[0], xs[1] + leg - 0.032)]
    rail_x = xs[1] + leg / 2
    parts.append(rod((rail_x, top - 0.13, zs[0] + leg), (rail_x, top - 0.13, zs[1]), 0.011, "varnished_wood",
                     "towel_rail", 16))
    shelf = 0.16
    for x in (xs[0] + leg, xs[1] - 0.02):
        parts.append(slab((x, shelf - 0.03, zs[0] + leg), (x + 0.02, shelf, zs[1]), "varnished_wood", "shelf_rail",
                          0.002))
    span = zs[1] - zs[0] - leg
    for at in range(5):
        z = zs[0] + leg + span * (at + 0.5) / 5
        parts.append(slab((xs[0], shelf, z - 0.022), (xs[1] + leg, shelf + 0.014, z + 0.022), "varnished_wood",
                          "shelf", 0.002))
    return parts


def bedside_table(size, laid):
    """A small varnished bedside table, as its close-up shows it: a top over a body with one drawer and a round
    knob, on four square legs."""
    wide, tall, deep = size
    top = tall - 0.025
    leg = 0.034
    inset = 0.015
    body_low = top - 0.16
    front = -deep / 2 + inset
    parts = [slab((-wide / 2, top, -deep / 2), (wide / 2, tall, deep / 2), "varnished_wood", "top", 0.004)]
    parts += [slab((x, 0.0, z), (x + leg, top, z + leg), "varnished_wood", "leg")
              for x in (-wide / 2 + inset, wide / 2 - inset - leg) for z in (front, deep / 2 - inset - leg)]
    parts.append(slab((-wide / 2 + inset + 0.005, body_low, front + 0.005), (wide / 2 - inset - 0.005, top,
                                                                             deep / 2 - inset - 0.005),
                      "varnished_wood", "body"))
    parts.append(slab((-wide / 2 + inset + leg + 0.006, body_low + 0.015, front - 0.003),
                      (wide / 2 - inset - leg - 0.006, top - 0.015, front + 0.005), "varnished_wood", "drawer"))
    parts.append(rod((0.0, (body_low + top) / 2, front - 0.003), (0.0, (body_low + top) / 2, front - 0.024), 0.012,
                     "varnished_wood", "knob", 16))
    return parts


def bed_frame(size, laid):
    """A painted steel tube bed, as its close-up shows it: a head frame (at +x, 0.9 m) and a foot frame (0.6 m),
    each two posts bent over into a top rail with upright bars from a cross bar, the posts' feet below the side
    rails as legs on rubber caps, angle side rails at 0.35 m and a wire spring base between them."""
    wide, tall, deep = size
    tube = 0.016
    rail = 0.35
    end_x = wide / 2 - tube
    parts = []
    for x, frame_top, cross, name in ((end_x, tall, 0.42, "head_frame"), (-end_x, 0.6, 0.2, "foot_frame")):
        parts += bed_end(x, frame_top, cross, rail, deep / 2 - tube, tube, name)
    for side in (-1, 1):
        z = side * (deep / 2 - tube)
        inward = -side * 0.035
        parts.append(slab((-end_x + tube, rail - 0.035, z - 0.002), (end_x - tube, rail, z + 0.002), "rail_green",
                          "side_rail", 0.001))
        z0, z1 = sorted((z, z + inward))
        parts.append(slab((-end_x + tube, rail - 0.004, z0), (end_x - tube, rail, z1), "rail_green", "side_rail", 0.001))
    parts += spring_base(end_x - tube, deep / 2 - tube - 0.035, rail - 0.004)
    return parts


def bed_end(x, frame_top, cross, rail, half, tube, name):
    """One end of the tube bed: two posts (legs below the side rail, the frame above), a bend over at each top corner
    into the top rail, a cross bar, four upright bars and a rubber cap under each leg."""
    bend = 0.1
    shoulder = frame_top - tube - bend
    parts = [rod((x, frame_top - tube, -half + bend), (x, frame_top - tube, half - bend), tube, "rail_green", name, 16),
             rod((x, cross, -half), (x, cross, half), tube * 0.75, "rail_green", name, 12)]
    for side in (-1, 1):
        z = side * half
        parts.append(rod((x, 0.03, z), (x, rail, z), tube, "rail_green", "leg", 16))
        parts.append(rod((x, rail, z), (x, shoulder, z), tube, "rail_green", name, 16))
        parts.append(arc_tube((x, shoulder, side * (half - bend)), (0, 0, side), (0, 1, 0), bend, tube, 0.0, 90.0,
                              "rail_green", name, 8, 16))
        parts.append(rod((x, 0.0, z), (x, 0.035, z), tube + 0.003, "rubber", "foot", 16))
    for at in range(4):
        z = -half + 2 * half * (at + 1) / 5
        parts.append(rod((x, cross, z), (x, frame_top - tube, z), 0.008, "rail_green", "bar", 10))
    return parts


def spring_base(half_x, half_z, high):
    """A wire spring base inside the side rails: steel strips across it every 5 cm and five along it."""
    parts = []
    across = round(2 * half_x / 0.05)
    for at in range(across + 1):
        x = -half_x + 2 * half_x * at / across
        parts.append(shapes.box((x - 0.002, high - 0.004, -half_z), (x + 0.002, high, half_z), "bare_steel", "spring"))
    for at in range(5):
        z = -half_z + 2 * half_z * (at + 0.5) / 5
        parts.append(shapes.box((-half_x, high - 0.008, z - 0.002), (half_x, high - 0.004, z + 0.002), "bare_steel",
                                "spring"))
    return parts


def mattress(size, laid):
    """A thin cotton-ticking mattress with a piped seam round its top and bottom edges."""
    wide, tall, deep = size
    parts = [slab((-wide / 2, 0.0, -deep / 2), (wide / 2, tall, deep / 2), "cotton_white", "mattress", 0.02)]
    inset = 0.006
    for y in (0.006, tall - 0.006):
        for z in (-deep / 2 + inset, deep / 2 - inset):
            parts.append(rod((-wide / 2 + 0.012, y, z), (wide / 2 - 0.012, y, z), 0.006, "cotton_white", "seam", 10))
        for x in (-wide / 2 + inset, wide / 2 - inset):
            parts.append(rod((x, y, -deep / 2 + 0.012), (x, y, deep / 2 - 0.012), 0.006, "cotton_white", "seam", 10))
    return parts


def ceiling_fan(size, laid):
    """A ceiling fan hung from the ceiling, as its close-up shows it: a cup canopy against the ceiling (y = tall), a
    down rod, a round motor housing with a yoke over it, four blade arms and four pitched blades."""
    wide, tall, deep = size
    motor_top, motor_low = 0.2, 0.11
    parts = [cone((0.0, tall - 0.08, 0.0), (0.0, tall, 0.0), 0.04, 0.065, "plastic_white", "canopy"),
             rod((0.0, motor_top + 0.06, 0.0), (0.0, tall - 0.08, 0.0), 0.012, "plastic_white", "downrod", 16),
             cone((0.0, motor_top, 0.0), (0.0, motor_top + 0.06, 0.0), 0.06, 0.03, "hull_white_old", "motor"),
             shapes.bevelled(shapes.cylinder((0.0, motor_low, 0.0), (0.0, motor_top, 0.0), 0.11, "hull_white_old", 40,
                                             "motor"), 0.006),
             cone((0.0, motor_low - 0.025, 0.0), (0.0, motor_low, 0.0), 0.05, 0.11, "hull_white_old", "motor", 40)]
    radius = min(wide, deep) / 2
    blade_high = motor_low + 0.01
    for at in range(4):
        degrees = 45.0 + 90.0 * at
        arm = slab((0.08, blade_high - 0.006, -0.018), (0.2, blade_high, 0.018), "hull_white_old", "blade_arm", 0.0015)
        blade = slab((0.17, blade_high, -0.06), (radius, blade_high + SHEET + 0.001, 0.06), "plastic_white", "blade",
                     0.0015)
        pitched(blade, blade_high, 8.0)
        parts += [spun(arm, degrees), spun(blade, degrees)]
    return parts


def tube_light(size, laid):
    """A wall batten light, as its close-up shows it: a white metal housing (a back plate and a canopy over the tube),
    one tube (switched off) and a lampholder end cap at each end."""
    wide, tall, deep = size
    back = deep / 2
    parts = [slab((-wide / 2, 0.0, back - 0.012), (wide / 2, tall, back), "hull_white_old", "housing", 0.002),
             slab((-wide / 2, tall - 0.012, -deep / 2 + 0.01), (wide / 2, tall, back - 0.012), "hull_white_old",
                  "housing", 0.002),
             slab((-wide / 2, tall - 0.03, -deep / 2 + 0.01), (wide / 2, tall - 0.012, -deep / 2 + 0.016),
                  "hull_white_old", "housing", 0.0015)]
    tube_y, tube_z = tall * 0.42, -0.01
    for side in (-1, 1):
        x0, x1 = sorted((side * (wide / 2 - 0.004), side * (wide / 2 - 0.04)))
        parts.append(slab((x0, tube_y - 0.03, tube_z - 0.025), (x1, tube_y + 0.035, back - 0.012), "plastic_white",
                          "end_cap", 0.006))
    parts.append(rod((-wide / 2 + 0.04, tube_y, tube_z), (wide / 2 - 0.04, tube_y, tube_z), 0.013, "plastic_white",
                     "tube", 16))
    return parts


def wall_print(size, laid):
    """A picture on the wall (laid["print"], a print variant), as its close-up shows it: the sheet, in a varnished
    frame on a backing board when laid["frame"], or on its own card backing with a hanger strip and a nail when laid
    ["hanger"] (the calendar); laid["turn"] hangs it askew (the fu sign at 45 degrees)."""
    wide, tall, deep = size
    variant = laid.get("print", "flat_poster_red")
    back = deep / 2
    if laid.get("frame"):
        parts = framed_print(wide, tall, back, variant)
    else:
        parts = card_print(wide, tall, back, variant, laid.get("hanger", variant == "flat_calendar"))
    degrees = float(laid.get("turn", 0.0))
    if degrees:
        parts = [turned(part, (0.0, tall / 2), degrees) for part in parts]
    return parts


def framed_print(wide, tall, back, variant):
    """A picture in a varnished moulding frame over a backing board, the sheet lying on the board."""
    rim = 0.025
    frame = shapes.box((-wide / 2, 0.0, back - 0.02), (wide / 2, tall, back), "varnished_wood", "frame")
    cut_box(frame, (-wide / 2 + rim, rim, back - 0.05), (wide / 2 - rim, tall - rim, back + 0.05))
    board = shapes.box((-wide / 2 + rim, rim, back - 0.006), (wide / 2 - rim, tall - rim, back), "varnished_wood",
                       "backing")
    sheet = shapes.content_plate((-wide / 2 + rim, rim, back - 0.006 - SHEET), (wide / 2 - rim, tall - rim,
                                                                                back - 0.006), variant, "sheet")
    return [shapes.bevelled(frame, 0.004), board, sheet]


def card_print(wide, tall, back, variant, hanger):
    """A printed sheet on a card backing a little smaller than it, flat on the wall; with a hanger, a steel strip
    across its head and the nail it hangs from."""
    head = tall - 0.03 if hanger else tall
    parts = [shapes.box((-wide / 2 + 0.002, 0.002, back - SHEET), (wide / 2 - 0.002, head - 0.002, back), "cotton_white",
                        "backing"),
             shapes.content_plate((-wide / 2, 0.0, back - 2 * SHEET), (wide / 2, head, back - SHEET), variant, "sheet")]
    if hanger:
        parts.append(slab((-wide / 2, head - 0.012, back - 2 * SHEET - 0.004), (wide / 2, head + 0.004,
                                                                                back - SHEET), "bare_steel", "hanger",
                          0.001))
        parts.append(rod((0.0, tall - 0.012, back), (0.0, tall - 0.012, back - 0.02), 0.002, "bare_steel", "nail", 8))
        parts.append(rod((0.0, tall - 0.012, back - 0.018), (0.0, tall - 0.012, back - 0.022), 0.005, "bare_steel",
                         "nail", 12))
    return parts


# ---- Round two: the small things the picked concept shows -------------------------------------------------------

def lathe(profile, material, name, middle=(0.0, 0.0), segments=32):
    """A round solid turned about the kit's up axis through `middle` (x, z): `profile` is its closed outline as
    (radius, y) points; a point at radius 0 lies on the axis."""
    built = bmesh.new()
    rings = []
    for radius, high in profile:
        if radius <= 0.0:
            rings.append([built.verts.new(shapes.to_blender((middle[0], high, middle[1])))] * segments)
            continue
        rings.append([built.verts.new(shapes.to_blender((middle[0] + radius * math.cos(2 * math.pi * at / segments),
                                                          high,
                                                          middle[1] + radius * math.sin(2 * math.pi * at / segments))))
                      for at in range(segments)])
    for first, second in zip(rings, rings[1:] + rings[:1]):
        for at in range(segments):
            corners = list(dict.fromkeys([first[at], first[(at + 1) % segments], second[(at + 1) % segments],
                                          second[at]]))
            if len(corners) >= 3:
                built.faces.new(corners)
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def trunk_handle(side, wide, high):
    """A trunk's end handle on its +x (side 1) or -x (side -1) end: a steel plate, two lugs out of it and a bail
    hanging from them."""
    face = side * wide / 2
    plate_x = sorted((face, face + side * 0.004))
    reach = face + side * 0.016
    parts = [slab((plate_x[0], high - 0.035, -0.055), (plate_x[1], high + 0.02, 0.055), "bare_steel", "handle",
                  0.001)]
    for z in (-0.04, 0.04):
        parts.append(rod((face, high, z), (reach, high, z), 0.006, "bare_steel", "handle", 10))
        parts.append(rod((reach, high, z), (reach, high - 0.03, z), 0.005, "bare_steel", "handle", 10))
    parts.append(rod((reach, high - 0.03, -0.045), (reach, high - 0.03, 0.045), 0.0055, "bare_steel", "handle", 10))
    return parts


def trunk_hasp(lid_low, lid_front, body_front, front):
    """A trunk's hasp at the middle of its front: a steel strap hinged on the lid's face hanging down over a staple
    plate on the body, the staple's loop standing out through it."""
    return [slab((-0.018, lid_low - 0.05, lid_front - 0.004), (0.018, lid_low + 0.03, lid_front), "bare_steel", "hasp",
                 0.001),
            rod((-0.022, lid_low + 0.018, lid_front - 0.004), (0.022, lid_low + 0.018, lid_front - 0.004), 0.004,
                "bare_steel", "hasp", 10),
            slab((-0.02, lid_low - 0.085, body_front - 0.004), (0.02, lid_low - 0.045, body_front), "bare_steel",
                 "hasp", 0.001),
            rod((0.0, lid_low - 0.04, body_front), (0.0, lid_low - 0.04, front + 0.004), 0.0045, "bare_steel", "hasp",
                10)]


def storage_box(size, laid):
    """An old grey-painted metal trunk, as its close-up shows it on top of the wardrobe: the body with two pressed
    ribs round it, a lid with a lip over the body's top edge, a bail handle on each end and a hasp at the front."""
    wide, tall, deep = size
    lip = 0.006
    body_wide, body_deep = wide - 2 * 0.022, deep - 4 * lip
    lid_low = tall - 0.06
    parts = [slab((-body_wide / 2, 0.0, -body_deep / 2), (body_wide / 2, lid_low + 0.01, body_deep / 2), "gate_grey",
                  "body", 0.006),
             slab((-body_wide / 2 - lip, lid_low, -deep / 2 + lip), (body_wide / 2 + lip, tall, deep / 2 - lip),
                  "gate_grey", "lid", 0.008)]
    for y in (0.03, lid_low - 0.06):
        parts.append(slab((-body_wide / 2 - 0.004, y, -body_deep / 2 - 0.004),
                          (body_wide / 2 + 0.004, y + 0.016, body_deep / 2 + 0.004), "gate_grey", "body", 0.002))
    for side in (-1, 1):
        parts += trunk_handle(side, body_wide, lid_low - 0.04)
    parts += trunk_hasp(lid_low, -deep / 2 + lip, -body_deep / 2, -deep / 2)
    return parts


def tea_tin(size, laid):
    """A round tea tin, as its close-up shows it: a painted tin with a rounded foot, a push-on lid with a rounded
    top edge, and a gilt band printed round its middle."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2 - 0.002
    lid_low = tall - 0.026
    return [lathe([(0.0, 0.0), (radius - 0.003, 0.0), (radius - 0.001, 0.003), (radius - 0.001, lid_low + 0.004),
                   (0.0, lid_low + 0.004)], "warning_paint", "tin", segments=40),
            lathe([(0.0, lid_low), (radius + 0.003, lid_low), (radius + 0.003, tall - 0.004), (radius - 0.002, tall),
                   (0.0, tall)], "warning_paint", "lid", segments=40),
            # The band stands 4 mm proud of the tin's face, never a skin over it (a 1 mm one failed the model check).
            lathe([(radius - 0.001, 0.025), (radius + 0.003, 0.025), (radius + 0.003, 0.085), (radius - 0.001, 0.085)],
                  "anodized_gold", "band", segments=40)]


def towel_hook(tall, back, fold_y):
    """The towel's hook: a small steel plate screwed to the wall at the top back, an arm out of it and a tip turned
    up at its end."""
    tip_z = -back + 0.0045
    return [slab((-0.016, tall - 0.06, back - SHEET), (0.016, tall, back), "bare_steel", "hook", 0.001),
            rod((0.0, fold_y, back - SHEET), (0.0, fold_y, tip_z), 0.0035, "bare_steel", "hook", 10),
            rod((0.0, fold_y - 0.0035, tip_z), (0.0, tall - 0.012, tip_z), 0.0035, "bare_steel", "hook", 10)] + [
        rod((0.0, y, back - SHEET + 0.001), (0.0, y, back - SHEET - 0.003), 0.004, "bare_steel", "hook", 8)
        for y in (tall - 0.05, tall - 0.008)]


def hanging_towel(size, laid):
    """A cotton towel hung over a hook, as its close-up shows it: the hook (towel_hook), the towel folded over its arm
    into two layers, the front one longer with two soft folds down it, a hem across the foot of each."""
    wide, tall, deep = size
    fold_y, fold_z = tall - 0.035, 0.001
    outer, inner = 0.0115, 0.0075
    fold = shapes.ring((-wide / 2, fold_y, fold_z), (wide / 2, fold_y, fold_z), outer, inner, "cotton_white", 24,
                       "towel")
    cut_box(fold, (-wide, fold_y - 0.05, -0.05), (wide, fold_y, 0.05))
    front, behind = (fold_z - outer, fold_z - inner), (fold_z + inner, fold_z + outer)
    drapes = [rod((x, 0.0, front[0] + 0.003), (x, fold_y - 0.01, front[0] + 0.003), 0.007, "cotton_white", "towel", 12)
              for x in (-wide * 0.22, wide * 0.27)]
    return towel_hook(tall, deep / 2, fold_y) + drapes + [
        fold,
        slab((-wide / 2, 0.03, front[0]), (wide / 2, fold_y, front[1]), "cotton_white", "towel", 0.001),
        slab((-wide / 2 + 0.004, 0.11, behind[0]), (wide / 2 - 0.004, fold_y, behind[1]), "cotton_white", "towel",
             0.001),
        slab((-wide / 2, 0.0, front[0] - 0.0015), (wide / 2, 0.03, front[1]), "cotton_white", "hem", 0.0015),
        slab((-wide / 2 + 0.004, 0.08, behind[0]), (wide / 2 - 0.004, 0.11, behind[1] + 0.0015), "cotton_white",
             "hem", 0.0015)]


def pot_handle(side, radius, high):
    """One of a cooking pot's side handles: a steel loop lying level out of the pot's side, on two rivet bosses."""
    reach = 0.026
    parts = [arc_tube((side * (radius - 0.004), high, 0.0), (side, 0, 0), (0, 0, 1), reach, 0.004, -90.0, 90.0,
                      "bare_steel", "handle", 10, 10)]
    for z in (-reach, reach):
        parts.append(rod((side * (radius - 0.008), high, z), (side * (radius - 0.001), high, z), 0.0075, "bare_steel",
                         "handle", 10))
    return parts


def cooking_pot(size, laid):
    """A cooking pot, as its close-up shows it: a straight-sided pot with a rolled rim and a rounded foot, a domed
    lid sitting in the rim with a black knob on top, and a loop handle on each side."""
    wide, tall, deep = size
    radius = min(deep, wide - 0.07) / 2 - 0.002
    rim = 0.125
    pot = lathe([(0.0, 0.0), (radius - 0.012, 0.0), (radius - 0.002, 0.004), (radius, 0.014), (radius, rim - 0.004),
                 (radius + 0.004, rim - 0.002), (radius + 0.004, rim + 0.002), (radius - 0.004, rim + 0.002),
                 (radius - 0.004, rim - 0.01), (0.0, rim - 0.01)], "bare_steel", "pot", segments=40)
    lid = lathe([(0.0, rim - 0.006), (radius - 0.006, rim - 0.006), (radius - 0.006, rim + 0.002),
                 (radius + 0.002, rim + 0.004), (radius + 0.002, rim + 0.008), (radius - 0.03, rim + 0.016),
                 (0.03, tall - 0.024), (0.0, tall - 0.023)], "bare_steel", "lid", segments=40)
    knob = lathe([(0.0, tall - 0.03), (0.01, tall - 0.03), (0.008, tall - 0.018), (0.016, tall - 0.012),
                  (0.016, tall - 0.004), (0.012, tall), (0.0, tall)], "rubber", "knob", segments=20)
    parts = [pot, lid, knob]
    for side in (-1, 1):
        parts += pot_handle(side, radius, rim - 0.03)
    return parts


def line_height(line, radius):
    """The height of a straight line given as two (radius, y) ends, at a radius."""
    (start_r, start_y), (end_r, end_y) = line
    return start_y + (end_y - start_y) * (radius - start_r) / (end_r - start_r)


def flange_outline(low, high, inner, outer):
    """The cross-section (radius, y) of a plate's sloping flange between two radii, under it the line `low`, over it
    the line `high`."""
    return [(inner, line_height(low, inner)), (outer, line_height(low, outer)), (outer, line_height(high, outer)),
            (inner, line_height(high, inner))]


def plate(size, laid):
    """A porcelain plate, as its close-up shows it: a foot ring, a shallow well and a sloping flange whose outer
    band is the painted rim."""
    wide, tall, deep = size
    edge = min(wide, deep) / 2
    band = edge - 0.012
    low_line, high_line = ((0.08, 0.006), (edge, tall - 0.005)), ((0.077, 0.0105), (edge, tall))
    body = [(0.0, 0.0045), (0.066, 0.0045), (0.069, 0.0), (0.076, 0.0), (0.08, 0.006)]
    body += flange_outline(low_line, high_line, 0.08, band)[1:3] + [(0.077, 0.0105), (0.0, 0.0105)]
    rim = flange_outline(low_line, high_line, band, edge)
    rim[2:3] = [(edge, tall - 0.0015), (edge - 0.0015, tall)]
    return [lathe(body, "enamel_white", "plate", segments=48), lathe(rim, "anodized_gold", "rim", segments=48)]


BUILDERS = {
    "plaster_wall": plaster_wall, "plaster_ceiling": plaster_ceiling, "floorboards": floorboards,
    "render_wall": render_wall, "balcony_slab": balcony_slab, "balcony_rail": balcony_rail,
    "balcony_door_frame": balcony_door_frame, "sliding_glass_leaf": sliding_glass_leaf, "timber_door_frame": timber_door_frame,
    "timber_door_leaf": timber_door_leaf, "wardrobe": wardrobe, "table": table, "timber_chair": timber_chair, "tv_cabinet": tv_cabinet,
    "kitchen_counter": kitchen_counter, "wall_shelf": wall_shelf, "washbasin_stand": washbasin_stand,
    "bedside_table": bedside_table, "bed_frame": bed_frame, "mattress": mattress, "ceiling_fan": ceiling_fan,
    "tube_light": tube_light, "wall_print": wall_print,
    "storage_box": storage_box, "tea_tin": tea_tin, "hanging_towel": hanging_towel, "cooking_pot": cooking_pot,
    "plate": plate,
}
