"""The light stage (experimental, PRD #6, until the owner reviews it; the paper-vs-world-1 audit's items 9 and 17): a
place's light layer, its lamps' strengths measured from one render of every lamp on its own, and the sky its record
holds, as three rows of the stage table.

    light-layer   (free) layers/light.usda over the place's round-three seed, from today's scene record with
                  tools/usd/scene.py's own writers (layer.py): each lamp where the record puts it, the Earth on its
                  ball with NASA's surface, Mars's day sky with the sun's disc, the floodlights' shafts; lamps.json
    light-passes  (paid) the seed with that layer rendered on the views of the place's own scene record (the
                  layer's views.json, passes.record_views), once, at passes.CHECK_SIZE, on one card class, each of
                  the place's own lamps in a Cycles light group of its own (inside/light_passes.py): per view the
                  look and the luminance of the whole picture and of each lamp alone
    light         (free) the sweep on the passes (mix.py): one scale for every lamp without a shaft (a floodlight's is
                  its shaft sweep's, 2026-10-11) bringing the place's brightness nearest its concept's, each blown-out
                  lamp turned down; those strengths written into the layer; the look at them mixed from the passes
                  (looks/), and every fault measured on it

    gates (light)  brightness      the place's brightness within BRIGHT_WITHIN of its concept's, each view within
                                   VIEW_WITHIN (mix.py has the rules)
                   lamps           no lamp on screen unlit, none blown out
                   sky elements    every element the record's sky holds is in the layer: the Earth with NASA's
                                   surface, the day dome and the sun's disc, the shafts
                   heads           floodlight heads facing the eye glow as concept K04's (halo, fill, beam, veil)
                   earth           the Earth's disc at most SMOOTH_MOST flat paint (concept C4's 0.0)
                   sky             an outdoor place's sky within SKY_GAP_MOST levels of its concept's sky colour,
                                   its blue to red within BLUE_TO_RED_WITHIN
                   exposure        no view more black or blown out than its concept (BLACK_OVER, BLOWN_OVER)
                   stage_no_worse  the seed with the layer has no more placeholder or made-only faults than without

The owner's plan for light is baked per-lamp layers mixed live (memory, project-sound-and-light-layers). This stage is
its first half on the views: one pass a lamp, mixed at any strengths with no render again. The layer it delivers holds
live lights (UsdLux) at the measured strengths; no lamp's light is baked into the surfaces yet.

The lightkit row (kit.py: the square's proscenium and floodlight towers, baked) keeps its own runner
(`python -m score.stages.light run lightkit`).
"""
import json
import pathlib
import shutil
import sys

import numpy as np
from PIL import Image

from score import checks, contracts, graph
from score.stages.light import haze, layer, measure, mix, needs, passes
from score.stages.light.passes import groups_of, neighbours, views_of
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import made_only  # noqa: E402
import placeholders  # noqa: E402
import stage_inputs  # noqa: E402

WORK = PROPS_HOME / "work"
# The concepts each fault is measured against (the coordinator's picks, data/inventory/<place>.json), worked out by
# measure.py on 2026-10-11: K04's two floodlight heads, C4's Earth. A sky is measured against the place's own concepts.
CONCEPTS = {"square": WORK / "scene/square/views/K04.png", "old_station": WORK / "scene/old_station/views/C4.png"}
CONCEPT_HEADS = (((663, 532), 49.0), ((1332, 558), 44.5))
CONCEPT_EARTH = ((719, 262), 53.0)
# The pass rules of 2026-10-11 (the light stage's first rows), set before any after-picture was made: half the
# concept's head halo and fill, a beam that lights its air, the place washed out by its haze at most VEIL_MOST, only
# heads whose lit face turns toward the eye judged (FACING_LEAST); an Earth disc at most a quarter smooth; a sky
# within 20 levels of the concept's colour, its blue to red within 0.15 of the concept's.
HALO_LEAST = 0.08
FILL_LEAST = 0.28
BEAM_LEAST = 0.02
VEIL_MOST = 0.04
FACING_LEAST = 0.2
# The floodlights' strengths tried, as shares of the layer's, the least first (set 2026-10-12, before the launch's
# first light node judged its heads: its pad lamps glowed at halo 0.059 at the square's numbers): by half octaves
# from a quarter to 16 times. The quarter to one were added after the first fan-out: with the before taken from the
# node's own passes (the floodlights off) the veil is all the floodlights give the place's lower part, and at the
# layer's strength the square's (0.097) and the launch's (0.040) were over it while their halos stood far over theirs.
FLOODLIGHT_SCALES = tuple(2.0 ** (step / 2.0) for step in range(-4, 9))
SMOOTH_MOST = 0.25
# The share of a pixel's light the place's lamps may give for it to count as the Earth's (set 2026-10-12 after the
# first fan-out, see earth_measures).
EARTH_LAMP_MOST = 0.1
SKY_GAP_MOST = 20.0
BLUE_TO_RED_WITHIN = 0.15
# Black and blown out (#27, the owner's gate "every place lit with no black or blown areas", set 2026-10-20 before any
# look it judges was rendered): a pixel under BLACK or over BLOWN in luminance, 0 to 1; a view fails when its share of
# them passes its concept pictures' mean share by more than BLACK_OVER or BLOWN_OVER (a black sky over the Moon is
# the concept's own).
BLACK = 4.0 / 255.0
BLOWN = 251.0 / 255.0
BLACK_OVER = 0.05
BLOWN_OVER = 0.02
# The floodlights each place's views show: its own, and the square's towers seen from the launch view.
LAMP_KINDS = {"square": (("square", "square_far_floodlight_tower"),),
              "launch": (("launch", "launch_far_pad_floodlight"), ("square", "square_far_floodlight_tower"))}


def place_of(inputs):
    return json.loads(pathlib.Path(inputs["scene"]).read_text())["place"]


def scene_of(place):
    return json.loads((REPO / f"data/scene/{place}.json").read_text())


def applies(place):
    """A place with a scene record in the repository (its views and lights; the door kits gdoor and hdoor have none). Its
    seed is an input like any other: a lost one is the place's hole, never a reason to leave the place unlit."""
    return place is not None and (REPO / "data/scene" / f"{place}.json").is_file()


# --- light-layer ----------------------------------------------------------------------------------------------------

def make_layer(inputs, out, seed, params):
    """The place's light layer over its stage as the assembly lays it before its layers (passes.source: the seed with
    its accepted scene record), and lamps.json (each lamp, its strength there, whether it has a shaft)."""
    place = place_of(inputs)
    stage = passes.source(place, inputs, out / "source")
    found = layer.write(place, passes.record_of(place, inputs), stage, out)
    record = passes.record_of(place, inputs)
    if not found["lamps"] or not (record.get("environment") or {}).get("inside"):
        found["lamps"] += sun_lamps(place, out, stage)
    shutil.rmtree(out / "source")
    layer.lamps_file(found, out)
    (out / passes.VIEWS).write_text(json.dumps(passes.record_views(record), indent=1))


def sun_lamps(place, out, stage):
    """The suns of a place lit by no lamp or under the open sky (its record's environment not `inside`), each in a
    light group of its own, swept after the lamps when they cannot bring the place to its concept's brightness (the
    captain, 2026-10-12: the old station stood at 0.38 of C4's with nothing to sweep, the wreck reached C4's only with
    its one small lamp at 500 times its strength)."""
    from pxr import Sdf, Usd, UsdLux
    composed = Sdf.Layer.CreateAnonymous(".usda")
    composed.subLayerPaths.append(str(out / layer.LAYER))
    composed.subLayerPaths.append(str(stage / f"{place}.usda"))
    held = Usd.Stage.Open(composed)  # kept: a prim of a stage nobody holds is gone
    lights = held.GetPrimAtPath(f"/{place}/Lights")
    return [{"path": str(prim.GetPath()), "spot": None, "shaped": False, "shaft": False, "sun": True,
             "intensity": float(prim.GetAttribute("inputs:intensity").Get())}
            for prim in (lights.GetChildren() if lights else []) if prim.IsA(UsdLux.DistantLight)]


def layer_faults(folder):
    found = [f"no {name}" for name in (layer.LAYER, "lamps.json", passes.VIEWS) if not (folder / name).exists()]
    if not found and not views_of(folder)[1]:
        found.append("no view to render the light on")
    return found


def judge_placed(output, inputs, evidence):
    """Every lamp of the record stands in the layer (kept, moved or added)."""
    found = json.loads((output / "lamps.json").read_text())
    lamps = {lamp["path"] for lamp in found["lamps"]}
    lost = [entry["record"] for entry in found["placed"] if entry["path"] not in lamps and "sun" not in entry["record"]]
    return verdict("lamps placed", not lost, f"{len(found['placed'])} of the record's lights placed "
                   f"({', '.join(sorted({entry['done'].split()[0] for entry in found['placed']})) or 'none'}), "
                   f"{len(lamps)} lamps in the layer; lost: {lost or 'none'}", {"lamps": len(lamps), "lost": len(lost)},
                   {"lost": "lower"}, lost)


def missing_elements(found):
    """The sky elements ({name: [wanted, held]}) the record holds and the layer does not."""
    return [f"{name}: the record holds {wanted}, the layer {held}" for name, (wanted, held) in found.items()
            if held < wanted]


def judge_layer_sky(output, inputs, evidence):
    """Every element the record's sky holds is in the layer (sky_elements), before anything is rendered."""
    place = json.loads((output / "lamps.json").read_text())["place"]
    found = sky_elements(place, output, passes.record_of(place, inputs))
    missing = missing_elements(found)
    return verdict("sky elements", not missing, "; ".join(missing) or f"every element the record holds: {found}",
                   {"missing": len(missing)}, {"missing": "lower"}, missing)


LAYERED = contracts.Contract("light-layer", 1, layer_faults, {"length": "metre", "up axis": "Y"})


def layer_files(place):
    """The record, the kit (its seat, its lenses) and the light data (passes.place_files), the seed and the grounds the
    sky stands on."""
    return {"scene": "{data}/scene/{place}.json", "seed": "{seeds}/usd-r3/{place}", "grounds": "{data}/ground",
            "kit": "{data}/kit/{place}.json", **passes.place_files(place)}


# --- light: the sweep, the strengths and the measures ------------------------------------------------------------

def luminance_of(path):
    """A look picture's luminance, 0 to 1, halved as the passes are."""
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0
    return halved(rgb @ np.array([0.2126, 0.7152, 0.0722]))


def halved(values):
    tall, wide = values.shape[0] // 2 * 2, values.shape[1] // 2 * 2
    return values[:tall, :wide].reshape(tall // 2, 2, wide // 2, 2, *values.shape[2:]).mean(axis=(1, 3))


def view_passes(passes_folder, name):
    """{view: (passes, tone curve, look path)} of one demo place's views."""
    found = {}
    for path in sorted(passes_folder.glob(f"passes/{name}-*/*-passes.npz")):
        view = path.name.removesuffix("-passes.npz")
        held = dict(np.load(path))
        look = path.with_name(f"{view}-look.png")
        found[view] = (held, mix.tone_curve(held["combined"], luminance_of(look)), look)
    return found


def concept_pictures(place):
    inventory = json.loads(stage_inputs.inventory_path(place).read_text())
    return [pathlib.Path(view["picture"].replace("WORK", str(WORK))) for view in inventory["plan"]["views"]]


def concept_brightness(place):
    """The mean look luminance of the place's concept pictures, each at its own size."""
    return float(np.mean([(np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0
                           @ np.array([0.2126, 0.7152, 0.0722])).mean() for path in concept_pictures(place)]))


def on_screen(spot, size, views):
    """The views whose picture a lamp's spot falls in."""
    found = []
    for view in views:
        x, y, _, _ = measure.where(view, size, spot)
        if x is not None and 0 <= x < size[0] and 0 <= y < size[1]:
            found.append(view["name"])
    return found


def strengths(place, passes_folder, lamps, layer_folder):
    """The sweep on the place's views (its passes, rendered on its light layer's views): (scales {group: scale},
    measures). Only a lamp those passes hold a group of is swept."""
    by_path = {lamp["path"]: lamp for lamp in lamps}
    groups = {group: path for group, path in groups_of(passes_folder).items() if path in by_path}
    views = {view: (held, curve) for view, (held, curve, _) in view_passes(passes_folder, place).items()}
    size, shown_views = views_of(layer_folder)
    target = concept_brightness(place)
    held = {group for passes_held, _ in views.values() for group in passes_held}
    swept = [group for group, path in groups.items()
             if not by_path[path]["shaft"] and not by_path[path].get("sun") and group in held]
    scale = mix.sweep(views, swept, target)
    scales = {group: (scale if group in swept else 1.0) for group in groups}
    suns = [group for group, path in groups.items() if by_path[path].get("sun") and group in held]
    sun_scale = 1.0
    if suns and not mix.within(views, scales, target):  # the lamps cannot: the sky's light can
        sun_scale = mix.sweep(views, suns, target, scales)
        scales.update(dict.fromkeys(suns, sun_scale))
    lamp_found = {}
    for group, path in sorted(groups.items()):
        if by_path[path].get("sun"):  # a sun is not turned down for its own glare: its light is the whole sky's
            lamp_found[path] = {"group": group, "scale": scales[group], "views": {}, "sun": True, "on_screen": []}
            continue
        scales[group], measures = mix.turned_down(views, scales, group)
        lamp_found[path] = {"group": group, "scale": scales[group], "views": measures,
                            "sun": bool(by_path[path].get("sun")),
                            "on_screen": on_screen(by_path[path]["spot"], size, shown_views)
                            if by_path[path]["spot"] else []}
    for entry in lamp_found.values():
        entry["fault"] = mix.lamp_faults(lamp_measures_again(views, scales, entry["group"]), entry["on_screen"])
    return scales, {"concept": round(target, 4), "swept_scale": scale, "swept": len(swept), "sun_scale": sun_scale,
                    "before": {name: round(value, 4) for name, value in mix.brightness(views, {}).items()},
                    "after": {name: round(value, 4) for name, value in mix.brightness(views, scales).items()},
                    "lamps": lamp_found}


def lamp_measures_again(views, scales, group):
    """A lamp's measures at the final scales (another lamp turned down after it moves its share)."""
    return mix.lamp_measures(views, scales, group)


def look_at(held, curve, look, scales):
    """A view's look at the scales, from its rendered look: every pixel's colour times the ratio of its look luminance
    mixed at the scales to the rendered one, that ratio smoothed on the rendered look (mix.smoothed: the lamp groups
    are not denoised)."""
    rendered = mix.toned(curve, held["combined"])
    ratio = mix.toned(curve, mix.mixed(held, scales)) / np.maximum(rendered, 1.0 / 255.0)
    ratio = mix.smoothed(ratio, luminance_of(look)[:ratio.shape[0], :ratio.shape[1]])
    rgb = np.asarray(Image.open(look).convert("RGB"), dtype=np.float64)
    full = np.repeat(np.repeat(ratio, 2, axis=0), 2, axis=1)
    full = np.pad(full, ((0, rgb.shape[0] - full.shape[0]), (0, rgb.shape[1] - full.shape[1])), mode="edge")
    return Image.fromarray(np.clip(rgb * full[..., None], 0, 255).astype(np.uint8))


def floodlight_sweep(place, passes_folder, scales, shafted, out, record, haze_folder=None):
    """The floodlights' strength (their shafts' light with them): the least of FLOODLIGHT_SCALES at which the heads
    rule holds on the looks mixed at it, else the layer's own (1), set into `scales`; the looks at the final strengths
    are left in out/looks. The layer's own strength is tried first and kept when it meets the rule: a floodlight is
    dimmed or brightened only where its gate needs it (2026-10-13: dimmed to the least passing strength, the square's
    heads read worse than its earlier accepted output while passing). What was tried, {scale: passed}."""
    tried = {}
    order = (1.0, *(scale for scale in FLOODLIGHT_SCALES if scale != 1.0))
    for scale in (order if shafted and place in LAMP_KINDS else (1.0,)):
        scales.update(dict.fromkeys(shafted, scale))
        mixed_looks(passes_folder, scales, shafted, out, haze_folder)
        if not (shafted and place in LAMP_KINDS):
            break
        summary = heads_summary(head_measures(place, out, record))
        tried[scale] = bool(summary and summary[0])
        if tried[scale]:
            return tried
    if tried:  # none met the rule: the floodlights stay at the layer's strength, the gate says what fails
        scales.update(dict.fromkeys(shafted, 1.0))
        mixed_looks(passes_folder, scales, shafted, out, haze_folder)
    return tried


def mixed_looks(passes_folder, scales, shafted, out, haze_folder=None):
    """Each view's look at the measured strengths (looks/<demo place>/<view>-look.png) and, where the place has
    floodlights with shafts, with those lamps off (<view>-unlit.png): the before their heads and beams are measured
    against, taken from the same render, never from an older one."""
    for name in {path.parent.name.rsplit("-", 1)[0] for path in passes_folder.glob("passes/*/*-passes.npz")}:
        for view, (held, curve, look) in view_passes(passes_folder, name).items():
            target = out / "looks" / name
            target.mkdir(parents=True, exist_ok=True)
            look_at(held, curve, look, scales).save(target / f"{view}-look.png")
            if shafted:
                look_at(held, curve, look, dict(scales, **dict.fromkeys(shafted, 0.0))).save(
                    target / f"{view}-unlit.png")
            if haze_folder is not None:  # the same view rendered with the shafts off, mixed at the same strengths
                held_off, curve_off, look_off = view_passes(haze_folder, name)[view]
                look_at(held_off, curve_off, look_off, scales).save(target / f"{view}-unhazed.png")


def layer_copied(layer_folder, out):
    """The layer's files and its views written anew into the node's output (never saved over the input, a read-only
    checkout)."""
    (out / "layers").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(layer_folder / layer.LAYER, out / layer.LAYER)
    shutil.copyfile(layer_folder / passes.VIEWS, out / passes.VIEWS)
    if (layer_folder / layer.ASSETS).exists():
        shutil.copytree(layer_folder / layer.ASSETS, out / layer.ASSETS, copy_function=shutil.copyfile)


def make_light(inputs, out, seed, params):
    """The sweep on the passes, the strengths into the place's layer, the looks at them and every measure."""
    place = place_of(inputs)
    layer_folder = pathlib.Path(inputs["light-layer"])
    passes_folder = pathlib.Path(inputs["light-passes"])
    haze_folder = pathlib.Path(inputs["light-haze"]) if "light-haze" in inputs else None
    layer_copied(layer_folder, out)
    found = json.loads((layer_folder / "lamps.json").read_text())
    scales, swept = strengths(place, passes_folder, found["lamps"], layer_folder)
    own = {lamp["path"] for lamp in found["lamps"]}
    by_group = {group: path for group, path in groups_of(passes_folder).items() if path in own}
    intensity = {lamp["path"]: lamp["intensity"] for lamp in found["lamps"]}
    shafted = [group for group, path in by_group.items()
               if next(lamp for lamp in found["lamps"] if lamp["path"] == path)["shaft"]]
    record = passes.record_of(place, inputs)
    swept["floodlights"] = floodlight_sweep(place, passes_folder, scales, shafted, out, record, haze_folder)
    for lamp in found["lamps"]:
        group = next((name for name, path in by_group.items() if path == lamp["path"]), None)
        lamp["scale"] = scales.get(group, 1.0)
    layer.strengths(out / layer.LAYER, place, {by_group[group]: (intensity[by_group[group]], scale)
                                               for group, scale in scales.items()})
    layer.lamps_file(found, out)
    measures = {"place": place, "brightness": swept, "sky_elements": sky_elements(place, out, record),
                "concept": concept_measures(), "stage_checks": stage_checks(place, layer_folder, inputs, out)}
    measures.update(fault_measures(place, out, passes_folder, record))
    (out / "measures.json").write_text(json.dumps(measures, indent=1) + "\n")


# --- the old faults' measures (the light stage's of 2026-10-11), on the looks at the measured strengths ------------

def rendered(out, name, kind="look"):
    return {path.name.removesuffix(f"-{kind}.png"): path for path in out.glob(f"looks/{name}/*-{kind}.png")}


def lamp_heads(place, record):
    """Each floodlight lamp a place's views show as (its lens middle, half its bank's width, its light, its front)."""
    found = []
    for owner, kind in LAMP_KINDS[place]:
        kit = json.loads((REPO / f"data/kit/{owner}.json").read_text())
        owned = record if owner == place else scene_of(owner)
        lights = [entry for entry in layer.lights_of(owner, owned) if entry.get("shaft")]
        for laid in kit["pieces"]:
            if laid["kind"] != kind or laid.get("part") != "glow":
                continue
            middle = layer.lens_middle(laid)
            light = min(lights, key=lambda entry: np.linalg.norm(np.asarray(entry["at"]) - middle)) if lights else None
            found.append((middle, laid["size"][0] / 2, light, -np.asarray(laid["z"], dtype=np.float64)))
    return found


def head_measures(place, out, record):
    """Every floodlight head on screen in every view, with its shafted lamps off (before) and on (after), and its
    beam's gain."""
    size, views = views_of(out)
    after, unlit, unhazed = rendered(out, place), rendered(out, place, "unlit"), rendered(out, place, "unhazed")
    found, veils = [], {}
    for view in views:
        if view["name"] not in after or view["name"] not in unlit:
            continue
        before_rgb, after_rgb = measure.picture(unlit[view["name"]]), measure.picture(after[view["name"]])
        # The veil is what the shafts' haze lays over the place: against the render with the shafts off where the
        # node has one (light-haze), else against the floodlights off (their floor light in it too).
        veiled = measure.picture(unhazed[view["name"]]) if view["name"] in unhazed else before_rgb
        veils[view["name"]] = measure.veil(veiled, after_rgb)
        for middle, half, light, front in lamp_heads(place, record):
            x, y, depth, focal = measure.where(view, size, middle)
            if x is None or not (0 <= x < size[0] and 0 <= y < size[1]):
                continue
            radius = focal * half / depth
            axis = [measure.where(view, size, np.asarray(light["at"]) + (np.asarray(light["aim"]) -
                                                                          np.asarray(light["at"])) * share)
                    for share in (0.15, 0.3, 0.45)] if light else []
            points = [(px, py) for px, py, _, _ in axis if px is not None and 0 <= px < size[0] and 0 <= py < size[1]]
            toward_eye = np.asarray(view["eye"], dtype=np.float64) - middle
            found.append({"view": view["name"], "at_px": [round(x), round(y)],
                          "faces_eye": round(float(front @ toward_eye / np.linalg.norm(toward_eye)), 3),
                          "before": measure.head(before_rgb, x, y, radius),
                          "after": measure.head(after_rgb, x, y, radius),
                          "beam_gain": measure.beam(before_rgb, after_rgb, points, max(radius, 6.0))})
    return {"heads": found, "veil": veils}


def earth_measures(place, out, passes_folder, record):
    """The Earth's disc in every view that shows it: its colours and its smooth share on its lit pixels that the
    place's lamps do not light (EARTH_LAMP_MOST of their light at most: the greenhouse's roof trusses, lit purple by
    its grow lights, stand across its Earth)."""
    lamps = {view: held for view, (held, _, _) in view_passes(passes_folder, place).items()}
    entry = next(item for root, kind, item in layer.earth_entries(record))
    size, views = views_of(out)
    after = rendered(out, place)
    found = []
    for view in views:
        x, y, depth, focal = measure.where(view, size, entry.get("placed_at", entry["centre"]))
        if x is None or view["name"] not in after:
            continue
        radius = focal * entry["radius"] / depth
        if x + radius < 0 or x - radius > size[0] or y + radius < 0 or y - radius > size[1]:
            continue
        after_rgb = measure.picture(after[view["name"]])
        rows, columns = np.mgrid[0:after_rgb.shape[0], 0:after_rgb.shape[1]]
        held = lamps[view["name"]]
        share = sum(held[group].astype(np.float64) for group in held if group.startswith("lamp_")) / np.maximum(
            held["combined"].astype(np.float64), 1e-6) if len(held) > 1 else np.zeros(held["combined"].shape)
        full = np.repeat(np.repeat(share, 2, axis=0), 2, axis=1)
        full = np.pad(full, ((0, rows.shape[0] - full.shape[0]), (0, rows.shape[1] - full.shape[1])), mode="edge")
        lit = (np.hypot(columns - x, rows - y) < radius * 0.92) & (after_rgb.mean(axis=-1) > 30) & (
            full <= EARTH_LAMP_MOST)
        found.append({"view": view["name"], "disc_px": [round(x), round(y), round(radius)],
                      "after": measure.disc(after_rgb, x, y, radius), "smooth": measure.smooth_share(after_rgb, lit)})
    return found


def concept_skies(place):
    """The sky of each of the place's concept pictures that shows one (measure.sky_pixels, as on a look): its mean
    colour, blue to red and rise, the median of each over the pictures; None when none shows a sky."""
    skies = [sky for sky in (measure.sky_of(rgb, measure.sky_pixels(rgb))
                             for rgb in (measure.picture(path) for path in concept_pictures(place))) if sky]
    if not skies:
        return None
    return {"mean_rgb": [round(float(np.median([sky["mean_rgb"][channel] for sky in skies])), 1)
                         for channel in range(3)],
            "blue_to_red": round(float(np.median([sky["blue_to_red"] for sky in skies])), 4),
            "rise_to_horizon": round(float(np.median([sky["rise_to_horizon"] for sky in skies])), 4),
            "pictures": len(skies)}


def sky_measures(place, out):
    """An outdoor place's sky in every view (the top of the picture near its commonest colour there), against its
    concept pictures' (concept_skies)."""
    concept = concept_skies(place)
    found = []
    for view, path in sorted(rendered(out, place).items()):
        rgb = measure.picture(path)
        sky = measure.sky_of(rgb, measure.sky_pixels(rgb))
        if sky is not None and concept is not None:
            sky["gap_to_concept"] = measure.colour_gap(sky["mean_rgb"], concept["mean_rgb"])
        found.append({"view": view, "after": sky})
    return {"concept": concept, "views": found}


def concept_measures():
    square, old = measure.picture(CONCEPTS["square"]), measure.picture(CONCEPTS["old_station"])
    (x, y), radius = CONCEPT_EARTH
    return {"heads": [measure.head(square, hx, hy, hr) for (hx, hy), hr in CONCEPT_HEADS],
            "earth": measure.disc(old, x, y, radius)}


def fault_measures(place, out, passes_folder, record):
    found = {}
    if place in LAMP_KINDS:
        heads = head_measures(place, out, record)
        found["heads"], found["veil"] = heads["heads"], heads["veil"]
    if layer.earth_entries(record):
        found["earth"] = earth_measures(place, out, passes_folder, record)
    if needs.outdoor(record, None):
        found["sky"] = sky_measures(place, out)
    found["exposure"] = exposure_measures(place, out)
    return found


def extremes(luminance):
    """The shares of a picture's pixels black (under BLACK) and blown out (over BLOWN)."""
    return {"black": round(float((luminance < BLACK).mean()), 4), "blown": round(float((luminance > BLOWN).mean()), 4)}


def picture_luminance(path):
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0
    return rgb @ np.array([0.2126, 0.7152, 0.0722])


def exposure_measures(place, out):
    """Each view's black and blown shares at the measured strengths, and its concept pictures' mean."""
    concepts = [extremes(picture_luminance(path)) for path in concept_pictures(place)]
    concept = {key: round(float(np.mean([found[key] for found in concepts])), 4) for key in ("black", "blown")} \
        if concepts else None
    return {"concept": concept, "views": {view: extremes(picture_luminance(path))
                                          for view, path in sorted(rendered(out, place).items())}}


def sky_elements(place, out, record):
    """What the record's sky holds against what the light layer holds: {element: [wanted, found]}."""
    from pxr import Usd
    held = Usd.Stage.Open(str(out / layer.LAYER))
    lights = layer.lights_of(place, record)
    paths = {str(prim.GetPath()) for prim in held.TraverseAll()}
    picture = held.GetPrimAtPath(f"/{place}/Looks/earth_face/picture")
    nasa = bool(picture) and str(picture.GetAttribute("inputs:file").Get().path).endswith(
        f"{layer.ASSETS}/earth_surface.png")
    shafts = sum(path.startswith(f"/{place}/Shafts/shaft_") and "_look" not in path for path in paths)
    return {"earth": [len(layer.earth_entries(record)) > 0, nasa],
            "sky_dome": [bool((record.get("environment") or {}).get("sky_dome")), f"/{place}/Sky/Dome" in paths],
            "sun_disc": [any(entry["type"] == "sun" and not entry.get("name") and float(entry.get("energy", 0)) > 0
                             for entry in lights), f"/{place}/Sky/sun_disc_0" in paths],
            "shafts": [sum(bool(entry.get("shaft")) for entry in lights), shafts]}


def stage_checks(place, layer_folder, inputs, out):
    """The placeholder and made-only checks on the place's stage as the assembly lays it (passes.source) without and
    with the light layer: fault counts."""
    found = {}
    for side in ("before", "after"):
        tree = out / f"check-{side}"
        tree.mkdir()
        root = (passes.source(place, inputs, tree / place) / f"{place}.usda" if side == "before"
                else passes.lit_tree(place, layer_folder, tree, inputs))
        found[side] = {"placeholders": len(placeholders.check(str(root))), "made_only": len(made_only.check(str(root)))}
        shutil.rmtree(tree)
    return {place: found}


# --- the gates -------------------------------------------------------------------------------------------------------

def measures_of(output):
    return json.loads((output / "measures.json").read_text())


def verdict(check, passed, reason, measures, better=None, findings=()):
    return checks.Verdict(check, checks.PASS if passed else checks.FAIL, reason, measures, better or {},
                          tuple(findings))


def judge_brightness(output, inputs, evidence):
    """The place's brightness (the median of its views' mean look luminance at the measured strengths) within
    mix.BRIGHT_WITHIN of its concept's, every view within mix.VIEW_WITHIN."""
    found = measures_of(output)["brightness"]
    target, views = found["concept"], found["after"]
    if not views:
        return checks.Verdict("brightness", checks.UNKNOWN, "no view's passes were measured")
    place = float(np.median(list(views.values())))
    off = [f"{name}: {value:.3f} against the concept's {target:.3f}" for name, value in views.items()
           if not target / mix.VIEW_WITHIN <= value <= target * mix.VIEW_WITHIN]
    ratio = place / target
    passed = 1 / mix.BRIGHT_WITHIN <= ratio <= mix.BRIGHT_WITHIN and not off
    return verdict("brightness", passed, f"the place {np.median(list(found['before'].values())):.3f} -> {place:.3f} "
                   f"against its concept's {target:.3f} (x{ratio:.2f}, within x{mix.BRIGHT_WITHIN}); the lamps without "
                   f"a shaft at x{found['swept_scale']:g} of the seed's ({found['swept']} lamps); {len(off)} views "
                   f"outside x{mix.VIEW_WITHIN}", {"ratio": round(ratio, 3), "views_off": len(off)},
                   {"views_off": "lower"}, off)


def judge_lamps(output, inputs, evidence):
    """No lamp on screen lights nothing, none is blown out at the measured strengths (mix.py's rules)."""
    lamps = {path: entry for path, entry in measures_of(output)["brightness"]["lamps"].items()
             if not entry.get("sun")}  # a sun the sweep scales (a place with no lamp) is no lamp to judge
    faults = [f"{path}: {entry['fault']}" for path, entry in lamps.items() if entry["fault"] in ("unlit", "blown")]
    unseen = [path for path, entry in lamps.items() if entry["fault"] == "unseen"]
    if lamps and len(unseen) == len(lamps):
        return checks.Verdict("lamps", checks.UNKNOWN, f"none of the {len(lamps)} lamps lights any view")
    return verdict("lamps", not faults, f"{len(lamps)} lamps: {len(faults)} unlit or blown out, {len(unseen)} light no "
                   f"view and stand in none (not judged)", {"faulty": len(faults)}, {"faulty": "lower"}, faults)


def judge_sky_elements(output, inputs, evidence):
    """Every element the record's sky holds is in the light layer: the Earth with NASA's surface, the day dome, the
    sun's disc, each floodlight's shaft."""
    found = measures_of(output)["sky_elements"]
    missing = missing_elements(found)
    return verdict("sky elements", not missing, "; ".join(missing) or f"every element the record holds: {found}",
                   {"missing": len(missing)}, {"missing": "lower"}, missing)


def judge_heads(output, inputs, evidence):
    """Each floodlight head that can read as a white grid (on screen, its lit face toward the eye: FACING_LEAST) glows
    as concept K04's do: halo and fill (medians after) at least half the concept's, its beam lighting the air, and no
    view's lower part washed out by the haze (VEIL_MOST)."""
    found = measures_of(output)
    if "heads" not in found:
        return verdict("heads", True, "no floodlight in this place", {})
    summary = heads_summary(found)
    if summary is None:
        return checks.Verdict("heads", checks.UNKNOWN, "no floodlight head faces the eye in any view")
    passed, heads, halo, fill, gain, washed = summary
    return verdict("heads", passed, f"{len(heads)} heads facing the eye of {len(found['heads'])} on screen: halo "
                   f"{halo['before']:.3f} -> {halo['after']:.3f} (>= {HALO_LEAST}), fill {fill['before']:.3f} -> "
                   f"{fill['after']:.3f} (>= {FILL_LEAST}), beam gain {gain:.3f} (>= {BEAM_LEAST}), washed out by at "
                   f"most {washed:.3f} (<= {VEIL_MOST})",
                   {"halo": round(halo["after"], 4), "fill": round(fill["after"], 4), "beam": round(gain, 4),
                    "veil": round(washed, 4), "facing_heads": len(heads)},
                   {"halo": "higher", "fill": "higher", "beam": "higher", "veil": "lower"})


def heads_summary(found):
    """(passed, heads judged, halo, fill, beam gain, veil) of the heads facing the eye, or None when none does."""
    heads = [head for head in found["heads"] if head["after"] and head["before"] and head["faces_eye"] >= FACING_LEAST]
    if not heads:
        return None
    halo = {side: float(np.median([head[side]["halo"] for head in heads])) for side in ("before", "after")}
    fill = {side: float(np.median([head[side]["fill"] for head in heads])) for side in ("before", "after")}
    gains = [head["beam_gain"] for head in heads if head["beam_gain"] is not None]
    gain = float(np.median(gains)) if gains else 0.0
    washed = max(found["veil"].values()) if found["veil"] else 0.0
    passed = halo["after"] >= HALO_LEAST and fill["after"] >= FILL_LEAST and gain >= BEAM_LEAST and washed <= VEIL_MOST
    return passed, heads, halo, fill, gain, washed


def judge_earth(output, inputs, evidence):
    """The Earth reads as the real planet: at most SMOOTH_MOST of its lit disc smooth (measure.smooth; median over the
    views showing it), where concept C4's is 0.0."""
    found = measures_of(output)
    if "earth" not in found:
        return verdict("earth", True, "no Earth in this place", {})
    discs = [disc["smooth"] for disc in found["earth"] if disc.get("smooth") is not None]
    if not discs and found["sky_elements"]["earth"][1]:
        # The hub's and the tube's views never show their Earth (2026-10-12): the cartoon disc is a fault only where it
        # is seen, and the layer's Earth is NASA's (sky elements).
        return verdict("earth", True, "the Earth is on screen in no view; the layer's is NASA's surface", {})
    if not discs:
        return checks.Verdict("earth", checks.UNKNOWN, "the Earth is on screen in no view")
    smooth = float(np.median(discs))
    return verdict("earth", smooth <= SMOOTH_MOST, f"{len(discs)} views: smooth share of the lit disc {smooth:.3f} "
                   f"(<= {SMOOTH_MOST}; concept C4's 0.0)", {"smooth": round(smooth, 4)}, {"smooth": "lower"})


def judge_sky(output, inputs, evidence):
    """An outdoor place's sky reads as its concept's: within SKY_GAP_MOST levels of its colour and its blue to red
    within BLUE_TO_RED_WITHIN (medians over the views); its rise to the horizon reported, not judged."""
    found = measures_of(output)
    if "sky" not in found:
        return verdict("sky", True, "no open sky over this place", {})
    concept = found["sky"]["concept"]
    if concept is None:
        return checks.Verdict("sky", checks.UNKNOWN, "no concept picture of the place shows its sky")
    views = [view for view in found["sky"]["views"] if view["after"] and "gap_to_concept" in view["after"]]
    if not views:
        return checks.Verdict("sky", checks.UNKNOWN, "no sky measured in any view")
    gap = {"after": float(np.median([view["after"]["gap_to_concept"] for view in views]))}
    ratio = float(np.median([view["after"]["blue_to_red"] for view in views]))
    rise = float(np.median([view["after"]["rise_to_horizon"] for view in views]))
    passed = gap["after"] <= SKY_GAP_MOST and abs(ratio - concept["blue_to_red"]) <= BLUE_TO_RED_WITHIN
    return verdict("sky", passed, f"{len(views)} views: colour gap to the concept "
                   f"{gap['after']:.1f} levels (<= {SKY_GAP_MOST}), blue to red {ratio:.3f} (concept "
                   f"{concept['blue_to_red']}, within {BLUE_TO_RED_WITHIN}), rise to the horizon {rise:.4f}",
                   {"gap": round(gap["after"], 1), "blue_to_red": round(ratio, 4), "rise": round(rise, 4)},
                   {"gap": "lower"})


def judge_exposure(output, inputs, evidence):
    """No view is more black or more blown out than the place's concept pictures, by BLACK_OVER or BLOWN_OVER."""
    found = measures_of(output).get("exposure") or {}
    concept, views = found.get("concept"), found.get("views") or {}
    if not concept or not views:
        return checks.Verdict("exposure", checks.UNKNOWN, "no concept picture or no look to compare")
    off = [f"{view}: {value['black']:.1%} black, {value['blown']:.1%} blown (concept {concept['black']:.1%}, "
           f"{concept['blown']:.1%})" for view, value in views.items()
           if value["black"] > concept["black"] + BLACK_OVER or value["blown"] > concept["blown"] + BLOWN_OVER]
    blackest = max(value["black"] for value in views.values())
    brightest = max(value["blown"] for value in views.values())
    return verdict("exposure", not off, f"{len(views)} views, {len(off)} more black or blown than the concept; at most "
                   f"{blackest:.1%} black and {brightest:.1%} blown", {"black": blackest, "blown": brightest,
                                                                       "views_off": len(off)},
                   {"black": "lower", "blown": "lower", "views_off": "lower"}, off)


def judge_stage(output, inputs, evidence):
    """The seed with the light layer has no more placeholder or made-only faults than the seed alone."""
    found = measures_of(output)["stage_checks"]
    worse = [f"{place} {check} {sides['before'][check]} -> {sides['after'][check]}"
             for place, sides in found.items() for check in ("placeholders", "made_only")
             if sides["after"][check] > sides["before"][check]]
    counts = {f"{place}_{check}": sides["after"][check] for place, sides in found.items()
              for check in ("placeholders", "made_only")}
    return verdict("stage_no_worse", not worse, "; ".join(worse) or f"no worse: {counts}", counts,
                   {name: "lower" for name in counts})


def light_faults(folder):
    found = [f"no {name}" for name in ("measures.json", "lamps.json", layer.LAYER) if not (folder / name).exists()]
    return found + ([] if any(folder.glob("looks/*/*-look.png")) else ["no look"])


def light_files(place):
    """What the sweep and the measures read: the records and kits, the seed and the places it shows (the stage
    checks), the concepts; the views come with the layer."""
    inventory = stage_inputs.inventory_path(place)
    found = {"scene": "{data}/scene/{place}.json", "seed": "{seeds}/usd-r3/{place}", "grounds": "{data}/ground",
             "kit": "{data}/kit/{place}.json", **passes.place_files(place),
             "inventory": "{data}/inventory/" + inventory.name,
             "concepts": f"{{seeds}}/scene/{inventory.stem}/views", "square concepts": "{seeds}/scene/square/views",
             "old station concepts": "{seeds}/scene/old_station/views"}
    for name in neighbours(place):
        found[f"neighbour {name}"] = f"{{seeds}}/usd-r3/{name}"
        if (REPO / f"data/scene/{name}.json").exists():
            found.update(passes.place_files(name))
    for owner, _ in LAMP_KINDS.get(place, ()):
        found.update(passes.place_files(owner))
    return found


LIT = contracts.Contract("light", 1, light_faults, {"length": "metre", "up axis": "Y"})
RECORD = {"scene-record": ("scene-record", 1)}  # read where the place has the row (Runner.reads)
LAYER_STAGE = graph.Stage("light-layer", "place", make_layer, LAYERED,
                          (checks.Check("lamps placed", judge_placed), checks.Check("sky elements", judge_layer_sky)),
                          files=layer_files, after=RECORD, applies=applies)
PASSES_STAGE = graph.Stage("light-passes", "place", passes.make_passes, passes.PASSES,
                           (checks.Check("rendered", passes.judge_rendered),
                            checks.Check("no missing pictures", passes.judge_magenta)), files=passes.passes_files,
                           after={"light-layer": ("light-layer", 1), **RECORD}, paid=True, euros=passes.EUROS,
                           applies=applies)
HAZE_STAGE = graph.Stage("light-haze", "place", haze.make_haze, contracts.Contract("light-haze", 1,
                                                                                   passes.passes_faults),
                         (checks.Check("rendered", passes.judge_rendered),
                          checks.Check("no missing pictures", passes.judge_magenta)), files=passes.passes_files,
                         after={"light-layer": ("light-layer", 1), **RECORD}, paid=True, euros=haze.EUROS,
                         applies=lambda place: place in haze.HAZED)
LIGHT_STAGE = graph.Stage("light", "place", make_light, LIT,
                          (checks.Check("brightness", judge_brightness), checks.Check("lamps", judge_lamps),
                           checks.Check("sky elements", judge_sky_elements), checks.Check("heads", judge_heads),
                           checks.Check("earth", judge_earth), checks.Check("sky", judge_sky),
                           checks.Check("exposure", judge_exposure), checks.Check("stage_no_worse", judge_stage)),
                          files=light_files, after={"light-layer": ("light-layer", 1),
                                                    "light-passes": ("light-passes", 1),
                                                    "light-haze": ("light-haze", 1), **RECORD},
                          applies=applies)
ROWS = (LAYER_STAGE, PASSES_STAGE, HAZE_STAGE, LIGHT_STAGE)
