"""The effects stage (experimental, PRD #6, until the owner reviews it): a place's effects record
(`data/effects/<place>.json`: what burns, vents and moves there, each entry with the game lines or the real footage it
was measured on) made into the place's OpenUSD effects layer, which the assembly stage puts into the place's stage.

    make     tools/usd/effects.py's write_layer on the record with the place's scene and motion records:
             layers/effects.usda and each emitter's baked particles under assets/effects/
    gates    attached  every emitter and light on a prim of the base (`on`) is that prim's child and keeps its place on
                       it through the prim's motion, and every emitter that follows a motion lets each particle out
                       where the moving prim stands at its birth (read off the composed stage, the seed's own layers
                       under the effects layer)
             footage   every check of the record's `footage` block: a measure of the baked particles at a moment after
                       lift-off (how far the cloud reaches out from the pad, how high it stands, how long the flame is,
                       how fine and how thick the particles are, how few lie loose at its edge as lone blobs) lies
                       within the range measured on real footage of
                       launches, in the rocket's heights
             light     the flame's light reaches the pad: from half a second after the engines light to two seconds
                       after lift-off it lights the pad round the rocket at least LIGHT_OVER times as much as the
                       place's own lamps do

Only places in STAGED have the row; the other places keep the effects layer of their seed. A place's effects are
modelled on real footage first (the owner's rule): many fine particles tied to the world, never thinned to draw
cheaper.
"""
import json
import pathlib
import sys

import numpy as np

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import effects as effect_layer  # noqa: E402

STAGED = ("launch",)
# How far an emitter on a moving prim may drift from its place on it, metres.
DRIFT_MOST = 0.01
# How often the composed stage is read along a motion and an event, seconds.
READ_EVERY = 0.5
# The flame's light on the pad against the place's own lamps: in the night footage (data/effects/launch.json's
# footage sources) the apron round the flame is lit far brighter than the floodlit tower beside it.
LIGHT_OVER = 2.0
# The pad round the rocket the light is judged on: rings this far out from its middle, eight spots each, metres.
PAD_RINGS = (10.0, 20.0, 30.0)
LIGHT_FROM_IGNITION = 0.5
LIGHT_AFTER_LIFT = 2.0
# Particles of a cloud at least this thick (one behind another) make it read as a cloud, not dots.
LAYERS = 3
# A particle thinner than this (its opacity) does not show: one just born or dying between two baked samples.
SEEN = 0.02


def files(place):
    """What the stage reads: the place's effects, scene and motion records, its kit and the planned grounds
    (tools/usd/effects.py's place_ground), and its seed stage (the gates compose the layer over it)."""
    found = {"record": "{data}/effects/{place}.json", "scene": "{data}/scene/{place}.json",
             "kit": "{data}/kit/{place}.json", "grounds": "{data}/ground", "seed": "{seeds}/usd-r3/{place}"}
    if (REPO / f"data/motion/{place}.json").exists():
        found["motion"] = "{data}/motion/{place}.json"
    return found


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


def motions_of(inputs):
    return read_json(inputs["motion"]) if "motion" in inputs else None


def make(inputs, out, seed, params):
    """The place's effects layer and its baked particles, from its records."""
    place = pathlib.Path(inputs["seed"]).name
    record = read_json(inputs["record"])
    held = effect_layer.write_layer(place, record, out, effect_layer.place_ground(place), read_json(inputs["scene"]),
                                    motions_of(inputs))
    (out / "held.json").write_text(json.dumps({"place": place, "particles": held}, indent=1))


# --- the composed stage -------------------------------------------------------------------------------------------

def composed(output, inputs):
    """The effects layer over the place's seed stage (its edit, stage layers and base), opened as one stage."""
    from pxr import Sdf, Usd
    seed = pathlib.Path(inputs["seed"])
    root = Sdf.Layer.CreateAnonymous(".usda")
    root.subLayerPaths = [str(pathlib.Path(output) / effect_layer.LAYER), str(seed / f"{seed.name}.usda")]
    return Usd.Stage.Open(root)


def place_of(inputs):
    return pathlib.Path(inputs["seed"]).name


def where(stage, path, seconds):
    """A prim's place in the world at a second of the stage."""
    from pxr import UsdGeom
    matrix = UsdGeom.Xformable(stage.GetPrimAtPath(path)).ComputeLocalToWorldTransform(seconds * effect_layer.RATE)
    return np.asarray(matrix.ExtractTranslation(), dtype=float)


def live(stage, path, seconds):
    """The live particles of an emitter's points at a second of the stage: their world spots and widths."""
    from pxr import UsdGeom
    prim = stage.GetPrimAtPath(path)
    grains = UsdGeom.Points(prim)
    code = seconds * effect_layer.RATE
    spots = np.asarray(grains.GetPointsAttr().Get(code), dtype=float)
    widths = np.asarray(grains.GetWidthsAttr().Get(code), dtype=float)
    matrix = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(code))
    world = spots @ matrix[:3, :3] + matrix[3, :3]
    scale = float(np.linalg.norm(matrix[0, :3]))
    alive = widths > 0
    return world[alive], widths[alive] * scale


def seen(stage, path, seconds):
    """The particles of an emitter's points that show at a second of the stage (thicker than SEEN; one just born
    or dying between two samples is nearly nothing): their world spots and widths."""
    from pxr import UsdGeom
    grains = UsdGeom.Points(stage.GetPrimAtPath(path))
    code = seconds * effect_layer.RATE
    widths = np.asarray(grains.GetWidthsAttr().Get(code), dtype=float)
    thickness = np.asarray(UsdGeom.PrimvarsAPI(grains).GetPrimvar("displayOpacity").Get(code), dtype=float)
    spots, sizes = live(stage, path, seconds)
    shows = thickness[widths > 0] > SEEN
    return spots[shows], sizes[shows]


def points_path(place, entry):
    """Where an emitter's points stand in the stage (tools/usd/effects.py's layout)."""
    placement = entry["placement"]
    holder = f"/{place}/{placement['on']}" if "on" in placement else f"/{place}/Effects"
    return f"{holder}/{entry['name']}/{entry['name']}_points"


def motion_span(motions, name):
    """(motion, its first and last second of the stage)."""
    motion = effect_layer.motion_named(motions, name)
    return motion, float(motion["start"]), float(motion["start"]) + float(motion["length"])


def moments(first, last):
    return np.arange(first, last + 1e-9, READ_EVERY)


# --- attached -----------------------------------------------------------------------------------------------------

def riding_drift(stage, place, holder, path, motions):
    """How far a prim riding `holder` strays from its place on it over every motion of the holder (metres), and how
    far the holder moves meanwhile; (0, 0) when nothing moves it."""
    own = [motion for motion in (motions or {}).get("motions", []) if motion["prim"] == f"/{place}/{holder}"]
    drift, moved = 0.0, 0.0
    for motion in own:
        first, last = float(motion["start"]), float(motion["start"]) + float(motion["length"])
        start_offset = where(stage, path, first) - where(stage, f"/{place}/{holder}", first)
        for seconds in moments(first, last):
            offset = where(stage, path, seconds) - where(stage, f"/{place}/{holder}", seconds)
            drift = max(drift, float(np.linalg.norm(offset - start_offset)))
        moved = max(moved, float(np.linalg.norm(where(stage, f"/{place}/{holder}", last)
                                                - where(stage, f"/{place}/{holder}", first))))
    return drift, moved


def newborn_miss(stage, place, entry, motions):
    """How far the particles a following emitter lets out stand from where its motion's prim is at their birth, past
    what the emitter's size and their first moment's flight allow (metres; 0 when every one is within)."""
    motion, _, _ = motion_span(motions, entry["placement"]["follows"])
    path = points_path(place, entry)
    rate = effect_layer.samples_of(entry)
    first, last = (float(value) for value in entry["once"])
    reach = (effect_layer.emitter_size(entry["emitter"])[0] + max(entry.get("speed", (0.0, 0.0))) / rate
             + float(entry["size"]) * max(entry.get("scale", (1.0, 1.0))))
    offset = np.asarray(entry["placement"].get("offset", (0.0, 0.0, 0.0)), dtype=float)
    worst = 0.0
    for seconds in moments(first + 1.0 / rate, last):
        from pxr import UsdGeom
        grains = UsdGeom.Points(stage.GetPrimAtPath(path))
        now = np.asarray(grains.GetWidthsAttr().Get(seconds * effect_layer.RATE))
        before = np.asarray(grains.GetWidthsAttr().Get((seconds - 1.0 / rate) * effect_layer.RATE))
        born = (now > 0) & (before == 0)
        if not born.any():
            continue
        spots, _ = live(stage, path, seconds)
        spots = spots[born[now > 0]]
        prim = where(stage, motion["prim"], seconds) + offset
        # Born within the last sample: the prim stood up to one sample's travel back.
        travel = float(np.linalg.norm(prim - where(stage, motion["prim"], seconds - 1.0 / rate) - offset))
        worst = max(worst, float(np.linalg.norm(spots - prim, axis=1).max()) - reach - travel)
    return max(worst, 0.0)


def judge_attached(output, inputs, evidence):
    """Pass when everything on a moving prim moves with it and every following emitter lets out at its prim."""
    stage, place, record = composed(output, inputs), place_of(inputs), read_json(inputs["record"])
    motions = motions_of(inputs)
    faults, measures = [], {"drift": 0.0, "miss": 0.0, "carried": 0.0}
    riders = [(entry["name"], entry["placement"]["on"]) for entry in record["effects"] if "on" in entry["placement"]]
    riders += [(light["name"], light["on"]) for light in record.get("lights", [])]
    for name, holder in riders:
        path = f"/{place}/{holder}/{name}"
        if not stage.GetPrimAtPath(path):
            faults.append(f"{name}: not on {holder} ({path} missing)")
            continue
        drift, moved = riding_drift(stage, place, holder, path, motions)
        measures["drift"] = max(measures["drift"], round(drift, 4))
        measures["carried"] = max(measures["carried"], round(moved, 1))
        if drift > DRIFT_MOST:
            faults.append(f"{name}: strays {drift:.3f} m from its place on {holder} as it moves {moved:.0f} m")
    for entry in [entry for entry in record["effects"] if "follows" in entry["placement"]]:
        miss = newborn_miss(stage, place, entry, motions)
        measures["miss"] = max(measures["miss"], round(miss, 3))
        if miss > 0:
            faults.append(f"{entry['name']}: lets particles out {miss:.2f} m past where its prim stands")
    followers = sum("follows" in entry["placement"] for entry in record["effects"])
    if not riders and not followers:
        return checks.Verdict("attached", checks.UNKNOWN, "nothing in the record rides or follows a moving prim")
    reason = (f"{len(faults)} faults over {len(riders)} riders and {followers} following emitters" if faults else
              f"{len(riders)} riders keep their place over {measures['carried']:.0f} m of their prim's travel and "
              f"{followers} following emitters let out where their prim stands")
    return checks.Verdict("attached", checks.FAIL if faults else checks.PASS, reason, measures,
                          {"drift": "lower", "miss": "lower"}, tuple(faults))


# --- footage ------------------------------------------------------------------------------------------------------

def rocket_of(record, scene, motions):
    """The footage block's rocket: its height (metres), its rest spot and its motion."""
    named = record["footage"]["rocket"]
    found = next(item for item in scene["objects"] if item["name"] == named["object"])
    motion = effect_layer.motion_named(motions, named["motion"])
    return float(found["height"]), np.asarray(found["at"], dtype=float), motion


def lift_second(motion):
    return float(motion["start"]) + float(motion["climb"]["lift"])


def gathered(stage, place, record, names, seconds):
    """Every particle of the named emitters that shows at a second: world spots and widths."""
    entries = {entry["name"]: entry for entry in record["effects"]}
    spots, widths = [np.zeros((0, 3))], [np.zeros(0)]
    for name in names:
        found = seen(stage, points_path(place, entries[name]), seconds)
        spots.append(found[0])
        widths.append(found[1])
    return np.concatenate(spots), np.concatenate(widths)


def reach(spots, widths, rest):
    """How far the particles reach out from the rocket's middle along the ground (95th share, their edges), m."""
    out = np.hypot(spots[:, 0] - rest[0], spots[:, 2] - rest[2]) + widths / 2
    return float(np.percentile(out, 95))


def height(spots, widths, rest):
    """How high the particles stand over the rocket's foot (95th share, their tops), metres."""
    return float(np.percentile(spots[:, 1] + widths / 2 - rest[1], 95))


def flame_length(spots, nozzle):
    """How far the flame reaches under the rocket's foot (95th share), metres."""
    return float(np.percentile(nozzle[1] - spots[:, 1], 95))


def layering(spots, widths, rest):
    """The share of the cloud's side outline (seen across x, cells half a median particle wide) that at least LAYERS
    particles cover one behind another."""
    cell = max(float(np.median(widths)) / 2, 0.05)
    across, up = (spots[:, 0] - rest[0]) / cell, (spots[:, 1] - rest[1]) / cell
    low = np.floor([across.min() - widths.max() / cell, up.min() - widths.max() / cell]).astype(int)
    shape = (np.ceil([across.max() + widths.max() / cell, up.max() + widths.max() / cell]).astype(int) - low) + 1
    cover = np.zeros(shape, dtype=np.int32)
    for column, row, width in zip(across - low[0], up - low[1], widths / 2 / cell):
        first = (max(int(column - width), 0), max(int(row - width), 0))
        lasts = (min(int(column + width) + 1, shape[0]), min(int(row + width) + 1, shape[1]))
        grid_x, grid_y = np.mgrid[first[0]:lasts[0], first[1]:lasts[1]]
        cover[first[0]:lasts[0], first[1]:lasts[1]] += ((grid_x + 0.5 - column) ** 2 + (grid_y + 0.5 - row) ** 2
                                                        <= width * width)
    outline = cover > 0
    return float((cover[outline] >= LAYERS).mean()) if outline.any() else 0.0


def loose(spots, widths):
    """The share of the particles that touch no other (the nearest one's middle farther than their own width): the
    lone blobs a cloud in the footage never shows at its edge."""
    from scipy.spatial import cKDTree
    if len(spots) < 2:
        return 1.0
    nearest, _ = cKDTree(spots).query(spots, k=2)
    return float((nearest[:, 1] > widths).mean())


def measured(check, stage, place, record, rocket):
    """One footage check's measure at its moment, in the rocket's heights (fineness and layering as shares)."""
    tall, rest, motion = rocket
    seconds = lift_second(motion) + float(check["after_lift"])
    spots, widths = gathered(stage, place, record, check["emitters"], seconds)
    if not len(spots):
        return None
    if check["measure"] == "reach":
        return reach(spots, widths, rest) / tall
    if check["measure"] == "height":
        return height(spots, widths, rest) / tall
    if check["measure"] == "flame_length":
        return flame_length(spots, where(stage, motion["prim"], seconds)) / tall
    if check["measure"] == "fineness":
        return float(np.median(widths)) / (2 * reach(spots, widths, rest))
    if check["measure"] == "layering":
        return layering(spots, widths, rest)
    if check["measure"] == "loose":
        return loose(spots, widths)
    raise ValueError(f"no footage measure {check['measure']}")


def judge_footage(output, inputs, evidence):
    """Pass when every footage check of the record measures within its range."""
    record = read_json(inputs["record"])
    if "footage" not in record:
        return checks.Verdict("footage", checks.UNKNOWN, "the record names no footage to measure its effects on")
    stage, place = composed(output, inputs), place_of(inputs)
    rocket = rocket_of(record, read_json(inputs["scene"]), motions_of(inputs))
    faults, measures, found = [], {}, []
    for check in record["footage"]["checks"]:
        value = measured(check, stage, place, record, rocket)
        low, high = check["range"]
        measures[check["name"]] = None if value is None else round(value, 4)
        line = f"{check['name']}: {'nothing alive' if value is None else f'{value:.3f}'} (footage {low} to {high})"
        found.append(line)
        if value is None or not low <= value <= high:
            faults.append(line)
    reason = (f"{len(faults)} of {len(found)} measures lie outside the footage's ranges" if faults
              else f"all {len(found)} measures lie within the footage's ranges")
    return checks.Verdict("footage", checks.FAIL if faults else checks.PASS, reason, measures, {},
                          tuple(faults or found))


# --- light --------------------------------------------------------------------------------------------------------

def lamp_light(stage, path, spot, seconds):
    """What a sphere light of the stage gives a spot of level ground facing up at a second (its intensity over the
    distance squared times the slant; nothing outside a cone it is shaped to)."""
    from pxr import UsdLux
    prim = stage.GetPrimAtPath(path)
    lamp = UsdLux.SphereLight(prim)
    matrix = np.asarray(UsdLux.SphereLight(prim).ComputeLocalToWorldTransform(seconds * effect_layer.RATE))
    way = spot - matrix[3, :3]
    distance = float(np.linalg.norm(way))
    slant = max(0.0, -way[1] / distance)
    if prim.HasAPI(UsdLux.ShapingAPI):
        aim = -matrix[2, :3] / np.linalg.norm(matrix[2, :3])
        cone = float(UsdLux.ShapingAPI(prim).GetShapingConeAngleAttr().Get())
        if np.degrees(np.arccos(np.clip(np.dot(aim, way / distance), -1.0, 1.0))) > cone:
            return 0.0
    return float(lamp.GetIntensityAttr().Get(seconds * effect_layer.RATE)) * slant / distance ** 2


def pad_spots(rest):
    """Spots of the pad round the rocket's foot: PAD_RINGS out, eight round each."""
    turns = np.radians(np.arange(8) * 45.0)
    return [rest + np.array([ring * np.cos(turn), 0.0, ring * np.sin(turn)]) for ring in PAD_RINGS for turn in turns]


def judge_light(output, inputs, evidence):
    """Pass when the flame's light lights the pad at least LIGHT_OVER times the place's own lamps, from just after
    the engines light to just after lift-off."""
    from pxr import UsdLux
    record = read_json(inputs["record"])
    if not record.get("lights"):
        return checks.Verdict("light", checks.UNKNOWN, "the record gives the effects no light of their own")
    stage, place = composed(output, inputs), place_of(inputs)
    tall, rest, motion = rocket_of(record, read_json(inputs["scene"]), motions_of(inputs))
    flames = [f"/{place}/{light['on']}/{light['name']}" for light in record["lights"]]
    lamps = [str(prim.GetPath()) for prim in stage.Traverse()
             if prim.IsA(UsdLux.SphereLight) and str(prim.GetPath()) not in flames]
    worst, faults = None, []
    for seconds in moments(float(motion["start"]) + LIGHT_FROM_IGNITION, lift_second(motion) + LIGHT_AFTER_LIFT):
        for spot in pad_spots(rest):
            flame = sum(lamp_light(stage, path, spot, seconds) for path in flames)
            own = sum(lamp_light(stage, path, spot, seconds) for path in lamps)
            ratio = flame / own if own > 0 else float("inf")
            worst = ratio if worst is None else min(worst, ratio)
            if ratio < LIGHT_OVER:
                faults.append(f"{seconds:.1f} s, ({spot[0]:.0f}, {spot[2]:.0f}): the flame lights it {ratio:.2f} "
                              "times the lamps")
    reason = (f"{len(faults)} pad spots and moments lit under {LIGHT_OVER} times the lamps" if faults else
              f"the flame lights the pad at least {worst:.1f} times the place's {len(lamps)} lamps from ignition to "
              "lift-off")
    return checks.Verdict("light", checks.FAIL if faults else checks.PASS, reason,
                          {"least over the lamps": round(float(worst), 3)}, {"least over the lamps": "higher"},
                          tuple(faults[:20]))


def layer_faults(folder):
    """The effects layer and every clip it plays are there."""
    folder = pathlib.Path(folder)
    if not (folder / effect_layer.LAYER).exists():
        return [f"no {effect_layer.LAYER}"]
    held = read_json(folder / "held.json")["particles"] if (folder / "held.json").exists() else {}
    return [f"{name} has no baked clip" for name in held
            if not (folder / effect_layer.ASSETS / f"{name}.usdc").exists()] or ([] if held else ["no emitter"])


LAYER = contracts.Contract("effects-layer", 1, layer_faults, {"length": "metre", "up axis": "Y", "time": "second"})
CHECKS = (checks.Check("attached", judge_attached), checks.Check("footage", judge_footage),
          checks.Check("light", judge_light))
