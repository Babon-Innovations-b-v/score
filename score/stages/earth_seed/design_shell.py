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
           the level, out to the walls' room faces (to_walls), cut open over each flight the plan draws
           going down from it (`hatches`: a floor hatch with its stairs)
    wall   (a room) round the outline (the plan's `outline`, else its box w x d), each edge a slab of its written wall's
           thickness on that wall's line (edge_wall, face_reach: the plan draws its outline round its walls' outer
           faces and each wall on its middle line, as holders lays a wall thing on its face; 2026-11-07: storage's
           walls stood 0.31 m behind the faces its wall lights were laid on), an edge with no written wall a slab
           THICK thick standing BACKING behind the outline, from the deck's foot to its written
           height (else the height words' ceiling, else STOREY), raised to a roof's eave over it; and every written wall
           the outline does not stand on (an inner wall, an arc in ARC_STEP pieces) centred on its line, as thick and
           high; each opening on a wall (a door, window, gate or opening: a written plan's `openings`, else a data
           plan's `doors`) cut from its sill to its head
    roof   (a room) each written roof over its points out to the walls' room faces (to_walls): a flat one a slab on
           its eave; a dome a sphere's cap over the circle round its box's middle (builders' `dome`), so the people
           the concept stands under it fit (the greenhouse's upper walk, Batch 1 of 2026-10-27); a vault a circle's
           arc from its eave to its top across its box, along the box's longer side, a square box's between the ends
           its openings stand on (`vault_way`; builders' `tube_arc`), so the people under it fit (the tube's,
           round 33 of 2026-10-30); one rising otherwise (shed, pitched) a closed gable along its box's longer side;
           no written roof, a flat one on the walls' height; a flat one with `openings` (each a footprint of points:
           a hatch, the hangar's roof door) is the slab round them (cut_out), open over each
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

    pieces of rows (`row_pieces`, laid by the scene record like the arches; 2026-11-05: the hangar's landing pad,
           wall pillars and floor grates and the garage's ceiling beams were built by nothing) a structure row the
           shell builds from the plan and its walls: an upright one (a pillar, column or post) its count spaced evenly
           round the outline's walls, its back on each wall's inside face, clear of corners and openings (`pillars`);
           a spanning one (a beam, girder, rafter, truss or joist) across the outline's shorter side wall face to wall
           face, spaced along the longer, its top at the roof's eave (`beams`); a floor row tied to plan items of its
           own (a pad, a grate) a slab at each, its count shared over them, at least FLUSH thick (`floor_pieces`)
"""
import hashlib
import json
import pathlib
import re

import numpy as np

from score.stages.scene_record import plan as place_plan
import score.stages.surfaces.palette_library as palette_library  # the module alone in the key, not the surface line
from score.stages.shell_parts import LEVEL_OFF, encloses, laid_for, part_kind, raised  # noqa: F401
from score.store import PROPS_HOME

KEPT_RELATIONS = PROPS_HOME / "design" / "relations"  # holders.KEPT, held equal by the scene record's test

# The scene record's backing shell (scene_record.writer BACKING, DECK_BELOW; held equal by the test): a wall the plan
# does not write stands this far behind its outline's edge and the deck's top this far under the floor: none, the deck
# is the floor
# (the retired kits laid 0.04 m floor plates on it; with none, every thing laid at the floor stood 0.042 m over it).
# Both take each part's surface from the scene's library (PART_KINDS).
BACKING = 0.15
DECK_BELOW = 0.0
SLAB = 0.2  # metres of a deck, level or roof slab
THICK = 0.3  # metres of a wall the plan gives no thickness
STOREY = 3.0  # metres of a wall neither the plan nor its words give a height
DOOR_HEAD = 2.1  # metres of a door's head the plan gives none
ON_WALL = 0.3  # metres an opening may stand off its wall's line past the wall's thickness and still be cut in it
VAULT_TIE = 0.05  # share two sides of a vault's box may differ by and still be equal (vault_way)
ARC_STEP = 15.0  # degrees of a written arc wall each straight piece of it spans
# A written wall runs along the outline (on_outline) where every point of it stands within OUTLINE_REACH metres of an
# outline edge turned within ALONG_TURN degrees of it: a round wall drawn round a polygon outline.
OUTLINE_REACH, ALONG_TURN = 1.0, 45.0
COVERS = 0.5  # share of an outline edge a written straight wall along it covers to be the edge's wall (written_wall)
CEILING = re.compile(r"\bceiling[^0-9;,]*?(\d+(?:\.\d+)?) ?m\b")
DOOR_SIZE = re.compile(r"\d+(?:\.\d+)? ?x ?(\d+(?:\.\d+)?) ?m")  # a data door's words "(0.9 x 2.0 m)": its height
ROOT = "Shell"
# The kinds of an arched structure row (`arched`), by a word of its name or noun, a plural's s dropped.
ARCHED = frozenset(("rib", "arch", "hoop"))
# The kinds of a row filling an opening of its wall (fills_opening).
OPENING_KINDS = frozenset(("door", "window", "gate", "hatch", "shutter"))
# An arched row is a band: its deep under this share of its wide and of its tall.
BAND_SHARE = 0.25
# The kinds of a structure row the shell stands along its walls (pillars) and spans under its roof (beams), by a word
# of its id, name or noun, a plural's s dropped (row_pieces).
UPRIGHT = frozenset(("pillar", "column", "post"))
SPANNING = frozenset(("beam", "girder", "rafter", "truss", "joist"))
FLUSH = 0.02  # metres a floor piece the plan gives no height stands over the floor (a grate laid in it)
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


def vault_way(points, openings):
    """Whether a vault over an outline's box runs east (True) or south (False): along the box's longer side; where
    its sides are within VAULT_TIE of each other, between the ends its plan's openings stand on, a tube running from
    door to door (2026-11-02: the tube's 10.04 m square box ran its vault east, across its length, so its arc came
    down to 1.3 m at its doorways and spot-1's eye stood over the roof, its picture the roof's outer skin); east
    where no opening tells."""
    xs, ys = [float(point[0]) for point in points], [float(point[1]) for point in points]
    west, east, north, south = min(xs), max(xs), min(ys), max(ys)
    if abs((east - west) - (south - north)) > VAULT_TIE * max(east - west, south - north):
        return east - west > south - north
    reach = ON_WALL + BACKING
    ends = sum(min(abs(opening["at"][0] - west), abs(opening["at"][0] - east)) <= reach for opening in openings)
    sides = sum(min(abs(opening["at"][1] - north), abs(opening["at"][1] - south)) <= reach for opening in openings)
    return ends >= sides


def vault_arc(points, eave, top, lengthwise=None):
    """A vault over an outline's box as tools/usd/builders' `tube_arc` draws it: the circle's `radius`, its axis'
    height (`axis_high`), the arc's half angle (degrees from straight up), and its run: `start` the middle of its
    west or north end, `along` its unit way ([1, 0] east, [0, 1] south) east when `lengthwise` (vault_way's), else
    south (None: along the box's longer side), `length` that side."""
    xs, ys = [float(point[0]) for point in points], [float(point[1]) for point in points]
    west, east, north, south = min(xs), max(xs), min(ys), max(ys)
    lengthwise = east - west >= south - north if lengthwise is None else lengthwise
    half, rise = ((south - north) if lengthwise else (east - west)) / 2, top - eave
    radius = (half ** 2 + rise ** 2) / (2 * rise)
    start = [west, (north + south) / 2] if lengthwise else [(west + east) / 2, north]
    return {"radius": radius, "axis_high": top - radius, "half": float(np.degrees(np.arctan2(half, radius - rise))),
            "start": start, "along": [1.0, 0.0] if lengthwise else [0.0, 1.0],
            "length": (east - west) if lengthwise else (south - north)}


def vault(points, eave, top, lengthwise=None, segments=24):
    """A vault's arc (vault_arc) in plan metres [x, up, y], the triangles tools/usd/builders' `tube_arc` draws."""
    arc = vault_arc(points, eave, top, lengthwise)
    along = np.array([arc["along"][0], 0.0, arc["along"][1]])
    across = np.array([arc["along"][1], 0.0, -arc["along"][0]])
    start = np.array([arc["start"][0], 0.0, arc["start"][1]])
    angles = np.radians(np.linspace(-arc["half"], arc["half"], segments + 1))
    rows = [[start + across * arc["radius"] * np.sin(angle) + along * run
             + [0.0, arc["axis_high"] + arc["radius"] * np.cos(angle), 0.0] for run in (0.0, arc["length"])]
            for angle in angles]
    return [triangle for one, two in zip(rows, rows[1:])
            for triangle in ([one[0], one[1], two[0]], [one[1], two[1], two[0]])]


def dome(centre, radius, base, rise, rings=12, segments=48):
    """A dome's cap as tools/usd/builders' `dome` draws it, in plan metres [x, up, y]: a sphere's cap over a circle of
    `radius` round `centre` from `base` up `rise`."""
    sphere = (radius ** 2 + rise ** 2) / (2 * rise)
    lowest = np.arcsin(min(1.0, radius / sphere))
    rows = [[[centre[0] + sphere * np.sin(polar) * np.sin(azimuth), base + sphere * np.cos(polar) - (sphere - rise),
              centre[1] - sphere * np.sin(polar) * np.cos(azimuth)]
             for azimuth in np.linspace(0.0, 2 * np.pi, segments + 1)]
            for polar in lowest * (1 - np.arange(rings + 1) / rings)]
    return [triangle for ring in range(rings) for segment in range(segments)
            for triangle in ([rows[ring][segment], rows[ring + 1][segment], rows[ring][segment + 1]],
                             [rows[ring][segment + 1], rows[ring + 1][segment], rows[ring + 1][segment + 1]])]


# --- walls -------------------------------------------------------------------------------------------------------

def measured_ceiling(plan):
    """The ceiling the plan's height words give (the first `ceiling <n> m`), else None."""
    found = CEILING.search(str(plan.get("height") or ""))
    return float(found.group(1)) if found else None


def written_wall(plan, start, end):
    """The written straight wall (`walls`: {from, to, thick, tall}) the outline's edge from `start` to `end` stands
    for: of those running along it (along_edge), the one covering most of it, the nearest its line of those
    covering as much, when it covers at least COVERS of it (camp's dome wall along 9% of its site's edge is the
    dome's); else {}. The plan draws its outline round its walls' outer faces and each wall on its middle
    line, so a wall stands inside its edge by half its thickness (storage's 0.168 m walls 0.08 m in from its outline),
    and on it where the plan draws a wall as its edge."""
    covers = [(round(along_edge(entry, start, end), 3), -abs(face_reach(entry, start, end)), number)
              for number, entry in enumerate(plan.get("walls") or [])
              if isinstance(entry, dict) and "from" in entry and "to" in entry]
    covered, _, number = max(covers, default=(0.0, 0.0, None))
    return plan["walls"][number] if covered >= COVERS * float(np.linalg.norm(np.subtract(end, start))) - 1e-3 and \
        covered > 1e-6 else {}


def along_edge(entry, start, end):
    """Metres of the edge from `start` to `end` a straight written wall covers where it runs along it (turned within
    ALONG_TURN of it, its ends within its thickness and ON_WALL of the edge's line, as an opening is on it: on_edge),
    else 0. A wall further in is another part's (airlock's room wall 0.75 m in from its porch's edge)."""
    start, end = np.asarray(start, float), np.asarray(end, float)
    first, second = np.asarray(entry["from"], float), np.asarray(entry["to"], float)
    length, run = float(np.linalg.norm(end - start)), second - first
    if length < 1e-6 or float(np.linalg.norm(run)) < 1e-6:
        return 0.0
    way = (end - start) / length
    if abs(float(way @ run)) < np.cos(np.radians(ALONG_TURN)) * float(np.linalg.norm(run)):
        return 0.0
    normal = outward(start, end)
    if max(abs(float((point - start) @ normal)) for point in (first, second)) > float(entry.get("thick") or THICK) + \
            ON_WALL:
        return 0.0
    low, high = sorted(float((point - start) @ way) for point in (first, second))
    return max(0.0, min(high, length) - max(low, 0.0))


def face_reach(entry, start, end):
    """Metres out from the outline's edge (`start` to `end`) to the room face of the wall built on it: its written
    wall's (`entry`, written_wall) middle line, out along the edge's outward normal, less half its thickness; with
    none, BACKING."""
    if not entry:
        return BACKING
    normal, start = outward(start, end), np.asarray(start, float)
    middle = (np.asarray(entry["from"], float) + np.asarray(entry["to"], float)) / 2
    return float((middle - start) @ normal) - float(entry.get("thick") or THICK) / 2


def openings_of(plan):
    """Every opening of the plan as {at [x, y], wide, sill, head}: a written plan's `openings`, else a data plan's
    `doors`; and the openings its door and window rows fill (`row_openings`, cut_for)."""
    return plan_openings(plan) + list(plan.get("row_openings") or [])


def plan_openings(plan):
    """The plan's own openings as {at [x, y], wide, sill, head}: a written plan's `openings`, else a data plan's
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


def fills_opening(row):
    """Whether an inventory row fills an opening of its wall (a door, window, gate, hatch or shutter by a word of its
    id, name or noun, a plural's s dropped), its size a panel (its deep under BAND_SHARE of its wide and its tall)."""
    words = {word.removesuffix("s") for word in
             re.findall(r"[a-z]+", f"{row.get('id')} {row.get('name')} {row.get('noun')}".replace("_", " ").lower())}
    size = row.get("size") or []
    return (bool(words & OPENING_KINDS) and len(size) == 3 and
            all(isinstance(side, (int, float)) and side > 0 for side in size) and
            size[1] < BAND_SHARE * min(size[0], size[2]))


def row_openings(plan, rows):
    """The opening each plan item of a row filling one (fills_opening) cuts: at the item's middle (walls cut only an
    opening standing on them, on_edge), the row's wide, from its shape's base to its top (its shape's tall, else the
    row's); none where one of the plan's own openings already stands within their half widths (2026-10-26: Batch 1's
    doors and windows stood at items the plan's openings missed, against uncut walls)."""
    by_id = {row["id"]: row for row in rows if fills_opening(row)}
    tied, shapes, own = plan.get("rows") or {}, plan.get("shapes") or {}, plan_openings(plan)
    found = []
    for item in plan.get("items") or []:
        for row_id in [row_id for row_id in tied.get(item[0]) or [] if row_id in by_id]:
            row, shape = by_id[row_id], shapes.get(item[0]) or {}
            at = [float(item[1]) + float(item[3]) / 2, float(item[2]) + float(item[4]) / 2]
            wide, base = float(row["size"][0]), float(shape.get("base") or 0.0)
            if any(np.linalg.norm(np.subtract(at, other["at"])) < (wide + other["wide"]) / 2 for other in own):
                continue
            found.append({"at": at, "wide": wide, "sill": base,
                          "head": base + float(shape.get("tall") or row["size"][2]), "row": row_id})
    return found


def relation_cuts(relations):
    """The openings the place's relations cut for doors and windows the plan's own openings do not hold
    (score/review/holders `cut`), as {at, wide, sill, head}."""
    return [{key: found["opening"][key] for key in ("at", "wide", "sill", "head")}
            for entry in (relations or {}).get("relations", []) for found in entry.get("pieces") or [entry]
            if (found.get("opening") or {}).get("cut")]


def cut_for(plan, rows, relations=None):
    """The plan with the openings its door and window rows fill (row_openings) and those its relations cut
    (relation_cuts, each but where one a wall cuts stands within their half widths, which it replaces where none of
    its outline's walls cuts it: cockpit's rear door, its item's middle 0.75 m off its slanted wall's line, left the
    wall uncut and its door swung into it, #36 2026-10-30) for its walls to cut."""
    own = row_openings(plan, rows)
    for cut in relation_cuts(relations):
        near = [other for other in own
                if np.linalg.norm(np.subtract(cut["at"], other["at"])) < (cut["wide"] + other["wide"]) / 2]
        kept = [other for other in near if on_a_wall(plan, other)]
        if not kept:
            own = [other for other in own if all(other is not found for found in near)] + [cut]
    return {**plan, "row_openings": own}


def on_a_wall(plan, opening):
    """Whether a wall the shell builds (wall_lines: the outline's and the inner ones) cuts the opening (on_edge, at its
    thickness)."""
    return any(on_edge([opening], start, end, thick) for _, start, end, thick, *_ in wall_lines(plan))


def arc_points(arc):
    """The points [[x, y]] along a written arc ({centre, radius, start, end}: degrees from x toward y, run from start
    up to end), one each ARC_STEP or less."""
    start, end = float(arc["start"]), float(arc["end"])
    end += 360.0 if end <= start else 0.0
    turns = np.radians(np.linspace(start, end, max(1, int(np.ceil((end - start) / ARC_STEP))) + 1))
    centre, radius = np.asarray(arc["centre"], float), float(arc["radius"])
    return [list(centre + radius * np.array([np.cos(turn), np.sin(turn)])) for turn in turns]


def written_lines(entry):
    """[(start, end)] of a written wall: its line from `from` to `to`, an arc's straight pieces (arc_points)."""
    if "from" in entry and "to" in entry:
        return [(list(map(float, entry["from"])), list(map(float, entry["to"])))]
    points = arc_points(entry["arc"]) if "arc" in entry else []
    return list(zip(points, points[1:]))


def off_line(point, start, end):
    """Metres from a point to the segment from `start` to `end`."""
    point, start, end = (np.asarray(each, float) for each in (point, start, end))
    run = end - start
    share = float(np.clip((point - start) @ run / max(float(run @ run), 1e-12), 0.0, 1.0))
    return float(np.linalg.norm(start + run * share - point))


def on_outline(entry, outline):
    """Whether a written wall runs along the outline, so the outline's wall is that wall: every point along it (each
    piece's ends, quarters and middle) within OUTLINE_REACH of an outline edge that runs its way (within ALONG_TURN).
    The greenhouse's round walls stand up to 0.76 m inside its eight-sided outline; the lab's entry passage walls, 0.79
    m from its outline, run across it."""
    corners = [np.asarray(point, float) for point in outline]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    edges = [(start, end) for start, end in edges if np.linalg.norm(end - start) >= 1e-6]

    def along(start, end, point):
        run = (end - start) / float(np.linalg.norm(end - start))
        return any(off_line(point, *edge) <= OUTLINE_REACH and abs(float(run @ (edge[1] - edge[0])))
                   >= np.cos(np.radians(ALONG_TURN)) * float(np.linalg.norm(edge[1] - edge[0])) for edge in edges)
    return all(along(start, end, start + (end - start) * share)
               for start, end in (tuple(np.asarray(each, float) for each in line) for line in written_lines(entry))
               for share in np.linspace(0.0, 1.0, 5))


def inner_walls(plan):
    """[(start, end, written wall)] of every written wall the outline does not stand on (on_outline), an arc as its
    straight pieces and those across its gap round each opening there (gap_lines): the shell builds them too, centred
    on their line (only an outline wall knows an outside)."""
    outline, openings = outline_of(plan), openings_of(plan)
    return [(start, end, entry) for entry in plan.get("walls") or [] if isinstance(entry, dict)
            and not on_outline(entry, outline) for start, end in written_lines(entry) + gap_lines(entry, openings)
            if np.linalg.norm(np.subtract(end, start)) >= 1e-6]


def gap_lines(entry, openings):
    """[(start, end)] of an arc wall's straight pieces across the part of its gap each opening on its circle (within
    its thickness and ON_WALL of it) stands in, as wide as the opening: the plan draws a dome's door in its wall's gap
    (camp's airlock door, where its entry tube meets the dome), and a door needs its wall built round it."""
    arc = entry.get("arc")
    if not arc:
        return []
    start, end = float(arc["start"]), float(arc["end"])
    end += 360.0 if end <= start else 0.0
    centre, radius = np.asarray(arc["centre"], float), float(arc["radius"])
    reach = float(entry.get("thick") or THICK) + ON_WALL
    found = []
    for opening in openings:
        off = np.asarray(opening["at"], float) - centre
        if abs(float(np.linalg.norm(off)) - radius) > reach:
            continue
        turn = float(np.degrees(np.arctan2(off[1], off[0]))) % 360.0
        turn += 360.0 if turn < start else 0.0
        half = float(np.degrees(np.arcsin(min(1.0, float(opening["wide"]) / 2 / radius))))
        low, high = max(end, turn - half), min(start + 360.0, turn + half)
        if turn > end and high > low:
            points = arc_points({**arc, "start": low, "end": high})
            found += list(zip(points, points[1:]))
    return found


def wall_lines(plan):
    """[(name, start, end, thick, written wall, inner)] of every wall the shell builds (walls): the outline's edges
    `wall_1` on, then its inner walls (inner_walls, `inner` true)."""
    outline = outline_of(plan)
    found = []
    for index, start in enumerate(outline):
        end = outline[(index + 1) % len(outline)]
        entry = written_wall(plan, start, end)
        if np.linalg.norm(np.subtract(end, start)) >= 1e-6:
            found.append((f"wall_{index + 1}", start, end, float(entry.get("thick") or THICK), entry, False))
    found += [(f"wall_{number}", start, end, float(entry.get("thick") or THICK), entry, True)
              for number, (start, end, entry) in enumerate(inner_walls(plan), len(outline) + 1)]
    return found


def relations_file(place):
    """{"relations": its kept path pattern} once the place's relations are derived (score/review/holders keep), else
    {}: its things are laid, and its walls cut, as the plan draws them."""
    return {"relations": "{home}/design/relations/" + f"{place}.json"} if (KEPT_RELATIONS / f"{place}.json").is_file() \
        else {}


def relations_read(inputs, plan_path):
    """(the place's relations, None) while they were derived from its kept plan as it stands (their `plan` sha), else
    (None, why they are left out): a plan kept since is laid as it is drawn until the next keep derives them again."""
    if "relations" not in inputs:
        return None, None
    relations = json.loads(pathlib.Path(inputs["relations"]).read_text())
    if relations.get("plan") != hashlib.sha256(pathlib.Path(plan_path).read_text().encode()).hexdigest():
        return None, "the relations were derived from another plan than the kept one (score/review/holders keep)"
    return relations, None


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


def grown(points, reaches):
    """An outline (clockwise on a map) with each edge pushed out by its reach (`reaches`, one an edge), its corners
    mitred."""
    count = len(points)
    normals = [outward(points[index], points[(index + 1) % count]) for index in range(count)]
    return [list(offset_corner(points[index], normals[index - 1], normals[index], reaches[index - 1], reaches[index]))
            for index in range(count)]


def to_walls(plan, points):
    """An outline (a level's, a roof's; clockwise on a map) grown out to the walls (grown): each edge lying along an
    edge of the plan's outline, between that edge and ON_WALL past its wall's room face (face_reach), out to that
    face; any other BACKING out, as a wall the plan does not write stands."""
    outline = outline_of(plan)
    edges = [(outline[index], outline[(index + 1) % len(outline)]) for index in range(len(outline))]
    faces = [face_reach(written_wall(plan, start, end), start, end) for start, end in edges]
    reaches = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        reach, middle, normal = BACKING, (np.asarray(start, float) + np.asarray(end, float)) / 2, outward(start, end)
        for (first, second), face in zip(edges, faces):
            if np.linalg.norm(np.subtract(second, first)) < 1e-6 or float(normal @ outward(first, second)) < \
                    np.cos(np.radians(ALONG_TURN)):
                continue
            out = float((middle - np.asarray(first, float)) @ outward(first, second))
            way = (np.asarray(second, float) - np.asarray(first, float))
            share = float((middle - np.asarray(first, float)) @ way) / float(way @ way)
            if 0.0 <= share <= 1.0 and min(face, 0.0) - ON_WALL <= out <= BACKING:
                reach = face - out
                break
        reaches.append(reach)
    return grown(points, reaches)


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


def inner_spans(length, cuts, high):
    """An inner wall's spans (spans), less any of no length: the lab's entry passage end walls are as long as their
    doors' openings, which leave no piece beside them."""
    return [span for span in spans(length, cuts, -DECK_BELOW - SLAB, high) if span[1] - span[0] > 1e-6]


def wall_height(plan, entry, roof_eave):
    """A wall's top: its written height, else the words' ceiling, else STOREY; raised to the roof's eave over it."""
    tall = float(entry.get("tall") or measured_ceiling(plan) or STOREY)
    return max(tall, roof_eave or 0.0)


def walls(plan, outline, roof_eave):
    """[(name, triangles, from)] of the outline's walls (module docstring), each edge's pieces round its openings, then
    the plan's inner walls (inner_pieces)."""
    count, openings = len(outline), openings_of(plan)
    entries = [written_wall(plan, outline[index], outline[(index + 1) % count]) for index in range(count)]
    thick = [float(entry.get("thick") or THICK) for entry in entries]
    reach = [face_reach(entries[index], outline[index], outline[(index + 1) % count]) for index in range(count)]
    normals = [outward(outline[index], outline[(index + 1) % count]) for index in range(count)]
    inner = [offset_corner(outline[index], normals[index - 1], normals[index], reach[index - 1], reach[index])
             for index in range(count)]
    outer = [offset_corner(outline[index], normals[index - 1], normals[index], reach[index - 1] + thick[index - 1],
                           reach[index] + thick[index]) for index in range(count)]
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
            near = [inner[index] if begin <= 1e-9 else start + along * begin + normals[index] * reach[index],
                    inner[after] if finish >= length - 1e-9 else start + along * finish + normals[index] * reach[index]]
            far = [outer[index] if begin <= 1e-9 else near[0] + normals[index] * thick[index],
                   outer[after] if finish >= length - 1e-9 else near[1] + normals[index] * thick[index]]
            parts.append(slab_piece([list(near[0]), list(near[1]), list(far[1]), list(far[0])], bottom, top))
        said = (f"the plan's wall {index + 1} from {outline[index]} to {outline[after]}, {thick[index]:g} m thick, "
                f"its room face {reach[index]:.3g} m out from that line, {high:g} m high" +
                (f", {len(cuts)} openings cut" if cuts else ""))
        found.append((f"wall_{index + 1}", parts, said))
    return found + inner_pieces(plan, len(outline), openings, roof_eave)


def inner_pieces(plan, count, openings, roof_eave):
    """[(name, triangles, from)] of the plan's inner walls (inner_walls), each centred on its line, round its
    openings: the lab's doors stood in their entry passages' end walls, which the outline does not hold, so no wall
    was built at them and they hung on nothing (motion@lab, round 35)."""
    found = []
    for number, (start, end, entry) in enumerate(inner_walls(plan), count + 1):
        start, end = np.asarray(start, float), np.asarray(end, float)
        length, thick = float(np.linalg.norm(end - start)), float(entry.get("thick") or THICK)
        along, half = (end - start) / length, outward(start, end) * thick / 2
        cuts = on_edge(openings, start, end, thick)
        high = wall_height(plan, entry, roof_eave)
        parts = [slab_piece([list(start + along * begin - half), list(start + along * finish - half),
                             list(start + along * finish + half), list(start + along * begin + half)], bottom, top)
                 for begin, finish, bottom, top in inner_spans(length, cuts, high)]
        found.append((f"wall_{number}", parts,
                      f"the plan's inner wall from {[round(float(value), 3) for value in start]} to "
                      f"{[round(float(value), 3) for value in end]}, {thick:g} m thick centred on its line, "
                      f"{high:g} m high" + (f", {len(cuts)} openings cut" if cuts else "")))
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
        points = to_walls(plan, outline_of({"outline": level["points"]}))
        top = float(level["height"]) - DECK_BELOW
        holes = [box for _, box in hatches(plan, level)]
        found.append((f"deck_{number}", [slab_piece(part, top - SLAB, top) for part in
                                         (cut_out(points, holes) if holes else [points])],
                      f"the plan's level {level.get('name', number)!r} at {float(level['height']):g} m: its deck "
                      f"{SLAB:g} m thick, {DECK_BELOW:g} m under it, out to the walls' room faces" +
                      (f", {len(holes)} hatches cut over the flights going down from it" if holes else "")))
    return found


def hatches(plan, level):
    """[(stair index, (west, north, east, south))] of each stair or ramp the plan draws going down from a level: its
    top at the level's height, its foot under it, its footprint's middle on the level; the box is the hatch its deck
    is cut open over (the hangar's open floor hatch with stairs down, 2026-11-05: its flight stood inside the solid
    deck)."""
    height, outline, found = float(level.get("height") or 0.0), level.get("points") or [], []
    for index, entry in enumerate(plan.get("stairs") or []):
        corners = np.asarray(entry.get("points") or [], float).reshape(-1, 2)
        if len(corners) < 3 or not (np.ptp(corners[:, 0]) > 0 and np.ptp(corners[:, 1]) > 0):
            continue
        low, high = sorted((float(entry.get("from") or 0.0), float(entry.get("to") or 0.0)))
        middle = list((corners.min(axis=0) + corners.max(axis=0)) / 2)
        if abs(high - height) <= 1e-3 and low < height - 1e-3 and inside(middle, outline):
            found.append((index, (*corners.min(axis=0).tolist(), *corners.max(axis=0).tolist())))
    return found


def roofs(plan, outline, high):
    """[(name, pieces, from)] of each written roof (module docstring), else a flat one on the walls' `high`."""
    written = [entry for entry in plan.get("roofs") or [] if len(entry.get("points") or []) >= 3]
    if not written:
        return [("roof_1", [slab_piece(to_walls(plan, outline), high, high + SLAB)],
                 f"no written roof: flat on the walls' {high:g} m")]
    found = []
    for number, entry in enumerate(written, 1):
        points, eave = to_walls(plan, outline_of({"outline": entry["points"]})), float(entry["eave"])
        top = float(entry.get("top") or eave)
        rising = top > eave + 1e-6
        domed, vaulted = entry.get("kind") == "dome", entry.get("kind") == "vault"
        holes = roof_holes(entry)
        if not rising and holes:  # a flat roof with its openings cut: the pieces round them
            found.append((f"roof_{number}", [slab_piece(part, eave, eave + SLAB) for part in cut_out(points, holes)],
                          f"the plan's flat roof, eave {eave:g} m: a slab {SLAB:g} m thick on it, its "
                          f"{len(holes)} openings cut"))
            continue
        piece = (dome_piece(points, eave, top) if domed else
                 {"builder": "vault" if vaulted else "gable", "points": [[float(x), float(y)] for x, y in points],
                  "eave": eave, "top": top}) \
            if rising else slab_piece(points, eave, eave + SLAB)
        if piece["builder"] == "vault":
            piece["lengthwise"] = vault_way(points, plan_openings(plan))
        found.append((f"roof_{number}", [piece],
                      f"the plan's {entry.get('kind', 'flat')} roof, eave {eave:g} m" +
                      (f", top {top:g} m: " + ("a dome over the circle round it" if domed else
                                               "a circle's arc across its box, running " +
                                               ("east" if piece.get("lengthwise") else "south") if vaulted else
                                               "a gable along its box's longer side") if rising else
                       f": a slab {SLAB:g} m thick on it")))
    return found


def roof_holes(entry):
    """[(west, north, east, south)] plan metres of each opening a written roof has (its `openings`, each a footprint
    of points: a hatch, a skylight, the hangar's 27 by 55 m roof door the ship leaves by), its box."""
    found = []
    for opening in entry.get("openings") or []:
        corners = np.asarray(opening.get("points") or [], float).reshape(-1, 2)
        if len(corners) >= 3 and np.ptp(corners[:, 0]) > 0 and np.ptp(corners[:, 1]) > 0:
            found.append((*corners.min(axis=0).tolist(), *corners.max(axis=0).tolist()))
    return found


def cut_out(points, holes):
    """The outline (plan metres) less each hole's box, as outlines round them: to the west and east of a hole, and
    north and south of it between the two; each clipped to the outline, none of no area."""
    pieces = [[[float(x), float(y)] for x, y in points]]
    for west, north, east, south in holes:
        bands = ((None, None, west, None), (east, None, None, None), (west, None, east, north),
                 (west, south, east, None))
        pieces = [part for piece in pieces for band in bands
                  if len(part := clipped(piece, *band)) >= 3 and abs(signed_area(part)) > 1e-9]
    return pieces


def clipped(points, west, north, east, south):
    """An outline clipped to the box between these lines (plan metres; None: no line there), Sutherland and Hodgman's
    way, one side at a time."""
    for axis, bound, keep_low in ((0, west, False), (0, east, True), (1, north, False), (1, south, True)):
        if bound is None or not points:
            continue
        kept = []
        for index, here in enumerate(points):
            before = points[index - 1]
            within = (here[axis] <= bound) if keep_low else (here[axis] >= bound)
            was = (before[axis] <= bound) if keep_low else (before[axis] >= bound)
            if within != was:
                share = (bound - before[axis]) / (here[axis] - before[axis])
                kept.append([before[0] + share * (here[0] - before[0]), before[1] + share * (here[1] - before[1])])
            if within:
                kept.append(list(here))
        points = kept
    return points


def dome_piece(points, eave, top):
    """A dome over an outline (plan metres), in the numbers tools/usd/builders' `dome` takes: a sphere's cap from the
    eave up to the top over the circle round the outline's box middle that holds every point."""
    centre = (np.min(points, axis=0) + np.max(points, axis=0)) / 2
    radius = float(np.max(np.linalg.norm(np.asarray(points, float) - centre, axis=1)))
    return {"builder": "dome", "centre": [float(centre[0]), float(centre[1])], "radius": radius, "base": float(eave),
            "rise": float(top - eave)}


def lowest_eave(plan):
    """The lowest eave of the plan's written roofs, else None."""
    eaves = [float(entry["eave"]) for entry in plan.get("roofs") or [] if "eave" in entry]
    return min(eaves) if eaves else None


def pieces(plan):
    """[(name, pieces, what it was made from)] of the plan's room shell, each piece a builder's numbers in plan metres
    (points [[x, y]]): a `slab` (points, low, high), a `gable` or `vault` (points, eave, top) or a `dome`, as
    tools/usd/builders takes them once stood in the place's frame (the scene record's shell entries,
    scene_record.writer)."""
    outline = outline_of(plan)
    eave = lowest_eave(plan)
    found = decks(plan, outline) + walls(plan, outline, eave)
    high = eave if eave is not None else (measured_ceiling(plan) or STOREY)
    return found + roofs(plan, outline, high)


def solid(piece):
    """A piece's triangles [[[x, up, y] x 3]] in plan metres."""
    if piece["builder"] == "gable":
        return gable(piece["points"], piece["eave"], piece["top"])
    if piece["builder"] == "vault":
        return vault(piece["points"], piece["eave"], piece["top"], piece.get("lengthwise"))
    if piece["builder"] == "dome":
        return dome(piece["centre"], piece["radius"], piece["base"], piece["rise"])
    return prism(piece["points"], piece["low"], piece["high"])


def room(plan):
    """[(name, triangles, from)] of a room's deck, walls and roof, each its pieces' solids."""
    return [(name, [triangle for piece in parts for triangle in solid(piece)], said)
            for name, parts, said in pieces(plan)]


def levels(plan):
    """[(name, triangles, from)] of an open place's raised levels (module docstring, `level`)."""
    found = []
    for number, level in enumerate(plan.get("levels") or [], 1):
        if not raised(level):
            continue
        height = float(level.get("height") or 0.0)
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


# --- the shell's own pieces: pillars, beams, pads and grates -------------------------------------------------------

def row_words(row):
    """The words of a row's id, name and noun, lower case, a plural's s dropped."""
    return {word.removesuffix("s") for word in
            re.findall(r"[a-z]+", f"{row.get('id')} {row.get('name')} {row.get('noun')}".replace("_", " ").lower())}


def sized(row):
    """The row's size [wide, deep, tall] when it has three lengths over nothing, else None."""
    size = row.get("size") or []
    return [float(side) for side in size] if len(size) == 3 and \
        all(isinstance(side, (int, float)) and side > 0 for side in size) else None


def row_pieces(plan, rows):
    """[(row id, name, piece, what it was made from, the part kind it is painted as)] of each structural row of the
    shell's (rows: the hand-in's rows the plan's shell lays) that the shell builds as pieces of its own (module
    docstring, `pieces of rows`): an upright structure row along the walls (pillars), a spanning one under the roof
    (beams), a floor row at its own plan items (a pad, a grate); each piece `<row>_<n>`."""
    found = []
    for row in rows:
        words, framed = row_words(row), row.get("part") == "structure" and not arched(row)
        if framed and words & UPRIGHT:
            made, kind = pillars(plan, row), "wall"
        elif framed and words & SPANNING:
            made, kind = beams(plan, row), "wall"
        elif row.get("part") == "floor":
            made, kind = floor_pieces(plan, row), "deck"
        else:
            continue
        found += [(row["id"], f"{row['id']}_{number}", piece, said, kind)
                  for number, (piece, said) in enumerate(made, 1)]
    return found


def clear_spot(want, length, half, cuts):
    """The point along an edge of `length` nearest `want` where a piece `half` wide each side stands clear of the
    edge's ends and of every opening cut in it (cuts: (from, to, ...)), else None: no room on the edge."""
    blocked = sorted((begin - half, finish + half) for begin, finish, *_ in cuts)
    free, low = [], half
    for begin, finish in blocked:
        if begin > low:
            free.append((low, min(begin, length - half)))
        low = max(low, finish)
    if length - half > low:
        free.append((low, length - half))
    spans = [(begin, finish) for begin, finish in free if finish >= begin]
    return min((min(max(want, begin), finish) for begin, finish in spans), key=lambda at: abs(at - want)) \
        if spans else None


def pillars(plan, row):
    """[(piece, from)] of an upright row's pillars (its count, else one), spaced evenly round the outline's walls from
    half a space past its first corner, each slid along its wall clear of its corners and openings (clear_spot), its
    back against the wall's room face (face_reach), its section the row's wide along the wall
    and deep into the room, standing from the floor to the row's tall, never past its wall's top; none for a row of no
    size or a wall with no room left."""
    size = sized(row)
    if size is None:
        return []
    wide, deep, tall = size
    outline, eave, openings = outline_of(plan), lowest_eave(plan), openings_of(plan)
    edges = [(np.asarray(start, float), np.asarray(outline[(index + 1) % len(outline)], float))
             for index, start in enumerate(outline)]
    lengths = [float(np.linalg.norm(end - start)) for start, end in edges]
    count, total = int(row.get("count") or 1), sum(lengths)
    found = []
    for number in range(count):
        reach, index = (number + 0.5) * total / count, 0
        while index < len(edges) - 1 and reach > lengths[index]:
            reach, index = reach - lengths[index], index + 1
        (start, end), entry = edges[index], written_wall(plan, list(edges[index][0]), list(edges[index][1]))
        thick = float(entry.get("thick") or THICK)
        at = clear_spot(reach, lengths[index], wide / 2, on_edge(openings, start, end, thick))
        if at is None:
            continue
        along, normal = (end - start) / lengths[index], outward(start, end)
        foot = [start + along * (at - wide / 2), start + along * (at + wide / 2)]
        face = face_reach(entry, start, end)
        points = [foot[0] + normal * face, foot[1] + normal * face, foot[1] + normal * (face - deep),
                  foot[0] + normal * (face - deep)]
        high = min(tall, wall_height(plan, entry, eave))
        found.append((slab_piece(points, -DECK_BELOW, -DECK_BELOW + high),
                      f"inventory row {row['id']}'s pillar {number + 1} of {count}: against wall {index + 1}, "
                      f"{at:g} m along it, {wide:g} by {deep:g} m, {high:g} m high (design_shell.pillars)"))
    return found


def chord(points, across, at):
    """(low, high) along axis `across` (0: x, 1: y) where the line through `at` on the other axis meets an outline,
    else None."""
    other, found = 1 - across, []
    for one, two in zip(points, points[1:] + points[:1]):
        if (one[other] - at) * (two[other] - at) <= 0 and one[other] != two[other]:
            share = (at - one[other]) / (two[other] - one[other])
            found.append(one[across] + share * (two[across] - one[across]))
    return (min(found), max(found)) if len(found) >= 2 else None


def beams(plan, row):
    """[(piece, from)] of a spanning row's beams (its count, else one) under the roof: each across the outline's box's
    shorter side from wall face to wall face (the chord there of the outline grown to its walls' room faces,
    to_walls), spaced evenly along
    its longer side, its top at the roof's lowest eave (else the walls' height), the row's deep wide and its tall
    deep; none for a row of no size."""
    size = sized(row)
    if size is None:
        return []
    _, wide, tall = size
    outline = outline_of(plan)
    corners, faces = np.asarray(outline, float), to_walls(plan, outline)
    low, high = corners.min(axis=0), corners.max(axis=0)
    across = 0 if high[0] - low[0] <= high[1] - low[1] else 1
    other, count = 1 - across, int(row.get("count") or 1)
    eave = lowest_eave(plan)
    top = eave if eave is not None else (measured_ceiling(plan) or STOREY)
    found = []
    for number in range(count):
        at = float(low[other] + (number + 0.5) * (high[other] - low[other]) / count)
        span = chord(faces, across, at)
        if span is None:
            continue
        begin, finish = span
        corner = [[begin, at - wide / 2], [finish, at - wide / 2], [finish, at + wide / 2], [begin, at + wide / 2]]
        points = [point if across == 0 else point[::-1] for point in corner]
        found.append((slab_piece(points, top - tall, top),
                      f"inventory row {row['id']}'s beam {number + 1} of {count}: across the room "
                      f"{'east' if across == 0 else 'south'}ward {finish - begin:g} m at {at:g} m, {wide:g} m wide, "
                      f"{tall:g} m deep under {top:g} m (design_shell.beams)"))
    return found


def floor_pieces(plan, row):
    """[(piece, from)] of a floor row at each plan item of its own (an item with a shape: a pad, a grate; one only
    on the walls item is the deck's): the row's count shared over its items in order, each item's box split along its
    longer side into its share, from its shape's base to its tall (else the row's), at least FLUSH thick."""
    tied, shapes = plan.get("rows") or {}, plan.get("shapes") or {}
    items = [item for item in plan.get("items") or [] if (len(item) <= 6 or item[6] == "item")
             and row["id"] in (tied.get(item[0]) or []) and shapes.get(item[0])]
    if not items:
        return []
    size, count = sized(row), max(int(row.get("count") or 1), len(items))
    found = []
    for index, item in enumerate(items):
        share = count // len(items) + (1 if index < count % len(items) else 0)
        x, y, wide, deep = (float(value) for value in item[1:5])
        shape = shapes[item[0]]
        base = float(shape.get("base") or 0.0)
        thick = max(float(shape.get("tall") or (size[2] if size else 0.0)), FLUSH)
        for part in range(share):
            west, north, east, south = (x + wide * part / share, y, x + wide * (part + 1) / share, y + deep) \
                if wide >= deep else (x, y + deep * part / share, x + wide, y + deep * (part + 1) / share)
            found.append((slab_piece([[west, north], [east, north], [east, south], [west, south]], base, base + thick),
                          f"plan item {item[0]!r}, inventory row {row['id']}: piece {part + 1} of {share} on it, "
                          f"{thick:g} m thick at {base:g} m (design_shell.floor_pieces)"))
    return found


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
