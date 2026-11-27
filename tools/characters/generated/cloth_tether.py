"""A garment's loose cloth as tethered secondary motion, as games move clothes (#223; coordinator 2026-11-26, after two
free cloth rounds on Newton's VBD tore the jeans down to the shoes and shredded the jacket: "stop free simulation").

Each sim point has a target, its skinned place (still_rig's weights, which walk cleanly) and is simulated but never
leaves it by more than its tether (`tethers`): none on the pinned points (`pinned`: the riding ones, the jacket's
collar, yoke and cuffs and the jeans' waistband, and a hem near the shoes; a hem never hangs on a shoe), rising over the
surface from them by SLOPE to TETHER_M over the loose cloth (the jacket's hem, the wide jeans' legs). A soft pull
draws each point back toward its target (PULL a substep at the longest tether, more as the tether shortens). The cloth feels
only the gravity its limb's turn adds to the hang its made shape already has (`turned_gravity`): the wide leg's back
panel, turned up behind the calf with the shin at the passing step, is pulled back down, while a jacket on an upright
trunk does not sag a tether's length. The body keeps it out (`retracted`: a point deeper than half the garment's
thickness, or than its skinned place where the skinning itself draws it inside, is drawn back toward its target, never
pushed sideways), and the edges keep the target's own lengths that frame, so the cloth is as stable as the skinning
and only swings and sags inside its tether.

Position-based (Mueller et al. 2007, "Position based dynamics"; the max distance and backstop of game cloth): numpy
on the processor, one step SUBSTEPS times a frame, the edges ITERATIONS times a substep, deterministic.
"""
import numpy as np
from scipy.spatial import cKDTree

TETHER_M = {"jacket": 0.05, "jeans": 0.06, "scarf": 0.04}  # the most a loose point may leave its target (cloth.py's
# --tether gives a garment its own: an open overshirt's fronts and a long coat's hem swing further)
SLOPE = 0.25  # a tether grows by this over each metre of surface from the nearest pinned point
HEM_M = 0.02  # a jeans point this near the shoes at rest is pinned
PULL = 0.005  # a substep's share of the way back toward the target at the longest tether (over its tether nearer)
DAMPING = 0.2  # a substep's share of the speed against its target's lost
SUBSTEPS = 10
NEIGHBOURS = 8  # body points asked whether a point is inside
ITERATIONS = 3
GRAVITY = np.array([0.0, -9.81, 0.0])


def edges_of(faces):
    """The mesh's unique edges (pairs of point numbers)."""
    pairs = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    return np.unique(np.sort(pairs, axis=1), axis=0)


def pinned(points, riding, shoes):
    """The points held to their targets: the riding ones and a hem within HEM_M of the shoes (`shoes`: the shoes'
    points at rest, the same frame as `points`). Hems never hang on the shoes; they only follow the skinned leg."""
    near = cKDTree(shoes).query(points)[0] < HEM_M if len(shoes) else np.zeros(len(points), bool)
    return riding | near


def tethers(longest, from_pinned):
    """Each sim point's tether (metres): SLOPE times its distance over the surface from the nearest pinned point, at
    most `longest` (the garment's TETHER_M or its own; a tether rising faster than its edges are long let a hem point beside a held one hang 4 mm off it
    on a 7 mm edge, half again its length; round 3, 2026-11-26)."""
    return np.minimum(longest, SLOPE * from_pinned)


def vertex_normals(points, faces):
    """Area-weighted unit normals at each point."""
    crossed = np.cross(points[faces[:, 1]] - points[faces[:, 0]], points[faces[:, 2]] - points[faces[:, 0]])
    normals = np.zeros_like(points)
    for corner in range(3):
        np.add.at(normals, faces[:, corner], crossed)
    return normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)


def outside(positions, body_points, body_normals):
    """How far each point lies outside the body (metres, negative inside) and the nearest body point's normal. A point
    is as far out as the most outside of its NEIGHBOURS nearest body points' planes says: one nearest point's plane
    alone put a hem 9 cm out beside the foot 9 cm inside (the sole's normal; round 3, 2026-11-26)."""
    nearest = cKDTree(body_points).query(positions, k=list(range(1, NEIGHBOURS + 1)))[1]
    over = np.einsum("pkd,pkd->pk", positions[:, None] - body_points[nearest], body_normals[nearest]).max(1)
    return over, body_normals[nearest[:, 0]]


def allowances(skinned, body, faces, clearance):
    """Each frame's least each point must lie outside the body (frames, points): `clearance`, or as deep as its
    plain skinned place lies where that is inside (the cloth is never pushed past what skinning draws: a push to the
    clearance from 5 cm inside tore an edge five times over against its neighbour; round 3, 2026-11-26)."""
    return np.stack([np.minimum(clearance, outside(points, frame, vertex_normals(frame, faces))[0])
                     for points, frame in zip(skinned, body)])


def retracted(positions, targets, body_points, body_normals, least):
    """`positions` drawn back toward their targets (which keep `least` outside the body) where they lie deeper than
    `least`: by the share of the way the body's planes say reaches `least`, never sideways. A push out along the
    nearest body point's normal moved a jeans point between the legs sideways off its neighbours and tore an edge two
    and a half times over (round 3, 2026-11-26)."""
    over, _ = outside(np.concatenate([positions, targets]), body_points, body_normals)
    over_now, over_target = over[:len(positions)], over[len(positions):]
    share = np.where(over_now < least, (over_target - least) / np.maximum(over_target - over_now, 1e-12), 1.0)
    share = np.clip(share, 0.0, 1.0)
    return targets + (positions - targets) * share[:, None]


def held(positions, targets, tether):
    """`positions` drawn back onto the sphere of radius `tether` round each target where outside it."""
    off = positions - targets
    length = np.linalg.norm(off, axis=1)
    scale = np.where(length > tether, tether / np.maximum(length, 1e-12), 1.0)
    return targets + off * scale[:, None]


def edges_kept(positions, edges, lengths, weight):
    """One Jacobi pass of the edge constraints toward `lengths`; a point of weight 0 never moves."""
    off = positions[edges[:, 1]] - positions[edges[:, 0]]
    now = np.linalg.norm(off, axis=1)
    share = weight[edges[:, 0]] + weight[edges[:, 1]]
    fix = np.where(share > 0, (now - lengths) / np.maximum(now * share, 1e-12), 0.0)[:, None] * off
    moves = np.zeros_like(positions)
    counts = np.zeros(len(positions))
    np.add.at(moves, edges[:, 0], fix * weight[edges[:, 0], None])
    np.add.at(moves, edges[:, 1], -fix * weight[edges[:, 1], None])
    np.add.at(counts, edges.ravel(), 1.0)
    return positions + moves / np.maximum(counts, 1.0)[:, None] * 1.5


def turned_gravity(weights, moves):
    """The gravity a point feels beyond the one its rest shape already hangs under (frames, points, 3): g less g turned
    by the point's skinned turn. The made shape is the garment hanging on the standing body, so a point whose limb
    has not turned feels none (all of g sagged the jacket a tether's length at rest), and the wide leg's back panel,
    turned up behind the calf with the shin at the passing step, feels most of g pulling it back down."""
    turns = np.einsum("pj,fjab->fpab", weights, moves[:, :, :3, :3])
    return GRAVITY[None, None] - np.einsum("fpab,b->fpa", turns, GRAVITY)


def tethered(targets, tether, faces, body, body_faces, rate, least, gravity):
    """The cloth over the run (frames, points, 3) from its targets (frames, points, 3), each point's tether, the posed
    body (frames, body points, 3) it stays outside by its `allowances`, and the gravity it feels (`turned_gravity`),
    starting at rest on its first target. Its speed is damped against its target's (damping the speed itself held a
    walking jeans leg behind its target at the tether, and each clamp showed as jitter)."""
    edges = edges_of(faces)
    loose = tether > 0
    weight = loose.astype(float)
    pull = np.where(loose, np.minimum(1.0, PULL * tether.max() / np.maximum(tether, 1e-12)), 0.0)
    step = 1.0 / (rate * SUBSTEPS)
    position = targets[0].copy()
    previous = position.copy()
    last_target = position.copy()
    found = [position.copy()]
    for frame in range(1, len(targets)):
        for sub in range(1, SUBSTEPS + 1):
            share = sub / SUBSTEPS
            target = targets[frame - 1] * (1.0 - share) + targets[frame] * share
            posed = body[frame - 1] * (1.0 - share) + body[frame] * share
            floor = least[frame - 1] * (1.0 - share) + least[frame] * share
            carried = target - last_target
            speed = carried + (position - previous - carried) * (1.0 - DAMPING)
            previous, last_target = position, target
            pulled = gravity[frame - 1] * (1.0 - share) + gravity[frame] * share
            moved = position + (speed + pulled * step * step) * weight[:, None]
            moved += (target - moved) * pull[:, None]
            lengths = np.linalg.norm(target[edges[:, 1]] - target[edges[:, 0]], axis=1)
            moved[loose] = retracted(moved[loose], target[loose], posed, vertex_normals(posed, body_faces),
                                     floor[loose])
            for _ in range(ITERATIONS):
                moved = edges_kept(moved, edges, lengths, weight)
            position = held(moved, target, tether)
        found.append(position.copy())
    return np.stack(found)
