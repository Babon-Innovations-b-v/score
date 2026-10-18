"""A model asset's drawn meshes as arrays, read with pxr: points in the asset's frame, triangles, each corner's
texture coordinate, the faces of each finish (a GeomSubset per library surface) and the base colour picture each
face is painted from. The collision mesh is left out."""
import dataclasses

import numpy as np
from pxr import Usd, UsdGeom, UsdShade


@dataclasses.dataclass
class Drawn:
    """One drawn mesh: points (n, 3), triangles (m, 3), corner texture coordinates (m, 3, 2) or None, finishes
    {surface name: face indices} and pictures {surface name or "": base colour file}."""
    name: str
    points: np.ndarray
    triangles: np.ndarray
    corners_uv: np.ndarray | None
    finishes: dict
    pictures: dict


def fan(counts, indices):
    """Faces of any size as triangles, fanned from each face's first corner; also each triangle's face number."""
    triangles, faces, at = [], [], 0
    for face, count in enumerate(counts):
        for step in range(1, count - 1):
            triangles.append((at, at + step, at + step + 1))
            faces.append(face)
        at += count
    corners = np.array(triangles, dtype=np.int64).reshape(-1, 3)
    return np.asarray(indices, dtype=np.int64)[corners], corners, np.array(faces, dtype=np.int64)


def corner_uv(prim, triangles, corners):
    """Each triangle corner's texture coordinate, or None for a mesh with none."""
    primvar = UsdGeom.PrimvarsAPI(prim).GetPrimvar("st")
    if not primvar or primvar.Get() is None:
        return None
    values = np.asarray(primvar.Get(), dtype=float)
    indices = primvar.GetIndices()
    if indices:
        values = values[np.asarray(indices)]
    if primvar.GetInterpolation() == UsdGeom.Tokens.faceVarying:
        return values[corners]
    return values[triangles]


def base_colour(material):
    """The base colour picture file of a material, or None."""
    if not material:
        return None
    for shader in Usd.PrimRange(material.GetPrim()):
        if not shader.IsA(UsdShade.Shader) or shader.GetName() != "base_color":
            continue
        found = UsdShade.Shader(shader).GetInput("file")
        asset = found.Get() if found else None
        if asset is not None:
            return asset.resolvedPath or None
    return None


def finishes_of(mesh, faces):
    """{surface name: triangle numbers} of a mesh's finish subsets, and {surface name or "": base colour file}."""
    finishes, pictures = {}, {}
    whole = base_colour(UsdShade.MaterialBindingAPI(mesh.GetPrim()).ComputeBoundMaterial()[0])
    if whole:
        pictures[""] = whole
    for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh):
        face_set = np.asarray(subset.GetIndicesAttr().Get() or [], dtype=np.int64)
        name = subset.GetPrim().GetName()
        finishes[name] = np.nonzero(np.isin(faces, face_set))[0]
        picture = base_colour(UsdShade.MaterialBindingAPI(subset.GetPrim()).ComputeBoundMaterial()[0])
        if picture:
            pictures[name] = picture
    return finishes, pictures


def drawn(asset):
    """The asset's drawn meshes, each in the asset's own frame."""
    stage = Usd.Stage.Open(str(asset))
    transforms = UsdGeom.XformCache(Usd.TimeCode(0))
    found = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.Mesh) or prim.GetName() == "collision":
            continue
        mesh = UsdGeom.Mesh(prim)
        counts, indices, points = (mesh.GetFaceVertexCountsAttr().Get(), mesh.GetFaceVertexIndicesAttr().Get(),
                                   mesh.GetPointsAttr().Get())
        if not counts or points is None:
            continue
        triangles, corners, faces = fan(counts, indices)
        matrix = np.array(transforms.GetLocalToWorldTransform(prim))
        placed = np.asarray(points, dtype=float) @ matrix[:3, :3] + matrix[3, :3]
        finishes, pictures = finishes_of(mesh, faces)
        found.append(Drawn(prim.GetName(), placed, triangles, corner_uv(prim, triangles, corners), finishes, pictures))
    return found


def triangle_areas(points, triangles):
    """Each triangle's area (points of 2 or 3 coordinates)."""
    first, second, third = points[triangles[:, 0]], points[triangles[:, 1]], points[triangles[:, 2]]
    if points.shape[1] == 2:
        along, across = second - first, third - first
        return np.abs(along[:, 0] * across[:, 1] - along[:, 1] * across[:, 0]) / 2
    return np.linalg.norm(np.cross(second - first, third - first), axis=1) / 2
