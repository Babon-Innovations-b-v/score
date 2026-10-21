"""Plan writing (CONTEXT.md "plan"; the owner, 2026-10-21): Gemini 3.1 Pro writes a place's dimensioned plan in
metres, element by element, the way the hand-written plans of data/plans were made, from its picked concept, its
scene inventory (rows with metres; their SAM 3 boxes only as a hint of order, left to right and far to near, never
projected), the layer above's plan (its outline, where this place sits there, its doors and neighbours) and its inside
places. One direct call a place; then the free checks (score/review/plan_checks.py), each failure a named gap of the
plan, never guessed past.

The plan keeps the stage table's schema (data/plans: w, d, doors, leads, items [name, x, y, wide, deep, facing, kind],
rows, people, holds) and adds, in plan metres (x east, y south from the outline's north-west corner, heights above
the place's +0.00):

    outline   [[x, y], ...]                       the place's footprint
    walls     [{from, to, thick, tall} | {arc {centre, radius, start, end}, thick, tall}]
    openings  [{kind: door|window|opening|gate, at, wide, angle, swing: left|right|double|slide|none, sill, head, to}]
    levels    [{name, height, points}]            floor areas at their heights
    stairs    [{kind: stair|ramp, points, from, to, angle (the way up), steps}]
    roofs     [{kind: flat|dome|pitched|vault|shed, points, eave, top}]
    terrain   {spots [[x, y, height]], contours [{height, points}]}
    shapes    {item name: {shape: rect|circle|polygon, points [[u, v]] in 0..1 of its box, tall, base}}
    section   {y}                                 where the section view cuts, west to east

Runs on its own after a place's scene inventory is read (AUTOMATIC: the owner's standing allowance of 2026-10-21, root
CLAUDE.md, compute.reading_clearance's PLAN_WRITING node), else on his Make plan click, his spend yes for that one
call (web.plan_write). Each writing kept in the store, written once:

    plan-writings/<place>/<time>.json  {place, concept, reading, at, by, method, plan, euros, seconds, clearance}
                                       (or `refused`: why, with its call's euros)

    python -m score.review.plan_writing <place> [<place> ...] [--by <name>]
"""
import argparse
import collections
import concurrent.futures
import contextlib
import json
import math
import os
import sys
import time
import urllib.error

from score.review import concepts, plan_checks, plans, reading
from score.store import Store, locked, stamp_key

AREA = "plan-writings"
MODEL = concepts.PROMPT_MODEL
CALLER = "plan-writing"
TIMEOUT = 600
METHOD = 1
# The owner's standing allowance (2026-10-21): a plan is written on its own once its inventory is read. False: only on
# his Make plan click, his spend yes for that one call.
AUTOMATIC = True
ESTIMATE = 0.05  # euros of one writing until one is measured (google_spend's Gemini 3.1 Pro estimate)
SWINGS = ("left", "right", "double", "slide", "none")
OPENINGS = ("door", "window", "opening", "gate")
ROOFS = ("flat", "dome", "pitched", "vault", "shed")
SHAPES = ("rect", "circle", "polygon")
FACINGS = ("N", "E", "S", "W")
ASKED = """You are an architect drawing the dimensioned floor plan of one place of a game environment, in metres,
element by element, from its concept painting (the picture) and the facts below. The picture is a three-quarter
view: read from it what stands where and how big, never copy its perspective. Plan metres: x east, y south, from the
north-west corner of the place's outline box ({wide:g} m wide, {deep:g} m deep); heights in metres above the place's
own floor or ground level +0.00.

The facts (JSON):
{facts}

Write the plan as one JSON object with these keys:
- "outline": the place's footprint, [[x, y], ...] clockwise, inside the outline box (a rectangle is its 4 corners; a
  round or curved place its curve in enough points).
- "walls": every wall, straight {{"from": [x, y], "to": [x, y], "thick": m, "tall": m}} or curved {{"arc":
  {{"centre": [x, y], "radius": m, "start": degrees, "end": degrees}}, "thick": m, "tall": m}} (degrees from east,
  clockwise, as y runs south); outer walls on the outline, inner walls where the picture shows them. An outdoor place
  has none unless the picture shows them.
- "openings": every door, window, gate or open doorway, {{"kind": "door"|"window"|"gate"|"opening", "at": [x, y] (its
  middle, on its wall), "wide": m, "angle": the wall's direction in degrees, "swing": "left"|"right"|"double"|"slide"|
  "none", "sill": m, "head": m, "to": the place it leads to or null}}; the doors listed in the facts are fixed: list
  each at its place with its swing.
- "levels": every floor or ground area at its own height, {{"name": words, "height": m, "points": [[x, y], ...]}}
  (the main floor +0.00; a raised deck, a sunken pit, a platform, a balcony; outside, the ground's own areas: a
  plaza, a road, a quay, the sea or a pool at its water line, sand, grass).
- "stairs": every stair or ramp, {{"kind": "stair"|"ramp", "points": its footprint, "from": m, "to": m, "angle": the
  direction one walks up in degrees, "steps": a count}}.
- "roofs": every roof, {{"kind": "flat"|"dome"|"pitched"|"vault"|"shed", "points": its footprint, "eave": m, "top": m}}.
- "terrain": for ground outside, {{"spots": [[x, y, height], ...], "contours": [{{"height": m, "points": [[x, y],
  ...]}}]}}: spot heights where the ground rises or falls and contour lines at an even step; {{}} for a place indoors.
- "items": every instance of every row of the facts' rows that stands on the floor or the ground (as many as the row
  counts), and the things on walls, ceilings or other rows worth placing, each {{"row": the row's id, "x": m, "y": m
  (its middle), "wide": m (along x), "deep": m (along y), "shape": "rect"|"circle"|"polygon", "points": [[x, y], ...]
  (a polygon's corners in plan metres, for a thing turned off the grid or of its own outline), "facing": "N"|"E"|"S"|
  "W"|null (the way its front faces), "tall": m, "base": m (the height it stands at: 0 on the floor, its parent's top
  on another row)}}. Size each by the row's metres, turned as it stands. Never two things on the same floor area
  unless one stands on the other; keep a way on foot from every door to every other and to the standing spots.
- "structure": the ids of the rows that are the place's own shell, walls, floors, roof, ground, terrain areas, water,
  sea, plaza or sky (drawn as walls, levels, roofs and terrain above, never as items).
- "beyond": the ids of the rows the picture shows beyond this place (through a window or a door, past its edge, far
  off): never placed here, they belong to the place they stand in.
- "zones": areas to keep clear beyond the doors' (a vehicle's keep-out, a landing pad), {{"name": words, "x": m, "y":
  m, "wide": m, "deep": m}} (x, y their north-west corner).
- "places": each inside place of the facts, laid out so they tile without overlap inside the outline, each inside
  the building or part of this place that holds it, {{"place": its name, "in": the id of the row holding it (a
  building, a ship, a hall) or null for this place's own floor, "x": m, "y": m, "w": m, "d": m}} (x, y its north-west
  corner).
- "people": two to four standing spots [[x, y], ...] on free floor where a person would stand to look round.
- "section": {{"y": m}}, where a west-to-east cut through the place shows the most of its heights.
No text besides the JSON."""


class Refused(ValueError):
    pass


# --- what Gemini is told -----------------------------------------------------------------------------------------

def order_hint(row, picture):
    """Each instance of a row where SAM 3 found it on the picture, [across, down] in 0..1 (left to right, far to near),
    sorted left to right: a hint of order, never a plan position; [] when none was found."""
    if not picture:
        return []
    boxes = row.get("boxes") or ([row["box"]] if row.get("box") else [])
    return sorted([round((box[0] + box[2]) / 2 / picture[0], 2), round(box[3] / picture[1], 2)] for box in boxes)


def rows_told(inventory):
    """The inventory's rows as Gemini is told them: id, name, count, metres, anchor, where, terrain, its order hint."""
    picture = inventory.get("picture")
    return [{"id": row["id"], "name": row.get("name") or row["id"], "count": int(row.get("count", 1) or 1),
             "metres [wide, deep, tall]": row.get("size") if isinstance(row.get("size"), list) else None,
             "size in words": row.get("size_words") or (row.get("size") if isinstance(row.get("size"), str) else None),
             "anchor": row.get("anchor") or "floor", "where": row.get("where"), "terrain": row.get("terrain", False),
             "seen at": order_hint(row, picture)} for row in inventory.get("rows", [])]


def within_told(store, place):
    """Where the place sits on the layer above's plan: the holder, its outline, this place's box, the places beside
    it there; None for an outside place."""
    held = plans.holder_of(store, place)
    if held is None:
        return None
    above = plans.current(store, held["holder"])["plan"]
    return {"holder": held["holder"], "holder outline [wide, deep]": [above["w"], above["d"]],
            "stands in the holder's row": held["row"], "this place's box there [x, y, wide, deep]": held["outline"],
            "beside it there": [{"place": hold["place"], "box [x, y, wide, deep]": [hold["x"], hold["y"], hold["w"],
                                                                                   hold["d"]]}
                                for hold in above.get("holds", []) if hold["place"] != place]}


def door_told(door, leads):
    """A fixed door as told: a wall door [side, along, wide, what, ...], or a faceted room's door by bearing or a
    tube's end [bearing or end, wide, what]."""
    if door[0] in plans.SIDES:
        side = f"{door[0]}@{door[4]:g}" if len(door) > 4 and f"{door[0]}@{door[4]:g}" in leads else door[0]
        return {"wall": door[0], "along it": door[1], "wide": door[2], "what": door[3],
                "leads to": (leads.get(side) or {}).get("to")}
    return {"bearing or end": door[0], "wide": door[1], "what": door[2],
            "leads to": (leads.get(str(door[0])) or {}).get("to")}


def facts_of(store, place, skeleton, inventory):
    """Everything the writing is told about the place (ASKED's facts)."""
    leads = skeleton.get("leads", {})
    return {"place": place, "name": concepts.name_of(place), "title": skeleton.get("title"),
            "shell": skeleton.get("shell"), "heights in words": skeleton.get("height") or None,
            "outline box [wide, deep]": [skeleton["w"], skeleton["d"]], "within": within_told(store, place),
            "fixed doors": [door_told(door, leads) for door in skeleton.get("doors", [])],
            "inside places": [{"place": hold["place"], "about [wide, deep]": [hold["w"], hold["d"]]}
                              for hold in skeleton.get("holds", [])],
            "rows": rows_told(inventory)}


def asked_body(concept, skeleton, facts):
    """The Gemini request: ASKED with the facts, and the picked concept."""
    from PIL import Image
    pro, _, _ = concepts.tools()
    picture = Image.open(concept)
    return {"contents": [{"role": "user", "parts": [
        {"text": ASKED.format(wide=skeleton["w"], deep=skeleton["d"], facts=json.dumps(facts, indent=1))},
        pro.part(picture, max(picture.size))]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"}}


def asked(body):
    """One Gemini call (google_spend, on its ledger, never cached); (response, seconds)."""
    _, google_spend, secret_store = concepts.tools()
    began = time.time()
    try:
        response = google_spend.generate(MODEL, body, secret_store.secret("gemini-api-key"), TIMEOUT, caller=CALLER)
    except urllib.error.HTTPError as error:
        raise concepts.Refused(f"the model refused ({error.code})") from error
    return response, round(time.time() - began, 1)


# --- the answer made into a plan ---------------------------------------------------------------------------------

def number(value, default=None):
    """A finite number as a float rounded to the millimetre, else `default`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return default
    return round(float(value), 3)


def point(value):
    """[x, y] of two numbers, else None."""
    if isinstance(value, list) and len(value) == 2 and all(number(part) is not None for part in value):
        return [number(part) for part in value]
    return None


def points(value, least=3):
    """[[x, y], ...] of at least `least` points, else None."""
    found = [point(part) for part in value] if isinstance(value, list) else []
    return found if len(found) >= least and all(found) else None


def wall_of(wall):
    """A wall as answered, checked; None when off the schema."""
    if not isinstance(wall, dict):
        return None
    sizes = {"thick": number(wall.get("thick"), 0.2), "tall": number(wall.get("tall"))}
    arc = wall.get("arc")
    if isinstance(arc, dict) and point(arc.get("centre")) and number(arc.get("radius")):
        return {"arc": {"centre": point(arc["centre"]), "radius": number(arc["radius"]),
                        "start": number(arc.get("start"), 0.0), "end": number(arc.get("end"), 360.0)}, **sizes}
    if point(wall.get("from")) and point(wall.get("to")):
        return {"from": point(wall["from"]), "to": point(wall["to"]), **sizes}
    return None


def opening_of(opening):
    if not isinstance(opening, dict) or opening.get("kind") not in OPENINGS or not point(opening.get("at")) \
            or not number(opening.get("wide")):
        return None
    return {"kind": opening["kind"], "at": point(opening["at"]), "wide": number(opening["wide"]),
            "angle": number(opening.get("angle"), 0.0),
            "swing": opening.get("swing") if opening.get("swing") in SWINGS else "none",
            "sill": number(opening.get("sill"), 0.0), "head": number(opening.get("head")),
            "to": str(opening["to"]) if opening.get("to") else None}


def level_of(level):
    if not isinstance(level, dict) or number(level.get("height")) is None or not points(level.get("points")):
        return None
    return {"name": str(level.get("name") or "")[:60], "height": number(level["height"]),
            "points": points(level["points"])}


def stair_of(stair):
    if not isinstance(stair, dict) or not points(stair.get("points")) or number(stair.get("from")) is None \
            or number(stair.get("to")) is None:
        return None
    return {"kind": "ramp" if stair.get("kind") == "ramp" else "stair", "points": points(stair["points"]),
            "from": number(stair["from"]), "to": number(stair["to"]), "angle": number(stair.get("angle"), 0.0),
            "steps": int(number(stair.get("steps"), 0) or 0)}


def roof_of(roof):
    if not isinstance(roof, dict) or not points(roof.get("points")) or number(roof.get("eave")) is None:
        return None
    return {"kind": roof.get("kind") if roof.get("kind") in ROOFS else "flat", "points": points(roof["points"]),
            "eave": number(roof["eave"]), "top": number(roof.get("top"), number(roof["eave"]))}


def terrain_of(terrain):
    """Spot heights and contour lines as answered, each checked; {} with none."""
    terrain = terrain if isinstance(terrain, dict) else {}
    spots = [[number(part) for part in spot] for spot in terrain.get("spots") or []
             if isinstance(spot, list) and len(spot) == 3 and all(number(part) is not None for part in spot)]
    contours = [{"height": number(line["height"]), "points": points(line.get("points"), 2)}
                for line in terrain.get("contours") or []
                if isinstance(line, dict) and number(line.get("height")) is not None and points(line.get("points"), 2)]
    return {key: found for key, found in (("spots", spots), ("contours", contours)) if found}


def listed(answer, key, check):
    """The answer's list under `key`, each entry checked (`check`), the ones off the schema dropped; (found, dropped)."""
    found = [check(entry) for entry in answer.get(key) or []] if isinstance(answer.get(key), list) else []
    return [entry for entry in found if entry], sum(1 for entry in found if not entry)


def footprint_of(item):
    """(x, y, wide, deep, shape) of an answered item: its box (north-west corner, size) and its shape in 0..1 of the
    box (`shapes`); None when it gives no size."""
    corners = points(item.get("points")) if item.get("shape") == "polygon" else None
    if corners:
        xs, ys = [corner[0] for corner in corners], [corner[1] for corner in corners]
        x, y, wide, deep = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
        if wide <= 0 or deep <= 0:
            return None
        shape = {"shape": "polygon", "points": [[round((cx - x) / wide, 4), round((cy - y) / deep, 4)]
                                                for cx, cy in corners]}
        return x, y, wide, deep, shape
    middle, wide, deep = point([item.get("x"), item.get("y")]), number(item.get("wide")), number(item.get("deep"))
    if not middle or not wide or not deep or wide <= 0 or deep <= 0:
        return None
    return middle[0] - wide / 2, middle[1] - deep / 2, wide, deep, {"shape": "circle" if item.get("shape") == "circle"
                                                                    else "rect"}


def structure_of(answer, inventory):
    """The ids of the rows that are the place's own shell or ground: those the answer names so, and every row that is
    the place itself (plans.whole: its ground, water, sky), never a sized item."""
    said = answer.get("structure") if isinstance(answer.get("structure"), list) else []
    return [row["id"] for row in inventory.get("rows", [])
            if row["id"] in said or plans.whole(row, inventory.get("picture"))]


def items_of(answer, inventory, wide, deep):
    """(items, rows, shapes, dropped) of the answered items: each a plan item named by its row and number, tied to its
    row and the rows riding on it that are not placed themselves; one walls-and-ceiling item holding the rows placed
    nowhere that stand on no floor, and the structure rows; `dropped` the answered items off the schema or of no row
    (kept on the plan, no gap of his: the count check names a row left short)."""
    by_id = {row["id"]: row for row in inventory.get("rows", [])}
    structure = structure_of(answer, inventory)
    items, rows, shapes, dropped, numbered = [], {}, {}, [], collections.Counter()
    for item in answer.get("items") or []:
        row = item.get("row") if isinstance(item, dict) else None
        found = footprint_of(item) if row in by_id and row not in structure else None
        if found is None:
            dropped.append({"item": str(row), "why": "no such row" if row not in by_id else
                            "a structure row" if row in structure else "no size"})
            continue
        numbered[row] += 1
        name = f"{row.replace('_', ' ').upper()} {numbered[row]}"
        x, y, wide, deep, shape = found
        facing = item.get("facing") if item.get("facing") in FACINGS else None
        items.append([name, round(x, 3), round(y, 3), round(wide, 3), round(deep, 3), facing, "item"])
        rows[name] = [row]
        size = by_id[row].get("size")
        shapes[name] = {**shape, "tall": number(item.get("tall"), number(size[2]) if isinstance(size, list) else None),
                        "base": number(item.get("base"), 0.0)}
    placed = set(numbered)
    for row_id, row in by_id.items():
        parent = plans.anchor_of(row)
        if row_id not in placed and parent in placed:
            rows[f"{parent.replace('_', ' ').upper()} 1"].append(row_id)
    on_walls = [row_id for row_id, row in by_id.items() if row_id not in placed and (
        row_id in structure or plans.anchor_of(row) not in ("floor", "ground", *placed))]
    if on_walls:
        items.append([plans.WALLS_ITEM, 0.0, 0.0, wide, deep, None, "item"])
        rows[plans.WALLS_ITEM] = on_walls
    return items, rows, shapes, dropped


def zones_of(answer):
    """The answered keep-clear zones as plan items of kind zone (rows: none)."""
    found = []
    for zone in answer.get("zones") or []:
        if isinstance(zone, dict) and point([zone.get("x"), zone.get("y")]) and number(zone.get("wide")) \
                and number(zone.get("deep")):
            found.append([f"KEEP CLEAR {str(zone.get('name') or len(found) + 1).upper()}"[:80], number(zone["x"]),
                          number(zone["y"]), number(zone["wide"]), number(zone["deep"]), None, "zone"])
    return found


def holds_of(answer, skeleton, ids):
    """The inside places as answered, each the skeleton's (its name) at the answered box, in the row the answer says
    holds it (`ids`: the inventory's; null: this place's own floor), else the skeleton's; (holds, gaps): one not laid
    keeps the skeleton's box and is a gap."""
    said = {entry.get("place"): entry for entry in answer.get("places") or [] if isinstance(entry, dict)}
    holds, gaps = [], []
    for hold in skeleton.get("holds", []):
        entry = said.get(hold["place"], {})
        box = [number(entry.get(key)) for key in ("x", "y", "w", "d")]
        if None in box or box[2] <= 0 or box[3] <= 0:
            gaps.append({"kind": "place", "item": hold["place"], "row": hold.get("row"),
                         "at": [round(hold["x"] + hold["w"] / 2, 2), round(hold["y"] + hold["d"] / 2, 2)],
                         "words": f"{hold['place'].replace('_', ' ')} was not laid out: it stands where it was"})
            holds.append(hold)
            continue
        row = entry.get("in") if entry.get("in") in ids else (None if "in" in entry else hold.get("row"))
        holds.append({**hold, "row": row, **dict(zip(("x", "y", "w", "d"), box))})
    return holds, gaps


def plan_from(answer, skeleton, inventory):
    """The written plan: the skeleton (its outline box, doors, leads, lamps, elements, the stage table's keys) with the
    answer's items, zones, inside places, standing spots and architecture, and every gap: the skeleton's that still
    hold, what the answer left off the schema, and the free checks' (plan_checks.checked)."""
    if not isinstance(answer, dict):
        raise Refused("the answer is no JSON object")
    plan = dict(skeleton)
    items, rows, shapes, dropped = items_of(answer, inventory, skeleton["w"], skeleton["d"])
    plan["items"] = items + plans.keep_clear(skeleton) + zones_of(answer)
    plan["rows"] = {**rows, **{item[0]: [] for item in plan["items"] if item[6] == "zone"}}
    plan["shapes"] = shapes
    plan["holds"], hold_gaps = holds_of(answer, skeleton, {row["id"] for row in inventory.get("rows", [])})
    if not plan["holds"]:
        plan.pop("holds")
    spots = points(answer.get("people"), 1)
    plan["people"] = spots or skeleton.get("people", [])
    outline = points(answer.get("outline"))
    plan["outline"] = outline or [[0.0, 0.0], [skeleton["w"], 0.0], [skeleton["w"], skeleton["d"]],
                                  [0.0, skeleton["d"]]]
    for key, check in (("walls", wall_of), ("openings", opening_of), ("levels", level_of), ("stairs", stair_of),
                       ("roofs", roof_of)):
        plan[key], off = listed(answer, key, check)
        dropped += [{"item": key, "why": f"{off} off the schema"}] if off else []
    # the skeleton's lamps, beams and leaves on rows this concept lacks are left out of it already: no gap of his
    plan["dropped"] = dropped + [{"item": gap["item"], "why": gap["words"]} for gap in skeleton.get("gaps", [])
                                 if gap["kind"] != "size"]
    plan["terrain"] = terrain_of(answer.get("terrain"))
    section = number((answer.get("section") or {}).get("y")) if isinstance(answer.get("section"), dict) else None
    plan["section"] = {"y": section if section is not None else round(skeleton["d"] / 2, 3)}
    plan["structure"] = structure_of(answer, inventory)
    said_beyond = answer.get("beyond") if isinstance(answer.get("beyond"), list) else []
    plan["beyond"] = [row["id"] for row in inventory.get("rows", []) if row["id"] in said_beyond]
    plan["gaps"] = hold_gaps + plan_checks.checked(plan, inventory, plan["structure"])
    return plan


# --- the writings kept ---------------------------------------------------------------------------------------------

def writings(store, place):
    """The place's writings, oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{place}/"))]


def reading_at(store, place):
    """When the reading the place's plan is written from was made (its scene inventory), None with none."""
    found = reading.reading_of(store, place)
    return found and found["at"]


def written_of(store, place):
    """The newest writing of the place's plan made by today's METHOD from its picked concept and the reading of it in
    force, or None (none, or only refused ones: those are written again)."""
    sha, read_at = concepts.picked(store, place), reading_at(store, place)
    return next((found for found in reversed(writings(store, place))
                 if sha and found["concept"] == sha and found.get("reading") == read_at
                 and found.get("method") == METHOD and not found.get("refused")), None)


def to_write(store, places):
    """The places of `places` whose scene inventory counts and whose plan is not written from it yet."""
    return [place for place in places if plans.counts(store, place) and not written_of(store, place)]


def spent(store, places):
    """The euros every writing of `places` cost, in sum (the cockpit's running total beside the readings')."""
    return round(sum(found["euros"] for place in places for found in writings(store, place)), 4)


def price(store=None):
    """The euros one writing is priced at: the dearest measured writing of any place, rounded up to the cent, else
    ESTIMATE."""
    measured = [store.read(key)["euros"] for key in store.objects.keys(f"{AREA}/")] if store else []
    return math.ceil(max(measured) * 100) / 100 if measured else ESTIMATE


def call_euros(response):
    """What one answered call cost, as google_spend wrote it on its ledger."""
    return reading.call_euros(response)


def layered(store, places):
    """`places` in layers: a place after the place holding it, so an inside place is written on its holder's
    written plan."""
    within, layers, left = plans.tree(store)["within"], [], list(places)
    while left:
        layer = [place for place in left if within.get(place) not in left] or left
        layers.append(layer)
        left = [place for place in left if place not in layer]
    return layers


def written_one(store, place, by, folder, ask):
    """Write one place's plan (`ask(body)` the call); its record, kept."""
    skeleton = plans.derived(store, place)
    inventory = plans.inventory_of(store, place)
    sha = concepts.picked(store, place)
    concept = reading.picture_path(store, sha, folder)
    body = asked_body(concept, skeleton, facts_of(store, place, skeleton, inventory))
    (folder / f"{place}-asked.json").write_text(json.dumps(body["contents"][0]["parts"][0], indent=1))
    response, seconds = ask(body)
    (folder / f"{place}-answer.json").write_text(json.dumps(response, indent=1))
    record = {"place": place, "concept": sha, "reading": reading_at(store, place), "at": concepts.now(), "by": by,
              "method": METHOD, "euros": call_euros(response), "seconds": seconds}
    try:
        record["plan"] = plan_from(json.loads(reading.answer_text(response)), skeleton, inventory)
    except (ValueError, Refused) as refused:
        record["refused"] = f"the plan answer is no plan: {str(refused)[:200]}"
    return kept(store, record)


def write(store, places, by, **steps):
    """write_now holding each place's lock (in order, across processes), so a second run of a place waits and then
    finds it written: nothing is paid twice."""
    with contextlib.ExitStack() as held:
        for place in sorted(set(places)):
            held.enter_context(locked(store.cache / AREA / "locks" / f"{place}.lock"))
        return write_now(store, places, by, **steps)


def cleared(store, places, euros, clear=None):
    """The spend block one writing run runs in: under the owner's allowance when AUTOMATIC (compute.reading_clearance's
    PLAN_WRITING node), else inside his yes (SCORE_SPEND_TICKET names it; compute.require_cleared refuses otherwise)."""
    from score.adapters import compute
    if AUTOMATIC:
        return compute.spending((clear or compute.reading_clearance)(store, places, euros, node=compute.PLAN_WRITING))
    compute.require_cleared("a plan writing", store)
    return contextlib.nullcontext()


def write_now(store, places, by, clear=None, ask=None):
    """Write the plan of every place of `places` whose inventory counts and has no plan written from it, a layer at a
    time (`layered`), the places of a layer side by side; the records. compute.Refused when it may not spend."""
    from score.adapters import compute
    places = to_write(store, places)
    if not places:
        return []
    folder = store.cache / AREA / stamp_key(concepts.now())
    folder.mkdir(parents=True, exist_ok=True)
    found = []
    with cleared(store, places, round(price(store) * len(places), 4), clear):
        compute.require_cleared("a plan writing", store)
        for layer in layered(store, places):
            with concurrent.futures.ThreadPoolExecutor(len(layer)) as pool:
                found += list(pool.map(lambda place: written_one(store, place, by, folder, ask or asked), layer))
    return found


def kept(store, record):
    store.write_once(f"{AREA}/{record['place']}/{stamp_key(record['at'])}.json", record)
    return record


def said(record):
    """One line of a writing: its place, items, gaps, euros and seconds, or why it was refused."""
    if record.get("refused"):
        return json.dumps({"place": record["place"], "refused": record["refused"], "euros": record["euros"]})
    return json.dumps({"place": record["place"], "items": len(record["plan"]["items"]),
                       "gaps": len(record["plan"]["gaps"]), "euros": record["euros"], "seconds": record["seconds"]})


def main(argv):
    """Write the places named; one line a place, or the refusal on stderr with exit 1."""
    from score.adapters.compute import Refused as NotCleared
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("places", nargs="+")
    parser.add_argument("--by", default="the owner's standing allowance")
    options = parser.parse_args(argv)
    store = Store.in_folder(os.environ["SCORE_SPEND_STORE"]) if os.environ.get("SCORE_SPEND_STORE") else Store.default()
    try:
        found = write(store, options.places, options.by)
    except (concepts.Refused, NotCleared) as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 1
    for record in found:
        print(said(record))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
