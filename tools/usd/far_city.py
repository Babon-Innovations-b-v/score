"""The far city's plan: a harbour city the framework lays itself (the owner on the demo, 2026-10-09: the game's Hong
Kong photographs on the skyline were "cheating").

A real skyline is density and depth (the owner, 2026-09-30: single models spread over flat ground read as a toy
lineup). So hundreds of copies of a few made tower kinds (data/definitions/far_city.json: the launch inventory's
far_city rows, each made from its close-up by the prop pipeline) stand as a dense wall along a far shore, rows deep,
seeded turns and heights, the business districts taller, with code-built mountains behind. far_city_stage.py stands
the plan up in 3D as a place of its own, which the flat, the street, the square and the launch view reference.

    .venv/bin/python tools/usd/far_city.py --seed 7       # prints how many towers of each kind the seed lays

Frame: EarthSite's metres (x across, -x toward the harbour; z along; bearings clockwise from north, -z), the water at
height 0.
"""
import argparse
import json
import math
import os
import pathlib
import random

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
KINDS = REPO / "data/definitions/far_city.json"
INVENTORY = REPO / "data/inventory/launch.json"
WORK = pathlib.Path(os.environ.get("PROPS_WORK", pathlib.Path.home() / ".farm-factory-props/work"))
# Where the made tower kinds wait for the world's release, each <row>_1.gltf (job r2-city, 2026-10-09).
MODELS = WORK / "far-city/release/models/far_city"

# The far shore's distance from the ring's middle: furthest straight across the harbour (west, bearing 270), nearer
# round to the south and the north, where the city runs on across land; a slow seeded wander along it.
SHORE_ACROSS = 1750.0
SHORE_ROUND = 1300.0
SHORE_WANDER = 70.0
# The city's stretch of bearings (round the harbour's far side, where the game's shore ring hung, 148 to 392 degrees)
# and its rows behind the shore.
CITY_FROM = 136.0
CITY_TO = 404.0
ROWS = 14
ROW_DEEP = 48.0
FIRST_ROW = 30.0
# The gap along a row between two lots' middles, and how much it varies.
LOT_ALONG = 44.0
LOT_SPREAD = 0.3
# The business districts: bearing and width (degrees); the office towers stand thick and tall there.
DISTRICTS = ((262.0, 20.0, 1.0), (334.0, 11.0, 0.75), (196.0, 10.0, 0.6))
# A lot left empty (a street, a park), and how far a tower may turn off facing the ring's middle.
EMPTY_SHARE = 0.08
TURN_JITTER = 18.0
# The mountains behind: from this far behind the shore, out to MOUNTAIN_DEEP more, their ridge's height round the
# bearings (a seeded fractal wander between the low and the high), sampled every MOUNTAIN_STEP metres and degree.
MOUNTAIN_BEHIND = 550.0
MOUNTAIN_DEEP = 3200.0
MOUNTAIN_LOW = 300.0
MOUNTAIN_HIGH = 1150.0
MOUNTAIN_STEP = 100.0


def wander(bearing, seed, waves=((2, 0.5), (5, 0.3), (11, 0.2))):
    """A smooth seeded wander round the bearings between -1 and 1: a few sines of whole turns with seeded phases."""
    phases = random.Random(seed).random
    total = sum(weight * math.sin(math.radians(bearing) * count + 2 * math.pi * phases()) for count, weight in waves)
    return total / sum(weight for _, weight in waves)


def shore_distance(bearing, seed):
    """How far the far shore lies from the ring's middle at a bearing."""
    across = max(0.0, math.cos(math.radians(bearing - 270.0)))
    return SHORE_ROUND + (SHORE_ACROSS - SHORE_ROUND) * across + SHORE_WANDER * wander(bearing, seed)


def district(bearing):
    """How much of a business district a bearing is in: 0 outside every one, up to its weight at its middle."""
    def apart(middle):
        return (bearing - middle + 180.0) % 360.0 - 180.0
    return max(weight * math.exp(-(apart(middle) / width) ** 2) for middle, width, weight in DISTRICTS)


def kinds(made=None):
    """The tower kinds with their row's size (wide, deep, tall in metres) from the launch inventory; with `made`, only
    the kinds named there (those with a made model)."""
    rows = {row["id"]: row for row in json.loads(INVENTORY.read_text())["rows"]}
    found = []
    for kind in json.loads(KINDS.read_text())["kinds"]:
        if made is not None and kind["row"] not in made:
            continue
        if kind["row"] not in rows:
            raise SystemExit(f"far city kind {kind['row']} is not a row of {INVENTORY}")
        found.append(dict(kind, size=[float(side) for side in rows[kind["row"]]["size"]]))
    return found


def pick_kind(choose, row, office, by_use):
    """Which kind stands on a lot: the waterfront's low blocks on the first row, office towers as often as the lot is
    in a business district, homes elsewhere; a use with no kind made takes the homes' (the offices' when there are
    none)."""
    by_use = {use: by_use[use] or by_use["residential"] or by_use["office"] for use in by_use}
    if row == 0 and choose.random() < 0.7:
        return choose.choice(by_use["front"])
    if choose.random() < 0.08 + 0.85 * office:
        return choose.choice(by_use["office"])
    return choose.choice(by_use["residential"])


def tower_height(choose, kind, row, office):
    """A tower's height: its kind's range, taller in a business district and a little taller further back."""
    low, high = kind["heights"]
    lift = 1.0 + 0.15 * office * (kind["use"] == "office") + 0.005 * row
    return choose.uniform(low, high) * lift


def footprint_radius(kind, height):
    """Half the longer side of a tower's foot, at the height it is dealt (its row's proportions)."""
    wide, deep, tall = kind["size"]
    return 0.5 * max(wide, deep) * height / tall


def clear(spot, radius, laid_grid, cell=120.0):
    """True when a foot at `spot` of `radius` keeps clear of every tower laid so far (a grid of cells by position)."""
    column, row = int(spot[0] // cell), int(spot[1] // cell)
    for near_column in range(column - 1, column + 2):
        for near_row in range(row - 1, row + 2):
            for other, other_radius in laid_grid.get((near_column, near_row), ()):
                if math.dist(spot, other) < radius + other_radius:
                    return False
    return True


def lay_towers(seed, made=None):
    """Every tower of the city: {kind, at: [x, z], facing: the bearing its front looks along, height}, rows deep
    along the far shore, seeded."""
    choose = random.Random(seed)
    all_kinds = kinds(made)
    by_use = {use: [kind for kind in all_kinds if kind["use"] == use] for use in ("office", "residential", "front")}
    laid, grid = [], {}
    for row in range(ROWS):
        bearing = CITY_FROM
        while bearing < CITY_TO:
            reach = shore_distance(bearing, seed) + FIRST_ROW + row * ROW_DEEP + choose.uniform(-0.3, 0.3) * ROW_DEEP
            step = LOT_ALONG * (1.0 + choose.uniform(-LOT_SPREAD, LOT_SPREAD))
            here = bearing % 360.0
            bearing += math.degrees(step / reach)
            if choose.random() < EMPTY_SHARE:
                continue
            office = district(here)
            kind = pick_kind(choose, row, office, by_use)
            height = tower_height(choose, kind, row, office)
            radius = footprint_radius(kind, height)
            spot = (reach * math.sin(math.radians(here)), -reach * math.cos(math.radians(here)))
            if not clear(spot, radius, grid):
                continue
            grid.setdefault((int(spot[0] // 120.0), int(spot[1] // 120.0)), []).append((spot, radius))
            facing = (here + 180.0 + choose.uniform(-TURN_JITTER, TURN_JITTER)) % 360.0
            laid.append({"kind": kind["row"], "at": [round(spot[0], 2), round(spot[1], 2)],
                         "facing": round(facing, 2), "height": round(height, 2), "radius": round(radius, 2)})
    return laid


def mountains(seed):
    """The mountains behind the city as a ground of heights on a polar grid: {bearings, reaches (metres behind the
    shore from MOUNTAIN_BEHIND), heights[reach][bearing], shore[bearing]}; each bearing's ridge rises from its foot to
    its crest a third of the way back and falls slowly after."""
    bearings = np.arange(CITY_FROM - 10.0, CITY_TO + 10.0 + 0.5, 1.0)
    reaches = np.arange(0.0, MOUNTAIN_DEEP + 0.5, MOUNTAIN_STEP)
    crest = np.array([MOUNTAIN_LOW + (MOUNTAIN_HIGH - MOUNTAIN_LOW) * max(0.0, 0.5 + 0.5 * wander(
        bearing, seed + 1, ((3, 0.4), (7, 0.3), (17, 0.2), (31, 0.1)))) ** 1.5 for bearing in bearings])
    back = reaches / MOUNTAIN_DEEP
    profile = np.where(back < 1 / 3, np.clip(np.sin(back * 1.5 * math.pi), 0.0, 1.0) ** 1.2, 1.0 - 0.55 * (back - 1 / 3) * 1.5)
    rough = np.array([[wander(bearing * 3.0 + reach * 0.05, seed + 2, ((13, 0.5), (29, 0.5)))
                       for bearing in bearings] for reach in reaches])
    heights = profile[:, None] * crest[None, :] * (1.0 + 0.12 * rough)
    heights[0, :] = 0.0
    return {"bearings": bearings.tolist(), "reaches": (reaches + MOUNTAIN_BEHIND).tolist(),
            "heights": np.round(heights, 2).tolist(),
            "shore": [round(shore_distance(bearing, seed), 2) for bearing in bearings]}


def plan(seed, made=None):
    """The city's plan: its towers (of the `made` kinds only, when given), mountains and shore, and each kind's use."""
    return {"seed": seed, "towers": lay_towers(seed, made), "mountains": mountains(seed),
            "uses": {kind["row"]: kind["use"] for kind in kinds(made)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seed", type=int, default=7)
    arguments = parser.parse_args()
    towers = lay_towers(arguments.seed)
    counts = {kind["row"]: sum(tower["kind"] == kind["row"] for tower in towers) for kind in kinds()}
    print(f"seed {arguments.seed}: {len(towers)} towers {json.dumps(counts)}")


if __name__ == "__main__":
    main()
