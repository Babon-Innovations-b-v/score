"""A gap's chain is every node the gap's place still needs, priced from the stage table's reads: a node that stands is
left out and ends its branch, one whose key cannot be worked out (a missing input) is in it, and a later node is in it
up to the ends of the place's line (past its completion: the film that reads it), an optional read too. A toy table
in a store of its own:

    draw -> shape -> gap <- part (its input missing)
    gap -> finish -> complete -> film,  gap -> aside (an end too: nothing reads it)
    people (optional to complete, not made: Runner.reads leaves it out), alone (an end of its own)

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
         stage("gap", ("shape", "part"), paid=True), stage("finish", ("gap",), paid=True),
         stage("aside", ("gap",), paid=True), stage("people", paid=True),
         stage("complete", ("finish", "people"), optional=("people",)), stage("film", ("complete",), paid=True),
         stage("alone", paid=True)]


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
        return chain.gap_chain(runner, runner.stages[name], "hangar", chain.readers(runner, ["hangar"]))


def test_a_node_that_stands_is_left_out_and_one_that_cannot_be_keyed_is_in():
    found = chained(a_runner(), "gap")
    assert "shape@hangar" not in found and "draw@hangar" not in found, found
    assert found["part@hangar"] is True and found["gap@hangar"] is True


def test_a_later_node_is_in_up_to_the_lines_ends_past_the_completion():
    found = chained(a_runner(), "gap")
    assert found["finish@hangar"] is True and found["complete@hangar"] is False
    assert found["film@hangar"] is True and found["aside@hangar"] is True
    assert found["people@hangar"] is True, "an optional read is made in a remake"
    assert "alone@hangar" not in found, "an end that does not read the gap's node is the line's, not the gap's"
    assert sorted(found) == ["aside@hangar", "complete@hangar", "film@hangar", "finish@hangar", "gap@hangar",
                             "part@hangar", "people@hangar"]


def test_the_lines_chain_is_every_node_its_ends_still_need():
    runner = a_runner()
    with runner.still():
        reading = chain.readers(runner, ["hangar"])
        named = sorted(end.name for end, _ in chain.ends(runner, "hangar", reading))
        assert named == ["alone", "aside", "film"], named
        found = chain.line_chain(runner, "hangar", reading)
    assert set(found) == {"aside@hangar", "alone@hangar", "film@hangar", "complete@hangar", "finish@hangar",
                          "gap@hangar", "part@hangar", "people@hangar"}, found
    assert found["complete@hangar"] is False and found["alone@hangar"] is True


def test_a_node_that_does_not_stand_is_walked_through():
    runner = a_runner()
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")  # draw's key moves: nothing stands
    found = chained(runner, "gap")
    assert {"draw@hangar", "shape@hangar", "part@hangar"} <= set(found), found
    assert found["draw@hangar"] is False


def test_a_still_pass_walks_the_same_reads_and_the_next_pass_sees_a_change():
    runner = a_runner()
    unheld = {graph.node_name(stage, place): sorted(graph.node_name(*before) for before in runner.read_nodes(stage, place, every=True))
              for stage, place in runner.nodes(["hangar"])}
    with runner.still():
        held = {graph.node_name(stage, place): sorted(graph.node_name(*before) for before in runner.read_nodes(stage, place, every=True))
                for stage, place in runner.nodes(["hangar"])}
        files = runner.files_of(runner.stages["draw"], "hangar")
    assert held == unheld and files == {"brief": "{data}/{place}.txt"}
    assert "draw@hangar" not in chained(runner, "gap")
    (runner.world.roots["data"] / "hangar.txt").write_text("a bigger hall")  # a pass held nothing over to the next
    assert chained(runner, "gap")["draw@hangar"] is False


if __name__ == "__main__":
    import runpy
    runpy.run_path(str(pathlib.Path(__file__).resolve().parents[2] / "conftest.py"))["refuse_outside_sandbox"]()
    for name, test in list(globals().items()):
        if name.startswith("test_"):
            test()
            print("ok", name)
