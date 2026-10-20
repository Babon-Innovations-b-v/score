"""Terrain: Mars's ground plan (`data/ground/plan/mars.json`) raised by `score.stages.terrain.plan` itself, one group
of its plan steps after another: the gentle base, the landforms, the craters, the canyon, then the flats and paths
the places stand on. Each step's heights are the real grid's, averaged down to SIDE x SIDE for the page."""
import json

from score.stages.terrain import plan

ALGORITHM = "terrain_landforms"
GROUND = "mars"
SIDE = 64  # the page's grid; the plan's 2048 points a side are averaged down to it
GROUPS = (("The plain's tilt and gentle swell", ("tilt", "noise")),
          ("Landforms added: basalt flows, a ridge, a butte, a knob, dunes", ("add", "over")),
          ("Craters laid, oldest first, then the canyon cut", ("craters",)),
          ("Flats levelled and paths graded for the places", ("flats", "paths", "cap")))


def averaged(heights):
    """The heights averaged down to SIDE x SIDE, rows north to south, to the decimetre."""
    block = heights.shape[0] // SIDE
    cut = heights[:block * SIDE, :block * SIDE]
    small = cut.reshape(SIDE, block, SIDE, block).mean(axis=(1, 3))
    return [[round(float(value), 1) for value in row] for row in small]


def group_ends(record):
    """The index of each group's last step in the plan's own order: the step before the next group's first."""
    kinds = [step["op"] for step in record["shape"]]
    starts = [min(rank for rank, kind in enumerate(kinds) if kind in ops) for _, ops in GROUPS]
    return [start - 1 for start in starts[1:]] + [len(kinds) - 1]


def stepped(record):
    """The heights after each group of plan steps, run as `plan.shape` runs them."""
    grid = plan.landforms.Grid(record["side"], record["points"])
    held = plan.held_flats(grid, record["flats"])
    on_path = plan.path_share(grid, record["paths"]) if record.get("paths") else plan.np.zeros_like(held)
    shaped = plan.Shaped(grid, plan.np.zeros_like(grid.x), held, on_path)
    ends, found = group_ends(record), []
    for rank, step in enumerate(record["shape"]):
        shaped.heights = plan.run_step(shaped, record, step)
        if rank in ends:
            found.append(averaged(shaped.heights.astype(plan.np.float64)))
    shaped.heights = shaped.heights.astype(plan.np.float64)
    plan.held_crests(shaped, record)  # as plan.shape ends: the hill ranges held under their planned highs
    found[-1] = averaged(shaped.heights)
    return found, shaped


def made(inputs):
    record = json.loads((inputs.repo / "data/ground/plan" / f"{GROUND}.json").read_text())
    steps, shaped = stepped(record)
    final = plan.np.asarray(steps[-1])
    return {
        "example": f"the {GROUND} ground plan, {record['side']:.0f} m across",
        "view": "relief",
        "relief": {"size": [record["side"], record["side"]], "heights": steps[-1],
                   "steps": [{"label": label, "heights": heights} for (label, _), heights in zip(GROUPS, steps)]},
        "steps": [],
        "numbers": [{"label": "across", "value": round(record["side"]), "unit": "m", "tip": "the plan's side"},
                    {"label": "craters", "value": len(shaped.craters), "unit": "", "tip": "named and small craters"},
                    {"label": "highest", "value": round(float(final.max()), 1), "unit": "m",
                     "tip": "highest point, averaged over the page's grid"},
                    {"label": "lowest", "value": round(float(final.min()), 1), "unit": "m",
                     "tip": "lowest point, averaged over the page's grid"}]}
