"""A groom written by basis_curves.py reads back as the strands it was given, or the file is refused.

The fixture is three strands (3, 4 and 2 points) at the bind and at two clip frames, the second strand a guide. Each
break below turns a row red:

- the prim is not a linear BasisCurves at /Groom/Hair, the default prim, Z up, in metres;
- a strand's point count, a point, a width (twice the radius, per point) or the constant colour is not the given one;
- `groom_root_uv` or `groom_guide` is not one per strand (uniform) with the given values, named as Unreal's groom
  schema names them;
- the bind is not the points' default value, or a clip frame is not a time sample at its frame number;
- arrays that disagree (more radii than points, a root UV short) or a clip frame with other strands than the bind's
  (a strand's count or root UV changed) are written instead of refused by name.
"""
import pathlib
import sys

import numpy as np
import pytest
from pxr import Usd, UsdGeom

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import basis_curves  # noqa: E402

COUNTS = np.array([3, 4, 2])
COLOUR = [0.144, 0.08, 0.04]


def strands(shift=0.0, **changed):
    made = {"counts": COUNTS.copy(), "points": np.arange(27, dtype=float).reshape(9, 3) / 100 + shift,
            "radius": np.linspace(0.0001, 0.00003, 9), "root_uv": np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]),
            "guide": np.array([0, 1, 0])}
    made.update(changed)
    return made


def frames(clip=None):
    made = [strands(), strands(0.01), clip or strands(0.02)]
    return [(name, time, one) for (name, time), one in zip(basis_curves.timed(["bind", "0", "7"]), made)]


@pytest.mark.parametrize("case, given, refused", [
    ("bind and two clip frames", frames(), None),
    ("more radii than points", [("bind", None, strands(radius=np.ones(10)))], "10 radii"),
    ("a root uv short", [("bind", None, strands(root_uv=np.zeros((2, 2))))], "2 root uvs"),
    ("a clip frame of other strands", frames(strands(0.02, counts=np.array([4, 3, 2]))), "not the same strands"),
    ("a clip frame with moved roots", frames(strands(0.02, root_uv=np.zeros((3, 2)))), "not the same strands"),
])
def test_a_groom_reads_back_strand_for_strand_or_is_refused(tmp_path, case, given, refused):
    path = tmp_path / "groom.usda"
    if refused:
        with pytest.raises(ValueError, match=refused):
            basis_curves.checked([(name, made) for name, _, made in given])
        return
    basis_curves.checked([(name, made) for name, _, made in given])
    basis_curves.written(path, given, COLOUR, 30.0)
    stage = Usd.Stage.Open(str(path))
    assert stage.GetDefaultPrim().GetPath() == "/Groom"
    assert UsdGeom.GetStageUpAxis(stage) == UsdGeom.Tokens.z and UsdGeom.GetStageMetersPerUnit(stage) == 1.0
    hair = UsdGeom.BasisCurves(stage.GetPrimAtPath("/Groom/Hair"))
    assert hair and hair.GetTypeAttr().Get() == UsdGeom.Tokens.linear
    assert list(hair.GetCurveVertexCountsAttr().Get()) == list(COUNTS)
    assert hair.GetWidthsInterpolation() == UsdGeom.Tokens.vertex
    assert np.allclose(np.array(hair.GetWidthsAttr().Get()), 2 * given[0][2]["radius"])
    assert np.allclose(np.array(hair.GetDisplayColorPrimvar().Get()[0]), COLOUR)
    primvars = UsdGeom.PrimvarsAPI(hair)
    for name, expected in (("groom_root_uv", given[0][2]["root_uv"]), ("groom_guide", given[0][2]["guide"])):
        primvar = primvars.GetPrimvar(name)
        assert primvar.GetInterpolation() == UsdGeom.Tokens.uniform
        assert np.allclose(np.array(primvar.Get()), expected)
    points = hair.GetPointsAttr()
    assert points.GetTimeSamples() == [0.0, 7.0]
    assert np.allclose(np.array(points.Get(Usd.TimeCode.Default())), given[0][2]["points"])
    for _, time, made in given[1:]:
        assert np.allclose(np.array(points.Get(time)), made["points"])
