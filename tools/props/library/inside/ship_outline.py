"""The ship's hull read off the owner's locked plan v7 (data/definitions/ship.json), in plain Python, so the hangar's
kit layout (tools/props/scene/bay_kit.py) and the hull's builder inside Blender (pieces_hull.py) read the same numbers.

The plan's tables are traced from the drawing at its `drawn_length`; the ship is built at its `length`, every number
scaled by length / drawn_length (2026-10-18: 46 m, 1.5 times the drawing's 31 m). The plan's frame, metres: y back
from the nose spike's tip, x across (starboard positive, the side ring's side), z up from the ground the ship stands
on. The tables:
    top        y -> [low, high] of the outline from above, fins and all, in the drawing's own across measure
    side       y -> [low, high] of the outline from the side, in the drawing's own down measure (z = ground - value)
    body_wide  y -> the body's full width at its waist (the white body, fins left out)

A section of the body is a faceted wedge round its waist: a flat keel, a lower chine, the waist (the plan's width),
an upper chine and a flat deck, its top and keel at the side table's heights (SECTION). The ship is built square to
its middle line: the drawing's two sides are averaged and its spike, drawn 1.5 m off the middle line, is put on it.
"""
import json
import math
import pathlib
import statistics

PLAN = pathlib.Path(__file__).resolve().parents[4] / "data/definitions/ship.json"
# A section's corners from the keel up, as (share of the waist's half width, share of the height from the keel).
SECTION = ((0.62, 0.0), (0.95, 0.30), (1.0, 0.48), (0.80, 0.80), (0.55, 1.0))
# The share of the height where the dark lower hull meets the white panels: the waist.
WAIST = SECTION[2][1]
# Stations of the body every this many drawn metres.
STEP = 0.25
# How many rows of the side table a height is the median of (0.9 m drawn): the drawing's small dome on the deck at
# 22.3 m pinched the whole section where the deck's line ran over it.
SMOOTH_ROWS = 9
# Where a fin starts: the outline from above reaching this far (drawn metres) past the body's white top (the outline
# runs 0.1 to 0.3 m outside it along the whole body: the dark side under the white, seen from above).
FIN_FROM = 0.45


def read_plan(path=PLAN):
    """The plan as data/definitions/ship.json holds it."""
    return json.loads(pathlib.Path(path).read_text())


def scale_of(plan):
    """How many built metres a drawn metre is."""
    return plan["length"] / plan["drawn_length"]


def interpolated(rows, at):
    """A table's value at `at` (rows: sorted (key, value) pairs, a value a number or a pair), straight between rows,
    the end rows' value beyond them."""
    if at <= rows[0][0]:
        return rows[0][1]
    for (before, low), (after, high) in zip(rows, rows[1:]):
        if at <= after:
            share = (at - before) / (after - before) if after > before else 0.0
            if isinstance(low, (list, tuple)):
                return [start + (end - start) * share for start, end in zip(low, high)]
            return low + (high - low) * share
    return rows[-1][1]


def body_rows(plan):
    """The body_wide table as sorted (y, width) pairs, drawn metres."""
    return sorted((float(key), value) for key, value in plan["body_wide"].items())


def ground_of(plan):
    """The side table's measure of the ground: the belly's lowest point stands the plan's `legs` over it."""
    return max(row[1][1] for row in plan["side"]) + plan["legs"]


def middle_of(plan):
    """The middle line in the top table's across measure: the median middle of the rows as wide as the body."""
    body = body_rows(plan)
    middles = [(low + high) / 2 for y, (low, high) in plan["top"]
               if body[0][0] <= y <= body[-1][0] and abs((high - low) - interpolated(body, y)) < FIN_FROM]
    return statistics.median(middles)


def spans(plan):
    """The outline from above as sorted (y, half span) pairs, both sides averaged about the middle line, drawn
    metres."""
    middle = middle_of(plan)
    return [(y, ((middle - low) + (high - middle)) / 2) for y, (low, high) in plan["top"]]


def is_fin(span, body_half):
    """Whether an outline's half span at a station reaches out as a fin past the body there."""
    return span - body_half > FIN_FROM


def side_overhang(plan):
    """How far the outline from above runs outside the body's white top where no fin is, its median, drawn metres."""
    body = body_rows(plan)
    return statistics.median(span - interpolated(body, y) / 2 for y, span in spans(plan)
                             if body[0][0] <= y <= body[-1][0] and not is_fin(span, interpolated(body, y) / 2))


def waist_half(plan, along, overhang):
    """The hull's half width at its waist `along` drawn metres from the tip: the outline from above, or past a fin
    the body's white top with the outline's usual overhang."""
    body_half = interpolated(body_rows(plan), along) / 2
    span = interpolated(spans(plan), along)
    return body_half + overhang if is_fin(span, body_half) else max(span, body_half)


def side_rows(plan):
    """The side table with each row's top and keel the median of SMOOTH_ROWS rows round it."""
    rows, half = plan["side"], SMOOTH_ROWS // 2
    return [(y, [statistics.median(row[1][end] for row in rows[max(0, index - half):index + half + 1])
                 for end in (0, 1)]) for index, (y, _) in enumerate(rows)]


def heights_at(plan, along, ground, side=None):
    """(keel, top) `along` drawn metres from the tip, drawn metres over the ground (`side`: side_rows, read once by a
    caller in a loop)."""
    low, high = interpolated(side or side_rows(plan), along)
    return ground - high, ground - low


def stations(plan):
    """The body's stations front to back: {y, half, keel, top}, built metres (y from the spike's tip)."""
    scale, ground, body = scale_of(plan), ground_of(plan), body_rows(plan)
    overhang, side = side_overhang(plan), side_rows(plan)
    first, last = body[0][0], body[-1][0]
    count = int(round((last - first) / STEP))
    found = []
    for index in range(count + 1):
        along = first + (last - first) * index / count
        keel, top = heights_at(plan, along, ground, side)
        half = waist_half(plan, along, overhang)
        if along >= plan["stern_block"]:  # the dark airlock block between the engines, which stand out beside it
            half = min(half, plan["block_wide"] / 2 + overhang)
        found.append({"y": round(along * scale, 4), "half": round(half * scale, 4),
                      "keel": round(keel * scale, 4), "top": round(top * scale, 4)})
    return found


def section(station):
    """A station's corners round the hull as (x, z), starboard keel first, up the starboard side, over the deck and
    down the port side: ten points."""
    height = station["top"] - station["keel"]
    starboard = [(station["half"] * across, station["keel"] + height * up) for across, up in SECTION]
    return starboard + [(-x, z) for x, z in reversed(starboard)]


def fin_spans(plan):
    """[(y, half span)] where the outline from above reaches past the body, both sides averaged, built metres."""
    scale, body = scale_of(plan), body_rows(plan)
    return [(round(y * scale, 4), round(span * scale, 4)) for y, span in spans(plan)
            if body[0][0] <= y <= body[-1][0] and is_fin(span, interpolated(body, y) / 2)]


def fins(plan):
    """Each fin as its outline from above on the starboard side, [(x, y)] round it, built metres: one run of
    fin_spans each, from the body's waist out to the drawn span and back."""
    spans = fin_spans(plan)
    body = [(row["y"], row["half"]) for row in stations(plan)]
    runs, run = [], []
    for y, span in spans:
        if run and y - run[-1][0] > 2 * STEP * scale_of(plan):
            runs.append(run)
            run = []
        run.append((y, span))
    if run:
        runs.append(run)
    return [[(interpolated(body, run[0][0]) * 0.9, run[0][0])] + [(span, y) for y, span in run]
            + [(interpolated(body, run[-1][0]) * 0.9, run[-1][0])] for run in runs if len(run) > 2]


def spike(plan):
    """The nose spike: {from, to (y), z, root, tip (radii)}, built metres, from its tip to the body's front."""
    scale, ground, body = scale_of(plan), ground_of(plan), body_rows(plan)
    widths = sorted(high - low for y, (low, high) in plan["top"] if y < body[0][0])
    keel, top = heights_at(plan, body[0][0] / 2, ground)
    return {"from": 0.0, "to": round(body[0][0] * scale, 4), "z": round((keel + top) / 2 * scale, 4),
            "tip": round(widths[0] / 2 * scale, 4), "root": round(statistics.median(widths) / 2 * scale, 4)}


def station_at(plan, along):
    """The body's station `along` built metres from the tip, straight between the plan's."""
    rows = stations(plan)
    return ({key: interpolated([(row["y"], row[key]) for row in rows], along) for key in ("half", "keel", "top")}
            | {"y": along})


def side_x(station, height):
    """How far out the hull's starboard side is at a height of a station (on its section's facets)."""
    corners = section(station)[:5]
    for (low_out, low), (high_out, high) in zip(corners, corners[1:]):
        if low <= height <= high:
            return low_out + (high_out - low_out) * ((height - low) / (high - low) if high > low else 0.0)
    return corners[-1][0] if height > corners[-1][1] else corners[0][0]


def legs(plan):
    """The landing legs: [{y, x, keel}], built metres, a pair at each of the plan's leg stations, under the keel's
    flat a third of the way in from its edge."""
    scale = scale_of(plan)
    found = []
    for drawn in plan["leg_pairs"]["y"]:
        here = station_at(plan, drawn * scale)
        for side in (1, -1):
            found.append({"y": round(drawn * scale, 4), "x": round(side * here["half"] * SECTION[0][0] * 0.66, 4),
                          "keel": round(here["keel"], 4)})
    return found


def side_ring(plan):
    """The side ring, the docking hatch and the people airlock in one: {y, z, x (where the hull's side is), outer,
    opening (radii)}, built metres; its middle a person's height over the deck."""
    scale, ring = scale_of(plan), plan["side_ring"]
    along = ring["y"] * scale
    height = plan["deck"] * scale + ring["door"]["tall"] / 2 + ring["door"]["sill"]
    here = station_at(plan, along)
    return {"y": round(along, 4), "z": round(height, 4), "x": round(side_x(here, height), 4),
            "outer": round(max(ring["across"] * scale, ring["door"]["tall"] + 2 * ring["collar"]) / 2, 4),
            "opening": round(ring["door"]["tall"] / 2, 4)}


def extents(plan):
    """The built ship's box: (wide, tall, long), fins and all, standing on its feet."""
    rows = stations(plan)
    span = max([row["half"] for row in rows] + [span for _, span in fin_spans(plan)])
    return (round(2 * span, 4), round(max(row["top"] for row in rows), 4), round(plan["length"], 4))


def hull_shows(plan):
    """What the hull's builder is made with (the kit layout's `shows`): its stations, fins, spike, legs, side ring,
    where its white panels stop at the stern block, its cabin windows and how long it is."""
    scale = scale_of(plan)
    return {"stations": stations(plan), "fins": fins(plan), "spike": spike(plan), "legs": legs(plan),
            "ring": side_ring(plan), "stern_block": round(plan["stern_block"] * scale, 4),
            "windows": [round(value * scale, 4) for value in plan["windows"]["y"]], "length": plan["length"]}


def under(station, across):
    """The belly's point under `across` at a station and its outward normal, as ((x, z), (normal x, normal z)): on
    the keel's flat, or on the facet from the keel's edge up to the lower chine."""
    (keel_x, keel_z), (chine_x, chine_z) = section(station)[:2]
    side = 1.0 if across >= 0 else -1.0
    if abs(across) <= keel_x:
        return (across, keel_z), (0.0, -1.0)
    share = min((abs(across) - keel_x) / (chine_x - keel_x), 1.0)
    normal_x, normal_z = (chine_z - keel_z), -(chine_x - keel_x)
    size = math.hypot(normal_x, normal_z)
    return (across, keel_z + (chine_z - keel_z) * share), (side * normal_x / size, normal_z / size)


# Laid sizes (wide, tall, deep) of the lift and nose thrusters, built metres: as wide as the plan's `across`, standing
# out of the hull this far.
LIFT_OUT, NOSE_OUT = 0.3, 0.25


def engine_mounts(plan, entry):
    """The main engines: each lying along the hull, its foot under its middle, its front toward the nose."""
    scale = scale_of(plan)
    radius, (front, back) = entry["across"] * scale / 2, entry["y"]
    return [{"row": "main_engine", "at": (across * scale, (front + back) / 2 * scale, entry["z"] * scale - radius),
             "out": (0.0, 0.0, 1.0), "size": (2 * radius, 2 * radius, (back - front) * scale)}
            for across in entry["x"]]


def lift_mounts(plan, entry):
    """The lift thrusters: each set into the belly under its plan place, pointing out of the hull."""
    scale = scale_of(plan)
    found = []
    for across, along in zip(entry["x"], entry["y"]):
        (_, height), (normal_x, normal_z) = under(station_at(plan, along * scale), across * scale)
        size = entry["across"] * scale
        found.append({"row": "lift_thruster", "at": (across * scale, along * scale, height),
                      "out": (normal_x, 0.0, normal_z), "size": (size, LIFT_OUT, size)})
    return found


def nose_mounts(plan, entry):
    """The nose thrusters: two on the snout's sides at its waist pointing out, one under its keel, one over its
    deck, each on the hull at its plan station."""
    scale = scale_of(plan)
    found = []
    middle_z = sum(entry["z"]) / len(entry["z"])
    for across, along, height in zip(entry["x"], entry["y"], entry["z"]):
        here = station_at(plan, along * scale)
        corners = section(here)
        if across:
            side = 1.0 if across > 0 else -1.0
            at, out = (side * corners[2][0], here["keel"] + (here["top"] - here["keel"]) * WAIST), (side, 0.0, 0.0)
        elif height < middle_z:
            at, out = (0.0, here["keel"]), (0.0, 0.0, -1.0)
        else:
            at, out = (0.0, here["top"]), (0.0, 0.0, 1.0)
        size = entry["across"] * scale
        found.append({"row": "nose_thruster", "at": (at[0], along * scale, at[1]), "out": out,
                      "size": (size, NOSE_OUT, size)})
    return found


def mounts(plan):
    """Every engine and thruster laid on the hull: [{row, at (its foot's middle), out (the way its height points),
    size (wide, tall, deep)}], in the plan's frame, built metres."""
    by_name = {entry["name"]: entry for entry in plan["thrusters"]}
    return (engine_mounts(plan, by_name["main engine"]) + lift_mounts(plan, by_name["lift thruster"])
            + nose_mounts(plan, by_name["nose thruster"]))
