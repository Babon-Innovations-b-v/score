"""A glTF-only library entry made layable (#128, the camp pilot: our picture-made models and takes hold only a .glb):
its meshes, each where the glTF's node tree sets it, joined into one USD mesh `geo` (y up, metres, as glTF is), with
their texture coordinates and smooth normals, each of its materials a named part (a GeomSubset, as the kit pieces'
colour regions are) wearing that material's own bake and paint (owner 2026-11-16: the made props with their bakes and
paint): a UsdPreviewSurface reading its base colour, metal-roughness and normal maps, written beside it as PNGs, or its
flat factors where it has no map. `surface` still puts a library surface over a part or the whole. A moving part (a
node named `<part>__<joint>_<axis>[n]`, score/stages/props/moving_parts' interface; a made model's door or drawer,
maker/parts.py, #177) is its own Xform of that name at its node's place, holding its own `geo`, so the motion layer
(from_design.parts_of) and the physics layer (tools/usd/physics.write_parted) find its pivot. Converted once, beside
the glTF in the place's assets.

    converted(path) -> <path>.usdc
"""
import pathlib
import re

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt


def part_name(material, number):
    """A USD-safe part name of a glTF material's name (`part_<n>` for one with none)."""
    name = re.sub(r"[^A-Za-z0-9_]", "_", getattr(material, "name", None) or "")
    return name if name and not name[0].isdigit() else f"part_{number}"


def moving_node(scene, node):
    """The nearest node at or above `node` named as a moving part (score/stages/props/moving_parts' interface,
    `<part>__<joint>_<axis>[n]`, its origin the pivot: from_design.PART), None when none is."""
    from score.stages.motion import from_design
    parents = scene.graph.transforms.parents
    while node is not None:
        if from_design.PART.match(str(node)):
            return node
        node = parents.get(node)
    return None


def meshes(path):
    """[(part name, material, points (n x 3), normals (n x 3), uv (n x 2) or None, triangles (m x 3), its moving
    part's node or None)] of the glTF at `path`, each in the scene's frame."""
    import trimesh
    scene = trimesh.load(str(path), force="scene")
    found = []
    for number, node in enumerate(scene.graph.nodes_geometry):
        transform, geometry = scene.graph[node]
        mesh = scene.geometry[geometry]
        if not hasattr(mesh, "faces") or not len(mesh.faces):
            continue
        visual = getattr(mesh, "visual", None)
        material = getattr(visual, "material", None)
        uv = getattr(visual, "uv", None)
        normals = trimesh.transform_points(mesh.vertex_normals, transform, translate=False)
        found.append((part_name(material, number), material, trimesh.transform_points(mesh.vertices, transform),
                      normals, None if uv is None or len(uv) != len(mesh.vertices) else uv, mesh.faces,
                      moving_node(scene, node)))
    if not found:
        raise ValueError(f"{path}: no mesh in this glTF")
    return found, scene


# A glTF map's slot on the UsdPreviewSurface: (its file's ending, its colour space, [(texture output, shader input,
# its type)]); glTF keeps roughness in green and metalness in blue.
MAPS = {"baseColorTexture": ("base", "sRGB", [("rgb", "diffuseColor", Sdf.ValueTypeNames.Color3f)]),
        "metallicRoughnessTexture": ("metal_rough", "raw", [("g", "roughness", Sdf.ValueTypeNames.Float),
                                                            ("b", "metallic", Sdf.ValueTypeNames.Float)]),
        "normalTexture": ("normal", "raw", [("rgb", "normal", Sdf.ValueTypeNames.Normal3f)])}


def linear(value):
    """An sRGB channel (0..1) as linear (glTF's factors are linear already; its colour maps are sRGB)."""
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def factors(material):
    """{shader input: value} of a glTF material's flat factors (its colour in linear RGB, its opacity, metalness and
    roughness), for where it has no map."""
    found = {}
    colour = getattr(material, "baseColorFactor", None)
    if colour is not None:
        colour = np.asarray(colour, dtype=float) / (255.0 if np.asarray(colour).dtype.kind in "iu" else 1.0)
        found["diffuseColor"] = Gf.Vec3f(*map(float, colour[:3]))
        if len(colour) > 3 and colour[3] < 1.0:
            found["opacity"] = float(colour[3])
    for name, key in (("metallicFactor", "metallic"), ("roughnessFactor", "roughness")):
        if getattr(material, name, None) is not None:
            found[key] = float(getattr(material, name))
    return found


def look(stage, path, material, folder, stem):
    """The glTF material as a UsdPreviewSurface at `path`, its maps written to `folder` as <stem>.<slot>.png."""
    made = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    made.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    reader = UsdShade.Shader.Define(stage, f"{path}/st")
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")
    for key, value in factors(material).items():
        shader.CreateInput(key, Sdf.ValueTypeNames.Color3f if key == "diffuseColor" else Sdf.ValueTypeNames.Float
                           ).Set(value)
    for attribute, (ending, space, outputs) in MAPS.items():
        image = getattr(material, attribute, None)
        if image is None:
            continue
        name = f"{stem}.{ending}.png"
        image.save(folder / name)
        texture = UsdShade.Shader.Define(stage, f"{path}/{ending}")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"./{name}")
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set(space)
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(reader.ConnectableAPI(), "result")
        if ending == "normal":
            texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2, 2, 2, 1))
            texture.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1, -1, -1, 0))
        for output, input_name, kind in outputs:
            texture.CreateOutput(output, Sdf.ValueTypeNames.Float3 if output == "rgb" else Sdf.ValueTypeNames.Float)
            shader.CreateInput(input_name, kind).ConnectToSource(texture.ConnectableAPI(), output)
    return made


def written_mesh(stage, at, pieces, path, looked):
    """One USD mesh `at` of `pieces` (meshes' rows, their points and normals already in its frame), a part a material
    (a GeomSubset bound to its look under /model/Looks, each look written once: `looked`)."""
    points, normals, uvs, triangles, parts, materials = [], [], [], [], {}, {}
    for name, material, mesh_points, mesh_normals, mesh_uv, mesh_triangles, _ in pieces:
        first = len(triangles)
        triangles += [[int(index) + len(points) for index in triangle] for triangle in mesh_triangles]
        points += [Gf.Vec3f(*map(float, point)) for point in mesh_points]
        normals += [Gf.Vec3f(*map(float, normal)) for normal in mesh_normals]
        uvs += [Gf.Vec2f(*map(float, uv)) for uv in (mesh_uv if mesh_uv is not None else np.zeros((len(mesh_points), 2)))]
        parts.setdefault(name, []).extend(range(first, len(triangles)))
        materials.setdefault(name, material)
    mesh = UsdGeom.Mesh.Define(stage, at)
    mesh.CreatePointsAttr(Vt.Vec3fArray(points))
    mesh.CreateNormalsAttr(Vt.Vec3fArray(normals))
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
        Vt.Vec2fArray(uvs))
    mesh.CreateFaceVertexCountsAttr([3] * len(triangles))
    mesh.CreateFaceVertexIndicesAttr([index for triangle in triangles for index in triangle])
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    for name, faces in parts.items():
        subset = UsdGeom.Subset.CreateGeomSubset(mesh, name, UsdGeom.Tokens.face, faces, "materialBind",
                                                 UsdGeom.Tokens.nonOverlapping)
        if name not in looked:
            looked[name] = look(stage, f"/model/Looks/{name}", materials[name], path.parent, f"{path.stem}.{name}")
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(looked[name])


def in_part(pieces, matrix):
    """The pieces' points and normals carried from the scene's frame into a part's (its node's world `matrix`)."""
    import trimesh
    inverse = np.linalg.inv(matrix)
    return [(name, material, trimesh.transform_points(points, inverse),
             trimesh.transform_points(normals, inverse, translate=False), uv, triangles, node)
            for name, material, points, normals, uv, triangles, node in pieces]


def converted(path):
    """The glTF at `path` as one USD mesh `geo` with a part a material, each part in its own bake, and each moving
    part (a node named `<part>__<joint>_<axis>[n]`, #177) an Xform of that name where its node stands (its origin the
    pivot the motion and physics layers turn it about) holding its own `geo`; written once beside it; its path."""
    path = pathlib.Path(path)
    target = path.with_suffix(".usdc")
    if target.exists():
        return target
    stage = Usd.Stage.CreateNew(str(target))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/model")
    stage.SetDefaultPrim(root.GetPrim())
    found, scene = meshes(path)
    looked = {}
    still = [piece for piece in found if piece[6] is None]
    if still:
        written_mesh(stage, "/model/geo", still, path, looked)
    for node in dict.fromkeys(piece[6] for piece in found if piece[6] is not None):
        matrix = np.asarray(scene.graph[node][0], dtype=float)
        part = UsdGeom.Xform.Define(stage, f"/model/{node}")
        part.MakeMatrixXform().Set(Gf.Matrix4d(matrix.T.tolist()))  # USD's matrices act on row vectors
        written_mesh(stage, f"/model/{node}/geo", in_part([piece for piece in found if piece[6] == node], matrix),
                     path, looked)
    stage.GetRootLayer().Save()
    return target
