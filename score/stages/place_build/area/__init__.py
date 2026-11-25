"""Places of one area fitted together (#150; the 2099 prologue, 2026-11-20: its walker stopped on the flat's landing
and never reached the stairwell, the flat laid at the street's level and raised by hand in the game). Each place_build
place is built in its own frame; this module seats them in the area's one frame and checks every join between them.

Where places meet comes from the kept plans (scene_record/plan.py, the outside place's plan `holds` the area's places):
two held places join where a door of one leads to the other and the other's door leads back (`plan.paired`), and the
plan's floor heights (`plan.levels_of`: the stairwell's flat door 9 m up, so the flat's floor 9 m up) are the storey
heights. Where the joined doorways stand in each place's built scene is its folder's place.json `joins` (`join`):
a doorway the stair core recorded when it was laid (place.json `doorways`) or a door leaf of the scene, each with its
sill middle, its inward way (into its own place) and its width, and the place it leads to.

    join(folder, doorway, to, inward=None)  a recorded doorway or a door leaf marked as the one leading to `to`
    seated(plans, outside, folders)         {place: its seat}, each joined place at its plan's storey height with its
                                            door on its neighbour's, the rest as laid; the joins and their faults
    shells_crossed(folders, seats)          a fault for each two seated places' shells standing inside each other
    area(plans, outside, folders, out)      the seats and the joins check written as one record (seats.json)

A seat is the place's frame in the area's: a turn about up and a shift, a 4 x 4 matrix in USD's row-vector order
(the 16 numbers of glTF's column-major matrix). The outside place is the area's frame; when no place left is joined
to a seated one, the lowest of them on the plans is seated as laid (the area's one frame), and says so.

The joins check, per joined pair: the two doorways' sills at one height in the area (LEVEL), their middles together
along the floor (ALIGN) and facing each other (FACING), a door leaf no wider than the doorway it is seated in
(ready.FIT), and a walker's way WALKWAY wide from INSIDE in from one doorway to INSIDE in from the other, over the
walkers' floor of both places' objects round the join (REACH), seated, every doorway open as ready's walkway check
judges a doorway a way (ready.route_on; a leaf's swing is each place's own check). A failed join is told by its places and doorways; never
loosen LEVEL or ALIGN to pass one: the place is rebuilt, or the plan says another storey.
"""
import json
import math
import pathlib
import types

import numpy as np
from pxr import Gf, Sdf, Usd, UsdGeom

from score.stages import place_build
from score.stages.place_build import ready
from score.stages.scene_record import plan

LEVEL = 0.03  # metres two joined doorways' sills may stand apart in height
ALIGN = 0.05  # metres two joined doorways' middles may stand apart along the floor
FACING = 5.0  # degrees two joined doorways may turn off facing each other
INSIDE = 2.0  # metres in from a doorway a join's route starts and ends: past its reveal and a hall stub (1.4 m)
REACH = 5.0  # metres round a join's doorway the objects its route is walked over are gathered
AREA = "area"  # the default prim of the stage a join's route is walked on
SEPARATOR = "__"  # an object's name there: its place, this, its own name
SHELLS = ("shell", "connector", "structure")  # the roles a place's built shell is of (ready's walls)
CROSSED = 1.0  # cubic metres two seated places' shells may stand inside each other (a sill on a reveal, a seam)
STEP = 0.1  # metres between the points the crossed volume is counted at
POINTS = 200_000  # points counted at most in one pair of solids' common box (STEP grown to keep within it)


def leaf_doorway(stage, place, name):
    """A door leaf's doorway: its sill middle (the leaf's middle at its lowest point), its through axis (level) and its
    width (its longer level side); Refused when the scene holds no such object."""
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    if not prim:
        raise place_build.Refused(f"the scene holds no doorway or object {name}")
    mesh = ready.solid_of(prim)
    if mesh is None:
        raise place_build.Refused(f"{name} has no triangles to read a doorway from")
    middle, axes, half = ready.frame_of(types.SimpleNamespace(prims={name: prim}, meshes={name: mesh}), name)
    sill = float(mesh.bounds[0][1])
    through = np.array([axes[2][0], 0.0, axes[2][2]])
    return {"middle": [float(middle[0]), sill, float(middle[2])], "through": through / np.linalg.norm(through),
            "wide": round(2 * float(half[0]), 4), "sill": round(sill, 4), "head": round(float(mesh.bounds[1][1]), 4)}


def leaf_inward(folder, middle, through):
    """The side of a leaf's plane its own place lies on, as ready.inward reads it (the shell or connector holding the
    leaf's middle); None when it is set in none."""
    stage, place = place_build.opened(folder)
    return ready.inward(ready.Place(stage, place), np.asarray(middle, float), through)


def join(folder, doorway, to, inward=None):
    """`doorway` of the place in `folder` marked as the one leading to place `to` (place.json `joins`): a doorway the
    stair core recorded (place.json `doorways`), else a door leaf of the scene, its inward way (x, z) given or read
    from the shell it is set in (Refused when none holds it: give `inward`)."""
    record = place_build.record_of(folder)
    recorded = (record.get("doorways") or {}).get(doorway)
    if recorded:
        spot = {key: recorded[key] for key in ("middle", "inward", "wide", "sill", "head")}
        if inward is not None:
            spot["inward"] = level_unit((inward[0], 0.0, inward[1]))
        spot["from"] = f"the doorway {doorway} as laid"
    else:
        stage, place = place_build.opened(folder)
        leaf = leaf_doorway(stage, place, doorway)
        if inward is not None:
            way = level_unit((inward[0], 0.0, inward[1]))
            if abs(float(np.dot(way, leaf["through"]))) < math.cos(math.radians(FACING)):
                raise place_build.Refused(f"{doorway}'s inward {list(inward)} lies along its leaf, not through it")
            side = 1.0 if np.dot(way, leaf["through"]) > 0 else -1.0
        else:
            side = leaf_inward(folder, leaf["middle"], leaf["through"])
            if side is None:
                raise place_build.Refused(f"{doorway} is set in no shell or connector to read its inside from: "
                                          "give its --inward x,z")
        spot = {"middle": np.round(leaf["middle"], 4).tolist(),
                "inward": np.round(leaf["through"] * side, 6).tolist(), "wide": leaf["wide"], "sill": leaf["sill"],
                "head": leaf["head"], "from": f"the door leaf {doorway}"}
    record.setdefault("joins", {})[doorway] = {**spot, "to": to}
    place_build.write_record(folder, record)
    return {"joins": record["joins"]}


def level_unit(vector):
    """A way made level and of length one; Refused when it has no level part."""
    vector = np.array([float(vector[0]), 0.0, float(vector[2])])
    length = float(np.linalg.norm(vector))
    if length < 1e-9:
        raise place_build.Refused("a doorway's inward way has no level part")
    return np.round(vector / length, 6).tolist()


# --- seats -------------------------------------------------------------------------------------------------------

def heading(vector):
    """A level way's heading about up (radians), as USD's rotateY turns it: (sin h, cos h) in (x, z)."""
    return math.atan2(float(vector[0]), float(vector[2]))


def seat_matrix(turn, shift):
    """The seat as a 4 x 4 column matrix: rotateY by `turn` radians, then `shift` (x, y, z)."""
    cos, sin = math.cos(turn), math.sin(turn)
    matrix = np.identity(4)
    matrix[:3, :3] = [[cos, 0.0, sin], [0.0, 1.0, 0.0], [-sin, 0.0, cos]]
    matrix[:3, 3] = shift
    return matrix


def put(seat, point):
    """A place point put in the area by its seat."""
    return seat[:3, :3] @ np.asarray(point, float) + seat[:3, 3]


def seat_onto(seat, doorway, other, rise):
    """The seat that puts `other`'s doorway on `doorway` (seated by `seat`), facing it, its floor `rise` metres over
    the seated place's floor (the plans' storey heights): its sill there, its level middle on the doorway's."""
    target = -(seat[:3, :3] @ np.asarray(doorway["inward"], float))
    turn = heading(target) - heading(other["inward"])
    turned = seat_matrix(turn, (0.0, 0.0, 0.0))[:3, :3] @ np.asarray(other["middle"], float)
    there = put(seat, doorway["middle"])
    return seat_matrix(turn, (there[0] - turned[0], seat[1, 3] + rise, there[2] - turned[2]))


def with_holder(held, outside, holder):
    """`held` with the outside place itself among them, held at its own corner (plan.on_holder: its plan points as
    they are), so a door of the outside leading to a place it holds is a join like a sibling's (2099 #161: the pad's
    walkway hatch leads into the capsule its plan holds at the tower's top)."""
    return {**held, outside: ({"place": outside, "x": 0.0, "y": 0.0}, holder)}


def planned_joins(holder, plans, outside):
    """Each pair of places of the area (the held places and the outside itself, `with_holder`) a door of one joins to
    a door of the other leading back, nearest first: (place, other, its door, the door back), each pair of doors once;
    and the faults of each pair the holder's plan holds more than plan.DOORS_MET apart (2099 #161: the square's plan
    held the street 45 m from the stairwell whose door leads to it). Such a pair is still a join: both plans lead it,
    the built doorways seat it, and the holder's plan is told to be fixed. A place's second door to the same neighbour
    pairs only when it meets on the plan. The held places alone are returned first."""
    held = plan.held_plans(holder, plans)
    found, faults = [], []
    placed = with_holder(held, outside, holder)
    for name, (hold, own) in sorted(placed.items()):
        for other, (other_hold, other_plan) in sorted(placed.items()):
            if other <= name:
                continue
            pairs = [pair for pair in plan.paired(own, hold, name, other_plan, other_hold, other)
                     if pair["back"] is not None]
            met = [pair for pair in pairs if pair["gap"] <= plan.DOORS_MET] or pairs[:1]
            found += [(name, other, pair["door"], pair["back"]) for pair in met]
            faults += [f"{name}'s plan door to {other} (sill {plan.sill(pair['door']):g} m) stands {pair['gap']:.2f} m "
                       f"from {other}'s door back on the holder's plan (its holds; within {plan.DOORS_MET:g} m)"
                       for pair in met if pair["gap"] > plan.DOORS_MET]
    return held, found, faults


def built_joins(folders, planned):
    """Each planned join with the doorways the two places' folders join to each other, matched by height in order
    (the lowest planned door to the lowest joined doorway); a planned join a folder joins no doorway for is told."""
    records = {name: place_build.record_of(folder).get("joins") or {} for name, folder in folders.items()}
    used, found, faults = set(), [], []
    for name, other, door, back in sorted(planned, key=lambda entry: plan.sill(entry[2])):
        if name not in folders or other not in folders:
            continue
        ends = []
        for place, to, planned_door in ((name, other, door), (other, name, back)):
            free = sorted(((key, spot) for key, spot in records[place].items()
                           if spot["to"] == to and (place, key) not in used), key=lambda entry: entry[1]["sill"])
            if not free:
                faults.append(f"{place}'s plan door to {to} (sill {plan.sill(planned_door):g} m) has no doorway "
                              f"joined to {to} in {folders[place]} (place_build join <folder> <doorway> {to})")
                break
            used.add((place, free[0][0]))
            ends.append((place, free[0][0], free[0][1]))
        if len(ends) == 2:
            found.append(ends)
    return found, faults


def grown(seats, joins, levels):
    """`seats` grown by every place joined to a seated one, seated onto it (seat_onto), until none is left to seat."""
    more = True
    while more:
        more = False
        for (name, key, spot), (other, other_key, other_spot) in joins:
            for (place, door), (next_place, next_door, next_spot) in (((name, spot), (other, other_key, other_spot)),
                                                                      ((other, other_spot), (name, key, spot))):
                if place in seats and next_place not in seats:
                    rise = levels.get(next_place, 0.0) - levels.get(place, 0.0)
                    seats[next_place] = {"matrix": seat_onto(seats[place]["matrix"], door, next_spot, rise),
                                         "from": f"its {next_door} on {place}'s doorway, its floor {rise:g} m over "
                                                 f"{place}'s (their plans' storeys)"}
                    more = True


def held_seat(holder, held, levels, name):
    """The seat of a place no door joins to a seated one: where the outside's plan holds it (its plan laid in its hold,
    plan.on_holder, each plan point put in its place by plan.placed), its floor at its plan's storey; as laid in the
    area's one frame when the outside's plan holds none of it (2099 #161: the street stood as laid on the square's
    middle, 45 m off where the square's plan holds it)."""
    if name not in held:
        return {"matrix": np.identity(4), "from": "no door joins it to a seated place, the outside's plan holds none "
                                                  "of it, and it stands lowest of those left: as laid, in the area's "
                                                  "one frame"}
    hold, own = held[name]
    ends = [(0.0, 0.0), (float(own["w"]), 0.0)]
    there = [plan.placed(holder, *plan.on_holder(hold, own, end)) for end in ends]
    here = [plan.placed(own, *end) for end in ends]
    turn = heading(there[1] - there[0]) - heading(here[1] - here[0])
    turned = seat_matrix(turn, (0.0, 0.0, 0.0))[:3, :3] @ here[0]
    rise = levels.get(name, 0.0)
    return {"matrix": seat_matrix(turn, (there[0][0] - turned[0], rise, there[0][2] - turned[2])),
            "from": f"no door joins it to a seated place, and it stands lowest of those left: where the outside's "
                    f"plan holds it, its floor {rise:g} m up (its plan's storey)"}


def seated(plans, outside, folders, stands=None):
    """{place: {"matrix", "from"}} of the outside place and every place its plan holds that has a folder, the joins
    between them and the faults that keep a planned join from being seated. `stands`, when given, is laid in the
    area's frame first, raised only to its plan's storey (the flat, laid in the frame the plans name, 9 m up: 2099
    #161); a place joined to a seated one is
    seated onto it: its floor where the plans' storey heights put it, its doorway on the other's, facing it; when none
    is left joined to a seated one, the lowest left on the plans (the street, under the stairwell) stands where the
    outside's plan holds it (held_seat)."""
    holder = plan.read(pathlib.Path(plans) / f"{outside}.json")
    held, planned, faults = planned_joins(holder, plans, outside)
    levels = plan.levels_of(with_holder(held, outside, holder))
    joins, unbuilt = built_joins(folders, planned)
    faults += unbuilt
    seats = {outside: {"matrix": np.identity(4), "from": f"the area's frame: {outside}'s own"}}
    if stands in folders:
        rise = levels.get(stands, 0.0)
        seats[stands] = {"matrix": seat_matrix(0.0, (0.0, rise, 0.0)),
                         "from": f"given to stand: as laid, its floor {rise:g} m up (its plan's storey)"}
    grown(seats, joins, levels)
    while set(folders) - set(seats):
        lowest = min(set(folders) - set(seats), key=lambda name: (levels.get(name, 0.0), name))
        seats[lowest] = held_seat(holder, held, levels, lowest)
        grown(seats, joins, levels)
    faults += [f"{name}: {outside}'s plan holds it, but no folder is given" for name in sorted(set(held) - set(folders))]
    return seats, joins, faults


# --- the joins check ---------------------------------------------------------------------------------------------

def gaps(seats, ends):
    """How far a join's two doorways stand apart in the area: in height, along the floor, and in degrees off facing."""
    (name, _, spot), (other, _, other_spot) = ends
    here, there = put(seats[name]["matrix"], spot["middle"]), put(seats[other]["matrix"], other_spot["middle"])
    inward = seats[name]["matrix"][:3, :3] @ np.asarray(spot["inward"], float)
    back = seats[other]["matrix"][:3, :3] @ np.asarray(other_spot["inward"], float)
    facing = math.degrees(math.acos(max(-1.0, min(1.0, -float(np.dot(inward, back))))))
    return here, there, inward, back, (abs(float(here[1] - there[1])), float(np.hypot(*(here - there)[[0, 2]])), facing)


def seated_bounds(prim, seat):
    """An object's box in the area: its own box's corners put by the seat."""
    box = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ["default", "render"]).ComputeWorldBound(prim).ComputeAlignedRange()
    if box.IsEmpty():
        return None
    low, high = np.asarray(box.GetMin()), np.asarray(box.GetMax())
    corners = np.array([[x, y, z] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    placed = corners @ seat[:3, :3].T + seat[:3, 3]
    return placed.min(axis=0), placed.max(axis=0)


def joined_stage(folders, seats, places, middle):
    """An in-memory stage /area/Objects holding, seated, every object of `places` whose box in the area comes within
    REACH of `middle`, each place's backdrop (place.json `backdrop`: a neighbour stands for it, its package leaves it
    out) left out as the game leaves it (2099's prologue, 2026-11-24: the stairwell's flat_wall, which the flat stands
    for, walled the flat's join off): each a reference to its own scene's object, its seat the first (outermost) of
    its ops."""
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    root = UsdGeom.Xform.Define(stage, f"/{AREA}")
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.Scope.Define(stage, f"/{AREA}/Objects")
    low, high = np.asarray(middle) - REACH, np.asarray(middle) + REACH
    for name in places:
        source, place = place_build.opened(folders[name])
        path = str(place_build.scene_path(folders[name]).resolve())
        seat = seats[name]["matrix"]
        neighbours = set(place_build.record_of(folders[name]).get("backdrop") or [])
        for prim in source.GetPrimAtPath(f"/{place}/Objects").GetChildren():
            if prim.GetName() in neighbours:
                continue
            bounds = seated_bounds(prim, seat)
            if bounds is None or np.any(bounds[1] < low) or np.any(bounds[0] > high):
                continue
            laid = stage.DefinePrim(f"/{AREA}/Objects/{name}{SEPARATOR}{prim.GetName()}")
            laid.GetReferences().AddReference(Sdf.Reference(path, prim.GetPath()))
            xform = UsdGeom.Xformable(laid)
            own = xform.GetOrderedXformOps()
            outer = xform.AddTransformOp(opSuffix="seat")
            outer.Set(Gf.Matrix4d(seat.T.tolist()))
            xform.SetXformOpOrder([outer, *own], xform.GetResetXformStack())
    return stage


def walked(folders, seats, ends, here, there, inward, back):
    """The length of a walker's way from INSIDE in from one doorway to INSIDE in from the other over the two places'
    objects round the join, seated, every doorway open (as ready's walkway check judges a doorway a way; whether a
    leaf swings open is each place's own check); the refusal's words when there is none."""
    places = sorted({ends[0][0], ends[1][0]})
    stage = joined_stage(folders, seats, places, (here + there) / 2)
    try:
        _, metres = ready.route_on(ready.Place(stage, AREA), [here + inward * INSIDE, there + back * INSIDE], {})
    except place_build.Refused as why:
        return None, str(why)
    return metres, None


def wider(ends):
    """A door leaf of one place wider than the other's doorway it is seated in by more than ready.FIT (the flat's leaf
    in its 1.2 m frame against the stair core's 1.02 m doorway): it cannot stand in it."""
    found = []
    for (name, key, spot), (other, other_key, other_spot) in (ends, ends[::-1]):
        if str(spot.get("from", "")).startswith("the door leaf") and spot["wide"] > other_spot["wide"] + ready.FIT:
            found.append(f"{name}'s {key} is {spot['wide']:.2f} m wide, {other}'s {other_key} it is seated in "
                         f"{other_spot['wide']:.2f} m")
    return found


def judged(folders, seats, ends):
    """One join's record: its places and doorways, how far apart they stand, the way walked through it, its faults."""
    (name, key, _), (other, other_key, _) = ends
    here, there, inward, back, (height, along, facing) = gaps(seats, ends)
    said = f"{name}'s {key} to {other}'s {other_key}"
    faults = []
    if height > LEVEL:
        faults.append(f"{said}: its sill stands at {here[1]:.2f} m in the area, {other}'s at {there[1]:.2f} m "
                      f"({height:.2f} m apart; the floors must meet within {LEVEL:g} m)")
    if along > ALIGN:
        faults.append(f"{said}: the doorways' middles stand {along:.2f} m apart along the floor (within {ALIGN:g} m)")
    if facing > FACING:
        faults.append(f"{said}: the doorways turn {facing:.1f} degrees off facing each other (within {FACING:g})")
    metres, refused = (None, None) if faults else walked(folders, seats, ends, here, there, inward, back)
    faults += wider(ends)
    if refused:
        faults.append(f"{said}: no walker's way through it ({refused})")
    return {"places": [name, other], "doorways": [key, other_key], "height": round(height, 4),
            "along": round(along, 4), "facing": round(facing, 2), "walked": metres, "faults": faults}


# --- the shells check ---------------------------------------------------------------------------------------------

def seated_shells(folder, seat):
    """{object: [its closed solids, seated in the area]} of the place's shell (SHELLS, ready.role_of), its place.json
    `backdrop` (a neighbour place stands for it) left out."""
    stage, place = place_build.opened(folder)
    neighbours = set(place_build.record_of(folder).get("backdrop") or [])
    found = {}
    for prim in stage.GetPrimAtPath(f"/{place}/Objects").GetChildren():
        if prim.GetName() in neighbours or ready.role_of(prim) not in SHELLS:
            continue
        mesh = ready.solid_of(prim)
        if mesh is None or not len(mesh.faces):
            continue
        mesh.apply_transform(seat)
        found[prim.GetName()] = [piece for piece in mesh.split(only_watertight=False) if abs(piece.volume) > 1e-6]
    return found


def crossed(pieces, others):
    """Cubic metres where solids of `pieces` and of `others` stand inside each other: points STEP apart (wider when
    a common box would hold more than POINTS) counted inside both."""
    total = 0.0
    for piece in pieces:
        for other in others:
            low = np.maximum(piece.bounds[0], other.bounds[0])
            high = np.minimum(piece.bounds[1], other.bounds[1])
            if np.any(high <= low):
                continue
            step = max(STEP, float(np.prod(high - low) / POINTS) ** (1 / 3))
            axes = [np.arange(start + step / 2, end, step) for start, end in zip(low, high)]
            if any(not len(axis) for axis in axes):
                continue
            points = np.stack(np.meshgrid(*axes, indexing="ij"), axis=-1).reshape(-1, 3)
            inside = piece.contains(points)
            if inside.any():
                total += int(np.count_nonzero(other.contains(points[inside]))) * step ** 3
    return total


def shells_crossed(folders, seats):
    """A fault for each two seated places' shell objects standing more than CROSSED cubic metres inside each other
    (the 2099 prologue, 2026-11-22: the walker began inside the street's block wall_l1, the flat and the stairwell
    seated within it): one of them is hollowed or left to its neighbour (place.json `backdrop`), never this loosened."""
    shells = {name: seated_shells(folder, seats[name]["matrix"]) for name, folder in sorted(folders.items())}
    faults = []
    names = sorted(shells)
    for number, name in enumerate(names):
        for other in names[number + 1:]:
            for own, pieces in shells[name].items():
                for theirs, others in shells[other].items():
                    if not any(np.all(piece.bounds[0] < other_piece.bounds[1]) and
                               np.all(other_piece.bounds[0] < piece.bounds[1])
                               for piece in pieces for other_piece in others):
                        continue
                    volume = crossed(pieces, others)
                    if volume > CROSSED:
                        faults.append(f"{name}'s {own} and {other}'s {theirs} stand {volume:.1f} m3 inside each "
                                      f"other, seated (shells may cross by {CROSSED:g} m3)")
    return faults


def area(plans, outside, folders, out=None, seat=False, stands=None):
    """The area's seats and its joins and shells checks as one record (written to `out` when given): every place's
    seat (`stands` laid as it is, seated), every planned join judged, every two places' shells crossed, and every
    fault; with `seat`, each place's seat also written
    into its folder's place.json `seat` (the package then lays the place in the area's frame: scene_package.seated).
    A seat carries no exposure: every place keeps its own light and exposure (pieces' docstring, 2099 #161)."""
    seats, joins, faults = seated(plans, outside, folders, stands)
    judged_joins = [judged(folders, seats, ends) for ends in joins]
    faults += shells_crossed(folders, seats)
    record = {"area": outside, "plans": str(plans),
              "seats": {name: {"matrix": np.round(seat["matrix"].T, 6).flatten().tolist(), "from": seat["from"]}
                        for name, seat in sorted(seats.items())},
              "joins": judged_joins,
              "faults": faults + [fault for entry in judged_joins for fault in entry["faults"]],
              "frame": "each seat the place's frame in the area's, USD's row-vector order (glTF's column-major)"}
    if out:
        pathlib.Path(out).write_text(json.dumps(record, indent=1))
    for name, folder in folders.items() if seat else ():
        laid = place_build.record_of(folder)
        laid["seat"] = {"area": outside, **record["seats"][name]}
        place_build.write_record(folder, laid)
    return record
