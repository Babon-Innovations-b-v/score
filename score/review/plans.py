"""Plan review (CONTEXT.md "plan", "design", "shell split"): a place's plan, the second half of its design, made
automatically once its concept is picked and its scene inventory read from it (owner, 2026-10-21: picking the
concept is the approval; the plan page is for inspecting and fixing it, his edits redoing what follows).

The plan shown is written by the prompt model (plan_writing.py, `made_plan`); until it is, a rough one is drawn free
from data already there (`derived`, also the skeleton the writing starts from): the place's plan in data/plans (its shell, frame, walls,
doors and where each leads, the neighbours' joined doors in its leads), its outline from the layer above's plan (its
box in that plan's `holds`), and its items from its scene inventory, each item tied to its inventory row (a row laid
at a spot stands there, one with none along the walls in the order its SAM box stands on the picture (never projected);
each sized by its reading's metres; a row the reading gives no size, and a lamp or beam on a row this concept's
inventory lacks, is named in the plan's `gaps`, shown on his page), a keep-clear zone in front of every
door, its standing spots. A place holding others (a shell, the Square, the Hangar, the Campgrounds) lays out its
inside places in it (`holds`: each a box with its name and the holder's inventory row it stands in, None for the
holder's own walls: the shell split): those listed now (within.json, then his edits), plus those he named on its
concept page.

The store keeps his work, written only in the owner's process (`concepts.recorded`'s barrier):

    plans/<place>/edits/<time>.json      {place, plan, concept (the pick it was made on), by, at, how, calls}
    plans/<place>/named/<time>.json      {place, names, by, at}: inside places he named on the concept page

The plan shown is his newest edit made on the current pick, else the derived one; the plan stage reads it (`keep`:
{home}/design/plans/<place>.json, written on his edit and by the sync pass, stages.creator_plan). An inside place's
concept is drawn only once the layer above's plan is made (`made`, concepts.step_refusal), from the row holding it
there (`holder_of`: the row, its SAM box, its outline); `shape_sent` draws its shape on that plan. His notes go to Gemini 3.1 Pro (`revised`: one direct call, his click its spend yes at
`revise_euros`, run as its own process like a concept draw):

    SCORE_SPEND_TICKET="override <key>" python -m score.review.plans <place> <request.json> <by>
    python -m score.review.plans keep      # every place's plan where the plan stage reads it (the sync pass)
"""
import contextlib
import contextvars
import copy
import hashlib
import io
import json
import math
import pathlib
import re
import sys

from score.review import concepts
from score.store import PROPS_HOME, stamp_key

AREA = "plans"
DATA = concepts.DATA
KEPT = PROPS_HOME / "design" / "plans"  # the plan the plan stage reads in place of data/plans (stages.creator_plan)
KEPT_INVENTORY = PROPS_HOME / "design" / "inventory"  # and the scene inventory it was made from
KEPT_CONCEPT = PROPS_HOME / "design" / "concepts"  # and the picked concept both were made from (its `concept` input)
SIDES = ("N", "S", "E", "W")
FACINGS = {0: "N", 90: "E", 180: "S", 270: "W"}
WALLS_ITEM = "ON THE WALLS AND CEILING"
GAP = 0.3  # metres between items laid along the walls, and round inside places laid in their holder
CLEAR = 1.2  # metres a door's keep-clear zone reaches into the room
BIGGEST = 2000.0  # metres: no plan is wider or deeper
NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
PIXELS = 900  # the drawing's longer side


class Refused(ValueError):
    pass


def records(store, place, kind):
    """The records of one place's `kind` (edits or named), oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{place}/{kind}/"))]


def kept_record(store, place, kind, record):
    """Write one of his records once (the owner's process only, or an agent's carrying his words for a design edit he
    asked for in a session: `asked`, root CLAUDE.md, the owner 2026-10-21); the record."""
    key = f"{AREA}/{place}/{kind}/{stamp_key(record['at'])}.json"
    if kind == "edits" and (record.get("asked") or {}).get("words") and (record["asked"]).get("at"):
        store.write_once(key, record)
    else:
        concepts.recorded(store, key, record)
    return record


# --- where places sit -----------------------------------------------------------------------------------------

def within_file():
    path = DATA / "places/within.json"
    found = json.loads(path.read_text()) if path.is_file() else {}
    return ({name: entry["within"] for name, entry in found.get("within", {}).items()},
            {name: entry["name"] for name, entry in found.get("shells", {}).items()})


def tree(store):
    """{within, shells}: data/places/within.json (environment 1's starting list) with the inside places his edits
    laid out (`overlaid`)."""
    within, shells = within_file()
    return once("tree", store, None, lambda: {"within": overlaid(store, within), "shells": shells})


def removed(store, within):
    """The places of `within` that no holder's newest edit lays out any more: the creator removed them (merged into
    another, owner 2026-10-21), so they are no card at all, never an outside place."""
    kept = overlaid(store, within)
    return sorted(place for place in within if place not in kept)


def overlaid(store, within):
    """{place: what holds it} with each holder's inside places replaced by the ones his newest edit of its plan lays
    out (CONTEXT.md "shell split", owner 2026-10-21)."""
    within = dict(within)
    for holder in sorted({key.split("/")[1] for key in store.objects.keys(f"{AREA}/")}):
        edit = newest_edit(store, holder)
        if edit is None or "holds" not in edit["plan"]:
            continue
        within = {place: above for place, above in within.items() if above != holder}
        within.update({hold["place"]: holder for hold in edit["plan"]["holds"]})
    return within


def named(store, place):
    """The inside places he named on `place`'s concept page, newest list ([] when none)."""
    found = records(store, place, "named")
    return found[-1]["names"] if found else []


def proposed_inside(store, place):
    """The inside places `place`'s derived plan lays out: those listed in it now, then those the locked environment
    concept says it holds (environment_concept.places_in_force), then those he named."""
    listed = [name for name, above in tree(store)["within"].items() if above == place]
    return list(dict.fromkeys([*listed, *concept_holds(store, place, listed), *named(store, place)]))


def concept_holds(store, place, listed):
    """The inside places the environment concept in force lists under `place`, as place names, less those `listed`
    already (matched by their names as the cockpit says them)."""
    from score.review import environment_concept
    entry = next((entry for entry in environment_concept.places_in_force(store, sorted(within_file()[0]))
                  if entry["place"] == place), {})
    said = {environment_concept.name_in(name, concepts.tree()).lower() for name in listed}
    return checked_names([name for name in entry.get("holds", []) if name.lower() not in said])


def checked_names(names):
    """Inside place names as given: short lowercase words (a-z, 0-9, _), no repeats; Refused otherwise."""
    found = []
    for name in names or []:
        name = str(name).strip().lower().replace(" ", "_")
        if not NAME.match(name):
            raise Refused(f"{name!r} is no place name (a-z, 0-9 and _, up to 40)")
        if name not in found:
            found.append(name)
    return found


# --- the pick and the inventory ---------------------------------------------------------------------------------

def pick_of(store, place):
    return concepts.picked(store, place)


def inventory_of(store, place):
    """The place's scene inventory read from its picked concept, else None (CONTEXT.md "scene inventory": none counts
    before the pick, an older one never does): its reading (score/review/reading.py), with the shell's room layout of
    its data/inventory file (walls, doors, roof opening: the plan's numbers, no object of an older concept), else a
    data/inventory file whose concept_pick is that pick."""
    from score.review import reading
    filed = filed_inventory(place)
    found = reading.reading_of(store, place)
    if found and found.get("inventory"):
        # its rows' boxes are pixels of the picture's size
        return {**found["inventory"], "picture": found.get("size"), **({"room": filed["room"]} if "room" in filed else {})}
    pick = pick_of(store, place)
    return filed if pick and (filed.get("concept_pick") or {}).get("sha256") == pick else None


def filed_inventory(place):
    """The place's data/inventory file (its plan's `inventory` name, else its own), {} with none."""
    plan_path = DATA / "plans" / f"{place}.json"
    name = json.loads(plan_path.read_text()).get("inventory", place) if plan_path.is_file() else place
    path = DATA / "inventory" / f"{name}.json"
    return json.loads(path.read_text()) if path.is_file() else {}


def counts(store, place):
    """Whether `place`'s scene inventory counts: read from its picked concept."""
    return inventory_of(store, place) is not None


def made(store, place):
    """Whether `place`'s plan is made (the step a place within it waits for, concepts.step_refusal): plan@<place>
    accepted after its pick for a place with a plan row, else its plan shown here."""
    if not has_row(place):
        return current(store, place) is not None
    picks = concepts.records(store, place, "picks")
    accept = store.current_accept(f"plan@{place}")
    return bool(picks and picks[-1]["sha"] and accept and accept["at"] > picks[-1]["at"])


def newest_edit(store, place):
    """His newest edit of `place`'s plan made on its current pick, else None."""
    pick = pick_of(store, place)
    found = [record for record in records(store, place, "edits") if pick and record["concept"] == pick]
    return found[-1] if found else None


def holder_of(store, place):
    """{holder, row, box, view, outline} of `place` on the layer above's plan, None while that has no plan or does
    not lay it out: the holder, its inventory row the place stands in (None: the holder's own walls), that row's box
    on the holder's picked concept and its view (the inventory's SAM box, None when it has none), and the place's
    outline in the holder's plan [x, y, w, d] in metres."""
    hold = room_of(store, place)
    if hold is None:
        return None
    holder = tree(store)["within"][place]
    row = next((row for row in inventory_of(store, holder).get("rows", []) if row["id"] == hold.get("row")), {})
    box = (row.get("boxes") or [None])[0] if "boxes" in row else row.get("box")  # a reading's surest SAM box first
    return {"holder": holder, "row": hold.get("row"), "box": box, "view": row.get("view"),
            "outline": [hold["x"], hold["y"], hold["w"], hold["d"]]}


def above_plan(store, place):
    """(the plan shown of the layer above `place`, `place`'s hold on it: row, outline, shape); (None, None) while that
    has no plan, a hold None while it does not lay `place` out."""
    holder = tree(store)["within"].get(place)
    shown = current(store, holder) if holder else None
    return shown, next((hold for hold in (shown or {}).get("plan", {}).get("holds", []) if hold["place"] == place),
                       None)


def room_of(store, place):
    """`place`'s room on the layer above's plan shown now (its hold there), None while it lays none out."""
    return above_plan(store, place)[1]


def moved_draws(store, place):
    """The shas of `place`'s draws drawn on another room than the layer above's plan gives it now (moved, resized,
    reshaped, merged: owner 2026-10-21, "all below would become need for redrawn"): each draw's recorded room against
    today's, a Redraw with notes by its base's."""
    draws = concepts.draws(store, place)
    by_sha = {}
    for draw in draws:  # the first draw of a sha: a redraw can come back as its base's picture
        by_sha.setdefault(draw.get("sha"), draw)
    shown, room = above_plan(store, place)
    since = shown and shown["at"]

    def moved(draw, seen=()):
        if draw.get("base"):
            base = by_sha.get(draw["base"])
            return base is not None and base is not draw and draw["base"] not in seen and moved(
                base, (*seen, draw["base"]))
        if "room" in draw:
            return draw["room"] != room
        # shortcut: a draw from before rooms were recorded counts as moved by any plan of the layer above made after
        # it, whether or not that plan moved this room; drop once no such draw is in use
        return bool(since) and draw.get("at", "") < since
    return {draw.get("sha") for draw in draws if moved(draw)}


# --- the plan drawn from data --------------------------------------------------------------------------------

def base_plan(place):
    """The place's plan in data/plans (a deep copy), else a bare one of the house schema."""
    path = DATA / "plans" / f"{place}.json"
    if path.is_file():
        return json.loads(path.read_text())
    return {"title": place.upper(), "shell": "kit", "w": 0.0, "d": 0.0, "height": "", "doors": [], "leads": {},
            "items": [], "rows": {}, "people": []}


def to_plan(plan, spot):
    """A place-frame spot {x, z} as plan metres (x east, y south from its north-west corner)."""
    from score.stages.scene_record.plan import frame_of
    corner, east, south = frame_of(plan)
    offset = [spot.get("x", 0.0) - corner[0], 0.0, spot.get("z", 0.0) - corner[2]]
    return (round(sum(a * b for a, b in zip(offset, east)), 3), round(sum(a * b for a, b in zip(offset, south)), 3))


UNSIZED = (1.0, 1.0)  # an item nothing gives a size: laid 1 x 1 m, and named a gap


def measured(row):
    """(wide, deep) of a row's floor footprint in metres: its scene inventory size (a reading's metres, judged by
    Gemini from what it is and the picture, or a data/inventory file's), None when it has none (a gap: SAM 3's box
    gives where a row stands, never its size)."""
    if isinstance(row.get("size"), list):
        size = list(row["size"]) + [1.0, 1.0]
        return abs(float(size[0])) or 0.5, abs(float(size[1])) or 0.5
    return None


def footprint(row, facing):
    """(wide, deep) of a row on the floor (`measured`, else UNSIZED), turned with its facing (a row facing east or
    west lies across)."""
    wide, deep = measured(row) or UNSIZED
    return (deep, wide) if facing in ("E", "W") else (wide, deep)


def facing_of(spot):
    """A spot's facing in degrees as a side (N, E, S, W), None when it names none."""
    degrees = spot.get("facing")
    return None if degrees is None else FACINGS[int(round(float(degrees) / 90.0)) % 4 * 90]


def anchor_of(row):
    """A row's anchor: floor, wall, ... or the id of the row it stands on (a reading's `on:<id>`)."""
    anchor = row.get("anchor") or "floor"
    return anchor[3:] if anchor.startswith("on:") else anchor


WHOLE = 0.6  # a row whose surest box spans this share of the picture both ways is the place itself (its ground, sky)


GROUND = {"sea", "ocean", "water", "lake", "pool", "river", "harbour", "plaza", "square", "ground", "terrain", "sky",
          "floor", "road", "street", "pavement", "grass", "sand", "dust", "regolith", "soil", "skyline", "backdrop",
          "horizon", "mountains", "hills"}


def whole(row, picture):
    """Whether a row is the place itself rather than a thing in it: its surest box spans most of the picture, or it
    is the place's ground, water or sky (`GROUND`: the plan's ground and terrain, never a sized object; owner,
    2026-10-21)."""
    box = (row.get("boxes") or [None])[0]
    # what it is, the last word of its id or noun ("harbour_water", not "floor_lamp")
    words = {re.split(r"[_\s]+", str(said).strip().lower())[-1] for said in (row["id"], row.get("noun") or "")}
    return bool(box and picture and (box[2] - box[0]) >= WHOLE * picture[0] and (box[3] - box[1]) >= WHOLE * picture[1]
                or row.get("anchor") == "sky" or (anchor_of(row) in ("floor", "ground") and words & GROUND))


def row_items(rows):
    """[(name, row id, spot or None)] of every floor instance of the inventory's rows: one per laid spot, else one
    per count; rows on the walls, the ceiling or another row are left to `walls_rows` and `children`."""
    found = []
    for row in rows:
        if anchor_of(row) not in ("floor", "ground"):
            continue
        label = str(row.get("id")).replace("_", " ").upper()
        spots = row.get("at") or [None] * int(row.get("count", 1) or 1)
        boxes = row.get("boxes") or []
        found += [(f"{label} {number}", row["id"], spot, boxes[number - 1] if number <= len(boxes) else None)
                  for number, spot in enumerate(spots, 1)]
    return found


def walls_rows(rows):
    """The row ids anchored on a wall or the ceiling (and none on another row): the plan's walls-and-ceiling item."""
    ids = {row["id"] for row in rows}
    return [row["id"] for row in rows if anchor_of(row) not in {"floor", "ground"} | ids]


def children(rows):
    """{parent row id: [child row ids]} of rows anchored on another row (they ride on its item)."""
    ids, found = {row["id"] for row in rows}, {}
    for row in rows:
        if anchor_of(row) in ids:
            found.setdefault(anchor_of(row), []).append(row["id"])
    return found


def laid_along(boxes, wide):
    """Positions for boxes (wide, deep) laid in rows from the north-west corner, GAP apart, wrapping at `wide`."""
    found, x, y, row_deep = [], GAP, GAP, 0.0
    for box_wide, box_deep in boxes:
        if x + box_wide > wide - GAP and x > GAP:
            x, y, row_deep = GAP, y + row_deep + GAP, 0.0
        found.append((round(x, 3), round(y, 3)))
        x, row_deep = x + box_wide + GAP, max(row_deep, box_deep)
    return found


def across(box):
    """Where a SAM box stands across the picture (its middle), the order unplaced items are laid in: a hint of order,
    never a plan position (owner, 2026-10-21: boxes on a perspective painting projected top down are no plan)."""
    return (box[0] + box[2]) / 2 if box else math.inf


def items_from(plan, inventory):
    """(items, rows, unsized) of the plan from its scene inventory: each floor instance a box at its laid spot, else
    laid along the walls in the order their boxes stand on the picked concept left to right (`across`), sized by
    `measured` (its reading's metres), tied to its row and the rows riding on it; one walls-and-ceiling item over the
    whole floor, the rows that are the place itself (`whole`) on it; `unsized` [(item, row id)] the items nothing
    gives a size. The written plan (plan_writing.py) places them; this one is the free stand-in until it is."""
    picture = inventory.get("picture")
    rows = [row for row in inventory.get("rows", []) if not whole(row, picture)]
    riders = children(rows)
    instances = sorted(row_items(rows), key=lambda instance: across(instance[3]))
    by_id = {row["id"]: row for row in rows}
    unplaced = [footprint(by_id[row_id], None) for _, row_id, spot, _ in instances if spot is None]
    free = iter(laid_along(unplaced, plan["w"]))
    items, tied, unsized = [], {}, []
    for name, row_id, spot, _ in instances:
        facing = facing_of(spot) if spot else None
        wide, deep = footprint(by_id[row_id], facing)
        if measured(by_id[row_id]) is None:
            unsized.append((name, row_id))
        if spot:
            middle_x, middle_y = to_plan(plan, spot)
            x, y = middle_x - wide / 2, middle_y - deep / 2
        else:
            x, y = next(free)
        items.append([name, round(x, 3), round(y, 3), round(wide, 3), round(deep, 3), facing, "item"])
        tied[name] = [row_id, *riders.get(row_id, [])]
    on_walls = walls_rows(rows) + [row["id"] for row in inventory.get("rows", []) if whole(row, picture)]
    if on_walls:
        items.append([WALLS_ITEM, 0.0, 0.0, plan["w"], plan["d"], None, "item"])
        tied[WALLS_ITEM] = on_walls
    return items, tied, unsized


def unlit(plan, ids):
    """(lamps, beams, gaps) of the plan: its outdoor lamps and beams standing on a row of its scene inventory (`ids`)
    or another place's, and a gap for each whose row this concept's reading does not hold (the plan stage's `mapped`
    gate refuses a lamp or beam on a row the inventory lacks: data/plans' lamps were written for an older concept)."""
    kept, gaps = {}, []
    for kind in ("lamps", "beams"):
        kept[kind] = [entry for entry in plan.get(kind, []) if entry["row"] in ids or entry.get("place")]
        gaps += [{"kind": kind[:-1], "item": entry["name"], "row": entry["row"],
                  "words": f"{kind[:-1]} {entry['name']}: no {entry['row'].replace('_', ' ')} in this concept"}
                 for entry in plan.get(kind, []) if entry not in kept[kind]]
    return kept["lamps"], kept["beams"], gaps


def unleafed(leads, ids):
    """(leads, gaps) of the plan's doors: each lead whose leaf's row this concept's reading holds (`ids`) as it is, the
    rest without their leaf and a gap each (the plan stage's `mapped` gate refuses a leaf on a row the inventory lacks:
    data/plans' leaves were written for an older concept, the airlock's door_leaf, #10)."""
    kept, gaps = {}, []
    for side, lead in leads.items():
        leaf = lead.get("leaf")
        if leaf and leaf["row"] not in ids:
            lead = {key: value for key, value in lead.items() if key != "leaf"}
            gaps.append({"kind": "leaf", "item": leaf.get("name") or side, "row": leaf["row"],
                         "words": f"door {side}'s leaf {leaf.get('name') or ''}: no "
                                  f"{leaf['row'].replace('_', ' ')} in this concept"})
        kept[side] = lead
    return kept, gaps


def size_gaps(unsized):
    """A gap for each item nothing gives a size (laid UNSIZED): the batch needs its size."""
    return [{"kind": "size", "item": name, "row": row_id, "words": f"{name.title()}: no size"}
            for name, row_id in unsized]


def sized_doors(plan, filed):
    """The plan's doors, each wall door whose words give no size given the one its leaf has in the data/inventory
    file (`W x H m`, as the plan stage reads a door's height; the leaf is the shell's, not an object of a concept)."""
    from score.stages.scene_record.plan import SIDES as WALLS, SIZE, leaf_tall
    kinds = (filed.get("room") or {}).get("layout", {}).get("doors", {})
    found = []
    for door in plan.get("doors", []):
        tall = (leaf_tall(filed, kinds[WALLS[door[0]]]) if door[0] in SIDES and not SIZE.search(str(door[3]))
                and kinds.get(WALLS[door[0]]) and filed.get("rows") else None)
        found.append([*door[:3], f"{door[3]} ({float(door[2]):g} x {tall:g} m)", *door[4:]] if tall else door)
    return found


def keep_clear(plan):
    """A keep-clear zone reaching CLEAR into the room in front of each wall door (N, S, E, W)."""
    found = []
    for door in plan.get("doors", []):
        if door[0] not in SIDES:  # a faceted room's door by bearing, a tube's end: no wall to stand clear of
            continue
        side, at, wide = door[0], float(door[1]), float(door[2])
        span = wide + 0.4
        x, y, zone_wide, zone_deep = {"N": (at - span / 2, 0.0, span, CLEAR),
                                      "S": (at - span / 2, plan["d"] - CLEAR, span, CLEAR),
                                      "W": (0.0, at - span / 2, CLEAR, span),
                                      "E": (plan["w"] - CLEAR, at - span / 2, CLEAR, span)}[side]
        found.append([f"KEEP CLEAR {side} {at:g}", round(x, 3), round(y, 3), round(zone_wide, 3),
                      round(zone_deep, 3), None, "zone"])
    return found


def held_size(place):
    """(wide, deep) of an inside place from its own plan, else 6 x 6 m."""
    path = DATA / "plans" / f"{place}.json"
    plan = json.loads(path.read_text()) if path.is_file() else {}
    return float(plan.get("w") or 6.0), float(plan.get("d") or 6.0)


def holding_row(rows, place):
    """The id of the holder's inventory row an inside place stands in: one named as the place, else one whose id ends
    in the place's name (the base's `central_hub` for the hub, `connecting_tube_1` for the tube), else one whose id within.json's reading of the place
    names or ends in a thing it names that is no place (the hangar's `spaceship` for its rooms, "the ship"); None:
    the holder's own walls (he sets it on the plan page)."""
    ids = [row["id"] for row in rows]
    if named_row(ids, place):
        return named_row(ids, place)
    said = json.loads((DATA / "places/within.json").read_text()).get("within", {}).get(place, {}).get("from", "") \
        if (DATA / "places/within.json").is_file() else ""
    # a thing it names that is no place (the hangar's rooms: "the ship"), as the end of a row's id ("spaceship")
    places = {path.stem for path in (DATA / "plans").glob("*.json")} | set(within_file()[0]) | set(within_file()[1])
    words = {word for word in re.findall(r"[a-z]{4,}", said.lower()) if word not in places}
    named = [row_id for row_id in ids if re.search(rf"\b{re.escape(row_id)}\b", said)
             or any(re.sub(r"(_\d+)+$", "", row_id).endswith(word) for word in words)]
    return min(named, key=len) if named else None


def named_row(ids, place):
    """The row of `ids` named as `place`, else the shortest whose id ends in its name (`central_hub` for the hub);
    None."""
    if place in ids:
        return place
    worded = [row_id for row_id in ids if re.sub(r"(_\d+)+$", "", row_id).split("_")[-1] == place]
    return min(worded, key=len) if worded else None


def neighbours_row(hold, holds):
    """The row `hold`'s room stands in: the row holding rooms it touches or adjoins (within GAP; the longest shared
    edge) when that row holds more rooms than its own, over the row its box was guessed into by overlap (owner,
    2026-10-21, the docking airlock behind the engine room filed under the crane: "that part is still part of the
    ship"); its own row when that names it (the base's `central_hub` for the hub) or is None (its own floor)."""
    if not hold["row"] or named_row([hold["row"]], hold["place"]):
        return hold["row"]
    held = [other["row"] for other in holds]
    shared = {}
    for other in holds:
        if other is hold or not other["row"] or held.count(other["row"]) <= held.count(hold["row"]):
            continue
        across = min(hold["x"] + hold["w"], other["x"] + other["w"]) - max(hold["x"], other["x"])
        along = min(hold["y"] + hold["d"], other["y"] + other["d"]) - max(hold["y"], other["y"])
        if min(across, along) > -GAP and max(across, along) > 0:
            shared[other["row"]] = shared.get(other["row"], 0.0) + max(across, along)
    return max(shared, key=shared.get) if shared else hold["row"]


def holds_of(store, place, plan, rows):
    """The plan's inside places, each a box {place, row, x, y, w, d}: those standing in one of its rows laid in rows
    inside that row's item (the hangar's rooms in its ship), the item grown round them when it is smaller (a
    reading's row is 1 x 1 m until its close-up is measured), the others in the outline."""
    names = proposed_inside(store, place)
    items = {plan["rows"][item[0]][0]: item for item in plan["items"] if plan["rows"].get(item[0])}
    found = []
    for row in dict.fromkeys(holding_row(rows, name) for name in names):
        group = [name for name in names if holding_row(rows, name) == row]
        sizes = [held_size(name) for name in group]
        item = items.get(row)
        spots = laid_along(sizes, max(item[3], square(sizes)) if item else plan["w"] or square(sizes))
        x0 = y0 = 0.0
        if item:
            grown(item, spots, sizes, plan)
            x0, y0 = item[1], item[2]
        found += [{"place": name, "row": row, "x": round(x0 + x, 3), "y": round(y0 + y, 3), "w": size[0],
                   "d": size[1]} for name, (x, y), size in zip(group, spots, sizes)]
    return sorted(found, key=lambda hold: names.index(hold["place"]))


def grown(item, spots, sizes, plan):
    """A row's item grown round the inside places laid in it at `spots`, then moved back inside the outline."""
    item[3] = round(max(item[3], max(x + size[0] for (x, _), size in zip(spots, sizes)) + GAP), 3)
    item[4] = round(max(item[4], max(y + size[1] for (_, y), size in zip(spots, sizes)) + GAP), 3)
    if plan["w"] and plan["d"]:
        item[1] = round(min(max(0.0, item[1]), max(0.0, plan["w"] - item[3])), 3)
        item[2] = round(min(max(0.0, item[2]), max(0.0, plan["d"] - item[4])), 3)


def square(sizes):
    """The width of an outline about square round boxes of `sizes` (a holder with no outline of its own: a shell
    with no plan)."""
    return max([sum(size[0] + GAP for size in sizes) / max(1, math.ceil(len(sizes) ** 0.5))]
               + [size[0] + GAP * 2 for size in sizes] + [1.0])


def outline_from_holder(store, place, plan):
    """The plan's w and d as the layer above's plan lays the place out (its box there), else its own, else round its
    inside places (`outline_from_inside`: a shell with no plan of its own, the base), so its items are placed on an
    outline before they are laid; (0, 0) with none of these."""
    held = holder_of(store, place)
    if held:
        return tuple(held["outline"][2:])
    return (plan["w"], plan["d"]) if plan["w"] and plan["d"] else outline_from_inside(store, place)


def outline_from_inside(store, place):
    """(wide, deep) of an outline round the place's inside places laid about square (`square`, `laid_along`), each
    its own plan's size (`held_size`); (0, 0) for a place holding none."""
    sizes = [held_size(name) for name in proposed_inside(store, place)]
    if not sizes:
        return 0.0, 0.0
    spots = laid_along(sizes, square(sizes))
    return (round(max(x + size[0] for (x, _), size in zip(spots, sizes)) + GAP, 3),
            round(max(y + size[1] for (_, y), size in zip(spots, sizes)) + GAP, 3))


def derived(store, place):
    """The place's plan drawn free from data (module docstring): None while its scene inventory does not count."""
    if not counts(store, place):
        return None
    plan = copy.deepcopy(base_plan(place))
    plan.pop("holds", None)  # a hand plan's {place: row} (concepts.holding_row's fallback): laid out here instead
    plan["w"], plan["d"] = outline_from_holder(store, place, plan)
    plan["doors"] = sized_doors(plan, filed_inventory(place))
    inventory = inventory_of(store, place)
    items, tied, unsized = items_from(plan, inventory)
    ids = {row["id"] for row in inventory.get("rows", [])}
    lamps, beams, unlit_gaps = unlit(plan, ids)
    plan.update({key: found for key, found in (("lamps", lamps), ("beams", beams)) if key in plan})
    leads, leaf_gaps = unleafed(plan.get("leads", {}), ids)
    plan.update({"leads": leads} if "leads" in plan else {})
    # what this concept's inventory does not give: shown, never hidden
    plan["gaps"] = unlit_gaps + leaf_gaps + size_gaps(unsized)
    zones = keep_clear(plan)
    plan["items"] = items + zones
    plan["rows"] = {**tied, **{zone[0]: [] for zone in zones}}  # a zone names no rows, and says so
    plan["elements"] = [{"element": row.get("name") or row["id"], "rows": [row["id"]]}
                        for row in inventory.get("rows", [])]
    plan["people"] = plan.get("people") or [[round(plan["w"] / 2, 3), round(plan["d"] / 2, 3)]]
    holds = holds_of(store, place, plan, inventory.get("rows", []))
    if holds:
        plan["holds"] = holds
        plan["w"] = plan["w"] or round(max(hold["x"] + hold["w"] for hold in holds) + GAP, 3)
        plan["d"] = plan["d"] or round(max(hold["y"] + hold["d"] for hold in holds) + GAP, 3)
    return plan


def written(store, place):
    """The plan written for `place` from its pick and inventory (plan_writing.written_of), None while none is."""
    from score.review import plan_writing
    return plan_writing.written_of(store, place)


def made_plan(store, place):
    """{plan, how, at, by} of the plan made for `place` without him: its written plan (how: written), else the derived
    one (how: derived, at and by None); None while its inventory does not count."""
    if not counts(store, place):
        return None
    found = written(store, place)
    if found:
        plan = {**found["plan"], "gaps": checked_again(found["plan"], inventory_of(store, place))}
        return {"plan": plan, "how": "written", "at": found["at"], "by": found["by"]}
    return {"plan": derived(store, place), "how": "derived", "at": None, "by": None}


CHECKED = {}  # {plan sha: its gaps}: a written plan checked once a process


def checked_again(plan, inventory):
    """A written plan's gaps by today's free checks (plan_checks; its inside places not laid out kept as written), so
    a check sharpened since it was written counts without writing it again."""
    from score.review import plan_checks
    key = plan_sha(plan)
    if key not in CHECKED:
        CHECKED[key] = [gap for gap in plan.get("gaps", []) if gap["kind"] == "place"] + plan_checks.checked(
            plan, inventory, plan.get("structure", []))
    return CHECKED[key]


HELD = contextvars.ContextVar("plans_held", default=None)  # {(what, store id, key): answer} inside one_moment()


@contextlib.contextmanager
def one_moment():
    """Inside it each answer `once` is asked for is made once and handed out as copies: a read-only page state is
    built from one moment's store and data and asked the same plans hundreds of times (a cockpit page took 33 s,
    2026-10-21). Never open it round a write."""
    token = HELD.set({}) if HELD.get() is None else None
    try:
        yield
    finally:
        if token is not None:
            HELD.reset(token)


def once(what, store, key, make, shared=False):
    """`make()`, the answer of `what` for `key` in `store`: inside `one_moment` made once and handed out as copies
    (a caller may change its own), or the one answer itself when `shared` (every reader only reads it), else made
    now."""
    memo = HELD.get()
    if memo is None:
        return make()
    if (what, id(store), key) not in memo:
        memo[what, id(store), key] = make()
    return memo[what, id(store), key] if shared else copy.deepcopy(memo[what, id(store), key])


def current(store, place):
    """{plan, how, at, by} of the plan shown: the newer of his newest edit made on the current pick (how: edited or
    revised) and the plan made without him (`made_plan`: written, else derived); None while its inventory does not
    count."""
    return once("plan", store, place, lambda: shown_plan(store, place))


def shown_plan(store, place):
    """`current`'s answer, made now."""
    made_one = made_plan(store, place)
    edit = newest_edit(store, place) if made_one else None
    if edit and (made_one["at"] is None or edit["at"] > made_one["at"]):
        return {key: edit.get(key) for key in ("plan", "how", "at", "by")}
    return made_one


# --- his edits --------------------------------------------------------------------------------------------------

def number(value, what, low=0.0, high=BIGGEST):
    try:
        found = float(value)
    except (TypeError, ValueError) as broken:
        raise Refused(f"{what} is not a number: {value!r}") from broken
    if not (low <= found <= high) or math.isnan(found):
        raise Refused(f"{what} {found:g} lies outside {low:g} to {high:g}")
    return round(found, 3)


def checked_items(items):
    found = []
    for item in items:
        name, x, y, item_wide, item_deep, facing, kind = item
        if facing not in (None, *SIDES) or kind not in ("item", "zone", "plot", "roof_door"):
            raise Refused(f"{name}: facing {facing!r} or kind {kind!r} is not a plan item's")
        found.append([str(name)[:80], number(x, f"{name} x", -BIGGEST), number(y, f"{name} y", -BIGGEST),
                      number(item_wide, f"{name} wide", 0.01), number(item_deep, f"{name} deep", 0.01), facing, kind])
    return found


def checked_doors(doors, base):
    """His doors: those of the derived plan, each a wall door moved along its wall or onto another (N, S, E, W);
    a faceted or tube door stays as it was."""
    if len(doors) != len(base):
        raise Refused("a plan keeps its doors: move them, never add or drop one here")
    found = []
    for door, was in zip(doors, base):
        if was[0] not in SIDES:
            found.append(was)
            continue
        if door[0] not in SIDES:
            raise Refused(f"door side {door[0]!r} is none of {SIDES}")
        found.append([door[0], number(door[1], "a door's place on its wall"), *was[2:]])
    return found


def checked_plan(plan, base):
    """His plan as sent from the page, checked against the derived one (`base`): its items, doors, standing spots and
    inside places edited, everything else kept from `base`; Refused otherwise."""
    if not isinstance(plan, dict):
        raise Refused("not a plan")
    found = copy.deepcopy(base)
    names = {item[0] for item in plan.get("items", [])}
    rows = {name: base.get("rows", {}).get(name, []) for name in names}
    for name in names - set(base.get("rows", {})):
        rows[name] = [str(row) for row in plan.get("rows", {}).get(name, [])]
    found["items"] = checked_items(plan.get("items", []))
    found["rows"] = rows
    found["gaps"] = sized_by_him(base, found["items"])
    found["doors"] = checked_doors(plan.get("doors", base.get("doors", [])), base.get("doors", []))
    found["people"] = [[number(x, "a standing spot", -BIGGEST), number(y, "a standing spot", -BIGGEST), *rest]
                       for x, y, *rest in plan.get("people", [])]
    ids = {row for tied in base.get("rows", {}).values() for row in tied}
    holds = [checked_hold(hold, ids) for hold in plan.get("holds", [])]
    holds = [{**hold, "row": neighbours_row(hold, holds)} for hold in holds]
    if holds or "holds" in base:
        found["holds"] = holds
    return found


def checked_hold(hold, ids):
    """One inside place's room as given: {place, row, x, y, w, d}, plus `name` once two scenes overlapped into one
    shared room and `things` once things stand in it (CONTEXT.md "shared room", "thing in a room"); each only when
    given, so a room he left alone stays equal to the one its draws were drawn on (`moved_draws`)."""
    place = checked_names([hold["place"]])[0]
    found = {"place": place, "row": checked_row(hold.get("row"), ids),
             **{key: number(hold[key], f"{place} {key}", -BIGGEST if key in "xy" else 0.5) for key in "xywd"}}
    name = str(hold.get("name") or "").strip()[:80]
    things = [checked_thing(thing, place) for thing in hold.get("things") or []]
    return {**found, **({"name": name} if name else {}), **({"things": things} if things else {})}


def checked_thing(thing, place):
    """A thing standing in `place`'s room as given: {name, x, y, w, d}, its corner in metres from the room's corner."""
    name = str((thing or {}).get("name") or "").strip()[:60]
    if not name:
        raise Refused(f"a thing in {place} has no name")
    return {"name": name, **{key: number(thing.get(key), f"{name} {key}", 0.0 if key in "xy" else 0.1)
                             for key in "xywd"}}


def sized_by_him(base, items):
    """The derived plan's gaps less the size gaps of the items he resized or removed (his size is its size)."""
    was = {item[0]: item[3:5] for item in base.get("items", [])}
    now = {item[0]: item[3:5] for item in items}
    return [gap for gap in base.get("gaps", [])
            if gap["kind"] != "size" or now.get(gap["item"]) == was.get(gap["item"])]


def checked_row(row, ids):
    """An inside place's holding row as given: one of the holder's inventory rows, or None (its own walls)."""
    if row is not None and row not in ids:
        raise Refused(f"{row!r} is no inventory row of this place")
    return row


def edited(store, place, plan, by, how="edited", calls=None, asked=None):
    """Keep his plan for `place` (checked against the derived one) as his own, and where the plan stage reads it;
    the record. `asked`: {words, at} of his request when an agent makes the edit he asked for in a session."""
    base = (made_plan(store, place) or {}).get("plan")
    if base is None:
        raise Refused(f"{place}'s scene inventory is not read from its locked concept: no plan yet")
    plan = checked_plan(plan, base)
    if "shapes" in base:  # a written plan: its free checks run again on his edit
        from score.review import plan_checks
        plan["gaps"] = [gap for gap in plan["gaps"] if gap["kind"] not in plan_checks.KINDS] + plan_checks.checked(
            plan, inventory_of(store, place), base.get("structure", []))
    record = kept_record(store, place, "edits", {
        "place": place, "plan": plan, "concept": pick_of(store, place), "by": by,
        "at": concepts.now(), "how": how, "calls": calls or [], **({"asked": asked} if asked else {})})
    if has_row(place):
        kept_for_stage(store, place, record["plan"])
    return record


def name_inside(store, place, names, by):
    """Keep the inside places he named on `place`'s concept page; the record."""
    return kept_record(store, place, "named", {"place": place, "names": checked_names(names), "by": by,
                                               "at": concepts.now()})


def has_row(place):
    """Whether `place` has a plan@ row: its plan in data/plans says where its doors lead (scene_record.written)."""
    path = DATA / "plans" / f"{place}.json"
    return path.is_file() and "leads" in json.loads(path.read_text())


def plan_sha(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


def kept_for_stage(store, place, plan):
    """The plan, the scene inventory it was made from and the picked concept both were made from where the plan
    stage reads them in place of data/plans, data/inventory and the plan's old concept picture (stages.creator_plan;
    the plan names that picture as its concept), each unless it stands there already."""
    pick = pick_of(store, place)
    plan = {**plan, "concept": {"pick": pick, "picture": f"{{home}}/design/concepts/{place}.png",
                                "read": "its scene inventory, read from this picked concept (score/review/reading.py)"}}
    for path, found in ((KEPT / f"{place}.json", json.dumps(plan, indent=1).encode()),
                        (KEPT_INVENTORY / f"{place}.json", json.dumps(inventory_of(store, place), indent=1).encode()),
                        (KEPT_CONCEPT / f"{place}.png", store.objects.read_bytes(f"blobs/{pick}"))):
        if not path.is_file() or path.read_bytes() != found:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(found)


def design_done(store, place):
    """Whether the place's design is done in the app: its concept locked, its scene inventory read from it and its
    plan written (or edited by him), not only derived from that inventory (`current`: None before the reading)."""
    shown = current(store, place)
    return shown is not None and shown["how"] != "derived"


def keep(store, places):
    """Every place's plan shown where the plan stage reads it, a place with none (its pick unlocked, its inventory
    not read from it) taken out there, so the stage reads data/plans again; ([kept], [changed]): the places whose
    plan the plan stage reads now, and those whose file was written or taken out."""
    kept, changed = [], []
    for place in places:
        path = KEPT / f"{place}.json"
        before = path.read_text() if path.is_file() else None
        # a scene he added in the app has no plan in data/plans: once its design is done, its kept plan is its plan
        # row's (stages.plan_written)
        filed = (DATA / "plans" / f"{place}.json").is_file()
        shown = current(store, place) if has_row(place) or (not filed and design_done(store, place)) else None
        if shown is not None:
            kept_for_stage(store, place, shown["plan"])
            kept.append(place)
        elif path.is_file():
            path.unlink()
            (KEPT_INVENTORY / f"{place}.json").unlink(missing_ok=True)
            (KEPT_CONCEPT / f"{place}.png").unlink(missing_ok=True)
        if (path.read_text() if path.is_file() else None) != before:
            changed.append(place)
    return kept, changed


def made_again(places, start=None):
    """The plan row made again for `places` (free, local, its own detached run: `score run`); its result line."""
    import subprocess
    words = [sys.executable, "-m", "score", "run", "world1", *[part for place in places for part in ("--place", place)],
             "--stage", "plan", "--detach"]
    done = (start or subprocess.run)(words, capture_output=True, text=True, cwd=str(concepts.REPO))
    said = (done.stderr if done.returncode else done.stdout).strip().splitlines()  # a refusal comes on stderr
    return (said or ["no output"])[-1]


# --- the drawing ------------------------------------------------------------------------------------------------

def drawn(plan, highlight=None, labelled=()):
    """A top-down drawing (PIL) of `plan`: its outline, doors with where each leads, items as labelled boxes, keep-
    clear zones, standing spots and inside places (`highlight` the one filled), plus (label, mark) boxes."""
    from PIL import Image, ImageDraw
    wide, deep = max(plan["w"], 0.5), max(plan["d"], 0.5)
    scale = (PIXELS - 80) / max(wide, deep)
    picture = Image.new("RGB", (int(wide * scale) + 80, int(deep * scale) + 80), (250, 250, 247))
    pen = ImageDraw.Draw(picture)
    at = lambda x, y: (40 + x * scale, 40 + y * scale)  # noqa: E731
    pen.rectangle([*at(0, 0), *at(wide, deep)], outline=(30, 30, 30), width=4)
    for hold in plan.get("holds", []):
        fill = (255, 214, 102) if hold["place"] == highlight else (232, 236, 242)
        pen.rectangle([*at(hold["x"], hold["y"]), *at(hold["x"] + hold["w"], hold["y"] + hold["d"])], fill=fill,
                      outline=(60, 60, 60), width=3)
        pen.text(at(hold["x"] + 0.2, hold["y"] + 0.2), hold["place"], fill=(20, 20, 20), font_size=22)
    for name, x, y, item_wide, item_deep, _, kind in plan.get("items", []):
        if name == WALLS_ITEM:
            continue
        colour = (200, 70, 70) if kind == "zone" else (40, 90, 160)
        pen.rectangle([*at(x, y), *at(x + item_wide, y + item_deep)], outline=colour, width=2)
        pen.text(at(x + 0.05, y + 0.05), name.title(), fill=colour, font_size=14)
    for door in plan.get("doors", []):
        if door[0] in SIDES:
            middle = {"N": (door[1], 0), "S": (door[1], deep), "W": (0, door[1]), "E": (wide, door[1])}[door[0]]
            half = float(door[2]) / 2
            ends = ((middle[0] - half, middle[1]), (middle[0] + half, middle[1])) if door[0] in "NS" else \
                ((middle[0], middle[1] - half), (middle[0], middle[1] + half))
            pen.line([*at(*ends[0]), *at(*ends[1])], fill=(0, 150, 80), width=10)
            lead = plan.get("leads", {}).get(door[0], {})
            pen.text(at(*middle), f"to {lead.get('to', '?')}", fill=(0, 120, 60), font_size=16)
    for spot in plan.get("people", []):
        x, y = at(spot[0], spot[1])
        pen.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(120, 60, 160))
    width, height = picture.size
    for label, mark in labelled:
        box = (mark["x"] * width, mark["y"] * height, (mark["x"] + mark["w"]) * width, (mark["y"] + mark["h"]) * height)
        pen.rectangle(box, outline=(255, 0, 0), width=concepts.MARK_WIDTH)
        pen.text((box[0] + 8, box[1] + 8), label, fill=(255, 0, 0), font_size=24)
    pen.text((10, 8), "N", fill=(30, 30, 30), font_size=20)
    return picture


def png_of(picture):
    buffer = io.BytesIO()
    picture.save(buffer, "PNG")
    return buffer.getvalue()


def shape_sent(store, place):
    """[(what it is, its path)] for `place`'s first draw (owner, 2026-10-21): its shape on the layer above's plan,
    the place filled among the places beside it, the doors marked; [] while that plan does not lay it out."""
    held = holder_of(store, place)
    if held is None:
        return []
    holder_plan = current(store, held["holder"])["plan"]
    path = store.cache / AREA / "shapes" / f"{place}-{plan_sha(holder_plan)[:12]}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png_of(drawn(holder_plan, highlight=place)))
    holder = held["holder"]
    return [(f"its shape on the {holder}'s plan (top down, north up, it is the yellow box): match its "
             "outline and doors", path)]


# --- notes through Gemini -------------------------------------------------------------------------------------

def revise_euros(per_unit=DATA / "costs/per-unit.json"):
    """The euros of one Correct with notes: the measured Gemini 3.1 Pro answer on pictures; None while unmeasured."""
    return concepts.draw_euros(per_unit, (concepts.MEASURED_ASK,))


def yes_key(place, at):
    return f"plan-{place}-{stamp_key(at)}"


def hand_edits(base, plan):
    """[words] of what his plan changes from the plan made without him: inside places and items (by name) removed,
    added, moved or resized, in metres."""
    said = []
    for kind, named in (("scene", lambda found: {hold["place"]: [hold["x"], hold["y"], hold["w"], hold["d"]]
                                                for hold in found.get("holds", [])}),
                        ("item", lambda found: {item[0]: list(item[1:5]) for item in found.get("items", [])})):
        was, now = named(base), named(plan)
        said += [f"removed the {kind} {name}" for name in was if name not in now]
        for name, (x, y, wide, deep) in now.items():
            if name not in was:
                said.append(f"added the {kind} {name}, {wide} x {deep} m at {x}, {y} m")
            elif [round(value, 2) for value in was[name]] != [round(value, 2) for value in (x, y, wide, deep)]:
                said.append(f"{kind} {name} now {wide} x {deep} m at {x}, {y} m (was {was[name][2]} x {was[name][3]} m "
                            f"at {was[name][0]}, {was[name][1]} m)")
    return said + room_edits(base, plan)


def room_edits(base, plan):
    """[words] of the shared rooms he made and the things he put in a room, against the plan made without him."""
    was = {hold["place"]: hold for hold in base.get("holds", [])}
    said = []
    for hold in plan.get("holds", []):
        before = was.get(hold["place"], {})
        if hold.get("name") and hold["name"] != before.get("name"):
            said.append(f"made the scene {hold['place']} one shared room called {hold['name']}")
        said += [f"put {thing['name']} in the scene {hold['place']}, {thing['w']} x {thing['d']} m at {thing['x']}, "
                 f"{thing['y']} m from its corner" for thing in hold.get("things", [])
                 if thing not in before.get("things", [])]
    return said


def note_of(store, place, request):
    """The note a Correct with notes sends: his typed note, else, with no mark either, his hand edits of the plan
    shown in words (owner, 2026-10-21: Correct with no note sends his edits); Refused when there is neither."""
    note = str(request.get("note") or "").strip()
    if note or request.get("marks") or request.get("context_marks"):
        return note
    shown, made_one = current(store, place), made_plan(store, place)
    edits = hand_edits(made_one["plan"], shown["plan"]) if shown and made_one and shown["how"] != made_one["how"] else []
    if not edits:
        raise Refused("no note to correct the plan by: type a note, mark an area or change the plan")
    return f"I changed the plan by hand: {'; '.join(edits)}. Keep these changes and fit the rest of the plan to them."


def plan_question(plan, marks, context, note):
    """What Gemini is asked: the plan as JSON corrected by his notes, answered as JSON of the same keys."""
    edited_keys = {key: plan.get(key) for key in ("w", "d", "items", "doors", "people", "holds") if key in plan}
    return ("Image 1 is a place's plan drawn top down (north up, metres; blue boxes its items, red its keep-clear "
            "zones, green its doors, purple dots its standing spots, grey its inside places) with numbered red boxes "
            "marking areas to change; image 2 is its concept painting, its boxes labelled P. Correct the plan's JSON "
            "below so it makes exactly the changes the creator's notes ask and keeps everything else: move, resize, "
            "add or drop items (keep each item's name), move doors along their walls, move standing spots, lay out "
            "inside places. Answer with the corrected JSON only, the same keys.\n\n"
            f"The creator's notes: {concepts.notes_words(marks, context, note)}\n\nThe plan:\n"
            f"{json.dumps(edited_keys)}")


def answered_plan(text):
    """The JSON object in Gemini's answer (its first { to its last }); Refused when there is none."""
    start, end = text.find("{"), text.rfind("}")
    try:
        return json.loads(text[start:end + 1])
    except ValueError as broken:
        raise Refused("the model answered with no plan") from broken


def revised(store, place, request, by, reviser=concepts.revise):
    """His Correct with notes inside the owner's yes (SCORE_SPEND_TICKET names it; compute.require_cleared refuses
    otherwise): Gemini (`reviser(question, pictures)`) corrects the plan shown by his marks on the plan and the
    concept and his note; the corrected plan is kept as his own edit (how: revised); the record."""
    from PIL import Image
    from score.adapters import compute
    yes = compute.require_cleared("a plan correction", store)
    shown = current(store, place)
    if shown is None:
        raise Refused(f"{place} has no plan yet")
    marks = concepts.checked_marks(request.get("marks"))
    context = concepts.checked_marks(request.get("context_marks"), on={place: True})
    if not marks and not context and not str(request.get("note", "")).strip():
        raise Refused("no note to correct the plan by")
    labelled = concepts.numbered(marks, context)
    pictures = [drawn(shown["plan"], labelled=[(label, mark) for label, mark in labelled if "on" not in mark]),
                concepts.boxed(Image.open(io.BytesIO(store.objects.read_bytes(f"blobs/{pick_of(store, place)}"))),
                               [(label, mark) for label, mark in labelled if "on" in mark])]
    question = plan_question(shown["plan"], marks, context, str(request.get("note", "")))
    answer = reviser(question, pictures)
    corrected = {**shown["plan"], **answered_plan(answer)}
    calls = [{"model": concepts.PROMPT_MODEL, "asked": question, "answered": answer, "euros": yes["euros"],
              "yes": yes["key"]}]
    return edited(store, place, corrected, by, how="revised", calls=calls)


def main(argv):
    """`<place> <request.json> <by>`: one Correct with notes inside the owner's yes (its ticket in the environment);
    its record as the last line, or `refused: <why>` on stderr. `keep`: every place's plan where the plan stage
    reads it; one line."""
    import os
    from score.adapters.compute import STORE, Refused as NotCleared
    from score.store import Store
    store = Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default()
    if argv == ["keep"]:
        from score.review import plan_writing
        # every scene of the tree, a parent scene with no plan in the data among them (the Moon base): its kept plan
        # lays out its child scenes for the scene tree (stages/assembly/scene_tree.py)
        laid = tree(store)["within"]
        places = sorted({*(path.stem for path in (DATA / "plans").glob("*.json")), *laid, *laid.values()})
        # a locked, read place with no plan written from its reading (a reading before today's METHOD, a run cut off)
        # gets it on its own under the standing allowance; kept on a later pass
        owed = plan_writing.owed(store, places) if plan_writing.AUTOMATIC else []
        writing = f"; plans of {', '.join(owed)} being written: {plan_writing.started(store, owed)}" if owed else ""
        kept, changed = keep(store, places)
        # changed, or not made yet (a run refused while another held the store is asked again next pass)
        again = [place for place in sorted({*changed, *kept}) if place in changed or not made(store, place)]
        print(f"plans for the plan stage: {len(kept)} kept, {len(changed)} changed"
              + (f"; plan rows of {len(again)} made again: {made_again(again)}" if again else "") + writing)
        return 0
    place, request, by = argv
    try:
        record = revised(store, place, json.loads(pathlib.Path(request).read_text()), by)
    except (Refused, concepts.Refused, NotCleared) as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 1
    print(json.dumps({key: record[key] for key in ("place", "at", "by", "how")}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
