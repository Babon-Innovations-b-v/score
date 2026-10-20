"""The benchmarks that settle #21's cuts, prepared and never launched from here: each one batch through a paid path
that writes every euro to the ledgers, the runner's (`score run ... --detach`, so the runner clears it and reserves
its estimate) or, for P2, the batch tool's own (tools/props/cloud/batch.py under the owner's override ticket, as
similar.py's pairs are). At most CAP_EUROS for all of them together, counted on their highs: each one's `euros` is
its likely figure and `high_euros` its high, #21's design estimates said as estimates (high equal to the estimate
until measured), P2's computed from pixal's measured per unit (pixal_steps.benchmark_euros). `needs` names what must
land before one can run. None lowers a setting that ships on a guess: P2 lowers Pixal3D's steps
for a shape only where every check sorts it the same (pixal_steps.py); a films benchmark of fewer samples is left out,
since its samples ship and no check sorts them (#21, 2026-10-20).

Before any of them starts, the month's guard (compute.month_refusal) is asked for the total: while the month's books
are unknown it refuses, and the owner runs `score spend --read-back` and `score spend --google-month EUR` first.
"""
from score.adapters import compute
from score.stages.complete.prepare import pixal_steps

CAP_EUROS = 20.0
LIKENESS_EUROS = 1.0  # DINOv2's pairs, score/stages/props/likeness_row.py LIKENESS_EUROS
RUN = ".venv/bin/python -m score run world1 --detach"
ESTIMATED = (
    {"id": "F-A", "what": "finish maps: one draw a map on Gemini's flex tier against the measured 7.51 calls a take",
     "euros": 4.5, "needs": "#21 track B: one draw a map and serviceTier sent by google_spend.post",
     "command": f"{RUN} --place campgrounds --stage surfaces-maps"},
    {"id": "P1", "what": "Pixal3D: a set of takes on one L4, slots from its peak memory", "euros": 1.5,
     "needs": "#21 track A: one run a job, no retry_once", "command": f"{RUN} --place campgrounds --stage pixal"},
    {"id": "P3", "what": "Pixal3D: the same takes on one H100, euros a model against the L4", "euros": 1.5,
     "needs": "#21 track A, and SCORE_MAX_MACHINES='gpu-24gb=0' for this run only",
     "command": f"SCORE_MAX_MACHINES='gpu-24gb=0' {RUN} --place campgrounds --stage pixal"},
    {"id": "S1", "what": "settle: every drop of a place on one cpu-4c-32gb machine", "euros": 0.6,
     "needs": "#21 track C: settle on cpu-4c-32gb only", "command": f"{RUN} --place habitat --stage settle"},
    {"id": "F-B", "what": "finish lists: one ask on low thinking on the flex tier", "euros": 0.5,
     "needs": "#21 track B: ASKS = 1 and serviceTier", "command": f"{RUN} --place campgrounds --stage surfaces-lists"},
    {"id": "C1", "what": "people: three looks packed on one L4", "euros": 1.5,
     "needs": "#21 track C: packed looks, one close-up",
     "command": f"{RUN} --stage people-dress-bram-work --stage people-dress-nev-work --stage people-dress-sefa-work"},
    {"id": "M1", "what": "sound: MOSS seed 1 only, CLAP sorting pass or hole", "euros": 1.5,
     "needs": "#21 track C: seed 1 in score/stages/sound/takes.py", "command": f"{RUN} --place garage --stage sound"},
)


def p2():
    """P2, priced from pixal's measured per unit with the bill share: 6 chunky takes twice and DINOv2's pairs."""
    euros = pixal_steps.benchmark_euros(compute.per_unit("pixal"), LIKENESS_EUROS)
    return {"id": "P2", "what": "Pixal3D: 8 sampling steps against 12 on chunky takes, same seed; a shape runs lower "
                                "only where the shape check, outline and DINOv2 likeness sort it the same",
            "euros": euros["likely_euros"], "high_euros": euros["high_euros"],
            "needs": "#21 track A: one run a job, no retry in batch.py (landed); the owner's yes on the #55 lock, at "
                     f"least 3 chunky close-ups, and his override yes for the node override, key p2-steps, at its "
                     f"high, EUR {euros['high_euros']:.2f}",
            "command": "python -m score.stages.complete.prepare.pixal_steps list <close-ups> <inventory.json> <out>; "
                       "SCORE_SPEND_TICKET='override p2-steps' tools/props/cloud/batch.py <out>/list.txt "
                       "--who 'P2 benchmark' --inventory <inventory.json> --no-finish"}


def listed():
    """Every benchmark, each with its likely `euros` and its `high_euros`."""
    return [{"high_euros": each["euros"], **each} for each in ESTIMATED] + [p2()]


def total(benchmarks, key="euros"):
    return round(sum(each.get(key, each["euros"]) for each in benchmarks), 2)


def guard(benchmarks=None):
    """{total_euros, high_euros, cap_euros, refusal}: refusal is why the benchmarks may not start (their highs over
    the cap, or the month's guard's reason for their highs), else None."""
    benchmarks = listed() if benchmarks is None else benchmarks
    high = total(benchmarks, "high_euros")
    if high > CAP_EUROS:
        refusal = f"the benchmarks' high EUR {high:.2f} passes their EUR {CAP_EUROS:.0f} cap"
    else:
        refusal = compute.month_refusal(high)
    return {"total_euros": total(benchmarks), "high_euros": high, "cap_euros": CAP_EUROS, "refusal": refusal}
