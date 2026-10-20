"""The light stage's paid row, light-passes (its own module, so an edit of the sweep or the gates in __init__.py does
not buy the render again): the place's stage as the assembly lays it before its layers (the seed with its
accepted scene record) with its light layer, and the places it shows each with its own light layer written here,
rendered on its own scene record's views (the light layer's views.json, `record_views`) on rented L4 cards with every
lamp of the place in a Cycles light group of its own (inside/light_passes.py).

One shot (#21, #27): every view once, at CHECK_SIZE only, since the passes feed the sweep and the gates and nothing
ships from them (a film or still renders its own frames at their final size once); one card class, never a fallback
to a larger card; a job that fails is a hole, never rendered again inside the batch.
"""
import json
import pathlib
import shutil
import subprocess

import numpy as np

from score import checks, contracts
import score.stages.light.layer as layer  # this form, not `from ... import`: the code version then leaves __init__ out
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
# One class, the card Blender's jobs were timed on (paper/evidence/cloud/capacity-2026-10.txt: L4, 116 s a job).
CARDS = "gpu-24gb"
WHO = "score light stage"
SCRIPT = "score/stages/light/inside/light_passes.py"
VIEWS_A_JOB = 4
MINUTES_A_VIEW = 5
# The size the passes are rendered at: the sweep and the gates read them, nothing ships from them.
CHECK_SIZE = [960, 540]
VIEWS = "views.json"  # in the light layer's output: the views the place's light is rendered and judged on
# Four to eight views of one stage on one or two rented cards, each set up once (the camp's first: EUR 0.18).
EUROS = 2.0


def scene_of(place):
    return json.loads((REPO / f"data/scene/{place}.json").read_text())


# --- the render ---------------------------------------------------------------------------------------------------

def neighbours(place):
    return sorted({entry["stage"] for entry in scene_of(place).get("places", [])} - {place})


def take(layer_folder, folder, place):
    """A light layer (layers/light.usda and assets/light/ of `layer_folder`) put into a place's stage folder, held by
    its root just over the base, under the motion, effects and edit layers: how an assembly takes it. The root is
    written anew (never through a hard link to a seed's). Returns the root."""
    from pxr import Sdf
    root = folder / f"{place}.usda"
    text = root.read_text()
    root.unlink()
    root.write_text(text)
    if layer_folder != folder:
        (folder / layer.LAYER).unlink(missing_ok=True)
        shutil.copyfile(layer_folder / layer.LAYER, folder / layer.LAYER)
        if (layer_folder / layer.ASSETS).exists():
            shutil.copytree(layer_folder / layer.ASSETS, folder / layer.ASSETS, copy_function=shutil.copyfile,
                            dirs_exist_ok=True)
    held = Sdf.Layer.FindOrOpen(str(root))
    paths = list(held.subLayerPaths)
    if f"./{layer.LAYER}" not in paths:
        paths.insert(paths.index("./layers/base.usda"), f"./{layer.LAYER}")
        held.subLayerPaths = paths
        held.Save()
    return root


def record_of(place, inputs):
    """The place's scene record: its accepted scene-record output's where it has one (what the assembly lays), else
    data/scene's."""
    if "scene-record" in inputs:
        return json.loads((pathlib.Path(inputs["scene-record"]) / "record" / f"{place}.json").read_text())
    return scene_of(place)


def source(place, inputs, folder):
    """The place's stage as the assembly lays it before its layers: the seed (hard links, but for its root, its base
    and its pictures, which the record's writer rewrites, written anew) with the accepted scene record written over
    the seed's record prims (assembly/record.take_record), or the seed alone for a place with no scene-record row."""
    seed = pathlib.Path(inputs["seed"])
    subprocess.run(["cp", "-al", str(seed), str(folder)], check=True)
    for part in (f"{place}.usda", "layers/base.usda"):
        (folder / part).unlink()
        shutil.copyfile(seed / part, folder / part)
    if (seed / "assets/textures").exists():
        shutil.rmtree(folder / "assets/textures")
        shutil.copytree(seed / "assets/textures", folder / "assets/textures", copy_function=shutil.copyfile)
    if "scene-record" in inputs:
        import score.stages.assembly.record as record  # this form: the code version hashes record.py alone
        record.take_record(inputs, folder, place)
    return folder


def lit_tree(place, layer_folder, tree, inputs):
    """The place's stage as the assembly lays it (source) with its light layer, and each place it shows (its seed)
    with the light layer its own record gives it (written here, as its own light-layer row would), hard links to the
    seeds but for what is written. Refused when the stage names a picture that is not there."""
    source(place, inputs, tree / place)
    root = take(layer_folder, tree / place, place)
    for name in neighbours(place):
        if (tree / name).exists():
            continue
        seed = pathlib.Path(inputs[f"neighbour {name}"])
        subprocess.run(["cp", "-al", str(seed), str(tree / name)], check=True)
        if (REPO / f"data/scene/{name}.json").exists():  # the far city is a stage with no scene record: no lights
            neighbour_layer(name, seed, tree)
    missing = unresolved(root)
    if missing:  # a missing picture renders as magenta on a paid card: refused before anything is rented
        raise RuntimeError(f"{len(missing)} pictures the lit stage names are missing, first: {missing[:5]}")
    return root


def neighbour_layer(name, seed, tree):
    """A shown place's light layer written in a folder of its own beside the tree, then taken into tree/<name>.
    Written straight into tree/<name> (until 2026-10-18), the writer moved every picture of that folder's
    assets/textures, the neighbour's own seed pictures among them, into assets/light: its materials lost their
    pictures and rendered Blender's missing-texture magenta through the doorways (PRD #10, the light step)."""
    written = tree.parent / f"light-of-{name}"
    shutil.rmtree(written, ignore_errors=True)
    try:
        layer.write(name, scene_of(name), seed, written)
        take(written, tree / name, name)
    finally:
        shutil.rmtree(written, ignore_errors=True)


def unresolved(root):
    """Every picture or other non-layer file the stage at `root` names that is not on disk. A missing layer is left
    out: a shown place's own neighbours are referenced under its Places, deactivated, and are not in the tree."""
    from pxr import Sdf, UsdUtils
    missing = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(str(root)))[2]
    return sorted(path for path in missing if pathlib.Path(path).suffix not in LAYER_SUFFIXES)


LAYER_SUFFIXES = (".usd", ".usda", ".usdc", ".usdz")


def record_views(record):
    """The views a place's light is rendered and judged on, from its scene record (its `views`: eye, aim, fov), at
    CHECK_SIZE, as usd_views.py reads them: {"size", "views"}."""
    return {"size": CHECK_SIZE, "views": [{"name": view["name"], "eye": view["eye"], "aim": view["aim"],
                                           "up": view.get("up", [0.0, 1.0, 0.0]), "fov": view["fov"], "frame": 0,
                                           "look_only": True} for view in record.get("views", [])]}


def views_of(folder):
    """The views a light layer's output (or a light output, which copies them) holds: (size, views)."""
    record = json.loads((pathlib.Path(folder) / VIEWS).read_text())
    return record["size"], record["views"]


def pass_jobs(root, tree, place, lamps, out, layer_folder):
    """blender_cloud jobs rendering every view of the place's light layer, VIEWS_A_JOB a job."""
    jobs = []
    size, views = views_of(layer_folder)
    for start in range(0, len(views), VIEWS_A_JOB):
        part = views[start:start + VIEWS_A_JOB]
        target = out / "passes" / f"{place}-{start // VIEWS_A_JOB}"
        spec = out / "passes" / f"{place}-{start // VIEWS_A_JOB}.views.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"size": size, "views": part, "lamps": lamps}))
        jobs.append({"script": SCRIPT, "args": [str(root), str(spec), str(target)],
                     "inputs": [*(str(child) for child in tree.iterdir()), str(spec)], "outputs": [str(target)],
                     "minutes": MINUTES_A_VIEW * len(part)})
    return jobs


def render(jobs, folder):
    """Run the jobs on rented cards (the runner's clearance names them), spread over as many as finish them soonest."""
    paths = []
    for number, job in enumerate(jobs):
        path = folder / f"job-{number}.json"
        path.write_text(json.dumps(job, indent=1))
        paths.append(str(path))
    subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/blender_cloud.py"), *paths, "--who", WHO,
                    "--classes", CARDS], check=True, cwd=REPO)
    for path in paths:
        pathlib.Path(path).unlink()


def make_passes(inputs, out, seed, params):
    """Render the place with its light layer on its views, every lamp in its own light group."""
    place = json.loads(pathlib.Path(inputs["scene"]).read_text())["place"]
    layer_folder = pathlib.Path(inputs["light-layer"])
    lamps = [lamp["path"] for lamp in json.loads((layer_folder / "lamps.json").read_text())["lamps"]]
    tree = out / "stages"
    tree.mkdir(parents=True)
    root = lit_tree(place, layer_folder, tree, inputs)
    render(pass_jobs(root, tree, place, lamps, out, layer_folder), out)
    shutil.rmtree(tree)


def judge_rendered(output, inputs, evidence):
    """Every view the passes are taken on came back with its look and its passes: the whole picture and every lamp."""
    groups = groups_of(output)
    layer_folder = pathlib.Path(inputs["light-layer"])
    lamps = json.loads((layer_folder / "lamps.json").read_text())["lamps"]
    lacking = [f"lamp {lamp['path']} has no light group" for lamp in lamps if lamp["path"] not in groups.values()]
    views = 0
    for view in views_of(layer_folder)[1]:
        views += 1
        found = list(output.glob(f"passes/*/{view['name']}-passes.npz"))
        if not found or not found[0].with_name(f"{view['name']}-look.png").exists():
            lacking.append(f"{view['name']}: not rendered")
            continue
        held = set(np.load(found[0]).files)
        lacking += [f"{view['name']}: no {group}" for group in ("combined", *groups) if group not in held]
    return checks.Verdict("rendered", checks.FAIL if lacking else checks.PASS,
                          f"{views} views, {len(groups)} lamps each: {len(lacking)} missing", {"missing": len(lacking)},
                          {"missing": "lower"}, tuple(lacking))


# Blender draws a material whose picture is missing in magenta (1, 0, 1); through the view's tone curve it reads as a
# saturated pink-purple. Set 2026-10-18 on the 85 accepted light looks of every place: each look holding 0.27% or
# more of such pixels showed a neighbour that had lost its pictures, seen by eye (ten places, up to 34%); of the
# rest, three held under 0.1% and all others none.
MAGENTA_HUE = (285.0, 340.0)
MAGENTA_SATURATION = 0.3
MAGENTA_VALUE = 0.15
MAGENTA_MOST = 0.002


def magenta_share(picture):
    """The share of a look's pixels in the missing-texture magenta's hue, saturated and lit."""
    from PIL import Image
    pixels = np.asarray(Image.open(picture).convert("HSV")).astype(float) / 255
    hue = pixels[..., 0] * 360
    return float(((hue > MAGENTA_HUE[0]) & (hue < MAGENTA_HUE[1]) & (pixels[..., 1] > MAGENTA_SATURATION)
                  & (pixels[..., 2] > MAGENTA_VALUE)).mean())


def judge_magenta(output, inputs, evidence):
    """No look holds more than MAGENTA_MOST of Blender's missing-texture magenta."""
    looks = sorted(output.glob("passes/*/*-look.png"))
    shares = {f"{look.parent.name}/{look.name}": magenta_share(look) for look in looks}
    over = [f"{name}: {share:.1%} missing-texture magenta" for name, share in shares.items() if share > MAGENTA_MOST]
    most = max(shares.values(), default=0.0)
    if not looks:
        return checks.Verdict("no missing pictures", checks.UNKNOWN, "no look rendered", {}, {}, ())
    return checks.Verdict("no missing pictures", checks.FAIL if over else checks.PASS,
                          f"{len(looks)} looks, the most magenta {most:.1%} (at most {MAGENTA_MOST:.0%})",
                          {"magenta share": round(most, 4)}, {"magenta share": "lower"}, tuple(over))


def passes_faults(folder):
    found = [] if any(folder.glob("passes/*/*-passes.npz")) else ["no passes rendered"]
    return found + ([] if any(folder.glob("passes/*/*-look.png")) else ["no look rendered"])


PASSES = contracts.Contract("light-passes", 1, passes_faults, {"length": "metre", "up axis": "Y"})


def place_files(name):
    """The files a place's light layer is written from: its scene record, its kit, its light data when it has one."""
    found = {f"scene {name}": f"{{data}}/scene/{name}.json", f"kit {name}": f"{{data}}/kit/{name}.json"}
    if (REPO / f"data/light/{name}.json").exists():  # its kit moves read the site's numbers through the layout
        found[f"light data {name}"] = f"{{data}}/light/{name}.json"
        found["site numbers"] = "{data}/definitions/earth_site.json"
    return found


def passes_files(place):
    """What the render reads besides the layer (which holds its views): the seed, the places it shows with the files
    their light layers are written from (theirs alone, never a whole folder: another place's record or kit edited
    moves no render here), the planned grounds, the scripts."""
    found = {"scene": "{data}/scene/{place}.json", "seed": "{seeds}/usd-r3/{place}", "grounds": "{data}/ground",
             "kit": "{data}/kit/{place}.json", "renderer": "{repo}/tools/blender/inside/usd_views.py",
             "passes script": "{repo}/" + SCRIPT}
    for name in neighbours(place):
        found[f"neighbour {name}"] = f"{{seeds}}/usd-r3/{name}"
        if (REPO / f"data/scene/{name}.json").exists():
            found.update(place_files(name))
    return found


def groups_of(passes_folder):
    """{group: lamp path}, the same in every job of the node."""
    found = {}
    for path in passes_folder.glob("passes/*/passes.json"):
        found.update(json.loads(path.read_text())["groups"])
    return found
