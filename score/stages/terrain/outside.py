"""What a place sees outside, from a made ground: the ground in the place's own frame (a fine patch round the place,
the whole plan past it, the ground running on to the horizon), the ball under it on a small world, the harbour's water
on the Earth, each mesh split into parts by zone with every part one library surface; and the place's neighbours from
its scene record. Written as OpenUSD under /<place>/Outside and /<place>/Places, over the old ground the place drew
(/<place>/Ground, /Terrain and /Water are made inactive).

    meshes = outside.meshes(made, seat, footprint)       # {name: (points, triangles, zone per triangle)}
    outside.write(stage, place, made, meshes, laid, scene_record, neighbour_path)
"""
import sys
import pathlib

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, UsdGeom, UsdShade, Vt

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import colliders  # noqa: E402
import ground as grounds  # noqa: E402
import scene as scene_records  # noqa: E402

# The fine patch: this far past the place's footprint, points this far apart (metres).
NEAR_MARGIN = 60.0
NEAR_STEP = 0.5
# The whole plan past the patch, at this many points a side, out to FAR_REACH times the plan's side round the place
# (past the plan its edge's heights run on, as ground.py reads a spot off the plan).
FAR_POINTS = 480
FAR_REACH = 0.75
# The ground on to the horizon: out to this far (metres), this many points a side; on a small world the ball does it.
HORIZON = 30000.0
HORIZON_POINTS = 96
# The ball under a small world's ground sits this far under its round surface (as the game's planned ground does).
BALL_BELOW = 0.6
# What the old ground of a place was drawn as, made inactive under the made ground.
OLD_GROUND = ("Ground", "Terrain", "Water")
# A neighbour's own shared things, made inactive where a place references it (as the export does).
NEIGHBOUR_SHARED = ("Ground", "Terrain", "Water", "Backdrop", "Sky", "Environment", "Places", "Outside")


def placed_ground(made, seat, on_seat):
    """The made ground as tools/usd/ground.py stands a place on it: the Ground of that seat."""
    return grounds.Ground(made, seat, on_seat)


def zone_reader(made):
    """Each spot's zone index on the plan, read off the zones picture at the plan's (u, v)."""
    zones = np.asarray(Image.open(pathlib.Path(made["folder"]) / made["zones"]))
    last = zones.shape[0] - 1

    def read(skin_at):
        at = np.clip(np.round(skin_at * last), 0, last).astype(int)
        return zones[at[:, 1], at[:, 0]]
    return read


def grid_mesh(laid, low, high, step, cut=None):
    """The ground over a box of the place (low, high: across and along) at `step` metres, as points, triangles
    (less those wholly inside `cut`, a box) and each point's plan (u, v)."""
    points, triangles, skin_at = laid.mesh(np.asarray(low, dtype=float), np.asarray(high, dtype=float), 0.0, step)
    if cut is not None:
        flat = points[:, [0, 2]]
        inside = np.all((flat > np.asarray(cut[0]) + step) & (flat < np.asarray(cut[1]) - step), axis=1)
        triangles = triangles[~np.all(inside[triangles], axis=1)]
    return points, triangles, skin_at


def meshes(made, seat, on_seat, footprint):
    """The made ground's meshes for one place: {name: (points, triangles, zone of each triangle)} in the place's
    frame, and the Ground they were read on."""
    laid = placed_ground(made, seat, on_seat)
    zone_of = zone_reader(made)
    low = np.asarray(footprint[0], dtype=float) - NEAR_MARGIN
    high = np.asarray(footprint[1], dtype=float) + NEAR_MARGIN
    middle = (np.asarray(footprint[0]) + np.asarray(footprint[1])) / 2
    reach = made["side"] * FAR_REACH
    far_step = 2 * reach / FAR_POINTS
    found = {}
    near = grid_mesh(laid, low, high, NEAR_STEP)
    found["near"] = near
    found["far"] = grid_mesh(laid, middle - reach, middle + reach, far_step, cut=(low, high))
    if made["radius"] > 10 * HORIZON:
        found["horizon"] = grid_mesh(laid, middle - HORIZON, middle + HORIZON, 2 * HORIZON / HORIZON_POINTS,
                                     cut=(middle - reach, middle + reach))
    zoned = {}
    for name, (points, triangles, skin_at) in found.items():
        corner_zones = zone_of(skin_at)[triangles]
        zoned[name] = (points, triangles, corner_zones[:, 0])
    if made.get("water"):
        zoned["water"] = water_mesh(laid, made, middle, reach)
    return zoned, laid


def water_mesh(laid, made, middle, reach):
    """The harbour's water: a level sheet at the plan's water level over every part of the plan and the horizon
    where the ground lies under it."""
    level = made["water"]["level"]
    parts = []
    for half, points_a_side in ((reach, FAR_POINTS), (HORIZON, HORIZON_POINTS)):
        step = 2 * half / points_a_side
        ground_points, triangles, _ = laid.mesh(middle - half, middle + half, 0.0, step)
        across = np.arange(middle[0] - half, middle[0] + half + step, step)
        along = np.arange(middle[1] - half, middle[1] + half + step, step)
        grid_x, grid_z = np.meshgrid(across, along)
        flat = laid.origin + grid_x.reshape(-1, 1) * laid.frame[0] + grid_z.reshape(-1, 1) * laid.frame[2]
        directions = flat / np.linalg.norm(flat, axis=1, keepdims=True)
        surface = laid.in_place_frame(directions * (laid.radius + level))
        under = ground_points[:, 1] < surface[:, 1] - 0.01
        keep = np.any(under[triangles], axis=1)
        parts.append((surface, triangles[keep]))
    offset = len(parts[0][0])
    points = np.concatenate([parts[0][0], parts[1][0]])
    triangles = np.concatenate([parts[0][1], parts[1][1] + offset])
    return points, triangles, np.full(len(triangles), -1)


def look(stage, path, surface, colour):
    """A library surface's look on the stage: its design token's colour, no shine, named for the surface."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*[srgb_to_linear(int(colour[index:index + 2], 16) / 255) for index in (1, 3, 5)]))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.05 if surface == "harbour_water" else 1.0)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    material.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(surface)
    return material


def srgb_to_linear(value):
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def write_mesh(stage, path, points, triangles, kind):
    """One mesh of triangles named for what it is (score:kind), a static collider when it is solid (ground, not
    water: colliders.solid)."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points.astype(np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(triangles), 3, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(triangles.reshape(-1).astype(np.int32)))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    used = points[np.unique(triangles)] if len(triangles) else points[:1]
    mesh.CreateExtentAttr([Gf.Vec3f(*used.min(axis=0).tolist()), Gf.Vec3f(*used.max(axis=0).tolist())])
    mesh.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set(kind)
    if kind in colliders.SOLID_KINDS:
        colliders.solid(mesh.GetPrim(), points, triangles)
    return mesh


def water_mirror(scene):
    """How the place's own water mirrors (its scene record's first water with a `mirror`), or None."""
    return next((entry["mirror"] for entry in scene.get("water") or [] if "mirror" in entry), None)


def write_ground(stage, place, made, zoned, looks, mirror):
    """The ground's meshes under /<place>/Outside, each split by zone into parts (GeomSubsets named after their
    library surface), every part bound to its surface's look; the water mirroring as the place's own did."""
    surfaces = made["surfaces"]
    for name, (points, triangles, zone) in zoned.items():
        if not len(triangles):
            continue
        path = f"/{place}/Outside/{name}"
        if name == "water":
            mesh = write_mesh(stage, path, points, triangles, "water")
            UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(looks[made["water"]["surface"]])
            mesh.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(made["water"]["surface"])
            if mirror:
                scene_records.write_mirror(mesh.GetPrim(), mirror)
            continue
        mesh = write_mesh(stage, path, points, triangles, "ground")
        for index in np.unique(zone):
            surface = surfaces[int(index)]["surface"]
            subset = UsdGeom.Subset.Define(stage, f"{path}/{surface}")
            subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
            subset.CreateFamilyNameAttr(UsdShade.Tokens.materialBind)
            subset.CreateIndicesAttr(Vt.IntArray.FromNumpy(np.nonzero(zone == index)[0].astype(np.int32)))
            UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(looks[surface])


def write_ball(stage, place, laid, made, looks):
    """A small world's ball under the ground, so the ground runs round to the horizon."""
    sphere = UsdGeom.Sphere.Define(stage, f"/{place}/Outside/ball")
    sphere.CreateRadiusAttr(laid.radius - BALL_BELOW)
    sphere.AddTranslateOp().Set(Gf.Vec3d(*map(float, laid.in_place_frame(np.zeros(3))[0])))
    first = made["surfaces"][-1]["surface"]
    UsdShade.MaterialBindingAPI.Apply(sphere.GetPrim()).Bind(looks[first])
    sphere.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("ground")
    colliders.solid(sphere.GetPrim())


def write_places(stage, place, places, neighbour_path):
    """The neighbours the place's scene record names and its stage lacks, under /<place>/Places, each a reference to
    its stage (`neighbour_path(stage name)`), moved and turned where the record stands it, its own shared things
    inactive; the names of those added."""
    added = []
    for entry in places:
        if stage.GetPrimAtPath(f"/{place}/Places/{entry['name']}").IsValid():
            continue
        added.append(entry["name"])
        prim = UsdGeom.Xform.Define(stage, f"/{place}/Places/{entry['name']}")
        prim.GetPrim().GetReferences().AddReference(neighbour_path(entry["stage"]))
        prim.AddTranslateOp().Set(Gf.Vec3d(*map(float, entry["at"])))
        prim.AddRotateYOp().Set(float(entry.get("yaw", 0.0)))
        prim.GetPrim().CreateAttribute("score:place", Sdf.ValueTypeNames.String).Set(entry["stage"])
        for shared in NEIGHBOUR_SHARED:
            stage.OverridePrim(f"/{place}/Places/{entry['name']}/{shared}").SetActive(False)
    return added


def write(stage, place, made, zoned, laid, scene, neighbour_path):
    """The made ground into the stage (its edit target), over the place's old ground (its water mirroring as the
    place's scene record has it), and the neighbours the record names that the stage lacks; the names of those
    added."""
    for old in OLD_GROUND:
        stage.OverridePrim(f"/{place}/{old}").SetActive(False)
    UsdGeom.Scope.Define(stage, f"/{place}/Outside")
    looks = {surface["surface"]: look(stage, f"/{place}/Outside/Looks/{surface['surface']}", surface["surface"],
                                      surface["colour"]) for surface in made["surfaces"]}
    if made.get("water"):
        looks[made["water"]["surface"]] = look(stage, f"/{place}/Outside/Looks/{made['water']['surface']}",
                                               made["water"]["surface"], made["water"]["colour"])
    write_ground(stage, place, made, zoned, looks, water_mirror(scene))
    if laid.radius < HORIZON:
        write_ball(stage, place, laid, made, looks)
    return write_places(stage, place, scene.get("places", []), neighbour_path)
