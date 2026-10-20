"""What the pages show: a place's one status, the look groups and the place's gaps as marks for the viewer and as
a tree. Presentation only: it reads the models of state/models.py and never the store."""
import re
from collections import Counter

from score.dashboard.pages import seen
from score.dashboard.state import groups, gaps, plain

GAP_COUNT = re.compile(r"accepted gaps \((\d+)\)")
OWN_LOOKS = "Each in its own look"
NO_LOOK = "Not given a look yet"
STATE_WORDS = {"accepted": "done", "waiting": "to review", "stopped": "stopped", "not run": "not run"}


def humane(key):
    """A key in words: underscores and dashes as spaces, the first letter capital."""
    words = key.replace("_", " ").replace("-", " ").strip()
    return words[:1].upper() + words[1:]


def place_title(place):
    """A place's title from its key alone, its key in words."""
    return humane(groups.place_title(place))


def field(item, name):
    """A field of a model or a dict, None when it has none."""
    return item.get(name) if isinstance(item, dict) else getattr(item, name, None)


# --- a place's one status ----------------------------------------------------------------------------------------

def problem_count(status, layers):
    """Stopped steps plus the accepted gaps the status counts."""
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
    """Which board group a style falls in: no look by name, shared pictures together, a key family with no
    picture together, else every place in its own look."""
    if style.look == groups.UNASSIGNED:
        return style.look
    if style.picture:
        return f"picture:{style.picture.sha}"
    family = family_of(style.look)
    return f"family:{family}" if family and families.get(family, 0) > 1 else OWN_LOOKS


def group_name(key, styles):
    if key == groups.UNASSIGNED:
        return NO_LOOK
    if key.startswith("family:"):
        return f"The {key.removeprefix('family:')}"
    if key.startswith("picture:") and len(styles) > 1:
        return shared_name([style.label for style in styles])
    return OWN_LOOKS


def place_name(style, card, within=""):
    """A place's name once: its own look's words when the look is its alone (less the group's own words: "the
    ship's galley" in the ship is "Galley"), else its title from its key (place_title); its look's `short` first."""
    if style.short:
        return groups.short_name(card.place, style)
    if len(style.places) == 1 and style.look != groups.UNASSIGNED:
        label = style.label
        prefix = f"{within.lower()}'s "
        if within and label.lower().startswith(prefix):
            label = label[len(prefix):]
        return humane(label)
    return place_title(card.place)


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
    last = (OWN_LOOKS, groups.UNASSIGNED)
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


# --- the place: its gaps in the viewer and as a tree --------------------------------------------------------------

def framed_gap(detail, ident):
    """{sentence, url} of the gap the viewer frames (`ident`, its id): its plain sentence and its line on the place
    page; None when no gap of the place has that id."""
    gap = next((gap for gap in detail.gaps if ident and gap.id == ident), None)
    if gap is None:
        return None
    return {"sentence": plain.gap_sentence(gap, detail.place),
            "url": f"/place/{detail.place}/#{anchors_of(detail)[gap.id]}"}


def gap_marks(detail):
    """[{id, low, high, kind, sentence, url}] the viewer outlines: each gap with a box in space, by its rule (missing,
    gate), its plain sentence and its line on the place page, so a click on its box names it."""
    anchors = anchors_of(detail)
    return [{"id": gap.id, "low": gap.low, "high": gap.high, "kind": gap.rule,
             "sentence": plain.gap_sentence(gap, detail.place),
             "url": f"/place/{detail.place}/#{anchors[gap.id]}"} for gap in detail.gaps
            if gap.low is not None and gap.high is not None]


def line_key(gap):
    """The line a gap is listed on: a row's missing objects share one, every other gap its own."""
    return (gaps.kind_of(gap), gap.row if gap.rule == "missing" else gap.id)


def anchors_of(detail):
    """{gap id: the anchor of the line it is listed on}."""
    first = {}
    for gap in detail.gaps:
        first.setdefault(line_key(gap), f"gap-{gap.id}")
    return {gap.id: first[line_key(gap)] for gap in detail.gaps}


def tree_path(gap, place):
    """The path a gap hangs at in the place's tree: a missing object's row beside its box (under /<place>/Objects
    with no box), a failing object's prim, a route step or lost input at the place itself."""
    if gap.rule == "missing":
        folder = gap.prim.rsplit("/", 1)[0] if gap.prim else f"/{place}/Objects"
        return f"{folder}/{gap.row}"
    if gap.rule == "gate":
        named = (gap.id or "").rsplit(":", 1)[-1].replace("/", " ")  # an object named by a path is one leaf
        return gap.prim or f"/{place}/not on a prim/{named}"
    return f"/{place}"


def tree_node(name):
    return {"name": name, "count": 0, "kinds": Counter(), "children": {}, "anchor": None, "placeholder": False,
            "gaps": []}


def finished(node):
    """A tree node with its kinds as [(kind, count)] worst first and its children as a list."""
    return {**node, "kinds": [(kind, node["kinds"][kind]) for kind, _ in gaps.KINDS if node["kinds"][kind]],
            "children": [finished(child) for child in node["children"].values()]}


def prim_tree(detail):
    """The gaps layer as a tree from the place's root: each node's gaps below it by kind, a missing row a
    placeholder leaf, each leaf linked to its line of the list, each node with the gaps hanging at it (`gaps`).
    The gaps layer only: no accepted assembly stands to give the whole scene's tree."""
    anchors = anchors_of(detail)
    root = tree_node(f"/{detail.place}")
    for gap in detail.gaps:
        kind = gaps.kind_of(gap)
        parts = tree_path(gap, detail.place).strip("/").split("/")
        node = root
        node["count"] += 1
        node["kinds"][kind] += 1
        for part in parts[1:] if parts[0] == detail.place else parts:
            node = node["children"].setdefault(part, tree_node(part))
            node["count"] += 1
            node["kinds"][kind] += 1
        node["gaps"].append(gap)
        node["anchor"] = node["anchor"] or anchors.get(gap.id)
        node["placeholder"] = node["placeholder"] or kind == "missing"
    return finished(root)



def place_names(shown):
    """{place: its title} of the board's groups (look_groups), the names every page says a place by."""
    return {tile["place"]: tile["name"] for group in shown for tile in group["tiles"]}

