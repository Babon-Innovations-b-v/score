"""Check the far city's plan (tools/usd/far_city.py) without Blender: the same seed lays the same city and another seed
another, hundreds of towers stand as a wall rows deep behind the shore with no two feet overlapping, each turned to
the ring's middle within its jitter, of the kinds the data names, taller in the business districts; the mountains
rise from their foot behind the shore; and each backdrop arc's strip covers exactly the arc's bearings and its
height on the ring, in the arc's own proportions.

Run: .venv/bin/python tools/usd/far_city_test.py   (make tests runs it with the framework's environment)
"""
import json
import math
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import far_city  # noqa: E402


def check_layout():
    towers = far_city.lay_towers(7)
    assert towers == far_city.lay_towers(7)
    assert towers != far_city.lay_towers(8)
    assert len(towers) > 500, len(towers)
    names = {kind["row"] for kind in far_city.kinds()}
    assert {tower["kind"] for tower in towers} == names
    spots = np.array([tower["at"] for tower in towers])
    radii = np.array([tower["radius"] for tower in towers])
    for index in range(len(towers)):
        gaps = np.linalg.norm(spots[index + 1:] - spots[index], axis=1)
        assert (gaps >= radii[index + 1:] + radii[index] - 0.02).all(), towers[index]
    for tower in towers:
        x, z = tower["at"]
        bearing = math.degrees(math.atan2(x, -z)) % 360.0
        assert math.hypot(x, z) >= far_city.shore_distance(bearing, 7) + far_city.FIRST_ROW - 0.3 * far_city.ROW_DEEP
        toward_middle = (bearing + 180.0) % 360.0
        assert abs((tower["facing"] - toward_middle + 180.0) % 360.0 - 180.0) <= far_city.TURN_JITTER + 1e-6
    office = [tower["height"] for tower in towers if far_city.district(
        math.degrees(math.atan2(tower["at"][0], -tower["at"][1])) % 360.0) > 0.5]
    plain = [tower["height"] for tower in towers if far_city.district(
        math.degrees(math.atan2(tower["at"][0], -tower["at"][1])) % 360.0) < 0.05]
    assert np.mean(office) > 1.3 * np.mean(plain), (np.mean(office), np.mean(plain))


def check_mountains():
    mountains = far_city.mountains(7)
    heights = np.array(mountains["heights"])
    assert heights.shape == (len(mountains["reaches"]), len(mountains["bearings"]))
    assert (heights[0] == 0.0).all() and heights.min() >= 0.0
    assert far_city.MOUNTAIN_LOW * 0.8 < heights.max() < far_city.MOUNTAIN_HIGH * 1.2
    assert mountains["reaches"][0] == far_city.MOUNTAIN_BEHIND


def check_strips():
    arcs = json.loads((far_city.SCENES / "launch.json").read_text())["backdrop"]
    for arc, strip in zip(arcs, far_city.strips(arcs)):
        assert strip["name"] == arc["name"]
        assert math.isclose(strip["middle"] - math.degrees(strip["half"]), arc["from"])
        assert math.isclose(strip["middle"] + math.degrees(strip["half"]), arc["from"] + arc["span"])
        tall = arc["high"] - arc["low"]
        assert math.isclose((strip["v_high"] - strip["v_low"]) * arc["radius"], tall)
        assert math.isclose(strip["v_low"] * arc["radius"], -far_city.EYE)
        across = arc["radius"] * math.radians(arc["span"])
        assert abs(strip["width"] / strip["height"] - across / tall) < 0.01


def main():
    check_layout()
    check_mountains()
    check_strips()
    print("far_city_test: ok")


if __name__ == "__main__":
    main()
