"""Each cockpit screen's data as one small JSON object: numbers, states, names and picture links, no sentences (#42).
Read from the same source as the pages (state.source(): the store or the export), the runner's spend, the library
and the basket; nothing is priced, counted or judged here that the runner did not write (ADR-0006).

    environment(source, spend, library)        # GET /api/screens/environment
    place(source, place, library)              # GET /api/screens/place/<place>
    buy(items, choices, spend)                 # GET /api/screens/buy
    stats(source, spend)                       # GET /api/screens/stats
    library_counts(library)                    # GET /api/screens/library

Money: the month is the runner's cost lines (the cloud bill; the model calls' bill from its billing export, else the
owner's books figure, else None); the stop is the one the last batch's yes wrote (its high plus 10%), never a figure set here. The
remake is prepare's one-shot figure of the prop route (every take, those waiting on lost inputs counted) plus the
holes price of every other paid step (ROUTE leaves out the prop route's steps, which prepare prices per take).
"""
from collections import Counter

from score.dashboard.checkout import pricing
from score.dashboard.state import groups, holes as hole_sums, money

# The prop route's stages, priced per take by prepare; the holes price adds only the other paid steps.
ROUTE = ("props-inputs", "closeup", "pixal", "finish-route-", "surfaces-", "likeness")
BUFFER = 1.10  # a batch's stop: its high plus 10% (CONTEXT.md "batch"; checkout/flow.BUFFER writes it)
MEASURED = ("measured runs", "per unit × counted", "per unit × forecast")


def on_route(node):
    return node.split("@", 1)[0].startswith(ROUTE)


def thumb(ref):
    """A store picture's thumbnail link, or None."""
    return (ref.thumb_url or ref.url) if ref else None


def library_picture(library, place):
    """The thumbnail link of the library's picture of a place: its place entry, else the first pictured entry made
    there; None when the library has none."""
    if library is None:
        return None
    entries = [entry for entry in library.entries() if entry.picture]
    found = next((entry for entry in entries if entry.kind == "place" and entry.entry_id == place), None) or \
        next((entry for entry in entries if entry.place == place), None)
    return f"/library-files/thumbs/{found.picture}.jpg" if found else None


def picture_of(card, library):
    """(link, where from) of a place's picture: the store's (its hero, else its film's still), else the library's."""
    stored = thumb(card.hero) or thumb(card.still)
    if stored:
        return stored, "store"
    found = library_picture(library, card.place)
    return (found, "library") if found else (None, None)


def steps_of(card):
    return [step for group in card.layers for step in group.steps]


def progress(card):
    """{made, needed}: the place's line's steps standing accepted, of all its steps."""
    found = steps_of(card)
    return {"made": sum(1 for step in found if step.state == "accepted"), "needed": len(found)}


def complete(card):
    """A place is complete when its library step stands accepted (score/CLAUDE.md, `library@<place>`)."""
    return any(step.stage == "library" and step.state == "accepted" for step in steps_of(card))


def cards(world):
    return [card for engine in world.engines for style in engine.styles for card in style.places]


def gap_counts(found):
    """{kind: count} of a place's holes, a lost input once (hole kinds: lost, route, missing, gate)."""
    return dict(Counter(hole_sums.kind_of(hole) for hole in found))


def worst(counts):
    return next((kind for kind, _ in hole_sums.KINDS if counts.get(kind)), None)


def priced(prices):
    """{likely, high, priced, unpriced} of {node: price}: the sums of the nodes with a measured basis, how many of
    them, and how many have none."""
    known = [price for price in prices.values() if price.get("basis") in MEASURED]
    return {"likely": round(sum(price["likely_euros"] for price in known), 2),
            "high": round(sum(price["high_euros"] for price in known), 2),
            "priced": len(known), "unpriced": len(prices) - len(known)}


def remake_money(world):
    """The whole remake: prepare's figure plus the holes price of every paid step off the prop route, None while
    either part is missing or stale (the rule of every price record here); each part apart, its ETA (a range only
    when both parts have one, else at least the longer floor), and why it is stale."""
    remake, price = world.remake, world.holes_price
    rest = priced({node: found for node, found in price.nodes.items() if not on_route(node)}) if price else None
    route = {"likely": remake.likely_euros, "high": remake.high_euros, "unpriced": len(remake.unpriced),
             **remake.counts} if remake else None
    parts = [part for part in (route, rest) if part is not None]
    stale = [why for why in ((remake.stale if remake else "prepare has not run"),
                             (price.stale if price else "the holes have not been priced")) if why]
    whole = None if stale or route["likely"] is None or route["high"] is None else \
        {"likely": round(route["likely"] + rest["likely"], 2), "high": round(route["high"] + rest["high"], 2)}
    return {**(whole or {"likely": None, "high": None}), "route": route, "rest": rest,
            "unpriced": sum(part["unpriced"] for part in parts), "eta": eta_of(remake, price),
            "made_at": remake.made_at if remake else None, "stale": stale}


def eta_of(remake, price):
    """{likely_minutes, high_minutes, at_least_minutes, untimed} of both parts (they run side by side, so the longer
    counts): a range only when both have one; None throughout while either part is missing."""
    if remake is None or price is None or price.eta is None:
        return {"likely_minutes": None, "high_minutes": None, "at_least_minutes": None, "untimed": None}
    etas = (remake.eta, price.eta)
    timed = all(eta.get("likely_minutes") is not None for eta in etas)
    return {"likely_minutes": max(eta["likely_minutes"] for eta in etas) if timed else None,
            "high_minutes": max(eta["high_minutes"] for eta in etas) if timed else None,
            "at_least_minutes": max(eta.get("at_least_minutes") or 0.0 for eta in etas),
            "untimed": remake.eta.get("untimed", 0) + len(price.eta.get("unknown") or [])}


def month_money(spend):
    """{month, cloud, models, total, whole, stop, against_stop, in_flight, refused}: the month's lines (None: not
    read), their total (whole False while any is missing), and the environment's spend since its first stop line plus
    what is in flight against the stop the last batch's yes wrote."""
    lines = {line.source: line.euros for line in money.lines(spend)}
    total = money.total(money.lines(spend))
    return {"month": money.this_month(spend), "cloud": lines.get("cloud"), "models": lines.get("models"),
            "total": total.euros, "whole": total.whole, "stop": spend.ceiling,
            "against_stop": None if spend.spent is None else round(spend.spent + (spend.reserved or 0.0), 2),
            "in_flight": spend.reserved, "refused": spend.paid_refused is not None}


def environment(source, spend, library):
    """The Environment screen: the month against the stop, the remake's price and ETA, the gaps by kind, a tile a
    place (picture, progress, gap count, worst kind, its takes)."""
    world = source.world_state(spend)
    takes = world.remake.places if world.remake else {}
    places = []
    for card in cards(world):
        counts = gap_counts(source.holes(card.place))
        link, origin = picture_of(card, library)
        places.append({"place": card.place, "title": groups.place_title(card.place), "status": card.status,
                       "picture": link, "picture_from": origin, "progress": progress(card),
                       "complete": complete(card), "gaps": sum(counts.values()), "worst": worst(counts),
                       "takes": takes.get(card.place)})
    return {"made_at": world.made_at, "money": month_money(spend), "remake": remake_money(world),
            "gaps": (world.holes_total.counts if world.holes_total else {}), "places": places}


def chain_price(price, place, node):
    """{likely, high, priced, unpriced} of a hole's chain (every paid node it names once); None with no current
    holes price or no chain."""
    if price is None or price.stale:
        return None
    chain = price.chains.get(place, {}).get(node)
    return priced({each: price.nodes[each] for each in chain or [] if each in price.nodes}) if chain else None


def web3d_link(source, place, library):
    """(link, where from) of the place's 3D: its fresh web copy, else the library place entry's web GLB."""
    if source.web3d(place):
        return f"/web/{place}/{place}.glb", "store"
    entry = next((entry for entry in (library.entries() if library else [])
                  if entry.kind == "place" and entry.entry_id == place and entry.web3d), None)
    return (f"/library-files/files/{entry.web3d.sha}", "library") if entry else (None, None)


def place(source, place, library):
    """The Place screen: its picture and 3D, its steps with their states, its holes as the scene tree's items (prim
    path, kind, the node that fills it) and each filling node's chain price once (`prices`)."""
    world = source.world_state()
    card = next(found for found in cards(world) if found.place == place)
    found = source.holes(place)
    link, origin = picture_of(card, library)
    model, model_from = web3d_link(source, place, library)
    price = world.holes_price
    nodes = sorted({hole.node for hole in found if hole.node})
    counts = gap_counts(found)
    return {"place": place, "title": groups.place_title(place), "status": card.status, "picture": link,
            "picture_from": origin, "web3d": model, "web3d_from": model_from, "view": f"/view/{place}",
            "progress": progress(card), "complete": complete(card), "gaps": counts, "worst": worst(counts),
            "takes": (world.remake.places.get(place) if world.remake else None),
            "steps": [{"node": step.node, "stage": step.stage, "label": step.label, "state": step.state,
                       "paid": step.paid, "thumb": step.thumb} for step in steps_of(card)],
            "items": [{"id": hole.id, "prim": hole.prim, "kind": hole_sums.kind_of(hole), "row": hole.row,
                       "node": hole.node, "paid": hole.paid, "work": hole.work,
                       "picture": thumb(hole.picture)} for hole in found],
            "prices": {node: chain_price(price, place, node) for node in nodes},
            "price_stale": bool(price is None or price.stale)}


def buy(items, choices, spend):
    """The Buy screen: the basket's items (the runner's plan, priced by it) with the owner's choice, the chosen
    ones' total, their ETA (a range only when every node has measured minutes) and the stop their yes would write;
    the whole basket's total beside (`basket`), each node once."""
    rows = []
    for item in items:
        totals = item["totals"]
        rows.append({"id": item["id"], "title": item.get("title"), "place": item.get("place"),
                     "places": item.get("places", []), "layers": item.get("layers", []),
                     "likely": totals["likely_euros"], "high": totals["high_euros"],
                     "guessed": totals.get("guessed_euros", 0.0), "nodes": totals["nodes"],
                     "unmeasured": len(totals.get("unmeasured", [])), "blocked": bool(item.get("missing")),
                     "choice": choices.get(item["id"])})
    chosen = [item for item in items if choices.get(item["id"]) == "buy"]
    nodes = pricing.basket_prices(chosen)
    totals = pricing.totals(nodes)
    return {"items": rows, "chosen": len(chosen), "total": total_of(totals),
            "basket": total_of(pricing.totals(pricing.basket_prices(items))),
            "eta": basket_eta(nodes), "stop": round(pricing.cleared_high(totals) * BUFFER, 2) if nodes else None,
            "money": month_money(spend)}


def total_of(totals):
    """{likely, high, guessed, nodes, unmeasured} of pricing.totals."""
    return {"likely": totals["likely_euros"], "high": totals["high_euros"], "guessed": totals["guessed_euros"],
            "nodes": totals["nodes"], "unmeasured": len(totals["unmeasured"])}


def basket_eta(nodes):
    """{likely_minutes, high_minutes, untimed} of the chosen nodes (pricing.span: each line's minutes summed, the
    longest line or the whole over the jobs at once); None minutes while any node has none, never a part as the
    whole."""
    untimed = sum(1 for found in nodes.values() if found.get("likely_minutes") is None)
    if untimed or not nodes:
        return {"likely_minutes": None, "high_minutes": None, "untimed": untimed}
    return {"likely_minutes": pricing.span(nodes, "likely_minutes", pricing.DEFAULT_JOBS),
            "high_minutes": pricing.span(nodes, "high_minutes", pricing.DEFAULT_JOBS), "untimed": 0}


def stats(source, spend):
    """The Stats screen: the month's money by source against the stop, its days (`bill_days` the bills as read each
    day, `days` the ledgers' own counts, which miss what the bills hold), the share of paid steps with a measured
    price, the gaps by kind and the places complete."""
    world = source.world_state(spend)
    price = world.holes_price
    bases = Counter(found.get("basis") for found in price.nodes.values()) if price else Counter()
    measured = sum(count for basis, count in bases.items() if basis in MEASURED)
    places = cards(world)
    return {"made_at": world.made_at, "money": month_money(spend), "bill_days": spend.bill_days, "days": spend.days,
            "prices": {"measured": measured, "steps": sum(bases.values()), "by_basis": dict(bases),
                       "stale": bool(price is None or price.stale)},
            "remake_layers": world.remake.counts if world.remake else None,
            "gaps": (world.holes_total.counts if world.holes_total else {}),
            "places": {"complete": sum(1 for card in places if complete(card)), "total": len(places)}}


def library_counts(library):
    """The Library screen's counts: each kind's entries, by state, pictured and scored."""
    if library is None:
        return {"kinds": [], "total": 0}
    by_kind = {}
    for entry in library.entries():
        counts = by_kind.setdefault(entry.kind, Counter())
        counts.update({"count": 1, entry.state: 1, "pictured": bool(entry.picture), "scored": entry.score is not None})
    from score.dashboard.state.library import KINDS
    order = [kind for kind, _ in KINDS] + sorted(set(by_kind) - {kind for kind, _ in KINDS})
    return {"kinds": [{"kind": kind, **{name: by_kind.get(kind, Counter())[name] for name in
                                        ("count", "draft", "locked", "withdrawn", "pictured", "scored")}}
                      for kind in order], "total": sum(counts["count"] for counts in by_kind.values())}
