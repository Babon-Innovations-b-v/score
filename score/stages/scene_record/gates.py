"""The scene-record stage's gates, each measured on the written record against the design it was written from:

    game-free     no text of the record names a game file or the game's code (a Godot script or scene, a game path,
                  the game's class names): the record is made from the design, never transcribed
    plan-matched  the record is its plan's: where the record lays the room shell, every wall of the plan's outline
                  stands in it and every opening on a wall is cut through it (no wall piece fills the opening's middle
                  between its sill and its head), and every row the hand-in gives the shell (route `plan`) is named
                  on a piece of it (unbuilt_rows); every stair the plan draws is laid; every plan item of a glowing row
                  has its light over its footprint (one outlining the whole room on its wall's face); every glowing
                  row the plan lays has at least as many lamps as its reading counts things (count_faults)
    openings      every doorway leads somewhere: each door, gate or open doorway of the plan leads to a place of the
                  design, outside, sealed, onto a row of its own inventory (a ground it opens onto), or (none named)
                  into what holds it; a door to a place its holder's plan holds beside it has that place stood in the
                  record's places, each door to it meeting one of the stood place's leading back (within
                  place_plan.DOORS_MET along the floor, LEVEL_MET in height); and every view of an inside place
                  stands on its floor, inside its outline

Whether the made ground fits the place round its doorways is ground-fit's, judged on the assembly that stands on it.
"""
import json
import pathlib
import re

import numpy as np

from score import checks
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


def unbuilt_rows(record, handin):
    """Each row the hand-in gives the plan's shell to lay (route `plan`, writer.plan_rows) that no structure piece of
    the record is named for: a row the shell has no way to build, dropped without a word (the hangar's landing pad,
    wall pillars, floor grates and hatch, the garage's ceiling beams its lamps hang on, 2026-11-04)."""
    named = {entry.get("row") for entry in record.get("structure") or []}
    return [f"shell row {row_id} ({part}) is built by no piece of the shell" for part, ids in
            writer.plan_rows(handin).items() for row_id in ids if row_id not in named]


def judge_plan_matched(output, inputs, evidence):
    """Fail on a wall, opening, stair or lamp of the plan the record does not hold as the plan says, and on a row of
    the shell's that no piece of it builds (unbuilt_rows)."""
    place, record = writer.record_in(output)
    design = design_of(inputs, place)
    shelled = writer.inside(design) and not design_shell.laid_for(design)
    handin = pathlib.Path(inputs.get("hand-in") or "")
    faults = (wall_faults(record, design) + opening_faults(record, design) +
              (unbuilt_rows(record, json.loads(handin.read_text())) if handin.is_file() else [])
              if shelled else []) + stair_faults(record, design) + lamp_faults(record, design) + \
        count_faults(record, design, inputs)
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
    held = {hold["place"] for hold in (holder or {}).get("holds") or []}
    stood = {entry["name"] for entry in record["places"]}
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
    for entry in record["places"]:
        path = plans / f"{entry['name']}.json"
        doors = writer.place_plan.doors_to(design, entry["name"])
        if not doors or not path.is_file():
            continue
        other = json.loads(path.read_text())
        axes = writer.axes_in(design, other)
        back = [door_spot(other, door, entry["at"], axes) for door in writer.place_plan.doors_to(other, record["place"])]
        for door in doors:
            spot = door_spot(design, door)
            said = f"the door to {entry['name']} at {door['at']}"
            if not back:
                found.append(f"{said}: no door of {entry['name']} leads back")
                continue
            nearest = min(back, key=lambda there: float(np.linalg.norm((there - spot)[[0, 2]])))
            along, up = float(np.linalg.norm((nearest - spot)[[0, 2]])), abs(float(nearest[1] - spot[1]))
            if along > writer.place_plan.DOORS_MET or up > writer.place_plan.LEVEL_MET:
                found.append(f"{said} opens {along:.2f} m along the floor and {up:.2f} m in height from "
                             f"{entry['name']}'s nearest door back, as the record stands it")
    return found


def view_faults(record, design):
    """Each view of an inside place whose eye stands outside its outline."""
    if not record.get("inside"):
        return []
    outline, _ = writer.in_frame(design, design_shell.outline_of(design))
    return [f"view {view['name']} stands outside the place's outline at {view['eye']}" for view in record["views"]
            if not writer.inside_polygon([view["eye"][0], view["eye"][2]], outline)]


def judge_openings(output, inputs, evidence):
    """Fail on a doorway that leads nowhere the design knows, to a neighbour the record lacks or stands off its door
    back, or a view outside."""
    place, record = writer.record_in(output)
    design = design_of(inputs, place)
    faults = lead_faults(record, design, inputs) + pair_faults(record, design, inputs) + view_faults(record, design)
    doorways = sum(1 for opening in design.get("openings") or [] if opening.get("kind") in DOORWAYS)
    reason = "; ".join(faults[:3]) + (f" and {len(faults) - 3} more" if len(faults) > 3 else "") if faults else \
        (f"every doorway leads somewhere ({doorways} doorways, {len(record['places'])} neighbours stood) and every "
         "view stands in the place")
    return checks.Verdict("openings", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "doorways": doorways}, {"faults": "lower"}, tuple(faults))


CHECKS = (checks.Check("game-free", judge_game_free), checks.Check("plan-matched", judge_plan_matched),
          checks.Check("openings", judge_openings))
