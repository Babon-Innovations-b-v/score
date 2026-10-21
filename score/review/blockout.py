"""The blockout (CONTEXT.md "blockout"; the owner, 2026-10-21, after ArtCraft's "stage the scene in 3D, then
generate"): a rough 3D model of a place built in code from its parent's plan, at real sizes in metres, untextured
neutral grey, rendered free from the fixed concept viewpoint and sent first with every new concept draw as its
structure picture ("keep this layout, shapes and proportions exactly; add the look"). Never shipped, never priced.

What it is built from, by the node drawn (`scene_of`):

- a top place: its site on the environment's plan (score/review/environment_plan.py): its footprint and blocks at
  their heights and roofs, the ground round it at the plan's spot heights, and every other world in its sky at its
  true direction, size and phase at the site's scene time (score/review/sky.py);
- a place within another (`inside_parts`; the owner, 2026-10-21: consistency between rooms comes from the
  blockouts alone): its own shell at full detail in its box on the holder's plan shown (`holds`), its own plan's
  walls, openings, levels, stairs and roofs (the written plan's schema, score/review/plan_writing.py), else its data
  plan's outline, doors and the heights its words give; its siblings' shells round it in a darker grey and the
  holder's own shell round them all, framed on it with a margin so the hull, the walkway and the rooms beside it
  frame it.

Geometry is plan metres (x east, y south, heights up) turned to x east, y up, z south. The render is a z-buffered
software rasteriser over numpy, flat-shaded grey with its creases drawn dark: no card, no Blender, no browser. Outside
places are seen from the high three-quarter corner view, 40 degrees down, a long lens; inside ones as a cutaway from
the same view (roofs and the walls facing the camera left out). A world in the sky that the fixed view does not show
gets a second picture from behind and above the site looking out over it at that world (`sky_picture`).

    python -m score.review.blockout <node> [--out FILE] [--sky FILE]   one render, from the framework's store
"""
import math
import re
import sys

import numpy as np

WIDE, TALL = 1280, 720  # the concept's 16:9
DOWN = 40.0  # degrees the fixed view looks down (CONTEXT.md "concept": 35 to 45)
LENS = 24.0  # the fixed view's vertical field in degrees: a long lens
SKY_LENS = 70.0  # the sky picture's vertical field: wide, so the place shows under the world
SKY_DOWN = 20.0  # degrees the sky picture's eye looks down on the place's middle, at least
SKY_EDGE = 4.0  # degrees a world stays inside the sky picture's top edge
THICK = 0.3  # metres of a wall a plan gives no thickness
DOOR_HEAD = 2.1  # metres: a door's head where the plan gives none
STOREY = 3.0  # metres: a wall's height where neither the plan nor its words give one
SLAB = 0.2  # metres of a floor slab or level
GROUND_REACH = 0.6  # of the place's size, the ground drawn beyond it each way
GROUND_STEPS = 40  # the ground's grid, each way
ALBEDO = {"sibling": 0.42, "holder": 0.5}  # the grey of a sibling's and the holder's shell; every other part 0.68
GREY = 0.68
FLOOR_DROP = 0.03  # metres the holder's floor sits under its inside places' floors
SIBLING_WALL = 1.2  # metres a sibling's walls stand in an inside place's blockout
MARGIN = 0.35  # of an inside place's box, the frame round it each way, so its siblings frame it
BACKGROUND = (214, 214, 214)
SKY = (196, 200, 206)
CREASE = 0.35  # how dark a crease line is
LIT, UNLIT = (246, 246, 240), (168, 172, 180)  # a world's sunlit face and its dark side against the sky
NEAR = 0.1  # metres: the near plane
LIGHT = np.array([-0.45, 0.8, 0.35])  # the key light: from up, west and a little south


class Missing(ValueError):
    """No plan to build the blockout from yet."""


# --- shapes ------------------------------------------------------------------------------------------------------

def to_world(points, height):
    """[[x, y], ...] plan metres at a height as [[x, up, z]] in metres."""
    return np.array([[x, height, y] for x, y in points], dtype=float)


def quad(corners):
    """Two triangles of four corners in order."""
    return [corners[0], corners[1], corners[2]], [corners[0], corners[2], corners[3]]


def cap(points, height, facing_up):
    """A flat polygon at a height, fanned from its first corner (shortcut: a fan, right for convex outlines; an
    ear-clip when a written plan brings a concave one)."""
    ring = to_world(points, height)
    found = [[ring[0], ring[step], ring[step + 1]] for step in range(1, len(ring) - 1)]
    return found if facing_up else [[one, three, two] for one, two, three in found]


def prism(points, low, high):
    """A closed solid of an outline from `low` to `high`."""
    below, above = to_world(points, low), to_world(points, high)
    sides = []
    for step in range(len(points)):
        after = (step + 1) % len(points)
        sides += quad([below[step], below[after], above[after], above[step]])
    return cap(points, high, True) + cap(points, low, False) + sides


def rectangle(x, y, wide, deep):
    return [[x, y], [x + wide, y], [x + wide, y + deep], [x, y + deep]]


def wall(start, end, thick, low, high, openings=()):
    """A straight wall slab from `start` to `end` (plan metres), `thick` to its right, from `low` to `high`, with
    each opening (along, wide, sill, head) left out of it."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    length = float(np.linalg.norm(end - start))
    if length < 1e-6:
        return []
    along = (end - start) / length
    side = np.array([-along[1], along[0]]) * thick
    pieces, cuts = [], sorted((max(0.0, centre - wide / 2), min(length, centre + wide / 2), sill, head)
                              for centre, wide, sill, head in openings)
    edge = 0.0
    for left, right, sill, head in cuts:
        if left > edge:
            pieces.append((edge, left, low, high))
        if sill > low:
            pieces.append((left, right, low, low + sill))
        if head < high - low:
            pieces.append((left, right, low + head, high))
        edge = max(edge, right)
    if edge < length:
        pieces.append((edge, length, low, high))
    found = []
    for begin, finish, bottom, top in pieces:
        one, two = start + along * begin, start + along * finish
        found += prism([list(one), list(two), list(two + side), list(one + side)], bottom, top)
    return found


def dome(points, eave, rise, steps=16):
    """A dome over an outline's box from `eave`, rising `rise` at its middle (an ellipsoid's top half)."""
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    middle, half = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2), ((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2)

    def at(up, round_):
        flat = math.cos(up)
        return [middle[0] + half[0] * flat * math.cos(round_), eave + rise * math.sin(up),
                middle[1] + half[1] * flat * math.sin(round_)]
    found = []
    for ring in range(steps // 2):
        for turn in range(steps):
            low, high = math.pi / 2 * ring / (steps // 2), math.pi / 2 * (ring + 1) / (steps // 2)
            left, right = 2 * math.pi * turn / steps, 2 * math.pi * (turn + 1) / steps
            found += quad([at(low, left), at(high, left), at(high, right), at(low, right)])
    return found


def pitched(points, eave, top):
    """A gable roof over an outline's box, its ridge along the longer side."""
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    west, east, north, south = min(xs), max(xs), min(ys), max(ys)
    if east - west >= south - north:
        middle = (north + south) / 2
        ridge = [[west, top, middle], [east, top, middle]]
        corners = [[west, eave, north], [east, eave, north], [east, eave, south], [west, eave, south]]
        return [*quad([corners[0], corners[1], ridge[1], ridge[0]]), *quad([corners[2], corners[3], ridge[0], ridge[1]]),
                [corners[3], corners[0], ridge[0]], [corners[1], corners[2], ridge[1]]]
    middle = (west + east) / 2
    ridge = [[middle, top, north], [middle, top, south]]
    corners = [[west, eave, north], [east, eave, north], [east, eave, south], [west, eave, south]]
    return [*quad([corners[1], corners[2], ridge[1], ridge[0]]), *quad([corners[3], corners[0], ridge[0], ridge[1]]),
            [corners[0], corners[1], ridge[0]], [corners[2], corners[3], ridge[1]]]


def roof(kind, points, eave, top):
    """A roof of a written plan's kind over its outline."""
    if kind in ("dome", "vault") and top > eave:
        return dome(points, eave, top - eave)
    if kind in ("pitched", "shed") and top > eave:
        return pitched(points, eave, top)
    return prism(points, eave, eave + SLAB)


def ground(spots, box, base=0.0):
    """The ground over `box` [west, north, east, south] through the spots [[x, y, height]] (a thin-plate spline, so it
    runs smooth between them; none: level at `base`), as a grid."""
    west, north, east, south = box
    xs, ys = np.linspace(west, east, GROUND_STEPS + 1), np.linspace(north, south, GROUND_STEPS + 1)
    grid_x, grid_y = np.meshgrid(xs, ys)
    heights = np.full(grid_x.shape, float(base))
    if spots:
        from scipy.interpolate import RBFInterpolator
        spots = np.unique(np.asarray(spots, float), axis=0)
        spots = spots[np.unique(spots[:, :2], axis=0, return_index=True)[1]]  # one height a spot
        heights = RBFInterpolator(spots[:, :2], spots[:, 2], kernel="thin_plate_spline", smoothing=1e-3)(
            np.column_stack([grid_x.ravel(), grid_y.ravel()])).reshape(grid_x.shape)
    found = []
    for row in range(GROUND_STEPS):
        for column in range(GROUND_STEPS):
            corner = [[grid_x[row + a, column + b], heights[row + a, column + b], grid_y[row + a, column + b]]
                      for a, b in ((0, 0), (0, 1), (1, 1), (1, 0))]
            found += [[corner[0], corner[3], corner[2]], [corner[0], corner[2], corner[1]]]
    return found


# --- a plan made into parts --------------------------------------------------------------------------------------

def measure(words, pattern):
    """The largest metres a plan's height words give after `pattern` ("walls 2.8 m", "dome rising 1.8 m"), else
    None."""
    found = [float(value) for value in re.findall(pattern + r"[^0-9;,]*?(\d+(?:\.\d+)?) ?m\b", words or "")]
    return max(found, default=None)


def heights_of(plan):
    """(walls, rise, roof kind) a plan's words give: its walls or ceiling, its dome's or roof's rise."""
    words = str(plan.get("height") or "")
    walls = measure(words, r"\b(?:walls|ceiling|floor to floor)") or STOREY
    rise = measure(words, r"\b(?:dome|roof) rising")
    return walls, rise or 0.0, "dome" if rise and "dome" in words else ("pitched" if rise else "flat")


def outdoor(plan):
    return plan.get("shell") == "outdoor" or str(plan.get("height", "")).startswith("outdoor")


DOOR_SIZE = re.compile(r"\d+(?:\.\d+)? ?x ?(\d+(?:\.\d+)?) ?m")  # a door's words "(2.2 x 2.6 m)": its height


def data_openings(plan, wide, deep):
    """A data plan's doors as written openings [{at, wide, head}]: [side, along, wide, words] (N and S along x, E
    and W along y) or [bearing, wide, words] (degrees from north, where the ray from the middle meets the box)."""
    found = []
    for door in plan.get("doors", []):
        words = str(door[-1])
        head = float(DOOR_SIZE.search(words).group(1)) if DOOR_SIZE.search(words) else DOOR_HEAD
        if isinstance(door[0], str) and door[0] in "NESW" and len(door) >= 3:
            along = float(door[1])
            at = {"N": [along, 0.0], "S": [along, deep], "W": [0.0, along], "E": [wide, along]}[door[0]]
            found.append({"at": at, "wide": float(door[2]), "head": head})
        elif isinstance(door[0], (int, float)):
            turn = math.radians(float(door[0]))
            way = np.array([math.sin(turn), -math.cos(turn)])
            reach = min(wide / 2 / abs(way[0]) if abs(way[0]) > 1e-9 else math.inf,
                        deep / 2 / abs(way[1]) if abs(way[1]) > 1e-9 else math.inf)
            found.append({"at": list(np.array([wide / 2, deep / 2]) + way * reach), "wide": float(door[1]),
                          "head": head})
    return found


def written_openings(plan, start, end, thick):
    """(along, wide, sill, head) of a written plan's openings standing on the wall from `start` to `end`."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    length = float(np.linalg.norm(end - start))
    along = (end - start) / max(length, 1e-6)
    found = []
    for opening in plan.get("openings", []):
        offset = np.asarray(opening["at"], float) - start
        across = abs(offset[0] * along[1] - offset[1] * along[0])
        distance = float(np.dot(offset, along))
        if across <= thick + 0.3 and -0.1 <= distance <= length + 0.1:
            found.append((distance, float(opening["wide"]), float(opening.get("sill") or 0.0),
                          float(opening.get("head") or DOOR_HEAD)))
    return found


def shell_parts(plan, box=None, cutaway=False, camera=None):
    """The parts of one place's shell from its plan, laid in `box` [x, y, wide, deep] of the holder's plan (None: at
    its own origin and size): [(triangles, kind)] with kind floor, wall, roof, level, stair or ground. A cutaway
    leaves the roofs and the walls facing `camera` (a way, plan x and y) out."""
    wide, deep = float(plan.get("w") or (box or [0, 0, 0, 0])[2]), float(plan.get("d") or (box or [0, 0, 0, 0])[3])
    x0, y0 = (box[0], box[1]) if box else (0.0, 0.0)
    scale_x, scale_y = (box[2] / wide, box[3] / deep) if box and wide and deep else (1.0, 1.0)

    def placed(points):
        return [[x0 + x * scale_x, y0 + y * scale_y] for x, y in points]
    walls_high, rise, kind = heights_of(plan)
    outline = placed(plan.get("outline") or rectangle(0, 0, wide, deep))
    parts = [(prism(outline, -SLAB, 0.0), "floor")]
    if outdoor(plan):
        return parts
    middle = np.mean(np.asarray(outline), axis=0)
    written = [entry for entry in plan.get("walls", []) if "from" in entry]
    corners = rectangle(0, 0, wide, deep)
    own = written or [{"from": one, "to": two} for one, two in zip(corners, corners[1:] + corners[:1])]
    holes = plan if written else {"openings": data_openings(plan, wide, deep)}
    runs = []
    for entry in own:
        thick = float(entry.get("thick") or THICK)
        start, end = placed([entry["from"], entry["to"]])
        stretch = float(np.linalg.norm(np.subtract(end, start))) / max(
            float(np.linalg.norm(np.subtract(entry["to"], entry["from"]))), 1e-6)
        runs.append((start, end, thick, float(entry.get("tall") or walls_high),
                     [(along * stretch, hole * stretch, sill, head)
                      for along, hole, sill, head in written_openings(holes, entry["from"], entry["to"], thick)]))
    for start, end, thick, tall, openings in runs:
        if cutaway and faces(start, end, middle, camera):
            continue
        inward = inward_thick(start, end, middle, thick)
        parts.append((wall(start, end, inward, 0.0, tall, openings), "wall"))
    parts += [(prism(placed(level["points"]), level["height"] - SLAB, level["height"]), "level")
              for level in plan.get("levels", []) if abs(level["height"]) > 0.05]
    parts += [(stair(placed(entry["points"]), entry["from"], entry["to"]), "stair") for entry in plan.get("stairs", [])]
    if not cutaway:
        written_roofs = plan.get("roofs") or []
        parts += [(roof(entry["kind"], placed(entry["points"]), entry["eave"], entry["top"]), "roof")
                  for entry in written_roofs]
        if not written_roofs:
            parts.append((roof(kind, outline, walls_high, walls_high + rise), "roof"))
    return parts


def stair(points, low, high):
    """A stair or ramp as a solid rising from `low` to `high` across its footprint's box (its first edge low)."""
    return prism(points, low, (low + high) / 2) if high - low < 0.05 else prism(points, min(low, high), max(low, high))


def faces(start, end, middle, camera):
    """Whether a wall from `start` to `end` of a room round `middle` faces the camera's way (plan x, y): a near wall."""
    if camera is None:
        return False
    run = np.asarray(end, float) - np.asarray(start, float)
    normal = np.array([run[1], -run[0]])
    if np.dot(normal, (np.asarray(start) + np.asarray(end)) / 2 - middle) < 0:
        normal = -normal
    return float(np.dot(normal, camera)) > 1e-6


def inward_thick(start, end, middle, thick):
    """The wall's thickness signed so it stands inside the room (the wall function lays it to its run's left)."""
    run = np.asarray(end, float) - np.asarray(start, float)
    left = np.array([-run[1], run[0]])
    return thick if np.dot(left, middle - np.asarray(start, float)) > 0 else -thick


# --- the camera and the render -------------------------------------------------------------------------------------

def bounds(parts):
    """(low, high) corners round the place itself: every part but the ground round it, the ground when that is all."""
    own = [triangles for triangles, kind in parts if triangles and kind != "ground"]
    points = np.concatenate([np.asarray(triangles, float).reshape(-1, 3)
                             for triangles in own or [triangles for triangles, _ in parts if triangles]])
    return points.min(axis=0), points.max(axis=0)


def corner_way(bearing=135.0):
    """The fixed view's way in plan metres (x east, y south): looking from the south-east corner to the north-west
    (`bearing`, degrees from north, is where the camera stands)."""
    turn = math.radians(bearing)
    return np.array([math.sin(turn), -math.cos(turn)])


def fixed_camera(parts, framed=None, bearing=135.0):
    """(eye, forward, up, field) of the fixed concept view framing the place (`bounds`), or the box `framed` [x, y,
    wide, deep, tall], with MARGIN round it."""
    low, high = bounds(parts)
    x, y, wide, deep, tall = framed or [low[0], low[2], high[0] - low[0], high[2] - low[2], high[1]]
    low = np.array([x - wide * MARGIN, 0.0, y - deep * MARGIN])
    high = np.array([x + wide * (1 + MARGIN), tall, y + deep * (1 + MARGIN)])
    middle, reach = (low + high) / 2, float(np.linalg.norm(high - low)) / 2
    way = corner_way(bearing)
    down = math.radians(DOWN)
    back = np.array([way[0] * math.cos(down), math.sin(down), way[1] * math.cos(down)])
    distance = reach / math.sin(math.radians(LENS) / 2) * 0.9
    return middle + back * distance, -back, np.array([0.0, 1.0, 0.0]), LENS


def basis(forward, up):
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    return right, np.cross(right, forward), forward


def project(points, eye, forward, up, field):
    """Pixel x, y and depth of world points."""
    right, true_up, ahead = basis(forward, up)
    offset = points - eye
    depth = offset @ ahead
    focal = TALL / 2 / math.tan(math.radians(field) / 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (WIDE / 2 + focal * (offset @ right) / depth, TALL / 2 - focal * (offset @ true_up) / depth, depth)


def rasterised(parts, camera):
    """(shade, normals, depth) buffers of the parts seen from `camera`."""
    eye, forward, up, field = camera
    depth = np.full((TALL, WIDE), np.inf)
    shade = np.zeros((TALL, WIDE))
    normals = np.zeros((TALL, WIDE, 3))
    light = LIGHT / np.linalg.norm(LIGHT)
    for triangles, kind in parts:
        if not triangles:
            continue
        corners = np.asarray(triangles, float)
        flat = corners.reshape(-1, 3)
        xs, ys, zs = (value.reshape(-1, 3) for value in project(flat, eye, forward, up, field))
        normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
        normal /= np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12
        toward = eye - corners.mean(axis=1)
        normal *= np.where((normal * toward).sum(1) < 0, -1.0, 1.0)[:, None]  # two-sided: face the eye
        for number in range(len(corners)):
            for piece in near_clipped(corners[number], (xs[number], ys[number], zs[number]), camera):
                fill(*piece, normal[number], light, ALBEDO.get(kind, GREY), (depth, shade, normals),
                     kind == "ground")
    return shade, normals, depth


def near_clipped(corners, projected, camera):
    """The triangle's projected pieces in front of the near plane: itself when wholly in front, else the part in front
    cut along the plane and fanned, so a floor reaching under the camera still shows (none when wholly behind)."""
    xs, ys, zs = projected
    if np.all(zs > NEAR):
        return [projected]
    eye, forward, up, field = camera
    ahead = basis(forward, up)[2]
    kept = []
    for step in range(3):
        here, there = corners[step], corners[(step + 1) % 3]
        here_depth, there_depth = float(np.dot(here - eye, ahead)), float(np.dot(there - eye, ahead))
        if here_depth > NEAR:
            kept.append(here)
        if (here_depth > NEAR) != (there_depth > NEAR):
            kept.append(here + (there - here) * (NEAR - here_depth) / (there_depth - here_depth))
    if len(kept) < 3:
        return []
    found_x, found_y, found_z = project(np.asarray(kept), eye, forward, up, field)
    return [(found_x[[0, step, step + 1]], found_y[[0, step, step + 1]], found_z[[0, step, step + 1]])
            for step in range(1, len(kept) - 1)]


def fill(xs, ys, zs, normal, light, albedo, buffers, smooth=False):
    """One triangle into the buffers (depth, shade, normals): depth-tested, flat-shaded; a smooth one leaves no crease."""
    depth, shade, normals = buffers
    if np.any(zs <= NEAR * 0.99) or not np.all(np.isfinite(xs)):
        return
    left, right = max(int(math.floor(xs.min())), 0), min(int(math.ceil(xs.max())), WIDE - 1)
    top, bottom = max(int(math.floor(ys.min())), 0), min(int(math.ceil(ys.max())), TALL - 1)
    if left > right or top > bottom:
        return
    area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
    if abs(area) < 1e-9:
        return
    grid_x, grid_y = np.meshgrid(np.arange(left, right + 1) + 0.5, np.arange(top, bottom + 1) + 0.5)
    one = ((xs[1] - grid_x) * (ys[2] - grid_y) - (xs[2] - grid_x) * (ys[1] - grid_y)) / area
    two = ((xs[2] - grid_x) * (ys[0] - grid_y) - (xs[0] - grid_x) * (ys[2] - grid_y)) / area
    three = 1.0 - one - two
    inside = (one >= 0) & (two >= 0) & (three >= 0)
    if not inside.any():
        return
    seen = 1.0 / (one / zs[0] + two / zs[1] + three / zs[2])
    window = depth[top:bottom + 1, left:right + 1]
    nearer = inside & (seen < window)
    window[nearer] = seen[nearer]
    shade[top:bottom + 1, left:right + 1][nearer] = albedo * (0.35 + 0.65 * max(0.0, float(np.dot(normal, light))))
    normals[top:bottom + 1, left:right + 1][nearer] = 0.0 if smooth else normal  # the ground's facets draw no creases


def creases(normals, depth):
    """Where neighbouring pixels turn sharply or jump in depth: the model's edges."""
    found = np.zeros(depth.shape, bool)
    finite = np.where(np.isfinite(depth), depth, 1e9)
    for axis in (0, 1):
        turn = np.linalg.norm(np.diff(normals, axis=axis), axis=-1) > 0.25
        jump = np.abs(np.diff(finite, axis=axis)) > 0.03 * np.minimum(finite[:-1] if axis == 0 else finite[:, :-1],
                                                                      finite[1:] if axis == 0 else finite[:, 1:])
        edge = turn | jump
        if axis == 0:
            found[:-1] |= edge
        else:
            found[:, :-1] |= edge
    return found


def worlds_drawn(image, worlds, camera):
    """Each world of the sky (sky.sky_at's) drawn as its disc at its true direction and size, its face lit from the
    Sun's side; a world too small to show a disc is a bright point."""
    eye, forward, up, field = camera
    right, true_up, ahead = basis(forward, up)
    focal = TALL / 2 / math.tan(math.radians(field) / 2)
    for world in worlds:
        if world["altitude"] <= 0:
            continue
        way = sky_way(world["azimuth"], world["altitude"])
        if float(np.dot(way, ahead)) <= 0:
            continue
        x = WIDE / 2 + focal * float(np.dot(way, right)) / float(np.dot(way, ahead))
        y = TALL / 2 - focal * float(np.dot(way, true_up)) / float(np.dot(way, ahead))
        radius = focal * math.tan(math.radians(world["across"]) / 2)
        sun = np.asarray(world["lit_from"], float)  # east, north, up
        sun_world = np.array([sun[0], sun[2], -sun[1]])
        sun_view = np.array([np.dot(sun_world, right), np.dot(sun_world, true_up), -np.dot(sun_world, ahead)])
        disc(image, x, y, max(radius, 1.5), sun_view, radius < 1.5)


def sky_way(azimuth, altitude):
    """A sky direction as a world way (x east, y up, z south)."""
    turn, rise = math.radians(azimuth), math.radians(altitude)
    return np.array([math.sin(turn) * math.cos(rise), math.sin(rise), -math.cos(turn) * math.cos(rise)])


def disc(image, x, y, radius, sun_view, point):
    """A lit sphere of `radius` pixels at x, y, its light from `sun_view` (right, up, toward the eye)."""
    reach = int(math.ceil(radius)) + 1
    for row in range(max(0, int(y) - reach), min(TALL, int(y) + reach + 1)):
        for column in range(max(0, int(x) - reach), min(WIDE, int(x) + reach + 1)):
            across, down = (column + 0.5 - x) / radius, (row + 0.5 - y) / radius
            if across * across + down * down > 1.0 or not np.isinf(image["depth"][row, column]):
                continue
            facing = math.sqrt(max(0.0, 1.0 - across * across - down * down))
            lit = point or across * sun_view[0] - down * sun_view[1] + facing * sun_view[2] > 0
            image["colour"][row, column] = LIT if lit else UNLIT


def render(parts, camera, worlds=()):
    """The PIL picture of the parts from `camera`, the worlds in its sky drawn where they fall in frame."""
    from PIL import Image
    shade, normals, depth = rasterised(parts, camera)
    colour = np.empty((TALL, WIDE, 3))
    colour[:] = SKY if worlds else BACKGROUND
    hit = np.isfinite(depth)
    colour[hit] = (shade[hit] * 255.0)[:, None] * np.ones(3)
    colour[creases(normals, depth) & hit] *= CREASE
    image = {"colour": colour, "depth": depth}
    worlds_drawn(image, worlds, camera)
    return Image.fromarray(np.clip(colour, 0, 255).astype(np.uint8))


def sky_camera(parts, world):
    """(eye, forward, up, field) behind the place from `world` and above it, looking out over it at `world`: the place
    low in the frame, the world high, both in when it stands under about 45 degrees."""
    low, high = bounds(parts)
    middle = (low + high) / 2
    way = sky_way(world["azimuth"], world["altitude"])
    level = np.array([way[0], 0.0, way[2]])
    level = level / (np.linalg.norm(level) or 1.0)
    back = float(np.linalg.norm((high - low)[[0, 2]])) * 0.75
    eye = np.array([middle[0], high[1] + back * math.tan(math.radians(SKY_DOWN)), middle[2]]) - level * back
    down = math.degrees(math.atan2(eye[1] - middle[1], back))
    reach = SKY_LENS / 2 - SKY_EDGE
    pitch = math.radians(min(max((world["altitude"] - down) / 2, world["altitude"] - reach), 80.0))
    forward = level * math.cos(pitch) + np.array([0.0, math.sin(pitch), 0.0])
    return eye, forward, np.array([0.0, 1.0, 0.0]), SKY_LENS


# --- what a node's blockout is built from ------------------------------------------------------------------------

def site_parts(site):
    """The parts of a top place's site on the environment's plan: the ground round it at its spot heights, its
    blocks (or its footprint) at their heights and roofs, in site metres."""
    footprint = site.get("footprint") or rectangle(-site["size"][0] / 2, -site["size"][1] / 2, *site["size"][:2])
    xs, ys = [point[0] for point in footprint], [point[1] for point in footprint]
    reach = max(max(xs) - min(xs), max(ys) - min(ys)) * GROUND_REACH
    box = [min(xs) - reach, min(ys) - reach, max(xs) + reach, max(ys) + reach]
    spots = (site.get("terrain") or {}).get("spots") or []
    parts = [(ground(spots, box), "ground")]
    for block in site.get("blocks") or [{"points": footprint, "tall": site["size"][2], "roof": "flat"}]:
        base = float(block.get("base") or 0.0)
        tall = float(block.get("tall") or 0.0)
        if tall > 0:
            parts.append((prism(block["points"], base, base + tall), "wall"))
        if block.get("roof") in ("dome", "vault", "pitched") and block.get("rise"):
            parts.append((roof(block["roof"], block["points"], base + tall, base + tall + float(block["rise"])),
                          "roof"))
    return parts


def sized(own, hold, holder_plan):
    """An inside place's own plan with the size of its box on the holder's plan where it gives none, walled where it
    is outdoor (an inside place has walls in the holder's blockout)."""
    found = {**own, "w": own.get("w") or hold["w"], "d": own.get("d") or hold["d"],
             "height": own.get("height") or holder_plan.get("height")}
    return {**found, "shell": None, "height": f"walls {STOREY} m"} if outdoor(found) else found


def dropped(triangles, by):
    """Triangles moved down `by` metres: a floor under another's, so the two never fight for a pixel."""
    return [[[x, y - by, z] for x, y, z in triangle] for triangle in triangles]


def lowered(triangles):
    """A sibling's walls cut down to SIBLING_WALL, so they lay out the rooms round a place without hiding it."""
    return [[[x, min(y, SIBLING_WALL), z] for x, y, z in triangle] for triangle in triangles]


def inside_parts(place, holder_plan, mine_plan, plan_of, camera_way):
    """An inside place's parts (the owner, 2026-10-21: consistency between rooms comes from the blockouts alone): its
    own shell at full detail (walls, openings, levels, stairs; `mine_plan` its own plan) where the holder's plan lays
    it, its siblings' floors and low walls round it in a darker grey (kind sibling; `plan_of(place)` their data plans, {}
    with none), inside the holder's own shell (kind holder), all cut away. Missing when the holder's plan does not lay
    `place` out."""
    holds = holder_plan.get("holds") or []
    mine = next((hold for hold in holds if hold["place"] == place), None)
    if mine is None:
        raise Missing(f"the plan holding {place} does not lay it out yet")
    parts = [(dropped(triangles, FLOOR_DROP) if kind == "floor" else triangles, "holder")
             for triangles, kind in shell_parts(holder_plan, None, True, camera_way)]
    for hold in holds:
        box = [hold["x"], hold["y"], hold["w"], hold["d"]]
        own = sized((mine_plan if hold["place"] == place else plan_of(hold["place"])) or {}, hold, holder_plan)
        if hold["place"] == place:
            parts += shell_parts(own, box, True, camera_way)
        else:
            parts += [(dropped(triangles, FLOOR_DROP / 2) if kind == "floor" else lowered(triangles), "sibling")
                      for triangles, kind in shell_parts(own, box, True, camera_way) if kind in ("wall", "floor")]
    tall = heights_of(sized(mine_plan or {}, mine, holder_plan))[0]
    return parts, [mine["x"], mine["y"], mine["w"], mine["d"], tall]


def scene_of(store, node):
    """(parts, framed, worlds) of `node`'s blockout from its parent's plan (module docstring): `framed` the box [x, y,
    wide, deep, tall] the view frames (None: every part); Missing while that plan is not there."""
    from score.review import concepts, plans
    above = concepts.above(node, store)
    if above:
        shown = plans.current(store, above)
        holder_plan = (shown or {}).get("plan") or {}
        parts, box = inside_parts(node, holder_plan, own_plan(store, node), concepts.plan_of, corner_way())
        return parts, box, []
    from score.review import environment_plan
    site = environment_plan.site_of(store, node)
    if site is None:
        raise Missing(f"the environment's plan has no site for {node} yet")
    return site_parts(site), None, (site.get("sky") or {}).get("worlds", [])


def own_plan(store, place):
    """A place's own plan: the one shown (written or his edit), else its data plan, {} with neither."""
    from score.review import concepts, plans
    shown = plans.current(store, place) if plans.counts(store, place) else None
    return (shown or {}).get("plan") or concepts.plan_of(place)


def picture(store, node):
    """The PIL blockout of `node` from the fixed concept view; Missing while its parent's plan is not there."""
    parts, framed, worlds = scene_of(store, node)
    return render(parts, fixed_camera(parts, framed), worlds)


def unseen(parts, worlds):
    """The worlds above the horizon that the fixed view does not show."""
    camera = fixed_camera(parts)
    right, true_up, ahead = basis(camera[1], camera[2])
    limit = math.tan(math.radians(camera[3]) / 2)
    found = []
    for world in worlds:
        way = sky_way(world["azimuth"], world["altitude"])
        depth = float(np.dot(way, ahead))
        shown = depth > 0 and abs(float(np.dot(way, true_up))) / depth <= limit and \
            abs(float(np.dot(way, right))) / depth <= limit * WIDE / TALL
        if world["altitude"] > 0 and not shown:
            found.append(world)
    return found


def sky_picture(store, node):
    """The PIL picture from behind and above the site looking out at the largest world in its sky that the fixed view
    does not show, None when there is none (an inside place, or every world below the horizon or in frame)."""
    parts, _, worlds = scene_of(store, node)
    hidden = unseen(parts, worlds)
    if not hidden:
        return None
    biggest = max(hidden, key=lambda world: world["across"])
    return render(parts, sky_camera(parts, biggest), worlds)


def main(argv):
    """`<node> [--out FILE] [--sky FILE]`: its blockout (and sky picture) from the framework's store."""
    import argparse
    from score.store import Store
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("node")
    parser.add_argument("--out", default="blockout.png")
    parser.add_argument("--sky")
    options = parser.parse_args(argv)
    store = Store.default()
    try:
        picture(store, options.node).save(options.out)
        found = sky_picture(store, options.node) if options.sky else None
    except Missing as missing:
        print(f"missing: {missing}", file=sys.stderr)
        return 1
    if found is not None:
        found.save(options.sky)
    print(f"{options.node}: {options.out}" + (f", sky {options.sky}" if found is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
