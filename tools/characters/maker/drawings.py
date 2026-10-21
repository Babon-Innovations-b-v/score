"""FLUX.2 klein 4B (Apache-2.0) on the rented card, as the prop route's close-up draws with it (prop_closeup.py):
the pipeline whole on the card (`klein`), one picture a seed (`draw`), the references opened (`pictures`) and the
words every person's picture ends with (`FORM`). The shipped person chain's own drawings (its A-pose picture, the
clay hair and the face on the head's depth) were retired with it (owner, 2026-10-21: all old stuff is retired).
"""
import pathlib
import time

import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

MODELS = pathlib.Path("/root/models")
KLEIN = MODELS / "klein-4b"

FORM = ("softly lit detailed 3D render of a realistic character as a game asset, believable materials with visible "
        "shading and fabric folds, soft studio light, no cast shadows, plain light grey background, not a toy, no text")


def klein():
    """FLUX.2 klein 4B (distilled), whole on the card."""
    return Flux2KleinPipeline.from_pretrained(KLEIN, torch_dtype=torch.bfloat16).to("cuda")


def draw(pipeline, out, seeds, settings):
    """One picture a seed into `out` (a path with `{seed}` in its name); their paths."""
    made = []
    for seed in seeds:
        began = time.time()
        picture = pipeline(generator=torch.Generator("cpu").manual_seed(seed), **settings).images[0]
        path = pathlib.Path(str(out).format(seed=seed))
        path.parent.mkdir(parents=True, exist_ok=True)
        picture.save(path)
        made.append(path)
        print(f"{path.name} {time.time() - began:.1f}", flush=True)
    return made


def pictures(paths):
    return [Image.open(path).convert("RGB") for path in paths]
