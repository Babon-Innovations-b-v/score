"""Check the completion gate on places made here: a laid place with every check run and its review page built passes;
a row with no object fails until it has a written drop reason; a stage edited after its checks makes them stale
(unknown, which blocks); an inventory changed after the export fails the stage; a mesh nothing says the framework made
fails the made-only check; a check that cannot run is unknown; and the review page's stamp goes stale with the stage.

Run: .venv/bin/python tools/usd/complete_test.py   (make tests runs it with the framework's environment)
"""
import json
import pathlib
import sys
import tempfile

from pxr import Gf, Sdf, Usd, UsdGeom

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools/review"))
import complete  # noqa: E402
import made_only  # noqa: E402
import page  # noqa: E402
import resting_test  # noqa: E402


def laid(folder, rows=(("crate", "floor"), ("lamp", "floor"))):
    """A place of two boxes, one a row, exported; its stage."""
    resting_test.made_models(folder)
    return resting_test.laid_place(folder, [("crate", "box", (0, 0, 0)), ("lamp", "box", (3, 0, 0))], list(rows))


def verdicts(stage, review):
    """{requirement: result} of the gate on the stage."""
    written = complete.manifest(resting_test.PLACE, stage, review)
    return {requirement["name"]: requirement["result"] for requirement in written["requirements"]}, written["verdict"]


def checked_and_reviewed(stage, review):
    """Every check run, then the review page's stamp written as page.py writes it after a render."""
    complete.run_checks(resting_test.PLACE, stage)
    review.mkdir(exist_ok=True)
    page.stamp(review, stage, rendered=True)


def a_finished_place_passes():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        found, verdict = verdicts(stage, folder / "review")
        problems = [] if verdict == complete.UNKNOWN and found["rows"] == complete.UNKNOWN else \
            [f"an unchecked place reads {verdict} ({found})"]
        checked_and_reviewed(stage, folder / "review")
        found, verdict = verdicts(stage, folder / "review")
        if verdict != complete.PASS:
            problems.append(f"a checked and reviewed place reads {verdict}: {found}")
        if not (stage.parent / "manifest.json").exists():
            problems.append("no manifest.json beside the stage")
        return problems


def a_row_with_no_object_needs_a_drop_reason():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder, rows=(("crate", "floor"), ("lamp", "floor"), ("rocket", "floor")))
        problems = []
        if complete.rows_check(resting_test.PLACE, stage)["result"] != complete.FAIL:
            problems.append("a row with no object and no drop reason passed")
        inventory = json.loads((folder / "inventory.json").read_text())
        inventory["rows"][2]["dropped"] = "owner, 2026-10-09: the rocket stands in the launch place, not here"
        (folder / "inventory.json").write_text(json.dumps(inventory))
        if complete.rows_check(resting_test.PLACE, stage)["result"] != complete.PASS:
            problems.append("a row dropped with a written reason still fails")
        if complete.stage_requirement(stage)[0] != complete.FAIL:
            problems.append("the inventory changed after the export, and the stage still reads current")
        return problems


def an_edit_after_the_checks_makes_them_stale():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        checked_and_reviewed(stage, folder / "review")
        edit = Usd.Stage.Open(str(stage))
        edit.SetEditTarget(Usd.EditTarget(Sdf.Layer.FindOrOpen(str(stage.parent / "layers/edit.usda"))))
        edit.GetPrimAtPath(f"/{resting_test.PLACE}/Objects/crate_1").GetAttribute("xformOp:translate").Set(
            Gf.Vec3d(0.0, 0.0, 1.0))
        edit.GetEditTarget().GetLayer().Save()
        found, verdict = verdicts(stage, folder / "review")
        problems = []
        if found["rows"] != complete.UNKNOWN or found["current"] != complete.UNKNOWN or verdict == complete.PASS:
            problems.append(f"checks made before an edit still count: {found}, {verdict}")
        if found["review"] != complete.FAIL:
            problems.append(f"the review page built before the edit reads {found['review']}")
        return problems


def a_mesh_from_nowhere_fails_made_only():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        edit = Usd.Stage.Open(str(stage))
        edit.SetEditTarget(Usd.EditTarget(Sdf.Layer.FindOrOpen(str(stage.parent / "layers/edit.usda"))))
        UsdGeom.Cube.Define(edit, f"/{resting_test.PLACE}/old_crate")
        edit.GetEditTarget().GetLayer().Save()
        faults = made_only.check(stage)
        if [fault["prim"] for fault in faults] != [f"/{resting_test.PLACE}/old_crate"]:
            return [f"made-only found {faults}, not only the cube from nowhere"]
        return []


def a_check_that_cannot_run_is_unknown():
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        missing = folder / "nowhere/nothing.usda"
        found = complete.run_check("rows", resting_test.PLACE, missing)
        broken = folder / "broken.usda"
        broken.write_text("#usda 1.0\n(\n not a stage")
        problems = []
        if found["result"] != complete.UNKNOWN:
            problems.append(f"a check on a missing stage reads {found['result']}")
        if complete.run_check("made_only", resting_test.PLACE, broken)["result"] != complete.UNKNOWN:
            problems.append("a check on a broken stage is not unknown")
        return problems


CHECKS = (a_finished_place_passes, a_row_with_no_object_needs_a_drop_reason, an_edit_after_the_checks_makes_them_stale,
          a_mesh_from_nowhere_fails_made_only, a_check_that_cannot_run_is_unknown)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
