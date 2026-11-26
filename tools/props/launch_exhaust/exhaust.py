"""The 2099 prologue launch's exhaust: the white core of the flame and the orange flame under the rocket's engines, the
hot exhaust glowing as it spreads over the pad at ignition, and the pale column of exhaust the rocket leaves under it as
it climbs. Four score_lib effect entries baked by the particle effects algorithm (tools/usd/effects.py).

    .venv/bin/python tools/props/launch_exhaust/exhaust.py <out folder> <smoke_billow folder>

Writes <out>/<name>/ for flame_core, flame, pad_fire and plume, each effect.usda (its default prim /exhaust: the
emitter at its root, y up: the flames riding the rocket's engines, the pad's fire on the pad under them, the plume let
out where the climbing rocket's engines stood), the clip.usdc it plays and settings.json (the record, its footage,
each check's measure); the plume's cards draw the smoke flipbook (its two atlases beside it, tools/props/smoke_card).

The numbers are the launch's footage-measured exhaust (score git e9e8cc813:data/effects/launch.json, `flame_core`,
`flame`, `pad_fire` and `plume`, its footage checks, and the climb of e9e8cc813:data/motion/launch.json: the engines
light 1 s into the event and the rocket lifts 3 s later at a push of 24 m/s/s against 9.81), measured against a Falcon
Heavy of about 70 m. The builder's own changes, each for the pad's rocket (place/pad's `rocket`, 48 m high):
- every length, speed and slowing scaled by 48/70 (the footage's checks are in rocket heights), the climb's push and
  pull left as they were (an acceleration the rocket's size does not change), the noise's scale left as it was;
- the plume's cards drawn with the smoke flipbook (`card` billow) instead of the dust card's tint, its colour the
  smoke's own.
"""
import json
import pathlib
import shutil
import subprocess
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
LIFT = 4.0            # the rocket lifts 4 s into the event: its climb starts at 1 s and lifts 3 s later
CLIMB = {"start": 1.0, "lift": 3.0, "push": 24.0, "pull": 9.81}
ROOT = "/exhaust"
NAMES = ("flame_core", "flame", "pad_fire", "plume")
ATLASES = ("smoke_a.png", "smoke_b.png")
RECORD = ("e9e8cc813", "data/effects/launch.json")


def scaled(record):
    """A launch record's emitter scaled to the pad's rocket; the plume's cards the smoke flipbook's."""
    out = dict(record)
    shape = dict(record["emitter"])
    for key in ("radius", "inner", "height"):
        if key in shape:
            shape[key] = shape[key] * SCALE
    out["emitter"] = shape
    for key in ("speed", "damping", "radial_accel"):
        if key in record:
            out[key] = [value * SCALE for value in record[key]]
    out["size"] = record["size"] * SCALE
    placement = record["placement"]
    out["lift"] = float(placement.get("offset", [0.0, placement.get("ground", [0, 0, 0])[2], 0.0])[1]) * SCALE
    out["placement"] = {}
    if record["name"] == "plume":
        out["card"] = "billow"
        out["climb"] = dict(CLIMB)
    out["from"] = (record["from"] + "; scaled to a 48 m rocket" + (", its puffs drawn with the smoke flipbook "
                   "effect/smoke_billow" if record["name"] == "plume" else "") + " (tools/props/launch_exhaust)")
    return out


def records():
    """{name: the launch record's emitter, scaled} for the four exhaust emitters, and the record's footage."""
    text = subprocess.run(["git", "-C", str(REPO), "show", ":".join(RECORD)], capture_output=True, text=True,
                          check=True).stdout
    launch = json.loads(text)
    named = {entry["name"]: entry for entry in launch["effects"]}
    return {name: scaled(named[name]) for name in NAMES}, launch["footage"]


def emitters(found):
    """{name: the emitter as the bake reads it}, each standing at its own lift over its root, upright."""
    return {name: dict(record, origin=np.array([0.0, record["lift"], 0.0]), basis=np.eye(3))
            for name, record in found.items()}


def measured(found, baked, footage):
    """[(check, the emitter, its least and most over every sample of the flame's loop, its range)] for the footage's
    flame checks: how far each flame reaches under the engines (95th share), in rocket heights. The flames burn the
    same through their loop from the engines' light, so every sample of it is held to the footage."""
    rows = []
    for check in footage["checks"]:
        if check["measure"] != "flame_length":
            continue
        (name,) = check["emitters"]
        points, widths = baked[name][:2]
        values = [float(np.percentile(-spots[sizes > 0][:, 1], 95)) / ROCKET
                  for spots, sizes in zip(points, widths) if (sizes > 0).any()]
        rows.append((check["name"], name, min(values), max(values), list(check["range"])))
    return rows


def faults(rows):
    """Each check whose measure falls outside its range, in words."""
    return [f"{name} {least:.3f} to {most:.3f}, outside {low} to {high}" for name, _, least, most, (low, high) in rows
            if least < low or most > high]


def baked_exhaust():
    """The four emitters' records, the footage and each emitter's bake: (found, footage, {name: bake})."""
    found, footage = records()
    return found, footage, {name: effects.bake(emitter) for name, emitter in emitters(found).items()}


def written_one(name, emitter, record, out, flipbook_folder):
    """effect.usda and clip.usdc of one emitter written into `out` (and the flipbook's atlases for one that draws it);
    the effect file's path."""
    out.mkdir(parents=True, exist_ok=True)
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
        if record.get("card") == "billow":
            root.CreateAttribute("score:effect:flipbook", Sdf.ValueTypeNames.AssetArray).Set(
                [Sdf.AssetPath(f"./{atlas}") for atlas in ATLASES])
            for atlas in ATLASES:
                shutil.copyfile(pathlib.Path(flipbook_folder) / atlas, out / atlas)
        points_prim = stage.GetPrimAtPath(f"{ROOT}/{name}/{name}_points")
        Usd.ClipsAPI(points_prim).SetClipAssetPaths([Sdf.AssetPath("./clip.usdc")])
        layer.Save()
        shutil.copyfile(layer.realPath, out / "effect.usda")
        shutil.copyfile(pathlib.Path(work) / effects.ASSETS / f"{name}.usdc", out / "clip.usdc")
    return out / "effect.usda"


def written(out, flipbook_folder, exhaust=None):
    """The four emitters baked (or `exhaust`, baked_exhaust's), the flames checked against the footage, and written
    under `out`; {name: effect file}. Refused (ValueError) when a flame misses its footage."""
    out = pathlib.Path(out)
    found, footage, baked = exhaust or baked_exhaust()
    rows = measured(found, baked, footage)
    if faults(rows):
        raise ValueError(f"the launch's exhaust misses its footage: {'; '.join(faults(rows))}")
    paths = {}
    for name, emitter in emitters(found).items():
        paths[name] = written_one(name, emitter, found[name], out / name, flipbook_folder)
        settings = {"emitter": found[name], "carried_from": ":".join(RECORD),
                    "sources": footage["sources"], "rocket_m": ROCKET, "lift_s": LIFT,
                    "checks": [{"name": check, "measured": [least, most], "range": bounds}
                               for check, emitter_name, least, most, bounds in rows if emitter_name == name],
                    "samples": len(baked[name][0]), "loop_seconds": effects.loop_of(emitter)}
        (out / name / "settings.json").write_text(json.dumps(settings, indent=1) + "\n")
    return paths


if __name__ == "__main__":
    for name, path in written(sys.argv[1], sys.argv[2]).items():
        print(name, path)
