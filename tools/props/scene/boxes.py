"""Turn MoGe-2's points and SAM 3's masks into the room's shape and a box for every object, in metres.

    ~/.farm-factory-props/env/bin/python tools/props/scene/boxes.py <room>

Reads depth.npz (depth.py), surfaces.npz and objects.json with the masks under objects/
(cutout.py), and writes boxes.json (measured on Marble's room instead, with --depth
depth-marble.npz from marble.py, boxes-depth-marble.json). The room's frame is the game's: y up from the floor, x across
the module with 0 halfway between its walls, and the target picture's camera on z = 0 heading
along -z, which the target was drawn looking along the module's length. What it measures:

  floor    a plane fitted to the floor's points (RANSAC), which sets up and the camera's height.
  section  the module's cross-section, read off the points rather than fitted: how wide the floor
           is, how wide the room is at its widest and at what height, how high the ceiling is, and
           where the far end wall stands. A circle or an ellipse fitted to the habitat's walls
           missed by 0.2 to 0.4 m on average: the "curved wall" mask runs over furniture, the end
           wall and the near ring frame, so percentiles of the right points do better.
  objects  for each mask, the box of its points (2nd to 98th percentile, so stray edge pixels do
           not stretch it). A box holds only what the picture showed: the back of an object, and
           anything hidden behind a neighbour, is not in it. layout.py snaps the boxes to the room
           and to known sizes.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from paths import scene_folder as folder  # noqa: E402

# Floor plane fitting: how many tries, and how near a point must be to count as on the plane.
TRIES = 400
ON_PLANE_M = 0.03
# The band of wall heights the widest point is looked for in, above the furniture's tops.
WALL_BAND_M = (1.2, 2.4)
# Wall points this near the far end belong to the end wall, which stands across the module.
END_WALL_M = 0.6
# Pixels peeled off a mask's edge before its points are read: edges mix object and background.
EDGE_PIXELS = 2
# The share of points left out at each end, for a box and for each edge of the section.
LOW, HIGH = 2.0, 98.0


def camera_points(points):
    """MoGe-2's points (x right, y down, z ahead) in the game's camera frame (y up, -z ahead)."""
    return points * np.array([1.0, -1.0, -1.0])


def floor_plane(points, seed=0):
    """The plane through the most floor points, as (unit normal pointing up at the camera, offset)
    with normal . p + offset = height above the floor."""
    random = np.random.default_rng(seed)
    best, best_count = None, -1
    for _ in range(TRIES):
        trio = points[random.choice(len(points), 3, replace=False)]
        normal = np.cross(trio[1] - trio[0], trio[2] - trio[0])
        if np.linalg.norm(normal) < 1e-9:
            continue
        normal /= np.linalg.norm(normal)
        offset = -normal @ trio[0]
        count = int((np.abs(points @ normal + offset) < ON_PLANE_M).sum())
        if count > best_count:
            best, best_count = (normal, offset), count
    normal, offset = best
    # The camera, at the origin, is above the floor.
    return (normal, offset) if offset > 0 else (-normal, -offset)


def room_turn(normal):
    """The 3x3 turn from the camera frame to a frame with y along the floor's normal and the
    camera's heading, flattened onto the floor, along -z."""
    up = normal
    ahead = np.array([0.0, 0.0, -1.0])
    ahead = ahead - (ahead @ up) * up
    ahead /= np.linalg.norm(ahead)
    across = np.cross(ahead, up)
    return np.stack([across, up, -ahead])


def section(floor, walls, ceiling):
    """The module's cross-section from its floor, wall and ceiling points in the room frame, with
    x not yet centred: the middle's x, and the measures by name."""
    far_end = float(np.percentile(np.concatenate([walls[:, 2], floor[:, 2]]), 1))
    # SAM 3 found no wall at all in the night cabin, whose curved walls run into its ceiling: the
    # ceiling's points stand in for them then.
    shell = walls if len(walls) else ceiling
    side = shell[(shell[:, 1] > WALL_BAND_M[0]) & (shell[:, 1] < WALL_BAND_M[1])
                 & (shell[:, 2] > far_end + END_WALL_M)]
    if not len(side):
        side = shell
    left, right = np.percentile(side[:, 0], LOW), np.percentile(side[:, 0], HIGH)
    middle = (left + right) / 2
    widest_at = [float(np.median(side[side[:, 0] < np.percentile(side[:, 0], 5), 1])),
                 float(np.median(side[side[:, 0] > np.percentile(side[:, 0], 95), 1]))]
    floor_left, floor_right = np.percentile(floor[:, 0], LOW), np.percentile(floor[:, 0], HIGH)
    return middle, {
        "floor_half_width": round(float(floor_right - floor_left) / 2, 3),
        "floor_middle": round(float((floor_left + floor_right) / 2 - middle), 3),
        "widest_half_width": round(float(right - left) / 2, 3),
        "widest_height": round(float(np.mean(widest_at)), 3),
        "ceiling": round(float(np.percentile(ceiling[:, 1], HIGH)), 3),
        "far_end": round(far_end, 3),
    }


def peeled(mask):
    """The mask with EDGE_PIXELS taken off its edge."""
    inner = mask.copy()
    for _ in range(EDGE_PIXELS):
        inner[1:-1, 1:-1] &= inner[:-2, 1:-1] & inner[2:, 1:-1] & inner[1:-1, :-2] & inner[1:-1, 2:]
    return inner if inner.any() else mask


def box(points):
    """The box round an object's points, as (lowest corner, highest corner)."""
    return np.percentile(points, LOW, axis=0), np.percentile(points, HIGH, axis=0)


def fitted(mask, shape):
    """A mask at the size of the points it picks from (Marble's are measured at half size)."""
    if mask.shape == shape:
        return mask
    return np.asarray(Image.fromarray(mask).resize(shape[::-1], Image.NEAREST))


def measure(room, depth_file="depth.npz"):
    """The room's shape and every object's box, in the room frame, from one source of points."""
    out = folder(room)
    depth = np.load(out / depth_file)
    points = camera_points(depth["points"])
    shape = points.shape[:2]
    surfaces = {name: fitted(mask, shape) for name, mask in np.load(out / "surfaces.npz").items()}
    valid = depth["valid"] & np.isfinite(points).all(axis=2)
    normal, offset = floor_plane(points[peeled(surfaces["floor"]) & valid])
    turn = room_turn(normal)

    def to_room(mask):
        return points[mask & valid] @ turn.T + np.array([0.0, offset, 0.0])

    middle, measures = section(to_room(peeled(surfaces["floor"])),
                               to_room(surfaces["wall"] & ~surfaces["floor"] & ~surfaces["ceiling"]),
                               to_room(surfaces["ceiling"]))
    shift = np.array([middle, 0.0, 0.0])
    objects = []
    for item in json.loads((out / "objects.json").read_text()):
        mask = fitted(np.asarray(Image.open(out / "objects" / f"{item['key']}.mask.png")) > 127, shape)
        seen = to_room(peeled(mask)) - shift
        low, high = box(seen)
        objects.append({**item, "low": low.round(3).tolist(), "high": high.round(3).tolist(),
                        "points": int(len(seen))})
    intrinsics = depth["intrinsics"]
    return {
        "camera": {"position": [round(-float(middle), 3), round(float(offset), 3), 0.0],
                   "ahead": (turn @ np.array([0.0, 0.0, -1.0])).round(4).tolist(),
                   "up": (turn @ np.array([0.0, 1.0, 0.0])).round(4).tolist(),
                   "fov_vertical": round(float(np.degrees(2 * np.arctan(0.5 / intrinsics[1, 1]))), 2)},
        "section": measures,
        "objects": objects,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("room")
    parser.add_argument("--depth", default="depth.npz",
                        help="the points to measure: depth.npz (MoGe-2) or depth-marble.npz (marble.py)")
    options = parser.parse_args()
    measured = measure(options.room, options.depth)
    name = "boxes.json" if options.depth == "depth.npz" else f"boxes-{pathlib.Path(options.depth).stem}.json"
    (folder(options.room) / name).write_text(json.dumps(measured, indent=1))
    print(json.dumps({key: measured[key] for key in ("camera", "section")}))
    for item in measured["objects"]:
        size = np.subtract(item["high"], item["low"]).round(2).tolist()
        print(f"{item['key']:22s} low {item['low']} size {size}")


if __name__ == "__main__":
    main()
