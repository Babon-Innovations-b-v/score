"""The straightness check (hub round six, 2026-10-07): a generated piece that should be square or straight (a
manufactured box, panel or frame: details.json `square`) fails when its sides come out tilted or warped, as round
four's tall locker did ("cleaner but still seems crooked", the owner). Such a kind goes to code when its code build
shows every part its close-up has (sorter.py), else it is generated again.

    ~/.farm-factory-props/env/bin/python tools/props/library/straight.py <model.gltf|.glb> [...]

Per side (front, back, left, right, top), rays on a 7 x 7 grid from outside the piece's box straight in; the hits
are fitted with a plane. A side is crooked when the plane tilts more than TILT_DEGREES off its axis, warped when the
hits stray from the plane by more than WARP_SHARE of the piece's largest side (the 80th percentile, so knobs and
handles standing proud do not count). The model's own frame is the kit's: x across, y up, z depth.
"""
import json
import math
import pathlib
import sys

import numpy as np

TILT_DEGREES = 2.0
WARP_SHARE = 0.012
GRID = 7
# A side, as the axis its rays run along (0 x, 1 y, 2 z) and the way they run.
SIDES = {"front": (2, 1.0), "back": (2, -1.0), "left": (0, -1.0), "right": (0, 1.0), "top": (1, -1.0)}


def side_fit(mesh, axis, way, share=0.8):
    """The side's tilt in degrees and its warp (80th percentile distance from the fitted plane) in metres, from a grid
    of rays over the middle `share` of the box's face; None when too few rays meet the piece."""
    low, high = mesh.bounds
    across = [index for index in range(3) if index != axis]
    starts = []
    for first in np.linspace(0.5 - share / 2, 0.5 + share / 2, GRID):
        for second in np.linspace(0.5 - share / 2, 0.5 + share / 2, GRID):
            point = np.zeros(3)
            point[across[0]] = low[across[0]] + (high[across[0]] - low[across[0]]) * first
            point[across[1]] = low[across[1]] + (high[across[1]] - low[across[1]]) * second
            point[axis] = low[axis] - 0.1 if way > 0 else high[axis] + 0.1
            starts.append(point)
    direction = np.zeros(3)
    direction[axis] = way
    hits, rays, _ = mesh.ray.intersects_location(np.array(starts), np.tile(direction, (len(starts), 1)),
                                                 multiple_hits=False)
    if len(hits) < GRID * GRID // 2:
        return None
    plane = np.c_[hits[:, across[0]], hits[:, across[1]], np.ones(len(hits))]
    solved, *_ = np.linalg.lstsq(plane, hits[:, axis], rcond=None)
    tilt = math.degrees(math.atan(math.hypot(solved[0], solved[1])))
    warp = float(np.percentile(np.abs(plane @ solved - hits[:, axis]), 80))
    return tilt, warp


def straightness(mesh):
    """Per side its tilt and warp, and whether the piece passes: no side tilted past TILT_DEGREES or warped past
    WARP_SHARE of its largest side."""
    limit = WARP_SHARE * float(max(mesh.extents))
    sides, passes = {}, True
    for name, (axis, way) in SIDES.items():
        found = side_fit(mesh, axis, way)
        if found is None:
            continue
        tilt, warp = found
        sides[name] = {"tilt": round(tilt, 2), "warp_mm": round(warp * 1000, 1)}
        passes &= tilt <= TILT_DEGREES and warp <= limit
    return {"sides": sides, "pass": bool(passes), "warp_limit_mm": round(limit * 1000, 1)}


def loaded(path):
    import trimesh
    found = trimesh.load(path, force="scene")
    return found.to_geometry() if hasattr(found, "to_geometry") else found.dump(concatenate=True)


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    report = {pathlib.Path(path).stem: straightness(loaded(path)) for path in sys.argv[1:]}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
