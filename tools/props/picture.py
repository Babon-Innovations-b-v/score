"""Make the reference picture a prop is built from.

The picture is the brief. The 3D step rebuilds what this picture shows and cannot invent a
surface it hides, so the wording below is doing the real work, not the 3D model. Three things
it insists on, each learned from a prop that came back wrong without it: solid slabs rather
than thin frames, a view from above the corner so the top and two sides all appear, and no
small raised detail, which comes back as soft bulges and belongs in ink lines instead.
"""
import argparse
import sys

import torch
from diffusers import Flux2Pipeline

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from paths import PICTURE_MODEL, PICTURES, make_directories  # noqa: E402

SHOT = ("product photograph, single object centred, seen from above the front left corner so the "
        "top surface and two sides are all clearly visible, plain light grey seamless background, "
        "even soft studio lighting, no cast shadows, sharp focus throughout, whole object in frame")

# Appended to every prop, because the 3D step rebuilds form and not ornament.
FORM = "built from thick solid panels, rigid and hard edged, plain, no logos, no text"


def make(sentence, name, seed, steps):
    make_directories()
    pipeline = Flux2Pipeline.from_pretrained(PICTURE_MODEL, torch_dtype=torch.bfloat16)
    pipeline.enable_model_cpu_offload()
    image = pipeline(
        prompt=f"{sentence}, {FORM}, {SHOT}",
        num_inference_steps=steps,
        guidance_scale=4.0,
        height=1024,
        width=1024,
        generator=torch.Generator("cpu").manual_seed(seed),
    ).images[0]
    path = PICTURES / f"{name}.png"
    image.save(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="what the prop is called, used for every file it produces")
    parser.add_argument("sentence", help="what the prop is, in plain words")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--steps", type=int, default=28)
    args = parser.parse_args()
    print(make(args.sentence, args.name, args.seed, args.steps))


if __name__ == "__main__":
    main()
