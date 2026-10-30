"""The inside scripts' pure parts, with bpy and mathutils stubbed out: ink falls only on a nearer thing's edge, and
every object and effect is found under its own prim path.

usd_views.py's ink rule (the game's ink_edges shader, pure numpy on a depth picture), annotate_stage.py's object
numbering (prim paths rebuilt from Blender's parent names), and usd_views.py's effect lookup (a film stage holds its
neighbours' effects, so one effect name comes several times: every Moon film failed, 2026-10-17; Blender folds a
one-child Xform into its child, so both hangar films failed, 2026-10-18). The rendering itself needs a Blender:
tools/blender/smoke.py starts one.

The break that turns each test red (applied once each, seen red, reverted):

- test_the_ink_rules_numeric_parts: smoothstep's `3.0 - 2.0 * share` made `3.0 - share`.
- test_ink_falls_only_on_a_nearer_things_edge: ink_lines drops its fade, `* (1.0 - smoothstep(INK_FADE...))`.
- test_each_laid_object_gets_one_id_and_its_meshes_carry_it: owner returns `item` at once.
- test_each_effect_finds_its_own_places_cloud: effect_cloud's `most and kept[id(cloud)] == most` made `True`.
- test_a_view_looking_along_its_own_up_is_refused_by_name: upright returns at once (round 33's spot-1 at shiplock
  looked straight down, up (0, 1, 0): its camera had no sideways, 2026-10-30).

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest tools/blender/inside/test_ink_at_edges_and_each_prim_its_own.py
"""
import pathlib
import sys
import types

import numpy
import pytest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
for name in ("bpy", "bpy_extras", "mathutils"):
    sys.modules[name] = types.ModuleType(name)
sys.modules["bpy_extras"].anim_utils = None
sys.modules["mathutils"].Matrix = sys.modules["mathutils"].Vector = lambda *given, **named: None

import annotate_stage  # noqa: E402
import usd_views  # noqa: E402


def test_the_ink_rules_numeric_parts():
    # smoothstep: 0 below, 1 above, 3t^2 - 2t^3 between (t = 0.25: 0.15625)
    values = usd_views.smoothstep(1.0, 3.0, numpy.array([0.0, 1.0, 1.5, 2.0, 3.0, 9.0]))
    assert numpy.allclose(values, [0, 0, 0.15625, 0.5, 1, 1])
    picture = numpy.arange(12.0).reshape(3, 4)
    right = usd_views.at_offset(picture, (1.0, 0.0), 1.0)
    assert (right[0, 0], right[2, 2], right[1, 3]) == (1.0, 11.0, 7.0)  # the edge column holds
    down = usd_views.at_offset(picture, (0.0, 1.0), 2.0)
    assert (down[0, 1], down[2, 1]) == (9.0, 9.0)  # two rows down, clamped at the last
    normal = usd_views.shape_normals(numpy.full((20, 30), 5.0), 60.0)
    assert numpy.allclose(normal[10, 15], [0.0, 0.0, -1.0], atol=1e-6)  # a wall square to the eye faces it
    assert numpy.allclose(numpy.linalg.norm(normal[1:-1, 1:-1], axis=2), 1.0)


def wall_normal(depth):
    normal = numpy.zeros(depth.shape + (3,))
    normal[..., 2] = 1.0
    return normal


def test_ink_falls_only_on_a_nearer_things_edge():
    """Half the game's 1080 rows, so lines are two pixels out; a board at 5 m stands before a wall at 10 m from
    column 480 on."""
    flat = numpy.full((540, 960), 10.0)
    assert usd_views.ink_lines(flat, wall_normal(flat), numpy.zeros(flat.shape), 60.0).max() < 1e-6
    step = flat.copy()
    step[:, 480:] = 5.0
    ink = usd_views.ink_lines(step, wall_normal(step), numpy.zeros(step.shape), 60.0)
    assert ink[270, 480] > 0.99 and ink[270, 481] > 0.99  # the nearer board's edge
    assert ink[270, 470] < 1e-6 and ink[270, 490] < 1e-6  # nowhere else
    textured = usd_views.ink_lines(step, wall_normal(step), numpy.ones(step.shape), 60.0)
    assert textured[270, 480] > 0.99
    far = step * 30.0  # 150 m and 300 m: past the fade (60 to 120 m)
    assert usd_views.ink_lines(far, wall_normal(far), numpy.zeros(far.shape), 60.0).max() < 1e-6


class Item:
    """A Blender object as the scripts read it: a name, a parent, a type, custom properties, a pass index."""

    def __init__(self, name, parent=None, kind="MESH", properties=()):
        self.name, self.parent, self.type, self.properties, self.pass_index = name, parent, kind, dict(properties), 0

    def keys(self):
        return self.properties.keys()


def test_each_laid_object_gets_one_id_and_its_meshes_carry_it():
    place = Item("camp", kind="EMPTY")
    objects = Item("Objects", place, "EMPTY")
    tent = Item("tent.001", objects, "EMPTY", {"score:inventory_row": 3})
    parts = [Item("geo", tent), Item("geo.002", tent)]
    ground = Item("Ground", place)
    assert annotate_stage.prim_path(tent) == "/camp/Objects/tent"  # Blender's .001 dropped
    assert annotate_stage.owner(parts[1]) is tent and annotate_stage.owner(ground) is ground
    assert annotate_stage.numbered([place, *parts, ground]) == {1: "/camp/Objects/tent", 2: "/camp/Ground"}
    assert [item.pass_index for item in (*parts, ground, place)] == [1, 1, 2, 0]


class Prim:
    def __init__(self, path):
        self.path = path

    def GetPath(self):
        return self.path

    def GetName(self):
        return self.path.rsplit("/", 1)[1]


def blender_tree(*paths):
    """Point clouds at Blender's rebuilt paths (names as Blender gave them), parents shared by name."""
    made, clouds = {}, []
    for path in paths:
        parent = None
        names = path.strip("/").split("/")
        for depth, name in enumerate(names):
            at = "/".join(names[:depth + 1])
            if at not in made:
                made[at] = Item(name, parent, "POINTCLOUD" if depth == len(names) - 1 else "EMPTY")
            parent = made[at]
        clouds.append(parent)
    return clouds


def test_each_effect_finds_its_own_places_cloud():
    # the hangar's film stage as Blender 4.2 brought it in, 2026-10-18 (one-child Xforms folded into their child)
    clouds = blender_tree("/hangar/Places/airlock/Fixtures.001/door_vent_points", "/hangar/Places/door_vent_points.001",
                          "/hangar/Places/garage/Effects.002/pump_fog_points",
                          "/hangar/Places/airlock/Effects.001/pump_fog_points.001",
                          "/hangar/Effects.004/pump_fog_points.002")
    found = [usd_views.effect_cloud(Prim(path), clouds).name for path in (
        "/hangar/Places/airlock/Fixtures/door_vent/door_vent_points", "/hangar/Places/door_vent/door_vent_points",
        "/hangar/Places/airlock/Effects/pump_fog/pump_fog_points", "/hangar/Places/garage/Effects/pump_fog/pump_fog_points",
        "/hangar/Effects/pump_fog/pump_fog_points")]
    assert found == ["door_vent_points", "door_vent_points.001", "pump_fog_points.001", "pump_fog_points",
                     "pump_fog_points.002"]
    lone = blender_tree("/other/dust_points")
    assert usd_views.effect_cloud(Prim("/camp/Effects/dust/dust_points"), lone).name == "dust_points"
    with pytest.raises(RuntimeError):  # two clouds of the name, neither on the path: no guess
        usd_views.effect_cloud(Prim("/camp/Effects/dust/dust_points"), blender_tree("/a/dust_points", "/b/dust_points"))


def test_a_view_looking_along_its_own_up_is_refused_by_name():
    usd_views.upright({"name": "level", "eye": [0, 1.6, 0], "aim": [3, 1.0, 0], "up": [0, 1, 0]})
    usd_views.upright({"name": "down", "eye": [0, 4, 0], "aim": [0, 1, 0], "up": [1, 0, 0]})
    with pytest.raises(ValueError, match="'spot-1' looks along its own up"):
        usd_views.upright({"name": "spot-1", "eye": [0, 4, 0], "aim": [0, 1, 0], "up": [0, 1, 0]})
