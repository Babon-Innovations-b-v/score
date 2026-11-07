"""What holds each plan item (issue #72; bible `architecture/layers`, assembly: the plan states the relations the
assembly lays by): derived free from the scene inventory's anchors, the concept's boxes and the kept plan, no model
call, and kept beside the plan in a file of its own, `{home}/design/relations/<place>.json`, which the scene record
reads (never in design/plans/: that file keys the close-ups and the surface library).

Each plan item of a row that stands on, against or in something gets one relation, in plan metres (x east, y south):

    top    on its holder item's top: the row's anchor `on:<row>`, and in the concept its box's foot stands over its
           holder's by more than TOP_SHARE of the holder's box (a monitor on its console, a lamp on its desk)
    within inside its holder item, where the plan lays its middle (plants in their greenhouse, a door in its frame);
           `hangs` where it hangs in it (hangs: a spacesuit in its locker); a row its reading's `where` says is under
           its holder (`under`: at its holder's foot, cables under the desk) or on its shelves (placement)
    face   (a moving door's `recess`, its room in its holder model behind it: recess_of; `spots` each piece's plan
           middle where a moving door's item lays several, at least its width, room and OPENING_ROOM apart: face_spots,
           or where things on one face that meet at their built sizes are spread along it: face_spread, a face too
           short for them `crowded`)
           against its holder item's side, `face` N, E, S or W: the side the concept shows it against (toward the
           viewer where its box stands within its holder's across, else the holder's left or right as seen), else the
           side toward it on the plan, else its facing, its holder's, or S (the garage door on its module's front)
    in     in a door or window opening of the plan (`opening`: its at, wide, sill, head, and the wall it stands on): a
           row that fills an opening (design_shell.fills_opening), anchored on a wall or on structure; each opening
           holds one, the nearest to the item's spot, of the row's kind (a window a window's, a door a door's); with
           none left, one cut for it (`cut`) where its spot meets the nearest wall with room beside its openings; each
           piece its own (`pieces`): an item's where the scene record lays it, the walls item's at its concept boxes'
           projections, else spread along the longest wall
    edge   past the plan's edge (`edge`, `spot` the edge's middle): a wall row the plan writer left on the walls item
           where the plan draws no wall (street's facades), on the side of the view its concept box stands; what is on
           it stands against its face toward the place
    wall   against a wall of the plan (`wall`, its from, to, thick, and `side` +1 or -1 of the line it stands on, `spot`
           its plan spot): a row anchored `wall`, or on a structure row that is a wall; an item the plan writer did not
           place (the walls item) stands where the concept's box projects onto the plan (plan_checks.projection), else
           at the longest wall's middle; an item outlining the whole room (outlines_room: its middle says nothing)
           on the wall its holder's id names as the viewer sees it (left_wall), else, the concept not placing it, the
           middle of the nearest wall no other such item holds; such items sharing a spot on one wall spread along it;
           any row's items at one spot on one wall at one height packed along it, else stood one over another up it
           (parted_on_wall); a wall thing whose built box still meets one laid before it on the walls (any row's,
           round a corner too) stood the nearest free height over or under it, inside its height band (apart_on_walls);
           a placed item stands on the room's side, drawn past the outline or not, but a passage (a tunnel, a tube)
           meets its wall from outside (past_outline)
    ramp   a ramp row on the floor where the plan draws a raised level (airlock's porch deck): up to the nearest such
           level's nearest edge (`edge`, its two plan points, and `height`), its long side run straight up to it
           (`way`), its high end on the edge's line and its middle at `spot` (up_to_level)
    floor / ceiling  on the place's own floor or under its roof, nothing to lay against; one the plan writer left on
           the walls item at its `spot` (a stair row at the plan's stair along its way up, else where its concept box
           projects), a thing on a staircase along the plan's stairs' sides (`pieces`); one its words say stands round
           a holder row (railings "around engines") at its own `spot` round that row's item's sides, `way` along it
           (around_holders); one its plan stands up on nothing at the `height` of what is under it (stood_under)
    hung   over the floor between the two standing things nearest its ends that reach its top (`holders`, `holder
           rows`): a floor row whose words say it hangs over it (lantern strings "above plaza", hung_between)

Each relation of a row whose reading's `where` says how it rests on what holds it carries `rests` (#94; rests):
`leaning`, its foot on the floor and its top against its holder (a board leaning against a wall: never on its
holder's top or within it, never at a mount height, and one the reading anchors on the floor against the nearest wall
of a plan with walls), which the settle leans there and fails where it falls or floats; `attached`, fixed to its
holder so it would stay put were that turned over (a ramp attached to its lander), which the settle holds as laid.

A row whose things the concept shows on several rows of its named holder's footing (hub's 38 monitors on four consoles,
the reading naming one bank: one anchor a row) has each item held by the nearest of them on the plan (seen_holders):
the anchors stay the reading's, so the hand-in, the close-ups and Pixal3D keep their keys. A row whose holder the plan
does not lay and is no wall, floor or roof, or a wall item in an open place with no wall,
is `unheld` with why. The file names the kept plan's sha it was derived from (`plan`), so the scene record lays by
it only while the plan is the same.

    relations(plan, inventory)   the place's relations {place, plan, about, relations, unheld, loose}
    keep(places)                 written for each place with a kept plan and inventory, where the scene record reads it
"""
import copy
import hashlib
import json
import math
import re

import numpy

from score.review import plan_checks
from score.stages import row_kinds
from score.stages import shell_parts
from score.stages.earth_seed import design_shell
from score.store import PROPS_HOME

KEPT_PLANS = PROPS_HOME / "design" / "plans"
KEPT_INVENTORY = PROPS_HOME / "design" / "inventory"
KEPT = PROPS_HOME / "design" / "relations"
# A window's sill, metres over its floor, where an opening is cut for it and its plan item gives no base.
WINDOW_SILL = 0.9
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
# Metres left between two pieces of one row laid side by side on a wall, a floor or before a holder: packed, never
# one in another (2026-11-04 audit: the workshop's 25 tools and 13 monitors each laid at one spot).
PIECE_GAP = 0.05
# A row's where words that say it hangs high on its wall, and those that say it spans the room under the roof (a crane
# 'top, spanning left to right' is no wall thing, 2026-11-04 audit), unless they name a wall.
HIGH_WORDS = {"high", "above", "upper", "overhead"}
SPAN_WORDS = {"top", "spanning", "overhead", "ceiling"}
WALL_NAMED = {"wall", "walls"}
LIGHT_WORDS = {"light", "lights", "lamp", "lamps", "sconce", "sconces"}
# Where words of a row under the roof that say it is hung from it (its top laid at the roof's underside).
ROOF_WORDS = {"ceiling", "top", "hanging", "roof", "overhead", "spanning"}
# A thing said high on a wall stands at this share of the room's height, never under a door's head and a hand.
HIGH_SHARE = 0.75
HIGH_LEAST = design_shell.DOOR_HEAD + 0.1
# A small wall thing (no taller than SMALL metres) the plan gives no height is centred at EYE_MOUNT metres.
SMALL = 1.0
EYE_MOUNT = 1.5
# A seat whose where words say it stands at, by, before or around a holder row (a chair at its desk) stands before its
# holder's built side the plan draws it on, SEAT_GAP metres clear of it, facing it (2026-11-04 audit: hangar's office
# chairs 0.7 to 1.1 m from their desks, laid at plan boxes drawn 3.5 times their size).
SEAT_WORDS = {"chair", "chairs", "stool", "stools", "seat", "seats", "bench", "benches", "armchair"}
BESIDE_WORDS = {"at", "by", "front", "beside", "next", "around"}
PERSON_WORDS = {"person", "people", "man", "woman", "worker", "crew"}  # a seat's sitter is never what it stands at
SEAT_GAP = 0.1
# Where words that say how a row rests on what holds it (#94, rests): leaning, its foot on the floor and its top
# against its holder; attached, fixed to it, so it would stay put were its holder turned upside down.
LEANING, ATTACHED = "leaning", "attached"
LEAN_WORDS = {"leaning", "leans", "leant", "leaned", "propped"}
ATTACH_WORDS = {"attached", "bolted", "welded", "clamped", "screwed", "strapped", "fastened", "affixed"}
# A row's words that say its things pile on one another (airlock's sandbags, "knee high pile"): only such a row's things
# stand on their own row's (plan_fixes.PILE_WORDS, held equal by the test; the scene record's laid-as-designed gate).
PILE_WORDS = {"pile", "piles", "piled", "stack", "stacks", "stacked", "heap", "heaps", "heaped"}
# A floor row's where words that say its things stand round a holder row its other words name (engineroom's railings
# "around engines"): laid as pieces round that holder's built outline (around_holders), never at one spot or stacked.
AROUND_WORDS = {"around", "surrounding", "encircling"}
# A floor row's where words that say its things hang over the floor (square's lantern strings "above plaza"): hung
# between the two standing things nearest its ends that reach its height (hung_between).
HUNG_WORDS = {"above", "overhead", "strung", "hung"}
# A plan base within this many metres of a stand (the floor, a level, a flight, another thing's top) stands on it.
STAND_REACH = 0.05


def plan_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def middle(item):
    return numpy.array([float(item[1]) + float(item[3]) / 2, float(item[2]) + float(item[4]) / 2])


def where_words(row):
    return set(re.findall(r"[a-z]+", str(row.get("where") or "").lower()))


def rests(row):
    """How a row rests on what holds it, as its where words say (LEAN_WORDS, ATTACH_WORDS): LEANING, ATTACHED, or
    None for one standing on, hung on or set against it as the other relations lay it."""
    words = where_words(row)
    return LEANING if words & LEAN_WORDS else ATTACHED if words & ATTACH_WORDS else None


def rests_entry(row):
    """{"rests": how} of a row that says how it rests (rests), else {}."""
    how = rests(row)
    return {"rests": how} if how else {}


def leaning_on_floor(row, plan):
    """Whether a row read on the floor leans against a wall (its where words, a plan with walls): held against the
    nearest wall, its foot on the floor, never laid upright in the room's middle."""
    return (row.get("anchor") or "floor") in plan_checks.FLOOR_ANCHORS and rests(row) == LEANING and bool(walls_of(plan))


def spans(row):
    """Whether a row read against a wall spans the room under its roof instead (its where words SPAN_WORDS and no
    wall named): hangar's overhead cranes 'top, spanning left to right'; never a door or window."""
    words = where_words(row)
    return bool(words & SPAN_WORDS) and not words & WALL_NAMED and not design_shell.fills_opening(row)


def under_roof(row):
    """Whether a row under the place's roof hangs from it (anchored ceiling or roof, or its where words ROOF_WORDS):
    its top laid at the roof's underside by the scene record; a floor read under a dome's holder is none."""
    return (row.get("anchor") or "") in ("ceiling", "roof") or bool(where_words(row) & ROOF_WORDS)


def piles(row):
    """Whether a row's things pile on one another: a PILE_WORDS word in its id, name, noun, where or size words."""
    return bool(PILE_WORDS & set(re.findall(r"[a-z]+", " ".join(
        str(row.get(key) or "") for key in ("id", "name", "noun", "where", "size_words")).replace("_", " ").lower())))


def words_of(row):
    return set(re.findall(r"[a-z]+", f"{row['id']} {row.get('name', '')} {row.get('noun', '')}".replace("_", " ").lower()))


def holder_kind(row):
    """What a structure row is to what stands on it: wall, floor or ceiling, by its part, else the words of its id and
    noun (never its name: airlock's "floor AC unit" is no floor); None."""
    if row.get("part") in PARTS:
        return PARTS[row["part"]]
    found = kind_words(row)
    return next((kind for kind, words in (("wall", WALL_WORDS), ("ceiling", CEILING_WORDS), ("floor", FLOOR_WORDS))
                 if found & words), None)


def items_of(plan):
    """{plan item name: item} of the plan's things, and {row id: [its item names, in the plan's order]}: the walls
    item (WALLS_ITEM) none of a row the plan also places on an item of its own, which the scene record lays it at
    alone (its writer.item_rows; 2026-11-06: street's restaurant doors and shutters were given openings on the walls
    item too, which the record never lays, and their wall too crowded to part their own)."""
    items = {item[0]: item for item in plan.get("items") or [] if len(item) > 6 and item[6] == "item"}
    tied, rows = plan.get("rows") or {}, {}
    for name in items:
        for row_id in tied.get(name) or []:
            rows.setdefault(row_id, []).append(name)
    for names in rows.values():
        if plan_checks.WALLS_ITEM in names and len(names) > 1:
            names.remove(plan_checks.WALLS_ITEM)
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


# A moving door's recess in its holder model, by its motion rule (data/checks/row-kinds.json `motion`): as deep as a
# swing sweeps (its width times the sine of its angle), or its own thickness where it slides (with its width of room
# along the face) or rolls, plus RECESS_MARGIN; a door whose rule moves it nowhere sits flush, no recess. Its room
# beside it along the face holds a side wall too (RECESS_WALL, the bake's score/stages/surfaces/route_bake.py
# RECESS_BACK: a recess kept that far inside each end of the face), so the assembly keeps the door that much further
# in and the door clears the kept wall by RECESS_MARGIN at full open (base's garage door, #36, 2026-10-29: its room
# its thickness plus RECESS_MARGIN alone, the wall took the clearance and it lay flush against it).
RECESS_MARGIN = 0.05
RECESS_WALL = 0.05


def item_way(holder_item, holder_row):
    """The plan way the scene record lays a holder item's model along (writer.item_way)."""
    from score.stages.scene_record import writer
    return writer.item_way(holder_item, holder_row)


def model_axes(way, holder_row):
    """(plan way of the holder model's +x, of its +z) as the scene record lays it along `way` (writer.yaw_turn: its
    long side along the way, its z there where its row is deeper than wide)."""
    way = numpy.asarray(way, float)
    size = holder_row.get("size") or [1.0, 1.0, 1.0]
    if float(size[1]) > float(size[0]):
        return numpy.array([way[1], -way[0]]), way
    return way, numpy.array([-way[1], way[0]])


def moving_rule(row, inventory, kinds):
    """The row's motion rule where it moves in its scene (its kind's rule served: a door where somebody passes), else
    None."""
    from score.stages.motion import from_design
    kind = row_kinds.kind_of(row, kinds)
    rule = (kinds.get(kind) or {}).get("motion") if kind else None
    if not rule or rule.get("move") not in ("swing", "slide", "roll") or not from_design.served(rule, inventory, kinds):
        return None
    return rule


def piece_middles(item, row, plan):
    """[(plan middle, the plan way its model's long side is laid along)] of each piece the scene record lays at an
    item (writer.spots_of, writer.pieces_of: street's three restaurant doors on one item)."""
    from score.stages.scene_record import writer
    shapes, tied = plan.get("shapes") or {}, plan.get("rows") or {}
    items = [(other, shapes.get(other[0]) or {}) for other in plan.get("items") or []
             if row["id"] in (tied.get(other[0]) or [])]
    counts = dict(zip((other[0] for other, _ in items), writer.pieces_of(row, items))) if items else {}
    return writer.spots_of(item, shapes.get(item[0]) or {}, counts.get(item[0], 1), row)


def face_spots(item, row, plan, room):
    """[(plan middle, way)] of a moving door's pieces against a face (piece_middles), moved apart along the line they
    stand on about their middle so neighbours stand their width, their recess's `room` and OPENING_ROOM apart where
    they stood closer (street's three 1.0 m restaurant doors laid 0.58 m apart on their 1.74 m item, their recesses in
    one another, #36); as laid where they stand far enough apart."""
    placed = piece_middles(item, row, plan)
    if len(placed) < 2:
        return placed
    pitch = float(row["size"][0]) + room + OPENING_ROOM
    first, last = (numpy.asarray(placed[end][0], float) for end in (0, -1))
    length = float(numpy.linalg.norm(last - first))
    if length >= pitch * (len(placed) - 1) - 1e-9:
        return placed
    run = (last - first) / length if length else numpy.asarray(placed[0][1], float)
    centre = (first + last) / 2
    return [(centre + run * pitch * (number - (len(placed) - 1) / 2), way) for number, (_, way) in enumerate(placed)]


def spots_entry(item, row, plan, recess):
    """{"spots": each piece's plan middle} of a moving door's face relation (its `recess`) whose item lays several
    (face_spots), where the scene record lays each piece (writer.related); {} for one piece or a door that never
    moves (laid as before)."""
    placed = face_spots(item, row, plan, float(recess["room"])) if recess else []
    return {"spots": [[round(float(value), 3) for value in spot] for spot, _ in placed]} if len(placed) > 1 else {}


def recess_of(item, row, holder, holder_row, face, plan, inventory, kinds, placed=None):
    """The recess a moving door needs in its holder model behind it, in the model's own frame: the model `axis` (x or
    z) and `side` its face is on, the door's middle `along` the face from the model's middle (`pieces`: one each where
    the item lays several), its `wide`, `tall`, `base` over the model's foot, and by its motion rule its `depth` and
    the `room` beside it along the face on its `room_side` (+1 or -1 along the model's axis, 0 both: its hinge side
    not read; `room_sides` one a piece), and that side as a plan way (`room_way`, `room_ways`: the assembly keeps the
    door so its room fits within the face's span too, fitting.on_face): a swing's as deep as it sweeps, widened on its hinge side by its own
    thickness, RECESS_MARGIN and the side wall the bake keeps (RECESS_WALL) so it lies clear of that wall at full open; a slide's its own thickness deep, with its width and
    thickness of room on the side it slides to; None for a door that never moves (it sits flush) or has no size.
    `placed`: its pieces' [(plan middle, way)] where they are spread along their face (face_spread), else face_spots'."""
    rule, size = moving_rule(row, inventory, kinds), row.get("size")
    if rule is None or not (isinstance(size, list) and len(size) == 3):
        return None
    wide, deep, tall = (float(side) for side in size)
    holder_middle, holder_way, holder_base = holder
    model_x, model_z = model_axes(holder_way, holder_row)
    out = numpy.asarray(FACES[face], float)
    on_x = abs(float(out @ model_x)) >= abs(float(out @ model_z))
    side = float(numpy.sign(out @ (model_x if on_x else model_z)))
    shapes = plan.get("shapes") or {}
    base = float((shapes.get(item[0]) or {}).get("base") or 0.0) - holder_base
    depth = (wide * abs(math.sin(math.radians(float(rule.get("angle") or 90.0)))) if rule["move"] == "swing"
             else deep) + RECESS_MARGIN
    along_way = model_z if on_x else model_x
    room = (deep if rule["move"] == "swing" else wide + deep) + RECESS_MARGIN + RECESS_WALL
    placed = face_spots(item, row, plan, room) if placed is None else placed
    alongs = [round(float((spot - holder_middle) @ along_way), 3) for spot, _ in placed]
    toward = (rule.get("hinge") if rule["move"] == "swing" else rule.get("slide") or [1.0, 0.0, 0.0]) or [None]
    sides = [room_side(toward[0], model_axes(way, row)[0], along_way) for _, way in placed]
    ways = [[round(float(value), 6) + 0.0 for value in along_way * piece_side] for piece_side in sides]
    return {"model": f"{holder_row['id']}_1", "axis": "x" if on_x else "z", "side": side, "along": alongs[0],
            **({"pieces": alongs, "room_sides": sides, "room_ways": ways} if len(alongs) > 1 else {}),
            "wide": wide, "room": round(room, 3), "room_side": sides[0], "room_way": ways[0], "tall": tall,
            "base": round(base, 3),
            "depth": round(depth, 3), "why": f"a {rule['move']} door's room in {holder_row['id']}'s {face} face"}


def room_side(toward, door_x, along_way):
    """Which end along the holder's face (+1 or -1 along its axis) a door's room is on: its hinge side, or the side it
    slides to, `toward` on its own x (-1 its left), turned as the door is laid; 0 (room both sides) where its rule
    names none or its own x does not run along the face."""
    lined = float(numpy.asarray(door_x, float) @ numpy.asarray(along_way, float))
    if toward is None or abs(lined) < 0.9 or not float(toward):
        return 0.0
    return float(numpy.sign(float(toward) * lined))


def fits_over(row, holder_row, room):
    """Whether the row, stood on its holder's top, stays under the place's height `room` (metres; None: no roof, it
    fits): both rows' heights (size[2]) together no more than it. The docking airlock's 1.8 m spacesuits, their boxes
    in their 2 m locker's top half, read as on its top and stood through the 2.5 m ceiling (round 32)."""
    heights = [float((found.get("size") or [0.0, 0.0, 0.0])[2]) for found in (row, holder_row)]
    return room is None or sum(heights) <= room


def hangs(item, holder_item, plan):
    """Whether an item laid within its holder hangs in it (`hangs` on its relation: the assembly hangs it on the
    holder's back and judges it by touching): by the plan's shapes, its foot over the holder's and under its top,
    at least half the holder's height, its top in the holder's top quarter (TOP_SHARE): the docking airlock's 1.8 m
    spacesuits at 0.1 m in their 2 m lockers; never a tray on a rack's shelf, a keyboard on a desk, a valve on a pipe."""
    shapes = plan.get("shapes") or {}
    base, tall, under, high = (float((shapes.get(name) or {}).get(key) or 0.0)
                               for name in (item[0], holder_item[0]) for key in ("base", "tall"))
    return under < base < under + high and tall >= high / 2 and base + tall >= under + high * (1 - TOP_SHARE)


def room_height(plan):
    """The place's height under its roof: its highest roof's top or tallest wall (a dome rises over its walls: the
    workshop's robotic arm on its console stands under it), or None where the plan draws neither."""
    talls = [float(wall["tall"]) for wall in plan.get("walls") or [] if wall.get("tall")] + [
        float(roof["top"]) for roof in plan.get("roofs") or [] if roof.get("top")]
    return max(talls) if talls else None


def placement(row, holder_row):
    """The placement word a row's reading says beside its holder (its `where`), past `on`: "under" (cables under the
    desk, a box under the lab table), "shelf" (boxes on the shelves, a tray on its rack's top shelf) or "side" (a
    poster on the locker's side, a hose on the side of the AC unit; never "left side of the desk", where on it), else
    None. Quarters' cables under its desk lay on the desk's top, the engine room's boxes on their shelves at 2 m on
    the unit's top (2026-11-04)."""
    where = str(row.get("where") or "").lower()
    named = "|".join(re.escape(word) for word in sorted(kind_words(holder_row)))
    if re.search(r"\b(under|underneath|beneath|below)\b", where):
        return "under"
    if re.search(r"\bshel(f|ves)\b", where):
        return "shelf"
    if re.search(r"(?<!left )(?<!right )\bsides? of\b", where) or (named and re.search(rf"\b({named})s? sides?\b",
                                                                                         where)):
        return "side"
    return None


def held(item, row, holder_row, holder_items, items, turn, room=None):
    """A relation to a holder the plan lays, its nearest item: within it, at its foot, where its reading says it is
    under it, and within it where on its shelves (placement: the settle lets it down onto the shelf under it); top
    (where it fits under the place's height `room`, never one said on its holder's side), within it where the plan
    lays it inside, else against the face the concept shows it on, the plan's side toward it, its facing, its
    holder's, or S."""
    nearest = min(holder_items, key=lambda name: float(numpy.linalg.norm(middle(items[name]) - middle(item))))
    said = "side" if rests(row) == LEANING else placement(row, holder_row)  # a leaning thing stands against a side
    if said in ("under", "shelf"):
        return {"how": "within", "holder": nearest, **({"under": True} if said == "under" else {}),
                "why": f"{'under' if said == 'under' else 'on the shelves of'} {holder_row['id']}: its reading says "
                       f"{row.get('where')!r}"}
    if said != "side" and on_top(row, holder_row) and fits_over(row, holder_row, room) \
            and not design_shell.fills_opening(row):
        return {"how": "top", "holder": nearest, "why": f"on {holder_row['id']}'s top in the concept"}
    if rests(row) != LEANING and inside(item, items[nearest]):
        return {"how": "within", "holder": nearest, "why": f"within {holder_row['id']}: the plan lays it inside"}
    for face, why in ((seen_side(row, holder_row, turn), "side the concept shows it on"),
                      (side_toward(item, items[nearest]), "side toward it on the plan"),
                      (item[5], "side its own facing names: the plan lays it on its holder's spot"),
                      (items[nearest][5], "facing side: the plan lays it on its holder's spot"),
                      ("S", "S side: the plan lays it on its holder's spot, facing nowhere")):
        if face:
            return {"how": "face", "holder": nearest, "face": face, "why": f"against {holder_row['id']}'s {why}"}


def walls_of(plan):
    """The plan's walls as straight pieces: a straight wall itself, an arc (the greenhouse's round wall) the straight
    pieces the shell builds it of (design_shell.written_lines: one each ARC_STEP, run from start up to end). 2026-11-04:
    24 pieces an arc whatever its span, run backwards past 0 degrees, held workshop's wall things on 0.16 m chords of
    a wall the shell does not build, and the assembly shrank them to those chords (a 1 m panel to 0.2 m)."""
    found = []
    for wall in plan.get("walls") or []:
        if "from" in wall and "to" in wall:
            found.append(wall)
        elif "arc" in wall:
            thick = float(wall.get("thick") or design_shell.THICK)
            found += [{"from": [round(float(value), 4) for value in first],
                       "to": [round(float(value), 4) for value in second], "thick": thick}
                      for first, second in design_shell.written_lines(wall)]
    return found


def off_line(spot, wall):
    """(metres from a wall's line segment, the side of its line the spot is on: +1 or -1)."""
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    run = end - start
    share = float(numpy.clip((spot - start) @ run / max(float(run @ run), 1e-9), 0.0, 1.0))
    across = run[0] * (spot - start)[1] - run[1] * (spot - start)[0]
    return float(numpy.linalg.norm(spot - (start + run * share))), 1 if across >= 0 else -1


def seen_spots(row, plan, inventory):
    """Where each of the row's concept boxes' feet projects onto the plan (plan_checks.projection); [] with none."""
    fitted, picture = plan_checks.projection(plan, inventory), inventory.get("picture")
    if fitted is None or not picture:
        return []
    return [numpy.array([(seen[0] + seen[2]) / 2 / picture[0], seen[3] / picture[1], 1.0]) @ fitted
            for seen in plan_checks.boxes_of(row)]


def seen_spot(row, plan, inventory):
    """Where the row's first concept box projects onto the plan, or None."""
    return next(iter(seen_spots(row, plan, inventory)), None)


# A row that meets its place's wall from outside (the walkway tubes the concepts show joining a module).
PASSAGE_WORDS = {"tunnel", "tunnels", "tube", "tubes", "corridor", "corridors"}


def past_outline(spot, row, plan):
    """Whether a plan spot lies past the plan's outline for a row that stands in the room, any row but a passage
    (PASSAGE_WORDS): hangar's back-wall pipes, drawn 1.6 and 2.3 m past their wall, stood outside the hangar."""
    outline = plan.get("outline") or []
    return len(outline) >= 3 and not kind_words(row) & PASSAGE_WORDS and not bool(
        plan_checks.inside(numpy.asarray([spot], float), outline)[0])


def wall_length(wall):
    return float(numpy.linalg.norm(numpy.subtract(wall["to"], wall["from"])))


def built_long(row):
    """The row's built length along what holds it: its size's longer ground side (a model is laid with its long side
    along its wall, the scene record's yaw_turn), 0 for a row with no size."""
    size = row.get("size")
    return max(float(size[0]), float(size[1])) if isinstance(size, list) and len(size) == 3 else 0.0


def run_needed(row, pieces):
    """Metres of wall a row's `pieces` take laid side by side at their built length, PIECE_GAP apart."""
    return pieces * built_long(row) + (pieces - 1) * PIECE_GAP


def mount_height(item, row, plan):
    """(metres over the floor, why) a wall thing stands at where the plan gives its item no base: one its words say
    high or above, or a light, at HIGH_SHARE of the room's height (never under HIGH_LEAST, its top under the room's
    height); a small thing (no taller than SMALL) centred at EYE_MOUNT; None for anything else, or with a base given
    (2026-11-04 audit: hangar's wall lamps 'high on left and back walls', quarters' string lights 'above bed' and the
    workshop's 25 tools stood on the floor)."""
    if float(((plan.get("shapes") or {}).get(item[0]) or {}).get("base") or 0.0) > 0.0:
        return None
    tall = float(row["size"][2]) if isinstance(row.get("size"), list) and len(row["size"]) == 3 else 0.0
    room = room_height(plan) or design_shell.STOREY
    if where_words(row) & HIGH_WORDS or kind_words(row) & LIGHT_WORDS:
        high = min(max(HIGH_LEAST, HIGH_SHARE * room), room - tall - PIECE_GAP)
        return round(max(0.0, high), 3), "high on its wall, as its words or its light say"
    if 0.0 < tall <= SMALL and not kind_words(row) & (FLOOR_WORDS | STAIR_WORDS):
        return round(EYE_MOUNT - tall / 2, 3), f"centred {EYE_MOUNT:g} m up its wall: a small wall thing"
    return None


def on_wall(item, row, plan, inventory, pieces=1):
    """A relation against the nearest wall to the item's spot (the concept's for the walls item) whose length holds
    the row's pieces at their built length (run_needed: hangar's 30 m cranes went on a 2.12 m door-jamb stub and were
    shrunk to 53%; several each flat along one straight run of its chain, holds_flat), else the longest wall, named
    `short`; its mount height where the plan gives none (mount_height);
    or None."""
    walls = walls_of(plan)
    if not walls:
        return None
    placed = item[0] != plan_checks.WALLS_ITEM
    spot = middle(item) if placed else seen_spot(row, plan, inventory)
    if spot is None:
        wall = max(walls, key=wall_length)
        spot, why = (numpy.asarray(wall["from"], float) + numpy.asarray(wall["to"], float)) / 2, "the longest wall's middle"
    else:
        why = "its plan spot" if placed else "where its concept box projects onto the plan"
    need, bend = run_needed(row, pieces), CORNER_BEND if pieces > 1 else ROUND_BEND
    fitting = ([wall for wall in walls if wall_length(wall) >= need] if pieces == 1 else []) or [
        wall for wall in walls if holds_flat(chain_of(wall, walls, bend), row, pieces)]
    wall = min(fitting, key=lambda wall: off_line(spot, wall)[0]) if fitting else max(walls, key=wall_length)
    side = off_line(spot, wall)[1]
    if off_line(spot, wall)[0] < 1e-6 or (placed and past_outline(spot, row, plan)):  # the side toward the plan's middle
        side = off_line(numpy.array([float(plan["w"]) / 2, float(plan["d"]) / 2]), wall)[1]
    mount = None if rests(row) == LEANING else mount_height(item, row, plan)  # a leaning thing's foot is on the floor
    found = {"how": "wall", "wall": {key: wall[key] for key in ("from", "to", "thick")}, "side": side,
             "spot": [round(float(value), 3) for value in spot],
             "why": f"against the wall nearest {why} long enough for it" + (f"; {mount[1]}" if mount else ""),
             **({"height": mount[0]} if mount else {})}
    if not fitting:
        found["short"] = f"no wall holds its {need:g} m: the longest, {wall_length(wall):g} m"
    elif pieces == 1 and wall_length(wall) < need:  # on a round wall's facets: its face the chord it covers
        found = {**wall_pieces(found, item, row, 1, walls, ROUND_BEND)[0], "why": found["why"] + ", round its facets"}
    return found


# A plan item outlines the whole room when its box reaches this share of the plan's width and depth both: its middle
# says nothing of which wall it is on (engineroom's two wall panels, each drawn as the 8.49 x 10.36 m room, #36).
ROOM_SHARE = 0.75
# Whole-room items closer than this along one wall, metres, share one spot: they are spread evenly along it.
WALL_APART = 0.5
# The plan way each side word of a wall row's id names, as the concept's viewer sees it: (right, toward) of ways().
SIDE_WAYS = {"left": (-1, 0), "right": (1, 0), "back": (0, -1), "rear": (0, -1), "far": (0, -1), "front": (0, 1),
             "near": (0, 1)}


def outlines_room(item, plan):
    """Whether a plan item is the walls item or a box reaching ROOM_SHARE of the plan's width and depth."""
    return item[0] == plan_checks.WALLS_ITEM or (float(item[3]) >= ROOM_SHARE * float(plan["w"]) and
                                                  float(item[4]) >= ROOM_SHARE * float(plan["d"]))


def wall_key(wall):
    return tuple(wall["from"]), tuple(wall["to"])


def named_wall(holder, plan, turn):
    """The plan wall a wall row's id names by its side as the viewer sees it (left_wall: the one furthest to the
    viewer's left), or None where it names no side."""
    side = next((SIDE_WAYS[word] for word in sorted(words_of(holder)) if word in SIDE_WAYS), None)
    walls = walls_of(plan)
    if side is None or not walls:
        return None
    right, toward = plan_checks.ways(turn)
    way, centre = right * side[0] + toward * side[1], numpy.array([float(plan["w"]) / 2, float(plan["d"]) / 2])
    return max(walls, key=lambda wall: float((numpy.add(wall["from"], wall["to"]) / 2 - centre) @ way))


def along_spot(entry, wall, centre):
    """A wall relation set on `wall`: its spot the nearest point of the wall's line, on the side toward `centre`."""
    spot = on_line(numpy.asarray(entry["spot"], float), wall)
    entry.update(wall=wall_part(wall), side=off_line(centre, wall)[1], spot=[round(float(value), 3) for value in spot])


def room_walls(found, items, rows, plan, turn, inventory, tied=None):
    """Each wall relation of an item outlining the whole room (outlines_room) on a wall of its own: the wall its
    holder's id names (named_wall), at its spot's nearest point on it; else, where the concept does not place it
    (seen_spot, for the walls item), the middle of the wall nearest its spot no such relation before it holds. Those
    left within WALL_APART of one another on one wall spread evenly along it (spread_room)."""
    walls, held = walls_of(plan), []
    centre = numpy.array([float(plan["w"]) / 2, float(plan["d"]) / 2])
    for entry in found:
        if entry.get("how") != "wall" or not outlines_room(items[entry["item"]], plan):
            continue
        row = rows[entry["row"]]
        anchor = row.get("anchor") or ""
        holder = rows.get(anchor[3:]) if anchor.startswith("on:") else None
        wall = named_wall(holder, plan, turn) if holder is not None else None
        if wall is not None:
            along_spot(entry, wall, centre)
            entry["why"] = f"against the wall {holder['id']} names, as the concept's viewer sees it"
        elif entry["item"] != plan_checks.WALLS_ITEM or seen_spot(row, plan, inventory) is None:
            taken, need = {wall_key(other["wall"]) for other in held}, run_needed(
                row, pieces_at(entry["item"], row, plan, tied or {}))
            long_enough = [wall for wall in walls if wall_length(wall) >= need] or [max(walls, key=wall_length)]
            free = [wall for wall in long_enough if wall_key(wall) not in taken] or long_enough
            wall = min(free, key=lambda wall: off_line(numpy.asarray(entry["spot"], float), wall)[0])
            entry["spot"] = numpy.add(wall["from"], wall["to"]) / 2
            along_spot(entry, wall, centre)
            entry["why"] = "against the middle of the free wall nearest its spot: its plan item outlines the whole room"
        held.append(entry)
    spread_room(held, centre)


def spread_room(held, centre):
    """Whole-room wall relations on one wall within WALL_APART of one another along it, set evenly along it."""
    by_wall = {}
    for entry in held:
        by_wall.setdefault(wall_key(entry["wall"]), []).append(entry)
    for entries in by_wall.values():
        start, end = numpy.asarray(entries[0]["wall"]["from"], float), numpy.asarray(entries[0]["wall"]["to"], float)
        run = (end - start) / max(float(numpy.linalg.norm(end - start)), 1e-9)
        entries.sort(key=lambda entry: float((numpy.asarray(entry["spot"], float) - start) @ run))
        alongs = [float((numpy.asarray(entry["spot"], float) - start) @ run) for entry in entries]
        if all(after - before >= WALL_APART for before, after in zip(alongs, alongs[1:])):
            continue
        for number, entry in enumerate(entries):
            entry["spot"] = start + (end - start) * (number + 1) / (len(entries) + 1)
            along_spot(entry, entry["wall"], centre)
            entry["why"] += f"; spread along its wall with the {len(entries) - 1} other(s) at its spot"


def openings_of(plan):
    """The plan's openings with their kinds (a data plan's doors are doors)."""
    kinds = [opening.get("kind") or "door" for opening in plan.get("openings") or []]
    return [dict(opening, kind=kinds[number] if number < len(kinds) else "door")
            for number, opening in enumerate(design_shell.plan_openings(plan))]


def kind_word(row):
    return next((word for word in ("window", "door", "gate", "hatch", "shutter")
                 if word in {found.removesuffix("s") for found in words_of(row)}), "door")


def on_line(spot, wall):
    """The point of a wall's line segment nearest a plan spot."""
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    run = end - start
    return start + run * float(numpy.clip((spot - start) @ run / max(float(run @ run), 1e-9), 0.0, 1.0))


def wall_part(wall):
    return {key: wall[key] for key in ("from", "to", "thick")} if wall else None


def cut_in(spot, row, item, plan, standing=()):
    """A relation in an opening cut for the row (`cut`) where its spot meets the nearest wall with room for it beside
    the openings the relations `standing` already put on it (has_room; 2026-11-06: street's second 3 m roller shutter
    cut on the 4.61 m wall its restaurant door and window stood in, 7.5 m of openings), else the nearest (one with
    none on it taken as it is, a short one keeping it at its middle: camp's dome facets), kept
    OPENING_ROOM and the wall's thickness inside its ends (camp's dome windows were cut on their walls' corners): the
    row's width, from its item's base (a window from WINDOW_SILL) to its top; None where the plan draws no wall."""
    walls = walls_of(plan)
    if not walls:
        return None
    size = row.get("size") or [1.0, 0.1, design_shell.DOOR_HEAD]
    on_walls = wall_openings(standing)
    by_near = sorted(walls, key=lambda wall: off_line(spot, wall)[0])
    wall = by_near[0]
    if wall_key(wall) in on_walls and not has_room(wall, on_walls, float(size[0])):
        wall = next((wall for wall in by_near if has_room(wall, on_walls, float(size[0]))), wall)
    moved = wall is not by_near[0]
    base = float(((plan.get("shapes") or {}).get(item[0]) or {}).get("base") or 0.0)
    sill = base or (WINDOW_SILL if kind_word(row) == "window" else 0.0)
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    length = float(numpy.linalg.norm(end - start))
    run = (end - start) / max(length, 1e-9)
    keep = float(size[0]) / 2 + OPENING_ROOM + float(wall.get("thick") or 0.0)
    at = start + run * kept_along(float((on_line(spot, wall) - start) @ run), length, keep)
    return {"how": "in", "opening": {"at": [round(float(value), 3) for value in at],
                                     "wide": float(size[0]), "sill": sill, "head": round(sill + float(size[2]), 3),
                                     "cut": True},
            "wall": wall_part(wall), "why": f"in an opening cut for it where it meets the nearest wall"
                                            f"{' with room beside its openings' if moved else ''}: the plan has no "
                                            f"free {kind_word(row)} opening"}


def has_room(wall, on_walls, wide):
    """Whether a wall holds an opening `wide` beside those on it ({wall's (from, to): (wall, [(row, opening)])}, as
    wall_openings), all at their widths OPENING_ROOM apart and OPENING_ROOM and its thickness inside its ends."""
    wides = [float(opening["wide"]) for _, opening in on_walls.get(wall_key(wall), (None, []))[1]] + [wide]
    ends = 2 * (OPENING_ROOM + float(wall.get("thick") or 0.0))
    return sum(wides) + OPENING_ROOM * (len(wides) - 1) + ends <= wall_length(wall) + 1e-9


def kept_along(along, length, keep):
    """`along` a wall `length` long moved the least that keeps it `keep` inside both ends; its middle where it is too
    short."""
    return min(max(along, keep), length - keep) if length >= 2 * keep else length / 2


def widened(opening, row, wall):
    """A plan opening at least as wide as the row that fills it (the plan's sizes are estimates, the built one is
    laid): one narrower is cut again (`cut`) at the row's width, its middle slid along its wall the least that keeps
    it within the wall's ends, the plan's own spot and width kept as `drawn` for spread (stairwell's plan drew its 1 m
    apartment doors and gate in 0.39 m openings, so the assembly shrank them to 0.39 m, #36)."""
    found = {key: opening[key] for key in ("at", "wide", "sill", "head")}
    wide = float((row.get("size") or [0.0])[0])
    if wide <= float(opening["wide"]):
        return found
    at = numpy.asarray(opening["at"], float)
    if wall:
        start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
        length = float(numpy.linalg.norm(end - start))
        run = (end - start) / max(length, 1e-9)
        at = start + run * (min(max(float((at - start) @ run), wide / 2), length - wide / 2) if length >= wide
                            else length / 2)
    return {**found, "at": [round(float(value), 3) for value in at], "wide": wide, "cut": True,
            "drawn": {"at": found["at"], "wide": found["wide"]}}


# Openings one wall holds, spread apart where they meet at their built widths, stand at least this far apart, and
# this far plus the wall's thickness inside its ends (clear of the corner's other wall), metres.
OPENING_ROOM = 0.2


def wall_openings(found):
    """{wall's (from, to): (the wall, [(row, its opening)])} of the relations' openings (each piece's too)."""
    walls = {}
    for entry in found:
        for piece in entry.get("pieces") or [entry]:
            if piece.get("how") == "in" and piece.get("wall"):
                key = (tuple(piece["wall"]["from"]), tuple(piece["wall"]["to"]))
                walls.setdefault(key, (piece["wall"], []))[1].append((entry["row"], piece["opening"]))
    return walls


def spread_lefts(alongs, wides, length, room):
    """The left ends along a wall `length` long of openings at `alongs` (middles, in order) `wides` wide: each kept
    at its own spot or pushed on past the one before by OPENING_ROOM, then pulled back from the wall's far end by as
    much, all `room` inside its ends; None where the wall cannot hold them so."""
    lefts = []
    for number, (along, wide) in enumerate(zip(alongs, wides)):
        lefts.append(max(along - wide / 2, lefts[-1] + wides[number - 1] + OPENING_ROOM if lefts else room))
    limit = length - room
    for number in reversed(range(len(lefts))):
        lefts[number] = min(lefts[number], limit - wides[number])
        limit = lefts[number] - OPENING_ROOM
    return lefts if lefts and lefts[0] >= room - 1e-9 else None


def spread(found):
    """Each wall's openings that meet one another cut at their built widths spread apart along it in their order
    along it (spread_lefts), each moved one cut again (`cut`); a wall that cannot hold them all at their built widths
    keeps those the plan drew narrower as it drew them, named in the [{wall, rows, why}] returned (habitat's door and
    window, 1 m and 1.5 m, drawn 0.42 m apart, #36)."""
    crowded = []
    for wall, openings in wall_openings(found).values():
        start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
        length = float(numpy.linalg.norm(end - start))
        run = (end - start) / max(length, 1e-9)
        openings = sorted(openings, key=lambda pair: float((numpy.asarray(pair[1]["at"], float) - start) @ run))
        alongs = [float((numpy.asarray(opening["at"], float) - start) @ run) for _, opening in openings]
        wides = [float(opening["wide"]) for _, opening in openings]
        if all(after - before >= (wide + next_wide) / 2 - 1e-9 for before, after, wide, next_wide
               in zip(alongs, alongs[1:], wides, wides[1:])):
            continue
        lefts = spread_lefts(alongs, wides, length, OPENING_ROOM + float(wall.get("thick") or 0.0))
        if lefts is None:
            for _, opening in openings:
                if "drawn" in opening:
                    opening.update(opening.pop("drawn"))
                    opening.pop("cut")
            crowded.append({"wall": wall, "rows": [row for row, _ in openings],
                            "why": f"the wall's {length:.2f} m cannot hold its openings at their built widths "
                                   f"({sum(wides):.2f} m) with {OPENING_ROOM:g} m between them and at its ends"})
            continue
        for (_, opening), along, left, wide in zip(openings, alongs, lefts, wides):
            if abs(left + wide / 2 - along) > 1e-6:
                opening.update(at=[round(float(value), 3) for value in start + run * (left + wide / 2)], cut=True)
    return crowded


# A face relation's holder as the scene record lays it, (plan middle, way, base): kept on the relation while the
# relations are derived, for face_spread, never written.
LINE = "_holder"


def reach(row, way, run):
    """Metres a row's model stands along the plan way `run`, laid along `way` as the scene record lays it
    (model_axes)."""
    size = row.get("size") or [0.0, 0.0, 0.0]
    model_x, model_z = model_axes(way, row)
    return abs(float(model_x @ run)) * float(size[0]) + abs(float(model_z @ run)) * float(size[1])


def face_pieces(entry, item, row, plan, run):
    """[{entry, number, at, way, along, before, after, band}] each piece of a face relation stands at against its face (its
    `spots`, else piece_middles), `along` its middle's metres along `run` from the holder's middle, `before` and
    `after` its reach on either side, a moving door's recess room on its room side (both sides where it names none),
    `band` its foot and top."""
    recess, size = entry.get("recess"), row.get("size") or [0.0, 0.0, 0.0]
    placed = piece_middles(item, row, plan)
    if entry.get("spots"):
        placed = [(numpy.asarray(spot, float), way) for spot, (_, way) in zip(entry["spots"], placed)]
    base = float(((plan.get("shapes") or {}).get(item[0]) or {}).get("base") or 0.0)
    holder_middle = numpy.asarray(entry[LINE][0], float)
    found = []
    for number, (spot, way) in enumerate(placed):
        half = reach(row, way, run) / 2
        room_way = (recess.get("room_ways") or [recess.get("room_way")])[number] if recess else None
        side = float(numpy.asarray(room_way, float) @ run) if room_way and any(room_way) else 0.0
        room = float(recess["room"]) if recess else 0.0
        found.append({"entry": entry, "number": number, "at": numpy.asarray(spot, float), "way": way,
                      "along": float((numpy.asarray(spot, float) - holder_middle) @ run),
                      "before": half + (room if side <= 0 else 0.0), "after": half + (room if side >= 0 else 0.0),
                      "band": (base, base + float(size[2]))})
    return found


def meet(first, second):
    """Whether two pieces' heights overlap."""
    return first["band"][0] < second["band"][1] - 1e-9 and second["band"][0] < first["band"][1] - 1e-9


def spread_face(pieces, half):
    """The left ends along a face `half` long either side of its middle of `pieces` (in order along it): each kept at
    its own spot or pushed on past every earlier one its height meets by OPENING_ROOM, then pulled back from the
    face's far end and every later one by as much, all OPENING_ROOM inside its ends; None where the face cannot hold
    them so."""
    lefts = []
    for number, piece in enumerate(pieces):
        least = [lefts[other] + pieces[other]["before"] + pieces[other]["after"] + OPENING_ROOM
                 for other in range(number) if meet(pieces[other], piece)]
        lefts.append(max([piece["along"] - piece["before"], -half + OPENING_ROOM, *least]))
    for number in reversed(range(len(pieces))):
        most = [lefts[other] - OPENING_ROOM for other in range(number + 1, len(pieces)) if meet(pieces[other],
                                                                                              pieces[number])]
        wide = pieces[number]["before"] + pieces[number]["after"]
        lefts[number] = min([lefts[number], half - OPENING_ROOM - wide, *(limit - wide for limit in most)])
    clear = all(lefts[later] >= lefts[number] + pieces[number]["before"] + pieces[number]["after"] + OPENING_ROOM
                - 1e-9 for number in range(len(pieces)) for later in range(number + 1, len(pieces))
                if meet(pieces[number], pieces[later]))
    return lefts if clear and lefts[0] >= -half + OPENING_ROOM - 1e-9 else None


def kept_on_face(piece, half):
    """A piece's `along` moved the least that keeps it inside a face `half` long either side of its middle, as the
    assembly keeps a face thing within its holder's built span (fitting.on_face)."""
    return min(max(piece["along"], -half + piece["before"]), half - piece["after"])


def face_spread(found, items, rows, plan, inventory, kinds):
    """The pieces against each holder's face spread along it (faces_spread); on a face too short for them all, each
    thing the plan draws on another side of its holder turned to that side (turned_toward) and the faces spread
    again; a face still too short keeps its things as drawn, named in the [{holder, holder row, face, rows, why}]
    returned (street's 3 m window, stairwell entrance and roller shutters laid at their built widths on 1.74 m items,
    its sign over three air conditioners, #36)."""
    while True:
        crowded = faces_spread(found, items, rows, plan, inventory, kinds)
        if not [turned for _, entries in crowded for turned in [turned_toward(entries, items)] if turned]:
            return [named for named, _ in crowded]


def turned_toward(entries, items):
    """Each face relation of a crowded face (`entries`, but a door's, whose recess is cut at its face) whose item the
    plan draws outside its holder's box turned to the holder's side toward it (side_toward) where that is another
    side: whether any turned (one drawn on its holder's spot, or on the walls item: a facade's window, stays).
    2026-11-07: storage's three pillar pipes, drawn on the pillar's N, S and E sides, all laid on the S side the
    concept shows, crowded there and laid in one another."""
    turned = False
    for entry in entries:
        item, holder = items[entry["item"]], items[entry["holder"]]
        side = None if inside(item, holder) or entry.get("recess") or entry["holder"] == plan_checks.WALLS_ITEM \
            else side_toward(item, holder)
        if side and side != entry["face"]:
            entry["why"] += f"; turned to its {side} side, toward it on the plan: its {entry['face']} side too short"
            entry["face"], turned = side, True
    return turned


def faces_spread(found, items, rows, plan, inventory, kinds):
    """The pieces against each holder's face that would overlap at their built sizes (along it and in height, each
    kept inside the face's ends as the assembly keeps it: kept_on_face) spread
    along it in the order the plan draws them (spread_face), each relation of a piece moved given its pieces' `spots`
    and a moving door its recess at them; [({holder, holder row, face, rows, why}, its relations)] of each face too
    short for them all, its things kept as drawn."""
    faces, crowded = {}, []
    for entry in found:
        if entry["how"] == "face" and LINE in entry:
            faces.setdefault((entry["holder"], entry["holder row"], entry["face"]), []).append(entry)
    for (holder, holder_row, face), entries in faces.items():
        out = numpy.asarray(FACES[face], float)
        run = numpy.array([-out[1], out[0]])
        line = entries[0][LINE]
        half = reach(rows[holder_row], line[1], run) / 2
        each = sorted((sorted(face_pieces(entry, items[entry["item"]], rows[entry["row"]], plan, run),
                              key=lambda piece: piece["along"]) for entry in entries),
                      key=lambda own: sum(piece["along"] for piece in own) / max(len(own), 1))
        pieces = [piece for own in each for piece in own]  # an item's pieces together, items in their plan order
        kept = [kept_on_face(piece, half) for piece in pieces]
        if all(kept[later] - pieces[later]["before"] >= kept[number] + piece["after"] - 1e-9
               or not meet(piece, pieces[later])
               for number, piece in enumerate(pieces) for later in range(number + 1, len(pieces))):
            continue
        lefts = spread_face(pieces, half)
        if lefts is None:
            crowded.append(({"holder": holder, "holder row": holder_row, "face": face,
                             "rows": sorted({piece["entry"]["row"] for piece in pieces}),
                             "why": f"the face's {2 * half:.2f} m cannot hold its things at their built widths with "
                                    f"{OPENING_ROOM:g} m between those that meet in height and at its ends"},
                            entries))
            continue
        for piece, left in zip(pieces, lefts):
            piece["at"] = piece["at"] + run * (left + piece["before"] - piece["along"])
            piece["moved"] = abs(left + piece["before"] - piece["along"]) > 1e-6
        for entry in entries:
            own = sorted((piece for piece in pieces if piece["entry"] is entry), key=lambda piece: piece["number"])
            if not any(piece.get("moved") for piece in own):
                continue
            entry["spots"] = [[round(float(value), 3) for value in piece["at"]] for piece in own]
            if entry.get("recess"):
                entry["recess"] = recess_of(items[entry["item"]], rows[entry["row"]], entry[LINE], rows[holder_row],
                                            face, plan, inventory, kinds,
                                            [(numpy.asarray(spot, float), piece["way"])
                                             for spot, piece in zip(entry["spots"], own)])
    return crowded


def in_plan_opening(spot, row, plan, taken):
    """A relation in the plan's opening nearest `spot` (any, with none) that holds none yet, of the row's kind (a
    window a window's, a door a door's: camp's dome window took the dome door's opening, standing in its swing, #36),
    widened to the row (widened); None with none left."""
    word = kind_word(row)
    alike = [(number, opening) for number, opening in enumerate(openings_of(plan))
             if number not in taken and (opening["kind"] == "window") == (word == "window")]
    if not alike:
        return None
    number, opening = min(alike, key=lambda pair: float(numpy.linalg.norm(numpy.subtract(pair[1]["at"], spot)))
                          if spot is not None else pair[0])
    taken.add(number)
    walls = walls_of(plan)
    wall = min(walls, key=lambda wall: off_line(numpy.asarray(opening["at"], float), wall)[0]) if walls else None
    return {"how": "in", "opening": widened(opening, row, wall), "wall": wall_part(wall),
            "why": f"in the plan's {opening['kind']} opening {number + 1}"}


def piece_spots(item, row, plan, inventory):
    """Where each piece of an item stands on the plan: for an item the plan places where the scene record lays each
    (piece_middles: cockpit's four rear doors on one item, stacked in one opening, #36); for the walls item each of the
    row's concept boxes as it projects onto the plan, else its pieces spread along the longest wall."""
    if item[0] != plan_checks.WALLS_ITEM:
        return [spot for spot, _ in piece_middles(item, row, plan)]
    count = max(1, int(((plan.get("shapes") or {}).get(item[0]) or {}).get("count") or 1), int(row.get("count") or 1))
    seen = seen_spots(row, plan, inventory)
    if len(seen) >= count:
        return seen[:count]
    walls = walls_of(plan)
    if not walls:
        return [None] * count
    wall = max(walls, key=lambda wall: float(numpy.linalg.norm(numpy.subtract(wall["to"], wall["from"]))))
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    return [start + (end - start) * (number + 1) / (count + 1) for number in range(count)]


def in_opening(item, row, plan, inventory, taken, standing=()):
    """A door or window in an opening: each of its pieces (piece_spots) in the plan's nearest free opening, else in
    one cut for it on its nearest wall; one relation, or `pieces` one each; None where the plan draws no wall and no
    opening is left."""
    found = []
    for spot in piece_spots(item, row, plan, inventory):
        found.append(in_plan_opening(spot, row, plan, taken) or (
            cut_in(spot, row, item, plan, [*standing, *({"row": row["id"], **piece} for piece in found if piece)])
            if spot is not None else None))
    if not all(found):
        return None
    return found[0] if len(found) == 1 else {"how": "in", "pieces": found, "why": "each piece in its opening"}


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


def alike_holders(row, holder, rows, laid):
    """The rows like the row's named holder: the same anchor, a word of what it is shared (a console beside a control
    bank, never the chair before a desk), laid on the plan."""
    return [other for other in rows.values() if other["id"] in laid and other is not row
            and (other.get("anchor") or "floor") == (holder.get("anchor") or "floor")
            and kind_words(other) & kind_words(holder)]


def seen_holders(row, holder, rows, laid):
    """The rows the concept shows the row's things standing on (hub's 38 monitors on its control bank and consoles, the
    reading's anchor naming one): for each of its boxes the row like its named holder (alike_holders) whose box
    holds its foot, the named holder first; the named holder alone where none is seen."""
    alike = alike_holders(row, holder, rows, laid)
    shown = {found["id"]: found for box in plan_checks.boxes_of(row) if (found := standing_on(box, alike))}
    return [holder, *[found for found_id, found in shown.items() if found_id != holder["id"]]]


OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}


def at_edge(row, plan, inventory, turn):
    """A relation past the plan's edge for a wall row the plan writer left on the walls item where the plan draws no
    wall (street's building facades on its 5.6 m strip): the edge on the side of the view its concept box stands
    (left half: the viewer's left), at the edge's middle; None for any other row."""
    if holder_kind(row) != "wall" or walls_of(plan) or not box_of(row) or not inventory.get("picture"):
        return None
    right, _ = plan_checks.ways(turn)
    seen = box_of(row)
    side = snapped(-right if (seen[0] + seen[2]) / 2 < inventory["picture"][0] / 2 else right)
    wide, deep = float(plan["w"]), float(plan["d"])
    spot = {"N": [wide / 2, 0.0], "S": [wide / 2, deep], "W": [0.0, deep / 2], "E": [wide, deep / 2]}[side]
    return {"how": "edge", "edge": side, "spot": spot,
            "why": f"past the plan's {side} edge, the side of the view its concept box stands: the plan draws no wall"}


def edge_holder(edge, row):
    """(plan middle, plan way, base) of a wall row laid past the plan's edge as the scene record lays it
    (writer.related `edge`: its face on the edge's line, its body out past it, its long side along the edge)."""
    out = numpy.asarray(FACES[edge["edge"]], float)
    size = row.get("size") or [0.0, 0.0, 0.0]
    depth = min(float(size[0]), float(size[1])) if len(size) == 3 else 0.0
    return numpy.asarray(edge["spot"], float) + out * depth / 2, numpy.array([out[1], -out[0]]), 0.0


STAIR_WORDS = {"stair", "stairs", "staircase", "steps", "ramp", "ladder"}


def floor_spot(item, row, plan, inventory, taken_stairs):
    """Where a row on a floor stands when the plan writer left it on the walls item: a stair row at the plan's next
    stair (its footprint's middle, along its way up), else where its concept box projects onto the plan; None."""
    if item[0] != plan_checks.WALLS_ITEM:
        return None
    stairs = [number for number in range(len(plan.get("stairs") or [])) if number not in taken_stairs]
    if words_of(row) & STAIR_WORDS and stairs:
        taken_stairs.add(stairs[0])
        stair = plan["stairs"][stairs[0]]
        angle = math.radians(float(stair.get("angle") or 0.0))  # its way up: 0 east, 90 south (y runs south)
        spot = numpy.asarray(stair["points"], float).mean(axis=0)
        return {"spot": [round(float(value), 3) for value in spot], "way": [round(math.cos(angle), 6) + 0.0,
                                                                            round(math.sin(angle), 6) + 0.0],
                "why": f"at the plan's stair {stairs[0] + 1}"}
    spot = seen_spot(row, plan, inventory)
    if spot is None:
        return None
    return {"spot": [round(float(value), 3) for value in spot], "why": "where its concept box projects onto the plan"}


RAMP_WORDS = {"ramp", "ramps"}


def up_to_level(item, row, plan):
    """A ramp row's relation to the raised level it climbs to (a plan level over the floor, the nearest to its item:
    airlock's porch deck): its long side (the row's size, else its item's) run straight up to that level's nearest
    edge, its high end on the edge's line, its spot its middle; None for any other row, or with no raised level."""
    if not kind_words(row) & RAMP_WORDS or item[0] == plan_checks.WALLS_ITEM:
        return None
    here = middle(item)
    edges = [(off_line(here, {"from": start, "to": end})[0], level, numpy.asarray(start, float),
              numpy.asarray(end, float), numpy.asarray(level["points"], float).mean(axis=0))
             for level in plan.get("levels") or [] if float(level.get("height") or 0.0) > 0.0
             and len(level.get("points") or []) >= 3
             for start, end in zip(level["points"], [*level["points"][1:], level["points"][0]])]
    if not edges:
        return None
    _, level, start, end, inner = min(edges, key=lambda edge: edge[0])
    size = row.get("size") if isinstance(row.get("size"), list) and len(row["size"]) == 3 else item[3:5]
    length, wide = max(float(size[0]), float(size[1])), min(float(size[0]), float(size[1]))
    run = (end - start) / max(float(numpy.linalg.norm(end - start)), 1e-9)
    way = numpy.array([-run[1], run[0]])
    way = way if way @ (inner - start) > 0 else -way  # into the level
    reach = float(numpy.linalg.norm(end - start))
    share = float(numpy.clip((here - start) @ run, min(wide / 2, reach / 2), max(reach - wide / 2, reach / 2)))
    spot = start + run * share - way * length / 2
    height = float(level["height"])
    return {"how": "ramp", "spot": [round(float(value), 3) for value in spot],
            "way": [round(float(value), 6) + 0.0 for value in way],
            "edge": [[round(float(value), 3) for value in point] for point in (start, end)], "height": height,
            "why": f"up to the plan's level {level.get('name', '')!r} at {height:g} m, its high end on its edge"}


def stair_sides(plan, count):
    """[{spot, way}] of `count` pieces along the plan's stairs' sides (a railing on a staircase): each stair's two
    sides in turn, each way the stair's way up (0 east, 90 south); the pieces one side takes spread evenly along it,
    each the middle of its share (stairwell's 12 railings on 4 stairs stood three at each side's middle, 2026-11-04
    audit)."""
    stairs = plan.get("stairs") or []
    sides = 2 * len(stairs)
    found = []
    for number in range(count):
        side = number % sides
        stair, left = stairs[side // 2], side % 2 == 0
        angle = math.radians(float(stair.get("angle") or 0.0))
        way = numpy.array([math.cos(angle), math.sin(angle)])
        across = numpy.array([-way[1], way[0]])
        points = numpy.asarray(stair["points"], float)
        middle_point, half = points.mean(axis=0), float(numpy.ptp(points @ across)) / 2
        run = float(numpy.ptp(points @ way))
        share, on_side = number // sides, len(range(side, count, sides))
        spot = middle_point + across * half * (1 if left else -1) + way * run * ((share + 0.5) / on_side - 0.5)
        found.append({"how": "floor", "spot": [round(float(value), 3) for value in spot],
                      "way": [round(float(value), 6) + 0.0 for value in way],
                      "why": f"along the {'left' if left else 'right'} side of the plan's stair {side // 2 + 1}"})
    return found


def relation(item, row, rows, plan, inventory, laid, taken, turn, taken_stairs, kinds, pieces=1, standing=()):
    """One item's relation (module docstring) for its row (laying `pieces` there), or (None, why) when nothing holds
    it; `standing` the relations found before it (where its openings' walls have room)."""
    anchor = row.get("anchor") or "floor"
    holder = rows.get(anchor[3:]) if anchor.startswith("on:") else None
    if anchor.startswith("on:") and holder is None:
        return None, f"its holder {anchor[3:]} is no row of the inventory"
    kind = "wall" if anchor == "wall" else "ceiling" if anchor in ("ceiling", "roof") else (
        holder_kind(holder) if holder is not None else None)
    edge = at_edge(holder, plan, inventory, turn) if holder is not None else None
    if edge:  # on a wall row laid past the plan's edge: against its face toward the plan
        found = {"how": "face", "holder": plan_checks.WALLS_ITEM, "holder row": holder["id"],
                 "face": OPPOSITE[edge["edge"]], "why": f"against {holder['id']}'s face toward the place"}
        line = edge_holder(edge, holder)
        recess = recess_of(item, row, line, holder, found["face"], plan, inventory, kinds)
        return {**found, **({"recess": recess} if recess else {}), **spots_entry(item, row, plan, recess),
                LINE: line}, None
    if holder is not None and holder["id"] in laid and kind not in ("wall", "floor"):  # an item of its own, or tied to its holder's
        items, shown = plan_items(plan), seen_holders(row, holder, rows, laid)
        pairs = [(other, name) for other in shown for name in laid[other["id"]]]
        if not any(inside(item, items[name]) for _, name in pairs):  # its spot in another like it: that one holds it
            pairs = [(other, name) for other in alike_holders(row, holder, rows, laid) for name in laid[other["id"]]
                     if inside(item, items[name])] or pairs
        nearest = min(pairs, key=lambda pair: float(numpy.linalg.norm(middle(items[pair[1]]) - middle(item))))
        found = {**held(item, row, nearest[0], [nearest[1]], items, turn, room_height(plan)),
                 "holder row": nearest[0]["id"]}
        holder_item = items[nearest[1]]
        if found["how"] == "within" and hangs(item, holder_item, plan):
            found["hangs"] = True
        holder_base = float(((plan.get("shapes") or {}).get(holder_item[0]) or {}).get("base") or 0.0)
        recess = recess_of(item, row, (middle(holder_item), item_way(holder_item, nearest[0]), holder_base),
                           nearest[0], found["face"], plan, inventory, kinds) if found["how"] == "face" else None
        if recess:
            found["recess"] = recess
        if found["how"] == "face":
            found.update(spots_entry(item, row, plan, recess))
            found[LINE] = (middle(holder_item), item_way(holder_item, nearest[0]), holder_base)
        if len(shown) > 1:
            found["why"] += (f" (its things stand on {len(shown)} rows in the concept: "
                             f"{', '.join(other['id'] for other in shown)}; the nearest on the plan)")
        return found, None
    if holder is not None and holder["id"] not in laid and words_of(holder) & STAIR_WORDS and plan.get("stairs"):
        count = max(1, int(((plan.get("shapes") or {}).get(item[0]) or {}).get("count") or 1),
                    int(row.get("count") or 1) if item[0] == plan_checks.WALLS_ITEM else 1)
        return {"how": "floor", "pieces": stair_sides(plan, count), "stairs": count,
                "why": f"along {holder['id']}'s stairs"}, None
    if kind is None and holder is not None and design_shell.fills_opening(row):
        kind = "wall"  # a door or window of a structure the plan's shell lays (camp's airlock entrance): in its wall
    spanning = kind == "wall" and spans(row)
    if spanning:
        kind = "ceiling"
    if kind in ("floor", "ceiling"):
        return {"how": kind, **(floor_spot(item, row, plan, inventory, taken_stairs) or {}),
                **({"to roof": True} if kind == "ceiling" and under_roof(row) else {}),
                "why": f"on the place's {kind}" + (": its words say it spans the room under the roof, no wall"
                                                   if spanning else "")}, None
    if kind != "wall":
        return None, (f"its holder {holder['id']} is neither laid on the plan nor a wall, floor or roof"
                      if holder is not None else None)
    found = in_opening(item, row, plan, inventory, taken, standing) if design_shell.fills_opening(row) else None
    found = found or on_wall(item, row, plan, inventory, pieces)
    return (found, None) if found else (None, "it stands on a wall, and the plan draws none")


def plan_items(plan):
    return items_of(plan)[0]


def pieces_at(name, row, plan, tied):
    """How many pieces the scene record lays at a plan item of the row (its writer.pieces_of): its shape's count, and
    what the row's items fall short of its own count laid one more an item in turn from the first in the plan's order
    (2026-11-06: hangar's 8 pipes on 7 items, its first laying 2, both at its one wall spot)."""
    shapes, names = plan.get("shapes") or {}, tied.get(row["id"]) or []
    if name not in names:
        return int((shapes.get(name) or {}).get("count") or 1)
    counts = [int((shapes.get(each) or {}).get("count") or 1) for each in names]
    for turn in range(max(int(row.get("count") or 1) - sum(counts), 0)):
        counts[turn % len(counts)] += 1
    return counts[names.index(name)]


def packed(alongs, length, long):
    """Alongs [metres] of pieces `long` long on a run `length` long, at least their length and PIECE_GAP apart: as
    they are where they already are, else the least run of them round their middle, kept inside the run's ends."""
    alongs, pitch = sorted(alongs), long + PIECE_GAP
    if all(after - before >= pitch - 1e-6 for before, after in zip(alongs, alongs[1:])):
        return alongs
    total = (len(alongs) - 1) * pitch
    low, high = long / 2, length - long / 2 - total
    first = min(max(float(numpy.mean(alongs)) - total / 2, low), high) if high >= low else (length - total) / 2
    return [first + number * pitch for number in range(len(alongs))]


# Wall things of one row nearer than this, metres, stand at one spot (scene_record/gates.SAME_SPOT): parted.
ONE_SPOT = 0.02
# Two wall things' built boxes may meet by this much, metres, and stand clear of each other (scene_record/gates'
# laid-as-designed judges by it): a touch, never one in the other.
WALL_TOUCH = 0.05
# Two walls meet in a chain where their ends lie within this of each other, metres; a run of one piece goes round a
# meeting no sharper than ROUND_BEND degrees (a round wall's facets), a run of several round a corner up to
# CORNER_BEND (never doubling back along a wall's other face).
JOIN = 0.02
ROUND_BEND = 30.0
CORNER_BEND = 120.0


def corner(tip, came, near, leg):
    """Where a chain's last leg (ending at `tip`, running `came`) meets the next wall's line (from `near`, running
    `leg`): their lines' crossing, else `near` where they run alike."""
    across = float(came[0] * leg[1] - came[1] * leg[0])
    if abs(across) < 1e-9:
        return near
    share = float((near - tip)[0] * leg[1] - (near - tip)[1] * leg[0]) / across
    return tip + came * share


def chain_of(wall, walls, bend):
    """[plan point] of the walls joined end to end with `wall` (its from to its to, then on past each end), each
    meeting turning less than `bend` degrees, the least turning where several meet; two walls join where an end of
    one lies within JOIN or the walls' thickness of the other's (the plan draws walls on their middle lines, so a
    rectangle's walls cross at its corners: quarters'), the chain turning where their lines cross."""
    def onward(points):
        while True:
            tip, came = points[-1], points[-1] - points[-2]
            ahead = []
            for other in walls:
                ends = [numpy.asarray(other["from"], float), numpy.asarray(other["to"], float)]
                reach = max(JOIN, float(other.get("thick") or 0.0), float(wall.get("thick") or 0.0))
                for near, far in (ends, ends[::-1]):
                    leg = far - near
                    if float(numpy.linalg.norm(near - tip)) <= reach and float(numpy.linalg.norm(leg)) > reach and \
                            not any(float(numpy.linalg.norm(far - point)) <= reach for point in points):
                        turn = math.degrees(math.acos(float(numpy.clip(
                            (came @ leg) / max(float(numpy.linalg.norm(came) * numpy.linalg.norm(leg)), 1e-9),
                            -1.0, 1.0))))
                        if turn < bend:
                            ahead.append((turn, corner(tip, came, near, leg), far))
            if not ahead:
                return points
            _, met, far = min(ahead, key=lambda found: found[0])
            points[-1:] = [met, far]
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    forward = onward([start, end])
    backward = onward([end, start])
    return numpy.asarray(backward[:1:-1] + forward if len(backward) > 2 else forward)


def chain_point(chain, along):
    """The point `along` metres down a chain of points, and the leg it lies on."""
    legs = numpy.diff(chain, axis=0)
    for number, (point, leg) in enumerate(zip(chain, legs)):
        length = float(numpy.linalg.norm(leg))
        if along <= length or number == len(legs) - 1:
            return point + leg * min(along, length) / max(length, 1e-9), number
        along -= length


def chain_length(chain):
    return float(numpy.linalg.norm(numpy.diff(chain, axis=0), axis=1).sum())


def wall_pieces(entry, item, row, count, walls, bend=CORNER_BEND):
    """Each piece of a wall relation laying `count` pieces (its item's own spots, along its long middle line as the
    scene record spreads them; the walls item's all at the relation's spot) as a wall relation of its own: brought
    onto its wall's chain of walls (chain_of: round a corner, a round wall's facets), packed their built length apart
    (packed), each flat along one straight run of the chain, never bent round a corner (flat_alongs), its wall the
    chord of the run it covers, so each piece has a face as long as it is (2026-11-04 audit: the workshop's 25 tools
    at one spot on a 0.96 m wall; 2026-11-06: hangar's second 32 m pipe of LARGE PIPES 1 laid as a 31 m diagonal
    across its left and front walls' corner, galley's cabinets and hub's panels round theirs)."""
    wall = entry["wall"]
    chain = chain_of(wall, walls, bend)
    length, long = chain_length(chain), max(built_long(row), PIECE_GAP)
    if item[0] == plan_checks.WALLS_ITEM:
        spots = [numpy.asarray(entry["spot"], float)] * count
    else:
        x, y, wide, deep = (float(value) for value in item[1:5])
        line = ([[x, y + deep / 2], [x + wide, y + deep / 2]] if wide >= deep else
                [[x + wide / 2, y], [x + wide / 2, y + deep]])
        first, last = numpy.asarray(line, float)
        spots = [first + (last - first) * (number + 0.5) / count for number in range(count)]
    alongs = [chain_along(chain, spot) for spot in spots]
    runs, clear = straight_runs(chain), built_deep(row) + PIECE_GAP
    found = []
    for along in flat_alongs(packed(alongs, length, long), runs, long, clear):
        (low, _), (high, _) = chain_point(chain, max(along - long / 2, 0.0)), chain_point(chain, along + long / 2)
        middle_point, way = (low + high) / 2, (high - low) / max(float(numpy.linalg.norm(high - low)), 1e-9)
        low, high = middle_point - way * long / 2, middle_point + way * long / 2  # the chord as long as the piece
        found.append({"how": "wall", "wall": {"from": [round(float(value), 4) for value in low],
                                              "to": [round(float(value), 4) for value in high],
                                              "thick": entry["wall"].get("thick")},
                      "side": entry["side"], "spot": [round(float(value), 3) for value in chain_point(chain, along)[0]],
                      **({"height": entry["height"]} if "height" in entry else {}),
                      "why": entry["why"] + "; packed along its walls with its row's other pieces"})
    return found


def built_deep(row):
    """The row's built depth off what holds it: its size's shorter ground side, 0 for a row with no size."""
    size = row.get("size")
    return min(float(size[0]), float(size[1])) if isinstance(size, list) and len(size) == 3 else 0.0


def straight_runs(chain):
    """[(start, end)] metres down a chain of the runs a straight piece lies flat along: its legs, joined where they
    meet no sharper than ROUND_BEND degrees (a round wall's facets), broken at each corner."""
    legs = numpy.diff(chain, axis=0)
    lengths = numpy.linalg.norm(legs, axis=1)
    runs, reach = [[0.0, float(lengths[0])]], float(lengths[0])
    for came, leg, length in zip(legs, legs[1:], lengths[1:]):
        turn = math.degrees(math.acos(float(numpy.clip((came @ leg) / max(float(numpy.linalg.norm(came)) *
                                                                            float(length), 1e-9), -1.0, 1.0))))
        if turn > ROUND_BEND:
            runs.append([reach, reach])
        reach += float(length)
        runs[-1][1] = reach
    return [tuple(run) for run in runs]


def onto_runs(middles, runs, long, clear, bounded=True):
    """Middles of pieces `long` long, from `middles` (in order) each moved on the least that lays it flat inside one
    run, PIECE_GAP past the one before, and `clear` past a corner the one before ends within `clear` of (the two
    would meet in the corner's room); the last run unbounded unless `bounded`. None where one fits no run."""
    placed, half = [], long / 2
    for along in middles:
        if placed:
            along = max(along, placed[-1] + long + PIECE_GAP)
        for number, (low, high) in enumerate(runs):
            high = high if bounded or number < len(runs) - 1 else math.inf
            spot = max(along, low + half)
            if placed and placed[-1] + half < low and placed[-1] + half > low - clear - 1e-9:
                spot = max(spot, low + clear + half)
            if spot + half <= high + 1e-9:
                placed.append(spot)
                break
        else:
            return None
    return placed


def holds_flat(chain, row, count):
    """Whether a chain of walls holds `count` of the row's pieces each flat along one of its straight runs."""
    long = max(built_long(row), PIECE_GAP)
    return onto_runs([0.0] * count, straight_runs(chain), long, built_deep(row) + PIECE_GAP) is not None


def flat_alongs(alongs, runs, long, clear):
    """Middles of pieces `long` long laid flat on a chain's straight runs (straight_runs) nearest `alongs`: a piece
    not fitting before a corner starts on the next run, and those then past the chain's end are pulled back the same
    way from it; where the runs cannot hold them all flat, those that fit and the rest at the end of the longest run
    (its relation named `short` by on_wall)."""
    total = runs[-1][1]
    forward = onto_runs(sorted(alongs), runs, long, clear, bounded=False)
    if forward[-1] + long / 2 <= total + 1e-9:
        return forward
    mirrored = [(total - high, total - low) for low, high in reversed(runs)]
    back = onto_runs([total - along for along in reversed(forward)], mirrored, long, clear)
    if back is not None:
        return [total - along for along in reversed(back)]
    low, high = max(runs, key=lambda run: run[1] - run[0])
    return [along if along + long / 2 <= total + 1e-9 else max(low, high - long) + long / 2 for along in forward]


def chain_along(chain, spot, near=None):
    """Metres down a chain of points to the point of it nearest a plan spot; of several as near (a chain round a
    closed room passes its walls twice), the one nearest `near` metres down it, else the first."""
    found, reach = [], 0.0
    for start, end in zip(chain, chain[1:]):
        run = end - start
        length = float(numpy.linalg.norm(run))
        share = float(numpy.clip((spot - start) @ run / max(length ** 2, 1e-9), 0.0, 1.0))
        found.append((float(numpy.linalg.norm(spot - (start + run * share))), reach + share * length))
        reach += length
    if near is None:
        return min(found)[1]
    least = min(off for off, _ in found)
    return min((along for off, along in found if off <= least + 1e-6), key=lambda along: abs(along - near))


def floor_pieces(entry, row, count, plan, inventory):
    """[spot] of a floor or ceiling relation's `count` pieces at its one spot (a row the plan writer left on the walls
    item): where its concept boxes project, one a piece, when it has that many apart; else packed along the plan's x
    round its spot."""
    seen = seen_spots(row, plan, inventory)[:count]
    pitch = built_long(row) + PIECE_GAP
    if len(seen) == count and all(float(numpy.linalg.norm(numpy.subtract(one, two))) >= pitch
                                  for number, one in enumerate(seen) for two in seen[number + 1:]):
        return [numpy.asarray(spot, float) for spot in seen]
    spot = numpy.asarray(entry["spot"], float)
    return [spot + numpy.array([along - (count - 1) * pitch / 2, 0.0]) for along in
            (number * pitch for number in range(count))]


def spread_pieces(found, items, rows, plan, inventory, tied):
    """Each relation laying several pieces at one spot given `pieces`, one a piece, each its own spot: on a wall along
    it (wall_pieces), on the floor or under the roof where the concept shows them (floor_pieces). The record laid every
    piece of such a relation at its one spot (2026-11-04 audit: 100 wall pieces and 12 floor pieces in each other)."""
    for entry in found:
        if "pieces" in entry or entry.get("beside"):
            continue
        row = rows[entry["row"]]
        count = pieces_at(entry["item"], row, plan, tied)
        if count <= 1:
            continue
        if entry["how"] == "wall":
            entry["pieces"] = wall_pieces(entry, items[entry["item"]], row, count, walls_of(plan))
        elif entry["how"] in ("floor", "ceiling") and entry.get("spot") and entry["item"] == plan_checks.WALLS_ITEM:
            entry["pieces"] = [{**{key: value for key, value in entry.items() if key not in ("item", "row", "spot")},
                                "spot": [round(float(value), 3) for value in spot]}
                               for spot in floor_pieces(entry, row, count, plan, inventory)]


def wall_height(entry, plan):
    """Metres over the floor a wall relation's object stands at: its mount `height`, else its plan item's base."""
    return float(entry.get("height", ((plan.get("shapes") or {}).get(entry["item"]) or {}).get("base") or 0.0))


def parted_on_wall(found, rows, plan):
    """Wall relations of one row's items at one spot on one wall at one height (within ONE_SPOT: the scene record would
    lay them in one another) each given its own place: packed along the wall their built length and PIECE_GAP apart
    where it holds them so (packed), else stood one over another up it round their height, their tall and PIECE_GAP
    apart, inside the room's height. 2026-11-06: garage's pipes 3 to 5, three 10 m pipes the plan's fixes moved to one
    corner of its 11.9 m wall, stood at one spot."""
    groups = {}
    for entry in found:
        if entry.get("how") == "wall" and "pieces" not in entry:
            key = (entry["row"], wall_key(entry["wall"]), entry["side"], round(wall_height(entry, plan), 3))
            groups.setdefault(key, []).append(entry)
    for (row_id, _, _, height), entries in groups.items():
        spots = []  # [[entry]] of each spot, the first entry's spot
        for entry in entries:
            near = next((laid for laid in spots if math.dist(laid[0]["spot"], entry["spot"]) < ONE_SPOT), None)
            near.append(entry) if near else spots.append([entry])
        for together in spots:
            if len(together) > 1:
                part_at_spot(together, rows[row_id], plan, height)


def part_at_spot(entries, row, plan, height):
    """Wall relations of one row at one spot given each its own: packed along its wall, else stood up it."""
    wall, long = entries[0]["wall"], max(built_long(row), PIECE_GAP)
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    length = wall_length(wall)
    run = (end - start) / max(length, 1e-9)
    if run_needed(row, len(entries)) <= length:
        alongs = [float((numpy.asarray(entry["spot"], float) - start) @ run) for entry in entries]
        for entry, along in zip(entries, packed(alongs, length, long)):
            entry["spot"] = [round(float(value), 3) for value in start + run * along]
            entry["why"] += "; packed along its wall with its row's others at its spot"
        return
    tall = float(row["size"][2]) if isinstance(row.get("size"), list) and len(row["size"]) == 3 else 0.0
    pitch, room = tall + PIECE_GAP, room_height(plan) or design_shell.STOREY
    heights = [height + (number - (len(entries) - 1) / 2) * pitch for number in range(len(entries))]
    lift = max(-heights[0], min(0.0, room - tall - heights[-1]))
    for entry, stood in zip(entries, heights):
        entry["height"] = round(stood + lift, 3)
        entry["why"] += "; stood over its row's others at its spot on its wall, too long to pack along it"


def wall_box(wall, side, spot, long, deep, low, high):
    """The box a wall thing is built in as the assembly lays it (assembly/fitting.on_wall), in plan or place metres:
    (middle, run, out, half long, half deep, low, high) on the face of `wall` [from, to] its `side` (+1 the line's
    left) and `thick` give, its spot along it kept inside the face's ends (`long` shrunk to the face where longer),
    `deep` out from the face into the room, from `low` to `high` over the floor (its scale with it)."""
    start, end = (numpy.asarray(point, float) for point in wall[:2])
    length = float(numpy.linalg.norm(end - start))
    run = (end - start) / max(length, 1e-9)
    out = numpy.array([-run[1], run[0]]) * side
    scale = min(1.0, length / max(long, 1e-9))
    half = long * scale / 2
    along = min(max(float((numpy.asarray(spot, float) - start) @ run), half), length - half)
    face = start + out * float(wall[2] if len(wall) > 2 else 0.0) / 2
    middle = face + run * along + out * deep * scale / 2
    return middle, run, out, half, deep * scale / 2, low, low + (high - low) * scale


def wall_reach(box, way):
    """Half a wall box's (wall_box) reach along a ground way."""
    return abs(float(box[1] @ way)) * box[3] + abs(float(box[2] @ way)) * box[4]


def boxes_meet(first, second):
    """Metres two wall boxes (wall_box) stand inside each other: the least of their overlap along each box's two ground
    ways and in height (negative where apart)."""
    ground = min(wall_reach(first, way) + wall_reach(second, way) - abs(float((first[0] - second[0]) @ way))
                 for way in (first[1], first[2], second[1], second[2]))
    return min(ground, min(first[6], second[6]) - max(first[5], second[5]))


def relation_box(entry, row, plan, height=None):
    """The wall box (wall_box) of a wall relation or one of its pieces at its `height` (its own by default)."""
    tall = float(row["size"][2]) if isinstance(row.get("size"), list) and len(row["size"]) == 3 else 0.0
    height = wall_height(entry, plan) if height is None else height
    return wall_box((entry["wall"]["from"], entry["wall"]["to"], float(entry["wall"].get("thick") or 0.0)),
                    entry["side"], entry["spot"], built_long(row), built_deep(row), height, height + tall)


def wall_top(wall, plan):
    """Metres the plan wall nearest a wall relation's wall's middle rises (its `tall`), else the room's height."""
    middle = (numpy.asarray(wall["from"], float) + numpy.asarray(wall["to"], float)) / 2
    drawn = [found for found in plan.get("walls") or [] if "from" in found and "to" in found]
    nearest = min(drawn, key=lambda found: off_line(middle, found)[0]) if drawn else {}
    return float(nearest.get("tall") or room_height(plan) or design_shell.STOREY)


def wall_band(row, height, tall, wall, plan):
    """(lowest, highest) metres over the floor a wall thing of the row standing at `height` may be stood at, its top
    under its wall's (wall_top): one on the floor stays on it, one its words say high or above or a light no lower
    than HIGH_LEAST or where it stands, the lower (mount_height's band), any other off the floor; one taller than its
    wall on the floor (2026-11-07: the stairwell's 12 m conduits stood 12 and 24 m up its 11.8 m walls)."""
    if height <= 0.0:
        return 0.0, 0.0
    high = where_words(row) & HIGH_WORDS or kind_words(row) & LIGHT_WORDS
    top = max(wall_top(wall, plan) - tall, 0.0)  # one taller than its wall stands on the floor
    return min(min(height, HIGH_LEAST) if high else PIECE_GAP, top), top


def meets_laid(context, row, plan, height, laid):
    """Whether a wall thing (relation_box of `context` at `height`) meets any box in `laid` by more than WALL_TOUCH."""
    box = relation_box(context, row, plan, height)
    return any(boxes_meet(box, other) > WALL_TOUCH for other in laid)


def slid_clear(context, row, plan, height, laid):
    """The plan spot on its wall's line nearest its own where a wall thing meets none of `laid` (meets_laid): just
    past either end of one of them along its wall, kept inside the wall's ends; None where there is none."""
    wall = context["wall"]
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    length = wall_length(wall)
    run = (end - start) / max(length, 1e-9)
    box = relation_box(context, row, plan, height)
    half, along = box[3], float((box[0] - start) @ run)
    tries = sorted({min(max(float((other[0] - start) @ run) + way * (wall_reach(other, run) + half + PIECE_GAP), half),
                        length - half) for other in laid for way in (1, -1)}, key=lambda spot: abs(spot - along))
    return next(([round(float(value), 3) for value in start + run * spot] for spot in tries if not meets_laid(
        {**context, "spot": list(start + run * spot)}, row, plan, height, laid)), None)


def stood_clear(context, row, plan, height, laid):
    """The height nearest its own, its tall and PIECE_GAP a step up or down, inside its band (wall_band: its row's,
    under its wall's top), where a wall
    thing meets none of `laid` (meets_laid); None where there is none."""
    tall = float(row["size"][2]) if isinstance(row.get("size"), list) and len(row["size"]) == 3 else 0.0
    low, high = wall_band(row, height, tall, context["wall"], plan)
    steps = range(1, int(max(high - low, 0.0) / (tall + PIECE_GAP)) + 2)
    tries = [round(height + way * step * (tall + PIECE_GAP), 3) for step in steps for way in (1, -1)]
    return next((stood for stood in tries if low - 1e-9 <= stood <= high + 1e-9 and
                 not meets_laid(context, row, plan, stood, laid)), None)


def onto_wall(context, wall, plan):
    """A wall thing's relation (`context`: its wall, side, spot) moved onto another plan `wall`: its spot the point of
    that wall nearest where it stood, on the side of it inside the plan's outline, else (both inside: an inner wall)
    the side its old face looked into the room from."""
    old = context["wall"]
    start, end = numpy.asarray(old["from"], float), numpy.asarray(old["to"], float)
    run = (end - start) / max(wall_length(old), 1e-9)
    room = numpy.asarray(context["spot"], float) + numpy.array([-run[1], run[0]]) * context["side"] * (
        float(old.get("thick") or 0.0) / 2 + PIECE_GAP)  # a point in the room before its old face
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    share = float(numpy.clip((room - start) @ (end - start) / max(float((end - start) @ (end - start)), 1e-9), 0, 1))
    run = (end - start) / max(wall_length(wall), 1e-9)
    sides = [side for side in (1, -1) if inside_outline((start + end) / 2 + numpy.array([-run[1], run[0]]) * side *
                                                        (float(wall.get("thick") or 0.0) / 2 + PIECE_GAP), plan)]
    return {**context, "wall": {key: wall[key] for key in ("from", "to", "thick")},
            "side": sides[0] if len(sides) == 1 else off_line(room, wall)[1],
            "spot": [round(float(value), 3) for value in start + (end - start) * share]}


def inside_outline(spot, plan):
    """Whether a plan spot lies inside the plan's outline (True with no outline)."""
    outline = plan.get("outline") or []
    return len(outline) < 3 or bool(plan_checks.inside(numpy.asarray([spot], float), outline)[0])


# Metres between the spots along a run of walls a wall thing with no room on its own wall is tried at (walled_clear).
SCAN = 0.1


def run_chords(plan, long):
    """[chord] of each stretch `long` metres long a straight thing lies flat along on a straight run of the plan's
    walls over more than one wall (a round wall's facets, walls drawn end to end in line: straight_runs of chain_of),
    every SCAN metres along it: the chord from its one end on the walls to its other, as wall_pieces lays a piece."""
    walls, found, seen = walls_of(plan), [], set()
    for wall in walls:
        chain = chain_of(wall, walls, ROUND_BEND)
        for low, high in straight_runs(chain) if len(chain) > 2 else []:
            if chain_point(chain, low + 1e-6)[1] == chain_point(chain, high - 1e-6)[1]:
                continue  # one wall: tried as itself
            for step in range(int(max(high - low - long, -1.0) / SCAN) + 1):
                ends = [chain_point(chain, low + step * SCAN + reach)[0] for reach in (0.0, long)]
                chord = {"from": [round(float(value), 4) for value in ends[0]],
                         "to": [round(float(value), 4) for value in ends[1]], "thick": wall.get("thick")}
                if wall_key(chord) not in seen and wall_key(chord)[::-1] not in seen:
                    seen.add(wall_key(chord))
                    found.append(chord)
    return found


def walled_clear(context, row, plan, height, laid):
    """(relation fields, height) of a wall thing that finds no room on its own wall (slid_clear, stood_clear) moved
    to the nearest other place on the walls with room for it: another plan wall long enough for it, where it stands
    there, else slid along it, else stood up or down it, or a stretch of a run of walls (run_chords: round a round
    wall's facets) where it stands or is stood; None where the walls have no room. 2026-11-07: habitat's 18 pipes each
    took the wall nearest its plan spot, three on one 3.9 m wall, without counting what was already on it."""
    own, spot, long = wall_key(context["wall"]), numpy.asarray(context["spot"], float), built_long(row)
    tries = [(off_line(spot, wall)[0], True, wall) for wall in walls_of(plan)
             if wall_key(wall) != own and wall_length(wall) >= long] + [
        (float(numpy.linalg.norm(spot - (numpy.asarray(chord["from"]) + numpy.asarray(chord["to"])) / 2)), False, chord)
        for chord in run_chords(plan, long)]
    for _, drawn, wall in sorted(tries, key=lambda tried: tried[0]):
        moved = onto_wall(context, wall, plan)
        if not drawn:  # a stretch as long as the thing: it stands in its middle
            moved["spot"] = [round((float(first) + float(second)) / 2, 3)
                             for first, second in zip(wall["from"], wall["to"])]
        if not meets_laid(moved, row, plan, height, laid):
            return moved, height
        if drawn and (slid := slid_clear(moved, row, plan, height, laid)) is not None:
            return {**moved, "spot": slid}, height
        if (stood := stood_clear(moved, row, plan, height, laid)) is not None:
            return moved, stood
    return None


def passage(row):
    """Whether a row is a passage (PASSAGE_WORDS: a tunnel, a tube) meeting its place's wall from outside."""
    return bool(kind_words(row) & PASSAGE_WORDS)


def apart_on_walls(found, rows, plan):
    """Each wall thing laid as an object (a wall relation of a row the plan's shell does not lay, `structure` or arched
    (design_shell.arched: a tube's ribs), or each of its pieces) whose built box (relation_box) meets one laid before it on the walls by more than WALL_TOUCH, of
    any row, round a corner too: slid along its wall to the nearest spot where it meets none (slid_clear), else stood
    the nearest height over or under it inside its band (stood_clear: a thing too long for the wall's free stretches);
    one with neither is left as it is (the scene record's laid-as-designed names it). 2026-11-06: hangar's eight 32 m
    pipes, four on its 64 m left wall and two on its front wall, at 10 m in one another. A passage (`passage`) is laid
    first and never moved: its stretch of wall is its own (2026-11-07: workshop's monitors packed into its glass
    tunnel's chord). One that finds no room anywhere (walled_clear) while it meets a smaller thing is laid before the
    others in a second go, the smaller parting round it (`laid_apart`; 2026-11-07: the stairwell's 12 m tall conduit
    pipes, laid after its lamps and boxes, found no 3 m of wall free of them)."""
    walled = [entry for entry in found if entry.get("how") == "wall"]
    first, kept = [], [copy.deepcopy(entry) for entry in walled]
    while True:
        stuck = [entry for entry in laid_apart(found, rows, plan, first) if all(entry is not was for was in first)]
        if not stuck:
            return
        for entry, was in zip(walled, kept):
            entry.clear()
            entry.update(copy.deepcopy(was))
        first += stuck


def hung_boxes(found, rows, plan):
    """The box (wall_box's form) each thing hung from the roof (a `ceiling` relation `to roof`, not a structure row)
    is laid in, as the scene record lays it: each of its pieces at its middle, its model along its way
    (piece_middles, model_axes), its top ROOF_CLEAR under the roof's underside over it (writer.roof_under).
    2026-11-07: storage's second wall pipe, stood up clear of the first, went into the ceiling light hung by its wall."""
    from score.stages.scene_record import writer  # here: the writer imports this module
    items, structure, boxes = plan_items(plan), set(plan.get("structure") or []), []
    for entry in found:
        row = rows.get(entry["row"])
        if entry.get("how") != "ceiling" or not entry.get("to roof") or entry["row"] in structure or row is None \
                or entry["item"] not in items or not (isinstance(row.get("size"), list) and len(row["size"]) == 3):
            continue
        size = [float(value) for value in row["size"]]
        for spot, way in piece_middles(items[entry["item"]], row, plan):
            run, out = model_axes(way, row)
            top = writer.roof_under(plan, spot) - writer.ROOF_CLEAR
            boxes.append((numpy.asarray(spot, float), run, out, size[0] / 2, size[1] / 2, top - size[2], top))
    return boxes


def laid_apart(found, rows, plan, first=()):
    """apart_on_walls' one go, the relations in `first` laid before the rest (each list in found's order), clear of
    the things hung from the roof (hung_boxes, never moved: laid as longer than any); the relations left meeting a
    smaller wall thing, of a row longer than it, with nowhere to go."""
    structure, stuck = set(plan.get("structure") or []), []
    laid = [(box, math.inf) for box in hung_boxes(found, rows, plan)]  # laid: (box, row long)
    ahead = {id(entry) for entry in first}
    order = [entry for entry in found if id(entry) in ahead] + [entry for entry in found if id(entry) not in ahead]
    for entry in sorted(order, key=lambda entry: not passage(rows[entry["row"]])):
        row = rows[entry["row"]]
        if entry.get("how") != "wall" or entry["row"] in structure or design_shell.arched(row):
            continue
        for piece in entry.get("pieces") or [entry]:
            if piece.get("how") != "wall":
                continue
            height = float(piece["height"]) if "height" in piece else wall_height(entry, plan)
            context = {**entry, **piece, "item": entry["item"]}
            tall = float(row["size"][2]) if isinstance(row.get("size"), list) and len(row["size"]) == 3 else 0.0
            if height > (top := wall_band(row, height, tall, context["wall"], plan)[1]) + 1e-9:
                piece["height"] = height = round(top, 3)
                piece["why"] += "; brought down to stand under its wall's top"
            boxes = [box for box, _ in laid]
            if meets_laid(context, row, plan, height, boxes) and not passage(row):
                if (spot := slid_clear(context, row, plan, height, boxes)) is not None:
                    piece["spot"] = context["spot"] = spot
                    piece["why"] += "; slid along its wall clear of the wall things laid before it"
                elif (stood := stood_clear(context, row, plan, height, boxes)) is not None:
                    piece["height"] = height = stood
                    piece["why"] += "; stood clear of the wall things laid before it at its spot"
                elif (moved := walled_clear(context, row, plan, height, boxes)) is not None:
                    (context, height), was = moved, context["wall"]
                    piece.update({key: context[key] for key in ("wall", "side", "spot")})
                    piece.pop("short", None)
                    if height != wall_height(entry, plan) or "height" in piece:
                        piece["height"] = height
                    piece["why"] += f"; moved to the nearest wall with room for it, its own ({was['from']} to " \
                                    f"{was['to']}) full"
                elif all(entry is not was for was in stuck) and any(
                        long < built_long(row) and boxes_meet(box, relation_box(context, row, plan, height)) > WALL_TOUCH
                        for box, long in laid):
                    stuck.append(entry)
            laid.append((relation_box(context, row, plan, height), built_long(row)))
    return stuck


def parted_on_floor(found, items, plan, inventory):
    """Floor relations of one row's items at one spot at one height (their middles within ONE_SPOT, one shape base:
    the scene record would lay them in one another) each after the first given its own `spot`: its item's box moved
    the shortest way clear of its row's others there (floor_room), inside the outline and onto no other floor thing;
    one with no such room keeps its spot. 2026-11-06: the engine room's railings 3 and 4, drawn on one box."""
    shapes, groups = plan.get("shapes") or {}, {}
    for entry in found:
        if entry.get("how") == "floor" and "spot" not in entry and "pieces" not in entry and entry["item"] in items:
            base = float((shapes.get(entry["item"]) or {}).get("base") or 0.0)
            groups.setdefault((entry["row"], round(base, 3)), []).append(entry)
    floor = [item[1:5] for item, *_ in plan_checks.blocking(plan, inventory)]
    for entries in groups.values():
        settled = []  # the boxes [x, y, w, d] of the group's items laid so far
        for entry in entries:
            box = [float(value) for value in items[entry["item"]][1:5]]
            still = [other for other in settled if math.dist(middle([None, *other]), middle([None, *box])) < ONE_SPOT]
            step = floor_room(box, still, plan, [other for other in floor if other != box] + settled) if still else None
            if step is not None:
                box = [box[0] + step[0], box[1] + step[1], box[2], box[3]]
                entry["spot"] = [round(float(value), 3) for value in middle([None, *box])]
                entry["why"] += "; parted from its row's other at its spot, where the floor has room"
            settled.append(box)


def floor_room(box, still, plan, others):
    """The shortest step [dx, dy] that lays `box` ([x, y, w, d]) beside one of the `still` boxes, PIECE_GAP clear,
    inside the plan's outline and overlapping none of `others`; None when there is none."""
    outline = plan_checks.outline_of(plan)
    steps = [step for other in still for step in (
        [other[0] + other[2] - box[0] + PIECE_GAP, 0.0], [other[0] - box[0] - box[2] - PIECE_GAP, 0.0],
        [0.0, other[1] + other[3] - box[1] + PIECE_GAP], [0.0, other[1] - box[1] - box[3] - PIECE_GAP])]
    for step in sorted(steps, key=lambda step: abs(step[0]) + abs(step[1])):
        x, y, wide, deep = box[0] + step[0], box[1] + step[1], box[2], box[3]
        corners = numpy.array([[x, y], [x + wide, y], [x + wide, y + deep], [x, y + deep]])
        if plan_checks.inside(corners, outline).all() and not any(
                x < rest[0] + rest[2] and rest[0] < x + wide and y < rest[1] + rest[3] and rest[1] < y + deep
                for rest in others):
            return step
    return None


def beside_holder(item, row, rows, laid, items):
    """(holder row, its plan item) a seat stands before: a seat row (SEAT_WORDS) whose where words say it stands at,
    by, before or around (BESIDE_WORDS) a row its other words name (a word of what that row is, plural or not) laid
    on the plan, the nearest such item; None."""
    words = where_words(row)
    if not kind_words(row) & SEAT_WORDS or not words & BESIDE_WORDS:
        return None
    stems = {word.rstrip("s") for word in words - BESIDE_WORDS - PLACE_WORDS}
    found = [(other, name) for other in rows.values() if other["id"] in laid and other is not row
             and not kind_words(other) & (SEAT_WORDS | PERSON_WORDS)
             and {word.rstrip("s") for word in kind_words(other)} & stems
             for name in laid[other["id"]] if name != item[0]]
    return min(found, key=lambda pair: float(numpy.linalg.norm(middle(items[pair[1]]) - middle(item)))) \
        if found else None


def holder_sides(holder_item, holder_row):
    """{plan side: (its out way, metres from the holder's middle to it, metres along it)} of a holder laid at its
    built size, its long side along its facing's way (a facing N lays its x east, as the scene record turns it)."""
    front = numpy.asarray(FACES.get(holder_item[5]) or FACES["N"], float)
    way = numpy.array([-front[1], front[0]])
    long = built_long(holder_row) or max(float(holder_item[3]), float(holder_item[4]))
    size = holder_row.get("size")
    short = min(float(size[0]), float(size[1])) if isinstance(size, list) and len(size) == 3 else \
        min(float(holder_item[3]), float(holder_item[4]))
    found = {}
    for side, out in FACES.items():
        lengthwise = abs(float(numpy.asarray(out) @ way)) > 0.5  # an end of its long side
        found[side] = (numpy.asarray(out, float), long / 2 if lengthwise else short / 2, short if lengthwise else long)
    return found


def rails_along(found, plan):
    """The railings of one row along the plan's stairs (relations marked `stairs`, each its count) shared out over
    every stair side as one row (stair_sides), never each item's from the first side again (stairwell's 12 railings,
    one an item, stood at one spot, 2026-11-04 audit)."""
    by_row = {}
    for entry in found:
        if entry.get("stairs"):
            by_row.setdefault(entry["row"], []).append(entry)
    for entries in by_row.values():
        sides = stair_sides(plan, sum(int(entry["stairs"]) for entry in entries))
        for entry in entries:
            entry["pieces"], sides = sides[:int(entry["stairs"])], sides[int(entry["stairs"]):]
            entry.pop("stairs")


def seats_beside(found, items, rows, plan, tied):
    """Each seat relation before its holder (`beside`) given `pieces`: the seats at one holder item on the side the
    plan draws each on, as many as its built side holds their built width and PIECE_GAP apart, the rest on its
    opposite side, then its ends; each SEAT_GAP clear of the holder's built side, facing it."""
    groups = {}
    for entry in found:
        if entry.get("beside"):
            groups.setdefault(entry["beside"], []).append(entry)
    for holder_name, entries in groups.items():
        holder_item = items[holder_name]
        sides, centre = holder_sides(holder_item, rows[entries[0]["holder row"]]), middle(holder_item)
        seats = [(entry, number) for entry in entries
                 for number in range(pieces_at(entry["item"], rows[entry["row"]], plan, tied))]
        seat = rows[entries[0]["row"]]
        pitch = (built_long(seat) or 0.6) + PIECE_GAP
        depth = min(float(seat["size"][0]), float(seat["size"][1])) if isinstance(seat.get("size"), list) and \
            len(seat["size"]) == 3 else 0.6
        taken = {side: [] for side in sides}
        for entry, number in seats:
            drawn = snapped(middle(items[entry["item"]]) - centre)
            order = [drawn, OPPOSITE[drawn], *[side for side in sides if side not in (drawn, OPPOSITE[drawn])]]
            side = next((side for side in order if (len(taken[side]) + 1) * pitch - PIECE_GAP <= sides[side][2]),
                        drawn)
            taken[side].append((entry, number))
        for side, placed in taken.items():
            out, reach, _ = sides[side]
            along = numpy.array([-out[1], out[0]])
            for slot, (entry, number) in enumerate(placed):
                spot = centre + out * (reach + SEAT_GAP + depth / 2) + along * (slot - (len(placed) - 1) / 2) * pitch
                entry.setdefault("pieces", {})[number] = {
                    "how": "floor", "spot": [round(float(value), 3) for value in spot],
                    "way": [round(float(out[1]), 6) + 0.0, round(float(-out[0]), 6) + 0.0],
                    "why": f"before {entry['holder row']}'s {side} side, {SEAT_GAP:g} m clear, facing it"}
        for entry in entries:
            entry["pieces"] = [entry["pieces"][number] for number in sorted(entry["pieces"])]


def shape_of(name, plan):
    return (plan.get("shapes") or {}).get(name) or {}


def tall_of(name, row, plan):
    """An item's built height: its row's read tall (what its model is made at), else its shape's tall, else 0."""
    size = row.get("size")
    return float(size[2]) if isinstance(size, list) and len(size) == 3 else \
        float(shape_of(name, plan).get("tall") or 0.0)


def named_holders(row, rows, tied):
    """The rows laid on the plan as items of their own whose kind words a row's where words name (engines for
    "around engines"), plural or not, never the row itself or a seat's sitter."""
    stems = {word.rstrip("s") for word in where_words(row) - AROUND_WORDS - BESIDE_WORDS - PLACE_WORDS}
    return [other for other in rows.values() if other is not row and other["id"] in tied
            and any(name != plan_checks.WALLS_ITEM for name in tied[other["id"]])
            and not kind_words(other) & PERSON_WORDS and {word.rstrip("s") for word in kind_words(other)} & stems]


def around_holders(found, items, rows, plan, tied):
    """The floor relations of a row whose where words say its things stand round a holder row (AROUND_WORDS,
    named_holders) laid round that row's items' built outlines (holder_sides), one a side: each piece, in turn, on
    the side not yet taken where it stands least past the outline, in other things standing on the floor or in its
    row's pieces laid already (side_crowding: the engine room's railing on its engine's end stood in the next
    engine), else of the holder with fewest, else the nearest; past every side taken, more a side spread along it
    their built length and PIECE_GAP apart; each PIECE_GAP clear of the holder's side, along it, at the holder's foot
    (`height`). 2026-11-06: the engine room's eight railings "around engines" stood four on one box, piled 1 to 4 m
    up by the plan's fixes."""
    groups = {}
    for entry in found:
        row = rows.get(entry["row"])
        if entry.get("how") == "floor" and "pieces" not in entry and not entry.get("beside") and row \
                and where_words(row) & AROUND_WORDS and not kind_words(row) & SEAT_WORDS \
                and entry["item"] in items and entry["item"] != plan_checks.WALLS_ITEM:
            groups.setdefault(entry["row"], []).append(entry)
    for row_id, entries in groups.items():
        row = rows[row_id]
        holding = [(other, name) for other in named_holders(row, rows, tied) for name in tied[other["id"]]
                   if name != plan_checks.WALLS_ITEM and name in items]
        if not holding:
            continue
        size = row.get("size")
        depth = min(float(size[0]), float(size[1])) if isinstance(size, list) and len(size) == 3 else 0.0
        long, people = built_long(row), plan_checks.people({"rows": list(rows.values())})
        laid_boxes, chosen = [], {}  # [x, y, w, d] of the pieces laid so far; {(holder, side): [entries]}
        for entry in entries:  # each on the free side standing least in things, then of the holder with fewest, nearest
            spot = middle(items[entry["item"]])
            free = [(other, name, side) for other, name in holding for side in FACES if (name, side) not in chosen] or \
                [(other, name, side) for other, name in holding for side in FACES]
            other, name, side = min(free, key=lambda slot: (
                round(side_crowding(holder_sides(items[slot[1]], slot[0])[slot[2]], middle(items[slot[1]]), depth,
                                    long, slot[1], row_id, items, rows, plan, people, laid_boxes), 3),
                sum(len(taken) for (held, _), taken in chosen.items() if held == slot[1]),
                round(float(numpy.linalg.norm(middle(items[slot[1]]) - spot)), 3)))
            chosen.setdefault((name, side), []).append((entry, other))
            laid_boxes.append(piece_box(holder_sides(items[name], other)[side], middle(items[name]), depth, long))
        for (name, side), laid in chosen.items():
            centre, base = middle(items[name]), float(shape_of(name, plan).get("base") or 0.0)
            out, reach, _ = holder_sides(items[name], laid[0][1])[side]
            along = numpy.array([-out[1], out[0]])
            for slot, (entry, other) in enumerate(laid):
                spot = centre + out * (reach + PIECE_GAP + depth / 2) + along * (slot - (len(laid) - 1) / 2) * \
                    (long + PIECE_GAP)
                entry.update({"spot": [round(float(value), 3) for value in spot],
                              "way": [round(float(out[1]), 6) + 0.0, round(float(-out[0]), 6) + 0.0],
                              "height": round(base, 3)})
                entry["why"] = (f"on the place's floor round {other['id']}'s {name} on its {side} side, "
                                f"{PIECE_GAP:g} m clear: its words say it stands {row.get('where')!r}")


def piece_box(side, centre, depth, long):
    """The box [x, y, w, d] of a piece `long` by `depth` laid along a holder's `side` (holder_sides' (out, reach,
    length)), PIECE_GAP clear of it."""
    out, reach, _ = side
    spot = centre + out * (reach + PIECE_GAP + depth / 2)
    half = numpy.abs(out) * depth / 2 + numpy.abs([out[1], out[0]]) * long / 2
    return [float(spot[0] - half[0]), float(spot[1] - half[1]), float(2 * half[0]), float(2 * half[1])]


def side_crowding(side, centre, depth, long, holder, row_id, items, rows, plan, people, laid):
    """Square metres a piece laid along a holder's `side` (piece_box) would stand past the plan's outline, in other
    things standing on the floor (on_floor, its base within STAND_REACH; not the holder's own row's, no person) or in
    the boxes of its row's pieces `laid` already."""
    box = piece_box(side, centre, depth, long)
    grid = numpy.array([[box[0] + box[2] * along, box[1] + box[3] * across]
                        for along in numpy.linspace(0, 1, 5) for across in numpy.linspace(0, 1, 5)])
    past = float((~plan_checks.inside(grid, plan_checks.outline_of(plan))).mean()) * box[2] * box[3]
    tied = plan.get("rows") or {}
    others = [[float(value) for value in other[1:5]] for name, other in items.items()
              if name not in (holder, plan_checks.WALLS_ITEM) and float(shape_of(name, plan).get("base") or 0.0)
              <= STAND_REACH for row_id_there in (tied.get(name) or [])[:1]
              if row_id_there in rows and on_floor(rows[row_id_there], rows) and row_id_there not in {row_id} | people]
    return past + sum(max(0.0, min(box[0] + box[2], other[0] + other[2]) - max(box[0], other[0])) *
                      max(0.0, min(box[1] + box[3], other[1] + other[3]) - max(box[1], other[1]))
                      for other in others + laid)


def on_floor(row, rows):
    """Whether a row stands on the floor, no shell part itself (PARTS): anchored on the floor or the ground, or on a
    row that is a floor (holder_kind); never a door in its wall, a box on its shelf, a pipe on a wall."""
    anchor = row.get("anchor") or "floor"
    holder = rows.get(anchor[3:]) if anchor.startswith("on:") else None
    return row.get("part") not in PARTS and (anchor in plan_checks.FLOOR_ANCHORS or
                                             (holder is not None and holder_kind(holder) == "floor"))


def box_reach(point, box):
    """Metres from a plan point to a box [x, y, w, d] (0 inside it)."""
    return math.hypot(max(box[0] - point[0], 0.0, point[0] - box[0] - box[2]),
                      max(box[1] - point[1], 0.0, point[1] - box[1] - box[3]))


def hung_between(found, items, rows, plan):
    """Each floor relation of a row whose where words say it hangs over the floor (HUNG_WORDS) laid by its plan over
    more than half its height up made `hung` between the two things standing on the floor that reach its top
    nearest its long side's two ends (`holders`, their `holder rows`), what holds it there; one with no two such
    things stays on the floor, for laid-as-designed to fail. 2026-11-06: the square's lantern strings 6 m over its
    plaza with nothing under them. People (plan_checks.people) hold nothing."""
    people = plan_checks.people({"rows": list(rows.values())})
    hung = [entry for entry in found if entry.get("how") == "floor" and "pieces" not in entry
            and entry["item"] in items and entry["item"] != plan_checks.WALLS_ITEM
            and where_words(rows.get(entry["row"]) or {}) & HUNG_WORDS]
    for entry in hung:
        item, row = items[entry["item"]], rows[entry["row"]]
        base, tall = float(shape_of(item[0], plan).get("base") or 0.0), tall_of(item[0], row, plan)
        if base <= max(STAND_REACH, tall / 2):
            continue
        standing = [(name, other) for name, other in items.items() if name not in (item[0], plan_checks.WALLS_ITEM)
                    for row_id in (plan.get("rows") or {}).get(name) or [] if row_id in rows and row_id != row["id"]
                    if row_id not in people
                    if float(shape_of(name, plan).get("base") or 0.0) <= STAND_REACH
                    and tall_of(name, rows[row_id], plan) >= base + tall - STAND_REACH]
        x, y, wide, deep = (float(value) for value in item[1:5])
        ends = [(x, y + deep / 2), (x + wide, y + deep / 2)] if wide >= deep else \
            [(x + wide / 2, y), (x + wide / 2, y + deep)]
        held = []
        for end in ends:
            left = [(name, other) for name, other in standing if name not in held]
            if left:
                held.append(min(left, key=lambda pair: box_reach(end, [float(value) for value in pair[1][1:5]]))[0])
        if len(held) == 2:
            entry.update({"how": "hung", "holders": held,
                          "holder rows": [(plan.get("rows") or {})[name][0] for name in held],
                          "why": f"hung {base:g} m over the place's floor between {held[0]} and {held[1]}: its words "
                                 f"say it hangs {row.get('where')!r}"})


def stood_under(found, items, rows, plan):
    """Each floor relation of an item its plan stands more than half its height (and STAND_REACH) up on nothing, no
    level, flight or other thing's top under its box within STAND_REACH (its own row's only where that row piles),
    given the `height` of the highest stand under it below its base: the floor's, a level's whose outline holds its
    box, a flight's, a thing's top. 2026-11-06: the square's stage screen drawn at its deck's 3.3 m just behind it;
    the street's barriers and the engine room's railings, piled on their own row by the plan's fixes, 1 to 4 m up.
    People (plan_checks.people) hold nothing up: the square's screens stood on its 1.8 m crowd's box."""
    people = plan_checks.people({"rows": list(rows.values())})
    for entry in found:
        if entry.get("how") != "floor" or "pieces" in entry or "height" in entry or entry["item"] not in items \
                or entry["item"] == plan_checks.WALLS_ITEM or entry["row"] not in rows:
            continue
        item, row = items[entry["item"]], rows[entry["row"]]
        base, tall = float(shape_of(item[0], plan).get("base") or 0.0), tall_of(item[0], row, plan)
        if base <= max(STAND_REACH, tall / 2):
            continue
        box = [float(value) for value in item[1:5]]
        spots = [[box[0] + box[2] * along, box[1] + box[3] * across] for along in (0.0, 0.5, 1.0)
                 for across in (0.0, 0.5, 1.0)]
        stands = [0.0] + [float(level["height"]) for level in plan.get("levels") or []
                          if len(level.get("points") or []) >= 3
                          and any(design_shell.inside(spot, level["points"]) for spot in spots)] + [
            min(max(base, float(stair["from"])), float(stair["to"])) for stair in plan.get("stairs") or []
            if len(stair.get("points") or []) >= 3 and "from" in stair and "to" in stair
            and any(design_shell.inside(spot, stair["points"]) for spot in spots)] + [
            float(shape_of(name, plan).get("base") or 0.0) + tall_of(name, rows.get(row_id) or {}, plan)
            for name, other in items.items() if name not in (item[0], plan_checks.WALLS_ITEM)
            for row_id in ((plan.get("rows") or {}).get(name) or [])[:1]
            if (row_id != row["id"] or piles(row)) and row_id not in people
            and box[0] < other[1] + other[3] and other[1] < box[0] + box[2]
            and box[1] < other[2] + other[4] and other[2] < box[1] + box[3]]
        if any(abs(base - stand) <= STAND_REACH for stand in stands):
            continue
        entry["height"] = round(max(stand for stand in stands if stand < base), 3)
        entry["why"] += (f"; standing on what is under it, {entry['height']:g} m up: its plan's {base:g} m stands "
                         "on nothing")


def wall_held(row, rows):
    """Whether a reading row stands against a wall: anchored on one, or on a row that is one (holder_kind)."""
    anchor = str(row.get("anchor") or "")
    holder = rows.get(anchor[3:]) if anchor.startswith("on:") else None
    return anchor == "wall" or (holder is not None and holder_kind(holder) == "wall")


def built_rows(rows, plan, inventory):
    """The reading's rows, each held on a wall at the size it is made at (prepare's groups.made_size, the hand-in's),
    never its reading's own metres where they measured a whole run: what the holders part on the walls is what the
    scene record lays (2026-11-07: the stairwell's four 12 m conduit pipes, made 3 m pieces, stood at one spot on its
    7.4 m wall; the cockpit's red pipes, made 6.6 m pieces of a run read 9.8 m, were stood clear as 9.8 m)."""
    from score.stages.complete.prepare import groups
    by_id = {row["id"]: row for row in rows}
    laid, picture = groups.plan_sizes_of(plan, rows), inventory.get("picture")
    found = []
    for row in rows:
        box = row.get("box") or (plan_checks.gemini_box(row["region"], picture) if row.get("region") and picture
                                 else None)
        made = groups.made_size(row, rows, plan, laid, box) if wall_held(row, by_id) else None
        found.append({**row, "size": made} if made and made != row.get("size") else row)
    return found


def relations(plan, inventory, sha=None, kinds=None):
    """The place's relations (module docstring): one a plan item's row that stands on, against or in something;
    `kinds` the row-kind rules (score/stages/row_kinds.py's table by default)."""
    kinds = row_kinds.table() if kinds is None else kinds
    rows = {row["id"]: row for row in built_rows(inventory.get("rows", []), plan, inventory)}
    items, tied = items_of(plan)
    structure = set(plan.get("structure") or [])
    laid = {row_id: kept for row_id, names in tied.items() if row_id not in structure
            for kept in [[name for name in names if name != plan_checks.WALLS_ITEM]] if kept}
    found, unheld, taken, taken_stairs = [], [], set(), set()
    turn = plan_checks.viewed(plan, inventory)[2]  # the way the concept's viewer looks on the plan
    for name, item in items.items():
        for row_id in (plan.get("rows") or {}).get(name) or []:
            row = rows.get(row_id)
            if row is None or name not in tied.get(row_id, []):  # a walls row placed on an item of its own
                continue
            seated = beside_holder(item, row, rows, laid, items)
            if seated and pieces_at(seated[1], seated[0], plan, tied) == 1:  # one holder there, not a run of them
                found.append({"item": name, "row": row_id, "how": "floor", "beside": seated[1],
                              "holder row": seated[0]["id"], **rests_entry(row),
                              "why": f"before {seated[0]['id']}: its words say it stands {row.get('where')!r}"})
                continue
            if leaning_on_floor(row, plan):
                row = {**row, "anchor": "wall"}  # against the nearest wall, its foot on the floor
            if (row.get("anchor") or "floor") in plan_checks.FLOOR_ANCHORS:
                got = (at_edge(row, plan, inventory, turn) if item[0] == plan_checks.WALLS_ITEM else None) or (
                    {"how": "floor", **spot} if (spot := floor_spot(item, row, plan, inventory, taken_stairs)) else
                    None) or up_to_level(item, row, plan)
                if got:
                    found.append({"item": name, "row": row_id, **got, **rests_entry(row)})
                continue
            got, why = relation(item, row, rows, plan, inventory, laid, taken, turn, taken_stairs, kinds,
                                pieces_at(name, row, plan, tied), found)
            if got:
                found.append({"item": name, "row": row_id, **got, **rests_entry(row)})
            elif why:
                unheld.append({"item": name, "row": row_id, "why": why})
    room_walls(found, items, rows, plan, turn, inventory, tied)
    crowded = spread(found) + face_spread(found, items, rows, plan, inventory, kinds)
    spread_pieces(found, items, rows, plan, inventory, tied)
    parted_on_wall(found, rows, plan)
    apart_on_walls(found, rows, plan)
    parted_on_floor(found, items, plan, inventory)
    seats_beside(found, items, rows, plan, tied)
    rails_along(found, plan)
    around_holders(found, items, rows, plan, tied)
    hung_between(found, items, rows, plan)
    stood_under(found, items, rows, plan)
    for entry in found:
        entry.pop(LINE, None)
    for _, openings in wall_openings(found).values():
        for _, opening in openings:
            opening.pop("drawn", None)
    return {"place": plan.get("place") or inventory.get("place"), "plan": sha,
            "about": "What holds each plan item, derived from the scene inventory's anchors, the concept's boxes and "
                     "the kept plan (score/review/holders); the scene record lays each object by it.",
            "relations": found, "unheld": unheld, **({"crowded": crowded} if crowded else {}),
            **({"loose": loose} if (loose := loose_openings(plan)) else {})}


def loose_openings(plan):
    """The plan check that every opening of a place whose shell builds walls sits on one (design_shell.on_a_wall: its
    outline's and its inner walls): [{opening, at, why}] of each that sits on none, which no wall is cut for (the
    lab's doors stood in their entry passages' end walls, which the shell did not build, motion@lab round 35). An open
    place's opening is a doorway into a building its facade row stands for, no opening of a wall of its own (the
    street's stairwell door, its plan drawing no walls: an open ground has none, plan_writing)."""
    if "wall" not in shell_parts.parts(plan):
        return []
    return [{"opening": number + 1, "at": opening["at"], "why": "it sits on no wall the shell builds"}
            for number, opening in enumerate(design_shell.plan_openings(plan))
            if not design_shell.on_a_wall(plan, opening)]


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
