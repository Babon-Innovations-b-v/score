"""The 2099 prologue's water effects the lay plans miss (2099 #161): the drips off a street awning's front edge in the
rain, and the white water a speedboat leaves on the harbour. Two score_lib effect entries baked by the particle
effects algorithm (tools/usd/effects.py), each played on a loop, measured against footage as tools/props/pad_vent's
venting is.

    .venv/bin/python tools/props/prologue_fx/fx.py <out folder>

Writes <out>/awning_drips/ and <out>/boat_wake/, each effect.usda (its default prim /effect: the emitter standing at
its root, y up), the clip.usdc it plays and settings.json (the record, its footage, each check's measure).

Awning drips. The drops are the size a pendant drop of water reaches before it pinches off, as the high-speed footage
of a drop dripping into still air measured it (arXiv 2003.07785: the critical volume 27.1 mm^3 filmed, 27.05 mm^3 by
the pendant-drop theory, a sphere 3.7 mm across; a wider outlet's drop holds up to about 0.05 ml, 4.6 mm). Each falls
from the edge nearly at rest and slows toward its end speed by the air's drag (Gunn and Kinzer 1949, J. Meteor. 6
243: 8.8 m/s for a 4 mm drop): over the awning's height h its speed is v_t sqrt(1 - exp(-2 g h / v_t^2)), 5.9 m/s
over 2.4 m, so the bake pulls each drop down by g less the steady slowing that reaches that speed over that fall, and
it dies on reaching the pavement. The builder's own choices: the edge 2 m long and 2.4 m over the pavement (a shop
awning's front edge over the street's 0.2 m pavement), the rain heavy (10 mm/h, the American Meteorological Society's
heavy rain from 7.6 mm/h) drained off an awning 1 m deep, so the edge lets 2 m x 1 m x 10 mm/h of water fall a second,
one drop of 27 mm^3 at a time; their spots along the edge are even, never the few fixed points a real edge drips from
(the game spreads copies under each awning).

Boat wake. A fast hull's wake narrows as its speed grows (Rabaud and Moisy 2013, Phys. Rev. Lett. 110 214503: wake
angles off airborne images, read from the line through the whitecaps and sun glitter, fall as 1/Fr past a hull
Froude number Fr = U / sqrt(g L) of about 0.5), the angle of its brightest waves 1 / (40^(1/4) sqrt(pi) Fr) radians
for a Gaussian hull (Darmon, Benzaquen and Raphael 2014, J. Fluid Mech. 738 R3), while nothing reaches past Kelvin's
19.47 degrees at any speed. The builder's own choices: the pad's speedboat (8 m long, 3 m wide) running at 15 m/s
(29 knots, planing), so Fr 1.69 and its whitecaps' angle 7.6 degrees; the boat is laid still, so the water and its
foam stream back past it at the boat's speed (the effect's +x, back from the transom), lying on the water.
"""
import json
import math
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

GRAVITY = 9.81
ROOT = "/effect"

# --- awning drips ---
EDGE_HALF = 1.0  # metres: half the edge's length
FALL_HIGH = 2.4  # metres from the edge to the pavement
DROP_VOLUME = 27.1e-9  # m^3, the filmed critical volume
DROP_WIDE = (6.0 * DROP_VOLUME / math.pi) ** (1.0 / 3.0)
END_SPEED = 8.8  # m/s, Gunn and Kinzer's for a 4 mm drop
FOOT_SPEED = END_SPEED * math.sqrt(1.0 - math.exp(-2.0 * GRAVITY * FALL_HIGH / END_SPEED ** 2))
PULL = FOOT_SPEED ** 2 / (2.0 * FALL_HIGH)  # m/s^2: the steady pull that reaches FOOT_SPEED over FALL_HIGH
# The seconds a drop lives: the game's particles step STEP at a time (velocity, then position), so a drop has fallen
# about PULL STEP^2 n (n + 1) / 2 after n steps; it lives the fewest whole steps that bring it down to the pavement.
STEPS = math.ceil((math.sqrt(1.0 + 8.0 * FALL_HIGH / (PULL * effects.STEP ** 2)) - 1.0) / 2.0)
FALL_SECONDS = STEPS * effects.STEP
RAIN = 10.0e-3 / 3600.0  # m/s of rain
AWNING_DEEP = 1.0  # metres
DRIPS_A_SECOND = RAIN * 2.0 * EDGE_HALF * AWNING_DEEP / DROP_VOLUME

# --- boat wake ---
BOAT_LONG, BOAT_WIDE, BOAT_SPEED = 8.0, 3.0, 15.0
FROUDE = BOAT_SPEED / math.sqrt(GRAVITY * BOAT_LONG)
BRIGHT_ANGLE = math.degrees(1.0 / (40.0 ** 0.25 * math.sqrt(math.pi) * FROUDE))
KELVIN = math.degrees(math.asin(1.0 / 3.0))
WAKE_SECONDS = 8.0

SOURCES = {
    "awning_drips": {
        "arXiv-2003.07785": {
            "what": "Short-term oscillation and falling dynamics for a water drop dripping in quiescent air "
                    "(high-speed footage of the drop's growth, pinch-off and fall)",
            "url": "https://arxiv.org/abs/2003.07785",
            "measured": "the critical volume at pinch-off 27.10 mm^3 filmed and simulated, 27.05 mm^3 by the "
                        "pendant-drop theory: a sphere 3.7 mm across"},
        "gunn-kinzer-1949": {
            "what": "Gunn and Kinzer, The terminal velocity of fall for water droplets in stagnant air, J. Meteor. 6, "
                    "243 (1949)",
            "url": "https://doi.org/10.1175/1520-0469(1949)006<0243:TTVOFF>2.0.CO;2",
            "measured": "a 4 mm drop's end speed 8.8 m/s"}},
    "boat_wake": {
        "rabaud-moisy-2013": {
            "what": "Rabaud and Moisy, Ship wakes: Kelvin or Mach angle?, Phys. Rev. Lett. 110, 214503 (2013), "
                    "wake angles measured on airborne images",
            "url": "https://arxiv.org/abs/1304.2653",
            "measured": "the wake angle read from the line through the whitecaps and sun glitter: Kelvin's 19.47 "
                        "degrees for a slow hull, falling as 1/Fr past Fr about 0.5"},
        "darmon-benzaquen-raphael-2014": {
            "what": "Darmon, Benzaquen and Raphael, Kelvin wake pattern at large Froude numbers, J. Fluid Mech. 738, "
                    "R3 (2014)",
            "url": "https://arxiv.org/abs/1309.6751",
            "measured": "the wake's edge stays at Kelvin's angle at every Froude number; the angle of its brightest "
                        "waves is 1 / (40^(1/4) sqrt(pi) Fr) for a Gaussian hull"}}}
LICENCE = "Published measurements only (papers cited by their numbers); no picture is copied."

DRIPS = {"name": "awning_drips", "kind": "awning_drips", "look": "speck", "placement": {},
         "emitter": {"shape": "box", "extents": [EDGE_HALF, 0.0, 0.005]},
         "count": int(round(DRIPS_A_SECOND * FALL_SECONDS)), "lifetime": FALL_SECONDS,
         "direction": [0.0, -1.0, 0.0], "spread": 0.0, "speed": [0.0, 0.0], "gravity": [0.0, -PULL, 0.0],
         "size": DROP_WIDE, "scale": [1.0, 1.0], "colour": "#cfd8e0", "opacity": 0.8,
         "opacity_over_life": [[0.0, 1.0], [1.0, 1.0]], "space": "world", "seed": 711,
         "from": "footage: arXiv-2003.07785 (a pendant drop pinching off at 27.1 mm^3, 3.7 mm across), "
                 "gunn-kinzer-1949 (its end speed 8.8 m/s); a 2 m awning edge 2.4 m over the pavement draining "
                 "heavy rain (tools/props/prologue_fx)"}
WAKE = {"name": "boat_wake", "kind": "boat_wake", "look": "puff", "card": "plain", "placement": {},
        "emitter": {"shape": "box", "extents": [0.2, 0.02, BOAT_WIDE / 2.0 * 0.8]},
        "count": 6000, "lifetime": WAKE_SECONDS, "direction": [1.0, 0.0, 0.0], "spread": BRIGHT_ANGLE * 1.15,
        "flatness": 1.0, "speed": [BOAT_SPEED * 0.97, BOAT_SPEED], "gravity": [0.0, 0.0, 0.0], "size": 1.2,
        "scale": [0.7, 1.4], "size_over_life": [[0.0, 0.6], [0.2, 1.4], [1.0, 3.0]], "colour": "#e8eef2",
        "opacity": 0.22, "opacity_over_life": [[0.0, 0.0], [0.04, 1.0], [0.5, 0.6], [1.0, 0.0]],
        "turbulence": {"strength": 0.3, "scale": 0.1, "influence": [0.005, 0.02]}, "near_fade": [1.0, 6.0],
        "space": "world", "seed": 712,
        "from": "footage: rabaud-moisy-2013 (airborne images: a fast hull's whitecaps narrow as 1/Fr), "
                "darmon-benzaquen-raphael-2014 (their angle 1 / (40^(1/4) sqrt(pi) Fr), never past Kelvin's 19.47 "
                "degrees); an 8 m speedboat at 15 m/s, Fr 1.69 (tools/props/prologue_fx)"}
RECORDS = {record["name"]: record for record in (DRIPS, WAKE)}
# The footage's checks: the drips' drop across (metres), how far they fall (metres) and stray from straight down; the
# wake's whitecaps' half angle (degrees, 95th share, from the transom) between the bright waves' and Kelvin's.
CHECKS = {"awning_drips": {"drop": (3.6e-3, 4.6e-3), "fall": (0.95 * FALL_HIGH, FALL_HIGH + 0.05),
                           "stray": (0.0, 0.02)},
          "boat_wake": {"angle": (BRIGHT_ANGLE, KELVIN), "loose": (0.0, 0.01)}}


def emitters():
    """{name: the emitter as the bake reads it}, each standing at its own root, upright."""
    return {name: dict(record, origin=np.zeros(3), basis=np.eye(3)) for name, record in RECORDS.items()}


def drip_measures(spots, sizes):
    """A sample's drips: (median drop across, the farthest fall under the edge, the farthest off the edge's plane)."""
    return (float(np.median(sizes)), float(-spots[:, 1].min()), float(np.abs(spots[:, 2]).max()))


def wake_measures(spots, sizes):
    """A sample's wake: (the whitecaps' half angle from the transom, 95th share, the loose share)."""
    from score.stages.effects import loose, spread
    return (spread(spots, np.zeros(3)), loose(spots, sizes))


def measures(name, points, widths):
    """{check: (least, most)} over every sample of the loop for the emitter `name`."""
    measure = drip_measures if name == "awning_drips" else wake_measures
    rows = np.asarray([measure(spots[sizes > 0], sizes[sizes > 0])
                       for spots, sizes in zip(points, widths) if (sizes > 0).sum() > 1])
    return {check: (float(rows[:, column].min()), float(rows[:, column].max()))
            for column, check in enumerate(CHECKS[name])}


def faults(name, found):
    """Each footage check of `name` a measure's least or most falls outside of, in words."""
    said = []
    for check, (low, high) in CHECKS[name].items():
        least, most = found[check]
        if least < low or most > high:
            said.append(f"{name} {check} {least:.4f} to {most:.4f}, outside {low:.4f} to {high:.4f}")
    return said


def written_one(name, emitter, out):
    """effect.usda, clip.usdc and settings.json of one emitter written into `out`; the effect file's path. Refused
    (ValueError) when its bake misses a footage check."""
    out.mkdir(parents=True, exist_ok=True)
    points, widths, _ = effects.bake(emitter)
    found = measures(name, points, widths)
    if faults(name, found):
        raise ValueError(f"the effect misses its footage: {'; '.join(faults(name, found))}")
    record = RECORDS[name]
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
    settings = {"emitter": record, "sources": SOURCES[name], "licence": LICENCE,
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
