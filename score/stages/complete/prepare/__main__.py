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
from score.stages.complete.prepare import benchmarks, contract, estimate, groups, library, machines, predict
from score.store import PROPS_HOME

REPO = pathlib.Path(__file__).resolve().parents[4]
WORK = PROPS_HOME / "work"
OUT = WORK / "checks" / "prepare" / "remake.json"
WORLD = "world1"
NOT_IN_FIGURE = ("the places' own paid rows (settle, light passes, effects look, tiles): `score price world1 --gaps`",
                 "films, people, sound and terrain: their layers' prepare steps are #21 tracks C's",
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


def status_of(match, prediction, is_made):
    """library (a model made under today's route, or locked, matches), made (its take stands), predicted gap, or
    bought."""
    if match["pipeline"]:
        return "library"
    if is_made:
        return "made"
    return "predicted gap" if prediction["outcome"] == "predicted gap" else "bought"


def take_entry(group, record, index, rates, work):
    """One take of the batch: its group with its library match, prediction, input faults, crop upscale, status and
    key-diff status."""
    match = library.match(group, index)
    prediction = predict.predicted(group["size"], rates)
    is_made = made(group["take"])
    return {**group, "library": match, "prediction": prediction, "inputs": contract.faults(record, group, work),
            "upscale": contract.upscale(group["box"]), "status": status_of(match, prediction, is_made),
            "key_diff": "made: its take stands, not bought again" if is_made else "new: no take of it stands"}


def take_counts(takes):
    """The batch's counts by status, and how many bought takes wait on lost inputs."""
    bought = [take for take in takes if take["status"] == "bought"]
    return {"library": sum(take["status"] == "library" for take in takes),
            "library_code_only": sum(not take["library"]["pipeline"] and bool(take["library"]["code"])
                                     for take in takes),
            "library_old": sum(not take["library"]["pipeline"] and bool(take["library"]["old"]) for take in takes),
            "made": sum(take["status"] == "made" for take in takes), "bought": len(bought),
            "predicted_gaps": sum(take["status"] == "predicted gap" for take in takes),
            "at_risk": sum(take["prediction"]["outcome"] == "at risk" for take in bought),
            "inputs_missing": sum(bool(take["inputs"]) for take in bought)}


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
    found = moved.rebuys(runner, runner.line_nodes(stages.places(runner.world), True))
    return [{"node": buy.node, "euros": buy.euros, "why": buy.why, "again": buy.again} for buy in found]


def priced_layers(route, takes, fixed):
    """(layers of the bought takes, layers of the predicted gaps) on the route."""
    rules = estimate.one_shot()
    bought = [take for take in takes if take["status"] == "bought"]
    gaps = [take for take in takes if take["status"] == "predicted gap"]
    return estimate.layers(route, bought, rules, fixed), estimate.layers(route, gaps, rules, fixed)


def across_places(route, takes, fixed):
    """{takes, totals} of the bought takes if one take served a model (kind, size ratio, kit) in every place: the
    owner's call, since a place's style may differ, so never the figure itself."""
    shared = list({tuple(map(str, take["key"])): take for take in takes if take["status"] == "bought"}.values())
    return {"takes": len(shared), "totals": estimate.totals(estimate.layers(route, shared, estimate.one_shot(), fixed))}


def remake(runner, data, root, work, stock=None, moved=None):
    """The remake's prepare record (this package's docstring)."""
    inventories = groups.inventories(data)
    by_place = {place: groups.place_groups(place, record) for place, record in inventories.items()}
    index, library_entry = read_library(root, inventories)
    rates = predict.hub_rates(data)
    takes = [take_entry(group, inventories[place], index, rates, work)
             for place, found in by_place.items() for group in found if not group["reuse"]]
    route = price.route_stages(runner)
    fixed = fixed_machines(route, stock)
    found, gaps = priced_layers(route, takes, fixed)
    edges = estimate.route_edges(runner.stages, route)
    record = {"made_at": graph.now(), "priced_on": price.priced_on(),
              "counts": {**groups.counts(by_place), **take_counts(takes)}, "rates": rates, "library": library_entry,
              "takes": takes, "layers": found, "totals": estimate.totals(found),
              "eta": estimate.eta(found, edges, graph.JOBS, price.run_cap()),
              "expected_gaps": estimate.expected_gaps([take for take in takes if take["status"] == "bought"]),
              "predicted_gaps_if_bought": estimate.totals(gaps),
              "across_places": across_places(route, takes, fixed),
              "moved": {"rows": moved} if moved is not None else {"not_run": "--moved not given"},
              "benchmarks": {"listed": benchmarks.listed(), "guard": benchmarks.guard()},
              "not_in_figure": list(NOT_IN_FIGURE)}
    return {**record, "line": estimate.line(record)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--library")
    parser.add_argument("--stock", action="store_true")
    parser.add_argument("--moved", action="store_true")
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--data", type=pathlib.Path, default=REPO / "data")
    options = parser.parse_args(argv)
    runner = stages.runner(world=stages.WORLDS[WORLD]())
    stock = stock_read(price.route_stages(runner)) if options.stock else None
    record = remake(runner, options.data, library_root(options.library), WORK, stock,
                    moved_rows(runner) if options.moved else None)
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(json.dumps(record, indent=1, default=str))
    refusal = record["benchmarks"]["guard"]["refusal"]
    print(record["line"], flush=True)
    guard = record["benchmarks"]["guard"]
    print(f"benchmarks EUR {guard['total_euros']:.2f} likely, {guard['high_euros']:.2f} high, of "
          f"{benchmarks.CAP_EUROS:.0f}: {'refused: ' + refusal if refusal else 'the guard has room'}; {options.out}")


if __name__ == "__main__":
    main()
