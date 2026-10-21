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
# A reading's code row of one of these nouns (" panel" or " plate" after it too) is that shell piece (read_row).
SHELL_NOUNS = {"wall": "kit: wall", "floor": "kit: floor", "ceiling": "kit: ceiling", "roof": "kit: ceiling"}
# A row's route by its noun (owner's rules, CONTEXT.md "layer adapter", "motion", "shell section"): people are models
# of the prop pipeline with the motion layer's steps after; the sky, the effects and the far city have routes of their
# own (layers without models); windows, stairs and building shells are shell pieces (route "shell"); the
# ground itself is the terrain node's (its own rows, CONTEXT.md "layer adapter": no take); every other row, a terrain
# feature too, a model through the prop pipeline.
ROUTES = {"people": {"astronaut", "person", "people", "pedestrian", "crowd", "child", "worker"},
          "sky": {"sky", "planet", "moon"},
          "effects": {"water", "ocean", "puddles", "rain", "smoke", "mist", "plume", "steam", "fog"},
          "skyline": {"city", "cityscape", "city skyline", "skyline"},
          "shell": {"window", "windows", "stairs", "steps", "staircase", "building", "buildings", "building facade",
                    "facade", "exterior wall"},
          "ground": {"ground"}}
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
    of its own, and keeps its own size), None where neither gives one (a gap: its take waits on "no size")."""
    sizes = plan_sizes(store, place, record["inventory"]["rows"])
    return [{**read_row(record, row), "size": sizes.get(row["id"]) or reading_size(row)}
            for row in record["inventory"]["rows"]]


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
    never counts as made), its route by its noun (route_of), and a code row whose noun is a shell word (SHELL_NOUNS)
    that shell piece's kit; every other row, a terrain feature's too, a model through the prop pipeline. A reading
    sizes in metres; its plan's item, his edits counted, gives it first (sized_rows). Its box is SAM 3's, else
    Gemini's (boxed_by)."""
    noun = SHELL_NOUNS.get(row["noun"].removesuffix(" panel").removesuffix(" plate")) if row["kind"] == "code" else None
    return {**row, **boxed_by(record, row), "thing": f"prop:{record['place']}_{row['id']}_{record['concept'][:8]}",
            "route": "shell" if noun else route_of(row["noun"]), **({"group": noun} if noun else {})}


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
    """A reading row's route by its noun (ROUTES), else prop."""
    return next((route for route, nouns in ROUTES.items() if noun.strip().lower() in nouns), "prop")


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
