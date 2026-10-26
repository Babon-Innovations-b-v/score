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

After it, every written plan that is `unsettled` (never fixed, or today's free fixes place or stand things it lacks:
a fix added since it was fixed, the airlock's sandbags at the concept's foot, 2026-10-26) is fixed again in a process
of its own (`fixing`, `python -m score.review.plans_pass fix <place> ...`: plan_fixes.settled, its free fixes and at
most its automatic Corrects under the plan-writing allowance, kept as a new writing). Each re-fix leaves fewer
missing, so a plan is fixed again only while the free fixes improve it. Here, not in plan_fixes.py, which is in
the code version of every stage that reads plans.py.

Before it, every place of the environment (stages.places: each scene whose design is done) with no kept plan gets one
(`restored`): `keep` walks only the kept plans and the scene tree, so a scene outside the tree whose kept plan was once
taken out (the wreck, 2026-10-24) never had it back, and prepare took its hand-in and surface data out every pass.
"""
import contextlib
import io
import os
import subprocess
import sys

from score.review import concepts, plan_fixes, plan_writing, plans
from score.store import Store, locked, runtime_store


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


def missing(plan, inventory):
    """The gaps of things the concept shows that the plan neither places nor stands (plan_checks' placed and people
    kinds), by today's checks."""
    return [gap for gap in plan_fixes.open_gaps(plan, inventory) if gap["kind"] in ("placed", "people")]


def unsettled(plan, inventory):
    """Whether a written plan wants its fixes made (again): never fixed, or today's free fixes leave fewer missing."""
    if "fixes" not in plan:
        return True
    lacking = len(missing(plan, inventory))
    return bool(lacking) and len(missing(plan_fixes.fixed(plan, inventory)[0], inventory)) < lacking


def to_fix(store, places):
    """The places of `places` whose writing in force is `unsettled`."""
    found = []
    for place in places:
        writing = plan_writing.written_of(store, place)
        if writing and unsettled(writing["plan"], plans.inventory_of(store, place)):
            found.append(place)
    return found


def fixing(store, places, start=subprocess.Popen):
    """`python -m score.review.plans_pass fix <places>` started as plan_writing.started starts a writing (a process of
    its own that outlives the pass); its log's path."""
    def started(command, **options):
        at = command.index("score.review.plan_writing")
        return start([*command[:at], "score.review.plans_pass", "fix", *command[at + 1:]], **options)
    return plan_writing.started(store, places, started)


def refixed(store, place, by, ask):
    """The place's writing in force fixed again (plan_fixes.settled) and kept as a new writing of the same lock,
    reading and method with its fixes and the cost of its Correct calls, under the place's writing lock (a second
    process waits and finds it settled: nothing is paid twice); None when it is not `unsettled`."""
    with locked(store.cache / plan_writing.AREA / "locks" / f"{place}.lock"):
        writing = plan_writing.written_of(store, place)
        inventory = plans.inventory_of(store, place)
        if not writing or not unsettled(writing["plan"], inventory):
            return None
        plan, calls = plan_fixes.settled(store, place, writing["plan"], inventory, ask)
        return plan_writing.kept(store, {
            **{key: writing[key] for key in ("place", "concept", "reading", "method", "drawing", "measured")
               if key in writing}, "by": by, "at": concepts.now(), "drawing_euros": 0.0, "fixed_from": writing["at"],
            "euros": round(sum(call.get("euros", 0.0) for call in calls), 6), "calls": calls, "plan": plan})


def fix_main(places):
    """Fix `places` again under the plan-writing allowance (the store SCORE_SPEND_STORE names, plan_writing.started's);
    one line a place fixed; its exit code."""
    from score.adapters import compute
    spend_store = os.environ.get("SCORE_SPEND_STORE")
    store = Store.in_folder(spend_store) if spend_store else Store.default()
    with plan_writing.cleared(store, places, round(0.2 * plan_fixes.CORRECTIONS * len(places), 2)):
        compute.require_cleared("a plan writing", store)
        for place in places:
            record = refixed(store, place, "the owner's standing allowance", plan_writing.asked)
            if record:
                print(f"{place}: {len(record['plan']['fixes'])} fixes, {len(record['plan']['gaps'])} gaps left, "
                      f"EUR {record['euros']:.4f}")
    return 0


def main():
    """plans.main(["keep"]) with narrow_keys, inside one moment, after `restored`, then the `unsettled` plans started
    being fixed; its exit code, keep's line with what is being fixed."""
    from score import stages
    from score.adapters.compute import STORE
    install()
    store = Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default()
    said = io.StringIO()
    with plans.one_moment():
        restored(store)
        with contextlib.redirect_stdout(said):
            code = plans.main(["keep"])
        refix = to_fix(store, stages.places(stages.world1(), store)) if plan_writing.AUTOMATIC else []
    line = said.getvalue().strip()
    print(line + (f"; plans of {', '.join(refix)} being fixed: {fixing(store, refix)}" if refix else ""))
    return code


if __name__ == "__main__":
    sys.exit(fix_main(sys.argv[2:]) if sys.argv[1:2] == ["fix"] else main())
