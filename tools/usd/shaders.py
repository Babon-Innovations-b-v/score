"""The framework's own shaders: surfaces the library's flat UsdPreviewSurface cannot carry, each written as a
UsdPreviewSurface over a picture the framework bakes, so every USD reader (Blender's importer included) draws it.

    earth_face   the Earth seen in a place's sky: the real planet, NASA's Blue Marble with NASA's cloud cover over
                 it, baked by earth.py into a longitude-latitude picture on the ball's own uvs, lit by the place's
                 sun so its night side falls dark (score:shader "earth")

    <surface>    a room shell's library surface (score/stages/surface_tiles: make_tiles.py bakes its recipe flat as a
                 repeating tile), drawn with the tile's colour, roughness, metal and normal pictures, repeated every
                 tile's side along the mesh's own uvs in metres (score:shader "library tile")

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
# A library tile's pictures by role, as make_tiles.py writes them (<surface>_<role>.png).
TILE_ROLES = ("base_color", "metal_roughness", "normal")


def look(stage, place, surface, out, tiles=None):
    """The framework shader for a surface: its own (LOOKS), else its library tile where `tiles` (a surface-tiles
    output, make_tiles.py's pictures and tiles.json) holds one; None when the library's flat surface is its look."""
    if out is None:
        return None
    if surface in LOOKS:
        return LOOKS[surface](stage, place, out)
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
