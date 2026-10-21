"""The cast stage (experimental, design 5 of 2026-10-12, until the owner reviews it): the people a place's concept
shows, each placed in the place with a clip, and measured against the concept and the place's geometry.

    make     the place's cast from its picked design (data/people/rows.json, score/stages/people_rows.py: its scene
             inventory's people rows, each person a look of the shared people line, at the plan's people spots in
             turn and stood clear round them; a crowd one far look in its palettes, #26), never the old game records
             or the lost concept pictures, dealt by cast.py's own rules, each with its
             spot, clip, look and whether it is made: its look's dress row (people-dress-<look>, `-in-<surface>`
             where its design row wears a fabric of its own) stands usable, read as an optional input; `cast.json`. Then every
             spot measured on the seed's base layer (measure.py): what it stands on and what its body runs into;
             `measures.json`.
    gates    counted   the cast holds as many people as the design shows (its rows' counts), everyone fits on the
                       place, and a crowd stands on its ground as many as it asks (a design's: the plan items its
                       row makes, its count SAM 3's instances, else as many as its ground holds packed; a crowd row
                       with no plan item is named short)
             standing  everyone stands on something solid: the first solid under their knee within STAND_SLACK of
                       their feet, not in water (a seated person sits on a seat the same way: no clip sits on a chair
                       yet, so seated crew stand at their desks)
             clear     no person's body (knee to head, cast_check's BODY_RADIUS) runs into any solid of the place,
                       no two bodies overlap, and cast_check's own rules hold (nobody twice, walks clear)
             made      which looks have a usable dressed body of the SOMA-shell route (its dress row passed and stands
                       accepted); a look with none is an accepted gap, never a stop: the gate passes with it as a finding,
                       the characters layer names it, complete's people check fails it

`drapes` (no body in the rejected Newton drapes) is retired, 2026-10-13: the SOMA-shell rig (the owner, 2026-10-12
21:40) replaced the drapes route, and the people rows' per-clip, shell and outline gates judge the cloth now.

Only places whose design shows people (a row that acts: score/stages/design_layers.py) have the row. The characters layer (layer.py) reads its output and lays each person whose look's dressed body stands usable.
"""
import json
import pathlib
import sys

import numpy as np
from scipy.spatial import cKDTree

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))  # already on it by the assembly's import

from score.stages import people_rows  # noqa: E402
from score.stages.cast import layer, measure, spread  # noqa: E402
from score.stages.scene_record import writer  # noqa: E402

# How far feet may stand off what is under them, metres: the floor's own unevenness, not a float or a sink.
STAND_SLACK = 0.05
# Faults named on the review page, at most this many a gate (a crowd's thousands are counted, not listed).
NAMED = 20


def files(place):
    """The place's people from its picked design (its entry of data/people/rows.json, #26, what each row wears among
    it: which dress row a look is), its seed stage, the environment's eye height (its views') and cast.py's and
    cast_check.py's code (imported only inside the make and the gates, so the code version does not follow them:
    measure.characters). Its views are its plan's (the plan row's output, an `after`: plan_views)."""
    return {"design": ("{data}/people/rows.json", people_rows.place_part(place)),
            "seed": "{seeds}/usd-r3/{place}",
            "places": "{data}/definitions/place.json", "cast rules": "{repo}/tools/characters/cast.py",
            "cast check": "{repo}/tools/characters/cast_check.py"}


def plan_views(inputs):
    """The views of the place's plan (the plan row's plan.json, metres in the place's frame), as the scene record
    writes them (scene_record.writer.views): one inside each door looking across and one from each of the plan's
    standing spots, each eye at the environment's eye height over its level; an outdoor plan's from its standing spots
    only, over the plan's own level (the made ground's rise under a spot is not the plan's). None for a place with no
    plan row (Runner.reads leaves it out), so no copy is kept off a view. A standing spot looking at something the
    plan's items do not hold (the camp's, at its kit's objects) is refused by name: its view has no aim."""
    if "plan" not in inputs:
        return []
    plan = read_json(pathlib.Path(inputs["plan"]) / "plan.json")
    items = {item["name"] for item in plan["items"]}
    unaimed = [spot["looks_at"] for spot in plan["standing"] if spot["looks_at"] and spot["looks_at"] not in items]
    if unaimed:
        raise ValueError(f"plan of {plan.get('place')}: standing spots look at {unaimed}, which are no plan items")
    eye = read_json(inputs["places"])["shared"]["scale"]["eye_height"]
    return writer.views(plan if plan["inside"] else dict(plan, doorways=[]), eye)


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


def made_row(look, surface, inputs):
    """The dress row of a look worn in its row's fabric (layer.body_row) when it stands usable for this node (an
    optional input the runner gave it), else None: the look is not made."""
    row = layer.body_row("/".join(look), surface) if look else None
    return row if row in inputs else None


def dealt(record, inputs):
    """Every single character of the cast (cast.py's people and groups' members) with its look, the fabric its design
    row wears and its made dress row (None when not made)."""
    found = []
    people = {person["name"]: person for person in record.get("people", [])}
    cast_rules, _ = measure.characters()
    for single in cast_rules.characters_of(record):
        person = people.get(single["name"], {})
        single = dict(single, look=person.get("look"), surface=person.get("surface"))
        look = look_of(single)
        found.append({**single, "look": "/".join(look) if look else None,
                      "made": made_row(look, single["surface"], inputs)})
    return found


def crowd_of(record, singles, inputs):
    """The crowd's far body's look and its candidate copies (spread.lattice, kept off each of the place's plan's views:
    spread.far_enough), or None for a cast with no crowd. The views are read only for a crowd with ground to stand
    on, so a place with none never reads them."""
    crowd = record.get("crowd")
    if not crowd:
        return None
    keep_clear = [single["at"] for single in singles if single["name"].startswith(crowd.get("keep_clear_of", "\0"))]
    look = look_of(crowd) or (crowd["character"], crowd.get("body", "far"))  # the record's far-only look
    # a design's crowd with no plan item has no ground (people_rows.cast_record): none stood, short_of names it
    candidates = (spread.far_enough(spread.lattice(crowd, keep_clear), plan_views(inputs))
                  if crowd.get("spread") else [])
    return {"name": crowd["name"], "character": crowd["character"], "look": "/".join(look),
            "made": made_row(look, None, inputs), "doing": crowd["doing"], "asked": asked_of(crowd, candidates),
            "grounds": crowd.get("grounds"), "copies": candidates}


def asked_of(crowd, candidates):
    """How many copies the crowd asks for: its count, else (a design's crowd SAM 3 saw as one mass) every candidate
    of its ground, packed; None with no ground."""
    if crowd.get("count") is not None:
        return crowd["count"]
    return len(candidates) if crowd.get("spread") else None


def members_of(record):
    """The names of the people stood round a spot: a design's every person (each dealt to a plan people spot in
    turn), and cast.py's groups' members."""
    return ({person["name"] for person in record.get("people", [])}
            | {f"{group['name']}_{number}" for group in record.get("groups", []) for number in range(group["count"])})


def design_count(place, found):
    """The people the picked design shows (its scene inventory's people rows' counts); with a crowd row at least
    those (`capped`: the crowd's copies stand on top, short_of judges their count)."""
    shown = len(people_rows.persons(place, found))
    return {"people": shown, "capped": people_rows.crowd_row(place, found) is not None, "views": {"design": shown}}


def make(inputs, out, seed, params):
    """The place's cast dealt into its characters, its people and crowd stood on the place (spread.py; `cast.json`),
    and every body measured on its seed's base layer (`measures.json`)."""
    place = pathlib.Path(inputs["seed"]).name
    base = pathlib.Path(inputs["seed"]) / "layers/base.usda"
    design = read_json(inputs["design"])
    record = people_rows.cast_record(place, design)
    singles = dealt(record, inputs)
    crowd = crowd_of(record, singles, inputs)
    found = measure.solids(base, place) if singles or crowd else {}
    if found:
        members = members_of(record)
        singles, copies = spread.stand_every(singles, members, crowd["copies"] if crowd else [],
                                             crowd["asked"] or 0 if crowd else 0, found)
        left_out = sorted(members - {single["name"] for single in singles})
        crowd = dict(crowd, copies=copies) if crowd else None
    cast = {"place": place, "inventory": place, "from": record.get("from"), "note": record.get("note"),
            "count_reason": record.get("count_reason"), "concept": design_count(place, design), "characters": singles,
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
            "cast_check": checked_cast(record)}


def checked_cast(record):
    """tools/characters/cast_check.py's people faults of the record: nobody twice, no walk through a person. Its walk
    against things is left out: it tests each thing's box, so a walk through a ring (the tube's hoops) runs into the
    box round it; the bodies' own triangle test (measure.run_into, every WALK_STEP along a walk) judges things."""
    _, cast_check = measure.characters()
    return cast_check.check(record, [])


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
    if crowd and crowd["asked"] is None and crowd.get("grounds") is None:
        short.append(f"the crowd's ground is not read from the plan yet: refresh data/people/rows.json "
                     f"(python -m score.stages.people_rows) ({crowd['look']})")
    elif crowd and crowd["asked"] is None:
        short.append(f"the crowd's row makes no item on the plan, so it has no ground ({crowd['look']})")
    elif crowd and len(crowd["copies"]) < crowd["asked"]:
        short.append(f"{len(crowd['copies'])} of the crowd's {crowd['asked']} fit")
    return short


def judge_counted(output, inputs, evidence):
    """The cast holds the people the concept shows, and everyone its record asks for fits on the place."""
    cast = read_json(output / "cast.json")
    concept, held = cast["concept"], head_count(cast)
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
    """Which looks have a usable dressed body (its dress row passed and stands accepted). A look without one is a
    accepted gap carried down, never a stop: the cast passes with each gap as a finding, the characters layer leaves
    that person out and names them, and complete's people check fails each gap by name (the owner's rule of
    2026-10-13: a place whose people fail ships with the people as a named fail; nothing waits on them)."""
    cast = read_json(output / "cast.json")
    everyone = cast["characters"] + ([cast["crowd"]] if cast["crowd"] else [])
    missing = tuple(f"{who['name']}: " + (f"{who['look']} has no accepted dressed body (its people-dress row)"
                                          if who["look"] else "its record names no look (which outfit)")
                    for who in everyone if not who["made"])
    if missing:
        return checks.Verdict("made", checks.PASS, f"{len(everyone) - len(missing)} of {len(everyone)} looks made; "
                              f"{len(missing)} named missing, for complete's people check to fail",
                              {"missing": len(missing), "bodies": len(everyone)}, {"missing": "lower"}, missing)
    return checks.Verdict("made", checks.PASS, f"all {len(everyone)} looks have accepted dressed bodies",
                          {"missing": 0, "bodies": len(everyone)}, {"missing": "lower"})


CHECKS = (checks.Check("counted", judge_counted), checks.Check("standing", judge_standing),
          checks.Check("clear", judge_clear), checks.Check("made", judge_made))
