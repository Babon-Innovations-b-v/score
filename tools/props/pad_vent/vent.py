"""The 2099 prologue pad's cryogenic venting before launch (2099 #161): the liquid oxygen boiling off through the
countdown, let out of a vent on the rocket's side as a cloud of cold white vapour that sinks and drifts, and the
vapour creeping down the body to swell round its foot. Two score_lib effect entries baked by the particle effects
algorithm (tools/usd/effects.py), each played on a loop while the rocket stands fuelled.

    .venv/bin/python tools/props/pad_vent/vent.py <out folder>

Writes <out>/lox_vent/ and <out>/foot_vapour/, each effect.usda (its default prim /vent: the emitter standing at its
root, y up), the clip.usdc it plays and settings.json (the record, its footage, each check's measure).

The numbers are the launch's footage-measured venting (score git e9e8cc813:data/effects/launch.json, `lox_vent` and
`foot_vapour`, retired 2026-10-21 with every old record), measured against a Falcon rocket of 70 m. The builder's own
changes, each for the pad's rocket (place/pad@10's `rocket`, 48 m high, its hull 9.06 m across):
- every length, speed, slowing and fall scaled by 48/70 (the footage's checks are in rocket heights), the noise's
  scale left as it was;
- the foot's ring round this hull: 4.6 to 5.2 m out (the record's 0.6 m band), 0.257 of its height tall, its middle
  0.146 of its height over the foot, as the record stood it;
- looped, not let out once from 12 s before the stage to lift-off: the footage's boil-off goes on through the whole
  countdown (nasa-DSCOVR-blog), and the game stops the emitters at ignition.
"""
import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np
from pxr import Sdf, Usd, UsdGeom

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
sys.path.insert(0, str(REPO))
import effects  # noqa: E402

ROCKET = 48.0
SCALE = ROCKET / 70.0
HULL = 4.6
FOOT_RING = (HULL + 0.6, HULL, 18.0 / 70.0 * ROCKET)
FOOT_LIFT = 10.2 / 70.0 * ROCKET
SOURCES = {
    "NHQ202302270024": {
        "what": "NASA/Joel Kowsky, Falcon 9 for Crew-6 fuelled on LC-39A at night, 27 February 2023",
        "url": "https://images.nasa.gov/details/NHQ202302270024",
        "measured": "measured on a 1400 px copy against the rocket's own published lengths (70 m, 0.129 m a pixel, its "
                    "height about 544 px): the vent's cloud on its left side between 0.59 and 0.76 of its height, "
                    "reaching 0.11 of it out from the body and 0.17 tall; below 0.45 to 0.50 of its height the vapour "
                    "hugs the body down to the foot and swells into lobes reaching 0.16 to 0.20 of its height out at "
                    "0.26 of it up, its edge opening about 40 degrees off upright; bright soft white, see-through at "
                    "its edges"},
    "commons-CRS-5-16512101410": {
        "what": "SpaceX, Falcon 9 for CRS-5 on SLC-40 at night, 10 January 2015 (Wikimedia Commons, CC0)",
        "url": "https://commons.wikimedia.org/wiki/File:Falcon_9_preparing_to_launch_CRS-5_Dragon,_ISS_trail_in_"
               "night_sky_(16512101410).jpg",
        "measured": "measured against the rocket's height in the picture (862 px): the main vent leaving at 0.51 to "
                    "0.63 of its height, carried sideways and down about 30 degrees below level for 0.41 of its "
                    "height, about 35 degrees either side near the vent narrowing to about 10 further out"},
    "nasa-DSCOVR-blog": {
        "what": "NASA's DSCOVR blog, fuelling continues for Falcon 9, 10 February 2015",
        "url": "https://science.nasa.gov/blogs/dscovr/2015/02/10/fueling-continues-for-falcon-9/",
        "measured": "read: the liquid oxygen boils off through the countdown, is let out as the cloud beside the rocket "
                    "and is topped up to the last moments"}}
LICENCE = "NASA photographs (not copyrighted in the United States) and a CC0 photograph, used only as measurements."
LOX = {"name": "lox_vent", "kind": "cryogenic_vent", "look": "puff", "card": "plain", "placement": {},
       "emitter": {"shape": "sphere", "radius": 0.1 * SCALE}, "count": 20000, "lifetime": 7.0,
       "direction": [1.0, -0.6, 0.0], "spread": 14.0, "speed": [2.0 * SCALE, 3.0 * SCALE],
       "damping": [0.3 * SCALE, 0.5 * SCALE], "gravity": [0.0, -0.3 * SCALE, 0.0], "size": 0.6 * SCALE,
       "scale": [0.7, 1.4], "size_over_life": [[0.0, 0.4], [0.3, 2.0], [1.0, 5.0]], "colour": "#eef2f6",
       "opacity": 0.08, "opacity_over_life": [[0.0, 0.0], [0.05, 1.0], [0.6, 0.6], [1.0, 0.0]],
       "turbulence": {"strength": 0.5, "scale": 0.3, "influence": [0.005, 0.02]}, "near_fade": [1.0, 6.0],
       "space": "world", "seed": 701,
       "from": "footage: NHQ202302270024, commons-CRS-5-16512101410, nasa-DSCOVR-blog (the liquid oxygen boiling off "
               "through the countdown, let out of a vent on the rocket's side at 0.55 to 0.75 of its height as a "
               "cloud of cold white vapour reaching 0.1 to 0.45 of its height, 10 to 40 degrees either side, sinking "
               "and drifting down; scaled to a 48 m rocket, looped through the countdown (tools/props/pad_vent))"}
FOOT = {"name": "foot_vapour", "kind": "cryogenic_vent_foot", "look": "puff", "card": "plain", "placement": {},
        "emitter": {"shape": "ring", "radius": FOOT_RING[0], "inner": FOOT_RING[1], "height": FOOT_RING[2]},
        "count": 16000, "lifetime": 12.0, "direction": [1.0, 0.0, 0.0], "spread": 180.0, "flatness": 0.6,
        "speed": [0.4 * SCALE, 1.2 * SCALE], "damping": [0.02 * SCALE, 0.05 * SCALE],
        "gravity": [0.0, -0.05 * SCALE, 0.0], "size": 1.0 * SCALE, "scale": [0.7, 1.4],
        "size_over_life": [[0.0, 0.5], [0.3, 2.5], [1.0, 5.0]], "colour": "#eef2f6", "opacity": 0.06,
        "opacity_over_life": [[0.0, 0.0], [0.05, 1.0], [0.7, 0.6], [1.0, 0.0]],
        "turbulence": {"strength": 0.4, "scale": 0.15, "influence": [0.02, 0.06]}, "near_fade": [1.0, 6.0],
        "space": "world", "seed": 702,
        "from": "footage: NHQ202302270024 (in still air the vapour sinks and creeps down the rocket's side to its foot "
                "as a sheath, swelling into lobes that reach 0.15 to 0.6 of its height round the foot and stand 0.25 "
                "to 0.6 of it high, a thin lit veil, never loose blobs; scaled to a 48 m rocket and its 9.06 m hull, "
                "looped through the countdown (tools/props/pad_vent))"}
# The footage's checks (the launch record's), in rocket heights; the spread read within 8/70 of a height of the vent.
CHECKS = {"lox_vent": {"length": (0.1, 0.45), "spread": (10.0, 40.0), "loose": (0.0, 0.01)},
          "foot_vapour": {"reach": (0.15, 0.6), "height": (0.25, 0.6), "loose": (0.0, 0.01)}}
NEAR = 8.0 / 70.0 * ROCKET
ROOT = "/vent"


def emitters():
    """{name: the emitter as the bake reads it}, each standing at its own root, upright."""
    return {record["name"]: dict(record, origin=np.zeros(3), basis=np.eye(3)) for record in (LOX, FOOT)}


def sample_measures(name, spots, sizes):
    """One sample's measures for the emitter `name`, lengths in rocket heights."""
    from score.stages.effects import height, length, loose, reach, spread
    if name == "lox_vent":
        near = np.linalg.norm(spots, axis=1) <= NEAR
        return (length(spots, sizes, np.zeros(3)) / ROCKET, spread(spots[near], np.zeros(3)), loose(spots, sizes))
    foot = np.array([0.0, -FOOT_LIFT, 0.0])
    return (reach(spots, sizes, foot) / ROCKET, height(spots, sizes, foot) / ROCKET, loose(spots, sizes))


def measures(name, points, widths):
    """{check: (least, most)} over every sample of the loop for the emitter `name`."""
    rows = np.asarray([sample_measures(name, spots[sizes > 0], sizes[sizes > 0])
                       for spots, sizes in zip(points, widths)])
    return {check: (float(rows[:, column].min()), float(rows[:, column].max()))
            for column, check in enumerate(CHECKS[name])}


def faults(name, found):
    """Each footage check of `name` a measure's least or most falls outside of, in words."""
    said = []
    for check, (low, high) in CHECKS[name].items():
        least, most = found[check]
        if least < low or most > high:
            said.append(f"{name} {check} {least:.3f} to {most:.3f}, outside {low} to {high}")
    return said


def written_one(name, emitter, out):
    """effect.usda, clip.usdc and settings.json of one emitter written into `out`; the effect file's path. Refused
    (ValueError) when its bake misses a footage check."""
    out.mkdir(parents=True, exist_ok=True)
    points, widths, _ = effects.bake(emitter)
    found = measures(name, points, widths)
    if faults(name, found):
        raise ValueError(f"the venting misses its footage: {'; '.join(faults(name, found))}")
    record = LOX if name == "lox_vent" else FOOT
    with tempfile.TemporaryDirectory() as work:
        layer = Sdf.Layer.CreateNew(str(pathlib.Path(work) / "effect.usda"))
        layer.timeCodesPerSecond = effects.RATE
        layer.framesPerSecond = effects.RATE
        stage = Usd.Stage.Open(layer)
        root = UsdGeom.Xform.Define(stage, ROOT).GetPrim()
        stage.SetDefaultPrim(root)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        effects.write_emitter(stage, ROOT, emitter, work)
        root.CreateAttribute("score:effect:kind", Sdf.ValueTypeNames.String).Set(record["kind"])
        root.CreateAttribute("score:effect:from", Sdf.ValueTypeNames.String).Set(record["from"])
        points_prim = stage.GetPrimAtPath(f"{ROOT}/{name}/{name}_points")
        Usd.ClipsAPI(points_prim).SetClipAssetPaths([Sdf.AssetPath("./clip.usdc")])
        layer.Save()
        shutil.copyfile(layer.realPath, out / "effect.usda")
        shutil.copyfile(pathlib.Path(work) / effects.ASSETS / f"{name}.usdc", out / "clip.usdc")
    settings = {"emitter": record, "sources": SOURCES, "licence": LICENCE,
                "checks": {check: list(bounds) for check, bounds in CHECKS[name].items()},
                "measured": {check: list(bounds) for check, bounds in found.items()},
                "samples": len(points), "loop_seconds": effects.loop_of(emitter)}
    (out / "settings.json").write_text(json.dumps(settings, indent=1) + "\n")
    return out / "effect.usda"


def written(out):
    """Both emitters written under `out`, one folder each; {name: effect file}."""
    out = pathlib.Path(out)
    return {name: written_one(name, emitter, out / name) for name, emitter in emitters().items()}


if __name__ == "__main__":
    for name, path in written(sys.argv[1]).items():
        print(name, path)
