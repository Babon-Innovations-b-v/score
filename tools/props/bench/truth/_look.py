"""Each truth triangle's look as NVIDIA's material draws it (#172): its base colour (linear RGB), metalness and
roughness read where the triangle lies on its maps, and each material's class.

    corner_uvs(prim, triangles, polygon, slots)              -> (T, 3, 2) each corner's texture coordinates (NaN: none)
    face_looks(stage, materials, face_material, face_uv)     -> {"albedo" (T, 3), "metal" (T,), "roughness" (T,),
                                                                "class" (T,)}
    material_class(stage, path)                              -> the material's class (sim.py's classes) or None

A material is read through its UsdPreviewSurface (the universal surface output): an input's constant, else the
UsdUVTexture it is wired to (its channel, scale and bias, an sRGB map made linear), else the input's fallback; a
material with no preview surface is read through its OmniPBR shader's inputs (the constants and the diffuse and ORM
maps). A triangle's value from a map is the mean of SAMPLES points inside it (nearest texel, the map repeated); a
triangle with no material or no coordinates where its look needs them is NaN, never a guess.
"""
import functools

import numpy as np
from pxr import Sdf, UsdGeom, UsdShade

# Barycentric points a triangle's map value is read at: its middle and one toward each corner.
SAMPLES = np.array([[1 / 3, 1 / 3, 1 / 3], [2 / 3, 1 / 6, 1 / 6], [1 / 6, 2 / 3, 1 / 6], [1 / 6, 1 / 6, 2 / 3]])
# UsdPreviewSurface's own fallbacks (its spec).
FALLBACK = {"diffuseColor": (0.18, 0.18, 0.18), "metallic": 0.0, "roughness": 0.5}
CHANNEL = {"r": 0, "g": 1, "b": 2, "a": 3}
# OmniPBR's ORM map: occlusion, roughness, metalness in r, g, b.
ORM_CHANNEL = {"roughness": 1, "metallic": 2}
OMNI = {"diffuseColor": "diffuse_color_constant", "metallic": "metallic_constant",
        "roughness": "reflection_roughness_constant"}
OMNI_DEFAULT = {"diffuseColor": (0.2, 0.2, 0.2), "metallic": 0.0, "roughness": 0.5}


def corner_uvs(prim, triangles, polygon, slots):
    """Each triangle corner's texture coordinates from the mesh's `st` primvar (face-varying by slot, vertex by
    point, uniform by polygon, constant), NaN where it has none."""
    primvar = UsdGeom.PrimvarsAPI(prim).GetPrimvar("st")
    found = np.full((len(triangles), 3, 2), np.nan)
    if not primvar or not primvar.HasValue():
        return found
    values = np.asarray(primvar.ComputeFlattened() or [], dtype=float).reshape(-1, 2)
    kind = primvar.GetInterpolation()
    index = {UsdGeom.Tokens.faceVarying: slots, UsdGeom.Tokens.vertex: triangles, UsdGeom.Tokens.varying: triangles,
             UsdGeom.Tokens.uniform: np.repeat(polygon[:, None], 3, 1),
             UsdGeom.Tokens.constant: np.zeros_like(slots)}.get(kind)
    if index is None or not len(values) or index.max(initial=-1) >= len(values):
        return found
    return values[index]


@functools.lru_cache(maxsize=16)
def texels(path):
    """A map's texels as stored (H, W, 4; a one-channel map's alpha 1) and the value its full level is: they are made
    floats, and linear, only where a triangle reads them (`sampled`): the whole of a 4K map made float and linear took
    the tool organizer cart's read past a minute (#159)."""
    from PIL import Image
    with Image.open(path) as picture:
        wide = picture.mode in ("I;16", "I;16B", "I", "F")
        found = np.asarray(picture.convert("RGBA") if not wide else picture)
    full = 65535.0 if wide else 255.0
    if found.ndim == 2:
        found = np.stack([found, found, found, np.full_like(found, full)], 2)
    return found, full


def sampled(map_texels, uvs, srgb=False):
    """The mean texel (4,) per triangle of `uvs` (T, 3, 2) over SAMPLES, the map repeated, v up, each texel as floats
    0..1, an sRGB map's colour made linear (its alpha left as it is) before the mean; NaN for a triangle with no
    coordinates. `map_texels` is texels'."""
    stored, full = map_texels
    missing = np.isnan(uvs).any(axis=(1, 2))
    points = np.einsum("sk,tkc->tsc", SAMPLES, np.nan_to_num(uvs))
    high, wide = stored.shape[:2]
    column = np.floor(np.mod(points[..., 0], 1.0) * wide).astype(int).clip(0, wide - 1)
    row = np.floor((1.0 - np.mod(points[..., 1], 1.0)) * high).astype(int).clip(0, high - 1)
    read = stored[row, column].astype(float) / full
    if srgb:
        colour = read[..., :3]
        read[..., :3] = np.where(colour <= 0.04045, colour / 12.92, ((colour + 0.055) / 1.055) ** 2.4)
    found = read.mean(1)
    found[missing] = np.nan
    return found


def asset_path(value):
    """An asset input's resolved file path, None when it names none or does not resolve."""
    if not isinstance(value, Sdf.AssetPath):
        return None
    return value.resolvedPath or None


def wired(shader_input):
    """(the UsdUVTexture shader an input is wired to, its output name), or None."""
    if not shader_input or not shader_input.HasConnectedSource():
        return None
    source, output, _ = shader_input.GetConnectedSource()
    shader = UsdShade.Shader(source.GetPrim())
    return (shader, output) if shader and shader.GetIdAttr().Get() == "UsdUVTexture" else None


def preview_value(shader, name, uvs):
    """One UsdPreviewSurface input per triangle (T, channels): its map's channel(s) through scale and bias, else its
    constant, else its fallback."""
    channels = 3 if name == "diffuseColor" else 1
    shader_input = shader.GetInput(name)
    texture = wired(shader_input)
    if texture is None:
        value = shader_input.Get() if shader_input and shader_input.Get() is not None else FALLBACK[name]
        return np.tile(np.asarray(value, dtype=float).reshape(-1)[:channels], (len(uvs), 1))
    texture, output = texture
    path = asset_path(texture.GetInput("file").Get() if texture.GetInput("file") else None)
    if path is None:
        return np.full((len(uvs), channels), np.nan)
    space = texture.GetInput("sourceColorSpace")
    srgb = name == "diffuseColor" and (space.Get() if space else "auto") != "raw"
    found = sampled(texels(path), uvs, srgb)
    scale = np.asarray(texture.GetInput("scale").Get() if texture.GetInput("scale") else (1, 1, 1, 1), dtype=float)
    bias = np.asarray(texture.GetInput("bias").Get() if texture.GetInput("bias") else (0, 0, 0, 0), dtype=float)
    found = found * scale + bias
    picked = [0, 1, 2] if output == "rgb" else [CHANNEL.get(output, 0)]
    return found[:, picked] if channels == len(picked) else np.repeat(found[:, picked[:1]], channels, 1)


def omni_value(shader, name, uvs):
    """One look input per triangle through an OmniPBR shader: the diffuse map (sRGB) or the ORM map's channel where
    one is set, else the shader's constant, else OmniPBR's default."""
    channels = 3 if name == "diffuseColor" else 1
    if name == "diffuseColor":
        path = asset_path(shader.GetInput("diffuse_texture").Get() if shader.GetInput("diffuse_texture") else None)
        if path:
            return sampled(texels(path), uvs, True)[:, :3]
    else:
        enabled = shader.GetInput("enable_ORM_texture")
        path = asset_path(shader.GetInput("ORM_texture").Get() if shader.GetInput("ORM_texture") else None)
        if path and enabled and enabled.Get():
            return sampled(texels(path), uvs)[:, [ORM_CHANNEL[name]]]
    constant = shader.GetInput(OMNI[name])
    value = constant.Get() if constant and constant.Get() is not None else OMNI_DEFAULT[name]
    return np.tile(np.asarray(value, dtype=float).reshape(-1)[:channels], (len(uvs), 1))


def surface_shader(material):
    """(the material's shader, its reader): its UsdPreviewSurface, else its OmniPBR (mdl) shader, else None."""
    source = material.ComputeSurfaceSource()[0]
    if source and source.GetIdAttr().Get() == "UsdPreviewSurface":
        return source, preview_value
    source = material.ComputeSurfaceSource("mdl")[0]
    return (source, omni_value) if source else None


def face_looks(stage, materials, face_material, face_uv):
    """{"albedo" (T, 3) linear, "metal" (T,), "roughness" (T,), "class" (T,)}: each triangle's look on its material,
    NaN where it has none, its material none, or a map it needs has no coordinates; its material's class (None:
    none)."""
    count = len(face_material)
    albedo, metal, roughness = np.full((count, 3), np.nan), np.full(count, np.nan), np.full(count, np.nan)
    for number, path in enumerate(materials):
        held = np.flatnonzero(np.asarray(face_material) == number)
        found = surface_shader(UsdShade.Material(stage.GetPrimAtPath(path)))
        if not len(held) or found is None:
            continue
        shader, read = found
        uvs = face_uv[held]
        albedo[held] = read(shader, "diffuseColor", uvs)
        metal[held] = read(shader, "metallic", uvs)[:, 0]
        roughness[held] = read(shader, "roughness", uvs)[:, 0]
    classes = np.array([material_class(stage, path) for path in materials] + [None], dtype=object)
    return {"albedo": albedo, "metal": metal, "roughness": roughness, "class": classes[np.asarray(face_material)]}


def material_class(stage, path):
    """The material's class as sim.py reads a surface adopted from NVIDIA (its name m_<opacity>__<class>__..., metal
    with an aluminium base aluminium), None when its name names none."""
    from score.stages.place_build.maker import sim
    prim = stage.GetPrimAtPath(path)
    base = prim.GetAttribute("omni:simready:nonvisual:base")
    return sim.surface_class({"material": prim.GetName(),
                              "nonvisual": {"base": (base.Get() if base and base.HasValue() else "") or ""}})
