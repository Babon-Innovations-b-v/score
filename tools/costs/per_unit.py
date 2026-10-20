"""What one unit of a paid stage's work costs, measured from the ledgers, kept as data the runner prices from.

    python3 tools/costs/per_unit.py --ledger <ledger.jsonl> [--ledger ...] --google <google-ledger.jsonl> \
        --out data/costs/per-unit.json

The owner's rule (2026-10-18): a price comes only from measured per-unit numbers, at full cost. A unit is what the
stage makes one of (a model, a close-up picture, a render job); `SPECS` says, per stage, which ledger lines did that
work and how many units each line made. Cloud lines: each batch's whole euros (every machine it held, set-up, failed
starts) over the units it finished. Google lines: each finished call's euros (the ledger's figure). Likely is the
median of those per-unit euros, high their HIGH quantile; `runs` is how many batches or calls they rest on, and
`sources` names each batch (a call's ledger is named with its caller and days). The runner counts a node's units in
its accepted output by the entry's `count` (score.adapters.compute.unit_price). A stage with no lines here stays
unmeasured: no price, never a guess shown as one.

The old disk took the live ledgers (2026-10-19). A stage of today's route whose runs' euros and units were written
down in git when they ran (`RECORDED`: a committed evidence file and line, or a commit) is priced from those runs, its
`sources` naming each, its `runs` how many, and no count rule (priced before a make only); a ledger line of it, once
read, replaces them.

Before a node is made it has nothing to count, so an entry also carries its `forecast` rule: what the units of a make
are forecast from, a source in git (`FORECASTS`), which `score price --holes` counts (compute.forecast_price), and
where a model makes more than one unit, `per_model`: a close-up's pictures a model as recorded, a finish map's or a
naming's calls over the take lists' calls in the same Google ledger (one list a take). The rules are this file's, so
`--rules-only` writes them, and the RECORDED stages, into the per-unit file in place, its ledger-measured numbers kept,
when the ledgers it rests on are not on this box:

    python3 tools/costs/per_unit.py --rules-only --out data/costs/per-unit.json

Several ledgers can hold the same batch (a backup, a reconstruction, the paper's scrubbed copy): a batch is read
once, from the first ledger that holds it. Paths are written with the local roots replaced, as the paper's copies are.
"""
import argparse
import json
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import costs  # noqa: E402

HIGH = 0.9  # the high price's quantile, as preflight.HIGH
# The forecast rules: what a make's units are forecast from before it runs, each from a source in git, counted by
# score.stages.complete.holes.price (for the entry's own stage only, never its `also`).
FORECASTS = {
    "prop_takes": "one a model, each once: the takes of the place's prop objects (data/props/<place>.json) not made "
                  "in WORK/pixal, and the missing rows of the place's holes (score/stages/complete/holes) whose node "
                  "is this stage's there, by their take",
    "models": "one a model, each once: the takes data/surfaces/<place>.json lists and the models pixal is forecast "
              "to make at the place (prop_takes)",
    "light_jobs": "score/stages/light/passes.py pass_jobs: the demo's views of each place shown, VIEWS_A_JOB a job "
                  "(the views of the place's scene record, data/scene/<place>.json, while the demo's copy of them is "
                  "lost)",
    "one": "one a place (one for an environment node)",
}
# A Google stage whose units are not one a model: its calls over the take lists' calls in the same ledger (the lists
# stage asks once a take), so a model is forecast to need that many.
LISTS = "surfaces-lists"
CLOSEUPS_15 = "paper/evidence/cloud/forecast-2026-10-15.txt"
# Per stage: the unit, the ledger lines of its work, the units a line made, how a node's units are counted in its
# accepted output, and how they are forecast before a make (a FORECASTS rule and, where a model makes more than one
# unit, `per_model`). `also` are the stages that make the same unit by the same code (the crops' and people's lines).
SPECS = {
    "pixal": {"unit": "model", "cloud": {"kind": "pixal"}, "per_line": "models_done",
              "count": {"json_keys": "takes.json"}, "also": ["crops-pixal"], "forecast": "prop_takes"},
    "closeup": {"unit": "close-up picture (Nano Banana Pro)", "google": "pro",
                "count": {"json_field": ["closeups.json", "pro_pictures"]}, "also": ["crops-closeup"],
                "forecast": "prop_takes",
                "per_model": {"units": 25, "models": 21, "from": f"{CLOSEUPS_15} line 37: the ship's close-ups, 25 "
                                                                 "Pro pictures for 21 pieces (2026-10-14)"}},
    "surfaces-maps": {"unit": "finish map picture (Nano Banana Pro)", "google": "finishmap-map",
                      "count": {"map_attempts": "map.json"}, "also": ["crops-surfaces-maps", "people-maps"],
                      "forecast": "models", "per_model": {"over": LISTS}},
    "surfaces-lists": {"unit": "finish list of a take (Gemini 3.1 Pro)", "google": "finishmap-list",
                       "count": {"take_files": ".json"}, "also": ["crops-surfaces-lists", "people-lists"],
                       "forecast": "models"},
    "surfaces-names": {"unit": "finish named again (Gemini 3.1 Pro)", "google": "finishmap-name",
                       "count": {"named_again": ".json"}, "also": ["crops-surfaces-names", "people-names"],
                       "forecast": "models", "per_model": {"over": LISTS}},
    "light-passes": {"unit": "render job of the light stage", "cloud": {"kind": "blender", "who": "score light stage"},
                     "per_line": "jobs", "count": {"files": "passes/*.views.json"}, "also": ["light-haze"],
                     "forecast": "light_jobs"},
    "settle": {"unit": "drop run", "cloud": {"kind": "blender", "who": "settle"}, "per_line": "one",
               "count": {"one": True}, "forecast": "one"},
    "surfaces-bake": {"unit": "bake job (library_bake.py, one a model)", "cloud": {"kind": "library"},
                      "per_line": "jobs", "count": {"files": "made/*.gltf"}, "also": ["crops-surfaces-bake"],
                      "forecast": "models"},
}
# Measured runs of today's route whose ledger lines went with the old disk (2026-10-19), their euros and the units they
# made written down in git when they ran: per stage, its unit, its forecast rule and each run (euros, units, where it
# is written). No count rule: the runner prices them before a make only. A ledger line of the stage, when one is read,
# replaces them.
STAGE_EUROS_13 = "paper/evidence/cloud/stage-euros-2026-10-13.txt"
SHIP_ROOMS = f"{CLOSEUPS_15} line 47: the ship's six rooms, surface line to paint, 12 takes (2026-10-14)"
RECORDED = {
    "surfaces-turntable": {"unit": "take turned (turntable render)", "forecast": "models",
                           "runs": [{"euros": 2.4, "units": 12, "source": f"{SHIP_ROOMS}, turntables EUR 2.4"}]},
    "surfaces-segvigen": {"unit": "take split back (SegviGen)", "forecast": "models",
                          "runs": [{"euros": 0.63, "units": 12, "source": f"{SHIP_ROOMS}, SegviGen EUR 0.63"}]},
    "surfaces-paint": {"unit": "take painted", "forecast": "models",
                       "runs": [{"euros": 5.83, "units": 12, "source": "commit b11c282f (2026-10-12): the campgrounds' "
                                                                       "cloud paint, twelve takes, EUR 5.83"},
                                {"euros": 0.6, "units": 12, "source": f"{SHIP_ROOMS}, paint EUR 0.6"}]},
    "ship_kit": {"unit": "ship kit of a place baked", "forecast": "one",
                 "runs": [{"euros": 0.60, "units": 8, "source": "commit 1198efc8 (2026-10-15): the ship's eight shell "
                                                                "kits baked by ship_kit@<place>, EUR 0.60"},
                          {"euros": 0.13, "units": 1, "source": "commit dc6851c4 (2026-10-15): ship_kit@engineroom, "
                                                                "EUR 0.13"}]},
    "concept_people": {"unit": "make of the environment's people concept", "forecast": "one",
                       "runs": [{"euros": 2.41, "units": 1,
                                 "source": f"{STAGE_EUROS_13} line 12 (world 1's ticketed run, 16 rows), its re-buy "
                                           f"priced at it in {CLOSEUPS_15} line 55"}]},
}


def quantile(values, share):
    """The `share` quantile of `values` (inclusive), the value itself for one."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    return statistics.quantiles(ordered, n=100, method="inclusive")[round(share * 100) - 1]


def ledger_lines(paths):
    """[(line, source)] of the cloud ledgers, each batch once (the first ledger that holds it wins)."""
    seen, found = set(), []
    for path in paths:
        for number, text in enumerate(pathlib.Path(path).read_text().splitlines(), 1):
            try:
                line = json.loads(text)
            except json.JSONDecodeError:
                continue  # a torn line of a backup: no batch can be read from it
            batch = line.get("batch")
            if batch is None or batch in seen:
                continue
            seen.add(batch)
            found.append((line, f"{costs.scrub(str(path))} line {number}"))
    return found


def line_units(line, per_line):
    """The units one cloud ledger line finished."""
    if per_line == "one":
        return 1
    if per_line == "jobs":
        return len(line.get("jobs") or [])
    return line.get(per_line) or 0


def matches(line, wanted):
    return all(line.get(field) == value for field, value in wanted.items())


def cloud_measures(lines, spec):
    """([euros a unit], [batch names]) of the cloud lines that did the stage's work and finished a unit."""
    each, batches = [], []
    for line, _ in lines:
        units = line_units(line, spec["per_line"])
        if matches(line, spec["cloud"]) and units and line.get("euros") is not None:
            each.append(line["euros"] / units)
            batches.append(line["batch"])
    return each, batches


def google_measures(calls, caller):
    """([euros a call], [days]) of the Google ledger's finished calls of `caller` (a line without a state is a call
    of the ledger's first format, written only once it came back)."""
    found = [call for call in calls if call.get("caller") == caller and call.get("state", "finished") == "finished"
             and call.get("euros") is not None]
    return [call["euros"] for call in found], sorted({call["day"] for call in found})


def per_model(spec, stages):
    """{per_model, per_model_from} of a stage whose model makes more than one unit: recorded units over models, or
    its calls over the take lists' calls in `stages` (the measured entries); {} for one a model."""
    ratio = spec.get("per_model")
    if ratio is None:
        return {}
    if "over" not in ratio:
        return {"per_model": round(ratio["units"] / ratio["models"], 4), "per_model_from": ratio["from"]}
    if ratio["over"] not in stages:
        raise SystemExit(f"{spec['stage']}: its units a model are its calls over {ratio['over']}'s, which no ledger "
                         "read here measured")
    mine, lists = stages[spec["stage"]], stages[ratio["over"]]
    return {"per_model": round(mine["runs"] / lists["runs"], 4),
            "per_model_from": f"{mine['runs']} {spec['unit']} calls over {lists['runs']} take lists ({ratio['over']}, "
                              "one call a take) in the same Google ledger"}


def forecast(spec, stages):
    """The forecast fields of a stage's entry: its rule with the source it counts and, where a model makes more than
    one unit, how many."""
    rule = spec["forecast"]
    return {"forecast": {"rule": rule, "source": FORECASTS[rule], **per_model(spec, stages)}}


def entry(stage, spec, each, sources):
    return {"stage": stage, "unit": spec["unit"], "count": spec.get("count"), "also": spec.get("also", []),
            "likely_euros": round(statistics.median(each), 5), "high_euros": round(quantile(each, HIGH), 5),
            "runs": len(each), "sources": sources}


def recorded():
    """{stage: entry} of the RECORDED runs, each run's euros over its units."""
    return {stage: entry(stage, spec, [run["euros"] / run["units"] for run in spec["runs"]],
                         {"recorded runs": [run["source"] for run in spec["runs"]]})
            for stage, spec in RECORDED.items()}


def with_forecasts(stages):
    """`stages` (measured entries) and the RECORDED stages no ledger measured, each with its forecast fields written
    from SPECS or RECORDED."""
    every = {**recorded(), **stages}
    specs = {**RECORDED, **SPECS}
    return {stage: {**{name: value for name, value in found.items() if name not in ("forecast", "forecast_why")},
                    **forecast({**specs[stage], "stage": stage}, every)} for stage, found in every.items()}


def with_rules(body):
    """The per-unit file's body with every ledger-measured stage's forecast fields written again, its measured numbers
    kept, and the RECORDED stages written again."""
    measured = {stage: found for stage, found in body["stages"].items() if stage in SPECS}
    return {**body, "stages": with_forecasts(measured)}


def measure(lines, calls, google_path):
    """{stage: entry} of every stage in SPECS with measured lines (a stage with none is left out), and the RECORDED
    stages no ledger measured."""
    found = {}
    for stage, spec in SPECS.items():
        if "cloud" in spec:
            each, batches = cloud_measures(lines, spec)
            sources = {"cloud batches": batches}
        else:
            each, days = google_measures(calls, spec["google"])
            sources = {"google calls": f"{costs.scrub(str(google_path))}, caller {spec['google']}, "
                                       f"{len(each)} finished calls, {days[0] if days else ''} to "
                                       f"{days[-1] if days else ''}"}
        if each:
            found[stage] = entry(stage, spec, each, sources)
    return with_forecasts(found)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ledger", action="append", help="a cloud ledger, in the order read")
    parser.add_argument("--google", help="the Google ledger")
    parser.add_argument("--out", required=True)
    parser.add_argument("--rules-only", action="store_true",
                        help="write only the forecast rules into --out, its measured numbers kept (no ledger read)")
    options = parser.parse_args(argv)
    if options.rules_only:
        out = pathlib.Path(options.out)
        out.write_text(json.dumps(with_rules(json.loads(out.read_text())), indent=1) + "\n")
        print(f"per unit: forecast rules written into {options.out}, its measured numbers kept")
        return
    if not options.ledger or not options.google:
        parser.error("--ledger and --google are needed unless --rules-only")
    lines = ledger_lines(options.ledger)
    calls = [json.loads(text) for text in pathlib.Path(options.google).read_text().splitlines() if text.strip()]
    found = measure(lines, calls, options.google)
    body = {"read": [costs.scrub(path) for path in options.ledger] + [costs.scrub(options.google)],
            "high_quantile": HIGH, "stages": found}
    pathlib.Path(options.out).write_text(json.dumps(body, indent=1) + "\n")
    print(f"per unit: {len(found)} stages priced ({len(SPECS)} measured from ledgers when they hold lines, "
          f"{len(RECORDED)} recorded) -> {options.out}")


if __name__ == "__main__":
    main()
