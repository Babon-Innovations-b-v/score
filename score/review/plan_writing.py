"""Plan writing (CONTEXT.md "plan"; the owner, 2026-10-21): a place's dimensioned plan measured off a drawing, element
by element. First its top-down drawing (score/review/plan_drawing.py: Nano Banana Pro redraws the picked concept as an
orthographic plan from above, on its outline on the layer above's plan); then Gemini 3.1 Pro reads every position and
footprint off that drawing, in its units (0..1000 of the squared drawing), and which part is which and the heights
from the concept, its scene inventory (rows with metres), the layer above's plan (where this place sits there, its
doors and neighbours) and its inside places; it never packs. The units are turned into metres here (`measured`): a
place the layer above lays out fills its box there, any other is scaled by its rows' metres (the median of each drawn
item's footprint against its row's), its outline box the drawn outline. A thing the creator already planned
(creator_plans: the ship's floor plan) is laid from his plan, never from the drawing's shapes (`creator_laid`). Then the free checks
(score/review/plan_checks.py, the arrangement against the concept's boxes among them), each failure a named gap of
the plan, never guessed past. A writing that wrote no plan from words alone (METHOD 1) is never shown again. A place
with no doors of its own (a scene added in the app) is given a door and its lead for each of its holder plan's
openings in its walls there (`held_doors`; one into the place leads back to the holder), told to the writing as fixed.

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

    plan-writings/<place>/<time>.json  {place, concept, reading, at, by, method, drawing (its sha), drawing_euros (0
                                       when an earlier writing paid it), measured, plan, euros, seconds}
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
import statistics
import sys
import time
import urllib.error

from score.review import concepts, creator_plans, plan_checks, plan_drawing, plan_fixes, plans, reading
from score.store import Store, locked, stamp_key

AREA = "plan-writings"
MODEL = concepts.PROMPT_MODEL
CALLER = "plan-writing"
TIMEOUT = 600
# 7: as 6, an item counting several of its row only for things drawn touching in one run (6 boxed a row's things
# drawn apart as one box round them all: palm trees round the square, owner 2026-10-21 "something has just broken the
# plans"); 6: measured off a top-down drawing in a square frame (owner, 2026-10-21), footprints as box_2d read on a
# grid, each inside place on the part its name fits; 5 to 2 trials of 2026-10-21 (2 and 3 drew in the painting's
# perspective); 1 packed from words. Only today's is shown.
METHOD = 7
# The owner's standing allowance (2026-10-21): a plan is written on its own once its inventory is read. False: only on
# his Make plan click, his spend yes for that one call.
AUTOMATIC = True
ESTIMATE = 0.05  # euros of one writing until one is measured (google_spend's Gemini 3.1 Pro estimate)
DRAWING_ESTIMATE = 0.15  # euros of one top-down drawing while no draw is measured (google_spend's Nano Banana Pro)
SWINGS = ("left", "right", "double", "slide", "none")
OPENINGS = ("door", "window", "opening", "gate")
ROOFS = ("flat", "dome", "pitched", "vault", "shed")
SHAPES = ("rect", "circle", "polygon")
FACINGS = ("N", "E", "S", "W")
SEEN = ("toward", "away", "left", "right")  # the way a thing faces in the painting, from its viewer
ASKED = """You are an architect drawing the dimensioned floor plan of one place of a game environment, element by
element. The first picture is the place's plan drawn from directly above (orthographic, north up, to scale): read every
position and shape off it, where it is drawn, and never move, pack or tidy anything. The second picture is the place's
concept painting (a three-quarter view): read from it which drawn part is which, and the heights. Every horizontal
position and length (x, y, wide, deep, points, from, to, centre, radius, thick, at, w, d, section) is in units of the
first picture: x from 0 at its left edge to 1000 at its right edge, y from 0 at its top edge to 1000 at its bottom edge
(the picture is square; its red grid lines, numbered at the edges, stand every 100 units: read each edge against
them). Every height (tall, base, sill, head, eave, top, a level's height, a stair's from and to, a
spot height) is in metres above the place's own floor or ground level +0.00. Angles in degrees from east (the
picture's right), clockwise, as y runs down.

The facts (JSON; the rows' metres name the rows and give their heights, the drawing gives their places and footprints):
{facts}

Write the plan as one JSON object with these keys:
- "outline": the place's footprint as drawn, [[x, y], ...] clockwise (a rectangle its 4 corners; a round or curved
  place its curve in enough points), round every part of the place.
- "walls": every wall, straight {{"from": [x, y], "to": [x, y], "thick": units, "tall": m}} or curved {{"arc":
  {{"centre": [x, y], "radius": units, "start": degrees, "end": degrees}}, "thick": units, "tall": m}}: the outer walls
  of every building, module, dome and tube as drawn, inner walls where drawn. An open ground has none of its own.
- "openings": every door, window, gate or open doorway, {{"kind": "door"|"window"|"gate"|"opening", "at": [x, y] (its
  middle, on its wall), "wide": units, "angle": the wall's direction in degrees, "swing": "left"|"right"|"double"|
  "slide"|"none", "sill": m, "head": m, "to": the place it leads to or null}}; the doors listed in the facts are fixed:
  list each at its place with its swing.
- "levels": every floor or ground area at its own height, {{"name": words, "height": m, "points": [[x, y], ...]}}
  (the main floor +0.00; a raised deck, a sunken pit, a platform, a balcony; outside, the ground's own areas: a
  plaza, a road, a quay, the sea or a pool at its water line, sand, grass).
- "stairs": every stair or ramp as drawn, {{"kind": "stair"|"ramp", "points": its footprint, "from": m, "to": m,
  "angle": the direction one walks up in degrees, "steps": a count}}.
- "roofs": every roof as drawn, {{"kind": "flat"|"dome"|"pitched"|"vault"|"shed", "points": its footprint, "eave": m,
  "top": m}}.
- "terrain": for ground outside, {{"spots": [[x, y, height m], ...], "contours": [{{"height": m, "points": [[x, y],
  ...]}}]}}: spot heights where the ground rises or falls and contour lines at an even step; {{}} for a place indoors.
- "items": every row of the facts' rows that stands on the floor or the ground (its items' counts adding up to the
  row's count), and the things on walls, ceilings or other rows worth placing, each where the drawing shows it,
  {{"row": the row's id, "count": how many of its row the item is (1 for one thing standing apart; only things of one
  row drawn touching each other in one tight run, a run of shelving, a row or stack of crates, a line of drums or
  cylinders standing together, are ONE item counting them all, its box round that run alone; things of a row drawn
  apart from each other, trees or lamps round a plaza, flags, chairs, scattered parts, are each an item of their own
  where each is drawn, never one box round them all),
  "box_2d": [ymin, xmin, ymax, xmax] of its footprint as drawn (in the drawing's units, never the row's metres),
  "shape": "rect"|"circle"|"polygon", "points": [[x, y], ...] (a polygon's corners, for a thing turned off the grid, a
  tube running at a slant, or of its own outline), "facing": "N"|"E"|"S"|"W"|null (the way its front or nose points
  on the drawing), "seen": the way its front or nose points in the painting, from its viewer: "toward"|"away"|"left"|
  "right", two joined by "-" for a slant ("toward-left"), null for a thing with no front, "tall": m, "base": m (the
  height it stands at: 0 on the floor, its parent's top on another row)}}. Every building, module, dome, hall and tube
  of the rows is an item of its row, also when it holds an inside place. A tube or corridor is one item from the part
  it leaves to the part it reaches, as long as drawn. A row the facts name under "planned by the creator" is laid
  from the creator's own plan at its own size: give its one item's box_2d where it is drawn, its facing the way its
  nose or front points as drawn and its seen; its inside places come from that plan: leave them out of "places".
- "structure": the ids of the rows that are the place's own shell, walls, floors, roof, ground, terrain areas, water,
  sea, plaza or sky (drawn as walls, levels, roofs and terrain above, never as items); never a building, module or
  tube standing on this place's ground.
- "beyond": the ids of the rows the painting shows beyond this place (through a window or a door, past its edge, far
  off): never placed here, they belong to the place they stand in.
- "zones": areas to keep clear beyond the doors' (a vehicle's keep-out, a landing pad), {{"name": words, "box_2d":
  [ymin, xmin, ymax, xmax]}}.
- "places": each inside place of the facts, on the part of the drawing that holds it, the part its name and use fit (an
  airlock where the way out is, by its ramp or outer door; a garage by its vehicle door; a greenhouse in the glass
  dome; a tube in a tube; a hangar in the hangar), {{"place": its name, "in": the id
  of the row holding it (a building, a module, a ship, a hall) or null for this place's own floor, "box_2d": [ymin,
  xmin, ymax, xmax] as drawn}}.
- "people": two to four standing spots [[x, y], ...] on free floor where a person would stand to look round.
- "section": {{"y": units}}, where a west-to-east cut through the place shows the most of its heights.
No text besides the JSON."""


# The plan answer's schema (ASKED's keys): the API holds the answer to it (ai.google.dev structured output).
NUMBER, STRING = {"type": "NUMBER"}, {"type": "STRING"}
POINT = {"type": "ARRAY", "items": NUMBER}
POINTS = {"type": "ARRAY", "items": POINT}


def shaped(fields, required=None):
    """An OBJECT schema of `fields` ({name: schema}) in their order; `required` names, else every field."""
    return {"type": "OBJECT", "properties": fields, "propertyOrdering": list(fields),
            "required": list(fields) if required is None else required}


def listed(fields, required=None):
    return {"type": "ARRAY", "items": shaped(fields, required)}


def chosen(*words, nullable=False):
    return {"type": "STRING", "enum": list(words), **({"nullable": True} if nullable else {})}


PLAN = shaped({
    "outline": POINTS,
    "walls": listed({"from": POINT, "to": POINT, "arc": shaped({"centre": POINT, "radius": NUMBER, "start": NUMBER,
                                                                "end": NUMBER}), "thick": NUMBER, "tall": NUMBER},
                    ["thick", "tall"]),
    "openings": listed({"kind": chosen("door", "window", "gate", "opening"), "at": POINT, "wide": NUMBER,
                        "angle": NUMBER, "swing": chosen("left", "right", "double", "slide", "none"), "sill": NUMBER,
                        "head": NUMBER, "to": {**STRING, "nullable": True}}),
    "levels": listed({"name": STRING, "height": NUMBER, "points": POINTS}),
    "stairs": listed({"kind": chosen("stair", "ramp"), "points": POINTS, "from": NUMBER, "to": NUMBER,
                      "angle": NUMBER, "steps": {"type": "INTEGER"}}),
    "roofs": listed({"kind": chosen("flat", "dome", "pitched", "vault", "shed"), "points": POINTS, "eave": NUMBER,
                     "top": NUMBER}),
    "terrain": shaped({"spots": POINTS, "contours": listed({"height": NUMBER, "points": POINTS})}, []),
    "items": listed({"row": STRING, "count": {"type": "INTEGER"}, "box_2d": POINT,
                     "shape": chosen("rect", "circle", "polygon"), "points": POINTS,
                     "facing": chosen(*FACINGS, nullable=True), "seen": {**STRING, "nullable": True}, "tall": NUMBER,
                     "base": NUMBER}, ["row", "count", "box_2d", "shape", "facing", "seen", "tall", "base"]),
    "structure": {"type": "ARRAY", "items": STRING},
    "beyond": {"type": "ARRAY", "items": STRING},
    "zones": listed({"name": STRING, "box_2d": POINT}),
    "places": listed({"place": STRING, "in": {**STRING, "nullable": True}, "box_2d": POINT}),
    "people": POINTS,
    "section": shaped({"y": NUMBER})})


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


def creator_metres(planned):
    """{row id: [wide, long, tall]} of the row a creator planned (creator_plans.planned's answer; None: none)."""
    if not planned:
        return {}
    row, found = planned
    return {row: [found["wide"], found["length"], found["tall"]]}


def rows_told(inventory, planned=None):
    """The inventory's rows as Gemini is told them: id, name, count, metres (a creator's plan's own over the
    reading's), anchor, where, terrain, its order hint."""
    picture = inventory.get("picture")
    metres = creator_metres(planned)
    return [{"id": row["id"], "name": row.get("name") or row["id"], "count": int(row.get("count", 1) or 1),
             "metres [wide, deep, tall]": metres.get(row["id"]) or (
                 row.get("size") if isinstance(row.get("size"), list) else None),
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
    planned = creator_plans.planned(skeleton.get("holds", []))
    return {"place": place, "name": concepts.name_of(place), "title": skeleton.get("title"),
            "shell": skeleton.get("shell"), "heights in words": skeleton.get("height") or None,
            "within": within_told(store, place),
            "fixed doors": [door_told(door, leads) for door in skeleton.get("doors", [])],
            "inside places": [{"place": hold["place"], "about [wide, deep]": [hold["w"], hold["d"]]}
                              for hold in skeleton.get("holds", [])
                              if not planned or hold["place"] not in planned[1]["places"]],
            "planned by the creator": planned and {
                "row": planned[0], "what": planned[1]["what"],
                "metres [wide, long, tall]": creator_metres(planned)[planned[0]],
                "its inside places": planned[1]["places"]},
            "rows": rows_told(inventory, planned)}


def squared(picture):
    """The drawing padded white to a square (its top-left kept), so the answer's 0..1000 units run alike both ways."""
    from PIL import Image
    side = max(picture.size)
    found = Image.new("RGB", (side, side), (255, 255, 255))
    found.paste(picture.convert("RGB"), (0, 0))
    return gridded(found)


GRID = 100  # drawing units between the lines of the grid the writer reads positions against


def gridded(picture):
    """The square drawing with a faint grid every GRID units, each line numbered at the edges (0..1000)."""
    from PIL import ImageDraw
    side = picture.size[0]
    pen = ImageDraw.Draw(picture)
    for unit in range(0, 1001, GRID):
        at = min(round(unit * side / 1000), side - 1)
        pen.line([(at, 0), (at, side)], fill=(255, 120, 120), width=1)
        pen.line([(0, at), (side, at)], fill=(255, 120, 120), width=1)
        pen.text((at + 3, 3), str(unit), fill=(200, 0, 0), font_size=max(12, side // 70))
        pen.text((3, at + 3), str(unit), fill=(200, 0, 0), font_size=max(12, side // 70))
    return picture


def asked_body(drawing, concept, facts):
    """The Gemini request: ASKED with the facts, the top-down drawing (squared) and the picked concept."""
    from PIL import Image
    pro, _, _ = concepts.tools()
    drawn, picture = squared(Image.open(drawing)), Image.open(concept)
    return {"contents": [{"role": "user", "parts": [
        {"text": ASKED.format(facts=json.dumps(facts, indent=1))},
        pro.part(drawn, max(drawn.size)), pro.part(picture, max(picture.size))]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json", "responseSchema": PLAN}}


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


def counted_seen(item):
    """An answered item's count (kept when more than one) and the way it is seen facing in the painting (SEEN words
    joined by "-"), as its shape keeps them."""
    count = int(number(item.get("count"), 1) or 1)
    seen = [word for word in str(item.get("seen") or "").lower().split("-") if word in SEEN]
    return {**({"count": count} if count > 1 else {}), **({"seen": seen} if seen else {})}


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
        x, y, across, along, shape = found
        facing = item.get("facing") if item.get("facing") in FACINGS else None
        items.append([name, round(x, 3), round(y, 3), round(across, 3), round(along, 3), facing, "item"])
        rows[name] = [row]
        size = by_id[row].get("size")
        shapes[name] = {**shape, "tall": number(item.get("tall"), number(size[2]) if isinstance(size, list) else None),
                        "base": number(item.get("base"), 0.0), **counted_seen(item)}
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


# --- the answer measured: drawing units to metres ----------------------------------------------------------------

def drawn_extent(answer):
    """(low x, low y, high x, high y) in drawing units of the answer's outline, else of its items; None with neither."""
    items = answer.get("items") if isinstance(answer.get("items"), list) else []
    corners = points(answer.get("outline")) or [corner for corner in (
        point([item.get("x"), item.get("y")]) for item in items if isinstance(item, dict)) if corner]
    if not corners:
        return None
    xs, ys = [corner[0] for corner in corners], [corner[1] for corner in corners]
    return min(xs), min(ys), max(xs), max(ys)


def rows_scale(answer, inventory):
    """Metres a drawing unit by the rows' metres: the median over the answered items of a row with a size of the
    root of its metres' footprint over its drawn footprint; None when no item can tell. A tube or a thing drawn as a
    polygon (turned off the grid: its box is not its footprint) tells nothing."""
    sizes = {row["id"]: row["size"] for row in inventory.get("rows", []) if isinstance(row.get("size"), list)
             and len(row["size"]) >= 2 and all(number(part) for part in row["size"][:2])
             and not plans.whole(row, inventory.get("picture")) and not plan_checks.connector(row)}
    found = []
    for item in answer.get("items") or []:
        box = footprint_of(item) if isinstance(item, dict) and item.get("row") in sizes \
            and item.get("shape") != "polygon" else None
        if box:
            wide, deep = sizes[item["row"]][:2]
            found.append(math.sqrt(wide * deep / (box[2] * box[3])))
    return sorted(found)[len(found) // 2] if found else None


def scale_of(answer, skeleton, inventory, held):
    """((metres a unit along x, along y), (origin x, origin y) in units, how): a place the layer above lays out
    (`held`) fills its box there, each way; any other is measured by its rows' metres, else fills its own plan's box;
    its origin its drawn outline's north-west corner. Refused when none tells."""
    extent = drawn_extent(answer)
    if extent is None or extent[2] <= extent[0] or extent[3] <= extent[1]:
        raise Refused("the answer draws no outline to measure")
    if held:
        return ((skeleton["w"] / (extent[2] - extent[0]), skeleton["d"] / (extent[3] - extent[1])), extent[:2],
                "its box on the layer above's plan")
    found = rows_scale(answer, inventory)
    if found is not None:
        return (found, found), extent[:2], "its rows' metres"
    if skeleton.get("w") and skeleton.get("d"):
        return ((skeleton["w"] / (extent[2] - extent[0]), skeleton["d"] / (extent[3] - extent[1])), extent[:2],
                "its own plan's box (no row with metres drawn)")
    raise Refused("no drawn item of a row with metres to measure the drawing by")


def unboxed(entry, keys, middle):
    """An answered entry's `box_2d` [ymin, xmin, ymax, xmax] as its `keys` (x, y, wide, deep): x, y its middle when
    `middle`, else its top-left corner; the entry as it is without one."""
    box = entry.get("box_2d") if isinstance(entry, dict) else None
    if not (isinstance(box, list) and len(box) == 4 and all(number(part) is not None for part in box)):
        return entry
    top, left, bottom, right = (number(part) for part in box)
    wide, deep = right - left, bottom - top
    return {**entry, keys[0]: left + wide / 2 if middle else left, keys[1]: top + deep / 2 if middle else top,
            keys[2]: wide, keys[3]: deep}


def unboxed_all(answer):
    """The answer with every item's, zone's and inside place's `box_2d` turned into its spans (`unboxed`)."""
    spans = {"items": (("x", "y", "wide", "deep"), True), "zones": (("x", "y", "wide", "deep"), False),
             "places": (("x", "y", "w", "d"), False)}
    return {**answer, **{key: [unboxed(entry, keys, middle) for entry in answer[key]]
                         for key, (keys, middle) in spans.items() if isinstance(answer.get(key), list)}}


def metred(answer, scale, origin):
    """The answer with every horizontal position and length in plan metres (`scale` metres a unit along x and y,
    `origin` the unit point at plan 0, 0); heights, angles and shapes as answered. A value off the schema is left as
    it is, for the checks of plan_from to drop."""
    (along_x, along_y), (left, top) = scale, origin
    mean = (along_x + along_y) / 2

    def at(value):
        found = point(value)
        return [round((found[0] - left) * along_x, 3), round((found[1] - top) * along_y, 3)] if found else value

    def run(value, along):
        found = number(value)
        return round(found * along, 3) if found is not None else value

    def each(value):
        return [at(part) for part in value] if isinstance(value, list) else value

    def walled(wall):
        if not isinstance(wall, dict):
            return wall
        found = {**wall, "from": at(wall.get("from")), "to": at(wall.get("to")), "thick": run(wall.get("thick"), mean)}
        if isinstance(wall.get("arc"), dict):
            found["arc"] = {**wall["arc"], "centre": at(wall["arc"].get("centre")),
                            "radius": run(wall["arc"].get("radius"), mean)}
        return found

    def boxed(entry, keys):
        if not isinstance(entry, dict):
            return entry
        x, y = at([entry.get(keys[0]), entry.get(keys[1])]) if point([entry.get(keys[0]), entry.get(keys[1])]) \
            else (entry.get(keys[0]), entry.get(keys[1]))
        return {**entry, keys[0]: x, keys[1]: y, keys[2]: run(entry.get(keys[2]), along_x),
                keys[3]: run(entry.get(keys[3]), along_y), **({"points": each(entry["points"])} if "points" in entry
                                                              else {})}

    def shaped(entry, key="points"):
        return {**entry, key: each(entry.get(key))} if isinstance(entry, dict) else entry

    def listed_as(key, change):
        return [change(entry) for entry in answer[key]] if isinstance(answer.get(key), list) else answer.get(key)

    terrain = answer.get("terrain") if isinstance(answer.get("terrain"), dict) else {}
    spots = [[*at(spot[:2]), spot[2]] if isinstance(spot, list) and len(spot) == 3 and point(spot[:2]) else spot
             for spot in terrain.get("spots") or []] if isinstance(terrain.get("spots"), list) else []
    section = answer.get("section") if isinstance(answer.get("section"), dict) else {}
    section_y = number(section.get("y"))
    return {**answer, "outline": each(answer.get("outline")), "walls": listed_as("walls", walled),
            "openings": listed_as("openings", lambda entry: {**entry, "at": at(entry.get("at")),
                                                             "wide": run(entry.get("wide"), mean)}
                                  if isinstance(entry, dict) else entry),
            "levels": listed_as("levels", shaped), "stairs": listed_as("stairs", shaped),
            "roofs": listed_as("roofs", shaped),
            "terrain": {**terrain, "spots": spots, "contours": [shaped(line) for line in terrain.get("contours") or []]
                        if isinstance(terrain.get("contours"), list) else []},
            "items": listed_as("items", lambda entry: boxed(entry, ("x", "y", "wide", "deep"))),
            "zones": listed_as("zones", lambda entry: boxed(entry, ("x", "y", "wide", "deep"))),
            "places": listed_as("places", lambda entry: boxed(entry, ("x", "y", "w", "d"))),
            "people": each(answer.get("people")),
            "section": {"y": round((section_y - top) * along_y, 3)} if section_y is not None else section}


def measured(answer, skeleton, inventory, held):
    """(the answer in plan metres, the skeleton with its outline box measured, how it was measured): the drawing's
    units turned into metres (`scale_of`); a place not laid out above takes its outline box from the drawing."""
    if not isinstance(answer, dict):
        raise Refused("the answer is no JSON object")
    answer = unboxed_all(answer)
    scale, origin, how = scale_of(answer, skeleton, inventory, held)
    found = metred(answer, scale, origin)
    if not held:
        low_x, low_y, high_x, high_y = drawn_extent(answer)
        skeleton = {**skeleton, "w": round((high_x - low_x) * scale[0], 3), "d": round((high_y - low_y) * scale[1], 3)}
    return found, skeleton, {"metres a unit": [round(scale[0], 5), round(scale[1], 5)], "by": how}


def creator_laid(plan):
    """Lay the thing a creator planned (creator_plans) on `plan`, in place: its item at its own size and outline, its
    middle where it is drawn, its nose the way it is drawn, its inside places that plan's rooms; (the places laid,
    gaps). Not drawn, it is a gap and its places stay as answered; drawn with no facing, it is laid along its drawn
    box's long side, nose south or east, and that is a gap."""
    found = creator_plans.planned(plan.get("holds", []))
    if not found:
        return set(), []
    row, creator = found
    drawn = [number for number, item in enumerate(plan["items"]) if (plan["rows"].get(item[0]) or [None])[0] == row]
    if not drawn:
        return set(), [{"kind": "placed", "item": row, "row": row,
                        "words": f"{row.replace('_', ' ')} is not drawn, so {creator['what']} is not laid"}]
    gaps = []
    name, x, y, wide, deep, facing, kind = plan["items"][drawn[0]]
    middle = [x + wide / 2, y + deep / 2]
    if facing is None:
        facing = "S" if deep >= wide else "E"
        gaps.append({"kind": "arrangement", "item": name, "row": row, "at": [round(value, 2) for value in middle],
                     "words": f"the way {name.lower()}'s nose points was not read: laid nose {facing}"})
    box, shape, rooms = creator_plans.laid(creator, middle, facing)
    plan["items"][drawn[0]] = [name, *box, facing, kind]
    plan["shapes"][name] = {**plan["shapes"].get(name, {}), **shape}
    plan["holds"] = [{**hold, "row": row, **dict(zip(("x", "y", "w", "d"), rooms[hold["place"]]))}
                     if hold["place"] in rooms else hold for hold in plan["holds"]]
    return set(rooms), gaps


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
    laid_places, laid_gaps = creator_laid(plan)
    hold_gaps = [gap for gap in hold_gaps if gap["item"] not in laid_places] + laid_gaps
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


def refused_now(store, place):
    """Whether the place's newest writing was refused from its lock and reading in force by today's METHOD."""
    last = (writings(store, place) or [{}])[-1]
    return bool(last.get("refused")) and last.get("method") == METHOD and last.get("concept") == concepts.picked(
        store, place) and last.get("reading") == reading_at(store, place)


def owed(store, places):
    """The places of `places` written on their own (`to_write`), less those `refused_now`: never paid for again on
    every sync pass, his Make plan writes them again."""
    return [place for place in to_write(store, places) if not refused_now(store, place)]


def started(store, places, start=None):
    """The plans of `places` written in a process of its own that outlives the caller (the sync pass's `plans keep`
    goes on); its log's path. Each place's lock makes a second run wait and find it written."""
    import shutil
    import subprocess
    log = store.cache / AREA / "logs" / f"{stamp_key(concepts.now())}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    # Under a systemd service (the sync) in a scope of its own, so the service's end does not kill it (web.reading_started).
    scope = (["systemd-run", "--user", "--scope", "--quiet", "--collect"]
             if os.environ.get("INVOCATION_ID") and shutil.which("systemd-run") else [])
    with log.open("w") as out:
        (start or subprocess.Popen)([*scope, sys.executable, "-m", "score.review.plan_writing", *places],
                                    env={**os.environ, "SCORE_SPEND_STORE": str(store.cache.parent)}, stdout=out,
                                    stderr=subprocess.STDOUT, start_new_session=True, cwd=str(concepts.REPO))
    return str(log)


def spent(store, places):
    """The euros every writing of `places` and every top-down drawing it was measured from cost, in sum (the cockpit's
    running total beside the readings')."""
    return round(sum(found["euros"] for place in places for found in writings(store, place))
                 + plan_drawing.spent(store, places), 4)


def typical(store, area, method=None):
    """The median euros of the calls kept under `area` (of `method` only, when given), None with none."""
    found = [record["euros"] for record in (store.read(key) for key in store.objects.keys(f"{area}/"))
             if method is None or record.get("method") == method] if store else []
    return statistics.median(found) if found else None


def price(store=None):
    """The euros one writing is priced at: its call (the median measured writing of today's METHOD, else ESTIMATE:
    an older method's call asked another question) and its top-down drawing (the median measured drawing, else a
    concept draw's price), rounded up to the cent: what one costs, not the dearest one ever."""
    call = typical(store, AREA, METHOD)
    call = call if call is not None else ESTIMATE
    drawing = typical(store, plan_drawing.AREA)
    drawing = drawing if drawing is not None else (concepts.draw_euros() or DRAWING_ESTIMATE)
    return math.ceil(round((call + drawing) * 100, 6)) / 100


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


ON_WALL = 0.3  # metres a holder's opening may lie off an inside place's box edge and still be in its wall


def opening_side(opening, outline):
    """(side, along) of a holder plan's opening on the edge of an inside place's box there ([x, y, w, d], metres):
    the wall it is in and how far along that wall from the box's north-west corner; None when it is in none."""
    x0, y0, wide, deep = outline
    at_x, at_y = opening["at"]
    across = x0 - ON_WALL <= at_x <= x0 + wide + ON_WALL
    along = y0 - ON_WALL <= at_y <= y0 + deep + ON_WALL
    for side, gap, inside, run in (("N", at_y - y0, across, at_x - x0), ("S", at_y - y0 - deep, across, at_x - x0),
                                   ("W", at_x - x0, along, at_y - y0), ("E", at_x - x0 - wide, along, at_y - y0)):
        if inside and abs(gap) <= ON_WALL:
            return side, round(min(max(run, 0.0), wide if side in "NS" else deep), 3)
    return None


def held_door(opening, place, holder, outline):
    """(door, lead key, lead) of a holder's opening in an inside place's wall: the door [side, along, wide, what(,
    sill)], its lead the holder for an opening into the place, else where the opening leads (none said: no `to`, a
    gap the plan gate names); None for an opening in none of its walls."""
    found = opening_side(opening, outline)
    if found is None:
        return None
    side, along = found
    tall = opening["head"] - opening["sill"] if opening.get("head") else None
    what = f"{opening['kind']} {opening['wide']:g} x {tall:g} m" if tall else opening["kind"]
    door = [side, along, opening["wide"], what] + ([opening["sill"]] if opening.get("sill") else [])
    key = f"{side}@{opening['sill']:g}" if opening.get("sill") else side
    to = holder if opening.get("to") == place else opening.get("to")
    lead = {"why": f"the {holder} plan's {opening['kind']} at {opening['at']} is in this place's {side} wall"}
    return door, key, {"to": to, **lead} if to else lead


def held_doors(skeleton, place, holder, outline, openings):
    """The skeleton of a place with no doors of its own (a scene added in the app) with a door and lead for each of its
    holder plan's openings in its walls (`outline`, its box there); any other skeleton as it is."""
    if skeleton.get("doors") or not outline:
        return skeleton
    found = [door for door in (held_door(opening, place, holder, outline) for opening in openings or []) if door]
    if not found:
        return skeleton
    return {**skeleton, "doors": [door for door, _, _ in found],
            "leads": {**skeleton.get("leads", {}), **{key: lead for _, key, lead in found}}}


def holder_doors(store, place, skeleton):
    """`held_doors` from the place's holder plan shown now, the skeleton as it is for a place nothing holds."""
    held = plans.holder_of(store, place)
    if held is None:
        return skeleton
    above = plans.current(store, held["holder"])["plan"]
    return held_doors(skeleton, place, held["holder"], held["outline"], above.get("openings"))


def written_one(store, place, by, folder, ask):
    """Write one place's plan: its top-down drawing first (plan_drawing.drawn), then `ask(body)` reading it; its
    record, kept (refused, with why, when the drawing is)."""
    skeleton = holder_doors(store, place, plans.derived(store, place))
    inventory = plans.inventory_of(store, place)
    sha = concepts.picked(store, place)
    record = {"place": place, "concept": sha, "reading": reading_at(store, place), "by": by, "method": METHOD}
    try:
        drawing = plan_drawing.drawn(store, place)
    except concepts.Refused as refused:
        return kept(store, {**record, "at": concepts.now(), "euros": 0.0, "refused": f"no top-down drawing: {refused}"})
    record.update({"drawing": drawing["sha"], "drawing_euros": drawing["euros"] if drawing.get("fresh") else 0.0})
    body = asked_body(reading.picture_path(store, drawing["sha"], folder), reading.picture_path(store, sha, folder),
                      facts_of(store, place, skeleton, inventory))
    (folder / f"{place}-asked.json").write_text(json.dumps(body["contents"][0]["parts"][0], indent=1))
    response, seconds = ask(body)
    (folder / f"{place}-answer.json").write_text(json.dumps(response, indent=1))
    record.update({"at": concepts.now(), "euros": call_euros(response), "seconds": seconds})
    try:
        answer, skeleton, record["measured"] = measured(json.loads(reading.answer_text(response)), skeleton,
                                                         inventory, plans.holder_of(store, place) is not None)
        record["plan"] = plan_from(answer, skeleton, inventory)
    except (ValueError, Refused) as refused:
        record["refused"] = f"the plan answer is no plan: {str(refused)[:200]}"
        return kept(store, record)
    # fixed before it is shown: the free fixes, then what is left corrected by the prompt model (plan_fixes)
    record["plan"], record["calls"] = plan_fixes.settled(store, place, record["plan"], inventory, ask)
    record["euros"] = round(record["euros"] + sum(call.get("euros", 0.0) for call in record["calls"]), 6)
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
        return json.dumps({"place": record["place"], "refused": record["refused"], "euros": record["euros"],
                           "drawing euros": record.get("drawing_euros", 0.0)})
    return json.dumps({"place": record["place"], "items": len(record["plan"]["items"]),
                       "gaps": len(record["plan"]["gaps"]), "euros": record["euros"],
                       "drawing euros": record.get("drawing_euros", 0.0), "seconds": record["seconds"]})


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
