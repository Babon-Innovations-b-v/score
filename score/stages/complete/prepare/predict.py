"""Each take's predicted outcome before the batch, from a measured failure mode only (#21's batch contract): a group
whose shape every measured row of that shape failed on is a predicted hole and is not bought; any other is bought,
with its shape's measured close-up pass share beside it. No threshold is a guess at an outcome: the rates are counted
here from the hub's prop-route table (paper/evidence/compare-hub/table.json, 13 objects, 2026-10) against the hub
inventory's sizes, every time.

Shapes by size alone (groups.sides, each side over the longest): a rod has its middle side at most ROD of its
longest (a strut, a rib, a pipe), a sheet its shortest side at most SHEET (a mat, a panel), anything else is solid.
On the hub every rod failed the close-up's shape check (the Pro takes), and so did the one sheet; a shape with fewer
than MIN_MEASURED measured rows is `at risk`, never a predicted hole.
"""
import json
import pathlib

from score.stages.complete.prepare import groups

REPO = pathlib.Path(__file__).resolve().parents[4]
TABLE = REPO / "paper/evidence/compare-hub/table.json"
TABLE_PLACE = "hub"  # the table's objects are the hub's rows
ROD = 0.15
SHEET = 0.05
MIN_MEASURED = 3
CLOSEUP_FAILED = "fail: close-up"


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


def hub_rates(data):
    """measured() of the hub's table against the hub inventory's sizes under `data`."""
    rows = json.loads(TABLE.read_text())["rows"]
    inventory = json.loads((pathlib.Path(data) / "inventory" / f"{TABLE_PLACE}.json").read_text())
    return measured(rows, {row["id"]: row.get("size") for row in inventory["rows"]})


def predicted(size, rates):
    """{outcome, shape, pass_share, mode, measured} of a take of this size: `predicted hole` when every one of at
    least MIN_MEASURED measured rows of its shape failed the close-up, `at risk` when its shape has fewer measured
    rows and some failed, else `pass` (pass_share its shape's measured close-up pass share, None unmeasured)."""
    shape = shape_of(size)
    counted = rates.get(shape)
    if counted is None:
        return {"outcome": "pass", "shape": shape, "pass_share": None, "mode": None,
                "measured": f"no measured row of shape {shape}"}
    said = f"{counted['failed']} of {counted['of']} hub {shape}s failed the close-up ({TABLE.name})"
    share = round(1 - counted["failed"] / counted["of"], 3)
    if counted["failed"] == counted["of"] and counted["of"] >= MIN_MEASURED:
        return {"outcome": "predicted hole", "shape": shape, "pass_share": share,
                "mode": f"close-up: every Pro take of a {shape} failed the shape check", "measured": said}
    outcome = "at risk" if counted["failed"] and counted["of"] < MIN_MEASURED else "pass"
    return {"outcome": outcome, "shape": shape, "pass_share": share, "mode": None, "measured": said}
