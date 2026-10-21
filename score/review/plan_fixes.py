"""The automatic fixes of a written plan (owner, 2026-10-21: "if u can detect these ... then why dont u just fix them,
gaps should only show things that cant be fixed auto"), run after every plan writing (plan_writing.written_one) and
before it is shown; his own edits are never touched, and no inside place's room moves (a locked scene's room stays
where its draw was drawn: plans.locked_rooms_kept).

First the free fixes (`fixed`), each a check of plan_checks with one answer: every people row stood as person spots
(plan["people"], [x, y, None, row], first: the cast stands on them), where its SAM boxes project onto the plan; a
counted box of things drawn apart split into its things along the drawing's spread; a row placed fewer times than the
concept counts given its missing things where their boxes project; a thing facing another way than the concept shows
turned to the concept's way; two floor things standing in each other nudged apart the shortest way out, inside the
walls. The projection is the arrangement check's (plan_checks.viewed): the rows boxed once on the concept and laid
on the plan, their box's middle across and its foot fitted to their middle on the plan.

Then what is still open goes to the prompt model as the notes of one automatic Correct (`corrected`, as the plan
page's, under the plan-writing allowance, its cost kept with the writing), the free fixes run again on its answer, and
it is kept only when fewer gaps are left; at most CORRECTIONS times. What is left is a gap, saying why (`why_left`).

    python -m score.review.plan_fixes <place> ...   # fix the written plans shown now, each a new writing kept
"""
import argparse
import copy
import io
import json
import math
import sys

import numpy

from score.review import concepts, plan_checks, plans

CORRECTIONS = 2  # automatic Correct calls at most, each kept only when it leaves fewer gaps
NUDGE_ROUNDS = 4  # passes over the overlaps, each moving the smaller thing of a pair
MARGIN = 0.05  # metres left between two things nudged apart
FACINGS = ("N", "E", "S", "W")
WHY = {  # what a gap left after the fixes says: why no fix of it took
    "placed": "no box of it on the concept projects onto the plan, and the correction did not place it",
    "people": "no box of them on the concept projects onto the plan",
    "overlap": "no free floor inside the walls to move either to, and the correction did not part them",
    "outside": "the correction did not bring it inside",
    "arrangement": "the correction did not lay it the concept's way",
    "reach": "the correction did not clear a way to it",
    "tiling": "inside places are never moved by the fixes",
    "joined": "the correction did not join it",
}


# --- the projection from the concept onto the plan ---------------------------------------------------------------

def projector(plan, inventory):
    """A function from a SAM box (pixels of the concept) to its spot [x, y] on the plan, inside its outline box, fitted
    on the rows boxed once and laid (plan_checks.viewed: the box's middle across and its foot); None with fewer than
    three such rows."""
    seen, laid, _ = plan_checks.viewed(plan, inventory)
    if len(seen) < 3:
        return None
    source = numpy.array([[spot[0], spot[2], 1.0] for spot in seen.values()])
    target = numpy.array([laid[row] for row in seen], dtype=float)
    matrix = numpy.linalg.lstsq(source, target, rcond=None)[0]
    wide, high = inventory["picture"]

    def project(box):
        spot = numpy.array([(box[0] + box[2]) / 2 / wide, box[3] / high, 1.0]) @ matrix
        return [round(min(max(float(spot[0]), 0.0), plan["w"]), 3), round(min(max(float(spot[1]), 0.0), plan["d"]), 3)]
    return project


def boxes_of(row):
    """A row's SAM boxes on the concept (its instances')."""
    return [box for box in row.get("boxes") or ([row["box"]] if row.get("box") else []) if box]


# --- the free fixes ------------------------------------------------------------------------------------------------

def item_name(plan, row):
    """The next free plan item name of `row` ("ROCKET ENGINE 2")."""
    stem, taken = row.replace("_", " ").upper(), {item[0] for item in plan["items"]}
    return next(f"{stem} {number}" for number in range(1, 10_000) if f"{stem} {number}" not in taken)


def dropped_item(plan, item):
    """Take `item` off the plan, with its rows and shape."""
    plan["items"].remove(item)
    plan.get("rows", {}).pop(item[0], None)
    plan.get("shapes", {}).pop(item[0], None)


def added_item(plan, row, spot, size, like=None):
    """Put one thing of `row` on the plan, its middle at `spot`, `size` [wide, deep] metres, its shape like `like`'s
    (count 1); its name."""
    name = item_name(plan, row)
    plan["items"].append([name, round(spot[0] - size[0] / 2, 3), round(spot[1] - size[1] / 2, 3), round(size[0], 3),
                          round(size[1], 3), None, "item"])
    plan.setdefault("rows", {})[name] = [row]
    plan.setdefault("shapes", {})[name] = {key: value for key, value in (like or {"shape": "rect"}).items()
                                           if key != "count"}
    return name


def stood_people(plan, inventory, project):
    """Every people row but a crowd stood as person spots where its boxes project (its items taken off: a person is
    no furniture), first among the plan's standing spots; the fixes said."""
    rows = plan_checks.person_rows(inventory)
    if not rows:
        return []
    ids = {row["id"] for row in rows}
    found = [spot for spot in plan.get("people", []) if not (len(spot) >= 4 and spot[3] in ids)]
    stood, fixes = [], []
    for row in rows:
        laid = [item for item, row_id, _ in plan_checks.placed_items(plan) if row_id == row["id"]]
        spots = ([project(box) for box in boxes_of(row)] if project else []) or [
            [round(item[1] + item[3] / 2, 3), round(item[2] + item[4] / 2, 3)] for item in laid]
        for item in laid:
            dropped_item(plan, item)
        stood += [[*spot, None, row["id"]] for spot in spots]
        if spots:
            fixes.append(f"{plan_checks.said_name(row['id'])}: stood as {len(spots)} person spot"
                         f"{'s' if len(spots) > 1 else ''} where the concept shows them")
    plan["people"] = stood + found
    return fixes


def spread_spots(box, count, size):
    """`count` middles of things of `size` spread over a run's `box` [x, y, w, d]: round its edge when the box is
    much larger than a thing both ways (trees round a plaza), else along its longer side."""
    x, y, wide, deep = box
    if wide > 3 * size[0] and deep > 3 * size[1]:
        edge = 2 * (wide + deep - size[0] - size[1])
        spots = []
        for number in range(count):
            way = edge * number / count
            left, top, right, bottom = x + size[0] / 2, y + size[1] / 2, x + wide - size[0] / 2, y + deep - size[1] / 2
            for start, end in (((left, top), (right, top)), ((right, top), (right, bottom)),
                               ((right, bottom), (left, bottom)), ((left, bottom), (left, top))):
                length = math.dist(start, end)
                if way <= length or (start, end) == ((left, bottom), (left, top)):
                    share = way / length if length else 0.0
                    spots.append([start[0] + (end[0] - start[0]) * share, start[1] + (end[1] - start[1]) * share])
                    break
                way -= length
        return spots
    along = wide >= deep
    step = (wide if along else deep) / count
    return [[x + step * (number + 0.5), y + deep / 2] if along else [x + wide / 2, y + step * (number + 0.5)]
            for number in range(count)]


def split_runs(plan, inventory, project):
    """Each counted box of things drawn apart (plan_checks.run_gaps) split into its things: where its row's boxes
    project when they are as many, else spread over the box; the fixes said."""
    by_id, fixes = {row["id"]: row for row in inventory.get("rows", [])}, []
    for gap in plan_checks.run_gaps(plan, inventory):
        item = next((item for item in plan["items"] if item[0] == gap["item"]), None)
        if item is None:
            continue
        shape = plan.get("shapes", {}).get(item[0]) or {}
        count, row = int(shape.get("count") or 1), by_id[gap["row"]]
        size = [min(float(row["size"][0]), item[3]), min(float(row["size"][1]), item[4])]
        boxes = boxes_of(row)
        spots = ([project(box) for box in boxes] if project and len(boxes) == count else
                 spread_spots(item[1:5], count, size))
        dropped_item(plan, item)
        for spot in spots:
            added_item(plan, row["id"], spot, size, shape)
        fixes.append(f"{plan_checks.said_name(gap['item'])}: split into its {count} things")
    return fixes


def placed_missing(plan, inventory, project):
    """Each row on the floor placed fewer times than the concept counts given its missing things where its boxes
    project, those nearest a thing already laid taken as that one's; the fixes said."""
    if project is None:
        return []
    fixes, short = [], {gap["row"] for gap in plan_checks.count_gaps(plan, inventory, set(plan.get("structure", [])))}
    for row in inventory.get("rows", []):
        if row["id"] not in short or not isinstance(row.get("size"), list):
            continue
        laid = [(item, shape) for item, row_id, shape in plan_checks.placed_items(plan) if row_id == row["id"]]
        placed = sum(int((shape or {}).get("count") or 1) for _, shape in laid)
        spots = [project(box) for box in boxes_of(row)]
        for item, shape in laid:  # each laid thing takes the spots nearest it, as many as it counts
            middle = [item[1] + item[3] / 2, item[2] + item[4] / 2]
            for _ in range(int((shape or {}).get("count") or 1)):
                if spots:
                    spots.remove(min(spots, key=lambda spot: math.dist(spot, middle)))
        missing = max(0, int(row.get("count", 1) or 1) - placed)
        like = laid[0][1] if laid else None
        size = [float(row["size"][0]), float(row["size"][1])]
        added = [added_item(plan, row["id"], spot, size, like) for spot in spots[:missing]]
        if added:
            fixes.append(f"{plan_checks.said_name(row['id'])}: {len(added)} more placed where the concept shows them")
    return fixes


def faced(plan, inventory):
    """Each thing facing another way than the concept shows turned the concept's way; the fixes said."""
    _, _, turn = plan_checks.viewed(plan, inventory)
    fixes = []
    for item, _, shape in plan_checks.placed_items(plan):
        seen = (shape or {}).get("seen")
        if item[5] in FACINGS and seen and plan_checks.facing_word(item[5], turn) not in seen:
            facing = next((facing for word in seen for facing in FACINGS
                           if plan_checks.facing_word(facing, turn) == word), None)
            if facing:
                item[5] = facing
                fixes.append(f"{plan_checks.said_name(item[0])}: turned to face {'-'.join(seen)} as in the concept")
    return fixes


def overlapping(box, other):
    """Whether two boxes [x, y, w, d] share any floor."""
    return box[0] < other[0] + other[2] and other[0] < box[0] + box[2] and box[1] < other[1] + other[3] \
        and other[1] < box[1] + box[3]


def way_out(mover, still, plan, others):
    """The shortest step [dx, dy] that takes `mover`'s box out of `still`'s, inside the outline and into no box of
    `others`; None when there is none."""
    box, other = mover[1:5], still[1:5]
    steps = [[other[0] + other[2] - box[0] + MARGIN, 0.0], [other[0] - box[0] - box[2] - MARGIN, 0.0],
             [0.0, other[1] + other[3] - box[1] + MARGIN], [0.0, other[1] - box[1] - box[3] - MARGIN]]
    outline = plan_checks.outline_of(plan)
    for step in sorted(steps, key=lambda step: abs(step[0]) + abs(step[1])):
        moved = [box[0] + step[0], box[1] + step[1], box[2], box[3]]
        corners = numpy.array([[moved[0], moved[1]], [moved[0] + moved[2], moved[1]],
                               [moved[0] + moved[2], moved[1] + moved[3]], [moved[0], moved[1] + moved[3]]])
        if plan_checks.inside(corners, outline).all() and not any(overlapping(moved, rest) for rest in others):
            return step
    return None


def nudged(plan, inventory):
    """Two floor things standing in each other (plan_checks.overlap_gaps) parted: the smaller moved the shortest way
    out, inside the walls and into nothing else; the fixes said."""
    fixes = []
    for _ in range(NUDGE_ROUNDS):
        found = plan_checks.overlap_gaps(plan, inventory, plan_checks.Grid(plan))
        moved_any = False
        for gap in found:
            items = {item[0]: item for item in plan["items"]}
            pair = [items.get(gap["item"]), items.get(gap["with"])]
            if None in pair:
                continue
            mover, still = sorted(pair, key=lambda item: item[3] * item[4])
            floor = {item[0] for item, *_ in plan_checks.blocking(plan, inventory)}
            others = [item[1:5] for item in plan["items"] if item[0] in floor and item[0] not in (mover[0], still[0])]
            step = way_out(mover, still, plan, others)
            if step:
                mover[1], mover[2] = round(mover[1] + step[0], 3), round(mover[2] + step[1], 3)
                moved_any = True
                fixes.append(f"{plan_checks.said_name(mover[0])}: moved {math.hypot(*step):.1f} m out of "
                             f"{plan_checks.said_name(still[0])}")
        if not moved_any:
            break
    return fixes


def fixed(plan, inventory):
    """(the plan with every free fix made, the fixes said): people stood, runs split, missing things placed, facings
    turned, overlaps parted, in that order (each later one on the earlier's plan)."""
    plan = copy.deepcopy(plan)
    project = projector(plan, inventory)
    fixes = stood_people(plan, inventory, project) + split_runs(plan, inventory, project)
    fixes += placed_missing(plan, inventory, project) + faced(plan, inventory) + nudged(plan, inventory)
    return plan, fixes


# --- what is left: the automatic Correct --------------------------------------------------------------------------

def open_gaps(plan, inventory):
    """The plan's gaps by today's free checks, its inside places not laid out kept as written."""
    return [gap for gap in plan.get("gaps", []) if gap["kind"] == "place"] + plan_checks.checked(
        plan, inventory, plan.get("structure", []))


def tied(plan, answered):
    """The corrected items kept: well formed, each tied to its row (a new one by its name's row) and shape."""
    rows, shapes = dict(plan.get("rows", {})), dict(plan.get("shapes", {}))
    ids = {row for found in rows.values() for row in found}
    items = []
    for item in answered if isinstance(answered, list) else []:
        if not (isinstance(item, list) and len(item) >= 7 and isinstance(item[0], str)
                and all(isinstance(value, (int, float)) for value in item[1:5]) and item[3] > 0 and item[4] > 0):
            continue
        row = rows.get(item[0]) or ([item[0].rsplit(" ", 1)[0].lower().replace(" ", "_")]
                                    if item[0].rsplit(" ", 1)[0].lower().replace(" ", "_") in ids else None)
        if row is None:
            continue
        rows[item[0]] = row
        items.append([item[0], *[round(float(value), 3) for value in item[1:5]],
                      item[5] if item[5] in FACINGS else None, item[6]])
    return items, rows, shapes


def corrected(store, place, plan, left, ask):
    """One automatic Correct of `plan` by the gaps `left` as its notes (the plan page's question, plans.plan_question),
    the drawn plan and the locked concept sent; (the corrected plan, its call {model, asked, answered, euros}). Its
    size, rooms and doors stay; Refused when it answers no plan."""
    from PIL import Image

    from score.review import plan_writing, reading
    note = ("Fix these problems the free checks found, each where it is, and change nothing else: "
            + "; ".join(gap["words"] for gap in left))
    question = plans.plan_question(plan, [], [], note)
    pro, _, _ = concepts.tools()
    concept = Image.open(io.BytesIO(store.objects.read_bytes(f"blobs/{plans.pick_of(store, place)}")))
    body = {"contents": [{"role": "user", "parts": [{"text": question}] + [
        pro.part(picture, concepts.LONGEST_SENT) for picture in (plans.drawn(plan), concept)]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}
    response, _ = ask(body)
    answered = reading.answer_text(response)
    call = {"model": plan_writing.MODEL, "asked": note, "answered": answered,
            "euros": plan_writing.call_euros(response)}
    found = plans.answered_plan(answered)
    items, rows, shapes = tied(plan, found.get("items"))
    if not items:
        raise plans.Refused("the correction answered no items")
    zones = [item for item in plan["items"] if item[6] == "zone"]
    people = [spot for spot in found.get("people") or [] if isinstance(spot, list) and len(spot) >= 2
              and all(isinstance(value, (int, float)) for value in spot[:2])]
    return {**plan, "items": [item for item in items if item[6] != "zone"] + zones, "rows": rows,
            "shapes": shapes, "people": people or plan.get("people", [])}, call


def why_left(gaps):
    """Each gap left after the fixes, saying why no fix of it took."""
    return [{**gap, "words": f"{gap['words']}: {WHY[gap['kind']]}"} if gap["kind"] in WHY and ": " + WHY[gap["kind"]]
            not in gap["words"] else gap for gap in gaps]


def settled(store, place, plan, inventory, ask):
    """(the plan with the free fixes made and up to CORRECTIONS automatic Corrects kept, each only when it left fewer
    gaps, its gaps what is left, each saying why, and `fixes` what was fixed; the Correct calls made)."""
    plan, fixes = fixed(plan, inventory)
    calls = []
    for _ in range(CORRECTIONS):
        left = open_gaps(plan, inventory)
        if not [gap for gap in left if gap["kind"] != "place"]:
            break
        try:
            answer, call = corrected(store, place, plan, left, ask)
        except (plans.Refused, concepts.Refused, ValueError) as refused:
            calls.append({"refused": str(refused)[:200]})
            break
        calls.append(call)
        answer, more = fixed(answer, inventory)
        if len(open_gaps(answer, inventory)) >= len(left):
            break
        plan, fixes = answer, fixes + [f"the prompt model corrected {len(left)} gaps"] + more
    plan["fixes"] = fixes
    plan["gaps"] = why_left(open_gaps(plan, inventory))
    return plan, calls


# --- the plans written before the fixes --------------------------------------------------------------------------

def fix_written(store, places, by, ask=None):
    """Fix the written plan shown of each of `places` (its newest writing in force, unless fixed already), each kept
    as a new writing of the same lock, reading and method with its fixes and the cost of its Correct calls; the
    records."""
    from score.review import plan_writing
    found = []
    for place in places:
        writing = plan_writing.written_of(store, place)
        if not writing or "fixes" in writing["plan"]:
            continue
        plan, calls = settled(store, place, writing["plan"], plans.inventory_of(store, place),
                              ask or plan_writing.asked)
        euros = round(sum(call.get("euros", 0.0) for call in calls), 6)
        found.append(plan_writing.kept(store, {
            **{key: writing[key] for key in ("place", "concept", "reading", "method", "drawing", "measured")
               if key in writing}, "by": by, "at": concepts.now(), "euros": euros, "drawing_euros": 0.0,
            "fixed_from": writing["at"], "calls": calls, "plan": plan}))
    return found


def main(argv):
    """Fix the places named under the plan-writing allowance; one line a place."""
    from score.adapters import compute
    from score.review import plan_writing
    from score.store import Store
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("places", nargs="+")
    parser.add_argument("--by", default="the owner's standing allowance")
    options = parser.parse_args(argv)
    store = Store.default()
    euros = round(0.2 * CORRECTIONS * len(options.places), 2)
    with plan_writing.cleared(store, options.places, euros):
        compute.require_cleared("a plan writing", store)
        for record in fix_written(store, options.places, options.by):
            print(json.dumps({"place": record["place"], "fixes": len(record["plan"]["fixes"]),
                              "gaps left": len(record["plan"]["gaps"]), "euros": record["euros"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
