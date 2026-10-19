"""What the pages show, in pictures and few words: a place's one status, the board's look groups, the place's chain
strip and its problems, and the money against the stop. Presentation only: it reads the models of state/models.py
and never the store."""
import re

from score.dashboard.pages import seen
from score.dashboard.state import groups

GAP_COUNT = re.compile(r"named gaps \((\d+)\)")
OWN_LOOKS = "Each in its own look"
NO_LOOK = "Not given a look yet"
STATE_WORDS = {"accepted": "done", "waiting": "to review", "stopped": "stopped", "not run": "not run"}


def humane(key):
    """A key in words: underscores and dashes as spaces, the first letter capital."""
    words = key.replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:]


def field(item, name):
    """A field of a model or a dict, None when it has none."""
    return item.get(name) if isinstance(item, dict) else getattr(item, name, None)


# --- a place's one status ----------------------------------------------------------------------------------------

def problem_count(status, layers):
    """Stopped steps plus the named gaps the status counts."""
    stopped = sum(1 for layer in layers for step in layer.steps if step.state == "stopped")
    found = GAP_COUNT.search(status or "")
    return stopped + (int(found.group(1)) if found else 0)


def place_status(status, layers):
    """{words, tone} of a place in a few words: problems first, then outputs waiting for the owner's eye, then
    outputs he has not seen, then how far it got."""
    steps = [step for layer in layers for step in layer.steps]
    problems = problem_count(status, layers)
    if problems:
        return {"words": f"{problems} problem{'s' if problems > 1 else ''}", "tone": "bad"}
    if any(step.state == "waiting" for step in steps):
        return {"words": "ready to review", "tone": "review"}
    if any(step.mark == seen.NOT_SEEN for step in steps):
        return {"words": "not seen by you", "tone": "new"}
    if steps and all(step.state == "accepted" for step in steps):
        return {"words": "done", "tone": "done"}
    if not any(step.state != "not run" for step in steps):
        return {"words": "not started", "tone": "idle"}
    return {"words": "in progress", "tone": "idle"}


def mark_words(mark):
    """The owner's mark in his words: "not seen by you", "seen by you", "advanced", or None."""
    if not mark:
        return None
    if mark == seen.NOT_SEEN:
        return "not seen by you"
    return "advanced" if mark.startswith(seen.ADVANCED) else "seen by you"


# --- the board's look groups -------------------------------------------------------------------------------------

def tile(card, name, queued):
    """A place's board tile: its name once, its best picture, its one status."""
    return {"place": card.place, "name": name, "film": card.film, "picture": card.hero,
            "still": field(card, "still"), "status": place_status(card.status, card.layers),
            "queued": card.place in queued}


def shared_name(labels):
    """A name for looks that share one reference picture: their common "the X's" ("the ship's cockpit", "the ship's
    galley": "The ship"), else "Sharing <the first>'s look"."""
    owners = {label.split("'s ")[0] for label in labels if "'s " in label}
    if len(owners) == 1 and all("'s " in label for label in labels):
        return humane(owners.pop())
    return f"Sharing {labels[0]}'s look"


def family_of(look):
    """The key family of a look with no picture ("prologue_flat": "prologue"), or None."""
    return look.split("_", 1)[0] if "_" in look else None


def group_key(style, families):
    """Which board group a style falls in: doors and no look by name, shared pictures together, a key family with no
    picture together, else every place in its own look."""
    if style.look in (groups.DOORS, groups.UNASSIGNED):
        return style.look
    if style.picture:
        return f"picture:{style.picture.sha}"
    family = family_of(style.look)
    return f"family:{family}" if family and families.get(family, 0) > 1 else OWN_LOOKS


def group_name(key, styles):
    if key == groups.DOORS:
        return "Doors"
    if key == groups.UNASSIGNED:
        return NO_LOOK
    if key.startswith("family:"):
        return f"The {key.removeprefix('family:')}"
    if key.startswith("picture:") and len(styles) > 1:
        return shared_name([style.label for style in styles])
    return OWN_LOOKS


def place_name(style, card, within=""):
    """A place's name once: its own look's words when the look is its alone (less the group's own words: "the
    ship's galley" in the ship is "Galley"), else its key in words."""
    if len(style.places) == 1 and style.look not in (groups.DOORS, groups.UNASSIGNED):
        label = style.label
        prefix = f"{within.lower()}'s "
        if within and label.lower().startswith(prefix):
            label = label[len(prefix):]
        return humane(label)
    return humane(card.place)


def look_groups(world, queued):
    """The board's groups: [{name, picture, palette, tiles}] in the order of the looks, one look's places once."""
    styles = [style for engine in world.engines for style in engine.styles]
    families = {}
    for style in styles:
        if not style.picture and family_of(style.look):
            families[family_of(style.look)] = families.get(family_of(style.look), 0) + 1
    keyed = {}
    for style in styles:
        keyed.setdefault(group_key(style, families), []).append(style)
    picture_keys = [key for key, members in keyed.items() if key.startswith("picture:") and len(members) == 1]
    for key in picture_keys:  # a reference picture of one look alone: that place is in its own look
        keyed.setdefault(OWN_LOOKS, []).extend(keyed.pop(key))
    last = (OWN_LOOKS, groups.DOORS, groups.UNASSIGNED)
    order = [key for key in keyed if key not in last] + [key for key in last if key in keyed]
    found = []
    for key in order:
        members = keyed[key]
        shared = key.startswith("picture:")
        name = group_name(key, members)
        within = name if shared and not name.startswith("Sharing") else ""
        found.append({"name": name, "picture": members[0].picture if shared else None,
                      "palette": members[0].palette if shared else [],
                      "tiles": [tile(card, place_name(style, card, within), queued) for style in members
                                for card in style.places]})
    return found


def look_of_place(world, place):
    """The style group a place's look is in, or None."""
    return next((style for engine in world.engines for style in engine.styles
                 if any(card.place == place for card in style.places)), None)


# --- the place page ----------------------------------------------------------------------------------------------

def full_picture(thumb):
    """The full picture behind a thumbnail URL (/thumbs/<sha>.jpg is /files/<sha>), or None."""
    if not thumb or not thumb.startswith("/thumbs/"):
        return None
    return "/files/" + thumb.removeprefix("/thumbs/").removesuffix(".jpg")


def step_tile(step, url):
    return {"label": step.label, "url": url, "thumb": step.thumb, "full": full_picture(step.thumb), "state": step.state,
            "words": STATE_WORDS.get(step.state, step.state), "unseen": step.mark == seen.NOT_SEEN,
            "paid": step.paid}


def picture_tile(label, picture, words):
    """A tile of a picture the chain starts from (the look's reference, the concept): no step page of its own."""
    return {"label": label, "url": picture.url if picture else None, "thumb": picture.thumb_url if picture else None,
            "full": picture.url if picture else None,
            "state": "accepted" if picture else "not run", "words": words if picture else "none yet",
            "unseen": False, "paid": False}


def first_clause(text, limit=110):
    """The text up to its first colon or semicolon, cut at a word under `limit`."""
    clause = re.split(r":\s|;\s", text.strip(), maxsplit=1)[0].strip().rstrip(".")
    if len(clause) > limit:
        clause = clause[:limit].rsplit(" ", 1)[0] + "..."
    return clause


def sentence(text):
    text = text.replace("the owner's ", "your ").replace("The owner's ", "Your ")
    return text[:1].upper() + text[1:]


KNOWN_GAP = "known gap, not fixed yet"
NO_PICTURE = "no picture of this yet"


def gap_problem(gap, place):
    """A named gap as one plain sentence and the picture of what it names, opening its step: a known problem not
    fixed yet."""
    name = gap.name.removeprefix(f"{place}: ").removeprefix(f"{place}:")
    picture = gap.picture
    return {"sentence": gap.sentence or sentence(first_clause(name)), "kind": KNOWN_GAP,
            "name": gap.picture_is or NO_PICTURE, "picture": picture.thumb_url if picture else None,
            "url": gap.step_url, "full": f"{gap.name}: {gap.reason}" if gap.reason else gap.name}


def fault_problem(fault):
    """A stopped step as one plain sentence and a picture of what it is about, opening its step."""
    picture = fault.picture
    return {"sentence": fault.sentence or sentence(f"{fault.label} stopped"), "kind": "stopped",
            "name": fault.picture_is or NO_PICTURE, "picture": picture.thumb_url if picture else None,
            "url": fault.step_url, "full": f"{fault.label}: {fault.why}"}


def check_problem(finding):
    """A standalone check's finding as one plain sentence and its picture: what it found, and the prim it is on."""
    picture = finding.picture
    return {"sentence": sentence(finding.sentence), "kind": f"{finding.check} check",
            "name": picture.name if picture else NO_PICTURE, "picture": picture.thumb_url if picture else None,
            "url": None, "full": f"{finding.rule}: {finding.prim}" if finding.prim else finding.rule}


def problems(detail):
    """Every stopped step, every named gap and every standalone check's finding of a place: [{sentence, kind,
    picture, url, full}]."""
    return ([fault_problem(fault) for fault in detail.faults]
            + [gap_problem(gap, detail.place) for gap in detail.gaps]
            + [check_problem(finding) for finding in detail.checks])


# --- money -------------------------------------------------------------------------------------------------------

STOP_LINE = '.venv/bin/python -m score.review stop {world} <euros> --reason "what it is for"'


def environment_name(stored):
    """An environment's id in the owner's words: `world1` (the stored id, kept so no node is made again) as
    "Environment 1"; any other id as it is."""
    numbered = re.fullmatch(r"world(\d+)", stored or "")
    return f"Environment {numbered.group(1)}" if numbered else stored


def share(part, whole):
    return min(100.0, 100.0 * part / whole) if part is not None and whole else None


def money(view, planned):
    """The money card from the month's MoneyView (state/money.py): the month's total ("at least" while a line is
    partial or missing, "not known yet" when no line has a number), a line per source, and the environment
    against its stop, or the terminal line that sets one."""
    known = [line for line in view.lines if line.euros is not None]
    spent = view.world_spent or 0.0
    flight = view.in_flight or 0.0
    return {"month": view.month, "total": view.total.euros if known else None, "whole": view.total.whole,
            "gaps": view.total.gaps, "lines": view.lines,
            "environment": environment_name(view.world) if view.world else "this environment",
            "stop": view.stop, "spent": view.world_spent, "in_flight": view.in_flight,
            "spent_share": share(spent, view.stop), "flight_share": share(flight, view.stop),
            "room": round(view.stop - spent - flight, 2) if view.stop else None,
            "stop_line": STOP_LINE.format(world=view.world or "<world>"),
            "likely": (planned or {}).get("likely"), "credit_note": view.credit_note}
