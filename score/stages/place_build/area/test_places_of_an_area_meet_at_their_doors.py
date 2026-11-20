"""Invariant: places of one area meet at their doors. A flat held beside a one-storey stair core (`stairs --joined 1`,
its flat door's doorway recorded as it is laid) is seated by its door leaf onto that doorway, its floor at the plans'
storey height (3 m), and a walker goes from the landing through the doorway into the flat; while the same flat is
told by name when the core keeps the hall stub behind that door (no walker's way), when the plans put the flat's floor
a storey higher than the doorway it is joined at (3 m apart), when the flat's leaf in its frame is 1.2 m wide in the
core's 1.02 m doorway, and when the flat joins no doorway back (no doorway joined).

Breaks that turn this red (each applied once and seen red, then reverted):
- area.seat_onto: `rise` left out of the seat's height -> the flat sits at the street's level, 3 m under its doorway
- area.seat_onto: `target` taken as the doorway's own inward (not its opposite) -> the flat is seated facing away,
  inside the stairwell, and the way is told off facing
- stair_core.structure: the `joined` storey's hall stub kept -> the meeting pair has no walker's way
- area.built_joins: a plan door with no joined doorway skipped silently -> the flat with no join back passes
- area.wider: ready.FIT taken as 0.5 m -> the 1.2 m leaf passes in the 1.02 m doorway
"""
import json

import numpy as np
import pytest
from PIL import Image
from pxr import Gf, Sdf, UsdGeom

from score.stages import place_build
from score.stages.place_build import area


def plans(folder, sill):
    """The area's kept plans: the town holds the stairwell and, south of it, the flat; the stairwell's flat door
    `sill` metres up meets the flat's front door on the town's plan."""
    folder.mkdir()
    door = {"kind": "door", "wide": 1.0, "angle": 0.0, "swing": "right", "head": 2.2}
    written = {
        "town": {"w": 20.0, "d": 20.0, "holds": [{"place": "stairwell", "x": 0.0, "y": 0.0, "w": 4.0, "d": 3.0},
                                                 {"place": "flat", "x": 0.0, "y": 3.0, "w": 4.0, "d": 4.0}]},
        "stairwell": {"w": 4.0, "d": 3.0, "openings": [{**door, "at": [1.0, 3.0], "sill": sill, "to": "flat"}]},
        "flat": {"w": 4.0, "d": 4.0, "openings": [{**door, "at": [1.0, 0.0], "sill": 0.0, "to": "stairwell"}]}}
    for name, body in written.items():
        (folder / f"{name}.json").write_text(json.dumps(body))
    return folder


def started(folder, place):
    folder.mkdir()
    concept = folder / "concept.png"
    Image.new("RGB", (8, 8)).save(concept)
    place_build.start(folder / "place", place, concept)
    return folder / "place"


def box(stage, place, name, size, low, role):
    """An object of one cube `size` whose lowest corner is `low`, of `role`."""
    holder = UsdGeom.Xform.Define(stage, f"/{place}/Objects/{name}")
    holder.AddTranslateOp().Set(Gf.Vec3d(*(np.asarray(low) + np.asarray(size) / 2)))
    cube = UsdGeom.Cube.Define(stage, f"/{place}/Objects/{name}/geo")
    cube.CreateSizeAttr(1.0)
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    holder.GetPrim().CreateAttribute("score:role", Sdf.ValueTypeNames.String).Set(role)
    return holder.GetPrim()


def stairwell(folder, joined):
    """A one-storey stair core, its flat door (core_door1, 3 m up) joined to the flat."""
    folder = started(folder, "stairwell")
    place_build.stairs(folder, "core", storeys=1, one_block=True, joined=joined)
    area.join(folder, "core_door1", "flat")
    return folder


def flat(folder, joined_back, wide):
    """A room 4 x 4 m on its own floor at 0, its front door's leaf `wide` metres (marked to open) on its north edge."""
    folder = started(folder, "flat")
    stage, place = place_build.opened(folder)
    box(stage, place, "floor", (4.0, 0.2, 4.1), (-2.0, -0.2, -4.0), "structure")
    leaf = box(stage, place, "front_door", (wide, 2.05, 0.05), (-wide / 2, 0.0, -0.05), "door")
    leaf.CreateAttribute("score:opens", Sdf.ValueTypeNames.Bool).Set(True)
    stage.GetRootLayer().Save()
    if joined_back:
        area.join(folder, "front_door", "stairwell", inward=(0.0, -1.0))
    return folder


ROWS = [  # (case, the core's joined storeys, the stairwell's flat door sill on the plans, the flat joins back, its
    # leaf's width, told)
    ("they meet", [1], 3.0, True, 0.96, None),
    ("the hall stub walls the flat off", [], 3.0, True, 0.96, "no walker's way"),
    ("the plans put the flat a storey higher", [1], 6.0, True, 0.96, "3.00 m apart"),
    ("the flat's leaf is wider than the doorway", [1], 3.0, True, 1.2, "1.20 m wide, stairwell's core_door1"),
    ("the flat joins no doorway back", [1], 3.0, False, 0.96, "has no doorway joined to stairwell"),
]


@pytest.mark.parametrize("case, joined, sill, joined_back, wide, told", ROWS, ids=[row[0] for row in ROWS])
def test_places_of_an_area_meet_at_their_doors(tmp_path, case, joined, sill, joined_back, wide, told):
    folders = {"stairwell": stairwell(tmp_path / "stairwell", joined),
               "flat": flat(tmp_path / "flat", joined_back, wide)}
    record = area.area(plans(tmp_path / "plans", sill), "town", folders, tmp_path / "seats.json")
    if told is None:
        assert record["faults"] == [], record["faults"]
        seat = np.asarray(record["seats"]["flat"]["matrix"]).reshape(4, 4)
        door = place_build.record_of(folders["stairwell"])["doorways"]["core_door1"]
        assert abs(seat[3, 1] - 3.0) < 1e-6, seat
        assert np.allclose(seat[:3, :3].T @ [0.0, 0.0, -1.0], [0.0, 0.0, 1.0], atol=1e-6), seat
        assert record["joins"][0]["walked"] > 1.5, record["joins"]
        assert np.allclose(seat[:3, :3].T @ [0.0, 0.0, -0.025] + seat[3, :3], door["middle"], atol=0.03), seat
    else:
        assert any(told in fault for fault in record["faults"]), (case, record["faults"])
