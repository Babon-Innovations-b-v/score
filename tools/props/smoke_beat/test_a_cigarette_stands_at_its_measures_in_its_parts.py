"""Invariant: the code-built cigarette (cigarette.py) is one closed round solid with its faces turned out, 84 mm long
and 7.9 mm across along +z from the mouth end at the origin, its faces in four parts: the filter its first 23.5 mm,
the paper to the burn line, the ember a 1.5 mm glowing band, the ash the last 2.5 mm; each part bound to a look named
after it in its library surface (`score:surface`, its colour), and the GLB the same part as a mesh of its own in that
finish (the ember alone glowing).

Breaks that turn it red:
- cigarette.solid: the mouth cap's winding flipped -> the solid is not watertight with its faces turned out
- cigarette.rings: the filter ring at FILTER / 2 -> the filter part ends at 11.75 mm
- cigarette.usd_written: the ash subset left out -> the parts are filter, paper and ember only
- cigarette.usd_written: the look's binding left out -> a part is bound to no material
- cigarette.look: the surface mark left out -> the part's look names no library surface
- cigarette.finish: glow not taken from the recipe -> the ember gives off nothing
- cigarette.glb_written: one mesh for the whole solid -> the GLB has no mesh named after the part
"""
import sys
import pathlib

import numpy as np
import pytest
import trimesh
from pxr import Usd, UsdGeom, UsdShade

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import cigarette  # noqa: E402


@pytest.mark.parametrize("part, low, high, glows", [("filter", 0.0, 0.0235, False), ("paper", 0.0235, 0.08, False),
                                                    ("ember", 0.08, 0.0815, True), ("ash", 0.0815, 0.084, False)])
def test_a_cigarette_stands_at_its_measures_in_its_parts(tmp_path, part, low, high, glows):
    stage = Usd.Stage.Open(str(cigarette.written(tmp_path)))
    mesh = UsdGeom.Mesh(stage.GetPrimAtPath("/cigarette/cigarette"))
    points = np.asarray(mesh.GetPointsAttr().Get(), dtype=np.float64)
    faces = np.asarray(mesh.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
    solid = trimesh.Trimesh(points, faces, process=True)
    assert solid.is_watertight and solid.is_winding_consistent and solid.volume > 0
    assert np.allclose(solid.bounds, [[-0.00395, -0.00395, 0.0], [0.00395, 0.00395, 0.084]], atol=1e-6)
    subsets = {subset.GetPrim().GetName(): np.asarray(subset.GetIndicesAttr().Get())
               for subset in UsdGeom.Subset.GetAllGeomSubsets(mesh)}
    assert sorted(subsets) == ["ash", "ember", "filter", "paper"] and sum(map(len, subsets.values())) == len(faces)
    bound = UsdShade.MaterialBindingAPI(stage.GetPrimAtPath(f"/cigarette/cigarette/{part}")).ComputeBoundMaterial()[0]
    assert bound and bound.GetPrim().GetName() == part
    assert bound.GetPrim().GetAttribute("score:surface").Get() == cigarette.FINISHES[part][0]
    shader = bound.ComputeSurfaceSource()[0]
    assert (max(shader.GetInput("emissiveColor").Get()) > 0) == glows
    heights = points[faces[subsets[part]]][:, :, 2]
    assert np.isclose(heights.min(), low, atol=1e-7) and np.isclose(heights.max(), high, atol=1e-7)
    drawn = trimesh.load(tmp_path / "cigarette.glb").geometry[part]
    assert np.isclose(drawn.bounds[0, 2], low, atol=1e-7) and np.isclose(drawn.bounds[1, 2], high, atol=1e-7)
    assert (drawn.visual.material.emissiveFactor is not None) == glows
