"""Turn the framework's inputs into an Infinigen job: a dimensioned plan's heights, zones and marked spots, the
place's look, and the game's budgets, written as one job folder that cloud/infinigen.py runs and patch.py reads.

    ~/.farm-factory-props/env/bin/python tools/props/infinigen/steer.py <kind> <job folder> [--plan <plan folder>]
        [--window x0 y0 side] [--seed 7]

kind: meadow (a terraformed-Mars ground patch from a place plan: heights.npy, zones.npz, placements.json), moon (a
Moon patch from the Moon plan: its crater, slope and boulders as numbers, so the crater element builds the shape),
underwater (a reef floor drawn here in code), fish (one fish with its swim loop).

The job folder gets spec.json, heights.npy (row 0 north, x east, metres) and zones.npz (the same grid, one boolean
mask a zone). Every number patch.py steers by is in spec.json; nothing up there is chosen by Infinigen's own scene
dice except what spec.json leaves to the seed.
"""
import argparse
import json
import math
import pathlib

import numpy as np

# The game's budgets for one 50 x 50 m patch, the owner's asset rules carried over: a structure-sized ground
# (20,000 triangles at a 0.5 m cell), each scattered kind small enough to draw thousands of.
GAME = {"ground_cell_m": 0.5, "ground_texture_px": 2048, "asset_texture_px": 512,
        "triangles": {"grass": 120, "moss": 60, "kelp": 1500, "coral": 3000, "shrub": 6000, "rock": 1500,
                      "boulder": 3000, "rubble": 40, "fish": 4000, "plant": 4000}}
EYE_M = 1.7
GRID = 256


def bilinear(field, side, x, y):
    """`field` (row 0 north, x east, covering `side` metres) read at metres (x, y) from its south-west corner."""
    rows, cols = field.shape
    column = np.clip(np.asarray(x) / side * (cols - 1), 0, cols - 1)
    row = np.clip((side - np.asarray(y)) / side * (rows - 1), 0, rows - 1)
    left, top = np.floor(column).astype(int), np.floor(row).astype(int)
    right, bottom = np.minimum(left + 1, cols - 1), np.minimum(top + 1, rows - 1)
    across, down = column - left, row - top
    upper = field[top, left] * (1 - across) + field[top, right] * across
    lower = field[bottom, left] * (1 - across) + field[bottom, right] * across
    return upper * (1 - down) + lower * down


def window_grid(x0, y0, side, size=GRID):
    """The plan metres of a `size` x `size` grid over the window, row 0 north."""
    across = np.linspace(0, side, size)
    east, north = np.meshgrid(x0 + across, y0 + across[::-1])
    return east, north


def crop(field, plan_side, x0, y0, side, size=GRID):
    """The window (x0, y0, side) of a plan field, resampled to `size` x `size`."""
    east, north = window_grid(x0, y0, side, size)
    return bilinear(field.astype(np.float64), plan_side, east, north)


def spots_inside(items, x0, y0, side):
    """The plan's marked spots inside the window, moved to the window's own metres."""
    return [dict(item, x=round(item["x"] - x0, 2), y=round(item["y"] - y0, 2)) for item in items
            if x0 <= item["x"] < x0 + side and y0 <= item["y"] < y0 + side]


def look_camera(side, heights, toward, at=None):
    """An eye-height camera at `at` (window metres; the south edge's middle by default), looking at `toward`."""
    x, y = at or (side / 2, side * 0.08)
    ground = float(bilinear(heights, side, x, y))
    return {"x": x, "y": y, "z": round(ground + EYE_M, 2), "look_x": toward[0], "look_y": toward[1],
            "look_z": round(float(bilinear(heights, side, *toward)) + EYE_M * 0.5, 2), "lens_mm": 24}


def meadow(plan, x0, y0, side, seed):
    """Test (a): a terraformed-Mars ground patch from a place plan's heights, zones and spots."""
    plan_side = json.loads((plan / "placements.json").read_text())["side_m"]
    heights = crop(np.load(plan / "heights.npy"), plan_side, x0, y0, side)
    masks = np.load(plan / "zones.npz")
    zones = {name: crop(masks[name].astype(np.float64), plan_side, x0, y0, side) > 0.5 for name in masks.files}
    level = np.load(plan / "water_level.npy")
    water_level = crop(np.nan_to_num(level, nan=-1e3), plan_side, x0, y0, side)
    # Grass where the plan leaves the ground open: not water, not the moss ring, not the dry rock.
    zones["grass"] = ~zones["water"] & ~zones["moss"] & ~zones["rock"]
    items = json.loads((plan / "placements.json").read_text())["items"]
    spec = {"kind": "meadow", "seed": seed, "side_m": side, "origin_in_plan": [x0, y0],
            "spots": spots_inside(items, x0, y0, side), "water_level": "water_level.npy",
            "look": {"sky": "earth", "sun_elevation_deg": 35, "sun_azimuth_deg": 135},
            "scatter": {"grass": "grass", "moss": "moss", "rock": "pebbles"},
            # Infinigen draws its grass palette at random (golden on one seed, pink on the next); the plan wants
            # it green: the hue every stop of its colour ramps is set to.
            "tint": {"grass": 0.25},
            # The cover is too dense to draw whole (6.3 M moss clumps): its colour goes into the ground's map seen
            # from above, and the game keeps a thinned share of the 3D copies.
            "game_more": {"cover_from_above": True, "max_copies": {"grass": 30000, "moss": 15000}},
            "camera": look_camera(side, heights, (side * 0.7, side * 0.66), at=(side * 0.4, side * 0.3)),
            "minutes": 90}
    spec["_arrays"] = {"water_level.npy": water_level}
    return spec, heights, zones


def moon(plan, x0, y0, side, seed):
    """Test (d): a Moon patch; the crater element builds the shape from the plan's numbers."""
    numbers = json.loads((plan / "rocks.json").read_text())
    crater = numbers["crater"]
    plan_side = 200.0
    truth = crop(np.load(plan / "terrain.npy"), plan_side, x0, y0, side)  # the ground without its boulders
    rise = numbers["rise_m"] / (2 * plan_side)  # metres a metre, east and north alike
    craters = [{"x": crater["x"] - x0, "y": crater["y"] - y0, "diameter": crater["diameter"],
                "depth_below_rim": crater["depth_below_rim"], "rim_above_plain": crater["rim_above_plain"],
                "ejecta_reach": 1.8, "ejecta_m": 0.4}]
    rocks = [{"kind": "boulder", "x": rock["x"] - x0, "y": rock["y"] - y0, "size_m": rock["across_m"],
              "tall_m": rock["tall_m"], "turn_deg": (index * 137.5) % 360}
             for index, rock in enumerate(numbers["rocks"])
             if x0 <= rock["x"] < x0 + side and y0 <= rock["y"] < y0 + side]
    spec = {"kind": "moon", "seed": seed, "side_m": side, "origin_in_plan": [x0, y0],
            "plane": {"base_m": rise * (x0 + y0), "rise_east": rise, "rise_north": rise},
            "craters": craters, "spots": rocks,
            "look": {"sky": "black", "sun_elevation_deg": 25, "sun_azimuth_deg": 250},
            "scatter": {"rubble": "everywhere"},
            "camera": look_camera(side, truth, (side * 0.62, side * 0.52), at=(side * 0.04, side * 0.46)),
            "minutes": 75}
    return spec, truth, {}


def reef_heights(side, seed, size=GRID):
    """A reef floor in code: a sandy floor with a low rock ridge across it, 0 to 2.5 m."""
    east, north = window_grid(0, 0, side, size)
    rng = np.random.default_rng(seed)
    bumps = sum(rng.uniform(0.1, 0.3) * np.sin(east / side * math.tau * rng.uniform(1, 3) + rng.uniform(0, 6))
                * np.cos(north / side * math.tau * rng.uniform(1, 3) + rng.uniform(0, 6)) for _ in range(4))
    ridge = 2.2 * np.exp(-((north - side * 0.55 - 0.15 * (east - side / 2)) / (side * 0.12)) ** 2)
    return bumps + ridge


def underwater(side, seed):
    """Test (b): a small reef patch, corals on the ridge, kelp on the sand behind it."""
    heights = reef_heights(side, seed)
    east, north = window_grid(0, 0, side, GRID)
    ridge = heights > 1.0
    zones = {"coral": ridge, "kelp": (north > side * 0.7) & ~ridge, "sand": ~ridge}
    spec = {"kind": "underwater", "seed": seed, "side_m": side, "water_depth_m": 8.0,
            "look": {"sky": "underwater", "sun_elevation_deg": 60, "sun_azimuth_deg": 160},
            "scatter": {"coral": "coral", "kelp": "kelp", "urchin": "sand"},
            "camera": look_camera(side, heights, (side / 2, side * 0.6)), "spots": [], "minutes": 75}
    return spec, heights, zones


def fish(seed):
    """Test (c): one fish, its swim baked into one loop."""
    spec = {"kind": "fish", "seed": seed, "loop_seconds": 1.0, "fps": 24, "minutes": 30,
            "look": {"sky": "underwater", "sun_elevation_deg": 60, "sun_azimuth_deg": 160}}
    return spec, None, {}


def write(folder, spec, heights, zones):
    """The job folder: spec.json, and the arrays it names."""
    folder.mkdir(parents=True, exist_ok=True)
    spec = dict(spec, game={**GAME, **spec.pop("game_more", {})})
    for name, array in spec.pop("_arrays", {}).items():
        np.save(folder / name, array.astype(np.float32))
    if heights is not None:
        np.save(folder / "heights.npy", heights.astype(np.float32))
        spec["heights"] = "heights.npy"
    if zones:
        np.savez_compressed(folder / "zones.npz", **{name: mask.astype(bool) for name, mask in zones.items()})
        spec["zones"] = "zones.npz"
    (folder / "spec.json").write_text(json.dumps(spec, indent=1))
    return spec


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("kind", choices=("meadow", "moon", "underwater", "fish"))
    parser.add_argument("folder", type=pathlib.Path)
    parser.add_argument("--plan", type=pathlib.Path, help="the place plan's folder (meadow, moon)")
    parser.add_argument("--window", type=float, nargs=3, metavar=("X0", "Y0", "SIDE"), default=(0, 0, 50))
    parser.add_argument("--seed", type=int, default=7)
    options = parser.parse_args()
    x0, y0, side = options.window
    if options.kind == "meadow":
        made = meadow(options.plan, x0, y0, side, options.seed)
    elif options.kind == "moon":
        made = moon(options.plan, x0, y0, side, options.seed)
    elif options.kind == "underwater":
        made = underwater(side, options.seed)
    else:
        made = fish(options.seed)
    spec = write(options.folder, *made)
    print(json.dumps({key: spec[key] for key in spec if key not in ("spots", "game")}))
    print(f"{len(spec.get('spots', []))} spots")


if __name__ == "__main__":
    main()
