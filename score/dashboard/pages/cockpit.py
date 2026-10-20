"""The cockpit's numbers (#42): what the five screens show, as numbers and states only, never sentences. Read from the
models of state/models.py and the runner's price record through state/holes.py; nothing is priced or judged here.
A number the runner does not give is None, which a page shows as a grey "unknown" state, never as 0."""
import datetime
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
    """{cloud, models, cloud_label, models_label, total, stop, share} of the month (a MoneyView): the cloud bill and
    the model bill with the labels their lines carry (a provider is named only by its line, never here), their total
    only when both are known, the environment's one stop line and the total's share of it."""
    lines = {line.source: line for line in view.lines}
    cloud, models = known(lines.get("cloud")), known(lines.get("models"))
    total = round(cloud + models, 2) if cloud is not None and models is not None else None
    share = min(100, round(100 * total / view.stop)) if total is not None and view.stop else None
    return {"cloud": cloud, "models": models, "total": total, "stop": view.stop, "share": share,
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


def made_of(card):
    """(made, needed) of a place: its steps standing accepted, of all its steps."""
    steps = [step for layer in card.layers for step in layer.steps]
    return sum(step.state == "accepted" for step in steps), len(steps)


def tone_of(row):
    """A place's state colour: its worst kind of hole, `done` with none, `idle` while not checked or unknown."""
    if row is None or row["not_checked"]:
        return "idle"
    return KIND_TONES[row["worst"]] if row["worst"] else "done"


def tiles(world, names, rows):
    """[{place, href, name, picture, made, needed, gaps, tone}] of every place of the environment (a WorldState),
    `names` their titles, with its row of holes.per_place: gaps None while its holes are not known."""
    by_place = {row["place"]: row for row in rows}
    shelf = library.library()
    found = []
    for card in [card for engine in world.engines for style in engine.styles for card in style.places]:
        row = by_place.get(card.place)
        picture = card.still or card.hero
        made, needed = made_of(card)
        found.append({"place": card.place, "href": f"/place/{card.place}/",
                      "name": names.get(card.place, card.place),
                      "picture": screens.thumb(picture) or screens.library_picture(shelf, card.place),
                      "made": made,
                      "needed": needed, "gaps": None if row is None or row["not_checked"] else row["holes"],
                      "tone": tone_of(row)})
    return found


def scene_tree(node):
    """A node of present.prim_tree as the tree component's (c/tree.html): its label and gap count, its worst kind's
    colour, its counts by kind as hover text, its side panel's title and state; its children likewise."""
    worst = node["kinds"][0][0] if node["kinds"] else None
    tone = KIND_TONES[worst] if worst else "done"
    tip = ", ".join(f"{count} {KIND_LABELS[kind]}" for kind, count in node["kinds"])
    return {"label": node["name"], "count": node["count"], "tone": tone, "tip": tip, "open": True,
            "panel": {"title": node["name"], "state": tip, "tone": tone},
            "children": [scene_tree(child) for child in node["children"]]}


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
