"""The cockpit's numbers (#42): what the five screens show, as numbers and states only, never sentences. Read from the
models of state/models.py and the runner's price record through state/gaps.py; nothing is priced or judged here.
A number the runner does not give is None, which a page shows as a grey "unknown" state, never as 0."""
import datetime
import json

from score.dashboard.state import gaps, screens

PLACES = "/places/"  # the Places screen: the environment's places (today's one environment)
# a gap kind's state colour (design/tokens/colours.css) and its short label
KIND_TONES = {"lost": "gap-lost", "route": "gap-route", "missing": "gap-missing", "gate": "gap-gate"}
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
    """{low, high, hours, at_least_hours, unknown, why, approved, in_design} of the remake of the places whose design
    is approved (state/screens.remake_money: prepare's one-shot figure of their prop route plus the gaps price of
    every paid step off it there): its likely and high euros, its likely hours only when every step is timed, else
    the floor; the steps and layers with no price; `why` the hover text while a part is missing or stale (no figure
    then); how many places are approved and still in design (no figure before one is approved)."""
    found = screens.remake_money(world)
    eta = found["eta"]
    return {"low": found["likely"], "high": found["high"], "approved": found["approved"],
            "in_design": found["in_design"],
            "hours": round(eta["likely_minutes"] / 60, 1) if eta["likely_minutes"] is not None else None,
            "at_least_hours": round(eta["at_least_minutes"] / 60, 1) if eta["at_least_minutes"] else None,
            "unknown": found["unpriced"], "why": "; ".join(found["stale"]) or None,
            "estimate": estimate(found["estimate"])}


def estimate(found):
    """{low, high, hours, at_least_hours, untimed, unknown, unknown_names, places, waiting, of, why} of the remake's
    estimate from the scene inventories (screens.estimate), None before prepare read them: its likely and high euros,
    its likely hours only when every layer is timed, else the floor, its layers with no price, how many places it
    covers of all, `why` while it is stale (no figure then)."""
    if found is None:
        return None
    eta = found["eta"]
    return {"low": found["likely"], "high": found["high"],
            "hours": round(eta["likely_minutes"] / 60, 1) if eta.get("likely_minutes") is not None else None,
            "at_least_hours": round(eta["at_least_minutes"] / 60, 1) if eta.get("at_least_minutes") else None,
            "untimed": eta.get("untimed") or 0, "unknown": len(found["unpriced"]),
            "unknown_names": ", ".join(found["unpriced"]), "places": found["places"], "waiting": found["waiting"],
            "of": found["places"] + found["waiting"], "why": found["stale"]}


def eta_hours(eta):
    """(likely, high) hours of a batch's ETA (screens.basket_eta), each None while a step is not timed."""
    return tuple(None if eta[name] is None else round(eta[name] / 60, 1) for name in ("likely_minutes", "high_minutes"))


def made_of(card):
    """(made, needed) of a place: its steps standing accepted, of all its steps."""
    steps = [step for layer in card.layers for step in layer.steps]
    return sum(step.state == "accepted" for step in steps), len(steps)


def tone_of(row):
    """A place's state colour: its worst kind of gap, `done` with none, `idle` while not checked or unknown."""
    if row is None or row["not_checked"]:
        return "idle"
    return KIND_TONES[row["worst"]] if row["worst"] else "done"


# What a place shows while its scene inventory does not count (screens.design_state), and its hover text.
DESIGN_WORDS = {"draw": ("to draw", "no concept yet: draw it"),
                "review": ("in review", "its concept is not picked: no scene inventory before it is"),
                "read": ("inventory to read", "picked; its scene inventory is not read from this concept yet"),
                "plan": ("plan to make", "its scene inventory is read from its picked concept (its concept page); "
                                         "its plan is not made from it yet"),
                "check": ("gaps to check", "its scene inventory is read; its gaps are not checked from it yet"),
                "design": ("in design", "no place in it has a scene inventory read from its picked concept yet")}


def place_tiles(world, names, rows):
    """{place: {place, href, name, about, picture, made, needed, gaps, tone, holds, more, design, design_tip}} of every
    place of the environment (a WorldState), `names` their short names, `about` its look's long words (hover text),
    `picture` its concept's thumbnail (None: its concept is lost, never a render instead), with its row of
    gaps.per_place: gaps None while its gaps are not known; made, needed and gaps None and its design state in words
    while its scene inventory does not count (CONTEXT.md "scene inventory": no number from an older one)."""
    by_place = {row["place"]: row for row in rows}
    found = {}
    for style, card in [(style, card) for engine in world.engines for style in engine.styles for card in style.places
                        if card.place not in world.parts]:  # a part of another place's outside: no card of its own
        row = by_place.get(card.place)
        design = screens.design_state(world, card.place)
        made, needed = made_of(card) if design is None else (None, None)
        found[card.place] = {"place": card.place,
                             "href": f"/place/{card.place}/" if design is None else f"/concept/{card.place}/",
                             "name": names.get(card.place, card.place),
                             "about": style.label if style.short else None,
                             "picture": screens.thumb(world.concepts.get(card.place)),
                             "made": made, "made_tip": f"made {made} of {needed}", "needed": needed,
                             "gaps": None if row is None or row["not_checked"] else row["gaps"],
                             "tone": tone_of(row), "holds": [], "more": 0, **design_of(design),
                             **steps_of(world, card.place)}
    for node in designed(world, found):
        found[node] = {"place": node, "href": f"/concept/{node}/", "name": names.get(node, node), "about": None,
                       "picture": screens.thumb(world.concepts.get(node)), "made": None, "made_tip": None,
                       "needed": None, "gaps": None, "tone": "idle", "holds": [], "more": 0,
                       **design_of(screens.design_state(world, node) or "design"), **steps_of(world, node)}
    return found


def designed(world, cards):
    """The inside places his kept plans name that have no line of their own yet (WorldState.within beyond `cards`, the
    shells and the parts): a design-only tile each, opening its concept page."""
    return [node for node in world.within if node not in cards and node not in world.shells
            and node not in world.parts]


def steps_of(world, node):
    """{steps, steps_done, steps_tip, plan} of a place's or shell's design steps (screens.design_steps): `plan` the plan
    part of its design page once it has a plan (None before)."""
    steps = screens.design_steps(world, node)
    return {"steps": steps, "steps_done": sum(steps),
            "steps_tip": " · ".join(f"{name} {'yes' if done else 'no'}" for name, done in zip(screens.DESIGN_STEPS, steps)),
            "plan": f"/concept/{node}/#plan-part" if steps[2] else None}


def design_of(design):
    """{design, design_tip} of a design state (DESIGN_WORDS), both None once the place's inventory counts."""
    words, tip = DESIGN_WORDS.get(design, (None, None))
    return {"design": words, "design_tip": tip}


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
    it whose scene inventory counts (none: "in design"), its worst tone, its own concept (None when it has none, never one from inside), `holds` what sits directly in
    it holding places itself (`holder`), `more` how many others sit directly in it; it opens one level down
    (`/?in=<node>`)."""
    inside = inside_of(world, node, by_place)
    parts = [by_place[place] for place in ([node] if node in by_place else []) + inside]
    checked = [part["gaps"] for part in parts if part["gaps"] is not None]
    shown = [part for part in parts if part["design"] is None]
    made = sum(part["made"] for part in shown) if shown else None
    needed = sum(part["needed"] for part in shown) if shown else None
    tones = {part["tone"] for part in parts}
    tone = next((tone for tone in KIND_TONES.values() if tone in tones), "done" if tones == {"done"} else "idle")
    children = [child for child in [*by_place, *world.shells] if parent_of(world, child, by_place) == node]
    holds = [holder(world, child, by_place, names) for child in children if inside_of(world, child, by_place)]
    leaves = [names.get(child, child) for child in children if not inside_of(world, child, by_place)]
    return {"place": node, "href": f"{PLACES}?in={node}", "name": world.shells.get(node) or names.get(node, node),
            "about": ", ".join([f"{held['name']} ({held['count']} {held['unit']})" for held in holds] + leaves),
            "picture": screens.thumb(world.concepts.get(node)),
            "made": made, "needed": needed, "made_tip": f"made {made} of {needed}",
            "gaps": sum(checked) if checked else None, "tone": tone, "holds": holds, "more": len(leaves),
            **design_of(None if shown else "design"), **steps_of(world, node)}


def holder(world, node, by_place, names):
    """{name, picture, count, unit} of a place or shell holding places, as the tile around it names it ("Hangar, 8
    rooms": the places of a shell, or of a place within another, are its rooms), with its concept's thumbnail."""
    count = len(inside_of(world, node, by_place))
    unit = ("room" if node in world.shells or node in world.within else "place") + ("" if count == 1 else "s")
    return {"name": world.shells.get(node) or names.get(node, node), "count": count, "unit": unit,
            "picture": screens.thumb(world.concepts.get(node))}


def head(world, names, rows, at):
    """The place or shell `at` itself, heading the level it opens to (CONTEXT.md "place": a place is its outside, never
    a card beside its inside places, owner 2026-10-20): its concept, progress and gaps as its tile one level up sums
    them; `href` its Place screen, None for a shell (no place of its own)."""
    by_place = place_tiles(world, names, rows)
    own = by_place.get(at)
    return {**nested_tile(world, at, by_place, names),
            "href": f"/place/{at}/" if own and own["design"] is None else None}


def tiles(world, names, rows, at=None):
    """[tile] of the places and shells sitting directly within `at` (None: the outside ones), shapes first: one
    holding places is a nested_tile; `at` itself is no tile but the level's head (`head`)."""
    by_place = place_tiles(world, names, rows)
    level = [node for node in [*by_place, *world.shells] if node != at and parent_of(world, node, by_place) == at
             and (node in by_place or inside_of(world, node, by_place))]
    found = []
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
    known += designed(world, known)
    if not inside_of(world, at, known):
        return None
    found, node = [], at
    while node:
        found.insert(0, {"name": world.shells.get(node) or names.get(node, node), "href": f"{PLACES}?in={node}"})
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
    """[row] of a scene-tree branch, one level: a row per gap hanging at the branch itself, then a row per child;
    a child with children loads them from `url(its path)` when it opens, a leaf opens `item_panel(gap, title)` of
    its first gap."""
    rows = []
    if node["children"]:
        for gap in node["gaps"]:
            row = scene_row({"name": gap.row or gap.id, "count": 1, "kinds": [(gaps.kind_of(gap), 1)]})
            rows.append({**row, "panel": {**row["panel"], **item_panel(gap, row["label"])}})
    for child in node["children"]:
        row = scene_row(child)
        if child["children"]:
            row["children_url"] = url(f"{path}/{child['name']}".lstrip("/"))
        elif child["gaps"]:
            row["panel"] = {**row["panel"], **item_panel(child["gaps"][0], child["name"])}
        rows.append(row)
    return rows


def chain_words(chain, paid):
    """A gap's price as its panel says it: the measured likely to high of its chain (a "+" while a node of it has
    no measured price), "free" for an unpaid node with no paid node in its chain, else "unknown"."""
    if chain and chain["priced"]:
        return f"EUR {chain['likely']:.2f}–{chain['high']:.2f}{' +' if chain['unpriced'] else ''}"
    return "free" if paid is False and not (chain and chain["unpriced"]) else "unknown"


def gap_action(gap, step):
    """{action, action_label, body, reason} of the one thing the owner may do for a gap on its filling step (a
    StepDetail, None for none): accept its waiting output, reject one that fails a check, waive the failed check of
    its accepted one; {} when there is nothing. `body` is the JSON the panel's button posts."""
    if step is None:
        return {}
    if step.waiting and gap.rule == "gate":
        taken, url, label, more, reason = step.waiting, "/api/decisions", "Reject", {"decision": "reject"}, True
    elif step.waiting:
        taken, url, label, more, reason = step.waiting, "/api/decisions", "Accept", {"decision": "accept"}, False
    elif step.accepted and gap.rule == "gate" and gap.gates:
        taken, url, label, more, reason = step.accepted, "/api/waivers", "Waive", {"check": gap.gates[0]}, True
    else:
        return {}
    body = {"node": step.node, "output": taken.output, **more}
    return {"action": url, "action_label": label, "body": json.dumps(body), "reason": reason}


def gap_panel(gap, place, step, price):
    """The side panel of one gap: its state, colour, picture, its chain's price, the box the 3D view frames and its
    one action on `step` (gap_action; None: none). `price` the GapsPrice."""
    kind = gaps.kind_of(gap)
    chain = screens.chain_price(price, place, gap.node) if gap.node else None
    return {"state": KIND_LABELS[kind], "tone": KIND_TONES[kind], "picture": screens.thumb(gap.picture),
            "price": chain_words(chain, gap.paid), "gap": gap.id if gap.low is not None else None,
            **gap_action(gap, step)}


# the Stats screen's gap kinds, most first in a remake: their plain words and hover text
KIND_WORDS = {"missing": ("not made yet", "a part a place needs that no step has made yet"),
              "gate": ("failing a check", "made, but a check fails on it"),
              "route": ("steps of the route still to do", "a step of a place's route that has not run yet"),
              "lost": ("inputs lost", "a file a step reads that is gone; counted once however many places read it")}


def gaps_by_kind(total):
    """[{kind, label, tip, tone, href, count}] of the environment's gaps (a GapsTotal: a lost input once however
    many places read it) in KIND_WORDS' order, each opening the Environment filtered to it; each count None before
    any gaps check."""
    return [{"kind": kind, "label": label, "tip": tip, "tone": KIND_TONES[kind], "href": f"{PLACES}?kind={kind}",
             "count": None if total is None else total.counts.get(kind, 0)} for kind, (label, tip) in KIND_WORDS.items()]


def of_kind(rows, kind):
    """The place rows (gaps.per_place) counting only their gaps of `kind`: its count as the place's gaps, `kind` its
    worst while it has any."""
    return [{**row, "gaps": row["counts"][kind], "worst": kind if row["counts"][kind] else None} for row in rows]


def places_complete(rows):
    """(complete, of): the places checked with no gap, of every place."""
    return sum(not row["not_checked"] and not row["gaps"] for row in rows), len(rows)


def measured_prices(price):
    """(measured, paid) of the paid steps in any gap's chain: how many have a measured price; (None, None) without a
    current record."""
    if price is None or price.stale:
        return None, None
    money = gaps.money_of(gaps.summed(price.nodes))
    return (money["measured"], money["paid"]) if money else (0, 0)


def spend_by_day(bill_days, ledger_days, month, today=None):
    """[{day, euros, whole}] every day of `month` up to today (its last day for a past month): the bills' growth over
    the day when its reading and the day before's both hold every line (`whole`; the 1st grows from 0), else the
    ledgers' own count of the day when above 0 (low: they miss what the bills hold, so their 0 says nothing), else
    euros None: not known, never 0."""
    read = {row["day"]: row["cloud"] + row["models"] for row in bill_days
            if row.get("cloud") is not None and row.get("models") is not None}
    ledger = {row["day"]: (row.get("cloud") or 0.0) + (row.get("models") or 0.0) for row in ledger_days}
    ledger = {day: euros for day, euros in ledger.items() if euros > 0}
    first = datetime.date.fromisoformat(f"{month}-01")
    end = (first + datetime.timedelta(days=31)).replace(day=1) - datetime.timedelta(days=1)
    found, day = [], first
    while day <= min(today or datetime.date.today(), end):
        key = day.isoformat()
        before = 0.0 if day == first else read.get((day - datetime.timedelta(days=1)).isoformat())
        if key in read and before is not None:
            found.append({"day": key, "euros": round(max(0.0, read[key] - before), 2), "whole": True})
        else:
            found.append({"day": key, "euros": round(ledger[key], 2) if key in ledger else None, "whole": False})
        day += datetime.timedelta(days=1)
    return found


CHART = {"width": 1000, "height": 230, "left": 64, "bottom": 34, "top": 12}  # the day chart's SVG box, in its units


def scale_top(highest):
    """The day chart's one scale: the first 1, 2, 2.5 or 5 times a power of ten at or above `highest` (1 for 0)."""
    if highest <= 0:
        return 1.0
    power = 1.0
    while power * 10 < highest:
        power *= 10
    return next(step * power for step in (1, 2, 2.5, 5, 10) if step * power >= highest)


def day_chart(days):
    """The day chart of spend_by_day: {width, height, base, left, bars [{x, y, w, h, day, euros, whole}], gaps [{x,
    w, day}] (the days not known), ticks [{y, euros}] (0, half and the top of the one scale), labels [{x, day}] (the
    1st, every 5th and the last day)}; None with no day."""
    if not days:
        return None
    box = CHART
    base, tall = box["height"] - box["bottom"], box["height"] - box["bottom"] - box["top"]
    top = scale_top(max((day["euros"] for day in days if day["euros"] is not None), default=0.0))
    slot = (box["width"] - box["left"]) / len(days)
    bars, gaps, labels = [], [], []
    for index, day in enumerate(days):
        x, width = round(box["left"] + index * slot + slot * 0.15, 1), round(slot * 0.7, 1)
        if day["euros"] is None:
            gaps.append({"x": x, "w": width, "day": day["day"]})
        else:
            height = round(tall * day["euros"] / top, 1)
            bars.append({"x": x, "w": width, "y": round(base - height, 1), "h": height, **day})
        number = int(day["day"][-2:])
        if number == 1 or number % 5 == 0 or index == len(days) - 1:
            labels.append({"x": round(box["left"] + (index + 0.5) * slot, 1), "day": number})
    ticks = [{"y": round(base - tall * share, 1), "euros": top * share} for share in (0, 0.5, 1)]
    return {"width": box["width"], "height": box["height"], "base": base, "left": box["left"],
            "bars": bars, "gaps": gaps, "ticks": ticks, "labels": labels}


def unplaced(total, days):
    """The month's euros no day holds (its known total less the days' known euros); None while the total is not
    known or every euro sits on a day."""
    if total is None:
        return None
    left = round(total - sum(day["euros"] for day in days if day["euros"] is not None), 2)
    return left if left >= 0.5 else None


def measured_share(batch):
    """The percent of the remake's likely euros (screens.batch) priced from measured runs (the rest estimated per
    unit times count); None while the remake has no likely figure."""
    likely = batch["total"]["likely"]
    if not likely:
        return None
    return round(100 * batch["total"]["measured"]["likely"] / likely)
