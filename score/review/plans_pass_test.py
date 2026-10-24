"""The sync pass's plans keep made fast (score/review/plans_pass.py): the narrow key walk answers exactly as the whole
store's walk, and the keep runs inside one moment. A folder store of the test's own."""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

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
    before_keys, before_main = runtime_store.FolderStore.keys, plans.main

    def main(argv):
        seen["argv"], seen["moment"] = argv, plans.HELD.get() is not None
        seen["narrow"] = runtime_store.FolderStore.keys is plans_pass.narrow_keys
        return 0
    plans.main = main
    try:
        assert plans_pass.main() == 0
    finally:
        runtime_store.FolderStore.keys, plans.main = before_keys, before_main
    assert seen == {"argv": ["keep"], "moment": True, "narrow": True}, seen


if __name__ == "__main__":
    test_the_narrow_walk_answers_as_the_whole_walk()
    test_the_keep_runs_inside_one_moment()
    print("plans_pass_test: ok")
