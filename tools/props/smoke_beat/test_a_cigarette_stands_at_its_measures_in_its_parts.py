"""Invariant: the code-built cigarette (cigarette.py) is one closed round solid with its faces turned out, 84 mm long
and 7.9 mm across along +z from the mouth end at the origin, its faces in three parts: the filter its first 23.5 mm,
the lit end its last 2 mm, the paper between, each part bound to a material named after it (so any USD reader
splits them, #156).

Breaks that turn it red:
- cigarette.solid: the mouth cap's winding flipped -> the solid is not watertight with its faces turned out
- cigarette.rings: the filter ring at FILTER / 2 -> the filter part ends at 11.75 mm
- cigarette.written: the ember subset left out -> the parts are filter and paper only
- cigarette.written: the placeholder binding left out -> a part is bound to no material
"""
import sys
import pathlib

import numpy as np
import pytest
import trimesh
from pxr import Usd, UsdGeom, UsdShade

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cigarette  # noqa: E402


@pytest.mark.parametrize("part, low, high", [("filter", 0.0, 0.0235), ("paper", 0.0235, 0.082),
                                             ("ember", 0.082, 0.084)])
def test_a_cigarette_stands_at_its_measures_in_its_parts(tmp_path, part, low, high):
    stage = Usd.Stage.Open(str(cigarette.written(tmp_path)))
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/cigarette/cigarette"))
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    faces = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    solid = trimesh.Trimesh(points, faces, process=True)
    assert solid.is_watertight and solid.is_winding_consistent and solid.volume > 0
    assert np.allclose(solid.bounds, [[-0.00395, -0.00395, 0.0], [0.00395, 0.00395, 0.084]], atol=1e-6)
    subsets = {subset.GetPrim().GetName(): np.asarray(subset.GetIndicesAttr().Get())
               for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh)}
    assert sorted(subsets) == ["ember", "filter", "paper"] and sum(map(len, subsets.values())) == len(faces)
    bound = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath(f"/cigarette/cigarette/{part}")).ComputeBoundMaterial()[0]
    assert bound and bound.GetPrim().GetName() == part
    heights = points[faces[subsets[part]]][:, :, 2]
    assert np.isclose(heights.min(), low, atol=1e-7) and np.isclose(heights.max(), high, atol=1e-7)
