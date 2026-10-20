"""Settle a place's loose objects with physics and write where they came to rest into its layout.

    .venv/bin/python tools/usd/settle.py <stage.usda> [--dry-run] [--cloud] [--reuse] [--detach]

--dry-run simulates and writes nothing to the layout; its result (settle/settled.json beside the stage) is what the
resting triage (triage.py --settled) reads for SAGE's stability rule (unstable: over SAGE_MOVE or SAGE_TURN).

A loose object is one laid on the ground that is not fixed: its inventory row's anchor is the floor (or none), and
the row is not marked `"fixed": true` (a building, a mast, a cable run laid where it is). Hung rows, children and
fixed rows stay where they are and are static in the simulation. Each loose object is lifted just clear of the ground
(SETTLE_DROP over its lowest point) and dropped in headless Blender onto the stage's real ground with its own triangles
for collision (tools/blender/inside/settle_stage.py), so it tilts and comes to rest the way a real object would.

Where it rests is written back to the place's layout, data/inventory/<place>.json (the spot) and data/kit/<place>.json
(the piece), as the layout says where a piece is: its spot (`x`, `z`) and its lift off the ground there (`y`), and its
turn in its own seat's frame as a unit quaternion `rotation` [x, y, z, w] (x across, y up, z along), which replaces
`facing` and `tilt` (`facing` is kept as the rotation's heading for readers that know only a heading; `tilt` is
dropped). Settling only corrects a laid pose: an object that would turn more than TURN_MOST or whose middle would drift
more than DRIFT_MOST to come to rest (small debris: any turn, DEBRIS_DRIFT) keeps its laid pose and is marked `"unrested"` in its spot and piece (what it
would do), which the resting check fails as "would not rest as laid"; the layout is put right instead (a support piece,
a laid pose that rests, or a bed in the ground under it). A tip over the triage's LEAN_MOST onto feet that do not lie in
one plane in the model's own frame is the model's fault, never written either (marked the same way: level the model's
feet; the surface stage's paint does so before its bake). A piece the drop found laid inside a static one was dropped
on the bare ground alone, so its result is no rest pose and is not written: its layout is put right first. What lies
on a written piece (held on its row, or its own glowing part or screen) is carried with it (carried_with). Export the
stage again after, and run the resting check (tools/usd/resting.py).
"""
import argparse
import json
import math
import pathlib
import subprocess
import sys

import numpy as np
import trimesh
from pxr import Usd, UsdGeom
from scipy.spatial.transform import Rotation

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import stage_inputs  # noqa: E402
import ground as grounds  # noqa: E402
import resting  # noqa: E402

SESSION = REPO / "tools/blender/session.py"
INSIDE = REPO / "tools/blender/inside/settle_stage.py"
# A drop takes a small processor machine and nothing else (#20; POP2-HM-4C-32G at about a sixth of a 32-core's hourly
# price; #21: one class decided before the batch, no chain to the 32-core classes): Blender's rigid-body solve is taken
# to run on one core, not yet timed on one (the first drop on it is that timing). None in stock at price time: the
# drop fails at once (blender_cloud.price), a hole; a later drop is a new batch. The machine is parked for its billed hour after its drop
# (blender_cloud's kind is in park.CLEANUPS), so the places' drops after the free triage share one rental within it.
DROP_CLASSES = ("cpu-4c-32gb",)
KITS = REPO / "data/kit"
# How far over the ground an object's lowest point starts its fall, in metres.
SETTLE_DROP = 0.02
# An object still moving faster than this at the end of the simulation has not settled (metres a second).
STILL = 0.05
# Settling only corrects a laid pose, it never re-poses: an object that turns more than this (degrees) or whose middle
# drifts further (metres) to come to rest keeps its laid pose and is marked (the concept's composition is the owner's).
TURN_MOST = 15.0
DRIFT_MOST = 0.3
# Small debris (no side longer than DEBRIS_SIZE metres: a panel, a strut, a sphere) may turn freely and drift up to
# DEBRIS_DRIFT metres: where a thrown piece fell is not part of the composition (coordinator, 2026-10-08).
DEBRIS_SIZE = 1.4
DEBRIS_DRIFT = 1.0
LOOSE_ANCHORS = {"floor", "ground", ""}
# SAGE's stability rule (NVlabs, arXiv 2602.10116, Apache-2.0): an object that moves further than this (metres) or turns
# more (degrees) when dropped does not rest as laid; the resting triage (triage.py) counts it a real fault.
# How far a fixture's footprint may reach past the loose object it lies on (metres) and still count as lying on it.
FOOTPRINT_SLACK = 0.02
# The scene record's groups whose pieces may lie on a loose object.
RECORD_GROUPS = ("Fixtures", "Structure")
SAGE_MOVE = 0.2
SAGE_TURN = 8.0
# An object's feet are looked for this share of its height over its lowest point (the paint's FOOT_BAND,
# score/stages/surfaces/place_line.py), at least the triage's LOW_BAND: the water tank's shortest leg ended 12.7 cm up.
FOOT_BAND = 0.15
# How far a loose object's bottom may lie from the top of another under it and still be stacked on it (metres).
STACK_REACH = 0.05


def loose_objects(stage, place, inventory):
    """The stage's top-level objects whose row lies loose on the ground: {object name: its lift for the drop}. Loose
    is what the resting triage judges as standing on the floor (triage.support_type): a kit's shell piece (a floor
    plate, data/checks/resting.json `fixed_in_kit`) and a glowing part judged with its host are not dropped."""
    import triage
    data, groups = triage.rules(), triage.kit_groups(place)
    rows = {row["id"]: row for row in inventory["rows"]}
    height = resting.ground_height(stage, place)
    found = {}
    for path, prim in resting.objects_of(stage, place).items():
        name = path.removeprefix(f"/{place}/Objects/")
        row = rows.get(prim.GetAttribute("score:row").Get(), {})
        if "/" in name or row.get("fixed") or row.get("anchor", "") not in LOOSE_ANCHORS:
            continue
        if triage.support_type(row, prim, data, groups) != "floor":
            continue
        points, _ = resting.in_stage(prim.GetChild("geo"))
        clearance = points[:, 1] - height(points[:, [0, 2]])
        found[name] = max(0.0, SETTLE_DROP - float(np.nanmin(clearance)))
    return found


def part_objects(stage, place, inventory):
    """The stage's glowing parts (a lamp's lens, a screen: rows the triage judges with their host, support `part`),
    which the drop leaves out of its statics: a part lies on or in its host by design, so a host would otherwise
    start "inside" it and be dropped on the bare ground alone."""
    import triage
    data, groups = triage.rules(), triage.kit_groups(place)
    rows = {row["id"]: row for row in inventory["rows"]}
    return sorted(path.removeprefix(f"/{place}/Objects/") for path, prim in resting.objects_of(stage, place).items()
                  if triage.support_type(rows.get(prim.GetAttribute("score:row").Get(), {}), prim, data, groups)
                  == "part")


def held_on_loose(stage, place, inventory, loose):
    """The stage's objects held on a loose one (row anchor `on:<row>` whose row is dropped: a seed tray on its shelf),
    which the drop leaves out of its statics: the holder raised by the nudge meets what lies on it, so it would
    otherwise start "inside" it and be dropped on the bare ground alone."""
    rows = {row["id"]: row for row in inventory["rows"]}
    objects = resting.objects_of(stage, place)
    dropped = {objects[f"/{place}/Objects/{name}"].GetAttribute("score:row").Get() for name in loose}
    anchors = {path: rows.get(prim.GetAttribute("score:row").Get(), {}).get("anchor", "")
               for path, prim in objects.items()}
    return sorted(path.removeprefix(f"/{place}/Objects/") for path, anchor in anchors.items()
                  if anchor.startswith("on:") and anchor.removeprefix("on:") in dropped)


def fixtures_on_loose(stage, place, loose):
    """The scene record's pieces (Fixtures, Structure) lying on a loose object (the workshop's robot, parts trays and
    tray tiles on its robot bench):
    each whose footprint lies within a loose object's and whose foot stands over that object's middle height. The drop
    leaves them out of its statics, as it does what is held on a loose object (held_on_loose): the holder raised by the
    nudge meets them, and a holder whose hull closes over them is thrown off them."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    boxes = {}
    for name in loose:
        box = cache.ComputeWorldBound(stage.GetPrimAtPath(f"/{place}/Objects/{name}")).ComputeAlignedRange()
        boxes[name] = (np.asarray(box.GetMin()), np.asarray(box.GetMax()))
    found = []
    for prim in (child for group in RECORD_GROUPS if stage.GetPrimAtPath(f"/{place}/{group}").IsValid()
                 for child in stage.GetPrimAtPath(f"/{place}/{group}").GetChildren()):
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if box.IsEmpty():
            continue
        low, high = np.asarray(box.GetMin()), np.asarray(box.GetMax())
        if any(np.all(low[[0, 2]] >= under[0][[0, 2]] - FOOTPRINT_SLACK)
               and np.all(high[[0, 2]] <= under[1][[0, 2]] + FOOTPRINT_SLACK)
               and low[1] >= (under[0][1] + under[1][1]) / 2 for under in boxes.values()):
            found.append(prim.GetName())
    return sorted(found)


def carried_with(stage, place, inventory, settled):
    """What lies on a settled object moves with it: each object held on its row (`on:<row>`) or its own glowing part
    or screen (triage.py's part suffixes), whose middle lies over the holder's footprint, and in turn what lies on
    that (a monitor's screen), given the holder's motion: {name: settled entry}, as settle writes the holder's."""
    import triage
    suffixes = triage.rules()["parts"]
    rows = {row["id"]: row for row in inventory["rows"]}
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    boxes = {}
    for path, prim in resting.objects_of(stage, place).items():
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        boxes[path.removeprefix(f"/{place}/Objects/")] = (np.asarray(box.GetMin()), np.asarray(box.GetMax()))
    queue = [(name, found["after"] @ np.linalg.inv(found["before"])) for name, found in settled.items()
             if correction(found)[0] <= TURN_MOST and correction(found)[1] <= DRIFT_MOST
             and not tips_on_uneven_feet(found)]  # a holder written back
    found = {}
    while queue:
        holder, motion = queue.pop(0)
        row = holder.rsplit("_", 1)[0]
        low, high = boxes[holder]
        for name, (other_low, other_high) in boxes.items():
            if "/" in name or name in settled or name in found or name == holder:
                continue
            own = name.rsplit("_", 1)[0]
            if rows.get(own, {}).get("anchor", "") != f"on:{row}" and own not in {row + suffix for suffix in suffixes}:
                continue
            middle = (other_low + other_high) / 2
            if np.any(middle[[0, 2]] < low[[0, 2]] - FOOTPRINT_SLACK) or np.any(middle[[0, 2]] > high[[0, 2]] + FOOTPRINT_SLACK):
                continue
            before = laid_matrix(stage, place, name)
            found[name] = {"before": before, "after": motion @ before, "middle": object_middle(stage, place, name)}
            queue.append((name, motion))
    return found


def upright_starts(stage, place, inventory, loose, ground):
    """{name: the motion (stage frame, column vectors) that stands it upright in its own seat about its middle, its
    heading and spot kept} for each loose object the resting triage asks to stand on its feet (no `leans`, no bedding
    class) that is laid tipped by more than a hundredth of a degree but at most TURN_MOST. Its drop starts there: an old
    settle's tip onto uneven feet (written before 2026-10-12: the hangar's racks 2 to 4 degrees, its monitor desk 8) is
    no pose to drop from, while a piece laid over further keeps its pose (the composition is the owner's)."""
    import triage
    data = triage.rules()
    rows = {row["id"]: row for row in inventory["rows"]}
    found = {}
    for name in loose:
        prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
        if lies_as_laid(rows.get(prim.GetAttribute("score:row").Get(), {}), data):
            continue
        laid = laid_matrix(stage, place, name)
        scale = float(np.cbrt(np.linalg.det(laid[:3, :3])))
        turn = laid[:3, :3] / scale
        across, along, _, in_seat = layout_pose(laid, ground, scale)
        seat = np.eye(3) if ground is None else ground.standing(across, along, 0.0)[1]
        upright = seat.T @ Rotation.from_euler("y", -math.radians(heading_of(in_seat))).as_matrix()
        change = upright @ turn.T
        tipped = math.degrees(Rotation.from_matrix(change).magnitude())
        if tipped < 0.01 or tipped > TURN_MOST:
            continue
        middle = laid[:3, :3] @ np.asarray(object_middle(stage, place, name)) + laid[:3, 3]
        motion = np.eye(4)
        motion[:3, :3] = change
        motion[:3, 3] = middle - change @ middle
        found[name] = motion
    return found


def lies_as_laid(row, data):
    """Whether a row lies as laid, asked neither to stand upright nor to rest on its feet: it says it `leans` (laid
    tilted on purpose) or is of a bedding class (a towel over a handle, a cable through its skirting)."""
    import triage
    return bool(row.get("leans")) or triage.bedding(row, data)[1] is not None


def start_lift(stage, place, name, start):
    """How far to lift an object stood at `start` (a motion from as laid) for its lowest point to begin its fall
    SETTLE_DROP over the ground, and at least as high as it lay (standing it up lowers a corner: on a deck it would
    begin inside it)."""
    points = object_points(stage, place, name)
    moved = points @ start[:3, :3].T + start[:3, 3]
    clearance = float(np.nanmin(moved[:, 1] - resting.ground_height(stage, place)(moved[:, [0, 2]])))
    return max(0.0, SETTLE_DROP - clearance, float(points[:, 1].min() - moved[:, 1].min()))


def object_points(stage, place, name):
    """An object's drawn points in the stage's frame."""
    return resting.in_stage(stage.GetPrimAtPath(f"/{place}/Objects/{name}").GetChild("geo"))[0]


def touching(stage, place, name, start, rested):
    """`start` (a motion from as laid) moved up or down until the object's lowest point stands where it did at rest
    (`rested`, a motion from as laid): on what held it there, ground or deck."""
    points = object_points(stage, place, name)
    down = np.eye(4)
    down[1, 3] = float((points @ rested[:3, :3].T + rested[:3, 3])[:, 1].min()
                       - (points @ start[:3, :3].T + start[:3, 3])[:, 1].min())
    return down @ start


def stacked_under(stage, place, loose):
    """{name: the loose objects it is stacked on}: each loose object whose top lies within STACK_REACH of another's
    bottom and whose footprint it overlaps (a crate laid on a crate, the hangar's parts_crate_4), which the drop lets
    meet it. Loose objects otherwise pass through each other in the drop, so a stacked one fell to the floor. Each
    pair is judged in the lower one's own upright frame, not the stage's: on the campgrounds' 4.8 degree slope the
    stage's boxes put cargo case 1, 2 mm over pallet 2's deck, 11 cm under the pallet's top, and the drop let it
    fall into the pallet (settle@campgrounds, 2026-10-15)."""
    corners = {name: box_corners(stage, place, name) for name in loose}
    found = {}
    for name in loose:
        under = []
        for other in loose:
            if other == name:
                continue
            frame = upright_frame(corners[other])
            other_low, other_high = box_in(frame, corners[other])
            low, high = box_in(frame, corners[name])
            if abs(other_high[1] - low[1]) <= STACK_REACH and other_low[1] < low[1] and \
                    np.all(np.minimum(high[[0, 2]], other_high[[0, 2]]) > np.maximum(low[[0, 2]], other_low[[0, 2]])):
                under.append(other)
        if under:
            found[name] = sorted(under)
    return found


def box_corners(stage, place, name):
    """The 8 corners (stage frame; x slowest, z fastest) of an object's box in its own frame."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    bound = cache.ComputeWorldBound(stage.GetPrimAtPath(f"/{place}/Objects/{name}"))
    low, high = (np.asarray(corner) for corner in (bound.GetRange().GetMin(), bound.GetRange().GetMax()))
    local = np.array([[x, y, z, 1.0] for x in (low[0], high[0]) for y in (low[1], high[1]) for z in (low[2], high[2])])
    return (local @ np.asarray(bound.GetMatrix()))[:, :3]  # USD's matrices act on row vectors


def stack_lift(stage, place, name, start, support):
    """How far to lift an object stood at `start` (a motion from as laid) for its lowest point to begin its fall
    SETTLE_DROP over its support's highest point, in the support's upright frame: the drop meets the support's convex
    hull, and one begun inside it is thrown (the campgrounds' cargo case 1, begun 2.4 cm inside pallet 2's hull,
    turned 179 degrees onto pallet 1 on the baked models, 2026-10-15)."""
    frame = upright_frame(box_corners(stage, place, support))
    points = object_points(stage, place, name)
    lowest = float(((points @ start[:3, :3].T + start[:3, 3]) @ frame.T)[:, 1].min())
    top = float((object_points(stage, place, support) @ frame.T)[:, 1].max())
    return max(0.0, top + SETTLE_DROP - lowest)


def upright_frame(corners):
    """The rotation (rows: its across, up and along in the stage's frame) of a box given by its 8 corners (in
    stacked_under's order: x slowest, z fastest), its up the box's own axis nearest the stage's up."""
    edges = [corners[4] - corners[0], corners[2] - corners[0], corners[1] - corners[0]]
    axes = [edge / (np.linalg.norm(edge) or 1.0) for edge in edges]
    up = max(range(3), key=lambda index: abs(axes[index][1]))
    vertical = axes[up] * np.sign(axes[up][1])
    longest = max((index for index in range(3) if index != up), key=lambda index: np.linalg.norm(edges[index]))
    across = axes[longest] - vertical * float(axes[longest] @ vertical)
    across /= np.linalg.norm(across)
    return np.array([across, vertical, np.cross(across, vertical)])


def box_in(frame, corners):
    """The low and high corners of points (stage frame) in a frame's own axes (upright_frame), metres."""
    turned = corners @ frame.T
    return turned.min(axis=0), turned.max(axis=0)


def drop_job(stage, place, inventory, upright, kit_path=None):
    """What a drop of the stage takes: the loose objects with their lifts, what is left out of the statics, the
    upright starts (only when `upright`: a drop that finds rest poses; a drop that judges the laid pose, SAGE's,
    starts as laid; the kit, data/kit/<place>.json or the file given, names the place's seat) and what each loose
    object is stacked on."""
    loose = loose_objects(stage, place, inventory)
    ignore = (part_objects(stage, place, inventory) + held_on_loose(stage, place, inventory, loose)
              + fixtures_on_loose(stage, place, loose))
    starts, under = {}, stacked_under(stage, place, loose)
    if upright:
        kit = json.loads(pathlib.Path(kit_path or KITS / f"{place}.json").read_text())
        starts = upright_starts(stage, place, inventory, loose, seat_ground(place, kit))
        for name, (support, shift) in onto_one_support(stage, place, under).items():
            starts[name] = shift @ starts.get(name, np.eye(4))
            under[name] = [support]
        loose.update({name: start_lift(stage, place, name, start) for name, start in starts.items()})
        loose.update({name: max(loose[name], stack_lift(stage, place, name, starts[name], supports[0]))
                      for name, supports in under.items() if name in starts})
    return loose, ignore, starts, under


def seat_ground(place, kit):
    """The ground whose seat an object stands upright in (upright_starts): none in a kit room, whose pieces stand on
    the room's own level floor in its frame (the greenhouse's water tank was stood upright in the terrain's seat under
    its spot, 6 degrees off the floor plates it stands on, 2026-10-15), else the place's (kit: its `on_seat`)."""
    return None if "room" in kit else grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0]))


def onto_one_support(stage, place, under):
    """{name: (its support, the shift that sets it wholly over it)} for each stacked object (stacked_under): the
    support it overlaps most, and the least move across that puts its footprint inside that support's (or its middle
    over the support's, when it is the wider). A stacked object rests on one support: the hangar's parts_crate_4,
    laid across two crates, came to rest with a skid 99 cm over the floor (2026-10-13)."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])

    def footprint(name):
        box = cache.ComputeWorldBound(stage.GetPrimAtPath(f"/{place}/Objects/{name}")).ComputeAlignedRange()
        return np.asarray(box.GetMin())[[0, 2]], np.asarray(box.GetMax())[[0, 2]]

    found = {}
    for name, supports in under.items():
        low, high = footprint(name)
        overlap = {support: float(np.prod(np.clip(np.minimum(high, footprint(support)[1])
                                                  - np.maximum(low, footprint(support)[0]), 0.0, None)))
                   for support in supports}
        support = max(sorted(overlap), key=overlap.get)
        support_low, support_high = footprint(support)
        inside = np.where(high - low <= support_high - support_low,
                          np.clip(low, support_low, support_high - (high - low)) - low,
                          (support_low + support_high) / 2 - (low + high) / 2)
        shift = np.eye(4)
        shift[[0, 2], 3] = inside
        found[name] = (support, shift)
    return found


def simulate(stage_path, loose, folder, cloud=False, ignore=(), start=None, under=None, cache=None):
    """The Blender run: how each loose object moved from as laid to at rest (stage frame, column vectors), how fast
    it still moved at the end, and the static objects it started inside; `ignore` are objects left out of the
    statics (part_objects, held_on_loose, fixtures_on_loose), `start` the motions that stand objects upright before
    their drop (upright_starts) and `under` what each is stacked on (stacked_under). With a `cache` folder, a cloud
    drop of the very same job on the very same stage with the same drop script is not paid for twice
    (drop_key)."""
    folder.mkdir(parents=True, exist_ok=True)
    job, out = folder / "settle-job.json", folder / "settled.json"
    job.write_text(json.dumps({"loose": sorted(loose), "lift": loose, "ignore": sorted(ignore),
                               "start": {name: np.asarray(motion).tolist() for name, motion in (start or {}).items()},
                               "under": under or {}}, indent=1))
    if out.exists():
        out.unlink()
    if cloud:  # a rented processor machine (tools/props/cloud/blender_cloud.py), not this PC's one Blender
        kept = pathlib.Path(cache) / drop_key(stage_path, job) / "settled.json" if cache else None
        if kept is not None and kept.exists():
            out.write_bytes(kept.read_bytes())
            return json.loads(out.read_text())
        sys.path.insert(0, str(REPO / "tools/props/cloud"))
        import blender_cloud
        blender_cloud.run_elsewhere(INSIDE, [stage_path, job, out], [stage_path.parent, job], [out],
                                    DROP_CLASSES, "settle", minutes=30)
        if kept is not None:
            kept.parent.mkdir(parents=True, exist_ok=True)
            kept.write_bytes(out.read_bytes())
        return json.loads(out.read_text())
    command = [sys.executable, str(SESSION), "batch", str(INSIDE), "--", str(stage_path), str(job), str(out)]
    if subprocess.run(command, stdout=subprocess.DEVNULL).returncode != 0 or not out.exists():
        raise RuntimeError(f"the settle run failed; run it by hand to see its output: {command}")
    return json.loads(out.read_text())


def drop_key(stage_path, job):
    """A drop's identity: the hash of its job, the drop script and every file of the stage's folder."""
    import hashlib
    digest = hashlib.sha256(pathlib.Path(job).read_bytes() + INSIDE.read_bytes())
    folder = pathlib.Path(stage_path).parent
    for path in sorted(item for item in folder.rglob("*") if item.is_file()):
        digest.update(str(path.relative_to(folder)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def rest_poses(stage, place, inventory, simulated, starts, room=False):
    """Where a drop leaves each loose object, as the rest layer lays it: {name: {"before", "after" (stage frame,
    column vectors), "rested": True when it came to rest by a small correction (write_layout's limits), "said": what it
    did}}, and what lies on a written one carried with it (carried_with). One laid inside a static, still moving, or
    that would turn or drift past the limits keeps its laid pose, not rested (its layout is put right instead). A tip
    onto uneven feet stands upright on its lowest foot (its start, let down to touch), not rested either: the model's
    feet are the paint's to level (feet.py), and the assembly's own drop judges the levelled model. One that stands on
    its feet on sloping ground rests flush on the slope (flush_on_slope), whatever the drop did; not in a kit `room`,
    whose pieces stand on its own level floor plates, whatever the terrain under them does."""
    import triage
    poses = {}
    data, rows = triage.rules(), {row["id"]: row for row in inventory["rows"]}
    ground = None if room else resting.ground_height(stage, place)
    for name, found in sorted(simulated["objects"].items()):
        before = laid_matrix(stage, place, name)
        if found["inside"] or found["moving"] > STILL:
            why = (f"laid inside {', '.join(found['inside'])}" if found["inside"]
                   else f"still moving {found['moving']:.2f} m/s at the end")
            poses[name] = {"before": before, "after": before, "rested": False, "said": f"{why}; left as laid"}
            continue
        dropped = dropped_pose(stage, place, name, found, starts)
        if ground is not None and (flush := flush_on_slope(stage, place, name, rows, data, ground)) is not None:
            # the drop's own rest kept beside it: what the object falls back to when flush rests worse
            poses[name] = {"before": before, "after": flush[0] @ before, "rested": True, "said": flush[1],
                           "fallback": dropped}
        else:
            poses[name] = dropped
    written = {name: {key: pose[key] for key in ("before", "after")} | {"middle": object_middle(stage, place, name)}
               for name, pose in poses.items() if pose["after"] is not pose["before"]}
    for name, found in carried_with(stage, place, inventory, written).items():
        poses[name] = {**found, "rested": True, "said": "carried with what it lies on"}
    return poses


def dropped_pose(stage, place, name, found, starts):
    """Where the drop alone leaves one loose object that came to rest (rest_poses): stood upright on its lowest foot
    after a tip onto uneven feet, kept as laid past the limits, else rested where the drop left it."""
    before = laid_matrix(stage, place, name)
    entry = {"before": before, "after": np.asarray(found["motion"]) @ before,
             "middle": object_middle(stage, place, name), "uneven": uneven_feet(stage, place, name),
             "base lean": base_lean(stage, place, name)}
    turned, drift = correction(entry)
    said = f"turns {turned:.0f} degrees and drifts {drift * 100:.0f} cm to rest"
    piece = max(UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_]).ComputeWorldBound(
        stage.GetPrimAtPath(f"/{place}/Objects/{name}")).ComputeAlignedRange().GetSize())
    debris = piece <= DEBRIS_SIZE
    if tips_on_uneven_feet(tip := {**entry, "before": starts.get(name, np.eye(4)) @ before}):
        # the tip from where its drop started: an old settle's tip onto the same feet is no rest either
        start = touching(stage, place, name, starts.get(name, np.eye(4)), np.asarray(found["motion"]))
        return {"before": before, "after": start @ before, "rested": False,
                "said": f"{said}{uneven_said(tip)}; stood upright on its lowest foot"}
    if (not debris and turned > TURN_MOST) or drift > (DEBRIS_DRIFT if debris else DRIFT_MOST):
        return {"before": before, "after": before, "rested": False, "said": f"would not rest as laid: {said}"}
    return {**entry, "rested": True, "said": said}


def flush_on_slope(stage, place, name, rows, data, ground):
    """(the motion from as laid, stage frame, column vectors; what it did) that stands an object flush on the ground's
    slope under it: its up turned onto the slope's normal about its middle, its heading kept, then let down (or up)
    until its lowest point meets the ground. None for one that lies as laid (lies_as_laid) or stands on no sloping
    ground (triage.ground_plane: off the ground, or the ground under it level). The drop drops the seed's model, whose
    feet or base the paint levels before its bake: on the campgrounds' 5 to 6.6 degree slopes it tipped the crane
    onto its seed's uneven feet (17 degrees, kept as laid) and left the reactor 1.7 degrees off the slope, a foot of
    the baked model 6.5 cm up (2026-10-15). On the slope's plane every levelled foot touches."""
    import triage
    import trimesh
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    if lies_as_laid(rows.get(prim.GetAttribute("score:row").Get(), {}), data):
        return None
    points = object_points(stage, place, name)
    plane = triage.ground_plane(trimesh.PointCloud(points), ground)
    if plane is None:
        return None
    normal = np.array([-plane[0], 1.0, -plane[1]]) / np.linalg.norm([plane[0], 1.0, plane[1]])
    laid = laid_matrix(stage, place, name)
    up = laid[:3, 1] / np.linalg.norm(laid[:3, 1])
    turn = Rotation.align_vectors([normal], [up])[0].as_matrix()
    middle = points.mean(axis=0)
    motion = np.eye(4)
    motion[:3, :3] = turn
    motion[:3, 3] = middle - turn @ middle
    moved = points @ turn.T + motion[:3, 3]
    lift = float(np.nanmin(moved[:, 1] - ground(moved[:, [0, 2]])))
    motion[1, 3] -= lift
    tilt = math.degrees(math.atan(math.hypot(plane[0], plane[1])))
    turned = math.degrees(Rotation.from_matrix(turn).magnitude())
    return motion, (f"stood flush on the ground's {tilt:.1f} degree slope (turned {turned:.1f} degrees) and let "
                    f"{'down' if lift > 0 else 'up'} {abs(lift) * 100:.1f} cm")


def layout_pose(matrix, ground, scale):
    """A settled matrix (stage frame, column vectors) as the layout says it: spot (x, z), lift off the ground there,
    and the turn in the piece's own seat frame as a quaternion [x, y, z, w]."""
    matrix = np.asarray(matrix, dtype=float)
    position, turn_in_stage = matrix[:3, 3], matrix[:3, :3] / scale
    if ground is None:
        return position[0], position[2], position[1], turn_in_stage
    across, along = position[0], position[2]
    for _ in range(4):  # the spot under the position: the seat's flat numbers, found by walking the residual off
        foot, seat_turn = ground.standing(across, along, 0.0)
        up = seat_turn[1]
        lift = float((position - foot) @ up)
        sideways = position - foot - lift * up
        across += float(sideways @ seat_turn[0])
        along += float(sideways @ seat_turn[2])
    foot, seat_turn = ground.standing(across, along, 0.0)
    lift = float((position - foot) @ seat_turn[1])
    return across, along, lift, seat_turn @ turn_in_stage


def heading_of(turn):
    """The bearing a turn faces (the layout's `facing`): where it lays the piece's own +x, flat, in degrees."""
    return round(math.degrees(math.atan2(turn[2, 0], turn[0, 0])), 2) % 360.0


def settled_spot(spot, across, along, lift, turn):
    """A layout spot (or kit piece) moved to where its object came to rest."""
    quaternion = Rotation.from_matrix(turn).as_quat()
    spot = {key: value for key, value in spot.items() if key != "tilt"}
    spot["rotation"] = [round(float(value), 6) for value in quaternion]
    spot["facing"] = heading_of(turn)
    if "at" in spot:  # a kit piece
        spot["at"] = [round(across, 4), round(lift, 4), round(along, 4)]
    else:  # an inventory spot
        spot.update(x=round(across, 4), y=round(lift, 4), z=round(along, 4))
    return spot


def laid_matrix(stage, place, name):
    """An object's matrix as the stage lays it, in the stage's frame, column vectors."""
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    return np.asarray(UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(Usd.TimeCode.Default())).T


def correction(found):
    """How far an object turned (degrees) and how far its middle drifted (metres) from as laid to at rest."""
    before, after = np.asarray(found["before"]), np.asarray(found["after"])
    motion = after @ np.linalg.inv(before)
    turned = math.degrees(Rotation.from_matrix(motion[:3, :3] / np.cbrt(np.linalg.det(motion[:3, :3]))).magnitude())
    middle = np.append(np.asarray(found.get("middle", (0.0, 0.0, 0.0)), dtype=float), 1.0)
    return turned, float(np.linalg.norm((after @ middle - before @ middle)[:3]))


def uneven_feet(stage, place, name):
    """How far (metres, in its own frame as laid: its scale kept, its turn taken off) an object's highest foot ends
    over its lowest, when it has three feet or more (triage.foot_clusters, as the triage finds them), else 0."""
    import triage
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    points, triangles = resting.in_stage(prim.GetChild("geo"))
    laid = laid_matrix(stage, place, name)
    turn = laid[:3, :3] / np.cbrt(np.linalg.det(laid[:3, :3]))
    own = (points - laid[:3, 3]) @ turn
    height = float(np.ptp(own[:, 1]))
    found = [low for _, low in triage.foot_clusters(own, triangles, max(triage.LOW_BAND, FOOT_BAND * height))]
    return found[-1] - found[0] if len(found) >= 3 else 0.0


def base_lean(stage, place, name):
    """How far (degrees) the face of an object's convex hull straight under its weight (resting.weight_at) leans from
    its own up, in its own frame as laid: the tip its own shape gives it on a level floor, whatever its feet are joined
    by. A wheeled chair's five casters are one foot to the clusters (its star base joins them), so uneven_feet read
    the lab's old chair as even while its hull, one caster 2.4 cm up, leans 4.8 degrees: the drop's tip (2026-10-15)."""
    prim = stage.GetPrimAtPath(f"/{place}/Objects/{name}")
    points, triangles = resting.in_stage(prim.GetChild("geo"))
    laid = laid_matrix(stage, place, name)
    turn = laid[:3, :3] / np.cbrt(np.linalg.det(laid[:3, :3]))
    own = trimesh.Trimesh((points - laid[:3, 3]) @ turn, np.asarray(triangles).reshape(-1, 3), process=False)
    across, along = resting.weight_at(own)
    hull = own.convex_hull
    hits, _, faces = hull.ray.intersects_location([[across, own.bounds[1][1] + 1.0, along]], [[0.0, -1.0, 0.0]])
    if not len(faces):
        return 0.0
    normal = hull.face_normals[faces[np.argmin(hits[:, 1])]]
    return float(np.degrees(np.arccos(np.clip(-normal[1], -1.0, 1.0))))


def tips_on_uneven_feet(found):
    """Whether a drop tipped an object over the triage's LEAN_MOST onto feet that do not lie in one plane in its own
    frame (`uneven`: uneven_feet over the resting tolerance, or `base lean`: base_lean over LEAN_MOST): the tip is the
    model's fault, not a rest pose, so it is never written (the greenhouse's water tank, 2026-10-12: tipped 7.5 degrees
    onto three of its legs, written into the kit, one foot left 7 cm up; the lab's desk chairs, 4.8 degrees onto a
    raised caster, 2026-10-15)."""
    import triage
    uneven = found.get("uneven", 0.0) > resting.TOLERANCE or found.get("base lean", 0.0) > triage.LEAN_MOST
    return uneven and correction(found)[0] > triage.LEAN_MOST


def uneven_said(found):
    """The words an unrested mark adds for a tip onto uneven feet, '' for any other settle."""
    if not tips_on_uneven_feet(found):
        return ""
    if found.get("uneven", 0.0) > resting.TOLERANCE:
        return f" onto feet ending up to {found['uneven'] * 100:.1f} cm apart in its own frame (level the model's feet)"
    return f" onto a base leaning {found['base lean']:.1f} degrees in its own frame (level the model's feet)"


def unstable(turned, drift):
    """Whether a drop moved an object too far to call it resting as laid (SAGE's rule)."""
    return drift > SAGE_MOVE or turned > SAGE_TURN


def object_middle(stage, place, name):
    """The middle of an object's drawn mesh, in its own frame."""
    extent = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{place}/Objects/{name}/geo")).GetExtentAttr().Get()
    return [(float(low) + float(high)) / 2 for low, high in zip(extent[0], extent[1])]


def write_layout(settled, ground, inventory_path, kit_path):
    """Every settled object (its "before" and "after" matrices, its "middle" in its own frame) written into its spot
    and its piece when coming to rest is a small correction (at most TURN_MOST and DRIFT_MOST); one that would move
    more keeps its laid pose and is marked `unrested` with what it would do, for the layout to be put right (a support,
    a laid pose that rests, a bed in the ground). The objects, with what each did."""
    kit = json.loads(kit_path.read_text())
    if any("row" not in piece for piece in kit["pieces"]):
        return write_kit_room(settled, kit, kit_path)
    inventory = json.loads(inventory_path.read_text())
    spots = {row["id"]: row["at"] for row in inventory["rows"]}
    pieces = {}
    for piece in kit["pieces"]:
        pieces.setdefault(piece["row"], []).append(piece)
    moved = {}
    for name, found in settled.items():
        row, number = name.rsplit("_", 1)
        index = int(number) - 1
        turned, drift = correction(found)
        said = f"turns {turned:.0f} degrees and drifts {drift * 100:.0f} cm to rest"
        debris = max(pieces[row][index]["size"]) <= DEBRIS_SIZE
        said += uneven_said(found)
        if tips_on_uneven_feet(found) or (not debris and turned > TURN_MOST) or \
                drift > (DEBRIS_DRIFT if debris else DRIFT_MOST):
            spots[row][index]["unrested"] = pieces[row][index]["unrested"] = said
            moved[name] = f"would not rest as laid: {said}"
            continue
        spots[row][index].pop("unrested", None)
        pieces[row][index].pop("unrested", None)
        scale = float(pieces[row][index].get("scale", 1.0))
        across, along, lift, turn = layout_pose(found["after"], ground, scale)
        spots[row][index] = settled_spot(spots[row][index], across, along, lift, turn)
        pieces[row][index].update(settled_spot(pieces[row][index], across, along, lift, turn))
        pieces[row][index].pop("tilt", None)
        moved[name] = said
    inventory_path.write_text(json.dumps(inventory, indent=1, ensure_ascii=False) + "\n")
    kit_path.write_text(json.dumps(kit, indent="\t", ensure_ascii=False) + "\n")
    return moved


def kit_room_pieces(kit, place):
    """A kit room's pieces (the game's kit: each its kind's row, as export.kit_room_pieces names them) by object name
    (`<row>_<n>` in the layout's order; a glowing part `<row>_<part>_<n>`)."""
    import export
    counts, found = {}, {}
    for piece in kit["pieces"]:
        row = piece.get("row", export.kind_row(piece["kind"], (kit.get("room", ""), place)))
        row = f"{row}_{piece['part']}" if "part" in piece else row
        counts[row] = counts.get(row, 0) + 1
        found[f"{row}_{counts[row]}"] = piece
    return found


def moved_piece(piece, before, after):
    """A kit room piece moved as its object moved from `before` to `after` (stage frame, which is the room's): its
    axes turned and its foot `at` carried by the motion (package.kit_matrix stands the model's foot on `at`)."""
    motion = np.asarray(after) @ np.linalg.inv(np.asarray(before))
    turn = motion[:3, :3] / np.cbrt(np.linalg.det(motion[:3, :3]))
    axes = {axis: turn @ np.asarray(piece[axis], dtype=float) for axis in ("x", "y", "z")}
    at = motion[:3, :3] @ np.asarray(piece["at"], dtype=float) + motion[:3, 3]
    return dict(piece, at=[round(float(value), 4) for value in at],
                **{axis: [round(float(value), 6) for value in way / np.linalg.norm(way)] for axis, way in axes.items()})


def write_kit_room(settled, kit, kit_path):
    """write_layout for a kit room (data/kit/<room>.json laid in the stage's own frame, no inventory spots): each piece
    whose object came to rest by a small correction turned and carried with it, the others marked `unrested`. A piece
    whose axes are not its object's as the stage lays it (another frame) is refused."""
    pieces = kit_room_pieces(kit, kit_path.stem)
    moved = {}
    for name, found in settled.items():
        piece = pieces[name]
        laid = np.asarray(found["before"])[:3, :3]
        laid = laid / np.linalg.norm(laid, axis=0)
        if not np.allclose(laid, np.column_stack([piece[axis] for axis in ("x", "y", "z")]), atol=1e-3):
            raise ValueError(f"{name}: its kit piece is not laid in the stage's frame; the room cannot be written back")
        turned, drift = correction(found)
        said = f"turns {turned:.0f} degrees and drifts {drift * 100:.0f} cm to rest"
        debris = max(piece["size"]) <= DEBRIS_SIZE
        said += uneven_said(found)
        if tips_on_uneven_feet(found) or (not debris and turned > TURN_MOST) or \
                drift > (DEBRIS_DRIFT if debris else DRIFT_MOST):
            piece["unrested"] = said
            moved[name] = f"would not rest as laid: {said}"
            continue
        piece.pop("unrested", None)
        piece.update(moved_piece(piece, found["before"], found["after"]))
        moved[name] = said
    kit_path.write_text(json.dumps(kit, indent="\t", ensure_ascii=False) + "\n")
    return moved


def detach(stage_path):
    """Rerun this call detached (tools/props/cloud/detached.py); its outputs are the settle folder and the layout."""
    sys.path.insert(0, str(REPO / "tools/props/cloud"))
    import detached
    stage = Usd.Stage.Open(str(stage_path))  # held: a prim of a stage nothing holds expires at once
    place = stage.GetDefaultPrim().GetName()
    detached.relaunch(sys.argv, "settle", [stage_path.parent / "settle", stage_inputs.inventory_path(place),
                                           KITS / f"{place}.json"])


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true", help="simulate and print, write nothing")
    parser.add_argument("--cloud", action="store_true", help="simulate on a rented processor machine")
    parser.add_argument("--reuse", action="store_true", help="write back the last run's result (settle/settled.json)")
    parser.add_argument("--detach", action="store_true", help="progress to a log, one result line at the end "
                        "(tools/props/cloud/detached.py): start it with run_in_background, never poll it")
    arguments = parser.parse_args()
    stage_path = arguments.stage.resolve()
    if arguments.detach:
        detach(stage_path)
    stage = Usd.Stage.Open(str(stage_path))
    place = stage.GetDefaultPrim().GetName()
    inventory_path, kit_path = stage_inputs.inventory_path(place), KITS / f"{place}.json"
    last = stage_path.parent / "settle" / "settled.json"
    inventory = json.loads(inventory_path.read_text())
    loose, ignore, starts, under = drop_job(stage, place, inventory, upright=not arguments.dry_run)
    simulated = (json.loads(last.read_text()) if arguments.reuse
                 else simulate(stage_path, loose, stage_path.parent / "settle", arguments.cloud, ignore, starts, under))
    for first, second in simulated["overlaps"]:
        print(f"{first} and {second} came to rest inside each other")
    settled = {}
    for name, found in sorted(simulated["objects"].items()):
        if found["inside"] and not arguments.dry_run:  # its drop, on the bare ground alone, is no rest pose
            print(f"{name}: laid inside {', '.join(found['inside'])}; left as laid (put its layout right first)")
            continue
        if found["inside"]:
            print(f"{name}: laid inside {', '.join(found['inside'])}; settled on the ground alone")
        if found["moving"] > STILL:
            print(f"{name}: still moving {found['moving']:.2f} m/s at the end; left as laid")
            continue
        before = laid_matrix(stage, place, name)
        settled[name] = {"before": before, "after": np.asarray(found["motion"]) @ before,
                         "middle": object_middle(stage, place, name), "uneven": uneven_feet(stage, place, name),
                         "base lean": base_lean(stage, place, name)}
    if not arguments.dry_run:
        settled.update(carried_with(stage, place, json.loads(inventory_path.read_text()), settled))
    if arguments.dry_run:
        for name, found in settled.items():
            turned, drift = correction(found)
            print(name, np.round(found["after"][:3, 3] - found["before"][:3, 3], 3),
                  "unstable (SAGE)" if unstable(turned, drift) else "")
        return
    kit = json.loads(kit_path.read_text())
    ground = grounds.place_ground(place, kit.get("on_seat", [0.0, 0.0]))
    moved = write_layout(settled, ground, inventory_path, kit_path)
    (stage_path.parent / "settle" / "expected.json").write_text(json.dumps(
        {name: found["after"].tolist() for name, found in settled.items()}, indent=1))
    for name, said in sorted(moved.items()):
        print(f"{name}: {said}")


if __name__ == "__main__":
    main()
