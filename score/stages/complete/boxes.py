"""complete-boxes@<place> (paid): the box gate's measure of the boxes no other row measures, so the completion gate's
`boxes` check has a verdict for every boxed row (2026-10-15: complete@quarters and complete@walkway answered unknown,
"not checked by SAM 3 or the judge on this box", on 10 and 8 rows).

The box gate (tools/props/scene/box_check.py `gate`) judges every inventory row that has a box: the box is where the
concept shows the row's thing, drawn round the partition's proposals, whether code or the prop route makes the row.
Its verdicts live in WORK/partition/<scene>/boxes.json, and only three things write them: box_check.py --masks by
hand (the old places' whole partitions), crops-boxes (crop rows) and motion-models-boxes (rows flagged
`ground_box`, which the prop route draws). A ship place's code rows and the rows it takes from another place's take
were never boxed by any of them, so complete could not tell. A designed place has none: its reading boxed every row on
its locked concept.

    make   motion-models-boxes' own make (SAM 3 on one rented card, the judge where SAM 3 does not ground) on every other
           boxed row, recorded where the box gate reads it
    gate   grounded: every such row's box grounded by SAM 3 or passed by the judge (motion-models-boxes' gate)
"""
import json
import pathlib

from score import checks, contracts
import score.stages.motion.models.boxes as model_boxes

REPO = pathlib.Path(__file__).resolve().parents[3]
EUROS = model_boxes.EUROS


def other_rows(inventory):
    """Every boxed row motion-models-boxes does not measure."""
    measured = {row["id"] for row in model_boxes.boxed_rows(inventory)}
    return [row for row in inventory["rows"] if row.get("box") and row["id"] not in measured]


def inventory_of(place):
    path = REPO / "data/inventory" / f"{place}.json"
    return json.loads(path.read_text()) if path.exists() else None


def has_rows(place):
    """True for a place whose old inventory has boxed rows no other box row measures; never a designed place, whose
    every box is its reading's of its locked concept (SAM 3's, else Gemini's region, in its hand-in:
    complete/prepare/handin.py), so its old inventory's views (lost pictures of an older concept) are read by nothing."""
    import score.stages.props.prop_data as prop_data
    inventory = inventory_of(place)
    return not prop_data.designed(place) and inventory is not None and bool(other_rows(inventory))


def files(place):
    """The place's inventory, its views' pictures and the box tools (no views for a place it has no rows for)."""
    inventory = (inventory_of(place) if has_rows(place) else None) or {"plan": {"views": []}}
    views = {f"view {view['id']}": view["picture"].replace("WORK/", "{seeds}/") for view in inventory["plan"]["views"]}
    return {"inventory": "{data}/inventory/" + f"{place}.json", **views, **model_boxes.BOX_TOOLS}


def make_boxes(inputs, out, seed, params):
    """motion-models-boxes' make on the other boxed rows, each flagged as a row it measures (the inventory it reads is
    written beside the output's files and removed after)."""
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text())
    wanted = {row["id"] for row in other_rows(inventory)}
    listing = out / ".rows.json"
    listing.write_text(json.dumps(dict(inventory, rows=[dict(row, ground_box=True) for row in inventory["rows"]
                                                        if row["id"] in wanted])))
    try:
        model_boxes.make_boxes(dict(inputs, inventory=listing), out, seed, params)
    finally:
        listing.unlink()


CONTRACT = contracts.Contract("complete-boxes", 1, model_boxes.boxes_faults)
CHECKS = (checks.Check("grounded", model_boxes.judge_grounded),)
