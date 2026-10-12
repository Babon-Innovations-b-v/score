"""The light stage's paid row, light-passes (its own module, so an edit of the sweep or the gates in __init__.py does
not buy the render again): the place's stage as the assembly lays it before its layers (the seed with its
accepted scene record) with its light layer, and the places it shows each with its own light layer written here, rendered on the demo's views on rented cards with every lamp of the place in a Cycles light group
of its own (inside/light_passes.py).
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
WORK = PROPS_HOME / "work"
SEEDS = WORK / "usd-r3"
DEMO = WORK / "demo/world1-r4"
CARDS = "gpu-24gb,gpu-48gb,gpu-80gb"
WHO = "score light stage"
SCRIPT = "score/stages/light/inside/light_passes.py"
FRAME = "-000"
VIEWS_A_JOB = 4
MINUTES_A_VIEW = 5
# Four to eight views of one stage on one or two rented cards, each set up once (the camp's first: EUR 0.18).
EUROS = 2.0
# The demo views a place's passes are rendered on, beside its own (the camp grounds' film is drawn on the camp's
# stage, which holds their sky).
ALSO_SHOWN = {"camp": ("campgrounds",)}


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
    the seed's record prims (assembly.take_record), or the seed alone for a place with no scene-record row."""
    seed = pathlib.Path(inputs["seed"])
    subprocess.run(["cp", "-al", str(seed), str(folder)], check=True)
    for part in (f"{place}.usda", "layers/base.usda"):
        (folder / part).unlink()
        shutil.copyfile(seed / part, folder / part)
    if (seed / "assets/textures").exists():
        shutil.rmtree(folder / "assets/textures")
        shutil.copytree(seed / "assets/textures", folder / "assets/textures", copy_function=shutil.copyfile)
    if "scene-record" in inputs:
        from score.stages import assembly
        assembly.take_record(inputs, folder, place)
    return folder


def lit_tree(place, layer_folder, tree, inputs):
    """The place's stage as the assembly lays it (source) with its light layer, and each place it shows (its seed)
    with the light layer its own record gives it (written here, as its own light-layer row would), hard links to the
    seeds but for what is written."""
    source(place, inputs, tree / place)
    root = take(layer_folder, tree / place, place)
    for name in neighbours(place):
        if (tree / name).exists():
            continue
        seed = pathlib.Path(inputs[f"neighbour {name}"])
        subprocess.run(["cp", "-al", str(seed), str(tree / name)], check=True)
        if (REPO / f"data/scene/{name}.json").exists():  # the far city is a stage with no scene record: no lights
            layer.write(name, scene_of(name), seed, tree / name)
            take(tree / name, tree / name, name)
    return root


def demo_views(name):
    """The demo's views of a place on frame 000 of each shot: (size, views)."""
    record = json.loads((DEMO / f"views/{name}.json").read_text())
    return record["size"], [dict(view, look_only=True) for view in record["views"] if view["name"].endswith(FRAME)]


def shown(place):
    return (place, *ALSO_SHOWN.get(place, ()))


def pass_jobs(root, tree, place, lamps, out):
    """blender_cloud jobs rendering every view the place's passes are taken on, VIEWS_A_JOB a job."""
    jobs = []
    for name in shown(place):
        size, views = demo_views(name)
        for start in range(0, len(views), VIEWS_A_JOB):
            part = views[start:start + VIEWS_A_JOB]
            target = out / "passes" / f"{name}-{start // VIEWS_A_JOB}"
            spec = out / "passes" / f"{name}-{start // VIEWS_A_JOB}.views.json"
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
    render(pass_jobs(root, tree, place, lamps, out), out)
    shutil.rmtree(tree)


def judge_rendered(output, inputs, evidence):
    """Every view the passes are taken on came back with its look and its passes: the whole picture and every lamp."""
    groups = groups_of(output)
    lamps = json.loads((pathlib.Path(inputs["light-layer"]) / "lamps.json").read_text())["lamps"]
    lacking = [f"lamp {lamp['path']} has no light group" for lamp in lamps if lamp["path"] not in groups.values()]
    views = 0
    for name in shown(json.loads((pathlib.Path(inputs["light-layer"]) / "lamps.json").read_text())["place"]):
        for view in demo_views(name)[1]:
            views += 1
            found = list(output.glob(f"passes/{name}-*/{view['name']}-passes.npz"))
            if not found or not found[0].with_name(f"{view['name']}-look.png").exists():
                lacking.append(f"{name} {view['name']}: not rendered")
                continue
            held = set(np.load(found[0]).files)
            lacking += [f"{name} {view['name']}: no {group}" for group in ("combined", *groups) if group not in held]
    return checks.Verdict("rendered", checks.FAIL if lacking else checks.PASS,
                          f"{views} views, {len(groups)} lamps each: {len(lacking)} missing", {"missing": len(lacking)},
                          {"missing": "lower"}, tuple(lacking))


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
    """What the render reads besides the layer: the seed, the places it shows with the files their light layers are
    written from (theirs alone, never a whole folder: another place's record or kit edited moves no render here), the
    planned grounds, the demo's views, the scripts."""
    found = {"scene": "{data}/scene/{place}.json", "seed": "{seeds}/usd-r3/{place}", "grounds": "{data}/ground",
             "kit": "{data}/kit/{place}.json", "renderer": "{repo}/tools/blender/inside/usd_views.py", "passes script": "{repo}/" + SCRIPT}
    found.update({f"views {name}": f"{{seeds}}/demo/world1-r4/views/{name}.json" for name in shown(place)})
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
