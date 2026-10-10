"""The style measure (PRD #1, the paper's style-coherence gap): do a place's made models share one style? Read from the
review pages' renders of each made model (Workbench, one studio light, no shadows, on one grey: every model of every
place is drawn the same way, so what differs between two renders is the model).

    .venv/bin/python tools/review/style.py pairs <review root> <work folder>      # the silhouettes and pairs.json
    .venv/bin/python tools/props/cloud/similar.py <work>/pairs.json <work>/likeness.json --who "<session>"
    .venv/bin/python tools/review/style.py report <review root> <work folder>     # <work>/style.json and style.txt

<review root> holds one review page per place (<place>/models/<model>--made--now.png, tools/review/page.py). Three
readings, each per place:

- **Palette fit.** Each model's coloured pixels (chroma at least CHROMATIC; a grey or a steel fits any palette at some
  brightness) against its place's library palette (tools/props/library/sweep.py's: every colour the place's surfaces
  bake to), each palette colour taken at every brightness the light can give it (SHADES, since a render is the
  surface's colour times its light): the share within sweep.NEAR (CIE76). A model with fewer than MIN_CHROMATIC
  coloured pixels reads as None. How much the places' coloured palettes share (`palette_overlap`) says whether the
  fit can tell one place's style from another's at all.
- **Lightness spread.** The spread (standard deviation) of the models' median L* within a place, against the spread
  over the whole world.
- **Feature likeness.** DINOv2's likeness (the cosine of its class tokens, similar.py, run on a rented machine) of
  every pair of models within a place, against pairs across places (ACROSS partners a model, drawn with a fixed seed).
  DINOv2 sees what an object is as well as how it looks, so the same pairs are compared again as plain silhouettes
  (black on white, the shape alone); the style gap is the colour renders' within-minus-across less the silhouettes'.

A model a place reuses from another (the hub's tools in the workshop) is the same render twice: such copies
(COPY_TOLERANCE) are left out of the likeness, which would otherwise count one model as two places agreeing. A place
with one model has no pair within it and reads as None. Nothing here judges a model good or bad: the numbers
are what the renders show, to be read beside the creator's reviews.
"""
import argparse
import json
import pathlib
import random
import sys

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "tools/props/library"))
import records  # noqa: E402
import sweep  # noqa: E402

SUFFIX = "--made--now.png"
# The brightness a surface's colour can take under the studio light: shadowed sides to lit faces with their sheen.
SHADES = np.geomspace(0.25, 1.6, 14)
# How far (0..255, per channel together) a pixel must lie from the background's grey to be the model's.
BACKGROUND_TOLERANCE = 12.0
CHROMATIC = 8.0
MIN_CHROMATIC = 100
SAMPLE = 3000
# Two renders whose greys (64 x 64) differ by less than this on average (0..255) are one model shown twice.
COPY_TOLERANCE = 0.5
ACROSS = 8
SEED = 7


def model_renders(root):
    """Every place's made-model renders under the review root: {place: {model: path}}, places with none left out."""
    found = {}
    for path in sorted(pathlib.Path(root).glob(f"*/models/*{SUFFIX}")):
        found.setdefault(path.parents[1].name, {})[path.name.removesuffix(SUFFIX)] = path
    return found


def foreground(picture):
    """Which pixels of an RGB render (h, w, 3, 0..255) are the model's: those away from the grey in its corners."""
    picture = picture.astype(np.float64)
    corners = np.concatenate([picture[:8, :8], picture[:8, -8:], picture[-8:, :8], picture[-8:, -8:]]).reshape(-1, 3)
    distance = np.linalg.norm(picture - np.median(corners, axis=0), axis=2)
    return distance > BACKGROUND_TOLERANCE


def drawn_pixels(path):
    """The render's model pixels as sRGB (n, 3, 0..255)."""
    picture = np.asarray(Image.open(path).convert("RGB"))
    return picture[foreground(picture)]


def shaded(palette_lab):
    """A palette (L*a*b*) at every brightness in SHADES, as L*a*b*."""
    linear = lab_to_linear(palette_lab)
    lit = np.clip(linear[None, :, :] * SHADES[:, None, None], 0.0, 1.0).reshape(-1, 3)
    return sweep.lab(lit)


def lab_to_linear(points):
    """CIE L*a*b* (D65) back to linear RGB, the inverse of sweep.lab."""
    bent_y = (points[:, 0] + 16) / 116
    bent = np.stack([bent_y + points[:, 1] / 500, bent_y, bent_y - points[:, 2] / 200], 1)
    xyz = np.where(bent > 0.206893, bent ** 3, (bent - 16 / 116) / 7.787) * np.array([0.9505, 1.0, 1.089])
    matrix = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    return xyz @ np.linalg.inv(matrix).T


def palette_share(points, palette):
    """The share of points (L*a*b*) within sweep.NEAR of any palette colour."""
    from scipy.spatial import cKDTree
    distance, _ = cKDTree(palette).query(points)
    return float(np.mean(distance < sweep.NEAR))


def sampled(pixels, count=SAMPLE):
    """At most count of the pixels, drawn with a fixed seed."""
    if len(pixels) <= count:
        return pixels
    return pixels[np.random.default_rng(SEED).choice(len(pixels), count, replace=False)]


def chroma(points):
    """Each L*a*b* point's chroma."""
    return np.hypot(points[:, 1], points[:, 2])


def model_colour(path, palette):
    """One render's colour readings: its share of coloured pixels, their fit to the place's shaded palette (None when
    too few) and its median L*."""
    points = sweep.lab(sweep.linear_of(sampled(drawn_pixels(path))))
    coloured = points[chroma(points) >= CHROMATIC]
    fit = round(palette_share(coloured, palette), 3) if len(coloured) >= MIN_CHROMATIC else None
    return {"coloured": round(len(coloured) / len(points), 3), "fit": fit,
            "lightness": round(float(np.median(points[:, 0])), 1)}


def place_colour(models):
    """A place's colour readings from its models': the median share of coloured pixels, the median fit of those that
    have enough, and the spread of the models' median L*."""
    fits = [entry["fit"] for entry in models.values() if entry["fit"] is not None]
    lightness = [entry["lightness"] for entry in models.values()]
    return {"models": len(models), "coloured": round(float(np.median([entry["coloured"] for entry in models.values()])), 3),
            "fitted": len(fits), "fit": round(float(np.median(fits)), 3) if fits else None,
            "lightness_spread": round(float(np.std(lightness)), 1) if len(lightness) > 1 else None}


def palette_overlap(palettes):
    """The median, over ordered pairs of places, of the share of one place's coloured palette colours within
    sweep.NEAR of the other's: near 1 when the places draw on one shared palette."""
    coloured = {place: palette[chroma(palette) >= CHROMATIC] for place, palette in palettes.items()}
    shares = [palette_share(coloured[first], coloured[second]) for first in coloured for second in coloured
              if first != second]
    return round(float(np.median(shares)), 3) if shares else None


def silhouette(path, out):
    """The render's shape alone, black on white, written to out."""
    picture = np.asarray(Image.open(path).convert("RGB"))
    Image.fromarray(np.where(foreground(picture), 0, 255).astype(np.uint8)).convert("RGB").save(out)


def pair_names(renders):
    """The pairs to compare, as (first, second) of "place/model" names: every pair within a place, and ACROSS
    partners from other places for each model, drawn with SEED."""
    names = [f"{place}/{model}" for place, models in renders.items() for model in models]
    chosen = random.Random(SEED)
    pairs = set()
    for first in names:
        place = first.split("/")[0]
        pairs.update(tuple(sorted((first, second))) for second in names if second > first and second.startswith(f"{place}/"))
        others = [second for second in names if not second.startswith(f"{place}/")]
        pairs.update(tuple(sorted((first, second))) for second in chosen.sample(others, min(ACROSS, len(others))))
    return sorted(pairs)


def write_pairs(root, work):
    """The silhouettes under work/shapes and work/pairs.json for similar.py: {"colour|a|b" or "shape|a|b": [a, b]}."""
    renders = model_renders(root)
    shapes = pathlib.Path(work) / "shapes"
    shapes.mkdir(parents=True, exist_ok=True)
    shape_of = {}
    for place, models in renders.items():
        for model, path in models.items():
            shape_of[f"{place}/{model}"] = shapes / f"{place}--{model}.png"
            silhouette(path, shape_of[f"{place}/{model}"])
    pairs = {}
    for first, second in pair_names(renders):
        colour = [str(renders[name.split("/")[0]][name.split("/")[1]]) for name in (first, second)]
        pairs[f"colour|{first}|{second}"] = colour
        pairs[f"shape|{first}|{second}"] = [str(shape_of[first]), str(shape_of[second])]
    (pathlib.Path(work) / "pairs.json").write_text(json.dumps(pairs, indent=1))
    return pairs


def copies(renders):
    """The pairs of "place/model" names whose renders are one model shown twice, as a set of sorted pairs."""
    greys = {f"{place}/{model}": np.asarray(Image.open(path).convert("L").resize((64, 64)), dtype=np.float64)
             for place, models in renders.items() for model, path in models.items()}
    names = sorted(greys)
    return {(first, second) for index, first in enumerate(names) for second in names[index + 1:]
            if np.abs(greys[first] - greys[second]).mean() < COPY_TOLERANCE}


def without_copies(likeness, copied):
    """The likenesses with every pair of copies left out."""
    return {name: value for name, value in likeness.items() if tuple(sorted(name.split("|")[1:])) not in copied}


def likeness_split(likeness, place, kind):
    """The likenesses of one kind ("colour" or "shape") of the pairs within a place and of its pairs across."""
    within, across = [], []
    for name, value in likeness.items():
        what, first, second = name.split("|")
        mine = [part.split("/")[0] == place for part in (first, second)]
        if what != kind or not any(mine):
            continue
        (within if all(mine) else across).append(value)
    return within, across


def world_features(likeness):
    """The whole world's feature readings: every pair within a place against every pair across, per kind, and the
    style gap from them."""
    found = {}
    for kind in ("colour", "shape"):
        within, across = [], []
        for name, value in likeness.items():
            what, first, second = name.split("|")
            if what == kind:
                (within if first.split("/")[0] == second.split("/")[0] else across).append(value)
        found[kind] = {"within": round(float(np.mean(within)), 3), "across": round(float(np.mean(across)), 3),
                       "pairs": [len(within), len(across)]}
    found["style_gap"] = round((found["colour"]["within"] - found["colour"]["across"])
                               - (found["shape"]["within"] - found["shape"]["across"]), 3)
    return found


def place_features(likeness, place):
    """A place's feature readings: mean likeness within and across, for colour renders and silhouettes, and the style
    gap (colour's within-minus-across less the silhouettes'); None where the place has no pair within."""
    found = {}
    for kind in ("colour", "shape"):
        within, across = likeness_split(likeness, place, kind)
        found[kind] = {"within": round(float(np.mean(within)), 3) if within else None,
                       "across": round(float(np.mean(across)), 3) if across else None, "pairs": len(within)}
    gaps = [found[kind]["within"] - found[kind]["across"] for kind in ("colour", "shape")
            if found[kind]["within"] is not None]
    found["style_gap"] = round(gaps[0] - gaps[1], 3) if len(gaps) == 2 else None
    return found


def palettes_of(places):
    """Each place's library palette in L*a*b* ({place: palette}), unshaded."""
    return {place: sweep.palette(records.place_key(place)) for place in places}


def report(root, work):
    """The per-place readings in work/style.json (and the models' own in work/style-models.json); returns them."""
    work = pathlib.Path(work)
    renders = model_renders(root)
    palettes = palettes_of(renders)
    colours = {place: {model: model_colour(path, shaded(palettes[place])) for model, path in models.items()}
               for place, models in renders.items()}
    likeness_path = work / "likeness.json"
    copied = copies(renders)
    likeness = without_copies(json.loads(likeness_path.read_text()), copied) if likeness_path.exists() else None
    places = {place: dict(place_colour(colours[place]),
                          **({"features": place_features(likeness, place)} if likeness else {}))
              for place in renders}
    every_lightness = [entry["lightness"] for models in colours.values() for entry in models.values()]
    found = {"places": places, "world_lightness_spread": round(float(np.std(every_lightness)), 1),
             "palette_overlap": palette_overlap(palettes), "models": len(every_lightness),
             "copies": sorted(copied), "likeness": bool(likeness),
             "features": world_features(likeness) if likeness else None}
    (work / "style.json").write_text(json.dumps(found, indent=1))
    (work / "style-models.json").write_text(json.dumps(colours, indent=1))
    return found


def cell(value, digits=3):
    """A table cell: the number, or a dash for None."""
    return "-" if value is None else f"{value:.{digits}f}"


def table(found):
    """The per-place readings as plain text lines."""
    lines = [f"{'place':12} {'n':>3} {'colrd':>6} {'fitted':>6} {'fit':>6} {'L* sd':>6} "
             f"{'col in':>6} {'col out':>7} {'shp in':>6} {'shp out':>7} {'gap':>6}"]
    for place, entry in sorted(found["places"].items()):
        features = entry.get("features", {})
        cells = [features.get(kind, {}).get(side) for kind in ("colour", "shape") for side in ("within", "across")]
        cells.append(features.get("style_gap"))
        lines.append(f"{place:12} {entry['models']:>3} {cell(entry['coloured']):>6} {entry['fitted']:>6} "
                     f"{cell(entry['fit']):>6} {cell(entry['lightness_spread'], 1):>6} "
                     + " ".join(f"{cell(value):>6}" for value in cells))
    lines.append(f"world: {found['models']} models ({len(found['copies'])} pairs of copies left out), L* sd {found['world_lightness_spread']}, coloured palettes shared "
                 f"{found['palette_overlap']}")
    if found["features"]:
        world = found["features"]
        lines.append(f"world likeness: colour {world['colour']['within']} within, {world['colour']['across']} across; "
                     f"shape {world['shape']['within']} within, {world['shape']['across']} across; "
                     f"gap {world['style_gap']} (pairs within, across: {world['colour']['pairs']})")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("step", choices=("pairs", "report"))
    parser.add_argument("root", type=pathlib.Path, help="the review root, one page folder per place")
    parser.add_argument("work", type=pathlib.Path, help="the measure's own folder")
    options = parser.parse_args()
    options.work.mkdir(parents=True, exist_ok=True)
    if options.step == "pairs":
        pairs = write_pairs(options.root, options.work)
        print(f"style: {len(pairs)} pairs, {options.work / 'pairs.json'}")
        return
    found = report(options.root, options.work)
    (options.work / "style.txt").write_text("\n".join(table(found)) + "\n")
    print(f"style: {len(found['places'])} places, {found['models']} models, likeness "
          f"{'in' if found['likeness'] else 'not yet run'}; {options.work / 'style.json'}, {options.work / 'style.txt'}")


if __name__ == "__main__":
    main()
