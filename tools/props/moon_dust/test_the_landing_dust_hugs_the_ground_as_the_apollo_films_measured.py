"""Invariant: the Moon's landing dust (dust.py) is one effect file, its default prim /dust carrying its effect kind and
playing its baked loop from the clip beside it, its cards falling at the Moon's pull, and every sample of the loop
meets the Apollo films' checks: the sheet 1 to 3 degrees over the ground beyond 5 m and at most a hundredth of its
cards loose; a sheet let out higher over the ground is refused.

Breaks that turn it red:
- dust.carried: the emitter's lift 1 m over the ground, not the record's 0.15 -> the sheet stands past 3 degrees: refused
- dust.written: the clip's asset path left as the bake wrote it (../assets/effects/landing_dust.usdc) -> no points play
- dust.MOON_PULL: 16.4, the old world's -> the gravity written is not the Moon's
"""
import json
import pathlib
import sys

import numpy as np
import pytest
from pxr import Usd, UsdGeom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import dust  # noqa: E402


def test_the_landing_dust_hugs_the_ground_as_the_apollo_films_measured(tmp_path, monkeypatch):
    path = dust.written(tmp_path / "moon")
    stage = Usd.Stage.Open(str(path))
    root = stage.GetDefaultPrim()
    assert root.GetPath() == "/dust" and root.GetAttribute("score:effect:kind").Get() == "landing_dust_veil"
    spots = UsdGeom.Points(stage.GetPrimAtPath("/dust/landing_dust/landing_dust_points")).GetPointsAttr().Get(12.0)
    assert spots is not None and len(spots) == 30000
    settings = json.loads((path.parent / "settings.json").read_text())
    assert np.allclose(settings["emitter"]["gravity"], [0.0, -1.62, 0.0])
    carried = dust.carried

    def lifted():
        record, sources, checks = carried()
        return dict(record, lift=1.0), sources, checks

    monkeypatch.setattr(dust, "carried", lifted)
    with pytest.raises(ValueError, match="rise over the ground"):
        dust.written(tmp_path / "high")
