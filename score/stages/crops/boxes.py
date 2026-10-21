"""crops-boxes@<place> (paid): the box gate's measure of the crop rows' boxes, run by the runner.

The close-up stage draws nothing whose box the box gate (tools/props/scene/box_check.py `gate`) has not passed: a box
from the partition's proposals (`box_from`), grounded by SAM 3 or passed by the judge on that very box, recorded in
WORK/partition/<scene>/boxes.json. This row runs box_check's own SAM 3 measure (its mask jobs, box_masks.py through
box_masks_cloud.py, its grounding and decided) on the crop rows only, every instance of their words kept (KEEP), and
records the result there as box_check --masks does; a copy of what it decided stays in the output. A box SAM 3 does not ground goes to the judge, which this
row does not ask: the gate then stays unknown and blocks.

The gate `boxed`: the box gate passes every crop row.
"""
import json
import pathlib

from score import checks
import score.stages.crops.crop_data as crop_data

# SAM 3 on one L4: EUR 0.04 a picture in the ledger on 2026-10-12, rounded up.
EUROS = 0.5
TOOLS = ("props/scene", "props", "props/cloud")
# Every instance of a crop's words (box_masks.py keeps 5 a row by default): a crop is one of dozens on the plot, and
# its box's own plant is seldom among SAM 3's five surest (2026-10-12: the lettuce's and the potato's were not).
KEEP = 400


def crop_rows(inputs):
    return {entry["row"] for entry in crop_data.read(inputs)["kinds"].values()}


def make_boxes(inputs, out, seed, params):
    """SAM 3's masks of the crop rows' words on their view, each box's grounding and what box_check decides,
    recorded in the partition's boxes.json."""
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text())
    wanted = crop_rows(inputs)
    with crop_data.tools(*TOOLS):
        import box_check
        import box_masks_cloud
        from PIL import Image
        jobs = [dict(job, rows=[dict(row, keep=KEEP) for row in job["rows"] if row["key"].split(".", 1)[1] in wanted])
                for job in box_check.mask_jobs(inventory["scene"], inventory, box_check.view_sizes(inventory))]
        jobs = [job for job in jobs if job["rows"]]
        (out / "mask-jobs.json").write_text(json.dumps(jobs, indent=1))
        box_masks_cloud.mask(out / "mask-jobs.json", out / "masks.json")
        measured = json.loads((out / "masks.json").read_text())
        sizes = {row["key"]: Image.open(job["picture"]).size for job in jobs for row in job["rows"]}
        grounded = {key: box_check.grounding(instances, sizes[key]) for key, instances in measured.items()}
        results = box_check.decided(grounded, {})
        box_check.record_results(results, box_check.measured_boxes([out]))
    (out / "decided.json").write_text(json.dumps({"grounding": grounded, "decided": results}, indent=1))


def boxes_faults(folder):
    return [] if (folder / "decided.json").exists() else ["no decided.json"]


def judge_boxed(output, inputs, evidence):
    """The box gate passes every crop row (read from the partition's record, as the close-up stage reads it)."""
    inventory = json.loads(pathlib.Path(inputs["inventory"]).read_text())
    with crop_data.tools(*TOOLS):
        import box_check
        rows = box_check.gate(inventory["scene"], inventory)["rows"]
    failing = [f"{row}: {rows.get(row, {}).get('result', 'no row')}: {rows.get(row, {}).get('why', '')}"
               for row in sorted(crop_rows(inputs)) if rows.get(row, {}).get("result") != box_check.PASS]
    answer = checks.FAIL if any(": fail:" in line for line in failing) else checks.UNKNOWN if failing else checks.PASS
    return checks.Verdict("boxed", answer, f"{len(failing)} of {len(crop_rows(inputs))} crop boxes not passed"
                          if failing else "the box gate passes every crop row", {"not passed": len(failing)},
                          findings=tuple(failing))


CHECKS = (checks.Check("boxed", judge_boxed),)
