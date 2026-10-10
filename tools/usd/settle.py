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
a laid pose that rests, or a bed in the ground under it). A piece the drop found laid inside a static one was dropped
on the bare ground alone, so its result is no rest pose and is not written: its layout is put right first. Export the
stage again after, and run the resting check (tools/usd/resting.py).
"""
import argparse
import json
import math
import pathlib
import subprocess
import sys

import numpy as np
from pxr import Usd, UsdGeom
from scipy.spatial.transform import Rotation

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import complete  # noqa: E402
import ground as grounds  # noqa: E402
import resting  # noqa: E402

SESSION = REPO / "tools/blender/session.py"
INSIDE = REPO / "tools/blender/inside/settle_stage.py"
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
SAGE_MOVE = 0.2
SAGE_TURN = 8.0


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
    """The scene record's Fixtures lying on a loose object (the workshop's robot and parts trays on its robot bench):
    each whose footprint lies within a loose object's and whose foot stands over that object's middle height. The drop
    leaves them out of its statics, as it does what is held on a loose object (held_on_loose): the holder raised by the
    nudge meets them, and a holder whose hull closes over them is thrown off them."""
    cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])
    root = stage.GetPrimAtPath(f"/{place}/Fixtures")
    if not root.IsValid():
        return []
    boxes = {}
    for name in loose:
        box = cache.ComputeWorldBound(stage.GetPrimAtPath(f"/{place}/Objects/{name}")).ComputeAlignedRange()
        boxes[name] = (np.asarray(box.GetMin()), np.asarray(box.GetMax()))
    found = []
    for prim in root.GetChildren():
        box = cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if box.IsEmpty():
            continue
        low, high = np.asarray(box.GetMin()), np.asarray(box.GetMax())
        if any(np.all(low[[0, 2]] >= under[0][[0, 2]] - FOOTPRINT_SLACK)
               and np.all(high[[0, 2]] <= under[1][[0, 2]] + FOOTPRINT_SLACK)
               and low[1] >= (under[0][1] + under[1][1]) / 2 for under in boxes.values()):
            found.append(prim.GetName())
    return sorted(found)


def simulate(stage_path, loose, folder, cloud=False, ignore=()):
    """The Blender run: how each loose object moved from as laid to at rest (stage frame, column vectors), how fast
    it still moved at the end, and the static objects it started inside; `ignore` are objects left out of the
    statics (part_objects, held_on_loose, fixtures_on_loose)."""
    folder.mkdir(parents=True, exist_ok=True)
    job, out = folder / "settle-job.json", folder / "settled.json"
    job.write_text(json.dumps({"loose": sorted(loose), "lift": loose, "ignore": sorted(ignore)}, indent=1))
    if out.exists():
        out.unlink()
    if cloud:  # a rented processor machine (tools/props/cloud/blender_cloud.py), not this PC's one Blender
        sys.path.insert(0, str(REPO / "tools/props/cloud"))
        import blender_cloud
        blender_cloud.run_elsewhere(INSIDE, [stage_path, job, out], [stage_path.parent, job], [out],
                                    blender_cloud.DEFAULT_CLASSES, "settle", minutes=15)
        return json.loads(out.read_text())
    command = [sys.executable, str(SESSION), "batch", str(INSIDE), "--", str(stage_path), str(job), str(out)]
    if subprocess.run(command, stdout=subprocess.DEVNULL).returncode != 0 or not out.exists():
        raise RuntimeError(f"the settle run failed; run it by hand to see its output: {command}")
    return json.loads(out.read_text())


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
        if (not debris and turned > TURN_MOST) or drift > (DEBRIS_DRIFT if debris else DRIFT_MOST):
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
        if (not debris and turned > TURN_MOST) or drift > (DEBRIS_DRIFT if debris else DRIFT_MOST):
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
    detached.relaunch(sys.argv, "settle", [stage_path.parent / "settle", complete.inventory_path(place),
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
    inventory_path, kit_path = complete.inventory_path(place), KITS / f"{place}.json"
    loose = loose_objects(stage, place, json.loads(inventory_path.read_text()))
    last = stage_path.parent / "settle" / "settled.json"
    inventory = json.loads(inventory_path.read_text())
    ignore = (part_objects(stage, place, inventory) + held_on_loose(stage, place, inventory, loose)
              + fixtures_on_loose(stage, place, loose))
    simulated = (json.loads(last.read_text()) if arguments.reuse
                 else simulate(stage_path, loose, stage_path.parent / "settle", arguments.cloud, ignore))
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
                         "middle": object_middle(stage, place, name)}
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
