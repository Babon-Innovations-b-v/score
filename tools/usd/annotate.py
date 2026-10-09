"""The annotate step: any check's eyes on a place's OpenUSD stage, measured rather than judged. From any camera it gives
the look, and per pixel the object shown, its distance and its facing; from those, each object's mask and the
occlusion boundaries (where one object stands in front of another).

    import annotate
    views = [annotate.view("crate", eye, aim, fov=40.0, only=["/hub/Objects/crate_1"])]
    found = annotate.run(stage, views, out, cloud=True)       # renders in headless Blender (here or on a rented box)
    seen = annotate.load(out, "crate")                       # {"depth", "normal", "ids", "paths", "look"}
    annotate.mask(seen, "/hub/Objects/crate_1")              # that object's pixels (a bool array)
    annotate.occlusion_boundaries(seen)                      # pixels where a nearer object hides a farther one

    .venv/bin/python tools/usd/annotate.py <stage.usda> <views.json> <out folder> [--cloud]

The Blender side is tools/blender/inside/annotate_stage.py (Cycles' object index, depth and normal passes). The same
step is what the resting triage's close-ups (triage.py --closeups) and the render-and-compare (compare.py) draw with,
and it is the labelling step a world for robot training takes its labels from (depth, normals, per-object masks and
boundaries for every frame of a camera path). ProcFunc's released code (v0.37.0, 2026-10-09) has no annotation API, and
Infinigen's own annotations run only on scenes Infinigen generated; this runs on any stage.
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
SESSION = REPO / "tools/blender/session.py"
INSIDE = REPO / "tools/blender/inside/annotate_stage.py"
SIZE = (640, 480)
# Two neighbouring pixels of different objects are an occlusion boundary when the farther lies this share further away.
OCCLUSION_STEP = 0.05
# How far a fault's close-up camera stands from what it looks at, as a multiple of the object's size, and its least.
CLOSEUP_DISTANCE = 2.2
CLOSEUP_LEAST = 1.2
CLOSEUP_WAY = np.array([1.0, 0.7, 1.0]) / np.linalg.norm([1.0, 0.7, 1.0])


def view(name, eye, aim, fov=40.0, up=(0.0, 1.0, 0.0), only=None, look=True):
    """One camera of the annotate step: points in the stage's frame (metres, y up), `only` the prim paths drawn."""
    found = {"name": name, "eye": [float(value) for value in eye], "aim": [float(value) for value in aim],
             "up": list(up), "fov": float(fov), "look": look}
    if only:
        found["only"] = list(only)
    return found


def run(stage, views, out, cloud=False, size=SIZE, classes=None, machine=None):
    """Render every view of the stage into `out` (here, on a rented machine of its own with `cloud`, or on a machine a
    caller holds for a chain of jobs, blender_cloud.Machine); the folder."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    job = out / "annotate-job.json"
    job.write_text(json.dumps({"size": list(size), "views": views}, indent=1))
    stage = pathlib.Path(stage).resolve()
    if cloud or machine is not None:
        sys.path.insert(0, str(REPO / "tools/props/cloud"))
        import blender_cloud
        outputs = [out / "ids.json"] + [out / f"{entry['name']}-{part}" for entry in views
                                        for part in (("look.png", "passes.npz") if entry.get("look", True)
                                                     else ("passes.npz",))]
        if machine is not None:
            machine.run(INSIDE, [stage, job, out], [stage.parent, job], outputs, max(5, len(views) // 4))
            return out
        blender_cloud.run_elsewhere(INSIDE, [stage, job, out], [stage.parent, job], outputs,
                                    classes or blender_cloud.DEFAULT_CLASSES, "annotate",
                                    minutes=max(5, len(views) // 4))
        return out
    command = [sys.executable, str(SESSION), "batch", str(INSIDE), "--", str(stage), str(job), str(out)]
    if subprocess.run(command, stdout=subprocess.DEVNULL).returncode != 0:
        raise RuntimeError(f"the annotate run failed; run it by hand to see its output: {command}")
    return out


def load(out, name):
    """One view's annotations: depth, normal and ids arrays, {id: prim path}, and the look's file if drawn."""
    out = pathlib.Path(out)
    with np.load(out / f"{name}-passes.npz") as passes:
        found = {key: passes[key] for key in ("depth", "normal", "ids")}
    found["paths"] = {int(key): value for key, value in json.loads((out / "ids.json").read_text()).items()}
    look = out / f"{name}-look.png"
    found["look"] = look if look.exists() else None
    return found


def mask(seen, path):
    """The pixels of one laid object (by prim path) in a view, as a bool array."""
    number = next((number for number, found in seen["paths"].items() if found == path), None)
    return seen["ids"] == number if number is not None else np.zeros(seen["ids"].shape, dtype=bool)


def occlusion_boundaries(seen, step=OCCLUSION_STEP):
    """The pixels where a nearer object stands in front of a farther one (or of nothing): between two neighbours of
    different objects whose distances differ by more than `step` of the nearer, the nearer pixel."""
    ids, depth = seen["ids"], np.where(np.isfinite(seen["depth"]), seen["depth"], np.inf)
    found = np.zeros(ids.shape, dtype=bool)
    for axis in (0, 1):
        here = [slice(None), slice(None)]
        there = [slice(None), slice(None)]
        here[axis], there[axis] = slice(0, -1), slice(1, None)
        near, far = depth[tuple(here)], depth[tuple(there)]
        apart = (ids[tuple(here)] != ids[tuple(there)]) & (np.abs(near - far) > step * np.minimum(near, far))
        found[tuple(here)] |= apart & (near < far)
        found[tuple(there)] |= apart & (far < near)
    return found


def aimed_at(name, point, size, only):
    """A close-up camera on a point: from up and to the side, at a distance by the object's size."""
    distance = max(CLOSEUP_LEAST, CLOSEUP_DISTANCE * float(size))
    return view(name, np.asarray(point) + CLOSEUP_WAY * distance, point, fov=40.0, only=only)


def fault_closeups(stage, groups, folder, cloud=False, machine=None):
    """One close-up of each group's worst fault (the object and what it meets, nothing else drawn); writes
    closeups.json beside them: {group number: its picture}."""
    import triage
    sizes = triage.object_sizes(stage)
    views = []
    for number, group in enumerate(groups, start=1):
        worst = group["worst"]
        only = [worst["object"]] + ([worst["partner"]] if worst.get("partner") else [])
        if worst["kind"] in ("floats", "sunk", "tips", "unstable"):
            only.append(f"/{worst['object'].split('/')[1]}/Ground")
        views.append(aimed_at(f"group-{number:03d}", worst["point"], sizes.get(worst["object"], 1.0), only))
    if not views:
        return {}
    run(stage, views, folder, cloud, machine=machine)
    found = {number: str(pathlib.Path(folder) / f"group-{number:03d}-look.png") for number in range(1, len(views) + 1)}
    (pathlib.Path(folder) / "closeups.json").write_text(json.dumps(found, indent=1))
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("views", type=pathlib.Path, help="a JSON list of views (annotate.view's fields)")
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--cloud", action="store_true")
    options = parser.parse_args()
    print(run(options.stage, json.loads(options.views.read_text()), options.out, options.cloud))


if __name__ == "__main__":
    main()
