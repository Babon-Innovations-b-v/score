"""A concept picture split into its objects by SAM 3 (#128, owner 2026-11-16: the whole-scene split segments the
concept picture; its boxes and masks are the placing agent's object list, no Gemini rows, counts or plan writing).

SAM 3 (tools/props/scene/box_masks.py, run by tools/cloud/box_masks_cloud.py) is asked every word of `words` over the
whole picture: the generic PROBES by default, or the nouns the placing agent names; a word given with a pixel box
(`boxes`) is the one thing in that box, SAM 3's point-and-box model prompted with it (where a noun over the whole
picture found specks or two panels as one, #156). Each instance it finds is one
object, an instance that is the same thing as a surer one under another word dropped (`distinct`, SAME of their
union); each object keeps its pixel box, its score, the word that found it and its mask, saved full size beside the
answer (`<out stem>.masks/<key>.<n>.png`).

    objects(picture, folder, words=PROBES, boxes=None)  ->  [{"word", "box", "score", "mask"}], surest first
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
# Generic words SAM 3 is asked on every concept, for whatever it holds.
PROBES = ("object", "machine", "furniture", "container", "vehicle", "person", "plant", "lamp", "door", "window")
KEEP = 40  # the instances kept a word, surest first
# Two instances are one object when they share this much of their union.
SAME = 0.6


def area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def shared(first, second):
    """The area two boxes share."""
    return area([max(first[0], second[0]), max(first[1], second[1]), min(first[2], second[2]),
                 min(first[3], second[3])])


def same(first, second):
    """Whether two pixel boxes are one object: they share SAME of their union."""
    common = shared(first, second)
    return common >= SAME * (area(first) + area(second) - common)


def job(picture, size, words, boxes=None):
    """box_masks_cloud.py's job for one picture (its path here): each word asked over the whole picture, every
    instance's mask saved; each word of `boxes` ({word: pixel box}) the one thing in its box, its mask saved."""
    whole = [0, 0, size[0], size[1]]
    boxes = boxes or {}
    if set(words) & set(boxes):
        raise ValueError(f"asked both over the whole picture and in a box: {sorted(set(words) & set(boxes))}")
    return {"picture": str(picture),
            "rows": [{"key": word, "nouns": [word], "box": whole, "keep": KEEP, "masks": True} for word in words]
            + [{"key": word, "nouns": [word], "box": list(box), "prompt": list(box), "keep": 1, "masks": True}
               for word, box in boxes.items()]}


def distinct(found, masks):
    """The objects of box_masks' answer `found` ({word: instances, surest first}), surest first, each the same thing
    as a surer one dropped; each with its saved mask's path under `masks` (None when none was saved)."""
    every = sorted(((instance["score"], word, number, instance["box"]) for word, instances in found.items()
                    for number, instance in enumerate(instances)), key=lambda entry: -entry[0])
    kept = []
    for score, word, number, box in every:
        if not any(same(box, other["box"]) for other in kept):
            mask = masks / f"{word}.{number}.png"
            kept.append({"word": word, "box": box, "score": score, "mask": str(mask) if mask.exists() else None})
    return kept


def objects(picture, folder, words=PROBES, run=None, boxes=None):
    """The concept picture's objects (`distinct`), SAM 3 run once over every word (and every box of `boxes`) on one
    card (`run(jobs_path, out)`: box_masks_cloud.mask by default); the job, answer and masks kept under `folder`."""
    from PIL import Image
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    local = folder / pathlib.Path(picture).name
    if local != pathlib.Path(picture):
        local.write_bytes(pathlib.Path(picture).read_bytes())
    jobs = folder / "jobs.json"
    jobs.write_text(json.dumps([job(local, Image.open(local).size, words, boxes)], indent=1))
    out = folder / "masks.json"
    if run is None:
        sys.path.insert(0, str(REPO / "tools/cloud"))
        import box_masks_cloud
        run = box_masks_cloud.mask
    run(jobs, out)
    return distinct(json.loads(out.read_text()), folder / "masks.masks")
