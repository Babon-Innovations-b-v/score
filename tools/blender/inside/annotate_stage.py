"""Runs inside Blender (`session.py batch`, or a rented machine through blender_cloud.py): the annotate step. Load a
place's OpenUSD stage and, from each camera given, render what a check needs to measure rather than judge: the look,
and per pixel which object it shows, how far away it is and which way its surface faces.

    python3 tools/blender/session.py batch tools/blender/inside/annotate_stage.py -- <stage.usda> <job.json> <out folder>

job.json: {"size": [wide, tall], "views": [{"name", "eye", "aim", "up", "fov", "only": [prim path, ...] or absent,
"look": true}]}, points in the stage's own frame (metres, y up). A view with `only` draws those objects alone (each
named by its laid object's prim path, /<place>/Objects/<name>; everything else hidden, the ground too unless
"/<place>/Ground" is listed): a fault's close-up, one object seen alone for render-and-compare. Per view it writes
<name>-look.png when `look` (the place lit by its own lights, else a fixed sun and fill as usd_views.py lights it) and
<name>-passes.npz (depth: metres along the view; normal: the surface's facing in Blender's world, z up; ids: the
object each pixel shows, 0 for none), with ids.json beside them: {id: the laid object's prim path}. The passes are
Cycles' own (one sample: object index, depth, normal), the way Infinigen's ground-truth annotations are made from a
Blender render (vendor/infinigen, BSD-3-Clause), here on any stage instead of only on Infinigen's own scenes.
tools/usd/annotate.py turns them into per-object masks and occlusion boundaries.
"""
import json
import pathlib
import re
import sys

import bpy

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import usd_views  # noqa: E402

SUFFIX = re.compile(r"\.\d{3}$")


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 3:
        raise SystemExit(__doc__)
    return pathlib.Path(given[0]), json.loads(pathlib.Path(given[1]).read_text()), pathlib.Path(given[2])


def prim_path(item):
    """An imported object's prim path, rebuilt from its parents' names (Blender adds .001 to names it has seen)."""
    names = []
    while item is not None:
        names.append(SUFFIX.sub("", item.name))
        item = item.parent
    return "/" + "/".join(reversed(names))


def owner(item):
    """The laid object (the nearest object above with an inventory row) a mesh belongs to, else the mesh itself."""
    found = item
    while found is not None:
        if any(key.endswith("row") and "score" in key for key in found.keys()):
            return found
        found = found.parent
    return item


def numbered(objects):
    """Each mesh's owner's prim path, numbered from 1 into its pass index: {id: path}."""
    ids, paths = {}, {}
    for item in objects:
        if item.type != "MESH":
            continue
        path = prim_path(owner(item))
        if path not in ids:
            ids[path] = len(ids) + 1
            paths[ids[path]] = path
        item.pass_index = ids[path]
    return paths


def lit(scene, stage):
    """The stage's own lights, or the fixed sun and fill when it has none."""
    lights, environment = usd_views.stage_lights(stage)
    for number, entry in enumerate(lights):
        usd_views.place_light(scene, number, entry)
    if environment is not None:
        usd_views.stage_sky(scene, environment)
    else:
        usd_views.black_sky(scene)
    if not lights:
        usd_views.sun(scene, "sun", usd_views.SUN_STRENGTH, usd_views.SUN_ELEVATION, usd_views.SUN_HEADING)
        usd_views.sun(scene, "fill", usd_views.FILL_STRENGTH, usd_views.FILL_ELEVATION, usd_views.SUN_HEADING + 180.0)


def shown_only(objects, only):
    """Hide every mesh whose laid object is not one of these prim paths (None: show all)."""
    for item in objects:
        if item.type == "MESH":
            item.hide_render = only is not None and prim_path(owner(item)) not in only


def passes(scene, view, out):
    """The view's depth, normal and object ids, saved as <name>-passes.npz."""
    import numpy
    exr = out / f"{view['name']}-passes.exr"
    usd_views.pass_render(scene, exr)
    depth, normal, index = usd_views.exr_channels(exr)
    exr.unlink()
    numpy.savez_compressed(out / f"{view['name']}-passes.npz", depth=depth.astype("float32"),
                           normal=normal.astype("float32"), ids=numpy.rint(index).astype("int32"))


def main():
    stage, job, out = arguments()
    out.mkdir(parents=True, exist_ok=True)
    scene = usd_views.empty_scene()
    objects = [item for item in usd_views.import_stage(stage) if not item.hide_render]
    paths = numbered(objects)
    (out / "ids.json").write_text(json.dumps(paths, indent=1))
    usd_views.renderer(scene, job["size"])
    lit(scene, stage)
    for view in job["views"]:
        usd_views.camera(scene, view)
        shown_only(objects, set(view["only"]) if view.get("only") else None)
        if view.get("look", True):
            usd_views.render(scene, out / f"{view['name']}-look.png", transparent=bool(view.get("only")))
        passes(scene, view, out)
    print("annotate_stage: wrote", out)


if __name__ == "__main__":
    main()
