"""part_looks: each face of a remade model wears the library surface of the part its old builder laid in that place,
the glowing parts' faces taken from the glow file, and a model whose triangles lie off its rebuild, or number other
than it, is refused, never guessed.

Breaks (each applied once, seen red, reverted), in part_looks.py: parts_by_order without the glowing parts put after
the rest (the glow case's faces wear the wrong parts); TOLERANCE raised to 0.01 (the 1 mm case is made, not refused);
refinished binding every subset to the first look (a face wears another part's surface); refinished leaving the baked
look and `st` on (the atlas is still there).
"""
import json
import pathlib
import sys

import numpy as np
import pytest
from pxr import Sdf, Usd, UsdGeom, UsdShade

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import part_looks  # noqa: E402

SPECS = {name: {"recipe": recipe, "colour": colour, "hex": "#808080", "roughness": 0.4, "metal": 0.0, "wear": 0.4,
                "dirt": 0.4}
         for name, recipe, colour in (("dark_panel", "painted_metal", [0.02, 0.03, 0.03]),
                                      ("bare_steel", "bare_metal", [0.3, 0.3, 0.4]),
                                      ("led_amber", "glowing", [1.0, 0.4, 0.05]))}
SURFACES = {"painted_metal": "surface/painted_metal@1", "bare_metal": "surface/bare_metal@1",
            "glowing": "surface/glowing@1"}
PARTS = [["flange", "dark_panel"], ["dome", "led_amber"], ["body", "bare_steel"]]


def baked(folder, name, triangles):
    """A baked model file as the old bake wrote it: one triangle mesh with st, bound to one atlas look."""
    stage = Usd.Stage.CreateNew(str(folder / f"{name}.usda"))
    root = UsdGeom.Xform.Define(stage, f"/{name}")
    stage.SetDefaultPrim(root.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, f"/{name}/geo")
    mesh.CreatePointsAttr([tuple(corner) for triangle in triangles for corner in triangle])
    mesh.CreateFaceVertexCountsAttr([3] * len(triangles))
    mesh.CreateFaceVertexIndicesAttr(list(range(3 * len(triangles))))
    UsdGeom.PrimvarsAPI(mesh.GetPrim()).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.vertex)
    look = UsdShade.Material.Define(stage, f"/{name}/Looks/baked")
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).Bind(look)
    return stage


def triangle_at(x):
    return [[x, 0.0, 0.0], [x + 0.1, 0.0, 0.0], [x, 0.1, 0.0]]


# Built in the old join's order: flange, dome (glowing), body, flange again.
BUILT_ORDER = [0, 1, 2, 0]
BUILT = [triangle_at(x) for x in (0.0, 1.0, 2.0, 3.0)]
# The model's files: the rest in order, then the glowing ones in the glow file.
MODEL = [BUILT[0], BUILT[2], BUILT[3]]
GLOW = [BUILT[1]]


@pytest.mark.parametrize("case, shift, glow, wanted", [
    ("exact", 0.0, True, [["flange", "body", "flange"], ["dome"]]),
    ("off by 0.05 mm, within", 5e-5, True, [["flange", "body", "flange"], ["dome"]]),
    ("off by 1 mm", 1e-3, True, "lie off"),
    ("no glow file for a glowing part", 0.0, False, "triangles"),
])
def test_each_face_wears_the_surface_of_the_part_built_in_its_place(tmp_path, case, shift, glow, wanted):
    model = [[[value + (shift if axis == 1 else 0.0) for axis, value in enumerate(corner)] for corner in triangle]
             for triangle in MODEL]
    stages = [baked(tmp_path, "model", model)] + ([baked(tmp_path, "model_glow", GLOW)] if glow else [])
    counts = [len(part_looks.mesh_of(stage).GetFaceVertexCountsAttr().Get()) for stage in stages]
    points = np.vstack([part_looks.triangle_middles(part_looks.mesh_of(stage)) for stage in stages])
    answer = {"parts": PARTS, "order": BUILT_ORDER,
              "middles": [np.mean(triangle, axis=0).tolist() for triangle in BUILT]}
    if isinstance(wanted, str):
        with pytest.raises(part_looks.Refused, match=wanted):
            part_looks.parts_by_order(answer, counts, lambda surface: surface == "led_amber", points)
        return
    by_file, _ = part_looks.parts_by_order(answer, counts, lambda surface: surface == "led_amber", points)
    worn = []
    for stage, faces in zip(stages, by_file):
        part_looks.refinished(stage, [tuple(part) for part in PARTS], faces, SPECS, SURFACES)
        mesh = part_looks.mesh_of(stage)
        assert not stage.GetPrimAtPath(stage.GetDefaultPrim().GetPath().AppendPath("Looks/baked")), case
        assert not UsdGeom.PrimvarsAPI(mesh.GetPrim()).HasPrimvar("st"), case
        shown = [None] * len(mesh.GetFaceVertexCountsAttr().Get())
        for subset in UsdShade.MaterialBindingAPI(mesh.GetPrim()).GetMaterialBindSubsets():
            look = UsdShade.MaterialBindingAPI(subset.GetPrim()).GetDirectBinding().GetMaterial()
            surface = look.GetPrim().GetAttribute("score:surface").Get()
            variant = look.GetPrim().GetAttribute("score:surface:variant").Get()
            assert surface == SURFACES[SPECS[variant]["recipe"]], case
            assert json.loads(look.GetPrim().GetAttribute("score:recipe:spec").Get())["recipe"] == \
                SPECS[variant]["recipe"], case
            for face in subset.GetIndicesAttr().Get():
                shown[face] = (subset.GetPrim().GetName(), variant)
        worn.append([part for part, _ in shown])
        assert all(variant == dict(map(tuple, PARTS))[part] for part, variant in shown), case
    assert worn == wanted, case
