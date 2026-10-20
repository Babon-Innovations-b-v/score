"""The shell split's gates, each read from the output's split.json and the shell's plan, never from the split's own
code, so a fault in the cut is caught here.

    tiled     every lane of the inside's span (left, middle, right) is covered front to back by exactly one shape at a
              time: no overlap, no gap, nothing past the span
    reached   every inside place is reached from the first through doors, each door on a wall the two shapes share
              and answered by a door back
    bounded   every room's length is within the plan's least and most, its narrowest width and its clear height at
              least the plan's least, and long enough for its door
"""
import json
import pathlib

from score import checks

EPSILON = 0.002  # metres: two lengths written to the millimetre are the same within this


def read_split(output):
    return json.loads((pathlib.Path(output) / "split.json").read_text())


def read_plan(inputs):
    return json.loads(pathlib.Path(inputs["shell plan"]).read_text())["split"]


def verdict(name, faults, passed, measures):
    """A gate's verdict: fail with its faults, else pass with `passed` as its reason."""
    return checks.Verdict(name, checks.FAIL if faults else checks.PASS, "; ".join(faults[:3]) or passed,
                          {**measures, "faults": len(faults)}, {"faults": "lower"}, tuple(faults))


def lane_faults(layout, lane):
    """Where one lane's shapes overlap, leave a gap or pass the span, front to back."""
    front, back = layout["span"]
    spans = sorted([tuple(item["along"]) for item in layout["places"] if lane in item["lanes"]]
                   + [tuple(item["hall"]) for item in layout["places"] if "hall" in item and lane != "middle"])
    faults, along = [], front
    for start, end in spans:
        if start < along - EPSILON:
            faults.append(f"{lane}: shapes overlap from {start} to {min(along, end)} m")
        elif start > along + EPSILON:
            faults.append(f"{lane}: nothing stands from {along} to {start} m")
        along = max(along, end)
    if along > back + EPSILON:
        faults.append(f"{lane}: a shape stands past the inside's end, {along} m over {back} m")
    return faults


def judge_tiled(output, inputs, evidence):
    """Every lane covered once, front to back (module docstring)."""
    layout = read_split(output)
    faults = [fault for lane in ("left", "middle", "right") for fault in lane_faults(layout, lane)]
    return verdict("tiled", faults, f"{len(layout['places'])} shapes tile the inside, no overlap",
                   {"shapes": len(layout["places"])})


def shared_wall(first, second, at):
    """Whether two shapes meet at `along`: side by side over it, or one's end the other's start there."""
    over = all(item["along"][0] - EPSILON <= at <= item["along"][1] + EPSILON for item in (first, second))
    touch = bool(set(first["lanes"]) & set(second["lanes"])) or {first["side"], second["side"]} & {"middle"}
    return over and bool(touch)


def door_faults(layout):
    """Doors that lead to no shape of the split, stand on no wall the two shapes share, or have no door back."""
    by_place, faults = {item["place"]: item for item in layout["places"]}, []
    for item in layout["places"]:
        for door in item["doors"]:
            other = by_place.get(door["leads"])
            if other is None:
                faults.append(f"{item['place']}: a door leads to {door['leads']}, no shape of the split")
            elif not shared_wall(item, other, door["along"]):
                faults.append(f"{item['place']}: its door at {door['along']} m is on no wall it shares with "
                              f"{door['leads']}")
            elif not any(back["leads"] == item["place"] and abs(back["along"] - door["along"]) <= EPSILON
                         for back in other["doors"]):
                faults.append(f"{item['place']}: its door to {door['leads']} has no door back")
    return faults


def reachable(layout):
    """The places reached from the first through doors."""
    by_place = {item["place"]: item for item in layout["places"]}
    seen, todo = set(), [layout["places"][0]["place"]] if layout["places"] else []
    while todo:
        place = todo.pop()
        if place in seen or place not in by_place:
            continue
        seen.add(place)
        todo += [door["leads"] for door in by_place[place]["doors"]]
    return seen


def judge_reached(output, inputs, evidence):
    """Every inside place reached through doors that stand on shared walls (module docstring)."""
    layout = read_split(output)
    seen = reachable(layout)
    faults = door_faults(layout) + [f"{item['place']}: no way in through the doors" for item in layout["places"]
                                    if item["place"] not in seen]
    return verdict("reached", faults, f"every one of {len(layout['places'])} shapes reached through its doors",
                   {"reached": len(seen), "shapes": len(layout["places"])})


def room_faults(item, room, least, door_wide):
    """Where one room passes its plan's bounds."""
    low, high = room["long"]
    faults = []
    if not low - EPSILON <= item["long"] <= high + EPSILON:
        faults.append(f"{item['place']}: {item['long']} m long, outside its plan's {low} to {high} m")
    if item["narrowest"] < least["wide"] - EPSILON:
        faults.append(f"{item['place']}: {item['narrowest']} m wide at its narrowest, under the least {least['wide']} m")
    if item["clear"] < least["clear"] - EPSILON:
        faults.append(f"{item['place']}: {item['clear']} m clear, under the least {least['clear']} m")
    if item["long"] < door_wide - EPSILON:
        faults.append(f"{item['place']}: {item['long']} m long, under its door's {door_wide} m")
    return faults


def judge_bounded(output, inputs, evidence):
    """Every room within its plan's bounds, and every room of the plan laid (module docstring)."""
    layout, plan = read_split(output), read_plan(inputs)
    by_place = {item["place"]: item for item in layout["places"]}
    faults = [f"{room['place']}: in the plan's room list, not in the split" for room in plan["rooms"]
              if room["place"] not in by_place]
    faults += [fault for room in plan["rooms"] if room["place"] in by_place
               for fault in room_faults(by_place[room["place"]], room, plan["least"], plan["door"]["wide"])]
    return verdict("bounded", faults, f"every one of {len(plan['rooms'])} rooms within its plan's bounds",
                   {"rooms": len(plan["rooms"])})


CHECKS = (checks.Check("tiled", judge_tiled), checks.Check("reached", judge_reached),
          checks.Check("bounded", judge_bounded))
