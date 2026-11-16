"""A glTF-only library entry made layable (#128, the camp pilot: many made models hold only a .glb): its meshes, each
where the glTF's node tree sets it, joined into one USD mesh `geo` (y up, metres, as glTF is), each of its materials
a named part (a GeomSubset, as the kit pieces' colour regions are), so the placing agent wears each part a library
surface. Geometry only: the glTF's own finish is left behind, as the library rule asks. Converted once, beside the
glTF in the place's assets.

    converted(path) -> <path>.usdc
"""
import pathlib
import re

from pxr import Gf, Usd, UsdGeom, Vt


def part_name(material, number):
    """A USD-safe part name of a glTF material's name (`part_<n>` for one with none)."""
    name = re.sub(r"[^A-Za-z0-9_]", "_", getattr(material, "name", None) or "")
    return name if name and not name[0].isdigit() else f"part_{number}"


def meshes(path):
    """[(part name, points (n x 3), triangles (m x 3))] of the glTF at `path`, each in the scene's frame."""
    import trimesh
    scene = trimesh.load(str(path), force="scene")
    found = []
    for number, node in enumerate(scene.graph.nodes_geometry):
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry]
        if not hasattr(mesh, "faces") or not len(mesh.faces):
            continue
        material = getattr(getattr(mesh, "visual", None), "material", None)
        found.append((part_name(material, number), trimesh.transform_points(mesh.vertices, transform), mesh.faces))
    if not found:
        raise ValueError(f"{path}: no mesh in this glTF")
    return found


def converted(path):
    """The glTF at `path` as one USD mesh with a part a material, written once beside it; its path."""
    path = pathlib.Path(path)
    target = path.with_suffix(".usdc")
    if target.exists():
        return target
    stage = Usd.Stage.CreateNew(str(target))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/model")
    stage.SetDefaultPrim(root.GetPrim())
    points, triangles, parts = [], [], {}
    for name, mesh_points, mesh_triangles in meshes(path):
        first = len(triangles)
        triangles += [[int(index) + len(points) for index in triangle] for triangle in mesh_triangles]
        points += [Gf.Vec3f(*map(float, point)) for point in mesh_points]
        parts.setdefault(name, []).extend(range(first, len(triangles)))
    mesh = UsdGeom.Mesh.Define(stage, "/model/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray(points))
    mesh.CreateFaceVertexCountsAttr([3] * len(triangles))
    mesh.CreateFaceVertexIndicesAttr([index for triangle in triangles for index in triangle])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    for name, faces in parts.items():
        UsdGeom.Subset.CreateGeomSubset(mesh, name, UsdGeom.Tokens.face, faces, "materialBind",
                                        UsdGeom.Tokens.nonOverlapping)
    stage.GetRootLayer().Save()
    return target
