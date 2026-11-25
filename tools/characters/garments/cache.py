"""The dressed person over its clip as one OpenUSD stage (metres, y up, RATE frames a second): the body and each
garment a Mesh whose points are sampled every clip frame (a point cache Blender reads as a mesh cache and Unreal
imports as a geometry cache), each garment with its panels' texture coordinates (`st`, face-varying: a seam's point
has its place on each panel it joins) and bound to its score_lib surface, referenced from the library's own
material.usda by its address. Score venv (pxr).
"""
import pathlib

import numpy as np

from tools.characters.garments import bands, details

TEXTURE_METRES = 0.5  # the cloth a library surface's texture covers once (its st 0..1)


def corner_uvs(record, flat=None):
    """Each triangle corner's texture coordinate from its flat panel (cm; `flat` each corner's when its triangles
    were cut, bands.corner_flat), in TEXTURE_METRES."""
    if flat is None:
        flat = np.asarray(record["flat"], dtype=float)[np.asarray(record["faces"])].reshape(-1, 2)
    return np.asarray(flat, dtype=float) / (100.0 * TEXTURE_METRES)


def mesh_at(stage, path, faces, frames, start):
    """A Mesh at `path` with `faces` and its points sampled at start, start + 1, ... (frames x points x 3)."""
    from pxr import UsdGeom, Vt
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray([3] * len(faces)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(np.asarray(faces, dtype=int).ravel().tolist()))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    points = mesh.CreatePointsAttr()
    for number, frame in enumerate(frames):
        points.Set(Vt.Vec3fArray.FromNumpy(np.asarray(frame, dtype=np.float32)), start + number)
    return mesh


def bound(stage, mesh, surface, library):
    """`mesh` (a mesh or a face subset of one) bound to its library surface, referenced from the fetched library
    (`library`/<kind>/<id>/<version>)."""
    from pxr import UsdShade
    kind, rest = surface["address"].split("/", 1)
    name, version = rest.split("@")
    material_file = pathlib.Path(library) / kind / name / version / "material.usda"
    if not material_file.is_file():
        raise SystemExit(f"{surface['address']}: not fetched into {library}")
    prim = stage.DefinePrim(f"/Outfit/Looks/{name}")
    prim.GetReferences().AddReference(str(material_file))
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(UsdShade.Material(prim))


def taped(stage, mesh, triangles, surface, library):
    """The garment's band triangles a subset of `mesh` bound to the bands' library surface (its tape)."""
    from pxr import UsdGeom, UsdShade, Vt
    subset = UsdGeom.Subset.Define(stage, mesh.GetPath().AppendChild("bands"))
    subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
    subset.CreateFamilyNameAttr(UsdShade.Tokens.materialBind)
    subset.CreateIndicesAttr(Vt.IntArray([int(triangle) for triangle in triangles]))
    bound(stage, subset, surface, library)


def marked(stage, record, garment, library, frames, body_points):
    """The garment's construction marks (details.py) as /Outfit/Garments/<name>_details over the clip, each mark's
    triangles bound to its library decal (the first by the mesh, the rest by face subsets)."""
    from pxr import Sdf, UsdGeom, UsdShade, Vt
    from tools.characters import garments
    made = details.laid(record, garment, library, frames, body_points, garments.THICKNESS_M)
    if made is None:
        return
    points, triangles, st, finish, surfaces = made
    mesh = mesh_at(stage, f"/Outfit/Garments/{garment['name']}_details", triangles, points, 0)
    uvs = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.faceVarying)
    uvs.Set(st.reshape(-1, 2).astype(np.float32).tolist())
    bound(stage, mesh, surfaces[0], library)
    for index, surface in enumerate(surfaces[1:], start=1):
        subset = UsdGeom.Subset.Define(stage, mesh.GetPath().AppendChild(f"mark{index}"))
        subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
        subset.CreateFamilyNameAttr(UsdShade.Tokens.materialBind)
        subset.CreateIndicesAttr(Vt.IntArray([int(triangle) for triangle in np.flatnonzero(finish == index)]))
        bound(stage, subset, surface, library)


def written(path, body, drape, records, outfit, library, rate):
    """outfit.usda: /Outfit/Body and /Outfit/Garments/<name>, every clip frame, garments bound to their surfaces. The
    stage, saved, for what is worn beside the garments to be added to."""
    from pxr import Sdf, Usd, UsdGeom
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/Outfit").GetPrim())
    UsdGeom.Xform.Define(stage, "/Outfit/Garments")
    UsdGeom.Scope.Define(stage, "/Outfit/Looks")
    first = drape[outfit["garments"][0]["name"]]
    start, count = int(body["clip_start"]), len(first)
    stage.SetTimeCodesPerSecond(rate)
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(count - 1)
    skin = mesh_at(stage, "/Outfit/Body", body["faces"], body["frames"][start:start + count], 0)
    bound(stage, skin, outfit["body surface"], library)
    for garment in outfit["garments"]:
        record = records[garment["name"]]
        faces, frames, flat = np.asarray(record["box"])[record["faces"]], drape[garment["name"]], None
        if "bands" in garment:
            banded = bands.cut(record, drape[f"{garment['name']}/sewn"], garment["bands"])
            faces, flat = banded["faces"], bands.corner_flat(record, banded["corners"])
            frames = bands.frames_with(frames, banded["made"], banded["weights"])
        mesh = mesh_at(stage, f"/Outfit/Garments/{garment['name']}", faces, frames, 0)
        uvs = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                                     UsdGeom.Tokens.faceVarying)
        uvs.Set(corner_uvs(record, flat).astype(np.float32).tolist())
        bound(stage, mesh, garment["surface"], library)
        if "bands" in garment:
            taped(stage, mesh, np.flatnonzero(banded["banded"]), garment["bands"]["surface"], library)
        marked(stage, record, garment, library, frames, body["frames"][start])
    stage.GetRootLayer().Save()
    return stage
