"""What the pages show, in pictures and few words: a place's one status, the board's look groups, the place's chain
strip and its problems, and the money against the stop. Presentation only: it reads the models of state/models.py
and never the store."""
import re
from collections import Counter
from urllib.parse import quote

from score.dashboard.pages import seen
from score.dashboard.state import groups, holes, plain

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


# --- holes -------------------------------------------------------------------------------------------------------

def node_words(node):
    """A node in words for the pages: its step's label and its place, never its id."""
    stage, _, place = node.partition("@")
    if not place:
        return f"the shared {groups.label(stage)} step"
    return f"the {groups.label(stage)} step of {plain.place_words(place)}"


def source_label(hole):
    """Where a hole was read, in a few words: its inventory row, its gate, its route step or its lost input."""
    kind = holes.kind_of(hole)
    if kind == "missing":
        return f"inventory row {hole.row}"
    if kind == "gate":
        return f"gate {hole.gates[0]}" if hole.gates else "a written fault"
    if kind == "route":
        return f"route step {(hole.id or '').split(':', 1)[-1]}"
    return f"lost input {plain.lost_item(hole.id or '')}"


def needs_words(hole, price, place):
    """What fills a hole and how long its chain is, in words; None when there is no chain to say."""
    current = price is not None and not price.stale and hole.node
    nodes = price.chains.get(place, {}).get(hole.node) if current else None
    if nodes is None:
        return None
    paid = sum(node in price.nodes for node in nodes)
    return f"needs {node_words(hole.node)}; its chain is {holes.steps(len(nodes))}, {paid} of them paid"


def hole_line(entry, place, count, price):
    """One line of the holes list: the hole in plain words, where it was read, the step that fills it and its
    chain's length (the chain itself, priced by the runner, for a fold), its basket item, or what stands in the
    way, and the viewer framing it when it has a box."""
    hole = entry["hole"]
    said = entry["said"]
    return {"sentence": plain.hole_sentence(hole, place, count), "source": source_label(hole),
            "needs": needs_words(hole, price, place), "chain": entry["chain"],
            "item_url": f"/basket/item/{entry['item']}/" if entry["item"] else None,
            "said": said, "short": f"{holes.NO_STAGE}: {holes.work_task(hole.work)}" if hole.node is None else said,
            "full": hole.sentence, "id": hole.id, "anchor": f"hole-{hole.id}", "filled_by": hole.node or hole.work,
            "view_url": f"/view/{place}?holes=1&hole={quote(hole.id or '')}" if hole.low is not None else None}


def framed_hole(detail, ident):
    """{sentence, url} of the hole the viewer frames (`ident`, its id): its plain sentence and its line on the place
    page; None when no hole of the place has that id."""
    hole = next((hole for hole in detail.holes if ident and hole.id == ident), None)
    if hole is None:
        return None
    return {"sentence": plain.hole_sentence(hole, detail.place),
            "url": f"/place/{detail.place}/#{anchors_of(detail)[hole.id]}"}


def hole_marks(detail):
    """[{id, low, high, kind, sentence, url}] the viewer outlines: each hole with a box in space, by its rule (missing,
    gate), its plain sentence and its line on the place page, so a click on its box names it."""
    anchors = anchors_of(detail)
    return [{"id": hole.id, "low": hole.low, "high": hole.high, "kind": hole.rule,
             "sentence": plain.hole_sentence(hole, detail.place),
             "url": f"/place/{detail.place}/#{anchors[hole.id]}"} for hole in detail.holes
            if hole.low is not None and hole.high is not None]


def line_key(hole):
    """The line a hole is listed on: a row's missing objects share one, every other hole its own."""
    return (holes.kind_of(hole), hole.row if hole.rule == "missing" else hole.id)


def hole_groups(detail, items, price):
    """[{kind, title, left, count, lines, framable}] of the place's holes by kind, worst first; a row's missing
    objects on one line. Each group says what happens if its holes are left, and whether any of its lines has a box
    the viewer can frame."""
    found = {kind: [] for kind, _ in holes.KINDS}
    counted = {}
    for entry in holes.priced(detail.holes, items, price, detail.place):
        key = line_key(entry["hole"])
        if key in counted:
            counted[key][1] += 1
            continue
        counted[key] = [entry, 1]
        found[key[0]].append(key)
    grouped = []
    for kind, title in holes.KINDS:
        if found[kind]:
            lines = [hole_line(counted[key][0], detail.place, counted[key][1], price) for key in found[kind]]
            grouped.append({"kind": kind, "title": title, "left": plain.LEFT[kind], "lines": lines,
                            "count": sum(counted[key][1] for key in found[kind]),
                            "framable": any(line["view_url"] for line in lines)})
    return grouped


def anchors_of(detail):
    """{hole id: the anchor of the line it is listed on}."""
    first = {}
    for hole in detail.holes:
        first.setdefault(line_key(hole), f"hole-{hole.id}")
    return {hole.id: first[line_key(hole)] for hole in detail.holes}


def tree_path(hole, place):
    """The path a hole hangs at in the place's tree: a missing object's row beside its box (under /<place>/Objects
    with no box), a failing object's prim, a route step or lost input at the place itself."""
    if hole.rule == "missing":
        folder = hole.prim.rsplit("/", 1)[0] if hole.prim else f"/{place}/Objects"
        return f"{folder}/{hole.row}"
    if hole.rule == "gate":
        named = (hole.id or "").rsplit(":", 1)[-1].replace("/", " ")  # an object named by a path is one leaf
        return hole.prim or f"/{place}/not on a prim/{named}"
    return f"/{place}"


def tree_node(name):
    return {"name": name, "count": 0, "kinds": Counter(), "children": {}, "anchor": None, "placeholder": False}


def finished(node):
    """A tree node with its kinds as [(kind, count)] worst first and its children as a list."""
    return {**node, "kinds": [(kind, node["kinds"][kind]) for kind, _ in holes.KINDS if node["kinds"][kind]],
            "children": [finished(child) for child in node["children"].values()]}


def prim_tree(detail):
    """The holes layer as a tree from the place's root: each node's holes below it by kind, a missing row a
    placeholder leaf, each leaf linked to its line of the list. The holes layer only: no accepted assembly stands
    to give the whole scene's tree."""
    anchors = anchors_of(detail)
    root = tree_node(f"/{detail.place}")
    for hole in detail.holes:
        kind = holes.kind_of(hole)
        parts = tree_path(hole, detail.place).strip("/").split("/")
        node = root
        node["count"] += 1
        node["kinds"][kind] += 1
        for part in parts[1:] if parts[0] == detail.place else parts:
            node = node["children"].setdefault(part, tree_node(part))
            node["count"] += 1
            node["kinds"][kind] += 1
        node["anchor"] = node["anchor"] or anchors.get(hole.id)
        node["placeholder"] = node["placeholder"] or kind == "missing"
    return finished(root)


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


# --- the environment overview ------------------------------------------------------------------------------------

# Each owner's command a books refusal names, as it names it: "score spend --read-back", "score spend --<figure> EUR".
OWNERS_COMMAND = re.compile(r"score spend[ ]+(--[a-z-]+(?: EUR)?)")
STATUS_WORDS = {"lost": ("a lost input", "bad"), "route": ("route steps not done", "bad"),
                "missing": ("objects not made", "review"), "gate": ("made, failing checks", "review")}


def overview(rows, names):
    """The overview's rows: each place's row with its name and its status, the worst kind of hole it has (or that
    it was not checked), and its next route step."""
    found = []
    for row in rows:
        if row["not_checked"]:
            status = {"words": "not checked", "tone": "idle"}
        elif row["worst"]:
            words, tone = STATUS_WORDS[row["worst"]]
            status = {"words": words, "tone": tone}
        else:
            status = {"words": "no holes found", "tone": "done"}
        found.append({**row, "name": names.get(row["place"], humane(row["place"])), "status": status,
                      "next": sentence(row["next"]) if row["next"] else None})
    return found


def with_holes(shown, places):
    """The board's groups with each tile's holes from the overview's rows (present.overview): {count, words, tone}
    of its holes and its worst kind, or None for a place the overview has no row of; the groups, changed in place."""
    rows = {row["place"]: row for row in places}
    for group in shown:
        for tile in group["tiles"]:
            row = rows.get(tile["place"])
            tile["holes"] = None if row is None else {
                "count": row["holes"], "words": row["status"]["words"], "tone": row["status"]["tone"],
                "checked": not row["not_checked"]}
    return shown


def blockers(money_card, spend, lost):
    """[{title, words, commands, details}] of the steps that block every paid step, read from state: no stop set (the
    money card's, as it says it, read or not), the month's books not known (or not read yet), and each kind of lost
    input with the places it blocks."""
    found = []
    if not money_card["stop"]:
        found.append({"title": "Set a stop", "words": "No stop is set for this environment, so every paid step "
                      "is refused. Type in your own terminal:", "commands": [money_card["stop_line"]],
                      "details": []})
    if spend.as_of is None:
        found.append({"title": "The month's books are not read yet",
                      "words": "Whether they are known is read with the month's spend; load the page again in a "
                               "moment.", "commands": [], "details": [spend.note] if spend.note else []})
    elif spend.paid_refused:
        found.append({"title": "The month's books are not known", "words": "Paid work is refused until they are. "
                      "Only you can make them known, in your own terminal:",
                      "commands": [f".venv/bin/python -m score spend {named}"
                                   for named in dict.fromkeys(OWNERS_COMMAND.findall(spend.paid_refused))],
                      "details": [spend.paid_refused]})
    for entry in lost:
        found.append({"title": entry["words"],
                      "words": f"Blocks {entry['places']} place{'s' if entry['places'] != 1 else ''} "
                               f"({entry['items']} input{'s' if entry['items'] != 1 else ''}). "
                               f"The code work: {holes.work_task(entry['work'][0])}.",
                      "commands": [], "details": entry["work"] + entry["ids"]})
    return found


def buy_line(entry):
    """One paid step of the buy-first list in words: its step, its own price and the basket item that carries it."""
    return {**entry, "words": node_words(entry["node"]),
            "item_url": f"/basket/item/{entry['item']}/" if entry["item"] else None}


def euros_words(money):
    """A sum's money in a few words: the measured likely to high, the guesses said as guessed."""
    words = []
    if money["measured"]:
        words.append(f"EUR {money['likely']:.2f} to {money['high']:.2f} measured")
    if money["guessed"]:
        words.append(f"EUR {money['guessed']:.2f} guessed")
    if money["unknown"]:
        words.append(f"{holes.steps(money['unknown'], 'paid step')} with no price and no guess")
    return ", ".join(words) or "no paid step"


def buy_lines(first, code):
    """{all_wait, ready, waiting, code, count} of the buy-first list (holes.buy_first) and the code work the places
    wait on (holes.code_first): the paid steps some of whose holes wait on nothing (`ready`) apart from those whose
    holes all wait on a lost input or a route step first (`waiting`), and `all_wait` when no step is ready, so the
    page says first that no paid step fills a hole yet and which code work comes before."""
    lines = [buy_line(entry) for entry in first]
    ready = [line for line in lines if line["waiting"] < line["holes"]]
    return {"all_wait": bool(lines) and not ready, "ready": ready,
            "waiting": [line for line in lines if line["waiting"] >= line["holes"]],
            "code": [{**task, "euros": euros_words(task["money"])} for task in code], "count": len(lines)}
