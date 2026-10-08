"""Redraw objects cut out of a room's target picture as whole, clean object pictures for Pixal3D.

    ~/.farm-factory-props/env/bin/python tools/props/scene/redraw.py <room> bench-1:bench cabinet-5:desk ... \
        --place <place> [--picture <view.png> --out <folder>] [--seeds 7,8] [--side 1536]

Each pair names a cut-out (cutout.py's key) and the model it becomes, with an optional third part
describing it for a close-up ("desk_lamp-1:desk_lamp:a globe lamp on a jointed arm"). Only a
cut-out whose box is at least cutsize.MIN_CUT_SIDE pixels on its short side is redrawn; a smaller
one is drawn afresh as a close-up when the target was drawn here, and left off otherwise
(cutsize.py). A key of "none" names an object with no cut-out, drawn as a close-up in the plan's
look; cloud/scene.py refuses it, since a scene's every object is a row boxed on its plan
(inventory.py). A cut-out is part
of an object: cut off by the picture's edge, hidden behind its neighbours, lit by the room. The
picture model (FLUX.2 klein 4B) gets the cut-out on grey as its first reference and the whole
target as its second, and draws the object whole, alone, on the prop chain's plain grey, square to
its front (the bible's rule: a model is turned by the wall it stands at, never by the plan's
camera). --picture names a view cut from a plan world (planview.py) in place of the target, whose
cut-outs cutout.py wrote under --out; such a plan's look can be drawn in again, so its small
objects get close-ups. Writes redraw/<model>.png (redraw/<model>-s<seed>.png for each of several
--seeds) and redraw/<model>-cut.png (the reference it was given), and redraw/report.json: every
object with its cut-out's size and the way it took, and the build list for the cloud batch. Holds
the card. Runs on a rented card through cloud/scene.py (a plan's "objects"); on this PC it is
refused. Every picture is worded with its place's style text from data/definitions/place.json
(--place, place.py), never with words a session wrote.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import torch  # noqa: E402
from PIL import Image  # noqa: E402

import picture  # noqa: E402
import place  # noqa: E402
from card import claimed  # noqa: E402
from cutsize import ROUTES, route, size_of  # noqa: E402
from target import folder  # noqa: E402

# The reference square a cut-out is set on, and the side the object's picture is drawn at (round
# three draws 1536; --side changes it).
SIDE = 1024
DRAW_SIDE = 1536
GREY = (200, 200, 200)
# What the object is to be drawn as: square to its own front, whatever angle the room showed it
# from, since turning models by the plan's camera put round one's 25 to 96 degrees off (bible,
# "How a scene is designed").
WORDING = ("the {name} from the first image, redrawn as one complete whole object standing alone, "
           "every part of it that was cut off or hidden drawn in, seen straight on from its front, "
           "square to its front face, level camera at its own height, matching the materials and "
           "colours of the object in the first image and of the room in "
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


def draw(pipeline, references, prompt, seed, side):
    """One clean object picture `side` pixels square from a loaded picture model."""
    return pipeline(
        image=references,
        prompt=prompt,
        num_inference_steps=picture.STEPS,
        guidance_scale=picture.GUIDANCE,
        height=side,
        width=side,
        generator=torch.Generator("cpu").manual_seed(seed),
    ).images[0]


def drawn_here(out, room):
    """Whether the target was drawn by target.py, so the picture model can draw in its look again."""
    return any(out.glob(f"{room}-target-*.png"))


# The key of an object the plan does not show: it has no box, so it can only be drawn as a close-up.
NOT_IN_PLAN = "none"


def planned(out, pairs, can_close_up):
    """Each asked-for object with its cut-out's size and its route, in the order asked."""
    listed = out / "objects.json"
    boxes = {item["key"]: item["box"] for item in json.loads(listed.read_text())} if listed.exists() else {}
    boxes[NOT_IN_PLAN] = [0, 0, 0, 0]
    rows = []
    for pair in pairs:
        key, _, rest = pair.partition(":")
        model, _, description = rest.partition(":")
        name = model.replace("_", " ")
        rows.append({"key": key, "model": model, "name": name, "description": description or name,
                     **size_of(boxes[key]), "route": route(boxes[key], can_close_up)})
    return rows


def in_the_place(prompt, style):
    """A picture's words with its place's style text after them."""
    return f"{prompt}, in the look of this place: {style}"


def draw_row(pipeline, out, room_picture, row, seed, path, side, style):
    """One object's picture, drawn by its route in its place's look and saved at `path`; its path."""
    if row["route"] == "redraw":
        reference = on_grey(Image.open(out / "objects" / f"{row['key']}.png"))
        reference.save(out / "redraw" / f"{row['model']}-cut.png")
        prompt = in_the_place(WORDING.format(name=row["name"]), style)
        drawn = draw(pipeline, [reference, room_picture], prompt, seed, side)
    else:
        prompt = in_the_place(CLOSE_UP.format(name=row["name"], description=row["description"]), style)
        drawn = draw(pipeline, [room_picture], prompt, seed, side)
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
    parser.add_argument("--seeds", default="7", help="one seed, or several to choose between: 7,8")
    parser.add_argument("--side", type=int, default=DRAW_SIDE, help="the picture's side in pixels")
    parser.add_argument("--picture", type=pathlib.Path, help="a plan view in place of the target")
    parser.add_argument("--out", type=pathlib.Path, help="where cutout.py put that view's cut-outs")
    parser.add_argument("--place", required=True, help="the place whose style text words every picture")
    options = parser.parse_args()
    if bool(options.picture) != bool(options.out):
        parser.error("--picture and --out go together")
    style = place.style_text(options.place)
    out = options.out or folder(options.room)
    (out / "redraw").mkdir(parents=True, exist_ok=True)
    rows = planned(out, options.pairs, bool(options.picture) or drawn_here(out, options.room))
    report(out, rows)
    to_draw = [row for row in rows if row["route"] != "dropped"]
    if not to_draw:
        return
    room_picture = Image.open(options.picture or out / f"{options.room}-target.png").convert("RGB")
    seeds = [int(seed) for seed in options.seeds.split(",")]
    with claimed(f"redrawing {len(to_draw)} objects of {options.room}"):
        pipeline = picture.load()
        for row in to_draw:
            for seed in seeds:
                suffix = f"-s{seed}" if len(seeds) > 1 else ""
                path = out / "redraw" / f"{row['model']}{suffix}.png"
                print(draw_row(pipeline, out, room_picture, row, seed, path, options.side, style), flush=True)


if __name__ == "__main__":
    main()
