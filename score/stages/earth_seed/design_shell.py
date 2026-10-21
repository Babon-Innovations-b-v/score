"""A designed scene's room shell, laid in its base layer from the plan the creator locked (CONTEXT.md "design",
"plan"; the owner, 2026-10-21: every designed scene's base from its own design, never from a lost seed). It is laid
for an inside room whose plan's shell is `kit` (its walls and floors are its kit's; `laid_for`) in every designed
scene, whose base never lays data/kit (earth_seed.kit_is_base: those kits were laid for the old concepts' rooms; a
scene he added in the app has none). A domed or outdoor shell is the scene record's,
which the assembly lays (scene_record.writer), and an open place (`inside` false: the street, the square) has no room
to close, so nothing is laid here for either.

    deck   each level of the plan (else its outline at the floor) a slab SLAB thick, its top DECK_BELOW under the
           level, where the scene's floor pieces lie on it, out to the walls (BACKING past the plan's line)
    walls  round the outline (the plan's `outline`, else its box w x d), each edge a slab of its written wall's
           thickness (else THICK) standing BACKING behind the plan's inside line, from the deck's foot to its written
           height (else the height words' ceiling, else STOREY), raised to a roof's eave over it; each opening on it
           (a written plan's `openings`, else a data plan's `doors`) cut from its sill to its head
    roof   each written roof over its points out to the walls: a flat one a slab on its eave; one rising (shed,
           pitched, dome, vault) a gable along its box's longer side, as the blockout draws it
           (score/review/blockout.py `pitched`: the structure picture the concept was drawn to); no written roof, a
           flat one on the walls' height

Points are plan metres (x east, y south from the plan's north-west corner) stood in the plan's own frame
(scene_record.plan.frame_of: its `frame` anchor, else the room's middle on its floor), as plan@<place> and the scene
record stand it. Every face is painted with the scene record's backing surface (SURFACE, a library surface: the shell
stands behind the scene's own shell pieces, which the prop pipeline makes) and marked score:plain `shell`, so the
placeholder gate (tools/usd/placeholders.py) reads it as the room's own shell.

    entries = design_shell.shell(plan)          # [(name, triangles in plan metres, what it was made from)]
    design_shell.lay(base_layer, place, plan, scene)   # the shell under /<place>/Shell (scene: tools/usd/scene.py)
"""
import re

import numpy as np

from score.stages.scene_record import plan as place_plan

# The scene record's backing shell (scene_record.writer SHELL_SURFACE, BACKING, DECK_BELOW; held equal by the test):
# the shell stands this far behind the plan's inside line and the deck this far under the floor.
SURFACE = "roof_steel_paint"
BACKING = 0.15
DECK_BELOW = 0.042
SLAB = 0.2  # metres of a deck or roof slab
THICK = 0.3  # metres of a wall the plan gives no thickness (the blockout's)
STOREY = 3.0  # metres of a wall neither the plan nor its words give a height (the blockout's)
DOOR_HEAD = 2.1  # metres of a door's head the plan gives none (the blockout's)
ON_WALL = 0.3  # metres an opening may stand off its wall's line past the wall's thickness and still be cut in it
CEILING = re.compile(r"\bceiling[^0-9;,]*?(\d+(?:\.\d+)?) ?m\b")
DOOR_SIZE = re.compile(r"\d+(?:\.\d+)? ?x ?(\d+(?:\.\d+)?) ?m")  # a data door's words "(0.9 x 2.0 m)": its height
ROOT = "Shell"


# --- outlines ----------------------------------------------------------------------------------------------------

def outline_of(plan):
    """The plan's floor outline [[x, y]] (its `outline`, else its box), clockwise on a map (x east, y south), no
    point repeated."""
    points = [[float(x), float(y)] for x, y in (plan.get("outline") or
                                                 [[0, 0], [plan["w"], 0], [plan["w"], plan["d"]], [0, plan["d"]]])]
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]
    return points if signed_area(points) > 0 else points[::-1]


def signed_area(points):
    """The signed area of an outline: positive when it runs clockwise on a map (x east, y south)."""
    return sum(one[0] * two[1] - two[0] * one[1] for one, two in zip(points, points[1:] + points[:1])) / 2


def inside(point, points):
    """Whether a point lies inside an outline (even-odd rule)."""
    found = False
    for one, two in zip(points, points[1:] + points[:1]):
        if (one[1] > point[1]) != (two[1] > point[1]):
            cross = one[0] + (point[1] - one[1]) * (two[0] - one[0]) / (two[1] - one[1])
            found ^= point[0] < cross
    return found


def triangles_of(points):
    """An outline's triangles by ear clipping, each as three indices (a simple outline, convex or not)."""
    left = list(range(len(points)))
    area = signed_area(points)
    found = []
    while len(left) > 3:
        for position in range(len(left)):
            before, at, after = left[position - 1], left[position], left[(position + 1) % len(left)]
            corner = [points[before], points[at], points[after]]
            if (signed_area(corner) > 0) != (area > 0) or abs(signed_area(corner)) < 1e-12:
                continue
            if any(inside(points[other], corner) for other in left if other not in (before, at, after)):
                continue
            found.append((before, at, after))
            left.pop(position)
            break
        else:
            raise ValueError(f"an outline of {len(points)} points crosses itself: it cannot be triangulated")
    return found + [tuple(left)]


# --- solids --------------------------------------------------------------------------------------------------------

def up(points, height):
    """Plan points at a height as [x, up, y]."""
    return [[point[0], height, point[1]] for point in points]


def cap(points, height, facing_up):
    """An outline as a flat face at a height, its triangles turned to face up or down."""
    ring = up(points, height)
    order = triangles_of(points)
    # a clockwise outline's triangles face down as written (x east, z south, y up): turned over to face up
    return [[ring[one], ring[three], ring[two]] if facing_up else [ring[one], ring[two], ring[three]]
            for one, two, three in order]


def prism(points, low, high):
    """A closed solid of an outline from `low` to `high`, every face turned outward."""
    points = points if signed_area(points) > 0 else points[::-1]
    below, above = up(points, low), up(points, high)
    sides = []
    for step in range(len(points)):
        after = (step + 1) % len(points)
        sides += [[below[step], above[after], below[after]], [below[step], above[step], above[after]]]
    return cap(points, high, True) + cap(points, low, False) + sides


def gable(points, eave, top):
    """A gable roof over an outline's box, its ridge along the longer side (the blockout's `pitched`)."""
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    west, east, north, south = min(xs), max(xs), min(ys), max(ys)
    corners = [[west, eave, north], [east, eave, north], [east, eave, south], [west, eave, south]]
    if east - west >= south - north:
        middle = (north + south) / 2
        ridge = [[west, top, middle], [east, top, middle]]
        slopes = [[corners[0], corners[1], ridge[1]], [corners[0], ridge[1], ridge[0]],
                  [corners[2], corners[3], ridge[0]], [corners[2], ridge[0], ridge[1]]]
        return slopes + [[corners[3], corners[0], ridge[0]], [corners[1], corners[2], ridge[1]]]
    middle = (west + east) / 2
    ridge = [[middle, top, north], [middle, top, south]]
    slopes = [[corners[1], corners[2], ridge[1]], [corners[1], ridge[1], ridge[0]],
              [corners[3], corners[0], ridge[0]], [corners[3], ridge[0], ridge[1]]]
    return slopes + [[corners[0], corners[1], ridge[0]], [corners[2], corners[3], ridge[1]]]


# --- walls -------------------------------------------------------------------------------------------------------

def measured_ceiling(plan):
    """The ceiling the plan's height words give (the first `ceiling <n> m`), else None."""
    found = CEILING.search(str(plan.get("height") or ""))
    return float(found.group(1)) if found else None


def written_wall(plan, start, end):
    """The written wall (`walls`: {from, to, thick, tall}) standing on the outline's edge from `start` to `end`, else
    {}."""
    for entry in plan.get("walls") or []:
        if not isinstance(entry, dict) or "from" not in entry:
            continue
        ends = [list(map(float, entry["from"])), list(map(float, entry["to"]))]
        if all(np.allclose(one, two, atol=0.01) for one, two in zip(sorted(ends), sorted([start, end]))):
            return entry
    return {}


def openings_of(plan):
    """Every opening of the plan as {at [x, y], wide, sill, head}: a written plan's `openings`, else a data plan's
    `doors` ([side, along, wide, words]: N and S along x, E and W along y; its head from its words)."""
    if plan.get("openings"):
        return [{"at": list(map(float, opening["at"])), "wide": float(opening["wide"]),
                 "sill": float(opening.get("sill") or 0.0), "head": float(opening.get("head") or DOOR_HEAD)}
                for opening in plan["openings"]]
    found = []
    for door in plan.get("doors") or []:
        if not (isinstance(door[0], str) and door[0] in ("N", "S", "E", "W") and len(door) >= 3):
            continue
        along, sized = float(door[1]), DOOR_SIZE.search(str(door[-1]))
        at = {"N": [along, 0.0], "S": [along, plan["d"]], "W": [0.0, along], "E": [plan["w"], along]}[door[0]]
        found.append({"at": at, "wide": float(door[2]), "sill": 0.0,
                      "head": float(sized.group(1)) if sized else DOOR_HEAD})
    return found


def on_edge(openings, start, end, thick):
    """(from, to, sill, head) along the edge from `start` of each opening standing on it, clipped to the edge."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    length = float(np.linalg.norm(end - start))
    along = (end - start) / length
    found = []
    for opening in openings:
        offset = np.asarray(opening["at"], float) - start
        off_line = abs(offset[0] * along[1] - offset[1] * along[0])
        middle = float(offset @ along)
        if off_line <= thick + ON_WALL and -0.1 <= middle <= length + 0.1:
            found.append((max(0.0, middle - opening["wide"] / 2), min(length, middle + opening["wide"] / 2),
                          opening["sill"], opening["head"]))
    return sorted(found)


def outward(start, end):
    """The unit normal of an edge pointing out of a clockwise-on-a-map outline (its left as one walks it, y south)."""
    run = np.asarray(end, float) - np.asarray(start, float)
    return np.array([run[1], -run[0]]) / float(np.linalg.norm(run))


def offset_corner(point, normal_in, normal_out, reach_in, reach_out):
    """Where the line of the edge ending at `point` (pushed out by reach_in along normal_in) meets the line of the edge
    starting there (pushed out by reach_out along normal_out); the in edge's push where the two run straight on."""
    point = np.asarray(point, float)
    first, second = point + normal_in * reach_in, point + normal_out * reach_out
    way_in, way_out = np.array([-normal_in[1], normal_in[0]]), np.array([-normal_out[1], normal_out[0]])
    across = way_in[0] * way_out[1] - way_in[1] * way_out[0]
    if abs(across) < 1e-9:
        return first
    gap = second - first
    return first + way_in * ((gap[0] * way_out[1] - gap[1] * way_out[0]) / across)


def grown(points, reach=BACKING):
    """An outline (clockwise on a map) pushed out by `reach` on every side, its corners mitred."""
    count = len(points)
    normals = [outward(points[index], points[(index + 1) % count]) for index in range(count)]
    return [list(offset_corner(points[index], normals[index - 1], normals[index], reach, reach))
            for index in range(count)]


def spans(length, cuts, low, high):
    """(from, to, bottom, top) of a wall's pieces along its length round its openings' cuts (an opening's sill and
    head are heights over the floor; under a door the wall's foot below the floor stays)."""
    found, edge = [], 0.0
    for left, right, sill, head in cuts:
        if left > edge:
            found.append((edge, left, low, high))
        if sill > low:
            found.append((left, right, low, sill))
        if head < high:
            found.append((left, right, head, high))
        edge = max(edge, right)
    if edge < length:
        found.append((edge, length, low, high))
    return found


def wall_height(plan, entry, roof_eave):
    """A wall's top: its written height, else the words' ceiling, else STOREY; raised to the roof's eave over it."""
    tall = float(entry.get("tall") or measured_ceiling(plan) or STOREY)
    return max(tall, roof_eave or 0.0)


def walls(plan, outline, roof_eave):
    """[(name, triangles, from)] of the outline's walls (module docstring), each edge's pieces round its openings."""
    count, openings = len(outline), openings_of(plan)
    entries = [written_wall(plan, outline[index], outline[(index + 1) % count]) for index in range(count)]
    thick = [float(entry.get("thick") or THICK) for entry in entries]
    normals = [outward(outline[index], outline[(index + 1) % count]) for index in range(count)]
    inner = [offset_corner(outline[index], normals[index - 1], normals[index], BACKING, BACKING)
             for index in range(count)]
    outer = [offset_corner(outline[index], normals[index - 1], normals[index], BACKING + thick[index - 1],
                           BACKING + thick[index]) for index in range(count)]
    found = []
    for index in range(count):
        after = (index + 1) % count
        start, end = np.asarray(outline[index], float), np.asarray(outline[after], float)
        length = float(np.linalg.norm(end - start))
        if length < 1e-6:
            continue
        along = (end - start) / length
        cuts = on_edge(openings, start, end, thick[index])
        high = wall_height(plan, entries[index], roof_eave)
        triangles = []
        for begin, finish, bottom, top in spans(length, cuts, -DECK_BELOW - SLAB, high):
            near = [inner[index] if begin <= 1e-9 else start + along * begin + normals[index] * BACKING,
                    inner[after] if finish >= length - 1e-9 else start + along * finish + normals[index] * BACKING]
            far = [outer[index] if begin <= 1e-9 else near[0] + normals[index] * thick[index],
                   outer[after] if finish >= length - 1e-9 else near[1] + normals[index] * thick[index]]
            triangles += prism([list(near[0]), list(near[1]), list(far[1]), list(far[0])], bottom, top)
        said = (f"the plan's wall {index + 1} from {outline[index]} to {outline[after]}, {thick[index]:g} m thick "
                f"{BACKING:g} m behind its inside line, {high:g} m high" +
                (f", {len(cuts)} openings cut" if cuts else ""))
        found.append((f"wall_{index + 1}", triangles, said))
    return found


# --- the shell -----------------------------------------------------------------------------------------------------

def decks(plan, outline):
    """[(name, triangles, from)] of each level's slab (else the outline's at the floor)."""
    levels = [level for level in plan.get("levels") or [] if len(level.get("points") or []) >= 3] or \
        [{"name": "floor", "height": 0.0, "points": outline}]
    found = []
    for number, level in enumerate(levels, 1):
        points = grown(outline_of({"outline": level["points"]}))
        top = float(level["height"]) - DECK_BELOW
        found.append((f"deck_{number}", prism(points, top - SLAB, top),
                      f"the plan's level {level.get('name', number)!r} at {float(level['height']):g} m: its deck "
                      f"{SLAB:g} m thick, {DECK_BELOW:g} m under it, out to the walls {BACKING:g} m behind its line"))
    return found


def roofs(plan, outline, high):
    """[(name, triangles, from)] of each written roof (module docstring), else a flat one on the walls' `high`."""
    written = [entry for entry in plan.get("roofs") or [] if len(entry.get("points") or []) >= 3]
    if not written:
        return [("roof_1", prism(grown(outline), high, high + SLAB), f"no written roof: flat on the walls' {high:g} m")]
    found = []
    for number, entry in enumerate(written, 1):
        points, eave = grown(outline_of({"outline": entry["points"]})), float(entry["eave"])
        top = float(entry.get("top") or eave)
        rising = top > eave + 1e-6
        triangles = gable(points, eave, top) if rising else prism(points, eave, eave + SLAB)
        found.append((f"roof_{number}", triangles,
                      f"the plan's {entry.get('kind', 'flat')} roof, eave {eave:g} m" +
                      (f", top {top:g} m: a gable along its box's longer side (the blockout's)" if rising else
                       f": a slab {SLAB:g} m thick on it")))
    return found


def lowest_eave(plan):
    """The lowest eave of the plan's written roofs, else None."""
    eaves = [float(entry["eave"]) for entry in plan.get("roofs") or [] if "eave" in entry]
    return min(eaves) if eaves else None


def laid_for(plan):
    """Whether the plan's room shell is laid here: an inside room (`inside`, read as plan@<place> reads a kit shell's)
    whose kit holds its walls (shell `kit`)."""
    return plan.get("shell") == "kit" and bool(plan.get("inside"))


def shell(plan):
    """[(name, triangles [[[x, up, y] x 3]] in plan metres, what it was made from)] of the plan's room shell."""
    outline = outline_of(plan)
    eave = lowest_eave(plan)
    found = decks(plan, outline) + walls(plan, outline, eave)
    high = eave if eave is not None else (measured_ceiling(plan) or STOREY)
    return found + roofs(plan, outline, high)


def placed(triangles, plan):
    """Plan-metre triangles ([x, up, y]) as points in the place's frame (scene_record.plan.frame_of)."""
    corner, east, south = place_plan.frame_of(plan)
    points = np.asarray(triangles, float).reshape(-1, 3)
    return corner + np.outer(points[:, 0], east) + np.outer(points[:, 2], south) + \
        np.outer(points[:, 1], [0.0, 1.0, 0.0])


def built(triangles, plan):
    """A shell part as tools/usd/builders' mesh: its triangles stood in the place's frame, each corner its own point
    and its uvs metres across the face's own plane (the axis its normal leans on most left out)."""
    points = placed(triangles, plan)
    corners = points.reshape(-1, 3, 3)
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    dropped = np.abs(normals).argmax(axis=1)
    uvs = np.array([np.delete(corner, axis) for face, axis in zip(corners, dropped) for corner in face])
    return {"points": points, "triangles": np.arange(len(points)).reshape(-1, 3), "uvs": uvs, "surface": SURFACE}


def lay(layer_path, place, plan, scene):
    """The plan's room shell under /<place>/Shell in the base layer at `layer_path`, each part a mesh painted with
    SURFACE from the place's library (scene: tools/usd/scene.py, its mesh_prim and bind_surface); the parts' names."""
    from pxr import Sdf, Usd, UsdGeom
    stage = Usd.Stage.Open(Sdf.Layer.FindOrOpen(str(layer_path)))
    UsdGeom.Scope.Define(stage, f"/{place}/{ROOT}")
    names = []
    for name, triangles, said in shell(plan):
        if not triangles:
            continue
        prim = scene.mesh_prim(stage, f"/{place}/{ROOT}/{name}", built(triangles, plan))
        scene.bind_surface(stage, prim, place, SURFACE)
        for key, value in (("score:kind", "shell"), ("score:plain", "shell"), ("score:from", said)):
            prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
        names.append(name)
    stage.GetRootLayer().Save()
    return names
