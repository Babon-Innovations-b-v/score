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
(bake_looks.py): the part unwrapped (xatlas; its big faces cut, in blocks no wider than a map) at DENSITY texels a
metre on maps each as big as its charts and at most LARGEST, each map its own primitive and material, or on a laid
ground one seamless GROUND_TILE box-projected; its base colour, metal-roughness and normal pictures carried in the
object's own buffer. Every picture an object carries (baked, an image surface's, a library glTF's, a character's) is
written at most HELD_TEXELS a side, as the game holds it (a bigger one halved as its mips are made), and pictures of
one object alike in bytes and in how they are read are one picture (pictures_held). A glTF-only model or take laid in its own bake (no look of the place's on it) goes as its library
entry's own glTF, unchanged.
Two objects that convert to the same file are one object. A copy turned and scaled evenly keeps its object in its
own frame (`matrix` the whole transform); a copy stretched unevenly has its stretch baked into its own object.

When the place's physics check has run (<folder>/ready.json, ready/), each copy carries its collider by its role
(COLLIDERS): a prop a convex hull, free, its mass the entry's own record (the maker's `physics.mass_kg`, times its
scale cubed) or null when the entry has none; everything else that stands a solid its mesh, fixed.
Every character laid (a SkelRoot under /<place>/Objects or /<place>/Characters, or a crowd's PointInstancer of them,
a copy each) is its own skinned glTF (skinned.py: its skeleton, shown skinned meshes and morph targets, every clip and
the animation it plays, checked against UsdSkel's own skin), its copy's `plays` the animation it plays from when; the
sky's dome, animated effects and a character skinned.py cannot carry as drawn are not converted: scene.json's
`left_out` names each.
Each door (an object the physics check takes for one, ready.role_of) carries its `door` block (doors_of): it moves as
its one whole piece the way the walkers open it (ready.opening: slid aside along its face when marked score:move
slide, else on a hinge, a pressure door swung to its high-pressure side), its opening, its score:opens mark and the
enclosures either side of it; an airlock chamber (locks_of: the object a door's score:lock names, its inner and outer
doors by their score:side, or a shell or connector a door from another enclosure and a door from outside open into)
is in scene.json's `chambers`, with its air's volume.
scene.json's `environment` is the place's sky and light as the final render draws them (environment_of): the sky's
picture written into <out>/environment, its turn and glow, the ambient light, background, exposure, the sun, the AgX
view transform and look, a night's moon and glow, the ground's albedo (ground_albedo: what an engine without
path-traced bounce lights from below with), and `grade`: that view transform and look drawn by Blender's own
OpenColorIO into a lattice picture (grade_lut.py), the engine's tone mapping sampling it as SCORE's render grades.
"""
import concurrent.futures
import contextlib
import faulthandler
import hashlib
import json
import math
import pathlib
import shutil
import struct
import threading

import numpy as np
from PIL import Image
from pxr import Gf, Usd, UsdGeom, UsdLux, UsdShade

from score.stages import place_build
from score.stages.place_build import skinned
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
NEAR = 2.0  # metres from an eye within which a face gets DENSITY (a texel a pixel at 2 m, above); farther, less (#153)
EYE_CELL = 1.0  # metres: the walkers' eyes kept one a cube this wide (thinned), each face's distance less its diagonal
LEAST_DENSITY = 16  # texels a metre no baked face goes under however far (6 cm a texel: a far wall's courses still read)
LARGEST = 4096
PADDING = 4
SPAN_SHARE = 0.9  # how much of a map's side one block of a part may span (blocks_of): its charts' slack
FILL = 0.5  # how much of a LARGEST map one group of blocks may hold at DENSITY (map_groups): xatlas's packing slack
HELD_SHARE = 0.97  # a map holding its charts under this share of DENSITY is refused (unwrapped)
GROUND_TILE = 8.0  # metres one seamless tile of a laid ground's recipe covers: LARGEST texels at DENSITY
FLAT_RECIPES = ("glass", "glowing")  # recipes of one colour, roughness and glow: their factors are exact, no bake
GLASS_IOR = 1.5  # a see-through look's glass (blender_views.GLASS_IOR)
TEXTURES = "textures"  # the baked pictures' folder beside the objects' .gltf files
HELD_TEXELS = 2048  # the longest side a package's picture is written at: the side the game holds it at (2099 #161,
# PlaceTextures.MostTexels), so a picture over it is written as the game's own taken-down mip, never decoded at 4096
BLOCK_TEXELS = 4  # every picture written has sides a multiple of this: an engine compresses it in 4 x 4 blocks
# (DXT/BC), and 2099 held one of another side raw (flat@4: 4.4 GB of its 5.5 GB uncompressed, 1182 x 1792 maps)
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
# Every step of a package runs under its time (deadline, blender_run, blender_graded), never for hours unseen (the
# base, 2026-11-20: a part's unwrap ran 11.5 h at 100% CPU): an object's or a character's conversion, the scene's
# doors, chambers and sky, a Blender run of BATCH maps (its wait for the card not counted), the grade. Each step is
# named in STEPS first.
STEP_SECONDS = {"object": 900, "scene": 900, "bake run": 1800, "grade": 600}
STEPS = "bake/steps.log"
SUN_NAMES = ("sun", "sky_sun")  # the sky step's sun, else sky-at's (light/sky.py: Lights/sky_<the Sun's key>)
PROBE = 0.3  # metres past a door's face (its depth's half and this) where the place on that side is read
# A draft package (`package --draft`, 2099 #161: a look at the place in the game in minutes, never kept): written as
# a real one, every palette recipe its look's plain colour, metal and roughness instead of its baked maps (an image
# surface keeps its own pictures, a glTF model its own), scene.json `draft` this mark; score-lib take-in --place
# refuses a folder whose package carries it, so a draft never reaches score_lib and the game takes it only as a
# local preview.
DRAFT = {"baked": False, "why": "a preview: palette recipes as their plain colour, metal and roughness, never baked; "
                                "never kept (score-lib take-in refuses it)"}


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
    return held_image(Image.merge("RGB", (Image.new("L", size, 255), rough, metallic)))


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


def pbr(look, ground=False, draft=False):
    """A bound look as glTF PBR: {"material": trimesh PBRMaterial, "tile": metres or None, "key": what tells it,
    "bake": a palette recipe's bake or None}. A recipe with a pattern (not FLAT_RECIPES) is baked as Blender draws it
    (bake_looks.py): on a laid ground (`ground`) as one seamless GROUND_TILE box-projected like an image surface, on
    anything else into its own unwrapped maps at DENSITY; in a `draft` it is never baked, its look's plain colour,
    metal and roughness alone (DRAFT)."""
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
    bake = {"spec": spec, "tile": GROUND_TILE if ground else None} if spec and not draft and \
        spec.get("recipe") not in FLAT_RECIPES else None
    material = trimesh.visual.material.PBRMaterial(
        name=look_name(look), baseColorFactor=[float(value) for value in colour] + [opacity],
        metallicFactor=1.0 if combined else metallic, roughnessFactor=1.0 if combined else roughness,
        emissiveFactor=glow, alphaMode="BLEND" if opacity < 1.0 else "OPAQUE", doubleSided=True,
        baseColorTexture=held_image(Image.open(colour_map[0]).convert("RGBA" if opacity < 1.0 else "RGB"))
        if colour_map else None,
        metallicRoughnessTexture=combined,
        normalTexture=held_image(Image.open(normal_map[0]).convert("RGB")) if normal_map else None,
        emissiveTexture=held_image(Image.open(glow_map[0]).convert("RGB")) if glow_map else None)
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


def looks_of(prim, draft=False):
    """Every look bound inside the object as glTF PBR, by key (a laid ground's recipes tiled, a `draft`'s never baked:
    pbr)."""
    looks, ground = {}, bool(text_of(prim, "score:ground"))
    for inside in gprims(prim):
        found = drawn(inside)
        if found is None or not len(found[2]):
            continue
        for look in face_looks(inside, int(found[3].max()) + 1)[0]:
            if pbr_key(look) not in looks:
                looks[pbr_key(look)] = pbr(look, ground, draft)
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


def gathered_of(prim, baked, draft=False):
    """The object's corners by look ({look: [(positions, normals, uv)]}, `baked` drawn in) and its looks (looks_of)."""
    looks = looks_of(prim, draft)
    gathered = {}
    for inside in gprims(prim):
        for key, (positions, normals, uv) in gprim_pieces(inside, prim, baked, looks).items():
            gathered.setdefault(key, []).append((positions, normals, uv))
    return gathered, looks


def object_glb(prim, baked, made, sights=None, draft=False):
    """The object's GLB (a primitive a look) in its own frame, `baked` (a row-major 3 x 3, or None) drawn into it, its
    triangle count and the triangles its unwrap cut them into besides (subdivided); None when it draws no face. `made`
    holds the GLBs written so far by what tells them (`told`) and what they copy (copied_from), so a copy of one already
    made is not written again; `sights` the walkers' eyes in each content's frame by what it copies (eyes_by_content),
    every copy's together; a `draft`'s recipes never baked (pbr)."""
    gathered, looks = gathered_of(prim, baked, draft)
    if not gathered:
        return None, 0, 0
    tells = (told(gathered, looks), copied_from(prim, baked))
    if tells not in made:
        made[tells] = gltf_written(gathered, looks, (sights or {}).get(tells[1]))
    return made[tells]


def eyes_by_content(stage, place, found):
    """The walkers' eyes (ready.look_points over the walkers' floor with every door open, thinned) in each object's own
    frame, by what it copies (copied_from), every copy's eyes together, so one content is baked once at the density its
    nearest copy needs (#153); only eyes within reach of a density over LEAST_DENSITY of its box are kept. {} when the
    place has no physics roles (no walkers' floor)."""
    from score.stages.place_build import ready
    laid = ready.Place(stage, place)
    if not laid.names:
        return {}
    eyes = thinned(ready.look_points(ready.walkers_floor(laid)[:4]))
    if not len(eyes):
        return {}
    farthest = DENSITY * NEAR / LEAST_DENSITY
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    sights = {}
    for prim, _ in found:
        world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        frame, _, baked = copy_frame(world)
        box = boxes.ComputeUntransformedBound(prim).ComputeAlignedRange()
        if box.IsEmpty():
            continue
        corners = np.array([[box.GetMin()[0], box.GetMin()[1], box.GetMin()[2]],
                            [box.GetMax()[0], box.GetMax()[1], box.GetMax()[2]]])
        corners = np.array([[corners[x, 0], corners[y, 1], corners[z, 2]] for x in (0, 1) for y in (0, 1)
                            for z in (0, 1)]) @ (baked if baked is not None else np.eye(3))
        low, high = corners.min(axis=0), corners.max(axis=0)
        local = (eyes - frame[3, :3]) @ np.linalg.inv(frame[:3, :3])
        outside = np.linalg.norm(np.maximum(np.maximum(low - local, local - high), 0.0), axis=1)
        key = copied_from(prim, baked)
        sights[key] = thinned(np.vstack([sights.get(key, np.zeros((0, 3))), local[outside <= farthest]]))
    return sights


def copied_from(prim, baked):
    """What a copy copies, read without its corners: its references and the turn and stretch drawn into it (copy_frame),
    else its own path. Two copies of one content always share it; two that share it and differ only pool their eyes,
    which only raises a density (eyes_by_content)."""
    references = prim.GetMetadata("references").GetAddedOrExplicitItems() if prim.HasMetadata("references") else []
    drawn = None if baked is None else tuple(np.round(baked, 6).ravel().tolist())
    return (tuple(str(reference.assetPath) for reference in references) or str(prim.GetPath()), drawn)


def thinned(points):
    """The points kept one an EYE_CELL cube (its middle): a face's density reads its distance to the nearest less the
    cube's diagonal (densities), so thinning never lowers a face's density below what an eye in the cube needs."""
    return (np.unique(np.floor(np.asarray(points) / EYE_CELL), axis=0) + 0.5) * EYE_CELL if len(points) else \
        np.zeros((0, 3))


def areas_of(points, faces):
    corners = points[faces]
    return 0.5 * np.linalg.norm(np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]), axis=-1)


def span(density=None):
    """Metres one block of a part may span on its map at `density` (SPAN_SHARE of a LARGEST map inside its padding;
    one a face when `density` is each face's)."""
    density = DENSITY if density is None else density
    metres = (LARGEST - 2 * PADDING) / np.asarray(density, float) * SPAN_SHARE  # each face's, given each's density
    return float(metres) if np.ndim(metres) == 0 else metres


def held(density=None):
    """Square metres of surface one map's charts may hold at `density`: FILL of a LARGEST map."""
    density = DENSITY if density is None else density
    return LARGEST ** 2 * FILL / density ** 2


def densities(middles, reach_out, eyes):
    """Each face's texels a metre (#153): DENSITY where an eye (ready.look_points, in the object's frame) comes within
    NEAR of it, else DENSITY * NEAR over its distance (a texel a pixel at 1920x1080 under 60 degrees) raised to a
    power of two so faces at like distances share maps, never under LEAST_DENSITY; a face's distance is its middle's
    less `reach_out` (half its longest edge), so no part of it is seen nearer than its density serves. DENSITY on
    every face when no eyes are given (None: a place without a walkers' floor), LEAST_DENSITY when none is near enough
    to need more (an empty set: eyes_by_content keeps only those within reach)."""
    if eyes is None:
        return np.full(len(middles), DENSITY)
    if not len(eyes):
        return np.full(len(middles), LEAST_DENSITY)
    import scipy.spatial
    slack = EYE_CELL * np.sqrt(3.0)  # an eye stands anywhere in its thinned cube
    distance = np.maximum(scipy.spatial.cKDTree(eyes).query(middles)[0] - reach_out - slack, NEAR)
    need = np.ceil(np.log2(np.maximum(DENSITY * NEAR / distance, LEAST_DENSITY)))
    return np.minimum(2 ** need.astype(int), DENSITY)


def subdivided(vertices, normals, faces, eyes=None):
    """The mesh with every triangle whose longest edge is over half a span at its density (span, densities: `eyes` in
    its frame) cut at that edge's middle until none is, the new corners' normals the edge's ends' mean: the same
    surface, so no one face is a chart wider than its map (the base's hangar: 44 faces over 4153 m², each its own
    block, packed as one map 33,000 texels wide by xatlas for 11.5 h), a face seen from far cut no finer than its
    own density's span (the square's far shore at DENSITY's: 19,184 triangles cut into 278,388); with each face's
    density: (vertices, normals, faces, densities)."""
    vertices, normals, faces = np.asarray(vertices, float), np.asarray(normals, float), np.asarray(faces)
    while True:
        corners = vertices[faces]
        lengths = np.linalg.norm(corners[:, [1, 2, 0]] - corners, axis=-1)  # edge k from corner k to corner k + 1
        banded = densities(corners.mean(axis=1), lengths.max(axis=1) / 2, eyes)
        over = lengths.max(axis=1) > span(banded) / 2
        if not over.any():
            return vertices, normals, faces, banded
        cut = faces[over]
        edge = lengths[over].argmax(axis=1)
        ring = np.arange(len(cut))
        first, second, third = (cut[ring, (edge + step) % 3] for step in range(3))
        middles = len(vertices) + ring
        way = normals[first] + normals[second]
        way /= np.maximum(np.linalg.norm(way, axis=1, keepdims=True), 1e-12)
        vertices = np.vstack([vertices, (vertices[first] + vertices[second]) / 2])
        normals = np.vstack([normals, way])
        faces = np.vstack([faces[~over], np.stack([first, middles, third], 1), np.stack([middles, second, third], 1)])


def halves(vertices, faces, chosen):
    """The faces `chosen` cut in two across their box's longest side, by the faces' middles (in index order when all
    middles fall on one side)."""
    corners = vertices[faces[chosen]]
    axis = int(np.ptp(corners.reshape(-1, 3), axis=0).argmax())
    middles = corners.mean(axis=1)[:, axis]
    low = middles < (corners[..., axis].min() + corners[..., axis].max()) / 2
    if low.all() or not low.any():
        low = np.arange(len(chosen)) < len(chosen) // 2
    return chosen[low], chosen[~low]


def blocks_of(vertices, faces, chosen, density=None):
    """The faces `chosen` cut into blocks no wider than a map holds at DENSITY (span) and holding no more surface than
    a map's worth (held): each block halved (halves) until it fits; so no chart xatlas makes is wider than its map, no
    block needs more than one, and none is shrunk to fit (a dome's 10 m deck as one chart came out at 390 texels a
    metre)."""
    box = np.ptp(vertices[faces[chosen]].reshape(-1, 3), axis=0)
    if (box.max() <= span(density) and areas_of(vertices, faces[chosen]).sum() <= held(density)) or len(chosen) == 1:
        return [chosen]
    return [block for half in halves(vertices, faces, chosen) for block in blocks_of(vertices, faces, half, density)]


def map_groups(vertices, faces, blocks, density=None):
    """The blocks (in blocks_of's order, side by side in space) gathered into maps' worth: each group's surface at
    DENSITY at most FILL of a LARGEST map, so each is packed alone into one map of its own size."""
    groups, area = [[]], 0.0
    for chosen in blocks:
        surface = float(areas_of(vertices, faces[chosen]).sum())
        if groups[-1] and area + surface > held(density):
            groups.append([])
            area = 0.0
        groups[-1].append(chosen)
        area += surface
    return groups


def atlas_of(vertices, normals, faces, group, density=None):
    """One map of blocks packed by xatlas at DENSITY, PADDING round each chart, its size as its charts need (no fixed
    resolution, so no chart is scaled to fit), each chart's boundary at most twice a span so none is wider than a map;
    None when that map is over LARGEST a side."""
    import xatlas
    density = DENSITY if density is None else density
    atlas = xatlas.Atlas()
    for chosen in group:
        kept, inverse = np.unique(faces[chosen], return_inverse=True)
        atlas.add_mesh(vertices[kept].astype(np.float32), inverse.reshape(-1, 3).astype(np.uint32),
                       normals[kept].astype(np.float32))
    charting = xatlas.ChartOptions()
    charting.max_boundary_length = 2 * span(density)
    packing = xatlas.PackOptions()
    packing.texels_per_unit, packing.padding, packing.bilinear, packing.blockAlign = density, PADDING, True, True
    atlas.generate(chart_options=charting, pack_options=packing)
    return atlas if max(atlas.width, atlas.height) <= LARGEST and atlas.atlas_count <= 1 else None


def mapped(vertices, normals, faces, group, density=None):
    """The group's blocks on maps of at most LARGEST: one map when it packs into one (atlas_of), else the group halved
    (a lone block cut in its own halves) and each half mapped; [(atlas, the blocks on it)]. Refused when one face
    alone needs more than a map."""
    atlas = atlas_of(vertices, normals, faces, group, density)
    if atlas is not None:
        return [(atlas, group)]
    if len(group) == 1 and len(group[0]) == 1:
        raise place_build.Refused(f"a face needs more than a {LARGEST} map at {density or DENSITY} texels a metre")
    parts = [[half] for half in halves(vertices, faces, group[0])] if len(group) == 1 else \
        [group[:len(group) // 2], group[len(group) // 2:]]
    return [laid for part in parts for laid in mapped(vertices, normals, faces, part, density)]


def unwrapped(vertices, normals, faces, eyes=None):
    """A mesh laid flat for its bake (subdivided, cut into blocks: blocks_of, gathered a map's worth a group:
    map_groups) at DENSITY texels a metre on maps each as big as its charts need and at most LARGEST a side:
    [(vertices, normals, uv, faces, [width, height], texels a metre as laid)] a map. Refused when a map holds its
    charts under its density (#146: xatlas packing at a fixed resolution scaled charts down to 147 texels a metre).
    Each face's density is set by how near the walkers' eyes come (`eyes`, in the mesh's frame: densities), its
    faces of one density on maps of their own."""
    vertices, normals, faces, banded = subdivided(vertices, normals, faces, eyes)
    found = []
    for density, group in ((density, group) for density in sorted(set(banded.tolist()), reverse=True)
                           for group in map_groups(vertices, faces, blocks_of(
                               vertices, faces, np.flatnonzero(banded == density), density), density)):
        for atlas, held in mapped(vertices, normals, faces, group, density):
            size = [int(atlas.width), int(atlas.height)]
            points, ways, coordinates, triangles = [], [], [], []
            for number, chosen in enumerate(held):
                kept = np.unique(faces[chosen])
                mapping, corners, uv = atlas[number]
                triangles.append(corners + sum(len(block) for block in points))
                points.append(vertices[kept[mapping]])
                ways.append(normals[kept[mapping]])
                coordinates.append(uv.astype(np.float64))
            points, coordinates, triangles = np.vstack(points), np.vstack(coordinates), np.vstack(triangles)
            texels = np.sqrt(areas_of(np.hstack([coordinates * size, np.zeros((len(coordinates), 1))]),
                                      triangles).sum() / max(areas_of(points, triangles).sum(), 1e-12))
            if texels < density * HELD_SHARE:
                raise place_build.Refused(f"a map of {size[0]}x{size[1]} holds its charts at {texels:.1f} texels a "
                                          f"metre, under {density}")
            found.append((points, np.vstack(ways), coordinates, triangles, size, round(float(texels), 1)))
    return found


def gltf_written(gathered, looks, eyes=None):
    """The GLB of an object's corners grouped by look (a recipe to bake on its own unwrapped maps, a part a map), its
    triangle count and the triangles its unwrap cut them into besides (subdivided); `eyes` the walkers' eyes in its
    frame (eyes_by_content), each baked face's density set by them (unwrapped)."""
    import trimesh
    scene, triangles, written_triangles, parts = trimesh.Scene(), 0, 0, []
    for key in sorted(gathered):
        pieces = gathered[key]
        with_uv = all(piece[2] is not None for piece in pieces)
        vertices, normals, uv, faces = welded(np.vstack([piece[0] for piece in pieces]),
                                              np.vstack([piece[1] for piece in pieces]),
                                              np.vstack([piece[2] for piece in pieces]) if with_uv else None)
        bake = looks[key].get("bake")
        maps = unwrapped(vertices, normals, faces, eyes) if bake and not bake["tile"] else \
            [(vertices, normals, uv, faces, [LARGEST, LARGEST], LARGEST / bake["tile"]) if bake else
             (vertices, normals, uv, faces, None, None)]
        triangles += len(faces)
        for page, (vertices, normals, uv, faces, size, texels) in enumerate(maps):
            number = len(parts)
            mesh = trimesh.Trimesh(vertices=vertices, faces=faces, vertex_normals=normals, process=False)
            mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=looks[key]["material"])
            scene.add_geometry(mesh, node_name=f"part_{number}", geom_name=f"part_{number}")
            written_triangles += len(faces)
            asked = dict(bake, size=size, texels_a_metre=texels) if bake else None
            parts.append({"factors": looks[key].get("factors", {}), "bake": asked,
                          "name": looks[key]["material"].name + (f" map{page + 1}" if len(maps) > 1 else "")})
    return exactly(scene.export(file_type="glb"), parts), triangles, written_triangles - triangles


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


# --- doors and airlocks ---------------------------------------------------------------------------------------------

def part_points(prim, part):
    """The scene-frame points of the faces in the GeomSubset `part` of every mesh under an object (empty: none)."""
    found = []
    for inside in gprims(prim):
        if not inside.IsA(UsdGeom.Mesh):
            continue
        subsets = [subset for subset in UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Imageable(inside))
                   if subset.GetPrim().GetName() == part]
        if not subsets:
            continue
        mesh = UsdGeom.Mesh(inside)
        counts = np.asarray(mesh.GetFaceVertexCountsAttr().Get(), dtype=np.int64)
        indices = np.asarray(mesh.GetFaceVertexIndicesAttr().Get(), dtype=np.int64)
        starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
        faces = np.concatenate([np.asarray(subset.GetIndicesAttr().Get(), dtype=np.int64) for subset in subsets])
        corners = np.concatenate([indices[starts[face]:starts[face] + counts[face]] for face in faces])
        world = np.asarray(UsdGeom.Xformable(inside).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
        points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)[corners]
        found.append(points @ world[:3, :3] + world[3, :3])
    return np.vstack(found) if found else np.zeros((0, 3))


def hull_of(points):
    """A convex hull's planes (n x 4: outward normal, offset) and volume, or None for points that span no volume."""
    from scipy.spatial import ConvexHull, QhullError
    try:
        hull = ConvexHull(points)
    except QhullError:
        return None
    return hull.equations, float(hull.volume)


def air_of(laid, name):
    """An enclosure's air: the convex hull of its solid over its deck's top (each point below it raised onto it), a
    tunnel's or dome's `deck` part, or the solid's own foot when it has none; (planes, volume) or None."""
    points = np.asarray(laid.meshes[name].vertices, dtype=np.float64)
    deck = part_points(laid.prims[name], "deck")
    floor = float(deck[:, 1].max()) if len(deck) else float(points[:, 1].min())
    return hull_of(np.column_stack([points[:, 0], np.maximum(points[:, 1], floor), points[:, 2]]))


def enclosure_at(airs, point):
    """The enclosure whose air holds a point (the smallest, when one lies in another), or None: outside."""
    holding = [(volume, name) for name, (planes, volume) in airs.items()
               if (planes[:, :3] @ point + planes[:, 3] <= 1e-6).all()]
    return min(holding)[1] if holding else None


def opening_of(laid, name, middle, axes, half, airs):
    """The opening a door fills: the enclosure (shell or connector) whose box holds the door's middle, `end_wall` true
    when that is a tunnel's end wall holding its doorway (the `cap` part within the door's depth and FRAME of its
    plane), the door's own middle, size (across, up) and the way through it."""
    holder = next((other for other in sorted(airs) if np.all(middle >= laid.meshes[other].bounds[0])
                   and np.all(middle <= laid.meshes[other].bounds[1])), None)
    cap = part_points(laid.prims[holder], "cap") if holder else np.zeros((0, 3))
    from score.stages.place_build import ready
    end_wall = bool(len(cap)) and bool(abs(float((cap.mean(axis=0) - middle) @ axes[2])) <= half[2] + ready.FRAME)
    return {"in": holder, "end_wall": end_wall, "middle": np.round(middle, 4).tolist(),
            "size": [round(float(2 * half[0]), 4), round(float(2 * half[1]), 4)],
            "through": np.round(axes[2], 6).tolist()}


def marked_locks(laid):
    """{door: (its chamber, inner or outer)} of every door marked a chamber's pressure door (score:lock, score:side:
    place_build.door) whose chamber the scene holds."""
    found = {}
    for name in laid.with_role("door"):
        lock, side = (text_of(laid.prims[name], key) for key in ("score:lock", "score:side"))
        if lock in laid.meshes and side in ("inner", "outer"):
            found[name] = (lock, side)
    return found


def airs_of(laid):
    """{enclosure: its air (air_of)} of every shell, connector and marked airlock chamber (marked_locks: the air between
    its doors, chamber_air, when its own solid's hull holds no door's inside)."""
    marked = marked_locks(laid)
    locks = {lock for lock, _ in marked.values()}
    found = {}
    for name in sorted(set(laid.with_role("shell", "connector")) | locks):
        air = air_of(laid, name)
        doors = sorted(door for door, (lock, _) in marked.items() if lock == name)
        if name in locks and (air is None or not any(inside_of(laid, door, air) for door in doors)):
            air = chamber_air(laid, name, doors)
        if air is not None:
            found[name] = air
    return found


def inside_of(laid, door, air):
    """Whether an air (planes, volume) holds a point PROBE past either face of the door."""
    from score.stages.place_build import ready
    middle, axes, half = ready.frame_of(laid, door)
    return any((air[0][:, :3] @ (middle + axes[2] * (half[2] + PROBE) * way) + air[0][:, 3] <= 1e-6).all()
               for way in (1.0, -1.0))


def chamber_air(laid, lock, doors):
    """A marked chamber's air read from the walkers' floor round its doors (every door shut): the one floor piece that
    meets a side of each of its doors, raised to the top of the object its doors name; (planes, volume) or None. A
    chamber whose named object is one wall of several (the shiplock's hull_wall) holds no air of its own hull (#154:
    shiplock's doors led nowhere and its chambers were [])."""
    from score.stages.place_build import ready
    if len(doors) < 2:
        return None
    grid, span_cells, span_heights, standing, pieces = ready.walkers_floor(
        laid, {name: laid.meshes[name] for name in laid.with_role("door")}, near=doors)
    sides = []  # each door's {piece: the spot PROBE past its face on that piece's side}
    for door in doors:
        middle, axes, half = ready.frame_of(laid, door)
        sill = float(laid.meshes[door].bounds[0][1])
        found = {}
        for way in (1.0, -1.0):
            spot = middle + axes[2] * (half[2] + PROBE) * way
            spot = np.array([spot[0], sill, spot[2]])
            for span in ready.spans_near(grid, span_cells, span_heights, standing, spot):
                found.setdefault(int(pieces[span]), spot)
        sides.append(found)
    shared = set.intersection(*(set(found) for found in sides))
    if len(shared) != 1:
        return None
    piece = shared.pop()
    kept = standing & (pieces == piece)
    middles = grid.middles()[span_cells[kept]]
    top = float(laid.meshes[lock].bounds[1][1])
    floor = np.vstack([np.column_stack([middles[:, 0], span_heights[kept], middles[:, 1]]),
                       [found[piece] for found in sides]])  # the doors' inside spots, where a walker stands short
    return hull_of(np.vstack([floor, np.column_stack([floor[:, 0], np.full(len(floor), top), floor[:, 2]])]))


def locks_of(laid, airs=None):
    """Every door's sides and the place's airlock chambers: ({door: {between, and for a chamber's door lock, side,
    leads, toward}}, [{name, inner, outer, air_volume}]). `between` is the enclosures (a shell's or connector's air, or
    a marked chamber's, air_of; null outside) PROBE past the door's face along its through axis and against it. A
    chamber is the object a door's score:lock names, its doors inner or outer by their score:side (a blocks-built
    airlock, whose walls are no shell: 2099 #164), else an enclosure two unmarked doors open into, one from another
    enclosure (inner) and one from outside (outer). A pressure door opens toward its high-pressure side, so the air
    holds it shut (`toward`, +1 or -1 along its through axis): the outer door into the chamber, the inner one out of it
    to the base, never into the chamber like a closet door (2099 stock-take C5). `airs`: airs_of's, when read."""
    from score.stages.place_build import ready
    marked = marked_locks(laid)
    airs = airs_of(laid) if airs is None else airs
    doors = {}
    for name in laid.with_role("door"):
        middle, axes, half = ready.frame_of(laid, name)
        reach_out = axes[2] * (half[2] + PROBE)
        doors[name] = {"between": [enclosure_at(airs, middle + reach_out), enclosure_at(airs, middle - reach_out)],
                       "middle": middle, "through": axes[2]}
    chambers = []
    for enclosure in sorted(airs):
        found = {side: sorted(name for name, (lock, marked_side) in marked.items()
                              if lock == enclosure and marked_side == side) for side in ("inner", "outer")}
        unmarked = {name: door for name, door in doors.items() if name not in marked and enclosure in door["between"]}
        found["inner"] += sorted(name for name, door in unmarked.items()
                                 if any(side not in (None, enclosure) for side in door["between"]))
        found["outer"] += sorted(name for name, door in unmarked.items() if None in door["between"])
        if not (found["inner"] and found["outer"]):
            continue
        chambers.append({"name": enclosure, "inner": found["inner"], "outer": found["outer"],
                         "air_volume": round(airs[enclosure][1], 3)})
        for side in ("inner", "outer"):
            for name in found[side]:
                door = doors[name]
                into = chamber_way(laid, enclosure, door)
                door.update({"lock": enclosure, "side": side, "toward": into if side == "outer" else -into,
                             "leads": next((other for other in door["between"] if other != enclosure), None)})
    for door in doors.values():
        del door["middle"], door["through"]
    return doors, chambers


def chamber_way(laid, enclosure, door):
    """Which way along a door's through axis its chamber lies (+1 or -1): the side whose probe reads the chamber, else
    the side its chamber's box middle lies on."""
    if door["between"][0] == enclosure:
        return 1.0
    if door["between"][1] == enclosure:
        return -1.0
    low, high = laid.meshes[enclosure].bounds
    return 1.0 if float(((low + high) / 2 - door["middle"]) @ door["through"]) >= 0 else -1.0


def door_block(laid, name, how, sides, airs):
    """A door's `door` block: moved whole (`leaf` the copy itself, no frame) as the walkers open it (`how`,
    ready.opening): a slide (`move` slide, `axis` the unit way it slides open, `pivot` its shut middle, `limits` [0
    and its open travel] in metres, `open` that travel) or a hinge (`move` hinge, up through an edge of its leaf,
    `limits` [0 and its open turn] in degrees right-handed about +y); its score:opens mark, opening, sides and, a
    chamber's door, its lock, side and where it leads."""
    from score.stages.place_build import ready
    middle, axes, half = ready.frame_of(laid, name)
    if "by" in how:
        by = np.asarray(how["by"], dtype=float)
        travel = float(np.linalg.norm(by))
        moved = {"move": "slide", "axis": np.round(by / travel, 6).tolist(), "pivot": np.round(middle, 4).tolist(),
                 "limits": [0.0, round(travel, 4)], "open": round(travel, 4)}
    else:
        moved = {"move": "hinge", "axis": [0.0, 1.0, 0.0], "pivot": how["hinge"],
                 "limits": sorted([0.0, float(how["degrees"])]), "open": float(how["degrees"])}
    block = {"leaf": name, "frame": None, **moved, "opens": ready.opens(laid, name),
             "opening": opening_of(laid, name, middle, axes, half, airs), "between": sides["between"]}
    block.update({key: sides[key] for key in ("lock", "side", "leads") if key in sides})
    return block


def doors_of(stage, place, names):
    """{door: its `door` block (door_block)} for every laid object of `names` the physics check takes for a door
    (ready.role_of), and scene.json's `chambers` (locks_of), each with its inner and outer doors and its air's volume
    (its hull's, air_of)."""
    from score.stages.place_build import ready
    prims = {name: stage.GetPrimAtPath(f"/{place}/Objects/{name}") for name in names}
    if not any(prim and ready.role_of(prim) == "door" for prim in prims.values()):
        return {}, []
    laid = ready.Place(stage, place)
    airs = airs_of(laid)
    sides, chambers = locks_of(laid, airs)
    return {name: door_block(laid, name, ready.opening(laid, name, sides[name].get("toward")), sides[name], airs)
            for name in laid.with_role("door") if name in prims}, chambers


# --- the package ----------------------------------------------------------------------------------------------------

def animated(prim):
    """Whether anything under the prim moves over time."""
    return any(attribute.GetNumTimeSamples() > 1 for inside in Usd.PrimRange(prim)
               for attribute in inside.GetAttributes())


def moving_door(prim):
    """Whether the prim is a door (ready.role_of) that moves only by its own transform (a walker's swing or slide
    keyed over time, walker_route's door times), its leaf's shape still: the package lays it as every read at the
    default time sees it (its keyed ops' own values, the swing at 0, else laid as put: shut), its `door` block the
    way it moves (2099 #161: stairwell@2's entrance door was left out, so the street met no door)."""
    from score.stages.place_build import ready
    if ready.role_of(prim) != "door":
        return False
    own = {op.GetAttr().GetName() for op in UsdGeom.Xformable(prim).GetOrderedXformOps()}
    return not any(attribute.GetNumTimeSamples() > 1 for inside in Usd.PrimRange(prim)
                   for attribute in inside.GetAttributes() if inside != prim or attribute.GetName() not in own)


def laid_objects(stage, place):
    """[(prim, kind)] of every object and effect laid (a moving door at rest, moving_door), [(prim, kind)] of every
    character (skinned.is_character: a SkelRoot or a crowd's PointInstancer, under Objects or Characters), and
    [{name, why}] of those not converted."""
    found, characters, left_out = [], [], []
    for scope, default in (("Objects", "object"), ("Effects", "effect"), ("Characters", "character")):
        holder = stage.GetPrimAtPath(f"/{place}/{scope}")
        for prim in holder.GetChildren() if holder else []:
            kind = text_of(prim, "score:kind") or default
            if kind == "light":
                left_out.append({"name": prim.GetName(), "why": "the place's sky dome: scene.json's environment"})
            elif skinned.is_character(prim):
                characters.append((prim, "character" if kind in ("object", "model") else kind))
            elif animated(prim) and not moving_door(prim):
                left_out.append({"name": prim.GetName(), "why": "it moves over time: not converted"})
            else:
                found.append((prim, kind))
    return found, characters, left_out


def character_copies(prim):
    """One laid character's copies as skinned glTFs (skinned.py), each SkelRoot it copies converted once and checked:
    [(name, world, glb, facts, check)] and [{name, why}] of those not converted. Read a character at a time, so only
    its own copies' glTFs are held (the square's 1,260 people, every one's held until all were made, passed 14 GB)."""
    made, copies, left_out = {}, [], []
    for root, name, world in skinned.copies_of(prim):
        frame, scale, baked = copy_frame(world)
        key = (str(root.GetPath()), None if baked is None else baked.round(9).tobytes())
        if key not in made:
            try:
                glb, facts = skinned.character_glb(root, baked)
                made[key] = (glb, facts, skinned.check_of(root, glb, facts))
            except skinned.Unconvertible as refused:
                made[key] = refused
        if isinstance(made[key], skinned.Unconvertible):
            left_out.append({"name": name, "why": str(made[key])})
            continue
        copies.append((name, frame, scale, *made[key]))
    return copies, left_out


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


def library_reference(folder, path):
    """A file copied under the place's assets (library_files.stage_name: kind/id/version/file) as the library
    reference it was copied from (`kind/id@version/file`); None for a file from anywhere else."""
    try:
        kind, entry_id, version, *rest = pathlib.Path(path).resolve().relative_to(
            (pathlib.Path(folder) / "assets").resolve()).parts
    except ValueError:
        return None
    return f"{kind}/{entry_id}@{version}/{'/'.join(rest)}" if version.isdigit() and rest else None


def sky_picture(stage, place, out):
    """The sky dome's picture (the glow its dome under Objects/sky gives off, a longitude-latitude picture) copied
    into <out>/environment, or with no `out` (a piece list, pieces.py) named by its library reference and not copied:
    {file, projection, turn (degrees about up, as laid), strength (its glow's), library}; None when the place lays no
    sky picture."""
    holder = stage.GetPrimAtPath(f"/{place}/Objects/sky")
    for inside in gprims(holder) if holder else []:
        look = UsdShade.MaterialBindingAPI(inside).ComputeBoundMaterial()[0]
        shader = look.ComputeSurfaceSource()[0] if look else None
        found = texture_of(shader, "emissiveColor") if shader else None
        if found is None:
            continue
        if out is None:
            file = library_reference(pathlib.Path(stage.GetRootLayer().realPath).parent, found[0])
        else:
            (out / "environment").mkdir(exist_ok=True)
            shutil.copyfile(found[0], out / "environment" / found[0].name)
            file = f"environment/{found[0].name}"
        turn = holder.GetAttribute("xformOp:rotateXYZ")
        return {"file": file,
                "projection": "longitude-latitude: u round up from +x (tools/usd/mars_sky.ways), v from the "
                              "bottom pole up, on a ball round the place",
                "turn": float(turn.Get()[1]) if turn and turn.HasValue() else 0.0,
                "strength": float(text_of(inside, "score:sky_strength") or 1.0),
                "library": text_of(holder, "score:library")}
    return None


def environment_of(stage, place, out):
    """The place's sky and light as the final render draws it (usd_views.stage_sky, blender_views): the sky picture
    (sky_picture: copied into `out`, or by its library reference with none), the dome's ambient light, the background
    the camera sees, the exposure (a multiplier), the sun,
    the view transform and look; `night` its moon and glow where the place has a night (place_build.night)."""
    sky = stage.GetPrimAtPath(f"/{place}/Environment")
    lights = {prim.GetName(): prim for prim in (stage.GetPrimAtPath(f"/{place}/Lights").GetChildren()
                                                if stage.GetPrimAtPath(f"/{place}/Lights") else [])
              if prim.IsA(UsdLux.DistantLight)}
    found = {"sky": None, "ambient": None, "background": None, "exposure": 1.0, **VIEW,
             "sun": distant(lights[SUN_NAMES[0] if SUN_NAMES[0] in lights else SUN_NAMES[1]])
             if any(name in lights for name in SUN_NAMES) else None, "night": None}
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


def converted(prim, baked, made, sights=None, draft=False):
    """An object's glTF (GLB bytes), where it came from, and its check: the library entry's own when laid unchanged
    in an even copy, else converted from the laid USD (`made` the conversions so far, object_glb), its triangles
    counted against the USD's (the triangles an unwrap cut a face into counted besides); a `draft`'s recipes never
    baked (pbr)."""
    import trimesh
    usd_triangles = sum(len(found[2]) for found in (drawn(inside) for inside in gprims(prim)) if found is not None)
    own = entry_glb(prim) if baked is None else None
    if own is not None:
        loaded = trimesh.load(trimesh.util.wrap_as_stream(own), file_type="glb", force="mesh", skip_materials=True)
        return own, "library glTF", {"pass": len(loaded.faces) == usd_triangles > 0, "triangles": len(loaded.faces),
                                     "usd_triangles": usd_triangles}
    glb, triangles, cut = object_glb(prim, baked, made, sights, draft)
    if glb is None:
        return None, None, None
    loaded = trimesh.load(trimesh.util.wrap_as_stream(glb), file_type="glb", force="mesh", skip_materials=True)
    return glb, "converted from the laid USD", {"pass": len(loaded.faces) - cut == triangles == usd_triangles > 0,
                                                "triangles": len(loaded.faces), "usd_triangles": usd_triangles,
                                                "cut": cut}


def taken_down(data):
    """A picture's bytes (PNG or JPEG) at the size the game holds it (2099's PlaceTextures.HeldSize): halved, each texel
    the mean of the two by two it covers as a mip level is made, until its longer side is at most HELD_TEXELS, its
    sides then multiples of BLOCK_TEXELS (held_image); (its bytes, mime type), unchanged when it fits."""
    import io
    picture = Image.open(io.BytesIO(data))
    if max(picture.size) <= HELD_TEXELS and all(side % BLOCK_TEXELS == 0 for side in picture.size):
        return data, None
    picture = held_image(picture.convert("RGBA" if "A" in picture.getbands() or picture.mode == "P" else "RGB"))
    held_bytes = io.BytesIO()
    picture.save(held_bytes, format="PNG")
    return held_bytes.getvalue(), "image/png"


def held_image(picture):
    """A decoded picture at the size the game holds it (taken_down's halving), so a look holds no more than the package
    writes (the square's rocket: 32 maps, each a 4096 normal map, 2.9 GB decoded at once), each side then resampled
    to its nearest multiple of BLOCK_TEXELS (the texture coordinates span the picture, so none moves)."""
    while max(picture.size) > HELD_TEXELS:
        picture = picture.reduce(2)
    blocked = tuple(max(BLOCK_TEXELS, round(side / BLOCK_TEXELS) * BLOCK_TEXELS) for side in picture.size)
    return picture if blocked == picture.size else picture.resize(blocked, Image.Resampling.LANCZOS)


def pictures_held(document, binary):
    """A glTF document's buffer (its one buffer, a bytes-like) with every picture in it written at most HELD_TEXELS a
    side (taken_down) and pictures of the same bytes read alike (pictures_read_as) held once, every texture of them
    reading the one: the document's images, textures and buffer views made to match; the new buffer."""
    views = document.get("bufferViews", [])
    content = [bytes(binary[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]])
               for view in views]
    kept, images, by_bytes, read_as = {}, [], {}, pictures_read_as(document)
    for number, image in enumerate(document.get("images", [])):
        if "bufferView" in image:
            data, mime = taken_down(content[image["bufferView"]])
            content[image["bufferView"]] = data
            image = dict(image, mimeType=mime or image.get("mimeType"))
            key = (hashlib.sha256(data).hexdigest(), read_as.get(number))
            if key in by_bytes:
                kept[number] = by_bytes[key]
                continue
            by_bytes[key] = len(images)
        kept[number] = len(images)
        images.append(image)
    if "images" in document:
        document["images"] = images
    for texture in document.get("textures", []):
        if "source" in texture:
            texture["source"] = kept[texture["source"]]
    used = sorted(set(view_numbers(document)))
    renumbered = {old: new for new, old in enumerate(used)}
    held_binary = bytearray()
    for old in used:
        held_binary.extend(b"\0" * (-len(held_binary) % 4))
        views[old] = dict(views[old], byteOffset=len(held_binary), byteLength=len(content[old]))
        held_binary.extend(content[old])
    if views:
        document["bufferViews"] = [views[old] for old in used]
        view_numbers(document, renumbered)
        document["buffers"][0]["byteLength"] = len(held_binary)
    return held_binary


def pictures_read_as(document):
    """{image: "colour" or "linear"}: how the document's materials read each picture (a base colour or glow map as
    colour, every other map as linear data), so a picture is shared only between textures an engine decodes alike."""
    found = {}
    for material in document.get("materials", []):
        maps = [(name, given) for name, given in material.items() if name.endswith("Texture")]
        maps += [(name, given) for name, given in material.get("pbrMetallicRoughness", {}).items()
                 if name.endswith("Texture")]
        for name, given in maps:
            source = document["textures"][given["index"]].get("source")
            if source is not None:
                found[source] = "colour" if name in ("baseColorTexture", "emissiveTexture") else "linear"
    return found


def view_numbers(item, renumbered=None):
    """Every buffer view number the document reads (any `bufferView` key, an extension's too), renumbered in place
    by `renumbered` when given."""
    found = []
    if isinstance(item, dict):
        for key, value in item.items():
            if key == "bufferView" and isinstance(value, int):
                found.append(value)
                if renumbered is not None:
                    item[key] = renumbered[value]
            else:
                found += view_numbers(value, renumbered)
    elif isinstance(item, list):
        for value in item:
            found += view_numbers(value, renumbered)
    return found


def written(out, name, glb):
    """An object's GLB written as objects/<name>.gltf and its .bin, its pictures held (pictures_held)."""
    document, binary = unpacked(glb, name)
    binary = pictures_held(document, binary) if binary else binary
    (out / "objects" / f"{name}.gltf").write_text(json.dumps(document))
    if binary:
        (out / "objects" / f"{name}.bin").write_bytes(binary)


def box_size(glb):
    import trimesh
    loaded = trimesh.load(trimesh.util.wrap_as_stream(glb), file_type="glb", force="mesh", skip_materials=True)
    return [round(float(side), 4) for side in np.ptp(loaded.vertices, axis=0)]


@contextlib.contextmanager
def deadline(out, step, kind):
    """The step named in <out>/STEPS and run under STEP_SECONDS[kind]: past it the process stops with every thread's
    stack on stderr (faulthandler's watchdog, which fires inside a C call such as xatlas's packing too)."""
    seconds = STEP_SECONDS[kind]
    log = out / STEPS
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as written_log:
        written_log.write(f"{kind} {step}: stopped past {seconds} s\n")
    faulthandler.dump_traceback_later(seconds, exit=True)
    try:
        yield
    finally:
        faulthandler.cancel_dump_traceback_later()


@contextlib.contextmanager
def seated(stage, place, seat):
    """The place's root set at its area seat (place.json `seat`, area.area: a turn about up and a shift, USD's
    row-vector order) on the stage's session layer while the package is written, so every object, door, lamp, sky and
    character reads in the area's frame (2099 lays an area's places where their packages put them); the scene's own
    file is never changed, and the seat is cleared after."""
    if not seat:
        yield
        return
    layer = stage.GetSessionLayer()
    with Usd.EditContext(stage, layer):
        root = UsdGeom.Xformable(stage.GetPrimAtPath(f"/{place}"))
        own = root.GetOrderedXformOps()
        op = root.AddTransformOp(opSuffix="seat")
        op.Set(Gf.Matrix4d(np.asarray(seat["matrix"], float).reshape(4, 4).tolist()))
        root.SetXformOpOrder([op, *own], root.GetResetXformStack())
    try:
        yield
    finally:
        with Usd.EditContext(stage, layer):
            stage.RemovePrim(f"/{place}")  # the session layer's spec alone: the seat


def write(folder, out, draft=False):
    """The laid place in <folder> as a scene package in <out>, laid at its area seat (seated), a `draft` with no bake
    asked (DRAFT); scene.json's content."""
    folder, out = pathlib.Path(folder), pathlib.Path(out)
    stage, place = place_build.opened(folder)
    seat = place_build.record_of(folder).get("seat")
    with seated(stage, place, seat):
        return written_scene(folder, out, stage, place, seat, draft)


def written_scene(folder, out, stage, place, seat, draft=False):
    """write's body: the package written from the open stage, its frame the area's when `seat` is given (then its
    place.json `backdrop`, the objects and lamps a neighbour place stands for, left out); a `draft` asks no bake and
    reads no walkers' eyes (they only set a bake's densities), its scene.json marked `draft`."""
    ready_file = folder / "ready.json"
    roles = json.loads(ready_file.read_text())["roles"] if ready_file.is_file() else None
    for held in (out.iterdir() if out.exists() else ()):  # all but the bake's maps a stopped bake left (BAKE)
        if held.name != "bake":
            shutil.rmtree(held) if held.is_dir() else held.unlink()
    (out / "objects").mkdir(parents=True)
    (out / STEPS).unlink(missing_ok=True)
    found, characters, left_out = laid_objects(stage, place)
    neighbours = set(place_build.record_of(folder).get("backdrop") or []) if seat else set()
    found, characters = ([(prim, kind) for prim, kind in listed if prim.GetName() not in neighbours]
                         for listed in (found, characters))
    left_out += [{"name": name, "why": f"the concept's backdrop: a neighbour place of the area {seat['area']} "
                                       "stands for it (place.json backdrop)"} for name in sorted(neighbours)]
    objects, instances, by_content, counts, made = {}, [], {}, {}, {}
    with deadline(out, "the walkers' eyes", "scene"):
        sights = {} if draft else eyes_by_content(stage, place, found)
    for prim, kind in found:
        with deadline(out, prim.GetName(), "object"):
            world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
            frame, scale, baked = copy_frame(world)
            glb, route, check = converted(prim, baked, made, sights, draft)
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
    for prim, kind in characters:
        with deadline(out, prim.GetName(), "object"):
            laid_characters, refused = character_copies(prim)
            left_out += refused
            for name, frame, scale, glb, facts, check in laid_characters:
                digest = hashlib.sha256(glb).hexdigest()
                if digest not in by_content:
                    by_content[digest] = name
                    written(out, name, glb)
                    objects[name] = {"file": f"objects/{name}.gltf", "kind": kind, "route": "skinned from the laid USD",
                                     "size": box_size(glb), "triangles": check["triangles"], "check": check,
                                     "clips": facts["clips"]}
                copy = instance_of(name, by_content[digest], kind, frame, scale)
                copy["plays"] = facts["plays"]
                instances.append(copy)
                counts[kind] = counts.get(kind, 0) + 1
            del laid_characters
    with deadline(out, "doors, chambers, lamps and sky", "scene"):
        doors, chambers = doors_of(stage, place, [copy["name"] for copy in instances])
        for copy in instances:
            if copy["name"] in doors:
                copy["door"] = doors[copy["name"]]
        scene = {"format": package.FORMAT, "version": package.VERSION, "place": place,
                 "frame": f"the area {seat['area']}'s frame (the place's seat, {seat['from']}): metres, y up"
                 if seat else "the place's own frame: metres, y up", "units": "metre", "up": "+y", "ground": GROUND,
                 "on_seat": [0.0, 0.0], "objects": objects, "instances": instances, "children": [],
                 "lamps": [lamp for lamp in lamps_of(stage, place) if lamp["name"] not in neighbours],
                 "counts": counts,
                 "physics": "ready.json" if roles is not None else None, "left_out": left_out, "chambers": chambers,
                 "environment": environment_of(stage, place, out)}
        if draft:
            scene["draft"] = DRAFT
    (out / "scene.json").write_text(json.dumps(scene, indent=1) + "\n")
    return scene


# --- the bake -------------------------------------------------------------------------------------------------------

PICTURES = ("base_color", "metal_roughness", "normal")  # a baked map's pictures, as glTF reads them
# A Blender run bakes at most BATCH maps of one object, then ends and gives its memory back (the street, 2026-11-20:
# one run over 225 maps of 4096 grew past render.MEMORY and was killed at its 173rd after 106 min). Its maps land in
# <out>/BAKE as <key>_<picture>.png with a <key>.done mark (bake_looks.written); `package` again keeps them (write
# leaves bake/ standing) and bakes only the maps not yet marked, a map's key its request, its object's file and the
# bake's code, so a changed object or recipe is baked again.
BATCH = 6
# A bake's card use is mostly its Blender's own work on the processor (each map's four bakes find their pixels, sync
# the object and build its rays there; nvidia-smi read 29% busy over 150 s with one run on the card, 2026-11-22), so
# SIDE_BY_SIDE runs of one package hold the card at once, each of BAKE_CARD_GB and BAKE_MEMORY_GB: the card queue's
# measures of place-build-bake-package read 0.6 to 2.2 GB in the hours nothing else was on the card (its 12.97 GB
# highest was read beside a Windows game holding 10 GB, 2026-11-22), its memory 5.2 GB at most under the 8 GB scope.
SIDE_BY_SIDE = 2
BAKE_CARD_GB = 4
BAKE_MEMORY_GB = 6
BAKE = "bake/maps"
BAKE_CODE = ("bake_looks.py", "../../../tools/props/library/recipes.py")  # under this folder: the code a map's key holds


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


def map_keys(out, jobs):
    """Each job's key: its request (all but its pictures' names), its object's .gltf and buffers and the bake's code,
    hashed; equal only when the map would be baked the same."""
    here = pathlib.Path(__file__).resolve().parent
    code = hashlib.sha256(b"".join((here / name).read_bytes() for name in BAKE_CODE)).hexdigest()
    objects = {}
    for gltf in {job["gltf"] for job in jobs}:
        path = out / gltf
        digest = hashlib.sha256(path.read_bytes())
        for buffer in json.loads(path.read_text()).get("buffers", []):
            digest.update((path.parent / buffer["uri"]).read_bytes())
        objects[gltf] = digest.hexdigest()
    keys = []
    for job in jobs:
        asked = json.dumps({name: value for name, value in job.items() if name != "pictures"}, sort_keys=True)
        keys.append(hashlib.sha256(f"{asked} {objects[job['gltf']]} {code}".encode()).hexdigest()[:32])
    return keys


def batches(jobs):
    """The jobs in runs of at most BATCH maps, each run one object's."""
    by_file = {}
    for job in jobs:
        by_file.setdefault(job["gltf"], []).append(job)
    return [held[start:start + BATCH] for held in by_file.values() for start in range(0, len(held), BATCH)]


def blender_run(out, listing, log):
    """One run of bake_looks.py over `listing` in headless Blender on this PC's card, through the card queue
    (render.queued), stopped past STEP_SECONDS' bake run, its output added to `log`; its exit code."""
    import subprocess
    from score.stages.place_build import render
    script = pathlib.Path(__file__).resolve().parent / "bake_looks.py"
    with log.open("a") as written_log:
        return subprocess.run(render.queued(f"place-build-bake-{out.name}", script, [str(listing.resolve())],
                                            seconds=STEP_SECONDS["bake run"], card_gb=BAKE_CARD_GB,
                                            memory_gb=BAKE_MEMORY_GB),
                              stdout=written_log, stderr=subprocess.STDOUT, cwd=place_build.REPO).returncode


def blender_baked(out, jobs, run=blender_run):
    """The jobs baked by bake_looks.py in runs of BATCH maps, SIDE_BY_SIDE at once (`run(out, listing, log)` one run,
    its exit code), every map already marked done under <out>/BAKE kept and every other mark there removed, each run's
    log added to <out>/bake/blender.log as it ends; each map's pictures then moved to its place under objects/. No run
    starts after one fails. Refused with the failed run's tail when a run fails or a map is not baked, its finished
    maps kept for the next `package` to resume from."""
    from score.stages.place_build import render
    into = out / BAKE
    into.mkdir(parents=True, exist_ok=True)
    keys = map_keys(out, jobs)
    for held in into.iterdir():
        if held.name.split("_")[0].split(".")[0] not in keys:
            held.unlink()
    left = [dict(job, key=key) for job, key in zip(jobs, keys) if not (into / f"{key}.done").is_file()]
    log = out / "bake" / "blender.log"
    log.write_text(f"{len(jobs) - len(left)} of {len(jobs)} maps kept from an earlier bake\n")
    runs, failed = batches(left), []
    ending = threading.Lock()

    def one(number):
        """Run `number` baked unless one has failed: its listing and log its own, its log added to the whole."""
        if failed:
            return
        batch = runs[number]
        listing, own = out / "bake" / f"jobs-{number + 1}.json", out / "bake" / f"run-{number + 1}.log"
        listing.write_text(json.dumps({"out": str(out.resolve()), "into": str(into.resolve()), "jobs": batch},
                                      indent=1))
        own.write_text(f"RUN {number + 1} of {len(runs)}: {len(batch)} maps of {batch[0]['gltf']}\n")
        code = run(out, listing, own)
        with ending:
            told = own.read_text(errors="replace")
            with log.open("a") as written_log:
                written_log.write(told)
            if code:
                failed.append((code, told.splitlines()[-6:]))
        own.unlink()
        listing.unlink()

    with concurrent.futures.ThreadPoolExecutor(SIDE_BY_SIDE) as pool:
        list(pool.map(one, range(len(runs))))
    code, tail = failed[0] if failed else (0, log.read_text(errors="replace").splitlines()[-6:])
    missing = [job for job, key in zip(jobs, keys) if not (into / f"{key}.done").is_file()]
    if code or missing:
        tail = " | ".join(tail)
        late = f", its run stopped past {STEP_SECONDS['bake run']} s" if code == render.TIMED_OUT else ""
        raise place_build.Refused(f"the bake failed (exit {code}{late}, {len(missing)} of {len(jobs)} maps not baked; "
                                  f"package again bakes only those), log {log}: {tail}")
    for job, key in zip(jobs, keys):
        for kind in PICTURES:
            (out / "objects" / job["pictures"][kind]).parent.mkdir(parents=True, exist_ok=True)
            (into / f"{key}_{kind}.png").replace(out / "objects" / job["pictures"][kind])
        (into / f"{key}.done").unlink()


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
    under its opacity, metal and roughness 1) and its bake request taken off; its pictures then held (pictures_held:
    at most HELD_TEXELS a side, the same bytes once)."""
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
        binary = pictures_held(document, binary)
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
        *(str(GRADE[key]) for key in ("size", "low", "high", "middle"))], card=False,
        seconds=STEP_SECONDS["grade"]),
        capture_output=True, text=True, cwd=place_build.REPO)
    if done.returncode or not (out / GRADE_FILE).is_file():
        tail = " | ".join((done.stdout + done.stderr).splitlines()[-6:])
        late = f", stopped past {STEP_SECONDS['grade']} s" if done.returncode == render.TIMED_OUT else ""
        raise place_build.Refused(f"the grade failed (exit {done.returncode}{late}): {tail}")


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


def packaged(folder, out, baker=blender_baked, grader=blender_graded, draft=False):
    """The package written, its palette recipes baked (`baker(out, jobs)` writes each job's pictures) and put on
    their looks (a `draft`'s never: DRAFT), its grade drawn (`grader(out, environment)` writes GRADE_FILE:
    environment `grade`), and checked by package.py's own check: its summary, or Refused naming its problems."""
    out = pathlib.Path(out)
    scene = write(folder, out, draft)
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
            "sky": (scene["environment"]["sky"] or {}).get("file"), "check": "sound", "draft": draft}
