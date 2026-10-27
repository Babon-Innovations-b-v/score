"""What a place's stage collides with (tools/usd/colliders.py) on shapes and stages made here: a box square to its
frame is an exact box and anything else (a turned box, a flight of stairs, an open box) its triangles simplified; the
scene record's walls, stairs and ground collide and its water and sky do not; a world model file converted for a
fixture (glb_asset.py) collides by a convex hull round each of its meshes; and the free check finds a wall without
collision, a switched-off one, a model without a collider of its own (a model standing on it does not lend it one),
and leaves a shown place to its own stage.

Breaks that turn each test red (each applied once and seen red, 2026-10-27):
- boxes_told_apart: colliders.is_square_box's `return abs(triangle_area(points, triangles) - surface) <=
  AREA_TOLERANCE * surface` made `return True` (the lidless box read as a box).
- the_record_s_structure_and_ground_collide_and_its_water_does_not: colliders.py's `NOT_SOLID_PLAINS = ("sky",
  "water")` made `("water",)` (the Earth in the sky collides).
- a_fixture_s_model_collides_by_a_hull_round_each_mesh: glb_asset.py's `colliders.hull_of(prim.GetPrim())` made `pass`.
- the_check_finds_what_does_not_collide: colliders.has_collider's `walk.PruneChildren()` made `pass` (the lamp lends
  the crate its collider).

Run: .venv/bin/python tools/usd/test_walls_and_models_collide_and_water_does_not.py
"""
import pathlib
import sys
import tempfile

import numpy as np
import trimesh
from pxr import Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import builders  # noqa: E402
import colliders  # noqa: E402
import glb_asset  # noqa: E402
import scene  # noqa: E402

PLACE = "yard"
SURFACE = "concrete"


def approximation(prim):
    return UsdPhysics.MeshCollisionAPI(prim).GetApproximationAttr().Get()


def boxes_told_apart():
    """A box square to its frame is one; a turned box, a flight of three steps, a box with its lid off and a flat
    quad are not."""
    square = builders.box([1.0, 2.0, 3.0], [2.0, 4.0, 6.0], SURFACE)
    turned = builders.box([0.0, 0.0, 0.0], [2.0, 1.0, 1.0], SURFACE, turn=30.0)
    flight = builders.stairs([0.0, 0.0, 0.0], [0.0, 0.6, -0.9], 1.0, 3, SURFACE)
    lidless = dict(square, triangles=square["triangles"][:-2])  # the last face's two triangles gone
    flat = builders.quad([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], SURFACE)
    found = {name: colliders.is_square_box(shape["points"], shape["triangles"]) for name, shape in
             (("square", square), ("turned", turned), ("flight", flight), ("lidless", lidless), ("flat", flat))}
    wanted = {"square": True, "turned": False, "flight": False, "lidless": False, "flat": False}
    return [] if found == wanted else [f"boxes told apart as {found}, not {wanted}"]


def a_stage():
    """A stage holding a place with its library surface, as the export makes one."""
    stage = Usd.Stage.CreateInMemory()
    root = UsdGeom.Xform.Define(stage, f"/{PLACE}")
    stage.SetDefaultPrim(root.GetPrim())
    UsdShade.Material.Define(stage, f"/{PLACE}/Library/{SURFACE}")
    return stage


def the_record_s_structure_and_ground_collide_and_its_water_does_not():
    """A wall (a box square to the place), a flight of stairs, a disc of ground, a pool and the Earth hung in the sky
    (a structure entry, plain sky, as the outdoor writer lays a body over the Moon), written from a record: the wall an
    exact box, the stairs and ground their triangles simplified, the pool and the Earth no collider."""
    stage = a_stage()
    wall = {"name": "wall", "builder": "box", "centre": [0, 1.5, -4], "size": [8, 3, 0.2], "surface": SURFACE}
    flight = {"name": "steps", "builder": "stairs", "foot": [2, 0, 0], "top": [2, 1.2, -1.8], "wide": 1.0, "steps": 6,
              "surface": SURFACE}
    earth = {"name": "earth", "builder": "sphere", "centre": [600.0, 300.0, 800.0], "radius": 220.0,
             "surface": SURFACE, "plain": "sky"}
    disc = {"name": "plain", "builder": "disc", "radius": 20.0, "height": 0.0, "surface": SURFACE}
    pool = {"name": "pool", "builder": "disc", "radius": 2.0, "height": 0.1, "surface": SURFACE}
    scene.write_structure(stage, PLACE, [wall, flight, earth])
    scene.write_structure(stage, PLACE, [disc], root="Terrain", kind="ground")
    scene.write_structure(stage, PLACE, [pool], root="Water", kind="water")
    found = {}
    for path in ("Structure/wall", "Structure/steps", "Structure/earth", "Terrain/plain", "Water/pool"):
        prim = stage.GetPrimAtPath(f"/{PLACE}/{path}")
        found[path] = approximation(prim) if prim.HasAPI(UsdPhysics.CollisionAPI) else None
    wanted = {"Structure/wall": "boundingCube", "Structure/steps": "meshSimplification", "Structure/earth": None,
              "Terrain/plain": "meshSimplification", "Water/pool": None}
    problems = [] if found == wanted else [f"the record's colliders are {found}, not {wanted}"]
    left = colliders.faults(stage)
    return problems + ([f"a record written whole still has faults: {left}"] if left else [])


def a_fixture_s_model_collides_by_a_hull_round_each_mesh():
    """A world model file of two boxes apart converted for a fixture: each of its two drawn meshes collides by a
    convex hull round itself, and nothing else is added to it (the asset holds its two meshes and no more)."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        far = trimesh.creation.box(extents=(0.5, 0.5, 0.5))
        far.apply_translation([3.0, 0.0, 0.0])
        trimesh.Scene([trimesh.creation.box(extents=(1.0, 1.0, 1.0)), far]).export(str(folder / "pair.glb"))
        glb_asset.asset(folder / "pair.glb", folder / "fixture_pair.usdc", folder / "textures")
        stage = Usd.Stage.Open(str(folder / "fixture_pair.usdc"))
        meshes = [prim for prim in stage.Traverse() if prim.IsA(UsdGeom.Mesh)]
        found = sorted((prim.GetName(), colliders.collides(prim), approximation(prim)) for prim in meshes)
        wanted = [("mesh_0", True, "convexHull"), ("mesh_1", True, "convexHull")]
        return [] if found == wanted else [f"the fixture's meshes are {found}, not {wanted}"]


def a_model(stage, path, model, collider=True):
    """A laid model: an Xform naming its model, a drawn cube, and a guide collider when asked."""
    xform = UsdGeom.Xform.Define(stage, path)
    xform.GetPrim().CreateAttribute("score:model", Sdf.ValueTypeNames.String).Set(model)
    UsdGeom.Cube.Define(stage, f"{path}/drawn")
    if collider:
        guide = UsdGeom.Cube.Define(stage, f"{path}/collision")
        guide.CreatePurposeAttr(UsdGeom.Tokens.guide)
        UsdPhysics.CollisionAPI.Apply(guide.GetPrim())
    return xform


def a_floor(stage, path, collide=True, enabled=True):
    floor = UsdGeom.Cube.Define(stage, path)
    floor.GetPrim().CreateAttribute("score:kind", Sdf.ValueTypeNames.String).Set("structure")
    if collide:
        UsdPhysics.CollisionAPI.Apply(floor.GetPrim()).CreateCollisionEnabledAttr(enabled)


def the_check_finds_what_does_not_collide():
    """A floor without collision, a wall with it switched off, a crate with no collider under a lamp that has one, and
    a ground in a shown place: the floor, the wall and the crate fail; the lamp, the good floor and the shown place's
    ground do not."""
    stage = a_stage()
    a_floor(stage, f"/{PLACE}/Structure/good_floor")
    a_floor(stage, f"/{PLACE}/Structure/bare_floor", collide=False)
    a_floor(stage, f"/{PLACE}/Structure/off_wall", enabled=False)
    a_model(stage, f"/{PLACE}/Objects/crate_1", "crate", collider=False)
    a_model(stage, f"/{PLACE}/Objects/crate_1/lamp_1", "lamp")
    a_model(stage, f"/{PLACE}/Objects/bench_1", "bench")
    a_floor(stage, f"/{PLACE}/Places/hub/Structure/floor", collide=False)
    found = sorted((fault["prim"], fault["what"]) for fault in colliders.faults(stage))
    wanted = sorted([(f"/{PLACE}/Structure/bare_floor", "structure"), (f"/{PLACE}/Structure/off_wall", "structure"),
                     (f"/{PLACE}/Objects/crate_1", "model")])
    return [] if found == wanted else [f"the check found {found}, not {wanted}"]


CHECKS = (boxes_told_apart, the_record_s_structure_and_ground_collide_and_its_water_does_not,
          a_fixture_s_model_collides_by_a_hull_round_each_mesh, the_check_finds_what_does_not_collide)


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
