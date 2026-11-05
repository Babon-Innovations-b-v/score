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
from score.stages.assembly.mounted import mounted  # noqa: E402

DRIFT_MOST = settle.DRIFT_MOST
# How far a held object may be raised onto what holds it (metres): out of a little bedding, no more. snap.py's rays
# start 10 cm back, so a held one would otherwise climb onto a part of its holder over its own bottom (the habitat's
# food jugs and a storage case rose 10 cm into the shelf above, 2026-10-12).
RISE_MOST = 0.03
# How far apart the spots a held object is tried at to stand it level (metres; level_spot).
SPOT_STEP = 0.05
# A mesh of more triangles than this is cut to the reach of what is snapped against it (near).
NEAR_FACES = 20000
# A leaning thing (#94, its scene record entry's `rests`): leaned this many degrees from upright, its top toward its
# holder, then slid against it and let down onto the floor (leaning_rests); it falls past LEAN_FALLS degrees.
LEAN = 12.0
LEAN_FALLS = 30.0
# How far a leaning thing is stood off its holder before it is slid back against it, metres past its lean's reach.
LEAN_OFF = 0.1


def faced(record):
    """The names of the scene `record`'s objects laid with their back on their holder's side (its relation `face`,
    #72: the assembly's fitting lays them on that side, front_face): mounted there, not held up from under."""
    return {entry["name"] for entry in record.get("objects") or [] if (entry.get("on") or {}).get("how") == "face"}


def held_objects(stage, place, inventory, kit_path=None, on_sides=frozenset()):
    """The stage's top-level objects held on another (the triage's support `held`: row anchor `on:<row>`; the kit
    given its kinds' groups), lowest first, so one held on a held one comes after its holder. One held on a wall or a
    ceiling row (`mounted`), or laid on its holder's side (`on_sides`, `faced`), is mounted, not held up from under,
    and left out: its laid pose stands (airlock's ceiling lamps on its roof dome, snapped toward a floor 280 cm down,
    2026-10-30; storage's pipes against its pillar's side snapped one by one, the one between left leaning 3.06
    degrees on its moved neighbour, settle@storage 2026-11-03)."""
    data, groups = triage.rules(), triage.kit_groups(kit_path)
    rows = {row["id"]: row for row in inventory["rows"]}
    on_walls = mounted(rows)
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    found = []
    for path, prim in resting.objects_of(stage, place).items():
        name = path.removeprefix(f"/{place}/Objects/")
        row = prim.GetAttribute("score:row").Get()
        if "/" not in name and row not in on_walls and name not in on_sides and triage.support_type(rows.get(row, {}), prim, data,
                                                                           groups) == "held":
            found.append((cache.ComputeWorldBound(prim).ComputeAlignedRange().GetMin()[1], name))
    return [name for _, name in sorted(found)]


def held_rests(stage_path, place, inventory, kit_path, record=None):
    """Where each held object rests on what holds it, its holders as the stage lays them (after their drop): {name:
    {"before", "after", "rested", "said"}}. A held object is not dropped (a convex hull of its holder, a shelf unit,
    spans the shelf it lies on): it is stood upright in its seat as a loose one is (upright_starts) and snapped
    straight down onto the first surface under it (snap.py's down), lowest first, each one's new place seen by the
    next. One with nothing under it, or that would fall further than DRIFT_MOST, keeps its laid pose, not rested; one
    the scene `record` lays on its holder's side is not snapped (held_objects)."""
    data = triage.rules()
    parts = data["parts"]
    rows = {row["id"]: row for row in inventory["rows"]}
    stage = Usd.Stage.Open(str(stage_path))
    names = [name for name in held_objects(stage, place, inventory, kit_path, faced(record or {}))
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


def leaning(record):
    """{name: the way out of its holder into the room, [x, z]} of each object the scene `record` says rests leaning
    against its holder (its `rests`, its `on`'s `out`: on a wall's or a holder's face); one with no such way (nothing
    to lean on: a plan with no wall) is named with None, for the gate to fail as falling."""
    return {entry["name"]: (entry.get("on") or {}).get("out") for entry in record.get("objects") or []
            if entry.get("rests") == "leaning"}


def leaning_rests(stage_path, place, ways):
    """Where each leaning object (`ways`: {name: its holder's way out, [x, z]}, leaning) rests on its foot against
    its holder: {name: {"before", "after", "rested", "said"}}. Turned LEAN degrees about its foot's middle, its top
    toward the holder, stood LEAN_OFF past its lean's reach out from it, slid back until it meets it and let down onto
    the floor (snap.py's runs), twice, so its top rests on the holder and its foot on the floor. One with no way, or
    with nothing to slide against or stand on, keeps its laid pose, not rested."""
    stage = Usd.Stage.Open(str(stage_path))
    laid = snap.read_place(stage_path)
    poses = {}
    for name, out in sorted(ways.items()):
        before = settle.laid_matrix(stage, place, name)
        if not out or name not in laid["objects"]:
            poses[name] = {"before": before, "after": before, "rested": False,
                           "said": "leaning on nothing: its relation gives no holder's face; left as laid"}
            continue
        mesh = laid["objects"][name]
        way = np.array([float(out[0]), 0.0, float(out[1])])
        way /= max(float(np.linalg.norm(way)), 1e-9)
        tall = float(mesh.bounds[1][1] - mesh.bounds[0][1])
        reach = tall * math.sin(math.radians(LEAN)) + LEAN_OFF
        obstacles = snap.Obstacles(near(mesh, snap.obstacles_of(laid, name), reach + DRIFT_MOST))
        motion = leaned_motion(mesh, way, reach)
        try:
            motion = against_and_down(mesh, motion, way, obstacles)
        except ValueError as error:
            poses[name] = {"before": before, "after": before, "rested": False, "said": f"{error}; left as laid"}
            continue
        poses[name] = {"before": before, "after": motion @ before, "rested": True,
                       "said": f"leaned {LEAN:g} degrees on its foot against its holder"}
    return poses


def leaned_motion(mesh, way, reach):
    """The motion (4 x 4, the stage's frame) that turns a mesh LEAN degrees about its foot's middle, its top toward
    -`way` (its holder), and stands it `reach` out along `way` and as high over where its foot was: clear of the
    holder and the floor it is then slid and let down onto."""
    axis = np.cross(way, [0.0, 1.0, 0.0])
    turn = Rotation.from_rotvec(axis / np.linalg.norm(axis) * math.radians(LEAN)).as_matrix()
    foot = mesh.bounds.mean(axis=0)
    foot[1] = mesh.bounds[0][1]
    motion = np.eye(4)
    motion[:3, :3] = turn
    motion[:3, 3] = foot - turn @ foot + way * reach + [0.0, reach, 0.0]
    return motion


def against_and_down(mesh, motion, way, obstacles):
    """The motion after which the mesh, moved by `motion`, is slid along -`way` until it meets what is there (its
    holder) and let straight down onto what is under it, twice (its top slides down a holder that is not upright);
    ValueError when nothing is there to meet or stand on."""
    moved = mesh.copy()
    moved.apply_transform(motion)
    for _ in range(2):
        run = snap.free_run(moved, obstacles, -way)
        if not np.isfinite(run):
            raise ValueError("nothing to lean against along its holder's way")
        shift = -way * (run - snap.CLEARANCE)
        shift = shift + snap.drop_offset(snap.shifted(moved, shift), obstacles)
        moved.apply_translation(shift)
        motion = snap.moved_matrix(motion, shift)
    return motion


def leaning_faults(stage_path, place, ways):
    """How each leaning object (`ways`, leaning) fails to rest on its foot against its holder as the stage lays it:
    ["<name>: falls ..." or "<name>: floats ..."]. It falls when it has no holder's way, when nothing lies within
    resting.TOLERANCE of it toward its holder, or when its own up leans past LEAN_FALLS; it floats when its foot is
    over resting.TOLERANCE above what is under it."""
    laid = snap.read_place(stage_path)
    faults = []
    for name, out in sorted(ways.items()):
        if name not in laid["objects"]:
            faults.append(f"{name}: falls: it is not laid")
            continue
        if not out:
            faults.append(f"{name}: falls: it leans on nothing, its relation giving no holder's face")
            continue
        mesh = laid["objects"][name]
        way = np.array([float(out[0]), 0.0, float(out[1])])
        way /= max(float(np.linalg.norm(way)), 1e-9)
        obstacles = snap.Obstacles(near(mesh, snap.obstacles_of(laid, name), DRIFT_MOST))
        up = laid["matrices"][name][:3, 1]
        tilt = math.degrees(math.acos(min(1.0, abs(float(up[1])) / max(float(np.linalg.norm(up)), 1e-9))))
        gap, foot = snap.free_run(mesh, obstacles, -way), snap.free_run(mesh, obstacles, snap.DOWN)
        if tilt > LEAN_FALLS:
            faults.append(f"{name}: falls: it lies {tilt:.0f} degrees over (past {LEAN_FALLS:g})")
        elif gap > resting.TOLERANCE:
            faults.append(f"{name}: falls: nothing holds its top, its holder "
                          + ("out of reach" if not np.isfinite(gap) else f"{gap * 100:.1f} cm off"))
        if foot > resting.TOLERANCE:
            faults.append(f"{name}: floats: its foot " + ("over nothing" if not np.isfinite(foot)
                                                          else f"{foot * 100:.1f} cm over what is under it"))
    return faults


def near(mesh, meshes, reach=DRIFT_MOST):
    """What of `meshes` lies within `reach` of the mesh across and along and not wholly over it: each a whole mesh,
    or the part of its triangles in reach (the ground's fine patch, 150 m across, is cut to it). A held object is
    snapped against these only: the hangar's 1,657 objects built into one scene for each of its held ones took over a
    quarter of an hour."""
    low, high = mesh.bounds
    low = low - [reach, np.inf, reach]
    high = high + [reach, 0.0, reach]
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
