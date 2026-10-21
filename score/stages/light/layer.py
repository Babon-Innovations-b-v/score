"""A place's light layer, `layers/light.usda`, written over its seed stage with tools/usd/scene.py's own writers, so
the sky and the lamps the assembly shows are today's records' and not the round-three export's:

    lamps     every lamp of the place (a sphere light under /<place>/Lights) as the seed has it, moved where its
              scene record now puts it (a light of the record whose spot the seed does not hold takes the nearest
              unmatched seed light of its kind within MOVE_MOST, else it is added); its strength stays the seed's here
              and is set by the light stage from the per-lamp passes (strengths)
    sky       the environment concept's physics overhead at the scene's site at its scene time (sky.py): each light
              a distant light from its direction, each shining body's disc and every other body a ball at its true
              direction and size, each backdrop; the old sky of the seed and the record turned off (its suns, sun
              discs, Moon pictures, star field, worlds hung as structure); and the air the record holds where the
              seed has none: the environment and its haze, the day dome its air scatters (mars_sky.py) from the
              physics' brightest light, the floodlights' shafts

The writers draw into a stage made of the light layer over the seed (its edit target the light layer), so they find
the seed's library and write only the layer. Pictures they bake go into `assets/light/`, never `assets/textures/`,
where the seed's own pictures of the same names lie.

    write(place, record, seed_folder, out, kept) -> {"lamps": [...], "sky": {...}}
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

from score.stages.light import sky  # noqa: E402

LAYER = "layers/light.usda"
ASSETS = "assets/light"
# How far a record light may stand from the seed light it moves (the square's floodlight lamps moved onto their
# lenses' middles, 2026-10-11, about 1.5 m).
MOVE_MOST = 5.0
# Two spots this close are one light.
SAME_SPOT = 0.05
# How near a record lamp stands to a kit lamp of the light data for the two to be one lamp, metres.
LENS_NEAR = 1.0
# A mesh no side of which is over this is small enough to be a lamp's fixture, metres; a freed lamp stands this far clear of it.
FIXTURE_MOST = 1.5
FIXTURE_GAP = 0.05
# A fixture whose solid parts stop this share of a lamp's ways out encloses it (RAYS ways tried).
ENCLOSED = 0.9
RAYS = 256


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
    MOVE_MOST, which is moved), else written new (the sky's lights are the physics', sky.py). Returns what was done
    to each record lamp."""
    seeded = own_lamps(stage, place)
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


def fixture_boxes(stage, place):
    """[(path, low, high)] of every small drawn mesh (no side over FIXTURE_MOST) of the place: a lamp's fixture."""
    from pxr import Usd, UsdGeom
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    found = []
    for prim in stage.GetPrimAtPath(f"/{place}").GetAllChildren():
        if prim.GetName() in ("Lights", "Sky", "Shafts", "Places"):
            continue
        for mesh in Usd.PrimRange(prim):
            if mesh.IsA(UsdGeom.Mesh):
                box = cache.ComputeWorldBound(mesh).ComputeAlignedRange()
                low, high = np.array(box.GetMin()), np.array(box.GetMax())
                if not box.IsEmpty() and np.all(high - low <= FIXTURE_MOST):
                    found.append((str(mesh.GetPath()), low, high))
    return found


def world_mesh(stage, path):
    """A drawn mesh prim as a trimesh in the stage's frame (its faces fanned into triangles)."""
    import trimesh
    from pxr import UsdGeom
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath(path))
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=float)
    counts, indices = mesh.GetFaceVertexCountsAttr().Get(), np.asarray(mesh.GetFaceVertexIndicesAttr().Get())
    faces, start = [], 0
    for count in counts:
        faces += [(indices[start], indices[start + corner], indices[start + corner + 1]) for corner in range(1, count - 1)]
        start += count
    matrix = np.asarray(UsdGeom.XformCache().GetLocalToWorldTransform(mesh.GetPrim()), dtype=float)
    return trimesh.Trimesh(points @ matrix[:3, :3] + matrix[3, :3], np.asarray(faces), process=False)


def blocked_share(spot, meshes):
    """The share of RAYS ways out from a spot (spread evenly over the sphere) that hit one of the meshes."""
    if not meshes:
        return 0.0
    import trimesh
    turn = np.pi * (3.0 - np.sqrt(5.0)) * np.arange(RAYS)
    height = 1.0 - 2.0 * (np.arange(RAYS) + 0.5) / RAYS
    ways = np.column_stack([np.sqrt(1.0 - height ** 2) * np.cos(turn), height, np.sqrt(1.0 - height ** 2) * np.sin(turn)])
    hit = trimesh.util.concatenate(meshes).ray.intersects_any(np.repeat([spot], RAYS, axis=0), ways)
    return float(np.mean(hit))


def out_of(stage, path, spot, way, low, high):
    """A lamp set FIXTURE_GAP past a box (low, high) along a way from its spot; where it stands now."""
    from pxr import Gf, UsdGeom
    way = way / np.linalg.norm(way)
    steps = [((high if step > 0 else low)[axis] - spot[axis]) / step for axis, step in enumerate(way) if abs(step) > 1e-9]
    out = spot + way * (min(steps) + FIXTURE_GAP)
    xform = UsdGeom.Xformable(stage.GetPrimAtPath(path))
    next(op for op in xform.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeTranslate).Set(
        Gf.Vec3d(*map(float, out)))
    return out


def lamps_through_fixtures(stage, place):
    """Each lamp standing inside a small mesh (its fixture: the stairwell's caged bulkheads held all seven, and their
    cage and lens took nearly all their light, 2026-10-13), by measure: where the fixture's solid parts (its meshes
    not named glow) stop at least ENCLOSED of the ways out, the lamp moves out of the whole fixture, FIXTURE_GAP clear,
    toward its lens where it has one, else toward the place's middle; where they do not, a lamp behind a lens stands
    just outside the lens, inside the rest of its fixture, so the lens lets its light through as clear glass does (the
    library's clear glass stops 2%; Cycles cannot pass light through a lens that also glows) and the cage or shade
    still shapes it; a lamp in an open fixture with no lens stays. {lamp path: {rule, blocked, moved}}."""
    from pxr import Usd, UsdGeom
    boxes = fixture_boxes(stage, place)
    middle = np.array(UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(
        stage.GetPrimAtPath(f"/{place}")).ComputeAlignedRange().GetMidpoint())
    found = {}
    for path, spot, _ in own_lamps(stage, place):
        holders = [(name, low, high) for name, low, high in boxes
                   if np.all(spot >= low - 1e-3) and np.all(spot <= high + 1e-3)]
        if not holders:
            continue
        bodies = [(name, low, high) for name, low, high in holders if "glow" not in name]
        lenses = [(name, low, high) for name, low, high in holders if "glow" in name]
        blocked = blocked_share(spot, [world_mesh(stage, name) for name, _, _ in bodies])
        whole_low = np.min([low for _, low, _ in holders], axis=0)
        whole_high = np.max([high for _, _, high in holders], axis=0)
        lens_middle = (lenses[0][1] + lenses[0][2]) / 2 if lenses else None
        way = (lens_middle - (whole_low + whole_high) / 2) if lenses else (middle - spot)
        if np.linalg.norm(way) < 1e-6:
            way = middle - spot
        if blocked >= ENCLOSED:
            out = out_of(stage, path, spot, way, whole_low, whole_high)
            rule = "moved out of its fixture"
        elif lenses:
            out = out_of(stage, path, spot, way, lenses[0][1], lenses[0][2])
            rule = "set just outside its lens"
        else:
            out, rule = spot, "open fixture, kept"
        found[path] = {"rule": rule, "blocked": round(blocked, 3), "moved": round(float(np.linalg.norm(out - spot)), 3)}
    return found


def earth_face_baked(stage, place, written, out):
    """NASA's surface (shaders.earth_look's picture) on every body of the physics' sky painted earth_face, baked into
    the layer's pictures and pointed at, the seed's own earth_face picture, when it has one, left unread; how many."""
    from pxr import Sdf, UsdShade
    faced = [body for body in (written or {}).get("bodies", []) if body["surface"] == "earth_face"]
    material = stage.GetPrimAtPath(f"/{place}/Looks/earth_face")
    if not faced or not material:
        return 0
    if (out / "assets/textures" / shaders.EARTH_PICTURE).exists():
        return len(faced)  # earth_look made the look in this layer and baked it there (pictures_moved moves it)
    shaders.earth.write(out / ASSETS / shaders.EARTH_PICTURE, shaders.EARTH_WIDTH)
    picture = UsdShade.Shader(stage.GetPrimAtPath(f"/{place}/Looks/earth_face/picture"))
    picture.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(f"../{ASSETS}/{shaders.EARTH_PICTURE}")
    for key, value in (("score:shader", "earth"),
                       ("score:from", "NASA Visible Earth: Blue Marble Next Generation (July 2004) and its cloud "
                                      "cover, baked by tools/usd/earth.py (the light stage's layer)")):
        material.CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
    return len(faced)


def planned_ground(place):
    """The place's planned ground (tools/usd/ground.py, seated as its kit says), or None for a flat place."""
    kit = REPO / f"data/kit/{place}.json"
    on_seat = json.loads(kit.read_text()).get("on_seat", [0.0, 0.0]) if kit.exists() else [0.0, 0.0]
    return grounds.place_ground(place, on_seat)


def write_sky(stage, place, record, out, kept=None):
    """The scene's sky from the environment concept's physics (sky.py: what is overhead at its site at its scene time,
    from its kept sky inputs; the old sky turned off first), and the air the record holds where the seed lacks it: the
    environment and its haze when the seed has none, the day dome scattered from the physics' brightest light, the
    floodlights' shafts. What was written, by name; `physics` None while the scene's sky is not known."""
    from pxr import UsdGeom
    environment = {key: value for key, value in (record.get("environment") or {}).items() if key != "stars"}
    seen = sky.seen_of(kept)
    done = {"retired": sky.retired(stage, place), "physics": sky.write(stage, place, seen, out) if seen else None}
    done["earth"] = earth_face_baked(stage, place, done["physics"], out)
    if environment and not stage.GetPrimAtPath(f"/{place}/Environment"):
        scene.write_environment(stage, place, environment)
        scene.write_sky(stage, place, environment, out, planned_ground(place))
        done["environment"] = True
    if environment.get("sky_dome") and seen and seen["lights"]:
        UsdGeom.Scope.Define(stage, f"/{place}/Sky")
        scene.write_sky_dome(stage, place, environment["sky_dome"], sky.sun_entries(seen), out)
        done["sky_dome"] = True
    lights = record.get("lights", [])
    if any(entry.get("shaft") for entry in lights):
        UsdGeom.Scope.Define(stage, f"/{place}/Shafts")
        done["shafts"] = scene.write_shafts(stage, place, lights)
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


def write(place, record, seed_folder, out, kept=None):
    """The place's light layer over its seed, and what it holds (lamps.json's content): the record's lamps with the
    light data's lamps among them, its sky from the physics (`kept`: its kept sky inputs, scene_sky.py), and the light
    data's glow on the place's sky."""
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
    fixtures = lamps_through_fixtures(stage, place)
    sky_written = write_sky(stage, place, record, out, kept)
    glow = light_data(place).get("glow")
    if glow:
        scene.write_glow(stage.GetPrimAtPath(f"/{place}/Environment"), glow)
        sky_written["glow"] = True
    pictures_moved(out, layer)
    layer.Save()
    lamps = [{"path": path, "spot": [round(float(value), 4) for value in spot], "shaped": shaped,
              "intensity": float(stage.GetPrimAtPath(path).GetAttribute("inputs:intensity").Get())}
             for path, spot, shaped in own_lamps(stage, place)]
    shafted = {entry["path"] for entry in placed
               if dict(record_lamps(record)).get(entry["record"], {}).get("shaft")}
    for lamp in lamps:
        lamp["shaft"] = lamp["path"] in shafted
    found = {"place": place, "lamps": lamps, "placed": placed, "sky": sky_written}
    if fixtures:
        found["fixtures"] = fixtures
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
