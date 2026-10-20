"""The remake's milestones, worked out from a toy table's reads and never written by hand: shapes first (the ground,
the shell's concept, plan and rough model, its split, then the inside place's own), then what the place holds, its
completion, the film past it, the environment's film (no row: unpriced, with why) and the owner's approval last; each
node after every node it reads; a paid node with no measured price unknown with its reason and its stage's set budget
labelled set, never summed; the code work of the holes at the step it waits at (a lost input at its reader's); the
month's books on the first paid step. A toy table in a store of its own, per-unit numbers written in the test. No
cloud, no Blender.

    terrain (world, paid) -> plan -> rough-model (paid) -> shell-split -> scene-record -> pixal (paid) -> complete
    complete -> demo-film (paid, not measured: set EUR 3.2) -> library (an end: nothing reads it)

Run: .venv/bin/python score/stages/complete/holes/milestones_test.py
"""
import contextlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.stages.complete.holes import WORLD, milestones, price  # noqa: E402
from score.store import Store  # noqa: E402

compute.ledger().entries = lambda: []  # no measured runs: the per-unit numbers price
TEXT = contracts.Contract("toy-text", 1, lambda folder: [])
READS = ("toy-text", 1)
SAID = (checks.Check("said", lambda output, inputs, evidence: checks.Verdict("said", checks.PASS, "said")),)
BOOKS = "the month's spend is unknown"
LOST = {"id": "place:lost:data:old-folder:old", "rule": "place", "node": None, "work": "an input no row makes"}
ROUGH = {"id": "place:rough-model", "rule": "place", "node": None, "work": "a rough-model stage"}
PROPS = {"id": "missing:crate_1", "rule": "missing", "node": None, "work": "prop data for hangar"}


def make_nothing(inputs, out, seed, params):
    raise AssertionError("nothing is made when the plan is worked out")


def row(name, after=(), paid=False, grain="place", euros=None, **more):
    return graph.Stage(name, grain, make_nothing, TEXT, SAID, after={before: READS for before in after}, paid=paid,
                       euros=euros, **more)


# In STAGES order on purpose out of the route's: the sort puts the shapes first, the order only breaks ties.
TABLE = [row("pixal", ("scene-record",), paid=True, euros=20.0),
         row("complete", ("pixal",)), row("demo-film", ("complete",), paid=True, euros=3.2),
         row("terrain", grain="world", paid=True, euros=6.0, files={"old": "{data}/old-folder"}),
         row("plan", ("terrain",)),
         row("rough-model", ("plan",), paid=True, euros=4.0), row("shell-split", ("rough-model",)),
         row("scene-record", ("shell-split",)), row("library", ("demo-film", "complete"))]
PER_UNIT = {"stages": {name: {"stage": name, "unit": "make", "count": {"one": True}, "also": [], "likely_euros": euros,
                              "high_euros": euros * 2, "runs": 3, "sources": {},
                              "forecast": {"rule": "one", "source": "one a place"}}
                       for name, euros in (("terrain", 5.0), ("rough-model", 1.0), ("pixal", 0.5))}}


@contextlib.contextmanager
def per_unit():
    kept = compute.PER_UNIT
    compute.PER_UNIT = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    compute.PER_UNIT.write_text(json.dumps(PER_UNIT))
    try:
        yield
    finally:
        compute.PER_UNIT = kept


def planned(findings=(ROUGH, LOST, PROPS), books=BOOKS):
    """The toy hangar's holes record, its milestones worked out; `books` why paid work is refused (None: it is not)."""
    data, root = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    for place, listed in (("hangar", list(findings)), (WORLD, [])):
        (root / place).mkdir()
        (root / place / "findings.json").write_text(json.dumps({"place": place, "outputs": {}, "findings": listed}))
    runner = graph.Runner(TABLE, graph.Environment("toy", 1, {"data": data}), Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {"kind": kind})
    kept = price.books_refused
    price.books_refused = lambda: books
    try:
        with per_unit():
            return price.holes_price(runner, "toy", root, ["hangar"], runner.store, made_at="2026-10-20T09:00:00Z")
    finally:
        price.books_refused = kept


def by_key(record):
    return {entry["key"]: entry for entry in record["milestones"]}


def test_the_milestones_go_shapes_first_and_end_with_the_owners_approval():
    record = planned()
    assert [entry["key"] for entry in record["milestones"]] == [
        "ground", "shapes", "split", "inside", "made", "complete", "after", "environment-film", "approval"]
    found = by_key(record)
    assert [entry["stage"] for entry in found["shapes"]["stages"]] == ["plan", "rough-model"]
    assert [entry["stage"] for entry in found["inside"]["stages"]] == ["scene-record"]
    assert [entry["stage"] for entry in found["after"]["stages"]] == ["demo-film", "library"]
    assert found["inside"]["reads"] == ["split"] and found["split"]["reads"] == ["shapes"]
    assert "no row of the stage table" in found["environment-film"]["unpriced"]
    assert found["approval"]["owner"] == [milestones.APPROVAL]


def test_every_node_comes_after_every_node_it_reads():
    record = planned()
    runner = graph.Runner(TABLE, graph.Environment("toy", 1, {"data": pathlib.Path(tempfile.mkdtemp())}),
                          Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {"kind": kind})
    edges = milestones.read_edges(runner, milestones.remake_nodes(record))
    order = milestones.ordered(runner, edges, milestones.steps_of(edges, set(runner.stages)))
    assert order[0] == "terrain" and order[-1] == "library@hangar", order
    for name, reads in edges.items():
        assert all(order.index(before) < order.index(name) for before in reads), name


def test_measured_euros_are_summed_and_an_unmeasured_node_is_unknown_with_its_set_budget_apart():
    found = by_key(planned())
    assert (found["ground"]["likely_euros"], found["ground"]["high_euros"]) == (5.0, 10.0)
    assert (found["shapes"]["likely_euros"], found["made"]["likely_euros"]) == (1.0, 0.5)
    after = found["after"]
    assert (after["likely_euros"], after["measured"], after["paid"]) == (0, 0, ["demo-film@hangar"])
    assert after["unknown"][0]["node"] == "demo-film@hangar" and "no run of demo-film" in after["unknown"][0]["why"]
    assert (after["set"]["euros"], after["set"]["nodes"]) == (3.2, 1)
    assert after["set"]["from"][0]["at"].startswith("score/stages/complete/holes/milestones_test.py:"), after["set"]


def test_the_code_work_waits_at_its_step_and_the_books_at_the_first_paid_one():
    found = by_key(planned())
    assert found["shapes"]["work"] == [{"work": "a rough-model stage", "holes": 1}]
    assert found["ground"]["work"] == [{"work": "an input no row makes", "holes": 1}]  # terrain reads it
    assert {"work": "prop data for hangar", "holes": 1} in found["made"]["work"]
    assert found["ground"]["owner"] == [f"the month's books before any paid step: {BOOKS}"]
    assert all(not entry["owner"] for key, entry in found.items() if key not in ("ground", "approval"))
    assert by_key(planned(books=None))["ground"]["owner"] == []


def test_a_node_of_a_table_of_its_own_is_what_the_place_holds_never_a_lines_end():
    found = by_key(planned(findings=[{"id": "missing:kit_1", "rule": "missing", "node": "ship_kit@hangar"}]))
    assert "ship_kit" in [entry["stage"] for entry in found["made"]["stages"]]
    assert "ship_kit" not in [entry["stage"] for entry in found["after"]["stages"]]


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[4] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
