"""A place's problems in one plain sentence each, for someone who did not build the framework: what is wrong and
where, never a gate's name or a node. A named gap is said by its check (data/checks/gaps/<place>.json `check`),
the things it names in words; a stopped step by what its fault report says stopped it."""
import re

NUMBERED = re.compile(r"(_\d+|-[a-z]\d+)$")  # an instance number or a take's suffix
MOST_NAMED = 4
LOST = "place:lost:"  # a lost input's hole id: place:lost:<kind>:<item> (score/stages/complete/holes/__main__.py)
# Each check of a named gap as a plain sentence, said of one thing and of several: {things} the named things in
# words, {place} the place.
SAID = {
    "game": ("Where things stand in {place} is still copied from the old game; it is not yet laid out from its own "
             "plan.",) * 2,
    "people": ("{things} should be in {place} but is missing: no finished body yet.",
               "{things} should be in {place} but are missing: no finished bodies yet."),
    "likeness": ("{things} in {place} was never compared with its close-up picture.",
                 "{things} in {place} were never compared with their close-up pictures."),
    "effects": ("The {things} effect is missing in {place}.", "The {things} effects are missing in {place}."),
    "rows": ("{things} should stand in {place} but is not there.",
             "{things} should stand in {place} but are not there."),
    "painted": ("{things} in {place} still wears the paint of a rough first model.",
                "{things} in {place} still wear the paint of a rough first model."),
    "stands level": ("{things} in {place} stands with a foot off the floor.",
                     "{things} in {place} stand with a foot off the floor."),
    "resting": ("{things} in {place} does not rest steadily where it stands.",
                "{things} in {place} do not rest steadily where they stand."),
    "colour against the close-up": ("The paint colour of {things} in {place} does not match its close-up picture.",
                                    "The paint colours of {things} in {place} do not match their close-up pictures."),
    "boxes": ("{things} in {place} is the wrong size or in the wrong place for its planned box.",
              "{things} in {place} are the wrong size or in the wrong place for their planned boxes."),
    "baked matches its surfaces": ("{things} in {place} comes out lighter or darker in places than its close-up.",
                                   "{things} in {place} come out lighter or darker in places than their close-ups."),
    "placeholders": ("{things} in {place} is still a stand-in block: no finished model yet.",
                     "{things} in {place} are still stand-in blocks: no finished models yet."),
    "outline": ("The shape of {things} in {place} does not match its close-up picture.",
                "The shapes of {things} in {place} do not match their close-up pictures."),
    "picks": ("{things} in {place} is not the version you picked: it was replaced.",
              "{things} in {place} are not the versions you picked: they were replaced."),
    "motion": ("{things} in {place} should move but stands still.", "{things} in {place} should move but stand still."),
    "reach": ("{things} is missing from {place}: its layout rule never places it here.",
              "{things} are missing from {place}: its layout rule never places them here."),
}
SAID["grounded"] = SAID["boxes"]
# What happens if a hole of each kind is left (state/holes.py KINDS).
LEFT = {"missing": "the place cannot be complete while a row of its scene inventory has no object.",
        "gate": "the place cannot be complete while a made object fails its check.",
        "route": "no step after it can run for this place, so nothing below it can be made.",
        "lost": "every step that reads it stays blocked, here and at every other place that reads it."}
NO_LIKENESS = "The props in {place} were never compared with their close-up pictures: it has no props list."


def place_words(place):
    return f"the {place.replace('_', ' ')}"


def thing_names(objects):
    """The named things by their bare names, each once ("/hangar/Objects/hose_reel_1" and "hose_reel" are "hose
    reel")."""
    found = []
    for item in objects:
        name = NUMBERED.sub("", item.split(" (")[0].rsplit("/", 1)[-1].rsplit(".", 1)[-1]).replace("_", " ")
        if name and name not in found:
            found.append(name)
    return found


def thing_words(names):
    """Names in words: at most MOST_NAMED, then how many more."""
    shown = names[:MOST_NAMED] + ([f"{len(names) - MOST_NAMED} more"] if len(names) > MOST_NAMED else [])
    if not shown:
        return "something"
    return shown[0] if len(shown) == 1 else ", ".join(shown[:-1]) + " and " + shown[-1]


def capital(text):
    return text[:1].upper() + text[1:]


def gap_sentence(entry, place):
    """A named gap in one plain sentence; its own name, the place's prefix dropped, when its check has none."""
    check = entry.get("check")
    objects = [item for item in entry.get("objects") or [] if isinstance(item, str)]
    if check == "likeness" and objects == ["likeness"]:
        return NO_LIKENESS.format(place=place_words(place))
    if check in SAID:
        names = thing_names(objects)
        said = SAID[check][len(names) > 1]
        return capital(said.format(things=thing_words(names), place=place_words(place)))
    name = entry["name"].removeprefix(f"{place}: ").removeprefix(f"{place}:").strip()
    return capital(name).rstrip(".") + "."


def stop_sentence(label, why, place, gaps):
    """A stopped step in one plain sentence: the known gaps that stopped it, a check it failed, else its cause."""
    if "named gaps" in why and gaps:
        return (f"The final check stopped {place_words(place)} because of the {gaps} known "
                f"gap{'s' if gaps > 1 else ''} below, which are not fixed yet.")
    failed = re.search(r"answered fail: ([^:;]+)", why)
    if failed:
        return f"The {label} step stopped: its {failed.group(1).strip()} check failed."
    cause = re.split(r"[;(]", why, maxsplit=1)[0].strip().rstrip(".:")
    return f"The {label} step stopped: {cause}." if cause else f"The {label} step stopped."


def lost_item(hole_id):
    """The item a lost input's id names (place:lost:<kind>:<item>), whole: an item may hold a colon itself."""
    return hole_id.removeprefix(LOST).split(":", 1)[-1]


def hole_sentence(hole, place, count=1):
    """A hole in one plain sentence: a row with nothing made for it (`count` of its objects), a made thing that fails
    a check (said by that check as a named gap's is, else as the check found it), or a step the place has not been
    through."""
    if hole.rule == "missing":
        name = hole.sentence.split(": ", 1)[0]
        many = f" ({count} of them)" if count > 1 else ""
        nowhere = "; the inventory gives it no spot" if hole.placed == "unplaced" else ""
        return capital(f"{name} should be in {place_words(place)} but nothing is made for it yet{many}{nowhere}.")
    if (hole.id or "").startswith(LOST):  # its words name the file and the steps reading it: kept for the fold
        return f"An input {place_words(place)}'s steps read is lost: {lost_item(hole.id)}."
    gate = (hole.gates or ["/"])[0].split("/", 1)[1]
    if hole.rule == "gate" and gate in SAID:
        names = thing_names([hole.prim or (hole.id or "").split(":", 2)[-1]])  # the object its id names
        return capital(SAID[gate][0].format(things=thing_words(names), place=place_words(place)))
    return capital(hole.sentence).rstrip(".") + "."
