"""An optional read is made by the run that reads it: its node, and the line no place given owns that it reads (the
people's), are in the run and its price, and the reader waits on it, taking it once it stands and running without it
once it stops. A toy table: a look made on the people line, a dress row of the environment reading it beside, a cast
at each place reading the dress as optional.

Fault (Buy of 2026-10-24): no Buy held a people-* node, since the cast and characters layer read the dress rows only
as optional and an optional read not usable now was left out of the run's line; the people were never made.

Run: .venv/bin/python score/graph/optional_test.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.adapters import compute  # noqa: E402
compute.cloud_bill = lambda: 0.0  # no cloud: the provider's bill is never read here
compute.ledger().open_books_for_tests(tempfile.mkdtemp())
from score.graph import rebuy  # noqa: E402
from score.store import Store  # noqa: E402

PLACES = ("hangar", "station")


def text_faults(folder):
    return [] if any(folder.glob("*.txt")) else ["no text file"]


TEXT = contracts.Contract("toy-text", 1, text_faults)


def judge_made(output, inputs, evidence):
    return checks.Verdict("made", checks.PASS, "written")


def make_look(inputs, out, seed, params):
    if "explode" in inputs["brief"].read_text():
        raise RuntimeError("the look fell over")
    (out / "look.txt").write_text(inputs["brief"].read_text())


def make_dress(inputs, out, seed, params):
    (out / "dress.txt").write_text((inputs["look@people"] / "look.txt").read_text())


def make_cast(inputs, out, seed, params):
    (out / "cast.txt").write_text("dressed" if "dress" in inputs else "undressed")


def a_runner(brief):
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "people").mkdir()
    (data / "people" / "brief.txt").write_text(brief)
    made = (checks.Check("made", judge_made),)
    look = graph.Stage("look", "place", make_look, TEXT, made, files={"brief": "{data}/{place}/brief.txt"},
                       applies=lambda place: place == "people")
    dress = graph.Stage("dress", "world", make_dress, TEXT, made, paid=True, euros=0.0, beside={"look": ("toy-text", 1)},
                        neighbours=lambda place: ["people"])
    cast = graph.Stage("cast", "place", make_cast, TEXT, made, after={"dress": ("toy-text", 1)}, optional=("dress",),
                       applies=lambda place: place != "people")
    return graph.Runner((look, dress, cast), graph.Environment("toy", 7, {"data": data}),
                        Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {"kind": kind})


def quiet(line):
    pass


def cast_of(runner, place):
    return (runner.store.checkout(runner.store.accepted(f"cast@{place}")) / "cast.txt").read_text()


def test_the_run_holds_and_prices_the_optional_read_and_the_line_it_reads():
    runner = a_runner("a suit")
    for whole in (True, False):
        names = {graph.node_name(*node) for node in runner.line_nodes(PLACES, whole)}
        assert {"look@people", "dress", "cast@hangar", "cast@station"} <= names, (whole, names)
    assert [buy.node for buy in rebuy.buys(runner, runner.line_nodes(PLACES, False))] == ["dress"]


def test_the_reader_waits_on_its_optional_read_and_takes_it():
    runner = a_runner("a suit")
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert found["dress"].startswith("made: pass"), found
    assert cast_of(runner, "hangar") == cast_of(runner, "station") == "dressed", found


def test_the_reader_runs_without_an_optional_read_that_stopped():
    runner = a_runner("explode")
    found = runner.drive(PLACES, say=quiet, whole=False)
    assert found["dress"] == "not run: its line stopped at look@people", found
    assert cast_of(runner, "hangar") == "undressed", found


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
