"""What a film's camera sees on a place's OpenUSD stage (read only): the stage's drawn geometry gathered with each
triangle's prim and face, rays cast through a grid over the picture, and each hit's surface: its prim, its material
and whether that material is textured.

    scene = seen.gathered(stage)              # one mesh of everything drawn, each triangle's prim and face kept
    sight = seen.look(scene, view)            # {prims, cells: prim number per grid cell (-1 nothing), distances}
    kinds = seen.surface_kinds(stage, scene, sight)   # {prim path: {surface kind: cells}} of what the camera saw

The grid is GRID cells across and down, each a ray through the cell's middle from the view's eye, the view's `fov`
the angle across the picture (as tools/blender/inside/usd_views.py's camera: sensor fit horizontal).
"""
import numpy as np
import trimesh
from pxr import Sdf, Usd, UsdGeom, UsdShade

from score.stages.terrain import sight

GRID = (96, 54)
# A surface's kinds, worst first: what it is drawn in.
NO_MATERIAL = "no material"
DEFAULT_GREY = "default grey"
TEXTURE_MISSING = "texture missing"
NO_TEXTURE_COORDINATES = "no texture coordinates"
PLAIN_COLOUR = "plain colour, no texture"
TEXTURED = "textured"
UNTEXTURED = (NO_MATERIAL, DEFAULT_GREY, TEXTURE_MISSING, NO_TEXTURE_COORDINATES, PLAIN_COLOUR)
# UsdPreviewSurface's own diffuse colour when none is authored, and Blender's default material colour.
DEFAULT_COLOURS = ((0.18, 0.18, 0.18), (0.8, 0.8, 0.8))
NEAREST = 0.05  # the film camera's near clip, metres
# Air, not surfaces: the kinds the film's renderer draws as sky, haze or light (tools/blender/inside/usd_views.py
# `sky`), which a ray passes through.
AIR = ("haze", "stars", "sky", "dust", "beam", "sky_dome")


class Gathered:
    """Everything drawn on a stage as one trimesh, with each triangle's prim (a number into `prims`) and face."""

    def __init__(self, mesh, prims, prim_of, face_of):
        self.mesh, self.prims, self.prim_of, self.face_of = mesh, prims, prim_of, face_of


def face_numbers(prim):
    """Each triangle's face number of a Mesh prim, in the order sight.mesh_triangles fans its faces."""
    counts = np.asarray(UsdGeom.Mesh(prim).GetFaceVertexCountsAttr().Get())
    kept = np.flatnonzero(counts >= 3)
    return np.repeat(kept, counts[kept] - 2)


def prim_triangles(prim, cache):
    """(points, triangles, face of each triangle) of one drawn prim in the stage's frame, or None. A sphere's and an
    instancer's faces are -1: they have no subsets."""
    if prim.IsA(UsdGeom.PointInstancer):
        made = sight.instancer_triangles(prim, cache)
        return None if made is None else (*made, np.full(len(made[1]), -1))
    if prim.IsA(UsdGeom.Sphere):
        made = sight.sphere_triangles(prim, cache)
        return (*made, np.full(len(made[1]), -1))
    if prim.IsA(UsdGeom.Mesh):
        made = sight.mesh_triangles(prim, cache)
        return None if made is None else (*made, face_numbers(prim))
    return None


def is_air(prim):
    """True for a prim, or one it stands under, whose score:kind is one of AIR."""
    while prim and not prim.IsPseudoRoot():
        kind = prim.GetAttribute("score:kind")
        if kind and kind.Get() in AIR:
            return True
        prim = prim.GetParent()
    return False


def drawn_prims(stage):
    """Every drawn geometry prim of the stage a viewer sees as the world (sight.is_seen), an instancer's own
    prototypes left out."""
    instancers = []
    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)):
        if any(str(prim.GetPath()).startswith(str(path) + "/") for path in instancers):
            continue
        if not (prim.IsA(UsdGeom.Gprim) or prim.IsA(UsdGeom.PointInstancer)) or not sight.is_seen(prim, ()):
            continue
        if is_air(prim):
            continue
        if prim.IsA(UsdGeom.PointInstancer):
            instancers.append(prim.GetPath())
        yield prim


def gathered(stage):
    """Every drawn prim of the stage as one Gathered mesh in the stage's frame."""
    cache = UsdGeom.XformCache(Usd.TimeCode.Default())
    parts, prims, prim_of, face_of = [], [], [], []
    for prim in drawn_prims(stage):
        made = prim_triangles(prim, cache)
        if made is None or not len(made[1]):
            continue
        parts.append(made[:2])
        prim_of.append(np.full(len(made[1]), len(prims)))
        face_of.append(made[2])
        prims.append(str(prim.GetPath()))
    points, triangles = sight.join(parts)
    return Gathered(trimesh.Trimesh(points, triangles, process=False), prims, np.concatenate(prim_of),
                    np.concatenate(face_of))


def camera_rays(view, grid=GRID):
    """(eye, unit directions row by row from the top left) of a view's grid of cells."""
    eye, aim, up = (np.asarray(view[name], dtype=float) for name in ("eye", "aim", "up"))
    forward = (aim - eye) / np.linalg.norm(aim - eye)
    across = np.cross(forward, up)
    across /= np.linalg.norm(across)
    upward = np.cross(across, forward)
    wide, tall = grid
    half = np.tan(np.radians(view["fov"]) / 2)
    sideways = ((np.arange(wide) + 0.5) / wide * 2 - 1) * half
    lifted = (1 - (np.arange(tall) + 0.5) / tall * 2) * half * tall / wide
    grid_x, grid_y = np.meshgrid(sideways, lifted)
    directions = (forward + grid_x[..., None] * across + grid_y[..., None] * upward).reshape(-1, 3)
    return eye, directions / np.linalg.norm(directions, axis=1)[:, None]


def look(scene, view, grid=GRID):
    """What the view's grid of rays meets first: {"triangles": triangle per cell (-1 nothing), "distances"}, rows
    from the top. A ray starts past the camera's near clip, as the film's renderer does."""
    eye, directions = camera_rays(view, grid)
    origins = eye + directions * NEAREST
    located, rays, met = scene.mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    triangles = np.full(len(directions), -1)
    distances = np.full(len(directions), np.inf)
    triangles[rays] = met
    distances[rays] = np.linalg.norm(located - eye, axis=1)
    return {"triangles": triangles.reshape(grid[1], grid[0]), "distances": distances.reshape(grid[1], grid[0])}


def subset_materials(prim):
    """{face: bound material} of a mesh's subsets that bind one, and the prim's own bound material (or None)."""
    by_face = {}
    for subset in UsdGeom.Subset.GetAllGeomSubsets(UsdGeom.Imageable(prim)):
        material = UsdShade.MaterialBindingAPI(subset.GetPrim()).ComputeBoundMaterial()[0]
        if material:
            by_face.update(dict.fromkeys((subset.GetIndicesAttr().Get() or []), material))
    own = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
    return by_face, own if own else None


def shaders_of(material):
    """Every shader prim inside a material."""
    return [UsdShade.Shader(child) for child in Usd.PrimRange(material.GetPrim()) if child.IsA(UsdShade.Shader)]


def texture_unresolved(shader):
    """True when a UsdUVTexture's file names nothing that resolves."""
    found = shader.GetInput("file")
    asset = found.Get() if found else None
    return not isinstance(asset, Sdf.AssetPath) or not (asset.resolvedPath or "").strip()


def coordinate_names(shaders):
    """The texture coordinate primvars a material's readers read (default "st")."""
    names = set()
    for shader in shaders:
        if str(shader.GetIdAttr().Get() or "").startswith("UsdPrimvarReader"):
            name = shader.GetInput("varname")
            names.add(str(name.Get()) if name and name.Get() else "st")
    return names or {"st"}


def diffuse_colour(shaders):
    """A preview surface's unconnected diffuse colour, (r, g, b), or None when connected or none is authored."""
    for shader in shaders:
        if shader.GetIdAttr().Get() != "UsdPreviewSurface":
            continue
        found = shader.GetInput("diffuseColor")
        if found and not found.HasConnectedSource() and found.Get() is not None:
            return tuple(float(value) for value in found.Get())
    return None


def is_default_grey(colour):
    """True for no colour at all, or one of the default greys (DEFAULT_COLOURS) within 0.01."""
    return colour is None or any(max(abs(value - grey) for value, grey in zip(colour, default)) < 0.01
                                 for default in DEFAULT_COLOURS)


def material_kind(material, prim):
    """One material's surface kind on a prim: textured, or which way it is not."""
    if material is None:
        return NO_MATERIAL
    shaders = shaders_of(material)
    textures = [shader for shader in shaders if shader.GetIdAttr().Get() == "UsdUVTexture"]
    if not textures:
        return DEFAULT_GREY if is_default_grey(diffuse_colour(shaders)) else PLAIN_COLOUR
    if any(texture_unresolved(shader) for shader in textures):
        return TEXTURE_MISSING
    primvars = UsdGeom.PrimvarsAPI(prim)
    if prim.IsA(UsdGeom.Mesh) and not any(primvars.HasPrimvar(name) for name in coordinate_names(shaders)):
        return NO_TEXTURE_COORDINATES
    return TEXTURED


def instancer_kind(stage, prim):
    """A PointInstancer's kind, from its prototypes' meshes: textured when any is, else the first one's."""
    kinds = [prim_kinds(stage, str(mesh.GetPath()))[0]
             for target in UsdGeom.PointInstancer(prim).GetPrototypesRel().GetTargets()
             for mesh in Usd.PrimRange(stage.GetPrimAtPath(target)) if mesh.IsA(UsdGeom.Mesh)]
    return TEXTURED if TEXTURED in kinds or not kinds else kinds[0]


def prim_kinds(stage, path):
    """(kind of a face not in any binding subset, {face: kind}) of one prim, each material judged once; an
    instancer's from its prototypes."""
    prim = stage.GetPrimAtPath(path)
    if prim.IsA(UsdGeom.PointInstancer):
        return instancer_kind(stage, prim), {}
    by_face, own = subset_materials(prim)
    judged = {}
    for material in {*by_face.values(), own}:
        judged[material.GetPath() if material else None] = material_kind(material, prim)
    return judged[own.GetPath() if own else None], {face: judged[material.GetPath()]
                                                    for face, material in by_face.items()}


def material_names(stage, path):
    """{face: material name} of one prim's subsets and its own material's name (or None)."""
    by_face, own = subset_materials(stage.GetPrimAtPath(path))
    return {face: material.GetPrim().GetName() for face, material in by_face.items()}, (
        own.GetPrim().GetName() if own else None)


def cell_surfaces(stage, scene, triangles):
    """Per grid cell (-1 nothing): (prim path, material name, surface kind) of what it meets, None for nothing."""
    kinds, names = {}, {}
    found = np.empty(triangles.shape, dtype=object)
    for spot, triangle in np.ndenumerate(triangles):
        if triangle < 0:
            continue
        path = scene.prims[scene.prim_of[triangle]]
        if path not in kinds:
            kinds[path], names[path] = prim_kinds(stage, path), material_names(stage, path)
        face = int(scene.face_of[triangle])
        own_kind, face_kinds = kinds[path]
        face_names, own_name = names[path]
        found[spot] = (path, face_names.get(face, own_name), face_kinds.get(face, own_kind))
    return found


def record(stage, scene, view, grid=GRID):
    """What one view sees, as JSON: {"grid", "surfaces": [[prim path, material, kind]], "cells": rows of a surface's
    number (-1 nothing), "distances": rows of metres (null nothing)}."""
    met = look(scene, view, grid)
    surfaces = cell_surfaces(stage, scene, met["triangles"])
    listed = sorted({surface for surface in surfaces.ravel() if surface is not None}, key=str)
    number = {surface: index for index, surface in enumerate(listed)}
    return {"grid": list(grid), "surfaces": [list(surface) for surface in listed],
            "cells": [[number[surface] if surface is not None else -1 for surface in row] for row in surfaces],
            "distances": [[round(float(value), 2) if np.isfinite(value) else None for value in row]
                          for row in met["distances"]]}
