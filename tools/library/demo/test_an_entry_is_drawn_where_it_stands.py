"""An entry's files prepared for the README pictures stand where the entry puts them: a kit piece's parts each its own
Z-up file with its own faces (Blender's reader cannot split them), and an effect's particles leave its model's spout
turned along the spout, Z-up; and a model whose parts are instanceable prims (every SimReady model) is read by the
studio as plain meshes where its stage puts them, so the camera frames the parts themselves (score #156: Blender's
default reader handed back the prototypes at their own place, and the fridge hovered while the electric panel left the
frame).

Breaks (each applied once, seen red, reverted), in pictures.py: z_up returning the points as they are (a Y-up piece
lies on its back: red); split_parts writing every face into each part (red); spout taking the farthest point of the whole
mesh, not of its upper half (the kettle's foot wins: red); steam_points leaving the jet unturned (red); in tools/blender/inside/library_demo.py, import_file dropping
`support_scene_instancing=False` (red).
"""
import pathlib
import sys
import types
from unittest import mock

import numpy
import pytest
from pxr import Gf, Usd, UsdGeom, Vt

HERE = pathlib.Path(__file__).resolve().parent
INSIDE = HERE.parents[2] / "tools/blender/inside"
sys.path.insert(0, str(HERE))
import pictures  # noqa: E402


def y_up_stage(path):
    stage = Usd.Stage.CreateNew(str(path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    return stage


def two_part_piece(folder):
    """Two quads, one a part each: a floor at y = 0 and a wall standing up to y = 2 at z = 1."""
    path = folder / "piece.usda"
    stage = y_up_stage(path)
    mesh = UsdGeom.Mesh.Define(stage, "/piece/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*point) for point in [
        (0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1), (0, 0, 1), (1, 0, 1), (1, 2, 1), (0, 2, 1)]]))
    mesh.CreateFaceVertexCountsAttr([4, 4])
    mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3, 4, 5, 6, 7])
    for name, faces in (("floor", [0]), ("wall", [1])):
        UsdGeom.Subset.CreateGeomSubset(mesh, name, UsdGeom.Tokens.face, Vt.IntArray(faces), "materialBind")
    stage.Save()
    return path


def read_ply(path):
    lines = path.read_text().splitlines()
    count = int(next(line for line in lines if line.startswith("element vertex")).split()[-1])
    start = lines.index("end_header") + 1
    return numpy.array([[float(value) for value in line.split()] for line in lines[start:start + count]]), \
        len(lines) - start - count


def kit_piece_parts(folder):
    """The wall part's top stands 2 m up (Z), the floor part lies at height 0; each holds one face."""
    pictures.split_parts(two_part_piece(folder), folder / "parts")
    wall, wall_faces = read_ply(folder / "parts" / "wall.ply")
    floor, floor_faces = read_ply(folder / "parts" / "floor.ply")
    return [round(wall[:, 2].max(), 3), round(floor[:, 2].max(), 3), wall_faces, floor_faces], [2.0, 0.0, 1, 1]


def kettle_and_jet(folder):
    """A kettle whose spout tip is at (0.25, 0.15, 0) in its upper half (its foot reaching farther from the middle, low
    down), and a jet of one particle 0.1 m along the clip's +z: it lands 0.1 m past the spout along +x, Z-up."""
    kettle = y_up_stage(folder / "kettle.usda")
    body = UsdGeom.Mesh.Define(kettle, "/kettle/geo")
    body.CreatePointsAttr(Vt.Vec3fArray([Gf.Vec3f(*point) for point in [
        (-0.1, 0, -0.1), (0.3, 0, 0), (0, 0.2, 0), (0.25, 0.15, 0), (0, 0.2, 0.1)]]))
    body.CreateFaceVertexCountsAttr([3, 3])
    body.CreateFaceVertexIndicesAttr([0, 1, 2, 2, 3, 4])
    kettle.Save()
    clip = y_up_stage(folder / "clip.usda")
    cloud = UsdGeom.Points.Define(clip, "/Effect")
    cloud.GetPointsAttr().Set(Vt.Vec3fArray([Gf.Vec3f(0, 0, 0.1)]), pictures.STEAM_TIME)
    cloud.GetWidthsAttr().Set(Vt.FloatArray([0.02]), pictures.STEAM_TIME)
    UsdGeom.PrimvarsAPI(cloud).CreatePrimvar("displayOpacity", Sdf_float()).Set(Vt.FloatArray([0.1]),
                                                                                  pictures.STEAM_TIME)
    clip.Save()
    out = pictures.steam_points(folder / "clip.usda", folder / "kettle.usda", folder / "steam.npz")
    placed = numpy.load(out)["points"][0]
    return [round(float(value), 3) for value in placed], [0.35, 0.0, 0.15]


def instanced_parts(folder):
    """A SimReady-shaped model: one instanceable part referencing its prototype, moved 1 m up. The studio's import asks
    Blender's USD reader for plain meshes (no scene instancing), the only reading in which the meshes it hands back to
    the framing stand where the stage puts them."""
    stage = Usd.Stage.CreateNew(str(folder / "model.usda"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.Mesh.Define(stage, "/Instances/part")
    part = UsdGeom.Xform.Define(stage, "/RootNode/part")
    part.GetPrim().GetReferences().AddInternalReference("/Instances/part")
    part.GetPrim().SetInstanceable(True)
    part.AddTranslateOp().Set(Gf.Vec3d(0, 0, 1))
    stage.Save()
    asked = []
    blender = types.ModuleType("bpy")
    blender.data = types.SimpleNamespace(objects=[])
    blender.ops = types.SimpleNamespace(wm=types.SimpleNamespace(usd_import=lambda **options: asked.append(options)))
    maths = types.ModuleType("mathutils")
    maths.Matrix = maths.Vector = None
    with mock.patch.dict(sys.modules, {"bpy": blender, "bmesh": types.ModuleType("bmesh"), "mathutils": maths}), \
            mock.patch.object(sys, "path", [str(INSIDE), *sys.path]):
        sys.modules.pop("library_demo", None)
        import library_demo
        library_demo.import_file(folder / "model.usda")
        sys.modules.pop("library_demo", None)
    return [stage.GetPrimAtPath("/RootNode/part").IsInstanceable(), asked[0].get("support_scene_instancing", True)], \
        [True, False]


def Sdf_float():
    from pxr import Sdf
    return Sdf.ValueTypeNames.FloatArray


@pytest.mark.parametrize("case", [kit_piece_parts, kettle_and_jet, instanced_parts], ids=lambda case: case.__name__)
def test_an_entry_is_drawn_where_it_stands(case, tmp_path):
    got, expected = case(tmp_path)
    assert got == expected
