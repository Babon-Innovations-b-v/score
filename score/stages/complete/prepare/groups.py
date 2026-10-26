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
# A row's route by the part of the place its reading says it is (score/review/reading.py PARTS, never a list of nouns:
# owner, 2026-10-25, "no hax tho ... framework remember"; CONTEXT.md "layer adapter", "motion"): people are models of
# the prop pipeline with the motion layer's steps after (every row the row-kind rules say acts: row_kinds' person
# kind, the one classification, people_of); the sky, the effects and the far backdrop have routes of their own
# (layers without models); the place's ground itself is the terrain node's (no take); its floors, walls, roofs,
# openings and other structure are shell pieces (route "shell"), or the plan's own where its shell lays that piece
# for this place (plan_parts: route "plan", no take); every other row, a feature lying on the land too, a model
# through the prop pipeline.
ROUTES = {"object": "prop", "floor": "shell", "wall": "shell", "roof": "shell", "opening": "shell",
          "structure": "shell", "ground": "ground", "sky": "sky", "effect": "effects", "backdrop": "skyline"}
# A floor, wall or roof row is that shell piece's kit.
KITS = {"floor": "kit: floor", "wall": "kit: wall", "roof": "kit: ceiling"}
# The part each piece of a plan's shell lays (score/stages/earth_seed/design_shell.pieces and levels, by part_kind).
PIECE_PARTS = {"deck": "floor", "level": "floor", "wall": "wall", "roof": "roof"}
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
    """A reading's rows as read_row gives them, each with its size (row_size: the object's own metres, unless his plan
    edit sized its item) and its `read_size`, the object's own metres as its reading gave them (None where it gave
    none): the close-up's request and shape check hold the object to its own size (owner, 2026-10-24). A row the
    reading and the plan give no size has none (a gap: its take waits on "no size"). A shell piece whose part the
    place's plan lays itself has route "plan" (plan_parts)."""
    from score.review import plans
    rows = record["inventory"]["rows"]
    laid, made = plan_sizes(store, place, rows), plan_sizes(store, place, rows, made=True)
    shown = plans.current(store, place)
    own = plan_parts(shown and shown["plan"])
    beyond = set((shown and shown["plan"] or {}).get("beyond") or [])
    found = [{**read_row(record, row), "size": row_size(reading_size(row), laid.get(row["id"]), made.get(row["id"]),
                                                         run_pieces(shown and shown["plan"], row)),
              "read_size": own_size(reading_size(row), laid.get(row["id"]), run_pieces(shown and shown["plan"], row))}
             for row in rows]
    return [routed(row, own, beyond) for row in found]


def routed(row, own, beyond):
    """A sized row with its plan's route: a shell piece whose part the plan lays itself (`own`) is the plan's; a model
    row the plan says the painting shows beyond the place (`beyond`: through a window, past its edge, far off; never
    placed here, plan_writing) is the backdrop's (route "skyline"), never a close-up of a far speck (Batch 1 try 4:
    the stairwell's palms, street lamps and lanterns seen through its window, the street's far rocket)."""
    if row["route"] == "shell" and row.get("part") in own:
        return {**row, "route": "plan"}
    if row["route"] in MODEL_ROUTES and row["id"] in beyond:
        return {**row, "route": ROUTES["backdrop"]}
    return row


def row_size(own, laid, made, pieces=None):
    """A row's size: its item's on the plan shown where his edit sized it (`laid` not the plan made without him's,
    `made`: his edits count, owner 2026-10-21), else the object's own metres from its reading (`own`), else its item's
    (an item he sized whose row the reading gave none). A plan's item is the footprint the object is laid in (a run
    of things, room round it: the airlock's porch post laid 0.48 by 1.7 m, a 0.1 by 0.1 m post), so it only places
    the object, never sizes its model (coordinator, 2026-10-25). A row the plan lays as a run or path (`pieces`,
    run_pieces) whose own metres do not fit its item measured the whole run (a railing round a floor, pipes along a
    wall): it is made as one repeating piece laid along the item (run_piece), never as one object the run's length."""
    if laid and laid != made:
        return laid
    return own_size(own, laid, pieces) or laid


def own_size(own, laid, pieces=None):
    """The object's own metres, the size its close-up is drawn and checked at (`read_size`): its reading's (`own`),
    but one repeating piece (run_piece) of a run the reading measured whole, so the close-up draws the piece, never
    the 50 m railing (Batch 1 try 4: the greenhouse's railing)."""
    if own and laid and pieces and not within(own, laid):
        return run_piece(own, laid, pieces)
    return own


def run_pieces(plan, row):
    """How many pieces a row the plan lays as a run or path is made of: its reading's count, or its items' on the
    plan (several items, an item counting several), whichever is more; at least 1 for one laid as a path (a polygon
    round a floor's edge). None for a row laid as one object (one item of one, a rect)."""
    tied = (plan or {}).get("rows") or {}
    names = [name for name, *_ in (plan or {}).get("items", []) if row["id"] in (tied.get(name) or [])]
    shapes = [(plan.get("shapes") or {}).get(name) or {} for name in names]
    pieces = max(row.get("count") or 1, sum(shape.get("count", 1) for shape in shapes))
    return pieces if pieces > 1 or any(shape.get("shape") == "polygon" for shape in shapes) else None


def within(size, laid):
    """Whether a size's wide and deep fit a laid footprint's, turned or not."""
    return all(side <= room for side, room in zip(sorted(size[:2]), sorted(laid[:2])))


def run_piece(own, laid, pieces):
    """One repeating piece of a run whose reading measured the whole run (`own`, longer than the item it is laid in):
    its long side the run's over its `pieces`, each side held to the laid item's (the piece is laid along it), its
    tall the reading's."""
    long = 0 if own[0] >= own[1] else 1
    room_long, room_short = sorted(laid[:2], reverse=True)
    piece = list(own)
    piece[long] = round(min(own[long] / pieces, room_long), 3)
    piece[1 - long] = round(min(own[1 - long], room_short), 3)
    return piece


def plan_parts(plan):
    """The parts of its place a plan's shell lays itself (score/stages/earth_seed/design_shell: the earth seed or the
    scene record lays them): an enclosed place's decks, walls and roofs, and the openings cut in its walls where it
    writes any; an open place's raised levels (floors); nothing without a plan."""
    from score.stages.earth_seed import design_shell
    if not plan:
        return set()
    if design_shell.laid_for(plan) or design_shell.encloses(plan):
        found = {PIECE_PARTS[design_shell.part_kind(name)] for name, _, _ in design_shell.pieces(plan)}
        return found | ({"opening"} if plan.get("openings") or plan.get("doors") else set())
    return {"floor"} if design_shell.levels(plan) else set()


def reading_size(row):
    """A reading row's [wide, deep, tall] metres (score/review/reading.py METHOD 4), None when it gave none."""
    size = row.get("size")
    return list(size) if sides(size) else None


def plan_sizes(store, place, rows, made=False):
    """{row id: [wide, deep, tall] metres} of the reading's `rows` the place's current plan sizes
    (score/review/plans.current: his newest edit on the pick, else the derived plan, whose items are sized by the
    reading's metres; `made`: the plan made without him, plans.made_plan), each from the first item tied to it: its
    wide and deep as laid (turned back for one facing east or west), its tall the reading's, else off its surest SAM
    box at the scale its wide gives the box (an item he sized whose row the reading gave no size). A row whose item
    is a size gap on its plan, or with no item of its own (on a wall, in the sky, riding on another row: `sized_rows`
    gives it its reading's), has none here."""
    from score.review import plans
    shown = (plans.made_plan if made else plans.current)(store, place)
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
    never counts as made), its route by its part (route_of), and a floor, wall or roof that piece's kit (KITS). A
    reading sizes in metres; its plan's item, his edits counted, gives it first (sized_rows). Its box is SAM 3's,
    else Gemini's (boxed_by)."""
    kit = KITS.get(row.get("part"))
    return {**row, **boxed_by(record, row), "thing": f"prop:{record['place']}_{row['id']}_{record['concept'][:8]}",
            "route": route_of(row), **({"group": kit} if kit else {})}


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


def route_of(row):
    """A reading row's route: people where the row-kind rules say it acts (people_of), else its part's (ROUTES); None
    for a row whose part is not read (a reading answered before it was asked: contract.faults makes its take an input
    gap until `python -m score.review.reading <place>` asks it, reading.parted)."""
    return "people" if people_of(row["noun"]) else ROUTES.get(row.get("part"))


def people_of(noun):
    """Whether a noun names people: its whole noun or its last word, as written or singular, is a noun of a row kind
    that acts (score/stages/row_kinds.py, data/checks/row-kinds.json: person, man, women, pilot...)."""
    from score.stages import row_kinds
    kinds = row_kinds.table()
    words = row_kinds.words(noun).split()
    last = words[-1] if words else ""
    return any("acts" in row_kinds.does(row_kinds.kind_of({"noun": wanted}, kinds), kinds)
               for wanted in {" ".join(words), last, singular(last)} if wanted)


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
