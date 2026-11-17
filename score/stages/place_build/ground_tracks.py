"""The ground tracks algorithm (library entry algorithm/ground_tracks, #128): a rover's wheel ruts and boot prints
pressed into a loose ground along the routes people and machines take, as one thin mesh laid over the ground (a
decal of relief, no solid of its own).

    tracks_file(target, rover, boots, height_at, seed)

`rover` is a list of polylines ([[x, z], ...]) a rover drove: each gets two ruts GAUGE apart, RUT_WIDE across, their
floors pressed a little and ridged across by the tyres' tread every TREAD metres, a berm of pushed-up ground either
side. `boots` is a list of polylines people walked: a print every STRIDE metres, left and right of the line by turns.
`height_at(xs, zs)` is the laid ground's height at each spot (arrays in, an array out); every point stands LIFT over it so the ground never shows through.
Two parts, `ruts` and `prints`, each a mesh for its own surface.
"""
import math

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

GAUGE = 1.9  # metres between a rover's two wheel tracks (a crewed rover's track width, the LRV's 1.83 m)
RUT_WIDE = 0.32  # metres across one rut
BERM_WIDE = 0.12  # metres of pushed-up ground beside a rut
BERM_HIGH = 0.022  # metres a berm stands over the ground
RUT_LOW = 0.004  # metres the rut floor stands over the ground (the pressed floor reads by its colour and its berms)
TREAD = 0.14  # metres between tread ridges across a rut
TREAD_HIGH = 0.008  # metres a tread ridge stands over the rut floor
STEP = 0.07  # metres along a rut between its rows of points
STRIDE = 0.75  # metres between one boot's print and the other's
PRINT_LONG = 0.31  # metres a boot print is long (a suit's boot)
PRINT_WIDE = 0.12
LIFT = 0.006  # metres every point stands over the ground
SPREAD = 0.18  # metres a walker's line wanders either side


def resampled(line, step):
    """The polyline's points every `step` metres along it, and each point's unit heading [x, z]."""
    line = np.asarray(line, float)
    lengths = np.hypot(*np.diff(line, axis=0).T)
    along = np.concatenate([[0.0], np.cumsum(lengths)])
    stations = np.arange(0.0, along[-1], step)
    points = np.column_stack([np.interp(stations, along, line[:, 0]), np.interp(stations, along, line[:, 1])])
    heading = np.gradient(points, axis=0)
    heading /= np.maximum(np.hypot(*heading.T), 1e-9)[:, None]
    return points, heading, stations


def rut_rows(line, offset, height_at):
    """One rut beside `line` at `offset` metres to its left: its points (rows x 6 x 3) across berm, rut and berm."""
    points, heading, stations = resampled(line, STEP)
    left = np.column_stack([-heading[:, 1], heading[:, 0]])
    across = np.array([-RUT_WIDE / 2 - BERM_WIDE, -RUT_WIDE / 2 - BERM_WIDE / 3, -RUT_WIDE / 2 + 0.02,
                       RUT_WIDE / 2 - 0.02, RUT_WIDE / 2 + BERM_WIDE / 3, RUT_WIDE / 2 + BERM_WIDE])
    ridge = np.where(np.mod(stations, TREAD) < TREAD / 2, TREAD_HIGH, 0.0)
    rise = np.array([0.0, BERM_HIGH, RUT_LOW, RUT_LOW, BERM_HIGH, 0.0])
    middles = points + left * offset
    spots = middles[:, None, :] + left[:, None, :] * across[None, :, None]
    lifted = rise[None, :] + ridge[:, None] * np.array([0.0, 0.0, 1.0, 1.0, 0.0, 0.0])[None, :]
    heights = np.asarray(height_at(spots[..., 0].ravel(), spots[..., 1].ravel())).reshape(spots.shape[:2])
    return np.stack([spots[..., 0], heights + LIFT + lifted, spots[..., 1]], axis=-1)


def strip_faces(rows, first):
    """Quad faces joining consecutive rows of points (numbered from `first`)."""
    count, wide = rows.shape[:2]
    faces = []
    for row in range(count - 1):
        for column in range(wide - 1):
            here = first + row * wide + column
            faces.append([here, here + 1, here + wide + 1, here + wide])
    return faces


def boot_prints(line, height_at, rng):
    """Boot prints along a walker's `line`, left and right by turns, as points and quad faces."""
    points, heading, _ = resampled(line, STRIDE / 2)
    corners, faces = [], []
    wander = 0.0
    for number, (at, ahead) in enumerate(zip(points, heading)):
        wander = float(np.clip(wander + rng.normal(0.0, 0.04), -SPREAD, SPREAD))
        side = np.array([-ahead[1], ahead[0]])
        centre = at + side * (wander + (0.13 if number % 2 else -0.13))
        turn = rng.normal(0.0, 0.08)
        forward = np.array([ahead[0] * math.cos(turn) - ahead[1] * math.sin(turn),
                            ahead[0] * math.sin(turn) + ahead[1] * math.cos(turn)])
        across = np.array([-forward[1], forward[0]])
        start = len(corners)
        for long_sign, wide_sign in ((-1, -1), (-1, 1), (1, 1), (1, -1)):
            corners.append(centre + forward * long_sign * PRINT_LONG / 2 + across * wide_sign * PRINT_WIDE / 2)
        faces.append([start, start + 1, start + 2, start + 3])
    if not corners:
        return [], []
    corners = np.asarray(corners)
    heights = np.asarray(height_at(corners[:, 0], corners[:, 1])) + LIFT
    return np.column_stack([corners[:, 0], heights, corners[:, 1]]).tolist(), faces


def part_mesh(stage, path, points, faces):
    """A mesh at `path` of quads `faces` over `points`, two-sided, its extent written."""
    points = np.asarray(points, dtype=np.float32).reshape(-1, 3)
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray([4] * len(faces)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(np.asarray(faces, int).reshape(-1).tolist()))
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*points.min(axis=0).tolist()),
                                         Gf.Vec3f(*points.max(axis=0).tolist())]))


def tracks_file(target, rover, boots, height_at, seed=0):
    """The ruts of every `rover` line and the prints of every `boots` line written to `target`; their counts."""
    if not rover and not boots:
        raise ValueError("tracks need a rover line or a boots line")
    for line in list(rover) + list(boots):
        if len(line) < 2:
            raise ValueError(f"a track's line needs two points or more: {line}")
    rng = np.random.default_rng(seed)
    rut_points, rut_faces = [], []
    for line in rover:
        for offset in (-GAUGE / 2, GAUGE / 2):
            rows = rut_rows(line, offset, height_at)
            rut_faces += strip_faces(rows, len(rut_points))
            rut_points += rows.reshape(-1, 3).tolist()
    print_points, print_faces = [], []
    for line in boots:
        corners, faces = boot_prints(line, height_at, rng)
        print_faces += [[corner + len(print_points) for corner in face] for face in faces]
        print_points += corners
    stage = Usd.Stage.CreateNew(str(target))
    stage.SetMetadata("upAxis", "Y")
    stage.SetMetadata("metersPerUnit", 1.0)
    root = UsdGeom.Xform.Define(stage, "/Tracks")
    stage.SetDefaultPrim(root.GetPrim())
    root.GetPrim().CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(
        "algorithm ground_tracks (ground_tracks.tracks_file)")
    if rut_faces:
        part_mesh(stage, "/Tracks/ruts", rut_points, rut_faces)
    if print_faces:
        part_mesh(stage, "/Tracks/prints", print_points, print_faces)
    stage.GetRootLayer().Save()
    return {"ruts": len(rut_faces), "prints": len(print_faces)}
