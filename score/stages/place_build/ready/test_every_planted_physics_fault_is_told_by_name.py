"""Invariant: the physics ready check tells the placing agent, by object, every planted fault that keeps a place from
being walked in and pushed (a crate floating 40 cm over the ground; two crates 10 cm inside each other; a door standing
free of any wall; a door's far side walled off by a crate so no way 0.9 m wide reaches it; a tunnel whose far end
joins nothing; a tunnel too low to walk in; a box half off a desk that tips, and moves when let go in MuJoCo; an object
with no triangles), while what rests right passes (the walls, the door in its opening, the desk, a monitor laid `on`
the desk, a panel mounted `on` a wall, a crate on the ground); and `on` lays an object in contact with its support.

Breaks that turn this red (each applied once and seen red, then reverted):
- ready.support_faults: `gaps[nearest] > TOLERANCE` made `> 1.0` -> the floating crate passes
- ready.crossing_depths: `count % 2` made `count % 2 == 0` -> the overlapping crates pass
- ready.door_faults: the `open_sides` list left empty -> the free-standing door passes
- ready.room_for_walkway: ERODED made 0 -> the blocked door's far side reads reached
- ready.connector_faults: JOIN made 10 -> the tunnel's free end reads joined
- ready.walkers_floor: `clear` taken as all True -> the low tunnel reads walkable
- ready.placed_on: the gap left unsubtracted -> the monitor floats over the desk
- ready.check: the no-collision list left empty -> the decal passes
- settle_mujoco.settled: the steps left out -> the tipping box reads stable
"""
import json
import pathlib

import numpy as np
from PIL import Image
from pxr import Gf, Sdf, UsdGeom

from score.stages import place_build
from score.stages.place_build import ready


def box(stage, place, name, size, low, kind="model"):
    """An object of one cube `size` (x, y, z metres) whose lowest corner is `low`."""
    path = f"/{place}/Objects/{name}"
    holder = UsdGeom.Xform.Define(stage, path)
    holder.AddTranslateOp().Set(Gf.Vec3d(*(np.asarray(low) + np.asarray(size) / 2)))
    holder.AddRotateXYZOp().Set(Gf.Vec3f(0, 0, 0))
    holder.AddScaleOp().Set(Gf.Vec3f(1, 1, 1))
    cube = UsdGeom.Cube.Define(stage, f"{path}/geo")
    cube.CreateSizeAttr(1.0)
    cube.AddScaleOp().Set(Gf.Vec3f(*size))
    prim = holder.GetPrim()
    prim.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set(kind)
    prim.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(f"model/{name}")
    return prim


def desk(stage, place):
    """A desk: a top 1.2 x 0.05 x 0.6 at 0.75 m on four legs, its corner at (-3, -3)."""
    prim = box(stage, place, "desk", (1.2, 0.05, 0.6), (-3.0, 0.70, -3.0))
    for number, (x, z) in enumerate(((-0.55, -0.25), (0.55, -0.25), (-0.55, 0.25), (0.55, 0.25))):
        leg = UsdGeom.Cube.Define(stage, f"{prim.GetPath()}/leg{number}")
        leg.CreateSizeAttr(1.0)
        leg.AddTranslateOp().Set(Gf.Vec3d(x, -0.375, z))
        leg.AddScaleOp().Set(Gf.Vec3f(0.05, 0.70, 0.05))


def wall(stage, place):
    """A wall 8 m long, 2.5 m high and 0.2 m thick along x at z 0, a doorway 1.2 m wide and 2.1 m high cut in its
    middle: one object of three blocks."""
    prim = box(stage, place, "wall", (3.4, 2.5, 0.2), (-4.0, 0.0, -0.1))
    for name, size, middle in (("right", (3.4, 2.5, 0.2), (4.6, 0.0, 0.0)), ("lintel", (1.2, 0.4, 0.2), (2.3, 1.05, 0.0))):
        block = UsdGeom.Cube.Define(stage, f"{prim.GetPath()}/{name}")
        block.CreateSizeAttr(1.0)
        block.AddTranslateOp().Set(Gf.Vec3d(*middle))
        block.AddScaleOp().Set(Gf.Vec3f(*size))


def planted(folder):
    """The fixture place: a ground disc, a wall with a 1.2 m opening and its door, and every planted fault."""
    concept = folder / "concept.png"
    Image.new("RGB", (8, 8)).save(concept)
    place_build.start(folder / "place", "fixture", concept)
    folder = folder / "place"
    place_build.ground(folder, "ground", 7.0, (0.0, -0.02, 0.0))
    place_build.tube(folder, "tunnel", 1.4, 3.0, (-3.0, 0.0, 2.5))  # its far end, at z 5.5, joins nothing
    place_build.tube(folder, "crawl", 0.7, 2.0, (3.5, 0.0, -5.0), (0.0, 90.0, 0.0))
    stage, place = place_build.opened(folder)
    wall(stage, place)
    box(stage, place, "door", (1.0, 2.0, 0.05), (-0.5, 0.0, -0.025))
    box(stage, place, "blocker", (2.4, 1.0, 1.1), (-1.2, 0.0, -1.4))
    box(stage, place, "hatch_free", (1.0, 2.0, 0.05), (2.5, 0.0, 3.0))
    box(stage, place, "bulkhead", (3.0, 2.8, 0.2), (-4.5, 0.0, 2.3))
    box(stage, place, "crate_ok", (0.5, 0.5, 0.5), (4.0, 0.0, 1.0))
    box(stage, place, "crate_float", (0.5, 0.5, 0.5), (-1.0, 0.4, -4.5))
    box(stage, place, "crate_a", (0.5, 0.5, 0.5), (1.5, 0.0, -3.5))
    box(stage, place, "crate_b", (0.5, 0.5, 0.5), (1.9, 0.0, -3.5))
    desk(stage, place)
    box(stage, place, "monitor", (0.5, 0.35, 0.1), (-2.65, 1.5, -2.8))
    box(stage, place, "tipper", (0.4, 0.4, 0.4), (-3.3, 0.75, -2.9))
    box(stage, place, "panel", (0.6, 0.4, 0.05), (2.0, 0.5, 1.0))
    decal = UsdGeom.Xform.Define(stage, f"/{place}/Objects/decal").GetPrim()
    decal.CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("model")
    stage.GetRootLayer().Save()
    return folder


def test_every_planted_physics_fault_is_told_by_name(tmp_path):
    folder = planted(tmp_path)
    monitor = ready.on(folder, "monitor", "desk")
    panel = ready.on(folder, "panel", "wall:wall", height=1.2)
    assert abs(monitor["at"][1] - (0.75 + 0.175)) < 0.01, monitor  # its bottom on the desk's top
    assert abs(panel["at"][2] - (0.1 + 0.025)) < 0.01 and abs(panel["at"][1] - 1.4) < 0.03, panel
    summary = ready.check(folder)
    found = json.loads(pathlib.Path(summary["file"]).read_text())["objects"]
    told = {name: {fault["fault"] for fault in faults} for name, faults in found.items()}
    print(json.dumps(summary))
    for name in ("wall", "desk", "monitor", "panel", "crate_ok", "bulkhead",
                 "ground"):
        assert name not in told, (name, found.get(name))
    assert told["door"] == {"walkway"}, found["door"]
    assert "floating" in told["crate_float"], found["crate_float"]
    assert "penetration" in told["crate_a"] and "penetration" in told["crate_b"], (found.get("crate_a"))
    assert "door not in an opening" in told["hatch_free"], found.get("hatch_free")
    assert any(fault.get("end") == "end" for fault in found["tunnel"]) \
        and not any(fault.get("end") == "start" for fault in found["tunnel"]), found["tunnel"]
    assert any("unwalkable" in fault for fault in found["crawl"]), found["crawl"]
    assert told["decal"] == {"no collision geometry"}, found["decal"]
    assert "tips" in told["tipper"], found["tipper"]
    if summary["settle"].startswith("not run"):
        print("skipped: the MuJoCo settle (" + summary["settle"] + ")")
        return
    assert "unstable" in told["tipper"] and "unstable" not in told.get("crate_ok", ()), found["tipper"]
