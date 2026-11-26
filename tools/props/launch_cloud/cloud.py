"""The 2099 prologue launch's cloud: the exhaust and steam the rocket's engines throw out of the pad at ignition, the
ground cloud rolling out sideways, its billows thrown up and the deluge's white steam round the pad's foot. Three
score_lib effect entries baked by the particle effects algorithm (tools/usd/effects.py), each played once from the
engines' light, its cards drawn with the billowing smoke flipbook (effect/smoke_billow, tools/props/smoke_card).

    .venv/bin/python tools/props/launch_cloud/cloud.py <out folder> <smoke_billow folder>

Writes <out>/<name>/ for ground_cloud, cloud_billows and deluge_steam, each effect.usda (its default prim /cloud: the
emitter standing at its root, the rocket's foot on the pad, y up), the clip.usdc it plays, settings.json (the record,
its footage, each check's measure) and the flipbook's two atlases (smoke_a.png, smoke_b.png) its cards draw.

The numbers are the launch's footage-measured cloud (score git e9e8cc813:data/effects/launch.json, `ground_cloud`,
`cloud_billows` and `deluge_steam` and its footage checks, retired 2026-10-21 with every old record), measured against
a Falcon Heavy of about 70 m: the engines light 1 s into the event and the rocket lifts 3 s later. The builder's own
changes, each for the pad's rocket (place/pad's `rocket`, 48 m high):
- every length, speed and slowing scaled by 48/70 (the footage's checks are in rocket heights), the noise's scale left
  as it was;
- round 2 (2026-11-26, the owner of the game's launch smoke: "this smoke ... is shit"; the footage's cloud is bright,
  lit white and billowing, the game drew faint grey dust cards): the cards are drawn with the smoke flipbook instead
  of the dust card's tint (`card` billow, the record's colour the smoke's own), each puff 1.3 times the record's size
  and 1.6 times as opaque, still inside every footage check: at 1.5 times the size the fineness check (the cloud's
  smallest billows 0.05 to 0.15 of its width, KSC-20190625-PH_CSH01_0013) read 0.052, past its 0.05, and 1.3 reads 0.045.
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
LIFT = 4.0            # the rocket lifts 4 s into the event (the engines light at 1 s), the record's motion
GROW = 1.3            # round 2: each puff's size against the record's (1.5 reads 0.052 on the fineness check, past its 0.05)
THICKEN = 1.6         # round 2: each puff's opacity against the record's
ROOT = "/cloud"
ATLASES = ("smoke_a.png", "smoke_b.png")
RECORD = "score git e9e8cc813:data/effects/launch.json"


def scaled(record):
    """A launch record's emitter scaled to the pad's rocket, its cards the smoke flipbook's, its puffs round 2's."""
    out = dict(record)
    shape = dict(record["emitter"])
    for key in ("radius", "inner", "height"):
        shape[key] = shape[key] * SCALE
    out["emitter"] = shape
    out["speed"] = [value * SCALE for value in record["speed"]]
    out["damping"] = [value * SCALE for value in record["damping"]]
    out["size"] = record["size"] * SCALE * GROW
    out["opacity"] = min(1.0, record["opacity"] * THICKEN)
    out["card"] = "billow"
    out["placement"] = {}
    out["lift"] = record["placement"]["ground"][2] * SCALE
    out["from"] = (record["from"].rstrip(")") + "; scaled to a 48 m rocket, its puffs drawn with the smoke flipbook "
                   "effect/smoke_billow (tools/props/launch_cloud))")
    return out


def records():
    """{name: the launch record's emitter, scaled} for the three cloud emitters, with the record's footage."""
    import subprocess
    text = subprocess.run(["git", "-C", str(REPO), "show", RECORD.split(" ", 2)[2]], capture_output=True, text=True,
                          check=True).stdout
    launch = json.loads(text)
    named = {entry["name"]: entry for entry in launch["effects"]}
    return ({name: scaled(named[name]) for name in ("ground_cloud", "cloud_billows", "deluge_steam")},
            launch["footage"])


def emitters(found):
    """{name: the emitter as the bake reads it}, each standing at its own height over the rocket's foot, upright."""
    return {name: dict(record, origin=np.array([0.0, record["lift"], 0.0]), basis=np.eye(3))
            for name, record in found.items()}


def at_second(record, points, widths, seconds):
    """The emitter's showing particles at a second of the event: spots and widths (none before it starts)."""
    first = float(record["once"][0])
    index = int(round((seconds - first) * effects.samples_of(record)))
    if index < 0 or index >= len(points):
        return np.zeros((0, 3)), np.zeros(0)
    showing = widths[index] > 0
    spots = points[index][showing] + np.array([0.0, record["lift"], 0.0])
    return spots, widths[index][showing]


def measure(check, spots, widths):
    """One footage check's measure of the cloud's particles, lengths in rocket heights."""
    from score.stages.effects import height, layering, loose, reach
    rest = np.zeros(3)
    if check == "reach":
        return reach(spots, widths, rest) / ROCKET
    if check == "height":
        return height(spots, widths, rest) / ROCKET
    if check == "fineness":
        return float(np.median(widths)) / (2 * reach(spots, widths, rest))
    if check == "layering":
        return layering(spots, widths, rest)
    if check == "loose":
        return loose(spots, widths)
    raise ValueError(f"no cloud measure {check}")


def cloud_checks(footage):
    """The footage's checks of the three emitters together (the cloud is all three)."""
    return [check for check in footage["checks"] if set(check["emitters"]) == {"ground_cloud", "cloud_billows",
                                                                               "deluge_steam"}]


def measured(found, baked, footage):
    """[(check, its measure, its range)] for every cloud check, the three emitters' particles together."""
    rows = []
    for check in cloud_checks(footage):
        seconds = LIFT + float(check["after_lift"])
        parts = [at_second(found[name], *baked[name][:2], seconds) for name in found]
        spots = np.concatenate([part[0] for part in parts])
        widths = np.concatenate([part[1] for part in parts])
        rows.append((check["name"], measure(check["measure"], spots, widths), list(check["range"])))
    return rows


def faults(rows):
    """Each check whose measure falls outside its range, in words."""
    return [f"{name} {value:.3f} outside {low} to {high}" for name, value, (low, high) in rows
            if not low <= value <= high]


def written_one(name, emitter, record, out, flipbook):
    """effect.usda, clip.usdc, the flipbook's atlases and settings.json of one emitter written into `out`."""
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
        root.CreateAttribute("score:effect:flipbook", Sdf.ValueTypeNames.AssetArray).Set(
            [Sdf.AssetPath(f"./{atlas}") for atlas in ATLASES])
        root.CreateAttribute("score:effect:flipbook_frames", Sdf.ValueTypeNames.Int).Set(flipbook["frames"])
        points_prim = stage.GetPrimAtPath(f"{ROOT}/{name}/{name}_points")
        Usd.ClipsAPI(points_prim).SetClipAssetPaths([Sdf.AssetPath("./clip.usdc")])
        layer.Save()
        shutil.copyfile(layer.realPath, out / "effect.usda")
        shutil.copyfile(pathlib.Path(work) / effects.ASSETS / f"{name}.usdc", out / "clip.usdc")
    for atlas in ATLASES:
        shutil.copyfile(flipbook["folder"] / atlas, out / atlas)
    return out / "effect.usda"


def baked_cloud():
    """The three emitters' records, the footage and each emitter's bake: (found, footage, {name: bake})."""
    found, footage = records()
    return found, footage, {name: effects.bake(emitter) for name, emitter in emitters(found).items()}


def written(out, flipbook_folder, cloud=None):
    """The three emitters baked (or `cloud`, baked_cloud's), checked together against the footage and written under
    `out`; {name: effect file}. Refused (ValueError) when the cloud misses any footage check."""
    out, flipbook_folder = pathlib.Path(out), pathlib.Path(flipbook_folder)
    flipbook = dict(json.loads((flipbook_folder / "surface.json").read_text())["atlas"], folder=flipbook_folder)
    found, footage, baked = cloud or baked_cloud()
    rows = measured(found, baked, footage)
    if faults(rows):
        raise ValueError(f"the launch cloud misses its footage: {'; '.join(faults(rows))}")
    paths = {}
    for name, emitter in emitters(found).items():
        paths[name] = written_one(name, emitter, found[name], out / name, flipbook)
        settings = {"emitter": found[name], "carried_from": RECORD, "sources": footage["sources"],
                    "licence": footage.get("licence"), "rocket_m": ROCKET, "lift_s": LIFT,
                    "checks": [{"name": check, "measured": value, "range": bounds} for check, value, bounds in rows],
                    "measured_together": sorted(found), "flipbook": "effect/smoke_billow",
                    "samples": len(baked[name][0]), "loop_seconds": effects.loop_of(emitter)}
        (out / name / "settings.json").write_text(json.dumps(settings, indent=1) + "\n")
    return paths


if __name__ == "__main__":
    for name, path in written(sys.argv[1], sys.argv[2]).items():
        print(name, path)
