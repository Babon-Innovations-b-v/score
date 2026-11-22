"""The dome shell algorithm (#128, the camp pilot: the kits hold no large ribbed glass dome, only straight ribs): a
hemisphere of `radius` metres standing on y = 0, one mesh `geo` with two named parts, `shell` (the thin glass skin,
one surface, faces outward) and `ribs` (curved square-section ribs over it: `meridians` from the ground to the top
and `rings` level rings between), so the placing agent wears each part its own library surface
(place_build.surface --part shell surface/clear_glass, --part ribs a metal).

A third part, `deck`, is the dome's floor: a flat disc of its radius DECK over y = 0, faces up. The same disc alone, of any
radius, is a laid ground (`disc_file`, place_build.ground), so a regolith or concrete surface has a ground to lie on
with no kit piece's stylised terrain under it.

    shell(path, radius, meridians=MERIDIANS, rings=RINGS, rib=RIB, openings=())
                                                                     the dome written as a USD file at `path`
    disc_file(path, radius)                                          a flat ground disc written at `path`
    tube(path, radius, length, hoops=HOOPS, rib=RIB, cap=None, trims=())
                                                                     a ribbed glass tunnel written at `path`
    blocks_file(path, boxes, bevel=BEVEL)                            solid boxes (a road, a kerbed pavement, a
                                                                     building's walls) written at `path`

**Blocks** (physics ready, the street: "no paper-thin walls, bevels on edges"): a straight-sided structure is laid as
solid boxes, each (x0, y0, z0, x1, y1, z1, part) in the object's own frame, its edges chamfered BEVEL so they catch
the light and the recipes' edge wear; every box a closed solid the walkers and a pushed object collide with, and each
box's part takes its own surface.

**Openings** (physics ready, owner 2026-11-16: "door is outside of the wall"): a dome's `openings` are level round
holes, each (around degrees from +x towards +z, radius, centre height), the size of the tunnel or airlock tube that
joins it there: the skin, ribs and base are cut away inside the hole (a walker passes, nothing stands in the way) and
a collar rib rims the hole where the tube meets the glass. A dome stands on `base`, a plinth ring BASE_HIGH high and
BASE_WIDE wide round its foot (the concept's base ring), cut at its openings. A tunnel's `cap` (door width, door
height) closes its far end with a wall CAP_THICK thick holding a doorway of that size from its deck up, so a door is
set in an opening of its wall. A tunnel's `trims` (the spheres of the domes it joins, in its own frame) take its skin
away inside them and spread its hoops between them, so it ends on the glass round its opening.

The tunnel between two domes (the concept's ribbed glass tube) is the same skin and ribs round a level axis: a
cylinder of `radius` lying along +z from 0 to `length`, its bottom on y = 0, `hoops` ring ribs evenly along it and
a flat deck (its floor) FLOOR of its radius up, parts `shell` (its glass), `wall` (its solid skin to WALL_HIGH over the
deck), `ribs` and `deck`.
"""
import math

import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdShade, Vt

MERIDIANS = 12  # ribs from the ground to the top
RINGS = 3  # level ribs between the ground and the top, evenly by angle
RIB = 0.12  # a rib's square section, metres
DECK = 0.02  # the deck's height over y = 0, so it never fights a ground laid under the dome
HOOPS = 5  # ring ribs along a tunnel
FLOOR = 0.3  # a tunnel's deck height over its bottom, in its radius
STEPS = 48  # points around the dome and along each rib (a quarter arc takes STEPS // 4)
TUBE_STEPS = 96  # points around a tunnel's skin and hoops: seen from inside at arm's length, never a polygon
FINE = 4  # a dome with openings is skinned FINE times finer, so a hole's edge follows its tube closely
BASE_HIGH = 0.22  # the plinth ring's height, metres
BASE_WIDE = 0.24  # its width, mostly outside the skin
CAP_THICK = 0.16  # a tunnel end wall's thickness
CAP_CELL = 0.05  # the end wall's grid, metres
TRIM_RING = 0.1  # a trimmed tube's rings apart, metres, so its end follows the dome's glass closely
WALL_HIGH = 0.8  # a tube's solid lower wall over its deck, metres
BEVEL = 0.02  # a block's chamfer, metres (never more than a third of its thinnest side)


def unit(angle_around, angle_up):
    """The outward unit vector at `angle_around` about up and `angle_up` over the ground (radians)."""
    return (math.cos(angle_up) * math.cos(angle_around), math.sin(angle_up), math.cos(angle_up) * math.sin(angle_around))


def in_opening(point, openings):
    """Whether `point` lies inside one of the dome's round openings (each a level cylinder from the dome's axis out
    along its `around`, of its radius, at its centre height), on the opening's own side."""
    for around, radius, centre in openings:
        towards = (math.cos(math.radians(around)), math.sin(math.radians(around)))
        along = point[0] * towards[0] + point[2] * towards[1]
        if along <= 0:
            continue
        off = (point[0] - along * towards[0], point[1] - centre, point[2] - along * towards[1])
        if math.sqrt(sum(value * value for value in off)) < radius:
            return True
    return False


def runs(points, openings):
    """The stretches of a path left outside the openings, as index lists of two or more points."""
    found, current = [], []
    for index, point in enumerate(points):
        if in_opening(point, openings):
            if len(current) > 1:
                found.append(current)
            current = []
        else:
            current.append(index)
    if len(current) > 1:
        found.append(current)
    return found


def skin(radius, openings=()):
    """The hemisphere's points and quads (and the top's triangles), faces wound outward; a face whose middle lies in
    an opening left out (finer faces when there are openings)."""
    around_steps = STEPS * (FINE if openings else 1)
    up_steps = around_steps // 4
    points = [tuple(radius * value for value in unit(2 * math.pi * around / around_steps,
                                                       math.pi / 2 * up / up_steps))
              for up in range(up_steps) for around in range(around_steps)]
    points.append((0.0, radius, 0.0))
    faces = []
    for up in range(up_steps - 1):
        for around in range(around_steps):
            following = (around + 1) % around_steps
            faces.append([up * around_steps + around, (up + 1) * around_steps + around,
                          (up + 1) * around_steps + following, up * around_steps + following])
    top = len(points) - 1
    faces += [[(up_steps - 1) * around_steps + around, top, (up_steps - 1) * around_steps + (around + 1) % around_steps]
              for around in range(around_steps)]
    kept = [face for face in faces
            if not in_opening(tuple(sum(points[index][axis] for index in face) / len(face) for axis in range(3)),
                              openings)]
    return points, kept


def disc(radius, height=0.0):
    """A flat disc of `radius` at y = `height` in rings STEPS around (rings about a metre apart, at least 2): its points
    and faces, wound to face up."""
    count = max(2, math.ceil(radius))
    points = [(0.0, height, 0.0)] + [(radius * ring / count * math.cos(2 * math.pi * around / STEPS), height,
                                   radius * ring / count * math.sin(2 * math.pi * around / STEPS))
                                  for ring in range(1, count + 1) for around in range(STEPS)]
    faces = [[0, 1 + (around + 1) % STEPS, 1 + around] for around in range(STEPS)]
    for ring in range(count - 1):
        inner, outer = 1 + ring * STEPS, 1 + (ring + 1) * STEPS
        faces += [[inner + around, inner + (around + 1) % STEPS, outer + (around + 1) % STEPS, outer + around]
                  for around in range(STEPS)]
    return points, faces


def swept(path, outward, side, rib, closed, stand=None):
    """A square-section rib along `path`: at each point its section stands outward from the skin by `rib` (`stand`
    when given, a flat band) and spans `rib` along `side`; (points, quads), open at its ends unless `closed`, wound to
    face out whichever way `side` turns."""
    stand = rib if stand is None else stand
    points = []
    for at, out, across in zip(path, outward, side):
        for along, lift in ((-0.5, 0.0), (0.5, 0.0), (0.5, 1.0), (-0.5, 1.0)):
            points.append(tuple(at[axis] + across[axis] * along * rib + out[axis] * lift * stand for axis in range(3)))
    faces = []
    count = len(path)
    # The section's corners run round it one way; they face out when the path runs along side x outward.
    ahead = np.subtract(path[1], path[0])
    turned = np.dot(ahead, np.cross(side[0], outward[0])) < 0
    for step in range(count if closed else count - 1):
        here, there = 4 * step, 4 * ((step + 1) % count)
        for corner in range(4):
            following = (corner + 1) % 4
            face = [here + corner, here + following, there + following, there + corner]
            faces.append(face[::-1] if turned else face)
    return points, faces


def cut_swept(path, outward, side, rib, closed, openings):
    """swept over the stretches of `path` outside the openings (the whole, closed if asked, when none cuts it)."""
    stretches = runs(path, openings)
    if len(stretches) == 1 and len(stretches[0]) == len(path):
        return [swept(path, outward, side, rib, closed)]
    return [swept([path[index] for index in stretch], [outward[index] for index in stretch],
                  [side[index] for index in stretch], rib, False) for stretch in stretches]


def ribs(radius, meridians, rings, rib, openings=(), oculus=0.0):
    """Every rib of the dome as (points, quads): the meridians ground to top (to the oculus ring when there is one),
    the rings level between, each cut where it crosses an opening."""
    made = []
    up_steps = STEPS // 4 * (FINE if openings else 1)
    top = math.acos(min(oculus / radius, 1.0)) if oculus > 0 else math.pi / 2
    for number in range(meridians):
        around = 2 * math.pi * number / meridians
        ups = [top * step / up_steps for step in range(up_steps + 1)]
        outward = [unit(around, up) for up in ups]
        made += cut_swept([tuple(radius * value for value in out) for out in outward], outward,
                          [(-math.sin(around), 0.0, math.cos(around))] * len(ups), rib, False, openings)
    around_steps = STEPS * (FINE if openings else 1)
    for number in range(1, rings + 1):
        up = math.pi / 2 * number / (rings + 1)
        arounds = [2 * math.pi * step / around_steps for step in range(around_steps)]
        outward = [unit(around, up) for around in arounds]
        made += cut_swept([tuple(radius * value for value in out) for out in outward], outward,
                          [(-math.sin(up) * math.cos(around), math.cos(up), -math.sin(up) * math.sin(around))
                           for around in arounds], rib, True, openings)
    return made


def collars(radius, rib, openings):
    """A rib round each opening where its tube meets the glass: the tube's circle carried out along its axis onto the
    sphere, its section across the axis."""
    made = []
    for around, hole, centre in openings:
        towards = (math.cos(math.radians(around)), 0.0, math.sin(math.radians(around)))
        side = (-towards[2], 0.0, towards[0])
        path, outward = [], []
        for step in range(STEPS):
            turn = 2 * math.pi * step / STEPS
            off = tuple(hole * (math.cos(turn) * side[axis] + math.sin(turn) * (axis == 1)) for axis in range(3))
            off = (off[0], off[1] + centre, off[2])
            along = math.sqrt(max(radius ** 2 - sum(value * value for value in off), 0.0))
            point = tuple(off[axis] + along * towards[axis] for axis in range(3))
            path.append(point)
            outward.append(tuple(value / radius for value in point))
        made.append(swept(path, outward, [towards] * STEPS, rib * 1.6, closed=True))
    return made


def oculus_ring(radius, oculus, rib):
    """The crown ring where the meridians end (the concept's top hatch): a wide rib round the skin's circle of radius
    `oculus`; one (points, quads) piece."""
    up = math.acos(min(oculus / radius, 1.0))
    arounds = [2 * math.pi * step / STEPS for step in range(STEPS)]
    outward = [unit(around, up) for around in arounds]
    return swept([tuple(radius * value for value in out) for out in outward], outward,
                 [(-math.sin(up) * math.cos(around), math.cos(up), -math.sin(up) * math.sin(around))
                  for around in arounds], rib * 2.0, True)


STRIP_WIDE, STRIP_THICK, STRIP_IN = 0.05, 0.025, 0.06  # a light strip's band, and how far inside the skin it hangs


def strips(radius, heights, openings=()):
    """A thin lamp band inside the skin, level at each of `heights` metres over the floor (the concept's glowing
    arcs), cut at the openings; (points, quads) pieces for the part `strip`."""
    made = []
    around_steps = STEPS * (FINE if openings else 1)
    for height in heights:
        up = math.asin(min(float(height) / radius, 0.99))
        arounds = [2 * math.pi * step / around_steps for step in range(around_steps)]
        inward = [tuple(-value for value in unit(around, up)) for around in arounds]
        path = [tuple((radius - STRIP_IN) * -value for value in inn) for inn in inward]
        side = [(-math.sin(up) * math.cos(around), math.cos(up), -math.sin(up) * math.sin(around)) for around in arounds]
        stretches = runs([tuple(radius * -value for value in inn) for inn in inward], openings)
        for stretch in stretches:
            closed = len(stretches) == 1 and len(stretch) == around_steps
            made.append(swept([path[index] for index in stretch], [inward[index] for index in stretch],
                              [side[index] for index in stretch], STRIP_WIDE, closed, STRIP_THICK))
    return made


def plinth(radius, openings=(), high=BASE_HIGH, wide=BASE_WIDE):
    """The base ring round the dome's foot: a rectangular section `wide` (mostly outside the skin) and `high`, cut at
    the openings; (points, quads) pieces, each a closed solid wound to face out (an engine draws a face from its front
    only, where Blender draws both)."""
    around_steps = STEPS * FINE
    inner, outer = radius - 0.25 * wide, radius + 0.75 * wide
    middles = [(radius * math.cos(2 * math.pi * step / around_steps), high / 2,
                radius * math.sin(2 * math.pi * step / around_steps)) for step in range(around_steps)]
    stretches = runs(middles, openings)
    whole = len(stretches) == 1 and len(stretches[0]) == around_steps
    made = []
    for stretch in stretches:
        points = []
        for index in stretch:
            angle = 2 * math.pi * index / around_steps
            for reach, high in ((inner, 0.0), (outer, 0.0), (outer, high), (inner, high)):
                points.append((reach * math.cos(angle), high, reach * math.sin(angle)))
        count = len(stretch)
        faces = []
        for step in range(count if whole else count - 1):
            here, there = 4 * step, 4 * ((step + 1) % count)
            for corner in range(4):
                following = (corner + 1) % 4
                faces.append([here + following, there + following, there + corner, here + corner])
        if not whole:
            faces += [[3, 2, 1, 0], [4 * (count - 1), 4 * (count - 1) + 1, 4 * (count - 1) + 2, 4 * (count - 1) + 3]]
        made.append((points, faces))
    return made


def face_normals(points, faces):
    """Each face's unit normal (Newell's, so an ear-clipped outline's triangles and a quad read alike) at each of its
    corners: the faceVarying normals of a flat-shaded mesh."""
    corners = np.asarray(points, dtype=float)
    found = []
    for face in faces:
        ring = corners[face]
        normal = np.cross(ring, np.roll(ring, -1, axis=0)).sum(axis=0)
        length = np.linalg.norm(normal)
        found += [tuple(map(float, normal / length if length > 1e-12 else (0.0, 1.0, 0.0)))] * len(face)
    return found


def written(path, root_name, pieces, flat=False):
    """`pieces` [(part name, (points, faces))] written at `path` as /<root_name> (y up, metres) with one mesh `geo`,
    each piece a named part bound to a placeholder material of its name (no shader: any USD reader splits the parts, as
    score-lib kit-parts binds a kit piece's, #156, and the library's surface goes over it); the path. `flat` writes each face's own normal at its corners (a box-built structure:
    with no normals a renderer shades it smooth, each box's faces bending to its corners, so a floor of slabs reads
    as pillowed tiles and a wall of columns as bright seams; owner, 2026-11-17)."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, f"/{root_name}")
    stage.SetDefaultPrim(root.GetPrim())
    points, faces, parts = [], [], {}
    for part, (piece_points, piece_faces) in pieces:
        offset, first = len(points), len(faces)
        points += piece_points
        faces += [[offset + index for index in face] for face in piece_faces]
        parts.setdefault(part, []).extend(range(first, len(faces)))
    mesh = UsdGeom.Mesh.Define(stage, f"/{root_name}/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*point) for point in points]))
    mesh.CreateFaceVertexCountsAttr([len(face) for face in faces])
    mesh.CreateFaceVertexIndicesAttr([index for face in faces for index in face])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(True)
    if flat:
        mesh.CreateNormalsAttr(Vt.Vec3fArray([Gf.Vec3f(*normal) for normal in face_normals(points, faces)]))
        mesh.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
    for part, part_faces in parts.items():
        subset = UsdGeom.Subset.CreateGeomSubset(mesh, part, UsdGeom.Tokens.face, part_faces, "materialBind",
                                                 UsdGeom.Tokens.nonOverlapping)
        placeholder = UsdShade.Material.Define(stage, f"/{root_name}/Looks/{part}")  # no shader: a part any reader
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(placeholder)       # splits; the library finishes it
    stage.GetRootLayer().Save()
    return path


def shell(path, radius, meridians=MERIDIANS, rings=RINGS, rib=RIB, openings=(), base_high=BASE_HIGH,
          base_wide=BASE_WIDE, oculus=0.0, strip_heights=()):
    """The dome written at `path`: /dome with its mesh `geo` and its parts `shell`, `ribs`, `deck` and `base` (and
    `strip` when it has light strips), cut at its `openings` (the module's rule); an `oculus` ring crowns it where the
    meridians end."""
    openings = [tuple(float(value) for value in opening) for opening in openings]
    return written(path, "dome", [("shell", skin(radius, openings)),
                                  *[("ribs", made) for made in ribs(radius, meridians, rings, rib, openings, oculus)],
                                  *[("ribs", made) for made in collars(radius, rib, openings)],
                                  *([("ribs", oculus_ring(radius, oculus, rib))] if oculus > 0 else []),
                                  *[("strip", made) for made in strips(radius, strip_heights, openings)],
                                  ("deck", disc(radius, DECK)),
                                  *[("base", made) for made in plinth(radius, openings, base_high, base_wide)]])


def disc_file(path, radius):
    """A laid ground's flat disc of `radius` written at `path`: /ground with its mesh `geo`, one part `ground`."""
    return written(path, "ground", [("ground", disc(radius))])


def in_trims(point, trims):
    """Whether `point` lies inside one of the spheres (x, y, z, radius) a tube is trimmed by (the domes it joins)."""
    return any(math.dist(point, trim[:3]) < trim[3] for trim in trims)


def onto_trims(point, trims, length):
    """`point` slid along the tube's axis out of any trim sphere it lies inside, onto that sphere's glass on the
    tube's side of it; (the point, whether it was moved)."""
    x, y, z = point
    for cx, cy, cz, reach in trims:
        if math.dist(point, (cx, cy, cz)) < reach:
            half = math.sqrt(max(reach * reach - (x - cx) ** 2 - (y - cy) ** 2, 0.0))
            return (x, y, cz + half if cz < length / 2 else cz - half), True
    return point, False


def tube_skin(radius, length, trims=()):
    """A level cylinder's skin along +z (its bottom on y = 0), rings about a metre apart (TRIM_RING apart when
    trimmed), faces wound outward; a point inside a trim sphere slid along the axis onto its glass and a face with
    every corner inside left out, so the tube ends on the dome's glass along a smooth edge instead of standing into
    the room or ending in steps."""
    count = max(1, math.ceil(length / (TRIM_RING if trims else 1.0)))
    steps = TUBE_STEPS
    ring = [(radius * math.cos(2 * math.pi * around / steps), radius + radius * math.sin(2 * math.pi * around / steps),
             length * along / count) for along in range(count + 1) for around in range(steps)]
    slid = [onto_trims(point, trims, length) for point in ring]
    points = [point for point, _ in slid]
    faces = [[along * steps + around, along * steps + (around + 1) % steps, (along + 1) * steps + (around + 1) % steps,
              (along + 1) * steps + around] for along in range(count) for around in range(steps)]
    faces = [face for face in faces if not all(slid[index][1] for index in face)]
    return points, faces


def tube_sides(radius, length, trims=()):
    """The tube's skin split at WALL_HIGH over its deck: (glass above, solid wall below), the corridor's lower walls
    solid as a habitat's are, so its glass starts above the knee."""
    points, faces = tube_skin(radius, length, trims)
    top = FLOOR * radius + WALL_HIGH
    low = [face for face in faces if sum(points[index][1] for index in face) / 4 < top]
    return (points, [face for face in faces if face not in low]), (points, low)


def hoop_ribs(radius, length, hoops, rib, trims=()):
    """The tunnel's ring ribs, `hoops` of them evenly from end to end (both ends included when two or more); trimmed,
    evenly over the stretch where the whole ring over the deck stands outside the trim spheres (a ring whose top only
    clears a dome's glass stands its sides inside the dome)."""
    made = []
    start, end = 0.0, length
    if trims:
        deck = FLOOR * radius
        ring = [(radius * math.cos(2 * math.pi * step / TUBE_STEPS),
                 radius + radius * math.sin(2 * math.pi * step / TUBE_STEPS)) for step in range(TUBE_STEPS)]
        ring = [(x, y) for x, y in ring if y >= deck]
        clear = [spot for spot in (length * step / 200 for step in range(201))
                 if not any(in_trims((x, y, spot), trims) for x, y in ring)]
        start, end = (min(clear), max(clear)) if clear else (0.0, length)
    spots = [(start + end) / 2.0] if hoops == 1 else [start + (end - start) * number / (hoops - 1)
                                                     for number in range(hoops)]
    arounds = [2 * math.pi * step / TUBE_STEPS for step in range(TUBE_STEPS)]
    outward = [(math.cos(around), math.sin(around), 0.0) for around in arounds]
    for spot in spots:
        spot = min(max(spot, rib / 2.0), length - rib / 2.0)
        made.append(swept([(radius * out[0], radius + radius * out[1], spot) for out in outward], outward,
                          [(0.0, 0.0, 1.0)] * TUBE_STEPS, rib, closed=True))
    return made


def tube_deck(radius, length):
    """The tunnel's floor: a flat strip FLOOR of its radius over its bottom, as wide as the skin there, faces up."""
    height = FLOOR * radius
    half = math.sqrt(max(radius ** 2 - (radius - height) ** 2, 0.0))
    return [(-half, height, 0.0), (half, height, 0.0), (half, height, length), (-half, height, length)], [[0, 3, 2, 1]]


def on_circle(x, y, radius):
    """An end wall's corner (x, y) drawn in to the tube's circle (centre (0, radius)) when it lies outside it."""
    off = math.hypot(x, y - radius)
    return (x, y) if off <= radius else (x * radius / off, radius + (y - radius) * radius / off)


def doorway_outline(cap):
    """A doorway's outline, anticlockwise (x across from the tunnel's axis, y up from its deck): `cap` as [width,
    height] (a rectangle) or as the door's own outline, its points in order round it (an octagonal hatch's octagon)."""
    cap = [cap] if np.ndim(cap) == 1 and len(cap) == 2 and np.ndim(cap[0]) == 0 else cap
    if len(cap) == 1:
        width, height = float(cap[0][0]), float(cap[0][1])
        return np.array([(-width / 2, 0.0), (width / 2, 0.0), (width / 2, height), (-width / 2, height)])
    points = np.asarray(cap, dtype=np.float64)
    following = np.roll(points, -1, axis=0)
    area = float(np.sum(points[:, 0] * following[:, 1] - following[:, 0] * points[:, 1]))
    return points if area > 0 else points[::-1]


def inside_outline(outline, x, y):
    """Whether (x, y) lies inside the outline (a ray to its right crosses its edges an odd number of times)."""
    following = np.roll(outline, -1, axis=0)
    spans = (outline[:, 1] > y) != (following[:, 1] > y)
    with np.errstate(divide="ignore", invalid="ignore"):
        crossing = outline[:, 0] + (y - outline[:, 1]) * (following[:, 0] - outline[:, 0]) \
            / (following[:, 1] - outline[:, 1])
    return bool(np.count_nonzero(spans & (crossing > x)) % 2)


def onto_outline(outline, x, y):
    """A corner inside the doorway moved out to the nearest point of its outline, so the wall's edge follows the door's
    shape, never stepped; a corner outside it kept."""
    if not inside_outline(outline, x, y):
        return x, y
    following = np.roll(outline, -1, axis=0)
    edges = following - outline
    along = np.clip(((x - outline[:, 0]) * edges[:, 0] + (y - outline[:, 1]) * edges[:, 1])
                    / np.maximum((edges ** 2).sum(axis=1), 1e-12), 0.0, 1.0)
    nearest = outline + edges * along[:, None]
    best = int(np.argmin(np.hypot(nearest[:, 0] - x, nearest[:, 1] - y)))
    return float(nearest[best, 0]), float(nearest[best, 1])


def end_wall(radius, length, cap):
    """The tunnel's far end closed by a wall CAP_THICK thick (its outer face at `length`) holding a doorway of the
    door's own shape (`cap`: [width, height], or the door's outline points; doorway_outline) up from the deck: its
    front and back faces in CAP_CELL cells inside the skin and outside the doorway, a cell the skin crosses drawn in to
    the skin's circle and one the doorway crosses out to its outline (so both rims follow their shapes, never
    stepped), and a reveal along each edge of the doorway off the deck; (points, quads)."""
    floor = FLOOR * radius
    outline = doorway_outline(cap) + [0.0, floor]
    def lines(low, high, edges):
        count = max(1, round((high - low) / CAP_CELL))
        return sorted(set([low + (high - low) * step / count for step in range(count + 1)] + list(edges)))
    across = lines(-radius, radius, outline[:, 0])
    up = lines(floor, 2 * radius, outline[:, 1])
    points, faces = [], []
    for depth, wound in ((length, False), (length - CAP_THICK, True)):
        for left, right in zip(across, across[1:]):
            for low, high in zip(up, up[1:]):
                middle = ((left + right) / 2, (low + high) / 2)
                corners = [(left, low), (right, low), (right, high), (left, high)]
                if all(math.hypot(x, y - radius) >= radius for x, y in corners) or inside_outline(outline, *middle):
                    continue
                first = len(points)
                points += [(*on_circle(*onto_outline(outline, x, y), radius), depth) for x, y in corners]
                quad = [first, first + 1, first + 2, first + 3]
                faces.append(quad[::-1] if wound else quad)
    for (x0, y0), (x1, y1) in zip(outline, np.roll(outline, -1, axis=0)):
        if max(y0, y1) <= floor + 1e-6:
            continue
        first = len(points)
        points += [(x1, y1, length), (x0, y0, length), (x0, y0, length - CAP_THICK), (x1, y1, length - CAP_THICK)]
        faces.append([first, first + 1, first + 2, first + 3])
    return points, faces


def tube(path, radius, length, hoops=HOOPS, rib=RIB, cap=None, trims=()):
    """The tunnel written at `path`: /tube with its mesh `geo` and its parts `shell`, `ribs` and `deck`, and `cap`
    (its end wall with a doorway, `cap` = (width, height) or the door's outline points, end_wall) when asked; its skin
    and hoops trimmed by `trims` (the spheres, x, y, z, radius in its own frame, of the domes it joins)."""
    trims = [tuple(float(value) for value in trim) for trim in trims]
    glass, wall = tube_sides(radius, length, trims)
    pieces = [("shell", glass), ("wall", wall),
              *[("ribs", made) for made in hoop_ribs(radius, length, hoops, rib, trims)],
              ("deck", tube_deck(radius, length))]
    if cap:
        pieces.append(("cap", end_wall(radius, length, cap)))
    return written(path, "tube", pieces)


def chamfered_box(low, high, bevel=BEVEL):
    """A closed box from `low` to `high` (x, y, z) with every edge chamfered `bevel` metres (at most a third of its
    thinnest side): its points and triangles, wound to face out."""
    from scipy.spatial import ConvexHull
    low, high = np.asarray(low, dtype=np.float64), np.asarray(high, dtype=np.float64)
    if np.any(high - low <= 0):
        raise ValueError(f"a block needs its high corner past its low one ({low.tolist()}, {high.tolist()})")
    cut = min(float(bevel), float((high - low).min()) / 3)
    middle, half = (low + high) / 2, (high - low) / 2
    points = []
    for signs in np.array([[sx, sy, sz] for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)], dtype=np.float64):
        for axis in range(3):
            inset = half - cut
            inset[axis] = half[axis]
            points.append(middle + signs * inset)
    points = np.unique(np.round(np.array(points), 9), axis=0)
    hull = ConvexHull(points)
    triangles = []
    for simplex, plane in zip(hull.simplices, hull.equations):
        first, second, third = points[simplex]
        if np.dot(np.cross(second - first, third - first), plane[:3]) < 0:
            simplex = simplex[[0, 2, 1]]
        triangles.append([int(index) for index in simplex])
    return [tuple(point) for point in points.tolist()], triangles


def blocks_file(path, boxes, bevel=BEVEL):
    """Solid chamfered boxes written at `path`: /blocks with one mesh `geo`, each box (x0, y0, z0, x1, y1, z1, part)
    a closed solid in its part (the module's rule)."""
    pieces = []
    for box in boxes:
        if len(box) != 7:
            raise ValueError(f"a block is x0, y0, z0, x1, y1, z1, part ({box})")
        pieces.append((str(box[6]), chamfered_box(box[:3], box[3:6], bevel)))
    return written(path, "blocks", pieces)
