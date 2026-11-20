"""Invariant: the cigarette's wisp (wisp.py) is one effect file whose default prim /smoke carries its effect kind and
plays the baked loop from the clip beside it (3,000 particles at any time, rising off the lit end at the origin), and
every sample of the loop meets the footage's checks: at least 22 cm high, 15 to 35 degrees half angle, at most a
hundredth of its particles loose.

Breaks that turn it red:
- wisp.WISP: the launch cone back to the flat's 20 degrees -> written refuses it (half angle 35.9 over 35)
- wisp.written: the clip's asset path left as the bake wrote it (../assets/effects/wisp.usdc) -> no points play
- wisp.written: the root's score:effect:kind left out -> the default prim is no effect
"""
import pathlib
import sys

import numpy as np
from pxr import Usd, UsdGeom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wisp  # noqa: E402


def test_the_wisp_rises_off_its_lit_end_as_its_footage_measured_it(tmp_path):
    stage = Usd.Stage.Open(str(wisp.written(tmp_path)))
    root = stage.GetDefaultPrim()
    assert root.GetPath() == "/smoke" and root.GetAttribute("score:effect:kind").Get() == "smoke_wisp"
    points = UsdGeom.Points(stage.GetPrimAtPath("/smoke/wisp/wisp_points"))
    spots = np.asarray(points.GetPointsAttr().Get(48.0))
    assert spots.shape == (3000, 3) and np.percentile(spots[:, 1], 95) > 0.2
    settings = (tmp_path / "settings.json").read_text()
    found = wisp.measures(*wisp.effects.bake(wisp.emitter())[:2])
    assert not wisp.faults(found) and '"spread": 16.0' in settings
