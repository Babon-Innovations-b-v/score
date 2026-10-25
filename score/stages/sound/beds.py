"""A scene's bed (its room tone, or what the suit lets through outside where no air carries sound), worked out free
from its design alone, never from a list written per scene: where it is heard from its plan and the body it stands
on, then the library beds whose brief fits it.

    facts     how the scene is heard:
                heard      `room` (its plan is a room: not an outdoor shell, not `inside` false, and, for a top
                           scene, held by none and so standing on its site, `inside` true), `suit` (outside on
                           a body or plot whose surface pressure is under the Armstrong limit: a person there wears a
                           pressure suit and hears through it), else `open` (outside in air a person breathes)
                air        the outside air of the body it stands on: `sealed` under the Armstrong limit, else
                           `breathable`; the body is the site's (data/physics/setting.json `sites`) of the outside
                           place holding it (data/places/within.json: `within`, a part's `of`, a merged place's
                           `into`; else the design's plan that `holds` it: a scene added in the app), its surface pressure the setting's own value, else the cited reference table's
                           (data/physics/bodies.json `surface_pressure_kpa`)
                shell      `open` for a room whose plan's shell is outdoor (a shelter standing alone in the open),
                           else `built`
                grounded   false when its plan stands on no made ground (`ground_free`: a room inside a craft)
                shape      its plan's `shape` (a tube, a faceted hall)
                rows       its inventory rows' reading nouns (else names) and row kinds (score/stages/row_kinds.py)
    beds      the library beds whose brief's `bed` (data/sound/sounds.json) fits the facts: every fitting `layer`,
              and one `tone`: the first fitting one that asks more than how it is heard (a shell, ground, shape, noun
              or row kind), else the first fitting one that does not

A fact the design cannot give (no plan, no site's body above it, a body with no surface pressure) leaves the bed
undecided, named in `missing`: a gap, never a guess.
"""
import json
import os
import pathlib
import re

from score.stages import row_kinds

# Wikipedia, Armstrong limit (en.wikipedia.org/wiki/Armstrong_limit), read 2026-10-21: below 0.0618 atm (6.26 kPa)
# water boils at body temperature, so a person outside below it wears a pressure suit.
ARMSTRONG_KPA = 6.26
PLAYS = ("tone", "layer")
ASKS_MORE = ("shell", "grounded", "shape", "nouns", "kinds")
REPO = pathlib.Path(__file__).resolve().parents[3]
# The creator's design as the cockpit keeps it (score/stages/__init__.py creator_plan): his plan and scene inventory.
DESIGN = pathlib.Path(os.environ.get("PROPS_HOME", pathlib.Path.home() / ".farm-factory-props")) / "design"
FILES = {"setting": "{data}/physics/setting.json", "bodies": "{data}/physics/bodies.json",
         "holders": "{data}/places/within.json", "plans": "{home}/design/plans", "row kinds": "{data}/checks/row-kinds.json",
         "sounds": "{data}/sound/sounds.json"}


def files(place, design=DESIGN):
    """The bed's inputs as the stage table's patterns: the place's kept plan and scene inventory (the old data/plans
    and data/inventory records were retired, owner, 2026-10-21), and the setting, reference bodies, holders (within.json
    and the design's plans, whose `holds` name the scenes added in the app), row kinds and library briefs."""
    found = dict(FILES)
    if (design / "plans" / f"{place}.json").is_file():
        found["plan"] = "{home}/design/plans/{place}.json"
    if (design / "inventory" / f"{place}.json").is_file():
        found["scene inventory"] = "{home}/design/inventory/{place}.json"
    return found


def paths(place, data=REPO / "data", design=DESIGN):
    """The bed's inputs as paths (files)."""
    return {name: pathlib.Path(pattern.format(place=place, data=data, home=design.parent))
            for name, pattern in files(place, design).items()}


def places(design=DESIGN):
    """Every scene with a kept plan: the scenes a bed is worked out for."""
    return [path.stem for path in sorted((design / "plans").glob("*.json"))]


def read(path):
    """A JSON file's document, None when there is none."""
    path = pathlib.Path(path) if path else None
    return json.loads(path.read_text()) if path and path.is_file() else None


def words(text):
    """A noun as its words: lower case, a possessive's 's dropped, split on anything not a letter or digit."""
    return [word for word in re.split(r"[^a-z0-9]+", re.sub(r"'s\b", "", str(text or "").lower())) if word]


def holds(row_words, phrase):
    """Whether the phrase's words stand together, in order, in the row's words."""
    wanted = words(phrase)
    return bool(wanted) and any(row_words[at:at + len(wanted)] == wanted for at in range(len(row_words)))


def outside(plan, top):
    """Whether the plan's scene stands outside: an outdoor shell or a top scene (held by none, standing on its site:
    the Moon base round its modules) not marked inside, or marked not inside."""
    return plan.get("inside") is False or ((plan.get("shell") == "outdoor" or top) and plan.get("inside") is not True)


def site_place(place, holders):
    """The outside place whose site holds the place: up its holders (within, a part's `of`, a merged place's
    `into`, then the design's plan that holds it: `held`, held_by) to one held by none."""
    seen = []
    while place not in seen:
        seen.append(place)
        for table, key in (("within", "within"), ("parts", "of"), ("merged", "into"), ("held", "by")):
            if place in holders.get(table, {}):
                place = holders[table][place][key]
                break
        else:
            return place
    return None


def held_by(plans):
    """{scene: {"by": the scene whose design plan `holds` it}} of the design's plans folder; {} with none."""
    folder = pathlib.Path(plans) if plans else None
    if folder is None or not folder.is_dir():
        return {}
    return {hold["place"]: {"by": path.stem} for path in sorted(folder.glob("*.json"))
            for hold in (read(path) or {}).get("holds") or [] if hold.get("place") and hold["place"] != path.stem}


def surface_pressure(place, setting, reference, holders):
    """(the body or plot the place stands on, its surface pressure in kPa); either None when the design gives none."""
    top = site_place(place, holders)
    site = next((site for site in setting.get("sites", []) if site.get("place") == top), None)
    if site is None:
        return None, None
    ground = site.get("on")
    own = next((row for row in setting.get("bodies", []) + setting.get("plots", [])
                if ground in (row.get("body"), row.get("plot"))), {})
    real = reference.get("bodies", {}).get(own.get("reference") or ground, {}) if "plot" not in own else {}
    kpa = own.get("surface_pressure_kpa", real.get("surface_pressure_kpa"))
    return ground, kpa


def facts(place, plan, inventory, setting, reference, holders, kinds):
    """How the scene is heard (the module's `facts`), with `missing`: what the design does not give."""
    ground, kpa = surface_pressure(place, setting, reference, holders)
    found = {"body": ground, "missing": []}
    if plan is None:
        found["missing"].append("no plan of its own")
    if ground is None:
        found["missing"].append("no site in the setting holds it")
    elif kpa is None:
        found["missing"].append(f"{ground} has no surface pressure")
    else:
        found["air"] = "sealed" if kpa < ARMSTRONG_KPA else "breathable"
    if plan is not None:
        found["heard"] = ("room" if not outside(plan, site_place(place, holders) == place) else
                          None if kpa is None else "suit" if kpa < ARMSTRONG_KPA else "open")
        found["shell"] = "open" if plan.get("shell") == "outdoor" else "built"
        found["grounded"] = not plan.get("ground_free")
        found["shape"] = plan.get("shape")
    if kinds is None:
        found["missing"].append("no row-kinds table (data/checks/row-kinds.json)")
    rows = inventory.get("rows", [])
    found["rows"] = [words(row.get("noun") or row.get("name") or row.get("id")) for row in rows]
    found["kinds"] = sorted({kind for kind in (row_kinds.kind_of(row, kinds or {}) for row in rows) if kind})
    return found


def fits(bed, found):
    """Whether a brief's `bed` fits the scene's facts: how it is heard, and each further thing it asks."""
    if found.get("heard") is None or bed["heard"] != found["heard"]:
        return False
    if "air" in bed and bed["air"] != found.get("air"):
        return False
    if any(key in bed and bed[key] != found.get(key) for key in ("shell", "grounded")):
        return False
    if "shape" in bed and found.get("shape") not in bed["shape"]:
        return False
    if ("nouns" in bed or "kinds" in bed) and not (
            any(holds(row, noun) for row in found["rows"] for noun in bed.get("nouns", []))
            or set(bed.get("kinds", [])) & set(found["kinds"])):
        return False
    return True


def beds(found, briefs):
    """The bed's sounds, its tone first: [name], empty when undecided or when no library bed fits."""
    if found["missing"]:
        return []
    fitting = [(name, brief["pick"]["bed"]) for name, brief in briefs.items()
               if brief.get("pick", {}).get("bed") and fits(brief["pick"]["bed"], found)]
    tones = [name for name, bed in fitting if bed["plays"] == "tone" and any(key in bed for key in ASKS_MORE)] or \
            [name for name, bed in fitting if bed["plays"] == "tone"]
    return tones[:1] + [name for name, bed in fitting if bed["plays"] == "layer"]


def of_place(place, inputs):
    """The place's facts and its bed from the stage's inputs (files: `plan`, `scene inventory`, `setting`, `bodies`,
    `holders`, `plans`, `row kinds`, `sounds`): {"facts", "sounds"}."""
    holders = {**(read(inputs.get("holders")) or {}), "held": held_by(inputs.get("plans"))}
    found = facts(place, read(inputs.get("plan")), read(inputs.get("scene inventory")) or {},
                  read(inputs.get("setting")) or {}, read(inputs.get("bodies")) or {},
                  holders, (read(inputs.get("row kinds")) or {}).get("kinds"))
    return {"facts": found, "sounds": beds(found, (read(inputs.get("sounds")) or {}).get("sounds", {}))}
