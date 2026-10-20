"""scene-record@<place>: the place's scene record written by SCORE from its plan (plan@<place>), the inventory, the
made ground's seats (the terrain stage) and the world's sky record, never from the game and never from the old record
(which only the `seed-matched` gate reads). Contract `scene-record` v1 is today's record schema, so tools/usd/scene.py
and builders.py build it unchanged; it lands as record/<place>.json in the output.

    shell        a domed room (plan shell `domed`): room_walls, room_deck and dome_roof on the plan's inside grown by
                 BACKING (the shell stands behind the kit's wall panels, which stand on the plan's line), its corners,
                 walls' height, the dome's rise and run, and a doorway cut in each door that leads somewhere; a place
                 whose kit holds its walls (plan shell `kit`: the Earth's) gets its block, lamps, night sky, moon,
                 water and objects from kit_shell.py instead; a domed plan's `shape` makes a faceted room's shell
                 (facet_shell), a walkway tube's (tube_shell) or a flat-roofed room's (flat_shell: the hangar's roof
                 slabs round its door opening), its layout's glass_dome a glass dome; a sloped item outside is a plate
                 (ramps), a plot soil in a curb (plots)
    objects      each inventory row the kit does not lay, at its own spots: the route made it (the hub's furniture) or
                 it names a library model (the airlock's suit); and each door leaf a plan lead names (`leaf`),
                 shut in its doorway (the airlock's outer door, which its cycle moves and copies for the inner door);
                 every object whose model the kit lists with `children` carries them (kit_children: the cases on the
                 camp's stores rack, the hub console's screens), each with its glow parts, its row the inventory's
    places       each door's leaves (the plan's `leaves` kit, the inventory's leaf size, shut in the doorway), a flat
                 roof's leaves (the layout's leaf that lies on the roof, shut over its opening); a door
                 joined to another place's door by a walkway tube (the tube's stage stood from this doorway to that
                 one, stretched along its run); and every other place seated on the same made ground, where its seat
                 stands it in this place's frame (the ball's curve turns it: `rotation`)
    lights       the room's fill at the sky record's height share, reaching the farthest floor corner (the lamps are
                 the kit's: tools/usd/scene.kit_lights lights each inventory lamp row)
    environment  the world body's indoor sky record (data/definitions/sky.json), its haze a box of the room's inside
    views        one from inside each door looking across, one from each of the plan's standing spots to the middle

Every entry's `from` names the plan element, inventory row, seat or world record it was made from. An outdoor place
(plan shell `outdoor`) has its own shell writer, outdoor.py.
"""
import json
import math
import pathlib
import re
from typing import NamedTuple

import numpy as np

from score import contracts
from score.stages.scene_record import kit_shell, plan as place_plan
from score.stages.terrain import outside, record as ground_records

REPO = pathlib.Path(__file__).resolve().parents[3]
# The shell's backing stands this far behind the plan's inside line, where the kit's wall panels stand.
BACKING = 0.15
# The deck lies just under the kit's floor plates (0.04 thick, their tops at the floor).
DECK_BELOW = 0.042
SHELL_SURFACE = "roof_steel_paint"
# A faceted room's roof and deck reach this far past its walls, over and under them.
ROOF_OVER = 0.1
# A walkway tube's hull stands this far outside its plan radius (the kit's hoops), its deck plate this thick.
TUBE_BACKING = 0.02
TUBE_DECK = 0.08
# A sloped plan item outside the room (`2.5 m at 20 deg`): a plain deck plate this thick.
SLOPE = re.compile(r"(\d+(?:\.\d+)?) m at (\d+(?:\.\d+)?) deg")
RAMP_THICK = 0.2
RAMP_SURFACE = "deck"
GLASS_SURFACE = "clear_glass"
# A flat roof's slabs are this thick on the walls' top; its door leaves lie on them raised this far, so the sliding
# leaves clear the wall tops and corner posts they reached 0.08 m into (the motion stage's clear gate, 2026-10-12).
ROOF_SLAB = 0.25
LEAF_CLEAR = 0.15
# A growing plot: its soil this deep, its curb (thick, high) round it.
SOIL = 0.06
SOIL_SURFACE = "potting_soil"
CURB = (0.06, 0.16)
CURB_SURFACE = "painted_panel"
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
    shows); and for the gates the old record (the seed) and the old stages of the place and of each place a door leads
    to (`seed <stage>`, seed_stages: what the views are cut by and the openings compose; the table reads each from its
    earth-seed row)."""
    return {"inventory": f"{{data}}/inventory/{place_plan.inventory_name(place)}.json", "kits": "{data}/kit",
            "plans": "{data}/plans",
            "sky": "{data}/definitions/sky.json", "base": "{data}/definitions/base.json", "tube length": "{data}/scene/tube.json",
            "places": "{data}/definitions/place.json",
            "seed record": "{data}/scene/{place}.json",
            **{f"seed {stage}": f"{{seeds}}/usd-r3/{stage}" for stage in seed_stages(place)},
            "tokens": "{data}/../design/tokens/tokens.json"}


# What a door may lead to that is no place with a stage.
NOT_PLACES = {"outside", "sealed"}


def seed_stages(place):
    """The places whose old stage the writer and its gates stand: the place's own (its stage in the base, for a module
    of it: data/definitions/base.json) and each place a door of its plan leads to."""
    path = REPO / "data/plans" / f"{place}.json"
    leads = read(path).get("leads", {}) if path.exists() else {}
    own = read(REPO / "data/definitions/base.json")["modules"].get(place, {}).get("stage", place)
    return sorted({own, *(lead["to"] for lead in leads.values())} - NOT_PLACES)


def seed_of(inputs, stage):
    """A place's old stage folder (`seed <stage>`, files)."""
    return pathlib.Path(inputs[f"seed {stage}"])


def read(path):
    return json.loads(pathlib.Path(path).read_text())


# --- the shell --------------------------------------------------------------------------------------------------

def facet_shell(plan):
    """A faceted room's shell entries: its facets' walls with the cut doorways, a pyramid roof over them, the deck
    round its sunken pit, and the pit's walls and floor; the walls BACKING behind the plan's apothem."""
    walls = plan["walls"]
    sides, turn, apothem = walls["facets"], walls["turn"], round(walls["apothem"] + BACKING, 4)
    over = round(apothem + ROOF_OVER, 4)
    cut = [door for door in plan["doors"] if door["cut"]]
    said = (f"plan: {sides} facets, apothem {walls['apothem']} m turned {turn} degrees, backed {BACKING} m behind "
            "the kit's wall line")
    pit = f"the plan's pit, {walls['pit_radius']} m across its apothem, its floor {walls['pit_floor']} m"
    return [
        {"name": "shell_walls", "builder": "walls", "sides": sides, "apothem": apothem, "low": -DECK_BELOW,
         "high": walls["high"], "surface": SHELL_SURFACE, "rotation": turn,
         "openings": [[door["bearing"], door["wide"], door["tall"]] for door in cut],
         "from": f"{said}; walls {walls['high']} m; doorways cut in " +
                 (", ".join(f"door {door['plan_side']} ({door['what']}, leads {door['leads']})" for door in cut)
                  or "no door")},
        {"name": "shell_roof", "builder": "pyramid_roof", "sides": sides, "apothem": over, "eave": walls["high"],
         "rise": walls["rise"], "surface": SHELL_SURFACE, "rotation": turn, "layer": 2,
         "from": f"{said}; roof rising {walls['rise']} m to its apex (plan words), {ROOF_OVER} m over the walls"},
        {"name": "shell_deck", "builder": "annulus", "sides": sides, "inner": walls["pit_radius"], "outer": over,
         "height": -DECK_BELOW, "surface": SHELL_SURFACE, "rotation": turn, "plain": "shell",
         "from": f"{said}; just under the kit's floor plates, cut round {pit}"},
        {"name": "shell_pit_walls", "builder": "walls", "sides": sides, "apothem": walls["pit_radius"],
         "low": walls["pit_floor"] - DECK_BELOW, "high": 0.0, "surface": SHELL_SURFACE, "rotation": turn,
         "from": f"{pit}: its walls down from the deck"},
        {"name": "shell_pit_floor", "builder": "annulus", "sides": sides, "inner": 0.0,
         "outer": walls["pit_radius"], "height": walls["pit_floor"] - DECK_BELOW, "surface": SHELL_SURFACE,
         "rotation": turn, "plain": "shell", "from": f"{pit}: its floor, just under the kit's pit plates"}]


def tube_shell(plan):
    """A walkway tube's shell entries along its run: the hull's crown and two feet (steel), a glass band each side
    between them, and the deck where the hull meets the floor; the hull TUBE_BACKING outside the plan's radius."""
    walls = plan["walls"]
    radius, length = round(walls["radius"] + TUBE_BACKING, 4), walls["length"]
    low, high = walls["glass"]
    foot = round(math.degrees(math.acos(-walls["axis"] / walls["radius"])), 2)
    said = (f"plan: a tube of radius {walls['radius']} m round an axis {walls['axis']} m over the deck, "
            f"{length} m long; the hull {TUBE_BACKING} m outside the kit's hoops")
    arc = {"builder": "tube_arc", "radius": radius, "axis_high": walls["axis"], "length": length}
    return [
        {"name": "hull_crown", **arc, "start": -low, "end": low, "surface": SHELL_SURFACE,
         "from": f"{said}; its crown between the glass bands"},
        {"name": "hull_foot_east", **arc, "start": high, "end": foot, "surface": SHELL_SURFACE,
         "from": f"{said}; its foot under the east glass, down to the deck"},
        {"name": "hull_foot_west", **arc, "start": -foot, "end": -high, "surface": SHELL_SURFACE,
         "from": f"{said}; its foot under the west glass, down to the deck"},
        {"name": "glass_east", **arc, "start": low, "end": high, "surface": GLASS_SURFACE, "segments": 5,
         "from": f"{said}; the east glass band from {low} to {high} degrees off the crown (plan)"},
        {"name": "glass_west", **arc, "start": -high, "end": -low, "surface": GLASS_SURFACE, "segments": 5,
         "from": f"{said}; the west glass band from {low} to {high} degrees off the crown (plan)"},
        {"name": "deck", "builder": "box", "centre": [0.0, -TUBE_DECK / 2 - DECK_BELOW, length / 2],
         "size": [walls["deck"], TUBE_DECK, length], "surface": SHELL_SURFACE, "plain": "plate",
         "from": f"{said}; the deck {walls['deck']} m wide where the hull meets the floor, under the kit's plates"}]


def capsule_walls(plan):
    """A capsule room's walls with the cut doorways and its deck, BACKING behind the plan's inside: the entries, the
    grown numbers and what the plan said."""
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
         "from": f"{said}; just under the kit's floor plates"}], grown, said


def flat_shell(plan):
    """A flat-roofed room's shell (the hangar): its capsule walls and deck, and its roof as four slabs ROOF_SLAB
    thick on the walls' top round the door opening (the inventory's room layout's), which they leave open."""
    walls = plan["walls"]
    entries, grown, said = capsule_walls(plan)
    half_wide, half_deep = grown["wide"] / 2, grown["deep"] / 2
    open_wide, open_deep = walls["opening"][0] / 2, walls["opening"][1] / 2
    level = walls["high"] + ROOF_SLAB / 2
    slabs = {"west": ((-(half_wide + open_wide) / 2, 0.0), (half_wide - open_wide, 2 * half_deep)),
             "east": (((half_wide + open_wide) / 2, 0.0), (half_wide - open_wide, 2 * half_deep)),
             "north": ((0.0, -(half_deep + open_deep) / 2), (2 * open_wide, half_deep - open_deep)),
             "south": ((0.0, (half_deep + open_deep) / 2), (2 * open_wide, half_deep - open_deep))}
    return entries + [
        {"name": f"roof_slab_{side}", "builder": "box", "centre": [round(across, 4), level, round(along, 4)],
         "size": [round(wide, 4), ROOF_SLAB, round(deep, 4)], "surface": SHELL_SURFACE, "layer": 2, "plain": "plate",
         "from": f"{said}; the flat roof {ROOF_SLAB} m thick on the walls' top ({walls['high']} m), its {side} slab "
                 f"round the {walls['opening'][0]:g} x {walls['opening'][1]:g} m door opening (inventory room layout)"}
        for side, ((across, along), (wide, deep)) in slabs.items()]


def roof_leaves(plan):
    """A flat roof's door leaves (the room layout's leaf that lies on the roof, its kit's stage), shut side by side
    over the opening, each on its half; on the roof's top, raised LEAF_CLEAR so they slide clear of the walls' tops."""
    leaf, walls = plan.get("leaf") or {}, plan["walls"]
    if walls.get("shape") != "flat" or leaf.get("lies") != "roof":
        return []
    count = max(1, round(walls["opening"][0] / leaf["size"][0]))
    high = round(walls["high"] + ROOF_SLAB + LEAF_CLEAR, 4)
    found = []
    for number in range(count):
        across = round((number + 0.5) * walls["opening"][0] / count - walls["opening"][0] / 2, 4)
        side = "west" if across < 0 else "east"
        found.append({"name": f"roof_leaf_{side}" if count == 2 else f"roof_leaf_{number + 1}", "stage": leaf["kit"],
                      "at": [across, high, 0.0], "yaw": 0.0, "door_leaf": "roof",
                      "from": f"the room layout's roof leaf ({leaf['kit']} kit, {leaf['size'][0]:g} x "
                              f"{leaf['size'][1]:g} m), {number + 1} of {count} shut over the plan's roof door "
                              f"opening on its half, on the roof's top raised {LEAF_CLEAR} m clear of the walls' tops "
                              "(the motion stage's clear gate)"})
    return found


def shell(plan):
    """The room's shell entries: a faceted room's (facet_shell), a walkway tube's (tube_shell), a flat-roofed room's
    (flat_shell), or a domed room's walls with the cut doorways, deck and dome."""
    if plan["walls"].get("shape") == "faceted":
        return facet_shell(plan)
    if plan["walls"].get("shape") == "tube":
        return tube_shell(plan)
    if plan["walls"].get("shape") == "flat":
        return flat_shell(plan)
    walls = plan["walls"]
    entries, grown, said = capsule_walls(plan)
    return entries + [
        {"name": "dome_glass" if plan.get("glass") else "shell_roof", "builder": "dome_roof", **grown,
         "eave": walls["high"], "rise": walls["rise"], "run": walls["run"],
         "surface": GLASS_SURFACE if plan.get("glass") else SHELL_SURFACE, "layer": 2,
         "from": f"{said}; dome rising {walls['rise']} m over {walls['run']} m (plan words; inventory room layout run)"
                 + ("; glazed (inventory room layout glass_dome)" if plan.get("glass") else "")}]


def picked(row, spot):
    """The model the route's pick lays at a spot: the spot's own `model`, else the pick's one `model`, else the one
    model of a pick that lists `models` (its glows left out); a pick of several models whose spot names none cannot
    be read: an error naming the row."""
    pick = row["pick"]
    if spot.get("model"):
        return spot["model"]
    if pick.get("model"):
        return pick["model"]
    models = [name for name in pick.get("models", {}) if not name.endswith("_glow")]
    if len(models) != 1:
        raise ValueError(f"inventory row {row['id']}: its pick lists {len(models)} models and its spot names none")
    return models[0]


def row_model(place, row, spot):
    """The model an inventory row the kit does not lay stands as at a spot, and what made it: a library model
    the row names (`release_model`, the airlock's suit) or the route's pick (picked, from the place's kit models);
    else None."""
    if row.get("release_model"):
        return row["release_model"], f"the library's {row['release_model']}"
    if str(row.get("made", "")).startswith("made by the route") and row.get("pick"):
        model = picked(row, spot)
        return f"models/{place}_kit/{model}.gltf", f"made by the route, its pick {model}"
    return None


def objects(place, inventory):
    """Each inventory row the kit does not lay (row_model), laid at its own spots: one object at each spot, turned to
    its facing."""
    found = []
    for row in inventory["rows"]:
        for number, spot in enumerate((spot for spot in row.get("at", []) if "x" in spot), 1):
            made = row_model(place, row, spot)
            if made is None:
                break
            found.append({"name": f"{row['id']}_{number}", "row": row["id"], "model": made[0],
                          "at": [spot["x"], spot["y"], spot["z"]], "yaw": -float(spot.get("facing", 0.0)),
                          "from": f"inventory row {row['id']} ({made[1]}): its spot {number}, facing "
                                  f"{spot.get('facing', 0.0)} degrees"})
    return found


def door_leaves(place, plan, kit):
    """Each door leaf the plan's leads name (`leaf`: the airlock's outer door, which its cycle's motion moves and copies
    for the inner door) as an object shut in its doorway, the kit's model of its inventory row."""
    found = []
    for door in plan["doors"]:
        leaf = door.get("leaf")
        if not leaf:
            continue
        model = f"{leaf['row']}_1"
        if model not in kit.get("models", {}):
            raise ValueError(f"{place}: door {door['plan_side']}'s leaf, row {leaf['row']}, has no model {model} in "
                             "its kit")
        found.append({"name": leaf["name"], "row": leaf["row"], "model": f"models/{place}_kit/{model}.gltf",
                      "at": door["middle"], "yaw": LEAF_YAW[door["side"]],
                      "from": f"plan door {door['plan_side']} ({door['what']}): its leaf, inventory row {leaf['row']} "
                              f"(the kit's {model}), shut in its doorway"})
    return found


def plots(plan):
    """Each growing plot of the plan (kind `plot`) as plain plates: its soil a slab over the plot's box, a low curb
    round it."""
    found = []
    for item in plan["items"]:
        if item["kind"] != "plot":
            continue
        low_x, low_z, high_x, high_z = item["box"]
        middle, wide, deep = ((low_x + high_x) / 2, (low_z + high_z) / 2), high_x - low_x, high_z - low_z
        said = f"plan item {item['name']!r}"
        found.append({"name": "plot_soil", "builder": "box", "centre": [middle[0], SOIL / 2, middle[1]],
                      "size": [wide, SOIL, deep], "surface": SOIL_SURFACE, "plain": "soil",
                      "from": f"{said}: its soil over the plot's box"})
        for number, (centre, size) in enumerate((
                ((middle[0], low_z), (wide + CURB[0], CURB[1], CURB[0])),
                ((middle[0], high_z), (wide + CURB[0], CURB[1], CURB[0])),
                ((low_x, middle[1]), (CURB[0], CURB[1], deep + CURB[0])),
                ((high_x, middle[1]), (CURB[0], CURB[1], deep + CURB[0])))):
            found.append({"name": f"plot_wall_{number}", "builder": "box",
                          "centre": [round(centre[0], 4), CURB[1] / 2, round(centre[1], 4)],
                          "size": [round(value, 4) for value in size], "surface": CURB_SURFACE, "plain": "plate",
                          "from": f"{said}: the curb along its edge"})
    return found


def ramps(plan, inventory):
    """Each plan item outside the room that slopes (`<long> m at <angle> deg`) as a plain plate of its inventory row,
    its top edge on the sill of the door it lies before (on the plan's wall line), falling away from the room."""
    sizes = {row["id"]: row["size"] for row in inventory["rows"]}
    found = []
    for item in plan["items"]:
        sloped = SLOPE.search(item["name"])
        if item["kind"] != "outside" or sloped is None:
            continue
        long, angle = float(sloped.group(1)), math.radians(float(sloped.group(2)))
        row = item["rows"][0]
        door = min(plan["doors"], key=lambda entry: np.linalg.norm(
            np.asarray(entry["middle"])[[0, 2]] - np.mean(np.reshape(item["box"], (2, 2)), axis=0)))
        out = np.asarray(door["normal"], dtype=float)
        along = out * math.cos(angle) + np.array([0.0, -math.sin(angle), 0.0])
        top = np.array([0.0, math.cos(angle), 0.0]) + out * math.sin(angle)
        wide = float(sizes[row][0])
        centre = np.asarray(door["middle"], dtype=float) + along * long / 2 - top * RAMP_THICK / 2
        # The plate is built long along the way out and tipped about the axis across the door, its far end down.
        half = math.sin(angle / 2)
        if door["side"] in ("south", "north"):
            turn, size = [math.copysign(half, out[2]), 0.0, 0.0, math.cos(angle / 2)], [wide, RAMP_THICK, long]
        else:
            turn, size = [0.0, 0.0, -math.copysign(half, out[0]), math.cos(angle / 2)], [long, RAMP_THICK, wide]
        found.append({"name": row, "builder": "box", "centre": [0.0, 0.0, 0.0], "size": size,
                      "surface": RAMP_SURFACE, "placed_at": np.round(centre, 4).tolist(),
                      "placed_turn": [round(value, 6) for value in turn], "plain": "plate", "row": row,
                      "from": f"plan item {item['name']!r} (inventory row {row}, {wide} m wide, {RAMP_THICK} m "
                              f"thick): its top edge on door {door['plan_side']}'s sill, falling away from the room"})
    return found


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


def door_outside(door):
    """A door's middle on the shell's outer face, in its own place's frame."""
    return np.asarray(door["middle"], dtype=float) + np.asarray(door["normal"], dtype=float) * BACKING


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
    far_local = np.asarray(place_plan.door_middle(other_plan, other_door[0], other_door[1]), dtype=float) + \
        np.asarray(place_plan.outward(other_plan, other_door[0]), dtype=float) * BACKING
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


def places_of(place, plan, inputs, grounds):
    """Every place this one shows: door leaves, joined tubes, seated neighbours, and what the plan shows."""
    found = []
    for door in plan["doors"]:
        if door["cut"] and door.get("leaves"):
            found += leaves(plan, door)
        if door["cut"] and door["joins"]:
            found.append(joined_tube(place, door, inputs["plans"], grounds, read(inputs["tube length"])["tube_length"]))
    return found + roof_leaves(plan) + neighbours(place, grounds) + kit_shell.shown(plan, place, grounds, pose_in, quaternion)


# --- light, sky, views ------------------------------------------------------------------------------------------

def fill(plan, indoor):
    """The room's fill light: at the sky record's height share of the walls, reaching the farthest floor corner."""
    walls, light = plan["walls"], indoor["fill"]
    height = round(walls["high"] * light["height_share"], 4)
    reach = round(math.sqrt((walls["wide"] / 2) ** 2 + (walls["deep"] / 2) ** 2 + height ** 2), 3)
    middle = middle_of(plan)
    return {"type": "omni", "at": [middle[0], height, middle[1]], "colour": light["colour"], "energy": light["energy"],
            "range": reach, "attenuation": light["attenuation"], "shadows": False,
            "from": "sky record (data/definitions/sky.json) indoor fill, at its height share of the plan's walls, "
                    "reaching the plan's farthest floor corner"}


def environment(plan, indoor, body):
    """The body's indoor sky, its haze a box of the plan's inside up to the walls' top."""
    walls = plan["walls"]
    return {"background": indoor["background"], "ambient": dict(indoor["ambient"]), "exposure": indoor["exposure"],
            "inside": True, "from": f"sky record (data/definitions/sky.json) {body} indoor",
            "haze": {"shape": "box", "centre": [middle_of(plan)[0], walls["high"] / 2, middle_of(plan)[1]],
                     "size": [walls["wide"], walls["high"], walls["deep"]], **indoor["haze"],
                     "from": f"sky record {body} indoor haze, a box of the plan's inside to its walls' top"}}


def middle_of(plan):
    """The plan's inside's middle on its floor, in the place's frame (x, z)."""
    (low_x, low_z), (high_x, high_z) = plan["floor"]
    return np.array([(low_x + high_x) / 2, (low_z + high_z) / 2])


def item_middle(plan, name):
    low_x, low_z, high_x, high_z = next(item["box"] for item in plan["items"] if item["name"] == name)
    return np.array([(low_x + high_x) / 2, (low_z + high_z) / 2])


def views(plan, eye_height):
    """One view inside each door looking across the inside's middle (the door's mirror through it), one from each
    standing spot to the middle at its own level or to the plan item it looks at on the floor; each eye at standing
    height over its level."""
    found, middle = [], middle_of(plan)
    for door in plan["doors"]:
        at = np.asarray(door["middle"], dtype=float)
        eye = at - np.asarray(door["normal"], dtype=float) * VIEW_IN
        aim = 2 * middle - at[[0, 2]]
        found.append({"name": f"from-{door['side']}-door" + (f"-at-{door['level']:g}" if door["level"] else ""),
                      "eye": [round(eye[0], 3), round(at[1] + eye_height, 3), round(eye[2], 3)],
                      "aim": [round(aim[0], 3), round(at[1] + AIM_HEIGHT, 3), round(aim[1], 3)], "fov": VIEW_FOV,
                      "from": f"plan door {door['name']} ({door['what']}), looking across"})
    for number, spot in enumerate(plan["standing"], 1):
        aim = item_middle(plan, spot["looks_at"]) if spot["looks_at"] else middle
        aim_level = plan["floor_height"] if spot["looks_at"] else spot["level"]
        found.append({"name": f"spot-{number}",
                      "eye": [round(spot["at"][0], 3), round(spot["level"] + eye_height, 3), round(spot["at"][1], 3)],
                      "aim": [round(aim[0], 3), round(aim_level + AIM_HEIGHT, 3), round(aim[1], 3)],
                      "fov": VIEW_FOV, "from": f"plan standing spot {number}, looking to " +
                                              (f"plan item {spot['looks_at']!r}" if spot["looks_at"] else "the middle")})
    return found


# --- the record -------------------------------------------------------------------------------------------------

def record_of(place, plan, inputs):
    """The place's scene record from its plan and the world's records (module docstring)."""
    grounds = seats(inputs)
    seated = grounds.get(place)
    if seated is None and plan["shell"] == "kit" and ground_free(place, inputs):
        return ground_free_record(place, plan, inputs, grounds)
    if seated is None:
        raise ValueError(f"{place}: no seat on a made ground and no module of the base: its world body is unknown")
    if plan["shell"] == "kit":
        return kit_record(place, plan, inputs, grounds)
    if plan["shell"] == "outdoor":
        from score.stages.scene_record import outdoor  # it builds on this module's seats, places and views' numbers
        return outdoor.record_of(place, plan, inputs, grounds)
    if not plan["inside"] or not (plan["walls"].get("rise") or
                                  plan["walls"].get("shape") in ("faceted", "tube", "flat")):
        raise NotImplementedError(f"{place}: its plan's shell is domed but it is no domed room, faceted room, "
                                  "walkway tube or flat-roofed room")
    walls = plan["walls"]
    body = seated.ground
    indoor = read(inputs["sky"])[body]["indoor"]
    eye = read(inputs["places"])["shared"]["scale"]["eye_height"]
    inventory = read(inputs["inventory"])
    return {"place": place,
            "about": f"{plan['title']}, written by SCORE's scene-record stage from its plan (data/plans/{place}.json), "
                     "its inventory, the made ground's seats and the world's sky record. Frame: the room's middle on "
                     "its floor, x east, z south.",
            "floor": plan["floor"], "ceiling": round(walls["high"] + walls["rise"], 4), "inside": True,
            "structure": shell(plan) + ramps(plan, inventory) + plots(plan),
            "objects": objects(place, inventory) + door_leaves(place, plan, read(pathlib.Path(inputs["kits"]) /
                                                                                 f"{place}.json")),
            "lights": [fill(plan, indoor)], "environment": environment(plan, indoor, body),
            "views": views(plan, eye), "places": places_of(place, plan, inputs, grounds),
            # A walkway tube's run, which its kit's bays are laid along (the assembly reads it).
            **({"tube_length": walls["length"]} if walls.get("shape") == "tube" else {})}


def ground_free(place, inputs):
    """The plan's reason when it is a ground-free interior (its `ground_free`: the ship's rooms, which stand in the
    hangar's ship, not on a made ground; the overseer, 2026-10-14), else None."""
    return read(pathlib.Path(inputs["plans"]) / f"{place}.json").get("ground_free")


def ground_free_record(place, plan, inputs, grounds):
    """The scene record of a ground-free interior: no seat, so nothing outside it and no body's sky over it; its kit
    holds its walls and floors, its air and fill are the base's body's indoor ones (the body the base's modules
    stand on, base.json `seat_of`), its views and door leaves its plan's, judged against its own walls."""
    body = grounds[read(inputs["base"])["seat_of"]].ground
    indoor = read(inputs["sky"])[body]["indoor"]
    kit_path = pathlib.Path(inputs["kits"]) / f"{place}.json"
    eye = read(inputs["places"])["shared"]["scale"]["eye_height"]
    found = [leaf for door in plan["doors"] if door["cut"] and door.get("leaves") for leaf in leaves(plan, door)]
    return {"place": place,
            "about": f"{plan['title']}, written by SCORE's scene-record stage from its plan (data/plans/{place}.json), "
                     f"a ground-free interior ({ground_free(place, inputs)}): no seat and nothing outside; its kit "
                     f"holds its walls and floors, its air is the {body} base's indoor air from the world's sky "
                     "record. Frame: the room's middle on its floor, x east, z south.",
            "floor": plan["floor"], "inside": True, "ceiling": round(plan["floor_height"] + plan["walls"]["high"], 4),
            "structure": [], "objects": kit_shell.objects(plan, read(kit_path) if kit_path.exists() else None),
            "lights": [fill(plan, indoor)], "environment": environment(plan, indoor, body), "views": views(plan, eye),
            "places": found + roof_leaves(plan)}


def kit_record(place, plan, inputs, grounds):
    """The scene record of a place whose kit holds its walls and floors (kit_shell.py's docstring)."""
    seated = grounds[place]
    sky = {**read(inputs["sky"])[seated.ground], "body": seated.ground}
    kit = read(pathlib.Path(inputs["kits"]) / f"{place}.json")
    pose = kit_shell.shared_pose(place, grounds, sky, pose_in)
    eye = read(inputs["places"])["shared"]["scale"]["eye_height"]
    record = {"place": place,
              "about": f"{plan['title']}, written by SCORE's scene-record stage from its plan (data/plans/{place}.json), "
                       f"its kit's lamps, the made ground's seats and the world's sky record. Frame: its kit's, "
                       f"{sky['frame_of']}'s frame moved to its seat.",
              "floor": plan["floor"], "inside": plan["inside"], "structure": kit_shell.block(plan),
              "objects": kit_shell.objects(plan, kit),
              "lights": kit_shell.lamps(plan, kit, sky) + [kit_shell.moonlight(sky, pose)],
              "moon": kit_shell.moon(sky, pose), "kit_glow": kit_shell.kit_glow(sky),
              "environment": kit_shell.environment(plan, sky, pose), "views": views(plan, eye),
              "places": places_of(place, plan, inputs, grounds)}
    if seated.made.get("water"):
        record["water"] = kit_shell.water(sky, seated.made, pose)
    if plan["inside"]:
        record["ceiling"] = round(plan["floor_height"] + plan["walls"]["high"], 4)
    if plan.get("moves"):
        record["moved"] = [{"node": move["node"], "by": move["by"],
                            "from": f"plan door {move['door']}: its leaf stands open ({move['why']})"}
                           for move in plan["moves"]]
    return record


def planned_ground(plan):
    """The ground past the place to the horizon and the ball under it (the plan's `far_ground`: how far round the
    place, how fine, the ball's surface), as the record's `planned_ground`; None when the plan sees no far ground."""
    far = plan.get("far_ground")
    if not far:
        return None
    return {"reach": far["reach"], "step": far["step"], "ball": far["ball"],
            "from": f"plan far_ground ({far['why']}): the made ground's place layer drawn out to {far['reach']} m round "
                    "the place, the ball under it"}


def removed(plan):
    """The rows the plan's concept leaves out (its `removes`), as the record's coordinator_removed: the assembly takes
    every seed object of those rows out of the base (assembly record.relay_kit)."""
    return [{"what": f"inventory row {entry['row']}", "rows": [entry["row"]], "date": entry["date"],
             "why": entry["why"], "from": f"plan removes {entry['row']} ({entry['why']})"} for entry in plan["removes"]]


def child_row(model, rows, place):
    """The inventory row a kit child model is of: its name less its number (`case_1`: case), a row the inventory has."""
    row = re.sub(r"_\d+$", "", model)
    if row not in rows:
        raise ValueError(f"{place}: kit child model {model} names no inventory row {row}")
    return row


def kit_children(entry, kit, rows, removed_rows, place):
    """What stands on an object as its kit's model lists it (`children`: model, at and turn in the object's own
    frame), each with the model's glow parts (kit models `part_of` it), less rows the plan removes; [] for a model
    the kit lists none for. Left out, the cases on the camp's stores rack went missing (2026-10-13)."""
    model_path = pathlib.PurePosixPath(entry["model"])
    models = kit.get("models", {})
    found = []
    for number, child in enumerate(models.get(model_path.stem, {}).get("children", []), 1):
        row = child_row(child["model"], rows, place)
        if row in removed_rows:
            continue
        glows = [name for name, about in sorted(models.items()) if about.get("part_of") == child["model"]]
        found += [{"model": str(model_path.parent / f"{name}.gltf"), "row": row, "at": child["at"],
                   "yaw": float(child["turn"]),
                   "from": f"kit model {model_path.stem}'s child {number} ({child['model']}), inventory row {row}"}
                  for name in [child["model"], *glows]]
    return found


def with_children(record, place, inputs, plan):
    """The record's objects, each carrying what its kit's model stands on it (kit_children)."""
    kit_path = pathlib.Path(inputs["kits"]) / f"{place}.json"
    if not kit_path.exists():
        return
    kit, rows = read(kit_path), {row["id"] for row in read(inputs["inventory"])["rows"]}
    removed_rows = {entry["row"] for entry in plan.get("removes", [])}
    for entry in record.get("objects", []):
        children = kit_children(entry, kit, rows, removed_rows, place) if "model" in entry else []
        if children:
            entry["children"] = children


def shown_only(place, plan, record, inputs):
    """The record with only the seated neighbours its own views see (seen.py); the nearest place of each stage a door
    leads to (its doorway opens onto it), a joined tube, a door leaf and a place the plan shows are always kept."""
    from score.stages.scene_record import seen
    from score.stages.terrain import gates as ground_gates
    grounds = seats(inputs)
    seated = [entry for entry in record["places"] if entry["name"] in grounds and "joins" not in entry
              and not entry.get("door_leaf") and entry["name"] not in plan.get("shows", {})]
    opened = {id(min(those, key=lambda entry: np.linalg.norm(np.asarray(entry["at"]) - door_outside(door))))
              for door in plan["doors"] if door["cut"]
              for those in [[entry for entry in seated if entry["stage"] == door["leads"]]] if those}
    candidates = [entry for entry in seated if id(entry) not in opened]
    if not candidates:
        return record
    here = grounds[place]
    kit_path = pathlib.Path(inputs["kits"]) / f"{here.stage}.json"
    kit = read(kit_path) if kit_path.exists() else None
    zoned, _ = outside.meshes(here.made, here.entry, on_seat_of(inputs["kits"], here.stage),
                              ground_gates.footprint(record, kit))
    rays = ground_gates.caster(seen.occluders(seed_of(inputs, here.stage), zoned))
    kept = seen.visible(record["views"], candidates, inputs["plans"], rays, VIEW_FOV)
    return {**record, "places": [entry for entry in record["places"]
                                 if entry not in candidates or entry["name"] in kept]}


def make(inputs, out, seed, params):
    """record/<place>.json: the place's scene record, with its planned ground when the plan sees one."""
    plan = read(pathlib.Path(inputs["plan"]) / "plan.json")
    place = plan["place"]
    record = shown_only(place, plan, record_of(place, plan, inputs), inputs)
    with_children(record, place, inputs, plan)
    far = planned_ground(plan)
    if far:
        record["planned_ground"] = far
    if plan.get("removes"):
        record["coordinator_removed"] = removed(plan)
    (out / "record").mkdir()
    (out / "record" / f"{place}.json").write_text(json.dumps(record, indent=1))


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
