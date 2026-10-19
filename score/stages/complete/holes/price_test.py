"""The holes priced by the runner: a node two holes share is priced once with their units summed, a later node the
place's completion reads is priced too, and a hole no stage fills goes to the unfillable list with its work. A toy
table (pixal, its bake, complete) in a store of its own, with per-unit numbers and holes written in the test. No
cloud, no Blender.

Run: .venv/bin/python score/stages/complete/holes/price_test.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.stages.complete.holes import price  # noqa: E402
from score.store import Store  # noqa: E402

compute.ledger().entries = lambda: []  # no measured runs: the per-unit numbers price
TEXT = contracts.Contract("toy-text", 1, lambda folder: [])
READS = ("toy-text", 1)


def make_nothing(inputs, out, seed, params):
    raise AssertionError("nothing is made when holes are priced")


SAID = (checks.Check("said", lambda output, inputs, evidence: checks.Verdict("said", checks.PASS, "said")),)
TABLE = [graph.Stage("pixal", "place", make_nothing, TEXT, SAID, files={"brief": "{data}/{place}.txt"}, paid=True,
                     euros=20.0),
         graph.Stage("surfaces-bake", "place", make_nothing, TEXT, SAID, after={"pixal": READS}, paid=True,
                     euros=2.0),
         graph.Stage("sound", "place", make_nothing, TEXT, SAID, paid=True, euros=1.0),
         graph.Stage("complete", "place", make_nothing, TEXT, SAID,
                     after={"surfaces-bake": READS, "sound": READS})]
PER_UNIT = {"stages": {
    "pixal": {"stage": "pixal", "unit": "model", "count": {"json_keys": "takes.json"}, "also": [],
              "likely_euros": 0.2, "high_euros": 0.5, "runs": 50, "sources": {},
              "forecast": {"rule": "missing_rows", "source": "the place's missing rows"}},
    "surfaces-bake": {"stage": "surfaces-bake", "unit": "bake job", "count": {"files": "made/*.gltf"}, "also": [],
                      "likely_euros": 0.04, "high_euros": 0.2, "runs": 200, "sources": {},
                      "forecast": {"rule": "models", "source": "the takes and the missing rows"}}}}


def hole(number, node, work=None):
    return {"id": f"missing:crate_{number}", "rule": "missing", "node": node, "work": work}


def a_place():
    """(runner, holes root): the hangar's data (3 takes in its surface data) and its holes: two missing rows pixal
    makes, one the sound fills, one no stage fills."""
    data, root = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    (data / "surfaces").mkdir()
    (data / "surfaces/hangar.json").write_text(json.dumps({"takes": {"a": {}, "b": {}, "c": {}}}))
    (root / "hangar").mkdir()
    (root / "hangar/findings.json").write_text(json.dumps({"place": "hangar", "outputs": {}, "findings": [
        hole(1, "pixal@hangar"), hole(2, "pixal@hangar"), {**hole(3, "sound@hangar"), "rule": "gate"},
        hole(4, None, "a rough-model stage")]}))
    runner = graph.Runner(TABLE, graph.Environment("toy", 1, {"data": data}), Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {"kind": kind})
    return runner, root


def priced():
    kept = compute.PER_UNIT
    compute.PER_UNIT = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    compute.PER_UNIT.write_text(json.dumps(PER_UNIT))
    try:
        runner, root = a_place()
        return price.holes_price(runner, "toy", root, ["hangar"], runner.store, made_at="2026-10-19T20:00:00+00:00")
    finally:
        compute.PER_UNIT = kept


def test_a_node_two_holes_share_is_priced_once_with_their_units_summed():
    found = priced()
    pixal = found["nodes"]["pixal@hangar"]
    assert (pixal["units"], pixal["basis"], pixal["likely_euros"], pixal["high_euros"]) == (
        2, "per unit × forecast", 0.4, 1.0), pixal
    bake = found["nodes"]["surfaces-bake@hangar"]
    assert (bake["units"], bake["basis"], bake["likely_euros"]) == (5, "per unit × forecast", 0.2), bake
    assert found["holes"]["hangar"] == {"missing:crate_1": "pixal@hangar", "missing:crate_2": "pixal@hangar",
                                        "missing:crate_3": "sound@hangar"}
    assert found["chains"]["hangar"]["pixal@hangar"] == [  # complete reads the sound too: the place needs it
        "complete@hangar", "pixal@hangar", "sound@hangar", "surfaces-bake@hangar"]
    assert found["free"] == ["complete@hangar"]


def test_a_stage_with_no_forecast_rule_is_a_guess_that_says_where_and_kept_out_of_the_price():
    found = priced()
    sound = found["nodes"]["sound@hangar"]
    assert sound["likely_euros"] is None and sound["guess_euros"] == 1.0, sound
    assert sound["guess_from"].startswith("score/stages/complete/holes/price_test.py:")
    assert found["totals"] == {"likely_euros": 0.6, "high_euros": 2.0, "guessed_euros": 1.0, "guessed": 1,
                               "unpriced": [], "nodes": 3}, found["totals"]


def test_a_hole_no_stage_fills_goes_to_the_unfillable_list_with_its_work():
    found = priced()
    assert found["unfillable"] == [{"work": "a rough-model stage", "holes": 1}]
    assert all(None not in nodes.values() for nodes in found["holes"].values())


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[4] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
