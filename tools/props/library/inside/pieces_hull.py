"""Runs inside Blender: the hangar ship built in code from the owner's locked plan v7 (2026-10-18, PRD #10: the
image-to-3D take of the found picture never read the plan's numbers, its nose came back too pointy, its fins short,
three leg pairs where the plan has two, and its paint split along the picture's colour edge). The kit layout
(tools/props/scene/bay_kit.py) hands the hull's numbers in as `laid["hull"]` (ship_outline.hull_shows), so the build
reads no file.

The hull's frame is a kit piece's (pieces.py, shapes.py): x across (starboard positive), y up from the ground the
feet stand on, z along, the nose toward -z (z = the plan's y less half the length). Its parts:
    hull      the body lofted through the plan's stations, a faceted wedge (ship_outline.SECTION), dark_panel: the
              dark lower hull, and the seams between the panels laid over it
    panel     plates on the seams over the upper body, hull_white_gloss ahead of the stern block, dark_panel on the
              lower body, the belly and the stern block: each its own plate, a seam's width in from its neighbours
    window    the cockpit's glazing over the nose (a dark frame round clear_glass lights) and the cabins' small lights
    fin       the swept fins, both pairs, as the outline from above draws them
    spike     the nose spike on the middle line
    leg, foot the landing legs, a pair at each of the plan's two leg stations, each a sleeve, a piston, a brace and a
              round foot on the ground
    ring      the side ring's collar on the starboard side, its hazard band, and the hatch in it: the docking hatch
              and the people airlock in one, a round door a person walks through
The hull is kind `ship` (row ship); the main engines and the lift and nose thrusters are their own kinds
(main_engine, lift_thruster, nose_thruster), laid on the hull by the kit layout.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import shapes
import ship_outline

# The seams between plates and how far a plate stands off the hull, its thickness (metres).
SEAM, LIFT, PLATE = 0.05, 0.015, 0.03
# How long a bay of plates is along the hull, about.
BAY = 2.6
# Facets of a section (pairs of ship_outline.section's corners), the upper ones painted white.
UPPER = ((2, 3), (3, 4), (4, 5), (5, 6), (6, 7))
LOWER = ((0, 1), (1, 2), (7, 8), (8, 9), (9, 0))
WINDOW_FACETS = ((3, 4), (4, 5), (5, 6))
# A fin's thickness at its root (metres).
FIN_THICK = 0.3
SEGMENTS = 32


def kit_point(station, corner, length):
    """A section corner (x, z up) of a station as a kit-frame point."""
    return (corner[0], corner[1], station["y"] - length / 2)


def finished(built, name, material):
    """A bmesh made into an object with one library material, its normals pointing out."""
    bmesh.ops.recalc_face_normals(built, faces=built.faces)
    data = bpy.data.meshes.new(name)
    built.to_mesh(data)
    built.free()
    return shapes.mesh_object(name, data, material)


def lofted(rings, material, name):
    """A closed solid through rings of kit-frame points (each ring the same count, round its own plane), capped at
    both ends."""
    built = bmesh.new()
    verts = [[built.verts.new(shapes.to_blender(point)) for point in ring] for ring in rings]
    count = len(rings[0])
    for here, there in zip(verts, verts[1:]):
        for at in range(count):
            following = (at + 1) % count
            built.faces.new([here[at], here[following], there[following], there[at]])
    built.faces.new(verts[0])
    built.faces.new(list(reversed(verts[-1])))
    return finished(built, name, material)


def cone(start, end, radius_start, radius_end, material, name, segments=SEGMENTS):
    """A round bar from one kit-frame point to another, its radius going from one end's to the other's."""
    start, end = shapes.to_blender(start), shapes.to_blender(end)
    built = bmesh.new()
    bmesh.ops.create_cone(built, cap_ends=True, cap_tris=False, segments=segments, radius1=radius_start,
                          radius2=radius_end, depth=(end - start).length)
    turn = (end - start).to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(built, matrix=Matrix.Translation((start + end) / 2) @ turn, verts=built.verts)
    return finished(built, name, material)


def body(hull):
    """The hull's body, lofted through every station."""
    rings = [[kit_point(station, corner, hull["length"]) for corner in ship_outline.section(station)]
             for station in hull["stations"]]
    return lofted(rings, "dark_panel", "hull")


def bays(stations):
    """The stations split into bays about BAY long: [(first index, last index)]."""
    length = stations[-1]["y"] - stations[0]["y"]
    count = max(1, round(length / BAY))
    edges = [min(range(len(stations)), key=lambda index: abs(stations[index]["y"] - stations[0]["y"]
                                                               - length * share / count))
             for share in range(count + 1)]
    return [(first, last) for first, last in zip(edges, edges[1:]) if last > first]


def facet_frame(start, end, along):
    """A facet's unit way across (start to end) and its unit outward normal, given its unit way along (toward the
    stern): a section runs up the starboard side, over the deck and down to port, so across x along points out."""
    across = (Vector(end) - Vector(start)).normalized()
    return across, across.cross(along).normalized()


def plate(rows, material, name):
    """One plate over a facet: rows of (start, end) kit points along it, inset a seam's width at every edge, lifted
    LIFT off the hull and PLATE thick."""
    along = (Vector(rows[-1][0]) - Vector(rows[0][0])).normalized()
    rings = []
    for index, (start, end) in enumerate(rows):
        across, normal = facet_frame(start, end, along)
        start, end = Vector(start) + across * SEAM / 2, Vector(end) - across * SEAM / 2
        if index == 0:
            start, end = start + along * SEAM / 2, end + along * SEAM / 2
        if index == len(rows) - 1:
            start, end = start - along * SEAM / 2, end - along * SEAM / 2
        low, high = normal * LIFT, normal * (LIFT + PLATE)
        rings.append([tuple(start + low), tuple(end + low), tuple(end + high), tuple(start + high)])
    return lofted(rings, material, name)


def facet_rows(hull, first, last, facet, share=(0.0, 1.0)):
    """A facet's (start, end) kit points at each station from first to last, `share` of the way across it."""
    rows = []
    for station in hull["stations"][first:last + 1]:
        corners = ship_outline.section(station)
        start, end = (Vector(kit_point(station, corners[index], hull["length"])) for index in facet)
        rows.append((tuple(start.lerp(end, share[0])), tuple(start.lerp(end, share[1]))))
    return rows


def in_windows(hull, first, last):
    """Whether a bay lies over the cockpit's glazing."""
    low, high = hull["windows"]
    return hull["stations"][last]["y"] > low and hull["stations"][first]["y"] < high


def plates(hull):
    """Every plate over the body: white over the upper body ahead of the stern block, dark under it and behind it;
    the deck split along its middle line; the glazing's bays left to `glazing`."""
    found = []
    for first, last in bays(hull["stations"]):
        aft = hull["stations"][first]["y"] >= hull["stern_block"]
        for facet in UPPER + LOWER:
            if facet in WINDOW_FACETS and in_windows(hull, first, last):
                continue
            white = facet in UPPER and not aft
            shares = ((0.0, 0.5), (0.5, 1.0)) if facet == (4, 5) else ((0.0, 1.0),)
            for share in shares:
                found.append(plate(facet_rows(hull, first, last, facet, share),
                                   "hull_white_gloss" if white else "dark_panel", "panel"))
    return found


# The cockpit's glazing: lights across each facet (the deck's two halves count two) and along the bay.
LIGHTS_ACROSS, LIGHTS_ALONG, LIGHT_RIM = 1, 3, 0.14


def glazing(hull):
    """The cockpit's glazing over the nose: a dark frame plate on each glazed facet, and clear lights set in it."""
    found = []
    stations = hull["stations"]
    low, high = hull["windows"]
    inside = [index for index, station in enumerate(stations) if low <= station["y"] <= high]
    first, last = inside[0], inside[-1]
    for facet in WINDOW_FACETS:
        shares = ((0.0, 0.5), (0.5, 1.0)) if facet == (4, 5) else ((0.0, 1.0),)
        for share in shares:
            rows = facet_rows(hull, first, last, facet, share)
            found.append(plate(rows, "dark_panel", "window"))
            step = (last - first) / LIGHTS_ALONG
            for light in range(LIGHTS_ALONG):
                low, high = first + round(step * light), first + round(step * (light + 1))
                found.append(light_pane(facet_rows(hull, low, high, facet, share)))
    return found


def light_pane(rows):
    """One clear light standing on its frame plate, a rim in from the plate's edges."""
    along = (Vector(rows[-1][0]) - Vector(rows[0][0])).normalized()
    rings = []
    for index, (start, end) in enumerate(rows):
        across, normal = facet_frame(start, end, along)
        start, end = Vector(start) + across * LIGHT_RIM, Vector(end) - across * LIGHT_RIM
        if index == 0:
            start, end = start + along * LIGHT_RIM, end + along * LIGHT_RIM
        if index == len(rows) - 1:
            start, end = start - along * LIGHT_RIM, end - along * LIGHT_RIM
        low, high = normal * (LIFT + PLATE), normal * (LIFT + PLATE + 0.02)
        rings.append([tuple(start + low), tuple(end + low), tuple(end + high), tuple(start + high)])
    return lofted(rings, "clear_glass", "window")


def fin_parts(hull):
    """Both fins of each pair: the outline from above, FIN_THICK thick at the waist's height, mirrored to port."""
    found = []
    for outline in hull["fins"]:
        middle_y = sum(y for _, y in outline) / len(outline)
        here = min(hull["stations"], key=lambda station: abs(station["y"] - middle_y))
        height = here["keel"] + (here["top"] - here["keel"]) * ship_outline.WAIST
        for side in (1, -1):
            found.append(fin(outline, side, height, hull["length"]))
    return found


def fin(outline, side, height, length):
    """One fin: its outline (x, plan y) on one side, a slab FIN_THICK thick about `height`."""
    built = bmesh.new()
    low = [built.verts.new(shapes.to_blender((side * x, height - FIN_THICK / 2, y - length / 2))) for x, y in outline]
    high = [built.verts.new(shapes.to_blender((side * x, height + FIN_THICK / 2, y - length / 2))) for x, y in outline]
    built.faces.new(low)
    built.faces.new(list(reversed(high)))
    count = len(outline)
    for at in range(count):
        following = (at + 1) % count
        built.faces.new([low[at], low[following], high[following], high[at]])
    return finished(built, "fin", "dark_panel")


def spike_parts(hull):
    """The nose spike on the middle line, from the body's front face to its tip, with a collar at its root."""
    spike, length = hull["spike"], hull["length"]
    root = (0.0, spike["z"], spike["to"] - length / 2 + 0.2)
    tip = (0.0, spike["z"], spike["from"] - length / 2)
    collar = (0.0, spike["z"], spike["to"] - length / 2 - 0.35)
    return [cone(root, tip, spike["root"], spike["tip"], "hammertone_grey", "spike", 16),
            cone(root, collar, spike["root"] * 1.6, spike["root"] * 1.3, "bare_steel", "spike", 16)]


# A landing leg's sleeve, piston and brace radii, its foot's radius and thickness, and how long its brace reaches
# forward along the keel (metres).
SLEEVE, PISTON, BRACE, FOOT, FOOT_THICK, BRACE_REACH = 0.2, 0.13, 0.08, 0.55, 0.15, 1.4


def leg_parts(hull):
    """Each landing leg: a housing on the keel, a sleeve down to a piston, a brace back up to the keel, and a round
    foot on the ground."""
    found = []
    for leg in hull["legs"]:
        along = leg["y"] - hull["length"] / 2
        across, keel = leg["x"], leg["keel"]
        found.append(shapes.box((across - 0.45, keel - 0.35, along - 0.7), (across + 0.45, keel + 0.25, along + 0.7),
                                "dark_panel", "leg"))
        found.append(shapes.cylinder((across, keel - 0.3, along), (across, keel * 0.45, along), SLEEVE,
                                     "hammertone_grey", 24, "leg"))
        found.append(shapes.cylinder((across, keel * 0.5, along), (across, FOOT_THICK + 0.12, along), PISTON,
                                     "bare_steel", 24, "leg"))
        found.append(shapes.cylinder((across, keel * 0.4, along), (across * 0.8, keel - 0.3, along - BRACE_REACH),
                                     BRACE, "bare_steel", 16, "leg"))
        found.append(cone((across, FOOT_THICK, along), (across, FOOT_THICK + 0.18, along), PISTON * 2.2,
                          PISTON * 1.1, "bare_steel", "foot", 24))
        found.append(shapes.cylinder((across, 0.0, along), (across, FOOT_THICK, along), FOOT, "rubber", SEGMENTS,
                                     "foot"))
    return found


# The side ring: how far its collar stands out of the hull and sinks into it, its hazard band's width, how deep its
# door sits in the collar (metres), and the door's locking dogs.
COLLAR_OUT, COLLAR_IN, BAND, DOOR_DEEP, DOGS = 0.45, 0.6, 0.1, 0.18, 6


def ring_parts(hull):
    """The side ring on the starboard side: a white collar standing out of the hull round the opening, a hazard band
    round its face, and the round hatch in it, the docking hatch and the people airlock in one, with its dogs,
    wheel, hinges and a small port."""
    ring = hull["ring"]
    along = ring["y"] - hull["length"] / 2
    face, back = ring["x"] + COLLAR_OUT, ring["x"] - COLLAR_IN
    middle = lambda out: (out, ring["z"], along)  # noqa: E731
    parts = [shapes.ring(middle(back), middle(face), ring["outer"], ring["opening"], "hull_white_gloss", 48, "ring"),
             shapes.ring(middle(face), middle(face + 0.02), ring["outer"] - 0.05, ring["outer"] - 0.05 - BAND,
                         "hazard_paint", 48, "ring")]
    door = face - DOOR_DEEP
    parts.append(shapes.cylinder(middle(door - 0.12), middle(door), ring["opening"] - 0.01, "bare_steel", 48, "hatch"))
    parts.append(shapes.ring(middle(door), middle(door + 0.03), ring["opening"] * 0.86, ring["opening"] * 0.8,
                             "hammertone_grey", 48, "hatch"))
    parts.append(shapes.cylinder(middle(door), middle(door + 0.1), ring["opening"] * 0.16, "hammertone_grey", 24,
                                 "hatch"))
    for index in range(DOGS):
        angle = 2 * math.pi * index / DOGS
        height = ring["z"] + math.sin(angle) * ring["opening"] * 0.72
        at = along + math.cos(angle) * ring["opening"] * 0.72
        parts.append(shapes.box((door, height - 0.06, at - 0.06), (door + 0.07, height + 0.06, at + 0.06),
                                "bare_steel", "hatch"))
    port = (door + 0.005, ring["z"] + ring["opening"] * 0.42, along)
    parts.append(shapes.cylinder(port, (door + 0.03, port[1], port[2]), ring["opening"] * 0.12, "clear_glass", 24,
                                 "hatch"))
    for at in (along - ring["opening"] * 0.45, along + ring["opening"] * 0.45):
        parts.append(shapes.box((face - 0.05, ring["z"] - ring["opening"] - 0.1, at - 0.1),
                                (face + 0.08, ring["z"] - ring["opening"] + 0.15, at + 0.1), "hammertone_grey",
                                "hatch"))
    return parts


def ship(size, laid):
    """The hangar ship's hull from the plan v7 numbers in `laid["hull"]`, scaled to its laid length (`size`'s depth)."""
    hull = scaled(laid["hull"], size[2] / laid["hull"]["length"])
    return ([body(hull)] + plates(hull) + glazing(hull) + fin_parts(hull) + spike_parts(hull) + leg_parts(hull)
            + ring_parts(hull))


def scaled(hull, factor):
    """The hull's numbers scaled by `factor` (1 when the kit lays it at the plan's length)."""
    if abs(factor - 1.0) < 1e-6:
        return hull

    def times(value):
        if isinstance(value, dict):
            return {key: times(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [times(item) for item in value]
        return value * factor if isinstance(value, float) else value
    return times(hull)


# A main engine's ribs: how many, how far they stand out of its cowling and how long each is along it (metres).
ENGINE_RIBS, RIB_OUT, RIB_LONG = 7, 0.06, 0.12


def main_engine(size, laid):
    """A main engine, the ribbed tube beside the stern block: a white cowling, dark ribs round it, a steel lip at its
    intake and a dark nozzle bell out of its back; its front (-z) toward the nose, standing on its foot."""
    wide, tall, deep = size
    radius = min(wide, tall) / 2 - RIB_OUT
    axis = lambda along: (0.0, tall / 2, along)  # noqa: E731
    front, back = -deep / 2, deep / 2
    parts = [shapes.cylinder(axis(front + 0.1), axis(back - 0.35), radius, "hull_white_gloss", SEGMENTS, "cowling"),
             shapes.ring(axis(front), axis(front + 0.12), radius + RIB_OUT * 0.5, radius * 0.7, "bare_steel", SEGMENTS,
                         "lip"),
             shapes.cylinder(axis(front + 0.12), axis(front + 0.2), radius * 0.72, "hammertone_grey", SEGMENTS, "lip"),
             cone(axis(back - 0.4), axis(back), radius * 0.92, radius * 1.02, "hammertone_grey", "nozzle"),
             cone(axis(back - 0.38), axis(back + 0.001), radius * 0.6, radius * 0.9, "dark_panel", "nozzle")]
    span = (back - 0.6) - (front + 0.4)
    for index in range(ENGINE_RIBS):
        along = front + 0.4 + span * index / (ENGINE_RIBS - 1)
        parts.append(shapes.cylinder(axis(along), axis(along + RIB_LONG), radius + RIB_OUT, "dark_panel", SEGMENTS,
                                     "rib"))
    return parts


def lift_thruster(size, laid):
    """A lift thruster set into the belly, its foot on the hull and its nozzle out along +y (laid pointing down):
    a square dark mounting plate, a steel nozzle ring, louvres across its throat and a dark throat behind them."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2
    parts = [shapes.box((-radius, 0.0, -radius), (radius, 0.06, radius), "dark_panel", "plate"),
             shapes.ring((0.0, 0.06, 0.0), (0.0, tall, 0.0), radius * 0.86, radius * 0.7, "bare_steel", SEGMENTS,
                         "nozzle"),
             shapes.cylinder((0.0, 0.06, 0.0), (0.0, tall * 0.35, 0.0), radius * 0.7, "hammertone_grey", SEGMENTS,
                             "throat")]
    for index in range(5):
        along = -radius * 0.55 + radius * 1.1 * index / 4
        half = math.sqrt(max((radius * 0.7) ** 2 - along ** 2, 0.0)) * 0.95
        parts.append(shapes.box((-half, tall * 0.35, along - 0.03), (half, tall * 0.75, along + 0.03), "dark_panel",
                                "louvre"))
    return parts


def nose_thruster(size, laid):
    """A small nose thruster on the snout, its foot on the hull and its nozzle out along +y: a square dark plate and
    a steel nozzle."""
    wide, tall, deep = size
    radius = min(wide, deep) / 2
    return [shapes.box((-radius, 0.0, -radius), (radius, 0.04, radius), "dark_panel", "plate"),
            cone((0.0, 0.04, 0.0), (0.0, tall, 0.0), radius * 0.45, radius * 0.75, "bare_steel", "nozzle", 24)]


BUILDERS = {name: value for name, value in globals().items() if callable(value) and name in (
    "ship", "main_engine", "lift_thruster", "nose_thruster")}
