"""Check the settle's write-back and the levelled yard on places made here, without Blender: a pose an object came to
rest in (tipped a little on a sloping planned ground) written into the layout as spot, lift and rotation, and exported
again, stands exactly where it rested; a 3 m piece that would turn 40 degrees to rest keeps its laid pose and is
marked, while 1 m debris may turn so; a kit room's piece (the game's kit) moves with its object, only floor pieces are dropped, not a kit's floor plate, and neither a glow nor what lies on a dropped piece is a static of the drop; a
levelled box of the plan is flat and eases back into the ground.

Run: .venv/bin/python tools/usd/settle_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
from pxr import Usd, UsdGeom
from scipy.spatial.transform import Rotation

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ground  # noqa: E402
import resting_test  # noqa: E402
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


def a_levelled_yard_is_flat_and_eases_out():
    heights = np.tile(np.linspace(-2.0, 2.0, 65), (65, 1))
    found = ground.levelled(heights, 64.0, np.array([-5.0, -5.0]), np.array([5.0, 5.0]), 0.25, 4.0)
    at = (np.arange(65) / 64 - 0.5) * 64.0
    inside = (np.abs(at) <= 5.0)
    problems = []
    if np.abs(found[np.ix_(inside, inside)] - 0.25).max() > 1e-9:
        problems.append("the levelled box is not held at its height")
    far = np.abs(at) > 9.5
    if np.abs(found[np.ix_(far, far)] - heights[np.ix_(far, far)]).max() > 1e-9:
        problems.append("the ground past the bank was changed")
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


def a_dent_is_a_shallow_bowl():
    with tempfile.TemporaryDirectory() as temporary:
        sloped = resting_test.sloping_ground(pathlib.Path(temporary))
        before = sloped.heights.copy()
        after = ground.dented(sloped, before, 2.0, 1.0, 0.6, 0.08)
        change = after - before
        problems = []
        middle = sloped.direction(sloped.frame, sloped.origin, 2.0, 1.0)
        sloped.heights = before
        was = sloped.plan_height(middle)[0][0]
        sloped.heights = after
        now = sloped.plan_height(middle)[0][0]
        if not 0.05 < was - now <= 0.08:
            problems.append(f"the dent's middle is {(was - now) * 100:.1f} cm deep, not about 8")
        if change.max() > 0 or change.min() < -0.0801:
            problems.append("the dent raised the ground or went deeper than asked")
        far = sloped.direction(sloped.frame, sloped.origin, 6.0, 1.0)
        sloped.heights = before
        far_before = sloped.plan_height(far)[0][0]
        sloped.heights = after
        if abs(sloped.plan_height(far)[0][0] - far_before) > 1e-9:
            problems.append("the ground 4 m from the dent moved")
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


CHECKS = (a_settled_pose_round_trips_through_the_layout, a_kit_room_piece_moves_with_its_object, only_floor_pieces_are_dropped, a_glowing_part_is_no_static_of_the_drop,
          what_lies_on_a_dropped_piece_is_no_static_of_the_drop, a_big_turn_is_marked_not_made,
          a_levelled_yard_is_flat_and_eases_out, a_dent_is_a_shallow_bowl)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
