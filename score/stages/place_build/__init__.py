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
import pathlib
import shutil
import sys

import numpy as np

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade

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
    """`kind/id@version`, the newest version when `address` gives none."""
    if "@" in address:
        return address
    kind, entry_id = address.split("/", 1)
    versions = sorted(int(path.name) for path in (pathlib.Path(root) / "entries" / kind / entry_id).glob("*")
                      if path.name.isdigit())
    if not versions:
        raise Refused(f"{address}: the library holds no such entry")
    return f"{address}@{versions[-1]}"


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
    {file name: path in the folder}."""
    address = resolved_address(address, library_root())
    record = entry_of(address)
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
    return address, record, copied


def finished_first(name):
    """A glTF's rank among an entry's models: a take's finished model (`-final`, its bake and paint) first, then a
    made model's full one, then the rest by name (a take's raw model and its reduced ones last)."""
    stem = pathlib.Path(name).stem
    return (not stem.endswith("-final"), stem != "full", name)


def usd_file(record, copied):
    """The entry's USD file to lay (a glTF-only entry's converted once beside it, gltf.py), or Refused naming what it
    holds instead."""
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
    wall: role "mount", support "wall:<building>"), which the physics check (ready/) reads."""
    address, record, copied = fetch(folder, address)
    asset = usd_file(record, copied)
    stage, place = opened(folder)
    path = f"/{place}/Objects/{name}"
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
    finish = own_paint_finished(folder, stage, place, name)
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
    """A model's own extra layers beside its USD (`<its file>_<layer>.usd*`: a monitor's lit screen, `_glow`) laid
    with it as its children <path>/<layer>, so a screen the model was made with glows where it was made; the layers
    laid, by name."""
    stem = pathlib.Path(asset).stem
    found = {}
    for name, info in record["files"].items():
        own = pathlib.Path(name)
        if info.get("role") in USD_ROLES and own.stem.startswith(stem + "_") and copied[name] != asset:
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
           curtain=False, cut=False, one_block=False, joined=()):
    """The stair core algorithm (stair_core.py) laid as Objects/<name>: a switchback stairwell `storeys` storeys tall
    of real size, its file written once under the place's assets; its parts `slab`, `steps`, `wall`, `dado`,
    `balusters` and `handrail` ready for their surfaces (`mirror`: the other hand, x taken as its length less x;
    `curtain`: its front a storey-high curtain wall),
    and its doorways (wall, along from, along to, sill, head in
    its own frame) answered for the doors laid in them (`cut`: its front wall laid as its own object <name>_front
    and listed in place.json `cut`, so the building stays closed and the camera alone cuts it, at render;
    `one_block`: only the flats' block its entrance opens into; `joined`: the storeys whose flat door opens onto a
    place of its own, no hall stub behind it). Its doorways are recorded in place.json `doorways` in the scene's
    frame (`<name>_door<k>`: sill middle, inward way, width), so a neighbour place joins it at one (area/)."""
    from score.stages.place_build import stair_core
    storeys = stair_core.STOREYS if storeys is None else int(storeys)
    if storeys < 1:
        raise Refused(f"a stair core needs one storey or more ({storeys})")
    joined = sorted({int(storey) for storey in joined})
    if any(not 1 <= storey <= storeys for storey in joined):
        raise Refused(f"a joined storey is one of the core's 1 to {storeys} ({joined})")
    named = (f"core_s{storeys}{'_m' if mirror else ''}{'_c' if curtain else ''}{'_o' if cut else ''}"
             f"{'_1' if one_block else ''}{''.join(f'_j{storey}' for storey in joined)}.usda")
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / named
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    doors = stair_core.core(target, storeys, bool(mirror), bool(curtain), bool(cut), bool(one_block), joined)
    front = target.with_name(f"front_s{storeys}{'_m' if mirror else ''}{'_c' if curtain else ''}.usda")
    if cut:  # written before the scene is opened, which holds the files it references
        front.unlink(missing_ok=True)
        stair_core.front_alone(front, storeys, bool(mirror), bool(curtain))
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
    laid = laid_doorways(stage.GetPrimAtPath(f"/{place}/Objects/{name}"), stair_core.doorway_spots(storeys, mirror))
    record = record_of(folder)
    record["doorways"] = {**{key: spot for key, spot in (record.get("doorways") or {}).items()
                             if not key.startswith(f"{name}_door")},
                          **{f"{name}_{key}": spot for key, spot in laid.items()}}
    write_record(folder, record)
    return {"name": name, "address": address, "usd": relative, "storeys": storeys, "mirror": bool(mirror),
            "curtain": bool(curtain), "cut": bool(cut), "one_block": bool(one_block), "joined": joined,
            "doorways": doors}


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


def door(folder, name, opens=False, move="hinge", lock=None, side=None):
    """The laid object `name` marked a door (score:role door): the walkers open it (`opens`, score:opens) or it stays
    shut, a solid; it opens by `move` (score:move: on a hinge at one of its edges, or slid aside along its face, a
    sliding balcony door's or a lock's plug door); `lock` names the airlock chamber it is a pressure door of
    (score:lock: any laid object whose solid closes the chamber's air, a blocks-built shell as well as a dome shell's
    tube) and `side` whether it is that chamber's inner door, to the base, or its outer one, to the outside
    (score:side). The scene package lists the chamber with its inner and outer doors and its air, and the door opens to
    its high-pressure side (scene_package.locks_of). Marked again, its marks are replaced."""
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
             "lock": lock, "side": side}
    for key, value in marks.items():
        if value is None:
            prim.RemoveProperty(f"score:{key}")
        else:
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


def blocks(folder, name, boxes, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), ground=False, address=DOME):
    """Solid chamfered boxes (dome_shell.blocks_file: each [x0, y0, z0, x1, y1, z1, part] in its own frame) laid as
    one object Objects/<name>: a road and its kerbed pavements with `ground` (the place's walked ground), else a
    structure (`score:role` structure: a building's walls, a step); each part ready for its surface."""
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
    marked(stage.GetPrimAtPath(f"/{place}/Objects/{name}"), None if ground else "structure")
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "boxes": len(boxes), "ground": bool(ground)}


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
    when one is given), else a UsdPreviewSurface of `colour` and the recipe's roughness (a recipe has no colour of
    its own, so it needs one)."""
    look = UsdShade.Material.Define(stage, path)
    if "material.usda" in copied:
        look.GetPrim().GetReferences().ClearReferences()
        look.GetPrim().GetReferences().AddReference("./" + copied["material.usda"].resolve().relative_to(
            pathlib.Path(stage.GetRootLayer().realPath).parent).as_posix())
        shader = UsdShade.Shader(stage.GetPrimAtPath(f"{path}/surface"))
    else:
        if colour is None:
            raise Refused("a recipe surface has no colour of its own: give --colour #rrggbb")
        shader = UsdShade.Shader.Define(stage, f"{path}/surface")
        shader.CreateIdAttr("UsdPreviewSurface")
        settings = json.loads(copied["surface.json"].read_text()).get("settings", {})
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(settings.get("roughness", 0.6)))
        look.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    if colour is not None:
        tinted(stage, shader, colour)
    return look


def recipe_marked(look, spec):
    """A palette variant's look carries its spec (`score:recipe:spec`, JSON) for the render's recipe pass, and its
    preview its roughness, metal and glow (a glowing recipe's colour given off); any other look carries none."""
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
    variant's settings, its tokens as linear colours, dirt in the palette's dirt token) with the place's wear, dirt and
    its token's colour as '#rrggbb'."""
    path = pathlib.Path(folder) / PALETTE
    if not path.exists():
        raise Refused("no palette: lay the place's surface library first (palette <folder> <materials.json>)")
    taken = json.loads(path.read_text())
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
    saved(stage)
    return {"haze": name, "density": density}


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
    """The object (and its look), effect or light called `name` taken out of the scene, and out of place.json `cut`."""
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
    if name in (record.get("cut") or []):  # a removed object is no longer the camera's to see through
        record["cut"] = [listed for listed in record["cut"] if listed != name]
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
         "cut": camera_cut, "kind": kind, "door": door,
         "camera": camera, "sky": sky, "view": view, "blocks": blocks, "night": night, "haze": haze,
         "refinish": refinish}



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
