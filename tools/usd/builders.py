"""Code builders for what a place's own engine code drew and no kit piece covers: room shells, stepped floors and pits,
stairs, domes, a water surface, a far backdrop ring, a ground of planned heights. Each builder takes plain numbers (from
the place's scene record, data/scene/<place>.json, read by tools/usd/scene.py) and gives meshes in the place's frame
(metres, y up): {"points": (n, 3), "triangles": (m, 3), "uvs": (n, 2) in metres along the surface (a picture's 0..1 for
a backdrop), "surface": the library surface it is painted with}. Nothing here knows an engine.

A builder's faces look the way its surface is seen: a wall's inside faces into the room, a floor's up, a dome's and a
backdrop ring's inward. Meshes are drawn double sided, so this matters only for normals.
"""
import math

import numpy as np


def mesh(points, triangles, uvs, surface):
    return {"points": np.asarray(points, dtype=np.float64).reshape(-1, 3),
            "triangles": np.asarray(triangles, dtype=np.int64).reshape(-1, 3),
            "uvs": np.asarray(uvs, dtype=np.float64).reshape(-1, 2), "surface": surface}


def joined(meshes):
    """Several meshes of one surface as one."""
    points, triangles, uvs, offset = [], [], [], 0
    for part in meshes:
        points.append(part["points"])
        triangles.append(part["triangles"] + offset)
        uvs.append(part["uvs"])
        offset += len(part["points"])
    return mesh(np.vstack(points), np.vstack(triangles), np.vstack(uvs), meshes[0]["surface"])


def quad(corners, surface, uv_size=None):
    """A flat four-cornered face (corners in order round it), its uvs its own metres."""
    corners = np.asarray(corners, dtype=np.float64)
    along = np.linalg.norm(corners[1] - corners[0])
    up = np.linalg.norm(corners[3] - corners[0])
    wide, tall = uv_size or (along, up)
    return mesh(corners, [[0, 1, 2], [0, 2, 3]], [[0, 0], [wide, 0], [wide, tall], [0, tall]], surface)


def box(centre, size, surface, turn=0.0):
    """A closed box, its middle at `centre`, `size` (x, y, z) in its own frame, turned `turn` degrees about up
    (clockwise seen from above, as a bearing)."""
    half = np.asarray(size, dtype=np.float64) / 2
    signs = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                      [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], dtype=np.float64)
    corners = signs * half
    angle = math.radians(turn)
    spin = np.array([[math.cos(angle), 0, math.sin(angle)], [0, 1, 0], [-math.sin(angle), 0, math.cos(angle)]])
    corners = corners @ spin.T + np.asarray(centre, dtype=np.float64)
    faces = [(0, 1, 2, 3), (5, 4, 7, 6), (4, 0, 3, 7), (1, 5, 6, 2), (3, 2, 6, 7), (4, 5, 1, 0)]
    return joined([quad(corners[list(face)], surface) for face in faces])


def polygon_ring(sides, radius, rotation=0.0):
    """The corners of a regular polygon round the middle, on the floor plane, `radius` to its corners; the first corner
    at `rotation` degrees clockwise from north (-z)."""
    angles = [math.radians(rotation + 360.0 * number / sides) for number in range(sides)]
    return np.array([[radius * math.sin(angle), 0.0, -radius * math.cos(angle)] for angle in angles])


def corner_radius(sides, apothem):
    return apothem / math.cos(math.pi / sides)


def annulus(sides, inner, outer, height, surface, rotation=0.0):
    """A flat ring between two regular polygons (`inner` 0 for a full disc) at `height`, facing up."""
    outside = polygon_ring(sides, outer, rotation) + [0, height, 0]
    if inner <= 0:
        points = np.vstack([[[0.0, height, 0.0]], outside])
        triangles = [[0, 1 + (number + 1) % sides, 1 + number] for number in range(sides)]
        return mesh(points, triangles, points[:, [0, 2]], surface)
    inside = polygon_ring(sides, inner, rotation) + [0, height, 0]
    points = np.vstack([inside, outside])
    triangles = []
    for number in range(sides):
        following = (number + 1) % sides
        triangles += [[number, sides + following, sides + number], [number, following, sides + following]]
    return mesh(points, triangles, points[:, [0, 2]], surface)


def walls(sides, apothem, low, high, surface, rotation=0.0, openings=()):
    """The inside faces of a regular polygon's walls from `low` to `high`; `openings` are (bearing, wide, tall)
    doorways cut out of the facet that bearing falls on (the wall above the doorway stays)."""
    corners = polygon_ring(sides, corner_radius(sides, apothem), rotation)
    faces = []
    for number in range(sides):
        start, end = corners[number], corners[(number + 1) % sides]
        middle_bearing = (rotation + 360.0 * (number + 0.5) / sides) % 360.0
        cut = next((opening for opening in openings
                    if abs((opening[0] - middle_bearing + 180.0) % 360.0 - 180.0) < 180.0 / sides), None)
        faces += wall_strip(start, end, low, high, surface, cut)
    return joined(faces)


def wall_strip(start, end, low, high, surface, cut=None):
    """One straight wall from `start` to `end` (floor points) between two heights, with an optional centred doorway
    (bearing, wide, tall)."""
    start, end = np.asarray(start, dtype=np.float64), np.asarray(end, dtype=np.float64)
    up = np.array([0.0, 1.0, 0.0])

    def panel(first, second, bottom, top):
        return quad([first + up * bottom, second + up * bottom, second + up * top, first + up * top], surface)
    if cut is None:
        return [panel(start, end, low, high)]
    length = np.linalg.norm(end - start)
    direction = (end - start) / length
    half = min(cut[1] / 2, length / 2)
    left, right = start + direction * (length / 2 - half), start + direction * (length / 2 + half)
    found = [panel(start, left, low, high), panel(right, end, low, high)]
    if low + cut[2] < high:
        found.append(panel(left, right, low + cut[2], high))
    return found


def pyramid_roof(sides, apothem, eave, rise, surface, rotation=0.0):
    """A regular polygon's roof from its walls' top (`eave`) up `rise` to a point over the middle."""
    corners = polygon_ring(sides, corner_radius(sides, apothem), rotation) + [0, eave, 0]
    points = np.vstack([[[0.0, eave + rise, 0.0]], corners])
    triangles = [[0, 1 + number, 1 + (number + 1) % sides] for number in range(sides)]
    return mesh(points, triangles, points[:, [0, 2]], surface)


def dome(radius, base, surface, rings=12, segments=48, rise=None, centre=(0.0, 0.0)):
    """A dome over a circle of `radius` standing at `base`: a spherical cap `rise` high (a half sphere by default)."""
    rise = radius if rise is None else rise
    sphere = (radius ** 2 + rise ** 2) / (2 * rise)
    lowest = math.asin(min(1.0, radius / sphere))
    points, uvs = [], []
    for ring in range(rings + 1):
        polar = lowest * (1 - ring / rings)
        for segment in range(segments + 1):
            azimuth = 2 * math.pi * segment / segments
            across = sphere * math.sin(polar)
            points.append([centre[0] + across * math.sin(azimuth), base + sphere * math.cos(polar) - (sphere - rise),
                           centre[1] - across * math.cos(azimuth)])
            uvs.append([azimuth * sphere, polar * sphere])
    triangles = []
    for ring in range(rings):
        for segment in range(segments):
            first = ring * (segments + 1) + segment
            below = first + segments + 1
            triangles += [[first, below, first + 1], [first + 1, below, below + 1]]
    return mesh(points, triangles, uvs, surface)


def cylinder_wall(radius, low, high, surface, segments=48, centre=(0.0, 0.0), start=0.0, sweep=360.0):
    """An upright cylinder's side (part of one when `sweep` < 360) from `low` to `high`."""
    points, uvs = [], []
    for segment in range(segments + 1):
        angle = math.radians(start + sweep * segment / segments)
        for height in (low, high):
            points.append([centre[0] + radius * math.sin(angle), height, centre[1] - radius * math.cos(angle)])
            uvs.append([radius * math.radians(sweep * segment / segments), height - low])
    triangles = []
    for segment in range(segments):
        first = 2 * segment
        triangles += [[first, first + 2, first + 1], [first + 1, first + 2, first + 3]]
    return mesh(points, triangles, uvs, surface)


def disc(radius, height, surface, segments=48, centre=(0.0, 0.0)):
    """A flat round floor or lid facing up."""
    points = [[centre[0], height, centre[1]]]
    for segment in range(segments):
        angle = 2 * math.pi * segment / segments
        points.append([centre[0] + radius * math.sin(angle), height, centre[1] - radius * math.cos(angle)])
    points = np.asarray(points)
    triangles = [[0, 1 + (segment + 1) % segments, 1 + segment] for segment in range(segments)]
    return mesh(points, triangles, points[:, [0, 2]], surface)


def stairs(foot, top, wide, steps, surface, rise_from=None):
    """A straight flight of solid steps from `foot` (a floor point at the bottom of the first riser) up to `top` (the
    floor point where the last tread ends), `wide` across; each step a box down to the flight's foot."""
    foot, top = np.asarray(foot, dtype=np.float64), np.asarray(top, dtype=np.float64)
    run = top - foot
    flat = np.array([run[0], 0.0, run[2]])
    length = np.linalg.norm(flat)
    turn = math.degrees(math.atan2(flat[0], -flat[2]))
    rise = run[1] / steps
    bottom = foot[1] if rise_from is None else rise_from
    found = []
    for step in range(steps):
        far = (step + 1) / steps
        near = step / steps
        middle = foot + flat * (near + far) / 2
        height = foot[1] + rise * (step + 1)
        found.append(box([middle[0], (bottom + height) / 2, middle[2]], [wide, height - bottom, length / steps],
                         surface, turn))
    return joined(found)


def grid(low, high, height, surface, step):
    """A flat rectangle at `height` from `low` to `high` (x, z), cut into squares `step` wide (a water surface, a
    floor): uvs in metres."""
    xs = np.arange(low[0], high[0] + step * 0.5, step)
    zs = np.arange(low[1], high[1] + step * 0.5, step)
    xx, zz = np.meshgrid(xs, zs)
    points = np.column_stack([xx.ravel(), np.full(xx.size, height), zz.ravel()])
    columns = len(xs)
    triangles = []
    for row in range(len(zs) - 1):
        for column in range(columns - 1):
            first = row * columns + column
            triangles += [[first, first + columns, first + 1], [first + 1, first + columns, first + columns + 1]]
    return mesh(points, triangles, points[:, [0, 2]], surface)


def backdrop_ring(radius, low, high, surface, segments=96, centre=(0.0, 0.0), start=0.0):
    """A far panorama ring round the place, facing in, its uvs the picture's 0..1 once round (u from `start`
    bearing clockwise), v from its foot to its top."""
    ring = cylinder_wall(radius, low, high, surface, segments, centre, start, 360.0)
    ring["uvs"] = np.column_stack([np.repeat(np.linspace(0.0, 1.0, segments + 1), 2),
                                   np.tile([0.0, 1.0], segments + 1)])
    return ring


def heightfield(heights, low, high, surface, uv_low=(0.0, 0.0), uv_high=(1.0, 1.0)):
    """A ground of sampled heights over a rectangle (`heights` rows along z, columns along x), uvs spread from uv_low
    to uv_high over it (a colour map's part)."""
    heights = np.asarray(heights, dtype=np.float64)
    rows, columns = heights.shape
    xs = np.linspace(low[0], high[0], columns)
    zs = np.linspace(low[1], high[1], rows)
    xx, zz = np.meshgrid(xs, zs)
    points = np.column_stack([xx.ravel(), heights.ravel(), zz.ravel()])
    us = np.linspace(uv_low[0], uv_high[0], columns)
    vs = np.linspace(uv_low[1], uv_high[1], rows)
    uu, vv = np.meshgrid(us, vs)
    triangles = []
    for row in range(rows - 1):
        for column in range(columns - 1):
            first = row * columns + column
            triangles += [[first, first + columns, first + 1], [first + 1, first + columns, first + columns + 1]]
    return mesh(points, triangles, np.column_stack([uu.ravel(), vv.ravel()]), surface)


def room_outline(wide, deep, corner, inset=0.0, steps=4):
    """A rounded-corner room's outline seen from above, as the game's ModuleShell.outline draws it: (x, z) points round
    it, each corner `steps` straight cuts of a quarter circle `corner` in radius, pushed in by `inset` (out when less
    than nothing); the corner keeps its middle, so it narrows as the walls come in."""
    half = np.array([wide / 2.0 - inset, deep / 2.0 - inset])
    reach = min(max(corner - inset, 0.0), half.min())
    points = []
    for which, signs in enumerate(((1.0, 1.0), (1.0, -1.0), (-1.0, -1.0), (-1.0, 1.0))):
        middle = np.array([signs[0] * (half[0] - reach), signs[1] * (half[1] - reach)])
        start = math.radians(90.0 - 90.0 * which)
        for step in range(steps + 1):
            angle = start - math.pi / 2.0 * step / steps
            points.append(middle + np.array([math.cos(angle), math.sin(angle)]) * reach)
    return np.array(points)


def room_walls(wide, deep, corner, high, surface, doors=(), low=0.0, steps=4):
    """A rounded room's walls on its outline, inside faces, from `low` to `high`, with a doorway (wide, tall) cut in
    the middle of each wall a door names (`doors`: [{"side": north|south|east|west, "wide", "tall"}])."""
    outline = room_outline(wide, deep, corner, 0.0, steps)
    faces = []
    count = len(outline)
    for number in range(count):
        start, end = outline[number], outline[(number + 1) % count]
        if np.linalg.norm(end - start) < 1e-6:
            continue
        middle = (start + end) / 2
        cut = None
        for door in doors:
            normal = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}[door["side"]]
            along = abs(normal[0]) < 0.5
            if (abs(middle[1] - normal[1] * deep / 2) < 1e-3 if along else abs(middle[0] - normal[0] * wide / 2) < 1e-3):
                cut = (0.0, float(door["wide"]), float(door["tall"]))
        faces += wall_strip([start[0], 0.0, start[1]], [end[0], 0.0, end[1]], low, high, surface, cut)
    return joined(faces)


def room_deck(wide, deep, corner, height, surface, steps=4, holes=()):
    """A rounded room's deck: its outline filled flat at `height`, facing up (a fan from its middle); `holes` are
    round openings (x, z, radius) left out of it (a pit), cut as the fan's triangles whose middles fall in them."""
    outline = room_outline(wide, deep, corner, 0.0, steps)
    rings = 12
    points, triangles = [[0.0, height, 0.0]], []
    for ring in range(1, rings + 1):
        for point in outline:
            points.append([point[0] * ring / rings, height, point[1] * ring / rings])
    count = len(outline)
    for number in range(count):
        following = (number + 1) % count
        triangles.append([0, 1 + following, 1 + number])
        for ring in range(1, rings):
            inner, outer = 1 + (ring - 1) * count, 1 + ring * count
            triangles += [[inner + number, inner + following, outer + following],
                          [inner + number, outer + following, outer + number]]
    points, triangles = np.array(points), np.array(triangles)
    for hole in holes:
        middles = points[triangles].mean(axis=1)
        keep = np.hypot(middles[:, 0] - hole[0], middles[:, 2] - hole[1]) > hole[2]
        triangles = triangles[keep]
    return mesh(points, triangles, points[:, [0, 2]], surface)


def dome_roof(wide, deep, corner, eave, rise, run, surface, rings=6, steps=4):
    """A rounded room's dome roof from its walls' top (`eave`), as ModuleShell.roof_rings draws it: ring k of `rings`
    pulled in by run (1 - cos) and raised by rise sin of k quarter-turns over rings, the last closed flat."""
    run = min(run, min(wide, deep) / 2.0 - 0.3) if run > 0 else min(wide, deep) / 2.0 * 0.55
    outlines = []
    for ring in range(rings + 1):
        angle = math.pi / 2.0 * ring / rings
        inward = run * (1.0 - math.cos(angle))
        flat = room_outline(wide, deep, corner, inward, steps)
        outlines.append(np.column_stack([flat[:, 0], np.full(len(flat), eave + rise * math.sin(angle)), flat[:, 1]]))
    count = len(outlines[0])
    points = np.vstack(outlines + [[[0.0, eave + rise, 0.0]]])
    triangles = []
    for ring in range(rings):
        for number in range(count):
            following = (number + 1) % count
            low, high = ring * count, (ring + 1) * count
            triangles += [[low + number, high + number, high + following], [low + number, high + following,
                                                                             low + following]]
    top = len(points) - 1
    triangles += [[rings * count + number, top, rings * count + (number + 1) % count] for number in range(count)]
    return mesh(points, triangles, points[:, [0, 2]], surface)


def lathe(profile, centre, surface, sides=24, turn=0.0):
    """A turned body standing on `centre` (a rocket, a tank): `profile` is [start, end, radius at start, radius at
    end] rows up its height, each a frustum's side; a closed cap where a radius is nought is left as a point."""
    found = []
    for start, end, bottom, top in profile:
        points, uvs = [], []
        for segment in range(sides + 1):
            angle = 2 * math.pi * segment / sides + math.radians(turn)
            for height, radius in ((start, bottom), (end, top)):
                points.append([centre[0] + radius * math.sin(angle), centre[1] + height,
                               centre[2] - radius * math.cos(angle)])
                uvs.append([angle * max(bottom, top), height])
        triangles = []
        for segment in range(sides):
            first = 2 * segment
            triangles += [[first, first + 2, first + 1], [first + 1, first + 2, first + 3]]
        found.append(mesh(points, triangles, uvs, surface))
        for height, radius in ((start, bottom), (end, top)):
            if radius > 0.0:
                found.append(disc(radius, centre[1] + height, surface, sides, (centre[0], centre[2])))
    return joined(found)


def sphere(centre, radius, surface, rings=24, segments=48):
    """A ball (a world seen in the sky, a lamp's globe), its uvs its longitude and latitude."""
    points, uvs = [], []
    for ring in range(rings + 1):
        polar = math.pi * ring / rings
        for segment in range(segments + 1):
            azimuth = 2 * math.pi * segment / segments
            points.append([centre[0] + radius * math.sin(polar) * math.sin(azimuth),
                           centre[1] + radius * math.cos(polar),
                           centre[2] - radius * math.sin(polar) * math.cos(azimuth)])
            uvs.append([segment / segments, 1.0 - ring / rings])
    triangles = []
    for ring in range(rings):
        for segment in range(segments):
            first = ring * (segments + 1) + segment
            below = first + segments + 1
            triangles += [[first, below, first + 1], [first + 1, below, below + 1]]
    return mesh(points, triangles, uvs, surface)


def tube_arc(radius, axis_high, start, end, length, surface, segments=24):
    """A walkway tube's hull between two angles (degrees from straight up, toward +x), its axis `axis_high` over the
    deck, running `length` along z from 0, facing in."""
    points, uvs = [], []
    for segment in range(segments + 1):
        angle = math.radians(start + (end - start) * segment / segments)
        for along in (0.0, length):
            points.append([radius * math.sin(angle), axis_high + radius * math.cos(angle), along])
            uvs.append([radius * angle, along])
    triangles = []
    for segment in range(segments):
        first = 2 * segment
        triangles += [[first, first + 1, first + 2], [first + 1, first + 3, first + 2]]
    return mesh(points, triangles, uvs, surface)
