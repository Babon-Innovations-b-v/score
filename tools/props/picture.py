"""Make the reference picture a prop is built from.

The picture is the brief. The 3D step rebuilds what this picture shows and cannot invent a
surface it hides, so the wording below is doing the real work, not the 3D model. Three things
it insists on, each learned from a prop that came back wrong without it: solid slabs rather
than thin frames, a level camera through a long lens, and no small raised detail, which comes
back as soft bulges and belongs in ink lines instead.

    picture.py <name> "<sentence>" [--seed 7] [--form-named machine] [--ref photo.jpg ...]
    picture.py --list jobs.json

Real photographs passed with --ref are handed to the picture model as references, so it draws our
own object in their style, scale and realism; that is what made the supply rockets (#55). A list
is a JSON array of {"name", "sentence", "seed", "form", "refs"} and loads the model once.
"""
import argparse
import json
import pathlib
import sys

import torch
from diffusers import Flux2KleinPipeline
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from card import claimed  # noqa: E402
from paths import PICTURE_MODEL, PICTURES, make_directories  # noqa: E402

# Composition only, and it refuses the ground many ways on purpose. Anything else in the picture is
# rebuilt as part of the prop, so a prop asked for in its setting comes back standing on a lump of
# that setting. The plinth is the same fault wearing a studio coat: asked for a clean product shot
# the model composes a display stand, and whatever the sentence names last and lowest becomes that
# stand. A machine's working end, a drill point or a picker's grab, is named last and points down,
# so it is exactly what gets flattened into a base plate. Hence "floating in empty space" and four
# names for the thing we do not want under it.
#
# The camera is level and far away through a long lens, because Pixal3D rebuilds as if it saw the
# object from a level front camera with a 20 degree lens (image-to-3dlab). The older view from
# above the corner tilted every model and bent tall ones; the level shot made the supply rockets
# and the Mars camp (#55, #109, 2026-09-28/29).
SHOT = ("clean 3D render of a single object floating in empty space, centred on a plain light grey "
        "background, soft even studio lighting with gentle shading, seen from straight in front at "
        "the object's own height, level camera, long telephoto lens, three quarter turn so the "
        "front and one side show, whole object in frame, nothing underneath it, no plinth, no "
        "pedestal, no display stand, no base plate, no ground, no terrain, no scenery, no people")

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


# The picture model is step-distilled: its own card asks for 4 steps at guidance 1.0 through its own
# pipeline. We ran 28 steps at 4.0 through the general one until 2026-09-29; side by side the 4-step
# pictures were as clean or cleaner, at about 8 s a picture instead of 20 on the owner's card (#55).
STEPS = 4
GUIDANCE = 1.0

# The forms by name, so a run can ask for one without anyone pasting the wording into a script.
FORMS = {"machine": MACHINE, "space": SPACE, "glass": GLASS}


def load():
    """The picture model, ready to draw."""
    pipeline = Flux2KleinPipeline.from_pretrained(PICTURE_MODEL, torch_dtype=torch.bfloat16)
    pipeline.enable_model_cpu_offload()
    return pipeline


def draw(pipeline, sentence, name, seed, steps, form=FORM, refs=()):
    """One picture from a loaded model, saved under PICTURES; the path to it."""
    references = [Image.open(ref).convert("RGB") for ref in refs]
    image = pipeline(
        image=references or None,
        prompt=f"{sentence}, {form}, {SHOT}",
        num_inference_steps=steps,
        guidance_scale=GUIDANCE,
        height=1024,
        width=1024,
        generator=torch.Generator("cpu").manual_seed(seed),
    ).images[0]
    path = PICTURES / f"{name}.png"
    image.save(path)
    return path


def make(sentence, name, seed, steps, form=FORM, refs=()):
    make_directories()
    with claimed(f"the picture for {name}"):
        return draw(load(), sentence, name, seed, steps, form, refs)


def make_list(jobs, steps):
    """Every picture in a list with the model loaded once, skipping any already made."""
    make_directories()
    with claimed(f"{len(jobs)} pictures"):
        pipeline = load()
        for job in jobs:
            if (PICTURES / f"{job['name']}.png").exists():
                continue
            form = FORMS.get(job.get("form"), job.get("form") or FORM)
            print(draw(pipeline, job["sentence"], job["name"], job.get("seed", 7), steps, form,
                       job.get("refs", ())), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", nargs="?", help="what the prop is called, used for every file it produces")
    parser.add_argument("sentence", nargs="?", help="what the prop is, in plain words")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--steps", type=int, default=STEPS)
    parser.add_argument("--form", default=None,
                        help="What the prop is made of, in full, when none of the named ones fit.")
    parser.add_argument("--form-named", choices=tuple(FORMS),
                        help="One of the forms written down above: machine, space or glass.")
    parser.add_argument("--ref", action="append", default=[], help="a real photograph to draw from")
    parser.add_argument("--list", type=pathlib.Path, help="a JSON list of pictures to make")
    args = parser.parse_args()
    if args.list:
        make_list(json.loads(args.list.read_text()), args.steps)
        return
    if not (args.name and args.sentence):
        parser.error("give a name and a sentence, or --list")
    form = args.form or (FORMS[args.form_named] if args.form_named else FORM)
    print(make(args.sentence, args.name, args.seed, args.steps, form, args.ref))


if __name__ == "__main__":
    main()
