"""Runs on a rented card: SAM 3 masks of every inventory row's thing on its view's picture, measured against the row's
box, for the box check (box_check.py --masks).

    /root/venv/bin/python tools/props/scene/box_masks.py <jobs.json> <out.json>

The jobs are [{"picture": <name of a picture beside jobs.json>, "rows": [{"key", "nouns", "box"}]}]. For each picture
every distinct noun is asked of SAM 3 once (cutout.py's way, at cutout.THRESHOLD); each instance it finds is measured
against each row asking for that noun: `inside`, the share of the mask inside the row's box, and `fills`, the share
of the box the mask covers. The out file maps each row's key to its instances, surest first, at most KEEP of them
(or the row's own `keep`: a count of many, such as a bed's plants):
{"box": the mask's pixel box, "score", "inside", "fills"}. No mask leaves the card, but for a row asking for its own
(`"mask": true`): its instance that best matches its box (`matching`) is saved, full size, as
<out stem>.masks/<key>.png beside the out file (a code-built row's likeness is held to it: score/stages/props
thin_straight.py). Refused on this PC (local_models.py); the runner is ../cloud/box_masks_cloud.py.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import cutout  # noqa: E402
from local_models import refuse_here  # noqa: E402

# The instances kept for a row, surest first.
KEEP = 5


def measured(mask, box):
    """One instance's mask against a row's box: its pixel box, the share of it inside the box and the share of the
    box it fills."""
    left, top, right, bottom = (int(round(value)) for value in box)
    within = int(mask[max(0, top):bottom, max(0, left):right].sum())
    area = max(1, (right - left) * (bottom - top))
    return {"box": cutout.pixel_box(mask), "inside": round(within / max(1, int(mask.sum())), 3),
            "fills": round(within / area, 3)}


def matching(pairs, box):
    """The mask of (mask, score) `pairs` that is most nearly the box's own thing (the larger of its smaller share,
    inside and fills), or None when there are none."""
    shares = [min(found["inside"], found["fills"]) for found in (measured(mask, box) for mask, _ in pairs)]
    return pairs[shares.index(max(shares))][0] if pairs else None


def save_masks(found, rows, folder):
    """Each row asking for its mask (`"mask": true`) whose words SAM 3 found: its matching mask as folder/<key>.png."""
    for row in rows:
        mask = matching([pair for word in row["nouns"] for pair in found[word]], row["box"]) if row.get("mask") else None
        if mask is not None:
            Image.fromarray(mask.astype("uint8") * 255).save(folder / f"{row['key']}.png")


def picture_rows(model, processor, picture, rows, masks):
    """Every row of one picture with its nouns' instances measured against its box, surest first; the masks the rows
    ask for saved in `masks`."""
    image = Image.open(picture).convert("RGB")
    found = {word: cutout.found(model, processor, image, word, cutout.THRESHOLD)
             for word in sorted({word for row in rows for word in row["nouns"]})}
    save_masks(found, rows, masks)
    return {row["key"]: [dict(measured(mask, row["box"]), score=round(score, 3))
                         for mask, score in sorted((pair for word in row["nouns"] for pair in found[word]),
                                                   key=lambda pair: -pair[1])[:row.get("keep", KEEP)]]
            for row in rows}


def main():
    refuse_here("SAM 3", "tools/cloud/box_masks_cloud.py")
    jobs_path, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    from transformers import Sam3Model, Sam3Processor
    processor = Sam3Processor.from_pretrained(cutout.WEIGHTS)
    model = Sam3Model.from_pretrained(cutout.WEIGHTS, torch_dtype=torch.float32).to("cuda").eval()
    results, masks = {}, out.parent / f"{out.stem}.masks"
    masks.mkdir(parents=True, exist_ok=True)  # there even when empty: the runner copies it back
    for job in json.loads(jobs_path.read_text()):
        results.update(picture_rows(model, processor, jobs_path.parent / job["picture"], job["rows"], masks))
        print(f"{job['picture']}: {len(job['rows'])} rows", flush=True)
        out.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
