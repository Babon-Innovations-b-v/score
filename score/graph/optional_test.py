"""An optional read is made by the run that reads it: its node, and the line no place given owns that it reads (the
people's), are in the run and its price, and the reader waits on it, taking it once it stands and running without it
once it stops. A toy table: a look made on the people line, a dress row of the environment reading it beside, a cast
at each place reading the dress as optional.

Fault (Buy of 2026-10-24): no Buy held a people-* node, since the cast and characters layer read the dress rows only
as optional and an optional read not usable now was left out of the run's line; the people were never made.

Run: .venv/bin/python score/graph/optional_test.py
"""
import os
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


def test_a_shared_line_is_held_for_each_place_that_reads_it():
    """The people line's nodes name every place whose cast reads them (the Buy buys them with those places, Buy of
    2026-10-24); a place's own node names that place alone."""
    runner = a_runner("a suit")
    held = rebuy.held_for(runner, runner.line_nodes(PLACES, True), set(PLACES))
    assert held["dress"] == held["look@people"] == set(PLACES), held
    assert held["cast@hangar"] == {"hangar"}, held


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


def test_a_pass_of_the_drive_works_out_each_key_once():
    """Batch 1 (2026-10-25): each pass of the drive worked out its waiting nodes' optional reads' keys outside a
    `still` pass, once a path through every node they read; its passes took 12 min and then over an hour, the run never
    ended and its pool's machines billed. A ladder (each rung reads the two below) read as optional by a top row: in
    the drive's own process no key is worked out outside a pass, nor twice in one."""
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar").mkdir()
    (data / "hangar" / "brief.txt").write_text("a rung")
    made = (checks.Check("made", judge_made),)
    rungs = [graph.Stage("rung0", "place", make_look, TEXT, made, files={"brief": "{data}/{place}/brief.txt"})]
    for number in range(1, 12):
        after = {f"rung{below}": ("toy-text", 1) for below in (number - 1, number - 2) if below >= 0}
        rungs.append(graph.Stage(f"rung{number}", "place", make_rung, TEXT, made, after=after))
    top = graph.Stage("top", "place", make_cast, TEXT, made, after={"rung11": ("toy-text", 1)}, optional=("rung11",))
    runner = graph.Runner((*rungs, top), graph.Environment("toy", 7, {"data": data}),
                          Store.in_folder(tempfile.mkdtemp()), model_record=lambda kind: {"kind": kind})
    drive_pid, worked, passes = os.getpid(), [], []
    work = runner.worked_out_key

    def counted(stage, place):
        if os.getpid() == drive_pid:
            if runner.remembered is not None and not any(seen is runner.remembered for seen in passes):
                passes.append(runner.remembered)
            worked.append((len(passes) if runner.remembered is not None else None, graph.node_name(stage, place)))
        return work(stage, place)
    runner.worked_out_key = counted
    available, graph.AVAILABLE = graph.AVAILABLE, lambda: 2**50  # the rungs start one after another, none held
    try:
        found = runner.drive(("hangar",), say=quiet, whole=False)
    finally:
        graph.AVAILABLE = available
    assert found["top@hangar"].startswith("made: pass"), found
    assert None not in {each for each, _ in worked}, worked
    assert len(worked) == len(set(worked)), sorted(worked)


def make_rung(inputs, out, seed, params):
    (out / "rung.txt").write_text(str(len(inputs)))


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
