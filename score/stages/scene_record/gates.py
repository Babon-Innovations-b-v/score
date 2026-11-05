"""The scene-record stage's gates, each measured on the written record against the design it was written from:

    game-free     no text of the record names a game file or the game's code (a Godot script or scene, a game path,
                  the game's class names): the record is made from the design, never transcribed
    plan-matched  the record is its plan's: where the record lays the room shell, every wall of the plan's outline
                  stands in it and every opening on a wall is cut through it (no wall piece fills the opening's middle
                  between its sill and its head), and every row the hand-in gives the shell (route `plan`) is named
                  on a piece of it (unbuilt_rows); every stair the plan draws is laid; every plan item of a glowing row
                  has its light over its footprint (one outlining the whole room on its wall's face); every glowing
                  row the plan lays has at least as many lamps as its reading counts things (count_faults); every
                  row laid numbers as its scene inventory counts unless the plan says why (row_count_faults)
    openings      every doorway leads somewhere: each door, gate or open doorway of the plan leads to a place of the
                  design, outside, sealed, onto a row of its own inventory (a ground it opens onto), or (none named)
                  into what holds it; a door to a place its holder's plan holds beside it has that place stood in the
                  record's places, each door to it meeting one of the stood place's leading back (within
                  place_plan.DOORS_MET along the floor, LEVEL_MET in height); and every view of an inside place
                  stands on its floor, inside its outline

Whether the made ground fits the place round its doorways is ground-fit's, judged on the assembly that stands on it.
"""
import json
import math
import pathlib
import re

import numpy as np

from score import checks
from score.review import holders
from score.stages.earth_seed import design_shell
from score.stages.scene_record import writer

# A game file or the game's code: a Godot script, scene or shader, a path into its tree, its shell class, its name
# (2099; a date of the year 2099, the scene time the physics is worked out at, is none).
GAME = re.compile(r"\.(gd|tscn|tres|gdshader)\b|res://|(^|[\s(])(game|sim)/\w|ModuleShell|module_shell|"
                  r"(?<![\d-])2099(?![\d-])")
# Plan numbers held within this (metres).
TOLERANCE = 0.05
# The kinds of opening a person walks through (a window is none).
DOORWAYS = ("door", "gate", "opening")


def strings(value, path=""):
    """Every text in a record with where it sits."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, inner in value.items():
            yield from strings(inner, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for number, inner in enumerate(value):
            yield from strings(inner, f"{path}[{number}]")


def judge_game_free(output, inputs, evidence):
    """Fail on any text of the record that names the game."""
    _, record = writer.record_in(output)
    found = tuple(f"{path}: {text[:120]}" for path, text in strings(record) if GAME.search(text))
    reason = f"{len(found)} texts name the game" if found else "no text of the record names the game"
    return checks.Verdict("game-free", checks.FAIL if found else checks.PASS, reason, {"game texts": len(found)},
                          {"game texts": "lower"}, found)


# --- plan-matched -------------------------------------------------------------------------------------------------

def design_of(inputs, place):
    """The place's kept plan (the design's)."""
    return json.loads((pathlib.Path(inputs["plans"]) / f"{place}.json").read_text())


def filled_at(record, point, height):
    """The names of the structure's slabs holding a point [x, z] at a height."""
    return [entry["name"] for entry in record["structure"] if entry["builder"] == "slab"
            and entry["low"] - TOLERANCE < height < entry["high"] + TOLERANCE
            and writer.inside_polygon(point, entry["points"])]


def opening_faults(record, design):
    """Each opening on one of the outline's walls that a wall piece of the record fills (between its sill and head)."""
    found = []
    outline = design_shell.outline_of(design)
    edges = list(zip(outline, outline[1:] + outline[:1]))
    for number, opening in enumerate(design.get("openings") or [], 1):
        on = [edge for edge in edges if design_shell.on_edge([{"at": opening["at"], "wide": float(opening["wide"]),
                                                                "sill": 0.0, "head": 0.0}],
                                                              *edge, design_shell.THICK)]
        if not on:
            continue
        start, end = np.asarray(on[0][0], float), np.asarray(on[0][1], float)
        thick = float(design_shell.written_wall(design, list(on[0][0]), list(on[0][1])).get("thick") or
                      design_shell.THICK)
        normal = design_shell.outward(start, end)
        middle = np.asarray(opening["at"], float) + normal * (design_shell.BACKING + thick / 2)
        sill = float(opening.get("sill") or 0.0)
        head = float(opening.get("head") or design_shell.DOOR_HEAD)
        (point,), floor = writer.in_frame(design, [middle], (sill + head) / 2)
        filled = filled_at(record, point, floor)
        if filled:
            found.append(f"opening {number} ({opening.get('kind')}) at {opening['at']} is filled by {filled}")
    return found


def wall_faults(record, design):
    """Each wall of the plan's outline the record's shell lacks."""
    names = {entry["name"] for entry in record["structure"]}
    return [f"the plan's {name.replace('_', ' ')} is not in the record's shell"
            for name, _, _ in design_shell.pieces(design) if name not in names]


def stair_faults(record, design):
    """Each stair or ramp the plan draws that the record does not lay."""
    laid = {entry["name"] for entry in record["structure"] if entry["builder"] == "stairs"}
    return [f"the plan's {entry.get('kind', 'stair')} {number} is not laid"
            for number, entry in enumerate(design.get("stairs") or [], 1)
            if len(entry.get("points") or []) >= 3 and f"{entry.get('kind', 'stair')}_{number}" not in laid]


def lamp_faults(record, design):
    """Each light of a glowing item that stands off its item's footprint."""
    found = []
    items = {item[0]: item for item in design.get("items") or []}
    for light in record["lights"]:
        named = re.match(r"plan item '(.+?)'", light.get("from", ""))
        if not named or named.group(1) not in items:
            found.append(f"light at {light['at']} names no plan item")
            continue
        name, x, y, wide, deep = items[named.group(1)][0], *[float(value) for value in items[named.group(1)][1:5]]
        box, _ = writer.in_frame(design, [[x, y], [x + wide, y + deep]])
        low, high = np.min(box, axis=0) - TOLERANCE, np.max(box, axis=0) + TOLERANCE
        spot = np.array([light["at"][0], light["at"][2]])
        if light.get("against"):  # held on its wall (writer.wall_lamp_spot): off that wall's face by LAMP_OUT
            start, end = (np.asarray(point, float) for point in light["against"])
            run = end - start
            nearest = start + run * float(np.clip((spot - start) @ run / max(float(run @ run), 1e-9), 0.0, 1.0))
            if float(np.linalg.norm(spot - nearest)) > writer.LAMP_OUT + TOLERANCE:
                found.append(f"the light of plan item {name!r} stands off its wall")
        elif not ((low <= spot).all() and (spot <= high).all()):
            found.append(f"the light of plan item {name!r} stands off its footprint")
    return found


def count_faults(record, design, inputs):
    """Each glowing row (writer.glowing_rows) the plan lays at an item that has fewer lamps in the record than its
    reading counts (its `count`; 2026-11-04: garage's three ceiling lamps, workshop's thirteen monitors and hangar's
    row of wall lamps each laid as one, and no gate compared a lamp with the inventory)."""
    glowing, _ = writer.glowing_rows(inputs)
    tied = {row for item in design.get("items") or [] if not (len(item) > 6 and item[6] == "zone")
            for row in (design.get("rows") or {}).get(item[0]) or []}
    made = {}
    for light in record["lights"]:
        made[light.get("row")] = made.get(light.get("row"), 0) + 1
    return [f"glowing row {row_id} has {made.get(row_id, 0)} lamps, its reading counts {int(row.get('count') or 1)}"
            for row_id, row in sorted(glowing.items())
            if row_id in tied and made.get(row_id, 0) < int(row.get("count") or 1)]


def row_count_faults(record, design, inputs):
    """Each row the record lays (a prop or shell row of the hand-in, not far, nor the place's structure, a person or
    seen beyond it) whose objects number other than its scene inventory counts, with no reason in the plan's
    `dropped` or notes naming it (2026-11-04 audit: the plan writer re-counted about 25 rows, hangar's crates 14 to
    7, and the record matched the plan, so nothing caught it)."""
    handin = json.loads(pathlib.Path(inputs["hand-in"]).read_text())
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text())
    laid = {row["id"] for row in handin.get("rows", []) if row.get("route", "prop") in writer.LAID_ROUTES
            and not row.get("far")}
    left = set(design.get("structure") or []) | set(design.get("beyond") or []) | \
        {row["id"] for row in inventory.get("rows", []) if row.get("noun") in ("person", "people")}
    said = json.dumps([design.get("dropped") or [], design.get("notes") or [],
                       [shape.get("note") for shape in (design.get("shapes") or {}).values()]])
    counted = {}
    for entry in record.get("objects", []):
        if entry.get("kind") == "object":
            counted[entry["row"]] = counted.get(entry["row"], 0) + 1
    return [f"row {row['id']}: {int(row.get('count') or 1)} in the scene inventory, {counted.get(row['id'], 0)} laid, "
            "and the plan says no reason" for row in inventory.get("rows", [])
            if row["id"] in laid - left and counted.get(row["id"], 0) != int(row.get("count") or 1)
            and row["id"] not in said]


def unbuilt_rows(record, handin):
    """Each row the hand-in gives the plan's shell to lay (route `plan`, writer.plan_rows) that no structure piece of
    the record is named for: a row the shell has no way to build, dropped without a word (the hangar's landing pad,
    wall pillars, floor grates and hatch, the garage's ceiling beams its lamps hang on, 2026-11-04)."""
    named = {entry.get("row") for entry in record.get("structure") or []}
    return [f"shell row {row_id} ({part}) is built by no piece of the shell" for part, ids in
            writer.plan_rows(handin).items() for row_id in ids if row_id not in named]


def judge_plan_matched(output, inputs, evidence):
    """Fail on a wall, opening, stair or lamp of the plan the record does not hold as the plan says, on a row of the
    shell's that no piece of it builds (unbuilt_rows), or a row laid another number of times than its scene inventory
    counts with no reason given (row_count_faults)."""
    place, record = writer.record_in(output)
    design = design_of(inputs, place)
    shelled = writer.inside(design) and not design_shell.laid_for(design)
    handin = pathlib.Path(inputs.get("hand-in") or "")
    faults = (wall_faults(record, design) + opening_faults(record, design) +
              (unbuilt_rows(record, json.loads(handin.read_text())) if handin.is_file() else [])
              if shelled else []) + stair_faults(record, design) + lamp_faults(record, design) + \
        count_faults(record, design, inputs) + row_count_faults(record, design, inputs)
    said = "its shell's walls and openings, " if shelled else \
        ("no shell of the record's (its base lays it), " if writer.inside(design) else "no shell (an open place), ")
    reason = "; ".join(faults[:3]) + (f" and {len(faults) - 3} more" if len(faults) > 3 else "") if faults else \
        f"the record holds its plan: {said}{len(record['lights'])} lamps"
    return checks.Verdict("plan-matched", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "lamps": len(record["lights"])}, {"faults": "lower"}, tuple(faults))


# --- openings -----------------------------------------------------------------------------------------------------

def lead_faults(record, design, inputs):
    """Each doorway leading nowhere the design knows, or to a place the holder holds beside it that the record does
    not stand."""
    places = {path.stem for path in pathlib.Path(inputs["plans"]).glob("*.json")}
    rows = {row["id"] for row in json.loads(pathlib.Path(inputs["inventory"]).read_text())["rows"]}
    _, holder = writer.holder_of(record["place"], inputs["plans"])
    held = {writer.place_plan.name_of(hold) for hold in (holder or {}).get("holds") or []}
    places |= held  # an instance of a place held several times (tube#3) is a place of the design
    stood = {entry.get("instance", entry["name"]) for entry in record["places"]}
    found = []
    for number, opening in enumerate(design.get("openings") or [], 1):
        to = opening.get("to")
        if opening.get("kind") not in DOORWAYS or to is None or to in writer.NOT_PLACES or to in rows:
            continue
        if to not in places:
            found.append(f"opening {number} leads to {to!r}, no place of the design nor a row of its inventory")
        elif to in held and to != record["place"] and to not in stood:
            found.append(f"opening {number} leads to {to}, which its holder holds beside it, but the record does not "
                         "stand it")
    return found


def door_spot(design, door, at=None, axes=None):
    """A door's middle on its sill in the frame of the place it is a door of, or, given where that place stands
    (`at`, its frame's `axes`: a stood place's), in the frame it stands in."""
    (point,), floor = writer.in_frame(design, [door["at"]], float(door.get("sill") or 0.0))
    spot = np.array([point[0], floor, point[1]])
    return spot if at is None else np.asarray(at, float) + spot @ axes


def pair_faults(record, design, inputs):
    """Each door of the place to a place it stands beside that meets no door of that place leading back where the
    record stands it: none leads back, or the nearest is off along the floor or in height."""
    found = []
    plans = pathlib.Path(inputs["plans"])
    _, holder = writer.holder_of(record["place"], inputs["plans"])
    holds = {writer.place_plan.name_of(hold): hold for hold in (holder or {}).get("holds") or []}
    own = writer.place_plan.hold_of(holder, record["place"]) if holder else None
    for entry in record["places"]:
        name = entry.get("instance", entry["name"])
        path = plans / f"{entry['stage']}.json"
        doors = writer.place_plan.doors_to(design, name)
        if not doors or not path.is_file():
            continue
        other_hold = holds.get(name) or {}
        other = writer.place_plan.as_held(other_hold, json.loads(path.read_text()))
        axes = writer.axes_in(design, other, own, other_hold) * np.asarray(entry.get("scale") or [1.0] * 3)[:, None]
        back = [door_spot(other, door, entry["at"], axes) for door in writer.place_plan.doors_to(other, record["place"])]
        for door in doors:
            spot = door_spot(design, door)
            said = f"the door to {name} at {door['at']}"
            if not back:
                found.append(f"{said}: no door of {name} leads back")
                continue
            nearest = min(back, key=lambda there: float(np.linalg.norm((there - spot)[[0, 2]])))
            along, up = float(np.linalg.norm((nearest - spot)[[0, 2]])), abs(float(nearest[1] - spot[1]))
            if along > writer.place_plan.DOORS_MET or up > writer.place_plan.LEVEL_MET:
                found.append(f"{said} opens {along:.2f} m along the floor and {up:.2f} m in height from "
                             f"{name}'s nearest door back, as the record stands it")
    return found


def view_faults(record, design):
    """Each view of an inside place whose eye stands outside its outline."""
    if not record.get("inside"):
        return []
    outline, _ = writer.in_frame(design, design_shell.outline_of(design))
    return [f"view {view['name']} stands outside the place's outline at {view['eye']}" for view in record["views"]
            if not writer.inside_polygon([view["eye"][0], view["eye"][2]], outline)]


# An opening stands within this share of its door row's metres (the drawing places it, the row sizes it), and a
# doorway a person walks through is at least PASSABLE metres wide (2026-11-04 audit: habitat's 2.2 m hatches cut
# 0.237 m wide, stairwell's 1 m doors 0.39 m).
DOOR_SHARE = 0.25
PASSABLE = 0.7
BEARING_REACH = 30.0  # degrees a doorway's bearing may stand off its door row's


def side_of(design, point):
    """The plan side (N, E, S or W) a plan point lies toward from the plan's middle, its box's half sides as one."""
    half = np.array([float(design["w"]) / 2, float(design["d"]) / 2])
    return holders.snapped((np.asarray(point, float) - half) / np.maximum(half, 1e-9))


def bearing_of(design, point):
    """A plan point's bearing from the plan's middle, degrees clockwise from north (up the plan)."""
    way = np.asarray(point, float) - [float(design["w"]) / 2, float(design["d"]) / 2]
    return math.degrees(math.atan2(float(way[0]), float(-way[1]))) % 360.0


def door_rows(design):
    """[(how it is placed: a side N/E/S/W, a bearing in degrees or another word (a tube's `near`), metres, words, sill
    or None, its lead, its along its side or None)] of the plan's door rows ([side, along, metres, words, sill], [bearing, metres, words],
    [word, metres, words]), each its lead under its side and along (`E:9`), else its key and sill (`W@9`), else its
    key."""
    leads, found = design.get("leads") or {}, []
    for door in design.get("doors") or []:
        if not isinstance(door, list) or len(door) < 3:
            continue
        sided = door[0] in holders.FACES
        metres, words = (door[2], door[3] if len(door) > 3 else "") if sided else (door[1], door[2])
        sill = float(door[4]) if sided and len(door) > 4 and door[4] is not None else None
        key = door[0] if isinstance(door[0], str) else f"{float(door[0]):g}"
        lead = (leads.get(f"{key}:{float(door[1]):g}") if sided else None) or (
            leads.get(f"{key}@{sill:g}") if sill is not None else None) or leads.get(key) or {}
        found.append((door[0], float(metres), str(words), sill, lead.get("to"), door[1] if sided else None))
    return found


def door_faults(design):
    """Each door row of the plan (door_rows) with no doorway of the plan's openings where it says (on its side and at
    its sill, at its bearing within BEARING_REACH, else leading where it leads), or one of another width than its
    metres (DOOR_SHARE), narrower than PASSABLE, or leading elsewhere than its lead; and, where the plan has door
    rows, each doorway none of them is (the scene record cuts the plan's openings, so the design's doors are what it
    stands)."""
    found, doors = [], door_rows(design)
    left = [(number, opening) for number, opening in enumerate(design.get("openings") or [], 1)
            if opening.get("kind") in DOORWAYS]
    for where, metres, words, sill, lead, along in doors:
        if where in holders.FACES:  # the nearest its along first (a wall with two doors)
            fits = sorted([pair for pair in left if side_of(design, pair[1]["at"]) == where and
                           (sill is None or abs(float(pair[1].get("sill") or 0.0) - sill) <= TOLERANCE)],
                          key=lambda pair: abs(float(pair[1]["at"][0 if where in ("N", "S") else 1]) - float(along)))
        elif isinstance(where, (int, float)):
            fits = sorted([pair for pair in left if abs((bearing_of(design, pair[1]["at"]) - float(where) + 180.0)
                                                         % 360.0 - 180.0) <= BEARING_REACH],
                          key=lambda pair: abs((bearing_of(design, pair[1]["at"]) - float(where) + 180.0) % 360.0
                                               - 180.0))
        else:
            fits = [pair for pair in left if lead is not None and pair[1].get("to") == lead]
        if not fits:
            found.append(f"door row {words!r} has no doorway where it says ({where})")
            continue
        number, opening = fits[0]
        left.remove(fits[0])
        wide = float(opening["wide"])
        if abs(wide - metres) > DOOR_SHARE * metres or wide < PASSABLE:
            found.append(f"opening {number} is {wide:g} m wide for door row {words!r} of {metres:g} m")
        if lead is not None and opening.get("to") != lead:
            found.append(f"opening {number} leads to {opening.get('to')!r}, its door row {words!r} to {lead!r}")
    return found + [f"opening {number} is no door row of the plan" for number, _ in (left if doors else [])]


def judge_openings(output, inputs, evidence):
    """Fail on a doorway that leads nowhere the design knows, to a neighbour the record lacks or stands off its door
    back, or a view outside."""
    place, record = writer.record_in(output)
    design = design_of(inputs, place)
    faults = lead_faults(record, design, inputs) + pair_faults(record, design, inputs) + view_faults(record, design) + \
        door_faults(design)
    doorways = sum(1 for opening in design.get("openings") or [] if opening.get("kind") in DOORWAYS)
    reason = "; ".join(faults[:3]) + (f" and {len(faults) - 3} more" if len(faults) > 3 else "") if faults else \
        (f"every doorway leads somewhere ({doorways} doorways, {len(record['places'])} neighbours stood) and every "
         "view stands in the place")
    return checks.Verdict("openings", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "doorways": doorways}, {"faults": "lower"}, tuple(faults))


# --- laid-as-designed ----------------------------------------------------------------------------------------------

# Two pieces of one row nearer than this stand at one spot, metres (each piece laid at its own).
SAME_SPOT = 0.02
# A seat its words put at, by or before a holder stands no further than this from the holder's built side, metres.
SEAT_REACH = 0.3
# A wall thing its words say is high, or a light, stands at least this far over the floor, metres.
OFF_FLOOR = 0.05
# A wall thing is longer than its wall's face by at most this share of it (the assembly shrinks it a few percent).
LONGER = 0.05


def plan_of_place(design, point):
    """A place point [x, y, z] as its plan spot [x, y] and its height over the floor."""
    corner, east, south = (np.asarray(value, float) for value in writer.place_plan.frame_of(design))
    turn = np.array([[east[0], south[0]], [east[2], south[2]]])
    spot = np.linalg.solve(turn, np.array([point[0] - corner[0], point[2] - corner[2]]))
    return spot, float(point[1] - corner[1])


def x_axis(rotation):
    """A turn about up [x, y, z, w] as the place way [x, z] its model's x points."""
    angle = 2 * math.atan2(float(rotation[1]), float(rotation[3]))
    return np.array([math.cos(angle), -math.sin(angle)])


def plan_turn(design, way):
    """A place way [x, z] as a plan way [x, y]."""
    _, east, south = writer.place_plan.frame_of(design)
    return np.linalg.solve(np.array([[east[0], south[0]], [east[2], south[2]]]), np.asarray(way, float))


def sizes_of(handin):
    """{row id: the size [wide, deep, tall] its objects are built at} (its take's model's row's, as the writer lays)."""
    by_id, models = {row["id"]: row for row in handin.get("rows", [])}, writer.models_of(handin)
    found = {}
    for row_id, row in by_id.items():
        model = models.get(row_id)
        size = by_id.get(model.removesuffix("_1"), row).get("size") if model else row.get("size")
        if writer.sized({"size": size}):
            found[row_id] = [float(side) for side in size]
    return found


def reach_along(entry, size, way):
    """Half a laid object's built footprint along a place way [x, z]: its box's support turned as it is laid."""
    x = x_axis(entry["rotation"])
    z = np.array([-x[1], x[0]])
    return abs(float(way @ x)) * size[0] / 2 + abs(float(way @ z)) * size[1] / 2


def spot_faults(objects):
    """Each two pieces of one row laid at one spot (within SAME_SPOT): one lump where the design shows several."""
    found, by_row = [], {}
    for entry in objects:
        by_row.setdefault(entry["row"], []).append(entry)
    for row, laid in by_row.items():
        for number, one in enumerate(laid):
            for other in laid[number + 1:]:
                if float(np.linalg.norm(np.subtract(one["at"], other["at"]))) < SAME_SPOT:
                    found.append(f"{one['name']} and {other['name']} of row {row} stand at one spot")
    return found


def held_wall_faults(objects, design, sizes, rows):
    """Each wall-held object that faces its wall (its model's front, FACING_WAY's, against its `out`), whose built
    length along its wall is more than the wall's face holds, or that stands on the floor where its words say it is
    high or it is a light."""
    found = []
    for entry in objects:
        on = entry.get("on") or {}
        if on.get("how") != "wall":
            continue
        start, end = (np.asarray(point, float) for point in on["span"])
        run = (end - start) / max(float(np.linalg.norm(end - start)), 1e-9)
        x = x_axis(entry["rotation"])
        if abs(float(x @ run)) > 0.7:  # its x along its wall (one deeper than wide lays its z there instead)
            ahead = plan_turn(design, x)
            front = writer.plan_way(design, [ahead[1], -ahead[0]])
            if float(np.asarray(front) @ np.asarray(on["out"], float)) < 0.0:
                found.append(f"{entry['name']} faces its wall, its back to the room")
        size = sizes.get(entry["row"])
        if size and max(size[0], size[1]) > float(np.linalg.norm(end - start)) * (1 + LONGER) + TOLERANCE:
            found.append(f"{entry['name']} is {max(size[0], size[1]):g} m long on a wall face "
                         f"{float(np.linalg.norm(end - start)):.2f} m long")
        row = rows.get(entry["row"]) or {"id": entry["row"]}
        _, height = plan_of_place(design, entry["at"])
        if height < OFF_FLOOR and (holders.where_words(row) & holders.HIGH_WORDS or
                                   holders.kind_words(row) & holders.LIGHT_WORDS):
            found.append(f"{entry['name']} stands on the floor, but its row is {row.get('where')!r} on its wall")
    return found


def roof_faults(objects, design, sizes, relations, rows):
    """Each object held under the roof (a `ceiling` relation) whose row hangs from it (holders.under_roof: anchored
    ceiling or roof, or its words say so) whose top is off the roof's underside over it by more than TOLERANCE."""
    hung = {(entry["item"], entry["row"]) for entry in (relations or {}).get("relations", [])
            if entry.get("how") == "ceiling" and holders.under_roof(rows.get(entry["row"]) or {})}
    found = []
    for entry in objects:
        named = re.match(r"plan item '(.+?)'", entry.get("from", ""))
        size = sizes.get(entry["row"])
        if not named or (named.group(1), entry["row"]) not in hung or not size:
            continue
        spot, height = plan_of_place(design, entry["at"])
        under = writer.roof_under(design, spot)
        if abs(height + size[2] - under) > TOLERANCE:
            found.append(f"{entry['name']}'s top stands {height + size[2]:.2f} m up, its roof's underside "
                         f"{under:.2f} m over it")
    return found


def seat_faults(objects, sizes, rows, design):
    """Each seat its words put at, by or before a holder (holders.beside_holder) that stands further than SEAT_REACH
    from the nearest of that holder's objects' built sides, or in it, or before none."""
    by_name = {entry["name"]: entry for entry in objects}
    found = []
    for entry in objects:
        row = rows.get(entry["row"])
        if not row or not holders.kind_words(row) & holders.SEAT_WORDS or \
                not holders.where_words(row) & holders.BESIDE_WORDS:
            continue
        held = [by_name[name] for name in (entry.get("beside") or {}).get("holder") or [] if name in by_name]
        if not held:
            if entry.get("beside"):
                found.append(f"{entry['name']} stands before {entry['beside']['holder item']}, which lays nothing")
            continue
        seat = np.array([entry["at"][0], entry["at"][2]])
        gaps = []
        for holder in held:  # the footprints' gap: their widest parting across either of the holder's sides
            middle, x = np.array([holder["at"][0], holder["at"][2]]), x_axis(holder["rotation"])
            gaps.append(max(abs(float((seat - middle) @ way)) - reach_along(holder, sizes.get(holder["row"], [0, 0, 0]),
                                                                              way)
                            - reach_along(entry, sizes.get(entry["row"], [0, 0, 0]), way)
                            for way in (x, np.array([-x[1], x[0]]))))
        gap = min(gaps)
        if not -TOLERANCE <= gap <= SEAT_REACH:
            found.append(f"{entry['name']} stands {gap:.2f} m from {entry['beside']['holder item']}, its words "
                         f"{row.get('where')!r}")
    return found


def judge_laid_as_designed(output, inputs, evidence):
    """Fail on pieces of one row at one spot, a wall thing facing its wall, longer than its wall or on the floor where
    its words say high, a thing hung from the roof off its underside, or a seat away from what it stands at."""
    place, record = writer.record_in(output)
    design = design_of(inputs, place)
    handin = json.loads(pathlib.Path(inputs["hand-in"]).read_text())
    rows = {row["id"]: row for row in json.loads(pathlib.Path(inputs["inventory"]).read_text()).get("rows", [])}
    sizes, objects = sizes_of(handin), [entry for entry in record.get("objects", []) if entry.get("kind") == "object"]
    relations, _ = writer.relations_input(inputs, place)
    faults = spot_faults(objects) + held_wall_faults(objects, design, sizes, rows) + \
        roof_faults(objects, design, sizes, relations, rows) + seat_faults(objects, sizes, rows, design)
    reason = "; ".join(faults[:3]) + (f" and {len(faults) - 3} more" if len(faults) > 3 else "") if faults else \
        f"its {len(objects)} objects stand as the design lays them"
    return checks.Verdict("laid-as-designed", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "objects": len(objects)}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("game-free", judge_game_free), checks.Check("plan-matched", judge_plan_matched),
          checks.Check("openings", judge_openings), checks.Check("laid-as-designed", judge_laid_as_designed))
