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
a fix added since it was fixed, the airlock's sandbags at the concept's foot, 2026-10-26), or whose things the free
fixes left in each other the relation solver parts (`relation_solver.parted`, IsaacLab-Arena's solver ported to
numpy: the airlock's sandbags, 7 pairs in each other after the nudge, none after it, 2026-10-26), is fixed again in
a process of its own (`fixing`, `python -m score.review.plans_pass fix <place> ...`: `settled_again`,
plan_fixes.settled's free fixes and at most its automatic Corrects under the plan-writing allowance when the free
fixes place more, then the solver, free; kept as a new writing). No person stands in anything there either
(`spaced_people`: a Correct's echo of a stood person spot dropped, the airlock's three spots within 7 cm, 2026-10-30;
a spot whose footprint overlaps a wall, a floor thing or another person moved to the nearest floor where it does not),
free and whether or not its plan row stands accepted: a person in a wall is a placement fault the assembly must
honour, not an overlap to leave. Each re-fix leaves fewer missing or fewer in each other, so a plan is fixed
again only while that improves it. The solver parts only a place whose plan row (plan@<place>) stands unaccepted
(`parting`: a parted writing would re-key an accepted row and every row after it, review of 2026-10-26), and a plan
it alone re-fixes (free) is parted before the keep in the pass itself (`parted_first`), so its plan row is made
once, from the parted writing, never from the unparted one a pass earlier. Here, not in plan_fixes.py, which is in the code version of every stage that
reads plans.py (an edit to it re-keyed 74 paid rows, `score.stages.moved`, 2026-10-26).

Before it, every place of the environment (stages.places: each scene whose design is done) with no kept plan gets one
(`restored`): `keep` walks only the kept plans and the scene tree, so a scene outside the tree whose kept plan was once
taken out (the wreck, 2026-10-24) never had it back, and prepare took its hand-in and surface data out every pass.
"""
import collections
import contextlib
import io
import math
import os
import subprocess
import sys

from score.review import concepts, holders, plan_checks, plan_fixes, plan_writing, plans, relation_solver, standing
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


def placing_more(plan, inventory):
    """Whether a written plan wants its fixes made (again): never fixed, or today's free fixes leave fewer missing."""
    if "fixes" not in plan:
        return True
    lacking = len(missing(plan, inventory))
    return bool(lacking) and len(missing(plan_fixes.fixed(plan, inventory)[0], inventory)) < lacking


def parting(store, place):
    """Whether the relation solver may part the place's writing: its plan row (plan@<place>) stands unaccepted. An
    accepted plan row is never moved for overlaps alone (a parted writing would re-key it and every row after it)."""
    return store.accepted(f"plan@{place}") is None


def numbered(spot):
    """A person spot's row number when its row is a number (the corrected schema's NUMBER items cannot carry the
    row's id: airlock's [6.951, 6.058, 0.0, 1] for its "astronaut", camp's 2 for its "astronaut_2"), else None."""
    if len(spot) >= 4 and isinstance(spot[3], (int, float)) and not isinstance(spot[3], bool):
        return int(spot[3])
    return None


def row_of(number, rows):
    """The people row (of `rows`) a row number names: the one whose id ends in _<number>, else the only one."""
    found = [row for row in rows if row["id"].rsplit("_", 1)[-1] == str(number)]
    return found[0] if found else (rows[0] if len(rows) == 1 else None)


def unnumbered(plan, inventory):
    """(the plan's person spots with each numbered one given its row back, a Correct's copies dropped, the fixes
    said): a numbered spot whose row already stands its full count of spots is a copy (hangar's eight workers and
    camp's six astronauts, 2026-10-30, each placed again by the Correct beside the free fixes' own), and so is one
    that names no row within a stood spot's footprint (airlock's); one whose row is short of its count stands a
    person of it."""
    rows = plan_checks.person_rows(inventory)
    stood = [(spot, size) for spot, size in zip(plan.get("people", []), standing.footprints(plan, inventory))
             if len(spot) >= 4 and isinstance(spot[3], str)]
    placed = collections.Counter(spot[3] for spot, _ in stood)
    spots, fixes = [], []
    for spot in plan.get("people", []):
        number = numbered(spot)
        row = row_of(number, rows) if number is not None else None
        if number is None:
            spots.append(spot)
        elif row and placed[row["id"]] < int(row.get("count", 1) or 1):
            placed[row["id"]] += 1
            spots.append([*spot[:3], row["id"]])
            fixes.append(f"{plan_checks.said_name(row['id'])}: its person spot {spot[:2]} given its row back")
        elif row or any(standing.in_each_other(spot, size, one, size) for one, size in stood):
            copied = row["id"] if row else next(one[3] for one, size in stood
                                                if standing.in_each_other(spot, size, one, size))
            fixes.append(f"{plan_checks.said_name(copied)}: a Correct's copy of its person spot dropped ({spot[:2]})")
        else:
            spots.append(spot)
    return spots, fixes


def spaced_people(plan, inventory):
    """(the plan with no person standing in a wall, a thing or another person, the fixes said): a Correct's echo of a
    stood spot dropped and each other numbered spot given its row back (`unnumbered`), then in order each spot whose footprint overlaps a
    wall, a floor thing or a spot kept before it moved to the nearest floor inside the outline where it overlaps none;
    every other spot kept as placed. Spots of rows beyond or afar stand out there on purpose; a spot with no such
    floor is left."""
    spots, fixes = unnumbered(plan, inventory)
    plan = {**plan, "people": spots}
    if not spots:
        return plan, fixes
    grid = plan_checks.Grid(plan)
    outline = grid.covered(plan_checks.outline_of(plan))
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    left_out = plan_checks.beyond(plan, inventory) | plan_checks.afar(inventory)
    sizes, walls_things, kept = standing.footprints(plan, inventory), {}, []
    for spot, size in zip(spots, sizes):
        row = spot[3] if len(spot) >= 4 and isinstance(spot[3], str) and spot[3] in rows else None
        sits_on = plan_checks.anchor_of(rows[row]) if row else None
        if sits_on not in walls_things:
            walls_things[sits_on] = standing.blocked(plan, inventory, grid, sits_on)
        others = list(zip(kept, sizes))
        free = None if row in left_out or not standing.stands_in(spot, size, walls_things[sits_on], grid, others) \
            else standing.nearest_free(spot, size, walls_things[sits_on], grid, outline, others)
        kept.append(spot if free is None else [*free, *spot[2:]])
        if free is not None:
            fixes.append(f"{plan_checks.said_name(row or 'a standing spot')}: moved "
                         f"{math.dist(spot[:2], free):.2f} m out of what it stood in")
    return {**plan, "people": kept}, fixes


def unsettled(plan, inventory, parts=True):
    """Whether a written plan wants fixing again: `placing_more`, a Correct's copy of a person spot or one standing in
    something (`spaced_people`), or (when it `parts`) the relation solver parts things the fixes left in each other
    (relation_solver.parted)."""
    return (placing_more(plan, inventory) or bool(spaced_people(plan, inventory)[1])
            or (parts and bool(relation_solver.parted(plan, inventory)[1])))


def settled_again(store, place, plan, inventory, ask, parts=True):
    """(the plan fixed again, the Correct calls made): plan_fixes.settled when it is `placing_more`, else as written
    (no Correct asked again for overlaps alone); then, when it `parts`, the things still in each other parted by the
    relation solver, and no person left standing in anything (`spaced_people`), their fixes added and its gaps
    checked again, each left saying why."""
    calls = []
    if placing_more(plan, inventory):
        plan, calls = plan_fixes.settled(store, place, plan, inventory, ask)
    answer, more = relation_solver.parted(plan, inventory) if parts else (plan, [])
    answer, spaced = spaced_people(answer, inventory)
    if more or spaced:
        plan = {**answer, "fixes": [*plan.get("fixes", []), *more, *spaced]}
        plan["gaps"] = plan_fixes.why_left(plan_fixes.open_gaps(plan, inventory))
    return plan, calls


def to_fix(store, places):
    """The places of `places` whose writing in force is `unsettled` (parted only where `parting`)."""
    found = []
    for place in places:
        writing = plan_writing.written_of(store, place)
        if writing and unsettled(writing["plan"], plans.inventory_of(store, place), parting(store, place)):
            found.append(place)
    return found


def unasked(body):
    """The Correct call of a free re-fix: refused (it may not be paid for)."""
    raise RuntimeError("a free re-fix asks no Correct")


def parted_first(store, places):
    """The places of `places` whose writing only the relation solver (`parting`) or `spaced_people` re-fixes
    (`unsettled`, not `placing_more`: free), fixed again here and now, so the keep after it makes their plan rows from
    the re-fixed writing in the same pass (a re-fix in a process of its own reached them a pass later); the places
    fixed."""
    found = []
    for place in places:
        writing = plan_writing.written_of(store, place)
        inventory = plans.inventory_of(store, place) if writing else None
        if not writing or placing_more(writing["plan"], inventory) or not (
                parting(store, place) or spaced_people(writing["plan"], inventory)[1]):
            continue
        if refixed(store, place, "the relation solver", unasked, free=True):
            found.append(place)
    return found


def fixing(store, places, start=subprocess.Popen):
    """`python -m score.review.plans_pass fix <places>` started as plan_writing.started starts a writing (a process of
    its own that outlives the pass); its log's path."""
    def started(command, **options):
        at = command.index("score.review.plan_writing")
        return start([*command[:at], "score.review.plans_pass", "fix", *command[at + 1:]], **options)
    return plan_writing.started(store, places, started)


def refixed(store, place, by, ask, free=False):
    """The place's writing in force fixed again (`settled_again`, parted only where `parting`) and kept as a new
    writing of the same lock, reading and method with its fixes and the cost of its Correct calls, under the place's
    writing lock (a second process waits and finds it settled: nothing is paid twice); None when it is not
    `unsettled`, or when `free` and it is `placing_more` (that re-fix may ask Corrects: `fixing` makes it)."""
    with locked(store.cache / plan_writing.AREA / "locks" / f"{place}.lock"):
        writing = plan_writing.written_of(store, place)
        inventory = plans.inventory_of(store, place)
        parts = parting(store, place)
        if (not writing or not unsettled(writing["plan"], inventory, parts)
                or (free and placing_more(writing["plan"], inventory))):
            return None
        plan, calls = settled_again(store, place, writing["plan"], inventory, ask, parts)
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
    """The plans only the relation solver re-fixes parted first (`parted_first`, outside the moment: it writes), then
    plans.main(["keep"]) with narrow_keys inside one moment, after `restored`, then the other `unsettled` plans
    started being fixed, then each kept plan's relations derived again where they changed (holders.keep: what the
    scene record lays each object by); its exit code, keep's line with what was parted, fixed and derived."""
    from score import stages
    from score.adapters.compute import STORE
    install()
    store = Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default()
    parted = parted_first(store, stages.places(stages.world1(), store)) if plan_writing.AUTOMATIC else []
    said = io.StringIO()
    with plans.one_moment():
        restored(store)
        with contextlib.redirect_stdout(said):
            code = plans.main(["keep"])
        refix = to_fix(store, stages.places(stages.world1(), store)) if plan_writing.AUTOMATIC else []
    related = holders.keep(sorted(path.stem for path in plans.KEPT.glob("*.json")))
    line = said.getvalue().strip() + (f"; plans of {', '.join(parted)} parted" if parted else "") + (
        f"; relations of {len(related)} derived again" if related else "")
    print(line + (f"; plans of {', '.join(refix)} being fixed: {fixing(store, refix)}" if refix else ""))
    return code


if __name__ == "__main__":
    sys.exit(fix_main(sys.argv[2:]) if sys.argv[1:2] == ["fix"] else main())
