"""Check the completion gate on places made here: a laid place with every check run and its review page built passes;
a row with no object fails until it has a written drop reason; a stage edited after its checks makes them stale
(unknown, which blocks); an inventory changed after the export fails the stage; a mesh nothing says the framework made
fails the made-only check; a check that cannot run is unknown; the review page's stamp goes stale with the stage; a
place missing what its cast says fails on its contents; and a failing reach is shown, the gate counting only that it
was recorded.

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
import contents  # noqa: E402
import contents_test  # noqa: E402
import made_only  # noqa: E402
import page  # noqa: E402
import resting_test  # noqa: E402
import triage_test  # noqa: E402

# The test's places have no stage outputs in the framework's store: the contents checks read none.
complete.stored_outputs = lambda place: dict(contents_test.NONE)
# Nor the world's named gaps (the test's place is named wreck, which has some): a test writes its own.
sys.path.insert(0, str(HERE.parents[1]))
from score.stages import gaps  # noqa: E402
gaps.FOLDER = HERE / "no gaps folder"


def laid(folder, rows=(("crate", "floor"), ("lamp", "floor"))):
    """A place of two boxes, one a row, exported; its stage. The test's rows are drawn from no concept, so each says
    so (`unseen`), as the box gate asks of a row with no box."""
    resting_test.made_models(folder)
    stage = triage_test.place_of(folder, [("crate", "box", (0, 0, 0)), ("lamp", "box", (3, 0, 0))],
                                 [triage_test.row(name, anchor, box=None, unseen="a test row, drawn from no concept")
                                  for name, anchor in rows])
    contents_test.world_data(folder, resting_test.PLACE)
    contents_test.held_layers(stage, resting_test.PLACE)
    return stage


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


def a_place_without_its_cast_fails_on_its_contents():
    """Fault (world 1 checklist, 2026-10-12): the gate passed places whose people, effects and motion it never looked
    at; a cast person not on the stage now fails the place."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        cast = {"place": resting_test.PLACE, "people": [{"name": "bram", "character": "bram", "doing": "idle",
                                                         "at": [0, 0, 0], "facing_to": [0, 0, 1], "why": "a test"}]}
        (contents.DATA / "characters" / f"{resting_test.PLACE}.json").write_text(json.dumps(cast))
        checked_and_reviewed(stage, folder / "review")
        found, verdict = verdicts(stage, folder / "review")
        return [] if found["people"] == complete.FAIL and verdict == complete.FAIL else \
            [f"a place missing its cast's person reads people {found['people']}, {verdict}"]


def a_failing_reach_is_shown_not_counted():
    """Fault (audit of 2026-10-11, item 5): the reach check failed places on backdrop rows nobody walks to, and its
    fail counted in the verdict before it had caught one real unreachable row. What counts is that it was recorded."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        checked_and_reviewed(stage, folder / "review")
        complete.save(complete.result("reach", complete.FAIL, stage, [{"row": "far_city_tower"}]), stage)
        written = complete.manifest(resting_test.PLACE, stage, folder / "review")
        reach = next(requirement for requirement in written["requirements"] if requirement["name"] == "reach")
        problems = [] if reach["result"] == complete.PASS and reach["why"].startswith("recorded, fail") and \
            "experimental" in reach else [f"the reach requirement does not show its fail as recorded: {reach}"]
        if written["verdict"] != complete.PASS:
            problems.append(f"an experimental check's fail decided the verdict: {written['verdict']}")
        return problems


def a_part_answers_for_its_own_rows_only():
    """Fault (2026-10-13): complete@gdoor failed on 40 of the garage's rows and on reach's 0 views. A part of another
    place (contents.json `part_of`) answers rows, boxes and picks for the rows its own kit lays; reach is its host's."""
    contents.DATA = HERE.parents[1] / "data"  # the world's own part_of records (earlier tests point it at theirs)
    with tempfile.TemporaryDirectory() as temporary:
        stage = pathlib.Path(temporary) / "gdoor.usda"  # no inputs record: the place's own inventory, the garage's
        problems = []
        own = {row["id"] for row in complete.own_inventory("gdoor", stage)["rows"]}
        if own != {"lattice_ring_rib", "wall_upper_plain"}:
            problems.append(f"the garage door leaves answer for rows {sorted(own)}, not their kit's two")
        if len(complete.own_inventory("garage", stage)["rows"]) <= len(own):
            problems.append("the garage itself lost its rows")
        if complete.reach_check("gdoor", stage)["result"] != complete.PASS:
            problems.append("reach is judged on the door leaves, not on the garage")
        return problems


def the_store_page_is_the_review_and_a_store_copy_is_judged_by_its_key():
    """The owner reviews from the store page (store_page.py, no renders): its stamp on the stage as it is answers the
    review requirement, an older stamp fails it. A stage copied out of the store (its output marker beside it) is
    judged by the runner's key, never by its inputs record's file times."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        saved = complete.STORE_REVIEWS, complete.store_stage_requirement
        complete.STORE_REVIEWS = folder / "review-store"
        problems = []
        try:
            (complete.STORE_REVIEWS / resting_test.PLACE).mkdir(parents=True)
            stamp = complete.STORE_REVIEWS / resting_test.PLACE / complete.REVIEW_STAMP
            stamp.write_text(json.dumps({"fingerprint": complete.fingerprint(stage), "at": "now"}))
            if complete.review_requirement(resting_test.PLACE, stage, None, complete.fingerprint(stage))[0] != \
                    complete.PASS:
                problems.append("the store page built from this stage does not answer the review")
            stamp.write_text(json.dumps({"fingerprint": "an earlier stage", "at": "then"}))
            if complete.review_requirement(resting_test.PLACE, stage, None, complete.fingerprint(stage))[0] != \
                    complete.FAIL:
                problems.append("a store page built from an earlier stage still answers the review")
            asked = []
            complete.store_stage_requirement = lambda place, output: asked.append((place, output)) or (complete.PASS,
                                                                                                         "keyed")
            (stage.parent / complete.STORE_OUTPUT).write_text("abc123\n")
            if complete.stage_requirement(stage, "garage") != (complete.PASS, "keyed") or \
                    asked != [("garage", "abc123")]:
                problems.append(f"a store copy was not judged by the runner's key: {asked}")
        finally:
            complete.STORE_REVIEWS, complete.store_stage_requirement = saved
        return problems


def a_named_gap_moves_only_the_faults_it_names():
    """Fault (2026-10-15): complete.py read no named gaps while the runner's complete row did, so the store page failed
    the stairwell on people, game and likeness faults the owner and the overseer had named. A gap moves only its own
    named faults of a gate GAP_GATES["complete"] lists, and the named gaps requirement fails each by name."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        saved = gaps.FOLDER
        gaps.FOLDER = folder / "data/checks/gaps"
        gaps.FOLDER.mkdir(parents=True)
        named = {"row": "complete", "reason": "a test", "decided": "the test", "faults": ["player: not on the stage"]}
        (gaps.FOLDER / f"{resting_test.PLACE}.json").write_text(json.dumps({"gaps": [
            {**named, "name": "no player", "check": "people", "objects": ["player"]},
            {**named, "name": "not a gap gate", "check": "painted", "objects": ["crate"]}]}))
        problems = []
        try:
            def answer(check, faults):
                complete.save(complete.result(check, complete.FAIL, stage, faults), stage)
                return complete.check_requirement(check, stage, complete.fingerprint(stage), resting_test.PLACE)
            moved = answer("people", ["player: not on the stage"])
            if moved[0] != complete.PASS or "named gaps: no player" not in moved[1]:
                problems.append(f"the named people fault did not move: {moved}")
            if answer("people", ["player: not on the stage", "guard: not on the stage"])[0] != complete.FAIL:
                problems.append("a fault no gap names passed with the named one")
            if answer("painted", ["crate: not repainted"])[0] != complete.FAIL:
                problems.append("a gap moved a check that is not one of complete's gap gates")
            if complete.named_gaps_requirement(resting_test.PLACE)[0] != complete.FAIL:
                problems.append("the named gaps requirement does not fail its gaps by name")
            if complete.named_gaps_requirement("no such place")[0] != complete.PASS:
                problems.append("a place with no gaps file fails on named gaps")
        finally:
            gaps.FOLDER = saved
        return problems


CHECKS = (a_finished_place_passes, a_named_gap_moves_only_the_faults_it_names, a_place_without_its_cast_fails_on_its_contents, a_failing_reach_is_shown_not_counted,
          a_row_with_no_object_needs_a_drop_reason,
          an_edit_after_the_checks_makes_them_stale, a_mesh_from_nowhere_fails_made_only,
          a_check_that_cannot_run_is_unknown, a_part_answers_for_its_own_rows_only,
          the_store_page_is_the_review_and_a_store_copy_is_judged_by_its_key)


if __name__ == "__main__":
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
