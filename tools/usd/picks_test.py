"""Check the pick lock and the render-and-compare's arithmetic: an export keeps a picked model and writes both hashes
on its object; an export that would show another model for a picked row, or none, is refused; a written owner decision
lets it through; the stage check finds a picked row showing another model; a row picked as several models (a piece's
variants) keeps each and refuses one swapped; a scene record's object that stands for a row (the launch's rocket) is
locked like a laid one; and a close-up's mask and the outline score
read a plain picture right.

Run: .venv/bin/python tools/usd/picks_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np
from PIL import Image
from pxr import Usd

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare  # noqa: E402
import complete  # noqa: E402
import export  # noqa: E402
import picks  # noqa: E402
import resting_test  # noqa: E402
import triage_test  # noqa: E402

PLACE = resting_test.PLACE


def picked_row(folder, model, **more):
    """A crate row picked to this model of the folder's made models."""
    pick = {"model": model, "sha256": complete.model_hash(folder / "models" / f"{model}.gltf"),
            "decided": "owner, 2026-10-09: this take"}
    return triage_test.row("crate", pick=pick, **more)


def a_kept_pick_exports_with_its_hashes():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        stage = triage_test.place_of(folder, [("crate", "box", (0, 0, 0))], [picked_row(folder, "box")])
        opened = Usd.Stage.Open(str(stage))
        prim = opened.GetPrimAtPath(f"/{PLACE}/Objects/crate_1")
        model, pick = prim.GetAttribute("score:model_sha256").Get(), prim.GetAttribute("score:pick_sha256").Get()
        problems = [] if model and model == pick else [f"the object carries model {model} and pick {pick}"]
        found, locked = picks.check(stage, json.loads((folder / "inventory.json").read_text()))
        if found or locked != 1:
            problems.append(f"the stage check reads {found}, {locked} locked")
        return problems


def a_replaced_pick_is_refused_without_a_decision():
    problems = []
    for rows in (lambda folder: [picked_row(folder, "plank")],
                 lambda folder: [picked_row(folder, "box"), triage_test.row("lamp")]):
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            resting_test.made_models(folder)
            pieces = [("crate", "box", (0, 0, 0))] if rows(folder)[0]["pick"]["model"] == "plank" else \
                [("lamp", "box", (0, 0, 0))]
            try:
                triage_test.place_of(folder, pieces, rows(folder))
                problems.append(f"an export showing {pieces} for a row picked to {rows(folder)[0]['pick']['model']} "
                                "was written")
            except picks.PickBroken:
                pass
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        try:
            triage_test.place_of(folder, [("crate", "box", (0, 0, 0))],
                                 [picked_row(folder, "plank", pick_replaced="owner, 2026-10-09: the box now")])
        except picks.PickBroken as refused:
            problems.append(f"a replacement the owner wrote down was refused: {refused}")
    return problems


def a_row_of_several_models_keeps_each():
    problems = []
    for allowed, refused in ((("box", "plank"), False), (("box",), True)):
        with tempfile.TemporaryDirectory() as temporary:
            folder = pathlib.Path(temporary)
            resting_test.made_models(folder)
            pick = {"models": {model: complete.model_hash(folder / "models" / f"{model}.gltf") for model in allowed},
                    "decided": "owner, 2026-10-09: these takes"}
            try:
                triage_test.place_of(folder, [("crate", "box", (0, 0, 0)), ("crate", "plank", (3, 0, 0))],
                                     [triage_test.row("crate", pick=pick)])
                if refused:
                    problems.append(f"a row picked as {allowed} was exported showing a plank too")
            except picks.PickBroken as broken:
                if not refused:
                    problems.append(f"a row picked as {allowed} was refused showing them: {broken}")
    return problems


def scene_rocket(folder, model):
    """A place with no kit pieces whose scene record stands one rocket (this model of the folder's) for the row
    `rocket`, picked to the box; its stage, or the lock's refusal."""
    kit = {"place": PLACE, "lamps": [], "children": [], "pieces": []}
    (folder / "kit.json").write_text(json.dumps(kit))
    pick = {"model": "box", "sha256": complete.model_hash(folder / "models/box.gltf"), "decided": "owner, 2026-10-09"}
    (folder / "inventory.json").write_text(json.dumps({"scene": PLACE, "rows": [triage_test.row("rocket", pick=pick)]}))
    scene = {"objects": [{"name": "rocket", "row": "rocket", "model": f"models/{model}.gltf", "at": [0, 0, 0]}]}
    return export.export(PLACE, folder / "models", folder / "stage", kit_path=folder / "kit.json",
                         inventory_path=folder / "inventory.json", scene=scene, world=folder)


def a_scene_object_is_locked_to_its_row():
    problems = []
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        stage = scene_rocket(folder, "box")
        found, locked = picks.check(stage, json.loads((folder / "inventory.json").read_text()))
        if found or locked != 1:
            problems.append(f"the kept rocket's stage check reads {found}, {locked} locked")
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        try:
            scene_rocket(folder, "plank")
            problems.append("a scene record showing another model for the picked rocket was exported")
        except picks.PickBroken:
            pass
    return problems


def closeup_mask_and_outline():
    pixels = np.full((60, 80, 3), 220, dtype=np.uint8)
    pixels[10:50, 20:40] = (90, 60, 40)
    mask = compare.closeup_mask(Image.fromarray(pixels))
    problems = [] if abs(int(mask.sum()) - 40 * 20) < 40 and mask[30, 30] else [f"the close-up's mask has {mask.sum()} pixels"]
    taller = np.zeros((100, 100), dtype=bool)
    taller[0:80, 40:80] = True
    if abs(compare.outline(mask, taller) - 1.0) > 0.02:
        problems.append(f"two boxes of one shape at different sizes outline {compare.outline(mask, taller):.2f}")
    wide = np.zeros((100, 100), dtype=bool)
    wide[40:60, 0:100] = True
    if compare.outline(mask, wide) > 0.3:
        problems.append(f"a tall box and a wide one outline {compare.outline(mask, wide):.2f}")
    return problems


CHECKS = (a_kept_pick_exports_with_its_hashes, a_replaced_pick_is_refused_without_a_decision,
          a_row_of_several_models_keeps_each, a_scene_object_is_locked_to_its_row, closeup_mask_and_outline)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
