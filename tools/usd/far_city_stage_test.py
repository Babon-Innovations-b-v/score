"""Check the far city's stage (tools/usd/far_city_stage.py) on towers made here: every tower of the plan stands as one
instance of its kind's model, its foot on the land and its top at the height the plan deals it, facing the ring's
middle; the land, the mountains and the harbour are painted with library surfaces and say which plain thing they are;
and a kind with no made model stops the stage rather than standing in for it.

Run: .venv/bin/python tools/usd/far_city_stage_test.py   (make tests runs it with the framework's environment)
"""
import math
import pathlib
import sys
import tempfile

import numpy as np
import trimesh
from pxr import Usd, UsdGeom, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import far_city  # noqa: E402
import far_city_stage  # noqa: E402


def made_towers(folder, kinds, skip=()):
    """A plain box for each kind, 2 m tall with its foot at -1, as a made model's file."""
    for kind in kinds:
        if kind not in skip:
            trimesh.creation.box(extents=(1.0, 2.0, 0.5)).export(folder / f"{kind}.glb")


def check_towers_stand_as_planned():
    city = far_city.plan(7)
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_towers(folder, city["uses"])
        path, counts = far_city_stage.write_stage(city, folder, folder / "stages")
        assert path == folder / "stages/far_city/far_city.usda"
        assert sum(counts.values()) == len(city["towers"]) and len(counts) == len(city["uses"])
        stage = Usd.Stage.Open(str(path))
        assert stage.GetDefaultPrim().GetName() == "far_city"
        instancer = UsdGeom.PointInstancer(stage.GetPrimAtPath("/far_city/Towers"))
        positions = np.array(instancer.GetPositionsAttr().Get())
        scales = np.array(instancer.GetScalesAttr().Get())
        assert len(positions) == len(city["towers"])
        first = city["towers"][0]
        assert math.isclose(scales[0][1] * 2.0, first["height"], rel_tol=1e-4)
        assert math.isclose(positions[0][1] - scales[0][1], far_city_stage.LAND_HIGH, abs_tol=1e-3)
        assert len(instancer.GetOrientationsAttr().Get()) == len(city["towers"])
        for name, plain in (("Land", "ground"), ("Mountains", "ground"), ("Harbour", "water")):
            prim = stage.GetPrimAtPath(f"/far_city/{name}")
            assert prim.GetAttribute("score:plain").Get() == plain
            material, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
            assert material, name


def check_windows_light_a_tower_s_sides_floor_by_floor():
    with tempfile.TemporaryDirectory() as temporary:
        model = pathlib.Path(temporary) / "tower.glb"
        trimesh.creation.box(bounds=((-10.0, 0.0, -10.0), (10.0, 60.0, 10.0))).export(model)
        windows = far_city_stage.window_lights(model, 7)
        assert windows["surface"] == far_city_stage.WINDOW_SURFACE
        count = len(windows["points"]) // 4
        bays = 4 * 20.0 * 60.0 / (far_city_stage.FLOOR * far_city_stage.BAY)
        assert 0.3 * bays < count < 0.6 * bays, (count, bays)
        middles = windows["points"].reshape(-1, 4, 3).mean(axis=1)
        floors = (middles[:, 1] / far_city_stage.FLOOR) - 0.5
        assert np.allclose(floors, np.round(floors), atol=1e-6)
        assert (np.abs(middles[:, [0, 2]]).max(axis=1) > 10.0).all(), "a window sits inside its tower"
        assert far_city_stage.made_kinds(pathlib.Path(temporary)) == set()


def check_a_kind_without_a_model_stops_the_stage():
    city = far_city.plan(7)
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_towers(folder, city["uses"], skip=("far_city_pencil_tower",))
        try:
            far_city_stage.write_stage(city, folder, folder / "stages")
        except SystemExit as stop:
            assert "far_city_pencil_tower" in str(stop)
        else:
            raise AssertionError("a city with a kind not made was written")


def check_tower_turn_faces_the_bearing():
    for facing in (0.0, 90.0, 213.0):
        turn = far_city_stage.tower_turn(facing)
        rotation = np.array(trimesh.transformations.quaternion_matrix(
            [float(turn.GetReal()), *map(float, turn.GetImaginary())]))[:3, :3]
        front = rotation @ np.array([0.0, 0.0, 1.0])
        look = np.array([math.sin(math.radians(facing)), 0.0, -math.cos(math.radians(facing))])
        assert np.allclose(front, look, atol=1e-2), (facing, front, look)


if __name__ == "__main__":
    check_tower_turn_faces_the_bearing()
    check_windows_light_a_tower_s_sides_floor_by_floor()
    check_a_kind_without_a_model_stops_the_stage()
    check_towers_stand_as_planned()
    print("far city stage: all checks passed")
