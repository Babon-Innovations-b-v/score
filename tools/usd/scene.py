"""The rest of a place that the game drew in its own code, from the place's scene record (`data/scene/<place>.json`),
written into its OpenUSD stage beside the made objects (tools/usd/export.py calls `write`).

A kit or an inventory holds the pieces the framework made. What the game 2099 built in code was never in either: room
shells and the building round a room, stepped floors, stairs, the gameplay objects it places from code (a console, the
rocket), the water, the far backdrop, the ground beyond the place, every light and the sky. The scene record holds them
as numbers copied from the game (each entry names the game file it came from), and this module builds them:

    structure   code builders (tools/usd/builders.py) by name with their numbers, each painted with a library surface,
                built in the place's frame or in its own and placed (`placed_at`, `placed_turn`):
                /<place>/Structure/<name>
    objects     a world model file (a gameplay object; tools/usd/glb_asset.py) where the game stands it, turned about up
                (`yaw`, as the game turns it) or by a whole `rotation` (one on a seat of its own, tipped with the
                ball's curve), scaled to the height the game gives it, with what stands on it: /<place>/Fixtures/<name>;
                one that stands for an inventory row names it (`row`) and carries its model's hash, so the pick lock
                (tools/usd/picks.py) holds it like a laid object
    planned_rocks  the plan's rocks round the place, each lying as the game lays it (tools/usd/rocks.py), one point
                instancer of the world's rock models: /<place>/Rocks
    ground_decals  what the game paints on the ground (the wreck's scorch), mixed into the near ground's baked colour
                (tools/usd/ground_detail.py, when the place's ground record carries the ground shader's detail)
    water       a flat surface of the library's water: /<place>/Water/<name>, with how much it mirrors (`mirror`)
    ground      a ground the game makes in code (a far disc, Mars's plain): structure entries with the ground's surface
    lights      the game's lights, UsdLux (/<place>/Lights): an omni a sphere light, a spot one shaped to its cone, the
                sun or moon a distant light; the game's own numbers ride on each as `score:game:*`
    environment the sky the camera sees and the ambient light (a dome light, `/<place>/Environment`), the exposure;
                its `stars` (the game's star field, its own seed's) and its `haze` (a body of fog the game fills a room
                or Mars's air with, as a see-through shell carrying the fog's numbers; on Earth the haze ring) and
                its `dust` (the fine grains Mars's wind carries along the ground, at one moment) under /<place>/Sky
    places      other places seen from this one, their own stages referenced where the game stands them (`yaw` or a
                whole `rotation`, as objects; `scale` for one shown at another length): /<place>/Places/<name>
    moon        the Moon on the night sky as the game's sky shader draws it (its face with its seas, and its halo in the
                city's air), each a picture on a square far out along its way: /<place>/Sky/moon, /<place>/Sky/halo
    moved       kit pieces the game moves in its own code (a door it slides open), by the piece's `node`: shifted `by`
                metres in the place's frame before the kit is laid (moved_pieces)
    kit_glow    how the night lights a kit's lights (a kind's `night_glow` in the kit): `strength` and `ramp` of the
                game's textured shader, which the export bakes into each such model's glow map
    views       the cameras the place is judged from (the player's own spots; inside a room at standing height), each
                naming the game's shot from about the same place
    game_only   what the game draws there that the scene does not carry, said plainly (a crowd, the stars)

Light units. The game's energies are unitless (Godot): a directional light of energy E lights a white floor it faces to
about E, an omni light of energy E about E at a metre, falling off as its distance to the power of its `attenuation`
(a physical light's is 2), so an omni or spot light's energy is matched halfway out to its range (reach_matched). The stage holds watts as Blender's USD reader takes them (a sphere
light's intensity times pi is its watts; a distant light's intensity times 4 its strength in W/m^2), from
SUN_PER_ENERGY and OMNI_PER_ENERGY; `score:game:energy`, `range` and `attenuation` keep the game's own numbers for an
engine that reads them back.
"""
import json
import math
import pathlib
import sys

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux, UsdShade, Vt

import builders
import glb_asset
import ground_detail
import rocks
import shaders

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools/assets"))
import world as world_assets  # noqa: E402
SCENES = REPO / "data/scene"
SHARED_PAINT = REPO / "data/library/shared_paint.json"
# A game directional light of energy 1 as a sun in W/m^2: a white surface it faces then reads about as bright as in
# the game (the game draws diffuse light without the 1/pi a physical renderer divides by).
SUN_PER_ENERGY = math.pi
# An omni light of energy 1 in watts: lights a surface a metre off as a sun of energy 1 does (4 pi times the sun's).
OMNI_PER_ENERGY = 4 * math.pi * SUN_PER_ENERGY
# Blender's USD reader: a sphere light's watts are its intensity times pi, a distant light's strength its intensity
# times 4.
SPHERE_WATTS_PER_INTENSITY = math.pi
DISTANT_STRENGTH_PER_INTENSITY = 4.0
LAMP_RADIUS = 0.05
# A game spot light dims from its middle all the way out to its cone's edge (Godot's SpotLight3D, its angle
# attenuation 1 by default: 1 - (1 - cos a) / (1 - cos cone)), so its cone is soft across the whole of it.
SPOT_SOFTNESS = 1.0
# The game's lamp (game/base/lamp/lamp.gd): energy LAMP_ENERGY times a lamp's strength, its colour and fall-off; only
# the hub's roof fittings cast shadows (HubKit); a walkway tube lights every second bay (TubeKit.LIGHT_EVERY).
LAMP_ENERGY = 12.0
LAMP_COLOUR = "#ffd29a"
LAMP_ATTENUATION = 2.2
SHADOW_KINDS = ("hub_roof_light_fixture",)
TUBE_LIGHT_EVERY = 2
# The code builders a scene record may name.
BUILDERS = ("quad", "box", "annulus", "walls", "wall_strip", "pyramid_roof", "dome", "cylinder_wall", "disc", "stairs",
            "grid", "heightfield", "room_walls", "room_deck", "dome_roof", "lathe", "sphere", "tube_arc", "stars",
            "haze_volume", "torus", "specks", "ship_hull", "ship_legs")


def record(place):
    """The place's scene record, or None when it has none."""
    path = SCENES / f"{place}.json"
    return json.loads(path.read_text()) if path.exists() else None


def colour(value):
    """A colour as three linear floats from '#rrggbb' (sRGB) or a list of linear floats."""
    if isinstance(value, str):
        value = value.lstrip("#")
        srgb = [int(value[index:index + 2], 16) / 255.0 for index in (0, 2, 4)]
        return tuple(channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in srgb)
    return tuple(float(channel) for channel in value[:3])


def world_file(world, name):
    """A file a record names: kept in git (`data/...`), else in the world's release (tools/assets/world.py), in the
    folder `world` when given (a test's own), else in the fetched release."""
    return world_assets.resolve(name, world)


def mesh_prim(stage, path, built):
    """A built mesh as a UsdGeomMesh: its triangles, uvs in its own metres (or a picture's 0..1), drawn double sided."""
    prim = UsdGeom.Mesh.Define(stage, path)
    points = built["points"].astype(np.float32)
    prim.CreatePointsAttr(Vt.Vec3fArray.FromNumpy(points))
    prim.CreateFaceVertexCountsAttr(Vt.IntArray.FromNumpy(np.full(len(built["triangles"]), 3, dtype=np.int32)))
    prim.CreateFaceVertexIndicesAttr(Vt.IntArray.FromNumpy(built["triangles"].reshape(-1).astype(np.int32)))
    UsdGeom.PrimvarsAPI(prim).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex).Set(
        Vt.Vec2fArray.FromNumpy(built["uvs"].astype(np.float32)))
    prim.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    prim.CreateDoubleSidedAttr(True)
    prim.CreateExtentAttr([Gf.Vec3f(*map(float, points.min(axis=0))), Gf.Vec3f(*map(float, points.max(axis=0)))])
    return prim


def bind_surface(stage, prim, place, surface, out=None):
    """Paint a built mesh with a library surface of the place (/<place>/Library/<surface>), or with its framework
    shader when it has one and the stage's folder is given (shaders.py), and say which."""
    material = shaders.look(stage, place, surface, out) or \
        UsdShade.Material(stage.GetPrimAtPath(f"/{place}/Library/{surface}"))
    if not material:
        raise ValueError(f"{place}: the library has no surface {surface}")
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(material)
    prim.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(surface)


def built_meshes(entry):
    """A structure entry's meshes: its builder called with its numbers (every key but name, builder, from, layer, plain
    and its placing), each placed where the entry stands (`placed`)."""
    if entry["builder"] not in BUILDERS:
        raise ValueError(f"no code builder named {entry['builder']}")
    builder = getattr(builders, entry["builder"])
    numbers = {key: value for key, value in entry.items()
               if key not in ("name", "builder", "from", "layer", "mirror", "placed_at", "placed_turn", "plain")}
    built = builder(**numbers)
    return [placed(part, entry) for part in (built if isinstance(built, list) else [built])]


def placed(built, entry):
    """A built mesh moved from the entry's own frame into the place's: turned by its `placed_turn` (a unit quaternion
    [x, y, z, w]) and moved to its `placed_at`, for a piece the game stands on a seat of its own (the landing pad,
    tipped with the ball's curve); an entry with neither is built in the place's frame already."""
    if "placed_at" not in entry and "placed_turn" not in entry:
        return built
    x, y, z, w = (float(value) for value in entry.get("placed_turn", (0.0, 0.0, 0.0, 1.0)))
    turn = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    return dict(built, points=built["points"] @ turn.T + np.asarray(entry.get("placed_at", (0.0, 0.0, 0.0)), dtype=float))


def sun_ball(stage, place, path, centre, radius):
    """A ball in the sky painted with the library's `sun_disc`, drawn on its own (no shadow, no collision)."""
    UsdGeom.Scope.Define(stage, str(Sdf.Path(path).GetParentPath()))
    prim = mesh_prim(stage, path, builders.sphere(list(map(float, centre)), float(radius), "sun_disc", 12, 24))
    bind_surface(stage, prim, place, "sun_disc")
    prim.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("sky")
    return prim


def write_structure(stage, place, entries, root="Structure", kind="structure", out=None):
    """Every structure entry as one mesh (several when its builder gives several) painted with its surface."""
    if not entries:
        return
    UsdGeom.Scope.Define(stage, f"/{place}/{root}")
    for entry in entries:
        for number, built in enumerate(built_meshes(entry)):
            name = entry["name"] if number == 0 else f"{entry['name']}_{number + 1}"
            prim = mesh_prim(stage, f"/{place}/{root}/{name}", built)
            bind_surface(stage, prim, place, built["surface"], out)
            for key, value in (("score:kind", kind), ("score:builder", entry["builder"]),
                               ("score:from", entry.get("from", ""))):
                prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
            if "plain" in entry:  # which plain thing a primitive is (tools/usd/placeholders.py)
                prim.GetPrim().CreateAttribute("score:plain", Sdf.ValueTypeNames.String).Set(entry["plain"])
            if "layer" in entry:  # a roof's draw layer, left out of a cutaway look
                prim.GetPrim().CreateAttribute("score:layer", Sdf.ValueTypeNames.String).Set(str(entry["layer"]))
            if "mirror" in entry:
                write_mirror(prim.GetPrim(), entry["mirror"])


def write_mirror(prim, mirror):
    """How much of what stands over it a water surface gives back (the game's harbour shader): `along` looking along
    it, `down` looking straight down, its ripples tipping it by `ripple_tip` and `ripple_size` metres across, as
    score:mirror_* on the surface for a renderer to draw (tools/blender/inside/usd_views.py)."""
    for key in ("along", "down", "ripple_tip", "ripple_size"):
        prim.CreateAttribute(f"score:mirror_{key}", Sdf.ValueTypeNames.Float).Set(float(mirror[key]))
    prim.CreateAttribute("score:mirror_from", Sdf.ValueTypeNames.String).Set(mirror.get("from", ""))


def fixture_asset(entry, out, world, boxes):
    """A fixture's world model converted once into the stage's assets; its asset name and box (low, high)."""
    source = world_file(world, entry["model"])
    name = "fixture_" + source.stem
    if name not in boxes:
        boxes[name] = glb_asset.asset(source, out / "assets" / f"{name}.usdc", out / "assets/textures")
    return name, boxes[name]


def label_picture(entry, world):
    """A label's text as the game's Label3D draws it, as a picture: each line of `label` in the game's font (`font`,
    `font_size` pixels) in `colour`, an `outline_size` pixel outline in `outline_colour`, the lines centred under each
    other on a clear ground."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(str(world_file(world, entry["font"])), int(entry["font_size"]))
    stroke = int(entry.get("outline_size", 0)) // 2
    lines = entry["label"]
    ascent, descent = font.getmetrics()
    tall = ascent + descent + 2 * stroke
    wide = max(int(font.getlength(line)) for line in lines) + 2 * stroke + 2
    picture = Image.new("RGBA", (wide, tall * len(lines)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(picture)
    for number, line in enumerate(lines):
        draw.text((wide / 2, number * tall + stroke), line, font=font, anchor="ma",
                  fill=entry.get("colour", "#ffffff"), stroke_width=stroke,
                  stroke_fill=entry.get("outline_colour", "#000000"))
    return picture


def label(stage, path, entry, out, world):
    """A label the game hangs in the room (a Label3D: a desk's readout, a screen's word): its text drawn unlit on a
    quad `pixel_size` metres a pixel, centred on `at`, facing +z turned `yaw` degrees about up."""
    picture = label_picture(entry, world)
    textures = out / "assets/textures"
    textures.mkdir(parents=True, exist_ok=True)
    target = textures / f"label_{pathlib.Path(path).name}.png"
    picture.save(target)
    half = np.array(picture.size, dtype=np.float64) * float(entry["pixel_size"]) / 2
    built = builders.quad([[-half[0], -half[1], 0.0], [half[0], -half[1], 0.0], [half[0], half[1], 0.0],
                           [-half[0], half[1], 0.0]], None, (1.0, 1.0))
    xform = UsdGeom.Xform.Define(stage, path)
    xform.AddTranslateOp().Set(Gf.Vec3d(*map(float, entry["at"])))
    xform.AddRotateYOp().Set(float(entry.get("yaw", 0.0)))
    prim = mesh_prim(stage, f"{path}/text", built)
    material = backdrop_material(stage, f"{path}/look", f"../assets/textures/{target.name}")
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(material)
    for key, value in (("score:kind", "label"), ("score:label", "\n".join(entry["label"])),
                       ("score:from", entry.get("from", ""))):
        xform.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)


def glow_material(stage, path, glow):
    """A lit lamp's lens as the game paints it over the model's own look: black under its `colour` glowing
    `strength` times (StandardMaterial3D emission and its energy)."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.0, 0.0, 0.0))
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*(channel * float(glow.get("strength", 1.0)) for channel in colour(glow["colour"]))))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def turn(xform, entry):
    """An entry's turn: its `rotation` (a unit quaternion [x, y, z, w] in the place's frame, for one standing on a seat
    of its own that the ball's curve tips), else `yaw` degrees about up (right-handed, as the game turns it: +x toward
    -z)."""
    if "rotation" in entry:
        x, y, z, w = (float(value) for value in entry["rotation"])
        xform.AddOrientOp(UsdGeom.XformOp.PrecisionDouble).Set(Gf.Quatd(w, Gf.Vec3d(x, y, z)))
        return
    xform.AddRotateYOp().Set(float(entry.get("yaw", 0.0)))


def fixture(stage, path, entry, out, world, boxes):
    """One gameplay object where the game stands it: its model at `at`, turned (`turn`), scaled by `scale` or to
    `height` metres tall, worn in a `glow` the game paints over it when it has one, in the game's shared paints by
    its surfaces' names when `shared_paint` (its children too); the things standing on it
    (`children`, each the same in its parent's frame, or a `label`) under it. A `stretch` (x, y, z) presses it
    unevenly after that, as the game draws a model pressed to other proportions."""
    if "label" in entry:
        label(stage, path, entry, out, world)
        return
    name, (low, high) = fixture_asset(entry, out, world, boxes)
    scale = float(entry.get("scale", 1.0))
    stretch = entry.get("stretch")
    if "height" in entry:
        scale = float(entry["height"]) / float(high[1] - low[1])
    xform = UsdGeom.Xform.Define(stage, path)
    xform.GetPrim().GetReferences().AddReference(f"../assets/{name}.usdc")
    xform.AddTranslateOp().Set(Gf.Vec3d(*map(float, entry["at"])))
    turn(xform, entry)
    xform.AddScaleOp().Set(Gf.Vec3f(*stretch) * scale if stretch is not None else Gf.Vec3f(scale))
    for key, value in (("score:kind", entry.get("kind", "fixture")), ("score:model", entry["model"]),
                       ("score:from", entry.get("from", ""))):
        xform.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
    if "row" in entry:  # an inventory row's made model the game stands from code: its row and model hash (picks.py)
        row_of(xform.GetPrim(), entry, world)
    if "glow" in entry:  # bound on the model's own meshes, so a label standing on it keeps its own look
        glow = glow_material(stage, f"{path}_glow", entry["glow"])
        for prim in Usd.PrimRange(xform.GetPrim()):
            if prim.IsA(UsdGeom.Mesh):
                UsdShade.MaterialBindingAPI.Apply(prim).Bind(glow)
    if entry.get("shared_paint"):
        shared_paint(stage, xform.GetPrim(), path)
    for number, child in enumerate(entry.get("children", []), start=1):
        stem = "label" if "label" in child else pathlib.Path(child["model"]).stem
        child = dict(child, scale=child.get("scale", 1.0),
                     shared_paint=child.get("shared_paint", entry.get("shared_paint")))
        fixture(stage, f"{path}/{stem}_{number}", child, out, world, boxes)


def shared_paint_material(stage, path, paint):
    """One of the game's shared paints (data/library/shared_paint.json) as a UsdPreviewSurface: its flat colour, its
    roughness and metal, given off as light when the game draws it unshaded."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    linear = Gf.Vec3f(*(channel ** 2.2 for channel in paint["colour"]))
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(linear)
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(float(paint.get("roughness", 0.7)))
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(float(paint.get("metal", 0.0)))
    if paint.get("unshaded"):
        shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(linear)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    material.GetPrim().CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(paint["from"])
    return material


def shared_paint(stage, prim, path):
    """Paint a game model as the game does (part_model.gd: a surface named after one of its shared materials is drawn
    in that material, which takes its colour from the tokens): each of the model's meshes whose own material carries
    a shared paint's name is bound to that paint; a surface named nothing shared keeps the model's own look."""
    paints = json.loads(SHARED_PAINT.read_text())["paints"]
    made = {}
    for part in Usd.PrimRange(prim):
        if not part.IsA(UsdGeom.Mesh):
            continue
        own = UsdShade.MaterialBindingAPI(part).ComputeBoundMaterial()[0]
        name = own.GetPrim().GetAttribute("score:material").Get() if own and own.GetPrim().HasAttribute(
            "score:material") else None
        if name not in paints:
            continue
        if name not in made:
            made[name] = shared_paint_material(stage, f"{path}_paint/{name}", paints[name])
        UsdShade.MaterialBindingAPI.Apply(part).Bind(made[name])


def row_of(prim, entry, world):
    """A fixture's inventory row and its model's content hash (complete.model_hash), as the pick lock reads them."""
    import complete
    prim.CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set(entry["row"])
    prim.CreateAttribute("score:model_sha256", Sdf.ValueTypeNames.String).Set(
        complete.model_hash(world_file(world, entry["model"])))


def write_objects(stage, place, entries, out, world):
    """The gameplay objects the game places from code (a console, the rocket's pad, a door leaf), each a fixture."""
    if not entries:
        return
    UsdGeom.Scope.Define(stage, f"/{place}/Fixtures")
    boxes = {}
    for entry in entries:
        fixture(stage, f"/{place}/Fixtures/{entry['name']}", entry, out, world, boxes)


def write_places(stage, place, entries):
    """Other places seen from this one (the base on the wreck's horizon, the square and the launch view past the
    flat's balcony): each the other place's own stage referenced, as exported beside this one (`../../<stage>/`),
    where the game stands it in this place's frame, turned as `turn` says."""
    if not entries:
        return
    UsdGeom.Scope.Define(stage, f"/{place}/Places")
    for entry in entries:
        xform = UsdGeom.Xform.Define(stage, f"/{place}/Places/{entry['name']}")
        xform.GetPrim().GetReferences().AddReference(f"../../{entry['stage']}/{entry['stage']}.usda")
        xform.AddTranslateOp().Set(Gf.Vec3d(*map(float, entry["at"])))
        turn(xform, entry)
        if "scale" in entry:  # a stage laid for one length, shown at another (a walkway tube's run)
            xform.AddScaleOp().Set(Gf.Vec3f(*map(float, entry["scale"])))
        for key, value in (("score:kind", "place"), ("score:place", entry["stage"]), ("score:from", entry.get("from", ""))):
            xform.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
        # What this place draws itself (its ground, water, backdrop, sky and sun) is left out of the one it shows.
        for shared in ("Ground", "Terrain", "Water", "Backdrop", "Sky", "Environment", "Places"):
            stage.OverridePrim(f"/{place}/Places/{entry['name']}/{shared}").SetActive(False)
        shown = (record(entry["stage"]) or {}).get("lights", [])
        for name, light in zip(light_names(shown), shown):
            if light["type"] == "sun":
                stage.OverridePrim(f"/{place}/Places/{entry['name']}/Lights/{name}").SetActive(False)


def write_rocks(stage, place, entry, out, world, ground):
    """The planned rocks round the place (rocks.py), as one point instancer (/<place>/Rocks): a prototype per rock
    model (the world's own file, converted once), an instance per rock where and how the game lays it."""
    if not entry or ground is None:
        return
    laid = rocks.laid_rocks(entry, world, ground)
    instancer = UsdGeom.PointInstancer.Define(stage, f"/{place}/Rocks")
    models = sorted({rock["model"] for rock in laid})
    boxes = {}
    prototypes = []
    for number, model in enumerate(models):
        name, _ = fixture_asset({"model": model}, out, world, boxes)
        prototype = UsdGeom.Xform.Define(stage, f"/{place}/Rocks/Prototypes/{name}")
        prototype.GetPrim().GetReferences().AddReference(f"../assets/{name}.usdc")
        prototypes.append(prototype.GetPath())
    instancer.CreatePrototypesRel().SetTargets(prototypes)
    instancer.CreateProtoIndicesAttr([models.index(rock["model"]) for rock in laid])
    instancer.CreatePositionsAttr([Gf.Vec3f(*map(float, rock["at"])) for rock in laid])
    instancer.CreateOrientationsAttr([Gf.Quath(Gf.Matrix3d(*np.asarray(rock["turn"]).T.reshape(-1).tolist())
                                               .ExtractRotation().GetQuat()) for rock in laid])
    instancer.CreateScalesAttr([Gf.Vec3f(*map(float, rock["stretch"])) for rock in laid])
    for key, value in (("score:kind", "rocks"), ("score:from", entry.get("from", ""))):
        instancer.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)


def backdrop_material(stage, path, picture_file, threshold=0.5):
    """A backdrop picture drawn as it is: unlit (its colour as emission, no diffuse), its alpha cutting out the sky
    (at `threshold`; 0 lays it over what is behind as much as its alpha says, as the game's sky draws its Moon)."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    reader = UsdShade.Shader.Define(stage, f"{path}/uv")
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    texture = UsdShade.Shader.Define(stage, f"{path}/picture")
    texture.CreateIdAttr("UsdUVTexture")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(picture_file)
    texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
        reader.CreateOutput("result", Sdf.ValueTypeNames.Float2))
    texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.0, 0.0, 0.0))
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).ConnectToSource(
        texture.CreateOutput("a", Sdf.ValueTypeNames.Float))
    shader.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(float(threshold))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def moved_pieces(pieces, moves):
    """The kit's laid pieces with the ones the game moves in its own code shifted: each move names a piece by its
    `node` (the game's node name in the kit's layout) and shifts it `by` metres in the place's frame (its `at` and
    its transform, `matrix`, when it has one)."""
    by_node = {move["node"]: np.asarray(move["by"], dtype=np.float64) for move in moves}
    found = []
    for piece in pieces:
        shift = by_node.get(piece.get("node"))
        if shift is None:
            found.append(piece)
            continue
        moved = dict(piece, at=[float(value) for value in np.asarray(piece["at"], dtype=np.float64) + shift])
        if "matrix" in piece:
            matrix = np.array(piece["matrix"], dtype=np.float64)
            matrix[:3, 3] += shift
            moved["matrix"] = matrix.tolist()
        found.append(moved)
    missing = set(by_node) - {piece.get("node") for piece in pieces}
    if missing:
        raise ValueError(f"the kit has no piece of the node {sorted(missing)} to move")
    return found


def smoothstep(low, high, value):
    inside = np.clip((value - low) / (high - low), 0.0, 1.0)
    return inside * inside * (3.0 - 2.0 * inside)


def sky_frame(way):
    """The Moon's way and the two ways across its face, as the game's sky shader sets them (night_dome.gdshader)."""
    toward = np.asarray(way, dtype=np.float64)
    toward /= np.linalg.norm(toward)
    right = np.cross([0.0, 1.0, 0.0], toward)
    right /= np.linalg.norm(right)
    return toward, right, np.cross(toward, right)


def sky_rays(half_angle, pixels):
    """For a square picture `pixels` across on a plane square to the way, `half_angle` radians either side of it: each
    pixel's ray as its share across (x) and up (y) the face of the sky, and how far it is from the way, in radians."""
    edge = math.tan(half_angle)
    across = (np.arange(pixels) + 0.5) / pixels * 2.0 - 1.0
    x_side, y_side = np.meshgrid(across * edge, -across * edge)
    length = np.sqrt(1.0 + x_side ** 2 + y_side ** 2)
    return x_side / length, y_side / length, np.arccos(np.clip(1.0 / length, -1.0, 1.0))


def face_noise(at_x, at_y):
    """The sky shader's smooth noise on the Moon's face, from 0 to 1 (its hash2 and face_noise)."""
    def hashed(cell_x, cell_y):
        return np.modf(np.sin(cell_x * 127.1 + cell_y * 311.7) * 43758.5453)[0] % 1.0
    cell_x, cell_y = np.floor(at_x), np.floor(at_y)
    blend_x = (at_x - cell_x) ** 2 * (3.0 - 2.0 * (at_x - cell_x))
    blend_y = (at_y - cell_y) ** 2 * (3.0 - 2.0 * (at_y - cell_y))
    low = hashed(cell_x, cell_y) * (1 - blend_x) + hashed(cell_x + 1, cell_y) * blend_x
    high = hashed(cell_x, cell_y + 1) * (1 - blend_x) + hashed(cell_x + 1, cell_y + 1) * blend_x
    return low * (1 - blend_y) + high * blend_y


def srgb_bytes(linear):
    linear = np.clip(linear, 0.0, 1.0)
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    return (srgb * 255.0 + 0.5).astype(np.uint8)


def moon_face_picture(entry, pixels=1024):
    """The Moon's face as the sky shader draws it on a full Moon: its colour, its seas darker, `brightness` times
    (kept to 1, a picture's most), its rim smoothed off; RGBA, the alpha how much of the sky it covers."""
    half = math.radians(float(entry["across"])) / 2.0
    on_x, on_y, _ = sky_rays(half * 1.05, pixels)
    across = math.sin(half)
    face_x, face_y = on_x / across, on_y / across
    covered = 1.0 - smoothstep(0.96, 1.0, np.hypot(face_x, face_y))
    seas = smoothstep(0.45, 0.75, face_noise(face_x * 2.2 + 4.0, face_y * 2.2 + 4.0)) * float(entry["seas"])
    lit = float(entry["brightness"]) * float(entry.get("lit", 1.0))
    rgb = np.stack([channel * (1.0 - seas) * lit for channel in colour(entry["colour"])], axis=-1)
    return np.dstack([srgb_bytes(rgb), (np.clip(covered, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)]), half * 1.05


def moon_halo_picture(entry, pixels=512):
    """The Moon's glow in the city's air as the sky shader draws it: the Moon's colour laid over the sky by
    `halo` times its lit share, falling off as exp(-angle / `halo_fall`) from its way; RGBA."""
    half = 6.0 * float(entry["halo_fall"])
    _, _, angle = sky_rays(half, pixels)
    glow = np.clip(float(entry["halo"]) * float(entry.get("lit", 1.0)) * np.exp(-angle / float(entry["halo_fall"])),
                   0.0, 1.0)
    rgb = np.broadcast_to(np.asarray(colour(entry["colour"])), (pixels, pixels, 3))
    # Dithered by a fixed half step either way, so the faint glow far out does not fall into rings of one byte each.
    dither = np.random.default_rng(0).uniform(-0.5, 0.5, glow.shape)
    alpha = np.clip(glow * 255.0 + 0.5 + dither, 0.0, 255.0).astype(np.uint8)
    return np.dstack([srgb_bytes(rgb), alpha]), half


def sky_square(stage, path, entry, half_angle, distance, picture_file):
    """A square far out along the Moon's way from its `eye`, square to the way, `half_angle` across either side,
    drawn with its picture as the sky shows it (unlit, laid over by its alpha)."""
    toward, right, up = sky_frame(entry["way"])
    middle = np.asarray(entry["eye"], dtype=np.float64) + toward * distance
    edge = distance * math.tan(half_angle)
    corners = [middle + (right * side_x + up * side_y) * edge for side_x, side_y in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    built = builders.quad(corners, "sky")
    built["uvs"] = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])
    prim = mesh_prim(stage, path, built)
    material = backdrop_material(stage, f"{path}_look", picture_file, threshold=0.0)
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(material)
    for key, value in (("score:kind", "sky"), ("score:from", entry.get("from", ""))):
        prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)


def write_moon(stage, place, entry, out):
    """The Moon as the game's sky draws it at infinity, here `distance` metres out along its way from the eye it is
    seen from (far past everything else, so it moves little across the place): its face, and behind it its halo."""
    if not entry:
        return
    from PIL import Image
    UsdGeom.Scope.Define(stage, f"/{place}/Sky")
    textures = out / "assets/textures"
    textures.mkdir(parents=True, exist_ok=True)
    distance = float(entry.get("distance", 1800.0))
    for name, (picture, half), farther in (("halo", moon_halo_picture(entry), 10.0),
                                           ("moon", moon_face_picture(entry), 0.0)):
        target = textures / f"sky_{name}.png"
        Image.fromarray(picture, "RGBA").save(target)
        sky_square(stage, f"/{place}/Sky/{name}", entry, half, distance + farther, f"../assets/textures/{target.name}")


def game_values(prim, entry):
    """The game's own numbers for a light, kept as they were."""
    for key in ("energy", "range", "attenuation", "angle"):
        if key in entry:
            prim.CreateAttribute(f"score:game:{key}", Sdf.ValueTypeNames.Float).Set(float(entry[key]))
    prim.CreateAttribute("score:game:shadows", Sdf.ValueTypeNames.Bool).Set(bool(entry.get("shadows", False)))
    prim.CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(entry.get("from", ""))


def aim_turn(eye, aim):
    """The rotation that turns a light's -z (the way UsdLux lights shine) toward aim from eye."""
    forward = np.asarray(aim, dtype=np.float64) - np.asarray(eye, dtype=np.float64)
    forward /= np.linalg.norm(forward)
    up = np.array([0.0, 1.0, 0.0]) if abs(forward[1]) < 0.99 else np.array([1.0, 0.0, 0.0])
    back = -forward
    across = np.cross(up, back)
    across /= np.linalg.norm(across)
    upward = np.cross(back, across)
    return Gf.Matrix3d(*across, *upward, *back).ExtractRotation().GetQuat()


def reach_matched(entry):
    """A lamp's energy as a physical light needs it to light what it lights in the game: the game's fall-off is its
    distance to the power `attenuation` (2 is a physical light's), so the energy is matched halfway out to its range,
    energy x (range / 2) ^ (2 - attenuation); a lamp with no range keeps its energy."""
    energy = float(entry["energy"])
    if "range" not in entry:
        return energy
    return energy * (float(entry["range"]) / 2.0) ** (2.0 - float(entry.get("attenuation", 1.0)))


def write_light(stage, path, entry):
    """One of the game's lights as a UsdLux light (see the module's note on units)."""
    kind = entry["type"]
    tint = Gf.Vec3f(*colour(entry.get("colour", "#ffffff")))
    if kind == "sun":
        light = UsdLux.DistantLight.Define(stage, path)
        strength = SUN_PER_ENERGY * float(entry["energy"])
        light.CreateIntensityAttr(strength / DISTANT_STRENGTH_PER_INTENSITY)
        light.CreateAngleAttr(float(entry.get("size", 0.5)))
        light.AddOrientOp().Set(Gf.Quatf(aim_turn([0.0, 0.0, 0.0], entry["toward"])))
    else:
        light = UsdLux.SphereLight.Define(stage, path)
        watts = OMNI_PER_ENERGY * reach_matched(entry)
        light.CreateIntensityAttr(watts / SPHERE_WATTS_PER_INTENSITY)
        light.CreateRadiusAttr(float(entry.get("radius", LAMP_RADIUS)))
        light.AddTranslateOp().Set(Gf.Vec3d(*map(float, entry["at"])))
        if kind == "spot":
            light.AddOrientOp().Set(Gf.Quatf(aim_turn(entry["at"], entry["aim"])))
            shaping = UsdLux.ShapingAPI.Apply(light.GetPrim())
            shaping.CreateShapingConeAngleAttr(float(entry["angle"]))
            shaping.CreateShapingConeSoftnessAttr(float(entry.get("softness", SPOT_SOFTNESS)))
    light.CreateColorAttr(tint)
    light.GetPrim().CreateAttribute("score:game:type", Sdf.ValueTypeNames.String).Set(kind)
    game_values(light.GetPrim(), entry)


def kit_lights(kit, pieces):
    """The lights a kit room's lamps give, where the game's HubKit hangs them: a lamp kind's `light` (strength, reach,
    high) on every piece of it that is not its lens, a little in front of the piece at `high` of its height, an omni
    light of the game's lamp (energy LAMP_ENERGY times strength, the lamp colour, reach its range); a walkway tube's on
    every TUBE_LIGHT_EVERY-th bay, under the lens (TubeKit._lamp). `pieces` are the laid pieces, a tube's with the
    `spot` of its bay (export.py)."""
    kinds = kit.get("kinds", {})
    found, seen = [], {}
    for laid in pieces:
        light = kinds.get(laid["kind"], {}).get("light")
        if light is None or "part" in laid:
            continue
        size = np.asarray(laid["size"], dtype=np.float64)
        frame = np.column_stack([np.asarray(laid[axis], dtype=np.float64) for axis in ("x", "y", "z")])
        if "spot" in laid:
            count = seen.get(laid["kind"], 0)
            seen[laid["kind"]] = count + 1
            if count % TUBE_LIGHT_EVERY:
                continue
            local = size * np.array([0.0, 0.5, -0.6])
        else:
            local = np.array([0.0, size[1] * float(light.get("high", 0.5)), -(size[2] / 2 + 0.05)])
        at = np.append(np.asarray(laid["at"], dtype=np.float64) + frame @ local, 1.0)
        if "spot" in laid:
            at = np.asarray(laid["spot"], dtype=np.float64) @ at
        found.append({"type": "omni", "at": [round(float(value), 4) for value in at[:3]], "colour": LAMP_COLOUR,
                      "energy": LAMP_ENERGY * float(light.get("strength", 0.1)), "range": float(light.get("reach", 4.0)),
                      "attenuation": LAMP_ATTENUATION, "shadows": laid["kind"] in SHADOW_KINDS,
                      "from": f"HubKit lamp ({laid['kind']}), game/base/lamp/lamp.gd"})
    return found


def light_names(entries):
    """Each light's prim name: its own, else `sun_<n>` for the n-th sun or moon and `light_<n>` for the rest."""
    names, suns = [], 0
    for number, entry in enumerate(entries, start=1):
        suns += entry["type"] == "sun"
        names.append(entry.get("name") or (f"sun_{suns}" if entry["type"] == "sun" else f"light_{number}"))
    return names


def write_lights(stage, place, entries):
    if not entries:
        return
    UsdGeom.Scope.Define(stage, f"/{place}/Lights")
    for name, entry in zip(light_names(entries), entries):
        write_light(stage, f"/{place}/Lights/{name}", entry)


def write_environment(stage, place, environment):
    """The place's sky and ambient light: a dome light of the ambient colour and energy (what lights every side), the
    background the camera sees and the exposure as score:* on it."""
    if not environment:
        return
    dome = UsdLux.DomeLight.Define(stage, f"/{place}/Environment")
    ambient = environment.get("ambient", {"colour": "#000000", "energy": 0.0})
    dome.CreateColorAttr(Gf.Vec3f(*colour(ambient["colour"])))
    dome.CreateIntensityAttr(float(ambient["energy"]))
    prim = dome.GetPrim()
    prim.CreateAttribute("score:background", Sdf.ValueTypeNames.Color3f).Set(
        Gf.Vec3f(*colour(environment.get("background", "#000000"))))
    prim.CreateAttribute("score:exposure", Sdf.ValueTypeNames.Float).Set(float(environment.get("exposure", 1.0)))
    prim.CreateAttribute("score:ground_plane", Sdf.ValueTypeNames.Bool).Set(bool(environment.get("ground_plane", False)))
    prim.CreateAttribute("score:inside", Sdf.ValueTypeNames.Bool).Set(bool(environment.get("inside", False)))
    prim.CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(environment.get("from", ""))


def ground_skin(ground, picture):
    """The ground's skin as drawn: as it is, or for a shade map painted in one colour (Mars's ground, its record's
    `tint`) every pixel's shade carried onto that colour, so the skin's mean is the tint; the picture back."""
    if getattr(ground, "tint", None) is None:
        return picture
    from PIL import Image
    pixels = np.asarray(picture.convert("RGB"), dtype=np.float64) / 255.0
    linear = np.where(pixels <= 0.04045, pixels / 12.92, ((pixels + 0.055) / 1.055) ** 2.4)
    tinted = np.clip(linear / max(float(linear.mean()), 1e-4) * np.asarray(colour(ground.tint)), 0.0, 1.0)
    srgb = np.where(tinted <= 0.0031308, tinted * 12.92, 1.055 * tinted ** (1 / 2.4) - 0.055)
    return Image.fromarray((srgb * 255.0 + 0.5).astype(np.uint8))


def far_ground(stage, place, ground, entry, out, near):
    """The planned ground past the near patch (the export's /<place>/Ground, `near` its box across and along): the
    plan's square out to `reach` metres round the place, `step` metres apart, in the plan's skin (shaded as the
    ground shader shades it, ground_detail.far_colour, when the ground carries its detail); and, under it, the
    ball itself (`ball`), so the horizon is round as the game's. Both in the place's frame."""
    reach, step = float(entry.get("reach", 130.0)), float(entry.get("step", 2.0))
    points, triangles, skin_at = ground.mesh(np.array([-reach, -reach]), np.array([reach, reach]), 0.0, step)
    flat = points[:, [0, 2]]
    inside = np.all((flat > near[0] + step) & (flat < near[1] - step), axis=1)
    keep = ~np.all(inside[triangles], axis=1)
    textures = out / "assets/textures"
    textures.mkdir(parents=True, exist_ok=True)
    shaded = getattr(ground, "detail", None)
    skin = textures / f"ground_far_{pathlib.Path(ground.skin).stem}{'_shaded' if shaded else ''}.jpg"
    if not skin.exists():
        from PIL import Image
        picture = Image.open(ground.skin)
        coloured = ground_detail.far_colour(shaded, picture) if shaded else ground_skin(ground, picture)
        coloured.convert("RGB").save(skin, quality=90)
    built = builders.mesh(points, triangles[keep], np.column_stack([skin_at[:, 0], 1.0 - skin_at[:, 1]]), None)
    prim = mesh_prim(stage, f"/{place}/Terrain/far", built)
    material = UsdShade.Material.Define(stage, f"/{place}/Terrain/far_look")
    shader = UsdShade.Shader.Define(stage, f"/{place}/Terrain/far_look/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    reader = UsdShade.Shader.Define(stage, f"/{place}/Terrain/far_look/uv")
    reader.CreateIdAttr("UsdPrimvarReader_float2")
    reader.CreateInput("varname", Sdf.ValueTypeNames.String).Set("st")
    texture = UsdShade.Shader.Define(stage, f"/{place}/Terrain/far_look/skin")
    texture.CreateIdAttr("UsdUVTexture")
    texture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"../assets/textures/{skin.name}")
    texture.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
        reader.CreateOutput("result", Sdf.ValueTypeNames.Float2))
    texture.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
        texture.CreateOutput("rgb", Sdf.ValueTypeNames.Float3))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(1.0)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(material)
    prim.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("ground")
    if entry.get("ball"):
        middle = ground.in_place_frame(np.zeros(3))[0]
        sphere = UsdGeom.Sphere.Define(stage, f"/{place}/Terrain/ball")
        sphere.CreateRadiusAttr(ground.radius - float(entry.get("ball_below", 0.6)))
        sphere.AddTranslateOp().Set(Gf.Vec3d(*map(float, middle)))
        bind_surface(stage, sphere, place, entry["ball"])
        sphere.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("ground")


def unlit_material(stage, path, value):
    """A surface that only gives off its colour (`value`, '#rrggbb'), lit by nothing: a star."""
    material = UsdShade.Material.Define(stage, path)
    shader = UsdShade.Shader.Define(stage, f"{path}/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.0, 0.0, 0.0))
    shader.CreateInput("emissiveColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*colour(value)))
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return material


def write_stars(stage, place, entry):
    """The game's star field (builders.stars) as one mesh, /<place>/Sky/Stars, in the stars' unlit colour."""
    built = builders.stars(int(entry["count"]), int(entry["seed"]), float(entry["sky_distance"]),
                           float(entry["distance"]), float(entry["radius"]), float(entry["size"][0]),
                           float(entry["size"][1]), None)
    prim = mesh_prim(stage, f"/{place}/Sky/Stars", built)
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(
        unlit_material(stage, f"/{place}/Sky/star_look", entry["colour"]))
    for key, value in (("score:kind", "stars"), ("score:from", entry.get("from", ""))):
        prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)


def haze_centre(entry, ground):
    """A haze body's middle: its own `centre`, or with `"ball"` the middle of the place's world (the planned ground's
    ball, in the place's frame), as Mars's air is centred on Mars."""
    if entry["centre"] != "ball":
        return [float(value) for value in entry["centre"]]
    if ground is None:
        raise ValueError("a haze centred on the ball needs the place's planned ground")
    return [float(value) for value in ground.in_place_frame(np.zeros(3))[0]]


def write_haze_volume(stage, place, entry, ground):
    """A body of haze as the game's FogVolume holds it: a closed shell of its shape (builders.haze_volume), drawn as
    nothing by its surface (fully see-through) and carrying the fog's colour, density (its thickness per metre), how
    strongly it throws light forward, how far out the game works it out and how much of a lamp's light it catches, as
    score:haze_*, for a renderer to fill it (tools/blender/inside/usd_views.py)."""
    built = builders.haze_volume(entry["shape"], haze_centre(entry, ground), entry["size"], None)
    prim = mesh_prim(stage, f"/{place}/Sky/Haze", built)
    material = UsdShade.Material.Define(stage, f"/{place}/Sky/haze_look")
    shader = UsdShade.Shader.Define(stage, f"/{place}/Sky/haze_look/surface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(0.0)
    material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(material)
    held = prim.GetPrim()
    held.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("haze")
    held.CreateAttribute("score:haze_colour", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*colour(entry["colour"])))
    for key in ("density", "forward", "reach", "lamp_share"):
        if key in entry:
            held.CreateAttribute(f"score:haze_{key}", Sdf.ValueTypeNames.Float).Set(float(entry[key]))
    held.CreateAttribute("score:from", Sdf.ValueTypeNames.String).Set(entry.get("from", ""))


def smoothstep(low, high, value):
    share = np.clip((np.asarray(value, dtype=np.float64) - low) / (high - low), 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def haze_ring_alpha(entry, heights, angles):
    """How thick the haze ring is at each height over its foot (metres) and way round (degrees from +x toward +z),
    as the game's night_haze shader works it out: faint all the way up and thickest near the top of the far shore over
    the pictures, and thick on the ground in the gap the pictures leave open."""
    gone = 1.0 - smoothstep(entry["thickest_at"], entry["gone_by"], heights)
    over = np.maximum(entry["faint"] * gone,
                      entry["thickest"] * smoothstep(entry["thicken_from"], entry["thickest_at"], heights) * gone)
    start, end = entry["gap"]
    past_start = np.mod(angles - start + 360.0, 360.0)
    before_end = np.mod(end - start + 360.0, 360.0) - past_start
    in_gap = smoothstep(0.0, entry["gap_edge"], past_start) * smoothstep(0.0, entry["gap_edge"], before_end)
    ground = entry["ground_haze"] * (1.0 - smoothstep(0.0, entry["ground_height"], heights))
    return np.maximum(over[:, None], ground[:, None] * in_gap[None, :])


def haze_ring_colour(entry, heights):
    """The ring's colour at each height (linear): the game's night sky along the line from an eye `eye` metres over
    the ring's foot at its middle, navy at the horizon deepening toward the zenith's (night_sky.gdshaderinc, the Moon's
    glow left out)."""
    rise = heights - float(entry["eye"])
    up = rise / np.hypot(rise, float(entry["radius"]))
    share = np.clip(up / entry["deepest_at"], 0.0, 1.0) ** entry["deepening"]
    horizon, zenith = np.asarray(colour(entry["horizon"])), np.asarray(colour(entry["zenith"]))
    return horizon[None, :] * (1.0 - share[:, None]) + zenith[None, :] * share[:, None]


def haze_ring_picture(entry, path, wide=720, tall=150):
    """The ring's picture, once round it from bearing 0 (north, -z) clockwise, its bottom row at the ring's foot: the
    colour in sRGB and how thick as alpha."""
    from PIL import Image
    high = float(entry["high"]) - float(entry["low"])
    heights = (np.arange(tall) + 0.5) / tall * high
    bearings = (np.arange(wide) + 0.5) / wide * 360.0
    alpha = haze_ring_alpha(entry, heights, np.mod(bearings - 90.0, 360.0))
    linear = haze_ring_colour(entry, heights)
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    pixels = np.dstack([np.repeat(srgb[:, None, :], wide, axis=1), alpha[:, :, None]])[::-1]
    Image.fromarray((np.clip(pixels, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8), "RGBA").save(path)


def write_haze_ring(stage, place, entry, out):
    """The city's night haze at the edge of the Earth site: an open ring of `radius` from `low` to `high`, round
    `centre`, laid over what stands behind it as thinly as its picture's alpha (haze_ring_picture), unlit."""
    textures = out / "assets/textures"
    textures.mkdir(parents=True, exist_ok=True)
    picture = textures / "haze_ring.png"
    haze_ring_picture(entry, picture)
    segments = int(entry.get("segments", 96))
    ring = builders.cylinder_wall(float(entry["radius"]), float(entry["low"]), float(entry["high"]), None, segments,
                                  tuple(entry.get("centre", (0.0, 0.0))))
    ring["uvs"] = np.column_stack([np.repeat(np.linspace(0.0, 1.0, segments + 1), 2), np.tile([0.0, 1.0], segments + 1)])
    prim = mesh_prim(stage, f"/{place}/Sky/HazeRing", ring)
    material = backdrop_material(stage, f"/{place}/Sky/haze_ring_look", f"../assets/textures/{picture.name}",
                                 threshold=0.0)
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(material)
    for key, value in (("score:kind", "haze"), ("score:from", entry.get("from", ""))):
        prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)


def dust_points(entry, ground):
    """Where the drift's fine grains hang at one moment (environment `dust`): `count` of them over a square `side`
    metres wide round the place's middle, each from three draws of Godot's seeded generator (`seed`: across, along,
    and its height up to `high` metres over the ground under it), in the place's frame."""
    count, side, high = int(entry["count"]), float(entry["side"]), float(entry["high"])
    draws = np.asarray(builders.pcg32_floats(int(entry["seed"]), 3 * count), dtype=np.float64).reshape(count, 3)
    across, along = (draws[:, 0] - 0.5) * side, (draws[:, 1] - 0.5) * side
    lift = draws[:, 2] * high
    if ground is None:
        return np.column_stack([across, lift, along])
    flat = ground.frame[1] * ground.radius + across[:, None] * ground.frame[0] + along[:, None] * ground.frame[2]
    directions = flat / np.linalg.norm(flat, axis=1, keepdims=True)
    height, _ = ground.plan_height(directions)
    return ground.in_place_frame(directions * (ground.radius + height + lift)[:, None])


def write_dust(stage, place, entry, ground):
    """The wind's fine grains of dust (environment `dust`, dust_points), as specks of their unlit colour, see-through
    by `thickness`: /<place>/Sky/Dust."""
    built = builders.specks(dust_points(entry, ground), float(entry["across"]), None)
    prim = mesh_prim(stage, f"/{place}/Sky/Dust", built)
    material = unlit_material(stage, f"/{place}/Sky/dust_look", entry["colour"])
    UsdShade.Shader(stage.GetPrimAtPath(f"/{place}/Sky/dust_look/surface")).CreateInput(
        "opacity", Sdf.ValueTypeNames.Float).Set(float(entry["thickness"]))
    UsdShade.MaterialBindingAPI.Apply(prim.GetPrim()).Bind(material)
    for key, value in (("score:kind", "dust"), ("score:from", entry.get("from", ""))):
        prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)


def write_sky(stage, place, environment, out, ground=None):
    """What the game hangs in the place's air and sky that the camera sees: the stars (environment `stars`), the
    haze (environment `haze`: a body of fog, or with shape `ring` the Earth site's haze ring) and the wind's dust
    (environment `dust`), under /<place>/Sky."""
    environment = environment or {}
    if not (environment.get("stars") or environment.get("haze") or environment.get("dust")):
        return
    UsdGeom.Scope.Define(stage, f"/{place}/Sky")
    if environment.get("stars"):
        write_stars(stage, place, environment["stars"])
    if environment.get("dust"):
        write_dust(stage, place, environment["dust"], ground)
    haze = environment.get("haze")
    if haze and haze["shape"] == "ring":
        write_haze_ring(stage, place, haze, out)
    elif haze:
        write_haze_volume(stage, place, haze, ground)


def write(stage, place, scene, out, world=None, kit=None, pieces=(), ground=None, near=None):
    """Everything the place's scene record holds, into the base layer being written; a kit room's lamps' lights too
    (kit_lights), and with the place's planned ground the ground past its near patch (far_ground)."""
    write_structure(stage, place, scene.get("structure", []), out=out)
    write_structure(stage, place, scene.get("ground", []), root="Terrain", kind="ground")
    if ground is not None and scene.get("planned_ground"):
        UsdGeom.Scope.Define(stage, f"/{place}/Terrain")
        far_ground(stage, place, ground, scene["planned_ground"], out, near)
    write_structure(stage, place, scene.get("water", []), root="Water", kind="water")
    write_objects(stage, place, scene.get("objects", []), out, world)
    write_rocks(stage, place, scene.get("planned_rocks"), out, world, ground)
    write_places(stage, place, scene.get("places", []))
    write_moon(stage, place, scene.get("moon"), out)
    lights = (kit_lights(kit, pieces) if kit is not None and scene.get("kit_lights", True) else []) + \
        scene.get("lights", [])
    write_lights(stage, place, lights)
    write_environment(stage, place, scene.get("environment"))
    write_sky(stage, place, scene.get("environment"), out, ground)
    shaders.sun_discs(stage, place, scene.get("lights", []), lambda path, centre, radius: sun_ball(stage, place, path,
                                                                                                 centre, radius))
