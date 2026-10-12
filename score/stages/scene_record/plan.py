"""plan@<place>: the place's dimensioned plan (data/plans/<place>.json) brought into the store in metres and the
place's own frame (contract `place-plan` v2: v1 had no shell, frame, block, levels or shows), beside what its concept was read into.

    shell     what holds the place's walls (the plan's `shell`): `domed` (the record's room_walls, deck and dome; the
              default) or `kit` (the kit's own pieces are the walls and floors: the Earth's rooms and open places)
    walls     the room's inside wide and deep, its corners' radius, its walls' height and its dome's rise (read off the
              plan's words) and run (the inventory's room layout, which the plan does not draw); a kit shell's ceiling
              and floor to floor (its storey) from the plan's words
    floor     the plan's inside as the place frame's box round it, and its floor's height
    block     the building a kit room stands in (the plan's `block`, in the place's frame), else None
    doors     each plan door: its side, its middle in the place's frame (on its sill: a door's fifth number is the
              sill's level), its wall's outward normal, its wide and tall, what it is, and where it leads (the plan's
              `leads`, by side or by `<side>@<level>`: a place, `outside` or `sealed`, with why), cut or shut
    items     each plan item's box in the place's frame, its facing and kind, and the inventory rows that make it
    zones     the plan's keep-clear zones; standing: the plan's people spots (a third number their level, a fourth the
              plan item they look at); elements: the concept's elements; shows: the places seen from it that no
              made ground seats (the far city), each with why; objects: the plan items a released world model
              makes; aims: where a spot lamp row aims (a plan item)

The plan's own frame is metres from its north-west corner (x east, y south). The place's frame is its kit's: a domed
room's middle on its floor (x east, z south); a plan with a `frame` stands where its `anchor` says (a plan point and
the place point it is), turned so its `toward` plan point falls the way of its place point (the Earth's places share
one frame, the street's; the square's and the launch's plans are drawn down the balcony's view).

Gate `mapped`: every plan item names inventory rows that exist (a zone names none, nor an item a released model
makes: its model must be in the world's release, data/assets/world1.json), every concept element names rows that
exist, a plan door, a plan object or its drop, every door says where it leads and why, and a sealed door is one the
inventory's room layout shuts with a leaf. How far a row's laid spot (the inventory's, else the kit's pieces of it)
lies from its item's box is measured and shown, never judged here: the layout is the inventory's.
"""
import json
import math
import pathlib
import re

import numpy as np

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
SIDES = {"N": "north", "S": "south", "E": "east", "W": "west"}
LEADS = ("outside", "sealed")
SHELLS = ("domed", "kit")
# A row's laid spot this far outside its item's box is shown as off the plan (metres).
SPOT_MARGIN = 0.6
WALLS = re.compile(r"walls (\d+(?:\.\d+)?) m")
RISE = re.compile(r"rising (?:about )?(\d+(?:\.\d+)?) m")
SIZE = re.compile(r"(\d+(?:\.\d+)?) x (\d+(?:\.\d+)?) m")
CEILING = re.compile(r"ceiling (\d+(?:\.\d+)?) m")
STOREY = re.compile(r"floor to floor (\d+(?:\.\d+)?) m")


def inventory_name(place):
    """The place's inventory's name: the plan's `inventory` (the prologue's rooms keep theirs as prologue_<place>),
    else the place's own."""
    return json.loads((REPO / "data/plans" / f"{place}.json").read_text()).get("inventory", place)


def files(place):
    """The plan, the place's inventory and kit, every plan (a door leads to another place's door) and the concept's
    picture the plan names."""
    plan = json.loads((REPO / "data/plans" / f"{place}.json").read_text())
    found = {"plan": "{data}/plans/{place}.json", "plans": "{data}/plans",
             "inventory": f"{{data}}/inventory/{inventory_name(place)}.json", "kit": "{data}/kit/{place}.json",
             "assets": "{data}/assets/world1.json"}
    if plan.get("concept", {}).get("picture"):
        found["concept"] = plan["concept"]["picture"]
    return found


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def heights(plan, layout):
    """The walls' height and the dome's rise from the plan's words, its run from the inventory's room layout; a kit
    shell's ceiling and floor to floor from its words (none named: 0, an open place)."""
    if plan.get("shell") == "kit":
        ceiling, storey = CEILING.search(plan["height"]), STOREY.search(plan["height"])
        return {"high": float(ceiling.group(1)) if ceiling else 0.0, "storey": float(storey.group(1)) if storey else 0.0,
                "rise": 0.0, "run": 0.0}
    walls, rise = WALLS.search(plan["height"]), RISE.search(plan["height"])
    if walls is None:
        raise ValueError(f"{plan['title']}: the plan's height names no walls' height ({plan['height']!r})")
    return {"high": float(walls.group(1)), "rise": float(rise.group(1)) if rise else 0.0,
            "run": float(layout.get("run", 0.0))}


def frame_of(plan):
    """The plan's frame in the place's: its north-west corner on its floor, and its east and south as place vectors.
    No `frame`: a domed room's middle on its floor, unturned."""
    frame = plan.get("frame")
    if frame is None:
        return np.array([-plan["w"] / 2, 0.0, -plan["d"] / 2]), np.array([1.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0])
    turn = 0.0
    if frame.get("toward"):
        plan_way = np.subtract(frame["toward"]["plan"], frame["anchor"]["plan"])
        place_way = np.subtract(np.asarray(frame["toward"]["place"])[[0, 2]],
                                np.asarray(frame["anchor"]["place"])[[0, 2]])
        turn = math.atan2(place_way[1], place_way[0]) - math.atan2(plan_way[1], plan_way[0])
    east = np.array([math.cos(turn), 0.0, math.sin(turn)])
    south = np.array([-math.sin(turn), 0.0, math.cos(turn)])
    anchor_x, anchor_y = frame["anchor"]["plan"]
    return np.asarray(frame["anchor"]["place"], dtype=float) - east * anchor_x - south * anchor_y, east, south


def placed(plan, x, y, level=0.0):
    """A plan point (metres from its north-west corner, x east, y south), `level` metres up, in the place's frame."""
    corner, east, south = frame_of(plan)
    return np.round(corner + east * x + south * y + np.array([0.0, level, 0.0]), 4)


def door_middle(plan, side, at, level=0.0):
    """A plan door's middle on its sill in the place's frame (`at` is metres along its wall from the plan's
    north-west corner)."""
    x, y = {"N": (at, 0.0), "S": (at, plan["d"]), "W": (0.0, at), "E": (plan["w"], at)}[side]
    return placed(plan, x, y, level).tolist()


def outward(plan, side):
    """A plan wall's outward normal in the place's frame."""
    _, east, south = frame_of(plan)
    return np.round({"N": -south, "S": south, "E": east, "W": -east}[side], 6).tolist()


def lead_of(plan, side, level):
    """A door's lead: the plan's `leads` by `<side>@<level>` (a wall with doors at several levels), else by side."""
    leads = plan.get("leads", {})
    return leads.get(f"{side}@{level:g}", leads.get(side, {}))


def leaf_tall(inventory, kind):
    """A door's height from the leaf that shuts it: the inventory row `<kind>_leaf` (its size's third, up)."""
    for row in inventory["rows"]:
        if row["id"] == f"{kind}_leaf":
            return float(row["size"][2])
    return None


def doors_of(plan, inventory):
    """Each plan door in the place's frame, with where it leads (plan `leads`) and whether it is cut (it leads to a
    place or outside) or shut."""
    layout = inventory.get("room", {}).get("layout", {})
    found = []
    for side, at, wide, what, *level in plan["doors"]:
        level = float(level[0]) if level else 0.0
        lead = lead_of(plan, side, level)
        sized = SIZE.search(what)
        kind = layout.get("doors", {}).get(SIDES[side])
        tall = float(sized.group(2)) if sized else leaf_tall(inventory, kind) if kind else None
        found.append({"side": SIDES[side], "plan_side": side, "name": f"{side}@{level:g}" if level else side,
                      "middle": door_middle(plan, side, at, level), "normal": outward(plan, side), "level": level,
                      "at": at, "wide": float(wide), "tall": tall, "what": what, "leads": lead.get("to"),
                      "joins": lead.get("joins"), "joins_door": lead.get("door"), "leaves": lead.get("leaves"),
                      "why": lead.get("why"), "cut": lead.get("to") not in (None, "sealed")})
    return found


def box_of(plan, x, y, wide, deep):
    """A plan box (x, y, wide, deep) as the place frame's box round it: x0, z0, x1, z1."""
    corners = np.array([placed(plan, x + across, y + along) for across in (0.0, wide) for along in (0.0, deep)])
    return [*corners[:, [0, 2]].min(axis=0).round(4).tolist(), *corners[:, [0, 2]].max(axis=0).round(4).tolist()]


def items_of(plan):
    """Each plan item: its box (x0, z0, x1, z1) in the place's frame, its facing, kind and rows."""
    rows = plan.get("rows", {})
    return [{"name": name, "box": box_of(plan, x, y, wide, deep), "facing": facing, "kind": kind,
             "rows": rows.get(name)}
            for name, x, y, wide, deep, facing, kind in plan["items"]]


def standing_of(plan):
    """Each people spot in the place's frame: [x, z], its level and the plan item it looks at (None: the middle)."""
    found = []
    for x, y, *rest in plan.get("people", []):
        spot = placed(plan, x, y, float(rest[0]) if rest else 0.0)
        found.append({"at": [float(spot[0]), float(spot[2])], "level": float(spot[1]),
                      "looks_at": rest[1] if len(rest) > 1 else None})
    return found


def floor_of(plan):
    """The plan's inside as the place frame's box round it, [[x0, z0], [x1, z1]], and its floor's height."""
    box = box_of(plan, 0.0, 0.0, plan["w"], plan["d"])
    return [box[:2], box[2:]], float(frame_of(plan)[0][1])


def make(inputs, out, seed, params):
    """plan.json: the plan in the place's frame, with its doors' leads, its items' rows and the concept's elements."""
    plan, inventory = read(inputs["plan"]), read(inputs["inventory"])
    layout = inventory.get("room", {}).get("layout", {})
    shell = plan.get("shell", "domed")
    if shell not in SHELLS:
        raise ValueError(f"{plan['title']}: shell {shell!r} is none of {SHELLS}")
    floor, floor_height = floor_of(plan)
    record = {"place": pathlib.Path(inputs["kit"]).stem, "title": plan["title"], "shell": shell,
              "inside": bool(layout.get("wall")) if shell == "domed" else bool(plan.get("inside")),
              "walls": {"wide": float(plan["w"]), "deep": float(plan["d"]), "corner": float(plan["corner"]),
                        **heights(plan, layout)},
              "floor": floor, "floor_height": floor_height, "block": plan.get("block"),
              "doors": doors_of(plan, inventory), "items": items_of(plan), "standing": standing_of(plan),
              "elements": plan.get("elements", []), "shows": plan.get("shows", {}), "objects": plan.get("objects", {}),
              "aims": plan.get("aims", {}),
              "concept": plan.get("concept", {}), "notes": plan.get("notes", []),
              "open": layout.get("open", []), "big_door": layout.get("big_door"), "leaf": layout.get("leaf")}
    (out / "plan.json").write_text(json.dumps(record, indent=1))


def plan_faults(folder):
    path = pathlib.Path(folder) / "plan.json"
    if not path.exists():
        return ["no plan.json"]
    record = json.loads(path.read_text())
    return [f"plan.json lacks {key}" for key in ("place", "walls", "doors", "items", "standing") if key not in record]


PLACE_PLAN = contracts.Contract("place-plan", 2, plan_faults, {"length": "metre", "up axis": "Y"})


# --- the gate ---------------------------------------------------------------------------------------------------

def row_spots(inventory, kit):
    """Each inventory row's laid spots (x, z) in the place's frame: the inventory's own, else the kit's pieces of it
    (a kind `<room>_<row>`, its parts left out); a row laid along a wall has none."""
    laid = {}
    for piece in kit.get("pieces", []):
        if "part" not in piece:
            laid.setdefault(piece["kind"], []).append((piece["at"][0], piece["at"][2]))
    return {row["id"]: [(spot["x"], spot["z"]) for spot in row.get("at", []) if "x" in spot]
            or laid.get(f"{kit.get('room')}_{row['id']}", []) for row in inventory["rows"]}


def item_faults(item, ids, made, released):
    """Why a plan item is not mapped: no rows named and no released model making it (`made`, the plan's object), a
    row the inventory lacks, or a model the world's release lacks."""
    found = []
    if made is not None and made["model"] not in released:
        found.append(f"plan item {item['name']!r}: model {made['model']} is not in the world's release")
    if item["rows"] is None and made is None:
        return found + [f"plan item {item['name']!r} names no inventory rows and no drop"]
    if not item["rows"] and item["kind"] != "zone" and made is None:
        return found + [f"plan item {item['name']!r} names no rows (only a zone, or an item a released model makes, "
                        "may)"]
    return found + [f"plan item {item['name']!r}: row {row} is not in the inventory"
                    for row in item["rows"] or [] if row not in ids]


def element_faults(element, ids, doors, made):
    """Why a concept element is not mapped: no rows, door, object or drop; a row the inventory lacks; a door the plan
    lacks; an object (a plan item a released model makes) the plan lacks."""
    if not any(element.get(key) for key in ("rows", "door", "object", "drop")):
        return [f"concept element {element['element']!r} names no rows, door, object or drop"]
    if element.get("object") and element["object"] not in made:
        return [f"concept element {element['element']!r}: object {element['object']!r} is no plan object"]
    found = [f"concept element {element['element']!r}: row {row} is not in the inventory"
             for row in element.get("rows", []) if row not in ids]
    if element.get("door") and element["door"] not in doors:
        found.append(f"concept element {element['element']!r}: door {element['door']} is not on the plan")
    return found


def door_faults(door, places, record):
    """Why a door's lead is not said: none, no why, a place the world lacks, a sealed door the layout leaves open, or a
    cut door with no height. A cut door may hold a leaf: it opens (a motion), and the doorway leads on."""
    name = f"door {door['name']} ({door['what']})"
    if not door["leads"] or not door["why"]:
        return [f"{name} says nowhere it leads, or not why"]
    found = []
    if door["leads"] not in LEADS and door["leads"] not in places:
        found.append(f"{name} leads to {door['leads']}, which is no place of the world")
    if door["joins"] and door["joins"] not in places:
        found.append(f"{name} joins {door['joins']}, which is no place of the world")
    is_big = (record.get("big_door") or {}).get("wall") == door["side"]
    if not door["cut"] and (is_big or door["side"] in record["open"]):
        found.append(f"{name} is sealed but the room layout leaves it open (no leaf shuts it)")
    if door["cut"] and door["tall"] is None:
        found.append(f"{name} has no height: neither its words nor a leaf row give one")
    return found


def off_plan(record, inventory, kit):
    """Each mapped row's laid spot farther than SPOT_MARGIN outside the nearest item naming it: shown, not judged."""
    spots, found = row_spots(inventory, kit), []
    boxes = {}
    for item in record["items"]:
        for row in item["rows"] or []:
            boxes.setdefault(row, []).append(item)
    for row, items in boxes.items():
        for x, z in spots.get(row, []):
            gap, item = min((max(low_x - x, x - high_x, low_z - z, z - high_z, 0.0), item["name"])
                            for item in items for low_x, low_z, high_x, high_z in [item["box"]])
            if gap > SPOT_MARGIN:
                found.append(f"{row} at ({x:.2f}, {z:.2f}) lies {gap:.2f} m off plan item {item!r}")
    return found


def judge_mapped(output, inputs, evidence):
    """Fail on a plan item, concept element or door that is not mapped (module docstring)."""
    record = read(pathlib.Path(output) / "plan.json")
    inventory = read(inputs["inventory"])
    ids = {row["id"] for row in inventory["rows"]}
    places = {path.stem for path in (REPO / "data/kit").glob("*.json")} | \
        {path.stem for path in pathlib.Path(inputs["plans"]).glob("*.json")}
    doors = {door["plan_side"] for door in record["doors"]} | {door["name"] for door in record["doors"]}
    released = read(inputs["assets"])["files"]
    faults = [fault for item in record["items"]
              for fault in item_faults(item, ids, record["objects"].get(item["name"]), released)]
    if not record["elements"]:
        faults.append("the plan holds no concept elements")
    faults += [fault for element in record["elements"]
               for fault in element_faults(element, ids, doors, record["objects"])]
    faults += [fault for door in record["doors"] for fault in door_faults(door, places, record)]
    shown = off_plan(record, inventory, read(inputs["kit"]))
    reason = "; ".join(faults[:3]) + (f" and {len(faults) - 3} more" if len(faults) > 3 else "") if faults else \
        (f"every plan item, concept element and door is mapped ({len(record['items'])} items, "
         f"{len(record['elements'])} elements, {len(record['doors'])} doors)")
    return checks.Verdict("mapped", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "rows off their item": len(shown)}, {"faults": "lower"},
                          tuple(faults + [f"shown, not judged: {line}" for line in shown]))


CHECKS = (checks.Check("mapped", judge_mapped),)
