"""Prepare a batch (CONTEXT.md "batch", #21): all the risk work before a paid batch, free and on this PC, so the batch
runs once and right. For the environment's remake through the prop pipeline (#19) it lists every take with its input
contract, its key-diff status, its predicted outcome from a measured failure mode, its library match and its fixed
settings, class and zone, and gives the one figure the creator says yes to: euros (likely and high, every job once),
one ETA on the fixed fleet and the predicted holes beside them. Nothing here buys, keys or judges an output.

    .venv/bin/python -m score.stages.complete.prepare [--library DIR] [--stock] [--moved] [--out FILE]

    groups.py      the free counts: one take a model (kind, size ratio, kit) a place, shell pieces apart
    library.py     library first: the creator's library models matching a take by kind and size ratio
    predict.py     the predicted outcome: a shape every measured row of which failed is a predicted hole
    contract.py    each take's inputs by contract (view, box, size, the view's picture) and its crop's upscale
    machines.py    one class and zone a layer, from the runner's order, the ledgers' boot records and the stock
    estimate.py    the layers' units, euros and minutes, the ETA (holes/schedule.py) and the one line
    pixal_steps.py Pixal3D's steps by shape: the #55 lock unless P2 sorted a shape the same and the owner said yes
    benchmarks.py  the benchmarks that settle #21's cuts, with their guard; never launched from here

The record (`WORK/checks/prepare/remake.json` by default):

    {"made_at", "priced_on": {commit, uncommitted, per_unit_sha256},
     "counts": {rows, instances, groups, reused, shell_groups, crops, across_places, library, library_code_only,
                bought, predicted_holes, at_risk, inputs_missing},
     "rates": {shape: {failed, of, objects}},             (the measured close-up failures by shape, predict.py)
     "library": {"root", "models"} or {"root": null, "why"},
     "takes": [{place, rows, take, key, shell, instances, crop, library, prediction, inputs, upscale, status,
                key_diff}],                               (status: library, predicted hole or bought)
     "layers": {stage: {takes, units, price, minutes, settings}},
     "totals": {likely_euros, high_euros, unpriced}, "eta": schedule.schedule's, "expected_holes",
     "predicted_holes_if_bought": {likely_euros, high_euros},
     "moved": {"rows": [{node, euros, why, again}]} or {"not_run": why},
     "pixal_steps": {locked, lower, owner_yes, benchmark, why},
     "benchmarks": {"listed": [...], "guard": {total_euros, high_euros, cap_euros, refusal}},
     "not_in_figure": [what the figure leaves out], "line"}
"""
