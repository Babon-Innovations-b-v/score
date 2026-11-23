"""Invariant: a laid place is told every way it strays from its plan, and only those: a room bigger than its plan's
floor, a plan item nothing stands in, one where only made blocks stand, a library thing far bigger or smaller than its
item, a dressing row of the plan's walls with nothing dressed as it; a place laid as planned is told nothing. The plan
taken in gives an eye-height view from each person spot and doorway, rendered at 1920 wide when no view is asked; a
wall's dressing runs edge to edge along its wall, backs on its face, turned into the room and clear of its doorway.

Breaks (each applied once, seen red, reverted), in plan_fit unless named:
- room_faults: `ratio.max() > ROOM` made `> 2 * ROOM` -> the room 1.8 times its plan passes
- item_faults: `is_library_thing` read as any address -> the console of made blocks passes
- standing_in: NEAR dropped from the box -> the lamp standing 0.2 m off its item reads missing
- standing_in: a structure over the room read as standing in -> the roof stands in for the missing lamp
- scale_faults: the long side read as the short side -> the 3 m engine on a 1.2 m item passes
- dress_faults: `score:dress` unread -> the dressed wall panels still read undressed
- views: the doorway's INWARD step dropped -> its view's eye stands in the doorway, not inside it
- wall_spots: doorways unread -> a panel is laid across the door
- yaw_to: the front left out -> a +x front on the north wall faces along the wall, not into the room
- render.render: plan_views unread -> a render with no views asked draws one camera
- render.WIDTH: 768 -> the preview is too small to judge
"""
import json

import numpy as np
import pytest
from pxr import Gf, Sdf, Usd, UsdGeom

from score.review.environment_plan import WALLS_ITEM
from score.stages import place_build
from score.stages.place_build import plan_fit, render

PLAN = {"place": "room", "walls": {"wide": 10.0, "deep": 8.0}, "doors": [], "floor": [[-5.0, -4.0], [5.0, 4.0]],
        "floor_height": 0.0,
        "items": [{"name": WALLS_ITEM, "box": [-5.0, -4.0, 5.0, 4.0], "kind": "item",
                   "rows": ["wall_panel", "floor_grating", "window"]},
                  {"name": "ENGINE 1", "box": [-3.0, -1.0, -1.8, 0.0], "kind": "item", "rows": ["engine"]},
                  {"name": "CONSOLE 1", "box": [1.0, -3.0, 2.0, -2.5], "kind": "item", "rows": ["console"]},
                  {"name": "LAMP 1", "box": [3.0, 2.0, 3.3, 2.3], "kind": "item", "rows": ["lamp"]},
                  {"name": "KEEP CLEAR", "box": [-1.0, 1.0, 1.0, 3.0], "kind": "zone", "rows": []}],
        "standing": [{"at": [0.0, -2.0], "level": 0.0, "looks_at": None}],
        "doorways": [{"name": "door-1", "middle": [0.0, 0.0, -4.0], "inward": [0.0, 0.0, 1.0], "wide": 1.2,
                      "sill": 0.0, "head": 2.2, "to": None}]}

# (name, x0, z0, x1, z1, address, role, dress): each laid object's footprint (1 m tall) in the planned room.
PLANNED = [("wall_north", -5.3, -4.3, 5.3, -4.0, None, "structure", None),
           ("wall_south", -5.3, 4.0, 5.3, 4.3, None, "structure", None),
           ("engine", -3.0, -1.0, -1.7, 0.0, "model/engine@1", None, None),
           ("console", 1.0, -3.0, 2.0, -2.5, "model/console@1", None, None),
           ("lamp", 3.4, 2.4, 3.6, 2.6, "model/lamp@1", None, None),
           ("panel_N0", -2.0, -4.0, -1.0, -3.9, "kit/panel@1", "mount", "wall_panel"),
           ("grate_floor0", -1.0, -1.0, 0.0, 0.0, "kit/grate@1", None, "floor_grating")]


def stage_of(objects):
    """A scene of the objects, each a box over its footprint, its address and marks as place_build lays them."""
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.Scope.Define(stage, "/room/Objects")
    for name, x0, z0, x1, z1, address, role, dressed in objects:
        prim = UsdGeom.Xform.Define(stage, f"/room/Objects/{name}")
        prim.AddTranslateOp().Set(Gf.Vec3d((x0 + x1) / 2, 0.5, (z0 + z1) / 2))
        prim.AddScaleOp().Set(Gf.Vec3f((x1 - x0) / 2, 0.5, (z1 - z0) / 2))
        UsdGeom.Cube.Define(stage, f"/room/Objects/{name}/geo")
        for key, value in (("score:library", address), ("score:role", role), ("score:dress", dressed)):
            if value:
                prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
    return stage


def role_of(prim):
    return prim.GetAttribute("score:role").Get() if prim.GetAttribute("score:role") else "prop"


def told(objects):
    """The faults of the objects against PLAN, as (fault, what) pairs."""
    found = plan_fit.faults(stage_of(objects), "room", PLAN, role_of)
    return sorted((fault["fault"], fault.get("item") or fault.get("row") or "") for fault in found)


def changed(name, **given):
    """PLANNED with one object's footprint or address replaced."""
    fields = ("name", "x0", "z0", "x1", "z1", "address", "role", "dress")
    return [tuple({**dict(zip(fields, each)), **given}.values()) if each[0] == name else each for each in PLANNED]


def taken(tmp_path):
    """A place folder with PLAN taken in; its record."""
    (tmp_path / "place.json").write_text(json.dumps({"place": "room", "size": [1600, 900], "camera":
                                                     place_build.CAMERA, "views": {"mine": place_build.CAMERA}}))
    (tmp_path / "source.json").write_text(json.dumps(PLAN))
    plan_fit.take(tmp_path, tmp_path / "source.json")
    return place_build.record_of(tmp_path)


def stretched():
    """PLANNED with both walls 1.8 times as long: the room far wider than its plan."""
    return [each if not each[0].startswith("wall") else (each[0], -9.5, each[2], 9.5, *each[4:]) for each in PLANNED]


CASES = [
    ("a place laid as planned is told nothing", lambda tmp: told(PLANNED), []),
    ("a room 1.9 times its plan is oversized", lambda tmp: told(stretched()), [("room oversized", "")]),
    ("a console of made blocks stands in", lambda tmp: told(changed("console", address=None)),
     [("block stands in", "CONSOLE 1")]),
    ("an algorithm's block stands in too", lambda tmp: told(changed("console", address="algorithm/dome_shell@1")),
     [("block stands in", "CONSOLE 1")]),
    ("a 3 m engine on a 1.2 m item is too big", lambda tmp: told(changed("engine", x0=-4.0, x1=-1.0)),
     [("too big", "ENGINE 1")]),
    ("a 0.4 m engine is too small", lambda tmp: told(changed("engine", x0=-2.6, x1=-2.2, z0=-0.6, z1=-0.4)),
     [("too small", "ENGINE 1")]),
    ("a roof whose middle stands over the missing lamp stands in for nothing",
     lambda tmp: told([each for each in PLANNED if each[0] != "lamp"]
                      + [("roof", 1.3, 0.3, 5.0, 4.0, None, "structure", None)]),
     [("missing", "LAMP 1")]),
    ("an item nothing stands in is missing", lambda tmp: told([each for each in PLANNED if each[0] != "lamp"]),
     [("missing", "LAMP 1")]),
    ("bare walls are undressed", lambda tmp: told([each for each in PLANNED if not each[7]]),
     [("undressed", "floor_grating"), ("undressed", "wall_panel")]),
    ("a view from the person spot and from inside the doorway", lambda tmp: plan_fit.views(PLAN),
     {"plan-stand-1": {"eye": [0.0, 1.6, -2.0], "aim": [0.0, 1.2, 0.0], "fov": 70.0},
      "plan-door-1": {"eye": [0.0, 1.6, -3.4], "aim": [0.0, 1.2, 0.0], "fov": 70.0}}),
    ("the plan's views are rendered when none is asked, at 1920",
     lambda tmp: (sorted(taken(tmp)["views"]), render.plan_views(tmp),
                  render.views(place_build.record_of(tmp), render.WIDTH, render.plan_views(tmp))["size"]),
     (["mine", "plan-door-1", "plan-stand-1"], ["plan-door-1", "plan-stand-1"], [1920, 1080])),
    ("panels along the north wall, edge to edge, backs on its face, the doorway clear",
     lambda tmp: plan_fit.wall_spots(PLAN, "N", (1.0, 0.1), None, -4.0),
     [[x, -3.95] for x in (-4.5, -3.5, -2.5, -1.5, 1.5, 2.5, 3.5, 4.5)]),
    ("grates tiled over the floor", lambda tmp: len(plan_fit.floor_spots(PLAN, (2.0, 2.0), None)), 20),
    ("a +z front on the north wall faces into the room", lambda tmp: plan_fit.yaw_to((0.0, 1.0), (0.0, 1.0)), 0.0),
    ("a +x front on the north wall turns a quarter", lambda tmp: plan_fit.yaw_to((1.0, 0.0), (0.0, 1.0)), 270.0),
]


@pytest.mark.parametrize("case, measured, expected", CASES, ids=[case[0] for case in CASES])
def test_a_place_is_told_where_it_strays_from_its_plan(case, measured, expected, tmp_path):
    found = measured(tmp_path)
    if isinstance(expected, list) and expected and isinstance(expected[0], list):
        assert np.allclose(found, expected, atol=1e-6), case
    else:
        assert found == expected, case
