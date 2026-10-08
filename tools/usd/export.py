"""Write one place as an OpenUSD stage: the framework's canonical scene, which Blender and other engines load.

    .venv/bin/python tools/usd/export.py <place> --models <folder of the place's made .gltf> --out <folder>
                                         [--work <the route run's work folder> | --parts <folder of labelled takes>]

The labelled parts are read where the run's records put them: with --work, <work>/parts/<model>-<take>/ for the take
plan-route.json names; with --parts (or a run that recorded no take), each model's newest take of any name
(`<model>-r1` from a first run, `<model>-s1` from the framework's rerun), one <variant>.ply per library surface.

A place today is its made models (glTF) and its layout (`data/kit/<place>.json`), read by the game in Godot. The
stage holds the same place in three layers, from the strongest down:

    <out>/<place>.usda           the stage itself: no prims, only its two layers and the units (metres, y up)
    <out>/layers/edit.usda       the creator's changes; made empty once and never written here again
    <out>/layers/base.usda       what the framework made; rewritten whole on every export
    <out>/assets/<model>.usdc    each model once, referenced by every object that is laid with it
    <out>/assets/textures/       the models' baked maps, and the ground's skin, as PNG

A place outside with a ground record (data/ground/, read by tools/usd/ground.py) stands on it as the game stands it:
each object on a seat of its own under its spot (a `seat` orient op: the ball's curve under it), lifted by its `at`
height off the planned ground there, and the ground round the place is `/<place>/Ground`, a mesh of the planned
heights in the plan's skin. Without a record (a room, `--flat`) the ground is y = 0 and `at` is the position.

Because the edit layer sits above the base and objects keep their names across exports (`<row>_<n>`, the n-th
object of an inventory row in the layout's order), regenerating the base keeps every edit: a moved object stays
moved, a part given another surface keeps it. An object standing on another (the layout's `children`, a gas bottle
on a parts rack) is a child prim of that object, `<object>/<row>_<n>`, with its transform on the parent as the
parent's composite places it, so a parent moved in the edit layer carries it along.

A kit room (a room the route lays as a kit of pieces, each piece in a frame of its own: `x`, `y`, `z` in its layout,
written by tools/props/library/route.py) is exported the same way: each piece is an object named after its kind's own
name (`<own name>_<n>`), its transform the game's (its model's box fitted to the piece's laid size on the middle of its
foot, tools/props/library/package.kit_matrix) as one matrix op. Its models are best read from its scene package's
objects (package.py --kit), which holds the screens and lamps the route writes rather than bakes; with --work, the
labelled parts are the ones its bake jobs (job-chunky*.json) name for each model.

Each object carries its kind (`score:kind`), its inventory row and name, its transform in metres (translate, turn
about up by the facing, tilt, scale, as the game lays it), its collision (a convex hull round the model, a guide
mesh with UsdPhysics' collision API, as the game's prop scene has it; no rigid body, so it is static), and its
sound (`score:sound`, the impact sound of its largest surface). Each part of a model is a GeomSubset named after
the library surface it is painted with, bound to a material of that name drawn with the model's baked maps, and
carrying that surface's sounds. A part can be given any of the place's library surfaces (`/<place>/Library`).
Mass and friction are not written: the game lays these pieces as static bodies with its default physics material
and the framework records neither yet.

Geometry is converted rather than referenced as glTF: usd-core and Blender's USD importer have no glTF file
format plugin, and a plain UsdGeomMesh with UsdPreviewSurface materials and PNG maps is what every USD reader
(Blender, Omniverse, Unreal, Houdini, usdview) loads. Library: usd-core (Pixar's OpenUSD, Tomorrow Open Source
Technology License 1.0: Apache 2.0 with a different trademark clause; commercial use allowed).
"""
import argparse
import json
import pathlib
import re
import sys

import numpy as np
import trimesh
from PIL import Image
from pxr import Gf, Kind, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade, Vt
from scipy.spatial import cKDTree

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools/props"))
sys.path.insert(0, str(REPO / "tools/usd"))
sys.path.insert(0, str(REPO / "tools/props/library"))
import glb_file  # noqa: E402
import ground as grounds  # noqa: E402
import library  # noqa: E402
import package  # noqa: E402

KITS = REPO / "data/kit"
INVENTORIES = REPO / "data/inventory"
DETAILS = REPO / "data/library/details.json"
COMPOSITES = REPO / "data/library/composites.json"
SOUNDS = REPO / "data/sound/surfaces.json"
# How many points of a labelled model the part lookup keeps at most: enough to tell parts apart a few
# millimetres wide, few enough that a million-face model never loads whole into the tree.
PART_POINTS = 400_000
EDIT_NOTE = ("The creator's changes to this place. The framework never writes this layer; it sits above the "
             "generated base, so every change here survives a regeneration.")
BASE_NOTE = "Generated by tools/usd/export.py from the place's layout and made models; rewritten on every export."


# --- reading the place --------------------------------------------------------------------------------------------

def read_gltf(path):
    """A .gltf with its .bin beside it, as glb_file's (document, list of each buffer view's bytes)."""
    document = json.loads(pathlib.Path(path).read_text())
    if len(document["buffers"]) != 1:
        raise ValueError(f"{path}: one buffer expected, found {len(document['buffers'])}")
    blob = (pathlib.Path(path).parent / document["buffers"][0]["uri"]).read_bytes()
    views = [blob[view.get("byteOffset", 0):view.get("byteOffset", 0) + view["byteLength"]]
             for view in document["bufferViews"]]
    return document, views


def model_geometry(path):
    """The model's one primitive: positions, normals, texture coordinates and triangles, in the file's metres."""
    document, views = read_gltf(path)
    primitives = [primitive for mesh in document["meshes"] for primitive in mesh["primitives"]]
    if len(primitives) != 1 or len(document["nodes"]) != 1 or set(document["nodes"][0]) - {"mesh", "name"}:
        raise ValueError(f"{path}: a made model is one untransformed node with one primitive")
    attributes = primitives[0]["attributes"]
    return {
        "positions": glb_file.accessor_array(document, views, attributes["POSITION"]).astype(np.float64),
        "normals": glb_file.accessor_array(document, views, attributes["NORMAL"]).astype(np.float64),
        "uvs": glb_file.accessor_array(document, views, attributes["TEXCOORD_0"]).astype(np.float64),
        "triangles": glb_file.accessor_array(document, views, primitives[0]["indices"]).reshape(-1, 3).astype(np.int64),
    }


def model_maps(path):
    """The model's baked maps by role (base_color, metal_roughness, normal), each the picture file it names."""
    document = json.loads(pathlib.Path(path).read_text())
    material = document["materials"][document["meshes"][0]["primitives"][0]["material"]]
    texture_of = {
        "base_color": material["pbrMetallicRoughness"].get("baseColorTexture"),
        "metal_roughness": material["pbrMetallicRoughness"].get("metallicRoughnessTexture"),
        "normal": material.get("normalTexture"),
    }
    found = {}
    for role, reference in texture_of.items():
        if reference is None:
            continue
        texture = document["textures"][reference["index"]]
        source = texture.get("extensions", {}).get("EXT_texture_webp", {}).get("source", texture.get("source"))
        found[role] = pathlib.Path(path).parent / document["images"][source]["uri"]
    return found


def labelled_take(parts, model, take=None):
    """A model's labelled take in the parts folder: `<model>-<take>` when the run recorded its take (plan-route.json),
    else the newest written of its takes under any take name (`-r1` from a first run, `-s1` from the framework's own
    rerun); None when the model has none."""
    if parts is None:
        return None
    if isinstance(parts, dict):  # a kit room's run: each model's labelled folder as its bake job names it
        found = parts.get(model)
        return found if found is not None and found.is_dir() else None
    if take is not None:
        found = pathlib.Path(parts) / f"{model}-{take}"
        return found if found.is_dir() else None
    takes = [found for found in pathlib.Path(parts).glob(f"{model}-*")
             if re.fullmatch(rf"{re.escape(model)}-[a-z]+\d+", found.name) and any(found.glob("*.ply"))]
    return max(takes, key=lambda found: max(ply.stat().st_mtime for ply in found.glob("*.ply"))) if takes else None


def run_parts(work):
    """Where a route run's labelled parts are and which take it made, from its own records: <work>/parts and the
    take plan-route.json names (None when the run did not record one); a kit room's run (route.py, no plan-route.json)
    gives each model's labelled folder as its bake jobs name it, and no take."""
    work = pathlib.Path(work)
    if not (work / "plan-route.json").exists():
        named = {}
        for job in sorted(work.glob("job-chunky*.json")):
            named.update({entry["name"]: pathlib.Path(entry["parts"])
                          for entry in json.loads(job.read_text())["chunky"]})
        return named, None
    planned = json.loads((work / "plan-route.json").read_text())
    return work / "parts", planned.get("take")


def part_points(take, turn, size):
    """Each labelled part's points in the kit frame the made model stands in: turned by the kind's turn and fitted
    to its laid size on the middle of its foot, as the route's make_chunky does; (points, variant of each point)."""
    files = sorted(take.glob("*.ply"))
    if not files:
        raise ValueError(f"{take}: no labelled parts")
    meshes = [trimesh.load(found, process=False) for found in files]
    total = sum(len(mesh.vertices) for mesh in meshes)
    stride = max(1, total // PART_POINTS)
    points = np.vstack([np.asarray(mesh.vertices)[::stride] for mesh in meshes]) @ np.asarray(turn).reshape(3, 3).T
    names = np.concatenate([np.full(len(np.asarray(mesh.vertices)[::stride]), found.stem)
                            for mesh, found in zip(meshes, files)])
    low, high = points.min(axis=0), points.max(axis=0)
    foot = np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])
    return (points - foot) * (np.asarray(size, dtype=np.float64) / (high - low)), names


def face_surfaces(geometry, points, names):
    """Each triangle's library surface: the part whose nearest labelled point lies under the triangle's middle."""
    middles = geometry["positions"][geometry["triangles"]].mean(axis=1)
    return names[cKDTree(points).query(middles)[1]]


def sound_of(variant, variants, sounds):
    """A library surface's sounds: the surface it sounds like (its own, else its family's) and that surface's
    footstep, impact, scrape and absorption; None for a part named after a place's own material that is no library
    surface (the hub's older `brushed_steel`), whose sound is not known."""
    if variant not in variants:
        return None
    surface = variants[variant].get("surface") or library.theme_library()["families"][variants[variant]["family"]]["surface"]
    entry = sounds["surfaces"].get(surface, sounds["fallback"])
    return dict(entry, surface=surface)


# --- the asset of one model ---------------------------------------------------------------------------------------

def png_maps(maps, textures):
    """Each baked map written as PNG into the textures folder; the asset-relative path of each by role."""
    textures.mkdir(parents=True, exist_ok=True)
    found = {}
    for role, source in maps.items():
        target = textures / f"{source.stem}.png"
        if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
            Image.open(source).save(target)
        found[role] = f"./textures/{target.name}"
    return found


def baked_material(stage, path, maps, surface):
    """A material drawn with the model's baked maps (UsdPreviewSurface), named for the library surface it paints;
    its surface's name, family and sounds ride on it."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    reader = UsdShade.Shader.Define(stage, f"{path}/uv")
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    coordinates = reader.CreateOutput("result", Sdf.ValueTypeNames.Float2)
    for role, file in maps.items():
        texture = UsdShade.Shader.Define(stage, f"{path}/{role}")
        texture.CreateIdAttr("UsdUVTexture")
        texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(file)
        texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(coordinates)
        texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB" if role == "base_color" else "raw")
        if role == "base_color":
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
        elif role == "metal_roughness":  # glTF packs roughness in green and metal in blue
            shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).ConnectToSource(
                texture.CreateOutput("g", Sdf.ValueTypeNames.Float))
            shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).ConnectToSource(
                texture.CreateOutput("b", Sdf.ValueTypeNames.Float))
        else:
            texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(2, 2, 2, 1))
            texture.CreateInput("bias", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(-1, -1, -1, 0))
            shader.CreateInput("normal", Sdf.ValueTypeNames.Normal3f).ConnectToSource(
                texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    if surface is not None:
        material.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(surface)
    return material


def surface_attributes(prim, variant, variants, sounds):
    """The library surface a part is, with its family and its sounds, as score:* attributes on the part."""
    sound = sound_of(variant, variants, sounds)
    if sound is None:
        prim.CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(variant)
        return
    values = {"score:surface": variant, "score:family": variants[variant]["family"],
              "score:sound:surface": sound["surface"], "score:sound:footstep": sound["footstep"],
              "score:sound:impact": sound["impact"], "score:sound:scrape": sound["scrape"]}
    for name, value in values.items():
        prim.CreateAttribute(name, Sdf.ValueTypeNames.String).Set(value)
    if "absorbs" in sound:
        prim.CreateAttribute("score:sound:absorbs", Sdf.ValueTypeNames.Float).Set(float(sound["absorbs"]))


def render_mesh(stage, path, geometry):
    """The model's drawn mesh: its triangles, smooth normals and texture coordinates (flipped to USD's lower-left
    origin), never subdivided."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    positions = geometry["positions"]
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(positions.astype(np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(geometry["triangles"]), 3, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(geometry["triangles"].reshape(-1).astype(np.int32)))
    mesh.CreateNormalsAttr(Vt.Vec3fArray.FromNumpy(geometry["normals"].astype(np.float32)))
    mesh.SetNormalsInterpolation(UsdGeom.Tokens.vertex)
    flipped = np.column_stack([geometry["uvs"][:, 0], 1.0 - geometry["uvs"][:, 1]]).astype(np.float32)
    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
        Vt.Vec2fArray.FromNumpy(flipped))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateDoubleSidedAttr(True)
    mesh.CreateExtentAttr([Gf.Vec3f(*positions.min(axis=0)), Gf.Vec3f(*positions.max(axis=0))])
    return mesh


def collision_mesh(stage, path, geometry):
    """The model's collision: a convex hull round it, as the game's prop scene has, a guide mesh (never drawn)
    with UsdPhysics' collision API and a convex hull approximation."""
    hull = trimesh.Trimesh(geometry["positions"], geometry["triangles"], process=False).convex_hull
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(np.asarray(hull.vertices, dtype=np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(hull.faces), 3, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(np.asarray(hull.faces, dtype=np.int32).reshape(-1)))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreatePurposeAttr(UsdGeom.Tokens.guide)
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    UsdPhysics.MeshCollisionAPI.Apply(mesh.GetPrim()).CreateApproximationAttr(UsdPhysics.Tokens.convexHull)
    return mesh


def part_subsets(stage, mesh, surfaces, maps, variants, sounds):
    """One GeomSubset per library surface over the faces painted with it, each bound to its own baked material;
    the name of the surface with the most area comes back (the model's sound)."""
    model_path = mesh.GetPath().GetParentPath()
    areas = trimesh.Trimesh(np.asarray(mesh.GetPointsAttr().Get()), np.asarray(
        mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3), process=False).area_faces
    for variant in sorted(set(surfaces)):
        faces = np.nonzero(surfaces == variant)[0].astype(np.int32)
        subset = UsdGeom.Subset.CreateGeomSubset(mesh, variant, UsdGeom.Tokens.face, Vt.IntArray.FromNumpy(faces),
                                                 UsdShade.Tokens.materialBind)
        material = baked_material(stage, model_path.AppendPath(f"Looks/{variant}"), maps, variant)
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(material)
        surface_attributes(subset.GetPrim(), variant, variants, sounds)
    UsdGeom.Subset.SetFamilyType(mesh, UsdShade.Tokens.materialBind, UsdGeom.Tokens.partition)
    return max(set(surfaces), key=lambda variant: areas[surfaces == variant].sum())


def write_asset(model, models, parts, take, turn, size, out, variants, sounds):
    """One model as its own USD file under <out>/assets: drawn mesh, parts, collision; its largest surface back
    (None when the model has no labelled parts)."""
    gltf = pathlib.Path(models) / f"{model}.gltf"
    geometry = model_geometry(gltf)
    maps = png_maps(model_maps(gltf), out / "assets/textures")
    stage = Usd.Stage.CreateNew(str(out / "assets" / f"{model}.usdc"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, f"/{model}")
    stage.SetDefaultPrim(root.GetPrim())
    Usd.ModelAPI(root).SetKind(Kind.Tokens.component)
    UsdGeom.Scope.Define(stage, f"/{model}/Looks")
    mesh = render_mesh(stage, f"/{model}/geo", geometry)
    collision_mesh(stage, f"/{model}/collision", geometry)
    labelled = labelled_take(parts, model, take)
    largest = None
    if labelled is None:
        UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(baked_material(stage, f"/{model}/Looks/baked", maps, None))
    else:
        points, names = part_points(labelled, turn, size)
        largest = part_subsets(stage, mesh, face_surfaces(geometry, points, names), maps, variants, sounds)
    stage.GetRootLayer().Save()
    return largest


# --- the place's layers -------------------------------------------------------------------------------------------

def kit_room_pieces(kit, models):
    """A kit room's pieces as objects: each its kind's own name as its row, and its transform (`matrix`, the game's,
    package.kit_matrix) from its model's box; the layout's other fields as they are."""
    room = kit.get("room", "")
    found = []
    for laid in kit["pieces"]:
        matrix, _ = package.kit_matrix(laid, *package.model_box(pathlib.Path(models) / f"{laid['model']}.gltf"))
        own = laid["kind"].removeprefix(f"{room}_")
        # A glowing part (a lamp's lens, a screen) is an object of its own, named apart from its host's.
        found.append(dict(laid, row=f"{own}_{laid['part']}" if "part" in laid else own, matrix=matrix.tolist()))
    return found


def object_names(pieces):
    """Each piece's object name, `<row>_<n>`: the n-th piece of its inventory row in the layout's order, so a name
    means the same object in every export."""
    counts, names = {}, []
    for piece in pieces:
        counts[piece["row"]] = counts.get(piece["row"], 0) + 1
        names.append(f"{piece['row']}_{counts[piece['row']]}")
    return names


def child_pieces(place, kit, inventory, composites):
    """Each object standing on another (the layout's `children`: its row and the row it stands `on`), as pieces laid
    in the parent's own frame: where the parent's composite (data/library/composites.json) stands it, its foot at
    `at` and turned `turn` degrees about up, as the game's prop scene places it; {parent row: [piece]}."""
    rows = {row["id"]: row for row in inventory["rows"]}
    kinds = {piece["row"]: piece["kind"] for piece in kit["pieces"]}
    found = {}
    for child in kit.get("children", []):
        kind = rows[child["row"]]["thing"].split(":", 1)[1]
        spots = [spot for spot in composites.get(kinds[child["on"]], {}).get("children", []) if spot["kind"] == kind]
        if not spots:
            raise ValueError(f"{place}: {child['row']} stands on {child['on']}, whose composite has no {kind}")
        found.setdefault(child["on"], []).extend(
            {"kind": kind, "model": child["row"], "row": child["row"], "size": list(spot["size"]),
             "at": list(spot["at"]), "facing": -float(spot.get("turn", 0.0))} for spot in spots)
    return found


def library_materials(stage, place, root):
    """Every library surface the place takes, as a flat-coloured UsdPreviewSurface under <root>/Library (its
    palette colour, roughness and metal), for the creator to give a part; recipe and token ride along."""
    for name, spec in library.by_library(place).items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
            raise ValueError(f"library surface '{name}' is not a USD prim name")
        material = UsdShade.Material.Define(stage, f"{root}/Library/{name}")
        shader = UsdShade.Shader.Define(stage, f"{root}/Library/{name}/surface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*spec["colour"]))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(spec.get("roughness", 0.5)))
        shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(spec.get("metal", 0.0)))
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        for key in ("recipe", "token", "family"):
            material.GetPrim().CreateAttribute(f"score:{key}", Sdf.ValueTypeNames.String).Set(str(spec[key]))


def laid_object(stage, path, piece, row, asset, sound, ground=None):
    """One object of the place: its model referenced, its transform as the game lays it (on the place's ground when
    it has one: stood on a seat of its own under its spot, lifted off the ground there), its kind, inventory row,
    name, lift and sound."""
    xform = UsdGeom.Xform.Define(stage, path)
    xform.GetPrim().GetReferences().AddReference(asset)
    if "matrix" in piece:  # a kit room's piece: its frame as one transform (USD's matrices are row by row, transposed)
        xform.AddTransformOp().Set(Gf.Matrix4d(np.asarray(piece["matrix"]).T.tolist()))
    else:
        stand_on(xform, piece["at"], ground)
        xform.AddRotateYOp().Set(-float(piece.get("facing", 0.0)))
        xform.AddRotateXOp().Set(float(piece.get("tilt", 0.0)))
        xform.AddScaleOp().Set(Gf.Vec3f(float(piece.get("scale", 1.0))))
    values = {"score:kind": piece["kind"], "score:row": piece["row"], "score:model": piece["model"],
              "score:name": row.get("name", ""), "score:anchor": row.get("anchor", "")}
    if "layer" in piece:  # a kit room's draw layer: 2 is its roof, left out of a cutaway look
        values["score:layer"] = str(piece["layer"])
    if sound is not None:
        values.update({"score:sound": sound["impact"], "score:sound:surface": sound["surface"]})
    for name, value in values.items():
        xform.GetPrim().CreateAttribute(name, Sdf.ValueTypeNames.String).Set(value)
    xform.GetPrim().CreateAttribute("score:size", Sdf.ValueTypeNames.Float3).Set(Gf.Vec3f(*piece["size"]))
    if "at" in piece:
        xform.GetPrim().CreateAttribute("score:lift", Sdf.ValueTypeNames.Float).Set(float(piece["at"][1]))


def stand_on(xform, at, ground):
    """Where a laid thing stands: at its `at` on a flat place; on a place with ground, on the ground under its spot
    lifted by its up, and turned with its own seat (the ball's curve under it) by an orient op named `seat`."""
    if ground is None:
        xform.AddTranslateOp().Set(Gf.Vec3d(*at))
        return
    position, seat_turn = ground.standing(float(at[0]), float(at[2]), float(at[1]))
    xform.AddTranslateOp().Set(Gf.Vec3d(*position.tolist()))
    turn = Gf.Matrix3d(*seat_turn.reshape(-1).tolist()).ExtractRotation().GetQuat()
    xform.AddOrientOp(UsdGeom.XformOp.PrecisionDouble, "seat").Set(turn)


def ground_mesh(stage, path, ground, pieces, out):
    """The place's ground round its pieces: a drawn mesh of the planned heights, coloured with the plan's skin (cut
    to the patch, as PNG under assets/textures), and a static collider."""
    spots = np.array([[piece["at"][0], piece["at"][2]] for piece in pieces])
    points, triangles, skin_at = ground.mesh(spots.min(axis=0), spots.max(axis=0))
    picture = Image.open(ground.skin).convert("RGB")
    wide, tall = picture.size
    low = np.floor(skin_at.min(axis=0) * [wide, tall]).astype(int).clip(0, [wide - 1, tall - 1])
    high = np.ceil(skin_at.max(axis=0) * [wide, tall]).astype(int).clip(1, [wide, tall])
    textures = out / "assets/textures"
    textures.mkdir(parents=True, exist_ok=True)
    picture.crop((*low, *high)).save(textures / "ground_skin.png")
    inside = (skin_at * [wide, tall] - low) / (high - low)
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points.astype(np.float32)))
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(triangles), 3, dtype=np.int32)))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(triangles.reshape(-1).astype(np.int32)))
    UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
        Vt.Vec2fArray.FromNumpy(np.column_stack([inside[:, 0], 1.0 - inside[:, 1]]).astype(np.float32)))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateExtentAttr([Gf.Vec3f(*points.min(axis=0)), Gf.Vec3f(*points.max(axis=0))])
    UsdPhysics.CollisionAPI.Apply(mesh.GetPrim())
    mesh.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("ground")
    material = baked_material(stage, f"{path}_look", {"base_color": "../assets/textures/ground_skin.png"}, None)
    shader = UsdShade.Shader(stage.GetPrimAtPath(f"{path}_look/surface"))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)  # regolith has no shine
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(material)


def lamp(stage, path, entry, ground=None):
    """A lamp of the layout: a small sphere light where it hangs, its strength and reach as the game reads them."""
    light = UsdLux.SphereLight.Define(stage, path)
    stand_on(light, entry["at"], ground)
    light.CreateRadiusAttr(0.05)
    light.GetPrim().CreateAttribute("score:strength", Sdf.ValueTypeNames.Float).Set(float(entry.get("strength", 1.0)))
    light.GetPrim().CreateAttribute("score:range", Sdf.ValueTypeNames.Float).Set(float(entry.get("range", 6.0)))


def write_base(place, kit, inventory, assets, out, children, ground=None):
    """The generated layer, rewritten whole: the place's root, its library surfaces, its objects (each child under
    the object it stands on, named as objects are, so moving the parent moves it) and its lamps."""
    path = out / "layers/base.usda"
    path.parent.mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.FindOrOpen(str(path)) or Sdf.Layer.CreateNew(str(path))
    layer.Clear()
    layer.documentation = BASE_NOTE
    stage = Usd.Stage.Open(layer)
    root = UsdGeom.Xform.Define(stage, f"/{place}")
    Usd.ModelAPI(root).SetKind(Kind.Tokens.assembly)
    Usd.ModelAPI(UsdGeom.Xform.Define(stage, f"/{place}/Objects")).SetKind(Kind.Tokens.group)
    UsdGeom.Scope.Define(stage, f"/{place}/Library")
    library_materials(stage, kit.get("place", place), f"/{place}")  # a room in a place of another name
    rows = {row["id"]: row for row in inventory["rows"]}
    for name, piece in zip(object_names(kit["pieces"]), kit["pieces"]):
        model = piece["model"]
        laid_object(stage, f"/{place}/Objects/{name}", piece, rows.get(piece["row"], {}),
                    f"../assets/{model}.usdc", assets[model], ground)
        on_it = children.get(piece["row"], [])
        for child_name, child in zip(object_names(on_it), on_it):
            laid_object(stage, f"/{place}/Objects/{name}/{child_name}", child, rows.get(child["row"], {}),
                        f"../assets/{child['model']}.usdc", assets[child["model"]])
    if kit.get("lamps"):
        UsdGeom.Scope.Define(stage, f"/{place}/Lamps")
    for number, entry in enumerate(kit.get("lamps", []), start=1):
        lamp(stage, f"/{place}/Lamps/lamp_{number}", entry, ground)
    if ground is not None:
        ground_mesh(stage, f"/{place}/Ground", ground, kit["pieces"], out)
    layer.Save()


def ensure_edit(out):
    """The creator's layer: made empty the first time, left exactly as it is every time after."""
    path = out / "layers/edit.usda"
    if path.exists():
        return
    layer = Sdf.Layer.CreateNew(str(path))
    layer.documentation = EDIT_NOTE
    layer.Save()


def write_root(place, out):
    """The stage's own file: the edit layer over the base, metres, y up, the place as its default prim."""
    path = out / f"{place}.usda"
    layer = Sdf.Layer.FindOrOpen(str(path)) or Sdf.Layer.CreateNew(str(path))
    layer.Clear()
    layer.subLayerPaths.append("./layers/edit.usda")
    layer.subLayerPaths.append("./layers/base.usda")
    layer.defaultPrim = place
    layer.pseudoRoot.SetInfo("upAxis", UsdGeom.Tokens.y)
    layer.pseudoRoot.SetInfo("metersPerUnit", 1.0)
    layer.Save()
    return path


# --- the way in ---------------------------------------------------------------------------------------------------

def export(place, models, out, parts=None, kit_path=None, inventory_path=None, take=None, ground=None):
    """Write the place's stage under `out` (base and assets rewritten, the edit layer kept) and return its path.
    `take` is the labelled take the run recorded; without it each model's newest take in `parts` is read. `ground`
    is the place's tools/usd/ground.Ground; without one the place is flat."""
    out = pathlib.Path(out)
    kit = json.loads(pathlib.Path(kit_path or KITS / f"{place}.json").read_text())
    if kit["pieces"] and "x" in kit["pieces"][0]:
        kit = dict(kit, pieces=kit_room_pieces(kit, models))
    if inventory_path is None:  # a room of a place of another name keeps its inventory under the place's (the flat)
        inventory_path = next((path for path in (INVENTORIES / f"{place}.json", INVENTORIES / f"{kit.get('place')}.json")
                               if path.exists()), INVENTORIES / f"{place}.json")
    inventory = json.loads(pathlib.Path(inventory_path).read_text())
    children = child_pieces(place, kit, inventory, json.loads(COMPOSITES.read_text()))
    details = json.loads(DETAILS.read_text())
    variants = library.variants(library.theme_library())
    sounds = json.loads(SOUNDS.read_text())
    (out / "assets").mkdir(parents=True, exist_ok=True)
    assets = {}
    for piece in kit["pieces"] + [child for on_it in children.values() for child in on_it]:
        model = piece["model"]
        if model in assets:
            continue
        turn = details.get(piece["kind"], {}).get("turn", [1, 0, 0, 0, 1, 0, 0, 0, 1])
        largest = write_asset(model, models, parts, take, turn, piece["size"], out, variants, sounds)
        assets[model] = None if largest is None else sound_of(largest, variants, sounds)
    write_base(place, kit, inventory, assets, out, children, ground)
    ensure_edit(out)
    return write_root(place, out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("place")
    parser.add_argument("--models", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    found = parser.add_mutually_exclusive_group()
    found.add_argument("--work", type=pathlib.Path, help="the route run's work folder: its parts and recorded take")
    found.add_argument("--parts", type=pathlib.Path, help="a folder of labelled takes, each model's newest read")
    parser.add_argument("--flat", action="store_true", help="lay the place on flat ground even if it has a ground")
    arguments = parser.parse_args()
    parts, take = run_parts(arguments.work) if arguments.work else (arguments.parts, None)
    kit = json.loads((KITS / f"{arguments.place}.json").read_text())
    laid_on = None if arguments.flat else grounds.place_ground(arguments.place, kit.get("on_seat", [0.0, 0.0]))
    print(export(arguments.place, arguments.models, arguments.out, parts, take=take, ground=laid_on))


if __name__ == "__main__":
    main()
