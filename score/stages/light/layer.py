"""A place's light layer, `layers/light.usda`, written over its seed stage with tools/usd/scene.py's own writers, so
the sky and the lamps the assembly shows are today's records' and not the round-three export's:

    lamps     every lamp of the place (a sphere light under /<place>/Lights) as the seed has it, moved where its
              scene record now puts it (a light of the record whose spot the seed does not hold takes the nearest
              unmatched seed light of its kind within MOVE_MOST, else it is added); its strength stays the seed's here
              and is set by the light stage from the per-lamp passes (strengths)
    sky       what the record's sky holds and the seed lacks or drew the old way: the Earth on its ball with NASA's
              surface (shaders.earth_look's picture, the seed's cartoon picture left unread), the day sky's dome over
              Mars (mars_sky.py), the sun's disc along the sky's sun, the floodlights' shafts; the environment, the
              sky's stars and haze and the record's lights where the seed has none (the camp grounds' seed)

The writers draw into a stage made of the light layer over the seed (its edit target the light layer), so they find
the seed's library and write only the layer. Pictures they bake go into `assets/light/`, never `assets/textures/`,
where the seed's own pictures of the same names lie.

    write(place, record, seed_folder, out) -> {"lamps": [...], "sky": {...}}
    strengths(layer_path, place, scales)      each lamp's intensity times its scale, written into the layer
"""
import json
import pathlib
import shutil
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import ground as grounds  # noqa: E402
import scene  # noqa: E402
import shaders  # noqa: E402

LAYER = "layers/light.usda"
ASSETS = "assets/light"
# How far a record light may stand from the seed light it moves (the square's floodlight lamps moved onto their
# lenses' middles, 2026-10-11, about 1.5 m).
MOVE_MOST = 5.0
# Two spots this close are one light.
SAME_SPOT = 0.05
# How near a record lamp stands to a kit lamp of the light data for the two to be one lamp, metres.
LENS_NEAR = 1.0


def light_data(place):
    """The light stage's own additions to a place (data/light/<place>.json), kept out of its scene record, which
    holds what the game drew: lamps on a kit kind's lenses (`kit_lamps`), the camera's glow (`glow`), and kit kinds
    the seed laid where the kit no longer has them (`kit_moves`)."""
    path = REPO / f"data/light/{place}.json"
    return json.loads(path.read_text()) if path.exists() else {}


def lens_middle(laid):
    """A kit piece's lens middle: its foot raised half its height along its own up."""
    return np.asarray(laid["at"], dtype=float) + np.asarray(laid["y"], dtype=float) * laid["size"][1] / 2


def kit_lamps(place, data):
    """A lamp on every lens (glow part) of each `kit_lamps` kind, `ahead` metres in front of it, as record lights."""
    found = []
    pieces = json.loads((REPO / f"data/kit/{place}.json").read_text())["pieces"] if data.get("kit_lamps") else []
    for wanted in data.get("kit_lamps", []):
        lenses = [laid for laid in pieces if laid["kind"] == wanted["kind"] and laid.get("part") == "glow"]
        for number, laid in enumerate(lenses, start=1):
            front = -np.asarray(laid["z"], dtype=float)
            at = lens_middle(laid) + front * float(wanted["ahead"])
            found.append(dict(wanted["light"], name=f"{wanted['kind']}_lamp_{number}",
                              at=[round(float(value), 4) for value in at]))
    return found


def laid_again(stage, place, data):
    """The seed's kit pieces of each `kit_moves` kind laid where the place's kit layout puts them now
    (tools/props/scene/earth_outside_kit.py, whose layout the seed was exported from): the n-th body and the n-th lens
    of the kind on the n-th laid piece, the seed's extra ones made inactive. How many moved and left out."""
    from pxr import Gf, UsdGeom
    if not data.get("kit_moves"):
        return {}
    sys.path.insert(0, str(REPO / "tools/props/scene"))
    import earth_outside_kit
    layout = earth_outside_kit.layout_of(place)["pieces"]
    done = {}
    for kind in data["kit_moves"]:
        laid = [piece for piece in layout if piece["kind"] == kind]
        seeded = [prim for prim in stage.Traverse() if prim.GetAttribute("score:kind").Get() == kind]
        number = lambda prim: int(prim.GetName().rsplit("_", 1)[1])  # noqa: E731 (the layout's order)
        for group in ([prim for prim in seeded if "_glow_" not in prim.GetName()],
                      [prim for prim in seeded if "_glow_" in prim.GetName()]):
            for index, prim in enumerate(sorted(group, key=number)):
                if index >= len(laid):
                    prim.SetActive(False)
                    continue
                piece = laid[index]
                rows = [list(piece[axis]) + [0.0] for axis in ("x", "y", "z")] + [list(piece["at"]) + [1.0]]
                xform = UsdGeom.Xformable(prim)
                xform.ClearXformOpOrder()
                xform.AddTransformOp().Set(Gf.Matrix4d(*[value for row in rows for value in row]))
        done[kind] = {"laid": len(laid), "seed": len(seeded)}
    return done


def lights_of(place, record):
    """The place's lights: its record's and the light data's lamps on its kit. A record lamp of the kit lamp's type
    within LENS_NEAR of it is that lamp (the record holds the launch's pad lamps since 2026-10-12): it keeps its own
    numbers and takes the kit lamp's shaft, and the kit lamp is not added."""
    lights = [dict(entry) for entry in record.get("lights", [])]
    added = []
    for lamp in kit_lamps(place, light_data(place)):
        near = [entry for entry in lights if entry["type"] == lamp["type"] and "at" in entry
                and np.linalg.norm(np.asarray(entry["at"]) - np.asarray(lamp["at"])) <= LENS_NEAR]
        if near:
            near[0].setdefault("shaft", lamp.get("shaft"))
        else:
            added.append(lamp)
    return lights + added


def own_lamps(stage, place):
    """Every sphere light under /<place>/Lights: [(path, world spot, shaped)]."""
    from pxr import UsdGeom, UsdLux
    cache = UsdGeom.XformCache()
    found = []
    lights = stage.GetPrimAtPath(f"/{place}/Lights")
    for prim in (lights.GetChildren() if lights else []):
        if prim.IsA(UsdLux.SphereLight):
            spot = np.asarray(cache.GetLocalToWorldTransform(prim).ExtractTranslation(), dtype=float)
            found.append((str(prim.GetPath()), spot, prim.HasAPI(UsdLux.ShapingAPI)))
    return found


def record_lamps(record):
    """The record's lamps (not its suns), each with its prim name as export gives it."""
    entries = record.get("lights", [])
    return [(name, entry) for name, entry in zip(scene.light_names(entries), entries) if entry["type"] != "sun"]


def placed_lamps(stage, place, record):
    """Each record lamp matched to a seed lamp (where it stands, or the nearest unmatched one of its kind within
    MOVE_MOST, which is moved), else written new; the record's suns written where the seed has no light at all.
    Returns what was done to each record light."""
    seeded = own_lamps(stage, place)
    lit = bool(stage.GetPrimAtPath(f"/{place}/Lights"))
    free = {path: (spot, shaped) for path, spot, shaped in seeded}
    done = []
    wanted = record_lamps(record)
    for name, entry in wanted:
        at = np.asarray(entry["at"], dtype=float)
        shaped = entry["type"] == "spot"
        same = [path for path, (spot, _) in free.items() if np.linalg.norm(spot - at) <= SAME_SPOT]
        if same:
            free.pop(same[0])
            done.append({"record": name, "path": same[0], "done": "kept"})
            continue
        near = sorted((np.linalg.norm(spot - at), path) for path, (spot, kind) in free.items() if kind == shaped)
        if near and near[0][0] <= MOVE_MOST:
            path = near[0][1]
            free.pop(path)
            moved(stage, path, entry)
            done.append({"record": name, "path": path, "done": f"moved {near[0][0]:.2f} m"})
            continue
        path = f"/{place}/Lights/{name}"
        if stage.GetPrimAtPath(path):
            path = f"/{place}/Lights/{name}_record"
        scene.write_light(stage, path, entry)
        done.append({"record": name, "path": path, "done": "added"})
    if not lit:
        suns = [(name, entry) for name, entry in zip(scene.light_names(record.get("lights", [])),
                                                     record.get("lights", [])) if entry["type"] == "sun"]
        for name, entry in suns:
            scene.write_light(stage, f"/{place}/Lights/{name}", entry)
            done.append({"record": name, "path": f"/{place}/Lights/{name}", "done": "added"})
    return done


def moved(stage, path, entry):
    """A seed light moved (and for a spot, turned and shaped) where the record puts it."""
    from pxr import Gf, UsdGeom, UsdLux
    light = UsdLux.SphereLight(stage.GetPrimAtPath(path))
    xform = UsdGeom.Xformable(light.GetPrim())
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(*map(float, entry["at"])))
    if entry["type"] == "spot":
        xform.AddOrientOp().Set(Gf.Quatf(scene.aim_turn(entry["at"], entry["aim"])))
        shaping = UsdLux.ShapingAPI.Apply(light.GetPrim())
        shaping.CreateShapingConeAngleAttr().Set(float(entry["angle"]))
        shaping.CreateShapingConeSoftnessAttr().Set(float(entry.get("softness", scene.SPOT_SOFTNESS)))


def earth_entries(record):
    """The record's Earth on its ball: (group root, kind, entry) for each structure or ground entry named earth."""
    return [(root, kind, entry) for group, root, kind in (("structure", "Structure", "structure"),
                                                         ("ground", "Terrain", "ground"))
            for entry in record.get(group, []) if entry.get("name") == "earth"]


def write_earth(stage, place, record, out):
    """The Earth's ball as the record lays it (turned to face the place) with NASA's surface: the seed's earth_face
    material, when it has one, pointed at the picture baked here."""
    from pxr import Sdf, UsdShade
    found = earth_entries(record)
    for root, kind, entry in found:
        scene.write_structure(stage, place, [entry], root=root, kind=kind, out=out)
    if not found:
        return 0
    shaders.earth.write(out / ASSETS / shaders.EARTH_PICTURE, shaders.EARTH_WIDTH)
    material = stage.GetPrimAtPath(f"/{place}/Looks/earth_face")
    picture = UsdShade.Shader(stage.GetPrimAtPath(f"/{place}/Looks/earth_face/picture"))
    picture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"../{ASSETS}/{shaders.EARTH_PICTURE}")
    for key, value in (("score:shader", "earth"),
                       ("score:from", "NASA Visible Earth: Blue Marble Next Generation (July 2004) and its cloud "
                                      "cover, baked by tools/usd/earth.py (the light stage's layer)")):
        material.CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
    return len(found)


def planned_ground(place):
    """The place's planned ground (tools/usd/ground.py, seated as its kit says), or None for a flat place."""
    kit = REPO / f"data/kit/{place}.json"
    on_seat = json.loads(kit.read_text()).get("on_seat", [0.0, 0.0]) if kit.exists() else [0.0, 0.0]
    return grounds.place_ground(place, on_seat)


def write_sky(stage, place, record, out):
    """The record's sky where the seed lacks it or drew it the old way: the environment and its stars and haze when
    the seed has none, the day dome, the sun's disc and the floodlights' shafts. What was written, by name."""
    from pxr import UsdGeom
    environment = record.get("environment") or {}
    done = {"earth": write_earth(stage, place, record, out)}
    if environment and not stage.GetPrimAtPath(f"/{place}/Environment"):
        scene.write_environment(stage, place, environment)
        scene.write_sky(stage, place, environment, out, planned_ground(place))
        done["environment"] = True
    if environment.get("sky_dome"):
        UsdGeom.Scope.Define(stage, f"/{place}/Sky")
        scene.write_sky_dome(stage, place, environment["sky_dome"], record.get("lights", []), out)
        done["sky_dome"] = True
    if any(entry["type"] == "sun" and not entry.get("name") for entry in record.get("lights", [])):
        done["sun_discs"] = shaders.sun_discs(stage, place, record.get("lights", []),
                                              lambda path, centre, radius: scene.sun_ball(stage, place, path, centre,
                                                                                         radius))
    if any(entry.get("shaft") for entry in record.get("lights", [])):
        UsdGeom.Scope.Define(stage, f"/{place}/Shafts")
        done["shafts"] = scene.write_shafts(stage, place, record.get("lights", []))
    return done


def pictures_moved(out, layer):
    """The pictures the writers baked into assets/textures moved into ASSETS, and the layer pointed at them."""
    baked = out / "assets/textures"
    if not baked.exists():
        return
    (out / ASSETS).mkdir(parents=True, exist_ok=True)
    text = layer.ExportToString()
    for picture in sorted(baked.iterdir()):
        shutil.move(str(picture), str(out / ASSETS / picture.name))
        text = text.replace(f"@../assets/textures/{picture.name}@", f"@../{ASSETS}/{picture.name}@")
    baked.rmdir()
    layer.ImportFromString(text)


def write(place, record, seed_folder, out):
    """The place's light layer over its seed, and what it holds (lamps.json's content): the record's lights with the
    light data's lamps among them, and the light data's glow on the place's sky."""
    from pxr import Sdf, Usd
    out = pathlib.Path(out)
    record = dict(record, lights=lights_of(place, record))
    (out / "layers").mkdir(parents=True, exist_ok=True)
    layer = Sdf.Layer.CreateNew(str(out / LAYER))
    composed = Sdf.Layer.CreateAnonymous(".usda")
    composed.subLayerPaths.append(layer.identifier)
    composed.subLayerPaths.append(str(pathlib.Path(seed_folder) / f"{place}.usda"))
    stage = Usd.Stage.Open(composed)
    stage.SetEditTarget(Usd.EditTarget(layer))
    moves = laid_again(stage, place, light_data(place))
    placed = placed_lamps(stage, place, record)
    sky = write_sky(stage, place, record, out)
    glow = light_data(place).get("glow")
    if glow:
        scene.write_glow(stage.GetPrimAtPath(f"/{place}/Environment"), glow)
        sky["glow"] = True
    pictures_moved(out, layer)
    layer.Save()
    lamps = [{"path": path, "spot": [round(float(value), 4) for value in spot], "shaped": shaped,
              "intensity": float(stage.GetPrimAtPath(path).GetAttribute("inputs:intensity").Get())}
             for path, spot, shaped in own_lamps(stage, place)]
    shafted = {entry["path"] for entry in placed
               if dict(record_lamps(record)).get(entry["record"], {}).get("shaft")}
    for lamp in lamps:
        lamp["shaft"] = lamp["path"] in shafted
    found = {"place": place, "lamps": lamps, "placed": placed, "sky": sky}
    return dict(found, moved=moves) if moves else found


def strengths(layer_path, place, scales):
    """Each lamp's intensity set to its seed intensity times its scale ({path: (intensity, scale)}), in the layer."""
    from pxr import Sdf
    layer = Sdf.Layer.FindOrOpen(str(layer_path))
    for path, (intensity, scale) in scales.items():
        spec = Sdf.CreatePrimInLayer(layer, path)
        attribute = spec.attributes.get("inputs:intensity") or Sdf.AttributeSpec(spec, "inputs:intensity",
                                                                                 Sdf.ValueTypeNames.Float)
        attribute.default = float(intensity * scale)
        held = spec.attributes.get("score:light:scale") or Sdf.AttributeSpec(spec, "score:light:scale",
                                                                            Sdf.ValueTypeNames.Float)
        held.default = float(scale)
    layer.Save()


def lamps_file(found, out):
    (pathlib.Path(out) / "lamps.json").write_text(json.dumps(found, indent=1) + "\n")
