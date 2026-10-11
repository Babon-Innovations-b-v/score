"""Runs on a rented machine: the relative depth of every picture in a folder, with Depth Anything V2 Small.

    /root/venv/bin/python depth_worker.py <folder of pictures>

Every picture gets its relative inverse depth (larger is nearer), worked at DEPTH_SIDE pixels and brought back to the
picture's own size, written as /root/depth/out/<stem>.npy (float32). A line "<stem> <seconds>" is printed as each
lands. The model's weights are under /root/dav2 (depth_setup.sh).
"""
import pathlib
import sys
import time

import numpy as np
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForDepthEstimation

MODEL = "/root/dav2"
OUT = pathlib.Path("/root/depth/out")
# The side the model works at: twice its own 518, a multiple of its 14-pixel patches, so the relief keeps detail.
DEPTH_SIDE = 1036


def depth_of(processor, model, picture):
    """One picture's relative inverse depth at its own size."""
    inputs = processor(images=picture, return_tensors="pt", size={"height": DEPTH_SIDE, "width": DEPTH_SIDE},
                       do_resize=True, keep_aspect_ratio=False).to("cuda")
    with torch.no_grad():
        predicted = model(**inputs).predicted_depth
    resized = torch.nn.functional.interpolate(predicted.unsqueeze(1), size=picture.size[::-1], mode="bicubic",
                                              align_corners=False)
    return resized.squeeze().float().cpu().numpy()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    processor = AutoImageProcessor.from_pretrained(MODEL)
    model = AutoModelForDepthEstimation.from_pretrained(MODEL).to("cuda").eval()
    for path in sorted(pathlib.Path(sys.argv[1]).glob("*.png")):
        start = time.time()
        np.save(OUT / f"{path.stem}.npy", depth_of(processor, model, Image.open(path).convert("RGB")))
        print(path.stem, round(time.time() - start, 1), flush=True)


if __name__ == "__main__":
    main()
