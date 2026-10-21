"""The effects look (experimental, PRD #6, until the owner reviews it): a place's stage without its effects layer
(before) and with it (after, the assembly stage's output), rendered on rented cards from the place's own review
cameras (the round-three demo's shots, frame 000 of each: its eye and aim) at a few moments of its event, and
measured. Stills, not films: films wait for the owner's go.

    make     both states in a tree of their own (the after state's root with the effects layer taken out is the
             before), each camera rendered at each of MOMENTS (seconds from the rocket's lift-off) by
             tools/blender/inside/usd_views.py through tools/props/cloud/blender_cloud.py inside the runner's
             clearance; measures.json per view
    gates    shown     every view at or after the engines light changes where the effects are: at least SHOWN_LEAST
                       of its pixels differ between before and after
             lit       up to two seconds after lift-off, the pad round the rocket's foot (a window round its spot in
                       the picture, where the camera sees it) is at least LIT_OVER times as bright after as before

Only the places in LOOKED have the row: none since 2026-10-21. Its proof place was the launch, whose rocket, motion and
effects records were the old concepts' (data/scene, data/motion, data/effects, retired: owner, 2026-10-21, all old
stuff is retired), and the launch is now part of the square's outside, no place of the build. The look is made again
only over a design's own effects record (the effects-layer row's record.json), which names no rocket yet.
"""
import json
import math
import pathlib
import shutil

import numpy as np
from PIL import Image

from score import checks, contracts, graph
from score.stages.terrain import look as terrain_look

LOOKED = ()
VIEWS = terrain_look.VIEWS
FRAME = terrain_look.FRAME
# Seconds from lift-off: the engines lit on the pad, just off the pad, climbing clear, the cloud left behind.
MOMENTS = (-1.0, 1.5, 5.0, 12.0)
VIEWS_A_JOB = 4
MINUTES_A_VIEW = 6
# Four cameras at four moments, drawn twice, look only, on two to four rented cards.
EUROS = 6.0
STATES = ("before", "after")
EFFECTS_LAYER = "./layers/effects.usda"
# A tenth of white: a pixel that moved more than this changed.
CHANGED = 0.1
SHOWN_LEAST = 0.002
LIT_OVER = 1.5
LIT_UNTIL = 2.0
# The pad window round the foot's spot in the picture, as a share of the picture's width either side.
WINDOW = 0.03


def files(place):
    """What the look reads besides the assembly's output: its views, its neighbours' seeds, the renderer."""
    found = {"views": f"{{seeds}}/{VIEWS}/{place}.json", "renderer": "{data}/../tools/blender/inside"}
    found.update({f"neighbour {name}": f"{{seeds}}/usd-r3/{name}" for name in terrain_look.neighbours(place)})
    return found


def rocket(inputs):
    """The record's rocket: its height, its rest spot and its motion. None is read: they were the old launch's
    records, retired (module docstring), and a design's effects record names no rocket yet."""
    raise graph.Blocked("the effects look's rocket came from the old launch's records (data/scene, data/motion, "
                        "data/effects), retired 2026-10-21: no look until it reads a design's effects record")


def lift_second(motion):
    return float(motion["start"]) + float(motion["climb"]["lift"])


def moment_views(record, motion):
    """Each review camera (frame 000 of each shot) at each moment: name, eye, aim, fov, frame (time code)."""
    cameras = [view for view in record["views"] if view["name"].endswith(FRAME)]
    views = []
    for camera in cameras:
        for moment in MOMENTS:
            seconds = lift_second(motion) + moment
            views.append(dict(camera, name=f"{camera['name'].removesuffix(FRAME)}-t{seconds:05.1f}",
                              frame=int(round(seconds * 24)), look_only=True, review=True, seconds=seconds))
    return views


def without_effects(folder, place):
    """The before state: the root no longer holds the effects layer."""
    from pxr import Sdf
    layer = Sdf.Layer.FindOrOpen(str(folder / place / f"{place}.usda"))
    layer.subLayerPaths = [path for path in layer.subLayerPaths if path != EFFECTS_LAYER]
    layer.Save()
    shutil.rmtree(folder / place / "assets/effects", ignore_errors=True)


def view_jobs(folder, place, views, size, out):
    """blender_cloud jobs rendering `views` of the tree's place stage, VIEWS_A_JOB a job, each into out/<n>."""
    out.mkdir(parents=True, exist_ok=True)
    jobs = []
    for start in range(0, len(views), VIEWS_A_JOB):
        part = views[start:start + VIEWS_A_JOB]
        spec = out / f"{start // VIEWS_A_JOB}.views.json"
        spec.write_text(json.dumps({"size": size, "review": True, "views": part}))
        target = out / str(start // VIEWS_A_JOB)
        jobs.append({"script": "tools/blender/inside/usd_views.py",
                     "args": [str(folder / place / f"{place}.usda"), str(spec), str(target)],
                     "inputs": [*(str(child) for child in folder.iterdir()), str(spec)], "outputs": [str(target)],
                     "minutes": MINUTES_A_VIEW * len(part)})
    return jobs


def projected(view, point, size):
    """Where a point of the stage falls in the view's picture (x, y from the top left, pixels), or None behind it."""
    eye, aim = np.asarray(view["eye"], dtype=float), np.asarray(view["aim"], dtype=float)
    ahead = (aim - eye) / np.linalg.norm(aim - eye)
    right = np.cross(ahead, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, ahead)
    way = np.asarray(point, dtype=float) - eye
    depth = float(way @ ahead)
    if depth <= 0:
        return None
    half_wide = math.tan(math.radians(view["fov"]) / 2)
    across = float(way @ right) / depth / half_wide
    rise = float(way @ up) / depth / half_wide
    return size[0] / 2 * (1 + across), size[1] / 2 - rise * size[0] / 2


def brightness(path):
    pixels = np.asarray(Image.open(path).convert("RGB"), dtype=float) / 255
    return pixels @ np.array([0.2126, 0.7152, 0.0722])


def pad_window(view, foot, size):
    """The picture's window round the pad at the rocket's foot (rows, columns), or None when it is out of sight."""
    spot = projected(view, foot, size)
    if spot is None or not (0 <= spot[0] < size[0] and 0 <= spot[1] < size[1]):
        return None
    half = max(int(WINDOW * size[0]), 2)
    column, row = int(spot[0]), int(spot[1])
    return slice(max(row - half, 0), row + half), slice(max(column - half, 0), column + half)


def measured(out, views, size, foot):
    """{view: {changed, pad before, pad after, seconds}} on the rendered pictures."""
    found = {}
    for view in views:
        name = view["name"]
        before, after = (brightness(terrain_look.rendered(out, state, name, "look")) for state in STATES)
        entry = {"seconds": view["seconds"], "changed": round(float((np.abs(after - before) > CHANGED).mean()), 5)}
        window = pad_window(view, foot, size)
        if window is not None:
            entry["pad before"] = round(float(before[window].mean()), 5)
            entry["pad after"] = round(float(after[window].mean()), 5)
        found[name] = entry
    return found


def make(inputs, out, seed, params):
    """Render the place without and with its effects on its review cameras at each moment, and measure both."""
    after_folder = pathlib.Path(inputs["assembly"])
    place = next(after_folder.glob("*.usda")).stem
    record = json.loads(pathlib.Path(inputs["views"]).read_text())
    _, rest, motion = rocket(inputs)
    views = moment_views(record, motion)
    jobs = []
    for state in STATES:
        folder = terrain_look.tree(out, state, place, after_folder, inputs)
        if state == "before":
            without_effects(folder, place)
        jobs += view_jobs(folder, place, views, record["size"], out / state)
    terrain_look.render(jobs, out)
    shutil.rmtree(out / "stages")
    for leftover in out.glob("job-*.json"):
        leftover.unlink()
    (out / "measures.json").write_text(json.dumps({"place": place, "size": record["size"], "lift": lift_second(motion),
                                                   "views": measured(out, views, record["size"], rest)}, indent=1))


def judge_shown(output, inputs, evidence):
    """Pass when every view from the engines' start on shows the effects."""
    found = json.loads((output / "measures.json").read_text())
    _, _, motion = rocket(inputs)
    lit = {name: entry for name, entry in found["views"].items() if entry["seconds"] >= float(motion["start"])}
    bare = [f"{name}: {entry['changed']:.4f} of the picture changed" for name, entry in lit.items()
            if entry["changed"] < SHOWN_LEAST]
    least = min(entry["changed"] for entry in lit.values())
    return checks.Verdict("shown", checks.FAIL if bare else checks.PASS,
                          f"{len(bare)} of {len(lit)} views show no effect" if bare
                          else f"every one of {len(lit)} views shows the effects", {"least changed": least},
                          {"least changed": "higher"}, tuple(bare))


def judge_lit(output, inputs, evidence):
    """Pass when the pad round the rocket's foot is lit LIT_OVER times as bright as without the flame, up to
    LIT_UNTIL seconds after lift-off, in every view that sees it."""
    found = json.loads((output / "measures.json").read_text())
    _, _, motion = rocket(inputs)
    judged = {name: entry for name, entry in found["views"].items()
              if float(motion["start"]) < entry["seconds"] <= found["lift"] + LIT_UNTIL and "pad after" in entry}
    if not judged:
        return checks.Verdict("lit", checks.UNKNOWN, "no view sees the pad while the flame is near it")
    ratios = {name: entry["pad after"] / max(entry["pad before"], 1e-4) for name, entry in judged.items()}
    dark = [f"{name}: the pad {ratio:.2f} times as bright" for name, ratio in ratios.items() if ratio < LIT_OVER]
    return checks.Verdict("lit", checks.FAIL if dark else checks.PASS,
                          f"{len(dark)} of {len(ratios)} views see the pad unlit by the flame" if dark
                          else f"the flame lights the pad in all {len(ratios)} views that see it",
                          {"least brighter": round(min(ratios.values()), 3)}, {"least brighter": "higher"},
                          tuple(dark or [f"{name}: {ratio:.2f} times" for name, ratio in ratios.items()]))


def look_faults(folder):
    """Every measured view has its look before and after."""
    folder = pathlib.Path(folder)
    if not (folder / "measures.json").exists():
        return ["no measures.json"]
    views = json.loads((folder / "measures.json").read_text())["views"]
    return [f"{name} lacks its {state} look" for name in views for state in STATES
            if terrain_look.rendered(folder, state, name, "look") is None] or ([] if views else ["no view measured"])


LOOK = contracts.Contract("effects-look", 1, look_faults, {"length": "metre", "time": "second"})
CHECKS = (checks.Check("shown", judge_shown), checks.Check("lit", judge_lit))
