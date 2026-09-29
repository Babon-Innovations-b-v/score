"""Runs on a rented machine: draws every picture in its share, the model held on the card whole.

    /root/venv/bin/python picture_worker.py /root/pics/jobs.json

Each job is {"name", "wording", "seed", "steps", "guidance", "refs"} with its reference photos
already under /root/pics/refs/; each picture is written to /root/pics/out/<name>.png, and a line
"<name> <seconds>" is printed as it lands, so the runner can follow along.
"""
import json
import pathlib
import sys
import time

import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

MODEL = "/root/klein"
OUT = pathlib.Path("/root/pics/out")
REFS = pathlib.Path("/root/pics/refs")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pipeline = Flux2KleinPipeline.from_pretrained(MODEL, torch_dtype=torch.bfloat16).to("cuda")
    for job in json.loads(pathlib.Path(sys.argv[1]).read_text()):
        start = time.time()
        references = [Image.open(REFS / ref).convert("RGB") for ref in job["refs"]]
        pipeline(image=references or None, prompt=job["wording"], num_inference_steps=job["steps"],
                 guidance_scale=job["guidance"], height=1024, width=1024,
                 generator=torch.Generator("cpu").manual_seed(job["seed"])).images[0].save(
                     OUT / f"{job['name']}.png")
        print(job["name"], round(time.time() - start, 1), flush=True)


if __name__ == "__main__":
    main()
