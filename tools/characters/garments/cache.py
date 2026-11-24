"""The dressed person over its clip as one OpenUSD stage (metres, y up, RATE frames a second): the body and each
garment a Mesh whose points are sampled every clip frame (a point cache Blender reads as a mesh cache and Unreal
imports as a geometry cache), each garment with its panels' texture coordinates (`st`, face-varying: a seam's point
has its place on each panel it joins) and bound to its score_lib surface, referenced from the library's own
material.usda by its address. Score venv (pxr).
"""
import pathlib

import numpy as np

TEXTURE_METRES = 0.5  # the cloth a library surface's texture covers once (its st 0..1)


def corner_uvs(record):
    """Each triangle corner's texture coordinate from its flat panel (cm), in TEXTURE_METRES."""
    return np.asarray(record["flat"], dtype=float)[np.asarray(record["faces"])].reshape(-1, 2) / (
        100.0 * TEXTURE_METRES)


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
    """`mesh` bound to its library surface, referenced from the fetched library (`library`/<kind>/<id>/<version>)."""
    from pxr import UsdShade
    kind, rest = surface["address"].split("/", 1)
    name, version = rest.split("@")
    material_file = pathlib.Path(library) / kind / name / version / "material.usda"
    if not material_file.is_file():
        raise SystemExit(f"{surface['address']}: not fetched into {library}")
    prim = stage.DefinePrim(f"/Outfit/Looks/{name}")
    prim.GetReferences().AddReference(str(material_file))
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(UsdShade.Material(prim))


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
        mesh = mesh_at(stage, f"/Outfit/Garments/{garment['name']}", np.asarray(record["box"])[record["faces"]],
                       drape[garment["name"]], 0)
        uvs = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                                     UsdGeom.Tokens.faceVarying)
        uvs.Set(corner_uvs(record).astype(np.float32).tolist())
        bound(stage, mesh, garment["surface"], library)
    stage.GetRootLayer().Save()
    return stage
