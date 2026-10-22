"""Prepare the remake's batch and say its one figure (this package's docstring has the record):

    .venv/bin/python -m score.stages.complete.prepare [--library DIR] [--stock] [--moved] [--out FILE] [--data DIR]

--library  the creator's library folder (default SCORE_LIB_ROOT, else the score_lib checkout beside score);
           without one, nothing matches and the record says why
--stock    read where each layer's classes are in stock now (the provider's free listing); without it the class is
           the runner's first and the zone the best boot record
--moved    add `score moved`'s dry run: the paid rows with an accepted output this tree would buy again (minutes)

Free and local: reads the scene inventories, the library's index, the per-unit prices, the ledgers and the store;
buys, keys and judges nothing. Prints the one line and the record's path.
"""
import argparse
import json
import pathlib

from score import graph, stages
from score.stages.complete.gaps import price
from score.stages.complete.prepare import (benchmarks, contract, design, estimate, groups, handin, library, machines,
                                           predict)
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[4]
WORK = PROPS_HOME / "work"
OUT = WORK / "checks" / "prepare" / "remake.json"
WORLD = "world1"
NOT_IN_FIGURE = ("the places' own paid rows (settle, light passes, tiles): `score price world1 --gaps`",
                 "the places waiting on inventory (no reading of their picked concept yet): no euros until read",
                 "films, sound and the ground: their layers' prepare steps are #21 tracks C's (a reading's terrain "
                 "rows are models through the prop pipeline, its people rows models with the motion layer after)",
                 "the sky's, the effects' and the far city's takes: their own routes, unpriced until measured, their "
                 "inputs that route's own (not the prop pipeline's contract, so not checked here)",
                 "the likeness calibration and any layer listed unpriced: no measured per unit")


def library_root(given):
    """The library folder to match against: `given`, else SCORE_LIB_ROOT, else None."""
    if given:
        return pathlib.Path(given)
    from score.stages.library import backend
    root = backend.settings().get("SCORE_LIB_ROOT")
    return pathlib.Path(root) if root else None


def read_library(root, inventories):
    """(the library index, its record entry) of the library at `root`; an empty index with why when there is none."""
    if root is None or not (root / "index" / "model.json").is_file():
        return {}, {"root": str(root) if root else None, "why": "no library folder with index/model.json"}
    models = library.library_models(root, library.todays_route())
    return library.index(models, inventories), {"root": str(root), "models": len(models)}


def made(take):
    """Whether the take's Pixal3D files stand in the work folder (pixal_row.made): a made take is not bought again."""
    from score.stages.props import pixal_row
    return pixal_row.made(take)


def status_of(match, prediction, is_made, inputs):
    """library (a model made under today's route, or locked, matches), made (its take stands), input gap (its inputs
    break their contract: no box from SAM 3 or Gemini, the whole picture, no size; its close-up cannot be framed or
    checked, so it is not bought, never a stopped line), predicted gap, or bought."""
    if match["pipeline"]:
        return "library"
    if is_made:
        return "made"
    if inputs:
        return "input gap"
    return "predicted gap" if prediction["outcome"] == "predicted gap" else "bought"


def take_entry(group, record, index, rates, work):
    """One take of the batch: its group with its library match, prediction, input faults, crop upscale, status and
    key-diff status."""
    match = library.match(group, index)
    model = group["route"] in groups.MODEL_ROUTES
    prediction = predict.predicted(group["size"], rates) if model else OWN_ROUTE
    is_made = made(group["take"])
    inputs = contract.faults(record, group, work) if model else []
    status = TERRAIN if group["route"] == "ground" else status_of(match, prediction, is_made, inputs)
    return {**group, "library": match, "prediction": prediction, "inputs": inputs,
            "upscale": contract.upscale(group["box"]), "status": status,
            "key_diff": "made: its take stands, not bought again" if is_made else "new: no take of it stands"}


# The ground itself: made by the terrain node from the design (free), its detail areas the scene inventory's terrain
# rows, the terrain adapter's own, never a close-up of the whole picture; no take bought.
TERRAIN = "terrain node"
OWN_ROUTE = {"outcome": "pass", "shape": None, "pass_share": None, "mode": None,
             "measured": "its own route: no close-up, so no close-up failure is measured against it"}


def take_counts(takes):
    """The batch's counts by status, and how many bought takes are at risk."""
    bought = [take for take in takes if take["status"] == "bought"]
    return {"library": sum(take["status"] == "library" for take in takes),
            "library_code_only": sum(not take["library"]["pipeline"] and bool(take["library"]["code"])
                                     for take in takes),
            "library_old": sum(not take["library"]["pipeline"] and bool(take["library"]["old"]) for take in takes),
            "made": sum(take["status"] == "made" for take in takes), "bought": len(bought),
            "predicted_gaps": sum(take["status"] == "predicted gap" for take in takes),
            "input_gaps": sum(take["status"] == "input gap" for take in takes),
            "terrain": sum(take["status"] == TERRAIN for take in takes),
            "at_risk": sum(take["prediction"]["outcome"] == "at risk" for take in bought)}


def stock_read(route):
    """The provider's free listing of where the route's machine classes are in stock now (provider Offers)."""
    cap = machines.capacity()
    import provider  # beside capacity.py
    classes = sorted({name for stage in route for name in (machines.candidates(stage, cap) or (None, []))[1]})
    return provider.cloud.offers(classes)


def fixed_machines(route, stock):
    """{stage: machines.fixed} of the route's layers on the ledgers' boot records."""
    cap = machines.capacity()
    import provider  # beside capacity.py
    records = machines.boot_records(machines.ledger_entries(), machines.class_names(provider.cloud.CLASSES))
    return {stage: machines.fixed(stage, records, cap, stock) for stage in route}


def moved_rows(runner):
    """`score moved`'s dry run of this tree: [{node, euros, why, again}]."""
    from score.stages import moved
    found = moved.rebuys(runner, runner.line_nodes(stages.places(runner.world, runner.store), True))
    return [{"node": buy.node, "euros": buy.euros, "why": buy.why, "again": buy.again} for buy in found]


def priced_layers(route, takes, fixed):
    """(layers of the bought takes, of the predicted gaps, of the input gaps): the prop route's of the models
    (groups.MODEL_ROUTES), then each take's own route's (estimate.own_route_layers)."""
    rules = estimate.one_shot()
    found = []
    for status in ("bought", "predicted gap", "input gap"):
        chosen = [take for take in takes if take["status"] == status]
        models = [take for take in chosen if take["route"] in groups.MODEL_ROUTES]
        found.append({**estimate.layers(route, models, rules, fixed), **estimate.own_route_layers(chosen)})
    return tuple(found)


def across_places(route, takes, fixed):
    """{takes, totals} of the bought takes if one take served a model (kind, size ratio, kit) in every place: the
    owner's call, since a place's style may differ, so never the figure itself."""
    shared = list({tuple(map(str, take["key"])): take for take in takes
                   if take["status"] == "bought" and take["route"] in groups.MODEL_ROUTES}.values())
    return {"takes": len(shared), "totals": estimate.totals(estimate.layers(route, shared, estimate.one_shot(), fixed))}


def design_route(runner):
    """The prop route's paid stages a design's take runs (price.route_stages), less likeness-calibration: it applies
    only to a place whose prop data names accepted models (prop_data.calibration_applies), never a design's hand-in,
    so the runner never makes it there (a designed place's likeness is measured, not judged: props/likeness_row)."""
    return [stage for stage in price.route_stages(runner) if stage != "likeness-calibration"]


def inventoried_places(world_places):
    """The places a scene inventory is read for: the environment's places (no part of another scene's outside among
    them, stages.places) and its outside shells (data/places/within.json)."""
    from score.review import concepts
    return sorted({*world_places, *concepts.tree()["shells"]})


def remake(runner, data, root, work, stock=None, moved=None):
    """The remake's prepare record (this package's docstring)."""
    from score.review import plans
    inventories, waiting = groups.current(runner.store, inventoried_places(stages.places(runner.world, runner.store)))
    by_place = {place: groups.place_groups(place, record) for place, record in inventories.items()}
    index, library_entry = read_library(root, groups.inventories(plans.KEPT_INVENTORY))
    rates = predict.hub_rates()
    takes = [take_entry(group, inventories[place], index, rates, work)
             for place, found in by_place.items() for group in found if not group["reuse"]]
    route = design_route(runner)
    fixed = fixed_machines(route, stock)
    found, gaps, input_gaps = priced_layers(route, takes, fixed)
    found.update(estimate.scene_layers(route, len({take["place"] for take in takes if take["status"] == "bought"})))
    edges = estimate.route_edges(runner.stages, route)
    record = {"made_at": graph.now(), "priced_on": price.priced_on(),
              "inventory": {"read": sorted(inventories), "waiting": waiting},
              "counts": {**groups.counts(by_place), **take_counts(takes)}, "rates": rates, "library": library_entry,
              "takes": takes, "layers": found, "totals": estimate.totals(found),
              "eta": estimate.eta(found, edges, graph.JOBS, price.run_cap()),
              "expected_gaps": estimate.expected_gaps([take for take in takes if take["status"] == "bought"]),
              "predicted_gaps_if_bought": estimate.totals(gaps),
              "input_gaps_if_bought": estimate.totals(input_gaps),
              "across_places": across_places(route, takes, fixed),
              "moved": {"rows": moved} if moved is not None else {"not_run": "--moved not given"},
              "benchmarks": {"listed": benchmarks.listed(), "guard": benchmarks.guard()},
              "design": design.designs(runner.store, pathlib.Path(data), stages.places(runner.world, runner.store)),
              "not_in_figure": list(NOT_IN_FIGURE)}
    return {**record, "line": estimate.line(record)}


def designed_places(record):
    """The read places whose design is kept where the plan stage reads it (score/review/plans.KEPT: picked, read and
    planned): the places the runner's loop runs from their design (handin.py)."""
    from score.review import plans
    return [place for place in record["inventory"]["read"] if (plans.KEPT / f"{place}.json").is_file()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--library")
    parser.add_argument("--stock", action="store_true")
    parser.add_argument("--moved", action="store_true")
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--data", type=pathlib.Path, default=REPO / "data")
    options = parser.parse_args(argv)
    runner = stages.runner(world=stages.WORLDS[WORLD]())
    stock = stock_read(design_route(runner)) if options.stock else None
    record = remake(runner, options.data, library_root(options.library), WORK, stock,
                    moved_rows(runner) if options.moved else None)
    kept, changed = handin.kept(runner.store, record, design_route(runner), designed_places(record))
    record["handin"] = {"kept": kept, "changed": changed}
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(record, indent=1, default=str))
    refusal = record["benchmarks"]["guard"]["refusal"]
    print(record["line"], flush=True)
    guard = record["benchmarks"]["guard"]
    print(f"benchmarks EUR {guard['total_euros']:.2f} likely, {guard['high_euros']:.2f} high, of "
          f"{benchmarks.CAP_EUROS:.0f}: {'refused: ' + refusal if refusal else 'the guard has room'}; {options.out}")


if __name__ == "__main__":
    main()
