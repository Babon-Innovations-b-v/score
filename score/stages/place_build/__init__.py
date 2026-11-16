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
    put(folder, name, address, at, turn, scale)        a library entry fetched and laid (again) under Objects
    snap(folder, name, grid)                           a kit piece's spot onto the grid, its turns onto quarter turns
    surface(folder, name, address, colour=None)        a library surface on an object (a recipe in a palette colour)
    light(folder, name, address, at, watts, radius, colour)
    remove(folder, name)                               an object or light taken out
    listing(folder)                                    what the scene holds, as the agent reads it

Rendering is render.py, the compare measure.py, the command line __main__.py.
"""
import json
import pathlib
import shutil
import sys

from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/library"))
import library_files  # noqa: E402

from score import library  # noqa: E402

# A new place's camera before the agent estimates the concept's: eye height standing at the origin, looking along -z
# level, 60 degrees across the picture.
CAMERA = {"eye": [0.0, 1.6, 0.0], "aim": [0.0, 1.6, -1.0], "fov": 60.0}
# The roles of an entry's file that can be laid in a scene, first found wins.
USD_ROLES = ("usd",)


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
    stage.GetRootLayer().Save()


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


def usd_file(record, copied):
    """The entry's USD file to lay, or Refused naming what it holds instead."""
    for role in USD_ROLES:
        for name, info in record["files"].items():
            if info.get("role") == role:
                return copied[name]
    roles = sorted({info.get("role") for info in record["files"].values()})
    raise Refused(f"{record['address']}: no USD file to lay (its files are {', '.join(roles)})")


def opened(folder):
    stage = Usd.Stage.Open(str(scene_path(folder)))
    return stage, stage.GetDefaultPrim().GetName()


def posed(prim, at, turn, scale):
    """The prim's transform set to translate `at`, rotateXYZ `turn` (degrees) and `scale`, in that order of ops."""
    xform = UsdGeom.Xformable(prim)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(*at))
    xform.AddRotateXYZOp().Set(Gf.Vec3f(*turn))
    xform.AddScaleOp().Set(Gf.Vec3f(*scale))


def put(folder, name, address, at=(0.0, 0.0, 0.0), turn=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    """The library entry laid as Objects/<name> (laid again when the name is taken: its reference and pose
    replaced, its surface kept); the scene saved."""
    address, record, copied = fetch(folder, address)
    asset = usd_file(record, copied)
    stage, place = opened(folder)
    path = f"/{place}/Objects/{name}"
    prim = UsdGeom.Xform.Define(stage, path).GetPrim()
    prim.GetReferences().ClearReferences()
    relative = "./" + asset.resolve().relative_to(pathlib.Path(folder).resolve()).as_posix()
    prim.GetReferences().AddReference(relative)
    posed(prim, at, turn, scale)
    prim.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(address)
    prim.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set(record["kind"])
    stage.GetRootLayer().Save()
    return {"name": name, "address": address, "usd": relative}


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
    stage.GetRootLayer().Save()
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
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*colour_of(colour)))
    return look


def surface(folder, name, address, colour=None):
    """The library surface `address` worn by the object, bound over everything inside it (so a model's own baked
    colour never shows): a variant as the library makes it, or in the palette colour `colour` ('#rrggbb'); a recipe
    in `colour`."""
    address = resolved_address(address, library_root())
    record = entry_of(address)
    if record["kind"] != "surface":
        raise Refused(f"{address} is a {record['kind']}, not a surface")
    _, _, copied = fetch(folder, address)
    stage, place = opened(folder)
    prim = object_prim(stage, place, name)
    look = look_shader(stage, f"/{place}/Looks/{name}", copied, colour)
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(look, UsdShade.Tokens.strongerThanDescendants)
    prim.CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(address)
    if colour is not None:
        prim.CreateAttribute("score:surface:colour", Sdf.ValueTypeNames.String).Set(colour)
    stage.GetRootLayer().Save()
    return {"name": name, "surface": address, "colour": colour}


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
    stage.GetRootLayer().Save()
    return {"name": name, "light": address, "at": list(at), "watts": watts}


def remove(folder, name):
    """The object (and its look) or light called `name` taken out of the scene."""
    stage, place = opened(folder)
    paths = [f"/{place}/{part}/{name}" for part in ("Objects", "Looks", "Lights")]
    found = [path for path in paths if stage.GetPrimAtPath(path)]
    if not found:
        raise Refused(f"the scene holds no object or light {name}")
    for path in found:
        stage.RemovePrim(path)
    stage.GetRootLayer().Save()
    return {"removed": name}


def listing(folder):
    """Each object (its address, pose, surface and box in the scene, metres) and light, as the agent reads them."""
    stage, place = opened(folder)
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    objects = []
    for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
        at, turn, scale = pose_of(prim)
        box = boxes.ComputeWorldBound(prim).ComputeAlignedRange()
        objects.append({"name": prim.GetName(), "address": prim.GetAttribute("score:library").Get(),
                        "at": at, "turn": turn, "scale": scale,
                        "surface": prim.GetAttribute("score:surface").Get(),
                        "colour": prim.GetAttribute("score:surface:colour").Get(),
                        "box": [[round(value, 3) for value in box.GetMin()],
                                [round(value, 3) for value in box.GetMax()]] if not box.IsEmpty() else None})
    lights = [{"name": prim.GetName(), "at": pose_of(prim)[0],
               "watts": UsdLux.SphereLight(prim).GetIntensityAttr().Get()}
              for prim in stage.GetPrimAtPath(f"/{place}/Lights").GetChildren()]
    return {"place": place, "camera": record_of(folder)["camera"], "objects": objects, "lights": lights}
