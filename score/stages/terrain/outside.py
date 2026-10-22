"""What a place sees outside: its made ground (design.py) in the place's own frame, a fine patch round its plan's box
and a coarse ground out past its horizon, written as OpenUSD under /<place>/Outside (`near`, `far`), over any old
ground the place drew (/<place>/Ground, /Terrain and /Water made inactive). Each mesh is a static collider and names
the ground's row (its top scene's inventory row the ground is) and its finish as missing until the surface line makes
it: never painted another way.

    meshes = outside.meshes(ground, place, shaped)     # {"near": (points, triangles), "far": ...} in the place's frame
    outside.write(stage, place, meshes, row, recipe)
"""
import math
import pathlib
import sys

import numpy as np
from pxr import Gf, Sdf, UsdGeom, Vt

from score.stages.terrain import design

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import colliders  # noqa: E402

# The fine patch: this far past the place's box, points this far apart, at most NEAR_MOST points a side (metres).
NEAR_MARGIN = 30.0
NEAR_STEP = 0.5
NEAR_MOST = 640
# The coarse ground: this many points a side, finest at its middle, out to the horizon an eye this high over the
# ground sees on a body (a balcony's), and never less than FAR_LEAST (a plot's, a ray's reach to the ground).
FAR_POINTS = 160
HORIZON_EYE = 12.0
FAR_LEAST = 1500.0
# What the old ground of a place was drawn as, made inactive under the made ground.
OLD_GROUND = ("Ground", "Terrain", "Water")


def reach(ground):
    """How far the coarse ground runs round a place (metres)."""
    if ground["kind"] != "body":
        return FAR_LEAST
    return max(FAR_LEAST, math.sqrt(2.0 * ground["radius"] * HORIZON_EYE))


def grid(across, along):
    """A grid's spots [[x, z]] over its lines across and along, and its triangles (two a square)."""
    grid_x, grid_z = np.meshgrid(across, along)
    columns = len(across)
    first = (np.arange(len(along) - 1)[:, None] * columns + np.arange(columns - 1)[None, :]).ravel()
    triangles = np.concatenate([np.column_stack([first, first + columns, first + 1]),
                                np.column_stack([first + 1, first + columns, first + columns + 1])])
    return np.column_stack([grid_x.ravel(), grid_z.ravel()]), triangles


def near_box(entry):
    """The fine patch's box (low, high: x and z) round a place's plan box, and its step."""
    low = np.asarray(entry["box"][0], dtype=float) - NEAR_MARGIN
    high = np.asarray(entry["box"][1], dtype=float) + NEAR_MARGIN
    return low, high, max(NEAR_STEP, float((high - low).max()) / NEAR_MOST)


def meshes(ground, place, shaped=None):
    """The ground's meshes for one place, {name: (points, triangles)} in its frame: `near` over its fine patch, `far`
    a grid finest at the place's middle out to `reach`, less what lies wholly inside the patch."""
    entry = ground["places"][place]
    low, high, step = near_box(entry)
    spots, triangles = grid(np.arange(low[0], high[0] + step / 2, step), np.arange(low[1], high[1] + step / 2, step))
    found = {"near": (design.ground_points(ground, place, spots, shaped), triangles)}
    middle = (low + high) / 2
    stretch = np.linspace(-1.0, 1.0, FAR_POINTS + 1)
    stretch = stretch * np.abs(stretch) * reach(ground)
    spots, triangles = grid(middle[0] + stretch, middle[1] + stretch)
    inside = np.all((spots > low + step) & (spots < high - step), axis=1)
    found["far"] = (design.ground_points(ground, place, spots, shaped), triangles[~inside[triangles].all(axis=1)])
    return found


def write_mesh(stage, path, points, triangles, row, recipe):
    """One ground mesh, a static collider, naming its row, the natural ground recipe its finish is made with by rule
    (`recipe`: [recipe, why], natural_grounds) and its finish missing until the surface line makes it."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points.astype(np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(triangles), 3, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(triangles.reshape(-1).astype(np.int32)))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    used = points[np.unique(triangles)]
    mesh.CreateExtentAttr([Gf.Vec3f(*used.min(axis=0).tolist()), Gf.Vec3f(*used.max(axis=0).tolist())])
    prim = mesh.GetPrim()
    prim.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("ground")
    prim.CreateAttribute("score:surface:missing", Sdf.ValueTypeNames.String).Set(
        f"the ground's finish ({row or 'no ground row in its top scene inventory'}, {recipe[0] or 'no'} recipe: "
        f"{recipe[1]}) is not in the library yet: the surface line makes it")
    if recipe[0]:
        prim.CreateAttribute("score:ground:recipe", Sdf.ValueTypeNames.String).Set(recipe[0])
    if row:
        prim.CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set(row)
    colliders.solid(prim, points, triangles)
    return mesh


def write(stage, place, found, row, recipe):
    """The made ground into the stage (its edit target) under /<place>/Outside, over the place's old ground; its
    natural ground recipe `recipe` ([recipe, why]) on each mesh."""
    for old in OLD_GROUND:
        stage.OverridePrim(f"/{place}/{old}").SetActive(False)
    UsdGeom.Scope.Define(stage, f"/{place}/Outside")
    for name, (points, triangles) in found.items():
        write_mesh(stage, f"/{place}/Outside/{name}", points, triangles, row, recipe)
