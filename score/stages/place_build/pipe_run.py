"""The pipe run algorithm (2099 ADR-0008, 2026-11-26: a place's long thin parts made from the library, never a
picture's model of a pipe): a run laid along its path with its profile, its fittings and a named part for each
library surface, every piece a closed solid, as the cockpit kit's pieces are (cockpit_kit.written: one mesh `geo`, a
GeomSubset a part).

    write(path, spec)    the run of `spec` written as a USD file at `path`; its answer {"parts", "length", "spots"}

The run's own frame is the frame its `path` is given in (metres, y up): laid at the origin with no turn, the run
stands where its points say. `spec`:

- `path` [[x, y, z], ...] the run's centreline (a railing's: its feet, along the floor or up a flight), or `paths`
  several of them in one object (a harness's straps, a row of drainpipes);
- `profile` its section, one of PROFILES, with its sizes:
  `round` a rigid pipe, conduit, drainpipe, rail or rib (`radius`); `corrugated` a ridged hose (`radius`, `pitch`);
  `cord` a flexible cable or power cord (`radius`); `bundle` a harness of `count` cables (`radius` each);
  `flat` a strap or band (`wide`, `thick`); `box` a square or flat bar, a stringer, a rib (`wide`, `deep`);
  `channel` an open cable tray (`wide`, `deep`, `thick`); `railing` posts under rails (`high`, `rails` the heights
  of the rails under the top one, `posts` the most metres between posts, `post` and `rail` their radii, `infill`
  none, `bars` (balusters, `bar` their radius, BAR_RADIUS by default) or `glass`);
- `sag` metres a flexible run hangs between each two of its points (a catenary: an overhead cable, a lantern
  string, a cord between a lamp and its socket);
- `bend` the bend radius at each corner (BEND_RADII of its radius by default; a cable's wider, FLEXIBLE_RADII);
- `face` the way a flat, box or channel section's depth points (default up), carried along the run;
- `wall` the way from the run to the wall it is held on (or a round wall, {"axis": [x, z], "side": "out" | "in"}: a
  cabin's lining round the run, a silo the run stands round) and `stand` the metres from its middle to that wall: a
  bracket every `brackets` metres (BRACKET_GAP), each a clamp round the run on a stand-off and a plate on the wall;
- `joints` metres between a rigid run's collars (a drainpipe's sockets; none by default), `caps` its ends closed by
  a cap, `clamps` metres between a bundle's ties (TIE_GAP), `buckles` [[x, y, z]] a strap's buckles;
- `hang` metres between the spots answered along the run (where a string's lanterns or a cable's tags hang);
  `pennants` {`wide`, `drop`, `thick`} a bunting's flags, one hanging from a flexible run at each of those spots:
  a triangle `wide` along the run under it and `drop` deep, `thick` through (PENNANT's sizes by default).

Parts: the run's own (RUN_PART: `pipe`, `hose`, `cable`, `strap`, `bar`, `tray`, `rail`), `fitting` (a rigid run's
elbow sleeve at each bend over ELBOW_TURN, its collars and caps, a hose's cuffs), `bracket` (wall clamps, a bundle's
ties, a railing's base plates), `post` (a railing's posts), `infill` (its bars or glass), `buckle` and `pennant`. Each wears
its own library surface when laid (place_build.pipe).
"""
import json
import math

import numpy as np

from score.stages.place_build import cockpit_kit

PROFILES = ("round", "corrugated", "cord", "bundle", "flat", "box", "channel", "railing")
RUN_PART = {"round": "pipe", "corrugated": "hose", "cord": "cable", "bundle": "cable", "flat": "strap", "box": "bar",
            "channel": "tray", "railing": "rail"}
RIGID = ("round", "box", "channel", "railing")  # the sections that bend only at an elbow and never sag
BEND_RADII = 2.5  # a rigid run's bend radius in its own radii (a long-radius elbow: 1.5 pipe diameters)
FLEXIBLE_RADII = 8.0  # a cable's, cord's or hose's (its least bend radius, a few times its diameter, and more)
ELBOW_TURN = 30.0  # degrees: a rigid run's bend over this carries an elbow sleeve (thin_straight's ELBOW_TURN)
FITTING_SHARE = 1.25  # an elbow's, collar's or cap's radius in the run's (thin_straight's FITTING_SHARE)
CLAMP_SHARE = 1.06  # a clamp's inner radius in the run's: it holds the run, never cuts it (thin_straight's)
BRACKET_GAP = 1.5  # metres between a run's wall brackets (thin_straight's BRACKET_GAP)
TIE_GAP = 0.3  # metres between a bundle's ties
POST_GAP = 1.5  # metres: the most between a railing's posts (thin_straight's POST_GAP)
RIDGE_DEPTH = 0.12  # a corrugated hose's ridges, a share of its radius over its troughs
RIDGE_PITCH = 2.4  # its ridges' pitch in its own radii, when none is given
RIDGE_RINGS = 6  # rings swept a ridge
SAG_STEP = 0.1  # metres between a hanging run's points
LEAST_TURN = 1.0  # degrees: a corner turning less is no bend
BAR_GLASS = 0.012  # metres: a railing's glass infill's thickness
INFILL_LOW = 0.1  # metres over the floor a railing's infill starts
BARS_GAP = 0.12  # metres between a railing's bars (a building code's 0.1 m sphere does not pass)
BAR_RADIUS = 0.008  # metres: a railing's bar's radius, when none is given
PENNANT = {"wide": 0.2, "drop": 0.25, "thick": 0.002}  # metres: a bunting flag's, when its sizes are not given


def segments_of(radius):
    """Points round a round section of `radius`: a thin cord's few, a big pipe's many."""
    return 10 if radius < 0.008 else 16 if radius < 0.03 else 24 if radius < 0.15 else 32


def unit(vector):
    vector = np.asarray(vector, dtype=np.float64)
    return vector / max(np.linalg.norm(vector), 1e-12)


def corners_rounded(points, bend):
    """The polyline `points` with each corner turning over LEAST_TURN rounded on an arc of `bend` metres (less where
    its legs are short: a corner takes at most 0.45 of each leg); the bends' arcs [(points, degrees)] beside it."""
    points = [np.asarray(point, dtype=np.float64) for point in points]
    laid, bends = [points[0]], []
    for before, corner, after in zip(points, points[1:], points[2:]):
        back, ahead = corner - before, after - corner
        into, out = unit(back), unit(ahead)
        turn = math.degrees(math.acos(float(np.clip(into @ out, -1.0, 1.0))))
        if turn < LEAST_TURN or bend <= 0:
            laid.append(corner)
            continue
        half = math.tan(math.radians(turn) / 2)
        reach = min(bend * half, 0.45 * np.linalg.norm(back), 0.45 * np.linalg.norm(ahead))
        radius = reach / half
        start = corner - into * reach
        toward = unit(out - (into @ out) * into)  # from the arc's start to its centre
        centre = start + toward * radius
        steps = max(2, math.ceil(turn / 10.0))
        arc = [centre + radius * (-math.cos(angle) * toward + math.sin(angle) * into)
               for angle in np.linspace(0.0, math.radians(turn), steps + 1)]
        laid += arc
        bends.append((np.asarray(arc), turn))
    laid.append(points[-1])
    return np.asarray(laid), bends


def catenary(start, end, sag, up=(0.0, 1.0, 0.0)):
    """Points from `start` to `end` hanging `sag` metres at their middle along a catenary of their span (a cable's
    own curve, never a parabola's), SAG_STEP apart."""
    start, end, up = (np.asarray(value, dtype=np.float64) for value in (start, end, up))
    span = float(np.linalg.norm(end - start))
    count = max(8, math.ceil(span / SAG_STEP))
    along = np.linspace(0.0, 1.0, count + 1)
    if sag <= 0 or span <= 0:
        return start + np.outer(along, end - start)
    low, high = span * 1e-3, span * 1e4  # the catenary's parameter: sag = a (cosh(span / 2a) - 1), falling in a
    for _ in range(200):
        middle = math.sqrt(low * high)
        drop = middle * (math.cosh(min(span / (2 * middle), 700.0)) - 1)
        low, high = (middle, high) if drop > sag else (low, middle)
    parameter = math.sqrt(low * high)
    hang = parameter * (math.cosh(span / (2 * parameter)) - np.cosh((along - 0.5) * span / parameter))
    return start + np.outer(along, end - start) - np.outer(hang, up)


def resampled(points, step):
    """The polyline `points` walked again at points no more than `step` apart (its own points kept)."""
    found = [points[0]]
    for start, end in zip(points, points[1:]):
        count = max(1, math.ceil(np.linalg.norm(end - start) / step))
        found += [start + (end - start) * share for share in np.linspace(0.0, 1.0, count + 1)[1:]]
    return np.asarray(found)


def frames(points, face=(0.0, 1.0, 0.0)):
    """Each point's (tangent, normal, binormal) along the polyline, the normal carried along it without twist
    (parallel transport) from `face` set square to the first tangent (another way when the run starts along it)."""
    tangents = np.gradient(points, axis=0)
    tangents = tangents / np.maximum(np.linalg.norm(tangents, axis=1, keepdims=True), 1e-12)
    face = unit(face)
    if abs(face @ tangents[0]) > 0.99:
        face = unit([1.0, 0.0, 0.0]) if abs(tangents[0][0]) < 0.9 else unit([0.0, 0.0, 1.0])
    normal = unit(face - (face @ tangents[0]) * tangents[0])
    found = []
    for tangent in tangents:
        normal = unit(normal - (normal @ tangent) * tangent)
        found.append((tangent, normal, np.cross(tangent, normal)))
    return found


def band(part, rings, loop):
    """A band through `rings` (R x K x 3, each ring K points round or across), closed round when `loop`, each face
    wound to look away from its ring's middle; shaded smooth."""
    rings = np.asarray(rings, dtype=np.float64)
    count, across = rings.shape[:2]
    points = rings.reshape(-1, 3)
    triangles = []
    for ring in range(count - 1):
        for step in range(across if loop else across - 1):
            here, there = ring * across + step, ring * across + (step + 1) % across
            triangles += [[here, there, there + across], [here, there + across, here + across]]
    triangles = np.asarray(triangles)
    middles = np.repeat(rings.mean(axis=1), across, axis=0)
    corners = points[triangles]
    normals = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
    outward = corners.mean(axis=1) - middles[triangles[:, 0]]
    flip = np.einsum("ij,ij->i", normals, outward) < 0
    triangles[flip] = triangles[flip][:, ::-1]
    return cockpit_kit.piece(part, points, triangles, True)


def cap(part, ring, outward):
    """A flat cap over the convex `ring` (K x 3), looking along `outward`."""
    points = np.vstack([ring, np.mean(ring, axis=0)[None]])
    count = len(ring)
    triangles = np.array([[count, step, (step + 1) % count] for step in range(count)])
    return cockpit_kit.piece(part, points, cockpit_kit.oriented(points, triangles, outward), False)


def swept(part, points, section, face=(0.0, 1.0, 0.0), scales=None, sharp=False):
    """A closed solid swept along `points` with `section` [(u, v)] (a convex outline across the run: u along the
    binormal, v along the normal), each ring scaled by `scales`; `sharp`: each side of the outline its own band, so a
    bar's edges stay sharp and its faces flat across."""
    section = np.asarray(section, dtype=np.float64)
    scales = np.ones(len(points)) if scales is None else np.asarray(scales, dtype=np.float64)
    laid = frames(points, face)
    rings = np.asarray([point + scale * (section[:, :1] * binormal + section[:, 1:] * normal)
                        for point, scale, (_, normal, binormal) in zip(points, scales, laid)])
    if sharp:
        sides = len(section)
        pieces = [band(part, rings[:, [side, (side + 1) % sides]], False) for side in range(sides)]
    else:
        pieces = [band(part, rings, True)]
    pieces.append(cap(part, rings[0], -laid[0][0]))
    pieces.append(cap(part, rings[-1], laid[-1][0]))
    return pieces


def round_section(radius):
    angles = np.linspace(0.0, 2 * math.pi, segments_of(radius) + 1)[:-1]
    return np.column_stack([radius * np.cos(angles), radius * np.sin(angles)])


def rectangle(wide, deep, low=None):
    """A rectangle `wide` across and `deep` along the normal, centred, or from `low` up along the normal."""
    bottom = -deep / 2 if low is None else low
    return [(-wide / 2, bottom), (wide / 2, bottom), (wide / 2, bottom + deep), (-wide / 2, bottom + deep)]


def ring_on(part, centre, tangent, inner, outer, long):
    """A short ring (a collar, a clamp, a tie) of `inner` to `outer` radius and `long` along `tangent` round
    `centre`: a closed solid (cockpit_kit.turned's profile out, up, in, down)."""
    profile = [(inner, -long / 2), (outer, -long / 2), (outer, long / 2), (inner, long / 2), (inner, -long / 2)]
    tangent = unit(tangent)
    side = unit(np.cross(tangent, [0.0, 1.0, 0.0] if abs(tangent[1]) < 0.9 else [1.0, 0.0, 0.0]))
    turn = np.column_stack([side, np.cross(tangent, side), tangent])
    return cockpit_kit.moved(cockpit_kit.turned(part, profile, segments_of(outer)), turn, centre)


def along(points, gap, first=None):
    """The spots `gap` metres apart along the polyline (from `first`, half a gap by default) and the run's way at
    each: [(point, tangent)]."""
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    reach = np.concatenate([[0.0], np.cumsum(lengths)])
    found = []
    for at in np.arange(gap / 2 if first is None else first, reach[-1], gap):
        piece = min(int(np.searchsorted(reach, at, side="right")) - 1, len(lengths) - 1)
        way = (points[piece + 1] - points[piece]) / max(lengths[piece], 1e-12)
        found.append((points[piece] + way * (at - reach[piece]), way))
    return found


def bracket(centre, tangent, wall, stand, radius):
    """A wall bracket at `centre`: a clamp round the run, a stand-off bar to the wall `stand` metres along `wall` and
    a plate on the wall's face (part `bracket`)."""
    wall = unit(np.asarray(wall) - (np.asarray(wall) @ unit(tangent)) * unit(tangent))
    long = max(0.02, radius * 0.6)
    found = ring_on("bracket", centre, tangent, radius * CLAMP_SHARE, radius * CLAMP_SHARE + max(0.003, radius * 0.15),
                    long)
    across = np.cross(wall, unit(tangent))
    turn = np.column_stack([unit(tangent), across, wall])
    bar = max(0.01, radius * 0.5)
    outer = radius * CLAMP_SHARE + max(0.003, radius * 0.15)
    if stand > outer + 0.002:
        found += cockpit_kit.moved(cockpit_kit.box("bracket", (-long / 2, -bar / 2, outer * 0.9),
                                                   (long / 2, bar / 2, stand - 0.004), 0.001), turn, centre)
    plate = max(0.03, outer * 1.4)
    found += cockpit_kit.moved(cockpit_kit.box("bracket", (-plate / 2, -plate / 2, stand - 0.004),
                                               (plate / 2, plate / 2, stand), 0.001), turn, centre)
    return found


def bundle_offsets(count, radius):
    """Where each of a bundle's `count` cables lies across it ([u, v]) and its radius: packed in a hexagonal grid
    from the middle out, each a little thinner or thicker than the next (a harness of several gauges)."""
    grid = [(column + row / 2, row * math.sqrt(3) / 2) for row in range(-3, 4) for column in range(-3, 4)]
    grid.sort(key=lambda spot: (round(spot[0] ** 2 + spot[1] ** 2, 6), math.atan2(spot[1], spot[0])))
    spots = np.asarray(grid[:count]) * 2.05 * radius
    spots -= spots.mean(axis=0)
    radii = [radius * (1.0 - 0.18 * ((number * 3) % 4) / 3) for number in range(count)]
    return spots, radii


def run_path(points, spec, bend):
    """The run's centreline: each two points hung on a catenary by `sag` (a flexible run), its corners rounded."""
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 2:
        raise ValueError("a run needs a path of two points or more")
    sag = float(spec.get("sag") or 0.0)
    if sag > 0:
        if spec["profile"] in RIGID:
            raise ValueError(f"a {spec['profile']} run is rigid: it does not sag")
        hung = [catenary(start, end, sag) for start, end in zip(points, points[1:])]
        points = np.vstack([hung[0]] + [stretch[1:] for stretch in hung[1:]])
    return corners_rounded(points, bend)


def round_run(points, bends, spec, radius):
    """A rigid round run: the pipe, an elbow sleeve over each bend over ELBOW_TURN, collars every `joints` metres,
    caps on its ends."""
    found = swept("pipe", points, round_section(radius))
    sleeve = round_section(radius * FITTING_SHARE)
    for arc, turn in bends:
        if turn > ELBOW_TURN:
            way_in, way_out = unit(arc[1] - arc[0]), unit(arc[-1] - arc[-2])
            legs = np.vstack([arc[0] - way_in * radius, arc, arc[-1] + way_out * radius])
            found += swept("fitting", legs, sleeve)
    if spec.get("joints"):
        for centre, way in along(points, float(spec["joints"]), first=float(spec["joints"])):
            found += ring_on("fitting", centre, way, radius * 0.98, radius * FITTING_SHARE, radius * 1.6)
    if spec.get("caps"):
        for end, way in ((points[0], unit(points[0] - points[1])), (points[-1], unit(points[-1] - points[-2]))):
            found += swept("fitting", np.asarray([end - way * radius * 0.3, end + way * radius * 0.4]),
                           round_section(radius * FITTING_SHARE))
    return found


def corrugated_run(points, spec, radius):
    """A ridged hose: its troughs `radius` round, its ridges RIDGE_DEPTH over them every `pitch` metres, a smooth
    cuff at each end (part `fitting`)."""
    pitch = float(spec.get("pitch") or radius * RIDGE_PITCH)
    dense = resampled(points, pitch / RIDGE_RINGS)
    reach = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(dense, axis=0), axis=1))])
    scales = 1.0 + RIDGE_DEPTH * (0.5 - 0.5 * np.cos(2 * math.pi * reach / pitch))
    found = swept("hose", dense, round_section(radius), scales=scales)
    cuff = round_section(radius * FITTING_SHARE)
    for end, way in ((dense[0], unit(dense[1] - dense[0])), (dense[-1], unit(dense[-2] - dense[-1]))):
        found += swept("fitting", np.asarray([end - way * radius * 0.2, end + way * radius * 2.5]), cuff)
    return found


def bundle_run(points, spec, radius):
    """A harness of `count` cables laid side by side along the run, tied every `clamps` metres (part `bracket`)."""
    count = int(spec.get("count") or 3)
    if not 1 <= count <= 19:
        raise ValueError(f"a bundle holds 1 to 19 cables, not {count}")
    spots, radii = bundle_offsets(count, radius)
    face = spec.get("face") or (0.0, 1.0, 0.0)
    laid = frames(points, face)
    found = []
    for (u, v), cable_radius in zip(spots, radii):
        shifted = np.asarray([point + u * binormal + v * normal for point, (_, normal, binormal) in zip(points, laid)])
        found += swept("cable", shifted, round_section(cable_radius))
    envelope = float(max(np.hypot(u, v) + cable_radius for (u, v), cable_radius in zip(spots, radii)))
    for centre, way in along(points, float(spec.get("clamps") or TIE_GAP)):
        found += ring_on("bracket", centre, way, envelope * CLAMP_SHARE, envelope * CLAMP_SHARE + 0.0025, 0.008)
    return found, envelope


def sectioned_run(points, spec):
    """A flat strap, a box bar or an open tray swept along the run, its section's depth along `face`; a strap's
    buckles on it."""
    profile, face = spec["profile"], spec.get("face") or (0.0, 1.0, 0.0)
    wide = float(spec.get("wide") or 0.04)
    if profile == "flat":
        thick = float(spec.get("thick") or 0.003)
        found = swept("strap", points, rectangle(wide, thick), face, sharp=True)
        laid = frames(points, face)
        for buckle in spec.get("buckles") or ():
            nearest = int(np.argmin(np.linalg.norm(points - np.asarray(buckle, dtype=np.float64), axis=1)))
            tangent, normal, binormal = laid[nearest]
            turn = np.column_stack([binormal, normal, tangent])
            found += cockpit_kit.moved(cockpit_kit.box("buckle", (-wide * 0.65, -thick * 1.5, -wide * 0.5),
                                                       (wide * 0.65, thick * 2.5, wide * 0.5), 0.001),
                                       turn, points[nearest])
        return found, max(wide, thick) / 2
    deep = float(spec.get("deep") or wide)
    if profile == "box":
        return swept("bar", points, rectangle(wide, deep), face, sharp=True), max(wide, deep) / 2
    thick = float(spec.get("thick") or 0.002)
    if not 2 * thick < wide and thick < deep:
        raise ValueError(f"a channel's sheet ({thick} m) must be thinner than half its width and its depth")
    found = swept("tray", points, rectangle(wide - thick, thick, -deep / 2), face, sharp=True)
    for side in (-1, 1):
        middle = side * (wide - thick) / 2
        outline = [(middle - thick / 2, -deep / 2), (middle + thick / 2, -deep / 2), (middle + thick / 2, deep / 2),
                   (middle - thick / 2, deep / 2)]
        found += swept("tray", points, outline, face, sharp=True)
    return found, max(wide, deep) / 2


def post_feet(points, gap):
    """A railing's posts' feet: at each of its path's points and evenly between, at most `gap` metres apart."""
    feet = [points[0]]
    for start, end in zip(points, points[1:]):
        count = max(1, math.ceil(np.linalg.norm(end - start) / gap - 1e-9))
        feet += [start + (end - start) * share for share in np.linspace(0.0, 1.0, count + 1)[1:]]
    return np.asarray(feet)


def railing_run(points, spec):
    """A railing on the floor line `points` (its feet; up a flight it climbs with them): round posts at most `posts`
    metres apart, each on a base plate, a top rail `high` over the feet and a rail at each of `rails`, and its
    `infill` (bars BARS_GAP apart or a glass pane) between each two posts."""
    high = float(spec.get("high") or 1.0)
    post = float(spec.get("post") or 0.022)
    rail = float(spec.get("rail") or 0.02)
    gap = float(spec.get("posts") or POST_GAP)
    infill = spec.get("infill") or "none"
    bar = float(spec.get("bar") or BAR_RADIUS)
    if infill not in ("none", "bars", "glass"):
        raise ValueError(f"a railing's infill is none, bars or glass, not {infill}")
    heights = sorted({float(height) for height in spec.get("rails") or (high * 0.5,)} | {high})
    if heights[0] <= 0 or heights[-1] > high:
        raise ValueError(f"a railing's rails stand over its feet and no higher than its top rail ({heights})")
    up = np.array([0.0, 1.0, 0.0])
    found = []
    for height in heights:
        laid, _ = corners_rounded(points + up * height, rail * BEND_RADII)
        found += swept("rail", laid, round_section(rail))
    feet = post_feet(points, gap)
    for foot in feet:
        found += swept("post", np.asarray([foot, foot + up * (high - rail * 0.5)]), round_section(post))
        plate = post * 3.2
        found += cockpit_kit.box("bracket", foot + (-plate / 2, 0.0, -plate / 2), foot + (plate / 2, 0.008, plate / 2),
                                 0.001)
    for start, end in zip(feet, feet[1:]):
        if infill == "bars":
            span = float(np.linalg.norm((end - start)[[0, 2]]))
            for share in np.linspace(0.0, 1.0, max(2, math.ceil(span / BARS_GAP)) + 1)[1:-1]:
                foot = start + (end - start) * share
                found += swept("infill", np.asarray([foot + up * INFILL_LOW, foot + up * (high - rail)]),
                               round_section(bar))
        elif infill == "glass":
            found += pane(start, end, post, high - rail * 1.5)
    return found, max(post, rail)


def pane(start, end, post, top):
    """A glass pane between two posts' feet (sloped with them up a flight): BAR_GLASS thick, from INFILL_LOW over
    them to `top`, clear of the posts (part `infill`)."""
    way = end - start
    level = unit([way[0], 0.0, way[2]])
    across = np.cross(level, [0.0, 1.0, 0.0]) * BAR_GLASS / 2
    inset = unit(way) * (post + 0.01)
    low_start, low_end = start + inset, end - inset
    corners = []
    for foot in (low_start, low_end):
        for height in (INFILL_LOW, top):
            for side in (-1, 1):
                corners.append(foot + np.array([0.0, height, 0.0]) + side * across)
    corners = np.asarray(corners)  # 0..7: foot (start, end) x height (low, high) x side
    quads = ([0, 1, 3, 2], [4, 6, 7, 5], [0, 4, 5, 1], [2, 3, 7, 6], [0, 2, 6, 4], [1, 5, 7, 3])
    middle = corners.mean(axis=0)
    found = []
    for quad in quads:
        points = corners[list(quad)]
        found.append(cockpit_kit.piece("infill", points, cockpit_kit.oriented(
            points, np.array([[0, 1, 2], [0, 2, 3]]), points.mean(axis=0) - middle), False))
    return found


def one_run(points, spec):
    """One run's pieces and its laid centreline, its section's reach from it (for its brackets)."""
    profile = spec["profile"]
    radius = float(spec.get("radius") or 0.02)
    if radius <= 0:
        raise ValueError(f"a run's radius must be over 0 ({radius})")
    flexible = profile in ("corrugated", "cord", "bundle")
    bend = float(spec["bend"]) if spec.get("bend") is not None else radius * (FLEXIBLE_RADII if flexible else
                                                                               BEND_RADII)
    if profile == "railing":
        points = np.asarray(points, dtype=np.float64)
        found, reach = railing_run(points, spec)
        return found, points, reach
    laid, bends = run_path(points, spec, bend)
    if profile == "round":
        return round_run(laid, bends, spec, radius), laid, radius
    if profile == "corrugated":
        return corrugated_run(laid, spec, radius), laid, radius * (1 + RIDGE_DEPTH)
    if profile == "cord":
        return swept("cable", laid, round_section(radius)), laid, radius
    if profile == "bundle":
        found, envelope = bundle_run(laid, spec, radius)
        return found, laid, envelope
    found, reach = sectioned_run(laid, spec)
    return found, laid, reach


def pennants(laid, spec, radius):
    """A bunting's flags along the hanging centreline `laid`: at each spot `hang` metres apart a closed triangular
    sheet in the run's upright plane, its top edge along the run's underside (`radius` under its centreline), its
    tip `drop` under that (part `pennant`)."""
    if not spec.get("hang"):
        raise ValueError("a bunting's pennants hang at its `hang` spots: give it a `hang`")
    if spec["profile"] in RIGID:
        raise ValueError(f"pennants hang from a flexible run, not a {spec['profile']} one")
    sizes = {**PENNANT, **spec["pennants"]} if isinstance(spec["pennants"], dict) else dict(PENNANT)
    wide, drop, thick = (float(sizes[key]) for key in ("wide", "drop", "thick"))
    if min(wide, drop, thick) <= 0 or wide > float(spec["hang"]):
        raise ValueError(f"a pennant is over 0 in every size and no wider than its `hang` ({sizes})")
    found = []
    for centre, way in along(laid, float(spec["hang"])):
        level = unit([way[0], 0.0, way[2]]) if np.hypot(way[0], way[2]) > 1e-6 else np.array([1.0, 0.0, 0.0])
        across = np.cross(level, [0.0, 1.0, 0.0])
        sheet = np.asarray([centre - across * thick / 2, centre + across * thick / 2])
        outline = [(-wide / 2, -radius), (0.0, -radius - drop), (wide / 2, -radius)]
        found += swept("pennant", sheet, outline, face=(0.0, 1.0, 0.0), sharp=True)
    return found


def pieces_of(spec):
    """Every piece of the runs `spec` names and their laid centrelines."""
    if spec.get("profile") not in PROFILES:
        raise ValueError(f"a run's profile is one of {', '.join(PROFILES)}, not {spec.get('profile')!r}")
    paths = spec.get("paths") or ([spec["path"]] if spec.get("path") else [])
    if not paths:
        raise ValueError("a run needs a `path` or `paths`")
    found, centrelines = [], []
    for points in paths:
        pieces, laid, reach = one_run(points, spec)
        found += pieces
        centrelines.append(laid)
        if spec.get("pennants"):
            found += pennants(laid, spec, float(spec.get("radius") or 0.02))
        if spec.get("wall") is not None and spec["profile"] != "railing":
            stand = float(spec.get("stand") or reach + 0.02)
            if stand <= reach:
                raise ValueError(f"a run held {stand} m off its wall must stand clear of it (its reach {reach:.3f} m)")
            for centre, way in along(laid, float(spec.get("brackets") or BRACKET_GAP)):
                found += bracket(centre, way, wall_way(spec["wall"], centre), stand, reach)
    return found, centrelines


def wall_way(wall, centre):
    """The way from a bracket at `centre` to its wall: `wall` itself ([x, y, z]), or for a round wall {"axis": [x, z],
    "side": "out" | "in"} level from that upright axis, outward for a run inside a round wall (a capsule's lining)
    and inward for one outside it (a silo's pipes)."""
    if not isinstance(wall, dict):
        return wall
    if wall.get("side") not in ("out", "in"):
        raise ValueError(f"a round wall's side is out or in, not {wall.get('side')!r}")
    axis = np.asarray(wall["axis"], dtype=np.float64)
    level = np.array([centre[0] - axis[0], 0.0, centre[2] - axis[1]])
    if np.linalg.norm(level) < 1e-6:
        raise ValueError("a run on a round wall cannot stand on its axis")
    return unit(level) * (1.0 if wall["side"] == "out" else -1.0)


def spots_of(centrelines, hang):
    """The spots `hang` metres apart along every run (half a gap in from its start), rounded to the millimetre."""
    return [[round(float(value), 4) for value in point] for laid in centrelines for point, _ in along(laid, hang)]


def write(path, spec):
    """The run of `spec` (the module's docstring) written at `path` as one piece file (cockpit_kit.written: /piece
    with one mesh `geo`, a GeomSubset a part, a placeholder look on each); its answer {"parts", "length" (metres of
    centreline), "spots" (every `hang` metres along it, its own frame)}, also written beside it as `<path>.json` so a
    cached file answers alike."""
    pieces, centrelines = pieces_of(spec)
    parts = cockpit_kit.written(path, pieces)
    length = sum(float(np.linalg.norm(np.diff(laid, axis=0), axis=1).sum()) for laid in centrelines)
    answer = {"parts": parts, "length": round(length, 4),
              "spots": spots_of(centrelines, float(spec["hang"])) if spec.get("hang") else []}
    with open(f"{path}.json", "w") as handle:
        json.dump(answer, handle)
    return answer
