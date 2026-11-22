"""The look-alike check's measures (#155): a surface's map material and its fitted recipe rendered on the same swatch
under the same light and camera (inside/likeness.py), compared view by view, and the recipe refined from what they
show.

    view_measures(map_picture, recipe_picture)   {delta_e, lightness, highlight, detail, ...} for one view
    passes(measured)                             every bound held in that view
    likeness(views, algorithm)                   {"measures": {view: ...}, "pass": ..., "algorithm": ...}
    refined(spec, views)                         the recipe's spec moved toward the maps' look

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


def shifted(linear_colour, shift):
    """A linear colour moved by a Lab shift."""
    return [round(float(value), 5) for value in colour.linear_of_lab(colour.lab(np.asarray(linear_colour)) + shift)]


def refined(spec, views):
    """The spec moved toward the maps' look from every view's measures: its colours by the mean Lab gap, its
    roughness by the highlight gap (a recipe's highlight too bright: rougher), its bump and contrast by the detail
    ratio."""
    measures = list(views.values())
    shift = np.mean([np.subtract(each["map_lab"], each["recipe_lab"]) for each in measures], axis=0)
    moved = dict(spec)
    for name in COLOUR_SETTINGS:
        if name in moved:
            moved[name] = shifted(moved[name], shift)
    highlight = float(np.mean([each["highlight"] for each in measures]))
    step = float(np.clip(highlight / HIGHLIGHT_PER_ROUGHNESS, -ROUGHNESS_STEP, ROUGHNESS_STEP))
    moved["roughness"] = round(float(np.clip(spec["roughness"] + step, 0.0, 1.0)), 4)
    detail = float(np.mean([each["detail"] for each in measures]))
    scale = float(np.clip(1.0 / max(detail, 1e-6), 1.0 / DETAIL_STEP, DETAIL_STEP))
    if "bump" in moved:
        moved["bump"] = round(float(moved["bump"] * scale), 6)
    if "contrast" in moved:
        moved["contrast"] = round(float(min(moved["contrast"] * scale, 1.0)), 4)
    return moved
