"""Luminance per region of a scene's views against the game's own shots from the same cameras: what the review page's
whole-picture brightness check cannot see (a dark far city behind a bright square still passes it).

    .venv/bin/python tools/review/brightness.py <renders> <annotate> <game shots> --match far_city/Towers \
        [--out <file.json>]

<renders> holds each view's `<view>-look.png` (tools/blender/inside/usd_views.py, renders.render_stage), <annotate>
the same views' object ids (tools/usd/annotate.py, no look needed) and <game shots> each view's `game-<view>.jpg` or
`.png` (the review page's copies, or the scene record's `game` files by their names). Two regions per view, both
measured in linear light (sRGB undone, Rec. 709 weights), the game's shot scaled to the render's size:

- the objects whose prim path holds every `--match` word (the far city's towers, say): their pixels in the render,
  the same pixels of the game's shot (same camera, so the same part of the picture);
- BANDS horizontal bands of the whole picture, for what no object names.

A region is `dark` when the scene shows under DARK_SHARE of the game's luminance there, and `unjudged` where the
game's own is under LIT_FLOOR (black sky). Prints one line per view; --out writes every number.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools/usd"))
import annotate  # noqa: E402

BANDS = 8
# The review page's share (page.DARK_SHARE): a region under half the game's luminance is dark.
DARK_SHARE = 0.5
# A region of the game's shot darker than this (linear) is night sky or shade, where a ratio says nothing.
LIT_FLOOR = 0.01
WEIGHTS = np.array([0.2126, 0.7152, 0.0722])


def linear_luminance(path, size=None):
    """A picture's luminance per pixel in linear light, 0 to 1, scaled to `size` (wide, tall) when given."""
    picture = Image.open(path).convert("RGB")
    if size is not None and picture.size != tuple(size):
        picture = picture.resize(tuple(size), Image.BILINEAR)
    values = np.asarray(picture, dtype=np.float64) / 255.0
    return np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4) @ WEIGHTS


def matched_mask(seen, words):
    """The pixels of every object whose prim path holds all the words, from one annotated view."""
    found = np.zeros(seen["ids"].shape, dtype=bool)
    for number, path in seen["paths"].items():
        if all(word in path for word in words):
            found |= seen["ids"] == number
    return found


def region(ours, theirs, pixels):
    """One region's luminance in the scene and the game, their ratio and its verdict."""
    if not pixels.any():
        return {"pixels": 0, "verdict": "unjudged"}
    scene, game = float(ours[pixels].mean()), float(theirs[pixels].mean())
    verdict = "unjudged" if game < LIT_FLOOR else "dark" if scene < DARK_SHARE * game else "lit"
    return {"pixels": int(pixels.sum()), "scene": round(scene, 4), "game": round(game, 4),
            "ratio": round(scene / game, 3) if game > 0 else None, "verdict": verdict}


def bands(shape, count=BANDS):
    """`count` horizontal bands of a picture of `shape`, top first, as masks."""
    rows = np.arange(shape[0])[:, None] * count // shape[0]
    return [np.broadcast_to(rows == band, shape) for band in range(count)]


def game_shot(shots, view):
    """The game's shot of a view in the shots folder (the review page's `game-<view>` copy), or None."""
    for name in (f"game-{view}.jpg", f"game-{view}.png", f"{view}.png", f"{view}.jpg"):
        if (pathlib.Path(shots) / name).exists():
            return pathlib.Path(shots) / name
    return None


def measure_view(render, seen, shot, words):
    """One view's regions: the matched objects' and the bands'."""
    ours = linear_luminance(render)
    theirs = linear_luminance(shot, (ours.shape[1], ours.shape[0]))
    if seen["ids"].shape != ours.shape:
        raise ValueError(f"{render}: the render is {ours.shape}, its annotation {seen['ids'].shape}")
    return {"matched": region(ours, theirs, matched_mask(seen, words)),
            "bands": [region(ours, theirs, band) for band in bands(ours.shape)]}


def measure(renders, annotated, shots, words):
    """Every view with a render, an annotation and a game shot: {view: regions}."""
    found = {}
    for render in sorted(pathlib.Path(renders).glob("*-look.png")):
        view = render.name.removesuffix("-look.png")
        shot = game_shot(shots, view)
        if shot is None or not (pathlib.Path(annotated) / f"{view}-passes.npz").exists():
            continue
        found[view] = measure_view(render, annotate.load(annotated, view), shot, words)
    return found


def line(view, regions):
    """One view's summary line."""
    matched = regions["matched"]
    darkest = min((band for band in regions["bands"] if band["verdict"] != "unjudged"),
                  key=lambda band: band["ratio"], default=None)
    head = (f"{view}: matched {matched['scene']:.4f} vs game {matched['game']:.4f} (x{matched['ratio']}, "
            f"{matched['verdict']})" if matched["pixels"] else f"{view}: nothing matched")
    return head + (f"; darkest band x{darkest['ratio']}" if darkest else "")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("renders", type=pathlib.Path)
    parser.add_argument("annotate", type=pathlib.Path)
    parser.add_argument("shots", type=pathlib.Path)
    parser.add_argument("--match", required=True, help="words a matched object's prim path holds, by slash")
    parser.add_argument("--out", type=pathlib.Path)
    arguments = parser.parse_args()
    found = measure(arguments.renders, arguments.annotate, arguments.shots, arguments.match.split("/"))
    if not found:
        raise SystemExit("no view has a render, an annotation and a game shot")
    for view, regions in found.items():
        print(line(view, regions))
    if arguments.out:
        arguments.out.write_text(json.dumps(found, indent=1))


if __name__ == "__main__":
    main()
