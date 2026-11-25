"""tools/usd/physics.py's layers on a small place made here, without Blender: each object's mass from its area, its
material and triangles, a drop lifted over its target, a blocked fall refused, the hinge at its pins' middle with its
limits and its motor's window, the hand's path, the layers' order under the edit layer, a run's motion played back by
time samples, and a record without the environment's gravity refused. The expected numbers are worked by hand from
BOXES and RECORD (a 0.3 m crate's six faces: 6 x 0.3² m² of steel sheet).

Breaks that turn each check red (each applied once and seen red, 2026-10-27), all in physics.py:
- masses_follow_the_area: `mass = area * spec["sheet"] * spec["density"]` made `mass = area * spec["density"]`.
- a_drop_is_lifted_over_its_target: `landing(stage, drop) + drop["over"] - low[1]` made `landing(stage, drop) -
  low[1]`.
- the_hinge_stands_at_its_pins: `middle = np.mean([(low + high) / 2 for low, high in pins], axis=0)` made
  `middle = (pins[0][0] + pins[0][1]) / 2` (the lower pin only).
- the_motion_plays_back: write_motion's `start * Gf.Matrix4d(np.asarray(motion).T.tolist())` made untransposed.
- a_blocked_fall_is_refused: the `found.append(f"{drop['object']}: {prim.GetName()} stands in its fall")` made `pass`.
- a_record_without_gravity_is_refused: write_scene's `if "gravity" not in record:` made `if False:`.
- masses_follow_the_area (the hull's material): make_body's `UsdShade.MaterialBindingAPI.Apply(hull).Bind(...)` line
  dropped (a hull with no physics material: Newton gave it friction 1.0, restitution 0).
- the_hinge_stands_at_its_pins (what Newton needs said): write_hinge's `newton:limitStiffness` line dropped (the leaf
  swung to 148.6 degrees through its 100), or its `pairs.AddTarget(mesh.GetPath())` made `pass` (the leaf rubbed its
  frame and opened 8.6 degrees), or its ArticulationRootAPI line dropped (Newton refused the orphan FixedJoint).
- a_hull_collides_about_its_middle (what Newton needs said): make_body's `centred(hull)` line dropped (the crate laid
  with its origin at its foot keeps it there: Newton leaves out the floor's triangles once that origin dips under
  them, and chair_1 fell through the engine room's deck, 2026-11-13).
- an_adopted_asset_keeps_its_physics (#155): collide_by_triangles' `or is_adopted(prim, adopted)` dropped (the
  asset's convex hull made triangles, steel bound over its own physics material), or write_masses' adopted masses
  left out (the 1.5496 kg asset weighed by its area as steel sheet), or write's `engine_chosen(..., "Newton")` line
  dropped (the trial reads the asset's default engine, not Newton's), or authored_mass's `WEIGHED` skip dropped (our
  own library crate_2, weighed by the physics layer, read as adopted: its hull never switched on, and a re-run's
  stage, holding the physics layer, reads every weighed object as adopted).
- a_blocked_fall_is_refused (#155): laid_objects' `or prim in adopted` dropped (the adopted asset whose mesh stands
  under an instanceable prim, as a SimReady model's does, is no laid object, so the crate falls through it unrefused).
- the_hinge_stands_at_its_pins (and the slide beside it, #148): write_slide's `CreateAxisAttr(... [slide["along"]])`
  made `CreateAxisAttr(UsdPhysics.Tokens.x)` (the glass door's leaf slides across its doorway's depth, not its width),
  or bodies_of's slides line dropped (the leaf is no body, the joint holds nothing that moves).

- a_made_door_and_drawer_join_their_cabinet (#177): part_drive's speed not turned by the sign (30, not -30);
  write_parted's sibling filter dropped (the drawer left out of the door's pairs); part_inertia's box made a thin
  rod's (0, 0, kg) (fails A + B >= C) (each seen red 2026-11-25);
- a_made_door_and_drawer_join_their_cabinet (#177): write_parted's limits not turned for the negative way (0 to 100),
  part_frames' rotation the world's (joint_frames') -> the turned cabinet's drawer slides along the world's z; the
  drive's speed not turned with the sign; the hull copy's approximation left unset.

Run: .venv/bin/python tools/usd/test_the_physics_layers_hold_mass_drop_and_hinge.py [<folder>]   (a folder keeps the
toy place, for a Blender run)
"""
import json
import math
import pathlib
import sys
import tempfile

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom, UsdPhysics, UsdShade

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import physics  # noqa: E402

PLACE = "toy"
MATERIALS = json.loads((REPO / "data/physics/materials.json").read_text())
# Name: (low corner, high corner), the stage's frame; a door frame is its two posts and its lintel.
BOXES = {"floor_plate_1": [((-3, -0.04, -3), (3, 0, 3))], "table_1": [((-1.5, 0, -0.5), (-0.5, 0.76, 0.5))],
         "crate_1": [((1.85, 0, 1.85), (2.15, 0.3, 2.15))], "crate_2": [((2.35, 0, 1.85), (2.65, 0.3, 2.15))],
         "frame_1": [((-1.2, 0, -2.65), (-1.13, 2.75, -2.35)), ((1.13, 0, -2.65), (1.2, 2.75, -2.35)),
                     ((-1.2, 2.67, -2.65), (1.2, 2.75, -2.35))],
         "leaf_1": [((-1.12, 0, -2.56), (1.12, 2.66, -2.44))],
         "pin_1": [((1.13, 0.5, -2.44), (1.25, 0.9, -2.3))], "pin_2": [((1.13, 2.0, -2.44), (1.25, 2.4, -2.3))],
         "wheel_1": [((-0.2, 1.0, -2.44), (0.2, 1.4, -2.38))], "stool_1": [((1.5, 0.01, 0.8), (1.9, 0.48, 1.2))],
         "glass_frame_1": [((-2.7, 0, -2.85), (-2.65, 2.15, -1.6)), ((-2.75, 0, -2.85), (-2.6, 2.15, -2.8)),
                           ((-2.75, 0, -1.65), (-2.6, 2.15, -1.6))],
         "glass_leaf_1": [((-2.64, 0, -2.79), (-2.6, 2.09, -1.66))]}
RECORD = {"place": PLACE, "body": "moon", "gravity": 1.62, "material": "steel", "seconds": 4.0,
          "drops": [{"object": "crate_1", "onto": "table_1", "at": [-1.0, 0.0], "over": 0.5},
                    {"object": "crate_2", "onto": "floor", "at": [2.2, 0.5], "over": 0.8}],
          "hinges": [{"leaf": "leaf_1", "frame": "frame_1", "pins": ["pin_1", "pin_2"], "carries": ["wheel_1"],
                      "opens": [0.0, 100.0], "clear": 0.01,
                      "drive": {"speed": 60.0, "torque": 2000.0, "start": 0.5, "end": 2.5}}],
          "slides": [{"leaf": "glass_leaf_1", "frame": "glass_frame_1", "along": "z", "opens": [0.0, 1.13],
                      "clear": 0.01}],
          "pushes": [{"name": "push_stool", "size": [0.15, 0.2, 0.3], "from": [1.2, 0.3, 1.0], "to": [2.2, 0.3, 1.0],
                      "start": 0.5, "end": 1.5}],
          "moved": ["stool_1"]}


def box_points(low, high):
    corners = [(x, y, z) for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return corners, faces


def mesh(stage, path, boxes, middle):
    points, counts, indices = [], [], []
    for low, high in boxes:
        corners, faces = box_points(np.subtract(low, middle), np.subtract(high, middle))
        indices += [len(points) + corner for face in faces for corner in face]
        counts += [4] * len(faces)
        points += corners
    found = UsdGeom.Mesh.Define(stage, path)
    found.CreatePointsAttr([Gf.Vec3f(*point) for point in points])
    found.CreateFaceVertexCountsAttr(counts)
    found.CreateFaceVertexIndicesAttr(indices)
    return found


def toy_place(folder, foot=()):
    """A room with a table, two crates, a hinged door in its frame, a stool, laid as the export lays objects: each
    object's origin at its middle, or at its foot for the objects named in `foot`."""
    folder = pathlib.Path(folder)
    (folder / "layers").mkdir(parents=True)
    Sdf.Layer.CreateNew(str(folder / "layers/edit.usda")).Save()
    stage = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
    place = UsdGeom.Xform.Define(stage, f"/{PLACE}")
    stage.SetDefaultPrim(place.GetPrim())
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    for name, boxes in BOXES.items():
        middle = np.mean([np.add(low, high) / 2 for low, high in boxes], axis=0)
        if name in foot:
            middle[1] = min(low[1] for low, _ in boxes)
        holder = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/{name}")
        holder.MakeMatrixXform().Set(Gf.Matrix4d().SetTranslate(Gf.Vec3d(*middle)))
        mesh(stage, f"/{PLACE}/Objects/{name}/geo", boxes, middle)
        hull = mesh(stage, f"/{PLACE}/Objects/{name}/collision", boxes, middle)
        hull.CreatePurposeAttr(UsdGeom.Tokens.guide)
        UsdPhysics.CollisionAPI.Apply(hull.GetPrim())
        UsdPhysics.MeshCollisionAPI.Apply(hull.GetPrim()).CreateApproximationAttr("convexHull")
    stage.Save()
    root = Sdf.Layer.CreateNew(str(folder / f"{PLACE}.usda"))
    root.subLayerPaths[:] = ["./layers/edit.usda", "./layers/base.usda"]
    root.defaultPrim = PLACE
    root.timeCodesPerSecond = 24
    root.pseudoRoot.SetInfo("upAxis", "Y")
    root.pseudoRoot.SetInfo("metersPerUnit", 1.0)
    root.Save()
    return folder


def composed(folder):
    return Usd.Stage.Open(str(pathlib.Path(folder) / f"{PLACE}.usda"))


def written_once(folder):
    found = physics.write(folder, RECORD, MATERIALS)
    assert not found["faults"], found["faults"]
    return found


def masses_follow_the_area(folder):
    found = written_once(folder)
    steel = MATERIALS["materials"]["steel"]
    assert math.isclose(found["masses"]["crate_1"], 6 * 0.3 ** 2 * steel["sheet"] * steel["density"], rel_tol=1e-3)
    stage = composed(folder)
    floor = stage.GetPrimAtPath(f"/{PLACE}/Objects/floor_plate_1/geo")
    assert UsdPhysics.MeshCollisionAPI(floor).GetApproximationAttr().Get() == "none"
    bound = UsdShade.MaterialBindingAPI(floor).ComputeBoundMaterial("physics")[0]
    assert math.isclose(UsdPhysics.MaterialAPI(bound.GetPrim()).GetDynamicFrictionAttr().Get(), steel["dynamic"],
                        rel_tol=1e-6)
    assert not stage.GetPrimAtPath(f"/{PLACE}/Objects/table_1").HasAPI(UsdPhysics.RigidBodyAPI)
    hull = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1/collision")
    assert UsdPhysics.CollisionAPI(hull).GetCollisionEnabledAttr().Get() is True
    assert UsdShade.MaterialBindingAPI(hull).ComputeBoundMaterial("physics")[0].GetPath() == bound.GetPath()
    scene = UsdPhysics.Scene(stage.GetPrimAtPath(f"/{PLACE}/Physics/Scene"))
    assert math.isclose(scene.GetGravityMagnitudeAttr().Get(), 1.62, rel_tol=1e-6)


def a_drop_is_lifted_over_its_target(folder):
    stage = composed(folder)
    low, high = physics.world_box(stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1"))
    assert math.isclose(low[1], 0.76 + 0.5, abs_tol=1e-5) and math.isclose((low[0] + high[0]) / 2, -1.0, abs_tol=1e-5)


def the_hinge_stands_at_its_pins(folder):
    stage = composed(folder)
    joint = UsdPhysics.RevoluteJoint(stage.GetPrimAtPath(f"/{PLACE}/Physics/Joints/leaf_1_hinge"))
    assert joint.GetAxisAttr().Get() == "Y" and (joint.GetLowerLimitAttr().Get(), joint.GetUpperLimitAttr().Get()) == \
        (0.0, 100.0)
    frame = physics.world(stage.GetPrimAtPath(f"/{PLACE}/Objects/frame_1"))
    at = frame.Transform(Gf.Vec3d(joint.GetLocalPos0Attr().Get()))
    assert np.allclose(at, (1.19, 1.45, -2.37), atol=1e-5), at
    assert joint.GetPrim().HasAPI(UsdPhysics.ArticulationRootAPI)
    assert joint.GetPrim().GetAttribute("newton:limitStiffness").Get() == math.inf
    pairs = UsdPhysics.FilteredPairsAPI(stage.GetPrimAtPath(f"/{PLACE}/Objects/leaf_1")).GetFilteredPairsRel()
    assert pairs.GetTargets() == [Sdf.Path(f"/{PLACE}/Objects/frame_1/geo")], pairs.GetTargets()
    pin = stage.GetPrimAtPath(f"/{PLACE}/Objects/pin_1/geo")
    assert UsdPhysics.CollisionAPI(pin).GetCollisionEnabledAttr().Get() is False
    assert math.isclose(physics.world_box(stage.GetPrimAtPath(f"/{PLACE}/Objects/leaf_1"))[0][1], 0.01, abs_tol=1e-6)
    slide = UsdPhysics.PrismaticJoint(stage.GetPrimAtPath(f"/{PLACE}/Physics/Joints/glass_leaf_1_slide"))
    leaf = stage.GetPrimAtPath(f"/{PLACE}/Objects/glass_leaf_1")
    assert slide.GetAxisAttr().Get() == "Z" and (slide.GetLowerLimitAttr().Get(), slide.GetUpperLimitAttr().Get()) == \
        (0.0, np.float32(1.13)) and slide.GetPrim().HasAPI(UsdPhysics.ArticulationRootAPI)
    assert leaf.HasAPI(UsdPhysics.RigidBodyAPI) and slide.GetBody1Rel().GetTargets() == [leaf.GetPath()]
    assert np.allclose(physics.world(leaf).Transform(Gf.Vec3d(slide.GetLocalPos1Attr().Get())),
                       (-2.62, 1.055, -2.225), atol=1e-5)
    drive = UsdPhysics.DriveAPI(joint.GetPrim(), "angular")
    assert [drive.GetMaxForceAttr().Get(code) for code in (0, 12, 36, 60, 61)] == [0.0, 2000.0, 2000.0, 2000.0, 0.0]
    hand = UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Physics/Hands/push_stool"))
    assert np.allclose(hand.ComputeLocalToWorldTransform(0).ExtractTranslation(), (1.2, 0.3, 1.0))
    assert np.allclose(hand.ComputeLocalToWorldTransform(24 * 1.0).ExtractTranslation(), (1.7, 0.3, 1.0))
    root = Sdf.Layer.FindOrOpen(str(pathlib.Path(folder) / f"{PLACE}.usda"))
    assert list(root.subLayerPaths) == ["./layers/edit.usda", "./layers/trial.usda", "./layers/physics.usda",
                                        "./layers/base.usda"]


def the_motion_plays_back(folder):
    before = composed(folder)
    lifted = Gf.Vec3d(physics.world(before.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")).ExtractTranslation())
    down = np.eye(4)
    down[1, 3] = -0.5
    assert physics.write_motion(folder, {"crate_1": [np.eye(4).tolist(), down.tolist()]}) == 2
    stage = composed(folder)
    prim = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
    assert np.allclose(physics.world(prim, 1).ExtractTranslation(), lifted - Gf.Vec3d(0, 0.5, 0))
    assert Sdf.Layer.FindOrOpen(str(pathlib.Path(folder) / f"{PLACE}.usda")).subLayerPaths[1] == \
        "./layers/physics_motion.usda"


def a_hull_collides_about_its_middle():
    """A body laid with its origin at its foot collides by a hull whose own origin is its middle, the hull's shape
    where the drawn crate stands."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = toy_place(pathlib.Path(temporary) / PLACE, foot=("crate_2",))
        written_once(folder)
        stage = composed(folder)
        hull = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_2/collision")
        placed = UsdGeom.Xformable(hull).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        corners = np.array([placed.Transform(Gf.Vec3d(*point))
                            for point in np.asarray(UsdGeom.Mesh(hull).GetPointsAttr().Get(), float).tolist()])
        low, high = physics.world_box(stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_2"))
        assert np.allclose(corners.min(axis=0), low, atol=1e-5) and np.allclose(corners.max(axis=0), high, atol=1e-5)
        assert np.allclose(placed.ExtractTranslation(), (low + high) / 2, atol=1e-5), placed.ExtractTranslation()


ADOPTED_KG = 1.5496  # the adopted asset's own mass, as its asset authors it


def adopted_asset(folder):
    """An adopted asset laid at a free spot of the toy place: its mesh authoring its own mass, a convex hull collider
    and its own physics material, its Newton and MuJoCo physics in variant sets (Newton's adds a contact gap)."""
    asset = Usd.Stage.CreateNew(str(pathlib.Path(folder) / "layers/adopted.usda"))
    root = UsdGeom.Xform.Define(asset, "/adopted")
    asset.SetDefaultPrim(root.GetPrim())
    geo = mesh(asset, "/adopted/geo", [((-0.1, 0, -0.1), (0.1, 0.2, 0.1))], (0, 0, 0)).GetPrim()
    UsdPhysics.MassAPI.Apply(geo).CreateMassAttr(ADOPTED_KG)
    UsdPhysics.CollisionAPI.Apply(geo)
    UsdPhysics.MeshCollisionAPI.Apply(geo).CreateApproximationAttr(UsdPhysics.Tokens.convexHull)
    rubber = UsdShade.Material.Define(asset, "/adopted/rubber")
    UsdPhysics.MaterialAPI.Apply(rubber.GetPrim()).CreateDynamicFrictionAttr(0.8)
    UsdShade.MaterialBindingAPI.Apply(geo).Bind(rubber, UsdShade.Tokens.weakerThanDescendants, "physics")
    for engine in ("Newton", "MuJoCo"):
        variants = root.GetPrim().GetVariantSets().AddVariantSet(engine)
        for name in ("Disabled", "Enabled"):
            variants.AddVariant(name)
        variants.SetVariantSelection("Enabled")
        if engine == "Newton":
            with variants.GetVariantEditContext():
                asset.OverridePrim("/adopted/geo").CreateAttribute("newton:contactGap", Sdf.ValueTypeNames.Float).Set(
                    0.01)
        variants.SetVariantSelection("Disabled")
    asset.Save()
    base = Usd.Stage.Open(str(pathlib.Path(folder) / "layers/base.usda"))
    laid = base.DefinePrim(f"/{PLACE}/Objects/adopted_1")
    laid.GetReferences().AddReference("./adopted.usda")
    UsdGeom.Xformable(laid).AddTranslateOp().Set(Gf.Vec3d(-2.0, 0.0, 2.0))
    laid.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set("model/adopted@1")
    base.GetPrimAtPath(f"/{PLACE}/Objects/crate_2").CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set(
        "model/crate@1")  # one of our own library objects beside it, weighed by the physics layer
    base.Save()


def an_adopted_asset_keeps_its_physics():
    """An adopted asset (#155) keeps the mass, collider and physics material its asset authors, its Newton physics
    chosen, and is a trial body as its asset says: the physics layer fills in only what nothing authors."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = toy_place(pathlib.Path(temporary) / PLACE)
        adopted_asset(folder)
        found = physics.write(folder, dict(RECORD, moved=[*RECORD["moved"], "adopted_1"]), MATERIALS)
        assert not found["faults"], found["faults"]
        assert found["masses"]["adopted_1"] == round(ADOPTED_KG, 3) == found["bodies"]["adopted_1"], found["masses"]
        stage = composed(folder)
        laid, geo = stage.GetPrimAtPath(f"/{PLACE}/Objects/adopted_1"), stage.GetPrimAtPath(
            f"/{PLACE}/Objects/adopted_1/geo")
        assert math.isclose(UsdPhysics.MassAPI(geo).GetMassAttr().Get(), ADOPTED_KG, rel_tol=1e-6)
        assert UsdPhysics.MeshCollisionAPI(geo).GetApproximationAttr().Get() == "convexHull"
        assert UsdShade.MaterialBindingAPI(geo).ComputeBoundMaterial("physics")[0].GetPath().name == "rubber"
        assert laid.GetVariantSets().GetVariantSelection("Newton") == "Enabled" and \
            laid.GetVariantSets().GetVariantSelection("MuJoCo") == "Disabled"
        assert geo.GetAttribute("newton:contactGap").Get() is not None
        assert laid.HasAPI(UsdPhysics.RigidBodyAPI) and not geo.HasAPI(UsdPhysics.RigidBodyAPI)
        assert UsdPhysics.CollisionAPI(geo).GetCollisionEnabledAttr().Get() is not False
        assert [prim.GetName() for prim in physics.adopted_objects(stage)] == ["adopted_1"]  # as a re-run reads it
        steel = MATERIALS["materials"]["steel"]
        assert math.isclose(found["masses"]["crate_2"], 6 * 0.3 ** 2 * steel["sheet"] * steel["density"], rel_tol=1e-3)
        ours = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_2/collision")
        assert UsdPhysics.CollisionAPI(ours).GetCollisionEnabledAttr().Get() is True
        assert UsdPhysics.CollisionAPI(stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_2/geo")
                                       ).GetCollisionEnabledAttr().Get() is False
        assert UsdShade.MaterialBindingAPI(ours).ComputeBoundMaterial("physics")[0].GetPath().name == "steel"


def instanced_asset(folder):
    """An adopted asset laid at (2.5, 0, -1) whose mesh, authoring its own mass, stands under an instanceable prim (as
    a SimReady model lays its shapes from its instances' payload, #155)."""
    asset = Usd.Stage.CreateNew(str(pathlib.Path(folder) / "layers/instanced.usda"))
    root = UsdGeom.Xform.Define(asset, "/instanced")
    asset.SetDefaultPrim(root.GetPrim())
    asset.CreateClassPrim("/instanced_shared")
    geo = mesh(asset, "/instanced_shared/geo", [((-0.1, 0, -0.1), (0.1, 0.2, 0.1))], (0, 0, 0)).GetPrim()
    UsdPhysics.MassAPI.Apply(geo).CreateMassAttr(ADOPTED_KG)
    shared = asset.DefinePrim("/instanced/shared", "Xform")
    shared.GetReferences().AddInternalReference("/instanced_shared")
    shared.SetInstanceable(True)
    asset.Save()
    base = Usd.Stage.Open(str(pathlib.Path(folder) / "layers/base.usda"))
    laid = base.DefinePrim(f"/{PLACE}/Objects/instanced_1")
    laid.GetReferences().AddReference("./instanced.usda")
    UsdGeom.Xformable(laid).AddTranslateOp().Set(Gf.Vec3d(2.5, 0.0, -1.0))
    laid.CreateAttribute("score:library", Sdf.ValueTypeNames.String).Set("model/instanced@1")
    base.Save()


def a_made_door_and_drawer_join_their_cabinet():
    """A made cabinet laid whole (#177, maker/parts.py's nodes as place_build's glTF conversion lays them: its body's
    `geo`, a door node `door_01__hinge_yn` at its hinge and a drawer node `drawer_01__slide_z` at its middle, each
    holding its own `geo`), the cabinet turned a quarter about up: the door a RevoluteJoint about its own y, -100 to 0
    degrees (its negative way), its motor's speed turned with it; the drawer a PrismaticJoint along its own z, which
    the turned cabinet lays along the world's x, 0 to 0.35 m; each its own body of its own mass, colliding by a guide
    hull copy of its mesh, its drawn mesh out of the collision, filtered against the cabinet's body."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary) / PLACE
        (folder / "layers").mkdir(parents=True)
        Sdf.Layer.CreateNew(str(folder / "layers/edit.usda")).Save()
        stage = Usd.Stage.CreateNew(str(folder / "layers/base.usda"))
        stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{PLACE}").GetPrim())
        mesh(stage, f"/{PLACE}/Objects/floor_plate_1/geo", [((-3.0, -0.04, -3.0), (3.0, 0.0, 3.0))], (0.0, 0.0, 0.0))
        holder = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/cabinet_1")
        holder.MakeMatrixXform().Set(Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0, 1, 0), 90)) *
                                     Gf.Matrix4d().SetTranslateOnly(Gf.Vec3d(1.0, 0.0, 0.0)))
        mesh(stage, f"/{PLACE}/Objects/cabinet_1/geo", [((-0.25, 0.0, -0.2), (0.25, 0.8, 0.2))], (0.0, 0.0, 0.0))
        for node, pivot, slab in (("door_01__hinge_yn", (-0.24, 0.54, 0.2), ((-0.24, 0.3, 0.2), (0.24, 0.78, 0.22))),
                                  ("drawer_01__slide_z", (0.0, 0.15, 0.21), ((-0.24, 0.02, 0.2), (0.24, 0.28, 0.22)))):
            part = UsdGeom.Xform.Define(stage, f"/{PLACE}/Objects/cabinet_1/{node}")
            part.MakeMatrixXform().Set(Gf.Matrix4d().SetTranslate(Gf.Vec3d(*pivot)))
            mesh(stage, f"/{PLACE}/Objects/cabinet_1/{node}/geo", [slab], pivot)
        stage.Save()
        root = Sdf.Layer.CreateNew(str(folder / f"{PLACE}.usda"))
        root.subLayerPaths[:] = ["./layers/edit.usda", "./layers/base.usda"]
        root.defaultPrim, root.timeCodesPerSecond = PLACE, 24
        root.Save()
        door = {"node": "door_01__hinge_yn", "joint": "hinge", "axis": "y", "sign": -1, "limits": [0.0, 100.0],
                "kg": 4.0, "drive": {"speed": 30.0, "torque": 50.0, "start": 0.5, "end": 2.0}}
        drawer = {"node": "drawer_01__slide_z", "joint": "slide", "axis": "z", "sign": 1, "limits": [0.0, 0.35],
                  "kg": 2.0}
        found = physics.write(folder, {**{key: RECORD[key] for key in ("place", "body", "gravity", "material",
                                                                        "seconds")},
                                       "drops": [], "hinges": [], "pushes": [], "moved": [],
                                       "parted": [{"object": "cabinet_1", "parts": [door, drawer]}]}, MATERIALS)
        assert not found["faults"], found["faults"]
        stage = composed(folder)
        cabinet = stage.GetPrimAtPath(f"/{PLACE}/Objects/cabinet_1")
        hinge = UsdPhysics.RevoluteJoint(stage.GetPrimAtPath(f"/{PLACE}/Physics/Joints/cabinet_1_door_01__hinge_yn"))
        slide = UsdPhysics.PrismaticJoint(stage.GetPrimAtPath(f"/{PLACE}/Physics/Joints/cabinet_1_drawer_01__slide_z"))
        assert hinge.GetAxisAttr().Get() == "Y" and (hinge.GetLowerLimitAttr().Get(), hinge.GetUpperLimitAttr().Get()) \
            == (-100.0, 0.0) and hinge.GetBody0Rel().GetTargets() == [cabinet.GetPath()]
        door_prim = stage.GetPrimAtPath(f"/{PLACE}/Objects/cabinet_1/door_01__hinge_yn")
        assert np.allclose(physics.world(cabinet).Transform(Gf.Vec3d(hinge.GetLocalPos0Attr().Get())),
                           physics.world(door_prim).ExtractTranslation(), atol=1e-6)
        way = physics.world(cabinet).TransformDir(Gf.Rotation(Gf.Quatd(slide.GetLocalRot0Attr().Get())).TransformDir(
            Gf.Vec3d(0, 0, 1)))
        assert slide.GetAxisAttr().Get() == "Z" and np.allclose(way, (1, 0, 0), atol=1e-6), way
        assert (slide.GetLowerLimitAttr().Get(), slide.GetUpperLimitAttr().Get()) == (0.0, np.float32(0.35))
        assert UsdPhysics.MassAPI(door_prim).GetMassAttr().Get() == 4.0 and door_prim.HasAPI(UsdPhysics.RigidBodyAPI)
        assert UsdPhysics.CollisionAPI(door_prim.GetChild("geo")).GetCollisionEnabledAttr().Get() is False
        hull = door_prim.GetChild("geo_hull")
        assert UsdPhysics.MeshCollisionAPI(hull).GetApproximationAttr().Get() == "convexHull" and \
            UsdGeom.Imageable(hull).ComputePurpose() == "guide"
        # the door driven by speed its negative way, damped by its own inertia (not STIFF_DRIVE); its inertia a solid
        # box's (A + B >= C, which MuJoCo checks); kept off the cabinet's body and its sibling drawer
        drive = UsdPhysics.DriveAPI(hinge.GetPrim(), "angular")
        assert drive.GetTargetVelocityAttr().Get() == -30.0 and drive.GetMaxForceAttr().Get(12) == 50.0
        assert 0 < drive.GetDampingAttr().Get() < physics.STIFF_DRIVE
        inertia = sorted(UsdPhysics.MassAPI(door_prim).GetDiagonalInertiaAttr().Get())
        assert inertia[0] > 0 and inertia[0] + inertia[1] >= inertia[2], inertia
        assert UsdPhysics.FilteredPairsAPI(door_prim).GetFilteredPairsRel().GetTargets() == [
            Sdf.Path(f"/{PLACE}/Objects/cabinet_1/geo"), Sdf.Path(f"/{PLACE}/Objects/cabinet_1/drawer_01__slide_z")]


def a_blocked_fall_is_refused():
    """A drop whose column holds another object is refused, the object an adopted asset laid in an instance too."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = toy_place(pathlib.Path(temporary) / PLACE)
        instanced_asset(folder)
        record = dict(RECORD, drops=[{"object": "crate_1", "onto": "floor", "at": [-1.0, 0.0], "over": 1.0},
                                     {"object": "crate_2", "onto": "floor", "at": [2.5, -1.0], "over": 1.0}])
        found = physics.write(folder, record, MATERIALS)
        assert found["faults"] == ["crate_1: table_1 stands in its fall",
                                   "crate_2: instanced_1 stands in its fall"], found["faults"]


def a_record_without_gravity_is_refused():
    """The pull is the environment concept's physics, carried by the record; none is refused by name, no fallback."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = toy_place(pathlib.Path(temporary) / PLACE)
        record = {key: value for key, value in RECORD.items() if key != "gravity"}
        try:
            physics.write(folder, record, MATERIALS)
        except SystemExit as refusal:
            assert "no physics for moon" in str(refusal), refusal
        else:
            raise AssertionError("a record without gravity was written")


def main():
    kept = sys.argv[1] if len(sys.argv) > 1 else None
    with tempfile.TemporaryDirectory() as temporary:
        folder = toy_place(pathlib.Path(kept or temporary) / PLACE)
        masses_follow_the_area(folder)
        a_drop_is_lifted_over_its_target(folder)
        the_hinge_stands_at_its_pins(folder)
        if not kept:
            the_motion_plays_back(folder)
    a_hull_collides_about_its_middle()
    an_adopted_asset_keeps_its_physics()
    a_blocked_fall_is_refused()
    a_record_without_gravity_is_refused()
    a_made_door_and_drawer_join_their_cabinet()
    print("test_the_physics_layers_hold_mass_drop_and_hinge: ok")


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    main()
