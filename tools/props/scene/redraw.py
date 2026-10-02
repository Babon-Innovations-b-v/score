"""Redraw objects cut out of a room's target picture as whole, clean object pictures for Pixal3D.

    ~/.farm-factory-props/env/bin/python tools/props/scene/redraw.py <room> bench-1:bench cabinet-5:desk ...

Each pair names a cut-out (cutout.py's key) and the model it becomes, with an optional third part
describing it for a close-up ("desk_lamp-1:desk_lamp:a globe lamp on a jointed arm"). Only a
cut-out whose box is at least cutsize.MIN_CUT_SIDE pixels on its short side is redrawn; a smaller
one is drawn afresh as a close-up when the target was drawn here, and left off otherwise
(cutsize.py). A cut-out is part of an
object: cut off by the picture's edge, hidden behind its neighbours, lit by the room. The picture
model (FLUX.2 klein 4B) gets the cut-out on grey as its first reference and the whole target as
its second, and draws the object whole, alone, on the prop chain's plain grey, seen from the same
side as in the room, so the model Pixal3D builds faces the way the object faced (layout.py turns it
by that). Writes redraw/<model>.png and redraw/<model>-cut.png (the reference it was given), and
redraw/report.json: every object with its cut-out's size and the way it took, and the build list
for pixal.py. Holds the card.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import picture  # noqa: E402
from card import claimed  # noqa: E402
from cutsize import ROUTES, route, size_of  # noqa: E402
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
# What an object too small to redraw is drawn as instead: from its name alone, in the room's look,
# square to its front, so Pixal3D sees it whole (layout.py turns it by the room, not the camera).
CLOSE_UP = ("a close-up of one {name}, {description}, as it would stand in the room in the image, "
            "matching that room's materials, colours and style, the whole object seen straight on "
            "from its front, clean 3D render floating in empty space, centred on a plain light "
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


def draw(pipeline, references, prompt, seed):
    """One clean object picture from a loaded picture model."""
    return pipeline(
        image=references,
        prompt=prompt,
        num_inference_steps=picture.STEPS,
        guidance_scale=picture.GUIDANCE,
        height=SIDE,
        width=SIDE,
        generator=torch.Generator("cpu").manual_seed(seed),
    ).images[0]


def drawn_here(out, room):
    """Whether the target was drawn by target.py, so the picture model can draw in its look again."""
    return any(out.glob(f"{room}-target-*.png"))


def planned(out, room, pairs):
    """Each asked-for object with its cut-out's size and its route, in the order asked."""
    boxes = {item["key"]: item["box"] for item in json.loads((out / "objects.json").read_text())}
    can_close_up = drawn_here(out, room)
    rows = []
    for pair in pairs:
        key, _, rest = pair.partition(":")
        model, _, description = rest.partition(":")
        name = model.replace("_", " ")
        rows.append({"key": key, "model": model, "name": name, "description": description or name,
                     **size_of(boxes[key]), "route": route(boxes[key], can_close_up)})
    return rows


def draw_row(pipeline, out, room_picture, row, seed):
    """One object's picture, drawn by its route and saved under redraw/; its path."""
    path = out / "redraw" / f"{row['model']}.png"
    if row["route"] == "redraw":
        reference = on_grey(Image.open(out / "objects" / f"{row['key']}.png"))
        reference.save(out / "redraw" / f"{row['model']}-cut.png")
        drawn = draw(pipeline, [reference, room_picture], WORDING.format(name=row["name"]), seed)
    else:
        prompt = CLOSE_UP.format(name=row["name"], description=row["description"])
        drawn = draw(pipeline, [room_picture], prompt, seed)
    drawn.save(path)
    return path


def report(out, rows):
    """Every object's cut-out size and route, printed and saved as redraw/report.json."""
    for row in rows:
        print(f"{row['key']:<22} {row['model']:<18} {row['width']:>4} x {row['height']:<4} "
              f"short {row['short_side']:>4}  area {row['area']:>7}  {ROUTES[row['route']]}")
    build = sorted({row["model"] for row in rows if row["route"] != "dropped"})
    (out / "redraw" / "report.json").write_text(json.dumps({"objects": rows, "build": build}, indent=1))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room")
    parser.add_argument("pairs", nargs="+", help="cut-out key:model name[:description]")
    parser.add_argument("--seed", type=int, default=7)
    options = parser.parse_args()
    out = folder(options.room)
    (out / "redraw").mkdir(exist_ok=True)
    rows = planned(out, options.room, options.pairs)
    report(out, rows)
    to_draw = [row for row in rows if row["route"] != "dropped"]
    if not to_draw:
        return
    room_picture = Image.open(out / f"{options.room}-target.png").convert("RGB")
    with claimed(f"redrawing {len(to_draw)} objects of {options.room}"):
        pipeline = picture.load()
        for row in to_draw:
            print(draw_row(pipeline, out, room_picture, row, options.seed), flush=True)


if __name__ == "__main__":
    main()
