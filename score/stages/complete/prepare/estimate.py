"""The one figure a batch is said yes to (#21): euros (likely and high, every job run once), one ETA on the fixed fleet
(schedule.py) and the predicted gaps beside them. Free and local; it buys nothing.

Each take a group needs runs once through its route's layers (the prop route, price.route_stages: close-up, Pixal3D,
the finish route, the bake); a shell piece too (CONTEXT.md "prop pipeline": every object and shell piece; the
finish route lists its library surface, no maps, and the bake bakes only the takes the route listed, #10). A layer's
units are its takes times its one-shot units a take (ONE_SHOT, else one), its euros
those units at its stage's measured per unit (data/costs/per-unit.json), a card or processor layer's times the
provider's bill over the ledger (compute.bill_share, the runner's: disks, addresses and storage the ledger misses). A
layer with no measured per unit is unpriced and named, never guessed. Its minutes are compute.unit_minutes on its
units (the runner's card rule, capped at the run's cap), or named as unmeasured; the ETA walks the layers in the
route's order."""
import math

from score.adapters import compute
from score.stages.complete.gaps import schedule
from score.stages.complete.prepare import groups

# {route: its layer's stage} of a take's layers past or in place of the prop pipeline (groups.ROUTES): a person's
# model is the prop pipeline's, then the people adapter's body step (rig, build, settle and every body gate:
# score/stages/people_bodies, the motion layer's "bodies" module; never the `motion` row, which moves rigid parts only);
# the sky and the far city are layers without models, each its own route (CONTEXT.md "layer adapter"); an effect's
# own layer is the free effects-layer, made from the design's emitting rows, so it adds no paid layer.
OWN_ROUTES = {"people": "people-body", "sky": "sky", "skyline": "skyline"}
# The route's rows that run once a scene, not once a take: the scene palette and the scene's surfaces made fresh
# (owner, 2026-10-21: every old material retired, so every scene's surfaces are made before anything is finished).
# Each is one Gemini 3.1 Pro answer on its concept through the Batch API, priced at its own measured per unit, else
# at the measured one of the same answer (ASK_PRICED_AS, the finish list's), named as estimated from it.
SCENE_ROWS = ("finish-route-palette", "surface-library")
ASK_PRICED_AS = "finish-route-list"
DEADLINE_TIMES = 2  # a job's watchdog deadline: twice its measured high seconds (guard.py's runaway limit)


def one_shot():
    """{stage: (units a take, why)} where a batch's one run of a take differs from one unit a take."""
    return {"closeup": (1, "one Pro wording a row, one take: the two-take chain goes (#21)")}


def takes_a_layer(route, groups_bought):
    """{stage: takes} of the bought groups: every route layer for every model, a shell piece's too."""
    return dict.fromkeys(route, len(groups_bought))


def take_stages(route, take):
    """The paid layers one bought take runs once each, as the figure counts them: its model's route layers (none off
    the prop pipeline), its own route's past or in place of the model (OWN_ROUTES). The runner counts a designed
    place's units from these (prepare/handin.py)."""
    model = list(route) if take["route"] in groups.MODEL_ROUTES else []
    return [*model, *([OWN_ROUTES[take["route"]]] if take["route"] in OWN_ROUTES else [])]


def layer_units(stage, takes, rules):
    """The units a layer makes for `takes` takes by its one-shot rule (`rules`, one_shot())."""
    per_take = rules.get(stage, (1, None))[0]
    return round(takes * per_take, 2)


def layer_price(stage, units):
    """{likely_euros, high_euros, unit, unit_likely_euros, bill_share} of a layer's units at its stage's measured
    per unit (layer_cost checks there is one)."""
    entry = compute.per_unit(stage)
    share = compute.bill_share(entry)
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
    for stage, takes in takes_a_layer([stage for stage in route if stage not in SCENE_ROWS], groups_bought).items():
        found[stage] = {"takes": takes, **layer_cost(stage, takes, rules),
                        "settings": settings(stage, rules, fixed.get(stage)),
                        "runs": {"routes": list(groups.MODEL_ROUTES), "shell": True}}
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


def scene_layers(route, scenes):
    """{stage: {scenes, units, price, minutes, settings, runs}} of the route's once-a-scene rows (SCENE_ROWS) for
    `scenes` scenes: each at its own measured per unit, else at ASK_PRICED_AS's with `estimated_from` named, else
    unpriced (layer_cost)."""
    found = {}
    for stage in (stage for stage in route if stage in SCENE_ROWS):
        own = compute.per_unit(stage)
        measured = stage if own is not None and own["stage"] == stage else ASK_PRICED_AS
        cost = layer_cost(measured, scenes, {})
        if measured != stage and cost["units"]:
            cost["price"] = {**cost["price"], "estimated_from": measured}
        found[stage] = {"scenes": scenes, **cost, "settings": settings(stage, {}, None),
                        "runs": {"routes": ["scene"], "shell": False}}
    return found


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
            f"{counts['input_gaps']} input gaps (no box or size) priced apart, not bought")
