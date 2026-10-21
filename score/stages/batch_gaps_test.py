"""Batch gaps (batch_gaps.py): a take whose paid step failed inside the batch is a gap carried down its place's line,
never a stop, and never a loosened gate. The Pixal3D row names the take its batch brought nothing back for, its gate
still fails it and the table moves that fault; the views leave the take out; a fixture line runs on to complete apart
from accepted gaps, which lists the gap with the batch run that decided it; a fault no batch gap names still stops.

Fault (#10, 2026-10-21): a failed close-up or Pixal3D job failed the next free gate, and the place's line waited for
the owner, though his yes to the batch had already decided that a failure is a gap.

Run: make tests TESTS=score/stages/batch_gaps_test.py (a sandbox PROPS_HOME: the takes are written under it)
"""
import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from score import checks, contracts, graph, review, stages  # noqa: E402
from score.stages import batch_gaps  # noqa: E402
from score.stages.surfaces import route_views  # noqa: E402
from score.store import Store  # noqa: E402
import score.stages.props.pixal_row as pixal_row  # noqa: E402

ROWS = {row.name: row for row in stages.STAGES}
OBJECTS = {"crate": {"route": "prop", "take": "crate-s1"},
           "hatch": {"route": "prop", "take": "hatch-s1", "rows": ["hatch"]}}


def written(folder, name, found):
    path = folder / name
    path.write_text(json.dumps(found))
    return path


def fake_batch(made):
    """subprocess.run as the Pixal3D batch would answer: only the takes in `made` come back (raw model and camera
    folder; the batch exits 0 and names the rest gaps), and the finish here writes the finished model."""
    def run(command, **options):
        pixal = pixal_row.take_files("any")[0].parent
        pixal.mkdir(parents=True, exist_ok=True)
        if command[1].endswith("batch.py"):
            for line in pathlib.Path(command[2]).read_text().splitlines():
                take = line.split()[0]
                if take in made:
                    (pixal / f"{take}.glb").write_text("raw")
                    (pixal / f"{take}.svviews").mkdir(exist_ok=True)
        else:
            take = command[3]
            (pixal / f"{take}-final.glb").write_text("finished")
        return subprocess.CompletedProcess(command, 0, "", "")
    return run


def pixal_made(made):
    """A Pixal3D row's output from a batch that brought back `made` only, and its inputs."""
    folder = pathlib.Path(tempfile.mkdtemp())
    (folder / "closeup" / "closeups").mkdir(parents=True)
    for row in OBJECTS:
        (folder / "closeup" / "closeups" / f"{row}.png").write_text("close-up")
    entries = {row: {"faces": 1000} for row in OBJECTS}
    inputs = {"closeup": folder / "closeup",
              "props": written(folder, "props.json", {"place": "toy", "objects": OBJECTS}),
              "surfaces": written(folder, "surfaces.json", {
                  "place": "toy", "takes": {entry["take"]: {} for entry in OBJECTS.values()},
                  "bake": {"models": {row: entry["take"] for row, entry in OBJECTS.items()}, "entries": entries}}),
              "inventory": written(folder, "inventory.json", {"rows": []})}
    out = folder / "pixal"
    out.mkdir()
    running, pixal_row.subprocess.run = pixal_row.subprocess.run, fake_batch(made)
    try:
        pixal_row.make_pixal(inputs, out, 0, {})
    finally:
        pixal_row.subprocess.run = running
    return out, inputs


def test_a_take_the_batch_made_no_model_of_is_a_gap_its_gate_still_fails_and_the_table_moves():
    out, inputs = pixal_made({"crate-s1"})
    found = batch_gaps.read([out])
    assert [entry["name"] for entry in found] == ["hatch: Pixal3D made no model"], found
    assert set(found[0]["objects"]) == {"hatch", "hatch-s1"} and found[0]["row"] == "pixal"
    assert found[0]["decided"] == f"the batch run (pixal, output {out.name})"
    gate = next(check for check in ROWS["pixal"].checks if check.name == "takes")
    raw = gate.judge.__wrapped__(out, inputs, None)
    assert raw.answer == checks.FAIL and all(finding.startswith("hatch: ") for finding in raw.findings), raw
    moved = gate.judge(out, inputs, None)
    assert moved.answer == checks.PASS and moved.findings == raw.findings, moved
    assert "moved to complete as accepted gaps: hatch: Pixal3D made no model (the batch run" in moved.reason


def test_a_fault_no_batch_gap_names_still_fails_the_gate():
    out, inputs = pixal_made({"crate-s1"})
    (pixal_row.take_files("crate-s1")[1]).write_text("changed since it was made")
    gate = next(check for check in ROWS["pixal"].checks if check.name == "takes")
    assert gate.judge(out, inputs, None).answer == checks.FAIL


def test_the_views_leave_a_batch_gap_s_take_out_and_carry_its_gap():
    out, inputs = pixal_made({"crate-s1"})
    views = out.parent / "views"
    views.mkdir()
    route_views.make_views({"surfaces": inputs["surfaces"], "pixal": out}, views, 0, {})
    assert list(json.loads((views / "views.json").read_text())) == ["crate-s1"]
    assert [entry["name"] for entry in batch_gaps.read([views])] == ["hatch: Pixal3D made no model"]


# The fixture batch: the prop route's rows by their table names, each a toy make, wrapped by the table's own gap
# mover (stages.accepted_gaps) as the real rows are.
TOY = contracts.Contract("toy", 1, lambda folder: [])


def make_pixal(inputs, out, seed, params):
    """Two takes asked; the batch brought the crate back and not the hatch (its job failed: a gap), unless the brief
    says it lost the crate too and named no gap for it."""
    brief = inputs["brief"].read_text()
    (out / "takes.json").write_text(json.dumps({"crate": "lost" not in brief, "hatch": False}))
    batch_gaps.write(out, [batch_gaps.gap("hatch: Pixal3D made no model", "pixal", "takes", ("hatch", "hatch-s1"),
                                          ["hatch: no hatch-s1.glb"], "the Pixal3D job ran once and failed")])


def judge_takes(output, inputs, evidence):
    takes = json.loads((output / "takes.json").read_text())
    failing = [f"{row}: no {row}-s1.glb" for row, made in sorted(takes.items()) if not made]
    return checks.Verdict("takes", checks.FAIL if failing else checks.PASS, f"{len(failing)} takes not made",
                          {"faults": len(failing)}, {"faults": "lower"}, tuple(failing))


def make_carried(inputs, out, seed, params):
    """A row after the take: works on the made takes, the batch gaps' left out and carried on."""
    batch_gaps.write(out, batch_gaps.of(inputs))
    (out / "made.json").write_text(json.dumps(["crate"]))


def judge_cast(output, inputs, evidence):
    """The views judge only the takes they worked on (the real row's: a left-out take is not in its views.json)."""
    return checks.Verdict("views cast", checks.PASS, f"{len(json.loads((output / 'made.json').read_text()))} cast")


def judge_rows(name):
    """A gate that fails each object of the place's two with no made model by name (as likeness and complete do)."""
    def judge(output, inputs, evidence):
        made = json.loads((output / "made.json").read_text())
        failing = [f"{row}: no model" for row in ("crate", "hatch") if row not in made]
        return checks.Verdict(name, checks.FAIL if failing else checks.PASS, f"{len(failing)} not made",
                              {"faults": len(failing)}, {"faults": "lower"}, tuple(failing))
    return judge


def fixture_line(brief):
    data = pathlib.Path(tempfile.mkdtemp())
    (data / "dock").mkdir()
    (data / "dock" / "brief.txt").write_text(brief)
    rows = (graph.Stage("pixal", "place", make_pixal, TOY, (checks.Check("takes", judge_takes),),
                        files={"brief": "{data}/{place}/brief.txt"}),
            graph.Stage("finish-route-views", "place", make_carried, TOY,
                        (checks.Check("views cast", judge_cast),), after={"pixal": ("toy", 1)}),
            graph.Stage("likeness", "place", make_carried, TOY, (checks.Check("outline", judge_rows("outline")),),
                        after={"finish-route-views": ("toy", 1)}),
            graph.Stage("complete", "place", make_carried, TOY, (checks.Check("rows", judge_rows("rows")),),
                        after={"likeness": ("toy", 1)}))
    world = graph.Environment("toy", 7, {"data": data})
    return graph.Runner(tuple(map(stages.accepted_gaps, rows)), world, Store.in_folder(tempfile.mkdtemp()),
                        model_record=lambda kind: {})


def test_a_failed_pixal_take_leaves_its_place_s_line_running_to_complete_apart_from_its_gaps():
    runner = fixture_line("the batch")
    found = runner.drive(["dock"], say=lambda line: None)
    for node in ("pixal@dock", "likeness@dock"):
        assert found[node] == "made: pass, accepted automatically", found
    assert found["complete@dock"].startswith("made: fail, accepted automatically"), found
    assert runner.status(["dock"])["complete@dock"] == "complete apart from accepted gaps (1), accepted"
    judgement = review.newest_judgement(runner.store, review.record_of(runner.store, "complete@dock"))
    listed = judgement["verdicts"][graph.GAPPED]
    assert "hatch: Pixal3D made no model (the Pixal3D job ran once and failed; the batch run (pixal, output" \
        in listed["reason"] and listed["findings"] == ["hatch: Pixal3D made no model: hatch: no hatch-s1.glb"]


def test_a_take_lost_with_no_batch_gap_still_stops_its_line():
    runner = fixture_line("the batch lost the crate")
    found = runner.drive(["dock"], say=lambda line: None)
    assert found["likeness@dock"] == "not run: its line stopped at pixal@dock", found
