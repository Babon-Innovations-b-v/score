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

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools/review"))
import complete  # noqa: E402
sys.path.insert(0, str(HERE.parents[1]))
from score import checks  # noqa: E402
import contents  # noqa: E402
import contents_test  # noqa: E402
import made_only  # noqa: E402
import page  # noqa: E402
import resting_test  # noqa: E402
import triage_test  # noqa: E402

# The test's places have no stage outputs in the framework's store: the contents checks read none until a test lays a
# place (`laid` gives its finished outputs).
complete.stored_outputs = lambda place: dict(contents_test.NONE)
# Nor the world's accepted gaps (the test's place is named wreck, which has some): a test writes its own.
sys.path.insert(0, str(HERE.parents[1]))
from score.stages import gaps  # noqa: E402
gaps.FOLDER = HERE / "no gaps folder"


def laid(folder, rows=(("crate", "floor"), ("lamp", "floor"))):
    """A place of two boxes, one a row, exported; its stage. The test's rows are drawn from no concept, so each says
    so (`unseen`), as the box gate asks of a row with no box. Every row's model is the shared loop's (sorter.row_route
    `model`, #41), so the place is finished only as the line leaves it: each model repainted by the surface line's
    bake, stamped as the assembly stamps it, and the place's likeness and surfaces-check outputs read
    (`finished_outputs`)."""
    resting_test.made_models(folder)
    stage = triage_test.place_of(folder, [("crate", "box", (0, 0, 0)), ("lamp", "box", (3, 0, 0))],
                                 [triage_test.row(name, anchor, box=None, unseen="a test row, drawn from no concept")
                                  for name, anchor in rows])
    contents_test.world_data(folder, resting_test.PLACE)
    contents_test.held_layers(stage, resting_test.PLACE)
    repainted_by_the_bake(stage, folder / "models")
    dropped_still(stage, [name for name, _ in rows])
    complete.stored_outputs = lambda place: finished_outputs(folder, [name for name, _ in rows])
    return stage


def dropped_still(stage, rows):
    """A settle run's drop beside the stage (settle/settled.json) in which each row's object stays as laid: without one
    the resting check of a place with loose objects is unknown."""
    (stage.parent / "settle").mkdir(exist_ok=True)
    still = {"motion": np.eye(4).tolist(), "moving": 0.0, "inside": []}
    (stage.parent / "settle/settled.json").write_text(json.dumps(
        {"objects": {f"{row}_1": still for row in rows}, "overlaps": []}))


def repainted_by_the_bake(stage, models):
    """Each model the stage lays stamped as the assembly stamps a baked one (score/stages/assembly/baked.py), its bake
    the model's own file: a repaint over the seed's paint, which the painted check asks of a generated row."""
    from score.stages.assembly import baked
    opened = Usd.Stage.Open(str(stage))
    laid_models = {prim.GetAttribute("score:model").Get() for prim in opened.Traverse()
                   if prim.HasAttribute("score:model")}
    for model in sorted(laid_models):
        baked.stamp_baked_hash(stage.parent / "layers/base.usda", model, models / f"{model}.gltf")


def finished_outputs(folder, held):
    """{stage: output folder} the contents checks read for a finished place: its accepted likeness holding these rows
    to their close-ups and its accepted surfaces-check; the others none."""
    likeness = folder / "outputs/likeness"
    likeness.mkdir(parents=True, exist_ok=True)
    (likeness / "likeness.json").write_text(json.dumps({"objects": sorted(held)}))
    (folder / "outputs/surfaces-check").mkdir(exist_ok=True)
    return {**contents_test.NONE, "likeness": likeness, "surfaces-check": folder / "outputs/surfaces-check"}


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
    at; a person the design shows not on the stage now fails the place."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        contents_test.people_mapped(contents_test.BRAM, resting_test.PLACE)
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


def an_accepted_gap_moves_only_the_faults_it_names():
    """Fault (2026-10-15): complete.py read no accepted gaps while the runner's complete row did, so the store page failed
    the stairwell on people, game and likeness faults the owner and the overseer had named. A gap moves only its own
    named faults of a gate GAP_GATES["complete"] lists, and the accepted gaps requirement fails each by name."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        saved = gaps.FOLDER
        gaps.FOLDER = folder / "data/checks/gaps"
        gaps.FOLDER.mkdir(parents=True)
        named = {"row": "complete", "reason": "a test", "decided": "the test", "faults": ["player: not on the stage"]}
        (gaps.FOLDER / f"{resting_test.PLACE}.json").write_text(json.dumps({"gaps": [
            {**named, "name": "no player", "check": "people", "objects": ["player"]},
            {**named, "name": "not a gap gate", "check": "light", "objects": ["crate"]}]}))
        problems = []
        try:
            def answer(check, faults):
                complete.save(complete.result(check, complete.FAIL, stage, faults), stage)
                return complete.check_requirement(check, stage, complete.fingerprint(stage), resting_test.PLACE)
            moved = answer("people", ["player: not on the stage"])
            if moved[0] != complete.PASS or "accepted gaps: no player" not in moved[1]:
                problems.append(f"the named people fault did not move: {moved}")
            if answer("people", ["player: not on the stage", "guard: not on the stage"])[0] != complete.FAIL:
                problems.append("a fault no gap names passed with the named one")
            if answer("light", ["crate: no lamp"])[0] != complete.FAIL:
                problems.append("a gap moved a check that is not one of complete's gap gates")
            if complete.accepted_gaps_requirement(resting_test.PLACE)[0] != complete.FAIL:
                problems.append("the accepted gaps requirement does not fail its gaps by name")
            if complete.accepted_gaps_requirement("no such place")[0] != complete.PASS:
                problems.append("a place with no gaps file fails on accepted gaps")
        finally:
            gaps.FOLDER = saved
        return problems


def the_three_statuses():
    """The overseer's decision (2026-10-15): done says "complete" for a place with no gaps, "complete apart from accepted
    gaps (N)" when its accepted gaps are the only fail, listing every gap with its numbers and who decided it, and passes
    the run for both; any other fail stays "NOT complete"."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        checked_and_reviewed(stage, folder / "review")
        saved = gaps.FOLDER
        problems = []
        try:
            written = complete.manifest(resting_test.PLACE, stage, folder / "review")
            if (written["verdict"], written["status"]) != (complete.PASS, "complete") or \
                    complete.done_line(resting_test.PLACE, written) != f"{resting_test.PLACE}: complete (pass)":
                problems.append(f"a place with no gaps is not plainly complete: {written['status']}")
            gaps.FOLDER = folder / "data/checks/gaps"
            gaps.FOLDER.mkdir(parents=True)
            (gaps.FOLDER / f"{resting_test.PLACE}.json").write_text(json.dumps({"gaps": [
                {"name": "no player", "row": "complete", "check": "people", "objects": ["player"], "reason": "a test",
                 "decided": "the overseer, 2026-10-15", "faults": ["player: not on the stage (0 of 1 bodies)"]}]}))
            complete.save(complete.result("people", complete.FAIL, stage, ["player: not on the stage"]), stage)
            written = complete.manifest(resting_test.PLACE, stage, folder / "review")
            said = complete.done_line(resting_test.PLACE, written)
            if (written["verdict"], written["status"]) != (complete.GAPPED, "complete apart from accepted gaps") or \
                    not said.startswith(f"{resting_test.PLACE}: complete apart from accepted gaps (1)") or \
                    "the overseer, 2026-10-15" not in said or "0 of 1 bodies" not in said:
                problems.append(f"a place failing only on its accepted gaps reads {written['verdict']}: {said}")
            complete.save(complete.result("people", complete.FAIL, stage,
                                          ["player: not on the stage", "guard: not on the stage"]), stage)
            written = complete.manifest(resting_test.PLACE, stage, folder / "review")
            if (written["verdict"], written["status"]) != (complete.FAIL, "NOT complete"):
                problems.append(f"a fail no gap names reads {written['status']}")
        finally:
            gaps.FOLDER = saved
        return problems


def judge_resting_toy(output, inputs, evidence):
    faulty = (output / "faults.txt").read_text().strip()
    return checks.Verdict("resting", checks.FAIL if faulty == "other" else checks.PASS, f"toy resting: {faulty}",
                          {"objects": 1}, {"objects": "lower"}, ("/hangar/Objects/crate_1: tips 0.3: outside",))


def make_toy(inputs, out, seed, params):
    (out / "faults.txt").write_text(inputs["faults"].read_text())


def a_store_copy_takes_resting_from_its_assembly_gate():
    """2026-10-17: complete.py judged a store copy's resting by its own triage with no drop run (campgrounds: 6 faults,
    "no drop run on this stage"), while the runner's complete row leaves resting to the assembly's gate, judged on
    its gathered drop run with the accepted gaps moved. A store copy's resting is now that gate's verdict on the
    runner's chosen assembly output: its pass with the faults shown; with no chosen output (its gate failed), unknown."""
    from score import contracts, graph
    from score.store import Store
    toy = graph.Stage("assembly", "place", make_toy, contracts.Contract("toy", 1, lambda folder: []),
                      (checks.Check("resting", judge_resting_toy),), files={"faults": "{data}/{place}.txt"})
    problems = []
    saved = Store.default
    try:
        for said, wanted in (("named", complete.PASS), ("other", complete.UNKNOWN)):
            data, store = pathlib.Path(tempfile.mkdtemp()), Store.in_folder(tempfile.mkdtemp())
            (data / "hangar.txt").write_text(said)
            graph.Runner([toy], graph.World("toy", 1, {"data": data}), store).run(["hangar"])
            Store.default = staticmethod(lambda store=store: store)
            stage = data / "copy" / "hangar.usda"
            stage.parent.mkdir()
            stage.write_text("#usda 1.0\n")
            (stage.parent / complete.STORE_OUTPUT).write_text("abc")
            found = complete.resting_check("hangar", stage)
            shown = found["faults"] == ["/hangar/Objects/crate_1: tips 0.3: outside"] and \
                "assembly@hangar's resting gate" in found["note"]
            if found["result"] != wanted or (wanted == complete.PASS and not shown):
                problems.append(f"a store copy's resting is not its assembly gate's ({said}): {found}")
    finally:
        Store.default = saved
    return problems


def a_ship_place_reads_the_runners_beside_likeness():
    """2026-10-17: the runner's complete row reads, for a ship place, the likeness of each place whose bake lays its
    made pieces (7caacee2); complete.py read only the place's own. Its stored outputs now name the same nodes."""
    sys.path.insert(0, str(HERE.parents[1]))
    from score import stages
    runner = stages.runner()
    problems = []
    for place in ("cockpit", "shiplock", "engineroom", "galley"):
        wanted = sorted(runner.besides(runner.stages["complete"], place))
        if sorted(complete.complete_besides(place)) != wanted:
            problems.append(f"{place}: complete.py reads {complete.complete_besides(place)} beside, the runner {wanted}")
    return problems


def loose_objects_with_no_drop_are_not_known_to_rest():
    """The resting check of a place whose loose objects no drop has run on is unknown, not a pass."""
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        stage = laid(folder)
        (stage.parent / "settle/settled.json").unlink()
        found = complete.resting_check(resting_test.PLACE, stage)["result"]
        return [] if found == complete.UNKNOWN else [f"two loose boxes with no drop run read {found}"]


def a_designed_place_s_boxes_are_judged_on_its_hand_in():
    """A designed place's boxes are judged on its hand-in, whose kept concept ({home}/design/concepts) and grounded
    boxes its design inventory (a store blob, no grounding) does not name: a box the reading grounded passes, one
    boxing the whole picture still fails."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as temporary:
        folder = pathlib.Path(temporary)
        held, complete.HOME = complete.HOME, folder
        try:
            (folder / "design/concepts").mkdir(parents=True)
            (folder / "design/props").mkdir(parents=True)
            Image.new("RGB", (400, 300)).save(folder / "design/concepts/toy.png")
            row = {"id": "crate", "name": "crate", "view": "v1", "grounded": "SAM 3's box in the reading"}
            handin = {"scene": "toy", "plan": {"views": [{"id": "v1", "picture": "{home}/design/concepts/toy.png"}]},
                      "rows": [{**row, "box": [40, 50, 120, 160]}]}
            (folder / "design/props/toy.json").write_text(json.dumps(handin))
            sys.path.insert(0, str(HERE.parents[1] / "tools/props/scene"))
            import box_check
            box_held, box_check.HOME = box_check.HOME, folder
            found = [complete.boxes_check("toy", folder / "toy.usda")["result"]]
            handin["rows"] = [{**row, "box": [0, 0, 400, 300]}]
            (folder / "design/props/toy.json").write_text(json.dumps(handin))
            found.append(complete.boxes_check("toy", folder / "toy.usda")["result"])
            box_check.HOME = box_held
        finally:
            complete.HOME = held
        return [] if found == [complete.PASS, complete.FAIL] else [f"a grounded box and a whole-picture box read {found}"]


CHECKS = (loose_objects_with_no_drop_are_not_known_to_rest, a_finished_place_passes, an_accepted_gap_moves_only_the_faults_it_names, the_three_statuses,
          a_store_copy_takes_resting_from_its_assembly_gate, a_ship_place_reads_the_runners_beside_likeness,
          a_place_without_its_cast_fails_on_its_contents, a_failing_reach_is_shown_not_counted,
          a_row_with_no_object_needs_a_drop_reason,
          an_edit_after_the_checks_makes_them_stale, a_mesh_from_nowhere_fails_made_only,
          a_check_that_cannot_run_is_unknown,
          the_store_page_is_the_review_and_a_store_copy_is_judged_by_its_key, a_designed_place_s_boxes_are_judged_on_its_hand_in)


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    failures = [f"{check.__name__}: {problem}" for check in CHECKS for problem in check()]
    for failure in failures:
        print(failure)
    print("ok" if not failures else f"{len(failures)} failed")
    sys.exit(1 if failures else 0)
