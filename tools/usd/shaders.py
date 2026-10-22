"""The framework's own shaders: surfaces the library's flat UsdPreviewSurface cannot carry, each written as a
UsdPreviewSurface over a picture the framework bakes, so every USD reader (Blender's importer included) draws it.

    <surface>    a room shell's library surface (score/stages/surface_tiles: make_tiles.py bakes its recipe flat as a
                 repeating tile), drawn with the tile's colour, roughness, metal and normal pictures, repeated every
                 tile's side along the mesh's own uvs in metres (score:shader "library tile")

A built mesh painted with one of these surfaces (scene.bind_surface) is bound to /<place>/Looks/<surface> in place of
the library's flat /<place>/Library/<surface>, and still says its library surface in `score:surface`. Without the
stage's folder (a stage only in memory) the library's flat surface is bound instead.
"""
import pathlib

from pxr import Sdf, UsdShade

# A library tile's pictures by role, as make_tiles.py writes them (<surface>_<role>.png).
TILE_ROLES = ("base_color", "metal_roughness", "normal")


def look(stage, place, surface, out, tiles=None):
    """The framework shader for a surface: its library tile where `tiles` (a surface-tiles
    output, make_tiles.py's pictures and tiles.json) holds one; None when the library's flat surface is its look."""
    if out is None:
        return None
    if tiles is not None and surface in tile_record(tiles):
        return tile_look(stage, place, surface, out, tiles)
    return None


def tile_record(tiles):
    """{surface: {"metres", "side"}} of a surface-tiles output."""
    import json
    return json.loads((pathlib.Path(tiles) / "tiles.json").read_text())


def tile_look(stage, place, surface, out, tiles):
    """A library surface drawn with its tile (make_tiles.py: its recipe baked flat and made to repeat) under
    /<place>/Looks/<surface>, its pictures copied once into the stage's textures, repeated every `metres` along the
    mesh's own uvs (in metres, scene.mesh_prim) by a UsdTransform2d."""
    import shutil
    path = f"/{place}/Looks/{surface}"
    material = UsdShade.Material(stage.GetPrimAtPath(path))
    if material:
        return material
    metres = float(tile_record(tiles)[surface]["metres"])
    textures = pathlib.Path(out) / "assets/textures"
    textures.mkdir(parents=True, exist_ok=True)
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    reader = UsdShade.Shader.Define(stage, f"{path}/uv")
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    repeat = UsdShade.Shader.Define(stage, f"{path}/repeat")
    repeat.CreateIdAttr("UsdTransform2d")
    repeat.CreateInput("in", Sdf.ValueTypeNames.Float2).ConnectToSource(
        reader.CreateOutput("result", Sdf.ValueTypeNames.Float2))
    repeat.CreateInput("scale", Sdf.ValueTypeNames.Float2).Set((1.0 / metres, 1.0 / metres))
    coordinates = repeat.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    for role in TILE_ROLES:
        name = f"tile_{place}_{surface}_{role}.png"
        shutil.copy2(pathlib.Path(tiles) / f"{surface}_{role}.png", textures / name)
        texture = UsdShade.Shader.Define(stage, f"{path}/{role}")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"../assets/textures/{name}")
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(coordinates)
        texture.CreateInput("wrapS", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("wrapT", Sdf.ValueTypeNames.Token).Set("repeat")
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB" if role == "base_color" else "raw")
        tile_channel(shader, texture, role)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    for key, value in (("score:shader", "library tile"), ("score:surface", surface),
                       ("score:from", "tools/props/library/inside/make_tiles.py: the library recipe baked flat")):
        material.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
    return material


def tile_channel(shader, texture, role):
    """A tile picture wired into the surface: base colour, roughness (green) and metal (blue), or the normal map."""
    if role == "base_color":
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
    elif role == "metal_roughness":  # glTF packs roughness in green and metal in blue
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).ConnectToSource(
            texture.CreateOutput("g", Sdf.ValueTypeNames.Float))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).ConnectToSource(
            texture.CreateOutput("b", Sdf.ValueTypeNames.Float))
    else:
        texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set((2.0, 2.0, 2.0, 1.0))
        texture.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set((-1.0, -1.0, -1.0, 0.0))
        shader.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(
            texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))

