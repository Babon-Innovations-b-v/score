"""Runs inside Blender: the prologue stairwell's fittings built in code (method B), each with every part its clean
close-up shows, every part named for its part and painted with a library variant of the stairwell's place.

    import earth_stairwell; parts = earth_stairwell.BUILDERS["stair_flight"]((1.35, 1.5, 2.6), {})

Sizes are (wide, tall, deep) in metres in the kit frame (shapes.py): x across (+x the viewer's left), y up from the
foot, the front toward -z and the back (against the wall) at +deep/2. The walls, ceiling, doors and prints the
stairwell shares with the flat are the flat's builders (earth_flat.py); its cables and conduits are the hub's.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import shapes

EDGE = 0.003
# A stair flight's finishes: the terrazzo tread's and riser's thickness, the steel nosing's depth along the going.
TREAD = 0.03
RISER = 0.02
NOSING = 0.045
STRING = 0.04  # the concrete stringer's thickness on the flight's open side (-x)
WAIST = 0.15  # the soffit slab's thickness square to its slope


# ---- shared shape helpers

def side_prism(outline, x_from, x_to, material, name):
    """A flat shape drawn in the kit's side plane, `outline` as (z, y) points, solid between two x positions."""
    built = bmesh.new()
    near = [built.verts.new(shapes.to_blender((x_from, height, depth))) for depth, height in outline]
    far = [built.verts.new(shapes.to_blender((x_to, height, depth))) for depth, height in outline]
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


def turned_about_depth(part, middle, degrees):
    """A part turned `degrees` about the kit's depth axis through `middle` (x, y): a diagonal lattice flat."""
    centre = shapes.to_blender((middle[0], middle[1], 0.0))
    part.data.transform(Matrix.Translation(centre) @ Matrix.Rotation(math.radians(degrees), 4, "Y")
                        @ Matrix.Translation(-centre))
    return part


def tube_frames(points):
    """For each point of a polyline: its tangent, a side vector carried along without twisting, and at a bend the
    bend's direction and how far a ring is stretched along it so the tube keeps its thickness round the bend."""
    found = []
    side = None
    for at, point in enumerate(points):
        before = points[max(0, at - 1)]
        after = points[min(len(points) - 1, at + 1)]
        tangent = (after - before).normalized()
        if side is None:
            helper = Vector((0.0, 1.0, 0.0)) if abs(tangent.y) < 0.9 else Vector((1.0, 0.0, 0.0))
            side = tangent.cross(helper).normalized()
        side = (side - tangent * side.dot(tangent)).normalized()
        bend, stretch = Vector((0.0, 0.0, 0.0)), 1.0
        if 0 < at < len(points) - 1:
            incoming, outgoing = (point - before).normalized(), (after - point).normalized()
            turn = outgoing - incoming
            turn -= tangent * turn.dot(tangent)
            if turn.length > 1e-6:
                bend = turn.normalized()
                stretch = 1.0 / max(0.5, math.cos(incoming.angle(tangent)))
        found.append((tangent, side, bend, stretch))
    return found


def tube(points, radius, material, name, sides=12):
    """A round tube along kit-frame points, mitred at its bends and capped at both ends: a wire, a bent rail."""
    points = [Vector(point) for point in points]
    built = bmesh.new()
    rings = []
    for point, (tangent, side, bend, stretch) in zip(points, tube_frames(points)):
        other = tangent.cross(side).normalized()
        ring = []
        for at in range(sides):
            angle = 2 * math.pi * at / sides
            offset = side * (math.cos(angle) * radius) + other * (math.sin(angle) * radius)
            offset += bend * (offset.dot(bend) * (stretch - 1.0))
            ring.append(built.verts.new(shapes.to_blender(point + offset)))
        rings.append(ring)
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


def ball(middle, radius, material, name, segments=16):
    """A ball at a kit-frame point: a rail's bend."""
    built = bmesh.new()
    bmesh.ops.create_uvsphere(built, u_segments=segments, v_segments=segments // 2, radius=radius)
    bmesh.ops.translate(built, verts=built.verts, vec=shapes.to_blender(middle))
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def cut_boxes(part, corners):
    """Boxes (pairs of kit-frame corners) taken out of a part in one cut: slots, pockets."""
    built = bmesh.new()
    for low, high in corners:
        cube = bmesh.ops.create_cube(built, size=1.0)["verts"]
        middle = (Vector(low) + Vector(high)) / 2
        size = Vector(high) - Vector(low)
        for vertex in cube:
            vertex.co = shapes.to_blender(Vector((middle.x + vertex.co.x * size.x, middle.y + vertex.co.y * size.y,
                                                  middle.z + vertex.co.z * size.z)))
    data = bpy.data.meshes.new("cutter")
    built.to_mesh(data)
    built.free()
    shapes.cut(part, shapes.mesh_object("cutter", data, "rubber"))
    return part


def frame_bars(low, high, rim, z_from, z_to, material, name="frame"):
    """A rectangular frame of four bars `rim` wide round the rectangle between two (x, y) corners."""
    (left, bottom), (right, top) = low, high
    bars = (((left, bottom), (left + rim, top)), ((right - rim, bottom), (right, top)),
            ((left + rim, bottom), (right - rim, bottom + rim)), ((left + rim, top - rim), (right - rim, top)))
    return [shapes.bevelled(shapes.box((*corner_low, z_from), (*corner_high, z_to), material, name), EDGE)
            for corner_low, corner_high in bars]


def knob(x, y, front, radius, long, material, name):
    """A round knob or lock barrel standing `long` out of a face at depth `front`, its root sunk into the face."""
    return shapes.bevelled(shapes.cylinder((x, y, front + 0.003), (x, y, front - long), radius, material, 16, name),
                           0.0015)


# ---- the stair flight: its step numbers are the game's walking collision, kept exact

def step_numbers(size):
    """Per step k = 1..8 counted from the top: (k, top, front z, back z). Nine equal risers of tall / 9 and eight
    goings of deep / 8: the foot (y 0) at the front edge, the top landing (y tall) beyond the back edge."""
    wide, tall, deep = size
    rise, going = tall / 9, deep / 8
    return [(step, tall - rise * step, deep / 2 - going * step, deep / 2 - going * (step - 1))
            for step in range(1, 9)]


def underside(size, depth):
    """The soffit's underside height at a depth: the line through the steps' inner corners, WAIST under it square to
    the slope."""
    wide, tall, deep = size
    slope = (tall / 9) / (deep / 8)
    return tall - tall / 9 + slope * (depth - deep / 2) - WAIST * math.sqrt(1 + slope * slope)


def underside_foot(size):
    """Where the soffit's underside meets the floor (its depth at y 0)."""
    wide, tall, deep = size
    slope = (tall / 9) / (deep / 8)
    return deep / 2 - (tall - tall / 9 - WAIST * math.sqrt(1 + slope * slope)) / slope


def step_finishes(size):
    """Every step's terrazzo tread with its steel nosing, and the terrazzo riser under its front edge."""
    wide, tall, deep = size
    left, right = wide / 2, -wide / 2 + STRING
    steps = step_numbers(size)
    parts = []
    for at, (step, top, front, back) in enumerate(steps):
        below = steps[at + 1][1] - TREAD if at + 1 < len(steps) else 0.0
        parts.append(shapes.bevelled(shapes.box((right, top - TREAD, front + NOSING), (left, top, back),
                                                "stair_terrazzo", "tread"), EDGE))
        parts.append(shapes.bevelled(shapes.box((right, top - TREAD, front - 0.004), (left, top, front + NOSING),
                                                "bare_steel", "nosing"), 0.002))
        parts.append(shapes.box((right, below, front), (left, top - TREAD, front + RISER), "stair_terrazzo", "riser"))
    return parts


def soffit_outline(size):
    """The flight's concrete body in side view (z, y): stepped under the finishes, its underside sloping WAIST under
    the steps down to the floor."""
    wide, tall, deep = size
    outline = [(-deep / 2 + RISER, 0.0)]
    for step, top, front, back in reversed(step_numbers(size)):
        outline += [(front + RISER, top - TREAD), (min(back + RISER, deep / 2), top - TREAD)]
    outline += [(deep / 2, underside(size, deep / 2)), (underside_foot(size), 0.0)]
    return outline


def stringer_outline(size):
    """The open side's stringer in side view (z, y): the steps' finished sawtooth over the soffit's underside."""
    wide, tall, deep = size
    outline = [(-deep / 2, 0.0)]
    for step, top, front, back in reversed(step_numbers(size)):
        outline += [(front, top), (back, top)]
    outline += [(deep / 2, underside(size, deep / 2)), (underside_foot(size), 0.0)]
    return outline


def stair_flight(size, laid):
    """A flight of eight terrazzo steps rising toward the back, as its close-up shows it: a tread with a steel nosing
    and a riser each, on a cast concrete soffit slab sloping with the flight, a concrete stringer face on its open side
    (-x). The ninth riser is the top landing's front edge."""
    wide, tall, deep = size
    parts = step_finishes(size)
    parts.append(side_prism(soffit_outline(size), -wide / 2 + STRING, wide / 2, "concrete", "soffit"))
    parts.append(side_prism(stringer_outline(size), -wide / 2, -wide / 2 + STRING, "concrete", "stringer"))
    return parts


def landing(size, laid):
    """A stair landing, as its close-up shows it: a concrete slab, a terrazzo top and a ribbed steel edge strip along
    its front edge, the top at y = tall."""
    wide, tall, deep = size
    front = -deep / 2
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, front), (wide / 2, tall - TREAD, deep / 2), "concrete",
                                        "slab"), EDGE),
             shapes.bevelled(shapes.box((-wide / 2, tall - TREAD, front + NOSING), (wide / 2, tall, deep / 2),
                                        "stair_terrazzo", "top"), EDGE),
             shapes.bevelled(shapes.box((-wide / 2, tall - 0.04, front - 0.004), (wide / 2, tall, front + NOSING),
                                        "bare_steel", "edge_strip"), 0.002)]
    for groove in (0.012, 0.024, 0.036):
        cut_boxes(parts[-1], [((-wide / 2 - 0.01, tall - 0.002, front + groove - 0.002),
                               (wide / 2 + 0.01, tall + 0.01, front + groove + 0.002))])
    return parts


# ---- the stair's wall handrail

def rail_height(size, x):
    """The handrail's centre height over its run: 0.9 at the low end (x = -wide/2), tall - 0.05 at the high end."""
    wide, tall, deep = size
    return 0.9 + (x + wide / 2) * (tall - 0.05 - 0.9) / wide


def rail_bracket(size, x, rail_z, radius):
    """One wall bracket under the rail at x: a round rose on the wall, an arm out of it bent up under the rail."""
    wide, tall, deep = size
    back = deep / 2
    low = rail_height(size, x) - 0.075
    return [shapes.bevelled(shapes.cylinder((x, low, back), (x, low, back - 0.006), 0.03, "rail_green", 24,
                                            "bracket"), 0.0015),
            tube([(x, low, back - 0.006), (x, low, rail_z), (x, rail_height(size, x) - radius + 0.004, rail_z)],
                 0.006, "rail_green", "bracket", 10)]


def stair_rail(size, laid):
    """A wall handrail, as its close-up shows it: a round steel rail rising along x (laid["rises_to"]: "+x" or
    "-x"), returned level at both ends, on three wall brackets with round roses."""
    wide, tall, deep = size
    radius = 0.021
    rail_z = deep / 2 - 0.08 + radius
    bend = wide / 2 - 0.15
    low, high = (-bend, rail_height(size, -bend), rail_z), (bend, rail_height(size, bend), rail_z)
    parts = [tube([low, high], radius, "rail_green", "rail", 20),
             ball(low, radius, "rail_green", "rail"), ball(high, radius, "rail_green", "rail"),
             tube([(-wide / 2, low[1], rail_z), low], radius, "rail_green", "end", 20),
             tube([high, (wide / 2, high[1], rail_z)], radius, "rail_green", "end", 20)]
    for x in (-wide / 2 + 0.4, 0.0, wide / 2 - 0.4):
        parts += rail_bracket(size, x, rail_z, radius)
    if laid.get("rises_to", "+x") == "-x":
        for part in parts:
            part.data.transform(Matrix.Scale(-1.0, 4, Vector((1.0, 0.0, 0.0))))
            part.data.flip_normals()
    return parts


# ---- gates

def gate_bars(xs, spans, z_from, z_to, thick, material="gate_grey"):
    """Upright flat bars at each x, each over the (y_from, y_to) spans given."""
    return [shapes.box((x - thick / 2, low, z_from), (x + thick / 2, high, z_to), material, "bar")
            for x in xs for low, high in spans]


def lattice_cells(left, right, bottom, top, pitch, front, material="gate_grey"):
    """A collapsible gate's lattice in one bay between two bars: stacked X's of thin flats."""
    cells = max(1, round((top - bottom) / pitch))
    tall = (top - bottom) / cells
    across = right - left
    long = math.hypot(across, tall)
    angle = math.degrees(math.atan2(tall, across))
    parts = []
    for cell in range(cells):
        middle = ((left + right) / 2, bottom + tall * (cell + 0.5))
        for sign in (-1, 1):
            flat = shapes.box((middle[0] - long / 2, middle[1] - 0.006, front), (middle[0] + long / 2, middle[1] + 0.006,
                                                                                 front + 0.004), material, "lattice")
            parts.append(turned_about_depth(flat, middle, sign * angle))
    return parts


def gate_hinges(x, heights, front, material="gate_grey"):
    """Barrel hinges on a gate's hinge edge at x: a knuckle and a leaf on the frame's face each."""
    parts = []
    for y in heights:
        parts.append(shapes.bevelled(shapes.cylinder((x, y - 0.06, front - 0.004), (x, y + 0.06, front - 0.004), 0.011,
                                                     material, 16, "hinge"), 0.0015))
    return parts


def security_gate(size, laid):
    """A folding steel security gate in front of a flat's door, as its close-up shows it: a box frame, upright flat
    bars, two cross rails, diagonal lattice top and bottom, a lock box on the viewer's left stile and barrel hinges
    on the right (-x)."""
    wide, tall, deep = size
    front, rim = -deep / 2, 0.04
    parts = frame_bars((-wide / 2, 0.0), (wide / 2, tall), rim, front, deep / 2, "gate_grey")
    inner = (-wide / 2 + rim, wide / 2 - rim)
    bays = 9
    xs = [inner[0] + (inner[1] - inner[0]) * at / bays for at in range(1, bays)]
    parts += gate_bars(xs, ((rim, tall - rim),), -0.012, 0.012, 0.014)
    for y in (0.88, 1.22):
        parts.append(shapes.bevelled(shapes.box((inner[0], y - 0.012, -0.014), (inner[1], y + 0.012, 0.014),
                                                "gate_grey", "bar"), 0.0015))
    edges = [inner[0]] + xs + [inner[1]]
    for left, right in zip(edges, edges[1:]):
        for bottom, top in ((0.12, 0.55), (1.26, 1.9)):
            parts += lattice_cells(left + 0.007, right - 0.007, bottom, top, 0.16, -0.0165)
    parts.append(shapes.bevelled(shapes.box((inner[1] - 0.12, 0.9, front - 0.03), (wide / 2 - 0.006, 1.2, front + 0.004),
                                            "gate_grey", "lock_box"), 0.003))
    parts.append(knob(inner[1] - 0.06, 1.1, front - 0.03, 0.011, 0.012, "bare_steel", "lock"))
    parts.append(knob(inner[1] - 0.06, 0.98, front - 0.03, 0.007, 0.006, "bare_steel", "lock"))
    parts += gate_hinges(-wide / 2 + 0.012, (0.3, tall / 2, tall - 0.3), front)
    return parts


def street_gate(size, laid):
    """A steel bar gate leaf to the street, as its close-up shows it: a box frame, square bars above and below a
    sheet steel lock plate framed by two rails, a pull handle and a lock on the plate, barrel hinges on the viewer's
    left (+x)."""
    wide, tall, deep = size
    front, rim = -deep / 2, 0.045
    plate = (0.75, 1.39)
    parts = frame_bars((-wide / 2, 0.0), (wide / 2, tall), rim, front, deep / 2, "gate_grey")
    inner = (-wide / 2 + rim, wide / 2 - rim)
    for y in plate:
        parts.append(shapes.bevelled(shapes.box((inner[0], y - 0.015, front + 0.005), (inner[1], y + 0.015, deep / 2 - 0.005),
                                                "gate_grey", "frame"), EDGE))
    parts.append(shapes.bevelled(shapes.box((inner[0], plate[0] + 0.015, -0.003), (inner[1], plate[1] - 0.015, 0.003),
                                            "gate_grey", "lock_plate"), 0.001))
    bays = 9
    xs = [inner[0] + (inner[1] - inner[0]) * at / bays for at in range(1, bays)]
    parts += gate_bars(xs, ((rim, plate[0] - 0.015), (plate[1] + 0.015, tall - rim)), -0.01, 0.01, 0.02)
    handle_x = inner[0] + 0.12
    parts.append(tube([(handle_x, 0.95, -0.003), (handle_x, 0.95, -0.05), (handle_x, 1.2, -0.05),
                       (handle_x, 1.2, -0.003)], 0.009, "bare_steel", "handle", 12))
    parts.append(knob(inner[0] + 0.05, 1.07, -0.003, 0.013, 0.012, "bare_steel", "lock"))
    parts += gate_hinges(wide / 2 - 0.012, (0.3, tall - 0.3), front)
    return parts


# ---- lamps and signs

def domed_globe(middle, across, depth, material, name, segments=24):
    """A glass dome standing out of a base toward the front: an ellipsoid's front half, `across` round and `depth`
    deep, its flat back on the base at `middle`."""
    built = bmesh.new()
    bmesh.ops.create_uvsphere(built, u_segments=segments, v_segments=segments // 2, radius=1.0)
    bmesh.ops.delete(built, geom=[vertex for vertex in built.verts if vertex.co.y < -1e-6], context="VERTS")
    bmesh.ops.holes_fill(built, edges=[edge for edge in built.edges if edge.is_boundary])
    for vertex in built.verts:
        x, front, y = vertex.co.x, vertex.co.y, vertex.co.z  # Blender +y is the kit's front (-z)
        kit = (middle[0] + x * across, middle[1] + y * across, middle[2] - max(front, 0.0) * depth)
        vertex.co = shapes.to_blender(kit)
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def cage_hoop(middle, across, depth, axis, offset, steps=12):
    """One wire hoop of a lamp cage over its dome: a half ellipse from the base ring out round the dome and back, in
    the plane `offset` off the middle along x (axis "x": an upright hoop) or along y (axis "y": a level hoop)."""
    reach = math.sqrt(max(across * across - offset * offset, 1e-6))
    bulge = depth * reach / across
    points = []
    for step in range(steps + 1):
        angle = math.pi * step / steps
        along, out = reach * math.cos(angle), bulge * math.sin(angle)
        if axis == "x":
            points.append((middle[0] + offset, middle[1] + along, middle[2] - out))
        else:
            points.append((middle[0] + along, middle[1] + offset, middle[2] - out))
    return points


def cage_bulkhead(size, laid):
    """A caged bulkhead lamp, as its close-up shows it: a round cast base on the wall with a rim, a glass globe
    standing out of it (glows), a wire cage of two upright and two level hoops over it on a ring."""
    wide, tall, deep = size
    back = deep / 2
    middle_y = tall / 2
    radius = min(wide, tall) / 2 - 0.005
    face = back - 0.05
    parts = [shapes.bevelled(shapes.cylinder((0.0, middle_y, back), (0.0, middle_y, face), radius, "post_dark", 32,
                                             "base"), 0.004),
             shapes.bevelled(shapes.ring((0.0, middle_y, face), (0.0, middle_y, face - 0.01), radius,
                                         radius - 0.018, "post_dark", 32, "base"), 0.002),
             domed_globe((0.0, middle_y, face), radius - 0.02, face + deep / 2 - 0.016, "lamp_lens", "globe")]
    cage_middle = (0.0, middle_y, face - 0.013)
    cage_across = radius - 0.012
    cage_depth = cage_middle[2] + deep / 2 - 0.004
    # The cage's ring stands on the base's rim, touching it, never inside it (an overlap read as a 2 mm wall).
    parts.append(shapes.ring((0.0, middle_y, face - 0.01), (0.0, middle_y, face - 0.016), cage_across + 0.004,
                             cage_across - 0.004, "bare_steel", 32, "cage"))
    for axis in ("x", "y"):
        for offset in (-0.033, 0.033):
            parts.append(tube(cage_hoop(cage_middle, cage_across, cage_depth, axis, offset), 0.0035, "bare_steel",
                              "cage", 8))
    return parts


def exit_sign(size, laid):
    """An exit sign, as its close-up shows it: a grey plastic box with rounded corners, its lit face (the exit_sign
    screen, which glows) set in a pocket in its front behind a narrow lip."""
    wide, tall, deep = size
    front, lip = -deep / 2, 0.016
    box = shapes.prism(rounded_outline((-wide / 2, 0.0), (wide / 2, tall), 0.012), front, deep / 2, "plastic_grey",
                       "box")
    cut_boxes(box, [((-wide / 2 + lip, lip, front - 0.01), (wide / 2 - lip, tall - lip, front + 0.008))])
    return [shapes.bevelled(box, 0.002),
            shapes.content_plate((-wide / 2 + lip, lip, front + 0.004), (wide / 2 - lip, tall - lip, front + 0.008),
                                 laid.get("screen", "exit_sign"), "face")]


def rounded_outline(low, high, radius, steps=4):
    """A rectangle's outline in the kit's x-y plane with its corners rounded to `radius`."""
    (left, bottom), (right, top) = low, high
    found = []
    for x, y, start in ((right - radius, top - radius, 0), (left + radius, top - radius, 90),
                        (left + radius, bottom + radius, 180), (right - radius, bottom + radius, 270)):
        for step in range(steps + 1):
            angle = math.radians(start + 90 * step / steps)
            found.append((x + radius * math.cos(angle), y + radius * math.sin(angle)))
    return found


# ---- boxes on the walls

def cabinet_doors(size, front, face):
    """The meter cabinet's four door panels: two meter doors over two cupboard doors, a gap between each."""
    wide, tall, deep = size
    margin, gap = 0.03, 0.006
    middle = 0.0
    rows = ((0.03, 0.33), (0.34, 0.6))
    parts = []
    for bottom, top in rows:
        for right, left in ((-wide / 2 + margin, middle - gap / 2), (middle + gap / 2, wide / 2 - margin)):
            parts.append(shapes.bevelled(shapes.box((right, bottom, front), (left, top, face), "gate_grey", "door"),
                                         0.002))
    return parts


def cabinet_meter(x, y, front):
    """A round electricity meter standing out through a meter door: its body and its glass window."""
    return [shapes.bevelled(shapes.cylinder((x, y, front + 0.003), (x, y, front - 0.026), 0.06, "plastic_grey", 32,
                                            "meter"), 0.003),
            shapes.bevelled(shapes.cylinder((x, y, front - 0.026), (x, y, front - 0.042), 0.05, "glass", 32,
                                            "meter_window"), 0.004)]


def cabinet_conduits(tall, top, back):
    """Conduit stubs out of the cabinet's top, each with a coupling collar."""
    parts = []
    for x, radius in ((0.17, 0.013), (0.1, 0.013), (0.02, 0.017), (-0.06, 0.01), (-0.11, 0.01), (-0.18, 0.013)):
        z = back - 0.05
        parts.append(shapes.cylinder((x, top, z), (x, tall, z), radius, "galvanized_dull", 16, "conduit_stub"))
        parts.append(shapes.bevelled(shapes.cylinder((x, top, z), (x, top + 0.025, z), radius + 0.006,
                                                     "galvanized_dull", 16, "conduit_stub"), 0.002))
    return parts


def meter_cabinet(size, laid):
    """A meter cabinet, as its close-up shows it: a grey steel cabinet with a lid, two meter doors each with a round
    meter and its window standing out through it, two cupboard doors with knob handles and hinges, conduit stubs out
    of its top."""
    wide, tall, deep = size
    front = -deep / 2 + 0.045  # the doors' face: the meters stand out in front of it
    face = front + 0.012
    top = tall - 0.08
    parts = [shapes.bevelled(shapes.box((-wide / 2 + 0.01, 0.0, face), (wide / 2 - 0.01, top - 0.02, deep / 2),
                                        "gate_grey", "cabinet"), EDGE),
             shapes.bevelled(shapes.box((-wide / 2, top - 0.02, front - 0.012), (wide / 2, top, deep / 2), "gate_grey",
                                        "cabinet"), EDGE)]
    parts += cabinet_doors(size, front, face)
    for x in (-0.12, 0.12):
        parts += cabinet_meter(x, 0.47, front)
    for x in (-0.035, 0.035):
        parts.append(knob(x, 0.16, front, 0.01, 0.014, "bare_steel", "handle"))
    for x in (-wide / 2 + 0.03, wide / 2 - 0.03):
        for y in (0.08, 0.28):
            parts.append(shapes.cylinder((x, y - 0.025, front - 0.004), (x, y + 0.025, front - 0.004), 0.006,
                                         "bare_steel", 12, "hinge"))
    parts += cabinet_conduits(tall, top, deep / 2)
    return parts


def letterbox_door(right, left, bottom, top, front, back):
    """One letterbox door: a steel plate with a letter slot and two vent slits through it (dark in their holes), a
    lock and a number holder."""
    middle = (right + left) / 2
    wide = left - right
    slot = ((middle - wide * 0.37, top - 0.045), (middle + wide * 0.37, top - 0.03))
    vents = [((middle - wide * 0.15, y - 0.004), (middle + wide * 0.15, y + 0.004)) for y in (bottom + 0.03,
                                                                                              bottom + 0.05)]
    plate = shapes.box((right, bottom, front), (left, top, back), "galvanized_dull", "door")
    cut_boxes(plate, [((*low, front - 0.01), (*high, back + 0.01)) for low, high in [slot] + vents])
    parts = [shapes.bevelled(plate, 0.0015),
             shapes.box((*slot[0], front + 0.003), (*slot[1], back + 0.004), "post_dark", "slot")]
    parts += [shapes.box((*low, front + 0.003), (*high, back + 0.004), "post_dark", "vent") for low, high in vents]
    parts.append(knob(left - 0.03, top - 0.08, front, 0.009, 0.006, "bare_steel", "lock"))
    holder = shapes.box((middle - 0.025, top - 0.075, front - 0.002), (middle + 0.025, top - 0.052, front + 0.004),
                        "bare_steel", "number_holder")
    parts.append(shapes.bevelled(holder, 0.001))
    return parts


def letterboxes(size, laid):
    """A bank of letterboxes, as its close-up shows it: a steel carcass and front frame of 4 x 3 boxes, a door each
    with a letter slot, vent slits, a lock and a number holder."""
    wide, tall, deep = size
    front = -deep / 2
    face = front + 0.01
    columns, rows, margin, gap = 4, 3, 0.03, 0.012
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, face), (wide / 2, tall, deep / 2), "galvanized_dull",
                                        "frame"), EDGE)]
    parts += frame_bars((-wide / 2, 0.0), (wide / 2, tall), margin, front, face, "galvanized_dull")
    door_wide = (wide - 2 * margin - gap * (columns - 1)) / columns
    door_tall = (tall - 2 * margin - gap * (rows - 1)) / rows
    for column in range(columns):
        right = -wide / 2 + margin + column * (door_wide + gap)
        if column:
            parts.append(shapes.box((right - gap, margin, front), (right, tall - margin, face), "galvanized_dull",
                                    "frame"))
        for row in range(rows):
            bottom = margin + row * (door_tall + gap)
            if row and not column:
                parts.append(shapes.box((-wide / 2 + margin, bottom - gap, front), (wide / 2 - margin, bottom, face),
                                        "galvanized_dull", "frame"))
            parts += letterbox_door(right + 0.002, right + door_wide - 0.002, bottom + 0.002,
                                    bottom + door_tall - 0.002, front + 0.003, face)
    return parts


# The lobby notice's drawing pins, (across, up) on its board from its viewer's-left top corner, as its close-up's
# sheets are pinned.
NOTICE_PINS = ((0.05, 0.93), (0.26, 0.94), (0.36, 0.95), (0.54, 0.95), (0.6, 0.94), (0.97, 0.95), (0.31, 0.73),
               (0.52, 0.55), (0.07, 0.43), (0.81, 0.5), (0.96, 0.52), (0.92, 0.66))


def lobby_notice(size, laid):
    """The lobby's notice board, as its close-up shows it: a timber frame round a board, the residents' sheets (one
    printed plate of them, lobby_sheets) and drawing pins at the sheets' heads."""
    wide, tall, deep = size
    front, rim = -deep / 2, 0.045
    board = front + 0.018
    parts = frame_bars((-wide / 2, 0.0), (wide / 2, tall), rim, front, deep / 2, "varnished_wood")
    parts.append(shapes.box((-wide / 2 + rim, rim, board), (wide / 2 - rim, tall - rim, deep / 2), "wood_board",
                            "board"))
    inset = rim + 0.03
    sheet = (-wide / 2 + inset, inset, wide / 2 - inset, tall - inset)
    parts.append(shapes.bevelled(shapes.content_plate((sheet[0], sheet[1], board - 0.004), (sheet[2], sheet[3], board),
                                                      laid.get("print", "lobby_sheets"), "sheet"), 0.0008))
    for across, up in NOTICE_PINS:
        x = sheet[2] - (sheet[2] - sheet[0]) * across
        y = sheet[1] + (sheet[3] - sheet[1]) * up
        parts.append(shapes.cylinder((x, y, board - 0.004), (x, y, board - 0.01), 0.006, "bare_steel", 12, "pin"))
    return parts


# ---- round two: the fire hose cabinet and the junction box

HOSE = 0.0125  # a fire hose's radius, flattened on its reel


def hose_reel_drum(middle, back):
    """A fire hose reel's steel: a rear flange disc on the cabinet's back, the drum, a hub at its front on the
    spindle and four spokes out of the hub."""
    x, y, z = middle
    parts = [shapes.bevelled(shapes.cylinder((x, y, back), (x, y, back - 0.008), 0.17, "warning_paint", 40, "reel"),
                             0.002),
             shapes.cylinder((x, y, back - 0.008), (x, y, z - 0.04), 0.07, "warning_paint", 32, "reel"),
             shapes.bevelled(shapes.cylinder((x, y, z - 0.04), (x, y, z - 0.062), 0.032, "bare_steel", 24, "reel"),
                             0.002)]
    for degrees in (0.0, 90.0):
        spoke = shapes.box((x - 0.16, y - 0.008, z - 0.056), (x + 0.16, y + 0.008, z - 0.044), "warning_paint", "reel")
        parts.append(shapes.bevelled(turned_about_depth(spoke, (x, y), degrees + 45.0), 0.0015))
    return parts


def hose_coils(middle, back):
    """The hose wound on the reel's drum: rings of hose layer on layer between the rear flange and the spokes."""
    x, y, z = middle
    parts = []
    for radius in (0.07 + HOSE, 0.07 + 3 * HOSE, 0.07 + 5 * HOSE):
        for depth in (z - 0.044 + HOSE, z - 0.044 + 3 * HOSE, z - 0.044 + 5 * HOSE, z - 0.044 + 7 * HOSE):
            if depth + HOSE > back - 0.008:
                continue
            points = [(x + radius * math.cos(2 * math.pi * at / 32), y + radius * math.sin(2 * math.pi * at / 32), depth)
                      for at in range(33)]
            parts.append(tube(points, HOSE * 0.95, "flag_red", "hose", 10))
    return parts


def hose_end(middle, front):
    """The hose's free end off the coil's foot to its nozzle, hung in a clip low in the cabinet."""
    x, y, z = middle
    start = (x + 0.02, y - 0.07 - 5 * HOSE, z - 0.044 + HOSE)
    clip = (x - 0.12, 0.09, front + 0.03)
    parts = [tube([start, (x - 0.05, y - 0.165, z - 0.03), (clip[0], clip[1] + 0.05, clip[2]), clip], HOSE * 0.95,
                  "flag_red", "hose", 10),
             shapes.bevelled(shapes.cylinder(clip, (clip[0], clip[1] - 0.07, clip[2]), 0.016, "bare_steel", 16,
                                             "nozzle"), 0.002)]
    return parts


def fire_hose_cabinet(size, laid):
    """A red steel fire hose reel cabinet on the wall, as its close-up shows it: the open-fronted cabinet, a door
    frame on hinges at the viewer's right (-x) with a glass panel over a mid rail and its lower light left open for
    the hose to be pulled out, a white label on the glass, a lever handle on the closing stile; inside, the reel and
    the coiled hose with its nozzle hung low."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    face = front + 0.02  # the door's face: its handle stands out in front of it
    rim, door = 0.035, face + 0.022
    body = shapes.box((-wide / 2, 0.0, door), (wide / 2, tall, back), "warning_paint", "cabinet")
    cut_boxes(body, [((-wide / 2 + 0.02, 0.02, door - 0.01), (wide / 2 - 0.02, tall - 0.02, back - 0.012))])
    parts = [shapes.bevelled(body, EDGE)]
    parts += frame_bars((-wide / 2, 0.0), (wide / 2, tall), rim, face, door, "warning_paint", "door_frame")
    split = (0.3, 0.34)
    parts.append(shapes.bevelled(shapes.box((-wide / 2 + rim, split[0], face), (wide / 2 - rim, split[1], door),
                                            "warning_paint", "door_frame"), EDGE))
    parts.append(shapes.box((-wide / 2 + rim - 0.004, split[1] - 0.004, face + 0.008),
                            (wide / 2 - rim + 0.004, tall - rim + 0.004, face + 0.012), "glass", "glass"))
    parts.append(shapes.content_plate((-0.075, 0.47, face + 0.008 - 0.0035), (0.075, 0.57, face + 0.008),
                                      "enamel_white", "label"))
    reel = (0.0, 0.3, 0.0)
    parts += hose_reel_drum(reel, back - 0.012) + hose_coils(reel, back - 0.012) + hose_end(reel, door)
    handle_x = wide / 2 - rim / 2
    parts.append(knob(handle_x, 0.36, face, 0.011, 0.012, "bare_steel", "handle"))
    parts.append(shapes.bevelled(shapes.box((handle_x - 0.006, 0.26, face - 0.02), (handle_x + 0.006, 0.37,
                                                                                   face - 0.008),
                                            "bare_steel", "handle"), 0.002))
    for y in (0.1, tall - 0.1):
        parts.append(shapes.cylinder((-wide / 2 + 0.007, y - 0.03, face - 0.001), (-wide / 2 + 0.007, y + 0.03,
                                                                                   face - 0.001),
                                     0.007, "bare_steel", 12, "hinge"))
    return parts


def junction_box(size, laid):
    """A small grey steel junction box on the wall, as its close-up shows it: the box, a cover on its front held by
    a screw at each corner, and two conduit stubs out of its top, each with a lock nut."""
    wide, tall, deep = size
    front, back = -deep / 2, deep / 2
    top = tall - 0.04
    cover = (front + 0.005, front + 0.012)
    parts = [shapes.bevelled(shapes.box((-wide / 2, 0.0, cover[1]), (wide / 2, top, back), "galvanized_dull", "box"),
                             EDGE),
             shapes.bevelled(shapes.box((-wide / 2 + 0.006, 0.006, cover[0]), (wide / 2 - 0.006, top - 0.006, cover[1]),
                                        "gate_grey", "cover"), 0.003)]
    for x in (-wide / 2 + 0.018, wide / 2 - 0.018):
        for y in (0.018, top - 0.018):
            parts.append(knob(x, y, cover[0], 0.0055, 0.004, "bare_steel", "screw"))
    for x in (-wide / 4, wide / 4):
        middle_z = (cover[1] + back) / 2
        parts.append(shapes.cylinder((x, top - 0.005, middle_z), (x, tall, middle_z), 0.011, "galvanized_dull", 16,
                                     "stub"))
        parts.append(shapes.bevelled(shapes.cylinder((x, top, middle_z), (x, top + 0.009, middle_z), 0.016,
                                                     "bare_steel", 6, "stub"), 0.001))
    return parts


BUILDERS = {"stair_flight": stair_flight, "landing": landing, "stair_rail": stair_rail,
            "security_gate": security_gate, "cage_bulkhead": cage_bulkhead, "meter_cabinet": meter_cabinet,
            "letterboxes": letterboxes, "lobby_notice": lobby_notice, "exit_sign": exit_sign,
            "street_gate": street_gate, "fire_hose_cabinet": fire_hose_cabinet, "junction_box": junction_box}
