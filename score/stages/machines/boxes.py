"""machines-boxes@<place> (paid, experimental): the box gate's SAM 3 grounding for a place's machine rows (inventory
rows with `"machine": true` and a box), so the prop route may draw their close-ups (the close-up stage draws only a
box the box gate passes, tools/props/scene/box_check.py).

    make   box_check.mask_jobs on the machine rows only, SAM 3 on one rented card (box_masks_cloud.mask, as the
           concept_people row runs it), each row's grounding (box_check.grounding) in grounding.json; a grounded box
           is recorded where the box gate reads it (box_check.record_results: WORK/partition/<place>/boxes.json, the
           partition's own record, written by box_check.py --masks the same way). A box SAM 3 does not ground is not
           recorded: the judge's half (box_check.py --judge) is not run here.
    gate   grounded: every machine row's box is grounded by SAM 3.
"""
import json
import pathlib
import sys

from PIL import Image

from score import checks, contracts

REPO = pathlib.Path(__file__).resolve().parents[3]
# SAM 3 on one L4 for one picture: about 5 minutes and its set-up (concept_people's estimate for every view is 3).
EUROS = 1.0
BOX_TOOLS = {"box check": "{repo}/tools/props/scene/box_check.py", "box masks": "{repo}/tools/props/scene/box_masks.py",
             "box masks cloud": "{repo}/tools/props/cloud/box_masks_cloud.py"}


def box_tools():
    """box_check and box_masks_cloud, their folders on the path only while imported (props overlay's rule)."""
    import score.stages.props.prop_data as prop_data
    with prop_data.tools("props/scene", "props", "props/cloud"):
        import box_check
        import box_masks_cloud
    return box_check, box_masks_cloud


def machine_rows(inventory):
    return [row for row in inventory["rows"] if row.get("machine") and row.get("box")]


def applies(place):
    path = REPO / "data/inventory" / f"{place}.json"
    return path.exists() and bool(machine_rows(json.loads(path.read_text())))


def files(place):
    inventory = json.loads((REPO / "data/inventory" / f"{place}.json").read_text()) if applies(place) else None
    views = {f"view {view['id']}": view["picture"].replace("WORK/", "{seeds}/")
             for view in (inventory or {"plan": {"views": []}})["plan"]["views"]}
    return {"inventory": "{data}/inventory/" + f"{place}.json", **views, **BOX_TOOLS}


def make_boxes(inputs, out, seed, params):
    """SAM 3's instances of every machine row's words, each row's grounding, the grounded ones recorded."""
    box_check, box_masks_cloud = box_tools()
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text())
    scene = inventory["scene"]
    wanted = {"plan": inventory["plan"], "rows": machine_rows(inventory)}
    jobs = box_check.mask_jobs(scene, wanted, box_check.view_sizes(wanted))
    for job in jobs:  # the declared picture, not the work folder's path
        job["picture"] = str(inputs[f"view {next(row['view'] for row in wanted['rows'])}"])
    (out / "jobs.json").write_text(json.dumps(jobs, indent=1))
    box_masks_cloud.mask(out / "jobs.json", out / "masks.json")
    measured = json.loads((out / "masks.json").read_text())
    sizes = {row["key"]: Image.open(job["picture"]).size for job in jobs for row in job["rows"]}
    grounded = {key: box_check.grounding(instances, sizes[key]) for key, instances in measured.items()}
    (out / "grounding.json").write_text(json.dumps(grounded, indent=1))
    boxes = {row["key"]: list(row["box"]) for job in jobs for row in job["rows"]}
    box_check.record_results(box_check.decided(grounded, {}), boxes)


def boxes_faults(folder):
    return [] if (pathlib.Path(folder) / "grounding.json").exists() else ["no grounding.json"]


def judge_grounded(output, inputs, evidence):
    found = json.loads((pathlib.Path(output) / "grounding.json").read_text())
    failing = [f"{key}: {entry['grounding']}" + (f" (SAM 3's instance at {entry['found_at']})"
                                                  if "found_at" in entry else "")
               for key, entry in sorted(found.items()) if entry["grounding"] != "grounded"]
    return checks.Verdict("grounded", checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} of {len(found)} machine boxes not grounded" if failing
                          else f"all {len(found)} machine boxes grounded",
                          {"failing": len(failing)}, {"failing": "lower"}, tuple(failing))


CONTRACT = contracts.Contract("machines-boxes", 1, boxes_faults)
CHECKS = (checks.Check("grounded", judge_grounded),)
