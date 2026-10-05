"""Close-ups of every inventory item out of a plan world's own 3D, for the object maker (the owner, 2026-10-05:
"the entire value of Marble is having the actual 3D explorable scene").

    ~/.farm-factory-props/env/bin/python tools/props/scene/closeups.py <world folder> <items.json> [--out <folder>]

The world folder holds what marble.py fetches for free: collider.glb, metric.json and the splats as PLY
(splats.ply, marble.py `splats`). items.json lists the items in the world's own frame, in metres:

    {"down": [0, 1, 0],                        # the world's down: Marble's frame is x right, y down, z ahead
     "items": [{"id": "rack", "name": "equipment rack", "centre": [x, y, z],
                "size": [0.6, 0.6, 1.9], "facing": [fx, 0, fz]}]}             # wide, deep, tall; out of its front

For every item this plans four cameras from its centre, size and facing, never by eye: a front view that fills the
frame with it, a three-quarter view from each side and one from slightly above. Each camera is checked against the
collider: a wall between the item and the camera pulls the camera in to stand clear of it, the lens widened to keep
the item whole, a camera blocked low (by a rail) is raised to
see over it, and one with still no room to stand, or outside the room, is dropped. Each camera also carries the
points to prompt the segmenter with, projected from 3D: the item's own (its front face) and every other item's in
view, so the item's mask is resolved against its neighbours', the highest score winning each pixel, as in page A's
partition.

Writes <out>/cameras.json. Rendering the splats and segmenting run on a rented card (closeups_gpu.py through
cloud/closeups_cloud.py); this file is plain numpy and trimesh and holds the geometry both sides share, so it is
tested on its own (closeups_test.py).
"""
import argparse
import json
import math
import pathlib

import numpy as np

# The share of the frame the item's larger side spans, the lens, the picture's side in pixels.
FILL = 0.8
FOV_DEGREES = 45.0
# The widest lens a pulled-in camera may use (measured on the hub, 2026-10-05: a 1.7 m rack behind the rail needs 103)
MAX_FOV_DEGREES = 110.0
SIZE = 1536
# The three-quarter turns either side of the front, and the tilt of the view from above.
SIDE_TURN_DEGREES = 40.0
ABOVE_TILT_DEGREES = 35.0
# How far a camera stands off a wall it was pulled in by, and the nearest it may stand to the item's front.
CLEARANCE_M = 0.25
NEAREST_M = 0.35
# The item's prompt points are spread this share of its width and height round its front face's centre.
SPREAD = 0.25
# A camera blocked low (by a rail, a desk) tries again raised by these tilts before it is dropped.
RAISES = (25.0, 50.0)
SHOTS = (("front", 0.0, 0.0), ("left", SIDE_TURN_DEGREES, 0.0), ("right", -SIDE_TURN_DEGREES, 0.0),
         ("above", 0.0, ABOVE_TILT_DEGREES))


def unit(vector):
    vector = np.asarray(vector, dtype=np.float64)
    return vector / np.linalg.norm(vector)


def turned(facing, down, degrees):
    """The facing turned about the down axis by `degrees` (Rodrigues)."""
    axis = unit(down)
    angle = math.radians(degrees)
    facing = np.asarray(facing, dtype=np.float64)
    return unit(facing * math.cos(angle) + np.cross(axis, facing) * math.sin(angle)
                + axis * np.dot(axis, facing) * (1 - math.cos(angle)))


def tilted(direction, down, degrees):
    """The direction raised toward up by `degrees`."""
    up = -unit(down)
    return unit(direction * math.cos(math.radians(degrees)) + up * math.sin(math.radians(degrees)))


def hits(triangles, origin, direction):
    """Every distance along a ray at which it crosses a triangle, sorted (Moller-Trumbore over all of them)."""
    first, edge1, edge2 = triangles[:, 0], triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
    across = np.cross(direction, edge2)
    det = np.einsum("ij,ij->i", edge1, across)
    usable = np.abs(det) > 1e-12
    inverse = np.where(usable, 1.0 / np.where(usable, det, 1.0), 0.0)
    offset = origin - first
    along_u = np.einsum("ij,ij->i", offset, across) * inverse
    lifted = np.cross(offset, edge1)
    along_v = (lifted @ direction) * inverse
    travel = np.einsum("ij,ij->i", edge2, lifted) * inverse
    crossed = usable & (along_u >= 0) & (along_v >= 0) & (along_u + along_v <= 1) & (travel > 1e-6)
    return np.sort(travel[crossed])


def inside_room(triangles, point, down):
    """Whether a point stands inside the collider's room: something above it and something below it."""
    return bool(len(hits(triangles, point, unit(down)))) and bool(len(hits(triangles, point, -unit(down))))


def view_matrix(eye, target, down):
    """World to camera in OpenCV's frame (x right, y down, z ahead), as a 4x4 matrix."""
    eye = np.asarray(eye, dtype=np.float64)
    ahead = unit(np.asarray(target, dtype=np.float64) - eye)
    right = unit(np.cross(unit(down), ahead))
    below = np.cross(ahead, right)
    rotation = np.stack([right, below, ahead])
    matrix = np.eye(4)
    matrix[:3, :3] = rotation
    matrix[:3, 3] = -rotation @ eye
    return matrix


def lens(fov_degrees, size):
    """The 3x3 intrinsics of a square picture `size` pixels wide with that field of view."""
    focal = (size / 2) / math.tan(math.radians(fov_degrees) / 2)
    return np.array([[focal, 0, size / 2], [0, focal, size / 2], [0, 0, 1.0]])


def project(points, view, intrinsics):
    """Pixels (column, row) and depth of world points seen by a camera."""
    points = np.atleast_2d(np.asarray(points, dtype=np.float64))
    camera = (view[:3, :3] @ points.T).T + view[:3, 3]
    depth = camera[:, 2]
    safe = np.where(depth > 1e-9, depth, 1e-9)
    pixel = (intrinsics @ (camera / safe[:, None]).T).T[:, :2]
    return pixel, depth


def extents(size, turn_degrees, tilt_degrees):
    """How wide and how tall the item looks from a direction, in metres, and how far its front reaches toward it."""
    wide, deep, tall = size
    turn, tilt = math.radians(turn_degrees), math.radians(tilt_degrees)
    across = abs(wide * math.cos(turn)) + abs(deep * math.sin(turn))
    reach = (abs(wide * math.sin(turn)) + abs(deep * math.cos(turn))) / 2
    upright = abs(tall * math.cos(tilt)) + abs(2 * reach * math.sin(tilt))
    return across, upright, reach


def front_points(item, down):
    """The item's own prompt points: its front face's centre and four round it, inside its outline."""
    centre = np.asarray(item["centre"], dtype=np.float64)
    facing = unit(item["facing"])
    up = -unit(down)
    side = unit(np.cross(up, facing))
    wide, deep, tall = item["size"]
    face = centre + facing * deep / 2 * 0.9
    spread = [(0, 0), (-SPREAD, -SPREAD), (SPREAD, -SPREAD), (-SPREAD, SPREAD), (SPREAD, SPREAD)]
    return [face + side * wide * across + up * tall * upward for across, upward in spread]


def camera_for(item, triangles, down, shot):
    """One camera on an item, checked against the collider; None when it has nowhere to stand."""
    name, turn, tilt = shot
    centre = np.asarray(item["centre"], dtype=np.float64)
    direction = tilted(turned(item["facing"], down, turn), down, tilt)
    across, upright, reach = extents(item["size"], turn, tilt)
    larger = max(across, upright)
    distance = reach + (larger / 2 / FILL) / math.tan(math.radians(FOV_DEGREES) / 2)
    fov = FOV_DEGREES
    crossings = hits(triangles, centre, direction)
    beyond = crossings[crossings > reach + 0.05]
    blocked = float(beyond[0]) if len(beyond) else math.inf
    note = ""
    if blocked < distance + CLEARANCE_M:
        distance = blocked - CLEARANCE_M
        if distance - reach < NEAREST_M:
            return None
        fov = math.degrees(2 * math.atan((larger / 2 / FILL) / (distance - reach)))
        if fov > MAX_FOV_DEGREES:
            return None
        note = f"pulled in to {distance:.2f} m by a wall at {blocked:.2f} m"
    eye = centre + direction * distance
    if not inside_room(triangles, eye, down):
        return None
    return {"shot": name, "eye": eye.tolist(), "target": centre.tolist(), "fov": round(fov, 2), "size": SIZE,
            "distance_m": round(distance, 3), "note": note}


def camera_or_raised(item, triangles, down, shot):
    """The shot's camera, or when it has no room, the same turn raised until it sees over what blocked it."""
    camera = camera_for(item, triangles, down, shot)
    name, turn, tilt = shot
    for raise_by in RAISES:
        if camera is not None:
            break
        camera = camera_for(item, triangles, down, (name, turn, tilt + raise_by))
        if camera is not None:
            camera["note"] = (camera["note"] + "; " if camera["note"] else "") + f"raised {raise_by:.0f} degrees"
    return camera


def prompts_seen(points, view, intrinsics, size):
    """Each item's prompt points that fall in the picture in front of the camera, as pixels with their depth."""
    found = {}
    for other, spots in points.items():
        pixels, depth = project(spots, view, intrinsics)
        inside = (depth > 0.05) & (pixels[:, 0] >= 0) & (pixels[:, 0] < size) & (pixels[:, 1] >= 0) & (pixels[:, 1] < size)
        if inside.any():
            found[other] = [{"pixel": [round(float(u), 1), round(float(v), 1)], "depth": round(float(d), 3)}
                            for (u, v), d, keep in zip(pixels, depth, inside) if keep]
    return found


def plan(triangles, items, down):
    """Every item's cameras, each with the prompt points of the items it sees, in metres in the world's frame."""
    points = {item["id"]: front_points(item, down) for item in items}
    planned = []
    for item in items:
        for shot in SHOTS:
            camera = camera_or_raised(item, triangles, down, shot)
            if camera is None:
                continue
            view = view_matrix(camera["eye"], camera["target"], down)
            intrinsics = lens(camera["fov"], camera["size"])
            prompts = prompts_seen(points, view, intrinsics, camera["size"])
            if item["id"] in prompts:
                planned.append({**camera, "item": item["id"], "view": view.tolist(), "intrinsics": intrinsics.tolist(),
                                "prompts": prompts})
    return planned


def world_triangles(world):
    """The collider's triangles in metres."""
    import trimesh
    scale = json.loads((pathlib.Path(world) / "metric.json").read_text())["metric_scale_factor"]
    mesh = trimesh.load(pathlib.Path(world) / "collider.glb", force="mesh")
    return np.asarray(mesh.triangles, dtype=np.float64) * scale


def resolve(masks, scores):
    """One label per pixel from overlapping masks: the highest-scoring mask covering a pixel wins it; -1 where none."""
    stack = np.asarray(masks, dtype=bool)
    weighted = np.where(stack, np.asarray(scores, dtype=np.float64)[:, None, None], -np.inf)
    labels = np.argmax(weighted, axis=0)
    return np.where(stack.any(axis=0), labels, -1)


def cut(image, mask, margin=0.06):
    """The masked part of an RGB picture on transparency, cropped round the mask with a margin; None for an empty mask."""
    rows, columns = np.nonzero(mask)
    if not len(rows):
        return None
    top, bottom, left, right = rows.min(), rows.max() + 1, columns.min(), columns.max() + 1
    pad = int(margin * max(bottom - top, right - left))
    rgba = np.dstack([np.asarray(image)[..., :3], mask.astype(np.uint8) * 255])
    return rgba[max(0, top - pad):bottom + pad, max(0, left - pad):right + pad]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("world", type=pathlib.Path)
    parser.add_argument("items", type=pathlib.Path)
    parser.add_argument("--out", type=pathlib.Path)
    options = parser.parse_args()
    listed = json.loads(options.items.read_text())
    down = listed.get("down", [0, 1, 0])
    planned = plan(world_triangles(options.world), listed["items"], down)
    out = options.out or options.world / "closeups"
    out.mkdir(parents=True, exist_ok=True)
    scale = json.loads((options.world / "metric.json").read_text())["metric_scale_factor"]
    (out / "cameras.json").write_text(json.dumps({"metric_scale_factor": scale, "down": down, "items": listed["items"],
                                                  "cameras": planned}, indent=1))
    by_item = {}
    for camera in planned:
        by_item.setdefault(camera["item"], []).append(camera["shot"])
    for item in listed["items"]:
        print(item["id"], ", ".join(by_item.get(item["id"], [])) or "no camera has room")
    print(f"{len(planned)} cameras -> {out / 'cameras.json'}")


if __name__ == "__main__":
    main()
