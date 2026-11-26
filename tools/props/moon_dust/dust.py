"""The 2099 prologue's Moon landing dust: the sheet of regolith the lander's engine blows out radially along the ground
as it comes down, one translucent veil 1 to 3 degrees over the ground with rocks seen through it. One score_lib effect
entry baked by the particle effects algorithm (tools/usd/effects.py), played on a loop while the engine fires near the
ground.

    .venv/bin/python tools/props/moon_dust/dust.py <out folder>

Writes <out>/landing_dust/: effect.usda (its default prim /dust: the emitter standing at its root, the ground under the
engine, y up), the clip.usdc it plays and settings.json (the record, its footage, each check's measure).

The numbers are the wreck's footage-measured landing dust (score git f46ea0f27^:data/effects/wreck.json,
`landing_dust`, its footage and checks, and the `rise` measure of f46ea0f27^:score/stages/effects/__init__.py, taken
out when the wreck's concept showed no landing). The builder's own change: the record's pull of 16.4 m/s/s followed the
old 220 m world's curve; on the Moon's own ground the cards fall at the Moon's 1.62 m/s/s (NASA's Moon fact sheet,
nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html), every sample of the loop still inside every footage check.
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

RECORD = ("f46ea0f27^", "data/effects/wreck.json")
MOON_PULL = 1.62
MOON_SOURCE = {"nasa-moon-factsheet": {
    "what": "NASA Goddard, Moon fact sheet", "url": "https://nssdc.gsfc.nasa.gov/planetary/factsheet/moonfact.html",
    "measured": "read: surface gravity 1.62 m/s/s"}}
ROOT = "/dust"
NAME = "landing_dust"


def carried():
    """The wreck record's landing dust emitter on the Moon's pull, its footage sources and its checks."""
    text = subprocess.run(["git", "-C", str(REPO), "show", ":".join(RECORD)], capture_output=True, text=True,
                          check=True).stdout
    wreck = json.loads(text)
    record = dict(next(entry for entry in wreck["effects"] if entry["name"] == NAME))
    record["gravity"] = [0.0, -MOON_PULL, 0.0]
    record["lift"] = float(record["placement"]["ground"][2])
    record["placement"] = {}
    record["from"] = (record["from"] + "; carried to the Moon's own ground, where its cards fall at 1.62 m/s/s "
                      "(nasa-moon-factsheet), not the old 220 m world's 16.4 (tools/props/moon_dust)")
    checks = [check for check in wreck["footage"]["checks"] if NAME in check["emitters"]]
    return record, dict(wreck["footage"]["sources"], **MOON_SOURCE), checks


def rise(spots, beyond):
    """How steeply the particles' middles stand over the flat ground beneath them against how far out from the engine
    they are (95th share, those more than `beyond` metres out), degrees (f46ea0f27^'s rise on a flat ground); None
    when none is that far out."""
    out = np.hypot(spots[:, 0], spots[:, 2])
    far = out > beyond
    if not far.any():
        return None
    return float(np.percentile(np.degrees(np.arctan2(spots[far, 1], out[far])), 95))


def sample_measure(check, spots, widths):
    """One check's measure of one sample's showing particles (over the ground under the engine)."""
    from score.stages.effects import loose
    if check["measure"] == "rise":
        return rise(spots, float(check.get("beyond", 1.0)))
    if check["measure"] == "loose":
        return loose(spots, widths)
    raise ValueError(f"no dust measure {check['measure']}")


def measures(record, checks, points, widths):
    """[(check name, least, most, range)] over every sample of the loop."""
    lift = np.array([0.0, record["lift"], 0.0])
    rows = []
    for check in checks:
        values = [sample_measure(check, spots[sizes > 0] + lift, sizes[sizes > 0])
                  for spots, sizes in zip(points, widths) if (sizes > 0).sum() > 1]
        values = [value for value in values if value is not None]
        rows.append((check["name"], min(values), max(values), list(check["range"])))
    return rows


def faults(rows):
    """Each check a sample's measure falls outside of, in words."""
    return [f"{name} {least:.3f} to {most:.3f}, outside {low} to {high}" for name, least, most, (low, high) in rows
            if least < low or most > high]


def written(out):
    """effect.usda, clip.usdc and settings.json of the landing dust written into <out>/landing_dust; the effect file.
    Refused (ValueError) when a sample of its loop misses a footage check."""
    out = pathlib.Path(out) / NAME
    out.mkdir(parents=True, exist_ok=True)
    record, sources, checks = carried()
    emitter = dict(record, origin=np.array([0.0, record["lift"], 0.0]), basis=np.eye(3))
    points, widths, _ = effects.bake(emitter)
    rows = measures(record, checks, points, widths)
    if faults(rows):
        raise ValueError(f"the landing dust misses its footage: {'; '.join(faults(rows))}")
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
        points_prim = stage.GetPrimAtPath(f"{ROOT}/{NAME}/{NAME}_points")
        Usd.ClipsAPI(points_prim).SetClipAssetPaths([Sdf.AssetPath("./clip.usdc")])
        layer.Save()
        shutil.copyfile(layer.realPath, out / "effect.usda")
        shutil.copyfile(pathlib.Path(work) / effects.ASSETS / f"{NAME}.usdc", out / "clip.usdc")
    settings = {"emitter": record, "carried_from": ":".join(RECORD), "sources": sources,
                "checks": [{"name": name, "measured": [least, most], "range": bounds}
                           for name, least, most, bounds in rows],
                "samples": len(points), "loop_seconds": effects.loop_of(emitter)}
    (out / "settings.json").write_text(json.dumps(settings, indent=1) + "\n")
    return out / "effect.usda"


if __name__ == "__main__":
    print(NAME, written(sys.argv[1]))
