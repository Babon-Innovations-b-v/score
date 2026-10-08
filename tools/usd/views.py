"""The Blender adapter's check: load a place's stage in Blender (no window) and render it from the cameras of the
place's recorded game shots, then measure how well the two agree.

    .venv/bin/python tools/usd/views.py wreck <stage.usda> --shots <folder of the game's shots> --out <folder>

The views are the game's bench views of the place (2099's tools/perf/place.gd, `wreck wake`, `wreck side` and
`wreck home`): an eye and an aim in the base seat's flat numbers, each laid on the 220 m Moon over the ground there,
1.7 m up, with a 73.74 degree lens across the picture. They are turned here into the place's own frame (the
wreck's seat, as Wreck.seat() turns it: 55 m from the base's middle on the bearing (-30, 100), its along towards
the base). The Moon's hills are not in the stage, so the ground is taken as level with the place's middle.

Agreement is measured where both pictures show the sky: above the stage's level ground in Blender's picture, an
object pixel is one Blender draws an object on, and in the game's shot one brighter than the black sky. Per view
it prints the share of Blender's object pixels the game also shows something on (`held`) and the two masks'
intersection over union (`iou`), and writes <view>-side.png (the game's shot beside Blender's) and
<view>-overlay.png (Blender's outline over the game's shot). The game also draws the base on the horizon and its
ink lines, which Blender does not, so a perfect match does not read 1.0.
"""
import argparse
import json
import pathlib
import subprocess
import sys

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

REPO = pathlib.Path(__file__).resolve().parents[2]
SESSION = REPO / "tools/blender/session.py"
INSIDE = REPO / "tools/blender/inside/usd_views.py"
SIZE = (960, 540)

MOON_RADIUS = 220.0
EYE_HEIGHT = 1.7
LENS = 73.74
WRECK_BEARING = (-30.0, 100.0)
WRECK_FROM_THE_BASE = 55.0
# name: (eye, aim) in the base seat's flat numbers, (across, up over the ground, along).
WRECK_VIEWS = {
    "wreck wake": ((-23.3, EYE_HEIGHT, 56.7), (3.575, 1.6, 6.192)),
    "wreck side": ((-28.4, EYE_HEIGHT, 51.6), (-16.7, 1.0, 55.6)),
    "wreck home": ((-9.0, EYE_HEIGHT, 42.0), (-16.1, 1.2, 53.8)),
}
# A game pixel brighter than this (0 to 1, its brightest channel) is not black sky: the sky reads 0.004 and the
# hull in shadow 0.01 to 0.07 in `wreck side`. Stars are opened away.
SKY_LEVEL = 0.015
STAR_SIZE = 5


# --- the cameras --------------------------------------------------------------------------------------------------

def moon_centre():
    """The Moon's middle, with the base's middle at the origin, its out along +y, across +x and along +z."""
    return np.array([0.0, -MOON_RADIUS, 0.0])


def on_the_ground(flat, lift):
    """A point given in the base seat's flat numbers laid on the ball (level ground), `lift` metres up."""
    out = np.array([flat[0], 0.0, flat[2]]) - moon_centre()
    out /= np.linalg.norm(out)
    return moon_centre() + out * (MOON_RADIUS + lift), out


def wreck_seat():
    """The wreck's middle and its frame (across, out, along as columns): the base's middle walked
    WRECK_FROM_THE_BASE over the ball on the bearing, its along turned towards the base."""
    going = np.array([WRECK_BEARING[0], 0.0, WRECK_BEARING[1]])
    going /= np.linalg.norm(going)
    turn = WRECK_FROM_THE_BASE / MOON_RADIUS
    out = np.array([0.0, 1.0, 0.0]) * np.cos(turn) + going * np.sin(turn)
    middle = moon_centre() + out * MOON_RADIUS
    home = -middle - out * np.dot(-middle, out)
    along = home / np.linalg.norm(home)
    return middle, np.column_stack([np.cross(out, along), out, along])


def place_view(name, eye_flat, aim_flat):
    """One game view in the place's own frame: eye, aim and up, and the lens."""
    middle, frame = wreck_seat()
    eye, up = on_the_ground(eye_flat, eye_flat[1])
    aim, _ = on_the_ground(aim_flat, aim_flat[1])
    return {"name": name.replace(" ", "-"), "fov": LENS, "eye": (frame.T @ (eye - middle)).tolist(),
            "aim": (frame.T @ (aim - middle)).tolist(), "up": (frame.T @ up).tolist()}


# --- Blender ------------------------------------------------------------------------------------------------------

def render_in_blender(stage, views, out):
    """The views rendered by Blender in a batch job (session.py: no window, the machine's lock, memory floor)."""
    out.mkdir(parents=True, exist_ok=True)
    spec = out / "views.json"
    spec.write_text(json.dumps({"size": list(SIZE), "views": views}, indent=1))
    command = [sys.executable, str(SESSION), "batch", str(INSIDE), str(stage), str(spec), str(out)]
    if subprocess.run(command).returncode != 0:
        raise RuntimeError("the Blender batch failed; its output is above")


# --- the comparison -----------------------------------------------------------------------------------------------

def game_shot(path):
    return np.asarray(Image.open(path).convert("RGB").resize(SIZE, Image.LANCZOS), dtype=np.float64) / 255


def something_drawn(shot):
    """Where the game's shot is brighter than the black sky, stars opened away."""
    bright = shot.max(axis=2) > SKY_LEVEL
    return ndimage.binary_opening(bright, structure=np.ones((STAR_SIZE, STAR_SIZE)))


def above_the_ground(ground):
    """Where Blender's level ground is not, seen with nothing in front of it: every pixel above the highest ground
    pixel of its column."""
    first = np.where(ground.any(axis=0), ground.argmax(axis=0), ground.shape[0])
    return np.arange(ground.shape[0])[:, None] < first[None, :]


def agreement(blender_objects, game_objects, region):
    ours, theirs = blender_objects & region, game_objects & region
    union = (ours | theirs).sum()
    return {"held": round(float((ours & theirs).sum() / max(ours.sum(), 1)), 3),
            "iou": round(float((ours & theirs).sum() / max(union, 1)), 3),
            "blender_pixels": int(ours.sum()), "game_pixels": int(theirs.sum())}


def side_by_side(shot, look, path):
    joined = np.concatenate([shot, look], axis=1)
    Image.fromarray((joined * 255).astype(np.uint8)).save(path)


def overlay(shot, mask, path):
    """Blender's object outline drawn in orange over the game's shot."""
    picture = Image.fromarray((shot * 255).astype(np.uint8))
    outline = Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.FIND_EDGES)
    edges = np.asarray(outline.filter(ImageFilter.MaxFilter(3))) > 0
    drawn = np.asarray(picture).copy()
    drawn[edges] = (255, 140, 0)
    Image.fromarray(drawn).save(path)


def compare(view, shots, out):
    shot = game_shot(shots / f"{view['name'].replace('-', ' ')}.png")
    look = np.asarray(Image.open(out / f"{view['name']}-look.png").convert("RGB"), dtype=np.float64) / 255
    mask = np.asarray(Image.open(out / f"{view['name']}-mask.png"))[:, :, 3] > 127
    ground = np.asarray(Image.open(out / f"{view['name']}-ground.png"))[:, :, 3] > 127
    side_by_side(shot, look, out / f"{view['name']}-side.png")
    overlay(shot, mask, out / f"{view['name']}-overlay.png")
    return agreement(mask, something_drawn(shot), above_the_ground(ground))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("place", choices=["wreck"])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("--shots", required=True, type=pathlib.Path)
    parser.add_argument("--out", required=True, type=pathlib.Path)
    arguments = parser.parse_args()
    views = [place_view(name, *ends) for name, ends in WRECK_VIEWS.items()]
    render_in_blender(arguments.stage.resolve(), views, arguments.out)
    results = {view["name"]: compare(view, arguments.shots, arguments.out) for view in views}
    (arguments.out / "agreement.json").write_text(json.dumps(results, indent=1))
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
