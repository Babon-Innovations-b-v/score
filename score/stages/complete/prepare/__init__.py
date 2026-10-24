"""Prepare a batch (CONTEXT.md "batch", #21): all the risk work before a paid batch, free and on this PC, so the batch
runs once and right. For the environment's remake through the prop pipeline (#19) it lists every take with its input
contract, its key-diff status, its predicted outcome from a measured failure mode, its library match and its fixed
settings, class and zone, and gives the one figure the creator says yes to: euros (likely and high, every job once),
one ETA on the fixed fleet and the predicted gaps beside them. Nothing here buys, keys or judges an output.

    .venv/bin/python -m score.stages.complete.prepare [--library DIR] [--stock] [--moved] [--out FILE]

    groups.py      the free counts: one take a model (kind, size ratio, kit) a place, shell pieces apart
    library.py     library first: the creator's library models matching a take by kind and size ratio
    predict.py     the predicted outcome: a shape every measured row of which failed is a predicted gap
    contract.py    each take's inputs by contract (view, box, size, the view's picture) and its crop's upscale
    machines.py    one class and zone a layer, from the runner's order, the ledgers' boot records and the stock
    estimate.py    the layers' units, euros and minutes, the ETA (gaps/schedule.py) and the one line
    benchmarks.py  the benchmarks that settle #21's cuts, their guard and their one batch (the owner's Buy starts it)
    design.py      each place's design: its concept and plan, approved by the creator before any batch is bought

The record (`WORK/checks/prepare/remake.json` by default):

    {"made_at", "priced_on": {commit, uncommitted, per_unit_sha256},
     "inventory": {read: [place], waiting: [place]},     (priced from each place's current scene inventory reading,
                                                          groups.current; the rest wait on inventory, no euros)
     "counts": {rows, instances, groups, reused, shell_groups, crops, across_places, library, library_old,
                library_code_only, bought, predicted_gaps, input_gaps, terrain, at_risk},
                                         (library: reused, made under today's route or locked; library_old and
                                          library_code_only: a library model matched, but the take is remade)
     "rates": {shape: {failed, of, objects}},             (the measured close-up failures by shape, predict.py)
     "library": {"root", "models"} or {"root": null, "why"},
     "takes": [{place, rows, take, key, route, shell, instances, crop, library, prediction, inputs, upscale, status,
                key_diff}],                               (status: library, made, input gap, terrain node or
                                                          bought, a predicted gap bought too; route groups.ROUTES')
     "layers": {stage: {takes, units, price, minutes, settings, runs: {routes, shell}}},
     "totals": {likely_euros, high_euros, unpriced}, "eta": schedule.schedule's, "expected_gaps",
     "input_gaps_if_bought": {likely_euros, high_euros},
     "moved": {"rows": [{node, euros, why, again}]} or {"not_run": why},
     "benchmarks": {"listed": [...], "guard": {total_euros, high_euros, cap_euros, refusal}},
     "design": {"places": {place: {concept, inventory, plan, output, waits, hint}}, "approved": [place]},   (design.py)
     "not_in_figure": [what the figure leaves out], "line"}
"""
