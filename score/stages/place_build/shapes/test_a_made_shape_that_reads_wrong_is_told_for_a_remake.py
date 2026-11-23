"""Invariant: a made shape that reads wrong is told for a remake, by object: a crop-built pipe whose section swells
along its run is `a sausage` while a straight one, or one whose section swells as much as NVIDIA's socketed grey
pipe, passes; a picture-made console of bumps with no flat face is
`a lump` while a box console passes; the same bumps as a library kit, or as a made seat, are not judged.

Breaks that turn this red (each applied once and seen red, then reverted):
- shapes.made: CROP_WORDS left out -> the crop-built sausage pipe is not judged
- shapes.section: the run's widths read at the run's ends too (SWELL_SPAN made 1.0) -> the straight pipe swells at
  its flanges
- shapes.shape_faults: the swell rule left out -> the sausage passes
- shapes.SWELL back at 0.05 -> the socketed pipe (its swell 0.069, NVIDIA's grey pipe's 0.066) is a sausage
- shapes.flat_share: every direction counted (FULLEST made DIRECTIONS) -> the lumpy console passes
- shapes.faults: `made` unread -> the library kit's lump is told
"""
import json

import numpy as np
import pytest
from pxr import Sdf, Usd, UsdGeom, Vt

from score.stages.place_build import finished, shapes

CROP = [("score", "red_pipes: its shape built in code from its concept crop")]
PIXAL = [("pixal3d", "its shape, a Pixal3D take from its close-up")]
KIT = [("polyhaven", "a Poly Haven model taken in")]


def grid(rows, columns, place):
    """A closed tube-like grid of quads: (points, counts, indices), points[row, column] from place(u, v)."""
    u, v = np.meshgrid(np.linspace(0, 1, rows), np.linspace(0, 1, columns, endpoint=False), indexing="ij")
    points = place(u, v).reshape(-1, 3)
    faces = [(row * columns + column, row * columns + (column + 1) % columns,
              (row + 1) * columns + (column + 1) % columns, (row + 1) * columns + column)
             for row in range(rows - 1) for column in range(columns)]
    return points, [4] * len(faces), [corner for face in faces for corner in face]


def pipe(swell):
    """A pipe 3 m long and 0.2 m wide along x, its radius swelling by `swell` four times along it, a flange half as
    wide again at each end."""
    def place(u, v):
        radius = 0.1 * (1 + swell * np.sin(u * 8 * np.pi))
        radius = np.where((u < 0.05) | (u > 0.95), 0.15, radius)
        return np.stack([u * 3, radius * np.cos(v * 2 * np.pi), radius * np.sin(v * 2 * np.pi)], -1)
    return grid(60, 24, place)


def lump():
    """A ball of bumps 1 m across: no flat face anywhere."""
    def place(u, v):
        polar, around = u * np.pi, v * 2 * np.pi
        radius = 0.5 * (1 + 0.15 * np.sin(5 * polar) * np.cos(4 * around))
        return np.stack([radius * np.sin(polar) * np.cos(around), radius * np.cos(polar),
                         radius * np.sin(polar) * np.sin(around)], -1)
    return grid(40, 40, place)


def box():
    """A console's box, 1.2 by 0.9 by 0.6 m, its faces each cut in quads."""
    corners = np.array([[x, y, z] for x in (0, 1.2) for y in (0, 0.9) for z in (0, 0.6)], dtype=float)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return corners, [4] * 6, [corner for face in faces for corner in face]


def model_text(name, shape):
    points, counts, indices = shape
    stage = Usd.Stage.CreateInMemory()
    top = UsdGeom.Xform.Define(stage, f"/{name}")
    stage.SetDefaultPrim(top.GetPrim())
    mesh = UsdGeom.Mesh.Define(stage, f"/{name}/geo")
    mesh.CreatePointsAttr(Vt.Vec3fArray([tuple(map(float, point)) for point in points]))
    mesh.CreateFaceVertexCountsAttr(counts)
    mesh.CreateFaceVertexIndicesAttr([int(index) for index in indices])
    return stage.GetRootLayer().ExportToString()


# (object, entry id, its shape, how it was made, the faults told)
CASES = [
    ("sausage", "red_pipes_1.cockpit", pipe(0.25), CROP, {"a sausage"}),
    ("straight", "large_pipes_1.hangar", pipe(0.0), CROP, set()),
    ("socketed", "grey_pipes_1.hangar", pipe(0.12), CROP, set()),
    ("lumpy", "pilot_console_1.cockpit", lump(), PIXAL, {"a lump"}),
    ("boxed", "comms_console_1.cockpit", box(), PIXAL, set()),
    ("kit", "console_kit", lump(), KIT, set()),
    ("seat", "pilot_seat_1.cockpit", lump(), PIXAL, set()),
]


@pytest.mark.parametrize("name, entry_id, shape, made_with, told", CASES, ids=[case[0] for case in CASES])
def test_a_made_shape_that_reads_wrong_is_told_for_a_remake(tmp_path, monkeypatch, name, entry_id, shape, made_with,
                                                            told):
    folder = tmp_path / "lib" / "entries" / "model" / entry_id / "1"
    folder.mkdir(parents=True)
    folder.joinpath("entry.json").write_text(json.dumps({
        "schema": "score-lib-entry/1", "address": f"model/{entry_id}@1", "kind": "model", "id": entry_id,
        "version": 1, "files": {"model.usda": {"role": "usd"}},
        "provenance": {"made_with": [{"by": by, "what": what} for by, what in made_with]}}))
    (tmp_path / "model.usda").write_text(model_text(entry_id.split(".")[0], shape))
    monkeypatch.setenv("SCORE_LIB_ROOT", str(tmp_path / "lib"))
    scene = Usd.Stage.CreateInMemory()
    prim = scene.DefinePrim(f"/camp/Objects/{name}")
    prim.GetReferences().AddReference(str(tmp_path / "model.usda"))
    prim.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(f"model/{entry_id}@1")
    found = shapes.faults(scene, "camp")
    assert {fault["kind"] for fault in found.get(name, ())} == told, (shapes.measured(finished.model_file(prim)),
                                                                      found)
