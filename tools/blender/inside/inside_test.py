"""Check the parts of the inside scripts that need no Blender, with bpy and mathutils stubbed out.

The game's ink rule in usd_views.py (pure numpy on a depth picture) and annotate_stage.py's object numbering (prim
paths rebuilt from parents' names). The rendering itself needs a Blender: tools/blender/smoke.py starts one.

Run: .venv/bin/python tools/blender/inside/inside_test.py
"""
import pathlib
import sys
import types

import numpy

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
for name in ("bpy", "bpy_extras", "mathutils"):
    sys.modules[name] = types.ModuleType(name)
sys.modules["bpy_extras"].anim_utils = None
sys.modules["mathutils"].Matrix = sys.modules["mathutils"].Vector = lambda *given, **named: None

import annotate_stage  # noqa: E402
import usd_views  # noqa: E402

_failures = []


def check(what, held):
    print(("PASS  " if held else "FAIL  ") + what)
    if not held:
        _failures.append(what)


def check_smoothstep():
    values = usd_views.smoothstep(1.0, 3.0, numpy.array([0.0, 1.0, 2.0, 3.0, 9.0]))
    check("smoothstep holds 0 below, 1 above, a half in the middle", numpy.allclose(values, [0, 0, 0.5, 1, 1]))


def check_at_offset():
    values = numpy.arange(12.0).reshape(3, 4)
    right = usd_views.at_offset(values, (1.0, 0.0), 1.0)
    check("at_offset reads the pixel to the right", right[0, 0] == 1.0 and right[2, 2] == 11.0)
    check("at_offset holds at the picture's edge", right[1, 3] == 7.0)
    down = usd_views.at_offset(values, (0.0, 1.0), 2.0)
    check("at_offset reads rows down, clamped", down[0, 1] == 9.0 and down[2, 1] == 9.0)


def check_shape_normals():
    normal = usd_views.shape_normals(numpy.full((20, 30), 5.0), 60.0)
    check("a wall square to the eye faces it", numpy.allclose(normal[10, 15], [0.0, 0.0, -1.0], atol=1e-6))
    check("its normals are unit long", numpy.allclose(numpy.linalg.norm(normal[1:-1, 1:-1], axis=2), 1.0))


def wall_normal(depth):
    normal = numpy.zeros(depth.shape + (3,))
    normal[..., 2] = 1.0
    return normal


def check_ink_lines():
    flat = numpy.full((540, 960), 10.0)  # half the game's 1080 rows: lines two pixels out
    check("a flat wall gets no ink", usd_views.ink_lines(flat, wall_normal(flat), numpy.zeros(flat.shape), 60.0).max()
          < 1e-6)
    step = flat.copy()
    step[:, 480:] = 5.0
    ink = usd_views.ink_lines(step, wall_normal(step), numpy.zeros(step.shape), 60.0)
    check("a nearer board's edge is inked", ink[270, 480] > 0.99 and ink[270, 481] > 0.99)
    check("away from the edge there is none", ink[270, 470] < 1e-6 and ink[270, 490] < 1e-6)
    textured = usd_views.ink_lines(step, wall_normal(step), numpy.ones(step.shape), 60.0)
    check("a textured board's edge is inked too", textured[270, 480] > 0.99)
    far = step * 30.0
    check("lines fade out past the fade distance",
          usd_views.ink_lines(far, wall_normal(far), numpy.zeros(far.shape), 60.0).max() < 1e-6)


class Item:
    def __init__(self, name, parent=None, kind="MESH", properties=()):
        self.name, self.parent, self.type, self.properties, self.pass_index = name, parent, kind, dict(properties), 0

    def keys(self):
        return self.properties.keys()


def check_numbering():
    place = Item("camp", kind="EMPTY")
    objects = Item("Objects", place, "EMPTY")
    tent = Item("tent.001", objects, "EMPTY", {"score:inventory_row": 3})
    parts = [Item("geo", tent), Item("geo.002", tent)]
    ground = Item("Ground", place)
    check("prim_path drops Blender's .001", annotate_stage.prim_path(tent) == "/camp/Objects/tent")
    check("a mesh's owner is the laid object above it", annotate_stage.owner(parts[1]) is tent)
    check("a mesh with no laid object owns itself", annotate_stage.owner(ground) is ground)
    paths = annotate_stage.numbered([place, *parts, ground])
    check("numbered gives each laid object one id", paths == {1: "/camp/Objects/tent", 2: "/camp/Ground"})
    check("each mesh carries its owner's id", [item.pass_index for item in (*parts, ground, place)] == [1, 1, 2, 0])


check_smoothstep()
check_at_offset()
check_shape_normals()
check_ink_lines()
check_numbering()
if _failures:
    sys.exit(f"{len(_failures)} failed")
print("ok")
