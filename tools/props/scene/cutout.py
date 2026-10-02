"""Cut every named object out of a room's target picture with SAM 3, one mask per thing found.

    ~/.farm-factory-props/env/bin/python tools/props/scene/cutout.py <room> bench desk@0.4 ...

Reads WORK/scene/<room>/<room>-target.png (the picked take). For each name SAM 3 finds every
instance it is sure of; each lands as <name>-<n>.mask.png (the mask, full size) and <name>-<n>.png
(the object cut out of the picture on transparency, cropped round it) under objects/, and all of
them in objects.json with their name, score, pixel box and its size (cutsize.py; a box under
cutsize.MIN_CUT_SIDE on its short side is never redrawn from its cut-out). The same pixels found under two names
(a "cabinet" that is also a "desk") are kept once, under the surer name. A name may carry its own
sureness after an @, for a word SAM 3 is less sure of (measured on the habitat: "bench" scores
0.43 where "mattress" scores 0.95, and "bed" finds nothing). The floor, the walls and the ceiling
are asked for too, for the room's own shape (boxes.py), and are not cut out.

SAM 3 is Meta's (SAM License, commercial use allowed). Its weights on Hugging Face are gated;
SAM3_WEIGHTS names a copy of them when the gated repo is not open to this account. Holds the card.
"""
import argparse
import json
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image  # noqa: E402

from card import claimed  # noqa: E402
from cutsize import size_of  # noqa: E402
from target import folder  # noqa: E402

WEIGHTS = os.environ.get("SAM3_WEIGHTS", "facebook/sam3")
# How sure SAM 3 must be of an instance, and of each pixel in it.
THRESHOLD = 0.5
MASK_THRESHOLD = 0.5
# Two masks sharing this much of their union are one thing found twice. Over the union, not over
# the smaller one: drawers inside a bench are a "cabinet" of their own, and must not cost the bench.
SAME_THING = 0.6
# The room's own surfaces, measured for its shape and never cut out as objects: what each is asked
# for as, and how sure SAM 3 must be. "wall" alone finds nothing above 0.5 in a rounded room;
# "curved wall" finds it at 0.66.
SURFACES = {"floor": ("floor", 0.5), "wall": ("curved wall", 0.3), "ceiling": ("ceiling", 0.3)}
# Room left round a cut-out, as a share of its longer side.
MARGIN = 0.08


def name_and_sureness(asked):
    """A name as asked on the command line, split from its own sureness after an @."""
    name, _, sureness = asked.partition("@")
    return name, float(sureness) if sureness else THRESHOLD


def found(model, processor, image, name, sureness):
    """Every instance of `name` SAM 3 finds in the picture, as (mask, score) pairs."""
    inputs = processor(images=image, text=name, return_tensors="pt").to("cuda")
    with torch.no_grad():
        outputs = model(**inputs)
    result = processor.post_process_instance_segmentation(
        outputs, threshold=sureness, mask_threshold=MASK_THRESHOLD,
        target_sizes=[image.size[::-1]])[0]
    return [(mask.cpu().numpy().astype(bool), float(score))
            for mask, score in zip(result["masks"], result["scores"])]


def overlap(first, second):
    """How much two masks share, over their union."""
    union = (first | second).sum()
    return float((first & second).sum()) / union if union else 0.0


def kept(instances):
    """The instances with each thing found twice kept once, the surest first."""
    chosen = []
    for instance in sorted(instances, key=lambda item: -item["score"]):
        if all(overlap(instance["mask"], other["mask"]) < SAME_THING for other in chosen):
            chosen.append(instance)
    return chosen


def pixel_box(mask):
    """The mask's box in pixels, as [left, top, right, bottom]."""
    rows, columns = np.nonzero(mask)
    return [int(columns.min()), int(rows.min()), int(columns.max()) + 1, int(rows.max()) + 1]


def cut(image, mask):
    """The object on transparency, cropped round its mask with a margin."""
    left, top, right, bottom = pixel_box(mask)
    pad = int(MARGIN * max(right - left, bottom - top))
    rgba = np.dstack([np.asarray(image), mask.astype(np.uint8) * 255])
    crop = rgba[max(0, top - pad):bottom + pad, max(0, left - pad):right + pad]
    return Image.fromarray(crop, "RGBA")


def segment(image, asked):
    """Every instance of every name and every room surface, found by SAM 3 on the card."""
    wanted = dict(name_and_sureness(name) for name in asked)
    wanted.update({surface: sureness for surface, (_, sureness) in SURFACES.items()})
    words = {surface: word for surface, (word, _) in SURFACES.items()}
    from transformers import Sam3Model, Sam3Processor
    with claimed("SAM 3 cut-outs"):
        processor = Sam3Processor.from_pretrained(WEIGHTS)
        model = Sam3Model.from_pretrained(WEIGHTS, torch_dtype=torch.float32).to("cuda").eval()
        masks_by_name = {name: found(model, processor, image, words.get(name, name), sureness)
                         for name, sureness in wanted.items()}
    for name, pairs in masks_by_name.items():
        print(f"{name}: {len(pairs)} found", file=sys.stderr)
    return masks_by_name


def save_surfaces(out, image, masks_by_name):
    """Each room surface's masks merged into one, saved as surfaces.npz."""
    shape = image.size[::-1]
    merged = {}
    for name in SURFACES:
        masks = [mask for mask, _ in masks_by_name.get(name, [])]
        merged[name] = np.any(masks, axis=0) if masks else np.zeros(shape, bool)
    np.savez_compressed(out / "surfaces.npz", **merged)


def save_objects(out, image, masks_by_name):
    """Each object instance's mask and cut-out, and the list of them; the list."""
    objects = out / "objects"
    objects.mkdir(exist_ok=True)
    instances = [{"name": name, "mask": mask, "score": score}
                 for name, pairs in masks_by_name.items() if name not in SURFACES
                 for mask, score in pairs]
    listed, counts = [], {}
    for instance in kept(instances):
        counts[instance["name"]] = counts.get(instance["name"], 0) + 1
        key = f"{instance['name'].replace(' ', '_')}-{counts[instance['name']]}"
        Image.fromarray(instance["mask"].astype(np.uint8) * 255).save(objects / f"{key}.mask.png")
        cut(image, instance["mask"]).save(objects / f"{key}.png")
        listed.append({"key": key, "name": instance["name"], "score": round(instance["score"], 3),
                       "box": pixel_box(instance["mask"]), **size_of(pixel_box(instance["mask"]))})
    (out / "objects.json").write_text(json.dumps(listed, indent=1))
    return listed


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room")
    parser.add_argument("names", nargs="+")
    options = parser.parse_args()
    out = folder(options.room)
    image = Image.open(out / f"{options.room}-target.png").convert("RGB")
    masks_by_name = segment(image, options.names)
    save_surfaces(out, image, masks_by_name)
    for item in save_objects(out, image, masks_by_name):
        print(item["key"], item["score"], item["box"], "short side", item["short_side"])


if __name__ == "__main__":
    main()
