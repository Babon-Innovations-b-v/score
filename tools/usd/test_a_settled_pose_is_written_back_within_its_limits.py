"""Check the settle's write-back on places made here, without Blender: a pose an object came to
rest in (tipped a little on a sloping planned ground) written into the layout as spot, lift and rotation, and exported
again, stands exactly where it rested; a 3 m piece that would turn 40 degrees to rest keeps its laid pose and is
marked, while 1 m debris may turn so; a tip onto uneven feet (the water tank's legs, or a base the clusters read as one foot) is refused while a crate's is written; a kit room's piece (the game's kit) moves with its object, what lies on a settled piece moves with it, only floor pieces are dropped, not a kit's floor plate, and neither a glow nor what lies on a dropped piece (held, or a scene record's fixture) is a static of the drop.
(The levelled yard and the dent went with the old grounds and kits, 2026-10-21.)

Run: .venv/bin/python tools/usd/test_a_settled_pose_is_written_back_within_its_limits.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
from pxr import Gf, Usd, UsdGeom
from scipy.spatial.transform import Rotation

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import resting  # noqa: E402
import test_floating_sunk_and_tipping_objects_are_told_apart as resting_test  # noqa: E402
import settle  # noqa: E402

PLACE = resting_test.PLACE


def stage_matrix(path, name):
    stage = Usd.Stage.Open(str(path))
    return np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Objects/{name}"))
                      .ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T


def a_settled_pose_round_trips_through_the_layout():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        sloped = resting_test.sloping_ground(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (4, 0, 2))], [("crate", "floor")], sloped)
        before = stage_matrix(path, "crate_1")
        tipped = np.eye(4)
        tipped[:3, :3] = Rotation.from_euler("xz", [6, -8], degrees=True).as_matrix()
        tipped[:3, 3] = before[:3, 3] - tipped[:3, :3] @ before[:3, 3] + [0.05, -0.04, 0.02]  # about the box itself
        after = tipped @ before
        inventory = {"rows": [{"id": "crate", "anchor": "floor", "at": [{"x": 4, "z": 2, "y": 0, "facing": 0}]}]}
        (folder / "inventory.json").write_text(json.dumps(inventory))
        settle.write_layout({"crate_1": {"before": before, "after": after}}, sloped, folder / "inventory.json",
                            folder / "kit.json")
        kit = json.loads((folder / "kit.json").read_text())
        (folder / "inventory.json").write_text(json.dumps(
            {"rows": [{"id": "crate", "name": "crate", "anchor": "floor", "thing": "prop:test_crate"}]}))
        again = resting_test.export.export(
            PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
            inventory_path=folder / "inventory.json", ground=sloped)
        problems = []
        if "rotation" not in kit["pieces"][0] or "tilt" in kit["pieces"][0]:
            problems.append(f"the settled piece is written as {kit['pieces'][0]}")
        off = np.abs(stage_matrix(again, "crate_1") - after).max()
        if off > 1e-4:
            problems.append(f"the exported piece stands {off:.5f} off the pose it rested in")
        return problems


def a_big_turn_is_marked_not_made():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (4, 0, 2))], [("crate", "floor")])
        before = stage_matrix(path, "crate_1")
        rolled = np.eye(4)
        rolled[:3, :3] = Rotation.from_euler("x", 40, degrees=True).as_matrix()
        rolled[:3, 3] = before[:3, 3] - rolled[:3, :3] @ before[:3, 3]
        laid_kit = json.loads((folder / "kit.json").read_text())
        problems = []
        for size, marked in ((3.0, True), (1.0, False)):  # a 3 m piece keeps its pose; 1 m debris may turn freely
            laid_kit["pieces"][0]["size"] = [size, 1.0, 1.0]
            (folder / "kit.json").write_text(json.dumps(laid_kit))
            inventory = {"rows": [{"id": "crate", "anchor": "floor", "at": [{"x": 4, "z": 2, "y": 0, "facing": 0}]}]}
            (folder / "inventory.json").write_text(json.dumps(inventory))
            settle.write_layout({"crate_1": {"before": before, "after": rolled @ before, "middle": [0, 0.5, 0]}},
                                None, folder / "inventory.json", folder / "kit.json")
            piece = json.loads((folder / "kit.json").read_text())["pieces"][0]
            if marked and (piece["at"] != [4, 0, 2] or "rotation" in piece or "turns 40" not in piece["unrested"]):
                problems.append(f"a 40 degree roll of a 3 m piece was not refused and marked: {piece}")
            if not marked and ("rotation" not in piece or "unrested" in piece):
                problems.append(f"a 40 degree roll of 1 m debris was not written: {piece}")
        return problems


def a_tip_onto_uneven_feet_is_refused():
    """Both ways, on the greenhouse's water tank's own legs (ending 0, 2.2, 5.2 and 12.7 cm up, 2026-10-12): its
    7.5 degree tip onto three of them keeps its laid pose and is marked, while a crate on an even base tipped as much
    is written."""
    import test_a_creators_edit_survives_a_regenerated_base as export_test
    import test_only_real_resting_faults_are_kept as triage_test
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        export_test.box_gltf(folder / "models", "tank", triage_test.legged_tank((0.0, 0.022, 0.052, 0.127)))
        path = resting_test.laid_place(folder, [("tank", "tank", (4, 0, 2)), ("crate", "box", (8, 0, 2))],
                                       [("tank", "floor"), ("crate", "floor")])
        stage = Usd.Stage.Open(str(path))
        settled = {}
        for name in ("tank_1", "crate_1"):
            before = stage_matrix(path, name)
            tipped = np.eye(4)
            tipped[:3, :3] = Rotation.from_euler("x", 7.5, degrees=True).as_matrix()
            tipped[:3, 3] = before[:3, 3] - tipped[:3, :3] @ before[:3, 3]
            settled[name] = {"before": before, "after": tipped @ before, "middle": [0, 0.5, 0],
                             "uneven": settle.uneven_feet(stage, PLACE, name)}
        inventory = {"rows": [{"id": row, "anchor": "floor", "at": [{"x": x, "z": 2, "y": 0, "facing": 0}]}
                              for row, x in (("tank", 4), ("crate", 8))]}
        (folder / "inventory.json").write_text(json.dumps(inventory))
        settle.write_layout(settled, None, folder / "inventory.json", folder / "kit.json")
        tank, crate = json.loads((folder / "kit.json").read_text())["pieces"]
        problems = []
        if abs(settled["tank_1"]["uneven"] - 0.127) > 0.002 or settled["crate_1"]["uneven"] != 0.0:
            problems.append(f"feet measured {settled['tank_1']['uneven']} (tank) and {settled['crate_1']['uneven']}")
        if "rotation" in tank or "level the model's feet" not in tank.get("unrested", ""):
            problems.append(f"the tank's tip onto uneven feet was written: {tank}")
        if "rotation" not in crate or "unrested" in crate:
            problems.append(f"the crate's 7.5 degree settle was not written: {crate}")
        return problems



def a_tip_onto_a_base_joined_as_one_foot_is_refused():
    """Both ways, as the lab's desk chairs (2026-10-15: five casters joined by a star base, one 2.4 cm up, read as one
    even foot and their 4.8 degree tip written): a block whose base slopes 5 degrees is one foot to the clusters, yet
    its tip onto that base is refused by the lean of its hull under its weight, while a crate's is written."""
    import test_a_creators_edit_survives_a_regenerated_base as export_test
    import test_only_real_resting_faults_are_kept as triage_test
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        export_test.box_gltf(folder / "models", "wedge", triage_test.wedge(5.0))
        path = resting_test.laid_place(folder, [("wedge", "wedge", (4, 0, 2)), ("crate", "box", (8, 0, 2))],
                                       [("wedge", "floor"), ("crate", "floor")])
        stage = Usd.Stage.Open(str(path))
        settled = {}
        for name in ("wedge_1", "crate_1"):
            before = stage_matrix(path, name)
            tipped = np.eye(4)
            tipped[:3, :3] = Rotation.from_euler("x", 5.0, degrees=True).as_matrix()
            tipped[:3, 3] = before[:3, 3] - tipped[:3, :3] @ before[:3, 3]
            settled[name] = {"before": before, "after": tipped @ before, "middle": [0, 0.5, 0],
                             "uneven": settle.uneven_feet(stage, PLACE, name),
                             "base lean": settle.base_lean(stage, PLACE, name)}
        problems = []
        if settled["wedge_1"]["uneven"] > settle.resting.TOLERANCE or abs(settled["wedge_1"]["base lean"] - 5.0) > 0.1 \
                or settled["crate_1"]["base lean"] > 0.1:
            problems.append(f"measured {settled['wedge_1']} (wedge) and {settled['crate_1']} (crate)")
        if not settle.tips_on_uneven_feet(settled["wedge_1"]) or settle.tips_on_uneven_feet(settled["crate_1"]):
            problems.append("the wedge's tip onto its sloping base was written, or the crate's refused")
        return problems

def only_floor_pieces_are_dropped():
    """A crate on the floor is dropped; a kit's floor plate (a shell group the triage holds fixed) and a row on the wall
    are not."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (0, 0, 0)), ("plate", "box", (3, 0, 0)),
                                                ("panel", "box", (6, 0, 0))],
                                       [("crate", "floor"), ("plate", "floor"), ("panel", "wall")])
        inventory = json.loads((folder / "inventory.json").read_text())
        inventory["rows"][1]["group"] = "kit: floor"
        loose = settle.loose_objects(Usd.Stage.Open(str(path)), PLACE, inventory)
        return [] if set(loose) == {"crate_1"} else [f"the drop takes {sorted(loose)}, not the crate alone"]


def a_glowing_part_is_no_static_of_the_drop():
    """A lamp's glow (a `_glow` row, judged with its host) is left out of the drop's statics; the lamp is not."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("lamp", "box", (0, 0, 0)), ("lamp_glow", "box", (0, 0, 0))],
                                       [("lamp", "floor"), ("lamp_glow", "floor")])
        inventory = json.loads((folder / "inventory.json").read_text())
        ignored = settle.part_objects(Usd.Stage.Open(str(path)), PLACE, inventory)
        return [] if ignored == ["lamp_glow_1"] else [f"the drop leaves out {ignored}, not the glow alone"]


def what_lies_on_a_dropped_piece_is_no_static_of_the_drop():
    """A tray held on a shelf that is dropped (`on:shelf`) is left out of the drop's statics; a lamp on the wall is not."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("shelf", "box", (0, 0, 0)), ("tray", "box", (0, 1, 0)),
                                                ("lamp", "box", (3, 1, 0))],
                                       [("shelf", "floor"), ("tray", "on:shelf"), ("lamp", "wall")])
        inventory = json.loads((folder / "inventory.json").read_text())
        stage = Usd.Stage.Open(str(path))
        ignored = settle.held_on_loose(stage, PLACE, inventory, settle.loose_objects(stage, PLACE, inventory))
        return [] if ignored == ["tray_1"] else [f"the drop leaves out {ignored}, not the tray alone"]


def a_fixture_on_a_dropped_piece_is_no_static_of_the_drop():
    """A scene record fixture lying on a crate that is dropped (a tray on the workshop's bench) is left out of the drop's
    statics; one standing on the floor beside it is not."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (0, 0, 0))], [("crate", "floor")])
        inventory = json.loads((folder / "inventory.json").read_text())
        stage = Usd.Stage.Open(str(path))
        top = float(UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(
            stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")).ComputeAlignedRange().GetMax()[1])
        for name, at in (("tray", (0.0, top + 0.05, 0.0)), ("barrel", (3.0, 0.1, 0.0))):
            holder = UsdGeom.Xform.Define(stage, f"/{PLACE}/Fixtures/{name}")
            holder.AddTranslateOp().Set(at)
            UsdGeom.Cube.Define(stage, f"/{PLACE}/Fixtures/{name}/mesh_0").GetSizeAttr().Set(0.1)
        ignored = settle.fixtures_on_loose(stage, PLACE, settle.loose_objects(stage, PLACE, inventory))
        return [] if ignored == ["tray"] else [f"the drop leaves out the fixtures {ignored}, not the tray alone"]


def what_lies_on_a_settled_piece_moves_with_it():
    """A tray held on a crate (`on:crate`) is carried by the crate's settled motion; a crate that would turn too far
    to be written carries nothing."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (0, 0, 0)), ("tray", "box", (0, 1, 0)),
                                                ("crate", "box", (3, 0, 0)), ("tray", "box", (3, 1, 0))],
                                       [("crate", "floor"), ("tray", "on:crate")])
        inventory = json.loads((folder / "inventory.json").read_text())
        stage = Usd.Stage.Open(str(path))
        small, large = np.eye(4), np.eye(4)
        small[:3, :3] = Rotation.from_euler("z", 3.0, degrees=True).as_matrix()
        small[:3, 3] = [0.02, 0.0, 0.01]
        large[:3, :3] = Rotation.from_euler("z", 60.0, degrees=True).as_matrix()
        settled = {}
        for name, motion in (("crate_1", small), ("crate_2", large)):
            before = settle.laid_matrix(stage, PLACE, name)
            settled[name] = {"before": before, "after": motion @ before, "middle": settle.object_middle(stage, PLACE, name)}
        carried = settle.carried_with(stage, PLACE, inventory, settled)
        problems = [] if sorted(carried) == ["tray_1"] else [f"carried {sorted(carried)}, not the first tray alone"]
        if "tray_1" in carried and not np.allclose(carried["tray_1"]["after"], small @ carried["tray_1"]["before"]):
            problems.append("the tray did not move as its crate moved")
        return problems


def a_kit_room_piece_moves_with_its_object():
    """A kit room's piece (the game's kit: axes and a foot `at`, no inventory spot) moved by a settle's small turn and
    drift stands, by package.kit_matrix, exactly where its object came to rest; a name finds its piece by kind."""
    sys.path.insert(0, str(HERE.parents[1] / "tools/props/library"))
    import package
    low, high = np.array([-0.3, 0.0, -0.2]), np.array([0.5, 0.9, 0.4])
    piece = {"kind": "lab_desk", "at": [1.0, 0.0, -2.0], "x": [0.0, 0.0, 1.0], "y": [0.0, 1.0, 0.0],
             "z": [-1.0, 0.0, 0.0], "size": [1.2, 0.75, 0.6], "model": "desk_1"}
    before, _ = package.kit_matrix(piece, low, high)
    motion = np.eye(4)
    motion[:3, :3] = Rotation.from_euler("xz", [4.0, -3.0], degrees=True).as_matrix()
    motion[:3, 3] = [0.05, -0.01, 0.12]
    after = motion @ before
    moved, _ = package.kit_matrix(settle.moved_piece(piece, before, after), low, high)
    problems = [] if np.allclose(moved, after, atol=1e-4) else [f"the moved piece stands at {moved}, not {after}"]
    kit = {"room": "lab", "pieces": [piece, dict(piece), dict(piece, kind="lab_desk_lamp", part="glow")]}
    names = sorted(settle.kit_room_pieces(kit, "lab"))
    return problems + ([] if names == ["desk_1", "desk_2", "desk_lamp_glow_1"] else [f"the room's names are {names}"])


def tipped_place(folder, pieces):
    """A place of 1 m boxes (row, at, degrees tipped about x) laid loose on the floor, exported; its stage's path."""
    kit = {"place": PLACE, "lamps": [], "children": [],
           "pieces": [{"prop": f"test_{row}", "kind": f"test_{row}", "model": "box", "row": row, "size": [1.0] * 3,
                       "at": list(at), "facing": 30.0,
                       "rotation": Rotation.from_euler("yx", [-30.0, degrees], degrees=True).as_quat().tolist()}
                      for row, at, degrees in pieces]}
    inventory = {"rows": [{"id": row, "name": row, "anchor": "floor", "thing": f"prop:test_{row}"}
                          for row in sorted({row for row, _, _ in pieces})]}
    (folder / "kit.json").write_text(json.dumps(kit))
    (folder / "inventory.json").write_text(json.dumps(inventory))
    return resting_test.export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                                      inventory_path=folder / "inventory.json")


def a_tipped_piece_drops_from_upright_and_a_stacked_one_meets_its_holder():
    """A crate an old settle left 6 degrees tipped starts its drop upright (its facing and middle kept), one laid
    40 degrees over keeps its pose, and a crate laid on a crate meets it in the drop."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = tipped_place(folder, [("crate", (0, 0, 0), 6.0), ("crate", (4, 0, 0), 40.0), ("box", (8, 0, 0), 0.0),
                                     ("box", (8, 1.0, 0), 0.0)])
        stage = Usd.Stage.Open(str(path))
        inventory = json.loads((folder / "inventory.json").read_text())
        names = ("crate_1", "crate_2", "box_1", "box_2")
        starts = settle.upright_starts(stage, PLACE, inventory, names, None)
        under = settle.stacked_under(stage, PLACE, names)
        problems = []
        if sorted(starts) != ["crate_1"]:
            problems.append(f"upright starts for {sorted(starts)}, not crate_1 alone")
        else:
            laid = stage_matrix(path, "crate_1")
            upright = starts["crate_1"] @ laid
            turn = upright[:3, :3]
            facing = settle.heading_of(laid[:3, :3])
            if not np.allclose(turn[:, 1], [0, 1, 0], atol=1e-6) or abs(settle.heading_of(turn) - facing) > 1e-3:
                problems.append(f"crate_1 starts with up {turn[:, 1]} facing {settle.heading_of(turn)}")
            middle = np.append(settle.object_middle(stage, PLACE, "crate_1"), 1.0)
            if not np.allclose(upright @ middle, laid @ middle, atol=1e-6):
                problems.append("crate_1's middle moved as it was stood upright")
        if under != {"box_2": ["box_1"]}:
            problems.append(f"stacked: {under}")
        return problems


def a_crate_laid_across_two_starts_wholly_on_the_one_it_overlaps_most():
    """A 1 m crate laid across two (0.6 m over one, 0.2 m over the other) starts its drop moved 0.4 m back onto the
    first alone, and meets only it."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = tipped_place(folder, [("crate", (8, 0, 0), 0.0), ("crate", (9.2, 0, 0), 0.0),
                                     ("crate", (8.4, 1.0, 0), 0.0)])
        stage = Usd.Stage.Open(str(path))
        under = settle.stacked_under(stage, PLACE, ("crate_1", "crate_2", "crate_3"))
        found = settle.onto_one_support(stage, PLACE, under)
        support, shift = found.get("crate_3", (None, np.eye(4)))
        if support != "crate_1" or not np.allclose(shift[:3, 3], [-0.4, 0.0, 0.0], atol=0.02):
            return [f"crate_3 starts over {support}, moved {shift[:3, 3]}"]
        return []


def a_piece_on_a_slope_rests_flush_on_it():
    """Both ways: a crate laid 17 degrees over on the test's 5.7 degree slope (the campgrounds' crane) is stood flush
    on the slope, its up along the ground's normal and its lowest point on the ground, heading kept; one on level
    ground, and one whose row says it leans, are left to the drop."""
    import triage
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        sloped = resting_test.sloping_ground(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (4, 0, 2)), ("ramp", "box", (-4, 0, 2))],
                                       [("crate", "floor"), ("ramp", "floor")], sloped)
        kit = json.loads((folder / "kit.json").read_text())
        for piece in kit["pieces"]:
            piece["tilt"] = 17.0
        (folder / "kit.json").write_text(json.dumps(kit))
        path = resting_test.export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                                          inventory_path=folder / "inventory.json", ground=sloped)
        stage = Usd.Stage.Open(str(path))
        ground_of = resting.ground_height(stage, PLACE)
        rows = {"crate": {"id": "crate", "anchor": "floor"}, "ramp": {"id": "ramp", "anchor": "floor", "leans": "cut"}}
        found = settle.flush_on_slope(stage, PLACE, "crate_1", rows, triage.rules(), ground_of)
        problems = []
        if found is None:
            return ["the tipped crate on the slope was not stood flush"]
        after = found[0] @ stage_matrix(path, "crate_1")
        points = settle.object_points(stage, PLACE, "crate_1") @ found[0][:3, :3].T + found[0][:3, 3]
        up = after[:3, 1] / np.linalg.norm(after[:3, 1])
        plane = triage.ground_plane(resting_test.trimesh.PointCloud(points), ground_of)  # the ball curves it a little
        normal = np.array([-plane[0], 1.0, -plane[1]]) / np.linalg.norm([plane[0], 1.0, plane[1]])
        if np.degrees(np.arccos(min(1.0, abs(up @ normal)))) > 0.5:
            problems.append(f"the crate's up stands {np.degrees(np.arccos(abs(up @ normal))):.1f} degrees off the slope")
        if abs(np.nanmin(points[:, 1] - ground_of(points[:, [0, 2]]))) > 0.005:
            problems.append("the flush crate does not meet the ground")
        if settle.flush_on_slope(stage, PLACE, "ramp_1", rows, triage.rules(), ground_of) is not None:
            problems.append("a row that leans was stood flush")
        level = lambda flat: np.zeros(len(np.atleast_2d(flat)))  # noqa: E731
        if settle.flush_on_slope(stage, PLACE, "crate_1", rows, triage.rules(), level) is not None:
            problems.append("a crate on level ground was stood flush instead of dropped")
        return problems


def a_box_stacked_on_a_box_on_a_slope_meets_it():
    """Two boxes tipped 8 degrees as on a slope, one laid on the other's top, are stacked; one laid 10 cm higher is
    not: the stage's boxes put the upper's bottom 14 cm under the lower's top (the campgrounds' cargo case 1 on its
    pallet, 2026-10-15)."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        top = Rotation.from_euler("yx", [-30.0, 8.0], degrees=True).apply([0.0, 1.0, 0.0])
        path = tipped_place(folder, [("box", (8, 0, 0), 8.0), ("box", tuple([8, 0, 0] + top), 8.0),
                                     ("box", (12, 0, 0), 8.0), ("box", tuple([12, 0.1, 0] + top), 8.0)])
        stage = Usd.Stage.Open(str(path))
        under = settle.stacked_under(stage, PLACE, ("box_1", "box_2", "box_3", "box_4"))
        return [] if under == {"box_2": ["box_1"]} else [f"stacked: {under}"]


def a_stacked_box_begun_inside_its_support_starts_over_it():
    """Both ways, on the 8 degree slope: a box laid 3 cm into the box under it begins its drop lifted to 2 cm over
    that box's top (SETTLE_DROP), not inside its hull, which the drop throws it out of (the campgrounds' cargo case 1
    turned 179 degrees onto the next pallet, 2026-10-15); one laid 10 cm over it is not lifted."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        up = Rotation.from_euler("yx", [-30.0, 8.0], degrees=True).apply([0.0, 1.0, 0.0])
        path = tipped_place(folder, [("box", (8, 0, 0), 8.0), ("box", tuple([8, 0, 0] + 0.97 * up), 8.0),
                                     ("box", (12, 0, 0), 8.0), ("box", tuple([12, 0, 0] + 1.1 * up), 8.0)])
        stage = Usd.Stage.Open(str(path))
        inside = settle.stack_lift(stage, PLACE, "box_2", np.eye(4), "box_1")
        over = settle.stack_lift(stage, PLACE, "box_4", np.eye(4), "box_3")
        problems = []
        if abs(inside - (0.03 + settle.SETTLE_DROP)) > 0.002:
            problems.append(f"box_2, 3 cm inside box_1, lifted {inside:.3f} m, not {0.03 + settle.SETTLE_DROP} m")
        if over != 0.0:
            problems.append(f"box_4, 10 cm over box_3, lifted {over:.3f} m")
        return problems


def a_cloud_drop_asks_the_small_processor_class_only():
    """#20, #21: a drop asks the small processor class only, a class the backend sells: no chain to bigger ones."""
    sys.path.insert(0, str(HERE.parents[1] / "tools/cloud"))
    import blender_cloud
    from backends import scaleway

    asked = []
    real = blender_cloud.run_elsewhere
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = folder / "place.usda"
        stage.write_text("#usda 1.0\n")

        def run_elsewhere(script, arguments, inputs, outputs, classes, who, minutes=10):
            asked.append(tuple(classes))
            pathlib.Path(arguments[2]).write_text("{}")

        blender_cloud.run_elsewhere = run_elsewhere
        try:
            settle.simulate(stage, {}, folder / "drop", cloud=True)
        finally:
            blender_cloud.run_elsewhere = real
    wanted = settle.DROP_CLASSES
    problems = [] if asked == [wanted] else [f"the drop asked {asked}, not {wanted}"]
    return problems + [f"{name} is sold by no backend class" for name in settle.DROP_CLASSES
                       if name not in scaleway.CLASSES]


def a_turn_about_up_is_no_tip_and_debris_is_sized_in_its_own_frame():
    """A spin about up onto uneven feet is no tip (a lean is); an object's size for the debris rule is its own, as its
    kit piece's size says it, the same however it is turned (a stage-frame box round it grows as it turns)."""
    problems = []
    for turn, tips in (("y", False), ("x", True)):
        motion = np.eye(4)
        motion[:3, :3] = Rotation.from_euler(turn, 30, degrees=True).as_matrix()
        if settle.tips_on_uneven_feet({"before": np.eye(4), "after": motion, "uneven": 0.1}) != tips:
            problems.append(f"a 30 degree turn about {turn} onto uneven feet read as tip={not tips}")
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (4, 0, 2))], [("crate", "floor")])
        stage = Usd.Stage.Open(str(path))
        prim = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
        laid = settle.laid_matrix(stage, PLACE, "crate_1")
        size = settle.own_size(stage, PLACE, "crate_1")
        turned = np.eye(4)
        turned[:3, :3] = Rotation.from_euler("y", 45, degrees=True).as_matrix()
        UsdGeom.Xformable(prim).MakeMatrixXform().Set(Gf.Matrix4d((turned @ laid).T.tolist()))
        if abs(settle.own_size(stage, PLACE, "crate_1") - size) > 1e-6:
            problems.append(f"turning the crate 45 degrees changed its own size from {size}")
    return problems


CHECKS = (a_turn_about_up_is_no_tip_and_debris_is_sized_in_its_own_frame, a_cloud_drop_asks_the_small_processor_class_only, a_piece_on_a_slope_rests_flush_on_it, a_tipped_piece_drops_from_upright_and_a_stacked_one_meets_its_holder,
          a_box_stacked_on_a_box_on_a_slope_meets_it,
          a_stacked_box_begun_inside_its_support_starts_over_it,
          a_crate_laid_across_two_starts_wholly_on_the_one_it_overlaps_most,
          a_settled_pose_round_trips_through_the_layout, a_kit_room_piece_moves_with_its_object, only_floor_pieces_are_dropped, a_glowing_part_is_no_static_of_the_drop,
          what_lies_on_a_dropped_piece_is_no_static_of_the_drop,
          a_fixture_on_a_dropped_piece_is_no_static_of_the_drop, what_lies_on_a_settled_piece_moves_with_it, a_big_turn_is_marked_not_made,
          a_tip_onto_uneven_feet_is_refused,
          a_tip_onto_a_base_joined_as_one_foot_is_refused)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
