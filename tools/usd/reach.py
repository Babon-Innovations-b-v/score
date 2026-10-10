"""The reach check: a walker on a place's floor reaches a standing spot in front of every inventory row, or the place
fails (the owner's automatic playtest, 2026-10-05: walk to each object; the interact press waits for interactable
assets).

    .venv/bin/python tools/usd/reach.py <place> [--stage <stage.usda>] [--out reach.json]

The walker is the cast check's (tools/characters/cast_check.py): a body BODY_RADIUS round its middle, HEAD tall,
stepping up or down no more than KNEE. Where it can stand is found Recast's way (Mononen's navigation mesh: a
heightfield of spans over a grid, a span walkable when nothing stands in the agent's height over it, the walkable area
eroded by the agent's radius, neighbouring spans joined when the step between them is climbable), on a grid of CELL,
half the body's radius (Recast's advice for the cell size):

- every object, Structure and Fixtures mesh over the grid is read as points: SAMPLES_PER_M2 seeded points a square
  metre of its faces and points every EDGE_STEP along each face's edges; a point lying within TOUCH of a cell's edge
  counts in both cells, as Recast's rasterisation counts a triangle in every column it touches;
- a cell's spans are the heights of the floors in it (points on faces that look up, leaning less than MAX_SLOPE;
  points within SPAN_GAP of each other are one span, at its top) and the ground under its middle;
- a span is clear when no point lies between SPAN_GAP and HEAD over it in its cell (no deck or table top over the
  walker) and, in a room whose scene record gives its `ceiling`, its HEAD stays under the ceiling (a roof's top is
  not a floor of the room); it is a standing spot when its middle lies no nearer than BODY_RADIUS to a cell it cannot
  step into (a wall, an obstacle or a drop beside it), counted in cells through the climbable steps;
- inside a place whose scene record has a `floor` (a room: its rectangle) the grid is that floor; elsewhere it runs
  REACH plus a cell past every row's objects;
- the walker's floor is the set of standing spots joined by four-way steps no higher than KNEE that most of the scene
  record's views stand on (the game's own shots; the larger set on a tie, the largest when no view stands on one),
  since no spawn is recorded. A view stands at the nearest standing spot within REACH of its eye, no higher than the
  eye and no more than HEAD and ARM under it; the views off the walker's floor are named in the result's note.

A row is reached when a standing spot of the walker's floor lies within REACH of the footprint (x, z) of one of its
objects (a prim carrying `score:row`), and that object reaches up to the spot less a KNEE (a thing on a storey under the
walker is not in front of it) and, when the row stands on a floor or on a thing (its `anchor`), down to the walker's
HEAD and ARM over the spot (a thing on a storey over the walker is not in front of it either; one on a wall or the
ceiling is in front of the walker under it). REACH is the body and an arm (an adult's arm, shoulder to fingertip, is
about 0.75 m). A row with no object on the stage and no written drop reason is unknown (the rows check says why); a
dropped or held-back row is not walked to. The check fails when a row is not reached, and is unknown when the walker has
no floor or a row is unknown.
"""
import argparse
import json
import pathlib
import sys

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "tools/characters"))
import cast_check  # noqa: E402
import snap  # noqa: E402

BODY_RADIUS, KNEE, HEAD = cast_check.BODY_RADIUS, cast_check.KNEE, cast_check.HEAD
CELL = BODY_RADIUS / 2
ARM = 0.75
REACH = BODY_RADIUS + ARM
SAMPLES_PER_M2 = 16 / CELL ** 2
MAX_SLOPE = 45.0
SPAN_GAP = 0.1
TOUCH = 0.01
EDGE_STEP = CELL / 4
SCENES = REPO / "data/scene"
PASS, FAIL, UNKNOWN = "pass", "fail", "unknown"


# --- what the walker walks to -------------------------------------------------------------------------------------

def row_targets(stage_path, place):
    """Each row's objects on the stage: {row: [(prim path, x low, z low, x high, z high, y low, y high)]}, the box of
    every visible mesh under each prim that carries `score:row`, the other places the stage shows (`Places`, with rows
    of their own) left out."""
    from pxr import Usd, UsdGeom
    stage = Usd.Stage.Open(str(stage_path))
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found = {}
    walk = iter(Usd.PrimRange(stage.GetPrimAtPath(f"/{place}")))
    for prim in walk:
        if prim.GetPath() == f"/{place}/Places":
            walk.PruneChildren()
        if not prim.HasAttribute("score:row"):
            continue
        extent = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if extent.IsEmpty():
            continue
        low, high = extent.GetMin(), extent.GetMax()
        found.setdefault(prim.GetAttribute("score:row").Get(), []).append(
            (str(prim.GetPath()), low[0], low[2], high[0], high[2], low[1], high[1]))
    return found


def walked_rows(inventory):
    """The rows the walker walks to: every row not dropped with a reason and not held back."""
    held_back = {row["id"] for row in inventory.get("held_back", []) if row.get("why_code") or row.get("why")}
    return [row for row in inventory["rows"]
            if not str(row.get("dropped", "")).strip() and row["id"] not in held_back]


# --- the grid -----------------------------------------------------------------------------------------------------

def record_of(place):
    """The place's scene record, or {} when it has none."""
    record = SCENES / f"{place}.json"
    return json.loads(record.read_text()) if record.exists() else {}


def grid_bounds(record, targets):
    """The rectangle the grid covers (x low, z low, x high, z high): the scene record's room floor, else every row's
    objects with REACH and a cell round them."""
    if record.get("floor"):
        (x_low, z_low), (x_high, z_high) = record["floor"]
        return x_low, z_low, x_high, z_high
    boxes = np.array([box[1:5] for boxes in targets.values() for box in boxes])
    pad = REACH + CELL
    return boxes[:, 0].min() - pad, boxes[:, 1].min() - pad, boxes[:, 2].max() + pad, boxes[:, 3].max() + pad


class Grid:
    """The cells over a rectangle: their middles along x and z, and each point's cell."""

    def __init__(self, bounds):
        self.xs = np.arange(bounds[0] + CELL / 2, bounds[2], CELL)
        self.zs = np.arange(bounds[1] + CELL / 2, bounds[3], CELL)
        self.shape = (len(self.xs), len(self.zs))

    def cells_touched(self, points):
        """Each cell a point lies in or within TOUCH of (a surface on a cell's edge counts in both cells, as Recast's
        conservative rasterisation counts a triangle in every column it touches): (the point's index, the cell in the
        grid's flat order)."""
        across = (points[:, 0] - (self.xs[0] - CELL / 2)) / CELL
        along = (points[:, 2] - (self.zs[0] - CELL / 2)) / CELL
        columns, rows = np.floor(across).astype(np.int64), np.floor(along).astype(np.int64)
        every = np.ones(len(points), bool)
        sides_x = {-1: across - columns < TOUCH / CELL, 0: every, 1: columns + 1 - across < TOUCH / CELL}
        sides_z = {-1: along - rows < TOUCH / CELL, 0: every, 1: rows + 1 - along < TOUCH / CELL}
        which, cells = [], []
        for step_x, near_x in sides_x.items():
            for step_z, near_z in sides_z.items():
                picked = np.flatnonzero(near_x & near_z)
                column, row = columns[picked] + step_x, rows[picked] + step_z
                inside = (column >= 0) & (column < self.shape[0]) & (row >= 0) & (row < self.shape[1])
                which.append(picked[inside])
                cells.append(np.ravel_multi_index((column[inside], row[inside]), self.shape))
        return np.concatenate(which), np.concatenate(cells)

    def middles(self):
        """Every cell's middle (x, z), in the grid's flat order."""
        return np.array(np.meshgrid(self.xs, self.zs, indexing="ij")).reshape(2, -1).T


# --- the surfaces -------------------------------------------------------------------------------------------------

def over_grid(mesh, bounds):
    """The part of a mesh whose faces reach over the grid's rectangle (None when none does)."""
    corners = mesh.vertices[mesh.faces]
    over = ((corners[:, :, 0].max(axis=1) >= bounds[0]) & (corners[:, :, 0].min(axis=1) <= bounds[2])
            & (corners[:, :, 2].max(axis=1) >= bounds[1]) & (corners[:, :, 2].min(axis=1) <= bounds[3]))
    return mesh.submesh([np.flatnonzero(over)], append=True) if over.any() else None


def cropped(laid, bounds):
    """Every object, Structure and Fixtures mesh over the grid, cut down to the faces that reach over it."""
    found = [over_grid(mesh, bounds) for mesh in [*laid["objects"].values(), *laid["statics"].values()]
             if len(mesh.faces)]
    return [mesh for mesh in found if mesh is not None]


def surface_samples(mesh):
    """A mesh as points: SAMPLES_PER_M2 seeded points a square metre of its faces and points every EDGE_STEP along
    each face's edges (a face's edge on a cell's border then touches both cells), (points (count, 3), whether each lies
    on a face that looks up, leaning less than MAX_SLOPE: a floor, not a wall or a slab's underside)."""
    import trimesh
    level = mesh.face_normals[:, 1] >= np.cos(np.radians(MAX_SLOPE))
    count = int(np.ceil(mesh.area * SAMPLES_PER_M2))
    sampled, faces = trimesh.sample.sample_surface(mesh, count, seed=0) if count else (np.zeros((0, 3)), [])
    along, edge_faces = edge_points(mesh)
    return np.vstack([np.asarray(sampled), along]), np.concatenate([level[faces], level[edge_faces]])


def edge_points(mesh):
    """Points along every face's edges, corners included, no more than EDGE_STEP apart, and each one's face."""
    corners = mesh.vertices[mesh.faces]
    starts = corners.reshape(-1, 3)
    ends = corners[:, [1, 2, 0]].reshape(-1, 3)
    counts = np.ceil(np.linalg.norm(ends - starts, axis=1) / EDGE_STEP).astype(int) + 1
    edge = np.repeat(np.arange(len(starts)), counts)
    shares = np.arange(counts.sum()) - np.repeat(np.cumsum(counts) - counts, counts)
    shares = shares / np.maximum(np.repeat(counts, counts) - 1, 1)
    return starts[edge] + (ends[edge] - starts[edge]) * shares[:, None], edge // 3


def floor_points(grid, meshes, ground):
    """Every height a floor lies at in each cell: the meshes' points on faces that look up, a mesh at a time and kept
    once a centimetre, and the ground under each cell's middle; (cells, heights), sorted by cell then height."""
    cells, heights = [], []
    for mesh in meshes:
        points, flat = surface_samples(mesh)
        which, touched = grid.cells_touched(points[flat])
        keys = np.unique(np.column_stack([touched, np.round(points[flat][which, 1] * 100).astype(np.int64)]), axis=0)
        cells.append(keys[:, 0])
        heights.append(keys[:, 1] / 100.0)
    under = np.asarray(ground(grid.middles()), dtype=float)
    known = np.flatnonzero(np.isfinite(under))
    cells, heights = np.concatenate(cells + [known]), np.concatenate(heights + [under[known]])
    order = np.lexsort((heights, cells))
    return cells[order], heights[order]


def spans(cells, heights):
    """Every cell's spans from its floor heights (sorted by cell then height): a run of heights none more than
    SPAN_GAP over the one under it is one span, at its top; (span cells, span heights), sorted the same way."""
    top = np.ones(len(cells), dtype=bool)
    top[:-1] = (cells[1:] != cells[:-1]) | (heights[1:] - heights[:-1] > SPAN_GAP)
    return cells[top], heights[top]


def clear_overhead(grid, meshes, span_cells, span_heights):
    """Whether no point of the meshes lies between SPAN_GAP and HEAD over each span in its cell (no deck or table top
    over the walker; under SPAN_GAP lies the span's own surface), a mesh at a time: each point marks the run of spans
    of its cell it stands over."""
    bottom = span_heights.min(initial=0.0) - 2 * HEAD
    stride = span_heights.max(initial=0.0) - bottom + 4 * HEAD
    keys = span_cells * stride + (span_heights - bottom)
    marks = np.zeros(len(span_cells) + 1, dtype=np.int64)
    for mesh in meshes:
        points, _ = surface_samples(mesh)
        which, cells = grid.cells_touched(points)
        heights = np.clip(points[which, 1], bottom, bottom + stride - 2 * HEAD) - bottom
        first = np.searchsorted(keys, cells * stride + heights - HEAD, side="right")
        last = np.searchsorted(keys, cells * stride + heights - SPAN_GAP, side="left")
        over = last > first
        np.add.at(marks, first[over], 1)
        np.add.at(marks, last[over], -1)
    return np.cumsum(marks)[:-1] == 0


# --- the walker's floor -------------------------------------------------------------------------------------------

def steps_between(grid, span_cells, span_heights):
    """Every pair of spans (index, index) in four-way neighbouring cells with a step no higher than KNEE between, the
    second one cell further along x (axis 0) or z (axis 1): (starts, ends, axes)."""
    total = grid.shape[0] * grid.shape[1]
    first = np.searchsorted(span_cells, np.arange(total), side="left")
    count = np.searchsorted(span_cells, np.arange(total), side="right") - first
    columns, rows = np.unravel_index(span_cells, grid.shape)
    starts, ends, axes = [np.zeros(0, int)], [np.zeros(0, int)], [np.zeros(0, int)]
    for axis, (step_x, step_z) in enumerate(((1, 0), (0, 1))):
        on = (columns + step_x < grid.shape[0]) & (rows + step_z < grid.shape[1])
        here = np.flatnonzero(on)
        there_cells = np.ravel_multi_index((columns[here] + step_x, rows[here] + step_z), grid.shape)
        for nth in range(int(count.max(initial=0))):
            has = count[there_cells] > nth
            there = first[there_cells[has]] + nth
            climbable = np.abs(span_heights[there] - span_heights[here[has]]) <= KNEE
            starts.append(here[has][climbable])
            ends.append(there[climbable])
            axes.append(np.full(int(climbable.sum()), axis))
    return np.concatenate(starts), np.concatenate(ends), np.concatenate(axes)


def room_for_body(span_count, steps, clear):
    """Whether each clear span has room for the body: its middle no nearer than BODY_RADIUS to a cell it cannot step
    into (a wall, an obstacle or a drop), counted in whole cells through the steps between clear spans from the
    border spans, those missing a climbable step to a clear span in one of their four neighbouring cells (Recast's
    erosion of the walkable area by the agent's radius)."""
    starts, ends, axes = steps
    joined = clear[starts] & clear[ends]
    starts, ends, axes = starts[joined], ends[joined], axes[joined]
    ways = np.zeros((span_count, 4), dtype=bool)
    ways[starts, axes] = True
    ways[ends, axes + 2] = True
    border = clear & ~ways.all(axis=1)
    near, steps_out = border.copy(), 1
    while (steps_out + 0.5) * CELL < BODY_RADIUS:  # a border span's middle is half a cell from what stops it
        grown = near.copy()
        grown[ends[near[starts]]] = True
        grown[starts[near[ends]]] = True
        near, steps_out = grown, steps_out + 1
    return clear & ~near


def components(span_count, steps, standing):
    """Each span's set of standing spans joined by climbable four-way steps (a label; spans that cannot be stood on
    are labelled too, and never chosen)."""
    starts, ends, _ = steps
    both = standing[starts] & standing[ends]
    graph = coo_matrix((np.ones(both.sum()), (starts[both], ends[both])), shape=(span_count,) * 2)
    return connected_components(graph, directed=False)[1]


def view_spots(grid, span_cells, span_heights, standing, views):
    """The standing span each of the record's views stands at: the nearest within REACH of its eye (x, z) that lies
    no higher than the eye and no more than HEAD and ARM under it; {view name: span index, or None}."""
    middles = grid.middles()[span_cells]
    found = {}
    for view in views:
        eye = np.asarray(view["eye"], dtype=float)
        gaps = np.hypot(middles[:, 0] - eye[0], middles[:, 1] - eye[2])
        under = standing & (gaps <= REACH) & (span_heights <= eye[1]) & (span_heights >= eye[1] - HEAD - ARM)
        found[view["name"]] = int(np.flatnonzero(under)[np.argmin(gaps[under])]) if under.any() else None
    return found


def chosen_floor(labels, standing, voters):
    """The walker's floor: the set of standing spans most views stand on (the larger on a tie), else the largest; a
    mask over the spans."""
    if not standing.any():
        return np.zeros_like(standing)
    sizes = np.bincount(labels[standing], minlength=labels.max() + 1)
    votes = np.bincount(labels[voters], minlength=len(sizes)) if voters else np.zeros(len(sizes), int)
    return standing & (labels == int(np.lexsort((sizes, votes))[-1]))


def walker_floor(laid, record, targets):
    """Where the walker can stand: the grid, every span (cell, height), the walker's floor as a mask over the spans,
    and the span each of the record's views stands at."""
    bounds = grid_bounds(record, targets)
    grid = Grid(bounds)
    meshes = cropped(laid, bounds)
    span_cells, span_heights = spans(*floor_points(grid, meshes, laid["height"]))
    clear = clear_overhead(grid, meshes, span_cells, span_heights)
    if record.get("ceiling") is not None:
        clear &= span_heights + HEAD <= float(record["ceiling"])
    steps = steps_between(grid, span_cells, span_heights)
    standing = room_for_body(len(span_cells), steps, clear)
    labels = components(len(span_cells), steps, standing)
    at = view_spots(grid, span_cells, span_heights, standing, record.get("views", []))
    floor = chosen_floor(labels, standing, [spot for spot in at.values() if spot is not None])
    return grid, span_cells, span_heights, floor, at


# --- the check ----------------------------------------------------------------------------------------------------

def near_box(grid, floor_cells, box):
    """The walker's floor spans (indices into its cells, sorted by cell) whose cells lie within REACH of a box's
    footprint along x and along z."""
    _, x_low, z_low, x_high, z_high, _, _ = box
    first_column = max(int(np.floor((x_low - REACH - grid.xs[0]) / CELL)), 0)
    last_column = min(int(np.ceil((x_high + REACH - grid.xs[0]) / CELL)), grid.shape[0] - 1)
    first_row = max(int(np.floor((z_low - REACH - grid.zs[0]) / CELL)), 0)
    last_row = min(int(np.ceil((z_high + REACH - grid.zs[0]) / CELL)), grid.shape[1] - 1)
    if first_column > last_column or first_row > last_row:
        return np.zeros(0, int)
    columns = np.arange(first_column, last_column + 1)
    starts = np.searchsorted(floor_cells, columns * grid.shape[1] + first_row, side="left")
    ends = np.searchsorted(floor_cells, columns * grid.shape[1] + last_row, side="right")
    return np.concatenate([np.arange(start, end) for start, end in zip(starts, ends)])


def gaps(box, spots, stands):
    """How far each standing spot (x, z, height) lies from the object's footprint (inf where the object is not level
    with it: it must reach up to the spot's height less a KNEE and, when it stands on a floor or a thing, down to the
    walker's HEAD and ARM over it; a thing on a wall or the ceiling is in front of the walker under it)."""
    _, x_low, z_low, x_high, z_high, y_low, y_high = box
    gap_x = np.maximum(np.maximum(x_low - spots[:, 0], spots[:, 0] - x_high), 0.0)
    gap_z = np.maximum(np.maximum(z_low - spots[:, 1], spots[:, 1] - z_high), 0.0)
    level = (spots[:, 2] <= y_high + KNEE) & (not stands or (y_low <= spots[:, 2] + HEAD + ARM))
    return np.where(level, np.hypot(gap_x, gap_z), np.inf)


def row_verdicts(rows, targets, grid, floor_cells, spots):
    """Each walked row's result: [{row, result, why}]; a row not reached says how near the walker comes."""
    verdicts = []
    for entry in rows:
        row, boxes = entry["id"], targets.get(entry["id"], [])
        if not boxes:
            verdicts.append({"row": row, "result": UNKNOWN, "why": "no object of this row on the stage"})
            continue
        stands = entry.get("anchor", "floor") == "floor" or str(entry.get("anchor")).startswith("on:")
        hits = sum(bool((gaps(box, spots[near_box(grid, floor_cells, box)], stands) <= REACH).any())
                   for box in boxes)
        if hits:
            verdicts.append({"row": row, "result": PASS, "why": f"{hits} of {len(boxes)} objects reached"})
            continue
        nearest = min(gaps(box, spots, stands).min(initial=np.inf) for box in boxes)
        verdicts.append({"row": row, "result": FAIL,
                         "why": f"none of its {len(boxes)} objects has a standing spot within {REACH:.2f} m on the "
                         f"walker's floor (the nearest: {nearest:.2f} m)"})
    return verdicts


def check(stage_path, place, inventory):
    """The reach check on a place's stage: (result, every walked row's verdict, a note)."""
    targets = row_targets(stage_path, place)
    rows = walked_rows(inventory)
    if not targets:
        return UNKNOWN, [{"row": row["id"], "result": UNKNOWN, "why": "no object of this row on the stage"}
                         for row in rows], \
            "no object on the stage carries a row"
    grid, span_cells, span_heights, floor, at = walker_floor(snap.read_place(stage_path), record_of(place), targets)
    middles = grid.middles()[span_cells[floor]]
    spots = np.column_stack([middles, span_heights[floor]])
    off = [name for name, spot in at.items() if spot is None or not floor[spot]]
    note = (f"walker's floor {len(spots) * CELL * CELL:.1f} m2, {len(at) - len(off)} of {len(at)} views stand on it"
            + (f" (not: {', '.join(off)})" if off else ""))
    if not len(spots):
        return UNKNOWN, [{"row": row["id"], "result": UNKNOWN, "why": "the walker has no floor"} for row in rows], note
    verdicts = row_verdicts(rows, targets, grid, span_cells[floor], spots)
    results = {verdict["result"] for verdict in verdicts}
    return FAIL if FAIL in results else UNKNOWN if UNKNOWN in results else PASS, verdicts, note


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("place")
    parser.add_argument("--stage", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    options = parser.parse_args()
    import complete
    stage = complete.stage_path(options.place, options.stage)
    inventory = json.loads(complete.recorded_inventory(options.place, stage).read_text())
    overall, verdicts, note = check(stage, options.place, inventory)
    failing = [verdict for verdict in verdicts if verdict["result"] != PASS]
    if options.out:
        options.out.write_text(json.dumps({"place": options.place, "result": overall, "note": note,
                                           "rows": verdicts}, indent=1) + "\n")
    for verdict in failing:
        print(f"  {verdict['row']}: {verdict['result']}: {verdict['why']}")
    print(f"{options.place}: {overall}: {len(verdicts) - len(failing)} of {len(verdicts)} rows reached ({note})")


if __name__ == "__main__":
    main()
