"""The sync pass's plans keep made fast (score/review/plans_pass.py): the narrow key walk answers exactly as the whole
store's walk, the keep runs inside one moment, a done place with no kept plan gets one first, and a pile the free
fixes left is parted free on a re-fix. A folder store of
the test's own."""
import contextlib
import io
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import stages  # noqa: E402
from score.review import plan_fixes, plan_writing, plans, plans_pass  # noqa: E402
from score.store import Store, runtime_store  # noqa: E402

KEYS = ["outputs/a.json", "outputs/ab/c.json", "outputs/b.json", "plans/x/edits/1.json", "plans/xy/edits/2.json",
        "blobs/abc", "top.json"]


def test_the_narrow_walk_answers_as_the_whole_walk():
    with tempfile.TemporaryDirectory() as folder:
        store = runtime_store.FolderStore(folder)
        for key in KEYS:
            store.write_bytes(key, b"{}")
        store.write_bytes("outputs/half.json.partial", b"")
        whole = runtime_store.FolderStore.keys
        for prefix in ("", "outputs/", "outputs/a", "outputs/ab/", "plans/x", "plans/x/", "plans/x/edits/1", "to",
                       "missing/", "missing/deeper/x"):
            assert plans_pass.narrow_keys(store, prefix) == whole(store, prefix), prefix


def test_the_keep_runs_inside_one_moment():
    seen = {}
    before = (runtime_store.FolderStore.keys, plans.main, plans_pass.restored, plans_pass.to_fix, stages.places,
              plans_pass.parted_first)

    def main(argv):
        seen["argv"], seen["moment"] = argv, plans.HELD.get() is not None
        seen["parted before the keep"] = "parted first" in seen
        seen["narrow"] = runtime_store.FolderStore.keys is plans_pass.narrow_keys
        print("plans for the plan stage: 1 kept")
        return 0
    plans.main = main
    plans_pass.restored = lambda store: seen.setdefault("restored", plans.HELD.get() is not None)
    plans_pass.to_fix = lambda store, places: seen.setdefault("fix asked", places) and []
    plans_pass.parted_first = lambda store, places: (
        seen.setdefault("parted first", (places, plans.HELD.get() is None)) and ["airlock"])
    stages.places = lambda world, store: ["shed"]
    said = io.StringIO()
    try:
        with contextlib.redirect_stdout(said):
            assert plans_pass.main() == 0
    finally:
        (runtime_store.FolderStore.keys, plans.main, plans_pass.restored, plans_pass.to_fix, stages.places,
         plans_pass.parted_first) = before
    assert seen == {"argv": ["keep"], "moment": True, "narrow": True, "restored": True, "fix asked": ["shed"],
                    "parted first": (["shed"], True), "parted before the keep": True}, seen
    assert said.getvalue() == "plans for the plan stage: 1 kept; plans of airlock parted\n", said.getvalue()


def test_a_plan_fixed_before_a_fix_it_needs_is_fixed_again_in_a_process_of_its_own():
    """2026-10-26: the airlock's plan was fixed before rows at the concept's foot were brought in from beyond, so its
    sandbags stayed unplaced; once fixed again, it is settled."""
    cube = [1.0, 1.0, 1.0]
    rows = [{"id": "plates", "anchor": "ground", "count": 1, "boxes": [[0, 500, 1000, 1000]]},
            {"id": "barrel", "count": 2, "size": cube, "boxes": [[150, 400, 250, 500], [750, 400, 850, 500]]},
            {"id": "pallet", "anchor": "on:plates", "count": 1, "size": cube, "boxes": [[450, 700, 550, 800]]},
            {"id": "desk", "count": 1, "size": cube, "boxes": [[750, 200, 850, 300]]},
            {"id": "sandbags", "anchor": "ground", "count": 1, "size": cube, "boxes": [[450, 900, 550, 1000]]}]
    items = [["BARREL 1", 1.5, 4.5, 1.0, 1.0, None, "item"], ["BARREL 2", 7.5, 4.5, 1.0, 1.0, None, "item"],
             ["PALLET 1", 4.5, 7.5, 1.0, 1.0, None, "item"], ["DESK 1", 7.5, 2.5, 1.0, 1.0, None, "item"]]
    plan = {"w": 10.0, "d": 10.0, "doors": [], "people": [], "items": items, "structure": ["plates"], "fixes": [],
            "beyond": ["sandbags"], "rows": {item[0]: [item[0].split(" ")[0].lower()] for item in items}}
    inventory = {"picture": [1000, 1000], "rows": rows}
    assert plans_pass.unsettled(plan, inventory)
    fixed, fixes = plan_fixes.fixed(plan, inventory)
    assert not plans_pass.unsettled({**fixed, "fixes": fixes}, inventory)
    started = []
    with tempfile.TemporaryDirectory() as folder:
        store = Store.in_folder(folder)
        plans_pass.fixing(store, ["airlock"], lambda command, **options: started.append(command))
    assert started and started[0][-3:] == ["score.review.plans_pass", "fix", "airlock"], started


def test_a_fixed_plan_with_a_pile_is_parted_again_free_and_then_settled():
    """2026-10-26: the airlock's sandbags stayed in each other after the nudge; the relation solver parts them on a
    re-fix, free (no Correct asked for overlaps alone), and the parted plan is not fixed again."""
    items = [[f"SANDBAGS {number}", 1.2, 1.3, 0.6, 0.35, None, "item"] for number in range(1, 7)]
    plan = {"w": 3.0, "d": 3.0, "doors": [], "people": [], "items": items, "fixes": ["earlier fix"], "gaps": [],
            "rows": {item[0]: ["sandbags"] for item in items}}
    inventory = {"rows": [{"id": "sandbags", "anchor": "ground", "count": 6, "size": [0.6, 0.35, 0.15]}]}
    assert not plans_pass.placing_more(plan, inventory) and plans_pass.unsettled(plan, inventory)

    def ask(body):
        raise AssertionError("no Correct is asked for overlaps alone")
    fixed, calls = plans_pass.settled_again(None, "airlock", plan, inventory, ask)
    assert calls == [] and fixed["fixes"][0] == "earlier fix" and len(fixed["fixes"]) >= 6
    assert not [gap for gap in fixed["gaps"] if gap["kind"] == "overlap"] and not plans_pass.unsettled(fixed, inventory)


def piled():
    """Six sandbags in one spot on a 3 m floor, fixed once: only the relation solver re-fixes it."""
    items = [[f"SANDBAGS {number}", 1.2, 1.3, 0.6, 0.35, None, "item"] for number in range(1, 7)]
    plan = {"w": 3.0, "d": 3.0, "doors": [], "people": [], "items": items, "fixes": ["earlier fix"], "gaps": [],
            "rows": {item[0]: ["sandbags"] for item in items}}
    return plan, {"rows": [{"id": "sandbags", "anchor": "ground", "count": 6, "size": [0.6, 0.35, 0.15]}]}


def test_an_accepted_plan_row_is_never_parted_and_an_unaccepted_one_is_parted_before_the_keep():
    """Review of 2026-10-26: plan@habitat stands accepted, so a parted writing would re-key it and every row after it;
    the airlock's plan is still to run, so it is parted in the pass, before `plans keep` makes its plan row."""
    plan, inventory = piled()
    kept = []
    before = plan_writing.written_of, plans.inventory_of, plan_writing.kept
    with tempfile.TemporaryDirectory() as folder:
        store = Store.in_folder(folder)
        standing = {"plan@habitat": "the accepted output"}
        store.accepted = standing.get
        plan_writing.written_of = lambda store, place: {"place": place, "at": "then", "plan": plan}
        plans.inventory_of = lambda store, place: inventory
        plan_writing.kept = lambda store, record: kept.append(record) or record
        try:
            assert not plans_pass.parting(store, "habitat") and plans_pass.parting(store, "airlock")
            assert plans_pass.to_fix(store, ["habitat", "airlock"]) == ["airlock"]
            assert plans_pass.refixed(store, "habitat", "test", plans_pass.unasked) is None
            assert plans_pass.parted_first(store, ["habitat", "airlock"]) == ["airlock"]
        finally:
            plan_writing.written_of, plans.inventory_of, plan_writing.kept = before
    assert [record["place"] for record in kept] == ["airlock"] and kept[0]["euros"] == 0.0 and kept[0]["calls"] == []
    assert not plans_pass.unsettled(kept[0]["plan"], inventory)


def test_a_plan_that_places_more_is_left_to_its_own_process_not_parted_first():
    """A re-fix that may ask Corrects (`placing_more`) is never made in the pass: `fixing` makes it under the
    allowance; the accepted row's placing re-fix still runs there, without the solver."""
    plan, inventory = piled()
    plan = {key: value for key, value in plan.items() if key != "fixes"}
    before = plan_writing.written_of, plans.inventory_of
    with tempfile.TemporaryDirectory() as folder:
        store = Store.in_folder(folder)
        store.accepted = {"plan@habitat": "the accepted output"}.get
        plan_writing.written_of = lambda store, place: {"place": place, "at": "then", "plan": plan}
        plans.inventory_of = lambda store, place: inventory
        try:
            assert plans_pass.parted_first(store, ["habitat", "airlock"]) == []
            assert plans_pass.to_fix(store, ["habitat", "airlock"]) == ["habitat", "airlock"]
        finally:
            plan_writing.written_of, plans.inventory_of = before
    asked = []
    fixed, calls = plans_pass.settled_again(None, "habitat", {**plan, "fixes": []}, inventory, asked.append,
                                            parts=False)
    assert fixed["items"] == plan["items"] and calls == [] and asked == []


def test_a_done_place_with_no_kept_plan_gets_one():
    """The wreck, 2026-10-24: an outside place in no tree whose kept plan was taken out is kept again; a place whose
    plan is kept is not asked again."""
    asked = {}
    before = stages.places, plans.keep, plans.KEPT
    with tempfile.TemporaryDirectory() as folder:
        plans.KEPT = pathlib.Path(folder)
        (plans.KEPT / "hangar.json").write_text("{}")
        stages.places = lambda world, store: ["hangar", "wreck"]
        plans.keep = lambda store, places: (asked.setdefault("places", places), places)
        try:
            assert plans_pass.restored("the store") == ["wreck"]
        finally:
            stages.places, plans.keep, plans.KEPT = before
    assert asked == {"places": ["wreck"]}, asked


if __name__ == "__main__":
    import pathlib
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    test_the_narrow_walk_answers_as_the_whole_walk()
    test_the_keep_runs_inside_one_moment()
    test_a_done_place_with_no_kept_plan_gets_one()
    test_a_plan_fixed_before_a_fix_it_needs_is_fixed_again_in_a_process_of_its_own()
    test_a_fixed_plan_with_a_pile_is_parted_again_free_and_then_settled()
    test_an_accepted_plan_row_is_never_parted_and_an_unaccepted_one_is_parted_before_the_keep()
    test_a_plan_that_places_more_is_left_to_its_own_process_not_parted_first()
    print("plans_pass_test: ok")
