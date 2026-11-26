"""Invariant: the launch's exhaust (exhaust.py) is four effect files, the flame's white core, the orange flame, the
fire on the pad and the plume, each with its default prim /exhaust carrying its effect kind and playing its baked
particles from the clip beside it, the plume's cards naming the smoke flipbook's atlases beside it and its particles
let out where the climbing rocket stood; every sample of each flame's loop reaches as far under the engines as the
footage measured, in the pad rocket's heights (the flame 0.45 to 1, its core 0.1 to 0.35); a flame too long is refused.

Breaks that turn it red:
- exhaust.scaled: the speeds left at the 70 m rocket's -> the core reaches 0.35 and more of the 48 m rocket: refused
- exhaust.scaled: no climb on the plume -> its particles stay on the pad as the rocket climbs
- exhaust.written_one: the clip's asset path left as the bake wrote it (../assets/effects/<name>.usdc) -> no points play
"""
import json
import pathlib
import sys

import numpy as np
import pytest
from PIL import Image
from pxr import Usd, UsdGeom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import exhaust  # noqa: E402


def test_the_flames_reach_as_far_under_the_pads_rocket_as_the_footage(tmp_path):
    book = tmp_path / "book"
    book.mkdir()
    for atlas in exhaust.ATLASES:
        Image.new("RGBA", (8, 8)).save(book / atlas)
    baked = exhaust.baked_exhaust()
    files = exhaust.written(tmp_path / "out", book, baked)
    for name, kind in (("flame_core", "rocket_flame"), ("flame", "rocket_flame"), ("pad_fire", "exhaust_on_the_pad"),
                       ("plume", "exhaust_trail")):
        stage = Usd.Stage.Open(str(files[name]))
        root = stage.GetDefaultPrim()
        assert root.GetPath() == "/exhaust" and root.GetAttribute("score:effect:kind").Get() == kind
        assert stage.GetPrimAtPath(f"/exhaust/{name}/{name}_points").IsValid()
        assert root.HasAttribute("score:effect:flipbook") == (name == "plume")
    found, footage, bakes = baked
    points, widths, _ = bakes["plume"]
    late = points[-60][widths[-60] > 0]
    assert float(np.percentile(late[:, 1], 95)) > 2 * exhaust.ROCKET  # let out up the climb, far over the pad
    settings = json.loads((files["flame_core"].parent / "settings.json").read_text())
    assert settings["checks"][0]["name"] == "flame core 3 s after lift-off"
    longer = dict(bakes, flame_core=(bakes["flame_core"][0] * 1.6, *bakes["flame_core"][1:]))
    with pytest.raises(ValueError, match="flame core"):
        exhaust.written(tmp_path / "long", book, (found, footage, longer))
