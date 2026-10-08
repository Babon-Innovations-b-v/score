"""A world's own glTF model (a gameplay object the game places from code: a console, a bed, a rocket) as one OpenUSD
asset, for a place's `objects` in its scene record (tools/usd/scene.py).

    asset(glb, out_file, textures) -> the asset's box (low, high) in metres, y up

Every mesh of the file becomes a UsdGeomMesh with its node's transform baked in, and every material a UsdPreviewSurface
from the file's own base colour (its texture, else its factor), roughness, metal and emission. These models are not
labelled by parts, so a part carries no library surface: the model's own materials are what is drawn.
"""
import pathlib

import numpy as np
import trimesh
from PIL import Image
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdShade, Vt


def flat_rgb(values, fallback):
    """A colour factor as three floats in 0..1 (glTF factors may be bytes)."""
    if values is None:
        return fallback
    found = np.asarray(values, dtype=np.float64)[:3]
    return tuple(float(value) for value in (found / 255.0 if found.max() > 1.0 else found))


def texture_file(picture, textures, name):
    """A material's picture written once as PNG; its path relative to the asset file."""
    textures.mkdir(parents=True, exist_ok=True)
    target = textures / f"{name}.png"
    if not target.exists():
        picture.convert("RGBA" if picture.mode in ("RGBA", "LA", "P") else "RGB").save(target)
    return f"./textures/{target.name}"


def preview_material(stage, path, material, textures, name, glows=False):
    """A UsdPreviewSurface from a trimesh PBR material: base colour (texture or factor), roughness, metal, emission
    (its own, or its base colour when the model is a glowing part: `glows`)."""
    surface = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    picture = getattr(material, "baseColorTexture", None)
    if picture is None and getattr(material, "image", None) is not None:
        picture = material.image
    if picture is not None:
        reader = UsdShade.Shader.Define(stage, f"{path}/uv")
        reader.CreateIdAttr("UsdPrimvarReader_float2")
        reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
        texture = UsdShade.Shader.Define(stage, f"{path}/base_color")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(texture_file(picture, textures, name))
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
            reader.CreateOutput("result", Sdf.ValueTypeNames.Float2))
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
        if glows:
            shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(texture.GetOutput("rgb"))
    else:
        colour = flat_rgb(getattr(material, "baseColorFactor", None) or getattr(material, "main_color", None),
                          (0.6, 0.6, 0.6))
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*colour))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(
        float(getattr(material, "roughnessFactor", None) if getattr(material, "roughnessFactor", None) is not None
              else 0.7))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(
        float(getattr(material, "metallicFactor", None) or 0.0))
    emission = flat_rgb(getattr(material, "emissiveFactor", None), (0.0, 0.0, 0.0))
    if max(emission) > 0.0:
        shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*emission))
    surface.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return surface


def mesh_prim(stage, path, mesh):
    """One baked mesh: triangles, smooth normals and its texture coordinates when it has them."""
    prim = UsdGeom.Mesh.Define(stage, path)
    points = np.asarray(mesh.vertices, dtype=np.float32)
    prim.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
    prim.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(mesh.faces), 3, dtype=np.int32)))
    prim.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(mesh.faces, dtype=np.int32).reshape(-1)))
    prim.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(mesh.vertex_normals, dtype=np.float32)))
    prim.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    uv = getattr(mesh.visual, "uv", None)
    if uv is not None and len(uv) == len(points):
        UsdGeom.PrimvarsAPI(prim).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
            Vt.Vec2fArray.FromNumpy(np.asarray(uv, dtype=np.float32)))
    prim.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    prim.CreateDoubleSidedAttr(True)
    prim.CreateExtentAttr([Gf.Vec3f(*map(float, points.min(axis=0))), Gf.Vec3f(*map(float, points.max(axis=0)))])
    return prim


def asset(glb, out_file, textures):
    """The glTF file as one USD asset at out_file (its textures under `textures`, beside it); its box (low, high). A
    glowing part (a screen's or a lamp's lens, its file named `*_glow`) gives off its own colour."""
    scene = trimesh.load(str(glb), force="scene", process=False)
    stage = Usd.Stage.CreateNew(str(out_file))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    name = pathlib.Path(out_file).stem
    root = UsdGeom.Xform.Define(stage, f"/{name}")
    stage.SetDefaultPrim(root.GetPrim())
    Usd.ModelAPI(root).SetKind(Kind.Tokens.component)
    UsdGeom.Scope.Define(stage, f"/{name}/Looks")
    materials = {}
    for number, (node, geometry_name) in enumerate(
            (node, scene.graph[node][1]) for node in scene.graph.nodes_geometry):
        transform = scene.graph[node][0]
        mesh = scene.geometry[geometry_name].copy()
        mesh.apply_transform(transform)
        prim = mesh_prim(stage, f"/{name}/mesh_{number}", mesh)
        material = getattr(mesh.visual, "material", None)
        if material is None:
            continue
        key = id(scene.geometry[geometry_name].visual.material)
        if key not in materials:
            materials[key] = preview_material(stage, f"/{name}/Looks/look_{len(materials)}", material, textures,
                                              f"{name}_{len(materials)}", pathlib.Path(glb).stem.endswith("_glow"))
        UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(materials[key])
    stage.GetRootLayer().Save()
    low, high = scene.bounds
    return np.asarray(low, dtype=np.float64), np.asarray(high, dtype=np.float64)
