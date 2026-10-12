"""scene-record@<place>: the place's scene record written by SCORE from its plan (plan@<place>), the inventory, the
made ground's seats (the terrain stage) and the world's sky record, never from the game and never from the old record
(which only the `seed-matched` gate reads). Contract `scene-record` v1 is today's record schema, so tools/usd/scene.py
and builders.py build it unchanged; it lands as record/<place>.json in the output.

    shell        a domed room (a plan with walls and a dome): room_walls, room_deck and dome_roof on the plan's inside
                 grown by BACKING (the shell stands behind the kit's wall panels, which stand on the plan's line), its
                 corners, walls' height, the dome's rise and run, and a doorway cut in each door that leads somewhere
    places       each door's leaves (the plan's `leaves` kit, the inventory's leaf size, shut in the doorway); a door
                 joined to another place's door by a walkway tube (the tube's stage stood from this doorway to that
                 one, stretched along its run); and every other place seated on the same made ground, where its seat
                 stands it in this place's frame (the ball's curve turns it: `rotation`)
    lights       the room's fill at the sky record's height share, reaching the farthest floor corner (the lamps are
                 the kit's: tools/usd/scene.kit_lights lights each inventory lamp row)
    environment  the world body's indoor sky record (data/definitions/sky.json), its haze a box of the room's inside
    views        one from inside each door looking across, one from each of the plan's standing spots to the middle

Every entry's `from` names the plan element, inventory row, seat or world record it was made from.
"""
import json
import math
import pathlib
from typing import NamedTuple

import numpy as np

from score import contracts
from score.stages.scene_record import plan as place_plan
from score.stages.terrain import outside, record as ground_records

REPO = pathlib.Path(__file__).resolve().parents[3]
# The shell's backing stands this far behind the plan's inside line, where the kit's wall panels stand.
BACKING = 0.15
# The deck lies just under the kit's floor plates (0.04 thick, their tops at the floor).
DECK_BELOW = 0.042
SHELL_SURFACE = "roof_steel_paint"
# A view stands this far inside its doorway, and every view sees this wide (degrees).
VIEW_IN = 1.0
VIEW_FOV = 80
AIM_HEIGHT = 1.0
NORMALS = {"north": (0.0, -1.0), "south": (0.0, 1.0), "east": (1.0, 0.0), "west": (-1.0, 0.0)}
# A wall's leaves stand turned about up by this (degrees): north and south walls unturned.
LEAF_YAW = {"north": 0.0, "south": 0.0, "east": 90.0, "west": 90.0}


def files(place):
    """The world files the writer reads: the place's inventory and kit, every plan and kit (joined and seated places),
    the sky record, the place definitions (the eye's height), the tube's record (only its length: the stage a tube
    shows); and for the gates the old record (the seed) and the old stages (the neighbours the openings compose)."""
    return {"inventory": "{data}/inventory/{place}.json", "kits": "{data}/kit", "plans": "{data}/plans",
            "sky": "{data}/definitions/sky.json", "base": "{data}/definitions/base.json", "tube length": "{data}/scene/tube.json",
            "places": "{data}/definitions/place.json", "seed record": "{data}/scene/{place}.json",
            "seeds": "{seeds}/usd-r3"}


def read(path):
    return json.loads(pathlib.Path(path).read_text())


# --- the shell --------------------------------------------------------------------------------------------------

def shell(plan):
    """The domed room's shell entries: walls with the cut doorways, deck and dome."""
    walls = plan["walls"]
    grown = {"wide": round(walls["wide"] + 2 * BACKING, 4), "deep": round(walls["deep"] + 2 * BACKING, 4),
             "corner": round(walls["corner"] + BACKING, 4)}
    cut = [door for door in plan["doors"] if door["cut"]]
    said = (f"plan: inside {walls['wide']} x {walls['deep']} m, corners {walls['corner']} m, backed {BACKING} m "
            f"behind the kit's wall line")
    return [
        {"name": "shell_walls", "builder": "room_walls", **grown, "high": walls["high"], "surface": SHELL_SURFACE,
         "doors": [{"side": door["side"], "wide": door["wide"], "tall": door["tall"]} for door in cut],
         "from": f"{said}; walls {walls['high']} m; doorways cut in " +
                 (", ".join(f"door {door['plan_side']} ({door['what']}, leads {door['leads']})" for door in cut)
                  or "no door")},
        {"name": "shell_deck", "builder": "room_deck", **grown, "height": -DECK_BELOW, "surface": SHELL_SURFACE,
         "from": f"{said}; just under the kit's floor plates"},
        {"name": "shell_roof", "builder": "dome_roof", **grown, "eave": walls["high"], "rise": walls["rise"],
         "run": walls["run"], "surface": SHELL_SURFACE, "layer": 2,
         "from": f"{said}; dome rising {walls['rise']} m over {walls['run']} m (plan words; inventory room layout run)"}]


# --- places -----------------------------------------------------------------------------------------------------

def leaves(plan, door):
    """A door's leaves (the plan's `leaves` kit), shut side by side across its doorway, each the inventory layout's
    leaf wide."""
    leaf = plan.get("leaf") or {}
    wide = float(leaf.get("size", [door["wide"]])[0])
    count = max(1, round(door["wide"] / wide))
    middle = np.asarray(door["middle"], dtype=float)
    along = np.array([abs(NORMALS[door["side"]][1]), 0.0, abs(NORMALS[door["side"]][0])])
    found = []
    for number in range(count):
        offset = (number - (count - 1) / 2) * wide
        found.append({"name": f"{door['side']}_door_leaf_{number + 1}", "stage": door["leaves"],
                      "at": np.round(middle + along * offset, 4).tolist(), "yaw": LEAF_YAW[door["side"]],
                      "door_leaf": door["plan_side"],
                      "from": f"plan door {door['plan_side']} ({door['what']}): leaf {number + 1} of {count}, the "
                              f"inventory room layout's {leaf.get('kit', door['leaves'])} leaf {wide} m wide, shut"})
    return found


class Seat(NamedTuple):
    """Where a place stands: its made ground's name and record, its seat entry, its stage and its laid Ground."""
    ground: str
    made: dict
    entry: dict
    stage: str
    laid: object


def on_seat_of(kits, stage):
    kit = pathlib.Path(kits) / f"{stage}.json"
    return read(kit).get("on_seat", [0.0, 0.0]) if kit.exists() else [0.0, 0.0]


def seats(inputs):
    """Every seated place: the made grounds' own seats (the terrain stage), and the base's modules (data/definitions/
    base.json) on the seat of the module it names: {name: Seat}."""
    found = {}
    for folder in sorted(pathlib.Path(inputs["terrain"]).iterdir()):
        if not (folder / "ground.json").exists():
            continue
        made = ground_records.read(folder)
        for place, entry in made.get("places", {}).items():
            found[place] = Seat(folder.name, made, entry, place,
                                outside.placed_ground(made, entry, on_seat_of(inputs["kits"], place)))
    base = read(inputs["base"])
    on = found[base["seat_of"]]
    for name, module in base["modules"].items():
        entry = {"out": on.entry["out"], "heading": module["heading"], "flat": module["flat"]}
        found[name] = Seat(on.ground, on.made, entry, module["stage"],
                           outside.placed_ground(on.made, entry, on_seat_of(inputs["kits"], module["stage"])))
    return found


def pose_in(laid, other):
    """Another seated place's floor middle and axes (rows: across, up, along) in this place's frame."""
    position = laid.in_place_frame(other.origin + other.frame[1] * other.drop)[0]
    return position, other.frame @ laid.frame.T


def quaternion(axes):
    """A turn (rows: the turned x, y, z axes, row vectors) as [x, y, z, w], as scene.turn reads `rotation`."""
    from pxr import Gf
    quat = Gf.Matrix3d(*np.asarray(axes, dtype=float).ravel().tolist()).ExtractRotation().GetQuat()
    return [round(value, 6) for value in (*quat.GetImaginary(), quat.GetReal())]


def outward(side):
    across, along = NORMALS[side]
    return np.array([across, 0.0, along])


def door_outside(door):
    """A door's middle on the shell's outer face, in its own place's frame."""
    return np.asarray(door["middle"], dtype=float) + outward(door["side"]) * BACKING


def neighbours(place, grounds):
    """Every other place seated on this place's made ground, stood where its seat puts it."""
    if place not in grounds:
        return []
    here = grounds[place]
    found = []
    for other, seat in sorted(grounds.items()):
        if other == place or seat.ground != here.ground:
            continue
        position, axes = pose_in(here.laid, seat.laid)
        found.append({"name": other, "stage": seat.stage, "at": np.round(position, 4).tolist(),
                      "rotation": quaternion(axes),
                      "from": f"the {seat.ground} ground's seats (terrain stage; the base's modules, data/definitions/"
                              f"base.json): {other}'s seat in {place}'s frame"})
    return found


def joined_tube(place, door, plans, grounds, tube_length):
    """The walkway tube joining a door to the joined place's door: the tube's stage stood at this doorway, turned
    along the run to that doorway and stretched to reach it."""
    if place not in grounds or door["joins"] not in grounds:
        raise ValueError(f"{place}: door {door['plan_side']} joins {door['joins']}, but the two are not both seated "
                         "on a made ground")
    laid, other = grounds[place].laid, grounds[door["joins"]].laid
    other_plan = read(pathlib.Path(plans) / f"{door['joins']}.json")
    other_door = next(entry for entry in other_plan["doors"] if entry[0] == door["joins_door"])
    side = place_plan.SIDES[other_door[0]]
    far_local = np.asarray(place_plan.door_middle(other_door[0], other_door[1], other_plan["w"], other_plan["d"]),
                           dtype=float) + outward(side) * BACKING
    position, axes = pose_in(laid, other)
    far = position + far_local @ axes
    near = door_outside(door)
    run = far - near
    along = run / np.linalg.norm(run)
    up = np.array([0.0, 1.0, 0.0]) - along * along[1]
    up /= np.linalg.norm(up)
    turn = np.array([np.cross(up, along), up, along])
    return {"name": f"{door['side']}_tube", "stage": door["leads"], "at": np.round(near, 4).tolist(),
            "rotation": quaternion(turn), "scale": [1.0, 1.0, round(float(np.linalg.norm(run)) / tube_length, 4)],
            "joins": door["joins"],
            "from": f"plan door {door['plan_side']} ({door['what']}) leads {door['leads']} to {door['joins']}'s door "
                    f"{door['joins_door']} (its plan, its seat): {np.linalg.norm(run):.2f} m run, the tube's stage "
                    f"{tube_length} m long stretched to it"}


def places_of(place, plan, inputs):
    """Every place this one shows: door leaves, joined tubes, seated neighbours."""
    grounds = seats(inputs)
    found = []
    for door in plan["doors"]:
        if door["cut"] and door.get("leaves"):
            found += leaves(plan, door)
        if door["cut"] and door["joins"]:
            found.append(joined_tube(place, door, inputs["plans"], grounds, read(inputs["tube length"])["tube_length"]))
    return found + neighbours(place, grounds)


# --- light, sky, views ------------------------------------------------------------------------------------------

def fill(plan, indoor):
    """The room's fill light: at the sky record's height share of the walls, reaching the farthest floor corner."""
    walls, light = plan["walls"], indoor["fill"]
    height = round(walls["high"] * light["height_share"], 4)
    reach = round(math.sqrt((walls["wide"] / 2) ** 2 + (walls["deep"] / 2) ** 2 + height ** 2), 3)
    return {"type": "omni", "at": [0.0, height, 0.0], "colour": light["colour"], "energy": light["energy"],
            "range": reach, "attenuation": light["attenuation"], "shadows": False,
            "from": "sky record (data/definitions/sky.json) indoor fill, at its height share of the plan's walls, "
                    "reaching the plan's farthest floor corner"}


def environment(plan, indoor, body):
    """The body's indoor sky, its haze a box of the plan's inside up to the walls' top."""
    walls = plan["walls"]
    return {"background": indoor["background"], "ambient": dict(indoor["ambient"]), "exposure": indoor["exposure"],
            "inside": True, "from": f"sky record (data/definitions/sky.json) {body} indoor",
            "haze": {"shape": "box", "centre": [0.0, walls["high"] / 2, 0.0],
                     "size": [walls["wide"], walls["high"], walls["deep"]], **indoor["haze"],
                     "from": f"sky record {body} indoor haze, a box of the plan's inside to its walls' top"}}


def views(plan, eye_height):
    """One view inside each door looking across the room, one from each standing spot to the middle."""
    found = []
    for door in plan["doors"]:
        middle = np.asarray(door["middle"], dtype=float)
        eye = middle - outward(door["side"]) * VIEW_IN
        aim = -middle
        found.append({"name": f"from-{door['side']}-door", "eye": [round(eye[0], 3), eye_height, round(eye[2], 3)],
                      "aim": [round(aim[0], 3), AIM_HEIGHT, round(aim[2], 3)], "fov": VIEW_FOV,
                      "from": f"plan door {door['plan_side']} ({door['what']}), looking across"})
    for number, (x, z) in enumerate(plan["standing"], 1):
        found.append({"name": f"spot-{number}", "eye": [round(x, 3), eye_height, round(z, 3)],
                      "aim": [0.0, AIM_HEIGHT, 0.0], "fov": VIEW_FOV,
                      "from": f"plan standing spot {number}, looking to the middle"})
    return found


# --- the record -------------------------------------------------------------------------------------------------

def record_of(place, plan, inputs):
    """The place's scene record from its plan and the world's records (module docstring)."""
    if not plan["inside"] or not plan["walls"].get("rise"):
        raise NotImplementedError(f"{place}: the writer makes domed rooms only so far; its plan is no domed room")
    walls = plan["walls"]
    seated = seats(inputs).get(place)
    if seated is None:
        raise ValueError(f"{place}: no seat on a made ground and no module of the base: its world body is unknown")
    body = seated.ground
    indoor = read(inputs["sky"])[body]["indoor"]
    eye = read(inputs["places"])["shared"]["scale"]["eye_height"]
    return {"place": place,
            "about": f"{plan['title']}, written by SCORE's scene-record stage from its plan (data/plans/{place}.json), "
                     "its inventory, the made ground's seats and the world's sky record. Frame: the room's middle on "
                     "its floor, x east, z south.",
            "floor": [[-walls["wide"] / 2, -walls["deep"] / 2], [walls["wide"] / 2, walls["deep"] / 2]],
            "ceiling": round(walls["high"] + walls["rise"], 4), "inside": True,
            "structure": shell(plan), "lights": [fill(plan, indoor)], "environment": environment(plan, indoor, body),
            "views": views(plan, eye), "places": places_of(place, plan, inputs)}


def make(inputs, out, seed, params):
    """record/<place>.json: the place's scene record."""
    plan = read(pathlib.Path(inputs["plan"]) / "plan.json")
    place = plan["place"]
    (out / "record").mkdir()
    (out / "record" / f"{place}.json").write_text(json.dumps(record_of(place, plan, inputs), indent=1))


def record_faults(folder):
    found = list(pathlib.Path(folder).glob("record/*.json"))
    if len(found) != 1:
        return [f"{len(found)} records in record/, not one"]
    record = json.loads(found[0].read_text())
    return [f"the record lacks {key}" for key in ("place", "floor", "structure", "views") if key not in record]


SCENE_RECORD = contracts.Contract("scene-record", 1, record_faults, {"length": "metre", "up axis": "Y",
                                                                     "angle": "degree"})


def record_in(output):
    """The record an output holds: (place, record)."""
    path = next(pathlib.Path(output).glob("record/*.json"))
    return path.stem, json.loads(path.read_text())
