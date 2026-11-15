"""The terrain kit (#128, D2: terrain pieces are code-made library entries, so no paid model making is needed for
them; the owner, 2026-11-15: "NO TERRAIN or terrain assets"): the ground's own pieces, made by code from a top
scene's kept plan and scene inventory and laid into its ground as reliefs, as the plan's terrain spots are.

    pieces = kit.laid(ground, plans, inventories, recipe)    # {"reliefs": [(source, relief)], "rocks": {"anchor",
                                                              #  "rocks"}, "record": [...]}
    rocks = kit.rock_mesh(ground, place, pieces["rocks"], shaped)   # (points, triangles) in its frame, or None

The pieces of every top scene on a ground, one relief in its first top scene's plan metres (the tops on a body stand
within metres of each other; design.relief_at reads it like a terrain spot's):
    crater   a bowl with a raised rim (a simple crater's profile: depth DEPTH_SHARE of its breadth at most, the rim
             RIM_SHARE of its depth, falling off as the cube of the distance past it), one each plan item of a
             crater row at its box, else the row's count scattered round the plan at its read size
    track    two ruts (a tyre row) or one wide groove (a skid row) on a gentle curve: along each plan item's box,
             else out from the plan's vehicle to past its edge
    field    the natural ground's own relief (only on a natural ground: a made one, the square's plaza, stays level):
             low waves and small craters pocking it on regolith (an airless body's impacts), drifts on sand, rising
             past the plan's box to ridges, terraced into mesas and cliffs on sand, fading to nothing FIELD_REACH out
    rocks    scattered stones, many small and few large (a power law), on the ground's natural ground, each a
             jittered icosphere sunk a share of its height into the ground, written as one mesh, a static collider,
             finished with the library's `rock` recipe
Every piece is level where people walk and things stand (`level_share`): zero within LEVEL_MARGIN of each plan item
that is no terrain row, each place the plan holds, each person spot and each terrain spot, rising over LEVEL_BLEND
(a crater the plan lays an item for only round the things themselves, PLANNED_MARGIN); no rock lies there. Seeds
come from the row's id and the body, so the same design gives the same ground. A made ground's recipe by its words:
`made_recipe`.
"""
import json
import math
import pathlib
import re
import zlib

import numpy as np

from score.stages.scene_record import plan as place_plan

ADDRESS = "algorithm/terrain_kit@1"  # the library entry this kit is (score_lib definitions/algorithms/terrain_kit)
NATURAL = ("regolith", "sand", "rock", "ice")  # the natural grounds whose field and rocks the kit lays
CRATER_WORDS = {"crater", "craters"}
TRACK_WORDS = {"track", "tracks", "tyre", "tire", "rut", "ruts", "wheel"}
SKID_WORDS = {"skid", "skids", "scrape", "gouge", "furrow"}
VEHICLE_WORDS = {"rover", "vehicle", "buggy", "truck", "car", "lander", "rocket", "wreck", "crawler"}
DEPTH_SHARE = 0.2   # a simple crater is at most a fifth as deep as it is broad
RIM_SHARE = 0.3     # its rim stands this share of its depth over the ground round it
RIM_FADE = 3.0      # its rim's fall-off ends this many radii out
TRACK_GAUGE = 1.8   # metres between a tyre track's two ruts
TRACK_WIDE, TRACK_DEEP = 0.5, 0.07   # one rut's breadth and depth (metres)
SKID_WIDE, SKID_DEEP = 1.4, 0.15     # a skid's groove
LEVEL_MARGIN = 1.5  # metres kept level round each thing standing on the ground
LEVEL_BLEND = 4.0   # over which the kit's relief rises again
PLANNED_MARGIN, PLANNED_BLEND = 0.4, 1.2  # a crater the plan lays keeps only the things themselves level
FIELD_REACH = 250.0   # the field fades to nothing this far past the plan's box
RISE_FROM, RISE_OVER = 10.0, 40.0   # the field rises from this far past the box over this many metres
# per natural ground: its waves' height inside the plan and past its rise, their length, terraced (mesas), and its
# pocks (small craters a square metre) and rocks (a square metre) and its largest rock's radius (metres)
FIELDS = {"regolith": {"inside": 0.25, "outside": 1.6, "wave": 22.0, "terraced": False, "pocks": 1 / 300,
                       "rocks": 0.05, "largest": 0.6},
          "sand": {"inside": 0.3, "outside": 12.0, "wave": 70.0, "terraced": True, "pocks": 0.0, "rocks": 0.04,
                   "largest": 1.2},
          "rock": {"inside": 0.3, "outside": 5.0, "wave": 40.0, "terraced": True, "pocks": 0.0, "rocks": 0.08,
                   "largest": 1.0},
          "ice": {"inside": 0.15, "outside": 2.0, "wave": 35.0, "terraced": False, "pocks": 0.0, "rocks": 0.01,
                  "largest": 0.5}}
POCKS_PAST = 120.0   # pocks lie out to this far past the plan's box
ROCKS_PAST = 60.0    # rocks lie out to this far past the plan's box
SMALLEST_ROCK = 0.05
SUNK = 0.35          # a rock sinks this share of its height into the ground
TERRACES = 3
REGION_SHARE = 0.5   # an item over this share of its plan's area is a region, not a piece's place
# A made ground's library recipe by its row's words (natural_grounds.MADE gives it none): a road's asphalt, else
# paving's tiles (the square's plaza: pale stone slabs in its concept)
MADE_RECIPES = (("wet_asphalt", {"asphalt", "road", "street", "tarmac"}),
                ("tiles", {"plaza", "square", "pavement", "paving", "paved", "tiles", "tiled", "courtyard", "deck",
                           "floor", "pad", "platform", "runway", "concrete"}))


def made_recipe(row):
    """(the library recipe a made ground is finished with, why) by its row's words, else (None, None)."""
    found = words(row)
    for recipe, said in MADE_RECIPES:
        if found & said:
            word = sorted(found & said)[0]
            return recipe, f"the row {row.get('id')} says {word}: a made ground, the library's {recipe}"
    return None, None


def seed_of(*words):
    """A seed from words (the same design, the same ground)."""
    return zlib.crc32(" ".join(str(word) for word in words).encode())


def rows_of(inventories, place):
    """{row id: row} of a place's kept scene inventory ({} with none)."""
    path = pathlib.Path(inventories) / f"{place}.json"
    return {row["id"]: row for row in json.loads(path.read_text())["rows"]} if path.is_file() else {}


def words(row):
    """A row's words: its id's, name's and noun's."""
    return set(re.findall(r"[a-z]+", f"{row.get('id', '')} {row.get('name') or ''} {row.get('noun') or ''}".lower()))


def piece_of(row):
    """Which kit piece a terrain row is: crater, track, skid, or None."""
    if not row.get("terrain"):
        return None
    found = words(row)
    if found & CRATER_WORDS:
        return "crater"
    if found & SKID_WORDS:
        return "skid"
    if found & TRACK_WORDS:
        return "track"
    return None


def items_of(plan):
    """[(name, row ids, (x0, y0, x1, y1))] of a plan's items, each box in plan metres."""
    rows = plan.get("rows") or {}
    found = []
    for item in plan.get("items") or []:
        name, left, top, wide, deep = item[0], *(float(value) for value in item[1:5])
        found.append((name, rows.get(name) or [], (left, top, left + wide, top + deep)))
    return found


def hold_box(hold, plans):
    """A held place's box on its holder's plan (x0, y0, x1, y1)."""
    plan = plans.get(hold["place"]) or {}
    wide, deep = (hold.get("w"), hold.get("d")) if "w" in hold and "d" in hold else \
        place_plan.laid_size(hold, plan) if plan else (0.0, 0.0)
    return float(hold["x"]), float(hold["y"]), float(hold["x"]) + float(wide), float(hold["y"]) + float(deep)


def level_zones(plan, plans, rows):
    """Where the plan's ground stays level: ([(x0, y0, x1, y1)] boxes of its things and held places, [(x, y, radius)]
    of its person and terrain spots); a terrain row's item and a region (base's "on the walls and ceiling" over the
    whole plan) none."""
    boxes = [box for _, item_rows, box in items_of(plan)
             if not region(box, plan) and not any(rows.get(row, {}).get("terrain") for row in item_rows)]
    boxes += [hold_box(hold, plans) for hold in plan.get("holds") or []]
    spots = [(float(spot[0]), float(spot[1]), 1.0) for spot in plan.get("people") or []]
    spots += [(float(spot[0]), float(spot[1]), 1.5) for spot in (plan.get("terrain") or {}).get("spots") or []]
    return boxes, spots


def level_share(points, zones, margin=LEVEL_MARGIN, blend=LEVEL_BLEND):
    """Over plan points [[x, y]], 0 where the ground stays level (within `margin` of a zone), rising smoothly to 1
    `blend` past it."""
    points = np.atleast_2d(points)
    boxes, spots = zones
    nearest = np.full(len(points), np.inf)
    for left, top, right, bottom in boxes:
        across = np.maximum.reduce([left - points[:, 0], np.zeros(len(points)), points[:, 0] - right])
        along = np.maximum.reduce([top - points[:, 1], np.zeros(len(points)), points[:, 1] - bottom])
        nearest = np.minimum(nearest, np.hypot(across, along))
    for x, y, radius in spots:
        nearest = np.minimum(nearest, np.maximum(np.hypot(points[:, 0] - x, points[:, 1] - y) - radius, 0.0))
    share = np.clip((nearest - margin) / blend, 0.0, 1.0)
    return share * share * (3.0 - 2.0 * share)


def crater_height(apart, radius, depth):
    """A simple crater's height at distances `apart` from its middle: a bowl `depth` deep from its rim, the rim
    RIM_SHARE of its depth over the ground, falling off past it as the cube of the distance, to nothing RIM_FADE
    radii out."""
    rim = RIM_SHARE * depth
    share = apart / radius
    inside = rim - depth + depth * share ** 2
    outside = rim * (np.maximum(share, 1.0) ** -3 - RIM_FADE ** -3) / (1.0 - RIM_FADE ** -3)
    return np.where(share < 1.0, inside, np.where(share < RIM_FADE, outside, 0.0))


def crater_depth(row, breadth):
    """A crater's depth at a breadth: its row's read depth scaled to that breadth, never deeper than DEPTH_SHARE."""
    size = row.get("size") or []
    if len(size) == 3 and size[0] and size[2]:
        depth = float(size[2]) * breadth / float(max(size[0], size[1]))
    else:
        depth = 0.12 * breadth
    return min(depth, DEPTH_SHARE * breadth)


def ruts_height(apart, piece):
    """A track's height at distances `apart` across it from its line: two ruts TRACK_GAUGE apart, or one skid."""
    if piece == "skid":
        return -SKID_DEEP * np.exp(-(apart / (SKID_WIDE / 2)) ** 2 * 2.0)
    return -TRACK_DEEP * np.exp(-((np.abs(apart) - TRACK_GAUGE / 2) / (TRACK_WIDE / 2)) ** 2 * 2.0)


def curve(start, end, bend):
    """A gentle curve [[x, y]] from start to end, its middle pushed `bend` of its length to one side."""
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    way = end - start
    side = np.array([-way[1], way[0]])
    control = (start + end) / 2 + side * bend
    steps = np.linspace(0.0, 1.0, max(8, int(np.hypot(*way) / 0.5)))[:, None]
    return (1 - steps) ** 2 * start + 2 * (1 - steps) * steps * control + steps ** 2 * end


def apart_from_line(points, line):
    """Each point's signed distance from a line [[x, y]] (plus left of its way), and whether it lies along it."""
    best = np.full(len(points), np.inf)
    signed = np.zeros(len(points))
    for one, two in zip(line[:-1], line[1:]):
        way = two - one
        length = float(way @ way) or 1.0
        share = np.clip(((points - one) @ way) / length, 0.0, 1.0)
        offset = points - (one + share[:, None] * way)
        apart = np.hypot(offset[:, 0], offset[:, 1])
        closer = apart < best
        best = np.where(closer, apart, best)
        cross = way[0] * offset[:, 1] - way[1] * offset[:, 0]
        signed = np.where(closer, np.sign(cross) * apart, signed)
    return signed, best


def vehicle_middle(plan, rows_of_place):
    """The middle of the plan's first item a vehicle row is (VEHICLE_WORDS), else the plan's middle."""
    for _, item_rows, (left, top, right, bottom) in items_of(plan):
        if any(words(rows_of_place.get(row, {"id": row})) & VEHICLE_WORDS for row in item_rows):
            return np.array([(left + right) / 2, (top + bottom) / 2])
    return np.array([float(plan["w"]) / 2, float(plan["d"]) / 2])


def track_lines(plan, row, rows_of_place, item_boxes):
    """The lines a track row's ruts run along: each item box's diagonal, else out from the plan's vehicle past its
    edge (away from the plan's middle)."""
    rng = np.random.default_rng(seed_of("track", row["id"]))
    lines = [curve((left, bottom), (right, top), rng.uniform(-0.15, 0.15)) for left, top, right, bottom in item_boxes]
    if lines:
        return lines
    middle = np.array([float(plan["w"]) / 2, float(plan["d"]) / 2])
    start = vehicle_middle(plan, rows_of_place)
    way = start - middle if np.hypot(*(start - middle)) > 1.0 else np.array([0.0, 1.0])
    reach = max(float(plan["w"]), float(plan["d"]))
    found = []
    for turn in rng.uniform(-0.6, 0.6, size=max(1, int(row.get("count") or 1))):
        cos, sin = math.cos(turn), math.sin(turn)
        heading = np.array([cos * way[0] - sin * way[1], sin * way[0] + cos * way[1]])
        found.append(curve(start, start + heading / np.hypot(*heading) * reach, rng.uniform(-0.15, 0.15)))
    return found


def scattered(plan, count, breadth, zones, seed):
    """`count` crater middles round the plan, each its whole rim on ground left level by nothing (level_share 1)."""
    rng = np.random.default_rng(seed)
    wide, deep = float(plan["w"]), float(plan["d"])
    found = []
    for _ in range(200 * count):
        if len(found) == count:
            break
        spot = rng.uniform([-0.3 * wide, -0.3 * deep], [1.3 * wide, 1.3 * deep])
        ring = spot + breadth / 2 * np.array([[1, 0], [-1, 0], [0, 1], [0, -1], [0, 0]])
        clear = all(np.hypot(*(spot - other)) > breadth for other in found)
        if clear and level_share(ring, zones).min() > 0.99:
            found.append(spot)
    return found


def craters_of(plan, row, item_boxes, zones):
    """[(middle, radius, depth)] of a crater row: each item box's, else its count scattered at its read size."""
    if item_boxes:
        found = []
        for left, top, right, bottom in item_boxes:
            breadth = ((right - left) + (bottom - top)) / 2
            found.append((np.array([(left + right) / 2, (top + bottom) / 2]), breadth / 2, crater_depth(row, breadth)))
        return found
    size = row.get("size") or [6.0, 6.0]
    breadth = float(max(size[0], size[1]))
    return [(spot, breadth / 2, crater_depth(row, breadth))
            for spot in scattered(plan, int(row.get("count") or 1), breadth, zones, seed_of("crater", row["id"]))]


def spread(boxes, past):
    """(low, high) [x, y] round boxes [(x0, y0, x1, y1)], grown by `past`."""
    boxes = np.asarray(boxes, dtype=float)
    return boxes[:, :2].min(axis=0) - past, boxes[:, 2:].max(axis=0) + past


def pocks_of(boxes, field, seed):
    """[(middle, radius, depth)] of the small craters pocking a regolith field round the plans' boxes (FIELDS'
    density, a power law of breadths from 1.5 m to 14 m)."""
    rng = np.random.default_rng(seed)
    low, high = spread(boxes, POCKS_PAST)
    count = int(np.prod(high - low) * field["pocks"])
    middles = rng.uniform(low, high, size=(count, 2))
    breadths = np.minimum(1.5 * (1.0 - rng.uniform(size=count)) ** (-1 / 1.6), 14.0)
    return [(middle, breadth / 2, 0.14 * breadth) for middle, breadth in zip(middles, breadths)]


def waves(points, length, seed):
    """Smooth waves over plan points, 0 to 1: six sines of about `length` at turns and phases the seed gives."""
    rng = np.random.default_rng(seed)
    total = np.zeros(len(points))
    for _ in range(6):
        turn, phase = rng.uniform(0, math.pi), rng.uniform(0, 2 * math.pi)
        stretch = length * rng.uniform(0.6, 1.5)
        total += np.sin((points[:, 0] * math.cos(turn) + points[:, 1] * math.sin(turn)) * 2 * math.pi / stretch + phase)
    return total / 12.0 + 0.5


def terraced(share):
    """Share 0 to 1 in TERRACES flat steps with steep risers between (mesas and cliffs)."""
    stepped = share * TERRACES
    floor = np.floor(stepped)
    rise = np.clip((stepped - floor - 0.75) / 0.25, 0.0, 1.0)
    return (floor + rise * rise * (3.0 - 2.0 * rise)) / TERRACES


def past_boxes(points, boxes):
    """Each point's distance past the nearest of the plans' boxes (0 inside one)."""
    nearest = np.full(len(points), np.inf)
    for left, top, right, bottom in boxes:
        across = np.maximum.reduce([left - points[:, 0], np.zeros(len(points)), points[:, 0] - right])
        along = np.maximum.reduce([top - points[:, 1], np.zeros(len(points)), points[:, 1] - bottom])
        nearest = np.minimum(nearest, np.hypot(across, along))
    return nearest


def field_height(points, past, field, seed):
    """The natural ground's own relief at points `past` metres past the plans' boxes: low waves inside them, rising
    past them to taller ones (terraced on sand and rock), fading to nothing FIELD_REACH out."""
    rise = np.clip((past - RISE_FROM) / RISE_OVER, 0.0, 1.0)
    rise = rise * rise * (3.0 - 2.0 * rise)
    fade = np.clip((FIELD_REACH - past) / (0.3 * FIELD_REACH), 0.0, 1.0)
    shape = waves(points, field["wave"], seed)
    tall = terraced(shape) if field["terraced"] else shape
    return (field["inside"] * (shape - 0.5) * (1.0 - rise) + field["outside"] * tall * rise) * fade


def craters_height(points, craters):
    """The sum of craters' heights at plan points (each read only within its rim's reach, points sorted across)."""
    total = np.zeros(len(points))
    order = np.argsort(points[:, 0])
    across = points[order, 0]
    for middle, radius, depth in craters:
        reach = radius * RIM_FADE
        first, last = np.searchsorted(across, [middle[0] - reach, middle[0] + reach])
        picked = order[first:last]
        picked = picked[np.abs(points[picked, 1] - middle[1]) < reach]
        total[picked] += crater_height(np.hypot(*(points[picked] - middle).T), radius, depth)
    return total


def tracks_height(points, lines):
    """The sum of tracks' heights at plan points: [(line, piece)]."""
    total = np.zeros(len(points))
    for line, piece in lines:
        low, high = line.min(axis=0) - 3.0, line.max(axis=0) + 3.0
        near = np.all((points >= low) & (points <= high), axis=1)
        if near.any():
            signed, _ = apart_from_line(points[near], line)
            total[near] += ruts_height(signed, piece)
    return total


def ground_relief(parts, field, seed):
    """The ground's kit relief over points of its first top scene's plan: the field, the craters and pocks and the
    tracks of every top scene on it, level where people walk and things stand; read only within FIELD_REACH of a
    plan's box."""
    def relief(points):
        points = np.atleast_2d(np.asarray(points, dtype=float))
        total = np.zeros(len(points))
        past = past_boxes(points, parts["boxes"])
        near = past < FIELD_REACH
        if not near.any():
            return total
        shown = points[near]
        height = craters_height(shown, parts["craters"]) + tracks_height(shown, parts["lines"])
        if field is not None:
            height += field_height(shown, past[near], field, seed)
        total[near] = height * level_share(shown, parts["zones"]) + craters_height(shown, parts["planned"]) * \
            level_share(shown, parts["zones"], PLANNED_MARGIN, PLANNED_BLEND)
        return total
    return relief


def rocks_of(parts, field, seed):
    """[[x, y, radius]] of a natural ground's rocks round the plans' boxes (FIELDS' density and largest, a power law
    of radii from SMALLEST_ROCK), none where the ground stays level."""
    rng = np.random.default_rng(seed)
    low, high = spread(parts["boxes"], ROCKS_PAST)
    count = int(np.prod(high - low) * field["rocks"])
    spots = rng.uniform(low, high, size=(count, 2))
    radii = np.minimum(SMALLEST_ROCK * (1.0 - rng.uniform(size=count)) ** (-1 / 1.8), field["largest"])
    kept = level_share(spots, parts["zones"]) > 0.99
    return np.column_stack([spots[kept], radii[kept]])


def region(box, plan):
    """Whether an item's box is a region of the plan rather than one piece's place: over REGION_SHARE of its area
    (wreck's craters and skid marks, each one item over the whole plan)."""
    left, top, right, bottom = box
    return (right - left) * (bottom - top) > REGION_SHARE * float(plan["w"]) * float(plan["d"])


def converter(ground, top, anchor):
    """The map from a top scene's plan points [[x, y]] to its ground's first top scene's (`anchor`): the tops on one
    body stand near each other (the Moon's base, old station and wreck within 111 m), so one frame holds them all."""
    from score.stages.terrain import design
    entry = ground["tops"][anchor]
    middle, east, south = (np.asarray(entry[key], dtype=float) for key in ("middle", "east", "south"))

    def convert(points):
        world = design.tangent(ground["tops"][top], np.atleast_2d(np.asarray(points, dtype=float)))
        return np.column_stack([(world - middle) @ east, (world - middle) @ south]) + np.asarray(entry["half"])
    return convert


def box_in(convert, box):
    """A box (x0, y0, x1, y1) through `convert`, the box round its turned corners."""
    left, top, right, bottom = box
    corners = convert([[left, top], [right, top], [left, bottom], [right, bottom]])
    return (*corners.min(axis=0).tolist(), *corners.max(axis=0).tolist())


def top_parts(top, plan, plans, rows, convert):
    """One top scene's part of its ground's kit in the anchor's plan metres: {"boxes": [its plan's box], "zones":
    (level boxes, level spots), "craters", "lines", "record"}."""
    boxes, spots = level_zones(plan, plans, rows)
    zones = (boxes, spots)
    parts = {"boxes": [box_in(convert, (0.0, 0.0, float(plan["w"]), float(plan["d"])))],
             "zones": ([box_in(convert, box) for box in boxes],
                       [(*convert([[x, y]])[0].tolist(), radius) for x, y, radius in spots]),
             "planned": [], "craters": [], "lines": [], "record": []}
    items = items_of(plan)
    for row in rows.values():
        piece = piece_of(row)
        if piece is None:
            continue
        item_boxes = [box for _, item_rows, box in items if row["id"] in item_rows and not region(box, plan)]
        if piece == "crater":
            made = craters_of(plan, row, item_boxes, zones)
            parts["planned" if item_boxes else "craters"] += [(convert([middle])[0], radius, depth)
                                                              for middle, radius, depth in made]
            parts["record"] += [{"place": top, "row": row["id"], "piece": "crater", "at": [
                round(float(value), 2) for value in middle], "breadth": round(2 * radius, 2), "depth": round(depth, 2)}
                for middle, radius, depth in made]
        else:
            made = track_lines(plan, row, rows, item_boxes)
            parts["lines"] += [(convert(line), piece) for line in made]
            parts["record"] += [{"place": top, "row": row["id"], "piece": piece, "from": line[0].round(2).tolist(),
                                 "to": line[-1].round(2).tolist()} for line in made]
    return parts


def laid(ground, plans, inventories, recipe):
    """The ground's kit, in its first top scene's plan metres: {"reliefs": [(source, relief)] for design.relief_at
    (one, or none when nothing is laid), "rocks": {"anchor": that top, "rocks": [[x, y, radius]]} or {}, "record":
    what was laid}. Every top scene's craters and tracks; a field, pocks and rocks only on a natural ground (NATURAL:
    `recipe`, the ground's)."""
    anchor = sorted(ground["tops"])[0]
    field = FIELDS.get(recipe) if recipe in NATURAL else None
    seed = seed_of("field", ground["on"], recipe)
    parts = {"boxes": [], "zones": ([], []), "planned": [], "craters": [], "lines": [], "record": []}
    for top in sorted(ground["tops"]):
        found = top_parts(top, plans[top], plans, rows_of(inventories, top), converter(ground, top, anchor))
        parts = {"boxes": parts["boxes"] + found["boxes"],
                 "zones": (parts["zones"][0] + found["zones"][0], parts["zones"][1] + found["zones"][1]),
                 **{key: parts[key] + found[key] for key in ("planned", "craters", "lines", "record")}}
    if field is not None:
        parts["craters"] += pocks_of(parts["boxes"], field, seed) if field["pocks"] else []
        parts["record"].append({"place": anchor, "piece": "field", "ground": recipe})
    if not (parts["planned"] or parts["craters"] or parts["lines"] or field):
        return {"reliefs": [], "rocks": {}, "record": parts["record"]}
    plan = plans[anchor]
    source = {"place": anchor, "top": anchor, "to_own": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
              "middle": [float(plan["w"]) / 2, float(plan["d"]) / 2], "kit": True}
    rocks = {}
    if field is not None:
        rocks = {"anchor": anchor, "rocks": rocks_of(parts, field, seed)}
        parts["record"].append({"place": anchor, "piece": "rocks", "count": len(rocks["rocks"])})
    return {"reliefs": [(source, ground_relief(parts, field, seed))], "rocks": rocks, "record": parts["record"]}


# --- rocks in a place's frame ---------------------------------------------------------------------------------------

def stone():
    """A unit icosphere's points and triangles (one subdivision: 42 points, 80 faces)."""
    golden = (1 + 5 ** 0.5) / 2
    points = [[-1, golden, 0], [1, golden, 0], [-1, -golden, 0], [1, -golden, 0], [0, -1, golden], [0, 1, golden],
              [0, -1, -golden], [0, 1, -golden], [golden, 0, -1], [golden, 0, 1], [-golden, 0, -1], [-golden, 0, 1]]
    faces = [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2],
             [10, 7, 6], [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11],
             [6, 2, 10], [8, 6, 7], [9, 8, 1]]
    points = [np.asarray(point, dtype=float) / np.linalg.norm(point) for point in points]
    halves, finer = {}, []
    for face in faces:
        middles = []
        for one, two in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            key = (min(one, two), max(one, two))
            if key not in halves:
                half = points[one] + points[two]
                points.append(half / np.linalg.norm(half))
                halves[key] = len(points) - 1
            middles.append(halves[key])
        finer += [[face[0], middles[0], middles[2]], [face[1], middles[1], middles[0]],
                  [face[2], middles[2], middles[1]], middles]
    return np.asarray(points), np.asarray(finer, dtype=np.int64)


def in_frame(ground, place, top, plan_points):
    """A top scene's plan points [[x, y]] as [x, z] of a place's frame."""
    from score.stages.terrain import design
    entry = ground["places"][place]
    world = design.tangent(ground["tops"][top], plan_points)
    return ((world - np.asarray(entry["origin"])) @ np.asarray(entry["axes"]))[:, [0, 2]]


def rock_mesh(ground, place, rocks, shaped):
    """The ground's rocks (laid's `rocks`) that lie in the place's fine patch, as one mesh (points, triangles) in its
    frame, each stone jittered and squat, sunk SUNK of its height into the ground there; None with none."""
    from score.stages.terrain import design, outside
    if not rocks or not len(rocks["rocks"]):
        return None
    found = rocks["rocks"]
    spots = in_frame(ground, place, rocks["anchor"], found[:, :2])
    low, high, _ = outside.near_box(ground["places"][place])
    kept = np.all((spots >= low) & (spots <= high), axis=1)
    if not kept.any():
        return None
    spots, radii, numbers = spots[kept], found[kept, 2], np.flatnonzero(kept)
    feet = design.ground_points(ground, place, spots, shaped)[:, 1]
    unit, faces = stone()
    points, triangles = [], []
    for index, (spot, radius, foot, number) in enumerate(zip(spots, radii, feet, numbers)):
        rng = np.random.default_rng([seed_of("rock"), int(number)])  # each stone its own shape in every place
        bumps = unit * rng.uniform(0.75, 1.15, size=(len(unit), 1))
        squat = rng.uniform(0.45, 0.8)
        turn = rng.uniform(0, 2 * math.pi)
        cos, sin = math.cos(turn), math.sin(turn)
        shaped_stone = np.column_stack([cos * bumps[:, 0] - sin * bumps[:, 2], bumps[:, 1] * squat,
                                        sin * bumps[:, 0] + cos * bumps[:, 2]]) * radius
        lift = foot + squat * radius * (1.0 - 2.0 * SUNK)
        points.append(shaped_stone + np.array([spot[0], lift, spot[1]]))
        triangles.append(faces + index * len(unit))
    return np.concatenate(points), np.concatenate(triangles)
