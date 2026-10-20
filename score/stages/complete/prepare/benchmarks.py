"""The benchmarks that settle #21's cuts, prepared and never launched from here: each one batch through the runner's
paid path (`score run ... --detach`, so the runner clears it, reserves its estimate and writes every euro to the
ledgers). At most CAP_EUROS for all of them together, counted on their highs: each one's `euros` is its likely figure
and `high_euros` its high, #21's design estimates said as estimates (high equal to the estimate until measured).
`needs` names what must land before one can run. None lowers a setting that ships: quality is never a cost lever
(owner, 2026-10-20), so a benchmark of fewer Pixal3D steps, fewer film samples or a finish list on low thinking is
never listed (#21).

Before any of them starts, the month's guard (compute.month_refusal) is asked for the total: while the month's books
are unknown it refuses, and the owner runs `score spend --read-back` and `score spend --google-month EUR` first.
"""
from score.adapters import compute

CAP_EUROS = 20.0
RUN = ".venv/bin/python -m score run world1 --detach"
ESTIMATED = (
    {"id": "P1", "what": "Pixal3D: a set of takes on one L4, slots from its peak memory", "euros": 1.5,
     "needs": "#21 track A: one run a job, no retry_once", "command": f"{RUN} --place campgrounds --stage pixal"},
    {"id": "P3", "what": "Pixal3D: the same takes on one H100, euros a model against the L4", "euros": 1.5,
     "needs": "#21 track A, and SCORE_MAX_MACHINES='gpu-24gb=0' for this run only",
     "command": f"SCORE_MAX_MACHINES='gpu-24gb=0' {RUN} --place campgrounds --stage pixal"},
    {"id": "S1", "what": "settle: every drop of a place on one cpu-4c-32gb machine", "euros": 0.6,
     "needs": "#21 track C: settle on cpu-4c-32gb only", "command": f"{RUN} --place habitat --stage settle"},
    {"id": "C1", "what": "people: three looks packed on one L4", "euros": 1.5,
     "needs": "#21 track C: packed looks, one close-up",
     "command": f"{RUN} --stage people-dress-bram-work --stage people-dress-nev-work --stage people-dress-sefa-work"},
    {"id": "M1", "what": "sound: MOSS seed 1 only, CLAP sorting pass or hole", "euros": 1.5,
     "needs": "#21 track C: seed 1 in score/stages/sound/takes.py", "command": f"{RUN} --place garage --stage sound"},
)


def listed():
    """Every benchmark, each with its likely `euros` and its `high_euros`."""
    return [{"high_euros": each["euros"], **each} for each in ESTIMATED]


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
