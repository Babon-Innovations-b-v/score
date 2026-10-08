"""Runs on a rented machine: draws every picture in its share with one picture model.

    /root/venv/bin/python picture_worker.py /root/pics/jobs.json <pipeline class> <whole GB>

The model's weights are under /root/model (picture_setup.sh), loaded with the named diffusers
pipeline; it is held on the card whole when the card has <whole GB> of memory, and moved on and off
the card part by part otherwise. Each job is {"name", "wording", "seed", "steps", "call", "refs"},
"call" being the model's own settings (pictures.MODELS), and optionally "width" and "height" for a
picture that is not square (a panorama). The reference photos are already under /root/pics/refs/;
each picture is written to /root/pics/out/<name>.png, and a line "<name> <seconds>" is printed as it
lands, so the runner can follow along.
"""
import json
import pathlib
import sys
import time

import diffusers
import torch
from PIL import Image

MODEL = "/root/model"
OUT = pathlib.Path("/root/pics/out")
REFS = pathlib.Path("/root/pics/refs")
# A picture is this many pixels square unless its job asks for a width and height of its own.
SIDE = 1024


def load(pipeline_class, whole_gb):
    """The picture model on the card: whole when the card holds `whole_gb`, else part by part."""
    pipeline = getattr(diffusers, pipeline_class).from_pretrained(MODEL, torch_dtype=torch.bfloat16)
    card_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
    if card_gb < whole_gb:
        pipeline.enable_model_cpu_offload()
        return pipeline
    return pipeline.to("cuda")


def arguments(job):
    """What the pipeline is called with for one job."""
    references = [Image.open(REFS / ref).convert("RGB") for ref in job["refs"]]
    return {"image": references or None, "prompt": job["wording"], "num_inference_steps": job["steps"],
            "height": job.get("height", SIDE), "width": job.get("width", SIDE),
            "generator": torch.Generator("cpu").manual_seed(job["seed"]), **job["call"]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pipeline = load(sys.argv[2], float(sys.argv[3]))
    for job in json.loads(pathlib.Path(sys.argv[1]).read_text()):
        start = time.time()
        pipeline(**arguments(job)).images[0].save(OUT / f"{job['name']}.png")
        print(job["name"], round(time.time() - start, 1), flush=True)


if __name__ == "__main__":
    main()
