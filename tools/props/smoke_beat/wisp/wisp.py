"""The smoke the 2099 prologue's cigarette gives off (#152): the thin thread rising off its lit end, baked by the
particle effects algorithm (tools/usd/effects.py, score_lib algorithm/particle_effects) as a score_lib effect entry.

    .venv/bin/python tools/props/smoke_beat/wisp/wisp.py <out folder>

Writes <out>/effect.usda (its default prim /smoke: the emitter /smoke/wisp with its score:effect:* schema, standing at
the lit end with y up, and its look /smoke/Looks/puff), <out>/clip.usdc (the baked particles the emitter plays, looped
over the stage's time) and <out>/settings.json (the emitter's record, its footage and each check's measure).

The numbers are the flat's footage-measured wisp (score git c3ef49db0^:data/effects/flat.json, retired 2026-10-21
with every old record, its entry effect/wisp@1 withdrawn the same day), carried whole except where it stood: there it
hung off the balcony camera, here it stands on the lit end, upright. One number is the builder's own: the launch cone
is 16 degrees either side, not the record's 20, which baked upright on its own read 34.0 to 35.9 degrees half angle
over its loop, past the footage's 35 (the camera's tilt bent it into range there); at 16 every sample of the loop
meets every footage check (CHECKS) with margin.
"""
import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np
from pxr import Sdf, Usd, UsdGeom

REPO = pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "tools/usd"))
sys.path.insert(0, str(REPO))
import effects  # noqa: E402

FOOTAGE = ("footage: commons-Cigarettesmoke.JPG, commons-Still_smoking_(2329760820).jpg, commons-Incense_stick.JPG "
           "(one thin thread off the lit end, straight for 4 to 10 cm, then folding into curls and sheets that widen "
           "at 15 to 35 degrees either side, one connected veil seen at least 22 cm up and never loose blobs: 3,000 "
           "fine cards a 3 s life, rising at 0.12 to 0.2 m/s and slowly growing to about 5 cm, each faint so many "
           "overlap into the thread); the colour #e5e6e6, neutral: the mean of the brightest 5% of the unclipped smoke "
           "pixels of commons-Cigarettesmoke.JPG under a warm lamp (#e0dad5) and "
           "commons-Exhaling_cloud_of_cigarette_smoke_(50652653823).png in sunlight (#eaf3f7), smoke taking its "
           "light's colour; carried from score git c3ef49db0^:data/effects/flat.json's wisp, its launch cone 16 "
           "degrees (tools/props/smoke_beat/wisp/wisp.py)")
WISP = {"name": "wisp", "kind": "smoke_wisp", "look": "puff", "placement": {}, "emitter": {"shape": "point"},
        "count": 3000, "lifetime": 3.0, "lives": 2, "direction": [0.0, 1.0, 0.0], "spread": 16.0,
        "speed": [0.12, 0.2], "rise": 0.05, "size": 0.006, "scale": [0.8, 1.4],
        "size_over_life": [[0.0, 0.5], [0.08, 1.0], [0.3, 3.0], [1.0, 8.0]], "colour": "#e5e6e6", "opacity": 0.05,
        "opacity_over_life": [[0.0, 0.0], [0.05, 1.0], [0.5, 0.6], [1.0, 0.0]],
        "turbulence": {"strength": 0.5, "scale": 6.0, "influence": [0.01, 0.06]}, "near_fade": [1.0, 6.0],
        "space": "world", "seed": 31, "from": FOOTAGE}
SOURCES = {
    "commons-Cigarettesmoke.JPG": {
        "what": "a hand-held lit cigarette, its smoke against a plain wall in still indoor air (Wikimedia Commons)",
        "url": "https://commons.wikimedia.org/wiki/File:Cigarettesmoke.JPG",
        "measured": "measured on its pixels against the cigarette's 7.8 mm width (15 px of 900): clear for about 1.5 "
                    "cm over the ember, one straight thread about 6.8 cm long, then folding into sheets and curls; "
                    "the plume at least 22 cm over the tip before the frame's edge, widening at 25 to 35 degrees "
                    "either side above the break; one connected veil, no loose blobs"},
    "commons-Still_smoking_(2329760820).jpg": {
        "what": "a cigarette butt in an ashtray, a thin thread of smoke (Wikimedia Commons)",
        "url": "https://commons.wikimedia.org/wiki/File:Still_smoking_(2329760820).jpg",
        "measured": "measured against the butt's 7.8 mm width (55 px): one faint thread 6.5 cm up to the frame's "
                    "top, still unbroken, meandering from 3.5 cm up"},
    "commons-Incense_stick.JPG": {
        "what": "an incense stick's smoke on black, the same kind of plume (Wikimedia Commons)",
        "url": "https://commons.wikimedia.org/wiki/File:Incense_stick.JPG",
        "measured": "measured against the stick (3 to 5 mm across): smooth for about 4 to 6 cm, then curling, seen "
                    "10 to 17 cm up, fanning out at about 28 degrees either side; folded sheets, no blobs"}}
# The footage's checks (the flat record's), each read on every sample of the baked loop, metres from the lit end.
CHECKS = {"height": (0.22, None), "spread": (15.0, 35.0), "loose": (0.0, 0.01)}
ROOT = "/smoke"


def emitter():
    """The wisp as the bake reads it: standing at the lit end, upright."""
    return dict(WISP, origin=np.zeros(3), basis=np.eye(3))


def measures(points, widths):
    """{check: (least, most)} over every sample of the loop: the plume's height (95th share of its tops), its half
    angle and its share of loose particles, as the effects stage measures them."""
    from score.stages.effects import height, loose, spread
    rows = []
    for spots, sizes in zip(points, widths):
        alive = sizes > 0
        rows.append((height(spots[alive], sizes[alive], np.zeros(3)), spread(spots[alive], np.zeros(3)),
                     loose(spots[alive], sizes[alive])))
    rows = np.asarray(rows)
    return {name: (float(rows[:, column].min()), float(rows[:, column].max()))
            for column, name in enumerate(CHECKS)}


def faults(found):
    """Each footage check a measure's least or most falls outside of, in words."""
    said = []
    for name, (low, high) in CHECKS.items():
        least, most = found[name]
        if (low is not None and least < low) or (high is not None and most > high):
            said.append(f"{name} {least:.3f} to {most:.3f}, outside {low} to {high}")
    return said


def written(out):
    """effect.usda, clip.usdc and settings.json written into `out`; the effect file's path. Refused (ValueError) when
    the bake misses a footage check."""
    out = pathlib.Path(out)
    out.mkdir(parents=True, exist_ok=True)
    wisp = emitter()
    points, widths, _ = effects.bake(wisp)
    found = measures(points, widths)
    if faults(found):
        raise ValueError(f"the wisp misses its footage: {'; '.join(faults(found))}")
    with tempfile.TemporaryDirectory() as work:
        layer = Sdf.Layer.CreateNew(str(pathlib.Path(work) / "effect.usda"))
        layer.timeCodesPerSecond = effects.RATE
        layer.framesPerSecond = effects.RATE
        stage = Usd.Stage.Open(layer)
        root = UsdGeom.Xform.Define(stage, ROOT).GetPrim()
        stage.SetDefaultPrim(root)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        effects.write_emitter(stage, ROOT, wisp, work)
        root.CreateAttribute("score:effect:kind", Sdf.ValueTypeNames.String).Set(WISP["kind"])
        root.CreateAttribute("score:effect:from", Sdf.ValueTypeNames.String).Set(FOOTAGE)
        points_prim = stage.GetPrimAtPath(f"{ROOT}/wisp/wisp_points")
        Usd.ClipsAPI(points_prim).SetClipAssetPaths([Sdf.AssetPath("./clip.usdc")])
        layer.Save()
        shutil.copyfile(layer.realPath, out / "effect.usda")
        shutil.copyfile(pathlib.Path(work) / effects.ASSETS / "wisp.usdc", out / "clip.usdc")
    record = {"emitter": WISP, "sources": SOURCES, "checks": {name: list(bounds) for name, bounds in CHECKS.items()},
              "measured": {name: list(bounds) for name, bounds in found.items()},
              "samples": len(points), "loop_seconds": effects.loop_of(wisp)}
    (out / "settings.json").write_text(json.dumps(record, indent=1) + "\n")
    return out / "effect.usda"


if __name__ == "__main__":
    print(written(sys.argv[1]))
