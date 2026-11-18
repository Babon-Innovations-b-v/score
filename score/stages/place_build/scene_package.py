"""A laid place's scene package (`package`): what a game engine loads (the game 2099's Unity, through glTFast), in
the one format tools/props/library/package.py writes and checks (score.scene version 1, its docstring the format):
<out>/scene.json and <out>/objects/<name>.gltf (its .bin beside it) for every distinct object.

    python -m score.stages.place_build package <folder> <out>

Every object under /<place>/Objects (and every still effect under /<place>/Effects) is converted from the laid USD
with usd-core and trimesh's glTF writer: each drawn mesh and cube in the object's own frame (a mesh that authors no
normals shaded smooth, as Blender imports it), each face in the look bound to it (its part's, or the object's whole
look laid over its own colour), that look as glTF PBR: its colour,
metal, roughness, opacity and glow factors (a glow past 1 with KHR_materials_emissive_strength; every look double
sided, as Cycles draws a face from both sides: a tunnel's one-skin wall and a dome's lamp strips are seen from inside
and from out), its colour,
metal-roughness, normal and glow maps as textures (an image surface's maps read box-projected in the mesh's own frame
over the surface's `tile_metres`, as the preview reads them: each face by its own axis, without the preview's blend
across a corner); a see-through look as glass (KHR_materials_transmission and _ior, its colour the preview's thin
glass tint, its alpha the opacity for a reader without transmission). A palette recipe with a pattern (its edge wear,
dirt and relief) is baked as the preview draws it, in headless Blender on this PC's card through the card queue
(bake_looks.py): the part unwrapped (xatlas, in blocks no wider than a map) at DENSITY texels a metre on maps of at
most LARGEST, each map its own primitive and material, or on a laid ground one seamless GROUND_TILE box-projected;
its base colour, metal-roughness and normal pictures carried in the object's own buffer. A glTF-only model or take
laid in its own bake (no look of the place's on it) goes as its library entry's own glTF, unchanged.
Two objects that convert to the same file are one object. A copy turned and scaled evenly keeps its object in its
own frame (`matrix` the whole transform); a copy stretched unevenly has its stretch baked into its own object.

When the place's physics check has run (<folder>/ready.json, ready/), each copy carries its collider by its role
(COLLIDERS): a prop a convex hull, free, its mass the entry's own record (the maker's `physics.mass_kg`, times its
scale cubed) or null when the entry has none; everything else that stands a solid its mesh, fixed.
Skinned characters (under /<place>/Characters too), the sky's dome and animated effects are not converted:
scene.json's `left_out` names each.
scene.json's `environment` is the place's sky and light as the final render draws them (environment_of): the sky's
picture written into <out>/environment, its turn and glow, the ambient light, background, exposure, the sun, the AgX
view transform and look, a night's moon and glow, the ground's albedo (ground_albedo: what an engine without
path-traced bounce lights from below with), and `grade`: that view transform and look drawn by Blender's own
OpenColorIO into a lattice picture (grade_lut.py), the engine's tone mapping sampling it as SCORE's render grades.
"""
import hashlib
import json
import math
import pathlib
import shutil
import struct

import numpy as np
from PIL import Image
from pxr import Usd, UsdGeom, UsdLux, UsdShade

from score.stages import place_build
import library_files  # tools/library, on the path by place_build
import package  # tools/props/library/package.py, on the path by place_build: the format and its check

GROUND = "y = 0 is the place frame's own zero; each copy stands where it was laid"
COLLIDERS = {"prop": "convex hull", "ground": "mesh", "shell": "mesh", "connector": "mesh", "door": "mesh",
             "structure": "mesh", "fixed": "mesh", "mount": "mesh"}
EVEN = 1e-6  # how far a copy's scale may differ across its axes and still be even
# A palette recipe's bake (bake_looks.py). DENSITY texels a metre on every map: at 1920x1080 under Unity's 60 degree
# field of view a pixel spans 0.97 mm a metre away, so 512 texels a metre is a texel a pixel from 2 m (the floor two
# steps ahead and a wall walked beside, at eye height) and two pixels a texel at 1 m; the room kit's density
# (tools/props/library/inside/bake.py SPLIT_DENSITY). A part needing more than LARGEST a side is split into more maps
# at the same density, never capped. PADDING texels round each chart (its mips' bleed).
DENSITY = 512
LARGEST = 4096
PADDING = 4
UNCHARTED = 0xFFFFFFFF  # xatlas's map number for a vertex of a face it charted on none
SPAN_SHARE = 0.9  # how much of a map's side one block of a part may span (blocks_of): its charts' slack
GROUND_TILE = 8.0  # metres one seamless tile of a laid ground's recipe covers: LARGEST texels at DENSITY
FLAT_RECIPES = ("glass", "glowing")  # recipes of one colour, roughness and glow: their factors are exact, no bake
GLASS_IOR = 1.5  # a see-through look's glass (blender_views.GLASS_IOR)
TEXTURES = "textures"  # the baked pictures' folder beside the objects' .gltf files
# The final render's grade, which the engine's tone mapping takes (blender_views.CONTRAST, usd_views' AgX).
VIEW = {"view_transform": "AgX", "look": "AgX - Medium High Contrast"}
# The grade's picture (grade_lut.py): a lattice `size` a side, each channel `middle` * 2 ** (low + c * (high - low)),
# AgX's own log range about middle grey, so every colour the render can grade has its place in it.
GRADE = {"size": 64, "low": -12.47393, "high": 4.026069, "middle": 0.18}
GRADE_FILE = "environment/grade.png"
# How the final render turns a UsdLux intensity into Blender's units (tools/blender/inside/usd_views.place_light, as
# Blender's own USD reader does): a distant light's strength (W/m²) its intensity times SUN_STRENGTH, a sphere light's
# watts its intensity times pi. A lamp's and the sun's `strength` is that, what the engine lights with.
SUN_STRENGTH = 4.0


# --- a gprim's faces ------------------------------------------------------------------------------------------------

def fanned(counts):
    """A mesh's faces (`counts` corners each) fanned from each face's first corner: (corner indices (m x 3), the face
    of each triangle)."""
    counts = np.asarray(counts, dtype=np.int64)
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    per = np.maximum(counts - 2, 0)
    faces = np.repeat(np.arange(len(counts)), per)
    step = np.arange(per.sum()) - np.repeat(np.cumsum(per) - per, per) + 1
    first = starts[faces]
    return np.column_stack([first, first + step, first + step + 1]), faces


def drawn(prim):
    """A drawn Mesh's or Cube's corners: (points, corner point indices, triangles of corners, the face of each,
    corner normals or None, corner texture coordinates or None); None for any other prim."""
    if prim.IsA(UsdGeom.Cube):
        half = UsdGeom.Cube(prim).GetSizeAttr().Get() / 2.0
        points = np.array([[x, y, z] for x in (-half, half) for y in (-half, half) for z in (-half, half)])
        quads = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3]]
        triangles, faces = fanned([4] * 6)
        return points, np.array(quads).ravel(), triangles, faces, None, None
    if not prim.IsA(UsdGeom.Mesh):
        return None
    mesh = UsdGeom.Mesh(prim)
    points = mesh.GetPointsAttr().Get()
    if not points:
        return None
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
    triangles, faces = fanned(counts)
    if mesh.GetOrientationAttr().Get() == UsdGeom.Tokens.leftHanded:
        triangles = triangles[:, ::-1]
    normals = by_corner(mesh.GetNormalsAttr().Get(), mesh.GetNormalsInterpolation(), indices, counts)
    st = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st")
    uv = by_corner(st.ComputeFlattened(), st.GetInterpolation(), indices, counts) if st and st.HasValue() else None
    return np.asarray(points, dtype=np.float64), indices, triangles, faces, normals, uv


def by_corner(values, interpolation, indices, counts):
    """A primvar's values for each face corner, by its interpolation; None when it has none."""
    if values is None or not len(values):
        return None
    values = np.asarray(values, dtype=np.float64)
    if interpolation == UsdGeom.Tokens.faceVarying:
        return values
    if interpolation in (UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying):
        return values[indices]
    if interpolation == UsdGeom.Tokens.uniform:
        return np.repeat(values, counts, axis=0)
    return np.repeat(values[:1], len(indices), axis=0)  # constant


def face_looks(prim, face_count):
    """The looks bound to a gprim's faces: a part's (its materialBind GeomSubset's) on its faces, the gprim's on the
    rest; ([the looks, material or None], the number of each face's look in them)."""
    whole = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
    looks, chosen = [whole if whole else None], np.zeros(face_count, dtype=np.int64)
    for subset in UsdShade.MaterialBindingAPI(prim).GetMaterialBindSubsets():
        bound = UsdShade.MaterialBindingAPI(subset.GetPrim()).ComputeBoundMaterial()[0]
        if bound:
            looks.append(bound)
            chosen[np.asarray(subset.GetIndicesAttr().Get(), dtype=np.int64)] = len(looks) - 1
    return looks, chosen


# --- a look as glTF PBR ---------------------------------------------------------------------------------------------

def texture_of(shader, name):
    """The UsdUVTexture feeding a shader input: (its file's path, the texture output read, its scale), or None."""
    given = shader.GetInput(name)
    if not given or not given.HasConnectedSource():
        return None
    source = given.GetConnectedSources()[0][0]
    texture = UsdShade.Shader(source.source.GetPrim())
    found = texture.GetInput("file").Get() if texture.GetInput("file") else None
    if found is None or not found.resolvedPath:
        raise place_build.Refused(f"{texture.GetPath()}: its map {found} is not there")
    scale = texture.GetInput("scale").Get() if texture.GetInput("scale") else None
    return pathlib.Path(found.resolvedPath), str(source.sourceName), scale


def value_of(shader, name, default):
    given = shader.GetInput(name)
    value = given.Get() if given else None
    return default if value is None else value


def tile_of(maps):
    """The ground one copy of an image surface's map covers (its surface.json's `tile_metres` beside it), or None for
    a model's own bake."""
    for path in maps:
        record = path.parent / "surface.json"
        if record.is_file():
            tile = json.loads(record.read_text()).get("tile_metres")
            if tile:
                return float(tile)
    return None


def channel(path, output):
    """One channel of a map as a greyscale picture (`r`, `g`, `b` or `a`; `rgb` its first)."""
    picture = Image.open(path)
    bands = picture.getbands()
    wanted = {"r": 0, "g": 1, "b": 2, "a": 3}.get(output, 0)
    return picture.getchannel(bands[min(wanted, len(bands) - 1)]).convert("L")


def metal_rough(roughness, metal, rough_value, metal_value):
    """glTF's metal-roughness map (roughness in green, metal in blue) from the look's two maps, a flat value where one
    has none; None when neither has a map."""
    if roughness is None and metal is None:
        return None
    size = Image.open((roughness or metal)[0]).size
    grey = [channel(found[0], found[1]).resize(size) if found else None for found in (roughness, metal)]
    rough = grey[0] or Image.new("L", size, int(round(float(rough_value) * 255)))
    metallic = grey[1] or Image.new("L", size, int(round(float(metal_value) * 255)))
    return Image.merge("RGB", (Image.new("L", size, 255), rough, metallic))


def look_name(look):
    """A look's material name: the library surface it lays (`score:surface`, its part after it), so two copies in the
    same surface convert to the same file; a model's own bake by its own name."""
    surface = text_of(look.GetPrim(), "score:surface")
    if not surface:
        return look.GetPrim().GetName()
    part = look.GetPrim().GetName().partition("__")[2]
    return surface + (f" {part}" if part else "")


def recipe_spec(look):
    """A palette variant's spec on a look (`score:recipe:spec`), or None."""
    marked = text_of(look.GetPrim(), "score:recipe:spec") if look else None
    return json.loads(marked) if marked else None


def glass_of(colour, opacity):
    """A see-through look's glTF transmission, as the preview's thin glass draws it (blender_views.thin_glass): light
    passing tinted 1 - opacity x (1 - colour) as far as it is not opaque, at window glass's IOR; (the colour the
    passing light takes, the extensions)."""
    tint = [1.0 - opacity * (1.0 - float(value)) for value in colour]
    return tint, {"KHR_materials_transmission": {"transmissionFactor": round(1.0 - opacity, 6)},
                  "KHR_materials_ior": {"ior": GLASS_IOR}}


def glowing(glow):
    """A glow colour as glTF holds it: a factor of at most 1 and, past 1, the strength it is given off at
    (KHR_materials_emissive_strength); (the factor, the extensions)."""
    strength = max([float(value) for value in glow] + [0.0])
    if strength <= 1.0:
        return [float(value) for value in glow], {}
    return [float(value) / strength for value in glow], {"KHR_materials_emissive_strength":
                                                        {"emissiveStrength": strength}}


def pbr(look, ground=False):
    """A bound look as glTF PBR: {"material": trimesh PBRMaterial, "tile": metres or None, "key": what tells it,
    "bake": a palette recipe's bake or None}. A recipe with a pattern (not FLAT_RECIPES) is baked as Blender draws it
    (bake_looks.py): on a laid ground (`ground`) as one seamless GROUND_TILE box-projected like an image surface, on
    anything else into its own unwrapped maps at DENSITY."""
    import trimesh
    if look is None:
        return {"material": trimesh.visual.material.PBRMaterial(name="no_look"), "tile": None, "key": "none"}
    shader = look.ComputeSurfaceSource()[0]
    if not shader:
        return {"material": trimesh.visual.material.PBRMaterial(name=look_name(look)), "tile": None,
                "key": str(look.GetPath())}
    colour_map, rough_map, metal_map, normal_map, glow_map = (texture_of(shader, name) for name in (
        "diffuseColor", "roughness", "metallic", "normal", "emissiveColor"))
    colour = list(colour_map[2])[:3] if colour_map and colour_map[2] is not None else (
        [1.0, 1.0, 1.0] if colour_map else list(value_of(shader, "diffuseColor", (0.18, 0.18, 0.18))))
    opacity = float(value_of(shader, "opacity", 1.0))
    roughness, metallic = float(value_of(shader, "roughness", 0.5)), float(value_of(shader, "metallic", 0.0))
    combined = metal_rough(rough_map, metal_map, roughness, metallic)
    glow, extensions = glowing([1.0, 1.0, 1.0] if glow_map else value_of(shader, "emissiveColor", (0.0, 0.0, 0.0)))
    if opacity < 1.0:
        colour, see_through = glass_of(colour, opacity)
        extensions.update(see_through)
    spec = recipe_spec(look)
    bake = {"spec": spec, "tile": GROUND_TILE if ground else None} if spec and \
        spec.get("recipe") not in FLAT_RECIPES else None
    material = trimesh.visual.material.PBRMaterial(
        name=look_name(look), baseColorFactor=[float(value) for value in colour] + [opacity],
        metallicFactor=1.0 if combined else metallic, roughnessFactor=1.0 if combined else roughness,
        emissiveFactor=glow, alphaMode="BLEND" if opacity < 1.0 else "OPAQUE", doubleSided=True,
        baseColorTexture=Image.open(colour_map[0]).convert("RGBA" if opacity < 1.0 else "RGB") if colour_map else None,
        metallicRoughnessTexture=combined,
        normalTexture=Image.open(normal_map[0]).convert("RGB") if normal_map else None,
        emissiveTexture=Image.open(glow_map[0]).convert("RGB") if glow_map else None)
    maps = [found[0] for found in (colour_map, rough_map, metal_map, normal_map, glow_map) if found]
    exact = {"baseColorFactor": [float(value) for value in colour] + [opacity], "emissiveFactor": glow}
    if not combined:
        exact.update(metallicFactor=metallic, roughnessFactor=roughness)
    if extensions:
        exact["extensions"] = extensions
    return {"material": material, "tile": bake["tile"] if bake else tile_of(maps), "key": str(look.GetPath()),
            "factors": exact, "bake": bake,
            "tells": json.dumps([look_name(look), exact, [str(path) for path in maps], bake], sort_keys=True)}


def boxed_uv(points, normals, tile):
    """Texture coordinates box-projected over `tile` metres in the mesh's own frame: each corner by its face's
    strongest axis (x: y, z; y: x, z; z: x, y), as the preview's box projection reads an image surface."""
    axis = np.abs(normals).argmax(axis=1)
    pairs = np.array([[1, 2], [0, 2], [0, 1]])[axis]
    return np.take_along_axis(points, pairs, axis=1) / tile


# --- an object as one glTF ------------------------------------------------------------------------------------------

def gprims(prim):
    """Every drawn, shown gprim under an object (its far bodies and guides left out)."""
    for inside in Usd.PrimRange(prim):
        imageable = UsdGeom.Imageable(inside)
        if not imageable or imageable.ComputeVisibility() == UsdGeom.Tokens.invisible \
                or imageable.ComputePurpose() not in (UsdGeom.Tokens.default_, UsdGeom.Tokens.render):
            continue
        if inside.IsA(UsdGeom.Mesh) or inside.IsA(UsdGeom.Cube):
            yield inside


def flat_normals(points, triangles):
    """Each triangle's own unit normal."""
    corners = points[triangles]
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    return normal / np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)


def smooth_normals(points, indices, triangles):
    """Each corner's normal as Blender shades a USD mesh that authors none (smooth): its point's normal, the normals
    of the triangles round it weighted by their angle at it."""
    corners = points[indices][triangles]
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
    summed = np.zeros_like(points)
    for at in range(3):
        towards = [corners[:, (at + step) % 3] - corners[:, at] for step in (1, 2)]
        lengths = [np.maximum(np.linalg.norm(side, axis=1), 1e-12) for side in towards]
        angle = np.arccos(np.clip(np.einsum("ij,ij->i", *towards) / (lengths[0] * lengths[1]), -1.0, 1.0))
        np.add.at(summed, indices[triangles[:, at]], normal * angle[:, None])
    summed /= np.maximum(np.linalg.norm(summed, axis=1, keepdims=True), 1e-12)
    return summed[indices]


def gprim_pieces(prim, holder, baked, looks):
    """One gprim's triangles in its object's frame (`holder` the object's prim; `baked` the row-major 3 x 3 of the
    copy's turn and stretch drawn into it, or None), grouped by look: {look key: (positions (k x 3), normals, uv or
    None)} per triangle corner, `looks` the PBR looks by key. Read below the object (its own transforms alone), so
    two copies of one object convert to the same numbers wherever they stand."""
    found = drawn(prim)
    if found is None or not len(found[2]):
        return {}
    points, indices, triangles, faces, normals, uv = found
    own = points[indices]  # by corner, the mesh's own frame
    if normals is not None:
        normals_at = triangles
    elif prim.IsA(UsdGeom.Mesh):
        normals, normals_at = smooth_normals(points, indices, triangles), triangles
    else:
        normals = np.repeat(flat_normals(own, triangles), 3, axis=0)
        normals_at = np.arange(len(triangles) * 3).reshape(-1, 3)
    matrix = np.asarray(UsdGeom.XformCache().ComputeRelativeTransform(prim, holder)[0])
    if baked is not None:
        turned_in = np.eye(4)
        turned_in[:3, :3] = baked
        matrix = matrix @ turned_in
    turn = np.linalg.inv(matrix[:3, :3]).T
    flipped = np.linalg.det(matrix[:3, :3]) < 0
    bound, per_face = face_looks(prim, int(faces.max()) + 1)
    keys = np.array([pbr_key(look) for look in bound])[per_face[faces]]
    grouped = {}
    for key in np.unique(keys):
        chosen = keys == key
        corners, corner_normals = triangles[chosen].ravel(), normals[normals_at[chosen].ravel()]
        tile = looks[key]["tile"]
        coordinates = boxed_uv(own[corners], corner_normals, tile) if tile else (
            uv[corners] if uv is not None else None)
        placed = own[corners] @ matrix[:3, :3] + matrix[3, :3]
        turned = corner_normals @ turn
        turned /= np.maximum(np.linalg.norm(turned, axis=1, keepdims=True), 1e-12)
        if flipped:
            placed, turned = placed.reshape(-1, 3, 3)[:, ::-1].reshape(-1, 3), turned.reshape(-1, 3, 3)[:, ::-1].reshape(-1, 3)
            coordinates = None if coordinates is None else coordinates.reshape(-1, 3, 2)[:, ::-1].reshape(-1, 2)
        grouped[str(key)] = (placed, turned, coordinates)
    return grouped


def text_of(prim, name):
    given = prim.GetAttribute(name)
    return given.Get() if given and given.HasValue() else None


def pbr_key(look):
    return str(look.GetPath()) if look else "none"


def looks_of(prim):
    """Every look bound inside the object as glTF PBR, by key (a laid ground's recipes tiled: pbr)."""
    looks, ground = {}, bool(text_of(prim, "score:ground"))
    for inside in gprims(prim):
        found = drawn(inside)
        if found is None or not len(found[2]):
            continue
        for look in face_looks(inside, int(found[3].max()) + 1)[0]:
            if pbr_key(look) not in looks:
                looks[pbr_key(look)] = pbr(look, ground)
    return looks


def welded(positions, normals, uv):
    """Corners with the same position, normal and texture coordinate made one vertex: (vertices, normals, uv, faces)."""
    rows = np.hstack([positions, normals] + ([uv] if uv is not None else []))
    unique, faces = np.unique(rows.round(7), axis=0, return_inverse=True)
    return unique[:, :3], unique[:, 3:6], (unique[:, 6:8] if uv is not None else None), faces.reshape(-1, 3)


def told(gathered, looks):
    """What tells an object's conversion apart: its looks and its corners' numbers, hashed (two copies of one object
    in one look tell the same, so it is written once)."""
    digest = hashlib.sha256()
    for key in sorted(gathered):
        digest.update(looks[key].get("tells", key).encode())
        for piece in gathered[key]:
            for values in piece:
                digest.update(b"-" if values is None else np.ascontiguousarray(values.round(7)).tobytes())
    return digest.hexdigest()


def object_glb(prim, baked, made):
    """The object's GLB (a primitive a look) in its own frame, `baked` (a row-major 3 x 3, or None) drawn into it, and
    its triangle count; None when it draws no face. `made` holds the GLBs written so far by what tells them (`told`),
    so a copy of one already made is not written again."""
    looks = looks_of(prim)
    gathered = {}
    for inside in gprims(prim):
        for key, (positions, normals, uv) in gprim_pieces(inside, prim, baked, looks).items():
            gathered.setdefault(key, []).append((positions, normals, uv))
    if not gathered:
        return None, 0
    tells = told(gathered, looks)
    if tells not in made:
        made[tells] = gltf_written(gathered, looks)
    return made[tells]


def areas_of(points, faces):
    corners = points[faces]
    return 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=-1)


def blocks_of(vertices, faces, chosen):
    """The faces `chosen` cut into blocks no wider than a map holds at DENSITY (SPAN): each block's box halved across
    its longest side, by the faces' middles, until it fits; so no chart xatlas makes is wider than its map and none is
    shrunk to fit (a dome's 10 m deck as one chart came out at 390 texels a metre)."""
    corners = vertices[faces[chosen]]
    box = np.ptp(corners.reshape(-1, 3), axis=0)
    if box.max() <= (LARGEST - 2 * PADDING) / DENSITY * SPAN_SHARE or len(chosen) == 1:
        return [chosen]
    axis = int(box.argmax())
    middles = corners.mean(axis=1)[:, axis]
    low = middles < (corners[..., axis].min() + corners[..., axis].max()) / 2
    if low.all() or not low.any():
        low = np.arange(len(chosen)) < len(chosen) // 2
    return blocks_of(vertices, faces, chosen[low]) + blocks_of(vertices, faces, chosen[~low])


def unwrapped(vertices, normals, faces):
    """A mesh laid flat for its bake (xatlas, a block a mesh: blocks_of) at DENSITY texels a metre, PADDING round each
    chart, on maps of at most LARGEST a side: [(vertices, normals, uv, faces, [width, height], texels a metre as
    laid)] a map."""
    import xatlas
    blocks = [np.unique(faces[chosen], return_inverse=True) for chosen in blocks_of(vertices, faces,
                                                                                    np.arange(len(faces)))]

    def generated(resolution):
        atlas = xatlas.Atlas()
        for kept, inverse in blocks:
            atlas.add_mesh(vertices[kept].astype(np.float32), inverse.reshape(-1, 3).astype(np.uint32),
                           normals[kept].astype(np.float32))
        packing = xatlas.PackOptions()
        packing.texels_per_unit, packing.padding, packing.bilinear, packing.blockAlign = DENSITY, PADDING, True, True
        packing.resolution = resolution
        atlas.generate(pack_options=packing)
        return atlas
    atlas = generated(0)
    if max(atlas.width, atlas.height) > LARGEST:
        atlas = generated(LARGEST)
    size = [int(atlas.width), int(atlas.height)]
    pages = [([], [], [], []) for _ in range(atlas.atlas_count)]
    for number, (kept, _) in enumerate(blocks):
        mapping, corners, uv = atlas[number]
        page = atlas.get_mesh_vertex_assignment(number)[0].astype(np.int64)[corners[:, 0]]
        page[page == UNCHARTED] = 0  # a sliver xatlas charts on no map stays, on the first
        for held, (points, ways, coordinates, triangles) in enumerate(pages):
            chosen = corners[page == held]
            if not len(chosen):
                continue
            used, inverse = np.unique(chosen, return_inverse=True)
            triangles.append(inverse.reshape(-1, 3) + sum(len(block) for block in points))
            points.append(vertices[kept[mapping[used]]])
            ways.append(normals[kept[mapping[used]]])
            coordinates.append(uv[used].astype(np.float64))
    found = []
    for points, ways, coordinates, triangles in pages:
        points, coordinates, triangles = np.vstack(points), np.vstack(coordinates), np.vstack(triangles)
        texels = np.sqrt(areas_of(np.hstack([coordinates * size, np.zeros((len(coordinates), 1))]),
                                  triangles).sum() / max(areas_of(points, triangles).sum(), 1e-12))
        found.append((points, np.vstack(ways), coordinates, triangles, size, round(float(texels), 1)))
    return found


def gltf_written(gathered, looks):
    """The GLB of an object's corners grouped by look (a recipe to bake on its own unwrapped maps, a part a map), and
    its triangle count."""
    import trimesh
    scene, triangles, parts = trimesh.Scene(), 0, []
    for key in sorted(gathered):
        pieces = gathered[key]
        with_uv = all(piece[2] is not None for piece in pieces)
        vertices, normals, uv, faces = welded(np.vstack([piece[0] for piece in pieces]),
                                              np.vstack([piece[1] for piece in pieces]),
                                              np.vstack([piece[2] for piece in pieces]) if with_uv else None)
        bake = looks[key].get("bake")
        maps = unwrapped(vertices, normals, faces) if bake and not bake["tile"] else \
            [(vertices, normals, uv, faces, [LARGEST, LARGEST], LARGEST / bake["tile"]) if bake else
             (vertices, normals, uv, faces, None, None)]
        for page, (vertices, normals, uv, faces, size, texels) in enumerate(maps):
            number = len(parts)
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_normals=normals, process=False)
            mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=looks[key]["material"])
            scene.add_geometry(mesh, node_name=f"part_{number}", geom_name=f"part_{number}")
            triangles += len(faces)
            asked = dict(bake, size=size, texels_a_metre=texels) if bake else None
            parts.append({"factors": looks[key].get("factors", {}), "bake": asked,
                          "name": looks[key]["material"].name + (f" map{page + 1}" if len(maps) > 1 else "")})
    return exactly(scene.export(file_type="glb"), parts), triangles


def exactly(glb, parts):
    """The GLB with each part's own material (`parts` by part number: its name, its factors as the look has them,
    its bake asked or None): trimesh's writer keeps a colour in 8 bits, so 0.3 would come out 0.302, and gives parts
    in one look one material, where each baked map needs its own pictures. A part's bake rides in its material's
    extras (`score_bake`) until bake_looks.py's pictures replace it (attached); its extensions are listed used."""
    document, binary = unpacked(glb, None)
    materials, used = [], set()
    for mesh in document["meshes"]:
        part = parts[int(mesh["name"].rsplit("_", 1)[1])]
        material = json.loads(json.dumps(document["materials"][mesh["primitives"][0]["material"]]))
        material["name"] = part["name"]
        for key, value in part["factors"].items():
            if key == "extensions":
                material.setdefault("extensions", {}).update(value)
                used |= set(value)
            else:
                (material["pbrMetallicRoughness"] if key != "emissiveFactor" else material)[key] = value
        if part["bake"]:
            material.setdefault("extras", {})["score_bake"] = part["bake"]
        for primitive in mesh["primitives"]:
            primitive["material"] = len(materials)
        materials.append(material)
    document["materials"] = materials
    if used:
        document["extensionsUsed"] = sorted(set(document.get("extensionsUsed", [])) | used)
    return packed(document, binary)


def packed(document, binary):
    """A .gltf document and its one buffer as one GLB (each chunk padded to four bytes)."""
    text = json.dumps(document, separators=(",", ":")).encode()
    text += b" " * (-len(text) % 4)
    binary += b"\0" * (-len(binary) % 4)
    chunks = struct.pack("<I4s", len(text), b"JSON") + text
    if binary:
        chunks += struct.pack("<I4s", len(binary), b"BIN\0") + binary
    return struct.pack("<4sII", b"glTF", 2, 12 + len(chunks)) + chunks


def unpacked(glb, name):
    """A GLB as a .gltf document and its one buffer, named <name>.bin when a name is given, the same bytes (its
    pictures stay in it)."""
    json_length = struct.unpack_from("<I", glb, 12)[0]
    document = json.loads(glb[20:20 + json_length])
    rest = 20 + json_length
    binary = glb[rest + 8:rest + 8 + struct.unpack_from("<I", glb, rest)[0]] if rest < len(glb) else b""
    if binary and name:
        document["buffers"][0]["uri"] = f"{name}.bin"
    return document, binary


def entry_glb(prim):
    """The library entry's own GLB a glTF-only model or take was laid from (gltf.converted wrote its USD beside it),
    when the place laid it unchanged: no look of the place's on it and no layer of its own; else None."""
    stage = prim.GetStage()
    place = stage.GetDefaultPrim().GetName()
    looks = stage.GetPrimAtPath(f"/{place}/Looks")
    if looks and any(look.GetName() == prim.GetName() or look.GetName().startswith(f"{prim.GetName()}__")
                     for look in looks.GetChildren()):
        return None
    if any(place_build.is_layer(child) for child in prim.GetChildren()):
        return None
    for reference in prim.GetMetadata("references").GetAddedOrExplicitItems() if prim.HasMetadata("references") else []:
        usd = pathlib.Path(stage.GetRootLayer().realPath).parent / reference.assetPath
        own = usd.with_suffix(".glb")
        if usd.suffix == ".usdc" and own.is_file():
            glb = own.read_bytes()
            document, _ = unpacked(glb, None)
            if all("uri" not in item for item in document.get("images", [])) and len(document.get("buffers", [])) <= 1:
                return glb
    return None


# --- a copy ---------------------------------------------------------------------------------------------------------

def copy_frame(world):
    """How a copy stands: (its transform as scene.json keeps it, row-major, its even scale, the turn and stretch
    drawn into its object instead or None): its whole transform when that is a turn and an even scale, else its spot
    alone, its turn and stretch drawn into its own object."""
    linear = world[:3, :3]
    stretch = np.linalg.norm(linear, axis=1)
    basis = linear / stretch[:, None]
    if np.ptp(stretch) <= EVEN * stretch.max() and np.allclose(basis @ basis.T, np.eye(3), atol=1e-6) \
            and np.linalg.det(basis) > 0:
        return world, float(stretch.mean()), None
    spot = np.eye(4)
    spot[3, :3] = world[3, :3]
    return spot, 1.0, linear.copy()


def instance_of(name, object_name, kind, frame, scale):
    """One copy as scene.json has it: its matrix glTF's (column by column), its facing and tilt read off it."""
    column = frame.T
    forward = column[:3, :3] @ np.array([0.0, 0.0, -1.0]) / scale
    return {"object": object_name, "name": name, "kind": kind,
            "at": [round(float(value), 4) for value in column[:3, 3]],
            "facing": round(math.degrees(math.atan2(forward[0], -forward[2])), 4),
            "tilt": round(math.degrees(math.asin(max(-1.0, min(1.0, forward[1])))), 4), "scale": scale,
            "matrix": [round(float(value), 6) + 0.0 for value in column.T.reshape(-1)]}


def mass_of(folder, prim, scale):
    """A copy's mass from its entry's own record (the maker's `physics.mass_kg`, beside its files in the place's
    assets), times its scale cubed; None when the entry records none."""
    address = text_of(prim, "score:library")
    if not address or "@" not in address:
        return None
    entry_id = address.split("/", 1)[1].split("@")[0]
    record = pathlib.Path(folder) / "assets" / library_files.stage_name(
        library_files.reference(address, f"{entry_id}.json"))
    if not record.is_file():
        return None
    mass = json.loads(record.read_text()).get("physics", {}).get("mass_kg")
    return None if mass is None else round(float(mass) * scale ** 3, 4)


def collider_of(folder, prim, role, scale):
    """A copy's collider by its role in the physics check (COLLIDERS); None for a role that is no solid."""
    shape = COLLIDERS.get(role)
    if shape is None:
        return None
    if role == "prop":
        return {"shape": shape, "dynamic": True, "mass_kg": mass_of(folder, prim, scale)}
    return {"shape": shape, "dynamic": False}


# --- the package ----------------------------------------------------------------------------------------------------

def animated(prim):
    """Whether anything under the prim moves over time."""
    return any(attribute.GetNumTimeSamples() > 1 for inside in Usd.PrimRange(prim)
               for attribute in inside.GetAttributes())


def laid_objects(stage, place):
    """[(prim, kind)] of every object and effect laid, and [{name, why}] of those not converted."""
    found, left_out = [], []
    for scope, default in (("Objects", "object"), ("Effects", "effect"), ("Characters", "character")):
        holder = stage.GetPrimAtPath(f"/{place}/{scope}")
        for prim in holder.GetChildren() if holder else []:
            kind = text_of(prim, "score:kind") or default
            if kind == "light":
                left_out.append({"name": prim.GetName(), "why": "the place's sky dome: scene.json's environment"})
            elif prim.GetTypeName() == "SkelRoot":
                left_out.append({"name": prim.GetName(), "why": "a skinned character: not converted"})
            elif animated(prim):
                left_out.append({"name": prim.GetName(), "why": "it moves over time: not converted"})
            else:
                found.append((prim, kind))
    return found, left_out


def lamps_of(stage, place):
    """The place's lamps: a sphere light's spot, watts, radius and colour; a distant light's way it shines; each its
    USD intensity and its `strength` in Blender's units as the final render lights with it (SUN_STRENGTH)."""
    holder = stage.GetPrimAtPath(f"/{place}/Lights")
    lamps = []
    for prim in holder.GetChildren() if holder else []:
        world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        light = UsdLux.LightAPI(prim)
        about = {"name": prim.GetName(), "intensity": float(light.GetIntensityAttr().Get() or 0.0),
                 "colour": [round(float(value), 6) for value in light.GetColorAttr().Get() or (1.0, 1.0, 1.0)]}
        if prim.IsA(UsdLux.SphereLight):
            watts = round(about["intensity"] * math.pi, 6)
            lamps.append(dict(about, kind="point", at=[round(float(value), 4) for value in world[3, :3]],
                              watts=watts, strength=watts,
                              radius=float(UsdLux.SphereLight(prim).GetRadiusAttr().Get())))
        elif prim.IsA(UsdLux.DistantLight):
            shines = np.array([0.0, 0.0, -1.0]) @ world[:3, :3]
            lamps.append(dict(about, kind="sun", strength=about["intensity"] * SUN_STRENGTH,
                              shines=[round(float(value), 6) for value in shines / np.linalg.norm(shines)]))
    return lamps


def sky_way(prim):
    """A distant light's way toward its light as the sky step lays it (place_build.sun_frame): (elevation, heading)
    degrees, the heading round from +x towards +z."""
    world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    towards = world[2, :3] / np.linalg.norm(world[2, :3])
    return (round(math.degrees(math.asin(max(-1.0, min(1.0, float(towards[1]))))), 4),
            round(math.degrees(math.atan2(float(towards[2]), float(towards[0]))) % 360.0, 4))


def distant(prim):
    """A sun's or moon's record: where it stands (sky_way), its strength (Blender's W/m², as the final render lights
    with it: its intensity times SUN_STRENGTH), colour and width."""
    light = UsdLux.DistantLight(prim)
    elevation, heading = sky_way(prim)
    return {"name": prim.GetName(), "elevation": elevation, "heading": heading,
            "strength": float(light.GetIntensityAttr().Get() or 0.0) * SUN_STRENGTH,
            "colour": [round(float(value), 6) for value in light.GetColorAttr().Get() or (1.0, 1.0, 1.0)],
            "angle": float(light.GetAngleAttr().Get() or 0.0)}


def sky_picture(stage, place, out):
    """The sky dome's picture (the glow its dome under Objects/sky gives off, a longitude-latitude picture) copied
    into <out>/environment: {file, projection, turn (degrees about up, as laid), strength (its glow's), library};
    None when the place lays no sky picture."""
    holder = stage.GetPrimAtPath(f"/{place}/Objects/sky")
    for inside in gprims(holder) if holder else []:
        look = UsdShade.MaterialBindingAPI(inside).ComputeBoundMaterial()[0]
        shader = look.ComputeSurfaceSource()[0] if look else None
        found = texture_of(shader, "emissiveColor") if shader else None
        if found is None:
            continue
        (out / "environment").mkdir(exist_ok=True)
        shutil.copyfile(found[0], out / "environment" / found[0].name)
        turn = holder.GetAttribute("xformOp:rotateXYZ")
        return {"file": f"environment/{found[0].name}",
                "projection": "longitude-latitude: u round up from +x (tools/usd/mars_sky.ways), v from the "
                              "bottom pole up, on a ball round the place",
                "turn": float(turn.Get()[1]) if turn and turn.HasValue() else 0.0,
                "strength": float(text_of(inside, "score:sky_strength") or 1.0),
                "library": text_of(holder, "score:library")}
    return None


def environment_of(stage, place, out):
    """The place's sky and light as the final render draws it (usd_views.stage_sky, blender_views): the sky picture
    (sky_picture), the dome's ambient light, the background the camera sees, the exposure (a multiplier), the sun,
    the view transform and look; `night` its moon and glow where the place has a night (place_build.night)."""
    sky = stage.GetPrimAtPath(f"/{place}/Environment")
    lights = {prim.GetName(): prim for prim in (stage.GetPrimAtPath(f"/{place}/Lights").GetChildren()
                                                if stage.GetPrimAtPath(f"/{place}/Lights") else [])
              if prim.IsA(UsdLux.DistantLight)}
    found = {"sky": None, "ambient": None, "background": None, "exposure": 1.0, **VIEW,
             "sun": distant(lights["sun"]) if "sun" in lights else None, "night": None}
    if sky and sky.IsA(UsdLux.DomeLight):
        dome = UsdLux.DomeLight(sky)
        background = text_of(sky, "score:background")
        found.update(ambient=[round(float(value) * float(dome.GetIntensityAttr().Get() or 1.0), 6)
                              for value in dome.GetColorAttr().Get() or (1.0, 1.0, 1.0)],
                     background=None if background is None else [round(float(value), 6) for value in background],
                     exposure=float(text_of(sky, "score:exposure") or 1.0))
        if "moon" not in lights:
            found["sky"] = sky_picture(stage, place, out)
        else:
            found["night"] = {"moon": distant(lights["moon"]), "glow": {
                key: float(text_of(sky, f"score:glow_{key}")) for key in ("threshold", "intensity")}
                if text_of(sky, "score:glow_threshold") is not None else None}
    return found


def converted(prim, baked, made):
    """An object's glTF (GLB bytes), where it came from, and its check: the library entry's own when laid unchanged
    in an even copy, else converted from the laid USD (`made` the conversions so far, object_glb), its triangles
    counted against the USD's."""
    import trimesh
    usd_triangles = sum(len(found[2]) for found in (drawn(inside) for inside in gprims(prim)) if found is not None)
    own = entry_glb(prim) if baked is None else None
    if own is not None:
        loaded = trimesh.load(trimesh.util.wrap_as_stream(own), file_type="glb", force="mesh", skip_materials=True)
        return own, "library glTF", {"pass": len(loaded.faces) == usd_triangles > 0, "triangles": len(loaded.faces),
                                     "usd_triangles": usd_triangles}
    glb, triangles = object_glb(prim, baked, made)
    if glb is None:
        return None, None, None
    loaded = trimesh.load(trimesh.util.wrap_as_stream(glb), file_type="glb", force="mesh", skip_materials=True)
    return glb, "converted from the laid USD", {"pass": len(loaded.faces) == triangles == usd_triangles > 0,
                                                "triangles": len(loaded.faces), "usd_triangles": usd_triangles}


def written(out, name, glb):
    """An object's GLB written as objects/<name>.gltf and its .bin."""
    document, binary = unpacked(glb, name)
    (out / "objects" / f"{name}.gltf").write_text(json.dumps(document))
    if binary:
        (out / "objects" / f"{name}.bin").write_bytes(binary)


def box_size(glb):
    import trimesh
    loaded = trimesh.load(trimesh.util.wrap_as_stream(glb), file_type="glb", force="mesh", skip_materials=True)
    return [round(float(side), 4) for side in np.ptp(loaded.vertices, axis=0)]


def write(folder, out):
    """The laid place in <folder> as a scene package in <out>; scene.json's content."""
    folder, out = pathlib.Path(folder), pathlib.Path(out)
    stage, place = place_build.opened(folder)
    ready_file = folder / "ready.json"
    roles = json.loads(ready_file.read_text())["roles"] if ready_file.is_file() else None
    if out.exists():
        shutil.rmtree(out)
    (out / "objects").mkdir(parents=True)
    found, left_out = laid_objects(stage, place)
    objects, instances, by_content, counts, made = {}, [], {}, {}, {}
    for prim, kind in found:
        world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        frame, scale, baked = copy_frame(world)
        glb, route, check = converted(prim, baked, made)
        if glb is None:
            left_out.append({"name": prim.GetName(), "why": "it draws no face"})
            continue
        digest = hashlib.sha256(glb).hexdigest()
        if digest not in by_content:
            by_content[digest] = prim.GetName()
            written(out, prim.GetName(), glb)
            objects[prim.GetName()] = {"file": f"objects/{prim.GetName()}.gltf", "kind": kind, "route": route,
                                       "size": box_size(glb), "triangles": check["triangles"], "check": check}
        copy = instance_of(prim.GetName(), by_content[digest], kind, frame, scale)
        if roles is not None:
            copy["role"] = roles.get(prim.GetName())
            copy["collider"] = collider_of(folder, prim, copy["role"], scale)
        instances.append(copy)
        counts[kind] = counts.get(kind, 0) + 1
    scene = {"format": package.FORMAT, "version": package.VERSION, "place": place,
             "frame": "the place's own frame: metres, y up", "units": "metre", "up": "+y", "ground": GROUND,
             "on_seat": [0.0, 0.0], "objects": objects, "instances": instances, "children": [],
             "lamps": lamps_of(stage, place), "counts": counts, "physics": "ready.json" if roles is not None else None,
             "left_out": left_out, "environment": environment_of(stage, place, out)}
    (out / "scene.json").write_text(json.dumps(scene, indent=1) + "\n")
    return scene


# --- the bake -------------------------------------------------------------------------------------------------------

PICTURES = ("base_color", "metal_roughness", "normal")  # a baked map's pictures, as glTF reads them


def bake_jobs(out):
    """Every baked map the package's objects ask for (a material's `score_bake`): [{gltf, material (its number),
    mesh (its part's node), spec, size, tile, pictures {kind: path under objects/}}]."""
    jobs = []
    for path in sorted((out / "objects").glob("*.gltf")):
        document = json.loads(path.read_text())
        for mesh in document.get("meshes", []):
            number = mesh["primitives"][0].get("material")
            asked = None if number is None else document["materials"][number].get("extras", {}).get("score_bake")
            if asked:
                stem = f"{path.stem}_{mesh['name']}"
                jobs.append({"gltf": f"objects/{path.name}", "material": number, "mesh": mesh["name"],
                             "spec": asked["spec"], "size": asked["size"], "tile": asked["tile"],
                             "texels_a_metre": asked["texels_a_metre"],
                             "pictures": {kind: f"{TEXTURES}/{stem}_{kind}.png" for kind in PICTURES}})
    return jobs


def blender_baked(out, jobs):
    """The jobs baked by bake_looks.py in headless Blender on this PC's card, through the card queue (render.queued),
    its log in <out>/bake/blender.log; Refused with the log's tail when a picture is missing."""
    import subprocess
    from score.stages.place_build import render
    listing = out / "bake" / "jobs.json"
    listing.parent.mkdir(exist_ok=True)
    listing.write_text(json.dumps({"out": str(out.resolve()), "jobs": jobs}, indent=1))
    log = out / "bake" / "blender.log"
    script = pathlib.Path(__file__).resolve().parent / "bake_looks.py"
    with log.open("w") as written_log:
        done = subprocess.run(render.queued(f"place-build-bake-{out.name}", script, [str(listing.resolve())]),
                              stdout=written_log, stderr=subprocess.STDOUT, cwd=place_build.REPO)
    missing = [picture for job in jobs for picture in job["pictures"].values()
               if not (out / "objects" / picture).is_file()]
    if done.returncode or missing:
        tail = " | ".join(log.read_text(errors="replace").splitlines()[-6:])
        raise place_build.Refused(f"the bake failed (exit {done.returncode}, {len(missing)} pictures missing), "
                                  f"log {log}: {tail}")


def embedded(document, binary, picture):
    """A picture's PNG bytes appended to the object's buffer (4-byte aligned) as its own buffer view: its image
    {bufferView, mimeType}. glTFast hands a linear picture named by a uri (a metal-roughness or normal map) to its
    material as white (seen on the camp, 2026-11-18: every baked part drawn as bare metal), and loads one from the
    buffer as a library GLB's."""
    binary.extend(b"\0" * (-len(binary) % 4))
    document.setdefault("bufferViews", []).append({"buffer": 0, "byteOffset": len(binary),
                                                   "byteLength": len(picture)})
    binary.extend(picture)
    return {"bufferView": len(document["bufferViews"]) - 1, "mimeType": "image/png"}


def attached(out, jobs):
    """Each baked map's pictures put on its material in its .gltf (base colour, metal-roughness, normal, each read by
    the part's first texture coordinates, repeated: a ground's tile repeats), carried in the object's own buffer
    (embedded) and their files under objects/textures/ removed, its factors made the pictures' own (white base colour
    under its opacity, metal and roughness 1) and its bake request taken off."""
    by_file = {}
    for job in jobs:
        by_file.setdefault(job["gltf"], []).append(job)
    for name, held in by_file.items():
        path = out / name
        document = json.loads(path.read_text())
        buffer_path = path.parent / document["buffers"][0]["uri"]
        binary = bytearray(buffer_path.read_bytes())
        document.setdefault("samplers", []).append({"magFilter": 9729, "minFilter": 9987, "wrapS": 10497,
                                                     "wrapT": 10497})
        sampler = len(document["samplers"]) - 1
        for job in held:
            numbers = {}
            for kind in PICTURES:
                picture = out / "objects" / job["pictures"][kind]
                document.setdefault("images", []).append(embedded(document, binary, picture.read_bytes()))
                picture.unlink()
                document.setdefault("textures", []).append({"source": len(document["images"]) - 1,
                                                            "sampler": sampler})
                numbers[kind] = len(document["textures"]) - 1
            material = document["materials"][job["material"]]
            metal = material.setdefault("pbrMetallicRoughness", {})
            opacity = metal.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])[3]
            metal.update(baseColorFactor=[1.0, 1.0, 1.0, opacity], metallicFactor=1.0, roughnessFactor=1.0,
                         baseColorTexture={"index": numbers["base_color"]},
                         metallicRoughnessTexture={"index": numbers["metal_roughness"]})
            material["normalTexture"] = {"index": numbers["normal"]}
            material.get("extras", {}).pop("score_bake", None)
            if "extras" in material and not material["extras"]:
                del material["extras"]
        document["buffers"][0]["byteLength"] = len(binary)
        buffer_path.write_bytes(bytes(binary))
        path.write_text(json.dumps(document))
    if (out / "objects" / TEXTURES).is_dir() and not any((out / "objects" / TEXTURES).iterdir()):
        (out / "objects" / TEXTURES).rmdir()
    return len(jobs)


def blender_graded(out, environment):
    """The final render's grade (its view transform and look) as Blender's own OpenColorIO draws it, written by
    grade_lut.py to <out>/GRADE_FILE (no card: it draws nothing); Refused with the log's tail when it is missing."""
    import subprocess
    from score.stages.place_build import render
    (out / GRADE_FILE).parent.mkdir(exist_ok=True)
    script = pathlib.Path(__file__).resolve().parent / "grade_lut.py"
    done = subprocess.run(render.queued(f"place-build-grade-{out.name}", script, [
        str((out / GRADE_FILE).resolve()), environment["view_transform"], environment["look"],
        *(str(GRADE[key]) for key in ("size", "low", "high", "middle"))], card=False),
        capture_output=True, text=True, cwd=place_build.REPO)
    if done.returncode or not (out / GRADE_FILE).is_file():
        tail = " | ".join((done.stdout + done.stderr).splitlines()[-6:])
        raise place_build.Refused(f"the grade failed (exit {done.returncode}): {tail}")


def ground_albedo(out, jobs):
    """The laid ground's mean base colour, linear [r, g, b], from its baked tile's picture (the one job with a tile);
    None when no ground tile was baked."""
    tiled = [job for job in jobs if job["tile"]]
    if not tiled:
        return None
    picture = np.asarray(Image.open(out / "objects" / tiled[0]["pictures"]["base_color"]).convert("RGB"),
                         dtype=np.float64) / 255.0
    linear = np.where(picture <= 0.04045, picture / 12.92, ((picture + 0.055) / 1.055) ** 2.4)
    return [round(float(value), 6) for value in linear.reshape(-1, 3).mean(axis=0)]


def packaged(folder, out, baker=blender_baked, grader=blender_graded):
    """The package written, its palette recipes baked (`baker(out, jobs)` writes each job's pictures) and put on
    their looks, its grade drawn (`grader(out, environment)` writes GRADE_FILE: environment `grade`), and checked
    by package.py's own check: its summary, or Refused naming its problems."""
    out = pathlib.Path(out)
    scene = write(folder, out)
    jobs = bake_jobs(out)
    scene["environment"]["ground_albedo"] = None
    if jobs:
        (out / "objects" / TEXTURES).mkdir(exist_ok=True)
        baker(out, jobs)
        scene["environment"]["ground_albedo"] = ground_albedo(out, jobs)
        attached(out, jobs)
    grader(out, scene["environment"])
    scene["environment"]["grade"] = dict(GRADE, file=GRADE_FILE, display="sRGB", layout=(
        "size tiles of size x size side by side: red along a tile, blue tile by tile, green up from the bottom row"))
    (out / "scene.json").write_text(json.dumps(scene, indent=1) + "\n")
    found = package.problems(pathlib.Path(out))
    if found:
        raise place_build.Refused(f"the package fails its check: {'; '.join(found[:12])}")
    return {"package": str(out), "summary": package.summary(pathlib.Path(out)), "objects": len(scene["objects"]),
            "copies": len(scene["instances"]), "left_out": scene["left_out"], "baked_maps": len(jobs),
            "sky": (scene["environment"]["sky"] or {}).get("file"), "check": "sound"}
