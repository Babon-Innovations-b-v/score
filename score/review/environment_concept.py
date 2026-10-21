"""The environment concept (CONTEXT.md "environment concept", the owner 2026-10-21): what the creator locks down for a
whole environment before any place is drawn: its style line, its setting (score/review/setting.py: what everything
stands on and in, a plot of ground, one world or several bodies that move one another, real bodies' values from the
cited reference table, and each top place's site on it), his reference pictures and what each is for, its first places and the places each may hold. Made
in a set interview in the creator cockpit (QUESTIONS, one at a time, each answer one direct Gemini 3.1 Pro call inside
his yes for it, `ask`), then locked by him.

The store keeps it, versioned, written only in the owner's process (concepts.recorded, the store's own barrier):

    environment-concept/<world>/versions/<time>.json  {world, concept {style, setting, references, places}, locked,
                                                       by, at}
    environment-concept/<world>/asks/<time>.json      {world, topic, question, answer, proposed, euros, yes, by, at}

With no version kept, the environment's concept is today's data (`prefilled`: the style line of
data/definitions/concept_views.json, the references of data/places/concept_inputs.json, the setting of
data/physics/setting.json, the outside places and what each holds from
data/places/within.json), shown as locked, so no draw already made moves. A locked version is what every place's
concept draw reads (`in_force`: its style line and references; score/review/concepts.py), and its places and what
each may hold are the starting proposal of within.json (`places_in_force`). A version kept before settings existed
reads today's setting (`with_setting`). Every draw and pick records the version it
was made under (`version`, the newest version's time); unlocking writes a new version, so every place's concept made
under the old one is out of date, and none is drawn or picked while it is unlocked (`unlocked`).

A reference picture he adds goes into the private bucket's references/ (content-addressed, named in its index.json)
and its local copy under {home}/references, never this public repository (`kept_reference`).

One ask runs as its own process inside the owner's yes for exactly that call (score.review.web.environment_ask):

    SCORE_SPEND_TICKET="override <key>" python -m score.review.environment_concept <world> <request.json> <by>

`request.json` is {topic, answer, concept (the concept as his page showed it)}.
"""
import hashlib
import io
import json
import pathlib
import sys

from score.review import concepts, setting as settings
from score.store import PROPS_HOME, running_under_agent, stamp_key

AREA = "environment-concept"
REFERENCES = "references"  # the private bucket's prefix and the local copy's folder under {home}
LONGEST_LINE = 300  # characters of the style line, a reference's purpose, a name or an answer's line
LONGEST_ANSWER = 2000  # characters of his answer to one question
MOST_ROWS = 60  # references, places, and places one place may hold
LARGEST_PICTURE = 12 * 1024 * 1024
QUESTIONS = (  # the set interview, asked in this order, one at a time
    ("style", "What style holds the whole environment, in one short line?"),
    ("setting", "What does everything stand on: a plot of ground, a world, or several bodies that move one another? "
                "Name real bodies or give an invented one's values, what lights it and what is too far to move, and "
                "say where each first place stands."),
    ("references", "Which pictures guide the look, and what is each one for?"),
    ("places", "Which places come first?"),
    ("insides", "What places may each of them hold inside?"),
)
FIELDS = {"style": "style", "setting": "setting", "references": "references", "places": "places", "insides": "places"}


class Refused(ValueError):
    """An environment concept or an ask that cannot be kept as given."""


def world_name():
    """Environment 1's id (data/definitions/world.json `name`): the one environment this store holds today."""
    return json.loads((concepts.DATA / "definitions/world.json").read_text())["name"]


def ask_euros(per_unit=concepts.DATA / "costs/per-unit.json"):
    """The euros of one ask: the measured Gemini 3.1 Pro answer at the standard tier (concepts.MEASURED_ASK), None
    while it is not measured."""
    return concepts.draw_euros(per_unit, (concepts.MEASURED_ASK,))


def yes_key(world, at):
    return f"environment-concept-{world}-{stamp_key(at)}"


# --- today's data: environment 1's concept before any version is kept -------------------------------------------

def style_now():
    """The style line of data/definitions/concept_views.json, the owner's."""
    return json.loads((concepts.DATA / "definitions/concept_views.json").read_text()).get("style", "").strip()


def references_now():
    """[{picture, shows, place}] of data/places/concept_inputs.json, each with the place it goes with."""
    found = json.loads((concepts.DATA / "places/concept_inputs.json").read_text())["places"]
    return [{"picture": ref["picture"], "shows": ref["shows"], "place": place}
            for place, inputs in found.items() for ref in inputs.get("references", [])]


def outermost(node, tree):
    """The outside place or shell holding `node` (itself when it is one; a part goes to the place it is part of)."""
    node = tree["parts"][node][0] if node in tree["parts"] else node
    while node in tree["within"]:
        node = tree["within"][node]
    return node


def places_now(places):
    """[{place, name, holds [name]}] of the outside places and shells (of `places` and within.json's shells) and of
    every place that holds others, outside ones first, by within.json."""
    tree = concepts.tree()
    nodes = [*tree["shells"], *[place for place in places if place not in tree["shells"]]]
    outside = [node for node in nodes if node not in tree["within"] and node not in tree["parts"]  # a part: no place
               and node not in tree["merged"]]  # merged into another: none either
    holders = [node for node in tree["within"] if concepts.inside_of(node)]
    return [{"place": node, "name": name_in(node, tree), "holds": [name_in(child, tree)
                                                                   for child in concepts.inside_of(node)]}
            for node in [*outside, *[node for node in holders if node not in outside]]]


def name_in(node, tree):
    """A place's or shell's short name as the cockpit says it."""
    return tree["shells"].get(node) or concepts.short_name(node).removeprefix("the ").capitalize()


def prefilled(places):
    """Environment 1's concept as today's data holds it (module docstring)."""
    return {"style": style_now(), "setting": settings.now(), "references": references_now(),
            "places": places_now(places)}


# --- the versions --------------------------------------------------------------------------------------------------

def with_setting(record):
    """A kept version with its concept's setting: today's (settings.now) for one kept before settings existed."""
    concept = record["concept"]
    return record if "setting" in concept else {**record, "concept": {
        **{name: value for name, value in concept.items() if name != "physics"}, "setting": settings.now()}}


def versions(store, world):
    """The versions kept, oldest first."""
    return [with_setting(store.read(key)) for key in sorted(store.objects.keys(f"{AREA}/{world}/versions/"))]


def newest(store, world):
    """The newest version kept, None while none is."""
    keys = sorted(store.objects.keys(f"{AREA}/{world}/versions/"))
    return with_setting(store.read(keys[-1])) if keys else None


def setting_of(store, world=None):
    """The environment's setting as its concept holds it now: the newest version's, else today's."""
    found = newest(store, world or world_name())
    return found["concept"]["setting"] if found else settings.now()


def version(store, world=None):
    """The version every draw and pick is made under: the newest version's time, None while none is kept."""
    found = newest(store, world or world_name())
    return found["at"] if found else None


def unlocked(store, world=None):
    """True while the newest version is not locked: no place is drawn or picked then."""
    found = newest(store, world or world_name())
    return bool(found) and not found["locked"]


def in_force(store, world=None):
    """The locked concept every place's draw reads, None while none is kept (the draws read today's data)."""
    found = newest(store, world or world_name())
    return found["concept"] if found and found["locked"] else None


def places_in_force(store, places, world=None):
    """[{place, name, holds}] the locked concept starts within.json's proposal from; today's when none is kept."""
    return (in_force(store, world) or {"places": places_now(places)})["places"]


def current(store, world, places):
    """{concept, locked, by, at, versions, prefilled} his page shows: the newest version, else today's data, locked."""
    found = versions(store, world)
    if not found:
        return {"concept": prefilled(places), "locked": True, "by": None, "at": None, "versions": 0,
                "prefilled": True}
    return {**{name: found[-1][name] for name in ("concept", "locked", "by", "at")}, "versions": len(found),
            "prefilled": False}


def line(value, what):
    """One stripped line of at most LONGEST_LINE characters; Refused past it."""
    found = " ".join(str(value or "").split())
    if len(found) > LONGEST_LINE:
        raise Refused(f"{what} is {len(found)} characters; at most {LONGEST_LINE}")
    return found


def rows(value, what):
    """A list of at most MOST_ROWS dicts; Refused otherwise."""
    if not isinstance(value, list) or len(value) > MOST_ROWS or not all(isinstance(row, dict) for row in value):
        raise Refused(f"{what} is a list of at most {MOST_ROWS} rows")
    return value


def names(value, what):
    """[name] of a list or a comma-separated line, each a line."""
    found = value.split(",") if isinstance(value, str) else value or []
    if not isinstance(found, list) or len(found) > MOST_ROWS:
        raise Refused(f"{what} is at most {MOST_ROWS} names")
    return [name for name in (line(item, what) for item in found) if name]


def checked_references(value):
    return [{"picture": line(row.get("picture"), "a picture"), "shows": line(row.get("shows"), "what it is for"),
             "place": line(row.get("place"), "its place") or None}
            for row in rows(value, "references") if line(row.get("picture"), "a picture")]


def checked_places(value):
    return [{**({"place": line(row["place"], "a place")} if row.get("place") else {}),
             "name": line(row.get("name"), "a place's name"), "holds": names(row.get("holds"), "what it holds")}
            for row in rows(value, "places") if line(row.get("name"), "a place's name")]


def checked(concept):
    """`concept` with every field in its shape (module docstring); Refused otherwise."""
    if not isinstance(concept, dict):
        raise Refused("an environment concept is an object")
    try:
        setting = settings.checked(concept.get("setting") or {})
    except settings.Refused as wrong:
        raise Refused(f"the setting: {wrong}") from wrong
    return {"style": line(concept.get("style"), "the style line"), "setting": setting,
            "references": checked_references(concept.get("references") or []),
            "places": checked_places(concept.get("places") or [])}


def saved(store, world, concept, locked, by):
    """Keep `concept` as the environment's newest version, locked or not; the record. Refused for a concept out of
    shape; PermissionError in an agent's process on the framework's store."""
    record = {"world": world, "concept": checked(concept), "locked": bool(locked), "by": by, "at": concepts.now()}
    concepts.recorded(store, f"{AREA}/{world}/versions/{stamp_key(record['at'])}.json", record)
    return record


# --- his reference pictures ---------------------------------------------------------------------------------------

def picture_kind(data):
    """The picture's file suffix (png, jpg, webp); Refused for anything else or past LARGEST_PICTURE."""
    from PIL import Image
    if len(data) > LARGEST_PICTURE:
        raise Refused(f"the picture is {len(data)} bytes; at most {LARGEST_PICTURE}")
    try:
        found = Image.open(io.BytesIO(data)).format
    except Exception as wrong:  # PIL raises several kinds for bytes that are no picture
        raise Refused("that is no picture") from wrong
    suffix = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}.get(found)
    if suffix is None:
        raise Refused(f"a reference is a PNG, JPEG or WebP picture, not {found}")
    return suffix


def kept_reference(data, name, offsite=None, home=None):
    """His new reference picture into the private bucket (references/<sha>.<suffix>, named in references/index.json)
    and its local copy ({home}/references/<name>); its `picture` path as the concept names it. Refused for no
    picture or a name another picture has; PermissionError for the private bucket in an agent's process."""
    if offsite is None and running_under_agent():
        raise PermissionError("only the owner adds a reference picture, from his own cockpit")
    suffix = picture_kind(data)
    stem = "".join(char if char.isalnum() or char in "-_" else "-" for char in pathlib.Path(name).stem)[:60] or "ref"
    named, sha = f"{stem}.{suffix}", hashlib.sha256(data).hexdigest()
    bucket = offsite or concepts.offsite_store()
    index = json.loads(bucket.read_bytes(f"{REFERENCES}/index.json")) if bucket.exists(
        f"{REFERENCES}/index.json") else {}
    key = f"{REFERENCES}/{sha}.{suffix}"
    if named in index and index[named]["key"] != key:
        raise Refused(f"another picture is already named {named}")
    if not bucket.exists(key):
        bucket.write_bytes(key, data)
    bucket.write_bytes(f"{REFERENCES}/index.json", json.dumps({**index, named: {"key": key, "bytes": len(data)}},
                                                              indent=1).encode())
    local = pathlib.Path(home or PROPS_HOME) / REFERENCES / named
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_bytes(data)
    return f"{{home}}/{REFERENCES}/{named}"


def referenced(store, world, data, name, shows, place, by, offsite=None):
    """His new reference added to the environment's concept: the picture kept (kept_reference), then a new unlocked
    version holding it; the version. Refused while the concept is locked."""
    found = newest(store, world)
    if found is None or found["locked"]:
        raise Refused("the environment concept is locked; unlock it first")
    picture = kept_reference(data, name, offsite)
    concept = found["concept"]
    added = {"picture": picture, "shows": shows, "place": place or None}
    return saved(store, world, {**concept, "references": [*concept["references"], added]}, False, by)


# --- the set interview ------------------------------------------------------------------------------------------

def question_of(topic):
    found = dict(QUESTIONS).get(topic)
    if found is None:
        raise Refused(f"no question on {topic!r}")
    return found


SETTING_SHAPE = ('{"bodies": [{"body": "key", "name": "", "reference": "a key of the real bodies"} for a real body, '
                 'or for an invented one {"body", "name", "radius_km", "mass_kg", "around": "the key it orbits, null '
                 'for the root", "distance_km", "period_days", "eccentricity", "inclination_deg", "day_hours" or '
                 '"locked_to", "tilt_deg", and for one that shines "kelvin", "lux", "lux_at_km"}] for what moves under '
                 'the physics, "lights": [{"light": "key", "name": "", "kelvin", "lux", "latitude", "tilt_deg", '
                 '"day_hours", "year_days", "equinox": "ISO moment"}] for a far light on its day path with no body '
                 '(one house\'s sun), "backdrops": [{"backdrop": "key", "name": "", "shape": "dome" or "skyline", '
                 '"lux", "kelvin"}] for what is too far to move (the stars), "plots": [{"plot": "key", "name": "", '
                 '"gravity": 9.81}] for flat ground with no body under it, "sites": [{"place": "the place", "on": '
                 '"a body or plot key", "latitude", "longitude", "height_m"} on a body, {"place", "on", "x", "y", '
                 '"height_m"} in metres on a plot]}')


def interview_question(topic, answer, concept):
    """What one ask sends the model: the environment concept so far, the question, his answer, and the JSON it
    answers with (only the field the question is about)."""
    field = FIELDS[topic]
    shape = {"style": '"one short line"',
             "setting": SETTING_SHAPE,
             "references": '[{"picture": "kept as given", "shows": "what it is for", "place": "its place or null"}]',
             "places": '[{"name": "", "holds": ["the places it may hold inside"]}]'}[field]
    return (f"You help a game environment's creator lock down its concept before any place is drawn. The concept so "
            f"far, as JSON:\n{json.dumps(concept, indent=1)}\n\nQuestion: {question_of(topic)}\nHis answer: {answer}\n\n"
            f"Answer with JSON only, no other words: {{\"{field}\": {shape}}}, the whole updated {field} with his "
            f"answer worked in, keeping what he did not change. Short plain words."
            + (" Keep every site's latitude and longitude to the digit as given unless he moves it; never put two "
               "sites on one spot." if field == "setting" else "")
            + (f" The real bodies: {', '.join(sorted(settings.reference()['bodies']))}." if field == "setting"
               else ""))


def proposed_from(text, topic, concept=None):
    """{field: value} the model answered for the topic, checked (a setting's sites it put on one spot that `concept`'s
    had apart kept where they were: setting.kept_apart); Refused when it is no such JSON."""
    field = FIELDS[topic]
    body = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        found = json.loads(body)
    except ValueError as wrong:
        raise Refused("the model answered no JSON") from wrong
    if not isinstance(found, dict) or field not in found:
        raise Refused(f"the model answered no {field}")
    value = settings.proposed(found[field]) if field == "setting" and isinstance(found[field], dict) else found[field]
    if field == "setting" and isinstance(value, dict):
        value = settings.kept_apart(value, (concept or {}).get("setting"))
    return {field: checked({field: value})[field]}


def reference_paths(concept):
    """The local copies of the concept's references that stand on this machine, as the model is sent them."""
    found = [concepts.resolved(ref["picture"]) for ref in concept.get("references", [])]
    return [path for path in found if path.is_file()]


def ask(store, world, request, by, reviser=None):
    """One answer of the set interview inside the owner's yes (SCORE_SPEND_TICKET names it): his answer and the
    concept so far sent to the model with the references on this machine, its proposed fields kept as an ask
    record; the record. `reviser(question, pictures)` makes the model's text (default concepts.revise)."""
    from score.adapters import compute
    yes = compute.require_cleared("an environment concept ask", store)
    topic, answer = str(request.get("topic")), str(request.get("answer") or "").strip()
    if not answer or len(answer) > LONGEST_ANSWER:
        raise Refused(f"an answer is 1 to {LONGEST_ANSWER} characters")
    concept = checked(request.get("concept") or {})
    question = interview_question(topic, answer, concept)
    text = (reviser or concepts.revise)(question, reference_paths(concept))
    record = {"world": world, "topic": topic, "question": question_of(topic), "answer": answer,
              "proposed": proposed_from(text, topic, concept), "euros": yes["euros"], "yes": yes["key"], "by": by,
              "at": concepts.now()}
    concepts.recorded(store, f"{AREA}/{world}/asks/{stamp_key(record['at'])}.json", record)
    return record


def asks(store, world):
    """The interview's asks kept, oldest first."""
    return [store.read(key) for key in sorted(store.objects.keys(f"{AREA}/{world}/asks/"))]


def main(argv):
    """`<world> <request.json> <by>`: one ask in the store its yes is in (SCORE_SPEND_STORE, else the framework's);
    its record as one JSON line, or the refusal on stderr with exit 1."""
    import os
    from score.adapters.compute import STORE, Refused as NotCleared
    from score.store import Store
    world, request, by = argv
    store = Store.in_folder(os.environ[STORE]) if os.environ.get(STORE) else Store.default()
    try:
        record = ask(store, world, json.loads(pathlib.Path(request).read_text()), by)
    except (Refused, concepts.Refused, NotCleared) as refused:
        print(f"refused: {refused}", file=sys.stderr)
        return 1
    print(json.dumps(record))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
