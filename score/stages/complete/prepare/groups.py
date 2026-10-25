"""Free counts of a remake's rows (#19: every scene inventory row through the prop pipeline): the unique models the
rows need, one take each, read from the environment's scene inventories alone (each place's current reading,
`current`). Nothing is judged or bought.

A row's model is its object kind (the row id with any trailing `_<n>`), the ratio of its sides (sorted, each over the
longest, bucketed in RATIO_STEP steps of log2, so a stool and a taller stool of the same build share one take while a
rod and a plate do not) and its kit (a kit group such as `kit: wall`, else none). Rows of one place with the same
model are one group: one take, drawn from the first row's concept crop (its place's concept picture, view and box).
The same model across places is counted apart (`across_places`): a place's style may differ, so sharing a take
across places is the owner's call, never assumed.

A shell piece (a wall, floor or ceiling kit piece, SHELL) is marked `shell`; it takes the whole route like any model
(estimate.py: the finish route lists its library surface, no maps). A row that already reuses another place's take
(`reuse`) needs no take of its own.
"""
import hashlib
import json
import math
import pathlib
import re

from score.stages.complete.prepare import contract

SHELL = ("kit: wall", "kit: floor", "kit: ceiling", "kit: under floor")
# A row whose head word (head_word) is one of these is that shell piece, whatever its kind (read_row).
SHELL_NOUNS = {"wall": "kit: wall", "floor": "kit: floor", "ceiling": "kit: ceiling", "roof": "kit: ceiling"}
# A row's route by its head word (head_word, or its whole noun) (owner's rules, CONTEXT.md "layer adapter",
# "motion"): people are models of the prop pipeline with the motion layer's steps after (every row the row-kind rules
# say acts: row_kinds' person kind, the one classification, people_of); the sky, the effects and the far city have
# routes of their own (layers without models); the place's ground itself (plans.GROUND's land words: the street, the
# pavement, the plaza, the hills) is the terrain node's (its own rows, CONTEXT.md "layer adapter": no take); the
# place's structure (the reading's STRUCTURE words, windows, doors, stairs and building shells) is a shell piece
# (route "shell"), or the plan's own where the plan lays it (plan_laid: route "plan", no take); every other row, a
# terrain feature too, a model through the prop pipeline.
ROUTES = {"sky": {"sky", "planet", "moon"},
          "effects": {"water", "ocean", "puddles", "rain", "smoke", "mist", "plume", "steam", "fog"},
          "skyline": {"city", "cityscape", "city skyline", "skyline"},
          "ground": {"ground", "terrain", "road", "street", "pavement", "plaza", "grass", "sand", "dust", "regolith",
                     "soil", "hills", "mountains", "landscape"}}
SHELL_WORDS = {"window", "windows", "door", "doors", "stairs", "steps", "staircase", "building facade", "exterior wall"}
# A head word that names a piece of what the word before it names: "wall panels", "floor grating", "street surface"
# are a wall's, a floor's, a street's (a "control panel" a control's: no shell).
PART_WORDS = {"panel", "panels", "plate", "plates", "grating", "grate", "grates", "tile", "tiles", "section",
              "sections", "slab", "slabs", "surface", "surfaces"}
# The plan cuts these itself (score/stages/earth_seed/design_shell.py, the scene record: every opening of its walls),
# so a row of one is no model. A stair or ramp stays a shell piece's model: a lander's ramp is no stair the plan draws.
PLAN_LAID = {"opening", "openings", "doorway", "doorways"}
# A floor, deck, wall, roof or ceiling at least this share of its place's outline across (its own longest side over
# the outline's shorter side) is the room's own shell the plan lays (deck, walls, roof), never a model: the Batch 1
# try 3 close-ups of a 50 m upper floor and 32 by 12 m wall panels. Measured on the 24 kept plans' rows (2026-10-25):
# a room's floors, walls and roofs span 1 to 3.4 of it, its single panels and porch pieces at most 0.17; a dome's
# floor or wall in an outdoor camp 0.46 to 0.61.
ROOM_SHARE = 0.5
ROOM_PIECES = {"floor", "floors", "deck", "decks", "wall", "walls", "roof", "roofs", "ceiling", "ceilings"}
MODEL_ROUTES = ("prop", "shell", "people")  # the routes whose models the prop pipeline makes
RATIO_STEP = 0.5  # log2: sides within about 41% of each other's ratio share a bucket


def inventories(folder):
    """{place: its scene inventory record} of every <place>.json in `folder` (the design's kept inventories)."""
    return {path.stem: json.loads(path.read_text()) for path in sorted(pathlib.Path(folder).glob("*.json"))}


def current(store, places):
    """({place: its scene inventory}, [place waiting on inventory]) of `places`: each place's current reading
    (score/review/reading.reading_of: read from its picked draw by today's method), its rows as read_row gives them;
    a place with none waits, with no rows and no euros (the old data/inventory files count for nothing here)."""
    from score.review import reading
    found = {place: reading.reading_of(store, place) for place in places}
    return ({place: {**record["inventory"], "rows": sized_rows(store, place, record), "size": record.get("size"),
                     "plan": {"views": [{"id": "v1", "picture": str(blob_path(store, record["concept"]))}]}}
             for place, record in found.items() if record},
            sorted(place for place, record in found.items() if not record))


def sized_rows(store, place, record):
    """A reading's rows as read_row gives them, each with its size: its item's on the place's current plan
    (plan_sizes: his edits count), else its reading's metres (a row on a wall, the ceiling or another row has no item
    of its own, and keeps its own size), None where neither gives one (a gap: its take waits on "no size"); and its
    `read_size`, the object's own metres as its reading gave them (None where it gave none): the plan's item is the
    footprint it is laid in (a run of things, room round it), so the close-up's request and shape check hold the
    object to its own size (owner, 2026-10-24). A shell piece the plan lays itself has route "plan" (plan_laid)."""
    sizes = plan_sizes(store, place, record["inventory"]["rows"])
    outline = outline_of(store, place)
    found = [{**read_row(record, row), "size": sizes.get(row["id"]) or reading_size(row),
              "read_size": reading_size(row)} for row in record["inventory"]["rows"]]
    return [{**row, "route": "plan"} if plan_laid(row, outline) else row for row in found]


def outline_of(store, place):
    """The place's outline [wide, deep] metres on its current plan, None without a plan."""
    from score.review import plans
    shown = plans.current(store, place)
    return [shown["plan"].get("w") or 0.0, shown["plan"].get("d") or 0.0] if shown else None


def plan_laid(row, outline):
    """Whether a shell piece is the plan's own (PLAN_LAID: an opening or a doorway; or a floor, deck, wall, roof or
    ceiling spanning ROOM_SHARE of the place's `outline` by its own size, else its size)."""
    if row["route"] != "shell":
        return False
    head = head_word(row["noun"])
    if head in PLAN_LAID:
        return True
    size, short = row.get("read_size") or row.get("size"), min(outline or [0.0])
    return head in ROOM_PIECES and bool(sides(size)) and short > 0 and max(size[:2]) >= ROOM_SHARE * short


def reading_size(row):
    """A reading row's [wide, deep, tall] metres (score/review/reading.py METHOD 4), None when it gave none."""
    size = row.get("size")
    return list(size) if sides(size) else None


def plan_sizes(store, place, rows):
    """{row id: [wide, deep, tall] metres} of the reading's `rows` the place's current plan sizes
    (score/review/plans.current: his newest edit on the pick, else the derived plan, whose items are sized by the
    reading's metres), each from the first item tied to it: its wide and deep as laid (turned back for one facing
    east or west), its tall the reading's, else off its surest SAM box at the scale its wide gives the box (an item
    he sized whose row the reading gave no size). A row whose item is a size gap on its plan, or with no item of its
    own (on a wall, in the sky, riding on another row: `sized_rows` gives it its reading's), has none here."""
    from score.review import plans
    shown = plans.current(store, place)
    if shown is None:
        return {}
    plan, by_id = shown["plan"], {row["id"]: row for row in rows}
    unsized = {gap["item"] for gap in plan.get("gaps", []) if gap.get("kind") == "size"}
    found = {}
    for name, _, _, wide, deep, facing, kind in plan.get("items", []):
        tied = (plan.get("rows") or {}).get(name) or []
        if kind != "item" or name == plans.WALLS_ITEM or name in unsized or not tied or tied[0] in found:
            continue
        if facing in ("E", "W"):
            wide, deep = deep, wide
        row = by_id.get(tied[0]) or {}
        tall = (reading_size(row) or [None] * 3)[2] or tall_of(row, wide)
        if tall:
            found[tied[0]] = [round(wide, 3), round(deep, 3), tall]
    return found


def tall_of(row, wide):
    """A row's tall in metres off its surest SAM box at `wide` metres across, None with no box of area."""
    box = (row.get("boxes") or [row.get("box")])[0]
    if contract.box_faults(box):
        return None
    return round(wide * (box[3] - box[1]) / (box[2] - box[0]), 3)


def blob_path(store, sha):
    """The picked concept's file in the store's blob folder (contract.faults reads it), or its key elsewhere."""
    return store.objects.path(f"blobs/{sha}") if hasattr(store.objects, "path") else f"blobs/{sha}"


def read_row(record, row):
    """A reading's row as a take's: its take named by its place, row and concept (a take made from another concept
    never counts as made), its route by its noun (route_of), and a shell piece whose head word is a shell word
    (SHELL_NOUNS) that piece's kit; every other row, a terrain feature's too, a model through the prop pipeline. A
    reading sizes in metres; its plan's item, his edits counted, gives it first (sized_rows). Its box is SAM 3's,
    else Gemini's (boxed_by)."""
    route = route_of(row["noun"])
    noun = SHELL_NOUNS.get(singular(head_word(row["noun"]))) if route == "shell" else None
    return {**row, **boxed_by(record, row), "thing": f"prop:{record['place']}_{row['id']}_{record['concept'][:8]}",
            "route": route, **({"group": noun} if noun else {})}


def boxed_by(record, row):
    """A reading row's box and who placed it: SAM 3's surest instance, else Gemini's region round all of it (the
    reading's first step, #10), so its close-up can still be framed; neither, nothing (its take an input gap)."""
    if row.get("box"):
        return {"boxed_by": "SAM 3"}
    if row.get("region") and record.get("size"):
        box = gemini_box(row["region"], record["size"])
        return {"box": box, "boxes": [box], "boxed_by": "Gemini"}
    return {}


def gemini_box(region, size):
    """A 0 to 1000 [ymin, xmin, ymax, xmax] region (score/review/reading.py) as a pixel box [left, top, right,
    bottom] on a picture of `size` [wide, tall]."""
    wide, tall = size
    return [round(region[1] * wide / 1000), round(region[0] * tall / 1000), round(region[3] * wide / 1000),
            round(region[2] * tall / 1000)]


def route_of(noun):
    """A reading row's route by its noun: people where the row-kind rules say it acts (people_of), else the first of
    ROUTES holding its whole noun or its head word (head_word), else a shell piece where that is a structure word
    (the reading's STRUCTURE, SHELL_WORDS), else prop."""
    whole, head = noun.strip().lower(), head_word(noun)
    if people_of(noun):
        return "people"
    found = next((route for route, nouns in ROUTES.items() if whole in nouns or {head, singular(head)} & nouns), None)
    if found:
        return found
    from score.review import reading
    return "shell" if whole in SHELL_WORDS or {head, singular(head)} & (reading.STRUCTURE | SHELL_WORDS) else "prop"


def people_of(noun):
    """Whether a noun names people: its whole noun or its last word, as written or singular, is a noun of a row kind
    that acts (score/stages/row_kinds.py, data/checks/row-kinds.json: person, man, women, pilot...)."""
    from score.stages import row_kinds
    kinds = row_kinds.table()
    words = row_kinds.words(noun).split()
    last = words[-1] if words else ""
    return any("acts" in row_kinds.does(row_kinds.kind_of({"noun": wanted}, kinds), kinds)
               for wanted in {" ".join(words), last, singular(last)} if wanted)


def head_word(noun):
    """A noun's head word, lower case: its last word, or the word before it where the last names a part of it
    (PART_WORDS: "wall panels" a wall's, "street surface" a street's)."""
    words = noun.strip().lower().split()
    if len(words) > 1 and words[-1] in PART_WORDS:
        return words[-2]
    return words[-1] if words else ""


def singular(word):
    """A word without a plural's s ("plates" "plate", "stairs" kept where its singular is no word here)."""
    return word[:-1] if word.endswith("s") and not word.endswith("ss") else word


def object_kind(row_id):
    """A row's object kind: its id with any trailing `_<n>` (a numbered copy) and `.<place>` left out."""
    return re.sub(r"(_\d+)+$", "", row_id.split(".")[0])


def sides(size):
    """A size's sides, shortest first, each over the longest; None for a size that is not three positive numbers."""
    if not isinstance(size, list) or len(size) != 3 or not all(isinstance(side, (int, float)) and side > 0
                                                               for side in size):
        return None
    ordered = sorted(size)
    return ordered[0] / ordered[2], ordered[1] / ordered[2]


def size_ratio(size):
    """A size's ratio bucket: (shortest, middle) over the longest in RATIO_STEP steps of log2, or None."""
    found = sides(size)
    return None if found is None else tuple(round(math.log2(side) / RATIO_STEP) for side in found)


def kit_of(row):
    """A row's kit group (`kit: wall`), or None for a row of no kit."""
    group = row.get("group") or ""
    return group if group.startswith("kit:") else None


def is_shell(row):
    return kit_of(row) in SHELL


def model_key(row):
    """(object kind, size ratio, kit): rows of one place with the same key are one take."""
    return object_kind(row["id"]), size_ratio(row.get("size")), kit_of(row)


def crop_hash(record, row):
    """The concept crop a row is drawn from: sha256 of its place's concept picture's sha256, its view and its box."""
    concept = (record.get("concept_pick") or {}).get("sha256", "")
    text = json.dumps([concept, row.get("view"), row.get("box")])
    return hashlib.sha256(text.encode()).hexdigest()


def place_groups(place, record):
    """[{place, key, rows, take, instances, shell, crop, size, view, box, reuse}] of a place's rows, one a model
    (model_key), in the inventory's order; a row that reuses another place's take is a group of its own marked
    `reuse`."""
    groups, by_key = [], {}
    for row in record.get("rows", []):
        if row.get("reuse"):
            groups.append(group_of(place, record, row, ("reuse", row["reuse"], None)))
            continue
        key = model_key(row)
        if key in by_key:
            by_key[key]["rows"].append(row["id"])
            by_key[key]["instances"] += row.get("count", 1)
            continue
        by_key[key] = group_of(place, record, row, key)
        groups.append(by_key[key])
    return groups


def group_of(place, record, row, key):
    """A new group whose first row is `row`."""
    return {"place": place, "key": list(key), "rows": [row["id"]],
            "take": row.get("thing", "").partition(":")[2] or row["id"], "instances": row.get("count", 1),
            "route": row.get("route", "prop"), "shell": is_shell(row) or row.get("route") == "shell",
            "crop": crop_hash(record, row), "size": row.get("size"), "view": row.get("view"),
            "box": row.get("box"), "reuse": row.get("reuse")}


def counts(groups_by_place):
    """{rows, instances, groups, reused, shell_groups, crops, across_places} of every place's groups."""
    every = [group for groups in groups_by_place.values() for group in groups]
    taking = [group for group in every if not group["reuse"]]
    return {"rows": sum(len(group["rows"]) for group in every),
            "instances": sum(group["instances"] for group in every),
            "groups": len(taking), "reused": len(every) - len(taking),
            "shell_groups": sum(group["shell"] for group in taking),
            "crops": len({group["crop"] for group in taking}),
            "across_places": len({tuple(map(str, group["key"])) for group in taking})}
