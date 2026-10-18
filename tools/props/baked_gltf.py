"""A baked model's .gltf read whole (library/inside/bake.py writes it): one node, one primitive a map. A piece that fits
one picture set has one map; a generated piece too big for one is split into several (bake.Atlas `split`), each map
its own material and pictures. numpy and Pillow only, so the prop environment, the stages and the OpenUSD export read
it the same way.

    document, views = read(path)
    found = geometry(document, views)       # positions, normals, uvs, triangles over every map; "maps": each triangle's
    pictures = maps(document, path)         # [{role: picture file}] one a map, in the primitives' order
    colour, texels = base_colours(found, pictures)
"""
import json
import pathlib

import numpy as np
from PIL import Image

import glb_file

ROLES = ("base_color", "metal_roughness", "normal")


def read(path):
    """A .gltf with its .bin beside it, as glb_file's (document, list of each buffer view's bytes)."""
    document = json.loads(pathlib.Path(path).read_text())
    if len(document["buffers"]) != 1:
        raise ValueError(f"{path}: one buffer expected, found {len(document['buffers'])}")
    blob = (pathlib.Path(path).parent / document["buffers"][0]["uri"]).read_bytes()
    views = [blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
             for view in document["bufferViews"]]
    return document, views


def primitives(document):
    """The model's primitives, one a map: those of its one mesh."""
    if len(document["meshes"]) != 1:
        raise ValueError(f"a baked model is one mesh, found {len(document['meshes'])}")
    return document["meshes"][0]["primitives"]


def geometry(document, views):
    """Every map's positions, normals, texture coordinates and triangles joined into one mesh (each map's corners
    after the last's), with each triangle's map number (`maps`)."""
    parts = {"positions": [], "normals": [], "uvs": [], "triangles": [], "maps": []}
    corners = 0
    for number, primitive in enumerate(primitives(document)):
        attributes = primitive["attributes"]
        positions = glb_file.accessor_array(document, views, attributes["POSITION"]).astype(np.float64)
        triangles = glb_file.accessor_array(document, views, primitive["indices"]).reshape(-1, 3).astype(np.int64)
        parts["positions"].append(positions)
        parts["normals"].append(glb_file.accessor_array(document, views, attributes["NORMAL"]).astype(np.float64))
        parts["uvs"].append(glb_file.accessor_array(document, views, attributes["TEXCOORD_0"]).astype(np.float64))
        parts["triangles"].append(triangles + corners)
        parts["maps"].append(np.full(len(triangles), number, dtype=np.int64))
        corners += len(positions)
    return {key: np.concatenate(values) for key, values in parts.items()}


def maps(document, path):
    """Each map's baked pictures by role (base_color, metal_roughness, normal), the picture files they name, in the
    primitives' order."""
    found = []
    for primitive in primitives(document):
        material = document["materials"][primitive["material"]]
        references = {"base_color": material["pbrMetallicRoughness"].get("baseColorTexture"),
                      "metal_roughness": material["pbrMetallicRoughness"].get("metallicRoughnessTexture"),
                      "normal": material.get("normalTexture")}
        pictures = {}
        for role, reference in references.items():
            if reference is None:
                continue
            texture = document["textures"][reference["index"]]
            source = texture.get("extensions", {}).get("EXT_texture_webp", {}).get("source", texture.get("source"))
            pictures[role] = pathlib.Path(path).parent / document["images"][source]["uri"]
        found.append(pictures)
    return found


def base_colours(found, pictures):
    """Each triangle's baked base colour (sRGB 0..1) at its middle's texel of its own map's picture (glTF's v runs
    down the picture), and that texel: (colours, rows, columns, each triangle's picture size as (width, height))."""
    uv = found["uvs"][found["triangles"]].mean(axis=1) % 1.0
    colours = np.zeros((len(uv), 3))
    rows = np.zeros(len(uv), dtype=np.int64)
    columns = np.zeros(len(uv), dtype=np.int64)
    sizes = np.zeros((len(uv), 2), dtype=np.int64)
    for number, roles in enumerate(pictures):
        chosen = found["maps"] == number
        picture = np.asarray(Image.open(roles["base_color"]).convert("RGB"), dtype=np.float64) / 255
        height, width = picture.shape[:2]
        columns[chosen] = np.clip((uv[chosen, 0] * width).astype(int), 0, width - 1)
        rows[chosen] = np.clip((uv[chosen, 1] * height).astype(int), 0, height - 1)
        colours[chosen] = picture[rows[chosen], columns[chosen]]
        sizes[chosen] = (width, height)
    return colours, rows, columns, sizes
