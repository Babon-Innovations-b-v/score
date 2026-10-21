"""The framework's own shaders: surfaces the library's flat UsdPreviewSurface cannot carry, each written as a
UsdPreviewSurface over a picture the framework bakes, so every USD reader (Blender's importer included) draws it.

    earth_face   the Earth seen in a place's sky: the real planet, NASA's Blue Marble with NASA's cloud cover over
                 it, baked by earth.py into a longitude-latitude picture on the ball's own uvs, lit by the place's
                 sun so its night side falls dark (score:shader "earth")

A built mesh painted with this surface (scene.bind_surface) is bound to /<place>/Looks/<surface> in place of
the library's flat /<place>/Library/<surface>, and still says its library surface in `score:surface`. Without the
stage's folder (a stage only in memory) the library's flat surface is bound instead.
"""
import pathlib

from pxr import Sdf, UsdShade

import earth

EARTH_PICTURE = "earth_surface.png"
EARTH_WIDTH = 4096


def earth_look(stage, place, out):
    """The Earth's surface material under /<place>/Looks, its picture baked once into the stage's textures."""
    path = f"/{place}/Looks/earth_face"
    material = UsdShade.Material(stage.GetPrimAtPath(path))
    if material:
        return material
    earth.write(pathlib.Path(out) / "assets/textures" / EARTH_PICTURE, EARTH_WIDTH)
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    reader = UsdShade.Shader.Define(stage, f"{path}/uv")
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    texture = UsdShade.Shader.Define(stage, f"{path}/picture")
    texture.CreateIdAttr("UsdUVTexture")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"../assets/textures/{EARTH_PICTURE}")
    texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
        reader.CreateOutput("result", Sdf.ValueTypeNames.Float2))
    texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    for key, value in (("score:shader", "earth"),
                       ("score:from", "NASA Visible Earth: Blue Marble Next Generation (July 2004) and its cloud cover, "
                                     "baked by tools/usd/earth.py")):
        material.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
    return material


# Surface -> the function writing its framework shader.
LOOKS = {"earth_face": earth_look}


def look(stage, place, surface, out):
    """The framework shader for a surface: its own (LOOKS); None when the library's flat surface is its look."""
    if out is None or surface not in LOOKS:
        return None
    return LOOKS[surface](stage, place, out)
