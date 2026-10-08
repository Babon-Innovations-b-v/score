"""Settle a place's loose objects with physics and write where they came to rest into its layout.

    .venv/bin/python tools/usd/settle.py <stage.usda> [--dry-run] [--cloud] [--reuse]

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
a laid pose that rests, or a bed in the ground under it). Export the stage again after, and
run the resting check (tools/usd/resting.py).
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
import ground as grounds  # noqa: E402
import resting  # noqa: E402

SESSION = REPO / "tools/blender/session.py"
INSIDE = REPO / "tools/blender/inside/settle_stage.py"
KITS = REPO / "data/kit"
INVENTORIES = REPO / "data/inventory"
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


def loose_objects(stage, place, inventory):
    """The stage's top-level objects whose row lies loose on the ground: {object name: its lift for the drop}."""
    rows = {row["id"]: row for row in inventory["rows"]}
    height = resting.ground_height(stage, place)
    found = {}
    for path, prim in resting.objects_of(stage, place).items():
        name = path.removeprefix(f"/{place}/Objects/")
        row = rows.get(prim.GetAttribute("score:row").Get(), {})
        if "/" in name or row.get("fixed") or row.get("anchor", "") not in LOOSE_ANCHORS:
            continue
        points, _ = resting.in_stage(prim.GetChild("geo"))
        clearance = points[:, 1] - height(points[:, [0, 2]])
        found[name] = max(0.0, SETTLE_DROP - float(np.nanmin(clearance)))
    return found


def simulate(stage_path, loose, folder, cloud=False):
    """The Blender run: how each loose object moved from as laid to at rest (stage frame, column vectors), how fast
    it still moved at the end, and the static objects it started inside."""
    folder.mkdir(parents=True, exist_ok=True)
    job, out = folder / "settle-job.json", folder / "settled.json"
    job.write_text(json.dumps({"loose": sorted(loose), "lift": loose}, indent=1))
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


def object_middle(stage, place, name):
    """The middle of an object's drawn mesh, in its own frame."""
    extent = UsdGeom.Mesh(stage.GetPrimAtPath(f"/{place}/Objects/{name}/geo")).GetExtentAttr().Get()
    return [(float(low) + float(high)) / 2 for low, high in zip(extent[0], extent[1])]


def write_layout(settled, ground, inventory_path, kit_path):
    """Every settled object (its "before" and "after" matrices, its "middle" in its own frame) written into its spot
    and its piece when coming to rest is a small correction (at most TURN_MOST and DRIFT_MOST); one that would move
    more keeps its laid pose and is marked `unrested` with what it would do, for the layout to be put right (a support,
    a laid pose that rests, a bed in the ground). The objects, with what each did."""
    inventory = json.loads(inventory_path.read_text())
    kit = json.loads(kit_path.read_text())
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


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("stage", type=pathlib.Path)
    parser.add_argument("--dry-run", action="store_true", help="simulate and print, write nothing")
    parser.add_argument("--cloud", action="store_true", help="simulate on a rented processor machine")
    parser.add_argument("--reuse", action="store_true", help="write back the last run's result (settle/settled.json)")
    arguments = parser.parse_args()
    stage_path = arguments.stage.resolve()
    stage = Usd.Stage.Open(str(stage_path))
    place = stage.GetDefaultPrim().GetName()
    inventory_path, kit_path = INVENTORIES / f"{place}.json", KITS / f"{place}.json"
    loose = loose_objects(stage, place, json.loads(inventory_path.read_text()))
    last = stage_path.parent / "settle" / "settled.json"
    simulated = (json.loads(last.read_text()) if arguments.reuse
                 else simulate(stage_path, loose, stage_path.parent / "settle", arguments.cloud))
    for first, second in simulated["overlaps"]:
        print(f"{first} and {second} came to rest inside each other")
    settled = {}
    for name, found in sorted(simulated["objects"].items()):
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
            print(name, np.round(found["after"][:3, 3] - found["before"][:3, 3], 3))
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
