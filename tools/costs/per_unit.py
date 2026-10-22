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
are forecast from, a source in git (`FORECASTS`), which `score price --gaps` counts (compute.forecast_price), and
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

The remake's stages are priced by the owner's method of 2026-10-20 (#21), written by every mode above (with_warm):
a WARM stage's unit at its jobs' measured work seconds on a warm card (no set-up, no idle; the paper's ledger copy, as
`capacity.py report`'s s/unit) over the jobs a card runs at once, at the saved bill's price a minute for the type,
plus OVERHEAD for warm parked cards' time outside jobs; a BATCH stage's at the Batch API's share of its measured
standard-tier calls, the finish route's asks from the method's list asks with a price_note until their own are on
the ledger. Its `basis` says which; every other stage keeps its fields byte for byte.

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
# score.stages.complete.gaps.price (for the entry's own stage only, never its `also`).
FORECASTS = {
    "prop_takes": "one a model, each once: the takes of the place's prop objects (data/props/<place>.json) not made "
                  "in WORK/pixal, and the missing rows of the place's gaps (score/stages/complete/gaps) whose node "
                  "is this stage's there, by their take",
    "models": "one a model, each once: the takes data/surfaces/<place>.json lists and the models pixal is forecast "
              "to make at the place (prop_takes)",
    "light_jobs": "score/stages/light/passes.py pass_jobs: the views of the place's own scene record: its accepted "
                  "scene-record output's views, else those the scene-record row writes from its filed plan "
                  "(price.planned_views: a standing spot one, a door one but outdoors), VIEWS_A_JOB a job",
    "one": "one a place (one for an environment node)",
    "sound_takes": "score/stages/sound environment_takes: the environment's MOSS takes still to make, one a brief "
                   "and seed, each counted once at the first scene with a sound row (needs.sounded) that plays it",
}
CLOSEUPS_15 = "paper/evidence/cloud/forecast-2026-10-15.txt"
# Per stage: the unit, the ledger lines of its work, the units a line made, how a node's units are counted in its
# accepted output, and how they are forecast before a make (a FORECASTS rule and, where a model makes more than one
# unit, `per_model`). `also` are the stages that made the same unit by the same code (the crops' and people's own
# lines until 2026-10-20: their ledger lines still measure it).
SPECS = {
    "pixal": {"unit": "model", "cloud": {"kind": "pixal"}, "per_line": "models_done",
              "count": {"json_keys": "takes.json"}, "also": ["crops-pixal"], "forecast": "prop_takes"},
    "closeup": {"unit": "close-up picture (Nano Banana Pro)", "google": "pro",
                "count": {"json_field": ["closeups.json", "pro_pictures"]}, "also": ["crops-closeup"],
                "forecast": "prop_takes",
                "per_model": {"units": 1, "models": 1,
                              "from": "tools/props/closeup/stage.py PRO_TAKES: one Pro picture a row, every job once "
                                      f"(#21); the two-take chain the ship's close-ups measured ({CLOSEUPS_15} line "
                                      "37: 25 for 21 pieces, 2026-10-14) is gone"}},
    "light-passes": {"unit": "render job of the light stage", "cloud": {"kind": "blender", "who": "score light stage"},
                     "per_line": "jobs", "count": {"files": "passes/*.views.json"},
                     "forecast": "light_jobs"},
    "settle": {"unit": "drop run", "cloud": {"kind": "blender", "who": "settle"}, "per_line": "one",
               "count": {"one": True}, "forecast": "one"},
    "surfaces-bake": {"unit": "bake job (library_bake.py, one a model)", "cloud": {"kind": "library"},
                      "per_line": "jobs", "count": {"files": "made/*.gltf"}, "also": ["crops-surfaces-bake"],
                      "forecast": "models"},
    # A sound line names its takes (score/stages/sound/takes.py plan_for); the lines written before it, SOUND_TAKES.
    "sound": {"unit": "MOSS take (one brief and seed, its card rented for it)",
              "cloud": {"kind": "prove", "who": "score runner, sound stage"}, "per_line": "takes",
              "forecast": "sound_takes"},
}
# Measured runs of today's route whose ledger lines went with the old disk (2026-10-19), their euros and the units they
# made written down in git when they ran: per stage, its unit, its forecast rule and each run (euros, units, where it
# is written). No count rule: the runner prices them before a make only. A ledger line of the stage, when one is read,
# replaces them.
SHIP_ROOMS = f"{CLOSEUPS_15} line 47: the ship's six rooms, surface line to paint, 12 takes (2026-10-14)"
RECORDED = {
    "surfaces-paint": {"unit": "take painted", "forecast": "models",
                       "runs": [{"euros": 5.83, "units": 12, "source": "commit b11c282f (2026-10-12): the campgrounds' "
                                                                       "cloud paint, twelve takes, EUR 5.83"},
                                {"euros": 0.6, "units": 12, "source": f"{SHIP_ROOMS}, paint EUR 0.6"}]},
    # The benchmark batch of 2026-10-21 (grant 20261021T182203, one score run at commit 99106427): one node a kind,
    # each its node's whole make (forecast "one"); one run, so likely and high alike.
    "finish-route-palette": {"unit": "scene palette of a place (one Gemini 3.1 Pro answer)", "forecast": "one",
                             "runs": [{"euros": 0.022318, "units": 1,
                                       "source": "google ledger call 80322def0eb2437e8ac358dcfccf3e67 "
                                                 "(finish-route-palette@greenhouse, 2026-10-21, benchmark grant "
                                                 "20261021T182203), standard tier"},
                                      {"euros": 0.019218, "units": 1,
                                       "source": "google ledger call 7759147ddd48417e8a1582e304ac85c7 "
                                                 "(finish-route-palette@greenhouse, 2026-10-22, benchmark grant "
                                                 "20261022T072047), standard tier"}],
                             "time": {"unit_seconds": {"likely": 218.5, "high": 242.1},
                                      "setup_minutes": {"likely": 0.0, "high": 0.0}, "slots": 1,
                                      "slots_from": "one call a place", "holds": "calls", "lines": 2,
                                      "from": ["google ledger call 80322def0eb2437e8ac358dcfccf3e67 (started "
                                               "20:33:26, finished 20:36:35 +02:00)",
                                               "google ledger call 7759147ddd48417e8a1582e304ac85c7 (started "
                                               "09:26:01, finished 09:30:09 +02:00 on 2026-10-22)"]}},
    "concept-views": {"unit": "make of the environment's concept views (16 Pro pictures, "
                              "data/definitions/concept_views.json)", "forecast": "one",
                      "runs": [{"euros": 2.254, "units": 1,
                                "source": "google ledger, caller pro, the 16 finished calls 2026-10-21 20:33:25 to "
                                          "20:39:33 +02:00 (concept-views, benchmark grant 20261021T182203), "
                                          "standard tier"}],
                      "time": {"unit_seconds": {"likely": 368.0, "high": 368.0},
                               "setup_minutes": {"likely": 0.0, "high": 0.0}, "slots": 1,
                               "slots_from": "its 16 calls one after another", "holds": "calls", "lines": 16,
                               "from": ["google ledger, caller pro, 20:33:25 to 20:39:33 +02:00 on 2026-10-21"]}},
    "surface-tiles": {"unit": "tile job of a place's shell surfaces (library_bake.py, one card)", "forecast": "one",
                      "runs": [{"euros": 0.07875, "units": 1,
                                "source": "ledger batch library-20261021-203323-3894491 (surface-tiles@greenhouse, "
                                          "2026-10-21, benchmark grant 20261021T182203): one L4, 5.1 machine "
                                          "minutes, its card parked after"}],
                      "time": {"unit_seconds": {"likely": 187.8, "high": 187.8},
                               "setup_minutes": {"likely": 1.9, "high": 1.9}, "slots": 1,
                               "slots_from": "one job on its one card", "holds": "machines", "lines": 1,
                               "from": ["ledger batch library-20261021-203323-3894491 (its machine's unit_seconds; "
                                        "start wait 0.37 and set-up 1.53 min)"]}},
    "people-clips-made": {"unit": "make of the people's Kimodo clips and mean rig (one characters machine)",
                          "forecast": "one",
                          "runs": [{"euros": 0.249375, "units": 1,
                                    "source": "ledger batch characters-20261021-203329-3895203 (people-clips-made, "
                                              "2026-10-21, benchmark grant 20261021T182203): one L4, 18.7 machine "
                                              "minutes"}],
                          "time": {"unit_seconds": {"likely": 245.6, "high": 245.6},
                                   "setup_minutes": {"likely": 14.5, "high": 14.5}, "slots": 1,
                                   "slots_from": "one chain on its one card", "holds": "machines", "lines": 1,
                                   "from": ["ledger batch characters-20261021-203329-3895203 (its machine's "
                                            "unit_seconds; start wait 0.37 and set-up 14.15 min)"]}},
    # The benchmark batch of 2026-10-22 (grant 20261022T072047, one score run at commit aac2fac2): the two guessed
    # kinds that ran, one node each, its whole make (forecast "one").
    "surface-library": {"unit": "scene surface library of a place (one Gemini 3.1 Pro answer)", "forecast": "one",
                        "runs": [{"euros": 0.08087, "units": 1,
                                  "source": "google ledger call 507bf0dfcea54d6b9723bcfe9d29a167 "
                                            "(surface-library@greenhouse, 2026-10-22, benchmark grant "
                                            "20261022T072047), standard tier"},
                                 {"euros": 0.076496, "units": 1,
                                  "source": "google ledger call 3561ae0918c647579b76a704f83cc884 "
                                            "(surface-library@greenhouse, 2026-10-22, benchmark grant "
                                            "20261022T072047 restored, commit d8d8f17e), standard tier"}],
                        "time": {"unit_seconds": {"likely": 218.5, "high": 242.9},
                                 "setup_minutes": {"likely": 0.0, "high": 0.0}, "slots": 1,
                                 "slots_from": "one call a place", "holds": "calls", "lines": 2,
                                 "from": ["google ledger call 507bf0dfcea54d6b9723bcfe9d29a167 (started 09:30:13, "
                                          "finished 09:34:22 +02:00 on 2026-10-22)",
                                          "google ledger call 3561ae0918c647579b76a704f83cc884 (started 11:15:49, "
                                          "finished 11:18:57 +02:00 on 2026-10-22)"]}},
    "crops-concept": {"unit": "make of a place's crop masks on its concept (one card, 7 pictures at greenhouse)",
                      "forecast": "one",
                      "runs": [{"euros": 0.06125, "units": 1,
                                "source": "ledger batch masks-20261022-092631-813070 (crops-concept@greenhouse, "
                                          "2026-10-22, benchmark grant 20261022T072047): one L4, 1.66 machine "
                                          "minutes EUR 0.02625, and its 7 disk-and-address lines EUR 0.035"},
                               {"euros": 0.0625, "units": 1,
                                "source": "ledger batch masks-20261022-102451-988273 (crops-concept@greenhouse, "
                                          "2026-10-22, benchmark grant 20261022T072047 restored, commit 3caaa3be): "
                                          "one L4, 3.56 machine minutes EUR 0.0525, and its 2 disk-and-address "
                                          "lines EUR 0.01"}],
                      "time": {"unit_seconds": {"likely": 78.2, "high": 78.5},
                               "setup_minutes": {"likely": 1.78, "high": 2.54}, "slots": 1,
                               "slots_from": "one job on its one card", "holds": "machines", "lines": 2,
                               "from": ["ledger batch masks-20261022-092631-813070 (its machine's work 1.30 min; "
                                        "start wait 0.36 and set-up 0.46 min; the batch waited 5.69 min in all "
                                        "for a card, 9 starts out of stock or refused)",
                                        "ledger batch masks-20261022-102451-988273 (its machine's work 1.31 min; "
                                        "start wait 2.25 and set-up 0.49 min; 3.83 min wall)"]}},
    # The benchmark runs of 2026-10-22 under the restored grant 20261022T072047 (commit a8ebe414): the one body face
    # that ran, its node's whole make (forecast "one"). Moon's and Mars's faces stay unmeasured.
    "body-face-earth": {"unit": "face of a body of the setting (one Gemini 3.1 Pro answer)", "forecast": "one",
                        "runs": [{"euros": 0.026236, "units": 1,
                                  "source": "google ledger call 3a0c4c5ae9544eedae3b824e57112b78 (body-face-earth, "
                                            "2026-10-22, benchmark grant 20261022T072047 restored), standard tier"}],
                        "time": {"unit_seconds": {"likely": 187.0, "high": 187.0},
                                 "setup_minutes": {"likely": 0.0, "high": 0.0}, "slots": 1,
                                 "slots_from": "one call a body", "holds": "calls", "lines": 1,
                                 "from": ["google ledger call 3a0c4c5ae9544eedae3b824e57112b78 (started 10:11:10, "
                                          "finished 10:14:17 +02:00 on 2026-10-22)"]}},
}


# The owner's method for the remake (2026-10-20, #21), which replaces a WARM or BATCH stage's ledger-measured price: a
# card stage's unit at its measured work seconds on a warm card (no set-up, no idle: its machines' own `unit_seconds`
# of its kind on its machine type in the paper's ledger copy, the capacity report's s/unit) over the jobs a card runs
# at once (capacity.runs_at_once), at the saved bill's euros a minute for that type (costs.unit_prices, the lowest
# zone), plus OVERHEAD for the time warm parked cards spend outside jobs; a Google stage's at the Batch API's share
# of the measured standard-tier calls (google_spend.TIER_PRICE, its euros already counted from dollars there).
EVIDENCE_LEDGER = REPO / "paper/evidence/cloud/ledger.jsonl"
SAVED_BILL = REPO / "paper/evidence/cloud/bill-2026-10-10T0136Z.json"
OVERHEAD = 0.10  # the owner's target share (2026-10-20): replace it with the measured one once runs record it
WARM = {
    "pixal": {"kind": "pixal", "type": "L4-1-24G", "class": "gpu-24gb"},
    "surfaces-bake": {"kind": "library", "type": "L4-1-24G", "class": "gpu-24gb"},
    # A light-passes job is one Blender render job of up to VIEWS_A_JOB views on one L4
    # (passes.CARDS); priced at every timed Blender job on L4 (116 s median in the capacity report), not at light
    # jobs' own seconds: the ledger copy names no job's stage. Its own runs' timings replace it once recorded.
    "light-passes": {"kind": "blender", "type": "L4-1-24G", "class": "gpu-24gb"},
}
# Measured standard-tier calls a BATCH stage is priced from (their Google ledger went with the old disk, 2026-10-19:
# the figures as this file wrote them from it at commit 71b1ccc4, data/costs/per-unit.json).
PRO_PICTURES = {"likely": 0.13991, "high": 0.14096, "runs": 135,
                "from": "$PROPS/cloud/google-ledger.jsonl, caller pro, 135 finished calls, 2026-10-12 to 2026-10-16 "
                        "(standard tier), as data/costs/per-unit.json held them at commit 71b1ccc4"}
LIST_ASKS = {"likely": 0.02244, "high": 0.03329, "runs": 275,
             "from": "$PROPS/cloud/google-ledger.jsonl, caller finishmap-list, 275 finished calls, 2026-10-11 to "
                     "2026-10-16 (standard tier), as data/costs/per-unit.json held them at commit 71b1ccc4"}
ROUTE_ASK = ("the finish route's ask sends every view and the split's groups beside the close-up, so it reads more "
             "than the method's list asks it is priced from; its own batch calls on the ledger replace them")
BATCH = {
    "closeup": {"calls": PRO_PICTURES},
    "finish-route-list": {"calls": LIST_ASKS, "unit": "finish list and labels of a take (Gemini 3.1 Pro, batch)",
                          "forecast": "models", "price_note": ROUTE_ASK},
    "finish-route-recheck": {"calls": LIST_ASKS, "unit": "recheck of a take (Gemini 3.1 Pro, batch)",
                             "forecast": "models", "price_note": ROUTE_ASK},
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


# The takes of the sound lines written before the stage wrote its takes into its line (#10), as their runs made them.
SOUND_TAKES = {"prove-20261020-181655-1467389": 1,  # sound@airlock's first run: one take (2026-10-20, its store log)
               "prove-20261021-005847-4017578": 11}  # sound@square: 11 takes (2026-10-21, #10's readiness report)


def line_units(line, per_line):
    """The units one cloud ledger line finished."""
    if per_line == "takes":
        return line.get("takes") or SOUND_TAKES.get(line.get("batch"), 0)
    if per_line == "one":
        return 1
    if per_line == "jobs":
        return len(line.get("jobs") or [])
    return line.get(per_line) or 0


def matches(line, wanted):
    return all(line.get(field) == value for field, value in wanted.items())


def of_spec(line, spec):
    """Whether a cloud ledger line did the work of `spec`'s stage: a line whose ticket names its node by its stage (or
    one of its `also`) and its kind; an older line with no ticket by its fields (kind and `who`)."""
    named = (line.get("ticket") or "").partition("@")[0]
    if not named:
        return matches(line, spec["cloud"])
    owner = next((found for stage, found in SPECS.items() if named == stage or named in found.get("also", ())), None)
    return owner is spec and line.get("kind") == spec["cloud"]["kind"]


def cloud_measures(lines, spec):
    """([euros a unit], [batch names]) of the cloud lines that did the stage's work and finished a unit."""
    each, batches = [], []
    for line, _ in lines:
        units = line_units(line, spec["per_line"])
        if of_spec(line, spec) and units and line.get("euros") is not None:
            each.append(line["euros"] / units)
            batches.append(line["batch"])
    return each, batches


def google_measures(calls, caller):
    """([euros a call], [days]) of the Google ledger's finished calls of `caller` (a line without a state is a call
    of the ledger's first format, written only once it came back)."""
    found = [call for call in calls if call.get("caller") == caller and call.get("state", "finished") == "finished"
             and call.get("euros") is not None]
    return [call["euros"] for call in found], sorted({call["day"] for call in found})


def per_model(spec):
    """{per_model, per_model_from} of a stage whose model makes more than one unit (its recorded units over models,
    or a bound from the code); {} for one a model."""
    ratio = spec.get("per_model")
    if ratio is None:
        return {}
    return {"per_model": round(ratio["units"] / ratio["models"], 4), "per_model_from": ratio["from"]}


def forecast(spec):
    """The forecast fields of a stage's entry: its rule with the source it counts and, where a model makes more than
    one unit, how many; a price note where its measured price was asked otherwise than today."""
    rule = spec["forecast"]
    note = {"price_note": spec["price_note"]} if "price_note" in spec else {}
    return {"forecast": {"rule": rule, "source": FORECASTS[rule], **per_model(spec)}, **note}


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
    """The seconds each unit of a cloud line took: its machines' own `unit_seconds`, else its machines' working
    minutes times the jobs each ran at once over its units (one figure for each unit: a job's time were the units
    shared evenly), else none."""
    own = [seconds for row in started_rows(line) for seconds in row.get("unit_seconds") or ()]
    if own:
        return own
    units, rows = line_units(line, per_line), started_rows(line)
    work = sum(row.get("work_minutes", row.get("minutes")) or 0.0 for row in rows) if rows else \
        line.get("machine_minutes") or 0.0
    found = line_slots(line)
    slots = statistics.median_low(found) if found else 1
    return [work * 60 * slots / units] * units if units and work else []


def row_slots(line, row):
    """The jobs one machine row of a cloud line ran at once: its per card times its cards, else the line's median
    (line_slots), else one."""
    per_card = line.get("per_card")
    if isinstance(per_card, int) and per_card > 0:
        return per_card * max(1, row.get("cards") or 1)
    found = line_slots(line)
    return statistics.median_low(found) if found else 1


def in_machine_setup(line, row):
    """The minutes a started machine worked before its jobs (install, sync, model load): its own `setup_minutes`,
    else its working minutes less its jobs' seconds over the jobs it ran at once, floored at 0; 0 where it timed no
    job (its units are then timed by its working minutes whole, unit_seconds)."""
    if row.get("setup_minutes") is not None:
        return row["setup_minutes"]
    jobs = row.get("unit_seconds") or ()
    work = row.get("work_minutes")
    if not jobs or work is None:
        return 0.0
    return max(0.0, work - sum(jobs) / row_slots(line, row) / 60)


def setups(line):
    """The minutes each fresh machine of a cloud line took from its order to its first job: its start wait and its
    in-machine set-up (in_machine_setup); the line's own figure where its machines wrote none."""
    own = [row["start_wait_minutes"] + in_machine_setup(line, row) for row in started_rows(line)
           if row.get("start_wait_minutes") is not None and not row.get("adopted")]
    if own:
        return own
    if line.get("start_wait_minutes") is None:
        return []
    setup = line.get("setup_minutes")
    return [line["start_wait_minutes"] + (setup if setup is not None else (line.get("setup_seconds") or 0.0) / 60)]


def line_slots(line):
    """The jobs each machine of a cloud line ran at once: its per card (one figure, or one a machine, whose machine
    rows are not named: times the line's median cards) times its cards; none where the line names no per card."""
    per_card, rows = line.get("per_card"), started_rows(line)
    cards = statistics.median_low([max(1, row.get("cards") or 1) for row in rows]) if rows else 1
    if isinstance(per_card, int) and per_card > 0:
        return [per_card * max(1, row.get("cards") or 1) for row in rows] or [per_card]
    if isinstance(per_card, dict):
        return [value * cards for value in per_card.values() if value and value > 0]
    return []


def cloud_times(lines, spec):
    """The `time` of a cloud stage from its lines (kind and `who`, as its euros): {unit_seconds, setup_minutes
    ({likely, high} of its fresh machines' set-ups, or {why} where no line timed one), slots, slots_from,
    failed_start_share, holds, lines, from}, or {why} with no unit timed."""
    found = [(line, source) for line, source in lines if of_spec(line, spec)]
    seconds = [value for line, _ in found for value in unit_seconds(line, spec["per_line"])]
    if not seconds:
        return {"why": f"no ledger line read here timed a unit of {spec['cloud']}"}
    starts = [value for line, _ in found for value in setups(line)]
    slots = [value for line, _ in found for value in line_slots(line)]
    started = sum(len(started_rows(line)) for line, _ in found)
    failed = sum(len(failed_starts(line)) for line, _ in found)
    setup = spread(starts) if starts else {"why": "no line read here timed a machine's set-up"}
    return {"unit_seconds": spread(seconds), "setup_minutes": setup,
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
    """How many of the calls were in flight as each began, itself included (one that ended the second it began
    too)."""
    return [1 + sum(1 for other, (other_start, other_end) in enumerate(spans)
                    if other != index and other_start <= start < other_end)
            for index, (start, _) in enumerate(spans)]


def google_times(calls, caller, google_path):
    """The `time` of a Google stage from its calls' started and finished lines: {unit_seconds, setup_minutes
    (none: a call holds no machine), slots, slots_from, failed_start_share, holds, lines, from}, or {why} with none
    timed."""
    if google_path is None:
        return {"why": "no Google ledger read here (the one its euros were read from went with the old disk, "
                       "2026-10-19)"}
    spans = call_spans(calls, caller)
    if not spans:
        return {"why": f"no call of {caller} in {costs.scrub(str(google_path))} has its started and finished times"}
    failed = sum(1 for call in calls if call.get("caller") == caller and call.get("state") == "failed")
    return {"unit_seconds": spread([(end - start).total_seconds() for start, end in spans]),
            "setup_minutes": {"likely": 0.0, "high": 0.0},
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
    return {**{stage: spec.get("time", lost) for stage, spec in RECORDED.items()}, **found}


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
    stages = {stage: {**found, "time": stage_times.get(stage, {"why": "no rule in per_unit.py reads its time"})}
              for stage, found in body["stages"].items()}
    return {**body, "stages": stages, "node_minutes": made}


def kept_times(body, stage_times, made):
    """The times to write in place: each stage's new time, else the file's measured one (a ledger or store not read
    here takes no measure away), and the store's makes, else the file's."""
    old = {stage: found.get("time") or {} for stage, found in body["stages"].items()}
    return ({stage: found if "unit_seconds" in found or "unit_seconds" not in old.get(stage, {}) else old[stage]
             for stage, found in stage_times.items()}, made if made else body.get("node_minutes", {}))


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
    return {stage: {**{name: value for name, value in found.items()
                       if name not in ("forecast", "forecast_why", "price_note")},
                    **forecast(specs[stage])} for stage, found in every.items()}


def with_rules(body):
    """The per-unit file's body with every ledger-measured stage's forecast fields written again, its measured numbers
    kept, and the RECORDED stages written again."""
    measured = {stage: found for stage, found in body["stages"].items() if stage in SPECS}
    rebuilt = with_forecasts(measured)
    kept = {stage: found["time"] for stage, found in body["stages"].items() if "time" in found}
    kept.update({stage: spec["time"] for stage, spec in RECORDED.items() if "time" in spec})  # its run's own times
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


def warm_rows(spec):
    """The machine rows of the paper's ledger copy that ran the stage's kind on its machine type and timed their jobs
    (capacity.machine_rows: a row with its line's kind)."""
    capacity = cloud_module("capacity")
    lines = [json.loads(text) for text in EVIDENCE_LEDGER.read_text().splitlines() if text.strip()]
    return [row for row in capacity.machine_rows(lines) if row["kind"] == spec["kind"]
            and row.get("type") == spec["type"] and row.get("started", True) and row.get("unit_seconds")]


def cloud_module(name):
    """A module of tools/props/cloud (capacity, google_spend), its folder put on the path."""
    folder = str(costs.CLOUD_TOOLS / "cloud")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return __import__(name)


def hourly(machine_type):
    """The saved bill's euros an hour for `machine_type` (costs.unit_prices, the lowest zone)."""
    return costs.hourly_price(costs.unit_prices(json.loads(SAVED_BILL.read_text())), machine_type)


def slots_of(spec):
    """The jobs one card of the spec's class runs of its kind at once (capacity.runs_at_once)."""
    return cloud_module("capacity").runs_at_once(spec["kind"], spec["class"])


def warm_price(spec, seconds):
    """Euros of one unit of `seconds` work on a warm card of the spec's type: over the jobs a card runs at once, at
    the saved bill's euros a second, plus OVERHEAD."""
    return seconds / slots_of(spec) * hourly(spec["type"]) / 3600 * (1 + OVERHEAD)


def own_rows(stage, spec, lines):
    """([machine row], [ledger]) of the lines read here whose ticket names `stage` that ran on the spec's type and
    timed their jobs: the stage's own work, which prices it in place of every job of its kind once read."""
    named = [(line, source) for line, source in lines if (line.get("ticket") or "").partition("@")[0] == stage]
    rows = [row for row in cloud_module("capacity").machine_rows([line for line, _ in named])
            if row["kind"] == spec["kind"] and row.get("type") == spec["type"] and row.get("started", True)
            and row.get("unit_seconds")]
    return rows, sorted({source.rpartition(" line ")[0] for _, source in named})


def warm_time(spec, seconds, machines, old, origin):
    """A warm stage's `time`: its work seconds and the jobs a card runs at once, the set-up and failed starts of its
    file's `time` kept (a fresh fleet still sets up), {why} for a set-up never measured."""
    return {**old, "unit_seconds": spread(seconds), "slots": slots_of(spec),
            "slots_from": f"capacity.runs_at_once({spec['kind']}, {spec['class']})",
            "setup_minutes": old.get("setup_minutes") or {"why": "no line read here timed a machine's set-up"},
            "holds": "machines", "lines": machines, "from": origin}


def warm_entry(found, spec, own=((), ())):
    """A stage's entry priced by the owner's warm-card method (WARM), its rules and count kept: on its own timed jobs
    (`own`, own_rows) where a ledger read here holds them, else every job of its kind in the paper's ledger copy."""
    rows, origin = own if own[0] else (warm_rows(spec), [costs.scrub(str(EVIDENCE_LEDGER))])
    whose = "of its own jobs" if own[0] else f"jobs of kind {spec['kind']}"
    seconds = [value for row in rows for value in row["unit_seconds"]]
    sources = {"warm work": f"{', '.join(origin)}: {len(seconds)} {whose} timed "
                            f"on {len(rows)} {spec['type']} machines (unit_seconds; capacity.py report's s/unit)",
               "machine price": f"{costs.scrub(str(SAVED_BILL))}: {spec['type']} EUR {hourly(spec['type']):.4f} an "
                                "hour "
                                "(costs.unit_prices, the lowest zone), by the minute",
               "overhead": f"{OVERHEAD:.0%} for time outside jobs on warm parked cards, the owner's target "
                           "(2026-10-20) until runs record it"}
    return {**found, "likely_euros": round(warm_price(spec, statistics.median(seconds)), 5),
            "high_euros": round(warm_price(spec, quantile(seconds, HIGH)), 5), "runs": len(seconds),
            "sources": sources, "basis": "warm work time", "time": warm_time(spec, seconds, len(rows), found.get("time") or {}, origin)}


def batch_entry(stage, found, spec):
    """A Google stage's entry at the Batch API's share of its measured standard-tier calls (BATCH)."""
    share, calls = cloud_module("google_spend").TIER_PRICE["batch"], spec["calls"]
    rules = {**SPECS.get(stage, {}), **spec}
    base = found or {"stage": stage, "unit": rules["unit"], "count": rules.get("count"), "also": rules.get("also", []),
                     **forecast(rules), "time": {"why": "no batch call of it timed yet"}}
    return {**base, "likely_euros": round(calls["likely"] * share, 5), "high_euros": round(calls["high"] * share, 5),
            "runs": calls["runs"], "sources": {"google calls": calls["from"],
                                               "batch tier": f"google_spend.TIER_PRICE['batch'] = {share}"},
            "basis": "batch price of measured calls"}


def bare_entry(stage):
    """A SPECS stage's entry before any ledger line of it is read: its unit, count rule and forecast fields."""
    spec = SPECS[stage]
    return {"stage": stage, "unit": spec["unit"], "count": spec.get("count"), "also": spec.get("also", []),
            **forecast(spec)}


def priced_own(found):
    """Whether a stage's entry was priced warm on its own timed jobs (its time read from a ledger other than the
    paper's copy)."""
    return bool(found) and found.get("basis") == "warm work time" and \
        (found.get("time") or {}).get("from") not in (None, [costs.scrub(str(EVIDENCE_LEDGER))])


def with_warm(body, lines=()):
    """The per-unit file's body with every WARM and BATCH stage priced by the owner's method of 2026-10-20 (a WARM
    stage on its own timed jobs where `lines` hold them), every other stage as it was."""
    stages = dict(body["stages"])
    for stage, spec in WARM.items():
        own = own_rows(stage, spec, lines)
        if not own[0] and priced_own(stages.get(stage)):
            continue  # its own jobs were read from a ledger not given here: kept, never priced back on its kind's
        if stage in stages or stage in SPECS:  # a SPECS stage no ledger line measured is priced warm from its rules
            stages[stage] = warm_entry(stages.get(stage) or bare_entry(stage), spec, own)
    for stage, spec in BATCH.items():
        stages[stage] = batch_entry(stage, stages.get(stage), spec)
    return {**body, "stages": stages}


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
    """Write the time fields into --out in place from the ledgers given (and the store's finish records), a measured
    time those do not hold kept, every other field as it was."""
    out = pathlib.Path(options.out)
    before = json.loads(out.read_text())
    stage_times, made = kept_times(before, times(ledger_lines(options.ledger or []), read_calls(options.google),
                                                 options.google), store_minutes(options.store))
    body = with_times(before, stage_times, made)
    out.write_text(json.dumps(with_warm(body, ledger_lines(options.ledger or [])), indent=1) + "\n")
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
    pathlib.Path(options.out).write_text(json.dumps(with_warm(body, lines), indent=1) + "\n")
    print(f"per unit: {len(found)} stages priced ({len(SPECS)} measured from ledgers when they hold lines, "
          f"{len(RECORDED)} recorded) -> {options.out}")


def write_added(options):
    """Write into --out in place what the ledgers given hold of each cloud stage outside WARM (its euros, rules and
    time) and every WARM stage's own timed jobs, every stage they hold no line of kept as it was: the ledgers the rest
    were read from went with the old disk (2026-10-19)."""
    out = pathlib.Path(options.out)
    before, lines = json.loads(out.read_text()), ledger_lines(options.ledger)
    found = {}
    for stage, spec in SPECS.items():
        each, batches = cloud_measures(lines, spec) if "cloud" in spec and stage not in WARM else ([], [])
        if each:
            found[stage] = {**entry(stage, spec, each, {"cloud batches": batches}), **forecast(spec),
                            "time": cloud_times(lines, spec)}
    read = before["read"] + [path for path in map(costs.scrub, options.ledger) if path not in before["read"]]
    body = {**before, "read": read, "stages": {**before["stages"], **found}}
    out.write_text(json.dumps(with_warm(body, lines), indent=1) + "\n")
    print(f"per unit: {', '.join(found) or 'no stage'} measured from {len(options.ledger)} ledgers, the warm stages' "
          f"own jobs read, every other stage kept -> {options.out}")


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
    parser.add_argument("--add", action="store_true",
                        help="write the stages the --ledger files hold lines of into --out, every other stage kept")
    options = parser.parse_args(argv)
    if options.rules_only:
        out = pathlib.Path(options.out)
        out.write_text(json.dumps(with_warm(with_rules(json.loads(out.read_text()))), indent=1) + "\n")
        print(f"per unit: forecast rules written into {options.out}, its measured numbers kept")
        return
    if options.times_only:
        write_times(options)
        return
    if options.add:
        if not options.ledger:
            parser.error("--add reads the --ledger files given")
        write_added(options)
        return
    if not options.ledger or not options.google:
        parser.error("--ledger and --google are needed unless --rules-only or --times-only")
    write_measures(options)


if __name__ == "__main__":
    main()
