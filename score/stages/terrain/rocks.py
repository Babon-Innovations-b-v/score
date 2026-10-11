"""Where a ground's rocks lie, by its plan's rule: thrown out of the fresh craters and sprinkled over the plain on the
Moon; crowded on the basalt swell, under the cliff bands and round the fresh crater on Mars. None on a held flat or
a path. The rules are the ones the game 2099's plans laid their rocks with (moonground and mars-build jobs), so the
stage lays the same rocks from the same plan; each rock is a spot (x, z), a size in metres, a kind (which made rock
model) and a turn in degrees. Rocks are single generated models (the paper's Terrain); this lays them, it does not
make them.
"""
import math

import numpy as np

from score.stages.terrain import plan


def sizes(rng):
    """A size between `small` and `big` metres, falling off as a power law of `fall`."""
    return lambda small, big, fall: float(min(small / (1.0 - rng.random() * 0.999) ** (1.0 / fall), big))


def moon(shaped, settings):
    """The Moon's rule: most rocks just past a fresh crater's rim, thinning outward, a few on its floor, and a
    sprinkle over the plain."""
    rng = np.random.default_rng(settings["seed"])
    size_between = sizes(rng)
    clear = clear_of(shaped)
    found = []
    for crater in shaped.craters:
        fresh = 1.0 - crater["age"]
        if fresh < 0.6:
            continue
        radius = crater["d"] / 2
        count = int(radius ** 1.6 * fresh * (3.0 if crater["name"] == "A" else 1.0))
        biggest = min(4.0, radius * 0.12)
        for _ in range(count):
            bearing = rng.uniform(0, math.tau)
            part = rng.uniform(0.15, 0.7) if rng.random() < 0.12 else 1.0 + rng.exponential(0.45)
            x = crater["x"] + math.cos(bearing) * part * radius
            z = crater["z"] + math.sin(bearing) * part * radius
            if clear(x, z):
                found.append({"x": round(x, 2), "z": round(z, 2), "size": round(size_between(0.3, biggest, 2.2), 2)})
    side = shaped.grid.side
    for _ in range(settings["plain"]):
        x, z = rng.uniform(-side / 2, side / 2, 2)
        if clear(x, z):
            found.append({"x": round(float(x), 2), "z": round(float(z), 2),
                          "size": round(size_between(0.2, 1.2, 2.6), 2)})
    for rock in found:
        rock["kind"] = int(rng.integers(0, 3))
        rock["turn"] = round(float(rng.uniform(0, 360)), 1)
    return found


def mars(shaped, settings, record):
    """Mars's rule: crowded on the basalt swell, talus under the buttes' and the canyon's cliff bands, a few round the
    fresh crater, a sprinkle over the plain. Kind 0 basalt, 1 layered rock."""
    rng = np.random.default_rng(settings["seed"])
    size_between = sizes(rng)
    slope = plan.slopes(shaped.heights, shaped.grid.cell)
    clear = clear_of(shaped, slope)
    found = []

    def add(x, z, kind, small, big, fall):
        if clear(x, z):
            found.append({"x": round(float(x), 2), "z": round(float(z), 2),
                          "size": round(size_between(small, big, fall), 2), "kind": kind})

    landforms = record["landforms"]
    basalt = landforms["basalt"]
    for _ in range(1100):
        bearing, part = rng.uniform(0, math.tau), math.sqrt(rng.random()) * basalt["radius"] * 1.2
        add(basalt["x"] + math.cos(bearing) * part, basalt["z"] + math.sin(bearing) * part, 0, 0.25, 2.6, 2.0)
    for spec, count in ((landforms["butte"], 320), (landforms["knob"], 90)):
        for _ in range(count):
            bearing = rng.uniform(0, math.tau)
            part = spec["top"] * (1.05 + rng.exponential(0.35) * spec["apron"] / spec["top"])
            add(spec["x"] + math.cos(bearing) * part, spec["z"] + math.sin(bearing) * part, 1, 0.3, 3.0, 2.0)
    canyon = landforms["canyon"]
    points = canyon["points"]
    for _ in range(300):
        leg = int(rng.integers(0, len(points) - 1))
        part = rng.random()
        (ax, az), (bx, bz) = points[leg], points[leg + 1]
        side = rng.choice([-1.0, 1.0]) * (canyon["floor_half"] + rng.uniform(0, 3))
        length = math.hypot(bx - ax, bz - az)
        add(ax + (bx - ax) * part - (bz - az) / length * side, az + (bz - az) * part + (bx - ax) / length * side,
            1, 0.3, 2.2, 2.2)
    crater = record["craters"][-1]
    for _ in range(70):
        bearing, part = rng.uniform(0, math.tau), crater["d"] / 2 * (1.0 + rng.exponential(0.5))
        add(crater["x"] + math.cos(bearing) * part, crater["z"] + math.sin(bearing) * part, 0, 0.25, 1.2, 2.2)
    half = shaped.grid.side / 2
    for _ in range(1600):
        x, z = rng.uniform(-half, half, 2)
        add(x, z, int(rng.random() < 0.25), 0.2, 1.0, 2.6)
    for rock in found:
        rock["turn"] = round(float(rng.uniform(0, 360)), 1)
    return found


def clear_of(shaped, slope=None):
    """Whether a spot may hold a rock: inside the plan, off the held flats and the paths, and (given the slopes) not
    on a slope of 35 degrees or more."""
    def clear(x, z):
        spot = shaped.grid.index(x, z)
        if spot is None or shaped.held[spot] >= 0.05 or shaped.on_path[spot] >= 0.05:
            return False
        return slope is None or slope[spot] < 35
    return clear


def laid(shaped, record):
    """The ground's rocks by its plan's rule; none for a plan without one."""
    settings = record.get("rocks")
    if not settings:
        return []
    if settings["rule"] == "moon":
        return moon(shaped, settings)
    return mars(shaped, settings, record)
