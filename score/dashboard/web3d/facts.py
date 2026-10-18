"""What the web copy's sidecar says about a place's stage beyond its meshes: the OpenUSD layer each prim comes from, the
stage's layers in order, its lamps, its effects as points, its movers' motion, its sounds, and the film's cameras.
Read with usd-core from the linked stage, nothing written."""
import base64
import json
import pathlib

import numpy as np

# Where the neighbours stage keeps each other place it shows (score/stages/assembly/neighbours.py), and the layer the
# viewer lists such a place's objects under, one per place ("place far_city").
NEIGHBOURS = "places"
PLACE_LAYER = "place"
# The layers of a place's stage that may define objects, by the file stem in layers/ (score/stages/assembly/record.py).
LAYER_STEMS = ("edit", "characters", "sound", "light", "motion", "effects", "crops", "machines", "settle", "ground",
               "base")
# An effect's points at most: a thicker cloud is thinned evenly (the launch's plume holds tens of thousands).
EFFECT_POINTS = 20000
# An effect's samples looked at for its fullest moment (the launch's flame holds 11,252: reading every one took
# minutes).
LOOKED_AT = 200
# A mover's key is dropped where the keys either side, blended, put it within this much: metres of its move, and
# the change of its turn's matrix entries (about 0.3 degrees).
MOTION_METRES = 0.01
MOTION_TURN = 0.005


def shown_place(prim):
    """The other place a prim belongs to (under /<place>/Places/<other>, a neighbour the scene shows), or None."""
    parts = prim.GetPath().pathString.split("/")
    return parts[3] if len(parts) > 3 and parts[2] == "Places" else None


def layer_of(prim):
    """The layer the viewer lists a prim under: "place <other>" for another place the scene shows, else the layer of
    the place's stage that defines it (or its nearest ancestor that one defines), the weakest sublayer spec that is a
    `def`; "base" when none says."""
    from pxr import Sdf
    shown = shown_place(prim)
    if shown:
        return f"{PLACE_LAYER} {shown}"
    while prim and prim.IsValid():
        defining = [spec.layer for spec in prim.GetPrimStack()
                    if spec.specifier == Sdf.SpecifierDef and "/layers/" in spec.layer.identifier]
        if defining:
            stem = pathlib.PurePosixPath(defining[-1].identifier).stem
            return stem if stem in LAYER_STEMS else "base"
        prim = prim.GetParent()
    return "base"


def switched_off(root):
    """The prims under a shown place's root that the showing stage makes inactive (its ground, its sky, its moon),
    as paths relative to that root."""
    from pxr import Usd
    return sorted(str(prim.GetPath().MakeRelativePath(root.GetPath()))
                  for prim in Usd.PrimRange(root, Usd.PrimAllPrimsPredicate) if not prim.IsActive())


def shown_places(stage, elsewhere, doubled, time):
    """The other places the stage shows: [{place, copy (whether the viewer loads its own web copy), seat (its root's
    place in the world, 16 numbers row by row), hidden (what of that copy the showing stage leaves out: its
    switched-off prims and its Outside parts in `doubled`)}]."""
    from pxr import UsdGeom
    places = stage.GetDefaultPrim().GetChild("Places")
    found = []
    for root in places.GetChildren() if places.IsValid() else []:
        seat = np.array(UsdGeom.Xformable(root).ComputeLocalToWorldTransform(time))
        found.append({"place": root.GetName(), "copy": root.GetName() in elsewhere,
                      "seat": np.round(seat, 5).ravel().tolist(),
                      "hidden": [*switched_off(root), *(f"Outside/{name}" for name in sorted(doubled))]})
    return found


def stage_layers(stage):
    """The place's own layers by file stem, strongest first, as its root layer lists them."""
    return [pathlib.PurePosixPath(path).stem for path in stage.GetRootLayer().subLayerPaths]


def lamps(export, stage, time):
    """Every lamp of the stage (the place's and the places it shows) as the viewer lights it (export.light_entry),
    with whether the game lets it cast shadows."""
    found = []
    for prim in stage.Traverse():
        entry = export.light_entry(prim, time)
        if entry:
            casts = prim.GetAttribute("score:game:shadows")
            found.append(dict(entry, shadows=bool(casts.Get()) if casts and casts.HasValue() else True,
                              layer=layer_of(prim)))
    return found


def glow(stage):
    """The game's glow over the picture, which the films bloom (their sky dome's score:glow_threshold and
    score:glow_intensity): {threshold, intensity}, or None when the place has none."""
    dome = stage.GetDefaultPrim().GetChild("Environment")
    if not dome.IsValid() or not dome.HasAttribute("score:glow_threshold"):
        return None
    return {key: float(dome.GetAttribute(f"score:glow_{key}").Get() or 0.0) for key in ("threshold", "intensity")}


def sounds(stage):
    """How many sounds the stage places (UsdMedia SpatialAudio prims)."""
    return sum(1 for prim in stage.Traverse() if prim.GetTypeName() == "SpatialAudio")


def fullest_time(points):
    """The time code at which an effect's points are most (of at most LOOKED_AT samples spread over its time), None
    when they are not sampled."""
    codes = points.GetPointsAttr().GetTimeSamples()
    if not codes:
        return None
    codes = codes[::max(1, len(codes) // LOOKED_AT)]
    return max(codes, key=lambda code: len(points.GetPointsAttr().Get(code) or []))


def packed_points(placed):
    """Points (n, 3) as the sidecar carries them: their box and each point's place in it as three 16-bit numbers
    (little-endian, base64): {low, high, count, data}."""
    low, high = placed.min(axis=0), placed.max(axis=0)
    steps = np.round((placed - low) / np.maximum(high - low, 1e-6) * 65535).astype("<u2")
    return {"low": np.round(low, 4).tolist(), "high": np.round(high, 4).tolist(), "count": len(placed),
            "data": base64.b64encode(steps.tobytes()).decode()}


def point_size(points, time, effect):
    """An effect's points' size across in metres: their mean width, else the effect's own size."""
    widths = points.GetWidthsAttr().Get(time)
    mean = float(np.mean(widths)) if widths is not None and len(widths) else 0.0
    return round(mean if mean > 0 else float(effect.GetAttribute("score:effect:size").Get() or 0.05), 4)


def effect_entry(prim):
    """One effect's points where they are most, in the stage's frame, at most EFFECT_POINTS of them: name, layer,
    colour (linear, times its brightness), opacity, size (metres across) and points (packed_points); None when it
    has none."""
    from pxr import Usd, UsdGeom
    points = UsdGeom.Points(prim)
    code = fullest_time(points)
    time = Usd.TimeCode(code) if code is not None else Usd.TimeCode.Default()
    found = np.asarray(points.GetPointsAttr().Get(time) or [], dtype=np.float64)
    if not len(found):
        return None
    found = found[::max(1, -(-len(found) // EFFECT_POINTS))]
    world = np.array(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(time))
    placed = np.column_stack([found, np.ones(len(found))]) @ world
    effect = prim.GetParent()
    colour = effect.GetAttribute("score:effect:colour").Get() or (1.0, 1.0, 1.0)
    brightness = float(effect.GetAttribute("score:effect:brightness").Get() or 1.0)
    return {"name": str(prim.GetPath().MakeRelativePath(prim.GetStage().GetDefaultPrim().GetPath())),
            "layer": "effects" if not shown_place(prim) else layer_of(prim),
            "colour": [round(float(part) * brightness, 4) for part in colour],
            "opacity": float(effect.GetAttribute("score:effect:opacity").Get() or 1.0),
            "size": point_size(points, time, effect), "points": packed_points(placed[:, :3])}


def effects(stage):
    """Every visible effect's points of the stage (effect_entry)."""
    from pxr import Usd, UsdGeom
    found = []
    for prim in Usd.PrimRange(stage.GetDefaultPrim()):
        if prim.IsA(UsdGeom.Points) and UsdGeom.Imageable(prim).ComputeVisibility() != UsdGeom.Tokens.invisible:
            entry = effect_entry(prim)
            if entry:
                found.append(entry)
    return found


def moving_prims(stage):
    """The prims whose own transform is sampled over time (a door's slide, a fan's spin, a ferry's route)."""
    from pxr import Usd, UsdGeom
    return [prim for prim in Usd.PrimRange(stage.GetDefaultPrim())
            if prim.IsA(UsdGeom.Xformable) and UsdGeom.Xformable(prim).GetTimeSamples()]


def nearest_mover(prim, movers):
    """The nearest prim up from `prim` (itself first) that moves, or None."""
    while prim and prim.IsValid():
        if prim.GetPath() in movers:
            return prim.GetPath()
        prim = prim.GetParent()
    return None


def moved_objects(export, stage, movers, time):
    """{mover's path: the objects (as the viewer names them) of the drawn meshes it carries}; a skinned mesh is
    left standing (its pose is the first)."""
    from pxr import Usd
    skinned = export.skins(stage)
    found = {}
    for prim in Usd.PrimRange(stage.GetDefaultPrim()):
        if prim.GetPath() in skinned or not export.drawn(prim, time):
            continue
        mover = nearest_mover(prim, movers)
        if mover is not None:
            found.setdefault(mover, set()).add(export.object_name(prim))
    return found


def needed(before, here, after):
    """Whether a key (code, matrix) is needed: blending the keys either side at its time does not put it within
    MOTION_METRES and MOTION_TURN."""
    share = (here[0] - before[0]) / (after[0] - before[0])
    blended = before[1] + (after[1] - before[1]) * share
    actual = here[1]
    return (np.abs(blended[3, :3] - actual[3, :3]).max() > MOTION_METRES
            or np.abs(blended[:3, :3] - actual[:3, :3]).max() > MOTION_TURN)


def thinned(keys):
    """A mover's keys, [(code, matrix)], with every key its neighbours already give dropped (the first and last
    kept)."""
    kept = [keys[0]]
    for number in range(1, len(keys) - 1):
        if needed(kept[-1], keys[number], keys[number + 1]):
            kept.append(keys[number])
    return kept + [keys[-1]] if len(keys) > 1 else kept


def motion(export, stage, time):
    """The stage's movers over its whole time, one key a time code thinned (thinned): {codes_per_second, start, end,
    movers: [{name, objects, keys: [[code, 16 numbers: the move from where it stands at `time`, row by row]]}]};
    None when nothing moves."""
    from pxr import UsdGeom
    movers = {prim.GetPath(): prim for prim in moving_prims(stage)}
    carried = moved_objects(export, stage, movers, time)
    if not carried:
        return None
    start, end = stage.GetStartTimeCode(), stage.GetEndTimeCode()
    codes = np.arange(start, end + 1.0)
    first = {path: np.linalg.inv(np.array(UsdGeom.XformCache(time).GetLocalToWorldTransform(movers[path])))
             for path in carried}
    tracks = {path: [] for path in carried}
    for code in codes:
        cache = UsdGeom.XformCache(float(code))
        for path in carried:
            tracks[path].append((float(code), first[path] @ np.array(cache.GetLocalToWorldTransform(movers[path]))))
    return {"codes_per_second": stage.GetTimeCodesPerSecond(), "start": start, "end": end,
            "movers": [{"name": export.object_name(movers[path]), "objects": sorted(carried[path]),
                        "keys": [[code, np.round(matrix, 5).ravel().tolist()] for code, matrix in thinned(tracks[path])]}
                       for path in sorted(carried)]}


def film_cameras(store_root, output):
    """The cameras of a place's accepted demo film (its views.json, each shot's first frame): name, eye, aim, fov
    across the picture; [] when it has none."""
    listing = json.loads((store_root / "objects" / "outputs" / f"{output}.json").read_text())
    if "views.json" not in listing:
        return []
    views = json.loads((store_root / "objects" / "blobs" / listing["views.json"]).read_text())["views"]
    return [{"name": f"film {view['name'].split('-')[0].replace('shot', 'shot ')}", "eye": view["eye"],
             "aim": view["aim"], "fov": float(view.get("fov", 75.0))}
            for view in views if view["name"].endswith("-000")]
