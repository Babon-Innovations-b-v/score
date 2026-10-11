"""The terrain look (experimental, PRD #6, until the owner reviews it): a place's stage before its made ground (the
round-three seed) and after it (the assembly stage's output, which takes the made ground), rendered on rented cards
from the place's own review cameras (the round-three demo's views, frame 000 of each shot), and measured.

    make     both stages in a tree of their own with the neighbours their records reference (hard links to the seeds),
             each view rendered by tools/blender/inside/usd_views.py through tools/props/cloud/blender_cloud.py inside
             the runner's clearance: its look and its mask (the place's objects and ground alone, alpha where they
             are); measures.json per view
    gates    horizon   no view of the place with the made ground looks out below the horizon onto nothing: the
                       share of the mask's rows under the horizon (less a margin for the dip and the far ground's
                       curve) where nothing is drawn stays under HOLE_MOST

Only the places in LOOKED have the row: the proof place, until the owner has seen it.
"""
import json
import math
import pathlib
import shutil
import subprocess

import numpy as np
from PIL import Image

from score import checks, contracts
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[3]
PROPS_PYTHON = PROPS_HOME / "env/bin/python"
LOOKED = ("launch",)
VIEWS = "demo/world1-r4/views"
FRAME = "-000"
VIEWS_A_JOB = 2
MINUTES_A_VIEW = 8
CARDS = "gpu-24gb,gpu-48gb,gpu-80gb"
WHO = "score terrain look"
# Four views, each drawn twice (before and after), its look and two masks, on two to four rented cards.
EUROS = 4.0
# Rows this share of the picture's height under the horizon are left out: the dip of the horizon from the eye and the
# far ground's curve at its 30 km edge lie within a few pixels of the level line.
MARGIN = 0.01
# The share of the rows under the horizon that may show nothing (a pixel or two of a seam).
HOLE_MOST = 0.001
STATES = ("before", "after")


def neighbours(place):
    """The other places a place's stage references (its scene record's `places`), by their stage's name."""
    record = json.loads((REPO / f"data/scene/{place}.json").read_text())
    return sorted({entry["stage"] for entry in record.get("places", [])})


def files(place):
    """What the look reads besides the assembly's output: its views, its seed, its neighbours' seeds, the renderer."""
    found = {"views": f"{{seeds}}/{VIEWS}/{place}.json", "scene": "{data}/scene/{place}.json",
             "seed": "{seeds}/usd-r3/{place}", "renderer": "{data}/../tools/blender/inside"}
    found.update({f"neighbour {name}": f"{{seeds}}/usd-r3/{name}" for name in neighbours(place)})
    return found


def tree(out, state, place, stage_folder, inputs):
    """A folder holding the place's stage (`stage_folder`, copied) and its neighbours (hard links to the seeds)."""
    folder = out / "stages" / state
    folder.mkdir(parents=True)
    shutil.copytree(stage_folder, folder / place)
    subprocess.run(["chmod", "-R", "u+w", str(folder / place)], check=True)
    for name in neighbours(place):
        subprocess.run(["cp", "-al", str(inputs[f"neighbour {name}"]), str(folder / name)], check=True)
    return folder


def view_jobs(folder, place, views, size, out):
    """blender_cloud jobs rendering `views` of the tree's place stage, VIEWS_A_JOB a job, each into out/<n>."""
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for start in range(0, len(views), VIEWS_A_JOB):
        part = views[start:start + VIEWS_A_JOB]
        spec = out / f"{start // VIEWS_A_JOB}.views.json"
        # The demo's views are walk frames (look only); the measure needs each view's mask too.
        spec.write_text(json.dumps({"size": size, "views": [dict(view, look_only=False) for view in part]}))
        target = out / str(start // VIEWS_A_JOB)
        jobs.append({"script": "tools/blender/inside/usd_views.py",
                     "args": [str(folder / place / f"{place}.usda"), str(spec), str(target)],
                     "inputs": [*(str(child) for child in folder.iterdir()), str(spec)], "outputs": [str(target)],
                     "minutes": MINUTES_A_VIEW * len(part)})
    return jobs


def render(jobs, folder):
    """Run the jobs on rented cards (the runner's clearance names them), spread over as many machines as suit."""
    paths = []
    for number, job in enumerate(jobs):
        path = folder / f"job-{number}.json"
        path.write_text(json.dumps(job, indent=1))
        paths.append(str(path))
    subprocess.run([str(PROPS_PYTHON), str(REPO / "tools/props/cloud/blender_cloud.py"), *paths, "--who", WHO,
                    "--classes", CARDS], check=True, cwd=REPO)


def horizon_row(view, size):
    """The picture row of the level line through the eye (from the top), the view's fov being the angle across."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    way = aim - eye
    pitch = math.atan2(way[1], math.hypot(way[0], way[2]))
    half_tall = math.tan(math.radians(view["fov"]) / 2) * size[1] / size[0]
    return size[1] / 2 * (1 + math.tan(pitch) / half_tall)


def holes_under_horizon(mask, view, size):
    """The share of the pixels under the horizon (less MARGIN) where the mask has nothing drawn."""
    alpha = np.asarray(Image.open(mask).convert("RGBA"))[:, :, 3]
    first = int(math.ceil(horizon_row(view, size) + MARGIN * size[1]))
    under = alpha[max(first, 0):]
    return float((under < 128).mean()) if under.size else 0.0


def looks_changed(before, after):
    """The share of pixels whose look moved by more than a tenth of white between before and after."""
    first, second = (np.asarray(Image.open(path).convert("RGB"), dtype=float) / 255 for path in (before, after))
    return float((np.abs(first - second).max(axis=2) > 0.1).mean())


def rendered(out, state, name, kind):
    """A view's rendered picture of one kind (look, mask) in one state, or None."""
    return next(iter(sorted(out.glob(f"{state}/*/{name}-{kind}.png"))), None)


def measured(out, views, size):
    """{view: {before: holes, after: holes, changed}} on the rendered pictures."""
    found = {}
    for view in views:
        name = view["name"]
        entry = {state: round(holes_under_horizon(rendered(out, state, name, "mask"), view, size), 5)
                 for state in STATES}
        entry["changed"] = round(looks_changed(rendered(out, "before", name, "look"),
                                               rendered(out, "after", name, "look")), 4)
        entry["horizon_row"] = round(horizon_row(view, size), 1)
        found[name] = entry
    return found


def make(inputs, out, seed, params):
    """Render the place before and after its made ground on its review cameras, and measure both."""
    place = pathlib.Path(inputs["seed"]).name
    record = json.loads(pathlib.Path(inputs["views"]).read_text())
    views = [view for view in record["views"] if view["name"].endswith(FRAME)]
    jobs = []
    for state, stage_folder in (("before", inputs["seed"]), ("after", inputs["assembly"])):
        jobs += view_jobs(tree(out, state, place, stage_folder, inputs), place, views, record["size"], out / state)
    render(jobs, out)
    shutil.rmtree(out / "stages")
    for leftover in [*out.glob("*/*/*-ground.png"), *out.glob("job-*.json")]:
        leftover.unlink()
    (out / "measures.json").write_text(json.dumps({"place": place, "size": record["size"],
                                                   "views": measured(out, views, record["size"])}, indent=1))


def judge_horizon(output, inputs, evidence):
    """Pass when no view of the place on its made ground looks out below the horizon onto nothing."""
    views = json.loads((output / "measures.json").read_text())["views"]
    open_views = [f"{name}: {found['after']:.4f} of the ground under the horizon shows nothing (before "
                  f"{found['before']:.4f})" for name, found in views.items() if found["after"] > HOLE_MOST]
    worst = max(found["after"] for found in views.values())
    return checks.Verdict("horizon", checks.FAIL if open_views else checks.PASS,
                          f"{len(open_views)} of {len(views)} views look out onto nothing under the horizon",
                          {"worst after": worst, "worst before": max(found["before"] for found in views.values())},
                          {"worst after": "lower"}, tuple(open_views))


def look_faults(folder):
    """Every measured view has its look and mask before and after."""
    folder = pathlib.Path(folder)
    if not (folder / "measures.json").exists():
        return ["no measures.json"]
    views = json.loads((folder / "measures.json").read_text())["views"]
    return [f"{name} lacks its {state} {kind}" for name in views for state in STATES for kind in ("look", "mask")
            if rendered(folder, state, name, kind) is None] or ([] if views else ["no view measured"])


LOOK = contracts.Contract("terrain-look", 1, look_faults, {"length": "metre", "up axis": "Y"})
CHECKS = (checks.Check("horizon", judge_horizon),)
