"""Small hardware and boxes built as products (2099's prologue, 2026-11-28: TRELLIS.2 from a picture kept failing on
thin parts and small hardware, new-seed remakes mostly failing again; the owner on the locker: "its mainly just the
lock and the holes ... make them library parts"): a wall switch, socket, knob, lever, pull handle, picture nail,
junction box, meter box, air conditioner unit, intercom or kerb grate built in code the way its product is built,
from one vocabulary of parts (a bevelled plate, a turned piece, a bent bar, a screw head, a cable gland, louvres, a
slatted grille, a fan guard, a key), each part a named mesh so every one wears its own library surface when laid
(`surface --part`), never one flat paint and never a bare box.

    parts(kind, size, **options) -> {part: trimesh.Trimesh}   the product of `kind` (KINDS) at `size`
    written(parts, path)                                       the parts as one GLB, a mesh and a material a part
    made(kind, size, out, entry, words, material, picture, options) -> record   GLB, hulls, mass and record files
    taken_in(items, work) -> [address]                          committed to score_lib as draft model entries

`size` is the row's (wide, deep, tall) metres. Every product is built as the maker lays a made model (fit.size_matrix):
y up, its front toward +z (a wall mount's back on the wall, z the least), stood on y = 0 and centred on x and z, so it
lays where a TRELLIS.2 model of its row lay. A flat product (`grate`) lies with its top up. Each kind's proportions are
its close-up's, held to the row's box: the box its product fills, its parts sized within it.

Every part is a closed solid of its own; the GLB keeps each part's sharp edges (its vertices split where faces turn
over SHARP degrees, each side its own box-projected texture coordinates, so a reader that merges equal vertices keeps
them apart) and gives each part a stand-in colour (TINTS) for a preview only: the place lays its library surface.
"""
import json
import math
import pathlib

import numpy as np
import trimesh

SHARP = 35.0  # degrees: faces turning more than this keep their own vertices (a hard edge)
ROUND = 24  # segments round a turned part
TINTS = {"brass": "#a8823f", "steel": "#b8bcc0", "grey": "#9a9e9f", "cream": "#e8dcb8", "dark": "#222426",
         "rust": "#7a4a2e", "glass": "#3c4a50", "white": "#e6e6e0", "black": "#1a1a1a"}


# --- the parts vocabulary -------------------------------------------------------------------------------------------

def rounded_rect(wide, high, radius, corner=6):
    """The outline of a rectangle `wide` x `high` with corners rounded at `radius`, centred, anticlockwise."""
    radius = max(0.0, min(radius, wide / 2 - 1e-6, high / 2 - 1e-6))
    if radius <= 1e-6:
        return np.array([[-wide / 2, -high / 2], [wide / 2, -high / 2], [wide / 2, high / 2], [-wide / 2, high / 2]])
    found = []
    for (cx, cy), start in zip([(1, 1), (-1, 1), (-1, -1), (1, -1)], [0, 90, 180, 270]):
        middle = np.array([cx * (wide / 2 - radius), cy * (high / 2 - radius)])
        for step in range(corner + 1):
            angle = math.radians(start + 90 * step / corner)
            found.append(middle + radius * np.array([math.cos(angle), math.sin(angle)]))
    return np.array(found)


def plate(wide, high, deep, radius=0.0, bevel=0.0, back=0.0):
    """A plate `wide` x `high` facing +z from z = `back` to `back + deep`, corners rounded at `radius`, its front edge
    chamfered `bevel` in and back: the convex hull of its outlines."""
    bevel = min(bevel, deep * 0.9, wide / 3, high / 3)
    rings = [(rounded_rect(wide, high, radius), back), (rounded_rect(wide, high, radius), back + deep - bevel),
             (rounded_rect(wide - 2 * bevel, high - 2 * bevel, max(radius - bevel, 0.0)), back + deep)]
    points = np.vstack([np.column_stack([ring, np.full(len(ring), z)]) for ring, z in rings])
    return trimesh.convex.convex_hull(points)


def block(wide, high, deep, at=(0.0, 0.0, 0.0)):
    """A box `wide` (x) x `high` (y) x `deep` (z) centred at `at`."""
    return trimesh.creation.box((wide, high, deep), trimesh.transformations.translation_matrix(at))


def turned(profile, at=(0.0, 0.0, 0.0), axis="z", sections=ROUND):
    """A solid turned round an axis through `at` from `profile` [(radius, along)], each end on the axis (radius 0):
    a knob, a rose, a gland's nut (6 sections), a screw head."""
    mesh = trimesh.creation.revolve(np.asarray(profile, float), sections=sections)
    return moved(mesh, axis, at)


def moved(mesh, axis, at):
    """A part built along z laid along `axis` ('x', 'y', 'z', or a direction) with its z = 0 at `at`."""
    direction = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}.get(axis, axis) if isinstance(axis, str) else axis
    direction = np.asarray(direction, float) / np.linalg.norm(direction)
    turn = trimesh.geometry.align_vectors([0, 0, 1], direction)
    mesh = mesh.copy()
    mesh.apply_transform(turn)
    mesh.apply_translation(at)
    return mesh


def rod(radius, start, end, sections=16):
    """A round bar from `start` to `end`."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    length = float(np.linalg.norm(end - start))
    mesh = trimesh.creation.cylinder(radius, length, sections=sections)
    mesh.apply_translation([0, 0, length / 2])
    return moved(mesh, end - start, start)


def bent(path, radius, closed=False, sides=12):
    """A round bar swept along `path` (points), its frames carried along it so it never twists; an open one capped at
    both ends, a closed one a ring."""
    path = np.asarray(path, float)
    steps = np.diff(np.vstack([path, path[:1]]) if closed else path, axis=0)
    ahead = np.array([steps[index % len(steps)] for index in range(len(path))])
    if not closed:
        ahead[1:-1] = steps[:-1] + steps[1:]
        ahead[-1] = steps[-1]
    else:
        ahead = steps + np.roll(steps, 1, axis=0)
    ahead /= np.linalg.norm(ahead, axis=1, keepdims=True)
    side = np.cross(ahead[0], [0, 0, 1] if abs(ahead[0][2]) < 0.9 else [1, 0, 0])
    side /= np.linalg.norm(side)
    rings = []
    for forward in ahead:
        side = side - forward * np.dot(side, forward)
        side /= np.linalg.norm(side)
        up = np.cross(forward, side)
        rings.append([side * math.cos(angle) + up * math.sin(angle)
                      for angle in np.linspace(0, 2 * math.pi, sides, endpoint=False)])
    points = np.vstack([centre + radius * np.asarray(ring) for centre, ring in zip(path, rings)])
    faces = []
    count = len(path) if closed else len(path) - 1
    for ring in range(count):
        here, there = ring * sides, ((ring + 1) % len(path)) * sides
        for corner in range(sides):
            nxt = (corner + 1) % sides
            faces += [[here + corner, there + corner, there + nxt], [here + corner, there + nxt, here + nxt]]
    if not closed:
        points = np.vstack([points, path[0], path[-1]])
        first, last = len(points) - 2, len(points) - 1
        tail = (len(path) - 1) * sides
        for corner in range(sides):
            nxt = (corner + 1) % sides
            faces += [[first, nxt, corner], [last, tail + corner, tail + nxt]]
    mesh = trimesh.Trimesh(points, faces, process=True)
    mesh.fix_normals()
    return mesh


def curve(control, count=24):
    """`count` points along the cubic Bezier through four `control` points."""
    control = np.asarray(control, float)
    share = np.linspace(0, 1, count)[:, None]
    return ((1 - share) ** 3 * control[0] + 3 * (1 - share) ** 2 * share * control[1]
            + 3 * (1 - share) * share ** 2 * control[2] + share ** 3 * control[3])


def screw(radius, at, axis="z"):
    """A pan screw head `radius` across, its slot cut as a groove (a dome turned with a notch), seated at `at`."""
    rise = radius * 0.55
    profile = [(0, 0), (radius, 0), (radius, rise * 0.35), (radius * 0.75, rise * 0.85), (radius * 0.3, rise),
               (0, rise)]
    head = turned(profile, sections=16)
    slot = block(radius * 1.7, radius * 0.25, rise * 0.7, (0, 0, rise * 0.85))
    return moved(trimesh.util.concatenate([head, slot]), axis, at)


def gland(radius, length, at, axis):
    """A cable gland: a hex nut, its domed cap and the cable stub leaving it, along `axis` from `at`."""
    nut = turned([(0, 0), (radius, 0), (radius, length * 0.45), (0, length * 0.45)], sections=6)
    cap = turned([(0, length * 0.42), (radius * 0.85, length * 0.42), (radius * 0.8, length * 0.7),
                  (radius * 0.5, length * 0.85), (0, length * 0.85)])
    stub = turned([(0, length * 0.8), (radius * 0.42, length * 0.8), (radius * 0.42, length), (0, length)], sections=12)
    return moved(trimesh.util.concatenate([nut, cap, stub]), axis, at)


def louvres(wide, high, count, depth, lean=30.0, back=0.0):
    """`count` slats across a `wide` x `high` opening, each leaning `lean` degrees down to the front, from z `back`."""
    pitch = high / count
    found = []
    for number in range(count):
        slat = block(wide, max(pitch * 0.18, 0.002), depth * 0.9)
        slat.apply_transform(trimesh.transformations.rotation_matrix(math.radians(lean), [1, 0, 0]))
        slat.apply_translation([0, -high / 2 + pitch * (number + 0.5), back + depth / 2])
        found.append(slat)
    return trimesh.util.concatenate(found)


def bars(wide, high, count, depth, bar, across=False, back=0.0):
    """`count` straight bars `bar` thick filling a `wide` x `high` field, upright (or `across`), from z `back`."""
    found = []
    for number in range(count):
        share = (number + 0.5) / count
        if across:
            found.append(block(wide, bar, depth, (0, -high / 2 + high * share, back + depth / 2)))
        else:
            found.append(block(bar, high, depth, (-wide / 2 + wide * share, 0, back + depth / 2)))
    return trimesh.util.concatenate(found)


def frame(wide, high, deep, rim, back=0.0):
    """A rectangular rim `rim` wide round a `wide` x `high` opening's outside edge, `deep` from z `back`."""
    middle = back + deep / 2
    return trimesh.util.concatenate([block(wide, rim, deep, (0, (high - rim) / 2, middle)),
                                     block(wide, rim, deep, (0, -(high - rim) / 2, middle)),
                                     block(rim, high - 2 * rim, deep, ((wide - rim) / 2, 0, middle)),
                                     block(rim, high - 2 * rim, deep, (-(wide - rim) / 2, 0, middle))])


def fan_guard(radius, wire, rings, spokes, at):
    """A fan's wire guard of `radius` facing +z at `at`: `rings` concentric wire rings, `spokes` straight wires from the
    hub to the rim and a hub plate."""
    found = []
    for number in range(1, rings + 1):
        ring_radius = radius * number / rings
        loop = [(ring_radius * math.cos(angle), ring_radius * math.sin(angle), 0.0)
                for angle in np.linspace(0, 2 * math.pi, 48, endpoint=False)]
        found.append(bent(loop, wire, closed=True, sides=8))
    for number in range(spokes):
        angle = 2 * math.pi * number / spokes
        found.append(rod(wire, (0, 0, 0), (radius * math.cos(angle), radius * math.sin(angle), 0), sections=8))
    found.append(turned([(0, -wire), (radius * 0.16, -wire), (radius * 0.16, wire * 2), (0, wire * 2)]))
    guard = trimesh.util.concatenate(found)
    guard.apply_translation(at)
    return guard


def blades(radius, count, at):
    """A fan's `count` pitched blades and hub, `radius` across, facing +z at `at`."""
    found = [turned([(0, 0), (radius * 0.2, 0), (radius * 0.2, radius * 0.15), (0, radius * 0.2)])]
    for number in range(count):
        blade = block(radius * 0.72, radius * 0.42, radius * 0.03, (radius * 0.55, 0, radius * 0.08))
        blade.apply_transform(trimesh.transformations.rotation_matrix(math.radians(25), [1, 0, 0], [0, 0, 0.08 * radius]))
        blade.apply_transform(trimesh.transformations.rotation_matrix(2 * math.pi * number / count, [0, 0, 1]))
        found.append(blade)
    fan = trimesh.util.concatenate(found)
    fan.apply_translation(at)
    return fan


def key(wide, high, deep, at):
    """A push key: a small rounded plate with a soft chamfer, its back at `at`."""
    found = plate(wide, high, deep, radius=min(wide, high) * 0.25, bevel=deep * 0.5)
    found.apply_translation(at)
    return found


# --- the products --------------------------------------------------------------------------------------------------

def knob(size, screws=2):
    """A round door knob on a narrow upright plate (the flat's brass knob): the plate the knob's width x 0.64 and the
    row's height, two screws above and below, a rose, a waisted neck and a mushroom knob the row's width across."""
    wide, deep, tall = size
    plate_deep = min(0.006, deep * 0.1)
    found = {"plate": plate(wide * 0.64, tall, plate_deep, radius=wide * 0.06, bevel=plate_deep * 0.45)}
    across = wide / 2
    profile = [(0, plate_deep), (across * 0.62, plate_deep), (across * 0.6, plate_deep + 0.004),
               (across * 0.34, plate_deep + 0.009), (across * 0.3, deep * 0.5), (across * 0.55, deep * 0.62),
               (across * 0.95, deep * 0.76), (across, deep * 0.84), (across * 0.85, deep * 0.94),
               (across * 0.5, deep * 0.99), (0, deep)]
    found["knob"] = turned(profile)
    found["screw"] = trimesh.util.concatenate([screw(wide * 0.06, (0, height, plate_deep - 0.0005))
                                               for height in np.linspace(-tall * 0.4, tall * 0.4, screws)])
    return found


def lever(size):
    """A lever door handle on a round rose (the stairwell's brass levers): the rose the row's height across, a neck
    out from it, an elbow and a flat bar running across to a rounded end, a raised panel along its top."""
    wide, deep, tall = size
    rose_radius = tall / 2
    rose_x = -wide / 2 + rose_radius
    rose = turned([(0, 0), (rose_radius, 0), (rose_radius, 0.004), (rose_radius * 0.85, 0.009),
                   (rose_radius * 0.4, 0.011), (0, 0.011)], at=(rose_x, 0, 0))
    bar_z, bar_thick, bar_high = deep * 0.72, min(deep * 0.28, 0.018), min(tall * 0.38, 0.02)
    neck = rod(rose_radius * 0.33, (rose_x, 0, 0.008), (rose_x, 0, bar_z), sections=ROUND)
    elbow = trimesh.creation.icosphere(2, rose_radius * 0.4)
    elbow.apply_translation([rose_x, 0, bar_z])
    length = wide / 2 - rose_x
    arm = plate(length, bar_thick, bar_high, radius=bar_thick / 2, bevel=bar_high * 0.2)
    arm.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    arm.apply_translation([rose_x + length / 2, -bar_high / 2, bar_z])
    panel = plate(length * 0.7, bar_thick * 0.5, 0.0012, radius=bar_thick * 0.24)
    panel.apply_transform(trimesh.transformations.rotation_matrix(-math.pi / 2, [1, 0, 0]))
    panel.apply_translation([rose_x + length * 0.55, bar_high / 2 - 0.0002, bar_z])
    return {"rose": rose, "lever": trimesh.util.concatenate([neck, elbow, arm, panel])}


def pull(size):
    """A bow pull handle (the flat's wardrobe handles): a round bar bent in one arc from foot to foot, the row's height
    apart and its depth out, each foot on a small round rose."""
    wide, deep, tall = size
    radius = min(wide * 0.32, 0.006)
    foot = tall / 2 - radius * 1.6
    control = [(0, -foot, 0), (0, -foot, (deep - radius) * 1.3), (0, foot, (deep - radius) * 1.3), (0, foot, 0)]
    handle = bent(curve(control, 32), radius)
    roses = [turned([(0, 0), (wide / 2, 0), (wide / 2 * 0.9, 0.003), (0, 0.003)], at=(0, end, 0))
             for end in (-foot, foot)]
    return {"handle": handle, "foot": trimesh.util.concatenate(roses)}


def nail(size, droop=12.0):
    """A picture nail and its hanging wire loop (the flat's portrait): a nail driven slightly upward into the wall, its
    flat head out front, a teardrop wire loop hung on its shank and falling in front of the wall to the row's height."""
    wide, deep, tall = size
    wire, head_radius = 0.0009, 0.0045
    lean = math.radians(droop)
    top = tall - head_radius - deep * 0.85 * math.sin(lean)
    tip = np.array([0.0, top + deep * 0.85 * math.sin(lean), deep * 0.85 * math.cos(lean)])
    shank = rod(0.0014, (0, top, 0), tip, sections=12)
    head = turned([(0, 0), (head_radius, 0), (head_radius, 0.0012), (0, 0.0012)], axis=tip - np.array([0, top, 0]), at=tip)
    hang_z = deep * 0.35
    hang = np.array([0.0, top + hang_z * math.tan(lean) + 0.0014 + wire, hang_z])
    loop = []
    for angle in np.linspace(0, 2 * math.pi, 40, endpoint=False):
        across = (wide / 2 - wire) * math.sin(angle) * (1 - 0.45 * math.cos(angle))
        down = (hang[1] - wire) * (1 - math.cos(angle)) / 2
        loop.append(hang + np.array([across, -down, 0.0]))
    return {"nail": trimesh.util.concatenate([shank, head]), "wire": bent(loop, wire, closed=True, sides=8)}


def switch(size, rocker=(0.3, 0.42), surround=True, screws=0):
    """A wall light switch (the flat's brushed plate, the stairwell's cream plates): a square plate with a softened
    front edge, a rocker or toggle `rocker` of the plate's width and height proud of it, set in a raised surround or
    not, and `screws` fixing screws across its middle."""
    wide, deep, tall = size
    plate_deep = deep * 0.55
    found = {"plate": plate(wide, tall, plate_deep, radius=wide * 0.05, bevel=plate_deep * 0.35)}
    rocker_wide, rocker_high = wide * rocker[0], tall * rocker[1]
    pieces = []
    if surround:
        pieces.append(frame(rocker_wide * 1.35, rocker_high * 1.3, deep * 0.12, rocker_wide * 0.12, back=plate_deep))
    toggle = plate(rocker_wide, rocker_high, deep - plate_deep, radius=rocker_wide * 0.08,
                   bevel=(deep - plate_deep) * 0.3, back=plate_deep - 0.0005)
    toggle.apply_transform(trimesh.transformations.rotation_matrix(math.radians(4), [1, 0, 0], [0, 0, plate_deep]))
    pieces.append(toggle)
    found["rocker"] = trimesh.util.concatenate(pieces)
    if screws:
        found["screw"] = trimesh.util.concatenate([screw(wide * 0.035, (side, 0, plate_deep - 0.0004))
                                                   for side in np.linspace(-wide * 0.36, wide * 0.36, screws)])
    return found


def socket(size, pins=2):
    """An old two-pin wall socket (the flat's): a square plate, a raised square face on it and a round boss on that
    face, dished in to a floor holding `pins` pin holes."""
    wide, deep, tall = size
    plate_deep, face_deep = deep * 0.4, deep * 0.75
    floor = face_deep + (deep - face_deep) * 0.2
    outer, inner = wide * 0.31, wide * 0.27
    found = {"plate": plate(wide, tall, plate_deep, radius=wide * 0.04, bevel=plate_deep * 0.3)}
    face = plate(wide * 0.8, tall * 0.8, face_deep - plate_deep, radius=wide * 0.06, bevel=deep * 0.08,
                 back=plate_deep - 0.0005)
    dish = turned([(0, floor), (inner, floor), (inner * 1.02, deep - 0.0008), (outer, deep), (outer * 1.06, deep - 0.001),
                   (outer * 1.08, face_deep - 0.0005), (0, face_deep - 0.0005)])
    found["face"] = trimesh.util.concatenate([face, dish])
    found["hole"] = trimesh.util.concatenate([turned([(0, floor - 0.0005), (wide * 0.035, floor - 0.0005),
                                                      (wide * 0.035, floor + 0.0004), (0, floor + 0.0004)],
                                                     at=(side, 0, 0), sections=12)
                                              for side in np.linspace(-wide * 0.12, wide * 0.12, pins)])
    return found


def junction(size, below=3, above=2):
    """A wall junction box (the stairwell's rusted top box): a box with a lid screwed down at its four corners, `below`
    cable glands out of its foot and `above` out of its top, all within the row's box."""
    wide, deep, tall = size
    gland_long = tall * 0.09
    box_high = tall - gland_long * ((below > 0) + (above > 0))
    middle = gland_long * ((below > 0) - (above > 0)) / 2
    body_deep, lid_deep = deep * 0.72, deep * 0.28
    body = plate(wide, box_high, body_deep, radius=wide * 0.03, bevel=0.002)
    lid = plate(wide * 0.98, box_high * 0.98, lid_deep, radius=wide * 0.03, bevel=lid_deep * 0.3, back=body_deep)
    found = {"box": body, "lid": lid}
    for part in found.values():
        part.apply_translation([0, middle, 0])
    corner_x, corner_y = wide * 0.42, box_high * 0.42
    found["screw"] = trimesh.util.concatenate([screw(wide * 0.035, (sx * corner_x, middle + sy * corner_y, deep - 0.0005))
                                               for sx in (-1, 1) for sy in (-1, 1)])
    glands = []
    for count, sign in ((below, -1), (above, 1)):
        for side in np.linspace(-wide * 0.3, wide * 0.3, count) if count > 1 else [0.0] * count:
            start = (side, middle + sign * box_high / 2, body_deep * 0.55)
            glands.append(gland(wide * 0.06, gland_long, start, (0, sign, 0)))
    found["gland"] = trimesh.util.concatenate(glands)
    return found


def meter(size, cables=2):
    """An old electricity meter box (the stairwell's nine): an upright box with a hinged door, a glazed window high on
    it showing the meter's dial face, two hinges on its left edge and `cables` cables down from its foot."""
    wide, deep, tall = size
    box_high = tall * 0.74
    bottom = tall - box_high
    body = plate(wide, box_high, deep * 0.8, radius=wide * 0.03, bevel=0.002)
    door = plate(wide * 0.94, box_high * 0.95, deep * 0.12, radius=wide * 0.03, bevel=0.002, back=deep * 0.8)
    window_y = box_high * 0.2
    window_wide, window_high = wide * 0.52, box_high * 0.24
    rim = frame(window_wide * 1.12, window_high * 1.15, deep * 0.04, window_wide * 0.06, back=deep * 0.92)
    for part in (body, door, rim):
        part.apply_translation([0, bottom + box_high / 2, 0])
    glass = plate(window_wide, window_high, deep * 0.02, back=deep * 0.925)
    dial = plate(window_wide * 0.9, window_high * 0.85, 0.002, back=deep * 0.92 - 0.0005)
    needle = block(window_wide * 0.02, window_high * 0.45, 0.001, (window_wide * 0.1, 0, deep * 0.92 + 0.002))
    needle.apply_transform(trimesh.transformations.rotation_matrix(math.radians(-35), [0, 0, 1]))
    for part in (glass, dial, needle):
        part.apply_translation([0, bottom + box_high / 2 + window_y, 0])
    hinges = trimesh.util.concatenate([rod(wide * 0.025, (-wide * 0.48, bottom + box_high * share, deep * 0.9),
                                           (-wide * 0.48, bottom + box_high * share + box_high * 0.1, deep * 0.9))
                                       for share in (0.15, 0.75)])
    leads = trimesh.util.concatenate([rod(wide * 0.03, (side, bottom + 0.01, deep * 0.4), (side, 0, deep * 0.4))
                                      for side in np.linspace(-wide * 0.22, wide * 0.22, cables)])
    return {"box": trimesh.util.concatenate([body, rim]), "door": door, "window": glass,
            "dial": trimesh.util.concatenate([dial, needle]), "hinge": hinges, "cable": leads}


def split_ac(size, fan="left", bracket=True, cover=True):
    """An air conditioner's outdoor unit (the street's and stairwell's): a rounded case, a round fan opening on its
    `fan` side behind a ringed wire guard with the blades behind it, fine horizontal vents beside it, a slatted grille
    on the far side face, a service cover and, with `bracket`, the two angle brackets it sits on against the wall."""
    wide, deep, tall = size
    hold = tall * 0.16 if bracket else 0.0
    case_high, case_deep = tall - hold, deep * 0.94
    case = plate(wide, case_high, case_deep, radius=wide * 0.03, bevel=0.006)
    case.apply_translation([0, hold + case_high / 2, 0])
    sign = -1 if fan == "left" else 1
    radius = case_high * 0.38
    centre = np.array([sign * (wide / 2 - case_high * 0.48), hold + case_high / 2, case_deep])
    rim = bent([(centre[0] + radius * 1.04 * math.cos(angle), centre[1] + radius * 1.04 * math.sin(angle),
                 case_deep + 0.004) for angle in np.linspace(0, 2 * math.pi, 64, endpoint=False)], 0.006, closed=True)
    guard = fan_guard(radius, 0.0022, 6, 8, centre + [0, 0, 0.012])
    fan_part = blades(radius * 0.92, 4, centre - [0, 0, radius * 0.25])
    hollow = turned([(0, -0.03), (radius * 0.99, -0.03), (radius * 0.99, 0.001), (0, 0.001)], at=centre)
    vent_wide = wide - case_high * 0.96 - 0.06
    vents = bars(vent_wide, case_high * 0.42, 9, 0.004, 0.006, across=True, back=case_deep - 0.001)
    vents.apply_translation([-sign * (wide / 2 - vent_wide / 2 - 0.03), hold + case_high * 0.3, 0])
    side = bars(case_deep * 0.62, case_high * 0.62, 12, 0.006, 0.006, back=0)
    side.apply_transform(trimesh.transformations.rotation_matrix(-sign * math.pi / 2, [0, 1, 0]))
    side.apply_translation([-sign * (wide / 2 - 0.0005), hold + case_high * 0.42, case_deep * 0.5])
    found = {"case": case, "guard": trimesh.util.concatenate([rim, guard]),
             "fan": trimesh.util.concatenate([fan_part, hollow]), "grille": trimesh.util.concatenate([vents, side])}
    if cover:
        lid = plate(case_deep * 0.55, case_high * 0.3, 0.006, radius=0.006, bevel=0.002)
        lid.apply_transform(trimesh.transformations.rotation_matrix(-sign * math.pi / 2, [0, 1, 0]))
        lid.apply_translation([-sign * (wide / 2 - 0.001), hold + case_high * 0.8, case_deep * 0.55])
        found["cover"] = lid
    if bracket:
        arms = []
        for x in (-wide * 0.36, wide * 0.36):
            arms += [block(0.035, 0.005, deep, (x, hold - 0.0025, deep / 2)),
                     block(0.035, hold, 0.005, (x, hold / 2, 0.0025)),
                     rod(0.008, (x, 0.01, 0.004), (x, hold - 0.006, deep * 0.85), sections=4)]
        found["bracket"] = trimesh.util.concatenate(arms)
    return found


def window_ac(size, slats=11, brace=True):
    """A box window air conditioner (the street's and stairwell's): a case open at its front round a field of
    leaning louvres in a rim, a slotted grille on its right side and, with `brace`, a diagonal angle brace on that
    side down to the sill."""
    wide, deep, tall = size
    wall = 0.012
    case = trimesh.util.concatenate([
        plate(wide, tall, deep * 0.08, radius=0.008, bevel=0.002),
        frame(wide, tall, deep * 0.92, wall, back=deep * 0.08),
        block(wide - 2 * wall, tall - 2 * wall, 0.01, (0, 0, deep * 0.55))])
    case.apply_translation([0, tall / 2, 0])
    field_wide, field_high = wide - 2 * wall - 0.02, tall - 2 * wall - 0.02
    rim = frame(field_wide + 0.02, field_high + 0.02, 0.012, 0.012, back=deep - 0.012)
    blades_part = louvres(field_wide, field_high, slats, min(deep * 0.4, 0.05), lean=30.0, back=deep - 0.06)
    for part in (rim, blades_part):
        part.apply_translation([0, tall / 2, 0])
    grille = trimesh.util.concatenate([frame(deep * 0.45, tall * 0.55, 0.006, 0.01),
                                       bars(deep * 0.4, tall * 0.5, 7, 0.006, 0.006)])
    grille.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
    grille.apply_translation([wide / 2 - 0.0005, tall * 0.55, deep * 0.4])
    found = {"case": trimesh.util.concatenate([case, rim]), "louvre": blades_part, "grille": grille}
    if brace:
        found["brace"] = trimesh.util.concatenate([
            rod(0.007, (wide / 2 + 0.004, 0.02, deep * 0.12), (wide / 2 + 0.004, tall - 0.03, deep * 0.9), sections=4),
            block(0.006, 0.03, deep * 0.9, (wide / 2 + 0.004, 0.015, deep * 0.5))])
    return found


def grate(size, rows=2, slots=12):
    """A cast-iron kerb gully grate lying in the road (the street's six): a chamfered frame, `rows` fields of `slots`
    slots each between round-topped bars and a rib between the fields, the dark gully under them."""
    wide, deep, tall = size
    rim = min(wide, deep) * 0.09
    frame_part = trimesh.util.concatenate([block(wide, tall, rim, (0, tall / 2, (deep - rim) / 2)),
                                           block(wide, tall, rim, (0, tall / 2, -(deep - rim) / 2)),
                                           block(rim, tall, deep - 2 * rim, ((wide - rim) / 2, tall / 2, 0)),
                                           block(rim, tall, deep - 2 * rim, (-(wide - rim) / 2, tall / 2, 0))])
    inner_wide, inner_deep = wide - 2 * rim, deep - 2 * rim
    rib = rim * 0.6
    field = (inner_deep - rib * (rows - 1)) / rows
    pitch = inner_wide / slots
    found_bars = [block(inner_wide, tall * 0.9, rib, (0, tall * 0.45, -inner_deep / 2 + field * (row + 1) + rib * (row + 0.5)))
                  for row in range(rows - 1)]
    for row in range(rows):
        middle = -inner_deep / 2 + field * (row + 0.5) + rib * row
        for number in range(slots + 1):
            x = -inner_wide / 2 + pitch * number
            found_bars.append(block(pitch * 0.42, tall * 0.85, field + 0.002, (x, tall * 0.425, middle)))
    gully = block(inner_wide, 0.004, inner_deep, (0, tall * 0.08, 0))
    return {"frame": frame_part, "bars": trimesh.util.concatenate(found_bars), "gully": gully}


def intercom(size, rows=4, columns=3, speaker=(4, 5)):
    """A door intercom (the street's): a rounded body, a raised faceplate, a dark display window high on its right, a
    grid of speaker holes beside it, a `rows` x `columns` keypad of rounded keys and a call key under the speaker."""
    wide, deep, tall = size
    body = plate(wide, tall, deep * 0.7, radius=wide * 0.12, bevel=deep * 0.12)
    face = plate(wide * 0.86, tall * 0.9, deep * 0.12, radius=wide * 0.08, bevel=deep * 0.05, back=deep * 0.7 - 0.0005)
    front = deep * 0.82
    screen = plate(wide * 0.42, tall * 0.13, 0.002, radius=0.002, back=front - 0.0008)
    screen.apply_translation([wide * 0.16, tall * 0.28, 0])
    holes = []
    for row in range(speaker[1]):
        for column in range(speaker[0]):
            holes.append(turned([(0, front - 0.0012), (wide * 0.018, front - 0.0012), (wide * 0.018, front + 0.0004),
                                 (0, front + 0.0004)], at=(-wide * 0.3 + column * wide * 0.055,
                                                           tall * 0.33 - row * tall * 0.035, 0), sections=10))
    key_wide, key_high = wide * 0.13, tall * 0.065
    keys = [key(key_wide, key_high, deep * 0.1, (wide * 0.05 + (column - 0.5) * key_wide * 1.45,
                                                    tall * 0.1 - row * key_high * 1.5, front - 0.0005))
            for row in range(rows) for column in range(columns)]
    keys.append(key(key_wide * 1.1, key_high * 1.2, deep * 0.1, (-wide * 0.25, -tall * 0.3, front - 0.0005)))
    found = {"body": body, "faceplate": face, "screen": screen, "speaker": trimesh.util.concatenate(holes),
             "keys": trimesh.util.concatenate(keys)}
    for part in found.values():
        part.apply_translation([0, tall / 2, 0])
    return found


KINDS = {"knob": knob, "lever": lever, "pull": pull, "nail": nail, "switch": switch, "socket": socket,
         "junction": junction, "meter": meter, "split_ac": split_ac, "window_ac": window_ac, "grate": grate,
         "intercom": intercom}
FLAT = {"grate"}  # built lying, its top up; every other kind built facing +z from its back on z = 0


def parts(kind, size, **options):
    """The product of `kind` at `size` (wide, deep, tall metres) with its `options`, as the maker lays a model: y up,
    front +z, stood on y = 0, centred on x and z; {part: mesh}."""
    if kind not in KINDS:
        raise ValueError(f"no hardware kind {kind!r} (the kinds: {', '.join(sorted(KINDS))})")
    built = KINDS[kind]([float(side) for side in size], **options)
    whole = trimesh.util.concatenate(list(built.values()))
    low, high = whole.bounds
    shift = [-(low[0] + high[0]) / 2, -low[1], -(low[2] + high[2]) / 2]
    for mesh in built.values():
        mesh.apply_translation(shift)
    return built


# --- the file ------------------------------------------------------------------------------------------------------

def edged(mesh):
    """`mesh` with its vertices split along edges whose faces turn over SHARP degrees, each vertex given box-projected
    texture coordinates by its own normal (so a reader merging equal vertices keeps a hard edge's two sides apart)."""
    mesh = trimesh.graph.smooth_shade(mesh, angle=math.radians(SHARP))
    normals = mesh.vertex_normals
    axis = np.argmax(np.abs(normals), axis=1)
    pairs = {0: (2, 1), 1: (0, 2), 2: (0, 1)}
    uv = np.array([[point[pairs[way][0]], point[pairs[way][1]]] for point, way in zip(mesh.vertices, axis)])
    uv = uv + axis[:, None] * 10.0  # each projection its own region, so two sides of an edge never share a texel
    mesh.visual = trimesh.visual.TextureVisuals(uv=uv)
    return mesh


def tint(part):
    """A part's stand-in preview colour by its name (TINTS), RGBA 0..255."""
    named = {"plate": "grey", "knob": "brass", "rose": "brass", "lever": "brass", "screw": "steel", "handle": "steel",
             "foot": "steel", "nail": "steel", "wire": "steel", "rocker": "white", "face": "white", "hole": "black",
             "box": "grey", "lid": "grey", "gland": "rust", "door": "grey", "window": "glass", "dial": "white",
             "hinge": "rust", "cable": "black", "case": "white", "guard": "grey", "fan": "dark", "grille": "grey",
             "cover": "white", "bracket": "rust", "louvre": "grey", "brace": "rust", "frame": "rust", "bars": "rust",
             "gully": "black", "body": "grey", "faceplate": "grey", "screen": "glass", "speaker": "black",
             "keys": "steel"}
    hexed = TINTS[named.get(part, "grey")]
    return [int(hexed[index:index + 2], 16) for index in (1, 3, 5)] + [255]


def written(built, path):
    """The parts as one GLB at `path`: a mesh a part, each with a material of the part's name (its stand-in tint)."""
    scene = trimesh.Scene()
    for name, mesh in built.items():
        shown = edged(mesh)
        shown.visual.material = trimesh.visual.material.PBRMaterial(name=name, baseColorFactor=tint(name),
                                                                    metallicFactor=0.0, roughnessFactor=0.6)
        scene.add_geometry(shown, geom_name=name, node_name=name)
    pathlib.Path(path).write_bytes(scene.export(file_type="glb", include_normals=True))
    return path


def closed(built):
    """{part: whether every piece of it is a closed solid} (a reader of volume and hulls needs it so)."""
    return {name: all(piece.is_watertight for piece in mesh.split(only_watertight=False)) for name, mesh in built.items()}


def made(kind, size, out, entry, words, material, picture=None, options=None, weigh=None):
    """The product built and written for the library under `out`: `<entry>-final.glb` (its parts), `<entry>-hulls.glb`
    (CoACD's) and `<entry>.json` (kind, size, options, parts, its physics as the maker's record holds it, so the scene
    package reads its mass alike); the record. `weigh` answers the mass ask (a test's), else Claude's."""
    from score.stages.place_build.maker import sim
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    built = parts(kind, size, **(options or {}))
    written(built, out / f"{entry}-final.glb")
    whole = trimesh.util.concatenate(list(built.values()))
    hulls = sim.hulls_of(whole.vertices, whole.faces)
    scene = trimesh.Scene()
    for number, (points, triangles) in enumerate(hulls):
        scene.add_geometry(trimesh.Trimesh(points, triangles, process=False), geom_name=f"hull_{number}")
    scene.export(str(out / f"{entry}-hulls.glb"))
    extent = whole.extents  # x, y, z
    laid = [float(extent[0]), float(extent[2]), float(extent[1])]  # wide, deep, tall
    areas = {name: float(mesh.area) for name, mesh in built.items()}
    total = sum(areas.values())
    rows = [{"words": f"{words}: {name}", "class": material, "share": areas[name] / total} for name in built]
    masses = sim.weighed(words, laid, rows, picture, ask=weigh)
    for row, mass in zip(rows, masses):
        row["kg"] = round(mass, 4)
    physics = sim.physical(hulls, [material] * len(hulls), rows, laid)
    record = {"maker": "score hardware", "kind": kind, "size_m": [round(side, 4) for side in laid],
              "row_size_m": [float(side) for side in size], "options": options or {}, "parts": sorted(built),
              "closed": closed(built), "physics": physics, "hulls_file": f"{entry}-hulls.glb",
              "faces": int(sum(len(mesh.faces) for mesh in built.values()))}
    (out / f"{entry}.json").write_text(json.dumps(record, indent=1))
    return {**record, "files": files_of(out, entry)}


def files_of(out, entry):
    """{file name: path} of the product `made` wrote for `entry` under `out`."""
    out = pathlib.Path(out)
    return {path.name: path for path in (out / f"{entry}-final.glb", out / f"{entry}-hulls.glb", out / f"{entry}.json")}


def listed(entry, record, title, out):
    """One built product as a score-lib take-in listing's entry: its files, what made it and its tags."""
    made_with = [{"what": f"{entry}: built in code as a {record['kind']} of parts {', '.join(record['parts'])} at "
                          f"{' x '.join(f'{side:g}' for side in record['size_m'])} m (score place_build hardware), "
                          "its proportions its approved close-up's", "source": "score"},
                 {"what": "CoACD hulls and a real-world mass a part (Claude's answer) by score place_build make's sim",
                  "source": "score"}]
    return {"kind": "model", "id": entry, "title": title,
            "files": {name: {"path": str(path), "from": f"made/{name}"} for name, path in files_of(out, entry).items()},
            "made_with": made_with, "tags": {"maker": ["score_hardware"]}}


def listing(items, commit):
    """The score-lib take-in listing of built products, `items` [(entry, record, title, out folder)]."""
    return {"world": "world1", "commit": commit, "taken_from": "score place_build hardware (built in code)",
            "entries": [listed(*item) for item in items]}


def taken_in(items, work):
    """The built products `items` [(entry, record, title, out folder)] committed to score_lib in one take-in as draft
    `model/<entry>` entries (score-lib take-in --save), under the maker's take-in lock so they go in one at a time with
    every make; their addresses."""
    import fcntl
    import subprocess
    import sys
    from score.stages import place_build
    from score.stages.place_build import maker
    sys.path.insert(0, str(maker.REPO / "tools/library"))
    import library_files
    import pixal_takes
    values = library_files.settings()
    root = values.get("SCORE_LIB_ROOT")
    if not root:
        raise place_build.Refused("no library is configured (SCORE_LIB_ROOT)")
    work = pathlib.Path(work)
    work.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "-C", str(maker.REPO), "rev-parse", "HEAD"], capture_output=True,
                            text=True).stdout.strip()
    asked, report = work / "take-in.json", work / "take-in-report.json"
    asked.write_text(json.dumps(listing(items, commit), indent=1))
    report.unlink(missing_ok=True)
    with open(maker.lock_file(root), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        maker.brought_forward(root)
        done = pixal_takes.library_command(values, "take-in", str(asked), "--save", "--report", str(report))
    if not report.is_file():
        raise place_build.Refused(f"score-lib take-in exited {done.returncode}: {(done.stderr or done.stdout)[-400:]}")
    answer = json.loads(report.read_text())
    if answer.get("refused"):
        raise place_build.Refused(f"score-lib refused the entry: {answer['refused']}")
    if answer.get("saved") and not answer["saved"].get("pushed"):
        raise place_build.Refused(f"score-lib wrote the entry but did not push it: {answer['saved']}")
    return [place_build.resolved_address(f"model/{item[0]}", root) for item in items]
