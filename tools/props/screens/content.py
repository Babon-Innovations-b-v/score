"""The library's screen picture: what a screen shows behind its glass, drawn by rule from its seed and its place's own
plan, in two of the scene's palette tokens (#88). The `screen` recipe (tools/props/library/recipes.py: dark glass, its
content a picture lit from behind) takes it as its picture; the screens stage (score/stages/screens) gives it to each
screen row's display parts. No model call, no picture generation, no Blender: numpy and Pillow, free on this PC.

The seed chooses the layout: the place's plan (its outline and walls, its doors as gaps with a mark, its items as
boxes, beside a column of status text and a small chart) where the place has a plan, or a dashboard (a title bar over
panels of line charts, bar charts, status text bars and tables). Every count, length and value is drawn from the seed,
so screens of other seeds differ. A level at each pixel says what lights it: 0 the bare glass, FAINT a frame, grid,
axis or item outline, ITEM_LIT a lit item of the plan, 1 the content at full.

    levels(seed, size, plan=None)           the picture's levels, rows top first, 0 to 1
    channels(glass, ink, levels)            (base colour, emission) as the screen recipe mixes them, linear RGB
    write(glass, ink, seed, folder, name, size, plan)   the two as sRGB PNGs; their paths and the lit share

    python3 tools/props/screens/content.py <glass #rrggbb> <ink #rrggbb> <seed> <out.png> [<plan.json>]
"""
import json
import pathlib
import sys

import numpy as np

# A frame, grid, axis or outline against the content at full.
FAINT = 0.35
# The picture's size in pixels (across, up): a 16:10 panel.
SIZE = (1024, 640)
# Under the title bar (its foot at TITLE of the height from the top), the dashboard's panels across and up.
TITLE, COLUMNS, ROWS = 0.14, 3, 2
# A drawn line's half width, in pixels.
LINE = 2.0
# A plan item covering more than this share of the plan's box is its floor or shell, not drawn; a lit item's level.
ITEM_MOST, ITEM_LIT = 0.25, 0.55


def grid(size):
    """Pixel centres as (u across, v down), each 0 to 1."""
    width, height = size
    return np.meshgrid((np.arange(width) + 0.5) / width, (np.arange(height) + 0.5) / height)


def boxed(u, v, box):
    """Where (u, v) lies inside box (left, top, right, bottom), and the coordinates across it (0 to 1)."""
    left, top, right, bottom = box
    inside = (u > left) & (u < right) & (v > top) & (v < bottom)
    return inside, (u - left) / (right - left), (v - top) / (bottom - top)


def outline(u, v, box, size, width=LINE):
    """A box's frame, `width` pixels wide."""
    left, top, right, bottom = box
    near_u, near_v = width / size[0], width / size[1]
    inside = (u > left - near_u) & (u < right + near_u) & (v > top - near_v) & (v < bottom + near_v)
    within = (u > left + near_u) & (u < right - near_u) & (v > top + near_v) & (v < bottom - near_v)
    return inside & ~within


def segment(x, y, start, end, width):
    """Where pixels at (x, y) (in pixels) lie within `width` of the segment from start to end."""
    along = np.subtract(end, start, dtype=float)
    length = max(float(along @ along), 1e-9)
    share = np.clip(((x - start[0]) * along[0] + (y - start[1]) * along[1]) / length, 0.0, 1.0)
    return np.hypot(x - start[0] - share * along[0], y - start[1] - share * along[1]) <= width


def line_chart(x, y, rng):
    """A trace of two waves across the panel over faint axes."""
    first, second = rng.uniform(4.0, 11.0, 2)
    phase = rng.uniform(0.0, 2 * np.pi, 2)
    curve = 0.5 + 0.22 * np.sin(x * first + phase[0]) + 0.12 * np.sin(x * (2.3 * second) + phase[1])
    axes = (x < 0.012) | (y > 0.98)
    return np.maximum(np.abs((1.0 - y) - curve) < 0.03, FAINT * axes)


def bar_chart(x, y, rng):
    """Seven to twelve bars on a faint baseline, each its own height."""
    count = int(rng.integers(7, 13))
    heights = rng.uniform(0.12, 0.92, count)
    index = np.clip((x * count).astype(int), 0, count - 1)
    bars = ((x * count) % 1.0 > 0.2) & ((x * count) % 1.0 < 0.8) & ((1.0 - y) < heights[index])
    return np.maximum(bars, FAINT * (y > 0.98))


def text_bars(x, y, rng):
    """Five to eight lines of status text drawn as bars, each its own length, some lit at full, the rest faint."""
    count = int(rng.integers(5, 9))
    lengths, lit = rng.uniform(0.25, 0.95, count), rng.random(count) > 0.4
    index = np.clip((y * count).astype(int), 0, count - 1)
    drawn = ((y * count) % 1.0 > 0.35) & ((y * count) % 1.0 < 0.65) & (x < lengths[index])
    return drawn * np.where(lit[index], 1.0, FAINT)


def table_grid(x, y, rng):
    """A faint table of four to six columns and five to eight rows, a few of its cells lit."""
    columns, rows = int(rng.integers(4, 7)), int(rng.integers(5, 9))
    filled = rng.random((rows, columns)) > 0.72
    column, row = np.clip((x * columns).astype(int), 0, columns - 1), np.clip((y * rows).astype(int), 0, rows - 1)
    rules = ((x * columns) % 1.0 < 0.03) | ((y * rows) % 1.0 < 0.04)
    cells = filled[row, column] & ((x * columns) % 1.0 > 0.1) & ((x * columns) % 1.0 < 0.9) & \
        ((y * rows) % 1.0 > 0.2) & ((y * rows) % 1.0 < 0.8)
    return np.maximum(FAINT * rules, cells)


KINDS = (line_chart, bar_chart, text_bars, table_grid)


def panel(u, v, box, size, rng, kinds=KINDS):
    """One framed panel at `box`, inside it one content of `kinds` the seed picks, inset from its frame."""
    left, top, right, bottom = box
    inside, x, y = boxed(u, v, (left + 0.03 * (right - left), top + 0.08 * (bottom - top),
                                right - 0.03 * (right - left), bottom - 0.08 * (bottom - top)))
    content = kinds[int(rng.integers(len(kinds)))](x, y, rng)
    return np.maximum(np.where(inside, content, 0.0), FAINT * outline(u, v, box, size))


def title_bar(u, v, size, rng):
    """A title drawn as a bar, a row of status blocks at the right, a faint rule under them."""
    band = (v > 0.04) & (v < 0.1)
    title = band & (u > 0.04) & (u < rng.uniform(0.25, 0.5))
    lit = rng.random(6) > 0.35
    block = np.clip(((u - 0.78) / 0.18 * 6).astype(int), 0, 5)
    blocks = band & (u > 0.78) & (u < 0.96) & (((u - 0.78) / 0.18 * 6) % 1.0 < 0.6) & lit[block]
    rule = (np.abs(v - (TITLE - 0.015)) < 1.5 / size[1]) & (u > 0.02) & (u < 0.98)
    return np.maximum((title | blocks).astype(float), FAINT * rule)


def dashboard(u, v, size, rng):
    """The title bar over COLUMNS by ROWS panels, each its own content."""
    found = title_bar(u, v, size, rng)
    for column in range(COLUMNS):
        for row in range(ROWS):
            box = (0.01 + column / COLUMNS, TITLE + row * (1 - TITLE) / ROWS + 0.01,
                   (column + 1) / COLUMNS - 0.01, TITLE + (row + 1) * (1 - TITLE) / ROWS - 0.01)
            found = np.maximum(found, panel(u, v, box, size, rng))
    return found


def plan_drawing(u, v, box, size, plan, rng):
    """The plan inside `box` ({"outline": [[x, y]], "walls": [{"from", "to"}], "openings": [{"at", "wide",
    "angle"}], "items"}, metres), its long side fitted, north up: its outline faint, its walls at full with each door a
    gap and a tick across it, its items (each [name, x, y, wide, deep, ...], x and y its low corner) faint boxes, a
    few lit; an item over ITEM_MOST of the plan's box is its floor or shell and is left out."""
    points = np.array(plan["outline"], float)
    low, high = points.min(axis=0), points.max(axis=0)
    left, top, right, bottom = (box[0] * size[0], box[1] * size[1], box[2] * size[0], box[3] * size[1])
    scale = 0.9 * min((right - left) / max(high[0] - low[0], 1e-6), (bottom - top) / max(high[1] - low[1], 1e-6))
    middle = (low + high) / 2

    def pixels(point):
        return ((left + right) / 2 + (point[0] - middle[0]) * scale,
                (top + bottom) / 2 - (point[1] - middle[1]) * scale)

    x, y = u * size[0], v * size[1]
    found = np.zeros_like(u)
    for start, end in zip(points, np.roll(points, -1, axis=0)):
        found = np.maximum(found, FAINT * segment(x, y, pixels(start), pixels(end), LINE * 0.75))
    for wall in plan.get("walls") or []:
        found = np.maximum(found, segment(x, y, pixels(wall["from"]), pixels(wall["to"]), LINE * 1.5))
    for opening in plan.get("openings") or []:
        at, half = np.array(opening["at"], float), float(opening.get("wide", 1.0)) / 2
        turn = np.radians(float(opening.get("angle", 0.0)))
        along = np.array([np.cos(turn), np.sin(turn)])
        gap = segment(x, y, pixels(at - along * half), pixels(at + along * half), LINE * 2.5)
        found = np.where(gap, 0.0, found)
        across = np.array([-along[1], along[0]]) * half * 0.6
        found = np.maximum(found, segment(x, y, pixels(at - across), pixels(at + across), LINE))
    for item in plan.get("items") or []:
        corner, wide, deep = np.array(item[1:3], float), float(item[3]), float(item[4])
        if wide * deep > ITEM_MOST * np.prod(high - low):  # the floor or the shell itself, no item on it
            continue
        first, second = pixels(corner), pixels(corner + [wide, deep])
        item_box = (min(first[0], second[0]) / size[0], min(first[1], second[1]) / size[1],
                    max(first[0], second[0]) / size[0], max(first[1], second[1]) / size[1])
        inside, _, _ = boxed(u, v, item_box)
        lit = rng.random() > 0.85
        found = np.maximum(found, np.where(inside, ITEM_LIT if lit else 0.0, 0.0))
        found = np.maximum(found, FAINT * outline(u, v, item_box, size, LINE * 0.5))
    return found


def plan_layout(u, v, size, plan, rng):
    """The title bar over the place's plan, framed, beside a column of status text and a small chart."""
    found = title_bar(u, v, size, rng)
    box = (0.01, TITLE + 0.01, 0.66, 0.99)
    inside, _, _ = boxed(u, v, box)
    found = np.maximum(found, np.where(inside, plan_drawing(u, v, box, size, plan, rng), 0.0))
    found = np.maximum(found, FAINT * outline(u, v, box, size))
    found = np.maximum(found, panel(u, v, (0.68, TITLE + 0.01, 0.99, 0.6), size, rng, (text_bars,)))
    return np.maximum(found, panel(u, v, (0.68, 0.62, 0.99, 0.99), size, rng, (bar_chart, line_chart)))


def levels(seed, size=SIZE, plan=None):
    """The picture's levels (rows top first): the plan layout or the dashboard, the seed choosing between them
    where the place has a plan with an outline."""
    rng = np.random.default_rng(int(seed))
    u, v = grid(size)
    chooses = rng.random()  # drawn first, so a seed's dashboard is the same with a plan or without
    planned = bool(plan and len(plan.get("outline") or []) >= 3)
    if planned and chooses < 0.5:
        return plan_layout(u, v, size, plan, rng)
    return dashboard(u, v, size, rng)


def channels(glass, ink, found):
    """(base colour, emission) of the screen recipe over these levels: the glass's colour where nothing is lit, the
    ink's where it is, mixed by the level; only the content gives off light (linear RGB)."""
    glass, ink = np.asarray(glass, float), np.asarray(ink, float)
    lit = found[..., None]
    return glass + lit * (ink - glass), lit * ink


def srgb_bytes(linear):
    """Linear RGB in 0 to 1 as 8-bit sRGB (IEC 61966-2-1)."""
    linear = np.clip(linear, 0.0, 1.0)
    encoded = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * np.power(linear, 1 / 2.4) - 0.055)
    return np.round(encoded * 255).astype(np.uint8)


def write(glass, ink, seed, folder, name, size=SIZE, plan=None):
    """The picture's base colour and emission as sRGB PNGs `<name>_base.png` and `<name>_glow.png` in `folder`:
    {"base", "glow": their paths, "lit": the share of pixels lit}."""
    from PIL import Image
    found = levels(seed, size, plan)
    base, glow = channels(glass, ink, found)
    folder = pathlib.Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    paths = {"base": folder / f"{name}_base.png", "glow": folder / f"{name}_glow.png"}
    Image.fromarray(srgb_bytes(base)).save(paths["base"])
    Image.fromarray(srgb_bytes(glow)).save(paths["glow"])
    return {**paths, "lit": round(float((found > 0).mean()), 4)}


def main():
    arguments = sys.argv[1:]
    if len(arguments) not in (4, 5):
        raise SystemExit(__doc__)
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "library"))
    import library
    plan = json.loads(pathlib.Path(arguments[4]).read_text()) if len(arguments) == 5 else None
    out = pathlib.Path(arguments[3])
    made = write(library.linear(arguments[0]), library.linear(arguments[1]), int(arguments[2]), out.parent, out.stem,
                 SIZE, plan)
    print(f"screen picture: seed {arguments[2]}, {made['lit']:.0%} lit; PNG: {made['base']}")


if __name__ == "__main__":
    main()
