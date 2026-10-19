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
from mathutils import Matrix, Vector  # noqa: E402

import bodies  # noqa: E402
import shapes  # noqa: E402

EDGE = 0.004
CONSOLE_EDGE = 0.006  # the console's shell edges, rounded a little more than a plate's
ROUND = 96  # segments round the module's hull and its rings
REACH = 2.0  # how far a cutter reaches past what it cuts, as a share of the thing's depth
BRACKET = 0.015  # a fuel tank cradle bracket's plate thickness (metres; over the model check's 3 mm)
WATER_DEPTH = 0.03  # the water tank's water: how thick its face is laid, under the water's level (metres)
PLATE_PROUD = 0.012  # how far the water tank's steel plate stands out of its lower box's front (metres)


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
    return cone((x_from, axis[0], axis[1]), (x_to, axis[0], axis[1]), radius_from, radius_to, material, name)


def cone(start, end, radius_from, radius_to, material, name, segments=ROUND):
    """A round solid from one kit-frame point to another, its radius going from one to the other."""
    start, end = shapes.to_blender(start), shapes.to_blender(end)
    built = bmesh.new()
    bmesh.ops.create_cone(built, cap_ends=True, cap_tris=False, segments=segments, radius1=radius_from,
                          radius2=radius_to, depth=(end - start).length)
    turn = (end - start).to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(built, matrix=Matrix.Translation((start + end) / 2) @ turn, verts=built.verts)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def turned_about_up(item, degrees):
    """A part turned about the kit's upright axis through its origin (the kit's y is Blender's z)."""
    item.data.transform(Matrix.Rotation(math.radians(degrees), 4, "Z"))
    return item


def pipe_run(points, radius, bend, material, name):
    """A round pipe through (x, y) points in the kit's upright plane through its middle, its corners bent round
    `bend` instead of meeting square; each corner's run in at least `bend` long."""
    path = [points[0]]
    for at in range(1, len(points) - 1):
        path += bent_corner(points[at - 1], points[at], points[at + 1], bend)
    path.append(points[-1])
    return swept_tube(path, radius, material, name)


def swept_tube(path, radius, material, name, segments=24):
    """One closed round tube along (x, y) points in the kit's upright plane through its middle (z 0), each ring
    square to the path there, its ends capped: a smooth bend, no seams between pieces."""
    built = bmesh.new()
    rings = []
    for at, point in enumerate(path):
        before, after = path[max(at - 1, 0)], path[min(at + 1, len(path) - 1)]
        along = (after[0] - before[0], after[1] - before[1])
        length = math.hypot(*along)
        across = (-along[1] / length, along[0] / length)
        rings.append([built.verts.new(shapes.to_blender((point[0] + across[0] * radius * math.cos(angle),
                                                         point[1] + across[1] * radius * math.cos(angle),
                                                         radius * math.sin(angle))))
                      for angle in (2 * math.pi * step / segments for step in range(segments))])
    for near, far in zip(rings, rings[1:]):
        for step in range(segments):
            following = (step + 1) % segments
            built.faces.new([near[step], far[step], far[following], near[following]])
    built.faces.new(rings[0])
    built.faces.new(list(reversed(rings[-1])))
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return [shapes.mesh_object(name, data, material)]


def bent_corner(before, corner, after, bend, steps=10):
    """The points round a pipe's bend at `corner` between two square runs, from `bend` short of it on the way in to
    `bend` past it on the way out."""
    inward = [corner[axis] - before[axis] for axis in range(2)]
    outward = [after[axis] - corner[axis] for axis in range(2)]
    inward = [value / math.hypot(*inward) for value in inward]
    outward = [value / math.hypot(*outward) for value in outward]
    middle = [corner[axis] - inward[axis] * bend + outward[axis] * bend for axis in range(2)]
    return [tuple(middle[axis] - outward[axis] * bend * math.cos(angle) + inward[axis] * bend * math.sin(angle)
                  for axis in range(2))
            for angle in (math.pi / 2 * step / steps for step in range(steps + 1))]


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


# --- the engine room's power core ------------------------------------------------------------------------------------

def core_plinth(size):
    """The square plinth: a dark slab, the hazard band round its sides standing proud of it, the dark top plate."""
    wide, tall, deep = size
    high, top, (band_from, band_to) = bodies.CORE_PLINTH
    inset = bodies.BAND_PROUD
    return [boxed((-wide / 2 + inset, 0.0, -deep / 2 + inset), (wide / 2 - inset, high * tall, deep / 2 - inset),
                  "dark_panel", "plinth"),
            boxed((-wide / 2, band_from * tall, -deep / 2), (wide / 2, band_to * tall, deep / 2), "hazard_paint",
                  "hazard"),
            boxed((-wide / 2, (high - top) * tall, -deep / 2), (wide / 2, high * tall, deep / 2), "dark_panel",
                  "plinth_top")]


def core_column(size):
    """The column from the plinth up: its stepped base drum, the paired steel flanges and the dark drums between,
    and four steel brackets round its foot at the diagonals."""
    wide, tall, _ = size
    parts = [shapes.bevelled(shapes.cylinder((0.0, low * tall, 0.0), (0.0, high * tall, 0.0), radius * wide, surface,
                                             ROUND, "column"), EDGE)
             for low, high, radius, surface in bodies.CORE_PROFILE]
    profile, half = bodies.CORE_BRACKET
    outline = [(reach * wide, up * tall) for reach, up in profile]
    for degrees in (45.0, 135.0, 225.0, 315.0):
        bracket = shapes.bevelled(shapes.prism(outline, -half * wide, half * wide, "bare_steel", "bracket"), EDGE)
        parts.append(turned_about_up(bracket, degrees))
    return parts


def core_chevrons(size):
    """The notched plates on the column's front and back at the ends of its middle, standing proud of it."""
    wide, tall, _ = size
    parts = []
    for low, high, foot, top in bodies.CORE_CHEVRONS:
        radius = core_drum_radius((low + high) / 2) * wide
        outline = [(-foot * wide, low * tall), (foot * wide, low * tall), (top * wide, high * tall),
                   (-top * wide, high * tall)]
        for side in (-1.0, 1.0):
            near, far = sorted((side * (radius + 0.006), side * (radius - 0.03)))
            parts.append(shapes.prism(outline, near, far, "bare_steel", "chevron"))
    return parts


def core_drum_radius(share):
    """The radius share of the column's drum at a height share: the profile's row there, else the hood's."""
    for low, high, radius, _ in bodies.CORE_PROFILE:
        if low <= share < high:
            return radius
    return bodies.CORE_HOOD[1]


def core_lamps(size):
    """The amber-lit rings round the column, each wrapping its drum and standing proud of it."""
    wide, tall, _ = size
    parts = []
    for low, high in bodies.CORE_LAMPS:
        radius = core_drum_radius((low + high) / 2) * wide
        parts.append(shapes.ring((0.0, low * tall, 0.0), (0.0, high * tall, 0.0), radius + bodies.BAND_PROUD,
                                 radius - 0.01, "led_amber", ROUND, "lamp"))
    return parts


def core_hood(size):
    """The hood on top: a drum its top cut on a slope down toward -x, the cowl standing at its low side and the
    hatch plate on its front."""
    wide, tall, deep = size
    foot, radius, high, low = bodies.CORE_HOOD
    radius *= wide
    hood = shapes.cylinder((0.0, foot * tall, 0.0), (0.0, high * tall + 0.05, 0.0), radius, "dark_panel", ROUND,
                           "hood")
    slope = (high - low) * tall / (2 * radius)
    middle = (high + low) / 2 * tall
    line = [(-wide, middle - slope * wide), (wide, middle + slope * wide)]
    shapes.cut(hood, shapes.prism(line + [(wide, tall * 2), (-wide, tall * 2)], -deep, deep, "dark_panel", "cutter"))
    parts = [shapes.bevelled(hood, EDGE)]
    x_from, x_to, half, y_from, y_to = bodies.CORE_COWL
    parts.append(boxed((x_from * wide, y_from * tall, -half * wide), (x_to * wide, y_to * tall, half * wide),
                       "dark_panel", "cowl"))
    x_from, x_to, y_from, y_to = bodies.CORE_HATCH
    back = -math.sqrt(radius ** 2 - max(abs(x_from), abs(x_to)) ** 2 * wide ** 2) + 0.01
    parts.append(boxed((x_from * wide, y_from * tall, -radius - 0.008), (x_to * wide, y_to * tall, back),
                       "dark_panel", "hatch"))
    return parts


def core_canister(size):
    """The coolant canister at +x: an upright drum with coned ends, two straps round it and two brackets holding it
    to the column."""
    wide, tall, _ = size
    held = bodies.CORE_CANISTER
    at, radius = held["at"] * wide, held["radius"] * wide
    (body_from, body_to), (tip_low, tip_high), tip = held["body"], held["tips"], held["tip"] * wide
    parts = [shapes.cylinder((at, body_from * tall, 0.0), (at, body_to * tall, 0.0), radius, "dark_panel", 48,
                             "canister"),
             cone((at, body_from * tall, 0.0), (at, tip_low * tall, 0.0), radius, tip, "dark_panel", "canister", 48),
             cone((at, body_to * tall, 0.0), (at, tip_high * tall, 0.0), radius, tip, "dark_panel", "canister", 48)]
    for strap in held["straps"]:
        parts.append(shapes.ring((at, strap * tall - 0.015, 0.0), (at, strap * tall + 0.015, 0.0), radius + 0.006,
                                 radius - 0.01, "bare_steel", 48, "strap"))
    column = core_drum_radius(held["brackets"][0]) * wide
    half_high, half_deep = (share * tall for share in held["bracket"])
    for bracket in held["brackets"]:
        parts.append(boxed((column - 0.02, bracket * tall - half_high, -half_deep),
                           (at - radius + 0.02, bracket * tall + half_high, half_deep), "bare_steel", "bracket"))
    return parts


def core_box(size):
    """The pump box at -x: a dark box set into the column, two steel pipe ports on its outer face and an amber lamp
    on its front."""
    wide, tall, _ = size
    outer, inner, half, low, high = bodies.CORE_BOX
    parts = [boxed((outer * wide, low * tall, -half * wide), (inner * wide, high * tall, half * wide), "dark_panel",
                   "pump_box")]
    heights, radius, stand = bodies.CORE_PORTS
    for port in heights:
        parts.append(shapes.cylinder((outer * wide + 0.01, port * tall, 0.0), (outer * wide - stand * wide, port * tall,
                                                                               0.0),
                                     radius * wide, "bare_steel", 32, "port"))
    x_from, x_to, y_from, y_to = bodies.CORE_BOX_LAMP
    parts.append(boxed((x_from * wide, y_from * tall, -half * wide - bodies.BAND_PROUD),
                       (x_to * wide, y_to * tall, -half * wide + bodies.BAND_PROUD), "led_amber", "lamp"))
    return parts


def core_pipes(size):
    """The teal coolant pipes: canister top into the hood, canister foot into the plinth, the cowl down into the
    box's upper port, the lower port into the plinth, each with a collar where it meets the plinth."""
    wide, tall, _ = size
    radius, bend = (share * wide for share in bodies.CORE_PIPE)
    plinth = bodies.CORE_PLINTH[0] * tall
    collar, collar_high = bodies.CORE_PIPE_COLLAR[0] * wide, bodies.CORE_PIPE_COLLAR[1] * tall
    parts = []
    for run in bodies.CORE_PIPES:
        points = [(reach * wide, up * tall) for reach, up in run]
        parts += pipe_run(points, radius, bend, bodies.CORE_PIPE_SURFACE, "pipe")
        foot = points[-1]
        if abs(foot[1] - plinth) < 1e-6:
            parts.append(shapes.cylinder((foot[0], plinth - 0.005, 0.0), (foot[0], plinth + collar_high, 0.0), collar,
                                         "bare_steel", 32, "collar"))
    return parts


def power_core(size, laid):
    """The engine room's power core's body (2026-10-18, PRD #10: its take is lumpy and laid at a slant on its plinth):
    an upright column on a square hazard-striped plinth, its stepped base held by four brackets, notched plates on
    its front and back, paired steel flanges with amber-lit rings between them and round its middle, the sloped hood
    on top with its cowl and hatch, the coolant canister at one side and the pump box at the other, and teal coolant
    pipes from both into the hood and down into the plinth."""
    return (core_plinth(size) + core_column(size) + core_chevrons(size) + core_lamps(size) + core_hood(size)
            + core_canister(size) + core_box(size) + core_pipes(size))


# --- the engine room's fuel tank -------------------------------------------------------------------------------------

def lathe(profile, axis, material, name):
    """A round solid about a vertical axis at (x, z) = `axis`: `profile` its (radius, height) points from its foot up,
    closed flat at both ends."""
    built = bmesh.new()
    rings = []
    for radius, height in profile:
        rings.append([built.verts.new(shapes.to_blender((axis[0] + radius * math.cos(2 * math.pi * step / ROUND),
                                                          height,
                                                          axis[1] + radius * math.sin(2 * math.pi * step / ROUND))))
                      for step in range(ROUND)])
    built.faces.new(rings[0])
    built.faces.new(list(reversed(rings[-1])))
    for lower, upper in zip(rings[:-1], rings[1:]):
        for step in range(ROUND):
            following = (step + 1) % ROUND
            built.faces.new([lower[step], lower[following], upper[following], upper[step]])
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def standing(outline, y_from, y_to, material, name):
    """A flat shape seen from above: `outline` in the kit's (x, z) plane, solid between two heights."""
    built = bmesh.new()
    low = [built.verts.new(shapes.to_blender((x, y_from, z))) for x, z in outline]
    high = [built.verts.new(shapes.to_blender((x, y_to, z))) for x, z in outline]
    built.faces.new(low)
    built.faces.new(list(reversed(high)))
    for at in range(len(outline)):
        following = (at + 1) % len(outline)
        built.faces.new([low[at], high[at], high[following], low[following]])
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def fuel_outline(size):
    """The fuel tank's outline up its axis, (radius, height): a half-ellipse lower dome, the straight shell and a
    half-ellipse top dome, each dome closed by a small flat boss where the drain and the pipes meet it."""
    wide, tall, deep = size
    radius = bodies.FUEL_RADIUS * deep
    foot, (shell_from, shell_to), crown = (bodies.FUEL_FOOT * tall, (bodies.FUEL_SHELL[0] * tall,
                                           bodies.FUEL_SHELL[1] * tall), bodies.FUEL_CROWN * tall)
    angles = [0.12 + (math.pi / 2 - 0.12) * step / 14 for step in range(15)]
    lower = [(radius * math.sin(angle), shell_from - (shell_from - foot) * math.cos(angle)) for angle in angles]
    upper = [(radius * math.sin(angle), shell_to + (crown - shell_to) * math.cos(angle)) for angle in reversed(angles)]
    return lower + upper


def fuel_cradle(size, axis, band):
    """The tank's dark steel cradle: a square frame on the floor, a post at each corner up to the lower band and a
    flat bracket from each post in to the band."""
    wide, tall, _ = size
    half, bar, frame = (bodies.FUEL_CRADLE[0] * wide, bodies.FUEL_CRADLE[1] * wide, bodies.FUEL_CRADLE[2] * tall)
    middle_x, middle_z = axis
    parts = square_frame(axis, half, bar, 0.0, frame, "dark_panel", "frame")
    band_from, band_to, band_radius = band
    corner = half - bar / 2
    for side_x in (-1.0, 1.0):
        for side_z in (-1.0, 1.0):
            post_x, post_z = middle_x + side_x * corner, middle_z + side_z * corner
            parts.append(boxed((post_x - bar / 2, frame, post_z - bar / 2), (post_x + bar / 2, band_to, post_z + bar / 2),
                               "dark_panel", "post"))
            along = (side_x / math.sqrt(2), side_z / math.sqrt(2))
            across = (-along[1] * BRACKET / 2, along[0] * BRACKET / 2)
            start, end = band_radius - 0.005, corner * math.sqrt(2)
            outline = [(middle_x + along[0] * reach + across[0] * sign, middle_z + along[1] * reach + across[1] * sign)
                       for reach, sign in ((start, 1), (end, 1), (end, -1), (start, -1))]
            parts.append(standing(outline, band_from, band_to, "dark_panel", "bracket"))
    return parts


def fuel_tank(size, laid):
    """The engine room's fuel tank's body (2026-10-18, PRD #10: its take is squashed front to back and lumpy; its
    gauge, valve and top pipe fittings stay the model's): a round white upright tank with domed ends, two dark bands
    round it, a drain stub under it, standing in a square dark steel cradle bracketed to its lower band."""
    wide, tall, deep = size
    axis = (0.0, bodies.FUEL_AXIS * deep)
    radius = bodies.FUEL_RADIUS * deep
    parts = [lathe(fuel_outline(size), axis, "hull_white_gloss", "tank")]
    band_radius = radius * (1 + bodies.FUEL_BAND_PROUD)
    for band_from, band_to in bodies.FUEL_BANDS:
        parts.append(shapes.ring((axis[0], band_from * tall, axis[1]), (axis[0], band_to * tall, axis[1]), band_radius,
                                 radius * 0.97, "dark_panel", ROUND, "band"))
    lower_band = (bodies.FUEL_BANDS[0][0] * tall, bodies.FUEL_BANDS[0][1] * tall, band_radius)
    parts += fuel_cradle(size, axis, lower_band)
    parts.append(shapes.cylinder((axis[0], bodies.FUEL_CRADLE[2] * tall, axis[1]),
                                 (axis[0], bodies.FUEL_FOOT * tall + 0.02, axis[1]), bodies.FUEL_DRAIN * wide,
                                 "hull_white_gloss", 24, "drain"))
    return parts


# --- the greenhouse's water tank -------------------------------------------------------------------------------------

def square_frame(middle, half, width, y_from, y_to, material, name):
    """A square frame of four beams round a vertical axis at (x, z) = `middle`: its outer half side and its beams'
    width."""
    x, z = middle
    return [boxed((x - half, y_from, z - half), (x + half, y_to, z - half + width), material, name),
            boxed((x - half, y_from, z + half - width), (x + half, y_to, z + half), material, name),
            boxed((x - half, y_from, z - half + width), (x - half + width, y_to, z + half - width), material, name),
            boxed((x + half - width, y_from, z - half + width), (x + half, y_to, z + half - width), material, name)]


def water_stand(size):
    """The tank's steel stand: a leg at each corner under a square top frame the tank's foot rests on."""
    wide, tall, _ = size
    half, side = bodies.WATER_LEGS[0] * wide, bodies.WATER_LEGS[1] * wide
    apron_from, apron_to, beam = (bodies.WATER_APRON[0] * tall, bodies.WATER_APRON[1] * tall,
                                  bodies.WATER_APRON[2] * wide)
    parts = square_frame((0.0, 0.0), half, beam, apron_from, apron_to, "bare_steel", "apron")
    for side_x in (-1.0, 1.0):
        for side_z in (-1.0, 1.0):
            corner_x, corner_z = side_x * (half - side / 2), side_z * (half - side / 2)
            parts.append(boxed((corner_x - side / 2, 0.0, corner_z - side / 2),
                               (corner_x + side / 2, apron_from, corner_z + side / 2), "bare_steel", "leg"))
    return parts


def water_boxes(size):
    """The cream tank: the lower box, the lip round its top, the upper box with its rim band, open at the top down to
    the water, the water's face, the overflow box in the rim's back corner and the steel plate on the lower box."""
    wide, tall, _ = size
    lower_from, lower_to, lower_half = (bodies.WATER_LOWER[0] * tall, bodies.WATER_LOWER[1] * tall,
                                        bodies.WATER_LOWER[2] * wide)
    lip_from, lip_to, lip_half = bodies.WATER_LIP[0] * tall, bodies.WATER_LIP[1] * tall, bodies.WATER_LIP[2] * wide
    upper_from, top, upper_half = (bodies.WATER_UPPER[0] * tall, bodies.WATER_UPPER[1] * tall,
                                   bodies.WATER_UPPER[2] * wide)
    rim_from, rim_half = bodies.WATER_RIM[0] * tall, bodies.WATER_RIM[1] * wide
    inside, level = upper_half - bodies.WATER_WALL * wide, bodies.WATER_LEVEL * tall
    upper = boxed((-upper_half, upper_from, -upper_half), (upper_half, rim_from, upper_half), "cream_paint", "upper")
    rim = boxed((-rim_half, rim_from, -rim_half), (rim_half, top, rim_half), "cream_paint", "rim")
    for shell in (upper, rim):
        shapes.cut(shell, shapes.box((-inside, level - WATER_DEPTH, -inside), (inside, top + 0.1, inside),
                                     "cream_paint", "cutter"))
    x0, x1, z0, z1 = (share * wide for share in bodies.WATER_OVERFLOW)
    px0, px1, py0, py1 = (bodies.WATER_PLATE[0] * wide, bodies.WATER_PLATE[1] * wide, bodies.WATER_PLATE[2] * tall,
                          bodies.WATER_PLATE[3] * tall)
    return [boxed((-lower_half, lower_from, -lower_half), (lower_half, lower_to, lower_half), "cream_paint", "lower"),
            boxed((-lip_half, lip_from, -lip_half), (lip_half, lip_to, lip_half), "cream_paint", "lip"), upper, rim,
            shapes.box((-inside + 0.001, level - WATER_DEPTH, -inside + 0.001), (inside - 0.001, level, inside - 0.001),
                       "glass", "water"),
            boxed((x0, level - WATER_DEPTH, z0), (x1, top, z1), "cream_paint", "overflow"),
            boxed((px0, py0, -lower_half - PLATE_PROUD), (px1, py1, -lower_half + 0.005), "bare_steel", "plate")]


def water_tank(size, laid):
    """The greenhouse's water tank's body (2026-10-18, PRD #10: its take is laid 18.5 degrees off square, its boxes
    twisted and its stand's top sloping): a square cream tank of two stacked boxes with a lip between them, open at
    the top to its water, an overflow box in the rim's corner and a steel plate on its front, on a four-legged steel
    stand."""
    return water_stand(size) + water_boxes(size)


# --- the campgrounds' landed lander ----------------------------------------------------------------------------------

def lathed(profile, middle, material, name, closed=False):
    """A round solid about an upright axis through `middle` (x, z): `profile` (radius, height) points swept round it,
    a point on the axis (radius 0) one vertex; `closed` joins the last point back to the first (a hollow ring)."""
    built = bmesh.new()
    rings = []
    for radius, height in profile:
        if radius <= 0.0:
            rings.append([built.verts.new(shapes.to_blender((middle[0], height, middle[1])))])
            continue
        rings.append([built.verts.new(shapes.to_blender((middle[0] + radius * math.cos(2 * math.pi * step / ROUND),
                                                         height,
                                                         middle[1] + radius * math.sin(2 * math.pi * step / ROUND))))
                      for step in range(ROUND)])
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for lower, upper in pairs:
        for step in range(ROUND):
            following = (step + 1) % ROUND
            corners = [lower[step % len(lower)], lower[following % len(lower)], upper[following % len(upper)],
                       upper[step % len(upper)]]
            unique = list(dict.fromkeys(corners))
            if len(unique) >= 3:
                built.faces.new(unique)
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def round_point(middle, radius, angle, height):
    """The kit-frame point `radius` out from an upright axis through `middle` (x, z), `angle` degrees round from +x
    toward +z, at a height."""
    turn = math.radians(angle)
    return (middle[0] + radius * math.cos(turn), height, middle[1] + radius * math.sin(turn))


def lander_hull(size, middle):
    """The hull and its ogive nose in one piece, its cargo bay cut into its foot at the front and its front cut flat
    where the decal stencil is laid."""
    wide, tall, _ = size
    radius = bodies.LANDER_RADIUS * wide
    hull = lathed(bodies.lander_profile(size), middle, "stainless", "hull")
    door = bodies.LANDER_DOOR
    half, back = door["half"] * wide, middle[1] - door["back"] * radius
    shapes.cut(hull, shapes.box((-half, door["sill"] * tall, middle[1] - radius * 2), (half, door["top"] * tall, back),
                                "stainless", "cutter"))
    across, low, high = bodies.LANDER_PANEL
    flat = middle[1] - math.sqrt(radius ** 2 - (across * wide) ** 2)
    shapes.cut(hull, shapes.box((-across * wide, low * tall, middle[1] - radius * 2),
                                (across * wide, high * tall, flat), "stainless", "cutter"))
    return hull


def lander_seams(size, middle):
    """The weld seams round the hull, a metre apart, standing a few millimetres proud."""
    wide, tall, _ = size
    radius = bodies.LANDER_RADIUS * wide
    first, last, count = bodies.LANDER_SEAMS
    height, proud = bodies.LANDER_SEAM[0] * tall, bodies.LANDER_SEAM[1] * radius
    seams = []
    for step in range(count):
        level = (first + (last - first) * step / (count - 1)) * tall
        seams.append(shapes.ring((middle[0], level - height / 2, middle[1]), (middle[0], level + height / 2, middle[1]),
                                 radius + proud, radius - 0.02, "stainless", ROUND, "seam"))
    return seams


def lander_fins(size, middle):
    """The two aft fins and the two forward flaps on the nose, flat plates across x either side, their roots sunk
    into the hull."""
    wide, tall, deep = size
    radius = bodies.LANDER_RADIUS * wide
    aft, fore = bodies.LANDER_AFT_FIN, bodies.LANDER_FORE_FLAP
    root_low, root_high = (share * tall for share in aft["root"])
    edge_low, edge_high = (share * tall for share in aft["edge"])
    inner, outer = radius * 0.8, wide / 2
    aft_outline = [(inner, root_low), (outer, edge_low), (outer, edge_high), (inner, root_high)]
    root_low, root_high = (share * tall for share in fore["root"])
    edge_low, edge_high = (share * tall for share in fore["edge"])
    reach = fore["reach"] * wide
    fore_outline = [(bodies.lander_radius_at(size, root_low) * 0.8, root_low), (reach, edge_low), (reach, edge_high),
                    (bodies.lander_radius_at(size, root_high) * 0.8, root_high)]
    fins = []
    for outline, thick in ((aft_outline, aft["thick"] * deep), (fore_outline, fore["thick"] * deep)):
        for side in (-1.0, 1.0):
            points = [(middle[0] + side * out, up) for out, up in outline]
            fins.append(shapes.bevelled(shapes.prism(points, middle[1] - thick / 2, middle[1] + thick / 2,
                                                     "stainless", "fin"), EDGE * 4))
    return fins


def lander_legs(size, middle):
    """The four splayed legs at the diagonals: a main strut from the hull's side and a lower strut from its bottom
    edge to each round pad, the pad's hub standing on it."""
    wide, tall, _ = size
    radius = bodies.LANDER_RADIUS * wide
    reach, pad = bodies.LANDER_LEG_REACH * wide, bodies.LANDER_PAD
    main, lower = (share * wide for share in bodies.LANDER_STRUTS)
    foot, hub_top = bodies.LANDER_FOOT * tall, pad["hub_top"] * tall
    legs = []
    for angle in bodies.LANDER_LEG_ANGLES:
        under = round_point(middle, reach, angle, 0.0)
        hub = (under[0], hub_top, under[2])
        legs += [shapes.cylinder(under, (under[0], pad["thick"] * tall, under[2]), pad["radius"] * wide, "stainless",
                                 48, "pad"),
                 shapes.cylinder(under, hub, pad["hub"] * wide, "stainless", 24, "hub"),
                 shapes.cylinder(round_point(middle, radius * 0.9, angle, bodies.LANDER_LEG_TOP * tall), hub, main,
                                 "stainless", 24, "strut"),
                 shapes.cylinder(round_point(middle, radius * 0.85, angle, foot + lower), hub, lower, "stainless",
                                 24, "strut")]
    return legs


def lander_bells(size, middle):
    """The three engine bells hanging under the hull, hollow, their tops sunk into its bottom."""
    wide, tall, _ = size
    bells = bodies.LANDER_BELLS
    top, mouth = bodies.LANDER_FOOT * tall + 0.05, bells["mouth"] * tall
    exit_radius, throat, wall = bells["exit"] * wide, bells["throat"] * wide, bells["wall"] * wide
    waist = (throat + (exit_radius - throat) * 0.45, (top + mouth) / 2)
    outline = [(throat, top), waist, (exit_radius, mouth), (exit_radius - wall, mouth),
               (waist[0] - wall, waist[1]), (throat - wall, top)]
    found = []
    for angle in bells["angles"]:
        centre = round_point(middle, bells["out"] * wide, angle, 0.0)
        found.append(lathed(outline, (centre[0], centre[2]), "stainless", "bell", closed=True))
    return found


def lander_bay(size, middle):
    """The cargo bay inside the open door: grey lining on its back wall, sides and ceiling, a ribbed back wall and a
    tread floor."""
    wide, tall, _ = size
    radius, door = bodies.LANDER_RADIUS * wide, bodies.LANDER_DOOR
    half, sill, top = door["half"] * wide, door["sill"] * tall, door["top"] * tall
    back, lining = middle[1] - door["back"] * radius, door["lining"] * wide
    front = middle[1] - math.sqrt(radius ** 2 - half ** 2) + 0.02
    parts = [boxed((-half, sill, back - lining), (half, top, back + 0.01), "plastic_grey", "lining"),
             boxed((-half - 0.01, top - lining, front), (half + 0.01, top + 0.01, back), "plastic_grey", "lining"),
             boxed((-half - 0.01, sill - 0.01, front - 0.02), (half + 0.01, sill + lining, back), "anodized_natural",
                   "floor")]
    for wall_from, wall_to in ((-half - 0.01, -half + lining), (half - lining, half + 0.01)):
        parts.append(boxed((wall_from, sill, front), (wall_to, top, back), "plastic_grey", "lining"))
    for step in range(bodies.LANDER_DOOR_RIBS):
        at = -half + 2 * half * (step + 0.5) / bodies.LANDER_DOOR_RIBS
        parts.append(boxed((at - 0.03, sill + lining, back - lining - 0.04), (at + 0.03, top - lining, back - lining),
                           "anodized_natural", "rib"))
    return parts


def slope_strip(start, end, base, height):
    """A strip lying on the ramp's slope from `start` to `end` ((z, y) points on its deck), from `base` under the deck
    to `height` over it, as a (z, y) outline across x."""
    along = (end[0] - start[0], end[1] - start[1])
    length = math.hypot(*along)
    normal = (-along[1] / length, along[0] / length)
    if normal[1] < 0:
        normal = (-normal[0], -normal[1])
    return [(point[0] + normal[0] * offset, point[1] + normal[1] * offset)
            for point, offset in ((start, base), (end, base), (end, height), (start, height))]


def lander_ramp(size, middle):
    """The ramp from the bay's sill down to the ground at the front: a deck with tread ribs across it, a rail along
    each edge and the hinge at its top."""
    wide, tall, deep = size
    radius, door, ramp = bodies.LANDER_RADIUS * wide, bodies.LANDER_DOOR, bodies.LANDER_RAMP
    half, thick = ramp["half"] * wide, ramp["thick"] * tall
    deck_top = door["sill"] * tall + door["lining"] * wide
    upper = (middle[1] - math.sqrt(radius ** 2 - (door["half"] * wide) ** 2) + 0.05, deck_top)
    lower = (-deep / 2, thick)
    parts = [shapes.bevelled(along_x([upper, lower, (lower[0], 0.0), (upper[0], upper[1] - thick)], -half, half,
                                     "stainless", "ramp"), EDGE)]
    rib_wide, rib_high = (share * tall for share in ramp["rib"])
    run = (lower[0] - upper[0], lower[1] - upper[1])
    length = math.hypot(*run)
    for step in range(ramp["ribs"]):
        share = (step + 1) / (ramp["ribs"] + 1)
        centre = (upper[0] + run[0] * share, upper[1] + run[1] * share)
        offset = (run[0] / length * rib_wide / 2, run[1] / length * rib_wide / 2)
        parts.append(along_x(slope_strip((centre[0] - offset[0], centre[1] - offset[1]),
                                         (centre[0] + offset[0], centre[1] + offset[1]), -0.01, rib_high),
                             -half + 0.08, half - 0.08, "stainless", "tread"))
    rail_wide, rail_high = ramp["rail"][0] * wide, ramp["rail"][1] * tall
    short = (lower[0] - run[0] / length * rail_high, lower[1] - run[1] / length * rail_high)  # inside the laid box
    for side in (-1.0, 1.0):
        parts.append(along_x(slope_strip(upper, short, -0.01, rail_high), side * (half - rail_wide), side * half,
                             "stainless", "rail"))
    parts.append(shapes.cylinder((-half, upper[1] - thick / 2, upper[0]), (half, upper[1] - thick / 2, upper[0]),
                                 thick * 0.7, "stainless", 24, "hinge"))
    return parts


def lander_pipes(size, middle):
    """The two pipes running up its side, held off the hull by brackets, each end turned into the hull."""
    wide, tall, _ = size
    radius, pipes = bodies.LANDER_RADIUS * wide, bodies.LANDER_PIPES
    low, high = (share * tall for share in pipes["ends"])
    pipe, standoff, gap = pipes["radius"] * wide, pipes["standoff"] * wide, pipes["gap"] * wide
    centre = 270.0 + pipes["angle"]  # the front is -z, 270 degrees round from +x toward +z; +x lies at 360
    parts = []
    for side in (-0.5, 0.5):
        angle = centre + math.degrees(side * gap / radius)
        bottom, top = (round_point(middle, radius + standoff, angle, level) for level in (low, high))
        parts.append(shapes.cylinder(bottom, top, pipe, "stainless", 24, "pipe"))
        for level in (low, high):
            parts.append(shapes.cylinder(round_point(middle, radius - 0.03, angle, level),
                                         round_point(middle, radius + standoff, angle, level), pipe, "stainless",
                                         24, "pipe"))
        for step in range(pipes["brackets"]):
            level = low + (high - low) * (step + 1) / (pipes["brackets"] + 1)
            parts.append(shapes.cylinder(round_point(middle, radius - 0.02, angle, level),
                                         round_point(middle, radius + standoff, angle, level), pipe * 0.6,
                                         "stainless", 12, "bracket"))
    return parts


def lander_body(size, laid):
    """The campgrounds' landed lander's body (2026-10-18, PRD #10: its take is one lumpy stainless surface, three legs
    where the concept has four, its hull turned off square): a round stainless hull with an ogive nose and weld seams,
    two forward flaps and two aft fins across it, four legs splayed to round pads at the diagonals, three engine
    bells under it, the open cargo bay at its foot with the ramp down to the ground in front, two pipes up its side,
    and a flat panel cut into its front where the decal stencil is laid."""
    wide, tall, deep = size
    middle = (0.0, bodies.LANDER_AXIS * deep)
    return ([lander_hull(size, middle)] + lander_seams(size, middle) + lander_fins(size, middle)
            + lander_legs(size, middle) + lander_bells(size, middle) + lander_bay(size, middle)
            + lander_ramp(size, middle) + lander_pipes(size, middle))


def tube(start, end, radius, material, name, segments=16):
    """A round tube between two kit-frame points, reaching its radius past each so tubes meeting at a corner join."""
    start, end = Vector(start), Vector(end)
    reach = (end - start).normalized() * radius
    return shapes.cylinder(tuple(start - reach), tuple(end + reach), radius, material, segments, name)


def turned_upright(item, degrees, middle=(0.0, 0.0)):
    """Turn a part about the kit's upright axis through (x, z) = `middle`, by `degrees` from +x toward -z."""
    centre = shapes.to_blender((middle[0], 0.0, middle[1]))
    item.data.transform(Matrix.Translation(centre) @ Matrix.Rotation(math.radians(degrees), 4, "Z")
                        @ Matrix.Translation(-centre))
    return item


# --- the garage's open rover -----------------------------------------------------------------------------------------

def rover_tyre(size, side, axle):
    """One tyre: a smooth carcass with rounded shoulders and two staggered rows of tread lugs round it."""
    wide, tall, _ = size
    height, radius = bodies.ROVER_WHEEL[0] * tall, bodies.ROVER_WHEEL[1] * tall
    outer, width = bodies.ROVER_TYRE[0] * wide, bodies.ROVER_TYRE[1] * wide
    inner_face = outer - width
    carcass = radius * bodies.ROVER_TYRE_CARCASS
    tyre = shapes.ring((side * inner_face, height, axle), (side * outer, height, axle), carcass,
                       radius * bodies.ROVER_RIM[1], "rubber", ROUND, "tyre")
    parts = [shapes.bevelled(tyre, (outer - inner_face) * 0.12)]
    axis = (height, axle)
    step = 360.0 / bodies.ROVER_LUGS
    rows = ((inner_face + width * 0.06, inner_face + width * 0.48, 0.0),
            (inner_face + width * 0.52, outer - width * 0.06, step / 2))
    for x_from, x_to, offset in rows:
        for lug in range(bodies.ROVER_LUGS):
            first = lug * step + offset
            outline = arc(axis, carcass - 0.01, radius, first, first + step * 0.45, 2)
            parts.append(along_x(outline, min(side * x_from, side * x_to), max(side * x_from, side * x_to), "rubber",
                                 "lug"))
    return parts


def rover_rim(size, side, axle):
    """One rim: its barrel inside the tyre, a hub standing out of the wheel and wire spokes from hub to barrel."""
    wide, tall, _ = size
    height, radius = bodies.ROVER_WHEEL[0] * tall, bodies.ROVER_WHEEL[1] * tall
    outer, width = bodies.ROVER_TYRE[0] * wide, bodies.ROVER_TYRE[1] * wide
    inner_face = outer - width
    rim_out, rim_in = (share * radius for share in bodies.ROVER_RIM)
    hub_radius, hub_out = bodies.ROVER_HUB[0] * radius, bodies.ROVER_HUB[1] * width
    parts = [shapes.ring((side * (inner_face + 0.01), height, axle), (side * (outer - 0.01), height, axle), rim_out,
                         rim_in, "bare_steel", ROUND, "rim"),
             shapes.cylinder((side * (inner_face - 0.03), height, axle), (side * (outer - hub_out), height, axle),
                             hub_radius, "bare_steel", 24, "hub")]
    spoke_plane = outer - width * 0.3
    for spoke in range(bodies.ROVER_SPOKES):
        angle = 2 * math.pi * spoke / bodies.ROVER_SPOKES
        rim_x = inner_face + width * (0.25 if spoke % 2 else 0.75)
        end = (side * rim_x, height + (rim_in + 0.01) * math.sin(angle), axle + (rim_in + 0.01) * math.cos(angle))
        start = (side * spoke_plane, height + hub_radius * 0.7 * math.sin(angle),
                 axle + hub_radius * 0.7 * math.cos(angle))
        parts.append(shapes.cylinder(start, end, 0.0045, "bare_steel", 8, "spoke"))
    return parts


def rover_mudguard(size, side, axle):
    """One white mudguard arched over its tyre, on a stay down to the frame's upper rail beside it."""
    wide, tall, deep = size
    height = bodies.ROVER_WHEEL[0] * tall
    inner, thick, first, last, x_from, x_to = bodies.ROVER_MUDGUARD
    inner, thick = inner * tall, thick * tall
    low, high = sorted((side * x_from * wide, side * x_to * wide))
    guard = shapes.bevelled(along_x(arc((height, axle), inner, inner + thick, first, last, 24), low, high,
                                    "enamel_white", "mudguard"), EDGE)
    rail, top = rover_rail_height(size, axle / deep), height + inner
    near, far = sorted((side * bodies.ROVER_FRAME[0] * wide, side * (x_from * wide + 0.03)))
    stay = boxed((near, min(rail, top), axle - 0.02), (far, max(rail, top) + thick / 2, axle + 0.02), "bare_steel",
                 "stay")
    return [guard, stay]


def rover_rail_height(size, at):
    """The upper side rail's height at `at` along z (a share of the depth), from ROVER_UPPER_RAIL."""
    points = bodies.ROVER_UPPER_RAIL
    for (z0, y0), (z1, y1) in zip(points, points[1:]):
        if min(z0, z1) <= at <= max(z0, z1):
            return (y0 + (y1 - y0) * (at - z0) / (z1 - z0)) * size[1]
    return points[0][1] * size[1]


def rover_wheels(size):
    """The four wheels on their stub axles out of the frame, each under its mudguard."""
    wide, tall, deep = size
    frame = bodies.ROVER_FRAME[0] * wide
    height = bodies.ROVER_WHEEL[0] * tall
    parts = []
    for axle_share in bodies.ROVER_AXLES:
        axle = axle_share * deep
        for side in (-1.0, 1.0):
            parts += rover_tyre(size, side, axle) + rover_rim(size, side, axle) + rover_mudguard(size, side, axle)
            parts.append(shapes.cylinder((side * (frame - 0.03), height, axle),
                                         (side * (bodies.ROVER_TYRE[0] - bodies.ROVER_TYRE[1]) * wide, height, axle),
                                         0.03, "bare_steel", 16, "axle"))
    return parts


def rover_frame(size):
    """The tubular steel frame: both side rails, the posts between them, the cross tubes, the floor pan and the
    cargo tray's floor with a cast fitting at each of its corners."""
    wide, tall, deep = size
    half, radius = bodies.ROVER_FRAME[0] * wide, bodies.ROVER_FRAME[1] * wide
    parts = []
    for side in (-1.0, 1.0):
        for rail in (bodies.ROVER_LOWER_RAIL, bodies.ROVER_UPPER_RAIL):
            for (z0, y0), (z1, y1) in zip(rail, rail[1:]):
                parts.append(tube((side * half, y0 * tall, z0 * deep), (side * half, y1 * tall, z1 * deep), radius,
                                  "bare_steel", "rail"))
        for z, y0, y1 in bodies.ROVER_POSTS:
            parts.append(tube((side * half, y0 * tall, z * deep), (side * half, y1 * tall, z * deep), radius,
                              "bare_steel", "post"))
    for z, y in bodies.ROVER_CROSS:
        parts.append(tube((-half, y * tall, z * deep), (half, y * tall, z * deep), radius, "bare_steel", "cross"))
    height, thick, z_from, z_to = bodies.ROVER_FLOOR
    parts.append(boxed((-half, height * tall, z_from * deep), (half, (height + thick) * tall, z_to * deep),
                       "galvanized_steel", "floor"))
    tray_from, tray_to, tray_height, tray_thick = bodies.ROVER_TRAY
    parts.append(boxed((-half, tray_height * tall, tray_from * deep),
                       (half, (tray_height + tray_thick) * tall, tray_to * deep), "galvanized_steel", "tray"))
    fitting = bodies.ROVER_FITTING * wide
    for side in (-1.0, 1.0):
        for z in (tray_from, tray_to):
            for y in (bodies.ROVER_LOWER_RAIL[-1][1], bodies.ROVER_UPPER_RAIL[-1][1]):
                middle = (side * half, y * tall, z * deep)
                parts.append(boxed(tuple(value - fitting for value in middle), tuple(value + fitting for value in middle),
                                   "cast_steel", "fitting"))
    return parts


def rover_boxes(size):
    """The white battery box on its carrier plate at the front, its dark grille on its face; the white console box
    ahead of the seats; the seats' risers on the floor; the antenna mast's pole up from the tray floor."""
    wide, tall, deep = size
    half = bodies.ROVER_FRAME[0] * wide
    x0, x1, y0, y1, z0, z1 = bodies.ROVER_BATTERY
    height, carrier_from, carrier_to = bodies.ROVER_CARRIER
    parts = [boxed((-half, height * tall, carrier_from * deep), (half, y0 * tall, carrier_to * deep),
                   "galvanized_steel", "carrier"),
             boxed((x0 * wide, y0 * tall, z0 * deep), (x1 * wide, y1 * tall, z1 * deep), "enamel_white", "battery", 0.008)]
    inset, rise = bodies.ROVER_GRILLE
    across, up = (x1 - x0) * wide, (y1 - y0) * tall
    parts.append(boxed((x0 * wide + across * inset, y0 * tall + up * rise, z1 * deep - 0.002),
                       (x1 * wide - across * inset, y1 * tall - up * rise, z1 * deep + 0.008), "dark_panel", "grille"))
    side_from, side_to = bodies.ROVER_CONSOLE_SIDES
    profile = [(z * deep, y * tall) for z, y in bodies.ROVER_CONSOLE_PROFILE]
    parts.append(shapes.bevelled(along_x(profile, side_from * wide, side_to * wide, "enamel_white", "console"), 0.008))
    (riser_from, riser_to), (riser_back, riser_front), riser_top = bodies.ROVER_RISERS
    floor_top = (bodies.ROVER_FLOOR[0] + bodies.ROVER_FLOOR[1]) * tall
    for side in (-1.0, 1.0):
        low, high = sorted((side * riser_from * wide, side * riser_to * wide))
        parts.append(boxed((low, floor_top, riser_back * deep), (high, riser_top * tall, riser_front * deep),
                           "bare_steel", "riser"))
    x, z, mast_from, mast_to, radius = bodies.ROVER_MAST
    parts.append(shapes.cylinder((x * wide, mast_from * tall, z * deep), (x * wide, mast_to * tall, z * deep),
                                 radius * wide, "bare_steel", 16, "mast"))
    return parts


def rover_body(size, laid):
    """The garage's open two-seat rover's body (2026-10-18, PRD #10: its take's frame tubes wander and its wheels are
    lumps): a tubular steel frame with a floor pan and a cargo tray behind the seats, four knobbly tyres on spoked
    rims under white mudguards, the white battery box at the front and the white console box ahead of the seats,
    and the antenna mast's pole. The take's seats, screens, switches, cables, the mast's dish and the lamps stay
    the model's (ROVER_DETAILS)."""
    return rover_frame(size) + rover_wheels(size) + rover_boxes(size)


# --- the campgrounds' cargo crane ------------------------------------------------------------------------------------

def crane_point(tall, share):
    """A point of the arm's plane (along, up), shares of the height, in metres."""
    return Vector((share[0] * tall, share[1] * tall))


def crane_beam(start, end, depth, across, width, material, name):
    """A straight beam of square section in the arm's plane, from one (along, up) point to another, `depth` deep in
    the plane and `width` wide across it about `across`."""
    normal = Vector((-(end - start).y, (end - start).x)).normalized() * depth / 2
    outline = [tuple(start - normal), tuple(end - normal), tuple(end + normal), tuple(start + normal)]
    return shapes.bevelled(shapes.prism(outline, across - width / 2, across + width / 2, material, name), EDGE)


def crane_legs(tall):
    """The four outrigger legs out of the hub: a beam each, a jack standing at its end, a foot pad under it with its
    rubber sole."""
    middle = (bodies.CRANE_MIDDLE[0] * tall, bodies.CRANE_MIDDLE[1] * tall)
    beam_foot, beam_top, beam_half, beam_start = (share * tall for share in bodies.CRANE_LEG_BEAM)
    jack_out, jack_half, jack_foot, jack_top = (share * tall for share in bodies.CRANE_JACK)
    pad_half, sole_top, pad_top = (share * tall for share in bodies.CRANE_PAD)
    first, count = bodies.CRANE_LEGS
    parts = []
    for leg in range(count):
        along, across = middle
        leg_parts = [boxed((along + beam_start, beam_foot, across - beam_half),
                           (along + jack_out, beam_top, across + beam_half), "cream_paint", "leg"),
                     boxed((along + jack_out - jack_half, jack_foot, across - jack_half),
                           (along + jack_out + jack_half, jack_top, across + jack_half), "cream_paint", "jack"),
                     boxed((along + jack_out - pad_half, sole_top, across - pad_half),
                           (along + jack_out + pad_half, pad_top, across + pad_half), "cream_paint", "pad"),
                     boxed((along + jack_out - pad_half, 0.0, across - pad_half),
                           (along + jack_out + pad_half, sole_top, across + pad_half), "rubber", "sole")]
        parts += [turned_upright(part, -(first + 360.0 * leg / count), middle) for part in leg_parts]
    return parts


def crane_base(tall):
    """The slewing base: the geared drum under the hub with its teeth, the six-sided hub, the slewing drum with its
    lip and the block on it the post is pinned to."""
    along, across = bodies.CRANE_MIDDLE[0] * tall, bodies.CRANE_MIDDLE[1] * tall
    gear_radius, gear_foot, gear_top = (share * tall for share in bodies.CRANE_GEAR[:3])
    hub_radius, hub_foot, hub_top = (share * tall for share in bodies.CRANE_HUB)
    drum_radius, drum_foot, drum_top, lip_radius, lip_depth = (share * tall for share in bodies.CRANE_DRUM)
    parts = [shapes.cylinder((along, gear_foot, across), (along, gear_top, across), gear_radius, "stainless", ROUND,
                             "gear"),
             shapes.bevelled(shapes.cylinder((along, hub_foot, across), (along, hub_top, across), hub_radius,
                                             "cream_paint", 6, "hub"), EDGE),
             shapes.cylinder((along, drum_foot, across), (along, drum_top, across), drum_radius, "cream_paint", ROUND,
                             "drum"),
             shapes.bevelled(shapes.cylinder((along, drum_top - lip_depth, across), (along, drum_top, across),
                                             lip_radius, "cream_paint", ROUND, "lip"), EDGE)]
    teeth = bodies.CRANE_GEAR[3]
    for tooth in range(teeth):
        part = boxed((along + gear_radius - 0.004, gear_foot + 0.01, across - 0.012),
                     (along + gear_radius + 0.014, gear_top - 0.01, across + 0.012), "stainless", "tooth")
        parts.append(turned_upright(part, 360.0 * tooth / teeth, (along, across)))
    column_from, column_to, column_half, column_foot, column_top = (share * tall for share in bodies.CRANE_COLUMN)
    middle = bodies.CRANE_ARM_ACROSS * tall
    parts.append(boxed((column_from, column_foot, middle - column_half), (column_to, column_top, middle + column_half),
                       "cream_paint", "column"))
    return parts


def crane_arm(tall):
    """The post from the column to the elbow, the knuckle there, the boom in its two parts with the collar round
    their joint, the winch drum on the post's side, the lifting ram and the extension ram along the boom's top."""
    middle = bodies.CRANE_ARM_ACROSS * tall
    root, elbow, post_depth, post_width = bodies.CRANE_POST
    root, elbow = crane_point(tall, root), crane_point(tall, elbow)
    tip = crane_point(tall, bodies.CRANE_BOOM_TIP)
    base_depth, base_width, fly_depth, fly_width, joint = bodies.CRANE_BOOM
    joint_point = elbow + (tip - elbow) * joint
    knuckle_radius, knuckle_width = (share * tall for share in bodies.CRANE_KNUCKLE)
    parts = [crane_beam(root, elbow, post_depth * tall, middle, post_width * tall, "cream_paint", "post"),
             shapes.cylinder((elbow.x, elbow.y, middle - knuckle_width / 2), (elbow.x, elbow.y, middle + knuckle_width / 2),
                             knuckle_radius, "cream_paint", 32, "knuckle"),
             shapes.cylinder((root.x, root.y, middle - post_width * tall / 2 - 0.012),
                             (root.x, root.y, middle + post_width * tall / 2 + 0.012), 0.025, "stainless", 24, "pin"),
             crane_beam(elbow, joint_point, base_depth * tall, middle, base_width * tall, "cream_paint", "boom"),
             crane_beam(joint_point - (tip - elbow).normalized() * 0.05, tip, fly_depth * tall, middle, fly_width * tall,
                        "cream_paint", "fly")]
    collar_length, collar_out = (share * tall for share in bodies.CRANE_COLLAR)
    direction = (tip - elbow).normalized()
    parts.append(crane_beam(joint_point - direction * collar_length, joint_point, base_depth * tall + collar_out * 2,
                            middle, base_width * tall + collar_out * 2, "cream_paint", "collar"))
    winch_along, winch_up, winch_radius, winch_from, winch_to = (share * tall for share in bodies.CRANE_WINCH)
    parts.append(shapes.bevelled(shapes.cylinder((winch_along, winch_up, middle + winch_from),
                                                 (winch_along, winch_up, middle + winch_to), winch_radius,
                                                 "cream_paint", 32, "winch"), EDGE))
    return parts + crane_rams(tall, elbow, tip)


def crane_rams(tall, elbow, tip):
    """The lifting ram from the column's side up to a lug under the boom (a painted barrel, a stainless rod), and
    the stainless extension ram along the boom's top on its two saddles."""
    middle = bodies.CRANE_ARM_ACROSS * tall
    foot, head, across, barrel, rod, share = bodies.CRANE_RAM
    foot, head = crane_point(tall, foot), crane_point(tall, head)
    across = across * tall
    split = foot + (head - foot) * share
    parts = [shapes.cylinder((foot.x, foot.y, across), (split.x, split.y, across), barrel * tall, "cream_paint", 24,
                             "barrel"),
             shapes.cylinder((split.x, split.y, across), (head.x, head.y, across), rod * tall, "stainless", 24, "rod")]
    for end in (foot, head):
        parts.append(shapes.cylinder((end.x, end.y, across - barrel * tall), (end.x, end.y, middle), 0.018,
                                     "stainless", 16, "eye"))
    start, stop, radius, stand = bodies.CRANE_TOP_RAM
    direction = (tip - elbow).normalized()
    up = Vector((-direction.y, direction.x))
    base_depth = bodies.CRANE_BOOM[0] * tall
    fly_depth = bodies.CRANE_BOOM[2] * tall
    over = up * (base_depth / 2 + stand * tall)
    ram_from = elbow + (tip - elbow) * start + over
    ram_to = elbow + (tip - elbow) * stop + up * (fly_depth / 2 + stand * tall)
    parts.append(shapes.cylinder((ram_from.x, ram_from.y, middle), (ram_to.x, ram_to.y, middle), radius * tall,
                                 "stainless", 24, "top_ram"))
    for at, depth in ((start + 0.02, base_depth), (stop - 0.02, fly_depth)):
        seat = elbow + (tip - elbow) * at
        parts.append(crane_beam(seat + up * depth / 2 - direction * 0.02, seat + up * depth / 2 + direction * 0.02,
                                stand * tall * 2 + radius * tall * 2, middle, 0.03, "stainless", "saddle"))
    return parts


def crane_hook(tall):
    """The hook gear at the boom's tip: the sheave between two cheek plates, the cable down from it, the block and
    the hook under it."""
    middle = bodies.CRANE_ARM_ACROSS * tall
    tip = crane_point(tall, bodies.CRANE_BOOM_TIP)
    sheave_radius, sheave_width = (share * tall for share in bodies.CRANE_SHEAVE)
    drop, block_radius, block_width, hook_radius = (share * tall for share in bodies.CRANE_HOOK)
    fly_width = bodies.CRANE_BOOM[3] * tall
    parts = [shapes.cylinder((tip.x, tip.y, middle - sheave_width / 2), (tip.x, tip.y, middle + sheave_width / 2),
                             sheave_radius, "stainless", 32, "sheave")]
    for side in (-1.0, 1.0):
        parts.append(shapes.bevelled(shapes.cylinder((tip.x, tip.y, middle + side * fly_width / 2),
                                                     (tip.x, tip.y, middle + side * (fly_width / 2 + 0.008)),
                                                     sheave_radius * 1.2, "cream_paint", 32, "cheek"), 0.002))
    cable_x = tip.x + sheave_radius
    block_y = tip.y - drop
    parts += [shapes.cylinder((cable_x, tip.y, middle), (cable_x, block_y + block_radius, middle), 0.006, "stainless",
                              8, "cable"),
              shapes.cylinder((cable_x, block_y, middle - block_width / 2), (cable_x, block_y, middle + block_width / 2),
                              block_radius, "stainless", 24, "block"),
              shapes.cylinder((cable_x, block_y, middle), (cable_x, block_y - block_radius - 0.04, middle), 0.009,
                              "stainless", 12, "shank")]
    hook_y = block_y - block_radius - 0.04 - hook_radius
    hook = shapes.ring((cable_x, hook_y, middle - 0.008), (cable_x, hook_y, middle + 0.008), hook_radius,
                       hook_radius - 0.012, "stainless", 24, "hook")
    shapes.cut(hook, shapes.box((cable_x - hook_radius * 1.5, hook_y, middle - 0.05), (cable_x, hook_y + hook_radius * 1.5,
                                                                                         middle + 0.05),
                                "stainless", "cutter"))
    return parts + [hook]


def crane_body(size, laid):
    """The campgrounds' small cargo crane's body (2026-10-18, PRD #10: its take's arm is lumpy and its hook is
    missing): the slewing base (a geared drum, the hub, the slewing drum) on four outrigger legs with jacks and foot
    pads, the post up to the knuckle, the two-part boom with its collar, the lifting ram and the extension ram, the
    winch drum, and the sheave, cable, block and hook at the tip. Built in its arm's plane and turned into the laid
    frame by CRANE_HEADING; it keeps nothing of its take."""
    tall = size[1]
    parts = crane_legs(tall) + crane_base(tall) + crane_arm(tall) + crane_hook(tall)
    return [turned_upright(part, bodies.CRANE_HEADING) for part in parts]


BUILDERS = {"console_body": console_body, "station_module": station_module, "power_core": power_core,
            "fuel_tank": fuel_tank, "water_tank": water_tank, "lander_body": lander_body, "rover_body": rover_body,
            "crane_body": crane_body}
