"""A thing nothing holds in an open place stood on the made ground under it, with what it holds: turned so its up
is the up of the ground under its foot and let down until its lowest point touches that ground, as the resting
check reads it (triage.ground_plane: the plane through GROUND_SPOTS by GROUND_SPOTS heights of the ground under its
box; resting.ground_height: the made ground's fine patch), on the base layer, laid.json written again.

assembly@wreck, 2026-11-12: the scene record lays each thing at its plan's floor (0 m), and its made ground, raised by
its plan's three terrain spots, runs from -4.8 to +4.0 m under its 21 things: its lunar lander stood 2.1 m over the
ground, its spherical tank 4.6 m, its metal ring 3.9 m under it, the crashed rocket's front half sunk 5.6 m into a
slope of about 30 degrees, and what each holds (the rocket's engine and cables, the lander's solar panels) floated
with it. Nothing laid it on the ground: only the people (cast) and the view eyes (scene_record.writer.spot_ground)
were.

    stood(folder, place)   [{name, how "grounded", ...}]: each thing of the record at `folder` that nothing holds
                           (parting.loose), stands on the floor by itself (even_feet.floor_thing) and is laid at the
                           plan's floor (at_floor, never on a level over it), in a place the
                           record does not enclose, over the made ground with no deck there (not over a built deck,
                           fitting.deck_triangles), not resting on it as laid (its lowest point off the ground by
                           more than TOLERANCE either way, or its up axis over LEAN_MOST from the ground's): turned
                           and let down (rested), with every thing it holds down their chain (parting.carried) moved
                           as it is; the base layer saved and laid.json's boxes and fits written again
"""
import json
import pathlib
import sys

import numpy as np

from score.stages.assembly import BASE_LAYER, RECORD, even_feet, fitting, made_waiting, parting

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))

# The resting check's own measures (tools/usd/triage.py, resting.py), named here so the drop and the check read one
# rule: a point within TOLERANCE metres of the ground touches it, an up axis may lean LEAN_MOST degrees from the
# ground's, ground sloping under FLAT_TILT degrees is read level, and the ground's plane is fitted to GROUND_SPOTS by
# GROUND_SPOTS heights over a thing's box.
TOLERANCE = 0.03
LEAN_MOST = 3.0
FLAT_TILT = 1.0
GROUND_SPOTS = 5
# The made ground's fine patch, which the resting check reads the ground from (resting.MADE_GROUND).
MADE_GROUND = "Outside/near"


def stood(folder, place):
    """Each thing nothing holds of the place at `folder` stood on the made ground under it (module docstring): the
    fits [{name, how "grounded", ...}], [] and nothing written when none moves."""
    from pxr import Gf, Sdf, Usd
    folder = pathlib.Path(folder)
    laid_path, record_path = folder / made_waiting.LAID, folder / RECORD
    if not laid_path.exists() or not record_path.exists():
        return []
    laid, record = json.loads(laid_path.read_text()), json.loads(record_path.read_text())
    stage = Usd.Stage.Open(str(folder / f"{place}.usda"))
    near = stage.GetPrimAtPath(f"/{place}/{MADE_GROUND}")
    if record.get("inside") or not (near and near.IsActive()):
        return []
    import resting
    ground = resting.ground_height(stage, place)
    layer = Sdf.Layer.FindOrOpen(str(folder / BASE_LAYER))
    stage.SetEditTarget(Usd.EditTarget(layer))
    decks = fitting.deck_triangles(stage, place)
    holding = fitting.holders_of(record)
    entries = {entry["name"]: entry for entry in record.get("objects") or []}
    fits = []
    for name, entry in sorted(entries.items()):
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        if not (prim and parting.loose(entry) and even_feet.floor_thing(prim) and at_floor(entry)):
            continue
        change = rest_change(world_points(prim), up_of(prim), ground, decks)
        if change is None:
            continue
        held = [other for other in parting.carried(name, holding)
                if other in entries and stage.GetPrimAtPath(f"/{place}/Objects/{other}")]
        for one in (name, *held):
            path = f"/{place}/Objects/{one}"
            before = fitting.foot_middle(*fitting.world_box(stage, path))
            fitting.changed_by(stage.GetPrimAtPath(path), Gf.Matrix4d(change.tolist()))
            moved = float(np.linalg.norm(fitting.foot_middle(*fitting.world_box(stage, path)) - before))
            fits.append(fitting.laid_fit(stage, path, entries[one], "grounded", None, moved, 1.0,
                                         f"stood on the made ground under it: moved {moved:.2f} m"
                                         + ("" if one == name else f" with {name}, which holds it")))
    if not fits:
        return []
    layer.Save()
    moved = {fit["name"]: fit for fit in fits}
    laid["objects"] = [{**entry, "low": moved[entry["name"]]["low"], "high": moved[entry["name"]]["high"],
                        **({"corners": [[round(float(value), 4) for value in point] for point in
                                        fitting.oriented_corners(stage, f"/{place}/Objects/{entry['name']}")]}
                           if "corners" in entry else {})}
                       if entry["name"] in moved else entry for entry in laid.get("objects", [])]
    laid["fitted"] = [*laid.get("fitted", []), *fits]
    laid_path.write_text(json.dumps(laid, indent=1))
    return fits


def at_floor(entry):
    """Whether the record lays an entry at its plan's floor (0 m over it), never on a level over it: square's podium
    and speakers stand on its 3.3 m stage and its lantern strings hang at 6 m (2026-11-12)."""
    return abs(float((entry.get("at") or [0.0, 0.0])[1])) <= TOLERANCE


def world_points(prim):
    """The points of every drawn mesh under a thing (its collider left out), in the stage's frame, (N, 3)."""
    from pxr import Usd, UsdGeom
    found = []
    for part in Usd.PrimRange(prim):
        if part.IsA(UsdGeom.Mesh) and part.GetName() != "collision" and "collision" not in str(part.GetPath()):
            points = part.GetAttribute("points").Get()
            if points:
                matrix = np.asarray(UsdGeom.Xformable(part).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
                found.append(np.c_[np.asarray(points, float), np.ones(len(points))] @ matrix)
    return np.concatenate(found)[:, :3] if found else np.zeros((0, 3))


def up_of(prim):
    """A thing's own up axis in the stage's frame, of unit length."""
    from pxr import Usd, UsdGeom
    matrix = np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default()))
    return matrix[1, :3] / np.linalg.norm(matrix[1, :3])


def rest_change(points, up, ground, decks):
    """The world matrix (4x4, row vectors, USD's) that stands a thing's `points` on `ground` ((N, 2) x, z -> heights,
    nan off the made ground): its `up` turned onto the ground plane's up (ground_up) about the middle of its foot, then
    let down until its lowest point touches; None where it rests as laid, stands over a built deck (`decks`,
    fitting.deck_triangles) or reaches off the made ground."""
    if not len(points):
        return None
    low, high = points.min(axis=0), points.max(axis=0)
    pivot = np.array([(low[0] + high[0]) / 2, low[1], (low[2] + high[2]) / 2])
    if over_deck(pivot, decks):
        return None
    normal = ground_up(low, high, ground)
    if normal is None:
        return None
    turn = turn_onto(up, normal)
    change = moved(-pivot) @ turn @ moved(pivot)
    turned = np.c_[points, np.ones(len(points))] @ change
    clearance = turned[:, 1] - ground(turned[:, [0, 2]])
    if not np.isfinite(clearance).all():
        return None
    drop = float(clearance.min())
    leans = float(np.degrees(np.arccos(np.clip(up @ normal, -1.0, 1.0))))
    if leans <= LEAN_MOST and abs(float(np.nanmin(points[:, 1] - ground(points[:, [0, 2]])))) <= TOLERANCE:
        return None
    return change @ moved([0.0, -drop, 0.0])


def ground_up(low, high, ground):
    """The up of the ground under a box (low, high): the normal of the plane fitted to GROUND_SPOTS by GROUND_SPOTS of
    its heights over the box (triage.ground_plane's), straight up where it slopes under FLAT_TILT; None where the box
    reaches off the made ground."""
    across, along = np.meshgrid(np.linspace(low[0], high[0], GROUND_SPOTS), np.linspace(low[2], high[2], GROUND_SPOTS))
    spots = np.c_[across.ravel(), along.ravel()]
    heights = ground(spots)
    if not np.all(np.isfinite(heights)):
        return None
    slope_x, slope_z, _ = np.linalg.lstsq(np.c_[spots, np.ones(len(spots))], heights, rcond=None)[0]
    if np.degrees(np.arctan(np.hypot(slope_x, slope_z))) <= FLAT_TILT:
        return np.array([0.0, 1.0, 0.0])
    return np.array([-slope_x, 1.0, -slope_z]) / np.linalg.norm([slope_x, 1.0, slope_z])


def turn_onto(start, end):
    """The 4x4 row-vector matrix of the least turn taking the unit direction `start` onto `end` (Rodrigues)."""
    axis = np.cross(start, end)
    sine, cosine = float(np.linalg.norm(axis)), float(np.clip(start @ end, -1.0, 1.0))
    turn = np.eye(4)
    if sine < 1e-9:
        return turn
    axis = axis / sine
    cross = np.array([[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]])
    column = np.eye(3) + sine * cross + (1.0 - cosine) * cross @ cross  # turns column vectors
    turn[:3, :3] = column.T
    return turn


def moved(by):
    """The 4x4 row-vector matrix moving by `by` [x, y, z]."""
    shift = np.eye(4)
    shift[3, :3] = by
    return shift


def over_deck(point, decks):
    """Whether a point's (x, z) lies within a built deck's triangle seen from above (decks: [n, 3, 3])."""
    if not len(decks):
        return False
    corners = decks[:, :, [0, 2]]
    spot = np.asarray(point, float)[[0, 2]]

    def side(one, two):
        return (two[:, 0] - one[:, 0]) * (spot[1] - one[:, 1]) - (two[:, 1] - one[:, 1]) * (spot[0] - one[:, 0])
    first, second, third = (side(corners[:, 0], corners[:, 1]), side(corners[:, 1], corners[:, 2]),
                            side(corners[:, 2], corners[:, 0]))
    inside = ((first >= 0) & (second >= 0) & (third >= 0)) | ((first <= 0) & (second <= 0) & (third <= 0))
    return bool(inside.any())
