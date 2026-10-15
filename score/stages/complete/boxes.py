"""complete-boxes@<place> (paid): the box gate's measure of the boxes no other row measures, so the completion gate's
`boxes` check has a verdict for every boxed row (2026-10-15: complete@quarters and complete@walkway answered unknown,
"not checked by SAM 3 or the judge on this box", on 10 and 8 rows).

The box gate (tools/props/scene/box_check.py `gate`) judges every inventory row that has a box: the box is where the
concept shows the row's thing, drawn round the partition's proposals, whether code or the prop route makes the row.
Its verdicts live in WORK/partition/<scene>/boxes.json, and only three things write them: box_check.py --masks by
hand (the old places' whole partitions), crops-boxes (crop rows) and machines-boxes (machine rows and rows flagged
`ground_box`, which the prop route draws). A ship place's code rows and the rows it takes from another place's take
were never boxed by any of them, so complete could not tell.

    make   machines-boxes' own make (SAM 3 on one rented card, the judge where SAM 3 does not ground) on every other
           boxed row, recorded where the box gate reads it; one make a view, as that make gives every job the
           picture of its first row's view (the cockpit's machine rows lie on four views: a fault of machines-boxes
           left for its own fix, which re-buys its accepted outputs)
    gate   grounded: every such row's box grounded by SAM 3 or passed by the judge (machines-boxes' gate)
"""
import json
import pathlib

from score import checks, contracts
import score.stages.machines.boxes as machine_boxes

REPO = pathlib.Path(__file__).resolve().parents[3]
# One rented card a view (machines-boxes' estimate); the ship's places box such rows on two views at most.
EUROS = 2 * machine_boxes.EUROS


def other_rows(inventory):
    """Every boxed row machines-boxes does not measure."""
    measured = {row["id"] for row in machine_boxes.machine_rows(inventory)}
    return [row for row in inventory["rows"] if row.get("box") and row["id"] not in measured]


def inventory_of(place):
    path = REPO / "data/inventory" / f"{place}.json"
    return json.loads(path.read_text()) if path.exists() else None


def has_rows(place):
    """True for a place whose inventory has boxed rows no other box row measures."""
    inventory = inventory_of(place)
    return inventory is not None and bool(other_rows(inventory))


def files(place):
    """The place's inventory, its views' pictures and the box tools."""
    inventory = inventory_of(place) or {"plan": {"views": []}}
    views = {f"view {view['id']}": view["picture"].replace("WORK/", "{seeds}/") for view in inventory["plan"]["views"]}
    return {"inventory": "{data}/inventory/" + f"{place}.json", **views, **machine_boxes.BOX_TOOLS}


def make_boxes(inputs, out, seed, params):
    """machines-boxes' make on the other boxed rows, view by view (a folder each), each row flagged as one it
    measures; every view's grounding and decisions gathered into the output's own."""
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text())
    rows = other_rows(inventory)
    found = {"grounding.json": {}, "decided.json": {}}
    for view in sorted({row["view"] for row in rows}):
        folder = out / view
        folder.mkdir()
        listing = folder / ".rows.json"
        listing.write_text(json.dumps(dict(inventory, rows=[dict(row, ground_box=True) for row in rows
                                                            if row["view"] == view])))
        try:
            machine_boxes.make_boxes(dict(inputs, inventory=listing), folder, seed, params)
        finally:
            listing.unlink()
        for name, gathered in found.items():
            gathered.update(json.loads((folder / name).read_text()))
    for name, gathered in found.items():
        (out / name).write_text(json.dumps(gathered, indent=1))


CONTRACT = contracts.Contract("complete-boxes", 1, machine_boxes.boxes_faults)
CHECKS = (checks.Check("grounded", machine_boxes.judge_grounded),)
