"""The landforms a terrain plan names, each built in code from its own settings on the plan's grid: craters of every
kind, ridges, layered buttes, dune fields, lava swells, canyons, hill ranges and a harbour's shore and seabed.

Every builder takes the grid (`Grid`: x across and z along in metres, row 0 at z = -side/2) and one landform's
settings from the plan, and gives heights in metres on the grid. The crater, ridge, butte, dune, swell and canyon
builders are the ones the game 2099's Moon and Mars plans were drawn with (its moonground and mars-build jobs,
6 to 8 October 2026), moved here unchanged in what they compute so the stage regenerates those grounds from their
plans; the hills, shore and seabed are new for the Earth's harbour.
"""
import math
from dataclasses import dataclass

import numpy as np
from scipy import ndimage


@dataclass
class Grid:
    """A square plan `side` metres across sampled `points` times a side: x across, z along, row 0 at -side/2."""
    side: float
    points: int

    def __post_init__(self):
        axis = np.linspace(-self.side / 2, self.side / 2, self.points)
        self.x, self.z = np.meshgrid(axis, axis)
        self.cell = self.side / (self.points - 1)

    def window(self, middle_x, middle_z, reach):
        """The rows and columns within `reach` metres of a middle."""
        def span(middle):
            low = max(0, int((middle - reach + self.side / 2) / self.cell))
            high = min(self.points, int((middle + reach + self.side / 2) / self.cell) + 2)
            return slice(low, high)
        return span(middle_z), span(middle_x)

    def index(self, x, z):
        """The (row, column) of the cell a spot falls in, or None outside the plan."""
        row, column = int((z + self.side / 2) / self.cell), int((x + self.side / 2) / self.cell)
        return (row, column) if 0 <= row < self.points and 0 <= column < self.points else None


def harmonics(theta, amount, seed, lowest=2, highest=7):
    """A wobble round a circle, the sum of a few low harmonics, each halving: what gives real rims their polygons."""
    rng = np.random.default_rng(seed)
    total = np.zeros_like(theta)
    for order in range(lowest, highest + 1):
        total += rng.normal() * math.pow(order / lowest, -1.2) * np.cos(order * theta + rng.uniform(0, math.tau))
    return amount * total / 1.6


def smooth_noise(shape, scale_px, seed):
    """Seeded noise smoothed over `scale_px` cells, at unit spread."""
    rng = np.random.default_rng(seed)
    field = ndimage.gaussian_filter(rng.normal(size=shape), scale_px, mode="wrap")
    return field / (field.std() + 1e-9)


def polar_noise(seed, radius, across_m, down_part, parts=1.25):
    """A noise field round a crater, read by bearing and by share of the radius out: lumps about across_m wide round
    the crater and down_part long down its wall, so they run downslope like a wall's chutes and spurs. Unit spread."""
    rng = np.random.default_rng(seed)
    bearings = max(64, int(math.tau * radius / (across_m / 4.0)))
    rings = 96
    field = rng.normal(size=(rings, bearings))
    field = ndimage.gaussian_filter(field, (down_part / parts * rings, across_m / (math.tau * radius) * bearings),
                                    mode=("nearest", "wrap"))
    field /= field.std() + 1e-9

    def read(theta, part):
        column = (theta + math.pi) / math.tau * bearings
        row = np.clip(part / parts * (rings - 1), 0, rings - 1)
        return ndimage.map_coordinates(field, [row, column], order=1, mode="grid-wrap")
    return read


def wall_texture(crater, theta, part, depth, fresh):
    """What roughens a crater's wall at one to five metres: chutes and spurs from crest to foot, talus lobes at the
    foot, and on a fresh crater bedrock knobs just under the crest."""
    radius = crater["d"] / 2
    seed = crater["seed"]
    floor = crater.get("floor", 0.0)
    toe = floor + (1.0 - floor) * 0.42
    wall = np.clip((part - toe) / 0.15, 0, 1) * np.clip((0.97 - part) / 0.07, 0, 1)
    chutes = (polar_noise(seed + 31, radius, min(2.5, radius * 0.2), 0.3)(theta, part)
              + 0.7 * polar_noise(seed + 34, radius, min(6.0, radius * 0.4), 0.5)(theta, part))
    texture = (0.25 + 0.75 * fresh) * crater.get("chutes", 1.0) * min(0.07 * depth, 1.2) * wall * chutes
    foot = np.exp(-((part - toe) / 0.08) ** 2)
    lobes = np.clip(polar_noise(seed + 32, radius, min(5.0, radius * 0.35), 0.2)(theta, part), 0, None)
    texture = texture + fresh * min(0.05 * depth, 0.8) * foot * lobes
    if fresh > 0.55:
        crest = np.exp(-((part - 0.9) / 0.035) ** 2)
        knobs = np.clip(polar_noise(seed + 33, radius, min(2.5, radius * 0.2), 0.06)(theta, part) - 0.6, 0, None)
        texture = texture + fresh * min(0.06 * depth, 1.0) * crest * knobs
    return texture


def crater_rim(crater, theta, part):
    """A crater's rim height round its bearings, broken where the plan breaks it."""
    rim = crater["rim"] * crater["d"] * (1.0 + harmonics(theta, 0.35, crater["seed"] + 1, 1, 5))
    for middle, width in crater.get("breaks", []):
        gap = np.angle(np.exp(1j * (theta - math.radians(middle))))
        rim = rim * (1.0 - 0.75 * np.exp(-(gap / math.radians(width / 2)) ** 2))
    return rim


def crater_bowl(crater, theta, part, depth, rim, fresh):
    """Inside the rim: the bowl from crest to floor, with the kind's terraces, gullies, bench, infill, mound and
    slump."""
    seed = crater["seed"]
    floor = crater.get("floor", 0.0)
    inner = np.clip((part - floor) / (1.0 - floor), 0.0, 1.0)
    steep = 0.5 * fresh
    wall = (1.0 - steep) * inner ** 2 + steep * inner ** 6
    terraces = crater.get("terraces", 0)
    if terraces:
        steps = wall * terraces
        stairs = (np.floor(steps) + np.clip((steps - np.floor(steps) - 0.55) / 0.45, 0, 1) ** 2) / terraces
        wall = 0.35 * wall + 0.65 * stairs
    bowl = -depth + (depth + rim) * wall
    if crater.get("gullies"):
        rng = np.random.default_rng(seed + 7)
        grooves = np.zeros_like(theta)
        for _ in range(26):
            gap = np.angle(np.exp(1j * (theta - rng.uniform(-math.pi, math.pi))))
            grooves += rng.uniform(0.3, 1.0) * np.exp(-(gap / math.radians(rng.uniform(1.0, 3.5))) ** 2)
        band = np.clip((part - 0.4) / 0.3, 0, 1) * np.clip((0.93 - part) / 0.12, 0, 1)
        bowl = bowl - crater["gullies"] * band * np.clip(grooves, 0, 1.2)
    bowl = bowl + wall_texture(crater, theta, part, depth, fresh)
    if crater.get("bench"):
        bowl = bowl + 0.12 * depth * np.clip((part - crater["bench"]) / 0.05, 0, 1) * np.clip((0.75 - part) / 0.2, 0, 1)
    if crater.get("infill"):
        bowl = np.maximum(bowl, -depth * (1.0 - crater["infill"]))
    if crater.get("mound"):
        bowl += crater["mound"] * depth * np.exp(-(part / 0.18) ** 2)
    slump = crater.get("slump")
    if slump:
        gap = np.angle(np.exp(1j * (theta - math.radians(slump[0]))))
        lobe = np.exp(-(gap / math.radians(slump[1] / 2)) ** 2)
        bowl += lobe * (0.45 * depth * np.exp(-((part - 0.55) / 0.22) ** 2)
                        - 0.5 * rim * np.exp(-((part - 1.0) / 0.12) ** 2))
    return bowl


def crater_profile(crater, grid, x, z):
    """One crater's height on its window, and how much of what lay there before it erases (1 inside the bowl)."""
    radius = crater["d"] / 2
    dx, dz = x - crater["x"], z - crater["z"]
    turn = math.radians(crater.get("turn", 0.0))
    along = (dx * math.cos(turn) + dz * math.sin(turn)) / crater.get("stretch", 1.0)
    across = -dx * math.sin(turn) + dz * math.cos(turn)
    theta = np.arctan2(across, along)
    part = np.hypot(along, across) / (radius * (1.0 + harmonics(theta, crater["wobble"], crater["seed"])))
    fresh = 1.0 - crater["age"]
    depth = crater["depth"] * crater["d"]
    rim = crater_rim(crater, theta, part)
    bowl = crater_bowl(crater, theta, part, depth, rim, fresh)
    reach = crater.get("ejecta", 2.0)
    flank = rim * np.clip(part, 1.0, None) ** -3.0 * np.clip((reach - part) / (reach - 1.0) * 3.0, 0.0, 1.0)
    height = np.where(part < 1.0, bowl, flank)
    if crater.get("rays") or fresh > 0.6:
        hummocks = smooth_noise(part.shape, 0.9 / grid.cell, crater["seed"] + 5) * 0.12 * rim
        rays = 0.5 + 0.5 * np.cos(harmonics(theta, 6.0, crater["seed"] + 6, 5, 13))
        outside = np.clip(part - 1.0, 0, None)
        near_rim = np.clip((part - 0.75) / 0.25, 0, 1)
        on_floor = np.clip((0.55 - part) / 0.2, 0, 1) * 0.5
        height = height + hummocks * (np.exp(-outside / 0.6) * near_rim * (0.5 + rays) + on_floor)
    height = ndimage.gaussian_filter(height, max(crater["age"] * radius * 0.12, min(0.03 * radius, 1.2)) / grid.cell)
    erase = np.clip((1.05 - part) / 0.15, 0.0, 1.0)
    return height, erase


def lay_craters(ground, grid, craters):
    """Cut every crater into the ground, oldest first: inside its bowl what lay there is dug out (a worn crater
    keeps a trace of it), outside it is buried under the rim's flank."""
    for crater in sorted(craters, key=lambda each: -each["age"]):
        stretch = crater.get("stretch", 1.0)
        rows, columns = grid.window(crater["x"], crater["z"],
                                    crater["d"] / 2 * stretch * (crater.get("ejecta", 2.0) + 0.3))
        local = ground[rows, columns]
        height, erase = crater_profile(crater, grid, grid.x[rows, columns], grid.z[rows, columns])
        level = float(np.median(local[erase < 0.01])) if np.any(erase < 0.01) else float(local.mean())
        keep = 1.0 - erase * (0.85 + 0.15 * (1.0 - crater["age"]))
        ground[rows, columns] = local * keep + level * (1.0 - keep) + height
    return ground


def small_craters(grid, settings, held):
    """The plan's count of small craters, sizes falling off as real crater counts do, none on a held flat."""
    rng = np.random.default_rng(settings["seed"])
    found = []
    while len(found) < settings["count"]:
        size = float(min(settings["smallest"] / math.sqrt(1.0 - rng.random() * settings["spread"]), settings["largest"]))
        x, z = rng.uniform(-grid.side / 2 + 8, grid.side / 2 - 8, 2)
        north = settings.get("north", 0.0)
        if north and rng.random() > (1.0 - north) + north * (-z / (grid.side / 2)):
            continue
        spot = grid.index(x, z)
        if spot is None or held[spot] > 0.01:
            continue
        age = float(rng.random() ** 0.7) if settings.get("age") == "any" else float(0.5 + 0.5 * rng.random())
        found.append(dict(name=f"s{len(found)}", x=float(x), z=float(z), d=size, kind="small", age=age,
                          depth=float(rng.uniform(*settings["depth"])), rim=float(rng.uniform(*settings["rim"])),
                          wobble=0.08, seed=int(settings["first_seed"] + len(found))))
    return found


def segment_distance(x, z, points):
    """How far each spot is from a polyline, and how far along it (0..1) the nearest point is."""
    best = np.full(x.shape, 1e9)
    along = np.zeros(x.shape)
    lengths = [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])]
    total, run = sum(lengths), 0.0
    for (ax, az), (bx, bz), length in zip(points, points[1:], lengths):
        segment = np.array([bx - ax, bz - az])
        part = np.clip(((x - ax) * segment[0] + (z - az) * segment[1]) / (segment @ segment), 0, 1)
        gap = np.hypot(x - ax - part * segment[0], z - az - part * segment[1])
        closer = gap < best
        best = np.where(closer, gap, best)
        along = np.where(closer, (run + part * length) / total, along)
        run += length
    return best, along


def banded(rise, bands, sharp=0.6):
    """A slope cut into steps: each layer a steep cliff band over a gentler bench."""
    steps = rise * bands
    whole = np.floor(steps)
    return (whole + np.clip((steps - whole - (1 - sharp)) / sharp, 0, 1) ** 0.6) / bands


def ridge(grid, spec):
    """A long ridge along its points, its crest rising and falling, dipping to a saddle where the plan puts one."""
    gap, along = segment_distance(grid.x, grid.z, spec["points"])
    crest = spec["height"] * (0.75 + 0.25 * np.sin(along * 9.0 + 1.0)) * np.clip(along * 6, 0, 1) * \
        np.clip((1 - along) * 5, 0, 1)
    if spec.get("saddle"):
        saddle = np.hypot(grid.x - spec["saddle"][0], grid.z - spec["saddle"][1])
        crest = crest - (crest - spec["saddle_height"]) * np.exp(-(saddle / 26.0) ** 2)
    wobble = smooth_noise(grid.x.shape, 9.0 / grid.cell, spec["seed"] + 1) * 3.0
    part = np.clip((gap + wobble) / spec["half_wide"], 0, None)
    profile = np.clip(1 - part ** 2, 0, 1) ** 1.6
    gullies = 1.0 - 0.04 * np.clip(smooth_noise(grid.x.shape, 2.2 / grid.cell, spec["seed"] + 2), 0, None) * \
        (part > 0.2) * (part < 0.9)
    return crest * profile * gullies


def butte(grid, spec):
    """A flat-topped butte with layered cliff bands and a talus apron."""
    seed = spec["seed"]
    theta = np.arctan2(grid.z - spec["z"], grid.x - spec["x"])
    radius = spec["top"] * (1.0 + harmonics(theta, 0.14, seed))
    out = np.hypot(grid.x - spec["x"], grid.z - spec["z"]) / radius
    out = out + 0.08 * smooth_noise(grid.x.shape, 3.0 / grid.cell, seed + 2) + \
        0.12 * smooth_noise(grid.x.shape, 9.0 / grid.cell, seed + 3)
    cliff = 1.0 + spec["apron"] / spec["top"] * 0.45
    rise = np.clip((cliff - out) / (cliff - 1.0), 0, 1)
    body = banded(rise, spec["bands"]) * spec["height"]
    apron_part = np.clip((out - 1.0) / (spec["apron"] / spec["top"]), 0, 1)
    apron = spec["height"] * 0.22 * (1 - apron_part) ** 2
    top = spec["height"] + 0.4 * smooth_noise(grid.x.shape, 3.0 / grid.cell, seed + 1)
    return np.where(out < 1.0, top, np.maximum(body, apron))


def dunes(grid, spec):
    """Crescent dunes on a low sand sheet with ripple trains: a gentle windward back and a slip face at repose,
    horns reaching downwind."""
    x, z = grid.x, grid.z
    x0, z0, wide, deep = spec["box"]
    inside = np.clip(np.minimum.reduce([x - x0, x0 + wide - x, z - z0, z0 + deep - z]) / 14.0, 0, 1)
    sheet = 0.5 * inside * inside
    ripples = 0.18 * inside * np.clip(np.sin((x + 0.3 * z + smooth_noise(x.shape, 6.0 / grid.cell, spec["seed"])
                                              * 2.0) / 1.6), 0, 1)
    rng = np.random.default_rng(spec["seed"] + 1)
    total = np.zeros_like(x)
    for _ in range(spec["count"]):
        size = float(rng.uniform(14.0, 30.0))
        middle_x = float(rng.uniform(x0 + size * 0.5, x0 + wide - size * 0.4))
        middle_z = float(rng.uniform(z0 + size * 0.5, z0 + deep - size * 0.5))
        height = spec["height"] * size / 30.0
        across, along = (x - middle_x) / size, (z - middle_z) / size
        body = np.clip(1 - ((across + 0.05) ** 2 / 0.32 ** 2 + along ** 2 / 0.5 ** 2), 0, 1) ** 0.7
        lee = np.clip(1 - ((across - 0.22) ** 2 / 0.3 ** 2 + along ** 2 / 0.3 ** 2), 0, 1) ** 0.45
        total = np.maximum(total, height * np.clip(body - lee, 0, 1))
    return sheet + ripples + ndimage.gaussian_filter(total, 0.5 / grid.cell) * inside


def swell(grid, spec):
    """A low lava swell, lobed."""
    out = np.hypot(grid.x - spec["x"], grid.z - spec["z"]) / spec["radius"]
    lobes = 1.0 + 0.25 * smooth_noise(grid.x.shape, 8.0 / grid.cell, spec["seed"])
    return spec["swell"] * np.clip(1 - out ** 2, 0, None) ** 1.2 * lobes


def canyon(grid, spec):
    """A winding trough with layered walls, its two ends shoaling out."""
    gap, _ = segment_distance(grid.x, grid.z, spec["points"])
    wobble = smooth_noise(grid.x.shape, 6.0 / grid.cell, spec["seed"]) * 2.2 + \
        smooth_noise(grid.x.shape, 18.0 / grid.cell, spec["seed"] + 1) * 3.0
    rise = np.clip((gap - (spec["floor_half"] + wobble)) / spec["wall"], 0, 1)
    first, last = spec["points"][0], spec["points"][-1]
    ends = np.clip(np.hypot(grid.x - first[0], grid.z - first[1]) / 30.0, 0, 1) * \
        np.clip(np.hypot(grid.x - last[0], grid.z - last[1]) / 30.0, 0, 1)
    ends = ends * ends * (3 - 2 * ends)
    return -spec["depth"] * (1 - banded(rise, spec["bands"], 0.5)) * ends


def hills(grid, spec):
    """A range of hills along its points: a crest that wanders between its low and high, falling to its foot over
    `half_wide` metres on each side, with spurs and valleys running down its flanks (seeded noise drawn out across
    the range). Heights in metres above the plain."""
    gap, along = segment_distance(grid.x, grid.z, spec["points"])
    seed = spec["seed"]
    wander = smooth_noise(grid.x.shape, spec["peaks"] / grid.cell, seed)
    crest = spec["low"] + (spec["high"] - spec["low"]) * np.clip(0.5 + 0.35 * wander, 0, 1)
    ends = np.clip(along * 8, 0, 1) * np.clip((1 - along) * 8, 0, 1)
    spurs = smooth_noise(grid.x.shape, spec["spurs"] / grid.cell, seed + 1)
    part = np.clip((gap + spurs * spec["half_wide"] * 0.18) / spec["half_wide"], 0, None)
    rise = np.clip(1 - part, 0, 1)
    profile = rise * rise * (3 - 2 * rise)
    return crest * profile * ends


def shore_distance(grid, shore):
    """Each spot's signed distance into the land from the plan's coastline, in metres (negative out over the water):
    the land is every spot within `land` (a list of polygons, x and z) smoothed over `round` metres."""
    from matplotlib.path import Path
    inside = np.zeros(grid.x.shape, dtype=bool)
    flat = np.column_stack([grid.x.ravel(), grid.z.ravel()])
    for polygon in shore["land"]:
        inside |= Path(np.asarray(polygon)).contains_points(flat).reshape(grid.x.shape)
    rounded = ndimage.gaussian_filter(inside.astype(np.float64), shore["round"] / grid.cell) > 0.5
    into_land = ndimage.distance_transform_edt(rounded) * grid.cell
    into_water = ndimage.distance_transform_edt(~rounded) * grid.cell
    return np.where(rounded, into_land, -into_water)


def seabed(distance, spec):
    """The harbour's floor: a quay wall straight down at the shore to `quay_foot`, then sloping out to `deep` over
    `shelf` metres."""
    out = np.clip(-distance / spec["shelf"], 0, 1)
    return spec["quay_foot"] + (spec["deep"] - spec["quay_foot"]) * (out * out * (3 - 2 * out))
