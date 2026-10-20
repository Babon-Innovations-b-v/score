"""The cockpit's numbers (#42): what the five screens show, as numbers and states only, never sentences. Read from the
models of state/models.py and the runner's price record through state/holes.py; nothing is priced or judged here.
A number the runner does not give is None, which a page shows as a grey "unknown" state, never as 0."""
import datetime
import json
from collections import defaultdict

from score.dashboard.launch.backend import Billed
from score.dashboard.state import holes, library, screens

# a hole kind's state colour (design/tokens/colours.css) and its short label
KIND_TONES = {"lost": "hole-lost", "route": "hole-route", "missing": "hole-missing", "gate": "hole-gate"}
KIND_LABELS = {"lost": "lost", "route": "route", "missing": "missing", "gate": "failing"}


def known(line):
    """A cost line's euros, or None while it is missing or partial: a partial count is no figure."""
    return None if line is None or line.partial or line.euros is None else line.euros


def month_money(view):
    """{cloud, models, cloud_label, models_label, total, spent, whole, missing, stop, share} of the month (a
    MoneyView): the cloud bill and the model bill with the labels their lines carry (a provider is named only by its
    line, never here), their total only when both are known, `spent` the sum of the lines read (None while none is;
    `whole` False and `missing` each line not read with why, hover text, while one is), the environment's one stop
    line and the total's share of it."""
    lines = {line.source: line for line in view.lines}
    cloud, models = known(lines.get("cloud")), known(lines.get("models"))
    total = round(cloud + models, 2) if cloud is not None and models is not None else None
    share = min(100, round(100 * total / view.stop)) if total is not None and view.stop else None
    read = [line for line in view.lines if known(line) is not None]
    missing = "; ".join(f"{line.label}: {line.origin or 'not read'}" for line in view.lines if known(line) is None)
    return {"cloud": cloud, "models": models, "total": total, "stop": view.stop, "share": share,
            "spent": round(sum(known(line) for line in read), 2) if read else None, "whole": not missing,
            "missing": missing or None,
            "cloud_label": lines["cloud"].label if "cloud" in lines else "Cloud",
            "models_label": lines["models"].label if "models" in lines else "Models"}


def remake(world):
    """{low, high, hours, at_least_hours, unknown, why} of the whole remake (state/screens.remake_money: prepare's
    one-shot figure of the prop route, the takes waiting on lost inputs counted, plus the holes price of every paid
    step off it): its likely and high euros, its likely hours only when every step is timed, else the floor; the
    steps and layers with no price; `why` the hover text while a part is missing or stale (no figure then)."""
    found = screens.remake_money(world)
    eta = found["eta"]
    return {"low": found["likely"], "high": found["high"],
            "hours": round(eta["likely_minutes"] / 60, 1) if eta["likely_minutes"] is not None else None,
            "at_least_hours": round(eta["at_least_minutes"] / 60, 1) if eta["at_least_minutes"] else None,
            "unknown": found["unpriced"], "why": "; ".join(found["stale"]) or None}


def eta_hours(eta):
    """(likely, high) hours of a batch's ETA (screens.basket_eta), each None while a step is not timed."""
    return tuple(None if eta[name] is None else round(eta[name] / 60, 1) for name in ("likely_minutes", "high_minutes"))


def made_of(card):
    """(made, needed) of a place: its steps standing accepted, of all its steps."""
    steps = [step for layer in card.layers for step in layer.steps]
    return sum(step.state == "accepted" for step in steps), len(steps)


def tone_of(row):
    """A place's state colour: its worst kind of hole, `done` with none, `idle` while not checked or unknown."""
    if row is None or row["not_checked"]:
        return "idle"
    return KIND_TONES[row["worst"]] if row["worst"] else "done"


def place_tiles(world, names, rows):
    """{place: {place, href, name, about, picture, made, needed, gaps, tone, inside}} of every place of the
    environment (a WorldState), `names` their short names, `about` its look's long words (hover text), with its row of
    holes.per_place: gaps None while its holes are not known."""
    by_place = {row["place"]: row for row in rows}
    shelf = library.library()
    found = {}
    for style, card in [(style, card) for engine in world.engines for style in engine.styles for card in style.places]:
        row = by_place.get(card.place)
        picture = card.still or card.hero
        made, needed = made_of(card)
        found[card.place] = {"place": card.place, "href": f"/place/{card.place}/",
                             "name": names.get(card.place, card.place),
                             "about": style.label if style.short else None,
                             "picture": screens.thumb(picture) or screens.library_picture(shelf, card.place),
                             "made": made, "made_tip": f"made {made} of {needed}", "needed": needed,
                             "gaps": None if row is None or row["not_checked"] else row["holes"],
                             "tone": tone_of(row), "inside": 0}
    return found


def parent_of(world, node, known):
    """The place or shell `node` sits within (WorldState.within), None for an outside one; a parent holding no place
    of `known` counts as none, so the tiles never lead to an empty level."""
    parent = world.within.get(node)
    return parent if parent and inside_of(world, parent, known) else None


def inside_of(world, node, known):
    """The places of `known` (in their order) sitting within `node`, however deep."""
    found = []
    for place in known:
        above = world.within.get(place)
        seen = {place}
        while above and above not in seen:
            if above == node:
                found.append(place)
                break
            seen.add(above)
            above = world.within.get(above)
    return found


def nested_tile(world, node, by_place, names):
    """A tile of a place or shell with places inside: its progress and gaps summed over itself and every place within
    it, its worst tone, its own picture else the first one inside; it opens one level down (`/?in=<node>`)."""
    inside = inside_of(world, node, by_place)
    parts = [by_place[place] for place in ([node] if node in by_place else []) + inside]
    checked = [part["gaps"] for part in parts if part["gaps"] is not None]
    made, needed = sum(part["made"] for part in parts), sum(part["needed"] for part in parts)
    tones = {part["tone"] for part in parts}
    tone = next((tone for tone in KIND_TONES.values() if tone in tones), "done" if tones == {"done"} else "idle")
    return {"place": node, "href": f"/?in={node}", "name": world.shells.get(node) or names.get(node, node),
            "about": f"{len(inside)} places inside", "picture": next((part["picture"] for part in parts
                                                                     if part["picture"]), None),
            "made": made, "needed": needed, "made_tip": f"made {made} of {needed}",
            "gaps": sum(checked) if checked else None, "tone": tone, "inside": len(inside)}


def tiles(world, names, rows, at=None):
    """[tile] of the places and shells sitting directly within `at` (None: the outside ones), shapes first: one
    holding places is a nested_tile; when `at` is a place, its own tile (to its Place screen) comes first."""
    by_place = place_tiles(world, names, rows)
    level = [node for node in [*by_place, *world.shells] if node != at and parent_of(world, node, by_place) == at
             and (node in by_place or inside_of(world, node, by_place))]
    found = [by_place[at]] if at in by_place else []
    for node in sorted(set(level), key=lambda node: first_index(world, node, by_place)):
        found.append(nested_tile(world, node, by_place, names) if inside_of(world, node, by_place)
                     else by_place[node])
    return found


def first_index(world, node, by_place):
    """Where a node sorts among its level: its own place's place in the environment, else its first inside place's."""
    order = list(by_place)
    return min(order.index(place) for place in ([node] if node in by_place else []) + inside_of(world, node, by_place))


def trail(world, names, at):
    """[{name, href}] from the environment down to `at` (the places and shells holding it, outermost first); None
    when `at` holds no place."""
    known = [card.place for engine in world.engines for style in engine.styles for card in style.places]
    if not inside_of(world, at, known):
        return None
    found, node = [], at
    while node:
        found.insert(0, {"name": world.shells.get(node) or names.get(node, node), "href": f"/?in={node}"})
        node = parent_of(world, node, known)
    return found


def scene_row(node):
    """A node of present.prim_tree as the tree component's row (c/tree.html): its label and gap count, its worst
    kind's colour, its counts by kind as hover text and as its side panel's state."""
    worst = node["kinds"][0][0] if node["kinds"] else None
    tone = KIND_TONES[worst] if worst else "done"
    tip = ", ".join(f"{count} {KIND_LABELS[kind]}" for kind, count in node["kinds"])
    return {"label": node["name"], "count": node["count"], "tone": tone, "tip": tip,
            "panel": {"title": node["name"], "state": tip, "tone": tone}}


def branch_at(tree, path):
    """The node of a present.prim_tree at `path` (its names below the root, "/"-joined; "" the root), or None."""
    node = tree
    for name in [part for part in path.split("/") if part]:
        node = next((child for child in node["children"] if child["name"] == name), None)
        if node is None:
            return None
    return node


def branch_rows(node, path, item_panel, url):
    """[row] of a scene-tree branch, one level: a row per hole hanging at the branch itself, then a row per child;
    a child with children loads them from `url(its path)` when it opens, a leaf opens `item_panel(hole, title)` of
    its first hole."""
    rows = []
    if node["children"]:
        for hole in node["holes"]:
            row = scene_row({"name": hole.row or hole.id, "count": 1, "kinds": [(holes.kind_of(hole), 1)]})
            rows.append({**row, "panel": {**row["panel"], **item_panel(hole, row["label"])}})
    for child in node["children"]:
        row = scene_row(child)
        if child["children"]:
            row["children_url"] = url(f"{path}/{child['name']}".lstrip("/"))
        elif child["holes"]:
            row["panel"] = {**row["panel"], **item_panel(child["holes"][0], child["name"])}
        rows.append(row)
    return rows


def chain_words(chain, paid):
    """A hole's price as its panel says it: the measured likely to high of its chain (a "+" while a node of it has
    no measured price), "free" for an unpaid node with no paid node in its chain, else "unknown"."""
    if chain and chain["priced"]:
        return f"EUR {chain['likely']:.2f}–{chain['high']:.2f}{' +' if chain['unpriced'] else ''}"
    return "free" if paid is False and not (chain and chain["unpriced"]) else "unknown"


def hole_action(hole, step):
    """{action, action_label, body, reason} of the one thing the owner may do for a hole on its filling step (a
    StepDetail, None for none): accept its waiting output, reject one that fails a check, waive the failed check of
    its accepted one; {} when there is nothing. `body` is the JSON the panel's button posts."""
    if step is None:
        return {}
    if step.waiting and hole.rule == "gate":
        taken, url, label, more, reason = step.waiting, "/api/decisions", "Reject", {"decision": "reject"}, True
    elif step.waiting:
        taken, url, label, more, reason = step.waiting, "/api/decisions", "Accept", {"decision": "accept"}, False
    elif step.accepted and hole.rule == "gate" and hole.gates:
        taken, url, label, more, reason = step.accepted, "/api/waivers", "Waive", {"check": hole.gates[0]}, True
    else:
        return {}
    body = {"node": step.node, "output": taken.output, **more}
    return {"action": url, "action_label": label, "body": json.dumps(body), "reason": reason}


def hole_panel(hole, place, step, price):
    """The side panel of one hole: its state, colour, picture, its chain's price, the box the 3D view frames and its
    one action on `step` (hole_action; None: none). `price` the HolesPrice."""
    kind = holes.kind_of(hole)
    chain = screens.chain_price(price, place, hole.node) if hole.node else None
    return {"state": KIND_LABELS[kind], "tone": KIND_TONES[kind], "picture": screens.thumb(hole.picture),
            "price": chain_words(chain, hole.paid), "hole": hole.id if hole.low is not None else None,
            **hole_action(hole, step)}


def gaps_by_kind(total):
    """[{kind, label, tone, count}] of the environment's holes (a HolesTotal: a lost input once however many places
    read it), worst kind first; each count None before any holes check."""
    return [{"kind": kind, "label": KIND_LABELS[kind], "tone": KIND_TONES[kind],
             "count": None if total is None else total.counts.get(kind, 0)} for kind, _ in holes.KINDS]


def places_complete(rows):
    """(complete, of): the places checked with no hole, of every place."""
    return sum(not row["not_checked"] and not row["holes"] for row in rows), len(rows)


def measured_prices(price):
    """(measured, paid) of the paid steps in any hole's chain: how many have a measured price; (None, None) without a
    current record."""
    if price is None or price.stale:
        return None, None
    money = holes.money_of(holes.summed(price.nodes))
    return (money["measured"], money["paid"]) if money else (0, 0)


def billed_days(bill_days):
    """[Billed] a day of the month's bills as read each day (MoneyView.bill_days, the month so far): each day what
    the month grew by since the reading before, the cloud's and the model calls' known figures together."""
    found, before = [], 0.0
    for day in bill_days:
        so_far = (day.get("cloud") or 0.0) + (day.get("models") or 0.0)
        found.append(Billed(node="bill", euros=round(max(0.0, so_far - before), 2), minutes=None, started=day["day"]))
        before = max(before, so_far)
    return found


def timeline(billed, month, today=None):
    """[{day, euros, height}] of the month's paid runs (launch.backend.Billed) by day, every day from the month's
    first to today (or the last billed day), `height` a percent of the costliest day; [] with nothing billed."""
    days = defaultdict(float)
    for line in billed:
        days[line.started[:10]] += line.euros
    if not days:
        return []
    day = datetime.date.fromisoformat(f"{month}-01")
    last = max(datetime.date.fromisoformat(max(days)), min(today or datetime.date.today(),
                                                           (day + datetime.timedelta(days=31)).replace(day=1)
                                                           - datetime.timedelta(days=1)))
    top = max(days.values()) or 1.0
    found = []
    while day <= last:
        euros = days.get(day.isoformat(), 0.0)
        found.append({"day": day.isoformat(), "euros": round(euros, 2), "height": round(100 * euros / top)})
        day += datetime.timedelta(days=1)
    return found
