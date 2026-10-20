"""An item's stage for its clip: the library's own stage for it (its plan row's `open`) under the sample shapes its
shelf is shown on, written as layers only (pxr's Sdf: nothing is composed or resolved on this PC).

    surface  a ball of BALL metres across standing on the ground, its material the surface's
    sky      a sample room (a floor's corner of two walls, a block and a ball) on the films' ground at y = 0, the sky
             lighting it
    lamp     a room round the lamps' spots (its floor `Ground` LAMP_DROP under the lowest lamp, two walls behind
             them), the lamps lighting it
    others   nothing added: the item stands on the films' ground as it is
"""
import math
import pathlib

ROOT = "Sample"
BALL = 1.0
ROOM = 6.0  # metres: the sky's sample room's floor side and wall height
WALL = 0.2
LAMP_DROP = 2.6  # metres from the lowest lamp to the room's floor
LAMP_MARGIN = 1.5  # metres the lamps' room reaches past its outermost lamps
RINGS, SEGMENTS = 24, 48


def ball(centre, radius):
    """(points, counts, indices, normals) of a UV sphere."""
    points, normals = [], []
    for ring in range(RINGS + 1):
        down = math.pi * ring / RINGS
        for segment in range(SEGMENTS):
            round_ = 2 * math.pi * segment / SEGMENTS
            normal = (math.sin(down) * math.cos(round_), math.cos(down), math.sin(down) * math.sin(round_))
            normals.append(normal)
            points.append(tuple(c + radius * n for c, n in zip(centre, normal)))
    counts, indices = [], []
    for ring in range(RINGS):
        for segment in range(SEGMENTS):
            here, right = ring * SEGMENTS + segment, ring * SEGMENTS + (segment + 1) % SEGMENTS
            counts.append(4)
            indices += [here, right, right + SEGMENTS, here + SEGMENTS]
    return points, counts, indices, normals


def box(low, high):
    """(points, counts, indices, None) of a box between two corners, its faces outward."""
    points = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return points, [4] * 6, [index for face in faces for index in face], None


def mesh(layer, path, shape, material=None):
    """A Mesh prim spec in `layer` from a shape (points, counts, indices, normals), bound to `material` when given."""
    from pxr import Sdf, Vt, Gf
    points, counts, indices, normals = shape
    spec = Sdf.CreatePrimInLayer(layer, path)
    spec.specifier, spec.typeName = Sdf.SpecifierDef, "Mesh"
    values = [("points", Sdf.ValueTypeNames.Point3fArray, Vt.Vec3fArray([Gf.Vec3f(*point) for point in points])),
              ("faceVertexCounts", Sdf.ValueTypeNames.IntArray, Vt.IntArray(counts)),
              ("faceVertexIndices", Sdf.ValueTypeNames.IntArray, Vt.IntArray(indices))]
    if normals:
        values.append(("normals", Sdf.ValueTypeNames.Normal3fArray,
                       Vt.Vec3fArray([Gf.Vec3f(*normal) for normal in normals])))
    for name, kind, value in values:
        Sdf.AttributeSpec(spec, name, kind).default = value
    if normals:
        spec.attributes["normals"].SetInfo("interpolation", "vertex")
    if material:
        spec.SetInfo("apiSchemas", Sdf.TokenListOp.CreateExplicit(["MaterialBindingAPI"]))
        Sdf.RelationshipSpec(spec, "material:binding").targetPathList.explicitItems = [material]


def sky_room(layer):
    """The sky's sample room (module docstring)."""
    half = ROOM / 2
    mesh(layer, f"/{ROOT}/BackWall", box((-half, 0, -half - WALL), (half, ROOM, -half)))
    mesh(layer, f"/{ROOT}/SideWall", box((-half - WALL, 0, -half), (-half, ROOM, half)))
    mesh(layer, f"/{ROOT}/Block", box((-1.5, 0, -1.5), (-0.5, 1.0, -0.5)))
    mesh(layer, f"/{ROOT}/Ball", ball((1.0, BALL / 2, 0.5), BALL / 2))


def lamp_room(layer, points):
    """The lamps' room (module docstring)."""
    low = [min(point[axis] for point in points) - LAMP_MARGIN for axis in range(3)]
    high = [max(point[axis] for point in points) + LAMP_MARGIN for axis in range(3)]
    floor = min(point[1] for point in points) - LAMP_DROP
    top = max(point[1] for point in points) + 0.5
    mesh(layer, f"/{ROOT}/Ground", box((low[0], floor - WALL, low[2]), (high[0], floor, high[2])))
    mesh(layer, f"/{ROOT}/BackWall", box((low[0], floor, low[2] - WALL), (high[0], top, low[2])))
    mesh(layer, f"/{ROOT}/SideWall", box((low[0] - WALL, floor, low[2]), (low[0], top, high[2])))
    mesh(layer, f"/{ROOT}/Ball", ball(((low[0] + high[0]) / 2, floor + BALL / 2, (low[2] + high[2]) / 2), BALL / 2))


def focus(shelf):
    """The prims a shelf's clip frames when its sample shapes are what it shows (a sky's dome would frame the sky,
    not the room it lights), or None: what the library's plan says."""
    return [f"/{ROOT}"] if shelf in ("surface", "sky", "lamp") else None


def default_prim(opened):
    """The default prim of the first layer the library's stage opens (its entry's own), or ROOT."""
    from pxr import Sdf
    layer = Sdf.Layer.FindOrOpen(str(opened))
    first = Sdf.Layer.FindOrOpen(layer.subLayerPaths[0]) if layer and layer.subLayerPaths else None
    return (first.defaultPrim if first else "") or ROOT


def item_stage(folder, row):
    """item.usda in `folder`: the shelf's sample shapes over the library's stage (row["open"]); its path."""
    from pxr import Sdf
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "item.usda"
    layer = Sdf.Layer.CreateNew(str(path))
    layer.subLayerPaths.append(row["open"])
    root = Sdf.CreatePrimInLayer(layer, f"/{ROOT}")
    root.specifier, root.typeName = Sdf.SpecifierDef, "Xform"
    if row["shelf"] == "surface":
        mesh(layer, f"/{ROOT}/Ball", ball((0.0, BALL / 2, 0.0), BALL / 2), row["material"])
    elif row["shelf"] == "sky":
        sky_room(layer)
    elif row["shelf"] == "lamp" and row["points"]:
        lamp_room(layer, row["points"])
    layer.defaultPrim = default_prim(row["open"])
    layer.Save()
    return path
