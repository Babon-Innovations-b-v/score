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

from score.review.plan_checks import AFAR, WALLS_ITEM, afar, at_foot, gemini_box
from score.stages.complete.prepare import contract

SHELL = ("kit: wall", "kit: floor", "kit: ceiling", "kit: under floor")
# A row's route by the part of the place its reading says it is (score/review/reading.py PARTS, never a list of nouns:
# owner, 2026-10-25, "no hax tho ... framework remember"; CONTEXT.md "layer adapter", "motion"): people are models of
# the prop pipeline with the motion layer's steps after (every row the row-kind rules say acts: row_kinds' person
# kind, the one classification, people_of); the sky and the effects have routes of their own (layers without
# models); the far backdrop (route "skyline") is shown from the place of its scene that makes it, else made here as
# models laid far off (shown_from, far_made); the place's ground and water are the terrain node's (no take); its floors, walls, roofs,
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
RUN_SLENDER = 0.25  # tools/props/gates/model.py SLENDER_SHARE: a run's footprint is a line (overruns)
FAR_RUN = 2.0  # a far row this many times longer than deep and tall is a run of pieces (far_made)


def inventories(folder):
    """{place: its scene inventory record} of every <place>.json in `folder` (the design's kept inventories)."""
    return {path.stem: json.loads(path.read_text()) for path in sorted(pathlib.Path(folder).glob("*.json"))}


def current(store, places):
    """({place: its scene inventory}, [place waiting on inventory]) of `places`: each place's current reading
    (score/review/reading.reading_of: read from its picked draw by today's method), its rows as read_row gives them;
    a place with none waits, with no rows and no euros (the old data/inventory files count for nothing here)."""
    from score.review import plans, reading
    found = {place: reading.reading_of(store, place) for place in places}
    read = {place: {**record["inventory"], "rows": sized_rows(store, place, record), "size": record.get("size"),
                    "plan": {"views": [{"id": "v1", "picture": str(blob_path(store, record["concept"]))}]}}
            for place, record in found.items() if record}
    return ({place: {**record, "rows": shown_from(place, record["rows"], read, plans.KEPT)}
             for place, record in read.items()},
            sorted(place for place, record in found.items() if not record))


def shown_from(place, rows, read, folder):
    """The place's rows, each backdrop row (route "skyline") that a place of its scene makes as a model marked
    `shown`: {place, row} of that place's row (source_of), the object made, bought and laid where it stands and stood
    in this place's stage with that place (the scene record's `places`, the neighbours stage), never a second take.
    A backdrop row no place of its scene makes is an ordinary model made here and laid far off (far_made); a top
    scene's own backdrop rows are made there, so a place it holds shows them from it (the stairwell's city skyline
    is the square's)."""
    others = [(other, [far_made(row) if not scene_places(other, folder) else row for row in read[other]["rows"]])
              for other in scene_places(place, folder) if other in read]
    found = []
    for row in rows:
        source = source_of(row, others) if row["route"] == ROUTES["backdrop"] else None
        found.append({**row, "shown": {"place": source[0], "row": source[1]}} if source else far_made(row))
    return found


def far_made(row):
    """A backdrop row (route "skyline") as an ordinary model made through the prop pipeline and laid far off by the
    scene record where its concept box is seen, at its true distance (scene_record/far.py; the owner, 2026-10-26: "the
    skyline is world1's own scenes at their real distance, plus ordinary objects for anything that isn't a scene"),
    marked `far`: {pieces, length}. One whose footprint is a line FAR_RUN times longer than it is deep or tall (a
    city's skyline) is a run of repeating pieces, each as long as it is tall, so its close-up is drawn and checked at
    one piece (its size and read size); one of a single piece is as wide as its concept box shows it (seen_size); any
    other row is returned as it is."""
    if row["route"] != ROUTES["backdrop"]:
        return row
    size = reading_size(row)
    if size is None:
        return {**row, "route": "prop", "far": {"pieces": 1, "length": 0.0}}
    long, short, tall = max(size[:2]), min(size[:2]), size[2]
    pieces = max(1, round(long / max(short, tall))) if long >= FAR_RUN * max(short, tall) else 1
    piece = [round(long / pieces, 3), short, tall] if size[0] >= size[1] else [short, round(long / pieces, 3), tall]
    piece = seen_size(piece, row) if pieces == 1 else piece
    return {**row, "route": "prop", "size": piece, "read_size": piece, "far": {"pieces": pieces, "length": long}}


def seen_size(size, row):
    """A far row's [wide, deep, tall] as its SAM 3 box shows it: its read tall kept (scene_record/far.spot stands it
    where that tall rises to its box's height) and its footprint scaled so its longer side is as wide as the box shows
    at that distance (tall times the box's width over its height: far off and near level, the painting is the
    object's outline). A reading sizes a far speck's core, never its outline: the square's 60 m rocket read 5 m wide,
    12:1, while its box (boosters and fins) is 3.8:1, and Batch 1's benchmark of 2026-10-26 failed its one clean take
    on that alone. A Gemini region, loose round its thing, or no box keeps the size."""
    box = row.get("box") if row.get("boxed_by") == "SAM 3" else None
    if not box or box[2] <= box[0] or box[3] <= box[1]:
        return size
    scale = size[2] * (box[2] - box[0]) / (box[3] - box[1]) / max(size[:2])
    return [round(size[0] * scale, 3), round(size[1] * scale, 3), size[2]]


def scene_places(place, folder):
    """The other places of the scene the place stands in, nearest first: the scene holding it, then the places that
    scene's plan lays out beside it (the kept plans' `holds`), the ones the scene record can stand in this place's
    stage where its holder's plan holds them (score/stages/scene_record/writer.places_of)."""
    for path in sorted(pathlib.Path(folder).glob("*.json")):
        held = [hold["place"] for hold in json.loads(path.read_text()).get("holds") or []]
        if place in held:
            return [path.stem, *sorted(name for name in set(held) if name != place)]
    return []


def source_of(row, others):
    """(place, row id) of the model row of `others` ([(place, rows)], nearest first) that a backdrop row is: one of the
    same object kind, else the nearest whose kind's words hold the row's or are held in them (kind_words: the
    stairwell's palm_tree is the square's palm_tree, the street's distant_rocket the square's rocket), else, for a
    part of a structure, the structure holding it (structure_of); None."""
    made = [(other, found["id"]) for other, rows in others for found in rows if found["route"] in MODEL_ROUTES]
    words = kind_words(row["id"])
    return next((source for source in made if object_kind(source[1]) == object_kind(row["id"])), None) or next(
        (source for source in made if words and kind_words(source[1])
         and (words <= kind_words(source[1]) or kind_words(source[1]) <= words)), None) or (
        structure_of(row, others))


def structure_of(row, others):
    """(place, row id) of the nearest structure of `others` that shows a backdrop row which is a part of a structure,
    its reading's anchor a wall (a window, door, sign, balcony or facade light) or its part a shell's (a wall, roof,
    opening or other structure of a building seen beyond): a shell row standing on the ground taller than the part
    (a building, tower, facade, wall), whose finish gives the part its look, a lit window its glow (the glow
    reading); None for any other row, or with no such structure (Batch 1: the stairwell's lit and dark windows of the
    buildings seen through its window are the square's buildings'; 2026-10-26: the white exterior wall seen through
    the tube's glass is the base's buildings')."""
    if row.get("anchor") != "wall" and ROUTES.get(row.get("part")) != "shell":
        return None
    tall = (row.get("size") or [0, 0, 0])[2]
    return next(((other, found["id"]) for other, rows in others for found in rows
                 if found["route"] == "shell" and found.get("anchor") == "ground"
                 and (found.get("size") or [0, 0, 0])[2] > tall), None)


def kind_words(row_id):
    """The words of a row's object kind, each singular (a trailing s off, never off ss), less the words saying it is
    seen far off (plan_checks.AFAR: where it is, not what: the street's distant_floodlight is the square's floodlight
    tower)."""
    return frozenset(re.sub(r"(?<!s)s$", "", word) for word in object_kind(row_id).split("_") if word) - AFAR


def sized_rows(store, place, record):
    """A reading's rows as read_row gives them, each with its size (row_size: the object's own metres) and its
    `read_size`, the object's own metres as its reading gave them (None where it gave
    none): the close-up's request and shape check hold the object to its own size (owner, 2026-10-24). A row the
    reading and the plan give no size has none (a gap: its take waits on "no size"). A shell piece whose part the
    place's plan lays itself (plan_parts), that it names its own shell (plan_structure), or that is arched structure
    at its plan items (plan_arches), has route "plan"."""
    from score.review import plans
    rows = record["inventory"]["rows"]
    laid = plan_sizes(store, place, rows)
    shown = plans.current(store, place)
    own = plan_parts(shown and shown["plan"])
    shell = plan_structure(shown and shown["plan"], own)
    beyond = beyond_of(shown and shown["plan"], rows, record.get("size"))
    found = [{**read_row(record, row), "size": row_size(reading_size(row), laid.get(row["id"]),
                                                         run_pieces(shown and shown["plan"], row)),
              "read_size": own_size(reading_size(row), laid.get(row["id"]), run_pieces(shown and shown["plan"], row))}
             for row in rows]
    return [routed(row, own, beyond, shell | plan_arches(shown and shown["plan"], found)) for row in found]


def plan_arches(plan, rows):
    """The ids of the arched structure rows (a tube's ribs) the plan's shell lays at their plan items
    (score/stages/earth_seed/design_shell.arches, as the scene record lays them): the plan's own, never a close-up
    (Batch 1's retry: the tube's ribs, their box the whole picture, framed none)."""
    from score.stages.earth_seed import design_shell
    return {row["id"] for row, _, _ in design_shell.arches(plan or {}, rows)}


def beyond_of(plan, rows, picture):
    """The ids of a reading's rows the place shows beyond it: the plan's `beyond`, every row the reading names
    seen far off (plan_checks.afar, the rows the plan checks leave outside the place on purpose: the street's distant
    floodlights, flags and palms in the square past its end, which its plan laid in the street and Batch 1 try 4 drew
    close-ups of from a speck), and every row it anchors in the sky (reading.ANCHORS: a planet, a moon, a backdrop;
    plan_checks.whole leaves it out of the place: the square's launching rocket over the sea, which its plan left off
    `beyond`, so its close-up took the room and Pro drew the whole square on three of four takes, 2026-10-26), less
    each standing on a row laid here (stood_beyond), at the picture's foot (at_foot) or stood here at a plan person
    spot (its `people` [x, y, facing, row]: the lab's three people at their desks, listed beyond too, 2026-10-30)."""
    sky = {row["id"] for row in rows if row.get("anchor") == "sky"}
    stood = {spot[3] for spot in (plan or {}).get("people") or [] if len(spot) >= 4}
    return stood_beyond(rows, set((plan or {}).get("beyond") or []) | afar({"rows": rows}) | sky) - at_foot(
        rows, picture) - stood


def stood_beyond(rows, beyond):
    """The plan's `beyond` ids less each row standing on a row of the place laid here (its anchor "on:<id>", that row
    itself not beyond): an object on the place's own staircase is the place's, whatever the plan said (2026-10-26: the
    stairwell's man and woman on its stairs were listed beyond, and nothing made them)."""
    anchors = {row["id"]: str(row.get("anchor") or "").partition("on:")[2] for row in rows}
    found = set(beyond)
    moved = True
    while moved:
        here = {row_id for row_id in found if anchors.get(row_id) in anchors and anchors[row_id] not in found}
        found -= here
        moved = bool(here)
    return found


def plan_structure(plan, own):
    """The ids of the rows a plan that lays its place's walls (`own`, plan_parts) names its place's own shell
    (its `structure`: drawn as walls, levels and roofs, never an item; score/review/plan_writing.py), none else."""
    return set((plan or {}).get("structure") or []) if "wall" in own else set()


def routed(row, own, beyond, shell=frozenset()):
    """A sized row with its plan's route: a shell piece whose part the plan lays itself (`own`), or that the plan
    names its own shell where it lays its walls (`shell`, plan_structure: the stairwell's 12 m building shell, whose
    box is the whole picture, Batch 1's retry), is the plan's, never a close-up; a model
    row the plan says the painting shows beyond the place (`beyond`: through a window, past its edge, far off; never
    placed here, plan_writing) is the backdrop's (route "skyline"), never a close-up of a far speck (Batch 1 try 4:
    the stairwell's palms, street lamps and lanterns seen through its window, the street's far rocket); a landform of
    the far ground beyond it (terrain.design.far_row: the campgrounds' distant hills) is the terrain node's (route
    "ground"), raised on the far ground round the place, and so is a body of water (terrain.design.water_row: the
    square's sea), laid as water over the ground lowered under it (shown_from makes every other backdrop row a
    model)."""
    import score.stages.terrain.design as design  # by module: terrain's make stays out of this key
    if design.far_row(row, beyond) or design.water_row(row):
        return {**row, "route": ROUTES["ground"]}
    if row["route"] == "shell" and (row.get("part") in own or row["id"] in shell):
        return {**row, "route": "plan"}
    if row["route"] in MODEL_ROUTES and row["id"] in beyond:
        return {**row, "route": ROUTES["backdrop"]}
    return row


def row_size(own, laid, pieces=None):
    """A row's size: the object's own metres from its reading (`own`), else its plan item's (`laid`: a row the reading
    gave none). A plan's item is the footprint the object is laid in (a run of things, room round it: the airlock's
    porch post laid 0.48 by 1.7 m, a 0.1 by 0.1 m post), so it only places the object, never sizes its model
    (coordinator, 2026-10-25), his edited items too: the plan is an estimate and the assembly fits each object to what
    it is laid by (owner, 2026-10-29; #72). An edit counted as his sizing wherever the plan shown differed from the plan
    made since, so a whole plan re-written after it, or a footprint off by a rounding, sized 17 of hangar's 30 rows
    (its spaceship 13.7 by 46 m against its reading's 8 by 24, its office chair 2.1 m) and 3 of habitat's (2026-10-29). A row the plan lays as a run (`pieces`, run_pieces)
    whose own metres overrun its item by a piece measured the whole run (a railing round a floor, pipes along a wall:
    overruns): it is made as one repeating piece laid along the item (run_piece), never as one object the run's
    length."""
    return own_size(own, laid, pieces) or laid


def own_size(own, laid, pieces=None):
    """The object's own metres, the size its close-up is drawn and checked at (`read_size`): its reading's (`own`),
    but one repeating piece (run_piece) of a run the reading measured whole (overruns), so the close-up draws the
    piece, never the 50 m railing (Batch 1 try 4: the greenhouse's railing)."""
    if own and laid and pieces and overruns(own, laid, pieces):
        return run_piece(own, laid, pieces)
    return own


def run_pieces(plan, row):
    """How many pieces a row the plan lays as a run or path is made of: its reading's count, or its items' on the
    plan (several items, an item counting several), whichever is more; at least 1 for one laid as a path (a polygon
    round a floor's edge). None for a row laid as one object (one item of one, a rect), or as one of it an item
    (one_each)."""
    tied = (plan or {}).get("rows") or {}
    names = [name for name, *_ in (plan or {}).get("items", []) if row["id"] in (tied.get(name) or [])]
    shapes = [(plan.get("shapes") or {}).get(name) or {} for name in names]
    if one_each(plan, names, shapes, reading_size(row)):
        return None
    pieces = max(row.get("count") or 1, sum(shape.get("count", 1) for shape in shapes))
    return pieces if pieces > 1 or any(shape.get("shape") == "polygon" for shape in shapes) else None


def one_each(plan, names, shapes, own):
    """Whether a row's several items (`names`, their `shapes`) each lay one of it, its reading's metres (`own`) one
    object's (score/review/reading.py: "of one of it"): no item counts several, and its long side is within their long
    sides end to end, so it never measured a run longer than all of them (2026-10-26: habitat's 10 rugs of 2 m, each
    laid in its own 1.4 m item, were cut to 0.2 m strips, its 6 curtains and square's flags and street's palms so too)."""
    if len(names) < 2 or own is None or any(shape.get("count", 1) > 1 for shape in shapes):
        return False
    long_sides = {name: max(wide, deep) for name, _, _, wide, deep, *_ in plan["items"]}
    return max(own[:2]) <= sum(long_sides[name] for name in names)


def overruns(size, laid, pieces):
    """Whether a reading measured a whole run of `pieces`, not one object: a line along the ground (its footprint's
    short side under RUN_SLENDER of its long side: a railing, pipes, a string of lanterns) whose long side holds the
    laid item's long side and one more of its pieces. An object a little longer or deeper than the footprint it is
    laid in, or one no line, is that object at its own size (2026-10-26: the cockpit's four 1.2 m rear doors on a
    1.16 m item were cut to 0.3 m)."""
    short, long = sorted(size[:2])
    return short < RUN_SLENDER * long and long * (1 - 1 / pieces) >= max(laid[:2])


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


def plan_sizes(store, place, rows):
    """{row id: [wide, deep, tall] metres} of the reading's `rows` the place's current plan sizes
    (score/review/plans.current: his newest edit on the pick, else the derived plan, whose items are sized by the
    reading's metres), each from the first item tied to it: its
    wide and deep as laid (turned back for one facing east or west), its tall the reading's, else off its surest SAM
    box at the scale its wide gives the box (an item he sized whose row the reading gave no size). A row whose item
    is a size gap on its plan, or with no item of its own (on a wall, in the sky, riding on another row: `sized_rows`
    gives it its reading's), has none here."""
    from score.review import plans
    shown = plans.current(store, place)
    if shown is None:
        return {}
    plan, by_id = shown["plan"], {row["id"]: row for row in rows}
    unsized = {gap["item"] for gap in plan.get("gaps", []) if gap.get("kind") == "size"}
    found = {}
    for name, _, _, wide, deep, facing, kind in plan.get("items", []):
        tied = (plan.get("rows") or {}).get(name) or []
        if kind != "item" or name == WALLS_ITEM or name in unsized or not tied or tied[0] in found:
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
            "box": row.get("box"), "reuse": row.get("reuse"), "shown": row.get("shown")}


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
