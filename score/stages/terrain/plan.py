"""A ground's dimensioned plan made into its large shape: the plan (`data/ground/plan/<ground>.json`) lists its steps
in order, each laying one thing on the grid, and this module runs them.

    shaped = plan.shape(record)      # Shaped: the grid, heights, held flats, paths, craters, the land (Earth)
    plan.drawing(shaped, record)     # the plan drawn straight down for reading (shade, contours, flats)

The steps (`shape` in the plan): `tilt` (a plain's own gentle tilt), `noise` (a seeded swell), `add` and `over` (a
landform added, or laid over what is there keeping `keep` of it), `craters` (the named ones and the small ones, oldest
first), `land` (a coastline: the land rising inland from the quay, the seabed falling away from it), `flats` (held
at their level, eased into the ground), `paths` (graded smooth), `cap` (the ground held under the round surface).
"""
import math
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from score.stages.terrain import landforms

LANDFORMS = {"ridge": landforms.ridge, "butte": landforms.butte, "dunes": landforms.dunes, "swell": landforms.swell,
             "canyon": landforms.canyon, "hills": landforms.hills}


@dataclass
class Shaped:
    """A plan made into heights on its grid, with what the later steps and the gates read."""
    grid: landforms.Grid
    heights: np.ndarray
    held: np.ndarray
    on_path: np.ndarray
    craters: list = field(default_factory=list)
    land: np.ndarray = None
    masks: dict = field(default_factory=dict)


def rect_away(grid, rect, margin):
    """How far each spot lies outside a rectangle (x, z, wide, deep) grown by `margin`."""
    x0, z0, wide, deep = rect
    away_x = np.maximum(np.maximum(x0 - margin - grid.x, grid.x - (x0 + wide + margin)), 0)
    away_z = np.maximum(np.maximum(z0 - margin - grid.z, grid.z - (z0 + deep + margin)), 0)
    return np.hypot(away_x, away_z)


def held_flats(grid, flats):
    """How much each spot is held flat (0..1): the plan's rectangles and discs, eased over `ramp` metres."""
    away = np.full(grid.x.shape, 1e9)
    for rect in flats.get("rects", []):
        away = np.minimum(away, rect_away(grid, rect, flats.get("margin", 0.0)))
    for middle_x, middle_z, radius in flats.get("discs", []):
        away = np.minimum(away, np.maximum(np.hypot(grid.x - middle_x, grid.z - middle_z) - radius, 0))
    held = np.clip(1.0 - away / flats["ramp"], 0.0, 1.0)
    return held * held * (3 - 2 * held)


def path_share(grid, paths):
    """How much each spot is on a path (0..1): within half the path's width, eased over `ramp` metres."""
    away = np.full(grid.x.shape, 1e9)
    for line in paths["lines"]:
        gap, _ = landforms.segment_distance(grid.x, grid.z, line["points"])
        away = np.minimum(away, gap)
    return np.clip(1.0 - (away - paths["wide"] / 2) / paths["ramp"], 0.0, 1.0)


def level_flats(shaped, step):
    """The flats held at their level: `level` at the middle disc, the ground's own smoothed height further out."""
    grid = shaped.grid
    near = np.clip((np.hypot(grid.x - step["middle"][0], grid.z - step["middle"][1]) - step["disc"])
                   / step["blend"], 0.0, 1.0)
    level = step["level"] * (1 - near) + ndimage.gaussian_filter(shaped.heights, step["smooth"] / grid.cell) * near
    if step.get("on_land") and shaped.land is not None:
        shaped.held = shaped.held * (shaped.land >= 0)
    return shaped.heights * (1 - shaped.held) + level * shaped.held


def grade_paths(shaped, step):
    """Paths graded to a gentle slope: the ground smoothed over `smooth` metres along them."""
    graded = ndimage.gaussian_filter(shaped.heights, step["smooth"] / shaped.grid.cell)
    return shaped.heights * (1 - shaped.on_path) + graded * shaped.on_path


def capped(shaped, step):
    """The ground held under the round surface round the middle: inside the disc only, or (with `rise`) everywhere,
    the cap rising at a gentle grade from `from` metres out."""
    grid = shaped.grid
    out = np.hypot(grid.x - step["middle"][0], grid.z - step["middle"][1])
    if "rise" in step:
        return np.minimum(shaped.heights, step["below"] + step["rise"] * np.clip(out - step["from"], 0, None) ** 2)
    inside = out < step["disc"]
    found = shaped.heights.copy()
    found[inside] = np.minimum(found[inside], step["below"])
    return found


def path_clearance(grid, record, step):
    """How much a landform is let in beside a named path (0 on it, 1 from `gap` plus `ramp` metres off it)."""
    line = next(line for line in record["paths"]["lines"] if line["name"] == step["clear_of"])
    gap, _ = landforms.segment_distance(grid.x, grid.z, line["points"])
    return np.clip((gap - step["gap"]) / step["ramp"], 0.0, 1.0)


def land_heights(shaped, step):
    """The coastline's land and seabed: on land the height rises inland by `inland` ([metres into the land,
    height], read between), over the water the seabed falls from the quay's foot. Keeps the land's distance."""
    distance = landforms.shore_distance(shaped.grid, step)
    inland = np.asarray(step["inland"], dtype=np.float64)
    on_land = np.interp(np.clip(distance, 0, None), inland[:, 0], inland[:, 1])
    shaped.land = distance
    return np.where(distance >= 0, shaped.heights + on_land, landforms.seabed(distance, step["seabed"]))


def landform(shaped, record, step):
    """One landform the step names, from the plan's own entry of it, and where it is let in."""
    built = LANDFORMS[step["kind"]](shaped.grid, record["landforms"][step["name"]])
    if step.get("clear_of"):
        built = built * path_clearance(shaped.grid, record, step)
    if step.get("on_land") and shaped.land is not None:
        built = built * np.clip(shaped.land / step["on_land"], 0.0, 1.0)
    shaped.masks[step["name"]] = built
    return built


def run_step(shaped, record, step):
    """The heights after one plan step."""
    grid, kind = shaped.grid, step["op"]
    if kind == "tilt":
        return shaped.heights + step["rise"][0] * grid.x + step["rise"][1] * grid.z
    if kind == "noise":
        return shaped.heights + landforms.smooth_noise(grid.x.shape, step["scale"] / grid.cell, step["seed"]) * \
            step["amount"]
    if kind == "add":
        return shaped.heights + landform(shaped, record, step)
    if kind == "over":
        return np.maximum(shaped.heights, landform(shaped, record, step) + shaped.heights * step["keep"])
    if kind == "craters":
        small = landforms.small_craters(grid, record["small_craters"], shaped.held) if "small_craters" in record \
            else []
        shaped.craters = sorted(record.get("craters", []) + small, key=lambda crater: -crater["age"])
        return landforms.lay_craters(shaped.heights, grid, shaped.craters)
    if kind == "land":
        return land_heights(shaped, step)
    if kind == "flats":
        return level_flats(shaped, step)
    if kind == "paths":
        return grade_paths(shaped, step)
    if kind == "cap":
        return capped(shaped, step)
    raise ValueError(f"the plan names a step this stage does not know: {kind}")


def shape(record):
    """The plan's large shape: every step of `shape` run in order on its grid, its hill ranges held under their
    planned highs."""
    grid = landforms.Grid(record["side"], record["points"])
    held = held_flats(grid, record["flats"])
    on_path = path_share(grid, record["paths"]) if record.get("paths") else np.zeros_like(held)
    shaped = Shaped(grid, np.zeros_like(grid.x), held, on_path)
    for step in record["shape"]:
        shaped.heights = run_step(shaped, record, step)
    shaped.heights = shaped.heights.astype(np.float64)
    held_crests(shaped, record)
    return shaped


def held_crests(shaped, record):
    """Each hill range's own rise lowered, in place, just enough that the made ground tops out under the range's
    planned `high` over the datum: the builder's crest stands on the plain the range rises from, so the plain is taken
    off the rise. A range already under it is left as it is."""
    for name, spec in record.get("landforms", {}).items():
        if "high" not in spec or name not in shaped.masks:
            continue
        rise = shaped.masks[name]
        rising = rise > 1.0  # under a metre of rise the plain alone stands far under a range's high
        if not rising.any():
            continue
        plain = shaped.heights - rise
        kept = min(1.0, float(((spec["high"] - plain[rising]) / rise[rising]).min()))
        shaped.heights = shaped.heights - (1.0 - kept) * rise
        shaped.masks[name] = rise * kept


def slopes(heights, cell):
    """Each cell's slope in degrees."""
    rise_rows, rise_columns = np.gradient(heights, cell)
    return np.degrees(np.arctan(np.hypot(rise_rows, rise_columns)))


def shaded(heights, cell):
    """The heights lit from the north-west, high: 0..1."""
    rise_rows, rise_columns = np.gradient(heights, cell)
    light = np.array([-0.6, -0.5, 0.62])
    normal = np.stack([-rise_columns, -rise_rows, np.ones_like(rise_columns)], axis=-1)
    normal /= np.linalg.norm(normal, axis=-1, keepdims=True)
    return np.clip(normal @ (light / np.linalg.norm(light)), 0, 1)


def drawing(shaped, record, size=1024):
    """The plan drawn straight down, north up, for the creator to read: the shaded heights, contours at the plan's
    `contour` metres, flats in green, paths in orange, water in blue and every named landform labelled."""
    scale = size / shaped.grid.points
    heights = ndimage.zoom(shaped.heights, scale, order=1)
    cell = shaped.grid.side / (size - 1)
    picture = np.stack([shaded(heights, cell) * 200 + 40] * 3, -1)
    held = ndimage.zoom(shaped.held, scale, order=1)
    on_path = ndimage.zoom(shaped.on_path, scale, order=1)
    picture[held > 0.5] = picture[held > 0.5] * 0.6 + np.array([120, 200, 120]) * 0.4
    picture[on_path > 0.5] = picture[on_path > 0.5] * 0.5 + np.array([230, 190, 90]) * 0.5
    if shaped.land is not None:
        water = ndimage.zoom(shaped.land, scale, order=1) < 0
        picture[water] = np.array([40, 70, 130])
    levels = np.floor(heights / record["contour"])
    edge = (np.abs(np.diff(levels, axis=0, prepend=levels[:1])) +
            np.abs(np.diff(levels, axis=1, prepend=levels[:, :1]))) > 0
    picture[edge & ~(picture == [40, 70, 130]).all(axis=-1)] = [90, 60, 40]
    image = Image.fromarray(np.clip(picture, 0, 255).astype(np.uint8))
    pen = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=max(12, size // 70))
    for label in record.get("labels", []):
        at = ((label["at"][0] / shaped.grid.side + 0.5) * size, (label["at"][1] / shaped.grid.side + 0.5) * size)
        pen.text(at, label["text"], fill=(120, 20, 20), font=font)
    return image


def named_size(shaped, crater):
    """A named crater as measured on the heights, the tilt of the ground it lies on (a plane fitted between 1.3 and
    1.8 of its radius out) taken off first: its depth from its rim's crest (the median over 36 bearings of the highest
    point between 0.6 and 1.4 of its radius out) to its floor (the median height within 0.15 of its radius), and its
    rim's diameter (twice the median distance out to those highest points)."""
    grid = shaped.grid
    radius = crater["d"] / 2 * crater.get("stretch", 1.0)
    rows, columns = grid.window(crater["x"], crater["z"], radius * 1.8)
    local = shaped.heights[rows, columns]
    dx, dz = grid.x[rows, columns] - crater["x"], grid.z[rows, columns] - crater["z"]
    out = np.hypot(dx, dz)
    ring = (out > radius * 1.3) & (out < radius * 1.8)
    if ring.sum() > 3:
        design = np.column_stack([dx[ring], dz[ring], np.ones(int(ring.sum()))])
        tilt, *_ = np.linalg.lstsq(design, local[ring], rcond=None)
        local = local - (tilt[0] * dx + tilt[1] * dz)
    bearing = (np.degrees(np.arctan2(dz, dx)) // 10).astype(int)
    crest, radii = [], []
    for sector in range(-18, 18):
        inside = (bearing == sector) & (out > 0.6 * crater["d"] / 2) & (out < radius * 1.4)
        if inside.any():
            top = np.argmax(np.where(inside, local, -np.inf))
            crest.append(local.ravel()[top])
            radii.append(out.ravel()[top])
    middle = out < 0.15 * crater["d"] / 2
    floor = float(np.median(local[middle])) if middle.any() else float(local.min())
    return {"depth": round(float(np.median(crest)) - floor, 2), "diameter": round(2 * float(np.median(radii)), 2)}
