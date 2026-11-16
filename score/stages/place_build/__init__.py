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
    terrain(folder, name, address, at, turn, pads)     a library terrain (relief.py) laid as the ground, its pads levelled
    snap(folder, name, grid)                           a kit piece's spot onto the grid, its turns onto quarter turns
    surface(folder, name, address, colour, part)       a library surface on an object, or on one of its named parts
    light(folder, name, address, at, watts, radius, colour)
    sky(folder, address, elevation, heading, strength, colour)
                                                       a library sky laid as the place's own (its dome, its
                                                       ambient light as /<place>/Environment) and its sun
    view(folder, name, eye, aim, fov)                  a named view besides the concept's (render --views)
    remove(folder, name)                               an object or light taken out
    listing(folder)                                    what the scene holds, as the agent reads it
    batch(folder, steps)                               many steps (put, surface, light, snap, remove, dome) in one
                                                       process: a whole relayout in seconds

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

from score import library  # noqa: E402

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
DOME = "algorithm/dome_shell"  # the dome shell algorithm's library address (its code: dome_shell.py)


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
        wear=None, clip=None, second=0.0, rest=False, on_ground=False):
    """The library entry laid as Objects/<name> (laid again when the name is taken: its reference and pose
    replaced, its surface kept); the scene saved. `ground` marks it as the place's ground (the renderer then lays no
    plane of its own); a character wears `wear` (its body groups, WORN's first by default) and is held still in its
    clip `clip` (CLIP by default) `second` seconds in; `rest` lifts or lowers it so its lowest point lies at `at`'s
    height (a model whose origin is not at its foot stands on the floor or table it is put on); `on_ground` takes
    `at`'s height as above the laid ground under it (a rock on a real terrain's relief, sunk in by a negative one)."""
    address, record, copied = fetch(folder, address)
    asset = usd_file(record, copied)
    stage, place = opened(folder)
    path = f"/{place}/Objects/{name}"
    if on_ground:
        at = [float(at[0]), float(at[1]) + ground_height(stage, place, at[0], at[2]), float(at[2])]
    relative = laid_reference(stage, path, folder, asset, address, record["kind"], (at, turn, scale), ground)
    laid = {"name": name, "address": address, "usd": relative}
    if record["kind"] == "character":
        laid.update(dressed(stage, path, asset, wear, clip, second))
    if rest:
        laid["at"] = rested(stage, path, at, turn, scale)
    saved(stage)
    return laid


GROUND_POINTS = {}  # {(scene path, its grounds and their poses): their points in the scene} while a batch runs


def ground_points(stage, place):
    """Every point of the laid ground (each object marked score:ground) in the scene's frame; read once a batch for the
    same grounds where they lie."""
    grounds = [prim for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren()
               if prim.GetAttribute("score:ground").Get()]
    key = (stage.GetRootLayer().realPath, tuple((str(prim.GetPath()), str(prim.GetReferences()),
                                                 str(pose_of(prim))) for prim in grounds))
    if key in GROUND_POINTS:
        return GROUND_POINTS[key]
    points = []
    for prim in grounds:
        for inside in Usd.PrimRange(prim):
            if inside.IsA(UsdGeom.Mesh):
                own = np.array(UsdGeom.Mesh(inside).GetPointsAttr().Get(), dtype=np.float64)
                matrix = np.array(UsdGeom.Xformable(inside).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
                points.append(own @ matrix[:3, :3] + matrix[3, :3])
    if not points:
        raise Refused("no ground is laid to stand on")
    points = np.concatenate(points)
    if stage.GetRootLayer().realPath in HELD:
        GROUND_POINTS[key] = points
    return points


def ground_height(stage, place, x, z):
    """The height of the laid ground (every object marked score:ground) at (x, z): its highest face over that spot,
    found among the points within reach and read off the nearest face's plane; Refused when nothing laid lies under."""
    points = ground_points(stage, place)
    distance = np.hypot(points[:, 0] - x, points[:, 2] - z)
    nearest = np.argsort(distance)[:3]
    if distance[nearest[0]] > 50.0:
        raise Refused(f"no laid ground under {x}, {z}")
    weights = 1.0 / np.maximum(distance[nearest], 1e-6)
    return float(np.sum(points[nearest, 1] * weights) / np.sum(weights))


def rested(stage, path, at, turn, scale):
    """The prim at `path` moved up or down so its lowest point lies at at[1]; its new spot."""
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    box = boxes.ComputeWorldBound(stage.GetPrimAtPath(path)).ComputeAlignedRange()
    if box.IsEmpty():
        raise Refused(f"{path} has no shape to rest")
    spot = [float(at[0]), float(at[1]) + float(at[1]) - box.GetMin()[1], float(at[2])]
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
         address=DOME):
    """The dome shell algorithm's dome (dome_shell.py) of `radius` metres laid as Objects/<name>: its file written once
    under the place's assets for its sizes, its parts `shell` and `ribs` ready for their surfaces."""
    from score.stages.place_build import dome_shell
    sizes = {"meridians": meridians or dome_shell.MERIDIANS, "rings": dome_shell.RINGS if rings is None else rings,
             "rib": rib or dome_shell.RIB}
    if radius <= 0 or sizes["meridians"] < 3 or sizes["rings"] < 0 or sizes["rib"] <= 0:
        raise Refused(f"a dome needs a radius over 0, 3 or more meridians, 0 or more rings and a rib over 0 ({radius}, "
                      f"{sizes})")
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / (
        f"r{radius:g}_m{sizes['meridians']}_r{sizes['rings']}_w{sizes['rib']:g}.usda")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        dome_shell.shell(target, float(radius), **sizes)
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/{name}", folder, target, address, "algorithm",
                              (at, turn, (1.0, 1.0, 1.0)), False)
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "radius": radius, **sizes}


def tube(folder, name, radius, length, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), hoops=None, rib=None, address=DOME):
    """The dome shell algorithm's ribbed glass tunnel (dome_shell.tube) of `radius` and `length` metres laid as
    Objects/<name>, lying along its own +z from `at`; its parts `shell`, `ribs` and `deck` ready for their surfaces."""
    from score.stages.place_build import dome_shell
    hoops = dome_shell.HOOPS if hoops is None else hoops
    rib = rib or dome_shell.RIB
    if radius <= 0 or length <= 0 or hoops < 0 or rib <= 0:
        raise Refused(f"a tunnel needs a radius and length over 0, 0 or more hoops and a rib over 0 ({radius}, "
                      f"{length}, {hoops}, {rib})")
    target = pathlib.Path(folder) / "assets" / "algorithm" / address.split("/", 1)[1] / (
        f"tube_r{radius:g}_l{length:g}_h{hoops}_w{rib:g}.usda")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        dome_shell.tube(target, float(radius), float(length), hoops, rib)
    stage, place = opened(folder)
    relative = laid_reference(stage, f"/{place}/Objects/{name}", folder, target, address, "algorithm",
                              (at, turn, (1.0, 1.0, 1.0)), False)
    saved(stage)
    return {"name": name, "address": address, "usd": relative, "radius": radius, "length": length, "hoops": hoops}


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
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
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


def parts_of(prim):
    """{part name: [its GeomSubsets]} of the object's meshes (a model's named colour regions)."""
    found = {}
    for inside in Usd.PrimRange(prim):
        if inside.IsA(UsdGeom.Subset):
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
        part = inside.GetName() if inside.IsA(UsdGeom.Subset) else None
        if part in named:
            UsdShade.MaterialBindingAPI.Apply(inside).Bind(named[part])
        elif whole and (part is not None or inside.IsA(UsdGeom.Gprim)):
            UsdShade.MaterialBindingAPI.Apply(inside).Bind(whole)


def surface(folder, name, address, colour=None, part=None):
    """The library surface `address` worn by the object, bound over everything inside it (so a model's own baked
    colour never shows), or, given `part`, by that named colour region alone (its GeomSubsets): a variant as the
    library makes it, or in the palette colour `colour` ('#rrggbb'; an image surface's map tinted by it); a recipe in
    `colour`."""
    address = resolved_address(address, library_root())
    record = entry_of(address)
    if record["kind"] != "surface":
        raise Refused(f"{address} is a {record['kind']}, not a surface")
    _, _, copied = fetch(folder, address)
    stage, place = opened(folder)
    prim = object_prim(stage, place, name)
    if part is not None and part not in parts_of(prim):
        raise Refused(f"{name} has no part {part} (its parts are {', '.join(sorted(parts_of(prim))) or 'none'})")
    look_name = name if part is None else f"{name}__{part}"
    look = look_shader(stage, f"/{place}/Looks/{look_name}", copied, colour)
    look.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(address)
    rebind(stage, place, prim)
    if part is None:
        prim.CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(address)
        if colour is not None:
            prim.CreateAttribute("score:surface:colour", Sdf.ValueTypeNames.String).Set(colour)
    saved(stage)
    return {"name": name, "surface": address, "colour": colour, "part": part}


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


def sky(folder, address, elevation, heading, strength=1.0, colour="#ffffff", turn=0.0):
    """A library sky (a light entry holding a sky dome and its DomeLight) laid as the place's own sky: its dome under
    Objects/sky, its DomeLight as /<place>/Environment (the ambient light and exposure the renderer takes as the
    stage's sky), and its sun a distant light Lights/sun from `elevation` and `heading` degrees, `strength` its
    intensity, in `colour` ('#rrggbb'); the dome turned `turn` degrees about up, so the glow its picture holds round
    its own sun stands where the sun is laid."""
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
    sun = UsdLux.DistantLight.Define(stage, f"/{place}/Lights/sun")
    UsdGeom.Xformable(sun).ClearXformOpOrder()
    UsdGeom.Xformable(sun).AddTransformOp().Set(sun_frame(float(elevation), float(heading)))
    sun.CreateIntensityAttr(float(strength))
    sun.CreateAngleAttr(0.35)  # the sun's width seen from Mars, degrees
    sun.CreateColorAttr(Gf.Vec3f(*colour_of(colour)))
    sun.GetPrim().CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(address)
    saved(stage)
    return {"sky": address, "usd": relative, "sun": {"elevation": elevation, "heading": heading, "strength": strength}}


def view(folder, name, eye, aim, fov):
    """A named view besides the concept's (an inside view at eye height, a low view across the ground), rendered
    with the concept's by `render --views`."""
    if name == "concept":
        raise Refused("the concept's own view is set with `camera`")
    record = record_of(folder)
    record.setdefault("views", {})[name] = {"eye": [float(value) for value in eye],
                                            "aim": [float(value) for value in aim], "fov": float(fov)}
    write_record(folder, record)
    return {name: record["views"][name]}


def remove(folder, name):
    """The object (and its look) or light called `name` taken out of the scene."""
    stage, place = opened(folder)
    paths = [f"/{place}/{part}/{name}" for part in ("Objects", "Looks", "Lights")]
    paths += [str(inside.GetPath()) for inside in stage.GetPrimAtPath(f"/{place}/Looks").GetChildren()
              if inside.GetName().startswith(f"{name}__")]
    found = [path for path in paths if stage.GetPrimAtPath(path)]
    if not found:
        raise Refused(f"the scene holds no object or light {name}")
    for path in found:
        stage.RemovePrim(path)
    saved(stage)
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


STEPS = {"put": put, "dome": dome, "ground": ground, "terrain": terrain, "tube": tube, "surface": surface, "light": light, "snap": snap, "remove": remove,
         "camera": camera, "sky": sky, "view": view}


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
