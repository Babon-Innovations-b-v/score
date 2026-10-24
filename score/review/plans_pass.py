"""The sync pass's `plans keep` (score/dashboard/sync/client.py plans_kept), made fast: plans.main(["keep"]) inside one
moment (plans.one_moment: each place's plan made once, not once a question) with the folder store's key lookups
walking only the folder a prefix names (narrow_keys).

    .venv/bin/python -m score.review.plans_pass       # what `python -m score.review.plans keep` does, in seconds

A pass took 10 to 12 min, about 7 in `plans keep` (2026-10-24): every Store.keys walked the whole store (5,400
objects) and current() asked it about 25 times a place, again for every question about the place. Both fixes live
here, in a module no stage imports, so they are in no row's key: plans.py and tools/cloud/runtime/store.py are in the
code version of every stage that reads them (an edit to either re-keyed about 50 paid rows, `score.stages.moved`).
The answers are the same; `keep` writes only the files the stages read and starts the plan writing in a process of
its own, never a store write the moment would hide.

Before it, every place of the environment (stages.places: each scene whose design is done) with no kept plan gets one
(`restored`): `keep` walks only the kept plans and the scene tree, so a scene outside the tree whose kept plan was once
taken out (the wreck, 2026-10-24) never had it back, and prepare took its hand-in and surface data out every pass.
"""
import os
import sys

from score.review import plans
from score.store import runtime_store


def narrow_keys(self, prefix):
    """FolderStore.keys walking only the folder the prefix names (its part up to the last slash): every key that
    starts with `prefix`, sorted, the same answer as the whole store's walk."""
    folder = self.root / prefix.rpartition("/")[0]
    found = (str(path.relative_to(self.root)) for path in (folder.rglob("*") if folder.is_dir() else ())
             if path.is_file() and not path.name.endswith(".partial"))
    return sorted(key for key in found if key.startswith(prefix))


def install():
    """Give every folder store in this process narrow_keys."""
    runtime_store.FolderStore.keys = narrow_keys


def restored(store):
    """The environment's places with no kept plan given theirs (plans.keep); the places it wrote."""
    from score import stages
    unkept = [place for place in stages.places(stages.world1(), store) if not (plans.KEPT / f"{place}.json").is_file()]
    return plans.keep(store, unkept)[1]


def main():
    """plans.main(["keep"]) with narrow_keys, inside one moment, after `restored`; its exit code."""
    from score.adapters.compute import STORE
    from score.store import Store
    install()
    with plans.one_moment():
        restored(Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default())
        return plans.main(["keep"])


if __name__ == "__main__":
    sys.exit(main())
