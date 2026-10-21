"""The gaps priced by the runner: a node two gaps share is priced once with their models counted once, a later node
the place's completion reads is priced too, a gap no stage fills goes to the unfillable list with its work, the prop
route of rows waiting on their prop data is priced apart, and what cannot be priced (a node outside the table,
findings over an output no longer accepted, a place never checked) is named, never dropped. A toy table (pixal, its
bake, sound, likeness, complete) in a store of its own, with per-unit numbers and gaps written in the test; and
`score price --gaps` at the command, its record written whole. No cloud, no Blender.

Run: .venv/bin/python score/stages/complete/gaps/price_test.py
"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
from score.stages.complete.gaps import WORLD, price  # noqa: E402
from score.store import Store  # noqa: E402

compute.ledger().entries = lambda: []  # no measured runs: the per-unit numbers price
TEXT = contracts.Contract("toy-text", 1, lambda folder: [])
READS = ("toy-text", 1)
MADE_AT = "2026-10-19T20:00:00+00:00"


def make_nothing(inputs, out, seed, params):
    raise AssertionError("nothing is made when gaps are priced")


SAID = (checks.Check("said", lambda output, inputs, evidence: checks.Verdict("said", checks.PASS, "said")),)
TABLE = [graph.Stage("pixal", "place", make_nothing, TEXT, SAID, files={"brief": "{data}/{place}.txt"}, paid=True,
                     euros=20.0),
         graph.Stage("surfaces-bake", "place", make_nothing, TEXT, SAID, after={"pixal": READS}, paid=True,
                     euros=2.0),
         graph.Stage("sound", "place", make_nothing, TEXT, SAID, paid=True, euros=1.0),
         graph.Stage("likeness", "place", make_nothing, TEXT, SAID, after={"surfaces-bake": READS}),
         graph.Stage("complete", "place", make_nothing, TEXT, SAID,
                     after={"likeness": READS, "sound": READS})]
PER_UNIT = {"stages": {
    "pixal": {"stage": "pixal", "unit": "model", "count": {"json_keys": "takes.json"}, "also": [],
              "likely_euros": 0.2, "high_euros": 0.5, "runs": 50, "sources": {},
              "forecast": {"rule": "prop_takes", "source": "the place's models not made"}},
    "surfaces-bake": {"stage": "surfaces-bake", "unit": "bake job", "count": {"files": "made/*.gltf"}, "also": [],
                      "likely_euros": 0.04, "high_euros": 0.2, "runs": 200, "sources": {},
                      "forecast": {"rule": "models", "source": "the takes and the models pixal makes"}}}}
ROUTE_WORK = "prop data for square: data/props/square.json"
LINE_PAID = ("pixal@hangar", "sound@hangar", "surfaces-bake@hangar")  # the paid nodes of the hangar's whole line


def gap(number, node, work=None, row=None):
    return {"id": f"missing:crate_{number}", "rule": "missing", "node": node, "work": work, "row": row}


def written(root, place, findings, outputs=None):
    (root / place).mkdir(parents=True, exist_ok=True)
    (root / place / "findings.json").write_text(json.dumps({"place": place, "outputs": outputs or {},
                                                             "findings": findings}))


BODY = "a code body (tools/props/library/body_parts.py) and the row in data/kit/hangar.json"


def a_place(findings=None, props=None, outputs=None):
    """(runner, gaps root): the hangar's data (3 takes in its surface data, `props` its prop data when given) and its
    gaps: two missing rows pixal makes, one the sound fills, one no stage fills (or `findings`)."""
    data, root = pathlib.Path(tempfile.mkdtemp()), pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    (data / "surfaces").mkdir()
    (data / "surfaces/hangar.json").write_text(json.dumps({"takes": {"a": {}, "b": {}, "c": {}}}))
    if props is not None:
        (data / "props").mkdir()
        (data / "props/hangar.json").write_text(json.dumps({"place": "hangar", "objects": props}))
    written(root, "hangar", findings if findings is not None else [
        gap(1, "pixal@hangar", row="crate"), gap(2, "pixal@hangar", row="lamp"),
        {**gap(3, "sound@hangar"), "rule": "gate"}, gap(4, None, BODY)], outputs)
    runner = graph.Runner(TABLE, graph.Environment("toy", 1, {"data": data}), Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {"kind": kind})
    return runner, root


@contextlib.contextmanager
def per_unit(numbers=None):
    kept = compute.PER_UNIT
    compute.PER_UNIT = pathlib.Path(tempfile.mkdtemp()) / "per-unit.json"
    compute.PER_UNIT.write_text(json.dumps(numbers or PER_UNIT))
    try:
        yield
    finally:
        compute.PER_UNIT = kept


def priced(places=("hangar",), store=None, **made):
    with per_unit():
        runner, root = a_place(**made)
        return price.gaps_price(runner, "toy", root, list(places), store or runner.store, made_at=MADE_AT), root


class Accepted:
    """A store whose only accepted output is pixal@hangar's, its takes.json listing `takes` (an older make)."""

    def __init__(self, takes):
        self.takes = takes

    def accepted(self, node):
        return "older-make" if node == "pixal@hangar" else None

    def listing(self, output):
        return {"takes.json": "sha"}

    def read_file(self, output, name):
        return self.takes


def test_a_node_two_gaps_share_is_priced_once_with_their_models_counted_once():
    found, _ = priced()
    pixal = found["nodes"]["pixal@hangar"]
    assert (pixal["units"], pixal["basis"], pixal["likely_euros"], pixal["high_euros"]) == (
        2, "per unit × forecast", 0.4, 1.0), pixal
    bake = found["nodes"]["surfaces-bake@hangar"]
    assert (bake["units"], bake["basis"], bake["likely_euros"]) == (5, "per unit × forecast", 0.2), bake
    assert found["gaps"]["hangar"] == {"missing:crate_1": "pixal@hangar", "missing:crate_2": "pixal@hangar",
                                        "missing:crate_3": "sound@hangar"}
    assert found["chains"]["hangar"]["pixal@hangar"] == [  # complete reads the sound too: the place needs it
        "complete@hangar", "likeness@hangar", "pixal@hangar", "sound@hangar", "surfaces-bake@hangar"]
    assert found["free"] == ["complete@hangar", "likeness@hangar"]
    assert found["priced_on"]["per_unit_sha256"] and "uncommitted" in found["priced_on"]


def test_the_models_are_the_unmade_prop_takes_and_the_missing_rows_each_once():
    """The cairn is both a surface take and a missing row, and two gaps are two of one row: each model once."""
    props = {"cairn": {"route": "prop", "take": "a"}, "rock": {"route": "prop", "take": "rock-p1"},
             "pipe": {"route": "code", "take": None}}
    found, _ = priced(props=props, findings=[gap(1, "pixal@hangar", row="cairn"), gap(2, "pixal@hangar", row="crate"),
                                             gap(3, "pixal@hangar", row="crate")])
    assert found["nodes"]["pixal@hangar"]["units"] == 3  # a, rock-p1 (prop takes not made) and crate
    assert found["nodes"]["surfaces-bake@hangar"]["units"] == 5  # a, b, c, rock-p1, crate


def test_the_gaps_forecast_prices_before_the_units_an_older_accept_counted():
    """pixal@hangar's accepted make counted 3 takes; the gap asks for 5 models: 5 are priced."""
    found, _ = priced(store=Accepted({"x": 1, "y": 2, "z": 3}),
                      findings=[gap(number, "pixal@hangar", row=f"row{number}") for number in range(5)])
    pixal = found["nodes"]["pixal@hangar"]
    assert (pixal["units"], pixal["basis"], pixal["likely_euros"]) == (5, "per unit × forecast", 1.0), pixal


def test_a_stage_with_no_measured_unit_is_unknown_never_its_flat_estimate():
    """The sound's row says EUR 1.00, but no run of it is measured: unknown, out of the price, no guess kept."""
    found, _ = priced()
    sound = found["nodes"]["sound@hangar"]
    assert (sound["basis"], sound["likely_euros"], sound["high_euros"]) == ("not measured yet", None, None), sound
    assert not sound.get("guess_euros") and not sound.get("guess_from"), sound
    assert found["totals"] == {"likely_euros": 0.6, "high_euros": 2.0, "unpriced": ["sound@hangar"], "nodes": 3}, (
        found["totals"])


def test_a_stage_whose_model_makes_several_units_is_forecast_at_its_per_model():
    """The bake's rule counts 5 models; 2.5 units a model makes 12.5 units."""
    numbers = json.loads(json.dumps(PER_UNIT))
    numbers["stages"]["surfaces-bake"]["forecast"]["per_model"] = 2.5
    with per_unit(numbers):
        runner, root = a_place()
        found = price.gaps_price(runner, "toy", root, ["hangar"], runner.store, made_at=MADE_AT)
    bake = found["nodes"]["surfaces-bake@hangar"]
    assert (bake["units"], bake["likely_euros"]) == (12.5, 0.5), bake


def test_the_pixal_code_work_is_priced_at_pixals_unit_a_lost_take_a_model_and_other_code_work_is_not():
    """A rough model is no code work since its stage is in the table (score/stages/rough_model): its gap names its
    node, which the chain prices."""
    lost = "Pixal3D take lost: made again"
    with per_unit():
        runner, root = a_place(findings=[gap(1, None, BODY), gap(2, None, BODY),
                                         gap(3, None, lost), gap(4, None, lost), gap(5, None, lost)])
        written(root, "lab", [gap(6, None, BODY)])
        found = price.gaps_price(runner, "toy", root, ["hangar", "lab"], runner.store, made_at=MADE_AT)
    takes = found["code_work"][lost]
    assert set(found["code_work"]) == {lost} and (takes["gaps"], takes["models"]) == (3, 3)
    model = takes["nodes"]["pixal: the lost Pixal3D takes made again"]
    assert (model["basis"], model["units"], model["likely_euros"], model["high_euros"]) == (
        "per unit × forecast", 3, 0.6, 1.5), model


def test_the_record_carries_the_runners_eta_over_every_chain_row_in_table_order():
    """The ETA walks every row of the chains, paid and free; a row with no measured minutes is listed with why, so
    likely and high stay null and only the lower bound is given."""
    found, _ = priced()
    eta, every = found["eta"], {node for at in found["chains"].values() for nodes in at.values() for node in nodes}
    assert {row["node"] for row in eta["unknown"]} <= every and eta["path"], eta
    assert eta["unknown"] and eta["likely_minutes"] is None and eta["high_minutes"] is None, eta
    assert eta["at_least_minutes"] >= 0 and eta["jobs"] >= 1 and eta["run_cap"] >= 1, eta


def test_a_gap_no_stage_fills_goes_to_the_unfillable_list_with_its_work():
    found, _ = priced()
    assert found["unfillable"] == [{"work": BODY, "gaps": 1}]
    assert all(None not in nodes.values() for nodes in found["gaps"].values())


def test_findings_over_an_output_no_longer_accepted_are_not_current_and_price_nothing():
    found, _ = priced(outputs={"pixal@hangar": "an-output-no-longer-accepted"})
    assert found["not_current"] == ["hangar"]
    assert found["chains"] == {} and found["gaps"] == {}
    assert set(found["nodes"]) == set(LINE_PAID), "the line to the place's end is the table's, priced all the same"


def test_a_place_never_checked_and_a_node_outside_every_table_are_named_not_dropped():
    found, _ = priced(places=("hangar", "lab"), findings=[gap(1, "drone@hangar")])
    assert found["not_checked"] == ["lab", WORLD]  # the environment's own findings were never written either
    assert found["outside"] == [{"node": "drone@hangar", "gaps": 1}]
    assert set(found["nodes"]) == set(LINE_PAID) | {node.replace("hangar", "lab") for node in LINE_PAID}


def test_a_ship_kit_is_priced_on_its_own_table():
    """ship_kit@<place> is in no runner's table here but the ship kits' own: priced once on its row, however many
    gaps name it; with no measured run it is unknown."""
    found, _ = priced(findings=[gap(1, "ship_kit@hangar"), gap(2, "ship_kit@hangar")])
    assert found["outside"] == [] and found["chains"]["hangar"]["ship_kit@hangar"] == ["ship_kit@hangar"]
    kit = found["nodes"]["ship_kit@hangar"]
    assert (kit["basis"], kit["likely_euros"]) == ("not measured yet", None) and not kit.get("guess_euros"), kit
    assert "ship_kit@hangar" in found["totals"]["unpriced"] and found["gaps"]["hangar"] == {
        "missing:crate_1": "ship_kit@hangar", "missing:crate_2": "ship_kit@hangar"}


def test_rows_waiting_on_their_prop_data_get_the_prop_route_priced_after_that_work():
    """Three gaps of two rows at the square wait on its prop data: pixal and the bake per model (2), apart."""
    with per_unit():
        runner, root = a_place()
        written(root, "square", [gap(1, None, ROUTE_WORK, "crate"), gap(2, None, ROUTE_WORK, "crate"),
                                 gap(3, None, ROUTE_WORK, "lamp")])
        found = price.gaps_price(runner, "toy", root, ["hangar", "square"], runner.store, made_at=MADE_AT)
    square = found["after_work"]["square"]
    assert (square["work"], square["gaps"], square["models"], square["in_chains"]) == (ROUTE_WORK, 3, 2, [])
    assert {node: (entry["units"], entry["likely_euros"]) for node, entry in square["nodes"].items()} == {
        "pixal@square": (2, 0.4), "surfaces-bake@square": (2, 0.08)}
    assert {"work": ROUTE_WORK, "gaps": 3} in found["unfillable"]  # still code work, with no price of its own


def test_a_lost_input_several_places_read_counts_once():
    lost = {"id": "place:lost:earth-seed:usd-r3", "rule": "place", "node": None, "work": "earth seed lost"}
    with per_unit():
        runner, root = a_place(findings=[lost])
        written(root, "lab", [lost])
        written(root, WORLD, [lost])
        found = price.gaps_price(runner, "toy", root, ["hangar", "lab"], runner.store, made_at=MADE_AT)
    assert found["unfillable"] == [{"work": "earth seed lost", "gaps": 1}] and found["not_checked"] == []


def test_the_forecast_rules_one_and_unknown():
    with per_unit({"stages": {"sound": {"stage": "sound", "unit": "place", "count": {"one": True}, "also": [],
                                        "likely_euros": 0.5, "high_euros": 1.0, "runs": 3, "sources": {},
                                        "forecast": {"rule": "one", "source": "one a place"}},
                              "pixal": {**PER_UNIT["stages"]["pixal"], "forecast": {"rule": "made-up", "source": ""}}}}):
        assert price.forecast_units("sound@hangar", [], "/nowhere") == 1
        # a run's plan and its clearance count the same units, with no gaps check run there; no data root, none
        assert price.planned_units("sound@hangar", "/nowhere", None, root="/nowhere") == 1
        assert price.planned_units("sound@hangar", None, None) is None
        try:
            price.forecast_units("pixal@hangar", [], "/nowhere")
        except ValueError as error:
            assert "made-up" in str(error)
        else:
            raise AssertionError("an unknown forecast rule must be refused")


def test_score_price_gaps_writes_its_record_whole_and_says_it_in_one_line():
    import score.__main__ as cli
    import score.store
    record, root = priced()
    home, kept = pathlib.Path(tempfile.mkdtemp()), (cli.gaps_record, score.store.PROPS_HOME)
    cli.gaps_record, score.store.PROPS_HOME = (lambda world: record), home
    try:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            cli.main(["price", "world1", "--gaps", "--json"])
        said = json.loads(printed.getvalue())
        out = home / "work/checks/gaps-price/world1.json"
        assert json.loads(out.read_text()) == record and not list(out.parent.glob("*.partial"))
        assert (said["written"], said["gaps"], said["unfillable"], said["outside"]) == (str(out), 3, 1, 0), said
        assert said["not_current"] == [] and said["not_checked"] == [WORLD], said
        for argv in (["price", "world1"], ["price", "world1", "--gaps", "--node", "pixal@hangar"]):
            try:
                cli.main(argv)
            except SystemExit as stop:
                assert "give --node (repeat it) or --gaps" in str(stop.code), stop
            else:
                raise AssertionError(f"{argv} must exit with the usage line")
    finally:
        cli.gaps_record, score.store.PROPS_HOME = kept


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[4] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
