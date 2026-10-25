"""The sync pass's plans keep made fast (score/review/plans_pass.py): the narrow key walk answers exactly as the whole
store's walk, the keep runs inside one moment, and a done place with no kept plan gets one first. A folder store of
the test's own."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import stages  # noqa: E402
from score.review import plans, plans_pass  # noqa: E402
from score.store import runtime_store  # noqa: E402

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
    before_keys, before_main, before_restored = runtime_store.FolderStore.keys, plans.main, plans_pass.restored

    def main(argv):
        seen["argv"], seen["moment"] = argv, plans.HELD.get() is not None
        seen["narrow"] = runtime_store.FolderStore.keys is plans_pass.narrow_keys
        return 0
    plans.main = main
    plans_pass.restored = lambda store: seen.setdefault("restored", plans.HELD.get() is not None)
    try:
        assert plans_pass.main() == 0
    finally:
        runtime_store.FolderStore.keys, plans.main, plans_pass.restored = before_keys, before_main, before_restored
    assert seen == {"argv": ["keep"], "moment": True, "narrow": True, "restored": True}, seen


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
    print("plans_pass_test: ok")
