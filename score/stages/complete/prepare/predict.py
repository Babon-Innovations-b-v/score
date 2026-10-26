"""Each take's predicted outcome before the batch, from a measured failure mode only (#21's batch contract): a group
whose shape every measured row of that shape failed on is a predicted gap, bought all the same and judged by the
real gates (a prediction never drops a row from the Buy, 2026-10-24); each with its shape's measured close-up pass
share beside it; a take this environment's own accepted outputs measured is predicted by that instead (`own_outcome`).
No threshold is a guess at an outcome: the rates are counted
here from the hub's prop-route table (paper/evidence/compare-hub/table.json, 13 objects, 2026-10) against those
objects' sizes as measured (sizes.json beside it, from the hub's inventory of then), every time.

Shapes by size alone (groups.sides, each side over the longest): a rod has its middle side at most ROD of its
longest (a strut, a rib, a pipe), a sheet its shortest side at most SHEET (a mat, a panel), anything else is solid.
On the hub every rod failed the close-up's shape check (the Pro takes), and so did the one sheet; a shape with fewer
than MIN_MEASURED measured rows is `at risk`, never a predicted gap. A row the close-up's failure no longer leaves a
gap is not predicted one: a thin straight row (score/stages/props/thin_straight.py, 2026-10-25) is built in code when
every close-up failed, so it is `at risk`, its code build's likeness on today's SAM 3 cut not measured yet.

A take measured here (`environment_measures`, `own_outcome`; 2026-10-26: 85 rows were `at risk` by the hub's 13
objects while Batch 1 try 4 had drawn and judged most of them): its place's accepted close-up output names its first
row at the object size it is asked at today (tools/props/closeup/stage.py object_size), under today's request (a row
that lies flat measured before FLAT_VIEW_SINCE was drawn at another view, one laid far off before FAR_CROP_SINCE from
the whole painting; a row every take failed before
LATER_TAKES_SINCE is asked anew, its next takes from the crop alone and upright). Its close-up passed: `pass`, unless the
accepted Pixal3D output's gaps say no model came back (`at risk`). Every Pro take failed: a code build the accepted
likeness output judged passes or is a `predicted gap`; one not judged yet is `at risk`; a row no route builds after is
a `predicted gap` (its next step draws new takes, judged by the real gate: bought all the same).
"""
import json
import pathlib

import score.stages.props.prop_data as prop_data
from score.stages.complete.prepare import groups
from score.stages.props import thin_straight

REPO = pathlib.Path(__file__).resolve().parents[4]
TABLE = REPO / "paper/evidence/compare-hub/table.json"
SIZES = TABLE.with_name("sizes.json")  # each table object's size as the hub's inventory gave it when it was measured
ROD = 0.15
SHEET = 0.05
MIN_MEASURED = 3
CLOSEUP_FAILED = "fail: close-up"
# When a close-up of a row that lies flat was first asked from straight above (tools/props/closeup b256f79c, commit
# time in UTC): a flat row's close-up accepted before it was drawn and judged at the three-quarter view.
FLAT_VIEW_SINCE = "2026-10-25T19:52:27+00:00"
# When a gap's later takes (past stage.PRO_TAKES, retry-4 on) were first asked from the crop alone and upright
# (tools/props/closeup/stage.py UPRIGHT, commit time in UTC): a row every take of which failed in a close-up accepted
# before is asked anew when its step is bought again, so its failures are not measured at today's request.
LATER_TAKES_SINCE = "2026-10-26T08:30:50+00:00"
# When a row laid far off (groups.far_made, `far`) was first asked from its crop alone, never the room (tools/props/
# closeup/stage.py pro_wording): its close-up accepted before was drawn from the whole painting.
FAR_CROP_SINCE = "2026-10-26T10:10:22+00:00"


def shape_of(size):
    """rod, sheet or solid by a size's sides; None for a size that is not three positive numbers."""
    found = groups.sides(size)
    if found is None:
        return None
    shortest, middle = found
    if middle <= ROD:
        return "rod"
    return "sheet" if shortest <= SHEET else "solid"


def measured(table_rows, sizes):
    """{shape: {"failed", "of", "objects"}} of the table's objects with a size (`sizes`, {object: size}): how many of
    each shape failed at the close-up (the route's first paid step)."""
    found = {}
    for row in table_rows:
        shape = shape_of(sizes.get(row["object"]))
        if shape is None:
            continue
        counted = found.setdefault(shape, {"failed": 0, "of": 0, "objects": []})
        counted["of"] += 1
        counted["objects"].append(row["object"])
        counted["failed"] += row["prop route"].startswith(CLOSEUP_FAILED)
    return found


def hub_rates():
    """measured() of the hub's table against its objects' sizes as measured (SIZES, beside the table)."""
    rows = json.loads(TABLE.read_text())["rows"]
    return measured(rows, json.loads(SIZES.read_text())["sizes"])


def predicted(size, rates, row=None):
    """{outcome, shape, pass_share, mode, measured} of a take of this size (its first inventory row `row`, by its
    name and noun): `predicted gap` when every one of at least MIN_MEASURED measured rows of its shape failed the
    close-up and no route builds it after (code_built), `at risk` when its shape has fewer measured rows and some
    failed, else `pass` (pass_share its shape's measured close-up pass share, None unmeasured)."""
    shape = shape_of(size)
    counted = rates.get(shape)
    if counted is None:
        return {"outcome": "pass", "shape": shape, "pass_share": None, "mode": None,
                "measured": f"no measured row of shape {shape}"}
    said = f"{counted['failed']} of {counted['of']} hub {shape}s failed the close-up ({TABLE.name})"
    share = round(1 - counted["failed"] / counted["of"], 3)
    if counted["failed"] == counted["of"] and counted["of"] >= MIN_MEASURED:
        if code_built(row, size):
            return {"outcome": "at risk", "shape": shape, "pass_share": None, "measured": said,
                    "mode": "close-up fails; built in code after (thin_straight), its likeness not measured yet"}
        return {"outcome": "predicted gap", "shape": shape, "pass_share": share,
                "mode": f"close-up: every Pro take of a {shape} failed the shape check", "measured": said}
    outcome = "at risk" if counted["failed"] and counted["of"] < MIN_MEASURED else "pass"
    return {"outcome": outcome, "shape": shape, "pass_share": share, "mode": None, "measured": said}


def code_built(row, size):
    """Whether a row whose close-up fails is built in code instead (thin_straight.thin_straight on its size)."""
    return row is not None and thin_straight.thin_straight({**row, "size": size})


def environment_measures(store, places):
    """{place: {at, closeups, unmade, built}} from each place's accepted outputs: the close-up row's objects
    (closeups.json, by a take's first row) and when it was accepted, the takes Pixal3D made no model of (its batch
    gaps), and {row: passed} of the code builds the likeness row judged (likeness.json `made` code; passed when no
    batch gap of it is carried)."""
    found = {}
    for place in places:
        standing = store.current_accept(f"closeup@{place}")
        if standing is None:
            continue
        found[place] = {"at": standing["at"],
                        "closeups": (store.read_file(standing["output"], "closeups.json") or {}).get("objects", {}),
                        "unmade": gap_objects(store, store.accepted(f"pixal@{place}"), "pixal"),
                        "built": code_builds(store, store.accepted(f"likeness@{place}"))}
    return found


def gap_objects(store, output, row):
    """The objects the output's batch gaps written by `row` name; none without an output."""
    gaps = (store.read_file(output, "batch-gaps.json") or {}).get("gaps", []) if output else []
    return {item for entry in gaps if entry["row"] == row for item in entry["objects"]}


def code_builds(store, output):
    """{row: passed} of the code builds a likeness output judged."""
    if output is None:
        return {}
    found = (store.read_file(output, "likeness.json") or {}).get("objects", {})
    gapped = {item for entry in (store.read_file(output, "batch-gaps.json") or {}).get("gaps", [])
              for item in entry["objects"]}
    return {row: row not in gapped for row, entry in found.items() if entry.get("made") == "code"}


def own_outcome(take, row, measures):
    """The take's outcome as this environment measured it (module docstring), or None when it is not measured at
    today's size and request; `row` its first inventory row, `measures` its place's environment_measures."""
    first = take["rows"][0]
    record = (measures or {}).get("closeups", {}).get(first)
    size = (row or {}).get("read_size") or take["size"]
    if record is None or not size or [float(side) for side in record.get("read_size") or record["size"]] != \
            [float(side) for side in size]:
        return None
    with prop_data.tools("props/closeup"):
        import check
    if check.lies_flat(size) and measures["at"] < FLAT_VIEW_SINCE:
        return None
    if (row or {}).get("far") and measures["at"] < FAR_CROP_SINCE:
        return None
    node = f"closeup@{take['place']}"
    outcome = {"shape": shape_of(take["size"]), "pass_share": None, "mode": None}
    if record["drawn_by"]:
        if {first, take["take"]} & measures["unmade"]:
            return {**outcome, "outcome": "at risk", "mode": f"Pixal3D made no model of it (pixal@{take['place']})",
                    "measured": f"its close-up passed ({node})"}
        return {**outcome, "outcome": "pass", "pass_share": 1.0, "measured": f"its close-up passed ({node})"}
    said = f"every one of its {len(record['takes'])} Pro takes failed the close-up ({node})"
    if first in measures["built"]:
        passed = measures["built"][first]
        return {**outcome, "outcome": "pass" if passed else "predicted gap", "measured": said,
                "mode": None if passed else f"its code build failed the likeness (likeness@{take['place']})"}
    if code_built(row, take["size"]):
        return {**outcome, "outcome": "at risk", "measured": said,
                "mode": "close-up failed; built in code after (thin_straight), its likeness not measured yet"}
    if measures["at"] < LATER_TAKES_SINCE:
        return None
    return {**outcome, "outcome": "predicted gap", "pass_share": 0.0, "measured": said,
            "mode": "close-up: every Pro take of it failed the shape check"}
