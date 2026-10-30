"""The settle stage's snapping: held objects onto their holders as they rest, fixed ones that float let down
(snap.py's down), apart from tools/usd/settle.py so that a snap edit moves only this row and complete."""
import json
import math
import pathlib
import sys

import numpy as np
from pxr import Usd, UsdGeom
from scipy.spatial.transform import Rotation

REPO = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tools/usd"))
import resting  # noqa: E402
import settle  # noqa: E402
import snap  # noqa: E402
import triage  # noqa: E402

DRIFT_MOST = settle.DRIFT_MOST
# How far a held object may be raised onto what holds it (metres): out of a little bedding, no more. snap.py's rays
# start 10 cm back, so a held one would otherwise climb onto a part of its holder over its own bottom (the habitat's
# food jugs and a storage case rose 10 cm into the shelf above, 2026-10-12).
RISE_MOST = 0.03
# How far apart the spots a held object is tried at to stand it level (metres; level_spot).
SPOT_STEP = 0.05
# A mesh of more triangles than this is cut to the reach of what is snapped against it (near).
NEAR_FACES = 20000


def held_objects(stage, place, inventory, kit_path=None):
    """The stage's top-level objects held on another (the triage's support `held`: row anchor `on:<row>`; the kit
    given its kinds' groups), lowest first, so one held on a held one comes after its holder. One held on a wall or a
    ceiling row (holders.holder_kind) is mounted, not held up from under, and left out: its laid pose stands
    (airlock's ceiling lamps on its roof dome, snapped toward a floor 280 cm down, 2026-10-30)."""
    from score.review.holders import holder_kind  # here: holders imports the stage table, which imports this module
    data, groups = triage.rules(), triage.kit_groups(kit_path)
    rows = {row["id"]: row for row in inventory["rows"]}
    mounted ={row["id"] for row in inventory["rows"] if (row.get("anchor") or "").startswith("on:")
               and holder_kind(rows.get(row["anchor"].removeprefix("on:"), {"id": ""})) in ("wall", "ceiling")}
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found = []
    for path, prim in resting.objects_of(stage, place).items():
        name = path.removeprefix(f"/{place}/Objects/")
        row = prim.GetAttribute("score:row").Get()
        if "/" not in name and row not in mounted and triage.support_type(rows.get(row, {}), prim, data,
                                                                           groups) == "held":
            found.append((cache.ComputeWorldBound(prim).ComputeAlignedRange().GetMin()[1], name))
    return [name for _, name in sorted(found)]


def held_rests(stage_path, place, inventory, kit_path):
    """Where each held object rests on what holds it, its holders as the stage lays them (after their drop): {name:
    {"before", "after", "rested", "said"}}. A held object is not dropped (a convex hull of its holder, a shelf unit,
    spans the shelf it lies on): it is stood upright in its seat as a loose one is (upright_starts) and snapped
    straight down onto the first surface under it (snap.py's down), lowest first, each one's new place seen by the
    next. One with nothing under it, or that would fall further than DRIFT_MOST, keeps its laid pose, not rested."""
    data = triage.rules()
    parts = data["parts"]
    rows = {row["id"]: row for row in inventory["rows"]}
    stage = Usd.Stage.Open(str(stage_path))
    names = [name for name in held_objects(stage, place, inventory, kit_path)
             if not settle.lies_as_laid(rows.get(name.rsplit("_", 1)[0], {}), data)]
    kit = json.loads(pathlib.Path(kit_path).read_text())
    starts = settle.upright_starts(stage, place, inventory, names, settle.seat_ground(place, kit))
    laid = snap.read_place(stage_path)
    poses = {}
    for name in names:
        before = settle.laid_matrix(stage, place, name)
        start = starts.get(name, np.eye(4))
        mesh = laid["objects"][name].copy()
        mesh.apply_transform(start)
        own_parts = tuple(name.rsplit("_", 1)[0] + suffix for suffix in parts)  # its own glow or screen
        obstacles = near(mesh, {other: found for other, found in snap.obstacles_of(laid, name).items()
                                if not other.startswith(own_parts)})
        try:
            offset = snap.drop_offset(mesh, snap.Obstacles(obstacles))
        except ValueError:
            offset = None
        if offset is not None and offset[1] > RISE_MOST:  # its holder's own part over its bottom: the triage judges it
            poses[name] = {"before": before, "after": before, "rested": True,
                           "said": f"left as laid (the snap would raise it {offset[1] * 100:.0f} cm onto a part of "
                                   "its holder over its bottom)"}
            continue
        straight = offset is not None and -offset[1] <= DRIFT_MOST
        moved = f"moved {-offset[1] * 100:+.1f} cm down onto what holds it" if straight else ""
        if not (straight and stands_level(snap.shifted(mesh, offset), snap.Obstacles(obstacles))):
            spot = level_spot(name, mesh, obstacles)
            if spot is None and not straight:
                poses[name] = {"before": before, "after": before, "rested": False,
                               "said": "nothing under it within reach; left as laid" if offset is None else
                                       f"would fall {-offset[1] * 100:.0f} cm onto what is under it; left as laid"}
                continue
            if spot is not None:
                offset = spot
                moved = (f"moved {np.hypot(spot[0], spot[2]) * 100:.0f} cm across and {-spot[1] * 100:+.1f} cm down "
                         "onto a level spot of what holds it")
        motion = snap.moved_matrix(start, offset)
        mesh.apply_translation(offset)
        laid["objects"][name] = mesh
        tipped = math.degrees(Rotation.from_matrix(start[:3, :3]).magnitude())
        poses[name] = {"before": before, "after": motion @ before, "rested": True,
                       "said": f"stood upright ({tipped:.0f} degrees) and {moved}" if tipped >= 0.01 else moved}
    return poses


def near(mesh, meshes):
    """What of `meshes` lies within DRIFT_MOST of the mesh across and along and not wholly over it: each a whole mesh,
    or the part of its triangles in reach (the ground's fine patch, 150 m across, is cut to it). A held object is
    snapped against these only: the hangar's 1,657 objects built into one scene for each of its held ones took over a
    quarter of an hour."""
    low, high = mesh.bounds
    low = low - [DRIFT_MOST, np.inf, DRIFT_MOST]
    high = high + [DRIFT_MOST, 0.0, DRIFT_MOST]
    found = {}
    for name, other in meshes.items():
        other_low, other_high = other.bounds
        if np.any(other_low > high) or np.any(other_high < low):
            continue
        if len(other.faces) > NEAR_FACES:
            corners = other.vertices[other.faces]
            inside = np.all((corners.max(axis=1) >= low) & (corners.min(axis=1) <= high), axis=1)
            other = other.submesh([np.nonzero(inside)[0]], append=True) if inside.any() else None
        if other is not None:
            found[name] = other
    return found


def footing(mesh, obstacles):
    """How a mesh stands on what is under it: (its lean in degrees from the plane through where its low points touch,
    how far its weight falls outside them, how many touch), as the triage's floor rule reads it."""
    low = triage.low_points(mesh)
    gaps = gaps_under(low, obstacles)
    touching = gaps <= resting.TOLERANCE
    support = low[touching] - np.outer(gaps[touching], [0.0, 1.0, 0.0])
    outside = resting.outside_by(resting.weight_at(mesh), support[:, [0, 2]])
    return triage.lean(np.eye(4), low[touching], gaps[touching]), outside, int(touching.sum())


def stands_level(mesh, obstacles):
    """Whether a mesh stands on its support as the triage asks: four contacts, its weight inside them, no lean, and
    every foot down (a desk mouse moved to a spot with a foot over the desk's edge stood 76 cm off, 2026-10-12)."""
    leans, outside, contacts = footing(mesh, obstacles)
    return contacts >= triage.CONTACTS_NEEDED and outside <= resting.BALANCE and leans <= triage.LEAN_MOST \
        and all(gap <= resting.TOLERANCE for _, gap in triage.feet_gaps(mesh, lambda low: gaps_under(low, obstacles)))


def gaps_under(points, obstacles):
    """How far each point stands over the first obstacle surface under it (inf over nothing)."""
    gaps, _ = obstacles.scene.raycast(points + [0.0, resting.RAY_START, 0.0],
                                      np.tile([0.0, -1.0, 0.0], (len(points), 1)))
    return gaps - resting.RAY_START


def level_spot(name, mesh, meshes):
    """The nearest shift (within DRIFT_MOST across, SPOT_STEP apart) after which the mesh, snapped down onto `meshes`
    (what it can meet: {name: mesh}), stands level on what holds it and meets nothing beside it: a monitor laid on a
    console's sloped panel moved onto its flat back. None when no spot within reach does."""
    obstacles, together = snap.Obstacles(meshes), snap.Obstacles({**meshes, name: mesh})
    reach = np.arange(-DRIFT_MOST, DRIFT_MOST + 1e-9, SPOT_STEP)
    spots = sorted(((across, along) for across in reach for along in reach if np.hypot(across, along) <= DRIFT_MOST),
                   key=lambda spot: np.hypot(*spot))
    for across, along in spots:
        try:
            down = snap.drop_offset(snap.shifted(mesh, [across, 0.0, along]), obstacles)
        except ValueError:
            continue
        offset = np.array([across, down[1], along])
        if -down[1] <= DRIFT_MOST and down[1] <= RISE_MOST and stands_level(snap.shifted(mesh, offset), obstacles) \
                and not snap.collides(together.scene, name, offset, mesh):
            return offset
    return None


def fixed_let_down(stage_path, place, floating):
    """Where each fixed object the triage finds floating (`floating`: names; a lander whose legs stand over a dip of
    the ground) rests when let straight down onto the first surface under it (snap.py's down, no turn): {name:
    {"before", "after", "rested", "said"}}. A fixed piece is never dropped (it is laid where it stands), but one that
    touches nothing is no pose; one with nothing under it, or more than DRIFT_MOST over it, keeps its laid pose."""
    stage = Usd.Stage.Open(str(stage_path))
    laid = snap.read_place(stage_path)
    poses = {}
    for name in floating:
        before = settle.laid_matrix(stage, place, name)
        try:
            mesh = laid["objects"][name]
            offset = snap.drop_offset(mesh, snap.Obstacles(near(mesh, snap.obstacles_of(laid, name))))
        except ValueError as error:
            poses[name] = {"before": before, "after": before, "rested": False, "said": f"{error}; left as laid"}
            continue
        if -offset[1] > DRIFT_MOST:
            poses[name] = {"before": before, "after": before, "rested": False,
                           "said": f"floats {-offset[1] * 100:.0f} cm over what is under it; left as laid"}
            continue
        poses[name] = {"before": before, "after": snap.moved_matrix(before, offset), "rested": True,
                       "said": f"let down {-offset[1] * 100:.1f} cm onto what is under it"}
    return poses
