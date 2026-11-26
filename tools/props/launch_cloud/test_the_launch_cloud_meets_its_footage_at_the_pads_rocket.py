"""Invariant: the launch's cloud (cloud.py) is three effect files, the ground cloud, its billows and the deluge's
steam, each with its default prim /cloud carrying its effect kind, naming the smoke flipbook's two atlases beside it and
playing its baked event from the clip beside it, and the three together meet every footage check of the launch in the
pad rocket's heights (reach and height at lift-off, 3 s and 12 s after, fine, thick and never loose); puffs grown past
the footage's finest billows are refused.

Breaks that turn it red:
- cloud.GROW: 1.6 -> the cloud's fineness 3 s after lift-off 0.055, past 0.05: refused
- cloud.written_one: the clip's asset path left as the bake wrote it (../assets/effects/<name>.usdc) -> no points play
- cloud.written_one: the flipbook's atlases not copied beside the effect -> its cards name files that are not there
"""
import json
import pathlib
import sys

import numpy as np
import pytest
from PIL import Image
from pxr import Usd, UsdGeom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cloud  # noqa: E402


def flipbook(folder):
    """A small stand-in flipbook folder: its record and two blank atlases (the pack is smoke_card's own test)."""
    folder.mkdir()
    (folder / "surface.json").write_text(json.dumps({"atlas": {"frames": 16}}))
    for atlas in cloud.ATLASES:
        Image.new("RGBA", (8, 8)).save(folder / atlas)
    return folder


def test_the_launch_cloud_meets_its_footage_at_the_pads_rocket(tmp_path):
    baked = cloud.baked_cloud()
    files = cloud.written(tmp_path / "out", flipbook(tmp_path / "book"), baked)
    for name, kind in (("ground_cloud", "exhaust_ground_cloud"), ("cloud_billows", "exhaust_ground_cloud"),
                       ("deluge_steam", "deluge_steam")):
        stage = Usd.Stage.Open(str(files[name]))
        root = stage.GetDefaultPrim()
        assert root.GetPath() == "/cloud" and root.GetAttribute("score:effect:kind").Get() == kind
        assert all((files[name].parent / atlas).exists() for atlas in cloud.ATLASES)
        assert [path.path for path in root.GetAttribute("score:effect:flipbook").Get()] == [
            f"./{atlas}" for atlas in cloud.ATLASES]
        first = float(baked[0][name]["once"][0]) * cloud.effects.RATE + 48.0
        spots = UsdGeom.Points(stage.GetPrimAtPath(f"/cloud/{name}/{name}_points")).GetPointsAttr().Get(first)
        assert spots is not None and len(spots) == baked[0][name]["count"]
    found, footage, bakes = baked
    grown = {name: (points, widths * 1.6 / cloud.GROW, opacity) for name, (points, widths, opacity) in bakes.items()}
    assert any("fine" in fault for fault in cloud.faults(cloud.measured(found, grown, footage)))
    with pytest.raises(ValueError, match="misses its footage"):
        cloud.written(tmp_path / "grown", tmp_path / "book", (found, footage, grown))
