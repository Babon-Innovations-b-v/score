"""The light stage (experimental, PRD #6, until the owner reviews it; the paper-vs-world-1 audit's items 9 and 17): a
place's light layer, its lamps' strengths measured from one render of every lamp on its own, and the sky its record
holds, as three rows of the stage table.

    light-layer   (free) layers/light.usda over the place as the assembly lays it (passes.source: its record, bakes,
                  ground), with tools/usd/scene.py's own writers (layer.py): each lamp where the record puts it,
                  the floodlights' shafts; its sky from the environment concept's physics overhead at its site at its scene time
                  (sky.py: each light, shining body's disc, other body drawn with its face as its body-face-<body>
                  row made it, and backdrop, the old sky turned off), the day dome its air scatters; lamps.json
    light-passes  (paid) the seed with that layer rendered on the views of the place's own scene record (the
                  layer's views.json, passes.record_views), once, at passes.CHECK_SIZE, on one card class, each of
                  the place's own lamps in a Cycles light group of its own (inside/light_passes.py): per view the
                  look and the luminance of the whole picture and of each lamp alone
    light         (free) the sweep on the passes (mix.py): one scale for every lamp without a shaft (a floodlight's is
                  its shaft sweep's, 2026-10-11) bringing the place's brightness nearest its concept's, each blown-out
                  lamp turned down; those strengths written into the layer; the look at them mixed from the passes
                  (looks/), and every fault measured on it

    gates (light-layer)  lamps placed  every lamp of the record stands in the layer
                         lit           a lamp of its own, or (an open place) a sky light over the horizon
                                       (unlit_why): an unlit place is a gap before the paid render
                         drawn         the stage it lights draws something outside its sky (an empty one renders
                                       black under any light)
                         sky elements  as below, before anything is rendered
                         sky bodies    the sky's bodies, lights and backdrops where overhead.py has them at the
                                       scene's site at its scene time (sky.faults on the layer's geometry)

    gates (light)  brightness      the place's brightness within BRIGHT_WITHIN of its concept's, each view within
                                   VIEW_WITHIN (mix.py has the rules)
                   lamps           no lamp on screen unlit, none blown out
                   sky elements    every element the sky calls for is in the layer: every body drawn with its face
                                   (its body-face-<body> row's), the day dome, the shafts
                   heads           floodlight heads facing the eye glow (halo, fill, beam, veil: the rules set on
                                   environment 1's concept K04 on 2026-10-11)
                   bodies          each face-drawn body present in the views that frame it and lit on the side
                                   toward its sun (SHOWN_LEAST, LIT_LEAST, SUNWARD_LEVELS); where it stands and how
                                   big is the layer's sky bodies
                   sky             an outdoor place's sky within SKY_GAP_MOST levels of its concept's sky colour,
                                   its blue to red within BLUE_TO_RED_WITHIN
                   exposure        no view more black or blown out than its concept (BLACK_OVER, BLOWN_OVER)
                   stage_no_worse  the seed with the layer has no more placeholder or made-only faults than without

The owner's plan for light is baked per-lamp layers mixed live (memory, project-sound-and-light-layers). This stage is
its first half on the views: one pass a lamp, mixed at any strengths with no render again. The layer it delivers holds
live lights (UsdLux) at the measured strengths; no lamp's light is baked into the surfaces yet.

Every row reads the place's design only (2026-10-21): it applies at every designed place (the table's
designed("light")), reads the place's record from the scene-record row's output only (passes.record_of), renders
the places that record shows (passes.neighbours) each lit by its own record read beside, and measures the
floodlight heads of the kinds whose lamps light a shaft (haze.shafted_kinds); no hand-kept record, place or kind
list.
"""
import json
import pathlib
import shutil
import sys

import numpy as np
from PIL import Image

from score import checks, contracts, graph
from score.stages.light import haze, layer, measure, mix, needs, passes, sky
from score.stages.light.passes import groups_of, neighbours, views_of
from score.stages.scene_record import concept_light
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import made_only  # noqa: E402
import placeholders  # noqa: E402
import stage_inputs  # noqa: E402

WORK = PROPS_HOME / "work"
# The pass rules of 2026-10-11 (the light stage's first rows), set before any after-picture was made: half the
# concept's head halo and fill, a beam that lights its air, the place washed out by its haze at most VEIL_MOST, only
# heads whose lit face turns toward the eye judged (FACING_LEAST); a sky
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
# The share of a pixel's light the place's lamps may give for it to count as a sky body's (set 2026-10-12 on the
# Earth's disc after the first fan-out, kept for every body: body_measures).
BODY_LAMP_MOST = 0.1
# The sky bodies' rules (2026-10-22, set before any face-drawn body was rendered, when the Earth's NASA picture was
# retired for each body's face): a body framed by a view shows in it when at least SHOWN_LEAST of its disc stands off
# the sky round it (measure.SHOWN_LEVELS); it is present when it shows in at least one view that frames it. Its lit
# side is judged where its phase is between LIT_LEAST and 1 - LIT_LEAST and its sun's way is seen across the view: the
# median over those views of its sunward half's mean lightness over its far half's at least SUNWARD_LEVELS (0 to 255).
SHOWN_LEAST = 0.5
LIT_LEAST = 0.15
SUNWARD_LEVELS = 4.0
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
place_of = passes.place_of


def applies(place):
    """A place whose scene record the scene-record row writes from its design (passes.recorded): its views and
    lights are that record's. Its seed is an input like any other: a lost one is the place's gap, never a reason to
    leave the place unlit."""
    return passes.recorded(place)


# --- light-layer ----------------------------------------------------------------------------------------------------

def make_layer(inputs, out, seed, params):
    """The place's light layer over its stage as the assembly lays it before its layers (passes.source: the seed with
    its accepted scene record), its sky from the physics over its site (its kept sky, `sky` input) with each body's
    face its `body-face-<body>` row made (read while it stands), and lamps.json (each lamp, its strength there,
    whether it has a shaft)."""
    place = place_of(inputs)
    stage = passes.source(place, inputs, out / "source")
    found = layer.write(place, passes.record_of(place, inputs), stage, out, sky.read(inputs["sky"]) if "sky" in inputs
                        else None, sky.faces_of(inputs), sky.read(inputs["library"]))
    record = passes.record_of(place, inputs)
    inside = bool((record.get("environment") or {}).get("inside"))
    if not found["lamps"] or not inside:
        found["lamps"] += sun_lamps(place, out, stage)
    light = sky.read(inputs["concept light"]) if "concept light" in inputs else None
    if fill_wanted(light, found["lamps"], inside):
        found["lamps"].append(layer.write_fill(out, stage, place, light["scene"]["unseen_colour"], inside,
                                               record.get("ceiling"), inputs["lamp library"]))
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


def fill_wanted(light, lamps, inside):
    """Whether the place takes its concept's fill (layer.write_fill): its concept (`light`, its reading's concept
    light) shows light falling on it from no source in view, and no sky light reaches it (none over the horizon at its
    scene time, or an inside place, whose sky lights stand outside its shell)."""
    if not light or not light["scene"]["unseen"]:
        return False
    return inside or not any(lamp.get("sun") for lamp in lamps)


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


def unlit_why(lamps, inside, read=True):
    """Why the layer gives the place no light the render could measure, or None: no lamp of its own (nor its
    concept's fill) and no sky light over the horizon at its scene time; or an inside place (its plan's walls or roofs)
    with no lamp of its own nor fill, whose sky lights stand outside its shell. Rendered anyway, the views come back
    black or under the renderer's fixed stand-in sun, a light not in the design (2026-10-25: engineroom, camp and
    campgrounds, a paid render each). `read`: whether its concept's light is read (reading.concept_light)."""
    if [lamp for lamp in lamps if not lamp.get("sun") or lamp.get("fill")]:
        return None
    glowing = "no glowing row (its row kinds" + (", its concept's light)" if read else "; its concept's light is not "
                                                 "read: python -m score.review.reading <place>)")
    if not lamps:
        return f"no lamp of its own ({glowing}) and no sky light over the horizon at its scene time"
    if inside:
        return f"an inside place with no lamp of its own ({glowing}): its sky lights stand outside its shell"
    return None


def judge_lit(output, inputs, evidence):
    """The layer lights the place from its design (unlit_why), before light-passes is bought."""
    found = json.loads((output / "lamps.json").read_text())
    record = passes.record_of(found["place"], inputs)
    why = unlit_why(found["lamps"], bool((record.get("environment") or {}).get("inside")), "concept light" in inputs)
    fills = sum(1 for lamp in found["lamps"] if lamp.get("fill"))
    suns = sum(1 for lamp in found["lamps"] if lamp.get("sun")) - fills
    light = sky.read(inputs["concept light"]) if "concept light" in inputs else None
    night = light and light["scene"]["daylight"] and not suns and \
        "its concept shows daylight and no sun is over the horizon at its scene time (the environment plan's)"
    said = f"{len(found['lamps']) - suns - fills} lamps of its own, {suns} sky lights, {fills} concept fill" + \
        (f"; {night}" if night else "")
    measures = {"lamps": len(found["lamps"]) - suns - fills, "sky_lights": suns, "fill": fills}
    return verdict("lit", why is None, why or said, measures, findings=[why] if why else ([night] if night else ()))


def drawn_count(root, place):
    """The drawn prims (meshes and other gprims) of the stage at `root` outside its sky: what the views can see lit."""
    from pxr import Usd, UsdGeom
    sky_root = f"/{place}/Sky"
    opened = Usd.Stage.Open(str(root))  # held: a prim of a stage nobody holds is gone
    return sum(1 for prim in opened.Traverse()
               if prim.IsA(UsdGeom.Gprim) and not str(prim.GetPath()).startswith(sky_root))


def judge_drawn(output, inputs, evidence):
    """The stage the layer lights (passes.source) draws something outside its sky, before light-passes is bought: an
    empty one renders black under any light (2026-10-29: light-passes@base, every object of its record waiting on its
    model, no ground)."""
    import tempfile
    place = json.loads((output / "lamps.json").read_text())["place"]
    # on the store's disk: the source hard-links the seed, which fails across into /tmp (light-layer@airlock,
    # 2026-10-29), as settling's scratch does
    (PROPS_HOME / "store/cache").mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=PROPS_HOME / "store/cache") as folder:
        stage = passes.source(place, inputs, pathlib.Path(folder) / "source")
        drawn = drawn_count(stage / f"{place}.usda", place)
    waiting = sum(1 for entries in passes.record_of(place, inputs).values() if isinstance(entries, list)
                  for entry in entries if isinstance(entry, dict) and entry.get("waiting"))
    why = f"the stage draws nothing to light ({waiting} record entries waiting on their models)"
    return verdict("drawn", drawn > 0, why if not drawn else f"{drawn} drawn prims to light, {waiting} waiting",
                   {"drawn": drawn, "waiting": waiting}, findings=[why] if not drawn else ())


def missing_elements(found):
    """The sky elements ({name: [wanted, held]}) the record holds and the layer does not."""
    return [f"{name}: the record holds {wanted}, the layer {held}" for name, (wanted, held) in found.items()
            if held < wanted]


def judge_sky_bodies(output, inputs, evidence):
    """The sky's bodies, lights and backdrops stand where overhead.py says they are at the scene's site at its scene
    time, read off the layer's geometry (sky.held, sky.faults); unknown while the scene's site or scene time is not on
    the environment's plan (no kept sky)."""
    from pxr import Usd
    seen = sky.seen_of(sky.read(inputs["sky"])) if "sky" in inputs else None
    if seen is None:
        return checks.Verdict("sky bodies", checks.UNKNOWN, "no sky over this scene yet: its site or its scene time is "
                              "not on the environment's plan (score/review/scene_sky.py)")
    place = json.loads((output / "lamps.json").read_text())["place"]
    held = sky.held(Usd.Stage.Open(str(output / layer.LAYER)), place)
    faults = sky.faults(seen, held)
    counts = {group: len(held[group]) for group in ("bodies", "lights", "discs", "backdrops")}
    return verdict("sky bodies", not faults, "; ".join(faults[:3]) or
                   f"the sky as overhead.py has it: {counts['bodies']} bodies, {counts['lights']} lights, "
                   f"{counts['discs']} discs, {counts['backdrops']} backdrops", {"faults": len(faults), **counts},
                   {"faults": "lower"}, faults)


def judge_layer_sky(output, inputs, evidence):
    """Every element the record's sky holds is in the layer (sky_elements), before anything is rendered."""
    place = json.loads((output / "lamps.json").read_text())["place"]
    found = sky_elements(place, output, passes.record_of(place, inputs))
    missing = missing_elements(found)
    return verdict("sky elements", not missing, "; ".join(missing) or f"every element the record holds: {found}",
                   {"missing": len(missing)}, {"missing": "lower"}, missing)


LAYERED = contracts.Contract("light-layer", 1, layer_faults, {"length": "metre", "up axis": "Y"})


def layer_files(place):
    """The kit (its seat, its lenses: passes.place_files), the seed, the surface library's method (a shining body's
    disc is its glowing recipe), the library's lamp (its concept's fill), the scene's kept sky (sky.kept_input) and its
    concept's light (scene_record.concept_light) when it has them; the record is the scene-record row's output."""
    return {"seed": "{seeds}/usd-r3/{place}", "kit": "{data}/kit/{place}.json", **passes.SURFACES,
            "library": "{data}/library/materials.json", "lamp library": "{data}/library/lamps.json",
            **passes.place_files(place), **sky.kept_input(place), **concept_light.concept_light_input(place)}


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


def designed(place):
    """Whether the place has an approved design (its hand-in, prop_data.designed): its concept is its picked one."""
    import score.stages.props.prop_data as prop_data
    return prop_data.designed(place)


def concept_pictures(place):
    """The place's concept pictures: a designed place's picked concept (as rough-model reads it), else its
    inventory's plan views."""
    if designed(place):
        return [PROPS_HOME / "design/concepts" / f"{place}.png"]
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


def floodlight_sweep(place, passes_folder, scales, shafted, out, inputs):
    """The floodlights' strength (their shafts' light with them): the least of FLOODLIGHT_SCALES at which the heads
    rule holds on the looks mixed at it, else the layer's own (1), set into `scales`; the looks at the final strengths
    are left in out/looks. The layer's own strength is tried first and kept when it meets the rule: a floodlight is
    dimmed or brightened only where its gate needs it (2026-10-13: dimmed to the least passing strength, the square's
    heads read worse than its earlier accepted output while passing). What was tried, {scale: passed}."""
    tried = {}
    heads = bool(shafted) and bool(lamp_heads(place, inputs))
    order = (1.0, *(scale for scale in FLOODLIGHT_SCALES if scale != 1.0))
    for scale in (order if heads else (1.0,)):
        scales.update(dict.fromkeys(shafted, scale))
        mixed_looks(passes_folder, scales, shafted, out)
        if not heads:
            break
        summary = heads_summary(head_measures(place, out, inputs))
        tried[scale] = bool(summary and summary[0])
        if tried[scale]:
            return tried
    if tried:  # none met the rule: the floodlights stay at the layer's strength, the gate says what fails
        scales.update(dict.fromkeys(shafted, 1.0))
        mixed_looks(passes_folder, scales, shafted, out)
    return tried


def mixed_looks(passes_folder, scales, shafted, out):
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
    layer_copied(layer_folder, out)
    found = json.loads((layer_folder / "lamps.json").read_text())
    scales, swept = strengths(place, passes_folder, found["lamps"], layer_folder)
    own = {lamp["path"] for lamp in found["lamps"]}
    by_group = {group: path for group, path in groups_of(passes_folder).items() if path in own}
    intensity = {lamp["path"]: lamp["intensity"] for lamp in found["lamps"]}
    shafted = [group for group, path in by_group.items()
               if next(lamp for lamp in found["lamps"] if lamp["path"] == path)["shaft"]]
    record = passes.record_of(place, inputs)
    swept["floodlights"] = floodlight_sweep(place, passes_folder, scales, shafted, out, inputs)
    for lamp in found["lamps"]:
        group = next((name for name, path in by_group.items() if path == lamp["path"]), None)
        lamp["scale"] = scales.get(group, 1.0)
    layer.strengths(out / layer.LAYER, place, {by_group[group]: (intensity[by_group[group]], scale)
                                               for group, scale in scales.items()})
    layer.lamps_file(found, out)
    measures = {"place": place, "brightness": swept, "sky_elements": sky_elements(place, out, record),
                "stage_checks": stage_checks(place, layer_folder, inputs, out)}
    measures.update(fault_measures(place, out, passes_folder, inputs))
    (out / "measures.json").write_text(json.dumps(measures, indent=1) + "\n")


# --- the old faults' measures (the light stage's of 2026-10-11), on the looks at the measured strengths ------------

def rendered(out, name, kind="look"):
    return {path.name.removesuffix(f"-{kind}.png"): path for path in out.glob(f"looks/{name}/*-{kind}.png")}


def lamp_heads(place, inputs):
    """Each floodlight head a place's views show, its own and those of the places it shows (passes.shown_in): every
    glow part of a kind its design kit lays (its `kit`, a shown place's `kit <place>`: earth_seed's kit.json) whose
    lamps light a shaft (haze.shafted_kinds), as (its lens middle, half its bank's width, the nearest of its owner's
    shafted lights, its front)."""
    found = []
    for owner in (place, *passes.shown_in(inputs)):
        kit = json.loads(pathlib.Path(inputs["kit" if owner == place else f"kit {owner}"]).read_text())
        kinds = haze.shafted_kinds(owner, kit)
        if not kinds:
            continue
        lights = [entry for entry in passes.record_of(owner, inputs).get("lights", []) if entry.get("shaft")]
        for laid in kit["pieces"]:
            if laid["kind"] not in kinds or laid.get("part") != "glow":
                continue
            middle = layer.lens_middle(laid)
            light = min(lights, key=lambda entry: np.linalg.norm(np.asarray(entry["at"]) - middle)) if lights else None
            found.append((middle, laid["size"][0] / 2, light, -np.asarray(laid["z"], dtype=np.float64)))
    return found


def head_measures(place, out, inputs):
    """Every floodlight head on screen in every view, with its shafted lamps off (before) and on (after), and its
    beam's gain."""
    size, views = views_of(out)
    after, unlit = rendered(out, place), rendered(out, place, "unlit")
    found, veils = [], {}
    for view in views:
        if view["name"] not in after or view["name"] not in unlit:
            continue
        before_rgb, after_rgb = measure.picture(unlit[view["name"]]), measure.picture(after[view["name"]])
        # The veil is what the shafts' haze lays over the place: against the floodlights off (their floor light in it
        # too).
        veils[view["name"]] = measure.veil(before_rgb, after_rgb)
        for middle, half, light, front in lamp_heads(place, inputs):
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


def sky_prims(folder, kind):
    """The light layer's own sky prims of one kind (sky.py: "sky light", "sky body", "sky disc", "sky backdrop")."""
    from pxr import Usd
    stage = Usd.Stage.Open(str(folder / layer.LAYER))
    return stage, [prim for prim in stage.TraverseAll() if sky.tag(prim, "kind") == kind]


def faced_balls(folder):
    """[{"body", "centre", "radius", "lit"}] of each body of the layer's sky (sky.py) drawn with its face (its
    `body-face-<body>` row's, `score:face`), read off the layer's geometry; `lit` its phase as overhead.py gave it."""
    from pxr import Usd, UsdGeom
    stage, bodies = sky_prims(folder, "sky body")
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"])
    found = []
    for prim in (prim for prim in bodies if sky.tag(prim, "face")):
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        found.append({"body": sky.tag(prim, "sky:body"), "centre": list(box.GetMidpoint()),
                      "radius": (box.GetMax()[1] - box.GetMin()[1]) / 2.0, "lit": sky.tag(prim, "sky:lit")})
    return found


def sun_way(folder):
    """The way toward the layer's brightest sky light (sky.py's, by its lux) in the scene's frame, None with none."""
    _, lights = sky_prims(folder, "sky light")
    if not lights:
        return None
    brightest = max(lights, key=lambda prim: sky.tag(prim, "sky:lux") or 0.0)
    return sky.way(*sky.light_seen(brightest))


def lamp_share(held, shape):
    """The share of each pixel's light the place's lamps give (a view's passes, at half size), at `shape`."""
    share = sum(held[group].astype(np.float64) for group in held if group.startswith("lamp_")) / np.maximum(
        held["combined"].astype(np.float64), 1e-6) if len(held) > 1 else np.zeros(held["combined"].shape)
    full = np.repeat(np.repeat(share, 2, axis=0), 2, axis=1)
    return np.pad(full, ((0, shape[0] - full.shape[0]), (0, shape[1] - full.shape[1])), mode="edge")


def body_measures(place, out, passes_folder, balls, sun):
    """Each face-drawn body's disc (faced_balls) in every view whose frame holds it: how much of it shows and its
    sunward and far halves (measure.body), on the pixels the place's lamps do not light (BODY_LAMP_MOST of their
    light at most: a greenhouse's roof trusses, lit by its grow lights, stand across its sky). The sunward side is
    where the brightest sky light (`sun`, a way) falls on the ball, as the view sees it."""
    lamps = {view: held for view, (held, _, _) in view_passes(passes_folder, place).items()}
    size, views = views_of(out)
    after = rendered(out, place)
    found = []
    for view, entry in ((view, entry) for view in views for entry in balls):
        x, y, depth, focal = measure.where(view, size, entry["centre"])
        if x is None or view["name"] not in after:
            continue
        radius = focal * entry["radius"] / depth
        if x + radius < 0 or x - radius > size[0] or y + radius < 0 or y - radius > size[1]:
            continue
        rgb = measure.picture(after[view["name"]])
        toward = sunward(view, size, entry, sun, (x, y))
        usable = lamp_share(lamps[view["name"]], rgb.shape[:2]) <= BODY_LAMP_MOST
        found.append({"view": view["name"], "body": entry["body"], "lit": entry["lit"],
                      "disc_px": [round(x), round(y), round(radius)], "sun_seen": toward is not None,
                      "after": measure.body(rgb, x, y, radius, toward or (0.0, 0.0), usable)})
    return found


def sunward(view, size, entry, sun, middle):
    """The way in the view's picture from a ball's middle toward the point its sun lights most, None with no sun or
    with that way along the view (under half a pixel)."""
    if sun is None:
        return None
    lit_x, lit_y, _, _ = measure.where(view, size, np.asarray(entry["centre"]) + np.asarray(sun) * entry["radius"])
    if lit_x is None or np.hypot(lit_x - middle[0], lit_y - middle[1]) < 0.5:
        return None
    return (lit_x - middle[0], lit_y - middle[1])


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


def fault_measures(place, out, passes_folder, inputs):
    """The heads (where the views show a floodlight), the sky's bodies, the sky and the exposure, measured on the
    looks."""
    record = passes.record_of(place, inputs)
    found = {}
    if lamp_heads(place, inputs):
        heads = head_measures(place, out, inputs)
        found["heads"], found["veil"] = heads["heads"], heads["veil"]
    balls = faced_balls(out)
    if balls:
        found["bodies"] = body_measures(place, out, passes_folder, balls, sun_way(out))
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
    """What the record's air and the physics' sky call for against what the light layer holds: {element: [wanted,
    found]}: every body of the physics' sky drawn with its face (face_drawn), the day dome where the record's air
    scatters one and the physics gives it a light, each floodlight's shaft. Where each body and light stands and how
    big is the gate "sky bodies"."""
    held, bodies = sky_prims(out, "sky body")
    lights = record.get("lights", [])
    paths = {str(prim.GetPath()) for prim in held.TraverseAll()}
    shafts = sum(path.startswith(f"/{place}/Shafts/shaft_") and "_look" not in path for path in paths)
    domed = bool((record.get("environment") or {}).get("sky_dome")) and bool(sky_prims(out, "sky light")[1])
    return {"faces": [len(bodies), sum(map(face_drawn, bodies))],
            "sky_dome": [domed, f"/{place}/Sky/Dome" in paths],
            "shafts": [sum(bool(entry.get("shaft")) for entry in lights), shafts]}


def face_drawn(prim):
    """Whether a sky body's ball is bound to the face its `score:face` row made (sky.faced)."""
    from pxr import UsdShade
    row = sky.tag(prim, "face")
    material = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()[0]
    return bool(row) and bool(material) and sky.tag(material.GetPrim(), "from") == row


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
    """Every element the sky calls for is in the light layer: every body drawn with its face, the day dome, each
    floodlight's shaft (sky_elements)."""
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


def body_faults(discs):
    """Each way the face-drawn bodies' discs (body_measures) fail the sky bodies' rules: a body framed by views and
    shown in none, or one whose sunward half is not SUNWARD_LEVELS lighter than its far half (median over its views)."""
    faults = []
    for name in sorted({disc["body"] for disc in discs}):
        own = [disc for disc in discs if disc["body"] == name and disc["after"]]
        shown = [disc for disc in own if disc["after"]["shown"] >= SHOWN_LEAST]
        if own and not shown:
            faults.append(f"{name}: framed by {len(own)} views, shown in none (at least {SHOWN_LEAST} of its disc off "
                          "the sky round it)")
        judged = [disc["after"]["sunward"] - disc["after"]["away"] for disc in shown
                  if disc["sun_seen"] and LIT_LEAST < disc["lit"] < 1.0 - LIT_LEAST
                  and disc["after"]["sunward"] is not None and disc["after"]["away"] is not None]
        if judged and float(np.median(judged)) < SUNWARD_LEVELS:
            faults.append(f"{name}: its sunward half {float(np.median(judged)):.1f} levels over its far half in "
                          f"{len(judged)} views (at least {SUNWARD_LEVELS}): not lit from its sun")
    return faults


def judge_bodies(output, inputs, evidence):
    """Each body of the sky drawn with its face reads in the views as the physics has it: present where a view frames
    it and lit on the side toward its sun (body_faults); where it stands and how big is the light layer's sky bodies
    gate, that it is drawn with its face its sky elements."""
    discs = [disc for disc in measures_of(output).get("bodies", []) if disc["after"]]
    if not discs:
        return verdict("bodies", True, "no face-drawn body of the sky on screen in any view", {})
    faults = body_faults(discs)
    return verdict("bodies", not faults, "; ".join(faults) or f"{len({disc['body'] for disc in discs})} bodies on "
                   f"screen in {len(discs)} views: each present and lit from its sun",
                   {"faults": len(faults), "discs": len(discs)}, {"faults": "lower"}, faults)


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
    """What the sweep and the measures read besides the scene records: the kits, the seed and the places it shows
    (the stage checks, their floodlight heads), the concepts; the views come with the layer."""
    found = {"seed": "{seeds}/usd-r3/{place}", "kit": "{data}/kit/{place}.json", **passes.SURFACES,
             **passes.place_files(place), "inventory": stage_inputs.inventory_pattern(place),
             # which lamps light a shaft (haze.shafted_kinds): the glowing rows each place's plan aims
             "row kinds": "{data}/checks/row-kinds.json", "lamp library": "{data}/library/lamps.json",
             **aimed_files(place)}
    if designed(place):  # its picked concept
        found["concepts"] = "{home}/design/concepts/" + f"{place}.png"
    else:
        found["concepts"] = f"{{seeds}}/scene/{place}/views"
    for name in neighbours(place):
        found[f"neighbour {name}"] = f"{{seeds}}/usd-r3/{name}"
        found.update(passes.place_files(name))
        found.update(aimed_files(name))
    return found


def aimed_files(name):
    """A place's kept plan and scene inventory (the design's), which say which of its lamps are aimed and light a
    shaft (haze.shafted_kinds); none for a place with no kept plan (it aims nothing)."""
    if not (passes.KEPT / "plans" / f"{name}.json").exists():
        return {}
    found = {f"plan {name}": "{home}/design/plans/" + f"{name}.json"}
    if (passes.KEPT / "inventory" / f"{name}.json").exists():
        found[f"inventory {name}"] = "{home}/design/inventory/" + f"{name}.json"
    return found


LIT = contracts.Contract("light", 1, light_faults, {"length": "metre", "up axis": "Y"})
RECORD = {passes.RECORD: ("scene-record", 1)}  # the place's own as an after, each shown place's beside
LAYER_STAGE = graph.Stage("light-layer", "place", make_layer, LAYERED,
                          (checks.Check("lamps placed", judge_placed), checks.Check("lit", judge_lit),
                           checks.Check("drawn", judge_drawn),
                           checks.Check("sky elements", judge_layer_sky), checks.Check("sky bodies", judge_sky_bodies)),
                          files=layer_files, after={**RECORD, **passes.LAID}, applies=applies)
PASSES_STAGE = graph.Stage("light-passes", "place", passes.make_passes, passes.PASSES,
                           (checks.Check("rendered", passes.judge_rendered),
                            checks.Check("no missing pictures", passes.judge_magenta)), files=passes.passes_files,
                           after={"light-layer": ("light-layer", 1), **RECORD, **passes.LAID}, paid=True, euros=passes.EUROS,
                           beside=RECORD, neighbours=neighbours, applies=applies)
LIGHT_STAGE = graph.Stage("light", "place", make_light, LIT,
                          (checks.Check("brightness", judge_brightness), checks.Check("lamps", judge_lamps),
                           checks.Check("sky elements", judge_sky_elements), checks.Check("heads", judge_heads),
                           checks.Check("bodies", judge_bodies), checks.Check("sky", judge_sky),
                           checks.Check("exposure", judge_exposure), checks.Check("stage_no_worse", judge_stage)),
                          files=light_files, after={"light-layer": ("light-layer", 1),
                                                    "light-passes": ("light-passes", 1), **RECORD, **passes.LAID},
                          beside=RECORD, neighbours=neighbours, applies=applies)
ROWS = (LAYER_STAGE, PASSES_STAGE, LIGHT_STAGE)
