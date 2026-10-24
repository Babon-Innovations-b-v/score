"""Runs on a rented machine: SAM 2.1's automatic mask generator over every picture in a folder.

    /root/venv/bin/python segment_worker.py <weights repo> <in folder> <out folder>

Each picture (a clean close-up, cut out on white) gives <out>/<picture stem>.npz: `masks` (the masks' pixels, packed
bits, n x height x ceil(width / 8)), `shape`, `area`, `predicted_iou` and `stability_score` per mask. The generator's
settings are its defaults but for a denser grid and a looser stability filter, so a painted band or a foil patch is
found as a region of its own; small regions are filtered where the masks are used (labels.py).
"""
import pathlib
import sys

import numpy as np
import torch
from PIL import Image
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
from sam2.build_sam import build_sam2_hf

POINTS_PER_SIDE = 48
PRED_IOU = 0.8
STABILITY = 0.9


def picture(path):
    """The picture as RGB on white, the way it was cut out."""
    cut = Image.open(path).convert("RGBA")
    white = Image.new("RGBA", cut.size, (255, 255, 255, 255))
    return np.asarray(Image.alpha_composite(white, cut).convert("RGB"))


def main():
    weights, source, out = sys.argv[1], pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    model = build_sam2_hf(weights, device="cuda")
    generator = SAM2AutomaticMaskGenerator(model, points_per_side=POINTS_PER_SIDE, pred_iou_thresh=PRED_IOU,
                                           stability_score_thresh=STABILITY)
    for path in sorted(source.glob("*.png")):
        image = picture(path)
        with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
            found = generator.generate(image)
        masks = np.array([entry["segmentation"] for entry in found], dtype=bool).reshape(-1, *image.shape[:2])
        np.savez_compressed(out / f"{path.stem}.npz", masks=np.packbits(masks, axis=-1),
                            shape=np.array(image.shape[:2]),
                            area=np.array([entry["area"] for entry in found]),
                            predicted_iou=np.array([entry["predicted_iou"] for entry in found]),
                            stability_score=np.array([entry["stability_score"] for entry in found]))
        print(path.stem, len(found), flush=True)


if __name__ == "__main__":
    main()
