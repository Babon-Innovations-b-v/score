"""The scene-record stage's gates, each measured on the written record:

    game-free     no text of the record names a game file or the game's code (a Godot script or scene, a game path,
                  the game's class names): the record is made from the plan, never transcribed
    plan-matched  the shell is the plan's: inside, corners, walls' height and dome (a flat roof: its slabs on the walls'
                  top covering the roof round its door opening, none over it) within TOLERANCE once the backing is
                  taken off, the floor box the plan's inside, every door the plan cuts cut at its wide and tall in its
                  wall's middle (room_walls cuts there only), every shut door uncut. A kit shell (the Earth's): the
                  floor box the plan's inside, the block's masses on the plan's block (over: its footprint from a
                  storey line over the room's ceiling to its roof; under: the room's inside grown by its walls, from
                  the street to the floor), no other structure, and the kit's doorways the plan's doors: each cut door
                  a kit doorway at its middle (along its wall; out of it, within the piece's thickness), wide and tall,
                  every kit piece the record moves (a leaf stood open) clear of the others along its path,
                  no doorway at a shut door, no open doorway off the plan (one a kit piece fills, a shopfront, is
                  none). An outdoor place: the floor box the plan's site, no room shell, a light for each plan lamp,
                  each plan decal painted and each plan beam stood; its openings' viewers stand on the made ground
    openings      every doorway leads somewhere: the record's shell with the places its doorways open onto (door_places; each door's leaves left out, as
                  opened; a kit shell's own kit floors with it) composed over the made ground in the place's frame
                  (terrain outside.py), every cut doorway
                  has a floor on both sides and no view from inside runs out below the horizon into nothing
                  (terrain sight.py); a door that leads to a place has that place's floor past it
    seed-matched  every entry of the old record (the seed, data/scene/<place>.json, never read by the writer) is matched
                  by a new entry of its kind (a builder, a light's type, a place's stage, a view's eye) or left out
                  with the writer's written reason (SEED_REASONS); how far a matched entry's numbers moved is shown,
                  never judged
"""
import json
import pathlib
import re

import numpy as np
from pxr import Usd, UsdGeom, UsdShade

from score import checks
from score.stages.scene_record import kit_shell, writer
from score.stages.terrain import gates as ground_gates, outside, sight

# A game file or the game's code: a Godot script, scene or shader, a path into its tree, its shell class.
GAME = re.compile(r"\.(gd|tscn|tres|gdshader)\b|res://|(^|[\s(])(game|sim)/\w|ModuleShell|module_shell|2099")
# Plan numbers held within this (metres).
TOLERANCE = 0.05
# A matched entry stands this close to its seed (metres); a view's eye this close.
MATCH_REACH = 2.0
# What the writer leaves out of a record on purpose: by the old record's section, one entry as
# `<place>:<section>/<name>`, or a family of entries by its name's start (`<section>/<start>_`, kept to one place
# with `<place>:`).
SEED_REASONS = {
    "game_only": "the record holds no notes about the game: what the concept shows is an inventory row or a plan item",
    "owner_rejected": "what the owner took out is in no plan item, concept element or inventory row, so nothing "
                      "writes it back: the record needs no list of it",
    "ground": "the made ground (the terrain stage) is the ground round the place: the assembly sublayers it, so the "
              "record draws no ground of its own",
    "tube:planned_ground": "the walkway tube has no window: no ground past it is seen from inside",
    "planned_rocks": "the ground's rocks are the terrain stage's, laid by its plan's rule with the ground",
    "places": "a place on the same made ground stands in the record only when the place's own views see it (in a "
              "view's frame, near enough to show, nothing of the place between: seen.py) or a doorway opens onto it; "
              "the concept decides what is shown, not the ground's seats",
    **{f"{place}:objects/{name}": "the solar rows and the inverter round the base are no element of this place's "
                                  "concept (the base shows far off or not at all) and no row of this place; they come "
                                  "back with the base's outside rows"
       for place in ("wreck", "old_station") for name in ("SolarRow1", "SolarRow2", "SolarRow3", "Inverter")},
    "wreck:coordinator_removed/coordinator_removed": "settled by the concept (decision of 2026-10-12): C2 shows no "
                                                     "supply rocket, cargo lift or landing dust, so the place stands "
                                                     "none; no kit piece lays their inventory rows",
    "old_station:coordinator_removed/coordinator_removed": "settled by the concept (decision of 2026-10-12): C4 shows "
                                                           "no supply rocket or cargo lift, so the place stands none; "
                                                           "no kit piece lays their inventory rows",
    **{f"{place}:views/{name}": "the old record's views were the game's shot cameras; the record's are the plan's "
                                "standing spots (an outside one of the camp's is the camp grounds')"
       for place, names in (("wreck", ("wreck-wake", "wreck-side", "wreck-home")),
                            ("old_station", ("station-approach", "station-ladder", "station-south", "station-above")),
                            ("campgrounds", ("from_the_ramp", "above")),
                            ("camp", ("door_from_doorway", "door_galley", "far_bunks", "passage", "outside_front",
                                      "outside_far")))
       for name in names},
    "camp:objects/BootRock": "the boot rock stands outside, in the camp grounds' record (a plan object of K05's tall "
                             "boulder), seen from here through the grounds",
    "camp:lights/omni": "the dome lamps are lit where the kit hangs its ring lamps under each dome's crown (2.3 m over "
                        "the old lamps, as K01 and K08 hang them high); the mast's beacon is the camp grounds' (its "
                        "beam), not this place's",
    "launch:objects/rocket": "the rocket stands on its pad's middle as the kit lays the pad's tiles (the plan's ROCKET "
                             "item), 3.6 m from where the old record stood it off that middle",
    "launch:lights/spot": "the rocket's one floodlight is now the pad's four (inventory row far_pad_floodlight), each "
                          "lit at its lamp and aimed at the rocket's middle",
    **{f"hangar:structure/{name}": "the ship is the inventory's row ship (the machines track's), not a hull the shell "
                                   "builds in code"
       for name in ("ship", "ship_legs")},
    "workshop:objects":"the robot and the parts tray come from the machines track as rows, not from this record",
    "workshop:structure/tray_tile_": "the workshop's parts tray (its tiles and the robot parts on them) comes from "
                                     "the machines track as rows, not as plain plates of the shell",
    "hub:objects/lab_bench/children/status_lamp_1": "concept M3-east (inventory view v3) shows the lab bench with no "
                                                    "red status lamp on it; the inventory has no row for one",
    "hub:objects/screen_":"the console's screens are its monitors, laid on it by its composite, not loose objects",
    **{f"{place}:views": "the record's views are its plan's: one inside each door and one from each standing spot; "
                         "a seed view with no such spot near it was a camera of the game's"
       for place in ("airlock", "workshop", "lab", "habitat", "greenhouse", "hub", "tube", "hangar")},
    "greenhouse:structure/bed_": "the plot is the plan's one bed of soil in its curb (plot_soil, plot_wall); its "
                                 "rows of crops are the crops track's",
    "greenhouse:structure/ridge_": "the plot is the plan's one bed of soil in its curb (plot_soil, plot_wall); its "
                                   "rows of crops are the crops track's",
    "greenhouse:structure/plot_wall_": "the seed's curb ringed a 3 m starting plot; the plan's plot is the 12 m bed "
                                       "the concept K09 shows, its curb laid along that bed's edge",
    "greenhouse:structure/tarp_": "the concept K09 shows no tarps on the deck",
    "greenhouse:lights/omni": "the grow lights are the grow-light bars' lamps (inventory grow_light_glow), which the "
                              "kit lights",
    "greenhouse:lights/sun": "the sun through the glass is the world's sky, the light stage's, not one room's record",
    "hub:lights/sun": "the sun is the world's sky, the light stage's, not one room's record",
    "tube:lights/sun": "the sun through the glass bands is the world's sky, the light stage's, not one room's record",
}
# A kit doorway: an opening in a kit piece (a wall, a facade) from its foot up, at least this tall.
DOORWAY_TALL = 1.9
# A doorway with another kit piece standing this close to its middle is filled (a shopfront's shutter or lit front).
FILLED = 0.3


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


# --- plan-matched -----------------------------------------------------------------------------------------------

def plan_of(inputs):
    return json.loads((pathlib.Path(inputs["plan"]) / "plan.json").read_text())


def entry(record, builder):
    return next((item for item in record["structure"] if item["builder"] == builder), None)


def shell_faults(record, walls):
    """The shell's numbers against the plan's, the backing taken off."""
    found = []
    wanted = {"wide": walls["wide"] + 2 * writer.BACKING, "deep": walls["deep"] + 2 * writer.BACKING,
              "corner": walls["corner"] + writer.BACKING}
    builders = (("room_walls", {"high": walls["high"]}), ("room_deck", {}))
    if walls.get("shape") != "flat":
        builders += (("dome_roof", {"eave": walls["high"], "rise": walls["rise"]}),)
    for builder, extra in builders:
        made = entry(record, builder)
        if made is None:
            found.append(f"no {builder} in the record's shell")
            continue
        found += [f"{builder} {key} {made[key]} against the plan's {value:.3f}"
                  for key, value in {**wanted, **extra}.items() if abs(float(made[key]) - value) > TOLERANCE]
    low, high = np.asarray(record["floor"], dtype=float)
    plan_low = np.array([-walls["wide"] / 2, -walls["deep"] / 2])
    if np.abs(low - plan_low).max() > TOLERANCE or np.abs(high + plan_low).max() > TOLERANCE:
        found.append(f"floor {record['floor']} is not the plan's inside {walls['wide']} x {walls['deep']} m")
    return found


def door_faults(record, plan):
    """Every cut door cut at its plan size in its wall's middle; every shut door uncut."""
    walls = entry(record, "room_walls") or {"doors": []}
    cut = {door["side"]: door for door in walls.get("doors", [])}
    found = []
    for door in plan["doors"]:
        name = f"door {door['plan_side']} ({door['what']})"
        middle = np.asarray(door["middle"], dtype=float)
        if door["cut"] and abs(middle[0 if door["side"] in ("north", "south") else 2]) > TOLERANCE:
            found.append(f"{name} stands {np.round(middle, 2).tolist()}, off its wall's middle, where room_walls "
                         "cannot cut it")
        made = cut.pop(door["side"], None)
        if door["cut"] and made is None:
            found.append(f"{name} leads {door['leads']} but is not cut")
        elif door["cut"] and (abs(made["wide"] - door["wide"]) > TOLERANCE or abs(made["tall"] - door["tall"]) > TOLERANCE):
            found.append(f"{name} cut {made['wide']} x {made['tall']} m against the plan's {door['wide']} x "
                         f"{door['tall']} m")
        elif not door["cut"] and made is not None:
            found.append(f"{name} is shut ({door['why']}) but cut")
    found += [f"a doorway is cut in the {side} wall, where the plan has no door" for side in cut]
    return found


def roof_faults(record, walls):
    """A flat roof's slabs against the plan: each on the walls' top, none over the door opening or past the walls, none
    over another, and together the whole roof round the opening (their areas summed, within TOLERANCE of it)."""
    half = np.array([walls["wide"] / 2 + writer.BACKING, walls["deep"] / 2 + writer.BACKING])
    opening = np.asarray(walls["opening"], dtype=float) / 2
    found, spans = [], []
    for slab in (item for item in record["structure"] if item["name"].startswith("roof_slab_")):
        low, high = box_span(slab)
        spans.append((low[[0, 2]], high[[0, 2]]))
        if abs(low[1] - walls["high"]) > TOLERANCE:
            found.append(f"{slab['name']} lies at {low[1]:.2f} m, not on the walls' top ({walls['high']} m)")
        if (low[[0, 2]] < -half - TOLERANCE).any() or (high[[0, 2]] > half + TOLERANCE).any():
            found.append(f"{slab['name']} reaches past the walls")
        if (np.minimum(high[[0, 2]], opening) - np.maximum(low[[0, 2]], -opening) > TOLERANCE).all():
            found.append(f"{slab['name']} lies over the roof's door opening")
    for number, (low, high) in enumerate(spans):
        for other_low, other_high in spans[number + 1:]:
            if (np.minimum(high, other_high) - np.maximum(low, other_low) > TOLERANCE).all():
                found.append("two roof slabs lie over each other")
    covered = sum(float(np.prod(high - low)) for low, high in spans)
    wanted = float(np.prod(2 * half) - np.prod(2 * opening))
    if abs(covered - wanted) > TOLERANCE * 2 * half.sum():
        found.append(f"the roof's slabs cover {covered:.2f} m2, the roof round its opening {wanted:.2f} m2")
    return found


def floor_faults(record, plan):
    if np.abs(np.asarray(record["floor"], dtype=float) - np.asarray(plan["floor"], dtype=float)).max() > TOLERANCE:
        return [f"floor {record['floor']} is not the plan's inside {plan['floor']}"]
    return []


def box_span(entry):
    """A box entry's low and high corners."""
    centre, size = np.asarray(entry["centre"], dtype=float), np.asarray(entry["size"], dtype=float)
    return centre - size / 2, centre + size / 2


def block_faults(record, plan):
    """The block's masses against the plan's block (module docstring); no other structure."""
    block, walls = plan.get("block"), plan["walls"]
    made = {entry["name"]: entry for entry in record["structure"]}
    if not block:
        return [f"structure {name} where the plan has no block" for name in made]
    found = [f"structure {name} is no mass of the plan's block" for name in made
             if name not in ("block_over", "block_under")]
    if "block_over" not in made:
        return found + ["no block_over: the plan's block has nothing over the room"]
    low, high = box_span(made["block_over"])
    lines = (low[1] - block["street"]) / walls["storey"]
    ceiling = plan["floor_height"] + walls["high"]
    if abs(lines - round(lines)) * walls["storey"] > TOLERANCE or not ceiling - TOLERANCE <= low[1] < ceiling + walls["storey"]:
        found.append(f"block_over starts at {low[1]:.2f} m, not the first storey line over the room's ceiling "
                     f"({ceiling:g} m)")
    wanted = [block["low"][0], block["top"], block["low"][1]], [block["high"][0], block["top"], block["high"][1]]
    if np.abs(low[[0, 2]] - np.asarray(wanted[0])[[0, 2]]).max() > TOLERANCE or             np.abs(high - np.asarray(wanted[1])).max() > TOLERANCE:
        found.append(f"block_over {low.round(2).tolist()} to {high.round(2).tolist()} is not the plan's block "
                     f"{block['low']} to {block['high']} up to {block['top']} m")
    under = plan["floor_height"] - block["street"] > TOLERANCE
    if under != ("block_under" in made):
        found.append("block_under " + ("missing under a room over the street" if under else "under a room on the street"))
    elif under:
        low, high = box_span(made["block_under"])
        (room_low_x, room_low_z), (room_high_x, room_high_z) = plan["floor"]
        grown = [room_low_x - block["wall"], room_low_z - block["wall"], room_high_x + block["wall"],
                 room_high_z + block["wall"]]
        if abs(low[1] - block["street"]) > TOLERANCE or abs(high[1] - plan["floor_height"]) > TOLERANCE or                 np.abs(np.array([low[0], low[2], high[0], high[2]]) - grown).max() > TOLERANCE:
            found.append(f"block_under {low.round(2).tolist()} to {high.round(2).tolist()} is not the room's inside "
                         f"grown by {block['wall']} m from the street to its floor")
    return found


def kit_doorways(kit):
    """Every doorway the kit's pieces cut: its middle on its sill (in the piece's thickness), wide, tall and the
    piece's thickness."""
    found = []
    for piece in kit.get("pieces", []):
        for low_u, low_v, high_u, high_v in piece.get("openings") or []:
            if low_v > TOLERANCE or high_v - low_v < DOORWAY_TALL:
                continue
            across, up = (np.asarray(piece[axis], dtype=float) for axis in ("x", "y"))
            middle = np.asarray(piece["at"], dtype=float) + across * (low_u + high_u) / 2 + up * low_v
            filled = any(np.linalg.norm(np.asarray(other["at"], dtype=float) - middle) <= FILLED
                         for other in kit["pieces"] if other["kind"] != piece["kind"])
            found.append({"middle": middle, "filled": filled,
                          "wide": high_u - low_u, "tall": high_v - low_v, "deep": float(piece["size"][2]),
                          "piece": piece.get("model", piece["kind"])})
    return found


def kit_door_faults(plan, kit):
    """Each cut plan door a kit doorway at its middle, wide and tall; no doorway at a shut door or off the plan."""
    doorways, found = kit_doorways(kit), []
    for door in plan["doors"]:
        name = f"door {door['name']} ({door['what']})"
        middle = np.asarray(door["middle"], dtype=float)
        near = [way for way in doorways if np.linalg.norm(way["middle"] - middle) <= max(TOLERANCE, door["wide"] / 2)]
        if not door["cut"]:
            found += [f"{name} is shut ({door['why']}) but the kit cuts a doorway at {way['middle'].round(2).tolist()}"
                      for way in near]
        elif not near:
            found.append(f"{name} leads {door['leads']} but no kit doorway stands at {middle.round(2).tolist()}")
        else:
            way = min(near, key=lambda way: np.linalg.norm(way["middle"] - middle))
            off = way["middle"] - middle
            out = abs(float(off @ np.asarray(door["normal"], dtype=float)))
            along = float(np.linalg.norm(off - off @ np.asarray(door["normal"], dtype=float) * np.asarray(door["normal"])))
            if along > TOLERANCE or out > way["deep"] / 2 + TOLERANCE or abs(way["wide"] - door["wide"]) > TOLERANCE \
                    or abs(way["tall"] - door["tall"]) > TOLERANCE:
                found.append(f"{name}: the kit's doorway stands {along:.2f} m along and {out:.2f} m out of its wall "
                             f"line off, {way['wide']:.2f} x {way['tall']:.2f} m against the plan's {door['wide']} x "
                             f"{door['tall']} m")
        doorways = [way for way in doorways if not any(way is other for other in near)]
    found += [f"the kit cuts a doorway at {way['middle'].round(2).tolist()} ({way['piece']}) where the plan has no door"
              for way in doorways if not way["filled"]]
    return found


def site_faults(record, plan):
    """An outdoor record against its plan: no room shell, a light for each plan lamp, each plan decal and beam
    stood."""
    found = [f"a {item['builder']} stands in an outdoor place's record" for item in record.get("structure", [])
             if item["builder"] in ("room_walls", "room_deck", "dome_roof")]
    lit = " ".join(light.get("from", "") for light in record.get("lights", []))
    found += [f"plan lamp {lamp['name']} has no light" for lamp in plan["lamps"]
              if f"plan lamp {lamp['name']} " not in lit]
    decals = {decal["name"] for decal in record.get("ground_decals", [])}
    found += [f"plan decal {decal['name']} is not painted" for decal in plan["decals"] if decal["name"] not in decals]
    beams = {beam["name"] for beam in record.get("environment", {}).get("beams", [])}
    found += [f"plan beam {beam['name']} is not stood" for beam in plan["beams"] if beam["name"] not in beams]
    stood = {item["name"] for item in record.get("structure", [])}
    found += [f"plan block {block['name']} is not stood" for block in plan["blocks"] if block["name"] not in stood]
    return found


def facet_faults(record, plan):
    """A faceted room's shell against its plan, the backing taken off: walls, roof, deck and pit, and every cut door
    an opening at its bearing, wide and tall (every shut one none)."""
    walls, found = plan["walls"], []
    wanted = {"walls": {"sides": walls["facets"], "apothem": walls["apothem"] + writer.BACKING,
                        "high": walls["high"], "rotation": walls["turn"]},
              "pyramid_roof": {"sides": walls["facets"], "eave": walls["high"], "rise": walls["rise"],
                               "rotation": walls["turn"]},
              "annulus": {"sides": walls["facets"], "inner": walls["pit_radius"], "rotation": walls["turn"]}}
    for builder, numbers in wanted.items():
        made = entry(record, builder)
        if made is None:
            found.append(f"no {builder} in the record's shell")
            continue
        found += [f"{builder} {key} {made[key]} against the plan's {value:.3f}"
                  for key, value in numbers.items() if abs(float(made[key]) - value) > TOLERANCE]
    openings = {round(float(bearing)) % 360: (wide, tall) for bearing, wide, tall in
                (entry(record, "walls") or {}).get("openings", [])}
    for door in plan["doors"]:
        name = f"door {door['plan_side']} ({door['what']})"
        made = openings.pop(round(door["bearing"]) % 360, None)
        if door["cut"] and made is None:
            found.append(f"{name} leads {door['leads']} but is not cut")
        elif door["cut"] and max(abs(made[0] - door["wide"]), abs(made[1] - door["tall"])) > TOLERANCE:
            found.append(f"{name} cut {made[0]} x {made[1]} m against the plan's {door['wide']} x {door['tall']} m")
        elif not door["cut"] and made is not None:
            found.append(f"{name} is shut ({door['why']}) but cut")
    return found + [f"a doorway is cut at bearing {bearing}, where the plan has no door" for bearing in openings]


def tube_faults(record, plan):
    """A walkway tube's hull, glass and deck against its plan: every arc round the plan's axis at its radius (the
    backing taken off) and length, the glass bands at the plan's bearings, the deck its width and length."""
    walls, found = plan["walls"], []
    arcs = [made for made in record["structure"] if made["builder"] == "tube_arc"]
    for made in arcs:
        found += [f"{made['name']} {key} {made[key]} against the plan's {value:.3f}" for key, value in
                  {"radius": walls["radius"] + writer.TUBE_BACKING, "axis_high": walls["axis"],
                   "length": walls["length"]}.items() if abs(float(made[key]) - value) > TOLERANCE]
    glass = sorted(sorted(map(abs, (made["start"], made["end"]))) for made in arcs
                   if made["surface"] == writer.GLASS_SURFACE)
    if glass != [walls["glass"], walls["glass"]]:
        found.append(f"glass bands {glass} against the plan's {walls['glass']} degrees each side")
    deck = entry(record, "box")
    if deck is None or abs(deck["size"][0] - walls["deck"]) > TOLERANCE or \
            abs(deck["size"][2] - walls["length"]) > TOLERANCE:
        found.append(f"the deck is not the plan's {walls['deck']} x {walls['length']} m")
    return found


# A moved kit piece's path may touch another piece this deep (metres): a leaf runs against its wall.
SWEEP_TOUCH = 0.01


def piece_box(piece):
    """A kit piece's box (low, high) in the place's frame: x across and z out centred on its `at`, y up from it."""
    axes = np.array([piece[axis] for axis in ("x", "y", "z")], dtype=float)
    corners = np.array([[across, up, out] for across in (-0.5, 0.5) for up in (0.0, 1.0) for out in (-0.5, 0.5)])
    laid = np.asarray(piece["at"], dtype=float) + (corners * np.asarray(piece["size"], dtype=float)) @ axes
    return laid.min(axis=0), laid.max(axis=0)


def sweep_faults(record, kit):
    """Each kit piece the record moves (`moved`: a leaf it stands open) sweeps its box from where the kit lays it to
    where it stands; no other kit piece may stand deeper than SWEEP_TOUCH in that path."""
    found = []
    for move in record.get("moved", []):
        moving = [piece for piece in kit["pieces"] if piece.get("node") == move["node"]]
        if not moving:
            found.append(f"moved node {move['node']} is no piece of the kit")
            continue
        by = np.asarray(move["by"], dtype=float)
        for piece in moving:
            low, high = piece_box(piece)
            low, high = np.minimum(low, low + by), np.maximum(high, high + by)
            for other in kit["pieces"]:
                if other.get("node") == move["node"]:
                    continue
                other_low, other_high = piece_box(other)
                depth = float(np.min(np.minimum(high, other_high) - np.maximum(low, other_low)))
                if depth > SWEEP_TOUCH:
                    found.append(f"{piece['kind']} ({move['node']}) moving {by.tolist()} m runs {depth:.2f} m into "
                                 f"{other['kind']} at {np.round(other['at'], 2).tolist()}")
    return found


def judge_plan_matched(output, inputs, evidence):
    """Fail on a shell number or a door off the plan (an outdoor place: its site, lamps, decals and beams)."""
    place, record = writer.record_in(output)
    plan = plan_of(inputs)
    if plan["shell"] == "kit":
        kit = json.loads((pathlib.Path(inputs["kits"]) / f"{place}.json").read_text())
        found = tuple(floor_faults(record, plan) + block_faults(record, plan) + kit_door_faults(plan, kit) +
                      sweep_faults(record, kit))
    elif plan["shell"] == "outdoor":
        found = tuple(floor_faults(record, plan) + site_faults(record, plan))
    elif plan["walls"].get("shape") == "faceted":
        found = tuple(facet_faults(record, plan))
    elif plan["walls"].get("shape") == "tube":
        found = tuple(tube_faults(record, plan))
    elif plan["walls"].get("shape") == "flat":
        found = tuple(shell_faults(record, plan["walls"]) + door_faults(record, plan) +
                      roof_faults(record, plan["walls"]))
    else:
        found = tuple(shell_faults(record, plan["walls"]) + door_faults(record, plan))
    reason = "; ".join(found[:3]) if found else \
        f"shell, floor and {len(plan['doors'])} doors on the plan within {TOLERANCE} m"
    return checks.Verdict("plan-matched", checks.FAIL if found else checks.PASS, reason, {"faults": len(found)},
                          {"faults": "lower"}, found)


# --- openings ---------------------------------------------------------------------------------------------------

def stand_places(stage, place, entries, seeds):
    """The record's places, each its old stage referenced (the seed's), moved, turned and stretched as the record
    says, its own shared things inactive; door leaves left out (the doors judged open)."""
    from pxr import Gf, Sdf
    UsdGeom.Scope.Define(stage, f"/{place}/Places")
    for item in entries:
        if item.get("door_leaf"):
            continue
        xform = UsdGeom.Xform.Define(stage, f"/{place}/Places/{item['name']}")
        xform.GetPrim().GetReferences().AddReference(str(pathlib.Path(seeds) / item["stage"] / f"{item['stage']}.usda"))
        xform.AddTranslateOp().Set(Gf.Vec3d(*map(float, item["at"])))
        outside.scene_records.turn(xform, item)
        if "scale" in item:
            xform.AddScaleOp().Set(Gf.Vec3f(*map(float, item["scale"])))
        xform.GetPrim().CreateAttribute("score:place", Sdf.ValueTypeNames.String).Set(item["stage"])
        for shared in outside.NEIGHBOUR_SHARED:
            stage.OverridePrim(f"/{place}/Places/{item['name']}/{shared}").SetActive(False)


def bare_stage(place):
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, f"/{place}").GetPrim())
    return stage


def door_places(record, plan):
    """The record's places a doorway opens onto: each place of a stage a cut door leads to (a joined tube among them).
    The other places it shows are left out of the openings gate's stage: one only stands in a ray's way, so leaving it
    out can find more rays into nothing, never fewer, and loading every seated neighbour's whole stage took the
    workshop's record past the 8 GB a process may hold (2026-10-13)."""
    leads = {door["leads"] for door in plan["doors"] if door["cut"]}
    return [item for item in record.get("places", []) if item["stage"] in leads]


SEALED_LEAF = 0.05  # a shut leaf's thickness, for the rays


def sealed_leaves(plan):
    """A ground-free room's doors that lead `sealed` (the plan: its leaf stays shut until the next place is made) as a
    shut leaf each, a box filling the doorway, so its views are judged against its own closed walls."""
    found = []
    for number, door in enumerate(plan["doors"]):  # by number: two doors may share a side's name, or carry a level
        if door["leads"] != "sealed":
            continue
        normal = np.asarray(door["normal"], dtype=float)
        across = np.abs(np.array([normal[2], 0.0, normal[0]]))
        size = across * door["wide"] + np.abs(normal) * SEALED_LEAF + np.array([0.0, door["tall"], 0.0])
        centre = np.asarray(door["middle"], dtype=float) + np.array([0.0, door["level"] + door["tall"] / 2, 0.0])
        found.append({"name": f"sealed_leaf_{number}", "builder": "box", "centre": centre.tolist(),
                      "size": size.tolist(), "surface": "kit_floor"})
    return found


def composed(output, inputs):
    """The record's shell and places over the made ground, in the place's frame (a kit shell's own floors with them):
    (stage, laid ground or None)."""
    place, record = writer.record_in(output)
    stage = bare_stage(place)
    structure = record.get("structure", [])
    if plan_of(inputs)["shell"] == "kit":
        kit = json.loads((pathlib.Path(inputs["kits"]) / f"{place}.json").read_text())
        ground_free = bool(json.loads((pathlib.Path(inputs["plans"]) / f"{place}.json").read_text()).get("ground_free"))
        structure = structure + kit_shell.kit_floors(kit, every=ground_free)
        if ground_free:
            structure = structure + sealed_leaves(plan_of(inputs))
    for surface in {item["surface"] for item in structure if item.get("surface")}:
        UsdShade.Material.Define(stage, f"/{place}/Library/{surface}")  # bound only: rays see shapes, not paint
    outside.scene_records.write_structure(stage, place, structure, out=pathlib.Path(output))
    stand_places(stage, place, door_places(record, plan_of(inputs)), inputs["seeds"])
    seat = writer.seats(inputs).get(place)
    if seat is None:
        return stage, None
    kit = json.loads((pathlib.Path(inputs["kits"]) / f"{place}.json").read_text())
    zoned, laid = outside.meshes(seat.made, seat.entry, kit.get("on_seat", [0.0, 0.0]),
                                 ground_gates.footprint(record, kit))
    outside.write(stage, place, seat.made, zoned, laid, {**record, "places": []}, str)
    return stage, laid


def lead_faults(output, inputs, plan):
    """A door that leads to a place with no floor of that place's stage under the way out of its doorway (the places
    of that stage alone composed, a drop cast DOOR_OUT past the doorway's outer face)."""
    place, record = writer.record_in(output)
    found = []
    for door in plan["doors"]:
        if not door["cut"] or door["leads"] == "outside":
            continue
        shown = [item for item in record.get("places", []) if item["stage"] == door["leads"]]
        drop = np.inf
        if shown:  # with none, nothing to gather: its place is missing outright
            stage = bare_stage(place)
            stand_places(stage, place, shown, inputs["seeds"])
            seen = sight.gathered(stage)
            spot = writer.door_outside(door) + np.asarray(door["normal"], dtype=float) * ground_gates.DOOR_OUT
            if len(seen.faces):
                drop = ground_gates.drops(ground_gates.caster(seen), np.array([spot + [0.0, 1.0, 0.0]]),
                                          [0.0, -1.0, 0.0])[0] - 1.0
        if not drop <= ground_gates.DOOR_DROP:
            found.append(f"door {door['name']} ({door['what']}) leads to {door['leads']}, but no floor of "
                         f"{door['leads']} lies under the way out of it")
    return found


def ground_probes(rays, record, laid, up):
    """An outdoor place's viewers: a grid over its site at eye height over the made ground (the ball curves away
    under a level grid), each kept only over a floor within PROBE_FLOOR."""
    low, high = np.asarray(record["floor"], dtype=float)
    spots = np.array([laid.standing(across, along, ground_gates.PROBE_HEIGHT)[0]
                      for across in np.linspace(low[0] + 0.4, high[0] - 0.4, ground_gates.PROBE_GRID)
                      for along in np.linspace(low[1] + 0.4, high[1] - 0.4, ground_gates.PROBE_GRID)], dtype=float)
    floor = ground_gates.drops(rays, spots, -np.asarray(up, dtype=float))
    return spots[floor <= ground_gates.PROBE_FLOOR]


def measure_openings(output, inputs):
    """The composed record's doorways' floors and its void rays from inside, with the doors' leads."""
    place, record = writer.record_in(output)
    stage, laid = composed(output, inputs)
    seen = sight.gathered(stage)
    rays = ground_gates.caster(seen)
    up = (0.0, 1.0, 0.0)
    plan = plan_of(inputs)
    ways = ground_gates.shell_doors(record) + [
        {"door": f"door {door['name']} ({door['what']})", "middle": np.asarray(door["middle"], dtype=float),
         "normal": np.asarray(door["normal"], dtype=float)} for door in plan["doors"]
        if door["cut"] and (plan["shell"] == "kit" or plan["walls"].get("shape") in ("faceted", "tube"))]
    doors = ground_gates.door_floors(rays, ways, up)
    ball = ground_gates.ball_of(laid) if laid is not None else None
    spots = ground_gates.probes(rays, record, None, up)
    if plan["shell"] == "outdoor" and laid is not None:
        spots = np.concatenate([spots, ground_probes(rays, record, laid, up)])
    viewed = sight.voids(seen, spots, up, ball=ball)
    return {"doors": doors, "void_rays": viewed["void"], "rays": viewed["rays"], "probes": len(viewed["probes"]),
            "worst_probe": viewed["worst"], "ground": laid is not None,
            "leads": lead_faults(output, inputs, plan)}


def judge_openings(output, inputs, evidence):
    """Fail on a doorway onto nothing, a view that runs out below the horizon into nothing, a door whose place does
    not stand in it, or a place with no made ground under it."""
    measured = measure_openings(output, inputs)
    findings = [f"{door['door']} opens onto nothing (floor {door['drops']} m under the sill)"
                for door in measured["doors"] if door["open_onto_nothing"]]
    if measured["void_rays"]:
        findings.append(f"{measured['void_rays']} of {measured['rays']} view rays run out below the horizon into "
                        f"nothing (worst from {measured['worst_probe']['at']})")
    findings += measured["leads"]
    if not measured["ground"]:
        findings.append("no made ground seats this place: its outside cannot be judged")
    reason = "; ".join(findings[:3]) if findings else \
        (f"all {len(measured['doors'])} doorways open onto a floor, no view runs out into nothing "
         f"({measured['probes']} spots), every door's place lies past it")
    return checks.Verdict("openings", checks.FAIL if findings else checks.PASS, reason,
                          {"doors onto nothing": sum(door["open_onto_nothing"] for door in measured["doors"]),
                           "void rays": measured["void_rays"], "doors without their place": len(measured["leads"])},
                          {"doors onto nothing": "lower", "void rays": "lower", "doors without their place": "lower"},
                          tuple(findings))


# --- seed-matched -----------------------------------------------------------------------------------------------

def spot(item):
    """Where an entry stands: a view's eye, a light's or place's `at`, a placed shape's `placed_at`, else None."""
    for key in ("eye", "at", "placed_at", "centre"):
        if isinstance(item.get(key), list) and len(item[key]) == 3:
            return np.asarray(item[key], dtype=float)
    return None


def kind_of(section, item):
    return item.get("builder") or item.get("stage") or item.get("type") or section


def distance(item, other):
    """How far apart two entries stand (0 when either has no spot)."""
    here, there = spot(item), spot(other)
    return 0.0 if here is None or there is None else float(np.linalg.norm(there - here))


def near(item, other):
    """Whether two entries stand within MATCH_REACH of each other (either with no spot: yes)."""
    return distance(item, other) <= MATCH_REACH


def matches(section, seed, made):
    """Each seed entry of a section matched to an unused new entry of its kind, nearest first within MATCH_REACH
    (one with no spot to any of its kind), a seed entry naming an inventory row (`row`) first to one of that row, so
    a nearer entry with no row (a console's screen) never takes it: [(seed entry, new entry or None)]."""
    free = list(made)
    partners = {}
    for number, item in enumerate(seed):
        rowed = [other for other in free if item.get("row") and other.get("row") == item["row"]
                 and kind_of(section, other) == kind_of(section, item) and near(item, other)]
        if rowed:
            partners[number] = min(rowed, key=lambda other: distance(item, other))
            free.remove(partners[number])
    found = []
    for number, item in enumerate(seed):
        if number in partners:
            found.append((item, partners[number]))
            continue
        same = [other for other in free if kind_of(section, other) == kind_of(section, item)]
        here = spot(item)
        if here is not None:
            same = sorted((other for other in same if spot(other) is not None
                           and np.linalg.norm(spot(other) - here) <= MATCH_REACH),
                          key=lambda other: np.linalg.norm(spot(other) - here))
        partner = same[0] if same else None
        if partner is not None:
            free.remove(partner)
        found.append((item, partner))
    return found


def moved(name, seed, made):
    """Each number of a matched entry that moved past TOLERANCE: shown, not judged."""
    found = []
    for key, value in seed.items():
        other = made.get(key)
        if isinstance(value, (int, float)) and isinstance(other, (int, float)) and abs(value - other) > TOLERANCE:
            found.append(f"{name}.{key}: seed {value}, now {other}")
        elif isinstance(value, list) and isinstance(other, list) and len(value) == len(other) and \
                all(isinstance(number, (int, float)) for number in value + other) and \
                max(abs(a - b) for a, b in zip(value, other)) > TOLERANCE:
            found.append(f"{name}.{key}: seed {value}, now {other}")
    return found


def reason_for(name, place):
    """The writer's reason for leaving a seed entry out: the most specific SEED_REASONS key naming it (a section,
    `<section>/<name start>` for a family of entries, either kept to one place as `<place>:<key>`), or None."""
    def names(key):
        own, _, key = key.rpartition(":")
        return own in ("", place) and (name == key or name.startswith(key + "/") or
                                       (key.endswith("_") and name.startswith(key)))
    named = [key for key in SEED_REASONS if names(key)]
    return SEED_REASONS[max(named, key=len)] if named else None


def children_left(name, item, partner):
    """Each seed child of a matched entry its partner lacks (by model), named `<entry>/children/<model>`: a child
    dropped without a reason fails like any seed entry (the camp's rack cases, 2026-10-13)."""
    have = [pathlib.PurePosixPath(child["model"]).stem for child in partner.get("children", []) if "model" in child]
    left = []
    for child in item.get("children", []):
        stem = pathlib.PurePosixPath(child.get("model", "")).stem
        if stem and stem in have:
            have.remove(stem)
        elif stem:
            left.append(f"{name}/children/{stem}")
    return left


def seed_diff(seed, record, place=None):
    """Every seed entry matched or unmatched (with the writer's reason or none), and what moved."""
    matched, unmatched, shown = 0, [], []
    for section, value in seed.items():
        if section == "place":
            continue
        if isinstance(value, list) and value and isinstance(value[0], dict):
            for item, partner in matches(section, value, record.get(section, [])):
                name = f"{section}/{item.get('name', kind_of(section, item))}"
                if partner is None:
                    unmatched.append((name, reason_for(name, place)))
                else:
                    matched += 1
                    shown += moved(name, item, partner)
                    unmatched += [(left, reason_for(left, place)) for left in children_left(name, item, partner)]
        elif section in record:
            matched += 1
            if isinstance(value, dict):
                shown += moved(section, value, record[section])
                shown += moved(f"{section}.haze", value.get("haze") or {}, record[section].get("haze") or {})
            elif value != record[section]:
                shown.append(f"{section}: seed {json.dumps(value)[:80]}, now {json.dumps(record[section])[:80]}")
        else:
            unmatched.append((section, reason_for(section, place)))
    return matched, unmatched, shown


def judge_seed_matched(output, inputs, evidence):
    """Fail on a seed entry left out with no written reason."""
    place, record = writer.record_in(output)
    seed_path = pathlib.Path(inputs["seed record"])
    if not seed_path.exists():
        return checks.Verdict("seed-matched", checks.PASS, "the place had no old record", {"unmatched": 0},
                              {"unmatched": "lower"})
    matched, unmatched, shown = seed_diff(json.loads(seed_path.read_text()), record, place)
    faults = [f"{name}: left out with no reason" for name, why in unmatched if not why]
    findings = tuple(faults + [f"left out, {name}: {why}" for name, why in unmatched if why] +
                     [f"shown, not judged: {line}" for line in shown])
    reason = "; ".join(faults[:3]) if faults else \
        f"{matched} seed entries matched, {len(unmatched)} left out with their reasons"
    return checks.Verdict("seed-matched", checks.FAIL if faults else checks.PASS, reason,
                          {"unmatched": len(faults), "matched": matched, "moved": len(shown)},
                          {"unmatched": "lower"}, findings)


CHECKS = (checks.Check("game-free", judge_game_free), checks.Check("plan-matched", judge_plan_matched),
          checks.Check("openings", judge_openings), checks.Check("seed-matched", judge_seed_matched))
