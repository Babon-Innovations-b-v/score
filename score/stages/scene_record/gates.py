"""The scene-record stage's gates, each measured on the written record:

    game-free     no text of the record names a game file or the game's code (a Godot script or scene, a game path,
                  the game's class names): the record is made from the plan, never transcribed
    plan-matched  the shell is the plan's: inside, corners, walls' height and dome within TOLERANCE once the backing is
                  taken off, the floor box the plan's inside, every door the plan cuts cut at its wide and tall in its
                  wall's middle (room_walls cuts there only), every shut door uncut
    openings      every doorway leads somewhere: the record's shell with its places (each door's leaves left out, as
                  opened) composed over the made ground in the place's frame (terrain outside.py), every cut doorway
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
from score.stages.scene_record import writer
from score.stages.terrain import gates as ground_gates, outside, sight

# A game file or the game's code: a Godot script, scene or shader, a path into its tree, its shell class.
GAME = re.compile(r"\.(gd|tscn|tres|gdshader)\b|res://|(^|[\s(])(game|sim)/\w|ModuleShell|module_shell|2099")
# Plan numbers held within this (metres).
TOLERANCE = 0.05
# A matched entry stands this close to its seed (metres); a view's eye this close.
MATCH_REACH = 2.0
# What the writer leaves out of a record on purpose, by the old record's section.
SEED_REASONS = {
    "game_only": "the record holds no notes about the game: what the concept shows is an inventory row or a plan item",
}


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
    for builder, extra in (("room_walls", {"high": walls["high"]}), ("room_deck", {}),
                           ("dome_roof", {"eave": walls["high"], "rise": walls["rise"]})):
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


def judge_plan_matched(output, inputs, evidence):
    """Fail on a shell number or a door off the plan."""
    _, record = writer.record_in(output)
    plan = plan_of(inputs)
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


def composed(output, inputs):
    """The record's shell and places over the made ground, in the place's frame: (stage, laid ground or None)."""
    place, record = writer.record_in(output)
    stage = bare_stage(place)
    for surface in {item["surface"] for item in record.get("structure", []) if item.get("surface")}:
        UsdShade.Material.Define(stage, f"/{place}/Library/{surface}")  # bound only: rays see shapes, not paint
    outside.scene_records.write_structure(stage, place, record.get("structure", []), out=pathlib.Path(output))
    stand_places(stage, place, record.get("places", []), inputs["seeds"])
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
        stage = bare_stage(place)
        stand_places(stage, place, [item for item in record.get("places", []) if item["stage"] == door["leads"]],
                     inputs["seeds"])
        seen = sight.gathered(stage)
        spot = writer.door_outside(door) + writer.outward(door["side"]) * ground_gates.DOOR_OUT
        drop = np.inf if not len(seen.faces) else \
            ground_gates.drops(ground_gates.caster(seen), np.array([spot + [0.0, 1.0, 0.0]]), [0.0, -1.0, 0.0])[0] - 1.0
        if not drop <= ground_gates.DOOR_DROP:
            found.append(f"door {door['plan_side']} ({door['what']}) leads to {door['leads']}, but no floor of "
                         f"{door['leads']} lies under the way out of it")
    return found


def measure_openings(output, inputs):
    """The composed record's doorways' floors and its void rays from inside, with the doors' leads."""
    place, record = writer.record_in(output)
    stage, laid = composed(output, inputs)
    seen = sight.gathered(stage)
    rays = ground_gates.caster(seen)
    up = (0.0, 1.0, 0.0)
    doors = ground_gates.door_floors(rays, ground_gates.shell_doors(record), up)
    ball = ground_gates.ball_of(laid) if laid is not None else None
    viewed = sight.voids(seen, ground_gates.probes(rays, record, None, up), up, ball=ball)
    return {"doors": doors, "void_rays": viewed["void"], "rays": viewed["rays"], "probes": len(viewed["probes"]),
            "worst_probe": viewed["worst"], "ground": laid is not None,
            "leads": lead_faults(output, inputs, plan_of(inputs))}


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
    """Where an entry stands: a view's eye, a light's or place's `at`, else None."""
    for key in ("eye", "at", "centre"):
        if isinstance(item.get(key), list) and len(item[key]) == 3:
            return np.asarray(item[key], dtype=float)
    return None


def kind_of(section, item):
    return item.get("builder") or item.get("stage") or item.get("type") or section


def matches(section, seed, made):
    """Each seed entry of a section matched to an unused new entry of its kind, nearest first within MATCH_REACH
    (one with no spot to any of its kind): [(seed entry, new entry or None)]."""
    free = list(made)
    found = []
    for item in seed:
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


def seed_diff(seed, record):
    """Every seed entry matched or unmatched (with the writer's reason or none), and what moved."""
    matched, unmatched, shown = 0, [], []
    for section, value in seed.items():
        if section == "place":
            continue
        if isinstance(value, list) and value and isinstance(value[0], dict):
            for item, partner in matches(section, value, record.get(section, [])):
                name = f"{section}/{item.get('name', kind_of(section, item))}"
                if partner is None:
                    unmatched.append((name, SEED_REASONS.get(section)))
                else:
                    matched += 1
                    shown += moved(name, item, partner)
        elif section in record:
            matched += 1
            if isinstance(value, dict):
                shown += moved(section, value, record[section])
                shown += moved(f"{section}.haze", value.get("haze") or {}, record[section].get("haze") or {})
            elif value != record[section]:
                shown.append(f"{section}: seed {json.dumps(value)[:80]}, now {json.dumps(record[section])[:80]}")
        else:
            unmatched.append((section, SEED_REASONS.get(section)))
    return matched, unmatched, shown


def judge_seed_matched(output, inputs, evidence):
    """Fail on a seed entry left out with no written reason."""
    _, record = writer.record_in(output)
    seed_path = pathlib.Path(inputs["seed record"])
    if not seed_path.exists():
        return checks.Verdict("seed-matched", checks.PASS, "the place had no old record", {"unmatched": 0},
                              {"unmatched": "lower"})
    matched, unmatched, shown = seed_diff(json.loads(seed_path.read_text()), record)
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
