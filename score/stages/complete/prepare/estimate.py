"""The one figure a batch is said yes to (#21): euros (likely and high, every job run once), one ETA on the fixed fleet
(schedule.py) and the predicted gaps beside them. Free and local; it buys nothing.

Each take a group needs runs once through its route's layers (the prop route, price.route_stages: close-up, Pixal3D,
the surface line, the bake); a shell piece takes its library surface with no maps, so only its close-up, model and
bake (SHELL_ROUTE). A layer's units are its takes times its one-shot units a take (ONE_SHOT, else one), its euros
those units at its stage's measured per unit (data/costs/per-unit.json), a card or processor layer's times the
provider's bill over the ledger (price.BILL_SHARE: disks, addresses and storage the ledger misses). A layer with no
measured per unit is unpriced and named, never guessed. Its minutes are compute.unit_minutes on its units (the
runner's card rule, capped at the run's cap), or named as unmeasured; the ETA walks the layers in the route's order.
"""
import math

from score.adapters import compute
from score.stages.complete.gaps import price, schedule
from score.stages.complete.prepare import groups

SHELL_ROUTE = ("closeup", "pixal", "surfaces-bake")
# {route: its layer's stage} of a take's layers past or in place of the prop pipeline (groups.ROUTES): a person's
# model is the prop pipeline's, then the motion layer's steps (CONTEXT.md "motion"); the sky, the effects and the far
# city are layers without models, each its own route (CONTEXT.md "layer adapter").
OWN_ROUTES = {"people": "motion", "sky": "sky", "effects": "effects-look", "skyline": "skyline"}
GOOGLE = "google calls"  # a per-unit entry's source of Google calls: the bill share does not apply
DEADLINE_TIMES = 2  # a job's watchdog deadline: twice its measured high seconds (guard.py's runaway limit)


def one_shot():
    """{stage: (units a take, why)} where a batch's one run of a take differs from one unit a take."""
    return {"closeup": (1, "one Pro wording a row, one take: the two-take chain goes (#21)")}


def takes_a_layer(route, groups_bought):
    """{stage: takes} of the bought groups: every route layer for a whole model, SHELL_ROUTE's for a shell piece."""
    found = dict.fromkeys(route, 0)
    for group in groups_bought:
        for stage in route:
            found[stage] += stage in SHELL_ROUTE or not group["shell"]
    return found


def layer_units(stage, takes, rules):
    """The units a layer makes for `takes` takes by its one-shot rule (`rules`, one_shot())."""
    per_take = rules.get(stage, (1, None))[0]
    return round(takes * per_take, 2)


def layer_price(stage, units):
    """{likely_euros, high_euros, unit, unit_likely_euros, bill_share} of a layer's units at its stage's measured
    per unit (layer_cost checks there is one)."""
    entry = compute.per_unit(stage)
    share = 1.0 if GOOGLE in (entry.get("sources") or {}) else price.BILL_SHARE
    return {"likely_euros": round(entry["likely_euros"] * units * share, 2),
            "high_euros": round(entry["high_euros"] * units * share, 2), "unit": entry["unit"],
            "unit_likely_euros": entry["likely_euros"], "bill_share": round(share, 4)}


def settings(stage, rules, fixed_machine):
    """The settings a layer's jobs are fixed at before the batch: one seed, its one-shot units a take, slots a
    machine and a deadline a job from its measured seconds where measured, its class and zone (machines.fixed)."""
    entry = compute.per_unit(stage) or {}
    time = entry.get("time") or {}
    high = (time.get("unit_seconds") or {}).get("high")
    per_take, why = rules.get(stage, (1, "one run a take"))
    return {"seed": 1, "units_a_take": per_take, "why": why, "slots": time.get("slots"),
            "deadline_seconds": math.ceil(high * DEADLINE_TIMES) if high else None,
            "deadline_why": None if high else time.get("why", "no measured seconds a job"),
            "machine": fixed_machine}


def layers(route, groups_bought, rules, fixed):
    """{stage: {takes, units, price, minutes, settings}} of the batch's layers; `fixed` {stage: machine or None}."""
    found = {}
    for stage, takes in takes_a_layer(route, groups_bought).items():
        found[stage] = {"takes": takes, **layer_cost(stage, takes, rules),
                        "settings": settings(stage, rules, fixed.get(stage)),
                        "runs": {"routes": list(groups.MODEL_ROUTES), "shell": stage in SHELL_ROUTE}}
    return found


def layer_cost(stage, takes, rules):
    """{units, price, minutes} of a layer's takes: units None and its price and minutes named unmeasured when its
    stage has no per unit (its unit is not known, so neither is the count); no units cost and take nothing, a free
    row's (no per unit) included."""
    units = layer_units(stage, takes, rules)
    if not units:
        return {"units": units, "price": {"likely_euros": 0.0, "high_euros": 0.0},
                "minutes": {"likely_minutes": 0.0, "high_minutes": 0.0, "cards": None}}
    entry = compute.per_unit(stage)
    if entry is None or entry["stage"] != stage:
        why = f"{stage}: no measured per unit in per-unit.json"
        return {"units": None, "price": {"likely_euros": None, "high_euros": None, "why": why},
                "minutes": {"minutes_why": why}}
    return {"units": units, "price": layer_price(stage, units), "minutes": compute.unit_minutes(stage, units)}


def own_route_layers(groups_bought):
    """{stage: {takes, units, price, minutes, settings, runs}} of the layers a take adds past the prop pipeline or in
    place of it (OWN_ROUTES): the motion layer's steps after a person's model, the sky's, the effects' and the far
    city's own routes; each at its stage's measured per unit, else unpriced and untimed (layer_cost)."""
    found = {}
    for route, stage in OWN_ROUTES.items():
        takes = sum(group["route"] == route for group in groups_bought)
        if takes:
            found[stage] = {"takes": takes, **layer_cost(stage, takes, {}), "settings": settings(stage, {}, None),
                            "runs": {"routes": [route], "shell": True}}
    return found


def clip_layer(places, cap, fixed_machine=None):
    """The preview clips' layer (score/stages/library/clips): one clip a bought take, each a new item the handover
    makes; `places` {place: bought takes}, at its measured per unit, its minutes `clip_minutes`."""
    from score.stages.library import clips
    items = sum(places.values())
    found = {**layers([clips.ROW], [{"shell": False}] * items, {}, {clips.ROW: fixed_machine})[clips.ROW],
             "runs": {"routes": ["prop", *groups.ROUTES], "shell": True}}
    if items and found["units"] is not None:
        found["minutes"] = clip_minutes(places, cap)
    return found


def clip_minutes(places, cap):
    """{likely_minutes, high_minutes, cards} of the places' clips spread over warm cards (clips.shares: CLIPS_A_CARD
    a card, so a card works about as long as the batch's longest layer), the places' nodes side by side within the
    run's `cap` cards, on library-clips' measured seconds a clip and set-up; {minutes_why} where unmeasured."""
    from score.stages.library import clips
    time = (compute.per_unit(clips.ROW) or {}).get("time") or {}
    setup = time.get("setup_minutes") or {}
    if "unit_seconds" not in time or "likely" not in setup:
        return {"minutes_why": time.get("why") or setup.get("why") or f"{clips.ROW}: no measured time"}
    counts = [count for count in places.values() if count]
    cards = sum(len(clips.shares(range(count))) for count in counts)
    busiest = max(len(share) for count in counts for share in clips.shares(range(count)))
    rounds = math.ceil(cards / cap)
    return {which: round(setup[key] + rounds * busiest * time["unit_seconds"][key] / 60, 1)
            for which, key in (("likely_minutes", "likely"), ("high_minutes", "high"))} | {"cards": min(cards, cap)}


def route_edges(table, route):
    """[(before, after)] of the route's layers: a layer after each route layer it reads, directly or through stages
    outside the route (`table`, the runner's {name: Stage})."""
    edges = []
    for stage in route:
        seen, todo = set(), list(table[stage].after)
        while todo:
            name = todo.pop()
            if name in seen or name not in table:
                continue
            seen.add(name)
            if name in route:
                edges.append((name, stage))
            else:
                todo.extend(table[name].after)
    return edges


def eta(found, edges, jobs, cap):
    """schedule.schedule over the layers as paid rows on their minutes, in the route's order."""
    rows = {stage: {"paid": True, "cards": layer["minutes"].get("cards"),
                    "likely_minutes": layer["minutes"].get("likely_minutes"),
                    "high_minutes": layer["minutes"].get("high_minutes"),
                    "why": layer["minutes"].get("minutes_why")} for stage, layer in found.items()}
    return schedule.schedule(rows, [edge for edge in edges if edge[0] in rows and edge[1] in rows], jobs, cap)


def totals(found):
    """{likely_euros, high_euros, unpriced, estimated} of the layers (estimated: priced from another stage's
    measures, not their own)."""
    priced = [layer["price"] for layer in found.values() if layer["price"]["likely_euros"] is not None]
    return {"likely_euros": round(sum(each["likely_euros"] for each in priced), 2),
            "high_euros": round(sum(each["high_euros"] for each in priced), 2),
            "unpriced": sorted(stage for stage, layer in found.items() if layer["price"]["likely_euros"] is None),
            "estimated": sorted(stage for stage, layer in found.items() if layer["price"].get("estimated_from"))}


def expected_gaps(bought):
    """The gaps the batch is expected to leave by its groups' measured pass shares (a group of no measured shape
    counts none), rounded; the measure is the close-up's, the first paid step."""
    return round(sum(1 - group["prediction"]["pass_share"] for group in bought
                     if group["prediction"]["pass_share"] is not None))


def line(record):
    """The one line the creator says yes to."""
    money, time, counts = record["totals"], record["eta"], record["counts"]
    minutes = (f"{time['likely_minutes']:.0f} to {time['high_minutes']:.0f} min" if time["likely_minutes"] is not None
               else f"at least {time['at_least_minutes']:.0f} min ({len(time['unknown'])} layers untimed)")
    unpriced = f", unpriced: {', '.join(money['unpriced'])}" if money["unpriced"] else ""
    inventory = record["inventory"]
    return (f"remake batch (estimate) of the {len(inventory['read'])} places with a scene inventory "
            f"({len(inventory['waiting'])} waiting on inventory, no euros): "
            f"{counts['bought']} takes of {counts['groups']} models "
            f"({counts['library']} from the library (made under today's route), "
            f"{counts['predicted_gaps']} predicted gaps not bought), "
            f"EUR {money['likely_euros']:.2f} likely, {money['high_euros']:.2f} high, every job once{unpriced}; "
            f"ETA {minutes}; about {record['expected_gaps']} gaps expected after; "
            f"{counts['inputs_missing']} takes wait on lost inputs")
