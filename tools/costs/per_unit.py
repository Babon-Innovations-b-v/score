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

Each entry also carries its `time`, read from the same lines (`times`): a unit's seconds (likely the median, high
the HIGH quantile: a machine's own `unit_seconds` where it wrote them, else the line's wall minutes over its units),
a fresh card's set-up (its start wait and set-up, the median), the jobs a machine ran at once (`slots`: per card times
its cards, one where a line names none) and the share of machine starts that failed; a Google stage's from its calls'
started and finished times, its slots how many of its calls were in flight as each began (the median). A stage with no
such lines read here keeps `time` null with its `why`. The runner turns them into a row's minutes by its own card rule
(compute.unit_minutes). `node_minutes` holds every stage's makes as the store's finish records time them
(score/graph/runs.py node_times: local and paid rows alike), read with `--store`. Neither ever moves a euro: with
`--times-only` the time fields alone are written into the file in place, its euros kept byte for byte, as the old
disk took the ledgers its euros were read from:

    python3 tools/costs/per_unit.py --times-only --ledger paper/evidence/cloud/ledger.jsonl [--google G] \
        [--store $PROPS_HOME/store] --out data/costs/per-unit.json

Several ledgers can hold the same batch (a backup, a reconstruction, the paper's scrubbed copy): a batch is read
once, from the first ledger that holds it. Paths are written with the local roots replaced, as the paper's copies are.
"""
import argparse
import datetime
import json
import pathlib
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
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


def spread(values):
    """{likely, high} of measured values: the median and the HIGH quantile, rounded."""
    return {"likely": round(statistics.median(values), 3), "high": round(quantile(values, HIGH), 3)}


def started_rows(line):
    """The machine rows of a cloud line that started (a line of the first format holds dicts only)."""
    return [row for row in line.get("machines") or () if isinstance(row, dict) and row.get("started", True)]


def failed_starts(line):
    """The machine starts of a cloud line that failed (out of stock, refused): its attempts that never started."""
    return [row for row in line.get("attempts") or () if isinstance(row, dict) and not row.get("started")]


def unit_seconds(line, per_line):
    """The seconds each unit of a cloud line took: its machines' own `unit_seconds`, else its wall minutes over its
    units (one figure for each unit), else none."""
    own = [seconds for row in started_rows(line) for seconds in row.get("unit_seconds") or ()]
    if own:
        return own
    units = line_units(line, per_line)
    return [line["wall_minutes"] * 60 / units] * units if units and line.get("wall_minutes") else []


def setups(line):
    """The minutes each fresh machine of a cloud line took from its order to its first job (start wait and set-up);
    the line's own figure where its machines wrote none."""
    own = [row["start_wait_minutes"] + (row.get("setup_minutes") or 0.0) for row in started_rows(line)
           if row.get("start_wait_minutes") is not None and not row.get("adopted")]
    if own:
        return own
    if line.get("start_wait_minutes") is None:
        return []
    setup = line.get("setup_minutes")
    return [line["start_wait_minutes"] + (setup if setup is not None else (line.get("setup_seconds") or 0.0) / 60)]


def line_slots(line):
    """The jobs each machine of a cloud line ran at once: its per card (one figure, or one a machine) times its cards;
    none where the line names no per card."""
    per_card = line.get("per_card")
    if isinstance(per_card, int):
        return [per_card * max(1, row.get("cards") or 1) for row in started_rows(line)] or [per_card]
    if isinstance(per_card, dict):
        return [value for value in per_card.values() if value]
    return []


def cloud_times(lines, spec):
    """The `time` of a cloud stage from its lines (kind and `who`, as its euros): {unit_seconds, setup_minutes,
    slots, slots_from, failed_start_share, holds, lines, from}, or {why} with no unit timed."""
    found = [(line, source) for line, source in lines if matches(line, spec["cloud"])]
    seconds = [value for line, _ in found for value in unit_seconds(line, spec["per_line"])]
    if not seconds:
        return {"why": f"no ledger line read here timed a unit of {spec['cloud']}"}
    starts = [value for line, _ in found for value in setups(line)]
    slots = [value for line, _ in found for value in line_slots(line)]
    started = sum(len(started_rows(line)) for line, _ in found)
    failed = sum(len(failed_starts(line)) for line, _ in found)
    return {"unit_seconds": spread(seconds), "setup_minutes": round(statistics.median(starts), 3) if starts else 0.0,
            "slots": statistics.median_low(slots) if slots else 1,
            "slots_from": "per card times cards, the median machine" if slots else
                          "one a machine: no line names jobs at once",
            "failed_start_share": round(failed / (failed + started), 3) if failed + started else None,
            "holds": "machines", "lines": len(found),
            "from": sorted({source.rpartition(" line ")[0] for _, source in found})}


def call_spans(calls, caller):
    """[(start, end)] datetimes of `caller`'s finished calls that have their started line (the ledger's later
    format)."""
    begun = {call["call"]: call["time"] for call in calls
             if call.get("caller") == caller and call.get("state") == "started" and call.get("time")}
    return [(datetime.datetime.fromisoformat(begun[call["call"]]), datetime.datetime.fromisoformat(call["time"]))
            for call in calls if call.get("caller") == caller and call.get("state") == "finished"
            and call.get("call") in begun and call.get("time")]


def in_flight(spans):
    """How many of the calls were in flight as each began, itself included."""
    return [sum(1 for other_start, other_end in spans if other_start <= start < other_end) for start, _ in spans]


def google_times(calls, caller, google_path):
    """The `time` of a Google stage from its calls' started and finished lines: {unit_seconds, setup_minutes 0,
    slots, slots_from, failed_start_share, holds, lines, from}, or {why} with none timed."""
    if google_path is None:
        return {"why": "no Google ledger read here (the one its euros were read from went with the old disk, "
                       "2026-10-19)"}
    spans = call_spans(calls, caller)
    if not spans:
        return {"why": f"no call of {caller} in {costs.scrub(str(google_path))} has its started and finished times"}
    failed = sum(1 for call in calls if call.get("caller") == caller and call.get("state") == "failed")
    return {"unit_seconds": spread([(end - start).total_seconds() for start, end in spans]), "setup_minutes": 0.0,
            "slots": statistics.median_low(in_flight(spans)),
            "slots_from": "the calls of the caller in flight as each began, the median",
            "failed_start_share": round(failed / (failed + len(spans)), 3), "holds": "calls", "lines": len(spans),
            "from": [costs.scrub(str(google_path))]}


def times(lines, calls, google_path):
    """{stage: time} of every stage in SPECS from the lines read (cloud_times, google_times), and the RECORDED
    stages' time, null with why."""
    found = {stage: cloud_times(lines, spec) if "cloud" in spec else google_times(calls, spec["google"], google_path)
             for stage, spec in SPECS.items()}
    lost = {"why": "priced from runs written down when they ran, euros and units but no time; their ledger lines "
                   "went with the old disk (2026-10-19)"}
    return {**{stage: lost for stage in RECORDED}, **found}


def node_minutes(records, store):
    """{stage: {likely, high, makes, from}} of the makes' minutes the store's finish records log
    (score.graph.runs.node_times), every stage with one."""
    each = {}
    for record in records:
        each.setdefault(record["stage"], []).append(record["minutes"])
    return {stage: {**spread(minutes), "makes": len(minutes), "from": f"finish records in {costs.scrub(str(store))}"}
            for stage, minutes in sorted(each.items())}


def with_times(body, stage_times, made):
    """The per-unit file's body with each stage's `time` and the `node_minutes` written, nothing else touched."""
    stages = {stage: {**found, "time": stage_times[stage]} for stage, found in body["stages"].items()}
    return {**body, "stages": stages, "node_minutes": made}


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
    rebuilt = with_forecasts(measured)
    kept = {stage: found["time"] for stage, found in body["stages"].items() if "time" in found}
    return {**body, "stages": {stage: {**found, **({"time": kept[stage]} if stage in kept else {})}
                               for stage, found in rebuilt.items()}}


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


def read_calls(path):
    """The Google ledger's lines, [] with no ledger given."""
    if path is None:
        return []
    return [json.loads(text) for text in pathlib.Path(path).read_text().splitlines() if text.strip()]


def store_minutes(root):
    """node_minutes of the store at `root` (its finish records, score.graph.runs.node_times), {} with no store."""
    if root is None:
        return {}
    sys.path.insert(0, str(REPO))
    from score.graph import runs
    from score.store import Store
    return node_minutes(runs.node_times(Store.in_folder(root)), root)


def write_times(options):
    """Write the time fields into --out in place from the ledgers given (and the store's finish records), every
    other field kept as it was."""
    out = pathlib.Path(options.out)
    stage_times = times(ledger_lines(options.ledger or []), read_calls(options.google), options.google)
    body = with_times(json.loads(out.read_text()), stage_times, store_minutes(options.store))
    out.write_text(json.dumps(body, indent=1) + "\n")
    timed = sum(1 for found in stage_times.values() if "unit_seconds" in found)
    print(f"per unit: time of {timed} of {len(stage_times)} stages and {len(body['node_minutes'])} stages' makes "
          f"written into {options.out}, its euros kept")


def write_measures(options):
    """Write --out whole from the ledgers: each stage's euros, rules and time."""
    lines, calls = ledger_lines(options.ledger), read_calls(options.google)
    found = measure(lines, calls, options.google)
    body = with_times({"read": [costs.scrub(path) for path in options.ledger] + [costs.scrub(options.google)],
                       "high_quantile": HIGH, "stages": found},
                      times(lines, calls, options.google), store_minutes(options.store))
    pathlib.Path(options.out).write_text(json.dumps(body, indent=1) + "\n")
    print(f"per unit: {len(found)} stages priced ({len(SPECS)} measured from ledgers when they hold lines, "
          f"{len(RECORDED)} recorded) -> {options.out}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ledger", action="append", help="a cloud ledger, in the order read")
    parser.add_argument("--google", help="the Google ledger")
    parser.add_argument("--store", help="a store root whose finish records time the makes (node_minutes)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--rules-only", action="store_true",
                        help="write only the forecast rules into --out, its measured numbers kept (no ledger read)")
    parser.add_argument("--times-only", action="store_true",
                        help="write only the time fields into --out, its euros kept")
    options = parser.parse_args(argv)
    if options.rules_only:
        out = pathlib.Path(options.out)
        out.write_text(json.dumps(with_rules(json.loads(out.read_text())), indent=1) + "\n")
        print(f"per unit: forecast rules written into {options.out}, its measured numbers kept")
        return
    if options.times_only:
        write_times(options)
        return
    if not options.ledger or not options.google:
        parser.error("--ledger and --google are needed unless --rules-only or --times-only")
    write_measures(options)


if __name__ == "__main__":
    main()
