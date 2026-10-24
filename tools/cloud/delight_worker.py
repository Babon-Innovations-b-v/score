"""Runs on a rented machine: an unlit paint copy of every picture, with Marigold-IID appearance.

    /root/venv/bin/python delight_worker.py [<folder of pictures>]

Every picture in the folder (/root/unlit/in/ by default; a share's own folder when a list is spread over machines)
gets its albedo, the colour of the paint with the light taken out,
written to /root/unlit/out/<stem>.png at the picture's own size and aligned with it pixel for pixel;
its roughness and metal go beside it as <stem>-roughness.png and <stem>-metal.png, for looking at.
A line "<stem> <seconds>" is printed as each lands.
"""
import pathlib
import sys
import time

import diffusers
import torch
from PIL import Image

MODEL = "/root/marigold"
IN = pathlib.Path("/root/unlit/in")
OUT = pathlib.Path("/root/unlit/out")
# Our pictures are 1024 square; worked at their own size the paint keeps its edges and lettering
# (the model's own default, 768, softens them).
RESOLUTION = 1024
# Predictions averaged per picture, which steadies the colour of large flat panels.
ENSEMBLE = 4


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pipeline = diffusers.MarigoldIntrinsicsPipeline.from_pretrained(
        MODEL, variant="fp16", torch_dtype=torch.float16).to("cuda")
    for path in sorted(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else IN).glob("*.png")):
        start = time.time()
        picture = Image.open(path).convert("RGB")
        result = pipeline(picture, ensemble_size=ENSEMBLE, processing_resolution=RESOLUTION,
                          generator=torch.Generator("cuda").manual_seed(0))
        maps = pipeline.image_processor.visualize_intrinsics(result.prediction,
                                                             pipeline.target_properties)[0]
        maps["albedo"].resize(picture.size, Image.LANCZOS).save(OUT / path.name)
        maps["roughness"].save(OUT / f"{path.stem}-roughness.png")
        maps["metallicity"].save(OUT / f"{path.stem}-metal.png")
        print(path.stem, round(time.time() - start, 1), flush=True)


if __name__ == "__main__":
    main()
