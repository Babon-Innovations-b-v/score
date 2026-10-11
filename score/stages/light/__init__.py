"""The light stage (experimental, PRD #6, world 1's finish of 2026-10-11, task `light`): the lamps, the sky and the
stage's backdrop that the paper-vs-world-1 audit found wrong (items 9 and 17), each fault measured before and after
on the same rendered views and against the place's concept, never judged by eye.

    .venv/bin/python -m score.stages.light run lightkit            # the square's new kit pieces, baked (paid)
    .venv/bin/python -m score.stages.light run sweep@square ...    # a lamp's or a sky's strength, measured (paid)
    .venv/bin/python -m score.stages.light run light@square ...    # the place made again and judged (paid)
    .venv/bin/python -m score.stages.light status <node> ...

What changed in the world's data and code (the scene records, tools/usd, the square's kit builders) is what a place
is made from; these stages make the places again from it and judge the result:

    lightkit   (world) the square's backdrop as concept K04's proscenium and its floodlight towers' round lamps,
               built in code and baked with the library's surfaces on rented cards (route.py late-plan,
               library_bake.py); gates: the model check on each built piece and the concept's stage parts present
    sweep      (place) the place exported, then one record number tried at several strengths on a few views (a
               lamp's shaft of light or a day sky's brightness), each measured against the concept; the record
               holds the least strength that meets the light gate's rule for the fault (the shafts), or, where the
               rule is nearness to the concept, the nearest (the sky), written into the record from this output
    light      (place) the place exported with the worktree's code and data over its round-three stage's other
               layers, rendered on the round-three demo's own views (frames 000 and 128 of each shot) on rented cards,
               and measured against the demo's frames of the same views (before) and the concept; gates: the fault's
               measure fixed, and the placeholder and made-only checks no worse than before

Every render runs inside the runner's clearance (score.adapters.compute) through tools/props/cloud/blender_cloud.py,
its jobs spread over L4, L40S and H100 cards (gpu-24gb, gpu-48gb, gpu-80gb) in every zone the cloud has stock.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import numpy as np

from score import checks, contracts, graph
from score.stages import world1
from score.stages.light import measure
from score.stages.light.kit import KIT
from score.store import PROPS_HOME, Store

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import made_only  # noqa: E402
import placeholders  # noqa: E402

PYTHON = sys.executable  # the framework's environment the runner runs in
# The tools these stages run write no bytecode beside their sources: those folders are the stages' declared inputs,
# and a cache written mid-run would read as an input changed while the node ran.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
WORK = PROPS_HOME / "work"
SEEDS = WORK / "usd-r3"
DEMO = WORK / "demo/world1-r4"
CARDS = "gpu-24gb,gpu-48gb,gpu-80gb"
WHO = "score light stage"
# How each place's base is made again: export_r3.sh's model folders (world1-night/gate/tools/export_r3.sh), with
# `{kit}` the lightkit stage's made models.
MODELS = {
    "square": ["package/square/objects", "place/square-rr1/made", "{kit}"],
    "launch": ["package/launch/objects"],
    "old_station": ["package/old_station/objects"],
    "greenhouse": ["package/greenhouse/objects"],
    "camp": ["package/camp-paint1/objects", "package/camp/objects", "place/camp-late1/made", "remake-retired/made/camp",
             "{camp late}"],
    "campgrounds": ["place/campgrounds-paint1/package/objects"],
}
# The camp's own airlock and link (main's 9e77a36): the late_bake@camp stage's accepted output, by its hash, a
# declared input of these stages (PLACE_FILES).
CAMP_LATE = PROPS_HOME / "store/cache/checkouts/d9d462cefefa3ae1952090928726c4d615be61ccc86c804c44dd9b0814db0432/made"
# What each node makes again (the place and a place it shows whose record changed) and whose views it renders (the
# camp grounds' film is drawn on the camp's stage).
EXPORTS = {"square": ("square", "launch"), "launch": ("launch", "square"), "old_station": ("old_station",),
           "greenhouse": ("greenhouse",), "camp": ("camp", "campgrounds")}
VIEWS = {"square": ("square",), "launch": ("launch",), "old_station": ("old_station",),
         "greenhouse": ("greenhouse",), "camp": ("campgrounds",)}
FRAMES = ("-000", "-128")
VIEWS_A_JOB = 2
MINUTES_A_VIEW = 4
# The concepts each fault is measured against (the coordinator's picks, data/inventory/<place>.json).
CONCEPTS = {"square": WORK / "scene/square/views/K04.png", "old_station": WORK / "scene/old_station/views/C4.png",
            "campgrounds": WORK / "scene/campgrounds/views/K05.png"}
# The concept's measures, worked out by measure.py on the concepts above (2026-10-11): K04's two floodlight heads,
# C4's Earth, K05's sky over its far hills (rows 0 to 150).
CONCEPT_HEADS = (((663, 532), 49.0), ((1332, 558), 44.5))
CONCEPT_EARTH = ((719, 262), 53.0)
CONCEPT_SKY_ROWS = (0, 150)
# The pass rules, set before any after-picture was made: half the concept's head halo and fill, a beam that lights
# its air, an Earth disc at most a quarter smooth (the concept's 0.0), a sky within 20 levels of the concept's colour, its
# blue to red within 0.15 of the concept's.
HALO_LEAST = 0.08
FILL_LEAST = 0.28
BEAM_LEAST = 0.02
# Added 2026-10-11 after the first shaft sweep, before any light node of a lit place ran: the shafts may not wash the
# place out (its lower part no more than 0.04 of white lighter than before; the sweep's 0.05 share of the record's
# density laid a milky veil over the whole square).
VEIL_MOST = 0.04
# Set 2026-10-11 after the first launch render, from the audit's own words (the fault is lamps whose faces read as
# white grids): only heads whose lit face turns toward the eye (the cosine between the lens's front and the way to
# the eye over FACING_LEAST) are judged; the launch's pad lamps face the rocket, so the balcony sees most of them
# side-on or from behind, and the square's towers it does see face it (they were not in the launch node's measure).
FACING_LEAST = 0.2
SMOOTH_MOST = 0.25
SKY_GAP_MOST = 20.0
BLUE_TO_RED_WITHIN = 0.15
# A sweep's strengths, as shares of the record's own number: the camp's sky first swept 0.25 to 4 (4 nearest the
# concept); the square's shafts, first 48 m long (to the ground they light), fogged the whole square at 0.25 to 4 of
# 0.02 a metre and veiled it at 0.05 and 0.1, so they are 12 m long round each lamp and swept again at 0.25 to 4.
SWEEP = {"square": (0.25, 0.5, 1.0, 2.0, 4.0), "launch": (0.25, 0.5, 1.0, 2.0, 4.0),
         "camp": (0.25, 0.5, 1.0, 2.0, 4.0)}
SWEEP_VIEWS = {"square": ("shot0-000", "shot1-000"), "launch": ("shot1-000", "shot2-000"),
               "camp": ("shot0-000", "shot1-000")}


# --- making a place again ----------------------------------------------------------------------------------------

def scene_of(place):
    return json.loads((REPO / f"data/scene/{place}.json").read_text())


def referenced(place):
    """The other places a place's stage shows (its record's `places`), by their stage's name."""
    return sorted({entry["stage"] for entry in scene_of(place).get("places", [])})


def tree_for(node_place, tree, kit):
    """A folder of stages to render from: every place this node makes again, exported here with the worktree's code
    over a copy of its round-three stage's other layers, and every place they show copied from round three (hard
    links: nothing writes them)."""
    made = EXPORTS[node_place]
    shown = sorted({other for place in made for other in referenced(place)} - set(made))
    for place in shown:
        subprocess.run(["cp", "-al", str(SEEDS / place), str(tree / place)], check=True)
    for place in made:
        export_place(place, tree / place, kit)
    return made


def base_files(seed):
    """What of a round-three stage is the base's own and so not copied (export writes it again; a picture left there,
    the Earth's, would be kept as it was): the base layer, its models and their pictures, and the old checks."""
    def ignored(folder, names):
        folder = pathlib.Path(folder)
        if folder == seed:
            return {"checks", "manifest.json", "settle"} & set(names)
        if folder == seed / "layers":
            return {"base.usda"} & set(names)
        if folder == seed / "assets":
            return {name for name in names if name == "textures" or name.endswith(".usdc")}
        return set()
    return ignored


def export_place(place, folder, kit):
    """One place exported again into `folder`: its round-three stage's layers other than the base copied (cast,
    sound, motion, effects, edits), then tools/usd/export.py writing the base and the root over them."""
    shutil.copytree(SEEDS / place, folder, ignore=base_files(SEEDS / place))
    named = {"{kit}": str(kit), "{camp late}": str(CAMP_LATE)}
    models = [named.get(path, str(WORK / path)) for path in MODELS[place]]
    command = ["systemd-run", "--user", "--scope", "-q", "-p", "MemoryMax=12G", str(PYTHON),
               str(REPO / "tools/usd/export.py"), place, "--models", *models, "--out", str(folder)]
    subprocess.run(command, check=True, cwd=REPO, stdout=subprocess.DEVNULL)


def chosen_views(name, only=None):
    """A demo place's views on the frames FRAMES (or the named ones), as the round-three demo drew them."""
    views = json.loads((DEMO / f"views/{name}.json").read_text())
    picked = [view for view in views["views"] if (view["name"] in only if only else view["name"].endswith(FRAMES))]
    return views["size"], picked


def view_jobs(stage_root, inputs, views, size, out, label):
    """blender_cloud jobs rendering `views` of a stage, VIEWS_A_JOB a job, each into its own folder of `out`."""
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for start in range(0, len(views), VIEWS_A_JOB):
        part = views[start:start + VIEWS_A_JOB]
        folder = out / f"{label}-{start // VIEWS_A_JOB}"
        spec = out / f"{label}-{start // VIEWS_A_JOB}.views.json"
        spec.write_text(json.dumps({"size": size, "views": [dict(view, look_only=True) for view in part]}))
        jobs.append({"script": "tools/blender/inside/usd_views.py", "args": [str(stage_root), str(spec), str(folder)],
                     "inputs": [*map(str, inputs), str(spec)], "outputs": [str(folder)],
                     "minutes": MINUTES_A_VIEW * len(part)})
    return jobs


def render(jobs, folder):
    """Run the jobs on rented cards, spread over as many machines as finish them soonest."""
    paths = []
    for number, job in enumerate(jobs):
        path = folder / f"job-{number}.json"
        path.write_text(json.dumps(job, indent=1))
        paths.append(str(path))
    subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/blender_cloud.py"), *paths, "--who", WHO,
                    "--classes", CARDS], check=True, cwd=REPO)


def rendered(out, name):
    """Every rendered look of the node, by view name."""
    return {path.name.removesuffix("-look.png"): path for path in out.glob(f"after/{name}-*/*-look.png")}


def place_root(tree, view_name):
    """The stage file a demo place's views are drawn on (the camp grounds' on the camp's)."""
    stage = "camp" if view_name == "campgrounds" else view_name
    return tree / stage / f"{stage}.usda"


def make_place(inputs, out, seed, params):
    """Export the node's places again, render the demo's views of them, measure every fault before and after, and
    keep the exported stages, the renders and the measures (the copied round-three stages are not kept)."""
    place = json.loads(pathlib.Path(inputs["scene"]).read_text())["place"]
    tree = out / "stages"
    tree.mkdir(parents=True)
    kit = pathlib.Path(inputs["lightkit"]) / "made"
    tree_for(place, tree, kit)
    jobs = []
    for name in VIEWS[place]:
        size, views = chosen_views(name)
        stage = place_root(tree, name)
        jobs += view_jobs(stage, [tree / child.name for child in tree.iterdir()], views, size, out / "after", name)
    render(jobs, out / "after")
    (out / "measures.json").write_text(json.dumps(place_measures(place, out), indent=1) + "\n")
    for child in list(tree.iterdir()):
        if child.name not in EXPORTS[place]:
            shutil.rmtree(child)


# --- the measures ------------------------------------------------------------------------------------------------

# The floodlights each place's views show: its own, and the square's towers seen from the launch view (the audit's
# "searchlights as white grids" there are the square's towers in front of the camera).
LAMP_KINDS = {"square": (("square", "square_far_floodlight_tower"),),
              "launch": (("launch", "launch_far_pad_floodlight"), ("square", "square_far_floodlight_tower"))}


def lamp_heads(place):
    """Each floodlight lamp a place's views show as (its lens middle, half its bank's width, its light, its front):
    the kit's glow parts of the floodlight kinds and the record's spot light standing on each (the places share the
    Earth site's frame)."""
    found = []
    for owner, kind in LAMP_KINDS[place]:
        kit = json.loads((REPO / f"data/kit/{owner}.json").read_text())
        lights = [entry for entry in scene_of(owner)["lights"] if entry.get("shaft")]
        for laid in kit["pieces"]:
            if laid["kind"] != kind or laid.get("part") != "glow":
                continue
            middle = np.asarray(laid["at"]) + np.asarray(laid["y"]) * laid["size"][1] / 2
            light = min(lights, key=lambda entry: np.linalg.norm(np.asarray(entry["at"]) - middle))
            found.append((middle, laid["size"][0] / 2, light, -np.asarray(laid["z"], dtype=np.float64)))
    return found


def head_measures(place, name, out):
    """Every floodlight head on screen in every rendered view, before and after, and its beam's gain."""
    size, views = chosen_views(name)
    found = []
    after = rendered(out, name)
    veils = {}
    for view in views:
        if view["name"] not in after:
            continue
        before_rgb = measure.picture(DEMO / f"frames/{name}/{view['name']}-look.png")
        after_rgb = measure.picture(after[view["name"]])
        veils[view["name"]] = measure.veil(before_rgb, after_rgb)
        for middle, half, light, front in lamp_heads(place):
            x, y, depth, focal = measure.where(view, size, middle)
            if x is None or not (0 <= x < size[0] and 0 <= y < size[1]):
                continue
            radius = focal * half / depth
            axis = [measure.where(view, size, np.asarray(light["at"]) + (np.asarray(light["aim"]) -
                                                                          np.asarray(light["at"])) * share)
                    for share in (0.15, 0.3, 0.45)]
            points = [(px, py) for px, py, _, _ in axis if px is not None and 0 <= px < size[0] and 0 <= py < size[1]]
            toward_eye = np.asarray(view["eye"], dtype=np.float64) - middle
            found.append({"view": view["name"], "at_px": [round(x), round(y)],
                          "faces_eye": round(float(front @ toward_eye / np.linalg.norm(toward_eye)), 3),
                          "before": measure.head(before_rgb, x, y, radius), "after": measure.head(after_rgb, x, y, radius),
                          "beam_gain": measure.beam(before_rgb, after_rgb, points, max(radius, 6.0))})
    return {"heads": found, "veil": veils}


def earth_measures(place, name, out):
    """The Earth's disc in every rendered view that shows it, before and after."""
    entry = next(item for group in ("structure", "ground") for item in scene_of(place).get(group, [])
                 if item.get("name") == "earth")
    size, views = chosen_views(name)
    after = rendered(out, name)
    found = []
    for view in views:
        x, y, depth, focal = measure.where(view, size, entry.get("placed_at", entry["centre"]))
        if x is None or view["name"] not in after:
            continue
        radius = focal * entry["radius"] / depth
        if x + radius < 0 or x - radius > size[0] or y + radius < 0 or y - radius > size[1]:
            continue
        before_rgb = measure.picture(DEMO / f"frames/{name}/{view['name']}-look.png")
        after_rgb = measure.picture(after[view["name"]])
        found.append({"view": view["name"], "disc_px": [round(x), round(y), round(radius)],
                      "before": measure.disc(before_rgb, x, y, radius), "after": measure.disc(after_rgb, x, y, radius),
                      "smooth": measure.smooth(before_rgb, after_rgb, x, y, radius)})
    return found


def sky_measures(name, out):
    """The day sky in every rendered view, before and after, against concept K05's."""
    concept = measure.concept_sky(measure.picture(CONCEPTS["campgrounds"]), CONCEPT_SKY_ROWS)
    after = rendered(out, name)
    found = []
    for view_name, path in sorted(after.items()):
        found.append({"view": view_name, **measure.sky(measure.picture(DEMO / f"frames/{name}/{view_name}-look.png"),
                                                       measure.picture(path), concept)})
    return {"concept": concept, "views": found}


def concept_measures():
    """The concepts' own measures, worked out the same way."""
    square = measure.picture(CONCEPTS["square"])
    old = measure.picture(CONCEPTS["old_station"])
    (x, y), radius = CONCEPT_EARTH
    return {"heads": [measure.head(square, hx, hy, hr) for (hx, hy), hr in CONCEPT_HEADS],
            "earth": measure.disc(old, x, y, radius)}


def stage_checks(place, out):
    """The placeholder and made-only checks on the stage made again and on its round-three stage: fault counts."""
    found = {}
    for side, root in (("before", SEEDS / place / f"{place}.usda"), ("after", out / "stages" / place / f"{place}.usda")):
        found[side] = {"placeholders": len(placeholders.check(str(root))), "made_only": len(made_only.check(str(root)))}
    return found


def place_measures(place, out):
    """Every fault the node fixes, measured before and after on the same views, with the concept's measures."""
    found = {"place": place, "concept": concept_measures(),
             "stage_checks": {made: stage_checks(made, out) for made in EXPORTS[place]}}
    if place in ("square", "launch"):
        heads = head_measures(place, place, out)
        found["heads"], found["veil"] = heads["heads"], heads["veil"]
    if place in ("old_station", "greenhouse"):
        found["earth"] = earth_measures(place, place, out)
    if place == "camp":
        found["sky"] = sky_measures("campgrounds", out)
    return found


# --- the gates ---------------------------------------------------------------------------------------------------

def measures_of(output):
    return json.loads((output / "measures.json").read_text())


def judge_heads(output, inputs, evidence):
    """Each floodlight head that can read as a white grid (on screen with its lit face toward the eye: FACING_LEAST;
    one seen side-on or from behind shows no face) now glows as concept K04's do: halo and fill
    (medians over those heads after) at least half the concept's, its beam lighting the air under it, and no view's
    lower part washed out by the haze (VEIL_MOST)."""
    found = measures_of(output)
    if "heads" not in found:
        return verdict("heads", True, "no floodlight in this place", {})
    heads = [head for head in found["heads"] if head["after"] and head["before"]
             and head["faces_eye"] >= FACING_LEAST]
    if not heads:
        return checks.Verdict("heads", checks.UNKNOWN, "no floodlight head faces the eye in any rendered view")
    halo = {side: float(np.median([head[side]["halo"] for head in heads])) for side in ("before", "after")}
    fill = {side: float(np.median([head[side]["fill"] for head in heads])) for side in ("before", "after")}
    gains = [head["beam_gain"] for head in heads if head["beam_gain"] is not None]
    gain = float(np.median(gains)) if gains else 0.0
    washed = max(found["veil"].values())
    passed = (halo["after"] >= HALO_LEAST and fill["after"] >= FILL_LEAST and gain >= BEAM_LEAST
              and washed <= VEIL_MOST)
    return verdict("heads", passed, f"{len(heads)} heads facing the eye of {len(found['heads'])} on screen: halo "
                   f"{halo['before']:.3f} -> {halo['after']:.3f} (>= {HALO_LEAST}), fill {fill['before']:.3f} -> "
                   f"{fill['after']:.3f} (>= {FILL_LEAST}), beam gain {gain:.3f} (>= {BEAM_LEAST}), the place washed "
                   f"out by at most {washed:.3f} (<= {VEIL_MOST})",
                   {"halo": round(halo["after"], 4), "fill": round(fill["after"], 4), "beam": round(gain, 4),
                    "veil": round(washed, 4), "facing_heads": len(heads)},
                   {"halo": "higher", "fill": "higher", "beam": "higher", "veil": "lower"})


def judge_earth(output, inputs, evidence):
    """The Earth reads as the real planet, not a flat-painted disc: at most SMOOTH_MOST of its lit disc smooth
    (measure.smooth; median over the views showing it), where concept C4's is 0.0.

    The first rule (the disc's eight commonest colours at most twice C4's share) was replaced on 2026-10-11 after the
    first renders of the turned Earth: it read the render's brightness and what stands in front of the Earth, not its
    paint (the greenhouse's roof trusses and purple light cross its disc; the real Earth in the old station's half
    light still scored 0.40 to 0.69). Its numbers stay in measures.json. The replacement's limit was set from the
    concept alone (0.0) before it was worked out on any render: a quarter of the disc."""
    found = measures_of(output)
    if "earth" not in found:
        return verdict("earth", True, "no Earth in this place", {})
    discs = [disc["smooth"] for disc in found["earth"] if disc.get("smooth") and disc["smooth"]["after"] is not None
             and disc["smooth"]["before"] is not None]
    if not discs:
        return checks.Verdict("earth", checks.UNKNOWN, "the Earth is on screen in no rendered view")
    smooth = {side: float(np.median([disc[side] for disc in discs])) for side in ("before", "after")}
    passed = smooth["after"] <= SMOOTH_MOST
    return verdict("earth", passed, f"{len(discs)} views: smooth share of the lit disc {smooth['before']:.3f} -> "
                   f"{smooth['after']:.3f} (<= {SMOOTH_MOST}; concept C4's 0.0)", {"smooth": round(smooth["after"], 4)},
                   {"smooth": "lower"})


def judge_sky(output, inputs, evidence):
    """Mars's day sky reads as concept K05's: within SKY_GAP_MOST levels of its colour and its blue to red within
    BLUE_TO_RED_WITHIN (medians over the views). Its rise to the horizon is reported, not judged: the rule first set
    (no darker toward the horizon) was dropped on 2026-10-11 before any light node judged a sky, because K05's own sky
    is flat (rise 0.006), the measure moved by 0.03 between the before frames' views on the flat wall alone (its
    pixels take in the far ground the wall hid), and a sky looked at under the sun is lighter upward."""
    found = measures_of(output)
    if "sky" not in found:
        return verdict("sky", True, "no day sky in this place", {})
    views = [view for view in found["sky"]["views"] if view["after"] and view["before"]]
    if not views:
        return checks.Verdict("sky", checks.UNKNOWN, "no sky measured in any rendered view")
    concept = found["sky"]["concept"]
    gap = {side: float(np.median([view[side]["gap_to_concept"] for view in views])) for side in ("before", "after")}
    ratio = float(np.median([view["after"]["blue_to_red"] for view in views]))
    rise = float(np.median([view["after"]["rise_to_horizon"] for view in views]))
    passed = gap["after"] <= SKY_GAP_MOST and abs(ratio - concept["blue_to_red"]) <= BLUE_TO_RED_WITHIN
    return verdict("sky", passed, f"{len(views)} views: colour gap to the concept {gap['before']:.1f} -> "
                   f"{gap['after']:.1f} levels (<= {SKY_GAP_MOST}), blue to red {ratio:.3f} (concept "
                   f"{concept['blue_to_red']}, within {BLUE_TO_RED_WITHIN}), rise to the horizon {rise:.4f} "
                   f"(the concept's {concept['rise_to_horizon']}; reported, not judged)",
                   {"gap": round(gap["after"], 1), "blue_to_red": round(ratio, 4), "rise": round(rise, 4)},
                   {"gap": "lower"})


def judge_stage(output, inputs, evidence):
    """The places made again have no more placeholder or made-only faults than their round-three stages."""
    found = measures_of(output)["stage_checks"]
    worse = [f"{place} {check} {sides['before'][check]} -> {sides['after'][check]}"
             for place, sides in found.items() for check in ("placeholders", "made_only")
             if sides["after"][check] > sides["before"][check]]
    counts = {f"{place}_{check}": sides["after"][check] for place, sides in found.items()
              for check in ("placeholders", "made_only")}
    return verdict("stage_no_worse", not worse, "; ".join(worse) or f"no worse: {counts}", counts,
                   {name: "lower" for name in counts})


def place_faults(folder):
    wanted = ["measures.json"]
    found = [f"no {name}" for name in wanted if not (folder / name).exists()]
    return found + ([] if any(folder.glob("after/*/*-look.png")) else ["no rendered view"])


def verdict(check, passed, reason, measures, better=None):
    return checks.Verdict(check, checks.PASS if passed else checks.FAIL, reason, measures, better or {})


LIT_PLACE = contracts.Contract("lit-place", 1, place_faults, {"length": "metre", "up axis": "Y"})
PLACE_FILES = {"scene": "{data}/scene/{place}.json", "scenes": "{data}/scene", "kits": "{data}/kit",
               "inventories": "{data}/inventory", "library": "{data}/library", "ground": "{data}/ground",
               "characters": "{data}/characters", "parts": "{data}/parts", "seed set": "{seeds}/usd-r3/inputs.json",
               "seed": "{seeds}/usd-r3/{place}", "demo views": "{seeds}/demo/world1-r4/views",
               "stage code": "{data}/../tools/usd", "renderer": "{data}/../tools/blender/inside",
               "camp late models": str(CAMP_LATE), "camp grounds seed": "{seeds}/usd-r3/campgrounds"}
LIGHT = graph.Stage("light", "place", make_place, LIT_PLACE,
                    (checks.Check("heads", judge_heads), checks.Check("earth", judge_earth),
                     checks.Check("sky", judge_sky), checks.Check("stage_no_worse", judge_stage)),
                    files=PLACE_FILES, after={"lightkit": ("kit-models", 1)}, paid=True, euros=6.0)


# --- the sweep ---------------------------------------------------------------------------------------------------

def overrides(place, folder, share):
    """A root over the exported stage with the place's sweep number at `share` of the record's: every lamp shaft's
    density, or the day sky's strength."""
    root = folder / f"{place}.usda"
    from pxr import Sdf, Usd
    stage = Usd.Stage.Open(str(root))
    layer = Sdf.Layer.CreateNew(str(folder / f"layers/sweep-{share}.usda"))
    edit = Usd.Stage.Open(layer)
    for prim in stage.Traverse():
        for name in ("score:haze_density", "score:sky_strength"):
            attribute = prim.GetAttribute(name)
            if attribute and (prim.GetName().startswith("shaft_") or name == "score:sky_strength"):
                edit.OverridePrim(prim.GetPath()).CreateAttribute(name, Sdf.ValueTypeNames.Float).Set(
                    float(attribute.Get()) * share)
    layer.Save()
    swept = Sdf.Layer.CreateNew(str(folder / f"{place}-sweep-{share}.usda"))
    swept.subLayerPaths.append(f"./layers/sweep-{share}.usda")
    swept.subLayerPaths.append(f"./{place}.usda")
    swept.defaultPrim = place
    swept.pseudoRoot.SetInfo("upAxis", "Y")  # the stage's own units, or a reader takes centimetres and z up
    swept.pseudoRoot.SetInfo("metersPerUnit", 1.0)
    swept.Save()
    return folder / f"{place}-sweep-{share}.usda"


def make_sweep(inputs, out, seed, params):
    """Export the node's places, render the sweep views at every strength in SWEEP, and measure each."""
    place = json.loads(pathlib.Path(inputs["scene"]).read_text())["place"]
    tree = out / "stages"
    tree.mkdir(parents=True)
    tree_for(place, tree, pathlib.Path(inputs["lightkit"]) / "made")
    name = VIEWS[place][0]
    size, views = chosen_views(name, SWEEP_VIEWS[place])
    stage_place = "camp" if name == "campgrounds" else name
    jobs = []
    for share in SWEEP[place]:
        root = overrides(stage_place, tree / stage_place, share)
        jobs += view_jobs(root, [tree / child.name for child in tree.iterdir()], views, size, out / "after",
                          f"{name}@{share}")
    render(jobs, out / "after")
    found = {}
    for share in SWEEP[place]:
        looks = {path.name.removesuffix("-look.png"): path for path in out.glob(f"after/{name}@{share}-*/*-look.png")}
        found[str(share)] = sweep_measure(place, name, looks)
    (out / "measures.json").write_text(json.dumps({"place": place, "shares": found}, indent=1) + "\n")
    for child in list(tree.iterdir()):
        shutil.rmtree(child)


def sweep_measure(place, name, looks):
    """One strength's measure on its views: the heads' median halo and fill, or the sky's median gap to the concept."""
    if place == "camp":
        concept = measure.concept_sky(measure.picture(CONCEPTS["campgrounds"]), CONCEPT_SKY_ROWS)
        views = [measure.sky(measure.picture(DEMO / f"frames/{name}/{view}-look.png"), measure.picture(path), concept)
                 for view, path in sorted(looks.items())]
        return {"gap": float(np.median([view["after"]["gap_to_concept"] for view in views if view["after"]])),
                "views": views}
    size, views = chosen_views(name, tuple(looks))
    heads, veils = [], []
    for view in views:
        rgb = measure.picture(looks[view["name"]])
        veils.append(measure.veil(measure.picture(DEMO / f"frames/{name}/{view['name']}-look.png"), rgb))
        for middle, half, _, _ in lamp_heads(place):
            x, y, depth, focal = measure.where(view, size, middle)
            if x is not None and 0 <= x < size[0] and 0 <= y < size[1]:
                found = measure.head(rgb, x, y, focal * half / depth)
                if found:
                    heads.append(found)
    return {"halo": float(np.median([head["halo"] for head in heads])) if heads else None,
            "fill": float(np.median([head["fill"] for head in heads])) if heads else None, "heads": len(heads),
            "veil": max(veils) if veils else None}


def judge_sweep(output, inputs, evidence):
    """Some strength of the sweep meets the light gate's rule for this place's fault."""
    shares = measures_of(output)["shares"]
    if all("gap" in found for found in shares.values()):
        meeting = [share for share, found in shares.items() if found["gap"] <= SKY_GAP_MOST]
    else:
        meeting = [share for share, found in shares.items()
                   if found["halo"] is not None and found["halo"] >= HALO_LEAST and found["fill"] >= FILL_LEAST
                   and found["veil"] <= VEIL_MOST]
    return verdict("sweep", bool(meeting), f"strengths meeting the rule: {meeting or 'none'} of {sorted(shares)}",
                   {"meeting": len(meeting)})


def sweep_faults(folder):
    return [] if (folder / "measures.json").exists() else ["no measures.json"]


SWEPT = contracts.Contract("light-sweep", 1, sweep_faults, {"length": "metre", "up axis": "Y"})
SWEEP_STAGE = graph.Stage("sweep", "place", make_sweep, SWEPT, (checks.Check("sweep", judge_sweep),),
                          files=PLACE_FILES, after={"lightkit": ("kit-models", 1)}, paid=True, euros=4.0)
STAGES = (KIT, SWEEP_STAGE, LIGHT)


def runner(store=None):
    """The runner over the light stages, on world 1 and the framework's store."""
    return graph.Runner(STAGES, world1(), store or Store.default())
