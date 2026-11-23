"""A laid place against its plan (scene_record/plan.py's place-plan, the plan in the place's frame): the plan taken in,
its views, its walls dressed from the library, and every way the laid place strays from it told for the placing agent
(ready.json's `plan`). The 2099 judge, 2026-11-23, scored all 20 places 3 to 6 of 10 on faults this tells: a room far
bigger than its plan, a block standing where the plan names a library thing, parts at the wrong scale, bare walls where
the plan's walls carry panels, pipes or grates, and a preview of one camera.

    take(folder, source) -> {"plan", "views"}      <folder>/plan.json, its views written as place.json views
    views(plan) -> {name: {eye, aim, fov}}         an eye-height view from each person spot and each doorway
    dress(folder, name, address, row, side, ...)   copies of a library piece along one plan wall or over the floor
    faults(stage, place, plan, role_of, outside)   [{"fault", ...}] where the laid place strays from its plan

The faults, each with its measure:
- `room oversized` / `room undersized`: the laid structures' footprint (role structure or shell) wider or deeper than
  the plan's floor by over ROOM times, or under 1/ROOM (an inside place only; an outside one's plan is its ground).
- `missing`: a plan item with no laid object standing in its box (its middle within NEAR of it).
- `block stands in`: a plan item where only made blocks stand (an algorithm's or no library address), the library
  thing the plan names left out.
- `too big` / `too small`: the library thing standing for a plan item (the one covering most of its box) with its
  long side over SCALE times the item's, or under 1/SCALE.
- `undressed`: a row of the plan's walls (environment_plan.WALLS_ITEM) that is a dressing (DRESSINGS: panels,
  grates, plates, pipes, rivets, seams, ducts, vents, cables, tiles) with no object dressed as it (`dress`,
  score:dress).
"""
import json
import math
import re
import pathlib
import shutil

import numpy as np
from pxr import Sdf, Usd, UsdGeom

from score.review.environment_plan import WALLS_ITEM
from score.stages import place_build
from score.stages.scene_record import plan as place_plan

PLAN = "plan.json"  # the place's plan in its folder (`take`)
ROOM = 1.25  # times the plan floor's wide or deep past which (or under 1/ROOM) the laid room is told
SCALE = 2.0  # times its plan item's long side past which (or under 1/SCALE) a library thing is told
NEAR = 0.3  # metres an object's middle may stand outside a plan item's box and still stand for it
DRESSINGS = ("panel", "grat", "plate", "pipe", "rivet", "seam", "duct", "vent", "cable", "tile")
LIBRARY_THINGS = ("model", "kit", "take")  # the kinds of library address that are things, never made blocks
UNJUDGED = ("ground", "shell", "connector", "light", "character", "scenery", "effect")  # roles no plan item reads
EYE = 1.6  # metres over the floor a plan view's eye stands
AIM = 1.2  # metres over the floor a plan view aims
INWARD = 0.6  # metres a doorway's view stands inside its doorway
FOV = 70.0  # a plan view's degrees across
VIEW_PREFIX = "plan-"  # a plan view's name: plan-stand-<k>, plan-<doorway>
# The plan's sides: N the wall at its least z, S at its most, W at its least x, E at its most (the plan's facings),
# and each side's way into the room.
SIDES = {"N": (2, 0, (0.0, 0.0, 1.0)), "S": (2, 1, (0.0, 0.0, -1.0)), "W": (0, 0, (1.0, 0.0, 0.0)),
         "E": (0, 1, (-1.0, 0.0, 0.0))}
FLOOR = "floor"  # dress's side for the floor: copies tiled over the plan's floor
FRONTS = {"+x": (1.0, 0.0), "-x": (-1.0, 0.0), "+z": (0.0, 1.0), "-z": (0.0, -1.0)}  # a piece's front, (x, z)


def plan_of(folder):
    """The place's plan (<folder>/plan.json), None when none was taken in."""
    path = pathlib.Path(folder) / PLAN
    return json.loads(path.read_text()) if path.exists() else None


def take(folder, source):
    """The place-plan `source` (scene_record/plan.py's plan.json, in the place's frame) taken in as <folder>/plan.json,
    refused when its contract faults it; its views (`views`) written as the place's named views, so `render` draws
    them with the concept's."""
    target = pathlib.Path(folder) / PLAN
    shutil.copyfile(source, target)
    wrong = place_plan.plan_faults(folder)
    if wrong:
        target.unlink()
        raise place_build.Refused(f"{source}: not a place plan ({'; '.join(wrong)})")
    plan = plan_of(folder)
    record = place_build.record_of(folder)
    kept = {name: view for name, view in record.get("views", {}).items() if not name.startswith(VIEW_PREFIX)}
    record["views"] = {**kept, **views(plan)}
    record["plan"] = str(source)
    place_build.write_record(folder, record)
    return {"plan": str(target), "views": sorted(views(plan))}


def middle_of(plan):
    """The plan floor's middle (x, z)."""
    floor = np.asarray(plan["floor"], dtype=float)
    return floor.mean(axis=0)


def views(plan):
    """An eye-height view from each person spot (aimed at what it looks at, else the floor's middle; from the middle
    itself, along the floor's longer side) and from each doorway, INWARD inside it, aimed at the floor's middle."""
    middle = middle_of(plan)
    floor = np.asarray(plan["floor"], dtype=float)
    level = float(plan.get("floor_height") or 0.0)
    found = {}
    for number, spot in enumerate(plan.get("standing", []), 1):
        at = np.asarray(spot["at"], dtype=float)
        target = middle if np.linalg.norm(middle - at) > 1.0 else at + along_longer(floor)
        height = float(spot.get("level", level))
        found[f"{VIEW_PREFIX}stand-{number}"] = view_at(at, height, target, level)
    for doorway in plan.get("doorways", []):
        inward = np.asarray(doorway["inward"], dtype=float)
        at = np.asarray(doorway["middle"], dtype=float)[[0, 2]] + INWARD * inward[[0, 2]]
        sill = float(doorway["middle"][1])
        found[f"{VIEW_PREFIX}{doorway['name']}"] = view_at(at, sill, middle, level)
    return found


def along_longer(floor):
    """Half the floor's longer side, as an (x, z) step along it."""
    wide, deep = floor[1] - floor[0]
    return np.array([wide / 2.0, 0.0]) if wide >= deep else np.array([0.0, deep / 2.0])


def view_at(at, height, target, level):
    """A view standing at (x, z) `at` on `height`, aimed at (x, z) `target` AIM over the floor `level`."""
    return {"eye": [round(float(at[0]), 4), round(height + EYE, 4), round(float(at[1]), 4)],
            "aim": [round(float(target[0]), 4), round(level + AIM, 4), round(float(target[1]), 4)], "fov": FOV}


# --- the faults ---------------------------------------------------------------------------------------------------

def laid_objects(stage, place, role_of, left_out=()):
    """Each laid object under Objects with a shape: {name, address, role, low, high} (its world box, metres); the
    objects `left_out` (place.json `backdrop`: a neighbour's part of the concept, none of the place's) skipped."""
    boxes = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found = []
    for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
        if prim.GetName() in left_out:
            continue
        box = boxes.ComputeWorldBound(prim).ComputeAlignedRange()
        if box.IsEmpty():
            continue
        address = prim.GetAttribute("score:library").Get() if prim.GetAttribute("score:library") else None
        dressed = prim.GetAttribute("score:dress").Get() if prim.GetAttribute("score:dress") else None
        found.append({"name": prim.GetName(), "address": address, "role": role_of(prim), "dress": dressed,
                      "low": np.array(box.GetMin(), dtype=float), "high": np.array(box.GetMax(), dtype=float)})
    return found


def faults(stage, place, plan, role_of, outside=False, left_out=()):
    """Every way the laid place strays from its plan (the module's list); its backdrop (`left_out`) is none of it."""
    laid = laid_objects(stage, place, role_of, left_out)
    return ([] if outside else room_faults(plan, laid)) + item_faults(plan, laid) + dress_faults(plan, laid)


def room_faults(plan, laid):
    """The laid structures' footprint against the plan's floor, wide and deep."""
    structures = [each for each in laid if each["role"] in ("structure", "shell")]
    if not structures:
        return []
    low = np.min([each["low"][[0, 2]] for each in structures], axis=0)
    high = np.max([each["high"][[0, 2]] for each in structures], axis=0)
    floor = np.asarray(plan["floor"], dtype=float)
    laid_size, plan_size = high - low, floor[1] - floor[0]
    ratio = laid_size / np.maximum(plan_size, 1e-6)
    sizes = {"laid": np.round(laid_size, 2).tolist(), "plan": np.round(plan_size, 2).tolist()}
    if ratio.max() > ROOM:
        return [{"fault": "room oversized", **sizes, "why": f"the laid room is {ratio.max():.2f} times its plan's "
                 f"{'wide' if ratio[0] >= ratio[1] else 'deep'}: its props stand lost in it"}]
    if ratio.min() < 1.0 / ROOM:
        return [{"fault": "room undersized", **sizes, "why": f"the laid room is {ratio.min():.2f} times its plan's "
                 f"{'wide' if ratio[0] <= ratio[1] else 'deep'}"}]
    return []


def is_library_thing(each):
    """Whether a laid object is a library thing (a model, kit piece or take), not a made block."""
    return bool(each["address"]) and each["address"].split("/", 1)[0] in LIBRARY_THINGS


def standing_in(item, laid):
    """The laid objects a plan item reads: their middle (x, z) within NEAR of its box, no role UNJUDGED, no dressing,
    and no structure over SCALE times the item across (a roof or a wall over the room is the building, not a stand-in:
    engineroom@7's roof stood in the core's box)."""
    x0, z0, x1, z1 = item["box"]
    across = max(x1 - x0, z1 - z0)
    found = []
    for each in laid:
        middle = (each["low"] + each["high"])[[0, 2]] / 2.0
        size = each["high"] - each["low"]
        if each["role"] in UNJUDGED or each["dress"]:
            continue
        if each["role"] == "structure" and max(size[0], size[2]) > SCALE * across:
            continue
        if x0 - NEAR <= middle[0] <= x1 + NEAR and z0 - NEAR <= middle[1] <= z1 + NEAR:
            found.append(each)
    return found


def named_by(item, each):
    """Whether a laid object is named for one of the item's rows: a word of a row in its name or address (the bowl
    `bowl_2` for the row bowl, `basin_stand` for wash_stand)."""
    words = {word for row in item.get("rows") or [] for word in row.lower().split("_") if len(word) > 2}
    said = re.split(r"[^a-z0-9]+", f"{each['name']} {each['address'] or ''}".lower())
    return bool(words & set(said))


def covering(item, things):
    """Of the library things, the one whose footprint covers most of the item's box, among those named for its rows
    when any is (a bowl on a table reads as the bowl, never the table it stands on)."""
    x0, z0, x1, z1 = item["box"]
    things = [each for each in things if named_by(item, each)] or things

    def covered(each):
        across = max(0.0, min(x1, each["high"][0]) - max(x0, each["low"][0]))
        along = max(0.0, min(z1, each["high"][2]) - max(z0, each["low"][2]))
        return across * along
    return max(things, key=covered)


def item_faults(plan, laid):
    """Each plan item (no zone, not the walls) missing, stood in for by blocks, or at the wrong scale."""
    found = []
    for item in plan.get("items", []):
        if item.get("kind") != "item" or item["name"] == WALLS_ITEM:
            continue
        rows = item.get("rows") or []
        there = standing_in(item, laid)
        if not there:
            found.append({"fault": "missing", "item": item["name"], "rows": rows,
                          "why": f"nothing laid stands in the plan's {item['name']}"})
            continue
        things = [each for each in there if is_library_thing(each)]
        if not things:
            found.append({"fault": "block stands in", "item": item["name"], "rows": rows,
                          "objects": sorted(each["name"] for each in there),
                          "why": f"only made blocks stand where the plan names {', '.join(rows) or item['name']}: "
                                 "lay its library thing"})
            continue
        found += scale_faults(item, covering(item, things))
    return found


def scale_faults(item, thing):
    """The library thing standing for a plan item too big or too small against it (their long sides)."""
    x0, z0, x1, z1 = item["box"]
    planned = max(x1 - x0, z1 - z0)
    size = thing["high"] - thing["low"]
    laid = max(size[0], size[2])
    ratio = laid / max(planned, 1e-6)
    measure = {"item": item["name"], "object": thing["name"], "laid": round(float(laid), 2),
               "plan": round(float(planned), 2)}
    if ratio > SCALE:
        return [{"fault": "too big", **measure, "why": f"{thing['name']} is {ratio:.1f} times the plan's "
                 f"{item['name']} across"}]
    if ratio < 1.0 / SCALE:
        return [{"fault": "too small", **measure, "why": f"{thing['name']} is {ratio:.2f} times the plan's "
                 f"{item['name']} across"}]
    return []


def is_dressing(row):
    return any(word in row.lower() for word in DRESSINGS)


def dress_faults(plan, laid):
    """Each dressing row of the plan's walls no laid object is dressed as."""
    walls = [item for item in plan.get("items", []) if item["name"] == WALLS_ITEM]
    rows = sorted({row for item in walls for row in item.get("rows") or [] if is_dressing(row)})
    dressed = {each["dress"] for each in laid if each["dress"]}
    return [{"fault": "undressed", "row": row,
             "why": f"the plan's walls carry {row}: dress them with its library piece (`dress`)"}
            for row in rows if row not in dressed]


# --- dressing -----------------------------------------------------------------------------------------------------

def yaw_to(front, inward):
    """The degrees about up turning a piece's `front` ((x, z)) onto `inward` ((x, z)), as a USD rotateY turns."""
    return round(math.degrees(math.atan2(inward[0], inward[1]) - math.atan2(front[0], front[1])) % 360.0, 6)


def runs(span, piece, every):
    """The middles along a run of `span` (low, high) of copies `piece` long, `every` apart (the piece's own length
    when none: edge to edge, their seams showing), centred on the run."""
    every = float(every or piece)
    low, high = span
    count = int(math.floor((high - low - piece) / every + 1e-9)) + 1
    if count < 1:
        return []
    start = (low + high) / 2.0 - (count - 1) * every / 2.0
    return [start + index * every for index in range(count)]


def clear_of_doorways(plan, axis, middle, piece, line, side_axis):
    """Whether a copy of length `piece` at `middle` along `axis` on a wall at `line` (on `side_axis`) keeps out of
    every plan doorway in that wall."""
    for doorway in plan.get("doorways", []):
        at = doorway["middle"]
        if abs(at[side_axis] - line) > NEAR:
            continue
        if abs(at[axis] - middle) < (float(doorway["wide"]) + piece) / 2.0:
            return False
    return True


def wall_spots(plan, side, piece, every, wall_face):
    """The (x, z) spots of copies along the plan's wall `side` (N, S, E or W), backs on the laid wall's inner face
    `wall_face`, `piece` (length along the wall, depth off it) a copy's size, doorways kept clear."""
    side_axis, end, inward = SIDES[side]
    axis = 2 if side_axis == 0 else 0
    floor = np.asarray(plan["floor"], dtype=float)
    span = (floor[0][axis // 2], floor[1][axis // 2])
    line = float(floor[end][side_axis // 2])
    depth_off = wall_face + inward[side_axis] * piece[1] / 2.0
    spots = []
    for middle in runs(span, piece[0], every):
        if not clear_of_doorways(plan, axis, middle, piece[0], line, side_axis):
            continue
        spot = [0.0, 0.0]
        spot[axis // 2], spot[side_axis // 2] = middle, depth_off
        spots.append(spot)
    return spots


def floor_spots(plan, piece, every):
    """The (x, z) spots of copies tiled over the plan's floor, `piece` (x, z) a copy's size."""
    floor = np.asarray(plan["floor"], dtype=float)
    xs = runs((floor[0][0], floor[1][0]), piece[0], every)
    zs = runs((floor[0][1], floor[1][1]), piece[1], every)
    return [[x, z] for x in xs for z in zs]


def dress(folder, name, address, row, side, support=None, height=0.0, every=None, front="+z"):
    """Copies of the library piece `address` dressing the plan's `row` (a wall panel, a pipe run, a floor grate): along
    the plan wall `side` (N, S, E or W), backs on the inner face of the laid wall `support` (mounted on it, role
    mount), `height` metres over the floor, its `front` turned into the room; or tiled over the floor (`side` floor).
    `every` metres apart (the piece's own length: edge to edge, seams showing). Each copy is laid as
    <name>_<side><k> (`put`), marked score:dress = `row`, so the check reads the row dressed."""
    plan = plan_of(folder)
    if plan is None:
        raise place_build.Refused("no plan: take the place's plan in first (plan <folder> <plan.json>)")
    if side != FLOOR and side not in SIDES:
        raise place_build.Refused(f"a side is {', '.join(SIDES)} or {FLOOR}, not {side}")
    if front not in FRONTS:
        raise place_build.Refused(f"a front is {', '.join(FRONTS)}, not {front}")
    if side != FLOOR and not support:
        raise place_build.Refused("a wall's dressing names the laid wall it is mounted on (--support)")
    level = float(plan.get("floor_height") or 0.0)
    inward = (0.0, 0.0, 1.0) if side == FLOOR else SIDES[side][2]
    turn = [0.0, yaw_to(FRONTS[front], (inward[0], inward[2])) if side != FLOOR else 0.0, 0.0]
    first = f"{name}_{side}0"
    place_build.put(folder, first, address, at=(0.0, level + float(height), 0.0), turn=turn, rest=True)
    stage, place = place_build.opened(folder)
    size, offset = laid_size(stage, place, first)
    if side == FLOOR:
        spots = floor_spots(plan, (size[0], size[2]), every)
        role, mount = None, None
    else:
        side_axis = SIDES[side][0]
        piece = (size[2 - side_axis], size[side_axis])
        spots = wall_spots(plan, side, piece, every, inner_face(stage, place, support, side, plan))
        role, mount = "mount", f"wall:{support}"
    if not spots:
        place_build.remove(folder, first)
        raise place_build.Refused(f"no copy of {address} fits along {side}")
    laid = []
    for index, spot in enumerate(spots):
        copy = f"{name}_{side}{index}"
        at = (spot[0] - offset[0], level + float(height), spot[1] - offset[1])
        place_build.put(folder, copy, address, at=at, turn=turn, rest=True, role=role, support=mount)
        marked_dressing(folder, copy, row)
        laid.append(copy)
    return {"row": row, "side": side, "copies": laid, "piece": [round(value, 3) for value in size]}


def laid_size(stage, place, name):
    """A laid object's world box size (x, y, z) and its box middle's (x, z) offset from its spot."""
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]) \
        .ComputeWorldBound(prim).ComputeAlignedRange()
    at = place_build.pose_of(prim)[0]
    low, high = np.array(box.GetMin()), np.array(box.GetMax())
    middle = (low + high) / 2.0
    return (high - low).tolist(), (float(middle[0] - at[0]), float(middle[2] - at[2]))


def inner_face(stage, place, support, side, plan):
    """The laid wall's face toward the room on `side`'s axis (its box's side nearest the plan floor's middle)."""
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{support}")
    if not prim:
        raise place_build.Refused(f"the scene holds no wall {support}")
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]) \
        .ComputeWorldBound(prim).ComputeAlignedRange()
    side_axis = SIDES[side][0]
    faces = (box.GetMin()[side_axis], box.GetMax()[side_axis])
    middle = middle_of(plan)[side_axis // 2]
    return float(min(faces, key=lambda face: abs(face - middle)))


def marked_dressing(folder, name, row):
    """The laid copy marked as dressing the plan's `row` (score:dress)."""
    stage, place = place_build.opened(folder)
    stage.GetPrimAtPath(f"/{place}/Objects/{name}").CreateAttribute(
        "score:dress", Sdf.ValueTypeNames.String).Set(row)
    place_build.saved(stage)
