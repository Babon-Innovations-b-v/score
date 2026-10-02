"""Redraw objects cut out of a room's target picture as whole, clean object pictures for Pixal3D.

    ~/.farm-factory-props/env/bin/python tools/props/scene/redraw.py <room> bench-1:bench cabinet-5:desk ...

Each pair names a cut-out (cutout.py's key) and the model it becomes. A cut-out is part of an
object: cut off by the picture's edge, hidden behind its neighbours, lit by the room. The picture
model (FLUX.2 klein 4B) gets the cut-out on grey as its first reference and the whole target as
its second, and draws the object whole, alone, on the prop chain's plain grey, seen from the same
side as in the room, so the model Pixal3D builds faces the way the object faced (layout.py turns it
by that). Writes redraw/<model>.png and redraw/<model>-cut.png (the reference it was given).
Holds the card.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import picture  # noqa: E402
from card import claimed  # noqa: E402
from target import folder  # noqa: E402

SIDE = 1024
GREY = (200, 200, 200)
# What the object is to be drawn as. It keeps the angle the room showed it from, which the prop
# chain's own shot (picture.SHOT) does not: that one turns every object three quarters.
WORDING = ("the {name} from the first image, redrawn as one complete whole object standing alone, "
           "every part of it that was cut off or hidden drawn in, seen from the same side and the "
           "same angle as in the first image, matching the materials and colours of the room in "
           "the second image, clean 3D render floating in empty space, centred on a plain light "
           "grey background, soft even studio lighting, whole object in frame, nothing underneath "
           "it, no floor, no wall behind it, no other objects, no people, no text")


def on_grey(cut):
    """A cut-out centred on the prop chain's grey square, filling most of it."""
    square = Image.new("RGB", (SIDE, SIDE), GREY)
    fitted = cut.copy()
    fitted.thumbnail((int(SIDE * 0.8), int(SIDE * 0.8)))
    if max(fitted.size) < SIDE * 0.8:
        scale = SIDE * 0.8 / max(fitted.size)
        fitted = cut.resize((int(cut.width * scale), int(cut.height * scale)), Image.LANCZOS)
    square.paste(fitted, ((SIDE - fitted.width) // 2, (SIDE - fitted.height) // 2), fitted)
    return square


def draw(pipeline, cut_on_grey, room_picture, name, seed):
    """One clean object picture from a loaded picture model."""
    return pipeline(
        image=[cut_on_grey, room_picture],
        prompt=WORDING.format(name=name),
        num_inference_steps=picture.STEPS,
        guidance_scale=picture.GUIDANCE,
        height=SIDE,
        width=SIDE,
        generator=torch.Generator("cpu").manual_seed(seed),
    ).images[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room")
    parser.add_argument("pairs", nargs="+", help="cut-out key:model name")
    parser.add_argument("--seed", type=int, default=7)
    options = parser.parse_args()
    out = folder(options.room)
    (out / "redraw").mkdir(exist_ok=True)
    room_picture = Image.open(out / f"{options.room}-target.png").convert("RGB")
    with claimed(f"redrawing {len(options.pairs)} objects of {options.room}"):
        pipeline = picture.load()
        for pair in options.pairs:
            key, _, model = pair.partition(":")
            reference = on_grey(Image.open(out / "objects" / f"{key}.png"))
            reference.save(out / "redraw" / f"{model}-cut.png")
            name = model.replace("_", " ")
            path = out / "redraw" / f"{model}.png"
            draw(pipeline, reference, room_picture, name, options.seed).save(path)
            print(path, flush=True)


if __name__ == "__main__":
    main()
