"""Sound layer: the hub's sounds as `tools/usd/sound.write_layer` laid them (the library's layer/sound.hub over the
hub's own 3D stage): each spatial sound at its object with how far it carries, the room tones heard everywhere; the
slider moves a listener between the place's camera spots and shows what each sound gives there by the soundtrack's
own rule (`sound.heard_gain`: its level over its distance, silent past its reach)."""
import json
import math

import numpy as np
from pxr import Usd, UsdGeom, UsdMedia

from score.stages.library.demo import camera_paths as stage_plan
from score.stages.library.demos import NoExample

ALGORITHM = "sound_layer"
PLACE = "hub"


def plan_at(point):
    return [round(float(point[0]), 2), round(float(-point[2]), 2)]


def sources(stage):
    """Every SpatialAudio prim but the surface bank: {name, spatial, volume (dB), reach (m), at (x, y, z)}."""
    cache = UsdGeom.XformCache()
    found = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdMedia.SpatialAudio) or "/Sound/Bank/" in str(prim.GetPath()):
            continue
        audio = UsdMedia.SpatialAudio(prim)
        found.append({"name": prim.GetAttribute("score:sound:name").Get() or prim.GetName(),
                      "spatial": str(audio.GetAuralModeAttr().Get()) == UsdMedia.Tokens.spatial,
                      "volume": float(prim.GetAttribute("score:sound:volumeDb").Get() or 0.0),
                      "reach": float(prim.GetAttribute("score:sound:reach").Get() or 0.0),
                      "at": list(cache.GetLocalToWorldTransform(prim).ExtractTranslation())})
    return found


def words(name):
    return name.replace("_", " ")


def laid(spatial):
    """Each spatial sound as a dot with a ring as far as it carries."""
    shapes = []
    for source in spatial:
        shapes.append({"kind": "dots", "points": [plan_at(source["at"])], "r": 0.35, "tone": "accent",
                       "label": f"{words(source['name'])}, {source['volume']:.0f} dB"})
        if source["reach"]:
            centre = plan_at(source["at"])
            shapes.append({"kind": "line", "tone": "ghost", "label": f"heard to {source['reach']:.0f} m",
                           "points": [[round(centre[0] + source["reach"] * math.cos(turn * math.pi / 16), 2),
                                       round(centre[1] + source["reach"] * math.sin(turn * math.pi / 16), 2)]
                                      for turn in range(33)]})
    return shapes


def heard_at(sound_code, spatial, view):
    """What a listener at a camera spot hears of each spatial sound: a dot each, its level there in dB, and the
    listener."""
    eye, aim = np.asarray(view["eye"], float), np.asarray(view["aim"], float)
    shapes = [{"kind": "dots", "points": [plan_at(eye)], "r": 0.6, "tone": "c1",
               "label": f"the listener at {words(view['name'])}"}]
    for source in spatial:
        level, _ = sound_code.heard_gain(source, eye, aim, np.asarray(source["at"], float))
        heard = f"{source['volume'] + 20 * math.log10(level):.0f} dB here" if level > 0 else "not heard here"
        shapes.append({"kind": "dots", "points": [plan_at(source["at"])], "r": 0.35,
                       "tone": "accent" if level > 0 else "ghost", "label": f"{words(source['name'])}: {heard}"})
    return shapes


def made(inputs):
    inputs.library(f"layer/sound.{PLACE}@1", "layer.usda")
    path = stage_plan.fetched_stage(inputs, PLACE, over=[f"score_lib/layer/sound.{PLACE}/1/layer.usda"])
    camera = stage_plan.camera_code(inputs.repo)
    import sound as sound_code  # tools/usd, on the path camera_code put it on
    walls = stage_plan.waist_lines(camera.place_scenes(path)["still"])
    found = sources(Usd.Stage.Open(str(path)))
    spatial = [source for source in found if source["spatial"]]
    rooms = [source for source in found if not source["spatial"]]
    if not spatial:
        raise NoExample(f"the {PLACE}'s sound layer has no spatial sound")
    views = json.loads((inputs.repo / "data/scene" / f"{PLACE}.json").read_text())["views"]
    shown = [point for shape in walls for point in shape["points"]]
    xs, ys = [point[0] for point in shown], [point[1] for point in shown]
    return {
        "example": f"the {PLACE}'s sounds",
        "view": "plan", "bounds": [min(xs) - 1, min(ys) - 1, max(xs) + 1, max(ys) + 1],
        "steps": [
            {"label": "The hub cut at waist height, from its own 3D stage", "shapes": walls},
            {"label": "Room tones, heard everywhere: " + ", ".join(
                f"{words(source['name'])} {source['volume']:.0f} dB" for source in rooms),
             "shapes": [{"kind": "text", "points": [[round(min(xs), 2), round(max(ys) + 0.5, 2)]], "tone": "base",
                         "label": "room tones: " + ", ".join(words(source["name"]) for source in rooms)}]},
            {"label": "Each machine's sound at the machine, with how far it carries", "shapes": laid(spatial)},
            {"label": "What a listener hears from where they stand",
             "shapes": heard_at(sound_code, spatial, views[0])}],
        "slider": {"label": "listening spot", "unit": "", "values": list(range(1, len(views) + 1)), "at": 0,
                   "shapes": [heard_at(sound_code, spatial, view) for view in views]},
        "numbers": [{"label": "sounds", "value": len(spatial), "unit": "", "tip": "sounds at objects"},
                    {"label": "room tones", "value": len(rooms), "unit": "", "tip": "sounds heard everywhere"}]}
