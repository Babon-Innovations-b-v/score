"""Invariant: the pad's venting (vent.py) is two effect files, the liquid oxygen vent and the vapour round the foot,
each with its default prim /vent carrying its effect kind and playing its baked loop from the clip beside it, and
every sample of each loop meets the launch footage's checks in the pad rocket's heights: the vent's cloud 0.1 to 0.45
of a height long and 10 to 40 degrees either side near the vent, the foot's vapour reaching 0.15 to 0.6 out and 0.25
to 0.6 high, at most a hundredth of either loose.

Breaks that turn it red:
- vent.FOOT_LIFT: 0, the ring's middle on the foot (the measures read from the ring) -> height 0.11, under 0.25
- vent.written_one: the clip's asset path left as the bake wrote it (../assets/effects/<name>.usdc) -> no points play
- vent.written_one: the root's score:effect:kind left out -> the default prim is no effect
"""
import pathlib
import sys

import numpy as np
from pxr import Usd, UsdGeom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import vent  # noqa: E402


def test_the_venting_meets_its_footage_at_the_pads_rocket(tmp_path):
    files = vent.written(tmp_path)
    for name, kind, count in (("lox_vent", "cryogenic_vent", 20000), ("foot_vapour", "cryogenic_vent_foot", 16000)):
        stage = Usd.Stage.Open(str(files[name]))
        root = stage.GetDefaultPrim()
        assert root.GetPath() == "/vent" and root.GetAttribute("score:effect:kind").Get() == kind
        spots = np.asarray(UsdGeom.Points(stage.GetPrimAtPath(f"/vent/{name}/{name}_points")).GetPointsAttr().Get(48.0))
        assert spots.shape == (count, 3)
        found = vent.measures(name, *vent.effects.bake(vent.emitters()[name])[:2])
        assert not vent.faults(name, found)
