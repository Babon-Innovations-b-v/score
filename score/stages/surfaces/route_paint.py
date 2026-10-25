"""The finish route's paint, `surfaces-paint` (free, here, after the bake): the paint runs in the bake's job on the
rented card (route_bake.py, #18, 2026-10-20: this PC's 14 GB cap failed heavy takes, crane-r1 peaked at 34.8 GB), so
this row takes the bake's painted takes over as its own output, which every reader of the paint reads (the check, the
assembly, the machines, the prop makers), and holds its gates: one surface a part, colour against the close-up (a
accepted gap's gate) and, set in the table, feet in one plane. The parts row's "off colour" measure names the colour
faults before the bake; the gates fail them here, after it.

A take a gate fails is a batch gap (the batch rule, owner 2026-10-20: its paint and bake ran once in the batch), named
in this output's batch-gaps.json with the gaps its inputs carry: the gate still fails it, the table moves the fault
(stages.BATCH_GATES) and complete fails it by name, so one off-colour finish no longer stops the place's line. A take
stays painted and in the place. `item_gaps` does the same for the check's models (route_check.py).

Output as the rented paint's: painted.json (with the takes the parts left out), labelled/<take>/, and batch-gaps.json
where a gap is named or carried.
"""
import json
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.append(str(HERE))

from surface_gates import guarded  # noqa: E402

ROW = "surfaces-paint"


def make_paint(inputs, out, seed, params):
    """The bake's painted takes as this output, each take a gate fails named a batch gap."""
    copy_paint(inputs, out)
    write_gaps(inputs, out, ROW, paint_gates(), "painted.json", lambda found: {"takes": found},
               json.loads((out / "painted.json").read_text())["takes"], lambda take: (take,),
               "the take's paint and bake ran once in the batch and failed this gate")


def copy_paint(inputs, out):
    """The bake's painted.json and labelled folders copied into `out` (as plain files: the input's checkout is
    read-only)."""
    baked = pathlib.Path(inputs["surfaces-bake"])
    for path in [baked / "painted.json", *(baked / "labelled").rglob("*")]:
        if path.is_file():
            target = out / path.relative_to(baked)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def paint_gates():
    """Every gate the row holds, guarded as the row's, the table's feet check among them (stages.feet_checked)."""
    import place_line
    return tuple(guarded(name, judge) for name, judge in (
        ("one surface a part", place_line.judge_one_surface),
        ("colour against the close-up", place_line.judge_concept_colour),
        ("feet in one plane", place_line.judge_feet)))


def item_findings(judge, filename, wrap, items, inputs):
    """{item: its findings} of each item `judge` fails, run on it alone (a one-item `filename`, in the form `wrap`
    gives, in a scratch folder), so no item's faults are cut by the gate's cap on findings."""
    from score import checks
    found = {}
    with tempfile.TemporaryDirectory() as scratch:
        folder = pathlib.Path(scratch)
        for item, record in items.items():
            (folder / filename).write_text(json.dumps(wrap({item: record})))
            verdict = judge(folder, inputs, {})
            if verdict.answer == checks.FAIL and verdict.findings:
                found[item] = list(verdict.findings)
    return found


def item_gaps(row, gates, filename, wrap, items, inputs, objects, reason):
    """A batch gap for each item (take or model) a gate (a check) of the row fails, its objects `objects(item)`; an
    item a gate cannot tell is no gap (the gate answers unknown and blocks)."""
    import score.stages.batch_gaps as batch_gaps
    return [batch_gaps.gap(f"{item}: {gate.name}", row, gate.name, objects(item), findings, reason)
            for gate in gates
            for item, findings in item_findings(gate.judge, filename, wrap, items, inputs).items()]


def write_gaps(inputs, out, row, gates, filename, wrap, items, objects, reason):
    """batch-gaps.json in `out`: the gaps the inputs carry and each item_gaps names; none written when there is none
    (a clean output stays as it was)."""
    import score.stages.batch_gaps as batch_gaps
    found = [*batch_gaps.of(inputs), *item_gaps(row, gates, filename, wrap, items, inputs, objects, reason)]
    if found:
        batch_gaps.write(out, found)
