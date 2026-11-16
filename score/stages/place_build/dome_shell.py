"""The dome shell algorithm (#128, the camp pilot: the kits hold no large ribbed glass dome, only straight ribs): a
hemisphere of `radius` metres standing on y = 0, one mesh `geo` with two named parts, `shell` (the thin glass skin,
one surface, faces outward) and `ribs` (curved square-section ribs over it: `meridians` from the ground to the top
and `rings` level rings between), so the placing agent wears each part its own library surface
(place_build.surface --part shell surface/clear_glass, --part ribs a metal).

A third part, `deck`, is the dome's floor: a flat disc of its radius DECK over y = 0, faces up. The same disc alone, of any
radius, is a laid ground (`disc_file`, place_build.ground), so a regolith or concrete surface has a ground to lie on
with no kit piece's stylised terrain under it.

    shell(path, radius, meridians=MERIDIANS, rings=RINGS, rib=RIB)   the dome written as a USD file at `path`
    disc_file(path, radius)                                          a flat ground disc written at `path`
    tube(path, radius, length, hoops=HOOPS, rib=RIB)                 a ribbed glass tunnel written at `path`

The tunnel between two domes (the concept's ribbed glass tube) is the same skin and ribs round a level axis: a
cylinder of `radius` lying along +z from 0 to `length`, its bottom on y = 0, `hoops` ring ribs evenly along it and
a flat deck (its floor) FLOOR of its radius up, parts `shell`, `ribs` and `deck`.
"""
import math

from pxr import Gf, Usd, UsdGeom, Vt

MERIDIANS = 12  # ribs from the ground to the top
RINGS = 3  # level ribs between the ground and the top, evenly by angle
RIB = 0.12  # a rib's square section, metres
DECK = 0.02  # the deck's height over y = 0, so it never fights a ground laid under the dome
HOOPS = 5  # ring ribs along a tunnel
FLOOR = 0.3  # a tunnel's deck height over its bottom, in its radius
STEPS = 48  # points around the dome and along each rib (a quarter arc takes STEPS // 4)


def unit(angle_around, angle_up):
    """The outward unit vector at `angle_around` about up and `angle_up` over the ground (radians)."""
    return (math.cos(angle_up) * math.cos(angle_around), math.sin(angle_up), math.cos(angle_up) * math.sin(angle_around))


def skin(radius):
    """The hemisphere's points and quads (and the top's triangles), faces wound outward."""
    up_steps = STEPS // 4
    points = [tuple(radius * value for value in unit(2 * math.pi * around / STEPS, math.pi / 2 * up / up_steps))
              for up in range(up_steps) for around in range(STEPS)]
    points.append((0.0, radius, 0.0))
    faces = []
    for up in range(up_steps - 1):
        for around in range(STEPS):
            following = (around + 1) % STEPS
            faces.append([up * STEPS + around, (up + 1) * STEPS + around, (up + 1) * STEPS + following,
                          up * STEPS + following])
    top = len(points) - 1
    faces += [[(up_steps - 1) * STEPS + around, top, (up_steps - 1) * STEPS + (around + 1) % STEPS]
              for around in range(STEPS)]
    return points, faces


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


def swept(path, outward, side, rib, closed):
    """A square-section rib along `path`: at each point its section stands outward from the skin by `rib` and spans
    `rib` along `side`; (points, quads), open at its ends unless `closed`."""
    points = []
    for at, out, across in zip(path, outward, side):
        for along, lift in ((-0.5, 0.0), (0.5, 0.0), (0.5, 1.0), (-0.5, 1.0)):
            points.append(tuple(at[axis] + across[axis] * along * rib + out[axis] * lift * rib for axis in range(3)))
    faces = []
    count = len(path)
    for step in range(count if closed else count - 1):
        here, there = 4 * step, 4 * ((step + 1) % count)
        for corner in range(4):
            following = (corner + 1) % 4
            faces.append([here + corner, here + following, there + following, there + corner])
    return points, faces


def ribs(radius, meridians, rings, rib):
    """Every rib of the dome as (points, quads): the meridians ground to top, the rings level between."""
    made = []
    up_steps = STEPS // 4
    for number in range(meridians):
        around = 2 * math.pi * number / meridians
        ups = [math.pi / 2 * step / up_steps for step in range(up_steps + 1)]
        outward = [unit(around, up) for up in ups]
        made.append(swept([tuple(radius * value for value in out) for out in outward], outward,
                          [(-math.sin(around), 0.0, math.cos(around))] * len(ups), rib, closed=False))
    for number in range(1, rings + 1):
        up = math.pi / 2 * number / (rings + 1)
        arounds = [2 * math.pi * step / STEPS for step in range(STEPS)]
        outward = [unit(around, up) for around in arounds]
        made.append(swept([tuple(radius * value for value in out) for out in outward], outward,
                          [(-math.sin(up) * math.cos(around), math.cos(up), -math.sin(up) * math.sin(around))
                           for around in arounds], rib, closed=True))
    return made


def written(path, root_name, pieces):
    """`pieces` [(part name, (points, faces))] written at `path` as /<root_name> (y up, metres) with one mesh `geo`,
    each piece a named part; the path."""
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
    for part, part_faces in parts.items():
        UsdGeom.Subset.CreateGeomSubset(mesh, part, UsdGeom.Tokens.face, part_faces, "materialBind",
                                        UsdGeom.Tokens.nonOverlapping)
    stage.GetRootLayer().Save()
    return path


def shell(path, radius, meridians=MERIDIANS, rings=RINGS, rib=RIB):
    """The dome written at `path`: /dome with its mesh `geo` and its parts `shell`, `ribs` and `deck`."""
    return written(path, "dome", [("shell", skin(radius)),
                                  *[("ribs", made) for made in ribs(radius, meridians, rings, rib)],
                                  ("deck", disc(radius, DECK))])


def disc_file(path, radius):
    """A laid ground's flat disc of `radius` written at `path`: /ground with its mesh `geo`, one part `ground`."""
    return written(path, "ground", [("ground", disc(radius))])


def tube_skin(radius, length):
    """A level cylinder's skin along +z (its bottom on y = 0), rings about a metre apart, faces wound outward."""
    count = max(1, math.ceil(length))
    points = [(radius * math.cos(2 * math.pi * around / STEPS), radius + radius * math.sin(2 * math.pi * around / STEPS),
               length * along / count) for along in range(count + 1) for around in range(STEPS)]
    faces = [[along * STEPS + around, along * STEPS + (around + 1) % STEPS, (along + 1) * STEPS + (around + 1) % STEPS,
              (along + 1) * STEPS + around] for along in range(count) for around in range(STEPS)]
    return points, faces


def hoop_ribs(radius, length, hoops, rib):
    """The tunnel's ring ribs, `hoops` of them evenly from end to end (both ends included when two or more)."""
    made = []
    spots = [length / 2.0] if hoops == 1 else [length * number / (hoops - 1) for number in range(hoops)]
    arounds = [2 * math.pi * step / STEPS for step in range(STEPS)]
    outward = [(math.cos(around), math.sin(around), 0.0) for around in arounds]
    for spot in spots:
        spot = min(max(spot, rib / 2.0), length - rib / 2.0)
        made.append(swept([(radius * out[0], radius + radius * out[1], spot) for out in outward], outward,
                          [(0.0, 0.0, 1.0)] * STEPS, rib, closed=True))
    return made


def tube_deck(radius, length):
    """The tunnel's floor: a flat strip FLOOR of its radius over its bottom, as wide as the skin there, faces up."""
    height = FLOOR * radius
    half = math.sqrt(max(radius ** 2 - (radius - height) ** 2, 0.0))
    return [(-half, height, 0.0), (half, height, 0.0), (half, height, length), (-half, height, length)], [[0, 3, 2, 1]]


def tube(path, radius, length, hoops=HOOPS, rib=RIB):
    """The tunnel written at `path`: /tube with its mesh `geo` and its parts `shell`, `ribs` and `deck`."""
    return written(path, "tube", [("shell", tube_skin(radius, length)),
                                  *[("ribs", made) for made in hoop_ribs(radius, length, hoops, rib)],
                                  ("deck", tube_deck(radius, length))])
