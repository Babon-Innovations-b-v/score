"""A railing laid on its floor held to its row's height and cut back clear of the built walls it runs into, on the
made ground's place (after on_ground.stood, before tops_levelled.laid, so what stands on a top keeps clear of it as
it stands).

settle@greenhouse, 2026-11-13 (its inputs' seed laid with the resting triage as laid): its railing row (count 5, "inner
edge of upper floor", 1 m tall) is one model, Pixal3D's take traced as a code build, 9.4 m long and 4.5 m tall: its bake
took its parts as they were before 70c87a4a (props/railing_hold.py), which holds a railing that does not climb a
flight to its row's height when it is built, and those parts stay locked, so the bake kept the 4.5 m build. Its five
pieces, 9.4 m chords laid along the plan's octagon round the upper floor's middle, stood 4.5 m tall, their weight
0.122 m outside what they touch, and the first and fifth ran 0.12 and 0.14 m into wall_2_4 and wall_7_3. Each is now
held as railing_hold holds the build (`held`, the same rule: a no-op on a build already held); the first and fifth,
whose lowest stretch then stood over the upper floor's opening for its stair, slid along their chords to where their
weight stands within the resting check's BALANCE of what they touch; and each end that runs into a built wall drawn
back along the chord until it stands CLEAR of the wall, its other end where it was.

    held(row)                                whether a row's railings are held to its height (railing_hold's rule)
    cut_back(points, axis, hulls)            the share of its length a chord keeps at each end so none of its points
                                             is in a wall
    change(mesh, row, hulls, under)          its world change: held, slid along itself to where it stands, cut back
    laid(folder, place, rows)                each held row's railing of the place at `folder` laid by change; the
                                             fits [{name, how "held", ...}], laid.json written again
"""
import json
import pathlib
import re
import sys

import numpy as np

from score.stages.assembly import BASE_LAYER, RECORD, fitting, made_waiting

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# railing_hold's rule, its words and share read here as data: importing the props code would put thin_straight.py and
# what it reads in the key of every row that reads the assembly (settle, sim body, peels), as 70c87a4a kept it out of
# them. The test holds these to thin_straight.RAILING, railing_hold.CLIMBED and the model gate's SLENDER_SHARE.
RAILING = frozenset(("railing", "balustrade", "guardrail", "banister"))
CLIMBED = frozenset(("stair", "stairs", "staircase", "stairway", "steps", "ramp"))
SLENDER_SHARE = 0.25

# How far, metres, a chord's end stands clear of a built wall's face once cut back.
CLEAR = 0.02
# The least share of its length a chord keeps: one a wall would cut shorter is left for the resting gate to name.
KEPT_LEAST = 0.5
# How many halvings the share a chord keeps is found by (2^-20 of its length: well under a millimetre).
HALVINGS = 20
# A chord is slid along itself SLIDE_STEP metres at a time, SLIDE_MOST at most either way, to where it stands; it then
# stands with its weight at most the resting check's BALANCE less BALANCE_SPARE outside what it touches.
SLIDE_STEP = 0.05
SLIDE_MOST = 1.0
BALANCE_SPARE = 0.005
# Points sampled on a railing's surface beside its vertices, for its walls.
SAMPLES = 4000


def held(row):
    """Whether a row's railings are held to its row's height, as railing_hold.held holds its build: a word of its name
    or noun names a railing (RAILING, a plural's s dropped), none of its name, noun or anchor names a flight it climbs
    (CLIMBED), and its size is slender (its middle side SLENDER_SHARE of its longest at most)."""
    named = re.findall(r"[a-z]+", f"{row.get('name') or ''} {row.get('noun') or ''}".lower())
    climbing = named + re.findall(r"[a-z]+", str(row.get("anchor") or "").lower())
    smallest, middle, largest = sorted(float(value) for value in row["size"])
    return (bool(RAILING & {word[:-1] if word.endswith("s") and word[:-1] in RAILING else word for word in named})
            and not CLIMBED & set(climbing) and largest > 0 and middle / largest <= SLENDER_SHARE)


def inside(points, hulls):
    """Whether any of `points` [n, 3] lies within CLEAR of the inside of any of the convex `hulls` (scipy hulls)."""
    for hull in hulls:
        if np.any(np.all(points @ hull.equations[:, :3].T + hull.equations[:, 3] < CLEAR, axis=1)):
            return True
    return False


def drawn(points, axis, pivot, share):
    """`points` [n, 3] drawn along the unit `axis` towards `pivot` (a point) to `share` of their reach from it."""
    return points + np.outer((share - 1.0) * ((points - pivot) @ axis), axis)


def cut_back(points, axis, hulls):
    """(share kept from the far end, share kept from the near end) of a chord's `points` [n, 3] along its unit `axis`:
    each end in a wall (`hulls`) drawn back towards the other end, the most it keeps with none of its points in one,
    found by halving; 1.0 an end in no wall, None where it would keep less than KEPT_LEAST."""
    shares = []
    for way in (1.0, -1.0):
        along = points @ axis
        pivot = points[np.argmin(way * along)]  # the other end stays where it is
        near = way * (along - (along.min() + along.max()) / 2) > 0  # this end's half
        if not inside(points[near], hulls):
            shares.append(1.0)
            continue
        if inside(drawn(points, axis, pivot, KEPT_LEAST)[near], hulls):
            return None
        short, long = KEPT_LEAST, 1.0
        for _ in range(HALVINGS):
            middle = (short + long) / 2
            short, long = (middle, long) if not inside(drawn(points, axis, pivot, middle)[near], hulls) else \
                (short, middle)
        points = drawn(points, axis, pivot, short)
        shares.append(short)
    return tuple(shares)


def wall_hulls(stage, place):
    """The convex hulls of the place's built walls' world meshes (fitting.walls' pieces named wall)."""
    from scipy.spatial import ConvexHull, QhullError
    hulls = []
    for name, _ in fitting.walls(stage, place):
        if name.split("_")[0] != "wall":
            continue
        for scope in ("Structure", "Shell"):
            mesh = fitting.surface_mesh(stage, f"/{place}/{scope}/{name}") \
                if stage.GetPrimAtPath(f"/{place}/{scope}/{name}") else None
            if mesh is None or len(mesh.vertices) < 4:
                continue
            try:
                hulls.append(ConvexHull(np.asarray(mesh.vertices, float)))
            except QhullError:
                continue
    return hulls


def built_under(stage, place):
    """A reader of what is under points [n, 3] -> their gaps, metres, straight down to the place's built structure
    (its decks, stairs and walls) or its ground (resting.ground_height), the nearer; read from RAY_START over each
    point, as the resting check reads it, so a point bedded a little in its deck still finds the deck's top."""
    import resting
    import trimesh
    ground = resting.ground_height(stage, place)
    root = stage.GetPrimAtPath(f"/{place}/Structure")
    meshes = [mesh for mesh in (fitting.surface_mesh(stage, str(child.GetPath()))
                                for child in (root.GetChildren() if root else [])) if mesh is not None]
    built = trimesh.util.concatenate(meshes) if meshes else None

    def gaps(points):
        points = np.asarray(points, float)
        found = points[:, 1] - np.asarray(ground(points[:, [0, 2]]), float)
        found = np.where(np.isfinite(found), found, np.inf)
        if built is not None and len(built.faces):
            starts = points + [0.0, resting.RAY_START, 0.0]
            hits, rays, _ = built.ray.intersects_location(starts, np.tile([0.0, -1.0, 0.0], (len(points), 1)),
                                                          multiple_hits=False)
            if len(rays):
                found[rays] = np.minimum(found[rays], starts[rays, 1] - hits[:, 1] - resting.RAY_START)
        return np.abs(found)
    return gaps


def along_of(points):
    """The unit horizontal axis [3] a chord's points [n, 3] run along: their floor spread's main way."""
    flat = points[:, [0, 2]] - points[:, [0, 2]].mean(axis=0)
    way = np.linalg.svd(flat, full_matrices=False)[2][0]
    return np.array([way[0], 0.0, way[1]])


def held_up(points, row):
    """(row-vector change [4, 4], points [n, 3] after it) holding a railing's points to its `row`'s height about
    their foot (at most whole height: a railing built no taller is left)."""
    tall = float(np.ptp(points[:, 1]))
    keep = min(1.0, float(row["size"][2]) / max(tall, 1e-9))
    low = float(points[:, 1].min())
    up = np.eye(4)
    up[1, 1], up[3, 1] = keep, low * (1.0 - keep)  # row vectors: a point [x, y, z, 1] times this
    return up, points @ up[:3, :3] + up[3, :3]


def cut(points, axis, shares):
    """(row-vector change [4, 4], points after it) drawing each end of a chord's `points` back by cut_back's `shares`
    (the + end towards the - end, then the - end towards the + end)."""
    whole = np.eye(4)
    for share, sign in zip(shares, (1.0, -1.0)):
        pivot = points[np.argmin(sign * (points @ axis))]
        drawn_in = np.eye(4)
        drawn_in[:3, :3] += (share - 1.0) * np.outer(axis, axis)
        drawn_in[3, :3] = pivot - pivot @ drawn_in[:3, :3]
        whole = whole @ drawn_in
        points = drawn(points, axis, pivot, share)
    return whole, points


def outside_by(mesh, under):
    """How far, metres, a railing's weight (resting.weight_at) falls outside its low points (triage.low_points) that
    touch what is under them within triage.TOLERANCE (`under`: points [n, 3] -> gaps); inf touching fewer than
    triage.CONTACTS_NEEDED: the resting check's own tip measure."""
    import resting
    import triage
    from score.stages.assembly import footing
    low = np.asarray(triage.low_points(mesh), float)
    touching = low[under(low) <= triage.TOLERANCE]
    if len(touching) < triage.CONTACTS_NEEDED:
        return np.inf
    return -footing.inside_by(resting.weight_at(mesh), touching[:, [0, 2]])


def change(mesh, row, hulls, under):
    """(world change [4, 4] as fitting.changed_by takes it, its words) of one railing (`mesh`, its world surface):
    held up to its `row`'s height about its foot (held_up), slid along its chord the least, SLIDE_STEP at a time and
    SLIDE_MOST at most, to where its weight stands within the resting check's BALANCE (less BALANCE_SPARE) of what it
    touches on what is `under` it (outside_by: greenhouse's first and fifth railings stood over its stair's opening),
    and each end then cut back from the walls (`hulls`, cut_back) along it; None where nothing moves it by
    fitting.MOVE_LEAST, or a wall would cut it past KEPT_LEAST."""
    import triage
    points = np.vstack([mesh.vertices, mesh.sample(SAMPLES, seed=0)])
    tall = float(np.ptp(points[:, 1]))
    whole, points = held_up(points, row)
    axis = along_of(points)
    slides = sorted(np.arange(-SLIDE_MOST, SLIDE_MOST + SLIDE_STEP / 2, SLIDE_STEP), key=abs)
    for slide in slides:
        moved = points + axis * slide
        shares = cut_back(moved, axis, hulls)
        if shares is None:
            continue
        shift = np.eye(4)
        shift[3, :3] = axis * slide
        drawn_back, _ = cut(moved, axis, shares)
        candidate = whole @ shift @ drawn_back
        laid_mesh = mesh.copy()
        laid_mesh.apply_transform(candidate.T)
        if outside_by(laid_mesh, under) <= triage.BALANCE - BALANCE_SPARE:
            break
    else:
        slide, shares = 0.0, cut_back(points, axis, hulls)
        if shares is None:
            return None
        candidate = whole @ cut(points, axis, shares)[0]
    reach = float(np.ptp(points @ axis))
    words = [f"held to its row's {float(row['size'][2]):.2f} m from {tall:.2f} m"] if \
        tall - float(np.ptp(points[:, 1])) >= fitting.MOVE_LEAST else []
    if abs(slide) >= fitting.MOVE_LEAST:
        words.append(f"slid {slide:+.2f} m along itself to where it stands")
    words += [f"cut back {reach * (1.0 - share):.2f} m from the wall at one end" for share in shares
              if reach * (1.0 - share) >= fitting.MOVE_LEAST]
    return (candidate, "; ".join(words)) if words else None


def laid(folder, place, rows=None):
    """Each railing of a held row (by the inventory `rows`) of the place at `folder`, laid on the floor (no `on`),
    held to its row's height and cut back clear of the walls (change); the base layer saved and laid.json's boxes and
    fits written again. The fits, [] and nothing written when none moves."""
    from pxr import Gf, Sdf, Usd
    folder = pathlib.Path(folder)
    laid_path, record_path = folder / made_waiting.LAID, folder / RECORD
    if not rows or not laid_path.exists() or not record_path.exists():
        return []
    by_id = {row["id"]: row for row in rows if row.get("size") and held(row)}
    record = json.loads(record_path.read_text())
    entries = [entry for entry in record.get("objects") or [] if entry.get("row") in by_id and not entry.get("on")]
    if not entries:
        return []
    stage = Usd.Stage.Open(str(folder / f"{place}.usda"))
    layer = Sdf.Layer.FindOrOpen(str(folder / BASE_LAYER))
    stage.SetEditTarget(Usd.EditTarget(layer))
    hulls, under = wall_hulls(stage, place), built_under(stage, place)
    fits = []
    for entry in entries:
        path = f"/{place}/Objects/{entry['name']}"
        prim = stage.GetPrimAtPath(path)
        mesh = fitting.surface_mesh(stage, path) if prim and prim.IsActive() else None
        if mesh is None:
            continue
        found = change(mesh, by_id[entry["row"]], hulls, under)
        if found is None:
            continue
        whole, words = found
        fitting.changed_by(prim, Gf.Matrix4d(whole.tolist()))
        fits.append(fitting.laid_fit(stage, path, entry, "held", None, 0.0, 1.0, words))
    if not fits:
        return []
    layer.Save()
    moved = {fit["name"]: fit for fit in fits}
    laid = json.loads(laid_path.read_text())
    laid["objects"] = [{**entry, "low": moved[entry["name"]]["low"], "high": moved[entry["name"]]["high"],
                        **({"corners": [[round(float(value), 4) for value in point] for point in
                                        fitting.oriented_corners(stage, f"/{place}/Objects/{entry['name']}")]}
                           if "corners" in entry else {})}
                       if entry["name"] in moved else entry for entry in laid.get("objects", [])]
    laid["fitted"] = [*laid.get("fitted", []), *fits]
    laid_path.write_text(json.dumps(laid, indent=1))
    return fits
