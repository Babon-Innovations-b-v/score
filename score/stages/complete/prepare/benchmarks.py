"""The benchmarks that settle #21's cuts, as one batch the creator buys as one basket item ("Benchmarks", #21): each
through the runner's paid path once (`score run`, so the runner clears it against the stop the owner's Buy wrote, its
high plus 10%, and writes every euro to the ledgers that tools/costs/per_unit.py reads on its next regeneration).
At most CAP_EUROS for all of them together, counted on their highs with the row estimates of the unmeasured ones.
None lowers a setting that ships: quality is never a cost lever (owner, 2026-10-20), so no benchmark of fewer
Pixal3D steps, fewer film samples or a finish list on low thinking is listed (#21).

    .venv/bin/python -m score.stages.complete.prepare.benchmarks run [--detach]

`listed()` gives each benchmark with its estimate (likely and high euros at its stages' measured per unit with the
bill share, else its row's estimate kept apart as `guess_euros`; minutes on one card from the measured unit seconds
and set-up, else the estimate its issue wrote, `minutes_from`) and its command. A benchmark with no paid path is a gap
(`gap`), never run, never priced. `run` is the batch, only ever started by the owner's checkout of the item: each
benchmark's plan first (free, `score plan`); one whose inputs are lost or not standing, which would buy any other
paid row, or which buys nothing is a gap and is never substituted; the rest run one after another, each once
(runs side by side would share their places' free nodes, which the run registry refuses). Its record:
WORK/checks/benchmarks/<made_at>.json, {made_at, benchmarks: [{id, gap or exit, started, minutes}]}.

Before the batch the books guard (compute.books_refusal) is asked: while the month's books are unknown it refuses, and the owner enters the month's Google figure on the cockpit's Buy screen first.
"""
import argparse
import json
import math
import os
import pathlib
import shlex
import subprocess
import sys
import time

from score import graph, stages
from score.adapters import compute
from score.graph import runs, stopped
from score.stages.complete.prepare import estimate
from score.store import PROPS_HOME

CAP_EUROS = 20.0
WORLD = "world1"
REPO = pathlib.Path(__file__).resolve().parents[4]
RECORDS = PROPS_HOME / "work" / "checks" / "benchmarks"
MODULE = "score.stages.complete.prepare.benchmarks"
ONE_L4 = "all=1,gpu-48gb=0,gpu-80gb=0,gpu-24gb-x2=0,gpu-80gb-x2=0"  # capacity.caps: one machine, an L4 only
GOOGLE_BATCH = "Google's batch page (ai.google.dev/gemini-api/docs/batch-mode): a 24 h target, most jobs much sooner"
# id, what, the run's --place and --stage, the paid stages it may buy and their units (`buys`), the run's extra
# environment, and the issue's minutes where its stages have no measured time.
BENCHMARKS = (
    {"id": "pixal-l4", "what": "Pixal3D: the 12 takes of the cockpit and the engine room on one warm L4, each job "
                              "timed",
     "places": ("cockpit", "engineroom"), "stages": ("pixal",), "buys": {"pixal": 12},
     "env": {"SCORE_MAX_MACHINES": ONE_L4}},
    {"id": "finish-route", "what": "the finish route on 40 takes: views, one Gemini batch list a place, the split's "
                                  "disagreement share, one recheck",
     "places": ("campgrounds", "hangar", "garage"), "stages": ("finish-route-recheck",),
     "buys": {"finish-route-list": 40, "finish-route-recheck": 40},
     "minutes": {"likely": 60.0, "high": 2 * 1440.0, "from": f"two batches a place, {GOOGLE_BATCH}"}},
    {"id": "sound", "what": "sound: the square's two takes on one L4", "places": ("square",), "stages": ("sound",),
     "buys": {"sound": 1}, "minutes": {"likely": 9.2, "high": 18.4, "from": "#29: about 8 min to the first take "
                                                                            "and 0.6 a take; high twice that"}},
    {"id": "film", "what": "films: the hub's place film, 192 frames at 1280x720 on one L4", "places": ("hub",),
     "stages": ("demo-film",), "buys": {"demo-film": 1},
     "minutes": {"likely": 64.0, "high": 144.0, "from": "#28: 192 frames at 17 s (720p measured) to 42 s "
                                                        "(demo.FRAME_MINUTES), plus about 10 min set-up"}},
    {"id": "light-passes", "what": "light passes at the hangar, once", "places": ("hangar",),
     "stages": ("light-passes",), "buys": {"light-passes": 1}},
    {"id": "earth-kit", "what": "the airlock's earth kit, once: 15 make_kit jobs on one L4", "places": ("airlock",),
     "stages": ("earth-kit",), "buys": {"earth-kit": 15}},
    {"id": "settle", "what": "settle: three drops in one run", "places": ("habitat", "hangar", "garage"),
     "stages": ("settle",), "buys": {"settle": 3}},
    {"id": "gemini-batch-direct", "what": "Gemini batch against direct on 20 finish lists",
     "gap": "no paid path asks a finish list direct: the route's list asks only through the Batch API "
            "(score/stages/surfaces/route_ask.py), and nothing rents or asks outside a row the runner clears"},
)


def selection(each):
    """The --place and --stage words of a benchmark's run."""
    return [word for place in each["places"] for word in ("--place", place)] + \
        [word for stage in each["stages"] for word in ("--stage", stage)]


def run_argv(each):
    return [sys.executable, "-m", "score", "run", WORLD, *selection(each)]


def row_estimate(stage, places):
    """The row's own estimate for `places` nodes (Stage.euros): what the runner's clearance reserves for a node never
    measured, so the stop must hold it."""
    row = next(row for row in stages.STAGES if row.name == stage)
    return round(float(row.euros) * places, 2)


def euros(each):
    """{likely_euros, high_euros, guess_euros, euros_from}: its stages at their measured per unit with the bill share
    (estimate.layer_price), else every stage at its row's estimate as a guess."""
    entries = {stage: compute.per_unit(stage) for stage in each["buys"]}
    if all(entry and entry["stage"] == stage for stage, entry in entries.items()):
        priced = [estimate.layer_price(stage, units) for stage, units in each["buys"].items()]
        return {"likely_euros": round(sum(found["likely_euros"] for found in priced), 2),
                "high_euros": round(sum(found["high_euros"] for found in priced), 2), "guess_euros": None,
                "euros_from": "measured per unit (data/costs/per-unit.json), card stages times the bill share"}
    guess = sum(row_estimate(stage, len(each["places"])) for stage in each["buys"])
    return {"likely_euros": None, "high_euros": None, "guess_euros": round(guess, 2),
            "euros_from": "no measured per unit: the row's estimate (Stage.euros), what the runner reserves"}


def card_minutes(stage, units, setup_from):
    """(likely, high) minutes of `units` jobs of a card stage on one card: its set-up, then the jobs `slots` at a
    time at their measured seconds; None when it has no measured unit seconds. `setup_from` the per-unit time whose
    set-up stands in when the stage's own is unmeasured (its card class's)."""
    time_of = (compute.per_unit(stage) or {}).get("time") or {}
    seconds = time_of.get("unit_seconds")
    if not seconds:
        return None
    setup = time_of.get("setup_minutes") or {}
    if "likely" not in setup:
        setup = setup_from.get("setup_minutes") or {}
    rounds = math.ceil(units / max(1, time_of.get("slots") or 1))
    return (round(setup.get("likely", 0.0) + rounds * seconds["likely"] / 60, 1),
            round(setup.get("high", 0.0) + rounds * seconds["high"] / 60, 1))


def minutes(each):
    """{likely_minutes, high_minutes, minutes_from}: the issue's estimate where it gives one, else each stage's jobs
    on one card one after another (card_minutes, the L4 set-up measured on Pixal3D's cards where a stage has none)."""
    if "minutes" in each:
        given = each["minutes"]
        return {"likely_minutes": given["likely"], "high_minutes": given["high"], "minutes_from": given["from"]}
    l4 = (compute.per_unit("pixal") or {}).get("time") or {}
    found = [card_minutes(stage, units, l4) for stage, units in each["buys"].items()]
    if None in found:
        return {"likely_minutes": None, "high_minutes": None, "minutes_from": "a stage has no measured unit seconds"}
    return {"likely_minutes": round(sum(pair[0] for pair in found), 1),
            "high_minutes": round(sum(pair[1] for pair in found), 1),
            "minutes_from": "measured unit seconds on one card (per-unit.json); a set-up not measured is the L4's"}


def listed():
    """Every benchmark with its estimate, minutes and command; a gap with its why and nothing else."""
    found = []
    for each in BENCHMARKS:
        if "gap" in each:
            found.append({"id": each["id"], "what": each["what"], "gap": each["gap"]})
            continue
        env = " ".join(f"{name}={shlex.quote(value)}" for name, value in each.get("env", {}).items())
        command = " ".join(filter(None, [env, ".venv/bin/python -m score run", WORLD, *selection(each)]))
        found.append({"id": each["id"], "what": each["what"], "places": list(each["places"]),
                      "stages": list(each["stages"]), "buys": dict(each["buys"]), "command": command, "gap": None,
                      **euros(each), **minutes(each)})
    return found


def total(benchmarks, key):
    """The sum of `key` over the benchmarks that run (None counts nothing)."""
    return round(sum(each.get(key) or 0.0 for each in benchmarks if not each.get("gap")), 2)


def high_with_guesses(benchmarks):
    """What the runner clears them at: their highs and the row estimates of the unmeasured ones."""
    return round(total(benchmarks, "high_euros") + total(benchmarks, "guess_euros"), 2)


def guard(benchmarks=None):
    """{total_euros, high_euros, cap_euros, refusal}: refusal is why the benchmarks may not start (their high, guesses
    in, over the cap, or the books guard's reason), else None."""
    benchmarks = listed() if benchmarks is None else benchmarks
    high = high_with_guesses(benchmarks)
    if high > CAP_EUROS:
        refusal = f"the benchmarks' high EUR {high:.2f} passes their EUR {CAP_EUROS:.0f} cap"
    else:
        refusal = compute.books_refusal()
    return {"total_euros": total(benchmarks, "likely_euros"), "high_euros": high, "cap_euros": CAP_EUROS,
            "refusal": refusal}


# --- the batch ------------------------------------------------------------------------------------------------------

def run_env(each):
    return {**os.environ, **each.get("env", {})}


def last_json(text):
    """The last line of a command's output that is a JSON object, or None."""
    return next((json.loads(line) for line in reversed(text.strip().splitlines()) if line.startswith("{")), None)


def plan_gap(each, plan):
    """Why a benchmark's runner plan (`score plan --json`'s object) may not run as it stands, or None: inputs lost or
    not standing, a refusal, a paid row other than its own, or nothing to buy."""
    if plan["missing"]:
        return f"inputs not standing: {'; '.join(plan['missing'][:4])}"
    if plan.get("blocked"):
        return f"blocked: {'; '.join(f'{node}: {why}' for node, why in list(plan['blocked'].items())[:3])}"
    if plan["refusal"]:
        return f"refused: {plan['refusal']}"
    other = sorted(buy["node"] for buy in plan["buys"] if buy["node"].split("@")[0] not in each["buys"])
    if other:
        return f"would also buy {', '.join(other[:5])}: its inputs are not standing"
    return None if plan["buys"] else "buys nothing: every node of it stands accepted"


def planned_gap(each, call=subprocess.run):
    """The runner's free plan of a benchmark's run, as plan_gap says it; a plan that fails is a gap with why."""
    done = call([sys.executable, "-m", "score", "plan", WORLD, *selection(each), "--json"], cwd=REPO,
                env=run_env(each), capture_output=True, text=True)
    plan = last_json(done.stdout or "") if done.returncode == 0 else None
    if plan is None:
        return f"its plan failed: {((done.stderr or done.stdout or 'no output').strip().splitlines() or [''])[-1]}"
    return plan_gap(each, plan)


def ran(each, call=subprocess.run):
    """{exit, started, minutes} of the benchmark's one `score run`, its output into this process's (the batch's log)."""
    started, began = graph.now(), time.monotonic()
    print(f"benchmark {each['id']}: {' '.join(run_argv(each)[2:])}", flush=True)
    done = call(run_argv(each), cwd=REPO, env=run_env(each))
    return {"exit": done.returncode, "started": started, "minutes": round((time.monotonic() - began) / 60, 1)}


def batch(call=subprocess.run, records=RECORDS):
    """The batch: each benchmark's gap, or its one run; the record written. 0 when every run that started ended 0."""
    made_at = graph.now()
    found = []
    for each in BENCHMARKS:
        gap = each.get("gap") or planned_gap(each, call)
        found.append({"id": each["id"], "gap": gap} if gap else {"id": each["id"], "gap": None, **ran(each, call)})
        print(f"benchmark {each['id']}: {'gap: ' + gap if gap else 'exit ' + str(found[-1]['exit'])}", flush=True)
    records.mkdir(parents=True, exist_ok=True)
    (records / f"{made_at.replace(':', '')}.json").write_text(json.dumps({"made_at": made_at, "benchmarks": found},
                                                                         indent=1))
    return 1 if any(each.get("exit") for each in found) else 0


def detach():
    """Start the batch in a session of its own under graph/stopped.py, its output and result line into a fresh log;
    print the line the compute backend reads (`detached: started pid=N log=PATH`) and return at once."""
    log = runs.log_path("benchmarks")
    command = [sys.executable, stopped.__file__, "--log", str(log), "--outputs", str(RECORDS), "--",
               sys.executable, "-m", MODULE, "run"]
    with open(log, "a") as result:
        process = subprocess.Popen(command, cwd=REPO, stdin=subprocess.DEVNULL, stdout=result,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    print(f"detached: started pid={process.pid} log={log}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--detach", action="store_true")
    options = parser.parse_args(argv)
    if options.detach:
        return detach()
    refusal = guard()["refusal"]
    if refusal:
        print(f"benchmarks refused: {refusal}", flush=True)
        sys.exit(1)
    sys.exit(batch())


if __name__ == "__main__":
    main()
