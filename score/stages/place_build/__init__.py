"""The placing agent's scene (#128, owner 2026-11-16): a place laid by hand from library entries, step by step, until
its render reads as the locked concept. One folder a place holds everything:

    <folder>/place.json    {"place", "concept", "size", "camera": {"eye", "aim", "fov"}, "objects"}
    <folder>/concept.png   the locked concept picture, copied in
    <folder>/objects.json  the concept's objects (score/review/concept_objects.py: word, box, score, mask), when split
    <folder>/scene.usda    the scene: a plain OpenUSD stage, y up, metres, default prim /<place>
    <folder>/assets/...    each placed entry's files, copied from the library (library_files.stage_name's folders)

The scene's layout is the one tools/usd reads (snap.py, resting.py) and sim body takes as its ground:
/<place>/Objects/<name> an Xform referencing its library entry's USD (translate, rotateXYZ in degrees, scale; its
address in `score:library`), /<place>/Looks/<name> the preview look of the library surface an object wears (bound
stronger than anything inside it, so a model's own baked colour never shows; its address in `score:surface`), and
/<place>/Lights/<name> a sphere light laid as the library's lamp (`score:library`).

    start(folder, place, concept, objects=None)        a new place folder; the camera a starting guess (CAMERA)
    start_objects(folder, objects)                     the concept's object list taken in
    camera(folder, eye, aim, fov)                      the concept's camera as the agent estimates it
    put(folder, name, address, at, turn, scale, ground, wear, clip, second)
                                                       a library entry fetched and laid (again) under Objects: a
                                                       glTF-only entry converted once (gltf.py), a character dressed
                                                       and held in a pose of its clip, a ground marked as the ground
    dome(folder, name, radius, at, ...)                the dome shell algorithm (dome_shell.py) laid: glass shell, curved ribs
    tube(folder, name, radius, length, at, turn, ...)  the dome shell algorithm's ribbed glass tunnel laid
    stairs(folder, name, storeys, at, turn)            the stair core algorithm (stair_core.py) laid: a walkable
                                                       switchback stairwell, its doorways answered
    camera_cut(folder, name)                           an object the camera sees through (place.json `cut`), at
                                                       render only: the building stays closed
    backdrop(folder, name)                             a concept's surroundings a neighbour place of the area stands
                                                       for (place.json `backdrop`): left out of the seated package
    hollow(folder, name, regions)                      a blocks object re-laid without what stands in the regions,
                                                       where the area seats a neighbour place (its fittings there too)
    kind(folder, kind)                                 inside (built closed) or outside (under the sky: only its
                                                       structures' rooms are judged closed), place.json `kind`
    terrain(folder, name, address, at, turn, pads)     a library terrain (relief.py) laid as the ground, its pads levelled
    blocks(folder, name, boxes, at, turn, ground)      solid chamfered boxes (dome_shell.blocks_file) as one object: a
                                                       road and kerbed pavements (ground) or a building (structure)
    snap(folder, name, grid)                           a kit piece's spot onto the grid, its turns onto quarter turns
    palette(folder, library, wear, dirt)               the place's one surface library (its scene palette's families
                                                       and tokens, as its props were painted from) taken in
    surface(folder, name, address, colour, part)       a library surface on an object, or on one of its named parts;
                                                       `palette/<variant>` a variant of the place's palette; refused
                                                       over the whole of a model whose own paint has parts
    refinish(folder, name)                             the object re-finished per part from the palette (finished/);
                                                       `put` does it to a model laid in a paint no library surface made
    light(folder, name, address, at, watts, radius, colour)
    sky(folder, address, elevation, heading, strength, colour)
                                                       a library sky laid as the place's own (its dome, its
                                                       ambient light as /<place>/Environment) and its sun
    sky_at(folder, scene | on, latitude, longitude, height, time, turn, exposure)
                                                       an airless body's physical sky from where and when the place
                                                       is (score/stages/light/sky.py on overhead.py): its sun, discs,
                                                       bodies at true size and phase in their library faces, black
    night(folder, ambient, background, exposure, moon, glow)
                                                       a night sky with no picture: the night's physics as the
                                                       Environment's light and exposure, the moon a distant light
    haze(folder, name, centre, size, colour, density, forward, reach)
                                                       a box of haze (tools/usd/scene.py's haze body) the renderer fills
    view(folder, name, eye, aim, fov)                  a named view besides the concept's (render --views)
    remove(folder, name)                               an object or light taken out
    listing(folder)                                    what the scene holds, as the agent reads it
    batch(folder, steps)                               many steps (every one above but start and listing; blocks,
                                                       night and haze only here) in one process: a relayout in seconds

Rendering is render.py, the compare measure.py, the command line __main__.py.
"""
import json
import os
import pathlib
import re
import shutil
import sys

import numpy as np

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, UsdSkel, Vt

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/library"))
import library_files  # noqa: E402

sys.path.insert(0, str(REPO / "tools/props/library"))
import library as surface_library  # noqa: E402  (the ProcFunc surface library's loader, standard library only)

from score import library  # noqa: E402

PALETTE = "palette.json"  # the place's own surface library in its folder (`palette`)

# A new place's camera before the agent estimates the concept's: eye height standing at the origin, looking along -z
# level, 60 degrees across the picture.
CAMERA = {"eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, -1.0], "fov": 60.0}
# The roles of an entry's file that can be laid in a scene, first found wins; a glTF one is converted (gltf.py).
USD_ROLES = ("usd",)
ROOTED_KINDS = ("effect", "model")  # the kinds whose record's `usd.root` names the file to lay
GLTF_ROLES = ("gltf", "web3d")
# A character's body group shown by default (its others made invisible), the first it has: the made body, the suit;
# its far group (a low-detail stand-in) never by default.
WORN = ("made", "suit")
FAR = "far"
CLIP = "standing"  # the clip a laid character is held in by default, at its start
TRACKS = "algorithm/ground_tracks"  # the ground tracks algorithm's library address (its code: ground_tracks.py)
RAIN = "algorithm/rain"  # the rain algorithm's library address (its code: rainfall.py)
DOME = "algorithm/dome_shell"  # the dome shell algorithm's library address (its code: dome_shell.py)
STAIRS = "algorithm/stair_core"  # the stair core algorithm's (stair_core.py)


class Refused(ValueError):
    """A step the scene cannot take (an unknown entry, an entry with no USD, a name it does not hold)."""


def record_of(folder):
    return json.loads((pathlib.Path(folder) / "place.json").read_text())


def write_record(folder, record):
    (pathlib.Path(folder) / "place.json").write_text(json.dumps(record, indent=1))


def scene_path(folder):
    return pathlib.Path(folder) / "scene.usda"


def new_stage(path, place):
    """An empty scene: y up, metres, /<place> with its Objects, Looks and Lights."""
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, f"/{place}")
    stage.SetDefaultPrim(root.GetPrim())
    for part in ("Objects", "Looks", "Lights"):
        UsdGeom.Scope.Define(stage, f"/{place}/{part}")
    saved(stage)


def start(folder, place, concept, objects=None):
    """A new place folder for `place` from its locked concept picture; `objects` the concept's object list
    (concept_objects.objects' answer, a JSON file) when it was split. Refused over a folder that holds a scene."""
    from PIL import Image
    folder = pathlib.Path(folder)
    if scene_path(folder).exists():
        raise Refused(f"{folder} already holds a scene; remove it or pick another folder")
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(concept, folder / "concept.png")
    new_stage(scene_path(folder), place)
    record = {"place": place, "concept": str(pathlib.Path(concept).resolve()), "size": list(Image.open(concept).size),
              "camera": dict(CAMERA), "objects": None}
    write_record(folder, record)
    return start_objects(folder, objects) if objects else record


def start_objects(folder, objects):
    """The concept's object list (a JSON file of concept_objects.objects' answer) taken into the place folder."""
    shutil.copyfile(objects, pathlib.Path(folder) / "objects.json")
    record = record_of(folder)
    record["objects"] = "objects.json"
    write_record(folder, record)
    return record


def camera(folder, eye, aim, fov):
    record = record_of(folder)
    record["camera"] = {"eye": [float(value) for value in eye], "aim": [float(value) for value in aim],
                        "fov": float(fov)}
    write_record(folder, record)
    return record["camera"]


def resolved_address(address, root):
    """`kind/id@version`, the newest version when `address` gives none, a withdrawn entry's replacement (`replaced_by`)
    followed to the end of its chain, so a place laid again takes the replacement (#155). The end may be withdrawn
    with nothing in its place: what lays it (fetch) refuses it then."""
    if "@" not in address:
        kind, entry_id = address.split("/", 1)
        versions = sorted(int(path.name) for path in (pathlib.Path(root) / "entries" / kind / entry_id).glob("*")
                          if path.name.isdigit())
        if not versions:
            raise Refused(f"{address}: the library holds no such entry")
        address = f"{address}@{versions[-1]}"
    try:
        return library.replaced_end(root, address)
    except ValueError as why:
        raise Refused(str(why)) from why


def library_root():
    root = library.root_from_environment() or library_files.default_root()
    if root is None:
        raise Refused("no library: set SCORE_LIB_ROOT or check score_lib out beside score")
    return root


def entry_of(address):
    """The entry record of `kind/id@version`."""
    kind, rest = address.split("/", 1)
    entry_id, version = rest.split("@")
    try:
        return library.entry(library_root(), kind, entry_id, int(version))
    except FileNotFoundError as error:
        raise Refused(f"{address}: the library holds no such entry") from error


def fetch(folder, address):
    """Every file of the library entry copied under the place's assets (so a model's maps lie beside its USD);
    {file name: path in the folder}. A withdrawn entry is refused: the library retired it (the owner, 2026-10-21,
    every old model, kit, character and surface), so nothing laid now comes from it."""
    address = resolved_address(address, library_root())
    record = entry_of(address)
    if record.get("state") == "withdrawn":
        raise Refused(f"{address}: withdrawn from the library; lay an entry it holds")
    return address, record, copied_entry(folder, address, record)


def copied_entry(folder, address, record):
    """Every file of the entry `record` (at `address`) copied under the folder's assets at its library_files.stage_name
    (a file already there kept); {file name: path in the folder}, Refused for a file the library does not hold."""
    copied = {}
    for name in record["files"]:
        reference = library_files.reference(address, name)
        found = library_files.resolve(reference)
        if found is None:
            raise Refused(f"{reference}: the library does not hold this file")
        target = pathlib.Path(folder) / "assets" / library_files.stage_name(reference)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copyfile(found, target)
        copied[name] = target
    return copied


SEARCHED = re.compile(r"^score_lib/(?P<kind>[a-z]+)/(?P<id>[a-z0-9_]+(?:\.[a-z0-9_]+)?)/(?P<version>[1-9][0-9]*)/"
                      r"(?P<file>.+)$")  # a library file as USD's search path found it in the library cache


def localised(folder):
    """Every `score_lib/<kind>/<id>/<version>/<file>` asset path the folder's USD layers name (a place laid while USD
    found the library on its search path, PXR_AR_DEFAULT_SEARCH_PATH) pointed at that file in the folder's assets,
    its entry copied there whole as `fetch` lays one (a withdrawn one too: the place opens as it was kept, and the
    finish check tells it), until no layer names one; the entries copied, sorted (#154: a fetched stairwell's cables
    and doors opened as nothing)."""
    from pxr import UsdUtils
    folder = pathlib.Path(folder)
    entries, done = set(), set()
    while True:
        layers = [path for path in sorted(folder.rglob("*.usd*")) if path.suffix in (".usd", ".usda", ".usdc")
                  and path not in done]
        if not layers:
            return sorted(entries)
        for path in layers:
            done.add(path)
            layer = Sdf.Layer.FindOrOpen(str(path))
            named = {asset for asset in layer.GetCompositionAssetDependencies() if SEARCHED.match(asset)}
            if not named:
                continue
            for asset in sorted(named):
                parts = SEARCHED.match(asset).groupdict()
                address = f"{parts['kind']}/{parts['id']}@{parts['version']}"
                if address not in entries:
                    copied_entry(folder, address, entry_of(address))
                    entries.add(address)
            def local(asset, here=path.parent):
                parts = SEARCHED.match(asset)
                if not parts:
                    return asset
                target = folder / "assets" / asset.split("/", 1)[1]
                relative = os.path.relpath(target, here).replace(os.sep, "/")
                return relative if relative.startswith("../") else f"./{relative}"
            UsdUtils.ModifyAssetPaths(layer, local)
            layer.Save()


def from_library(address, folder):
    """A place entry of the library (`place/<id>@<version>`) laid out as a place_build folder: each of its files at its
    own name in `folder` (scene.usda, place.json, assets/..., package/...), so every step opens it as a placed folder
    (#154: fetched places held score_lib's search paths and were rebuilt by hand). A sublayer of its scene the entry
    does not hold (the films' walkers layer) is dropped and named, and every library file its layers name on USD's
    search path is copied in and pointed at (`localised`). Refused for another kind, a withdrawn entry, a file
    the library does not hold, or a folder that is not empty. {address, files, dropped, entries}."""
    address = resolved_address(address, library_root())
    if not address.startswith("place/"):
        raise Refused(f"{address}: not a place entry")
    record = entry_of(address)
    if record.get("state") == "withdrawn":
        raise Refused(f"{address}: withdrawn from the library")
    folder = pathlib.Path(folder)
    if folder.exists() and any(folder.iterdir()):
        raise Refused(f"{folder}: not empty; lay the place out in a new folder")
    for name in record["files"]:
        reference = library_files.reference(address, name)
        found = library_files.resolve(reference)
        if found is None:
            raise Refused(f"{reference}: the library does not hold this file")
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(found, target)
    layer = Sdf.Layer.FindOrOpen(str(scene_path(folder)))
    dropped = [path for path in layer.subLayerPaths if not (folder / path).is_file()]
    if dropped:
        layer.subLayerPaths[:] = [path for path in layer.subLayerPaths if path not in dropped]
        layer.Save()
    entries = localised(folder)
    return {"address": address, "files": len(record["files"]), "dropped": dropped, "entries": entries}


def finished_first(name):
    """A glTF's rank among an entry's models: a take's finished model (`-final`, its bake and paint) first, then a
    made model's full one, then the rest by name (a take's raw model and its reduced ones last)."""
    stem = pathlib.Path(name).stem
    return (not stem.endswith("-final"), stem != "full", name)


def usd_file(record, copied):
    """The entry's USD file to lay (an effect's the emitter file its record's `usd` names, not the clip it plays; a
    model's its root too, an adopted model's base file and not a payload beside it; a glTF-only entry's converted once
    beside it, gltf.py), or Refused naming what it holds instead."""
    root = (record.get("usd") or {}).get("root")
    if record["kind"] in ROOTED_KINDS and root in copied:
        return copied[root]
    for role in USD_ROLES:
        for name, info in record["files"].items():
            if info.get("role") == role:
                return copied[name]
    models = [name for name, info in record["files"].items()
              if info.get("role") in GLTF_ROLES and pathlib.Path(name).suffix in (".glb", ".gltf")]
    if models:
        from score.stages.place_build import gltf
        return gltf.converted(copied[min(models, key=finished_first)])
    roles = sorted({info.get("role") for info in record["files"].values()})
    raise Refused(f"{record['address']}: no USD file to lay (its files are {', '.join(roles)})")


HELD = {}  # {scene path: its open stage} while a batch runs, so its steps compose the scene once


def saved(stage):
    """The scene written to its file, unless a batch holds it open (the batch writes it once at its end: saving a
    stage of a thousand objects after each of a thousand steps took minutes)."""
    if stage.GetRootLayer().realPath not in HELD:
        stage.GetRootLayer().Save()


def opened(folder):
    path = str(scene_path(folder).resolve())
    stage = HELD.get(path) or Usd.Stage.Open(path)
    return stage, stage.GetDefaultPrim().GetName()


def posed(prim, at, turn, scale):
    """The prim's transform set to translate `at`, rotateXYZ `turn` (degrees) and `scale`, in that order of ops."""
    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(*at))
    xform.AddRotateXYZOp().Set(Gf.Vec3f(*turn))
    xform.AddScaleOp().Set(Gf.Vec3f(*scale))


def put(folder, name, address, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0), ground=False,
        wear=None, clip=None, second=0.0, rest=False, on_ground=False, role=None, support=None):
    """The library entry laid as Objects/<name> (laid again when the name is taken: its reference and pose
    replaced, its surface kept); the scene saved. `ground` marks it as the place's ground (the renderer then lays no
    plane of its own); a character wears `wear` (its body groups, WORN's first by default) and is held still in its
    clip `clip` (CLIP by default) `second` seconds in; `rest` lifts or lowers it so its lowest point lies at `at`'s
    height (a model whose origin is not at its foot stands on the floor or table it is put on); `on_ground` takes
    `at`'s height as above the laid ground under it (a rock on a real terrain's relief, sunk in by a negative one);
    `role` and `support` are written as its `score:role` and `score:support` (a window laid flush on its building's
    wall: role "mount", support "wall:<building>"), which the physics check (ready/) reads. An effect entry (a smoke's
    emitter) is laid as Effects/<name>, role "effect": no solid, as the rain is."""
    address, record, copied = fetch(folder, address)
    asset = usd_file(record, copied)
    stage, place = opened(folder)
    path = f"/{place}/Objects/{name}"
    if record["kind"] == "effect":
        UsdGeom.Scope.Define(stage, f"/{place}/Effects")
        path, role = f"/{place}/Effects/{name}", "effect"
    if on_ground:
        at = [float(at[0]), float(at[1]) + ground_height(stage, place, at[0], at[2]), float(at[2])]
    relative = laid_reference(stage, path, folder, asset, address, record["kind"], (at, turn, scale), ground)
    laid = {"name": name, "address": address, "usd": relative}
    layers = layered(stage, path, folder, asset, record, copied)
    if layers:
        laid["layers"] = layers
    if record["kind"] == "character":
        laid.update(dressed(stage, path, asset, wear, clip, second))
    if rest:
        laid["at"] = rested(stage, path, at, turn, scale)
    marked(stage.GetPrimAtPath(path), role, support)
    saved(stage)
    finish = own_paint_finished(folder, stage, place, name) if record["kind"] != "effect" else None
    if finish:
        laid["finish"] = finish
    return laid


def own_paint_finished(folder, stage, place, name):
    """A laid model made from a picture (a take, a Pixal3D or TRELLIS.2 model) whose own paint no library surface
    painted, re-finished per part from the place's palette (finished.refinish) while it wears no look and the place
    has its palette: never laid wearing a picture's paint. The re-finish's answer, or None."""
    from score.stages.place_build import finished
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    record = finished.record_of(prim)
    if (not (pathlib.Path(folder) / PALETTE).exists() or prim.GetAttribute("score:surface").HasAuthoredValue()
            or finished.part_looks(stage, place, prim) or not finished.picture_made(record)
            or finished.library_painted(prim, record)):
        return None
    asset = finished.model_file(prim)
    if asset is None or not asset.exists() or not finished.paint(asset).parts:
        return None
    return finished.refinish(folder, name)


def marked(prim, role=None, support=None):
    """The object's role and support written as `score:role` and `score:support` when given."""
    for key, value in (("role", role), ("support", support)):
        if value:
            prim.CreateAttribute(f"score:{key}", Sdf.ValueTypeNames.String).Set(str(value))


def layered(stage, path, folder, asset, record, copied):
    """A model's own extra layers beside its USD (`<its file>_<layer>.usd*` in its folder: a monitor's lit screen,
    `_glow`) laid with it as its children <path>/<layer>, so a screen the model was made with glows where it was made
    (an adopted model's payloads, in a folder below its root, are its root's to compose, never a layer); the layers
    laid, by name."""
    stem, beside = pathlib.Path(asset).stem, pathlib.Path(asset).parent
    found = {}
    for name, info in record["files"].items():
        own = pathlib.Path(name)
        if (info.get("role") in USD_ROLES and own.stem.startswith(stem + "_") and copied[name] != asset
                and pathlib.Path(copied[name]).parent == beside):
            layer = own.stem[len(stem) + 1:]
            child = stage.DefinePrim(f"{path}/{layer}")
            child.GetReferences().ClearReferences()
            child.GetReferences().AddReference(
                "./" + pathlib.Path(copied[name]).resolve().relative_to(pathlib.Path(folder).resolve()).as_posix())
            child.CreateAttribute("score:layered_from", Sdf.ValueTypeNames.String).Set(name)
            found[layer] = name
    return found


GROUND_POINTS = {}  # {(scene path, its grounds and their poses): their points and triangles in the scene} in a batch


def ground_points(stage, place):
    """Every point of the laid ground (each object marked score:ground) in the scene's frame and its triangles (rows
    of three point numbers); read once a batch for the same grounds where they lie."""
    grounds = [prim for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren()
               if prim.GetAttribute("score:ground").Get()]
    key = (stage.GetRootLayer().realPath, tuple((str(prim.GetPath()), str(prim.GetMetadata("references")),
                                                 str(pose_of(prim))) for prim in grounds))  # the references' items,
    # never the References handle's repr (its address changes, so every rock read the ground again and kept it)
    if key in GROUND_POINTS:
        return GROUND_POINTS[key]
    points, triangles, count = [], [], 0
    for prim in grounds:
        for inside in Usd.PrimRange(prim):
            if inside.IsA(UsdGeom.Mesh):
                mesh = UsdGeom.Mesh(inside)
                own = np.array(mesh.GetPointsAttr().Get(), dtype=np.float64)
                matrix = np.array(UsdGeom.Xformable(inside).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
                points.append(own @ matrix[:3, :3] + matrix[3, :3])
                sizes = np.array(mesh.GetFaceVertexCountsAttr().Get() or [], dtype=np.int64)
                indices = np.array(mesh.GetFaceVertexIndicesAttr().Get() or [], dtype=np.int64)
                starts = np.concatenate([[0], np.cumsum(sizes)[:-1]]) if len(sizes) else sizes
                for corner in range(1, int(sizes.max()) - 1 if len(sizes) else 0):  # each face fanned from its first
                    has = sizes > corner + 1
                    triangles.append(np.stack([indices[starts[has]], indices[starts[has] + corner],
                                               indices[starts[has] + corner + 1]], axis=1) + count)
                count += len(own)
    if not points:
        raise Refused("no ground is laid to stand on")
    found = (np.concatenate(points), np.concatenate(triangles) if triangles else np.zeros((0, 3), dtype=np.int64))
    if stage.GetRootLayer().realPath in HELD:
        GROUND_POINTS[key] = found
    return found


NEAREST = 12  # the ground's points nearest a spot whose triangles are searched for the one under it


def ground_height(stage, place, x, z):
    """The height of the laid ground (every object marked score:ground) at (x, z): its highest face over that spot,
    found among the faces of the points within reach and read off that face's plane (the nearest points' weighted
    height where no face lies over it); Refused when nothing laid lies under."""
    points, triangles = ground_points(stage, place)
    distance = np.hypot(points[:, 0] - x, points[:, 2] - z)
    nearest = np.argsort(distance)[:NEAREST]
    if distance[nearest[0]] > 50.0:
        raise Refused(f"no laid ground under {x}, {z}")
    near = triangles[np.isin(triangles, nearest).any(axis=1)]
    heights = []
    for first, second, third in points[near][:, :, [0, 2, 1]]:
        across = (second[1] - third[1]) * (first[0] - third[0]) + (third[0] - second[0]) * (first[1] - third[1])
        if abs(across) < 1e-12:
            continue
        one = ((second[1] - third[1]) * (x - third[0]) + (third[0] - second[0]) * (z - third[1])) / across
        two = ((third[1] - first[1]) * (x - third[0]) + (first[0] - third[0]) * (z - third[1])) / across
        if min(one, two, 1.0 - one - two) >= -1e-9:
            heights.append(one * first[2] + two * second[2] + (1.0 - one - two) * third[2])
    if heights:
        return float(max(heights))
    weights = 1.0 / np.maximum(distance[nearest[:3]], 1e-6)
    return float(np.sum(points[nearest[:3], 1] * weights) / np.sum(weights))


def lowest_of(stage, path):
    """The prim's lowest point's height as drawn: a person's posed skin (its SkelRoot's box is every clip's at once,
    which left a held woman 40 cm over her landing), else its box; None when it has no shape."""
    from score.stages.place_build.ready import people
    body = people.posed_body(stage.GetPrimAtPath(path))
    if body is not None:
        return float(body.mesh.bounds[0][1])
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    box = boxes.ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
    return None if box.IsEmpty() else box.GetMin()[1]


def rested(stage, path, at, turn, scale):
    """The prim at `path` moved up or down so its lowest point lies at at[1]; its new spot."""
    lowest = lowest_of(stage, path)
    if lowest is None:
        raise Refused(f"{path} has no shape to rest")
    spot = [float(at[0]), float(at[1]) + float(at[1]) - lowest, float(at[2])]
    posed(stage.GetPrimAtPath(path), spot, turn, scale)
    return spot


def laid_reference(stage, path, folder, asset, address, kind, pose, ground):
    """The prim at `path` referencing `asset` (a file in the place folder), posed (at, turn, scale) and carrying its
    library address, kind and ground mark; the reference as written."""
    prim = stage.DefinePrim(path)
    prim.SetTypeName("")  # the entry's own type (a character's SkelRoot) composes through, never an Xform over it
    prim.GetReferences().ClearReferences()
    relative = "./" + pathlib.Path(asset).resolve().relative_to(pathlib.Path(folder).resolve()).as_posix()
    prim.GetReferences().AddReference(relative)
    posed(prim, *pose)
    prim.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(address)
    prim.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set(kind)
    prim.CreateAttribute("score:ground", Sdf.ValueTypeNames.Bool).Set(bool(ground))
    return relative


def dome(folder, name, radius, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), meridians=None, rings=None, rib=None,
         address=DOME, openings=(), base=None, oculus=None, strips=()):
    """The dome shell algorithm's dome (dome_shell.py) of `radius` metres laid as Objects/<name>: its file written once
    under the place's assets for its sizes and `openings` ([around degrees, radius, centre height] in its own frame,
    where a tunnel or airlock joins it), its parts `shell`, `ribs`, `deck` and `base` ready for their surfaces;
    `base` [high, wide] its plinth's section, `oculus` its crown ring's radius, `strips` the heights of its light
    strips (part `strip`)."""
    from score.stages.place_build import dome_shell
    sizes = {"meridians": meridians or dome_shell.MERIDIANS, "rings": dome_shell.RINGS if rings is None else rings,
             "rib": rib or dome_shell.RIB}
    if radius <= 0 or sizes["meridians"] < 3 or sizes["rings"] < 0 or sizes["rib"] <= 0:
        raise Refused(f"a dome needs a radius over 0, 3 or more meridians, 0 or more rings and a rib over 0 ({radius}, "
                      f"{sizes})")
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / (
        f"r{radius:g}_m{sizes['meridians']}_r{sizes['rings']}_w{sizes['rib']:g}"
        + "".join(f"_o{around:g},{hole:g},{centre:g}" for around, hole, centre in openings)
        + (f"_b{base[0]:g},{base[1]:g}" if base else "") + (f"_k{oculus:g}" if oculus else "")
        + ("_s" + ",".join(f"{height:g}" for height in strips) if strips else "") + ".usda")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        made = {"base_high": float(base[0]), "base_wide": float(base[1])} if base else {}
        dome_shell.shell(target, float(radius), openings=openings, oculus=float(oculus or 0.0),
                         strip_heights=[float(height) for height in strips], **made, **sizes)
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/{name}", folder, target, address, "algorithm",
                              (at, turn, (1.0, 1.0, 1.0)), False)
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "radius": radius, **sizes}


def rain(folder, name, low, high, height, density, seed=0, address=RAIN):
    """The rain algorithm's rain (rainfall.py) over the box from `low` to `high` ([x, z] metres on the ground) up to
    `height`, `density` streaks a cubic metre, laid as Effects/<name> (an effect: no solid, so neither the check's
    settle nor a walker's route reads it); its file written once under the place's assets for its sizes. A `surface`
    gives it its look like any object's. Each drop lands on the place's highest solid under the rain's top at its spot
    (`surface_under` of ready.solids: a pavement, a step, an awning), its splash there."""
    from score.stages.place_build import rainfall
    from score.stages.place_build import ready
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / (
        f"x{low[0]:g},{high[0]:g}_z{low[1]:g},{high[1]:g}_h{height:g}_d{density:g}_s{seed}_m{rainfall.MADE}.usdc")
    target.parent.mkdir(parents=True, exist_ok=True)
    counts = None
    if not target.exists():
        try:
            counts = rainfall.rain_file(target, low, high, float(height), float(density), seed=int(seed),
                                        ground=surface_under(ready.solids(folder), float(height)))
        except ValueError as why:
            raise Refused(str(why)) from why
    stage, place = opened(folder)
    UsdGeom.Scope.Define(stage, f"/{place}/Effects")
    relative = laid_reference(stage, f"/{place}/Effects/{name}", folder, target, address, "effect",
                              ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), False)
    stage.GetPrimAtPath(f"/{place}/Effects/{name}").CreateAttribute(
        "score:role", Sdf.ValueTypeNames.String).Set("effect")
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "counts": counts}


def surface_under(solids, top):
    """The highest face of `solids` ({name: triangles n x 3 x 3}, the scene's frame) under each spot, as a function of
    arrays of x and z: rays cast down from `top`, nan where none is."""
    import trimesh
    found = [tris for tris in solids.values() if len(tris)]
    if not found:
        return lambda xs, zs: np.full(len(np.asarray(xs)), np.nan)
    corners = np.concatenate(found).reshape(-1, 3)
    mesh = trimesh.Trimesh(corners, np.arange(len(corners)).reshape(-1, 3), process=False)

    def height_at(xs, zs):
        xs, zs = np.asarray(xs, float), np.asarray(zs, float)
        starts = np.column_stack([xs, np.full(len(xs), top), zs])
        hits, rays, _ = mesh.ray.intersects_location(starts, np.tile([0.0, -1.0, 0.0], (len(xs), 1)),
                                                     multiple_hits=False)
        heights = np.full(len(xs), np.nan)
        heights[rays] = hits[:, 1]
        return heights
    return height_at


def ground_surface(stage, place, lines, margin=3.0):
    """The laid ground's height as a function of arrays of x and z over the box round `lines` (polylines of [x, z]):
    the highest of its faces over each spot, as ground_height reads one, found for a whole route at once by rays cast
    down onto the ground's faces in the box."""
    import trimesh
    points, triangles = ground_points(stage, place)
    spots = np.concatenate([np.asarray(line, float) for line in lines])
    low, high = spots.min(axis=0) - margin, spots.max(axis=0) + margin
    inside = ((points[:, 0] >= low[0]) & (points[:, 0] <= high[0]) & (points[:, 2] >= low[1])
              & (points[:, 2] <= high[1]))
    kept = triangles[inside[triangles].any(axis=1)]
    if not len(kept):
        raise Refused(f"no laid ground under the tracks' box {low.tolist()} to {high.tolist()}")
    ground = trimesh.Trimesh(points, kept, process=False)
    top = float(points[:, 1].max()) + 10.0

    def height_at(xs, zs):
        xs, zs = np.asarray(xs, float), np.asarray(zs, float)
        starts = np.column_stack([xs, np.full(len(xs), top), zs])
        hits, rays, _ = ground.ray.intersects_location(starts, np.tile([0.0, -1.0, 0.0], (len(xs), 1)))
        heights = np.full(len(xs), np.nan)
        np.fmax.at(heights, rays, hits[:, 1])
        if np.isnan(heights).any():
            missing = np.flatnonzero(np.isnan(heights))
            raise Refused(f"no laid ground under {xs[missing[0]]:.2f}, {zs[missing[0]]:.2f}")
        return heights
    return height_at


def tracks(folder, name, rover=(), boots=(), seed=0, address=TRACKS):
    """The ground tracks algorithm's ruts and prints (ground_tracks.py) along `rover` and `boots` polylines ([[x, z],
    ...] each) over the laid ground, laid as Effects/<name> (a decal of relief: no solid, so neither the check's settle
    nor a walker's route reads it); its file written under the place's assets, named by its lines' hash."""
    import hashlib
    from score.stages.place_build import ground_tracks
    stage, place = opened(folder)
    key = hashlib.sha256(json.dumps([rover, boots, seed]).encode()).hexdigest()[:12]
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / f"tracks_{key}.usdc"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        counts = ground_tracks.tracks_file(target, rover, boots, ground_surface(stage, place, list(rover) + list(boots)),
                                           seed=int(seed))
    except ValueError as why:
        raise Refused(str(why)) from why
    UsdGeom.Scope.Define(stage, f"/{place}/Effects")
    relative = laid_reference(stage, f"/{place}/Effects/{name}", folder, target, address, "effect",
                              ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), False)
    stage.GetPrimAtPath(f"/{place}/Effects/{name}").CreateAttribute(
        "score:role", Sdf.ValueTypeNames.String).Set("effect")
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "counts": counts}


def cap_key(cap):
    """A tunnel cap's part of its file's name: `_c<width>,<height>`, or `_o<hash>` of a door's outline points."""
    import hashlib
    if not cap:
        return ""
    if len(cap) == 2 and all(isinstance(value, (int, float)) for value in cap):
        return f"_c{cap[0]:g},{cap[1]:g}"
    return "_o" + hashlib.sha256(json.dumps([[round(float(value), 4) for value in point] for point in cap])
                                 .encode()).hexdigest()[:10]


def door_outline(folder, door, radius, at, turn):
    """A laid door's outline seen along a tunnel laid at `at`, `turn` of `radius`: its points in the tunnel's frame (x
    across its axis, y up from its deck), for its cap's doorway (a round hatch takes a round doorway)."""
    from score.stages.place_build import dome_shell, ready
    stage, place = opened(folder)
    solid = ready.solid_of(object_prim(stage, place, door))
    if solid is None:
        raise Refused(f"{door} has no shape to cut a doorway for")
    frame = (Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(1, 0, 0), float(turn[0])))
             * Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), float(turn[1])))
             * Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 0, 1), float(turn[2])))
             * Gf.Matrix4d().SetTranslate(Gf.Vec3d(*map(float, at))))
    inverse = np.asarray(frame.GetInverse())
    own = np.asarray(solid.vertices) @ inverse[:3, :3] + inverse[3, :3]
    return leaf_outline(own[:, 0], np.maximum(0.0, own[:, 1] - dome_shell.FLOOR * radius))


OUTLINE_BAND = 0.02  # metres of height a door's outline is read across at a time
OUTLINE_SPAN = 0.25  # metres of height a door's edge is the median over, so a hinge's knuckle or a latch is no edge


def leaf_outline(across, up):
    """A door's outline in order round it, from its points (across, up): up its left edge and down its right, each
    OUTLINE_BAND's widest reach that side, held in to the median of its OUTLINE_SPAN where it juts past it, so what
    sticks out of the leaf's edge on a short stretch (a hinge, a latch) does not widen the doorway into a gap beside
    the leaf while its curves (a hatch's rounded foot) are kept."""
    bands = np.floor(up / OUTLINE_BAND).astype(int)
    heights, left, right = [], [], []
    for band in np.unique(bands):
        inside = bands == band
        heights.append(float(up[inside].mean()))
        left.append(float(across[inside].min()))
        right.append(float(across[inside].max()))
    reach = max(1, int(round(OUTLINE_SPAN / OUTLINE_BAND / 2)))
    left, right = np.array(left), np.array(right)
    medians = [np.array([np.median(values[max(0, at - reach):at + reach + 1]) for at in range(len(values))])
               for values in (left, right)]
    held_left, held_right = np.maximum(left, medians[0]), np.minimum(right, medians[1])
    sole = up <= up.min() + 0.005  # the door's very foot: a hatch rounded at its bottom is narrow where it stands
    return ([[float(across[sole].min()), float(up.min())]]
            + [[float(edge), height] for edge, height in zip(held_left, heights)]
            + [[float(left[-1]), float(up.max())], [float(right[-1]), float(up.max())]]
            + [[float(edge), height] for edge, height in reversed(list(zip(held_right, heights)))]
            + [[float(across[sole].max()), float(up.min())]])


def tube(folder, name, radius, length, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), hoops=None, rib=None, address=DOME,
         cap=None, trims=(), cap_door=None):
    """The dome shell algorithm's ribbed glass tunnel (dome_shell.tube) of `radius` and `length` metres laid as
    Objects/<name>, lying along its own +z from `at`; its parts `shell`, `ribs` and `deck` ready for their surfaces,
    and with `cap` ([door width, door height], or the door's outline: door_outline) an end wall `cap` at its far end
    holding a doorway that shape; `cap_door` (a laid door's name) cuts it to that door's own outline instead; `trims`
    ([x, y, z, radius] in its own frame: the domes it joins) end its skin on their glass."""
    from score.stages.place_build import dome_shell
    hoops = dome_shell.HOOPS if hoops is None else hoops
    rib = rib or dome_shell.RIB
    if cap_door:
        cap = np.round(door_outline(folder, cap_door, radius, at, turn), 4).tolist()
    if radius <= 0 or length <= 0 or hoops < 0 or rib <= 0:
        raise Refused(f"a tunnel needs a radius and length over 0, 0 or more hoops and a rib over 0 ({radius}, "
                      f"{length}, {hoops}, {rib})")
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / (
        f"tube_r{radius:g}_l{length:g}_h{hoops}_w{rib:g}" + cap_key(cap)
        + "".join("_t" + ",".join(f"{value:.3f}" for value in trim) for trim in trims) + ".usda")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        dome_shell.tube(target, float(radius), float(length), hoops, rib, cap, trims)
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/{name}", folder, target, address, "algorithm",
                              (at, turn, (1.0, 1.0, 1.0)), False)
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "radius": radius, "length": length, "hoops": hoops}


def stairs(folder, name, storeys=None, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), mirror=False, address=STAIRS,
           curtain=False, cut=False, one_block=False, joined=(), street=False):
    """The stair core algorithm (stair_core.py) laid as Objects/<name>: a switchback stairwell `storeys` storeys tall
    of real size, its file written once under the place's assets; its parts `slab`, `steps`, `wall`, `dado`,
    `balusters` and `handrail` ready for their surfaces (`mirror`: the other hand, x taken as its length less x;
    `curtain`: its front a storey-high curtain wall),
    and its doorways (wall, along from, along to, sill, head in
    its own frame) answered for the doors laid in them (`cut`: its front wall laid as its own object <name>_front
    and listed in place.json `cut`, so the building stays closed and the camera alone cuts it, at render;
    `one_block`: only the flats' block its entrance opens into; `joined`: the storeys whose flat door opens onto a
    place of its own, no hall stub behind it; `street`: a street door in its entrance block's facade, its ground
    floor the lobby). Its doorways are recorded in place.json `doorways` in the scene's frame (`<name>_door<k>`,
    `<name>_street`: sill middle, inward way, width), so a neighbour place joins it at one (area/)."""
    from score.stages.place_build import stair_core
    storeys = stair_core.STOREYS if storeys is None else int(storeys)
    if storeys < 1:
        raise Refused(f"a stair core needs one storey or more ({storeys})")
    joined = sorted({int(storey) for storey in joined})
    if any(not 1 <= storey <= storeys for storey in joined):
        raise Refused(f"a joined storey is one of the core's 1 to {storeys} ({joined})")
    named = (f"core_s{storeys}{'_m' if mirror else ''}{'_c' if curtain else ''}{'_o' if cut else ''}"
             f"{'_1' if one_block else ''}{''.join(f'_j{storey}' for storey in joined)}{'_st' if street else ''}.usda")
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / named
    target.parent.mkdir(parents=True, exist_ok=True)
    doors = rewritten(target, lambda path: stair_core.core(path, storeys, bool(mirror), bool(curtain), bool(cut),
                                                           bool(one_block), joined, bool(street)))
    front = target.with_name(f"front_s{storeys}{'_m' if mirror else ''}{'_c' if curtain else ''}.usda")
    if cut:  # written before the scene is opened, which holds the files it references
        rewritten(front, lambda path: stair_core.front_alone(path, storeys, bool(mirror), bool(curtain)))
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/{name}", folder, target, address, "algorithm",
                              (at, turn, (1.0, 1.0, 1.0)), False)
    if cut:
        laid_reference(stage, f"/{place}/Objects/{name}_front", folder, front, address, "algorithm",
                       (at, turn, (1.0, 1.0, 1.0)), False)
        stage.GetPrimAtPath(f"/{place}/Objects/{name}_front").CreateAttribute(
            "score:role", Sdf.ValueTypeNames.String).Set("structure")  # a wall of the shell, no floor of its own
    saved(stage)
    if cut:
        camera_cut(folder, f"{name}_front")
    laid = laid_doorways(stage.GetPrimAtPath(f"/{place}/Objects/{name}"),
                         stair_core.doorway_spots(storeys, mirror, bool(street)))
    record = record_of(folder)
    record["doorways"] = {**{key: spot for key, spot in (record.get("doorways") or {}).items()
                             if not key.startswith(f"{name}_door") and key != f"{name}_street"},
                          **{f"{name}_{key}": spot for key, spot in laid.items()}}
    write_record(folder, record)
    return {"name": name, "address": address, "usd": relative, "storeys": storeys, "mirror": bool(mirror),
            "curtain": bool(curtain), "cut": bool(cut), "one_block": bool(one_block), "joined": joined,
            "street": bool(street), "doorways": doors}


def rewritten(path, write):
    """`write(path)`'s answer, the file written anew; a layer already open at `path` (a batch's scene laying it, the
    stairwell re-laid with its street door) takes the new file's content, since USD makes no new layer where one is
    open (#154)."""
    path = pathlib.Path(path)
    held = Sdf.Layer.Find(str(path.resolve()))
    if held is None:
        path.unlink(missing_ok=True)
        return write(path)
    fresh = path.with_name(f"new_{path.name}")
    fresh.unlink(missing_ok=True)
    answer = write(fresh)
    held.TransferContent(Sdf.Layer.FindOrOpen(str(fresh.resolve())))
    held.Save()
    fresh.unlink()
    return answer


def laid_doorways(prim, spots):
    """Doorway spots in an object's own frame (`middle`, `inward`) put in the scene's frame by the object's laid
    transform, their sill and head with them; their width as it is."""
    matrix = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    found = {}
    for key, spot in spots.items():
        middle = np.asarray(spot["middle"], float) @ matrix[:3, :3] + matrix[3, :3]
        inward = np.asarray(spot["inward"], float) @ matrix[:3, :3]
        inward = inward / np.linalg.norm(inward)
        found[key] = {**spot, "middle": np.round(middle, 4).tolist(), "inward": np.round(inward, 6).tolist(),
                      "sill": round(float(middle[1]), 4),
                      "head": round(float(middle[1]) + spot["head"] - spot["sill"], 4)}
    return found


def camera_cut(folder, name):
    """The object `name` listed in place.json `cut`: the camera sees through it (the concept's cut-away, at render
    only; owner 2026-11-19: a concept's cut is the camera's, never the building's), while it stands for the walkers,
    the physics check and every game engine as built."""
    stage, place = opened(folder)
    if not stage.GetPrimAtPath(f"/{place}/Objects/{name}"):
        raise Refused(f"the scene holds no object {name} to cut")
    record = record_of(folder)
    record["cut"] = sorted(set(record.get("cut") or []) | {name})
    write_record(folder, record)
    return {"cut": record["cut"]}


def backdrop(folder, name):
    """The object or light `name` listed in place.json `backdrop`: a part of the concept's surroundings that a
    neighbour place of the area stands for (the flat's square, crowd, stage and far blocks: place/square is them in
    the game, 2099's prologue 2026-11-22). The place's own renders draw it; the package of a place the area seats
    leaves it out (its neighbour packages it), and the area's shells check reads it as no shell of the place."""
    stage, place = opened(folder)
    if not any(stage.GetPrimAtPath(f"/{place}/{scope}/{name}") for scope in ("Objects", "Effects", "Lights")):
        raise Refused(f"the scene holds no object or light {name} to leave to a neighbour")
    record = record_of(folder)
    record["backdrop"] = sorted(set(record.get("backdrop") or []) | {name})
    write_record(folder, record)
    return {"backdrop": record["backdrop"]}


KINDS = ("inside", "outside")  # place.json `kind`; a place without one is inside


def kind(folder, kind):
    """Whether the place is an inside, built closed all round, or an outside under the sky, of which only the rooms of
    its structures are closed (ready.open_faults: a street's awnings, arcades and overhangs are no rooms)."""
    if kind not in KINDS:
        raise Refused(f"a place is {' or '.join(KINDS)}, not {kind}")
    record = record_of(folder)
    record["kind"] = kind
    write_record(folder, record)
    return {"kind": kind}


MOVES = ("hinge", "slide")  # how a door opens (score:move): on a hinge at one edge, or slid aside along its face
SIDES = ("inner", "outer")  # an airlock chamber's pressure door (score:side): to the base, or to the outside


def door(folder, name, opens=False, move="hinge", lock=None, side=None, crouch=False):
    """The laid object `name` marked a door (score:role door): the walkers open it (`opens`, score:opens) or it stays
    shut, a solid; it opens by `move` (score:move: on a hinge at one of its edges, or slid aside along its face, a
    sliding balcony door's or a lock's plug door); `lock` names the airlock chamber it is a pressure door of
    (score:lock: any laid object whose solid closes the chamber's air, a blocks-built shell as well as a dome shell's
    tube) and `side` whether it is that chamber's inner door, to the base, or its outer one, to the outside
    (score:side). The scene package lists the chamber with its inner and outer doors and its air, and the door opens to
    its high-pressure side (scene_package.locks_of); `crouch` (score:crouch) a hatch the walkers cross crouching, under
    ready.CROUCH_HEAD and over a sill to ready.CROUCH_KNEE (a crew capsule's side hatch). Marked again, its marks are
    replaced."""
    if move not in MOVES:
        raise Refused(f"a door opens by {' or '.join(MOVES)}, not {move}")
    if (lock is None) != (side is None) or (side is not None and side not in SIDES):
        raise Refused(f"an airlock's door names its chamber and its side ({' or '.join(SIDES)}) together, "
                      f"not lock {lock!r} and side {side!r}")
    stage, place = opened(folder)
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    if not prim:
        raise Refused(f"the scene holds no object {name} to make a door")
    if lock is not None and not stage.GetPrimAtPath(f"/{place}/Objects/{lock}"):
        raise Refused(f"the scene holds no chamber {lock} for the door {name}")
    marks = {"role": "door", "opens": "walkers" if opens else None, "move": move if move != "hinge" else None,
             "lock": lock, "side": side, "crouch": "hatch" if crouch else None}
    for key, value in marks.items():
        held = prim.GetAttribute(f"score:{key}")
        if value is None or (held and held.GetTypeName() != Sdf.ValueTypeNames.String):
            prim.RemoveProperty(f"score:{key}")  # a mark of another type, from a place laid before #148, replaced
        if value is not None:
            prim.CreateAttribute(f"score:{key}", Sdf.ValueTypeNames.String).Set(value)
    saved(stage)
    return {"door": name, **{key: value for key, value in marks.items() if key != "role"}}


def ground(folder, name, radius, at=(0.0, 0.0, 0.0), address=DOME):
    """A flat ground disc of `radius` metres (dome_shell.disc_file) laid as Objects/<name> and marked as the place's
    ground (so the renderer lays no plane of its own); its one part `ground` ready for a surface."""
    from score.stages.place_build import dome_shell
    if radius <= 0:
        raise Refused(f"a ground needs a radius over 0 ({radius})")
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / f"ground_r{radius:g}.usda"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        dome_shell.disc_file(target, float(radius))
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/{name}", folder, target, address, "algorithm",
                              (at, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)), True)
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "radius": radius, "ground": True}


BLOCK_ROLES = ("structure", "prop", "fixed", "mount")  # what a blocks object may be besides the walked ground


def blocks(folder, name, boxes, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), ground=False, address=DOME,
           role="structure", support=None):
    """Solid chamfered boxes (dome_shell.blocks_file: each [x0, y0, z0, x1, y1, z1, part] in its own frame) laid as
    one object Objects/<name>: a road and its kerbed pavements with `ground` (the place's walked ground), else of
    `role` (`score:role`, BLOCK_ROLES: a structure, a building's walls or a step, by default; a small fitting built from
    blocks a prop, #154: the capsule's stick; a fitting on a wall a mount with its `support`, wall:<object>, as `put`
    marks one: the stairwell's couplets); each part ready for its surface."""
    if role not in BLOCK_ROLES:
        raise Refused(f"blocks are a {', '.join(BLOCK_ROLES)} or the ground, not {role}")
    import hashlib
    from score.stages.place_build import dome_shell
    boxes = [[float(value) for value in box[:6]] + [str(box[6])] for box in boxes]
    if not boxes or any(len(box) != 7 or box[3] <= box[0] or box[4] <= box[1] or box[5] <= box[2] for box in boxes):
        raise Refused(f"blocks need one box or more, each x0, y0, z0, x1, y1, z1, part with x1 > x0, y1 > y0, z1 > z0")
    key = hashlib.sha256(json.dumps(boxes).encode()).hexdigest()[:16]
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / f"blocks_{key}.usda"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        dome_shell.blocks_file(target, boxes)
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/{name}", folder, target, address, "algorithm",
                              (at, turn, (1.0, 1.0, 1.0)), ground)
    marked(stage.GetPrimAtPath(f"/{place}/Objects/{name}"), None if ground else role, None if ground else support)
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "boxes": len(boxes), "ground": bool(ground)}


HOLLOW_LEAST = 0.02  # metres: a box's piece left thinner than this by a hollow is dropped (a sliver, no wall)
FITTING_REACH = 0.5  # metres round a fitting the wall it is mounted on must still stand after a hollow (a rack's wash)


def laid_boxes(stage, prim):
    """A blocks object's boxes as laid ([x0, y0, z0, x1, y1, z1, part], its own frame), read back from its mesh: each
    closed piece's box (a chamfer stays inside it) and the part its faces are in."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    geo = UsdGeom.Mesh(stage.GetPrimAtPath(prim.GetPath().AppendChild("geo")))
    if not geo or not geo.GetPointsAttr().Get():
        raise Refused(f"{prim.GetName()} is no blocks object (no mesh geo of solid boxes)")
    points = np.asarray(geo.GetPointsAttr().Get(), dtype=np.float64)
    counts = np.asarray(geo.GetFaceVertexCountsAttr().Get())
    indices = np.asarray(geo.GetFaceVertexIndicesAttr().Get())
    face_of = np.repeat(np.arange(len(counts)), counts)
    first = indices[np.r_[0, np.cumsum(counts)[:-1]]][face_of]  # each corner joined to its face's first corner
    pieces = connected_components(coo_matrix((np.ones(len(indices)), (indices, first)),
                                             shape=(len(points),) * 2), directed=False)[1]
    part_of = {}
    for subset in UsdGeom.Subset.GetAllGeomSubsets(geo):
        for face in subset.GetIndicesAttr().Get():
            part_of[int(face)] = subset.GetPrim().GetName()
    boxes = {}
    for face, corner in zip(face_of, indices):
        piece = int(pieces[corner])
        if piece not in boxes:
            boxes[piece] = [points[corner].copy(), points[corner].copy(), part_of.get(int(face), "block")]
        boxes[piece][0] = np.minimum(boxes[piece][0], points[corner])
        boxes[piece][1] = np.maximum(boxes[piece][1], points[corner])
    return [[round(float(value), 4) for value in (*low, *high)] + [part] for low, high, part in boxes.values()]


def box_less(box, region):
    """The pieces of `box` ([x0, y0, z0, x1, y1, z1, part]) outside `region` (x0, y0, z0, x1, y1, z1), each no
    thinner than HOLLOW_LEAST: the box itself when they do not meet."""
    low, high, part = list(box[:3]), list(box[3:6]), box[6]
    if any(region[axis + 3] <= low[axis] or region[axis] >= high[axis] for axis in range(3)):
        return [box]
    pieces = []
    for axis in range(3):
        if region[axis] > low[axis]:
            pieces.append([*low, *high[:axis], region[axis], *high[axis + 1:], part])
            low[axis] = region[axis]
        if region[axis + 3] < high[axis]:
            pieces.append([*low[:axis], region[axis + 3], *low[axis + 1:], *high, part])
            high[axis] = region[axis + 3]
    return [piece for piece in pieces if min(piece[3 + axis] - piece[axis] for axis in range(3)) >= HOLLOW_LEAST]


def boxes_meet(low, high, other_low, other_high):
    return bool(np.all(np.asarray(low) < other_high) and np.all(np.asarray(other_low) < high))


def hollow(folder, name, regions):
    """The blocks object `name` re-laid without what stands in `regions` (each x0, y0, z0, x1, y1, z1 in the scene's
    frame): where the area seats a neighbour place in it (the street's block wall_l1 round the stairwell and the
    flat, 2099's prologue 2026-11-22: the walker stood inside the block). Each of its boxes is cut to its pieces
    outside every region, in its parts and at its pose and role; every other object or light standing wholly in a
    region (a shop's tables, its lamps; a neighbouring block reaching into it stays) and every fitting mounted on it (`support` wall:<name>, or on a fitting taken
    out) that no box left stands within FITTING_REACH of is taken out, a door leaf never (a join's leaf stays), nor
    the place's backdrop (place.json `backdrop`: its own renders draw it)."""
    regions = [[float(value) for value in region] for region in regions]
    if not regions or any(len(region) != 6 or any(region[axis + 3] <= region[axis] for axis in range(3))
                          for region in regions):
        raise Refused("a hollow needs one region or more, each x0, y0, z0, x1, y1, z1 with x1 > x0, y1 > y0, z1 > z0")
    stage, place = opened(folder)
    prim = object_prim(stage, place, name)
    world = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    if not np.allclose(np.abs(world[:3, :3]), np.round(np.abs(world[:3, :3]))):
        raise Refused(f"{name} is not laid at quarter turns: its boxes cannot be cut along the scene's axes")
    own = np.linalg.inv(world)
    kept = laid_boxes(stage, prim)
    for region in regions:
        corners = np.array([[x, y, z, 1.0] for x in region[0::3] for y in region[1::3] for z in region[2::3]]) @ own
        local = [*corners[:, :3].min(axis=0), *corners[:, :3].max(axis=0)]
        kept = [piece for box in kept for piece in box_less(box, local)]
    at, turn, _ = pose_of(prim)
    role, support = (prim.GetAttribute(f"score:{key}").Get() if prim.GetAttribute(f"score:{key}") else None
                     for key in ("role", "support"))
    left = [(np.c_[[[x, y, z] for x in box[0::3][:2] for y in box[1::3][:2] for z in box[2::3][:2]], np.ones(8)]
             @ world)[:, :3] for box in kept]
    gone = taken_with(stage, place, name, regions, [(corners.min(axis=0), corners.max(axis=0)) for corners in left],
                      set(record_of(folder).get("backdrop") or []))
    held = prim.GetMetadata("references")
    before = [str(item.assetPath) for item in held.GetAddedOrExplicitItems()] if held else []
    laid = blocks(folder, name, kept, at=at, turn=turn, ground=False, role=role or "structure", support=support)
    for taken in gone:
        remove(folder, taken)
    text = scene_path(folder).read_text()
    for asset in before:  # the old blocks file, unless another object still lays it
        if asset != laid["usd"] and asset not in text:
            (pathlib.Path(folder) / asset).unlink(missing_ok=True)
    return {**laid, "regions": regions, "taken_out": gone}


def taken_with(stage, place, name, regions, left, kept=()):
    """The objects and lights a hollow of `name` takes out (hollow): every one but a door leaf standing wholly in a
    region (a neighbouring block reaching into it stays, to be hollowed in its turn: the street's wall_l2 and wall_l3
    went whole with wall_l1's hollow, 2099 #161 2026-11-22), and every fitting mounted on `name` (or on one taken out) that no box `left` (low, high in the scene)
    stands within FITTING_REACH of; never one `kept` (the place's backdrop: its own renders draw it); by name."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    spans = {}
    for scope in ("Objects", "Lights"):
        for prim in stage.GetPrimAtPath(f"/{place}/{scope}").GetChildren():
            box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
            if prim.GetName() != name and prim.GetName() not in kept and not box.IsEmpty():
                spans[prim.GetName()] = (prim, np.asarray(box.GetMin()), np.asarray(box.GetMax()))
    gone = []
    for other, (prim, low, high) in spans.items():
        role = prim.GetAttribute("score:role").Get() if prim.GetAttribute("score:role") else None
        if role != "door" and any(np.all(low >= region[:3]) and np.all(high <= region[3:]) for region in regions):
            gone.append(other)
    more = True
    while more:
        more = False
        for other, (prim, low, high) in spans.items():
            mounted = prim.GetAttribute("score:support").Get() if prim.GetAttribute("score:support") else None
            on = str(mounted or "").split(":", 1)[-1]
            if other in gone or not str(mounted or "").startswith("wall:") or (on != name and on not in gone):
                continue
            if on in gone or not any(boxes_meet(low - FITTING_REACH, high + FITTING_REACH, box_low, box_high)
                                     for box_low, box_high in left):
                gone.append(other)
                more = True
    return gone


def terrain(folder, name, address, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), pads=()):
    """A library terrain (a heightfield model, relief.py) laid as Objects/<name> and marked as the place's ground,
    with each pad (x, z, radius in the scene's frame) levelled to the laid height and eased into the ground round
    it, as a building's site is graded: its padded copy written once under the place's assets."""
    import hashlib
    from score.stages.place_build import relief
    address, record, copied = fetch(folder, address)
    source = usd_file(record, copied)
    pads = [tuple(float(value) for value in pad) for pad in pads]
    if any(len(pad) != 3 or pad[2] <= 0 for pad in pads):
        raise Refused(f"a pad is x, z and a radius over 0 ({pads})")
    own = relief.turned_pads(pads, at, float(turn[1])) if pads else []
    key = hashlib.sha256(json.dumps([address, [list(pad) for pad in own]]).encode()).hexdigest()[:12]
    target = pathlib.Path(source).with_name(f"padded_{key}.usdc")
    if not target.exists():
        relief.padded_file(source, target, own)
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/{name}", folder, target, address, record["kind"],
                              (at, turn, (1.0, 1.0, 1.0)), True)
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "pads": pads, "ground": True}


def dressed(stage, path, asset, wear=None, clip=None, second=0.0):
    """A laid character's body groups `wear` shown (WORN's first it has by default) and every other made invisible,
    its skeleton held still in `clip` `second` seconds in (tools/characters/cast.py's own steps)."""
    sys.path.insert(0, str(REPO / "tools/characters"))
    import cast
    groups, clips = cast.asset_facts(asset)
    worn = list(wear) if wear else [next((group for group in WORN if group in groups),
                                         next((group for group in groups if group != FAR), None))]
    unknown = sorted(set(worn) - set(groups))
    if unknown or not worn[0]:
        raise Refused(f"{path}: no body group {', '.join(map(str, unknown))} (it has {', '.join(groups)})")
    cast.dressed(stage, path, groups, worn)
    if not clips:  # a body with no clips stands in its rest pose
        return {"wear": worn, "clip": None, "second": 0.0}
    clip = clip or (CLIP if CLIP in clips else sorted(clips)[0])
    if clip not in clips:
        raise Refused(f"{path}: no clip {clip} (it has {', '.join(sorted(clips))})")
    cast.held_still(stage, path, asset, clip, second)
    return {"wear": worn, "clip": clip, "second": second}


POSE = "pose.json"  # a pose entry's record (tools/props/smoke_beat/hold/hold.py writes one)


def hold(folder, name, address, prop=None):
    """The laid character `name`'s joints set to a library pose (a character entry holding POSE: local rotations
    over the clip the character is held still in, solved on its `clip` at its `second`), its Skeleton's held pose
    marked `score:pose` with the pose's address; with `prop`, that laid object (the cigarette) set at the pose's
    `hold` frame of its joint as posed. The scene saved; {name, pose, joints, prop}."""
    address, record, copied = fetch(folder, address)
    if POSE not in copied:
        raise Refused(f"{address}: no {POSE} (a pose entry holds its joints' rotations there)")
    pose = json.loads(pathlib.Path(copied[POSE]).read_text())
    stage, place = opened(folder)
    path = f"/{place}/Objects/{name}"
    held = UsdSkel.Animation(stage.GetPrimAtPath(f"{path}/Held"))
    if not held:
        raise Refused(f"{name}: no character held still to pose (put a character entry first)")
    joints = [str(joint) for joint in held.GetJointsAttr().Get()]
    rotations = list(held.GetRotationsAttr().Get())
    for joint, about in sorted(pose["joints"].items()):
        if joint not in joints:
            raise Refused(f"{name}: its skeleton has no joint {joint}")
        rotations[joints.index(joint)] = Gf.Quatf(*about["rotation"])
    held.GetRotationsAttr().Set(Vt.QuatfArray(rotations))
    held.GetPrim().CreateAttribute("score:pose", Sdf.ValueTypeNames.String).Set(address)
    laid = {"name": name, "pose": address, "joints": sorted(pose["joints"])}
    if prop:
        laid["prop"] = held_prop(stage, place, path, pose["hold"], prop)
    saved(stage)
    return laid


def held_joint(skeleton, held, name):
    """The joint `name`'s transform in its skeleton's space as the held pose `held` (a SkelAnimation without time
    samples) sets it: each joint's local from the pose (its rest where the pose names it not) times its parent's."""
    order = [str(joint) for joint in skeleton.GetJointsAttr().Get()]
    if name not in order:
        raise Refused(f"{skeleton.GetPath()}: no joint {name}")
    rest = dict(zip(order, skeleton.GetRestTransformsAttr().Get() or [Gf.Matrix4d(1)] * len(order)))
    posed = dict(zip([str(joint) for joint in held.GetJointsAttr().Get()],
                     zip(held.GetTranslationsAttr().Get(), held.GetRotationsAttr().Get(),
                         held.GetScalesAttr().Get())))
    found = Gf.Matrix4d(1)
    for depth in range(name.count("/") + 1):
        joint = "/".join(name.split("/")[:depth + 1])
        if joint in posed:
            place, turn, size = posed[joint]
            local = (Gf.Matrix4d().SetScale(Gf.Vec3d(size)) * Gf.Matrix4d(Gf.Rotation(Gf.Quatd(turn)), Gf.Vec3d(0))
                     * Gf.Matrix4d().SetTranslate(Gf.Vec3d(place)))
        else:
            local = rest[joint]
        found = local * found
    return found


def held_prop(stage, place, path, frame, prop):
    """The laid object `prop` posed at `frame` ({joint, translate, rotation [w, x, y, z]}, in that joint's own frame)
    of the character at `path` as its skeleton is posed; its (at, turn)."""
    skeleton = UsdSkel.Skeleton(stage.GetPrimAtPath(f"{path}/Turned/Skeleton"))
    joint = held_joint(skeleton, UsdSkel.Animation(stage.GetPrimAtPath(f"{path}/Held")), frame["joint"])
    held = Gf.Matrix4d(Gf.Rotation(Gf.Quatd(*frame["rotation"])), Gf.Vec3d(*frame["translate"]))
    target = object_prim(stage, place, prop)
    parent = UsdGeom.Xformable(target.GetParent()).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    skeleton_world = UsdGeom.Xformable(skeleton.GetPrim()).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
    local = held * Gf.Matrix4d(joint) * skeleton_world * parent.GetInverse()
    turn = local.ExtractRotation().Decompose(Gf.Vec3d.ZAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.XAxis())
    at, turn = list(local.ExtractTranslation()), list(turn)[::-1]  # rotateXYZ's angles, X first
    posed(target, at, turn, pose_of(target)[2])
    return {"name": prop, "at": at, "turn": turn}


def object_prim(stage, place, name):
    """The laid object `name`: under Objects, else an effect under Effects (the rain)."""
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}") or stage.GetPrimAtPath(f"/{place}/Effects/{name}")
    if not prim:
        raise Refused(f"the scene holds no object {name}")
    return prim


def pose_of(prim):
    """(at, turn, scale) of a prim posed by `posed`."""
    values = {op.GetOpName(): op.Get() for op in UsdGeom.Xformable(prim).GetOrderedXformOps()}
    return (list(values.get("xformOp:translate", (0, 0, 0))), list(values.get("xformOp:rotateXYZ", (0, 0, 0))),
            list(values.get("xformOp:scale", (1, 1, 1))))


def on_grid(value, grid):
    return round(round(value / grid) * grid, 6)


def snap(folder, name, grid=0.5):
    """The object's spot moved onto the nearest point of a `grid` metres square grid on the ground (x and z; its
    height kept) and each turn onto the nearest quarter turn, as modular kit pieces meet edge to edge."""
    stage, place = opened(folder)
    prim = object_prim(stage, place, name)
    at, turn, scale = pose_of(prim)
    at = [on_grid(at[0], grid), at[1], on_grid(at[2], grid)]
    turn = [on_grid(value, 90.0) for value in turn]
    posed(prim, at, turn, scale)
    saved(stage)
    return {"name": name, "at": at, "turn": turn}


def colour_of(text):
    """'#rrggbb' as linear RGB (a look's diffuse colour is linear)."""
    text = text.lstrip("#")
    if len(text) != 6:
        raise Refused(f"#{text}: a colour is #rrggbb")
    srgb = [int(text[index:index + 2], 16) / 255.0 for index in (0, 2, 4)]
    return [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in srgb]


def look_shader(stage, path, copied, colour):
    """The look's shader at `path`: the variant's own (its material.usda referenced, its colour replaced by `colour`
    when one is given), else a UsdPreviewSurface of `colour` and the recipe's roughness and opacity (glass seen
    through), a setting its entry lacks taken from the method's (data/library/materials.json), as palette_spec does
    (a recipe has no colour of its own, so it needs one)."""
    look = UsdShade.Material.Define(stage, path)
    look.GetPrim().GetReferences().ClearReferences()  # a surface laid before (a ground's) composes no more (#154)
    if "material.usda" in copied:
        look.GetPrim().GetReferences().AddReference("./" + copied["material.usda"].resolve().relative_to(
            pathlib.Path(stage.GetRootLayer().realPath).parent).as_posix())
        shader = UsdShade.Shader(stage.GetPrimAtPath(f"{path}/surface"))
    else:
        if colour is None:
            raise Refused("a recipe surface has no colour of its own: give --colour #rrggbb")
        shader = UsdShade.Shader.Define(stage, f"{path}/surface")
        shader.CreateIdAttr("UsdPreviewSurface")
        own = json.loads(copied["surface.json"].read_text())
        method = json.loads((REPO / "data/library/materials.json").read_text())["recipes"].get(own.get("recipe"), {})
        settings = {**method, **own.get("settings", {})}  # a recipe entry made before glass carried its opacity
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(settings.get("roughness", 0.6)))
        if float(settings.get("opacity", 1.0)) < 1.0:
            shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(settings["opacity"]))
        look.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    if colour is not None:
        tinted(stage, shader, colour)
    return look


def recipe_marked(look, spec):
    """A palette variant's look carries its spec (`score:recipe:spec`, JSON) for the render's recipe pass, and its
    preview its roughness, metal, glow (a glowing recipe's colour given off) and opacity (glass seen through, as the
    preview's thin glass and the scene package's transmission read it); any other look carries none."""
    marked = look.GetPrim().GetAttribute("score:recipe:spec")
    if spec is None:
        if marked:
            look.GetPrim().RemoveProperty("score:recipe:spec")
        return
    look.GetPrim().CreateAttribute("score:recipe:spec", Sdf.ValueTypeNames.String).Set(json.dumps(spec))
    shader = UsdShade.Shader(look.GetPrim().GetStage().GetPrimAtPath(f"{look.GetPath()}/surface"))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(spec.get("roughness", 0.5)))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(spec.get("metal", 0.0)))
    glow = Gf.Vec3f(*spec["colour"]) if spec["recipe"] == "glowing" else Gf.Vec3f(0.0, 0.0, 0.0)
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(glow)
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(float(spec.get("opacity", 1.0)))


def tinted(stage, shader, colour):
    """The look's colour set to `colour`: its diffuse colour, or, when that comes from an image surface's map, the
    map multiplied by it (the texture's scale, which Blender's reader brings in as a multiply), so a scanned ground
    takes the planet's tint and keeps its grain."""
    linear = colour_of(colour)
    source = shader.GetInput("diffuseColor")
    connected = source.GetConnectedSources()[0] if source else []
    if connected:
        texture = UsdShade.Shader(connected[0].source.GetPrim())
        texture.CreateInput("scale", Sdf.ValueTypeNames.Float4).Set(Gf.Vec4f(*linear, 1.0))
        return
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*linear))


def is_layer(prim):
    """Whether the prim is a model's own extra layer laid with it (`layered`)."""
    return bool(prim.GetAttribute("score:layered_from") and prim.GetAttribute("score:layered_from").Get())


def parts_of(prim):
    """{part name: [its GeomSubsets, or its laid layer]} of the object's meshes (a model's named colour regions, and
    its extra layers such as a lit screen)."""
    found = {}
    for inside in Usd.PrimRange(prim):
        if inside.IsA(UsdGeom.Subset) or is_layer(inside):
            found.setdefault(inside.GetName(), []).append(inside)
    return found


def rebind(stage, place, prim):
    """The object's looks bound: its whole look over everything inside it (stronger than anything there, so a model's
    own baked colour never shows) while it has no part looks; with part looks, each part's look on its subsets and the
    whole look (when it has one) on every shape and every other subset, so what no part names still wears it."""
    name = prim.GetName()
    whole = UsdShade.Material(stage.GetPrimAtPath(f"/{place}/Looks/{name}"))
    named = {inside.GetName()[len(name) + 2:]: UsdShade.Material(inside)
             for inside in stage.GetPrimAtPath(f"/{place}/Looks").GetChildren()
             if inside.GetName().startswith(f"{name}__")}
    if not named:
        if whole:
            UsdShade.MaterialBindingAPI.Apply(prim).Bind(whole, UsdShade.Tokens.strongerThanDescendants)
        return
    UsdShade.MaterialBindingAPI.Apply(prim).UnbindDirectBinding()
    for inside in Usd.PrimRange(prim):
        part = inside.GetName() if inside.IsA(UsdGeom.Subset) or is_layer(inside) else None
        if part in named and is_layer(inside):  # a laid layer (a lit screen) wears its look over all it holds
            UsdShade.MaterialBindingAPI.Apply(inside).Bind(named[part], UsdShade.Tokens.strongerThanDescendants)
        elif part in named:
            UsdShade.MaterialBindingAPI.Apply(inside).Bind(named[part])
        elif whole and (part is not None or inside.IsA(UsdGeom.Gprim)):
            UsdShade.MaterialBindingAPI.Apply(inside).Bind(whole)


def palette(folder, library, wear, dirt):
    """The place's one surface library taken in as <folder>/palette.json: a scene's surface-library output (its
    families of ProcFunc recipe variants and its palette tokens, the one its props were painted from), with the
    place's `wear` (0 new .. 1 worn) and `dirt` (0 .. 1), so every surface laid from it shares one palette and wear."""
    taken = json.loads(pathlib.Path(library).read_text())
    if not surface_library.variants(taken) or not taken.get("tokens"):
        raise Refused(f"{library}: no families or tokens (a scene's surface library, not the method's)")
    taken["place_wear"] = {"wear": float(wear), "dirt": float(dirt)}
    (pathlib.Path(folder) / PALETTE).write_text(json.dumps(taken, indent=1))
    return {"palette": str(pathlib.Path(folder) / PALETTE), "variants": len(surface_library.variants(taken)),
            "tokens": len(taken["tokens"]), "wear": float(wear), "dirt": float(dirt)}


def palette_spec(folder, variant):
    """A variant of the place's palette as its recipe wants it (library.spec: the recipe's defaults under the
    variant's settings, a default the place's copy lacks taken from the method's (data/library/materials.json: a
    palette taken before glass carried its opacity still lays see-through glass), its tokens as linear colours, dirt in the palette's dirt token) with the place's wear, dirt and
    its token's colour as '#rrggbb'."""
    path = pathlib.Path(folder) / PALETTE
    if not path.exists():
        raise Refused("no palette: lay the place's surface library first (palette <folder> <materials.json>)")
    taken = json.loads(path.read_text())
    method = json.loads((REPO / "data/library/materials.json").read_text())["recipes"]
    taken["recipes"] = {name: {**method.get(name, {}), **own} for name, own in taken.get("recipes", {}).items()}
    every = surface_library.variants(taken)
    if variant not in every:
        raise Refused(f"palette/{variant}: the place's palette holds no such variant ({', '.join(sorted(every))})")
    token = every[variant]["token"]
    try:
        found = surface_library.spec(taken, variant, token, surface_library.token_colours(taken))
    except surface_library.LibraryEmpty as why:
        raise Refused(str(why)) from why
    return dict(found, hex=taken["tokens"][token], **taken["place_wear"])


def surface(folder, name, address, colour=None, part=None):
    """The library surface `address` worn by the object, bound over everything inside it (so a model's own baked
    colour never shows), or, given `part`, by that named colour region alone (its GeomSubsets): a variant as the
    library makes it, or in the palette colour `colour` ('#rrggbb'; an image surface's map tinted by it); a recipe in
    `colour`. `palette/<variant>` lays a variant of the place's palette (palette_spec): its recipe's library entry in
    its token's colour, the full spec on the look (`score:recipe:spec`) for the render to draw the recipe itself
    (its edge wear, dirt and relief)."""
    spec = None
    if address.startswith("palette/"):
        spec = palette_spec(folder, address.split("/", 1)[1])
        address, colour = f"surface/{spec['recipe']}", spec["hex"]
    address = resolved_address(address, library_root())
    record = entry_of(address)
    if record["kind"] != "surface":
        raise Refused(f"{address} is a {record['kind']}, not a surface")
    _, _, copied = fetch(folder, address)
    stage, place = opened(folder)
    prim = object_prim(stage, place, name)
    if part is None:
        whole_over_parts(prim)
        from score.stages.place_build import finished
        finished.refinish_undone(stage, place, prim)
    if part is not None and part not in parts_of(prim):
        raise Refused(f"{name} has no part {part} (its parts are {', '.join(sorted(parts_of(prim))) or 'none'})")
    look_name = name if part is None else f"{name}__{part}"
    look = look_shader(stage, f"/{place}/Looks/{look_name}", copied, colour)
    look.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(address)
    recipe_marked(look, spec)
    rebind(stage, place, prim)
    if part is None:
        prim.CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(address)
        if colour is not None:
            prim.CreateAttribute("score:surface:colour", Sdf.ValueTypeNames.String).Set(colour)
    saved(stage)
    return {"name": name, "surface": address, "colour": colour, "part": part}


def whole_over_parts(prim):
    """Refused: one surface over the whole of a model whose own paint has several parts (finished.PARTS), which
    would paint every part one flat paint (owner, 2026-11-19: a generator shown as plain clay)."""
    from score.stages.place_build import finished
    asset = finished.model_file(prim)
    if asset is None or not asset.exists() or finished.is_scan(finished.record_of(prim)):
        return
    parts = finished.paint(asset).parts
    if len(parts) >= finished.PARTS:
        raise Refused(f"{prim.GetName()}'s own paint has {len(parts)} parts: one surface over all of it paints them "
                      "one flat paint; `refinish` it (per part from the palette), or lay a surface on one part (--part)")


def light(folder, name, at, watts, radius=0.05, colour="#ffffff", address="light/lamp"):
    """A sphere light laid at `at` as the library's lamp: `watts` its strength, `radius` its bulb."""
    address = resolved_address(address, library_root())
    if entry_of(address)["kind"] != "light":
        raise Refused(f"{address} is not a light")
    stage, place = opened(folder)
    lamp = UsdLux.SphereLight.Define(stage, f"/{place}/Lights/{name}")
    posed(lamp.GetPrim(), at, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
    lamp.CreateIntensityAttr(float(watts))
    lamp.CreateRadiusAttr(float(radius))
    lamp.CreateColorAttr(Gf.Vec3f(*colour_of(colour)))
    lamp.GetPrim().CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(address)
    saved(stage)
    return {"name": name, "light": address, "at": list(at), "watts": watts}


def sun_frame(elevation, heading):
    """The turn of a distant light (UsdLux shines down its own -z) whose light comes from `elevation` degrees over the
    horizon and `heading` degrees round from +x towards +z, as a 4 x 4 matrix."""
    import math
    up, round_ = math.radians(elevation), math.radians(heading)
    towards = Gf.Vec3d(math.cos(up) * math.cos(round_), math.sin(up), math.cos(up) * math.sin(round_))
    across = Gf.Cross(Gf.Vec3d(0.0, 1.0, 0.0), towards).GetNormalized()
    upward = Gf.Cross(towards, across)
    return Gf.Matrix4d(across[0], across[1], across[2], 0.0, upward[0], upward[1], upward[2], 0.0,
                       towards[0], towards[1], towards[2], 0.0, 0.0, 0.0, 0.0, 1.0)


def sky(folder, address, elevation, heading, strength=1.0, colour="#ffffff", turn=0.0, background=None, exposure=None):
    """A library sky (a light entry holding a sky dome and its DomeLight) laid as the place's own sky: its dome under
    Objects/sky, its DomeLight as /<place>/Environment (the ambient light and exposure the renderer takes as the
    stage's sky), and its sun a distant light Lights/sun from `elevation` and `heading` degrees, `strength` its
    intensity, in `colour` ('#rrggbb'); the dome turned `turn` degrees about up, so the glow its picture holds round
    its own sun stands where the sun is laid; `background` ('#rrggbb', a palette token's colour) the sky the camera
    sees in place of the entry's own (a night sky's blue where the entry's is black); `exposure` the camera's
    multiplier in place of the entry's own (a bright day stopped down)."""
    address, record, copied = fetch(folder, address)
    if record["kind"] != "light":
        raise Refused(f"{address} is a {record['kind']}, not a light")
    source = usd_file(record, copied)
    held = Usd.Stage.Open(str(source))  # held while its prims are read
    domes = [prim.GetPath() for prim in held.Traverse() if prim.IsA(UsdLux.DomeLight)]
    if not domes:
        raise Refused(f"{address}: its USD holds no DomeLight (no sky)")
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/sky", folder, source, address, record["kind"],
                              ((0.0, 0.0, 0.0), (0.0, float(turn), 0.0), (1.0, 1.0, 1.0)), False)
    environment = stage.DefinePrim(f"/{place}/Environment", "DomeLight")
    environment.GetReferences().ClearReferences()
    environment.GetReferences().AddReference(relative, domes[0])
    environment.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(address)
    if background is not None:
        environment.CreateAttribute("score:background", Sdf.ValueTypeNames.Color3f).Set(
            Gf.Vec3f(*colour_of(background)))
    if exposure is not None:
        environment.CreateAttribute("score:exposure", Sdf.ValueTypeNames.Float).Set(float(exposure))
    sun = UsdLux.DistantLight.Define(stage, f"/{place}/Lights/sun")
    UsdGeom.Xformable(sun).ClearXformOpOrder()
    UsdGeom.Xformable(sun).AddTransformOp().Set(sun_frame(float(elevation), float(heading)))
    sun.CreateIntensityAttr(float(strength))
    sun.CreateAngleAttr(0.35)  # the sun's width seen from Mars, degrees
    sun.CreateColorAttr(Gf.Vec3f(*colour_of(colour)))
    sun.GetPrim().CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(address)
    saved(stage)
    return {"sky": address, "usd": relative, "sun": {"elevation": elevation, "heading": heading, "strength": strength}}


FACE = "surface/{body}_face"  # a body's face in the library: its face.json as its body-face-<body> row made it
FACE_FILE = "face.json"
# An airless body's sky (the Moon's 3e-13 kPa): no air scatters its sun's light, so the sky the camera sees is black
# and only the backdrops light it. Set between an exosphere's 1e-13 kPa and Pluto's hazy 1e-3 kPa (natural_grounds'
# reference table), far under Mars's 0.636 kPa, whose dust scatters a day dome this step does not lay.
AIRLESS_KPA = 1e-6
SKY_PATHS = ("Sky", "Environment", "Objects/sky", "Lights/sun", "Lights/moon")  # a sky laid before, cleared first


def library_face(body):
    """(the body's face as the library holds it: `surface/<body>_face`'s face.json, its address beside it, or None;
    why none)."""
    try:
        address = resolved_address(FACE.format(body=body), library_root())
    except Refused as why:
        return None, str(why)
    record = entry_of(address)
    if record.get("state") == "withdrawn":
        return None, f"{address}: withdrawn from the library"
    if FACE_FILE not in record["files"]:
        return None, f"{address}: holds no {FACE_FILE}"
    found = library_files.resolve(library_files.reference(address, FACE_FILE))
    if found is None:
        return None, f"{library_files.reference(address, FACE_FILE)}: the library does not hold this file"
    return {**json.loads(pathlib.Path(found).read_text()), "address": address}, None


def sky_site(scene, on, latitude, longitude, height, time):
    """(setting, site, time) of a sky: the scene's kept sky (score/review/scene_sky.py: its top scene's site and scene
    time, the setting it was kept under) when `scene` is named, else the site given on environment 1's setting
    (data/physics/setting.json); a given time over the kept one."""
    from score.review import scene_sky, setting as settings
    if scene is not None:
        path = scene_sky.KEPT / f"{scene}.json"
        if not path.is_file():
            raise Refused(f"{path}: no kept sky for {scene} (python -m score.review.plans keep writes it)")
        kept = json.loads(path.read_text())
        return kept["setting"], kept["site"], time or kept["time"]
    if None in (on, latitude, longitude, time):
        raise Refused("give --scene <kept sky>, or --on <body> --latitude --longitude --time")
    return settings.now(), {"on": on, "latitude": float(latitude), "longitude": float(longitude),
                            "height_m": float(height)}, time


def airless(setting, on):
    """Whether the body a site stands on has no air to scatter its sky (AIRLESS_KPA), by the setting's pressure,
    else the reference table's (data/physics/bodies.json)."""
    from score.review import setting as settings
    from score.stages import natural_grounds
    body, kind = settings.ground_of(setting, on)
    if kind != "body":
        raise Refused(f"{on}: not a body of the setting; sky-at lays a body's sky")
    kpa = natural_grounds.pressure_kpa(body, settings.reference())
    if kpa is None:
        raise Refused(f"{on}: the setting gives no surface pressure, so its air is not known")
    return kpa < AIRLESS_KPA


def turned(seen, turn):
    """What is overhead with every azimuth turned `turn` degrees (the place's frame turned from x east, z south)."""
    def moved(item):
        return {**item, "azimuth": (item["azimuth"] + float(turn)) % 360.0}
    return {**seen, "lights": [moved(light) for light in seen["lights"]],
            "bodies": [moved(body) for body in seen["bodies"]]}


def sky_at(folder, scene=None, on=None, latitude=None, longitude=None, height=0.0, time=None, turn=0.0,
           exposure=None):
    """The place's physical sky from where and when it is (score/stages/light/sky.py's write, the light stage's sky,
    on score/review/overhead.py's answer): each risen light a distant light at its true direction, kelvin and lux,
    a shining body's disc at its true size, every other body a ball at its true direction, size and phase painted
    with its library face (`surface/<body>_face`'s face.json; one the library lacks is laid named missing, never
    grey-painted), the backdrops' domes as /<place>/Environment's ambient light under a black sky (an airless body
    only: one with air is refused), `exposure` the camera's (default: a white face square to the brightest light
    reads 1). The site and time a kept scene's sky (`scene`) or given (`on`, `latitude`, `longitude`, `height`
    metres, `time` ISO); `turn` degrees turns the sky's azimuths onto the place's frame. A sky laid before (SKY_PATHS,
    the sky's own lights) is cleared first."""
    import math
    from score.stages.light import sky as physics_sky
    from score.review import overhead
    setting, site, when = sky_site(scene, on, latitude, longitude, height, time)
    if not airless(setting, site["on"]):
        raise Refused(f"{site['on']} has air: its day sky is a scattered dome, not laid by sky-at")
    seen = overhead.seen(setting, site, when)
    if seen is None:
        raise Refused(f"{site}: its position on {site['on']} is not known")
    seen = turned(seen, turn)
    stage, place = opened(folder)
    lights = stage.GetPrimAtPath(f"/{place}/Lights")
    for path in [f"/{place}/{part}" for part in SKY_PATHS] + [
            str(prim.GetPath()) for prim in (lights.GetChildren() if lights else [])
            if prim.GetName().startswith("sky_")]:
        stage.RemovePrim(path)
    faces, missing = {}, {}
    for body in seen["bodies"]:
        faces[body["body"]], why = library_face(body["body"])
        if why:
            missing[body["body"]] = why
    faces = {body: face for body, face in faces.items() if face}
    library_method = json.loads((REPO / "data/library/materials.json").read_text())
    written = physics_sky.write(stage, place, seen, faces, library_method, None)
    for found in written["bodies"]:
        ball = stage.GetPrimAtPath(found["path"])
        if found["body"] in faces:
            ball.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(faces[found["body"]]["address"])
        else:
            ball.GetAttribute("score:surface:missing").Set(missing[found["body"]])
    risen = overhead.risen(seen)["lights"]
    if exposure is None:
        exposure = math.pi * physics_sky.LUMENS_PER_WATT / risen[0]["lux"] if risen else 1.0
    ambient = sum(backdrop["lux"] for backdrop in seen["backdrops"] if backdrop["shape"] == "dome")
    environment = UsdLux.DomeLight.Define(stage, f"/{place}/Environment")
    environment.CreateIntensityAttr(float(ambient / math.pi / physics_sky.LUMENS_PER_WATT))
    prim = environment.GetPrim()
    prim.CreateAttribute("score:background", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.0, 0.0, 0.0))
    prim.CreateAttribute("score:exposure", Sdf.ValueTypeNames.Float).Set(float(exposure))
    prim.CreateAttribute("score:sky", Sdf.ValueTypeNames.String).Set(
        f"{site['on']} at {site.get('latitude')}, {site.get('longitude')} at {when}: {physics_sky.FROM}")
    made_by_library(stage, place, SKY_ALGORITHM)
    saved(stage)
    return {"site": site, "time": when, "lights": [light["name"] for light in risen],
            "bodies": [found["body"] for found in written["bodies"]], "faces missing": missing,
            "exposure": float(exposure)}


SKY_ALGORITHM = "(sky_orbits.write)"  # the library algorithm holding overhead.py and the light stage's sky
NIGHT_ALGORITHM = "(night_sky.night)"  # the library algorithm holding the night's physics (light/night.py)
GLOWING = "surface/glowing"  # the library's glowing recipe a shining body's disc wears


def made_by_library(stage, place, algorithm):
    """The sky's lights, backdrops, discs and Environment named as built by the library `algorithm` (their score:from
    ending "(<id>.<function>)", as a code-built structure's: complete/library traces them to that entry), and a
    shining body's disc look naming the library's glowing recipe it wears (#154: every Moon and night place failed
    the library check on its sky)."""
    lights = stage.GetPrimAtPath(f"/{place}/Lights")
    prims = [stage.GetPrimAtPath(f"/{place}/Environment")]
    prims += [prim for prim in (lights.GetChildren() if lights else []) if prim.GetName().startswith(("sky_", "moon"))]
    sky_scope = stage.GetPrimAtPath(f"/{place}/Sky")
    prims += list(Usd.PrimRange(sky_scope)) if sky_scope else []
    for prim in prims:
        if not prim or prim.HasAttribute("score:library"):
            continue
        said = str(prim.GetAttribute("score:from").Get() or "") if prim.HasAttribute("score:from") else ""
        prim.CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(
            said if said.endswith(algorithm) else f"{said} {algorithm}".strip())
    looks = stage.GetPrimAtPath(f"/{place}/Looks")
    for look in looks.GetChildren() if looks else []:
        if look.GetAttribute("score:recipe").Get() == "glowing" if look.HasAttribute("score:recipe") else False:
            look.CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(GLOWING)


def night(folder, ambient, background, exposure, moon, glow=None):
    """A night sky with no picture (the night's physics, score/stages/light/night.py, worked out for the place and
    passed in): /<place>/Environment a DomeLight of the moonlit and city-lit air's `ambient` light ([r, g, b], linear),
    the `background` the camera sees ([r, g, b]) and the camera's `exposure` (a multiplier); `moon` {elevation,
    heading, strength, colour [r, g, b], angle} a distant light Lights/moon; `glow` {threshold, intensity} the bloom
    of whatever is brighter than the threshold."""
    stage, place = opened(folder)
    stage.RemovePrim(f"/{place}/Environment")
    environment = UsdLux.DomeLight.Define(stage, f"/{place}/Environment")
    environment.CreateIntensityAttr(1.0)
    environment.CreateColorAttr(Gf.Vec3f(*[float(value) for value in ambient]))
    prim = environment.GetPrim()
    prim.CreateAttribute("score:background", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*[float(value) for value in background]))
    prim.CreateAttribute("score:exposure", Sdf.ValueTypeNames.Float).Set(float(exposure))
    for key, value in (glow or {}).items():
        prim.CreateAttribute(f"score:glow_{key}", Sdf.ValueTypeNames.Float).Set(float(value))
    lamp = UsdLux.DistantLight.Define(stage, f"/{place}/Lights/moon")
    UsdGeom.Xformable(lamp).ClearXformOpOrder()
    UsdGeom.Xformable(lamp).AddTransformOp().Set(sun_frame(float(moon["elevation"]), float(moon["heading"])))
    lamp.CreateIntensityAttr(float(moon["strength"]))
    lamp.CreateAngleAttr(float(moon.get("angle", 0.5)))
    lamp.CreateColorAttr(Gf.Vec3f(*[float(value) for value in moon["colour"]]))
    made_by_library(stage, place, NIGHT_ALGORITHM)
    saved(stage)
    return {"night": {"ambient": list(ambient), "exposure": exposure}, "moon": moon}


def haze(folder, name, centre, size, colour, density, forward=0.0, reach=None):
    """A box of haze (tools/usd/scene.py's haze body: a see-through shell the renderer fills with fog of `colour`,
    `density` its thickness a metre, `forward` its forward throw, only out to `reach` metres from the eye) laid as
    /<place>/Haze/<name>, beside the objects (no body to collide with)."""
    sys.path.insert(0, str(REPO / "tools/usd"))
    import scene as usd_scene
    stage, place = opened(folder)
    entry = {"shape": "box", "centre": [float(value) for value in centre], "size": [float(value) for value in size],
             "colour": colour, "density": float(density), "forward": float(forward)}
    if reach:
        entry["reach"] = float(reach)
    usd_scene.write_haze_volume(stage, f"{place}/Haze/{name}", entry, None)
    made_by_haze(stage, stage.GetPrimAtPath(f"/{place}/Haze/{name}"))
    saved(stage)
    return {"haze": name, "density": density}


HAZE_ALGORITHM = "(sky_dust_stars_haze.haze)"  # the library algorithm holding tools/usd/scene.py's haze body


def made_by_haze(stage, holder):
    """A haze body's prims and the looks bound to them named as made by the library's haze algorithm (score:from
    ending HAZE_ALGORITHM): complete/library traces them to it, as it does a sky (#154: every haze box was found
    twice, its body and its look, with no library entry)."""
    for prim in Usd.PrimRange(holder):
        targets = [prim]
        if prim.IsA(UsdGeom.Gprim):
            bound, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
            targets += [bound.GetPrim()] if bound else []
        for target in targets:
            said = str(target.GetAttribute("score:from").Get() or "") if target.HasAttribute("score:from") else ""
            if not said.endswith(HAZE_ALGORITHM):
                target.CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(f"{said} {HAZE_ALGORITHM}".strip())


def view(folder, name, eye, aim, fov, cut=False):
    """A named view besides the concept's (an inside view at eye height, a low view across the ground), rendered
    with the concept's by `render --views`; `cut`: it sees through place.json `cut` as the concept's view does (a
    named view otherwise sees the building closed)."""
    if name == "concept":
        raise Refused("the concept's own view is set with `camera`")
    record = record_of(folder)
    record.setdefault("views", {})[name] = {"eye": [float(value) for value in eye],
                                            "aim": [float(value) for value in aim], "fov": float(fov)}
    if cut:
        record["views"][name]["cut"] = True
    write_record(folder, record)
    return {name: record["views"][name]}


def remove(folder, name):
    """The object (and its look), effect or light called `name` taken out of the scene, and out of place.json `cut`
    and `backdrop`."""
    stage, place = opened(folder)
    paths = [f"/{place}/{part}/{name}" for part in ("Objects", "Effects", "Looks", "Lights")]
    paths += [str(inside.GetPath()) for inside in stage.GetPrimAtPath(f"/{place}/Looks").GetChildren()
              if inside.GetName().startswith(f"{name}__")]
    found = [path for path in paths if stage.GetPrimAtPath(path)]
    if not found:
        raise Refused(f"the scene holds no object or light {name}")
    for path in found:
        stage.RemovePrim(path)
    saved(stage)
    record = record_of(folder)
    listed_in = [key for key in ("cut", "backdrop") if name in (record.get(key) or [])]
    for key in listed_in:  # a removed object is no longer the camera's to see through, nor a neighbour's
        record[key] = [listed for listed in record[key] if listed != name]
    if listed_in:
        write_record(folder, record)
    return {"removed": name}


def listing(folder):
    """Each object (its address, pose, surface and box in the scene, metres) and light, as the agent reads them."""
    stage, place = opened(folder)
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    looks = {inside.GetName(): inside.GetAttribute("score:surface").Get()
             for inside in stage.GetPrimAtPath(f"/{place}/Looks").GetChildren()}
    objects = []
    for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
        at, turn, scale = pose_of(prim)
        box = boxes.ComputeWorldBound(prim).ComputeAlignedRange()
        objects.append({"name": prim.GetName(), "address": prim.GetAttribute("score:library").Get(),
                        "at": at, "turn": turn, "scale": scale,
                        "surface": prim.GetAttribute("score:surface").Get(),
                        "colour": prim.GetAttribute("score:surface:colour").Get(),
                        "parts": {part: looks.get(f"{prim.GetName()}__{part}") for part in sorted(parts_of(prim))},
                        "box": [[round(value, 3) for value in box.GetMin()],
                                [round(value, 3) for value in box.GetMax()]] if not box.IsEmpty() else None})
    lights = [{"name": prim.GetName(), "at": pose_of(prim)[0],
               "watts": UsdLux.SphereLight(prim).GetIntensityAttr().Get()}
              for prim in stage.GetPrimAtPath(f"/{place}/Lights").GetChildren()]
    return {"place": place, "camera": record_of(folder)["camera"], "objects": objects, "lights": lights}


def refinish(folder, name):
    """The object re-finished per part from the place's palette (finished.refinish)."""
    from score.stages.place_build import finished
    return finished.refinish(folder, name)


STEPS = {"put": put, "palette": palette, "dome": dome, "ground": ground, "terrain": terrain, "tube": tube, "stairs": stairs, "surface": surface, "light": light, "snap": snap, "remove": remove,
         "cut": camera_cut, "backdrop": backdrop, "hollow": hollow, "kind": kind, "door": door,
         "camera": camera, "sky": sky, "sky-at": sky_at, "view": view, "blocks": blocks, "night": night, "haze": haze,
         "refinish": refinish, "hold": hold}



def batch(folder, steps):
    """Many steps in one process, the scene composed once (`steps`: [{"step": <one of STEPS>, its arguments by name}],
    points as lists, a single scale number for all three axes); each step's answer in order, a refused one as
    {"refused": why, "step": its number} while the rest go on."""
    path = str(scene_path(folder).resolve())
    HELD[path] = Usd.Stage.Open(path)
    answers = []
    try:
        for number, given in enumerate(steps):
            given = dict(given)
            step = given.pop("step", None)
            if step not in STEPS:
                answers.append({"refused": f"no step {step!r} (steps are {', '.join(STEPS)})", "step": number})
                continue
            if isinstance(given.get("scale"), (int, float)):
                given["scale"] = [float(given["scale"])] * 3
            try:
                answers.append(STEPS[step](folder, **given))
            except (Refused, TypeError) as why:
                answers.append({"refused": str(why), "step": number})
    finally:
        held = HELD.pop(path)
        held.GetRootLayer().Save()
        GROUND_POINTS.clear()
    return answers
