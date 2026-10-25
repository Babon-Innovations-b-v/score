"""A place's problems in one plain sentence each, for someone who did not build the framework: what is wrong and
where, never a gate's name or a node. An accepted gap is said by its check (data/checks/gaps/<place>.json `check`),
the things it names in words; a stopped step by what its fault report says stopped it."""
import re

from score.dashboard.state.groups import place_title

NUMBERED = re.compile(r"(_\d+|-[a-z]\d+)$")  # an instance number or a take's suffix
MOST_NAMED = 4
LOST = "place:lost:"  # a lost input's gap id: place:lost:<kind>:<item> (score/stages/complete/gaps/__main__.py)
# Each check of an accepted gap as a plain sentence, said of one thing and of several: {things} the named things in
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
# A stopped step's fault in plain words, first match wins (step_cause); a cloud tool's exit 1 is said apart.
CAUSES = ((re.compile(r"an input changed while it ran"), "an input file changed while it ran"),
          (re.compile(r"the finish call failed"), "the model's finishing step on a cloud machine failed"),
          (re.compile(r"Insufficient permissions"), "a file could not be saved"),
          (re.compile(r"^made: fail"), "it was made but failed its check"))
CLOUD_TOOL = re.compile(r"CalledProcessError: Command .*(blender_cloud|library_bake|characters)\S*\.py.*exit status 1")
NO_MACHINE = re.compile(r"could be rented|in stock|no machine|none rented")
EXCEPTION = re.compile(r"^(?:error|blocked):\s*|^\w+(?:Error|Exception):\s*")
A_PATH = re.compile(r"(?:\S*/)+([^\s/'\",\]]+)")
CAUSE_LENGTH = 100
NO_LIKENESS = "The props in {place} were never compared with their close-up pictures: it has no props list."


def place_words(place):
    return f"the {place_title(place)}"


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


def accepted_gap_sentence(entry, place):
    """An accepted gap in one plain sentence; its own name, the place's prefix dropped, when its check has none."""
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
    if "accepted gaps" in why and gaps:
        return (f"The final check stopped {place_words(place)} because of the {gaps} known "
                f"gap{'s' if gaps > 1 else ''} below, which are not fixed yet.")
    failed = re.search(r"answered fail: ([^:;]+)", why)
    if failed:
        return f"The {label} step stopped: its {failed.group(1).strip()} check failed."
    cause = re.split(r"[;(]", why, maxsplit=1)[0].strip().rstrip(".:")
    return f"The {label} step stopped: {cause}." if cause else f"The {label} step stopped."


def step_cause(why, report=""):
    """A stopped step's cause in a few plain words from its run line's fault (`why`) and its fault report's text: a
    cloud tool that rented no machine, a known cause of CAUSES, a check it failed, else the fault's first line, its
    exception name and folders dropped, at most CAUSE_LENGTH characters."""
    if re.search(r"could be rented|no machine", why) or CLOUD_TOOL.search(why) and NO_MACHINE.search(report):
        return "no cloud machine could be rented"
    if CLOUD_TOOL.search(why):
        return "its run on a cloud machine failed"
    found = next((cause for pattern, cause in CAUSES if pattern.search(why)), None)
    if found:
        return found
    failed = re.search(r"answered fail: ([^:;]+)", why)
    if failed:
        return f"its {failed.group(1).strip()} check failed"
    first = re.split(r"[;(]", (why.splitlines() or [""])[0], maxsplit=1)[0]
    cause = A_PATH.sub(r"\1", EXCEPTION.sub("", EXCEPTION.sub("", first.strip()))).strip().rstrip(".:")
    return cause if len(cause) <= CAUSE_LENGTH else cause[:CAUSE_LENGTH].rsplit(" ", 1)[0] + "..."


def lost_item(gap_id):
    """The item a lost input's id names (place:lost:<kind>:<item>), whole: an item may hold a colon itself."""
    return gap_id.removeprefix(LOST).split(":", 1)[-1]


def gap_sentence(gap, place, count=1):
    """A gap in one plain sentence: a row with nothing made for it (`count` of its objects), a made thing that fails
    a check (said by that check as an accepted gap's is, else as the check found it), or a step the place has not been
    through."""
    if gap.rule == "missing":
        name = gap.sentence.split(": ", 1)[0]
        many = f" ({count} of them)" if count > 1 else ""
        nowhere = "; the inventory gives it no spot" if gap.placed == "unplaced" else ""
        return capital(f"{name} should be in {place_words(place)} but nothing is made for it yet{many}{nowhere}.")
    if (gap.id or "").startswith(LOST):  # its words name the file and the steps reading it: kept for the fold
        return f"An input {place_words(place)}'s steps read is lost: {lost_item(gap.id)}."
    gate = (gap.gates or ["/"])[0].split("/", 1)[1]
    if gap.rule == "gate" and gate in SAID:
        names = thing_names([gap.prim or (gap.id or "").split(":", 2)[-1]])  # the object its id names
        return capital(SAID[gate][0].format(things=thing_words(names), place=place_words(place)))
    return capital(gap.sentence).rstrip(".") + "."
