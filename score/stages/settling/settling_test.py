"""Check the settle stage without a drop: its layer lays each written object where its matrix says over the seed (the
assembly takes it the same way), and its drop gate fails a broken drop while one kept as laid or stood upright for
the paint is named.

Run: .venv/bin/python score/stages/settling/settling_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools/usd"))
from pxr import Usd, UsdGeom  # noqa: E402
from score import checks, review  # noqa: E402
from score.stages import assembly, settling as settle  # noqa: E402
import resting_test  # noqa: E402

PLACE = resting_test.PLACE


def laid(stage, name):
    return np.asarray(UsdGeom.Xformable(stage.GetPrimAtPath(f"/{PLACE}/Objects/{name}"))
                      .ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T


def the_layer_lays_each_object_at_its_rest():
    """A crate moved 10 cm and turned 5 degrees by the layer stands there in the assembly's stage; the other keeps
    the seed's pose."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        resting_test.made_models(folder)
        path = resting_test.laid_place(folder, [("crate", "box", (0, 0, 0)), ("crate", "box", (3, 0, 0))],
                                       [("crate", "floor")])
        stage = Usd.Stage.Open(str(path))
        before = laid(stage, "crate_1")
        turn = np.eye(4)
        angle = np.radians(5.0)
        turn[:3, :3] = [[np.cos(angle), 0, np.sin(angle)], [0, 1, 0], [-np.sin(angle), 0, np.cos(angle)]]
        turn[:3, 3] = [0.1, 0.0, 0.0]
        settle.write_layer(stage, PLACE, {"crate_1": turn @ before}, folder / "made" / settle.LAYER)
        assembly.take_layer(folder / "made", path, settle.LAYER, None)
        again = Usd.Stage.Open(str(path))
        problems = []
        if not np.allclose(laid(again, "crate_1"), turn @ before, atol=1e-9):
            problems.append(f"crate_1 stands at {laid(again, 'crate_1')}, not its rest")
        if not np.allclose(laid(again, "crate_2"), laid(stage, "crate_2")):
            problems.append("crate_2 moved though the layer does not name it")
        return problems


def the_drop_gate_fails_a_broken_drop_and_names_what_was_kept():
    """One kept as laid (a 40 degree turn) and one stood upright for the paint pass, named; one still moving at the
    drop's end fails."""
    with tempfile.TemporaryDirectory() as temporary:
        output = pathlib.Path(temporary)
        objects = {"crate_1": {"rested": True, "said": "turns 1 degrees and drifts 1 cm to rest"},
                   "tank_1": {"rested": False, "said": "turns 7 degrees and drifts 2 cm to rest onto feet ending up to "
                                                       "12.7 cm apart in its own frame (level the model's feet); stood "
                                                       "upright on its lowest foot"},
                   "rack_1": {"rested": False, "said": "would not rest as laid: turns 40 degrees and drifts 90 cm"}}
        (output / settle.RECORD).write_text(json.dumps({"place": PLACE, "overlaps": [], "objects": objects}))
        passed = settle.judge_rested(output, {}, None)
        objects["box_1"] = {"rested": False, "said": "still moving 0.40 m/s at the end; left as laid"}
        (output / settle.RECORD).write_text(json.dumps({"place": PLACE, "overlaps": [], "objects": objects}))
        failed = settle.judge_rested(output, {}, None)
        problems = []
        if passed.answer != checks.PASS or passed.measures["kept"] != 1 or not any(
                line.startswith("tank_1") for line in passed.findings):
            problems.append(f"kept as laid counted, the one for the paint named only: {passed}")
        if failed.answer != checks.FAIL or failed.measures["broken"] != 1:
            problems.append(f"still moving: {failed}")
        objects["rack_2"] = dict(objects["rack_1"])  # one more kept as laid is still worse on accept
        objects.pop("box_1")
        (output / settle.RECORD).write_text(json.dumps({"place": PLACE, "overlaps": [], "objects": objects}))
        card = lambda verdict: {"rested": {"answer": verdict.answer, "measures": verdict.measures,
                                           "better": verdict.better}}
        more = settle.judge_rested(output, {}, None)
        if not review.regressions(card(more), card(passed)):
            problems.append("one more kept as laid was not worse than the accepted output")
        return problems


def only_what_lies_on_the_object_resting_worse_is_kept_with_it():
    """Both ways: a case on the pallet that rests worse is kept as laid with it; a case of the same row on another
    pallet of the same row is not (the campgrounds' open cases, 2026-10-15)."""
    eye = np.eye(4)
    moved = np.eye(4)
    moved[1, 3] = 0.01
    poses = {name: {"before": eye, "after": moved, "rested": True, "said": "moved"}
             for name in ("pallet_1", "pallet_2", "case_1", "case_2")}
    inventory = {"rows": [{"id": "pallet", "anchor": "floor"}, {"id": "case", "anchor": "on:pallet"}]}
    under = {"case_1": {"pallet_1"}, "case_2": {"pallet_2"}}
    found = settle.kept_where_worse(poses, {"pallet_1"}, inventory, lambda name: under.get(name, set()))
    kept = sorted(name for name, pose in found.items() if not pose["rested"])
    return [] if kept == ["case_1", "pallet_1"] else [f"kept {kept}, not the worse pallet and its own case"]



def a_flush_pose_resting_worse_falls_back_to_the_drops_rest():
    """Both ways (the wreck's probe lander, 2026-10-15): one stood flush on its slope that rests worse goes back to
    where the drop left it, not to as laid; one flush that rests no worse keeps its flush pose; one resting worse with
    no flush pose is left for kept_where_worse."""
    eye, flush, dropped = np.eye(4), np.eye(4), np.eye(4)
    flush[1, 3], dropped[0, 3] = 0.01, 0.02
    fallback = {"before": eye, "after": dropped, "rested": True, "said": "turns 1 degrees and drifts 2 cm to rest"}
    poses = {"lander_1": {"before": eye, "after": flush, "rested": True, "said": "stood flush", "fallback": fallback},
             "lamp_1": {"before": eye, "after": flush, "rested": True, "said": "stood flush", "fallback": fallback},
             "crate_1": {"before": eye, "after": dropped, "rested": True, "said": "turns 1 degrees"}}
    found, back = settle.fallen_back(poses, {"lander_1", "crate_1"})
    problems = []
    if back != {"lander_1"} or found["lander_1"]["after"] is not dropped or not found["lander_1"]["rested"]:
        problems.append(f"the lander did not fall back to the drop's rest: {back}, {found['lander_1']}")
    if found["lamp_1"] is not poses["lamp_1"] or found["crate_1"] is not poses["crate_1"]:
        problems.append("a flush pose resting no worse, or a worse one with no flush, was changed")
    return problems

CHECKS = (the_layer_lays_each_object_at_its_rest, the_drop_gate_fails_a_broken_drop_and_names_what_was_kept,
          only_what_lies_on_the_object_resting_worse_is_kept_with_it,
          a_flush_pose_resting_worse_falls_back_to_the_drops_rest)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
