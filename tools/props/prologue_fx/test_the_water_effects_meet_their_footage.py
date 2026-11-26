"""Invariant: the prologue's water effects (fx.py) are two effect files, the awning's drips and the speedboat's wake,
each with its default prim /effect carrying its effect kind and playing its baked loop from the clip beside it, and
every sample of each loop meets its footage's checks: the drips 3.6 to 4.6 mm across, falling the awning's 2.4 m to
the pavement and no further than 5 cm past it, straight down within 2 cm; the wake's whitecaps between the bright
waves' angle at the boat's Froude number (7.6 degrees) and Kelvin's 19.47 degrees, at most a hundredth loose.

Breaks that turn it red:
- fx.STEPS: math.floor in place of math.ceil -> the drips die 2.23 m down, short of the pavement
- fx.WAKE: spread BRIGHT_ANGLE * 0.5 -> the whitecaps' angle under the bright waves'
- fx.written_one: the clip's asset path left as the bake wrote it (../assets/effects/<name>.usdc) -> no points play
"""
import pathlib
import sys

import numpy as np
from pxr import Usd, UsdGeom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import fx  # noqa: E402


def test_the_water_effects_meet_their_footage(tmp_path):
    files = fx.written(tmp_path)
    for name in ("awning_drips", "boat_wake"):
        stage = Usd.Stage.Open(str(files[name]))
        root = stage.GetDefaultPrim()
        assert root.GetPath() == "/effect" and root.GetAttribute("score:effect:kind").Get() == fx.RECORDS[name]["kind"]
        spots = np.asarray(UsdGeom.Points(stage.GetPrimAtPath(f"/effect/{name}/{name}_points")).GetPointsAttr().Get(48.0))
        assert spots.shape == (fx.RECORDS[name]["count"], 3)
        assert not fx.faults(name, fx.measures(name, *fx.effects.bake(fx.emitters()[name])[:2]))
