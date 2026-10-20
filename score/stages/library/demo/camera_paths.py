"""Camera paths: the greenhouse's own 3D stage (its base layer and every model it references, from the library) cut
at waist height for the plan, two of its scene record's camera spots, RRT*'s path between them
(`tools/usd/camera_paths.rrt_star`), the path cut short (`shortcut`) and flown as the walk's camera (`walk_views`);
the slider runs the same search with other seeds."""
import json
import pathlib
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from score.stages.library.demos import NoExample

ALGORITHM = "camera_paths"
PLACE = "greenhouse"
START, GOAL = "east-door-in", "south-west-corner"  # two of the scene record's camera spots, across the beds
SEEDS = (0, 1, 2, 3, 4)
WAIST = 1.0  # metres: the height the plan is cut at
FRAMES = 40  # the flown camera's views
MODEL = re.compile(r"@score_lib/model/([^/]+)/(\d+)/(model\.usdc)@")


def camera_code(repo):
    """tools/usd/camera_paths, imported from the repository's tools folder."""
    sys.path.insert(0, str(repo / "tools/usd"))
    import camera_paths
    return camera_paths


def fetched_stage(inputs, place, over=(), places_off=True):
    """The place's base layer and every model it references in the library cache, and a stage over them in a folder
    of its own (`over`: library layers, as score_lib/... paths, laid over the base; `places_off`: its neighbouring
    places left out); the stage's path."""
    layer = inputs.library(f"layer/base.{place}@1", "layer.usda")
    models = sorted(set(MODEL.findall(layer.read_text())))
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda model: inputs.library(f"model/{model[0]}@{model[1]}", model[2]), models))
    folder = layer.parents[4] / "demo-stages" / place  # beside the library cache, made again each run
    folder.mkdir(parents=True, exist_ok=True)
    if not (folder / "score_lib").is_symlink():
        (folder / "score_lib").symlink_to(layer.parents[3])
    sublayers = ", ".join(f"@{path}@" for path in (*over, f"score_lib/layer/base.{place}/1/layer.usda"))
    places = f'\nover "{place}"\n{{\n    over "Places" (active = false)\n    {{\n    }}\n}}\n' if places_off else ""
    stage = folder / "stage.usda"
    stage.write_text(f'#usda 1.0\n(\n    defaultPrim = "{place}"\n    subLayers = [{sublayers}]\n)\n{places}')
    return stage


def plan_point(point):
    return [round(float(point[0]), 2), round(float(-point[2]), 2)]


def waist_lines(still):
    """The place's meshes cut at waist height: one line shape an outline, centimetre points."""
    cut = still.section(plane_origin=[0.0, WAIST, 0.0], plane_normal=[0.0, 1.0, 0.0])
    lines = []
    for outline in cut.discrete if cut is not None else []:
        points = [plan_point(point) for point in outline]
        kept = [point for rank, point in enumerate(points) if rank == 0 or point != points[rank - 1]]
        if len(kept) > 1:
            lines.append({"kind": "line", "points": kept, "tone": "base"})
    return lines


def walked(camera, scenes, eyes, seed):
    """(RRT*'s path, the path cut short, its flown views) from the start eye to the goal with one seed."""
    found = camera.rrt_star(scenes, eyes[0], eyes[1], scenes["extent"], seed)
    if found is None:
        return None
    short = camera.shortcut(scenes, found, camera.CLEARANCE)
    return found, short, camera.walk_views(short, FRAMES, False)


def path_shapes(walk):
    """RRT*'s path as a ghost line and the cut path as the flown camera."""
    found, short, views = walk
    return [{"kind": "line", "points": [plan_point(point) for point in found], "tone": "ghost",
             "label": "the tree's shortest path"},
            {"kind": "path", "points": [plan_point(view["eye"]) for view in views], "tone": "accent",
             "label": "the camera's walk",
             "look": [[round(view["aim"][0] - view["eye"][0], 2), round(view["eye"][2] - view["aim"][2], 2)]
                      for view in views]}]


def made(inputs):
    camera = camera_code(inputs.repo)
    scenes = camera.place_scenes(fetched_stage(inputs, PLACE))
    views = {view["name"]: view for view in json.loads((inputs.repo / "data/scene" / f"{PLACE}.json").read_text())
             ["views"]}
    spots = [[views[name]["eye"][0], views[name]["eye"][2]] for name in (START, GOAL)]
    eyes = camera.eyes_over(scenes, spots, camera.EYE_HEIGHT)
    walks = [walked(camera, scenes, eyes, seed) for seed in SEEDS]
    if walks[0] is None:
        raise NoExample("RRT* found no path between the two camera spots with seed 0")
    low_x, low_z, high_x, high_z = scenes["extent"]
    ends = [{"kind": "dots", "points": [plan_point(eye)], "r": 0.4, "tone": tone, "label": label}
            for eye, tone, label in ((eyes[0], "c1", "start: the east door"), (eyes[1], "c2", "goal: the south-west corner"))]
    kept = [walk for walk in walks if walk is not None]
    return {
        "example": f"the {PLACE}, from its east door to its south-west corner",
        "view": "plan", "bounds": [round(low_x - 0.5, 2), round(-high_z - 0.5, 2), round(high_x + 0.5, 2),
                                   round(-low_z + 0.5, 2)],
        "steps": [
            {"label": "The place cut at waist height, from its own 3D stage", "shapes": waist_lines(scenes["still"])},
            {"label": "Where the camera starts and where it must go", "shapes": ends},
            {"label": "A tree of walkable points grows; the shortest way through it is kept",
             "shapes": path_shapes(walks[0])[:1]},
            {"label": "Corners a straight walkable line can skip are cut, and the camera walks it",
             "shapes": path_shapes(walks[0])}],
        "slider": {"label": "seed", "unit": "", "values": [seed for seed, walk in zip(SEEDS, walks) if walk],
                   "at": 0, "shapes": [path_shapes(walk) for walk in kept]},
        "numbers": [{"label": "corners", "value": len(walks[0][1]), "unit": "",
                     "tip": "points of the path after it is cut short"},
                    {"label": "length", "value": round(float(sum(np.linalg.norm(np.diff(np.array(walks[0][1]),
                                                                                       axis=0), axis=1))), 1),
                     "unit": "m", "tip": "how far the camera walks"}]}

