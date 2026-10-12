"""The cast stage (experimental, design 5 of 2026-10-12, until the owner reviews it): the people a place's concept
shows, each placed in the place with a clip, and measured against the concept and the place's geometry.

    make     the place's cast (`data/characters/<place>.json`, the record tools/characters/cast.py reads) dealt into
             its characters by cast.py's own rules (people, a group's members, a crowd's copies), each with its
             spot, clip, look and the body it would play: the look's made model when the people route
             (issue #5, `PROP_PEOPLE`) has one, else today's built body (`cast.BODIES`); `cast.json`. Then every
             spot measured on the seed's base layer (measure.py): what it stands on and what its body runs into;
             `measures.json`.
    gates    counted   the cast holds as many people as the concept shows (concept_people's count, the most any one
                       view shows); a view with KEEP figures is capped, so there the cast holds at least
                       that many; a different count passes only with the record's written `count_reason`
             standing  everyone stands on something solid: the first solid under their knee within STAND_SLACK of
                       their feet, not in water (a seated person sits on a seat the same way: no clip sits on a chair
                       yet, so seated crew stand at their desks)
             clear     no person's body (knee to head, cast_check's BODY_RADIUS) runs into any solid of the place,
                       no two bodies overlap, and cast_check's own rules hold (nobody twice, walks clear)
             made      every look is a made model of the people route: a take under PROP_PEOPLE/<person>/<outfit>
                       with its built body and a checks.txt with no FAIL
             drapes    no person plays a body in drapes the owner rejected (the Newton drapes, 2026-10-10) or whose
                       simulator's licence is not commercial-OK (people/cloth_licence.py)

Only places whose concept shows people (PLACES) have the row. Nothing reads its output yet: the characters layer is
written from it once every look is made (the people agent's route), and the assembly takes that layer then.
"""
import json
import os
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))  # already on it by the assembly's import
import stage_inputs  # noqa: E402

from score.stages.cast import measure, spread  # noqa: E402

# Places whose concept shows people (concept_people's accepted count, 2026-10-12). The greenhouse's people are the
# greenhouse crops-and-people line's (design D, 2026-10-12).
PLACES = ("airlock", "camp", "flat", "garage", "habitat", "hangar", "hub", "lab", "square", "stairwell", "street",
          "tube", "workshop")
# Where the people route (issue #5: Pixal3D's mesh, library clothing, faces, SOMA-X rig) lands each take.
PROP_PEOPLE = pathlib.Path(os.environ.get("PROP_PEOPLE",
                                          pathlib.Path.home() / ".farm-factory-motion/candidates/prop-people"))
# The most figures concept_people keeps a picture (tools/props/scene/box_masks.py KEEP, which imports torch, so
# not imported here; cast_test.py checks the two agree): a view with this many is capped.
KEEP = 5
# Today's built bodies (tools/characters/cast.py's BODIES, not imported at load: measure.characters).
BODIES = pathlib.Path(os.environ.get("MOTION_WORK", pathlib.Path.home() / ".farm-factory-motion/work")) / "bodies"
# How far feet may stand off what is under them, metres: the floor's own unevenness, not a float or a sink.
STAND_SLACK = 0.05
# The drape simulators a body may ship in: people/cloth_licence.py's COMMERCIAL less Newton, whose drapes the owner
# rejected (2026-10-10). Not imported from there: its folder on the path would put its paths.py into every other
# stage's code version. cast_test.py checks the two agree.
SHIPPABLE = ("Blender",)
# Faults named on the review page, at most this many a gate (a crowd's thousands are counted, not listed).
NAMED = 20


def takes_text(folder):
    """The part of the people route's folder the stage reads: each take's checks and built bodies."""
    lines = []
    for checked in sorted(pathlib.Path(folder).glob("*/*/checks/checks.txt")):
        take = checked.parents[1]
        bodies = sorted(path.name for path in (take / "out").glob("*.glb"))
        lines.append(f"{take.relative_to(folder)} {bodies}\n{checked.read_text()}")
    return "\n".join(lines)


def reports_text(folder):
    """The part of today's bodies folder the stage reads: each built body's report."""
    return "\n".join(f"{path.name}\n{path.read_text()}" for path in sorted(pathlib.Path(folder).glob("*.json")))


def files(place):
    """The place's cast record, its kit (which inventory's concept it is), its seed stage, the people route's takes,
    today's bodies' reports, and cast.py's and cast_check.py's code (imported only inside the make and the gates, so
    the code version does not follow them: measure.characters)."""
    return {"record": "{data}/characters/{place}.json", "kit": "{data}/kit/{place}.json",
            "seed": "{seeds}/usd-r3/{place}", "takes": (str(PROP_PEOPLE), takes_text),
            "bodies": (str(BODIES), reports_text), "cast rules": "{repo}/tools/characters/cast.py",
            "cast check": "{repo}/tools/characters/cast_check.py"}


def read_json(path):
    return json.loads(pathlib.Path(path).read_text())


# --- who: each character's look and the body it plays --------------------------------------------------------------

def look_of(character):
    """The look (person, outfit) a character wears, or None when its record names none: a named look
    (`bram_work`), or a kit mix's outfit (`plain_jacket_blue` worn: jacket-blue), or the crowd's far body."""
    if character.get("look"):
        return character["character"], character["look"].removeprefix(f"{character['character']}_")
    worn = character.get("worn") or []
    outfit = next((part for part in worn if part.startswith(("plain_", "work_"))), None)
    if outfit:
        return character["character"], outfit.removeprefix("plain_").replace("_", "-")
    return None


def made_take(look, folder):
    """The people route's take of a look when it is made: its built body there and a checks.txt with no FAIL."""
    if look is None:
        return None
    take = pathlib.Path(folder) / look[0] / look[1]
    checked = take / "checks/checks.txt"
    bodies = sorted((take / "out").glob("*.glb"))
    if not checked.exists() or not bodies or any(line.rstrip().endswith("FAIL")
                                                 for line in checked.read_text().splitlines()):
        return None
    return str(bodies[0])


def dealt(record, takes):
    """Every single character of the cast (cast.py's people and groups' members) with its look and body."""
    found = []
    looks = {person["name"]: person.get("look") for person in record.get("people", [])}
    cast_rules, _ = measure.characters()
    for single in cast_rules.characters_of(record):
        single = dict(single, look=looks.get(single["name"]))
        look = look_of(single)
        found.append({**single, "look": "/".join(look) if look else None, "made": made_take(look, takes)})
    return found


def crowd_of(record, singles, takes):
    """The crowd's far body's look and its candidate copies (spread.lattice), or None for a cast with no crowd."""
    crowd = record.get("crowd")
    if not crowd:
        return None
    keep_clear = [single["at"] for single in singles if single["name"].startswith(crowd.get("keep_clear_of", "\0"))]
    look = (crowd["character"], crowd.get("body", "far"))
    candidates = spread.lattice(crowd, keep_clear)
    return {"name": crowd["name"], "character": crowd["character"], "look": "/".join(look),
            "made": made_take(look, takes), "doing": crowd["doing"], "asked": crowd["count"], "copies": candidates}


def members_of(record):
    """The names cast.py gives its groups' members."""
    return {f"{group['name']}_{number}" for group in record.get("groups", []) for number in range(group["count"])}


def concept_count(counts, inventory):
    """The concept's people for one inventory: the most any one view shows, whether a view is capped at KEEP
    figures, and each view's count; None when concept_people measured none of its views."""
    views = counts.get(inventory)
    if not views:
        return None
    return {"people": max(view["people"] for view in views.values()),
            "capped": any(len(view["instances"]) >= KEEP for view in views.values()),
            "views": {name: view["people"] for name, view in views.items()}}


def make(inputs, out, seed, params):
    """The place's cast dealt into its characters, its groups and crowd stood on the place (spread.py; `cast.json`),
    and every body measured on its seed's base layer (`measures.json`)."""
    place = pathlib.Path(inputs["seed"]).name
    base = pathlib.Path(inputs["seed"]) / "layers/base.usda"
    record = read_json(inputs["record"])
    singles = dealt(record, inputs["takes"])
    crowd = crowd_of(record, singles, inputs["takes"])
    found = measure.solids(base, place) if singles or crowd else {}
    if found:
        members = members_of(record)
        singles, copies = spread.stand_every(singles, members, crowd["copies"] if crowd else [],
                                             crowd["asked"] if crowd else 0, found)
        left_out = sorted(members - {single["name"] for single in singles})
        crowd = dict(crowd, copies=copies) if crowd else None
    inventory = stage_inputs.inventory_path(place).stem
    concept = concept_count(read_json(pathlib.Path(inputs["concept_people"]) / "people.json"), inventory)
    cast = {"place": place, "inventory": inventory, "from": record.get("from"), "note": record.get("note"),
            "count_reason": record.get("count_reason"), "concept": concept, "characters": singles,
            "left_out": left_out if found else [], "crowd": crowd}
    (out / "cast.json").write_text(json.dumps(cast, indent=1))
    (out / "measures.json").write_text(json.dumps(measured(record, singles, crowd, found, base, place), indent=1))


def body_spots(singles, crowd):
    """(name, spot, clip) of every body to measure: each person at their spot or every WALK_STEP along their walk,
    and each crowd copy."""
    spots = [(single["name"], spot, single["doing"]) for single in singles
             for spot in (measure.walk_spots(single["path"]) if single.get("path") else [single["at"]])]
    return spots + ([(f"{crowd['name']}_{number}", copy["at"], crowd["doing"][copy["clip"]])
                     for number, copy in enumerate(crowd["copies"])] if crowd else [])


def measured(record, singles, crowd, found, base, place):
    """Every body's ground and clashes on the seed's base layer, the bodies that overlap, and the cast check's faults
    against its things (nobody twice, walks clear; on the record's own spots)."""
    spots = body_spots(singles, crowd)
    if not spots:
        return {"bodies": [], "overlaps": [], "cast_check": []}
    grounds = measure.ground_under([spot for _, spot, _ in spots], found)
    clashes = measure.run_into([spot for _, spot, _ in spots], found, [measure.top_of(doing) for _, _, doing in spots])
    bodies = [{"name": name, "at": [round(value, 3) for value in spot], "doing": doing, **ground, "into": into}
              for (name, spot, doing), ground, into in zip(spots, grounds, clashes)]
    return {"bodies": bodies, "overlaps": overlaps(singles, crowd),
            "cast_check": checked_cast(record, base, place)}


def checked_cast(record, base, place):
    """tools/characters/cast_check.py's faults of the record against the base layer's things."""
    _, cast_check = measure.characters()
    return cast_check.check(record, cast_check.stage_things(base, place))


def overlaps(singles, crowd):
    """Pairs of standing bodies whose middles are nearer than two body widths on the same level."""
    named = [(name, at) for name, at, _ in body_spots([single for single in singles if not single.get("path")], crowd)]
    if len(named) < 2:
        return []
    spots = np.array([at for _, at in named], dtype=float)
    pairs = cKDTree(spots[:, [0, 2]]).query_pairs(2 * measure.BODY_RADIUS)
    return sorted([named[first][0], named[second][0]] for first, second in pairs
                  if abs(spots[first][1] - spots[second][1]) < measure.KNEE)


def cast_faults(folder):
    """Why a folder is not a cast: its files missing, or a character with no clip."""
    if not (folder / "cast.json").exists() or not (folder / "measures.json").exists():
        return ["no cast.json and measures.json"]
    cast = read_json(folder / "cast.json")
    return [f"{single['name']} has no clip" for single in cast["characters"] if not single.get("doing")]


CAST = contracts.Contract("cast", 1, cast_faults, units={"length": "metre"})


# --- the gates ----------------------------------------------------------------------------------------------------

def head_count(cast):
    return len(cast["characters"]) + (len(cast["crowd"]["copies"]) if cast["crowd"] else 0)


def short_of(cast):
    """What the record asked for that did not fit on the place: group members left out, crowd copies short."""
    short = [f"{len(cast['left_out'])} group members left out ({', '.join(cast['left_out'][:NAMED])})"
             ] if cast["left_out"] else []
    crowd = cast["crowd"]
    if crowd and len(crowd["copies"]) < crowd["asked"]:
        short.append(f"{len(crowd['copies'])} of the crowd's {crowd['asked']} fit")
    return short


def judge_counted(output, inputs, evidence):
    """The cast holds the people the concept shows, and everyone its record asks for fits on the place."""
    cast = read_json(output / "cast.json")
    concept, held = cast["concept"], head_count(cast)
    if concept is None:
        return checks.Verdict("counted", checks.UNKNOWN, f"concept_people measured no view of {cast['inventory']}")
    shown, short = concept["people"], short_of(cast)
    fits = held == shown or (concept["capped"] and held >= shown)
    measures = {"cast": held, "concept": shown, "capped": int(concept["capped"])}
    said = (f"the cast holds {held}, the concept shows {'at least ' if concept['capped'] else ''}{shown} "
            f"{concept['views']}") + "".join(f"; {words}" for words in short)
    if fits and not short:
        return checks.Verdict("counted", checks.PASS, said, measures)
    if cast.get("count_reason") and not short:
        return checks.Verdict("counted", checks.PASS, f"{said}; the record's reason: {cast['count_reason']}", measures)
    return checks.Verdict("counted", checks.FAIL, said + ("" if fits else ", and the record gives no count_reason"),
                          measures, findings=tuple(short))


def counted_faults(bodies, fault_of):
    """Names and words of every body `fault_of` finds a fault in (None for none)."""
    return [(body["name"], words) for body in bodies for words in [fault_of(body)] if words]


def verdict_of(name, faults, total, passed):
    """A gate's verdict from its faults: (name, words) pairs, at most NAMED of them in words."""
    people = sorted({who for who, _ in faults})
    if not faults:
        return checks.Verdict(name, checks.PASS, passed, {"faults": 0, "bodies": total}, {"faults": "lower"})
    shown = [f"{who}: {words}" for who, words in faults[:NAMED]]
    more = f" (and {len(faults) - NAMED} more)" if len(faults) > NAMED else ""
    return checks.Verdict(name, checks.FAIL, f"{len(people)} of {total} people: " + "; ".join(shown) + more,
                          {"faults": len(faults), "bodies": total}, {"faults": "lower"}, tuple(shown))


def off_ground(body):
    """What is wrong with where a body's feet are, or None."""
    if body["gap"] is None:
        return f"nothing solid under their feet within {measure.LOOK_DOWN} m"
    if body["water"]:
        return "standing in the water"
    if abs(body["gap"]) > STAND_SLACK:
        return f"feet {body['gap']:+.2f} m off {body['on']}"
    return None


def judge_standing(output, inputs, evidence):
    """Everyone stands on something solid."""
    bodies = read_json(output / "measures.json")["bodies"]
    return verdict_of("standing", counted_faults(bodies, off_ground), len(bodies),
                      f"all {len(bodies)} body spots stand on something solid within {STAND_SLACK} m")


def judge_clear(output, inputs, evidence):
    """No body runs into the place's solids or another body, and cast_check's rules hold."""
    found = read_json(output / "measures.json")
    faults = counted_faults(found["bodies"], lambda body: body["into"] and "runs into " + ", ".join(body["into"]))
    faults += [(pair[0], f"overlaps {pair[1]}") for pair in found["overlaps"]]
    faults += [("cast check", words) for words in found["cast_check"]]
    lying = [body["name"] for body in found["bodies"] if body["into"] is None]
    if lying and not faults:
        return checks.Verdict("clear", checks.UNKNOWN, f"{len(lying)} lying bodies are not measured: "
                              + ", ".join(lying[:NAMED]), {"faults": 0, "unmeasured": len(lying)})
    return verdict_of("clear", faults, len(found["bodies"]),
                      f"no body of {len(found['bodies'])} runs into a solid or another, and the cast check passes")


def judge_made(output, inputs, evidence):
    """Every look is a made model of the people route."""
    cast = read_json(output / "cast.json")
    everyone = cast["characters"] + ([cast["crowd"]] if cast["crowd"] else [])
    faults = [(who["name"], f"{who['look']} has no made take under {PROP_PEOPLE}" if who["look"]
               else "its record names no look (which outfit)") for who in everyone if not who["made"]]
    return verdict_of("made", faults, len(everyone), f"all {len(everyone)} looks are made models")


def rejected(report):
    """The drapes of a body's report the owner rejected or whose licence does not allow shipping."""
    return [f"{kind} hung by {simulator.get('name')}" for kind, simulator in sorted((report.get("drapes") or {}).items())
            if not simulator.get("name", "").startswith(SHIPPABLE)]


def judge_drapes(output, inputs, evidence):
    """No one plays a body in rejected drapes: everyone not on a made take plays today's body, whose drapes count."""
    cast = read_json(output / "cast.json")
    everyone = cast["characters"] + ([cast["crowd"]] if cast["crowd"] else [])
    faults = []
    for who in everyone:
        report = pathlib.Path(inputs["bodies"]) / f"{who['character']}.json"
        if who["made"] or not report.exists():
            continue
        found = rejected(read_json(report))
        if found:
            faults.append((who["name"], f"plays today's {who['character']} body: " + ", ".join(found)))
    return verdict_of("drapes", faults, len(everyone), f"none of {len(everyone)} plays a body in rejected drapes")


CHECKS = (checks.Check("counted", judge_counted), checks.Check("standing", judge_standing),
          checks.Check("clear", judge_clear), checks.Check("made", judge_made), checks.Check("drapes", judge_drapes))
