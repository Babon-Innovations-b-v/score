"""Runs inside Blender: a walker peel in its place (`../peel.py` walker_job writes the job and joins the passes).

    blender -b --python walker_peel.py -- <scene.usda> <views.json> <out folder>   (usd_views.py's arguments)

The place drawn as its film draws it (score/stages/place_build/blender_views.py: usd_views.py with the laid place's
ground, glass, tiled maps and palette recipes, its own lights, sky and grade), its walkers played as the film plays
them, on the views' camera; one walker (the job's) peeled in three passes, each written to <job out>/<pass>/<frame>.png
for the frames the job's `draws` names (and the concept's view, `opening`, for the views o<frame> where the film
dissolves in from it): `dressed` (the place as it is), `mesh` (the walker's bare SOMA surface at the
job's points, solid with its edges drawn) and `sim` (its sim body layer, timed to the place, each touching body's
push an arrow, its muscles in the film's activation colours), the walker's own dressed body hidden in the last two. The peel's drawing is body_peel.py's (bare,
sim, arrow_at, faded); nothing here works out a pose, a push or a camera.
"""
import json
import pathlib
import sys

import bpy
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path[:0] = [str(HERE), str(REPO / "tools/blender/inside"), str(REPO / "score/stages/place_build")]
import body_peel  # noqa: E402
import usd_views  # noqa: E402

LISTING = json.loads(pathlib.Path(sys.argv[sys.argv.index("--") + 2]).read_text())
JOB = json.loads(pathlib.Path(LISTING["peel"]).read_text())
PEELED = {}


def own_body(name):
    """The walker's own drawn objects in the place (the film's dressed body under its SkelRoot)."""
    root = bpy.data.objects.get(name)
    if root is None:
        raise RuntimeError(f"the place holds no walker {name}")
    return [item for item in [root, *root.children_recursive] if item.type != "EMPTY"]


def peeled():
    """The walker's peel laid over the imported place: its passes' collections and their parts."""
    groups = {name: body_peel.collection(name) for name in ("mesh", "sim")}
    look = {"sim": body_peel.material("sim", body_peel.SIM, alpha=0.55),
            "arrow": body_peel.material("arrow", tuple(JOB["arrows"]["colour"]), glow=body_peel.ARROW_GLOW,
                                        alpha=body_peel.ARROW_ALPHA),
            "coloured": body_peel.coloured()}
    look["muscles"] = dict(JOB["muscles"], material=body_peel.activation(JOB["muscles"]))
    person = JOB["people"][0]
    arrays = dict(np.load(person["arrays"]))
    mesh = body_peel.bare(person, arrays, groups["mesh"])
    arrows = body_peel.sim(person, arrays, groups["sim"], look)
    return {"groups": groups, "look": look, "arrays": arrays, "mesh": mesh, "arrows": arrows,
            "own": own_body(JOB["walker"])}


def with_peel(importer):
    def imported(stage):
        objects = importer(stage)
        PEELED.update(peeled())
        return objects
    return imported


def shown(name):
    """The pass `name` alone on show: the walker's own body only in `dressed`, its SOMA surface or its sim body only
    in their own."""
    for item in PEELED["own"]:
        item.hide_render = name != "dressed"
    for other, group in PEELED["groups"].items():
        group.hide_render = other != name


def posed(scene, frame):
    """The walker's SOMA surface and push arrows at film frame `frame` (the place's time is already set)."""
    arrays, fade = PEELED["arrays"], JOB["arrows"]["fade"][frame]
    PEELED["mesh"].vertices.foreach_set("co", arrays["points"][frame].astype(np.float32).ravel())
    PEELED["mesh"].update()
    body_peel.faded(PEELED["look"]["arrow"], fade)
    for parts, start, vector in zip(PEELED["arrows"], arrays["arrow_start"][frame], arrays["arrow_vector"][frame]):
        body_peel.arrow_at(parts, start, vector, scene.camera, fade, JOB["arrows"]["full"])


def with_passes(render):
    def drawn(scene, path, transparent):
        view = pathlib.Path(path).name  # usd_views' <view name>-look.png, the view f<frame> (o<frame> the opening's)
        frame = int(view[1:5])
        if view.startswith("o"):  # the concept's view the film dissolves in from: the place as it is
            shown("dressed")
            render(scene, pathlib.Path(JOB["out"]) / "opening" / f"{frame:04d}.png", transparent)
            return
        posed(scene, frame)
        for name in JOB["draws"][frame]:
            shown(name)
            render(scene, pathlib.Path(JOB["out"]) / name / f"{frame:04d}.png", transparent)
        shown("dressed")
    return drawn


usd_views.import_stage = with_peel(usd_views.import_stage)
usd_views.render = with_passes(usd_views.render)
import blender_views  # noqa: E402,F401  (runs usd_views.main() with the laid place's look)
