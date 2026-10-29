"""What holds each plan item (issue #72; bible `architecture/layers`, assembly: the plan states the relations the
assembly lays by): derived free from the scene inventory's anchors, the concept's boxes and the kept plan, no model
call, and kept beside the plan in a file of its own, `{home}/design/relations/<place>.json`, which the scene record
reads (never in design/plans/: that file keys the close-ups and the surface library).

Each plan item of a row that stands on, against or in something gets one relation, in plan metres (x east, y south):

    top    on its holder item's top: the row's anchor `on:<row>`, and in the concept its box's foot stands over its
           holder's by more than TOP_SHARE of the holder's box (a monitor on its console, a lamp on its desk)
    within inside its holder item, where the plan lays its middle (plants in their greenhouse, a door in its frame)
    face   against its holder item's side, `face` N, E, S or W: the side the concept shows it against (toward the
           viewer where its box stands within its holder's across, else the holder's left or right as seen), else the
           side toward it on the plan, else its facing, its holder's, or S (the garage door on its module's front)
    in     in a door or window opening of the plan (`opening`: its at, wide, sill, head, and the wall it stands on): a
           row that fills an opening (design_shell.fills_opening), anchored on a wall or on structure; each opening
           holds one, the nearest to the item's spot, a kind like the row's first (a door in a door)
    wall   against a wall of the plan (`wall`, its from, to, thick, and `side` +1 or -1 of the line it stands on, `spot`
           its plan spot): a row anchored `wall`, or on a structure row that is a wall; an item the plan writer did not
           place (the walls item) stands where the concept's box projects onto the plan (plan_checks.projection), else
           at the longest wall's middle
    floor / ceiling  on the place's own floor or under its roof: named, nothing to lay against

A row whose things the concept shows on several rows of its named holder's footing (hub's 38 monitors on four consoles,
the reading naming one bank: one anchor a row) has each item held by the nearest of them on the plan (seen_holders):
the anchors stay the reading's, so the hand-in, the close-ups and Pixal3D keep their keys. A row whose holder the plan
does not lay and is no wall, floor or roof, or a wall item in an open place with no wall,
is `unheld` with why. The file names the kept plan's sha it was derived from (`plan`), so the scene record lays by
it only while the plan is the same.

    relations(plan, inventory)   the place's relations {place, plan, about, relations, unheld}
    keep(places)                 written for each place with a kept plan and inventory, where the scene record reads it
"""
import hashlib
import json
import re

import numpy

from score.review import plan_checks
from score.stages.earth_seed import design_shell
from score.store import PROPS_HOME

KEPT_PLANS = PROPS_HOME / "design" / "plans"
KEPT_INVENTORY = PROPS_HOME / "design" / "inventory"
KEPT = PROPS_HOME / "design" / "relations"
# An item stands on its holder's top when its concept box's foot is over the holder's by this share of its box's height.
TOP_SHARE = 0.25
FACES = {"N": (0.0, -1.0), "S": (0.0, 1.0), "E": (1.0, 0.0), "W": (-1.0, 0.0)}
WALL_WORDS = {"wall", "walls", "facade", "panel", "partition", "side", "bulkhead"}
FLOOR_WORDS = {"floor", "deck", "plates", "plate", "grating", "plaza", "ground", "platform", "terrain", "regolith",
               "pavement", "road", "street", "yard", "quay"}
CEILING_WORDS = {"roof", "ceiling", "dome", "canopy", "sky"}
# Words of a row's id that say where it stands, not what it is (main_control_bank, control_console_left: both control).
PLACE_WORDS = {"left", "right", "front", "back", "rear", "main", "top", "upper", "lower", "middle", "centre", "center",
               "inner", "outer", "side", "big", "small", "large", "tall", "short", "long", "near", "far", "the", "of",
               "and", "with"}
PARTS = {"wall": "wall", "opening": "wall", "floor": "floor", "ground": "floor", "roof": "ceiling", "sky": "ceiling"}


def plan_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def middle(item):
    return numpy.array([float(item[1]) + float(item[3]) / 2, float(item[2]) + float(item[4]) / 2])


def words_of(row):
    return set(re.findall(r"[a-z]+", f"{row['id']} {row.get('name', '')} {row.get('noun', '')}".replace("_", " ").lower()))


def holder_kind(row):
    """What a structure row is to what stands on it: wall, floor or ceiling, by its part, else its words; None."""
    if row.get("part") in PARTS:
        return PARTS[row["part"]]
    found = words_of(row)
    return next((kind for kind, words in (("wall", WALL_WORDS), ("ceiling", CEILING_WORDS), ("floor", FLOOR_WORDS))
                 if found & words), None)


def items_of(plan):
    """{plan item name: item} of the plan's things, and {row id: [its item names]}."""
    items = {item[0]: item for item in plan.get("items") or [] if len(item) > 6 and item[6] == "item"}
    rows = {}
    for name, ids in (plan.get("rows") or {}).items():
        for row_id in ids if name in items else []:
            rows.setdefault(row_id, []).append(name)
    return items, rows


def box_of(row):
    return next(iter(plan_checks.boxes_of(row)), None)


def seen_pair(row, holder):
    """(the row's box, the holder's box) the concept shows it on: the first of its boxes whose foot one of the
    holder's holds, with that box; else each one's first."""
    for seen in plan_checks.boxes_of(row):
        x, y = foot(seen)
        for under in plan_checks.boxes_of(holder):
            if under[0] <= x <= under[2] and under[1] <= y <= under[3]:
                return seen, under
    return box_of(row), box_of(holder)


def on_top(row, holder):
    """Whether the concept shows the row on its holder's top (seen_pair: the box of it standing on the holder): its
    box's foot over the holder's by TOP_SHARE of the holder's box and its top no lower than the holder's top quarter
    (a window high on a module's face stays on its face); with a box missing, False (against its side)."""
    seen, under = seen_pair(row, holder)
    if not (seen and under):
        return False
    tall = under[3] - under[1]
    return under[3] - seen[3] > TOP_SHARE * tall and seen[1] < under[1] + TOP_SHARE * tall


def snapped(way):
    """The plan side (N, E, S or W) nearest a plan way."""
    return max(FACES, key=lambda face: float(numpy.asarray(FACES[face]) @ way))


def seen_side(row, holder, turn):
    """The holder's side the concept shows the row against, as a plan side: the side toward the viewer where its box
    stands within the holder's across, else the holder's left or right side as the viewer sees it; None with a box
    missing."""
    seen, under = seen_pair(row, holder)
    if not (seen and under):
        return None
    right, toward = plan_checks.ways(turn)
    across = (seen[0] + seen[2]) / 2
    if across < under[0]:
        return snapped(-right)
    return snapped(right) if across > under[2] else snapped(toward)


def side_toward(item, holder_item):
    """The holder's side toward the item on the plan (N, E, S or W), or None for an item on its spot."""
    offset = middle(item) - middle(holder_item)
    half = numpy.maximum(numpy.array([float(holder_item[3]), float(holder_item[4])]) / 2, 1e-6)
    share = offset / half
    if numpy.abs(share).max() < 0.1:
        return None
    return snapped(share * (numpy.abs(share) == numpy.abs(share).max()))


def inside(item, holder_item):
    """Whether the item's plan middle lies within its holder item's box."""
    spot, corner = middle(item), numpy.array([float(holder_item[1]), float(holder_item[2])])
    return bool((spot >= corner).all() and (spot <= corner + [float(holder_item[3]), float(holder_item[4])]).all())


def held(item, row, holder_row, holder_items, items, turn):
    """A relation to a holder the plan lays, its nearest item: top, within it where the plan lays it inside, else
    against the face the concept shows it on, the plan's side toward it, its facing, its holder's, or S."""
    nearest = min(holder_items, key=lambda name: float(numpy.linalg.norm(middle(items[name]) - middle(item))))
    if on_top(row, holder_row) and not design_shell.fills_opening(row):
        return {"how": "top", "holder": nearest, "why": f"on {holder_row['id']}'s top in the concept"}
    if inside(item, items[nearest]):
        return {"how": "within", "holder": nearest, "why": f"within {holder_row['id']}: the plan lays it inside"}
    for face, why in ((seen_side(row, holder_row, turn), "side the concept shows it on"),
                      (side_toward(item, items[nearest]), "side toward it on the plan"),
                      (item[5], "side its own facing names: the plan lays it on its holder's spot"),
                      (items[nearest][5], "facing side: the plan lays it on its holder's spot"),
                      ("S", "S side: the plan lays it on its holder's spot, facing nowhere")):
        if face:
            return {"how": "face", "holder": nearest, "face": face, "why": f"against {holder_row['id']}'s {why}"}


def walls_of(plan):
    """The plan's straight walls (an arc is left out: nothing stands against it yet)."""
    return [wall for wall in plan.get("walls") or [] if "from" in wall and "to" in wall]


def off_line(spot, wall):
    """(metres from a wall's line segment, the side of its line the spot is on: +1 or -1)."""
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    run = end - start
    share = float(numpy.clip((spot - start) @ run / max(float(run @ run), 1e-9), 0.0, 1.0))
    across = run[0] * (spot - start)[1] - run[1] * (spot - start)[0]
    return float(numpy.linalg.norm(spot - (start + run * share))), 1 if across >= 0 else -1


def seen_spot(row, plan, inventory):
    """Where the row's concept box projects onto the plan (plan_checks.projection), or None."""
    fitted, seen, picture = plan_checks.projection(plan, inventory), box_of(row), inventory.get("picture")
    if fitted is None or not seen or not picture:
        return None
    return numpy.array([(seen[0] + seen[2]) / 2 / picture[0], seen[3] / picture[1], 1.0]) @ fitted


def on_wall(item, row, plan, inventory):
    """A relation against the nearest wall to the item's spot (the concept's for the walls item), or None."""
    walls = walls_of(plan)
    if not walls:
        return None
    placed = item[0] != plan_checks.WALLS_ITEM
    spot = middle(item) if placed else seen_spot(row, plan, inventory)
    if spot is None:
        wall = max(walls, key=lambda wall: float(numpy.linalg.norm(numpy.subtract(wall["to"], wall["from"]))))
        spot, why = (numpy.asarray(wall["from"], float) + numpy.asarray(wall["to"], float)) / 2, "the longest wall's middle"
    else:
        why = "its plan spot" if placed else "where its concept box projects onto the plan"
    wall = min(walls, key=lambda wall: off_line(spot, wall)[0])
    side = off_line(spot, wall)[1]
    if off_line(spot, wall)[0] < 1e-6:  # on the line: the side toward the plan's middle
        side = off_line(numpy.array([float(plan["w"]) / 2, float(plan["d"]) / 2]), wall)[1]
    return {"how": "wall", "wall": {key: wall[key] for key in ("from", "to", "thick")}, "side": side,
            "spot": [round(float(value), 3) for value in spot], "why": f"against the wall nearest {why}"}


def openings_of(plan):
    """The plan's openings with their kinds (a data plan's doors are doors)."""
    kinds = [opening.get("kind") or "door" for opening in plan.get("openings") or []]
    return [dict(opening, kind=kinds[number] if number < len(kinds) else "door")
            for number, opening in enumerate(design_shell.plan_openings(plan))]


def kind_word(row):
    return next((word for word in ("window", "door", "gate", "hatch", "shutter")
                 if word in {found.removesuffix("s") for found in words_of(row)}), "door")


def in_opening(item, row, plan, inventory, taken):
    """A relation in the plan's opening nearest the item's spot (the concept's for the walls item) that holds none yet,
    of the row's kind first; None with none left."""
    free = [(number, opening) for number, opening in enumerate(openings_of(plan)) if number not in taken]
    if not free:
        return None
    spot = middle(item) if item[0] != plan_checks.WALLS_ITEM else seen_spot(row, plan, inventory)
    word = kind_word(row)
    alike = [pair for pair in free if (pair[1]["kind"] == "window") == (word == "window")] or free
    number, opening = min(alike, key=lambda pair: float(numpy.linalg.norm(numpy.subtract(pair[1]["at"], spot)))
                          if spot is not None else pair[0])
    taken.add(number)
    walls = walls_of(plan)
    wall = min(walls, key=lambda wall: off_line(numpy.asarray(opening["at"], float), wall)[0]) if walls else None
    return {"how": "in", "opening": {key: opening[key] for key in ("at", "wide", "sill", "head")},
            "wall": {key: wall[key] for key in ("from", "to", "thick")} if wall else None,
            "why": f"in the plan's {opening['kind']} opening {number + 1}"}


def foot(box):
    """The middle of a concept box's foot [x, y]."""
    return (box[0] + box[2]) / 2, box[3]


def standing_on(box, rows):
    """The row whose concept box holds the foot of `box`, the smallest such box's, or None."""
    x, y = foot(box)
    found = [((held[2] - held[0]) * (held[3] - held[1]), row) for row in rows for held in plan_checks.boxes_of(row)
             if held[0] <= x <= held[2] and held[1] <= y <= held[3]]
    return min(found, key=lambda pair: pair[0])[1] if found else None


def kind_words(row):
    """The words of a row's id and noun that say what it is, its place words (left, front, main...) left out."""
    return words_of({"id": row["id"], "noun": row.get("noun", "")}) - PLACE_WORDS


def seen_holders(row, holder, rows, laid):
    """The rows the concept shows the row's things standing on (hub's 38 monitors on its control bank and consoles, the
    reading's anchor naming one): for each of its boxes the row like its named holder (the same anchor, a word of
    what it is shared: a console beside a control bank, never the chair before a desk; laid on the plan) whose box
    holds its foot, the named holder first; the named holder alone where none is seen."""
    alike = [other for other in rows.values() if other["id"] in laid and other is not row
             and (other.get("anchor") or "floor") == (holder.get("anchor") or "floor")
             and kind_words(other) & kind_words(holder)]
    shown = {found["id"]: found for box in plan_checks.boxes_of(row) if (found := standing_on(box, alike))}
    return [holder, *[found for found_id, found in shown.items() if found_id != holder["id"]]]


def relation(item, row, rows, plan, inventory, laid, taken, turn):
    """One item's relation (module docstring) for its row, or (None, why) when nothing holds it."""
    anchor = row.get("anchor") or "floor"
    holder = rows.get(anchor[3:]) if anchor.startswith("on:") else None
    if anchor.startswith("on:") and holder is None:
        return None, f"its holder {anchor[3:]} is no row of the inventory"
    if holder is not None and holder["id"] in laid:  # an item of its own, or tied to its holder's: laid on it
        items, shown = plan_items(plan), seen_holders(row, holder, rows, laid)
        nearest = min(((other, name) for other in shown for name in laid[other["id"]]),
                      key=lambda pair: float(numpy.linalg.norm(middle(items[pair[1]]) - middle(item))))
        found = held(item, row, nearest[0], [nearest[1]], items, turn)
        if len(shown) > 1:
            found["why"] += (f" (its things stand on {len(shown)} rows in the concept: "
                             f"{', '.join(other['id'] for other in shown)}; the nearest on the plan)")
        return found, None
    kind = "wall" if anchor == "wall" else "ceiling" if anchor in ("ceiling", "roof") else (
        holder_kind(holder) if holder is not None else None)
    if kind in ("floor", "ceiling"):
        return {"how": kind, "why": f"on the place's {kind}"}, None
    if kind != "wall":
        return None, (f"its holder {holder['id']} is neither laid on the plan nor a wall, floor or roof"
                      if holder is not None else None)
    found = in_opening(item, row, plan, inventory, taken) if design_shell.fills_opening(row) else None
    found = found or on_wall(item, row, plan, inventory)
    return (found, None) if found else (None, "it stands on a wall, and the plan draws none")


def plan_items(plan):
    return items_of(plan)[0]


def relations(plan, inventory, sha=None):
    """The place's relations (module docstring): one a plan item's row that stands on, against or in something."""
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    items, tied = items_of(plan)
    structure = set(plan.get("structure") or [])
    laid = {row_id: kept for row_id, names in tied.items() if row_id not in structure
            for kept in [[name for name in names if name != plan_checks.WALLS_ITEM]] if kept}
    found, unheld, taken = [], [], set()
    turn = plan_checks.viewed(plan, inventory)[2]  # the way the concept's viewer looks on the plan
    for name, item in items.items():
        for row_id in (plan.get("rows") or {}).get(name) or []:
            row = rows.get(row_id)
            if row is None or (row.get("anchor") or "floor") in plan_checks.FLOOR_ANCHORS:
                continue
            got, why = relation(item, row, rows, plan, inventory, laid, taken, turn)
            if got:
                found.append({"item": name, "row": row_id, **got})
            elif why:
                unheld.append({"item": name, "row": row_id, "why": why})
    return {"place": plan.get("place") or inventory.get("place"), "plan": sha,
            "about": "What holds each plan item, derived from the scene inventory's anchors, the concept's boxes and "
                     "the kept plan (score/review/holders); the scene record lays each object by it.",
            "relations": found, "unheld": unheld}


def keep(places):
    """Each place's relations written where the scene record reads them, from its kept plan and scene inventory; the
    places whose file changed."""
    changed = []
    for place in places:
        plan_path, inventory_path, path = (KEPT_PLANS / f"{place}.json", KEPT_INVENTORY / f"{place}.json",
                                           KEPT / f"{place}.json")
        if not (plan_path.is_file() and inventory_path.is_file()):
            continue
        text = plan_path.read_text()
        found = json.dumps(relations(json.loads(text), json.loads(inventory_path.read_text()), plan_sha(text)),
                           indent=1)
        if not path.is_file() or path.read_text() != found:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(found)
            changed.append(place)
    return changed
