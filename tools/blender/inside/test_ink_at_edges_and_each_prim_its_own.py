"""The inside scripts' pure parts, with bpy and mathutils stubbed out: ink falls only on a nearer thing's edge, and
every object and effect is found under its own prim path.

usd_views.py's ink rule (the game's ink_edges shader, pure numpy on a depth picture), annotate_stage.py's object
numbering (prim paths rebuilt from Blender's parent names), and usd_views.py's effect lookup (a film stage holds its
neighbours' effects, so one effect name comes several times: every Moon film failed, 2026-10-17; Blender folds a
one-child Xform into its child, so both hangar films failed, 2026-10-18). The rendering itself needs a Blender:
tools/blender/smoke.py starts one.

The break that turns the test red (applied once each, seen red, reverted):

- The ink rule's numeric parts hold (smoothstep 3t^2 - 2t^3, offset reads held at the edge, a wall square to the eye
  faces it). Break: smoothstep's `3.0 - 2.0 * share` made `3.0 - share`.
- Ink falls only on a nearer thing's edge, never on a flat wall nor past the fade. Break: ink_lines drops its fade,
  `* (1.0 - smoothstep(INK_FADE...))`.
- Each laid object gets one id and its meshes carry it. Break: owner returns `item` at once.
- Each effect finds its own place's cloud. Break: effect_cloud's `most and kept[id(cloud)] == most` made `True`.
- A view looking along its own up is refused by name. Break: upright returns at once (round 33's spot-1 at shiplock
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


class Item:
    """A Blender object as the scripts read it: a name, a parent, a type, custom properties, a pass index."""

    def __init__(self, name, parent=None, kind="MESH", properties=()):
        self.name, self.parent, self.type, self.properties, self.pass_index = name, parent, kind, dict(properties), 0

    def keys(self):
        return self.properties.keys()


class Prim:
    def __init__(self, path):
        self.path = path

    def GetPath(self):
        return self.path

    def GetName(self):
        return self.path.rsplit("/", 1)[1]


def blender_stage(*leaves):
    """Blender's objects at its rebuilt paths (names as Blender gave them), parents shared by path and empty:
    {path: Item}. Each leaf is (path, kind, properties)."""
    made = {}
    for path, kind, properties in leaves:
        parent = None
        names = path.strip("/").split("/")
        for depth, name in enumerate(names):
            at = "/" + "/".join(names[:depth + 1])
            if at not in made:
                made[at] = (Item(name, parent, kind, properties) if depth == len(names) - 1
                            else Item(name, parent, "EMPTY"))
            parent = made[at]
    return made


def wall_normal(depth):
    normal = numpy.zeros(depth.shape + (3,))
    normal[..., 2] = 1.0
    return normal


# Half the game's 1080 rows, so lines are two pixels out: a wall at 10 m, a board at 5 m before it from column 480 on.
WALL = numpy.full((540, 960), 10.0)
BOARD = WALL.copy()
BOARD[:, 480:] = 5.0
# (picture, its depth, textured, pixels inked, pixels clean); None for clean: nowhere inked
PICTURES = [("flat wall", WALL, False, [], None),
            ("board before the wall", BOARD, False, [(270, 480), (270, 481)], [(270, 470), (270, 490)]),
            ("textured board", BOARD, True, [(270, 480)], [(270, 470), (270, 490)]),
            ("board past the fade (150 m and 300 m, fade 60 to 120 m)", BOARD * 30.0, False, [], None)]
# smoothstep(1, 3): 0 below, 1 above, 3t^2 - 2t^3 between (t = 0.25: 0.15625)
STEPS = [(0.0, 0.0), (1.0, 0.0), (1.5, 0.15625), (2.0, 0.5), (3.0, 1.0), (9.0, 1.0)]
# a 3 x 4 picture 0..11 read along (across, down) by reach: (way, reach, pixel, value); edges held
OFFSETS = [((1.0, 0.0), 1.0, (0, 0), 1.0), ((1.0, 0.0), 1.0, (2, 2), 11.0), ((1.0, 0.0), 1.0, (1, 3), 7.0),
           ((0.0, 1.0), 2.0, (0, 1), 9.0), ((0.0, 1.0), 2.0, (2, 1), 9.0)]
# the hangar's film stage as Blender 4.2 brought it in, 2026-10-18 (one-child Xforms folded into their child), with
# the airlock's laid tent and ground, and two loose effect names elsewhere
STAGE = [("/hangar/Places/airlock/Objects/tent.001/geo", "MESH", {}),
         ("/hangar/Places/airlock/Objects/tent.001/geo.002", "MESH", {}),
         ("/hangar/Places/airlock/Ground", "MESH", {}),
         ("/hangar/Places/airlock/Fixtures.001/door_vent_points", "POINTCLOUD", {}),
         ("/hangar/Places/door_vent_points.001", "POINTCLOUD", {}),
         ("/hangar/Places/garage/Effects.002/pump_fog_points", "POINTCLOUD", {}),
         ("/hangar/Places/airlock/Effects.001/pump_fog_points.001", "POINTCLOUD", {}),
         ("/hangar/Effects.004/pump_fog_points.002", "POINTCLOUD", {}),
         ("/other/dust_points", "POINTCLOUD", {}),
         ("/a/smoke_points", "POINTCLOUD", {}), ("/b/smoke_points", "POINTCLOUD", {})]
# effect prim -> the cloud it is found as; None: two clouds of the name, neither on the path, no guess
EFFECTS = [("/hangar/Places/airlock/Fixtures/door_vent/door_vent_points", "door_vent_points"),
           ("/hangar/Places/door_vent/door_vent_points", "door_vent_points.001"),
           ("/hangar/Places/airlock/Effects/pump_fog/pump_fog_points", "pump_fog_points.001"),
           ("/hangar/Places/garage/Effects/pump_fog/pump_fog_points", "pump_fog_points"),
           ("/hangar/Effects/pump_fog/pump_fog_points", "pump_fog_points.002"),
           ("/camp/Effects/dust/dust_points", "dust_points"),
           ("/camp/Effects/smoke/smoke_points", None)]
# a view and whether it is refused
VIEWS = [({"name": "level", "eye": [0, 1.6, 0], "aim": [3, 1.0, 0], "up": [0, 1, 0]}, None),
         ({"name": "down", "eye": [0, 4, 0], "aim": [0, 1, 0], "up": [1, 0, 0]}, None),
         ({"name": "spot-1", "eye": [0, 4, 0], "aim": [0, 1, 0], "up": [0, 1, 0]}, "'spot-1' looks along its own up")]


def test_ink_at_edges_and_each_prim_its_own():
    values = usd_views.smoothstep(1.0, 3.0, numpy.array([given for given, _ in STEPS]))
    assert numpy.allclose(values, [wanted for _, wanted in STEPS])
    picture = numpy.arange(12.0).reshape(3, 4)
    for way, reach, (row, column), wanted in OFFSETS:
        assert usd_views.at_offset(picture, way, reach)[row, column] == wanted, (way, reach, row, column)
    normal = usd_views.shape_normals(WALL, 60.0)
    assert numpy.allclose(normal[270, 480], [0.0, 0.0, -1.0], atol=1e-6)  # a wall square to the eye faces it
    assert numpy.allclose(numpy.linalg.norm(normal[1:-1, 1:-1], axis=2), 1.0)
    for label, depth, textured, inked, clean in PICTURES:
        ink = usd_views.ink_lines(depth, wall_normal(depth), numpy.full(depth.shape, float(textured)), 60.0)
        assert all(ink[pixel] > 0.99 for pixel in inked), label
        assert (ink.max() < 1e-6) if clean is None else all(ink[pixel] < 1e-6 for pixel in clean), label

    stage = blender_stage(*STAGE)
    tent_path = "/hangar/Places/airlock/Objects/tent.001"
    tent, ground = stage[tent_path], stage["/hangar/Places/airlock/Ground"]
    tent.properties["score:inventory_row"] = 3
    parts = [stage[f"{tent_path}/geo"], stage[f"{tent_path}/geo.002"]]
    clouds = [item for item in stage.values() if item.type == "POINTCLOUD"]
    assert annotate_stage.prim_path(tent) == "/hangar/Places/airlock/Objects/tent"  # Blender's .001 dropped
    assert annotate_stage.owner(parts[1]) is tent and annotate_stage.owner(ground) is ground
    assert annotate_stage.numbered(list(stage.values())) == {1: "/hangar/Places/airlock/Objects/tent",
                                                             2: "/hangar/Places/airlock/Ground"}
    place = stage["/hangar/Places/airlock"]
    assert [item.pass_index for item in (*parts, ground, place, clouds[0])] == [1, 1, 2, 0, 0]
    for prim, wanted in EFFECTS:
        if wanted is None:
            with pytest.raises(RuntimeError):
                usd_views.effect_cloud(Prim(prim), clouds)
        else:
            assert usd_views.effect_cloud(Prim(prim), clouds).name == wanted, prim
    for view, refusal in VIEWS:
        if refusal is None:
            usd_views.upright(view)
        else:
            with pytest.raises(ValueError, match=refusal):
                usd_views.upright(view)
