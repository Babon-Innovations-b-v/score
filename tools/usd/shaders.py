"""The framework's own shaders: surfaces the library's flat UsdPreviewSurface cannot carry, each written as a
UsdPreviewSurface over a picture the framework bakes, so every USD reader (Blender's importer included) draws it.

    earth_face   the Earth seen in a place's sky: continents, deserts, ice and cloud from the game 2099's ink_earth
                 shader, baked by earth.py into a longitude-latitude picture on the ball's own uvs, lit by the place's
                 sun so its night side falls dark (score:shader "earth")

A built mesh painted with one of these surfaces (scene.bind_surface) is bound to /<place>/Looks/<surface> in place of
the library's flat /<place>/Library/<surface>, and still says its library surface in `score:surface`. Without the
stage's folder (a stage only in memory) the library's flat surface is bound instead.

The sun's disc in the sky is drawn here too (sun_discs): a ball along each of the record's unnamed sun lights (the
sky's sun; the earthshine and the moonlight are named), as wide as the game draws it, in the library's `sun_disc`.
"""
import math
import pathlib

import numpy as np
from pxr import Sdf, UsdShade

import earth

# How far out the sun's disc hangs: inside the views' reach (2000 m) and in front of the stars (1900 m, scene.py).
SUN_DISC_DISTANCE = 1880.0
# How wide the sun looks from the ground, in degrees (the game's sky.gd SUN_ACROSS_ON_THE_GROUND_DEGREES).
SUN_ACROSS_DEGREES = 1.51
EARTH_PICTURE = "earth_surface.png"
EARTH_WIDTH = 2048


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
                       ("score:from", "the game 2099's game/art/shaders/ink_earth.gdshader, baked by tools/usd/earth.py")):
        material.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
    return material


# Surface -> the function writing its framework shader.
LOOKS = {"earth_face": earth_look}


def look(stage, place, surface, out):
    """The framework shader for a surface, or None when the library's flat surface is its look."""
    if surface not in LOOKS or out is None:
        return None
    return LOOKS[surface](stage, place, out)


def sun_discs(stage, place, lights, sphere_prim):
    """A ball in the sky along each unnamed sun light (the sky's sun), as wide as the game draws it; how many.
    `sphere_prim(path, centre, radius)` builds and paints the ball (scene.py's builders)."""
    count = 0
    for entry in lights:
        if entry.get("type") != "sun" or entry.get("name") or float(entry.get("energy", 0.0)) <= 0.0:
            continue
        toward = np.asarray(entry["toward"], dtype=np.float64)
        centre = -toward / np.linalg.norm(toward) * SUN_DISC_DISTANCE
        radius = SUN_DISC_DISTANCE * math.sin(math.radians(SUN_ACROSS_DEGREES) / 2.0)
        prim = sphere_prim(f"/{place}/Sky/sun_disc_{count}", centre, radius)
        prim.GetPrim().CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(
            "the game 2099's game/world/sky/sky.gd:33-38,462,512 (the sun's disc hung along the light, "
            f"{SUN_ACROSS_DEGREES} degrees across from the ground), its light's own way: {entry.get('from', '')}")
        count += 1
    return count
