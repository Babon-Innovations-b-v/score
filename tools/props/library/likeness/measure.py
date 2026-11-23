"""The look-alike check's measures (#155): a surface's map material and its fitted recipe rendered on the same swatch
under the same light and camera (inside/likeness.py), compared view by view, and the recipe refined from what they
show.

    view_measures(map_picture, recipe_picture)   {delta_e, lightness, highlight, detail, ...} for one view
    passes(measured)                             every bound held in that view
    likeness(views, algorithm)                   {"measures": {view: ...}, "pass": ..., "algorithm": ...}
    ranking(views)                               (bounds broken, how far): a round's place among a surface's rounds
    highlight_of(views)                          the views' mean highlight gap
    refined(spec, views, earlier)                the recipe's spec moved toward the maps' look

The measures, each over the swatch's pixels both pictures cover:
- delta_e: the mean CIE76 colour difference of CELL-texel cells (each cell's mean Lab), so a pattern's grain does not
  count, the mean colour per region does;
- lightness: the distance between the two pictures' lightness histograms (the mean gap between their quantiles, L
  units), which roughness, metal and a pattern's spread all move;
- highlight: the gap between the two pictures' brightest lightness (its HIGHLIGHT_QUANTILE), the highlight lobe
  roughness and metal shape;
- detail: the recipe's high-pass lightness energy over the maps' (relief and pattern), 1 when both are under
  DETAIL_FLOOR.
The bounds are the check's own (a recipe drawn beside its maps under one light): they are first set here and settled
by the first run over the set, never loosened to pass. Render settings are check-only: a recipe that ships is the
recipe, never these pictures. Standard library and numpy (Pillow to read).
"""
import numpy as np

import colour
import fit

CELL = 16  # texels a side of a colour cell
CELL_COVER = 0.75  # the share of a cell the swatch must cover for it to count
QUANTILES = np.linspace(0.02, 0.98, 49)
HIGHLIGHT_QUANTILE = 0.99
DETAIL_REACH = 3  # texels each side of the high-pass's blur
DETAIL_FLOOR = 0.5  # L units: an energy under this on both sides is no detail to compare
# The bounds (the check's, #155, 2026-11-22). A mean cell colour difference of 10 is a colour plainly of the same name
# and shade side by side (the bake check's 20 turned gold silver; finish_parts.COLOUR_DELTA_E, 32, picks a token
# against a close-up, a looser question); lightness and highlight in L units; detail as the plan's ratio.
DELTA_E_BOUND = 10.0
LIGHTNESS_BOUND = 8.0
HIGHLIGHT_BOUND = 12.0
DETAIL_LOW, DETAIL_HIGH = 0.8, 1.25
# The refinement's steps: the recipe's roughness moved by the highlight gap over this many L units, at most
# ROUGHNESS_STEP a round; its bump and contrast scaled by the detail ratio, within DETAIL_STEP either way.
HIGHLIGHT_PER_ROUGHNESS = 100.0
ROUGHNESS_STEP = 0.2
DETAIL_STEP = 2.0
COLOUR_SETTINGS = ("colour", "second", "bare", "dirt_colour")
# The refinement grows a bump no higher than this share of its pattern's size (its fit's own bump stands): a tread
# plate's bump doubled each round to 0.275 m on 1 cm lugs, 2026-11-23.
RELIEF_ASPECT = 0.25


def picture(path):
    """A rendered picture as (Lab pixels, covered mask): its RGB read as sRGB, its alpha the swatch."""
    from PIL import Image
    with Image.open(path) as opened:
        values = np.asarray(opened.convert("RGBA"), dtype=float) / 255.0
    return colour.lab(colour.linear(values[..., :3])), values[..., 3] > 0.5


def cell_means(lightness_lab, covered):
    """Each CELL-texel cell's mean Lab where the swatch covers CELL_COVER of it: (cells, 3)."""
    rows, columns = covered.shape[0] // CELL, covered.shape[1] // CELL
    means = []
    for row in range(rows):
        for column in range(columns):
            window = (slice(row * CELL, (row + 1) * CELL), slice(column * CELL, (column + 1) * CELL))
            if covered[window].mean() >= CELL_COVER:
                means.append(lightness_lab[window][covered[window]].mean(axis=0))
    return np.array(means).reshape(-1, 3)


def high_pass_energy(lightness, covered):
    """The rms of lightness less its local mean, over covered texels whose whole blur reach is covered."""
    reach = DETAIL_REACH
    blurred, inside = lightness, covered.astype(float)
    for axis in (0, 1):
        blurred = sum(np.roll(blurred, shift, axis=axis) for shift in range(-reach, reach + 1)) / (2 * reach + 1)
        inside = sum(np.roll(inside, shift, axis=axis) for shift in range(-reach, reach + 1)) / (2 * reach + 1)
    kept = inside > 0.999
    return float(np.sqrt(np.mean((lightness - blurred)[kept] ** 2))) if kept.any() else 0.0


def view_measures(map_path, recipe_path):
    """One view's measures between the map material's picture and the recipe's, with each side's mean Lab and
    highlight for the refinement."""
    map_lab, map_covered = picture(map_path)
    recipe_lab, recipe_covered = picture(recipe_path)
    covered = map_covered & recipe_covered
    if not covered.any():
        raise ValueError(f"{map_path} and {recipe_path} share no swatch pixels")
    map_cells, recipe_cells = cell_means(map_lab, covered), cell_means(recipe_lab, covered)
    apart = np.linalg.norm(map_cells - recipe_cells, axis=1)
    map_light, recipe_light = map_lab[..., 0][covered], recipe_lab[..., 0][covered]
    map_detail = high_pass_energy(map_lab[..., 0], covered)
    recipe_detail = high_pass_energy(recipe_lab[..., 0], covered)
    detail = 1.0 if max(map_detail, recipe_detail) < DETAIL_FLOOR else recipe_detail / max(map_detail, 1e-6)
    return {"delta_e": round(float(apart.mean()) if apart.size else float("inf"), 3),
            "lightness": round(float(np.abs(np.quantile(map_light, QUANTILES) -
                                            np.quantile(recipe_light, QUANTILES)).mean()), 3),
            "highlight": round(float(np.quantile(recipe_light, HIGHLIGHT_QUANTILE) -
                                     np.quantile(map_light, HIGHLIGHT_QUANTILE)), 3),
            "detail": round(float(detail), 3),
            "map_lab": [round(float(value), 3) for value in map_lab[covered].mean(axis=0)],
            "recipe_lab": [round(float(value), 3) for value in recipe_lab[covered].mean(axis=0)]}


def passes(measured):
    """Whether one view's measures all hold their bounds."""
    return (measured["delta_e"] <= DELTA_E_BOUND and measured["lightness"] <= LIGHTNESS_BOUND
            and abs(measured["highlight"]) <= HIGHLIGHT_BOUND and DETAIL_LOW <= measured["detail"] <= DETAIL_HIGH)


def likeness(views, algorithm):
    """The likeness block an adopted surface's record carries: every view's measures, whether every view passed, and
    the recipe algorithm's address the recipe is drawn by."""
    return {"measures": views, "pass": bool(views) and all(passes(measured) for measured in views.values()),
            "algorithm": algorithm}


def breach(measured):
    """How far each of one view's measures lies past its bound, as a share of the bound (0 where it holds)."""
    detail = measured["detail"]
    return {"delta_e": max(0.0, measured["delta_e"] - DELTA_E_BOUND) / DELTA_E_BOUND,
            "lightness": max(0.0, measured["lightness"] - LIGHTNESS_BOUND) / LIGHTNESS_BOUND,
            "highlight": max(0.0, abs(measured["highlight"]) - HIGHLIGHT_BOUND) / HIGHLIGHT_BOUND,
            "detail": max(0.0, DETAIL_LOW - detail) / DETAIL_LOW + max(0.0, detail - DETAIL_HIGH) / DETAIL_HIGH}


def ranking(views):
    """A round's place among a surface's rounds, the smaller the nearer its maps: (how many bounds it breaks over
    every view, the sum of how far, each a share of its bound); (0, 0.0) is a pass."""
    shares = [share for measured in views.values() for share in breach(measured).values()]
    return sum(1 for share in shares if share > 0), round(float(sum(shares)), 6)


def highlight_of(views):
    """The views' mean highlight gap (the recipe's brightest lightness less the maps')."""
    return float(np.mean([each["highlight"] for each in views.values()]))


def roughness_step(roughness, highlight, earlier=None):
    """The roughness's move toward the maps' highlight: with an earlier round ({"roughness", "highlight"}) at another
    roughness that moved the highlight, a secant step to where the gap would close (a highlight is not monotone in
    roughness under the studio's small suns: a dim one can want a rougher lobe, and the old fixed rule walked
    glossy glass from 0.05 to 0 while the gap held at -12 to -20, 2026-11-23); else the first round's rule, a
    recipe's highlight too bright: rougher. At most ROUGHNESS_STEP either way."""
    step = highlight / HIGHLIGHT_PER_ROUGHNESS
    if earlier and earlier["roughness"] != roughness and earlier["highlight"] != highlight:
        slope = (highlight - earlier["highlight"]) / (roughness - earlier["roughness"])
        step = -highlight / slope
    return float(np.clip(step, -ROUGHNESS_STEP, ROUGHNESS_STEP))


# Halvings of the chroma scale that bring a shifted colour into gamut.
GAMUT_HALVINGS = 30


def in_gamut(target):
    """A Lab colour brought into linear RGB's gamut keeping its lightness (within 0..100) and its hue: its chroma
    scaled down as little as it takes (a per-channel clip turned an anodized orange raised in lightness yellow,
    1, 1, 0.02, 2026-11-23)."""
    lightness = float(np.clip(target[0], 0.0, 100.0))

    def fits(scale):
        light = colour.linear_of_lab_unclipped(np.array([lightness, target[1] * scale, target[2] * scale]))
        return bool(np.all(light >= -1e-9) and np.all(light <= 1.0 + 1e-9))

    low, high = 0.0, 1.0
    if not fits(high):
        for _ in range(GAMUT_HALVINGS):
            middle = (low + high) / 2.0
            low, high = (middle, high) if fits(middle) else (low, middle)
        high = low
    return np.array([lightness, target[1] * high, target[2] * high])


def shifted(linear_colour, shift):
    """A linear colour moved by a Lab shift, brought into gamut by its chroma (in_gamut)."""
    moved = in_gamut(colour.lab(np.asarray(linear_colour)) + shift)
    return [round(float(value), 5) for value in colour.linear_of_lab(moved)]


def views_apart(views):
    """The close view's detail ratio over the overview's when they disagree past the detail bounds' own width (one
    view's fine detail short while the other's coarse detail is over: no amplitude can pass both), else None."""
    if "close" not in views or "overview" not in views:
        return None
    apart = views["close"]["detail"] / max(views["overview"]["detail"], 1e-6)
    return apart if not DETAIL_LOW <= apart <= DETAIL_HIGH else None


def refined(spec, views, earlier=None):
    """The spec moved toward the maps' look from every view's measures: its colours by the mean Lab gap, its
    roughness by the highlight gap (roughness_step, from the `earlier` round's {"roughness", "highlight"} when there
    is one), its bump (grown no higher than RELIEF_ASPECT of its pattern size), contrast and scratches by the detail
    ratio (a contrast already at 1 moving its second shade further off instead); its pattern size by the close view's
    detail over the overview's when they disagree (views_apart), its bump then by the close view's."""
    measures = list(views.values())
    shift = np.mean([np.subtract(each["map_lab"], each["recipe_lab"]) for each in measures], axis=0)
    moved = dict(spec)
    for name in COLOUR_SETTINGS:
        if name in moved:
            moved[name] = shifted(moved[name], shift)
    step = roughness_step(spec["roughness"], highlight_of(views), earlier)
    moved["roughness"] = round(float(np.clip(spec["roughness"] + step, 0.0, 1.0)), 4)
    detail = float(np.mean([each["detail"] for each in measures]))
    size_setting = fit.SIZE_SETTING.get(moved["recipe"])
    apart = views_apart(views)
    if apart is not None and size_setting in moved:
        # The views disagree: the pattern's size is wrong, not its height. A close view short of the overview's
        # detail wants a finer pattern; the height then follows the close view alone.
        moved[size_setting] = round(float(moved[size_setting] * np.clip(apart, 1.0 / DETAIL_STEP, DETAIL_STEP)), 6)
        detail = views["close"]["detail"]
    scale = float(np.clip(1.0 / max(detail, 1e-6), 1.0 / DETAIL_STEP, DETAIL_STEP))
    if "bump" in moved:
        grown = moved["bump"] * scale
        size = moved.get(fit.SIZE_SETTING.get(moved["recipe"], ""))
        if size:
            grown = min(grown, max(moved["bump"], size * RELIEF_ASPECT))
        moved["bump"] = round(float(grown), 6)
    if moved.get("contrast") == 1.0 and scale > 1.0 and "second" in moved:  # contrast spent: the shades apart
        apart = colour.lab(np.asarray(moved["second"])) - colour.lab(np.asarray(moved["colour"]))
        moved["second"] = [round(float(value), 5) for value in colour.linear_of_lab(
            in_gamut(colour.lab(np.asarray(moved["colour"])) + apart * scale))]
    for name in ("contrast", "scratches"):
        if name in moved:
            moved[name] = round(float(min(moved[name] * scale, 1.0)), 4)
    return moved
