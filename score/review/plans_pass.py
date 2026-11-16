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
any free re-fix settles (parted, people spaced, kept inside, kept apart: every one but `placing_more`) is re-fixed
before the keep in the pass itself (`parted_first`), so its plan row is made once, from the re-fixed writing, never
from the unfixed one a pass earlier (settle@airlock, 2026-11-09: plan@airlock stands accepted, so its sandbags 5 to 9
laid again in their run were taken off only in the background fix and kept a pass later). Here, not in plan_fixes.py, which is in the code version of every stage that
reads plans.py (an edit to it re-keyed 74 paid rows, `score.stages.moved`, 2026-10-26).

`python -m score.review.plans_pass refit <place> [--from <at>]` makes a place's writing (in force, or the one made at
`--from`) again by today's writer steps that need no call (`refit`: fitted to its creator's shape, its flights laid),
free, kept as the writing in force: the stairwell's writing of 2026-11-02 laid again after a later writing went wrong.

Before it, every place of the environment (stages.places: each scene whose design is done) with no kept plan gets one
(`restored`): `keep` walks only the kept plans and the scene tree, so a scene outside the tree whose kept plan was once
taken out (the wreck, 2026-10-24) never had it back, and prepare took its hand-in and surface data out every pass.
"""
import collections
import contextlib
import copy
import io
import json
import math
import os
import subprocess
import sys

import numpy

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
    stood spot dropped and each other numbered spot given its row back (`unnumbered`), then each spot standing in
    something moved out of it (plans.people_moved_out)."""
    spots, fixes = unnumbered(plan, inventory)
    plan, moved = plans.people_moved_out({**plan, "people": spots}, inventory)
    return plan, fixes + moved


def brought_inside(plan):
    """(the plan with every row marked beyond whose person spots all stand inside its outline taken off `beyond`, the
    fixes said), free, no Correct asked: plan_fixes.stood_people stands a people row where its concept boxes project,
    so a row it stands inside the room is in it, not beyond it (2026-11-02: lab's writing marked its three people at
    the desks beyond, the people rows dropped them and its cast was empty while its design showed people). Kept here,
    not in plan_fixes, which sits in the code of about 80 rows (surface libraries and bakes, the body faces)."""
    beyond, spots = set(plan.get("beyond") or []), {}
    for spot in plan.get("people") or []:
        if len(spot) >= 4 and spot[3] in beyond:
            spots.setdefault(spot[3], []).append(spot[:2])
    outline = plan_checks.outline_of(plan)
    inside = [row for row, points in spots.items()
              if plan_checks.inside(numpy.asarray(points, dtype=float), outline).all()]
    answer = {**plan, "beyond": [row for row in plan.get("beyond") or [] if row not in inside]} if inside else plan
    return answer, [f"{plan_checks.said_name(row)}: stands on person spots inside this place, so in it, not beyond it"
                    for row in inside]


def unstood(plan, inventory):
    """The people rows (plan_checks.person_rows) the plan stands on no person spot: a writing fixed before
    plan_fixes.stood_people stood people (2026-11-02: stairwell's, written 2026-10-21, its man and woman on the stairs
    on no spot and marked beyond, its cast empty)."""
    have = {spot[3] for spot in plan.get("people") or [] if len(spot) >= 4}
    return [row["id"] for row in plan_checks.person_rows(inventory) if row["id"] not in have]


def spread_people(plan, inventory):
    """The fixes said of each people row the plan still stands on no person spot (`unstood`: no box of it projects
    and no thing of it is laid), but one beyond or afar (out there on purpose), spread, its count of them, over free
    floor inside the outline: plan_fixes.spread_spots over the middle half of the outline's box (round it, clear of
    the walls), each moved to the nearest floor inside the outline where it stands in nothing (standing.nearest_free);
    `plan["people"]` given them. The hangar's eight workers stood on none, so its cast dealt them its four view
    spots, four of them outside its 32 x 64 m (2026-11-04)."""
    rows = {row["id"]: row for row in plan_checks.person_rows(inventory)}
    grid = plan_checks.Grid(plan)
    outline = plan_checks.outline_of(plan)
    inside, corners = grid.covered(outline), numpy.asarray(outline, dtype=float)
    low, high = corners.min(axis=0), corners.max(axis=0)
    middle = [*(low + (high - low) / 4).tolist(), *((high - low) / 2).tolist()]
    others = list(zip(plan.get("people", []), standing.footprints(plan, inventory)))
    fixes, away = [], plan_checks.beyond(plan, inventory) | plan_checks.afar(inventory)
    for row_id in [row_id for row_id in unstood(plan, inventory) if row_id not in away]:
        row, stood = rows[row_id], []
        size = [float(side) for side in row["size"][:2]] if isinstance(row.get("size"), list) else [standing.PERSON] * 2
        walls_things = standing.blocked(plan, inventory, grid, plan_checks.anchor_of(row))
        for spot in plan_fixes.spread_spots(middle, int(row.get("count", 1) or 1), size):
            free = standing.nearest_free(spot, size, walls_things, grid, inside, others)
            if free is not None:
                stood.append([round(free[0], 3), round(free[1], 3), 0.0, row_id])
                others.append((stood[-1], size))
        plan["people"] = [*plan.get("people", []), *stood]
        if stood:
            fixes.append(f"{plan_checks.said_name(row_id)}: no box of it projects, so its {len(stood)} people "
                         f"spread over the free floor")
    return fixes


def stood_again(plan, inventory):
    """(the plan with its unstood people rows stood where their concept boxes project, else spread over its free floor
    (`spread_people`), its fixes said), free; the plan as it was when every people row stands."""
    if not unstood(plan, inventory):
        return plan, []
    answer = copy.deepcopy(plan)
    fixes = plan_fixes.stood_people(answer, inventory, plan_fixes.projector(answer, inventory))
    return answer, fixes + spread_people(answer, inventory)


def unsettled(plan, inventory, parts=True):
    """Whether a written plan wants fixing again: `placing_more`, a Correct's copy of a person spot or one standing in
    something (`spaced_people`), a row marked beyond standing inside (`brought_inside`), a run in a wall or a stair, a
    thing piled on its own row's or two runs in each other on a wall (plan_fixes.kept_apart), or (when it `parts`) the
    relation solver parts things the fixes left in each other (relation_solver.parted)."""
    return (placing_more(plan, inventory) or bool(spaced_people(plan, inventory)[1]) or bool(brought_inside(plan)[1])
            or bool(unstood(plan, inventory)) or bool(plan_fixes.doors_kept(copy.deepcopy(plan), inventory))
            or bool(plan_fixes.kept_inside(copy.deepcopy(plan), inventory))
            or bool(plan_fixes.kept_apart(copy.deepcopy(plan), inventory))
            or (parts and bool(relation_solver.parted(plan, inventory)[1])))


def settled_again(store, place, plan, inventory, ask, parts=True):
    """(the plan fixed again, the Correct calls made): plan_fixes.settled when it is `placing_more`, else as written
    (no Correct asked again for overlaps alone); then, when it `parts`, the things still in each other parted by the
    relation solver, no person left standing in anything (`spaced_people`), nothing past its own outline
    (plan_fixes.kept_inside) and nothing in a wall or its own row's (plan_fixes.kept_apart), people spaced again
    after what those changed, their fixes added and its gaps checked again, each left saying why."""
    calls = []
    if placing_more(plan, inventory):
        plan, calls = plan_fixes.settled(store, place, plan, inventory, ask)
    answer, more = relation_solver.parted(plan, inventory) if parts else (plan, [])
    answer, spaced = spaced_people(answer, inventory)
    answer, stood = stood_again(answer, inventory)
    if stood:
        answer, again = spaced_people(answer, inventory)
        spaced = [*spaced, *again]
    answer, inside = brought_inside(answer)
    answer = copy.deepcopy(answer)
    doors = plan_fixes.doors_kept(answer, inventory)  # its doorways the design's door rows (a fix added 2026-11-04)
    within = plan_fixes.kept_inside(answer, inventory)  # nothing past its own outline (a fix added 2026-11-05)
    apart = plan_fixes.kept_apart(answer, inventory)  # nothing laid in a wall or its own row's (2026-11-09)
    if doors or within or apart:  # what they changed may stand a person in something (airlock's sandbags, 2026-11-09)
        answer, again = spaced_people(answer, inventory)
        spaced = [*spaced, *again]
    if more or spaced or stood or inside or doors or within or apart:
        plan = {**answer, "fixes": plans.said_once([*plan.get("fixes", []), *more, *spaced, *stood, *inside, *doors,
                                                     *within, *apart])}
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
    """The places of `places` whose writing a free re-fix settles (`unsettled`, not `placing_more`: the relation
    solver where `parting`, people spaced, things kept inside, apart and off their doors), fixed again here and now, so
    the keep after it makes their plan rows from the re-fixed writing in the same pass (a re-fix in a process of its
    own reached them a pass later: airlock's sandbags 5 to 9, 2026-11-09, its plan row accepted); the places fixed. A
    settled place's writing lock is not waited on."""
    found = []
    for place in places:
        writing = plan_writing.written_of(store, place)
        inventory = plans.inventory_of(store, place) if writing else None
        if not writing or placing_more(writing["plan"], inventory) or not unsettled(
                writing["plan"], inventory, parting(store, place)):
            continue
        if refixed(store, place, "the free re-fix (plans_pass)", unasked, free=True):
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


def laid_again(plan, inventory, shape, floors=()):
    """(the plan with today's writer steps that need no call made again, what changed said): held at its `floors`
    (plan_writing.floor_held, #128: its room row's, its lock's earlier plan's), fitted to its creator's `shape`
    (plan_writing.fitted), its flights laid (plan_writing.flights_laid: a flight ending in the air not built) and its
    doorways as big as their doors (plan_fixes.doorways_fit), its roof the concept's (plan_writing.concept_roofed,
    #128 D1: beams across it and no dome: flat), its gaps checked again, each left saying why (#72, #87: the stairwell's kept writing of 2026-11-02 had 56-degree
    flights, the flat's of 2026-11-04 a 4.78 x 4.78 m outline for its 6 x 5 m inside)."""
    answer = plan_writing.fitted(plan_writing.floor_held(copy.deepcopy(plan), floors), shape)
    said = answer.get("fixes", [])[len(plan.get("fixes", [])):]
    stairs, levels, unlanded = plan_writing.flights_laid(answer)
    if stairs != (answer.get("stairs") or []) or levels != (answer.get("levels") or []):
        steep = sum(1 for gap in plan_checks.stair_gaps(answer) if "degrees" in gap["words"])
        answer = {**answer, "stairs": stairs, "levels": levels,
                  "dropped": [*(answer.get("dropped") or []), *unlanded]}
        said = [*said, f"{len(stairs)} flights built from their rises and laid inside the walls apart ({steep} were "
                       f"steeper than {plan_checks.STEEPEST:g} degrees), {len(levels) - len(plan.get('levels') or [])} "
                       f"landings added"] + [f"{entry['item']}: {entry['why']}" for entry in unlanded]
    answer, roofed = plan_writing.concept_roofed(answer, inventory)
    said = [*said, *roofed, *plan_fixes.doorways_fit(answer, inventory)]
    answer = {**answer, "fixes": plans.said_once([*plan.get("fixes", []), *said])}
    answer["gaps"] = plan_fixes.why_left(plan_fixes.open_gaps(answer, inventory))
    return answer, said


def first_of(store, place, writing):
    """The `at` of the writing `writing` was fixed from, through its fixes (`fixed_from`), back to the one written."""
    by_at = {found["at"]: found for found in plan_writing.writings(store, place)}
    seen = set()
    while writing.get("fixed_from") in by_at and writing["fixed_from"] not in seen:
        seen.add(writing["fixed_from"])
        writing = by_at[writing["fixed_from"]]
    return writing["at"]


def refit(store, place, by, written_at=None):
    """`place`'s writing in force, or its writing made at `written_at` (a kept one a later writing went wrong over),
    made again by `laid_again`, free, and kept as a new writing of the same lock, reading and method under the
    place's writing lock, so it is the writing in force; None when nothing changed."""
    with locked(store.cache / plan_writing.AREA / "locks" / f"{place}.lock"):
        writing = next((found for found in plan_writing.writings(store, place) if found["at"] == written_at), None) \
            if written_at else plan_writing.written_of(store, place)
        if writing is None or writing.get("refused"):
            raise ValueError(f"{place} has no writing {'made at ' + written_at if written_at else 'in force'}")
        inventory = plans.inventory_of(store, place)
        floors = plan_writing.room_floors(store, place, inventory, writing.get("concept"),
                                          first_of(store, place, writing))
        plan, said = laid_again(writing["plan"], inventory, plans.creator_shape(place), floors)
        if not said:
            return None
        return plan_writing.kept(store, {
            **{key: writing[key] for key in ("place", "concept", "reading", "method", "drawing", "measured")
               if key in writing}, "by": by, "at": concepts.now(), "drawing_euros": 0.0, "fixed_from": writing["at"],
            "euros": 0.0, "calls": [], "plan": plan})


# An agent's edit carried onto the reading in force (`carried`) is a design fix under the owner's word for the #128
# rework, kept as a redrawing that quotes it, so who moved what stays traceable on the plan's own record.
CARRIED_BY = "the plan pass, carrying an agent's edit onto the reading in force (#128)"
CARRIED_WORDS = ("the owner, 2026-11-15: \"do the rework during the night, ill look through the discisions after\"; "
                 "then \"u got it from here true the night\"; #128 D1, the owner's decision: \"Where ship plan v7 or "
                 "the game's numbers disagree with the concept (walkway width, storage door, shiplock headroom, "
                 "quarters and lab doors), the concept wins.\"")
CARRIED_AT = "2026-11-15T20:00:00+00:00"


def laid_rows(place):
    """The rows the scene record lays as objects (its hand-in's prop and shell rows, none far: the plan-matched gate's
    rows), None while the place has no hand-in (then every row counts)."""
    path = plans.PROPS_HOME / "design" / "props" / f"{place}.json"
    if not path.is_file():
        return None
    from score.stages.scene_record import writer
    return {row["id"] for row in json.loads(path.read_text()).get("rows", [])
            if row.get("route", "prop") in writer.LAID_ROUTES and not row.get("far")}


# A row the shell lays as its openings or flights (the record counts their doorways and flights, not plan items: the
# greenhouse's stairs, 3 flights laid for its 2), never recounted by its items.
OPENING_WORDS = frozenset(("door", "doors", "doorway", "doorways", "window", "windows", "opening", "openings"))


def recountable(row, plan):
    """Whether `recounted` lays the row by its plan items: not a door, window or flight of the shell, nor one the
    plan's notes or its shapes' notes give a reason for (the plan-matched gate leaves those: the stairwell's railings
    laid along its flights)."""
    from score.stages.scene_record import writer
    said = str([plan.get("notes") or [], [(shape or {}).get("note") for shape in (plan.get("shapes") or {}).values()]])
    return (str(row["id"]).lower().split("_")[-1] not in OPENING_WORDS and writer.flight_kind(row) is None
            and row["id"] not in said)


def counted_laid(plan, row_id):
    """[(item, shape)] of `row_id`'s things on the plan, and how many they count (a run's shape `count`)."""
    laid = [(item, shape) for item, row, shape in plan_checks.placed_items(plan) if row == row_id]
    return laid, sum(int((shape or {}).get("count") or 1) for _, shape in laid)


def lowered(plan, row_id, excess):
    """`excess` copies of the row taken off the plan, its last laid first (a run's count lowered and its long side
    shortened with it, a single thing dropped); how many it could not take off."""
    for item, shape in reversed(counted_laid(plan, row_id)[0]):
        if excess <= 0:
            break
        count = int((shape or {}).get("count") or 1)
        if count > 1:
            keep = max(1, count - excess)
            long_side = 3 if item[3] >= item[4] else 4
            item[long_side] = round(item[long_side] * keep / count, 3)
            plan["shapes"][item[0]]["count"] = keep
            excess -= count - keep
        else:
            plan_fixes.dropped_item(plan, item)
            excess -= 1
    return excess


def unread_dropped(plan, inventory):
    """The plan's things whose rows the reading no longer has taken off; the fixes said."""
    ids = {row["id"] for row in inventory.get("rows", [])}
    said = []
    for item, _, _ in list(plan_checks.placed_items(plan)):
        tied = plan.get("rows", {}).get(item[0]) or []
        if tied and not ids & set(tied):
            plan_fixes.dropped_item(plan, item)
            said.append(f"{item[0].lower()}: its row {', '.join(tied)} is no longer read, so taken off")
    return said


def recounted(plan, inventory, rows=None):
    """(the plan with each row laid as often as the reading counts, the fixes said), free: things of rows no longer
    read taken off (`unread_dropped`), each row of `rows` (None: every row) laid more often than it counts given its
    copies off (`lowered`), each laid fewer times given its missing ones where its boxes project (SAM 3's, else its
    Gemini region's: plan_fixes.placed_missing; a wall row or one on a thing stands where its box projects, and
    holders.relations holds it on its wall or holder there), as count_gaps counts them (a structure row, one beyond
    and a row the plan's `dropped` names left as they are). Everything else is the plan's own."""
    plan = copy.deepcopy(plan)
    unread = unread_dropped(plan, inventory)
    plan, said = surplus_lowered(plan, inventory, rows)
    said = unread + said
    # placed_missing places every short row by its items' first rows: a row the record lays no object of, and one
    # tied to an item after another row (hangar's wall lamps on its pipes' item, counted none there), are left out
    shared = {row for tied in plan.get("rows", {}).values() for row in tied[1:]}
    laying = {**inventory, "rows": [row for row in inventory.get("rows", [])
                                    if (rows is None or row["id"] in rows) and row["id"] not in shared
                                    and recountable(row, plan)]}
    project = plan_fixes.projector(plan, inventory)
    said += plan_fixes.placed_missing(plan, laying, project)
    return plan, said + spread_over_region(plan, laying, project)


def region_spots(row, picture, project, count):
    """`count` spots on the plan across the row's box on the concept (its one SAM box, else its Gemini region's), the
    box cut into `count` slices side by side, each slice's foot projected: things read as more than the concept
    boxes, across where the reading saw them."""
    boxes = plan_checks.seen_boxes(row, picture)
    if not boxes or project is None:
        return []
    left, top, right, foot = (min(box[0] for box in boxes), min(box[1] for box in boxes),
                              max(box[2] for box in boxes), max(box[3] for box in boxes))
    wide = (right - left) / count
    return [project([left + wide * number, top, left + wide * (number + 1), foot]) for number in range(count)]


def spread_over_region(plan, inventory, project):
    """Each row of `inventory` still laid fewer times than it counts once its boxes are spent (placed_missing places
    one a box: greenhouse's four wall panels read in one region, 2026-11-16) given its missing things at the slices of
    its boxes' span nearest none of its laid things (`region_spots`), like its first laid thing; the fixes said."""
    fixes = []
    for gap in plan_checks.count_gaps(plan, inventory, set(plan.get("structure") or [])):
        row = next(row for row in inventory["rows"] if row["id"] == gap["row"])
        laid, placed = counted_laid(plan, row["id"])
        want = int(row.get("count") or 1)
        if placed >= want or not isinstance(row.get("size"), list):
            continue
        spots = region_spots(row, inventory.get("picture"), project, want)
        middles = [[item[1] + item[3] / 2, item[2] + item[4] / 2] for item, _ in laid]
        spots.sort(key=lambda spot: -min((math.dist(spot, middle) for middle in middles), default=0.0))
        size = [float(row["size"][0]), float(row["size"][1])]
        for spot in spots[:want - placed]:
            plan_fixes.added_item(plan, row["id"], spot, size, laid[0][1] if laid else None)
        if spots:
            fixes.append(f"{plan_checks.said_name(row['id'])}: {min(len(spots), want - placed)} more placed across "
                         f"where the concept shows it")
    return fixes


def agents_edit(store, place):
    """The place's newest edit when an agent made it (it carries the words it stood on, `asked`), else None: his own
    edit (none carries `asked`: habitat's of 2026-10-25) is never carried."""
    edit = plans.newest_edit(store, place)
    return edit if edit and (edit.get("asked") or {}).get("words") else None


def carried(store, place):
    """The place's plan, when it is an agent's edit (`agents_edit`) whose rows the reading in force counts otherwise,
    carried onto that reading (`recounted` over the plan shown, the edit's shape, size, doors and holds its own),
    kept as a redrawing quoting the owner's words and #128 D1 with the reading it was carried onto; the record, None
    when nothing changed. An edit wins over every writing after it (plans.shown_plan), so an agent's edit laid on an
    older reading kept its old counts and rows against tonight's reading (2026-11-16: scene-record's plan-matched
    failed at hangar, lab, quarters, square, stairwell, tube, walkway and greenhouse, hand recounts missing rows on
    walls and on things)."""
    from score.review import reading
    edit, read = agents_edit(store, place), reading.reading_of(store, place)
    inventory = plans.inventory_of(store, place)
    shown = plans.current(store, place) if edit and read and inventory else None
    if not shown or shown.get("at") != edit["at"]:
        return None
    plan, said = recounted(shown["plan"], inventory, laid_rows(place))
    if not said:
        return None
    return plans.redrawn(store, place, {key: plan[key] for key in ("items", "rows", "shapes")}, CARRIED_BY, {
        "words": CARRIED_WORDS, "at": CARRIED_AT, "reading": read["at"],
        "reason": f"{place}'s plan in force is an agent's edit of {edit['at'][:16]} laid on an older reading than its "
                  f"reading of {read['at'][:16]}, and as the newest edit it wins over the writings of that reading, "
                  "so its things kept the old counts and rows (scene-record plan-matched). Carried onto the reading "
                  "in force, the edit's own decisions kept: " + "; ".join(said)})


def carried_all(store, places):
    """`carried` for each of `places`; {place: its record} of those carried, and the places whose own edit of his
    stands over an older reading (never carried: his to replace)."""
    found, his = {}, []
    for place in places:
        edit = plans.newest_edit(store, place)
        if edit and not agents_edit(store, place):
            his.append(place)
            continue
        record = carried(store, place) if edit else copies_dropped(store, place)
        if record:
            found[place] = record
    return found, his


def surplus_lowered(plan, inventory, rows=None):
    """(the plan with each row of `rows` (None: every row) `recountable` laid more often than its reading counts given
    its copies off, its last laid first (`lowered`), the fixes said), free; a row laid as often as its child scene's
    instances the plan's doorways lead to (gates.led_instances) is left as laid."""
    from score.stages.scene_record import gates
    plan, said = copy.deepcopy(plan), []
    led = gates.led_instances(plan)  # a child scene's instances its doorways lead to (base's seven tubes for six)
    for gap in plan_checks.count_gaps(plan, inventory, set(plan.get("structure") or [])):
        row = next(row for row in inventory["rows"] if row["id"] == gap["row"])
        laid, want = counted_laid(plan, row["id"])[1], int(row.get("count") or 1)
        if (rows is None or row["id"] in rows) and recountable(row, plan) and laid > want \
                and led.get(row["id"]) != laid:
            lowered(plan, row["id"], laid - want)
            said.append(f"{plan_checks.said_name(row['id'])}: {laid} laid, its reading counts {want}, so "
                        f"{laid - counted_laid(plan, row['id'])[1]} taken off")
    return plan, said


def copies_dropped(store, place):
    """The place's writing in force (no edit over it) with the copies of each row it lays more often than its reading
    counts taken off (`surplus_lowered`), kept as a new writing of the same lock, reading and method under the place's
    writing lock; the record, None when it lays none over. A Correct asked to join what the concept shows a tunnel
    touching laid a tunnel at each (old_station's writing of 2026-11-15: connecting tunnel left 1 read, 5 laid), and
    no free fix takes a copy off."""
    with locked(store.cache / plan_writing.AREA / "locks" / f"{place}.lock"):
        writing = plan_writing.written_of(store, place)
        inventory = plans.inventory_of(store, place)
        if not writing or writing.get("refused") or not inventory:
            return None
        plan, said = surplus_lowered(writing["plan"], inventory, laid_rows(place))
        if not said:
            return None
        plan = {**plan, "fixes": plans.said_once([*plan.get("fixes", []), *said])}
        plan["gaps"] = plan_fixes.why_left(plan_fixes.open_gaps(plan, inventory))
        return plan_writing.kept(store, {
            **{key: writing[key] for key in ("place", "concept", "reading", "method", "drawing", "measured")
               if key in writing}, "by": "the free recount (plans_pass)", "at": concepts.now(), "drawing_euros": 0.0,
            "fixed_from": writing["at"], "euros": 0.0, "calls": [], "plan": plan})


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
    """Each place's agent's edit carried onto its reading and each writing's surplus copies taken off
    (`carried_all`), the plans a free re-fix settles fixed (`parted_first`), both outside the moment (they write), then
    plans.main(["keep"]) with narrow_keys inside one moment, after `restored`, then the other `unsettled` plans
    started being fixed, then each kept plan's relations derived again where they changed (holders.keep: what the
    scene record lays each object by); its exit code, keep's line with what was parted, fixed and derived."""
    from score import stages
    from score.adapters.compute import STORE
    install()
    store = Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default()
    places = stages.places(stages.world1(), store)
    carried_now, his = carried_all(store, places)  # before the keep, outside the moment: they write
    parted = parted_first(store, places) if plan_writing.AUTOMATIC else []
    said = io.StringIO()
    with plans.one_moment():
        restored(store)
        with contextlib.redirect_stdout(said):
            code = plans.main(["keep"])
        refix = to_fix(store, stages.places(stages.world1(), store)) if plan_writing.AUTOMATIC else []
    related = holders.keep(sorted(path.stem for path in plans.KEPT.glob("*.json")))
    line = said.getvalue().strip() + (f"; plans of {', '.join(carried_now)} recounted to their readings"
                                      if carried_now else "") + (
        f"; his own edits of {', '.join(his)} kept as he left them" if his else "") + (
        f"; plans of {', '.join(parted)} parted" if parted else "") + (
        f"; relations of {len(related)} derived again" if related else "")
    print(line + (f"; plans of {', '.join(refix)} being fixed: {fixing(store, refix)}" if refix else ""))
    return code


def refit_main(argv):
    """`refit <place> [--from <a writing's at>]`: `refit` in the framework's store, free; one line."""
    import argparse
    parser = argparse.ArgumentParser(description=refit.__doc__.split("\n")[0])
    parser.add_argument("place")
    parser.add_argument("--from", dest="written_at")
    parser.add_argument("--by", default="the free writer steps (plans_pass refit)")
    options = parser.parse_args(argv)
    install()
    record = refit(Store.default(), options.place, options.by, options.written_at)
    plan = record and record["plan"]
    print(f"{options.place}: " + (f"{plan['w']:g} x {plan['d']:g} m, {len(plan['stairs'] or [])} flights, "
                                  f"{len(plan['gaps'])} gaps left, kept at {record['at']}" if record else "unchanged"))
    return 0


if __name__ == "__main__":
    sys.exit(fix_main(sys.argv[2:]) if sys.argv[1:2] == ["fix"] else refit_main(sys.argv[2:])
             if sys.argv[1:2] == ["refit"] else main())
