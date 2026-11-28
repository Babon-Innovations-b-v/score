"""The cabin shell algorithm (library entry algorithm/cabin_shell, 2099 #246 and ADR-0008): a small craft's cabin
structure inside its conical pressure hull, built in code at its real size, every piece one mesh `geo` of named
parts for the place's library surfaces (cockpit_kit.written), laid by `kit` like the dome shell's blocks.

The owner wants a real Apollo- or Soyuz-like cabin (2099 #246: flat Beta-cloth panels, no quilted padding), and the
cabin's floor a deck over an underfloor bay (the concept's pipes, boxes and valves under the floor), so:

- `cabin_wall`: the wall's lining from the floor to the ceiling ring, as flat panels: each panel a flat slab
  inscribed in the cone between two of its `joints` (degrees round) and two of its course lines (COURSES up the
  cone, then the shoulder's straight chamfer in to the ceiling ring), its edges SEAM short of each joint; under
  every joint a recessed channel (part frame), on every upright joint of the wall courses a T-section rib standing
  off the panels (part rib, riveted), round-headed fasteners along each panel's edges (part fastener). The panels'
  face is part panel (the Beta cloth), their back and sides part back. A round hole [theta, y, r] (`holes`: the
  portholes, the hatch) is left open through the panels, and frames, ribs and fasteners stop short of its flange
  (`fades`); the cut-away (`cut`, cockpit_kit.in_cut) is left out of the "main" body and fills the "plug" (the
  camera's alone). `sector` [from, to] keeps the panels whose middle lies in it, `rise` [low, high] the courses whose
  middle lies in it (the shoulder a piece of its own, so a wall's middle stays by the wall).
- `cabin_ceiling`: the flat ceiling under the hull's top: a round middle panel and a ring of `ceiling_panels` flat
  panels (part panel), their seams over a backing plate (part frame), fasteners along their edges.
- `cabin_floor`: the walked deck over the underfloor bay: removable walkway plates (part deck) in a middle disc of
  four and an outer ring of `plates`, the seams between them open over the joists under them (part joist: a ring
  beam under the ring seam, a radial beam under every seam, an edge ring), countersunk fasteners at each plate's
  corners (part fastener), and the bay's bottom bulkhead at the hull's foot (part bay), so the bay between holds the
  underfloor rows (BAY: its clear height).

Every piece is built in the capsule's frame (y up the cone's axis, the floor's top at y = 0, theta from +z toward
+x), as cockpit_kit's FLAT_KINDS, and written as built.

    write(path, kind, sizes)    the piece of `kind` (KINDS) with its `sizes` written at `path`; its parts, sorted
"""
import math

import numpy as np
from scipy.spatial.transform import Rotation

from score.stages.place_build.cockpit_kit import (Cone, about, bolt_ring, box, circle_path, collar_flange, console,
                                                  frame_ring, grid_solid, in_cut, moved, near_hole, outline_slab, piece,
                                                  placed, sleeve, tube, turned, written)

COURSES = (0.0, 1.80)  # the wall's course lines, metres up the cone from the floor: one tall panel a joint, as a
# real cabin's wall (the inventory's lining panels, 0.8 x 1.9 m); the shoulder runs from the last to the ceiling ring
CEILING = 2.05  # metres up: the ceiling ring, where the shoulder's chamfer meets the ceiling's panels
INSET = 0.30  # metres the shoulder's chamfer comes in toward the axis from the wall's line by the ceiling ring
JOINTS = tuple(4.0 + 24.0 * step for step in range(15))  # degrees round: the panels' joints, the capsule lining's
# own (its walls lining_004 to lining_340 and the panels, lockers and mounting rails laid on them by their middles); a
# porthole on a joint (theta 28 and 76) cuts both panels and stops the joint's frame and rib at its flange
FOOT = 0.015  # metres up the cone a joint's frame and rib start: the cone leans in, so a rib's cap, laid square
# off the wall, would reach down into the deck from the floor line
SEAT = 0.0003  # metres a fastener's foot sinks into what it is driven into, so no face of it lies on that face
SEAM = 0.008  # metres from a joint to a panel's edge: the 16 mm open seam over the frame's channel
FRAME = (0.003, 0.014, 0.03)  # a frame channel's back and front (metres in off the hull's inner face) and width
BACK = 0.015  # metres in off the hull a panel's back stands at its edges, a millimetre over the frame's front
PANEL = 0.012  # a panel's thickness (Beta cloth over a honeycomb board)
RIB = (0.010, 0.045, 0.040, 0.012)  # a rib's stem width, its cap's back (metres in off the hull), the cap's width
# and thickness: a T-section stringer over each upright joint, its cap standing clear of the panels' faces
RIVET_PITCH = 0.14  # metres between the rivets along a rib's cap
FASTENER = (0.0055, 0.0025, 0.03, 0.16)  # a panel fastener's head radius, its height, its inset from the panel's
# edge and the most metres between two along an edge
CELL = 0.02  # metres: a panel's grid cell (a hole's edge is cut along it)
STEP = 0.01  # metres: how finely a frame's or rib's run is walked for the holes and the cut-away it stops at
DECK = 0.02  # metres: a walkway plate's thickness, its top the floor (y = 0)
RING = 0.49  # metres: the radius of the seam between the deck's middle disc and its outer ring
JOIST = (0.05, 0.10)  # a joist's width and depth under the deck plates
BAY = (-0.43, -0.40)  # the bay's bottom bulkhead, from and to (metres): the hull's foot, the bay clear above it
CEILING_PANELS = 6  # the ceiling's ring panels round its middle panel
CEILING_MIDDLE = 0.22  # metres: the ceiling's middle panel's radius


def line_point(cone, theta, height, offset):
    """The point of a wall's course line at `theta` (radians) and course height `height`, `offset` metres in off the
    hull's inner face: on the cone up to the last course, on the shoulder's chamfer above it (straight in INSET to
    the ceiling ring at CEILING)."""
    top = COURSES[-1]
    if height <= top + 1e-9:
        return cone.at(theta, height, offset)
    share = (height - top) / (CEILING - top)
    low, high = cone.at(theta, top, offset), cone.at(theta, CEILING, offset)
    radial = np.array([math.sin(theta), 0.0, math.cos(theta)])
    return low + share * (high - low) - radial * INSET * share


def course_lines():
    """Every course line of the wall from the floor to the ceiling ring, in order."""
    return [*COURSES, CEILING]


def panel_frame(corners):
    """A flat panel's frame from its four back corners [low a, low b, high a, high b]: (right along its bottom, up
    its middle, its normal toward the room)."""
    low_a, low_b, high_a, high_b = corners
    right = low_b - low_a
    right /= np.linalg.norm(right)
    up = (high_a + high_b - low_a - low_b) / 2
    up -= right * (up @ right)
    up /= np.linalg.norm(up)
    normal = np.cross(up, right)
    middle = (low_a + low_b + high_a + high_b) / 4
    if normal @ np.array([-middle[0], 0.0, -middle[2]]) < 0:
        normal = -normal
    return right, up, normal


def panel_corners(cone, theta_a, theta_b, low, high):
    """A flat panel's back corners between joints `theta_a` and `theta_b` (radians) and course lines `low` and
    `high`, SEAM short of each joint and course line, its edges on BACK: [low a, low b, high a, high b]. On a cone
    the four lie in one plane (an isosceles trapezoid)."""
    rho = float(cone.rho(low, BACK))
    shrink = SEAM / max(rho, 1e-6)
    theta_a, theta_b = theta_a + shrink, theta_b - shrink
    rise = SEAM if low > 0 else 0.010  # the bottom course stands a centimetre off the deck
    fall = SEAM
    bottom = [line_point(cone, theta, low, BACK) for theta in (theta_a, theta_b)]
    top = [line_point(cone, theta, high, BACK) for theta in (theta_a, theta_b)]
    along = [(upper - lower) / np.linalg.norm(upper - lower) for lower, upper in zip(bottom, top)]
    return [bottom[0] + along[0] * rise, bottom[1] + along[1] * rise, top[0] - along[0] * fall,
            top[1] - along[1] * fall]


def spot_angles(points):
    """Each point's angle round the axis (radians from +z toward +x) and its height."""
    return np.arctan2(points[..., 0], points[..., 2]), points[..., 1]


def outside_holes(cone, points, holes):
    """Whether each point lies clear of every round hole [theta, y, r] (cockpit_kit.near_hole's measure)."""
    return ~near_hole(cone, points, holes) if holes else np.ones(points.shape[:-1], dtype=bool)


def wanted(points, cut, which):
    """Whether each point belongs to the `which` body: outside the cut-away (`cut`) for "main", inside it for "plug"."""
    if which not in ("main", "plug"):
        raise ValueError(f"a cabin wall is its main body or its plug, not {which!r}")
    theta, height = spot_angles(points)
    inside = in_cut(theta, height, cut) if cut else np.zeros(points.shape[:-1], dtype=bool)
    return inside if which == "plug" else ~inside


def flat_panel(cone, corners, holes, cut, which):
    """One flat panel over its back `corners` as a closed slab PANEL thick toward the room: its cells (CELL) in a
    hole or not of `which` body left out, its face part panel, its back and sides part back."""
    right, up, normal = panel_frame(corners)
    low_a, low_b, high_a, high_b = corners
    across = max(np.linalg.norm(low_b - low_a), np.linalg.norm(high_b - high_a))
    tall = np.linalg.norm((high_a + high_b - low_a - low_b) / 2)
    columns, rows = max(2, int(math.ceil(across / CELL)) + 1), max(2, int(math.ceil(tall / CELL)) + 1)
    share_u, share_v = np.meshgrid(np.linspace(0.0, 1.0, columns), np.linspace(0.0, 1.0, rows))
    back = ((1 - share_v)[..., None] * ((1 - share_u)[..., None] * low_a + share_u[..., None] * low_b)
            + share_v[..., None] * ((1 - share_u)[..., None] * high_a + share_u[..., None] * high_b))
    front = back + normal * PANEL
    middles = (front[:-1, :-1] + front[:-1, 1:] + front[1:, :-1] + front[1:, 1:]) / 4
    corner_clear = outside_holes(cone, back, holes) & outside_holes(cone, front, holes)
    clear = corner_clear[:-1, :-1] & corner_clear[:-1, 1:] & corner_clear[1:, :-1] & corner_clear[1:, 1:]
    keep = clear & wanted(middles, cut, which)
    if not keep.any():
        return []
    open_column = np.zeros((rows - 1, 1), dtype=bool)  # grid_solid closes its grid round a ring: the column
    # joining the panel's last edge to its first is never kept
    keep = np.hstack([keep, open_column])
    parts = np.full(keep.shape, "panel")
    ways = np.broadcast_to(normal, front.shape)
    return grid_solid(front, back, keep, parts, "back", "back", ways)


def runs(kept):
    """The (first, last) index pairs of each unbroken run of True in `kept`."""
    found, start = [], None
    for index, value in enumerate(kept):
        if value and start is None:
            start = index
        if not value and start is not None:
            found.append((start, index - 1))
            start = None
    if start is not None:
        found.append((start, len(kept) - 1))
    return found


def bar(part, start, end, across, inward, wide, low, high, bevel=0.0015):
    """A straight closed bar from `start` to `end` (points on the hull's inner face line), `wide` across, from `low`
    to `high` metres along `inward`, its edges chamfered."""
    along = end - start
    length = np.linalg.norm(along)
    along = along / length
    across = across - along * (across @ along)
    across /= np.linalg.norm(across)
    inward = np.cross(across, along)  # (across, along, inward) right-handed: the box keeps its faces out
    if inward @ np.array([-start[0], 0.0, -start[2]]) < 0:
        across, inward = -across, -inward
    found = box(part, (-wide / 2, 0.0, low), (wide / 2, length, high), min(bevel, wide / 3, (high - low) / 3))
    return moved(found, np.column_stack([across, along, inward]), start)


def clear_runs(cone, line, holes, cut, which, least=0.03):
    """The runs (first, last point) of the points `line` (n x 3, the inner face's line of a joint) that stand clear
    of every hole's fade and in the `which` body, none shorter than `least` metres."""
    kept = outside_holes(cone, line, holes) & wanted(line, cut, which)
    found = []
    for first, last in runs(kept):
        if np.linalg.norm(line[last] - line[first]) >= least:
            found.append((line[first], line[last]))
    return found


def walked(start, end):
    """Points every STEP metres from `start` to `end`, both ends in."""
    count = max(2, int(math.ceil(np.linalg.norm(end - start) / STEP)) + 1)
    return start + np.linspace(0.0, 1.0, count)[:, None] * (end - start)


def upright_joint(cone, theta, low, high, holes, fades, cut, which, ribbed):
    """The frame channel under an upright joint at `theta` (radians) from course line `low` to `high`, and with
    `ribbed` the T-section rib over it with its rivets; each stopped short of every hole's flange (`fades`) and the
    cut-away."""
    start, end = line_point(cone, theta, max(low, FOOT), 0.0), line_point(cone, theta, high, 0.0)
    across = np.array([math.cos(theta), 0.0, -math.sin(theta)])
    inward = cone.inward(theta)
    back, front, wide = FRAME
    found = []
    for first, last in clear_runs(cone, walked(start, end), list(holes) + list(fades), cut, which):
        found += bar("frame", first, last, across, inward, wide, back, front)
        if not ribbed:
            continue
        stem, cap_back, cap_wide, cap_thick = RIB
        found += bar("rib", first, last, across, inward, stem, front, cap_back)
        found += bar("rib", first, last, across, inward, cap_wide, cap_back, cap_back + cap_thick, 0.003)
        found += rivets(first, last, inward, cap_back + cap_thick)
    return found


def rivets(first, last, inward, face):
    """Round rivet heads every RIVET_PITCH along a rib's cap from `first` to `last`, standing on its face `face`
    metres in."""
    length = np.linalg.norm(last - first)
    end = 0.04  # metres in from each end of the cap the first rivet stands
    head = fastener_head(0.0045, 0.002)
    found = []
    shares = ([0.5] if length < 2 * end + RIVET_PITCH / 2 else
              np.linspace(end / length, 1 - end / length, int((length - 2 * end) // RIVET_PITCH) + 2))
    for share in shares:  # a short run takes one rivet in its middle, never two on one spot
        spot = first + share * (last - first) + inward * (face - SEAT)
        found += moved(head, onto(inward), spot)
    return found


def fastener_head(radius, high):
    """A round-headed fastener standing `high` on its seat, `radius` across, its axis +z, closed."""
    return turned("fastener", [(0.0, 0.0), (radius, 0.0), (radius, high * 0.45), (radius * 0.75, high),
                               (0.0, high)], segments=10)


def onto(normal):
    """The rotation turning +z onto `normal`."""
    normal = np.asarray(normal, dtype=np.float64) / np.linalg.norm(normal)
    helper = np.array([0.0, 1.0, 0.0]) if abs(normal[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    right = np.cross(helper, normal)
    right /= np.linalg.norm(right)
    return np.column_stack([right, np.cross(normal, right), normal])


def edge_spots(corners):
    """The fastener spots of a flat panel over its back `corners`, on its face: along each edge FASTENER's inset in
    from it, no more than its pitch apart, the corners in."""
    radius, _, inset, pitch = FASTENER
    low_a, low_b, high_a, high_b = corners
    _, _, normal = panel_frame(corners)

    def at(share_u, share_v):
        bottom = low_a + share_u * (low_b - low_a)
        top = high_a + share_u * (high_b - high_a)
        return bottom + share_v * (top - bottom)

    across = min(np.linalg.norm(low_b - low_a), np.linalg.norm(high_b - high_a))
    tall = np.linalg.norm((high_a + high_b - low_a - low_b) / 2)
    edge_u, edge_v = inset / across, inset / tall
    shares_u = np.linspace(edge_u, 1 - edge_u, max(2, int(math.ceil((across - 2 * inset) / pitch)) + 1))
    shares_v = np.linspace(edge_v, 1 - edge_v, max(2, int(math.ceil((tall - 2 * inset) / pitch)) + 1))
    spots = {(round(u, 6), round(v, 6)) for u in shares_u for v in (edge_v, 1 - edge_v)}
    spots |= {(round(u, 6), round(v, 6)) for u in (edge_u, 1 - edge_u) for v in shares_v}
    points = np.array([at(u, v) for u, v in sorted(spots)]) + normal * (PANEL - SEAT)
    return points, normal, radius


def panel_fasteners(cone, corners, holes, fades, cut, which):
    """The fasteners along a flat panel's edges, each clear of every hole's flange and in the `which` body."""
    points, normal, radius = edge_spots(corners)
    keep = outside_holes(cone, points, list(holes) + list(fades)) & wanted(points, cut, which)
    head = fastener_head(radius, FASTENER[1])
    turn = onto(normal)
    found = []
    for point in points[keep]:
        found += moved(head, turn, point)
    return found


def course_joint(cone, theta_a, theta_b, height, holes, fades, cut, which):
    """The frame channel under the course line `height` between joints `theta_a` and `theta_b` (radians): one
    straight chord on a cone, stopped short of every hole's flange and the cut-away."""
    start, end = line_point(cone, theta_a, height, 0.0), line_point(cone, theta_b, height, 0.0)
    middle = (theta_a + theta_b) / 2
    up = line_point(cone, middle, min(height + 0.05, CEILING), 0.0) - line_point(cone, middle,
                                                                                 max(height - 0.05, 0.0), 0.0)
    inward = cone.inward(middle)
    back, front, wide = FRAME
    found = []
    for first, last in clear_runs(cone, walked(start, end), list(holes) + list(fades), cut, which):
        found += bar("frame", first, last, up, inward, wide, back, front)
    return found


def in_sector(theta, sector):
    """Whether the angle `theta` (radians) lies in `sector` [from, to] degrees (every angle when None)."""
    if sector is None:
        return True
    start = math.radians(sector[0])
    return (theta - start + 1e-9) % (2 * math.pi) < math.radians(sector[1] - sector[0])


def in_rise(low, high, rise):
    """Whether a course from `low` to `high` has its middle in `rise` [low, high] (every course when None)."""
    return rise is None or rise[0] <= (low + high) / 2 < rise[1]


def cabin_wall(joints=JOINTS, holes=(), fades=(), cut=None, which="main", sector=None, rise=None, **sizes):
    """The wall's flat-panelled lining (the module's `cabin_wall`): a flat panel between each two `joints` and each
    two course lines, the frames under their joints, a rib over each upright joint of the wall courses, the
    fasteners along each panel's edges; holes, fades, cut-away, `sector` and `rise` as the module says."""
    cone = Cone(**sizes)
    angles = sorted(math.radians(value % 360.0) for value in joints)
    lines = course_lines()
    found = []
    for index, theta_a in enumerate(angles):
        theta_b = angles[(index + 1) % len(angles)] + (2 * math.pi if index + 1 == len(angles) else 0.0)
        if not in_sector((theta_a + theta_b) / 2, sector):
            continue
        for low, high in zip(lines[:-1], lines[1:]):
            if not in_rise(low, high, rise):
                continue
            corners = panel_corners(cone, theta_a, theta_b, low, high)
            found += flat_panel(cone, corners, holes, cut, which)
            found += panel_fasteners(cone, corners, holes, fades, cut, which)
            found += course_joint(cone, theta_a, theta_b, high, holes, fades, cut, which)
            found += upright_joint(cone, theta_a, low, high, holes, fades, cut, which, high <= COURSES[-1])
    return found


def annulus_sheet(part, inner, outer, start, end, low, high, side_part=None):
    """A closed slab over the ring sector from radius `inner` to `outer` and angle `start` to `end` (radians), from
    y `low` to `high`; its top in `part` (facing up), its bottom and sides in `side_part` (`part` when None)."""
    columns = max(3, int(math.ceil((end - start) * outer / 0.03)) + 1)
    rows = max(2, int(math.ceil((outer - inner) / 0.05)) + 1)
    angles = np.linspace(start, end, columns)
    radii = np.linspace(inner, outer, rows)
    grid_radius, grid_angle = np.meshgrid(radii, angles, indexing="ij")
    top = np.stack([grid_radius * np.sin(grid_angle), np.full_like(grid_radius, high),
                    grid_radius * np.cos(grid_angle)], axis=-1)
    bottom = top.copy()
    bottom[..., 1] = low
    keep = np.ones((rows - 1, columns), dtype=bool)
    keep[:, -1] = False  # the column closing the grid round a ring is never kept: the sector's ends are sides
    parts = np.full(keep.shape, part)
    ways = np.broadcast_to(np.array([0.0, 1.0, 0.0]), top.shape)
    return grid_solid(top, bottom, keep, parts, side_part or part, side_part or part, ways)


def disc_sheet(part, radius, low, high, side_part=None):
    """A closed round slab of `radius` from y `low` to `high`; its top in `part`, bottom and side in `side_part`."""
    side = side_part or part
    return moved(turned(side, [(0.0, low), (radius, low), (radius, high)], segments=72)
                 + turned(part, [(radius, high), (0.0, high)], segments=72), about("x", -90))


def floor_edge(cone):
    """The deck's outer radius: under the wall panels' feet, a little short of the hull."""
    return float(cone.rho(0.0, FRAME[0])) - 0.002


def plate_angles(plates):
    """The outer ring's seams (radians), `plates` of them evenly round from the first."""
    return [2 * math.pi * step / plates for step in range(plates)]


def cabin_floor(plates=10, bay=BAY, **sizes):
    """The walked deck over the underfloor bay (the module's `cabin_floor`): four plates in its middle disc and
    `plates` in its outer ring, SEAM-wide open seams between them over the joists, countersunk fasteners at each
    plate's corners, the bay's bottom bulkhead at the hull's foot (`bay` [from, to] y)."""
    cone = Cone(**sizes)
    edge = floor_edge(cone)
    gap = SEAM / 2
    found = []
    for quarter in range(4):
        start, end = quarter * math.pi / 2, (quarter + 1) * math.pi / 2
        found += annulus_sheet("deck", 0.0 + 0.001, RING - gap, start + gap / RING * 2, end - gap / RING * 2,
                               -DECK, 0.0)
    seams = plate_angles(plates)
    for index, start in enumerate(seams):
        end = seams[(index + 1) % plates] + (2 * math.pi if index + 1 == plates else 0.0)
        found += annulus_sheet("deck", RING + gap, edge, start + gap / RING, end - gap / RING, -DECK, 0.0)
    found += floor_joists(edge, seams)
    found += plate_fasteners(edge, seams)
    found += disc_sheet("bay", float(cone.rho(bay[1])) + cone.sizes["hull"], bay[0], bay[1])
    return found


def floor_joists(edge, seams):
    """The deck's joists, their tops under the plates: a ring beam under the ring seam, an edge ring under the
    plates' outer edge, a radial beam under each outer seam and a cross under the middle disc's seams."""
    wide, deep = JOIST
    top, bottom = -DECK - 0.001, -DECK - deep  # a millimetre under the plates, no face shared with them
    found = annulus_sheet("joist", RING - wide / 2, RING + wide / 2, 0.0, 2 * math.pi * 0.999, bottom, top)
    found += annulus_sheet("joist", edge - wide, edge, 0.0, 2 * math.pi * 0.999, bottom, top)
    for angle in seams:
        direction = np.array([math.sin(angle), 0.0, math.cos(angle)])
        found += beam(direction, RING + wide / 2, edge - wide, wide, bottom, top)
    for angle in (0.0, math.pi / 2):
        direction = np.array([math.sin(angle), 0.0, math.cos(angle)])
        found += beam(direction, -(RING - wide / 2), RING - wide / 2, wide, bottom, top)
    return found


def beam(direction, near, far, wide, bottom, top):
    """A straight joist along `direction` (level) from `near` to `far` metres from the axis, `wide` across, from y
    `bottom` to `top`."""
    across = np.array([direction[2], 0.0, -direction[0]])
    turn = np.column_stack([across, np.array([0.0, 1.0, 0.0]), direction])
    return moved(box("joist", (-wide / 2, bottom, near), (wide / 2, top, far), 0.002), turn)


def plate_fasteners(edge, seams):
    """Countersunk fasteners at each walkway plate's corners, standing a millimetre proud of the deck."""
    head = fastener_head(0.006, 0.001)
    inset = 0.03
    spots = []
    for angle in seams:
        for offset in (-1, 1):
            for radius in (RING + inset, edge - inset * 1.5):
                turned_angle = angle + offset * inset / radius
                spots.append((radius * math.sin(turned_angle), radius * math.cos(turned_angle)))
    for quarter in range(4):
        middle = quarter * math.pi / 2 + math.pi / 4
        radius = RING - inset * 1.5
        for offset in (-1, 1):
            turned_angle = middle + offset * (math.pi / 4 - inset / radius)
            spots.append((radius * math.sin(turned_angle), radius * math.cos(turned_angle)))
    found = []
    for x, z in spots:
        found += moved(head, about("x", -90), (x, -0.0002, z))
    return found


def cabin_ceiling(panels=CEILING_PANELS, **sizes):
    """The flat ceiling under the hull's top (the module's `cabin_ceiling`): its face at the ceiling ring's height,
    reaching the shoulder's top line; a round middle panel and `panels` ring panels PANEL thick (part panel), the
    open seams between them over a backing plate (part frame), fasteners along their edges."""
    cone = Cone(**sizes)
    outer = float(np.hypot(*line_point(cone, 0.0, CEILING, BACK)[[0, 2]])) - SEAM
    gap = SEAM
    low, high = CEILING, CEILING + PANEL
    found = disc_sheet("frame", outer + 0.02, high + 0.001, high + 0.05)  # the backing plate the panels hang from
    found += flipped(disc_sheet("panel", CEILING_MIDDLE - gap, low, high, "back"), low, high)
    seams = [2 * math.pi * step / panels for step in range(panels)]
    for index, start in enumerate(seams):
        end = seams[(index + 1) % panels] + (2 * math.pi if index + 1 == panels else 0.0)
        found += flipped(annulus_sheet("panel", CEILING_MIDDLE + gap, outer, start + gap / CEILING_MIDDLE,
                                       end - gap / CEILING_MIDDLE, low, high, "back"), low, high)
    head = fastener_head(FASTENER[0], FASTENER[1])
    down = about("x", 90)
    for index, start in enumerate(seams):
        for offset in (-1, 1):
            for radius in (CEILING_MIDDLE + 0.05, (CEILING_MIDDLE + outer) / 2, outer - 0.04):
                angle = start + offset * 0.04 / radius
                found += moved(head, down, (radius * math.sin(angle), low + SEAT, radius * math.cos(angle)))
    return found


def flipped(pieces, low, high):
    """Pieces built facing up between y `low` and `high` turned upside down in place (their face now down)."""
    mirror = np.diag([1.0, -1.0, 1.0])
    return [(part, points @ mirror.T + np.array([0.0, low + high, 0.0]), triangles[:, ::-1],
             smooth @ mirror.T if isinstance(smooth, np.ndarray) else smooth)
            for part, points, triangles, smooth in pieces]


# --- the instrument side (2099 #246, 2026-11-28): the panels, screens, ball, console and portholes the hardware sits on.
# Each is built in a made model's frame (origin at its foot's middle, y up, its front +z, its depth centred on z = 0), so
# the inventory's spots for it and for the library hardware on its face hold as written; the pieces the game draws on
# (GAME_FACES: a display's glass, the attitude ball, a gauge's dial) are written turned half round y, their front -z, as
# the game's cockpit reads a display's face, and laid turned back. The portholes are built in the capsule's frame.

HOUSING_BACK = 0.008  # metres a panel's housing stops short of its face, under the face plate
LIFT = 0.0003  # metres each body of a panel stands off the one under it: none overlaps or shares a face with another
# (two closed bodies overlapping read their faces' count wrong, and the check found a panel inside its gauge)
RIM = 0.005  # metres a bezel stands over the face it is laid on
BORDER = 0.018  # a panel's bezel band, metres in from its edge
FASTENER_PITCH = 0.12  # metres at most between the fasteners along a bezel
GAME_FACES = ("display", "attitude_ball", "gauge")


def housing(wide, high, deep, front):
    """A panel's housing (part frame): a closed box `wide` x `high` from its back (z = -deep/2) to `front`."""
    return box("frame", (-wide / 2, 0.0, -deep / 2), (wide / 2, high, front), 0.004)


def face_plate(part, wide, high, low, face):
    """The plate (part `part`) over a housing whose front is at z `low`: `wide` x `high`, its face at `face`."""
    return box(part, (-wide / 2 + 0.004, 0.004, low + LIFT), (wide / 2 - 0.004, high - 0.004, face), 0.0015)


def bezel_ring(outer, inner, low, top, middle):
    """A bezel (part bezel) between the plans `outer` and `inner` round `middle` (x, y), from z `low` to `top`."""
    return moved(frame_ring("bezel", outer, inner, low, top), offset=(middle[0], middle[1], 0.0))


def bezel_fasteners(wide, high, border, top, middle):
    """Round-headed fasteners (part fastener) along the middle of a `border` wide bezel band round a `wide` x `high`
    plan at `middle`: one by each corner and more along each edge, at most FASTENER_PITCH apart, standing on `top`."""
    reach_x, reach_y = wide / 2 - border / 2, high / 2 - border / 2
    spots = [(sx * reach_x, sy * reach_y) for sx in (-1, 1) for sy in (-1, 1)]
    for reach, edge, across in ((reach_x, reach_y, False), (reach_y, reach_x, True)):
        count = max(1, math.ceil(2 * reach / FASTENER_PITCH))
        for step in range(1, count):
            along = -reach + 2 * reach * step / count
            spots += [(side * edge, along) if across else (along, side * edge) for side in (-1, 1)]
    head = fastener_head(FASTENER[0] * 0.8, FASTENER[1])
    found = []
    for x, y in spots:
        found += moved(head, offset=(middle[0] + x, middle[1] + y, top + LIFT))
    return found


def bezel_bars(wide, high, border, low, top, bottom=0.0):
    """A bezel band `border` wide round a `wide` x `high` plan from y = `bottom` (part bezel), from z `low` to `top`,
    as four bars: each body convex, so its middle lies in itself and never in what stands in the band's hole (a ring's
    middle lies in its hole: the check read a panel inside the gauge standing there)."""
    left, right, foot, head = -wide / 2, wide / 2, bottom, bottom + high
    found = box("bezel", (left, foot, low), (right, foot + border, top), 0.0015)
    found += box("bezel", (left, head - border, low), (right, head, top), 0.0015)
    found += box("bezel", (left, foot + border + 0.0005, low), (left + border, head - border - 0.0005, top), 0.0015)
    found += box("bezel", (right - border, foot + border + 0.0005, low), (right, head - border - 0.0005, top), 0.0015)
    return found


def instrument_panel(wide=0.4, high=0.35, deep=0.06, **_):
    """A wall instrument panel (rows power, fuel, tower, engine and radio panel, the attitude hold scenery panel, the
    SAS strip): a housing `deep` deep (part frame), a face plate with its face at z = deep/2 (part plate) where the
    library hardware sits, a raised bezel band round it (part bezel, bezel_bars) and fasteners along the bezel (part
    fastener)."""
    face = deep / 2
    low = face - HOUSING_BACK
    found = housing(wide, high, deep, low)
    found += face_plate("plate", wide, high, low, face)
    found += bezel_bars(wide - 0.004, high - 0.004, BORDER, face + LIFT, face + RIM, 0.002)
    found += bezel_fasteners(wide, high, BORDER, face + RIM, (0.0, high / 2))
    return found


def display(wide=0.42, high=0.32, deep=0.08, glass="glass_dark", border=0.03, header=0.0, **_):
    """A screen in its housing (rows main flight screen, burn timer): a housing (part frame), a wide bezel (part
    bezel, bezel_bars) round a dark glass face (part `glass`, the face the game draws its page on) set a little behind
    the bezel's top, `header` metres more of bezel over the glass (where its lit label sits), and fasteners along the
    bezel."""
    face = deep / 2
    low = face - HOUSING_BACK
    glass_high = high - 2 * border - header
    found = housing(wide, high, deep, low)
    found += box(glass, (-wide / 2 + border + 0.0005, border + 0.0005, low + LIFT),
                 (wide / 2 - border - 0.0005, border + glass_high - 0.0005, face - 0.0015), 0.0005)
    found += bezel_bars(wide - 0.004, high - 0.004, border, low + LIFT, face + RIM, 0.002)
    if header:  # the band over the glass widened to the header: one more bar under the top one
        found += box("bezel", (-wide / 2 + 0.002 + border, border + glass_high, low + LIFT),
                     (wide / 2 - 0.002 - border, high - 0.002 - border - 0.0005, face + RIM), 0.0015)
    found += bezel_fasteners(wide, high, min(border, BORDER), face + RIM, (0.0, high / 2))
    return found


def ball_quarter(part, radius, sign, rings=12, sides=24):
    """A closed quarter ball: the front (+z) half of a ball of `radius` round the origin, its upper (`sign` 1) or lower
    (-1) half, its dome shaded smooth and its two flat faces (across its horizon and its back) flat."""
    polar = np.linspace(0.0, math.pi / 2, rings + 1)
    around = np.linspace(0.0, math.pi, sides + 1)
    grid = np.array([[(radius * math.sin(down) * math.cos(turn), sign * radius * math.sin(down) * math.sin(turn),
                       radius * math.cos(down)) for turn in around] for down in polar[1:]])
    points = np.vstack([[[0.0, 0.0, radius]], grid.reshape(-1, 3)])
    index = lambda ring, side: 1 + ring * (sides + 1) + side  # noqa: E731 (the grid's point index, one line)
    dome = [[0, index(0, side), index(0, side + 1)] for side in range(sides)]
    for ring in range(rings - 1):
        for side in range(sides):
            dome += [[index(ring, side), index(ring + 1, side), index(ring + 1, side + 1)],
                     [index(ring, side), index(ring + 1, side + 1), index(ring, side + 1)]]
    centre = len(points)
    points = np.vstack([points, [[0.0, 0.0, 0.0]]])
    edge = ([index(ring, sides) for ring in range(rings - 1, -1, -1)] + [0] + [index(ring, 0) for ring in range(rings)])
    flat = [[centre, edge[step], edge[step + 1]] for step in range(len(edge) - 1)]
    flat += [[centre, index(rings - 1, side + 1), index(rings - 1, side)] for side in range(sides)]
    middle = np.array([0.0, sign * radius * 0.42, radius * 0.375])
    return [piece(part, points, outward(points, np.asarray(dome), middle), True),
            piece(part, points, outward(points, np.asarray(flat), middle), False)]


def outward(points, triangles, middle):
    """The triangles of a convex solid round `middle` each wound to face away from it."""
    corners = points[triangles]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    flip = np.einsum("ij,ij->i", normals, corners.mean(axis=1) - middle) < 0
    triangles = triangles.copy()
    triangles[flip] = triangles[flip][:, ::-1]
    return triangles


def attitude_ball(wide=0.22, high=0.22, deep=0.07, size=0.13, header=0.0, **_):
    """The attitude ball (rows attitude ball, attitude ball sphere): a housing (part frame), its plate (part plate) and
    a round bezel (part bezel) holding a ball `size` across whose front half stands out of the plate, its sky half over
    its horizon (part ball_sky) and its ground half under it (part ball_ground; the game turns the two as one ball
    round their middle, on the plate's face), `header` metres of plate over it for its lit label, an orange craft
    marker before its face (part marker) and fasteners at the plate's corners."""
    face, radius = deep / 2, size / 2
    low = face - HOUSING_BACK
    middle = (0.0, (high - header) / 2, face + LIFT)
    found = housing(wide, high, deep, low)
    found += face_plate("plate", wide, high, low, face)
    found += bezel_ring(circle_path(radius * 1.32, radius * 1.32, steps=64)[:-1],
                        circle_path(radius * 1.06, radius * 1.06, steps=64)[:-1], face + LIFT, face + RIM, middle[:2])
    for part, sign in (("ball_sky", 1.0), ("ball_ground", -1.0)):  # parted a hair at the horizon: no shared face
        found += moved(ball_quarter(part, radius, sign), offset=(middle[0], middle[1] + sign * 0.0004, middle[2]))
    front = middle[2] + radius
    for low_x, high_x in ((-radius * 0.5, -radius * 0.14), (radius * 0.14, radius * 0.5)):
        found += box("marker", (low_x, middle[1] - 0.002, front + 0.002), (high_x, middle[1] + 0.002, front + 0.006),
                     0.0006)
    found += bezel_fasteners(wide, high, BORDER, face, (0.0, high / 2))[:4]
    return found


def gauge(size=0.09, deep=0.04, **_):
    """A round dial gauge (FUEL's tank pressure gauge): a square housing (part frame), a round bezel (part bezel)
    round a dark dial face (part dial, the face the game draws on) on the housing's front, and four corner
    fasteners."""
    face, radius = deep / 2, size * 0.4
    low = face - HOUSING_BACK
    found = housing(size, size, deep, low)
    found += moved(turned("dial", [(0.0, low + LIFT), (radius - 0.0025, low + LIFT), (radius - 0.0025, face - 0.0015),
                                   (0.0, face - 0.0015)], segments=48), offset=(0.0, size / 2, 0.0))
    found += bezel_ring(circle_path(size * 0.47, size * 0.47, steps=48)[:-1],
                        circle_path(radius - 0.002, radius - 0.002, steps=48)[:-1], low + LIFT, face + RIM,
                        (0.0, size / 2))
    corner = size / 2 - 0.0055
    head = fastener_head(FASTENER[0] * 0.6, FASTENER[1] * 0.8)
    for x in (-corner, corner):
        for y in (size / 2 - corner, size / 2 + corner):
            found += moved(head, offset=(x, y, low + LIFT))
    return found


def console_desk(wide=1.0, deep=0.3, front_high=0.52, back_high=0.62, **_):
    """The pilot's console (row pilot console): cockpit_kit.console's box `wide` across, its sloping deck from
    `back_high` at its back (z = 0) down to `front_high` on the pilot's side (z = `deep`), its lip, vent grille and
    side equipment covers (parts body, deck, lip, vent, cover, hinge, bolt, plate), as the inventory's spots on its
    deck are written for (the stick, throttle, SAS panel, screen and ball)."""
    return console(wide=wide, deep=deep, front_high=front_high, back_high=back_high, grille=0.4, covers=True)


def porthole(at=(76.0, 1.54), radius=0.18, wall=0.012, flange=0.05, bolts=12, outside=0.03, **sizes):
    """A porthole through the cabin wall at `at` [theta (degrees), y] (rows porthole, its glass and its bolts), in the
    capsule's frame: a sleeve of `radius` through the hull and the wall's panels (part rim), a flange hugging the
    panels' face round it and one the hull's outside (part rim), `bolts` bolt heads round the inner flange (part
    fastener) and its pane out past the hull (part glass)."""
    cone = Cone(**sizes)
    angle = math.radians(at[0])
    right, up, axis = cone.frame(angle)
    middle = cone.at(angle, at[1])
    face = BACK + PANEL
    found = sleeve(cone, middle, right, up, axis, radius, wall, -cone.sizes["hull"] - outside, face, "rim", "rim")
    bedded = radius + wall - 0.003  # each flange reaches into the sleeve's wall, so no face of one lies on the other
    found += collar_flange(cone, middle, right, up, axis, bedded, radius + wall + flange, face, 0.012, False, "rim")
    found += collar_flange(cone, middle, right, up, axis, bedded, radius + wall + flange * 0.8, -cone.sizes["hull"],
                           0.010, True, "rim")
    found += [("fastener", *rest) for _, *rest in bolt_ring(cone, middle, right, up, axis, radius + wall + flange / 2,
                                                             face, 0.0125, bolts)]
    pane = -cone.sizes["hull"] - outside / 2
    found += placed(turned("glass", [(0.0, pane - 0.002), (radius + 0.001, pane - 0.002), (radius + 0.001, pane + 0.002),
                                     (0.0, pane + 0.002)], segments=96), middle, right, up, axis)
    return found


def superellipse_path(half_x, half_y, square, steps=96):
    """The counter-clockwise plan of a superellipse `half_x` by `half_y` round its middle, of exponent `square` (2 an
    ellipse, higher squarer), `steps` points."""
    turns = np.arange(steps) * 2 * math.pi / steps
    bend = 2 / square
    return [(half_x * math.copysign(abs(math.cos(turn)) ** bend, math.cos(turn)),
             half_y * math.copysign(abs(math.sin(turn)) ** bend, math.sin(turn))) for turn in turns]


def hatch_door(wide=0.77, high=1.21, thick=0.05, window=0.23, square=2.8, **_):
    """The side hatch's door (rows side hatch door, hatch window, hatch handles), built in a made model's frame
    (origin at its foot's middle, y up, its inside face +z, its thickness centred on z = 0) and laid at `hatch_spot`:
    an oval leaf `wide` x `high` (part leaf) `thick` thick, its outline a superellipse of exponent `square` (2 an
    ellipse; the side hatch frame's bore is fuller at its corners than one), a round window `window` across through
    its middle (part glass, set within the leaf's thickness), a raised band round its inside edge and a bezel round
    the window (part rim) and two grab handles on its inside face either side of the window (part handle)."""
    low, top = -thick / 2, thick / 2
    hole = window / 2
    oval = lambda inset: superellipse_path(wide / 2 - inset, high / 2 - inset, square)  # noqa: E731 (one line)
    disc = lambda radius: circle_path(radius, radius, steps=96)[:-1]  # noqa: E731 (one line)
    found = frame_ring("leaf", oval(0.0), disc(hole), low, top)
    found += outline_slab("glass", disc(hole - 0.001), low + 0.012, top - 0.012)
    found += frame_ring("rim", oval(0.004), oval(0.05), top + LIFT, top + 0.015)
    found += frame_ring("rim", disc(hole + 0.035), disc(hole - 0.003), top + LIFT, top + 0.012)
    for side in (-1.0, 1.0):  # a grab bar each side of the window, standing off the leaf's face on its two feet
        x = side * (hole + 0.11)
        found += tube("handle", [(x, -0.13, top + 0.001), (x, -0.13, top + 0.032), (x, -0.112, top + 0.05),
                                 (x, 0.112, top + 0.05), (x, 0.13, top + 0.032), (x, 0.13, top + 0.001)], 0.011, 12)
    return moved(found, offset=(0.0, high / 2, 0.0))


def hatch_spot(at=(268.0, 1.0), centre=(-0.035, 0.0), depth=-0.02, high=1.21, **sizes):
    """Where `hatch_door` is laid shut in its frame's bore through the wall at `at` [theta (degrees), y], in the
    capsule's frame: its middle `centre` metres right and up of the hole's middle (square to the wall) and `depth`
    metres along the wall's normal off the hull's inner face, its inside facing into the cabin; (at, turn) as a
    kit step takes them (its foot's middle, XYZ degrees)."""
    cone = Cone(**sizes)
    angle = math.radians(at[0])
    right, up, axis = cone.frame(angle)
    middle = cone.at(angle, at[1]) + centre[0] * right + centre[1] * up + depth * axis
    turn = Rotation.from_matrix(np.stack([right, up, axis], axis=1)).as_euler("xyz", degrees=True)
    return [round(float(value), 5) for value in middle - up * high / 2], [round(float(value), 5) for value in turn]


KINDS = {"cabin_wall": cabin_wall, "cabin_floor": cabin_floor, "cabin_ceiling": cabin_ceiling,
         "instrument_panel": instrument_panel, "display": display, "attitude_ball": attitude_ball, "gauge": gauge,
         "console_desk": console_desk, "porthole": porthole, "hatch_door": hatch_door}


def write(path, kind, sizes):
    """The piece of `kind` (KINDS) with its `sizes` written at `path` as built (cockpit_kit.written), a GAME_FACES
    piece turned half round y (its front -z, as the game reads a display's face); its parts."""
    if kind not in KINDS:
        raise ValueError(f"no cabin shell piece {kind!r} (pieces are {', '.join(sorted(KINDS))})")
    pieces = KINDS[kind](**sizes)
    return written(path, moved(pieces, about("y", 180)) if kind in GAME_FACES else pieces)
