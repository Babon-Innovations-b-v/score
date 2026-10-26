"""straight-masks@<place>: the SAM 3 mask of every thin straight object of the place's prop data (thin_straight.py:
built in code once its close-ups fail) on its concept, made on one rented card before its close-ups are judged, so
its code build can be held free to the likeness row's checks ahead of a Buy (score/stages/complete/prepare/predict.py
straight_outcome). The masks and cuts are thin_straight's own (concept_masks, cut_by_mask), as the Pixal3D row makes
them when it builds such a row; that row makes its own, so no row reads this one. Its row (STAGE) is added to the
table by score/stages/__init__.py after every other, never in the prop route's table (score/stages/props/__init__.py,
shapes_first), whose modules most rows' code versions hash: added there it re-keyed 75 paid rows (2026-10-26).

Its output: `masks.json` ({"asked": the rows asked, "cut": the rows with a cut}), `cuts/<row>.png` (the row's concept
crop cut out by its mask: the build's input.png) and `masks/` (box_masks_cloud.py's jobs, instances and masks). A
row SAM 3 found nothing of has no cut: the Pixal3D row would leave it a gap.
"""
import json

from score import checks, contracts, graph
import score.stages.props.prop_data as prop_data
import score.stages.props.thin_straight as thin_straight
from score.stages.surfaces.surface_gates import guarded

# One SAM 3 card for a place's rows, as the crops' concept row prices its own (score/stages/crops/concept.py EUROS).
EUROS = 0.5


def files(place):
    """The place's hand-in, its inventory, its concept views and the tools that mask and crop."""
    return {"props": prop_data.keyed(place), "inventory": prop_data.inventory_pattern(place),
            **prop_data.view_files(place), **thin_straight.TOOLS}


def asked(record, rows, params):
    """{row: inventory row} of the prop objects the object filter keeps that are thin and straight with a box."""
    return {row: rows[row] for row in sorted(prop_data.kept(prop_data.prop_objects(record), params))
            if row in rows and rows[row].get("box") and thin_straight.thin_straight(rows[row])}


def make_masks(inputs, out, seed, params):
    """masks.json and each asked row's cut (module docstring)."""
    rows = {row["id"]: row for row in json.loads(inputs["inventory"].read_text())["rows"]}
    thin = asked(prop_data.record_at(inputs["props"]), rows, params)
    concepts = {row: inputs[f"view {entry['view']}"] for row, entry in thin.items()}
    masks = thin_straight.concept_masks(thin, concepts, out / "masks") if thin else {}
    (out / "cuts").mkdir()
    cut = []
    for row, mask in sorted(masks.items()):
        picture = thin_straight.cut_by_mask(concepts[row], thin[row]["box"], mask)
        if picture is not None:
            picture.save(out / "cuts" / f"{row}.png")
            cut.append(row)
    (out / "masks.json").write_text(json.dumps({"asked": sorted(thin), "cut": cut}, indent=1))


def masks_faults(folder):
    return [] if (folder / "masks.json").exists() else ["no masks.json"]


def judge_masks(output, inputs, evidence):
    """Pass, counting the rows cut: a row SAM 3 found nothing of is a measured outcome (no build), not a fault."""
    found = json.loads((output / "masks.json").read_text())
    missed = sorted(set(found["asked"]) - set(found["cut"]))
    return checks.Verdict("masks", checks.PASS, f"{len(found['cut'])} of {len(found['asked'])} rows cut",
                          {"asked": len(found["asked"]), "cut": len(found["cut"])}, {},
                          tuple(f"{row}: SAM 3 found nothing in its box" for row in missed[:40]))


STAGE = graph.Stage("straight-masks", "place", make_masks, contracts.Contract("straight-masks", 1, masks_faults),
                    (guarded("masks", judge_masks),), files=files, paid=True, euros=EUROS, applies=prop_data.applies,
                    selects=True)
