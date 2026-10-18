"""A place's web copy for the viewer (`serve.py`): its OpenUSD stage as one compressed glTF binary, and beside it what
three.js needs that glTF does not carry (the lights, the sky, the scene record's cameras, each object's box).

    systemd-run --user --scope -q -p MemoryMax=16G .venv/bin/python tools/review/viewer/export.py <place> \
        [--stage <stage.usda>] [--stages ~/.farm-factory-props/work/usd-r3] [--out ~/.farm-factory-props/work/web]

The stage is read with usd-core at its first moment, so a character stands in its first pose (UsdSkel skins its
meshes there) and a light the motion stage switches shines as it does then. Every mesh a renderer draws is written
(purpose default or render, visible), whole: nothing is simplified. Its UsdPreviewSurface becomes a glTF metal-rough
material (the baked colour, the roughness and metalness channels, the normal map, the glow), named after its surface
(a part's GeomSubset name, else its material's), so the viewer names what is under the mouse. What the export leaves
out (another kind of shape, a point instancer) it counts in the sidecar's `left_out`.

gltfpack (meshoptimizer, run through npx at a pinned version) then merges the meshes by material and compresses them
with meshopt (EXT_meshopt_compression), positions kept as floats: quantized to 16 bits over a place whose far ground
ball is 440 m across, a gently sloping sheet steps in 7 mm terraces through the floor it lies on (the greenhouse's
tarps, 2026-10-11). Normals and texture coordinates are quantized as gltfpack does. The pictures go in at web size
(at most TEXTURE_SIZE pixels a side, JPEG, or PNG where they hold see-through parts), so the copy opens fast. Out:
`<out>/<place>/<place>.glb` and `<place>.json` (lights, sky, cameras, boxes, counts). Nothing it makes is committed.
"""
import argparse
import json
import math
import pathlib
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "usd"))
import scene as scene_record  # noqa: E402  (tools/usd)

GLTFPACK = "gltfpack@0.22.0"
TEXTURE_SIZE = 2048
JPEG_QUALITY = 88
# A UsdGeom.Sphere (a place's far ground ball) drawn as a latitude-longitude mesh this many steps round.
SPHERE_SEGMENTS = 256
STAGES = pathlib.Path.home() / ".farm-factory-props/work/usd-r3"
OUT = pathlib.Path.home() / ".farm-factory-props/work/web"
# Blender's reading of the stage's lights (tools/blender/inside/usd_views.py): a sphere light's watts its intensity
# times pi, a distant light's strength its intensity times 4. three.js wants a point light's candela (watts over 4 pi,
# the same light per steradian) and a directional light's lux (the same irradiance), so the balance stays Blender's.
CANDELA_PER_INTENSITY = math.pi / (4 * math.pi)
LUX_PER_INTENSITY = 4.0
GLTF_FLOAT, GLTF_UINT = 5126, 5125
TRANSFORM = "KHR_texture_transform"
ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER = 34962, 34963


def drawn(prim, time):
    """Whether a renderer draws this prim: a mesh or a sphere of purpose default or render, visible at the time."""
    from pxr import UsdGeom
    imageable = UsdGeom.Imageable(prim)
    shown = imageable.ComputePurpose() in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render)
    return ((prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Sphere)) and shown
            and imageable.ComputeVisibility(time) != UsdGeom.Tokens.invisible)


def fan(counts):
    """Each polygon as a triangle fan: (triangles, 3) corner numbers into faceVertexIndices, and each one's face."""
    counts = np.asarray(counts, dtype=np.int64)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    per_face = np.maximum(counts - 2, 0)
    faces = np.repeat(np.arange(len(counts)), per_face)
    step = np.arange(per_face.sum()) - np.repeat(np.cumsum(per_face) - per_face, per_face)
    first = starts[faces]
    return np.column_stack([first, first + step + 1, first + step + 2]), faces


def per_corner(values, interpolation, indices, corner_faces):
    """A primvar's values at every corner of the mesh, whatever its interpolation."""
    values = np.asarray(values, dtype=np.float64)
    if interpolation in ("vertex", "varying"):
        return values[indices]
    if interpolation == "faceVarying":
        return values
    if interpolation == "uniform":
        return values[corner_faces]
    return np.repeat(values.reshape(1, -1), len(indices), axis=0)


def skins(stage):
    """Every skinned mesh of the stage by its path: (its skeleton's query, its skinning query)."""
    from pxr import Usd, UsdSkel
    cache, found = UsdSkel.Cache(), {}
    for prim in stage.Traverse():
        if not prim.IsA(UsdSkel.Root):
            continue
        cache.Populate(UsdSkel.Root(prim), Usd.PrimDefaultPredicate)
        for binding in cache.ComputeSkelBindings(UsdSkel.Root(prim), Usd.PrimDefaultPredicate):
            skeleton = cache.GetSkelQuery(binding.GetSkeleton())
            for target in binding.GetSkinningTargets():
                if target.HasJointInfluences():
                    found[target.GetPrim().GetPath()] = (skeleton, target)
    return found


def skinned_points(prim, skinned, time):
    """A skinned mesh's points at the time, posed by its skeleton, in the stage's frame ((count, 4), w = 1), or None
    for a mesh no skeleton moves."""
    from pxr import UsdGeom
    if prim.GetPath() not in skinned:
        return None
    skeleton, query = skinned[prim.GetPath()]
    points = UsdGeom.Mesh(prim).GetPointsAttr().Get(time)
    if not query.ComputeSkinnedPoints(skeleton.ComputeSkinningTransforms(time), points, time):
        raise RuntimeError(f"{prim.GetPath()}: UsdSkel could not skin its points")
    world = np.array(UsdGeom.Xformable(skeleton.GetPrim()).ComputeLocalToWorldTransform(time))
    return np.column_stack([np.asarray(points, dtype=np.float64), np.ones(len(points))]) @ world


def world_points(prim, skinned, time):
    """A mesh's points in the stage's frame at the time ((count, 4), w = 1) and whether that frame mirrors it. USD's
    matrices act on row vectors."""
    from pxr import UsdGeom
    posed = skinned_points(prim, skinned, time)
    if posed is not None:
        return posed, False
    world = np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(time))
    points = np.asarray(UsdGeom.Mesh(prim).GetPointsAttr().Get(time), dtype=np.float64)
    return np.column_stack([points, np.ones(len(points))]) @ world, np.linalg.det(world[:3, :3]) < 0


def mesh_corners(prim, skinned, time):
    """A mesh at every corner of its triangles: positions, normals (or None), texcoords (or None), the triangles'
    corners and each triangle's face; None for a mesh with no faces."""
    from pxr import UsdGeom
    mesh = UsdGeom.Mesh(prim)
    counts = mesh.GetFaceVertexCountsAttr().Get(time)
    indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(time) or [], dtype=np.int64)
    if counts is None or not len(indices):
        return None
    points, mirrored = world_points(prim, skinned, time)
    triangles, faces = fan(counts)
    corner_faces = np.repeat(np.arange(len(counts)), np.asarray(counts, dtype=np.int64))
    if (mesh.GetOrientationAttr().Get() == UsdGeom.Tokens.leftHanded) != mirrored:
        triangles = triangles[:, ::-1]
    return {"positions": points[indices, :3], "normals": world_normals(prim, indices, corner_faces, time),
            "texcoords": texcoords(prim, indices, corner_faces, time), "triangles": triangles, "faces": faces}


def sphere_corners(prim, time):
    """A UsdGeom.Sphere as a latitude-longitude mesh (SPHERE_SEGMENTS round, half as many pole to pole) in
    mesh_corners's form, its points and normals in the stage's frame."""
    from pxr import UsdGeom
    radius = float(UsdGeom.Sphere(prim).GetRadiusAttr().Get(time))
    rows, columns = SPHERE_SEGMENTS // 2 + 1, SPHERE_SEGMENTS + 1
    around, down = np.meshgrid(np.linspace(0, 2 * np.pi, columns), np.linspace(0, np.pi, rows))
    unit = np.stack([np.sin(down) * np.cos(around), np.cos(down), -np.sin(down) * np.sin(around)], -1).reshape(-1, 3)
    world = np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(time))
    row, column = np.meshgrid(np.arange(rows - 1), np.arange(columns - 1), indexing="ij")
    first = (row * columns + column).ravel()
    triangles = np.concatenate([np.column_stack([first, first + columns, first + columns + 1]),
                                np.column_stack([first, first + columns + 1, first + 1])])
    if np.linalg.det(world[:3, :3]) < 0:
        triangles = triangles[:, ::-1]
    normals = unit @ np.linalg.inv(world[:3, :3]).T
    return {"positions": (np.column_stack([unit * radius, np.ones(len(unit))]) @ world)[:, :3],
            "normals": normals / np.linalg.norm(normals, axis=1, keepdims=True),
            "texcoords": np.column_stack([around.ravel() / (2 * np.pi), down.ravel() / np.pi]),
            "triangles": triangles, "faces": np.arange(len(triangles))}


def world_normals(prim, indices, corner_faces, time):
    """A mesh's authored normals at every corner, turned into the stage's frame, or None when it has none."""
    from pxr import UsdGeom
    mesh = UsdGeom.Mesh(prim)
    normals = mesh.GetNormalsAttr().Get(time)
    if normals is None or not len(normals):
        return None
    turn = np.linalg.inv(np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(time))[:3, :3])
    found = per_corner(normals, mesh.GetNormalsInterpolation(), indices, corner_faces) @ turn.T
    return found / np.maximum(np.linalg.norm(found, axis=1, keepdims=True), 1e-12)


def texcoords(prim, indices, corner_faces, time):
    """A mesh's st at every corner as glTF's texture coordinates (v from the top), or None when it has none."""
    from pxr import UsdGeom
    st = UsdGeom.PrimvarsAPI(prim).GetPrimvar("st")
    if not st or not st.HasValue():
        return None
    found = per_corner(st.ComputeFlattened(time), st.GetInterpolation(), indices, corner_faces)
    return np.column_stack([found[:, 0], 1.0 - found[:, 1]])


def channel_source(shader, name):
    """A UsdPreviewSurface input: ["texture", file, channel] when a picture drives it (with its repeat scale on the
    end when a UsdTransform2d scales its coordinates: a library tile, tools/usd/shaders.py), else ["value", value];
    None when unauthored."""
    from pxr import UsdShade
    found = shader.GetInput(name)
    if not found:
        return None
    sources = found.GetConnectedSources()[0]
    if sources:
        picture = UsdShade.Shader(sources[0].source.GetPrim())
        asset = picture.GetInput("file").Get()
        path = asset.resolvedPath or asset.path if asset else ""
        scale = repeat_scale(picture)
        return (["texture", path, str(sources[0].sourceName)] + ([scale] if scale else [])) if path else None
    value = found.Get()
    if value is None:
        return None
    return ["value", [float(part) for part in value] if hasattr(value, "__len__") else float(value)]


def repeat_scale(picture):
    """The [u, v] scale a UsdTransform2d feeding a picture's coordinates sets, or None when none does."""
    from pxr import UsdShade
    coordinates = picture.GetInput("st")
    sources = coordinates.GetConnectedSources()[0] if coordinates else []
    if not sources:
        return None
    upstream = UsdShade.Shader(sources[0].source.GetPrim())
    if upstream.GetIdAttr().Get() != "UsdTransform2d" or not upstream.GetInput("scale"):
        return None
    return [float(part) for part in upstream.GetInput("scale").Get()]


def surface_inputs(material):
    """A bound material's UsdPreviewSurface inputs that glTF can carry, by name, or {} for none."""
    from pxr import UsdShade
    shader = material.ComputeSurfaceSource()[0] if material else None
    if not shader or shader.GetIdAttr().Get() != "UsdPreviewSurface":
        return {}
    names = ("diffuseColor", "roughness", "metallic", "normal", "emissiveColor", "opacity", "opacityThreshold")
    found = {name: channel_source(UsdShade.Shader(shader.GetPrim()), name) for name in names}
    return {name: source for name, source in found.items() if source is not None}


def bound_material(prim):
    from pxr import UsdShade
    return UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]


def surface_groups(prim, triangle_faces):
    """The mesh's triangles by what paints them: [(surface name, material, triangle numbers)]. A part (a GeomSubset
    with a material of its own) is named after itself; the rest after the mesh's material."""
    from pxr import UsdGeom
    taken = np.zeros(len(triangle_faces), dtype=bool)
    groups = []
    for subset in UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Imageable(prim)):
        material = bound_material(subset.GetPrim())
        if not material or subset.GetElementTypeAttr().Get() != UsdGeom.Tokens.face:
            continue
        chosen = np.isin(triangle_faces, np.asarray(subset.GetIndicesAttr().Get(), dtype=np.int64)) & ~taken
        taken |= chosen
        groups.append((subset.GetPrim().GetName(), material, np.flatnonzero(chosen)))
    material = bound_material(prim)
    rest = np.flatnonzero(~taken)
    if len(rest):
        groups.append((material.GetPrim().GetName() if material else "unpainted", material, rest))
    return [group for group in groups if len(group[2])]


class Gltf:
    """A glTF document and its one binary buffer, written as `.gltf` and `.bin` into a work folder for gltfpack."""

    def __init__(self, folder):
        self.folder = folder
        self.document = {"asset": {"version": "2.0", "generator": "SCORE tools/review/viewer/export.py"},
                         "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "materials": [],
                         "textures": [], "images": [], "accessors": [], "bufferViews": [], "extensionsUsed": []}
        self.blob = bytearray()
        self.materials, self.images = {}, {}

    def accessor(self, values, kind, target):
        """One accessor over its own buffer view: float32 VEC2 or VEC3 (VEC3 with its bounds), or uint32 indices."""
        data = np.ascontiguousarray(values, dtype=np.uint32 if kind == "SCALAR" else np.float32)
        self.document["bufferViews"].append({"buffer": 0, "byteOffset": len(self.blob), "byteLength": data.nbytes,
                                             "target": target})
        self.blob += data.tobytes()
        entry = {"bufferView": len(self.document["bufferViews"]) - 1, "count": len(data), "type": kind,
                 "componentType": GLTF_UINT if kind == "SCALAR" else GLTF_FLOAT}
        if kind == "VEC3":
            entry.update(min=data.min(axis=0).tolist(), max=data.max(axis=0).tolist())
        self.document["accessors"].append(entry)
        return len(self.document["accessors"]) - 1

    def texture(self, path, scale=None):
        """A texture of the picture at `path`, each picture once (its web-size copy is made at write); repeated by
        `scale` ([u, v], KHR_texture_transform) when given."""
        if path not in self.images:
            self.document["images"].append({"uri": path})
            self.document["textures"].append({"source": len(self.document["images"]) - 1})
            self.images[path] = len(self.document["textures"]) - 1
        if scale is None:
            return {"index": self.images[path]}
        if TRANSFORM not in self.document["extensionsUsed"]:
            self.document["extensionsUsed"].append(TRANSFORM)
        return {"index": self.images[path], "extensions": {TRANSFORM: {"scale": scale}}}

    def roughness_metal(self, rough, metal):
        """The metal-rough texture glTF wants (roughness in green, metalness in blue): the stage's own picture when
        both come from one in those channels, else one put together from the two."""
        if rough[0] == metal[0] == "texture" and rough[1] == metal[1] and (rough[2], metal[2]) == ("g", "b"):
            return self.texture(rough[1], *rough[3:])
        key = json.dumps([rough, metal])
        if key not in self.images:
            sizes = [Image.open(source[1]).size for source in (rough, metal) if source[0] == "texture"]
            size = max(sizes, key=lambda each: each[0] * each[1])
            planes = [channel_plane(source, size) for source in (rough, metal)]
            path = self.folder / f"metal_rough_{len(self.images)}.png"
            Image.merge("RGB", [planes[0], planes[0], planes[1]]).save(path)
            self.images[key] = self.texture(str(path))["index"]
        return {"index": self.images[key]}

    def material(self, name, inputs, double_sided):
        """A glTF material for a surface's inputs, each distinct one once: its index."""
        key = (name, double_sided, json.dumps(inputs, sort_keys=True))
        if key not in self.materials:
            self.document["materials"].append(material_entry(self, name, inputs, double_sided))
            self.materials[key] = len(self.document["materials"]) - 1
        return self.materials[key]

    def node(self, name, primitives):
        """A node of one mesh holding the primitives, its points already in the stage's frame."""
        self.document["meshes"].append({"name": name, "primitives": primitives})
        self.document["nodes"].append({"name": name, "mesh": len(self.document["meshes"]) - 1})
        self.document["scenes"][0]["nodes"].append(len(self.document["nodes"]) - 1)

    def write(self):
        """The document, its buffer and its pictures at web size into the work folder: the .gltf's path."""
        with ThreadPoolExecutor() as pool:
            names = pool.map(web_picture, [image["uri"] for image in self.document["images"]],
                             [self.folder / f"picture_{number}" for number in range(len(self.document["images"]))])
            for image, name in zip(self.document["images"], names):
                image["uri"] = name
        self.document["buffers"] = [{"uri": "scene.bin", "byteLength": len(self.blob)}]
        (self.folder / "scene.bin").write_bytes(self.blob)
        path = self.folder / "scene.gltf"
        path.write_text(json.dumps({key: value for key, value in self.document.items() if value != []}))
        return path


def web_picture(source, stem):
    """The picture at `source` at most TEXTURE_SIZE a side, as `stem`.png where it is see-through somewhere, else
    `stem`.jpg: the file's name."""
    picture = Image.open(source)
    picture.thumbnail((TEXTURE_SIZE, TEXTURE_SIZE), Image.LANCZOS)
    see_through = picture.mode in ("RGBA", "LA", "PA") and picture.getchannel("A").getextrema()[0] < 255
    if see_through:
        picture.save(stem.with_suffix(".png"), optimize=True)
        return stem.with_suffix(".png").name
    picture.convert("RGB").save(stem.with_suffix(".jpg"), quality=JPEG_QUALITY)
    return stem.with_suffix(".jpg").name


def channel_plane(source, size):
    """One greyscale plane at `size` of a texture's channel, or of a value."""
    if source[0] == "value":
        return Image.new("L", size, round(255 * float(np.clip(source[1], 0.0, 1.0))))
    picture = Image.open(source[1]).convert("RGBA").resize(size)
    return picture.getchannel("RGBA".index(source[2].upper()))


def material_entry(gltf, name, inputs, double_sided):
    """A glTF metal-rough material from a UsdPreviewSurface's inputs (surface_inputs)."""
    pbr = {"baseColorFactor": [1.0, 1.0, 1.0, 1.0], "roughnessFactor": 1.0, "metallicFactor": 1.0}
    entry = {"name": name, "pbrMetallicRoughness": pbr, "doubleSided": double_sided}
    diffuse = inputs.get("diffuseColor", ["value", [0.18, 0.18, 0.18]])
    opacity = inputs.get("opacity")
    if diffuse[0] == "texture":
        pbr["baseColorTexture"] = gltf.texture(*diffuse[1:2], *diffuse[3:])
    else:
        pbr["baseColorFactor"] = [*diffuse[1][:3], 1.0]
        if opacity and opacity[0] == "texture":
            pbr["baseColorTexture"] = gltf.texture(opacity[1])  # for its alpha, the opacity
    rough = inputs.get("roughness", ["value", 0.5])
    metal = inputs.get("metallic", ["value", 0.0])
    if "texture" in (rough[0], metal[0]):
        pbr["metallicRoughnessTexture"] = gltf.roughness_metal(rough, metal)
    else:
        pbr["roughnessFactor"], pbr["metallicFactor"] = float(rough[1]), float(metal[1])
    if inputs.get("normal", ["value"])[0] == "texture":
        entry["normalTexture"] = gltf.texture(*inputs["normal"][1:2], *inputs["normal"][3:])
    glowing(gltf, entry, inputs.get("emissiveColor"))
    see_through(entry, opacity, inputs.get("opacityThreshold"))
    return entry


def glowing(gltf, entry, glow):
    """A glowing surface's emission: its picture, or its colour, over glTF's 0..1 by emissive strength."""
    if glow and glow[0] == "texture":
        entry["emissiveTexture"], entry["emissiveFactor"] = gltf.texture(glow[1]), [1.0, 1.0, 1.0]
        return
    if not glow or max(glow[1]) <= 0:
        return
    strongest = max(glow[1])
    entry["emissiveFactor"] = [value / max(strongest, 1.0) for value in glow[1]]
    if strongest > 1.0:
        entry["extensions"] = {"KHR_materials_emissive_strength": {"emissiveStrength": strongest}}
        if "KHR_materials_emissive_strength" not in gltf.document["extensionsUsed"]:
            gltf.document["extensionsUsed"].append("KHR_materials_emissive_strength")


def see_through(entry, opacity, threshold):
    """A see-through surface's alpha: a cutout where the stage sets a threshold, else blended."""
    if not opacity or (opacity[0] == "value" and opacity[1] >= 1.0):
        return
    if threshold and threshold[1] > 0:
        entry["alphaMode"], entry["alphaCutoff"] = "MASK", float(threshold[1])
    else:
        entry["alphaMode"] = "BLEND"
    if opacity[0] == "value":
        entry["pbrMetallicRoughness"]["baseColorFactor"][3] = float(opacity[1])


def object_name(prim):
    """The object a mesh belongs to, as the viewer names it: its path under the place, an object's one mesh (`geo`)
    by its object's."""
    named = prim.GetParent() if prim.GetName() == "geo" else prim
    return str(named.GetPath().MakeRelativePath(prim.GetStage().GetDefaultPrim().GetPath()))


def add_mesh(gltf, prim, skinned, time, boxes):
    """One stage mesh as a node, a primitive per surface, its box joined into its object's in `boxes`: its
    triangle count."""
    from pxr import UsdGeom
    corners = sphere_corners(prim, time) if prim.IsA(UsdGeom.Sphere) else mesh_corners(prim, skinned, time)
    if corners is None:
        return 0
    double_sided = bool(UsdGeom.Gprim(prim).GetDoubleSidedAttr().Get())
    primitives = []
    for surface, material, chosen in surface_groups(prim, corners["faces"]):
        used = np.unique(corners["triangles"][chosen])
        renumber = np.full(len(corners["positions"]), -1, dtype=np.int64)
        renumber[used] = np.arange(len(used))
        attributes = {"POSITION": gltf.accessor(corners["positions"][used], "VEC3", ARRAY_BUFFER)}
        if corners["normals"] is not None:
            attributes["NORMAL"] = gltf.accessor(corners["normals"][used], "VEC3", ARRAY_BUFFER)
        if corners["texcoords"] is not None:
            attributes["TEXCOORD_0"] = gltf.accessor(corners["texcoords"][used], "VEC2", ARRAY_BUFFER)
        indices = gltf.accessor(renumber[corners["triangles"][chosen]].ravel(), "SCALAR", ELEMENT_ARRAY_BUFFER)
        primitives.append({"attributes": attributes, "indices": indices,
                           "material": gltf.material(surface, surface_inputs(material), double_sided)})
    name = object_name(prim)
    gltf.node(name, primitives)
    low, high = corners["positions"].min(axis=0), corners["positions"].max(axis=0)
    if name in boxes:
        low, high = np.minimum(low, boxes[name][0]), np.maximum(high, boxes[name][1])
    boxes[name] = (low, high)
    return len(corners["triangles"])


def write_meshes(stage, gltf, time):
    """Every drawn mesh of the stage into the document: the objects' boxes, the triangle count and what was left
    out (other shapes and point instancers, counted by kind)."""
    from pxr import Usd, UsdGeom
    skinned = skins(stage)
    boxes, triangles, left_out = {}, 0, {}
    prims = iter(Usd.PrimRange(stage.GetDefaultPrim()))
    for prim in prims:
        if prim.IsA(UsdGeom.PointInstancer) or (
                prim.IsA(UsdGeom.Gprim) and not (prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Sphere))):
            if UsdGeom.Imageable(prim).ComputeVisibility(time) != UsdGeom.Tokens.invisible:
                left_out[str(prim.GetTypeName())] = left_out.get(str(prim.GetTypeName()), 0) + 1
            prims.PruneChildren()
        elif drawn(prim, time):
            triangles += add_mesh(gltf, prim, skinned, time, boxes)
    return boxes, triangles, left_out


def light_entry(prim, time):
    """A UsdLux sphere or distant light as the viewer lights it (three.js units, see CANDELA_PER_INTENSITY), or
    None for another kind."""
    from pxr import UsdGeom, UsdLux
    if not (prim.IsA(UsdLux.SphereLight) or prim.IsA(UsdLux.DistantLight)):
        return None
    light = UsdLux.SphereLight(prim) if prim.IsA(UsdLux.SphereLight) else UsdLux.DistantLight(prim)
    world = np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(time))
    strength = float(light.GetIntensityAttr().Get(time) or 0.0) * 2.0 ** float(light.GetExposureAttr().Get(time) or 0.0)
    entry = {"name": prim.GetName(), "colour": [float(part) for part in light.GetColorAttr().Get(time)],
             "at": world[3, :3].tolist(), "toward": (-world[2, :3] / np.linalg.norm(world[2, :3])).tolist()}
    if prim.IsA(UsdLux.DistantLight):
        return dict(entry, type="directional", intensity=strength * LUX_PER_INTENSITY)
    entry.update(type="point", intensity=strength * CANDELA_PER_INTENSITY,
                 radius=float(light.GetRadiusAttr().Get(time) or 0.0))
    if prim.HasAPI(UsdLux.ShapingAPI):
        shaping = UsdLux.ShapingAPI(prim)
        cone = shaping.GetShapingConeAngleAttr().Get(time)
        if cone is not None and cone < 180:
            entry.update(type="spot", angle=math.radians(float(cone)),
                         penumbra=float(shaping.GetShapingConeSoftnessAttr().Get(time) or 0.0))
    return entry


def sky(stage, time):
    """The place's own sky (its dome, `/<place>/Environment`): the background the camera sees, the ambient light
    (three.js's irradiance: pi times Blender's radiance of colour times energy) and the exposure."""
    from pxr import UsdLux
    dome = stage.GetDefaultPrim().GetChild("Environment")
    if not (dome.IsValid() and dome.IsA(UsdLux.DomeLight)):
        return {"background": [0.0, 0.0, 0.0], "ambient": [0.0, 0.0, 0.0], "exposure": 1.0}
    light = UsdLux.DomeLight(dome)
    energy = float(light.GetIntensityAttr().Get(time) or 0.0)
    background = dome.GetAttribute("score:background").Get(time)
    return {"background": [float(part) for part in (background or (0.0, 0.0, 0.0))],
            "ambient": [math.pi * energy * float(part) for part in light.GetColorAttr().Get(time)],
            "exposure": float(dome.GetAttribute("score:exposure").Get(time) or 1.0)}


def cameras(place):
    """The scene record's cameras (data/scene/<place>.json `views`): name, eye, aim, fov."""
    record = scene_record.record(place) or {}
    return [{"name": view["name"], "eye": view["eye"], "aim": view["aim"], "fov": float(view.get("fov", 75.0))}
            for view in record.get("views", [])]


def pack(source, out):
    """gltfpack's merged, quantized and meshopt-compressed binary of the document at `source`: its log."""
    command = ["npx", "-y", GLTFPACK, "-i", str(source), "-o", str(out), "-cc", "-km", "-vpf", "-v"]
    run = subprocess.run(command, capture_output=True, text=True)
    if run.returncode != 0 or not out.exists():
        raise RuntimeError(f"gltfpack failed:\n{run.stdout[-2000:]}\n{run.stderr[-2000:]}")
    return run.stdout + run.stderr


def export(place, stage_path, out):
    """Write the place's web copy (`<out>/<place>/<place>.glb` and its sidecar): the sidecar's path."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(stage_path))
    time = Usd.TimeCode(stage.GetStartTimeCode())
    folder = out / place
    folder.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix=f"viewer-{place}-"))
    try:
        gltf = Gltf(work)
        boxes, triangles, left_out = write_meshes(stage, gltf, time)
        log = pack(gltf.write(), folder / f"{place}.glb")
    finally:
        shutil.rmtree(work)
    lights = [entry for entry in (light_entry(prim, time) for prim in stage.Traverse()) if entry]
    sidecar = {"place": place, "stage": str(stage_path), "triangles": triangles, "left_out": left_out,
               "lights": lights, "sky": sky(stage, time), "cameras": cameras(place),
               "objects": [{"name": name, "low": low.round(4).tolist(), "high": high.round(4).tolist()}
                           for name, (low, high) in boxes.items()],
               "bytes": (folder / f"{place}.glb").stat().st_size, "packed_with": GLTFPACK}
    path = folder / f"{place}.json"
    path.write_text(json.dumps(sidecar))
    (folder / "gltfpack.log").write_text(log)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("place")
    parser.add_argument("--stage", type=pathlib.Path, help="the stage's .usda (default: <stages>/<place>/<place>.usda)")
    parser.add_argument("--stages", type=pathlib.Path, default=STAGES)
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    arguments = parser.parse_args()
    stage = arguments.stage or arguments.stages / arguments.place / f"{arguments.place}.usda"
    sidecar = json.loads(export(arguments.place, stage, arguments.out).read_text())
    print(f"{arguments.place}: {sidecar['triangles']} triangles, {sidecar['bytes'] / 1e6:.1f} MB, "
          f"{len(sidecar['lights'])} lights, {len(sidecar['cameras'])} cameras, "
          f"left out {sidecar['left_out'] or 'nothing'} -> {arguments.out / arguments.place}")


if __name__ == "__main__":
    main()
