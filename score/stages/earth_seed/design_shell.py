"""A designed scene's shell, from the plan the creator locked (CONTEXT.md "design", "plan"; the owner, 2026-10-21: every
scene builds from its design alone, every old kit retired). The room shell's pieces (`pieces`: each level's deck, the
outline's walls with every opening cut, the roofs) are one answer for both who lay them: the earth seed lays a room
whose kit holds its walls in its base (`laid_for`), the scene record every other enclosed place's
(scene_record.writer, `inside`), and the scene record every stair and ramp; the earth seed lays an open place's
raised levels (the street, the square, the base: a plan that encloses nothing), so nothing is drawn twice.

    room   a plan whose shell is `kit` (its walls are the design's own: the Earth's rooms, the ship's) and that is
           inside (`inside`; a plan that says neither is a room when it writes walls: a scene added in the app, the
           docking airlock); an open place (`inside` false) has no room to close
    deck   (a room) each level of the plan (else its outline at the floor) a slab SLAB thick, its top DECK_BELOW under
           the level, out to the walls (BACKING past the plan's line)
    wall   (a room) round the outline (the plan's `outline`, else its box w x d), each edge a slab of its written wall's
           thickness (else THICK) standing BACKING behind the plan's inside line, from the deck's foot to its written
           height (else the height words' ceiling, else STOREY), raised to a roof's eave over it; each opening on it
           (a door, window, gate or opening: a written plan's `openings`, else a data plan's `doors`) cut from its
           sill to its head
    roof   (a room) each written roof over its points out to the walls: a flat one a slab on its eave; one rising
           (shed, pitched, dome, vault) a closed gable along its box's longer side; no written roof, a flat one on
           the walls' height
    level  (an open place: no room, and a plan that encloses nothing, `encloses`) each level standing off the ground by
           more than LEVEL_OFF: one up to STOREY high stands solid from the ground (a raised deck, a
           stage); a higher one a slab SLAB thick under its height (a balcony)

Points are plan metres (x east, y south from the plan's north-west corner) stood in the plan's own frame
(scene_record.plan.frame_of: its `frame` anchor, else the room's middle on its floor), as plan@<place> and the scene
record stand it. Each part the earth seed lays takes its surface from the scene's own surface library
(surface-library@<scene>, its materials.json: the first variant its `kinds` gives the part's kind, PART_KINDS), laid
under /<place>/Library and bound; a part whose kinds the library gives no variant, or a scene whose library is not
made, is named missing on its mesh (score:surface:missing), never painted another way. Every part is a static collider
(tools/usd/colliders.py) of kind structure, marked score:plain `shell`, so the collision gate holds it and the
placeholder gate reads it as the scene's own shell.

    entries = design_shell.pieces(plan)     # [(name, builders' pieces in plan metres, what it was made from)]
    entries = design_shell.shell(plan)      # [(name, triangles in plan metres, from)]: what the earth seed lays
    design_shell.lay(base_layer, place, plan, tools, library)   # under /<place>/Shell (tools: tools/usd's export
                                                                # module; library: the materials.json or None)
    design_shell.arches(plan, rows)         # [(row, item, shape)]: the arched structure the scene record lays

An arched structure row (`arched`: a rib, an arch or a hoop of the place, a band thin across the plane it stands in) is
the shell's too, laid by the scene record at each plan item tied to it as a builders' `arch` at the row's size
(scene_record.writer `arch_entry`; the owner, 2026-10-26, lets the framework build structure pieces as the earth seed
builds shells; Batch 1's retry: the tube's ribs, its box the whole picture, framed no close-up).
"""
import json
import pathlib
import re

import numpy as np

from score.stages.scene_record import plan as place_plan
import score.stages.surfaces.palette_library as palette_library  # the module alone in the key, not the surface line

# The scene record's backing shell (scene_record.writer BACKING, DECK_BELOW; held equal by the test): the shell stands
# this far behind the plan's inside line and the deck this far under the floor. Both take each part's surface from the
# scene's library (PART_KINDS).
BACKING = 0.15
DECK_BELOW = 0.042
SLAB = 0.2  # metres of a deck, level or roof slab
THICK = 0.3  # metres of a wall the plan gives no thickness
STOREY = 3.0  # metres of a wall neither the plan nor its words give a height
DOOR_HEAD = 2.1  # metres of a door's head the plan gives none
ON_WALL = 0.3  # metres an opening may stand off its wall's line past the wall's thickness and still be cut in it
LEVEL_OFF = 0.05  # metres a level stands off the ground before it is drawn as a level of its own
CEILING = re.compile(r"\bceiling[^0-9;,]*?(\d+(?:\.\d+)?) ?m\b")
DOOR_SIZE = re.compile(r"\d+(?:\.\d+)? ?x ?(\d+(?:\.\d+)?) ?m")  # a data door's words "(0.9 x 2.0 m)": its height
ROOT = "Shell"
# The kinds of an arched structure row (`arched`), by a word of its name or noun, a plural's s dropped.
ARCHED = frozenset(("rib", "arch", "hoop"))
# An arched row is a band: its deep under this share of its wide and of its tall.
BAND_SHARE = 0.25
# The scene library's kinds each part takes its surface from, the first it names a variant for: one answer with the
# paint's (palette_library.SHELL_KINDS), so a prop's finish can take the shell's own surface.
PART_KINDS = palette_library.SHELL_KINDS


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
    """A gable roof over an outline's box, its ridge along the longer side: a closed solid,
    its slopes, its gable ends and its underside on the eave, every face turned outward."""
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    west, east, north, south = min(xs), max(xs), min(ys), max(ys)
    corners = [[west, eave, north], [east, eave, north], [east, eave, south], [west, eave, south]]
    if east - west >= south - north:
        middle = (north + south) / 2
        ridge = [[west, top, middle], [east, top, middle]]
        inward = [[corners[0], corners[1], ridge[1]], [corners[0], ridge[1], ridge[0]],
                  [corners[2], corners[3], ridge[0]], [corners[2], ridge[0], ridge[1]],
                  [corners[3], corners[0], ridge[0]], [corners[1], corners[2], ridge[1]]]
    else:
        middle = (west + east) / 2
        ridge = [[middle, top, north], [middle, top, south]]
        inward = [[corners[1], corners[2], ridge[1]], [corners[1], ridge[1], ridge[0]],
                  [corners[3], corners[0], ridge[0]], [corners[3], ridge[0], ridge[1]],
                  [corners[0], corners[1], ridge[0]], [corners[2], corners[3], ridge[1]]]
    box = [[west, north], [east, north], [east, south], [west, south]]
    return [[one, three, two] for one, two, three in inward + cap(box, eave, True)]


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
        parts = []
        for begin, finish, bottom, top in spans(length, cuts, -DECK_BELOW - SLAB, high):
            near = [inner[index] if begin <= 1e-9 else start + along * begin + normals[index] * BACKING,
                    inner[after] if finish >= length - 1e-9 else start + along * finish + normals[index] * BACKING]
            far = [outer[index] if begin <= 1e-9 else near[0] + normals[index] * thick[index],
                   outer[after] if finish >= length - 1e-9 else near[1] + normals[index] * thick[index]]
            parts.append(slab_piece([list(near[0]), list(near[1]), list(far[1]), list(far[0])], bottom, top))
        said = (f"the plan's wall {index + 1} from {outline[index]} to {outline[after]}, {thick[index]:g} m thick "
                f"{BACKING:g} m behind its inside line, {high:g} m high" +
                (f", {len(cuts)} openings cut" if cuts else ""))
        found.append((f"wall_{index + 1}", parts, said))
    return found


# --- the shell -----------------------------------------------------------------------------------------------------

def slab_piece(points, low, high):
    """A solid of an outline (plan metres) from `low` to `high`, in the numbers tools/usd/builders' `slab` takes."""
    return {"builder": "slab", "points": [[float(x), float(y)] for x, y in points], "low": float(low),
            "high": float(high)}


def decks(plan, outline):
    """[(name, pieces, from)] of each level's slab (else the outline's at the floor)."""
    levels = [level for level in plan.get("levels") or [] if len(level.get("points") or []) >= 3] or \
        [{"name": "floor", "height": 0.0, "points": outline}]
    found = []
    for number, level in enumerate(levels, 1):
        points = grown(outline_of({"outline": level["points"]}))
        top = float(level["height"]) - DECK_BELOW
        found.append((f"deck_{number}", [slab_piece(points, top - SLAB, top)],
                      f"the plan's level {level.get('name', number)!r} at {float(level['height']):g} m: its deck "
                      f"{SLAB:g} m thick, {DECK_BELOW:g} m under it, out to the walls {BACKING:g} m behind its line"))
    return found


def roofs(plan, outline, high):
    """[(name, pieces, from)] of each written roof (module docstring), else a flat one on the walls' `high`."""
    written = [entry for entry in plan.get("roofs") or [] if len(entry.get("points") or []) >= 3]
    if not written:
        return [("roof_1", [slab_piece(grown(outline), high, high + SLAB)],
                 f"no written roof: flat on the walls' {high:g} m")]
    found = []
    for number, entry in enumerate(written, 1):
        points, eave = grown(outline_of({"outline": entry["points"]})), float(entry["eave"])
        top = float(entry.get("top") or eave)
        rising = top > eave + 1e-6
        piece = {"builder": "gable", "points": [[float(x), float(y)] for x, y in points], "eave": eave, "top": top} \
            if rising else slab_piece(points, eave, eave + SLAB)
        found.append((f"roof_{number}", [piece],
                      f"the plan's {entry.get('kind', 'flat')} roof, eave {eave:g} m" +
                      (f", top {top:g} m: a gable along its box's longer side" if rising else
                       f": a slab {SLAB:g} m thick on it")))
    return found


def lowest_eave(plan):
    """The lowest eave of the plan's written roofs, else None."""
    eaves = [float(entry["eave"]) for entry in plan.get("roofs") or [] if "eave" in entry]
    return min(eaves) if eaves else None


def laid_for(plan):
    """Whether the earth seed lays the plan's room shell (module docstring, `room`): a `kit` shell inside, or, its
    inside not said, one that writes walls. The scene record lays every other enclosed place's (scene_record.writer)."""
    inside = plan.get("inside")
    return plan.get("shell") == "kit" and (bool(inside) if inside is not None else bool(plan.get("walls")))


def encloses(plan):
    """Whether the plan encloses its place: walls or roofs drawn, and no ground of its own (terrain spots), as the scene
    record reads it (scene_record.writer `inside`, held equal by the test), which then lays its shell."""
    return bool(plan.get("walls") or plan.get("roofs")) and not (plan.get("terrain") or {}).get("spots")


def pieces(plan):
    """[(name, pieces, what it was made from)] of the plan's room shell, each piece a builder's numbers in plan metres
    (points [[x, y]]): a `slab` (points, low, high) or a `gable` (points, eave, top), as tools/usd/builders takes them
    once stood in the place's frame (the scene record's shell entries, scene_record.writer)."""
    outline = outline_of(plan)
    eave = lowest_eave(plan)
    found = decks(plan, outline) + walls(plan, outline, eave)
    high = eave if eave is not None else (measured_ceiling(plan) or STOREY)
    return found + roofs(plan, outline, high)


def solid(piece):
    """A piece's triangles [[[x, up, y] x 3]] in plan metres."""
    if piece["builder"] == "gable":
        return gable(piece["points"], piece["eave"], piece["top"])
    return prism(piece["points"], piece["low"], piece["high"])


def room(plan):
    """[(name, triangles, from)] of a room's deck, walls and roof, each its pieces' solids."""
    return [(name, [triangle for piece in parts for triangle in solid(piece)], said)
            for name, parts, said in pieces(plan)]


def levels(plan):
    """[(name, triangles, from)] of an open place's raised levels (module docstring, `level`)."""
    found = []
    for number, level in enumerate(plan.get("levels") or [], 1):
        height = float(level.get("height") or 0.0)
        if len(level.get("points") or []) < 3 or abs(height) <= LEVEL_OFF:
            continue
        points = outline_of({"outline": level["points"]})
        standing = 0.0 < height <= STOREY
        found.append((f"level_{number}", prism(points, 0.0 if standing else height - SLAB, height),
                      f"the plan's level {level.get('name', number)!r} at {height:g} m: " +
                      ("solid from the ground (a raised deck)" if standing else
                       f"a slab {SLAB:g} m thick under it")))
    return found


def shell(plan):
    """[(name, triangles [[[x, up, y] x 3]] in plan metres, what it was made from)] of what the earth seed lays (module
    docstring): a room's deck, walls and roof, else an open place's raised levels; nothing for a place the scene
    record encloses."""
    if laid_for(plan):
        return room(plan)
    return [] if encloses(plan) else levels(plan)


def arched(row):
    """Whether an inventory row is arched structure the shell lays (module docstring): a structure part, named a
    rib, arch or hoop, its size a band (its deep under BAND_SHARE of its wide and of its tall)."""
    words = {word.removesuffix("s") for word in re.findall(r"[a-z]+", f"{row.get('name')} {row.get('noun')}".lower())}
    size = row.get("size") or []
    return (row.get("part") == "structure" and bool(words & ARCHED) and len(size) == 3 and
            all(isinstance(side, (int, float)) and side > 0 for side in size) and
            size[1] < BAND_SHARE * min(size[0], size[2]))


def arches(plan, rows):
    """[(row, plan item, its shape)] of every plan item tied to an arched row of `rows` (inventory rows)."""
    by_id = {row["id"]: row for row in rows if arched(row)}
    tied, shapes = plan.get("rows") or {}, plan.get("shapes") or {}
    return [(by_id[row_id], item, shapes.get(item[0]) or {}) for item in plan.get("items") or []
            if len(item) <= 6 or item[6] == "item" for row_id in tied.get(item[0]) or [] if row_id in by_id]


def part_kind(name):
    """A part's kind from its name (`wall_3`: wall)."""
    return name.rsplit("_", 1)[0]


# --- the scene's surfaces -----------------------------------------------------------------------------------------

def library_of(path):
    """The scene's surface library (its materials.json at `path`), else None: not made yet."""
    return json.loads(pathlib.Path(path).read_text()) if path is not None and pathlib.Path(path).is_file() else None


def surface_for(kind, library):
    """The variant the scene library gives a part of `kind` (the first of its PART_KINDS it names one for), else
    None."""
    return palette_library.shell_surface(kind, library)


def missing_why(place, kind, library):
    """Why a part of `kind` has no surface: the scene's library is not made, or names none of its kinds."""
    if library is None:
        return f"{place}: the scene's surface library is not made (run surface-library first): its {kind} has none"
    return (f"{place}: the scene's surface library names no surface for the kinds a {kind} takes "
            f"({', '.join(PART_KINDS[kind])})")


# --- laying ---------------------------------------------------------------------------------------------------------

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
    return {"points": points, "triangles": np.arange(len(points)).reshape(-1, 3), "uvs": uvs}


def footprint(plan):
    """The plan's box in the place's frame: [[least x, least z], [most x, most z]] of its outline stood there."""
    points = placed([up(outline_of(plan), 0.0)], plan)[:, [0, 2]]
    return [np.round(points.min(axis=0), 4).tolist(), np.round(points.max(axis=0), 4).tolist()]


def paint(stage, prim, place, kind, library, scene):
    """A part bound to its scene library surface (laid under /<place>/Library), else named missing on it."""
    from pxr import Sdf
    surface = surface_for(kind, library)
    if surface is None:
        prim.GetPrim().CreateAttribute("score:surface:missing", Sdf.ValueTypeNames.String).Set(
            missing_why(place, kind, library))
        return
    scene.bind_surface(stage, prim, place, surface)


def lay(layer_path, place, plan, tools, library_path=None):
    """The plan's shell under /<place>/Shell in the base layer at `layer_path`, each part a static collider painted
    with its scene library surface (tools: tools/usd/export.py's module, for its scene writer, library materials and
    colliders; library_path: the scene's materials.json, else None); the parts' names."""
    from pxr import Sdf, Usd, UsdGeom
    stage = Usd.Stage.Open(Sdf.Layer.FindOrOpen(str(layer_path)))
    library = library_of(library_path)
    if library is not None:
        tools.library_materials(stage, place, f"/{place}", specs=tools.library.library_specs(library_path))
    scene, names = tools.scene_record, []
    for name, triangles, said in shell(plan):
        if not triangles:
            continue
        UsdGeom.Scope.Define(stage, f"/{place}/{ROOT}")
        mesh = built(triangles, plan)
        prim = scene.mesh_prim(stage, f"/{place}/{ROOT}/{name}", mesh)
        paint(stage, prim, place, part_kind(name), library, scene)
        tools.colliders.solid(prim.GetPrim(), mesh["points"], mesh["triangles"])
        for key, value in (("score:kind", "structure"), ("score:plain", "shell"), ("score:from", said)):
            prim.GetPrim().CreateAttribute(key, Sdf.ValueTypeNames.String).Set(value)
        names.append(name)
    stage.GetRootLayer().Save()
    return names
