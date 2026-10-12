"""plan@<place>: the place's dimensioned plan (data/plans/<place>.json) brought into the store in metres and the
place's own frame (contract `place-plan` v1), beside what its concept was read into.

    walls     the room's inside wide and deep, its corners' radius, its walls' height and its dome's rise (read off the
              plan's words) and run (the inventory's room layout, which the plan does not draw)
    doors     each plan door: its side, its middle in the place's frame, its wide and tall, what it is, and where it
              leads (the plan's `leads`: a place, `outside` or `sealed`, with why), cut or shut
    items     each plan item's box in the place's frame, its facing and kind, and the inventory rows that make it
    zones     the plan's keep-clear zones; standing: the plan's people spots; elements: the concept's elements

The plan's own frame is metres from its north-west corner (x east, y south); the place's is the room's middle on its
floor (x east, z south), as every kit and inventory of world 1 is laid.

Gate `mapped`: every plan item names inventory rows that exist (a zone names none), every concept element names
rows that exist, a plan door, or its drop, every door says where it leads and why, and a sealed door is one the
inventory's room layout shuts with a leaf. How far a row's laid spot lies from its item's box is
measured and shown, never judged here: the layout is the inventory's.
"""
import json
import pathlib
import re

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
SIDES = {"N": "north", "S": "south", "E": "east", "W": "west"}
LEADS = ("outside", "sealed")
# A row's laid spot this far outside its item's box is shown as off the plan (metres).
SPOT_MARGIN = 0.6
WALLS = re.compile(r"walls (\d+(?:\.\d+)?) m")
RISE = re.compile(r"rising (?:about )?(\d+(?:\.\d+)?) m")
SIZE = re.compile(r"(\d+(?:\.\d+)?) x (\d+(?:\.\d+)?) m")


def files(place):
    """The plan, the place's inventory and kit, every plan (a door leads to another place's door) and the concept's
    picture the plan names."""
    plan = json.loads((REPO / "data/plans" / f"{place}.json").read_text())
    found = {"plan": "{data}/plans/{place}.json", "plans": "{data}/plans", "inventory": "{data}/inventory/{place}.json",
             "kit": "{data}/kit/{place}.json"}
    if plan.get("concept", {}).get("picture"):
        found["concept"] = plan["concept"]["picture"]
    return found


def read(path):
    return json.loads(pathlib.Path(path).read_text())


def heights(plan, layout):
    """The walls' height and the dome's rise from the plan's words, its run from the inventory's room layout."""
    walls, rise = WALLS.search(plan["height"]), RISE.search(plan["height"])
    if walls is None:
        raise ValueError(f"{plan['title']}: the plan's height names no walls' height ({plan['height']!r})")
    return {"high": float(walls.group(1)), "rise": float(rise.group(1)) if rise else 0.0,
            "run": float(layout.get("run", 0.0))}


def door_middle(side, at, wide, deep):
    """A plan door's middle on the floor in the place's frame (`at` is metres along its wall from the plan's
    north-west corner)."""
    return {"N": [at - wide / 2, 0.0, -deep / 2], "S": [at - wide / 2, 0.0, deep / 2],
            "W": [-wide / 2, 0.0, at - deep / 2], "E": [wide / 2, 0.0, at - deep / 2]}[side]


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
    for side, at, wide, what in plan["doors"]:
        lead = plan.get("leads", {}).get(side, {})
        sized = SIZE.search(what)
        kind = layout.get("doors", {}).get(SIDES[side])
        tall = float(sized.group(2)) if sized else leaf_tall(inventory, kind) if kind else None
        found.append({"side": SIDES[side], "plan_side": side, "middle": door_middle(side, at, plan["w"], plan["d"]),
                      "at": at, "wide": float(wide), "tall": tall, "what": what, "leads": lead.get("to"),
                      "joins": lead.get("joins"), "joins_door": lead.get("door"), "leaves": lead.get("leaves"),
                      "why": lead.get("why"), "cut": lead.get("to") not in (None, "sealed")})
    return found


def items_of(plan):
    """Each plan item: its box (x0, z0, x1, z1) in the place's frame, its facing, kind and rows."""
    half = (plan["w"] / 2, plan["d"] / 2)
    rows = plan.get("rows", {})
    return [{"name": name, "box": [x - half[0], y - half[1], x + wide - half[0], y + deep - half[1]],
             "facing": facing, "kind": kind, "rows": rows.get(name)}
            for name, x, y, wide, deep, facing, kind in plan["items"]]


def make(inputs, out, seed, params):
    """plan.json: the plan in the place's frame, with its doors' leads, its items' rows and the concept's elements."""
    plan, inventory = read(inputs["plan"]), read(inputs["inventory"])
    layout = inventory.get("room", {}).get("layout", {})
    record = {"place": inventory["place"], "title": plan["title"], "inside": bool(layout.get("wall")),
              "walls": {"wide": float(plan["w"]), "deep": float(plan["d"]), "corner": float(plan["corner"]),
                        **heights(plan, layout)},
              "doors": doors_of(plan, inventory), "items": items_of(plan),
              "standing": [[x - plan["w"] / 2, y - plan["d"] / 2] for x, y in plan.get("people", [])],
              "elements": plan.get("elements", []), "concept": plan.get("concept", {}), "notes": plan.get("notes", []),
              "open": layout.get("open", []), "big_door": layout.get("big_door"), "leaf": layout.get("leaf")}
    (out / "plan.json").write_text(json.dumps(record, indent=1))


def plan_faults(folder):
    path = pathlib.Path(folder) / "plan.json"
    if not path.exists():
        return ["no plan.json"]
    record = json.loads(path.read_text())
    return [f"plan.json lacks {key}" for key in ("place", "walls", "doors", "items", "standing") if key not in record]


PLACE_PLAN = contracts.Contract("place-plan", 1, plan_faults, {"length": "metre", "up axis": "Y"})


# --- the gate ---------------------------------------------------------------------------------------------------

def row_spots(inventory):
    """Each inventory row's laid spots (x, z) in the place's frame; rows laid along a wall or by the kit have none."""
    return {row["id"]: [(spot["x"], spot["z"]) for spot in row.get("at", []) if "x" in spot]
            for row in inventory["rows"]}


def item_faults(item, ids):
    """Why a plan item is not mapped: no rows named, or a row the inventory lacks."""
    if item["rows"] is None:
        return [f"plan item {item['name']!r} names no inventory rows and no drop"]
    if not item["rows"] and item["kind"] != "zone":
        return [f"plan item {item['name']!r} names no rows (only a zone may)"]
    return [f"plan item {item['name']!r}: row {row} is not in the inventory" for row in item["rows"] if row not in ids]


def element_faults(element, ids, doors):
    """Why a concept element is not mapped: no rows, door or drop; a row the inventory lacks; a door the plan lacks."""
    if not element.get("rows") and not element.get("door") and not element.get("drop"):
        return [f"concept element {element['element']!r} names no rows, door or drop"]
    found = [f"concept element {element['element']!r}: row {row} is not in the inventory"
             for row in element.get("rows", []) if row not in ids]
    if element.get("door") and element["door"] not in doors:
        found.append(f"concept element {element['element']!r}: door {element['door']} is not on the plan")
    return found


def door_faults(door, places, record):
    """Why a door's lead is not said: none, no why, a place the world lacks, a sealed door the layout leaves open, or a
    cut door with no height. A cut door may hold a leaf: it opens (a motion), and the doorway leads on."""
    name = f"door {door['plan_side']} ({door['what']})"
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


def off_plan(record, inventory):
    """Each mapped row's laid spot farther than SPOT_MARGIN outside the nearest item naming it: shown, not judged."""
    spots, found = row_spots(inventory), []
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
    doors = {door["plan_side"] for door in record["doors"]}
    faults = [fault for item in record["items"] for fault in item_faults(item, ids)]
    if not record["elements"]:
        faults.append("the plan holds no concept elements")
    faults += [fault for element in record["elements"] for fault in element_faults(element, ids, doors)]
    faults += [fault for door in record["doors"] for fault in door_faults(door, places, record)]
    shown = off_plan(record, inventory)
    reason = "; ".join(faults[:3]) + (f" and {len(faults) - 3} more" if len(faults) > 3 else "") if faults else \
        (f"every plan item, concept element and door is mapped ({len(record['items'])} items, "
         f"{len(record['elements'])} elements, {len(record['doors'])} doors)")
    return checks.Verdict("mapped", checks.FAIL if faults else checks.PASS, reason,
                          {"faults": len(faults), "rows off their item": len(shown)}, {"faults": "lower"},
                          tuple(faults + [f"shown, not judged: {line}" for line in shown]))


CHECKS = (checks.Check("mapped", judge_mapped),)
