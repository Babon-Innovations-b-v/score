"""Check the resting check, and the ground objects are stood on, on places made here: a box on the ground rests, one
lifted floats, one laid into the ground is sunk however its layout lifted it, a plank held up at one end tips, a hung
object is not checked, and a box laid on a sloping planned ground stands on it.

Run: .venv/bin/python tools/usd/resting_test.py   (make tests runs it with the framework's environment)
"""
import json
import math
import pathlib
import sys
import tempfile

import numpy as np
import trimesh
from PIL import Image
from pxr import Usd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import export  # noqa: E402
import export_test  # noqa: E402
import ground  # noqa: E402
import resting  # noqa: E402

PLACE = export_test.PLACE
SLOPE = 0.1  # the test ground rises this many metres a metre across


def plank_on_a_leg():
    """A 2 m plank 0.5 m up held by one leg at its far end: its weight hangs outside what it stands on."""
    plank = trimesh.creation.box(bounds=((-1.0, 0.45, -0.2), (1.0, 0.5, 0.2)))
    leg = trimesh.creation.box(bounds=((0.9, 0.0, -0.05), (1.0, 0.45, 0.05)))
    return trimesh.util.concatenate([plank, leg])


def laid_place(folder, pieces, rows, ground_at=None):
    """A place of these pieces (row, model, at) and inventory rows (id, anchor), exported; its stage's path."""
    kit = {"place": PLACE, "lamps": [], "children": [],
           "pieces": [{"prop": f"test_{row}", "kind": f"test_{row}", "model": model, "row": row,
                       "size": [1.0, 1.0, 1.0], "at": list(at), "facing": 0.0} for row, model, at in pieces]}
    inventory = {"rows": [{"id": row, "name": row, "anchor": anchor, "thing": f"prop:test_{row}"}
                          for row, anchor in rows]}
    (folder / "kit.json").write_text(json.dumps(kit))
    (folder / "inventory.json").write_text(json.dumps(inventory))
    return export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                         inventory_path=folder / "inventory.json", ground=ground_at)


def made_models(folder):
    (folder / "models").mkdir()
    export_test.box_gltf(folder / "models")
    export_test.box_gltf(folder / "models", "plank", plank_on_a_leg())


def results(stage_path):
    return {found["object"]: found for found in resting.check(stage_path)}


def floating_sunk_and_hung_are_told_apart():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_models(folder)
        path = laid_place(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (3, 0.2, 0)),
                                   ("crate", "box", (6, -0.2, 0)), ("lamp", "box", (9, 1.5, 0))],
                          [("crate", "floor"), ("lamp", "wall")])
        found = results(path)
        expected = {"crate_1": "rests", "crate_2": "floats", "crate_3": "sunk", "lamp_1": "hung"}
        return [f"{name} reads '{found[name]['result']}', not '{word}...'" for name, word in expected.items()
                if not found[name]["result"].startswith(word)]


def a_plank_held_at_one_end_tips():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_models(folder)
        found = results(laid_place(folder, [("plank", "plank", (0, 0, 0))], [("plank", "floor")]))["plank_1"]
        if not found["result"].startswith("tips"):
            return [f"the plank on one leg reads '{found['result']}'"]
        if not 0.8 <= found["outside"] <= 1.0:
            return [f"the plank's weight is {found['outside']} m outside its leg, not about 0.9 m"]
        return []


def sloping_ground(folder):
    """A ground record for a plan rising SLOPE a metre across, its seat facing straight out from the plan's middle."""
    side, low, span, size = 64.0, 20.0, 40.0, 129
    across = (np.arange(size) / (size - 1) - 0.5) * side
    code = np.round((np.tile(across * SLOPE, (size, 1)) + low) / span * 65535).astype(np.int64)
    pixels = np.stack([code >> 8, code & 255, np.zeros_like(code)], axis=-1).astype(np.uint8)
    Image.fromarray(pixels).save(folder / "heights.png")
    Image.new("RGB", (64, 64), (120, 118, 115)).save(folder / "skin.jpg")
    record = {"heights": "heights.png", "skin": "skin.jpg", "side": side, "low": low, "span": span,
              "radius": 220.0, "plan_out": [0.0, 1.0, 0.0], "folder": str(folder)}
    return ground.Ground(record, {"out": [0.0, 1.0, 0.0], "heading": 0.0}, [0.0, 0.0])


def a_box_stands_on_the_planned_ground():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_models(folder)
        sloped = sloping_ground(folder)
        path = laid_place(folder, [("crate", "box", (5, 0, 0)), ("crate", "box", (-5, 0.3, 0))], [("crate", "floor")],
                          sloped)
        stage = Usd.Stage.Open(str(path))
        problems = []
        standing = stage.GetPrimAtPath(f"/{PLACE}/Objects/crate_1").GetAttribute("xformOp:translate").Get()
        if abs(standing[1] - sloped.standing(5.0, 0.0, 0.0)[0][1]) > 1e-6 or abs(standing[1] - 5 * SLOPE) > 0.1:
            problems.append(f"the box laid 5 m across stands at {standing[1]:.3f} m, not on the ground there")
        if not stage.GetPrimAtPath(f"/{PLACE}/Ground").IsValid():
            problems.append("the stage has no Ground")
        found = results(path)
        if found["crate_1"]["result"].startswith("floats"):
            problems.append(f"the box on the slope reads '{found['crate_1']['result']}'")
        if not found["crate_2"]["result"].startswith("floats"):
            problems.append(f"the box lifted 0.3 m off the slope reads '{found['crate_2']['result']}'")
        return problems


def two_boxes_inside_each_other_overlap():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        made_models(folder)
        found = results(laid_place(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (0.6, 0, 0)),
                                            ("crate", "box", (3, 0, 0))], [("crate", "floor")]))
        problems = []
        for name in ("crate_1", "crate_2"):
            if "overlaps" not in found[name]["result"]:
                problems.append(f"{name}, 40 cm inside the other box, reads '{found[name]['result']}'")
        if found["crate_3"]["result"] != "rests":
            problems.append(f"the box standing apart reads '{found['crate_3']['result']}'")
        return problems


def a_room_lies_flat_on_its_seat_over_a_dug_pit():
    """A room laid flat on the base seat (`flat`) has its middle there on the seat's plane, its frame the seat's turned
    by its heading, and the ground under the base's pit dug out past the pit's floor (`dug`), as the game's Ground digs
    it; out past the dig the ground is the plan's again."""
    with tempfile.TemporaryDirectory() as temporary:
        sloped = sloping_ground(pathlib.Path(temporary))
        record = {"heights": "heights.png", "skin": "skin.jpg", "side": 64.0, "low": 20.0, "span": 40.0,
                  "radius": 220.0, "plan_out": [0.0, 1.0, 0.0], "folder": temporary,
                  "dug": {"radius": 2.33, "deep": 0.9}}
        room = ground.Ground(record, {"out": [0.0, 1.0, 0.0], "heading": math.pi / 2, "flat": [-9.0, 0.0]}, [0, 0])
        problems = []
        if not np.allclose(room.origin, [-9.0, 220.0, 0.0]):
            problems.append(f"the room's middle stands at {room.origin}, not 9 m across the seat's plane")
        if not np.allclose(room.in_place_frame(np.array([0.0, 220.0, 0.0]))[0], [0.0, 0.0, 9.0], atol=1e-9):
            problems.append("the seat's middle is not 9 m along the room turned a quarter round")
        hub = ground.Ground(record, {"out": [0.0, 1.0, 0.0], "heading": math.pi, "flat": [0.0, 0.0]}, [0, 0])
        points, _, _ = hub.mesh(np.array([0.0, 0.0]), np.array([0.0, 0.0]), 8.0, 0.5)
        middle = points[np.argmin(np.hypot(points[:, 0], points[:, 2]))]
        if abs(middle[1] + 1.2) > 1e-6:
            problems.append(f"the ground under the pit stands at {middle[1]:.3f}, not dug 0.3 past its 0.9 floor")
        far = points[np.argmin(np.hypot(points[:, 0] + 7.0, points[:, 2]))]
        if abs(far[1] - sloped.standing(7.0, 0.0, 0.0)[0][1]) > 0.02:
            problems.append(f"7 m out the ground stands at {far[1]:.3f}, not the plan's own height")
        return problems


CHECKS = (floating_sunk_and_hung_are_told_apart, a_plank_held_at_one_end_tips, a_box_stands_on_the_planned_ground,
          two_boxes_inside_each_other_overlap, a_room_lies_flat_on_its_seat_over_a_dug_pit)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
