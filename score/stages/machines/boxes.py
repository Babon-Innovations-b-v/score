"""machines-boxes@<place> (paid, experimental): the box gate's SAM 3 grounding for a place's machine rows (inventory
rows with `"machine": true` and a box) and the rows added after its partition's own run that name `"ground_box":
true` (the airlock's suit), so the prop route may draw their close-ups (the close-up stage draws only a
box the box gate passes, tools/props/scene/box_check.py).

    make   box_check.mask_jobs on the machine rows only, SAM 3 on one rented card (box_masks_cloud.mask, as the
           concept_people row runs it), each row's grounding (box_check.grounding) in grounding.json; a grounded box
           is recorded where the box gate reads it (box_check.record_results: WORK/partition/<place>/boxes.json, the
           partition's own record, written by box_check.py --masks the same way). A box SAM 3 does not ground, and
           every row flagged `"ground_box": "judge"` (one SAM 3 finds under no word), goes to the box judge
           (box_check.judge_jobs, asked of Gemini through tools/props/cloud/gemini_judge.py, cents an ask: two seeds,
           a third where they split), and its verdict is recorded the same way.
    gate   grounded: every row's box is grounded by SAM 3 or passed by the judge.
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
             "box masks cloud": "{repo}/tools/props/cloud/box_masks_cloud.py",
             "gemini judge": "{repo}/tools/props/cloud/gemini_judge.py"}


def box_tools():
    """box_check and box_masks_cloud, their folders on the path only while imported (props overlay's rule)."""
    import score.stages.props.prop_data as prop_data
    with prop_data.tools("props/scene", "props", "props/cloud"):
        import box_check
        import box_masks_cloud
    return box_check, box_masks_cloud


def machine_rows(inventory):
    """Every row this stage checks: a machine row, or one flagged `ground_box` (true: SAM 3 first; "judge": the judge
    alone)."""
    return [row for row in inventory["rows"] if (row.get("machine") or row.get("ground_box")) and row.get("box")]


def sam_rows(inventory):
    return [row for row in machine_rows(inventory) if row.get("ground_box") != "judge"]


def judged(box_check, scene, inventory, rows, folder):
    """The box judge's verdicts on rows' boxes ({`<scene>.<row>.<box>`: verdict}), asked of Gemini (two seeds, the
    third where they split), its questions, pictures and answers under `folder`."""
    import score.stages.props.prop_data as prop_data
    wanted = {"plan": inventory["plan"], "rows": rows}
    jobs = [dict(job, answer="box") for job in
            box_check.judge_jobs(scene, wanted, box_check.view_sizes(wanted), folder, box_check.SEEDS[:2])]
    answers = folder / "answers"
    with prop_data.tools("props/cloud", "props"):  # gemini_judge reads its key's store when it asks
        import gemini_judge
        for number, listed in ((1, jobs), (2, None)):
            listed = listed if listed is not None else box_check.deciding_jobs(jobs, answers)
            if listed:
                (folder / f"questions-{number}.json").write_text(json.dumps(listed, indent=1))
                gemini_judge.ask(folder / f"questions-{number}.json", answers)
    return box_check.verdicts(jobs, answers)


def applies(place):
    path = REPO / "data/inventory" / f"{place}.json"
    return path.exists() and bool(machine_rows(json.loads(path.read_text())))


def files(place):
    inventory = json.loads((REPO / "data/inventory" / f"{place}.json").read_text()) if applies(place) else None
    views = {f"view {view['id']}": view["picture"].replace("WORK/", "{seeds}/")
             for view in (inventory or {"plan": {"views": []}})["plan"]["views"]}
    return {"inventory": "{data}/inventory/" + f"{place}.json", **views, **BOX_TOOLS}


def make_boxes(inputs, out, seed, params):
    """SAM 3's instances of every SAM row's words and each one's grounding; the judge's verdict on every other row;
    each decided box recorded where the box gate reads it (decided.json beside)."""
    box_check, box_masks_cloud = box_tools()
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text())
    scene = inventory["scene"]
    grounded = {}
    wanted = {"plan": inventory["plan"], "rows": sam_rows(inventory)}
    if wanted["rows"]:
        jobs = box_check.mask_jobs(scene, wanted, box_check.view_sizes(wanted))
        for job in jobs:  # the declared picture, not the work folder's path
            job["picture"] = str(inputs[f"view {next(row['view'] for row in wanted['rows'])}"])
        (out / "jobs.json").write_text(json.dumps(jobs, indent=1))
        box_masks_cloud.mask(out / "jobs.json", out / "masks.json")
        measured = json.loads((out / "masks.json").read_text())
        sizes = {row["key"]: Image.open(job["picture"]).size for job in jobs for row in job["rows"]}
        grounded = {key: box_check.grounding(instances, sizes[key]) for key, instances in measured.items()}
    (out / "grounding.json").write_text(json.dumps(grounded, indent=1))
    rows = machine_rows(inventory)
    left = [row for row in rows if grounded.get(f"{scene}.{row['id']}", {}).get("grounding") != "grounded"]
    verdicts = judged(box_check, scene, inventory, left, out / "judge") if left else {}
    (out / "judged.json").write_text(json.dumps(verdicts, indent=1))
    decided = box_check.decided({**{f"{scene}.{row['id']}": {"grounding": "not found"} for row in rows}, **grounded},
                                verdicts)
    (out / "decided.json").write_text(json.dumps(decided, indent=1))
    box_check.record_results(decided, {f"{scene}.{row['id']}": list(row["box"]) for row in rows})


def boxes_faults(folder):
    return [f"no {name}" for name in ("grounding.json", "decided.json") if not (pathlib.Path(folder) / name).exists()]


def judge_grounded(output, inputs, evidence):
    """Fail on a row whose box neither SAM 3 grounded nor the judge passed, naming why."""
    found = json.loads((pathlib.Path(output) / "decided.json").read_text())
    failing = [f"{key}: {entry['by']}" for key, entry in sorted(found.items()) if not entry["passes"]]
    return checks.Verdict("grounded", checks.FAIL if failing else checks.PASS,
                          f"{len(failing)} of {len(found)} boxes neither grounded nor passed" if failing
                          else f"all {len(found)} boxes grounded or passed by the judge",
                          {"failing": len(failing)}, {"failing": "lower"}, tuple(failing))


CONTRACT = contracts.Contract("machines-boxes", 1, boxes_faults)
CHECKS = (checks.Check("grounded", judge_grounded),)
