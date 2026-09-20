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
from card import claimed  # noqa: E402
from paths import PICTURE_MODEL, PICTURES, make_directories  # noqa: E402

# Composition only, and it refuses the ground many ways on purpose. Anything else in the picture is
# rebuilt as part of the prop, so a prop asked for in its setting comes back standing on a lump of
# that setting. The plinth is the same fault wearing a studio coat: asked for a clean product shot
# the model composes a display stand, and whatever the sentence names last and lowest becomes that
# stand. A machine's working end, a drill point or a picker's grab, is named last and points down,
# so it is exactly what gets flattened into a base plate. Hence "floating in empty space" and four
# names for the thing we do not want under it.
SHOT = ("clean 3D render of a single object floating in empty space, centred on a plain light grey "
        "background, neutral even studio lighting, no cast shadows, seen from above the front left "
        "corner so the top surface and two sides are all clearly visible, whole object in frame, "
        "nothing underneath it, no plinth, no pedestal, no display stand, no base plate, no ground, "
        "no terrain, no scenery, no people")

# Appended by default, because the 3D step rebuilds form and not ornament. A prop whose character
# is a different material passes its own with --form; the two below cover most of this game.
FORM = "built from thick solid panels, rigid and hard edged, plain, no logos, no text"
# For anything that flew here. Asking for a plain solid object returns concrete furniture; this
# returns spaceflight hardware, and every feature named is big enough to survive the rebuild.
SPACE = ("spacecraft hardware, white thermal panels with visible panel lines and fasteners, "
         "thick rigid panels, heavy bolted flanges, gold foil insulation, hard edged, industrial, "
         "no text")
GLASS = ("thick metal ribs with flat opaque dark teal panels set between them, rigid and hard "
         "edged, no text")


def make(sentence, name, seed, steps, form=FORM, shot=SHOT):
    make_directories()
    with claimed(f"the picture for {name}"):
        pipeline = Flux2Pipeline.from_pretrained(PICTURE_MODEL, torch_dtype=torch.bfloat16)
        pipeline.enable_model_cpu_offload()
        image = pipeline(
            prompt=f"{sentence}, {form}, {shot}",
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
    parser.add_argument("--form", default=FORM,
                        help="What the prop is made of, when solid panels is the wrong answer.")
    args = parser.parse_args()
    print(make(args.sentence, args.name, args.seed, args.steps, args.form))


if __name__ == "__main__":
    main()
