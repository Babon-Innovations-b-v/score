"""A thing moves as its scene's design says, and the motion check holds every move to its record. Made from the design
on a small stage made here (no record written for the scene): the door swings a right angle on the hinge at its own
left edge and shuts again, the fan turns a whole number of times a round, the rover stands parked with its rule's
reason, and every gate passes; with nobody in the scene the door stands shut; two seeds make the same moves, so
the row is unseeded; a moving row with no object fails `designed`, left out by name where a batch gap or the accepted plan's
gap names it; a door whose swing strikes is swung the other
way, or less far down to sixty degrees, else stands with its strike; a hatch lying flat stands; a rocket climbs off the Moon at its push less its
body's pull and stands where its push would not lift it, and a flag on an airless body hangs still. The check (check.py, #23), on a cart driven round a closed path, a door swung on its hinge and a hatch slid
down: each passes, and one known fault each fails by name. Expected spots are worked out by hand below.

The worlds of one shape are rows of one case table, fed through the one parametrized test at the end; each test names
the break that turns it red (`Break: <file>: `old` -> `new``); each was applied once and seen red.

Run: PROPS_HOME=$(mktemp -d) .venv/bin/python -m pytest score/stages/motion/test_a_thing_moves_as_its_design_says.py
"""
import copy
import json
import pathlib
import re
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3]))

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from pxr import Gf, Sdf, Usd, UsdGeom  # noqa: E402

from score import checks  # noqa: E402
from score.stages import motion  # noqa: E402
from score.stages.motion import exhaust, from_design  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[3]
PLACE = "toy"
ROWS = [{"id": "door", "name": "door", "noun": "door"}, {"id": "fan", "name": "ceiling fan", "noun": "fan"},
        {"id": "rover", "name": "rover", "noun": "rover"},
        {"id": "astronaut", "name": "astronaut", "noun": "astronaut"}, {"id": "wall", "name": "wall", "noun": "wall"},
        {"id": "ceiling", "name": "ceiling", "noun": "ceiling"}]


def box(stage, path, low, high):
    """A drawn box mesh of triangles from `low` to `high`."""
    (x0, y0, z0), (x1, y1, z1) = low, high
    points = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1),
              (x0, y1, z1)]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (3, 7, 6, 2), (0, 4, 7, 3), (1, 2, 6, 5)]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.GetPointsAttr().Set([Gf.Vec3f(*point) for point in points])
    mesh.GetFaceVertexCountsAttr().Set([3] * 12)
    mesh.GetFaceVertexIndicesAttr().Set([index for a, b, c, d in quads for index in (a, b, c, a, c, d)])


def thing(stage, name, at, low, high):
    """An object Xform at `at` with a box mesh from `low` to `high` in its own frame."""
    xform = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
    xform.AddTranslateOp().Set(Gf.Vec3d(*at))
    box(stage, f"/{PLACE}/Objects/{name}/body", low, high)


def a_seed(folder, structure, things):
    """A scene's stage folder: a root over one base layer holding `structure` ({name: (low, high)}) and `things`
    ((name, at, low, high))."""
    seed = pathlib.Path(folder) / "seeds" / PLACE
    (seed / "layers").mkdir(parents=True)
    stage = Usd.Stage.CreateNew(str(seed / "layers/base.usda"))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{PLACE}").GetPrim())
    for name, (low, high) in structure.items():
        box(stage, f"/{PLACE}/Structure/{name}", low, high)
    for name, at, low, high in things:
        thing(stage, name, at, low, high)
    stage.GetRootLayer().Save()
    top = Sdf.Layer.CreateNew(str(seed / f"{PLACE}.usda"))
    top.subLayerPaths.append("./layers/base.usda")
    top.defaultPrim = PLACE
    top.timeCodesPerSecond = 24.0
    top.Save()
    return seed


# --- the moves made from the design ---------------------------------------------------------------------------------

# A floor; a wall the door's hinge edge stands in; a ceiling the fan hangs in; a door, a fan, a rover and an astronaut.
DESIGNED = [("wall_1", (2.2, 0.0, 1.0), (-0.5, 0.0, -0.1), (0.5, 2.5, 0.1)),
            ("ceiling_1", (-3.0, 2.8, -3.0), (-1.0, 0.0, -1.0), (1.0, 0.2, 1.0)),
            ("door_1", (3.0, 0.0, 1.0), (-0.45, 0.0, -0.05), (0.45, 2.0, 0.05)),
            ("fan_1", (-3.0, 2.6, -3.0), (-0.6, 0.0, -0.6), (0.6, 0.25, 0.6)),
            ("rover_1", (-3.0, 0.0, 3.0), (-1.0, 0.0, -0.7), (1.0, 1.0, 0.7)),
            ("astronaut_1", (0.0, 0.0, -4.0), (-0.25, 0.0, -0.15), (0.25, 1.8, 0.15))]


# The cast's walker: along x = 3 from z = 5 to z = -3 at 1.333 m a second, through the door's doorway (its box x 2.55
# to 3.45 at z 0.95 to 1.05); within a metre of the box from z 2.05 to -0.05, 2.21 to 3.79 s into its walk.
WALKER = {"name": "astronaut_1", "doing": "walking", "at": [3.0, 0.0, 5.0], "turn": 0.0, "pace": 1.333,
          "path": [[3.0, 0.0, 5.0], [3.0, 0.0, -3.0]]}
SEATED = {"name": "astronaut_1", "doing": "sitting", "at": [0.0, 0.0, -4.0], "turn": 0.0, "path": None}


def a_sky(on, gravity):
    """A scene's sky inputs (score/review/scene_sky.py) whose site stands on one body of the reference table."""
    return {"place": PLACE, "site": {"on": on}, "setting": {"bodies": [{"body": on, "name": on.title(),
                                                                         "reference": on, "gravity": gravity}]}}


FLOOR = {"floor": ((-6.0, -0.1, -6.0), (6.0, 0.0, 6.0))}


def toy_inputs(folder, rows=ROWS, extra=(), cast=(WALKER,), sky=a_sky("earth", 9.82), designed=DESIGNED,
               structure=FLOOR):
    folder = pathlib.Path(folder)
    (folder / "inventory.json").write_text(json.dumps({"rows": rows}))
    (folder / "sky.json").write_text(json.dumps(sky))
    seed = a_seed(folder, structure, [*designed, *extra])
    (folder / "cast").mkdir(exist_ok=True)
    (folder / "cast/cast.json").write_text(json.dumps({"characters": list(cast)}))
    return {"design": folder / "inventory.json", "row kinds": REPO / "data/checks/row-kinds.json",
            "screens": REPO / "data/checks/screens.json",
            "kinds": REPO / "data/checks/motion.json", "seed": seed, "cast": folder / "cast",
            "sky": folder / "sky.json", "bodies": REPO / "data/physics/bodies.json"}


def made(inputs, folder):
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    motion.make(inputs, out, 0, {})
    assert motion.layer_faults(out) == []
    return out, json.loads((out / motion.RECORD).read_text())


def judge(name, out, inputs):
    return next(check for check in motion.CHECKS if check.name == name).judge(out, inputs, None)


def middle_at(output, inputs, prim, seconds):
    """The world middle of a prim's bounds at a second, with the motion layer over the scene's stage."""
    root = Sdf.Layer.CreateAnonymous(".usda")
    root.subLayerPaths = [str(pathlib.Path(output) / "layers/motion.usda"),
                          str(pathlib.Path(inputs["seed"]) / f"{PLACE}.usda")]
    stage = Usd.Stage.Open(root)
    bound = UsdGeom.BBoxCache(seconds * 24.0, ["default"]).ComputeWorldBound(stage.GetPrimAtPath(prim))
    return np.asarray(bound.ComputeAlignedRange().GetMidpoint())



OPEN_DOOR = ("open_door_1", (-4.0, 0.0, 0.0), (-0.45, 0.0, -0.05), (0.45, 2.0, 0.05))
SLIDING_DOOR = ("sliding_door_1", (-4.0, 0.0, 4.0), (-0.6, 0.0, -0.05), (0.6, 2.1, 0.05))
WORDED = [{"id": "open_door", "name": "open apartment door", "noun": "door"},
          {"id": "sliding_door", "name": "sliding door", "noun": "door"}]


def test_a_row_that_moves_with_no_object_fails_designed(tmp_path):
    """A crane row moves and no object of it stands on the stage: `designed` fails naming it. Standing on a camp's
    terrain (the place's Terrain scope, no thing under it: motion@campgrounds, 2026-11-08), the crane slewing about its
    middle is mounted on that ground and `grounded` passes it; lifted 0.5 m off it, it fails touching nothing.
    A recorded gap of the crane (data/checks/gaps, the env1 plan's C6: a #88 maker not built) moves `designed`'s fault.
    Break: score/stages/motion/__init__.py: `faults += list(record.get("missing", []))` -> `pass`
    Break: score/stages/__init__.py: `"motion": ("designed", "covered"),` in GAP_GATES dropped, and BATCH_GATES'
        `"motion": ("designed",)` -> `"motion": ()` (the gap moves nothing)
    Break: score/stages/motion/__init__.py: `found = rail_faults(entry, shape, surfaces["ground"], others, rate,
        seconds)` -> `found = rail_faults(entry, shape, stills, others, rate, seconds)`
    The camp's ground is the terrain row's made ground, its own layer (places/camp.usdc under /<place>/Outside), not
    in the place's stage (motion@campgrounds, 2026-11-10): standing on it the crane passes, lifted off it it fails.
    Break: score/stages/motion/__init__.py: `*space.made_ground_meshes(inputs.get("terrain"), place), ` -> ``
    A crane the hand-in marks shown from another place (motion@street, 2026-11-10: its distant flags and rocket are
    the square's) is that place's to move, so `designed` passes it here naming where; one marked shown from no place
    still fails.
    Break: score/stages/motion/shown_rows.py: `if row_of(line) not in shown` -> `if True`
    The sea (motion@square, 2026-11-10): the terrain lays it as one water sheet, /<place>/Outside/water, that only its
    score:row names; the table's make finds it by that tag on the build with the made ground and keys the library's
    ripple into its points (deep-water waves of 5, 4 and 2.5 s: 39.07, 25.0 and 9.77 m long on the Earth's 9.82
    m/s/s), so `designed` and `covered` pass, the sheet rises and falls and stands at the round's end as it started;
    motion's own make, which finds objects by name alone, leaves the sea missing. Untagged it fails `designed`; with
    its ripple's keys gone it fails `covered`.
    Break: score/stages/motion/tagged_rows.py: `if tag and tag.HasAuthoredValue() and tag.Get() == row:` -> `if False:`
    Break: score/stages/motion/water_rows.py: `ripple.write(layer, path, ripple.keyed(...), why)` -> `pass`
    Break: score/stages/motion/ripple.py: `number = omega * omega / float(gravity)` -> `number = omega / float(gravity)`"""
    from score import stages
    inputs = toy_inputs(tmp_path, ROWS + [{"id": "crane", "name": "crane", "noun": "crane"}])
    out, _ = made(inputs, tmp_path)
    verdict = judge("designed", out, inputs)
    assert verdict.answer == checks.FAIL
    assert verdict.findings == ("crane: moves (swing), and no object of it stands on the stage",), verdict.findings
    assert table_judge("designed", out, inputs).answer == checks.FAIL, "no batch gap names the crane, so its fault stays"
    gapped = dict(inputs, gaps=a_gap(tmp_path / "gaps.json", "designed", ["crane"]))
    assert table_judge("designed", out, gapped).answer == checks.PASS, "a recorded gap of the crane moves its fault"
    for shown, answer in (({"place": "square", "row": "crane"}, checks.PASS), (None, checks.FAIL)):
        (tmp_path / "handin.json").write_text(json.dumps({"rows": [{"id": "crane", "shown": shown}]}))
        verdict = table_judge("designed", out, dict(inputs, props=tmp_path / "handin.json"))
        assert verdict.answer == answer and ("square's crane" in verdict.reason) == bool(shown), (shown, verdict)
    for rises, answer in ((0.0, checks.PASS), (0.5, checks.FAIL)):
        folder = tmp_path / f"camp_{rises:g}"
        folder.mkdir()
        inputs = toy_inputs(folder, ROWS + [{"id": "crane", "name": "crane", "noun": "crane"}],
                            extra=(("crane_1", (9.5, rises, 0.0), (-1.0, 0.0, -0.5), (1.0, 3.0, 0.5)),))
        stage = Usd.Stage.Open(str(inputs["seed"] / "layers/base.usda"))
        box(stage, f"/{PLACE}/Terrain/ground", (7.0, -0.1, -4.0), (12.0, 0.0, 4.0))
        stage.GetRootLayer().Save()
        out, record = made(inputs, folder)
        assert "crane_1" in {entry["name"] for entry in record["moves"]}, record
        verdict = judge("grounded", out, inputs)
        assert verdict.answer == answer and all(line.startswith("crane_1: on a rail, yet it touches nothing")
                                                for line in verdict.findings), (rises, verdict.reason, verdict.findings)
    for rises, answer in ((0.0, checks.PASS), (0.5, checks.FAIL)):
        folder = tmp_path / f"made_{rises:g}"
        folder.mkdir()
        inputs = toy_inputs(folder, ROWS + [{"id": "crane", "name": "crane", "noun": "crane"}],
                            extra=(("crane_1", (9.5, rises, 0.0), (-1.0, 0.0, -0.5), (1.0, 3.0, 0.5)),))
        (folder / "terrain/mars/places").mkdir(parents=True)
        ground = Usd.Stage.CreateNew(str(folder / f"terrain/mars/places/{PLACE}.usdc"))
        box(ground, f"/{PLACE}/Outside/near", (7.0, -0.1, -4.0), (12.0, 0.0, 4.0))
        ground.GetRootLayer().Save()
        out, _ = made(inputs, folder)
        verdict = judge("grounded", out, dict(inputs, terrain=folder / "terrain"))
        assert verdict.answer == answer, (rises, verdict.reason, verdict.findings)
    for tagged in (False, True):
        folder = tmp_path / f"sea_{tagged}"
        inputs = a_sea(folder, tagged)
        out = folder / "out"
        out.mkdir()
        stages.MOTION.make(inputs, out, 0, {})
        verdict = table_judge("designed", out, inputs)
        assert (verdict.answer == checks.PASS) == tagged, (tagged, verdict.reason, verdict.findings)
        if not tagged:
            assert verdict.findings == ("sea: moves (ripple), and no object of it stands on the stage",), verdict
    assert judge("designed", out, inputs).answer == checks.FAIL, "by name alone the sea has no object"
    entry, = json.loads((out / "ripples.json").read_text())["ripples"]
    assert (entry["prim"], entry["row"]) == (f"/{PLACE}/Outside/water", "sea"), entry
    assert [wave["length"] for wave in entry["waves"]] == [39.0725, 25.0064, 9.7681], entry["waves"]
    verdict = table_judge("covered", out, inputs)
    assert verdict.answer == checks.PASS and verdict.measures["tagged moved"] == 1, (verdict.reason, verdict.findings)
    rises = [sea_heights(out, inputs, second) for second in (0.0, 1.0, 20.0)]
    assert np.allclose(rises[0], rises[2], atol=1e-6) and np.abs(rises[1] - rises[0]).max() > 0.05, rises
    layer = Sdf.Layer.FindOrOpen(str(out / "layers/motion.usda"))
    layer.GetPrimAtPath(f"/{PLACE}/Outside/water").RemoveProperty(
        layer.GetAttributeAtPath(f"/{PLACE}/Outside/water.points"))
    layer.Save()
    verdict = table_judge("covered", out, inputs)
    assert verdict.answer == checks.FAIL and verdict.findings == (
        f"/{PLACE}/Outside/water (sea): its ripple keys its points still (0 keys)",), verdict.findings


def a_sea(folder, tagged):
    """A place with a sea row whose only object is its terrain's water sheet (outside.write_mesh's form: 41 by 41
    points 0.5 m apart, a metre under the floor), naming the row in its score:row where `tagged`."""
    folder.mkdir()
    inputs = toy_inputs(folder, ROWS + [{"id": "sea", "name": "sea", "noun": "sea"}])
    (folder / "terrain/earth/places").mkdir(parents=True)
    ground = Usd.Stage.CreateNew(str(folder / f"terrain/earth/places/{PLACE}.usdc"))
    spots = np.stack(np.meshgrid(np.arange(41) * 0.5, np.arange(41) * 0.5, indexing="ij"), axis=-1).reshape(-1, 2)
    mesh = UsdGeom.Mesh.Define(ground, f"/{PLACE}/Outside/water")
    mesh.GetPointsAttr().Set([Gf.Vec3f(float(x) + 8.0, -1.0, float(z) - 10.0) for x, z in spots])
    cells = [(row * 41 + column, row * 41 + column + 1, (row + 1) * 41 + column + 1, (row + 1) * 41 + column)
             for row in range(40) for column in range(40)]
    mesh.GetFaceVertexCountsAttr().Set([3] * (2 * len(cells)))
    mesh.GetFaceVertexIndicesAttr().Set([corner for a, b, c, d in cells for corner in (a, b, c, a, c, d)])
    if tagged:
        mesh.GetPrim().CreateAttribute("score:row", Sdf.ValueTypeNames.String).Set("sea")
    ground.GetRootLayer().Save()
    return dict(inputs, terrain=folder / "terrain")


def sea_heights(out, inputs, second):
    """The sea sheet's heights at a second, its motion layer over the terrain's ground."""
    root = Sdf.Layer.CreateAnonymous(".usda")
    root.subLayerPaths = [str(out / "layers/motion.usda"), str(inputs["terrain"] / f"earth/places/{PLACE}.usdc")]
    stage = Usd.Stage.Open(root)
    points = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{PLACE}/Outside/water")).GetPointsAttr()
    return np.asarray(points.Get(second * 24.0), dtype=float)[:, 1]


def a_gap(path, check, objects):
    """A place's gaps file (score/stages/gaps.py) with one accepted gap moving `check`'s faults of `objects`."""
    path.write_text(json.dumps({"gaps": [{"name": "not built yet", "row": "motion", "check": check, "objects": objects,
                                          "reason": "no maker builds it (#88)", "decided": "test", "faults": []}]}))
    return path


def table_judge(name, out, inputs):
    """A gate as the stage table runs it, batch gaps moved (stages.accepted_gaps, BATCH_GATES)."""
    from score import stages
    row = stages.accepted_gaps(stages.MOTION)
    return next(check for check in row.checks if check.name == name).judge(out, inputs, None)



def a_baked_door(bake, paint, out, models=None):
    """The bake's door_1 written as the assembly's asset of it (baked.take_bake's place, its repaint left out): a leaf
    0.9 m wide, 2 m tall and 0.1 m thick."""
    stage = Usd.Stage.CreateNew(str(pathlib.Path(out) / "assets/door_1.usdc"))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/door_1").GetPrim())
    box(stage, "/door_1/leaf", (-0.45, 0.0, -0.05), (0.45, 2.0, 0.05))
    stage.GetRootLayer().Save()



# A post standing in the quarter the door sweeps opening its rule's way (rotateY +90: from +x of its hinge (2.55, 1)
# toward -z): its corner (2.8, 0.6) lies 0.47 m from the hinge, inside the leaf's 0.9 m; and its mirror over the
# door's line (z = 1), in the quarter it sweeps the other way.
POST = ("wall_2", (3.0, 0.0, 0.4), (-0.2, 0.0, -0.2), (0.2, 1.0, 0.2))
MIRROR = ("wall_3", (3.0, 0.0, 1.6), (-0.2, 0.0, -0.2), (0.2, 1.0, 0.2))


# A wall behind the sliding door along its whole travel either way, and a post 0.3 m past its +x end; a second walker
# along x = -4 from z = 0 to 6 passes it from 2.2 s to its walk's end at 4.5 s.
BEHIND = ("wall_4", (-3.6, 0.0, 4.15), (-2.4, 0.0, -0.1), (2.4, 2.5, 0.1))
PAST = ("wall_5", (-2.9, 0.0, 3.9), (-0.2, 0.0, -0.1), (0.2, 1.0, 0.1))
SLIDER = {"name": "astronaut_2", "doing": "walking", "at": [-4.0, 0.0, 0.0], "turn": 0.0, "pace": 1.333,
          "path": [[-4.0, 0.0, 0.0], [-4.0, 0.0, 6.0]]}



def parted(folder, name, at, row, turn=0.0):
    """A parted build (score/stages/props/moving_parts) on the toy's base layer as the route lays it: an object Xform
    at `at` turned `turn` degrees about up, each node of its model an Xform of its own name at its node's origin
    holding its mesh."""
    from score.stages.props import moving_parts
    scene, _ = moving_parts.build(row, from_design.row_kinds.table())
    stage = Usd.Stage.Open(str(pathlib.Path(folder) / "seeds" / PLACE / "layers/base.usda"))
    xform = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
    xform.AddTranslateOp().Set(Gf.Vec3d(*at))
    xform.AddRotateYOp().Set(turn)
    for node in scene.graph.nodes_geometry:
        placed, geometry = scene.graph[node]
        mesh = scene.geometry[geometry]
        part = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}/{node}")
        part.AddTranslateOp().Set(Gf.Vec3d(*(float(value) for value in placed[:3, 3])))
        drawn = UsdGeom.Mesh.Define(stage, f"/{PLACE}/Objects/{name}/{node}/mesh")
        drawn.GetPointsAttr().Set([Gf.Vec3f(*(float(value) for value in point)) for point in mesh.vertices])
        drawn.GetFaceVertexCountsAttr().Set([3] * len(mesh.faces))
        drawn.GetFaceVertexIndicesAttr().Set([int(index) for index in mesh.faces.flatten()])
    stage.GetRootLayer().Save()



def a_flag(stage, path):
    """A flag on its pole as one mesh: its pole a 2 cm post 1 m tall on its own upright line, its cloth a 0.5 x 0.4 m
    sheet of 10 x 8 squares off the pole's top toward +x, each a GeomSubset named by its library surface as a bake
    names it (`<library surface>__<finish>`)."""
    post = [(x, y, z) for y in (0.0, 1.0) for x in (-0.01, 0.01) for z in (-0.01, 0.01)]
    sides = [(0, 1, 5), (0, 5, 4), (2, 3, 7), (2, 7, 6), (0, 2, 6), (0, 6, 4), (1, 3, 7), (1, 7, 5)]
    sheet = [(0.05 * column, 0.6 + 0.05 * row, 0.0) for row in range(9) for column in range(11)]
    squares = [(8 + row * 11 + column, 8 + row * 11 + column + 1, 8 + (row + 1) * 11 + column + 1,
                8 + (row + 1) * 11 + column) for row in range(8) for column in range(10)]
    faces = sides + [tri for a, b, c, d in squares for tri in ((a, b, c), (a, c, d))]
    mesh = UsdGeom.Mesh.Define(stage, path)
    mesh.GetPointsAttr().Set([Gf.Vec3f(*point) for point in post + sheet])
    mesh.GetFaceVertexCountsAttr().Set([3] * len(faces))
    mesh.GetFaceVertexIndicesAttr().Set([index for face in faces for index in face])
    for name, chosen in (("pole_iron__iron_r050", range(len(sides))), ("flag_cloth__red_r085",
                                                                         range(len(sides), len(faces)))):
        subset = UsdGeom.Subset.Define(stage, f"{path}/{name.split('__')[0]}")
        subset.GetIndicesAttr().Set(list(chosen))
        subset.GetElementTypeAttr().Set(UsdGeom.Tokens.face)
        subset.GetPrim().CreateAttribute("score:surface", Sdf.ValueTypeNames.String).Set(name)


def flag_inputs(folder, recipe="cloth"):
    """The toy place with a red flag's row and one flag at (4, 0, -4) whose cloth's library surface is made with
    `recipe`, its surface bake's specs and the flag cloth's files."""
    from score.stages.motion import cloth
    inputs = toy_inputs(folder, ROWS + [{"id": "flag", "name": "red flag", "noun": "flag"}])
    stage = Usd.Stage.Open(str(inputs["seed"] / "layers/base.usda"))
    UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/flag_1").AddTranslateOp().Set(Gf.Vec3d(4.0, 0.0, -4.0))
    a_flag(stage, f"/{PLACE}/Objects/flag_1/geo")
    stage.GetRootLayer().Save()
    (folder / "bake").mkdir()
    (folder / "bake/specs.json").write_text(json.dumps({"flag_cloth": {"recipe": recipe, "thread": 0.003},
                                                        "pole_iron": {"recipe": "metal"}}))
    roots = {"data": str(REPO / "data"), "repo": str(REPO)}
    return dict(inputs, **{name: pathlib.Path(pattern.format(**roots)) for name, pattern in cloth.FILES.items()},
                **{"surfaces-bake": folder / "bake"})


def a_written_run(turn):
    """A cloth run as Newton's would come back, written here (Newton is not run in the test): the grid's nodes swung
    about the pole's upright line by `turn` times sin(pi t) radians at t seconds, the pinned column on it standing."""
    def ran(job, folder):
        points = np.asarray(job["points"])
        angles = turn * np.sin(np.pi * np.arange(job["frames"]) / job["rate"])
        sine, cosine = np.sin(angles)[:, None], np.cos(angles)[:, None]
        swung = np.stack([points[:, 0] * cosine + points[:, 2] * sine, np.broadcast_to(points[:, 1], (len(angles), len(points))),
                          -points[:, 0] * sine + points[:, 2] * cosine], axis=2)
        return swung, "a written run"
    return ran


def waved_out(inputs, folder, run):
    """The motion row's output for the flag place, its flag waved by `run`: motion.make, then cloth.waved."""
    from score.stages.motion import cloth
    out, record = made(inputs, folder)
    with motion.built(inputs) as source:
        found = cloth.waved(record, inputs, source, out / "layers/motion.usda", run)
    (out / motion.RECORD).write_text(json.dumps(found))
    return out, record, found


def test_covered_asks_for_the_design_s_moving_rows_only(tmp_path):
    """A ship named as an old record's moving kind, on a craft row that stands with its written reason, is not asked
    for (3 moving kinds: door, fan, rover); the design's door taken out of the record (neither moved nor standing with
    a reason) fails by name. Fault (the audit of 2026-11-04): a row no kind moves was invisible to every gate (the
    launching rocket, flags, a body of water, 102 screens). A launching rocket in the sky over Earth climbs straight
    up at the middle of its kind's cited push, (11.13 + 13.84) / 2 = 12.485 m/s/s, less Earth's 9.82: 2.665 m/s/s,
    so 0.5 * 2.665 * 20^2 = 533 m risen in the 20 s round, and `speeds`, `grounded` and the check pass it; its
    exhaust (no effect kind makes it) and a wind turbine (a moving word no kind moves) each fail `covered` by name,
    and a design holding only the turbine has the motion row, so the fault is judged; a screen is not among them, its
    picture the screens stage's (data/checks/screens.json `read_by` over row-kinds.json's null, #88). A launch written with no pull taken off climbs at the whole 12.485 m/s/s, which with Earth's pull is a
    push of 22.3, over the kind's: `speeds` fails it. On the Moon (3e-13 kPa of air, the reference table's) the flag hangs still with its reason and the
    rocket (12.485 over 1.624) climbs off its pad on the floor, `grounded` reading it once it has risen half a metre; under a body pulling 15 m/s/s it stands, its push not lifting it.
    Break: score/stages/motion/__init__.py: `if path not in moved and path not in still and path.rsplit("/", 1)[-1] not
        in still]` -> `if False]`
    Break: score/stages/motion/from_design.py: `unmade.append(f"{path}: {rule['move']}, which no writer makes:
        {rule['why']}")` -> `still[path] = rule["why"]`
    Break: score/stages/row_kinds.py: `if heard and not done & {"moves", "loose"} and not (kind and
        kinds[kind].get("stands")):` -> `if False:`
    Break: score/stages/design_layers.py: `return found | {"motion"} if row_kinds.uncovered(inventory, kinds) else
        found` -> `return found`
    Break: score/stages/motion/__init__.py: in coverage, `**read_json(inputs["screens"])["read_by"]` dropped (the
        screen fails `covered` again)
    Break: score/stages/motion/from_design.py: `"climb": {"lift": 0.0, "push": round(push, 4), "pull":
        float(body["gravity"])},` -> `"climb": {"lift": 0.0, "push": round(push, 4), "pull": 0.0},`
    Break: score/stages/motion/__init__.py: `push = 2.0 * risen / (seconds - lift) ** 2 + float(body["gravity"])` ->
        `push = 2.0 * risen / (seconds - lift) ** 2 + float(entry["climb"]["pull"])`
    Break: score/stages/motion/from_design.py: `return [f"{path}: exhaust, {rule['exhaust']}"] if rule.get("exhaust")
        else []` -> `return []`
    Break: score/stages/motion/from_design.py: `elif rule.get("airless") and airless(body):` -> `elif False:`
    A recorded gap naming the exhaust's rocket and the turbine moves `covered`'s faults; one naming the turbine alone
    leaves the rocket's fault failing it.
    Break: score/stages/__init__.py: `"motion": ("designed", "covered"),` -> `"motion": ("designed",),`
    Break: score/stages/motion/__init__.py: `for moment in np.arange(np.ceil(climbed_from(entry)), seconds + 1e-9,
        1.0):` ->
        `for moment in np.arange(0.0, seconds + 1e-9, 1.0):`
    The library's exhaust (data/effects/exhaust.json, motion@square 2026-11-12) drawn for the launch takes its line
    off `unmade`: its flame 0.67 rocket heights at 3 s (2.01 m under the 3 m rocket), its core 0.2 (0.6 m), its smoke
    column of puffs, its flame held under the climbing rocket's foot, so `covered` passes with only the turbine's gap;
    one drawn at 0.3 rocket heights (under the footage's 0.45), its flame taken off the layer and the whole exhaust
    taken off each fail it by name.
    Break: score/stages/motion/exhaust.py: `move.Set(Gf.Vec3d(*foot_at(stage, rocket, code)), code)` ->
        `move.Set(Gf.Vec3d(*foot_at(stage, rocket, 0.0)), code)`
    Break: score/stages/motion/exhaust.py: `if not low <= share <= high:` -> `if False:`
    Break: score/stages/motion/exhaust.py: `if not prim or prim.GetAttribute("score:effect:kind").Get() != KIND:` ->
        `if False:`
    Break: score/stages/__init__.py: `"covered": exhaust.judge_covered` dropped from MOTION_JUDGES
    A red flag on its pole on Earth (#88), its cloth's library surface made with the cloth table's `cloth` recipe: the
    rigid make leaves it unmade, and the flag cloth (cloth.py) waves it from a run written here (Newton is not run):
    its unmade line goes, its cloth grid pins the 21 nodes on the pole's line, its 8 pole points ride the pole and
    its 99 cloth points the cloth, and the table's `covered` passes it waving as UsdSkel skins it, `moving area`,
    `steps`, `follows` and `designed` passing too; a run that stands still fails `covered` by the flag's name; a flag
    whose surface's recipe the cloth table does not hold keeps its unmade line, with why.
    Break: score/stages/motion/cloth.py: `if off.max() < MOVED_LEAST:` -> `if False:`
    Break: score/stages/motion/cloth.py: `for line in record["unmade"] if line.split(":", 1)[0] not in waving]` ->
        `for line in record["unmade"]]`
    Break: score/stages/motion/cloth.py: `if recipe in table)` -> `if recipe)`
    Break: score/stages/motion/cloth_layer.py: `skeleton.SetInfo("apiSchemas", ...)` dropped (the skeleton plays no
        animation: the flag stands)
    Break: score/stages/motion/cloth_rig.py: `"pinned": index[:, 0] == 0` -> `"pinned": index[:, 0] < 0`
    Break: score/stages/__init__.py: `motion_cloth.covering(exhaust.judge_covered)` -> `exhaust.judge_covered`"""
    from score.stages import design_layers
    ship = ("ship_1", (-4.0, 0.0, 0.0), (-0.5, 0.0, -0.5), (0.5, 3.0, 0.5))
    inputs = toy_inputs(tmp_path, ROWS + [{"id": "ship", "name": "ship", "noun": "ship"}], extra=(ship,))
    out, record = made(inputs, tmp_path)
    kept = judge("covered", out, inputs)
    (out / motion.RECORD).write_text(json.dumps(dict(record, moves=[entry for entry in record["moves"]
                                                                    if entry["name"] != "door_1"])))
    dropped = judge("covered", out, inputs)
    assert kept.answer == checks.PASS and kept.measures["moving kinds"] == 3, (kept.reason, kept.findings)
    assert dropped.answer == checks.FAIL and dropped.findings == (f"/{PLACE}/Objects/door_1 (door)",), dropped.findings
    unmade = [{"id": "rocket", "name": "launching rocket", "noun": "rocket"},
              {"id": "turbine", "name": "wind turbine", "noun": "turbine"},
              {"id": "screen", "name": "wall screen", "noun": "screen"}]
    rocket = ("rocket_1", (-4.0, 10.0, -4.0), (-0.5, 0.0, -0.5), (0.5, 3.0, 0.5))  # in the sky, as the reading anchors it
    (tmp_path / "unmade").mkdir()
    inputs = toy_inputs(tmp_path / "unmade", ROWS + unmade, extra=(rocket,))
    out, record = made(inputs, tmp_path / "unmade")
    verdict = judge("covered", out, inputs)
    launch = next(entry for entry in record["moves"] if entry["name"] == "rocket_1")
    risen = middle_at(out, inputs, f"/{PLACE}/Objects/rocket_1", 20.0) - middle_at(out, inputs,
                                                                                  f"/{PLACE}/Objects/rocket_1", 0.0)
    assert launch["climb"] == {"lift": 0.0, "push": 12.485, "pull": 9.82} and not launch["loop"], launch
    assert np.allclose(risen, [0.0, 533.0, 0.0], atol=0.01), risen
    for name in ("speeds", "grounded", "follows", "steps"):
        assert judge(name, out, inputs).answer == checks.PASS, (name, judge(name, out, inputs).findings)
    assert abs(judge("speeds", out, inputs).measures["rocket_1 push"] - 12.485) < 0.01
    assert verdict.answer == checks.FAIL, verdict.reason
    assert [line.split(":", 2)[:2] for line in verdict.findings] == [
        [f"/{PLACE}/Objects/rocket_1", " exhaust, its exhaust's flame and smoke under it, which no effect kind makes "
         "yet (data/checks/effects.json measures no rocket exhaust on footage)"], ["turbine", " \"wind turbine\" names a moving thing (turbine), and its kind (none) gives it no move and no written reason to stand (data/checks/row-kinds.json)"]], verdict.findings
    assert "motion" in design_layers.kinds_of({"rows": [unmade[1]]})
    for objects, answer in (([f"/{PLACE}/Objects/rocket_1", "turbine"], checks.PASS), (["turbine"], checks.FAIL)):
        gapped = dict(inputs, gaps=a_gap(tmp_path / "unmade" / "gaps.json", "covered", objects))
        assert table_judge("covered", out, gapped).answer == answer, (objects, table_judge("covered", out, gapped))
    exhausted = dict(inputs, exhaust=REPO / "data/effects/exhaust.json",
                     gaps=a_gap(tmp_path / "unmade" / "turbine.json", "covered", ["turbine"]))
    short = json.loads(exhausted["exhaust"].read_text())
    (tmp_path / "short.json").write_text(json.dumps(dict(short, flame=dict(short["flame"], length=[[3.0, 0.3]]))))
    shutil.copytree(out, tmp_path / "short")
    for folder, recipe in ((out, exhausted["exhaust"]), (tmp_path / "short", tmp_path / "short.json")):
        with motion.built(exhausted) as source:
            exhaust.write(dict(exhausted, exhaust=recipe), folder, source)
    drawn = json.loads((out / motion.RECORD).read_text())
    rocket_exhaust = drawn["exhaust"][f"/{PLACE}/Objects/rocket_1"]
    assert not [line for line in drawn["unmade"] if "rocket_1" in line], drawn["unmade"]
    assert rocket_exhaust["flame"]["length"][1] == [3.0, 2.01] and rocket_exhaust["core"]["length"] == [[3.0, 0.6]]
    assert rocket_exhaust["puffs"] > 1, rocket_exhaust
    passed = table_judge("covered", out, exhausted)
    assert passed.answer == checks.PASS and passed.measures["exhausts"] == 1, (passed.reason, passed.findings)
    shortened = table_judge("covered", tmp_path / "short", exhausted)
    assert shortened.answer == checks.FAIL and "flame length 3 s after lift-off 0.30" in " ".join(
        shortened.findings), shortened.findings
    flame = f"/{PLACE}/Effects/rocket_1_exhaust/flame"
    layer = Sdf.Layer.FindOrOpen(str(out / "layers/motion.usda"))
    Usd.Stage.Open(layer).RemovePrim(flame)
    layer.Save()
    dropped = table_judge("covered", out, exhausted)
    assert dropped.answer == checks.FAIL and dropped.findings[-1].endswith("its flame is not drawn"), dropped.findings
    Usd.Stage.Open(layer).RemovePrim(f"/{PLACE}/Effects/rocket_1_exhaust")
    layer.Save()
    gone = table_judge("covered", out, exhausted)
    assert gone.answer == checks.FAIL and gone.findings[-1].endswith("stands on the stage"), gone.findings
    unpulled = dict(record, moves=[dict(entry, climb=dict(entry["climb"], pull=0.0)) if "climb" in entry else entry
                                   for entry in record["moves"]])
    (tmp_path / "unpulled").mkdir()
    (tmp_path / "unpulled" / motion.RECORD).write_text(json.dumps(unpulled))
    motion.write_motion(dict(inputs, moves=tmp_path / "unpulled" / motion.RECORD), tmp_path / "unpulled",
                        inputs["seed"])
    shutil.copy(out / "moved.json", tmp_path / "unpulled" / "moved.json")
    assert judge("speeds", tmp_path / "unpulled", inputs).answer == checks.FAIL
    flag = [{"id": "flag", "name": "flag", "noun": "flag"}, unmade[0]]
    for name, sky in (("moon", a_sky("moon", 1.624)), ("heavy", a_sky("heavy", 15.0))):
        (tmp_path / name).mkdir()
        pad = ("rocket_1", (-4.0, 0.0, -4.0), (-0.5, 0.0, -0.5), (0.5, 3.0, 0.5))
        flagged = toy_inputs(tmp_path / name, ROWS + flag, extra=(pad, ("flag_1", (4.0, 0.0, -4.0),
                                                                       (-0.5, 0.0, -0.05), (0.5, 1.0, 0.05))), sky=sky)
        lifted, found = made(flagged, tmp_path / name)
        moved = [entry["name"] for entry in found["moves"]]
        if name == "moon":
            assert found["still"].get(f"/{PLACE}/Objects/flag_1", "").startswith(
                "it hangs still: no air stands on its body to wave it (Moon: 3e-13 kPa)"), found["still"]
            assert "rocket_1" in moved and judge("grounded", lifted, flagged).answer == checks.PASS
        else:
            assert "rocket_1" not in moved and "does not lift it off" in found["still"][f"/{PLACE}/Objects/rocket_1"]
    flag = f"/{PLACE}/Objects/flag_1"
    for name, turn in (("waving", 0.5), ("standing", 0.0)):
        (tmp_path / name).mkdir()
        flagged = flag_inputs(tmp_path / name)
        out, rigid, found = waved_out(flagged, tmp_path / name, a_written_run(turn))
        verdict = table_judge("covered", out, flagged)
        assert [line.split(":", 1)[0] for line in rigid["unmade"]] == [flag], rigid["unmade"]
        assert found["unmade"] == [] and found["cloth"][flag]["mesh"] == f"{flag}/geo", found
        run = found["cloth runs"][found["cloth"][flag]["run"]]
        assert run["recipe"] == "cloth" and run["measures"]["pinned nodes"] == 21, run
        assert run["measures"]["pole points"] == 8 and run["measures"]["cloth points"] == 99, run["measures"]
        if name == "waving":
            assert verdict.answer == checks.PASS and verdict.measures["waving cloth"] == 1, (verdict.reason,
                                                                                            verdict.findings)
            for gate in ("moving area", "steps", "follows", "designed"):
                assert table_judge(gate, out, flagged).answer == checks.PASS, table_judge(gate, out, flagged)
        else:
            assert verdict.answer == checks.FAIL and verdict.findings[0].startswith(
                f"{flag}: its cloth reaches only 0.000 m off its start"), verdict.findings
    (tmp_path / "metal").mkdir()
    unwoven = flag_inputs(tmp_path / "metal", recipe="metal")
    _, _, found = waved_out(unwoven, tmp_path / "metal", a_written_run(0.5))
    assert len(found["unmade"]) == 1 and found["unmade"][0].endswith(
        "(no part of it has a library surface whose recipe the cloth table holds)") and not found["cloth"], found



# --- the motion check on a written record ---------------------------------------------------------------------------

RECORD = {"place": PLACE, "seconds": 12.0, "moves": [
    {"name": "cart_round", "prim": f"/{PLACE}/Objects/cart_1", "kind": "rover", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "path": {"points": [[0, 0], [3, 0], [3, 3], [0, 3]], "relative": True}},
    {"name": "door_swing", "prim": f"/{PLACE}/Objects/door_1", "kind": "hatch", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "swing": {"about": "Objects/hinge_1", "angle": 90.0, "speed": 45.0, "starts": "shut",
               "moves": [[1.0, "open"], [6.0, "shut"]]}},
    {"name": "hatch_slide", "prim": f"/{PLACE}/Objects/hatch_1", "kind": "hatch", "on": "rail", "start": 0.0,
     "length": 12.0, "loop": True,
     "slide": {"by": [0.0, -1.0, 0.0], "speed": 0.5, "starts": "shut", "moves": [[1.0, "open"], [6.0, "shut"]]}}]}
# A wall at x = 8 to 8.3; a cart, a door on its hinge post, a hatch and a crate, each standing on its own origin.
CHECKED = [(name, at, (-size[0] / 2, 0.0, -size[2] / 2), (size[0] / 2, size[1], size[2] / 2))
           for name, at, size in (("cart_1", (0.0, 0.05, 0.0), (1.0, 0.8, 1.0)),
                                  ("door_1", (-4.0, 0.0, -4.0), (1.0, 2.0, 0.1)),
                                  ("hinge_1", (-4.55, 0.0, -4.0), (0.1, 2.0, 0.1)),
                                  ("hatch_1", (5.0, 0.0, -4.0), (1.0, 0.1, 1.0)),
                                  ("crate_1", (-4.0, 0.0, 3.0), (0.6, 0.6, 0.6)))]


def checked_place(folder, record=RECORD):
    """The checked place's seed and its motion layer written from `record` (the stage makes its own from the design:
    from_design.py), the record kept as the output's."""
    seed = a_seed(folder, {"wall": ((8.0, 0.0, -2.0), (8.3, 3.0, 6.0))}, CHECKED)
    out = pathlib.Path(folder) / "out"
    out.mkdir()
    (out / motion.RECORD).write_text(json.dumps(record))
    motion.write_motion({"kinds": REPO / "data/checks/motion.json", "seed": seed, "moves": out / motion.RECORD}, out,
                        seed)
    return seed, out


def judged(output, seed, record, name):
    """The named gate judged against `record` as the output's record."""
    (pathlib.Path(output) / motion.RECORD).write_text(json.dumps(record))
    check = next(check for check in motion.CHECKS if check.name == name)
    return check.judge(output, {"kinds": REPO / "data/checks/motion.json", "seed": seed}, None)


def motion_layer(output):
    return Sdf.Layer.FindOrOpen(str(pathlib.Path(output) / "layers/motion.usda"))


def a_frame_thrown_aside(output):
    """One frame of the cart's drive thrown 2 m aside in the layer."""
    layer = motion_layer(output)
    moved = layer.GetAttributeAtPath(f"/{PLACE}/Objects/cart_1.xformOp:translate:path")
    code = sorted(layer.ListTimeSamplesForPath(moved.path))[40]
    spot = layer.QueryTimeSample(moved.path, code)
    layer.SetTimeSample(moved.path, code, Gf.Vec3d(spot[0] + 2.0, spot[1], spot[2]))
    layer.Save()


def a_stray_crate_and_a_still_door(output):
    """The layer moves the crate, which no record names, and the door's turn is taken out of it."""
    layer = motion_layer(output)
    crate = Sdf.CreatePrimInLayer(layer, f"/{PLACE}/Objects/crate_1")
    crate.specifier = Sdf.SpecifierOver
    shift = Sdf.AttributeSpec(crate, "xformOp:translate", Sdf.ValueTypeNames.Double3)
    layer.SetTimeSample(shift.path, 0.0, Gf.Vec3d(-4.0, 0.0, 3.0))
    layer.SetTimeSample(shift.path, 48.0, Gf.Vec3d(-3.0, 0.0, 3.0))
    swung = layer.GetAttributeAtPath(f"/{PLACE}/Objects/door_1.xformOp:rotateY:swing")
    for sample in layer.ListTimeSamplesForPath(swung.path):
        layer.EraseTimeSample(swung.path, sample)
    layer.Save()


def recorded(change):
    """RECORD with `change` applied to a deep copy of it."""
    record = copy.deepcopy(RECORD)
    change(record)
    return record


# The cart's path laid out to x = 9, through the wall at x = 8.
THROUGH = recorded(lambda record: record["moves"][0]["path"].update(points=[[0, 0], [9, 0], [9, 3], [0, 3]]))


# A thin post 0.6 m out from the door's hinge at 70 degrees of its rule's way (rotateY +90, toward -z): the leaf turned
# 70 degrees or more sweeps through it, turned 60 it stays 0.05 m clear; with MIRROR the other way strikes at every
# angle, so the swing is fitted to 60 degrees its rule's way, the least it is tried at.
STOP = ("wall_6", (2.755, 0.0, 0.436), (-0.02, 0.0, -0.02), (0.02, 1.0, 0.02))
CRANE = {"id": "crane", "name": "crane", "noun": "crane"}
HATCHES = [{"id": "hatch", "name": "floor hatch", "noun": "hatch"}, {"id": "open_flat", "name": "open hatch", "noun": "hatch"}]
FLAT = ("hatch_1", (-1.0, 0.0, -1.0), (-0.3, 0.0, -0.3), (0.3, 0.1, 0.3))
FLAT_OPEN = ("open_flat_1", (1.0, 0.0, -4.0), (-0.3, 0.0, -0.3), (0.3, 0.1, 0.3))
DOUBLE = {"id": "double_door", "name": "double door", "noun": "door", "size": [1.6, 0.1, 2.1]}
LID = {"id": "open_hatch", "name": "open floor hatch", "noun": "hatch", "size": [0.6, 0.6, 0.1]}
WALKED = {"id": "floor_hatch", "name": "floor hatch", "noun": "hatch", "size": [0.6, 0.6, 0.1]}
WAITING_DOOR = {"name": "door_1", "row": "door", "bake": "door_1", "kind": "object", "at": [3.0, 0.0, 1.0],
                "rotation": [0.0, 0.0, 0.0, 1.0], "waiting": "its model door_1 comes from the surface line's bake",
                "on": {"how": "in", "middle": [3.0, 0.0, 1.0], "along": [1.0, 0.0], "wide": 0.9, "tall": 2.0,
                       "why": "opening"}}


def objects(*names):
    """The prim paths of the toy's objects."""
    return [f"/{PLACE}/Objects/{name}" for name in names]


def gate(answer, *findings, reason=None):
    """A gate's expected verdict: its answer, patterns each found in its findings (one per line, re.M), and a pattern
    found in its reason."""
    return {"answer": answer, "findings": findings, "reason": reason}


def exactly(text):
    """A pattern matching `text` whole."""
    return re.compile(re.escape(text) + r"\Z", re.S)


def starting(text, then=""):
    """A pattern matching a text that starts with `text`, then holds `then` (a pattern) somewhere after."""
    return re.compile(re.escape(text) + ".*" + then + ".*", re.S)


def holding(text):
    """A pattern matching a text that holds `text`."""
    return re.compile(".*" + re.escape(text) + ".*", re.S)


EVERY = "every gate"
MOVED_ON = holding("moved to complete")
# The hatch kind's swing on the old fixed clock (a swing open at 2 s, shut at 10 s, every round) and a sliding door
# written as that swing; an open hatch written lifting.
CLOCK = {"name": "door_1", "prim": f"/{PLACE}/Objects/door_1", "row": "door", "kind": "hatch", "on": "rail",
         "start": 0.0, "length": 20.0, "loop": True,
         "swing": {"about": {"side": [-1.0, 0.0, 0.0]}, "angle": 90.0, "speed": 34.0, "starts": "shut",
                   "moves": [[2.0, "open"], [10.0, "shut"]]}}
LIFTED = {"name": "open_flat_1", "prim": f"/{PLACE}/Objects/open_flat_1", "row": "open_flat", "kind": "hatch",
          "on": "rail", "start": 0.0, "length": 20.0, "loop": True,
          "slide": {"by": [0.0, 0.5, 0.0], "speed": 0.5, "starts": "shut", "moves": [[2.0, "open"]]}}
LEAF = f"/{PLACE}/Objects/double_door_1/leaf_left__hinge_y"
CARRIED_BAKE_GAP = {"gaps": [{
    "name": "toy_crane_b26f85f9: not baked", "row": "surfaces-bake", "check": "baked", "objects": ["toy_crane_b26f85f9"],
    "faults": ["toy_crane_b26f85f9: its bake job brought nothing back"],
    "reason": "the take's bake job ran once in the batch and failed"}]}
PLAN = {"gaps": [{"kind": "placed", "item": "crane", "row": "crane", "words": "crane: 1 in the concept, 0 on the plan"},
                 {"kind": "outside", "item": "FAN 1", "row": "fan", "words": "fan 1 sticks out of the place"}]}

# Each case is one world and what it must show. The world: `toy` (toy_inputs' arguments: the design made into the
# record and layer by motion.make), with `files` written into its folder, `inputs` pointing at them, `parted` builds
# laid on its base layer; or `written` (the checked place's layer written from one record, judged against another,
# an edit made to the written layer). What it shows: `record` (paths into the record, `moves` and `posed` by name, to a
# value or a pattern; a dict is compared by its sorted keys to a list), `carried` (the output's batch gaps' names),
# `middles` (a prim's middle at a second: near a spot, or one axis under or over a number or another middle),
# `gates` (gate name, `table:` for the stage table's, `every gate` for each motion gate, to its verdict), `rewrites`
# (moves added to or dropped from the record and the gates judged on it), and `reseeded` (made again with another
# seed: the same bytes).
CASES = [
    ("a door swings on its hinge for the walker, the fan turns and the rover stands", {
        "toy": {}, "reseeded": True,
        "record": [(("moves",), ["door_1", "fan_1"]), (("still",), objects("rover_1")),
                   (("moves", "door_1", "swing", "speed"), 34.0), (("moves", "door_1", "swing", "angle"), 90.0),
                   (("moves", "door_1", "swing", "moves"), [[0.0, "open"], [3.7, "shut"]]),
                   (("moves", "door_1", "loop"), False), (("moves", "fan_1", "spin", "speed"), 738.0)],
        "middles": [(f"/{PLACE}/Objects/door_1", 8.0, None, "near", ((3.0, 1.0, 1.0), 1e-6)),
                    (f"/{PLACE}/Objects/door_1", 3.0, None, "near", ((2.55, 1.0, 0.55), 1e-4))],
        "gates": {EVERY: gate(checks.PASS)}}),
    ("with nobody walking the doors stand as their words say", {
        "toy": {"rows": ROWS + WORDED, "extra": (OPEN_DOOR, SLIDING_DOOR), "cast": (SEATED,)},
        "record": [(("moves",), ["fan_1"]),
                   (("still", f"/{PLACE}/Objects/door_1"), starting("nobody passes through it")),
                   (("still", f"/{PLACE}/Objects/sliding_door_1"), starting("nobody passes through it")),
                   (("posed",), ["open_door_1"]),
                   (("still", f"/{PLACE}/Objects/open_door_1"), starting("it stands open"))],
        "middles": [(f"/{PLACE}/Objects/open_door_1", 5.0, 2, "<", -0.4)],  # turned off its wall line
        "gates": {name: gate(checks.PASS) for name in ("passed", "rests", "moving area", "covered")},
        "rewrites": [({"add": [CLOCK, dict(CLOCK, name="sliding_door_1", prim=f"/{PLACE}/Objects/sliding_door_1",
                                           row="sliding_door")]},
                      {"passed": gate(checks.FAIL, r"\A" + re.escape("door_1: off its rest from 2.0 to 12.6 s, and no walker")),
                       "rests": gate(checks.FAIL, re.escape("sliding_door_1: its row says sliding, yet it swings"))})]}),
    ("with no cast at all every door stands", {"toy": {"cast": ()}, "record": [(("moves",), ["fan_1"])]}),
    ("a door that strikes its rule's way swings the other, a sliding door slides the other way", {
        "toy": {"rows": ROWS + WORDED[1:], "extra": (POST, SLIDING_DOOR, BEHIND, PAST), "cast": (WALKER, SLIDER)},
        "record": [(("moves", "door_1", "swing", "angle"), -90.0),
                   (("moves", "door_1", "from"), holding("fitted by the clear gate")),
                   (("moves", "sliding_door_1", "slide", "by"), [-1.2, 0.0, 0.0]),
                   (("moves", "sliding_door_1", "slide", "moves"), [[0.0, "open"], [4.138, "shut"]])],
        "middles": [(f"/{PLACE}/Objects/door_1", 3.0, None, "near", ((2.55, 1.0, 1.45), 1e-4)),
                    (f"/{PLACE}/Objects/sliding_door_1", 2.0, None, "near", ((-4.58, 1.05, 4.0), 1e-4))],
        "gates": {EVERY: gate(checks.PASS)}}),
    ("a door that strikes every way stands with its strike", {
        "toy": {"extra": (POST, MIRROR)},
        "record": [(("moves",), ["fan_1"]), (("still", f"/{PLACE}/Objects/door_1"),
                                             starting("it strikes at every way it was tried", "wall_"))],
        "gates": {"clear": gate(checks.PASS)}}),
    ("a door clear only at sixty degrees its rule's way swings sixty", {
        "toy": {"extra": (STOP, MIRROR)},
        "record": [(("moves", "door_1", "swing", "angle"), 60.0),
                   (("moves", "door_1", "from"), holding("fitted by the clear gate: 60 degrees its rule's way"))],
        "gates": {"clear": gate(checks.PASS)}}),
    ("a hatch lying flat stands, one whose words say open stands open", {
        "toy": {"rows": ROWS + HATCHES, "extra": (FLAT, FLAT_OPEN)},
        "record": [(("moves",), ["door_1", "fan_1"]),
                   (("still", f"/{PLACE}/Objects/hatch_1"), exactly(from_design.LYING)),
                   (("still", f"/{PLACE}/Objects/open_flat_1"), exactly(from_design.LYING_OPEN))],
        "gates": {"rests": gate(checks.PASS)},
        "rewrites": [({"add": [LIFTED]}, {"rests": gate(checks.FAIL, r"\A" + re.escape(
            f"/{PLACE}/Objects/open_flat_1: its row says open (\"open hatch\"), yet it stands shut or moves") + r"\Z")})]}),
    ("a parted build moves its parts: a double door's leaves, a walked hatch's lid", {
        "toy": {"rows": ROWS + [DOUBLE, LID, WALKED]},
        "parted": [("double_door_1", (3.0, 0.0, -2.0), DOUBLE, 90.0), ("open_hatch_1", (-1.0, 0.0, -1.0), LID, 0.0),
                   ("floor_hatch_1", (3.0, 0.0, 3.5), WALKED, 0.0)],
        "record": [(("moves",), ["door_1", "double_door_1.leaf_left", "double_door_1.leaf_right", "fan_1",
                                 "floor_hatch_1.lid"]),
                   (("moves", "floor_hatch_1.lid", "swing", "axis"), "x"),
                   (("moves", "floor_hatch_1.lid", "swing", "angle"), -90.0),
                   (("moves", "double_door_1.leaf_left", "swing", "angle"), 90.0),
                   (("moves", "double_door_1.leaf_right", "swing", "angle"), -90.0),
                   (("moves", "double_door_1.leaf_left", "swing", "axis"), "y"),
                   (("moves", "double_door_1.leaf_left", "swing", "about"), {"pivot": True}),
                   # 4.5 less 90 / 34; the walk ends at 6.1
                   (("moves", "double_door_1.leaf_left", "swing", "moves"), [[1.853, "open"], [6.1, "shut"]]),
                   (("posed",), ["open_hatch_1.lid"])],
        "middles": [(LEAF, 5.0, 2, "<", (LEAF, 0.0, -0.3)),  # both leaves open to -z
                    (f"/{PLACE}/Objects/double_door_1/leaf_right__hinge_yn", 5.0, 2, "<", (LEAF, 0.0, -0.3)),
                    (f"/{PLACE}/Objects/open_hatch_1/lid__hinge_xn", 5.0, 1, ">", 0.2),
                    (f"/{PLACE}/Objects/floor_hatch_1/lid__hinge_xn", 2.0, 1, ">", 0.2),
                    (f"/{PLACE}/Objects/floor_hatch_1/lid__hinge_xn", 15.0, 1, "<", 0.1)],
        "gates": {EVERY: gate(checks.PASS)}}),
    ("a moving row whose take the bake left out carries its gap", {
        "toy": {"rows": ROWS + [dict(CRANE, thing="prop:toy_crane_b26f85f9")]},
        "files": {"bake/batch-gaps.json": CARRIED_BAKE_GAP}, "inputs": {"surfaces-bake": "bake"},
        "record": [(("left_out",), {"crane": ["toy_crane_b26f85f9: not baked"]})],
        "carried": ["toy_crane_b26f85f9: not baked", "crane: no object, so it does not move"],
        "gates": {"designed": gate(checks.FAIL), "table:designed": gate(checks.PASS, reason=MOVED_ON)}}),
    ("a moving row the accepted plan places none of is left out by its plan gap", {
        "toy": {"rows": ROWS + [CRANE]}, "files": {"plan.json": PLAN}, "inputs": {"plan": "plan.json"},
        "record": [(("left_out", "crane"), [re.compile(  # its source fix waits on #36
            re.escape("crane: the accepted plan's gap \"crane: 1 in the concept, 0 on the plan\" (its source fix: ")
            + r"(?=[^)]*issues/36#issuecomment-)" + re.escape(from_design.PLAN_FIX) + r"\)\Z")])],
        "carried": ["crane: no object, so it does not move"],
        "gates": {"designed": gate(checks.FAIL), "table:designed": gate(checks.PASS, reason=MOVED_ON)}}),
    ("a design's door waiting on its bake stands on the stage and swings", {
        "toy": {"designed": [thing for thing in DESIGNED if thing[0] != "door_1"], "structure": {}},
        "files": {f"record/record/{PLACE}.json": {"place": PLACE, "objects": [WAITING_DOOR]},
                  "bake/baked.json": {"door_1": {}}, "bake/made/door_1.gltf": {}, "kit.json": {"pieces": []},
                  "surfaces.json": {}},
        "inputs": {"scene-record": "record", "kit": "kit.json", "surfaces-bake": "bake", "surfaces-paint": ".",
                   "surfaces": "surfaces.json"},
        "record": [(("missing",), []), (("moves",), ["door_1", "fan_1"])],
        "gates": {"designed": gate(checks.PASS)}}),
    ("the checked place's true motion", {
        "written": (RECORD, RECORD, None),
        "gates": {name: gate(checks.PASS) for name in ("follows", "steps", "moving area", "clear")}}),
    ("the cart judged against a path its layer does not drive", {
        "written": (RECORD, recorded(lambda record: record["moves"][0]["path"]["points"].__setitem__(2, [4.0, 4.0])),
                    None),
        "gates": {"follows": gate(checks.FAIL, r"off its path's curve")}}),
    ("the door judged against a 60 degree swing it does not make", {
        "written": (RECORD, recorded(lambda record: record["moves"][1]["swing"].update(angle=60.0)), None),
        "gates": {"follows": gate(checks.FAIL, r"swings 90\.0 degrees, its record 60\.0")}}),
    ("a frame of the cart thrown 2 m aside", {
        "written": (RECORD, RECORD, a_frame_thrown_aside), "gates": {"steps": gate(checks.FAIL, r"^cart_round: jumps")}}),
    ("a stray crate moving and the door standing still", {
        "written": (RECORD, RECORD, a_stray_crate_and_a_still_door),
        "gates": {"moving area": gate(checks.FAIL, rf"^/{PLACE}/Objects/crate_1: moves, yet no record moves it$",
                                      rf"^/{PLACE}/Objects/door_1: its record moves it, yet it stands still in the "
                                      "stage$")}}),
    ("the cart's path laid through the wall", {
        "written": (THROUGH, THROUGH, None), "gates": {"clear": gate(checks.FAIL, r"Structure/wall")}}),
]


def world(folder, case):
    """The case's world made: (its output, its inputs, its record)."""
    if "written" in case:
        laid, against, edit = case["written"]
        seed, out = checked_place(folder, laid)
        if edit:
            edit(out)
        (out / motion.RECORD).write_text(json.dumps(against))
        return out, {"kinds": REPO / "data/checks/motion.json", "seed": seed}, against
    inputs = toy_inputs(folder, **case["toy"])
    for name, spec in case.get("files", {}).items():
        (folder / name).parent.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(json.dumps(spec))
    inputs.update({key: folder / name for key, name in case.get("inputs", {}).items()})
    for name, at, row, turn in case.get("parted", ()):
        parted(folder, name, at, row, turn)
    out, record = made(inputs, folder)
    return out, inputs, record


def dug(record, path):
    """The record's value at `path`, its moves and posed read by name."""
    value = dict(record, moves={entry["name"]: entry for entry in record["moves"]},
                 posed=[entry["name"] for entry in record.get("posed", [])])
    for key in path:
        value = value[key]
    return value


def matches(value, expected):
    """Whether `value` is `expected`: a pattern matched whole, a list item by item, a dict to a list by its sorted
    keys, else equal."""
    if isinstance(expected, re.Pattern):
        return isinstance(value, str) and expected.fullmatch(value) is not None
    if isinstance(expected, list) and isinstance(value, dict):
        return sorted(value) == expected
    if isinstance(expected, list) and any(isinstance(item, re.Pattern) for item in expected):
        return isinstance(value, list) and len(value) == len(expected) and all(map(matches, value, expected))
    return value == expected


def judged_all(out, inputs, expected):
    """{gate: verdict} of the expected gates, `every gate` judging each motion gate."""
    from score import stages
    names = [check.name for check in motion.CHECKS] if EVERY in expected else [name for name in expected]
    table = {check.name: check for check in stages.accepted_gaps(stages.MOTION).checks}
    return {name: (table[name.split(":", 1)[1]] if name.startswith("table:") else
                   next(check for check in motion.CHECKS if check.name == name)).judge(out, inputs, None)
            for name in names}


def gate_faults(out, inputs, expected):
    """The expected gates whose verdict differs, with why."""
    faults = {}
    for name, verdict in judged_all(out, inputs, expected).items():
        want = expected.get(name, expected.get(EVERY))
        joined = "\n".join(verdict.findings)
        unmatched = [pattern for pattern in want["findings"] if not re.search(pattern, joined, re.M)]
        if verdict.answer != want["answer"] or unmatched or (
                want["reason"] and not want["reason"].fullmatch(verdict.reason)):
            faults[name] = (verdict.answer, verdict.reason, verdict.findings, unmatched)
    return faults


def middle_faults(out, inputs, expected):
    """The expected middles that are not where the case says."""
    faults = []
    for prim, second, axis, how, reference in expected:
        middle = middle_at(out, inputs, prim, second)
        if how == "near":
            right = np.allclose(middle, reference[0], atol=reference[1])
        else:
            bound = (middle_at(out, inputs, reference[0], reference[1])[axis] + reference[2]
                     if isinstance(reference, tuple) else reference)
            right = middle[axis] < bound if how == "<" else middle[axis] > bound
        if not right:
            faults.append((prim, second, how, reference, middle))
    return faults


@pytest.mark.parametrize("case", [case for _, case in CASES], ids=[name for name, _ in CASES])
def test_a_thing_moves_as_its_design_says(tmp_path, monkeypatch, case):
    """Each world is made through motion.make from its design (or, for the motion check, check.py #23, its layer written
    from a record on the checked place), then its record, carried gaps, middles and gates are held to the case; a record
    rewritten with a known fault fails its gate by name. The bake is not run: its door is written here (a_baked_door).
    Break: score/stages/motion/from_design.py: `turns = max(1, round(middle_speed(motion_kind, "angular") * ROUND /
        360.0))` -> `turns = middle_speed(motion_kind, "angular") * ROUND / 360.0`
    Break: score/stages/motion/from_design.py: `opens = max(free, enter - travel)` -> `opens = max(free, enter)`
    Break: score/stages/motion/from_design.py: `return (float(low) + float(high)) / 2` -> `return float(high)`
    Break: score/stages/__init__.py: `"light", "motion", "sim-body")` -> `"light", "sim-body")`
    Break: score/stages/motion/from_design.py: `elif not served(rule, inventory, kinds) or spans == []:`
        -> `elif not served(rule, inventory, kinds):`
    Break: score/stages/motion/__init__.py: `if not any(enter <= end and leave >= begin for enter, leave in near):`
        -> `if False:`
    Break: score/stages/motion/__init__.py: `if said & set(NOT_ONE_LEAF) and path in swings:` -> `if False:`
    Break: score/stages/motion/from_design.py: `return dict(rule, rests="open") if said & set(base.get("open_words",
        ())) else rule` -> `return rule`
    Break: score/stages/motion/__init__.py: `kept.append(fit(first[prim], left[prim].pop(0)))` -> `still[prim] =
        "struck"`
    Break: score/stages/motion/from_design.py: `variant = next((entry["motion"] for entry in kinds[row["row_kind"]]
        .get("variants", []) if said & set(entry["words"])), {})` -> `variant = {}`
    Break: score/stages/motion/__init__.py: `still[prim] = f"it strikes at every way it was tried, so it stands:
        {struck[prim]}"` -> `still[prim] = "struck"`
    Break: score/stages/motion/__init__.py: `sizes = np.arange(abs(float(angle)), FIT_LEAST - 1e-9, -FIT_STEP)` ->
        `sizes = np.arange(abs(float(angle)), FIT_LEAST, -FIT_STEP)`
    Break: score/stages/motion/from_design.py: `elif rule["move"] == "swing" and not upright(stage, path):` -> `elif
        False:`
    Break: score/stages/motion/from_design.py: `still[path] = LYING_OPEN if rule.get("rests") == "open" else LYING`
        -> `still[path] = LYING`
    Break: score/stages/motion/__init__.py: `under(path, posed) or (opened and built)` -> `under(path, posed)`
    Break: score/stages/motion/__init__.py: `if opened and (not off or under(path, moving)):` -> `if opened and not
        off:` (the open hatch written moving passes)
    Break: score/stages/motion/from_design.py: `if rule["move"] in ("swing", "split") and hinged(stage, path):` ->
        `if False:` (the double door is unmade, covered fails)
    Break: tools/usd/motion_layer.py: `return own_pivot(stage, move)` -> `return own_side(stage, move, [0.0, 0.0,
        0.0])` (a leaf turns about its middle)
    Break: score/stages/motion/check.py: `tilt = max(tilt_of(turn, axis) for turn in turns)` -> `tilt =
        max(tilt_of(turn) for turn in turns)` (follows fails the lid's level hinge as tipping off the upright)
    Break: score/stages/motion/__init__.py: `moved = {path for path in moving_row_prims(stage, place, inputs) if
        under(path, moving)} | moving` -> `moved = moving`
    Break: score/stages/motion/from_design.py: `moves += [[at_least(opens), "open"], [at_least(shuts), "shut"]]` ->
        `moves += [[round(opens, 3), "open"], [round(shuts, 3), "shut"]]` (the walked lid's shut rounds to before its
        opening ends, and its layer is refused)
    Break: score/stages/motion/from_design.py: `names = {row["id"], str(row.get("thing", "")).split(":", 1)[-1]}`
        -> `names = {row["id"]}`
    Break: score/stages/motion/__init__.py: `planned = from_design.plan_gaps(read_json(inputs["plan"])) if "plan" in
        inputs else []` -> `planned = []`
    Break: score/stages/layer_base.py: `grounded.take_bakes(inputs, folder, seed.name)` -> `pass`
    Break: score/stages/motion/check.py: `if abs(reached - wanted) > ANGLE_MOST:` -> `if abs(reached - wanted) >= 0:`
    Break: score/stages/motion/check.py: `faults.append(f"{name}: {off.max():.2f} m off its path's curve at its frame
        {int(off.argmax())}")` -> `pass`
    Break: score/stages/motion/check.py: `if abs(reached - wanted) > ANGLE_MOST:` -> `if False:`
    Break: score/stages/motion/check.py: `return np.flatnonzero(steps > most)` -> `return np.array([], dtype=int)`
    Break: score/stages/motion/check.py: `stray = [path for path in varying_prims(stage, place, scopes) if not
        under_any(path, named)]` -> `stray = []`
    Break: score/stages/motion/check.py: `still = [path for path in named if frame_steps(shapes[path], codes).sum() <=
        STILL_MOST]` -> `still = []`
    Break: score/stages/motion/__init__.py: `faults.append((path, f"{path}: reaches {worst:.2f} m into {where[0]} at
        {where[1] / rate:.2f} s"))` -> `pass`"""
    import score.stages.assembly.baked as baked
    from score import stages
    monkeypatch.setattr(baked, "take_bake", a_baked_door)
    out, inputs, record = world(tmp_path, case)
    wrong = [(path, dug(record, path)) for path, expected in case.get("record", ()) if not matches(dug(record, path),
                                                                                                   expected)]
    assert wrong == [], wrong
    if "carried" in case:
        carried = [entry["name"] for entry in json.loads((out / "batch-gaps.json").read_text())["gaps"]]
        assert carried == case["carried"], carried
    assert middle_faults(out, inputs, case.get("middles", ())) == []
    assert gate_faults(out, inputs, case.get("gates", {})) == {}
    for change, expected in case.get("rewrites", ()):
        moves = [entry for entry in record["moves"] if entry["name"] not in change.get("drop", ())]
        (out / motion.RECORD).write_text(json.dumps(dict(record, moves=[*moves, *change.get("add", ())])))
        assert gate_faults(out, inputs, expected) == {}, change
    if case.get("reseeded"):
        again = tmp_path / "again"
        again.mkdir()
        motion.make(inputs, again, 1778076555, {})
        assert [(again / name).read_bytes() == (out / name).read_bytes()
                for name in (motion.RECORD, "layers/motion.usda")] == [True, True]
        assert not next(row for row in stages.STAGES if row.name == "motion").seeded
