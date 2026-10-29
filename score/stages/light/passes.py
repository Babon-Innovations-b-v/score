"""The light stage's paid row, light-passes (its own module, so an edit of the sweep or the gates in __init__.py does
not buy the render again): the place's stage as the assembly lays it before its layers (the seed with its
accepted scene record) with its light layer, and the places it shows each with its own light layer written here,
rendered on its own scene record's views (the light layer's views.json, `record_views`) on rented L4 cards with every
lamp of the place in a Cycles light group of its own (inside/light_passes.py).

One shot (#21, #27): every view once, at CHECK_SIZE only, since the passes feed the sweep and the gates and nothing
ships from them (a film or still renders its own frames at their final size once); one card class, never a fallback
to a larger card; a job that fails is a gap, never rendered again inside the batch.
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
RECORD = "scene-record"  # the row writing a place's scene record: the node's own place's an after, a shown one's beside
# What the assembly lays over the record (source), read as it reads them: the surface line's bake and paint, the made
# ground; and the place's design surface data, which bakes of other places it lays (grounded.take_bakes).
LAID = {"terrain": ("grounds", 2), "surfaces-bake": ("surfaces-bake", 1), "surfaces-paint": ("surfaces-paint", 1)}
SURFACES = {"surfaces": "{home}/design/surfaces/{place}.json"}
# Four to eight views of one stage on one or two rented cards, each set up once (the camp's first: EUR 0.18).
EUROS = 2.0


# --- the render ---------------------------------------------------------------------------------------------------

def neighbours(place):
    """The other places the place's accepted scene record shows (its `places`: the place each of its plan's doors
    opens onto, and those its views see over the made ground's seats), each a place of the design: one whose kept
    plan says where its doors lead, so the scene-record row writes its lights too (scene_record.written's rule). The
    places rendered, each lit by its own record, through the doorways and past the edges. None before the place's
    scene record stands accepted (every light row reads it, so it is keyed again once it does); a shown place the
    design has no plan for (the far city) is left out of the render, and the neighbours row names it a gap."""
    from score.store import Store
    store = Store.default()
    output = store.accepted(f"{RECORD}@{place}")
    record = store.read_file(output, f"record/{place}.json") if output else None
    shown = {entry["stage"] for entry in (record or {}).get("places", [])} - {place}
    return sorted(name for name in shown if recorded(name))


KEPT = PROPS_HOME / "design"  # the design's plans and scene inventories (score/review/plans.py keep)


def plan_of(name):
    """A place's kept plan ({home}/design/plans/<name>.json: his edit, else the written plan), {} for a place with
    none."""
    path = KEPT / "plans" / f"{name}.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def recorded(place):
    """Whether the scene-record row writes the place's record (and so its lights and views): its kept plan says where
    its doors lead (scene_record.written's rule, read here so the paid rows never hash the writer's code)."""
    return place is not None and "leads" in plan_of(place)


def shown_in(inputs):
    """The places a node's inputs show: each other place whose scene record it reads beside (`scene-record@<name>`),
    as the runner gave them from neighbours."""
    return sorted(node.split("@", 1)[1] for node in inputs if node.startswith(f"{RECORD}@"))


def take(layer_folder, folder, place):
    """A light layer (layers/light.usda and assets/light/ of `layer_folder`) put into a place's stage folder, held by
    its root over the made ground and the base, under the motion, effects and edit layers (record.ORDER): how an
    assembly takes it. The root is written anew (never through a hard link to a seed's). Returns the root."""
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
    import score.stages.assembly.record as record  # this form: the code version hashes record.py alone
    record.hold(root, f"./{layer.LAYER}")  # in the assembly's ORDER: over the made ground, under the motion
    return root


def place_of(inputs):
    """The place a light node is made for: the one record its scene-record output holds. Refused by name for a place
    the scene-record row writes no record for (its filed plan says nowhere where its doors lead): its lights and
    views are that record's."""
    if RECORD not in inputs:
        raise RuntimeError(f"no scene record to light (the {RECORD} row does not apply here: no filed plan with leads, "
                           f"kit {pathlib.Path(inputs.get('kit', '?')).stem})")
    return next((pathlib.Path(inputs[RECORD]) / "record").glob("*.json")).stem


def record_of(place, inputs):
    """A place's scene record as the scene-record row wrote it from its plan, inventory and sky (what the assembly
    lays): the node's own place's from its after (`scene-record`), a shown place's read beside
    (`scene-record@<place>`)."""
    node = RECORD if place == place_of(inputs) else f"{RECORD}@{place}"
    return json.loads((pathlib.Path(inputs[node]) / "record" / f"{place}.json").read_text())


def source(place, inputs, folder):
    """The place's stage as the assembly lays it before its layers: the seed (hard links, but for its root, its base
    and its pictures, which the record's writer rewrites, written anew; its assets all written anew where a bake is
    laid over them) with the accepted scene record written over the seed's record prims (assembly/record.take_record),
    the surface line's bakes over its models and its waiting entries (assembly/grounded.take_bakes) and its made
    ground (record.take_ground): the assembly's own code, so the lamps are measured on what ships (2026-10-29:
    light-passes@base drew nothing, every object waiting on its bake). The seed alone for a place with no
    scene-record row."""
    import score.stages.assembly.grounded as grounded  # this form: the code version hashes grounded.py's imports
    import score.stages.assembly.record as record
    seed = pathlib.Path(inputs["seed"])
    subprocess.run(["cp", "-al", str(seed), str(folder)], check=True)
    for part in (f"{place}.usda", "layers/base.usda"):
        (folder / part).unlink()
        shutil.copyfile(seed / part, folder / part)
    fresh = "assets" if "surfaces-bake" in inputs else "assets/textures"  # a write through a link changes the seed
    if (seed / fresh).exists():
        shutil.rmtree(folder / fresh)
        shutil.copytree(seed / fresh, folder / fresh, copy_function=shutil.copyfile)
    (folder / "assets").mkdir(exist_ok=True)  # the bakes are written there; a seed laying no kit piece has none
    if "scene-record" in inputs:
        record.take_record(inputs, folder, place)
        grounded.take_bakes(inputs, folder, place)
    if "terrain" in inputs:
        record.take_ground(inputs["terrain"], place, folder / f"{place}.usda")
    return folder


def lit_tree(place, layer_folder, tree, inputs):
    """The place's stage as the assembly lays it (source) with its light layer, and each place it shows (its seed,
    shown_in) with the light layer its own scene record gives it (written here, as its own light-layer row would),
    hard links to the seeds but for what is written. Refused when the stage names a picture that is not there."""
    source(place, inputs, tree / place)
    root = take(layer_folder, tree / place, place)
    for name in shown_in(inputs):
        if (tree / name).exists():
            continue
        seed = pathlib.Path(inputs[f"neighbour {name}"])
        subprocess.run(["cp", "-al", str(seed), str(tree / name)], check=True)
        neighbour_layer(name, record_of(name, inputs), seed, tree)
    missing = unresolved(root)
    if missing:  # a missing picture renders as magenta on a paid card: refused before anything is rented
        raise RuntimeError(f"{len(missing)} pictures the lit stage names are missing, first: {missing[:5]}")
    return root


def neighbour_layer(name, record, seed, tree):
    """A shown place's light layer written in a folder of its own beside the tree, then taken into tree/<name>.
    Written straight into tree/<name> (until 2026-10-18), the writer moved every picture of that folder's
    assets/textures, the neighbour's own seed pictures among them, into assets/light: its materials lost their
    pictures and rendered Blender's missing-texture magenta through the doorways (PRD #10, the light step)."""
    written = tree.parent / f"light-of-{name}"
    shutil.rmtree(written, ignore_errors=True)
    try:
        layer.write(name, record, seed, written)
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
    subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/cloud/blender_cloud.py"), *paths, "--who", WHO,
                    "--classes", CARDS], check=True, cwd=REPO)
    for path in paths:
        pathlib.Path(path).unlink()


def make_passes(inputs, out, seed, params):
    """Render the place with its light layer on its views, every lamp in its own light group."""
    place = place_of(inputs)
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
    """The files a place's light layer is written from besides its scene record (a stored output): its kit."""
    return {f"kit {name}": f"{{data}}/kit/{name}.json"}


def passes_files(place):
    """What the render reads besides the layer (which holds its views) and the scene records: the seed, the places it
    shows (neighbours) with the files their light layers are written from (theirs alone, never a whole folder:
    another place's kit edited moves no render here), the scripts."""
    found = {"seed": "{seeds}/usd-r3/{place}", "kit": "{data}/kit/{place}.json", **SURFACES,
             "renderer": "{repo}/tools/blender/inside/usd_views.py", "passes script": "{repo}/" + SCRIPT}
    for name in neighbours(place):
        found[f"neighbour {name}"] = f"{{seeds}}/usd-r3/{name}"
        found.update(place_files(name))
    return found


def groups_of(passes_folder):
    """{group: lamp path}, the same in every job of the node."""
    found = {}
    for path in passes_folder.glob("passes/*/passes.json"):
        found.update(json.loads(path.read_text())["groups"])
    return found
