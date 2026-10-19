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
unmeasured: the runner shows its declared estimate as a guess, never as a price.

Before a node is made it has nothing to count, so an entry also carries its `forecast` rule: what the units of a make
are forecast from, a source in git (`FORECASTS`), which `score price --holes` counts (compute.forecast_price). An entry
with no rule says why in `forecast_why`, and its node's price stays the stage's guess. The rules are this file's, so
`--rules-only` writes them into the per-unit file in place, its measured numbers kept, when the ledgers it rests on
are not on this box (the old disk took the live ones, 2026-10-19):

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
    "light_jobs": "score/stages/light/passes.py pass_jobs: the demo's views of each place shown, VIEWS_A_JOB a job",
    "one": "one a place",
}
# A per-model forecast needs a ledger line that holds both a batch's units and its models; the Google ledger names
# only each call's caller, so these stages have no rule and their price stays a guess.
NO_BATCH = "no ledger line holds both a batch's units and its models: the Google ledger names only each call's caller"
# Per stage: the unit, the ledger lines of its work, the units a line made, how a node's units are counted in its
# accepted output, and how they are forecast before a make (a FORECASTS rule, or None and why). `also` are the
# stages that make the same unit by the same code (the crops' and people's lines).
SPECS = {
    "pixal": {"unit": "model", "cloud": {"kind": "pixal"}, "per_line": "models_done",
              "count": {"json_keys": "takes.json"}, "also": ["crops-pixal"], "forecast": "prop_takes"},
    "closeup": {"unit": "close-up picture (Nano Banana Pro)", "google": "pro",
                "count": {"json_field": ["closeups.json", "pro_pictures"]}, "also": ["crops-closeup"],
                "forecast": None, "forecast_why": NO_BATCH},
    "surfaces-maps": {"unit": "finish map picture (Nano Banana Pro)", "google": "finishmap-map",
                      "count": {"map_attempts": "map.json"}, "also": ["crops-surfaces-maps", "people-maps"],
                      "forecast": None, "forecast_why": NO_BATCH},
    "surfaces-lists": {"unit": "finish list of a take (Gemini 3.1 Pro)", "google": "finishmap-list",
                       "count": {"take_files": ".json"}, "also": ["crops-surfaces-lists", "people-lists"],
                       "forecast": "models"},
    "surfaces-names": {"unit": "finish named again (Gemini 3.1 Pro)", "google": "finishmap-name",
                       "count": {"named_again": ".json"}, "also": ["crops-surfaces-names", "people-names"],
                       "forecast": None, "forecast_why": NO_BATCH},
    "light-passes": {"unit": "render job of the light stage", "cloud": {"kind": "blender", "who": "score light stage"},
                     "per_line": "jobs", "count": {"files": "passes/*.views.json"}, "also": ["light-haze"],
                     "forecast": "light_jobs"},
    "settle": {"unit": "drop run", "cloud": {"kind": "blender", "who": "settle"}, "per_line": "one",
               "count": {"one": True}, "forecast": "one"},
    "surfaces-bake": {"unit": "bake job (library_bake.py, one a model)", "cloud": {"kind": "library"},
                      "per_line": "jobs", "count": {"files": "made/*.gltf"}, "also": ["crops-surfaces-bake"],
                      "forecast": "models"},
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


def forecast(spec):
    """The forecast fields of a stage's entry: its rule with the source it counts, or none and why."""
    rule = spec["forecast"]
    if rule is None:
        return {"forecast": None, "forecast_why": spec["forecast_why"]}
    return {"forecast": {"rule": rule, "source": FORECASTS[rule]}}


def entry(stage, spec, each, sources):
    return {"stage": stage, "unit": spec["unit"], "count": spec["count"], "also": spec.get("also", []),
            "likely_euros": round(statistics.median(each), 5), "high_euros": round(quantile(each, HIGH), 5),
            "runs": len(each), "sources": sources, **forecast(spec)}


def with_rules(body):
    """The per-unit file's body with every measured stage's forecast fields written again from SPECS, its measured
    numbers kept."""
    stages = {}
    for stage, found in body["stages"].items():
        kept = {name: value for name, value in found.items() if name not in ("forecast", "forecast_why")}
        stages[stage] = {**kept, **forecast(SPECS[stage])}
    return {**body, "stages": stages}


def measure(lines, calls, google_path):
    """{stage: entry} of every stage in SPECS with measured lines; a stage with none is left out."""
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
    return found


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
    print(f"per unit: {len(found)} of {len(SPECS)} stages measured -> {options.out}")


if __name__ == "__main__":
    main()
