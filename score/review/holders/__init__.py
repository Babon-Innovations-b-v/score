"""What holds each plan item (issue #72; bible `architecture/layers`, assembly: the plan states the relations the
assembly lays by): derived free from the scene inventory's anchors, the concept's boxes and the kept plan, no model
call, and kept beside the plan in a file of its own, `{home}/design/relations/<place>.json`, which the scene record
reads (never in design/plans/: that file keys the close-ups and the surface library).

Each plan item of a row that stands on, against or in something gets one relation, in plan metres (x east, y south):

    top    on its holder item's top: the row's anchor `on:<row>`, and in the concept its box's foot stands over its
           holder's by more than TOP_SHARE of the holder's box (a monitor on its console, a lamp on its desk)
    within inside its holder item, where the plan lays its middle (plants in their greenhouse, a door in its frame);
           `hangs` where it hangs in it (hangs: a spacesuit in its locker)
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
           none left, one cut for it (`cut`) where its spot meets the nearest wall; each piece its own (`pieces`): an
           item's where the scene record lays it, the walls item's at its concept boxes' projections, else spread
           along the longest wall
    edge   past the plan's edge (`edge`, `spot` the edge's middle): a wall row the plan writer left on the walls item
           where the plan draws no wall (street's facades), on the side of the view its concept box stands; what is on
           it stands against its face toward the place
    wall   against a wall of the plan (`wall`, its from, to, thick, and `side` +1 or -1 of the line it stands on, `spot`
           its plan spot): a row anchored `wall`, or on a structure row that is a wall; an item the plan writer did not
           place (the walls item) stands where the concept's box projects onto the plan (plan_checks.projection), else
           at the longest wall's middle; an item outlining the whole room (outlines_room: its middle says nothing)
           on the wall its holder's id names as the viewer sees it (left_wall), else, the concept not placing it, the
           middle of the nearest wall no other such item holds; such items sharing a spot on one wall spread along it;
           a placed item stands on the room's side, drawn past the outline or not, but a passage (a tunnel, a tube)
           meets its wall from outside (past_outline)
    ramp   a ramp row on the floor where the plan draws a raised level (airlock's porch deck): up to the nearest such
           level's nearest edge (`edge`, its two plan points, and `height`), its long side run straight up to it
           (`way`), its high end on the edge's line and its middle at `spot` (up_to_level)
    floor / ceiling  on the place's own floor or under its roof, nothing to lay against; one the plan writer left on
           the walls item at its `spot` (a stair row at the plan's stair along its way up, else where its concept box
           projects), a thing on a staircase along the plan's stairs' sides (`pieces`)

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
import math
import re

import numpy

from score.review import plan_checks
from score.stages import row_kinds
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


def plan_sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def middle(item):
    return numpy.array([float(item[1]) + float(item[3]) / 2, float(item[2]) + float(item[4]) / 2])


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


def held(item, row, holder_row, holder_items, items, turn, room=None):
    """A relation to a holder the plan lays, its nearest item: top (where it fits under the place's height `room`),
    within it where the plan lays it inside, else against the face the concept shows it on, the plan's side toward
    it, its facing, its holder's, or S."""
    nearest = min(holder_items, key=lambda name: float(numpy.linalg.norm(middle(items[name]) - middle(item))))
    if on_top(row, holder_row) and fits_over(row, holder_row, room) and not design_shell.fills_opening(row):
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
    """The plan's walls as straight pieces: a straight wall itself, an arc (the greenhouse's round wall) its
    plan_checks.ROUND pieces round its centre."""
    found = []
    for wall in plan.get("walls") or []:
        if "from" in wall and "to" in wall:
            found.append(wall)
        elif "arc" in wall:
            arc = wall["arc"]
            turns = numpy.radians(numpy.linspace(float(arc["start"]), float(arc["end"]), plan_checks.ROUND + 1))
            line = [[round(float(arc["centre"][0]) + float(arc["radius"]) * math.cos(turn), 4),
                     round(float(arc["centre"][1]) + float(arc["radius"]) * math.sin(turn), 4)] for turn in turns]
            found += [{"from": first, "to": second, "thick": float(wall.get("thick") or design_shell.THICK)}
                      for first, second in zip(line, line[1:])]
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
    if off_line(spot, wall)[0] < 1e-6 or (placed and past_outline(spot, row, plan)):  # the side toward the plan's middle
        side = off_line(numpy.array([float(plan["w"]) / 2, float(plan["d"]) / 2]), wall)[1]
    return {"how": "wall", "wall": {key: wall[key] for key in ("from", "to", "thick")}, "side": side,
            "spot": [round(float(value), 3) for value in spot], "why": f"against the wall nearest {why}"}


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


def room_walls(found, items, rows, plan, turn, inventory):
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
            taken = {wall_key(other["wall"]) for other in held}
            free = [wall for wall in walls if wall_key(wall) not in taken] or walls
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


def cut_in(spot, row, item, plan):
    """A relation in an opening cut for the row (`cut`) where its spot meets the nearest wall, kept OPENING_ROOM and
    the wall's thickness inside its ends (camp's dome windows were cut on their walls' corners): the row's width,
    from its item's base (a window from WINDOW_SILL) to its top; None where the plan draws no wall."""
    walls = walls_of(plan)
    if not walls:
        return None
    wall = min(walls, key=lambda wall: off_line(spot, wall)[0])
    base = float(((plan.get("shapes") or {}).get(item[0]) or {}).get("base") or 0.0)
    sill = base or (WINDOW_SILL if kind_word(row) == "window" else 0.0)
    size = row.get("size") or [1.0, 0.1, design_shell.DOOR_HEAD]
    start, end = numpy.asarray(wall["from"], float), numpy.asarray(wall["to"], float)
    length = float(numpy.linalg.norm(end - start))
    run = (end - start) / max(length, 1e-9)
    keep = float(size[0]) / 2 + OPENING_ROOM + float(wall.get("thick") or 0.0)
    at = start + run * kept_along(float((on_line(spot, wall) - start) @ run), length, keep)
    return {"how": "in", "opening": {"at": [round(float(value), 3) for value in at],
                                     "wide": float(size[0]), "sill": sill, "head": round(sill + float(size[2]), 3),
                                     "cut": True},
            "wall": wall_part(wall), "why": "in an opening cut for it where it meets the nearest wall: the plan has no "
                                            f"free {kind_word(row)} opening"}


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


def face_spread(found, items, rows, plan, inventory, kinds):
    """The pieces against each holder's face that would overlap at their built sizes (along it and in height) spread
    along it in the order the plan draws them (spread_face), each relation of a piece moved given its pieces' `spots`
    and a moving door its recess at them; a face too short for them all keeps them as drawn, named in the
    [{holder, holder row, face, rows, why}] returned (street's 3 m window, stairwell entrance and roller shutters laid
    at their built widths on 1.74 m items, its sign over three air conditioners, #36)."""
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
        if all(later["along"] - later["before"] >= piece["along"] + piece["after"] - 1e-9 or not meet(piece, later)
               for number, piece in enumerate(pieces) for later in pieces[number + 1:]):
            continue
        lefts = spread_face(pieces, half)
        if lefts is None:
            crowded.append({"holder": holder, "holder row": holder_row, "face": face,
                            "rows": sorted({piece["entry"]["row"] for piece in pieces}),
                            "why": f"the face's {2 * half:.2f} m cannot hold its things at their built widths with "
                                   f"{OPENING_ROOM:g} m between those that meet in height and at its ends"})
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


def in_opening(item, row, plan, inventory, taken):
    """A door or window in an opening: each of its pieces (piece_spots) in the plan's nearest free opening, else in
    one cut for it on its nearest wall; one relation, or `pieces` one each; None where the plan draws no wall and no
    opening is left."""
    found = [in_plan_opening(spot, row, plan, taken) or (cut_in(spot, row, item, plan) if spot is not None else None)
             for spot in piece_spots(item, row, plan, inventory)]
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
    sides in turn, each spot the middle of a side, each way the stair's way up (0 east, 90 south)."""
    stairs = plan.get("stairs") or []
    found = []
    for number in range(count):
        stair = stairs[(number // 2) % len(stairs)]
        angle = math.radians(float(stair.get("angle") or 0.0))
        way = numpy.array([math.cos(angle), math.sin(angle)])
        across = numpy.array([-way[1], way[0]])
        points = numpy.asarray(stair["points"], float)
        middle_point, half = points.mean(axis=0), float(numpy.ptp(points @ across)) / 2
        spot = middle_point + across * half * (1 if number % 2 == 0 else -1)
        found.append({"how": "floor", "spot": [round(float(value), 3) for value in spot],
                      "way": [round(float(value), 6) + 0.0 for value in way],
                      "why": f"along the {'left' if number % 2 == 0 else 'right'} side of the plan's stair "
                             f"{(number // 2) % len(stairs) + 1}"})
    return found


def relation(item, row, rows, plan, inventory, laid, taken, turn, taken_stairs, kinds):
    """One item's relation (module docstring) for its row, or (None, why) when nothing holds it."""
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
            found[LINE] = (middle(holder_item), item_way(holder_item), holder_base)
        if len(shown) > 1:
            found["why"] += (f" (its things stand on {len(shown)} rows in the concept: "
                             f"{', '.join(other['id'] for other in shown)}; the nearest on the plan)")
        return found, None
    if holder is not None and holder["id"] not in laid and words_of(holder) & STAIR_WORDS and plan.get("stairs"):
        count = max(1, int(((plan.get("shapes") or {}).get(item[0]) or {}).get("count") or 1),
                    int(row.get("count") or 1) if item[0] == plan_checks.WALLS_ITEM else 1)
        return {"how": "floor", "pieces": stair_sides(plan, count), "why": f"along {holder['id']}'s stairs"}, None
    if kind is None and holder is not None and design_shell.fills_opening(row):
        kind = "wall"  # a door or window of a structure the plan's shell lays (camp's airlock entrance): in its wall
    if kind in ("floor", "ceiling"):
        return {"how": kind, **(floor_spot(item, row, plan, inventory, taken_stairs) or {}),
                "why": f"on the place's {kind}"}, None
    if kind != "wall":
        return None, (f"its holder {holder['id']} is neither laid on the plan nor a wall, floor or roof"
                      if holder is not None else None)
    found = in_opening(item, row, plan, inventory, taken) if design_shell.fills_opening(row) else None
    found = found or on_wall(item, row, plan, inventory)
    return (found, None) if found else (None, "it stands on a wall, and the plan draws none")


def plan_items(plan):
    return items_of(plan)[0]


def relations(plan, inventory, sha=None, kinds=None):
    """The place's relations (module docstring): one a plan item's row that stands on, against or in something;
    `kinds` the row-kind rules (score/stages/row_kinds.py's table by default)."""
    kinds = row_kinds.table() if kinds is None else kinds
    rows = {row["id"]: row for row in inventory.get("rows", [])}
    items, tied = items_of(plan)
    structure = set(plan.get("structure") or [])
    laid = {row_id: kept for row_id, names in tied.items() if row_id not in structure
            for kept in [[name for name in names if name != plan_checks.WALLS_ITEM]] if kept}
    found, unheld, taken, taken_stairs = [], [], set(), set()
    turn = plan_checks.viewed(plan, inventory)[2]  # the way the concept's viewer looks on the plan
    for name, item in items.items():
        for row_id in (plan.get("rows") or {}).get(name) or []:
            row = rows.get(row_id)
            if row is None:
                continue
            if (row.get("anchor") or "floor") in plan_checks.FLOOR_ANCHORS:
                got = (at_edge(row, plan, inventory, turn) if item[0] == plan_checks.WALLS_ITEM else None) or (
                    {"how": "floor", **spot} if (spot := floor_spot(item, row, plan, inventory, taken_stairs)) else
                    None) or up_to_level(item, row, plan)
                if got:
                    found.append({"item": name, "row": row_id, **got})
                continue
            got, why = relation(item, row, rows, plan, inventory, laid, taken, turn, taken_stairs, kinds)
            if got:
                found.append({"item": name, "row": row_id, **got})
            elif why:
                unheld.append({"item": name, "row": row_id, "why": why})
    room_walls(found, items, rows, plan, turn, inventory)
    crowded = spread(found) + face_spread(found, items, rows, plan, inventory, kinds)
    for entry in found:
        entry.pop(LINE, None)
    for _, openings in wall_openings(found).values():
        for _, opening in openings:
            opening.pop("drawn", None)
    return {"place": plan.get("place") or inventory.get("place"), "plan": sha,
            "about": "What holds each plan item, derived from the scene inventory's anchors, the concept's boxes and "
                     "the kept plan (score/review/holders); the scene record lays each object by it.",
            "relations": found, "unheld": unheld, **({"crowded": crowded} if crowded else {})}


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
