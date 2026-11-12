"""A floor thing standing on one thin post whose footing no cut holds stood upright on a round plate under its post's
foot that holds its weight by the resting check's own measure, in the place's own copy of its baked asset
(even_feet.level_asset, before big_bases.levelled): its post turned upright about its foot, the model lifted by the
plate's thickness, the plate's faces joined to the drawn mesh in its post's own part (its library surface and
finish), each of its points given the post foot's texture place.

square, 2026-11-12 (the make as laid.py lays it, the resting triage as laid): its 41 red flags, one Pixal3D model
0.42 x 0.53 x 0.11 m, stood on a pole 1.5 cm wide at its foot leaning 10 degrees, its cloth 0.42 m to one side; the
triage weighs a model by its surface area, so its weight lay 0.18 m outside the pole's foot, and no cut, turn or level
of the model moves it (38994f50). A flag stand's plate does.

    based(root, scale)        [the post's turn in degrees, the plate's radius in metres] for the asset's root prim
                              whose drawn mesh (`geo`, at `scale`: the size it is laid at, per axis) stands on a thin
                              post (post_foot) that does not hold it, the post a part of its own (the GeomSubset
                              holding its lowest point, not the whole mesh) standing within LEAN_MOST of upright
                              (standing_post), its mesh given the stood post and the plate; [] and nothing changed
                              otherwise (greenhouse's pipe, one part 3 m long touching at one narrow spot, is no post)
    post_foot(points)         the (x, z) of a model's foot when it is one thin post (its points within FOOT_BAND of
                              its lowest no wider than POST across, the model at least SPREAD times as wide), else None
    stood(points, post)       the points turned about the post's foot so the post's long axis (`post`: its points)
                              stands up, its foot where it was; and the turn (3 x 3)
    plate(foot, low, radius)  (points, triangles, normals) of a round plate THICK thick, SEGMENTS sides, its sole at
                              `low`, centred under `foot`
"""
import numpy as np

# The widest a model's foot is across, metres, to be read as one thin post.
POST = 0.05
# How far over its lowest point a model's foot is read, metres.
FOOT_BAND = 0.05
# How many times wider than its foot a model is, at least, to stand on a post (a bare post holds itself or not).
SPREAD = 3.0
# A post leaned less than this, degrees, is left as made.
LEAN_LEAST = 1.0
# The most a post leans, degrees, to be stood upright: past it the part is no post (a pipe lying on its bend).
LEAN_MOST = 20.0
# The share of its longest reach a post's other reaches stay under: one slender part (thin_straight's slender rule).
SLENDER = 0.25
# The plate: its thickness, sides, the radii tried (metres apart) and the largest, a share of the model's height.
THICK = 0.01
SEGMENTS = 32
RADIUS_STEP = 0.01
RADIUS_MOST = 0.5


def based(root, scale):
    """The model at `root` (an asset's default prim) stood upright on a plate under its post (module docstring),
    written into its drawn mesh on the open stage; what was done ([] and nothing written when nothing was)."""
    from pxr import UsdGeom
    from score.stages.assembly import big_bases, footing
    mesh = UsdGeom.Mesh(root.GetChild("geo"))
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get())
    if not len(counts) or np.any(counts != 3):
        return []
    scale = np.asarray(scale, dtype=np.float64)
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64) * scale
    triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    foot = post_foot(points)
    if foot is None:
        return []
    part = post_part(mesh, triangles, points)
    if part is None or len(part) == len(triangles) or not standing_post(points[np.unique(triangles[part])]):
        return []
    if footing.needed_cut(points, triangles) is not None:
        return []
    turned, turn = stood(points, points[np.unique(triangles[part])])
    turned = turned + (0.0, THICK, 0.0)
    low = float(points[:, 1].min())
    height = float(np.ptp(turned[:, 1]))
    for radius in np.arange(max(POST, RADIUS_STEP), RADIUS_MOST * height + RADIUS_STEP / 2, RADIUS_STEP):
        added, faces, normals = plate(foot, low, float(radius))  # stood keeps the foot where it was
        if big_bases.holds_as_made(np.vstack([turned, added]), np.vstack([triangles, faces + len(turned)])):
            joined(mesh, part, turned / scale, turn, scale, (added / scale, faces, normals))
            lean = float(np.degrees(np.arccos(np.clip(turn[1, 1], -1.0, 1.0))))
            return [round(lean, 2), round(float(radius), 3)]
    return []


def post_foot(points):
    """The (x, z) middle of a model's foot when it stands on one thin post (module docstring), else None."""
    points = np.asarray(points, dtype=np.float64)
    foot = points[points[:, 1] <= points[:, 1].min() + FOOT_BAND][:, [0, 2]]
    across = float(np.ptp(foot, axis=0).max())
    wide = float(np.ptp(points[:, [0, 2]], axis=0).max())
    if across > POST or wide < SPREAD * max(across, 1e-9):
        return None
    return (foot.min(axis=0) + foot.max(axis=0)) / 2


def post_part(mesh, triangles, points):
    """The face indices of the drawn mesh's part (GeomSubset) holding its lowest point, None without parts."""
    from pxr import UsdGeom
    lowest = int(np.argmin(points[:, 1]))
    holding = set(np.nonzero(np.any(triangles == lowest, axis=1))[0].tolist())
    for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh):
        indices = np.asarray(subset.GetIndicesAttr().Get())
        if holding & set(indices.tolist()):
            return indices
    return None


def standing_post(points):
    """Whether a part's points lie along one slender part (its oriented box's other reaches under SLENDER of its
    longest) standing within LEAN_MOST of upright: a post, never a pipe lying on its bend."""
    from score.stages.surfaces import tumble
    axes, extents, _ = tumble.oriented(points)
    _, middle, largest = sorted(extents)
    up = abs(float(axes[1, int(np.argmax(extents))]))
    return largest > 0 and middle <= SLENDER * largest and np.degrees(np.arccos(min(up, 1.0))) <= LEAN_MOST


def stood(points, post):
    """(the points turned about the post's foot so its long axis stands up, its foot where it was; the turn, 3 x 3);
    the points as made and no turn when it leans under LEAN_LEAST."""
    from score.stages.assembly import big_bases
    from score.stages.surfaces import tumble
    axes, extents, _ = tumble.oriented(post)
    up = axes[:, int(np.argmax(extents))]
    up = up * np.sign(up[1])
    if np.degrees(np.arccos(np.clip(up[1], -1.0, 1.0))) < LEAN_LEAST:
        return np.asarray(points, dtype=np.float64), np.eye(3)
    turn = big_bases.turned_onto(up / np.linalg.norm(up), np.array([0.0, 1.0, 0.0]))
    low = float(points[:, 1].min())
    foot = post_foot(points)
    pivot = np.array([foot[0], low, foot[1]])
    turned = (points - pivot) @ turn.T + pivot
    after = post_foot(turned)
    after = foot if after is None else after
    return turned + (foot[0] - after[0], low - turned[:, 1].min(), foot[1] - after[1]), turn


def plate(foot, low, radius):
    """(points, triangles, normals) of a round plate (module docstring): its top and sole each a fan round its middle,
    its rim a band, each with its own points so each face has its own normal."""
    angles = np.linspace(0.0, 2 * np.pi, SEGMENTS, endpoint=False)
    ring = np.c_[foot[0] + radius * np.cos(angles), np.zeros(SEGMENTS), foot[1] + radius * np.sin(angles)]
    outward = np.c_[np.cos(angles), np.zeros(SEGMENTS), np.sin(angles)]
    top, sole = ring + (0.0, low + THICK, 0.0), ring + (0.0, low, 0.0)
    middle = np.array([[foot[0], 0.0, foot[1]]])
    points = np.vstack([middle + (0.0, low + THICK, 0.0), top, middle + (0.0, low, 0.0), sole, top, sole])
    normals = np.vstack([np.tile((0.0, 1.0, 0.0), (SEGMENTS + 1, 1)), np.tile((0.0, -1.0, 0.0), (SEGMENTS + 1, 1)),
                         outward, outward])
    following = (np.arange(SEGMENTS) + 1) % SEGMENTS
    around = np.arange(SEGMENTS)
    upper = np.c_[np.zeros(SEGMENTS), 1 + following, 1 + around]
    lower = np.c_[np.full(SEGMENTS, SEGMENTS + 1), SEGMENTS + 2 + around, SEGMENTS + 2 + following]
    rim_top, rim_sole = 2 * SEGMENTS + 2, 3 * SEGMENTS + 2
    rim = np.vstack([np.c_[rim_top + around, rim_top + following, rim_sole + around],
                     np.c_[rim_top + following, rim_sole + following, rim_sole + around]])
    return points, np.vstack([upper, lower, rim]).astype(np.int64), normals


def joined(mesh, part, points, turn, scale, added):
    """The drawn mesh written as stood (`points`, in its own units) with the plate (`added`: its points in its own
    units, triangles, normals) joined: in the post's part (`part`), each primvar of its points and faces carried to
    the plate as the post's foot has it, its normals turned with it."""
    from pxr import Gf, UsdGeom, Vt
    plate_points, faces, normals = added
    before = len(points)
    foot = int(np.argmin(points[:, 1]))
    triangles = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    every = np.vstack([points, plate_points]).astype(np.float32)
    mesh.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(every))
    mesh.GetFaceVertexCountsAttr().Set(Vt.IntArray.FromNumpy(np.full(len(triangles) + len(faces), 3, dtype=np.int32)))
    mesh.GetFaceVertexIndicesAttr().Set(Vt.IntArray.FromNumpy(
        np.vstack([triangles, faces + before]).reshape(-1).astype(np.int32)))
    mesh.GetExtentAttr().Set([Gf.Vec3f(*every.min(axis=0).tolist()), Gf.Vec3f(*every.max(axis=0).tolist())])
    made = mesh.GetNormalsAttr().Get()
    if made is not None and len(made) == before:
        bend = np.diag(1.0 / scale) @ turn @ np.diag(scale)  # a normal's turn: the inverse transpose of the points'
        turned = np.asarray(made, dtype=np.float64) @ np.linalg.inv(bend)
        turned /= np.maximum(np.linalg.norm(turned, axis=1, keepdims=True), 1e-12)
        normals = normals * scale  # a plate normal at the model's own units
        normals /= np.linalg.norm(normals, axis=1, keepdims=True)
        mesh.GetNormalsAttr().Set(Vt.Vec3fArray.FromNumpy(np.vstack([turned, normals]).astype(np.float32)))
    sizes = {UsdGeom.Tokens.vertex: len(plate_points), UsdGeom.Tokens.varying: len(plate_points),
             UsdGeom.Tokens.faceVarying: 3 * len(faces), UsdGeom.Tokens.uniform: len(faces)}
    corner = {UsdGeom.Tokens.vertex: foot, UsdGeom.Tokens.varying: foot,
              UsdGeom.Tokens.faceVarying: 3 * int(np.nonzero(np.any(triangles == foot, axis=1))[0][0])
              + int(np.nonzero(triangles[np.any(triangles == foot, axis=1)][0] == foot)[0][0]),
              UsdGeom.Tokens.uniform: int(np.nonzero(np.any(triangles == foot, axis=1))[0][0])}
    for primvar in UsdGeom.PrimvarsAPI(mesh.GetPrim()).GetPrimvars():
        kind = primvar.GetInterpolation()
        if kind not in sizes or primvar.Get() is None:
            continue
        carried(primvar, corner[kind], sizes[kind])
    if part is not None:
        for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh):
            indices = np.asarray(subset.GetIndicesAttr().Get())
            if len(indices) == len(part) and np.array_equal(indices, part):
                subset.GetIndicesAttr().Set(Vt.IntArray.FromNumpy(
                    np.concatenate([part, len(triangles) + np.arange(len(faces))]).astype(np.int32)))


def carried(primvar, at, count):
    """A primvar given `count` more elements, each its element `at` (an indexed one its index there)."""
    if primvar.IsIndexed():
        indices = np.asarray(primvar.GetIndices())
        primvar.SetIndices(type(primvar.GetIndices())(list(indices) + [int(indices[at])] * count))
        return
    values = primvar.Get()
    primvar.Set(type(values)(list(values) + [values[at]] * count))
