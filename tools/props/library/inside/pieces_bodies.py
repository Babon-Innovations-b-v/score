"""Runs inside Blender: the code-built bodies of big objects seen up close (PRD #10, the owner's rule of 2026-10-18),
each built from its numbers in bodies.py, every part one library surface. The bake (make_chunky.py) lays a body under
the details it keeps of its object's take; pieces.py takes BUILDERS in.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix  # noqa: E402

import bodies  # noqa: E402
import shapes  # noqa: E402

EDGE = 0.004
CONSOLE_EDGE = 0.006  # the console's shell edges, rounded a little more than a plate's
ROUND = 96  # segments round the module's hull and its rings
REACH = 2.0  # how far a cutter reaches past what it cuts, as a share of the thing's depth


def along_x(outline, x_from, x_to, material, name):
    """A flat shape solid between two points along the kit's x: `outline` in the (z, y) plane across it."""
    built = bmesh.new()
    near = [built.verts.new(shapes.to_blender((x_from, y, z))) for z, y in outline]
    far = [built.verts.new(shapes.to_blender((x_to, y, z))) for z, y in outline]
    built.faces.new(near)
    built.faces.new(list(reversed(far)))
    for at in range(len(outline)):
        following = (at + 1) % len(outline)
        built.faces.new([near[at], far[at], far[following], near[following]])
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def frustum(x_from, x_to, radius_from, radius_to, axis, material, name):
    """A round solid along the kit's x about (y, z) = `axis`, its radius going from one to the other."""
    start, end = shapes.to_blender((x_from, axis[0], axis[1])), shapes.to_blender((x_to, axis[0], axis[1]))
    built = bmesh.new()
    bmesh.ops.create_cone(built, cap_ends=True, cap_tris=False, segments=ROUND, radius1=radius_from,
                          radius2=radius_to, depth=(end - start).length)
    turn = (end - start).to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(built, matrix=Matrix.Translation((start + end) / 2) @ turn, verts=built.verts)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def arc(axis, inner, outer, first, last, segments):
    """An annular sector's outline in the (z, y) plane round `axis` (y, z), its angles in degrees from +z toward up."""
    angles = [math.radians(first + (last - first) * step / segments) for step in range(segments + 1)]
    outside = [(axis[1] + outer * math.cos(angle), axis[0] + outer * math.sin(angle)) for angle in angles]
    inside = [(axis[1] + inner * math.cos(angle), axis[0] + inner * math.sin(angle)) for angle in reversed(angles)]
    return outside + inside


def boxed(low, high, material, name, edge=EDGE):
    return shapes.bevelled(shapes.box(low, high, material, name), edge)


# --- the cockpit's main console --------------------------------------------------------------------------------------

def console_shell(size):
    """The console's shell: its outline from in front, solid from its face to its back, its top's back edge
    chamfered and its underside sloping up at the back, its edges rounded."""
    wide, tall, deep = size
    shell = shapes.bevelled(shapes.prism(bodies.console_outline(size), bodies.CONSOLE_FACE * deep,
                                         bodies.CONSOLE_BACK * deep, "dark_panel", "shell"), CONSOLE_EDGE)
    for (z0, y0), (z1, y1) in (bodies.CONSOLE_UNDER, bodies.CONSOLE_TOP_BACK):
        slope = (y1 - y0) * tall / ((z1 - z0) * deep)
        past = deep * 0.2
        line = [(z0 * deep - past, y0 * tall - slope * past), (z1 * deep + past, y1 * tall + slope * past)]
        beyond = -tall if y1 > y0 else tall * 2
        outline = line + [(line[1][0], beyond), (line[0][0], beyond)]
        shapes.cut(shell, along_x(outline, -wide, wide, "dark_panel", "cutter"))
    for low, high in bodies.console_bays(size).values():
        shapes.cut(shell, shapes.box(low, high, "dark_panel", "cutter"))
    return shell


def console_body(size, laid):
    """The cockpit's main console's body (2026-10-18, PRD #10: its take is lumpy, laid turned a quarter and stretched
    seven times across; the screens, lamps and button rows stay the model's, kept in the bays by the bake): a dark
    panelled shell with rounded upper corners, three bays sunk into its face for the model's controls, a hood over
    each wing's screen, the crown block over the middle, pillars between the bays and a kick plinth along its foot."""
    wide, tall, deep = size
    face = bodies.CONSOLE_FACE * deep
    parts = [console_shell(size)]
    height, front = bodies.CONSOLE_KICK
    parts.append(boxed((-wide / 2 + 0.03, 0.0, front * deep), (wide / 2 - 0.03, height * tall, face + 0.01),
                       "dark_panel", "kick"))
    for x0, x1, y0, y1, out in bodies.CONSOLE_HOODS:
        parts.append(boxed((x0 * wide, y0 * tall, out * deep), (x1 * wide, y1 * tall, face + 0.01), "dark_panel",
                           "hood"))
    x0, x1, y0, y1, out = bodies.CONSOLE_CROWN_BLOCK
    parts.append(boxed((x0 * wide, y0 * tall, out * deep), (x1 * wide, y1 * tall, face + 0.01), "dark_panel",
                       "crown"))
    for x0, x1, y0, y1, out in bodies.CONSOLE_PILLARS:
        parts.append(boxed((x0 * wide, y0 * tall, out * deep), (x1 * wide, y1 * tall, face + 0.01), "dark_panel",
                           "pillar"))
    return parts


# --- the old station's first module ----------------------------------------------------------------------------------

def module_hull(size, axis, radius):
    """The straight hull: a tube with a wall, open where the model has holes through it."""
    wide = size[0]
    start, end = bodies.MODULE_HULL[0] * wide, bodies.MODULE_HULL[1] * wide
    hull = shapes.ring((start, axis[0], axis[1]), (end, axis[0], axis[1]), radius,
                       radius * (1 - bodies.MODULE_SKIN), "galvanized_dull", ROUND, "hull")
    for first, last, x_from, x_to in bodies.module_holes(size):
        shapes.cut(hull, along_x(arc(axis, radius * 0.8, radius * 1.2, first, last, 12), x_from, x_to,
                                 "galvanized_dull", "cutter"))
    return hull


def module_ends(size, axis, radius):
    """The aft end tapered to its berthing drum, lip and white end plate; the front end tapered to a white bulkhead
    with its docking ring and white hatch."""
    wide = size[0]
    hull_from, hull_to = bodies.MODULE_HULL[0] * wide, bodies.MODULE_HULL[1] * wide
    aft, fore = bodies.MODULE_AFT, bodies.MODULE_FORE
    taper, taper_radius = aft["taper"][0] * wide, aft["taper"][1] * radius
    drum, lip = aft["drum"] * wide, aft["lip"][0] * wide
    parts = [frustum(hull_from, taper, radius, taper_radius, axis, "galvanized_dull", "taper"),
             shapes.cylinder((taper, axis[0], axis[1]), (drum, axis[0], axis[1]), taper_radius, "galvanized_dull",
                             ROUND, "drum"),
             shapes.ring((drum, axis[0], axis[1]), (lip, axis[0], axis[1]), taper_radius, aft["lip"][1] * radius,
                         "galvanized_dull", ROUND, "lip"),
             shapes.cylinder((drum, axis[0], axis[1]), (aft["plate"][0] * wide, axis[0], axis[1]),
                             aft["plate"][1] * radius, "hull_white_old", ROUND, "plate")]
    taper, taper_radius = fore["taper"][0] * wide, fore["taper"][1] * radius
    ring_to, ring_out, ring_in = fore["ring"][0] * wide, fore["ring"][1] * radius, fore["ring"][2] * radius
    parts += [frustum(hull_to, taper, radius, taper_radius, axis, "galvanized_dull", "taper"),
              shapes.cylinder((taper - 0.004, axis[0], axis[1]), (taper + 0.012, axis[0], axis[1]),
                              taper_radius * 0.98, "hull_white_old", ROUND, "bulkhead"),
              shapes.ring((taper, axis[0], axis[1]), (ring_to, axis[0], axis[1]), ring_out, ring_in,
                          "galvanized_dull", ROUND, "dock"),
              shapes.cylinder((taper, axis[0], axis[1]), (fore["hatch"][1] * wide, axis[0], axis[1]),
                              fore["hatch"][2] * radius, "hull_white_old", ROUND, "hatch")]
    return parts


def module_frames(size, axis, radius):
    """The ring frames round the hull, standing proud of its blankets."""
    wide = size[0]
    width, proud = bodies.MODULE_FRAME[0] * wide, bodies.MODULE_FRAME[1] * radius
    return [shapes.ring((at * wide - width / 2, axis[0], axis[1]), (at * wide + width / 2, axis[0], axis[1]),
                        radius * (1 + bodies.MODULE_FOIL_PROUD[1]) + proud, radius * (1 - bodies.MODULE_SKIN),
                        "galvanized_dull", ROUND, "frame")
            for at in bodies.MODULE_FRAMES]


def module_foil(size, axis, radius):
    """The insulation blankets over the hull where the model shows them, silver or gold, a small gap between each."""
    inner, outer = (radius * (1 + share) for share in bodies.MODULE_FOIL_PROUD)
    parts = []
    for material, first, last, x_from, x_to in bodies.module_foil(size):
        segments = max(2, round((last - first) / 5))
        parts.append(along_x(arc(axis, inner, outer, first + 0.4, last - 0.4, segments), x_from + 0.01, x_to - 0.01,
                             material, "blanket"))
    return parts


def module_cradles(size, axis, radius):
    """The two cradles the hull lies in, their saddles shaped to it, on two rails along the ground, and the access
    stand at its aft end."""
    wide, tall, deep = size
    half, thick, foot = bodies.MODULE_CRADLE[0] * deep, bodies.MODULE_CRADLE[1] * wide, bodies.MODULE_CRADLE[2] * tall
    reach = math.acos(half / radius)
    angles = [-reach - (math.pi - 2 * reach) * step / 16 for step in range(17)]
    saddle = [(-half, foot), (half, foot)] + [(radius * math.cos(angle), axis[0] + radius * math.sin(angle))
                                              for angle in angles]
    parts = [shapes.bevelled(along_x(saddle, at * wide - thick / 2, at * wide + thick / 2, "galvanized_dull",
                                     "cradle"), EDGE) for at in bodies.MODULE_CRADLES]
    rail_from, rail_to = (share * wide for share in bodies.MODULE_RAILS)
    for side in (-1.0, 1.0):
        parts.append(boxed((rail_from, 0.0, side * half - 0.08), (rail_to, foot, side * half + 0.08),
                           "galvanized_dull", "rail"))
    x, z, high = bodies.MODULE_STAND[0] * wide, bodies.MODULE_STAND[1] * deep, bodies.MODULE_STAND[2] * tall
    parts += [boxed((x - 0.15, 0.0, z - 0.15), (x + 0.15, 0.02, z + 0.15), "galvanized_dull", "stand"),
              shapes.cylinder((x, 0.02, z), (x, high, z), 0.04, "galvanized_dull", 16, "stand"),
              boxed((x - 0.1, high, z - 0.06), (x + 0.1, high + 0.04, z + 0.06), "galvanized_dull", "stand")]
    return parts


def station_module(size, laid):
    """The old station's first module's body (2026-10-18, PRD #10: its take's hull wanders and lumps): a straight
    grey hull holed where the model is holed, ring frames, silver and gold blankets laid where the model has them,
    the aft berthing drum and white end plate, the front docking ring and white hatch, two cradles on their rails and
    the access stand."""
    wide, tall, deep = size
    axis = (bodies.MODULE_AXIS * tall, 0.0)
    radius = bodies.MODULE_RADIUS * deep
    return ([module_hull(size, axis, radius)] + module_ends(size, axis, radius) + module_frames(size, axis, radius)
            + module_foil(size, axis, radius) + module_cradles(size, axis, radius))


BUILDERS = {"console_body": console_body, "station_module": station_module}
