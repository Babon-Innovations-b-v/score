"""Runs inside Blender on the rented card (score/stages/library/clips, the library-clips row): every item of a manifest
rendered in turn on this one machine, each by the films' drawer (tools/blender/inside/usd_views.py), its views from
framing.py round the box of what it shows.

    blender -b --python score/stages/library/clips/blender/render_clips.py -- <manifest.json> <out folder>

manifest.json: {"search": the library folder its entries were fetched into (their score_lib/... paths resolve
against it), "size": [wide, tall], "items": [{"slug", "stage", "framing", "focus", "start", "end", "per_second"}]}.
Per item: <out>/<slug>/f<NNN>-look.png and usd_views's report.json; <out>/rendered.json says per slug whether it
rendered, and why not. One item that fails is named there and the others still render.

USD reads its search path once, when it starts, so the script starts Blender again with PXR_AR_DEFAULT_SEARCH_PATH set
to the manifest's folder before it opens any stage.
"""
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
INSIDE = HERE.parents[4] / "tools/blender/inside"
SEARCH = "PXR_AR_DEFAULT_SEARCH_PATH"
BOX_SAMPLES = 8  # time codes the box of what moves is taken over


def arguments():
    given = sys.argv[sys.argv.index("--") + 1:]
    if len(given) != 2:
        raise SystemExit(__doc__)
    return given


def again_with_search(given, search):
    """This script run again in a Blender started with the search path set; its exit code."""
    import bpy
    return subprocess.run([bpy.app.binary_path, "-b", "-setaudio", "None", "--python-exit-code", "1", "--python",
                           __file__, "--", *given], env={**os.environ, SEARCH: search}).returncode


def box(stage_path, focus, codes):
    """(low, high) of what the item shows over `codes`: its focus prims, else the whole stage; a 2 m box round the
    origin when nothing has a size."""
    from pxr import Gf, Usd, UsdGeom
    stage = Usd.Stage.Open(str(stage_path))
    prims = [stage.GetPrimAtPath(path) for path in focus] if focus else [stage.GetPseudoRoot()]
    total = Gf.Range3d()
    for code in codes:
        cache = UsdGeom.BBoxCache(Usd.TimeCode(code), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
        for prim in prims:
            if prim and prim.IsValid():
                total.UnionWith(cache.ComputeWorldBound(prim).ComputeAlignedRange())
    if total.IsEmpty():
        return [-1.0, 0.0, -1.0], [1.0, 2.0, 1.0]
    return list(total.GetMin()), list(total.GetMax())


def box_codes(item):
    """The time codes the box is taken over: BOX_SAMPLES across the item's range, its start alone when it has none."""
    start, end = item["start"], item["end"]
    if end <= start:
        return [start]
    return [start + (end - start) * number / (BOX_SAMPLES - 1) for number in range(BOX_SAMPLES)]


def render_one(item, size, out):
    """One item's frames by usd_views.py into <out>/<slug>."""
    import framing
    import usd_views
    folder = out / item["slug"]
    folder.mkdir(parents=True, exist_ok=True)
    low, high = box(item["stage"], item["focus"], box_codes(item))
    views = framing.views(item["framing"], low, high, item["start"], item["end"], item["per_second"])
    views_path = folder / "views.json"
    views_path.write_text(json.dumps({"size": size, "views": views}, indent=1))
    sys.argv = [sys.argv[0], "--", str(item["stage"]), str(views_path), str(folder)]
    usd_views.main()


def main():
    given = arguments()
    manifest = json.loads(pathlib.Path(given[0]).read_text())
    if os.environ.get(SEARCH) != manifest["search"]:
        raise SystemExit(again_with_search(given, manifest["search"]))
    sys.path[:0] = [str(HERE), str(INSIDE)]
    out = pathlib.Path(given[1])
    out.mkdir(parents=True, exist_ok=True)
    rendered = {}
    for item in manifest["items"]:
        try:
            render_one(item, manifest["size"], out)
            rendered[item["slug"]] = {"rendered": True}
        except Exception as failed:  # one item's failure is its own gap, named in rendered.json; the rest still render
            rendered[item["slug"]] = {"rendered": False, "why": f"{type(failed).__name__}: {failed}"}
        (out / "rendered.json").write_text(json.dumps(rendered, indent=1))
    print("render_clips: rendered", sum(each["rendered"] for each in rendered.values()), "of", len(rendered))


main()
