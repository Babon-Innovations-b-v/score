"""Lay each Marble world built from one of our depth panoramas onto the base, in the seat's frame.

    ~/.farm-factory-props/env/bin/python tools/props/scene/align.py <depth folder> <out.json> \
        <spot>=<scene> ... [--base base.glb --plans <folder>]

A world made from a panorama stands with the panorama's camera at its origin, in Marble's frame:
x right (east, the panorama's middle column looks north), y down, z ahead (north), in model
units that `metric_scale_factor` turns into metres, with the ground `ground_plane_offset` below
the camera. Our camera stood at a known spot on the seat, a known height over the floor
(depth_pano.tscn's spots.json), so the world is scaled until its ground is that far below, its y
and z turned over into the game's (y up, z south), and moved onto the spot. Writes, per spot, the
scale and the 4x3 transform (basis columns, then origin) that does it, for a viewer to apply to
the world's splats or collider. With --base, also draws each world's collider over the base's
plan (plan-<spot>.png), the check that doorways line up between neighbours.
"""
import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from target import folder  # noqa: E402

# Marble's axes into the game's: y down to up, z ahead (north) to z south.
FLIP = np.diag([1.0, -1.0, -1.0])


def seat_transform(metric, eye_m, spot, eye_on_seat=None):
    """The scale and the (basis, origin) carrying a world's raw points onto the seat. The camera
    stands at `eye_on_seat` when given (outside, where the ground is not the seat's floor), else
    `eye_m` over the floor at the spot."""
    metres = metric["metric_scale_factor"]
    fix = eye_m / metric["ground_plane_offset"]
    basis = FLIP * metres * fix
    origin = np.array(eye_on_seat if eye_on_seat is not None else [spot[0], eye_m, spot[1]], float)
    return metres * fix, basis, origin


def placed(points, basis, origin):
    """Raw world points on the seat."""
    return points @ basis.T + origin


def transforms(depth_folder, pairs):
    """Per spot, the transform for its scene's world, from spots.json and the world's metric.json."""
    spots = json.loads((depth_folder / "spots.json").read_text())["spots"]
    found = {}
    for spot, scene in pairs.items():
        metric = json.loads((folder(scene) / "marble" / "metric.json").read_text())
        facts = spots[spot]
        scale, basis, origin = seat_transform(metric, facts["eye_m"], (facts["across"], facts["along"]),
                                              facts.get("eye_on_seat"))
        found[spot] = {"scene": scene, "scale": round(float(scale), 5), "basis": basis.T.round(6).tolist(),
                       "origin": origin.round(4).tolist(), "eye_m": facts["eye_m"]}
    return found


# A room's own plan (<spot>-room.glb) is drawn this far round its eye, in metres.
ROOM_REACH_M = 9.0


def plan(base_points, world_points, spot, path, floor_m=0.0, around=None):
    """The base's plan with one world laid over it, seen from above, near the floor and below head;
    `around` (across, along) draws only ROOM_REACH_M round that spot, for a room's own plan."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    band = lambda points: points[(points[:, 1] > floor_m + 0.2) & (points[:, 1] < floor_m + 2.2)]  # noqa: E731
    base, world = band(base_points), band(world_points)
    figure, axes = plt.subplots(figsize=(10, 6), facecolor="#111")
    axes.set_facecolor("#111")
    axes.scatter(base[:, 0], base[:, 2], s=0.05, c="#888", label="our base")
    axes.scatter(world[:, 0], world[:, 2], s=0.05, c="#ff7a3d", alpha=0.5, label=f"Marble world from {spot}")
    if around is None:
        axes.set_xlim(-30, 22)
        axes.set_ylim(16, -14)
    else:
        axes.set_xlim(around[0] - ROOM_REACH_M, around[0] + ROOM_REACH_M)
        axes.set_ylim(around[1] + ROOM_REACH_M, around[1] - ROOM_REACH_M)
    axes.set_aspect("equal")
    axes.tick_params(colors="#aaa")
    axes.legend(loc="lower left", markerscale=40, facecolor="#222", labelcolor="#ddd")
    axes.set_title(f"{spot}: walls between 0.2 and 2.2 m, metres on the seat (north up)", color="#ddd", fontsize=10)
    figure.tight_layout()
    figure.savefig(path, dpi=80, facecolor="#111")
    plt.close(figure)


def room_points(path):
    """Points spread over a room's own file, leaving out anything bigger than the room's plan
    (a sky dome, the ground out to the horizon), which would take every point."""
    import trimesh
    parts = [mesh for mesh in trimesh.load(path, force="scene").dump()
             if max(mesh.extents) < 4 * ROOM_REACH_M]
    return np.asarray(trimesh.util.concatenate(parts).sample(400000))


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("depth_folder", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("pairs", nargs="+", help="spot=scene")
    parser.add_argument("--base", type=pathlib.Path)
    parser.add_argument("--plans", type=pathlib.Path)
    options = parser.parse_args()
    pairs = dict(pair.split("=", 1) for pair in options.pairs)
    found = transforms(options.depth_folder, pairs)
    options.out.write_text(json.dumps(found, indent=1))
    if options.plans:
        import trimesh
        whole = np.asarray(trimesh.load(options.base, force="mesh").sample(400000)) if options.base else None
        for spot, item in found.items():
            # A spot taken in a frame of its own (a kit module, the ready room) has its own room file.
            own = options.depth_folder / f"{spot}-room.glb"
            base = whole if whole is not None and not own.exists() else room_points(own)
            collider = trimesh.load(folder(item["scene"]) / "marble" / "collider.glb", force="mesh")
            world = placed(np.asarray(collider.sample(200000)), np.array(item["basis"]).T, np.array(item["origin"]))
            floor_m = item["origin"][1] - item["eye_m"]
            around = (item["origin"][0], item["origin"][2]) if own.exists() else None
            plan(base, world, spot, options.plans / f"plan-{spot}.png", floor_m, around)
    for spot, item in found.items():
        print(spot, item["scene"], "scale", item["scale"])


if __name__ == "__main__":
    main()
