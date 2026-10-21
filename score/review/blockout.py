"""The blockout (CONTEXT.md "blockout"; the owner, 2026-10-21, after ArtCraft's "stage the scene in 3D, then
generate"): a rough 3D model of a place built in code from its parent's plan, at real sizes in metres, untextured
neutral grey, rendered free from the fixed concept viewpoint and sent first with every new concept draw as its
structure picture ("keep this layout, shapes and proportions exactly; add the look"). Never shipped, never priced.
It reads like an architect's massing model (the owner, 2026-10-21: "good enough to guide a picture model"): light grey
solids on a darker ground, lit by the setting's sun with soft shadows, the place filling the frame, a person for scale.

What it is built from, by the node drawn (`scene_of`):

- a top place: its site on the environment's plan (score/review/environment_plan.py), on the ground of its setting
  curving with the body's true radius, with the plan's spot heights (`ground`); on it, each part of the site that is
  a place with a plan of its own (the Base's modules) at full detail where the plan lays it, else the place's own
  plan at full detail where it has one (as an inside place's), else the site's blocks at their heights and roofs; lit
  from the direction of the setting's first light over the site at its scene time (score/review/overhead.py),
  every body in its sky at its true direction, size and phase;
- a place within another (`inside_parts`): its own room shell alone at full detail in its box on the holder's plan
  shown (`holds`), its own plan's walls, openings, levels, stairs, roofs and items (the written plan's schema,
  score/review/plan_writing.py), else its data plan's outline, doors and the heights its words give; no hull and no
  rooms beside it (the owner, 2026-10-21: the room is drawn on its own).

"At full detail" is: walls with their thickness and openings (straight or on an arc), levels as platforms, stairs,
roofs by kind (a dome as a dome, a vault as a half cylinder, pitched, flat), a tube as a tube, and each item as a
solid of its shape (a box, a cylinder, a polygon) at its height. A person 1.8 m tall stands at the place's front where
its plan has people, for scale.

Geometry is plan metres (x east, y south, heights up) turned to x east, y up, z south. The render is a z-buffered
software rasteriser over numpy at twice the size, then halved: no card, no Blender, no browser. Each face is shaded by
a soft ambient and the sun's key light, shadowed through a shadow map from the sun with soft edges, its creases drawn
a little dark. Outside places are seen from the high three-quarter corner view, 40 degrees down, a long lens, framed
so the place fills the frame; inside ones as a cutaway from the same view (roofs and the walls facing the camera left
out). A world in the sky that the fixed view does not show gets a second picture from behind and above the site
looking out over it at that world (`overhead_view`). `scene_key` keys a render by what it is built from and this
module's code, so no render made by older code is served again.

    python -m score.review.blockout <node> [--out FILE] [--overhead FILE]   one render, from the framework's store
"""
import hashlib
import json
import math
import pathlib
import re
import sys

import numpy as np

WIDE, TALL = 1280, 720  # the concept's 16:9
SUPER = 2  # rendered at twice the size each way and halved: smooth edges
DOWN = 40.0  # degrees the fixed view looks down (CONTEXT.md "concept": 35 to 45)
LENS = 24.0  # the fixed view's vertical field in degrees: a long lens
FILL = 0.86  # of the frame's half width and half height the place's outermost point reaches
OVERHEAD_LENS = 70.0  # the overhead view's vertical field: wide, so the place shows under the world
OVERHEAD_DOWN = 20.0  # degrees the overhead view's eye looks down on the place's middle, at least
OVERHEAD_EDGE = 4.0  # degrees a world stays inside the overhead view's top edge
THICK = 0.3  # metres of a wall a plan gives no thickness
DOOR_HEAD = 2.1  # metres: a door's head where the plan gives none
STOREY = 3.0  # metres: a wall's height where neither the plan nor its words give one
SLAB = 0.2  # metres of a floor slab or level
CURVE = 32  # facets round a dome, a cylinder or a tube: fine enough that no crease shows between two
ARC_STEP = 10.0  # degrees of an arc wall a straight piece spans, at most
GROUND_REACH = 20.0  # of the site's span, the ground drawn round its middle each way: to the overhead view's horizon
GROUND_STEPS = 96  # the ground's grid, each way, finest at its middle
GROUND_BLUR = 31  # pixels (at twice the size) the ground's facet normals are averaged over
BEYOND = 0.1  # of a plan's box: an item standing further out than this is beyond the place, not drawn
PERSON = 1.8  # metres: the person standing for scale
GREY = 0.86  # the place's own solids: light grey
ALBEDO = {"ground": 0.42, "person": 0.62}
MARGIN = 0.05  # of an inside place's box, the frame round it each way: its room alone fills the view
BACKGROUND = (92, 92, 92)
SKY_GREY = (196, 200, 206)
CREASE = 0.62  # how dark a crease line is
LIT, UNLIT = (246, 246, 240), (168, 172, 180)  # a world's sunlit face and its dark side against the sky
NEAR = 0.1  # metres: the near plane
AMBIENT, SKY_FILL, KEY = 0.3, 0.2, 0.62  # the light: soft all round, a little more from above, the sun's key
LOWEST_SUN = 20.0  # degrees: a sun lower than this (or set) lights the model from this height on its bearing
NO_SUN = (225.0, 40.0)  # (azimuth, altitude) of the key light with no scene time: south-west, high
SHADOW = 2048  # pixels of the shadow map each way
SHADOW_BIAS = 0.08  # metres a point is lifted toward the sun before its shadow test
SOFT = 1  # pixels of the shadow map each way a shadow's edge is softened over
VERSION = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]  # this code, in every render's key


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


def ellipse(x, y, wide, deep, steps=CURVE):
    """The outline of the ellipse in the box [x, y, wide, deep]."""
    return [[x + wide / 2 * (1 + math.cos(2 * math.pi * step / steps)),
             y + deep / 2 * (1 + math.sin(2 * math.pi * step / steps))] for step in range(steps)]


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


def box_of(points):
    """(middle, half) of an outline's box, plan metres."""
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2), ((max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2)


def dome(points, eave, rise, steps=CURVE):
    """A dome over an outline's box from `eave`, rising `rise` at its middle (an ellipsoid's top half)."""
    middle, half = box_of(points)

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


def vault(points, eave, rise, steps=CURVE):
    """A barrel vault over an outline's box from `eave`, rising `rise`: a half cylinder along its longer side, its
    two ends closed."""
    middle, half = box_of(points)
    lengthwise = half[0] >= half[1]
    span, reach = (half[1], half[0]) if lengthwise else (half[0], half[1])

    def at(turn, end):
        across, up = span * math.cos(turn), eave + rise * math.sin(turn)
        return [middle[0] + end, up, middle[1] + across] if lengthwise else [middle[0] + across, up, middle[1] + end]
    found = []
    for step in range(steps // 2):
        one, two = math.pi * step / (steps // 2), math.pi * (step + 1) / (steps // 2)
        found += quad([at(one, -reach), at(two, -reach), at(two, reach), at(one, reach)])
        for end in (-reach, reach):
            foot = at(math.pi / 2, end)
            found.append([[foot[0], eave, foot[2]], at(one, end), at(two, end)])  # its end, fanned from its foot
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
    """A roof of a written plan's kind over its outline (shortcut: a shed is drawn as a gable)."""
    if kind == "dome" and top > eave:
        return dome(points, eave, top - eave)
    if kind == "vault" and top > eave:
        return vault(points, eave, top - eave)
    if kind in ("pitched", "shed") and top > eave:
        return pitched(points, eave, top)
    return prism(points, eave, eave + SLAB)


def tube(start, end, radius, axis, steps=CURVE):
    """A tube of `radius` round its axis `axis` metres up, from plan point `start` to `end`, its ends open."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    run = end - start
    length = float(np.linalg.norm(run))
    if length < 1e-6:
        return []
    across = np.array([-run[1], run[0]]) / length

    def at(turn, point):
        side = across * radius * math.cos(turn)
        return [point[0] + side[0], axis + radius * math.sin(turn), point[1] + side[1]]
    found = []
    for step in range(steps):
        one, two = 2 * math.pi * step / steps, 2 * math.pi * (step + 1) / steps
        found += quad([at(one, start), at(two, start), at(two, end), at(one, end)])
    return found


def person(x, y, base=0.0):
    """A standing person for scale at plan point (x, y): a body and a head, PERSON tall."""
    return prism(ellipse(x - 0.22, y - 0.16, 0.44, 0.32, 12), base, base + PERSON - 0.27) + \
        prism(ellipse(x - 0.11, y - 0.11, 0.22, 0.22, 12), base + PERSON - 0.25, base + PERSON)


def relief_of(spots, radius):
    """The spots [[x, y, height]] with the fall of a body's curve d² / 2R taken back out of their heights: the
    ground's own rises and falls (all of it on a plot, `radius` None)."""
    spots = np.asarray(spots, float).reshape(-1, 3).copy()
    if radius:
        spots[:, 2] += (spots[:, 0] ** 2 + spots[:, 1] ** 2) / (2 * radius)
    return spots


def ground(spots, box, radius=None):
    """The ground over `box` [west, north, east, south] (site metres, its middle at 0, 0): falling away with a body's
    true curve d² / 2R (`radius` in metres; level on a plot), with the rises and falls of the spots [[x, y, height]]
    through a thin-plate spline, faded out past the furthest spot, as a grid."""
    west, north, east, south = box
    steps = np.linspace(-1.0, 1.0, GROUND_STEPS + 1)
    steps = steps * np.abs(steps)  # fine at the middle, coarse far out
    xs = (west + east) / 2 + steps * (east - west) / 2
    ys = (north + south) / 2 + steps * (south - north) / 2
    grid_x, grid_y = np.meshgrid(xs, ys)
    far = np.hypot(grid_x, grid_y)
    heights = np.zeros(grid_x.shape)
    relief = relief_of(spots, radius) if len(spots) else np.zeros((0, 3))
    if len(relief) >= 3 and np.ptp(relief[:, 2]) > 1e-3:
        from scipy.interpolate import RBFInterpolator
        relief = relief[np.unique(relief[:, :2], axis=0, return_index=True)[1]]  # one height a spot
        heights = RBFInterpolator(relief[:, :2], relief[:, 2], kernel="thin_plate_spline", smoothing=1e-3)(
            np.column_stack([grid_x.ravel(), grid_y.ravel()])).reshape(grid_x.shape)
        reach = float(np.hypot(relief[:, 0], relief[:, 1]).max()) or 1.0
        heights *= np.clip((1.3 * reach - far) / (0.3 * reach), 0.0, 1.0)  # no spline guesses past the spots
    if radius:
        heights -= far ** 2 / (2 * radius)
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


def arc_runs(entry):
    """A written arc wall ({arc {centre, radius, start, end}, thick, tall}; degrees from east, clockwise as y runs
    south) as straight runs [{from, to, thick, tall}] of at most ARC_STEP degrees each."""
    arc = entry["arc"]
    start, end = float(arc["start"]), float(arc["end"])
    if end <= start:
        end += 360.0
    steps = max(1, math.ceil((end - start) / ARC_STEP))
    corners = [[arc["centre"][0] + arc["radius"] * math.cos(math.radians(start + (end - start) * step / steps)),
                arc["centre"][1] + arc["radius"] * math.sin(math.radians(start + (end - start) * step / steps))]
               for step in range(steps + 1)]
    return [{"from": one, "to": two, "thick": entry.get("thick"), "tall": entry.get("tall")}
            for one, two in zip(corners, corners[1:])]


def wall_runs(plan, wide, deep):
    """(runs, holes) of a plan's walls: its written straight and arc walls with its written openings, else the four
    sides of its box with its data doors."""
    written = []
    for entry in plan.get("walls", []):
        if "from" in entry:
            written.append(entry)
        elif isinstance(entry.get("arc"), dict):
            written += arc_runs(entry)
    if written:
        return written, plan
    corners = rectangle(0, 0, wide, deep)
    return [{"from": one, "to": two} for one, two in zip(corners, corners[1:] + corners[:1])], \
        {"openings": data_openings(plan, wide, deep)}


def item_parts(plan, placed, wide, deep):
    """Each item of a plan standing in the place as a solid of its shape (a box, a cylinder, a polygon) from its base
    to its top (its `shapes` entry); one with no height, a zone, the walls' row, or one standing beyond the plan's box
    (a skyline far off) is left out."""
    shapes, found = plan.get("shapes") or {}, []
    for item in plan.get("items") or []:
        name, x, y, item_wide, item_deep = item[0], *[float(value) for value in item[1:5]]
        shape = shapes.get(name) or {}
        tall = float(shape.get("tall") or 0.0)
        if len(item) > 6 and item[6] == "zone" or tall <= 0 or item_wide <= 0 or item_deep <= 0:
            continue
        if x < -BEYOND * wide or y < -BEYOND * deep or x + item_wide > (1 + BEYOND) * wide or \
                y + item_deep > (1 + BEYOND) * deep:
            continue
        if shape.get("shape") == "circle":
            outline = ellipse(x, y, item_wide, item_deep)
        elif shape.get("shape") == "polygon" and len(shape.get("points") or []) >= 3:
            outline = [[x + u * item_wide, y + v * item_deep] for u, v in shape["points"]]
        else:
            outline = rectangle(x, y, item_wide, item_deep)
        base = float(shape.get("base") or 0.0)
        found.append((prism(placed(outline), base, base + tall), "item"))
    return found


def tube_parts(plan, placed):
    """A tube's shell (a plan of shape tube: its radius and axis height): a tube along its box's longer side and the
    deck in it."""
    wide, deep = float(plan["w"]), float(plan["d"])
    radius = float(plan.get("radius") or min(wide, deep) / 2)
    axis = float(plan.get("axis") if plan.get("axis") is not None else radius)
    start, end = ([0.0, deep / 2], [wide, deep / 2]) if wide > deep else ([wide / 2, 0.0], [wide / 2, deep])
    start, end = placed([start, end])
    return [(tube(start, end, radius, axis), "wall")]


def shell_parts(plan, box=None, cutaway=False, camera=None, on_ground=False, standing=False):
    """The parts of one place's shell from its plan, laid in `box` [x, y, wide, deep] of the holder's plan (None: at
    its own origin and size): [(triangles, kind)] with kind floor, wall, roof, level, stair, item or person. A
    cutaway leaves the roofs and the walls facing `camera` (a way, plan x and y) out; a shell `on_ground` (a site's)
    stands on the ground with no slab of its own; `standing` puts a person on its first standing spot."""
    wide, deep = float(plan.get("w") or (box or [0, 0, 0, 0])[2]), float(plan.get("d") or (box or [0, 0, 0, 0])[3])
    x0, y0 = (box[0], box[1]) if box else (0.0, 0.0)
    scale_x, scale_y = (box[2] / wide, box[3] / deep) if box and wide and deep else (1.0, 1.0)

    def placed(points):
        return [[x0 + x * scale_x, y0 + y * scale_y] for x, y in points]
    walls_high, rise, kind = heights_of(plan)
    outline = placed(plan.get("outline") or rectangle(0, 0, wide, deep))
    parts = [] if on_ground else [(prism(outline, -SLAB, 0.0), "floor")]
    parts += [(level_solid(placed(level["points"]), level["height"]), "level")
              for level in plan.get("levels", []) if level["height"] > 0.05 or (level["height"] < -0.05 and cutaway)]
    parts += [(stair(placed(entry["points"]), entry["from"], entry["to"]), "stair") for entry in plan.get("stairs", [])]
    parts += item_parts(plan, placed, wide, deep)
    if standing and plan.get("people"):
        parts.append((person(*placed([plan["people"][0][:2]])[0]), "person"))  # a data plan's: [x, y, facing, words]
    if plan.get("shape") == "tube" and wide and deep:
        return parts + tube_parts(plan, placed)
    if outdoor(plan):
        return parts
    middle = np.mean(np.asarray(outline), axis=0)
    own, holes = wall_runs(plan, wide, deep)
    for entry in own:
        thick = float(entry.get("thick") or THICK)
        start, end = placed([entry["from"], entry["to"]])
        if cutaway and faces(start, end, middle, camera):
            continue
        stretch = float(np.linalg.norm(np.subtract(end, start))) / max(
            float(np.linalg.norm(np.subtract(entry["to"], entry["from"]))), 1e-6)
        openings = [(along * stretch, hole * stretch, sill, head)
                    for along, hole, sill, head in written_openings(holes, entry["from"], entry["to"], thick)]
        tall = up_to_roof(float(entry.get("tall") or walls_high), start, end, plan.get("roofs") or [], placed)
        parts.append((wall(start, end, inward_thick(start, end, middle, thick), 0.0, tall, openings), "wall"))
    if not cutaway:
        written_roofs = plan.get("roofs") or []
        parts += [(roof(entry["kind"], placed(entry["points"]), entry["eave"], entry["top"]), "roof")
                  for entry in written_roofs]
        if not written_roofs:
            parts.append((roof(kind, outline, walls_high, walls_high + rise), "roof"))
    return parts


def level_solid(points, height):
    """A level as a solid: a raised deck, plaza or platform up to a storey high stands solid from the ground, a higher
    one (an upper floor, a balcony) or a sunken one is a slab at its height."""
    return prism(points, 0.0, height) if 0.0 < height <= STOREY else prism(points, height - SLAB, height)


def up_to_roof(tall, start, end, roofs, placed):
    """A wall's top raised to the eave of a written roof over it standing higher (a roof rests on its walls; a plan's
    walls measured from a raised level under them would leave it floating)."""
    middle = (np.asarray(start, float) + np.asarray(end, float)) / 2
    for entry in roofs:
        points = np.asarray(placed(entry["points"]), float)
        if (points.min(axis=0) - 0.5 <= middle).all() and (middle <= points.max(axis=0) + 0.5).all():
            tall = max(tall, float(entry["eave"]))
    return tall


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


def laid(parts, plan, middle, heading, size=None):
    """A plan's parts (at its own origin) laid with its box's middle at `middle` (site metres) turned `heading`
    radians (environment_plan.turned_box's way), stretched to `size` (wide, deep) where it gives one."""
    wide, deep = float(plan["w"]), float(plan["d"])
    stretch = (size[0] / wide, size[1] / deep) if size else (1.0, 1.0)
    cos, sin = math.cos(heading), math.sin(heading)
    found = []
    for triangles, kind in parts:
        points = np.asarray(triangles, float).reshape(-1, 3)
        x, z = (points[:, 0] - wide / 2) * stretch[0], (points[:, 2] - deep / 2) * stretch[1]
        moved = np.column_stack([middle[0] + x * cos + z * sin, points[:, 1], middle[1] - x * sin + z * cos])
        found.append((moved.reshape(-1, 3, 3).tolist(), kind))
    return found


# --- the camera and the render -------------------------------------------------------------------------------------

def points_of(parts, kinds=None):
    """Every corner of the parts (of `kinds` only, when given), [[x, up, z]]."""
    found = [np.asarray(triangles, float).reshape(-1, 3) for triangles, kind in parts
             if triangles and (kinds is None or kind in kinds)]
    return np.concatenate(found) if found else np.zeros((0, 3))


def bounds(parts):
    """(low, high) corners round the place itself: every part but the ground round it, the ground when that is all."""
    points = points_of([part for part in parts if part[1] != "ground"]) if any(
        triangles and kind != "ground" for triangles, kind in parts) else points_of(parts)
    return points.min(axis=0), points.max(axis=0)


def corner_way(bearing=135.0):
    """The fixed view's way in plan metres (x east, y south): looking from the south-east corner to the north-west
    (`bearing`, degrees from north, is where the camera stands)."""
    turn = math.radians(bearing)
    return np.array([math.sin(turn), -math.cos(turn)])


def framed_points(framed):
    """The eight corners of the box `framed` [x, y, wide, deep, tall] with MARGIN round it."""
    x, y, wide, deep, tall = framed
    return np.array([[x + wide * across, up, y + deep * along] for across in (-MARGIN, 1 + MARGIN)
                     for along in (-MARGIN, 1 + MARGIN) for up in (0.0, tall)])


def fixed_camera(parts, framed=None, bearing=135.0):
    """(eye, forward, up, field) of the fixed concept view, 40 degrees down from the corner at `bearing`, aimed and
    set back so the place (every part but the ground; or the box `framed` [x, y, wide, deep, tall] with MARGIN round
    it) fills FILL of the frame."""
    points = framed_points(framed) if framed else points_of([part for part in parts if part[1] != "ground"])
    if not len(points):
        points = points_of(parts)
    points = points[:: max(1, len(points) // 20000)]
    way, down = corner_way(bearing), math.radians(DOWN)
    back = np.array([way[0] * math.cos(down), math.sin(down), way[1] * math.cos(down)])
    up = np.array([0.0, 1.0, 0.0])
    right, true_up, ahead = basis(-back, up)
    aim = (points.min(axis=0) + points.max(axis=0)) / 2
    focal = TALL / 2 / math.tan(math.radians(LENS) / 2)
    reach = float(np.linalg.norm(points - aim, axis=1).max()) or 1.0
    distance = reach / math.sin(math.radians(LENS) / 2)
    for _ in range(4):
        low, high = reach * 1.05, reach * 200.0
        for _ in range(40):  # the nearest eye that keeps every point inside FILL of the frame
            middle = (low + high) / 2
            xs, ys, _depth = project(points, aim + back * middle, -back, up, LENS)
            inside = np.abs(xs - WIDE / 2).max() <= FILL * WIDE / 2 and np.abs(ys - TALL / 2).max() <= FILL * TALL / 2
            low, high = (low, middle) if inside else (middle, high)
        distance = high
        xs, ys, _depth = project(points, aim + back * distance, -back, up, LENS)
        shift_x, shift_y = (xs.min() + xs.max()) / 2 - WIDE / 2, (ys.min() + ys.max()) / 2 - TALL / 2
        aim = aim + right * shift_x / focal * distance - true_up * shift_y / focal * distance
    return aim + back * distance, -back, up, LENS


def basis(forward, up):
    forward = forward / np.linalg.norm(forward)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    return right, np.cross(right, forward), forward


def project(points, eye, forward, up, field, size=(WIDE, TALL)):
    """Pixel x, y and depth of world points in a picture of `size`."""
    right, true_up, ahead = basis(forward, up)
    offset = points - eye
    depth = offset @ ahead
    focal = size[1] / 2 / math.tan(math.radians(field) / 2)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (size[0] / 2 + focal * (offset @ right) / depth, size[1] / 2 - focal * (offset @ true_up) / depth,
                depth)


def normals_of(corners):
    """Each triangle's unit normal."""
    normal = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    return normal / (np.linalg.norm(normal, axis=1, keepdims=True) + 1e-12)


def rasterised(parts, camera, size):
    """(depth, normals, albedo, smooth) buffers of the parts seen from `camera` in a picture of `size`; each pixel's
    normal faces the eye (two-sided), `smooth` where it is ground (no creases between its facets)."""
    eye, forward, up, field = camera
    depth = np.full((size[1], size[0]), np.inf)
    normals = np.zeros((size[1], size[0], 3))
    albedo = np.zeros((size[1], size[0]))
    smooth = np.zeros((size[1], size[0]), bool)
    for triangles, kind in parts:
        if not triangles:
            continue
        corners = np.asarray(triangles, float)
        xs, ys, zs = (value.reshape(-1, 3) for value in project(corners.reshape(-1, 3), eye, forward, up, field, size))
        normal = normals_of(corners)
        toward = eye - corners.mean(axis=1)
        normal *= np.where((normal * toward).sum(1) < 0, -1.0, 1.0)[:, None]  # two-sided: face the eye
        for number in np.nonzero(in_frame(xs, ys, zs, size))[0]:
            for piece in near_clipped(corners[number], (xs[number], ys[number], zs[number]), camera, size):
                found = fill(*piece, depth)
                if found is not None:
                    window, nearer = found
                    normals[window][nearer] = normal[number]
                    albedo[window][nearer] = ALBEDO.get(kind, GREY)
                    smooth[window][nearer] = kind == "ground"
    return depth, normals, albedo, smooth


def in_frame(xs, ys, zs, size):
    """Which projected triangles may land in the picture: those cut by the near plane, and those wholly in front of
    it whose box meets the frame (the far ground off screen costs nothing)."""
    with np.errstate(invalid="ignore"):
        cut = (zs <= NEAR).any(axis=1) & ~(zs <= NEAR).all(axis=1)
        seen = (zs > NEAR).all(axis=1) & (xs.max(axis=1) >= 0) & (xs.min(axis=1) <= size[0]) & \
            (ys.max(axis=1) >= 0) & (ys.min(axis=1) <= size[1])
    return cut | seen


def near_clipped(corners, projected, camera, size=(WIDE, TALL)):
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
    found_x, found_y, found_z = project(np.asarray(kept), eye, forward, up, field, size)
    return [(found_x[[0, step, step + 1]], found_y[[0, step, step + 1]], found_z[[0, step, step + 1]])
            for step in range(1, len(kept) - 1)]


def fill(xs, ys, zs, depth, perspective=True):
    """One triangle into the depth buffer, depth-tested (depth interpolated as a perspective picture's, else
    straight, as an orthographic one's); (window, nearer) where it landed, None where it did not."""
    tall, wide = depth.shape
    if perspective and np.any(zs <= NEAR * 0.99) or not np.all(np.isfinite(xs)):
        return None
    left, right = max(int(math.floor(xs.min())), 0), min(int(math.ceil(xs.max())), wide - 1)
    top, bottom = max(int(math.floor(ys.min())), 0), min(int(math.ceil(ys.max())), tall - 1)
    if left > right or top > bottom:
        return None
    area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
    if abs(area) < 1e-9:
        return None
    grid_x, grid_y = np.meshgrid(np.arange(left, right + 1) + 0.5, np.arange(top, bottom + 1) + 0.5)
    one = ((xs[1] - grid_x) * (ys[2] - grid_y) - (xs[2] - grid_x) * (ys[1] - grid_y)) / area
    two = ((xs[2] - grid_x) * (ys[0] - grid_y) - (xs[0] - grid_x) * (ys[2] - grid_y)) / area
    three = 1.0 - one - two
    inside = (one >= 0) & (two >= 0) & (three >= 0)
    if not inside.any():
        return None
    seen = 1.0 / (one / zs[0] + two / zs[1] + three / zs[2]) if perspective else \
        one * zs[0] + two * zs[1] + three * zs[2]
    window = (slice(top, bottom + 1), slice(left, right + 1))
    nearer = inside & (seen < depth[window])
    depth[window][nearer] = seen[nearer]
    return window, nearer


def creases(normals, depth, smooth):
    """Where neighbouring pixels turn sharply (not both ground) or jump in depth: the model's edges."""
    found = np.zeros(depth.shape, bool)
    finite = np.where(np.isfinite(depth), depth, 1e9)
    for axis in (0, 1):
        both_smooth = (smooth[:-1] & smooth[1:]) if axis == 0 else (smooth[:, :-1] & smooth[:, 1:])
        turn = (np.linalg.norm(np.diff(normals, axis=axis), axis=-1) > 0.25) & ~both_smooth
        jump = np.abs(np.diff(finite, axis=axis)) > 0.03 * np.minimum(finite[:-1] if axis == 0 else finite[:, :-1],
                                                                      finite[1:] if axis == 0 else finite[:, 1:])
        edge = turn | jump
        if axis == 0:
            found[:-1] |= edge
        else:
            found[:, :-1] |= edge
    return found


def sun_way(light):
    """The key light's way toward the sun (x east, y up, z south) from (azimuth, altitude) in degrees, raised to
    LOWEST_SUN when lower (the blockout shows structure, never the hour: the look adds night); NO_SUN with none."""
    azimuth, altitude = light or NO_SUN
    return sky_way(azimuth, max(altitude, LOWEST_SUN))


def light_basis(way):
    """(right, up, ahead) of the sun's view: looking along its light, down `way` reversed."""
    helper = np.array([0.0, 0.0, 1.0]) if abs(way[1]) > 0.99 else np.array([0.0, 1.0, 0.0])
    return basis(-way, helper)


def shadow_map(parts, way):
    """(right, up, ahead, left, top, scale, depth) of an orthographic depth map from the sun along `way` over every
    part that casts a shadow (all but the ground); None with none."""
    casters = [np.asarray(triangles, float) for triangles, kind in parts if triangles and kind != "ground"]
    if not casters:
        return None
    right, up, ahead = light_basis(way)
    every = np.concatenate([corners.reshape(-1, 3) for corners in casters])
    left, top = float((every @ right).min()), float((every @ up).max())
    span = max(float((every @ right).max()) - left, top - float((every @ up).min()), 1e-3)
    scale = (SHADOW - 2) / span
    depth = np.full((SHADOW, SHADOW), np.inf)
    for corners in casters:
        flat = corners.reshape(-1, 3)
        xs, ys, zs = (((flat @ right) - left) * scale + 1).reshape(-1, 3), ((top - (flat @ up)) * scale + 1).reshape(
            -1, 3), (flat @ ahead).reshape(-1, 3)
        for number in range(len(corners)):
            fill(xs[number], ys[number], zs[number], depth, perspective=False)
    return right, up, ahead, left, top, scale, depth


def sunlit(found, points, normals):
    """How much of the sun reaches each point (0 to 1), its shadow's edge softened over SOFT pixels of the map."""
    if found is None or not len(points):
        return np.ones(len(points))
    right, up, ahead, left, top, scale, depth = found
    lifted = points + normals * SHADOW_BIAS - ahead * SHADOW_BIAS
    xs, ys, zs = ((lifted @ right) - left) * scale + 1, (top - (lifted @ up)) * scale + 1, lifted @ ahead
    total = np.zeros(len(points))
    count = 0
    for down in range(-SOFT, SOFT + 1):
        for across in range(-SOFT, SOFT + 1):
            rows, columns = np.floor(ys).astype(int) + down, np.floor(xs).astype(int) + across
            outside = (rows < 0) | (rows >= SHADOW) | (columns < 0) | (columns >= SHADOW)
            blocker = depth[np.clip(rows, 0, SHADOW - 1), np.clip(columns, 0, SHADOW - 1)]
            total += outside | (zs <= blocker + SHADOW_BIAS)
            count += 1
    return total / count


def seen_points(depth, camera, size):
    """The world point of every pixel the model covers (`depth` finite), [[x, up, z]] in their order."""
    eye, forward, up, field = camera
    right, true_up, ahead = basis(forward, up)
    focal = size[1] / 2 / math.tan(math.radians(field) / 2)
    rows, columns = np.nonzero(np.isfinite(depth))
    far = depth[rows, columns][:, None]
    across, high = ((columns + 0.5 - size[0] / 2) / focal)[:, None], ((size[1] / 2 - rows - 0.5) / focal)[:, None]
    return eye + far * (ahead + across * right + high * true_up)


def worlds_drawn(image, worlds, camera):
    """Each body of the sky (overhead.py's) drawn as its disc at its true direction and size, its face lit from the
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


def smoothed(normals, smooth):
    """The normals with the ground's (`smooth`) averaged over its neighbours, so its facets shade as one surface."""
    from scipy.ndimage import uniform_filter
    weight = uniform_filter(smooth.astype(float), GROUND_BLUR)
    found = normals.copy()
    for axis in range(3):
        blurred = uniform_filter(normals[..., axis] * smooth, GROUND_BLUR) / np.maximum(weight, 1e-9)
        found[..., axis] = np.where(smooth, blurred, normals[..., axis])
    return found / (np.linalg.norm(found, axis=-1, keepdims=True) + 1e-12)


def halved(values, size):
    """A SUPER-sized buffer averaged down to `size`."""
    return values.reshape(size[1], SUPER, size[0], SUPER, *values.shape[2:]).mean(axis=(1, 3))


def render(parts, camera, worlds=(), light=None):
    """The PIL picture of the parts from `camera`, lit by the sun at `light` (azimuth, altitude; None: NO_SUN) with
    its shadows, the worlds in its sky drawn where they fall in frame."""
    from PIL import Image
    size = (WIDE * SUPER, TALL * SUPER)
    depth, normals, albedo, smooth = rasterised(parts, camera, size)
    hit = np.isfinite(depth)
    way = sun_way(light)
    facing = smoothed(normals, smooth)[hit]
    shade = albedo[hit] * (AMBIENT + SKY_FILL * (0.5 + 0.5 * facing[:, 1]) + KEY * np.clip(facing @ way, 0.0, 1.0) *
                           sunlit(shadow_map(parts, way), seen_points(depth, camera, size), facing))
    grey = np.full(depth.shape, float(SKY_GREY[0] if worlds else BACKGROUND[0]))
    grey[hit] = np.clip(shade, 0.0, 1.0) * 255.0
    grey[creases(normals, depth, smooth) & hit] *= CREASE
    colour = np.repeat(halved(grey, (WIDE, TALL))[..., None], 3, axis=-1)
    if worlds:
        colour[~halved(hit.astype(float), (WIDE, TALL)).astype(bool)] = SKY_GREY
    image = {"colour": colour, "depth": np.where(halved(hit.astype(float), (WIDE, TALL)) > 0, 1.0, np.inf)}
    worlds_drawn(image, worlds, camera)
    return Image.fromarray(np.clip(np.round(colour), 0, 255).astype(np.uint8))


def overhead_camera(parts, world):
    """(eye, forward, up, field) behind the place from `world` and above it, looking out over it at `world`: the place
    low in the frame, the world high, both in when it stands under about 45 degrees."""
    low, high = bounds(parts)
    middle = (low + high) / 2
    way = sky_way(world["azimuth"], world["altitude"])
    level = np.array([way[0], 0.0, way[2]])
    level = level / (np.linalg.norm(level) or 1.0)
    back = float(np.linalg.norm((high - low)[[0, 2]])) * 0.75
    eye = np.array([middle[0], high[1] + back * math.tan(math.radians(OVERHEAD_DOWN)), middle[2]]) - level * back
    down = math.degrees(math.atan2(eye[1] - middle[1], back))
    reach = OVERHEAD_LENS / 2 - OVERHEAD_EDGE
    pitch = math.radians(min(max((world["altitude"] - down) / 2, world["altitude"] - reach), 80.0))
    forward = level * math.cos(pitch) + np.array([0.0, math.sin(pitch), 0.0])
    return eye, forward, np.array([0.0, 1.0, 0.0]), OVERHEAD_LENS


# --- what a node's blockout is built from ------------------------------------------------------------------------

def block_parts(block):
    """One of a site's blocks at its height and roof (environment_plan's block)."""
    base, tall = float(block.get("base") or 0.0), float(block.get("tall") or 0.0)
    found = [(prism(block["points"], base, base + tall), "wall")] if tall > 0 else []
    if block.get("roof") in ("dome", "vault", "pitched") and block.get("rise"):
        found.append((roof(block["roof"], block["points"], base + tall, base + tall + float(block["rise"])), "roof"))
    return found


def part_laid(block, plan):
    """A site's part that is a place with a plan of its own, at full detail where the block lays it: its box's middle
    and heading read from the block's corners (environment_plan.turned_box's)."""
    corners = np.asarray(block["points"], float)
    middle = corners.mean(axis=0)
    run, side = corners[1] - corners[0], corners[2] - corners[1]
    heading = math.atan2(-run[1], run[0])
    return laid(shell_parts(plan, on_ground=True), plan, middle, heading,
                (float(np.linalg.norm(run)), float(np.linalg.norm(side))))


def front_spot(parts):
    """Where a person stands for scale: on the ground 2 m out from the place's foot nearest the fixed view."""
    points = points_of(parts)
    feet = points[points[:, 1] < 0.5] if (points[:, 1] < 0.5).any() else points
    way = corner_way()
    nearest = feet[np.argmax(feet[:, 0] * way[0] + feet[:, 2] * way[1])]
    return nearest[0] + way[0] * 2.0, nearest[2] + way[1] * 2.0


def site_parts(site, plan_of=None):
    """The parts of a top place's site on the environment's plan (module docstring), in site metres (its middle at
    0, 0): each block that is a place with a plan of its own (`plan_of(place)`, {} with none) at full detail, else the
    place's own written plan at full detail laid on the site's middle, else the site's blocks; the ground round it
    falling with its body's radius (`radius_m`) through its spot heights; a person in front where
    its plan has people."""
    plan_of = plan_of or (lambda place: {})
    footprint = site.get("footprint") or rectangle(-site["size"][0] / 2, -site["size"][1] / 2, *site["size"][:2])
    blocks = site.get("blocks") or [{"points": footprint, "tall": site["size"][2], "roof": "flat"}]
    spots = list((site.get("terrain") or {}).get("spots") or [])
    own = plan_of(site.get("place")) or {}
    planned = {index: plan_of(block.get("name")) for index, block in enumerate(blocks) if block.get("name")}
    planned = {index: plan for index, plan in planned.items() if plan.get("w") and plan.get("d")}
    parts = []
    if planned:
        for index, block in enumerate(blocks):
            parts += part_laid(block, planned[index]) if index in planned else block_parts(block)
    elif own.get("outline") and own.get("w") and own.get("d"):  # a written plan; a data plan gives only its box
        parts = laid(shell_parts(own, on_ground=True), own, [0.0, 0.0], 0.0)
        spots += [[x - own["w"] / 2, y - own["d"] / 2, height]
                  for x, y, height in (own.get("terrain") or {}).get("spots") or []]
    else:
        for block in blocks:
            parts += block_parts(block)
    if not parts:
        parts = [(prism(footprint, 0.0, max(float(site["size"][2]), 0.1)), "wall")]
    if own.get("people"):
        parts.append((person(*front_spot(parts)), "person"))
    low, high = bounds(parts)
    reach = max(high[0] - low[0], high[2] - low[2], 10.0) * GROUND_REACH
    middle = (low + high) / 2
    box = [middle[0] - reach, middle[2] - reach, middle[0] + reach, middle[2] + reach]
    return [(ground(spots, box, site.get("radius_m")), "ground")] + parts


def sized(own, hold, holder_plan):
    """An inside place's own plan with the size of its box on the holder's plan where it gives none, walled where it
    is outdoor (an inside place has walls in the holder's blockout)."""
    found = {**own, "w": own.get("w") or hold["w"], "d": own.get("d") or hold["d"],
             "height": own.get("height") or holder_plan.get("height")}
    return {**found, "shell": None, "height": f"walls {STOREY} m"} if outdoor(found) else found


def inside_parts(place, holder_plan, mine_plan, camera_way):
    """An inside place's parts: its own room shell alone at full detail (walls, openings, levels, stairs, items, a
    person on its first standing spot; `mine_plan` its own plan) where the holder's plan lays it, cut away; no hull and
    no rooms beside it (the owner, 2026-10-21: the room is drawn on its own). Missing when the holder's plan does not
    lay `place` out."""
    mine = next((hold for hold in holder_plan.get("holds") or [] if hold["place"] == place), None)
    if mine is None:
        raise Missing(f"the plan holding {place} does not lay it out yet")
    own = sized(mine_plan or {}, mine, holder_plan)
    box = [mine["x"], mine["y"], mine["w"], mine["d"]]
    return shell_parts(own, box, True, camera_way, standing=True), [*box, heights_of(own)[0]]


def scene_of(store, node):
    """(parts, framed, worlds, light) of `node`'s blockout from its parent's plan (module docstring): `framed` the box
    [x, y, wide, deep, tall] the view frames (None: every part), `light` the Sun's (azimuth, altitude) over its site
    at its scene time (None: NO_SUN); Missing while that plan is not there."""
    from score.review import concepts, plans
    above = concepts.above(node, store)
    if above:
        shown = plans.current(store, above)
        holder_plan = (shown or {}).get("plan") or {}
        parts, box = inside_parts(node, holder_plan, own_plan(store, node), corner_way())
        return parts, box, [], None
    from score.review import environment_plan
    site = environment_plan.site_of(store, node)
    if site is None:
        raise Missing(f"the environment's plan has no site for {node} yet")
    sun = next(iter((site.get("overhead") or {}).get("lights", [])), None)
    return (site_parts(site, lambda place: own_plan(store, place) if place else {}), None,
            (site.get("overhead") or {}).get("bodies", []), (sun["azimuth"], sun["altitude"]) if sun else None)


def scene_key(scene):
    """The key of a scene's render: what it is built from and this module's code (VERSION), so a render made by older
    code is never served again."""
    parts, framed, worlds, light = scene
    digest = hashlib.sha256(json.dumps([VERSION, framed, worlds, light], sort_keys=True).encode())
    for triangles, kind in parts:
        digest.update(kind.encode())
        digest.update(np.asarray(triangles, dtype=np.float64).tobytes())
    return digest.hexdigest()


def own_plan(store, place):
    """A place's own plan: the one shown (written or his edit), else its data plan, {} with neither."""
    from score.review import concepts, plans
    shown = plans.current(store, place) if plans.counts(store, place) else None
    return (shown or {}).get("plan") or concepts.plan_of(place)


def drawn(scene):
    """The PIL blockout of a scene (`scene_of`) from the fixed concept view."""
    parts, framed, worlds, light = scene
    return render(parts, fixed_camera(parts, framed), worlds, light)


def picture(store, node):
    """The PIL blockout of `node` from the fixed concept view; Missing while its parent's plan is not there."""
    return drawn(scene_of(store, node))


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


def overhead_view(store, node):
    """The PIL picture from behind and above the site looking out at the largest world in its sky that the fixed view
    does not show, None when there is none (an inside place, or every world below the horizon or in frame)."""
    parts, _, worlds, light = scene_of(store, node)
    hidden = unseen(parts, worlds)
    if not hidden:
        return None
    biggest = max(hidden, key=lambda world: world["across"])
    return render(parts, overhead_camera(parts, biggest), worlds, light)


def main(argv):
    """`<node> [--out FILE] [--overhead FILE]`: its blockout (and overhead view) from the framework's store."""
    import argparse
    from score.store import Store
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("node")
    parser.add_argument("--out", default="blockout.png")
    parser.add_argument("--overhead")
    options = parser.parse_args(argv)
    store = Store.default()
    try:
        picture(store, options.node).save(options.out)
        found = overhead_view(store, options.node) if options.overhead else None
    except Missing as missing:
        print(f"missing: {missing}", file=sys.stderr)
        return 1
    if found is not None:
        found.save(options.overhead)
    print(f"{options.node}: {options.out}" + (f", overhead {options.overhead}" if found is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
