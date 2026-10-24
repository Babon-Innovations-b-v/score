"""crops-boxes@<place> (paid): the box gate's measure of the crop rows' boxes, read off the design.

The crop rows are the design's (crop_data.read: the kept scene inventory's rows whose kind grows, row_kinds), and each
row's box is its locked concept's reading's (the kept inventory's `box`: SAM 3's surest instance of the row on that
concept, score/review/reading.py). A box SAM 3 placed in the reading passes as it stands: it is SAM 3's own (as the
hand-in's `grounded`, box_check.row_verdict). Only a row the reading framed otherwise (Gemini's region, `boxed_by`
"gemini") is masked again: box_check's own SAM 3 measure (box_masks.py through box_masks_cloud.py, its grounding and
decided) on the concept, every instance of the row's words kept (KEEP). A design whose crop rows SAM 3 boxed already
has nothing to mask, and rents nothing (2026-10-22 benchmark: the old page-A read found nothing to mask and still
rented a card). A box SAM 3 does not ground goes to the judge, which this row does not ask: the gate then stays
unknown and blocks.

    decided.json   {"grounding": {row: {grounding}}, "decided": {row: {passes, by}}}

The gate `boxed`: every crop row's box passes.
"""
import json
import pathlib

from score import checks
import score.stages.crops.crop_data as crop_data

# SAM 3 on one L4: EUR 0.04 a picture in the ledger on 2026-10-12, rounded up.
EUROS = 0.5
TOOLS = ("props/scene", "props", "cloud")
# Every instance of a crop's words (box_masks.py keeps 5 a row by default): a crop is one of dozens on the plot, and
# its box's own plant is seldom among SAM 3's five surest (2026-10-12: the lettuce's and the potato's were not).
KEEP = 400
# The reading's mark of a row whose box is Gemini's region, SAM 3 having found none of it (reading.py).
GEMINI = "gemini"
IN_READING = {"passes": True, "by": "SAM 3: its box in the reading of the locked concept"}


def crop_rows(inputs):
    """The design's crop rows: {row id: crop_data's kind}."""
    return {entry["row"]: entry for entry in crop_data.read(inputs)["kinds"].values()}


def to_mask(inputs):
    """The mask jobs of the crop rows the reading did not box by SAM 3 (box_masks.py's form, one job on the locked
    concept); [] when there are none."""
    rows = {row["id"]: row for row in json.loads(pathlib.Path(inputs["inventory"]).read_text())["rows"]}
    asked = [{"key": name, "nouns": kind["nouns"], "box": rows[name]["box"], "keep": KEEP}
             for name, kind in crop_rows(inputs).items()
             if rows[name].get("box") and rows[name].get("boxed_by") == GEMINI]
    return [{"picture": str(inputs["concept"]), "rows": asked}] if asked else []


def make_boxes(inputs, out, seed, params):
    """Each crop row's box decided: the reading's SAM 3 box as it stands, the rest masked by SAM 3 on a rented card
    only when there are any; decided.json."""
    wanted = crop_rows(inputs)
    jobs = to_mask(inputs)
    asked = {row["key"] for job in jobs for row in job["rows"]}
    rows = {row["id"]: row for row in json.loads(pathlib.Path(inputs["inventory"]).read_text())["rows"]}
    grounded, results = {}, {name: IN_READING for name in wanted if name not in asked and rows[name].get("box")}
    if jobs:
        (out / "mask-jobs.json").write_text(json.dumps(jobs, indent=1))
        with crop_data.tools(*TOOLS):
            import box_check
            import box_masks_cloud
            from PIL import Image
            box_masks_cloud.mask(out / "mask-jobs.json", out / "masks.json")
            measured = json.loads((out / "masks.json").read_text())
            size = Image.open(inputs["concept"]).size
            grounded = {key: box_check.grounding(measured.get(key, []), size) for key in asked}
            results.update(box_check.decided(grounded, {}))
    (out / "decided.json").write_text(json.dumps({"grounding": grounded, "decided": results}, indent=1))


def boxes_faults(folder):
    return [] if (folder / "decided.json").exists() else ["no decided.json"]


def judge_boxed(output, inputs, evidence):
    """Every crop row's box passes (decided.json): one failed fails, one undecided or missing is unknown."""
    results = json.loads((output / "decided.json").read_text())["decided"]
    wanted = sorted(crop_rows(inputs))
    failing = [f"{row}: {results.get(row, {}).get('by', 'no box in the reading')}" for row in wanted
               if results.get(row, {}).get("passes") is not True]
    answer = (checks.FAIL if any(results.get(row, {}).get("passes") is False for row in wanted)
              else checks.UNKNOWN if failing else checks.PASS)
    return checks.Verdict("boxed", answer, f"{len(failing)} of {len(wanted)} crop boxes not passed"
                          if failing else "every crop row's box passes", {"not passed": len(failing)},
                          findings=tuple(failing))


CHECKS = (checks.Check("boxed", judge_boxed),)
