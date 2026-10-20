"""Each cockpit screen's data as one small JSON object: numbers, states, names and picture links, no sentences (#42).
Read from the same source as the pages (state.source(): the store or the export), the runner's spend, the library
and the basket; nothing is priced, counted or judged here that the runner did not write (ADR-0006).

    environment(source, spend)                 # GET /api/screens/environment
    place(source, place, library)              # GET /api/screens/place/<place>
    buy(items, choices, spend)                 # GET /api/screens/buy
    stats(source, spend)                       # GET /api/screens/stats
    library_counts(library)                    # GET /api/screens/library

Money: the month is the runner's cost lines (the cloud bill; the model calls' bill from its billing export, else the
owner's books figure, else None); the stop is the one the last batch's yes wrote (its high plus 10%), never a figure set here. The
remake is prepare's one-shot figure of the prop route (every take, those waiting on lost inputs counted) plus the
gaps price of every other paid step (ROUTE leaves out the prop route's steps, which prepare prices per take).
"""
from collections import Counter

from score.dashboard.checkout import pricing
from score.dashboard.proposals import benchmarks
from score.dashboard.state import groups, gaps as gap_sums, money

# The prop route's stages, priced per take by prepare; the gaps price adds only the other paid steps.
ROUTE = ("props-inputs", "closeup", "pixal", "finish-route-", "surfaces-", "likeness")
BUFFER = 1.10  # a batch's stop: its high plus 10% (CONTEXT.md "batch"; checkout/flow.BUFFER writes it)
MEASURED = ("measured runs", "per unit × counted", "per unit × forecast")


def on_route(node):
    return node.split("@", 1)[0].startswith(ROUTE)


def thumb(ref):
    """A store picture's thumbnail link, or None."""
    return (ref.thumb_url or ref.url) if ref else None


def picture_of(world, place):
    """(link, where from) of a place's picture: its concept's thumbnail, else (None, None): a lost concept is a gap,
    never filled with a render (owner, 2026-10-20)."""
    concept = world.concepts.get(place)
    return (thumb(concept), "concept") if concept else (None, None)


def inventory_current(world, place, picked):
    """Whether the place's scene inventory counts (CONTEXT.md "scene inventory"): read from `picked`, its picked
    draw's sha. None counts while its concept is not locked, and one from an older concept, or naming none, never
    does; until one counts the place shows its design state only, no number made from an inventory."""
    read = world.inventories.get(place)
    return bool(picked and read and read["concept"] == picked)


def counted(world, place):
    """Whether the place's numbers count: its inventory current against the WorldState's own pick and its gaps
    checked from it (findings written after the pick; earlier ones were read from an older inventory)."""
    return (inventory_current(world, place, world.concept_picked.get(place))
            and bool(world.inventories[place].get("checked")))


def design_state(world, place):
    """What a place whose scene inventory does not count shows instead of its numbers: `draw` (no concept), `review`
    (drawn, not picked), `read` (picked, its inventory not read from it yet), `plan` (its scene inventory reading of
    the pick made, its plan not: score/review/reading.py), `check` (its inventory file read from the pick, its gaps not
    checked from it yet); None once its numbers count (`counted`)."""
    picked = world.concept_picked.get(place)
    if counted(world, place):
        return None
    if inventory_current(world, place, picked):
        return "check"
    if picked and (world.inventory_readings.get(place) or {}).get("concept") == picked:
        return "plan"
    if picked:
        return "read"
    return "review" if world.concepts.get(place) else "draw"  # a concept shown: none while lost or out of date


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
    """{kind: count} of a place's gaps, a lost input once (gap kinds: lost, route, missing, gate)."""
    return dict(Counter(gap_sums.kind_of(gap) for gap in found))


def worst(counts):
    return next((kind for kind, _ in gap_sums.KINDS if counts.get(kind)), None)


def priced(prices):
    """{likely, high, priced, unpriced} of {node: price}: the sums of the nodes with a measured basis, how many of
    them, and how many have none."""
    known = [price for price in prices.values() if price.get("basis") in MEASURED]
    return {"likely": round(sum(price["likely_euros"] for price in known), 2),
            "high": round(sum(price["high_euros"] for price in known), 2),
            "priced": len(known), "unpriced": len(prices) - len(known)}


def at_approved(node, approved):
    """Whether a node is at a place whose design is approved (an environment node: once any one is)."""
    place = node.partition("@")[2]
    return place in approved if place else bool(approved)


def approved_layer(found, approved):
    """One prepare layer at the approved places only: their takes, the stage's price shared by takes."""
    places = {place: takes for place, takes in found["places"].items() if place in approved}
    takes = sum(places.values())
    share = takes / found["takes"] if found["takes"] else 0.0
    return {**found, "takes": takes, "places": places,
            "waits": {place: why for place, why in found.get("waits", {}).items() if place in approved},
            "likely": None if found["likely"] is None else found["likely"] * share,
            "high": None if found["high"] is None else found["high"] * share}


def approved_parts(world):
    """(remake, price) at the places whose design the creator approved only (CONTEXT.md "design": a price on the old
    inventories the new designs replace says nothing): prepare's layers there, each stage's price shared by its
    takes, their take counts and figure, and the gaps price's nodes there; each None while its record is."""
    approved = set(approved_places(world))
    remake, price = world.remake, world.gaps_price
    if remake:
        layers = {stage: approved_layer(found, approved) for stage, found in remake.layers.items()}
        priced_layers = [found for found in layers.values() if found["takes"] and found["likely"] is not None]
        counts = Counter()
        for place in approved:
            counts.update(remake.places.get(place, {}))
        remake = remake.model_copy(update={
            "layers": layers, "counts": dict(counts), "places": {place: remake.places[place] for place in
                                                                 approved if place in remake.places},
            "likely_euros": round(sum(found["likely"] for found in priced_layers), 2),
            "high_euros": round(sum(found["high"] for found in priced_layers), 2),
            "unpriced": sorted(stage for stage, found in layers.items() if found["takes"] and found["likely"] is None)})
    if price:
        price = price.model_copy(update={"nodes": {node: found for node, found in price.nodes.items()
                                                   if at_approved(node, approved)}})
    return remake, price


def remake_money(world):
    """The remake of the places whose design the creator approved (`approved_parts`): prepare's figure plus the gaps
    price of every paid step off the prop route, None while none is approved or either part is missing or stale (the
    rule of every price record here); each part apart, its ETA (a range only when both parts have one, else at least
    the longer floor; the runner times the whole remake only, so unknown until every design is approved), why it is
    stale, and how many places are approved and still in design."""
    approved, every = len(approved_places(world)), len(cards(world))
    remake, price = approved_parts(world)
    rest = priced({node: found for node, found in price.nodes.items() if not on_route(node)}) if price else None
    route = {"likely": remake.likely_euros, "high": remake.high_euros, "unpriced": len(remake.unpriced),
             **remake.counts} if remake else None
    parts = [part for part in (route, rest) if part is not None]
    stale = [why for why in ((remake.stale if remake else "prepare has not run"),
                             (price.stale if price else "the gaps have not been priced")) if why]
    whole = None if stale or not approved or route["likely"] is None or route["high"] is None else \
        {"likely": round(route["likely"] + rest["likely"], 2), "high": round(route["high"] + rest["high"], 2)}
    return {**(whole or {"likely": None, "high": None}), "route": route, "rest": rest,
            "unpriced": sum(part["unpriced"] for part in parts),
            "eta": eta_of(remake, price) if approved == every else eta_of(None, None),
            "made_at": remake.made_at if remake else None, "stale": stale, "approved": approved,
            "in_design": every - approved, "estimate": estimate(world.remake)}


def estimate(remake):
    """The remake's estimate from the scene inventories (owner, 2026-10-21): prepare's whole one-shot figure of the
    prop route over the places with a current reading, before any design is approved. {likely, high (None while
    stale), unpriced [stage], places (read), waiting (places waiting on inventory: no euros), eta (prepare's: likely
    and high only when every layer is timed, else at_least_minutes, `untimed` its untimed layers), stale}; None
    before prepare read the readings."""
    if remake is None or not remake.inventory:
        return None
    current = remake.stale is None
    return {"likely": remake.likely_euros if current else None, "high": remake.high_euros if current else None,
            "unpriced": remake.unpriced, "places": len(remake.inventory.get("read", [])),
            "waiting": len(remake.inventory.get("waiting", [])), "eta": remake.eta, "stale": remake.stale}


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


def environment(source, spend):
    """The Environment screen: the month against the stop, the remake's price and ETA, the gaps by kind, a tile a
    place (picture, progress, gap count, worst kind, its takes; its design state instead of progress and gaps while
    its scene inventory does not count)."""
    world = source.world_state(spend)
    takes = world.remake.places if world.remake else {}
    names = groups.short_names(world)
    places = []
    for card in cards(world):
        shown = counted(world, card.place)
        counts = gap_counts(source.gaps(card.place)) if shown else {}
        link, origin = picture_of(world, card.place)
        places.append({"place": card.place, "title": names[card.place], "status": card.status,
                       "picture": link, "picture_from": origin, "design": design_state(world, card.place),
                       "progress": progress(card) if shown else None, "complete": complete(card),
                       "gaps": sum(counts.values()) if shown else None, "worst": worst(counts),
                       "takes": takes.get(card.place), "within": world.within.get(card.place)})
    return {"made_at": world.made_at, "money": month_money(spend), "remake": remake_money(world),
            "gaps": (world.gaps_total.counts if world.gaps_total else {}), "places": places,
            "shells": world.shells}


def chain_price(price, place, node):
    """{likely, high, priced, unpriced} of a gap's chain (every paid node it names once); None with no current
    gaps price or no chain."""
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
    """The Place screen: its picture and 3D, its steps with their states, its gaps as the scene tree's items (prim
    path, kind, the node that fills it) and each filling node's chain price once (`prices`)."""
    world = source.world_state()
    card = next(found for found in cards(world) if found.place == place)
    shown = counted(world, place)
    found = source.gaps(place) if shown else []
    link, origin = picture_of(world, card.place)
    model, model_from = web3d_link(source, place, library)
    price = world.gaps_price
    nodes = sorted({gap.node for gap in found if gap.node})
    counts = gap_counts(found)
    return {"place": place, "title": groups.short_names(world)[place], "status": card.status, "picture": link,
            "picture_from": origin, "web3d": model, "web3d_from": model_from, "view": f"/view/{place}",
            "design": design_state(world, place), "progress": progress(card) if shown else None,
            "complete": complete(card), "gaps": counts if shown else None, "worst": worst(counts),
            "takes": (world.remake.places.get(place) if world.remake else None),
            "steps": [{"node": step.node, "stage": step.stage, "label": step.label, "state": step.state,
                       "paid": step.paid, "thumb": step.thumb} for step in steps_of(card)],
            "items": [{"id": gap.id, "prim": gap.prim, "kind": gap_sums.kind_of(gap), "row": gap.row,
                       "node": gap.node, "paid": gap.paid, "work": gap.work,
                       "picture": thumb(gap.picture)} for gap in found],
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


# The Buy screen's layers, each the stage prefixes it gathers, in the order shown; any other stage is "other".
LAYERS = (("models", ("rough-model", "rough-align", "props-inputs", "closeup", "pixal", "likeness", "complete-boxes",
                      "motion-models-boxes", "ship_kit", "earth-kit", "partition-proposals", "concept-views")),
          ("finishes", ("finish-route-", "surfaces-", "surface-tiles")),
          ("people", ("people-", "concept_people", "cast", "characters-")),
          ("motion", ("settle", "physics-", "motion")), ("crops", ("crops-",)), ("light", ("light",)),
          ("effects", ("effects-",)), ("sound", ("sound",)), ("films", ("demo-",)))
ORDER = [name for name, _ in LAYERS] + ["other"]
# Why a part of the batch waits, in plain words (a take's lost input: local.WAITS).
EARLIER, PLAN, MISSING, PREDICTED = ("an earlier step first", "not in the last plan", "inputs missing",
                                     "predicted to fail")


def layer_of(stage):
    return next((name for name, prefixes in LAYERS if stage.startswith(prefixes)), "other")


def now_items(items, approved):
    """The basket items the Buy screen's batch yes buys: every item a run on main buys now but the Benchmarks, the
    ones waiting on a missing input and any at a place whose design the creator has not approved (`approved`,
    CONTEXT.md "design": no step is bought on a concept he did not approve; none before one is approved)."""
    return [item for item in items if item["id"] != benchmarks.ID and not item.get("missing")
            and approved and set(item.get("places", [])) <= set(approved)]


GAME = "complete/game"  # the gate that finds a place's layout still taken from the source game


def approved_places(world):
    """The places whose design the creator approved, as prepare's design record says ([] before it ran)."""
    return world.remake.design.get("approved", []) if world.remake else []


def design(source, world):
    """The Buy screen's design (CONTEXT.md "design"), made first on each place's card: each place's concept
    (missing, drawn or picked), its plan (remake, made or approved), its accepted plan output and the old
    plan's pick as a hint, as prepare's design record says (None for a place it does not name, or before it ran);
    whether its layout still takes numbers from the source game (its gaps' game gate); the places approved."""
    found = world.remake.design if world.remake else {}
    return {"places": [{"place": card.place, "design": found.get("places", {}).get(card.place),
                        "game": any(GAME in (gap.gates or []) for gap in source.gaps(card.place))}
                       for card in cards(world)],
            "approved": approved_places(world)}


def part():
    return {"likely": 0.0, "high": 0.0}


def layer_row(rows, name):
    return rows.setdefault(name, {"layer": name, "make": 0, "library": 0, "waiting": 0, "why": {}, "models": 0,
                                  "takes": 0, "steps": 0, "now": part(), "later": part(), "guessed": 0.0, "guesses": 0,
                                  "no_price": {}, "measured": part(), "estimated": part(), "places": {}})


def add_price(row, which, likely, high, basis):
    """Adds one priced part to a row's `which` (now or later) and to its basis's sum (a measured run's, else
    estimated: per unit times a count)."""
    for into in (row[which], row["measured" if basis == MEASURED[0] else "estimated"]):
        into["likely"], into["high"] = round(into["likely"] + likely, 4), round(into["high"] + high, 4)


def count(into, key, number=1):
    into[key] = into.get(key, 0) + number


def step_name(stage):
    """A kind of step in words, a person's look left out (one name for every look's body, model or parts)."""
    prefix = next((prefix for prefix in (*groups.PEOPLE, "people-look-parts-") if stage.startswith(prefix)), None)
    if prefix:
        return f"people's {groups.PEOPLE.get(prefix, 'parts')}"
    return groups.label(stage).replace("-", " ")


def node_price(row, which, node, found):
    """A node's price into its row: measured or per unit, else its stage's guess kept apart (what the runner
    reserves for a node bought now), else no price, said by its step's name."""
    if found.get("likely_euros") is not None and found.get("basis", MEASURED[1]) in MEASURED:
        add_price(row, which, found["likely_euros"], found["high_euros"], found.get("basis"))
    elif which == "now" and found.get("guess_euros"):
        row["guessed"], row["guesses"] = round(row["guessed"] + found["guess_euros"], 4), row["guesses"] + 1
    else:
        count(row["no_price"], step_name(node.partition("@")[0]))


def now_rows(now, route, rows):
    """The nodes the Buy buys now into `rows`, each priced as the runner planned it; a prop-route stage prepare
    counts by its takes (`route`) adds no step of its own."""
    for node, found in now.items():
        stage, _, place = node.partition("@")
        row = layer_row(rows, layer_of(stage))
        count(row["places"], place or "environment")
        if stage not in route:
            row["make"], row["steps"] = row["make"] + 1, row["steps"] + 1
        node_price(row, "now", node, found)


def route_rows(remake, now, rows):
    """Prepare's prop route into `rows`: a stage's takes at a place whose node the Buy buys are priced with it, the
    rest wait (by why) with their share of the stage's price; each layer's takes counted on its stage with the most,
    the models layer's library and predicted-to-fail takes beside."""
    widest = {}
    for stage, found in remake.layers.items():
        if not found["takes"]:
            continue
        row = layer_row(rows, layer_of(stage))
        bought = {place for place in found["places"] if f"{stage}@{place}" in now}
        later = found["takes"] - sum(found["places"][place] for place in bought)
        if found["likely"] is None:
            count(row["no_price"], step_name(stage), later)
        elif found["takes"]:
            share = later / found["takes"]
            add_price(row, "later", found["likely"] * share, found["high"] * share, None)
        if found["takes"] > widest.get(row["layer"], (0, None))[0]:
            widest[row["layer"]] = (found["takes"], stage)
    for name, (takes, stage) in widest.items():
        route_counts(rows[name], remake.layers[stage], stage, now)
    if "models" in rows and widest:
        models = rows["models"]
        models["library"] = remake.counts.get("library", 0)
        predicted = remake.counts.get("predicted_gaps", 0)
        models["waiting"] += predicted
        count(models["why"], PREDICTED, predicted)
        models["models"] += models["library"] + predicted


def route_counts(row, found, stage, now):
    """A layer's takes on its widest route stage: made now where the Buy buys the stage at the place, else waiting
    on its takes' lost inputs or, ready, on the next plan."""
    row["models"], row["takes"] = row["models"] + found["takes"], found["takes"]
    for place, takes in found["places"].items():
        if f"{stage}@{place}" in now:
            row["make"] += takes
            continue
        waits = found.get("waits", {}).get(place, {})
        for why, number in [*waits.items(), (PLAN, takes - sum(waits.values()))]:
            if number:
                count(row["why"], why, number)
                row["waiting"] += number


def rest_rows(price, now, blocked, rows):
    """The gaps price's paid steps off the prop route that the Buy does not buy now into `rows`, each waiting on a
    missing input (its basket item says so) or an earlier step, priced where measured or per unit."""
    for node, found in price.nodes.items():
        if on_route(node) or node in now:
            continue
        row = layer_row(rows, layer_of(node.partition("@")[0]))
        row["steps"], row["waiting"] = row["steps"] + 1, row["waiting"] + 1
        count(row["why"], MISSING if node in blocked else EARLIER)
        node_price(row, "later", node, found)


def rounded(row):
    """A layer row as shown: its euros to the cent, its likely and high (the guesses the Buy reserves in the high)."""
    for key in ("now", "later", "measured", "estimated"):
        row[key] = {name: round(value, 2) for name, value in row[key].items()}
    row["guessed"] = round(row["guessed"], 2)
    row["makes"] = row["takes"] + row["steps"]  # what it makes: its route takes and its steps at places
    row["likely"] = round(row["now"]["likely"] + row["later"]["likely"], 2)
    row["high"] = round(row["now"]["high"] + row["guessed"] + row["later"]["high"], 2)
    return row


def summed(rows, key, field):
    return round(sum(row[key][field] for row in rows), 2)


def batch(world, items):
    """The Buy screen's one batch (CONTEXT.md "batch"): what its Buy buys now (the basket items of `now_items`, priced
    as the runner planned them, the guesses it reserves in the high) and what waits, by why (prepare's prop route,
    take by take, and every other paid step of the gaps price), by layer. Each layer {layer, make, library, waiting,
    why, models, steps, now, later, guessed, guesses, no_price, measured, estimated, likely, high}; `total` its sum,
    `now` {likely, high, guessed, guesses, stop, places, eta} the Buy's line, `waiting` {likely, high, why}; `gets`
    the places it reaches. Nothing priced here (ADR-0006)."""
    whole = remake_money(world)
    remake, price = approved_parts(world)
    price = None if price is None or price.stale else price
    remake = None if whole["stale"] or remake is None else remake
    buying = now_items(items, approved_places(world))
    now = pricing.basket_prices(buying)
    blocked = {node for item in items if item.get("missing") for node in item["nodes"]}
    rows = {}
    now_rows(now, set(remake.layers) if remake else set(), rows)
    if remake:
        route_rows(remake, now, rows)
    if price:
        rest_rows(price, now, blocked, rows)
    shown = [rounded(rows[name]) for name in ORDER if name in rows]
    for row in shown:
        row["places"] = sorted(row["places"])
    return {"total": total_of_rows(shown), "now": now_of(shown, now, buying), "waiting": waiting_of(shown),
            "gets": gets(world, now), "eta": whole["eta"], "stale": whole["stale"], "layers": shown,
            "estimate": whole["estimate"]}


def total_of_rows(rows):
    """{likely, high, measured, estimated, guessed, no_price} of the layer rows: the high's measured part, its guessed
    part and the rest estimated (the three add up to it), and the names of the steps with no price."""
    likely, high = round(sum(row["likely"] for row in rows), 2), round(sum(row["high"] for row in rows), 2)
    measured = {"likely": summed(rows, "measured", "likely"), "high": summed(rows, "measured", "high")}
    guessed = round(sum(row["guessed"] for row in rows), 2)
    return {"likely": likely, "high": high, "measured": measured, "guessed": guessed,
            "estimated": {"likely": round(likely - measured["likely"], 2),
                          "high": round(high - measured["high"] - guessed, 2)},
            "no_price": sorted({name for row in rows for name in row["no_price"]})}


def now_of(rows, now, buying):
    """{likely, high, guessed, guesses, stop, steps, places, eta} of what the Buy buys: its high holds the guesses the
    runner reserves, its stop that high plus 10%."""
    guessed = round(sum(row["guessed"] for row in rows), 2)
    high = round(summed(rows, "now", "high") + guessed, 2)
    return {"likely": summed(rows, "now", "likely"), "high": high, "guessed": guessed,
            "guesses": sum(row["guesses"] for row in rows), "stop": round(high * BUFFER, 2) if now else None,
            "steps": len(now), "places": sorted({place for item in buying for place in item.get("places", [])}),
            "eta": now_eta(now)}


def waiting_of(rows):
    """{likely, high, why} of what waits: its euros and why, the commonest first."""
    why = {}
    for row in rows:
        for reason, number in row["why"].items():
            count(why, reason, number)
    return {"likely": summed(rows, "later", "likely"), "high": summed(rows, "later", "high"),
            "why": [reason for reason, _ in sorted(why.items(), key=lambda pair: -pair[1])]}


def now_eta(nodes):
    """basket_eta of the nodes bought now and, while a node is not timed, `at_least_minutes`: the timed ones'
    span (pricing.span), a floor."""
    timed = {node: found for node, found in nodes.items() if found.get("likely_minutes") is not None}
    return {**basket_eta(nodes), "at_least_minutes": pricing.span(timed, "likely_minutes", pricing.DEFAULT_JOBS)
            if timed else None}


def gets(world, now):
    """[{place, made, after, needed, complete, layers}] of the places the Buy reaches, most bought first: each
    place's steps standing accepted now and once its bought steps stand too (the free steps after them, made as the
    run goes on, not counted), whether that completes it, and the layers bought there."""
    found = []
    for card in cards(world):
        steps = steps_of(card)
        bought = [step for step in steps if step.node in now and step.state != "accepted"]
        if not bought:
            continue
        made = sum(1 for step in steps if step.state == "accepted")
        found.append({"place": card.place, "made": made, "after": made + len(bought), "needed": len(steps),
                      "complete": made + len(bought) == len(steps),
                      "layers": [name for name in ORDER if name in {layer_of(step.stage) for step in bought}]})
    return sorted(found, key=lambda row: (-(row["after"] - row["made"]), row["place"]))


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
    price = world.gaps_price
    bases = Counter(found.get("basis") for found in price.nodes.values()) if price else Counter()
    measured = sum(count for basis, count in bases.items() if basis in MEASURED)
    places = cards(world)
    return {"made_at": world.made_at, "money": month_money(spend), "bill_days": spend.bill_days, "days": spend.days,
            "prices": {"measured": measured, "steps": sum(bases.values()), "by_basis": dict(bases),
                       "stale": bool(price is None or price.stale)},
            "remake_layers": world.remake.counts if world.remake else None,
            "gaps": (world.gaps_total.counts if world.gaps_total else {}),
            "places": {"complete": sum(1 for card in places if complete(card)), "total": len(places)}}


def library_counts(library):
    """The Library screen's counts: each shelf's entries (a kind, lamps, a place with its layers), by state,
    pictured and scored."""
    if library is None:
        return {"kinds": [], "total": 0}
    by_kind = {}
    for entry in library.entries():
        counts = by_kind.setdefault(entry.shelf or entry.kind, Counter())
        counts.update({"count": 1, entry.state: 1, "pictured": bool(entry.picture), "scored": entry.score is not None})
    from score.dashboard.state.library import KINDS
    order = [kind for kind, _ in KINDS] + sorted(set(by_kind) - {kind for kind, _ in KINDS})
    return {"kinds": [{"kind": kind, **{name: by_kind.get(kind, Counter())[name] for name in
                                        ("count", "draft", "locked", "withdrawn", "pictured", "scored")}}
                      for kind in order], "total": sum(counts["count"] for counts in by_kind.values())}
