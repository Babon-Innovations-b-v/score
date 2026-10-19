"""A hole's chain is every node the hole's place still needs, priced from the stage table's reads: a node that stands is
left out and ends its branch, one whose key cannot be worked out (a missing input) is in it, and a later node is in it
only when the place's completion reads it. A toy table in a store of its own:

    draw -> shape -> hole <- part (its input missing)
    hole -> finish -> complete,  hole -> aside (complete does not read it)

Run: .venv/bin/python score/graph/chain_test.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from score import checks, contracts, graph  # noqa: E402
from score.graph import chain  # noqa: E402
from score.store import Store  # noqa: E402

TEXT = contracts.Contract("toy-text", 1, lambda folder: [])


def make_copy(inputs, out, seed, params):
    source = next(iter(inputs.values()))
    found = source if source.is_file() else next(source.glob("*.txt"))
    (out / "text.txt").write_text(found.read_text())


def judge_said(output, inputs, evidence):
    return checks.Verdict("said", checks.PASS, "a text was written")


SAID = (checks.Check("said", judge_said),)
READS = ("toy-text", 1)


def stage(name, after=(), paid=False, **more):
    return graph.Stage(name, "place", make_copy, TEXT, SAID, after={before: READS for before in after}, paid=paid,
                       euros=1.0 if paid else None, **more)


TABLE = [stage("draw", files={"brief": "{data}/{place}.txt"}), stage("shape", ("draw",)),
         stage("part", paid=True, files={"brief": "{data}/{place}-part.txt"}),
         stage("hole", ("shape", "part"), paid=True), stage("finish", ("hole",), paid=True),
         stage("aside", ("hole",), paid=True), stage("complete", ("finish",))]


def a_runner():
    """The toy table with draw and shape made and standing at the hangar; part's input is missing."""
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "hangar.txt").write_text("a hall")
    runner = graph.Runner(TABLE, graph.Environment("toy", 1, {"data": data}), Store.in_folder(tempfile.mkdtemp()),
                          model_record=lambda kind: {"kind": kind})
    for name in ("draw", "shape"):
        assert "accepted automatically" in runner.run_node(runner.stages[name], "hangar"), name
    return runner


def chained(runner, name):
    with runner.still():
        return chain.hole_chain(runner, runner.stages[name], "hangar", chain.readers(runner, ["hangar"]))


def test_a_node_that_stands_is_left_out_and_one_that_cannot_be_keyed_is_in():
    found = chained(a_runner(), "hole")
    assert "shape@hangar" not in found and "draw@hangar" not in found, found
    assert found["part@hangar"] is True and found["hole@hangar"] is True


def test_a_later_node_is_in_only_when_the_completion_reads_it():
    found = chained(a_runner(), "hole")
    assert found["finish@hangar"] is True and found["complete@hangar"] is False
    assert "aside@hangar" not in found
    assert sorted(found) == ["complete@hangar", "finish@hangar", "hole@hangar", "part@hangar"]


def test_a_node_that_does_not_stand_is_walked_through():
    runner = a_runner()
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")  # draw's key moves: nothing stands
    found = chained(runner, "hole")
    assert {"draw@hangar", "shape@hangar", "part@hangar"} <= set(found), found
    assert found["draw@hangar"] is False


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
