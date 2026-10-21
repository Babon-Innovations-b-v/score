"""What a made ground measures, read off its record (heights picture, zones) against its plan: the scale of its named
landforms and levels, the slope of its flats, paths and seats, and how far it lies from the ground copied in before.

    measures.scale(made, plan_record, shaped)  # {"craters", "hills", "levels", "faults": [...]}
    measures.slope(made, plan_record, inputs)  # {"flats_max", "paths_p99", "rooms": {place: ...}, "faults": [...]}
    measures.compared(made, plan_record, inputs)   # the copied ground's numbers beside the made one's
"""
import json
import pathlib

import numpy as np
from scipy import ndimage

from score.stages.terrain import landforms, outside, plan, record

# A named crater's depth and rim diameter on the made ground within these shares of the same measure on the plan's
# large shape.
CRATER_DEPTH_SHARE = 0.25
CRATER_DIAMETER_SHARE = 0.1
LEVEL_HELD = 0.03
# The record's sixteen-bit heights (record.heights_code): one step is span / CODES metres, the only slack a hill
# range's highest point has past its plan.
CODES = 65535
# A held flat no steeper over a metre than the resting check's drop rule takes as stable (8 degrees; SAGE's,
# tools/usd/triage.py).
FLAT_SLOPE = 8.0
PATH_SLOPE = 15.0
SEAT_STEP = 0.5
# Slopes are read over this many metres (a foot's or a wheel's scale, not one cell's fine relief).
SLOPE_OVER = 1.0
# A room's floor may stand this far under the highest ground under it (its deck's own thickness).
FLOOR_CLEAR = 0.05


def made_heights(made):
    """The made ground's heights in metres, row 0 at the plan's -side/2 along."""
    return record.decoded(pathlib.Path(made["folder"]) / made["heights"], made["low"], made["span"])


def on_grid(made, plan_record):
    """The made heights, the grid they lie on and the plan's masks brought to it."""
    heights = made_heights(made)
    grid = landforms.Grid(made["side"], heights.shape[0])
    shaped_grid = landforms.Grid(plan_record["side"], plan_record["points"])
    held = plan.held_flats(shaped_grid, plan_record["flats"])
    on_path = plan.path_share(shaped_grid, plan_record["paths"]) if plan_record.get("paths") else np.zeros_like(held)
    zoom = heights.shape[0] / held.shape[0]
    return heights, grid, ndimage.zoom(held, zoom, order=1), ndimage.zoom(on_path, zoom, order=1)


def yards(grid, plan_record):
    """Where the plan's levelled yards lie: each level's box grown by its blend (the yard and its bank)."""
    found = np.zeros(grid.x.shape, dtype=bool)
    for level in plan_record.get("levels", []):
        box = level["box"]
        found |= ((grid.x > box[0] - level["blend"]) & (grid.x < box[2] + level["blend"]) &
                  (grid.z > box[1] - level["blend"]) & (grid.z < box[3] + level["blend"]))
    return found


def hill_ranges(heights, grid, plan_record, rounding):
    """Every hill range's highest point beside its planned crest heights over the datum, with a fault when it stands
    outside them by more than `rounding` (the record's height step): {name: {"highest", "planned"[, "fault"]}}."""
    hills = {}
    for name, spec in plan_record.get("landforms", {}).items():
        if "high" not in spec:
            continue
        gap, _ = landforms.segment_distance(grid.x, grid.z, spec["points"])
        top = float(heights[gap < spec["half_wide"]].max())
        hills[name] = {"highest": round(top, 2), "planned": [spec["low"], spec["high"]]}
        if not spec["low"] - rounding <= top <= spec["high"] + rounding:
            hills[name]["fault"] = f"{name} rises to {top:.2f} m, planned {spec['low']} to {spec['high']} m"
    return hills


def scale(made, plan_record, shaped=None):
    """The made ground against the plan's large shape (`shaped`, made again when not given): every named crater's
    depth and rim diameter beside the same measure on the plan's shape, the hill ranges' crests, the held
    waterfront's level and the record's range; and the faults."""
    shaped = shaped or plan.shape(plan_record)
    heights, grid, held, _ = on_grid(made, plan_record)
    large = ndimage.zoom(shaped.heights, heights.shape[0] / shaped.heights.shape[0], order=1)
    planned_grid = plan.Shaped(grid, large, None, None)
    made_grid = plan.Shaped(grid, heights, None, None)
    faults, craters = [], {}
    for crater in plan_record.get("craters", []):
        measured, planned = plan.named_size(made_grid, crater), plan.named_size(planned_grid, crater)
        craters[crater["name"]] = {"measured": measured, "plan": planned}
        deeper = abs(measured["depth"] - planned["depth"]) > CRATER_DEPTH_SHARE * planned["depth"]
        wider = abs(measured["diameter"] - planned["diameter"]) > CRATER_DIAMETER_SHARE * planned["diameter"]
        if deeper or wider:
            faults.append(f"crater {crater['name']} measures {measured['depth']} m deep and {measured['diameter']} m "
                          f"across, its plan {planned['depth']} and {planned['diameter']}")
    hills = hill_ranges(heights, grid, plan_record, made["span"] / CODES)
    faults += [found["fault"] for found in hills.values() if "fault" in found]
    levels = {}
    for step in plan_record["shape"]:
        if step["op"] == "flats" and plan_record.get("water"):
            inside = ndimage.binary_erosion((held > 0.99) & (heights > plan_record["water"]["level"] - 0.5),
                                            iterations=3) & \
                (np.hypot(grid.x - step["middle"][0], grid.z - step["middle"][1]) < step["disc"])
            if inside.any():
                spread = [round(float(heights[inside].min()), 3), round(float(heights[inside].max()), 3)]
                levels["waterfront"] = spread
                if max(abs(value - step["level"]) for value in spread) > LEVEL_HELD:
                    faults.append(f"the waterfront lies {spread} m, planned {step['level']} m")
    clipped = int(np.sum((heights <= -made["low"] + 1e-6) | (heights >= made["span"] - made["low"] - 1e-6)))
    if clipped:
        faults.append(f"{clipped} points clipped by the record's range")
    return {"craters": craters, "hills": hills, "levels": levels, "clipped": clipped,
            "cell": round(made["side"] / (heights.shape[0] - 1), 3), "faults": faults}


def under_floor(made, seat, on_seat, box):
    """The highest and lowest ground under a room's own box, in its frame (its floor at 0), SEAT_STEP apart."""
    from score.stages.terrain import gates
    laid = outside.placed_ground(made, seat, on_seat)
    across = np.arange(box[0][0], box[1][0] + SEAT_STEP, SEAT_STEP)
    along = np.arange(box[0][1], box[1][1] + SEAT_STEP, SEAT_STEP)
    grid_x, grid_z = np.meshgrid(across, along)
    under = gates.heights_under(laid, np.column_stack([grid_x.ravel(), grid_z.ravel()]))
    return float(under.max()), float(under.min())


def exempt(grid, plan_record):
    """The spots the plan exempts from the flats' slope (a yard that holds dug dents)."""
    found = np.zeros(grid.x.shape, dtype=bool)
    for middle_x, middle_z, radius in plan_record.get("slope_exempt", {}).get("discs", []):
        found |= np.hypot(grid.x - middle_x, grid.z - middle_z) < radius
    return found


def slope(made, plan_record, inputs):
    """The held flats' steepest slope over a metre (two cells in from their edge, over land, less the exempt
    yards and the levelled yards with their banks, which the level holds, not the flats: the hangar's yard, held on its
    seat's plane, banks into the base's flat), the paths' 99th percentile over a metre, and every room's floor against the ground under it (the ground
    never above its floor); the faults."""
    from score.stages.terrain import gates
    heights, grid, held, on_path = on_grid(made, plan_record)
    slopes = plan.slopes(ndimage.gaussian_filter(heights, SLOPE_OVER / grid.cell), grid.cell)
    flats = ndimage.binary_erosion(held > 0.99, iterations=2) & ~exempt(grid, plan_record) & ~yards(grid, plan_record)
    if made.get("water"):
        flats &= ndimage.binary_erosion(heights > made["water"]["level"] - 0.5, iterations=3)
    found = {"flats_max": round(float(slopes[flats].max()), 2) if flats.any() else 0.0,
             "paths_p99": round(float(np.percentile(slopes[on_path > 0.99], 99)), 2) if np.any(on_path > 0.99)
             else None, "rooms": {}}
    faults = []
    if found["flats_max"] > FLAT_SLOPE:
        faults.append(f"a held flat slopes {found['flats_max']} degrees over a metre (at most {FLAT_SLOPE})")
    if found["paths_p99"] is not None and found["paths_p99"] > PATH_SLOPE:
        faults.append(f"paths slope {found['paths_p99']} degrees at the 99th percentile (at most {PATH_SLOPE})")
    for place, seat in plan_record["seats"].items():
        if seat.get("outdoor"):
            continue
        scene, kit = gates.place_files(inputs, place)
        if not scene:
            continue
        highest, lowest = under_floor(made, seat, (kit or {}).get("on_seat", [0.0, 0.0]), gates.footprint(scene, kit))
        found["rooms"][place] = {"ground_highest": round(highest, 3), "ground_lowest": round(lowest, 3)}
        if highest > FLOOR_CLEAR:
            faults.append(f"{place}: the ground rises {highest:.2f} m over its floor")
    found["faults"] = faults
    return found


def compared(made, plan_record, inputs):
    """The made ground beside the one copied in before (a ball's: its heights and rocks; the Earth's: the old disc):
    the height difference over the square (RMS, after a 1 m smoothing, its 99th percentile) and the rocks laid the
    same."""
    copied = plan_record.get("copied", {})
    if "record" not in copied:
        return {"copied": "the old flat disc", "disc_radius": copied.get("disc", {}).get("radius")}
    folder = pathlib.Path(inputs["grounds"])
    old = json.loads((folder / copied["record"]).read_text())
    before = record.decoded(folder / old["heights"], old["low"], old["span"])
    after = made_heights(made)
    if before.shape != after.shape:
        before = ndimage.zoom(before, after.shape[0] / before.shape[0], order=1)
    difference = after - before
    pixels_a_metre = after.shape[0] / made["side"]
    old_rocks = json.loads((folder / copied["rocks"]).read_text())["rocks"]
    new_rocks = json.loads((pathlib.Path(made["folder"]) / made["rocks"]).read_text())
    same = sum(abs(first["x"] - second["x"]) < 0.01 and abs(first["z"] - second["z"]) < 0.01 and
               abs(first["size"] - second["size"]) < 0.01 for first, second in zip(new_rocks, old_rocks))
    return {"rms_m": round(float(difference.std()), 3), "mean_m": round(float(difference.mean()), 3),
            "p99_abs_m": round(float(np.percentile(np.abs(difference), 99)), 3),
            "smoothed_1m_rms_m": round(float(ndimage.gaussian_filter(difference, pixels_a_metre).std()), 3),
            "range_before": [round(float(before.min()), 2), round(float(before.max()), 2)],
            "range_after": [round(float(after.min()), 2), round(float(after.max()), 2)],
            "rocks": {"before": len(old_rocks), "after": len(new_rocks), "the same": same}}
