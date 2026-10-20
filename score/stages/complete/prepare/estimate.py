"""The one figure a batch is said yes to (#21): euros (likely and high, every job run once), one ETA on the fixed fleet
(schedule.py) and the predicted holes beside them. Free and local; it buys nothing.

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
from score.stages.complete.holes import price, schedule

SHELL_ROUTE = ("closeup", "pixal", "surfaces-bake")
GOOGLE = "google calls"  # a per-unit entry's source of Google calls: the bill share does not apply
DEADLINE_TIMES = 2  # a job's watchdog deadline: twice its measured high seconds (guard.py's runaway limit)


def map_calls():
    """One draw a finish map: the close-up's map and one a turntable view (turntable_views.MAP_VIEWS)."""
    from score.stages.surfaces import turntable_views
    return 1 + len(turntable_views.MAP_VIEWS)


def one_shot():
    """{stage: (units a take, why)} where a batch's one run of a take differs from one unit a take."""
    return {"closeup": (1, "one Pro wording a row, one take: the two-take chain goes (#21)"),
            "surfaces-maps": (map_calls(), "one draw a map: the close-up's and one a turntable view (#21)"),
            "surfaces-names": (0, "no finish asked again: Lab colours and candidate surfaces go in the list ask (#21)")}


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
                        "settings": settings(stage, rules, fixed.get(stage))}
    return found


def layer_cost(stage, takes, rules):
    """{units, price, minutes} of a layer's takes: units None and its price and minutes named unmeasured when its
    stage has no per unit (its unit is not known, so neither is the count); no units cost and take nothing."""
    entry = compute.per_unit(stage)
    if entry is None or entry["stage"] != stage:
        why = f"{stage}: no measured per unit in per-unit.json"
        return {"units": None, "price": {"likely_euros": None, "high_euros": None, "why": why},
                "minutes": {"minutes_why": why}}
    units = layer_units(stage, takes, rules)
    if not units:
        return {"units": units, "price": {"likely_euros": 0.0, "high_euros": 0.0},
                "minutes": {"likely_minutes": 0.0, "high_minutes": 0.0, "cards": None}}
    return {"units": units, "price": layer_price(stage, units), "minutes": compute.unit_minutes(stage, units)}


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
    """{likely_euros, high_euros, unpriced} of the layers."""
    priced = [layer["price"] for layer in found.values() if layer["price"]["likely_euros"] is not None]
    return {"likely_euros": round(sum(each["likely_euros"] for each in priced), 2),
            "high_euros": round(sum(each["high_euros"] for each in priced), 2),
            "unpriced": sorted(stage for stage, layer in found.items() if layer["price"]["likely_euros"] is None)}


def expected_holes(bought):
    """The holes the batch is expected to leave by its groups' measured pass shares (a group of no measured shape
    counts none), rounded; the measure is the close-up's, the first paid step."""
    return round(sum(1 - group["prediction"]["pass_share"] for group in bought
                     if group["prediction"]["pass_share"] is not None))


def line(record):
    """The one line the creator says yes to."""
    money, time, counts = record["totals"], record["eta"], record["counts"]
    minutes = (f"{time['likely_minutes']:.0f} to {time['high_minutes']:.0f} min" if time["likely_minutes"] is not None
               else f"at least {time['at_least_minutes']:.0f} min ({len(time['unknown'])} layers untimed)")
    unpriced = f", unpriced: {', '.join(money['unpriced'])}" if money["unpriced"] else ""
    return (f"remake batch (estimate): {counts['bought']} takes of {counts['groups']} models "
            f"({counts['library']} from the library, {counts['predicted_holes']} predicted holes not bought), "
            f"EUR {money['likely_euros']:.2f} likely, {money['high_euros']:.2f} high, every job once{unpriced}; "
            f"ETA {minutes}; about {record['expected_holes']} holes expected after; "
            f"{counts['inputs_missing']} takes wait on lost inputs")
