"""A real ground's relief (#128, the camp's third try: the owner found the flat ground disc "still very fake"): a
heightfield read from a public-domain HiRISE digital terrain model of Mars, written once as a terrain model entry's
mesh, and laid in a place with its building pads levelled.

The mesh is one `geo` with one part `ground` (so `surface --part ground` dresses it as a ground disc is dressed),
y up, metres, its origin the window's centre at height 0. Its posts are the DTM's own (about 1 m) out to `near` metres
from the centre and grow wider beyond (FAR_GROWTH, at most FAR_POST), each far post the DTM smoothed over its own
spacing, so a view across the plain to the horizon reads the real relief without a million points; the plain bends
down with the planet (PLANET_RADIUS) so its far edge drops under the eye as the real horizon does.

    dtm_label(url)                                  the PDS label's numbers a window needs
    dtm_window(url, first_row, rows, first_col, cols)   heights in metres (gaps filled from the nearest)
    graded_axis(half, near)                          a post line from -half to half, fine near 0, wider out
    heightfield_file(heights, post, path, near, half)    the terrain written as a USD file at `path`
    padded_file(source, path, pads, blend)           a copy of a terrain with level pads (x, z, radius) at height 0

The DTM is read with HTTP range requests (only the rows a window needs), never downloaded whole.
"""
import math
import re
import urllib.request

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

PLANET_RADIUS = 3389500.0  # Mars' mean radius, metres
NEAR = 160.0  # metres from the centre with the DTM's own posts
FAR_GROWTH = 0.02  # how much wider each post beyond NEAR is than the one before (2 %)
FAR_POST = 24.0  # the widest post, metres
FINE_SMOOTH = 1.0  # the DTM's own posts smoothed over this many posts (its stereo noise and tile seams; HiRISE
# DTMs resolve about three posts, so this keeps every real form)
BLEND = 6.0  # metres over which a pad eases into the ground round it
LABEL_BYTES = 65536


def dtm_label(url):
    """{record_bytes, image_record, lines, samples, post, missing} of a HiRISE DTM's PDS label (its first bytes)."""
    request = urllib.request.Request(url, headers={"Range": f"bytes=0-{LABEL_BYTES - 1}"})
    text = urllib.request.urlopen(request, timeout=60).read().decode("latin-1")
    ending = re.search(r"^END\s*$", text, re.MULTILINE)
    text = text[:ending.start()] if ending else text

    def number(key):
        found = re.search(rf"^\s*{key}\s*=\s*([-0-9.]+)", text, re.MULTILINE)
        if found is None:
            raise ValueError(f"{url}: its label names no {key}")
        return float(found.group(1))
    return {"record_bytes": int(number("RECORD_BYTES")), "image_record": int(number(r"\^IMAGE")),
            "lines": int(number("LINES")), "samples": int(number("LINE_SAMPLES")),
            "post": number("MAP_SCALE")}


def filled(heights):
    """The heights with every gap (no-data posts, NaN) taken from its nearest post that has one."""
    from scipy import ndimage
    gaps = ~np.isfinite(heights)
    if not gaps.any():
        return heights
    if gaps.all():
        raise ValueError("the window holds no heights")
    nearest = ndimage.distance_transform_edt(gaps, return_distances=False, return_indices=True)
    return heights[tuple(nearest)]


def dtm_window(url, first_row, rows, first_col, cols):
    """The DTM's heights (metres, float64) of `rows` lines from `first_row` and `cols` samples from `first_col`, read
    with one range request; its no-data posts (any value under -1e30, the PDS missing constant) filled."""
    label = dtm_label(url)
    if first_row < 0 or first_col < 0 or first_row + rows > label["lines"] or first_col + cols > label["samples"]:
        raise ValueError(f"the window {first_row}+{rows} x {first_col}+{cols} leaves the DTM "
                         f"({label['lines']} x {label['samples']})")
    start = label["record_bytes"] * (label["image_record"] - 1 + first_row)
    end = start + label["record_bytes"] * rows - 1
    request = urllib.request.Request(url, headers={"Range": f"bytes={start}-{end}"})
    data = urllib.request.urlopen(request, timeout=600).read()
    if len(data) != end - start + 1:
        raise ValueError(f"{url}: {len(data)} bytes came back for {end - start + 1}")
    lines = np.frombuffer(data, "<f4").reshape(rows, label["record_bytes"] // 4)
    heights = lines[:, first_col:first_col + cols].astype(np.float64)
    heights[heights < -1e30] = np.nan
    return filled(heights), label["post"]


def graded_axis(half, near=NEAR, post=1.0):
    """Post positions from -half to half (metres): `post` apart out to `near`, then each FAR_GROWTH wider than the
    last, at most FAR_POST, the last one on `half`."""
    outward = [0.0]
    step = post
    while outward[-1] < half:
        if outward[-1] >= near:
            step = min(step * (1.0 + FAR_GROWTH), FAR_POST)
        outward.append(min(outward[-1] + step, half))
    outward = np.array(outward)
    return np.concatenate([-outward[:0:-1], outward])


def sampled(heights, post, xs, zs):
    """The heights at the grid of posts xs (across) by zs (down), metres from the window's centre, each read
    (bilinear) from the DTM smoothed over that post's own spacing, so a wide far post is the mean of its ground."""
    from scipy import ndimage
    rows, cols = heights.shape
    spacing = np.maximum.outer(np.gradient(zs), np.gradient(xs)) if min(len(xs), len(zs)) > 1 else \
        np.full((len(zs), len(xs)), post)
    levels = np.maximum(np.round(spacing / post), FINE_SMOOTH)
    grid_x, grid_z = np.meshgrid(xs / post + (cols - 1) / 2.0, zs / post + (rows - 1) / 2.0)
    found = np.empty(levels.shape)
    for level in np.unique(levels):
        chosen = levels == level
        smoothed = ndimage.gaussian_filter(heights, level / 2.0, mode="nearest")
        found[chosen] = ndimage.map_coordinates(smoothed, [grid_z[chosen], grid_x[chosen]], order=1, mode="nearest")
    return found


def grid_faces(across, down):
    """Quads of a grid `across` x `down` points (row-major), wound so their normals face up (+y) when x runs east and
    z runs down the rows."""
    index = np.arange(across * down).reshape(down, across)
    corners = np.stack([index[:-1, :-1], index[1:, :-1], index[1:, 1:], index[:-1, 1:]], axis=-1)
    return corners.reshape(-1, 4)


def mesh_file(path, points, quads, extra=None):
    """A USD file at `path`: Xform `terrain` with one Mesh `geo` of `points` and `quads`, its faces all in the part
    `ground`; `extra` {name: value} written as score: attributes on the root (the window's source)."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/terrain")
    stage.SetDefaultPrim(root.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, "/terrain/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points.astype(np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(quads), 4, np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(quads.reshape(-1).astype(np.int32)))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    low, high = points.min(axis=0), points.max(axis=0)
    mesh.CreateExtentAttr(Vt.Vec3fArray([Gf.Vec3f(*map(float, low)), Gf.Vec3f(*map(float, high))]))
    UsdGeom.Subset.CreateGeomSubset(mesh, "ground", UsdGeom.Tokens.face,
                                    Vt.IntArray.FromNumpy(np.arange(len(quads), dtype=np.int32)), "materialBind")
    for name, value in (extra or {}).items():
        root.GetPrim().CreateAttribute(f"score:{name}", Sdf.ValueTypeNames.String).Set(str(value))
    stage.GetRootLayer().Save()
    return path


def heightfield_file(heights, post, path, near=NEAR, half=None, source=None):
    """The window's terrain written at `path`: graded posts (graded_axis) over the window's middle square of `half`
    metres each way (all of it by default), heights relative to the centre's, bent down with the planet."""
    rows, cols = heights.shape
    half = half or post * (min(rows, cols) - 1) / 2.0
    xs = graded_axis(half, near, post)
    zs = graded_axis(half, near, post)
    found = sampled(heights, post, xs, zs)
    middle = sampled(heights, post, np.array([0.0]), np.array([0.0]))[0, 0]
    grid_x, grid_z = np.meshgrid(xs, zs)
    lift = found - middle - (grid_x ** 2 + grid_z ** 2) / (2.0 * PLANET_RADIUS)
    points = np.stack([grid_x, lift, grid_z], axis=-1).reshape(-1, 3)
    return mesh_file(path, points, grid_faces(len(xs), len(zs)), {"source": source} if source else None)


def eased(distance, radius, blend):
    """How much of a pad's level a point `distance` from its centre takes: 1 inside its radius, easing to 0 over
    `blend` metres beyond (smoothstep)."""
    share = np.clip((radius + blend - distance) / blend, 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def padded_file(source, path, pads, blend=BLEND):
    """A copy of the terrain at `source` written at `path` with each pad (x, z, radius; the terrain's own frame)
    levelled to height 0 and eased into the ground round it, as a building's site is graded."""
    opened = Usd.Stage.Open(str(source))
    mesh = UsdGeom.Mesh(next(prim for prim in opened.Traverse() if prim.IsA(UsdGeom.Mesh)))
    points = np.array(mesh.GetPointsAttr().Get(), dtype=np.float64)
    keep = np.ones(len(points))
    for x, z, radius in pads:
        distance = np.hypot(points[:, 0] - x, points[:, 2] - z)
        keep = np.minimum(keep, 1.0 - eased(distance, radius, blend))
    points[:, 1] *= keep
    quads = np.array(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 4)
    return mesh_file(path, points, quads, {"padded": [list(pad) for pad in pads]})


def height_at(source, x, z):
    """The terrain's height at (x, z) in its own frame: the nearest post's."""
    opened = Usd.Stage.Open(str(source))
    mesh = UsdGeom.Mesh(next(prim for prim in opened.Traverse() if prim.IsA(UsdGeom.Mesh)))
    points = np.array(mesh.GetPointsAttr().Get())
    return float(points[np.argmin(np.hypot(points[:, 0] - x, points[:, 2] - z)), 1])


def turned_pads(pads, at, turn_degrees):
    """Pads given in the scene's frame (x, z, radius) carried into the terrain's own frame (laid at `at`, turned
    `turn_degrees` about up)."""
    angle = math.radians(turn_degrees)
    found = []
    for x, z, radius in pads:
        dx, dz = x - at[0], z - at[2]
        # the inverse of a turn about +y: x' = cos*x - sin*z, z' = sin*x + cos*z
        found.append((math.cos(angle) * dx - math.sin(angle) * dz, math.sin(angle) * dx + math.cos(angle) * dz,
                      radius))
    return found
