"""The dome shell algorithm (#128, the camp pilot: the kits hold no large ribbed glass dome, only straight ribs): a
hemisphere of `radius` metres standing on y = 0, one mesh `geo` with two named parts, `shell` (the thin glass skin,
one surface, faces outward) and `ribs` (curved square-section ribs over it: `meridians` from the ground to the top
and `rings` level rings between), so the placing agent wears each part its own library surface
(place_build.surface --part shell surface/clear_glass, --part ribs a metal).

    shell(path, radius, meridians=MERIDIANS, rings=RINGS, rib=RIB)   the dome written as a USD file at `path`
"""
import math

from pxr import Gf, Usd, UsdGeom, Vt

MERIDIANS = 12  # ribs from the ground to the top
RINGS = 3  # level ribs between the ground and the top, evenly by angle
RIB = 0.12  # a rib's square section, metres
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


def shell(path, radius, meridians=MERIDIANS, rings=RINGS, rib=RIB):
    """The dome written at `path`: /dome (y up, metres) with its mesh `geo` and its parts `shell` and `ribs`."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/dome")
    stage.SetDefaultPrim(root.GetPrim())
    points, faces = skin(radius)
    shell_faces = list(range(len(faces)))
    for rib_points, rib_faces in ribs(radius, meridians, rings, rib):
        offset = len(points)
        points += rib_points
        faces += [[offset + index for index in face] for face in rib_faces]
    mesh = UsdGeom.Mesh.Define(stage, "/dome/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*point) for point in points]))
    mesh.CreateFaceVertexCountsAttr([len(face) for face in faces])
    mesh.CreateFaceVertexIndicesAttr([index for face in faces for index in face])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(True)
    binding = UsdGeom.Subset.CreateGeomSubset
    binding(mesh, "shell", UsdGeom.Tokens.face, shell_faces, "materialBind", UsdGeom.Tokens.nonOverlapping)
    binding(mesh, "ribs", UsdGeom.Tokens.face, list(range(len(shell_faces), len(faces))), "materialBind",
            UsdGeom.Tokens.nonOverlapping)
    stage.GetRootLayer().Save()
    return path
