"""The truth of one adopted NVIDIA SimReady model, read from its library entry (the shape `truth/__init__.py` names).

Its USD files only are fetched (library_files: the library cache), its stage opened, and every prim walked through its
instances (`Usd.TraverseInstanceProxies`, as place_build reads an adopted model). Points are carried to the world by
each prim's own transform and to metres by the stage's metersPerUnit, kept Z up as NVIDIA authors every SimReady model
(the measures' frame, tools/props/bench/measures); a stage that is not Z up is refused.
"""
import pathlib
import sys

import numpy as np
import trimesh

from pxr import Usd, UsdGeom, UsdPhysics, UsdShade

from score import library

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tools/library"))
import library_files  # noqa: E402

from tools.props.bench.truth import _look  # noqa: E402

SURFACE = "score:surface"  # the library surface a material names (score_lib's take-in writes it)
SHOWN = ("default", "render")  # the purposes of a mesh that is drawn
SIMULATORS = {"newton": "Newton", "mujoco": "MuJoCo"}  # the payloads read: {key: its variant set on the root}
HULLED = ("convexHull",)  # Newton approximations whose collider is the mesh's convex hull
MESHED = ("none", "convexDecomposition", "meshSimplification", "sdf")  # Newton ones the payload holds as the mesh
FRICTION = {"static_friction": "physics:staticFriction", "dynamic_friction": "physics:dynamicFriction",
            "restitution": "physics:restitution", "density": "physics:density"}
OWN_PREFIXES = ("newton:", "mjc:")  # a physics material's simulator-own settings, kept as they are
FETCHED = ("usd", "texture")  # the entry's files read: its stages, and its maps for each face's look (_look)


class Unread(RuntimeError):
    """An entry whose truth cannot be read as it stands (no USD root, an approximation this reader does not know)."""


def fetched_root(address):
    """The entry's root USD file in the library cache, its other USD files and its maps (FETCHED) fetched beside it."""
    kind, rest = address.split("/", 1)
    entry_id, version = rest.split("@")
    root = library.root_from_environment() or library_files.default_root()
    record = library.entry(root, kind, entry_id, int(version))
    named = (record.get("usd") or {}).get("root")
    if named not in record["files"]:
        raise Unread(f"{address}: its record names no USD root among its files")
    found = {}
    for name, info in record["files"].items():
        if info.get("role") in FETCHED:
            path = library_files.resolve(library_files.reference(address, name))
            if path is None:
                raise Unread(f"{address}/{name}: the library does not hold this file")
            found[name] = path
    return record, found[named]


def opened(path, simulator=None):
    """The stage at `path`, its payload variant sets set in its session layer: `simulator`'s enabled and the others
    disabled, or the file's own selection when None."""
    stage = Usd.Stage.Open(str(path))
    if simulator is not None:
        stage.SetEditTarget(stage.GetSessionLayer())
        sets = stage.GetDefaultPrim().GetVariantSets()
        for name in sets.GetNames():
            sets.GetVariantSet(name).SetVariantSelection("Enabled" if name == simulator else "Disabled")
    return stage


def upright_turn(stage):
    """The 4x4 that carries the stage's units to metres (row vectors, as USD's matrices); Unread for a stage that is
    not Z up."""
    if str(UsdGeom.GetStageUpAxis(stage)).upper() != "Z":
        raise Unread(f"{stage.GetRootLayer().identifier}: up axis {UsdGeom.GetStageUpAxis(stage)}, not Z")
    turn = np.eye(4) * UsdGeom.GetStageMetersPerUnit(stage)
    turn[3, 3] = 1.0
    return turn


def placed_points(prim, turn):
    """The mesh's points in metres, Z up, in the world (its own transform, through any instance)."""
    points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get() or [], dtype=float).reshape(-1, 3)
    matrix = np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())) @ turn
    return np.c_[points, np.ones(len(points))] @ matrix[:, :3], matrix


def triangles(prim, matrix):
    """(the mesh's polygons fanned into triangles (T, 3), each triangle's polygon index (T,), each corner's face-vertex
    slot (T, 3): where a face-varying primvar holds it), wound so their normals point out after `matrix` (a
    left-handed mesh or a mirroring transform turned over)."""
    mesh = UsdGeom.Mesh(prim)
    counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get() or [], dtype=np.int64)
    corners = np.asarray(mesh.GetFaceVertexIndicesAttr().Get() or [], dtype=np.int64)
    if not len(counts):
        return np.zeros((0, 3), dtype=np.int64), np.zeros(0, dtype=np.int64), np.zeros((0, 3), dtype=np.int64)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    fans = np.clip(counts - 2, 0, None)
    polygon = np.repeat(np.arange(len(counts)), fans)
    step = np.arange(len(polygon)) - np.repeat(np.cumsum(fans) - fans, fans)
    first = starts[polygon]
    slots = np.stack([first, first + step + 1, first + step + 2], axis=1)
    mirrored = np.linalg.det(matrix[:3, :3]) < 0
    if (mesh.GetOrientationAttr().Get() == UsdGeom.Tokens.leftHanded) != mirrored:
        slots = slots[:, ::-1]
    return corners[slots], polygon, slots


def polygon_materials(prim, count, materials):
    """Each polygon's bound material as an index into `materials` (a list of material prim paths, grown here): the
    mesh's own binding, a material subset's over the faces it holds; -1 where none is bound."""
    def index_of(bound):
        if not bound:
            return -1
        path = str(bound.GetPath())
        if path not in materials:
            materials.append(path)
        return materials.index(path)
    binding = UsdShade.MaterialBindingAPI(prim)
    found = np.full(count, index_of(binding.ComputeBoundMaterial()[0]), dtype=np.int32)
    for subset in binding.GetMaterialBindSubsets():
        held = np.asarray(subset.GetIndicesAttr().Get() or [], dtype=np.int64)
        found[held[held < count]] = index_of(UsdShade.MaterialBindingAPI(subset.GetPrim()).ComputeBoundMaterial()[0])
    return found


def shown(prim):
    """Whether the prim is a mesh that is drawn (a drawn purpose, not invisible)."""
    imageable = UsdGeom.Imageable(prim)
    return (prim.IsA(UsdGeom.Mesh) and imageable.ComputePurpose() in SHOWN
            and imageable.ComputeVisibility() != UsdGeom.Tokens.invisible)


def visual(stage):
    """(vertices, faces, face_material, materials, face_prim, prims, face_uv) of every drawn mesh, instances
    flattened; face_uv (T, 3, 2) each triangle's corners' texture coordinates (_look.corner_uvs, NaN without)."""
    turn = upright_turn(stage)
    vertices, faces, face_material, face_prim, materials, prims, face_uv = [], [], [], [], [], [], []
    offset = 0
    for prim in Usd.PrimRange(stage.GetDefaultPrim(), Usd.TraverseInstanceProxies()):
        if not shown(prim):
            continue
        points, matrix = placed_points(prim, turn)
        triangle, polygon, slots = triangles(prim, matrix)
        counts = UsdGeom.Mesh(prim).GetFaceVertexCountsAttr().Get() or []
        face_uv.append(_look.corner_uvs(prim, triangle, polygon, slots))
        vertices.append(points)
        faces.append(triangle + offset)
        face_material.append(polygon_materials(prim, len(counts), materials)[polygon])
        face_prim.append(np.full(len(triangle), len(prims), dtype=np.int32))
        prims.append(str(prim.GetPath()))
        offset += len(points)
    if not prims:
        raise Unread(f"{stage.GetRootLayer().identifier}: no drawn mesh")
    return (np.concatenate(vertices), np.concatenate(faces), np.concatenate(face_material), materials,
            np.concatenate(face_prim), prims, np.concatenate(face_uv))


def described(stage, path, painted=()):
    """A material prim's {prim, name, surface, one_model}: the library surface its `score:surface` names, None when
    none; `one_model` whether that surface is painted for one model (`painted`: one_model_surfaces)."""
    prim = stage.GetPrimAtPath(path)
    named = prim.GetAttribute(SURFACE)
    surface = named.Get() if named and named.HasAuthoredValue() else None
    return {"prim": path, "name": prim.GetName(), "surface": surface, "one_model": surface in painted}


def one_model_surfaces(root):
    """The addresses of the library's surfaces painted for one model (their index rows' `painted_for` tag: maps that
    cover one model's UVs once); none when the library has no surface index."""
    if not (pathlib.Path(root) / "index" / "surface.json").is_file():
        return set()
    return {row["address"] for row in library.index(root, "surface")["entries"]
            if row.get("tags", {}).get("painted_for")}


def authored(prim, name):
    """An attribute's authored value, None when it has none."""
    attribute = prim.GetAttribute(name)
    return attribute.Get() if attribute and attribute.HasAuthoredValue() else None


def body_of(prim, bodies):
    """The index in `bodies` (rigid body prim paths) of the prim's nearest body, -1 when it has none."""
    while prim and prim.IsValid():
        path = str(prim.GetPath())
        if path in bodies:
            return bodies.index(path)
        prim = prim.GetParent()
    return -1


def rigid(stage):
    """(bodies [{prim, mass}] in prim path order, total mass) by USD physics' rule: a body's own authored MassAPI mass when above zero,
    else the sum of the masses authored under it; the total None when a body has no mass authored."""
    prims = sorted((prim for prim in Usd.PrimRange(stage.GetDefaultPrim(), Usd.TraverseInstanceProxies())
                    if prim.HasAPI(UsdPhysics.RigidBodyAPI)), key=lambda prim: str(prim.GetPath()))
    paths = [str(prim.GetPath()) for prim in prims]
    own = [authored(prim, "physics:mass") or 0.0 for prim in prims]
    under = [0.0] * len(prims)
    for prim in Usd.PrimRange(stage.GetDefaultPrim(), Usd.TraverseInstanceProxies()):
        mass = authored(prim, "physics:mass")
        if mass and str(prim.GetPath()) not in paths and body_of(prim, paths) >= 0:
            under[body_of(prim, paths)] += float(mass)
    masses = [float(mine) if mine > 0 else (rest or None) for mine, rest in zip(own, under)]
    bodies = [{"prim": path, "mass": mass} for path, mass in zip(paths, masses)]
    total = None if not bodies or None in masses else float(sum(masses))
    return bodies, total


def joints(stage, bodies):
    """[{prim, type, body0, body1}] of the stage's physics joints, each body an index into `bodies`' prims (-1 for
    the world or one outside the asset)."""
    paths = [body["prim"] for body in bodies]
    found = []
    for prim in Usd.PrimRange(stage.GetDefaultPrim(), Usd.TraverseInstanceProxies()):
        if prim.IsA(UsdPhysics.Joint):
            joint = UsdPhysics.Joint(prim)
            ends = [joint.GetBody0Rel().GetTargets(), joint.GetBody1Rel().GetTargets()]
            ends = [paths.index(str(end[0])) if end and str(end[0]) in paths else -1 for end in ends]
            found.append({"prim": str(prim.GetPath()), "type": prim.GetTypeName(), "body0": ends[0], "body1": ends[1]})
    return found


def physics_material(prim):
    """A physics material's {static_friction, dynamic_friction, restitution, density, own: {its newton:/mjc:
    settings}}, None for each it does not author."""
    found = {key: (float(value) if (value := authored(prim, name)) is not None else None)
             for key, name in FRICTION.items()}
    found["own"] = {attribute.GetName(): attribute.Get() for attribute in prim.GetAttributes()
                    if attribute.GetName().startswith(OWN_PREFIXES) and attribute.HasAuthoredValue()}
    found["own"] = {name: (value if isinstance(value, (bool, int, float, str)) else str(value))
                    for name, value in found["own"].items()}
    return found


def hull(points):
    """(vertices, faces) of the points' convex hull."""
    shape = trimesh.convex.convex_hull(points)
    return np.asarray(shape.vertices, dtype=float), np.asarray(shape.faces, dtype=np.int64)


def collider(prim, key, turn, bodies):
    """One collision prim of the `key` payload: {prim, body, approximation, physics_material, max_hull_vertices,
    convex, vertices, faces}, its shape the one the simulator collides with: MuJoCo every mesh's convex hull (it
    convexifies a mesh geom whatever it is told), Newton a convexHull's hull and the mesh itself otherwise."""
    if not prim.IsA(UsdGeom.Mesh):
        raise Unread(f"{prim.GetPath()}: a {prim.GetTypeName()} collider; this reader knows mesh colliders only")
    approximation = str(authored(prim, "physics:approximation") or "none")
    if key == "newton" and approximation not in HULLED + MESHED:
        raise Unread(f"{prim.GetPath()}: Newton approximation {approximation} is not one this reader knows")
    points, matrix = placed_points(prim, turn)
    convex = key == "mujoco" or approximation in HULLED
    vertices, faces = hull(points) if convex else (points, triangles(prim, matrix)[0])
    bound = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial("physics")[0]
    most = authored(prim, "mjc:maxhullvert")
    return {"prim": str(prim.GetPath()), "body": body_of(prim, [body["prim"] for body in bodies]),
            "approximation": approximation, "physics_material": str(bound.GetPath()) if bound else None,
            "max_hull_vertices": int(most) if most is not None and most > 0 else None,
            "convex": convex, "vertices": vertices, "faces": faces}


def colliders(path, key, bodies):
    """(colliders in prim path order, {physics material prim: its settings}) of the `key` payload (SIMULATORS)
    enabled alone."""
    stage = opened(path, SIMULATORS[key])
    turn = upright_turn(stage)
    found = [collider(prim, key, turn, bodies)
             for prim in sorted(Usd.PrimRange(stage.GetDefaultPrim(), Usd.TraverseInstanceProxies()),
                                key=lambda prim: str(prim.GetPath()))
             if prim.HasAPI(UsdPhysics.CollisionAPI) and authored(prim, "physics:collisionEnabled") is not False]
    materials = {name: physics_material(stage.GetPrimAtPath(name))
                 for name in sorted({shape["physics_material"] for shape in found} - {None})}
    return found, materials


def friction(shapes, materials):
    """The static friction the colliders touch with: their physics materials' own, weighted by each collider's volume
    when they differ; None when none authors one."""
    held = [(materials[shape["physics_material"]]["static_friction"],
             abs(trimesh.Trimesh(shape["vertices"], shape["faces"]).volume)) for shape in shapes
            if shape["physics_material"] and materials[shape["physics_material"]]["static_friction"] is not None]
    if not held:
        return None
    values, weights = np.array(held, dtype=float).T
    return float(np.average(values, weights=weights)) if weights.sum() > 0 else float(values.mean())


def read(address):
    """The truth of the adopted model at `address` (`model/<id>@<version>`), as `truth/__init__.py` names it."""
    record, path = fetched_root(address)
    stage = opened(path)
    vertices, faces, face_material, materials, face_prim, prims, face_uv = visual(stage)
    bodied = opened(path, SIMULATORS["mujoco"])
    bodies, mass = rigid(bodied)
    physics, shapes = {}, {}
    for key in SIMULATORS:
        shapes[key], physics[key] = colliders(path, key, bodies)
    low, high = vertices[np.unique(faces)].min(axis=0), vertices[np.unique(faces)].max(axis=0)
    tags = record.get("tags") or {}
    painted = one_model_surfaces(library.root_from_environment() or library_files.default_root())
    return {"address": record["address"], "id": record["id"], "title": record.get("title") or record["id"],
            "words": list(tags.get("description") or []), "wikidata_class": list(tags.get("wikidata_class") or []),
            "vertices": vertices, "faces": faces, "face_material": face_material, "face_prim": face_prim,
            "prims": prims, "materials": [described(stage, name, painted) for name in materials],
            "face_look": _look.face_looks(stage, materials, face_material, face_uv),
            "box": [low.tolist(), high.tolist()], "size": (high - low).tolist(),
            "mass": mass, "bodies": bodies, "joints": joints(bodied, bodies),
            "colliders": shapes["mujoco"], "friction": friction(shapes["mujoco"], physics["mujoco"]),
            "payloads": shapes, "physics_materials": physics}
