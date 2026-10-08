"""Check the settle's write-back and the levelled yard on places made here, without Blender: a pose an object came to
rest in (tipped a little on a sloping planned ground) written into the layout as spot, lift and rotation, and exported
again, stands exactly where it rested; one that would turn 40 degrees to rest keeps its laid pose and is marked; a
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
        inventory = {"rows": [{"id": "crate", "anchor": "floor", "at": [{"x": 4, "z": 2, "y": 0, "facing": 0}]}]}
        (folder / "inventory.json").write_text(json.dumps(inventory))
        settle.write_layout({"crate_1": {"before": before, "after": rolled @ before, "middle": [0, 0.5, 0]}}, None,
                            folder / "inventory.json", folder / "kit.json")
        piece = json.loads((folder / "kit.json").read_text())["pieces"][0]
        problems = []
        if piece["at"] != [4, 0, 2] or "rotation" in piece:
            problems.append(f"a 40 degree roll was written into the layout: {piece}")
        if "turns 40 degrees" not in piece.get("unrested", ""):
            problems.append(f"the piece that would roll is not marked: {piece}")
        return problems


CHECKS = (a_settled_pose_round_trips_through_the_layout, a_big_turn_is_marked_not_made,
          a_levelled_yard_is_flat_and_eases_out)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
