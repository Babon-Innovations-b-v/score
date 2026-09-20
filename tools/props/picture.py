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
# The default suits a crate, a locker, a desk: things that really are plain. It says "plain, no
# logos" on purpose, and that is a refusal, so anything meant to look like working equipment must
# pass one of the forms below instead of inheriting this.
FORM = "built from thick solid panels, rigid and hard edged, plain, no logos, no text"
# For anything that flew here. Asking for a plain solid object returns concrete furniture; this
# returns spaceflight hardware, and every feature named is big enough to survive the rebuild.
SPACE = ("spacecraft hardware, white thermal panels with visible panel lines and fasteners, "
         "thick rigid panels, heavy bolted flanges, gold foil insulation, hard edged, industrial, "
         "no text")
# For a machine, which has to look like it could actually work. The default forbids exactly what
# makes equipment read as equipment: the panels, the sensors, the cables. The detail is not
# decoration here, it changes what the model takes the object to be, and enough of it survives the
# rebuild to matter; sensor domes on stalks came through as stalks with heads.
#
# This wording was terrestrial farm equipment, painted green and white with warning stripes, and
# the owner turned it down on 2026-09-20: everything here works on a Moon base, inside pressurised
# modules, so a machine should be built like the hardware that flew there rather than like a
# tractor. Writing a robot from pictures of real field machinery is what produced a green cart on
# tractor tyres for a whole day. Locked to the Moon look at the owner's word.
MACHINE = ("machine built like spacecraft hardware, white composite and brushed aluminium panels "
           "with visible panel lines and fasteners, gold foil insulation in its open bays, a "
           "glowing teal screen panel, black sensor domes and camera pods, slim machined struts, "
           "cable looms in braided sleeving, heavy bolted flanges, hard edged, clean high "
           "technology, no dirt, no text")
GLASS = ("thick metal ribs with flat opaque dark teal panels set between them, rigid and hard "
         "edged, no text")


# The forms by name, so a run can ask for one without anyone pasting the wording into a script.
FORMS = {"machine": MACHINE, "space": SPACE, "glass": GLASS}


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
    parser.add_argument("--form", default=None,
                        help="What the prop is made of, in full, when none of the named ones fit.")
    parser.add_argument("--form-named", choices=tuple(FORMS),
                        help="One of the forms written down above: machine, space or glass.")
    args = parser.parse_args()
    form = args.form or (FORMS[args.form_named] if args.form_named else FORM)
    print(make(args.sentence, args.name, args.seed, args.steps, form))


if __name__ == "__main__":
    main()
